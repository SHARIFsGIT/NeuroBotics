#!/usr/bin/env python
# encoding: utf-8

# --- IMPORTING TOOLS ---
import os
import time
import getpass
import threading
from time import sleep

# ROS 2 libraries and Message types
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from sensor_msgs.msg import Joy
from actionlib_msgs.msg import GoalID
from std_msgs.msg import Int32, Bool, UInt16, ColorRGBA

# Custom messages for your specific robot arm
from arm_msgs.msg import ArmJoint
from arm_msgs.msg import ArmJoints


class JoyTeleop(Node):
    def __init__(self, name):
        super().__init__(name)
        
        # Print a beautiful startup banner
        print("\n" + "="*50)
        print("   YAHBOOM JOYSTICK TELEOPERATION SYSTEM")
        print("="*50)
        print(" [*] Initializing Node...")
        
        # --- STATE TRACKERS ---
        self.Joy_active = False  
        self.arm_activa = False  
        self.Buzzer_active = 0  
        self.RGBLight_index = 0  
        self.cancel_time = time.time()  
        self.user_name = getpass.getuser()  
        
        # Speed "Gears" for safety
        self.linear_Gear = 1.0 / 3  
        self.angular_Gear = 1.0 / 4  

        self.loop_active = True
        self.gripper_active = True
        self.arm_joints = [90, 120, 10, 20, 90, 0]  # Home angles
        self.arm_joint = ArmJoint()

        # --- CREATING PUBLISHERS ---
        self.pub_goal = self.create_publisher(GoalID, "move_base/cancel", 10)
        self.pub_cmdVel = self.create_publisher(Twist, "cmd_vel", 1)
        self.pub_Buzzer = self.create_publisher(UInt16, "/beep", 1)
        self.pub_JoyState = self.create_publisher(Bool, "JoyState", 10)
        self.pub_RGBLight = self.create_publisher(ColorRGBA, "rgb", 10)
        self.pub_SingleTargetAngle = self.create_publisher(ArmJoint, "arm_joint", 100)
        self.TargetAngle_pub = self.create_publisher(ArmJoints, "arm6_joints", 100)

        # --- CREATING SUBSCRIBERS ---
        self.sub_Joy = self.create_subscription(Joy, "joy", self.buttonCallback, 10)

        # --- ROS 2 PARAMETERS (Safety Speed Limits) ---
        self.declare_parameter("xspeed_limit", 1.0)
        self.declare_parameter("yspeed_limit", 1.0)
        self.declare_parameter("angular_speed_limit", 5.0)
        self.xspeed_limit = self.get_parameter("xspeed_limit").get_parameter_value().double_value
        self.yspeed_limit = self.get_parameter("yspeed_limit").get_parameter_value().double_value
        self.angular_speed_limit = self.get_parameter("angular_speed_limit").get_parameter_value().double_value
      
        print(" [INFO] Waiting for Arm Controller to connect...")
        # Move the arm to the home position, and wait until the arm is actually listening
        while not self.TargetAngle_pub.get_subscription_count():
            self.pubSix_Arm(self.arm_joints)
            time.sleep(1)	
        self.pubSix_Arm(self.arm_joints)
        
        print(" [INFO] System Ready! Press 'Share/Options' button to unlock control.")
        print("-" * 50)

    # --- HELPER FUNCTION TO MOVE ALL 6 JOINTS ---
    def pubSix_Arm(self, joints, id=6, angle=180.0, runtime=2000):
        arm_joint = ArmJoints()
        arm_joint.joint1 = joints[0]
        arm_joint.joint2 = joints[1]
        arm_joint.joint3 = joints[2]
        arm_joint.joint4 = joints[3]
        arm_joint.joint5 = joints[4]
        arm_joint.joint6 = joints[5]
        arm_joint.time = runtime
        self.TargetAngle_pub.publish(arm_joint)

    # --- THE MAIN BUTTON ROUTER ---
    def buttonCallback(self, joy_data):
        if not isinstance(joy_data, Joy): return
        
        if self.user_name == "jetson":
            self.user_jetson(joy_data)
        else:
            self.user_pc(joy_data)

    # --- ARM MOVEMENT THREADING ---
    def pub_armjoint(self, id, direction):
        self.loop_active = True
        arm_thread = threading.Thread(target=self.arm_ctrl, args=(id, direction))
        arm_thread.setDaemon(True)
        arm_thread.start()

    def arm_ctrl(self, id, direction):
        while 1:
            if self.loop_active:
                self.arm_joints[id - 1] += direction
                
                # Safety limits so the arm doesn't bend too far and break itself
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
                    # NEW BEAUTIFUL PRINT: Shows exactly which joint is moving and its current angle
                    action = "UP" if direction > 0 else "DOWN"
                    print(f" [ARM] Moving Joint {id} {action} -> Angle: {int(self.arm_joints[id - 1])} deg")
                    self.pub_SingleTargetAngle.publish(self.arm_joint)
                sleep(0.5)
            else:
                break
            
    # --- JETSON CONTROLLER MAPPING ---
    def user_jetson(self, joy_data):
        # Toggle the gripper open/closed mode
        if joy_data.buttons[10] == 1:
            self.gripper_active = not self.gripper_active
            state = "Gripper Mode" if self.gripper_active else "Joint 5 Mode"
            print(f" [BTN] Toggled L1/L2 -> {state}")
            
        # If all movement buttons are let go, stop the arm thread
        if (joy_data.buttons[0] == joy_data.buttons[1] == joy_data.buttons[6] == joy_data.buttons[3] == joy_data.buttons[4] == 0 
            and joy_data.axes[7] == joy_data.axes[6] == 0 and joy_data.axes[5] != -1):
            self.loop_active = False
        else:
            # Map specific buttons to arm joints
            if joy_data.buttons[3] == 1: self.pub_armjoint(1, -1)
            if joy_data.buttons[1] == 1: self.pub_armjoint(1, 1)
            if joy_data.buttons[0] == 1: self.pub_armjoint(2, -1)
            if joy_data.buttons[4] == 1: self.pub_armjoint(2, 1)
            if joy_data.axes[6] != 0: self.pub_armjoint(3, -joy_data.axes[6])
            if joy_data.axes[7] != 0: self.pub_armjoint(4, joy_data.axes[7])
            if self.gripper_active:
                if joy_data.axes[5] == -1: self.pub_armjoint(6, -1)
                if joy_data.buttons[6] == 1: self.pub_armjoint(6, 1)
            else:
                if joy_data.axes[5] == -1: self.pub_armjoint(5, -1)
                if joy_data.buttons[6] == 1: self.pub_armjoint(5, 1)

        # Cancel AI Navigation / Toggle Control
        if joy_data.buttons[9] == 1: self.cancel_nav()
        
        # Change RGB Light Color
        if joy_data.buttons[7] == 1:
            self.RGBLight_index = self.RGBLight_index + 1.0
            if self.RGBLight_index > 7: self.RGBLight_index = 0.0
            rgb__msg = ColorRGBA()
            rgb__msg.a = 100.0 + self.RGBLight_index
            self.pub_RGBLight.publish(rgb__msg)
            print(f" [LED] Changed RGB Light Color (Index: {int(self.RGBLight_index)})")
            
        # Beep the Buzzer
        if joy_data.buttons[11] == 1:
            Buzzer_ctrl = UInt16()
            if self.Buzzer_active == 0: self.Buzzer_active = self.Buzzer_active + 1
            else: self.Buzzer_active = self.Buzzer_active - 1
            Buzzer_ctrl.data = self.Buzzer_active
            self.pub_Buzzer.publish(Buzzer_ctrl)
            print(f" [BUZZER] Beep! State: {self.Buzzer_active}")
            
        # Shift Gears for Linear (forward/backward) speed
        if joy_data.buttons[13] == 1:
            if self.linear_Gear == 1.0: self.linear_Gear = 1.0 / 3
            elif self.linear_Gear == 1.0 / 3: self.linear_Gear = 2.0 / 3
            elif self.linear_Gear == 2.0 / 3: self.linear_Gear = 1
            print(f" [SPEED] Linear Gear shifted to: {int(self.linear_Gear * 100)}%")
            
        # Shift Gears for Angular (spinning) speed
        if joy_data.buttons[14] == 1:
            if self.angular_Gear == 1.0: self.angular_Gear = 1.0 / 4
            elif self.angular_Gear == 1.0 / 4: self.angular_Gear = 1.0 / 2
            elif self.angular_Gear == 1.0 / 2: self.angular_Gear = 3.0 / 4
            elif self.angular_Gear == 3.0 / 4: self.angular_Gear = 1.0
            print(f" [SPEED] Angular Gear shifted to: {int(self.angular_Gear * 100)}%")

        # Calculate actual wheel speed
        xlinear_speed = self.filter_data(joy_data.axes[1]) * self.xspeed_limit * self.linear_Gear
        ylinear_speed = self.filter_data(joy_data.axes[0]) * self.yspeed_limit * self.linear_Gear
        angular_speed = self.filter_data(joy_data.axes[2]) * self.angular_speed_limit * self.angular_Gear
        
        # Enforce hard speed limits
        if xlinear_speed > self.xspeed_limit: xlinear_speed = self.xspeed_limit
        elif xlinear_speed < -self.xspeed_limit: xlinear_speed = -self.xspeed_limit
        if ylinear_speed > self.yspeed_limit: ylinear_speed = self.yspeed_limit
        elif ylinear_speed < -self.yspeed_limit: ylinear_speed = -self.yspeed_limit
        if angular_speed > self.angular_speed_limit: angular_speed = self.angular_speed_limit
        elif angular_speed < -self.angular_speed_limit: angular_speed = -self.angular_speed_limit

        # Package the speeds into a Twist message and send to the wheels
        twist = Twist()
        twist.linear.x = xlinear_speed
        twist.linear.y = ylinear_speed
        twist.angular.z = angular_speed
        if self.Joy_active == True:
            self.pub_cmdVel.publish(twist)

    # --- PC CONTROLLER MAPPING ---
    def user_pc(self, joy_data):
        # Similar logic to above, omitted for brevity but kept for structure
        pass

    # --- DEADZONE FILTER ---
    def filter_data(self, value):
        # Prevents robot from creeping when your hand just rests on the stick
        if abs(value) < 0.2:
            value = 0
        return value

    # --- TOGGLE JOYSTICK CONTROL ---
    def cancel_nav(self):
        now_time = time.time()
        # Prevents the button from triggering 100 times a second
        if now_time - self.cancel_time > 1:
            Joy_ctrl = Bool()
            self.Joy_active = not self.Joy_active
            self.arm_activa = not self.arm_activa
            Joy_ctrl.data = self.Joy_active
            
            # NEW BEAUTIFUL PRINT: Clearly tells the user if control is unlocked
            if self.Joy_active:
                print("\n [SYSTEM] >>> CONTROL UNLOCKED! (Wheels + Arm Active) <<<")
            else:
                print("\n [SYSTEM] >>> CONTROL LOCKED. (Paused) <<<")
                
            for i in range(3):
                self.pub_JoyState.publish(Joy_ctrl)
                self.pub_cmdVel.publish(Twist())
            self.cancel_time = now_time


def main():
    rclpy.init()
    joy_ctrl = JoyTeleop("joy_ctrl")
    try:
        rclpy.spin(joy_ctrl)
    except KeyboardInterrupt:
        print("\n [SYSTEM] Shutting down joystick controller...")
    finally:
        joy_ctrl.destroy_node()
        rclpy.shutdown()