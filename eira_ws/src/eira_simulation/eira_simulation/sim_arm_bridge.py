"""Bridge existing Yahboom arm interfaces to measured Gazebo joint trajectories.

Author: E-AIRA maintainers.
Hardware target: M3 Pro Gazebo simulation / Jetson Orin NX development, ROS 2 Humble.
This adapter is simulation-only. It never creates replacement vendor interface types,
never reports desired positions as measurements, and does not assert object contact.
"""

import json
import math
from pathlib import Path
import sys
from typing import Any

import numpy as np
import rclpy
from rclpy.duration import Duration
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.time import Time
from sensor_msgs.msg import JointState
from std_msgs.msg import String
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint

from eira_brain.console import format_line, sanitize_text
from eira_simulation.kinematics import (
    ARM_JOINTS, FINGER_JOINTS, KinematicsError, URDFChain, joints_to_servo,
    rotation_rpy, servo_to_joints,
)


class SimArmBridge(Node):
    """Translate degree-valued arm commands to the native model and expose numerical IK."""

    def __init__(self) -> None:
        """Load actual geometry, native vendor interfaces and measured-state subscriptions."""
        super().__init__('sim_arm_bridge')
        try:
            from arm_interface.msg import CurJoints
            from arm_interface.srv import ArmKinemarics
            from arm_msgs.msg import ArmJoint, ArmJoints
        except ImportError as exc:
            raise RuntimeError(
                'simulation requires existing arm_msgs and arm_interface packages') from exc
        defaults = {
            'robot_description_file': '', 'base_frame': 'base_link', 'tip_frame': 'Gripping',
            'servo_offsets_deg': [90.0] * 5, 'servo_signs': [1.0] * 5,
            'gripper_open_deg': 90.0, 'gripper_close_deg': 30.0,
            'gripper_open_rad': 0.0, 'gripper_close_rad': -1.0,
            'trajectory_topic': '/eira/sim/joint_trajectory', 'feedback_topic': '/joint_states',
            'feedback_timeout_s': 1.0, 'feedback_future_tolerance_s': 0.05,
            'default_runtime_ms': 2000, 'min_runtime_s': 0.05, 'max_runtime_s': 15.0,
            'ik_position_tolerance_m': 0.005, 'ik_orientation_tolerance_rad': 0.15,
            'ik_orientation_weight': 0.0, 'ik_max_iterations': 100,
            'ik_timeout_s': 0.25, 'ik_damping': 0.02, 'ik_epsilon': 1e-5,
            'ik_max_step_rad': 0.15, 'ik_restarts': 3, 'ik_random_seed': 42,
            'ik_joint4_max_deg': 90.0, 'allow_fk': True, 'command_hz': 50.0,
        }
        for name, value in defaults.items():
            self.declare_parameter(name, value)
        path = Path(str(self._p('robot_description_file'))).expanduser()
        if not path.is_file():
            raise ValueError('robot_description_file must identify the expanded M3 Pro URDF')
        self._chain = URDFChain.from_file(path, self._p('base_frame'), self._p('tip_frame'))
        required = (*ARM_JOINTS, *FINGER_JOINTS)
        if any(name not in self._chain.all_joints for name in required):
            raise ValueError('the supplied URDF lacks native M3 Pro arm/finger joints')
        self._offsets = list(self._p('servo_offsets_deg'))
        self._signs = list(self._p('servo_signs'))
        self._mapping = dict(gripper_open_deg=float(self._p('gripper_open_deg')),
                             gripper_close_deg=float(self._p('gripper_close_deg')),
                             gripper_open_rad=float(self._p('gripper_open_rad')),
                             gripper_close_rad=float(self._p('gripper_close_rad')))
        # Validate mapping against the actual URDF before accepting any command.
        self._validate_model(servo_to_joints([90.0] * 6, self._offsets, self._signs,
                                             **self._mapping))
        self._validate_model(servo_to_joints([90.0] * 5 + [self._p('gripper_close_deg')],
                                             self._offsets, self._signs, **self._mapping))
        if (self._p('feedback_timeout_s') <= 0 or self._p('min_runtime_s') <= 0
                or self._p('max_runtime_s') < self._p('min_runtime_s')):
            raise ValueError('invalid feedback/runtime bounds')
        self._measured: dict[str, float] = {}
        self._measurement_time: Time | None = None
        self._active_motion: dict[str, Any] | None = None
        self._CurJoints = CurJoints
        self._trajectory_pub = self.create_publisher(
            JointTrajectory, self._p('trajectory_topic'), 10)
        self._feedback_pub = self.create_publisher(CurJoints, '/Curjoints', 10)
        self._event_pub = self.create_publisher(String, '/eira/sim/arm/event', 10)
        self.create_subscription(JointState, self._p('feedback_topic'), self._on_states, 10)
        self.create_subscription(ArmJoints, '/arm6_joints', self._on_six, 10)
        self.create_subscription(ArmJoint, '/arm_joint', self._on_single, 10)
        self.create_service(ArmKinemarics, '/get_kinemarics', self._on_kinematics)
        if not math.isfinite(float(self._p('command_hz'))) or self._p('command_hz') <= 0:
            raise ValueError('command_hz must be positive and finite')
        self.create_timer(1.0 / self._p('command_hz'), self._tick_motion)
        self._emit('ready', model=str(path), inverse_kinematics='bounded_numerical_proxy',
                   object_contact_verified=False)

    def _p(self, name: str) -> Any:
        """Return a declared simulation parameter value."""
        return self.get_parameter(name).value

    def _emit(self, event: str, **fields: Any) -> None:
        """Publish structured simulation provenance without claiming physical grasp success."""
        payload = dict(event=event, environment='simulation', **fields)
        message = String()
        message.data = json.dumps(payload)
        self._event_pub.publish(message)
        detail = sanitize_text(fields.get('reason') or fields.get('model') or '')
        self.get_logger().info(format_line(
            'SIM ARM', event.replace('_', ' ').capitalize() + (f': {detail}' if detail else '')))

    def _validate_model(self, positions: dict[str, float]) -> None:
        """Reject model commands outside finite original joint limits."""
        for name, value in positions.items():
            joint = self._chain.all_joints[name]
            if not math.isfinite(value) or not joint.lower <= value <= joint.upper:
                raise ValueError(f'{name} command outside actual URDF joint limits')

    def _feedback_fresh(self) -> bool:
        """Return whether a measured joint-state stamp is recent in the simulation clock."""
        if self._measurement_time is None:
            return False
        age = (self.get_clock().now() - self._measurement_time).nanoseconds / 1e9
        return -self._p('feedback_future_tolerance_s') <= age <= self._p('feedback_timeout_s')

    def _on_states(self, message: JointState) -> None:
        """Publish Curjoints solely from complete finite Gazebo measured joint positions."""
        try:
            if len(message.name) != len(message.position):
                raise ValueError('joint-state names and positions must have equal lengths')
            now = self.get_clock().now()
            stamp = Time.from_msg(message.header.stamp, clock_type=now.clock_type)
            age = (now - stamp).nanoseconds / 1e9
            if not -self._p('feedback_future_tolerance_s') <= age <= self._p('feedback_timeout_s'):
                return
            positions = dict(zip(message.name, message.position))
            values = joints_to_servo(positions, self._offsets, self._signs, **self._mapping)
            self._validate_model({name: positions[name]
                                  for name in (*ARM_JOINTS, FINGER_JOINTS[0])})
            self._measured = {name: float(value) for name, value in positions.items()}
            self._measurement_time = stamp
            response = self._CurJoints()
            fields = response.get_fields_and_field_types()
            if 'int' in fields.get('joints', ''):
                response.joints = [int(round(value)) for value in values]
            else:
                response.joints = values
            self._feedback_pub.publish(response)
        except (ValueError, TypeError, KeyError, OverflowError) as exc:
            self.get_logger().warning(format_line(
                'SIM ARM', f'Joint feedback rejected: {sanitize_text(exc)}', 'warning'))

    def _send_trajectory(self, angles: list[float], runtime_ms: int) -> None:
        """Schedule a bounded measured-state trajectory within original velocity limits."""
        positions = servo_to_joints(angles, self._offsets, self._signs, **self._mapping)
        self._validate_model(positions)
        runtime_s = runtime_ms / 1000.0
        if not math.isfinite(runtime_s) or runtime_s <= 0:
            raise ValueError('positive trajectory duration is required')
        runtime_s = max(float(self._p('min_runtime_s')), runtime_s)
        if self._feedback_fresh():
            for name, value in positions.items():
                if name in self._measured:
                    limit = self._chain.all_joints[name].velocity
                    if limit <= 0:
                        raise ValueError('URDF joint velocity limit must be positive')
                    runtime_s = max(runtime_s, abs(value - self._measured[name]) / limit)
        if runtime_s > self._p('max_runtime_s'):
            raise ValueError('requested trajectory exceeds bounded runtime')
        self._active_motion = {
            'target': positions, 'duration_s': runtime_s, 'start_ns': None,
            'start': None, 'requested_ns': self.get_clock().now().nanoseconds}
        self._tick_motion()
        self._emit('trajectory_sent', duration_s=runtime_s, object_contact_verified=False)

    def _tick_motion(self) -> None:
        """Interpolate measured-to-target joints on the ROS simulation clock.

        Gazebo's native pose plugin applies each incoming point immediately; it
        does not interpolate JointTrajectory endpoints. Stream legal immediate
        single-point messages with frame_id=world rather than faking velocity
        compliance by attaching a duration to a teleported endpoint.
        """
        motion = getattr(self, '_active_motion', None)
        if motion is None:
            return
        now = self.get_clock().now().nanoseconds
        if not self._feedback_fresh() or any(name not in self._measured
                                             for name in motion['target']):
            if now-motion['requested_ns'] > self._p('feedback_timeout_s')*1e9:
                self._active_motion = None
                self._emit('trajectory_aborted', reason='measured joint feedback unavailable')
            return
        if motion['start_ns'] is None:
            motion['start_ns'] = now
            motion['start'] = {name: self._measured[name] for name in motion['target']}
        elapsed = max(0.0, (now-motion['start_ns'])/1e9)
        alpha = min(1.0, elapsed/motion['duration_s'])
        command = JointTrajectory()
        command.header.frame_id = 'world'
        command.header.stamp = self.get_clock().now().to_msg()
        command.joint_names = list(motion['target'])
        point = JointTrajectoryPoint()
        point.positions = [motion['start'][name] + alpha*(target-motion['start'][name])
                           for name, target in motion['target'].items()]
        point.time_from_start = Duration(seconds=0.0).to_msg()
        command.points = [point]
        self._trajectory_pub.publish(command)
        if alpha >= 1.0:
            self._active_motion = None

    def _on_six(self, message: Any) -> None:
        """Translate the unchanged ArmJoints command; invalid commands emit no trajectory."""
        try:
            angles = [float(getattr(message, f'joint{i}')) for i in range(1, 7)]
            self._send_trajectory(angles, int(message.time))
        except (ValueError, TypeError, AttributeError, OverflowError) as exc:
            self._emit('command_rejected', reason=str(exc))

    def _on_single(self, message: Any) -> None:
        """Change one servo only when complete recent measured state can preserve the others."""
        try:
            if not self._feedback_fresh():
                raise ValueError('single-joint command requires fresh measured joint states')
            index = int(message.id)
            if not 1 <= index <= 6:
                raise ValueError('servo ID must lie in [1, 6]')
            angles = joints_to_servo(self._measured, self._offsets, self._signs, **self._mapping)
            angles[index - 1] = float(message.joint)
            self._send_trajectory(angles, int(message.time))
        except (ValueError, TypeError, AttributeError, OverflowError) as exc:
            self._emit('command_rejected', reason=str(exc))

    @staticmethod
    def _assign_number(response: Any, name: str, value: float) -> None:
        """Assign a numeric field using its installed vendor interface's actual declared type."""
        fields = response.get_fields_and_field_types()
        if name not in fields:
            raise KinematicsError(f'installed ArmKinemarics response lacks required field {name}')
        setattr(response, name, int(round(value)) if 'int' in fields[name] else float(value))

    def _on_kinematics(self, request: Any, response: Any) -> Any:
        """Serve finite FK/IK requests; unreachable goals never return fabricated valid angles.

        Args:
            request: Native arm_interface ArmKinemarics request.
            response: Native response instance allocated by ROS.

        Returns:
            Valid response, or explicit success=false when that field exists on failure.

        Raises:
            KinematicsError: Invalid/unreachable IK when the installed interface has no
                failure-status field. The executor catches this and keeps the service alive;
                the caller's normal bounded response timeout then reports failure.
        """
        try:
            operation = str(request.kin_name).lower()
            if operation == 'fk' and self._p('allow_fk'):
                angles = [float(getattr(request, f'cur_joint{i}')) for i in range(1, 6)]
                positions = servo_to_joints(angles + [self._p('gripper_open_deg')],
                                            self._offsets, self._signs, **self._mapping)
                transform = self._chain.forward(positions)
                for name, value in zip(('x', 'y', 'z'), transform[:3, 3]):
                    self._assign_number(response, name, float(value))
                rotation = transform[:3, :3]
                roll = math.atan2(rotation[2, 1], rotation[2, 2])
                pitch = math.atan2(-rotation[2, 0], math.hypot(rotation[2, 1], rotation[2, 2]))
                yaw = math.atan2(rotation[1, 0], rotation[0, 0])
                for name, value in zip(('roll', 'pitch', 'yaw'), (roll, pitch, yaw)):
                    self._assign_number(response, name, value)
            elif operation == 'ik':
                target = np.array([float(request.tar_x), float(request.tar_y),
                                   float(request.tar_z)])
                desired = rotation_rpy(float(request.roll), float(request.pitch),
                                       float(request.yaw))
                # The high-level executor sets servo 5 itself, so solve the first four joints.
                q4_upper = math.radians(self._p('ik_joint4_max_deg') - self._offsets[3])
                extra = {}
                for name, offset, sign in zip(ARM_JOINTS, self._offsets, self._signs):
                    bounds = (math.radians(-offset) * sign,
                              math.radians(180.0 - offset) * sign)
                    extra[name] = (min(bounds), max(bounds))
                lo, hi = extra[ARM_JOINTS[3]]
                extra[ARM_JOINTS[3]] = ((max(lo, -q4_upper), hi) if self._signs[3] < 0
                                        else (lo, min(hi, q4_upper)))
                seed = dict(self._measured) if self._feedback_fresh() else {}
                result = self._chain.inverse(
                    target, seed, ARM_JOINTS[:4], extra_limits=extra, orientation=desired,
                    orientation_weight=float(self._p('ik_orientation_weight')),
                    tolerance_m=float(self._p('ik_position_tolerance_m')),
                    orientation_tolerance_rad=float(self._p('ik_orientation_tolerance_rad')),
                    max_iterations=int(self._p('ik_max_iterations')),
                    max_seconds=float(self._p('ik_timeout_s')),
                    damping=float(self._p('ik_damping')),
                    epsilon=float(self._p('ik_epsilon')), max_step_rad=self._p('ik_max_step_rad'),
                    restarts=int(self._p('ik_restarts')),
                    random_seed=int(self._p('ik_random_seed')))
                if not result.success:
                    residual = result.position_error_m
                    raise KinematicsError(f'unreachable target; residual={residual:.4f}m')
                values = [math.degrees(result.positions[name]) / sign + offset
                          for name, sign, offset in zip(ARM_JOINTS, self._signs, self._offsets)]
                if not all(0 <= value <= 180 for value in values):
                    raise KinematicsError('solution exceeds existing servo degree envelope')
                self._assign_number(response, 'joint1', 180.0 - values[0])
                for number in range(2, 5):
                    self._assign_number(response, f'joint{number}', values[number - 1])
                self._emit('ik_solved', position_error_m=result.position_error_m,
                           orientation_error_rad=result.orientation_error_rad,
                           orientation_constrained=bool(self._p('ik_orientation_weight') > 0),
                           object_contact_verified=False)
            else:
                raise KinematicsError(f'unsupported simulation kinematics operation: {operation}')
            if hasattr(response, 'success'):
                response.success = True
            return response
        except (ValueError, TypeError, AttributeError, KeyError, np.linalg.LinAlgError,
                KinematicsError) as exc:
            self._emit('ik_failed', reason=str(exc), object_contact_verified=False)
            if hasattr(response, 'success'):
                response.success = False
                return response
            raise KinematicsError(str(exc)) from exc


def main(args: list[str] | None = None) -> int:
    """Run simulation-only adapters and retain service availability after rejected IK goals."""
    rclpy.init(args=args)
    node = None
    try:
        node = SimArmBridge()
        while rclpy.ok():
            try:
                rclpy.spin_once(node, timeout_sec=0.1)
            except KinematicsError as exc:
                node.get_logger().warning(format_line(
                    'SIM ARM', f'IK unavailable: {sanitize_text(exc)}', 'warning'))
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    except (RuntimeError, ValueError, OSError) as exc:
        if node is not None:
            node.get_logger().error(format_line(
                'SIM ARM', f'Startup failed: {sanitize_text(exc)}', 'error'))
        else:
            import logging
            logging.getLogger('sim_arm_bridge').error('startup failed: %s', exc)
        return 2
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    return 0


if __name__ == '__main__':
    sys.exit(main())
