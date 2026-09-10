#!/usr/bin/env python
# encoding: utf-8

# --- IMPORTING TOOLS ---
import sys
import select
import termios
import tty
import time

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from arm_msgs.msg import ArmJoint, ArmJoints

# --- PROFESSIONAL CONTROL PANEL MENU ---
msg = """
====================================
 TELEOPERATION (Mecanum & 6-DOF Arm)
====================================

 [ BASE MOTION ]
   i / ,       : Forward / Backward
   j / l       : Rotate Left / Right (in-place)
   a / d       : Strafe Left / Right (Mecanum)
   u / o / m /.: Diagonal Movements

 [ ARM MOTION (5 deg / press) ]
   1 / 2       : Joint 1 (Base)      Down / Up
   3 / 4       : Joint 2 (Shoulder)  Down / Up
   5 / 6       : Joint 3 (Elbow)      Down / Up
   7 / 8       : Joint 4 (Wrist)     Down / Up
   9 / 0       : Joint 5 (Wrist Rot) Down / Up
   g / h       : Joint 6 (Gripper)   Close / Open

 [ SYSTEM ]
   SPACE       : EMERGENCY STOP (Base + Arm)
   s           : PAUSE ALL CONTROLS (Press 's' again to resume)
   r           : Reset Arm to Home Position
   q / z       : Increase / Decrease overall speed by 10%
   w / x       : Increase / Decrease linear speed by 10%
   e / c       : Increase / Decrease angular speed by 10%
   CTRL + C    : Quit
============================================================
"""

# Maps keys to (forward_back, strafe_left_right, rotate_left_right)
moveBindings = {
    'i': (1, 0, 0),     'I': (1, 0, 0),
    ',': (-1, 0, 0),    'M': (-1, 0, 0),
    'a': (0, 1, 0),     'A': (0, 1, 0),
    'd': (0, -1, 0),    'D': (0, -1, 0),
    'j': (0, 0, 1),     'J': (0, 0, 1),
    'l': (0, 0, -1),    'L': (0, 0, -1),
    'u': (1, 1, 0),     'U': (1, 1, 0),
    'o': (1, -1, 0),    'O': (1, -1, 0),
    'm': (-1, 1, 0),     '.': (-1, -1, 0),
}

speedBindings = {
    'Q': (1.1, 1.1), 'Z': (.9, .9), 'W': (1.1, 1), 'X': (.9, 1),
    'E': (1, 1.1), 'C': (1, .9), 'q': (1.1, 1.1), 'z': (.9, .9),
    'w': (1.1, 1), 'x': (.9, 1), 'e': (1, 1.1), 'c': (1, .9),
}

class YahboomKeyboard(Node):
    def __init__(self, name):
        super().__init__(name)
        
        # Publishers
        self.pub_cmd_vel = self.create_publisher(Twist, 'cmd_vel', 1)
        self.pub_arm_single = self.create_publisher(ArmJoint, "arm_joint", 100)
        self.pub_arm_all = self.create_publisher(ArmJoints, "arm6_joints", 100)
        
        # Parameters (Safety Speed Limits)
        self.declare_parameter("linear_speed_limit", 1.0)
        self.declare_parameter("angular_speed_limit", 5.0)
        self.linear_speed_limit = self.get_parameter("linear_speed_limit").get_parameter_value().double_value
        self.angular_speed_limit = self.get_parameter("angular_speed_limit").get_parameter_value().double_value
        
        # State Trackers
        self.arm_joints = [90, 90, 0, 0, 90, 90]
        self.settings = termios.tcgetattr(sys.stdin)
        
        # Initialize arm to home position safely
        self.reset_arm()

    def getKey(self):
        tty.setraw(sys.stdin.fileno())
        rlist, _, _ = select.select([sys.stdin], [], [], 0.1)
        if rlist:
            key = sys.stdin.read(1)
        else:
            key = ''
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.settings)
        return key
        
    def vels(self, speed, turn):
        return f"Current Speed -> Linear: {speed:.2f} m/s | Angular: {turn:.2f} rad/s"
    
    def step_arm_joint(self, joint_id, delta):
        self.arm_joints[joint_id - 1] += delta
        
        # Safety limits to prevent breaking the arm
        if joint_id == 5:
            self.arm_joints[joint_id - 1] = max(0, min(270, self.arm_joints[joint_id - 1]))
        elif joint_id == 6:
            self.arm_joints[joint_id - 1] = max(30, min(180, self.arm_joints[joint_id - 1]))
        else:
            self.arm_joints[joint_id - 1] = max(0, min(180, self.arm_joints[joint_id - 1]))
            
        arm_msg = ArmJoint()
        arm_msg.id = joint_id
        arm_msg.joint = int(self.arm_joints[joint_id - 1])
        arm_msg.time = 500
        self.pub_arm_single.publish(arm_msg)
        
        action = "Opening" if delta > 0 else "Closing"
        if joint_id != 6:
            action = "Up" if delta > 0 else "Down"
        print(f"[ARM] Joint {joint_id} -> {action} -> {arm_msg.joint} deg")

    def reset_arm(self):
        self.arm_joints = [90, 90, 0, 0, 90, 90]
        arm_msg = ArmJoints()
        arm_msg.joint1 = self.arm_joints[0]
        arm_msg.joint2 = self.arm_joints[1]
        arm_msg.joint3 = self.arm_joints[2]
        arm_msg.joint4 = self.arm_joints[3]
        arm_msg.joint5 = self.arm_joints[4]
        arm_msg.joint6 = self.arm_joints[5]
        arm_msg.time = 2000
        self.pub_arm_all.publish(arm_msg)
        print("[SYSTEM] Arm reset to Home Position.")

    def emergency_stop(self):
        # 1. Stop Wheels
        self.pub_cmd_vel.publish(Twist())
        # 2. Stop Arm (Send current positions with 100ms time to force immediate braking)
        arm_msg = ArmJoints()
        arm_msg.joint1 = self.arm_joints[0]
        arm_msg.joint2 = self.arm_joints[1]
        arm_msg.joint3 = self.arm_joints[2]
        arm_msg.joint4 = self.arm_joints[3]
        arm_msg.joint5 = self.arm_joints[4]
        arm_msg.joint6 = self.arm_joints[5]
        arm_msg.time = 100
        self.pub_arm_all.publish(arm_msg)

def main():
    rclpy.init()
    robot_teleop = YahboomKeyboard("yahboom_keyboard_ctrl")
    
    speed, turn = 0.2, 1.0
    x, y, th = 0, 0, 0
    stop = False
    count = 0
    twist = Twist()
    
    try:
        print(msg)
        print(robot_teleop.vels(speed, turn))
        
        while True:
            key = robot_teleop.getKey()
            
            # Handle Pause/Resume
            if key in ("s", "S"):
                stop = not stop
                print(f"[SYSTEM] ALL CONTROLS PAUSED: {stop}")
                if stop:
                    robot_teleop.emergency_stop() # Lock everything immediately
                    x, y, th = 0, 0, 0

            # Handle Emergency Stop
            elif key == ' ':
                robot_teleop.emergency_stop()
                x, y, th = 0, 0, 0
                print("[SYSTEM] EMERGENCY STOP ENGAGED.")
                
            # If NOT paused, process movement
            elif not stop:
                if key in moveBindings.keys():
                    x, y, th = moveBindings[key]
                    count = 0	
                elif key in speedBindings.keys():
                    speed = speed * speedBindings[key][0]
                    turn = turn * speedBindings[key][1]
                    count = 0
                    speed = min(speed, robot_teleop.linear_speed_limit)
                    turn = min(turn, robot_teleop.angular_speed_limit)
                    print(robot_teleop.vels(speed, turn))
                    
                # Arm Controls
                elif key == '1': robot_teleop.step_arm_joint(1, -5)
                elif key == '2': robot_teleop.step_arm_joint(1, 5)
                elif key == '3': robot_teleop.step_arm_joint(2, -5)
                elif key == '4': robot_teleop.step_arm_joint(2, 5)
                elif key == '5': robot_teleop.step_arm_joint(3, -5)
                elif key == '6': robot_teleop.step_arm_joint(3, 5)
                elif key == '7': robot_teleop.step_arm_joint(4, -5)
                elif key == '8': robot_teleop.step_arm_joint(4, 5)
                elif key == '9': robot_teleop.step_arm_joint(5, -5)
                elif key == '0': robot_teleop.step_arm_joint(5, 5)
                
                # NEW Gripper Controls (g to close, h to open)
                elif key in ('g', 'G'): robot_teleop.step_arm_joint(6, -5)
                elif key in ('h', 'H'): robot_teleop.step_arm_joint(6, 5)
                
                elif key in ('r', 'R'): robot_teleop.reset_arm()
                else:
                    count = count + 1
                    if count > 4:
                        x, y, th = 0, 0, 0
                    if key == '\x03':  # Ctrl+C
                        break
            
            # If paused, ignore everything except Ctrl+C
            else:
                if key == '\x03':
                    break
                elif key != '':
                    print("[SYSTEM] System paused. Press 's' to resume.")
                
            # Calculate and publish base movement
            twist.linear.x = speed * x
            twist.linear.y = speed * y
            twist.angular.z = turn * th
            
            if not stop:
                robot_teleop.pub_cmd_vel.publish(twist)
            else:
                robot_teleop.pub_cmd_vel.publish(Twist())
            
    except Exception as e:
        print(f"[ERROR] {e}")
    finally:
        # Graceful shutdown: stop everything before exiting
        robot_teleop.emergency_stop()
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, robot_teleop.settings)
        robot_teleop.destroy_node()
        rclpy.shutdown()