
# ============================================================
# 1. IMPORTING REQUIRED LIBRARIES
# ============================================================

# OpenCV: Image processing, shape detection, drawing and display.
import cv2

# Operating system functions, such as working with file paths.
import os

# NumPy: Mathematical operations and image data processing.
import numpy as np

# ROS 2 camera message types.
from sensor_msgs.msg import Image, CameraInfo

# Message filters allow us to synchronize messages from multiple topics.
import message_filters

# Helper functions for drawing tags.
from M3Pro_demo.vutils import draw_tags

# AprilTag detector library.
from dt_apriltags import Detector

# Converts ROS 2 images into OpenCV images.
from cv_bridge import CvBridge

# Import OpenCV again using the shorter name cv.
import cv2 as cv

# Import robot movement functions.
from M3Pro_demo.Robot_Move import *

# Import pose calculation and transformation functions.
from M3Pro_demo.compute_pose import *

# Import the robot arm kinematics service.
from arm_interface.srv import ArmKinemarics

# Import custom messages for AprilTag information and current joints.
from arm_interface.msg import AprilTagInfo, CurJoints

# Import the robot arm joint command message.
from arm_msgs.msg import ArmJoints

# Import standard ROS 2 message types.
from std_msgs.msg import Float32, Bool, Int16

# Supported depth image encodings:
# 16UC1 = 16-bit unsigned integer depth image.
# 32FC1 = 32-bit floating-point depth image.
encoding = ['16UC1', '32FC1']

# Time-related functions.
import time

# Transforms3d provides mathematical tools for 3D transformations.
import transforms3d as tfs

# tf_transformations provides functions for working with quaternions.
import tf_transformations as tf

# YAML is used to read configuration values from a YAML file.
import yaml

# Math provides mathematical functions such as sqrt, pi and radians.
import math

# ROS 2 Node class.
from rclpy.node import Node

# ROS 2 Python client library.
import rclpy

# Import message-filter subscriber and synchronization tools.
from message_filters import (
    Subscriber,
    TimeSynchronizer,
    ApproximateTimeSynchronizer
)

# ROS 2 velocity command message.
from geometry_msgs.msg import Twist

# Import functions for calculating the robot's fifth joint angle.
from M3Pro_demo.compute_joint5 import *


# ============================================================
# 2. LOAD ROBOT ARM OFFSET CONFIGURATION
# ============================================================

# Path to the YAML file containing the robot arm position offsets.
# These offsets are used to correct the calculated object position.
offset_file = "/home/jetson/yahboomcar_ws/src/arm_kin/param/offset_value.yaml"

# Open the YAML file in read mode.
with open(offset_file, 'r') as file:

    # Read the YAML configuration and convert it into a Python dictionary.
    offset_config = yaml.safe_load(file)

# Print the complete configuration dictionary.
print(offset_config)

print("----------------------------")

# Read and print the X-axis correction value.
print("x_offset: ", offset_config.get('x_offset'))

# Read and print the Y-axis correction value.
print("y_offset: ", offset_config.get('y_offset'))

# Read and print the Z-axis correction value.
print("z_offset: ", offset_config.get('z_offset'))

print('init done')


# ============================================================
# 3. CREATE THE SHAPE RECOGNITION ROS 2 NODE
# ============================================================

class ShapeRecognizeNode(Node):

    def __init__(self, name):

        # Initialize the parent ROS 2 Node class.
        super().__init__(name)

        # ----------------------------------------------------
        # INITIAL ROBOT ARM CONFIGURATION
        # ----------------------------------------------------

        # Initial positions of the six robot arm joints.
        self.init_joints = [90, 90, 0, 0, 90, 90]

        # Another initial joint configuration using floating-point values.
        self.init_joints_float = [90.0, 150.0, 12.0, 20.0, 90.0, 0.0]

        # ----------------------------------------------------
        # IMAGE CONVERSION
        # ----------------------------------------------------

        # CvBridge for converting RGB camera images.
        self.rgb_bridge = CvBridge()

        # CvBridge for converting depth camera images.
        self.depth_bridge = CvBridge()

        # Controls whether the detected object's position can be published.
        # Initially False, so object-position processing is disabled.
        self.pub_pos_flag = False

        # Store the current time.
        self.pr_time = time.time()

        # Counter variable.
        self.cnt = 0

        # Current measured distance.
        self.cur_distance = 0.0

        # Flag for enabling or disabling robot tracking.
        self.track_flag = True

        # Previous measured distance.
        self.prev_dist = 0

        # Previous angular value.
        self.prev_angular = 0

        # Previous roll angle.
        self.prev_roll = 0

        # Minimum target distance used by the movement controller.
        self.minDist = 400

        # Target distance for grasping.
        self.grasp_Dist = 250

        # Enables or disables XY tracking.
        self.xy_track_flag = True

        # PID controller parameters for X-axis movement.
        self.linearx_PID = (0.5, 0.0, 0.2)

        # PID controller parameters for Y-axis movement.
        self.lineary_PID = (0.2, 0.0, 0.1)

        # PID controller parameters for angular movement.
        self.angz_PID = (0.5, 0.0, 0.5)

        # ----------------------------------------------------
        # APRILTAG DETECTOR CONFIGURATION
        # ----------------------------------------------------

        # Create an AprilTag detector.
        # This detector is configured to recognize tag36h11 markers.
        self.at_detector = Detector(
            searchpath=['apriltags'],
            families='tag36h11',

            # Number of threads used for detection.
            nthreads=8,

            # Reduce image resolution for faster detection.
            quad_decimate=2.0,

            # No additional Gaussian blur.
            quad_sigma=0.0,

            # Enable edge refinement.
            refine_edges=1,

            # Sharpening parameter for decoding.
            decode_sharpening=0.25,

            # Disable detector debugging output.
            debug=0
        )

        # ----------------------------------------------------
        # ROBOT END-EFFECTOR POSITION
        # ----------------------------------------------------

        # Initial estimated end-effector position.
        #
        # Format:
        # [X, Y, Z, Roll, Pitch, Yaw]
        #
        # Position values are generally expressed in metres.
        # Orientation values are generally expressed in radians.
        self.CurEndPos = [
            0.1279009179959246,
            0.00023254956548456117,
            0.1484898062979958,
            0.00036263794618046863,
            1.3962632350758744,
            0.0003332603981328959
        ]

        # Camera intrinsic matrix values.
        #
        # fx = focal length in X direction.
        # fy = focal length in Y direction.
        # cx = optical centre X coordinate.
        # cy = optical centre Y coordinate.
        #
        # These values are used to convert image pixels
        # into 3D camera coordinates.
        self.camera_info_K = [
            477.57421875, 0.0, 319.3820495605469,
            0.0, 477.55718994140625, 238.64108276367188,
            0.0, 0.0, 1.0
        ]

        # Transformation matrix between the end-effector and camera.
        #
        # A transformation matrix describes the position and
        # orientation of one coordinate frame relative to another.
        #
        # The upper-left 3x3 section represents rotation.
        # The last column represents translation.
        self.EndToCamMat = np.array([
            [0, 0, 1, -1.00e-01],
            [-1, 0, 0, 0],
            [0, -1, 0, 4.82000000e-02],
            [0.00000000e+00, 0.00000000e+00,
             0.00000000e+00, 1.00000000e+00]
        ])

        # ----------------------------------------------------
        # CAMERA SUBSCRIBERS
        # ----------------------------------------------------

        # Subscribe to the RGB camera topic.
        # Subscriber from message_filters allows synchronization
        # with the depth camera topic.
        self.rgb_image_sub = Subscriber(
            self,
            Image,
            '/camera/color/image_raw'
        )

        # Subscribe to the grasp completion status.
        # When the arm finishes grasping, the callback is called.
        self.sub_grasp_status = self.create_subscription(
            Bool,
            "grasp_done",
            self.get_graspStatusCallBack,
            100
        )

        # Subscribe to the depth camera topic.
        self.depth_image_sub = Subscriber(
            self,
            Image,
            '/camera/depth/image_raw'
        )

        # ----------------------------------------------------
        # ROS 2 PUBLISHERS
        # ----------------------------------------------------

        # Publisher for controlling the mobile robot's velocity.
        self.CmdVel_pub = self.create_publisher(
            Twist,
            "cmd_vel",
            1
        )

        # Publisher for the current robot arm joint positions.
        self.pub_cur_joints = self.create_publisher(
            CurJoints,
            "Curjoints",
            1
        )

        # Publisher for AprilTag position information.
        self.pos_info_pub = self.create_publisher(
            AprilTagInfo,
            "PosInfo",
            1
        )

        # Publisher for sending target angles to all six arm joints.
        self.pub_SixTargetAngle = self.create_publisher(
            ArmJoints,
            "arm6_joints",
            10
        )

        # ----------------------------------------------------
        # KINEMATICS SERVICE CLIENT
        # ----------------------------------------------------

        # Create a client for the robot arm kinematics service.
        # The service name is 'get_kinemarics'.
        self.client = self.create_client(
            ArmKinemarics,
            'get_kinemarics'
        )

        # Wait until the kinematics service becomes available.
        # The loop checks once every second.
        while not self.client.wait_for_service(timeout_sec=1.0):

            self.get_logger().info(
                'Service not available, waiting again...'
            )

        # Request the current end-effector position using
        # Forward Kinematics (FK).
        self.get_current_end_pos()

        # Wait until a subscriber is connected to the arm joint topic.
        # Until then, repeatedly publish the initial joint positions.
        while not self.pub_SixTargetAngle.get_subscription_count():

            self.pubSixArm(self.init_joints)

            time.sleep(0.1)

        # Send the initial arm position.
        self.pubSixArm(self.init_joints)

        # ----------------------------------------------------
        # ADDITIONAL PUBLISHERS
        # ----------------------------------------------------

        # Publisher for controlling the robot's buzzer.
        self.pub_beep = self.create_publisher(
            Bool,
            "beep",
            10
        )

        # Publisher for controlling the fifth joint separately.
        self.TargetJoint5_pub = self.create_publisher(
            Int16,
            "set_joint5",
            10
        )

        # Send the initial joint position again.
        self.pubSixArm(self.init_joints)

        # ----------------------------------------------------
        # CAMERA INFORMATION SUBSCRIBER
        # ----------------------------------------------------

        # Subscribe to the RGB camera calibration information.
        self.camera_info_sub = self.create_subscription(
            CameraInfo,
            '/camera/color/camera_info',
            self.camera_info_callback,
            10
        )

        # ----------------------------------------------------
        # SYNCHRONIZE RGB AND DEPTH IMAGES
        # ----------------------------------------------------

        # ApproximateTimeSynchronizer allows RGB and depth images
        # with slightly different timestamps to be processed together.
        #
        # Parameters:
        #   [rgb_image_sub, depth_image_sub] = topics to synchronize.
        #   1 = message queue size.
        #   0.5 = maximum allowed timestamp difference in seconds.
        self.ts = ApproximateTimeSynchronizer(
            [self.rgb_image_sub, self.depth_image_sub],
            1,
            0.5
        )

        # Register the callback that processes both images together.
        self.ts.registerCallback(self.callback)

        # Publish the initial joint information.
        self.pubCurrentJoints()

        # Physical size of the AprilTag in metres.
        self.tag_size = 0.05

        # Variables for storing camera calibration information.
        self.camera_matrix = None
        self.dist_coeffs = None

        # Direction used for robot rotation.
        self.rotation_direction = 1

        # Enables or disables roll tracking.
        self.roll_track_flag = True

        # Indicates whether the grasp process has started.
        self.start_grasp = False

        # Enables Y-axis movement.
        self.move_y = True

        # Create an object for calculating poses and distances.
        self.compute_dist = ComputePose("compute_dist")

        # Direction used for X-axis movement.
        self.x_direction = 1

        # Tracking flags for roll movement.
        self.x_roll_track_flag = True
        self.y_roll_track_flag = False

        # Flags indicating whether each tracking stage is complete.
        self.x_track_done = False
        self.roll_track_done = False
        self.y_track_done = False

        # Target shape to recognize.
        # Available shapes: Rectangle, Square and Cylinder.
        self.Target_Shape = "Cylinder"

        # Load position correction values from the YAML configuration.
        self.x_offset = offset_config.get('x_offset')
        self.y_offset = offset_config.get('y_offset')
        self.z_offset = offset_config.get('z_offset')

        # Enable distance adjustment.
        self.adjust_dist = True

        # Reset previous distance.
        self.prev_dist = 0

        # PID controller parameters for X-axis movement.
        self.linearx_PID = (0.5, 0.0, 0.2)

        # Create the actual PID controller.
        # The parameters are divided by 1000 before being passed in.
        self.linearx_pid = simplePID(
            self.linearx_PID[0] / 1000.0,
            self.linearx_PID[1] / 1000.0,
            self.linearx_PID[2] / 1000.0
        )

        # Target distance for grasping.
        self.grasp_Dist = 220.0

        # Indicates whether the robot is ready for another operation.
        self.done_flag = True

        # Create an Int16 message for the fifth joint.
        self.joint5 = Int16()

        # Store the detected object's contour corner points.
        self.corners = np.empty((4, 2), dtype=np.int32)

        # Indicates whether the measured distance is valid.
        self.valid_dist = True

        print("Init done.")


    # ========================================================
    # 4. BUZZER CONTROL
    # ========================================================

    def Beep_Loop(self):

        # Create a Bool message.
        beep = Bool()

        # Turn the buzzer ON.
        beep.data = True
        self.pub_beep.publish(beep)

        # Keep the buzzer on for one second.
        time.sleep(1.0)

        # Turn the buzzer OFF.
        beep.data = False
        self.pub_beep.publish(beep)


    # ========================================================
    # 5. GET CURRENT END-EFFECTOR POSITION USING FK
    # ========================================================

    def get_current_end_pos(self):

        # Create a request for the arm kinematics service.
        request = ArmKinemarics.Request()

        # Send the current joint positions to the service.
        request.cur_joint1 = float(self.init_joints[0])
        request.cur_joint2 = float(self.init_joints[1])
        request.cur_joint3 = float(self.init_joints[2])
        request.cur_joint4 = float(self.init_joints[3])
        request.cur_joint5 = float(self.init_joints[4])

        # Tell the service that we want Forward Kinematics.
        request.kin_name = "fk"

        # Send the service request asynchronously.
        # This allows the node to continue running without
        # waiting for the service response immediately.
        future = self.client.call_async(request)

        # When the service responds, execute the callback.
        future.add_done_callback(self.get_fk_respone_callback)


    # ========================================================
    # 6. RECEIVE FORWARD KINEMATICS RESPONSE
    # ========================================================

    def get_fk_respone_callback(self, future):

        try:

            # Get the service response.
            response = future.result()

            # Store the calculated X position.
            self.CurEndPos[0] = response.x

            # Store the calculated Y position.
            self.CurEndPos[1] = response.y

            # Store the calculated Z position.
            self.CurEndPos[2] = response.z

            # Store the calculated roll angle.
            self.CurEndPos[3] = response.roll

            # Store the calculated pitch angle.
            self.CurEndPos[4] = response.pitch

            # Store the calculated yaw angle.
            self.CurEndPos[5] = response.yaw

            # Print the complete end-effector position.
            print("self.CurEndPose: ", self.CurEndPos)

        except Exception as e:

            # Display an error if the service request fails.
            self.get_logger().error(
                f'Service call failed: {e}'
            )


    # ========================================================
    # 7. CAMERA CALIBRATION CALLBACK
    # ========================================================

    def camera_info_callback(self, msg):

        # Extract the camera intrinsic matrix from CameraInfo.
        # msg.k contains nine values, which are reshaped into 3x3.
        self.camera_matrix = np.array(msg.k).reshape(3, 3)

        # Store the camera lens distortion coefficients.
        self.dist_coeffs = np.array(msg.d)


    # ========================================================
    # 8. GRASP STATUS CALLBACK
    # ========================================================

    def get_graspStatusCallBack(self, msg):

        # Check whether the grasp operation has completed.
        if msg.data == True:

            # Indicate that the operation is complete.
            self.done_flag = True

            # Allow object-position processing again.
            self.pub_pos_flag = True

            # Ask the user which shape should be targeted.
            # Available choices: Rectangle, Square and Cylinder.
            self.Target_Shape = input(
                "Please enter a target shape, which can be selected "
                "from Rectangle  Square  Cylinder："
            )


    # ========================================================
    # 9. PUBLISH CURRENT JOINT POSITIONS
    # ========================================================

    def pubCurrentJoints(self):

        # Create a CurJoints message.
        cur_joints = CurJoints()

        # Assign the initial joint positions to the message.
        cur_joints.joints = self.init_joints

        # Publish the joint positions.
        self.pub_cur_joints.publish(cur_joints)


    # ========================================================
    # 10. CONTROL ROBOT MOVEMENT USING DISTANCE
    # ========================================================

    def move_dist(self, dist):

        # Compare the current distance with the previous distance.
        #
        # If the difference is greater than 20, update the previous
        # distance and skip this movement calculation.
        #
        # This helps reject sudden changes in measured distance.
        if abs(self.prev_dist - dist) > 20:

            self.prev_dist = dist
            return

        # Calculate the required X-axis velocity using the PID controller.
        # The target distance is 200.
        linear_x = self.linearx_pid.compute(dist, 200)

        # Publish the movement command.
        # X = forward/backward, Y = sideways, Z = rotation.
        self.pubVel(linear_x, 0, 0)


    # ========================================================
    # 11. PUBLISH SIX ROBOT ARM JOINT ANGLES
    # ========================================================

    def pubSixArm(self, joints, id=6, angle=180.0, runtime=2000):

        # Create an ArmJoints message.
        arm_joints = ArmJoints()

        # Convert the first joint angle using 180 - joints[0].
        arm_joints.joint1 = 180 - joints[0]

        # Assign the remaining five joint angles.
        arm_joints.joint2 = joints[1]
        arm_joints.joint3 = joints[2]
        arm_joints.joint4 = joints[3]
        arm_joints.joint5 = joints[4]
        arm_joints.joint6 = joints[5]

        # Set the movement duration.
        arm_joints.time = runtime

        # Publish the target angles to the robot arm.
        self.pub_SixTargetAngle.publish(arm_joints)


    # ========================================================
    # 12. CALCULATE OBJECT POSITION IN WORLD COORDINATES
    # ========================================================

    def compute_heigh(self, x, y, z):

        # Convert the image pixel coordinate and depth value
        # into a 3D position in the camera coordinate frame.
        camera_location = self.pixel_to_camera_depth((x, y), z)

        # Convert the camera position into a transformation matrix.
        # The rotation is initially set to (0, 0, 0).
        PoseEndMat = np.matmul(
            self.EndToCamMat,
            self.xyz_euler_to_mat(camera_location, (0, 0, 0))
        )

        # Get the current end-effector transformation matrix.
        EndPointMat = self.get_end_point_mat()

        # Transform the camera-relative position into the world frame.
        WorldPose = np.matmul(EndPointMat, PoseEndMat)

        # Convert the transformation matrix back into:
        #   pose_T = translation [X, Y, Z]
        #   pose_R = orientation [Roll, Pitch, Yaw]
        pose_T, pose_R = self.mat_to_xyz_euler(WorldPose)

        # Apply the configured X-axis correction.
        pose_T[0] = pose_T[0] + self.x_offset

        # Apply the configured Y-axis correction.
        pose_T[1] = pose_T[1] + self.y_offset

        # Apply the configured Z-axis correction.
        pose_T[2] = pose_T[2] + self.z_offset

        # Return the corrected 3D position.
        return pose_T


    # ========================================================
    # 13. GET END-EFFECTOR TRANSFORMATION MATRIX
    # ========================================================

    def get_end_point_mat(self):

        # Convert the current end-effector Euler angles
        # (roll, pitch, yaw) into a quaternion.
        end_w, end_x, end_y, end_z = self.euler_to_quaternion(
            self.CurEndPos[3],
            self.CurEndPos[4],
            self.CurEndPos[5]
        )

        # Combine the end-effector translation and quaternion
        # to create a 4x4 transformation matrix.
        endpoint_mat = self.xyz_quat_to_mat(
            [
                self.CurEndPos[0],
                self.CurEndPos[1],
                self.CurEndPos[2]
            ],
            [end_w, end_x, end_y, end_z]
        )

        # Return the transformation matrix.
        return endpoint_mat


    # ========================================================
    # 14. CONVERT IMAGE PIXEL INTO 3D CAMERA COORDINATES
    # ========================================================

    def pixel_to_camera_depth(self, pixel_coords, depth):

        # Extract camera intrinsic parameters.
        fx = self.camera_info_K[0]
        fy = self.camera_info_K[4]
        cx = self.camera_info_K[2]
        cy = self.camera_info_K[5]

        # Get the pixel coordinates.
        px, py = pixel_coords

        # Calculate the X coordinate in the camera frame.
        x = (px - cx) * depth / fx

        # Calculate the Y coordinate in the camera frame.
        y = (py - cy) * depth / fy

        # The depth value becomes the Z coordinate.
        z = depth

        # Return the 3D camera position as a NumPy array.
        return np.array([x, y, z])


    # ========================================================
    # 15. CONVERT XYZ AND EULER ANGLES INTO A MATRIX
    # ========================================================

    def xyz_euler_to_mat(self, xyz, euler, degrees=False):

        # If the input angles are in degrees, convert them into radians.
        if degrees:

            mat = tfs.euler.euler2mat(
                math.radians(euler[0]),
                math.radians(euler[1]),
                math.radians(euler[2])
            )

        else:

            # Otherwise, use the input angles directly as radians.
            mat = tfs.euler.euler2mat(
                euler[0],
                euler[1],
                euler[2]
            )

        # Combine translation and rotation into a 4x4 affine matrix.
        mat = tfs.affines.compose(
            np.squeeze(np.asarray(xyz)),
            mat,
            [1, 1, 1]
        )

        # Return the transformation matrix.
        return mat


    # ========================================================
    # 16. CONVERT EULER ANGLES INTO A QUATERNION
    # ========================================================

    def euler_to_quaternion(self, roll, pitch, yaw):

        # Convert roll, pitch and yaw into a quaternion.
        quaternion = tf.quaternion_from_euler(
            roll,
            pitch,
            yaw
        )

        # Extract quaternion components.
        # tf_transformations returns them in [x, y, z, w] order.
        qw = quaternion[3]
        qx = quaternion[0]
        qy = quaternion[1]
        qz = quaternion[2]

        # Return the quaternion in [w, x, y, z] order.
        return np.array([qw, qx, qy, qz])


    # ========================================================
    # 17. CONVERT XYZ AND QUATERNION INTO A MATRIX
    # ========================================================

    def xyz_quat_to_mat(self, xyz, quat):

        # Convert the quaternion into a 3x3 rotation matrix.
        mat = tfs.quaternions.quat2mat(np.asarray(quat))

        # Combine translation and rotation into a 4x4 matrix.
        mat = tfs.affines.compose(
            np.squeeze(np.asarray(xyz)),
            mat,
            [1, 1, 1]
        )

        # Return the transformation matrix.
        return mat


    # ========================================================
    # 18. CONVERT A MATRIX INTO XYZ AND EULER ANGLES
    # ========================================================

    def mat_to_xyz_euler(self, mat, degrees=False):

        # Decompose the affine transformation matrix.
        # t = translation.
        # r = rotation matrix.
        t, r, _, _ = tfs.affines.decompose(mat)

        # Convert the rotation matrix into Euler angles.
        if degrees:

            euler = np.degrees(tfs.euler.mat2euler(r))

        else:

            # Return Euler angles in radians.
            euler = tfs.euler.mat2euler(r)

        # Return translation and orientation.
        return t, euler


    # ========================================================
    # 19. ROBOT TRACKING AND MOVEMENT CONTROL
    # ========================================================

    def robot_move(self, point_x, dist, roll):

        # Convert the detected roll angle from radians into degrees.
        roll_degree = abs(math.degrees(roll))

        # Print the current tracking measurements.
        print("point_x: ", point_x)
        print("dist: ", dist)
        print("roll_degree: ", roll_degree)

        # Reject sudden distance changes greater than 30.
        if abs(self.prev_dist - dist) > 30:

            self.prev_dist = dist
            return

        # Calculate forward/backward velocity using the PID controller.
        # The target distance is self.minDist.
        linear_x = self.linearx_pid.compute(
            dist,
            self.minDist
        )

        # Set the initial angular velocity.
        # The sign depends on the rotation direction.
        angular_z = -self.rotation_direction * 0.25

        # Set the initial sideways velocity.
        linera_y = self.rotation_direction * 0.1

        # Check whether the robot has reached the required distance.
        if abs(dist - self.minDist) < 30:

            # Stop forward/backward movement.
            linear_x = 0

            # Mark X-axis tracking as complete.
            self.x_track_done = True

        # Check whether the object's roll angle is close to 175 degrees.
        if abs(roll_degree - 175) < 5:

            # Stop angular rotation.
            angular_z = 0

            # Mark roll tracking as complete.
            self.roll_track_done = True

            # Use the Y-axis PID controller to align the object
            # with the image centre at X = 320.
            linera_y = self.lineary_pid.compute(
                320,
                point_x
            ) * 0.3

            # If the object's X coordinate is close to the centre,
            # stop sideways movement.
            if abs(point_x - 320) < 5:

                linera_y = 0.0

                # Mark Y-axis tracking as complete.
                self.y_track_done = True

        # Print the calculated movement velocities.
        print("linear_x: ", linear_x)
        print("linear_y: ", linera_y)
        print("angular_z: ", angular_z)

        # Publish the movement command.
        self.pubVel(
            linear_x,
            linera_y,
            angular_z
        )

        # Check whether all three tracking stages are complete.
        if (
            self.x_track_done == True
            and self.roll_track_done == True
            and self.y_track_done == True
        ):

            print("adjust dist to grasp it.")

            # Stop the tracking phase.
            self.track_flag = False

            # Enable distance adjustment for grasping.
            self.adjust_dist = True


    # ========================================================
    # 20. PUBLISH MOBILE ROBOT VELOCITY
    # ========================================================

    def pubVel(self, vx, vy, vz):

        # Create a Twist message for robot movement.
        vel = Twist()

        # Set forward/backward velocity.
        vel.linear.x = float(vx)

        # Set sideways velocity.
        vel.linear.y = float(vy)

        # Set rotational velocity around the Z-axis.
        vel.angular.z = float(vz)

        # Publish the velocity command.
        self.CmdVel_pub.publish(vel)


    # ========================================================
    # 21. MAIN RGB AND DEPTH IMAGE PROCESSING CALLBACK
    # ========================================================

    # This function receives synchronized RGB and depth images.
    # It performs:
    #   1. Image conversion.
    #   2. Depth image processing.
    #   3. Contour detection.
    #   4. Shape classification.
    #   5. 3D position calculation.
    #   6. Object dimension and volume estimation.
    #   7. Display of processed images.

    def callback(self, color_frame, depth_frame):

        # ----------------------------------------------------
        # STEP 1: CONVERT RGB IMAGE
        # ----------------------------------------------------

        # Convert the ROS 2 RGB image message into an OpenCV image.
        # 'rgb8' means 8-bit RGB image with three colour channels.
        rgb_image = self.rgb_bridge.imgmsg_to_cv2(
            color_frame,
            'rgb8'
        )

        # Convert RGB format into BGR format.
        # OpenCV normally uses BGR channel ordering.
        rgb_image = cv2.cvtColor(
            rgb_image,
            cv2.COLOR_RGB2BGR
        )

        # Create a copy of the RGB image.
        result_image = np.copy(rgb_image)

        # ----------------------------------------------------
        # STEP 2: CONVERT DEPTH IMAGE
        # ----------------------------------------------------

        # Convert the ROS 2 depth image message into an OpenCV image.
        # encoding[1] selects the 32FC1 format.
        depth_image = self.depth_bridge.imgmsg_to_cv2(
            depth_frame,
            encoding[1]
        )

        # Resize the depth image to 640 x 480 pixels.
        # This is used for the image-processing operations below.
        frame = cv.resize(
            depth_image,
            (640, 480)
        )

        # Convert the depth image into a colourized image.
        # COLORMAP_JET represents depth differences using colours.
        depth_to_color_image = cv2.applyColorMap(
            cv2.convertScaleAbs(
                depth_image,
                alpha=1.0
            ),
            cv2.COLORMAP_JET
        )

        # Convert the resized depth image into float32 format.
        # This image is used later to read depth values at pixel locations.
        depth_image_info = frame.astype(np.float32)

        # ----------------------------------------------------
        # STEP 3: PREPARE DEPTH IMAGE FOR SHAPE DETECTION
        # ----------------------------------------------------

        # Convert the colourized depth image into grayscale.
        gray_image = cv2.cvtColor(
            depth_to_color_image,
            cv2.COLOR_BGR2GRAY
        )

        # Create a completely black image with the same dimensions.
        black_image = np.zeros_like(gray_image)

        # Copy only the upper 320 rows of the grayscale image.
        # The remaining rows stay black.
        black_image[0:320, 0:640] = gray_image[0:320, 0:640]

        # Remove low-intensity pixel values below 120.
        # This helps reduce unwanted areas in the image.
        black_image[black_image < 120] = 0

        # Draw a small white circle at the image centre.
        cv2.circle(
            black_image,
            (320, 240),
            1,
            (255, 255, 255),
            1
        )

        # Apply Gaussian blur to reduce image noise.
        # (3, 3) is the kernel size.
        # 1 is the Gaussian standard deviation.
        gauss_image = cv2.GaussianBlur(
            black_image,
            (3, 3),
            1
        )

        # Convert the blurred image into a binary image.
        # Pixels become either black or white.
        _, threshold_img = cv2.threshold(
            gauss_image,
            0,
            255,
            cv2.THRESH_BINARY
        )

        # Erosion:
        # Removes small white areas and shrinks white regions.
        erode_img = cv2.erode(
            threshold_img,
            np.ones((5, 5), np.uint8)
        )

        # Dilation:
        # Expands white areas and helps fill small gaps.
        dilate_img = cv2.dilate(
            erode_img,
            np.ones((5, 5), np.uint8)
        )

        # ----------------------------------------------------
        # STEP 4: FIND OBJECT CONTOURS
        # ----------------------------------------------------

        # Find external contours in the processed binary image.
        #
        # RETR_EXTERNAL:
        # Detect only the outermost contours.
        #
        # CHAIN_APPROX_NONE:
        # Store all contour boundary points.
        contours, hierarchy = cv2.findContours(
            dilate_img,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_NONE
        )

        # Process every detected contour separately.
        for obj in contours:

            # Calculate the area enclosed by the contour.
            area = cv2.contourArea(obj)

            # Ignore objects whose contour area is smaller than 2000.
            # This filters out small unwanted detections.
            if area < 2000:
                continue

            # Draw the detected contour on the colourized depth image.
            cv2.drawContours(
                depth_to_color_image,
                obj,
                -1,
                (255, 255, 0),
                4
            )

            # Calculate the perimeter of the contour.
            perimeter = cv2.arcLength(
                obj,
                True
            )

            # Approximate the contour using fewer points.
            #
            # 0.035 * perimeter controls the approximation accuracy.
            approx = cv2.approxPolyDP(
                obj,
                0.035 * perimeter,
                True
            )

            # Save the approximated corner points.
            self.corners = approx

            # Draw the approximated contour corners.
            cv2.drawContours(
                depth_to_color_image,
                approx,
                -1,
                (255, 0, 0),
                4
            )

            # Count the number of points in the approximated contour.
            CornerNum = len(approx)

            # Calculate the bounding rectangle around the detected object.
            #
            # x, y = top-left coordinate.
            # w = width.
            # h = height.
            x, y, w, h = cv2.boundingRect(approx)

            # ------------------------------------------------
            # STEP 5: CLASSIFY THE OBJECT SHAPE
            # ------------------------------------------------

            # If the approximated contour has exactly four corners,
            # classify it as either a Square or Rectangle.
            if CornerNum == 4:

                # Store the lengths of the four sides.
                side_lengths = []

                # Calculate the distance between consecutive corners.
                for i in range(4):

                    # Current corner.
                    p1 = approx[i]

                    # Next corner.
                    # Modulo 4 connects the last corner to the first.
                    p2 = approx[(i + 1) % 4]

                    # Calculate the Euclidean distance between the corners.
                    side_lengths.append(
                        np.linalg.norm(p1 - p2)
                    )

                # Convert the list into a NumPy array.
                side_lengths = np.array(side_lengths)

                # If the first two side lengths are approximately equal,
                # classify the object as a Square.
                #
                # atol=50 allows a difference of up to approximately
                # 50 pixels in this comparison.
                if np.allclose(
                    side_lengths[1],
                    side_lengths[0],
                    atol=50
                ):

                    objType = "Square"

                else:

                    # Otherwise, classify it as a Rectangle.
                    objType = "Rectangle"

            # If the contour has more than five corners,
            # classify it as a Cylinder.
            elif CornerNum > 5:

                objType = "Cylinder"

            else:

                # Any other contour shape is not recognized.
                objType = "None"

                # Reset the stored corners.
                self.corners = np.empty(
                    (4, 2),
                    dtype=np.int32
                )

            # ------------------------------------------------
            # STEP 6: FIND OBJECT CENTRE
            # ------------------------------------------------

            # Calculate the minimum-area rotated rectangle
            # that encloses the detected contour.
            rect = cv2.minAreaRect(obj)

            # Get the centre point of that rectangle.
            center = rect[0]

            # Read keyboard input.
            key = cv2.waitKey(1)

            # If the SPACE key is pressed (ASCII value 32),
            # enable object-position processing.
            if key == 32:

                self.pub_pos_flag = True
                self.adjust_dist = True

            # ------------------------------------------------
            # STEP 7: PROCESS THE DETECTED OBJECT
            # ------------------------------------------------

            # Continue only if position processing is enabled.
            if self.pub_pos_flag == True:

                # Process recognized objects only when the robot
                # is ready for another operation.
                if objType != "None" and self.done_flag == True:

                    # Convert the object centre coordinates into integers.
                    cx = int(center[0])
                    cy = int(center[1])

                    # Read the depth value at the object's centre.
                    # Divide by 1000 to convert millimetres into metres,
                    # assuming the camera depth values are in millimetres.
                    dist = depth_image_info[int(cy), int(cx)] / 1000

                    # Calculate the object's 3D position in the world frame.
                    pose = self.compute_heigh(
                        cx,
                        cy,
                        dist
                    )

                    # Round the object's Z coordinate to two decimal places.
                    pose[2] = round(pose[2], 2)

                    # Calculate the horizontal distance from the robot origin.
                    #
                    # sqrt(X^2 + Y^2)
                    dist_detect = math.sqrt(
                        pose[1] ** 2 + pose[0] ** 2
                    )

                    # Print the calculated object height.
                    print("heigh: ", pose[2])

                    # ------------------------------------------------
                    # STEP 8: CALCULATE SQUARE VOLUME
                    # ------------------------------------------------

                    if objType == "Square":

                        # Estimate the volume of the square-shaped object.
                        #
                        # Volume = side x side x side.
                        #
                        # The factor 100000 is used by the original
                        # program for its cubic-centimetre conversion.
                        volume = pose[2] ** 3 * 100000

                        # Round the estimated volume to one decimal place.
                        volume = round(volume, 1)

                        # Print the estimated volume.
                        print("volume: ", volume)
                        print("------------------")

                    # ------------------------------------------------
                    # STEP 9: CALCULATE RECTANGLE VOLUME
                    # ------------------------------------------------

                    elif objType == "Rectangle":

                        # Get the first approximated contour corner.
                        # Multiply the coordinates by 1.01 as in the original.
                        corn_x = self.corners[0][0][0] * 1.01
                        corn_y = self.corners[0][0][1] * 1.01

                        # Draw a red circle at the selected corner.
                        cv2.circle(
                            rgb_image,
                            (int(corn_x), int(corn_y)),
                            5,
                            (0, 0, 255),
                            5
                        )

                        # Draw a yellow circle at the object centre.
                        cv2.circle(
                            rgb_image,
                            (int(center[0]), int(center[1])),
                            5,
                            (0, 255, 255),
                            5
                        )

                        # Read the depth value at the selected corner.
                        # Divide by 1000 to convert millimetres into metres,
                        # assuming the depth image uses millimetres.
                        dist_corn = depth_image_info[
                            int(corn_y),
                            int(corn_x)
                        ] / 1000

                        print("dist_corn: ", dist_corn)

                        # Continue only if the corner depth is not zero.
                        if dist_corn != 0:

                            # Calculate the 3D position of the corner.
                            pose_corn = self.compute_heigh(
                                corn_x,
                                corn_y,
                                dist_corn
                            )

                            # Round the corner's Z coordinate.
                            pose_corn[2] = round(
                                pose_corn[2],
                                2
                            )

                            print("pose_corn: ", pose_corn)

                            # Calculate the distance between the object centre
                            # and the selected corner in the XY plane.
                            #
                            # Multiply by 2 to estimate the diagonal.
                            # The result is expressed in metres.
                            diagonal = math.sqrt(
                                (pose[1] - pose_corn[1]) ** 2
                                +
                                (pose[0] - pose_corn[0]) ** 2
                            ) * 2

                            print("diagonal: ", diagonal)

                            # Estimate the rectangle's volume using
                            # the original program's geometric formula.
                            volume = (
                                pose_corn[2] ** 2
                                *
                                math.sqrt(
                                    diagonal ** 2 - pose_corn[2] ** 2
                                )
                                * 100000
                            )

                            # Round the volume to one decimal place.
                            volume = round(volume, 1)

                            print("volume: ", volume)
                            print("------------------")

                    # ------------------------------------------------
                    # STEP 10: CALCULATE CYLINDER VOLUME
                    # ------------------------------------------------

                    elif objType == "Cylinder":

                        # Get the first approximated contour corner.
                        corn_x = self.corners[0][0][0] * 1.01
                        corn_y = self.corners[0][0][1] * 1.01

                        # Draw a red circle at the selected corner.
                        cv2.circle(
                            rgb_image,
                            (int(corn_x), int(corn_y)),
                            5,
                            (0, 0, 255),
                            5
                        )

                        # Draw a yellow circle at the object centre.
                        cv2.circle(
                            rgb_image,
                            (int(center[0]), int(center[1])),
                            5,
                            (0, 255, 255),
                            5
                        )

                        # Read the depth value at the selected corner.
                        # Divide by 1000 to convert millimetres into metres,
                        # assuming the camera depth values are in millimetres.
                        dist_corn = depth_image_info[
                            int(corn_y),
                            int(corn_x)
                        ] / 1000

                        print("dist_corn: ", dist_corn)

                        # Continue only if the corner depth is not zero.
                        if dist_corn != 0:

                            # Calculate the 3D position of the corner.
                            pose_corn = self.compute_heigh(
                                corn_x,
                                corn_y,
                                dist_corn
                            )

                            print("pose_corn: ", pose_corn)

                            # Round the corner height to two decimal places.
                            pose_corn[2] = round(
                                pose_corn[2],
                                2
                            )

                            # Calculate the radius using the distance
                            # between the centre and corner in the XY plane.
                            #
                            # The result is expressed in metres.
                            radius = math.sqrt(
                                (pose[1] - pose_corn[1]) ** 2
                                +
                                (pose[0] - pose_corn[0]) ** 2
                            )

                            print("radius: ", radius)

                            # Estimate cylinder volume.
                            #
                            # Volume = pi x radius^2 x height.
                            #
                            # The original program uses the factor 100000
                            # for its cubic-centimetre conversion.
                            volume = (
                                pose_corn[2]
                                * radius ** 2
                                * math.pi
                                * 100000
                            )

                            # Round the estimated volume to one decimal place.
                            volume = round(volume, 1)

                            print("volume: ", volume)
                            print("------------------")

                    # ------------------------------------------------
                    # STEP 11: DISPLAY OBJECT DISTANCE AND SHAPE
                    # ------------------------------------------------

                    # Convert the horizontal distance from metres to millimetres.
                    dist_detect = dist_detect * 1000

                    # Check whether the detected object is too close.
                    if dist_detect < 130:

                        # Mark the distance as invalid.
                        self.valid_dist = False

                        # Print a warning.
                        print(
                            "Invalid dist.Plese restart the program."
                        )

                    # Create a text label showing the object's distance.
                    dist = 'dist: ' + str(dist_detect) + 'mm'

                    # Display the distance near the object's centre.
                    cv.putText(
                        rgb_image,
                        dist,
                        (int(cx) + 5, int(cy) + 15),
                        cv.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (255, 0, 0),
                        2
                    )

                    # Draw a yellow circle at the object centre.
                    cv2.circle(
                        rgb_image,
                        (int(center[0]), int(center[1])),
                        5,
                        (0, 255, 255),
                        5
                    )

                    # Display the detected shape name on the RGB image.
                    cv2.putText(
                        rgb_image,
                        objType,
                        (x + w // 2, y + (h // 2)),
                        cv2.FONT_HERSHEY_COMPLEX,
                        0.6,
                        (0, 0, 0),
                        1
                    )

        # ----------------------------------------------------
        # STEP 12: DISPLAY THE FINAL IMAGES
        # ----------------------------------------------------

        # Display the processed, colourized depth image.
        cv2.imshow(
            "depth_to_color_image",
            depth_to_color_image
        )

        # Display the RGB image with the detected object information.
        cv2.imshow(
            "rgb_image",
            rgb_image
        )

        # Process OpenCV window events.
        # The value 10 means OpenCV waits approximately 10 milliseconds.
        key = cv2.waitKey(10)


# ============================================================
# 22. MAIN FUNCTION
# ============================================================

def main():

    # Print a separator in the terminal.
    print('----------------------')

    # Initialize the ROS 2 Python client library.
    rclpy.init()

    # Create the Shape Recognition ROS 2 node.
    shape_recognize = ShapeRecognizeNode(
        'ShapeRecognize_node'
    )

    # Keep the node running and process ROS 2 messages.
    # The synchronized RGB and depth images will trigger callback().
    rclpy.spin(shape_recognize)


# ============================================================
# 23. RUN THE PROGRAM
# ============================================================

# Execute main() when this Python file is run directly.
if __name__ == '__main__':
    main()
