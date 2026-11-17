"""Verify operator-facing console text without starting robot nodes.

Author: E-AIRA maintainers.
Hardware target: ROSMASTER M3 Pro / Jetson Orin NX, ROS 2 Humble / Python 3.10.
"""

from copy import deepcopy
from unittest.mock import Mock

import pytest

from eira_brain.console import format_line, format_plan, format_status, sanitize_text


def test_sanitize_prevents_terminal_control_and_multiple_lines() -> None:
    """Untrusted model/command text cannot inject colors, titles, or extra log lines."""
    value = '\033[31mred\033[0m\n\033]0;fake title\007cup\r\t\u202ehello'
    assert sanitize_text(value) == 'red cup hello'


def test_sanitize_retains_unicode_and_marks_truncation() -> None:
    """Readable Unicode survives while long values remain visibly truncated."""
    assert sanitize_text('  café  カップ  ') == 'café カップ'
    assert sanitize_text('abcdefgh', 5) == 'abcd…'
    assert sanitize_text('abcdefgh', 0) == 'abcdefgh'
    assert sanitize_text(None) == ''


def test_explicit_color_only_styles_the_component_label() -> None:
    """Color improves scanning without hiding severity in monochrome terminals."""
    assert format_line('brain', 'Planning', color=False) == '[BRAIN] Planning'
    rendered = format_line('arm', 'Target lost', 'warning', color=True)
    assert rendered == '\033[1;33m[ARM]\033[0m WARNING: Target lost'


@pytest.mark.parametrize('name,value,expected', [
    ('NO_COLOR', '', False), ('FORCE_COLOR', '1', True), ('FORCE_COLOR', '0', False),
    ('RCUTILS_COLORIZED_OUTPUT', '1', True), ('RCUTILS_COLORIZED_OUTPUT', '0', False),
    ('TERM', 'dumb', False),
])
def test_environment_controls_automatic_color(
        monkeypatch: pytest.MonkeyPatch, name: str, value: str, expected: bool) -> None:
    """Common shell and ROS color preferences work for redirected launch output.

    Args:
        monkeypatch: Environment and stream patch fixture.
        name: Environment variable under test.
        value: Requested environment setting.
        expected: Whether ANSI escapes should appear.
    """
    for variable in ('NO_COLOR', 'FORCE_COLOR', 'RCUTILS_COLORIZED_OUTPUT', 'TERM'):
        monkeypatch.delenv(variable, raising=False)
    monkeypatch.setenv(name, value)
    monkeypatch.setattr('sys.stderr', Mock(isatty=Mock(return_value=True)))
    assert ('\033[' in format_line('BRAIN', 'Ready')) is expected


def test_no_color_overrides_force_in_automatic_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    """An explicit accessibility preference takes precedence over shell forcing.

    Args:
        monkeypatch: Fixture setting conflicting environment preferences.
    """
    monkeypatch.setenv('NO_COLOR', '1')
    monkeypatch.setenv('FORCE_COLOR', '1')
    assert '\033[' not in format_line('BRAIN', 'Ready')


def test_redirected_stream_defaults_to_plain_text(monkeypatch: pytest.MonkeyPatch) -> None:
    """Piped logs do not gain terminal escapes unless color was explicitly requested.

    Args:
        monkeypatch: Fixture replacing stream capability and color settings.
    """
    for name in ('NO_COLOR', 'FORCE_COLOR', 'RCUTILS_COLORIZED_OUTPUT'):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr('sys.stderr', Mock(isatty=Mock(return_value=False)))
    assert format_line('VISION', 'Ready') == '[VISION] Ready'


def test_plan_is_readable_and_does_not_mutate_actions() -> None:
    """Users see a complete concise plan and data consumers retain the original objects."""
    actions = [{'action': 'navigate', 'target': 'kitchen'},
               {'action': 'find', 'target': 'red cup'}, {'action': 'grasp'},
               {'action': 'navigate', 'target': 'home'}, {'action': 'release'}]
    original = deepcopy(actions)
    assert format_plan(actions, color=False) == (
        'Navigate to kitchen -> Find red cup -> Grasp -> Navigate to home -> Release')
    assert actions == original
    assert format_plan([], color=False) == 'No actions'


@pytest.mark.parametrize('payload,expected', [
    ({'detail': 'ready'}, '[BRAIN] Ready for commands'),
    ({'event': 'mission_started', 'command': 'Bring me a cup'},
     '[BRAIN] Planning: Bring me a cup'),
    ({'detail': 'queued', 'command': 'find cup', 'queue': 2},
     '[BRAIN] Queued: find cup (2 waiting)'),
    ({'detail': 'rejected: mission queue full'},
     '[BRAIN] WARNING: Command rejected: mission queue full'),
    ({'event': 'action_started', 'action': 'navigate', 'target': 'kitchen',
      'step': 0, 'total': 5}, '[BRAIN] [1/5] Navigating to kitchen'),
    ({'event': 'action_finished', 'action': 'navigate', 'target': 'kitchen',
      'success': True, 'duration_s': 6.2}, '[BRAIN] Navigation to kitchen completed (6.2 s)'),
    ({'event': 'action_finished', 'action': 'find', 'result': 'failed',
      'error_reason': 'Camera stale'}, '[BRAIN] ERROR: Find failed: Camera stale'),
    ({'event': 'action_finished', 'action': 'navigate', 'result': 'canceled'},
     '[BRAIN] WARNING: Navigate canceled'),
    ({'event': 'navigation_settling', 'delay_s': 3.0},
     '[BRAIN] Navigation reached goal; waiting 3 s for localization'),
    ({'event': 'recovery', 'recovery_kind': 'retry', 'retry_index': 2,
      'retry_delay_s': 10.0, 'recovery_reason': 'AMCL uncertain'},
     '[BRAIN] WARNING: Retrying 2 in 10 s: AMCL uncertain'),
    ({'event': 'recovery', 'recovery_kind': 'scan', 'scan_count': 1},
     '[BRAIN] WARNING: Scanning for target 1'),
    ({'event': 'mission_finished', 'success': True, 'duration_s': 20.1},
     '[BRAIN] Mission complete (20.1 s)'),
    ({'event': 'mission_finished', 'result': 'canceled', 'error_reason': 'operator stop'},
     '[BRAIN] WARNING: Mission canceled: operator stop'),
    ({'event': 'mission_finished', 'success': True, 'detail': 'stopped'},
     '[BRAIN] WARNING: Stopped'),
    ({'state': 'FAILED', 'detail': 'No path'}, '[BRAIN] ERROR: Mission failed: No path'),
    ({'state': 'WAIT_GRASP'}, '[BRAIN] Grasp in progress'),
    ({}, '[BRAIN] Status updated'),
])
def test_status_events_are_human_readable(payload: dict, expected: str) -> None:
    """Mission events become concise operator statements rather than serialized fields.

    Args:
        payload: Synthetic ROS status payload.
        expected: Required monochrome operator-facing line.
    """
    assert format_status(payload, color=False) == expected


def test_fallback_reason_and_latency_remain_visible() -> None:
    """Readable planning output preserves information needed to explain degradation."""
    payload = {'event': 'planning_finished', 'planner': 'fallback',
               'planning_latency_ms': 30_010.4, 'planner_reason': 'LLM request timed out'}
    assert format_status(payload, color=False) == (
        '[BRAIN] WARNING: Plan ready: rule-based fallback (30010 ms); LLM request timed out')


def test_grasp_completion_is_not_reported_as_verified_holding() -> None:
    """A servo sequence success cannot be translated into an unsupported physical claim."""
    payload = {'event': 'action_finished', 'action': 'grasp', 'success': True,
               'physical_contact_verified': False}
    text = format_status(payload, color=False)
    assert 'Grasp sequence completed' in text
    assert 'object hold unverified' in text
    assert 'object held' not in text.lower()


def test_status_retains_payload_and_hides_verbose_ids() -> None:
    """Formatting is observational and mission correlation stays available in ROS data."""
    payload = {'event': 'action_started', 'action': 'find', 'target': 'cup',
               'mission_id': 'a' * 32, 'action_id': '0:1', 'step': 0, 'total': 1}
    original = deepcopy(payload)
    text = format_status(payload, color=False)
    assert text == '[BRAIN] [1/1] Searching for cup'
    assert payload == original
    assert payload['mission_id'] not in text


def test_missing_and_invalid_optional_fields_do_not_break_display() -> None:
    """Incomplete legacy status remains displayable without invented progress or timing."""
    payload = {'event': 'action_finished', 'action': 'find', 'success': True,
               'duration_s': float('nan'), 'step': True, 'total': 'unknown'}
    assert format_status(payload, color=False) == '[BRAIN] Target found'


def test_explicit_failure_cannot_be_overridden_by_legacy_done_state() -> None:
    """An explicit failed result takes precedence over a legacy terminal-state label."""
    payload = {'state': 'DONE', 'success': False, 'error_reason': 'delivery unverified'}
    assert format_status(payload, color=False) == (
        '[BRAIN] ERROR: Mission failed: delivery unverified')


def test_oversized_numeric_observations_do_not_break_logging() -> None:
    """Malformed external timing metadata cannot interrupt status rendering."""
    payload = {'event': 'mission_finished', 'success': True, 'duration_s': 10 ** 1000}
    assert format_status(payload, color=False) == '[BRAIN] Mission complete'
