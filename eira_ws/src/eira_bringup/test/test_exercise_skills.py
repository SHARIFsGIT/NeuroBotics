"""Verify adapted course skills with synthetic images, scans and mocked ROS boundaries.

Author: E-AIRA maintainers.
Hardware target: ROSMASTER M3 Pro / Jetson Orin NX (mocked).
"""

import json
import math
from types import SimpleNamespace
from typing import Any

import cv2
import numpy as np
import pytest

from eira_bringup.exercise_skills import (
    ExerciseSkills, line_error, sector_distance, track_velocity, valid_scan_points,
)


def test_scan_rejects_nan_zero_and_outside_sensor_range() -> None:
    """Invalid returns must not become a nearby track or false clear corridor."""
    points = valid_scan_points([math.nan, 0.0, 0.01, 0.5, math.inf], -0.2, 0.1, 0.1, 10.0)
    assert len(points) == 1
    assert points[0][0] == 0.5


def test_clear_returns_and_scanner_orientation_are_explicit() -> None:
    """Infinity represents clear space only for obstacle checking, not target tracking."""
    points = valid_scan_points([math.inf], math.pi, 0.1, 0.1, 10.0, math.pi, True)
    assert points == [(10.0, 0.0)]
    assert sector_distance(points, 0.0, 0.2) == 10.0
    assert sector_distance(points, 1.0, 0.2) is None


def test_tracking_never_reverses_into_unobserved_space() -> None:
    """Too-close targets stop translation rather than triggering a blind reverse."""
    linear, angular = track_velocity(0.2, 0.2, 0.55, 0.5, 1.0, 0.15, 0.5, 0.05)
    assert linear == 0.0
    assert angular == pytest.approx(0.2)


def test_guard_rotates_without_translation_and_tracking_is_bounded() -> None:
    """Guard remains stationary; extreme track errors obey configured caps."""
    assert track_velocity(3.0, 0.0, 0.55, 1.0, 1.0, 0.15, 0.5, 0.05, True)[0] == 0
    linear, angular = track_velocity(30.0, 1.0, 0.55, 1.0, 1.0, 0.15, 0.5, 0.05)
    assert 0 <= linear <= 0.15
    assert angular == 0.5


def test_line_centroid_uses_floor_region_and_returns_loss() -> None:
    """A synthetic calibrated red stripe yields rightward error; absent stripe yields None."""
    hsv = np.zeros((100, 100, 3), dtype=np.uint8)
    hsv[60:, 70:80] = (5, 200, 200)
    image = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
    assert line_error(image, [0, 85, 126], [9, 253, 253], 0.6, 10) > 0.3
    assert line_error(np.zeros_like(image), [0, 85, 126], [9, 253, 253], 0.6, 10) is None


def test_invalid_hsv_configuration_is_rejected() -> None:
    """Avoid silently wrapping out-of-range thresholds into a different line color."""
    with pytest.raises(ValueError):
        line_error(np.zeros((10, 10, 3), dtype=np.uint8), [-1, 0, 0], [180, 255, 255], .5, 1)


@pytest.fixture
def skill() -> Any:
    """Construct callback state with mocked publishers and a deterministic configuration."""
    node = object.__new__(ExerciseSkills)
    node._command, node._mission_id, node._action_id = '', '', ''
    node._manual, node._owner = False, 'none'
    node._deadline = 0.0
    node._completed = {}
    node._scan_received = None
    parameters = {'default_command_s': 10.0, 'max_command_s': 60.0,
                  'max_linear': .15, 'max_angular': .5, 'sensor_timeout_s': .7,
                  'request_cache_size': 32}
    node._p = parameters.__getitem__
    node.events, node.owners, node.velocities = [], [], []
    node._event_pub = SimpleNamespace(publish=node.events.append)
    node._owner_pub = SimpleNamespace(publish=node.owners.append)
    node._vel_pub = SimpleNamespace(publish=node.velocities.append)
    node.get_logger = lambda: SimpleNamespace(info=lambda text: None, warning=lambda text: None)
    return node


def test_explicit_activation_and_duplicates_do_not_extend_deadline(skill: Any) -> None:
    """A repeated packet cannot keep autonomous motion alive indefinitely."""
    message = SimpleNamespace(data=json.dumps(dict(command='lidar_track', mission_id='m',
                                                   action_id='a', duration_s=1.0)))
    skill._on_request(message)
    deadline = skill._deadline
    skill._on_request(message)
    assert skill._deadline == deadline
    assert len(skill.owners) == 1


def test_stale_sensor_terminates_skill_and_zeroes_owned_channel(skill: Any) -> None:
    """A sensor dropout causes a terminal failure before any nonzero command."""
    skill._on_request(SimpleNamespace(data=json.dumps(dict(
        command='lidar_avoid', mission_id='m', action_id='a', duration_s=10.0))))
    skill._tick()
    assert skill._command == ''
    assert skill.velocities[-1].linear.x == 0.0
    assert json.loads(skill.events[-1].data)['event'] == 'failed'
    assert json.loads(skill.owners[-1].data)['owner'] == 'none'


def test_manual_override_cancels_without_automatic_resume(skill: Any) -> None:
    """Joystick takeover requires a new explicit autonomous request afterward."""
    skill._on_request(SimpleNamespace(data=json.dumps(dict(
        command='lidar_guard', mission_id='m', action_id='a', duration_s=10.0))))
    skill._on_manual(SimpleNamespace(data=True))
    skill._on_manual(SimpleNamespace(data=False))
    assert skill._command == ''
    assert skill.velocities[-1].angular.z == 0.0


def test_other_owner_is_never_overridden_on_skill_exit(skill: Any) -> None:
    """Yielding to Nav2 cannot publish a later none-owner command that undoes its claim."""
    skill._on_request(SimpleNamespace(data=json.dumps(dict(
        command='lidar_guard', mission_id='m', action_id='a', duration_s=10.0))))
    before = len(skill.owners)
    skill._on_owner(SimpleNamespace(data=json.dumps(dict(
        owner='nav', mission_id='other', action_id='b'))))
    assert len(skill.owners) == before
    assert skill._command == ''
    assert skill._owner == 'nav'


def test_retransmitting_completed_action_cannot_restart_motion(skill: Any) -> None:
    """An old completed packet returns its cached terminal response without claiming the base."""
    request = SimpleNamespace(data=json.dumps(dict(
        command='lidar_guard', mission_id='m', action_id='a', duration_s=10.0)))
    skill._on_request(request)
    skill._finish('done', 'test completion')
    claims = len(skill.owners)
    skill._on_request(request)
    assert len(skill.owners) == claims
    assert skill._command == ''
    assert json.loads(skill.events[-1].data)['event'] == 'done'
