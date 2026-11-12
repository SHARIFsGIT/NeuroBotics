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
    
    # --- SETTING UP VARIABLES ---
    
    # 1. use_sim_time: 
    # In robotics, you can use real-world time (the clock on the wall) or "simulation time" 
    # (a fake clock used when running in a video game/simulator). We are on a real robot, so 'false'.
    use_sim_time = LaunchConfiguration('use_sim_time', default='false')
    
    # 2. rviz_config:
    # Find the path to a special settings file called 'slam_rviz.rviz' inside the 'slam_mapping' folder.
    # RViz has millions of buttons and settings. This file pre-configures all of them so the screen 
    # opens up perfectly set up to view SLAM mapping!
    rviz_config = LaunchConfiguration('rviz_config', default=os.path.join(
        get_package_share_directory('slam_mapping'),
        'rviz',
        'slam_rviz.rviz'
    ))
    
    # Declare that 'rviz_config' is a variable that ROS 2 should know about.
    rviz_config_arg = DeclareLaunchArgument('rviz_config', default_value=rviz_config)

    # --- THE RVIZ NODE ---
    # Start the RViz program!
    rviz_node = Node(
        package='rviz2',               # Look in the rviz2 package
        executable='rviz2',            # Find the RViz executable
        name='rviz2',                  # Name it 'rviz2' in the ROS 2 network
        output='screen',              # Print any errors directly to our terminal
        
        # Give RViz some startup arguments (command line flags)
        arguments=[
            '-d', rviz_config,         # '-d' means "Load this configuration file automatically"
            use_sim_time               # Tell it to use real-world time
        ]
    )
    
    # --- THE FINAL LIST ---
    # Hand the list back to ROS 2 to start the program.
    return LaunchDescription([
        rviz_config_arg,  # Load the variable
        rviz_node,        # Start RViz!
    ])