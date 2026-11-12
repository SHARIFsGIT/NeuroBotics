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
        find     → /eira/vision/request                     (vision_manager)
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
import os
import re
import threading
import time

import rclpy
from rclpy.action import ActionClient
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node

from action_msgs.msg import GoalStatus
from geometry_msgs.msg import Pose, PoseStamped, PoseWithCovarianceStamped
from std_msgs.msg import String, UInt16

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
        self._deadline = None      # wall-clock deadline of current wait
        self._retries_left = 0
        self._last_vision_event = None
        self._last_manip_event = None
        self._nav_result = None    # GoalStatus value once navigation settles
        self._nav_goal_handle = None
        self._planner_source = "none"   # "llm" | "fallback" — logged per task

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
        self._vision_req_pub = self.create_publisher(
            String, "eira/vision/request", 10)
        self._manip_req_pub = self.create_publisher(
            String, "eira/manipulation/request", 10)
        # Folder 22 (apriltag_transport_V2) beeps with UInt16 milliseconds.
        self._beep_pub = self.create_publisher(UInt16, "beep", 10)

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
        # STATE-MACHINE TICKER
        # --------------------------------------------------------
        self.create_timer(0.1, self._tick, callback_group=self._cb_group)

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
        if self._state not in (self.IDLE, self.DONE, self.FAILED):
            self._publish_status(
                f"rejected '{command}': planner busy in state {self._state}")
            self._beep(80)  # short refusal beep
            return

        self._state = self.PLANNING
        self._publish_status(f"planning '{command}'")
        worker = threading.Thread(
            target=self._plan_worker, args=(command,), daemon=True)
        worker.start()

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
            return

        self._plan = plan
        self._plan_idx = 0
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
        """Template-based plan extraction used when the LLM is unavailable."""
        text = command.lower()
        plan = []

        if self._RX_STOP.search(text):
            return [{"action": "stop"}]

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
            }.get(self._state)
            if handler:
                handler()
        except Exception as exc:  # noqa: BLE001 — FSM must never die silently
            self.get_logger().error(f"FSM error: {exc}")
            self._abort_task(f"internal error: {exc}")

    # -- dispatch ------------------------------------------------

    def _dispatch_next_action(self):
        if self._plan_idx >= len(self._plan):
            self._state = self.DONE
            self._beep(300)
            self._publish_status(
                f"task complete ({len(self._plan)} actions, planner="
                f"{self._planner_source})")
            self._state = self.IDLE
            return

        action = self._plan[self._plan_idx]
        kind = action["action"]
        target = action.get("target", "")
        self._publish_status(
            f"action {self._plan_idx + 1}/{len(self._plan)}: {kind} {target}")
        self._retries_left = int(self.get_parameter("action_retries").value)

        if kind == "navigate":
            if self._send_nav_goal(target):
                self._state = self.WAIT_NAV
            else:
                reason = ("navigation unavailable (nav2_msgs not installed)"
                          if self._nav_client is None
                          else f"unknown waypoint '{target}'")
                self._action_failed(reason)
        elif kind == "find":
            self._last_vision_event = None
            request = String()
            request.data = target
            self._vision_req_pub.publish(request)
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
            self._beep(200)
            self._state = self.WAIT_MISC
        elif kind == "stop":
            self._stop_everything()
            self._state = self.IDLE
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
        event = self._last_vision_event
        if event:
            if event.get("event") == "found":
                self._advance()
            elif event.get("event") in ("timeout", "tf_error"):
                self._action_failed(f"vision: {event.get('event')}")
                return
        if self._timed_out():
            self._action_failed("object not found in time")

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
        self._state = self.IDLE

    def _stop_everything(self):
        if self._nav_goal_handle is not None:
            self._nav_goal_handle.cancel_goal_async()
            self._nav_goal_handle = None
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
        # Nav2 number-of-poses feedback; deliberately quiet, kept for metrics.
        self.get_logger().debug(
            f"nav feedback: {feedback.feedback.number_of_poses} poses left")

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
    finally:
        planner.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
