"""Replay recorded missions into a namespace or an explicitly isolated ROS domain.

Author: E-AIRA maintainers.
Hardware target: Jetson Orin NX or developer PC, ROS 2 Humble/Python 3.10.
Default analysis replay remaps every recorded topic, including TF and commands;
perception replay selects sensor inputs only. Physical actuator outputs are never
replayed on original names, even in the explicit isolated-domain mode.
"""

import argparse
import json
import math
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import time
from typing import Any

import yaml

from eira_brain.mission_recorder import stop_process
from eira_brain.console import format_line, sanitize_text


SENSOR_TOPICS = {
    '/camera/color/image_raw/compressed', '/camera/depth/image_raw',
    '/camera/color/camera_info', '/camera/depth/camera_info',
    '/tf', '/tf_static', '/scan', '/clock',
    '/eira/vision_target',
}
ACTUATOR_TOPICS = {'/cmd_vel', '/arm6_joints', '/arm_joint', '/beep', '/set_joint5', '/set_joint6'}
REQUEST_TOPICS = {'/eira/manipulation/request'}
_TOPIC = re.compile(r'^/[A-Za-z0-9_/]+$')


def bag_topics(path: Path) -> tuple[Path, list[str]]:
    """Resolve a mission/bag directory and read its authoritative recorded-topic inventory.

    Args:
        path: Mission directory containing bag/ or a rosbag directory itself.

    Returns:
        Resolved bag directory and unique recorded topic names.

    Raises:
        OSError: Bag metadata is unavailable.
        ValueError: Metadata has invalid structure/topic names.
    """
    bag = path.expanduser().resolve()
    if not (bag / 'metadata.yaml').is_file() and (bag / 'bag' / 'metadata.yaml').is_file():
        bag /= 'bag'
    try:
        data = yaml.safe_load((bag / 'metadata.yaml').read_text(encoding='utf-8'))
        entries = data['rosbag2_bagfile_information']['topics_with_message_count']
        topics = [entry['topic_metadata']['name'] for entry in entries]
    except (yaml.YAMLError, KeyError, TypeError) as exc:
        raise ValueError('invalid rosbag metadata topic inventory') from exc
    if not topics or any(not isinstance(topic, str) or not _TOPIC.fullmatch(topic)
                         for topic in topics):
        raise ValueError('bag contains no valid absolute ROS topics')
    return bag, list(dict.fromkeys(topics))


def replay_command(bag: Path, topics: list[str], mode: str, namespace: str,
                   rate: float = 1.0, offset_s: float = 0.0,
                   include_requests: bool = False, use_clock: bool = False) -> list[str]:
    """Build a replay command that cannot expose actuator outputs on original topic names.

    Args:
        bag: Resolved rosbag directory.
        topics: Authoritative recorded topic list.
        mode: analysis (all remapped), perception (remapped inputs), or isolated.
        namespace: Absolute nonroot replay namespace for nonisolated modes.
        rate: Positive playback speed multiplier.
        offset_s: Nonnegative starting offset into the bag.
        include_requests: Include arm skill requests only in isolated mode.
        use_clock: Emit simulated clock only in an isolated domain.

    Returns:
        A ros2 bag play argument list.

    Raises:
        ValueError: A mode, namespace, topic, or numeric option is unsafe/invalid.
    """
    if mode not in ('analysis', 'perception', 'isolated'):
        raise ValueError('unknown replay mode')
    if not math.isfinite(rate) or rate <= 0 or not math.isfinite(offset_s) or offset_s < 0:
        raise ValueError('rate must be positive and start offset must be nonnegative')
    if any(not _TOPIC.fullmatch(topic) for topic in topics):
        raise ValueError('invalid replay topic name')
    namespace = namespace.rstrip('/')
    if mode != 'isolated' and (not _TOPIC.fullmatch(namespace) or not namespace):
        raise ValueError('analysis/perception requires an absolute nonroot namespace')
    if include_requests and mode != 'isolated':
        raise ValueError('request reprocessing is available only in an isolated ROS domain')
    if use_clock and mode != 'isolated':
        raise ValueError('publishing /clock is available only in an isolated ROS domain')
    selected = list(topics) if mode == 'analysis' else [
        topic for topic in topics if topic in SENSOR_TOPICS]
    if mode == 'isolated' and include_requests:
        selected.extend(topic for topic in topics if topic in REQUEST_TOPICS)
    if mode == 'isolated':
        # Defensive even if the sensor allowlist changes later.
        selected = [topic for topic in selected if topic not in ACTUATOR_TOPICS]
    if not selected:
        raise ValueError('the bag has no topics matching the selected replay mode')
    # A recorded /clock is input data; --clock generates the playback timeline instead.
    if use_clock:
        selected = [topic for topic in selected if topic != '/clock']
        if not selected:
            raise ValueError('no sensor topics remain after replacing the recorded clock')
    command = ['ros2', 'bag', 'play', str(bag), '--rate', str(rate),
               '--start-offset', str(offset_s), '--disable-keyboard-controls',
               '--read-ahead-queue-size', '100', '--topics', *selected]
    if mode != 'isolated':
        command += ['--remap', *(f'{topic}:={namespace}{topic}' for topic in selected)]
    if use_clock:
        command += ['--clock', '30']
    return command


def replay_environment(mode: str, domain_id: int | None,
                       current: dict[str, str] | None = None) -> dict[str, str]:
    """Require an explicit different DDS domain for original-topic reprocessing.

    Args:
        mode: Replay mode.
        domain_id: Explicit requested DDS domain for isolated mode.
        current: Environment snapshot, defaulting to the process environment.

    Returns:
        Child-process environment with explicit isolated domain when applicable.

    Raises:
        ValueError: Isolation is absent, invalid, or identical to the active domain.
    """
    environment = dict(os.environ if current is None else current)
    parent = environment.get('ROS_DOMAIN_ID', '0')
    if mode == 'isolated':
        if domain_id is None or not 0 <= domain_id <= 232 or domain_id == int(parent):
            raise ValueError('isolated replay requires --domain-id 0..232 different from current')
        environment['ROS_DOMAIN_ID'] = str(domain_id)
        environment['ROS_LOCALHOST_ONLY'] = '1'
    elif domain_id is not None:
        raise ValueError('--domain-id is reserved for explicit isolated mode')
    return environment


class ReplayImageDecoder:
    """Construct an optional namespaced JPEG decoder without importing vision libraries eagerly."""

    @staticmethod
    def create(namespace: str) -> Any:
        """Create a ROS node that restores raw RGB only on the selected replay topic tree.

        Args:
            namespace: Replay prefix, empty only inside an explicitly isolated domain.

        Returns:
            Node with compressed-image subscription and raw Image publisher.

        Raises:
            ImportError: Required ROS/OpenCV bridge packages are unavailable.
        """
        from cv_bridge import CvBridge, CvBridgeError
        import cv2
        import numpy as np
        from rclpy.node import Node
        from rclpy.qos import qos_profile_sensor_data
        from sensor_msgs.msg import CompressedImage, Image

        class Decoder(Node):
            """Decode replay JPEG messages while retaining their measurement timestamps."""

            def __init__(self) -> None:
                """Connect only the replay namespace's color image topics."""
                super().__init__('mission_replay_decoder')
                self._bridge = CvBridge()
                self._publisher = self.create_publisher(
                    Image, namespace + '/camera/color/image_raw', qos_profile_sensor_data)
                self.create_subscription(CompressedImage,
                                         namespace + '/camera/color/image_raw/compressed',
                                         self._on_image, qos_profile_sensor_data)

            def _on_image(self, message: Any) -> None:
                """Decode one JPEG safely without altering the original camera header."""
                try:
                    pixels = cv2.imdecode(np.frombuffer(message.data, dtype=np.uint8),
                                          cv2.IMREAD_COLOR)
                    if pixels is None:
                        raise ValueError('replay JPEG contains no decodable pixels')
                    image = self._bridge.cv2_to_imgmsg(pixels, encoding='bgr8')
                    image.header = message.header
                    self._publisher.publish(image)
                except (CvBridgeError, cv2.error, ValueError, TypeError) as exc:
                    self.get_logger().warning(format_line(
                        'REPLAY', f'Image skipped: {sanitize_text(exc)}', 'warning'))
        return Decoder()


def main(args: list[str] | None = None) -> int:
    """Run a safe default replay and reap the player on interruption or a finite deadline.

    Args:
        args: Optional CLI arguments, primarily for testing.

    Returns:
        Playback exit status, or 2 for invalid configuration/dependencies.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bag', type=Path, help='mission folder or rosbag directory')
    parser.add_argument('--mode', choices=('analysis', 'perception', 'isolated'),
                        default='analysis')
    parser.add_argument('--namespace', default='/eira/replay')
    parser.add_argument('--domain-id', type=int)
    parser.add_argument('--rate', type=float, default=1.0)
    parser.add_argument('--start-offset', type=float, default=0.0)
    parser.add_argument('--include-requests', action='store_true')
    parser.add_argument('--clock', action='store_true')
    parser.add_argument('--decode-color', action='store_true')
    parser.add_argument('--max-duration-s', type=float, default=0.0,
                        help='wall-clock deadline; zero plays until end of bag')
    parser.add_argument('--dry-run', action='store_true',
                        help='print command without starting ROS')
    parser.add_argument('--json', action='store_true',
                        help='machine-readable output for an explicit dry run')
    options = parser.parse_args(args)
    process = None
    decoder = None
    initialized = False
    try:
        if not math.isfinite(options.max_duration_s) or options.max_duration_s < 0:
            raise ValueError('max duration must be finite and nonnegative')
        bag, topics = bag_topics(options.bag)
        environment = replay_environment(options.mode, options.domain_id)
        command = replay_command(bag, topics, options.mode, options.namespace, options.rate,
                                 options.start_offset, options.include_requests, options.clock)
        if options.dry_run:
            if options.json:
                print(json.dumps(dict(event='replay_plan', command=command,
                                      domain_id=environment.get('ROS_DOMAIN_ID', '0'),
                                      decode_color=options.decode_color)))
            else:
                print(format_line('REPLAY', 'Preview only; playback has not started'))
                domain = environment.get('ROS_DOMAIN_ID', '0')
                print(format_line('REPLAY', 'ROS domain: ' + domain))
                print(format_line('REPLAY', 'Command: ' + shlex.join(command)))
            return 0
        if options.decode_color:
            import rclpy
            if options.mode == 'isolated':
                os.environ['ROS_LOCALHOST_ONLY'] = '1'
            rclpy.init(domain_id=int(environment.get('ROS_DOMAIN_ID', '0')))
            initialized = True
            decoder = ReplayImageDecoder.create(
                '' if options.mode == 'isolated' else options.namespace.rstrip('/'))
        process = subprocess.Popen(command, env=environment, stdin=subprocess.DEVNULL,
                                   start_new_session=True)
        started = time.monotonic()
        while process.poll() is None:
            if options.max_duration_s and time.monotonic() - started >= options.max_duration_s:
                stop_process(process, 5.0, 2.0)
                return 124
            if decoder is not None:
                import rclpy
                rclpy.spin_once(decoder, timeout_sec=0.1)
            else:
                time.sleep(0.1)
        return int(process.returncode)
    except KeyboardInterrupt:
        return 130
    except (OSError, ValueError, ImportError, RuntimeError, subprocess.SubprocessError) as exc:
        print(format_line('REPLAY', f'Playback failed: {sanitize_text(exc)}', 'error'),
              file=sys.stderr)
        return 2
    finally:
        if process is not None and process.poll() is None:
            try:
                stop_process(process, 5.0, 2.0)
            except (OSError, subprocess.SubprocessError) as exc:
                print(format_line('REPLAY', f'Could not stop playback: {sanitize_text(exc)}',
                                  'error'), file=sys.stderr)
        if decoder is not None:
            decoder.destroy_node()
        if initialized:
            import rclpy
            if rclpy.ok():
                rclpy.shutdown()


if __name__ == '__main__':
    sys.exit(main())
