#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
grasp_executor.py — E-AIRA manipulation layer.

Contract
--------
Subscribes ``/target_pose`` (``geometry_msgs/PoseStamped``, ``base_link``)
from ``vision_manager`` and closes the loop in two stages:

1. **Base alignment (PID).** Rotate until the target bearing ≈ 0, then drive
   to the pre-grasp standoff distance. Gains follow the proven deep-tracking
   tuning of folder 32, rescaled to SI units. ``cmd_vel`` is published only
   while aligning and is zeroed on every exit path.

2. **Arm grasp (existing kinematics).** The target is expressed in the arm
   base frame (via the live TF tree when available, otherwise via the
   calibrated static mount offset) and sent to the *unchanged* Yahboom
   kinematics service ``get_kinemarics`` (``arm_interface/srv/
   ArmKinemarics``), replicating the exact request/response handling of
   ``grasp_transport.py`` (folder 23): the 1.5 cm X pre-compensation, the
   1.396 rad (≈80°) grasp pitch, the ``180 − joint1`` base reflection, the
   joint-4 ≤ 90° clamp and the joint-5 wrap rules. Joint commands go out on
   ``arm6_joints`` / ``arm_joint``; completion on ``grasp_done`` (Bool).

Accepted requests on ``/eira/manipulation/request`` (String):
``grasp`` | ``release`` | ``home`` | ``stop``.

Topic map (all names audited from the existing workspace)
---------------------------------------------------------
  subscribe  /target_pose             geometry_msgs/PoseStamped
  subscribe  Curjoints                arm_interface/CurJoints
  subscribe  /eira/manipulation/request  std_msgs/String
  subscribe  /eira/vision/event       std_msgs/String (abort on "lost")
  publish    cmd_vel                  geometry_msgs/Twist
  publish    arm6_joints              arm_msgs/ArmJoints
  publish    arm_joint                arm_msgs/ArmJoint
  publish    grasp_done               std_msgs/Bool
  publish    /eira/manipulation/event std_msgs/String (JSON)
  publish    beep                     std_msgs/UInt16
  service    get_kinemarics           arm_interface/srv/ArmKinemarics
"""

import json
import math
import time

import rclpy
import tf2_ros
from rclpy.node import Node

from arm_interface.msg import CurJoints
from arm_interface.srv import ArmKinemarics
from arm_msgs.msg import ArmJoint, ArmJoints
from geometry_msgs.msg import PointStamped, PoseStamped, Twist
from std_msgs.msg import Bool, String, UInt16

from eira_manipulation.pid import PID


class GraspExecutor(Node):
    """PID base alignment + IK-driven grasping for the ROSMASTER M3 Pro."""

    # -- FSM states --
    IDLE = "IDLE"
    ALIGN = "ALIGN"            # PID: rotate + approach on /target_pose
    WAIT_IK = "WAIT_IK"        # IK service round-trip in flight
    WAIT_ARM = "WAIT_ARM"      # timed sequencer running arm steps

    def __init__(self):
        super().__init__("grasp_executor")

        # --------------------------------------------------------
        # PARAMETERS — every default traces to an audited course value
        # --------------------------------------------------------
        # Base alignment (SI rescale of the folder-32 PID tuning).
        self.declare_parameter("standoff_dist", 0.19)      # pre-grasp range
        self.declare_parameter("dist_tol", 0.03)
        self.declare_parameter("yaw_tol", 0.06)            # rad ≈ 3.4°
        self.declare_parameter("max_lin_vel", 0.15)
        self.declare_parameter("max_rev_vel", 0.08)
        self.declare_parameter("max_ang_vel", 1.2)
        self.declare_parameter("lin_kp", 0.5)
        self.declare_parameter("lin_ki", 0.0)
        self.declare_parameter("lin_kd", 0.1)
        self.declare_parameter("ang_kp", 1.2)
        self.declare_parameter("ang_ki", 0.0)
        self.declare_parameter("ang_kd", 0.05)
        self.declare_parameter("settle_ticks", 3)          # ticks inside tol
        self.declare_parameter("align_timeout_s", 45.0)
        self.declare_parameter("target_timeout_s", 0.8)    # stale /target_pose
        self.declare_parameter("control_hz", 20.0)

        # Arm / kinematics (folder-23 conventions).
        self.declare_parameter("arm_base_frame", "")       # TF name or ""
        self.declare_parameter("arm_mount_x", 0.0)         # arm origin in base
        self.declare_parameter("arm_mount_y", 0.0)
        self.declare_parameter("arm_mount_z", 0.0)
        self.declare_parameter("arm_mount_yaw", 0.0)
        self.declare_parameter("grasp_x_compensation", -0.015)
        self.declare_parameter("grasp_pitch", 1.3962614348313127)  # ≈ 80°
        self.declare_parameter("grasp_joint5", 90)
        self.declare_parameter("gripper_open", 90)
        self.declare_parameter("gripper_close", 30)
        self.declare_parameter("gripper_carry", 115)
        self.declare_parameter("arm_runtime_ms", 2000)

        # init_joints: user-defined default home pose (2026-11-13; was the
        # folder-23 verbatim [90,120,0,0,90,90]). transport_joints remains
        # verbatim from grasp_transport.py (folder 23).
        self._init_joints = [int(j) for j in self.declare_parameter(
            "init_joints", [90, 140, 20, 10, 90, 180]).value]
        self._transport_joints = [int(j) for j in self.declare_parameter(
            "transport_joints", [90, 150, 12, 20, 90, 120]).value]

        # --------------------------------------------------------
        # CONTROLLERS
        # --------------------------------------------------------
        self._lin_pid = PID(
            self.get_parameter("lin_kp").value,
            self.get_parameter("lin_ki").value,
            self.get_parameter("lin_kd").value,
            output_min=-self.get_parameter("max_rev_vel").value,
            output_max=self.get_parameter("max_lin_vel").value)
        self._ang_pid = PID(
            self.get_parameter("ang_kp").value,
            self.get_parameter("ang_ki").value,
            self.get_parameter("ang_kd").value,
            output_min=-self.get_parameter("max_ang_vel").value,
            output_max=self.get_parameter("max_ang_vel").value)

        self._tf_buffer = tf2_ros.Buffer()
        self._tf_listener = tf2_ros.TransformListener(
            self._tf_buffer, self, spin_thread=True)

        # --------------------------------------------------------
        # RUNTIME STATE
        # --------------------------------------------------------
        self._state = self.IDLE
        self._target = None            # latest PoseStamped (base_link)
        self._target_time = None       # wall clock of last /target_pose
        self._cur_joints = list(self._init_joints)
        self._steps = []               # timed sequencer queue
        self._step_wait_until = None
        self._settle_count = 0
        self._align_deadline = None
        self._last_tick = None

        # --------------------------------------------------------
        # SUBSCRIPTIONS
        # --------------------------------------------------------
        self.create_subscription(
            PoseStamped, "target_pose", self._on_target_pose, 10)
        self.create_subscription(
            CurJoints, "Curjoints", self._on_cur_joints, 10)
        self.create_subscription(
            String, "eira/manipulation/request", self._on_request, 10)
        self.create_subscription(
            String, "eira/vision/event", self._on_vision_event, 10)

        # --------------------------------------------------------
        # PUBLISHERS
        # --------------------------------------------------------
        self._cmd_pub = self.create_publisher(Twist, "cmd_vel", 1)
        self._six_pub = self.create_publisher(ArmJoints, "arm6_joints", 10)
        self._single_pub = self.create_publisher(ArmJoint, "arm_joint", 10)
        self._grasp_done_pub = self.create_publisher(Bool, "grasp_done", 1)
        self._event_pub = self.create_publisher(
            String, "eira/manipulation/event", 10)
        self._beep_pub = self.create_publisher(UInt16, "beep", 10)

        # --------------------------------------------------------
        # KINEMATICS SERVICE (existing arm_kin node "kin_ik_fk")
        # --------------------------------------------------------
        self._kin_client = self.create_client(ArmKinemarics, "get_kinemarics")

        # --------------------------------------------------------
        # CONTROL LOOP
        # --------------------------------------------------------
        period = 1.0 / float(self.get_parameter("control_hz").value)
        self.create_timer(period, self._tick)

        standoff = float(self.get_parameter("standoff_dist").value)
        self.get_logger().info(
            f"grasp_executor ready (standoff={standoff:.2f} m, "
            "waiting for requests)")

    # ========================================================
    # INPUT CALLBACKS
    # ========================================================

    def _on_target_pose(self, msg: PoseStamped):
        self._target = msg
        self._target_time = time.monotonic()

    def _on_cur_joints(self, msg: CurJoints):
        self._cur_joints = list(msg.joints)

    def _on_vision_event(self, msg: String):
        try:
            event = json.loads(msg.data)
        except json.JSONDecodeError:
            return
        # Vision gave up while we are aligning → abort cleanly, base stopped.
        if event.get("event") in ("lost", "timeout") and \
                self._state == self.ALIGN:
            self._fail("target lost during alignment")

    def _on_request(self, msg: String):
        request = msg.data.strip().lower()
        dispatch = {
            "grasp": self._start_grasp,
            "release": self._start_release,
            "home": self._start_home,
            "stop": self._stop,
        }
        handler = dispatch.get(request)
        if handler is None:
            self.get_logger().warning(f"unknown request: '{request}'")
            return
        handler()

    # ========================================================
    # REQUEST HANDLERS
    # ========================================================

    def _start_grasp(self):
        if self._state != self.IDLE:
            self._emit_event("failed", reason=f"busy ({self._state})")
            return
        if not self._kin_client.wait_for_service(timeout_sec=1.0):
            self._emit_event(
                "failed",
                reason="get_kinemarics service unavailable "
                       "(is arm_kin/kin_ik_fk running?)")
            return
        if self._target is None or self._target_stale():
            self._emit_event("failed", reason="no fresh /target_pose")
            return

        self._lin_pid.reset()
        self._ang_pid.reset()
        self._settle_count = 0
        self._align_deadline = time.monotonic() + \
            float(self.get_parameter("align_timeout_s").value)
        self._state = self.ALIGN
        self.get_logger().info("grasp: aligning base to target")

    def _start_release(self):
        if self._state != self.IDLE:
            self._emit_event("failed", reason=f"busy ({self._state})")
            return
        # transport pose → open gripper → home
        self._steps = [
            (lambda: self._pub_six(self._transport_joints), 2.5),
            (lambda: self._pub_single(6, int(
                self.get_parameter("gripper_open").value)), 1.5),
            (lambda: self._pub_six(self._init_joints), 2.0),
        ]
        self._begin_sequence("release")

    def _start_home(self):
        if self._state != self.IDLE:
            self._emit_event("failed", reason=f"busy ({self._state})")
            return
        self._steps = [(lambda: self._pub_six(self._init_joints), 2.5)]
        self._begin_sequence("home")

    def _stop(self):
        self._zero_cmd()
        self._state = self.IDLE
        self._steps = []
        self._step_wait_until = None
        self._emit_event("stopped")
        self.get_logger().warning("STOP requested — all motion halted")

    # ========================================================
    # 20 Hz CONTROL LOOP
    # ========================================================

    def _tick(self):
        now = time.monotonic()
        dt = 0.05 if self._last_tick is None else now - self._last_tick
        self._last_tick = now

        if self._state == self.ALIGN:
            self._tick_align(dt, now)
        elif self._state == self.WAIT_ARM:
            self._tick_sequence(now)

    # -- stage 1: base alignment --------------------------------

    def _tick_align(self, dt: float, now: float):
        if self._target_stale():
            self._fail("target pose stale — vision lost the object")
            return
        if now > self._align_deadline:
            self._fail("alignment timeout")
            return

        pose = self._target.pose.position
        distance = math.hypot(pose.x, pose.y)
        bearing = math.atan2(pose.y, pose.x)
        standoff = float(self.get_parameter("standoff_dist").value)
        dist_tol = float(self.get_parameter("dist_tol").value)
        yaw_tol = float(self.get_parameter("yaw_tol").value)

        # Pure rotation while far off-axis; combined servo afterwards
        # (same phase structure as the folder-32 follower).
        angular = self._ang_pid.update(bearing, dt)
        if abs(bearing) > 0.35:
            linear = 0.0
        else:
            linear = self._lin_pid.update(distance - standoff, dt)

        self._drive(linear, angular)

        settled = (abs(distance - standoff) < dist_tol
                   and abs(bearing) < yaw_tol)
        self._settle_count = self._settle_count + 1 if settled else 0
        if self._settle_count >= int(self.get_parameter("settle_ticks").value):
            self._zero_cmd()
            self.get_logger().info(
                f"aligned: dist={distance:.3f} m (standoff {standoff:.2f}), "
                f"bearing={math.degrees(bearing):.1f}°")
            self._begin_arm_grasp()

    # -- stage 2: arm grasp --------------------------------------

    def _begin_arm_grasp(self):
        """Express the target in the arm base frame and request IK."""
        target_arm = self._target_in_arm_frame()
        if target_arm is None:
            self._fail("could not resolve arm base frame")
            return

        request = ArmKinemarics.Request()
        request.kin_name = "ik"
        # Folder-23 pre-compensation on X and fixed grasp pitch.
        request.tar_x = target_arm[0] + \
            float(self.get_parameter("grasp_x_compensation").value)
        request.tar_y = target_arm[1]
        request.tar_z = target_arm[2]
        request.roll = 0.0
        request.pitch = float(self.get_parameter("grasp_pitch").value)
        request.yaw = 0.0

        future = self._kin_client.call_async(request)
        future.add_done_callback(self._on_ik_response)
        self._state = self.WAIT_IK           # sequencer idles until IK returns
        self._steps = []
        self._step_wait_until = None
        self.get_logger().info(
            "IK requested for arm-frame target "
            f"[{request.tar_x:.3f}, {request.tar_y:.3f}, {request.tar_z:.3f}]")

    def _on_ik_response(self, future):
        """Port of grasp_transport.py's get_ik_respone_callback (folder 23)."""
        # A stop/failure may have landed while the service was in flight.
        if self._state != self.WAIT_IK:
            self.get_logger().warning(
                f"IK response ignored (state={self._state})")
            return
        try:
            response = future.result()
        except Exception as exc:  # noqa: BLE001 — service transport error
            self._fail(f"IK service call failed: {exc}")
            return

        joints = [0, 0, 0, 0, 0, 0]
        joints[0] = 180 - int(response.joint1)        # base reflection rule
        joints[1] = int(response.joint2)
        joints[2] = int(response.joint3)
        joints[3] = min(int(response.joint4), 90)     # joint-4 ≤ 90° clamp

        # Joint-5 wrap rules, verbatim from the audited implementation.
        joint5 = int(self.get_parameter("grasp_joint5").value)
        if joint5 < 0:
            joints[4] = abs(joint5)
            if abs(joint5) < 90:
                joints[4] = 180 - joints[0] + joints[4] - 90
            else:
                joints[4] = joints[4] - joints[0] + 90
            if joints[4] > 135:
                joints[4] -= 90
            elif joints[4] < 45:
                joints[4] += 90
        elif joint5 > 0:
            joints[4] = 180 - abs(joint5)
            if joint5 < 90:
                joints[4] = joints[4] - joints[0]
            else:
                joints[4] = joints[4] - (joints[0] - 90)
            if joints[4] > 135:
                joints[4] -= 90
            elif joints[4] < 45:
                joints[4] += 90
        else:
            joints[4] = 90

        joints[5] = int(self.get_parameter("gripper_close").value)
        joints = [max(0, j) for j in joints]          # no negative angles

        self.get_logger().info(f"IK joints (folder-23 rules): {joints}")

        transport = list(self._transport_joints)
        transport[5] = int(self.get_parameter("gripper_carry").value)

        self._steps = [
            (lambda: self._pub_six(joints), 3.5),               # reach + close
            (lambda: self._pub_single(
                6, int(self.get_parameter("gripper_carry").value)), 2.0),
            (lambda: self._pub_six(transport), 2.5),            # lift & carry
            (self._announce_grasp_done, 0.0),
        ]
        self._state = self.WAIT_ARM

    # -- timed sequencer ------------------------------------------

    def _tick_sequence(self, now: float):
        if self._step_wait_until is not None and now < self._step_wait_until:
            return
        if not self._steps:
            self._state = self.IDLE
            return
        action, wait_s = self._steps.pop(0)
        action()
        self._step_wait_until = now + wait_s

    def _begin_sequence(self, name: str):
        self._state = self.WAIT_ARM
        final = {"release": "released", "home": "homed"}[name]
        self._steps.append((lambda: self._emit_event(final), 0.0))
        self.get_logger().info(f"executing {name} sequence")

    # ========================================================
    # FRAMES
    # ========================================================

    def _target_in_arm_frame(self):
        """base_link target → arm base frame.

        Preference order:
        1. live TF lookup of ``arm_base_frame`` (URDF-driven, exact);
        2. static mount offset parameters (calibrated x/y/z/yaw of the arm
           origin inside base_link) — the offline fallback.
        """
        pose = self._target.pose.position
        frame = self.get_parameter("arm_base_frame").value
        if frame:
            point = PointStamped()
            point.header.frame_id = "base_link"
            point.header.stamp = self._target.header.stamp
            point.point.x, point.point.y, point.point.z = \
                pose.x, pose.y, pose.z
            try:
                in_arm = self._tf_buffer.transform(
                    point, frame,
                    timeout=rclpy.duration.Duration(seconds=0.2))
                return (in_arm.point.x, in_arm.point.y, in_arm.point.z)
            except tf2_ros.TransformException as exc:
                self.get_logger().warning(
                    f"TF base_link → {frame} failed ({exc}); "
                    "using static mount offset")

        # Static fallback: p_arm = Rz(yaw)ᵀ · (p_base − t)
        tx = float(self.get_parameter("arm_mount_x").value)
        ty = float(self.get_parameter("arm_mount_y").value)
        tz = float(self.get_parameter("arm_mount_z").value)
        yaw = float(self.get_parameter("arm_mount_yaw").value)
        cos_y, sin_y = math.cos(-yaw), math.sin(-yaw)
        dx, dy, dz = pose.x - tx, pose.y - ty, pose.z - tz
        return (cos_y * dx - sin_y * dy,
                sin_y * dx + cos_y * dy,
                dz)

    def _target_stale(self) -> bool:
        if self._target_time is None:
            return True
        return (time.monotonic() - self._target_time) > \
            float(self.get_parameter("target_timeout_s").value)

    # ========================================================
    # ACTUATION HELPERS
    # ========================================================

    def _drive(self, linear: float, angular: float):
        twist = Twist()
        twist.linear.x = float(linear)
        twist.angular.z = float(angular)
        self._cmd_pub.publish(twist)

    def _zero_cmd(self):
        self._drive(0.0, 0.0)

    def _pub_six(self, joints, runtime_ms=None):
        """Six-joint command (arm_msgs/ArmJoints) — folder-23 helper."""
        runtime = int(runtime_ms or
                      self.get_parameter("arm_runtime_ms").value)
        message = ArmJoints()
        message.joint1 = int(joints[0])
        message.joint2 = int(joints[1])
        message.joint3 = int(joints[2])
        message.joint4 = int(joints[3])
        message.joint5 = int(joints[4])
        message.joint6 = int(joints[5])
        message.time = runtime
        self._six_pub.publish(message)
        self.get_logger().debug(f"arm6_joints: {joints} ({runtime} ms)")

    def _pub_single(self, joint_id: int, angle: int, runtime_ms=None):
        """Single-joint command (arm_msgs/ArmJoint) — folder-23 helper."""
        message = ArmJoint()
        message.id = int(joint_id)
        message.joint = int(angle)
        message.time = int(runtime_ms or
                           self.get_parameter("arm_runtime_ms").value)
        self._single_pub.publish(message)

    # ========================================================
    # EVENTS
    # ========================================================

    def _announce_grasp_done(self):
        done = Bool()
        done.data = True
        self._grasp_done_pub.publish(done)          # legacy ecosystem topic
        self._emit_event("grasped")
        self._beep(200)

    def _emit_event(self, event: str, **fields):
        message = String()
        payload = {"event": event, "wall_time": time.time()}
        payload.update(fields)
        message.data = json.dumps(payload)
        self._event_pub.publish(message)
        self.get_logger().info(f"event: {event} {fields if fields else ''}")

    def _fail(self, reason: str):
        self._zero_cmd()
        self._state = self.IDLE
        self._steps = []
        self._step_wait_until = None
        self._emit_event("failed", reason=reason)
        self.get_logger().error(f"grasp failed: {reason}")

    def _beep(self, duration_ms: int):
        beep = UInt16()
        beep.data = max(0, min(60000, int(duration_ms)))
        self._beep_pub.publish(beep)

    def destroy_node(self):
        # Safety net: never leave the base moving when the node dies.
        try:
            self._zero_cmd()
        except Exception:  # noqa: BLE001 — best effort during teardown
            pass
        super().destroy_node()


# ============================================================
# ENTRY POINT
# ============================================================


def main(args=None):
    rclpy.init(args=args)
    node = GraspExecutor()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
