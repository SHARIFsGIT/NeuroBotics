"""Verify commanded arm-model display without connecting to hardware.

Author: E-AIRA maintainers.
Hardware target: ROSMASTER M3 Pro / Jetson Orin NX, ROS 2 Humble / Python 3.10.
"""

import importlib.util
import math
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from eira_bringup.arm_state_relay import (
    ArmStateRelay, JOINT_NAMES, positions_from_degrees, read_servo_angles,
)


@pytest.fixture
def relay() -> ArmStateRelay:
    """Construct a display relay with observable output and no real ROS participant.

    Returns:
        Relay instance bypassing hardware-dependent construction.
    """
    node = object.__new__(ArmStateRelay)
    node._offsets = [0.0] * 6
    node._signs = [1.0] * 6
    node._max_abs_angle = 360.0
    node._commanded_degrees = None
    node._pub = Mock()
    node.get_logger = Mock(return_value=Mock())
    # JointState requires the actual builtin Time class rather than arbitrary data.
    from builtin_interfaces.msg import Time
    node.get_clock = Mock(return_value=SimpleNamespace(now=lambda: SimpleNamespace(
        to_msg=lambda: Time(sec=123, nanosec=456))))
    return node


def six_command(values: list[float]) -> SimpleNamespace:
    """Build a synthetic command using the real vendor field names.

    Args:
        values: Six servo commands in degrees.

    Returns:
        Attribute-compatible full arm command.
    """
    return SimpleNamespace(**{f'joint{index}': value for index, value in enumerate(values, 1)})


def test_default_mapping_is_exact_degree_to_radian_conversion() -> None:
    """Default conversion does not invent model-specific servo offsets."""
    angles = [0.0, 30.0, 60.0, 90.0, 120.0, 180.0]
    assert positions_from_degrees(angles, [0.0] * 6, [1.0] * 6) == pytest.approx(
        [math.radians(value) for value in angles])
    assert JOINT_NAMES == ('arm1_Joint', 'arm2_Joint', 'arm3_Joint', 'arm4_Joint',
                           'arm5_Joint', 'rlink1_Joint')


def test_calibrated_offsets_and_axis_signs_are_explicit() -> None:
    """A measured model mapping can be supplied without changing the wire command."""
    assert positions_from_degrees([90.0] * 6, [90.0] * 6, [-1.0] * 6) == [0.0] * 6
    result = positions_from_degrees([100.0] * 6, [90.0] * 6, [-1.0] * 6)
    assert result == pytest.approx([-math.radians(10.0)] * 6)


@pytest.mark.parametrize('values', [
    [0.0] * 5, [0.0] * 7, [float('nan')] * 6, [float('inf')] * 6,
    [True] * 6, ['90'] * 6, [361.0] * 6,
])
def test_invalid_commands_are_rejected(values: list) -> None:
    """Invalid command vectors cannot corrupt the model display.

    Args:
        values: Malformed synthetic command values.
    """
    with pytest.raises(ValueError):
        positions_from_degrees(values, [0.0] * 6, [1.0] * 6)


@pytest.mark.parametrize('offsets,signs,bound', [
    ([0.0] * 5, [1.0] * 6, 360.0), ([0.0] * 6, [0.0] * 6, 360.0),
    ([0.0] * 6, [1.0] * 5, 360.0), ([float('nan')] * 6, [1.0] * 6, 360.0),
    ([0.0] * 6, [1.0] * 6, float('inf')), ([0.0] * 6, [1.0] * 6, 0.0),
])
def test_invalid_calibration_is_rejected(offsets: list, signs: list, bound: float) -> None:
    """Calibration must have complete finite vectors and actual axis signs.

    Args:
        offsets: Candidate degree zero offsets.
        signs: Candidate axis signs.
        bound: Candidate maximum input angle magnitude.
    """
    with pytest.raises(ValueError):
        positions_from_degrees([90.0] * 6, offsets, signs, bound)


def test_missing_vendor_fields_are_rejected() -> None:
    """The relay does not guess an alternative message layout."""
    with pytest.raises(ValueError, match='joint1 through joint6'):
        read_servo_angles(SimpleNamespace(joints=[90.0] * 6))


def test_full_command_publishes_complete_stamped_joint_state(relay: ArmStateRelay) -> None:
    """Display output has exact URDF names and a current receipt stamp.

    Args:
        relay: Hardware-free relay fixture.
    """
    angles = [0.0, 30.0, 60.0, 90.0, 120.0, 180.0]
    relay._on_six(six_command(angles))
    message = relay._pub.publish.call_args.args[0]
    assert message.name == list(JOINT_NAMES)
    assert list(message.position) == pytest.approx([math.radians(angle) for angle in angles])
    assert message.header.stamp.sec == 123
    assert message.header.stamp.nanosec == 456
    assert not message.velocity and not message.effort
    assert relay._commanded_degrees == angles


def test_invalid_full_command_preserves_last_valid_pose(relay: ArmStateRelay) -> None:
    """A malformed command never overwrites cached valid display data.

    Args:
        relay: Hardware-free relay fixture.
    """
    relay._on_six(six_command([90.0] * 6))
    relay._pub.publish.reset_mock()
    relay._on_six(six_command([float('nan')] * 6))
    relay._pub.publish.assert_not_called()
    assert relay._commanded_degrees == [90.0] * 6
    relay.get_logger().warning.assert_called_once()


def test_single_command_waits_for_a_complete_known_pose(relay: ArmStateRelay) -> None:
    """A lone gripper command does not invent positions for five unknown joints.

    Args:
        relay: Hardware-free relay fixture.
    """
    relay._on_single(SimpleNamespace(id=6, joint=30.0))
    relay._pub.publish.assert_not_called()
    assert relay._commanded_degrees is None


def test_single_gripper_command_updates_only_its_known_joint(relay: ArmStateRelay) -> None:
    """The existing single-servo interface keeps RViz gripper motion visible.

    Args:
        relay: Hardware-free relay fixture.
    """
    relay._on_six(six_command([90.0] * 6))
    relay._pub.publish.reset_mock()
    relay._on_single(SimpleNamespace(id=6, joint=30.0))
    message = relay._pub.publish.call_args.args[0]
    assert list(message.position)[:5] == pytest.approx([math.pi / 2.0] * 5)
    assert message.position[5] == pytest.approx(math.pi / 6.0)
    assert relay._commanded_degrees == [90.0] * 5 + [30.0]


@pytest.mark.parametrize('message', [
    SimpleNamespace(id=0, joint=30.0), SimpleNamespace(id=7, joint=30.0),
    SimpleNamespace(id=True, joint=30.0), SimpleNamespace(id=6, joint=float('nan')),
    SimpleNamespace(id=6),
])
def test_invalid_single_commands_do_not_publish(
        relay: ArmStateRelay, message: SimpleNamespace) -> None:
    """Bad single-servo commands cannot be shown as actual valid state.

    Args:
        relay: Hardware-free relay fixture.
        message: Malformed synthetic single command.
    """
    relay._on_six(six_command([90.0] * 6))
    relay._pub.publish.reset_mock()
    relay._on_single(message)
    relay._pub.publish.assert_not_called()
    assert relay._commanded_degrees == [90.0] * 6


def test_source_module_defers_vendor_imports() -> None:
    """Launch discovery and pure conversion tests work without arm_msgs installed."""
    source = Path(__file__).resolve().parents[1] / 'eira_bringup' / 'arm_state_relay.py'
    specification = importlib.util.spec_from_file_location('relay_import_probe', source)
    assert specification is not None and specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    assert module.JOINT_NAMES == JOINT_NAMES
