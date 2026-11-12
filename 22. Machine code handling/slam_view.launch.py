
#!/usr/bin/env python3

# ============================================================
# 1. IMPORT ROS 2 LAUNCH LIBRARIES
# ============================================================

# Node allows us to start a ROS 2 node or program
from launch_ros.actions import Node

# IncludeLaunchDescription allows us to include another launch file
from launch.actions import IncludeLaunchDescription

# Finds the installed location of a ROS 2 package
from ament_index_python.packages import get_package_share_directory

# LaunchDescription contains all the actions we want ROS 2 to execute
from launch import LaunchDescription

# Allows us to create arguments that users can change when launching
from launch.actions import DeclareLaunchArgument

# Allows us to run external system commands
from launch.actions import ExecuteProcess

# Allows us to start or stop actions based on conditions
from launch.conditions import IfCondition, UnlessCondition

# Allows us to read launch arguments and their values
from launch.substitutions import LaunchConfiguration

# Allows us to change ROS 2 topic names (remapping)
from launch_ros.actions import SetRemap

# Finds the share directory of a ROS 2 package
from launch_ros.substitutions import FindPackageShare

# Allows us to include Python launch files
from launch.launch_description_sources import PythonLaunchDescriptionSource

# Allows us to shut down the launch system
from launch.actions import Shutdown

# Python library for working with file paths
import os


# ============================================================
# 2. MAIN FUNCTION: GENERATE LAUNCH DESCRIPTION
# ============================================================

# ROS 2 automatically calls this function when we run the launch file

def generate_launch_description():

    # ========================================================
    # 3. CONFIGURE SIMULATION TIME
    # ========================================================

    # ROS 2 can use two different types of time:
    #
    # Real time:
    # Uses the actual clock of the computer or robot.
    #
    # Simulation time:
    # Uses simulated time provided by a simulator or /clock topic.
    #
    # Since this launch file is intended for a real robot,
    # simulation time is disabled.

    use_sim_time = LaunchConfiguration(
        'use_sim_time',
        default='false'
    )


    # ========================================================
    # 4. FIND THE RVIZ CONFIGURATION FILE
    # ========================================================

    # RViz is a visualization program for ROS 2.
    #
    # A configuration file saves the RViz settings, such as:
    # - Fixed frame
    # - Robot model
    # - Laser scan display
    # - Map display
    # - TF display
    # - Camera display
    #
    # Instead of configuring RViz manually every time,
    # we load a previously saved configuration file.

    rviz_config = LaunchConfiguration(
        'rviz_config',

        # Find the installed slam_mapping package directory
        default=os.path.join(

            get_package_share_directory('slam_mapping'),

            # Open its rviz folder
            'rviz',

            # Select the RViz configuration file
            'slam_rviz.rviz'
        )
    )


    # ========================================================
    # 5. DECLARE RVIZ CONFIGURATION ARGUMENT
    # ========================================================

    # DeclareLaunchArgument makes rviz_config available
    # as a launch argument.
    #
    # This means users can provide another RViz configuration
    # file when starting the launch file.

    rviz_config_arg = DeclareLaunchArgument(

        # Name of the launch argument
        'rviz_config',

        # Default configuration file
        default_value=rviz_config
    )


    # ========================================================
    # 6. CREATE THE RVIZ2 NODE
    # ========================================================

    # Node tells ROS 2 to start a program.
    #
    # Here we want to start RViz2.

    rviz_node = Node(

        # ROS 2 package containing RViz
        package='rviz2',

        # Executable program inside the package
        executable='rviz2',

        # Name of the ROS 2 node
        name='rviz2',

        # Display messages and errors in the terminal
        output='screen',

        # Arguments passed to the RViz program
        arguments=[

            # -d tells RViz to load a configuration file
            '-d',

            # Load our saved RViz settings
            rviz_config,

            # Tell RViz whether to use simulation time
            use_sim_time
        ]
    )


    # ========================================================
    # 7. RETURN THE COMPLETE LAUNCH DESCRIPTION
    # ========================================================

    # LaunchDescription is a list of actions that ROS 2 executes.
    #
    # First:
    # Declare the RViz configuration argument.
    #
    # Second:
    # Start the RViz2 node.

    return LaunchDescription([

        # Register the RViz configuration argument
        rviz_config_arg,

        # Start RViz2 with the selected configuration
        rviz_node,

    ])


# ============================================================
# END OF LAUNCH FILE
# ============================================================
