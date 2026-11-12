
# ============================================================
# 1. IMPORT REQUIRED ROS 2 LIBRARIES
# ============================================================

# os provides functions for working with directories and file paths.
import os

# Finds the installation directory of a ROS 2 package.
from ament_index_python.packages import get_package_share_directory

# Main class used to create a ROS 2 launch description.
from launch import LaunchDescription

# DeclareLaunchArgument:
# Allows users to configure launch arguments.
#
# GroupAction:
# Groups multiple launch actions together.
#
# IncludeLaunchDescription:
# Includes another ROS 2 launch file.
#
# LogInfo:
# Prints an informational message in the terminal.
#
# RegisterEventHandler:
# Registers an event handler for launch events.
from launch.actions import (
    DeclareLaunchArgument,
    GroupAction,
    IncludeLaunchDescription,
    LogInfo,
    RegisterEventHandler
)

# LoadComposableNodes:
# Loads ROS 2 components into a component container.
#
# Node:
# Starts a normal ROS 2 node.
#
# PushRosNamespace:
# Adds a namespace to nodes launched inside a group.
#
# ComposableNodeContainer:
# Starts a container for composable ROS 2 nodes.
from launch_ros.actions import (
    LoadComposableNodes,
    Node,
    PushRosNamespace,
    ComposableNodeContainer
)

# Loads another Python-based ROS 2 launch file.
from launch.launch_description_sources import PythonLaunchDescriptionSource

# IfCondition allows an action to run only when a condition is true.
from launch.conditions import IfCondition

# LaunchConfiguration reads values passed through launch arguments.
#
# PythonExpression evaluates Python expressions in launch conditions.
#
# LocalSubstitution provides information about the local launch context.
#
# PathJoinSubstitution joins paths using launch substitutions.
from launch.substitutions import (
    LaunchConfiguration,
    PythonExpression,
    LocalSubstitution,
    PathJoinSubstitution
)


# ============================================================
# 2. MAIN LAUNCH FUNCTION
# ============================================================

def generate_launch_description():

    # --------------------------------------------------------
    # 2.1 DEFINE THE MAP DIRECTORY
    # --------------------------------------------------------

    # Get the current user's home directory.
    #
    # Example:
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
    # 2.2 PREPARE THE LAUNCH ARGUMENTS
    # --------------------------------------------------------

    # This list stores all arguments declared in this launch file.
    declared_arguments = []

    # Find the installation directory of the M3Pro_navigation package.
    #
    # This directory contains navigation configuration files,
    # parameter files, RViz configurations and launch files.
    m3pronav_dir = os.path.join(
        get_package_share_directory('M3Pro_navigation')
    )

    # ========================================================
    # 3. DECLARE MAP ARGUMENT
    # ========================================================

    # The "map" argument defines the name of the occupancy grid map.
    #
    # Default:
    # map.yaml
    #
    # The file is expected inside:
    # ~/map/
    #
    # Example:
    # ~/map/map.yaml
    declared_arguments.append(
        DeclareLaunchArgument(
            "map",
            default_value="map.yaml",
            description="Map name"
        )
    )

    # ========================================================
    # 4. DECLARE GUI ARGUMENT
    # ========================================================

    # The "gui" argument controls whether RViz should start.
    #
    # True  = Start RViz.
    # False = Do not start RViz.
    #
    # Default value: True
    declared_arguments.append(
        DeclareLaunchArgument(
            "gui",
            default_value='True',
            description=(
                "If RViz is used, set to True. "
                "If False, RViz will not be launched."
            )
        )
    )

    # ========================================================
    # 5. DECLARE SLAM TOOLBOX POSE MAP ARGUMENT
    # ========================================================

    # This argument defines the name of the saved SLAM Toolbox
    # pose graph file.
    #
    # Default:
    # map
    #
    # The file is expected inside:
    # ~/map/
    declared_arguments.append(
        DeclareLaunchArgument(
            "pose_map",
            default_value="map",
            description=""
        )
    )

    # ========================================================
    # 6. DECLARE RELOCATION ARGUMENT
    # ========================================================

    # Controls the relocation option in the robot base launch file.
    #
    # Default:
    # false
    declared_arguments.append(
        DeclareLaunchArgument(
            'relocation',
            default_value='false'
        )
    )

    # ========================================================
    # 7. DECLARE APRILTAG DETECTION ARGUMENT
    # ========================================================

    # Controls whether AprilTag detection is enabled.
    #
    # This value is passed to car_base.launch.py.
    #
    # Default:
    # false
    declared_arguments.append(
        DeclareLaunchArgument(
            'detection_enabled',
            default_value='false'
        )
    )

    # ========================================================
    # 8. DECLARE NAVIGATION PARAMETER FILE
    # ========================================================

    # Nav2 needs a YAML parameter file to configure its nodes.
    #
    # This file contains navigation settings such as:
    # - Controller parameters.
    # - Planner parameters.
    # - Costmap configuration.
    # - Behavior settings.
    # - Navigation-related frame and topic settings.
    #
    # Default file:
    # M3Pro_navigation/param/yahboom_M3Pro.yaml
    declared_arguments.append(
        DeclareLaunchArgument(
            "params_file",

            default_value=os.path.join(
                get_package_share_directory("M3Pro_navigation"),
                "param",
                "yahboom_M3Pro.yaml"
            ),

            description="Full path to parameter file to load"
        )
    )

    # ========================================================
    # 9. DECLARE SIMULATION TIME ARGUMENT
    # ========================================================

    # Controls whether ROS 2 nodes use simulation time.
    #
    # True  = Use the /clock topic, usually from Gazebo.
    # False = Use the real system clock.
    #
    # Default:
    # False
    declared_arguments.append(
        DeclareLaunchArgument(
            "use_sim_time",
            default_value="False",
            description="Use simulation (Gazebo) clock if true"
        )
    )

    # ========================================================
    # 10. DECLARE RVIZ CONFIGURATION ARGUMENT
    # ========================================================

    # Defines which RViz configuration file should be loaded.
    #
    # Default file:
    # M3Pro_navigation/rviz/nav2.rviz
    declared_arguments.append(
        DeclareLaunchArgument(
            "rviz_config",

            default_value=os.path.join(
                m3pronav_dir,
                'rviz',
                'nav2.rviz'
            )
        )
    )

    # ========================================================
    # 11. DECLARE LOG LEVEL ARGUMENT
    # ========================================================

    # Controls the amount of logging information.
    #
    # Common log levels:
    # debug
    # info
    # warn
    # error
    # fatal
    #
    # Default:
    # info
    declared_arguments.append(
        DeclareLaunchArgument(
            "log_level",
            default_value="info",
            description="Log level"
        )
    )

    # ========================================================
    # 12. INITIALIZE LAUNCH CONFIGURATIONS
    # ========================================================

    # Read the map filename supplied by the user.
    map = LaunchConfiguration("map")

    # Build the complete occupancy grid map path.
    #
    # Example:
    # /home/jetson/map/map.yaml
    map_dir = PathJoinSubstitution([
        map_folder_dir,
        map
    ])

    # Read the pose graph filename.
    pose_map = PathJoinSubstitution([
        map_folder_dir,
        LaunchConfiguration("pose_map")
    ])

    # Read the Nav2 parameter file path.
    params_file = LaunchConfiguration("params_file")

    # Read the simulation time setting.
    #
    # The declared argument above already provides a default.
    use_sim_time = LaunchConfiguration(
        "use_sim_time",
        default="false"
    )

    # Read the RViz configuration path.
    rviz_config = LaunchConfiguration("rviz_config")

    # Read the logging level.
    log_level = LaunchConfiguration("log_level")

    # ========================================================
    # 13. START THE ROBOT BASE
    # ========================================================

    # Include the car_base.launch.py launch file.
    #
    # This launch file is responsible for starting
    # the robot's base-related components.
    carbase_launch = IncludeLaunchDescription(

        # Find the m3pro_bringup package and its launch directory.
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory('m3pro_bringup'),
                'launch',
                'car_base.launch.py'
            )
        ),

        # Pass arguments to car_base.launch.py.
        launch_arguments={

            # Set the logging level.
            'log_level': log_level,

            # Pass the relocation setting.
            'relocation': LaunchConfiguration('relocation'),

            # Pass the AprilTag detection setting.
            'detection_enabled': LaunchConfiguration(
                'detection_enabled'
            ),

        }.items()
    )

    # ========================================================
    # 14. FIND THE MODIFIED NAV2 LAUNCH FILE
    # ========================================================

    # This is the modified Navigation2 launch file.
    #
    # According to the original code comments, this version
    # disables the normal AMCL localization functionality.
    #
    # SLAM Toolbox will instead provide localization.
    nav2_launch_mod = os.path.join(
        m3pronav_dir,
        'launch',
        'bringup_mod.launch.py'
    )

    # ========================================================
    # 15. FIND THE SLAM TOOLBOX LOCALIZATION LAUNCH FILE
    # ========================================================

    # Locate the SLAM Toolbox localization launch file.
    #
    # This launch file starts the SLAM Toolbox localization system.
    slamtoolbox_localization_launch_file = os.path.join(
        get_package_share_directory('slam_mapping'),
        'launch',
        'localization_launch.py'
    )

    # ========================================================
    # 16. START NAV2 AND SLAM TOOLBOX LOCALIZATION
    # ========================================================

    # GroupAction allows us to group multiple launch actions.
    #
    # Here, we group:
    # 1. Navigation2 startup.
    # 2. SLAM Toolbox localization startup.
    # 3. A message indicating that navigation has started.
    slamtoolbox_localization_nav = GroupAction(

        actions=[

            # ------------------------------------------------
            # 16.1 START NAVIGATION2
            # ------------------------------------------------

            # Include the modified Nav2 launch file.
            #
            # This version is configured to run without
            # the normal AMCL localization process.
            IncludeLaunchDescription(

                # Load bringup_mod.launch.py.
                PythonLaunchDescriptionSource(
                    nav2_launch_mod
                ),

                # Pass configuration values to Nav2.
                launch_arguments={

                    # Provide the occupancy grid map path.
                    "map": map_dir,

                    # Provide the Nav2 parameter YAML file.
                    "params_file": params_file,

                    # Enable or disable simulation time.
                    "use_sim_time": use_sim_time,

                    # Set the logging level.
                    "log_level": log_level,

                }.items()
            ),

            # ------------------------------------------------
            # 16.2 START SLAM TOOLBOX LOCALIZATION
            # ------------------------------------------------

            # Include the SLAM Toolbox localization launch file.
            IncludeLaunchDescription(

                # Load localization_launch.py.
                PythonLaunchDescriptionSource(
                    slamtoolbox_localization_launch_file
                ),

                # Pass the pose graph and clock settings.
                launch_arguments={

                    # Provide the saved pose graph path.
                    "pose_map": pose_map,

                    # Use the selected simulation time setting.
                    "use_sim_time": use_sim_time,

                }.items()
            ),

            # ------------------------------------------------
            # 16.3 DISPLAY NAVIGATION START MESSAGE
            # ------------------------------------------------

            # Print an informational message in the terminal.
            LogInfo(
                msg=[
                    "====================",
                    "Robot-M3Pro Navigation Start with ",
                    "SlamToolbox localization",
                    "===================="
                ]
            )
        ]
    )

    # ========================================================
    # 17. START RVIZ
    # ========================================================

    # Create an RViz node.
    #
    # RViz is a visualization tool used to display:
    # - Robot model.
    # - Laser scan data.
    # - Map.
    # - TF coordinate frames.
    # - Navigation paths.
    # - Robot position.
    rviz_node = Node(

        # ROS 2 package containing RViz.
        package='rviz2',

        # RViz executable.
        executable='rviz2',

        # Name of the node.
        name='rviz2',

        # Load the selected RViz configuration file.
        #
        # -d tells RViz which configuration file to load.
        arguments=[
            '-d',
            rviz_config
        ],

        # Pass the simulation time parameter to RViz.
        parameters=[
            {
                'use_sim_time': use_sim_time
            }
        ],

        # Display RViz output in the terminal.
        output='screen',

        # Start RViz only when gui is True.
        #
        # If gui:=False is passed when launching,
        # this RViz node will not start.
        condition=IfCondition(
            LaunchConfiguration('gui')
        )
    )

    # ========================================================
    # 18. RETURN THE COMPLETE LAUNCH DESCRIPTION
    # ========================================================

    # Return all launch actions to ROS 2.
    return LaunchDescription([

        # Register all declared launch arguments.
        *declared_arguments,

        # Start RViz if the GUI option is enabled.
        rviz_node,

        # Start the robot base.
        carbase_launch,

        # Start Nav2 and SLAM Toolbox localization.
        slamtoolbox_localization_nav

    ])


# ============================================================
# END OF LAUNCH FILE
# ============================================================
