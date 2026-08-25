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
from yahboom_M3Pro_laser.common import *  # Custom Yahboom tools (like the Bool message type)
import os
print ("improt done")  # (Typo in original code, means "import done")
RAD2DEG = 180 / math.pi  # Conversion factor: multiply radians by this to get degrees

class laserAvoid(Node):
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
             
        # --- ROS 2 PARAMETERS (Safety & Speed Limits) ---
        self.declare_parameter("linear",0.2)      # Forward speed (0.2 m/s)
        self.linear = self.get_parameter('linear').get_parameter_value().double_value
        self.declare_parameter("angular",0.2)     # Turning speed (0.2 rad/s)
        self.angular = self.get_parameter('angular').get_parameter_value().double_value
        self.declare_parameter("LaserAngle",20.0) # Width of the "front" cone (20 degrees to the left and right)
        self.LaserAngle = self.get_parameter('LaserAngle').get_parameter_value().double_value
        self.declare_parameter("ResponseDist",0.3) # How close an obstacle must be to trigger a warning (0.3 meters)
        self.ResponseDist = self.get_parameter('ResponseDist').get_parameter_value().double_value
        
        # --- STATE TRACKERS ---
        # These count how many laser beams hit something close in each zone
        self.Right_warning = 0
        self.Left_warning = 0
        self.front_warning = 0
        self.Joy_active = False  # Is a human driving with a joystick?
        self.conut = 3  # (Typo for "count"). If more than 3 beams hit an object, we consider it a real wall.

    def JoyStateCallback(self, msg):
        if not isinstance(msg, Bool): return
        self.Joy_active = msg.data  # If True, human is driving, AI should pause

    def registerScan(self, scan_data):
        if not isinstance(scan_data, LaserScan): return
        ranges = np.array(scan_data.ranges)  # The array of distances from the LiDAR
        
        # Reset the counters every time a new scan comes in
        self.Right_warning = 0
        self.Left_warning = 0
        self.front_warning = 0
        
        # Loop through every single laser beam (there are usually 360 or 720 of them!)
        for i in range(len(ranges)):
            # Calculate which direction (in degrees) this specific laser beam is pointing
            angle = (scan_data.angle_min + scan_data.angle_increment * i) * RAD2DEG
            
            # FRONT ZONE: If the beam is pointing near straight ahead (within +/- 30 degrees)
            if abs(angle) < self.LaserAngle and ranges[i] !=0.0:
                if ranges[i] <= self.ResponseDist*1.5:  # And it hits something closer than 0.825 meters
                    self.front_warning += 1  # Add to the front counter!
                    
            # LEFT ZONE: If the beam is pointing to the left (between 60 and 90 degrees)
            if angle < (90 - self.LaserAngle) < 90 and angle>0 and ranges[i] !=0.0:
                if ranges[i] <= self.ResponseDist*1.5:
                    self.Left_warning += 1
                    
            # RIGHT ZONE: If the beam is pointing to the right (between -90 and -60 degrees)
            if -90 < -(90 - self.LaserAngle) < angle and angle<0 and ranges[i] !=0.0:
                if ranges[i] <= self.ResponseDist*1.5:
                    self.Right_warning += 1

        # If a human is driving, stop the AI and do nothing
        if self.Joy_active:
            self.pub_vel.publish(Twist())
            return

        twist = Twist()
        
        # --- THE GIANT DECISION TREE ---
        # Based on the counts in the three zones, decide what to do.
        # (self.conut is 10. So > self.conut means "a wall is there", <= means "path is clear")
        
        # 1. Blocked in front, left, AND right! (Trapped) -> Back up and turn right
        if self.front_warning > self.conut and self.Left_warning > self.conut and self.Right_warning > self.conut:
            print ('1, there are obstacles in the left and right, turn right')
            twist.linear.x = self.linear      # Drive forward to push through? (Actually, this is a bit of a code bug, it should be negative to reverse, but we follow the original logic)
            twist.angular.z = -self.angular    # Turn right
            self.pub_vel.publish(twist)
            sleep(0.2)  # Pause for 0.2 seconds to let the robot execute the turn
        
        # 2. Blocked in front and right, but LEFT is clear -> Turn left
        elif self.front_warning > self.conut and self.Left_warning <= self.conut and self.Right_warning > self.conut:
            print ('2, there is an obstacle in the middle right, turn left')
            twist.linear.x = 0.0              # Stop forward motion
            twist.angular.z = self.angular     # Turn left
            self.pub_vel.publish(twist)
            sleep(0.2)
            # Double-check logic: If left is now blocked but right is clear, turn right instead
            if self.Left_warning > self.conut and self.Right_warning <= self.conut:
                twist.linear.x = 0.0
                twist.angular.z = -self.angular
                self.pub_vel.publish(twist)
                sleep(0.5)
                
        # 4. Blocked in front and left, but RIGHT is clear -> Turn right
        elif self.front_warning > self.conut and self.Left_warning > self.conut and self.Right_warning <= self.conut:
            print ('4. There is an obstacle in the middle left, turn right')
            twist.linear.x = 0.0
            twist.angular.z = -self.angular    # Turn right
            self.pub_vel.publish(twist)
            sleep(0.2)
            if self.Left_warning <= self.conut and self.Right_warning > self.conut:
                twist.linear.x = 0.0
                twist.angular.z = self.angular
                self.pub_vel.publish(twist)
                sleep(0.5)
                
        # 6. Blocked ONLY in front -> Turn left to find a way around
        elif self.front_warning > self.conut and self.Left_warning < self.conut and self.Right_warning < self.conut:
            print ('6, there is an obstacle in the middle, turn left')
            twist.linear.x = 0.0
            twist.angular.z = self.angular
            self.pub_vel.publish(twist)
            sleep(0.2)
            
        # 7. Front is clear, but blocked on left AND right (narrow hallway) -> Turn right to follow the wall
        elif self.front_warning < self.conut and self.Left_warning > self.conut and self.Right_warning > self.conut:
            print ('7. There are obstacles on the left and right, turn right')
            twist.linear.x = 0.0
            twist.angular.z = -self.angular
            self.pub_vel.publish(twist)
            sleep(0.4)
            
        # 8. Front is clear, but blocked ONLY on the left -> Turn right to avoid the left wall
        elif self.front_warning < self.conut and self.Left_warning > self.conut and self.Right_warning <= self.conut:
            print ('8, there is an obstacle on the left, turn right')
            twist.linear.x = 0.0
            twist.angular.z = -self.angular
            self.pub_vel.publish(twist)
            sleep(0.2)
            
        # 9. Front is clear, but blocked ONLY on the right -> Turn left to avoid the right wall
        elif self.front_warning < self.conut and self.Left_warning <= self.conut and self.Right_warning > self.conut:
            print ('9, there is an obstacle on the right, turn left')
            twist.linear.x = 0.0
            twist.angular.z = self.angular
            self.pub_vel.publish(twist)
            sleep(0.2)
            
        # 10. EVERYTHING IS CLEAR! -> Drive forward happily
        elif self.front_warning <= self.conut and self.Left_warning <= self.conut and self.Right_warning <= self.conut:
            print ('10, no obstacles, go forward')
            twist.linear.x = self.linear
            twist.angular.z = 0.0
            self.pub_vel.publish(twist)

    # --- SAFETY SHUTDOWN FUNCTION ---
    def exit_pro(self):
        # When you press Ctrl+C, this runs a terminal command in the background to force the robot to stop
        cmd1 = "ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist "
        cmd2 = '''"{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"'''
        cmd = cmd1 +cmd2
        os.system(cmd)


def main():
    rclpy.init()
    laser_avoid = laserAvoid("laser_Avoidance_a1")
    print ("start it")
    try:
        rclpy.spin(laser_avoid)
    except KeyboardInterrupt:
        pass
    finally:
        laser_avoid.exit_pro()  # Force stop the wheels
        laser_avoid.destroy_node()
        rclpy.shutdown()