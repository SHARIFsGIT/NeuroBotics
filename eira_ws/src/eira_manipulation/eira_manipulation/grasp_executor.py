"""Run correlated, cancellable base-alignment and Yahboom arm sequences.

Author: E-AIRA maintainers.
Hardware target: ROSMASTER M3 Pro, Jetson Orin NX, ROS 2 Humble/Python 3.10.
The node uses existing IK and servo interfaces; it does not implement a driver.
"""

from concurrent.futures import CancelledError
from dataclasses import dataclass
import json
import math
import threading
import time
from typing import Any

import rclpy
from rclpy.duration import Duration
from rclpy.executors import ExternalShutdownException, MultiThreadedExecutor
from rclpy.node import Node
from rclpy.time import Time
import tf2_geometry_msgs  # noqa: F401 -- register PointStamped transforms
import tf2_ros
from tf2_ros.buffer_interface import TypeException

from arm_interface.msg import CurJoints
from arm_interface.srv import ArmKinemarics
from arm_msgs.msg import ArmJoint, ArmJoints
from geometry_msgs.msg import PointStamped, PoseStamped, Twist
from std_msgs.msg import Bool, String, UInt16

from eira_brain.console import error_hint, format_line, sanitize_text
from eira_manipulation.grasp_policy import (
    calibrated_gripper_angle, joint_vector, request_envelope,
)
from eira_manipulation.pid import PID


@dataclass
class ArmStep:
    """Represent one bounded actuator step; angles are in driver degrees.

    Args:
        joints: Six-joint target or None for a single-joint command.
        angle: Gripper target for a single-joint command.
        duration_s: Minimum execution duration, never shorter than driver runtime.
        description: Operator-facing description logged when this step is dispatched.
    """

    joints: list[int] | None
    angle: int | None = None
    duration_s: float = 0.0
    description: str = ''


class GraspExecutor(Node):
    """Serialize validated requests, asynchronous IK and feedback-aware motions."""

    IDLE = 'IDLE'
    WAIT_SERVICE = 'WAIT_SERVICE'
    WAIT_CONFIRM = 'WAIT_CONFIRM'
    ALIGN = 'ALIGN'
    WAIT_IK = 'WAIT_IK'
    WAIT_ARM = 'WAIT_ARM'

    def __init__(self) -> None:
        """Declare calibration, interfaces and the bounded execution state machine."""
        super().__init__('grasp_executor')
        defaults = {
            'standoff_dist': 0.19, 'dist_tol': 0.03, 'yaw_tol': 0.06,
            'max_lin_vel': 0.15, 'max_rev_vel': 0.08, 'max_ang_vel': 1.2,
            'lin_kp': 0.5, 'lin_ki': 0.0, 'lin_kd': 0.1,
            'ang_kp': 1.2, 'ang_ki': 0.0, 'ang_kd': 0.05,
            'settle_ticks': 3, 'align_timeout_s': 45.0, 'target_timeout_s': 1.5,
            'stale_grace_ticks': 3, 'service_wait_s': 5.0, 'control_hz': 20.0,
            'arm_base_frame': '', 'base_frame': 'base_link',
            'arm_mount_x': 0.0, 'arm_mount_y': 0.0, 'arm_mount_z': 0.0,
            'arm_mount_yaw': 0.0, 'static_mount_calibrated': False,
            'grasp_x_compensation': -0.015, 'grasp_pitch': 1.3962614348313127,
            'grasp_joint5': 90, 'gripper_open': 90, 'gripper_close': 30,
            'gripper_carry': 115, 'arm_runtime_ms': 2000, 'hold_runtime_ms': 100,
            'init_joints': [90, 140, 20, 10, 90, 180],
            'transport_joints': [90, 150, 12, 20, 90, 120],
            'joint_lower_limits': [0.0] * 6, 'joint_upper_limits': [180.0] * 6,
            'ik_timeout_s': 5.0, 'ik_retries': 1, 'tf_timeout_s': 0.2,
            'joint_feedback_timeout_s': 1.0, 'joint_tolerance_deg': 5.0,
            'joint_feedback_is_measured': False,
            'require_joint_feedback': True, 'arm_step_timeout_s': 6.0,
            'sequence_settle_s': 0.5, 'max_pose_age_s': 1.5,
            'pose_future_tolerance_s': 0.1, 'rotation_only_bearing': 0.35,
            'require_gesture_confirmation': False, 'gesture_timeout_s': 15.0,
            'gripper_mode': 'fixed', 'gripper_width_table': '[]',
            'width_metadata_timeout_s': 5.0, 'sort_poses': '{}',
            'require_actuator_subscribers': True, 'request_cache_size': 32,
            'allow_legacy_requests': True,
        }
        for name, value in defaults.items():
            self.declare_parameter(name, value)
        if self._p('control_hz') <= 0 or self._p('ik_timeout_s') <= 0:
            raise ValueError('control_hz and ik_timeout_s must be positive')
        self._lower = list(self._p('joint_lower_limits'))
        self._upper = list(self._p('joint_upper_limits'))
        self._init_joints = self._validate_joints(self._p('init_joints'))
        self._transport_joints = self._validate_joints(self._p('transport_joints'))
        self._lin_pid = PID(self._p('lin_kp'), self._p('lin_ki'), self._p('lin_kd'),
                            -self._p('max_rev_vel'), self._p('max_lin_vel'))
        self._ang_pid = PID(self._p('ang_kp'), self._p('ang_ki'), self._p('ang_kd'),
                            -self._p('max_ang_vel'), self._p('max_ang_vel'))
        self._lock = threading.RLock()
        self._state = self.IDLE
        self._mission_id = ''
        self._action_id = ''
        self._request: dict[str, Any] = {}
        self._completed: dict[tuple[str, str], dict[str, Any]] = {}
        self._target: PoseStamped | None = None
        self._target_time: float | None = None
        self._cur_joints: list[int] | None = None
        self._feedback_time: float | None = None
        self._metadata: dict[str, Any] = {}
        self._metadata_time: float | None = None
        self._generation = 0
        self._ik_id = 0
        self._ik_future = None
        self._ik_request = None
        self._ik_retries_left = 0
        self._deadline = 0.0
        self._steps: list[ArmStep] = []
        self._active_step: ArmStep | None = None
        self._step_target: list[int] | None = None
        self._step_started = 0.0
        self._step_wait_until = 0.0
        self._final_event = ''
        self._settle_count = 0
        self._last_settled_stamp: tuple[int, int] | None = None
        self._stale_ticks = 0
        self._last_tick: float | None = None
        self._tf_buffer = tf2_ros.Buffer()
        self._tf_listener = tf2_ros.TransformListener(self._tf_buffer, self, spin_thread=False)
        self.create_subscription(PoseStamped, 'target_pose', self._on_target_pose, 10)
        self.create_subscription(CurJoints, 'Curjoints', self._on_cur_joints, 10)
        self.create_subscription(String, 'eira/manipulation/request', self._on_request, 10)
        self.create_subscription(String, 'eira/vision/event', self._on_vision_event, 10)
        self.create_subscription(String, 'eira/gesture', self._on_gesture, 10)
        self._cmd_pub = self.create_publisher(Twist, 'cmd_vel', 1)
        self._six_pub = self.create_publisher(ArmJoints, 'arm6_joints', 10)
        self._single_pub = self.create_publisher(ArmJoint, 'arm_joint', 10)
        self._grasp_done_pub = self.create_publisher(Bool, 'grasp_done', 1)
        self._event_pub = self.create_publisher(String, 'eira/manipulation/event', 10)
        self._beep_pub = self.create_publisher(UInt16, 'beep', 10)
        self._kin_client = self.create_client(ArmKinemarics, 'get_kinemarics')
        self.create_timer(1.0 / self._p('control_hz'), self._tick)
        self._log_event('manipulation_ready')

    def _p(self, name: str) -> Any:
        """Return a declared parameter value.

        Args:
            name: ROS parameter name.

        Returns:
            Parameter's configured value.
        """
        return self.get_parameter(name).value

    def _validate_joints(self, values: Any) -> list[int]:
        """Return six angles within configured limits or raise ValueError."""
        return joint_vector(values, self._lower, self._upper)

    def _pose_age(self, msg: PoseStamped) -> float:
        """Return measurement age in ROS seconds, retaining simulation-clock semantics."""
        now = self.get_clock().now()
        stamp = Time.from_msg(msg.header.stamp, clock_type=now.clock_type)
        return (now - stamp).nanoseconds / 1e9

    def _on_target_pose(self, msg: PoseStamped) -> None:
        """Cache only finite, recently measured poses in the required base frame.

        Args:
            msg: Measured target pose, whose stamp must be nonzero.
        """
        with self._lock:
            p = msg.pose.position
            stamp = msg.header.stamp
            age = self._pose_age(msg)
            if (msg.header.frame_id != self._p('base_frame')
                    or not all(math.isfinite(v) for v in (p.x, p.y, p.z))
                    or (stamp.sec == 0 and stamp.nanosec == 0)
                    or age < -self._p('pose_future_tolerance_s')
                    or age > self._p('max_pose_age_s')):
                self._log_event('invalid_target_pose')
                return
            self._target = msg
            self._target_time = time.monotonic()

    def _on_cur_joints(self, msg: CurJoints) -> None:
        """Validate and cache degree-valued feedback from the existing arm stack."""
        try:
            values = self._validate_joints(list(msg.joints))
        except (ValueError, TypeError, OverflowError) as exc:
            self._log_event('invalid_joint_feedback', reason=str(exc))
            return
        with self._lock:
            self._cur_joints = values
            self._feedback_time = time.monotonic()

    def _on_vision_event(self, msg: String) -> None:
        """Cache correlated object width/color and react to current-mission target loss."""
        try:
            event = json.loads(msg.data)
        except json.JSONDecodeError:
            return
        if not isinstance(event, dict):
            return
        with self._lock:
            mission = str(event.get('mission_id', ''))
            if event.get('event') == 'found':
                if self._state != self.IDLE and mission != self._mission_id:
                    return
                self._metadata = event
                self._metadata_time = time.monotonic()
            same_acquisition = (str(event.get('action_id', ''))
                                == str(self._metadata.get('action_id', '')))
            if (mission == self._mission_id and same_acquisition
                    and event.get('event') in ('lost', 'timeout')
                    and self._state in (self.ALIGN, self.WAIT_CONFIRM)):
                self._fail('target lost during alignment')

    def _on_gesture(self, msg: String) -> None:
        """Confirm the active grasp with OK or cancel with Thumb_down."""
        try:
            event = json.loads(msg.data)
        except json.JSONDecodeError:
            event = {'gesture': msg.data}
        if not isinstance(event, dict):
            return
        with self._lock:
            if event.get('mission_id') and str(event['mission_id']) != self._mission_id:
                return
            if event.get('action_id') and str(event['action_id']) != self._action_id:
                return
            gesture = str(event.get('gesture', '')).lower().replace('_', '')
            if gesture in ('thumbdown', 'thumbsdown') and self._state != self.IDLE:
                self._stop()
            elif gesture in ('ok', 'okay') and self._state == self.WAIT_CONFIRM:
                self._start_alignment()

    def _on_request(self, msg: String) -> None:
        """Decode, deduplicate and serialize correlated commands; stop always preempts."""
        try:
            request = request_envelope(msg.data)
        except ValueError as exc:
            self._log_event('invalid_request', reason=str(exc))
            return
        with self._lock:
            mission, action = request['mission_id'], request['action_id']
            if not mission and not self._p('allow_legacy_requests'):
                self._log_event('legacy_request_rejected')
                return
            key = (mission, action)
            if request['command'] == 'stop':
                self._stop()
                return
            if mission and key in self._completed:
                self._publish_payload(self._completed[key])
                return
            if self._state != self.IDLE:
                if key != (self._mission_id, self._action_id) or not mission:
                    self._publish_payload({'event': 'failed', 'reason': f'busy ({self._state})',
                                           'mission_id': mission, 'action_id': action})
                return
            self._mission_id, self._action_id = mission, action
            self._request = request
            context = request.get('target')
            if (isinstance(context, dict)
                    and str(context.get('mission_id', '')) == mission):
                self._metadata = context
                self._metadata_time = time.monotonic()
            self._generation += 1
            if request['command'] == 'grasp':
                self._start_grasp()
            elif request['command'] == 'release':
                self._start_release()
            else:
                self._start_home()

    def _start_grasp(self) -> None:
        """Wait nonblocking for IK availability before alignment and optional confirmation."""
        if self._target is None or self._target_stale():
            self._fail('no fresh /target_pose')
            return
        metadata_stale = (self._metadata_time is None or time.monotonic() - self._metadata_time
                          > self._p('width_metadata_timeout_s'))
        if self._mission_id and (str(self._metadata.get('mission_id', '')) != self._mission_id
                                 or metadata_stale):
            self._fail('no correlated target acquisition for this mission')
            return
        self._state = self.WAIT_SERVICE
        self._deadline = time.monotonic() + self._p('service_wait_s')
        self._log_event('waiting_service')

    def _start_alignment(self) -> None:
        """Reset PID history and arm a finite alignment deadline."""
        self._lin_pid.reset()
        self._ang_pid.reset()
        self._settle_count = self._stale_ticks = 0
        self._last_settled_stamp = None
        self._deadline = time.monotonic() + self._p('align_timeout_s')
        self._state = self.ALIGN
        self._log_event('aligning')

    def _runtime_s(self) -> float:
        """Return servo runtime plus the configured settling interval."""
        return self._p('arm_runtime_ms') / 1000.0 + self._p('sequence_settle_s')

    def _start_release(self) -> None:
        """Release at the calibrated color destination, or the standard transport pose."""
        pose = list(self._transport_joints)
        try:
            poses = json.loads(self._p('sort_poses'))
            if not isinstance(poses, dict):
                raise ValueError('sort_poses must be a JSON object')
            context = self._request.get('target')
            color = self._request.get('color')
            if not color and isinstance(context, dict):
                # Sorting is explicitly enabled only when calibrated destinations exist.
                color = context.get('color', '') if poses else ''
            elif not color and isinstance(context, str):
                color = context
            if color:
                if color not in poses:
                    raise ValueError(f'no calibrated sorting pose for {color}')
                pose = self._validate_joints(poses[color])
        except (ValueError, TypeError, OverflowError) as exc:
            self._fail(str(exc))
            return
        self._begin_sequence([
            ArmStep(pose, description='Moving to release pose'),
            ArmStep(None, int(self._p('gripper_open')), description='Opening gripper'),
            ArmStep(list(self._init_joints), description='Returning arm home'),
        ], 'released')

    def _start_home(self) -> None:
        """Queue the configured home pose with feedback-aware completion."""
        self._begin_sequence([
            ArmStep(list(self._init_joints), description='Returning arm home')], 'homed')

    def _invalidate_ik(self) -> None:
        """Invalidate every outstanding IK callback before canceling the local future."""
        self._ik_id += 1
        future, self._ik_future = self._ik_future, None
        if future is not None and not future.done():
            future.cancel()

    def _hold_arm(self) -> bool:
        """Command a best-effort servo hold only from fresh received joint feedback.

        Returns:
            Whether a feedback-derived hold command was published. This is not a
            hardware emergency stop; absent feedback is reported instead of guessed.
        """
        if not self._p('joint_feedback_is_measured') or not self._feedback_fresh():
            return False
        self._pub_six(list(self._cur_joints), int(self._p('hold_runtime_ms')))
        return True

    def _stop(self) -> None:
        """Invalidate pending work, zero the base and publish a feedback-derived arm hold."""
        self._generation += 1
        self._invalidate_ik()
        self._zero_cmd()
        self._state = self.IDLE
        self._steps.clear()
        self._active_step = None
        held = self._hold_arm()
        self._emit_event('stopped', arm_hold_sent=held,
                         reason='' if held else 'fresh measured arm feedback unavailable')

    def _tick(self) -> None:
        """Advance one serialized state-machine tick and fail safely on transport errors."""
        with self._lock:
            now = time.monotonic()
            dt = 1.0 / self._p('control_hz') if self._last_tick is None else now - self._last_tick
            self._last_tick = now
            try:
                if self._state == self.WAIT_SERVICE:
                    if self._kin_client.service_is_ready():
                        if self._p('require_gesture_confirmation'):
                            self._state = self.WAIT_CONFIRM
                            self._deadline = now + self._p('gesture_timeout_s')
                            self._emit_event('confirmation_required')
                        else:
                            self._start_alignment()
                    elif now > self._deadline:
                        self._fail('get_kinemarics service unavailable')
                elif self._state == self.WAIT_CONFIRM and now > self._deadline:
                    self._fail('gesture confirmation timeout')
                elif self._state == self.ALIGN:
                    self._tick_align(dt, now)
                elif self._state == self.WAIT_IK and now > self._deadline:
                    self._invalidate_ik()
                    if self._ik_retries_left > 0:
                        self._ik_retries_left -= 1
                        self._log_event('ik_retry')
                        self._send_ik()
                    else:
                        self._fail('IK response timeout')
                elif self._state == self.WAIT_ARM:
                    self._tick_sequence(now)
            except (RuntimeError, ValueError, TypeError, AttributeError, OverflowError) as exc:
                self._fail(f'manipulation transport or validation error: {exc}')

    def _tick_align(self, dt: float, now: float) -> None:
        """Apply bounded base PID only while the measurement is fresh and finite."""
        if now > self._deadline:
            self._fail('alignment timeout')
            return
        if self._target_stale():
            self._stale_ticks += 1
            self._zero_cmd()
            if self._stale_ticks >= self._p('stale_grace_ticks'):
                self._fail('target pose stale')
            return
        self._stale_ticks = 0
        point = self._target.pose.position
        distance, bearing = math.hypot(point.x, point.y), math.atan2(point.y, point.x)
        angular = self._ang_pid.update(bearing, dt)
        linear = 0.0 if abs(bearing) > self._p('rotation_only_bearing') else self._lin_pid.update(
            distance - self._p('standoff_dist'), dt)
        self._drive(linear, angular)
        settled = (abs(distance - self._p('standoff_dist')) < self._p('dist_tol')
                   and abs(bearing) < self._p('yaw_tol'))
        stamp = (self._target.header.stamp.sec, self._target.header.stamp.nanosec)
        if not settled:
            self._settle_count = 0
        elif stamp != self._last_settled_stamp:
            self._settle_count += 1
        self._last_settled_stamp = stamp
        if self._settle_count >= self._p('settle_ticks'):
            self._zero_cmd()
            self._begin_arm_grasp()

    def _begin_arm_grasp(self) -> None:
        """Build the original IK request only after resolving a calibrated arm frame."""
        target = self._target_in_arm_frame()
        if target is None:
            self._fail('arm frame unavailable; configure TF or calibrate static mount')
            return
        request = ArmKinemarics.Request()
        request.kin_name = 'ik'
        request.tar_x = target[0] + self._p('grasp_x_compensation')
        request.tar_y, request.tar_z = target[1], target[2]
        request.roll, request.pitch, request.yaw = 0.0, self._p('grasp_pitch'), 0.0
        self._ik_request = request
        self._ik_retries_left = int(self._p('ik_retries'))
        self._send_ik()

    def _send_ik(self) -> None:
        """Send a generation-tagged IK request with a finite local response deadline."""
        self._ik_id += 1
        token = (self._generation, self._ik_id)
        self._state = self.WAIT_IK
        self._deadline = time.monotonic() + self._p('ik_timeout_s')
        self._log_event('ik_request')
        future = self._kin_client.call_async(self._ik_request)
        self._ik_future = future
        future.add_done_callback(lambda reply: self._on_ik_response(reply, token))

    def _on_ik_response(self, future: Any, token: tuple[int, int]) -> None:
        """Reject stale responses and adapt validated IK angles to Yahboom conventions."""
        with self._lock:
            if (token != (self._generation, self._ik_id) or self._state != self.WAIT_IK):
                return
            try:
                response = future.result()
                if response is None or getattr(response, 'success', True) is False:
                    raise ValueError('IK returned no reachable solution')
                raw = [float(getattr(response, f'joint{i}')) for i in range(1, 5)]
                if not all(math.isfinite(v) for v in raw):
                    raise ValueError('IK returned nonfinite angles')
                joints = [180 - raw[0], raw[1], raw[2], min(raw[3], 90.0), 90, 0]
                joint5 = float(self._p('grasp_joint5'))
                if joint5 < 0:
                    wrist = abs(joint5)
                    wrist = (180 - joints[0] + wrist - 90 if wrist < 90
                             else wrist - joints[0] + 90)
                elif joint5 > 0:
                    wrist = 180 - abs(joint5)
                    wrist -= joints[0] if joint5 < 90 else joints[0] - 90
                else:
                    wrist = 90.0
                if wrist > 135:
                    wrist -= 90
                elif wrist < 45:
                    wrist += 90
                joints[4] = wrist
                close_angle = int(self._p('gripper_close'))
                if self._p('gripper_mode') == 'width':
                    width = float(self._metadata.get('width_m', float('nan')))
                    close_angle = calibrated_gripper_angle(width, self._p('gripper_width_table'))
                elif self._p('gripper_mode') != 'fixed':
                    raise ValueError('gripper_mode must be fixed or width')
                joints[5] = int(self._p('gripper_open'))
                reach = self._validate_joints(joints)
                closed = list(reach)
                closed[5] = close_angle
                closed = self._validate_joints(closed)
                transport = list(self._transport_joints)
                transport[5] = close_angle
                self._begin_sequence([
                    ArmStep(None, int(self._p('gripper_open')), description='Opening gripper'),
                    ArmStep(reach, description='Reaching toward object'),
                    ArmStep(None, closed[5], description='Closing gripper'),
                    ArmStep(self._validate_joints(transport), description='Moving to carry pose'),
                ], 'grasped')
            except (RuntimeError, ValueError, TypeError, AttributeError, OverflowError,
                    CancelledError) as exc:
                self._fail(f'IK response invalid: {exc}')

    def _begin_sequence(self, steps: list[ArmStep], final: str) -> None:
        """Start a sequence after enforcing connected actuators and required feedback."""
        if self._p('require_actuator_subscribers') and (
                self._six_pub.get_subscription_count() == 0
                or self._single_pub.get_subscription_count() == 0):
            self._fail('arm command subscribers unavailable')
            return
        if self._p('require_joint_feedback') and not self._feedback_fresh():
            self._fail('fresh joint feedback required')
            return
        self._steps, self._active_step = steps, None
        self._final_event = final
        self._state = self.WAIT_ARM

    def _tick_sequence(self, now: float) -> None:
        """Wait for runtime and fresh joint convergence before dispatching the next step."""
        if self._active_step is not None:
            if now < self._step_wait_until:
                return
            verified = (self._feedback_fresh() and self._feedback_time >= self._step_started
                        and self._step_target is not None
                        and all(abs(a - b) <= self._p('joint_tolerance_deg')
                                for a, b in zip(self._cur_joints, self._step_target)))
            if self._p('require_joint_feedback') and not verified:
                if now > self._step_wait_until + self._p('arm_step_timeout_s'):
                    self._fail('joint convergence timeout')
                return
            self._active_step = None
        if not self._steps:
            self._state = self.IDLE
            if self._final_event == 'grasped':
                done = Bool()
                done.data = True
                self._grasp_done_pub.publish(done)
            verified = bool(self._p('require_joint_feedback')
                            and self._p('joint_feedback_is_measured'))
            self._emit_event(self._final_event, joint_feedback_verified=verified,
                             reported_joint_convergence=bool(self._p('require_joint_feedback')),
                             object_contact_verified=False)
            return
        step = self._steps.pop(0)
        self._active_step = step
        self._step_started = now
        self._step_wait_until = now + max(step.duration_s, self._runtime_s())
        if step.joints is not None:
            self._step_target = self._validate_joints(step.joints)
            self._pub_six(self._step_target)
        else:
            self._step_target = list(self._cur_joints) if self._feedback_fresh() else None
            if self._step_target is not None:
                self._step_target[5] = int(step.angle)
            self._pub_single(6, int(step.angle))
        self._log_event('step', description=step.description or (
            'Moving arm to next pose' if step.joints is not None else 'Moving gripper'))

    def _target_in_arm_frame(self) -> tuple[float, float, float] | None:
        """Resolve a measurement-time TF or explicitly calibrated static mount.

        Returns:
            Arm-frame coordinates in metres, or None when calibration is unavailable.
        """
        if self._target is None or self._target_stale():
            return None
        pose = self._target.pose.position
        frame = str(self._p('arm_base_frame'))
        if frame:
            point = PointStamped()
            point.header = self._target.header
            point.point.x, point.point.y, point.point.z = pose.x, pose.y, pose.z
            try:
                transformed = self._tf_buffer.transform(
                    point, frame, timeout=Duration(seconds=self._p('tf_timeout_s')))
                return transformed.point.x, transformed.point.y, transformed.point.z
            except (tf2_ros.TransformException, TypeException, TypeError, RuntimeError) as exc:
                self._log_event('arm_tf_unavailable', reason=str(exc))
        if not self._p('static_mount_calibrated'):
            return None
        dx = pose.x - self._p('arm_mount_x')
        dy = pose.y - self._p('arm_mount_y')
        dz = pose.z - self._p('arm_mount_z')
        yaw = -self._p('arm_mount_yaw')
        return math.cos(yaw) * dx - math.sin(yaw) * dy, math.sin(yaw) * dx + math.cos(yaw) * dy, dz

    def _target_stale(self) -> bool:
        """Return whether receipt or original measurement freshness has expired."""
        if self._target is not None and self._mission_id:
            acquired = self._metadata.get('measurement_stamp_ns')
            if isinstance(acquired, int):
                stamp = self._target.header.stamp
                if stamp.sec * 1000000000 + stamp.nanosec < acquired:
                    return True
        return (self._target is None or self._target_time is None
                or time.monotonic() - self._target_time > self._p('target_timeout_s')
                or self._pose_age(self._target) > self._p('max_pose_age_s'))

    def _feedback_fresh(self) -> bool:
        """Return whether valid received feedback is available for hold/convergence."""
        return (self._cur_joints is not None and self._feedback_time is not None
                and time.monotonic() - self._feedback_time <= self._p('joint_feedback_timeout_s'))

    def _drive(self, linear: float, angular: float) -> None:
        """Publish a finite bounded velocity on the launch-remapped arm command channel."""
        if not math.isfinite(linear) or not math.isfinite(angular):
            raise ValueError('nonfinite velocity')
        twist = Twist()
        twist.linear.x = max(-self._p('max_rev_vel'), min(self._p('max_lin_vel'), linear))
        twist.angular.z = max(-self._p('max_ang_vel'), min(self._p('max_ang_vel'), angular))
        self._cmd_pub.publish(twist)

    def _zero_cmd(self) -> None:
        """Publish zero velocity to the base command gate."""
        self._drive(0.0, 0.0)

    def _pub_six(self, joints: list[int], runtime_ms: int | None = None) -> None:
        """Validate and publish one six-servo command using unchanged driver fields."""
        values = self._validate_joints(joints)
        message = ArmJoints()
        for index, value in enumerate(values, 1):
            setattr(message, f'joint{index}', value)
        message.time = int(self._p('arm_runtime_ms') if runtime_ms is None else runtime_ms)
        if message.time <= 0:
            raise ValueError('servo command duration must be positive')
        self._six_pub.publish(message)

    def _pub_single(self, joint_id: int, angle: int) -> None:
        """Publish a bounded one-servo command without shortening its execution wait."""
        if not 1 <= joint_id <= 6 or not self._lower[joint_id - 1] <= angle <= self._upper[
                joint_id - 1]:
            raise ValueError('single joint command exceeds calibrated limits')
        message = ArmJoint()
        message.id, message.joint = int(joint_id), int(angle)
        message.time = int(self._p('arm_runtime_ms'))
        self._single_pub.publish(message)

    def _publish_payload(self, payload: dict[str, Any]) -> None:
        """Publish the unchanged JSON contract and show a readable terminal event."""
        payload = dict(payload, wall_time=time.time())
        message = String()
        message.data = json.dumps(payload)
        self._event_pub.publish(message)
        self._log_event(str(payload.get('event', 'update')), **{
            key: value for key, value in payload.items() if key != 'event'})

    def _log_event(self, event: str, **fields: Any) -> None:
        """Describe arm progress without exposing JSON or repeating unchanged messages.

        Args:
            event: Internal progress or public manipulation event name.
            **fields: Event details, including failure/verification evidence.
        """
        messages = {
            'manipulation_ready': 'Ready for grasp, release and arm-home requests',
            'invalid_target_pose': ('Ignoring target pose: wrong frame or '
                                    'stale/invalid measurement'),
            'invalid_joint_feedback': 'Ignoring invalid joint feedback',
            'invalid_request': 'Ignoring invalid arm request',
            'legacy_request_rejected': 'Request rejected: mission and action IDs are required',
            'waiting_service': 'Waiting for arm inverse-kinematics service',
            'aligning': 'Aligning base with target',
            'ik_request': 'Waiting for inverse-kinematics solution',
            'ik_retry': 'IK timed out; retrying',
            'confirmation_required': 'Waiting for OK gesture to confirm grasp',
            'released': 'Release sequence complete',
            'homed': 'Arm home sequence complete',
            'arm_tf_unavailable': 'Cannot transform target into the arm frame',
            'shutdown_stop_failed': 'Arm shutdown stop failed',
        }
        reason = error_hint(fields.get('reason', ''))
        severity = 'info'
        if event == 'failed':
            text, severity = 'Action failed', 'error'
        elif event == 'stopped':
            held = fields.get('arm_hold_sent') is True
            text = 'Stopped; arm hold sent' if held else 'Stopped; arm hold unavailable'
            severity = 'info' if held else 'warning'
            if not held:
                text += '; ' + error_hint('fresh measured arm feedback unavailable')
        elif event == 'grasped':
            verified = (fields.get('object_contact_verified') is True
                        and isinstance(fields.get('object_held'), bool))
            if verified and fields['object_held']:
                text = 'Grasp complete; object holding verified'
            elif verified:
                text, severity = 'Grasp sequence complete; object not held (verified)', 'warning'
            else:
                text = 'Grasp sequence complete; object holding is unverified'
        elif event == 'step':
            text = sanitize_text(fields.get('description', 'Moving arm'))
        else:
            text = messages.get(event, sanitize_text(event.replace('_', ' ').capitalize()))
            if event in ('invalid_target_pose', 'invalid_joint_feedback', 'invalid_request',
                         'legacy_request_rejected', 'arm_tf_unavailable', 'ik_retry',
                         'shutdown_stop_failed'):
                severity = 'warning'
        if reason:
            text += ': ' + reason
        signature = (event, text, fields.get('mission_id', getattr(self, '_mission_id', '')),
                     fields.get('action_id', getattr(self, '_action_id', '')))
        if signature == getattr(self, '_console_last', None):
            return
        self._console_last = signature
        logger = self.get_logger()
        # Humble requires one logger severity per call site. Styling retains urgency.
        logger.info(format_line('ARM', text, severity))

    def _emit_event(self, event: str, **fields: Any) -> None:
        """Echo correlation IDs and retain terminal responses for duplicate requests."""
        payload = dict(event=event, mission_id=self._mission_id,
                       action_id=self._action_id, **fields)
        self._publish_payload(payload)
        if event in ('grasped', 'released', 'homed', 'failed', 'stopped') and self._mission_id:
            self._completed[(self._mission_id, self._action_id)] = payload
            while len(self._completed) > max(1, int(self._p('request_cache_size'))):
                self._completed.pop(next(iter(self._completed)))

    def _fail(self, reason: str) -> None:
        """Invalidate work, stop the base, hold from fresh feedback and emit failure."""
        self._generation += 1
        self._invalidate_ik()
        self._zero_cmd()
        self._state = self.IDLE
        self._steps.clear()
        self._active_step = None
        held = self._hold_arm()
        self._emit_event('failed', reason=reason, arm_hold_sent=held)

    def _beep(self, duration_ms: int) -> None:
        """Publish a bounded buzzer duration through the existing UInt16 interface."""
        message = UInt16()
        message.data = max(0, min(60000, duration_ms))
        self._beep_pub.publish(message)

    def destroy_node(self) -> None:
        """Invalidate asynchronous work and issue best-effort stops before teardown."""
        with self._lock:
            self._generation += 1
            self._invalidate_ik()
            try:
                self._zero_cmd()
                self._hold_arm()
            except (RuntimeError, ValueError):
                self._log_event('shutdown_stop_failed',
                                reason='Arm stop could not be sent during shutdown')
        super().destroy_node()


def main(args: list[str] | None = None) -> None:
    """Run the manipulation executor until ROS shutdown or a keyboard interrupt."""
    rclpy.init(args=args)
    node = GraspExecutor()
    executor = MultiThreadedExecutor(num_threads=2)
    executor.add_node(node)
    try:
        executor.spin()
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        executor.shutdown()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
