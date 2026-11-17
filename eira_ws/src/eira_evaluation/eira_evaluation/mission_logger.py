"""Record correlated missions as daily CSV and complete JSON event evidence.

Author: E-AIRA maintainers.
Hardware target: ROSMASTER M3 Pro / Jetson Orin NX, ROS 2 Humble / Python 3.10.
"""

import json
import math
from pathlib import Path
import time
from typing import Callable

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from std_msgs.msg import String

from eira_brain.console import format_line, sanitize_text
from eira_evaluation.records import MissionAccumulator
from eira_evaluation.storage import DailyArchive

TOPIC_MAP = {
    '/eira/command': 'command', '/eira/plan': 'plan', '/eira/status': 'status',
    '/eira/vision/event': 'vision', '/eira/manipulation/event': 'manipulation',
}


class MissionLogger(Node):
    """Keep durable, correlated observations independently of robot execution."""

    def __init__(self) -> None:
        """Create the result archive and subscribe without creating actuator interfaces.

        Raises:
            OSError: If the configured output directory is unavailable.
            ValueError: If archived data or metadata parameters are invalid.
            RuntimeError: If another logger owns the same output archive.
        """
        super().__init__('mission_logger')
        self.declare_parameter('results_dir', '~/eira_ws/results')
        self.declare_parameter('archive_prefix', 'mission_log')
        self.declare_parameter('flush_interval_s', 1.0)
        self.declare_parameter('environment', 'hardware')
        self.declare_parameter('random_seed', -1)
        if self.get_parameter('environment').value not in (
                'hardware', 'simulation', 'simulation_oracle'):
            raise ValueError('environment must be hardware, simulation or simulation_oracle')
        interval = float(self.get_parameter('flush_interval_s').value)
        if not math.isfinite(interval) or interval <= 0:
            raise ValueError('flush_interval_s must be positive')
        self.archive = DailyArchive(Path(self.get_parameter('results_dir').value),
                                    self.get_parameter('archive_prefix').value)
        self.accumulator = MissionAccumulator(self.archive.load())
        self._dirty = False
        self.accumulator.unmatched_commands = self.archive.unmatched_commands
        for topic, key in TOPIC_MAP.items():
            self.create_subscription(String, topic, self._callback(key), 100)
        self.create_subscription(String, '/eira/evaluation/grasp_truth', self._truth, 10)
        self.create_timer(interval, self._flush)
        self.get_logger().info(format_line(
            'EVALUATION', f'Mission evidence will be saved to {self.archive.directory}'))

    def _callback(self, key: str) -> Callable[[String], None]:
        """Build a topic-key-specific collector.

        Args:
            key: Logical source of this subscription.
        Returns:
            Callback that records the message without blocking the robot executor.
        """
        def receive(message: String) -> None:
            """Collect one message; flush terminal events immediately for durability."""
            try:
                identity = self.accumulator.ingest(key, message.data, time.time())
                if identity is not None:
                    record = self.accumulator.records[identity]
                    record.setdefault('environment', self.get_parameter('environment').value)
                    record.setdefault('random_seed', self.get_parameter('random_seed').value)
                    self._dirty = True
                    if record['terminal_state']:
                        self._flush()
                elif key == 'command':
                    self._dirty = True
            except (OSError, ValueError, TypeError, KeyError) as exc:
                self.get_logger().error(format_line(
                    'EVALUATION', f'Cannot record {key}: {sanitize_text(exc)}', 'error'))
        return receive

    def _truth(self, message: String) -> None:
        """Attach explicit physical grasp labels with their evidence provenance.

        Args:
            message: JSON {mission_id, action_id, object_held:boolean, source:string}.
        """
        try:
            data = json.loads(message.data)
            if (not isinstance(data, dict) or not isinstance(data.get('object_held'), bool)
                    or not data.get('mission_id') or not data.get('action_id')
                    or not isinstance(data.get('source'), str) or not data['source']):
                raise ValueError('grasp truth requires IDs, boolean object_held and source')
            event = {'event': 'grasped', 'mission_id': str(data['mission_id']),
                     'action_id': str(data['action_id']), 'object_contact_verified': True,
                     'object_held': data['object_held'], 'contact_evidence': data['source'],
                     'wall_time': time.time(), 'ground_truth_annotation': True}
            identity = self.accumulator.ingest('manipulation', event, time.time())
            if identity is not None:
                self._dirty = True
                self._flush()
        except (OSError, ValueError, TypeError) as exc:
            self.get_logger().error(format_line(
                'EVALUATION', f'Grasp annotation rejected: {sanitize_text(exc)}', 'error'))

    def _flush(self) -> None:
        """Commit dirty snapshots and keep failed writes pending for a later retry."""
        if not self._dirty:
            return
        try:
            self.archive.save(self.accumulator.snapshot(), self.accumulator.unmatched_commands)
            self._dirty = False
        except (OSError, ValueError, TypeError) as exc:
            self.get_logger().error(format_line(
                'EVALUATION', f'Cannot save mission evidence: {sanitize_text(exc)}', 'error'))

    def destroy_node(self) -> None:
        """Flush pending observations without inventing terminal results on logger shutdown."""
        self._flush()
        self.archive.close()
        super().destroy_node()


def main(args: list[str] | None = None) -> None:
    """Run the observational mission logger.

    Args:
        args: Optional ROS command-line arguments.
    """
    rclpy.init(args=args)
    node = MissionLogger()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
