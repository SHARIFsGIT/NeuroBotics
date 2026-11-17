"""Save readable per-mission reports while preserving the structured ROS interfaces.

Author: E-AIRA maintainers.
Hardware target: ROSMASTER M3 Pro / Jetson Orin NX, ROS 2 Humble / Python 3.10.
Reports describe observed controller outcomes; they do not verify object contact.
"""

from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import tempfile
import time
from typing import Any, Mapping

import rclpy
from rclpy.clock import Clock, ClockType
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from std_msgs.msg import String

from eira_brain.console import error_hint, format_line, sanitize_text
from eira_brain.ollama_client import is_stop_command


def _number(value: object) -> float | None:
    """Return a finite nonnegative numeric observation, or None when unavailable.

    Args:
        value: Observed time or duration, never a numeric string or boolean.

    Returns:
        Validated value or None.
    """
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except OverflowError:
        return None
    return number if math.isfinite(number) and number >= 0 else None


def _index(value: object, minimum: int = 0) -> int | None:
    """Read a bounded-schema integer without accepting booleans.

    Args:
        value: Plan step or attempt number.
        minimum: Lowest valid value.

    Returns:
        Valid integer or None.
    """
    return value if isinstance(value, int) and not isinstance(value, bool) and (
        value >= minimum) else None


def _seconds(value: float | None) -> str:
    """Display an observed duration without fabricating missing timing evidence.

    Args:
        value: Duration in seconds, or None.

    Returns:
        Human-readable duration or an explicit unknown label.
    """
    return f'{value:.2f} s' if value is not None else 'not observed'


def _utc(value: float | None) -> str:
    """Render an observed timestamp without accepting out-of-range platform dates.

    Args:
        value: Wall-clock epoch seconds or None.

    Returns:
        UTC date and time, or an explicit unknown label.
    """
    if value is None:
        return 'not observed'
    try:
        return datetime.fromtimestamp(value, timezone.utc).isoformat()
    except (OverflowError, OSError, ValueError):
        return 'not observed (invalid timestamp)'


@dataclass
class ActionAttempt:
    """Hold one action attempt, including failed attempts followed by recovery.

    Args:
        action_id: Correlation identity supplied by the Brain.
    """

    action_id: str
    action: str = ''
    target: str = ''
    step: int | None = None
    attempt: int | None = None
    started_wall: float | None = None
    ended_wall: float | None = None
    duration_s: float | None = None
    result: str = 'not finished'
    error_reason: str = ''

    def ingest(self, data: Mapping[str, Any], finished: bool) -> None:
        """Merge an action event without letting a late start erase its completion.

        Args:
            data: Structured Brain action event.
            finished: Whether this is an action-finished event.
        """
        for name in ('action', 'target'):
            value = data.get(name)
            if isinstance(value, str) and value:
                setattr(self, name, value)
        step, attempt = _index(data.get('step')), _index(data.get('attempt'), 1)
        if step is not None:
            self.step = step
        if attempt is not None:
            self.attempt = attempt
        start = _number(data.get('started_wall_time'))
        if start is None and not finished:
            start = _number(data.get('wall_time'))
        if start is not None and self.started_wall is None:
            self.started_wall = start
        if finished:
            if self.ended_wall is None:
                self.ended_wall = _number(data.get('wall_time'))
            duration = _number(data.get('duration_s'))
            if duration is not None:
                self.duration_s = duration
            result = data.get('result')
            if result in ('succeeded', 'failed', 'canceled', 'cancelled'):
                self.result = 'canceled' if result == 'cancelled' else result
            elif isinstance(data.get('success'), bool):
                self.result = 'succeeded' if data['success'] else 'failed'
            self.error_reason = sanitize_text(data.get('error_reason', ''), 0)
        if self.duration_s is None and self.started_wall is not None and (
                self.ended_wall is not None and self.ended_wall >= self.started_wall):
            self.duration_s = self.ended_wall - self.started_wall


@dataclass
class MissionReport:
    """Accumulate a readable mission summary without a ROS context or device access.

    Args:
        mission_id: Exact identity observed on the structured Brain topics.
    """

    mission_id: str
    command: str = ''
    planner: str = ''
    planner_reason: str = ''
    actions: list[dict[str, str]] = field(default_factory=list)
    attempts: dict[str, ActionAttempt] = field(default_factory=dict)
    started_wall: float | None = None
    ended_wall: float | None = None
    duration_s: float | None = None
    result: str = 'pending'
    error_reason: str = ''
    retries: int = 0

    @property
    def terminal(self) -> bool:
        """Return whether an actual terminal observation has been received.

        Returns:
            True only for observed completion, failure or cancellation.
        """
        return self.result in ('succeeded', 'failed', 'canceled')

    def ingest(self, data: Mapping[str, Any], source: str) -> bool:
        """Merge plan/status evidence, including messages delivered after terminal status.

        Args:
            data: Decoded JSON object from a Brain topic.
            source: Either plan or status.

        Returns:
            Whether the rendered report changed; unrelated messages return False.
        """
        if source not in ('plan', 'status') or data.get('mission_id') != self.mission_id:
            return False
        before = self.render_text()
        command = data.get('command')
        if isinstance(command, str) and command:
            self.command = command
        planner = data.get('planner', data.get('source'))
        if isinstance(planner, str) and planner not in ('', 'none'):
            self.planner = planner
        reason = data.get('planner_reason', data.get('reason'))
        if isinstance(reason, str) and reason and reason not in ('planning', 'not planned'):
            self.planner_reason = reason
        if source == 'plan':
            actions = data.get('actions')
            if isinstance(actions, list) and all(isinstance(action, dict) and isinstance(
                    action.get('action'), str) and isinstance(action.get('target', ''), str)
                    for action in actions):
                self.actions = [{'action': action['action'], 'target': action.get('target', '')}
                                for action in actions]
        else:
            event = data.get('event')
            queued = data.get('detail') == 'queued'
            if event == 'mission_started' and not queued:
                stamp = _number(data.get('wall_time'))
                if stamp is not None and self.started_wall is None:
                    self.started_wall = stamp
            if event in ('action_started', 'action_finished') and isinstance(
                    data.get('action_id'), str) and data['action_id']:
                identity = data['action_id']
                attempt = self.attempts.setdefault(identity, ActionAttempt(identity))
                attempt.ingest(data, event == 'action_finished')
            retry_count = _index(data.get('retry_count'))
            if retry_count is None:
                retry_count = _index(data.get('retry_index'))
            if retry_count is not None:
                self.retries = max(self.retries, retry_count)
            terminal = not queued and (event == 'mission_finished' or data.get('state') in (
                'DONE', 'FAILED', 'CANCELED', 'CANCELLED'))
            if terminal and not self.terminal:
                result = data.get('result')
                if result in ('canceled', 'cancelled') or data.get('state') in (
                        'CANCELED', 'CANCELLED'):
                    self.result = 'canceled'
                elif result == 'failed' or data.get('success') is False or (
                        data.get('state') == 'FAILED'):
                    self.result = 'failed'
                elif result == 'succeeded' or data.get('success') is True or (
                        data.get('state') == 'DONE'):
                    self.result = 'succeeded'
                if self.terminal:
                    self.ended_wall = _number(data.get('wall_time'))
                    self.duration_s = _number(data.get('duration_s'))
                    self.error_reason = sanitize_text(data.get('error_reason') or (
                        data.get('detail') if self.result != 'succeeded' else ''), 0)
        if self.command and is_stop_command(self.command):
            self.planner = 'control (no LLM planning)'
        if self.duration_s is None and self.started_wall is not None and (
                self.ended_wall is not None and self.ended_wall >= self.started_wall):
            self.duration_s = self.ended_wall - self.started_wall
        return self.render_text() != before

    def render_text(self, include_technical: bool = True) -> str:
        """Render UTF-8 text with no ANSI sequences and no assumed physical grasp success.

        Args:
            include_technical: Retain exact failure reasons in saved text files.

        Returns:
            Complete operator-readable report ending in a newline.
        """
        labels = {'pending': 'INCOMPLETE (no terminal event observed)',
                  'succeeded': 'COMPLETED (controller-reported)',
                  'failed': 'FAILED', 'canceled': 'CANCELED'}
        lines = ['E-AIRA MISSION SUMMARY', f'Mission: {sanitize_text(self.mission_id, 0)}',
                 f'Command: {sanitize_text(self.command, 0) or "not observed"}',
                 f'Planner: {sanitize_text(self.planner) or "not observed"}',
                 f'Result: {labels[self.result]}', f'Duration: {_seconds(self.duration_s)}',
                 f'Started: {_utc(self.started_wall)}', f'Finished: {_utc(self.ended_wall)}']
        if self.planner_reason:
            note = error_hint(self.planner_reason)
            lines.append('Planning note: ' + note)
            if include_technical and note != sanitize_text(self.planner_reason):
                lines.append('Technical planning note: ' + sanitize_text(self.planner_reason, 0))
        if self.error_reason:
            hint = error_hint(self.error_reason)
            lines.append('Error: ' + hint)
            if include_technical and hint != sanitize_text(self.error_reason):
                lines.append('Technical reason: ' + sanitize_text(self.error_reason, 0))
        lines.append('Plan:')
        for index, action in enumerate(self.actions, 1):
            label = sanitize_text(action['action'] + ' ' + action.get('target', ''))
            lines.append(f'  {index}. {label}')
        if not self.actions:
            lines.append('  Not observed / no actions')
        lines.append('Action attempts:')
        attempts = sorted(self.attempts.values(), key=lambda attempt: (
            attempt.step if attempt.step is not None else len(self.actions),
            attempt.attempt if attempt.attempt is not None else 0, attempt.action_id))
        for action in attempts:
            step = str(action.step + 1) if action.step is not None else '?'
            attempt = str(action.attempt) if action.attempt is not None else '?'
            label = sanitize_text(f'{action.action or "action"} {action.target}')
            lines.append(f'  Step {step}, attempt {attempt}: {label} -> '
                         f'{action.result.upper()} ({_seconds(action.duration_s)})')
            if action.error_reason:
                reason = error_hint(action.error_reason, target=action.target or 'object')
                lines.append('    Reason: ' + reason)
                if include_technical and reason != sanitize_text(action.error_reason):
                    lines.append('    Technical reason: ' + sanitize_text(action.error_reason, 0))
        if not attempts:
            lines.append('  Not observed')
        lines.append(f'Retry count observed: {self.retries}')
        if any(action.get('action') == 'grasp' for action in self.actions) or any(
                attempt.action == 'grasp' for attempt in attempts):
            lines.append('Object holding: not verified by this controller summary.')
        return '\n'.join(lines) + '\n'


def report_path(directory: Path, mission_id: str, timestamp: float | None = None) -> Path:
    """Construct a safe timestamped filename without trusting mission IDs as paths.

    Args:
        directory: Configured results directory.
        mission_id: Correlation identity, included only as a sanitized filename suffix.
        timestamp: Optional wall-clock seconds for deterministic tests.

    Returns:
        New mission text-file path.
    """
    now = time.time() if timestamp is None else timestamp
    stamp = datetime.fromtimestamp(now, timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ')
    suffix = re.sub(r'[^A-Za-z0-9_-]', '_', mission_id)[:40] or 'mission'
    digest = hashlib.sha256(mission_id.encode('utf-8', errors='replace')).hexdigest()[:8]
    candidate = directory / f'mission_{stamp}_{suffix}_{digest}.txt'
    counter = 1
    while candidate.exists():
        candidate = directory / f'mission_{stamp}_{suffix}_{digest}_{counter}.txt'
        counter += 1
    return candidate


def write_report(path: Path, text: str) -> None:
    """Atomically replace one report without leaving partial files or ANSI escapes.

    Args:
        path: Reporter-owned destination filename.
        text: Plain report content generated by MissionReport.render_text.

    Raises:
        OSError: Directory creation or atomic writing fails.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix='.mission-', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8') as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class MissionReporter(Node):
    """Observe Brain evidence and emit one readable report per terminal mission."""

    def __init__(self) -> None:
        """Declare bounded retention and subscribe without changing robot control."""
        super().__init__('mission_reporter')
        defaults = {'results_dir': '~/eira_ws/results', 'terminal_grace_s': 1.0,
                    'flush_period_s': 0.2, 'max_recent_missions': 128,
                    'max_message_chars': 65536, 'write_retries': 2,
                    'write_retry_delay_s': 2.0}
        for name, value in defaults.items():
            self.declare_parameter(name, value)
        self._base = Path(str(self.get_parameter('results_dir').value)).expanduser()
        self._grace = float(self.get_parameter('terminal_grace_s').value)
        period = float(self.get_parameter('flush_period_s').value)
        self._capacity = int(self.get_parameter('max_recent_missions').value)
        self._max_chars = int(self.get_parameter('max_message_chars').value)
        self._write_retries = int(self.get_parameter('write_retries').value)
        self._write_retry_delay = float(self.get_parameter('write_retry_delay_s').value)
        if not math.isfinite(self._grace) or self._grace < 0 or (
                not math.isfinite(period) or period <= 0) or min(
                    self._capacity, self._max_chars) < 1:
            raise ValueError('mission report timing, capacity and message limits are invalid')
        if self._write_retries < 0 or not math.isfinite(self._write_retry_delay) or (
                self._write_retry_delay <= 0):
            raise ValueError('mission report write retry limits are invalid')
        self._reports: OrderedDict[str, MissionReport] = OrderedDict()
        self._pending: dict[str, float] = {}
        self._paths: dict[str, Path] = {}
        self._written: dict[str, str] = {}
        self._write_failures: dict[str, int] = {}
        self._summarized: set[str] = set()
        self.create_subscription(String, '/eira/plan', self._on_plan, 100)
        self.create_subscription(String, '/eira/status', self._on_status, 100)
        self._steady_clock = Clock(clock_type=ClockType.STEADY_TIME)
        self.create_timer(period, self._flush, clock=self._steady_clock)
        self.get_logger().info(format_line('MISSION', f'Reports will be saved to {self._base}'))

    def _on_plan(self, message: String) -> None:
        """Accept one plan message.

        Args:
            message: Existing JSON String plan contract.
        """
        self._ingest(message, 'plan')

    def _on_status(self, message: String) -> None:
        """Accept one status message.

        Args:
            message: Existing JSON String status contract.
        """
        self._ingest(message, 'status')

    def _ingest(self, message: String, source: str) -> None:
        """Bound and reconcile cross-topic evidence before scheduling a report.

        Args:
            message: Encoded Brain message.
            source: plan or status.
        """
        if len(message.data) > self._max_chars:
            return
        try:
            data = json.loads(message.data)
        except json.JSONDecodeError:
            return
        if not isinstance(data, dict) or not isinstance(data.get('mission_id'), str) or not (
                data['mission_id']):
            return
        if source == 'status' and data.get('detail') == 'queued':
            return
        identity = data['mission_id']
        if identity not in self._reports:
            if len(self._reports) >= self._capacity:
                removable = next((key for key in self._reports if key in self._summarized), None)
                if removable is None:
                    removable = next((key for key in self._reports
                                      if key not in self._pending), None)
                    if removable is None:
                        self._flush(force=True)
                        removable = next(iter(self._reports))
                    self.get_logger().warning(format_line(
                        'MISSION', 'Report retention limit reached; oldest cached mission evicted',
                        'warning'))
                self._reports.pop(removable)
                self._paths.pop(removable, None)
                self._written.pop(removable, None)
                self._write_failures.pop(removable, None)
                self._pending.pop(removable, None)
                self._summarized.discard(removable)
            self._reports[identity] = MissionReport(identity)
        report = self._reports[identity]
        changed = report.ingest(data, source)
        if report.terminal and (changed or identity not in self._summarized):
            self._pending.setdefault(identity, time.monotonic() + self._grace)

    def _flush(self, force: bool = False) -> None:
        """Finalize terminal reports after a wall-clock grace interval.

        Args:
            force: Flush known terminal reports immediately during shutdown.
        """
        now = time.monotonic()
        for identity, deadline in list(self._pending.items()):
            if not force and now < deadline:
                continue
            report = self._reports[identity]
            text = report.render_text()
            if identity not in self._paths:
                self._paths[identity] = report_path(self._base, identity)
            path = self._paths[identity]
            had_saved = identity in self._written
            saved_now = False
            retry = False
            if text != self._written.get(identity):
                try:
                    write_report(path, text)
                    self._written[identity] = text
                    self._write_failures.pop(identity, None)
                    saved_now = True
                except OSError as exc:
                    failures = self._write_failures.get(identity, 0) + 1
                    self._write_failures[identity] = failures
                    retry = failures <= self._write_retries
                    self.get_logger().warning(format_line(
                        'MISSION', f'Could not save mission report: {sanitize_text(exc)}',
                        'warning'))
            if identity not in self._summarized:
                level = {'succeeded': 'success', 'failed': 'error', 'canceled': 'warning'}[
                    report.result]
                for index, line in enumerate(report.render_text(
                        include_technical=False).splitlines()):
                    self.get_logger().info(format_line(
                        'MISSION', line, level if index == 0 else 'info'))
                self._summarized.add(identity)
            if saved_now and not had_saved:
                self.get_logger().info(format_line('MISSION', f'Report saved: {path}'))
            if retry and not force:
                self._pending[identity] = now + self._write_retry_delay
            else:
                self._pending.pop(identity, None)

    def destroy_node(self) -> None:
        """Flush observed terminal missions without labeling unfinished ones as failures."""
        self._flush(force=True)
        super().destroy_node()


def main(args: list[str] | None = None) -> None:
    """Run mission reporting alongside the high-level robot nodes.

    Args:
        args: Optional ROS command-line arguments.
    """
    rclpy.init(args=args)
    node = MissionReporter()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
