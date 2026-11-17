"""Test readable mission reports with reordered evidence and no live ROS graph.

Author: E-AIRA maintainers.
Hardware target: mocked ROSMASTER M3 Pro / Jetson Orin NX, ROS 2 Humble.
"""

from collections import OrderedDict
import json
from pathlib import Path
import time
from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock

import pytest

from eira_brain.mission_reporter import MissionReport, MissionReporter, report_path, write_report


def event(event_name: str, **fields: Any) -> dict[str, Any]:
    """Build synthetic Brain evidence with explicit mission identity.

    Args:
        event_name: Mission/action lifecycle event.
        **fields: Event-specific observed fields.

    Returns:
        Structured topic payload.
    """
    return {'mission_id': 'mission-a', 'event': event_name, 'command': 'find a cup', **fields}


def message(payload: object) -> Any:
    """Encode synthetic topic data without initializing a ROS node.

    Args:
        payload: JSON-compatible test evidence.

    Returns:
        Minimal String-like message.
    """
    return SimpleNamespace(data=json.dumps(payload))


@pytest.fixture
def reporter(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> MissionReporter:
    """Provide the real reporter callbacks with storage and logger boundaries isolated.

    Args:
        tmp_path: Temporary report directory.
        monkeypatch: Fixture disabling terminal color for exact text assertions.

    Returns:
        Uninitialized ROS node wrapper with complete observational state.
    """
    monkeypatch.setenv('NO_COLOR', '1')
    node = object.__new__(MissionReporter)
    node._base = tmp_path
    node._grace = 1.0
    node._capacity = 128
    node._max_chars = 65536
    node._write_retries = 2
    node._write_retry_delay = 2.0
    node._reports = OrderedDict()
    node._pending = {}
    node._paths = {}
    node._written = {}
    node._write_failures = {}
    node._summarized = set()
    node.get_logger = Mock(return_value=Mock())
    return node


def test_report_preserves_retry_attempts_and_observed_durations() -> None:
    """Failed attempts remain visible even after an eventual successful retry."""
    report = MissionReport('mission-a')
    report.ingest(event('mission_started', wall_time=100.0), 'status')
    report.ingest({'mission_id': 'mission-a', 'source': 'fallback', 'actions': [
        {'action': 'find', 'target': 'cup'}]}, 'plan')
    for attempt, result, duration in ((1, 'failed', 5.0), (2, 'succeeded', 2.5)):
        report.ingest(event('action_finished', action='find', target='cup', step=0,
                            action_id=f'0:{attempt}', attempt=attempt, result=result,
                            duration_s=duration, wall_time=105.0 + attempt,
                            error_reason='acquisition_timeout' if result == 'failed' else None),
                      'status')
    report.ingest(event('mission_finished', state='DONE', success=True, duration_s=8.0,
                        wall_time=108.0, retry_count=1), 'status')
    text = report.render_text()
    assert 'Planner: fallback' in text
    assert 'attempt 1: find cup -> FAILED (5.00 s)' in text
    assert 'attempt 2: find cup -> SUCCEEDED (2.50 s)' in text
    assert 'Retry count observed: 1' in text
    assert 'Duration: 8.00 s' in text
    assert report.terminal


def test_late_action_start_does_not_erase_completion() -> None:
    """Cross-topic or delayed telemetry cannot turn a completed attempt into pending."""
    report = MissionReport('mission-a')
    report.ingest(event('action_finished', action_id='0:1', action='navigate', target='home',
                        step=0, attempt=1, result='failed', duration_s=3.0,
                        error_reason='navigation status 6', wall_time=103.0), 'status')
    report.ingest(event('action_started', action_id='0:1', action='navigate', target='home',
                        step=0, attempt=1, duration_s=0.0, wall_time=100.0), 'status')
    assert len(report.attempts) == 1
    attempt = report.attempts['0:1']
    assert attempt.result == 'failed'
    assert attempt.duration_s == 3.0
    assert attempt.started_wall == 100.0
    assert '2D Pose Estimate' in report.render_text()
    assert 'navigation status 6' in report.render_text()
    assert 'navigation status 6' not in report.render_text(include_technical=False)


def test_terminal_before_plan_accepts_late_details() -> None:
    """Completion does not prevent a late plan/start event from enriching the report."""
    report = MissionReport('mission-a')
    report.ingest(event('mission_finished', state='DONE', wall_time=110.0), 'status')
    report.ingest(event('mission_started', wall_time=100.0), 'status')
    report.ingest({'mission_id': 'mission-a', 'planner': 'llm', 'command': 'pick up cup',
                   'actions': [{'action': 'find', 'target': 'cup'}, {'action': 'grasp'}]}, 'plan')
    text = report.render_text()
    assert 'Duration: 10.00 s' in text
    assert 'Planner: llm' in text
    assert '1. find cup' in text
    assert '2. grasp' in text
    assert 'Object holding: not verified' in text


@pytest.mark.parametrize('state', ['WAIT_NAV', 'DONE', 'FAILED'])
def test_queued_acknowledgements_are_never_terminal(state: str) -> None:
    """A queued command cannot inherit the active mission's terminal state.

    Args:
        state: State copied into a queued acknowledgement by an older producer.
    """
    report = MissionReport('mission-a')
    report.ingest(event('', detail='queued', state=state), 'status')
    assert not report.terminal
    assert 'INCOMPLETE' in report.render_text()


def test_malformed_terminal_does_not_invent_success() -> None:
    """An event label alone is insufficient to declare mission completion."""
    report = MissionReport('mission-a')
    report.ingest(event('mission_finished'), 'status')
    assert not report.terminal
    assert report.result == 'pending'


def test_unrelated_messages_do_not_mutate_report() -> None:
    """Mission identity and source remain necessary for observational updates."""
    report = MissionReport('mission-a')
    assert not report.ingest({'mission_id': 'other', 'command': 'wrong'}, 'plan')
    assert not report.ingest(event('mission_finished', state='DONE'), 'camera')
    assert not report.command


def test_stop_reports_control_without_claiming_llm_planning() -> None:
    """Stop acknowledgements work without a plan or mission-start message."""
    report = MissionReport('mission-a')
    report.ingest(event('mission_finished', command='stop', planner='llm', state='DONE',
                        duration_s=0.0), 'status')
    assert report.terminal
    assert report.planner == 'control (no LLM planning)'
    assert 'Duration: 0.00 s' in report.render_text()


def test_report_rejects_terminal_escape_injection() -> None:
    """Plain text remains readable when commands/errors contain control characters."""
    report = MissionReport('mission-a')
    report.ingest(event('mission_finished', command='find\ncup\x1b[2J', state='FAILED',
                        error_reason='bad\rmeasurement\x1b[31m'), 'status')
    text = report.render_text()
    assert '\x1b' not in text
    assert '\r' not in text
    assert 'Command: find cup' in text


def test_report_path_is_safe_and_collision_resistant(tmp_path: Path) -> None:
    """External IDs cannot create paths outside results or overwrite an existing report.

    Args:
        tmp_path: Isolated results directory.
    """
    first = report_path(tmp_path, '../../mission/strange', timestamp=100.123456)
    assert first.parent == tmp_path
    assert '19700101T000140_123456Z' in first.name
    first.write_text('existing report')
    second = report_path(tmp_path, '../../mission/strange', timestamp=100.123456)
    assert second != first
    assert first.read_text() == 'existing report'


def test_atomic_report_update_leaves_only_final_text(tmp_path: Path) -> None:
    """Late evidence replaces the same complete UTF-8 artifact without temporary debris.

    Args:
        tmp_path: Isolated results directory.
    """
    path = tmp_path / 'nested' / 'mission.txt'
    write_report(path, 'First summary\n')
    write_report(path, 'Updated summary: café\n')
    assert path.read_text(encoding='utf-8') == 'Updated summary: café\n'
    assert list(path.parent.iterdir()) == [path]


def test_reporter_grace_collects_plan_then_late_updates_without_resummary(
        reporter: MissionReporter, monkeypatch: pytest.MonkeyPatch) -> None:
    """The first summary waits for late DDS evidence; subsequent evidence updates its file.

    Args:
        reporter: Reporter with mocked logger and no active ROS participant.
        monkeypatch: Fixture controlling wall-independent grace timing.
    """
    clock = [10.0]
    monkeypatch.setattr(time, 'monotonic', lambda: clock[0])
    reporter._on_status(message(event('mission_finished', state='DONE', duration_s=3.0)))
    reporter._flush()
    assert not list(reporter._base.glob('mission_*.txt'))
    reporter._on_plan(message({'mission_id': 'mission-a', 'planner': 'llm', 'actions': [
        {'action': 'find', 'target': 'cup'}]}))
    clock[0] = 11.0
    reporter._flush()
    files = list(reporter._base.glob('mission_*.txt'))
    assert len(files) == 1
    assert 'Planner: llm' in files[0].read_text()
    count = reporter.get_logger().info.call_count
    reporter._on_status(message(event('action_finished', action_id='0:1', action='find',
                                      target='cup', attempt=1, step=0, result='succeeded',
                                      duration_s=2.0)))
    clock[0] = 12.0
    reporter._flush()
    assert reporter.get_logger().info.call_count == count
    assert 'SUCCEEDED (2.00 s)' in files[0].read_text()
    assert list(reporter._base.glob('mission_*.txt')) == files


def test_queued_only_evidence_does_not_allocate_cache(reporter: MissionReporter) -> None:
    """Abandoned queued commands cannot fill the report retention limit.

    Args:
        reporter: Reporter with a bounded observational cache.
    """
    for index in range(200):
        reporter._on_status(message(event('', mission_id=f'queued-{index}', detail='queued',
                                          state='DONE')))
    assert not reporter._reports
    assert not reporter._pending
    assert not list(reporter._base.iterdir())


def test_reporter_write_retry_recovers_without_reprinting_summary(
        reporter: MissionReporter, monkeypatch: pytest.MonkeyPatch) -> None:
    """A transient filesystem failure gets a bounded retry and one terminal summary.

    Args:
        reporter: Reporter with captured logging.
        monkeypatch: Fixture simulating one temporary write failure and elapsed time.
    """
    from eira_brain import mission_reporter as module
    clock = [10.0]
    monkeypatch.setattr(time, 'monotonic', lambda: clock[0])
    writer = Mock(side_effect=[PermissionError('temporarily unwritable'), None])
    monkeypatch.setattr(module, 'write_report', writer)
    reporter._on_status(message(event('mission_finished', state='DONE')))
    clock[0] = 11.0
    reporter._flush()
    assert reporter._pending['mission-a'] == 13.0
    summary_count = sum('E-AIRA MISSION SUMMARY' in call.args[0]
                        for call in reporter.get_logger().info.call_args_list)
    clock[0] = 13.0
    reporter._flush()
    assert writer.call_count == 2
    assert 'mission-a' in reporter._written
    assert 'mission-a' not in reporter._pending
    assert summary_count == sum('E-AIRA MISSION SUMMARY' in call.args[0]
                                for call in reporter.get_logger().info.call_args_list) == 1


def test_reporter_permanent_write_failure_has_finite_retry_budget(
        reporter: MissionReporter, monkeypatch: pytest.MonkeyPatch) -> None:
    """Persistent permission errors cannot produce an infinite retry/log loop.

    Args:
        reporter: Reporter with two additional write attempts configured.
        monkeypatch: Fixture forcing a filesystem error and advancing grace time.
    """
    from eira_brain import mission_reporter as module
    clock = [10.0]
    monkeypatch.setattr(time, 'monotonic', lambda: clock[0])
    writer = Mock(side_effect=PermissionError('read-only storage'))
    monkeypatch.setattr(module, 'write_report', writer)
    reporter._on_status(message(event('mission_finished', state='FAILED', error_reason='bad IK')))
    for when in (11.0, 13.0, 15.0, 17.0):
        clock[0] = when
        reporter._flush()
    assert writer.call_count == 3
    assert not reporter._pending
    assert 'mission-a' not in reporter._written
    assert reporter.get_logger().warning.call_count == 3


@pytest.mark.parametrize('payload', [[], None, 'text', {'mission_id': ''}])
def test_malformed_topic_messages_are_ignored(
        reporter: MissionReporter, payload: object) -> None:
    """Malformed or uncorrelated evidence cannot create a mission or crash reporting.

    Args:
        reporter: Reporter without any accepted mission.
        payload: Invalid topic shape.
    """
    reporter._on_status(message(payload))
    assert not reporter._reports


def test_shutdown_flushes_terminal_but_not_unfinished_mission(
        reporter: MissionReporter) -> None:
    """Immediate flush does not turn unfinished missions into failures.

    Args:
        reporter: Reporter with one incomplete and one terminal observation.
    """
    reporter._on_status(message(event('mission_started', wall_time=100.0)))
    reporter._on_status(message(event('mission_finished', mission_id='terminal', state='DONE')))
    reporter._flush(force=True)
    assert len(list(reporter._base.glob('mission_*.txt'))) == 1
    assert not reporter._reports['mission-a'].terminal
