"""Correlated E-AIRA CLI with a strictly nonexecuting local plan preview.

Author: E-AIRA contributors.
Hardware target: ROSMASTER M3 Pro / Jetson Orin NX, ROS 2 Humble.
"""

import argparse
import json
from pathlib import Path
import sys
import time
from typing import Any
import uuid

from ament_index_python.packages import PackageNotFoundError, get_package_share_directory
import rclpy
from rclpy.node import Node
from std_msgs.msg import String

from eira_brain.console import format_line, format_plan, format_status, sanitize_text
from eira_brain.llm_task_planner import LLMTaskPlanner
from eira_brain.ollama_client import (
    COCO_CLASSES, MISSION_START, TARGET_COLORS, OllamaClient, OllamaError, extract_json,
)
from eira_brain.waypoint_store import load_waypoints


def _default_waypoints_file() -> Path:
    """Locate installed or source waypoint data.

    Returns:
        Candidate waypoint file path.
    """
    try:
        installed = Path(get_package_share_directory("eira_bringup")) / "config/waypoints.yaml"
        if installed.is_file():
            return installed
    except PackageNotFoundError:
        pass
    return Path(__file__).resolve().parents[2] / "eira_bringup/config/waypoints.yaml"


def _print_error(event: str, reason: str, *, json_output: bool = False,
                 color: bool | None = None) -> None:
    """Report an error in the requested human or machine output format.

    Args:
        event: Stable diagnostic name for machine output.
        reason: Human-readable explanation.
        json_output: Print the legacy JSON error envelope when true.
        color: Explicit color selection, or automatic detection when None.
    """
    text = (json.dumps({"event": event, "reason": reason}) if json_output else
            format_line("CLI", reason, "error", color=color))
    print(text, file=sys.stderr, flush=True)


def _print_preview(plan: dict[str, Any], *, json_output: bool = False,
                   color: bool | None = None) -> None:
    """Show a clearly nonexecuting preview without exposing its JSON by default.

    Args:
        plan: Preview envelope containing source, command and validated actions.
        json_output: Print the complete legacy JSON envelope when true.
        color: Explicit color selection, or automatic detection when None.
    """
    if json_output:
        print(json.dumps(plan, indent=2))
        return
    print(format_line("CLI", "Preview only; nothing sent to robot", color=color))
    print(format_line("CLI", f"Command: {sanitize_text(plan['command'])}", color=color))
    planner = "LLM" if plan["source"] == "llm" else "deterministic fallback"
    print(format_line("CLI", f"Planner: {planner}", color=color))
    for index, action in enumerate(plan["actions"], 1):
        label = format_plan([action], color=False)
        print(format_line("PLAN", f"{index}. {label}", color=color))
    if any(action.get("target") == MISSION_START for action in plan["actions"]):
        print(format_line("CLI", "mission_start is the robot pose captured when execution "
                          "starts; this preview does not capture a pose.", color=color))


def list_waypoints(path: Path, *, json_output: bool = False,
                   color: bool | None = None) -> int:
    """Print validated waypoint data as a table or the legacy JSON envelope.

    Args:
        path: Waypoint YAML database.
        json_output: Preserve machine-readable JSON when true.
        color: Explicit color selection, or automatic detection when None.

    Returns:
        Zero on success; one for unreadable/invalid data.
    """
    try:
        data = load_waypoints(path)
    except (OSError, ValueError) as exc:
        _print_error("waypoint_error", str(exc), json_output=json_output, color=color)
        return 1
    if json_output:
        print(json.dumps(data, indent=2))
        return 0
    print(format_line("CLI", f"Waypoints in frame {sanitize_text(data['frame'])}", color=color))
    print(f"{'NAME':<24} {'X (m)':>10} {'Y (m)':>10} {'YAW (rad)':>12}")
    for name, pose in sorted(data["waypoints"].items()):
        print(f"{sanitize_text(name, limit=24):<24} {pose['x']:>10.3f} "
              f"{pose['y']:>10.3f} {pose['yaw']:>12.3f}")
    return 0


def preview_plan(command: str, url: str = "http://localhost:11434", model: str = "phi3",
                 timeout_s: float = 30.0, *, waypoints_file: Path | None = None,
                 object_classes: tuple[str, ...] = COCO_CLASSES) -> dict:
    """Generate a plan locally without initializing ROS or publishing commands.

    Args:
        command: Instruction to preview.
        url: Local Ollama address.
        model: Ollama model tag.
        timeout_s: HTTP request timeout.
        waypoints_file: Named places used by the running planner; source defaults otherwise.
        object_classes: Labels supported by the selected detector model.

    Returns:
        A nonexecuting plan envelope with its planning source.

    Raises:
        ValueError: Neither planner produces a valid plan.
    """
    planner = object.__new__(LLMTaskPlanner)
    try:
        planner._waypoints = load_waypoints(waypoints_file or _default_waypoints_file())["waypoints"]
    except (OSError, ValueError) as exc:
        raise ValueError(f"cannot load preview waypoints: {exc}") from exc
    planner._object_classes = object_classes
    planner._target_colors = TARGET_COLORS
    places = tuple(name for name in planner._waypoints if name != MISSION_START) + (MISSION_START,)
    source, plan = "llm", None
    reason = "no valid plan"
    try:
        raw = OllamaClient(url, model, timeout_s).generate_plan(
            command, waypoints=places, object_classes=object_classes, colors=TARGET_COLORS)
        plan, reason = planner._validate_command_plan(command, extract_json(raw), places)
    except OllamaError:
        pass
    if plan is None:
        source = "fallback"
        plan, reason = planner._validate_command_plan(command, planner._fallback_plan(command), places)
    if plan is None:
        raise ValueError(f"no valid plan: {reason}")
    return {"source": source, "command": command, "actions": plan, "execute": False}


class CliFrontend(Node):
    """Follow exactly one requested mission.

    Args:
        command: Natural-language instruction.
        quiet: Return after sending when true.
        plan_only: Return a local preview without publishing when true.
        timeout_s: Total wall-clock mission wait budget.
        json_output: Preserve original machine-readable status messages when true.
        color: Explicit color selection, or automatic detection when None.
    """

    def __init__(self, command: str, quiet: bool = False, plan_only: bool = False,
                 timeout_s: float = 1800.0, *, json_output: bool = False,
                 color: bool | None = None) -> None:
        """Initialize the one-shot ROS frontend."""
        super().__init__("eira_cli")
        self._command, self._quiet, self._plan_only = command, quiet, plan_only
        self._timeout_s = max(0.1, timeout_s)
        self._json_output, self._color = json_output, color
        self._last_output: str | None = None
        self._mission_id = uuid.uuid4().hex
        self._settled, self._exit_code = False, 2
        self._command_pub = self.create_publisher(String, "eira/command", 10)
        self.create_subscription(String, "eira/status", self._on_status, 10)

    def run(self) -> int:
        """Publish once and follow the matching mission to completion.

        Returns:
            Zero for success; two for failure or missing responses.
        """
        if self._plan_only:
            _print_preview(preview_plan(self._command),
                           json_output=getattr(self, "_json_output", False),
                           color=getattr(self, "_color", None))
            return 0
        discovery_deadline = time.monotonic() + min(5.0, self._timeout_s)
        while (self._command_pub.get_subscription_count() == 0
               and time.monotonic() < discovery_deadline and rclpy.ok()):
            rclpy.spin_once(self, timeout_sec=0.1)
        if self._command_pub.get_subscription_count() == 0:
            _print_error("planner_unavailable", "No planner subscription discovered",
                         json_output=self._json_output, color=self._color)
            return 2
        self._command_pub.publish(String(data=json.dumps({
            "command": self._command, "mission_id": self._mission_id})))
        if self._quiet:
            rclpy.spin_once(self, timeout_sec=0.1)
            return 0
        if not self._json_output:
            print(format_line("CLI", f"Command sent: {sanitize_text(self._command)}",
                              color=self._color), flush=True)
        deadline = time.monotonic() + self._timeout_s
        while rclpy.ok() and not self._settled and time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=min(0.5, max(0.0, deadline - time.monotonic())))
        if not self._settled:
            _print_error("mission_response_timeout",
                         "Timed out waiting; the mission may still be active. "
                         "Send 'stop' to cancel it.",
                         json_output=self._json_output, color=self._color)
        return self._exit_code

    def _on_status(self, msg: String) -> None:
        """Ignore unrelated terminal statuses.

        Args:
            msg: Brain JSON status event.
        """
        try:
            status = json.loads(msg.data)
        except json.JSONDecodeError:
            return
        if not isinstance(status, dict) or status.get("mission_id") != self._mission_id:
            return
        if getattr(self, "_json_output", False):
            print(json.dumps(status), flush=True)
        else:
            line = format_status(status, component="CLI", color=getattr(self, "_color", None))
            terminal = status.get("state") in ("DONE", "FAILED") or (
                "rejected" in str(status.get("detail", "")))
            if line != getattr(self, "_last_output", None) or terminal:
                print(line, flush=True)
                self._last_output = line
        if "rejected" in str(status.get("detail", "")):
            self._settled, self._exit_code = True, 2
        elif status.get("state") in ("DONE", "FAILED"):
            self._settled = True
            self._exit_code = 0 if status["state"] == "DONE" else 2


def main(args: list[str] | None = None) -> int:
    """Run CLI parsing and optionally a ROS frontend.

    Args:
        args: Optional CLI arguments.

    Returns:
        Process exit code.
    """
    parser = argparse.ArgumentParser(description="Command or preview an E-AIRA mission")
    parser.add_argument("command", nargs="?")
    parser.add_argument("-q", "--quiet", action="store_true")
    parser.add_argument("--plan-only", action="store_true")
    parser.add_argument("--list-waypoints", action="store_true")
    parser.add_argument("--waypoints-file", type=Path,
                        help="waypoint database for --list-waypoints or --plan-only")
    parser.add_argument("--timeout", type=float, default=1800.0)
    parser.add_argument("--ollama-url", default="http://localhost:11434")
    parser.add_argument("--llm-model", default="phi3")
    parser.add_argument("--json", dest="json_output", action="store_true",
                        help="print original machine-readable JSON instead of readable output")
    parser.add_argument("--no-color", action="store_true",
                        help="disable color in readable output")
    options = parser.parse_args(args)
    color = False if options.no_color else None
    if options.list_waypoints:
        return list_waypoints(options.waypoints_file or _default_waypoints_file(),
                              json_output=options.json_output, color=color)
    if not options.command:
        parser.error("command required")
    if options.plan_only:
        try:
            kwargs = {"waypoints_file": options.waypoints_file} if options.waypoints_file else {}
            plan = preview_plan(options.command, options.ollama_url, options.llm_model, **kwargs)
            _print_preview(plan, json_output=options.json_output, color=color)
        except ValueError as exc:
            _print_error("preview_failed", str(exc), json_output=options.json_output, color=color)
            return 2
        return 0
    rclpy.init()
    frontend = CliFrontend(options.command, options.quiet, timeout_s=options.timeout,
                           json_output=options.json_output, color=color)
    try:
        return frontend.run()
    except KeyboardInterrupt:
        _print_error("watch_interrupted", "Stopped watching; send 'stop' to cancel the mission.",
                     json_output=options.json_output, color=color)
        return 130
    finally:
        frontend.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    sys.exit(main())
