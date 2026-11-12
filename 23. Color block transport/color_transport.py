
# ============================================================
# 1. IMPORT LIBRARIES
# ============================================================

# OpenCV is used for image processing and displaying camera images.
import cv2
import cv as cv

# os helps us work with file and folder paths.
import os

# NumPy is used for arrays and mathematical calculations.
import numpy as np

# ROS 2 camera message types.
from sensor_msgs.msg import Image, CameraInfo

# Synchronizes messages from multiple ROS 2 topics.
import message_filters

# Functions for drawing AprilTags.
from M3Pro_demo.vutils import draw_tags

# AprilTag detection library.
from dt_apriltags import Detector

# Converts ROS images into OpenCV images.
from cv_bridge import CvBridge

# Robot movement and pose calculation functions.
from M3Pro_demo.Robot_Move import *
from M3Pro_demo.compute_pose import *
from M3Pro_demo.color_common import *

# Custom ROS 2 service for robot arm kinematics.
from arm_interface.srv import ArmKinemarics

# Custom messages for AprilTag information and current joints.
from arm_interface.msg import AprilTagInfo, CurJoints

# Custom robot arm messages.
from arm_msgs.msg import ArmJoints, ArmJoint

# Standard ROS 2 messages.
from std_msgs.msg import Float32, Bool, Int16

# Supported depth image encodings.
encoding = ['16UC1', '32FC1']

# Used for delays and time measurements.
import time

# Libraries for 3D transformations and coordinate calculations.
import transforms3d as tfs
import tf_transformations as tf

# Reads configuration values from a YAML file.
import yaml

# Provides mathematical functions such as sqrt, radians and degrees.
import math

# ROS 2 Python node and client libraries.
from rclpy.node import Node
import rclpy

# ROS 2 message synchronization tools.
from message_filters import Subscriber, TimeSynchronizer, ApproximateTimeSynchronizer

# Used to publish robot movement commands.
from geometry_msgs.msg import Twist

# Finds installed ROS 2 package directories.
from ament_index_python.packages import get_package_share_directory

# Allows image display to run in a separate thread.
import threading

# Calculates the robot arm's fifth joint angle.
from M3Pro_demo.compute_joint5 import *


# ============================================================
# 2. CONFIGURATION FILE PATHS
# ============================================================

# Main directory containing this robot demonstration package.
package_pwd = "/home/jetson/yahboomcar_ws/src/M3Pro_demo/M3Pro_demo/"

# YAML file containing camera-to-robot coordinate offsets.
offset_file = "/home/jetson/yahboomcar_ws/src/arm_kin/param/offset_value.yaml"

# Open the YAML file and load its values.
with open(offset_file, 'r') as file:
    offset_config = yaml.safe_load(file)

# Display all loaded configuration values.
print(offset_config)
print("----------------------------")

# Display the coordinate offsets individually.
print("x_offset: ", offset_config.get('x_offset'))
print("y_offset: ", offset_config.get('y_offset'))
print("z_offset: ", offset_config.get('z_offset'))

print('init done')


# ============================================================
# 3. MAIN ROS 2 NODE
# ============================================================

# This class handles:
# - Camera image processing.
# - Color recognition.
# - Object distance calculation.
# - Robot movement.
# - Robot arm commands.
# - Grasping and unloading operations.

class ColorRecognizeNode(Node):

    def __init__(self, name):

        # Initialize this class as a ROS 2 node.
        super().__init__(name)

        # ----------------------------------------------------
        # 3.1 ROBOT ARM INITIAL POSITIONS
        # ----------------------------------------------------

        # Initial positions of the six robot arm joints.
        self.init_joints = [90, 100, 0, 0, 90, 0]

        # Another initial joint configuration using float values.
        self.init_joints_float = [90.0, 150.0, 12.0, 20.0, 90.0, 30.0]

        # Joint positions used when placing or unloading an object.
        self.down_joint = [155, 35, 70, 5, 60, 120]

        # ----------------------------------------------------
        # 3.2 CAMERA BRIDGES
        # ----------------------------------------------------

        # Converts RGB camera messages into OpenCV images.
        self.rgb_bridge = CvBridge()

        # Converts depth camera messages into OpenCV images.
        self.depth_bridge = CvBridge()

        # Controls whether object position information can be published.
        self.pub_pos_flag = True

        # Stores the current time.
        self.pr_time = time.time()

        # Counter variable.
        self.cnt = 0

        # Stores the current measured distance.
        self.cur_distance = 0.0

        # Enables or disables object tracking.
        self.track_flag = True

        # Stores the previous distance measurement.
        self.prev_dist = 0

        # Stores the previous angular measurement.
        self.prev_angular = 0

        # Stores the previous roll measurement.
        self.prev_roll = 0

        # Minimum target distance used during robot movement.
        self.minDist = 400

        # Target distance for grasping.
        self.grasp_Dist = 250

        # Enables or disables XY tracking.
        self.xy_track_flag = True

        # PID parameters for movement along the X axis.
        self.linearx_PID = (0.5, 0.0, 0.2)

        # PID parameters for movement along the Y axis.
        self.lineary_PID = (0.2, 0.0, 0.1)

        # PID parameters for angular movement.
        self.angz_PID = (0.5, 0.0, 0.5)

        # ----------------------------------------------------
        # 3.3 APRILTAG DETECTOR
        # ----------------------------------------------------

        # Create an AprilTag detector.
        # The detector is configured to recognize the tag36h11 family.
        self.at_detector = Detector(
            searchpath=['apriltags'],
            families='tag36h11',
            nthreads=8,
            quad_decimate=2.0,
            quad_sigma=0.0,
            refine_edges=1,
            decode_sharpening=0.25,
            debug=0
        )

        # Current end-effector position of the robot arm.
        # The values represent XYZ position and roll, pitch, yaw.
        self.CurEndPos = [
            0.1279009179959246,
            0.00023254956548456117,
            0.1484898062979958,
            0.00036263794618046863,
            1.3962632350758744,
            0.0003332603981328959
        ]

        # Camera intrinsic matrix.
        # It contains focal lengths and the optical center.
        self.camera_info_K = [
            477.57421875, 0.0, 319.3820495605469,
            0.0, 477.55718994140625, 238.64108276367188,
            0.0, 0.0, 1.0
        ]

        # Transformation matrix between the robot end-effector
        # coordinate system and the camera coordinate system.
        self.EndToCamMat = np.array([
            [0, 0, 1, -1.00e-01],
            [-1, 0, 0, 0],
            [0, -1, 0, 4.82000000e-02],
            [0.00000000e+00, 0.00000000e+00,
             0.00000000e+00, 1.00000000e+00]
        ])

        # ----------------------------------------------------
        # 3.4 CAMERA SUBSCRIBERS
        # ----------------------------------------------------

        # Subscribe to the RGB camera image topic.
        self.rgb_image_sub = Subscriber(
            self,
            Image,
            '/camera/color/image_raw'
        )

        # Receive information when the robot arm finishes grasping.
        self.sub_grasp_status = self.create_subscription(
            Bool,
            "grasp_done",
            self.get_graspStatusCallBack,
            100
        )

        # Subscribe to the depth camera image topic.
        self.depth_image_sub = Subscriber(
            self,
            Image,
            '/camera/depth/image_raw'
        )

        # ----------------------------------------------------
        # 3.5 ROS 2 PUBLISHERS
        # ----------------------------------------------------

        # Publishes movement commands to the mobile robot.
        self.CmdVel_pub = self.create_publisher(
            Twist,
            "cmd_vel",
            1
        )

        # Publishes the current robot arm joint positions.
        self.pub_cur_joints = self.create_publisher(
            CurJoints,
            "Curjoints",
            1
        )

        # Publishes a command for one robot arm joint.
        self.pub_SingleTargetAngle = self.create_publisher(
            ArmJoint,
            "arm_joint",
            10
        )

        # Publishes detected object position information.
        self.pos_info_pub = self.create_publisher(
            AprilTagInfo,
            "PosInfo",
            1
        )

        # Publishes commands for all six robot arm joints.
        self.pub_SixTargetAngle = self.create_publisher(
            ArmJoints,
            "arm6_joints",
            10
        )

        # ----------------------------------------------------
        # 3.6 ROBOT ARM KINEMATICS SERVICE
        # ----------------------------------------------------

        # Create a client for the robot arm kinematics service.
        # This service calculates forward or inverse kinematics.
        self.client = self.create_client(
            ArmKinemarics,
            'get_kinemarics'
        )

        # Publishes a beep command.
        self.pub_beep = self.create_publisher(
            Bool,
            "beep",
            10
        )

        # Sends a command to return the mobile robot to its origin.
        self.send_back2orin = self.create_publisher(
            Bool,
            "/back_orin",
            10
        )

        # Receives a command to start transporting the object.
        self.sub_start_transport = self.create_subscription(
            Bool,
            "/start_transport",
            self.get_StartTransportCallBack,
            100
        )

        # Publishes the next navigation or operation status.
        self.pub_status = self.create_publisher(
            Int16,
            "/next_status",
            10
        )

        # Receives information that the robot has completed transportation.
        self.sub_start_back2orin = self.create_subscription(
            Bool,
            "/transport_done",
            self.get_TransbotStatusCallBack,
            100
        )

        # Publishes the status of the unloading operation.
        self.pub_unload_done = self.create_publisher(
            Bool,
            "/unload_done",
            10
        )

        # Publishes the target angle for the fifth robot arm joint.
        self.TargetJoint5_pub = self.create_publisher(
            Int16,
            "set_joint5",
            10
        )

        # ----------------------------------------------------
        # 3.7 INITIAL ROBOT STATE
        # ----------------------------------------------------

        # Publish the initial joint positions.
        self.pubCurrentJoints()

        # Request the current robot arm end-effector position
        # using forward kinematics.
        self.get_current_end_pos()

        # Subscribe to camera calibration information.
        self.camera_info_sub = self.create_subscription(
            CameraInfo,
            '/camera/color/camera_info',
            self.camera_info_callback,
            10
        )

        # Synchronize RGB and depth images.
        # Queue size = 1.
        # Maximum allowed timestamp difference = 0.5 seconds.
        self.ts = ApproximateTimeSynchronizer(
            [self.rgb_image_sub, self.depth_image_sub],
            1,
            0.5
        )

        # Call callback() whenever synchronized images arrive.
        self.ts.registerCallback(self.callback)

        # Move the robot arm to its initial position.
        self.pubSixArm(self.init_joints)

        # ----------------------------------------------------
        # 3.8 OBJECT TRACKING SETTINGS
        # ----------------------------------------------------

        # Physical size of an AprilTag in meters.
        self.tag_size = 0.05

        # Camera calibration matrix will be updated by camera_info_callback().
        self.camera_matrix = None

        # Camera distortion coefficients.
        self.dist_coeffs = None

        # Direction used for robot rotation.
        self.rotation_direction = 1

        # Enables roll tracking.
        self.roll_track_flag = True

        # Indicates whether grasping has started.
        self.start_grasp = False

        # Enables Y-axis movement.
        self.move_y = True

        # Create an object for pose and distance calculations.
        self.compute_dist = ComputePose("compute_dist")

        # Direction used for X-axis movement.
        self.x_direction = 1

        # Tracking control flags.
        self.x_roll_track_flag = True
        self.y_roll_track_flag = False

        # Indicates whether each tracking stage has finished.
        self.x_track_done = False
        self.roll_track_done = False
        self.y_track_done = False

        # Target object shape.
        self.Target_Shape = "Square"

        # Read coordinate correction values from the YAML file.
        self.x_offset = offset_config.get('x_offset')
        self.y_offset = offset_config.get('y_offset')
        self.z_offset = offset_config.get('z_offset')

        # Enables distance adjustment before grasping.
        self.adjust_dist = True

        # Reset previous distance.
        self.prev_dist = 0

        # PID parameters for X-axis distance control.
        self.linearx_PID = (0.5, 0.0, 0.2)

        # Create the PID controller.
        # The parameters are divided by 1000 to convert their scale.
        self.linearx_pid = simplePID(
            self.linearx_PID[0] / 1000.0,
            self.linearx_PID[1] / 1000.0,
            self.linearx_PID[2] / 1000.0
        )

        # Target grasping distance in millimeters.
        self.grasp_Dist = 220.0

        # Indicates whether the current operation is complete.
        self.done_flag = True

        # Selected color:
        # 0 = no color
        # 1 = red
        # 2 = green
        # 3 = blue
        # 4 = yellow
        self.target_color = 0

        # Paths to the saved HSV configuration files.
        self.red_hsv_text = os.path.join(
            package_pwd,
            'red_colorHSV.text'
        )

        self.green_hsv_text = os.path.join(
            package_pwd,
            'green_colorHSV.text'
        )

        self.blue_hsv_text = os.path.join(
            package_pwd,
            'blue_colorHSV.text'
        )

        self.yellow_hsv_text = os.path.join(
            package_pwd,
            'yellow_colorHSV.text'
        )

        # Stores the HSV range used to detect the selected color.
        self.hsv_range = ()

        # Indicates whether the user has selected an image region.
        self.select_flags = False

        # Enables the color tracking state.
        self.gTracker_state = False

        # Name of the OpenCV display window.
        self.windows_name = 'frame'

        # Current tracking state.
        # 'init' means initialization.
        # 'identify' means color identification.
        # 'mouse' is used after mouse selection.
        self.Track_state = 'init'

        # Stores the mouse position.
        self.Mouse_XY = (0, 0)

        # Stores the selected image region coordinates.
        self.cols, self.rows = 0, 0

        # Stores the selected region of interest.
        self.Roi_init = ()

        # Create the color detection object.
        self.color = color_detect()

        # Stores the name of the currently selected color.
        self.cur_color = None

        # Text color used in the OpenCV window.
        self.text_color = (0, 0, 0)

        # Center position of the detected object.
        self.cx = 0
        self.cy = 0

        # Radius of the detected object.
        self.circle_r = 0

        # Indicates whether the measured distance is valid.
        self.valid_dist = True

        # Indicates whether grasping has finished.
        self.grasp_done = False

        # Message used to publish the fifth joint angle.
        self.joint5 = Int16()

        # Stores the four detected object corners.
        self.corners = np.empty((4, 2), dtype=np.int32)


    # ========================================================
    # 4. TRANSPORT STATUS CALLBACK
    # ========================================================

    # Called when a message arrives on /transport_done.
    def get_TransbotStatusCallBack(self, msg):

        # If transportation is complete...
        if msg.data == True:

            # Reset the tracking system.
            self.Reset()

            # Allow object position information to be published again.
            self.pub_pos_flag = True


    # ========================================================
    # 5. MOVE A SINGLE ROBOT ARM JOINT
    # ========================================================

    def pubSingleArm(self, joint_id, joint_angle, run_time):

        # Create a message for one robot arm joint.
        arm_joint = ArmJoint()

        # Set the target joint angle.
        arm_joint.joint = joint_angle

        # Set the joint ID.
        arm_joint.id = joint_id

        # Set the movement duration.
        arm_joint.time = run_time

        # Publish the joint command.
        self.pub_SingleTargetAngle.publish(arm_joint)


    # ========================================================
    # 6. START TRANSPORT CALLBACK
    # ========================================================

    # Called when a message arrives on /start_transport.
    def get_StartTransportCallBack(self, msg):

        if msg.data == True:

            print("Transbot the tag.")

            # Unload the object only if grasping is complete.
            if self.grasp_done == True:

                self.unload()

                # Display instructions for the next operation.
                print(
                    "Click on the image screen and press the following "
                    "buttons to select the next step: "
                )

                print("n to navigate to the next point")
                print("b to come back to the origin")


    # ========================================================
    # 7. UNLOAD THE OBJECT
    # ========================================================

    def unload(self):

        # Select an unloading joint position according to the color.
        if self.target_color == 1:

            # Red object.
            self.down_joint = [155, 35, 70, 5, 60, 120]

        elif self.target_color == 2:

            # Green object.
            self.down_joint = [180, 35, 60, 0, 90, 120]

        elif self.target_color == 3:

            # Blue object.
            self.down_joint = [28, 30, 70, 2, 90, 120]

        elif self.target_color == 4:

            # Yellow object.
            self.down_joint = [0, 43, 48, 6, 90, 120]

        # Move the arm to the selected unloading position.
        self.pubSixArm(self.down_joint)

        # Wait for the arm to complete the movement.
        time.sleep(2.5)

        # Move the sixth joint to release the object.
        self.pubSingleArm(6, 30, 2000)

        time.sleep(2.5)

        # Return the arm to its initial position.
        self.pubSixArm(self.init_joints)

        time.sleep(2.5)

        # Play a beep to indicate completion.
        self.Beep_Loop()

        # Reset the grasping status.
        self.grasp_done = False

        # Publish the next operation status.
        next_status = Int16()
        next_status.data = 0
        self.pub_status.publish(next_status)

        # Tell the navigation system to return to the origin.
        back_orin = Bool()
        back_orin.data = True
        self.send_back2orin.publish(back_orin)

        # Publish that unloading has finished.
        unload_status = Bool()
        unload_status.data = True
        self.pub_unload_done.publish(unload_status)

        print("Unload done.")


    # ========================================================
    # 8. BEEP SOUND
    # ========================================================

    def Beep_Loop(self):

        # Create a Boolean message.
        beep = Bool()

        # Turn the beep on.
        beep.data = True
        self.pub_beep.publish(beep)

        # Keep it on for one second.
        time.sleep(1.0)

        # Turn the beep off.
        beep.data = False
        self.pub_beep.publish(beep)


    # ========================================================
    # 9. GET CURRENT ROBOT ARM POSITION
    # ========================================================

    def get_current_end_pos(self):

        # Create a request for the kinematics service.
        request = ArmKinemarics.Request()

        # Send the current joint positions.
        request.cur_joint1 = float(self.init_joints[0])
        request.cur_joint2 = float(self.init_joints[1])
        request.cur_joint3 = float(self.init_joints[2])
        request.cur_joint4 = float(self.init_joints[3])
        request.cur_joint5 = float(self.init_joints[4])

        # Request forward kinematics.
        # FK calculates the end-effector position from joint angles.
        request.kin_name = "fk"

        # Send the request asynchronously.
        future = self.client.call_async(request)

        # Call the response callback when the service responds.
        future.add_done_callback(self.get_fk_respone_callback)


    # ========================================================
    # 10. FORWARD KINEMATICS RESPONSE CALLBACK
    # ========================================================

    def get_fk_respone_callback(self, future):

        try:

            # Get the service response.
            response = future.result()

            # Update the robot end-effector position.
            self.CurEndPos[0] = response.x
            self.CurEndPos[1] = response.y
            self.CurEndPos[2] = response.z

            # Update the end-effector orientation.
            self.CurEndPos[3] = response.roll
            self.CurEndPos[4] = response.pitch
            self.CurEndPos[5] = response.yaw

            print("self.CurEndPose: ", self.CurEndPos)

        except Exception as e:

            # Display an error if the service call fails.
            self.get_logger().error(
                f'Service call failed: {e}'
            )


    # ========================================================
    # 11. CAMERA INFORMATION CALLBACK
    # ========================================================

    # Receives camera calibration information.
    def camera_info_callback(self, msg):

        # Convert the camera intrinsic matrix into a 3x3 NumPy array.
        self.camera_matrix = np.array(msg.k).reshape(3, 3)

        # Store the camera distortion coefficients.
        self.dist_coeffs = np.array(msg.d)


    # ========================================================
    # 12. GRASP STATUS CALLBACK
    # ========================================================

    # Called when the robot arm publishes grasp_done.
    def get_graspStatusCallBack(self, msg):

        if msg.data == True:

            # Update the operation status.
            self.done_flag = True

            # Enable distance adjustment again.
            self.adjust_dist = True

            # Mark the grasping operation as complete.
            self.grasp_done = True

            # Return the tracking state to initialization.
            self.Track_state = 'init'

            # Rotate the mobile robot.
            self.pubVel(0, 0, -0.8)

            # Wait for two seconds.
            time.sleep(2.0)

            # Stop the mobile robot.
            self.pubVel(0, 0, 0.0)

            # Reset tracking and color information.
            self.Track_state = 'init'
            self.hsv_range = ()
            self.target_color = 0


    # ========================================================
    # 13. PUBLISH CURRENT JOINT POSITIONS
    # ========================================================

    def pubCurrentJoints(self):

        # Create a message containing the current joint positions.
        cur_joints = CurJoints()

        # Assign the initial joint positions.
        cur_joints.joints = self.init_joints

        # Publish the joint information.
        self.pub_cur_joints.publish(cur_joints)


    # ========================================================
    # 14. MOVE THE ROBOT TOWARD A TARGET DISTANCE
    # ========================================================

    def move_dist(self, dist):

        # Ignore a measurement if it changes too much
        # compared with the previous measurement.
        if abs(self.prev_dist - dist) > 20:

            # Save the new distance for the next comparison.
            self.prev_dist = dist
            return

        # Calculate the required X-axis velocity using PID.
        # The target distance is 200.
        linear_x = self.linearx_pid.compute(dist, 200)

        # Publish the movement command.
        self.pubVel(linear_x, 0, 0)


    # ========================================================
    # 15. MOVE ALL SIX ROBOT ARM JOINTS
    # ========================================================

    def pubSixArm(self, joints, id=6, angle=180.0, runtime=2000):

        # Create a message for all six robot arm joints.
        arm_joints = ArmJoints()

        # Convert the first joint angle to the robot's required format.
        arm_joints.joint1 = 180 - joints[0]

        # Assign the remaining five joint angles.
        arm_joints.joint2 = joints[1]
        arm_joints.joint3 = joints[2]
        arm_joints.joint4 = joints[3]
        arm_joints.joint5 = joints[4]
        arm_joints.joint6 = joints[5]

        # Set the movement duration.
        arm_joints.time = runtime

        # Publish the six-joint command.
        self.pub_SixTargetAngle.publish(arm_joints)


    # ========================================================
    # 16. CALCULATE OBJECT POSITION IN ROBOT COORDINATES
    # ========================================================

    def compute_heigh(self, x, y, z):

        # Convert the image pixel position and depth into
        # a 3D position in the camera coordinate system.
        camera_location = self.pixel_to_camera_depth((x, y), z)

        # Convert the camera position into a transformation matrix.
        PoseEndMat = np.matmul(
            self.EndToCamMat,
            self.xyz_euler_to_mat(
                camera_location,
                (0, 0, 0)
            )
        )

        # Get the transformation matrix of the robot end-effector.
        EndPointMat = self.get_end_point_mat()

        # Transform the object position into the robot/world coordinates.
        WorldPose = np.matmul(EndPointMat, PoseEndMat)

        # Extract the XYZ position and orientation from the matrix.
        pose_T, pose_R = self.mat_to_xyz_euler(WorldPose)

        # Apply the correction offsets from the YAML configuration.
        pose_T[0] = pose_T[0] + self.x_offset
        pose_T[1] = pose_T[1] + self.y_offset
        pose_T[2] = pose_T[2] + self.z_offset

        # Return the corrected 3D position.
        return pose_T


    # ========================================================
    # 17. GET ROBOT END-EFFECTOR TRANSFORMATION MATRIX
    # ========================================================

    def get_end_point_mat(self):

        # Convert the end-effector Euler angles into a quaternion.
        end_w, end_x, end_y, end_z = self.euler_to_quaternion(
            self.CurEndPos[3],
            self.CurEndPos[4],
            self.CurEndPos[5]
        )

        # Combine the XYZ position and quaternion orientation
        # to create a 4x4 transformation matrix.
        endpoint_mat = self.xyz_quat_to_mat(
            [
                self.CurEndPos[0],
                self.CurEndPos[1],
                self.CurEndPos[2]
            ],
            [end_w, end_x, end_y, end_z]
        )

        return endpoint_mat


    # ========================================================
    # 18. CONVERT IMAGE PIXELS INTO 3D CAMERA COORDINATES
    # ========================================================

    def pixel_to_camera_depth(self, pixel_coords, depth):

        # Extract the camera focal lengths and optical center.
        fx = self.camera_info_K[0]
        fy = self.camera_info_K[4]
        cx = self.camera_info_K[2]
        cy = self.camera_info_K[5]

        # Get the pixel coordinates.
        px, py = pixel_coords

        # Calculate the 3D X coordinate.
        x = (px - cx) * depth / fx

        # Calculate the 3D Y coordinate.
        y = (py - cy) * depth / fy

        # The depth value becomes the Z coordinate.
        z = depth

        # Return the 3D camera position.
        return np.array([x, y, z])


    # ========================================================
    # 19. CONVERT XYZ AND EULER ANGLES INTO A MATRIX
    # ========================================================

    def xyz_euler_to_mat(self, xyz, euler, degrees=False):

        # Convert angles from degrees to radians if required.
        if degrees:

            mat = tfs.euler.euler2mat(
                math.radians(euler[0]),
                math.radians(euler[1]),
                math.radians(euler[2])
            )

        else:

            # Otherwise, assume the angles are already in radians.
            mat = tfs.euler.euler2mat(
                euler[0],
                euler[1],
                euler[2]
            )

        # Combine translation and rotation into one transformation matrix.
        mat = tfs.affines.compose(
            np.squeeze(np.asarray(xyz)),
            mat,
            [1, 1, 1]
        )

        return mat


    # ========================================================
    # 20. CONVERT EULER ANGLES INTO A QUATERNION
    # ========================================================

    def euler_to_quaternion(self, roll, pitch, yaw):

        # Convert roll, pitch and yaw into a quaternion.
        quaternion = tf.quaternion_from_euler(
            roll,
            pitch,
            yaw
        )

        # Extract quaternion components.
        qw = quaternion[3]
        qx = quaternion[0]
        qy = quaternion[1]
        qz = quaternion[2]

        # Return the quaternion in w, x, y, z order.
        return np.array([qw, qx, qy, qz])


    # ========================================================
    # 21. CONVERT XYZ AND QUATERNION INTO A MATRIX
    # ========================================================

    def xyz_quat_to_mat(self, xyz, quat):

        # Convert quaternion orientation into a rotation matrix.
        mat = tfs.quaternions.quat2mat(np.asarray(quat))

        # Combine the position and rotation.
        mat = tfs.affines.compose(
            np.squeeze(np.asarray(xyz)),
            mat,
            [1, 1, 1]
        )

        return mat


    # ========================================================
    # 22. CONVERT MATRIX INTO XYZ AND EULER ANGLES
    # ========================================================

    def mat_to_xyz_euler(self, mat, degrees=False):

        # Extract translation and rotation from the transformation matrix.
        t, r, _, _ = tfs.affines.decompose(mat)

        # Convert rotation matrix into Euler angles.
        if degrees:

            # Convert the result into degrees.
            euler = np.degrees(tfs.euler.mat2euler(r))

        else:

            # Keep the result in radians.
            euler = tfs.euler.mat2euler(r)

        # Return position and orientation.
        return t, euler


    # ========================================================
    # 23. CONTROL MOBILE ROBOT MOVEMENT
    # ========================================================

    def robot_move(self, point_x, dist, roll):

        # Convert the roll angle from radians into degrees.
        roll_degree = abs(math.degrees(roll))

        # Display current measurements.
        print("point_x: ", point_x)
        print("dist: ", dist)
        print("roll_degree: ", roll_degree)

        # Ignore large sudden changes in distance.
        if abs(self.prev_dist - dist) > 30:

            self.prev_dist = dist
            return

        # Calculate forward/backward movement using PID.
        linear_x = self.linearx_pid.compute(
            dist,
            self.minDist
        )

        # Set the angular rotation velocity.
        angular_z = -self.rotation_direction * 0.25

        # Set the sideways movement velocity.
        linera_y = self.rotation_direction * 0.1

        # If the measured distance is close enough to the target...
        if abs(dist - self.minDist) < 30:

            # Stop forward/backward movement.
            linear_x = 0

            # Mark X-axis tracking as complete.
            self.x_track_done = True

        # Check whether the object's roll angle is aligned.
        if abs(roll_degree - 175) < 5:

            # Stop angular rotation.
            angular_z = 0

            # Mark roll tracking as complete.
            self.roll_track_done = True

            # Use PID to align the object horizontally.
            linera_y = self.lineary_pid.compute(
                320,
                point_x
            ) * 0.3

            # If the object is close to the image center...
            if abs(point_x - 320) < 5:

                # Stop sideways movement.
                linera_y = 0.0

                # Mark Y-axis tracking as complete.
                self.y_track_done = True

        # Display calculated velocities.
        print("linear_x: ", linear_x)
        print("linear_y: ", linera_y)
        print("angular_z: ", angular_z)

        # Publish the movement command.
        self.pubVel(linear_x, linera_y, angular_z)

        # Check whether all three alignment stages are complete.
        if (
            self.x_track_done == True
            and self.roll_track_done == True
            and self.y_track_done == True
        ):

            print("adjust dist to grasp it.")

            # Stop the main tracking process.
            self.track_flag = False

            # Enable the final distance adjustment.
            self.adjust_dist = True


    # ========================================================
    # 24. PUBLISH MOBILE ROBOT VELOCITY
    # ========================================================

    def pubVel(self, vx, vy, vz):

        # Create a Twist message for robot movement.
        vel = Twist()

        # Linear velocity along X.
        vel.linear.x = float(vx)

        # Linear velocity along Y.
        vel.linear.y = float(vy)

        # Angular velocity around Z.
        vel.angular.z = float(vz)

        # Publish the movement command.
        self.CmdVel_pub.publish(vel)


    # ========================================================
    # 25. RESET COLOR TRACKING
    # ========================================================

    def Reset(self):

        # Clear the selected HSV color range.
        self.hsv_range = ()

        # Reset the detected circle.
        self.circle = (0, 0, 0)

        # Reset the mouse position.
        self.Mouse_XY = (0, 0)

        # Return to the initialization state.
        self.Track_state = 'init'

        print("Change the state.")

        # Reset the detected object center.
        self.cx = 0
        self.cy = 0

        # Disable publishing object position.
        self.pubPos_flag = False

        # Stop the mobile robot.
        self.pubVel(0, 0, 0)

        # Clear the selected target color.
        self.target_color = 0


    # ========================================================
    # 26. DISPLAY CAMERA IMAGES
    # ========================================================

    def img_out(self, result_frame, binary):

        # If a binary image exists, display both images together.
        if len(binary) != 0:

            cv.imshow(
                self.windows_name,
                ManyImgs(1, ([result_frame, binary]))
            )

        else:

            # Otherwise, display only the processed camera image.
            cv.imshow(
                self.windows_name,
                result_frame
            )


    # ========================================================
    # 27. HANDLE MOUSE EVENTS
    # ========================================================

    def onMouse(self, event, x, y, flags, param):

        # Event 1 represents the left mouse button being pressed.
        if event == 1:

            # Return to the initialization state.
            self.Track_state = 'init'

            # Enable region selection.
            self.select_flags = True

            # Save the initial mouse position.
            self.Mouse_XY = (x, y)

        # Event 4 represents the left mouse button being released.
        if event == 4:

            # Finish selecting the image region.
            self.select_flags = False

            # Change the tracking state.
            self.Track_state = 'mouse'

        # While the user is selecting an image region...
        if self.select_flags == True:

            # Calculate the upper-left corner.
            self.cols = (
                min(self.Mouse_XY[0], x),
                min(self.Mouse_XY[1], y)
            )

            # Calculate the lower-right corner.
            self.rows = (
                max(self.Mouse_XY[0], x),
                max(self.Mouse_XY[1], y)
            )

            # Store the complete region of interest.
            self.Roi_init = (
                self.cols[0],
                self.cols[1],
                self.rows[0],
                self.rows[1]
            )


    # ========================================================
    # 28. MAIN CAMERA CALLBACK
    # ========================================================

    # This function runs whenever synchronized RGB and depth images arrive.
    def callback(self, color_frame, depth_frame):

        # ----------------------------------------------------
        # 28.1 CONVERT ROS IMAGES INTO OPENCV IMAGES
        # ----------------------------------------------------

        # Convert the ROS RGB image message into an OpenCV image.
        rgb_image = self.rgb_bridge.imgmsg_to_cv2(
            color_frame,
            'rgb8'
        )

        # Convert RGB color order into BGR for OpenCV.
        rgb_image = cv2.cvtColor(
            rgb_image,
            cv2.COLOR_RGB2BGR
        )

        # Create a copy of the original image.
        result_image = np.copy(rgb_image)

        # Convert the ROS depth image message into an OpenCV image.
        depth_image = self.depth_bridge.imgmsg_to_cv2(
            depth_frame,
            encoding[1]
        )

        # Resize the depth image to 640 x 480.
        frame = cv.resize(
            depth_image,
            (640, 480)
        )

        # Convert depth values into a color visualization.
        depth_to_color_image = cv2.applyColorMap(
            cv2.convertScaleAbs(depth_image, alpha=1.0),
            cv2.COLORMAP_JET
        )

        # Convert the depth image into float32 format.
        depth_image_info = frame.astype(np.float32)

        # Read keyboard input from the OpenCV window.
        key = cv2.waitKey(10) & 0xFF

        # Process the RGB image and detect the selected color.
        result_frame, binary = self.process(
            rgb_image,
            key
        )

        # Create a separate thread to display the processed image.
        show_frame = threading.Thread(
            target=self.img_out,
            args=(result_frame, binary,)
        )

        # Start the image display thread.
        show_frame.start()

        # Wait until the display thread finishes.
        show_frame.join()

        # ----------------------------------------------------
        # 28.2 CALCULATE OBJECT POSITION
        # ----------------------------------------------------

        # Continue only when position publishing is enabled.
        if self.pub_pos_flag:

            # Check whether a valid object center and circle were detected.
            if (
                self.cx != 0
                and self.cy != 0
                and self.circle_r > 30
            ):

                # Convert object center coordinates into integers.
                cx = int(self.cx)
                cy = int(self.cy)

                # Read the depth value at the detected object center.
                # Divide by 1000 to convert millimeters into meters
                # when the depth camera provides millimeter values.
                dist = depth_image_info[int(cy), int(cx)] / 1000

                # Convert the camera measurement into robot coordinates.
                pose = self.compute_heigh(
                    cx,
                    cy,
                    dist
                )

                # Calculate the horizontal distance from the robot origin.
                dist_detect = math.sqrt(
                    pose[1] ** 2 + pose[0] ** 2
                )

                # Convert meters into millimeters.
                dist_detect = dist_detect * 1000

                # Reject measurements that are too close.
                if dist_detect < 130:

                    print("Invalid dist.")

                    self.valid_dist = False

                # Prepare a readable distance message.
                dist = 'dist: ' + str(dist_detect) + ' mm'

                print("dist: ", dist)

                # ------------------------------------------------
                # 28.3 ADJUST THE ROBOT DISTANCE
                # ------------------------------------------------

                # If the robot is not at the target distance,
                # distance adjustment is enabled, and the measurement
                # is valid, move the robot toward the target.
                if (
                    abs(dist_detect - 200.0) > 10
                    and self.adjust_dist == True
                    and self.valid_dist == True
                ):

                    self.move_dist(dist_detect)

                else:

                    # Stop the mobile robot.
                    self.pubVel(0, 0, 0)

                    # Disable further distance adjustment.
                    self.adjust_dist = False

                    # Read the current depth value again.
                    cx = int(self.cx)
                    cy = int(self.cy)

                    dist = depth_image_info[int(cy), int(cx)] / 1000

                    # ------------------------------------------------
                    # 28.4 PREPARE OBJECT INFORMATION FOR THE ARM
                    # ------------------------------------------------

                    # Continue only if the depth measurement is non-zero.
                    if dist != 0:

                        # Calculate the horizontal and vertical
                        # differences between two detected corners.
                        vx = (
                            self.corners[0][0][0]
                            - self.corners[1][0][0]
                        )

                        vy = (
                            self.corners[0][0][1]
                            - self.corners[1][0][1]
                        )

                        # Calculate the required fifth joint angle.
                        target_joint5 = compute_joint5(vx, vy)

                        # Store the angle in an Int16 message.
                        self.joint5.data = int(target_joint5)

                        # Create an AprilTagInfo message.
                        pos = AprilTagInfo()

                        # Store the selected color ID.
                        pos.id = self.target_color

                        # Store the object's image X coordinate.
                        pos.x = float(cx)

                        # Store the object's image Y coordinate.
                        pos.y = float(cy)

                        # Store the object's depth in meters.
                        pos.z = float(dist)

                        # Prevent the same object position
                        # from being published repeatedly.
                        self.pub_pos_flag = False

                        # Mark the current operation as not yet complete.
                        self.done_flag = False

                        # Publish the object's position for the arm controller.
                        self.pos_info_pub.publish(pos)

                        # Publish the calculated fifth joint angle.
                        self.TargetJoint5_pub.publish(self.joint5)

            else:

                # If no valid object is detected, stop the robot.
                self.pubVel(0, 0, 0)


    # ========================================================
    # 29. COLOR DETECTION AND IMAGE PROCESSING
    # ========================================================

    def process(self, rgb_img, key):

        # Resize the camera image to 640 x 480.
        rgb_img = cv.resize(
            rgb_img,
            (640, 480)
        )

        # This list will contain the binary image returned
        # by the color detection function.
        binary = []

        # ----------------------------------------------------
        # 29.1 KEYBOARD CONTROLS
        # ----------------------------------------------------

        # Press C to reset color tracking.
        if key == ord('c') or key == ord('C'):

            self.Reset()

        # Press R to select red.
        elif key == ord('r') or key == ord('R'):

            self.target_color = 1

        # Press G to select green.
        elif key == ord('g') or key == ord('G'):

            self.target_color = 2

        # Press B to select blue.
        elif key == ord('b') or key == ord('B'):

            self.target_color = 3

        # Press Y to select yellow.
        elif key == ord('y') or key == ord('Y'):

            self.target_color = 4

        # Press I to identify the selected color.
        # Color identification also starts automatically
        # when target_color is not zero.
        elif (
            key == ord('i')
            or key == ord('I')
            or self.target_color != 0
        ):

            self.Track_state = "identify"

        # ----------------------------------------------------
        # 29.2 INITIALIZATION AND REGION SELECTION
        # ----------------------------------------------------

        if self.Track_state == 'init':

            # Create the OpenCV display window.
            cv.namedWindow(
                self.windows_name,
                cv.WINDOW_AUTOSIZE
            )

            # Register the mouse callback.
            cv.setMouseCallback(
                self.windows_name,
                self.onMouse,
                0
            )

            # If the user is selecting an image region...
            if self.select_flags == True:

                # Draw a line showing the selected region.
                cv.line(
                    rgb_img,
                    self.cols,
                    self.rows,
                    (255, 0, 0),
                    2
                )

                # Draw a rectangle around the selected region.
                cv.rectangle(
                    rgb_img,
                    self.cols,
                    self.rows,
                    (0, 255, 0),
                    2
                )

                # Check that the selected region has a non-zero size.
                if (
                    self.Roi_init[0] != self.Roi_init[2]
                    and self.Roi_init[1] != self.Roi_init[3]
                ):

                    # Extract the HSV color range from the selected region.
                    rgb_img, self.hsv_range = self.color.Roi_hsv(
                        rgb_img,
                        self.Roi_init
                    )

                    # Enable the color tracker.
                    self.gTracker_state = True

                    # Enable dynamic updating.
                    self.dyn_update = True

                else:

                    # Keep the system in initialization state.
                    self.Track_state = 'init'

        # ----------------------------------------------------
        # 29.3 LOAD THE HSV RANGE FOR THE SELECTED COLOR
        # ----------------------------------------------------

        elif self.Track_state == "identify":

            # Load the saved HSV range for red.
            if self.target_color == 1:

                self.hsv_range = read_HSV(
                    self.red_hsv_text
                )

                self.cur_color = "red"
                self.text_color = (0, 0, 255)

            # Load the saved HSV range for green.
            elif self.target_color == 2:

                self.hsv_range = read_HSV(
                    self.green_hsv_text
                )

                self.cur_color = "green"
                self.text_color = (0, 255, 0)

            # Load the saved HSV range for blue.
            elif self.target_color == 3:

                self.hsv_range = read_HSV(
                    self.blue_hsv_text
                )

                self.cur_color = "blue"
                self.text_color = (255, 0, 0)

            # Load the saved HSV range for yellow.
            elif self.target_color == 4:

                self.hsv_range = read_HSV(
                    self.yellow_hsv_text
                )

                self.cur_color = "yellow"
                self.text_color = (255, 255, 0)

            else:

                # If no valid color is selected, return to initialization.
                self.Track_state = 'init'

        # ----------------------------------------------------
        # 29.4 TRACK THE SELECTED COLOR
        # ----------------------------------------------------

        # Continue processing if the system is not in initialization.
        if self.Track_state != 'init':

            # Check whether an HSV range is available.
            if len(self.hsv_range) != 0:

                # Detect and track the selected colored object.
                # The function returns:
                # - Processed image.
                # - Binary mask.
                # - Detected circle.
                # - Additional result.
                # - Detected object corners.
                (
                    rgb_img,
                    binary,
                    self.circle,
                    _,
                    self.corners
                ) = self.color.object_follow(
                    rgb_img,
                    self.hsv_range
                )

                # Display the current HSV configuration.
                print("self.hsv_range: ", self.hsv_range)

                # Display the selected color ID.
                print("self.target_color: ", self.target_color)

                # Store the detected object center.
                self.cx = self.circle[0]
                self.cy = self.circle[1]

                # Store the detected circle radius.
                self.circle_r = self.circle[2]

                # ------------------------------------------------
                # 29.5 SAVE THE HSV CONFIGURATION
                # ------------------------------------------------

                # Save the current red HSV range.
                if self.target_color == 1:

                    write_HSV(
                        self.red_hsv_text,
                        self.hsv_range
                    )

                # Save the current green HSV range.
                elif self.target_color == 2:

                    write_HSV(
                        self.green_hsv_text,
                        self.hsv_range
                    )

                # Save the current blue HSV range.
                elif self.target_color == 3:

                    write_HSV(
                        self.blue_hsv_text,
                        self.hsv_range
                    )

                # Save the current yellow HSV range.
                elif self.target_color == 4:

                    write_HSV(
                        self.yellow_hsv_text,
                        self.hsv_range
                    )

        # ----------------------------------------------------
        # 29.6 DISPLAY THE SELECTED COLOR NAME
        # ----------------------------------------------------

        # Write the selected color name on the camera image.
        rgb_img = cv2.putText(
            rgb_img,
            self.cur_color,
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            self.text_color,
            2
        )

        # Return the processed image and binary mask.
        return rgb_img, binary


# ============================================================
# 30. MAIN FUNCTION
# ============================================================

def main():

    # Display a separator in the terminal.
    print('----------------------')

    # Initialize the ROS 2 communication system.
    rclpy.init()

    # Create an instance of the ColorRecognizeNode.
    color_recognize = ColorRecognizeNode(
        'ColorRecognize_node'
    )

    # Keep the node running and process ROS 2 callbacks.
    rclpy.spin(color_recognize)


# ============================================================
# 31. START THE PROGRAM
# ============================================================

# Run main() when this Python file is executed directly.
if __name__ == '__main__':
    main()
