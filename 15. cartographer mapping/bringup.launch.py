# --- IMPORTING ROS 2 LAUNCH TOOLS ---
# (Note: The programmer imported a lot of tools here that they didn't actually end up using, 
# like IfCondition, ExecuteProcess, etc. That's normal when copying from templates!)
from launch_ros.actions import Node
from launch.actions import IncludeLaunchDescription
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, ExecuteProcess
from launch.conditions import IfCondition, UnlessCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node, SetRemap
from launch_ros.substitutions import FindPackageShare
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.actions import Shutdown
import os

def generate_launch_description():

    # --- FINDING ALL THE PIECES ---
        
    # 1. Laser Merger path
    # Find the script that stitches the front and back lasers into one 360-degree map.
    laser_merge_launch_file = os.path.join(
        get_package_share_directory('ira_laser_tools'),
        'launch',
        'merge_multi.launch.py'
    )

    # 2. Laser Filter path
    # Find the script that removes the robot's own body (like the arm) from the laser map.
    laser_filter_launch_file = os.path.join(
        get_package_share_directory('yahboom_laser_filter'),
        'launch',
        'laser_filter_node.launch.py'
    )

    # 3. EKF (Extended Kalman Filter) path
    # Find the script that fuses the wheel data and IMU data to track exact movement.
    ekf_odom_launch_file = os.path.join(
        get_package_share_directory('ekf_bringup'),
        'launch',
        'ekf.launch.py'
    )
    
    # 4. IMU Filter Node
    # Start the program that cleans up the jittery data from the physical gyroscope chip.
    imu_filter_madgwick_node = Node(
            package='imu_filter_madgwick',
            executable='imu_filter_madgwick_node',
            name='imu_filter_madgwick_node',
    )
    
    # --- THE FINAL LIST ---
    # Hand the list of all 4 programs back to ROS 2 to start them all at once.
    return LaunchDescription([

        # 1. Start the IMU Filter
        # This runs first so the robot knows its exact tilt and rotation before doing anything else.
        imu_filter_madgwick_node,
    
        # 2. Start the Laser Merger
        # Stitch the raw laser data together into one full 360-degree view.
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(laser_merge_launch_file)
        ),
        
        # 3. Start the Laser Filter
        # Clean up the 360-degree view by deleting "ghost" obstacles that are just the robot's own arm.
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(laser_filter_launch_file)
        ),
    
        # 4. Start the EKF (Extended Kalman Filter)
        # Now that the IMU is clean, mix its data with the wheel encoders to calculate 
        # exactly how many meters the robot has driven and turned. 
        # This publishes the all-important "Odometry" (the robot's GPS coordinates on the map).
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(ekf_odom_launch_file)
        ),
        
    ])