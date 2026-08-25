#!/usr/bin/env python3
"""Linear velocity calibration for the Neurobotics simulation.

Same procedure as the real robot (github.com/SHARIFsGIT/NeuroBotics,
"05. linear velocity calibration"): command a straight-line distance,
measure how far the robot ACTUALLY travelled, and compute

    scale = commanded distance / measured distance

On the real robot the actual distance is measured with a tape measure on
the floor, and the scale is stored in the motor firmware with
config_robot.py -> set_ros_scale_line. In the simulation the "tape
measure" is Gazebo itself (the true position of the robot, read with
'gz model'); wheel odometry is ALSO reported for comparison.

A scale away from 1.00 in the simulation means wheel_radius in
config/my_controllers.yaml is wrong (the controller converts m/s into
wheel revolutions using that radius).

Prerequisites:
  1. source install/setup.bash
  2. ros2 launch neurobotics gazebo.launch.py
Then run:
  ros2 run neurobotics calib_linear.py

Give the robot ~3 m of clear space ahead. Keep the arm straight (HOME
pose). CTRL+C aborts and halts the robot.
"""

import math
import subprocess
import sys
import time

import rclpy
from rclpy.node import Node
from rclpy.signals import SignalHandlerOptions
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry

SPEED = 0.2         # m/s commanded forward speed during the test
TARGET = 1.0        # m commanded distance
TOLERANCE = 0.02    # pass if scale is within 2 % of 1.0
SETTLE = 2.0        # seconds to stand still after driving, before measuring


def true_position():
    """The 'tape measure': ask Gazebo where the robot really is.

    Returns (x, y) or None if the gz tool cannot be reached.
    """
    try:
        out = subprocess.run(['gz', 'model', '-m', 'neurobotics', '-p'],
                             capture_output=True, text=True, timeout=8)
        first = out.stdout.split('\n')[0].split()
        return float(first[0]), float(first[1])
    except Exception:
        return None


class CalibLinear(Node):
    def __init__(self):
        super().__init__('calib_linear')
        self.pub = self.create_publisher(Twist, '/diff_cont/cmd_vel_unstamped', 10)
        self.sub = self.create_subscription(
            Odometry, '/diff_cont/odom', self.on_odom, 10)
        self.odom_pos = None    # latest (x, y) from wheel odometry
        self.start_odom = None
        self.start_true = None

    def on_odom(self, msg):
        p = msg.pose.pose.position
        self.odom_pos = (p.x, p.y)

    def wait_for_odom(self):
        print("Waiting for /diff_cont/odom ...")
        t0 = time.time()
        while self.odom_pos is None:
            if time.time() - t0 > 10.0:
                return False
            self.pub.publish(Twist())     # zero speed = hold the robot still
            rclpy.spin_once(self, timeout_sec=0.1)
        return True

    def drive(self):
        print(f"Commanding {TARGET:.2f} m straight ahead at {SPEED} m/s ...")
        self.start_odom = self.odom_pos
        self.start_true = true_position()
        if self.start_true is None:
            print("[WARN] Could not read Gazebo ground truth "
                  "('gz model'). Reporting odometry only.")
        cmd = Twist()
        cmd.linear.x = SPEED
        # Stop when the wheels have SEEN one metre (the real robot does the
        # same - its firmware counts wheel revolutions for the distance).
        t0 = time.time()
        while True:
            dx = self.odom_pos[0] - self.start_odom[0]
            dy = self.odom_pos[1] - self.start_odom[1]
            if math.hypot(dx, dy) >= TARGET:
                break
            if time.time() - t0 > 60.0:
                print("[WARN] Timed out - measuring with what we have.")
                break
            self.pub.publish(cmd)
            rclpy.spin_once(self, timeout_sec=0.05)
        self.pub.publish(Twist())
        print("Distance reached - letting the robot settle ...")
        t0 = time.time()
        while time.time() - t0 < SETTLE:
            self.pub.publish(Twist())
            rclpy.spin_once(self, timeout_sec=0.05)

    def report(self):
        dx = self.odom_pos[0] - self.start_odom[0]
        dy = self.odom_pos[1] - self.start_odom[1]
        odom_m = math.hypot(dx, dy)
        print()
        print("================ LINEAR CALIBRATION RESULT ================")
        print(f"  Commanded distance : {TARGET:7.3f} m")
        print(f"  Odometry measured  : {odom_m:7.3f} m   (wheel revolutions)")
        scale = TARGET / odom_m
        if self.start_true is not None:
            end = true_position()
            if end is not None:
                true_m = math.hypot(end[0] - self.start_true[0],
                                    end[1] - self.start_true[1])
                print(f"  Tape measure (gz)  : {true_m:7.3f} m   "
                      "(Gazebo ground truth)")
                scale = TARGET / true_m
                print(f"  Linear scale       : {scale:7.3f}   "
                      "(commanded / tape measure)")
            else:
                print(f"  Linear scale       : {scale:7.3f}   (odometry only)")
        else:
            print(f"  Linear scale       : {scale:7.3f}   (odometry only)")
        if abs(scale - 1.0) <= TOLERANCE:
            print(f"  VERDICT: PASS - within {TOLERANCE*100:.0f} % of 1.0.")
            print( "      No correction needed.")
        else:
            print(f"  VERDICT: ADJUST - off by {(scale-1.0)*100:+.1f} %.")
            print( "      On the real robot you would now run config_robot.py")
            print( "      and store this with:  set_ros_scale_line")
            print( "      In the simulation check wheel_radius in")
            print( "      config/my_controllers.yaml instead - a value too")
            print( "      large makes every metre commanded travel less.")
        print("===========================================================")


def main():
    try:
        rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
    except Exception as e:
        print(f"[ERROR] Could not start ROS 2: {e}")
        print("Hint: run 'source /opt/ros/humble/setup.bash' and "
              "'source install/setup.bash' first.")
        sys.exit(1)

    node = CalibLinear()
    print("Linear velocity calibration (one commanded 1 m straight line).")
    try:
        if not node.wait_for_odom():
            print("[ERROR] No /diff_cont/odom data after 10 s.")
            print("Is the simulation running? (ros2 launch neurobotics "
                  "gazebo.launch.py)")
            raise KeyboardInterrupt
        node.drive()
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
