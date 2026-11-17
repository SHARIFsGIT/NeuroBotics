"""Verify readable arm logs without changing machine-readable manipulation events.

Author: E-AIRA maintainers.
Hardware target: mocked ROSMASTER M3 Pro / Jetson Orin NX, ROS 2 Humble.
"""

import json
import time
from typing import Any
from unittest.mock import Mock

import pytest

from test_grasp_integration import node  # noqa: F401 -- shared mocked hardware fixture


@pytest.fixture
def console_arm(node: Any, monkeypatch: pytest.MonkeyPatch) -> Any:  # noqa: F811
    """Capture uncolored terminal messages from the real executor callbacks.

    Args:
        node: Existing manipulation fixture with captured ROS publishers.
        monkeypatch: Fixture selecting portable terminal rendering.

    Returns:
        Executor with an observable console logger and no hardware access.
    """
    monkeypatch.setenv('NO_COLOR', '1')
    # An INFO-only logger rejects dynamic severity selection on Humble's shared call site.
    node._console_logger = Mock(spec_set=['info'])
    node.get_logger = lambda: node._console_logger
    return node


def test_arm_logs_readable_completion_but_preserves_json(console_arm: Any) -> None:
    """A readable completion must not change the event contract or claim contact.

    Args:
        console_arm: Executor with captured console and ROS events.
    """
    payload = {'event': 'grasped', 'mission_id': 'mission-a', 'action_id': '2:1',
               'joint_feedback_verified': True, 'object_contact_verified': False}
    console_arm._publish_payload(payload)
    published = json.loads(console_arm._event_pub.messages[-1].data)
    assert {key: published[key] for key in payload} == payload
    assert isinstance(published['wall_time'], float)
    text = console_arm._console_logger.info.call_args.args[0]
    assert '[ARM]' in text
    assert 'sequence complete' in text
    assert 'holding is unverified' in text
    assert 'mission_id' not in text
    assert '{' not in text


def test_arm_failure_is_clear_and_keeps_correlated_reason(console_arm: Any) -> None:
    """Operators see the failure reason while collectors retain its exact identity.

    Args:
        console_arm: Executor with captured console and ROS events.
    """
    console_arm._publish_payload({'event': 'failed', 'reason': 'IK response timeout',
                                  'mission_id': 'mission-a', 'action_id': '2:1'})
    text = console_arm._console_logger.info.call_args.args[0]
    assert 'Action failed' in text
    assert 'IK response timeout' in text
    published = json.loads(console_arm._event_pub.messages[-1].data)
    assert published['reason'] == 'IK response timeout'
    assert published['action_id'] == '2:1'


@pytest.mark.parametrize('held,word', [
    (True, 'hold sent'), (False, 'hold unavailable'),
])
def test_arm_stop_distinguishes_feedback_hold(
        console_arm: Any, held: bool, word: str) -> None:
    """A stop request cannot be presented as a measured hold without evidence.

    Args:
        console_arm: Executor with captured console and ROS events.
        held: Whether an actual feedback-derived hold command was sent.
        word: Expected operator-facing hold outcome.
    """
    console_arm._publish_payload({'event': 'stopped', 'arm_hold_sent': held,
                                  'reason': '' if held else 'measured feedback unavailable'})
    text = console_arm._console_logger.info.call_args.args[0]
    assert word in text
    if not held:
        assert 'measured feedback unavailable' in text


def test_replayed_completion_publishes_again_without_console_spam(console_arm: Any) -> None:
    """Request deduplication remains observable on ROS without repeated terminal noise.

    Args:
        console_arm: Executor with captured console and ROS events.
    """
    payload = {'event': 'homed', 'mission_id': 'mission-a', 'action_id': '1:1'}
    console_arm._publish_payload(payload)
    console_arm._publish_payload(payload)
    assert len(console_arm._event_pub.messages) == 2
    assert console_arm._console_logger.info.call_count == 1
    console_arm._publish_payload({**payload, 'mission_id': 'mission-b'})
    assert console_arm._console_logger.info.call_count == 2


def test_arm_progress_logs_dispatched_steps_not_control_ticks(console_arm: Any) -> None:
    """Servo runtime waiting does not repeat the same progress line at control rate.

    Args:
        console_arm: Executor with captured console and ROS events.
    """
    console_arm._start_home()
    started = time.monotonic()
    console_arm._tick_sequence(started)
    text = console_arm._console_logger.info.call_args.args[0]
    assert 'Returning arm home' in text
    console_arm._tick_sequence(started + 0.01)
    console_arm._tick_sequence(started + 0.02)
    assert console_arm._console_logger.info.call_count == 1
    assert len(console_arm._six_pub.messages) == 1


def test_bad_measurements_warn_once_until_another_transition(console_arm: Any) -> None:
    """A stale camera stream cannot print the identical arm warning every frame.

    Args:
        console_arm: Executor with captured console and ROS events.
    """
    for _ in range(20):
        console_arm._log_event('invalid_target_pose')
    assert console_arm._console_logger.info.call_count == 1
    text = console_arm._console_logger.info.call_args.args[0]
    assert 'Ignoring target pose' in text


def test_external_failure_text_cannot_write_terminal_controls(console_arm: Any) -> None:
    """Error text is displayed as one line without injected escape/control sequences.

    Args:
        console_arm: Executor with captured console and ROS events.
    """
    console_arm._log_event('failed', reason='IK failed\n\x1b[2Junexpected')
    text = console_arm._console_logger.info.call_args.args[0]
    assert '\n' not in text
    assert '\x1b' not in text
    assert 'IK failed' in text


def test_verified_negative_contact_does_not_become_grasp_success(console_arm: Any) -> None:
    """A future contact source can report a failed hold without misleading green success.

    Args:
        console_arm: Executor with captured console and ROS events.
    """
    console_arm._publish_payload({'event': 'grasped', 'object_contact_verified': True,
                                  'object_held': False})
    text = console_arm._console_logger.info.call_args.args[0]
    assert 'object not held' in text
    assert 'holding verified' not in text
