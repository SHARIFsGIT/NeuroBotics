"""Correlated, cancellable E-AIRA mission orchestration.

Author: E-AIRA contributors.
Hardware target: Yahboom ROSMASTER M3 Pro, Jetson Orin NX, ROS 2 Humble.
LLM HTTP work runs outside the state lock. Every asynchronous result carries
its generation; cancellation invalidates pending work before stopping actuators.
"""

from collections import deque
from functools import wraps
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import threading
import time
from typing import Any, Callable
import uuid

from ament_index_python.packages import PackageNotFoundError, get_package_share_directory
import rclpy
from rclpy.action import ActionClient
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import ExternalShutdownException, MultiThreadedExecutor
from rclpy.node import Node
from rclpy.time import Time
import tf2_ros
from action_msgs.msg import GoalStatus
from geometry_msgs.msg import Pose, PoseStamped, PoseWithCovarianceStamped, Twist
from std_msgs.msg import Empty, String, UInt16

from eira_brain.console import format_line, format_plan, format_status, sanitize_text
from eira_brain.ollama_client import (
    COCO_CLASSES, MISSION_START, TARGET_COLORS, OllamaClient, OllamaError, is_stop_command, parse_plan_json,
    validate_actions,
)
from eira_brain.waypoint_store import load_waypoints

try:
    from nav2_msgs.action import NavigateThroughPoses
except ImportError:
    NavigateThroughPoses = None

NAV2_AVAILABLE = NavigateThroughPoses is not None


def synchronized(method: Callable) -> Callable:
    """Serialize callbacks with the node's reentrant state lock.

    Args:
        method: Callback that accesses mission state.

    Returns:
        Callback protected by the node state lock.
    """
    @wraps(method)
    def guarded(self: Any, *args: Any, **kwargs: Any) -> Any:
        """Invoke the wrapped method while holding the state lock.
        Returns:
            Wrapped method result.
        """
        with self._mission_lock:
            return method(self, *args, **kwargs)
    return guarded


class LLMTaskPlanner(Node):
    """Execute LLM-first missions with a deterministic fallback.

    Args:
        None.
    """

    IDLE = "IDLE"
    PLANNING = "PLANNING"
    EXECUTING = "EXECUTING"
    WAIT_NAV = "WAIT_NAV"
    NAV_SETTLE = "NAV_SETTLE"
    NAV_RETRY_WAIT = "NAV_RETRY_WAIT"
    WAIT_FIND = "WAIT_FIND"
    WAIT_GRASP = "WAIT_GRASP"
    WAIT_MISC = "WAIT_MISC"
    SCAN = "SCAN"
    DONE = "DONE"
    FAILED = "FAILED"

    def __init__(self) -> None:
        """Declare interfaces and initialize mission state."""
        super().__init__("llm_task_planner")
        defaults = {
            "ollama_url": "http://localhost:11434", "llm_model": "phi3",
            "llm_timeout_s": 30.0, "llm_retries": 1, "llm_retry_backoff_s": 0.25,
            "llm_log_raw_response": True,
            "llm_temperature": 0.1, "llm_max_tokens": 256, "waypoints_file": "",
            "waypoints_file_default": "", "map_frame": "map", "nav_timeout_s": 300.0,
            "find_timeout_s": 75.0, "grasp_timeout_s": 90.0, "misc_timeout_s": 15.0,
            "action_retries": 1, "mission_queue_len": 4, "scan_enabled": True,
            "nav_retries": 2, "nav_settle_s": 3.0, "nav_retry_delay_s": 10.0,
            "amcl_check_enabled": True, "amcl_xy_variance_max": 0.5,
            "amcl_yaw_variance_max": 0.4, "amcl_pose_timeout_s": 15.0,
            "scan_arc_deg": 60.0, "scan_speed_radps": 0.4, "scan_max_sweeps": 3,
            "tts_enabled": True, "tts_voice": "en-us", "tts_timeout_s": 15.0,
            "sound_feedback": True, "sound_short_ms": 100, "sound_long_ms": 600,
            "sound_gap_s": 0.15, "sound_queue_size": 32,
            "tick_hz": 10.0, "heartbeat_hz": 2.0, "scan_min_speed_radps": 0.05,
            "target_republish_s": 1.0, "max_plan_steps": 64, "nav_server_wait_s": 5.0,
            "grasp_target_refresh_s": 0.5,
            "known_object_classes": list(COCO_CLASSES),
            "supported_target_colors": list(TARGET_COLORS),
            "base_frame": "base_link", "start_pose_max_age_s": 2.0,
        }
        for key, value in defaults.items():
            self.declare_parameter(key, value)
        for key in ("nav_settle_s", "nav_retry_delay_s", "amcl_xy_variance_max",
                    "amcl_yaw_variance_max", "amcl_pose_timeout_s", "grasp_target_refresh_s",
                    "start_pose_max_age_s"):
            value = float(self.get_parameter(key).value)
            if not math.isfinite(value) or value < 0 or (
                    key in ("amcl_pose_timeout_s", "grasp_target_refresh_s", "start_pose_max_age_s")
                    and value == 0):
                raise ValueError(f"invalid {key}")
        if int(self.get_parameter("nav_retries").value) < 0:
            raise ValueError("nav_retries must be nonnegative")
        if any(not 0 < int(self.get_parameter(name).value) <= 65535
               for name in ("sound_short_ms", "sound_long_ms")):
            raise ValueError("buzzer durations must fit positive UInt16 milliseconds")
        gap = float(self.get_parameter("sound_gap_s").value)
        if not math.isfinite(gap) or gap < 0 or int(self.get_parameter(
                "sound_queue_size").value) < 1:
            raise ValueError("invalid buzzer gap or queue size")
        self._mission_lock = threading.RLock()
        self._tts_lock = threading.Lock()
        self._object_classes = tuple(str(value).strip().lower() for value in
                                     self.get_parameter("known_object_classes").value)
        self._target_colors = tuple(str(value).strip().lower() for value in
                                    self.get_parameter("supported_target_colors").value)
        self._active_action: dict[str, Any] | None = None
        self._mission_started_at = None
        self._planning_started_at = None
        self._llm_response_ms = 0.0
        self._planning_latency_ms = 0.0
        self._llm_attempts = 0
        self._planner_reason = "not planned"
        self._fallback_reason = None
        self._retry_count = 0
        self._scan_count_total = 0
        self._benchmark_reset = False
        self._generation = 0
        self._mission_id = ""
        self._command = ""
        self._action_id = ""
        self._attempt = 0
        self._nav_generation = 0
        self._nav_handles: dict[tuple[int, int], Any] = {}
        self._nav_goal_handle = None
        self._nav_result = None
        self._nav_token = None
        self._pending_nav_waypoint = None
        self._nav_discovery_deadline = None
        self._nav_resume_at: float | None = None
        self._amcl_pose: PoseWithCovarianceStamped | None = None
        self._amcl_received_at: float | None = None
        self._max_plan_steps = int(self.get_parameter("max_plan_steps").value)
        self._state = self.IDLE
        self._plan: list[dict[str, str]] = []
        self._plan_idx = 0
        self._plan_seq = 0
        self._retries_stamp = None
        self._deadline = None
        self._retries_left = 0
        self._last_vision_event = None
        self._last_manip_event = None
        self._found_context: dict[str, Any] = {}
        self._planner_source = "none"
        self._mission_queue: list[tuple[str, str]] = []
        self._scans_done = 0
        self._scan_until = None
        self._scan_direction = 1
        self._last_target_pub = 0.0
        self._vision_refresh_seq = 0
        self._last_grasp_target_pub: float | None = None
        self._active_vision_request: dict[str, Any] | None = None
        self._motion_owner = "none"
        self._sound_queue: deque[int] = deque(maxlen=int(self.get_parameter(
            "sound_queue_size").value))
        self._sound_next_at = 0.0
        self._closing = False
        self._waypoints: dict[str, dict[str, float]] = {}
        self._map_frame = "map"
        self._mission_start_pose: dict[str, float] | None = None
        self._tf_buffer = tf2_ros.Buffer()
        self._tf_listener = tf2_ros.TransformListener(self._tf_buffer, self, spin_thread=False)
        self._load_waypoints()
        self._ollama = OllamaClient(
            self.get_parameter("ollama_url").value,
            self.get_parameter("llm_model").value,
            self.get_parameter("llm_timeout_s").value,
            retries=self.get_parameter("llm_retries").value,
            retry_backoff_s=self.get_parameter("llm_retry_backoff_s").value,
            temperature=self.get_parameter("llm_temperature").value,
            max_tokens=self.get_parameter("llm_max_tokens").value,
        )
        self._cb_group = ReentrantCallbackGroup()
        for topic, callback in (
            ("eira/command", self._on_command), ("eira/voice", self._on_command),
            ("eira/vision/event", self._on_vision_event),
            ("eira/manipulation/event", self._on_manip_event),
            ("eira/gesture", self._on_gesture),
            ("eira/motion/event", self._on_motion_event),
        ):
            self.create_subscription(String, topic, callback, 10,
                                     callback_group=self._cb_group)
        self.create_subscription(PoseWithCovarianceStamped, "initialpose",
                                 self._on_initialpose, 1,
                                 callback_group=self._cb_group)
        self.create_subscription(PoseWithCovarianceStamped, "/amcl_pose",
                                 self._on_amcl_pose, 10,
                                 callback_group=self._cb_group)
        self._plan_pub = self.create_publisher(String, "eira/plan", 10)
        self._status_pub = self.create_publisher(String, "eira/status", 10)
        self._vision_target_pub = self.create_publisher(String, "/eira/vision_target", 10)
        self._manip_req_pub = self.create_publisher(String, "eira/manipulation/request", 10)
        self._beep_pub = self.create_publisher(UInt16, "beep", 10)
        self._speech_pub = self.create_publisher(String, "eira/speech", 10)
        self._cmd_vel_pub = self.create_publisher(Twist, "cmd_vel", 10)
        self._heartbeat_pub = self.create_publisher(Empty, "eira/heartbeat", 10)
        self._owner_pub = self.create_publisher(String, "/eira/motion_owner", 10)
        self._nav_client = (
            ActionClient(self, NavigateThroughPoses, "navigate_through_poses")
            if NAV2_AVAILABLE else None)
        self.create_timer(1.0 / max(1.0, float(self.get_parameter("tick_hz").value)),
                          self._tick, callback_group=self._cb_group)
        self.create_timer(1.0 / max(1.0, float(self.get_parameter("heartbeat_hz").value)),
                          self._publish_heartbeat, callback_group=self._cb_group)
        self.create_timer(0.05, self._tick_sound, callback_group=self._cb_group)
        self._publish_status("ready")

    def _load_waypoints(self) -> None:
        """Reload validated waypoint data before each mission."""
        path = (self.get_parameter("waypoints_file").value
                or self.get_parameter("waypoints_file_default").value)
        if not path:
            candidate = Path(__file__).resolve().parents[2] / "eira_bringup/config/waypoints.yaml"
            path = str(candidate) if candidate.is_file() else ""
            if not path:
                try:
                    path = str(Path(get_package_share_directory("eira_bringup")) /
                               "config/waypoints.yaml")
                except PackageNotFoundError:
                    path = ""
        self._map_frame = str(self.get_parameter("map_frame").value)
        if not path:
            return
        try:
            data = load_waypoints(Path(path).expanduser())
            self._waypoints = data["waypoints"]
            if self._waypoints.pop(MISSION_START, None) is not None:
                self.get_logger().warning(format_line(
                    "BRAIN", "Ignored waypoint mission_start: this name is reserved for the return pose",
                    "warning"))
            self._map_frame = data["frame"]
        except (OSError, ValueError) as exc:
            self._waypoints = {}
            self.get_logger().error(format_line(
                "BRAIN", f"Cannot load waypoints: {sanitize_text(exc)}", "error"))

    @synchronized
    def _on_command(self, msg: String) -> None:
        """Queue an instruction or synchronously invalidate all work on stop.

        Args:
            msg: Plain command or JSON {command, mission_id} envelope.
        """
        command = msg.data.strip()
        payload: dict[str, Any] = {}
        mission_id = uuid.uuid4().hex
        if command.startswith("{"):
            try:
                payload = json.loads(command)
            except json.JSONDecodeError:
                return
            if not isinstance(payload, dict) or not isinstance(payload.get("command"), str):
                return
            command = payload["command"].strip()
            mission_id = str(payload.get("mission_id") or mission_id)
        if not command or self._closing:
            return
        if payload.get("purpose") == "benchmark_reset":
            waypoint = payload.get("start_waypoint")
            if not isinstance(waypoint, str) or not waypoint.strip():
                self._publish_status("rejected: reset requires start_waypoint",
                                     mission_id=mission_id, benchmark_reset=True,
                                     source="benchmark_reset", planner="benchmark_reset")
                return
            if self._state not in (self.IDLE, self.DONE, self.FAILED):
                self._publish_status("rejected: reset requires an idle planner",
                                     mission_id=mission_id, benchmark_reset=True,
                                     source="benchmark_reset", planner="benchmark_reset")
                return
            self._reserve_mission(command, mission_id, reset_waypoint=waypoint.strip().lower())
            return
        if is_stop_command(command):
            self._generation += 1
            self._mission_queue.clear()
            self._end_action("canceled", "mission canceled by stop")
            self._stop_everything()
            if self._mission_id and self._state not in (self.IDLE, self.DONE, self.FAILED):
                self._state = self.FAILED
                self._publish_status("mission canceled by stop", event="mission_finished",
                                     result="canceled", success=False,
                                     error_reason="mission canceled by stop",
                                     duration_s=self._mission_duration())
            self._mission_id, self._command = mission_id, command
            self._benchmark_reset = False
            self._state = self.DONE
            self._publish_status("stopped", event="mission_finished", result="succeeded",
                                 success=True, duration_s=0.0, error_reason=None)
            self._state = self.IDLE
            return
        if self._state not in (self.IDLE, self.DONE, self.FAILED):
            limit = max(0, int(self.get_parameter("mission_queue_len").value))
            if len(self._mission_queue) >= limit:
                self._publish_status("rejected: mission queue full", mission_id=mission_id)
                return
            self._mission_queue.append((command, mission_id))
            self._publish_status("queued", mission_id=mission_id, command=command)
            return
        self._reserve_mission(command, mission_id)

    def _reserve_mission(self, command: str, mission_id: str,
                         reset_waypoint: str | None = None) -> None:
        """Reserve a generation while the state lock is held.

        Args:
            command: Natural-language instruction.
            mission_id: Request identity returned to frontend observers.
            reset_waypoint: Trusted benchmark reset destination; normal commands use the LLM.
        """
        self._generation += 1
        self._mission_id, self._command = mission_id, command
        self._action_id = ""
        self._active_action = None
        self._benchmark_reset = reset_waypoint is not None
        self._mission_started_at = time.monotonic()
        self._planning_started_at = self._mission_started_at
        self._llm_response_ms = self._planning_latency_ms = 0.0
        self._llm_attempts = self._retry_count = self._scan_count_total = 0
        self._planner_reason, self._fallback_reason = "planning", None
        self._found_context = {}
        self._nav_resume_at = None
        self._last_grasp_target_pub = None
        self._scans_done = 0
        self._plan, self._plan_idx = [], 0
        self._planner_source = "none"
        self._state = self.PLANNING
        self._load_waypoints()
        self._mission_start_pose = self._capture_start_pose() if reset_waypoint is None else None
        if reset_waypoint is not None:
            self._planner_source = "benchmark_reset"
            self._publish_status("benchmark reset", event="mission_started")
            plan, reason = validate_actions(
                [{"action": "navigate", "target": reset_waypoint}], tuple(self._waypoints))
            self._planner_reason = "trusted navigation-only benchmark reset" if plan else reason
            self._plan = plan or []
            self._plan_seq += 1
            self._publish_plan(command)
            if plan:
                self._state = self.EXECUTING
            else:
                self._abort_task(reason)
            return
        self._spawn_plan_worker(command)

    def _spawn_plan_worker(self, command: str) -> None:
        """Start bounded LLM work without holding the executor thread.

        Args:
            command: Instruction belonging to the current generation.
        """
        self._publish_status("planning", event="mission_started")
        threading.Thread(target=self._plan_worker, args=(command, self._generation),
                         daemon=True).start()

    @synchronized
    def _finish_mission(self) -> None:
        """Start the next FIFO command after a terminal state."""
        if self._state == self.IDLE and self._mission_queue:
            self._reserve_mission(*self._mission_queue.pop(0))

    def _plan_worker(self, command: str, generation: int | None = None) -> None:
        """Ground model outputs, retry one invalid response, then use the fallback.

        Args:
            command: Natural-language instruction.
            generation: Generation captured before the external call.
        """
        with self._mission_lock:
            generation = self._generation if generation is None else generation
            if generation != self._generation or self._closing:
                return
            started = getattr(self, "_planning_started_at", None) or time.monotonic()
            places = self._planning_places()
            classes = getattr(self, "_object_classes", COCO_CLASSES)
            colors = getattr(self, "_target_colors", TARGET_COLORS)
            mission_id = self._mission_id
        plan = None
        source, reason, fallback_reason = "llm", "grounded LLM plan", None
        response_ms, calls, validation_reason = 0.0, 0, ""
        for attempt in range(2):
            with self._mission_lock:
                if generation != self._generation or self._closing:
                    return
            call_started = time.monotonic()
            calls += 1
            try:
                raw = self._ollama.generate_plan(
                    command, waypoints=places, object_classes=classes, colors=colors,
                    repair_reason=validation_reason)
            except OllamaError as exc:
                response_ms += (time.monotonic() - call_started) * 1000.0
                fallback_reason = f"LLM unavailable: {exc}"
                break
            response_ms += (time.monotonic() - call_started) * 1000.0
            if self.get_parameter("llm_log_raw_response").value:
                self.get_logger().debug(format_line(
                    "BRAIN", f"Model reply {attempt + 1} for {sanitize_text(mission_id)}: "
                    f"{sanitize_text(raw, limit=0)}", "debug"))
            plan, validation_reason = self._validate_command_plan(command, parse_plan_json(raw), places)
            if plan is not None:
                reason = "grounded LLM plan" if attempt == 0 else "grounded LLM plan after repair"
                break
            fallback_reason = f"invalid LLM response: {validation_reason}"
        if plan is None:
            source = "fallback"
            plan, validation_reason = self._validate_command_plan(command, self._fallback_plan(command), places)
            reason = fallback_reason or "LLM plan was unusable"
            if plan is None:
                reason += f"; fallback rejected: {validation_reason}"
        with self._mission_lock:
            if generation != self._generation or self._state != self.PLANNING or self._closing:
                return
            self._llm_response_ms = response_ms
            self._planning_latency_ms = (time.monotonic() - started) * 1000.0
            self._llm_attempts = calls
            self._planner_reason, self._fallback_reason = reason, fallback_reason
            self._planner_source = source
            self._plan, self._plan_idx = plan or [], 0
            self._plan_seq += 1
            self._publish_plan(command)
            if plan is None:
                self._abort_task(reason)
                return
            self._state = self.EXECUTING
            self._publish_status("planning complete", event="planning_finished")

    def _publish_plan(self, command: str) -> None:
        """Publish backward-compatible plans with measured planning provenance.

        Args:
            command: Original instruction or trusted reset description.
        """
        self._plan_pub.publish(String(data=json.dumps({
            "source": self._planner_source, "planner": self._planner_source,
            "command": command, "actions": self._plan, "mission_id": self._mission_id,
            "reason": self._planner_reason, "planner_reason": self._planner_reason,
            "fallback_reason": self._fallback_reason, "llm_response_ms": self._llm_response_ms,
            "planning_latency_ms": self._planning_latency_ms, "llm_attempts": self._llm_attempts,
            "benchmark_reset": getattr(self, "_benchmark_reset", False),
            "wall_time": time.time(), "monotonic_ns": time.monotonic_ns(),
            "ros_stamp_ns": self._ros_stamp_ns(),
        })))
        self.get_logger().info(format_line("BRAIN", format_plan(self._plan)))

    def _validate_plan(self, parsed: Any) -> list[dict[str, str]] | None:
        """Validate the entire plan against configured resources and prerequisites.

        Args:
            parsed: Decoded model response or fallback plan.

        Returns:
            Normalized complete plan, or None when any step is invalid.
        """
        plan, _ = validate_actions(
            parsed, tuple(self._waypoints) if hasattr(self, "_waypoints") else None,
            getattr(self, "_object_classes", COCO_CLASSES),
            getattr(self, "_target_colors", TARGET_COLORS),
            getattr(self, "_max_plan_steps", 64))
        return plan

    def _planning_places(self) -> tuple[str, ...]:
        """Expose the reserved return target only after a real start pose was captured."""
        places = tuple(name for name in self._waypoints if name != MISSION_START)
        return places + ((MISSION_START,) if getattr(self, "_mission_start_pose", None) else ())

    def _validate_command_plan(self, command: str, parsed: Any,
                               waypoints: tuple[str, ...] | None = None
                               ) -> tuple[list[dict[str, str]] | None, str]:
        """Ground actions and require a fetch to preserve its object, source, and return."""
        places = self._planning_places() if waypoints is None else waypoints
        classes = getattr(self, "_object_classes", COCO_CLASSES)
        colors = getattr(self, "_target_colors", TARGET_COLORS)
        fetch = self._RX_FETCH.search(command.lower().strip())
        expected = None
        if fetch:
            if MISSION_START not in places:
                return None, ("cannot fetch: initial robot pose unavailable or stale; "
                              "provide fresh map-to-base TF or a localized AMCL pose before retrying")
            source = self._fallback_waypoint(fetch.group("wp"))
            if source == MISSION_START:
                return None, "mission_start is reserved for the captured return pose"
            expected = [step for step in self._fallback_plan(command) if step["action"] != "speak"]
            grounded, reason = validate_actions(expected, places, classes, colors)
            if grounded is None:
                return None, reason
        plan, reason = validate_actions(parsed, places, classes, colors,
                                        getattr(self, "_max_plan_steps", 64))
        if plan is not None and expected is not None:
            primitives = [step for step in plan if step["action"] != "speak"]
            if primitives != expected:
                return None, ("fetch must navigate to the requested place, find the requested "
                              "object, grasp, return to mission_start, and release in that order")
        return plan, reason

    def _fallback_waypoint(self, name: str) -> str:
        """Resolve spoken spaces to an existing waypoint without dropping unknown words."""
        normalized = re.sub(r"[_\s-]+", " ", name.strip().lower())
        for place in getattr(self, "_waypoints", {}):
            if re.sub(r"[_\s-]+", " ", place) == normalized:
                return place
        return name.strip().lower()

    @staticmethod
    def _planar_pose(position: Any, rotation: Any) -> dict[str, float]:
        """Copy a finite position and normalized quaternion into immutable planar values."""
        x, y = float(position.x), float(position.y)
        q = [float(getattr(rotation, axis)) for axis in ("x", "y", "z", "w")]
        norm = math.sqrt(sum(value * value for value in q))
        if not all(math.isfinite(value) for value in (x, y, *q, norm)) or norm < 1e-8:
            raise ValueError("invalid initial pose")
        qx, qy, qz, qw = (value / norm for value in q)
        return {"x": x, "y": y, "yaw": math.atan2(
            2 * (qw * qz + qx * qy), 1 - 2 * (qy * qy + qz * qz))}

    def _capture_start_pose(self) -> dict[str, float] | None:
        """Capture once at mission reservation; never substitute the named home waypoint."""
        max_age = float(self.get_parameter("start_pose_max_age_s").value)
        now_ns = self._ros_stamp_ns()

        def fresh(header: Any) -> bool:
            stamp = header.stamp.sec * 1_000_000_000 + header.stamp.nanosec
            return (header.frame_id == self._map_frame and stamp > 0 and now_ns is not None
                    and 0 <= (now_ns - stamp) * 1e-9 <= max_age)

        buffer = getattr(self, "_tf_buffer", None)
        if buffer is not None:
            try:
                transform = buffer.lookup_transform(
                    self._map_frame, self.get_parameter("base_frame").value, Time())
                if fresh(transform.header):
                    return self._planar_pose(transform.transform.translation,
                                             transform.transform.rotation)
            except (tf2_ros.TransformException, AttributeError, TypeError, ValueError):
                pass
        pose = getattr(self, "_amcl_pose", None)
        received = getattr(self, "_amcl_received_at", None)
        try:
            if (pose is not None and received is not None and fresh(pose.header)
                    and 0 <= time.monotonic() - received <= max_age
                    and self._check_amcl_convergence()):
                return self._planar_pose(pose.pose.pose.position, pose.pose.pose.orientation)
        except (AttributeError, TypeError, ValueError):
            pass
        return None

    _RX_FETCH = re.compile(                       # "bring me a wine glass from the kitchen"
        r"\b(?:bring|fetch|get|take)(?:\s+me)?\s+(?:the\s+|a\s+|an\s+)?"
        r"(?P<obj>[a-z][a-z _-]*?)"
        r"\s+(?:from|in|at)\s+(?:the\s+)?(?P<wp>[a-z0-9_-]+(?:\s+[a-z0-9_-]+)*?)"
        r"(?=\s+(?:and|then|please)\b|[.!?,;]|$)",
        re.IGNORECASE)
    _RX_GOTO = re.compile(                        # "go to the kitchen"
        r"\b(?:go\s+to|navigate\s+to|drive\s+to|move\s+to|goto)\s+"
        r"(?:the\s+)?(?P<wp>[a-z0-9_]+)", re.IGNORECASE)
    _RX_PICK = re.compile(                        # "pick up the bottle"
        r"\b(?:pick\s+up|grab|grasp|take|get)\s+(?:the\s+|a\s+|an\s+)?"
        r"(?P<obj>(?:(?:red|blue|green|yellow|orange|white|black)\s+)?[a-z]+)",
        re.IGNORECASE)
    _RX_FIND = re.compile(                        # "find the cup"
        r"\b(?:find|look\s+for|locate|detect)\s+(?:the\s+|a\s+|an\s+)?"
        r"(?P<obj>(?:(?:red|blue|green|yellow|orange|white|black)\s+)?[a-z]+)",
        re.IGNORECASE)
    _RX_RELEASE = re.compile(r"\b(?:release|drop|put\s+down|place)\b",
                             re.IGNORECASE)
    _RX_HOME = re.compile(r"\b(?:go\s+home|return\s+home)\b",
                          re.IGNORECASE)
    _RX_RETURN_START = re.compile(
        r"\b(?:come\s+back|return\s+(?:back\s+)?(?:to\s+)?(?:the\s+)?"
        r"(?:initial|starting|start|original)\s+(?:position|pose|location))\b", re.IGNORECASE)

    def _fallback_plan(self, command: str) -> list[dict[str, str]]:
        """Template-based plan extraction used when the LLM is unavailable.

        Compound commands are supported by splitting on ' and ' / ' and
        then ' and concatenating each clause's plan: "find the cup and the
        bottle" becomes two find actions; "fetch a cup and go home" becomes
        a full fetch chain followed by a return home. A stop anywhere in
        the command still preempts everything.
        """
        text = command.lower().strip()

        if is_stop_command(text):
            return [{"action": "stop"}]

        clauses = re.split(r"\s+(?:and(?:\s+(?:also|then))?|then)\s+", text)
        if len(clauses) > 1:
            plan = []
            for clause in clauses:
                clause = clause.strip()
                if clause:
                    following = self._fallback_plan_single(clause)
                    if (following == [{"action": "navigate", "target": MISSION_START}]
                            and len(plan) >= 2 and plan[-2:] == [
                                {"action": "navigate", "target": MISSION_START},
                                {"action": "release"}]):
                        continue
                    plan.extend(following)
            return plan or [{"action": "speak",
                             "target": "command not understood"}]
        return self._fallback_plan_single(text)

    def _fallback_plan_single(self, text: str) -> list[dict[str, str]]:
        """Plan one imperative clause (no stop handling — see above)."""
        plan = []

        sorting = re.search(
            r"\bsort\s+(?:the\s+)?(?P<obj>(?:red|blue|green|yellow|orange|white|black)"
            r"\s+[a-z]+)\s+(?:to|into)\s+(?:the\s+)?(?P<wp>[a-z0-9_\-]+)", text)
        if sorting:
            return [{"action": "find", "target": sorting.group("obj")},
                    {"action": "grasp"},
                    {"action": "navigate", "target": sorting.group("wp")},
                    {"action": "release"}]
        fetch = self._RX_FETCH.search(text)
        if fetch:
            plan += [
                {"action": "navigate", "target": self._fallback_waypoint(fetch.group("wp"))},
                {"action": "find", "target": " ".join(fetch.group("obj").split())},
                {"action": "grasp"},
                {"action": "navigate", "target": MISSION_START},
                {"action": "release"},
            ]
        else:
            goto = self._RX_GOTO.search(text)
            pick = self._RX_PICK.search(text)
            find = self._RX_FIND.search(text)
            if goto:
                plan.append({"action": "navigate", "target": goto.group("wp")})
            if find:
                plan.append({"action": "find", "target": self._fallback_object(text, find)})
            if pick:
                if (not find or self._fallback_object(text, find)
                        != self._fallback_object(text, pick)):
                    plan.append({"action": "find", "target": self._fallback_object(text, pick)})
                plan.append({"action": "grasp"})
            if self._RX_HOME.search(text):
                plan.append({"action": "navigate", "target": "home"})
            elif self._RX_RETURN_START.search(text):
                plan.append({"action": "navigate", "target": MISSION_START})
            if self._RX_RELEASE.search(text):
                plan.append({"action": "release"})

        if not plan:  # at least acknowledge so the task does not vanish
            plan = [{"action": "speak", "target": "command not understood"}]
        return plan

    def _fallback_object(self, text: str, match: re.Match[str]) -> str:
        """Preserve configured multiword classes and optional colors in fallback plans.

        Args:
            text: Current imperative clause.
            match: Regex match whose obj group marks the first noun token.

        Returns:
            Longest configured class target, or the original noun for safe rejection.
        """
        remaining = text[match.start("obj"):].lower()
        classes = sorted(getattr(self, "_object_classes", COCO_CLASSES), key=len, reverse=True)
        colors = getattr(self, "_target_colors", TARGET_COLORS)
        for prefix in ("", *(color + " " for color in colors)):
            for label in classes:
                target = prefix + label
                if re.match(re.escape(target) + r"\b", remaining):
                    return target
        return match.group("obj")

    @synchronized
    def _on_vision_event(self, msg: String) -> None:
        """Accept only a vision event for the current action.

        Args:
            msg: JSON event including mission_id and action_id.
        """
        event = self._correlated_event(msg)
        if event is not None and self._state in (self.WAIT_FIND, self.SCAN):
            if (event.get("event") == "found" and self._plan_idx < len(self._plan)
                    and event.get("target") != self._plan[self._plan_idx].get("target")):
                return
            self._last_vision_event = event

    @synchronized
    def _on_manip_event(self, msg: String) -> None:
        """Accept only manipulation events for the current action.

        Args:
            msg: Correlated manipulation event.
        """
        event = self._correlated_event(msg)
        if event is not None and self._state in (self.WAIT_GRASP, self.WAIT_MISC):
            self._last_manip_event = event

    def _correlated_event(self, msg: String) -> dict[str, Any] | None:
        """Validate an asynchronous event identity.

        Args:
            msg: JSON String event.

        Returns:
            Event object when both identifiers match, otherwise None.
        """
        try:
            event = json.loads(msg.data)
        except json.JSONDecodeError:
            return None
        if not isinstance(event, dict):
            return None
        if (event.get("mission_id") != self._mission_id
                or event.get("action_id") != self._action_id):
            return None
        return event

    def _on_initialpose(self, msg: PoseWithCovarianceStamped) -> None:
        """Expose localization updates without changing mission state.

        Args:
            msg: Pose consumed independently by AMCL.
        """
        self._publish_status("initial pose updated")

    @synchronized
    def _on_amcl_pose(self, msg: PoseWithCovarianceStamped) -> None:
        """Cache localization evidence without blocking action callbacks.

        Args:
            msg: AMCL map-frame pose with x/y/yaw covariance.
        """
        self._amcl_pose = msg
        self._amcl_received_at = time.monotonic()

    def _check_amcl_convergence(self) -> bool:
        """Check fresh planar covariance and warn before submitting a Nav2 goal.

        Missing AMCL is advisory because external localization is supported.
        Covariance is an uncertainty indicator, not proof of localization accuracy.

        Returns:
            Whether the available AMCL estimate passes configured age/variance limits.
        """
        if not self.get_parameter("amcl_check_enabled").value:
            return True
        pose = getattr(self, "_amcl_pose", None)
        received = getattr(self, "_amcl_received_at", None)
        maximum_age = float(self.get_parameter("amcl_pose_timeout_s").value)
        reason = "AMCL pose unavailable"
        variances = None
        if pose is not None and received is not None:
            try:
                age = time.monotonic() - received
                stamp_ns = (pose.header.stamp.sec * 1_000_000_000
                            + pose.header.stamp.nanosec)
                now_ns = self._ros_stamp_ns()
                sensor_age = (now_ns - stamp_ns) * 1e-9 if now_ns is not None else age
                variances = [float(pose.pose.covariance[index]) for index in (0, 7, 35)]
                if pose.header.frame_id != self._map_frame:
                    reason = "AMCL pose has the wrong map frame"
                elif stamp_ns <= 0 or sensor_age < 0 or max(age, sensor_age) > maximum_age:
                    reason = "AMCL pose stale or timestamp invalid"
                elif not all(math.isfinite(value) and value >= 0 for value in variances):
                    reason = "AMCL covariance invalid"
                elif (max(variances[:2]) > float(self.get_parameter(
                        "amcl_xy_variance_max").value) or variances[2] > float(
                            self.get_parameter("amcl_yaw_variance_max").value)):
                    reason = "AMCL covariance exceeds configured limits"
                else:
                    return True
            except (AttributeError, IndexError, TypeError, ValueError, OverflowError):
                reason = "AMCL pose/covariance malformed"
        self.get_logger().warning(format_line(
            "BRAIN", "AMCL uncertainty high, navigation may fail: " + sanitize_text(reason),
            "warning"))
        return False

    @synchronized
    def _on_gesture(self, msg: String) -> None:
        """Make a cancel gesture an immediate stop; Arm handles confirmation.

        Args:
            msg: Gesture label or JSON with gesture field.
        """
        label = msg.data
        try:
            payload = json.loads(label)
            if isinstance(payload, dict):
                label = str(payload.get("gesture", ""))
        except json.JSONDecodeError:
            pass
        if label.lower() in ("thumb_down", "thumbs_down"):
            self._on_command(String(data="stop"))

    @synchronized
    def _on_motion_event(self, msg: String) -> None:
        """Cancel missions when the velocity gate revokes motion for a hazard.

        Args:
            msg: Correlated gate event describing the safety stop.
        """
        event = self._correlated_event(msg)
        if event is None or self._state in (self.IDLE, self.DONE, self.FAILED):
            return
        if event.get("event") in ("heartbeat_stale", "safety_stop", "edge_blocked_or_stale"):
            self._generation += 1
            self._mission_queue.clear()
            self._abort_task(f"motion gate: {event['event']}")

    @synchronized
    def _tick(self) -> None:
        """Advance exactly one serialized state-machine transition."""
        handler = {
            self.EXECUTING: self._dispatch_next_action,
            self.WAIT_NAV: self._check_nav, self.WAIT_FIND: self._check_find,
            self.NAV_SETTLE: self._check_nav_delay,
            self.NAV_RETRY_WAIT: self._check_nav_delay,
            self.WAIT_GRASP: self._check_grasp, self.WAIT_MISC: self._check_misc,
            self.SCAN: self._check_scan,
        }.get(self._state)
        if handler:
            try:
                handler()
            except (RuntimeError, ValueError, TypeError, AttributeError, OSError) as exc:
                self._abort_task(f"execution error: {exc}")

    @synchronized
    def _publish_heartbeat(self) -> None:
        """Renew liveness and the velocity gate's ownership lease."""
        self._heartbeat_pub.publish(Empty())
        self._set_owner(self._motion_owner)

    def _set_owner(self, owner: str) -> None:
        """Select the only permitted velocity source.

        Args:
            owner: brain, arm, nav, or none.
        """
        self._motion_owner = owner
        self._owner_pub.publish(String(data=json.dumps({
            "owner": owner, "mission_id": self._mission_id, "action_id": self._action_id})))

    def _dispatch_next_action(self) -> None:
        """Dispatch one step while preserving its bounded retry budget."""
        if self._plan_idx >= len(self._plan):
            self._set_owner("none")
            self._state = self.DONE
            self._publish_status("task complete", event="mission_finished", success=True,
                                 result="succeeded", error_reason=None,
                                 duration_s=self._mission_duration(),
                                 physical_contact_verified=False)
            self._state = self.IDLE
            self._finish_mission()
            return
        action = self._plan[self._plan_idx]
        kind, target = action["action"], action.get("target", "")
        stamp = (self._plan_seq, self._plan_idx)
        if self._retries_stamp != stamp:
            self._retries_stamp = stamp
            retry_parameter = "nav_retries" if kind == "navigate" else "action_retries"
            self._retries_left = max(0, int(self.get_parameter(retry_parameter).value))
            self._attempt = 0
        self._attempt += 1
        self._action_id = f"{self._plan_idx}:{self._attempt}"
        self._deadline = time.monotonic() + self._timeout_for(kind)
        self._last_vision_event = self._last_manip_event = None
        self._begin_action(kind, target)
        if kind == "navigate":
            self._set_owner("nav")
            self._state = self.WAIT_NAV
            if not self._send_nav_goal(target):
                self._action_failed("navigation server or waypoint unavailable")
        elif kind == "find":
            self._vision_refresh_seq = getattr(self, "_vision_refresh_seq", 0) + 1
            self._set_owner("none")
            self._state = self.WAIT_FIND
            self._last_target_pub = 0.0
            self._republish_vision_target()
        elif kind in ("grasp", "release", "home"):
            self._last_grasp_target_pub = None
            self._set_owner("arm")
            self._state = self.WAIT_GRASP if kind == "grasp" else self.WAIT_MISC
            self._send_manip(kind)
        elif kind == "speak":
            self._speak(target or "acknowledged")
            self._advance()
        elif kind == "stop":
            self._stop_everything()
            self._advance()

    def _timeout_for(self, kind: str) -> float:
        """Return a positive per-action timeout.

        Args:
            kind: Primitive action name.

        Returns:
            Timeout in seconds.
        """
        parameter = {"navigate": "nav_timeout_s", "find": "find_timeout_s",
                     "grasp": "grasp_timeout_s"}.get(kind, "misc_timeout_s")
        return max(0.1, float(self.get_parameter(parameter).value))

    def _check_nav(self) -> None:
        """Consume only the current navigation attempt result."""
        if self._pending_nav_waypoint is not None:
            if self._nav_client is not None and self._nav_client.server_is_ready():
                waypoint = self._pending_nav_waypoint
                self._pending_nav_waypoint = None
                if not self._send_nav_goal(waypoint):
                    self._action_failed("navigation submission failed")
            elif time.monotonic() >= self._nav_discovery_deadline:
                self._action_failed("navigation server discovery timeout")
            return
        if self._nav_result is not None:
            if self._nav_result == GoalStatus.STATUS_SUCCEEDED:
                self._end_action("succeeded")
                self._set_owner("none")
                self._zero_cmd_vel()
                self._nav_result = self._nav_goal_handle = self._nav_token = None
                delay = max(0.0, float(self.get_parameter("nav_settle_s").value))
                self._nav_resume_at = time.monotonic() + delay
                self._deadline = None
                self._state = self.NAV_SETTLE
                self._publish_status("waiting for AMCL after navigation",
                                     event="navigation_settling", delay_s=delay)
            else:
                self._action_failed(f"navigation status {self._nav_result}")
        elif self._timed_out():
            self._action_failed("navigation timeout")

    def _check_nav_delay(self) -> None:
        """Finish navigation settling or retry backoff without sleeping an executor."""
        deadline = getattr(self, "_nav_resume_at", None)
        if deadline is None or time.monotonic() < deadline:
            return
        self._nav_resume_at = None
        if self._state == self.NAV_SETTLE:
            self._advance()
        elif self._state == self.NAV_RETRY_WAIT:
            self._state = self.EXECUTING

    def _check_find(self) -> None:
        """Wait for the matching target acquisition, then optionally scan."""
        self._republish_vision_target()
        event = self._last_vision_event
        if event and event.get("event") == "found":
            self._found_context = dict(event)
            self._scans_done = 0
            self._advance()
            return
        if event and event.get("event") in ("timeout", "tf_error", "failed"):
            reason = str(event.get("reason") or event.get("event"))
            detail = str(event.get("detail") or "")
            if event.get("event") == "failed":
                self._abort_task(f"vision failed: {reason}" + (f": {detail}" if detail else ""))
            else:
                self._find_failed(reason + (f": {detail}" if detail else ""))
        elif self._timed_out():
            if self._vision_target_pub.get_subscription_count() == 0:
                self._abort_task("vision manager unavailable: no subscriber on /eira/vision_target; "
                                 "start vision_manager with use_perception:=true")
            else:
                self._find_failed("object acquisition timeout")

    def _republish_vision_target(self) -> None:
        """Repeat the same correlated target without resetting its identity."""
        now = time.monotonic()
        period = max(0.1, float(self.get_parameter("target_republish_s").value))
        if now - self._last_target_pub < period:
            return
        self._last_target_pub = now
        target = self._plan[self._plan_idx].get("target", "")
        self._publish_vision_request(target, getattr(self, "_vision_refresh_seq", 0))

    def _publish_vision_request(self, target: str, refresh_id: int) -> None:
        """Request one bounded acquisition through the existing String topic.

        Args:
            target: Detector class with optional supported color prefix.
            refresh_id: One-shot token; repeated keepalives do not restart a search.
        """
        request = {"mission_id": self._mission_id, "action_id": self._action_id,
                   "target": target, "refresh_id": refresh_id}
        self._active_vision_request = request
        self._vision_target_pub.publish(String(data=json.dumps(request)))

    def _cancel_vision_request(self) -> None:
        """Cancel any remaining one-shot search when its action or mission ends."""
        request = getattr(self, "_active_vision_request", None)
        if request is not None:
            self._vision_target_pub.publish(String(data=json.dumps({**request, "cancel": True})))
        self._active_vision_request = None

    def _refresh_grasp_target(self) -> None:
        """Request fresh real poses only while grasp alignment can need them."""
        target = self._found_context.get("target")
        if not isinstance(target, str) or not target:
            return
        now = time.monotonic()
        last = getattr(self, "_last_grasp_target_pub", None)
        period = max(0.1, float(self.get_parameter("grasp_target_refresh_s").value))
        if last is not None and now - last < period:
            return
        self._last_grasp_target_pub = now
        self._vision_refresh_seq = getattr(self, "_vision_refresh_seq", 0) + 1
        self._publish_vision_request(target, self._vision_refresh_seq)

    def _find_failed(self, reason: str) -> None:
        """Schedule bounded active search or fail the action.

        Args:
            reason: Acquisition failure description.
        """
        if (self.get_parameter("scan_enabled").value and self._scans_done
                < int(self.get_parameter("scan_max_sweeps").value)):
            self._begin_scan(reason)
        else:
            self._action_failed(reason)

    def _begin_scan(self, reason: str = "object acquisition timeout") -> None:
        """Begin one measured recovery sweep without ending the find attempt.

        Args:
            reason: Failure that triggered the active-search recovery.
        """
        self._scans_done += 1
        self._scan_count_total = getattr(self, "_scan_count_total", 0) + 1
        self._scan_direction *= -1
        speed = max(float(self.get_parameter("scan_min_speed_radps").value),
                    abs(float(self.get_parameter("scan_speed_radps").value)), 0.001)
        arc = max(0.0, math.radians(float(self.get_parameter("scan_arc_deg").value)))
        self._scan_until = time.monotonic() + arc / speed
        self._vision_refresh_seq = getattr(self, "_vision_refresh_seq", 0) + 1
        self._last_target_pub = 0.0
        self._republish_vision_target()
        self._state = self.SCAN
        self._set_owner("brain")
        self._publish_status("scanning", event="recovery", recovery_kind="scan",
                             recovery_reason=reason, scan_count=self._scan_count_total,
                             scan_duration_s=arc / speed, retry_index=getattr(
                                 self, "_retry_count", 0))

    def _check_scan(self) -> None:
        """Stop when the sweep ends or the requested target is acquired."""
        event = self._last_vision_event
        if event and event.get("event") == "failed":
            reason = str(event.get("reason") or "failed")
            detail = str(event.get("detail") or "")
            self._abort_task(f"vision failed: {reason}" + (f": {detail}" if detail else ""))
            return
        if event and event.get("event") == "found":
            self._found_context = dict(event)
            self._zero_cmd_vel()
            self._advance()
            return
        if self._scan_until is not None and time.monotonic() < self._scan_until:
            speed = abs(float(self.get_parameter("scan_speed_radps").value))
            twist = Twist()
            twist.angular.z = self._scan_direction * max(
                float(self.get_parameter("scan_min_speed_radps").value), speed, 0.001)
            self._cmd_vel_pub.publish(twist)
            return
        self._zero_cmd_vel()
        self._set_owner("none")
        self._end_action("failed", "scan sweep ended without target acquisition")
        self._state = self.EXECUTING

    def _check_grasp(self) -> None:
        """Complete only on grasped, returning before deadline evaluation."""
        self._check_manip("grasped")
        if self._state == self.WAIT_GRASP:
            self._refresh_grasp_target()

    def _check_misc(self) -> None:
        """Require explicit confirmation for home and release."""
        command = self._plan[self._plan_idx]["action"]
        self._check_manip({"home": "homed", "release": "released"}[command])

    def _check_manip(self, expected: str) -> None:
        """Check the exact expected completion event.

        Args:
            expected: Event name matching the currently dispatched action.
        """
        event = self._last_manip_event
        if event and event.get("event") == expected:
            self._advance()
            return
        if event and event.get("event") == "failed":
            self._action_failed(f"manipulation failed: {event.get('reason', '?')}")
        elif self._timed_out():
            self._action_failed("manipulation timeout")

    def _timed_out(self) -> bool:
        """Return whether the active monotonic deadline has expired."""
        return self._deadline is not None and time.monotonic() >= self._deadline

    def _advance(self) -> None:
        """Finish one action and revoke its velocity ownership."""
        handing_to_grasp = (self._plan_idx + 1 < len(self._plan)
                            and self._plan[self._plan_idx]["action"] == "find"
                            and self._plan[self._plan_idx + 1]["action"] == "grasp")
        if not handing_to_grasp:
            self._cancel_vision_request()
        self._end_action("succeeded")
        self._set_owner("none")
        self._plan_idx += 1
        self._state = self.EXECUTING
        self._deadline = None
        self._nav_result = None
        self._nav_goal_handle = None
        self._nav_resume_at = None

    def _action_failed(self, reason: str) -> None:
        """Cancel the attempt before retrying or terminating.

        Args:
            reason: Failure description.
        """
        self._end_action("failed", reason)
        self._cancel_vision_request()
        self._cancel_navigation()
        self._set_owner("none")
        if self._state in (self.WAIT_GRASP, self.WAIT_MISC):
            self._send_manip("stop")
        if self._retries_left > 0:
            self._retries_left -= 1
            self._retry_count = getattr(self, "_retry_count", 0) + 1
            navigation = (self._plan_idx < len(self._plan)
                          and self._plan[self._plan_idx]["action"] == "navigate")
            delay = max(0.0, float(self.get_parameter("nav_retry_delay_s").value)) if (
                navigation) else 0.0
            self._publish_status(f"retrying: {reason}", event="recovery",
                                 recovery_kind="retry", recovery_reason=reason,
                                 retry_index=self._retry_count,
                                 retry_delay_s=delay,
                                 scan_count=getattr(self, "_scan_count_total", 0))
            if navigation:
                self._nav_resume_at = time.monotonic() + delay
                self._deadline = None
                self._state = self.NAV_RETRY_WAIT
            else:
                self._state = self.EXECUTING
            self._nav_result = None
        else:
            self._abort_task(reason)

    def _abort_task(self, reason: str) -> None:
        """Publish a terminal failure and drain the FIFO normally.

        Args:
            reason: Failure description.
        """
        self._end_action("failed", reason)
        self._stop_everything()
        self._state = self.FAILED
        self._publish_status(reason, event="mission_finished", result="failed", success=False,
                             error_reason=reason, duration_s=self._mission_duration(),
                             physical_contact_verified=False)
        self._state = self.IDLE
        self._finish_mission()

    def _begin_action(self, kind: str, target: str) -> None:
        """Record an immutable attempt identity before issuing any side effect.

        Args:
            kind: Exact primitive action name.
            target: Grounded target, or an empty string for targetless actions.
        """
        self._active_action = {
            "action": kind, "target": target, "step": self._plan_idx,
            "attempt": self._attempt, "action_id": self._action_id,
            "started_at": time.monotonic(), "started_wall_time": time.time(),
        }
        self._publish_status(f"dispatch {kind} {target}", event="action_started",
                             action=kind, target=target, attempt=self._attempt,
                             duration_s=0.0, result=None, error_reason=None,
                             started_wall_time=self._active_action["started_wall_time"])

    def _end_action(self, result: str, reason: str | None = None) -> None:
        """Emit one terminal event per attempt with exact measured duration.

        Args:
            result: succeeded, failed, or canceled at the orchestration layer.
            reason: Failure or cancellation explanation; None on success.
        """
        active = getattr(self, "_active_action", None)
        if active is None:
            return
        self._active_action = None
        duration = max(0.0, time.monotonic() - active["started_at"])
        fields = {key: value for key, value in active.items() if key != "started_at"}
        self._publish_status(f"{active['action']} {result}", event="action_finished",
                             **fields, duration_s=duration, success=result == "succeeded",
                             result=result, error_reason=reason,
                             physical_contact_verified=False,
                             completion_evidence="controller_or_skill_result")

    def _mission_duration(self) -> float:
        """Return measured elapsed mission time, excluding time in the FIFO.

        Returns:
            Duration in seconds, or zero for a legacy uninitialized fixture.
        """
        started = getattr(self, "_mission_started_at", None)
        return max(0.0, time.monotonic() - started) if started is not None else 0.0

    def _cancel_navigation(self) -> None:
        """Invalidate callbacks and cancel every accepted navigation handle."""
        self._nav_generation += 1
        self._nav_token = None
        self._pending_nav_waypoint = None
        self._nav_discovery_deadline = None
        self._nav_resume_at = None
        for handle in list(self._nav_handles.values()):
            try:
                handle.cancel_goal_async()
            except (RuntimeError, ValueError) as exc:
                self.get_logger().warning(format_line(
                    "BRAIN", f"Navigation cancellation failed: {sanitize_text(exc)}", "warning"))
        self._nav_handles.clear()
        self._nav_goal_handle = None
        self._nav_result = None

    def _stop_everything(self) -> None:
        """Revoke motion before canceling high-level and actuator commands."""
        self._cancel_vision_request()
        self._set_owner("none")
        self._cancel_navigation()
        self._scan_until = None
        self._zero_cmd_vel()
        self._send_manip("stop")

    def _send_manip(self, command: str) -> None:
        """Publish a correlated manipulation command and acquisition context.

        Args:
            command: grasp, release, home, or stop.
        """
        payload = {"mission_id": self._mission_id, "action_id": self._action_id,
                   "command": command, "target": dict(self._found_context)}
        self._manip_req_pub.publish(String(data=json.dumps(payload)))

    def _beep(self, duration_ms: int) -> None:
        """Publish a bounded buzzer duration.

        Args:
            duration_ms: Beep length in milliseconds.
        """
        if self.get_parameter("sound_feedback").value:
            self._beep_pub.publish(UInt16(data=max(0, min(65535, int(duration_ms)))))

    def _queue_sound(self, event: str) -> None:
        """Schedule a recognizable buzzer pattern without sleeping ROS callbacks.

        Args:
            event: mission_started, navigate, find, grasp, failed, or canceled.
        """
        if not self.get_parameter("sound_feedback").value:
            return
        queue = getattr(self, "_sound_queue", None)
        if queue is None:
            queue = self._sound_queue = deque(maxlen=int(self.get_parameter(
                "sound_queue_size").value))
        short = int(self.get_parameter("sound_short_ms").value)
        long = int(self.get_parameter("sound_long_ms").value)
        patterns = {"mission_started": [short], "navigate": [short, short],
                    "find": [short, short, short], "grasp": [long], "failed": [long, short]}
        if event in ("failed", "canceled"):
            queue.clear()
        queue.extend(patterns.get(event, []))
        self._tick_sound()

    @synchronized
    def _tick_sound(self) -> None:
        """Publish one due tone; robot control and heartbeats remain independent."""
        queue = getattr(self, "_sound_queue", None)
        if not queue:
            return
        if not self.get_parameter("sound_feedback").value:
            queue.clear()
            return
        now = time.monotonic()
        if now < getattr(self, "_sound_next_at", 0.0):
            return
        duration = queue.popleft()
        self._beep(duration)
        self._sound_next_at = now + duration / 1000.0 + max(
            0.0, float(self.get_parameter("sound_gap_s").value))

    def _zero_cmd_vel(self) -> None:
        """Send a zero velocity on the brain's gated source channel."""
        self._cmd_vel_pub.publish(Twist())

    def _speak(self, phrase: str) -> None:
        """Publish speech and optionally launch local TTS.

        Args:
            phrase: Short text to announce.
        """
        self._speech_pub.publish(String(data=phrase))
        executable = shutil.which("espeak") if self.get_parameter("tts_enabled").value else None
        if executable is None:
            self._beep(200)
            return
        if not self._tts_lock.acquire(blocking=False):
            self._beep(120)
            return
        threading.Thread(target=self._run_tts, args=(
            executable, str(self.get_parameter("tts_voice").value), phrase,
            max(0.1, float(self.get_parameter("tts_timeout_s").value))), daemon=True).start()

    def _run_tts(self, executable: str, voice: str, phrase: str, timeout_s: float) -> None:
        """Bound a single local speech process without blocking the FSM.

        Args:
            executable: Resolved espeak executable.
            voice: Installed voice identifier.
            phrase: Phrase to speak.
            timeout_s: Maximum process runtime in seconds.
        """
        try:
            subprocess.run([executable, "-v", voice, "--", phrase],
                           stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, timeout=timeout_s, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            self.get_logger().warning(format_line(
                "BRAIN", f"Speech unavailable: {sanitize_text(exc)}", "warning"))
        finally:
            self._tts_lock.release()

    def _send_nav_goal(self, waypoint_name: str) -> bool:
        """Submit a goal without blocking the executor for server discovery.

        Args:
            waypoint_name: Validated named waypoint.

        Returns:
            Whether a goal request was submitted.
        """
        pose = (getattr(self, "_mission_start_pose", None) if waypoint_name.lower() == MISSION_START
                else self._waypoints.get(waypoint_name.lower()))
        if self._nav_client is None or pose is None:
            return False
        if not self._nav_client.server_is_ready():
            self._pending_nav_waypoint = waypoint_name
            self._nav_discovery_deadline = time.monotonic() + max(
                0.1, float(self.get_parameter("nav_server_wait_s").value))
            self._nav_result = None
            return True
        self._pending_nav_waypoint = None
        self._check_amcl_convergence()
        self._nav_generation += 1
        token = (self._generation, self._nav_generation)
        self._nav_token = token
        goal = NavigateThroughPoses.Goal()
        stamped = PoseStamped()
        stamped.header.frame_id = self._map_frame
        stamped.header.stamp = self.get_clock().now().to_msg()
        stamped.pose = self._pose_from_waypoint(pose)
        goal.poses = [stamped]
        self._nav_result = None
        future = self._nav_client.send_goal_async(goal, feedback_callback=self._on_nav_feedback)
        future.add_done_callback(lambda result: self._on_goal_response(result, token))
        return True

    @staticmethod
    def _pose_from_waypoint(pose: dict[str, float]) -> Pose:
        """Convert a planar waypoint to a quaternion pose.

        Args:
            pose: x, y, and yaw in metres/radians.

        Returns:
            Geometry pose with a unit yaw quaternion.
        """
        msg = Pose()
        msg.position.x, msg.position.y = pose["x"], pose["y"]
        msg.orientation.z = math.sin(pose["yaw"] / 2.0)
        msg.orientation.w = math.cos(pose["yaw"] / 2.0)
        return msg

    def _on_nav_feedback(self, feedback: Any) -> None:
        """Log feedback without assuming optional Nav2 fields.

        Args:
            feedback: Nav2 feedback wrapper.
        """
        distance = getattr(feedback.feedback, "distance_remaining", None)
        if isinstance(distance, (int, float)) and math.isfinite(distance):
            self.get_logger().debug(format_line(
                "BRAIN", f"Navigation: {distance:.2f} m remaining", "debug"))

    @synchronized
    def _on_goal_response(self, future: Any, token: tuple[int, int] | None = None) -> None:
        """Cancel late accepted goals instead of installing stale handles.

        Args:
            future: Goal response future.
            token: Mission generation and navigation attempt.
        """
        try:
            handle = future.result()
        except (RuntimeError, ValueError, TypeError) as exc:
            if token == self._nav_token:
                self._nav_result = GoalStatus.STATUS_ABORTED
            self.get_logger().warning(format_line(
                "BRAIN", f"Navigation goal failed: {sanitize_text(exc)}", "warning"))
            return
        if handle is None or not handle.accepted:
            if token == self._nav_token:
                self._nav_result = GoalStatus.STATUS_ABORTED
            return
        if token != self._nav_token or self._state != self.WAIT_NAV or self._closing:
            handle.cancel_goal_async()
            return
        self._nav_handles[token] = handle
        self._nav_goal_handle = handle
        handle.get_result_async().add_done_callback(
            lambda result: self._on_nav_result(result, token))

    @synchronized
    def _on_nav_result(self, future: Any, token: tuple[int, int] | None = None) -> None:
        """Ignore results belonging to canceled or replaced attempts.

        Args:
            future: Navigation result future.
            token: Original navigation attempt identity.
        """
        self._nav_handles.pop(token, None)
        if token != self._nav_token or self._state != self.WAIT_NAV:
            return
        try:
            self._nav_result = future.result().status
        except (RuntimeError, ValueError, AttributeError, TypeError):
            self._nav_result = GoalStatus.STATUS_ABORTED

    def _ros_stamp_ns(self) -> int | None:
        """Expose the ROS clock separately from measured wall-clock inference latency.

        Returns:
            ROS timestamp in nanoseconds, or None before a ROS clock is initialized.
        """
        clock = getattr(self, "_clock", None)
        return int(clock.now().nanoseconds) if clock is not None else None

    @synchronized
    def _publish_status(self, detail: str, **overrides: Any) -> None:
        """Publish structured state with frontend correlation identifiers.

        Args:
            detail: Human-readable transition description.
            **overrides: Fields for queue acknowledgements.
        """
        payload = {
            "mission_id": self._mission_id, "action_id": self._action_id,
            "command": self._command, "state": self._state, "step": self._plan_idx,
            "total": len(self._plan), "planner": self._planner_source,
            "source": self._planner_source,
            "attempt": getattr(self, "_attempt", 0),
            "llm_response_ms": getattr(self, "_llm_response_ms", 0.0),
            "planning_latency_ms": getattr(self, "_planning_latency_ms", 0.0),
            "planner_reason": getattr(self, "_planner_reason", "not planned"),
            "benchmark_reset": getattr(self, "_benchmark_reset", False),
            "retry_count": getattr(self, "_retry_count", 0),
            "scan_count": getattr(self, "_scan_count_total", 0),
            "action": (self._plan[self._plan_idx]["action"]
                       if self._plan_idx < len(self._plan) else ""),
            "queue": len(self._mission_queue), "detail": detail, "wall_time": time.time(),
            "monotonic_ns": time.monotonic_ns(),
            "ros_stamp_ns": self._ros_stamp_ns(),
        }
        payload.update(overrides)
        message = json.dumps(payload)
        self._status_pub.publish(String(data=message))
        event = payload.get("event")
        if event == "mission_started":
            self._queue_sound("mission_started")
        elif event == "action_finished" and payload.get("success") is True:
            self._queue_sound(str(payload.get("action", "")))
        elif event == "mission_finished" and payload.get("success") is False:
            self._queue_sound("canceled" if payload.get("result") == "canceled" else "failed")
        # Humble caches logger severity by call site; keep this call fixed at INFO.
        # The formatter still communicates warnings/errors through text and color.
        logger = self.get_logger()
        logger.info(format_status(payload))

    @synchronized
    def destroy_node(self) -> None:
        """Invalidate workers and stop motion before destroying ROS entities."""
        self._closing = True
        self._generation += 1
        try:
            self._end_action("canceled", "planner shutdown")
            self._stop_everything()
        except (RuntimeError, ValueError):
            pass
        super().destroy_node()


def main(args: list[str] | None = None) -> None:
    """Run the Humble multi-threaded executor.

    Args:
        args: Optional ROS arguments.
    """
    rclpy.init(args=args)
    planner = LLMTaskPlanner()
    executor = MultiThreadedExecutor()
    executor.add_node(planner)
    try:
        executor.spin()
    except (ExternalShutdownException, KeyboardInterrupt):
        pass
    finally:
        executor.shutdown()
        planner.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
