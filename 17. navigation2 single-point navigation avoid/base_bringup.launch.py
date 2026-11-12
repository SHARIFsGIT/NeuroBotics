import os  # (System file operations) - Lets Python interact with computer folders and file paths
from ament_index_python.packages import get_package_share_directory  # A ROS 2 tool that finds where a package is installed
from launch import LaunchDescription  # The main container that holds our list of programs to start
from launch.actions import IncludeLaunchDescription  # A tool to run ANOTHER launch file inside this one
from launch.launch_description_sources import PythonLaunchDescriptionSource  # Tells ROS the other launch file is written in Python
from launch_ros.actions import Node  # A tool to start a single ROS 2 program (Node)

def generate_launch_description():

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

    # 3. IMU Filter path
    # (Note: This version uses the full launch file for the IMU filter, 
    # instead of creating the Node directly like the previous script did!)
    imu_filter_madgwick_launch_file = os.path.join(
        get_package_share_directory('imu_filter_madgwick'),
        'launch',
        'imu_filter.launch.py'
    )

    # 4. EKF (Extended Kalman Filter) path
    # Fuses the wheel data and IMU data to track exact movement.
    ekf_odom_launch_file = os.path.join(
        get_package_share_directory('ekf_bringup'),
        'launch',
        'ekf.launch.py'
    )

    # 5. The Costmap Updater Node (DEFINED BUT NOT ACTUALLY USED!)
    # This program would take live laser data and paint obstacles onto the robot's 
    # "costmap" (the map it uses for navigation, where walls = expensive to drive through).
    # Think of it as a janitor constantly repainting the "danger zones" on the floor plan.
    updatecostmap = Node(
        package='updatecostmap',         # Look in the updatecostmap package
        executable='update_costmap',     # Find the program named 'update_costmap'
        name='update_costmap',           # Give it this name in the ROS 2 network
        output='screen'                  # Print its messages to our terminal
    )

    # --- THE FINAL LIST ---
    # Hand the list of programs back to ROS 2 to start them all at once.
    return LaunchDescription([
    
        # 1. Start the IMU Filter
        # This runs FIRST so the robot knows its exact tilt and rotation before doing anything else.
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(imu_filter_madgwick_launch_file)
        ),

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

        # 4. Start the EKF Localization
        # EKF stands for Extended Kalman Filter. This is the "Math Brain".
        # It takes the wheel data AND the IMU data and mixes them together to calculate 
        # exactly how many meters the robot has driven and turned (Odometry).
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(ekf_odom_launch_file)
        ),

        # 5. Start the Costmap Updater... WAIT, IT'S COMMENTED OUT!
        # The '#' symbol means this line is ignored. So the updatecostmap program 
        # is defined above but NEVER actually starts. It's like buying a tool 
        # but leaving it in the toolbox.
        # updatecostmap,

    ])