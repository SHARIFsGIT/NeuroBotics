"""Record bounded, mission-scoped ROS bags without blocking the robot executor.

Author: E-AIRA maintainers.
Hardware target: ROSMASTER M3 Pro / Jetson Orin NX, ROS 2 Humble, Python 3.10.
The bag process is a recorder only. Complete status/plan boundary sidecars expose
startup discovery gaps instead of treating subprocess creation as data readiness.
"""

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import platform
import re
import signal
import shutil
import subprocess
import threading
import time
from typing import Any

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from std_msgs.msg import String

from eira_brain.console import error_hint, format_line, sanitize_text


DEFAULT_TOPICS = [
    '/camera/color/image_raw/compressed', '/camera/depth/image_raw',
    '/camera/color/camera_info', '/camera/depth/camera_info',
    '/scan', '/tf', '/tf_static', '/cmd_vel',
    '/eira/command', '/eira/voice', '/eira/plan', '/eira/status', '/target_pose',
    '/eira/vision_target', '/eira/vision/event', '/eira/manipulation/request',
    '/eira/manipulation/event', '/eira/gesture', '/eira/safety/edge',
    '/eira/safety/event', '/eira/motion/event', '/eira/heartbeat',
    '/arm6_joints', '/arm_joint', '/Curjoints', '/clock', '/eira/evaluation/grasp_truth',
]
_TOPIC = re.compile(r'^/[A-Za-z0-9_/]+$')


def record_command(directory: Path, topics: list[str], storage_id: str,
                   qos_file: Path, node_name: str = 'rosbag2_recorder',
                   use_sim_time: bool = False) -> list[str]:
    """Build an argument-list-only recording command with validated topic names.

    Args:
        directory: New rosbag output directory (must not already exist).
        topics: Absolute ROS topic names.
        storage_id: Installed rosbag storage backend.
        qos_file: QoS override YAML written beside the bag.
        node_name: Unique recorder identity used to verify discovery during overlap.
        use_sim_time: Timestamp bag messages from the simulation clock when enabled.

    Returns:
        Subprocess argument vector; no shell expansion occurs.

    Raises:
        ValueError: Topic names or storage ID are invalid.
    """
    if not topics or any(not _TOPIC.fullmatch(topic) for topic in topics):
        raise ValueError('recording requires valid absolute ROS topic names')
    if not re.fullmatch(r'[A-Za-z0-9_]+', storage_id):
        raise ValueError('invalid storage backend name')
    if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', node_name):
        raise ValueError('invalid recorder node name')
    command = ['ros2', 'bag', 'record', '--output', str(directory), '--storage', storage_id,
               '--qos-profile-overrides-path', str(qos_file), '--node-name', node_name,
               '--max-cache-size', '16777216']
    if use_sim_time:
        command.append('--use-sim-time')
    return command + list(dict.fromkeys(topics))


def stop_process(process: Any, interrupt_s: float, terminate_s: float,
                 kill_s: float = 2.0) -> str:
    """Flush and reap a child process group with finite escalation deadlines.

    Args:
        process: Popen-compatible process started with start_new_session=True.
        interrupt_s: Time allowed for SIGINT and rosbag metadata flush.
        terminate_s: Time allowed after SIGTERM.
        kill_s: Final reap timeout after SIGKILL.

    Returns:
        Last signal stage, or ``exited`` if the child had already completed.

    Raises:
        subprocess.TimeoutExpired: A killed child cannot be reaped within kill_s.
        OSError: A signal cannot be delivered for reasons other than process exit.
    """
    if process.poll() is not None:
        process.wait(timeout=kill_s)
        return 'exited'
    for sig, timeout, label in ((signal.SIGINT, interrupt_s, 'sigint'),
                                (signal.SIGTERM, terminate_s, 'sigterm'),
                                (signal.SIGKILL, kill_s, 'sigkill')):
        try:
            os.killpg(process.pid, sig)
        except ProcessLookupError:
            process.wait(timeout=kill_s)
            return 'exited'
        try:
            process.wait(timeout=timeout)
            return label
        except subprocess.TimeoutExpired:
            if sig == signal.SIGKILL:
                raise
    return 'sigkill'


@dataclass
class MissionCapture:
    """Hold one mission's capture state, including a bounded boundary-event prebuffer.

    Args:
        mission_id: Planner correlation identity.
        path: Mission directory containing bag/ and provenance sidecars.
        started_wall: Mission start time from the recorder's system clock.
        history: Bounded status/plan events seen before/during recorder discovery.
    """

    mission_id: str
    path: Path
    started_wall: float
    history: deque = field(default_factory=lambda: deque(maxlen=4096))
    terminal: threading.Event = field(default_factory=threading.Event)
    terminal_wall: float | None = None
    terminal_state: str = ''
    node_name: str = ''
    process: Any = None
    manifest: dict[str, Any] = field(default_factory=dict)


class MissionRecorder(Node):
    """Automatically record each planner mission with at most two live bag processes."""

    def __init__(self) -> None:
        """Declare recorder limits, mission status taps and optional bounded JPEG conversion."""
        super().__init__('mission_recorder')
        defaults = {
            'bags_directory': '~/eira_ws/bags', 'topics': DEFAULT_TOPICS,
            'storage_id': 'sqlite3', 'max_parallel_recorders': 2,
            'max_pending_missions': 8, 'boundary_history_size': 4096,
            'max_event_chars': 65536, 'discovery_timeout_s': 5.0,
            'flush_timeout_s': 10.0, 'terminate_timeout_s': 3.0, 'kill_timeout_s': 2.0,
            'post_roll_s': 0.5, 'minimum_capture_s': 1.0, 'poll_period_s': 0.1,
            'max_capture_s': 900.0, 'min_free_space_mb': 256.0, 'space_check_period_s': 5.0,
            'discovery_topics': ['/eira/status', '/eira/plan'],
            'compress_color': True, 'color_topic': '/camera/color/image_raw',
            'compressed_color_topic': '/camera/color/image_raw/compressed',
            'jpeg_quality': 75, 'jpeg_max_fps': 5.0, 'capture_config_files': [],
            'environment': 'hardware', 'random_seed': -1,
        }
        for name, value in defaults.items():
            if name == 'capture_config_files':
                self.declare_parameter(name, rclpy.Parameter.Type.STRING_ARRAY)
            else:
                self.declare_parameter(name, value)
        for name in ('max_parallel_recorders', 'max_pending_missions', 'boundary_history_size',
                     'max_event_chars', 'discovery_timeout_s', 'flush_timeout_s',
                     'terminate_timeout_s', 'kill_timeout_s', 'poll_period_s', 'jpeg_max_fps',
                     'max_capture_s', 'min_free_space_mb', 'space_check_period_s'):
            if not math.isfinite(float(self._p(name))) or float(self._p(name)) <= 0:
                raise ValueError(f'{name} must be positive')
        if not 1 <= int(self._p('max_parallel_recorders')) <= 2:
            raise ValueError('max_parallel_recorders must lie in [1, 2]')
        if not 1 <= int(self._p('jpeg_quality')) <= 100:
            raise ValueError('jpeg_quality must lie in [1, 100]')
        self._base = Path(str(self._p('bags_directory'))).expanduser()
        self._lock = threading.RLock()
        self._closing = threading.Event()
        self._slots = threading.Semaphore(int(self._p('max_parallel_recorders')))
        self._sessions: dict[str, MissionCapture] = {}
        self._completed = deque(maxlen=int(self._p('max_pending_missions')) * 8)
        self._threads: list[threading.Thread] = []
        self._last_jpeg = 0.0
        self._bridge = None
        self._jpeg_pub = None
        self._event_pub = self.create_publisher(String, '/eira/recording/status', 10)
        self.create_subscription(String, '/eira/status', self._on_status, 50)
        self.create_subscription(String, '/eira/plan', self._on_plan, 50)
        self._topics = list(self._p('topics'))
        # Validate before any subprocess starts.
        record_command(self._base / 'validation_only', self._topics, self._p('storage_id'),
                       self._base / 'qos.yaml')
        if self._p('compress_color'):
            self._configure_jpeg()

    def _p(self, name: str) -> Any:
        """Return a declared parameter value."""
        if name == 'capture_config_files':
            fallback = rclpy.Parameter(name, rclpy.Parameter.Type.STRING_ARRAY, [])
            return self.get_parameter_or(name, fallback).value
        return self.get_parameter(name).value

    def _configure_jpeg(self) -> None:
        """Create a bounded JPEG tap; an existing camera compressed publisher takes precedence."""
        try:
            from cv_bridge import CvBridge
            from sensor_msgs.msg import CompressedImage, Image
        except ImportError as exc:
            self._emit('compression_unavailable', '', reason=str(exc))
            return
        self._bridge = CvBridge()
        self._jpeg_pub = self.create_publisher(
            CompressedImage, self._p('compressed_color_topic'), qos_profile_sensor_data)
        self.create_subscription(Image, self._p('color_topic'), self._on_image,
                                 qos_profile_sensor_data)

    def _on_image(self, msg: Any) -> None:
        """Compress color only during mission capture at the configured bounded frame rate."""
        now = time.monotonic()
        if (self._bridge is None or not self._sessions
                or now - self._last_jpeg < 1.0 / float(self._p('jpeg_max_fps'))):
            return
        if self.count_publishers(self._p('compressed_color_topic')) > 1:
            return
        from cv_bridge import CvBridgeError
        import cv2
        from sensor_msgs.msg import CompressedImage
        self._last_jpeg = now
        try:
            pixels = self._bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
            ok, encoded = cv2.imencode('.jpg', pixels,
                                       [cv2.IMWRITE_JPEG_QUALITY, int(self._p('jpeg_quality'))])
            if not ok:
                raise ValueError('JPEG encoder returned no image')
            image = CompressedImage()
            image.header = msg.header
            image.format = 'bgr8; jpeg compressed bgr8'
            image.data = encoded.tobytes()
            self._jpeg_pub.publish(image)
        except (CvBridgeError, cv2.error, ValueError, RuntimeError) as exc:
            self._emit('compression_frame_dropped', '', reason=str(exc))

    def _decode(self, text: str) -> dict[str, Any] | None:
        """Validate a bounded structured planner event before adding it to the prebuffer."""
        if len(text) > int(self._p('max_event_chars')):
            return None
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return None
        if not isinstance(data, dict) or not isinstance(data.get('mission_id'), str):
            return None
        return data

    def _on_status(self, msg: String) -> None:
        """Start on PLANNING and stop only the matching mission on terminal planner status."""
        data = self._decode(msg.data)
        if data is None or not data['mission_id']:
            return
        mission, state = data['mission_id'], data.get('state', '')
        with self._lock:
            if self._closing.is_set() or mission in self._completed:
                return
            session = self._sessions.get(mission)
            if session is None and state == 'PLANNING' and data.get('detail') != 'queued':
                if len(self._sessions) >= int(self._p('max_pending_missions')):
                    self._emit('failed', mission, reason='pending capture capacity exceeded')
                    self._completed.append(mission)
                    return
                suffix = re.sub(r'[^A-Za-z0-9_-]', '_', mission)[:40]
                stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ')
                session = MissionCapture(mission, self._base / f'mission_{stamp}_{suffix}',
                                         time.time(), deque(maxlen=int(
                                             self._p('boundary_history_size'))))
                session.node_name = f'eira_bag_recorder_{stamp}_{suffix.replace("-", "_")}'
                self._sessions[mission] = session
                worker = threading.Thread(target=self._capture, args=(session,), daemon=True)
                self._threads = [thread for thread in self._threads if thread.is_alive()]
                self._threads.append(worker)
                worker.start()
                self._emit('queued', mission, path=str(session.path))
            if session is None:
                return
            session.history.append(dict(topic='/eira/status',
                                        received_wall=time.time(), data=data))
            if state in ('DONE', 'FAILED', 'CANCELLED') or (
                    state == 'IDLE' and 'preempt' in str(data.get('detail', '')).lower()):
                session.terminal_state = str(state)
                session.terminal_wall = time.time()
                session.terminal.set()

    def _on_plan(self, msg: String) -> None:
        """Retain the complete plan even if recorder discovery has not yet subscribed."""
        data = self._decode(msg.data)
        if data is None:
            return
        with self._lock:
            session = self._sessions.get(data['mission_id'])
            if session is not None:
                session.history.append(dict(topic='/eira/plan',
                                            received_wall=time.time(), data=data))

    def _emit(self, event: str, mission_id: str, **fields: Any) -> None:
        """Publish structured recording lifecycle independently from planner mission success."""
        payload = dict(event=event, mission_id=mission_id, wall_time=time.time(), **fields)
        message = String()
        message.data = json.dumps(payload)
        try:
            self._event_pub.publish(message)
        except RuntimeError:
            # Signal handlers may shut ROS down while the bag flush worker is still active.
            pass
        descriptions = {
            'queued': 'Mission recording queued',
            'starting': 'Starting mission recorder',
            'recording': 'Recorder started; waiting for topic discovery',
            'ready': 'Recorder connected; capturing mission',
            'finalizing': 'Finalizing mission bag',
            'complete': 'Mission bag saved',
            'incomplete': 'Mission bag incomplete; inspect its manifest',
            'failed': 'Mission recording failed',
            'manifest_failed': 'Could not save recording manifest',
            'compression_unavailable': 'Camera compression unavailable',
            'compression_frame_dropped': 'Skipped camera compression frame',
        }
        description = descriptions.get(event, sanitize_text(event).replace('_', ' ').capitalize())
        if fields.get('reason'):
            description += ': ' + error_hint(fields['reason'])
        if fields.get('path'):
            description += ' — ' + sanitize_text(fields['path'])
        level = 'warning' if event in (
            'incomplete', 'failed', 'manifest_failed', 'compression_unavailable') else 'info'
        self.get_logger().info(format_line('RECORDER', description, level))

    def _discovered(self, node_name: str) -> bool:
        """Return true only when required topics expose rosbag-recorder subscriptions."""
        required = list(self._p('discovery_topics'))
        if not required:
            return False
        return all(any(node_name == info.node_name
                       for info in self.get_subscriptions_info_by_topic(topic))
                   for topic in required)

    def _provenance(self, session: MissionCapture) -> dict[str, Any]:
        """Collect curated runtime/configuration provenance without copying environment secrets."""
        import hashlib
        configs = {}
        for raw in self._p('capture_config_files') or []:
            path = Path(raw).expanduser()
            try:
                content = path.read_bytes()
                configs[str(path)] = {'sha256': hashlib.sha256(content).hexdigest(),
                                      'size_bytes': len(content)}
            except OSError as exc:
                configs[str(path)] = {'error': str(exc)}
        return dict(schema_version=1, mission_id=session.mission_id,
                    mission_started_wall=session.started_wall, topics=self._topics,
                    ros_distro=os.environ.get('ROS_DISTRO', 'unknown'),
                    ros_domain_id=os.environ.get('ROS_DOMAIN_ID', '0'),
                    architecture=platform.machine(), python_version=platform.python_version(),
                    use_sim_time=bool(self._p('use_sim_time')), configs=configs,
                    environment=self._p('environment'), random_seed=self._p('random_seed'),
                    capture_boundary='process/discovery startup gap; see boundary_events.jsonl',
                    compression=dict(topic=self._p('compressed_color_topic'),
                                     quality=self._p('jpeg_quality'),
                                     max_fps=self._p('jpeg_max_fps')))

    def _capture(self, session: MissionCapture) -> None:
        """Manage one recorder process, bounded overlap, metadata flush and provenance writes."""
        acquired = False
        log_handle = None
        manifest = self._provenance(session)
        try:
            while not self._closing.is_set():
                if self._slots.acquire(timeout=float(self._p('poll_period_s'))):
                    acquired = True
                    break
            if not acquired:
                manifest['result'] = 'cancelled_before_start'
                return
            session.path.mkdir(parents=True, exist_ok=False)
            if shutil.disk_usage(session.path).free < float(
                    self._p('min_free_space_mb')) * 1048576:
                raise OSError('insufficient free storage for mission recording')
            qos = session.path / 'qos.yaml'
            qos.write_text('/tf_static:\n  durability: transient_local\n  reliability: reliable\n'
                           '  history: keep_last\n  depth: 1\n', encoding='utf-8')
            log_handle = (session.path / 'recorder.log').open('w', encoding='utf-8')
            command = record_command(session.path / 'bag', self._topics,
                                     self._p('storage_id'), qos, session.node_name,
                                     bool(self._p('use_sim_time')))
            self._emit('starting', session.mission_id, path=str(session.path))
            session.process = subprocess.Popen(
                command, stdin=subprocess.DEVNULL, stdout=log_handle,
                stderr=subprocess.STDOUT, start_new_session=True)
            started = time.monotonic()
            manifest['process_started_wall'] = time.time()
            manifest['startup_gap_s'] = manifest['process_started_wall'] - session.started_wall
            self._emit('recording', session.mission_id, ready=False, path=str(session.path))
            ready = False
            discovery_until = started + float(self._p('discovery_timeout_s'))
            space_check = started + float(self._p('space_check_period_s'))
            while not self._closing.is_set():
                if session.process.poll() is not None:
                    code = session.process.returncode
                    raise RuntimeError(f'rosbag exited early with code {code}')
                now = time.monotonic()
                if now - started >= float(self._p('max_capture_s')):
                    raise RuntimeError('maximum mission capture duration exceeded')
                if now >= space_check:
                    if shutil.disk_usage(session.path).free < float(
                            self._p('min_free_space_mb')) * 1048576:
                        raise OSError('storage reserve reached during mission recording')
                    space_check = now + float(self._p('space_check_period_s'))
                if not ready and self._discovered(session.node_name):
                    ready = True
                    manifest['discovery_ready_wall'] = time.time()
                    manifest['discovery_gap_s'] = time.time() - session.started_wall
                    self._emit('ready', session.mission_id, path=str(session.path),
                               required_topics=list(self._p('discovery_topics')))
                if not ready and now >= discovery_until:
                    manifest['discovery_warning'] = 'required recorder subscriptions not observed'
                minimum_elapsed = now - started >= float(self._p('minimum_capture_s'))
                post_roll_elapsed = (session.terminal_wall is not None
                                     and time.time() - session.terminal_wall
                                     >= float(self._p('post_roll_s')))
                if session.terminal.is_set() and minimum_elapsed and post_roll_elapsed:
                    break
                self._closing.wait(float(self._p('poll_period_s')))
            self._emit('finalizing', session.mission_id)
            manifest['stop_stage'] = stop_process(
                session.process, float(self._p('flush_timeout_s')),
                float(self._p('terminate_timeout_s')), float(self._p('kill_timeout_s')))
            manifest['return_code'] = session.process.returncode
            metadata = session.path / 'bag' / 'metadata.yaml'
            # SIGTERM/KILL does not establish a flushed/reproducible bag.
            complete = (metadata.is_file() and manifest['stop_stage'] in ('sigint', 'exited')
                        and session.process.returncode in (0, -signal.SIGINT, 130))
            manifest['result'] = 'complete' if complete else 'incomplete'
            manifest['discovery_observed'] = ready
            self._emit(manifest['result'], session.mission_id, path=str(session.path),
                       discovery_observed=ready)
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
            manifest.update(result='failed', error=str(exc))
            self._emit('failed', session.mission_id, reason=str(exc), path=str(session.path))
        finally:
            if session.process is not None and session.process.poll() is None:
                try:
                    manifest['stop_stage'] = stop_process(
                        session.process, float(self._p('flush_timeout_s')),
                        float(self._p('terminate_timeout_s')), float(self._p('kill_timeout_s')))
                except (OSError, subprocess.SubprocessError) as exc:
                    manifest['stop_error'] = str(exc)
            manifest.update(mission_terminal_state=session.terminal_state,
                            mission_terminal_wall=session.terminal_wall,
                            finalized_wall=time.time())
            try:
                session.path.mkdir(parents=True, exist_ok=True)
                with self._lock:
                    history = list(session.history)
                (session.path / 'boundary_events.jsonl').write_text(
                    ''.join(json.dumps(event) + '\n' for event in history), encoding='utf-8')
                (session.path / 'mission.json').write_text(
                    json.dumps(manifest, indent=2), encoding='utf-8')
            except OSError as exc:
                self._emit('manifest_failed', session.mission_id, reason=str(exc))
            if log_handle is not None:
                log_handle.close()
            with self._lock:
                self._sessions.pop(session.mission_id, None)
                self._completed.append(session.mission_id)
            if acquired:
                self._slots.release()

    def destroy_node(self) -> None:
        """Stop and reap bag children before the ROS context is destroyed."""
        self._closing.set()
        budget = (float(self._p('flush_timeout_s')) + float(self._p('terminate_timeout_s'))
                  + float(self._p('kill_timeout_s')) + 2.0)
        until = time.monotonic() + budget
        for thread in self._threads:
            thread.join(timeout=max(0.0, until - time.monotonic()))
        super().destroy_node()


def main(args: list[str] | None = None) -> None:
    """Run automatic mission recording until shutdown while allowing bag metadata to flush."""
    rclpy.init(args=args)
    node = MissionRecorder()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
