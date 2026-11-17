"""Regression tests for correlated, out-of-order mission evidence.

Author: E-AIRA maintainers.
Hardware target: hardware-free ROSMASTER M3 Pro / Jetson Orin NX evaluation tests.
"""

from copy import deepcopy

import pytest

from eira_evaluation.records import MissionAccumulator, csv_record


def event(accumulator: MissionAccumulator, topic: str, stamp: float,
          **fields: object) -> None:
    """Ingest a correlated fixture event.

    Args:
        accumulator: Collector under test.
        topic: Logical input source.
        stamp: Producer and receipt wall time.
        **fields: Fixture event fields.
    """
    accumulator.ingest(topic, {'mission_id': 'm1', 'wall_time': stamp, **fields}, stamp)


def completed_mission() -> dict:
    """Build one completed find/grasp mission with explicit structured evidence.

    Returns:
        Detailed mission record.
    """
    accumulator = MissionAccumulator()
    event(accumulator, 'command', 100.0, command='find and grasp cup', phase='trial')
    event(accumulator, 'status', 100.1, event='mission_started', state='PLANNING')
    event(accumulator, 'plan', 101.0, source='llm', planning_latency_ms=900.0,
          llm_response_ms=850.0, llm_attempts=1,
          actions=[{'action': 'find', 'target': 'cup'}, {'action': 'grasp'}])
    event(accumulator, 'status', 101.1, event='action_started', action_id='0:1', action='find',
          step=0, attempt=1)
    event(accumulator, 'vision', 101.6, event='found', action_id='0:1')
    event(accumulator, 'status', 101.7, event='action_finished', action_id='0:1', action='find',
          step=0, success=True, duration_s=0.6)
    event(accumulator, 'status', 101.8, event='action_started', action_id='1:1', action='grasp',
          step=1, attempt=1)
    event(accumulator, 'manipulation', 103.0, event='grasped', action_id='1:1',
          object_contact_verified=False)
    event(accumulator, 'status', 103.0, event='action_finished', action_id='1:1', action='grasp',
          step=1, success=True, duration_s=1.2)
    event(accumulator, 'status', 103.1, event='mission_finished', state='DONE')
    return accumulator.snapshot()[0]


def test_completed_actions_are_required_for_mission_success() -> None:
    """DONE alone must not masquerade as observed completion of all actions."""
    accumulator = MissionAccumulator()
    event(accumulator, 'plan', 10, actions=[{'action': 'navigate', 'target': 'home'}])
    event(accumulator, 'status', 11, state='DONE')
    assert accumulator.records['m1']['success'] is False
    assert accumulator.records['m1']['error_reason'] == 'action_completion_evidence_missing'


def test_completed_find_grasp_records_latency_and_unknown_contact() -> None:
    """A timed successful sequence remains physically unverified without contact labels."""
    record = completed_mission()
    assert record['success'] is True
    assert record['completed_actions'] == record['total_actions'] == 2
    assert record['duration_s'] == pytest.approx(3.1)
    assert record['perception_latencies_ms'][0]['latency_ms'] == pytest.approx(500.0)
    assert record['grasp_outcomes'][0]['object_held'] is None
    assert record['grasp_outcomes'][0]['verified'] is False


def test_duplicate_events_are_idempotent() -> None:
    """Repeated delivery must not double action counts or perception samples."""
    accumulator = MissionAccumulator([completed_mission()])
    before = deepcopy(accumulator.snapshot())
    data = before[0]['events'][4]
    accumulator.ingest(data['topic'], data['payload'], data['received_at']+5)
    assert accumulator.snapshot() == before


def test_out_of_order_found_and_finished_are_reconciled() -> None:
    """Independent ROS subscriptions may deliver found and finish before start."""
    accumulator = MissionAccumulator()
    event(accumulator, 'vision', 12, event='found', action_id='0:1')
    event(accumulator, 'status', 13, event='action_finished', action_id='0:1', action='find',
          step=0, success=True)
    event(accumulator, 'status', 10, event='action_started', action_id='0:1',
          action='find', step=0)
    event(accumulator, 'status', 14, state='DONE')
    event(accumulator, 'plan', 9, actions=[{'action': 'find', 'target': 'cup'}])
    record = accumulator.records['m1']
    assert record['success'] is True
    assert record['action_results'][0]['duration_s'] == 3
    assert record['perception_latencies_ms'][0]['latency_ms'] == 2000


def test_retries_remain_separate_attempts() -> None:
    """A failed attempt and successful replacement have distinct action IDs."""
    accumulator = MissionAccumulator()
    event(accumulator, 'plan', 1, actions=[{'action': 'navigate', 'target': 'home'}])
    event(accumulator, 'status', 2, event='action_finished', action_id='0:1', action='navigate',
          step=0, success=False, error_reason='blocked', duration_s=1)
    event(accumulator, 'status', 2.1, event='recovery', action_id='0:1', step=0,
          recovery_kind='retry')
    event(accumulator, 'status', 4, event='action_finished', action_id='0:2', action='navigate',
          step=0, success=True, duration_s=1.9)
    event(accumulator, 'status', 5, state='DONE')
    record = accumulator.records['m1']
    assert len(record['action_results']) == 2
    assert record['completed_actions'] == 1
    assert record['success'] is True
    assert len(record['recovery_events']) == 1


def test_verified_annotation_replaces_unknown_grasp_outcome() -> None:
    """Operator contact evidence can arrive after terminal sequencer completion."""
    accumulator = MissionAccumulator([completed_mission()])
    event(accumulator, 'manipulation', 105, event='grasped', action_id='1:1',
          object_contact_verified=True, object_held=False, contact_evidence='operator')
    outcome = accumulator.records['m1']['grasp_outcomes'][0]
    assert outcome['verified'] is True
    assert outcome['object_held'] is False
    assert outcome['evidence'] == 'operator'


def test_reset_and_stop_excluded_from_task_denominator() -> None:
    """Setup navigation and deliberate stop are controls, not task-success trials."""
    accumulator = MissionAccumulator()
    event(accumulator, 'plan', 1, benchmark_reset=True, source='benchmark_reset',
          actions=[{'action': 'navigate', 'target': 'home'}])
    assert accumulator.records['m1']['evaluation_eligible'] is False
    accumulator.ingest('command', {'mission_id': 'stop', 'command': 'stop'}, 1)
    assert accumulator.records['stop']['evaluation_eligible'] is False


def test_unrecognized_trial_acknowledgement_counts_as_failure() -> None:
    """An unsupported task must not become a successful benchmark by speaking."""
    accumulator = MissionAccumulator()
    event(accumulator, 'command', 1, phase='trial', command='unknown task')
    event(accumulator, 'plan', 2, actions=[{'action': 'speak', 'target': 'not understood'}])
    event(accumulator, 'status', 3, event='action_finished', action='speak', action_id='0:1',
          step=0, success=True)
    event(accumulator, 'status', 4, state='DONE')
    assert accumulator.records['m1']['evaluation_eligible'] is True
    assert accumulator.records['m1']['success'] is False


def test_plain_commands_wait_for_real_brain_identity() -> None:
    """Legacy commands are associated only when the Brain supplies an actual ID."""
    accumulator = MissionAccumulator()
    assert accumulator.ingest('command', 'find cup', 1) is None
    assert len(accumulator.unmatched_commands) == 1
    event(accumulator, 'status', 2, command='find cup', state='PLANNING')
    assert accumulator.records['m1']['command_received_at'] == 1
    assert not accumulator.unmatched_commands


def test_malformed_and_nonfinite_evidence_is_normalized() -> None:
    """Malformed roots are rejected and nonfinite metadata never enters strict JSON."""
    accumulator = MissionAccumulator()
    assert accumulator.ingest('vision', '[1,2]', 1) is None
    event(accumulator, 'plan', 2, actions=[], llm_response_ms=float('nan'))
    assert accumulator.records['m1']['llm_response_ms'] is None
    assert csv_record(accumulator.records['m1'])['action_results'] == '[]'


def test_calendar_overflow_is_an_explicit_invalid_event() -> None:
    """Malformed producer timestamps cannot crash an uncontrolled archive write."""
    accumulator = MissionAccumulator()
    with pytest.raises(ValueError):
        accumulator.ingest('status', {'mission_id': 'm', 'wall_time': 1e30}, 1)
