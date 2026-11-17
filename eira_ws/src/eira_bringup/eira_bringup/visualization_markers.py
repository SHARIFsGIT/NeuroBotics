"""Display observed mission goals, object poses and robot heading in RViz.

Author: E-AIRA maintainers.
Hardware target: ROSMASTER M3 Pro / Jetson Orin NX, ROS 2 Humble / Python 3.10.
Markers never command motion. Object and heading poses retain their measurement
frames and stamps; RViz resolves the existing TF tree independently.
"""

from collections import OrderedDict
from copy import deepcopy
import json
import math
from pathlib import Path
import time
from typing import Any

from ament_index_python.packages import PackageNotFoundError, get_package_share_directory
from geometry_msgs.msg import PoseStamped, PoseWithCovarianceStamped
import rclpy
from rclpy.duration import Duration
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from std_msgs.msg import String
from visualization_msgs.msg import Marker, MarkerArray

from eira_brain.console import format_line, sanitize_text
from eira_brain.waypoint_store import load_waypoints


class VisualizationMarkers(Node):
    """Render bounded observations without assuming cross-topic delivery order."""

    MISSION_MARKERS = (('eira/waypoint', 0), ('eira/waypoint', 1),
                       ('eira/object', 0), ('eira/object', 1))
    TERMINAL_STATES = {'DONE', 'FAILED', 'CANCELLED'}
    CACHE_LIMIT = 64

    def __init__(self) -> None:
        """Declare display parameters and connect observational subscriptions.

        Raises:
            ValueError: A marker size, lifetime or update rate is invalid.
        """
        super().__init__('visualization_markers')
        defaults = {
            'waypoints_file': '', 'marker_lifetime_s': 5.0, 'refresh_hz': 2.0,
            'pose_stale_s': 5.0, 'heading_stale_s': 15.0, 'future_tolerance_s': 0.1,
            'waypoint_diameter_m': 0.18, 'object_diameter_m': 0.10,
            'heading_length_m': 0.45, 'heading_width_m': 0.04,
            'label_height_m': 0.15, 'label_scale_m': 0.10,
        }
        for name, value in defaults.items():
            self.declare_parameter(name, value)
            if name != 'waypoints_file' and (
                    not math.isfinite(float(self._param(name))) or self._param(name) <= 0):
                raise ValueError(f'{name} must be positive and finite')
        self._mission_id = ''
        self._status: dict[str, Any] = {}
        self._plans: OrderedDict[str, list[dict[str, Any]]] = OrderedDict()
        self._finished: OrderedDict[str, None] = OrderedDict()
        self._found: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self._poses: OrderedDict[int, tuple[PoseStamped, float]] = OrderedDict()
        self._object_event: dict[str, Any] | None = None
        self._object_pose: PoseStamped | None = None
        self._object_received_at: float | None = None
        self._heading: PoseStamped | None = None
        self._heading_received_at: float | None = None
        self._waypoints: dict[str, dict[str, float]] = {}
        self._map_frame = 'map'
        self._shown: set[tuple[str, int]] = set()
        self._pub = self.create_publisher(MarkerArray, '/eira/visualization_markers', 10)
        for topic, callback in (
                ('/eira/status', self._on_status), ('/eira/plan', self._on_plan),
                ('/eira/vision/event', self._on_vision_event)):
            self.create_subscription(String, topic, callback, 10)
        self.create_subscription(PoseStamped, '/target_pose', self._on_target_pose, 10)
        self.create_subscription(PoseWithCovarianceStamped, '/amcl_pose', self._on_amcl_pose, 10)
        self._load_waypoints()
        self.create_timer(1.0 / self._param('refresh_hz'), self._refresh)
        self.get_logger().info(format_line('RVIZ', 'Mission markers ready'))

    def _param(self, name: str) -> Any:
        """Return a display parameter.

        Args:
            name: Declared parameter name.

        Returns:
            Current parameter value.
        """
        return self.get_parameter(name).value

    @staticmethod
    def _decode(message: String) -> dict[str, Any] | None:
        """Ignore malformed telemetry without affecting robot operation.

        Args:
            message: JSON String from an existing E-AIRA topic.

        Returns:
            Object payload, or None for invalid/nonobject JSON.
        """
        try:
            data = json.loads(message.data)
        except (ValueError, TypeError, RecursionError):
            return None
        return data if isinstance(data, dict) else None

    @classmethod
    def _remember(cls, cache: OrderedDict, key: Any, value: Any) -> None:
        """Store recent evidence with a fixed memory bound.

        Args:
            cache: Ordered evidence cache.
            key: Correlation or timestamp key.
            value: Validated observation.
        """
        cache[key] = value
        cache.move_to_end(key)
        while len(cache) > cls.CACHE_LIMIT:
            cache.popitem(last=False)

    @staticmethod
    def _identity(data: dict[str, Any]) -> str:
        """Read a real mission identity without inventing one for legacy messages.

        Args:
            data: Decoded telemetry object.

        Returns:
            Nonempty mission string, or empty when unavailable.
        """
        identity = data.get('mission_id')
        return identity.strip() if isinstance(identity, str) else ''

    def _load_waypoints(self) -> None:
        """Reload grounded waypoint coordinates when a mission starts."""
        configured = self._param('waypoints_file')
        if configured:
            path = Path(configured).expanduser()
        else:
            try:
                path = Path(get_package_share_directory('eira_bringup')) / 'config/waypoints.yaml'
            except PackageNotFoundError:
                path = Path(__file__).resolve().parents[1] / 'config/waypoints.yaml'
        try:
            data = load_waypoints(path)
            self._map_frame, self._waypoints = data['frame'], data['waypoints']
        except (OSError, ValueError) as exc:
            self._waypoints = {}
            warning = format_line('RVIZ', f'Waypoint markers unavailable: {exc}', 'warning')
            self.get_logger().warning(warning)

    def _on_plan(self, message: String) -> None:
        """Cache plans arriving before or after their first status message.

        Args:
            message: Existing plan JSON with mission identity and actions.
        """
        data = self._decode(message)
        if data is None:
            return
        identity, actions = self._identity(data), data.get('actions')
        if not identity or identity in self._finished or not isinstance(actions, list):
            return
        if not all(isinstance(action, dict) for action in actions):
            return
        self._remember(self._plans, identity, actions)

    def _on_status(self, message: String) -> None:
        """Select the observed active mission and remove completed mission markers.

        Args:
            message: Existing Brain status JSON.
        """
        data = self._decode(message)
        if data is None:
            return
        identity = self._identity(data)
        detail = str(data.get('detail', ''))
        if not identity or detail == 'queued' or detail.startswith('rejected'):
            return
        state = data.get('state')
        if not isinstance(state, str):
            return
        if state in self.TERMINAL_STATES:
            self._remember(self._finished, identity, None)
            self._plans.pop(identity, None)
            self._found.pop(identity, None)
            if identity == self._mission_id:
                self._delete(self.MISSION_MARKERS)
                self._mission_id, self._status = '', {}
                self._object_event = self._object_pose = self._object_received_at = None
            return
        if identity in self._finished:
            return
        if identity != self._mission_id:
            self._delete(self.MISSION_MARKERS)
            if self._mission_id:
                self._remember(self._finished, self._mission_id, None)
                self._plans.pop(self._mission_id, None)
                self._found.pop(self._mission_id, None)
            self._mission_id = identity
            self._object_pose = self._object_received_at = None
            self._object_event = self._found.get(identity)
            self._load_waypoints()
            self._match_object_pose()
        self._status = data

    def _on_vision_event(self, message: String) -> None:
        """Join found metadata to a real pose and delete explicitly lost objects.

        Args:
            message: Existing correlated vision event JSON.
        """
        data = self._decode(message)
        if data is None:
            return
        identity = self._identity(data)
        if not identity or identity in self._finished:
            return
        if data.get('event') == 'found':
            stamp = data.get('measurement_stamp_ns')
            if isinstance(stamp, bool) or not isinstance(stamp, int) or stamp <= 0:
                return
            previous = self._found.get(identity)
            if previous and stamp < previous['measurement_stamp_ns']:
                return
            self._remember(self._found, identity, data)
            if identity == self._mission_id:
                self._object_event = data
                self._object_pose = self._object_received_at = None
                self._match_object_pose()
        elif data.get('event') in ('lost', 'timeout', 'failed') and identity == self._mission_id:
            if self._object_event and data.get('action_id') == self._object_event.get('action_id'):
                self._object_event = self._object_pose = self._object_received_at = None
                self._found.pop(identity, None)
                self._delete((('eira/object', 0), ('eira/object', 1)))

    def _valid_pose(self, message: PoseStamped, maximum_age_s: float | None = None) -> bool:
        """Reject nonfinite, unstamped or stale sensor geometry.

        Args:
            message: Actual sensor/AMCL pose; no timestamp is synthesized.
            maximum_age_s: Measurement age limit; heading limit when omitted.

        Returns:
            Whether its position, frame and measurement time are usable.
        """
        point = message.pose.position
        stamp_ns = message.header.stamp.sec * 1_000_000_000 + message.header.stamp.nanosec
        age = (self.get_clock().now().nanoseconds - stamp_ns) * 1e-9
        maximum_age_s = (self._param('heading_stale_s') if maximum_age_s is None
                         else maximum_age_s)
        return bool(message.header.frame_id.strip() and stamp_ns > 0
                    and all(math.isfinite(value) for value in (point.x, point.y, point.z))
                    and -self._param('future_tolerance_s') <= age
                    <= maximum_age_s)

    def _on_target_pose(self, message: PoseStamped) -> None:
        """Cache real target measurements and preserve their original coordinate frame.

        Args:
            message: Pose from the existing `/target_pose` topic.
        """
        if not self._valid_pose(message, self._param('pose_stale_s')):
            return
        stamp = message.header.stamp.sec * 1_000_000_000 + message.header.stamp.nanosec
        received = time.monotonic()
        self._remember(self._poses, stamp, (deepcopy(message), received))
        if self._object_event:
            original = self._object_event['measurement_stamp_ns']
            current = (self._object_pose.header.stamp.sec * 1_000_000_000
                       + self._object_pose.header.stamp.nanosec) if self._object_pose else original
            if ((self._object_pose is None and stamp == original)
                    or (self._object_pose is not None and stamp >= current)):
                self._object_pose, self._object_received_at = deepcopy(message), received

    def _match_object_pose(self) -> None:
        """Match cross-topic telemetry by its exact captured measurement timestamp."""
        if self._object_event is not None:
            cached = self._poses.get(self._object_event['measurement_stamp_ns'])
            if cached is not None:
                self._object_pose, self._object_received_at = cached

    def _on_amcl_pose(self, message: PoseWithCovarianceStamped) -> None:
        """Cache an observed heading arrow only when its quaternion is valid.

        Args:
            message: Current AMCL pose in its actual global frame.
        """
        pose = PoseStamped(header=deepcopy(message.header), pose=deepcopy(message.pose.pose))
        quaternion = pose.pose.orientation
        values = (quaternion.x, quaternion.y, quaternion.z, quaternion.w)
        norm = math.sqrt(sum(value * value for value in values))
        if not self._valid_pose(pose) or not math.isfinite(norm) or norm <= 0:
            return
        quaternion.x, quaternion.y, quaternion.z, quaternion.w = (value / norm for value in values)
        self._heading, self._heading_received_at = pose, time.monotonic()

    def _marker(self, namespace: str, identity: int, kind: int,
                pose: PoseStamped, color: tuple[float, float, float]) -> Marker:
        """Construct a visible marker at a real or grounded pose.

        Args:
            namespace: Stable marker namespace.
            identity: Stable ID within the namespace.
            kind: RViz Marker type constant.
            pose: Stamped coordinate geometry.
            color: RGB display color; alpha is always visible.

        Returns:
            Marker with a finite lifetime and original frame/stamp.
        """
        marker = Marker()
        marker.header, marker.pose = deepcopy(pose.header), deepcopy(pose.pose)
        marker.ns, marker.id, marker.type, marker.action = namespace, identity, kind, Marker.ADD
        marker.color.r, marker.color.g, marker.color.b = color
        marker.color.a = 0.95
        marker.lifetime = Duration(seconds=float(self._param('marker_lifetime_s'))).to_msg()
        return marker

    def _delete(self, identities: tuple | list | set) -> None:
        """Delete previously visible markers without affecting any other RViz publisher.

        Args:
            identities: Namespace/ID pairs to remove.
        """
        messages = []
        for namespace, identity in identities:
            if (namespace, identity) not in self._shown:
                continue
            marker = Marker()
            marker.ns, marker.id, marker.action = namespace, identity, Marker.DELETE
            messages.append(marker)
            self._shown.discard((namespace, identity))
        if messages:
            self._pub.publish(MarkerArray(markers=messages))

    def _current_waypoint(self) -> tuple[str, dict[str, float]] | None:
        """Resolve the active navigation target from status and its matching plan.

        Returns:
            Grounded name/coordinates, or None outside navigation.
        """
        action = self._status.get('action')
        target = self._status.get('target')
        plan = self._plans.get(self._mission_id, [])
        step = self._status.get('step')
        if isinstance(step, int) and not isinstance(step, bool) and 0 <= step < len(plan):
            selected = plan[step]
            action = selected.get('action') if action is None else action
            target = selected.get('target') if not target else target
        if action != 'navigate' or not isinstance(target, str):
            return None
        pose = self._waypoints.get(target.lower())
        return (target, pose) if pose is not None else None

    def _sphere_label(self, namespace: str, pose: PoseStamped, label: str,
                      color: tuple[float, float, float], diameter: float) -> list[Marker]:
        """Build a sphere/text pair without changing the supplied measurement pose.

        Args:
            namespace: Target or waypoint namespace.
            pose: Actual stamped position.
            label: Human-readable text.
            color: Display RGB color.
            diameter: Sphere diameter in metres.

        Returns:
            Sphere and billboard text markers sharing the same source frame/time.
        """
        sphere = self._marker(namespace, 0, Marker.SPHERE, pose, color)
        sphere.pose.orientation.x = sphere.pose.orientation.y = sphere.pose.orientation.z = 0.0
        sphere.pose.orientation.w = 1.0
        sphere.scale.x = sphere.scale.y = sphere.scale.z = float(diameter)
        text = self._marker(namespace, 1, Marker.TEXT_VIEW_FACING, pose, color)
        text.pose.position.z += self._param('label_height_m')
        text.pose.orientation.x = text.pose.orientation.y = text.pose.orientation.z = 0.0
        text.pose.orientation.w = 1.0
        text.scale.z = float(self._param('label_scale_m'))
        text.text = label
        return [sphere, text]

    def _object_label(self) -> str:
        """Describe object identity and a distance whose reference is explicit.

        Returns:
            Sanitized label and measured coordinate/depth distance information.
        """
        event = self._object_event or {}
        label = sanitize_text(event.get('target') or event.get('label') or 'Object', limit=80)
        if self._object_pose is not None and self._object_pose.header.frame_id == 'base_link':
            position = self._object_pose.pose.position
            distance = math.sqrt(position.x**2 + position.y**2 + position.z**2)
            return f'OBJECT: {label} at {distance:.2f} m from base_link'
        depth = event.get('depth_m')
        if not isinstance(depth, bool) and isinstance(depth, (int, float)) and (
                math.isfinite(depth) and depth > 0):
            return f'OBJECT: {label} at camera depth {depth:.2f} m'
        return f'OBJECT: {label} (distance unavailable)'

    def _refresh(self) -> None:
        """Publish current observations and explicitly remove expired marker pairs."""
        markers = []
        waypoint = self._current_waypoint() if self._mission_id else None
        if waypoint is not None:
            name, values = waypoint
            pose = PoseStamped()
            pose.header.frame_id = self._map_frame
            pose.header.stamp = self.get_clock().now().to_msg()
            pose.pose.position.x, pose.pose.position.y = values['x'], values['y']
            pose.pose.orientation.w = 1.0
            markers += self._sphere_label(
                'eira/waypoint', pose, f'TARGET: {sanitize_text(name, limit=80)}',
                (0.0, 1.0, 0.0), self._param('waypoint_diameter_m'))
        now = time.monotonic()
        if (self._mission_id and self._object_pose is not None
                and self._object_received_at is not None
                and now - self._object_received_at <= self._param('pose_stale_s')
                and self._valid_pose(self._object_pose, self._param('pose_stale_s'))):
            markers += self._sphere_label(
                'eira/object', self._object_pose, self._object_label(),
                (1.0, 0.0, 0.0), self._param('object_diameter_m'))
        if (self._heading is not None and self._heading_received_at is not None
                and now - self._heading_received_at <= self._param('heading_stale_s')
                and self._valid_pose(self._heading)):
            arrow = self._marker('eira/heading', 0, Marker.ARROW, self._heading, (1.0, 1.0, 0.0))
            arrow.scale.x = float(self._param('heading_length_m'))
            arrow.scale.y = arrow.scale.z = float(self._param('heading_width_m'))
            markers.append(arrow)
        current = {(marker.ns, marker.id) for marker in markers}
        self._delete(self._shown - current)
        if markers:
            self._pub.publish(MarkerArray(markers=markers))
        self._shown = current


def main(args: list[str] | None = None) -> None:
    """Run observational RViz markers without starting hardware or control nodes.

    Args:
        args: Optional ROS command-line arguments.
    """
    rclpy.init(args=args)
    node = None
    try:
        node = VisualizationMarkers()
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        if node is not None:
            node.destroy_node()
        rclpy.try_shutdown()
