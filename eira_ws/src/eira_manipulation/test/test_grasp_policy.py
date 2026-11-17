"""Test calibrated grasp validation without ROS or hardware.

Author: E-AIRA maintainers.
Hardware target: ROSMASTER M3 Pro / Jetson Orin NX (mocked).
"""

import json

import pytest

from eira_manipulation.grasp_policy import (
    calibrated_gripper_angle, joint_vector, request_envelope,
)
from eira_manipulation.pid import PID


def test_width_interpolation_uses_measured_points() -> None:
    """Interpolate a supplied test fixture, never an invented hardware calibration."""
    assert calibrated_gripper_angle(0.03, '[[0.02, 40], [0.04, 80]]') == 60


@pytest.mark.parametrize('width,table', [
    (0.03, '[]'), (0.01, '[[0.02, 40], [0.04, 80]]'),
    (0.05, '[[0.02, 40], [0.04, 80]]'),
    (0.03, '[[0.02, 40], [0.02, 80]]'),
    (0.03, '[[0.02, 40], [0.04, 280]]'), (float('nan'), '[[0.02, 40], [0.04, 80]]'),
])
def test_width_rejects_unsafe_or_missing_calibration(width: float, table: str) -> None:
    """Reject missing calibration and out-of-range extrapolation."""
    with pytest.raises(ValueError):
        calibrated_gripper_angle(width, table)


@pytest.mark.parametrize('joints', [[90] * 5, [90] * 5 + [181], [float('nan')] * 6])
def test_invalid_joint_solution_rejected(joints: list[float]) -> None:
    """Reject malformed or unsafe IK outputs instead of silently clamping them."""
    with pytest.raises(ValueError):
        joint_vector(joints, [0.0] * 6, [180.0] * 6)


def test_request_preserves_correlated_target_context() -> None:
    """Keep acquisition metadata and identifiers across the String envelope."""
    request = request_envelope(json.dumps({
        'mission_id': 'mission', 'action_id': '2:0', 'command': 'grasp',
        'target': {'width_m': 0.03, 'color': 'red', 'mission_id': 'mission'},
    }))
    assert request['target']['width_m'] == 0.03
    assert request['action_id'] == '2:0'


@pytest.mark.parametrize('payload', ['[]', '123', '{"command":"grasp","mission_id":"m"}'])
def test_request_rejects_invalid_structure(payload: str) -> None:
    """Reject structured messages that cannot be correlated safely."""
    with pytest.raises(ValueError):
        request_envelope(payload)


def test_legacy_request_remains_available() -> None:
    """Retain the original plain String command API."""
    assert request_envelope('home')['command'] == 'home'


def test_pid_rejects_nonfinite_error() -> None:
    """Never let NaN sensor input become a saturated motor command."""
    with pytest.raises(ValueError):
        PID(1.0).update(float('nan'), 0.1)
