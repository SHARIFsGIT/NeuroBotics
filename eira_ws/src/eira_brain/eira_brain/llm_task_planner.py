#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
llm_task_planner.py — E-AIRA cognitive core (the "Brain").

Pipeline
--------
    /eira/command (String)                      natural language, any front-end
        │
        ▼
    [Ollama / Phi-3  ──fail──►  rule-based fallback parser]   ← this node
        │  JSON action sequence (closed vocabulary)
        ▼
    /eira/plan (String, JSON)                  published for logging / HCI
        │
        ▼
    sequenced execution:
        navigate → nav2_msgs/action/NavigateThroughPoses   (folder 22 pattern)
        find     → /eira/vision_target                      (vision_manager)
        grasp    → /eira/manipulation/request               (grasp_executor)
        release  → /eira/manipulation/request
        home     → /eira/manipulation/request
        speak    → beep (UInt16)                            (folder 22 pattern)
        stop     → cancel active goal + halt manipulation

Every state transition is published on /eira/status as JSON, which is what the
evaluation harness later consumes for task-success-rate and latency metrics.

The node is fully non-blocking: the LLM HTTP call runs in a worker thread and
the execution state machine is advanced by a wall-clock timer.
"""

import json
import math
import re
import shutil
import subprocess
import threading
import time

import rclpy
from rclpy.action import ActionClient
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import ExternalShutdownException, MultiThreadedExecutor
from rclpy.node import Node

from action_msgs.msg import GoalStatus
from geometry_msgs.msg import Pose, PoseStamped, PoseWithCovarianceStamped, Twist
from std_msgs.msg import Empty, String, UInt16

from eira_brain.ollama_client import (
    ACTIONS_WITH_TARGET,
    KNOWN_ACTIONS,
    OllamaClient,
    OllamaError,
    extract_json,
)

# Nav2 is present on the robot; on dev machines without ros-humble-nav2-msgs
# the node still runs (perception/manipulation tasks and unit testing work;
# `navigate` actions report a clear failure instead of crashing).
try:
    from nav2_msgs.action import NavigateThroughPoses
    NAV2_AVAILABLE = True
except ImportError:  # pragma: no cover — dev machines only
    NavigateThroughPoses = None
    NAV2_AVAILABLE = False


# ============================================================
# NODE
# ============================================================


class LLMTaskPlanner(Node):
    """Natural-language task planner and action sequencer."""

    # -- planner FSM states (also the values published on /eira/status) --
    IDLE = "IDLE"
    PLANNING = "PLANNING"
    EXECUTING = "EXECUTING"
    WAIT_NAV = "WAIT_NAV"
    WAIT_FIND = "WAIT_FIND"
    WAIT_GRASP = "WAIT_GRASP"
    WAIT_MISC = "WAIT_MISC"
    SCAN = "SCAN"          # active search: rotating the base for the camera
    DONE = "DONE"
    FAILED = "FAILED"

    def __init__(self):
        super().__init__("llm_task_planner")

        # --------------------------------------------------------
        # PARAMETERS
        # --------------------------------------------------------
        self.declare_parameter("ollama_url", "http://localhost:11434")
        self.declare_parameter("llm_model", "phi3")
        self.declare_parameter("llm_timeout_s", 20.0)
        self.declare_parameter("waypoints_file", "")
        # Standalone-run default: the installed bringup config (the master
        # launch always passes the file explicitly).
        self.declare_parameter(
            "waypoints_file_default", "")
        self.declare_parameter("map_frame", "map")
        self.declare_parameter("nav_timeout_s", 300.0)
        self.declare_parameter("find_timeout_s", 30.0)
        self.declare_parameter("grasp_timeout_s", 90.0)
        self.declare_parameter("misc_timeout_s", 15.0)
        self.declare_parameter("action_retries", 1)
        # --- mission queue: commands arriving while busy are queued -------
        self.declare_parameter("mission_queue_len", 4)
        # --- active search: rotate the base when `find` comes up empty ---
        self.declare_parameter("scan_enabled", True)
        self.declare_parameter("scan_arc_deg", 60.0)
        self.declare_parameter("scan_speed_radps", 0.4)
        self.declare_parameter("scan_max_sweeps", 3)
        # --- spoken feedback (espeak when present, beep otherwise) --------
        self.declare_parameter("tts_enabled", True)

        self._ollama = OllamaClient(
            url=self.get_parameter("ollama_url").value,
            model=self.get_parameter("llm_model").value,
            timeout_s=self.get_parameter("llm_timeout_s").value,
        )
        self._load_waypoints()

        # --------------------------------------------------------
        # PLANNER STATE
        # --------------------------------------------------------
        self._state = self.IDLE
        self._plan = []            # validated list of action dicts
        self._plan_idx = 0
        self._plan_seq = 0          # bumped per installed plan (retry budget key)
        self._retries_stamp = None  # (plan_seq, plan_idx) budget minted for
        self._deadline = None      # wall-clock deadline of current wait
        self._retries_left = 0
        self._last_vision_event = None
        self._last_manip_event = None
        self._nav_result = None    # GoalStatus value once navigation settles
        self._nav_goal_handle = None
        self._planner_source = "none"   # "llm" | "fallback" — logged per task
        # Mission queue: commands that arrive while a task is running are
        # executed in order once the current mission reaches a terminal
        # state (a 'stop' command preempts and drops the whole queue).
        # The lock serialises queue mutation + the IDLE→PLANNING transition
        # between the command callback and the tick thread (reentrant
        # callback group → true concurrency).
        self._mission_queue = []
        self._mission_lock = threading.Lock()
        # Active-search bookkeeping (SCAN state).
        self._scans_done = 0
        self._scan_until = None
        self._scan_direction = 1        # alternates: left, right, left...
        self._last_target_pub = 0.0     # 1 Hz cap for vision-target re-sends

        self._cb_group = ReentrantCallbackGroup()

        # --------------------------------------------------------
        # SUBSCRIPTIONS
        # --------------------------------------------------------
        self.create_subscription(
            String, "eira/command", self._on_command, 10,
            callback_group=self._cb_group)

        self.create_subscription(
            String, "eira/vision/event", self._on_vision_event, 10,
            callback_group=self._cb_group)

        self.create_subscription(
            String, "eira/manipulation/event", self._on_manip_event, 10,
            callback_group=self._cb_group)

        # Kept for compatibility with RViz "2D Pose Estimate" (folder 22 uses
        # /initialpose the same way); the brain only surfaces the event —
        # AMCL consumes the original topic directly.
        self.create_subscription(
            PoseWithCovarianceStamped, "initialpose", self._on_initialpose, 1,
            callback_group=self._cb_group)

        # --------------------------------------------------------
        # PUBLISHERS
        # --------------------------------------------------------
        self._plan_pub = self.create_publisher(String, "eira/plan", 10)
        self._status_pub = self.create_publisher(String, "eira/status", 10)
        # Dynamic vision target: the label the vision stack hunts for. The
        # plan's 'find' action publishes its target here (e.g. 'bottle') and
        # vision_manager switches its YOLO search class on the fly; until a
        # message arrives, vision defaults to its own 'target_class' ('cup').
        self._vision_target_pub = self.create_publisher(
            String, "/eira/vision_target", 10)
        self._manip_req_pub = self.create_publisher(
            String, "eira/manipulation/request", 10)
        # Folder 22 (apriltag_transport_V2) beeps with UInt16 milliseconds.
        self._beep_pub = self.create_publisher(UInt16, "beep", 10)
        # Spoken-feedback event tap (consumed by any TTS/voice front-end)
        # and the scan rotation channel — the brain only writes cmd_vel
        # during SCAN, never while Nav2 or the grasp stage own the base.
        self._speech_pub = self.create_publisher(String, "eira/speech", 10)
        self._cmd_vel_pub = self.create_publisher(Twist, "cmd_vel", 10)
        # Liveness heartbeat: safety_monitor stops the base if this stops.
        self._heartbeat_pub = self.create_publisher(Empty, "eira/heartbeat", 10)

        # --------------------------------------------------------
        # NAV2 ACTION CLIENT  (NavigateThroughPoses — proven on this robot)
        # --------------------------------------------------------
        self._nav_client = None
        if NAV2_AVAILABLE:
            self._nav_client = ActionClient(
                self, NavigateThroughPoses, "navigate_through_poses")
        else:
            self.get_logger().warning(
                "nav2_msgs not installed — running without navigation "
                "support; `navigate` actions will fail with a clear status.")

        # --------------------------------------------------------
        # STATE-MACHINE TICKER + LIVENESS HEARTBEAT
        # --------------------------------------------------------
        self.create_timer(0.1, self._tick, callback_group=self._cb_group)
        self.create_timer(
            0.5, self._publish_heartbeat, callback_group=self._cb_group)

        self._publish_status("node started, waiting for /eira/command")
        self.get_logger().info(
            f"E-AIRA brain up. LLM={self._ollama.model}@{self._ollama.url}, "
            f"{len(self._waypoints)} waypoints known, "
            f"nav2={'on' if NAV2_AVAILABLE else 'off'}")

    # ========================================================
    # CONFIGURATION HELPERS
    # ========================================================

    def _load_waypoints(self):
        """Read the named-pose database used by the `navigate` action."""
        import yaml  # kept local: only needed at startup

        path = self.get_parameter("waypoints_file").value or \
            self.get_parameter("waypoints_file_default").value
        self._waypoints = {}
        self._map_frame = self.get_parameter("map_frame").value
        if not path:
            self.get_logger().warning(
                "No waypoints_file parameter — `navigate` will fail until "
                "one is provided (see eira_bringup/config/waypoints.yaml).")
            return
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = yaml.safe_load(handle) or {}
            frame = data.get("frame", self._map_frame)
            for name, pose in (data.get("waypoints") or {}).items():
                self._waypoints[name.lower()] = {
                    "x": float(pose.get("x", 0.0)),
                    "y": float(pose.get("y", 0.0)),
                    "yaw": float(pose.get("yaw", 0.0)),
                }
            self._map_frame = frame
            self.get_logger().info(
                f"Loaded {len(self._waypoints)} waypoints from {path} "
                f"(frame={self._map_frame})")
        except (OSError, yaml.YAMLError) as exc:
            self.get_logger().warning(
                f"Waypoint file {path} unusable ({exc}) — `navigate` will "
                "fail until fixed.")

    # ========================================================
    # PLANNING (runs in a worker thread, never blocks the executor)
    # ========================================================

    def _on_command(self, msg: String):
        command = msg.data.strip()
        if not command:
            return

        # A stop ALWAYS preempts: cancel motion and drop the whole queue.
        if self._state != self.IDLE and self._RX_STOP.search(command.lower()):
            with self._mission_lock:
                self._mission_queue.clear()
                self._stop_everything()
                self._state = self.IDLE
                self._publish_status(f"preempted by '{command}'")
            return

        with self._mission_lock:
            if self._state in (self.IDLE, self.DONE, self.FAILED):
                # Reserve the planner slot so a concurrent command cannot
                # also enter _spawn_plan_worker.
                self._scans_done = 0
                self._plan = []
                self._plan_idx = 0
                self._planner_source = "none"
                self._state = self.PLANNING
                start = True
            else:
                start = False
                # Mission queue: instead of rejecting, remember the command
                # and start it when the running mission finishes.
                limit = int(self.get_parameter("mission_queue_len").value)
                if len(self._mission_queue) >= limit:
                    self._publish_status(
                        f"rejected '{command}': mission queue full ({limit})")
                    self._beep(80)
                    return
                self._mission_queue.append(command)
                position = len(self._mission_queue)
        if start:
            self._spawn_plan_worker(command)
        else:
            self._beep(120)  # short acknowledgement beep
            self._publish_status(
                f"queued '{command}' (position {position} of {limit})")

    def _spawn_plan_worker(self, command: str):
        """(Caller holds no lock.) Announce + launch the planning thread."""
        self._publish_status(f"planning '{command}'")
        worker = threading.Thread(
            target=self._plan_worker, args=(command,), daemon=True)
        worker.start()

    def _finish_mission(self):
        """Terminal state reached — start the next queued mission, if any."""
        with self._mission_lock:
            if self._state != self.IDLE:
                return  # a concurrent command already started the next one
            if not self._mission_queue:
                return
            command = self._mission_queue.pop(0)
            self._scans_done = 0
            self._plan = []
            self._plan_idx = 0
            self._planner_source = "none"
            self._state = self.PLANNING
        self._spawn_plan_worker(command)

    def _plan_worker(self, command: str):
        """Query the LLM, validate, and hand the plan to the FSM."""
        raw, source = None, "llm"
        try:
            raw = self._ollama.generate_plan(command)
        except OllamaError as exc:
            self.get_logger().warning(
                f"LLM planning failed ({exc}) — using rule-based fallback.")
            source = "fallback"

        plan = None
        if raw is not None:
            plan = self._validate_plan(extract_json(raw))
        if plan is None:
            source = "fallback"
            plan = self._validate_plan(self._fallback_plan(command))

        if not plan:
            self._state = self.FAILED
            self._publish_status(
                f"no valid plan for '{command}'; nothing executed")
            with self._mission_lock:
                if self._state == self.FAILED:   # not preempted/restarted
                    self._state = self.IDLE
            self._finish_mission()
            return

        self._plan = plan
        self._plan_idx = 0
        self._plan_seq += 1
        self._planner_source = source

        plan_msg = String()
        plan_msg.data = json.dumps(
            {"source": source, "command": command, "actions": plan})
        self._plan_pub.publish(plan_msg)
        self.get_logger().info(f"Plan ({source}): {plan}")

        self._state = self.EXECUTING

    def _validate_plan(self, parsed):
        """Normalize an LLM/fallback structure into a list of action dicts.

        Returns a (possibly empty) list, or None when ``parsed`` itself was
        unusable. Unknown actions are dropped and logged — the closed
        vocabulary is the safety envelope of the whole system.
        """
        if parsed is None:
            return None
        if isinstance(parsed, dict):        # single-action answer
            parsed = [parsed]
        if not isinstance(parsed, list):
            return None

        valid = []
        for item in parsed:
            if not isinstance(item, dict):
                continue
            action = str(item.get("action", "")).strip().lower()
            if action not in KNOWN_ACTIONS:
                self.get_logger().warning(f"Dropping unknown action: {item}")
                continue
            target = str(item.get("target", "") or "").strip()
            if action in ACTIONS_WITH_TARGET and not target:
                self.get_logger().warning(
                    f"Dropping target-less action: {item}")
                continue
            entry = {"action": action}
            if target:
                entry["target"] = target
            valid.append(entry)
        return valid

    # --------------------------------------------------------
    # DETERMINISTIC BASELINE PARSER (paper ablation: no-LLM planner)
    # --------------------------------------------------------

    _RX_FETCH = re.compile(                       # "bring me a cup from the kitchen"
        r"\b(?:bring|fetch|get|take)(?:\s+me)?\s+(?:the\s+|a\s+|an\s+)?"
        r"(?P<obj>[a-z]+)\s+(?:from|in|at)\s+(?:the\s+)?(?P<wp>[a-z0-9_]+)",
        re.IGNORECASE)
    _RX_GOTO = re.compile(                        # "go to the kitchen"
        r"\b(?:go\s+to|navigate\s+to|drive\s+to|move\s+to|goto)\s+"
        r"(?:the\s+)?(?P<wp>[a-z0-9_]+)", re.IGNORECASE)
    _RX_PICK = re.compile(                        # "pick up the bottle"
        r"\b(?:pick\s+up|grab|grasp|take|get)\s+(?:the\s+|a\s+|an\s+)?"
        r"(?P<obj>[a-z]+)", re.IGNORECASE)
    _RX_FIND = re.compile(                        # "find the cup"
        r"\b(?:find|look\s+for|locate|detect)\s+(?:the\s+|a\s+|an\s+)?"
        r"(?P<obj>[a-z]+)", re.IGNORECASE)
    _RX_RELEASE = re.compile(r"\b(?:release|drop|put\s+down|place)\b",
                             re.IGNORECASE)
    _RX_HOME = re.compile(r"\b(?:go\s+home|return\s+home|come\s+back)\b",
                          re.IGNORECASE)
    _RX_STOP = re.compile(r"\b(?:stop|halt|cancel|abort)\b", re.IGNORECASE)

    def _fallback_plan(self, command: str) -> list:
        """Template-based plan extraction used when the LLM is unavailable.

        Compound commands are supported by splitting on ' and ' / ' and
        then ' and concatenating each clause's plan: "find the cup and the
        bottle" becomes two find actions; "fetch a cup and go home" becomes
        a full fetch chain followed by a return home. A stop anywhere in
        the command still preempts everything.
        """
        text = command.lower().strip()

        if self._RX_STOP.search(text):
            return [{"action": "stop"}]

        clauses = re.split(r"\s+and\s+(?:also\s+|then\s+)?", text)
        if len(clauses) > 1:
            plan = []
            for clause in clauses:
                clause = clause.strip()
                if clause:
                    plan.extend(self._fallback_plan_single(clause))
            return plan or [{"action": "speak",
                             "target": "command not understood"}]
        return self._fallback_plan_single(text)

    def _fallback_plan_single(self, text: str) -> list:
        """Plan one imperative clause (no stop handling — see above)."""
        plan = []

        fetch = self._RX_FETCH.search(text)
        if fetch:
            plan += [
                {"action": "navigate", "target": fetch.group("wp")},
                {"action": "find", "target": fetch.group("obj")},
                {"action": "grasp"},
                {"action": "navigate", "target": "home"},
                {"action": "release"},
            ]
        else:
            goto = self._RX_GOTO.search(text)
            pick = self._RX_PICK.search(text)
            find = self._RX_FIND.search(text)
            if goto:
                plan.append({"action": "navigate", "target": goto.group("wp")})
            if find:
                plan.append({"action": "find", "target": find.group("obj")})
            if pick:
                if not find or find.group("obj") != pick.group("obj"):
                    plan.append({"action": "find", "target": pick.group("obj")})
                plan.append({"action": "grasp"})
            if self._RX_HOME.search(text):
                plan.append({"action": "navigate", "target": "home"})
            if self._RX_RELEASE.search(text):
                plan.append({"action": "release"})

        if not plan:  # at least acknowledge so the task does not vanish
            plan = [{"action": "speak", "target": "command not understood"}]
        return plan

    # ========================================================
    # EVENT HANDLERS (results from the skill modules)
    # ========================================================

    def _on_vision_event(self, msg: String):
        try:
            self._last_vision_event = json.loads(msg.data)
        except json.JSONDecodeError:
            self._last_vision_event = {"event": msg.data}
        self.get_logger().debug(f"vision event: {self._last_vision_event}")

    def _on_manip_event(self, msg: String):
        try:
            self._last_manip_event = json.loads(msg.data)
        except json.JSONDecodeError:
            self._last_manip_event = {"event": msg.data}
        self.get_logger().debug(
            f"manipulation event: {self._last_manip_event}")

    def _on_initialpose(self, msg: PoseWithCovarianceStamped):
        # AMCL subscribes to /initialpose itself; we only surface the event.
        self._publish_status("initial pose updated via RViz")

    # ========================================================
    # EXECUTION STATE MACHINE (ticked at 10 Hz)
    # ========================================================

    def _tick(self):
        try:
            handler = {
                self.EXECUTING: self._dispatch_next_action,
                self.WAIT_NAV: self._check_nav,
                self.WAIT_FIND: self._check_find,
                self.WAIT_GRASP: self._check_grasp,
                self.WAIT_MISC: self._check_misc,
                self.SCAN: self._check_scan,
            }.get(self._state)
            if handler:
                handler()
        except Exception as exc:  # noqa: BLE001 — FSM must never die silently
            self.get_logger().error(f"FSM error: {exc}")
            self._abort_task(f"internal error: {exc}")

    def _publish_heartbeat(self):
        """2 Hz liveness signal for the safety watchdog."""
        self._heartbeat_pub.publish(Empty())

    # -- dispatch ------------------------------------------------

    def _dispatch_next_action(self):
        if self._plan_idx >= len(self._plan):
            self._state = self.DONE
            self._beep(300)
            self._publish_status(
                f"task complete ({len(self._plan)} actions, planner="
                f"{self._planner_source})")
            with self._mission_lock:
                if self._state == self.DONE:    # not preempted/restarted
                    self._state = self.IDLE
            self._finish_mission()
            return

        action = self._plan[self._plan_idx]
        kind = action["action"]
        target = action.get("target", "")
        self._publish_status(
            f"action {self._plan_idx + 1}/{len(self._plan)}: {kind} {target}")
        # Mint the retry budget ONCE per (plan, action-index). Re-dispatch
        # after a failed attempt must NOT reset it — otherwise the counter
        # cycles N→N-1→N→… and a failing action (e.g. `navigate` with Nav2
        # down) retries forever at 10 Hz and the task never terminates.
        stamp = (self._plan_seq, self._plan_idx)
        if self._retries_stamp != stamp:
            self._retries_stamp = stamp
            self._retries_left = int(
                self.get_parameter("action_retries").value)

        if kind == "navigate":
            if self._send_nav_goal(target):
                self._state = self.WAIT_NAV
            else:
                reason = ("navigation unavailable (nav2_msgs not installed)"
                          if self._nav_client is None
                          else f"unknown waypoint '{target}'")
                self._action_failed(reason)
        elif kind == "find":
            # Tell vision WHAT to look for — the plan's target ('bottle',
            # 'red cup', ...) travels on /eira/vision_target and overrides
            # vision_manager's default search class for this task.
            # _check_find re-sends it at 1 Hz until the find resolves.
            self._last_vision_event = None
            self._last_target_pub = time.monotonic()
            target_msg = String()
            target_msg.data = target
            self._vision_target_pub.publish(target_msg)
            self._state = self.WAIT_FIND
        elif kind == "grasp":
            self._last_manip_event = None
            self._send_manip("grasp")
            self._state = self.WAIT_GRASP
        elif kind in ("release", "home"):
            self._last_manip_event = None
            self._send_manip(kind)
            self._state = self.WAIT_MISC
        elif kind == "speak":
            # Fire-and-forget: TTS/beep runs outside the FSM, so the plan
            # advances immediately (no artificial WAIT_MISC timeout).
            self._speak(target or "acknowledged")
            self._advance()
        elif kind == "stop":
            self._stop_everything()
            # Publish a terminal status: `eira_cli` (and any harness)
            # blocks on /eira/status until DONE or FAILED — going straight
            # to IDLE would leave listeners waiting forever.
            self._state = self.DONE
            self._publish_status(
                f"stopped by command ({self._plan_idx} of "
                f"{len(self._plan)} actions had completed)")
            with self._mission_lock:
                if self._state == self.DONE:    # not preempted/restarted
                    self._state = self.IDLE
            self._finish_mission()
            return
        else:  # unreachable — validator already dropped unknowns
            self._action_failed(f"unhandled action {kind}")

        if self._state in (self.WAIT_NAV, self.WAIT_FIND,
                           self.WAIT_GRASP, self.WAIT_MISC):
            self._deadline = time.monotonic() + self._timeout_for(kind)

    def _timeout_for(self, kind: str) -> float:
        return {
            "navigate": self.get_parameter("nav_timeout_s").value,
            "find": self.get_parameter("find_timeout_s").value,
            "grasp": self.get_parameter("grasp_timeout_s").value,
        }.get(kind, self.get_parameter("misc_timeout_s").value)

    # -- wait handlers ------------------------------------------

    def _check_nav(self):
        if self._nav_result is not None:
            if self._nav_result == GoalStatus.STATUS_SUCCEEDED:
                self._advance()
            else:
                self._action_failed(
                    f"navigation ended with status {self._nav_result}")
            return
        if self._timed_out():
            if self._nav_goal_handle is not None:
                self._nav_goal_handle.cancel_goal_async()
            self._action_failed("navigation timeout")

    def _check_find(self):
        # Keep-alive: re-send the vision target ~1 Hz while waiting. The
        # message is volatile, so the dispatch-time copy is lost if
        # vision_manager was still loading its YOLO weights (10-30 s on the
        # Jetson) or restarted — without this the robot keeps hunting the
        # default class instead of the plan's target.
        self._republish_vision_target()

        event = self._last_vision_event
        if event:
            if event.get("event") == "found":
                self._scans_done = 0        # found it — reset the sweep count
                self._advance()
                return
            if event.get("event") in ("timeout", "tf_error"):
                self._find_failed(f"vision: {event.get('event')}")
                return
        if self._timed_out():
            self._find_failed("object not found in time")

    def _republish_vision_target(self):
        """(Re)send the current find target on /eira/vision_target, 1 Hz max."""
        now = time.monotonic()
        if now - self._last_target_pub < 1.0:
            return
        self._last_target_pub = now
        action = self._plan[self._plan_idx] if self._plan_idx < len(
            self._plan) else {}
        target = str(action.get("target", "") or "").strip()
        if not target:
            return
        message = String()
        message.data = target
        self._vision_target_pub.publish(message)

    def _find_failed(self, reason: str):
        """`find` came up empty: sweep the base before burning a retry.

        Active search — instead of repeating an identical doomed query,
        rotate the base ~scan_arc_deg so the camera FOV covers fresh ground,
        then re-send the vision target. Only after scan_max_sweeps do we
        fall through to the ordinary retry/abort policy.
        """
        sweeps_left = (
            bool(self.get_parameter("scan_enabled").value)
            and self._scans_done < int(
                self.get_parameter("scan_max_sweeps").value))
        if sweeps_left:
            self._begin_scan()
            return
        self._action_failed(reason)

    def _begin_scan(self):
        """Enter SCAN: rotate in place (alternating direction) for the
        time that covers scan_arc_deg at scan_speed_radps."""
        self._scans_done += 1
        self._scan_direction *= -1            # left, right, left, ...
        arc = math.radians(float(self.get_parameter("scan_arc_deg").value))
        speed = abs(float(self.get_parameter("scan_speed_radps").value))
        speed = max(speed, 0.05)              # sane floor
        duration = arc / speed

        twist = Twist()
        twist.angular.z = self._scan_direction * speed
        self._cmd_vel_pub.publish(twist)
        self._scan_until = time.monotonic() + duration
        self._state = self.SCAN

        target = self._plan[self._plan_idx].get("target", "?") \
            if self._plan_idx < len(self._plan) else "?"
        self._publish_status(
            f"scanning for '{target}' — sweep {self._scans_done}/"
            f"{self.get_parameter('scan_max_sweeps').value} "
            f"({self.get_parameter('scan_arc_deg').value:.0f}° rotation)")

    def _check_scan(self):
        if self._scan_until is not None and time.monotonic() < self._scan_until:
            return                             # still rotating
        self._zero_cmd_vel()
        # Re-dispatch the SAME find action: publishing the vision target
        # again re-arms vision's search session, and the retry stamp keeps
        # the budget untouched (scans are free, retries are not).
        self._state = self.EXECUTING

    def _check_grasp(self):
        event = self._last_manip_event
        if event:
            if event.get("event") in ("grasped", "released", "homed"):
                self._advance()
            elif event.get("event") == "failed":
                self._action_failed(
                    f"manipulation failed: {event.get('reason', '?')}")
                return
        if self._timed_out():
            self._action_failed("grasp timeout")

    def _check_misc(self):
        event = self._last_manip_event
        if event and event.get("event") in ("released", "homed", "failed"):
            if event.get("event") == "failed":
                self._action_failed(
                    f"manipulation failed: {event.get('reason', '?')}")
            else:
                self._advance()
            return
        if self._timed_out():
            # release/home are best-effort: a timeout is not a task failure
            self._advance()

    # -- helpers ------------------------------------------------

    def _timed_out(self) -> bool:
        return self._deadline is not None and time.monotonic() > self._deadline

    def _advance(self):
        self._plan_idx += 1
        self._state = self.EXECUTING
        self._nav_result = None
        self._nav_goal_handle = None

    def _action_failed(self, reason: str):
        if self._retries_left > 0:
            self._retries_left -= 1
            self._publish_status(f"retrying action ({reason})")
            self._state = self.EXECUTING          # re-dispatch same index
            self._nav_result = None
            self._nav_goal_handle = None
            return
        self._abort_task(reason)

    def _abort_task(self, reason: str):
        self._stop_everything()
        self._beep(80)
        self._state = self.FAILED
        self._publish_status(f"task aborted: {reason}")
        self.get_logger().warning(f"Task aborted: {reason}")
        with self._mission_lock:
            if self._state == self.FAILED:      # not preempted/restarted
                self._state = self.IDLE
        self._finish_mission()

    def _stop_everything(self):
        if self._nav_goal_handle is not None:
            self._nav_goal_handle.cancel_goal_async()
            self._nav_goal_handle = None
        self._scan_until = None
        self._zero_cmd_vel()                      # brain-owned scan rotation
        self._send_manip("stop")                  # zeroes cmd_vel on the base
        self._nav_result = None

    def _send_manip(self, command: str):
        request = String()
        request.data = command
        self._manip_req_pub.publish(request)

    def _beep(self, duration_ms: int):
        beep = UInt16()
        beep.data = max(0, min(60000, int(duration_ms)))
        self._beep_pub.publish(beep)

    def _zero_cmd_vel(self):
        """Stop the brain-owned rotation channel (SCAN / preemption)."""
        self._cmd_vel_pub.publish(Twist())        # all-zero Twist

    def _speak(self, phrase: str):
        """Announce a phrase: espeak TTS when installed, beep otherwise.

        The phrase is always published on /eira/speech so a future voice
        front-end (or the evaluation bag recorder) sees it regardless of
        the audio backend.
        """
        message = String()
        message.data = phrase
        self._speech_pub.publish(message)
        self.get_logger().info(f"speak: {phrase}")
        if not bool(self.get_parameter("tts_enabled").value):
            self._beep(200)
            return
        executable = shutil.which("espeak")
        if executable is None:
            self._beep(200)                      # no TTS engine on this box
            return
        try:
            subprocess.Popen(                     # non-blocking, fire-and-forget
                [executable, "-v", "en-us", phrase],
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL)
        except OSError as exc:
            self.get_logger().warning(f"espeak failed ({exc}); beeping")
            self._beep(200)

    # -- Nav2 plumbing -------------------------------------------

    def _send_nav_goal(self, waypoint_name: str) -> bool:
        if self._nav_client is None:
            return False                                # dev machine, no Nav2
        pose = self._waypoints.get(waypoint_name.lower())
        if pose is None:
            return False
        if not self._nav_client.wait_for_server(timeout_sec=2.0):
            self.get_logger().warning(
                "navigate_through_poses action server not up yet")

        goal = NavigateThroughPoses.Goal()
        stamped = PoseStamped()
        stamped.header.frame_id = self._map_frame
        stamped.header.stamp = self.get_clock().now().to_msg()
        stamped.pose = self._pose_from_waypoint(pose)
        goal.poses = [stamped]                    # single-pose variant

        self._nav_result = None
        future = self._nav_client.send_goal_async(
            goal, feedback_callback=self._on_nav_feedback)
        future.add_done_callback(self._on_goal_response)
        return True

    @staticmethod
    def _pose_from_waypoint(pose: dict) -> Pose:
        """x/y/yaw dict → geometry_msgs/Pose with yaw quaternion (ZYX)."""
        half_yaw = pose["yaw"] / 2.0
        msg = Pose()
        msg.position.x = pose["x"]
        msg.position.y = pose["y"]
        msg.position.z = 0.0
        msg.orientation.z = math.sin(half_yaw)
        msg.orientation.w = math.cos(half_yaw)
        return msg

    def _on_nav_feedback(self, feedback):
        # NavigateThroughPoses feedback: 'number_of_poses' does NOT exist
        # (that AttributeError kills the spin thread on the robot). Humble's
        # NavigateThroughPoses carries 'distance_remaining'; NavigateToPose
        # uses 'distance_to_goal'. Read defensively via getattr so this
        # callback can never raise across Nav2 versions — a debug log line
        # must not be able to take the node down.
        message = feedback.feedback
        distance = getattr(
            message, "distance_remaining",
            getattr(message, "distance_to_goal", None))
        if distance is not None:
            self.get_logger().debug(
                f"nav feedback: {distance:.2f} m to goal")

    def _on_goal_response(self, future):
        goal_handle = future.result()
        if goal_handle is None or not goal_handle.accepted:
            self._nav_result = GoalStatus.STATUS_ABORTED
            return
        self._nav_goal_handle = goal_handle
        goal_handle.get_result_async().add_done_callback(self._on_nav_result)

    def _on_nav_result(self, future):
        try:
            self._nav_result = future.result().status
        except Exception:  # noqa: BLE001 — action transport hiccups
            self._nav_result = GoalStatus.STATUS_ABORTED

    # ========================================================
    # STATUS REPORTING (the paper's measurement tap)
    # ========================================================

    def _publish_status(self, detail: str):
        status = String()
        status.data = json.dumps({
            "state": self._state,
            "step": self._plan_idx,
            "total": len(self._plan),
            "action": (self._plan[self._plan_idx].get("action", "")
                       if self._plan_idx < len(self._plan) else ""),
            "planner": self._planner_source,
            "queue": len(self._mission_queue),
            "detail": detail,
            "wall_time": time.time(),
        })
        self._status_pub.publish(status)
        self.get_logger().info(f"status: {status.data}")


# ============================================================
# ENTRY POINT
# ============================================================


def main(args=None):
    rclpy.init(args=args)
    planner = LLMTaskPlanner()
    executor = MultiThreadedExecutor()
    executor.add_node(planner)
    try:
        executor.spin()
    except (ExternalShutdownException, KeyboardInterrupt):
        pass  # SIGTERM/Ctrl-C — context is already shutting down
    finally:
        planner.destroy_node()
        if rclpy.ok():
            # On SIGTERM rclpy's signal handler shuts the context itself;
            # a second shutdown call raises RCLError and spams a traceback.
            rclpy.shutdown()


if __name__ == "__main__":
    main()
