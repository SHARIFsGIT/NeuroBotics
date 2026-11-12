
# ============================================================
# 1. IMPORT REQUIRED LIBRARIES
# ============================================================

# os provides functions for working with directories and file paths.
import os

# Finds the installation directory of a ROS 2 package.
# This is useful for locating configuration files and launch files.
from ament_index_python.packages import get_package_share_directory

# Main class used to create a ROS 2 launch description.
from launch import LaunchDescription

# Reads values passed as launch arguments.
from launch.substitutions import LaunchConfiguration

# Starts ROS 2 nodes.
from launch_ros.actions import Node

# DeclareLaunchArgument:
# Allows users to configure values when starting the launch file.
#
# IncludeLaunchDescription:
# Includes another ROS 2 launch file.
#
# TimerAction:
# Delays the execution of launch actions.
#
# ExecuteProcess:
# Executes an external command, such as a ROS 2 service call.
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    TimerAction,
    ExecuteProcess
)

# Allows us to load another Python-based ROS 2 launch file.
from launch.launch_description_sources import PythonLaunchDescriptionSource


# ============================================================
# 2. MAIN LAUNCH FUNCTION
# ============================================================

def generate_launch_description():

    # ========================================================
    # 2.1 DECLARE OUTPUT FILE PATH ARGUMENT
    # ========================================================

    # Declare a launch argument called "output_file_path".
    #
    # This argument defines where the AprilTag recorder
    # will save the detected AprilTag poses.
    #
    # The default path is constructed using:
    #
    # m3pro_bringup package
    #     └── config
    #          └── aritag_relocation.yaml
    #
    # get_package_share_directory() finds the installed
    # package's share directory.
    output_file_path_arg = DeclareLaunchArgument(

        # Name of the launch argument.
        'output_file_path',

        # Default YAML output file location.
        default_value=os.path.join(
            get_package_share_directory("m3pro_bringup"),
            "config",
            "aritag_relocation.yaml"
        ),

        # Description displayed when inspecting launch arguments.
        description='Path to the output YAML file for saving AprilTag poses'
    )

    # ========================================================
    # 2.2 DECLARE TARGET FRAME ARGUMENT
    # ========================================================

    # Declare another launch argument called "target_frame".
    #
    # This defines the coordinate frame in which
    # AprilTag poses should be recorded.
    #
    # The default frame is "map".
    #
    # In ROS 2, the map frame normally represents
    # the global coordinate system used for navigation.
    target_frame_arg = DeclareLaunchArgument(

        # Name of the launch argument.
        'target_frame',

        # Default coordinate frame.
        default_value='map',

        # Description of this argument.
        description='Target coordinate frame for recording AprilTag poses'
    )

    # ========================================================
    # 3. START THE APRILTAG RECORDER NODE
    # ========================================================

    # Create a ROS 2 node that records AprilTag poses.
    apriltag_recorder_node = Node(

        # Package containing the AprilTag recorder executable.
        package='apriltag_localization',

        # Executable that performs AprilTag pose recording.
        executable='apriltag_recorder',

        # Name assigned to the running ROS 2 node.
        name='apriltag_recorder',

        # Display the node's output in the terminal.
        output='screen',

        # Pass parameters to the recorder node.
        parameters=[{

            # Tell the recorder where to save the detected poses.
            #
            # LaunchConfiguration reads the value supplied
            # through the output_file_path launch argument.
            'output_file_path': LaunchConfiguration(
                'output_file_path'
            ),

            # Tell the recorder which coordinate frame to use.
            #
            # By default, this is the "map" frame.
            'target_frame': LaunchConfiguration(
                'target_frame'
            ),

        }]
    )

    # ========================================================
    # 4. INCLUDE THE SLAM TOOLBOX NAVIGATION LAUNCH FILE
    # ========================================================

    # Start another ROS 2 launch file.
    #
    # This launch file is responsible for the navigation
    # and SLAM Toolbox localization setup.
    navigation_launch = IncludeLaunchDescription(

        # Find the M3Pro_navigation package's launch directory
        # and load toolbox_location_nav.launch.py.
        PythonLaunchDescriptionSource([

            os.path.join(
                get_package_share_directory('M3Pro_navigation'),
                'launch',
                'toolbox_location_nav.launch.py'
            )

        ]),

        # Pass arguments to the included navigation launch file.
        launch_arguments={

            # Use the RViz configuration designed for AprilTag recording.
            #
            # File:
            # m3pro_bringup/rviz/aritag_record.rviz
            "rviz_config": os.path.join(
                get_package_share_directory('m3pro_bringup'),
                'rviz',
                'aritag_record.rviz'
            ),

            # Set the ROS 2 logging level to info.
            #
            # This displays informational messages,
            # warnings and errors in the terminal.
            "log_level": "info",

        }.items()
    )

    # ========================================================
    # 5. ENABLE APRILTAG DETECTION AFTER A DELAY
    # ========================================================

    # Create a TimerAction.
    #
    # TimerAction waits for a specified number of seconds
    # before executing its actions.
    #
    # Here, we wait 8 seconds before enabling detection.
    #
    # This gives the recorder and navigation systems
    # some time to start.
    call_detection_service = TimerAction(

        # Delay before executing the service call.
        period=8.0,

        # Actions to execute after the delay.
        actions=[

            # Execute a ROS 2 service call from the terminal.
            ExecuteProcess(

                # The command is equivalent to:
                #
                # ros2 service call /control_detection
                # apriltag_localization/srv/ControlDetection
                # "{command: 1}"
                #
                # This requests the AprilTag detection system
                # to enable detection.
                cmd=[

                    # ROS 2 command-line tool.
                    'ros2',

                    # Call a ROS 2 service.
                    'service',

                    'call',

                    # Name of the service.
                    '/control_detection',

                    # Service type.
                    'apriltag_localization/srv/ControlDetection',

                    # Request data.
                    #
                    # command: 1 is the value sent to the service.
                    '{command: 1}'
                ],

                # Display the service call output in the terminal.
                output='screen'
            )
        ]
    )

    # ========================================================
    # 6. RETURN THE COMPLETE LAUNCH DESCRIPTION
    # ========================================================

    # Return all launch actions.
    #
    # ROS 2 processes these actions when this launch file starts.
    return LaunchDescription([

        # Register the output YAML path argument.
        output_file_path_arg,

        # Register the target coordinate frame argument.
        target_frame_arg,

        # Start the AprilTag recorder node.
        apriltag_recorder_node,

        # Start the SLAM Toolbox navigation launch file.
        navigation_launch,

        # Wait 8 seconds and then enable AprilTag detection.
        call_detection_service

    ])


# ============================================================
# END OF LAUNCH FILE
# ============================================================
