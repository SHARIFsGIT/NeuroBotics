"""Accumulate correlated mission evidence without assuming physical grasp success.

Author: E-AIRA maintainers.
Hardware target: ROSMASTER M3 Pro / Jetson Orin NX, ROS 2 Humble / Python 3.10.
"""

from copy import deepcopy
from datetime import datetime, timezone
import json
import math
from typing import Any

SCHEMA_VERSION = 1
TOPICS = ('command', 'plan', 'status', 'vision', 'manipulation')
CSV_FIELDS = (
    'schema_version', 'mission_id', 'timestamp', 'start_time', 'end_time', 'duration_s',
    'command', 'planner', 'planner_reason', 'planning_latency_ms',
    'llm_response_ms', 'llm_attempts',
    'phase', 'experiment_id', 'iteration', 'environment', 'random_seed',
    'terminal_state', 'success',
    'evaluation_eligible', 'completed_actions', 'total_actions', 'error_reason',
    'action_results', 'perception_latencies_ms', 'grasp_outcomes', 'recovery_events',
    'benchmark_timed_out',
)


def finite_number(value: Any) -> float | None:
    """Return a finite numeric value without coercing booleans.

    Args:
        value: Potential measurement.
    Returns:
        Finite float or None for unavailable measurements.
    """
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return None
    try:
        value = float(value)
    except OverflowError:
        return None
    return value if math.isfinite(value) else None


def clean_json(value: Any) -> Any:
    """Normalize nonfinite values before writing strict JSON.

    Args:
        value: JSON-compatible nested value.
    Returns:
        Copy with nonfinite floats replaced by null.
    """
    if isinstance(value, dict):
        return {str(key): clean_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean_json(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def decode_payload(payload: str | dict[str, Any]) -> dict[str, Any] | None:
    """Accept JSON objects and legacy plain commands without accepting scalar events.

    Args:
        payload: Incoming String data or already decoded object.
    Returns:
        Decoded object, a legacy command envelope, or None.
    """
    if isinstance(payload, dict):
        return clean_json(payload)
    if not isinstance(payload, str):
        return None
    try:
        data = json.loads(payload)
    except (json.JSONDecodeError, TypeError):
        return {'command': payload, 'legacy': True}
    return clean_json(data) if isinstance(data, dict) else None


def csv_record(record: dict[str, Any]) -> dict[str, Any]:
    """Flatten one mission into stable, header-addressed CSV columns.

    Args:
        record: Detailed mission evidence.
    Returns:
        Dictionary restricted to the published CSV schema.
    """
    result = {key: record.get(key) for key in CSV_FIELDS}
    for key in ('action_results', 'perception_latencies_ms', 'grasp_outcomes', 'recovery_events'):
        result[key] = json.dumps(record.get(key, []), allow_nan=False, separators=(',', ':'))
    return result


class MissionAccumulator:
    """Correlate out-of-order ROS messages and retain an auditable event trace."""

    def __init__(self, records: list[dict[str, Any]] | None = None) -> None:
        """Restore records without marking still-running missions as failures.

        Args:
            records: Prior JSON snapshot records, if available.
        """
        self.records = {str(record['mission_id']): deepcopy(record) for record in records or []}
        self.unmatched_commands: list[dict[str, Any]] = []
        self.rejected_events = 0
        self._seen: dict[str, set[str]] = {}
        for mission_id, record in self.records.items():
            self._seen[mission_id] = {
                json.dumps([entry['topic'], entry['payload']], sort_keys=True, allow_nan=False)
                for entry in record.get('events', [])}

    def _mission(self, identity: str, stamp: float) -> dict[str, Any]:
        """Get or create a record for an explicit mission identity.

        Args:
            identity: Nonempty mission ID.
            stamp: First observed event time in Unix seconds.
        Returns:
            Mutable mission record.
        """
        if identity not in self.records:
            self.records[identity] = {
                'schema_version': SCHEMA_VERSION, 'mission_id': identity,
                'timestamp': datetime.fromtimestamp(stamp, timezone.utc).isoformat(),
                'start_time': stamp, 'end_time': None, 'duration_s': None,
                'command': '', 'planner': 'unknown', 'planner_reason': '',
                'planning_latency_ms': None, 'llm_response_ms': None, 'llm_attempts': None,
                'phase': 'mission', 'experiment_id': '', 'iteration': None,
                'terminal_state': '', 'success': None, 'evaluation_eligible': True,
                'completed_actions': 0, 'total_actions': 0, 'error_reason': '',
                'actions': [], 'action_results': [], 'perception_latencies_ms': [],
                'grasp_outcomes': [], 'recovery_events': [], 'events': [],
                'benchmark_timed_out': False,
            }
            self._seen[identity] = set()
        return self.records[identity]

    def ingest(self, topic: str, payload: str | dict[str, Any], received_at: float) -> str | None:
        """Ingest one event, preserving receive and producer timestamps separately.

        Args:
            topic: Logical topic key: command, plan, status, vision, manipulation.
            payload: Message String or decoded JSON object.
            received_at: Receiver wall time; used when producer time is unavailable.
        Returns:
            Affected mission ID, or None for unmatched/unusable input.
        Raises:
            ValueError: If the logical topic or receipt timestamp is invalid.
        """
        if topic not in TOPICS or finite_number(received_at) is None:
            raise ValueError('invalid topic or receipt timestamp')
        data = decode_payload(payload)
        if data is None or (data.get('legacy') and topic != 'command'):
            self.rejected_events += 1
            return None
        stamp = finite_number(data.get('wall_time'))
        stamp = received_at if stamp is None else stamp
        try:
            datetime.fromtimestamp(stamp, timezone.utc)
        except (OverflowError, OSError, ValueError) as exc:
            raise ValueError('event timestamp is outside the supported calendar') from exc
        identity = str(data.get('mission_id') or '')
        if not identity:
            if topic == 'command' and isinstance(data.get('command'), str):
                self.unmatched_commands.append({'received_at': received_at, **data})
            else:
                self.rejected_events += 1
            return None
        record = self._mission(identity, stamp)
        fingerprint = json.dumps([topic, data], sort_keys=True, allow_nan=False)
        if fingerprint in self._seen[identity]:
            return identity
        self._seen[identity].add(fingerprint)
        record['events'].append({'topic': topic, 'received_at': received_at,
                                 'producer_time': stamp, 'payload': deepcopy(data)})
        record['start_time'] = min(record['start_time'], stamp)
        record['timestamp'] = datetime.fromtimestamp(
            record['start_time'], timezone.utc).isoformat()
        if isinstance(data.get('command'), str):
            record['command'] = data['command']
            for pending in self.unmatched_commands:
                if pending.get('command') == data['command']:
                    record['command_received_at'] = pending['received_at']
                    self.unmatched_commands.remove(pending)
                    break
        if topic == 'command':
            for name in ('phase', 'experiment_id', 'iteration'):
                if name in data:
                    record[name] = data[name]
        elif topic == 'plan':
            actions = data.get('actions')
            if isinstance(actions, list) and all(isinstance(item, dict) for item in actions):
                record['actions'] = deepcopy(actions)
                record['total_actions'] = len(actions)
            record['planner'] = str(data.get('source', data.get('planner', 'unknown')))
            record['planner_reason'] = str(data.get('planner_reason', data.get('reason', '')))
            if isinstance(data.get('llm_attempts'), int) and data['llm_attempts'] >= 0:
                record['llm_attempts'] = data['llm_attempts']
            if data.get('benchmark_reset') is True or record['planner'] == 'benchmark_reset':
                record['phase'] = 'reset'
            for name in ('planning_latency_ms', 'llm_response_ms'):
                value = finite_number(data.get(name))
                record[name] = value if value is not None and value >= 0 else None
        elif topic == 'status':
            self._status(record, data, stamp)
        elif topic == 'vision':
            self._vision(record, data, stamp)
        else:
            self._manipulation(record, data, stamp)
        self._derive(record)
        return identity

    def _action(self, record: dict[str, Any], data: dict[str, Any]) -> dict[str, Any] | None:
        """Find an attempt by action ID without conflating retries.

        Args:
            record: Mission record.
            data: Structured action event.
        Returns:
            Existing/new attempt, or None without an action identity.
        """
        identity = str(data.get('action_id') or '')
        if not identity:
            return None
        for action in record['action_results']:
            if action['action_id'] == identity:
                return action
        step = data.get('step')
        if not isinstance(step, int) or isinstance(step, bool):
            try:
                step = int(identity.split(':')[0])
            except ValueError:
                step = None
        action = {'action_id': identity, 'step': step, 'action': str(data.get('action', '')),
                  'attempt': data.get('attempt'), 'start_time': None, 'end_time': None,
                  'duration_s': None, 'success': None, 'error_reason': ''}
        record['action_results'].append(action)
        return action

    def _status(self, record: dict[str, Any], data: dict[str, Any], stamp: float) -> None:
        """Consume canonical execution telemetry and terminal mission states.

        Args:
            record: Mission record.
            data: Brain status object.
            stamp: Producer event time.
        """
        event = data.get('event', '')
        if data.get('planner') in ('llm', 'fallback'):
            record['planner'] = data['planner']
        if event == 'mission_started' or data.get('state') == 'PLANNING':
            record['planning_started_at'] = min(record.get('planning_started_at', stamp), stamp)
        if event in ('action_started', 'action_finished'):
            action = self._action(record, data)
            if action is not None:
                action['action'] = str(data.get('action') or action['action'])
                if event == 'action_started':
                    action['start_time'] = stamp
                else:
                    action['end_time'] = stamp
                    action['success'] = data.get('success') if isinstance(
                        data.get('success'), bool) else None
                    action['error_reason'] = str(data.get('error_reason') or '')
                    duration = finite_number(data.get('duration_s'))
                    if duration is not None and duration >= 0:
                        action['duration_s'] = duration
                    elif action['start_time'] is not None:
                        action['duration_s'] = max(0.0, stamp-action['start_time'])
        if event == 'recovery' or data.get('state') == 'SCAN' or str(
                data.get('detail', '')).startswith('retrying:'):
            recovery = {'action_id': str(data.get('action_id') or ''),
                        'step': data.get('step'), 'time': stamp,
                        'kind': data.get('recovery_kind') or (
                            'scan' if data.get('state') == 'SCAN' else 'retry'),
                        'reason': data.get('recovery_reason', data.get('detail', ''))}
            # Status transitions can describe the same recovery twice.
            if not any(item['action_id'] == recovery['action_id'] and item['kind'] == recovery[
                    'kind'] and item['time'] == stamp for item in record['recovery_events']):
                record['recovery_events'].append(recovery)
        if data.get('state') in ('DONE', 'FAILED'):
            record['terminal_state'] = data['state']
            record['end_time'] = stamp
            record['reported_success'] = data['state'] == 'DONE'
            if data['state'] == 'FAILED':
                record['error_reason'] = str(data.get('error_reason') or data.get('detail') or
                                             'mission failed')

    def _vision(self, record: dict[str, Any], data: dict[str, Any], stamp: float) -> None:
        """Measure search-to-found latency only with a matching search identity.

        Args:
            record: Mission record.
            data: Vision event.
            stamp: Event timestamp.
        """
        identity = str(data.get('action_id') or '')
        event = data.get('event')
        if event in ('searching', 'search_started'):
            record.setdefault('search_starts', {})[identity] = stamp
        if event != 'found' or not identity:
            return
        record.setdefault('found_times', {})[identity] = stamp
        starts = [a['start_time'] for a in record['action_results']
                  if a['action_id'] == identity and a['action'] == 'find'
                  and a['start_time'] is not None]
        start = record.get('search_starts', {}).get(identity, min(starts) if starts else None)
        if start is not None and stamp >= start and not any(
                item['action_id'] == identity for item in record['perception_latencies_ms']):
            record['perception_latencies_ms'].append(
                {'action_id': identity, 'latency_ms': (stamp - start) * 1000.0})

    def _manipulation(self, record: dict[str, Any], data: dict[str, Any], stamp: float) -> None:
        """Record verified physical outcomes separately from sequencer completion.

        Args:
            record: Mission record.
            data: Manipulation event.
            stamp: Producer timestamp.
        """
        if data.get('event') != 'grasped':
            return
        identity = str(data.get('action_id') or '')
        held = data.get('object_held', data.get('grasp_success'))
        verified = data.get('object_contact_verified') is True and isinstance(held, bool)
        outcome = {'action_id': identity, 'time': stamp, 'verified': verified,
                   'object_held': held if verified else None,
                   'evidence': data.get('contact_evidence', 'unspecified')}
        for index, previous in enumerate(record['grasp_outcomes']):
            if previous['action_id'] == identity:
                if verified:
                    record['grasp_outcomes'][index] = outcome
                return
        record['grasp_outcomes'].append(outcome)

    def _derive(self, record: dict[str, Any]) -> None:
        """Derive completeness without assuming DONE means all actions were observed.

        Args:
            record: Mutable mission evidence.
        """
        for action in record['action_results']:
            if (action.get('duration_s') is None and action.get('start_time') is not None
                    and action.get('end_time') is not None):
                action['duration_s'] = max(0.0, action['end_time']-action['start_time'])
            identity = action['action_id']
            found = record.get('found_times', {}).get(identity)
            if (action.get('action') == 'find' and action.get('start_time') is not None
                    and found is not None and found >= action['start_time'] and not any(
                        item['action_id'] == identity
                        for item in record['perception_latencies_ms'])):
                record['perception_latencies_ms'].append({
                    'action_id': identity, 'latency_ms': (found-action['start_time'])*1000.0})
        successful = {action['step'] for action in record['action_results']
                      if action.get('success') is True and action.get('step') is not None}
        record['completed_actions'] = len(successful)
        if record['end_time'] is not None:
            record['duration_s'] = max(0.0, record['end_time'] - record['start_time'])
        control = record['command'].strip().lower() in ('stop', 'halt', 'cancel', 'abort')
        task_actions = [item for item in record['actions'] if item.get('action') not in
                        ('stop', 'speak')]
        record['evaluation_eligible'] = record['phase'] not in ('reset', 'control') and not control
        if record['phase'] != 'trial' and record['actions'] and not task_actions:
            record['evaluation_eligible'] = False
        if record['terminal_state']:
            complete = record['total_actions'] > 0 and record['completed_actions'] == record[
                'total_actions']
            record['success'] = bool(record.get('reported_success') and complete and task_actions
                                     and not record.get('benchmark_timed_out'))
            if record['success'] and record['error_reason'] in (
                    'no_task_actions', 'action_completion_evidence_missing'):
                record['error_reason'] = ''
            if record.get('reported_success') and not record['success'] and not record[
                    'error_reason']:
                record['error_reason'] = 'no_task_actions' if not task_actions else (
                    'action_completion_evidence_missing')

    def snapshot(self) -> list[dict[str, Any]]:
        """Return deterministic deep copies suitable for strict JSON persistence.

        Returns:
            Records ordered by start time and mission identity.
        """
        return deepcopy(sorted(self.records.values(), key=lambda item: (
            item['start_time'], item['mission_id'])))
