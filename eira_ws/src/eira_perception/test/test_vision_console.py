"""Verify readable perception logs while retaining correlated JSON ROS events.

Author: E-AIRA maintainers.
Hardware target: mocked ROSMASTER M3 Pro / Jetson Orin NX, ROS 2 Humble.
"""

import json
from unittest.mock import Mock

from eira_perception.vision_manager import VisionManager


def node() -> VisionManager:
    """Create a perception logger without a camera, GPU, or DDS participant.

    Returns:
        Node fixture with observable log and event publishers.
    """
    vision = object.__new__(VisionManager)
    vision._request = {'mission_id': 'm', 'action_id': '1:1', 'target': 'red cup'}
    vision.get_logger = Mock(return_value=Mock())
    vision._event_pub = Mock()
    vision._param = Mock(return_value=20.0)
    vision._warnings = {}
    return vision


def test_found_is_readable_and_machine_evidence_is_unchanged() -> None:
    """Readable distance/confidence output does not replace JSON evidence on ROS."""
    vision = node()
    vision._emit('found', depth_m=0.85, confidence=0.92, track_id=7)
    payload = json.loads(vision._event_pub.publish.call_args.args[0].data)
    assert payload['event'] == 'found'
    assert payload['mission_id'] == 'm' and payload['action_id'] == '1:1'
    text = vision.get_logger().info.call_args.args[0]
    assert 'Found red cup' in text and '0.85 m' in text and '92%' in text
    assert 'mission_id' not in text


def test_refresh_observations_do_not_repeat_info_logs() -> None:
    """Repeated one-shot updates remain on topics while normal terminal output stays quiet."""
    vision = node()
    for _ in range(3):
        vision._emit('found', depth_m=0.85, confidence=0.92, track_id=7)
        vision._log('idle')
    assert vision._event_pub.publish.call_count == 3
    assert vision.get_logger().info.call_count == 2
    assert vision.get_logger().debug.call_count == 4


def test_timeout_hint_names_object_and_configured_budget() -> None:
    """Search failures include the actual target and an operator-facing visibility hint."""
    vision = node()
    vision._emit('timeout', reason='acquisition_timeout')
    text = vision.get_logger().info.call_args.args[0]
    assert "Cannot find 'red cup' within 20s" in text
    assert 'Is the object visible?' in text


def test_depth_warning_contains_recovery_advice() -> None:
    """A visible object without usable depth produces an actionable warning."""
    vision = node()
    vision._warn('no_valid_depth', 'no valid depth')
    assert 'Try better lighting' in vision.get_logger().warning.call_args.args[0]
