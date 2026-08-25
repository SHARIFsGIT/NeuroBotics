#!/usr/bin/env python3
"""Keyboard teleop for the Neurobotics Gazebo simulation.

Controls the diff-drive base plus the 5-DOF arm and gripper.
Key layout matches the real-robot Yahboom teleop.

Prerequisites:
  1. source install/setup.bash
  2. ros2 launch neurobotics gazebo.launch.py
Then run:
  ros2 run neurobotics teleop.py
"""

import sys
import select
import termios
import tty

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import Float64MultiArray

DEG = 57.29578  # radians -> degrees

# Joint limits in degrees (converted from the URDF, in radians)
ARM_LIMITS = [(-90, 90), (-90, 90), (-90, 90), (-90, 90), (-90, 180)]
GRIP_LIMITS = (-88, 0)

MSG = """
====================================
 NEUROBOTICS TELEOP (Diff + Arm)
====================================

 [ BASE MOTION ]
   i / ,      : Forward / Backward
   j / l      : Rotate Left / Right (in-place)
   u / o      : Arc forward-left / forward-right
   m / .      : Arc backward-left / backward-right
   k          : Stop base

 [ ARM MOTION (5 deg / press) ]
   1 / 2      : Joint 1 (Base)      Down / Up
   3 / 4      : Joint 2 (Shoulder)  Down / Up
   5 / 6      : Joint 3 (Elbow)     Down / Up
   7 / 8      : Joint 4 (Wrist)     Down / Up
   9 / 0      : Joint 5 (Rotate)    Down / Up
   g / h      : Gripper             Close / Open

 [ SYSTEM ]
   SPACE      : EMERGENCY STOP (base stops, arm holds position)
   s          : PAUSE / RESUME all controls
   r          : Reset arm to home (straight, 0 deg)
   q / z      : Increase / decrease overall speed by 10%
   w / x      : Increase / decrease linear speed by 10%
   e / c      : Increase / decrease angular speed by 10%
   CTRL+C     : Quit
=============================================================
 NOTE: a/d (strafe) needs mecanum wheels - not available in
       this diff-drive simulation.
=============================================================
"""

# key -> (linear, angular); arcs combine forward motion + rotation
MOVE = {
    'i': (1, 0),    ',': (-1, 0),
    'j': (0, 1),    'l': (0, -1),
    'u': (1, 1),    'o': (1, -1),
    'm': (-1, 1),   '.': (-1, -1),
    'k': (0, 0),
}

SPEED = {
    'q': (1.1, 1.1), 'z': (0.9, 0.9),
    'w': (1.1, 1.0), 'x': (0.9, 1.0),
    'e': (1.0, 1.1), 'c': (1.0, 0.9),
}


class Teleop(Node):
    def __init__(self):
        super().__init__('neurobotics_teleop')
        self.cmd_pub = self.create_publisher(Twist, '/diff_cont/cmd_vel_unstamped', 10)
        self.arm_pub = self.create_publisher(
            Float64MultiArray, '/arm_cont/commands', 10)

        self.declare_parameter('linear_speed_limit', 1.0)
        self.declare_parameter('angular_speed_limit', 2.0)
        self.lin_limit = self.get_parameter('linear_speed_limit').value
        self.ang_limit = self.get_parameter('angular_speed_limit').value

        self.arm_deg = [0.0] * 5      # home = straight (like RViz)
        self.grip_deg = 0.0
        self.settings = termios.tcgetattr(sys.stdin)

    def get_key(self):
        tty.setraw(sys.stdin.fileno())
        rlist, _, _ = select.select([sys.stdin], [], [], 0.1)
        key = sys.stdin.read(1) if rlist else ''
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.settings)
        return key

    # ---------- arm ----------
    def arm_msg(self):
        a = [d / DEG for d in self.arm_deg]
        g = self.grip_deg / DEG
        # The gripper fingers physically mimic rlink1_Joint with these signs
        # (Gazebo Classic ignores <mimic>, so we command every joint):
        # rlink2:+g  llink1:+g  llink2:-g  rlink3:-g  llink3:+g
        m = Float64MultiArray()
        m.data = a + [g, g, g, -g, -g, g]
        return m

    def step(self, idx, delta):
        if idx == 5:
            lo, hi = GRIP_LIMITS
            self.grip_deg = max(lo, min(hi, self.grip_deg + delta))
            print(f"[ARM] Gripper -> {self.grip_deg:.0f} deg")
        else:
            lo, hi = ARM_LIMITS[idx]
            self.arm_deg[idx] = max(lo, min(hi, self.arm_deg[idx] + delta))
            print(f"[ARM] Joint {idx+1} -> {self.arm_deg[idx]:.0f} deg")
        self.arm_pub.publish(self.arm_msg())

    def hold_arm(self):
        self.arm_pub.publish(self.arm_msg())

    def reset_arm(self):
        self.arm_deg = [0.0] * 5
        self.grip_deg = 0.0
        self.hold_arm()
        print("[SYSTEM] Arm reset to home (straight).")


def main():
    try:
        rclpy.init()
    except Exception as e:
        print(f"[ERROR] Could not start ROS 2: {e}")
        print("Hint: run 'source /opt/ros/humble/setup.bash' and "
              "'source install/setup.bash' first.")
        sys.exit(1)

    t = Teleop()

    speed, turn = 0.2, 1.0
    lin, ang = 0, 0
    paused = False
    count = 0
    twist = Twist()

    def vels():
        return f"Speed -> Linear: {speed:.2f} m/s | Angular: {turn:.2f} rad/s"

    try:
        print(MSG)
        print(vels())
        while True:
            key = t.get_key()

            if key == '\x03':                      # Ctrl+C
                break

            elif key in ('s', 'S'):                # pause / resume
                paused = not paused
                print(f"[SYSTEM] ALL CONTROLS PAUSED: {paused}")
                if paused:
                    lin = ang = 0

            elif key == ' ':                       # emergency stop
                lin = ang = 0
                t.cmd_pub.publish(Twist())
                t.hold_arm()
                print("[SYSTEM] EMERGENCY STOP ENGAGED.")

            elif not paused:
                if key in MOVE:
                    lin, ang = MOVE[key]
                    count = 0
                elif key in SPEED:
                    speed = min(speed * SPEED[key][0], t.lin_limit)
                    turn = min(turn * SPEED[key][1], t.ang_limit)
                    count = 0
                    print(vels())
                elif key in ('a', 'd', 'A', 'D'):
                    print("[SYSTEM] Strafe not supported in this diff-drive sim.")
                # arm joints (5 deg per press)
                elif key == '1': t.step(0, -5)
                elif key == '2': t.step(0, +5)
                elif key == '3': t.step(1, -5)
                elif key == '4': t.step(1, +5)
                elif key == '5': t.step(2, -5)
                elif key == '6': t.step(2, +5)
                elif key == '7': t.step(3, -5)
                elif key == '8': t.step(3, +5)
                elif key == '9': t.step(4, -5)
                elif key == '0': t.step(4, +5)
                elif key in ('g', 'G'): t.step(5, -5)
                elif key in ('h', 'H'): t.step(5, +5)
                elif key in ('r', 'R'): t.reset_arm()
                else:
                    count += 1
                    if count > 4:
                        lin = ang = 0

            # publish base command at ~10 Hz (also while paused -> stays stopped)
            twist.linear.x = speed * lin
            twist.angular.z = turn * ang
            if paused:
                twist.linear.x = 0.0
                twist.angular.z = 0.0
            t.cmd_pub.publish(twist)

    except Exception as e:
        print(f"[ERROR] {e}")
    finally:
        t.cmd_pub.publish(Twist())     # stop base
        t.hold_arm()                   # hold arm where it is
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, t.settings)
        t.destroy_node()
        rclpy.shutdown()
        print("\nTeleop stopped. Robot base halted.")


if __name__ == '__main__':
    main()
