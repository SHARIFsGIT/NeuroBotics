
# Import LaunchDescription.
# It defines which launch actions should run when this launch file starts.
from launch import LaunchDescription

# Import Node.
# This allows us to launch individual ROS 2 nodes.
from launch_ros.actions import Node

# Import os.
# Used for constructing file paths.
import os

# Import IncludeLaunchDescription.
# This allows us to include and execute another launch file.
from launch.actions import IncludeLaunchDescription

# Import PythonLaunchDescriptionSource.
# Used to tell ROS 2 that the included launch file is written in Python.
from launch.launch_description_sources import PythonLaunchDescriptionSource

# Import get_package_share_directory.
# This function finds the installed share directory of a ROS 2 package.
from ament_index_python.packages import get_package_share_directory


# ============================================================
# MAIN LAUNCH DESCRIPTION FUNCTION
# ============================================================

def generate_launch_description():

    # --------------------------------------------------------
    # 1. LASER DRIVER LAUNCH
    # --------------------------------------------------------

    # Find the installed share directory of the Yahboom M3Pro laser package.
    #
    # Then locate its launch directory and include laser_driver.launch.py.
    #
    # This starts the laser driver using the configuration
    # defined inside that launch file.
    laser_driver_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            os.path.join(
                get_package_share_directory('yahboom_M3Pro_laser'),
                'launch'
            ),
            '/laser_driver.launch.py'
        ])
    )

    # --------------------------------------------------------
    # 2. ORBBEC CAMERA LAUNCH
    # --------------------------------------------------------

    # Find the installed share directory of the Orbbec camera package.
    #
    # Then locate its launch directory and include dabai_dcw2.launch.py.
    #
    # This starts the Orbbec camera driver using the settings
    # defined inside that launch file.
    camera_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            os.path.join(
                get_package_share_directory('orbbec_camera'),
                'launch'
            ),
            '/dabai_dcw2.launch.py'
        ])
    )

    # --------------------------------------------------------
    # 3. RETURN THE COMPLETE LAUNCH DESCRIPTION
    # --------------------------------------------------------

    # Launch both drivers when this launch file is executed.
    #
    # laser_driver_launch:
    #   Starts the M3Pro laser driver.
    #
    # camera_launch:
    #   Starts the Orbbec camera driver.
    #
    # Both launch actions are included in the same LaunchDescription.
    return LaunchDescription([
        laser_driver_launch,
        camera_launch
    ])
