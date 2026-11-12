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

def generate_launch_description():
    # These lists are just left over from a template the programmer used, 
    # they aren't actually used in this file.
    declared_arguments = []
    declared_env_vars = []
    declared_parameters = []
    
    # --- FINDING ALL THE PIECES ---
    
    # 1. Laser Merger path
    # Stitches the front and back lasers into one 360-degree view.
    laser_merge_launch_file = os.path.join(
        get_package_share_directory('ira_laser_tools'),
        'launch',
        'merge_multi.launch.py'
    )

    # 2. Laser Filter path
    # Removes the robot's own body (like the arm) from the laser map.
    laser_filter_launch_file = os.path.join(
        get_package_share_directory('yahboom_laser_filter'),
        'launch',
        'laser_filter_node.launch.py'
    )

    # 3. IMU Filter Node
    # Cleans up the jittery data from the physical gyroscope chip.
    imu_filter_madgwick_node = Node(
        package='imu_filter_madgwick',
        executable='imu_filter_madgwick_node',
        name='imu_filter_madgwick_node',
    )
    
    # 4. EKF (Extended Kalman Filter) path
    # Fuses the wheel data and IMU data to track exact movement.
    ekf_odom_launch_file = os.path.join(
        get_package_share_directory('ekf_bringup'),
        'launch',
        'ekf.launch.py'
    )
    
    # 5. SLAM Toolbox path
    # The modern AI algorithm that draws the 2D map of the room.
    # 'online_async' means it draws the map live as you drive!
    slam_toolbox_launch_file = os.path.join(
        get_package_share_directory('slam_mapping'),
        'launch',
        'online_async_launch.py'
    )
    
    # 6. RViz Node (The Visualizer)
    # Opens a 3D window on your screen so you can watch the map be drawn.
    # It loads a pre-configured settings file so all the right buttons are already clicked for you.
    rviz = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=[
            '-d',  # '-d' means "Load this configuration file automatically"
            os.path.join(get_package_share_directory('slam_mapping'), 'rviz', 'slam_toolbox_rviz.rviz')
        ],
    )

    # --- THE FINAL LIST ---
    # Hand the list of all 6 programs back to ROS 2 to start them all at once.
    return LaunchDescription([
    
        # 1. Start the Laser Merger
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(laser_merge_launch_file)
        ),

        # 2. Start the Laser Filter
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(laser_filter_launch_file)
        ),
        
        # 3. Start the IMU Filter
        imu_filter_madgwick_node,
        
        # 4. Start the EKF (Calculate exactly how far the robot has driven)
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(ekf_odom_launch_file)
        ),
        
        # 5. Start SLAM Toolbox! (The AI brain drawing the map)
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(slam_toolbox_launch_file)
        ),
        
        # 6. Open RViz (The screen showing the map)
        rviz

    ])