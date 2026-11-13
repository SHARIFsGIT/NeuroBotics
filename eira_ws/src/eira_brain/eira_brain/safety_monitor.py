#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
safety_monitor.py — E-AIRA watchdog: stop the base if the brain dies.

Rationale
---------
The brain orchestrates every motion channel (Nav2 goals, the grasp
alignment stage, and its own active-scan rotations). If that process
crashes mid-motion, whatever velocity command was last published keeps
being executed by the base controller — a classic single-point-of-failure
in LLM-driven robots. This node closes that gap:

* the brain publishes a 2 Hz heartbeat on ``/eira/heartbeat``;
* this watchdog listens to it **and** to ``cmd_vel`` (to know whether the
  base is actually being commanded to move);
* when the heartbeat goes stale while motion commands are still flowing
  (or were flowing moments ago), the watchdog publishes zero-velocity
  Twists on ``cmd_vel`` at 5 Hz until the heartbeat returns, and emits a
  JSON event on ``/eira/safety/event`` for the evaluation log.

Deliberately conservative: it only intervenes on *staleness + motion*,
never on any other heuristic, and it stands down the moment the heartbeat
resumes.

Topic contract
--------------
  subscribe  /eira/heartbeat   std_msgs/Empty      (brain liveness, 2 Hz)
  subscribe  /cmd_vel          geometry_msgs/Twist (motion observation)
  publish    /cmd_vel          geometry_msgs/Twist (zeros, intervention only)
  publish    /eira/safety/event std_msgs/String    (JSON events)
"""

import json
import time

import rclpy
from geometry_msgs.msg import Twist
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from std_msgs.msg import Empty, String

_MOTION_EPS = 1e-4          # below this a Twist counts as "stopped"


class SafetyMonitor(Node):
    """Heartbeat watchdog with motion-gated zero-velocity intervention."""

    def __init__(self):
        super().__init__("safety_monitor")

        self.declare_parameter("heartbeat_timeout_s", 5.0)
        self.declare_parameter("startup_grace_s", 10.0)
        self.declare_parameter("motion_window_s", 2.0)
        self.declare_parameter("intervene_rate_hz", 5.0)

        self._last_heartbeat = None          # monotonic, None until first
        self._last_motion = None             # monotonic of last non-zero cmd
        self._intervening = False
        self._started_at = time.monotonic()

        self.create_subscription(
            Empty, "/eira/heartbeat", self._on_heartbeat, 10)
        self.create_subscription(
            Twist, "/cmd_vel", self._on_cmd_vel, 10)

        self._cmd_vel_pub = self.create_publisher(Twist, "/cmd_vel", 10)
        self._event_pub = self.create_publisher(
            String, "/eira/safety/event", 10)

        rate = float(self.get_parameter("intervene_rate_hz").value)
        self.create_timer(1.0 / max(rate, 0.5), self._check)

        self.get_logger().info(
            "safety_monitor up: watching /eira/heartbeat "
            f"(stale after {self.get_parameter('heartbeat_timeout_s').value:.0f} s)"
            " + /cmd_vel activity")

    # ========================================================
    # CALLBACKS
    # ========================================================

    def _on_heartbeat(self, _msg: Empty):
        now = time.monotonic()
        if self._intervening:
            self._intervening = False
            self._emit("heartbeat_restored",
                       detail="brain heartbeat returned; watchdog standing down")
            self.get_logger().info("brain heartbeat restored — standing down")
        self._last_heartbeat = now

    def _on_cmd_vel(self, msg: Twist):
        # Only *motion* counts; zero Twists (stop commands) do not.
        if (abs(msg.linear.x) > _MOTION_EPS
                or abs(msg.linear.y) > _MOTION_EPS
                or abs(msg.angular.z) > _MOTION_EPS):
            self._last_motion = time.monotonic()

    # ========================================================
    # WATCHDOG TICK (5 Hz)
    # ========================================================

    def _check(self):
        now = time.monotonic()
        timeout = float(self.get_parameter("heartbeat_timeout_s").value)
        grace = float(self.get_parameter("startup_grace_s").value)
        window = float(self.get_parameter("motion_window_s").value)

        # During startup grace (brain may simply not be launched yet) we
        # only watch, never intervene.
        if now - self._started_at < grace:
            return

        heartbeat_stale = (
            self._last_heartbeat is None
            or now - self._last_heartbeat > timeout)
        motion_recent = (self._last_motion is not None
                         and now - self._last_motion <= window)

        if heartbeat_stale and motion_recent:
            if not self._intervening:
                self._intervening = True
                age = ("never" if self._last_heartbeat is None
                       else f"{now - self._last_heartbeat:.1f} s ago")
                self._emit(
                    "brain_heartbeat_lost",
                    detail=f"last heartbeat {age}; zeroing cmd_vel")
                self.get_logger().error(
                    "BRAIN HEARTBEAT LOST — publishing zero velocity")
            # Keep the base pinned while the condition holds.
            self._cmd_vel_pub.publish(Twist())
        elif self._intervening and not heartbeat_stale:
            self._intervening = False
            self._emit("heartbeat_restored")
            self.get_logger().info("brain heartbeat restored — standing down")

    # ========================================================
    # EVENTS
    # ========================================================

    def _emit(self, event: str, **fields):
        message = String()
        payload = {"event": event, "wall_time": time.time()}
        payload.update(fields)
        message.data = json.dumps(payload)
        self._event_pub.publish(message)


def main(args=None):
    rclpy.init(args=args)
    node = SafetyMonitor()
    try:
        rclpy.spin(node)
    except (ExternalShutdownException, KeyboardInterrupt):
        pass  # SIGTERM/Ctrl-C — context is already shutting down
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
