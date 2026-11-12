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
"""

import argparse
import json
import sys

import rclpy
from rclpy.node import Node

from std_msgs.msg import String

TERMINAL_STATES = {"IDLE", "DONE", "FAILED"}


class CliFrontend(Node):
    """One-shot command publisher + status follower."""

    def __init__(self, command: str, quiet: bool = False):
        super().__init__("eira_cli")
        self._command = command
        self._quiet = quiet
        self._settled = False
        self._exit_code = 2

        self._status_sub = self.create_subscription(
            String, "eira/status", self._on_status, 10)
        self._command_pub = self.create_publisher(
            String, "eira/command", 10)

    def run(self) -> int:
        """Send the command, follow status, return 0 on DONE / 2 on FAILED."""
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

        while rclpy.ok() and not self._settled:
            rclpy.spin_once(self, timeout_sec=0.5)
        return self._exit_code

    def _on_status(self, msg: String):
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
    parser.add_argument("command", help="task in natural language")
    parser.add_argument(
        "-q", "--quiet", action="store_true",
        help="fire and forget; do not follow /eira/status")
    arguments = parser.parse_args(args)

    rclpy.init()
    frontend = CliFrontend(arguments.command, arguments.quiet)
    try:
        return frontend.run()
    except KeyboardInterrupt:
        return 130
    finally:
        frontend.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    sys.exit(main())
