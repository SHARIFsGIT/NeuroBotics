
# ============================================================
# 1. IMPORT REQUIRED LIBRARIES
# ============================================================

# os provides functions for working with directories and file paths.
import os

# Main class used to create a ROS 2 launch description.
from launch import LaunchDescription

# DeclareLaunchArgument allows users to provide arguments
# when starting the launch file.
#
# ExecuteProcess runs an external terminal command.
# GroupAction groups multiple launch actions together.
# TimerAction can delay the execution of launch actions.
from launch.actions import (
    DeclareLaunchArgument,
    ExecuteProcess,
    GroupAction,
    TimerAction
)

# LaunchConfiguration reads values passed through launch arguments.
# PathJoinSubstitution joins paths using ROS 2 launch substitutions.
from launch.substitutions import (
    LaunchConfiguration,
    PathJoinSubstitution
)

# Node starts a ROS 2 node.
from launch_ros.actions import Node

# IfCondition allows an action to run only when a condition is true.
from launch.conditions import IfCondition

# PythonExpression allows Python expressions to be evaluated
# inside ROS 2 launch conditions.
from launch.substitutions import PythonExpression

# Fore provides terminal text colors using Colorama.
from colorama import Fore

# Command can execute a command and use its output as a substitution.
from launch.substitutions import Command


# ============================================================
# 2. MAIN LAUNCH FUNCTION
# ============================================================

def generate_launch_description():

    # --------------------------------------------------------
    # 2.1 DEFINE THE MAP SAVE DIRECTORY
    # --------------------------------------------------------

    # Get the current user's home directory.
    #
    # For example:
    # /home/jetson
    #
    # Create the path to the map directory.
    #
    # Final path:
    # /home/jetson/map
    map_folder_dir = os.path.join(
        os.path.expanduser('~'),
        'map'
    )

    # --------------------------------------------------------
    # 2.2 DECLARE LAUNCH ARGUMENTS
    # --------------------------------------------------------

    # This list stores all launch arguments.
    declared_arguments = []

    # Argument 1: map_name
    #
    # Defines the name of the map that will be saved.
    #
    # Default value: map
    #
    # Example:
    # ros2 launch package save_map.launch.py map_name=my_map
    declared_arguments.append(
        DeclareLaunchArgument(
            "map_name",
            default_value='map',
            description="Naming the saved map"
        )
    )

    # Argument 2: map_type
    #
    # Defines which type of map should be saved.
    #
    # Available options:
    # 1. gridmap
    # 2. posegraph
    #
    # Default value: gridmap
    declared_arguments.append(
        DeclareLaunchArgument(
            "map_type",
            default_value="gridmap",
            description=(
                "Map type to save: "
                "gridmap or posegraph"
            )
        )
    )

    # --------------------------------------------------------
    # 2.3 READ THE LAUNCH ARGUMENT VALUES
    # --------------------------------------------------------

    # Read the map_name argument.
    # If the user does not provide a value, it uses "map".
    map_name = LaunchConfiguration("map_name")

    # Read the map_type argument.
    # If the user does not provide a value, it uses "gridmap".
    map_type = LaunchConfiguration("map_type")

    # ========================================================
    # 3. SAVE THE SLAM TOOLBOX POSE GRAPH
    # ========================================================

    # GroupAction groups launch actions together.
    #
    # If map_type is "posegraph", this action will run.
    #
    # Otherwise, it will be skipped.
    save_posegraph = GroupAction(

        # Check whether the map_type argument equals "posegraph".
        condition=IfCondition(
            PythonExpression([
                "'",
                map_type,
                "' == 'posegraph'"
            ])
        ),

        actions=[

            # Execute an external ROS 2 service call.
            ExecuteProcess(

                # Command that will be executed:
                #
                # ros2 service call
                # /slam_toolbox/serialize_map
                # slam_toolbox/srv/SerializePoseGraph
                #
                # The filename is constructed using:
                # map_folder_dir + map_name
                cmd=[
                    'ros2',
                    'service',
                    'call',
                    '/slam_toolbox/serialize_map',

                    # Service type used by SLAM Toolbox.
                    'slam_toolbox/srv/SerializePoseGraph',

                    # Pass the full output filename to the service.
                    [
                        '{filename: "',
                        PathJoinSubstitution([
                            map_folder_dir,
                            map_name
                        ]),
                        '"}'
                    ]
                ],

                # Do not execute the command through a shell.
                shell=False,

                # Keep terminal output interactive.
                emulate_tty=True,

                # Display command output in the terminal.
                output='screen'
            )
        ]
    )

    # ========================================================
    # 4. SAVE A STANDARD 2D GRID MAP
    # ========================================================

    # Start the map_saver_cli executable from Nav2.
    #
    # This action runs only when map_type is "gridmap".
    save_map = Node(

        # ROS 2 package containing the map saver.
        package='nav2_map_server',

        # Executable responsible for saving occupancy grid maps.
        executable='map_saver_cli',

        # Arguments passed to map_saver_cli.
        arguments=[

            # -f specifies the output map filename.
            #
            # Example:
            # /home/jetson/map/my_map
            #
            # The map saver normally creates files such as:
            # my_map.yaml
            # my_map.pgm
            '-f',

            PathJoinSubstitution([
                map_folder_dir,
                map_name
            ]),

            # Threshold below which cells are considered free.
            '--free',
            '0.196',

            # Threshold above which cells are considered occupied.
            '--occ',
            '0.65'
        ],

        # Run this node only when map_type equals "gridmap".
        condition=IfCondition(
            PythonExpression([
                "'",
                map_type,
                "' == 'gridmap'"
            ])
        )
    )

    # ========================================================
    # 5. RETURN THE COMPLETE LAUNCH DESCRIPTION
    # ========================================================

    # ROS 2 executes the actions listed here.
    return LaunchDescription([

        # Register the launch arguments.
        *declared_arguments,

        # Save a standard occupancy grid map if selected.
        save_map,

        # Save a SLAM Toolbox pose graph if selected.
        save_posegraph,
    ])
