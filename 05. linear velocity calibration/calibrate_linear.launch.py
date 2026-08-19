# --- IMPORTING ROS 2 LAUNCH TOOLS ---
import os
from launch import LaunchDescription
from launch_ros.actions import Node
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
    
    # --- PROGRAM 3: THE LINEAR CALIBRATION NODE ---
    # Start a single Node directly instead of using a launch file.
    calibrate_linear = Node(
        package='calibration',               # Look in the 'calibration' package
        executable='calibrate_linear',       # Find the program named 'calibrate_linear'
        name='calibrate_linear',             # Give it this name in the ROS 2 network
        parameters=[
            # Tell the calibration tool what parts of the robot to measure.
            # 'base_frame' is the center of the robot (base_footprint).
            # 'odom_frame' is the starting point of the world (odom).
            {'base_frame': 'base_footprint'},
            {'odom_frame': 'odom'}
        ],
        output='screen'  # Print the output directly to our terminal screen so we can see the math results
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

        # 2. Start the EKF Localization (ekf，odom-base_rootpringt tf)
        # EKF stands for Extended Kalman Filter. This is the "Math Brain".
        # It takes the wheel data AND the IMU data and mixes them together to guess where the robot is.
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(ekf_odom_launch_file)
        ),
        
        # 3. Start the linear calibration tool
        # This program tells the robot to drive forward exactly 1 meter.
        # It then measures how far the robot *actually* drove. If the robot only drove 0.9 meters, 
        # it calculates a "correction factor" to put in the robot's config files so it drives accurately next time!
        calibrate_linear,

    ])