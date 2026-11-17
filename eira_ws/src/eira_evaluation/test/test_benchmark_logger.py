"""Mocked ROS integration tests for serial benchmarking and mission persistence.

Author: E-AIRA maintainers.
Hardware target: hardware-free ROSMASTER M3 Pro / Jetson Orin NX evaluation tests.
"""

import argparse
import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from std_msgs.msg import String

from eira_evaluation.benchmark import BenchmarkRunner, command_envelope, run_trials
from eira_evaluation.mission_logger import MissionLogger
from eira_evaluation.records import MissionAccumulator
from test_records import completed_mission


class FakeRunner:
    """Simulate actual outcomes without any ROS node or actuator publication."""

    def __init__(self, outcomes: list[str], stop_confirmed: bool = True) -> None:
        """Set deterministic mission outcomes for a serial runner.

        Args:
            outcomes: Wait results consumed in publish order.
            stop_confirmed: Whether the synthetic stop handshake succeeds.
        """
        self.accumulator = MissionAccumulator()
        self.sent: list[dict] = []
        self.outcomes = outcomes
        self.stops = 0
        self.saved = 0
        self.stop_confirmed = stop_confirmed
        self._rejections: dict[str, str] = {}

    def send(self, envelope: dict) -> str:
        """Capture a correlated command and create its observed record."""
        self.sent.append(envelope)
        identity = envelope['mission_id']
        self.accumulator.ingest('command', envelope, 100)
        self.accumulator.records[identity]['success'] = True
        return identity

    def wait(self, identity: str, _timeout_s: float) -> str:
        """Return the next predetermined completion result."""
        result = self.outcomes.pop(0)
        self.accumulator.records[identity]['success'] = result == 'done'
        return result

    def stop_and_confirm(self, _experiment: str, _iteration: int, _timeout: float) -> bool:
        """Count stop requests and return the supplied acknowledgement outcome."""
        self.stops += 1
        return self.stop_confirmed

    def finish_timeout(self, identity: str, reason: str) -> None:
        """Record a benchmark-level failure without manufacturing a success."""
        self.accumulator.records[identity].update(success=False, error_reason=reason)

    def persist(self) -> None:
        """Count requested archive commits."""
        self.saved += 1


def options(iterations: int = 2) -> argparse.Namespace:
    """Provide deterministic runner options without parsing process arguments.

    Args:
        iterations: Requested number of trials.
    Returns:
        Minimal benchmark option namespace.
    """
    return argparse.Namespace(iterations=iterations, skip_reset=False, start_waypoint='home',
                              command='find cup', reset_timeout=10, timeout=20, stop_timeout=5,
                              environment='hardware', seed=-1)


def test_reset_envelope_is_a_grounded_navigation_purpose() -> None:
    """Benchmark setup cannot depend on an LLM inventing the reset sequence."""
    envelope = command_envelope('', 'm', 'exp', 'reset', 0, 'home')
    assert envelope['purpose'] == 'benchmark_reset'
    assert envelope['start_waypoint'] == 'home'
    assert envelope['phase'] == 'reset'


def test_each_trial_is_preceded_by_a_confirmed_reset() -> None:
    """The reset and trial sequences never overlap or share correlation IDs."""
    node = FakeRunner(['done', 'done', 'done', 'failed'])
    context = run_trials(node, options(), 'exp')
    assert [item['phase'] for item in node.sent] == ['reset', 'trial', 'reset', 'trial']
    assert len({item['mission_id'] for item in node.sent}) == 4
    assert context['completed_iterations'] == 2
    assert not context['abort_reason']


def test_failed_reset_aborts_before_trial_command() -> None:
    """No task is issued from an unconfirmed start pose."""
    node = FakeRunner(['failed'])
    context = run_trials(node, options(), 'exp')
    assert [item['phase'] for item in node.sent] == ['reset']
    assert context['trial_ids'] == []
    assert context['abort_reason'] == 'start-pose reset failed'


def test_timeout_stops_and_never_starts_another_trial() -> None:
    """Even an acknowledged timeout stop does not silently resume the campaign."""
    node = FakeRunner(['done', 'timed_out'])
    context = run_trials(node, options(20), 'exp')
    assert node.stops == 1
    assert len(context['trial_ids']) == 1
    assert context['stop_confirmed'] is True
    assert context['abort_reason']


def test_unacknowledged_stop_is_reported() -> None:
    """A failed stop handshake remains visible instead of authorizing more motion."""
    node = FakeRunner(['timed_out'], stop_confirmed=False)
    context = run_trials(node, options(), 'exp')
    assert context['stop_confirmed'] is False
    assert not context['trial_ids']


def test_wait_ignores_unrelated_terminal_state(monkeypatch: pytest.MonkeyPatch) -> None:
    """An unrelated DONE does not complete the requested benchmark mission."""
    node = object.__new__(BenchmarkRunner)
    node.accumulator = MissionAccumulator([completed_mission()])
    node._rejections = {}
    monkeypatch.setattr('eira_evaluation.benchmark.rclpy.ok', lambda: True)
    times = iter([0.0, 0.0, 2.0])
    monkeypatch.setattr('eira_evaluation.benchmark.time.monotonic', lambda: next(times))
    spin = Mock()
    monkeypatch.setattr('eira_evaluation.benchmark.rclpy.spin_once', spin)
    assert node.wait('different-mission', 1.0) == 'timed_out'
    spin.assert_called_once()


def test_stop_requires_new_zero_and_matching_control_ack(monkeypatch: pytest.MonkeyPatch) -> None:
    """A control DONE and fresh zero command are both necessary evidence."""
    node = object.__new__(BenchmarkRunner)
    node.accumulator = MissionAccumulator()
    node._zero_received_at = -1.0

    def send(envelope: dict) -> str:
        """Return an acknowledged stop whose zero velocity arrived after publication."""
        identity = envelope['mission_id']
        node.accumulator.ingest('status', {'mission_id': identity, 'state': 'DONE'}, 1)
        node._zero_received_at = 1.0
        return identity
    node.send = send
    monkeypatch.setattr('eira_evaluation.benchmark.rclpy.ok', lambda: True)
    monkeypatch.setattr('eira_evaluation.benchmark.time.monotonic', lambda: 0.0)
    assert node.stop_and_confirm('exp', 0, 1) is True


def test_logger_callback_records_environment_and_retries_flush() -> None:
    """An archive failure stays dirty for a later retry rather than dropping evidence."""
    node = object.__new__(MissionLogger)
    node.accumulator = MissionAccumulator()
    node.archive = Mock()
    node._dirty = False
    node.get_parameter = Mock(side_effect=lambda name: SimpleNamespace(value={
        'environment': 'simulation_oracle', 'random_seed': 42}[name]))
    node.get_logger = Mock(return_value=Mock())
    node._callback('command')(String(data=json.dumps({'mission_id': 'm', 'command': 'find cup'})))
    assert node.accumulator.records['m']['environment'] == 'simulation_oracle'
    node.archive.save.side_effect = OSError('temporarily unavailable')
    node._flush()
    assert node._dirty is True
    node.archive.save.side_effect = None
    node._flush()
    assert node._dirty is False


def test_operator_truth_updates_existing_unknown_contact() -> None:
    """A verified post-mission label can establish actual held/not-held accuracy."""
    node = object.__new__(MissionLogger)
    node.accumulator = MissionAccumulator([completed_mission()])
    node._dirty = False
    node.archive = Mock()
    node.get_logger = Mock(return_value=Mock())
    node._truth(String(data=json.dumps({'mission_id': 'm1', 'action_id': '1:1',
                                       'object_held': True, 'source': 'operator video review'})))
    assert node.accumulator.records['m1']['grasp_outcomes'][0]['object_held'] is True
    node.archive.save.assert_called_once()


def test_wait_drains_plan_evidence_arriving_after_done(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cross-topic reordering cannot turn a completed reset into a spurious failure."""
    node = object.__new__(BenchmarkRunner)
    node.accumulator = MissionAccumulator()
    node.accumulator.ingest('command', {'mission_id': 'reset', 'command': 'reset'}, 100)
    node._rejections = {}
    node.event_grace_s = 0.2
    clock = iter(index*0.05 for index in range(50))
    monkeypatch.setattr('eira_evaluation.benchmark.time.monotonic', lambda: next(clock))
    monkeypatch.setattr('eira_evaluation.benchmark.rclpy.ok', lambda: True)
    calls = []

    def spin(_node: BenchmarkRunner, timeout_sec: float) -> None:
        """Deliver terminal status before delayed plan/action evidence.

        Args:
            _node: Runner being observed.
            timeout_sec: Unused simulated wait.
        """
        calls.append(timeout_sec)
        if len(calls) == 1:
            node.accumulator.ingest('status', {
                'mission_id': 'reset', 'state': 'DONE', 'step': 1, 'total': 1}, 102)
        elif len(calls) == 2:
            record = completed_mission()
            record['mission_id'] = 'reset'
            node.accumulator.records['reset'] = record
    monkeypatch.setattr('eira_evaluation.benchmark.rclpy.spin_once', spin)
    assert node.wait('reset', 1.0) == 'done'
    assert len(calls) >= 2
    assert node.accumulator.records['reset']['success'] is True
