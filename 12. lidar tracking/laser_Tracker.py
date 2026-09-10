#ros lib
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from sensor_msgs.msg import LaserScan

#commom lib
import math
import numpy as np
import time
from time import sleep
from yahboom_M3Pro_laser.common import *  # Custom Yahboom tools (like Bool message and SinglePID)
import os
print ("improt done")  # (Typo in original: means "import done")
RAD2DEG = 180 / math.pi  # Conversion factor: radians to degrees

class laserTracker(Node):
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
        
        # --- ROS 2 PARAMETERS (Speed & Distance Limits) ---
        self.declare_parameter("linear",0.5)       # Max forward speed (0.5 m/s)
        self.linear = self.get_parameter('linear').get_parameter_value().double_value
        self.declare_parameter("angular",1.0)      # Max turning speed (1.0 rad/s)
        self.angular = self.get_parameter('angular').get_parameter_value().double_value
        self.declare_parameter("LaserAngle",45.0)  # Width of the front cone (45 degrees left and right)
        self.LaserAngle = self.get_parameter('LaserAngle').get_parameter_value().double_value
        self.declare_parameter("ResponseDist",0.55) # The "Sweet Spot" distance to keep from the object (0.55 meters)
        self.ResponseDist = self.get_parameter('ResponseDist').get_parameter_value().double_value
        
        # --- STATE TRACKERS & PID CONTROLLERS ---
        self.Joy_active = False
        
        # PID controllers are math algorithms that help the robot move smoothly toward a target 
        # without overshooting or stuttering.
        # This one controls forward/backward speed to maintain the 0.55m distance.
        self.lin_pid = SinglePID(1.0, 0.0, 1.0)  # (Kp, Ki, Kd)
        # This one controls left/right turning to keep the object centered in the camera.
        self.ang_pid = SinglePID(2.0, 0.0, 2.0)
        

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
        
        # If we found at least one object in front of us...
        if len(minDistList) != 0:
            # Find the absolute closest distance out of all the beams
            minDist = min(minDistList)
            # Find out what angle that closest object is sitting at
            minDistID = minDistIDList[minDistList.index(minDist)]
        else:
            # If nothing is in front of us, do nothing and wait
            print("-----------------------")
            return

        # If a human is driving, stop the AI and do nothing
        if self.Joy_active :
            self.pub_vel.publish(Twist())
            return

        velocity = Twist()
        print("minDist: ", minDist)       # Print how far away the object is
        print("minDistID: ", minDistID)   # Print the angle of the object
        
        # Create a tiny deadzone: If we are already almost perfectly at 0.55m, pretend we are exactly at 0.55m 
        # so the motors don't jitter back and forth.
        if abs(minDist - self.ResponseDist) < 0.1: minDist = self.ResponseDist
        
        # LINEAR PID: Calculate how fast to drive forward.
        # We feed it our Target (0.55m) and our Current Distance (minDist).
        # The negative sign is because if we are too far away, the error is positive, 
        # but we need a positive forward speed to drive toward it.
        velocity.linear.x = -self.lin_pid.pid_compute(self.ResponseDist, minDist)
        
        # ANGULAR PID: Calculate how much to turn.
        # We feed it our Target Angle (0 degrees = straight ahead) and the Current Angle (minDistID).
        # Dividing by 72 just scales the angle down to a number the PID likes.
        ang_pid_compute = self.ang_pid.pid_compute(abs(minDistID) / 72, 0)
        
        # If the object is to the left (positive angle), turn left (positive angular z)
        if 0 < minDistID : 
            velocity.angular.z = ang_pid_compute
        # If the object is to the right (negative angle), turn right (negative angular z)
        elif minDistID < 0:
            velocity.angular.z = -ang_pid_compute
            
        # Deadzone for turning: If the object is almost directly in front, don't turn.
        if abs(ang_pid_compute) < 0.5: velocity.angular.z = 0.0
        
        # Slow down the turning speed to 60% so the robot doesn't whip around too fast.
        velocity.angular.z = velocity.angular.z * 0.6
        
        print("angular.z: ", velocity.angular.z)
        
        # Send the movement command to the wheels!
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
    laser_tracker = laserTracker("laser_Tracker_a1")
    print ("start it")
    try:
        rclpy.spin(laser_tracker)
    except KeyboardInterrupt:
        pass
    finally:
        laser_tracker.exit_pro()  # Force stop the wheels
        laser_tracker.destroy_node()
        rclpy.shutdown()