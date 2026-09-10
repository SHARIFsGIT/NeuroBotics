#ros lib
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from sensor_msgs.msg import LaserScan
from std_msgs.msg import UInt16  # The message type used to turn the buzzer ON/OFF

#commom lib
import math
import numpy as np
import time
from time import sleep
from yahboom_M3Pro_laser.common import *  # Custom Yahboom tools (Bool message and SinglePID)
import os
print ("improt done")  # (Typo in original: means "import done")
RAD2DEG = 180 / math.pi  # Conversion factor: radians to degrees

class laserWarning(Node):
    def __init__(self,name):
        super().__init__(name)
        
        # --- CREATING SUBSCRIBERS (Listeners) ---
        # Listen to the 360-degree LiDAR scanner
        self.sub_laser = self.create_subscription(LaserScan,"/scan",self.registerScan,1)
        # Listen to the joystick (so you can pause the AI and drive manually)
        self.sub_JoyState = self.create_subscription(Bool,'/JoyState', self.JoyStateCallback,1)
        
        # --- CREATING PUBLISHERS (Radio Stations) ---
        # Tell the wheels to move
        self.pub_vel = self.create_publisher(Twist,'/cmd_vel',1)
        # Tell the buzzer to beep!
        self.pub_Buzzer = self.create_publisher(UInt16,'/beep',1)

        # --- ROS 2 PARAMETERS (Speed & Distance Limits) ---
        self.declare_parameter("linear",0.5)       # Max forward speed (not actually used in this script, but declared)
        self.linear = self.get_parameter('linear').get_parameter_value().double_value
        self.declare_parameter("angular",1.0)      # Max turning speed
        self.angular = self.get_parameter('angular').get_parameter_value().double_value
        self.declare_parameter("LaserAngle",45.0)  # Width of the front cone (45 degrees left and right)
        self.LaserAngle = self.get_parameter('LaserAngle').get_parameter_value().double_value
        self.declare_parameter("ResponseDist",0.55) # The "Danger Zone" distance (0.55 meters)
        self.ResponseDist = self.get_parameter('ResponseDist').get_parameter_value().double_value
        
        # --- STATE TRACKERS & PID CONTROLLER ---
        self.Joy_active = False
        # This PID controller controls the steering wheel to keep the closest object centered.
        # It is tuned a bit more aggressively than the tracker (3.0, 0.0, 5.0)
        self.ang_pid = SinglePID(3.0, 0.0, 5.0)

    def JoyStateCallback(self, msg):
        if not isinstance(msg, Bool): return
        self.Joy_active = msg.data  # If True, human is driving, AI should pause

    def registerScan(self, scan_data):
        if not isinstance(scan_data, LaserScan): return
        ranges = np.array(scan_data.ranges)  # Array of distances from the LiDAR
        
        # We will search for the absolute closest object in the front 90-degree cone
        minDistList = []    # A list to hold all the close distances
        minDistIDList = []  # A list to hold the angles of those close distances
        
        # Loop through every single laser beam
        for i in range(len(ranges)):
            # Calculate which direction (in degrees) this specific laser beam is pointing
            angle = (scan_data.angle_min + scan_data.angle_increment * i) * RAD2DEG
            
            # FRONT ZONE: If the beam is pointing forward (within +/- 45 degrees) and hits something valid
            if abs(angle) < self.LaserAngle and ranges[i] !=0.0 : 
                minDistList.append(ranges[i])     # Save the distance
                minDistIDList.append(angle)       # Save the angle
        
        # If nothing is in front of us, do nothing and wait
        if len(minDistList) == 0: return
        
        # Find the absolute closest distance out of all the beams
        minDist = min(minDistList)
        # Find out what angle that closest object is sitting at
        minDistID = minDistIDList[minDistList.index(minDist)]
        
        # If a human is driving, stop the AI and do nothing
        if self.Joy_active :
            self.pub_vel.publish(Twist())
            return

        print("minDist: ", minDist)   # Print how far away the object is
        
        # --- THE ALARM LOGIC ---
        # If the closest object is inside the Danger Zone (0.55m)...
        if minDist <= self.ResponseDist and minDist != 0.0:
            b = UInt16()
            b.data = 1               # 1 means BEEP!
            self.pub_Buzzer.publish(b)
        else:
            # If the object is outside the danger zone, turn the buzzer off (0).
            self.pub_Buzzer.publish(UInt16()) 

        # --- THE TRACKING LOGIC ---
        velocity = Twist()
        print("minDistID: ", minDistID)	
        
        # Calculate how much to turn to face the object.
        # Target Angle is 0 (straight ahead). Current Angle is minDistID.
        ang_pid_compute = self.ang_pid.pid_compute(abs(minDistID) / 72, 0)
        
        # If the object is to the left (positive angle), turn left
        if 0 < minDistID :
            velocity.angular.z = ang_pid_compute
        # If the object is to the right (negative angle), turn right
        elif minDistID < 0:
            velocity.angular.z = -ang_pid_compute
            
        print("orin_angular.z: ", velocity.angular.z)  # Original calculated turn speed
        
        # Deadzone: If the object is almost directly in front, don't turn.
        if abs(ang_pid_compute) < 0.5: velocity.angular.z = 0.0
        
        # Slow down the turning speed to 50% so the robot doesn't whip around too fast.
        velocity.angular.z = velocity.angular.z * 0.5
        
        print("angular.z: ", velocity.angular.z)  # Final turn speed
        
        # Send the movement command to the wheels!
        # Note: linear.x is never set here, so the robot stays perfectly still and just spins in place!
        self.pub_vel.publish(velocity)

    # --- SAFETY SHUTDOWN FUNCTION ---
    def exit_pro(self):
        # When you press Ctrl+C, this runs a terminal command in the background to force the robot to stop
        cmd1 = "ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist "
        cmd2 = '''"{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"'''
        cmd = cmd1 + cmd2
        os.system(cmd)

def main():
    rclpy.init()
    laser_warn = laserWarning("laser_Warnning_a1")
    print ("start it")
    try:
        rclpy.spin(laser_warn)
    except KeyboardInterrupt:
        pass
    finally:
        laser_warn.exit_pro()  # Force stop the wheels
        laser_warn.destroy_node()
        rclpy.shutdown()