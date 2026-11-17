"""Verify truthful RViz markers through mocked topic delivery and publisher endpoints.

Author: E-AIRA maintainers.
Hardware target: mocked ROSMASTER M3 Pro / Jetson Orin NX, ROS 2 Humble.
"""

from collections import OrderedDict
import json
import math
from pathlib import Path
import time
from types import SimpleNamespace
from unittest.mock import Mock

from builtin_interfaces.msg import Time
from geometry_msgs.msg import PoseStamped, PoseWithCovarianceStamped
import pytest
from std_msgs.msg import String
from visualization_msgs.msg import Marker

from eira_bringup.visualization_markers import VisualizationMarkers


@pytest.fixture
def display() -> VisualizationMarkers:
    """Create the display state without constructing any ROS participant.

    Returns:
        Marker node with a fixed clock and mocked publisher.
    """
    node = object.__new__(VisualizationMarkers)
    node._test_parameters = {
        'waypoints_file': '', 'marker_lifetime_s': 5.0, 'refresh_hz': 2.0,
        'pose_stale_s': 5.0, 'heading_stale_s': 15.0, 'future_tolerance_s': 0.1,
        'waypoint_diameter_m': 0.18, 'object_diameter_m': 0.10,
        'heading_length_m': 0.45, 'heading_width_m': 0.04,
        'label_height_m': 0.15, 'label_scale_m': 0.10,
    }
    node.get_parameter = Mock(side_effect=lambda key: SimpleNamespace(
        value=node._test_parameters[key]))
    node._test_now_ns = 100_000_000_000
    node.get_clock = Mock(return_value=SimpleNamespace(now=lambda: SimpleNamespace(
        nanoseconds=node._test_now_ns,
        to_msg=lambda: Time(sec=node._test_now_ns // 1_000_000_000,
                            nanosec=node._test_now_ns % 1_000_000_000))))
    node._mission_id, node._status = '', {}
    node._plans, node._finished, node._found, node._poses = (
        OrderedDict(), OrderedDict(), OrderedDict(), OrderedDict())
    node._object_event = node._object_pose = node._object_received_at = None
    node._heading = node._heading_received_at = None
    node._waypoints = {'kitchen': {'x': 1.25, 'y': -0.5, 'yaw': 0.0}}
    node._map_frame = 'arena_map'
    node._shown = set()
    node._pub, node.get_logger = Mock(), Mock(return_value=Mock())
    node._load_waypoints = Mock()
    return node


def status(**fields: object) -> String:
    """Create synthetic status telemetry.

    Args:
        **fields: Overrides for the active navigation mission.

    Returns:
        Existing JSON String contract with a mission identity.
    """
    return String(data=json.dumps({
        'mission_id': 'm1', 'state': 'WAIT_NAV', 'action': 'navigate', 'step': 0, **fields}))


def plan(mission_id: str = 'm1') -> String:
    """Create a grounded navigation plan arriving on a separate topic.

    Args:
        mission_id: Mission owning the plan.

    Returns:
        Existing plan JSON message.
    """
    return String(data=json.dumps({'mission_id': mission_id,
                                   'actions': [{'action': 'navigate', 'target': 'kitchen'}]}))


def found(**fields: object) -> String:
    """Create a found event with an actual measurement join key.

    Args:
        **fields: Overrides for mission, identity or measurement metadata.

    Returns:
        Existing vision event JSON.
    """
    return String(data=json.dumps({'mission_id': 'm1', 'action_id': '0:1', 'event': 'found',
                                   'target': 'red cup', 'measurement_stamp_ns': 100_000_000_000,
                                   **fields}))


def target_pose(stamp: int = 100, frame: str = 'base_link') -> PoseStamped:
    """Create a real-shaped target pose with known Euclidean range.

    Args:
        stamp: Capture timestamp in ROS seconds.
        frame: Original measurement frame.

    Returns:
        Pose located 0.5 metres from its coordinate origin.
    """
    message = PoseStamped()
    message.header.frame_id, message.header.stamp.sec = frame, stamp
    message.pose.position.x, message.pose.position.y = 0.3, 0.4
    message.pose.orientation.w = 1.0
    return message


def shown_markers(display: VisualizationMarkers) -> list[Marker]:
    """Read the latest marker array published by the mocked endpoint.

    Args:
        display: Marker node with an observable publisher.

    Returns:
        Last MarkerArray's markers.
    """
    return display._pub.publish.call_args.args[0].markers


@pytest.mark.parametrize('plan_first', [False, True])
def test_goal_uses_grounded_coordinates_in_either_topic_order(
        display: VisualizationMarkers, plan_first: bool) -> None:
    """Cross-topic order must not change the green goal or its actual map frame.

    Args:
        display: Mocked display.
        plan_first: Whether the plan arrives before its first status.
    """
    callbacks = [(display._on_plan, plan()), (display._on_status, status())]
    if not plan_first:
        callbacks.reverse()
    for callback, message in callbacks:
        callback(message)
    display._refresh()
    sphere, text = shown_markers(display)
    assert sphere.type == Marker.SPHERE and text.type == Marker.TEXT_VIEW_FACING
    assert sphere.header.frame_id == 'arena_map'
    assert (sphere.pose.position.x, sphere.pose.position.y) == (1.25, -0.5)
    assert (sphere.color.r, sphere.color.g, sphere.color.b) == (0.0, 1.0, 0.0)
    assert sphere.lifetime.sec == 5
    assert 'kitchen' in text.text


def test_future_plan_does_not_claim_navigation_is_active(display: VisualizationMarkers) -> None:
    """A plan alone is not evidence that its first action was dispatched.

    Args:
        display: Mocked display without active status.
    """
    display._on_plan(plan())
    display._refresh()
    display._pub.publish.assert_not_called()


def test_unknown_waypoint_never_creates_a_fake_origin(display: VisualizationMarkers) -> None:
    """Unavailable coordinates must not be replaced with a zero-valued goal.

    Args:
        display: Mocked display with only one calibrated waypoint.
    """
    display._on_status(status(target='unknown'))
    display._refresh()
    display._pub.publish.assert_not_called()


@pytest.mark.parametrize('pose_first', [False, True])
def test_object_keeps_measured_frame_stamp_label_and_range(
        display: VisualizationMarkers, pose_first: bool) -> None:
    """A red target marker joins found metadata without inventing a map transform.

    Args:
        display: Mocked display with actual-shaped pose messages.
        pose_first: Whether geometry arrives before its found event.
    """
    display._on_status(status(action='find'))
    callbacks = [(display._on_target_pose, target_pose()), (display._on_vision_event, found())]
    if not pose_first:
        callbacks.reverse()
    for callback, message in callbacks:
        callback(message)
    display._refresh()
    sphere, text = shown_markers(display)
    assert sphere.header.frame_id == 'base_link'
    assert sphere.header.stamp.sec == 100
    assert sphere.pose.position.x == 0.3
    assert (sphere.color.r, sphere.color.g, sphere.color.b) == (1.0, 0.0, 0.0)
    assert 'red cup' in text.text and '0.50 m from base_link' in text.text


def test_found_and_pose_can_arrive_before_first_status(display: VisualizationMarkers) -> None:
    """Joining the mission later still uses the exact captured pose.

    Args:
        display: Mocked display before any mission status.
    """
    display._on_target_pose(target_pose())
    display._on_vision_event(found())
    display._on_status(status(action='find'))
    display._refresh()
    assert shown_markers(display)[0].ns == 'eira/object'


def test_mismatched_pose_stamp_is_not_assigned_to_found_object(
        display: VisualizationMarkers) -> None:
    """Nearby timestamps are not treated as proof of object identity.

    Args:
        display: Mocked display receiving out-of-order sensor geometry.
    """
    display._on_status(status(action='find'))
    display._on_target_pose(target_pose(stamp=99))
    display._on_vision_event(found())
    display._refresh()
    display._pub.publish.assert_not_called()
    display._on_target_pose(target_pose())
    display._refresh()
    assert shown_markers(display)[0].header.stamp.sec == 100


@pytest.mark.parametrize('stamp,frame,invalid_position', [
    (0, 'base_link', False), (90, 'base_link', False),
    (101, 'base_link', False), (100, '', False), (100, 'base_link', True),
])
def test_invalid_geometry_does_not_render(
        display: VisualizationMarkers, stamp: int, frame: str, invalid_position: bool) -> None:
    """Unstamped, stale, future, frameless or nonfinite poses are rejected.

    Args:
        display: Mocked display with a 100-second ROS clock.
        stamp: Measurement timestamp.
        frame: Measurement frame.
        invalid_position: Whether the target contains a NaN coordinate.
    """
    message = target_pose(stamp, frame)
    if invalid_position:
        message.pose.position.z = float('nan')
    display._on_target_pose(message)
    assert not display._poses


def test_stale_object_is_deleted_not_refreshed_with_new_time(
        display: VisualizationMarkers, monkeypatch: pytest.MonkeyPatch) -> None:
    """A frozen target cannot remain apparently current through marker republishing.

    Args:
        display: Mocked display with an initially observed cup.
        monkeypatch: Fixture advancing both receipt and ROS time.
    """
    clock = [100.0]
    monkeypatch.setattr(time, 'monotonic', lambda: clock[0])
    display._on_status(status(action='find'))
    display._on_target_pose(target_pose())
    display._on_vision_event(found())
    display._refresh()
    clock[0], display._test_now_ns = 106.0, 106_000_000_000
    display._refresh()
    deleted = shown_markers(display)
    assert len(deleted) == 2
    assert all(marker.ns == 'eira/object' and marker.action == Marker.DELETE for marker in deleted)


def test_heading_arrow_uses_observed_quaternion_and_frame(display: VisualizationMarkers) -> None:
    """Yellow heading is based on actual AMCL pose rather than a default direction.

    Args:
        display: Mocked display without a mission.
    """
    message = PoseWithCovarianceStamped()
    message.header.frame_id, message.header.stamp.sec = 'localization_map', 100
    message.pose.pose.position.x = 2.0
    message.pose.pose.orientation.z = math.sin(math.pi / 4)
    message.pose.pose.orientation.w = math.cos(math.pi / 4)
    display._on_amcl_pose(message)
    display._refresh()
    arrow = shown_markers(display)[0]
    assert arrow.type == Marker.ARROW and arrow.ns == 'eira/heading'
    assert arrow.header.frame_id == 'localization_map' and arrow.header.stamp.sec == 100
    assert arrow.pose.position.x == 2.0
    assert arrow.pose.orientation.z == pytest.approx(math.sin(math.pi / 4))
    assert (arrow.color.r, arrow.color.g, arrow.color.b) == (1.0, 1.0, 0.0)


def test_invalid_heading_never_becomes_an_identity_quaternion(
        display: VisualizationMarkers) -> None:
    """An unavailable rotation is not silently replaced with a fabricated heading.

    Args:
        display: Mocked display receiving an invalid AMCL orientation.
    """
    message = PoseWithCovarianceStamped()
    message.header.frame_id, message.header.stamp.sec = 'map', 100
    message.pose.pose.orientation.w = 0.0
    display._on_amcl_pose(message)
    display._refresh()
    display._pub.publish.assert_not_called()


def test_terminal_clears_mission_markers_and_ignores_late_events(
        display: VisualizationMarkers) -> None:
    """Completed missions cannot be resurrected by delayed plans or sensor events.

    Args:
        display: Mocked display with both mission-owned marker pairs.
    """
    display._on_status(status(target='kitchen'))
    display._on_target_pose(target_pose())
    display._on_vision_event(found())
    display._refresh()
    display._on_status(status(state='DONE'))
    assert all(marker.action == Marker.DELETE for marker in shown_markers(display))
    assert len(shown_markers(display)) == 4
    count = display._pub.publish.call_count
    display._on_plan(plan())
    display._on_status(status())
    display._on_vision_event(found())
    display._refresh()
    assert display._pub.publish.call_count == count
    assert display._mission_id == ''


def test_new_mission_ignores_old_or_queued_context(display: VisualizationMarkers) -> None:
    """A queued or delayed mission cannot replace the observed active mission.

    Args:
        display: Mocked display following mission transitions.
    """
    display._on_status(status())
    display._on_status(status(mission_id='m2', detail='queued'))
    assert display._mission_id == 'm1'
    display._on_status(status(mission_id='m2'))
    display._on_status(status(mission_id='m1'))
    assert display._mission_id == 'm2'


def test_only_matching_loss_clears_current_object(display: VisualizationMarkers) -> None:
    """Late acquisition failures from another action do not erase a newer observation.

    Args:
        display: Mocked display with one acquired object.
    """
    display._on_status(status(action='find'))
    display._on_target_pose(target_pose())
    display._on_vision_event(found())
    display._refresh()
    display._on_vision_event(found(event='lost', action_id='old'))
    assert display._object_pose is not None
    display._on_vision_event(found(event='lost'))
    assert display._object_pose is None
    assert all(marker.action == Marker.DELETE for marker in shown_markers(display))


def test_late_pose_does_not_move_object_back_in_time(display: VisualizationMarkers) -> None:
    """Continuous pose observations advance timestamps without rollback from old frames.

    Args:
        display: Mocked display with an established exact pose join.
    """
    display._on_status(status(action='find'))
    display._on_target_pose(target_pose())
    display._on_vision_event(found())
    display._test_now_ns = 102_000_000_000
    display._on_target_pose(target_pose(stamp=101))
    display._on_target_pose(target_pose(stamp=100))
    display._refresh()
    assert shown_markers(display)[0].header.stamp.sec == 101


@pytest.mark.parametrize('payload', [
    'bad json', '[]', 'null', '42', '{"actions":[1]}',
    '{"mission_id":"m1","state":[]}', '{"mission_id":"m1","state":{}}',
])
def test_malformed_telemetry_is_ignored(display: VisualizationMarkers, payload: str) -> None:
    """Display-only callbacks cannot crash on malformed or uncorrelated JSON.

    Args:
        display: Mocked display with no active mission.
        payload: Malformed/nonobject/unidentified data.
    """
    message = String(data=payload)
    display._on_plan(message)
    display._on_status(message)
    display._on_vision_event(message)
    display._refresh()
    display._pub.publish.assert_not_called()


def test_waypoint_file_controls_marker_frame_and_fails_without_fake_coordinates(
        display: VisualizationMarkers, tmp_path: Path) -> None:
    """Reloading actual configuration preserves its frame and rejects broken coordinates.

    Args:
        display: Mocked display with configurable waypoint path.
        tmp_path: Directory for a real temporary calibration file.
    """
    path = tmp_path / 'waypoints.yaml'
    display._test_parameters['waypoints_file'] = str(path)
    path.write_text('frame: measured_map\nwaypoints:\n  kitchen: {x: 2.5, y: 1.5, yaw: 0}\n')
    VisualizationMarkers._load_waypoints(display)
    assert display._map_frame == 'measured_map'
    assert display._waypoints['kitchen']['x'] == 2.5
    path.write_text('frame: measured_map\nwaypoints:\n  kitchen: {x: .nan}\n')
    VisualizationMarkers._load_waypoints(display)
    assert display._waypoints == {}
