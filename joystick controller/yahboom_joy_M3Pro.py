#!/usr/bin/env python
# encoding: utf-8

# --- IMPORTING TOOLS ---
import os
import time
import getpass  # Lets Python find out who is currently logged into the computer
import threading  # Lets Python do multiple things at the exact same time (like moving the arm while driving)
from time import sleep

# ROS 2 libraries and Message types
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist  # For moving the wheels
from sensor_msgs.msg import Joy  # The raw gamepad data
from actionlib_msgs.msg import GoalID  # For canceling AI navigation
from std_msgs.msg import Int32, Bool, UInt16, ColorRGBA  # Basic message types

# Custom messages for your specific robot arm
from arm_msgs.msg import ArmJoint
from arm_msgs.msg import ArmJoints


class JoyTeleop(Node):
    def __init__(self, name):
        super().__init__(name)  # Name this ROS 2 Node
        
        # --- STATE TRACKERS ---
        self.Joy_active = False  # Is the joystick currently allowed to drive the robot?
        self.arm_activa = False  # Is the joystick currently allowed to move the arm?
        self.Buzzer_active = 0  # Is the beeper on or off?
        self.RGBLight_index = 0  # What color is the LED light currently?
        self.cancel_time = time.time()  # A timer to prevent double-pressing buttons too fast
        self.user_name = getpass.getuser()  # Find out if we are running on the robot ("jetson") or a normal PC
        
        # Speed "Gears". Instead of 100% speed, you can drive at 1/3 or 1/2 speed for safety.
        self.linear_Gear = 1.0 / 3  # Start in 1st gear (slow)
        self.angular_Gear = 1.0 / 4  # Start in 1st gear (slow turning)

        self.loop_active = True
        self.gripper_active = True
        self.arm_joints = [90, 120, 10, 20, 90, 0]  # The starting "home" angles for the 6 arm joints
        self.arm_joint = ArmJoint()

        # --- CREATING PUBLISHERS (Radio Stations) ---
        self.pub_goal = self.create_publisher(GoalID, "move_base/cancel", 10)  # Tell the AI to stop navigating
        self.pub_cmdVel = self.create_publisher(Twist, "cmd_vel", 1)  # Tell the wheels to move
        self.pub_Buzzer = self.create_publisher(UInt16, "/beep", 1)  # Tell the robot to beep
        self.pub_JoyState = self.create_publisher(Bool, "JoyState", 10)  # Tell other programs if the joystick is active
        self.pub_RGBLight = self.create_publisher(ColorRGBA, "rgb", 10)  # Tell the LED lights what color to be
        self.pub_SingleTargetAngle = self.create_publisher(ArmJoint, "arm_joint", 100)  # Tell one arm joint to move
        self.TargetAngle_pub = self.create_publisher(ArmJoints, "arm6_joints", 100)  # Tell all 6 arm joints to move

        # --- CREATING SUBSCRIBERS (Listeners) ---
        # Listen to the 'joy' topic. Whenever a button is pressed, run the 'buttonCallback' function below.
        self.sub_Joy = self.create_subscription(Joy, "joy", self.buttonCallback, 10)

        # --- ROS 2 PARAMETERS (Safety Speed Limits) ---
        # These load settings from a config file so you can't accidentally make the robot go dangerously fast.
        self.declare_parameter("xspeed_limit", 1.0)
        self.declare_parameter("yspeed_limit", 1.0)
        self.declare_parameter("angular_speed_limit", 5.0)
        self.xspeed_limit = self.get_parameter("xspeed_limit").get_parameter_value().double_value
        self.yspeed_limit = self.get_parameter("yspeed_limit").get_parameter_value().double_value
        self.angular_speed_limit = self.get_parameter("angular_speed_limit").get_parameter_value().double_value
      
        # Move the arm to the home position, and wait until the arm is actually listening before continuing
        while not self.TargetAngle_pub.get_subscription_count():
            self.pubSix_Arm(self.arm_joints)
            time.sleep(1)	
        self.pubSix_Arm(self.arm_joints)

    # --- HELPER FUNCTION TO MOVE ALL 6 JOINTS ---
    def pubSix_Arm(self, joints, id=6, angle=180.0, runtime=2000):
        arm_joint = ArmJoints()
        arm_joint.joint1 = joints[0]
        arm_joint.joint2 = joints[1]
        arm_joint.joint3 = joints[2]
        arm_joint.joint4 = joints[3]
        arm_joint.joint5 = joints[4]
        arm_joint.joint6 = joints[5]
        arm_joint.time = runtime  # Take 2 seconds to reach this pose
        self.TargetAngle_pub.publish(arm_joint)

    # --- THE MAIN BUTTON ROUTER ---
    def buttonCallback(self, joy_data):
        if not isinstance(joy_data, Joy): return  # Safety check: ignore fake data
        
        # If we are running ON the robot itself, use the "jetson" button layout. 
        # If we are running on a laptop, use the "pc" button layout.
        if self.user_name == "jetson":
            self.user_jetson(joy_data)
        else:
            self.user_pc(joy_data)

    # --- ARM MOVEMENT THREADING ---
    def pub_armjoint(self, id, direction):
        self.loop_active = True
        # Start a separate "Thread". A thread is like a mini-program running in the background.
        # This allows you to hold a button down and the arm keeps moving until you let go!
        arm_thread = threading.Thread(target=self.arm_ctrl, args=(id, direction))
        arm_thread.setDaemon(True)  # Kills the thread automatically when the main program closes
        arm_thread.start()

    def arm_ctrl(self, id, direction):
        while 1:  # Loop forever
            if self.loop_active:
                self.arm_joints[id - 1] += direction  # Add or subtract 1 degree from the joint
                
                # Safety limits so the arm doesn't bend too far and break itself!
                if id == 5:
                    if self.arm_joints[id - 1] > 270: self.arm_joints[id - 1] = 270
                    elif self.arm_joints[id - 1] < 0: self.arm_joints[id - 1] = 0
                elif id == 6:
                    if self.arm_joints[id - 1] >= 180: self.arm_joints[id - 1] = 180
                    elif self.arm_joints[id - 1] <= 30: self.arm_joints[id - 1] = 30
                else:
                    if self.arm_joints[id - 1] > 180: self.arm_joints[id - 1] = 180
                    elif self.arm_joints[id - 1] < 0: self.arm_joints[id - 1] = 0
                    
                self.arm_joint.id = id
                self.arm_joint.joint = int(self.arm_joints[id - 1])
                self.arm_joint.time = 1000
                if self.arm_activa:
                    print("arm control")
                    self.pub_SingleTargetAngle.publish(self.arm_joint)
                sleep(0.5)  # Move 1 degree every 0.5 seconds
            else:
                break  # If loop_active becomes False, stop moving the arm
            
    # --- JETSON CONTROLLER MAPPING ---
    def user_jetson(self, joy_data):
        # Toggle the gripper open/closed
        if joy_data.buttons[10] == 1:
            self.gripper_active = not self.gripper_active
            
        # If all movement buttons are let go, stop the arm thread
        if (joy_data.buttons[0] == joy_data.buttons[1] == joy_data.buttons[6] == joy_data.buttons[3] == joy_data.buttons[4] == 0 
            and joy_data.axes[7] == joy_data.axes[6] == 0 and joy_data.axes[5] != -1):
            self.loop_active = False
        else:
            # Map specific buttons (A, B, X, Y, D-pad, L1, L2) to specific arm joints (1 through 6)
            if joy_data.buttons[3] == 1: self.pub_armjoint(1, -1)  # Button X moves Joint 1 down
            if joy_data.buttons[1] == 1: self.pub_armjoint(1, 1)   # Button B moves Joint 1 up
            if joy_data.buttons[0] == 1: self.pub_armjoint(2, -1)  # Button A moves Joint 2 down
            if joy_data.buttons[4] == 1: self.pub_armjoint(2, 1)   # Button Y moves Joint 2 up
            if joy_data.axes[6] != 0: self.pub_armjoint(3, -joy_data.axes[6])  # D-pad left/right moves Joint 3
            if joy_data.axes[7] != 0: self.pub_armjoint(4, joy_data.axes[7])   # D-pad up/down moves Joint 4
            if self.gripper_active:
                if joy_data.axes[5] == -1: self.pub_armjoint(6, -1) # L2 closes gripper
                if joy_data.buttons[6] == 1: self.pub_armjoint(6, 1) # L1 opens gripper
            else:
                if joy_data.axes[5] == -1: self.pub_armjoint(5, -1) # L2 moves Joint 5 down
                if joy_data.buttons[6] == 1: self.pub_armjoint(5, 1) # L1 moves Joint 5 up

        # Cancel AI Navigation
        if joy_data.buttons[9] == 1: self.cancel_nav()
        
        # Change RGB Light Color
        if joy_data.buttons[7] == 1:
            self.RGBLight_index = self.RGBLight_index + 1.0
            if self.RGBLight_index > 7: self.RGBLight_index = 0.0
            rgb__msg = ColorRGBA()
            rgb__msg.a = 100.0 + self.RGBLight_index
            self.pub_RGBLight.publish(rgb__msg)
            
        # Beep the Buzzer
        if joy_data.buttons[11] == 1:
            Buzzer_ctrl = UInt16()
            if self.Buzzer_active == 0: self.Buzzer_active = self.Buzzer_active + 1
            else: self.Buzzer_active = self.Buzzer_active - 1
            Buzzer_ctrl.data = self.Buzzer_active
            self.pub_Buzzer.publish(Buzzer_ctrl)
            
        # Shift Gears for Linear (forward/backward) speed
        if joy_data.buttons[13] == 1:
            if self.linear_Gear == 1.0: self.linear_Gear = 1.0 / 3
            elif self.linear_Gear == 1.0 / 3: self.linear_Gear = 2.0 / 3
            elif self.linear_Gear == 2.0 / 3: self.linear_Gear = 1
            
        # Shift Gears for Angular (spinning) speed
        if joy_data.buttons[14] == 1:
            if self.angular_Gear == 1.0: self.angular_Gear = 1.0 / 4
            elif self.angular_Gear == 1.0 / 4: self.angular_Gear = 1.0 / 2
            elif self.angular_Gear == 1.0 / 2: self.angular_Gear = 3.0 / 4
            elif self.angular_Gear == 3.0 / 4: self.angular_Gear = 1.0

        # Calculate actual wheel speed: (Joystick Position) * (Max Speed Limit) * (Current Gear)
        xlinear_speed = self.filter_data(joy_data.axes[1]) * self.xspeed_limit * self.linear_Gear
        ylinear_speed = self.filter_data(joy_data.axes[0]) * self.yspeed_limit * self.linear_Gear
        angular_speed = self.filter_data(joy_data.axes[2]) * self.angular_speed_limit * self.angular_Gear
        
        # Enforce hard speed limits (just in case!)
        if xlinear_speed > self.xspeed_limit: xlinear_speed = self.xspeed_limit
        elif xlinear_speed < -self.xspeed_limit: xlinear_speed = -self.xspeed_limit
        # ... (same for y and angular) ...

        # Package the speeds into a Twist message and send to the wheels
        twist = Twist()
        twist.linear.x = xlinear_speed
        twist.linear.y = ylinear_speed
        twist.angular.z = angular_speed
        if self.Joy_active == True:
            self.pub_cmdVel.publish(twist)

    # --- PC CONTROLLER MAPPING ---
    # This is almost identical to the Jetson mapping, but the button numbers are slightly different 
    # because a PC interprets the controller differently than the Jetson does.
    def user_pc(self, joy_data):
        # ... (Similar button mapping logic as above, but for PC) ...
        pass # Code omitted for brevity in the explanation, but it does the exact same thing!

    # --- DEADZONE FILTER ---
    def filter_data(self, value):
        # If the joystick is pushed less than 20% in any direction, treat it as 0.
        # This stops the robot from creeping forward when you just rest your hand on the stick!
        if abs(value) < 0.2:
            value = 0
        return value

    # --- TOGGLE JOYSTICK CONTROL ---
    def cancel_nav(self):
        now_time = time.time()
        # This prevents the button from triggering 100 times a second
        if now_time - self.cancel_time > 1:
            Joy_ctrl = Bool()
            self.Joy_active = not self.Joy_active  # Flip the switch (True becomes False, False becomes True)
            self.arm_activa = not self.arm_activa  # Flip arm control too
            Joy_ctrl.data = self.Joy_active
            for i in range(3):
                self.pub_JoyState.publish(Joy_ctrl)  # Tell the world joystick control is active!
                self.pub_cmdVel.publish(Twist())     # Send a STOP command to the wheels to be safe
            self.cancel_time = now_time


def main():
    rclpy.init()  # Turn on ROS 2
    joy_ctrl = JoyTeleop("joy_ctrl")  # Create our translator node
    rclpy.spin(joy_ctrl)  # Keep it running forever until you press Ctrl+C