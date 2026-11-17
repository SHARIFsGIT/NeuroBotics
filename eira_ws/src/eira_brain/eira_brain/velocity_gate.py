"""Arbitrate base commands with fail-closed leases.

Author: E-AIRA maintainers.
Hardware target: Yahboom ROSMASTER M3 Pro, Jetson Orin NX, ROS 2 Humble.
"""

import json
import math
import time
from dataclasses import dataclass, field
from typing import Callable

import rclpy
from geometry_msgs.msg import Twist
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rcl_interfaces.msg import SetParametersResult
from std_msgs.msg import Bool, Empty, String

from eira_brain.ollama_client import is_stop_command
from eira_brain.console import format_line, sanitize_text

SOURCES = ('brain', 'arm', 'nav', 'teleop', 'exercise')


@dataclass
class GatePolicy:
    """Pure arbitration policy; all timestamps use a monotonic clock.

    Args:
        command_timeout: Maximum age of an input velocity in seconds.
        heartbeat_timeout: Maximum age of the Brain heartbeat in seconds.
        require_heartbeat: Whether motion requires a live Brain.
        require_edge: Whether a recent clear edge observation is required.
        edge_timeout: Maximum age of an edge observation in seconds.
    """

    command_timeout: float = 0.5
    heartbeat_timeout: float = 5.0
    require_heartbeat: bool = True
    require_edge: bool = False
    edge_timeout: float = 1.0
    owner: str = 'none'
    owner_since: float = 0.0
    heartbeat: float | None = None
    edge_stamp: float | None = None
    edge_blocked: bool = True
    safety_stop: bool = False
    commands: dict[str, tuple[float, tuple[float, float, float]]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Reject nonfinite leases that could silently disable expiration.

        Raises:
            ValueError: If any timeout is nonpositive or nonfinite.
        """
        limits = (self.command_timeout, self.heartbeat_timeout, self.edge_timeout)
        if not all(math.isfinite(value) and value > 0 for value in limits):
            raise ValueError('gate timeouts must be finite and positive')

    def select(self, owner: str, now: float) -> None:
        """Switch ownership and discard all previous commands.

        Args:
            owner: Allowed source or ``none``.
            now: Monotonic time of the switch.
        Raises:
            ValueError: If the source name is unknown.
        """
        if owner not in (*SOURCES, 'none'):
            raise ValueError(f'unknown motion owner: {owner}')
        self.owner = owner
        self.owner_since = now
        self.commands.clear()

    def put(self, source: str, values: tuple[float, float, float], now: float) -> None:
        """Cache a finite planar velocity for the selected source.

        Args:
            source: Input channel.
            values: Linear x/y and angular z in SI units.
            now: Monotonic receipt time.
        Raises:
            ValueError: If any value is nonfinite or source is unknown.
        """
        if source not in SOURCES or not all(math.isfinite(x) for x in values):
            raise ValueError('invalid velocity input')
        if source == self.owner:
            self.commands[source] = (now, values)

    def output(self, now: float) -> tuple[tuple[float, float, float], str]:
        """Compute an authorized output, revoking ownership on safety loss.

        Args:
            now: Monotonic evaluation time.
        Returns:
            Planar velocity and a machine-readable reason.
        """
        reason = ''
        if self.safety_stop:
            reason = 'safety_stop'
        elif (self.require_heartbeat and self.heartbeat is None
              and now - self.owner_since <= self.heartbeat_timeout):
            # Initial discovery waits at zero; a healthy late subscriber must not
            # permanently revoke the first mission before its first heartbeat.
            return (0.0, 0.0, 0.0), 'heartbeat_pending'
        elif self.require_heartbeat and (
                self.heartbeat is None or now - self.heartbeat > self.heartbeat_timeout):
            reason = 'heartbeat_stale'
        elif self.require_edge and (
                self.edge_stamp is None or now - self.edge_stamp > self.edge_timeout
                or self.edge_blocked):
            reason = 'edge_blocked_or_stale'
        if reason:
            if self.owner != 'none':
                self.select('none', now)
            return (0.0, 0.0, 0.0), reason
        command = self.commands.get(self.owner)
        if command is None or now - command[0] > self.command_timeout:
            return (0.0, 0.0, 0.0), 'command_stale'
        return command[1], 'authorized'


class VelocityGate(Node):
    """Publish the sole final /cmd_vel stream for the managed launch."""

    def __init__(self) -> None:
        """Create the source subscriptions, watchdog inputs, and output timer."""
        super().__init__('velocity_gate')
        defaults = {
            'command_timeout_s': 0.5, 'heartbeat_timeout_s': 5.0,
            'require_heartbeat': True, 'require_edge': False, 'edge_timeout_s': 1.0,
            'output_hz': 20.0, 'max_linear_mps': 0.25, 'max_angular_radps': 1.2,
            'initial_owner': 'none',
        }
        for name, value in defaults.items():
            self.declare_parameter(name, value)
        get = lambda name: self.get_parameter(name).value  # noqa: E731
        self.policy = GatePolicy(
            float(get('command_timeout_s')), float(get('heartbeat_timeout_s')),
            bool(get('require_heartbeat')), bool(get('require_edge')),
            float(get('edge_timeout_s')))
        if min(self.policy.command_timeout, self.policy.heartbeat_timeout,
               self.policy.edge_timeout, float(get('output_hz'))) <= 0:
            raise ValueError('gate timeouts and output rate must be positive')
        for name in ('max_linear_mps', 'max_angular_radps'):
            value = float(get(name))
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f'{name} must be finite and positive')
        self.policy.select(str(get('initial_owner')), time.monotonic())
        self._publisher = self.create_publisher(Twist, '/cmd_vel', 1)
        self._events = self.create_publisher(String, '/eira/motion/event', 10)
        self._last_reason = ''
        self._context: dict[str, object] = {'mission_id': None, 'action_id': None}
        self._revoked_missions: set[str] = set()
        for source in SOURCES:
            self.create_subscription(
                Twist, f'/eira/cmd_vel/{source}', self._input_callback(source), 1)
        self.create_subscription(String, '/eira/motion_owner', self._on_owner, 10)
        self.create_subscription(Empty, '/eira/heartbeat', self._on_heartbeat, 10)
        self.create_subscription(Bool, '/eira/safety/stop', self._on_safety, 10)
        self.create_subscription(String, '/eira/safety/edge', self._on_edge, 10)
        self.create_subscription(String, '/eira/command', self._on_command, 10)
        self.create_timer(1.0 / float(get('output_hz')), self._tick)
        self.add_on_set_parameters_callback(self._on_parameters)

    def _on_parameters(self, parameters: list) -> SetParametersResult:
        """Validate live limits without permitting a disabled timeout or reversed clamp.

        Args:
            parameters: Proposed parameter updates.
        Returns:
            Acceptance result with a diagnostic on invalid settings.
        """
        updates = {parameter.name: parameter.value for parameter in parameters}
        if {'output_hz', 'initial_owner'} & updates.keys():
            return SetParametersResult(successful=False, reason='setting requires restart')
        numeric = ('command_timeout_s', 'heartbeat_timeout_s', 'edge_timeout_s',
                   'max_linear_mps', 'max_angular_radps')
        for name in numeric:
            if name in updates and (not isinstance(updates[name], (int, float)) or
                                    not math.isfinite(updates[name]) or updates[name] <= 0):
                return SetParametersResult(successful=False, reason=f'invalid {name}')
        for name, attr in (('command_timeout_s', 'command_timeout'),
                           ('heartbeat_timeout_s', 'heartbeat_timeout'),
                           ('edge_timeout_s', 'edge_timeout'),
                           ('require_heartbeat', 'require_heartbeat'),
                           ('require_edge', 'require_edge')):
            if name in updates:
                setattr(self.policy, attr, updates[name])
        return SetParametersResult(successful=True)

    def _input_callback(self, source: str) -> Callable[[Twist], None]:
        """Build a callback bound to an input source.

        Args:
            source: Input channel name.
        Returns:
            Callback that caches a Twist or rejects invalid input.
        """
        def receive(message: Twist) -> None:
            """Cache a finite command; invalid commands immediately revoke motion."""
            try:
                self.policy.put(source, (message.linear.x, message.linear.y,
                                         message.angular.z), time.monotonic())
            except ValueError as exc:
                self._revoke('invalid_velocity')
                self.get_logger().error(format_line(
                    'MOTION', f'Invalid {sanitize_text(source)} velocity; stopped: {exc}',
                    'error'))
        return receive

    def _on_owner(self, message: String) -> None:
        """Accept an ownership envelope and clear velocities from the previous stage."""
        try:
            data = json.loads(message.data)
            if not isinstance(data, dict):
                raise ValueError('owner must be a JSON object')
            context = {k: data.get(k) for k in ('mission_id', 'action_id')}
            owner = str(data.get('owner', 'none'))
            mission = str(data.get('mission_id') or '')
            if owner != 'none' and mission in self._revoked_missions:
                return
            if owner != self.policy.owner or context != self._context:
                self.policy.select(owner, time.monotonic())
                self._publisher.publish(Twist())
            self._context = context
        except (ValueError, TypeError) as exc:
            self._revoke('invalid_ownership')
            self.get_logger().warning(format_line(
                'MOTION', f'Invalid motion ownership request; stopped: {exc}', 'warning'))

    def _on_heartbeat(self, _message: Empty) -> None:
        """Record Brain liveness without automatically restoring an old lease."""
        self.policy.heartbeat = time.monotonic()

    def _on_safety(self, message: Bool) -> None:
        """Apply the watchdog's stop condition before the next output tick."""
        self.policy.safety_stop = message.data
        if message.data:
            self._revoke('safety_stop')

    def _on_edge(self, message: String) -> None:
        """Record a floor-safety observation; malformed input blocks motion."""
        try:
            data = json.loads(message.data)
            if not isinstance(data, dict) or not isinstance(data.get('blocked'), bool):
                raise ValueError('edge event requires a boolean blocked field')
            self.policy.edge_blocked = data['blocked']
            self.policy.edge_stamp = time.monotonic()
        except (ValueError, TypeError):
            self.policy.edge_blocked = True

    def _on_command(self, message: String) -> None:
        """Revoke ownership immediately for a stop command from any frontend."""
        if is_stop_command(message.data):
            self._revoke('command_stop')

    def _revoke(self, reason: str) -> None:
        """Latch the current mission so delayed owner messages cannot resume motion.

        Args:
            reason: Machine-readable reason for stopping the active mission.
        """
        mission = str(self._context.get('mission_id') or '')
        if mission:
            self._revoked_missions.add(mission)
        self.policy.select('none', time.monotonic())
        self._publisher.publish(Twist())
        event = String(data=json.dumps({'event': reason, 'owner': 'none',
                                       **self._context, 'wall_time': time.time()}))
        self._events.publish(event)

    def _tick(self) -> None:
        """Publish a fresh, bounded command or zero and log reason transitions."""
        previous_owner = self.policy.owner
        values, reason = self.policy.output(time.monotonic())
        if previous_owner != 'none' and reason in (
                'heartbeat_stale', 'safety_stop', 'edge_blocked_or_stale'):
            self._revoke(reason)
        linear = float(self.get_parameter('max_linear_mps').value)
        angular = float(self.get_parameter('max_angular_radps').value)
        message = Twist()
        speed = math.hypot(values[0], values[1])
        scale = min(1.0, linear / speed) if speed > 0 else 1.0
        message.linear.x = values[0] * scale
        message.linear.y = values[1] * scale
        message.angular.z = max(-angular, min(angular, values[2]))
        self._publisher.publish(message)
        if reason != self._last_reason:
            self._last_reason = reason
            event = String()
            event.data = json.dumps({'event': reason, 'owner': self.policy.owner,
                                     **self._context, 'wall_time': time.time()})
            self._events.publish(event)
            descriptions = {
                'authorized': 'Motion enabled for the active controller',
                'no_owner': 'Stopped; no active motion controller',
                'heartbeat_pending': 'Waiting for Brain heartbeat; motion is stopped',
                'command_stale': 'Stopped; velocity command expired',
                'heartbeat_stale': 'Stopped; Brain heartbeat is missing',
                'safety_stop': 'Stopped by safety interlock',
                'edge_blocked_or_stale': 'Stopped; floor clearance is blocked or unknown',
            }
            description = descriptions.get(reason, sanitize_text(reason).replace('_', ' '))
            if reason == 'command_stale' and self.policy.owner == 'none':
                description = 'Stopped; no active motion controller'
            level = 'success' if reason == 'authorized' else 'info'
            if reason in ('heartbeat_stale', 'safety_stop', 'edge_blocked_or_stale'):
                level = 'warning'
            self.get_logger().info(format_line(
                'MOTION', description, level))


def main(args: list[str] | None = None) -> None:
    """Run the gate and send a final zero while its ROS context is available."""
    rclpy.init(args=args)
    node = VelocityGate()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        if rclpy.ok():
            node._publisher.publish(Twist())
        node.destroy_node()
        rclpy.try_shutdown()
