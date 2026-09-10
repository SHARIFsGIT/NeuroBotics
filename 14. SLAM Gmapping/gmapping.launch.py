# --- IMPORTING ROS 2 LAUNCH TOOLS ---
from launch_ros.actions import Node
from launch.substitutions import LaunchConfiguration
from launch.actions import DeclareLaunchArgument
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from launch.actions import IncludeLaunchDescription
# (Note: Some imports are duplicated here, which is harmless, just a bit messy)


def generate_launch_description():
    # These lists are created but not actually used in this file. 
    # They are just left over from a template the programmer used.
    declared_arguments = []
    declared_env_vars = []
    declared_parameters = []
    
    # --- FINDING ALL THE PIECES ---
    
    # 1. Laser Merger path
    laser_merge_launch_file = os.path.join(
        get_package_share_directory('ira_laser_tools'),
        'launch',
        'merge_multi.launch.py'
    )

    # 2. Laser Filter path
    laser_filter_launch_file = os.path.join(
        get_package_share_directory('yahboom_laser_filter'),
        'launch',
        'laser_filter_node.launch.py'
    )
    
    # 3. EKF (Extended Kalman Filter) path
    ekf_odom_launch_file = os.path.join(
        get_package_share_directory('ekf_bringup'),
        'launch',
        'ekf.launch.py'
    )
    
    # 4. Gmapping (The actual SLAM AI!) path
    gmapping_launch_file = os.path.join(
        get_package_share_directory('slam_gmapping'),
        'launch',
        'slam_gmapping.launch.py'
    )
    
    # 5. IMU Filter Node
    # Instead of a launch file, we start this one directly.
    imu_filter_madgwick_node = Node(
        package='imu_filter_madgwick',
        executable='imu_filter_madgwick_node',
        # Remapping is a superpower in ROS 2! 
        # The IMU node publishes its data on a topic called '/imu'.
        # But the robot's brain expects the data on a topic called '/imu/data_raw'.
        # This line acts like a mail forwarder, redirecting the letters automatically.
        remappings=[('/imu','/imu/data_raw')],
        name='imu_filter_madgwick_node',
    )

    # --- THE FINAL LIST ---
    # Hand the list of all 5 programs back to ROS 2 to start them all at once.
    return LaunchDescription([
    
        # 1. Start the Laser Merger (Stitch the 360 radar together)
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(laser_merge_launch_file)
        ),

        # 2. Start the Laser Filter (Remove the robot's own body from the radar)
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(laser_filter_launch_file)
        ),
        
        # 3. Start the IMU Filter (Clean up the gyroscope/accelerometer data)
        imu_filter_madgwick_node,
        
        # 4. Start the EKF (Calculate exactly how far the robot has driven)
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(ekf_odom_launch_file)
        ),
        
        # 5. Start Gmapping SLAM!
        # This AI listens to the cleaned radar data AND the EKF distance data.
        # It compares them frame-by-frame to guess if the robot is in a hallway or a room,
        # and slowly draws a 2D map of the environment.
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(gmapping_launch_file)
        )

    ])