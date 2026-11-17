"""Verify that robot failure codes become actionable operator hints.

Author: E-AIRA maintainers.
Hardware target: ROSMASTER M3 Pro / Jetson Orin NX, ROS 2 Humble.
"""

import pytest

from eira_brain.console import error_hint, format_status


@pytest.mark.parametrize('reason,expected', [
    ('navigation status 6', 'Try 2D Pose Estimate in RViz'),
    ('navigation server discovery timeout', 'Is Nav2 running?'),
    ('invalid LLM response: malformed JSON', 'using rule-based fallback'),
    ('vision: timeout', "Cannot find 'cup' within 20s"),
    ('no valid depth', 'Try better lighting or move object to a table.'),
    ('fresh measured arm feedback unavailable', 'Check if arm_status node is running.'),
    ('fresh joint feedback required', 'Check if arm_status node is running.'),
])
def test_known_failure_hints(reason: str, expected: str) -> None:
    """Known failures include concrete next steps rather than unexplained codes.

    Args:
        reason: Existing technical diagnostic.
        expected: Essential operator-facing guidance.
    """
    assert expected in error_hint(reason, target='cup', timeout_s=20.0)


def test_unknown_failure_preserves_detail_without_controls() -> None:
    """Unexpected failures remain observable without permitting terminal injection."""
    assert error_hint('driver\n\x1b[31moffline') == 'driver offline'


def test_failed_fallback_never_claims_a_working_plan() -> None:
    """A fallback validation failure must not falsely reassure an operator."""
    text = error_hint('invalid LLM response; fallback rejected: unknown waypoint')
    assert 'Cannot build a valid plan' in text
    assert 'using rule-based fallback' not in text


def test_action_error_formatting_does_not_mutate_evidence() -> None:
    """ROS consumers retain original codes while terminal readers get recovery advice."""
    payload = {'event': 'action_finished', 'action': 'navigate', 'result': 'failed',
               'success': False, 'error_reason': 'navigation status 6'}
    text = format_status(payload, color=False)
    assert '2D Pose Estimate' in text
    assert payload['error_reason'] == 'navigation status 6'
