#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
eira_cli.py — terminal front-end for the E-AIRA brain.

Publishes a natural-language command on /eira/command (the same interface a
voice node would use) and then echoes /eira/status until the task reaches a
terminal state. Useful for demos, scripted evaluation runs, and for driving
the system from an SSH session on the Jetson.

Examples
--------
    ros2 run eira_brain eira_cli "bring me a cup from the kitchen"
    ros2 run eira_brain eira_cli "stop"
    ros2 run eira_brain eira_cli --list-waypoints
    ros2 run eira_brain eira_cli --plan-only "go to the kitchen and find a cup"
"""

import argparse
import json
import sys
from pathlib import Path

import rclpy
import yaml
from rclpy.node import Node

from std_msgs.msg import String

TERMINAL_STATES = {"IDLE", "DONE", "FAILED"}


def _default_waypoints_file() -> Path:
    """Locate waypoints.yaml: installed share first, source tree fallback."""
    try:
        from ament_index_python.packages import get_package_share_directory
        installed = (Path(get_package_share_directory("eira_bringup"))
                     / "config" / "waypoints.yaml")
        if installed.is_file():
            return installed
    except Exception:  # not launched from an overlay — use the source tree
        pass
    return (Path(__file__).resolve().parents[2]
            / "eira_bringup" / "config" / "waypoints.yaml")


def list_waypoints(path: Path) -> int:
    """Pretty-print the waypoint database; exit 1 if unreadable."""
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except FileNotFoundError:
        print(f"eira_cli: waypoints file not found: {path}", file=sys.stderr)
        return 1
    except yaml.YAMLError as exc:
        print(f"eira_cli: cannot parse {path}: {exc}", file=sys.stderr)
        return 1

    frame = data.get("frame", "?")
    points = data.get("waypoints") or {}
    print(f"Waypoint database — frame: {frame}  ({len(points)} named poses)")
    print(f"  source: {path}")
    if not points:
        print("  (empty — record poses with `ros2 run eira_brain "
              "waypoint_recorder`)")
        return 0
    width = max(len(name) for name in points)
    for name, pose in points.items():
        if not isinstance(pose, dict):
            continue
        note = f"  — {pose['description']}" if pose.get("description") else ""
        print(f"  {name:<{width}}  x={float(pose.get('x', 0.0)):>7.3f}  "
              f"y={float(pose.get('y', 0.0)):>7.3f}  "
              f"yaw={float(pose.get('yaw', 0.0)):>7.3f}{note}")
    return 0


class CliFrontend(Node):
    """One-shot command publisher + status/plan follower."""

    def __init__(self, command: str, quiet: bool = False,
                 plan_only: bool = False):
        super().__init__("eira_cli")
        self._command = command
        self._quiet = quiet
        self._plan_only = plan_only
        self._settled = False
        self._exit_code = 2

        self._status_sub = self.create_subscription(
            String, "eira/status", self._on_status, 10)
        self._plan_sub = self.create_subscription(
            String, "eira/plan", self._on_plan, 10)
        self._command_pub = self.create_publisher(
            String, "eira/command", 10)

    def run(self) -> int:
        """Send the command, follow status (or plan), return the exit code."""
        # Give the publisher a moment to match subscriptions (QoS handshake).
        for _ in range(10):
            if self._command_pub.get_subscription_count() > 0:
                break
            rclpy.spin_once(self, timeout_sec=0.1)

        message = String()
        message.data = self._command
        self._command_pub.publish(message)

        if self._quiet:
            return 0

        # Worst case: LLM timeout (20 s) + fallback planning + queue drain.
        deadline = 45.0
        waited = 0.0
        while rclpy.ok() and not self._settled and waited < deadline:
            rclpy.spin_once(self, timeout_sec=0.5)
            waited += 0.5
        if not self._settled:
            print(f"eira_cli: no terminal status within {deadline:.0f} s",
                  file=sys.stderr)
        return self._exit_code

    def _on_plan(self, msg: String):
        if not self._plan_only:
            return
        try:
            plan = json.loads(msg.data)
        except json.JSONDecodeError:
            print(msg.data)
        else:
            print("— plan " + "─" * 50)
            print(f"  planner: {plan.get('source', '?')}   "
                  f"command: {plan.get('command', '?')}")
            for idx, step in enumerate(plan.get("actions", []), start=1):
                target = f" → {step['target']}" if step.get("target") else ""
                print(f"   {idx}. {step.get('action', '?')}{target}")
            print("  " + "─" * 58)
        self._settled = True
        self._exit_code = 0

    def _on_status(self, msg: String):
        if self._plan_only:
            return
        try:
            status = json.loads(msg.data)
        except json.JSONDecodeError:
            print(msg.data)
            return
        print(f"[{status.get('state', '?'):>9}] "
              f"step {status.get('step', '?')}/{status.get('total', '?')} "
              f"— {status.get('detail', '')}")
        if status.get("state") in TERMINAL_STATES and \
                "rejected" not in status.get("detail", "").lower():
            self._exit_code = 0 if status.get("state") != "FAILED" else 2
            self._settled = True


def main(args=None):
    parser = argparse.ArgumentParser(
        description="Send a natural-language task to the E-AIRA brain.")
    parser.add_argument("command", nargs="?", default=None,
                        help="task in natural language")
    parser.add_argument(
        "-q", "--quiet", action="store_true",
        help="fire and forget; do not follow /eira/status")
    parser.add_argument(
        "--plan-only", action="store_true",
        help="print the generated plan and exit (no execution)")
    parser.add_argument(
        "--list-waypoints", action="store_true",
        help="print the waypoint database and exit (no ROS traffic)")
    parser.add_argument(
        "--waypoints-file", type=Path, default=None,
        help="waypoints.yaml to read with --list-waypoints "
             "(default: installed share, then source tree)")
    arguments = parser.parse_args(args)

    if arguments.list_waypoints:
        return list_waypoints(
            arguments.waypoints_file or _default_waypoints_file())
    if arguments.command is None:
        parser.error("a command is required unless --list-waypoints is given")

    rclpy.init()
    frontend = CliFrontend(arguments.command, arguments.quiet,
                           arguments.plan_only)
    try:
        return frontend.run()
    except KeyboardInterrupt:
        return 130
    finally:
        frontend.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    sys.exit(main())
