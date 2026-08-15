# --- IMPORTING ROS 2 LAUNCH TOOLS ---
import os
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import IncludeLaunchDescription
from ament_index_python.packages import get_package_share_directory
from launch.launch_description_sources import PythonLaunchDescriptionSource

# Every ROS 2 Python launch file MUST have this exact function.
def generate_launch_description():
    
    # --- PROGRAM 1: THE IMU FILTER ---
    # Find the path to the 'imu_filter_madgwick' package.
    imu_filter_madgwick_launch_file = os.path.join(
        get_package_share_directory('imu_filter_madgwick'),
        'launch',
        'imu_filter.launch.py'
    )

    # --- PROGRAM 2: THE EXTENDED KALMAN FILTER (EKF) ---
    # Find the path to the 'ekf_bringup' package.
    ekf_odom_launch_file = os.path.join(
        get_package_share_directory('ekf_bringup'),
        'launch',
        'ekf.launch.py'
    )
    
    # --- PROGRAM 3: THE PATROL NODE ---
    # Start a single Node directly. This is the AI brain that makes the robot drive itself!
    patrol = Node(
        package='patrol',               # Look in the 'patrol' package
        executable='patrol',           # Find the program named 'patrol'
        name='patrol',                 # Give it this name in the ROS 2 network
        parameters=[
            # Tell the AI what parts of the robot to measure.
            # 'base_frame' is the center of the robot (base_footprint).
            # 'odom_frame' is the starting point of the world (odom).
            {'base_frame': 'base_footprint'},
            {'odom_frame': 'odom'}
        ],
        output='screen'  # Print the output directly to our terminal screen so we can see the AI thinking
    )

    # --- THE FINAL LIST ---
    # Hand the list of programs back to ROS 2 to start them all at once.
    return LaunchDescription([
        
        # 1. Start the IMU filter
        # This cleans up the noisy, jittery data coming from the physical IMU chip.
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(imu_filter_madgwick_launch_file)
        ),

        # 2. Start the EKF Localization
        # EKF stands for Extended Kalman Filter. This is the "Math Brain".
        # It takes the wheel data AND the IMU data and mixes them together to figure out exactly where the robot is on a map.
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(ekf_odom_launch_file)
        ),
        
        # 3. Start the patrol AI
        # This program contains a list of waypoints (GPS-like coordinates on your map).
        # It tells the robot: "Drive to point A, then drive to point B, then turn around and do it again!"
        patrol,

    ])