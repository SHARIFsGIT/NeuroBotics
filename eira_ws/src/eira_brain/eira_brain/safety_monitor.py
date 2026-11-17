"""Publish a fail-closed heartbeat interlock for the velocity gate.

Author: E-AIRA maintainers.
Hardware target: Yahboom ROSMASTER M3 Pro / Jetson Orin NX, ROS 2 Humble.
"""

import json
import time

import rclpy
from geometry_msgs.msg import Twist
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile
from std_msgs.msg import Bool, Empty, String

from eira_brain.console import format_line


class SafetyMonitor(Node):
    """Observe Brain liveness independently of the last command's age."""

    def __init__(self) -> None:
        """Declare watchdog timing and create the interlock interfaces.

        Raises:
            ValueError: If a timeout or publishing rate is invalid.
        """
        super().__init__('safety_monitor')
        for name, default in {
                'heartbeat_timeout_s': 5.0, 'startup_grace_s': 10.0,
                'motion_window_s': 5.0, 'intervene_rate_hz': 20.0}.items():
            self.declare_parameter(name, default)
        self._timeout = float(self.get_parameter('heartbeat_timeout_s').value)
        self._grace = float(self.get_parameter('startup_grace_s').value)
        self._motion_window = max(self._timeout,
                                  float(self.get_parameter('motion_window_s').value))
        rate = float(self.get_parameter('intervene_rate_hz').value)
        if self._timeout <= 0 or self._grace < 0 or rate <= 0:
            raise ValueError('invalid watchdog timeout, grace, or rate')
        self._last_heartbeat: float | None = None
        self._last_motion: float | None = None
        self._started_at = time.monotonic()
        self._intervening = False
        self._context: dict[str, object] = {'mission_id': None, 'action_id': None}
        self.create_subscription(Empty, '/eira/heartbeat', self._on_heartbeat, 10)
        self.create_subscription(Twist, '/cmd_vel', self._on_cmd_vel, 10)
        self.create_subscription(String, '/eira/motion_owner', self._on_owner, 10)
        self._cmd_vel_pub = self.create_publisher(Twist, '/cmd_vel', 1)
        self._event_pub = self.create_publisher(String, '/eira/safety/event', 10)
        qos = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self._stop_pub = self.create_publisher(Bool, '/eira/safety/stop', qos)
        self.create_timer(1.0 / rate, self._check)

    def _on_owner(self, message: String) -> None:
        """Cache mission identifiers for correlated watchdog events."""
        try:
            data = json.loads(message.data)
            if isinstance(data, dict):
                self._context = {k: data.get(k) for k in ('mission_id', 'action_id')}
        except (ValueError, TypeError):
            self.get_logger().warning(format_line(
                'SAFETY', 'Ignored invalid motion ownership event', 'warning'))

    def _on_heartbeat(self, _message: Empty) -> None:
        """Record a liveness update using monotonic time."""
        self._last_heartbeat = time.monotonic()

    def _on_cmd_vel(self, message: Twist) -> None:
        """Record motion for diagnostics without using it to suppress intervention."""
        if any(abs(x) > 1e-4 for x in (message.linear.x, message.linear.y,
                                       message.angular.z)):
            self._last_motion = time.monotonic()

    def _check(self) -> None:
        """Refresh the interlock; a held last velocity is also covered."""
        now = time.monotonic()
        stale = (now - self._started_at >= self._grace and (
            self._last_heartbeat is None or now - self._last_heartbeat > self._timeout))
        self._stop_pub.publish(Bool(data=stale))
        if stale:
            self._cmd_vel_pub.publish(Twist())
        if stale != self._intervening:
            self._intervening = stale
            self._emit('brain_heartbeat_lost' if stale else 'heartbeat_restored')

    def _emit(self, event: str) -> None:
        """Publish a structured watchdog transition.

        Args:
            event: Machine-readable transition name.
        """
        message = String()
        message.data = json.dumps({'event': event, **self._context,
                                   'wall_time': time.time()})
        self._event_pub.publish(message)
        description = ('Brain heartbeat lost; motion is blocked' if event == 'brain_heartbeat_lost'
                       else 'Brain heartbeat restored; waiting for a new mission')
        self.get_logger().info(format_line(
            'SAFETY', description, 'warning' if event == 'brain_heartbeat_lost' else 'success'))


def main(args: list[str] | None = None) -> None:
    """Run the independent watchdog until ROS shuts down."""
    rclpy.init(args=args)
    node = SafetyMonitor()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
