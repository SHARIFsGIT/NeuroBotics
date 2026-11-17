"""AMCL recovery from calibrated ArUco landmarks or external visual poses.

Author: E-AIRA contributors.
Hardware target: ROSMASTER M3 Pro / Jetson Orin NX, ROS 2 Humble.
Course 24 uses AprilTag localization. This adapter accepts that stack's
map-frame pose and optionally derives a pose from calibrated ArUco landmarks.
"""

import json
import math
from pathlib import Path
import time
from typing import Any

import numpy as np
import rclpy
from rclpy.duration import Duration
from rclpy.executors import ExternalShutdownException, MultiThreadedExecutor
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rclpy.time import Time
from geometry_msgs.msg import PoseWithCovarianceStamped
from sensor_msgs.msg import CameraInfo, Image
from std_msgs.msg import String
import tf2_ros
import yaml

from eira_brain.console import error_hint, format_line, sanitize_text


def quaternion_matrix(x: float, y: float, z: float, w: float) -> np.ndarray:
    """Convert a finite nonzero quaternion to a homogeneous rotation.

    Args:
        x: Quaternion x component.
        y: Quaternion y component.
        z: Quaternion z component.
        w: Quaternion w component.

    Returns:
        Four-by-four rigid transformation matrix.

    Raises:
        ValueError: Quaternion is zero or nonfinite.
    """
    q = np.asarray([x, y, z, w], dtype=float)
    norm = float(np.linalg.norm(q))
    if not np.all(np.isfinite(q)) or norm < 1e-8:
        raise ValueError("invalid quaternion")
    x, y, z, w = q / norm
    result = np.eye(4)
    result[:3, :3] = [
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
    ]
    return result


def recovery_needed(covariance: Any, xy_limit: float, yaw_limit: float) -> bool:
    """Determine whether AMCL covariance exceeds configured variance limits.

    Args:
        covariance: Row-major 6x6 pose covariance.
        xy_limit: Maximum acceptable x/y variance in square metres.
        yaw_limit: Maximum acceptable yaw variance in square radians.

    Returns:
        True for invalid or excessive localization uncertainty.
    """
    values = np.asarray(covariance, dtype=float)
    return (values.size != 36 or not np.all(np.isfinite(values))
            or min(values[0], values[7], values[35]) < 0.0
            or max(values[0], values[7]) > xy_limit or values[35] > yaw_limit)


class VisualRelocalization(Node):
    """Gate visual corrections by localization uncertainty and measurement age.

    Args:
        None.
    """

    def __init__(self) -> None:
        """Declare an optional calibrated landmark detector."""
        super().__init__("visual_relocalization")
        defaults = {
            "amcl_topic": "/amcl_pose", "visual_pose_topic": "/eira/visual_pose",
            "color_topic": "/camera/color/image_raw",
            "camera_info_topic": "/camera/color/camera_info",
            "map_frame": "map", "base_frame": "base_link", "marker_map_file": "",
            "aruco_dictionary": "DICT_4X4_50", "marker_size_m": 0.08,
            "xy_variance_limit": 0.5, "yaw_variance_limit": 0.4,
            "visual_xy_variance_max": 0.1, "visual_yaw_variance_max": 0.2,
            "measurement_max_age_s": 1.0, "cooldown_s": 10.0,
            "detection_hz": 2.0, "tf_timeout_s": 0.1,
            "max_correction_m": 5.0, "max_reprojection_error_px": 3.0,
        }
        for key, value in defaults.items():
            self.declare_parameter(key, value)
        self._uncertain = False
        self._amcl = None
        self._info = None
        self._last_correction = -math.inf
        self._last_detection = -math.inf
        self._landmarks: dict[str, Any] = {}
        self._bridge = None
        self._bridge_errors = (ValueError,)
        self._cv2 = None
        self._tf_buffer = tf2_ros.Buffer()
        self._tf_listener = tf2_ros.TransformListener(self._tf_buffer, self, spin_thread=False)
        self._pose_pub = self.create_publisher(PoseWithCovarianceStamped, "/initialpose", 10)
        self._event_pub = self.create_publisher(String, "/eira/localization/event", 10)
        self.create_subscription(PoseWithCovarianceStamped,
                                 self.get_parameter("amcl_topic").value, self._on_amcl, 10)
        self.create_subscription(PoseWithCovarianceStamped,
                                 self.get_parameter("visual_pose_topic").value,
                                 self._on_visual_pose, 10)
        marker_file = self.get_parameter("marker_map_file").value
        if marker_file:
            try:
                data = yaml.safe_load(Path(marker_file).expanduser().read_text())
                if not isinstance(data, dict) or not isinstance(data.get("markers"), dict):
                    raise ValueError("marker map requires a markers mapping")
                if data.get("frame", "map") != self.get_parameter("map_frame").value:
                    raise ValueError("marker map frame mismatch")
                self._landmarks = data["markers"]
                import cv2
                from cv_bridge import CvBridge, CvBridgeError
                self._bridge_errors = (CvBridgeError,)
                if not hasattr(cv2, "aruco"):
                    raise ImportError("OpenCV aruco module unavailable")
                self._cv2, self._bridge = cv2, CvBridge()
            except (OSError, ValueError, yaml.YAMLError, ImportError) as exc:
                self._emit("aruco_unavailable", reason=str(exc))
                self._landmarks = {}
        if self._landmarks:
            self.create_subscription(CameraInfo, self.get_parameter("camera_info_topic").value,
                                     self._on_info, qos_profile_sensor_data)
            self.create_subscription(Image, self.get_parameter("color_topic").value,
                                     self._on_image, qos_profile_sensor_data)

    def _emit(self, event: str, **fields: Any) -> None:
        """Publish structured recovery diagnostics.

        Args:
            event: Recovery lifecycle event.
            **fields: Additional diagnostics.
        """
        payload = json.dumps({"event": event, "mission_id": None, "action_id": None,
                              "wall_time": time.time(), **fields})
        self._event_pub.publish(String(data=payload))
        descriptions = {
            'aruco_unavailable': 'Visual localization unavailable',
            'correction_rejected': 'Visual localization correction rejected',
            'relocalized': 'Localization corrected from a visual landmark',
            'visual_measurement_failed': 'Visual pose measurement failed',
        }
        description = descriptions.get(event, sanitize_text(event).replace('_', ' ').capitalize())
        if fields.get('reason'):
            description += ': ' + error_hint(fields['reason'])
        self.get_logger().info(format_line(
            'LOCALIZATION', description, 'success' if event == 'relocalized' else 'warning'))

    def _on_amcl(self, msg: PoseWithCovarianceStamped) -> None:
        """Monitor AMCL uncertainty without modifying healthy localization.

        Args:
            msg: AMCL pose/covariance.
        """
        self._amcl = msg
        self._uncertain = recovery_needed(
            msg.pose.covariance, float(self.get_parameter("xy_variance_limit").value),
            float(self.get_parameter("yaw_variance_limit").value))

    def _on_info(self, msg: CameraInfo) -> None:
        """Cache the live calibrated camera model.

        Args:
            msg: Color camera calibration.
        """
        self._info = msg

    def _on_visual_pose(self, msg: PoseWithCovarianceStamped) -> None:
        """Accept only recent, confident map-frame corrections while lost.

        Args:
            msg: Calibrated visual estimate of base pose in map frame.
        """
        now = time.monotonic()
        if not self._uncertain or now - self._last_correction < float(
                self.get_parameter("cooldown_s").value):
            return
        if msg.header.frame_id != self.get_parameter("map_frame").value:
            return
        age = (self.get_clock().now() - Time.from_msg(msg.header.stamp)).nanoseconds / 1e9
        if age < 0.0 or age > float(self.get_parameter("measurement_max_age_s").value):
            return
        covariance = msg.pose.covariance
        if recovery_needed(covariance, float(self.get_parameter("visual_xy_variance_max").value),
                           float(self.get_parameter("visual_yaw_variance_max").value)):
            return
        position, orientation = msg.pose.pose.position, msg.pose.pose.orientation
        if not all(math.isfinite(v) for v in (position.x, position.y, position.z)):
            return
        try:
            quaternion_matrix(orientation.x, orientation.y, orientation.z, orientation.w)
        except ValueError:
            return
        if self._amcl is not None:
            previous = self._amcl.pose.pose.position
            jump = math.hypot(position.x - previous.x, position.y - previous.y)
            if jump > float(self.get_parameter("max_correction_m").value):
                self._emit("correction_rejected", reason="translation exceeds limit")
                return
        self._pose_pub.publish(msg)
        self._last_correction = now
        self._uncertain = False
        self._emit("relocalized", x=position.x, y=position.y)

    def _on_image(self, msg: Image) -> None:
        """Estimate a map-to-base correction from a known ArUco landmark.

        Args:
            msg: Color image with its measurement timestamp.
        """
        now = time.monotonic()
        period = 1.0 / max(0.1, float(self.get_parameter("detection_hz").value))
        if not self._uncertain or self._info is None or now - self._last_detection < period:
            return
        self._last_detection = now
        cv2 = self._cv2
        try:
            frame = self._bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
            dictionary = cv2.aruco.getPredefinedDictionary(getattr(
                cv2.aruco, self.get_parameter("aruco_dictionary").value))
            corners, ids, _ = cv2.aruco.detectMarkers(frame, dictionary)
            if ids is None:
                return
            camera = np.asarray(self._info.k).reshape(3, 3)
            distortion = np.asarray(self._info.d)
            for corner, identity in zip(corners, ids.flatten()):
                landmark = self._landmarks.get(str(int(identity)),
                                               self._landmarks.get(int(identity)))
                if not isinstance(landmark, dict):
                    continue
                size = float(landmark.get("size_m", self.get_parameter("marker_size_m").value))
                if not math.isfinite(size) or size <= 0.0:
                    continue
                half = size / 2.0
                object_points = np.array([[-half, half, 0], [half, half, 0],
                                          [half, -half, 0], [-half, -half, 0]], dtype=float)
                ok, rvec, tvec = cv2.solvePnP(
                    object_points, corner.reshape(4, 2), camera, distortion,
                    flags=cv2.SOLVEPNP_IPPE_SQUARE)
                if not ok or float(tvec[2, 0]) <= 0.0:
                    continue
                projected, _ = cv2.projectPoints(object_points, rvec, tvec, camera, distortion)
                error = float(np.sqrt(np.mean((projected.reshape(4, 2)
                                               - corner.reshape(4, 2)) ** 2)))
                if error > float(self.get_parameter("max_reprojection_error_px").value):
                    continue
                camera_marker = np.eye(4)
                camera_marker[:3, :3] = cv2.Rodrigues(rvec)[0]
                camera_marker[:3, 3] = tvec.flatten()
                q = landmark.get("quaternion", [0.0, 0.0, 0.0, 1.0])
                map_marker = quaternion_matrix(*q)
                map_marker[:3, 3] = [float(landmark[key]) for key in ("x", "y", "z")]
                transform = self._tf_buffer.lookup_transform(
                    self.get_parameter("base_frame").value,
                    self._info.header.frame_id or msg.header.frame_id,
                    Time.from_msg(msg.header.stamp), timeout=Duration(
                        seconds=float(self.get_parameter("tf_timeout_s").value)))
                t, rotation = transform.transform.translation, transform.transform.rotation
                base_camera = quaternion_matrix(rotation.x, rotation.y, rotation.z, rotation.w)
                base_camera[:3, 3] = [t.x, t.y, t.z]
                map_base = map_marker @ np.linalg.inv(camera_marker) @ np.linalg.inv(base_camera)
                yaw = math.atan2(map_base[1, 0], map_base[0, 0])
                pose = PoseWithCovarianceStamped()
                pose.header.frame_id = self.get_parameter("map_frame").value
                pose.header.stamp = msg.header.stamp
                pose.pose.pose.position.x = float(map_base[0, 3])
                pose.pose.pose.position.y = float(map_base[1, 3])
                pose.pose.pose.orientation.z = math.sin(yaw / 2.0)
                pose.pose.pose.orientation.w = math.cos(yaw / 2.0)
                pose.pose.covariance[0] = pose.pose.covariance[7] = 0.05
                pose.pose.covariance[35] = 0.1
                self._on_visual_pose(pose)
                return
        except (ValueError, TypeError, KeyError, AttributeError, cv2.error,
                tf2_ros.TransformException, np.linalg.LinAlgError, *self._bridge_errors) as exc:
            self._emit("visual_measurement_failed", reason=str(exc))


def main(args: list[str] | None = None) -> None:
    """Run the optional visual recovery adapter.

    Args:
        args: Optional ROS arguments.
    """
    rclpy.init(args=args)
    node = VisualRelocalization()
    executor = MultiThreadedExecutor(num_threads=2)
    executor.add_node(node)
    try:
        executor.spin()
    except (ExternalShutdownException, KeyboardInterrupt):
        pass
    finally:
        executor.shutdown()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
