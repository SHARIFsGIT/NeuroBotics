# --- IMPORTING ROS 2 LAUNCH TOOLS ---
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.substitutions import LaunchConfiguration  # Lets us read variables typed in the terminal
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
import os
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    # These lists will hold extra settings we want to pass to ROS 2
    declared_arguments = []
    declared_env_vars = []
    declared_parameters = []

    # --- 1. SETTING UP A LAUNCH ARGUMENT ---
    # We want to tell the robot where to find its configuration file (a YAML file).
    # We create a variable called 'params_file' to hold this path.
    params_file = LaunchConfiguration("params_file")

    # Declare that 'params_file' is a valid argument someone can type in the terminal.
    declared_arguments.append(
        DeclareLaunchArgument(
            "params_file",
            # If the user doesn't provide a file, use this default one:
            default_value=os.path.join(
                get_package_share_directory("ira_laser_tools"), # Look in the ira_laser_tools package
                "config",                                        # Go into the config folder
                "laserscan_merge.yaml",                           # Find this file
            ),
            description="Path to param config in yaml format",
        )
    )
    

    # --- 2. THE LASER MERGER NODE ---
    # This is the program that takes multiple laser scans and merges them into one!
    laser_merge = Node(
        package="ira_laser_tools",                  # The package containing the merger
        executable="laserscan_multi_merger",        # The program that does the merging
        name="laserscan_multi_merger",              # Give it this name in the ROS 2 network
        parameters=[params_file],                   # Feed it the YAML config file we set up above!
    )

    # --- 3. THE VISUAL DISPLAY (RVIZ) ---
    # Find the path to another launch file called 'display.launch.py' inside the 'M3Pro' package.
    display_launch_file = os.path.join(
        get_package_share_directory('M3Pro'),
        'launch',
        'display.launch.py'
    )

    
    # --- 4. THE FINAL LIST ---
    # Put everything we want to launch into one big list.
    # 1. IncludeLaunchDescription starts the display file (usually opens RViz, the 3D visualizer).
    # 2. laser_merge starts the radar stitching program.
    nodes = [ IncludeLaunchDescription(PythonLaunchDescriptionSource(display_launch_file)), laser_merge]
    

    # Hand the list back to ROS 2 to start everything at once.
    # We combine the arguments, parameters, env vars, and nodes into one final LaunchDescription.
    return LaunchDescription(
        declared_parameters + declared_arguments + declared_env_vars + nodes
    )