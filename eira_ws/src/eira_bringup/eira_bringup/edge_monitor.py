"""Detect drop-offs from calibrated, timestamped RGB-D ground samples.

Author: E-AIRA maintainers.
Hardware target: Dabai DCW2 / ROSMASTER M3 Pro / Jetson Orin NX, ROS 2 Humble.
"""

import json
import time
from typing import Any

import numpy as np
import rclpy
from rclpy.duration import Duration
from rclpy.executors import ExternalShutdownException, MultiThreadedExecutor
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rclpy.time import Time
from sensor_msgs.msg import CameraInfo, Image
from std_msgs.msg import String
import tf2_ros

from eira_bringup.edge_geometry import floor_observation, transform_points
from eira_brain.console import error_hint, format_line


class EdgeMonitor(Node):
    """Publish a continuously refreshed floor safety state without moving the arm."""

    def __init__(self) -> None:
        """Declare calibrated geometry and subscribe to depth and intrinsics.

        Raises:
            ImportError: If cv_bridge is absent on the deployment.
            ValueError: If the processing rate is invalid.
        """
        super().__init__('edge_monitor')
        from cv_bridge import CvBridge, CvBridgeError
        self._bridge = CvBridge()
        self._bridge_error = CvBridgeError
        defaults = {
            'depth_topic': '/camera/depth/image_raw',
            'camera_info_topic': '/camera/color/camera_info',
            'target_frame': 'base_link', 'floor_z_m': 0.0, 'drop_threshold_m': 0.08,
            'minimum_points': 30, 'drop_fraction': 0.15, 'corridor_near_m': 0.15,
            'corridor_far_m': 0.8, 'corridor_half_width_m': 0.25,
            'sample_stride': 12, 'roi_top_fraction': 0.4, 'max_depth_m': 4.0,
            'frame_timeout_s': 1.0, 'tf_timeout_s': 0.1, 'processing_hz': 5.0,
            'camera_info_max_age_s': 60.0, 'depth_registered': True,
        }
        for name, value in defaults.items():
            self.declare_parameter(name, value)
        rate = float(self.get_parameter('processing_hz').value)
        if rate <= 0:
            raise ValueError('processing_hz must be positive')
        self._interval = 1.0 / rate
        self._last_processed = 0.0
        self._last_frame: float | None = None
        self._info: CameraInfo | None = None
        self._info_time: float | None = None
        self._context: dict = {'mission_id': None, 'action_id': None}
        self._tf = tf2_ros.Buffer()
        self._listener = tf2_ros.TransformListener(self._tf, self, spin_thread=False)
        self._pub = self.create_publisher(String, '/eira/safety/edge', 10)
        self.create_subscription(Image, self._param('depth_topic'), self._depth,
                                 qos_profile_sensor_data)
        self.create_subscription(CameraInfo, self._param('camera_info_topic'), self._camera,
                                 qos_profile_sensor_data)
        self.create_subscription(String, '/eira/motion_owner', self._owner, 10)
        self.create_timer(self._interval, self._watchdog)

    def _param(self, name: str) -> Any:
        """Return a declared parameter's current value.

        Args:
            name: Parameter identifier.
        Returns:
            Parameter value.
        """
        return self.get_parameter(name).value

    def _owner(self, message: String) -> None:
        """Cache mission IDs to correlate safety observations."""
        try:
            data = json.loads(message.data)
            if isinstance(data, dict):
                self._context = {k: data.get(k) for k in ('mission_id', 'action_id')}
        except (ValueError, TypeError):
            self.get_logger().warning(format_line(
                'EDGE', 'Ignored invalid motion ownership context', 'warning'))

    def _camera(self, message: CameraInfo) -> None:
        """Cache intrinsics for a registered depth image."""
        self._info = message
        self._info_time = time.monotonic()

    def _publish(self, observation: dict) -> None:
        """Publish an observation envelope and its mission context."""
        message = String()
        message.data = json.dumps({**observation, **self._context, 'wall_time': time.time()})
        self._pub.publish(message)

    def _watchdog(self) -> None:
        """Block on missing or frozen camera data independently of frame callbacks."""
        if self._last_frame is None or time.monotonic() - self._last_frame > self._param(
                'frame_timeout_s'):
            self._publish({'blocked': True, 'reason': 'depth_stream_stale'})

    def _depth(self, message: Image) -> None:
        """Deproject and transform current depth samples, blocking on any failure."""
        now = time.monotonic()
        if now - self._last_processed < self._interval:
            return
        self._last_processed = now
        try:
            age = (self.get_clock().now() - Time.from_msg(message.header.stamp)).nanoseconds
            if Time.from_msg(message.header.stamp).nanoseconds == 0 or (
                    age < -100_000_000 or age > self._param('frame_timeout_s') * 1e9):
                raise ValueError('depth measurement timestamp is stale')
            if not self._param('depth_registered'):
                raise ValueError('depth registration must be enabled')
            if self._info_time is None or now - self._info_time > self._param(
                    'camera_info_max_age_s'):
                raise ValueError('camera calibration is stale')
            if self._info is None or not np.isfinite(self._info.k).all() or (
                    min(self._info.k[0], self._info.k[4]) <= 0):
                raise ValueError('registered depth intrinsics unavailable')
            depth = np.asarray(self._bridge.imgmsg_to_cv2(message, 'passthrough'))
            if depth.dtype == np.uint16:
                depth = depth.astype(float) / 1000.0
            elif depth.dtype not in (np.float32, np.float64):
                raise ValueError('unsupported depth encoding')
            if depth.shape != (self._info.height, self._info.width):
                raise ValueError('registered depth dimensions differ from intrinsics')
            stride = max(1, int(self._param('sample_stride')))
            top = int(depth.shape[0] * float(self._param('roi_top_fraction')))
            v, u = np.mgrid[top:depth.shape[0]:stride, 0:depth.shape[1]:stride]
            z = depth[v, u]
            k = self._info.k
            points = np.column_stack((((u-k[2])*z/k[0]).ravel(),
                                      ((v-k[5])*z/k[4]).ravel(), z.ravel()))
            valid = np.isfinite(points).all(axis=1) & (points[:, 2] > 0)
            valid &= points[:, 2] <= self._param('max_depth_m')
            # Registered depth is deprojected in the color optical frame.
            source_frame = self._info.header.frame_id
            if not source_frame:
                raise ValueError('camera optical frame unavailable')
            tf = self._tf.lookup_transform(
                self._param('target_frame'), source_frame,
                Time.from_msg(message.header.stamp),
                timeout=Duration(seconds=float(self._param('tf_timeout_s'))))
            t, q = tf.transform.translation, tf.transform.rotation
            points = transform_points(points[valid], (t.x, t.y, t.z), (q.x, q.y, q.z, q.w))
            result = floor_observation(
                points, self._param('floor_z_m'), self._param('drop_threshold_m'),
                self._param('minimum_points'), self._param('drop_fraction'),
                self._param('corridor_near_m'), self._param('corridor_far_m'),
                self._param('corridor_half_width_m'))
            self._last_frame = now
            self._publish(result)
        except (self._bridge_error, ValueError, TypeError, IndexError,
                tf2_ros.TransformException) as exc:
            self._publish({'blocked': True, 'reason': str(exc)})
            self.get_logger().warning(format_line(
                'EDGE', 'Floor-edge protection unavailable: ' + error_hint(exc), 'warning'),
                throttle_duration_sec=5.0)


def main(args: list[str] | None = None) -> None:
    """Run the floor monitor until shutdown."""
    rclpy.init(args=args)
    node = EdgeMonitor()
    executor = MultiThreadedExecutor(num_threads=2)
    executor.add_node(node)
    try:
        executor.spin()
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        executor.shutdown()
        node._listener.unregister()
        node.destroy_node()
        rclpy.try_shutdown()
