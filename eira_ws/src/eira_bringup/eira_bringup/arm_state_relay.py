"""Relay commanded servo poses into JointState for robot-model visualization.

Author: E-AIRA maintainers.
Hardware target: ROSMASTER M3 Pro / Jetson Orin NX, ROS 2 Humble / Python 3.10.
These are commanded display positions, not measured feedback or grasp evidence.
This node does not publish motor commands, Curjoints, or actuator acknowledgements.
"""

from collections.abc import Sequence
import math
from numbers import Real
import sys
from typing import Any

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from sensor_msgs.msg import JointState

from eira_brain.console import format_line


JOINT_NAMES = tuple([f'arm{index}_Joint' for index in range(1, 6)] + ['rlink1_Joint'])


def _finite_six(values: Sequence[float], label: str) -> list[float]:
    """Validate a six-value servo/calibration vector before display conversion.

    Args:
        values: Six numeric entries.
        label: Diagnostic name used when reporting a malformed vector.

    Returns:
        Finite numeric values as a new list.

    Raises:
        ValueError: The vector has the wrong length or contains invalid values.
    """
    if len(values) != len(JOINT_NAMES):
        raise ValueError(f'{label} must contain exactly six values')
    if any(isinstance(value, bool) or not isinstance(value, Real) for value in values):
        raise ValueError(f'{label} must contain numeric values')
    try:
        result = [float(value) for value in values]
    except (ValueError, TypeError, OverflowError) as exc:
        raise ValueError(f'{label} contains an invalid number') from exc
    if not all(math.isfinite(value) for value in result):
        raise ValueError(f'{label} must contain finite values')
    return result


def positions_from_degrees(angles: Sequence[float], offsets: Sequence[float],
                           signs: Sequence[float], max_abs_angle_deg: float = 360.0
                           ) -> list[float]:
    """Convert degree-valued commands into configurable display joint coordinates.

    Raw degree-to-radian conversion uses zero offsets and positive signs. Supply
    the robot model's calibrated zero offsets and axis signs when they differ.
    No gripper geometry or hidden encoder measurement is inferred here.

    Args:
        angles: Six degree-valued servo commands in the existing driver order.
        offsets: Six degree-valued zero offsets for the displayed model joints.
        signs: Six axis signs, each either -1 or 1.
        max_abs_angle_deg: Positive finite input-command magnitude bound.

    Returns:
        Six radian-valued commanded joint positions in JOINT_NAMES order.

    Raises:
        ValueError: A command, vector, sign, bound, or computed position is invalid.
    """
    commands = _finite_six(angles, 'servo angles')
    zeros = _finite_six(offsets, 'servo offsets')
    axes = _finite_six(signs, 'servo signs')
    if isinstance(max_abs_angle_deg, bool) or not isinstance(max_abs_angle_deg, Real) or (
            not math.isfinite(max_abs_angle_deg) or max_abs_angle_deg <= 0):
        raise ValueError('max_abs_angle_deg must be positive and finite')
    if any(abs(angle) > max_abs_angle_deg for angle in commands):
        raise ValueError('servo angle exceeds configured display command bound')
    if any(sign not in (-1.0, 1.0) for sign in axes):
        raise ValueError('servo signs must be -1 or 1')
    positions = [math.radians(angle - offset) * sign
                 for angle, offset, sign in zip(commands, zeros, axes)]
    if not all(math.isfinite(position) for position in positions):
        raise ValueError('converted joint position is not finite')
    return positions


def read_servo_angles(message: Any) -> list[float]:
    """Read the six existing ArmJoints fields without importing vendor types eagerly.

    Args:
        message: Existing arm_msgs/ArmJoints command with joint1 through joint6.

    Returns:
        Finite degree-valued commands in driver order.

    Raises:
        ValueError: A required joint field is absent or malformed.
    """
    try:
        values = [getattr(message, f'joint{index}') for index in range(1, 7)]
    except AttributeError as exc:
        raise ValueError('arm command requires joint1 through joint6') from exc
    return _finite_six(values, 'servo angles')


class ArmStateRelay(Node):
    """Display the latest complete commanded arm pose without fabricating measurements."""

    def __init__(self) -> None:
        """Declare display mapping and subscribe to the original arm command interfaces.

        Raises:
            ImportError: The real vendor arm message definitions are not installed.
            ValueError: Display calibration or command bounds are invalid.
        """
        from arm_msgs.msg import ArmJoint, ArmJoints

        super().__init__('arm_state_relay')
        defaults = {
            'command_topic': '/arm6_joints', 'single_command_topic': '/arm_joint',
            'joint_state_topic': '/joint_states', 'servo_offsets_deg': [0.0] * 6,
            'servo_signs': [1.0] * 6, 'max_abs_angle_deg': 360.0,
        }
        for name, value in defaults.items():
            self.declare_parameter(name, value)
        self._offsets = list(self.get_parameter('servo_offsets_deg').value)
        self._signs = list(self.get_parameter('servo_signs').value)
        self._max_abs_angle = float(self.get_parameter('max_abs_angle_deg').value)
        positions_from_degrees([0.0] * 6, self._offsets, self._signs, self._max_abs_angle)
        self._commanded_degrees: list[float] | None = None
        self._pub = self.create_publisher(
            JointState, self.get_parameter('joint_state_topic').value, 10)
        self.create_subscription(ArmJoints, self.get_parameter('command_topic').value,
                                 self._on_six, 10)
        self.create_subscription(ArmJoint, self.get_parameter('single_command_topic').value,
                                 self._on_single, 10)
        self.get_logger().info(format_line(
            'ARM DISPLAY', 'Commanded arm display poses; not measured feedback'))

    def _publish(self, angles: list[float]) -> None:
        """Publish a complete validated display pose stamped at command receipt time.

        Args:
            angles: Six actual degree-valued commands; not a guessed startup pose.

        Raises:
            ValueError: The command or display mapping is invalid.
        """
        positions = positions_from_degrees(
            angles, self._offsets, self._signs, self._max_abs_angle)
        message = JointState()
        message.header.stamp = self.get_clock().now().to_msg()
        message.name = list(JOINT_NAMES)
        message.position = positions
        self._pub.publish(message)
        self._commanded_degrees = list(angles)

    def _on_six(self, message: Any) -> None:
        """Relay valid full commands and leave the previous display unchanged on errors.

        Args:
            message: Existing ArmJoints command.
        """
        try:
            self._publish(read_servo_angles(message))
        except (ValueError, TypeError, OverflowError) as exc:
            self.get_logger().warning(format_line(
                'ARM DISPLAY', f'Ignored invalid arm command: {exc}', 'warning'))

    def _on_single(self, message: Any) -> None:
        """Apply a valid single-servo command only after a complete pose is known.

        Args:
            message: Existing ArmJoint command with one-based id and degree joint value.
        """
        try:
            joint_id, angle = message.id, message.joint
            if isinstance(joint_id, bool) or not isinstance(joint_id, int) or not (
                    1 <= joint_id <= len(JOINT_NAMES)):
                raise ValueError('single joint id must be between 1 and 6')
            if self._commanded_degrees is None:
                self.get_logger().debug(format_line(
                    'ARM DISPLAY', 'Waiting for a complete arm command before single updates'))
                return
            updated = list(self._commanded_degrees)
            updated[joint_id - 1] = angle
            self._publish(updated)
        except (AttributeError, ValueError, TypeError, OverflowError) as exc:
            self.get_logger().warning(format_line(
                'ARM DISPLAY', f'Ignored invalid single-joint command: {exc}', 'warning'))


def main(args: list[str] | None = None) -> None:
    """Run the display relay with deferred vendor interfaces and orderly shutdown.

    Args:
        args: Optional ROS command-line arguments.
    """
    rclpy.init(args=args)
    node = None
    try:
        node = ArmStateRelay()
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    except (ImportError, ValueError) as exc:
        print(format_line('ARM DISPLAY', str(exc), 'error'), file=sys.stderr)
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
