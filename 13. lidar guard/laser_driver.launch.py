import os   # (System file operations) - Lets Python interact with computer folders and file paths
from ament_index_python.packages import get_package_share_directory  # A ROS 2 tool that finds where a package is installed
from launch import LaunchDescription  # The main container that holds our list of programs to start
from launch.actions import IncludeLaunchDescription  # A tool to run ANOTHER launch file inside this one
from launch.launch_description_sources import PythonLaunchDescriptionSource  # Tells ROS the other launch file is written in Python
from launch_ros.actions import Node  # A tool to start a single ROS 2 program (Node) - imported just in case it's needed later

def generate_launch_description():

    # --- PROGRAM 1: THE LASER MERGER ---
    # Find the path to the 'ira_laser_tools' package, go into the 'launch' folder, and find 'merge_multi.launch.py'
    laser_merge_launch_file = os.path.join(
        get_package_share_directory('ira_laser_tools'),
        'launch',
        'merge_multi.launch.py'
    )
    
    # --- PROGRAM 2: THE LASER FILTER ---
    # Find the path to the 'yahboom_laser_filter' package, go into the 'launch' folder, and find 'laser_filter_node.launch.py'
    laser_filter_launch_file = os.path.join(
        get_package_share_directory('yahboom_laser_filter'),
        'launch',
        'laser_filter_node.launch.py'
    )

    # --- THE FINAL LIST ---
    # Hand the list of programs back to ROS 2 to start them all at once.
    return LaunchDescription([

        # 1. Start the Laser Merger
        # This runs the file we found above. It stitches the front and back lasers together into one 360-degree map.
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(laser_merge_launch_file)
        ),
        
        # 2. Start the Laser Filter
        # This runs the file we found above. It cleans up the data by removing "blind spots" (like the robot's own arm).
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(laser_filter_launch_file)
        )

    ])