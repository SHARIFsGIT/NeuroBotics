#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# --- IMPORTING TOOLS ---
import cv2  # OpenCV: The main library for computer vision (looking at camera images)
import os
import numpy as np  # Math tool for handling arrays and matrices (grids of numbers)
from sensor_msgs.msg import Image  # ROS 2 message type for camera pictures
import message_filters  # Tool to sync two camera feeds (color and depth) so they happen at the exact same millisecond
from M3Pro_demo.vutils import draw_tags  # Custom tool to draw boxes around AprilTags on the screen
from M3Pro_demo.compute_joint5 import *  # Custom math for the arm
from dt_apriltags import Detector  # The actual AprilTag detection engine
from cv_bridge import CvBridge  # Translates ROS image messages into OpenCV images Python can understand
import cv2 as cv
from arm_interface.srv import ArmKinemarics  # The ROS 2 "Service" to ask the arm's brain to do math
from arm_interface.msg import AprilTagInfo,CurJoints  # Custom message types for your robot
from arm_msgs.msg import ArmJoints
from std_msgs.msg import Float32,Bool,Int16
encoding = ['16UC1', '32FC1']  # Formats for depth image data
import time
import transforms3d as tfs  # Advanced math library for 3D transformations (moving things in 3D space)
import tf_transformations as tf  # More 3D math (quaternions and rotations)
import yaml  # Lets Python read and write YAML config files
import math
from M3Pro_demo.Robot_Move import *  # Custom movement tools
from rclpy.node import Node  # The ROS 2 Node blueprint
import rclpy
from message_filters import Subscriber, TimeSynchronizer, ApproximateTimeSynchronizer  # Syncs camera feeds
from sensor_msgs.msg import Image
from geometry_msgs.msg import Twist  # Message type for moving the robot base


# --- READING THE CALIBRATION OFFSET FILE ---
# This loads a settings file. It contains little tweaks (offsets) to fix minor inaccuracies in the camera's math.
offset_file = "/home/jetson/yahboomcar_ws/src/arm_kin/param/offset_value.yaml"
with open(offset_file, 'r') as file:
    offset_config = yaml.safe_load(file)
print(offset_config)
print("----------------------------")
print("x_offset: ",offset_config.get('x_offset'))
print("y_offset: ",offset_config.get('y_offset'))
print("z_offset: ",offset_config.get('z_offset'))

print('init done')

# --- CREATING THE ROBOT NODE ---
class AprilTagDetectNode(Node):
    def __init__(self, name):
        super().__init__(name)  # Give this node a name in the ROS 2 system
        
        # The "Home" position for the 6 joints of the robotic arm (in degrees)
        self.init_joints = [90, 90, 0, 0, 90, 90]
        
        # Tools to convert ROS images to OpenCV images
        self.rgb_bridge = CvBridge()
        self.depth_bridge = CvBridge()
        
        # Flags and timers to keep track of what the robot is doing
        self.pubPos_flag = False
        self.pr_time = time.time()
        
        # --- THE APRILTAG DETECTOR ENGINE ---
        # This sets up the brain that looks for the black and white squares.
        self.at_detector = Detector(searchpath=['apriltags'], 
                                    families='tag36h11',  # The specific "language" of the AprilTags
                                    nthreads=8,  # Use 8 CPU cores to make it super fast
                                    quad_decimate=2.0,
                                    quad_sigma=0.0,
                                    refine_edges=1,
                                    decode_sharpening=0.25,
                                    debug=0)
        
        self.Center_x_list = []
        self.Center_y_list = []
        
        # Where is the arm's claw right now? [x, y, z, roll, pitch, yaw]
        self.CurEndPos = [0.1279, 0.00023, 0.1674, 0.00036, 1.3962, 0.00033]
        
        # Camera calibration numbers (how the camera lens bends light)
        self.camera_info_K = [477.57, 0.0, 319.38, 0.0, 477.55, 238.64, 0.0, 0.0, 1.0]
        
        # --- THE TRANSLATION MATRIX ---
        # This is super important! It is the physical measurement (in meters) from the arm's claw to the camera lens.
        # It tells the computer: "The camera is mounted 10.1cm to the left, 0.2cm forward, and 4.8cm above the claw."
        self.EndToCamMat = np.array([[ 0 ,0 ,1 ,-0.101],
                                     [-1  ,0 ,0  ,0.002],
                                     [0  ,-1  ,0 ,0.0482],
                                     [ 0.0 , 0.0 , 0.0 , 1.0]])
        
        # --- COMMUNICATION SETUP (Publishers & Subscribers) ---
        # Publishers = Radio stations the robot broadcasts on
        self.pos_info_pub = self.create_publisher(AprilTagInfo,"PosInfo",1)  # Tell others where the tag is
        self.CmdVel_pub = self.create_publisher(Twist,"cmd_vel",1)  # Tell the robot wheels to move
        self.TargetAngle_pub = self.create_publisher(ArmJoints, "arm6_joints", 10)  # Tell the arm to move its 6 joints
        self.TargetJoint5_pub = self.create_publisher(Int16, "set_joint5", 10)
        self.pub_cur_joints = self.create_publisher(CurJoints,"Curjoints",1)
        
        # Subscribers = Radio stations the robot listens to
        self.sub_grasp_status = self.create_subscription(Bool,"grasp_done",self.get_graspStatusCallBack,100)  # Listen for "I grabbed it!"
        
        # Listen to the camera's color and depth video feeds
        self.rgb_image_sub = Subscriber(self, Image, '/camera/color/image_raw')
        self.depth_image_sub = Subscriber(self, Image, '/camera/depth/image_raw')
        
        # --- ROS 2 SERVICE CLIENT ---
        # Ask the arm's math brain to calculate Forward Kinematics (FK)
        self.client = self.create_client(ArmKinemarics, 'get_kinemarics')
        
        # Wait here until the math brain service is awake and ready to do math
        while not self.client.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('Service not available, waiting again...')		
        
        # Move the arm to the home position, and wait until the arm is actually listening
        while not self.TargetAngle_pub.get_subscription_count():
            self.pubSix_Arm(self.init_joints)
            time.sleep(0.1)	
        self.pubSix_Arm(self.init_joints)  # Send the command one last time to be sure
        
        # --- SYNCING THE CAMERAS ---
        # This is brilliant. A depth camera sends two pictures: a color one and a distance one.
        # If the robot is moving, the two pictures might be taken a millisecond apart, causing the math to be wrong.
        # ApproximateTimeSynchronizer forces Python to wait until it has a matching pair of pictures taken at the exact same time.
        self.ts = ApproximateTimeSynchronizer([self.rgb_image_sub, self.depth_image_sub], 1, 0.5)
        # When a matched pair arrives, run the 'callback' function below
        self.ts.registerCallback(self.callback)

        # Load the offset settings from the YAML file earlier
        self.x_offset = offset_config.get('x_offset')
        self.y_offset = offset_config.get('y_offset')
        self.z_offset = offset_config.get('z_offset')
        
        # --- PID CONTROLLER FOR DRIVING ---
        # A PID controller is a math algorithm that helps a robot drive smoothly to a target distance without overshooting.
        # (P=Proportional, I=Integral, D=Derivative). Here, it is tuned to slow down as it gets closer.
        self.adjust_dist = True
        self.prev_dist = 0
        self.linearx_PID = (0.5, 0.0, 0.2)
        self.linearx_pid = simplePID(self.linearx_PID[0] / 1000.0, self.linearx_PID[1] / 1000.0, self.linearx_PID[2] / 1000.0)
        
        self.grasp_Dist = 220.0  # The ideal distance (in mm) to stop the robot from the target
        self.joint5 = Int16()
        
    # --- HELPER FUNCTIONS ---

    def pubCurrentJoints(self):
        # Broadcast where the arm currently is so other programs know
        cur_joints = CurJoints()
        cur_joints.joints = self.init_joints
        self.pub_cur_joints.publish(cur_joints) 
    
    def get_graspStatusCallBack(self,msg):
        # This triggers when the robot finishes grabbing the object.
        if msg.data == True:
            self.pubPos_flag = True
            self.adjust_dist = True
            time.sleep(3.0)  # Wait 3 seconds before looking for another tag

    def pubSix_Arm(self, joints, id=6, angle=180.0, runtime=2000):
        # Package the 6 joint angles into a message and send it to the arm motors.
        arm_joint =ArmJoints()
        arm_joint.joint1 = joints[0]
        arm_joint.joint2 = joints[1]
        arm_joint.joint3 = joints[2]
        arm_joint.joint4 = joints[3]
        arm_joint.joint5 = joints[4]
        arm_joint.joint6 = joints[5]
        arm_joint.time = runtime  # Tell the motors to take 2000 milliseconds (2 seconds) to reach this pose
        self.TargetAngle_pub.publish(arm_joint)

    def pubVel(self,vx,vy,vz):
        # Send driving commands to the robot's wheels
        vel = Twist()
        vel.linear.x = float(vx)  # Forward/backward speed
        vel.linear.y = float(vy)  # Side to side speed
        vel.angular.z = float(vz)  # Spin speed
        self.CmdVel_pub.publish(vel)
 
    def get_current_end_pos(self):
        # Ask the math brain: "Based on my current joint angles, where is my claw?"
        request = ArmKinemarics.Request()
        request.cur_joint1 = float(self.init_joints[0])
        # ... send joint angles ...
        request.kin_name = "fk"  # "fk" means Forward Kinematics
        future = self.client.call_async(request)  # Send the request in the background
        future.add_done_callback(self.get_fk_respone_callback)  # When the math is done, run the callback below

    def get_fk_respone_callback(self, future):
        # Catch the math brain's answer and save the claw's X, Y, Z, Roll, Pitch, Yaw into our memory
        try:
            response = future.result()
            self.CurEndPos[0] = response.x 
            self.CurEndPos[1] = response.y
            self.CurEndPos[2] = response.z 
            self.CurEndPos[3] = response.roll
            self.CurEndPos[4] = response.pitch
            self.CurEndPos[5] = response.yaw
        except Exception as e:
            self.get_logger().error(f'Service call failed: {e}')

    # --- THE MAIN CAMERA LOOP ---
    # This function runs automatically every time a matched pair of color and depth images arrives.
    def callback(self, color_frame, depth_frame):
        
        # 1. Convert images into OpenCV format
        rgb_image = self.rgb_bridge.imgmsg_to_cv2(color_frame,'rgb8')
        result_image = np.copy(rgb_image)
        result_image = cv.resize(result_image, (640, 480))  # Make it fit on the screen
        
        # 2. Process the depth image (this tells us how far away every single pixel is in millimeters)
        depth_image = self.depth_bridge.imgmsg_to_cv2(depth_frame, encoding[1])
        depth_to_color_image = cv2.applyColorMap(cv2.convertScaleAbs(depth_image, alpha=1.0), cv2.COLORMAP_JET) # Make it colorful so humans can see the distances
        frame = cv.resize(depth_image, (640, 480))
        depth_image_info = frame.astype(np.float32)
        
        # 3. Look for AprilTags! 
        # Convert to grayscale first, because color confuses the tag detector.
        tags = self.at_detector.detect(cv2.cvtColor(rgb_image, cv2.COLOR_RGB2GRAY), False, None, 0.025)
        # Sort them by their ID number
        tags = sorted(tags, key=lambda tag: tag.tag_id) 
        # Draw boxes around the tags so we can see them on screen
        draw_tags(result_image, tags, corners_color=(0, 0, 255), center_color=(0, 255, 0))
        
        # Draw a red rectangle in the center of the screen (probably a target zone for the camera)
        cv2.rectangle(result_image, (307, 241), (409, 338), (0, 0, 255), 3)
        
        key = cv2.waitKey(10)  # Listen for keyboard presses

        # 4. If we found a tag, AND we haven't grabbed it yet...
        if len(tags) > 0  and self.pubPos_flag == False:
            for i in range(len(tags)):
                # Get the X, Y pixel coordinates of the center of the tag
                center_x, center_y = tags[i].center
                cx = center_x
                cy = center_y
                # Look up that exact pixel in the depth image to find out how far away it is!
                # Divide by 1000 to convert millimeters to meters.
                cz = depth_image_info[int(cy),int(cx)]/1000
                
                # Calculate the exact 3D position of the tag in the real world
                pose = self.compute_heigh(cx,cy,cz)
                
                # How far off is the tag from where we actually want it to be? (Calibration math)
                x_offset_value = 0.145 - pose[0]
                y_offset_value = 0.0 - pose[1]
                z_offset_value = 0.04 - pose[2]
                
                # If the user presses the SPACEBAR (key code 32)
                if key == 32:
                    self.pubPos_flag = True
                    # Save these new offset numbers into our YAML config file to make the robot more accurate next time!
                    offset_config['x_offset'] = x_offset_value.item()
                    offset_config['y_offset'] = y_offset_value.item()
                    offset_config['z_offset'] = z_offset_value.item()
                    with open(offset_file, 'w') as file:
                        yaml.dump(offset_config, file, default_flow_style=False)	
                    print("Finish calibrate offset.")
                    
        # 5. Show the image on the screen and calculate the FPS (Frames Per Second)
        result_image = cv2.cvtColor(result_image, cv2.COLOR_RGB2BGR)  # Convert back to BGR for OpenCV display
        cur_time = time.time()
        fps = str(int(1/(cur_time - self.pr_time)))
        self.pr_time = cur_time
        cv2.putText(result_image, fps, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.imshow("result_image", result_image)
        key = cv2.waitKey(1)

    def move_dist(self, dist):
        # Use the PID controller to calculate how fast to drive the wheels to reach the target distance
        linear_x = self.linearx_pid.compute(dist, 200)
        self.pubVel(linear_x, 0, 0)

    # --- THE 3D MATH SECTION ---
    # (This is where it gets very complex, but here is the simple version of what's happening)

    def compute_heigh(self, x, y, z):
        # Step 1: We have a pixel (x,y) and a distance (z). Convert this into a 3D coordinate in the Camera's world.
        camera_location = self.pixel_to_camera_depth((x,y), z)
        
        # Step 2: Use the translation matrix to figure out where the tag is relative to the Arm's Claw.
        PoseEndMat = np.matmul(self.EndToCamMat, self.xyz_euler_to_mat(camera_location, (0, 0, 0)))
        
        # Step 3: We know where the claw is relative to the robot's base. Do more matrix math to combine them all!
        EndPointMat = self.get_end_point_mat()
        
        # Step 4: Final calculation! Where is the tag relative to the robot's main body?
        WorldPose = np.matmul(EndPointMat, PoseEndMat) 
        
        # Break the final matrix back down into X, Y, Z coordinates and angles
        pose_T, pose_R = self.mat_to_xyz_euler(WorldPose)
        print("pose_T: ", pose_T) # pose_T contains the final [X, Y, Z] location of the tag in the real world!
        return pose_T

    def get_end_point_mat(self):
        # Convert the arm's current position (Euler angles) into a 4x4 Matrix for the math above
        end_w, end_x, end_y, end_z = self.euler_to_quaternion(self.CurEndPos[3], self.CurEndPos[4], self.CurEndPos[5])
        endpoint_mat = self.xyz_quat_to_mat([self.CurEndPos[0], self.CurEndPos[1], self.CurEndPos[2]], [end_w, end_x, end_y, end_z])
        return endpoint_mat
        
    def pixel_to_camera_depth(self, pixel_coords, depth):
        # This is the camera math. It uses the camera lens properties (fx, fy, cx, cy) to turn a 2D pixel + distance 
        # into a real 3D X, Y, Z coordinate. 
        fx, fy, cx, cy = self.camera_info_K[0], self.camera_info_K[4], self.camera_info_K[2], self.camera_info_K[5]
        px, py = pixel_coords
        x = (px - cx) * depth / fx
        y = (py - cy) * depth / fy
        z = depth
        return np.array([x, y, z])
        
    # --- MATH HELPER FUNCTIONS ---
    # These functions convert data back and forth between different 3D math formats. 
    # (Euler angles = pitch/roll/yaw. Matrices = grids of numbers. Quaternions = a 4-part number system that avoids gimbal lock).
    # You don't need to memorize these, they are just translating languages for the robot's brain!
    
    def xyz_euler_to_mat(self, xyz, euler, degrees=False):
        if degrees:
            mat = tfs.euler.euler2mat(math.radians(euler[0]), math.radians(euler[1]), math.radians(euler[2]))
        else:
            mat = tfs.euler.euler2mat(euler[0], euler[1], euler[2])
        mat = tfs.affines.compose(np.squeeze(np.asarray(xyz)), mat, [1, 1, 1])
        return mat 
        
    def euler_to_quaternion(self, roll, pitch, yaw):
        quaternion = tf.quaternion_from_euler(roll, pitch, yaw)
        qw = quaternion[3]
        qx = quaternion[0]
        qy = quaternion[1]
        qz = quaternion[2]
        return np.array([qw, qx, qy, qz])
        
    def xyz_quat_to_mat(self, xyz, quat):
        mat = tfs.quaternions.quat2mat(np.asarray(quat))
        mat = tfs.affines.compose(np.squeeze(np.asarray(xyz)), mat, [1, 1, 1])
        return mat
        
    def mat_to_xyz_euler(self, mat, degrees=False):
        t, r, _, _ = tfs.affines.decompose(mat)
        if degrees:
            euler = np.degrees(tfs.euler.mat2euler(r))
        else:
            euler = tfs.euler.mat2euler(r)
        return t, euler

           
def main():
    # Turn on ROS 2
    print('----------------------')
    rclpy.init()
    
    # Create our AprilTag Detection Node
    apriltag_detect = AprilTagDetectNode('ApriltagDetect_node')
    
    # Ask for the arm's starting position
    apriltag_detect.get_current_end_pos()
    
    # Keep the node running forever until you press Ctrl+C
    rclpy.spin(apriltag_detect)