# --- IMPORTING ROS 2 LAUNCH TOOLS ---
import os
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch.actions import IncludeLaunchDescription
from ament_index_python.packages import get_package_share_directory
from launch.launch_description_sources import PythonLaunchDescriptionSource

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
    
    # --- PROGRAM 3: THE ANGULAR CALIBRATION NODE ---
    # Instead of a launch file, we are starting a single Node directly.
    calibrate_angular = Node(
        package='calibration',               # Look in the 'calibration' package
        executable='calibrate_angular',      # Find the program named 'calibrate_angular'
        name='calibrate_angular',            # Give it this name in the ROS 2 network
        parameters=[
            # Tell the calibration tool what parts of the robot to measure.
            # 'base_frame' is the center of the robot (base_footprint).
            # 'odom_frame' is the starting point of the world (odom).
            {'base_frame': 'base_footprint'},
            {'odom_frame': 'odom'}
        ],
        output='screen'  # Print the output directly to our terminal screen so we can see the results
    )

    # --- THE FINAL LIST ---
    # Hand the list of programs back to ROS 2 to start them all at once.
    return LaunchDescription([
        
        # 1. Start the IMU filter (/imu)
        # This cleans up the noisy, jittery data coming from the physical IMU chip 
        # so the robot doesn't think it's shaking when it's standing still.
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(imu_filter_madgwick_launch_file)
        ),

        # 2. Start the EKF Localization (ekf, odom-base_rootpringt)
        # EKF stands for Extended Kalman Filter. This is the "Math Brain".
        # It takes the wheel data AND the IMU data and mixes them together.
        # It then publishes the "TF" (Transform) which tells the robot: 
        # "Based on my wheels and my IMU, I am exactly X meters from my starting point."
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(ekf_odom_launch_file)
        ),
        
        # 3. Start the calibration tool
        # This program spins the robot in a circle and measures how far it *actually* turned 
        # vs how far you *told* it to turn. This helps fix math errors in the robot's brain.
        calibrate_angular,

    ])