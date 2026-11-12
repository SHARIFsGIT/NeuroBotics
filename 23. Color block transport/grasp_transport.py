
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# ============================================================
# 1. IMPORT LIBRARIES
# ============================================================

import rclpy                  # ROS 2 Python library
import numpy as np            # Mathematical calculations
import time                   # Time delays
import math                   # Mathematical functions
import threading              # Run tasks in separate threads
import yaml                   # Read configuration files

import transforms3d as tfs    # 3D coordinate transformations
import tf_transformations as tf

from std_msgs.msg import Float32, Bool, Int16

from arm_msgs.msg import ArmJoints
from arm_msgs.msg import ArmJoint

from arm_interface.srv import *
from arm_interface.msg import AprilTagInfo, CurJoints

from rclpy.node import Node


# ============================================================
# 2. LOAD ROBOT CAMERA OFFSET CONFIGURATION
# ============================================================

# Location of the YAML configuration file
offset_file = "/home/jetson/yahboomcar_ws/src/arm_kin/param/offset_value.yaml"

# Open and read the configuration file
with open(offset_file, 'r') as file:
    offset_config = yaml.safe_load(file)

# Display the loaded configuration
print(offset_config)
print("----------------------------")

print("x_offset: ", offset_config.get('x_offset'))
print("y_offset: ", offset_config.get('y_offset'))
print("z_offset: ", offset_config.get('z_offset'))


# ============================================================
# 3. CREATE THE ROBOT GRASPING NODE
# ============================================================

class GraspNode(Node):

    def __init__(self, name):

        # Initialize the ROS 2 node
        super().__init__(name)

        # Control whether the robot is allowed to grasp
        self.grasp_flag = True

        # Initial positions of the six robot joints
        self.init_joints = [90, 120, 0, 0, 90, 90]

        # Joint positions used to transport an object
        self.transport_joints = [90, 150, 12, 20, 90, 120]

        # Joint positions for downward movement
        self.down_joint = [90, 90, 12, 20, 90, 0]

        # Gripper joint angle
        self.gripper_joint = 90

        # Current end-effector position:
        # [X, Y, Z, Roll, Pitch, Yaw]
        self.CurEndPos = [
            0.1458589529828534,
            0.00022969568906952754,
            0.18566515428310748,
            0.00012389155580734876,
            1.0471973953319513,
            8.297829493472317e-05
        ]

        # Camera intrinsic parameters (camera calibration)
        self.camera_info_K = [
            477.57421875, 0.0, 319.3820495605469,
            0.0, 477.55718994140625, 238.64108276367188,
            0.0, 0.0, 1.0
        ]

        # Transformation matrix from camera frame to end-effector frame
        self.EndToCamMat = np.array([
            [0,  0,  1, -1.000e-01],
            [-1, 0,  0,  0],
            [0, -1,  0,  4.82000000e-02],
            [0,  0,  0,  1]
        ])


        # ====================================================
        # 4. CREATE ROS 2 SUBSCRIBERS
        # ====================================================

        # Receive object position detected by AprilTag
        self.sub_pos_info = self.create_subscription(
            AprilTagInfo,
            "PosInfo",
            self.pos_info_callback,
            1
        )

        # Receive gripper/joint 5 setting
        self.sub_joint5 = self.create_subscription(
            Int16,
            "set_joint5",
            self.get_joint5_callback,
            1
        )

        # Receive current positions of robot joints
        self.sub_cur_joints = self.create_subscription(
            CurJoints,
            "Curjoints",
            self.get_cur_joint_callback,
            1
        )

        # Receive signal that unloading has finished
        self.sub_unload = self.create_subscription(
            Bool,
            "/unload_done",
            self.get_UnloadCallBack,
            100
        )


        # ====================================================
        # 5. CREATE ROS 2 PUBLISHERS
        # ====================================================

        # Publish commands for all six robot joints
        self.pub_SixTargetAngle = self.create_publisher(
            ArmJoints,
            "arm6_joints",
            10
        )

        # Publish a command for a single robot joint
        self.pub_SingleTargetAngle = self.create_publisher(
            ArmJoint,
            "arm_joint",
            10
        )

        # Publish grasp completion status
        self.pubGraspStatus = self.create_publisher(
            Bool,
            "grasp_done",
            1
        )


        # ====================================================
        # 6. CONNECT TO ROBOT KINEMATICS SERVICE
        # ====================================================

        # Create a client to request inverse and forward kinematics
        self.client = self.create_client(
            ArmKinemarics,
            'get_kinemarics'
        )

        # Wait until the kinematics service becomes available
        while not self.client.wait_for_service(timeout_sec=1.0):
            self.get_logger().info(
                'Service not available, waiting again...'
            )

        print('init done')


        # ====================================================
        # 7. INITIALIZE ROBOT VARIABLES
        # ====================================================

        self.cur_joints = self.init_joints

        # Current sixth joint angle
        self.joint6 = 115

        # Current detected AprilTag ID
        self.cur_tagId = 0

        # Load camera position offsets from YAML
        self.x_offset = offset_config.get('x_offset')
        self.y_offset = offset_config.get('y_offset')
        self.z_offset = offset_config.get('z_offset')

        # Current end-effector pitch in radians
        self.angle_radians = self.CurEndPos[4]


    # ========================================================
    # 8. RECEIVE JOINT 5 COMMAND
    # ========================================================

    def get_joint5_callback(self, msg):

        # Save the received joint angle
        self.gripper_joint = msg.data

        print("get joint5 = ", msg.data)


    # ========================================================
    # 9. RECEIVE UNLOADING COMPLETION SIGNAL
    # ========================================================

    def get_UnloadCallBack(self, msg):

        # Allow another grasp after unloading is complete
        if msg.data == True:
            self.grasp_flag = True


    # ========================================================
    # 10. CALCULATE DISTANCE AND PITCH INFORMATION
    # ========================================================

    def compute_pitch(self, pose_T):

        # Current robot end-effector position
        P1 = np.array([
            self.CurEndPos[0],
            self.CurEndPos[1],
            self.CurEndPos[2]
        ])

        # Target object position
        P2 = np.array([
            pose_T[0],
            pose_T[1],
            pose_T[2]
        ])

        # Calculate 3D Euclidean distance
        distance_xyz = np.linalg.norm(P2 - P1)

        print("distance_xyz: ", distance_xyz)


        # Current robot XY position
        P3 = np.array([
            self.CurEndPos[0],
            self.CurEndPos[1]
        ])

        # Robot origin
        P0 = np.array([0.0, 0.0])

        # Target XY position
        P4 = np.array([
            pose_T[0],
            pose_T[1]
        ])

        # Calculate horizontal distance
        distance_xy = np.linalg.norm(P4 - P0)

        print("distance_xy: ", distance_xy)

        # Display current pitch angle
        print("angle_radians: ", self.angle_radians)


    # ========================================================
    # 11. RECEIVE CURRENT JOINT POSITIONS
    # ========================================================

    def get_cur_joint_callback(self, msg):

        # Display received joint positions
        print(msg.joints)

        # Save current joint positions
        self.cur_joints = msg.joints

        # Calculate current end-effector position using FK
        self.get_current_end_pos()


    # ========================================================
    # 12. RECEIVE APRILTAG OBJECT POSITION
    # ========================================================

    def pos_info_callback(self, msg):

        print(msg)

        # Read object pixel coordinates and depth
        pos_x = msg.x
        pos_y = msg.y
        pos_z = msg.z

        # Save detected AprilTag ID
        self.cur_tagId = msg.id

        # Continue only if valid depth information exists
        if pos_z != 0.0:

            # Convert camera pixel coordinates into 3D coordinates
            camera_location = self.pixel_to_camera_depth(
                (pos_x, pos_y),
                pos_z
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

            # Calculate object position in robot/world coordinates
            WorldPose = np.matmul(
                EndPointMat,
                PoseEndMat
            )

            # Convert transformation matrix into position and orientation
            pose_T, pose_R = self.mat_to_xyz_euler(WorldPose)

            print("pose_T: ", pose_T)

            # Apply calibration offsets
            pose_T[0] = pose_T[0] + self.x_offset
            pose_T[1] = pose_T[1] + self.y_offset
            pose_T[2] = pose_T[2] + self.z_offset

            print("pose_T_add_offset: ", pose_T)
            print("pose_R: ", pose_R)

            # Calculate distance and pitch information
            self.compute_pitch(pose_T)

            # Check whether the robot is allowed to grasp
            if self.grasp_flag == True:

                print("Take it now.")

                # Disable another grasp until unloading finishes
                self.grasp_flag = False

                # Create a separate thread for the grasping operation
                grasp = threading.Thread(
                    target=self.grasp,
                    args=(pose_T,)
                )

                # Start the grasping operation
                grasp.start()

                # Wait until the thread finishes
                grasp.join()


    # ========================================================
    # 13. START GRASPING OPERATION
    # ========================================================

    def grasp(self, pose_T):

        print("------------------------------------------------")

        # Create inverse kinematics service request
        request = ArmKinemarics.Request()

        # Set target X position
        request.tar_x = pose_T[0] - 0.015

        # Set target Y position
        request.tar_y = pose_T[1]

        # Set target Z position
        request.tar_z = pose_T[2]

        # Select inverse kinematics
        request.kin_name = "ik"

        # Set target orientation
        request.roll = 0.0

        request.pitch = 1.3962614348313127

        request.yaw = 0.0

        print("calcutelate_request: ", request)

        # Send the service request asynchronously
        future = self.client.call_async(request)

        # Execute callback when the IK response arrives
        future.add_done_callback(
            self.get_ik_respone_callback
        )


    # ========================================================
    # 14. RECEIVE INVERSE KINEMATICS RESPONSE
    # ========================================================

    def get_ik_respone_callback(self, future):

        try:

            # Get response from the IK service
            response = future.result()

            print("response: ", response)

            # Create an array for six joint angles
            joints = [
                0.0, 0.0, 0.0,
                0.0, 0.0, 0.0
            ]

            # Calculate joint 1 angle
            joints[0] = 180 - int(response.joint1)

            # Save joint 2 angle
            joints[1] = int(response.joint2)

            # Save joint 3 angle
            joints[2] = int(response.joint3)

            # Limit joint 4 to a maximum of 90 degrees
            if response.joint4 > 90:
                joints[3] = 90
            else:
                joints[3] = int(response.joint4)


            # Calculate joint 5 if the configured angle is negative
            if self.gripper_joint < 0:

                joints[4] = abs(self.gripper_joint)

                if abs(self.gripper_joint) < 90:

                    joints[4] = (
                        180 - joints[0] +
                        joints[4] - 90
                    )

                else:

                    joints[4] = (
                        joints[4] - joints[0] + 90
                    )

                if joints[4] > 135:
                    joints[4] = joints[4] - 90

                elif joints[4] < 45:
                    joints[4] = joints[4] + 90


            # Calculate joint 5 if the configured angle is positive
            if self.gripper_joint > 0:

                joints[4] = 180 - abs(self.gripper_joint)

                if self.gripper_joint < 90:

                    joints[4] = joints[4] - joints[0]

                else:

                    joints[4] = (
                        joints[4] - (joints[0] - 90)
                    )

                if joints[4] > 135:
                    joints[4] = joints[4] - 90

                elif joints[4] < 45:
                    joints[4] = joints[4] + 90


            # Set joint 6 angle
            joints[5] = 30

            print("compute_joints: ", joints)


            # Prevent negative joint angles
            for i in range(6):

                if joints[i] < 0:
                    joints[i] = 0


            # Publish all six joint commands
            self.pubSixArm(joints)

            # Wait 3.5 seconds for the movement
            time.sleep(3.5)

            # Continue with the transport movement
            self.move()


        except Exception as e:

            # Display service error
            self.get_logger().error(
                f'Service call failed: {e}'
            )


    # ========================================================
    # 15. MOVE ROBOT AFTER GRASPING
    # ========================================================

    def move(self):

        # Move joint 6 to its configured angle
        self.pubSingleArm(
            6,
            self.joint6,
            2000
        )

        time.sleep(2.5)

        # Move all six joints to transport position
        self.pubSixArm(self.transport_joints)

        time.sleep(2.5)

        # Create grasp completion message
        grasp_done = Bool()

        grasp_done.data = True

        # Publish grasp completion status
        self.pubGraspStatus.publish(grasp_done)


    # ========================================================
    # 16. PUBLISH COMMANDS FOR ALL SIX JOINTS
    # ========================================================

    def pubSixArm(
        self,
        joints,
        id=6,
        angle=180.0,
        runtime=2000
    ):

        # Create a six-joint command message
        arm_joints = ArmJoints()

        # Assign each joint angle
        arm_joints.joint1 = int(joints[0])
        arm_joints.joint2 = int(joints[1])
        arm_joints.joint3 = int(joints[2])
        arm_joints.joint4 = int(joints[3])
        arm_joints.joint5 = int(joints[4])
        arm_joints.joint6 = int(joints[5])

        # Set movement duration in milliseconds
        arm_joints.time = runtime

        # Publish the command
        self.pub_SixTargetAngle.publish(arm_joints)


    # ========================================================
    # 17. PUBLISH COMMAND FOR A SINGLE JOINT
    # ========================================================

    def pubSingleArm(
        self,
        joint_id,
        joint_angle,
        run_time
    ):

        # Create a single-joint command message
        arm_joint = ArmJoint()

        # Set the joint angle
        arm_joint.joint = joint_angle

        # Set the joint ID
        arm_joint.id = joint_id

        # Set movement duration
        arm_joint.time = run_time

        # Publish the command
        self.pub_SingleTargetAngle.publish(arm_joint)


    # ========================================================
    # 18. CALCULATE CURRENT END-EFFECTOR POSITION (FK)
    # ========================================================

    def get_current_end_pos(self):

        # Create forward kinematics service request
        request = ArmKinemarics.Request()

        # Send current joint angles
        request.cur_joint1 = float(self.cur_joints[0])
        request.cur_joint2 = float(self.cur_joints[1])
        request.cur_joint3 = float(self.cur_joints[2])
        request.cur_joint4 = float(self.cur_joints[3])
        request.cur_joint5 = float(self.cur_joints[4])

        # Select forward kinematics
        request.kin_name = "fk"

        # Send request asynchronously
        future = self.client.call_async(request)

        # Process response when available
        future.add_done_callback(
            self.get_fk_respone_callback
        )


    # ========================================================
    # 19. RECEIVE FORWARD KINEMATICS RESPONSE
    # ========================================================

    def get_fk_respone_callback(self, future):

        try:

            # Get FK response
            response = future.result()

            # Save current end-effector position and orientation
            self.CurEndPos[0] = response.x
            self.CurEndPos[1] = response.y
            self.CurEndPos[2] = response.z

            self.CurEndPos[3] = response.roll
            self.CurEndPos[4] = response.pitch
            self.CurEndPos[5] = response.yaw

            print("self.CurEndPose: ", self.CurEndPos)

        except Exception as e:

            self.get_logger().error(
                f'Service call failed: {e}'
            )


    # ========================================================
    # 20. GET CURRENT END-EFFECTOR TRANSFORMATION MATRIX
    # ========================================================

    def get_end_point_mat(self):

        # Convert Euler angles into a quaternion
        end_w, end_x, end_y, end_z = self.euler_to_quaternion(
            self.CurEndPos[3],
            self.CurEndPos[4],
            self.CurEndPos[5]
        )

        # Create transformation matrix from position and quaternion
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
    # 21. CONVERT CAMERA PIXELS INTO 3D COORDINATES
    # ========================================================

    def pixel_to_camera_depth(self, pixel_coords, depth):

        # Read camera intrinsic parameters
        fx = self.camera_info_K[0]
        fy = self.camera_info_K[4]

        cx = self.camera_info_K[2]
        cy = self.camera_info_K[5]

        # Read pixel coordinates
        px, py = pixel_coords

        # Calculate 3D X coordinate
        x = (px - cx) * depth / fx

        # Calculate 3D Y coordinate
        y = (py - cy) * depth / fy

        # Z coordinate is the depth measurement
        z = depth

        return np.array([x, y, z])


    # ========================================================
    # 22. CONVERT XYZ + EULER ANGLES INTO A MATRIX
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

            mat = tfs.euler.euler2mat(
                euler[0],
                euler[1],
                euler[2]
            )

        # Combine position and rotation into a transformation matrix
        mat = tfs.affines.compose(
            np.squeeze(np.asarray(xyz)),
            mat,
            [1, 1, 1]
        )

        return mat


    # ========================================================
    # 23. CONVERT EULER ANGLES INTO QUATERNION
    # ========================================================

    def euler_to_quaternion(self, roll, pitch, yaw):

        # Convert Euler angles into quaternion
        quaternion = tf.quaternion_from_euler(
            roll,
            pitch,
            yaw
        )

        # Extract quaternion components
        qw = quaternion[3]
        qx = quaternion[0]
        qy = quaternion[1]
        qz = quaternion[2]

        return np.array([qw, qx, qy, qz])


    # ========================================================
    # 24. CONVERT XYZ + QUATERNION INTO A MATRIX
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
    # 25. CONVERT MATRIX INTO POSITION + EULER ANGLES
    # ========================================================

    def mat_to_xyz_euler(self, mat, degrees=False):

        # Extract translation and rotation from matrix
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
# 26. MAIN FUNCTION: START THE ROS 2 NODE
# ============================================================

def main():

    print('----------------------')

    # Initialize ROS 2
    rclpy.init()

    # Create the grasping node
    grasp = GraspNode('Grasp_Node')

    # Keep the node running and listening for messages
    rclpy.spin(grasp)


# ============================================================
# 27. RUN THE PROGRAM
# ============================================================

if __name__ == '__main__':

    main()
