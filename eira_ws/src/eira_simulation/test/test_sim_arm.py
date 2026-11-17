"""Verify native-URDF kinematics and measured-state simulation arm contracts.

Author: E-AIRA maintainers.
Hardware target: M3 Pro Gazebo simulation, mocked ROS boundaries without hardware.
"""

import math
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest

from eira_simulation.kinematics import (
    ARM_JOINTS, FINGER_JOINTS, FINGER_SIGNS, KinematicsError, URDFChain,
    axis_rotation, joints_to_servo, rotation_rpy, rotation_vector, servo_to_joints,
)


@pytest.fixture
def chain() -> URDFChain:
    """Load the actual supplied exercise-08 CAD model, including its real origins and axes."""
    source = Path(__file__).resolve().parents[4] / (
        '08. robot model/neurobotics_ws/src/neurobotics/urdf/neurobotics.urdf')
    return URDFChain.from_file(source)


def test_native_chain_preserves_five_arm_joints_and_tool(chain: URDFChain) -> None:
    """The simulation arm must derive geometry from M3 Pro rather than a generic template."""
    assert tuple(joint.name for joint in chain.movable) == ARM_JOINTS
    transform = chain.forward({})
    assert transform.shape == (4, 4)
    assert transform[2, 3] == pytest.approx(.55175, abs=.001)
    assert np.linalg.det(transform[:3, :3]) == pytest.approx(1.0)


@pytest.mark.parametrize('configuration', [
    [.2, -.3, .4, -.5, 0], [0, -1, 1, -1, 0], [.5, -.5, -.5, -.5, 0],
])
def test_forward_inverse_round_trip_in_original_limits(
        chain: URDFChain, configuration: list[float]) -> None:
    """Reach known poses using bounded numerical IK and the executor's fourth-servo limit."""
    target = chain.forward(dict(zip(ARM_JOINTS, configuration)))[:3, 3]
    result = chain.inverse(target, active_names=ARM_JOINTS[:4], max_seconds=2.0,
                           extra_limits={ARM_JOINTS[3]: (-math.pi / 2, 0.0)})
    assert result.success
    assert np.linalg.norm(chain.forward(result.positions)[:3, 3] - target) <= .005
    assert result.positions[ARM_JOINTS[3]] <= 0.0


def test_unreachable_target_reports_failure_without_valid_looking_solution(
        chain: URDFChain) -> None:
    """IK cannot turn an impossible target into a successful all-zero servo response."""
    result = chain.inverse(np.array([10.0, 10.0, 10.0]), max_iterations=10,
                           restarts=1, max_seconds=.2)
    assert not result.success
    assert result.position_error_m > 1.0


@pytest.mark.parametrize('position', [math.nan, math.inf, 10.0])
def test_fk_rejects_nonfinite_or_out_of_limit_configuration(
        chain: URDFChain, position: float) -> None:
    """Bad geometry requests must fail before model or trajectory publication."""
    with pytest.raises(ValueError):
        chain.forward({ARM_JOINTS[0]: position})


def test_axis_and_rpy_rotations_follow_urdf_convention() -> None:
    """Joint and origin rotations retain their specified order and normalized axes."""
    rotation = axis_rotation(np.array([0, 0, 2]), math.pi / 2)
    assert np.allclose(rotation @ [1, 0, 0], [0, 1, 0], atol=1e-8)
    assert np.allclose(rotation_rpy(0, 0, math.pi / 2), rotation)
    assert np.linalg.norm(rotation_vector(rotation_rpy(math.pi, 0, 0))) == pytest.approx(math.pi)


def test_servo_mapping_preserves_original_gripper_coupling() -> None:
    """The original six-finger coupling signs remain explicit and measured round trips agree."""
    angles = [80.0, 70.0, 95.0, 60.0, 100.0, 30.0]
    positions = servo_to_joints(angles, [90.0] * 5, [1.0] * 5)
    for name, sign in zip(FINGER_JOINTS, FINGER_SIGNS):
        assert positions[name] == -float(sign)
    assert joints_to_servo(positions, [90.0] * 5, [1.0] * 5) == pytest.approx(angles)


def test_gripper_open_saturates_at_actual_model_limit() -> None:
    """A legacy 180-degree open command must not push the simulated finger beyond zero radians."""
    positions = servo_to_joints([90.0] * 5 + [180.0], [90.0] * 5, [1.0] * 5)
    assert positions[FINGER_JOINTS[0]] == 0.0


@pytest.fixture
def bridge(chain: URDFChain) -> Any:
    """Construct real callbacks with installed ROS messages and mocked graph publications."""
    from rclpy.time import Time
    from eira_simulation.sim_arm_bridge import SimArmBridge
    node = object.__new__(SimArmBridge)
    node._chain, node._offsets, node._signs = chain, [90.0] * 5, [1.0] * 5
    node._mapping = dict(gripper_open_deg=90.0, gripper_close_deg=30.0,
                         gripper_open_rad=0.0, gripper_close_rad=-1.0)
    node._measured, node._measurement_time = {}, None
    parameters = dict(feedback_future_tolerance_s=.05, feedback_timeout_s=1.0,
                      min_runtime_s=.05, max_runtime_s=15.0, allow_fk=True,
                      gripper_open_deg=90.0, ik_joint4_max_deg=90.0, ik_orientation_weight=0.0,
                      ik_position_tolerance_m=.005, ik_orientation_tolerance_rad=.15,
                      ik_max_iterations=100, ik_timeout_s=1.0, ik_damping=.02,
                      ik_epsilon=1e-5, ik_max_step_rad=.15, ik_restarts=3, ik_random_seed=42)
    node._p = parameters.__getitem__
    node.trajectories, node.feedback, node.events = [], [], []
    node._trajectory_pub = SimpleNamespace(publish=node.trajectories.append)
    node._feedback_pub = SimpleNamespace(publish=node.feedback.append)
    node._event_pub = SimpleNamespace(publish=node.events.append)
    node._CurJoints = lambda: SimpleNamespace(
        get_fields_and_field_types=lambda: {'joints': 'float[]'})
    node.get_clock = lambda: SimpleNamespace(now=lambda: Time(seconds=10.0))
    node.get_logger = lambda: SimpleNamespace(info=lambda text: None, warning=lambda text: None)
    return node


def test_commands_never_publish_desired_as_measured_feedback(bridge: Any) -> None:
    """Only a measured JointState callback may produce Curjoints."""
    command = SimpleNamespace(**{f'joint{i}': 90 for i in range(1, 7)}, time=2000)
    bridge._on_six(command)
    assert bridge.trajectories == []  # Wait for measurements before starting interpolation.
    assert bridge.feedback == []
    assert len(bridge._active_motion['target']) == 11


def test_complete_measured_state_produces_curjoints(bridge: Any) -> None:
    """Gazebo's measured joint positions are the only feedback source."""
    from sensor_msgs.msg import JointState
    message = JointState()
    positions = servo_to_joints([90.0] * 5 + [30.0], [90.0] * 5, [1.0] * 5)
    message.name, message.position = list(positions), list(positions.values())
    message.header.stamp.sec = 10
    bridge._on_states(message)
    assert bridge.feedback[-1].joints == pytest.approx([90.0] * 5 + [30.0])


def test_single_servo_without_measured_state_is_rejected(bridge: Any) -> None:
    """Preserving other joints requires observed positions, not a fabricated home pose."""
    bridge._on_single(SimpleNamespace(id=6, joint=30, time=2000))
    assert not bridge.trajectories


def test_trajectory_respects_native_velocity_limit(bridge: Any) -> None:
    """A short command duration is lengthened to respect the actual URDF speed limit."""
    from rclpy.time import Time
    bridge._measured = servo_to_joints([90.0] * 6, [90.0] * 5, [1.0] * 5)
    bridge._measurement_time = Time(seconds=10)
    bridge._send_trajectory([0.0] + [90.0] * 5, 100)
    assert bridge._active_motion['duration_s'] >= math.pi / 2 - 1e-8
    assert bridge.trajectories[-1].header.frame_id == 'world'
    # The native pose plugin receives the measured starting point, not a jump.
    assert bridge.trajectories[-1].points[0].positions[0] == pytest.approx(0.0)
    bridge.get_clock = lambda: SimpleNamespace(now=lambda: Time(seconds=10.5))
    bridge._tick_motion()
    assert bridge.trajectories[-1].points[0].positions[0] == pytest.approx(-0.5, abs=1e-5)


def test_ik_service_uses_existing_response_base_reflection(bridge: Any) -> None:
    """Response conventions reproduce the high-level executor's 180-minus-joint1 mapping."""
    target = bridge._chain.forward(dict(zip(ARM_JOINTS, [.2, -.3, .4, -.5, 0])))[:3, 3]
    request = SimpleNamespace(kin_name='ik', tar_x=target[0], tar_y=target[1], tar_z=target[2],
                              roll=0.0, pitch=0.0, yaw=0.0)
    response = SimpleNamespace(get_fields_and_field_types=lambda: {
        f'joint{i}': 'float64' for i in range(1, 5)})
    bridge._on_kinematics(request, response)
    angles = [180 - response.joint1, response.joint2, response.joint3, response.joint4, 90.0, 90.0]
    positions = servo_to_joints(angles, [90.0] * 5, [1.0] * 5)
    assert np.linalg.norm(bridge._chain.forward(positions)[:3, 3] - target) <= .005


def test_failed_ik_without_status_field_withholds_response(bridge: Any) -> None:
    """Without a failure flag, withhold a response rather than emit valid-looking zero angles."""
    request = SimpleNamespace(kin_name='ik', tar_x=10.0, tar_y=10.0, tar_z=10.0,
                              roll=0.0, pitch=0.0, yaw=0.0)
    response = SimpleNamespace(get_fields_and_field_types=lambda: {})
    with pytest.raises(KinematicsError):
        bridge._on_kinematics(request, response)
    assert not hasattr(response, 'joint1')
