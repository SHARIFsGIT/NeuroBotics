"""Run serial, reset-separated benchmark trials through existing Brain interfaces.

Author: E-AIRA maintainers.
Hardware target: ROSMASTER M3 Pro / Jetson Orin NX, ROS 2 Humble / Python 3.10.
"""

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import time
from typing import Any, Callable
import uuid

import rclpy
from geometry_msgs.msg import Twist
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from std_msgs.msg import String

from eira_brain.console import format_line, sanitize_text
from eira_evaluation.metrics_calculator import calculate, export_report, summary_rows
from eira_evaluation.mission_logger import TOPIC_MAP
from eira_evaluation.records import MissionAccumulator
from eira_evaluation.storage import DailyArchive


def command_envelope(command: str, mission_id: str, experiment_id: str, phase: str,
                     iteration: int, start_waypoint: str = '') -> dict[str, Any]:
    """Build a correlated trial or deterministic physical-reset command.

    Args:
        command: Natural-language trial instruction.
        mission_id: Unique command identity.
        experiment_id: Group identifier for the benchmark run.
        phase: Trial, reset or control phase.
        iteration: Zero-based trial index.
        start_waypoint: Measured waypoint for the reset phase.
    Returns:
        Backward-compatible JSON envelope for /eira/command String.
    """
    result = {'command': command, 'mission_id': mission_id, 'experiment_id': experiment_id,
              'phase': phase, 'iteration': iteration}
    if phase == 'reset':
        result.update(command='benchmark reset', purpose='benchmark_reset',
                      start_waypoint=start_waypoint)
    return result


class BenchmarkRunner(Node):
    """Observe actual Brain results; never teleport hardware or assume a reset succeeded."""

    def __init__(self, archive: DailyArchive, environment: str, seed: int) -> None:
        """Create observational subscriptions and a command-only publisher.

        Args:
            archive: Dedicated output archive for this benchmark run.
            environment: Hardware or simulation, kept separate during analysis.
            seed: Documented simulation/randomization seed, or -1 when unspecified.
        """
        super().__init__('eira_benchmark')
        self.archive = archive
        self.accumulator = MissionAccumulator(archive.load())
        self.environment = environment
        self.seed = seed
        self._known: set[str] = set()
        self._rejections: dict[str, str] = {}
        self._last_state = ''
        self._last_queue = 0
        self._zero_received_at = -math.inf
        self._publisher = self.create_publisher(String, '/eira/command', 10)
        for topic, key in TOPIC_MAP.items():
            if key != 'command':
                self.create_subscription(String, topic, self._callback(key), 100)
        self.create_subscription(Twist, '/cmd_vel', self._velocity, 10)

    def _callback(self, key: str) -> Callable[[String], None]:
        """Bind a collector to one observational topic.

        Args:
            key: Logical source name.
        Returns:
            Callback accepting correlated JSON Strings.
        """
        def receive(message: String) -> None:
            """Accept only this run's mission IDs and remember explicit busy rejections."""
            try:
                data = json.loads(message.data)
            except json.JSONDecodeError:
                return
            if not isinstance(data, dict):
                return
            if key == 'status':
                self._last_state = str(data.get('state', ''))
                queue = data.get('queue', 0)
                self._last_queue = queue if isinstance(queue, int) else 0
            identity = str(data.get('mission_id') or '')
            if identity not in self._known:
                return
            self.accumulator.ingest(key, data, time.time())
            record = self.accumulator.records[identity]
            record['environment'], record['random_seed'] = self.environment, self.seed
            if key == 'status' and str(data.get('detail', '')).startswith('rejected'):
                self._rejections[identity] = str(data['detail'])
        return receive

    def _velocity(self, message: Twist) -> None:
        """Observe zero base commands for a post-timeout stop acknowledgement."""
        values = (message.linear.x, message.linear.y, message.linear.z,
                  message.angular.x, message.angular.y, message.angular.z)
        if all(math.isfinite(value) and abs(value) <= 1e-4 for value in values):
            self._zero_received_at = time.monotonic()

    def ready(self, timeout_s: float) -> bool:
        """Wait for Brain command/status discovery with a finite wall-clock budget.

        Args:
            timeout_s: Maximum discovery wait.
        Returns:
            Whether the Brain's command and status channels are available.
        """
        deadline = time.monotonic()+timeout_s
        while rclpy.ok() and time.monotonic() < deadline:
            if self._publisher.get_subscription_count() > 0 and self.count_publishers(
                    '/eira/status') > 0:
                return True
            rclpy.spin_once(self, timeout_sec=0.05)
        return False

    def send(self, envelope: dict[str, Any]) -> str:
        """Record and publish one correlated command exactly once.

        Args:
            envelope: Trial/reset/control metadata and command.
        Returns:
            Published mission identity.
        """
        identity = str(envelope['mission_id'])
        self._known.add(identity)
        self.accumulator.ingest('command', envelope, time.time())
        record = self.accumulator.records[identity]
        record['environment'], record['random_seed'] = self.environment, self.seed
        self._publisher.publish(String(data=json.dumps(envelope)))
        return identity

    def wait(self, identity: str, timeout_s: float) -> str:
        """Wait only for the requested mission, not unrelated terminal statuses.

        Args:
            identity: Requested mission ID.
            timeout_s: Maximum wall-clock wait.
        Returns:
            done, failed, rejected, timed_out or shutdown.
        """
        deadline = time.monotonic()+timeout_s
        settled_at = None
        while rclpy.ok():
            now = time.monotonic()
            if identity in self._rejections:
                return 'rejected'
            record = self.accumulator.records.get(identity, {})
            if record.get('terminal_state') in ('DONE', 'FAILED'):
                # Different DDS topics do not guarantee cross-topic ordering.
                # Drain late plan/action evidence before evaluating trial success.
                if settled_at is None:
                    settled_at = now + getattr(self, 'event_grace_s', 1.0)
                if now >= settled_at:
                    return 'done' if record['terminal_state'] == 'DONE' else 'failed'
            elif now >= deadline:
                return 'timed_out'
            rclpy.spin_once(self, timeout_sec=0.05)
        return 'shutdown'

    def stop_and_confirm(self, experiment_id: str, iteration: int, timeout_s: float) -> bool:
        """Request stop and require its terminal acknowledgement plus a fresh zero Twist.

        Args:
            experiment_id: Parent benchmark run ID.
            iteration: Interrupted trial index.
            timeout_s: Finite stop-handshake budget.
        Returns:
            Whether both control acknowledgement and a post-request zero were observed.
        """
        sent_at = time.monotonic()
        identity = self.send(command_envelope('stop', uuid.uuid4().hex, experiment_id,
                                              'control', iteration))
        deadline = sent_at+timeout_s
        while rclpy.ok() and time.monotonic() < deadline:
            record = self.accumulator.records[identity]
            if record.get('terminal_state') == 'DONE' and self._zero_received_at >= sent_at:
                return True
            rclpy.spin_once(self, timeout_sec=0.05)
        return False

    def finish_timeout(self, identity: str, reason: str) -> None:
        """Mark a benchmark deadline failure without erasing the original event trace.

        Args:
            identity: Timed-out mission identity.
            reason: Benchmark-level timeout reason.
        """
        record = self.accumulator.records[identity]
        record['benchmark_timed_out'] = True
        record['terminal_state'] = record['terminal_state'] or 'FAILED'
        record['end_time'] = record['end_time'] or time.time()
        record['error_reason'] = reason
        self.accumulator._derive(record)

    def persist(self) -> None:
        """Commit all trials, resets and stop handshakes to this run's archive."""
        self.archive.save(self.accumulator.snapshot())


def run_trials(node: BenchmarkRunner, options: argparse.Namespace,
               experiment_id: str) -> dict[str, Any]:
    """Perform reset/trial pairs serially and stop the campaign on an unsafe timeout.

    Args:
        node: Ready benchmark runner.
        options: Validated CLI settings.
        experiment_id: Unique run identity.
    Returns:
        Requested/completed trial counts and abort/stop evidence.
    """
    context = {'experiment_id': experiment_id, 'requested_iterations': options.iterations,
               'trial_ids': [], 'reset_ids': [], 'abort_reason': '', 'stop_confirmed': None,
               'environment': options.environment, 'random_seed': options.seed,
               'command': options.command, 'start_waypoint': options.start_waypoint,
               'reset_omitted': options.skip_reset, 'trial_timeout_s': options.timeout,
               'reset_timeout_s': options.reset_timeout, 'stop_timeout_s': options.stop_timeout}
    for iteration in range(options.iterations):
        if not options.skip_reset:
            reset = node.send(command_envelope('', uuid.uuid4().hex, experiment_id,
                                               'reset', iteration, options.start_waypoint))
            context['reset_ids'].append(reset)
            outcome = node.wait(reset, options.reset_timeout)
            record = node.accumulator.records[reset]
            if outcome != 'done' or record.get('success') is not True:
                context['abort_reason'] = f'start-pose reset {outcome}'
                if outcome in ('timed_out', 'shutdown'):
                    context['stop_confirmed'] = node.stop_and_confirm(
                        experiment_id, iteration, options.stop_timeout)
                    node.finish_timeout(reset, context['abort_reason'])
                node.persist()
                break
        identity = node.send(command_envelope(options.command, uuid.uuid4().hex, experiment_id,
                                              'trial', iteration))
        context['trial_ids'].append(identity)
        outcome = node.wait(identity, options.timeout)
        if outcome in ('timed_out', 'shutdown'):
            context['stop_confirmed'] = node.stop_and_confirm(
                experiment_id, iteration, options.stop_timeout)
            node.finish_timeout(identity, f'benchmark {outcome}')
            context['abort_reason'] = f'trial {iteration+1} {outcome}'
            node.persist()
            # A timed-out trial is not a safe basis for another reset/grasp.
            break
        if outcome == 'rejected':
            node.finish_timeout(identity, node._rejections[identity])
            context['abort_reason'] = 'trial rejected; experiment is not isolated'
            node.persist()
            break
        node.persist()
    context['completed_iterations'] = len(context['trial_ids'])
    return context


def main(args: list[str] | None = None) -> int:
    """Run an explicitly requested physical/simulation benchmark campaign.

    Args:
        args: Optional CLI arguments.
    Returns:
        Zero for a finished campaign, two for setup/abort failures.
    """
    parser = argparse.ArgumentParser(
        description='Repeat E-AIRA missions with measured pose resets')
    parser.add_argument('--command', required=True)
    parser.add_argument('--iterations', type=int, default=20)
    parser.add_argument('--start-waypoint', default='home')
    parser.add_argument('--timeout', type=float, default=600.0)
    parser.add_argument('--reset-timeout', type=float, default=300.0)
    parser.add_argument('--stop-timeout', type=float, default=10.0)
    parser.add_argument('--ready-timeout', type=float, default=15.0)
    parser.add_argument('--event-grace', type=float, default=1.0,
                        help='drain late cross-topic evidence after terminal status (seconds)')
    parser.add_argument('--skip-reset', action='store_true', help='explicitly omit pose reset')
    parser.add_argument('--results-dir', type=Path, default=Path('~/eira_ws/results'))
    parser.add_argument('--environment', choices=('hardware', 'simulation', 'simulation_oracle'),
                        default='hardware')
    parser.add_argument('--seed', type=int, default=-1)
    options = parser.parse_args(args)
    if options.iterations < 1 or not options.command.strip() or any(
            not math.isfinite(value) or value <= 0 for value in
            (options.timeout, options.reset_timeout, options.stop_timeout, options.ready_timeout,
             options.event_grace)):
        parser.error('iterations and all timeouts must be positive; command must be nonempty')
    experiment_id = uuid.uuid4().hex
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    prefix = f'benchmark_{stamp}_{experiment_id[:8]}'
    directory = options.results_dir.expanduser()
    try:
        archive = DailyArchive(directory, prefix)
    except (OSError, ValueError, RuntimeError) as exc:
        parser.exit(2, f'cannot initialize benchmark archive: {exc}\n')
    rclpy.init()
    node = BenchmarkRunner(archive, options.environment, options.seed)
    node.event_grace_s = options.event_grace
    result = 0
    try:
        if not node.ready(options.ready_timeout):
            raise RuntimeError('Brain command/status discovery timed out; nothing was commanded')
        context = run_trials(node, options, experiment_id)
        summary = calculate(node.accumulator.snapshot(), options.environment)
        report_dir = directory / prefix
        export_report(summary, report_dir)
        (report_dir/'benchmark_run.json').write_text(json.dumps(context, indent=2)+'\n',
                                                     encoding='utf-8')
        completed = len(context['trial_ids'])
        print(f"Benchmark {experiment_id}: {completed}/{options.iterations} trials")
        for label, value, count in summary_rows(summary):
            print(f'{label:<38} {value:>16}   n={count}')
        if context['abort_reason']:
            node.get_logger().error(format_line(
                'BENCHMARK', 'Campaign stopped: ' + sanitize_text(context['abort_reason']),
                'error'))
            result = 2
    except (KeyboardInterrupt, ExternalShutdownException):
        if rclpy.ok():
            node.stop_and_confirm(experiment_id, -1, options.stop_timeout)
        result = 2
    except (OSError, RuntimeError, ValueError, TypeError, KeyError, ImportError) as exc:
        node.get_logger().error(format_line(
            'BENCHMARK', f'Campaign failed: {sanitize_text(exc)}', 'error'))
        active = any(record.get('terminal_state') not in ('DONE', 'FAILED')
                     and record.get('phase') in ('reset', 'trial')
                     for record in node.accumulator.records.values())
        if active and rclpy.ok():
            node.stop_and_confirm(experiment_id, -1, options.stop_timeout)
        result = 2
    finally:
        try:
            node.persist()
        except (OSError, ValueError, TypeError) as exc:
            node.get_logger().error(format_line(
                'BENCHMARK', f'Cannot save campaign: {sanitize_text(exc)}', 'error'))
            result = 2
        finally:
            archive.close()
            node.destroy_node()
            rclpy.try_shutdown()
    return result
