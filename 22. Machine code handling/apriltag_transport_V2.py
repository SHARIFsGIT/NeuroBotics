
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# ============================================================
# 1. IMPORT LIBRARIES
# ============================================================

import cv2                       # OpenCV: image processing and display
import os                        # Operating system functions
import numpy as np               # Mathematical calculations
import time                      # Time and delays
import math                      # Mathematical functions
import yaml                      # Read YAML configuration files

import rclpy                     # ROS 2 Python library
from rclpy.node import Node      # Create a ROS 2 node
from rclpy.action import ActionClient

import message_filters           # Synchronize camera messages
from message_filters import Subscriber, TimeSynchronizer, ApproximateTimeSynchronizer

from cv_bridge import CvBridge   # Convert ROS images into OpenCV images
from sensor_msgs.msg import Image

from dt_apriltags import Detector  # AprilTag detection

import transforms3d as tfs       # 3D transformations
import tf_transformations as tf  # Quaternion transformations

# Custom robot packages
from M3Pro_demo.vutils import draw_tags
from M3Pro_demo.compute_joint5 import *
from M3Pro_demo.Robot_Move import *

# Robot arm messages
from arm_interface.srv import ArmKinemarics
from arm_interface.msg import AprilTagInfo, CurJoints

from arm_msgs.msg import ArmJoints
from arm_msgs.msg import ArmJoint

# Standard ROS 2 messages
from std_msgs.msg import Float32, Bool, Int16, UInt16

# Robot movement and navigation messages
from geometry_msgs.msg import Twist, PoseWithCovarianceStamped, PoseStamped

from nav2_msgs.action import NavigateThroughPoses
from visualization_msgs.msg import MarkerArray


# ============================================================
# 2. LOAD CAMERA CALIBRATION OFFSETS
# ============================================================

# Location of the YAML file containing camera calibration offsets
offset_file = "/home/jetson/yahboomcar_ws/src/arm_kin/param/offset_value.yaml"

# Open the YAML file
with open(offset_file, 'r') as file:

    # Read the configuration values
    offset_config = yaml.safe_load(file)

# Display the loaded configuration
print(offset_config)

print("----------------------------")

print("x_offset: ", offset_config.get('x_offset'))
print("y_offset: ", offset_config.get('y_offset'))
print("z_offset: ", offset_config.get('z_offset'))

print('init done')


# ============================================================
# 3. CREATE APRILTAG DETECTION NODE
# ============================================================

class AprilTagDetectNode(Node):

    def __init__(self, name):

        # Initialize the ROS 2 node
        super().__init__(name)

        # Initial positions of the six robot joints
        self.init_joints = [90, 120, 0, 0, 90, 90]

        # Create bridge objects to convert ROS images into OpenCV images
        self.rgb_bridge = CvBridge()
        self.depth_bridge = CvBridge()

        # Control whether the detected position should be published
        self.pubPos_flag = False

        # Save the current time for FPS calculation
        self.pr_time = time.time()


        # ====================================================
        # 4. INITIALIZE APRILTAG DETECTOR
        # ====================================================

        self.at_detector = Detector(

            # AprilTag detector search path
            searchpath=['apriltags'],

            # AprilTag family
            families='tag36h11',

            # Number of processing threads
            nthreads=8,

            # Reduce image resolution for faster detection
            quad_decimate=2.0,

            # Image blur setting
            quad_sigma=0.0,

            # Improve edge detection
            refine_edges=1,

            # Improve decoding quality
            decode_sharpening=0.25,

            # Disable debug mode
            debug=0
        )


        # Lists to store detected AprilTag center coordinates
        self.Center_x_list = []
        self.Center_y_list = []


        # ====================================================
        # 5. ROBOT AND CAMERA CONFIGURATION
        # ====================================================

        # Current robot end-effector position
        # Format: X, Y, Z, Roll, Pitch, Yaw
        self.CurEndPos = [
            0.1458589529828534,
            0.00022969568906952754,
            0.18566515428310748,
            0.00012389155580734876,
            1.0471973953319513,
            8.297829493472317e-05
        ]

        # Camera intrinsic calibration matrix
        self.camera_info_K = [
            477.57421875, 0.0, 319.3820495605469,
            0.0, 477.55718994140625, 238.64108276367188,
            0.0, 0.0, 1.0
        ]

        # Transformation matrix between end-effector and camera
        self.EndToCamMat = np.array([
            [0,  0,  1, -1.00e-01],
            [-1, 0,  0,  0],
            [0, -1,  0,  4.82000000e-02],
            [0,  0,  0,  1.00000000e+00]
        ])


        # ====================================================
        # 6. CREATE ROS 2 PUBLISHERS
        # ====================================================

        # Publish detected AprilTag position
        self.pos_info_pub = self.create_publisher(
            AprilTagInfo, "PosInfo", 1
        )

        # Publish robot movement velocity
        self.CmdVel_pub = self.create_publisher(
            Twist, "cmd_vel", 1
        )

        # Publish commands for all six robot joints
        self.TargetAngle_pub = self.create_publisher(
            ArmJoints, "arm6_joints", 10
        )

        # Publish commands for a single robot joint
        self.pub_SingleTargetAngle = self.create_publisher(
            ArmJoint, "arm_joint", 10
        )

        # Publish robot navigation goal
        self.pub_orin_pose = self.create_publisher(
            PoseStamped, "/goal_pose", 10
        )

        # Publish joint 5 angle
        self.TargetJoint5_pub = self.create_publisher(
            Int16, "set_joint5", 10
        )

        # Publish the next robot operation status
        self.pub_status = self.create_publisher(
            Int16, "/next_status", 10
        )

        # Publish current robot joint positions
        self.pub_cur_joints = self.create_publisher(
            CurJoints, "Curjoints", 1
        )

        # Publish buzzer commands
        self.pub_beep = self.create_publisher(
            UInt16, "beep", 10
        )

        # Publish when no AprilTag is found
        self.pub_no_found = self.create_publisher(
            Bool, "/No_found", 10
        )

        # Publish unloading completion
        self.pub_unload_done = self.create_publisher(
            Bool, "/unload_done", 10
        )

        # Publish AprilTag detection result
        self.pub_detect_res = self.create_publisher(
            Bool, "/detect_result", 10
        )

        # Publish command to start robot rotation
        self.pub_start_rotate = self.create_publisher(
            Bool, "/start_rotate", 10
        )

        # Publish command to return to the original position
        self.send_back2orin = self.create_publisher(
            Bool, "/back_orin", 10
        )


        # ====================================================
        # 7. CREATE ROS 2 SUBSCRIBERS
        # ====================================================

        # Receive grasp completion status
        self.sub_grasp_status = self.create_subscription(
            Bool,
            "grasp_done",
            self.get_graspStatusCallBack,
            100
        )

        # Receive initial robot position from RViz
        self.sub_init_pose = self.create_subscription(
            PoseWithCovarianceStamped,
            "/initialpose",
            self.get_InitPoseCallBack,
            1
        )

        # Receive command to start AprilTag detection
        self.sub_start_detect = self.create_subscription(
            Bool,
            "/start_detect",
            self.get_StartDetectCallBack,
            100
        )

        # Receive command to transport the robot
        self.sub_start_transport = self.create_subscription(
            Bool,
            "/start_transport",
            self.get_StartTransportCallBack,
            100
        )

        # Receive signal that robot transportation is complete
        self.sub_start_back2orin = self.create_subscription(
            Bool,
            "/transport_done",
            self.get_TransbotStatusCallBack,
            100
        )

        # Receive rotation completion status
        self.sub_rotation_done = self.create_subscription(
            Bool,
            "/rotation_done",
            self.get_RotationStatusCallBack,
            100
        )


        # ====================================================
        # 8. CONNECT TO ROBOT CAMERA
        # ====================================================

        # Subscribe to RGB camera images
        self.rgb_image_sub = Subscriber(
            self,
            Image,
            '/camera/color/image_raw'
        )

        # Subscribe to depth camera images
        self.depth_image_sub = Subscriber(
            self,
            Image,
            '/camera/depth/image_raw'
        )


        # ====================================================
        # 9. CONNECT TO ROBOT KINEMATICS SERVICE
        # ====================================================

        # Create service client for forward kinematics
        self.client = self.create_client(
            ArmKinemarics,
            'get_kinemarics'
        )


        # ====================================================
        # 10. INITIALIZE ROBOT
        # ====================================================

        # Request current end-effector position
        self.get_current_end_pos()

        # Move the robot arm to its initial joint positions
        self.pubSix_Arm(self.init_joints)

        # Synchronize RGB and depth camera messages
        self.ts = ApproximateTimeSynchronizer(
            [self.rgb_image_sub, self.depth_image_sub],
            1,
            0.5
        )

        # Call callback() when synchronized images arrive
        self.ts.registerCallback(self.callback)

        # Publish initial joint positions
        self.pubCurrentJoints()


        # ====================================================
        # 11. INITIALIZE ROBOT CONTROL VARIABLES
        # ====================================================

        # Load camera calibration offsets
        self.x_offset = offset_config.get('x_offset')
        self.y_offset = offset_config.get('y_offset')
        self.z_offset = offset_config.get('z_offset')

        # Enable distance adjustment
        self.adjust_dist = True

        # Previous distance measurement
        self.prev_dist = 0

        # PID parameters for forward/backward movement
        self.linearx_PID = (0.3, 0.0, 0.1)

        # PID parameters for left/right movement
        self.lineary_PID = (0.2, 0.0, 0.2)

        # Initialize X-axis PID controller
        self.linearx_pid = simplePID(
            self.linearx_PID[0] / 1000.0,
            self.linearx_PID[1] / 1000.0,
            self.linearx_PID[2] / 1000.0
        )

        # Initialize Y-axis PID controller
        self.lineary_pid = simplePID(
            self.lineary_PID[0] / 100.0,
            self.lineary_PID[1] / 100.0,
            self.lineary_PID[2] / 100.0
        )

        # Desired distance from AprilTag in millimeters
        self.grasp_Dist = 220.0

        # Create message for joint 5
        self.joint5 = Int16()

        # Robot operation status variables
        self.start_transport = False
        self.rotate = False
        self.y_track_done = False
        self.y_track = False
        self.grasp_done = False

        # Store original robot navigation position
        self.orinal_pose = PoseStamped()

        # Set map coordinate frame
        self.orinal_pose.header.frame_id = "map"

        self.start_detect = False
        self.stop_rotate = False
        self.come_back = False
        self.next_navigation = False


    # ========================================================
    # 12. ROTATION STATUS CALLBACK
    # ========================================================

    def get_RotationStatusCallBack(self, msg):

        # Check whether rotation has finished
        if msg.data == True:

            self.stop_rotate = True

            print("Click on the image screen and press the following buttons to select the next step:")
            print("N to navigate to the next point")
            print("B to come back to the origin")


    # ========================================================
    # 13. START APRILTAG DETECTION CALLBACK
    # ========================================================

    def get_StartDetectCallBack(self, msg):

        if msg.data == True:

            # Enable AprilTag detection
            self.start_detect = True

            print("Detect the tag.")

            print("Click on the image screen and press the following buttons to select the next step:")

            print("n to navigate to the next point")
            print("b to come back to the origin")
            print("r to start rotating to find the machine block.")


    # ========================================================
    # 14. START TRANSPORT CALLBACK
    # ========================================================

    def get_StartTransportCallBack(self, msg):

        if msg.data == True:

            print("Transbot the tag.")

            # Check whether grasping has completed
            if self.grasp_done == True:

                # Start unloading operation
                self.unload()

                print("Click on the image screen and press the following buttons to select the next step:")

                print("n to navigate to the next point")
                print("b to come back to the origin")


    # ========================================================
    # 15. TRANSPORT COMPLETION CALLBACK
    # ========================================================

    def get_TransbotStatusCallBack(self, msg):

        if msg.data == True:

            # Reset robot tracking variables
            self.y_track_done = False
            self.adjust_dist = True
            self.stop_rotate = False

            # If an object was grasped, unload it
            if self.grasp_done == True:
                self.unload()

            print("Back to the orin,change the rotate status.")

            print("Click on the image screen and press the following buttons to select the next step:")

            print("n to navigate to the next point")


    # ========================================================
    # 16. RECEIVE INITIAL ROBOT POSITION
    # ========================================================

    def get_InitPoseCallBack(self, msg):

        # Save initial X position
        self.orinal_pose.pose.position.x = msg.pose.pose.position.x

        # Save initial Y position
        self.orinal_pose.pose.position.y = msg.pose.pose.position.y

        # Set orientation
        self.orinal_pose.pose.orientation.w = 1.0


    # ========================================================
    # 17. ROBOT Y-AXIS MOVEMENT USING PID
    # ========================================================

    def robot_Y_move(self, point_x):

        # Use PID to move the robot until the AprilTag
        # reaches the center of the camera image (pixel 320)
        linera_y = self.lineary_pid.compute(320, point_x) * 0.1

        # Check whether the AprilTag is close to the image center
        if abs(point_x - 320) < 15:

            # Stop sideways movement
            linera_y = 0.0

            self.y_track_done = True

        # Publish sideways velocity
        self.pubVel(0.0, linera_y, 0.0)

        # Stop tracking when alignment is complete
        if self.y_track_done == True:

            self.y_track = False

            self.pubVel(0.0, 0.0, 0.0)

            print("adjust dist to grasp it.")

            # Allow target position publication
            self.pubPos_flag = True

            self.adjust_dist = True


    # ========================================================
    # 18. UNLOAD OBJECT FROM ROBOT ARM
    # ========================================================

    def unload(self):

        # Select unloading joint positions based on AprilTag ID
        if self.cur_tagId == 1:

            self.down_joint = [155, 35, 70, 5, 60, 120]

        elif self.cur_tagId == 2:

            self.down_joint = [180, 35, 60, 0, 90, 120]

        elif self.cur_tagId == 3:

            self.down_joint = [28, 30, 70, 2, 90, 120]

        elif self.cur_tagId == 4:

            self.down_joint = [0, 43, 48, 6, 90, 120]


        # Move the robot arm to the unloading position
        self.pubSix_Arm(self.down_joint)

        time.sleep(2.5)

        # Move the sixth joint
        self.pubSingleArm(6, 30, 2000)

        time.sleep(2.5)

        # Return the arm to its initial position
        self.pubSix_Arm(self.init_joints)

        time.sleep(2.5)

        # Activate the buzzer
        self.Beep_Loop()

        # Reset grasp status
        self.grasp_done = False

        # Create unloading completion message
        unload_status = Bool()

        unload_status.data = True

        # Publish unloading completion
        self.pub_unload_done.publish(unload_status)

        self.y_track_done = False


    # ========================================================
    # 19. CONTROL THE BUZZER
    # ========================================================

    def Beep_Loop(self):

        # Create buzzer message
        beep = UInt16()

        # Turn buzzer ON
        beep.data = 1

        self.pub_beep.publish(beep)

        time.sleep(1.0)

        # Turn buzzer OFF
        beep.data = 0

        self.pub_beep.publish(beep)


    # ========================================================
    # 20. PUBLISH CURRENT JOINT POSITIONS
    # ========================================================

    def pubCurrentJoints(self):

        # Create current joint message
        cur_joints = CurJoints()

        # Set initial joint positions
        cur_joints.joints = self.init_joints

        # Publish joint positions
        self.pub_cur_joints.publish(cur_joints)


    # ========================================================
    # 21. RECEIVE GRASP COMPLETION STATUS
    # ========================================================

    def get_graspStatusCallBack(self, msg):

        if msg.data == True:

            # Mark grasp operation as completed
            self.grasp_done = True

            print("Click the rviz window with the mouse to give the next target point, or press the b key on the keyboard to return to the origin")


    # ========================================================
    # 22. PUBLISH COMMANDS FOR ALL SIX ROBOT JOINTS
    # ========================================================

    def pubSix_Arm(self, joints, id=6, angle=180.0, runtime=2000):

        # Create six-joint command message
        arm_joint = ArmJoints()

        # Assign joint angles
        arm_joint.joint1 = joints[0]
        arm_joint.joint2 = joints[1]
        arm_joint.joint3 = joints[2]
        arm_joint.joint4 = joints[3]
        arm_joint.joint5 = joints[4]
        arm_joint.joint6 = joints[5]

        # Set movement duration in milliseconds
        arm_joint.time = runtime

        # Publish the six-joint command
        self.TargetAngle_pub.publish(arm_joint)


    # ========================================================
    # 23. PUBLISH COMMAND FOR A SINGLE JOINT
    # ========================================================

    def pubSingleArm(self, joint_id, joint_angle, run_time):

        # Create single-joint command message
        arm_joint = ArmJoint()

        # Set joint angle
        arm_joint.joint = joint_angle

        # Set joint ID
        arm_joint.id = joint_id

        # Set movement duration
        arm_joint.time = run_time

        # Publish command
        self.pub_SingleTargetAngle.publish(arm_joint)


    # ========================================================
    # 24. PUBLISH ROBOT MOVEMENT VELOCITY
    # ========================================================

    def pubVel(self, vx, vy, vz):

        # Create velocity message
        vel = Twist()

        # Forward and backward velocity
        vel.linear.x = float(vx)

        # Left and right velocity
        vel.linear.y = float(vy)

        # Rotational velocity
        vel.angular.z = float(vz)

        # Publish movement command
        self.CmdVel_pub.publish(vel)


    # ========================================================
    # 25. CALCULATE CURRENT END-EFFECTOR POSITION (FK)
    # ========================================================

    def get_current_end_pos(self):

        # Create forward kinematics request
        request = ArmKinemarics.Request()

        # Send current joint angles
        request.cur_joint1 = float(self.init_joints[0])
        request.cur_joint2 = float(self.init_joints[1])
        request.cur_joint3 = float(self.init_joints[2])
        request.cur_joint4 = float(self.init_joints[3])
        request.cur_joint5 = float(self.init_joints[4])

        # Select forward kinematics calculation
        request.kin_name = "fk"

        # Send request asynchronously
        future = self.client.call_async(request)

        # Process the response when it arrives
        future.add_done_callback(
            self.get_fk_respone_callback
        )


    # ========================================================
    # 26. RECEIVE FORWARD KINEMATICS RESPONSE
    # ========================================================

    def get_fk_respone_callback(self, future):

        try:

            # Get service response
            response = future.result()

            # Update current end-effector position
            self.CurEndPos[0] = response.x
            self.CurEndPos[1] = response.y
            self.CurEndPos[2] = response.z

            # Update current orientation
            self.CurEndPos[3] = response.roll
            self.CurEndPos[4] = response.pitch
            self.CurEndPos[5] = response.yaw

            print("self.CurEndPose: ", self.CurEndPos)

        except Exception as e:

            # Display error if service call fails
            self.get_logger().error(
                f'Service call failed: {e}'
            )


    # ========================================================
    # 27. MAIN CAMERA CALLBACK
    # ========================================================
    # This function processes synchronized RGB and depth images.
    # It detects AprilTags and controls the robot.

    def callback(self, color_frame, depth_frame):

        # ====================================================
        # 27.1 CONVERT RGB IMAGE
        # ====================================================

        # Convert ROS RGB image into OpenCV format
        rgb_image = self.rgb_bridge.imgmsg_to_cv2(
            color_frame,
            'rgb8'
        )

        # Create a copy of the image for drawing
        result_image = np.copy(rgb_image)

        # Resize RGB image
        result_image = cv.resize(
            result_image,
            (640, 480)
        )


        # ====================================================
        # 27.2 CONVERT DEPTH IMAGE
        # ====================================================

        # Convert ROS depth image into OpenCV format
        depth_image = self.depth_bridge.imgmsg_to_cv2(
            depth_frame,
            encoding[1]
        )

        # Convert depth data into a colored visualization
        depth_to_color_image = cv2.applyColorMap(
            cv2.convertScaleAbs(depth_image, alpha=1.0),
            cv2.COLORMAP_JET
        )

        # Resize depth image
        frame = cv.resize(
            depth_image,
            (640, 480)
        )

        # Convert depth data into floating-point format
        depth_image_info = frame.astype(np.float32)


        # ====================================================
        # 27.3 DETECT APRILTAGS
        # ====================================================

        # Convert RGB image into grayscale
        gray_image = cv2.cvtColor(
            rgb_image,
            cv2.COLOR_RGB2GRAY
        )

        # Detect AprilTags
        tags = self.at_detector.detect(
            gray_image,
            False,
            None,
            0.025
        )

        # Sort detected tags by their ID
        tags = sorted(
            tags,
            key=lambda tag: tag.tag_id
        )

        # Draw detected AprilTags on the image
        draw_tags(
            result_image,
            tags,
            corners_color=(0, 0, 255),
            center_color=(0, 255, 0)
        )


        # ====================================================
        # 27.4 CHECK KEYBOARD INPUT
        # ====================================================

        # Read keyboard input
        key = cv2.waitKey(10)

        # Create lists to store tag center positions
        self.Center_x_list = list(range(len(tags)))
        self.Center_y_list = list(range(len(tags)))


        # Press R to start robot rotation
        if key == ord('r'):

            self.rotate = True
            self.stop_rotate = False

            # Create rotation command
            start_rotate = Bool()

            start_rotate.data = True

            # Publish rotation command
            self.pub_start_rotate.publish(start_rotate)

            print("start to rotate.")


        # Press N to navigate to the next point
        elif key == ord('n'):

            self.next_navigation = True
            self.rotate = False
            self.stop_rotate = False

            # Create next navigation status
            next_status = Int16()

            next_status.data = 1

            # Publish next navigation status
            self.pub_status.publish(next_status)

            print("Go to the next point.")


        # Press B to return to the original position
        elif key == ord('b'):

            print("Come back to the orin.")

            self.rotate = False
            self.start_detect = False

            # Set navigation status to zero
            next_status = Int16()

            next_status.data = 0

            self.pub_status.publish(next_status)

            self.come_back = True

            # Create return-to-origin message
            back_orin = Bool()

            back_orin.data = True

            self.send_back2orin.publish(back_orin)


        # ====================================================
        # 27.5 APRILTAG SEARCH AND ROBOT ROTATION
        # ====================================================

        if self.start_detect == True:

            # If no tag is detected, keep rotating
            if (
                self.rotate == True
                and len(tags) == 0
                and self.stop_rotate == False
            ):

                # Rotate robot
                self.pubVel(0, 0, 0.2)

                print("Rotating to detect the apriltag.")


            # If AprilTag is detected while rotating
            elif len(tags) > 0 and self.rotate == True:

                # Publish successful detection
                detect = Bool()

                detect.data = True

                self.pub_detect_res.publish(detect)

                # Stop rotation
                self.rotate = False

                self.pubVel(0, 0, 0)

                # Activate buzzer
                self.Beep_Loop()

                print("Found the apriltag.")

                # Start horizontal alignment
                self.y_track = True


            # If rotation stops and no tag is detected
            elif self.stop_rotate == True and len(tags) == 0:

                # Stop robot movement
                self.pubVel(0, 0, 0)

                # Publish no-tag-found message
                no_found = Bool()

                no_found.data = True

                self.pub_no_found.publish(no_found)


        # ====================================================
        # 27.6 PROCESS DETECTED APRILTAGS
        # ====================================================

        if len(tags) > 0 and self.rotate == False:

            # Process every detected AprilTag
            for i in range(len(tags)):

                # Get AprilTag center coordinates
                center_x, center_y = tags[i].center

                # Save center coordinates
                self.Center_x_list[i] = center_x
                self.Center_y_list[i] = center_y

                # Store X and Y coordinates
                cx = center_x
                cy = center_y

                # Read depth at the AprilTag center
                # Convert millimeters into meters
                cz = depth_image_info[
                    int(cy),
                    int(cx)
                ] / 1000


                # =================================================
                # 27.7 CALCULATE OBJECT POSITION
                # =================================================

                # Calculate object position in robot coordinates
                pose = self.compute_heigh(
                    cx,
                    cy,
                    cz
                )

                # Calculate position ratio
                degree = pose[1] / pose[0]

                # Calculate distance from robot
                dist_detect = math.sqrt(
                    pose[1] ** 2 + pose[0] ** 2
                )

                # Convert meters into millimeters
                dist_detect = dist_detect * 1000

                # Create distance text
                dist = 'dist: ' + str(dist_detect) + 'mm'

                # Display distance on camera image
                cv.putText(
                    result_image,
                    dist,
                    (int(cx) + 5, int(cy) + 15),
                    cv.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (255, 0, 0),
                    2
                )


                # =================================================
                # 27.8 CALCULATE JOINT 5 ANGLE
                # =================================================

                # Calculate tag orientation using its corner coordinates
                vx = (
                    int(tags[i].corners[0][0])
                    - int(tags[i].corners[1][0])
                )

                vy = (
                    int(tags[i].corners[0][1])
                    - int(tags[i].corners[1][1])
                )

                # Calculate required joint 5 angle
                target_joint5 = compute_joint5(vx, vy)


                # =================================================
                # 27.9 ALIGN ROBOT WITH APRILTAG
                # =================================================

                # If horizontal tracking is enabled
                if self.y_track == True:

                    # Move robot sideways to center the AprilTag
                    self.robot_Y_move(center_x)


                # =================================================
                # 27.10 ADJUST DISTANCE BEFORE GRASPING
                # =================================================

                if self.pubPos_flag == True:

                    # Check whether robot is at the desired distance
                    if (
                        abs(dist_detect - 200.0) > 10
                        and self.adjust_dist == True
                    ):

                        # Move robot forward or backward
                        self.move_dist(dist_detect)

                    else:

                        # Stop distance adjustment
                        self.adjust_dist = False

                        # Stop robot
                        self.pubVel(0, 0, 0)

                        # Create AprilTag information message
                        tag = AprilTagInfo()

                        # Save AprilTag ID
                        tag.id = tags[i].tag_id

                        self.cur_tagId = tag.id

                        # Save image center coordinates
                        tag.x = self.Center_x_list[i]
                        tag.y = self.Center_y_list[i]

                        # Read depth at the tag center
                        tag.z = depth_image_info[
                            int(tag.y),
                            int(tag.x)
                        ] / 1000

                        # Calculate tag orientation again
                        vx = (
                            int(tags[i].corners[0][0])
                            - int(tags[i].corners[1][0])
                        )

                        vy = (
                            int(tags[i].corners[0][1])
                            - int(tags[i].corners[1][1])
                        )

                        target_joint5 = compute_joint5(vx, vy)

                        print("target_joint5: ", target_joint5)

                        # Save target joint angle
                        self.joint5.data = int(target_joint5)

                        # Continue only if valid depth exists
                        if tag.z != 0:

                            # Publish target joint angle
                            self.TargetJoint5_pub.publish(
                                self.joint5
                            )

                            # Publish AprilTag position
                            self.pos_info_pub.publish(tag)

                            # Disable repeated position publication
                            self.pubPos_flag = False

                            # Stop detection process
                            self.start_detect = False

                            # Update robot operation status
                            next_status = Int16()

                            next_status.data = 2

                            self.pub_status.publish(next_status)

                        else:

                            print("Invalid distance.")


        # ====================================================
        # 27.11 DISPLAY CAMERA IMAGE AND FPS
        # ====================================================

        # Convert RGB image into BGR for OpenCV display
        result_image = cv2.cvtColor(
            result_image,
            cv2.COLOR_RGB2BGR
        )

        # Calculate current time
        cur_time = time.time()

        # Calculate frames per second
        fps = str(
            int(1 / (cur_time - self.pr_time))
        )

        # Update previous time
        self.pr_time = cur_time

        # Display FPS on image
        cv2.putText(
            result_image,
            fps,
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
            2
        )

        # Display final camera image
        cv2.imshow(
            "result_image",
            result_image
        )

        # Check keyboard input
        key = cv2.waitKey(1)


    # ========================================================
    # 28. ADJUST ROBOT FORWARD/BACKWARD DISTANCE
    # ========================================================

    def move_dist(self, dist):

        # Use PID controller to reach desired distance
        linear_x = self.linearx_pid.compute(
            dist,
            200
        )

        # Publish forward/backward movement
        self.pubVel(
            linear_x,
            0,
            0
        )


    # ========================================================
    # 29. CALCULATE OBJECT POSITION IN ROBOT COORDINATES
    # ========================================================

    def compute_heigh(self, x, y, z):

        # Convert camera pixel and depth into 3D coordinates
        camera_location = self.pixel_to_camera_depth(
            (x, y),
            z
        )

        # Transform camera coordinates into end-effector coordinates
        PoseEndMat = np.matmul(
            self.EndToCamMat,
            self.xyz_euler_to_mat(
                camera_location,
                (0, 0, 0)
            )
        )

        # Get current end-effector transformation matrix
        EndPointMat = self.get_end_point_mat()

        # Transform object coordinates into robot/world coordinates
        WorldPose = np.matmul(
            EndPointMat,
            PoseEndMat
        )

        # Convert matrix into position and orientation
        pose_T, pose_R = self.mat_to_xyz_euler(
            WorldPose
        )

        # Apply calibration offsets
        pose_T[0] = pose_T[0] + self.x_offset
        pose_T[1] = pose_T[1] + self.y_offset
        pose_T[2] = pose_T[2] + self.z_offset

        return pose_T


    # ========================================================
    # 30. GET END-EFFECTOR TRANSFORMATION MATRIX
    # ========================================================

    def get_end_point_mat(self):

        # Convert current Euler angles into quaternion
        end_w, end_x, end_y, end_z = self.euler_to_quaternion(
            self.CurEndPos[3],
            self.CurEndPos[4],
            self.CurEndPos[5]
        )

        # Create transformation matrix
        endpoint_mat = self.xyz_quat_to_mat(
            [
                self.CurEndPos[0],
                self.CurEndPos[1],
                self.CurEndPos[2]
            ],
            [
                end_w,
                end_x,
                end_y,
                end_z
            ]
        )

        return endpoint_mat


    # ========================================================
    # 31. CONVERT CAMERA PIXELS INTO 3D COORDINATES
    # ========================================================

    def pixel_to_camera_depth(self, pixel_coords, depth):

        # Read camera focal lengths and center coordinates
        fx = self.camera_info_K[0]
        fy = self.camera_info_K[4]

        cx = self.camera_info_K[2]
        cy = self.camera_info_K[5]

        # Get pixel X and Y coordinates
        px, py = pixel_coords

        # Calculate 3D X coordinate
        x = (px - cx) * depth / fx

        # Calculate 3D Y coordinate
        y = (py - cy) * depth / fy

        # Z represents depth
        z = depth

        return np.array([x, y, z])


    # ========================================================
    # 32. CONVERT POSITION AND EULER ANGLES INTO MATRIX
    # ========================================================

    def xyz_euler_to_mat(self, xyz, euler, degrees=False):

        # Convert degrees into radians if necessary
        if degrees:

            mat = tfs.euler.euler2mat(
                math.radians(euler[0]),
                math.radians(euler[1]),
                math.radians(euler[2])
            )

        else:

            # Convert Euler angles directly into rotation matrix
            mat = tfs.euler.euler2mat(
                euler[0],
                euler[1],
                euler[2]
            )

        # Combine translation and rotation
        mat = tfs.affines.compose(
            np.squeeze(np.asarray(xyz)),
            mat,
            [1, 1, 1]
        )

        return mat


    # ========================================================
    # 33. CONVERT EULER ANGLES INTO QUATERNION
    # ========================================================

    def euler_to_quaternion(self, roll, pitch, yaw):

        # Convert Euler angles into quaternion
        quaternion = tf.quaternion_from_euler(
            roll,
            pitch,
            yaw
        )

        # Extract quaternion values
        qw = quaternion[3]
        qx = quaternion[0]
        qy = quaternion[1]
        qz = quaternion[2]

        return np.array([
            qw,
            qx,
            qy,
            qz
        ])


    # ========================================================
    # 34. CONVERT POSITION AND QUATERNION INTO MATRIX
    # ========================================================

    def xyz_quat_to_mat(self, xyz, quat):

        # Convert quaternion into rotation matrix
        mat = tfs.quaternions.quat2mat(
            np.asarray(quat)
        )

        # Combine translation and rotation
        mat = tfs.affines.compose(
            np.squeeze(np.asarray(xyz)),
            mat,
            [1, 1, 1]
        )

        return mat


    # ========================================================
    # 35. CONVERT MATRIX INTO POSITION AND EULER ANGLES
    # ========================================================

    def mat_to_xyz_euler(self, mat, degrees=False):

        # Extract translation and rotation
        t, r, _, _ = tfs.affines.decompose(mat)

        # Convert rotation matrix into Euler angles
        if degrees:

            euler = np.degrees(
                tfs.euler.mat2euler(r)
            )

        else:

            euler = tfs.euler.mat2euler(r)

        return t, euler


# ============================================================
# 36. MAIN FUNCTION: START ROS 2
# ============================================================

def main():

    print('----------------------')

    # Initialize ROS 2
    rclpy.init()

    # Create AprilTag detection node
    apriltag_detect = AprilTagDetectNode(
        'ApriltagDetect_node'
    )

    # Keep the node running and processing camera messages
    rclpy.spin(apriltag_detect)


# ============================================================
# 37. EXECUTE THE PROGRAM
# ============================================================

if __name__ == '__main__':

    # Start the main function
    main()
