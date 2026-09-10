# --- IMPORTING ROS 2 LAUNCH TOOLS ---
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch_ros.actions import Node
from launch.substitutions import LaunchConfiguration
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import ThisLaunchFileDir

def generate_launch_description():
    # --- 1. SIM TIME ---
    # We are on a real robot, not a simulator, so we use real-world time ('false').
    use_sim_time = LaunchConfiguration('use_sim_time', default='false')
    
    # --- 2. CONFIGURATION FILES ---
    # Find the 'slam_mapping' package and go into the 'config' folder.
    package_path = get_package_share_directory('slam_mapping')
    configuration_directory = LaunchConfiguration('configuration_directory', default=os.path.join(
                                                  package_path, 'config'))
    
    # Cartographer uses a special settings file written in the Lua programming language.
    # 'lds_2d.lua' means "Laser Distance Sensor, 2D". This file tells Cartographer 
    # exactly what kind of LiDAR the robot has and how fast it spins.
    configuration_basename = LaunchConfiguration('configuration_basename', default='lds_2d.lua')

    # --- 3. MAP SETTINGS ---
    # Resolution: How big is each pixel on the map? 0.05 means 1 pixel = 5 centimeters in the real world.
    resolution = LaunchConfiguration('resolution', default='0.05')
    
    # Publish period: How often should the robot update the map on the screen? (Every 1.0 second)
    publish_period_sec = LaunchConfiguration('publish_period_sec', default='1.0')

    # --- THE FINAL LIST ---
    return LaunchDescription([
        # Declare all the variables so ROS 2 knows they exist
        DeclareLaunchArgument('configuration_directory', default_value=configuration_directory, description='Full path to config file to load'),
        DeclareLaunchArgument('configuration_basename', default_value=configuration_basename, description='Name of lua file for cartographer'),
        DeclareLaunchArgument('use_sim_time', default_value='false', description='Use simulation (Gazebo) clock if true'),

        # --- THE CARTOGRAPHER AI BRAIN ---
        # Start the main Google Cartographer node!
        Node(
            package='cartographer_ros',
            executable='cartographer_node',
            name='cartographer_node',
            output='screen', # Print the AI's thoughts to the terminal
            parameters=[{'use_sim_time': use_sim_time}],
            
            # Feed the AI the Lua configuration file so it knows how to process the LiDAR data
            arguments=[
                '-configuration_directory', configuration_directory,
                '-configuration_basename', configuration_basename
            ]
        ),

        DeclareLaunchArgument('resolution', default_value=resolution, description='Resolution of a grid cell in the published occupancy grid'),
        DeclareLaunchArgument('publish_period_sec', default_value=publish_period_sec, description='OccupancyGrid publishing period'),

        # --- THE MAP PUBLISHER ---
        # Cartographer builds the map internally, but it needs a helper program to turn that 
        # internal data into a standard ROS 2 "OccupancyGrid" (the black/white/gray map) 
        # so that RViz can display it on your screen!
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource([ThisLaunchFileDir(), '/occupancy_grid_launch.py']),
            launch_arguments={
                'use_sim_time': use_sim_time, 
                'resolution': resolution,
                'publish_period_sec': publish_period_sec
            }.items(),
        ),
    ])