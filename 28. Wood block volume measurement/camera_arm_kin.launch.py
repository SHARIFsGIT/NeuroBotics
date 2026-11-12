
# ---------------------------------------------------------
# IMPORTING ROS 2 LAUNCH TOOLS
# ---------------------------------------------------------

# LaunchDescription is the main container for all actions
# that ROS 2 should execute when this launch file runs.
from launch import LaunchDescription

# Node allows us to start a ROS 2 node (a running program).
from launch_ros.actions import Node

# os provides functions for working with folders and file paths.
import os

# IncludeLaunchDescription allows us to include and run
# another ROS 2 launch file from this launch file.
from launch.actions import IncludeLaunchDescription

# PythonLaunchDescriptionSource tells ROS 2 that the
# included launch file is written in Python.
from launch.launch_description_sources import PythonLaunchDescriptionSource

# This function finds the installation directory of a ROS 2 package.
from ament_index_python.packages import get_package_share_directory


# ---------------------------------------------------------
# MAIN LAUNCH FUNCTION
# ---------------------------------------------------------

# ROS 2 calls this function when you execute:
# ros2 launch <package_name> <launch_file_name>
#
# The function returns a LaunchDescription containing
# all the programs and actions that should be started.
def generate_launch_description():

    # -----------------------------------------------------
    # PROGRAM 1: START THE ORBBEC CAMERA
    # -----------------------------------------------------

    # Include an existing camera launch file instead of
    # manually configuring the camera driver here.
    camera_driver_launch = IncludeLaunchDescription(

        # Tell ROS 2 that the included launch file is Python-based.
        PythonLaunchDescriptionSource(

            # Construct the complete path to the camera launch file.
            #
            # get_package_share_directory('orbbec_camera')
            # finds the installed share directory of the package.
            #
            # os.path.join() combines:
            #   1. The package installation directory.
            #   2. The 'launch' folder.
            #   3. The camera launch filename.
            [
                os.path.join(
                    get_package_share_directory('orbbec_camera'),
                    'launch'
                ),
                '/dabai_dcw2.launch.py'
            ]
        )
    )

    # When this action runs, ROS 2 starts the camera driver
    # using the configuration defined in dabai_dcw2.launch.py.
    #
    # This allows other ROS 2 nodes to receive camera data,
    # such as RGB images and depth images, depending on
    # the camera launch configuration.


    # -----------------------------------------------------
    # PROGRAM 2: START THE ROBOT ARM KINEMATICS SERVICE
    # -----------------------------------------------------

    # Define a ROS 2 node that runs the arm kinematics program.
    kin_node = Node(

        # Name of the ROS 2 package containing the executable.
        package='arm_kin',

        # Name of the executable program to start.
        # This executable is expected to provide the kinematics service.
        executable='kin_srv',

        # Name assigned to the running ROS 2 node.
        # Other ROS 2 nodes can use this name to identify it.
        name='kin_ik_fk'

        # FK = Forward Kinematics:
        # Calculates the end-effector position from joint angles.
        #
        # IK = Inverse Kinematics:
        # Calculates the required joint angles from a target
        # end-effector position.
    )


    # -----------------------------------------------------
    # FINAL LAUNCH DESCRIPTION
    # -----------------------------------------------------

    # Return all the launch actions to ROS 2.
    #
    # ROS 2 will start:
    #   1. The Orbbec camera driver.
    #   2. The arm kinematics node.
    #
    # Both actions are included in the same launch description.
    return LaunchDescription([
        camera_driver_launch,
        kin_node
    ])
