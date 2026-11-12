import os   # (System file operations) - Lets Python work with folders and file paths on your computer.

# A ROS 2 tool that finds the installation directory of a package.
from ament_index_python.packages import get_package_share_directory

# The main container that holds all the actions ROS 2 should execute.
from launch import LaunchDescription

# DeclareLaunchArgument lets users configure launch settings.
# TimerAction can delay the execution of launch actions.
from launch.actions import DeclareLaunchArgument,TimerAction

# Allows this launch file to start another launch file.
from launch.actions import IncludeLaunchDescription

# Tells ROS 2 how to load another launch file written in Python.
from launch.launch_description_sources import PythonLaunchDescriptionSource

# LaunchConfiguration represents the value of a launch argument.
# It allows the launch system to retrieve the argument's value when needed.
from launch.substitutions import LaunchConfiguration# References the value of a launch argument.

# Node is used to start a ROS 2 node, which is an individual program in the ROS 2 system.
from launch_ros.actions import Node

# Imports Python's time module, which provides tools for working with time and delays.
import time


# ROS 2 calls this function to obtain the actions that should be launched.
def generate_launch_description():

    # Create a launch configuration named 'use_sim_time'.
    # By default, 'false' means RViz uses the normal ROS/system clock
    # instead of a simulation clock, such as the one provided by Gazebo.
    use_sim_time = LaunchConfiguration('use_sim_time', default='false')

    # Build the full path to the RViz configuration file.
    # get_package_share_directory('M3Pro_navigation') finds the installed
    # M3Pro_navigation package's shared directory.
    # 'rviz' is the folder containing the RViz configuration.
    # 'nav2.rviz' stores RViz display settings, such as panels, displays,
    # topic selections, and the initial view.
    rviz_config_dir = os.path.join(
        get_package_share_directory('M3Pro_navigation'),
        'rviz',
        'nav2.rviz')

    # Create the complete list of launch actions and return it to ROS 2.
    # In this example, the launch file declares an argument and starts RViz.
    return LaunchDescription([

        # Declare a launch argument called 'use_sim_time'.
        # This setting can be overridden when the launch file is started.
        DeclareLaunchArgument(
            'use_sim_time',

            # Set the default value to 'false'.
            # Use 'true' when RViz should follow a simulation clock.
            default_value='false',

            # Explain the purpose of this launch argument.
            description='Use simulation (Gazebo) clock if true'),

        # Start RViz, the ROS 2 visualization tool.
        # RViz can display information such as maps, laser scans,
        # robot models, coordinate frames, and navigation paths.
        Node(
            # The ROS 2 package that contains the RViz application.
            package='rviz2',

            # The executable program to start from the rviz2 package.
            executable='rviz2',

            # Assign the node the name 'rviz2' in the ROS 2 system.
            name='rviz2',

            # Pass command-line arguments to RViz.
            # '-d' tells RViz to load the specified configuration file.
            # rviz_config_dir contains the full path to nav2.rviz.
            arguments=['-d', rviz_config_dir],

            # Pass ROS 2 parameters to the RViz node.
            # 'use_sim_time' determines whether RViz uses simulation time.
            # The value comes from the launch configuration defined above.
            parameters=[{'use_sim_time': use_sim_time}],

            # Display RViz's log messages in the terminal.
            output='screen'),
    ])