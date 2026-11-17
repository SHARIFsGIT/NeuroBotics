"""Debounced MediaPipe hand gestures for optional E-AIRA grasp confirmation.

Author: E-AIRA contributors.
Hardware target: Jetson Orin NX with the ROSMASTER M3 Pro RGB camera.
"""

import json
import math
import time
from typing import Any

import cv2
from cv_bridge import CvBridge, CvBridgeError
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image
from std_msgs.msg import String

from eira_brain.console import error_hint, format_line


def classify_hand(points: list[tuple[float, float]], pinch_ratio: float = 0.3,
                  extension_ratio: float = 1.15) -> str:
    """Classify OK and downward thumb from normalized MediaPipe landmarks.

    Args:
        points: Twenty-one image-coordinate hand landmarks.
        pinch_ratio: Thumb/index fingertip distance relative to palm size.
        extension_ratio: Minimum tip-to-wrist / knuckle-to-wrist ratio.

    Returns:
        OK, Thumb_down, or an empty string for an unrecognized hand.
    """
    if len(points) != 21 or not all(math.isfinite(v) for p in points for v in p):
        return ''

    def distance(first: int, second: int) -> float:
        """Return Euclidean distance between two landmark indices.

        Args:
            first: First landmark index.
            second: Second landmark index.

        Returns:
            Landmark distance in normalized image coordinates.
        """
        return math.dist(points[first], points[second])
    palm = distance(0, 9)
    if palm <= 0:
        return ''
    extended = [distance(tip, 0) > extension_ratio * distance(base, 0)
                for tip, base in ((8, 6), (12, 10), (16, 14), (20, 18))]
    if distance(4, 8) < pinch_ratio * palm and all(extended[1:]):
        return 'OK'
    if not any(extended) and points[4][1] > points[3][1] > points[2][1] and (
            distance(4, 2) > pinch_ratio * palm):
        return 'Thumb_down'
    return ''


class GestureNode(Node):
    """Recognize two explicit gestures without issuing direct actuator commands."""

    def __init__(self) -> None:
        """Create optional camera interfaces and load locally installed MediaPipe."""
        super().__init__('gesture_recognizer')
        defaults = {'color_topic': '/camera/color/image_raw', 'max_fps': 4.0,
                    'stable_frames': 3, 'cooldown_s': 2.0, 'pinch_ratio': 0.3,
                    'extension_ratio': 1.15, 'max_image_age_s': 1.0,
                    'min_detection_confidence': 0.6, 'cancel_on_thumb_down': True}
        for name, value in defaults.items():
            self.declare_parameter(name, value)
        if self._param('max_fps') <= 0 or self._param('stable_frames') < 1:
            raise ValueError('gesture frame rate and debounce count must be positive')
        self._bridge = CvBridge()
        self._hands: Any = None
        self._last_frame = 0.0
        self._last_emit = -float('inf')
        self._candidate = ''
        self._count = 0
        self._identity = {'mission_id': '', 'action_id': ''}
        self._gesture_pub = self.create_publisher(String, '/eira/gesture', 10)
        self._command_pub = self.create_publisher(String, '/eira/command', 10)
        self.create_subscription(String, '/eira/status', self._on_status, 10)
        self.create_subscription(Image, self._param('color_topic'), self._on_image,
                                 qos_profile_sensor_data)
        try:
            import mediapipe as mp
            self._hands = mp.solutions.hands.Hands(
                static_image_mode=False, max_num_hands=1, model_complexity=0,
                min_detection_confidence=self._param('min_detection_confidence'))
        except (ImportError, AttributeError, RuntimeError, OSError) as exc:
            self.get_logger().error(format_line(
                'GESTURE', 'Gesture recognition unavailable: ' + error_hint(exc), 'error'))

    def _param(self, name: str) -> Any:
        """Read one parameter.

        Args:
            name: Parameter name.

        Returns:
            Current value.
        """
        return self.get_parameter(name).value

    def _on_status(self, msg: String) -> None:
        """Attach current mission/action identity to confirmation gestures.

        Args:
            msg: Brain status JSON.
        """
        try:
            status = json.loads(msg.data)
            if isinstance(status, dict):
                self._identity = {key: str(status.get(key, '')) for key in self._identity}
        except (ValueError, TypeError):
            return

    def _on_image(self, msg: Image) -> None:
        """Process a rate-limited frame and publish only stable gesture edges.

        Args:
            msg: Fresh BGR-convertible camera image.
        """
        now = time.monotonic()
        if self._hands is None or now - self._last_frame < 1.0 / self._param('max_fps'):
            return
        self._last_frame = now
        stamp = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
        age = self.get_clock().now().nanoseconds * 1e-9 - stamp
        if stamp <= 0 or age < 0 or age > self._param('max_image_age_s'):
            return
        try:
            frame = self._bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
            result = self._hands.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            gesture = ''
            if result.multi_hand_landmarks:
                points = [(p.x, p.y) for p in result.multi_hand_landmarks[0].landmark]
                gesture = classify_hand(points, self._param('pinch_ratio'),
                                        self._param('extension_ratio'))
            self._count = self._count + 1 if gesture == self._candidate else 1
            self._candidate = gesture
            if gesture and self._count >= self._param('stable_frames') and (
                    now - self._last_emit >= self._param('cooldown_s')):
                self._last_emit = now
                event = {'gesture': gesture, **self._identity, 'wall_time': time.time()}
                self._gesture_pub.publish(String(data=json.dumps(event)))
                description = ('OK recognized; grasp confirmation requested' if gesture == 'OK'
                               else 'Thumb down recognized; cancellation requested')
                self.get_logger().info(format_line('GESTURE', description))
                if gesture == 'Thumb_down' and self._param('cancel_on_thumb_down'):
                    self._command_pub.publish(String(data='stop'))
        except (CvBridgeError, cv2.error, ValueError, TypeError, RuntimeError) as exc:
            self.get_logger().warning(format_line(
                'GESTURE', 'Could not recognize hand gesture: ' + error_hint(exc), 'warning'))

    def destroy_node(self) -> None:
        """Release the optional MediaPipe graph before closing ROS interfaces."""
        if self._hands is not None:
            self._hands.close()
        super().destroy_node()


def main(args: list[str] | None = None) -> None:
    """Run optional gesture recognition.

    Args:
        args: ROS command-line arguments.
    """
    rclpy.init(args=args)
    node = GestureNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
