
#!/usr/bin/env python3

# ============================================================
# IMPORT LIBRARIES
# ============================================================

# os: Used to construct file paths and access the user's home directory.
import os

# LaunchDescription: Defines all actions that ROS 2 should execute.
from launch import LaunchDescription

# DeclareLaunchArgument: Allows users to configure launch arguments.
from launch.actions import DeclareLaunchArgument

# LaunchConfiguration: Reads values passed through launch arguments.
from launch.substitutions import LaunchConfiguration

# Node: Used to start ROS 2 nodes.
from launch_ros.actions import Node

# Finds the installed share directory of a ROS 2 package.
from ament_index_python.packages import get_package_share_directory


# ============================================================
# MAIN LAUNCH DESCRIPTION FUNCTION
# ============================================================

def generate_launch_description():

    # ========================================================
    # 1. FIND CONFIGURATION FILES AND MODEL PATHS
    # ========================================================

    # Locate the common.yaml configuration file.
    #
    # Package: m3pro_bringup
    # Directory: config
    # File: common.yaml
    #
    # This configuration file is passed to the PCL segmentation node.
    commom_param_file = os.path.join(
        get_package_share_directory('m3pro_bringup'),
        'config',
        'common.yaml'
    )

    # Construct the path to the Super Tracker ONNX model.
    #
    # os.path.expanduser('~') finds the current user's home directory.
    #
    # Example:
    # /home/jetson/MODELS/tracker/super_track_sim.onnx
    #
    # ONNX is a format for storing machine learning models.
    super_track_model = os.path.join(
        os.path.expanduser('~'),
        'MODELS',
        'tracker',
        'super_track_sim.onnx'
    )

    # Locate the RViz configuration file.
    #
    # Package: m3pro_bringup
    # Directory: rviz
    # File: super_tracker.rviz
    #
    # This file contains the saved RViz display configuration.
    rviz_config = os.path.join(
        get_package_share_directory('m3pro_bringup'),
        'rviz',
        'super_tracker.rviz'
    )

    # ========================================================
    # 2. DECLARE LAUNCH ARGUMENTS
    # ========================================================

    # Create a list to store launch arguments.
    declared_arguments = []

    # --------------------------------------------------------
    # DISPLAY WINDOWS ONLY TRACK
    # --------------------------------------------------------

    # Declare an argument that controls the
    # display_windows_only_track parameter.
    #
    # Default value: false
    #
    # The exact behavior depends on the implementation
    # of the smart_tracker package.
    declared_arguments.append(
        DeclareLaunchArgument(
            "display_windows_only_track",
            default_value='false',
            description=""
        )
    )

    # --------------------------------------------------------
    # DISPLAY WINDOWS
    # --------------------------------------------------------

    # Declare an argument that controls whether display windows
    # are enabled in the Super Tracker node.
    #
    # Default value: true
    declared_arguments.append(
        DeclareLaunchArgument(
            "display_windows",
            default_value='true',
            description=""
        )
    )

    # ========================================================
    # 3. SUPER TRACKER NODE
    # ========================================================

    # Start the Super Tracker node.
    #
    # Package: smart_tracker
    # Executable: super_tracker
    # Node name: super_tracker
    #
    # This node uses the ONNX model to perform object tracking.
    tracker_node = Node(

        package='smart_tracker',

        executable='super_tracker',

        name='super_tracker',

        # ----------------------------------------------------
        # NODE PARAMETERS
        # ----------------------------------------------------

        parameters=[{

            # Controls the display_windows_only_track parameter.
            #
            # Its value comes from the launch argument declared above.
            'display_windows_only_track': LaunchConfiguration(
                'display_windows_only_track'
            ),

            # Controls the display_windows parameter.
            #
            # Its value also comes from a launch argument.
            'display_windows': LaunchConfiguration(
                'display_windows'
            ),

            # Path to the ONNX tracking model.
            'model_path': super_track_model,

        }],

        # ----------------------------------------------------
        # TOPIC REMAPPING
        # ----------------------------------------------------

        # Remap the node's /image_raw topic to the Orbbec camera topic.
        #
        # Original topic:
        # /image_raw
        #
        # New topic:
        # /camera/color/image_raw
        #
        # This allows the Super Tracker node to receive
        # images from the Orbbec RGB camera.
        remappings=[
            (
                '/image_raw',
                '/camera/color/image_raw'
            )
        ],

        # Display node output in the terminal.
        output='screen'

        # Optional debugging configuration:
        # prefix='gdb -ex run --args'
        #
        # Uncomment this prefix if you want to run the node
        # using GDB for debugging.
    )

    # ========================================================
    # 4. POINT CLOUD SEGMENTATION NODE
    # ========================================================

    # Start the PCL segmentation node.
    #
    # Package: smart_tracker
    # Executable: pcl_segment
    # Node name: pcl_segment
    #
    # PCL stands for Point Cloud Library.
    #
    # This node is intended to perform point-cloud segmentation
    # for a region of interest (ROI).
    #
    # Its configuration parameters are loaded from common.yaml.
    pclsegment_node = Node(

        package='smart_tracker',

        executable='pcl_segment',

        name='pcl_segment',

        # Load the common configuration file.
        parameters=[
            commom_param_file
        ],

        # Display node output in the terminal.
        output='screen'
    )

    # ========================================================
    # 5. RVIZ2 VISUALIZATION NODE
    # ========================================================

    # Start RViz2.
    #
    # Package: rviz2
    # Executable: rviz2
    # Node name: rviz2
    rviz_node = Node(

        package='rviz2',

        executable='rviz2',

        name='rviz2',

        # Load the saved RViz configuration.
        #
        # -d tells RViz2 to open the specified configuration file.
        arguments=[
            '-d',
            rviz_config
        ],

        # Display RViz output in the terminal.
        output='screen'
    )

    # ========================================================
    # 6. RETURN THE COMPLETE LAUNCH DESCRIPTION
    # ========================================================

    # Start all the components together.
    #
    # *declared_arguments:
    # Adds the two launch arguments.
    #
    # tracker_node:
    # Starts the ONNX-based Super Tracker.
    #
    # pclsegment_node:
    # Starts the point-cloud segmentation node.
    #
    # rviz_node:
    # Opens RViz2 for visualization.
    return LaunchDescription([

        *declared_arguments,

        tracker_node,

        pclsegment_node,

        rviz_node

    ])
