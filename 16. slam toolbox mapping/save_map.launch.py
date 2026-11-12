# --- IMPORTING ROS 2 LAUNCH TOOLS ---
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from ament_index_python.packages import get_package_share_directory
from launch_ros.actions import Node
import os
from ament_index_python.packages import get_package_share_path

def generate_launch_description():
    
    # --- 1. NAMING THE MAP ---
    # Give the map a name so you know what it is later!
    map_name = "yahboom_map"
    
    # Figure out where to save it. 
    # It goes into the 'M3Pro_navigation' package, inside a folder called 'map'.
    default_map_path = os.path.join(get_package_share_path("M3Pro_navigation"), 'map', map_name)

    # --- 2. CREATING A LAUNCH ARGUMENT ---
    # This lets you type a different name in the terminal if you want to (e.g. map_path:=my_new_map)
    # But if you don't type anything, it uses the default 'yahboom_map' path from above.
    map_arg = DeclareLaunchArgument(
        name='map_path', 
        default_value=str(default_map_path),
        description='The path of the map'
    )

    # --- 3. THE MAP SAVER NODE ---
    # Start the official ROS 2 Navigation (Nav2) map saving tool.
    map_saver_node = Node(
        package='nav2_map_server',          # Look in the Nav2 map server package
        executable='map_saver_cli',         # Run the command line interface (CLI) tool
        
        # Give the tool some specific instructions (arguments):
        arguments=[
            '-f', LaunchConfiguration('map_path'),  # '-f' means "Save the file at this path"
            
            '--free', '0.196',  # Threshold for "Free Space": If the robot is less than 19.6% sure a spot is a wall, make it White (clear).
            '--occ', '0.65'     # Threshold for "Occupied Space": If the robot is more than 65% sure a spot is a wall, make it Black (solid).
        ],
    )

    # --- THE FINAL LIST ---
    # Hand the list back to ROS 2 to start the tool and save the map!
    return LaunchDescription([
        map_arg,
        map_saver_node
    ])