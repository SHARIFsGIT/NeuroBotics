#!/usr/bin/env python3
"""Angular velocity calibration for the Neurobotics simulation.

Same procedure as the real robot (github.com/SHARIFsGIT/NeuroBotics,
"04. angular velocity calibration"): command one full rotation at a fixed
angular speed, measure how far the robot ACTUALLY turned, and compute

    scale = commanded angle / measured angle

A scale of 1.00 means the robot turns exactly what it is told. On the real
robot the number is then written into the motor firmware with
config_robot.py -> set_ros_scale_angular (yours came out as 1.05). The
simulation has no firmware - its "translation table" is the diff-drive
controller config - so a scale away from 1.00 here means a wrong
wheel_separation or wheel_radius in config/my_controllers.yaml.

The rotation is measured from the IMU (/imu), which is trustworthy even
when the body rotates through tyre scrub. Wheel odometry
(/diff_cont/odom) is ALSO reported so you can see how much it disagrees -
wheel counters cannot see skidding (a pivot makes all four wheels skid),
exactly why the real robot fuses its IMU with an EKF.

Prerequisites:
  1. source install/setup.bash
  2. ros2 launch neurobotics gazebo.launch.py
Then run:
  ros2 run neurobotics calib_angular.py

Keep the arm straight (HOME pose) while this runs. CTRL+C aborts and
halts the robot.
"""

import math
import sys

import rclpy
from rclpy.node import Node
from rclpy.signals import SignalHandlerOptions
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from sensor_msgs.msg import Imu

SPEED = 0.5          # rad/s commanded angular speed during the test
TARGET = 2.0 * math.pi   # one full rotation (360 deg)
TOLERANCE = 0.02     # pass if scale is within 2 % of 1.0
SETTLE = 2.0         # seconds to stand still after turning, before measuring


def yaw_of(q):
    """Yaw angle (rad) of a quaternion - roll/pitch are ~0 on flat floor."""
    return math.atan2(2.0 * (q.w * q.z + q.x * q.y),
                      1.0 - 2.0 * (q.y * q.y + q.z * q.z))


def wrap(a):
    """Wrap an angle difference to +-pi (so 359 deg -> -1 deg, not 359)."""
    return math.atan2(math.sin(a), math.cos(a))


class CalibAngular(Node):
    def __init__(self):
        super().__init__('calib_angular')
        self.pub = self.create_publisher(Twist, '/diff_cont/cmd_vel_unstamped', 10)
        self.sub_odom = self.create_subscription(
            Odometry, '/diff_cont/odom', self.on_odom, 10)
        self.sub_imu = self.create_subscription(Imu, '/imu', self.on_imu, 10)
        self.imu_yaw = None      # latest yaw, or None until the IMU speaks
        self.odom_yaw = None
        # Unwrapped accumulators: yaw jumps from +pi to -pi mid-turn, so we
        # add up the small step-by-step changes instead of subtracting raw
        # angles (the same trick real IMU code uses).
        self.imu_total = 0.0
        self.odom_total = 0.0
        self.last_imu = None
        self.last_odom = None
        self.odom_start = None
        self.imu_start = None

    def on_imu(self, msg):
        y = yaw_of(msg.orientation)
        if self.last_imu is not None:
            self.imu_total += wrap(y - self.last_imu)
        self.last_imu = y
        self.imu_yaw = y

    def on_odom(self, msg):
        y = yaw_of(msg.pose.pose.orientation)
        if self.last_odom is not None:
            self.odom_total += wrap(y - self.last_odom)
        self.last_odom = y
        self.odom_yaw = y

    def wait_for_sensors(self):
        import time
        print("Waiting for /imu and /diff_cont/odom ...")
        t0 = time.time()
        while (self.imu_yaw is None or self.odom_yaw is None):
            if time.time() - t0 > 10.0:
                return False
            self.pub.publish(Twist())     # zero speed = hold the robot still
            rclpy.spin_once(self, timeout_sec=0.1)
        return True

    def spin_robot(self, seconds_max):
        import time
        print(f"Commanding one full turn: {TARGET:.2f} rad "
              f"({math.degrees(TARGET):.0f} deg) at {SPEED} rad/s ...")
        self.imu_start = self.imu_total
        self.odom_start = self.odom_total
        cmd = Twist()
        cmd.angular.z = SPEED
        t0 = time.time()
        # Stop when the IMU has SEEN a full turn (not after a fixed time) -
        # the same way you would watch the robot on the floor.
        while self.imu_total - self.imu_start < TARGET:
            if time.time() - t0 > seconds_max:
                break
            self.pub.publish(cmd)
            rclpy.spin_once(self, timeout_sec=0.05)
        self.pub.publish(Twist())
        print("Turn command finished - letting the robot settle ...")
        t0 = time.time()
        while time.time() - t0 < SETTLE:
            self.pub.publish(Twist())
            rclpy.spin_once(self, timeout_sec=0.05)

    def report(self):
        imu_deg = math.degrees(self.imu_total - self.imu_start)
        odom_deg = math.degrees(self.odom_total - self.odom_start)
        print()
        print("================ ANGULAR CALIBRATION RESULT ================")
        print(f"  Commanded rotation : {math.degrees(TARGET):7.1f} deg")
        print(f"  IMU measured       : {imu_deg:7.1f} deg   (ground truth)")
        print(f"  Odometry measured  : {odom_deg:7.1f} deg   (what the")
        print( "      wheels alone believe - they cannot see tyre slip,")
        print( "      and a pivot makes all four wheels skid, so the")
        print( "      two numbers drift apart; the real robot fixes")
        print( "      this with an EKF fusing its IMU)")
        scale = TARGET / (self.imu_total - self.imu_start)
        print(f"  Angular scale      : {scale:7.3f}   "
              f"(commanded / IMU measured)")
        if abs(scale - 1.0) <= TOLERANCE:
            print(f"  VERDICT: PASS - within {TOLERANCE*100:.0f} % of 1.0.")
            print( "      No correction needed.")
        else:
            print(f"  VERDICT: ADJUST - off by {(scale-1.0)*100:+.1f} %.")
            print( "      On the real robot you would now run config_robot.py")
            print( "      and store this with:  set_ros_scale_angular")
            print(f"      In the simulation check wheel_separation in")
            print( "      config/my_controllers.yaml instead - a value too")
            print( "      large makes the wheels under-steer every turn.")
        print("=============================================================")


def main():
    try:
        rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
    except Exception as e:
        print(f"[ERROR] Could not start ROS 2: {e}")
        print("Hint: run 'source /opt/ros/humble/setup.bash' and "
              "'source install/setup.bash' first.")
        sys.exit(1)

    node = CalibAngular()
    print("Angular velocity calibration (one commanded 360 deg turn).")
    try:
        if not node.wait_for_sensors():
            print("[ERROR] No /imu or /diff_cont/odom data after 10 s.")
            print("Is the simulation running? (ros2 launch neurobotics "
                  "gazebo.launch.py)")
            raise KeyboardInterrupt
        node.spin_robot(seconds_max=30.0)
        node.report()
    except KeyboardInterrupt:
        print("\nCalibration interrupted.")
    finally:
        try:
            node.pub.publish(Twist())     # make sure the robot stands still
        except Exception:
            pass
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
        print("Robot halted. Calibration done.")


if __name__ == '__main__':
    main()
