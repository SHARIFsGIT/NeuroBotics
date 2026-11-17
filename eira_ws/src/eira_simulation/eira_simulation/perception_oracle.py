"""Explicit ground-truth perception mode for control regression, not vision scoring.

Author: E-AIRA maintainers.
Hardware target: M3 Pro Gazebo Classic / ROS 2 Humble only.
This optional oracle never runs on hardware and never claims measured perception
latency or object-contact success. Learned perception remains the launch default.
"""

import json
import math
import time

import rclpy
from gazebo_msgs.msg import ModelStates
from geometry_msgs.msg import PoseStamped
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from std_msgs.msg import String

from eira_perception.perception_core import split_target, target_request


class PerceptionOracle(Node):
    """Publish the known simulated cup pose with the ordinary request/event schema."""

    def __init__(self) -> None:
        """Subscribe to simulated ground truth and explicit find requests."""
        super().__init__('sim_perception_oracle')
        defaults = {'robot_name': 'eira_m3pro', 'cup_name': 'cup', 'max_range_m': 3.0,
                    'half_fov_rad': 0.65, 'publish_hz': 10.0, 'stale_after_s': 1.0}
        for name, value in defaults.items():
            self.declare_parameter(name, value)
        self._request = {'mission_id': '', 'action_id': '', 'target': 'cup'}
        self._announced = False
        self._models: ModelStates | None = None
        self._seen = 0.0
        self._pose = self.create_publisher(PoseStamped, '/target_pose', 10)
        self._events = self.create_publisher(String, '/eira/vision/event', 10)
        self.create_subscription(ModelStates, '/gazebo/model_states', self._on_models, 10)
        self.create_subscription(String, '/eira/vision_target', self._on_request, 10)
        self.create_timer(1.0 / float(self.get_parameter('publish_hz').value), self._tick)
        self.get_logger().warning('GROUND-TRUTH ORACLE: exclude this mode from vision evaluation')

    def _on_models(self, message: ModelStates) -> None:
        """Cache Gazebo model-state evidence, with a monotonic receipt deadline.

        Args:
            message: Actual world model poses.
        """
        self._models, self._seen = message, time.monotonic()

    def _on_request(self, message: String) -> None:
        """Associate simulated target evidence with the current find attempt.

        Args:
            message: Correlated target envelope or legacy label.
        """
        try:
            request = target_request(message.data)
            if request != self._request:
                self._request, self._announced = request, False
        except (ValueError, TypeError) as exc:
            self.get_logger().warning(f'oracle target rejected: {exc}')

    def _emit(self, event: str, **fields: object) -> None:
        """Publish clearly labeled oracle evidence.

        Args:
            event: Lifecycle event.
            **fields: Additional measurement metadata.
        """
        self._events.publish(String(data=json.dumps({
            **self._request, 'event': event, 'source': 'simulation_ground_truth',
            'wall_time': time.time(), **fields})))

    def _tick(self) -> None:
        """Transform the known cup point into the robot's planar base coordinates."""
        if self._models is None or time.monotonic() - self._seen > self.get_parameter(
                'stale_after_s').value:
            if self._announced:
                self._emit('lost', reason='simulated_ground_truth_stale')
                self._announced = False
            return
        label, color = split_target(self._request['target'])
        if label != 'cup' or color not in ('', 'red'):
            return
        names = self._models.name
        robot_name, cup_name = (self.get_parameter(key).value
                                for key in ('robot_name', 'cup_name'))
        if robot_name not in names or cup_name not in names:
            return
        robot, cup = (self._models.pose[names.index(name)] for name in (robot_name, cup_name))
        q = robot.orientation
        yaw = math.atan2(2*(q.w*q.z+q.x*q.y), 1-2*(q.y*q.y+q.z*q.z))
        dx, dy = cup.position.x-robot.position.x, cup.position.y-robot.position.y
        x, y = math.cos(yaw)*dx+math.sin(yaw)*dy, -math.sin(yaw)*dx+math.cos(yaw)*dy
        if (math.hypot(x, y) > self.get_parameter('max_range_m').value
                or abs(math.atan2(y, x)) > self.get_parameter('half_fov_rad').value):
            if self._announced:
                self._emit('lost', reason='outside_oracle_view_window')
                self._announced = False
            return
        pose = PoseStamped()
        pose.header.frame_id = 'base_link'
        pose.header.stamp = self.get_clock().now().to_msg()
        pose.pose.position.x, pose.pose.position.y = x, y
        pose.pose.position.z = cup.position.z-robot.position.z
        pose.pose.orientation.w = 1.0
        self._pose.publish(pose)
        if not self._announced:
            self._emit('found', label='cup', color='red', width_m=0.06, height_m=0.12,
                       volume_m3=math.pi*0.03**2*0.12,
                       measurement_stamp_ns=self.get_clock().now().nanoseconds,
                       confidence=1.0, track_id=1, ground_truth=True)
            self._announced = True


def main(args: list[str] | None = None) -> None:
    """Run an explicitly selected simulation-only oracle.

    Args:
        args: Optional ROS arguments.
    """
    rclpy.init(args=args)
    node = PerceptionOracle()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
