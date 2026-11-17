"""Adapt course line-following and LiDAR behaviours to bounded E-AIRA skills.

Author: E-AIRA maintainers.
Hardware target: ROSMASTER M3 Pro / Jetson Orin NX, ROS 2 Humble.
Exercises 06/11/12/13 supply behaviour intent; drivers remain external.
Commands never publish to the physical cmd_vel: the central gate arbitrates them.
"""

import json
import math
import time
from typing import Any

import cv2
import numpy as np
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rclpy.time import Time
from geometry_msgs.msg import Twist
from sensor_msgs.msg import Image, LaserScan
from std_msgs.msg import Bool, String, UInt16

from eira_brain.console import error_hint, format_line, sanitize_text


def valid_scan_points(ranges: list[float], angle_min: float, increment: float,
                      minimum: float, maximum: float, front_angle: float = 0.0,
                      include_clear: bool = False) -> list[tuple[float, float]]:
    """Convert valid scan beams to distances and normalized robot-relative bearings.

    Args:
        ranges: LaserScan ranges in metres.
        angle_min: First beam bearing in radians.
        increment: Angular spacing in radians.
        minimum: Sensor's minimum valid range.
        maximum: Sensor's maximum valid range.
        front_angle: Scanner-frame bearing of the robot's forward axis.
        include_clear: Treat positive infinity as clear space to maximum range.

    Returns:
        Valid ``(distance_m, bearing_rad)`` pairs.

    Raises:
        ValueError: Scan geometry or sensor bounds are invalid.
    """
    if (not all(math.isfinite(v) for v in (angle_min, increment, minimum, maximum, front_angle))
            or increment == 0 or minimum < 0 or maximum <= minimum):
        raise ValueError('invalid scan geometry or range bounds')
    points = []
    for index, raw in enumerate(ranges):
        distance = maximum if include_clear and raw == math.inf else raw
        if not math.isfinite(distance) or not minimum <= distance <= maximum or distance <= 0:
            continue
        bearing = angle_min + index * increment - front_angle
        bearing = math.atan2(math.sin(bearing), math.cos(bearing))
        points.append((float(distance), bearing))
    return points


def sector_distance(points: list[tuple[float, float]], center: float,
                    half_angle: float) -> float | None:
    """Return the nearest valid beam in a circular angular sector, or None if uncovered."""
    candidates = [distance for distance, angle in points
                  if abs(math.atan2(math.sin(angle - center), math.cos(angle - center)))
                  <= half_angle]
    return min(candidates) if candidates else None


def track_velocity(distance: float, bearing: float, standoff: float, linear_gain: float,
                   angular_gain: float, max_linear: float, max_angular: float,
                   deadband: float, guard: bool = False) -> tuple[float, float]:
    """Compute clamped target-facing motion without backing into unobserved space.

    Args:
        distance: Target distance in metres.
        bearing: Target bearing in radians.
        standoff: Desired separation in metres.
        linear_gain: Proportional distance gain.
        angular_gain: Proportional bearing gain.
        max_linear: Forward speed cap in metres per second.
        max_angular: Rotation cap in radians per second.
        deadband: Distance deadband in metres.
        guard: When true, face the target without translation.

    Returns:
        Forward and angular velocity.

    Raises:
        ValueError: Any input is nonfinite or a bound is negative.
    """
    values = (distance, bearing, standoff, linear_gain, angular_gain,
              max_linear, max_angular, deadband)
    if not all(math.isfinite(v) for v in values) or min(values[2:]) < 0:
        raise ValueError('tracking gains and bounds must be finite and nonnegative')
    linear = 0.0 if guard or abs(distance - standoff) <= deadband else max(
        0.0, min(max_linear, linear_gain * (distance - standoff)))
    # Reduce forward motion when facing across the target instead of directly toward it.
    linear *= max(0.0, math.cos(bearing))
    return linear, max(-max_angular, min(max_angular, angular_gain * bearing))


def line_error(frame: np.ndarray, lower_hsv: list[int], upper_hsv: list[int],
               roi_start: float, min_pixels: int) -> float | None:
    """Measure normalized line displacement in the lower camera region.

    Args:
        frame: BGR camera pixels.
        lower_hsv: Inclusive HSV lower threshold.
        upper_hsv: Inclusive HSV upper threshold.
        roi_start: Fractional top of the floor-view region.
        min_pixels: Minimum segmented line area.

    Returns:
        Displacement in [-1, 1], positive to image right, or None if absent.

    Raises:
        ValueError: Image or calibrated threshold shape is invalid.
    """
    if (frame.ndim != 3 or frame.shape[2] != 3 or not 0 <= roi_start < 1
            or len(lower_hsv) != 3 or len(upper_hsv) != 3 or min_pixels <= 0):
        raise ValueError('invalid line detector configuration/image')
    limits = (179, 255, 255)
    if any(not 0 <= lo <= hi <= limit for lo, hi, limit in zip(lower_hsv, upper_hsv, limits)):
        raise ValueError('HSV thresholds must be ordered inside the OpenCV range')
    roi = frame[int(frame.shape[0] * roi_start):]
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, np.asarray(lower_hsv, dtype=np.uint8),
                       np.asarray(upper_hsv, dtype=np.uint8))
    moments = cv2.moments(mask, binaryImage=True)
    if moments['m00'] < min_pixels:
        return None
    center = moments['m10'] / moments['m00']
    return float((center - (frame.shape[1] - 1) / 2) / (frame.shape[1] / 2))


class ExerciseSkills(Node):
    """Execute one bounded, correlated course behaviour under the velocity gate."""

    COMMANDS = {'line_follow', 'lidar_avoid', 'lidar_track', 'lidar_guard'}

    def __init__(self) -> None:
        """Configure sensor streams, explicit activation and conservative motion limits."""
        super().__init__('exercise_skills')
        defaults = {
            'scan_topic': '/scan', 'color_topic': '/camera/color/image_raw',
            'control_hz': 10.0, 'sensor_timeout_s': 0.7, 'max_command_s': 60.0,
            'default_command_s': 10.0, 'max_linear': 0.15, 'max_angular': 0.5,
            'obstacle_distance_m': 0.35, 'front_half_angle_rad': 0.35,
            'side_center_rad': 0.9, 'side_half_angle_rad': 0.35,
            'scan_front_angle_rad': 0.0, 'track_half_angle_rad': 0.78,
            'track_standoff_m': 0.55, 'track_linear_gain': 0.5,
            'track_angular_gain': 1.0, 'track_deadband_m': 0.05,
            'line_roi_start': 0.6, 'line_min_pixels': 40, 'line_angular_gain': 0.5,
            'line_hsv_lower': [0, 85, 126], 'line_hsv_upper': [9, 253, 253],
            'line_mirror': False, 'guard_warning_distance_m': 0.55,
            'beep_interval_s': 2.0, 'beep_duration_ms': 100,
            'request_cache_size': 32,
        }
        for name, value in defaults.items():
            self.declare_parameter(name, value)
        for name in ('control_hz', 'sensor_timeout_s', 'max_command_s', 'max_linear',
                     'max_angular', 'obstacle_distance_m'):
            if not math.isfinite(float(self._p(name))) or self._p(name) <= 0:
                raise ValueError(f'{name} must be finite and positive')
        try:
            from cv_bridge import CvBridge
            self._bridge = CvBridge()
        except ImportError:
            self._bridge = None
            self.get_logger().warning(format_line(
                'SKILL', 'Line following unavailable: cv_bridge is not installed', 'warning'))
        self._scan: LaserScan | None = None
        self._scan_received: float | None = None
        self._image_received: float | None = None
        self._line_error: float | None = None
        self._command = ''
        self._mission_id = ''
        self._action_id = ''
        self._deadline = 0.0
        self._completed: dict[tuple[str, str], dict[str, Any]] = {}
        self._manual = False
        self._owner = 'none'
        self._last_beep = 0.0
        self._vel_pub = self.create_publisher(Twist, '/eira/cmd_vel/exercise', 1)
        self._owner_pub = self.create_publisher(String, '/eira/motion_owner', 10)
        self._event_pub = self.create_publisher(String, '/eira/skill/event', 10)
        self._beep_pub = self.create_publisher(UInt16, '/beep', 1)
        self.create_subscription(String, '/eira/skill/request', self._on_request, 10)
        self.create_subscription(String, '/eira/motion_owner', self._on_owner, 10)
        self.create_subscription(Bool, '/JoyState', self._on_manual, 10)
        self.create_subscription(LaserScan, self._p('scan_topic'), self._on_scan,
                                 qos_profile_sensor_data)
        self.create_subscription(Image, self._p('color_topic'), self._on_image,
                                 qos_profile_sensor_data)
        self.create_timer(1.0 / self._p('control_hz'), self._tick)

    def _p(self, name: str) -> Any:
        """Return one declared parameter value."""
        return self.get_parameter(name).value

    def _emit(self, event: str, reason: str = '') -> None:
        """Publish structured progress with the active mission/action identifiers."""
        payload = dict(event=event, command=self._command, reason=reason,
                       mission_id=self._mission_id, action_id=self._action_id,
                       wall_time=time.time())
        message = String()
        message.data = json.dumps(payload)
        self._event_pub.publish(message)
        description = (sanitize_text(self._command).replace('_', ' ').capitalize()
                       + ': ' + sanitize_text(event).replace('_', ' '))
        if reason:
            description += ' — ' + error_hint(reason)
        self.get_logger().info(format_line('SKILL', description))

    def _claim(self, owner: str) -> None:
        """Select this skill's channel or release its ownership after publishing zero."""
        message = String()
        message.data = json.dumps(dict(owner=owner, mission_id=self._mission_id,
                                       action_id=self._action_id))
        self._owner = owner
        self._owner_pub.publish(message)

    def _on_owner(self, msg: String) -> None:
        """Yield promptly if the Brain changes the active command owner."""
        try:
            data = json.loads(msg.data)
        except json.JSONDecodeError:
            return
        if not isinstance(data, dict):
            return
        owner = str(data.get('owner', 'none'))
        ours = (owner == 'exercise' and str(data.get('mission_id', '')) == self._mission_id
                and str(data.get('action_id', '')) == self._action_id)
        if self._command and not ours:
            self._owner = owner
            self._finish('stopped', 'motion ownership changed', release=False)
        else:
            self._owner = owner

    def _on_manual(self, msg: Bool) -> None:
        """Stop autonomous behaviour immediately when joystick control activates."""
        self._manual = bool(msg.data)
        if self._manual and self._command:
            self._finish('stopped', 'manual override')

    def _on_request(self, msg: String) -> None:
        """Activate an explicit bounded skill or stop; reject unknown/unbounded requests."""
        try:
            data = json.loads(msg.data)
            if not isinstance(data, dict):
                raise ValueError('skill request must be a JSON object')
            command = str(data.get('command', '')).lower()
            if command == 'stop':
                self._finish('stopped', 'requested')
                return
            if command not in self.COMMANDS:
                raise ValueError('unknown exercise skill')
            duration = float(data.get('duration_s', self._p('default_command_s')))
            if not math.isfinite(duration) or not 0 < duration <= self._p('max_command_s'):
                raise ValueError('duration_s exceeds bounded execution limits')
            mission, action = str(data.get('mission_id', '')), str(data.get('action_id', ''))
            if not mission or not action:
                raise ValueError('mission_id and action_id are required')
            if (mission, action) in self._completed:
                reply = String()
                reply.data = json.dumps(self._completed[(mission, action)])
                self._event_pub.publish(reply)
                return
            if self._command:
                if (mission, action) == (self._mission_id, self._action_id):
                    return  # A duplicate must not extend the deadline.
                raise ValueError('another exercise skill is active')
            if self._manual or self._owner not in ('none', 'exercise'):
                raise ValueError('motion is owned by another controller or manual override')
            self._mission_id, self._action_id = mission, action
            self._command, self._deadline = command, time.monotonic() + duration
            self._claim('exercise')
            self._emit('started')
        except (json.JSONDecodeError, ValueError, TypeError) as exc:
            self.get_logger().warning(format_line(
                'SKILL', 'Skill request rejected: ' + error_hint(exc), 'warning'))

    def _measurement_fresh(self, msg: Any) -> bool:
        """Check sensor acquisition age using the same ROS clock type as the node."""
        now = self.get_clock().now()
        stamp = Time.from_msg(msg.header.stamp, clock_type=now.clock_type)
        age = (now - stamp).nanoseconds / 1e9
        return 0 <= age <= self._p('sensor_timeout_s')

    def _on_scan(self, msg: LaserScan) -> None:
        """Cache recently acquired scan data; invalid data cannot refresh the watchdog."""
        if self._measurement_fresh(msg):
            self._scan = msg
            self._scan_received = time.monotonic()

    def _on_image(self, msg: Image) -> None:
        """Extract the configured floor-line centroid only while line following is active."""
        if (self._command != 'line_follow' or not self._measurement_fresh(msg)
                or self._bridge is None):
            return
        from cv_bridge import CvBridgeError
        try:
            image = self._bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
            self._line_error = line_error(image, self._p('line_hsv_lower'),
                                          self._p('line_hsv_upper'), self._p('line_roi_start'),
                                          self._p('line_min_pixels'))
            self._image_received = time.monotonic()
        except (CvBridgeError, cv2.error, ValueError, TypeError) as exc:
            self._line_error = None
            self.get_logger().warning(format_line(
                'SKILL', 'Line-following frame rejected: ' + error_hint(exc), 'warning'))

    def _velocity(self, linear: float = 0.0, angular: float = 0.0) -> None:
        """Publish bounded velocity exclusively to the exercise input of the gate."""
        message = Twist()
        message.linear.x = max(0.0, min(self._p('max_linear'), linear))
        message.angular.z = max(-self._p('max_angular'), min(self._p('max_angular'), angular))
        self._vel_pub.publish(message)

    def _finish(self, event: str, reason: str, release: bool = True) -> None:
        """Publish zero before completion and release ownership only when still held."""
        self._velocity()
        if self._command:
            self._emit(event, reason)
            self._completed[(self._mission_id, self._action_id)] = dict(
                event=event, command=self._command, mission_id=self._mission_id,
                action_id=self._action_id, reason=reason, wall_time=time.time())
            while len(self._completed) > max(1, int(self._p('request_cache_size'))):
                self._completed.pop(next(iter(self._completed)))
        self._command = ''
        if release and self._owner == 'exercise':
            self._claim('none')

    def _tick(self) -> None:
        """Compute one bounded control update; abort on stale sensors or sensor errors."""
        if not self._command:
            return
        now = time.monotonic()
        if now >= self._deadline:
            self._finish('done', 'requested duration completed')
            return
        if (self._manual or self._scan_received is None
                or now - self._scan_received > self._p('sensor_timeout_s')):
            self._finish('failed', 'manual override or stale LiDAR')
            return
        try:
            scan = self._scan
            points = valid_scan_points(list(scan.ranges), scan.angle_min, scan.angle_increment,
                                       scan.range_min, scan.range_max,
                                       self._p('scan_front_angle_rad'), include_clear=True)
            front = sector_distance(points, 0.0, self._p('front_half_angle_rad'))
            if front is None:
                raise ValueError('forward LiDAR sector has no valid coverage')
            obstacle = front < self._p('obstacle_distance_m')
            if self._command == 'line_follow':
                if (self._image_received is None
                        or now - self._image_received > self._p('sensor_timeout_s')
                        or self._line_error is None):
                    raise ValueError('floor line lost or camera stale')
                sign = 1.0 if self._p('line_mirror') else -1.0
                self._velocity(0.0 if obstacle else self._p('max_linear'),
                               sign * self._p('line_angular_gain') * self._line_error)
            elif self._command == 'lidar_avoid':
                left = sector_distance(points, self._p('side_center_rad'),
                                       self._p('side_half_angle_rad'))
                right = sector_distance(points, -self._p('side_center_rad'),
                                        self._p('side_half_angle_rad'))
                if obstacle:
                    if left is None or right is None:
                        raise ValueError('avoidance side sectors are uncovered')
                    if max(left, right) < self._p('obstacle_distance_m'):
                        self._velocity()  # Trapped: never drive forward or reverse blindly.
                    else:
                        turn = self._p('max_angular') * (1.0 if left >= right else -1.0)
                        self._velocity(0.0, turn)
                else:
                    self._velocity(self._p('max_linear'))
            else:
                hits = valid_scan_points(list(scan.ranges), scan.angle_min, scan.angle_increment,
                                         scan.range_min, scan.range_max,
                                         self._p('scan_front_angle_rad'))
                targets = [point for point in hits
                           if abs(point[1]) <= self._p('track_half_angle_rad')]
                if not targets:
                    self._velocity()
                    return
                distance, angle = min(targets)
                guard = self._command == 'lidar_guard'
                linear, angular = track_velocity(
                    distance, angle, self._p('track_standoff_m'), self._p('track_linear_gain'),
                    self._p('track_angular_gain'), self._p('max_linear'), self._p('max_angular'),
                    self._p('track_deadband_m'), guard=guard)
                self._velocity(0.0 if obstacle else linear, angular)
                if (guard and distance <= self._p('guard_warning_distance_m')
                        and now - self._last_beep >= self._p('beep_interval_s')):
                    warning = UInt16()
                    warning.data = max(0, min(60000, int(self._p('beep_duration_ms'))))
                    self._beep_pub.publish(warning)
                    self._last_beep = now
        except (ValueError, TypeError, RuntimeError, AttributeError) as exc:
            self._finish('failed', str(exc))

    def destroy_node(self) -> None:
        """Stop the owned exercise channel before releasing ROS resources."""
        try:
            self._finish('stopped', 'shutdown')
        except RuntimeError:
            self.get_logger().warning(format_line(
                'SKILL', 'Exercise stop unavailable during shutdown', 'warning'))
        super().destroy_node()


def main(args: list[str] | None = None) -> None:
    """Run optional course skills until ROS shutdown without direct actuator access."""
    rclpy.init(args=args)
    node = ExerciseSkills()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
