"""Correlated RGB-D perception with persistent object tracking for E-AIRA.

Author: E-AIRA contributors.
Hardware target: ROSMASTER M3 Pro, Jetson Orin NX, registered Dabai DCW2 RGB-D.
"""

from collections import OrderedDict
from concurrent.futures import Future
from copy import deepcopy
import json
import math
from pathlib import Path
import time
from typing import Any, NamedTuple

import cv2
import numpy as np
import rclpy
from cv_bridge import CvBridge, CvBridgeError
from geometry_msgs.msg import PointStamped, PoseStamped
from rclpy.duration import Duration
from rclpy.executors import ExternalShutdownException, MultiThreadedExecutor
from rclpy.node import Node
from rcl_interfaces.msg import SetParametersResult
from rclpy.qos import qos_profile_sensor_data
from rclpy.time import Time
from sensor_msgs.msg import CameraInfo, Image
from std_msgs.msg import String
import tf2_geometry_msgs  # noqa: F401 -- register PointStamped transformations
import tf2_ros
from tf2_ros.buffer_interface import TypeException

from eira_brain.console import error_hint, format_line, sanitize_text
from eira_perception.perception_core import (
    Detection, PositionFilter, TargetTrack, color_fraction,
    object_dimensions, split_target, target_request,
)
from eira_perception.depth_geometry import (
    DepthSample, estimate_bbox_depth, normalize_depth, resize_depth, sample_depth,
    scale_intrinsics,
)
from eira_perception.inference_worker import InferenceWorker


class ImageContext(NamedTuple):
    """Keep one inference's sensor measurements and calibration snapshots together."""

    generation: int
    frame: np.ndarray
    depth: np.ndarray
    color_image: Image
    depth_image: Image | None
    color_info: CameraInfo | None
    depth_info: CameraInfo | None
    original_depth_size: tuple[int, int]


class VisionManager(Node):
    """Acquire, follow and measure one correlated target without blocking ROS I/O."""

    def __init__(self) -> None:
        """Create interfaces and defer model initialization to a bounded worker."""
        super().__init__('vision_manager')
        defaults = {
            'model_path': '/home/jetson/yahboomcar_ws/src/yahboom_yolov8/'
                          'yahboom_yolov8/yolov8/weights/yolov8n.pt',
            'yolo_source_dir': '',
            'target_class': '', 'confidence': 0.4,
            'color_topic': '/camera/color/image_raw',
            'depth_topic': '/camera/depth/image_raw',
            'camera_info_topic': '/camera/color/camera_info',
            'depth_camera_info_topic': '/camera/depth/camera_info',
            'target_frame': 'base_link', 'camera_optical_frame': 'camera_color_optical_frame',
            'sync_slop_s': 2.0, 'depth_roi_half': 10, 'min_depth_m': 0.10,
            'max_depth_m': 3.0, 'find_timeout_s': 20.0, 'lost_after_s': 1.5,
            'tf_timeout_s': 0.15, 'camera_stale_s': 1.5, 'max_image_age_s': 5.0,
            'image_freshness_s': 5.0,
            'bbox_depth_enabled': False, 'bbox_depth_class': '', 'real_object_height_m': 0.1,
            'uint8_depth_scale_m': 0.0, 'depth_debug': False, 'depth_debug_every_n': 10,
            'camera_info_max_age_s': 60.0, 'depth_registered': True,
            'continuous_mode': False, 'request_cache_size': 256,
            'max_fps': 8.0, 'idle_fps': 2.0, 'imgsz': 416, 'device': '',
            'inference_timeout_s': 5.0, 'model_load_timeout_s': 45.0,
            'model_retries': 2, 'retry_backoff_s': 2.0,
            'smoothing_alpha': 0.65, 'smoothing_max_jump_m': 0.3,
            'track_min_iou': 0.3, 'color_min_fraction': 0.25,
            'tracking_backend': 'yolo', 'tracker_factory': '',
            'transformer_model_path': str(Path('~/MODELS/tracker/super_track_sim.onnx')
                                          .expanduser()),
            'transformer_refresh_frames': 15, 'volume_thickness_m': 0.0,
            'volume_shape': 'cuboid', 'publish_depth_image': False,
            'depth_view_fps': 2.0, 'depth_probe_u': -1, 'depth_probe_v': -1,
        }
        for name, value in defaults.items():
            self.declare_parameter(name, value)
        self._validate_configuration()
        self._request = {'target': self._param('target_class'), 'mission_id': '', 'action_id': ''}
        self._class, self._color = split_target(self._request['target'])
        self._searching = False
        self._idle_logged = False
        self._seen_requests: OrderedDict[tuple[str, str, str, str | None], None] = OrderedDict()
        self._deadline: float | None = None
        self._announced = False
        self._last_seen: float | None = None
        self._last_camera: float | None = None
        self._latest_depth: Image | None = None
        self._last_submit = 0.0
        self._last_depth_view = 0.0
        self._camera_info: CameraInfo | None = None
        self._camera_info_received: float | None = None
        self._depth_camera_info: CameraInfo | None = None
        self._depth_camera_info_received: float | None = None
        self._depth_notices: dict[str, str] = {}
        self._depth_debug_frames = 0
        self._track = TargetTrack(self._param('track_min_iou'))
        self._filter = PositionFilter(self._param('smoothing_alpha'), self._param('lost_after_s'),
                                      self._param('smoothing_max_jump_m'))
        self._bridge = CvBridge()
        self._tf_buffer = tf2_ros.Buffer()
        self._tf_listener = tf2_ros.TransformListener(self._tf_buffer, self, spin_thread=False)
        self._event_pub = self.create_publisher(String, '/eira/vision/event', 10)
        self._pose_pub = self.create_publisher(PoseStamped, '/target_pose', 10)
        self._image_pub = self.create_publisher(Image, '/eira/detect_image', 2)
        self._depth_pub = self.create_publisher(Image, '/eira/depth_image', 2)
        self._distance_pub = self.create_publisher(String, '/eira/depth_distance', 2)
        self.create_subscription(Image, self._param('depth_topic'), self._on_depth,
                                 qos_profile_sensor_data)
        self.create_subscription(String, '/eira/vision_target', self._on_target, 10)
        self.create_subscription(CameraInfo, self._param('camera_info_topic'),
                                 self._on_camera_info, qos_profile_sensor_data)
        self.create_subscription(CameraInfo, self._param('depth_camera_info_topic'),
                                 self._on_depth_camera_info, qos_profile_sensor_data)
        self._color_sub = self.create_subscription(
            Image, self._param('color_topic'), self._on_color, qos_profile_sensor_data)
        self._worker = InferenceWorker()
        self._pending: Future | None = None
        self._pending_context: ImageContext | None = None
        self._pending_started = 0.0
        self._pending_timed_out = False
        self._model: Any = None
        self._model_labels: set[str] | None = None
        self._transformer: Any = None
        self._transformer_ready = False
        self._transformer_label = ''
        self._frames = 0
        self._load_attempts = 0
        self._inference_errors = 0
        self._next_load = 0.0
        self._generation = 0
        self._reload_requested = False
        self._warnings: dict[str, float] = {}
        self._search_issue = ''
        self.create_timer(0.05, self._poll_worker)
        self.create_timer(0.2, self._housekeeping)
        self.add_on_set_parameters_callback(self._on_parameters)
        self._log('ready', backend=self._param('tracking_backend'))
        self._log_idle()

    def _param(self, name: str) -> Any:
        """Read a declared parameter.

        Args:
            name: Parameter name.

        Returns:
            Parameter value.
        """
        return self.get_parameter(name).value

    def _validate_configuration(self) -> None:
        """Reject invalid runtime limits before subscribing to hardware.

        Raises:
            ValueError: If a limit, frame, or selected backend is invalid.
        """
        for name in ('max_fps', 'idle_fps', 'inference_timeout_s', 'model_load_timeout_s',
                     'find_timeout_s', 'lost_after_s', 'camera_stale_s', 'max_image_age_s',
                     'tf_timeout_s', 'camera_info_max_age_s', 'depth_view_fps',
                     'image_freshness_s', 'sync_slop_s', 'real_object_height_m'):
            if not math.isfinite(float(self._param(name))) or self._param(name) <= 0:
                raise ValueError(f'{name} must be positive and finite')
        if self._param('tracking_backend') not in ('yolo', 'transformer'):
            raise ValueError('tracking_backend must be yolo or transformer')
        if not 0 < self._param('confidence') <= 1 or not (
                0 <= self._param('color_min_fraction') <= 1):
            raise ValueError('confidence/color fraction out of range')
        if self._param('model_retries') < 0 or self._param('depth_roi_half') < 0:
            raise ValueError('retry count and depth ROI must be nonnegative')
        if not isinstance(self._param('continuous_mode'), bool):
            raise ValueError('continuous_mode must be a boolean')
        if self._param('request_cache_size') < 1:
            raise ValueError('request_cache_size must be positive')
        if not all(isinstance(self._param(name), bool) for name in (
                'bbox_depth_enabled', 'depth_debug')):
            raise ValueError('depth debug and bbox estimate switches must be booleans')
        if not isinstance(self._param('bbox_depth_class'), str):
            raise ValueError('bbox_depth_class must be a class label')
        if not isinstance(self._param('depth_debug_every_n'), int) or self._param(
                'depth_debug_every_n') < 1:
            raise ValueError('depth_debug_every_n must be a positive integer')
        if not math.isfinite(self._param('uint8_depth_scale_m')) or self._param(
                'uint8_depth_scale_m') < 0:
            raise ValueError('uint8_depth_scale_m must be nonnegative and finite')
        if self._param('min_depth_m') <= 0 or (
                self._param('max_depth_m') <= self._param('min_depth_m')):
            raise ValueError('invalid depth range')
        if self._param('volume_shape') not in ('cuboid', 'cylinder'):
            raise ValueError('volume_shape must be cuboid or cylinder')
        if self._param('volume_thickness_m') < 0 or self._param('transformer_refresh_frames') < 1:
            raise ValueError('invalid volume thickness or tracker refresh period')

    def _on_parameters(self, parameters: list) -> SetParametersResult:
        """Validate live settings and defer backend changes until the worker is idle.

        Args:
            parameters: Proposed ROS parameter changes.

        Returns:
            Whether this atomic update is accepted.
        """
        values = {parameter.name: parameter.value for parameter in parameters}
        positive = {'max_fps', 'idle_fps', 'inference_timeout_s', 'model_load_timeout_s',
                    'find_timeout_s', 'lost_after_s', 'camera_stale_s', 'max_image_age_s',
                    'tf_timeout_s', 'camera_info_max_age_s', 'imgsz',
                    'transformer_refresh_frames', 'sync_slop_s', 'request_cache_size'}
        positive.update({'image_freshness_s', 'real_object_height_m', 'depth_debug_every_n'})
        for name, value in values.items():
            if name in positive and (not isinstance(value, (int, float)) or
                                     not math.isfinite(value) or value <= 0):
                return SetParametersResult(successful=False, reason=f'invalid {name}')
        if 'continuous_mode' in values and not isinstance(values['continuous_mode'], bool):
            return SetParametersResult(successful=False, reason='continuous_mode must be boolean')
        if any(name in values and not isinstance(values[name], bool)
               for name in ('bbox_depth_enabled', 'depth_debug')):
            return SetParametersResult(successful=False, reason='depth switches must be boolean')
        if 'bbox_depth_class' in values and not isinstance(values['bbox_depth_class'], str):
            return SetParametersResult(successful=False, reason='bbox_depth_class must be a label')
        for name in ('depth_roi_half', 'uint8_depth_scale_m'):
            if name in values and (not isinstance(values[name], (int, float)) or
                                   not math.isfinite(values[name]) or values[name] < 0):
                return SetParametersResult(successful=False, reason=f'invalid {name}')
        if any(name in values and (isinstance(values[name], bool) or not isinstance(
                values[name], int)) for name in ('depth_roi_half', 'depth_debug_every_n')):
            return SetParametersResult(successful=False,
                                       reason='pixel/count settings need integers')
        if values.get('tracking_backend', self._param('tracking_backend')) not in (
                'yolo', 'transformer'):
            return SetParametersResult(successful=False, reason='unknown tracking backend')
        if values.get('volume_shape', self._param('volume_shape')) not in ('cuboid', 'cylinder'):
            return SetParametersResult(successful=False, reason='unknown volume shape')
        for name in ('smoothing_alpha', 'confidence', 'color_min_fraction', 'track_min_iou'):
            if name in values and (not isinstance(values[name], (int, float)) or
                                   not 0 < values[name] <= 1):
                return SetParametersResult(successful=False, reason=f'invalid {name}')
        if 'target_frame' in values or 'color_topic' in values or 'depth_topic' in values or (
                'camera_info_topic' in values or 'depth_camera_info_topic' in values):
            return SetParametersResult(successful=False,
                                       reason='frame and topic changes require a restart')
        if 'sync_slop_s' in values:
            return SetParametersResult(successful=False, reason='sync tolerance requires restart')
        if {'tracking_backend', 'tracker_factory', 'transformer_model_path', 'model_path',
                'yolo_source_dir',
                'device'} & values.keys():
            self._reload_requested = True
        if values.get('continuous_mode') is False and not self._searching:
            self._finish_search(cancel_pending=True)
            self._idle_logged = False
        return SetParametersResult(successful=True)

    def _log_idle(self) -> None:
        """Log demand-mode idleness once rather than on every dropped camera frame."""
        if not self._param('continuous_mode') and not self._searching and not self._idle_logged:
            self._idle_logged = True
            self._log('idle', detail='idle (no active search)')

    def _finish_search(self, cancel_pending: bool = False) -> None:
        """End a bounded request and invalidate its late image results.

        Args:
            cancel_pending: Terminate outstanding native work when stopping or timing out.
        """
        self._searching = False
        self._deadline = None
        self._generation += 1
        if cancel_pending and self._pending is not None:
            self._worker.close()
            self._pending = None
            self._pending_context = None
            self._model = None
            self._next_load = time.monotonic() + self._param('retry_backoff_s')
        self._log_idle()

    def _on_camera_info(self, msg: CameraInfo) -> None:
        """Cache a validated calibration.

        Args:
            msg: Live camera intrinsics.
        """
        if self._valid_camera_info(msg):
            self._camera_info = msg
            self._camera_info_received = time.monotonic()

    def _on_depth_camera_info(self, msg: CameraInfo) -> None:
        """Cache the calibration corresponding to the depth optical raster.

        Args:
            msg: Depth CameraInfo, separate from the color camera model.
        """
        if self._valid_camera_info(msg):
            self._depth_camera_info = msg
            self._depth_camera_info_received = time.monotonic()

    @staticmethod
    def _valid_camera_info(msg: CameraInfo) -> bool:
        """Check that intrinsics and calibration raster dimensions are usable.

        Args:
            msg: Candidate camera model.
        Returns:
            Whether focal lengths, K and raster dimensions are finite and positive.
        """
        return (msg.width > 0 and msg.height > 0 and len(msg.k) == 9
                and all(math.isfinite(v) for v in msg.k) and min(msg.k[0], msg.k[4]) > 0)

    def _camera_snapshot(self, depth: bool = False) -> CameraInfo | None:
        """Copy a fresh calibration so later callbacks cannot change a queued frame.

        Args:
            depth: Select depth rather than color CameraInfo.
        Returns:
            An independent valid calibration, or None when unavailable/stale.
        """
        prefix = '_depth_camera_info' if depth else '_camera_info'
        info = getattr(self, prefix, None)
        received = getattr(self, prefix + '_received', None)
        if info is None or received is None or time.monotonic() - received > self._param(
                'camera_info_max_age_s') or not self._valid_camera_info(info):
            return None
        return deepcopy(info)

    def _depth_notice(self, key: str, message: str, warning: bool = False) -> None:
        """Log a camera configuration observation only when its value changes.

        Args:
            key: Stable notice category.
            message: Readable diagnostic.
            warning: Use a fixed warning call site instead of the fixed INFO site.
        """
        notices = getattr(self, '_depth_notices', {})
        if notices.get(key) == message:
            return
        notices[key] = message
        self._depth_notices = notices
        line = format_line('VISION', message, 'warning' if warning else 'info')
        if warning:
            self.get_logger().warning(line)
        else:
            self.get_logger().info(line)

    def _log_depth_format(self, image: Image) -> None:
        """Report the actual depth encoding and native dimensions on first receipt.

        Args:
            image: Depth message metadata, without converting its pixels.
        """
        self._depth_notice('encoding', f'Depth encoding: {sanitize_text(image.encoding)}, '
                           f'size: {image.width}x{image.height}')

    def _decode_depth(self, image: Image) -> np.ndarray:
        """Normalize metric depth or leave unknown units unavailable for the size fallback.

        Args:
            image: Depth message with explicit ROS encoding.
        Returns:
            Native-sized metre image; unsupported units become NaNs.
        Raises:
            CvBridgeError: The message cannot be decoded by cv_bridge.
            ValueError: The decoded image has no two-dimensional raster.
        """
        pixels = self._bridge.imgmsg_to_cv2(image, desired_encoding='passthrough')
        try:
            return normalize_depth(pixels, image.encoding, self._param('uint8_depth_scale_m'))
        except ValueError as exc:
            if pixels.ndim != 2 or min(pixels.shape) <= 0:
                raise
            self._depth_notice('unsupported_encoding',
                               f'Depth encoding {sanitize_text(image.encoding)} unavailable: '
                               f'{sanitize_text(exc)}; metric depth will not be guessed', True)
            return np.full(pixels.shape, np.nan, dtype=np.float64)

    def _on_target(self, msg: String) -> None:
        """Start one demand search, refresh its acquisition, or cancel a matching mission.

        Args:
            msg: Plain class name or JSON target envelope.
        """
        try:
            envelope = json.loads(msg.data) if msg.data.lstrip().startswith('{') else {}
            if not isinstance(envelope, dict):
                raise ValueError('vision request must be an object')
            if 'cancel' in envelope and not isinstance(envelope['cancel'], bool):
                raise ValueError('cancel must be a boolean')
            refresh = envelope.get('refresh_id')
            if refresh is not None and (isinstance(refresh, bool) or not isinstance(
                    refresh, (str, int)) or not str(refresh).strip()):
                raise ValueError('refresh_id must be a nonempty string or integer')
            refresh = None if refresh is None else str(refresh)
            request = target_request(msg.data)
        except (ValueError, TypeError) as exc:
            self._warn('invalid_request', str(exc))
            return
        if envelope.get('cancel'):
            matches = (request['mission_id'] == self._request.get('mission_id')
                       if request['mission_id'] else request == self._request)
            if matches:
                self._finish_search(cancel_pending=True)
                self._announced = False
                self._track.reset()
                self._filter.reset()
                self._log('search_canceled', **request)
            return
        if request == self._request and self._searching:
            return
        if request == self._request and self._announced and refresh is None and (
                request['mission_id'] or request['action_id']):
            return
        key = (request['mission_id'], request['action_id'], request['target'], refresh)
        correlated = bool(request['mission_id'] or request['action_id'] or refresh is not None)
        if correlated and key in self._seen_requests:
            return
        if correlated:
            self._seen_requests[key] = None
            while len(self._seen_requests) > self._param('request_cache_size'):
                self._seen_requests.popitem(last=False)
        preserve_track = (refresh is not None and request['target'] == self._request.get('target')
                          and request['mission_id'] == self._request.get('mission_id'))
        self._request = request
        self._class, self._color = split_target(request['target'])
        self._generation += 1
        if not preserve_track:
            self._track.reset()
            self._filter.reset()
        self._transformer_ready = False
        self._announced = False
        self._last_seen = None
        self._search_issue = ''
        self._searching = True
        self._idle_logged = False
        if self._model is None and self._pending is None:
            self._load_attempts = 0
            self._inference_errors = 0
        self._deadline = (time.monotonic() + self._param('find_timeout_s')
                          if self._model is not None else None)
        self._log('search_started', **request, refresh_id=refresh)
        self._check_target_class()

    def _check_target_class(self) -> None:
        """Reject classes absent from the loaded weights with a correlated explanation."""
        labels = getattr(self, '_model_labels', None)
        if self._model is None or not self._searching or not labels or self._class in labels:
            return
        self._emit('failed', reason='unsupported_target',
                   detail=f"The loaded YOLO model cannot detect '{self._class}'. "
                          'Use weights trained for that class or request a supported class.',
                   supported_classes=sorted(labels))
        self._finish_search()

    def _on_depth(self, msg: Image) -> None:
        """Publish optional exercise-26/27 depth views and metric distance probes.

        Args:
            msg: uint16 millimeter or floating-point meter depth image.
        """
        self._latest_depth = msg
        self._log_depth_format(msg)
        now = time.monotonic()
        if now - self._last_depth_view < 1.0 / self._param('depth_view_fps'):
            return
        if not self._param('publish_depth_image') and not (
                self._distance_pub.get_subscription_count()):
            return
        self._last_depth_view = now
        try:
            self._check_image_time(msg)
            depth = self._decode_depth(msg)
            height, width = depth.shape
            u, v = self._param('depth_probe_u'), self._param('depth_probe_v')
            u = width // 2 if u < 0 else u
            v = height // 2 if v < 0 else v
            if not 0 <= u < width or not 0 <= v < height:
                raise ValueError('depth probe pixel is outside the image')
            half = self._param('depth_roi_half')
            roi = depth[max(0, v - half):v + half + 1, max(0, u - half):u + half + 1]
            valid = roi[np.isfinite(roi) & (roi >= self._param('min_depth_m')) &
                        (roi <= self._param('max_depth_m'))]
            distance = float(np.median(valid)) if valid.size else None
            self._distance_pub.publish(String(data=json.dumps({
                'pixel': [u, v], 'distance_m': distance, 'frame_id': msg.header.frame_id,
                'stamp_s': msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9})))
            if self._param('publish_depth_image') and self._depth_pub.get_subscription_count():
                lo, hi = self._param('min_depth_m'), self._param('max_depth_m')
                scaled = np.nan_to_num(np.clip((depth - lo) / (hi - lo), 0, 1))
                pixels = (scaled * 255).astype(np.uint8)
                output = cv2.applyColorMap(pixels, cv2.COLORMAP_JET)
                output[~np.isfinite(depth) | (depth <= 0)] = 0
                cv2.drawMarker(output, (u, v), (255, 255, 255), cv2.MARKER_CROSS)
                image = self._bridge.cv2_to_imgmsg(output, encoding='bgr8')
                image.header = msg.header
                self._depth_pub.publish(image)
        except (CvBridgeError, cv2.error, ValueError, TypeError, IndexError) as exc:
            self._warn('depth_view_error', str(exc))

    def _on_color(self, color: Image) -> None:
        """Schedule RGB detection independently of depth availability.

        Args:
            color: Original RGB measurement from the camera's sensor-data stream.
        """
        depth = getattr(self, '_latest_depth', None)
        if depth is not None:
            color_ns = Time.from_msg(color.header.stamp).nanoseconds
            depth_ns = Time.from_msg(depth.header.stamp).nanoseconds
            if depth_ns <= 0 or abs(color_ns - depth_ns) * 1e-9 > self._param('sync_slop_s'):
                depth = None
        self._on_synced_images(color, depth)

    def _on_synced_images(self, color: Image, depth: Image | None) -> None:
        """Queue at most one RGB inference with optional captured metric depth.

        Args:
            color: RGB image with measurement timestamp.
            depth: Nearby depth acquisition, or None when depth is missing/unpairable.
        """
        self._last_camera = time.monotonic()
        try:
            if not self._param('continuous_mode') and not self._searching:
                self._log_idle()
                return
            if self._pending is not None or self._model is None:
                return
            rate = self._param('max_fps') if self._searching or self._announced else self._param(
                'idle_fps')
            if self._last_camera - self._last_submit < 1.0 / rate:
                return
            self._check_image_time(color)
            frame = self._bridge.imgmsg_to_cv2(color, desired_encoding='bgr8')
            if frame.ndim != 3 or frame.shape[2] != 3 or frame.dtype != np.uint8 or not frame.size:
                raise ValueError('RGB conversion must produce an 8-bit, three-channel BGR image')
            depth_m = None
            original_size = (0, 0)
            if depth is not None:
                self._log_depth_format(depth)
                original_size = (depth.width, depth.height)
                try:
                    self._check_image_time(depth)
                    if not self._param('depth_registered'):
                        raise ValueError('enable camera depth_registration for measured 3D poses')
                    depth_m = self._decode_depth(depth)
                    original_size = (depth_m.shape[1], depth_m.shape[0])
                except (CvBridgeError, cv2.error, ValueError, TypeError, IndexError) as exc:
                    self._warn('depth_unavailable', f'{exc}; RGB detection remains active')
                    depth = None
            else:
                self._depth_notice('depth_stream', 'No matching depth frame; RGB detection '
                                   'remains active. Check the depth topic and camera timestamps',
                                   True)
            if depth_m is None:
                depth_m = np.full(frame.shape[:2], np.nan, dtype=np.float64)
            if frame.shape[:2] != depth_m.shape:
                self._depth_notice('resize', f'Depth/color dimensions differ: '
                                   f'{original_size[0]}x{original_size[1]} vs '
                                   f'{frame.shape[1]}x{frame.shape[0]}; resizing registered '
                                   'depth with nearest-neighbor (not camera registration)', True)
                depth_m = resize_depth(depth_m, frame.shape[1], frame.shape[0])
            self._last_submit = self._last_camera
            self._pending_context = ImageContext(
                self._generation, frame, depth_m, color, depth,
                self._camera_snapshot(), self._camera_snapshot(depth=True), original_size)
            options = {key: self._param(key) for key in (
                'confidence', 'imgsz', 'device', 'transformer_refresh_frames',
                'color_min_fraction')}
            self._submit('infer', {'frame': frame, 'generation': self._generation,
                                   'class': self._class, 'color': self._color, **options})
        except (CvBridgeError, cv2.error, ValueError, TypeError, RuntimeError, IndexError) as exc:
            self._warn('frame_rejected', str(exc))

    def _check_image_time(self, image: Image) -> float:
        """Warn about processing latency while retaining the real acquisition timestamp.

        Args:
            image: Sensor image whose timestamp uses the ROS clock.
        Returns:
            Actual message age in seconds; old valid frames are still processed.
        Raises:
            ValueError: If a measurement is unstamped or implausibly future-dated.
        """
        stamp = Time.from_msg(image.header.stamp).nanoseconds
        age = (self.get_clock().now().nanoseconds - stamp) * 1e-9
        if stamp <= 0 or age < -self._param('sync_slop_s'):
            raise ValueError(f'image timestamp invalid: age={age:.3f}s')
        if age > self._param('image_freshness_s'):
            self._warn('image_stale', f'image timestamp outside freshness window: '
                       f'age={age:.3f}s; still processing the original frame')
        return age

    def _submit(self, operation: str, payload: dict[str, Any]) -> None:
        """Submit one job to the isolated native inference process.

        Args:
            operation: Model initialization or inference operation.
            payload: Serializable settings and optional frame pixels.
        """
        self._pending_started = time.monotonic()
        self._pending_timed_out = False
        try:
            self._pending = self._worker.submit(operation, payload)
        except (OSError, RuntimeError, ValueError) as exc:
            self._pending = Future()
            self._pending.set_exception(RuntimeError(f'inference process unavailable: {exc}'))

    def _poll_worker(self) -> None:
        """Collect jobs, discard late results and retry initialization with a fixed budget."""
        now = time.monotonic()
        if hasattr(self, '_worker'):
            self._worker.poll()
        if self._pending is None:
            if self._reload_requested:
                self._reload_requested = False
                self._model = None
                self._transformer = None
                self._transformer_ready = False
                self._load_attempts = 0
                self._next_load = 0.0
                self._generation += 1
                self._track.reset()
                self._filter.reset()
                if self._searching:
                    self._deadline = None
            load_needed = (self._param('continuous_mode') or self._searching
                           or self._load_attempts == 0)
            if self._model is None and load_needed and now >= self._next_load and (
                    self._load_attempts <= self._param('model_retries')):
                self._load_attempts += 1
                self._pending_context = None
                settings = {key: self._param(key) for key in (
                    'model_path', 'tracking_backend', 'tracker_factory',
                    'transformer_model_path', 'track_min_iou', 'yolo_source_dir',
                    'imgsz', 'device', 'confidence', 'lost_after_s')}
                self._log('model_loading')
                self._submit('load', settings)
            return
        loading = self._pending_context is None
        timeout = self._param('model_load_timeout_s' if loading else 'inference_timeout_s')
        if not self._pending.done():
            if now - self._pending_started > timeout and not self._pending_timed_out:
                self._pending_timed_out = True
                self._emit('timeout', reason='model_load_timeout' if loading
                           else 'inference_timeout')
                self._warn('worker_timeout',
                           'native inference process terminated; retry budget is bounded')
                self._worker.close()
                self._pending = None
                self._pending_context = None
                self._model = None
                self._next_load = now + self._param('retry_backoff_s')
                if not self._param('continuous_mode'):
                    self._finish_search()
            return
        pending, context = self._pending, self._pending_context
        self._pending = None
        self._pending_context = None
        try:
            result = pending.result()
            if loading:
                self._model = True
                self._model_labels = set(result.get('supported_classes', [])) or None
                self._transformer = True if result.get('transformer_available') else None
                if result.get('warning'):
                    self._warn('transformer_unavailable', result['warning'])
                self._log('model_loaded', attempts=self._load_attempts,
                          model_source=result.get('model_source', ''))
                if self._searching and self._deadline is None:
                    self._deadline = now + self._param('find_timeout_s')
                self._check_target_class()
            elif not self._pending_timed_out and not self._reload_requested and (
                    context[0] == self._generation) and (
                    self._param('continuous_mode') or self._searching):
                self._inference_errors = 0
                try:
                    self._process_result(result, context)
                except (AttributeError, ValueError, TypeError, IndexError, KeyError,
                        cv2.error, CvBridgeError, OverflowError) as exc:
                    self._warn('geometry_error', f'{exc}; detector remains available')
        except (ImportError, AttributeError, OSError, RuntimeError, ValueError, TypeError,
                IndexError, KeyError, cv2.error, CvBridgeError, OverflowError) as exc:
            self._warn('model_error' if loading else 'processing_error', str(exc))
            if loading:
                self._next_load = now + self._param('retry_backoff_s')
                if self._load_attempts > self._param('model_retries'):
                    self._emit('failed', reason='model_unavailable', detail=str(exc))
                    if not self._param('continuous_mode'):
                        self._finish_search()
            else:
                self._inference_errors = getattr(self, '_inference_errors', 0) + 1
                if self._inference_errors > self._param('model_retries'):
                    self._emit('failed', reason='inference_retry_budget_exhausted', detail=str(exc))
                    self._worker.close()
                    self._model = None
                    self._load_attempts = self._param('model_retries') + 1
                    if not self._param('continuous_mode'):
                        self._finish_search()

    def _process_result(self, detections: list[Detection], context: ImageContext) -> None:
        """Fuse a detection with its captured depth/model; mark estimated ranges explicitly.

        Args:
            detections: Backend output for the queued color frame.
            context: Original RGB-D pair and corresponding calibration snapshots.
        """
        frame, depth, color = context.frame, context.depth, context.color_image
        candidates = [d for d in detections if d.label == self._class and color_fraction(
            frame, d.box, self._color) >= self._param('color_min_fraction')]
        target = self._track.select(candidates)
        self._annotate(frame, detections, target, color)
        if target is None:
            self._depth_notice('pipeline', f'YOLO is processing RGB; waiting for '
                               f'{sanitize_text(self._request["target"])} '
                               f'(confidence threshold {self._param("confidence"):.0%})')
            return
        color_age = self._check_image_time(color)
        depth_age = (self._check_image_time(context.depth_image)
                     if context.depth_image is not None else None)
        if context.color_info is not None and color.header.frame_id and (
                context.color_info.header.frame_id and
                context.color_info.header.frame_id != color.header.frame_id):
            self._depth_notice('color_frame', 'Color CameraInfo frame differs from RGB image; '
                               'ignoring the mismatched calibration', True)
            context = context._replace(color_info=None)
        try:
            intrinsics, optical_frame, model_source = self._depth_model(context)
        except ValueError as exc:
            self._warn('camera_info_missing', f'{exc}; bounding boxes remain available')
            return
        fx, fy, cx, cy = intrinsics
        sample = sample_depth(depth, target.box, self._param('depth_roi_half'),
                              self._param('min_depth_m'), self._param('max_depth_m'))
        distance, depth_source = sample.distance_m, sample.source
        if sample.roi_median_m is None:
            self._warn('depth_roi_empty', 'Depth unavailable at ROI, trying full box')
        if distance is None:
            distance = self._estimate_bbox_distance(target.box, context.color_info,
                                                    frame.shape[1], frame.shape[0])
            if distance is None:
                self._warn('no_valid_depth', error_hint('no valid depth'))
                self._debug_depth(context, target.box, sample, intrinsics)
                return
            depth_source = 'bbox_estimate'
            self._warn('bbox_depth_estimate', f'Distance {distance:.2f}m estimated from bbox '
                       f'(calibrated {self._class} height '
                       f'{self._param("real_object_height_m"):.3f}m)')
            # Height-based ranging follows the color camera ray, not a raw depth model.
            intrinsics = scale_intrinsics(context.color_info.k, context.color_info.width,
                                          context.color_info.height,
                                          frame.shape[1], frame.shape[0])
            fx, fy, cx, cy = intrinsics
            optical_frame = context.color_info.header.frame_id or color.header.frame_id or (
                self._param('camera_optical_frame'))
            model_source = 'color_bbox_estimate'
        self._debug_depth(context, target.box, sample, intrinsics)
        u = float(np.clip((target.box[0] + target.box[2]) / 2, 0, depth.shape[1] - 1))
        v = float(np.clip((target.box[1] + target.box[3]) / 2, 0, depth.shape[0] - 1))
        ui, vi = int(round(u)), int(round(v))
        estimated = depth_source == 'bbox_estimate'
        measurement = color if estimated else context.depth_image
        if measurement is None:
            return
        measurement_ns = Time.from_msg(measurement.header.stamp).nanoseconds
        stamp = measurement_ns * 1e-9
        measurement_source = (estimated, optical_frame)
        if getattr(self, '_last_measurement_source', None) == measurement_source and (
                self._filter.stamp is not None and stamp <= self._filter.stamp):
            # RGB can arrive faster than depth; never reissue one depth capture as a new pose.
            return
        point = PointStamped()
        point.header = deepcopy(measurement.header)
        point.header.frame_id = optical_frame
        point.point.x = (u - cx) * distance / fx
        point.point.y = (v - cy) * distance / fy
        point.point.z = distance
        try:
            transformed = self._tf_buffer.transform(
                point, self._param('target_frame'),
                timeout=Duration(seconds=self._param('tf_timeout_s')))
        except (tf2_ros.TransformException, TypeException) as exc:
            self._warn('tf_error', str(exc))
            return
        p = transformed.point
        if getattr(self, '_last_measurement_source', None) != measurement_source:
            self._filter.reset()
        self._last_measurement_source = measurement_source
        x, y, z = self._filter.update((p.x, p.y, p.z), stamp)
        pose = PoseStamped()
        pose.header = transformed.header
        pose.pose.position.x, pose.pose.position.y, pose.pose.position.z = x, y, z
        pose.pose.orientation.w = 1.0
        self._pose_pub.publish(pose)
        self._last_seen = time.monotonic()
        self._depth_notice('pipeline', 'Target localized; calibrated pose published')
        if not self._announced:
            self._announced = True
            self._searching = False
            # Bounding boxes are expressed in color pixels, even when depth has its own K.
            size_model = intrinsics if context.color_info is None else scale_intrinsics(
                context.color_info.k, context.color_info.width, context.color_info.height,
                frame.shape[1], frame.shape[0])
            dimensions = object_dimensions(target.box, distance, size_model[0], size_model[1],
                                           self._param('volume_thickness_m'),
                                           self._param('volume_shape'))
            depth_ns = (Time.from_msg(context.depth_image.header.stamp).nanoseconds
                        if context.depth_image is not None else None)
            color_ns = Time.from_msg(color.header.stamp).nanoseconds
            self._emit('found', label=target.label, color=self._color,
                       confidence=target.confidence, depth_m=distance, track_id=target.track_id,
                       pixel=[ui, vi], measurement_stamp_ns=measurement_ns,
                       color_stamp_ns=color_ns, depth_stamp_ns=depth_ns,
                       color_age_s=color_age, depth_age_s=depth_age,
                       pair_skew_s=abs(color_ns - depth_ns) * 1e-9
                       if depth_ns is not None else None,
                       depth_source=depth_source, depth_estimated=estimated,
                       intrinsics_source=model_source,
                       depth_resized=depth_ns is not None and context.original_depth_size != (
                           frame.shape[1], frame.shape[0]),
                       assumed_object_height_m=self._param('real_object_height_m')
                       if estimated else None, **dimensions)
            if not self._param('continuous_mode'):
                self._finish_search()

    def _depth_model(self, context: ImageContext
                     ) -> tuple[tuple[float, float, float, float], str, str]:
        """Select a matching camera model and scale it to the resized sampling raster.

        Args:
            context: Captured depth image, raster and camera-model snapshots.
        Returns:
            Intrinsics, source optical frame, and camera-model provenance.
        Raises:
            ValueError: No usable matching depth or fallback color model exists.
        """
        info = context.depth_info if context.depth_image is not None else None
        image_frame = (context.depth_image.header.frame_id
                       if context.depth_image is not None else '')
        if info is not None and image_frame and info.header.frame_id and (
                image_frame != info.header.frame_id):
            self._depth_notice('intrinsics_frame', 'Depth CameraInfo frame differs from depth '
                               'image; ignoring the mismatched calibration', True)
            info = None
        source = 'depth'
        if info is None:
            info = context.color_info
            source = 'color_approximation'
            self._depth_notice('color_intrinsics', 'Using color intrinsics for depth '
                               '(approximation)', True)
        if info is None:
            raise ValueError('missing or stale CameraInfo; cannot deproject target')
        height, width = context.depth.shape
        intrinsics = scale_intrinsics(info.k, info.width, info.height, width, height)
        frame = info.header.frame_id or image_frame or self._param('camera_optical_frame')
        return intrinsics, frame, source

    def _estimate_bbox_distance(self, box: tuple[float, float, float, float],
                                color_info: CameraInfo | None, width: int,
                                height: int) -> float | None:
        """Estimate range only for an explicitly calibrated object class.

        Args:
            box: Detector coordinates in the original color raster.
            color_info: Color model matching those detector coordinates.
            width: Color raster width.
            height: Color raster height.
        Returns:
            Estimated axial range in metres, or None if disabled/invalid/out of range.
        """
        if not self._param('bbox_depth_enabled') or color_info is None:
            return None
        calibrated_class = self._param('bbox_depth_class').strip().lower()
        if not calibrated_class or self._class != calibrated_class:
            return None
        _, fy, _, _ = scale_intrinsics(
            color_info.k, color_info.width, color_info.height, width, height)
        distance = estimate_bbox_depth(box, fy, self._param('real_object_height_m'))
        if distance is None or not self._param('min_depth_m') <= distance <= self._param(
                'max_depth_m'):
            return None
        return distance

    def _debug_depth(self, context: ImageContext, box: tuple[float, float, float, float],
                     sample: DepthSample, intrinsics: tuple[float, float, float, float]) -> None:
        """Print requested sampling diagnostics for every Nth detected target frame.

        Args:
            context: Original camera dimensions/encoding and sampled metric raster.
            box: Current detected target rectangle.
            sample: ROI/full-box diagnostics with unavailable values represented by None.
            intrinsics: Model scaled to the actual depth sampling raster.
        """
        if not self._param('depth_debug'):
            return
        self._depth_debug_frames = getattr(self, '_depth_debug_frames', 0) + 1
        if self._depth_debug_frames % self._param('depth_debug_every_n'):
            return

        def metres(value: float | None) -> str:
            """Format a possibly missing diagnostic without inventing a range.

            Args:
                value: Raw/median/range endpoint, or None.
            Returns:
                Readable metric value or an unavailable label.
            """
            return f'{value:.3f}m' if value is not None else 'unavailable'

        fx, fy, cx, cy = intrinsics
        encoding = (sanitize_text(context.depth_image.encoding)
                    if context.depth_image is not None else 'unavailable')
        for message in (
                f'Depth at bbox center: {metres(sample.center_m)}, '
                f'encoding: {encoding}',
                f'Depth ROI median: {metres(sample.roi_median_m)}, '
                f'valid pixels: {sample.roi_valid}/{sample.roi_total}',
                f'Depth range in bbox: min={metres(sample.bbox_min_m)}, '
                f'max={metres(sample.bbox_max_m)}',
                f'Color image size: {context.frame.shape[1]}x{context.frame.shape[0]}, '
                f'Depth image size: {context.original_depth_size[0]}x'
                f'{context.original_depth_size[1]}',
                f'Camera intrinsics: fx={fx:.3f}, fy={fy:.3f}, cx={cx:.3f}, cy={cy:.3f}'):
            self.get_logger().info(format_line('VISION DEPTH', message))

    def _annotate(self, frame: np.ndarray, detections: list[Detection], target: Detection | None,
                  source: Image) -> None:
        """Publish detection visualization only when a viewer is subscribed.

        Args:
            frame: BGR image to annotate.
            detections: All objects from the selected backend.
            target: Locked target, if visible.
            source: Original timestamp/frame metadata.
        """
        if not self._image_pub.get_subscription_count():
            return
        output = frame.copy()
        for detection in detections:
            x0, y0, x1, y1 = (int(v) for v in detection.box)
            color = (0, 255, 0) if detection is target else (128, 128, 128)
            cv2.rectangle(output, (x0, y0), (x1, y1), color, 2)
            cv2.putText(output, f'{detection.label} #{detection.track_id}',
                        (x0, max(14, y0)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        message = self._bridge.cv2_to_imgmsg(output, encoding='bgr8')
        message.header = source.header
        self._image_pub.publish(message)

    def _housekeeping(self) -> None:
        """Detect acquisition deadlines, pose gaps and entirely frozen camera streams."""
        now = time.monotonic()
        if not self._param('continuous_mode') and not self._searching:
            self._log_idle()
            return
        if self._model is None:
            self._depth_notice('pipeline', 'Waiting for YOLO model initialization; '
                               'the search timer starts when the model is ready')
        elif self._last_camera is None or now - self._last_camera > self._param(
                'camera_stale_s'):
            self._depth_notice('pipeline', f'Waiting for RGB images on '
                               f'{sanitize_text(self._param("color_topic"))}; '
                               'check the camera driver and topic QoS', True)
        camera_stale = self._last_camera is None or now - self._last_camera > self._param(
            'camera_stale_s')
        pose_stale = self._last_seen is None or now - self._last_seen > self._param('lost_after_s')
        if self._announced and (camera_stale or pose_stale):
            self._announced = False
            self._generation += 1
            self._track.reset()
            self._filter.reset()
            self._transformer_ready = False
            self._emit('lost', reason='camera_stale' if camera_stale else 'pose_stale')
        if self._searching and self._deadline is not None and now > self._deadline:
            detail = getattr(self, '_search_issue', '')
            if camera_stale:
                detail = f'No fresh RGB images on {self._param("color_topic")}; check the ' \
                         'camera driver, topic name and sensor-data QoS.'
            self._emit('timeout', reason='acquisition_timeout', **({'detail': detail} if detail
                                                                  else {}))
            self._finish_search(cancel_pending=not self._param('continuous_mode'))

    def _emit(self, event: str, **fields: Any) -> None:
        """Publish structured lifecycle events with request identity.

        Args:
            event: Lifecycle event name.
            **fields: Additional JSON-compatible measurement or failure fields.
        """
        payload = {'event': event, **self._request, 'wall_time': time.time(), **fields}
        self._event_pub.publish(String(data=json.dumps(payload, allow_nan=False)))
        self._log(event, **fields)

    def _log(self, event: str, **fields: Any) -> None:
        """Describe perception changes without repeating one-shot refresh diagnostics.

        Args:
            event: Log event name.
            **fields: Event context; full evidence remains on the ROS event topic.
        """
        request = getattr(self, '_request', {})
        target = sanitize_text(fields.get('target') or request.get('target')
                               or fields.get('label') or 'object')
        reason = sanitize_text(fields.get('reason', '')).replace('_', ' ')
        level = 'info'
        if event == 'ready':
            text = f'Ready; tracking backend: {sanitize_text(fields.get("backend", "yolo"))}'
        elif event == 'model_loading':
            text = 'Loading YOLO and warming up inference; waiting for model readiness'
        elif event == 'model_loaded':
            text = 'YOLO model ready for detection'
            if fields.get('model_source'):
                text += f' | source: {sanitize_text(fields["model_source"])}'
        elif event == 'search_started':
            text = f'Searching for {target}'
        elif event == 'found':
            details = [f'Found {target}']
            distance = fields.get('depth_m')
            confidence = fields.get('confidence')
            if isinstance(distance, (int, float)) and math.isfinite(distance):
                details.append(f'{distance:.2f} m away')
            if isinstance(confidence, (int, float)) and math.isfinite(confidence):
                details.append(f'{confidence:.0%} confidence')
            if fields.get('track_id') is not None:
                details.append(f'track {sanitize_text(fields["track_id"])}')
            if fields.get('depth_estimated'):
                details.append('estimated from bbox')
            text = ' | '.join(details)
            level = 'success'
        elif event == 'idle':
            text = 'Idle (no active search)'
        elif event == 'search_canceled':
            text = 'Search stopped'
        elif event == 'lost':
            text = f'Lost {target}' + (f': {reason}' if reason else '')
            level = 'warning'
        elif event == 'timeout':
            if fields.get('reason') == 'model_load_timeout':
                text = 'YOLO initialization timed out; check model weights, CUDA and Jetson load'
            elif fields.get('reason') == 'inference_timeout':
                text = 'YOLO frame processing timed out; check GPU memory and Jetson load'
            else:
                text = error_hint('vision: timeout', target=target,
                                  timeout_s=self._param('find_timeout_s'))
            level = 'warning'
        elif event == 'failed':
            detail = sanitize_text(fields.get('detail', ''))
            text = 'Detection failed' + (f': {detail or reason}' if detail or reason else '')
            level = 'error'
        else:
            text = sanitize_text(event).replace('_', ' ').capitalize()
        logger = self.get_logger()
        repeated = False
        if event in ('search_started', 'found', 'idle', 'search_canceled'):
            key = (request.get('mission_id'), request.get('action_id'), target,
                   fields.get('track_id') if event == 'found' else None)
            recent = getattr(self, '_console_recent', {})
            if recent.get(event) == key:
                repeated = True
            recent[event] = key
            self._console_recent = recent
        line = format_line('VISION', text, level)
        if repeated:
            logger.debug(line)
        else:
            logger.info(line)

    def _warn(self, event: str, detail: str) -> None:
        """Throttle repeated structured warnings.

        Args:
            event: Warning category.
            detail: Human-readable diagnostic.
        """
        if getattr(self, '_searching', False) and event in {
                'camera_info_missing', 'depth_unavailable', 'no_valid_depth', 'tf_error',
                'frame_rejected', 'geometry_error'}:
            self._search_issue = detail
        now = time.monotonic()
        if now >= self._warnings.get(event, 0):
            self._warnings[event] = now + self._param('retry_backoff_s')
            label = sanitize_text(event).replace('_', ' ').capitalize()
            self.get_logger().warning(format_line(
                'VISION', f'{label}: {error_hint(detail)}', 'warning'))

    def destroy_node(self) -> None:
        """Cancel queued work and tear down interfaces without waiting for inference."""
        self._worker.close()
        self._tf_listener.unregister()
        super().destroy_node()


def main(args: list[str] | None = None) -> None:
    """Run perception with orderly shutdown.

    Args:
        args: ROS command-line arguments.
    """
    rclpy.init(args=args)
    node = None
    executor = MultiThreadedExecutor(num_threads=2)
    try:
        node = VisionManager()
        executor.add_node(node)
        executor.spin()
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        executor.shutdown()
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
