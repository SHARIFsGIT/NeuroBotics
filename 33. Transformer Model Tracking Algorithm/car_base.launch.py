
#!/usr/bin/env python3

# ============================================================
# IMPORT LIBRARIES
# ============================================================

# os: Used to construct file and directory paths.
import os

# Finds the installed share directory of a ROS 2 package.
from ament_index_python.packages import get_package_share_directory

# LaunchDescription: Defines all actions that ROS 2 should execute.
from launch import LaunchDescription

# IncludeLaunchDescription: Allows us to include other launch files.
from launch.actions import IncludeLaunchDescription

# PythonLaunchDescriptionSource: Loads another Python launch file.
from launch.launch_description_sources import PythonLaunchDescriptionSource

# Node: Used to start ROS 2 nodes.
from launch_ros.actions import Node

# DeclareLaunchArgument: Defines arguments that users can pass
# when starting this launch file.
from launch.actions import DeclareLaunchArgument

# Command: Executes a command and uses its output as a substitution.
# LaunchConfiguration: Reads the value of a launch argument.
# PythonExpression: Allows Python expressions in launch substitutions.
from launch.substitutions import (
    Command,
    LaunchConfiguration,
    PythonExpression
)

# IfCondition: Runs a launch action only when a condition is true.
from launch.conditions import IfCondition

# ExecuteProcess: Executes an external system command or process.
from launch.actions import ExecuteProcess

# ParameterValue: Allows us to specify the expected type of a parameter.
from launch_ros.parameter_descriptions import ParameterValue


# ============================================================
# MAIN LAUNCH DESCRIPTION FUNCTION
# ============================================================

def generate_launch_description():

    # ========================================================
    # 1. DECLARE LAUNCH ARGUMENTS
    # ========================================================

    # Create a list to store launch arguments.
    declared_arguments = []

    # --------------------------------------------------------
    # RELOCATION ARGUMENT
    # --------------------------------------------------------

    # Controls whether the robot should use the relocation process.
    #
    # Default value: false
    #
    # This value is passed to the AprilTag relocation launch file.
    declared_arguments.append(
        DeclareLaunchArgument(
            'relocation',
            default_value='false'
        )
    )

    # --------------------------------------------------------
    # DETECTION ENABLED ARGUMENT
    # --------------------------------------------------------

    # Controls whether AprilTag detection should be enabled.
    #
    # Default value: false
    #
    # This value is also passed to the AprilTag relocation launch file.
    declared_arguments.append(
        DeclareLaunchArgument(
            'detection_enabled',
            default_value='false'
        )
    )

    # ========================================================
    # 2. LASER SCAN MERGER CONFIGURATION
    # ========================================================

    # Find the installed share directory of the ira_laser_tools package.
    #
    # Then locate the YAML configuration file:
    # config/laserscan_merge.yaml
    #
    # This file contains the configuration for combining
    # multiple laser scanner inputs into one LaserScan.
    laser_params_file = os.path.join(
        get_package_share_directory("ira_laser_tools"),
        "config",
        "laserscan_merge.yaml"
    )

    # ========================================================
    # 3. ROBOT DESCRIPTION / URDF
    # ========================================================

    # Find the installed share directory of the M3Pro robot description package.
    #
    # Locate the robot's Xacro file:
    # urdf/m3pro.urdf
    model = os.path.join(
        get_package_share_directory('M3Pro'),
        'urdf',
        'm3pro.urdf'
    )

    # Process the Xacro file and generate the robot description.
    #
    # Command(['xacro ', model]) executes the Xacro command.
    #
    # ParameterValue(value_type=str) ensures that the result
    # is treated as a string parameter.
    robot_description = ParameterValue(
        Command(['xacro ', model]),
        value_type=str
    )

    # --------------------------------------------------------
    # ROBOT STATE PUBLISHER
    # --------------------------------------------------------

    # Start the robot_state_publisher node.
    #
    # This node reads the robot description (URDF) and publishes
    # the TF transforms describing the robot's links and joints.
    #
    # These transforms allow ROS 2 tools such as RViz to understand
    # the robot's physical structure and link relationships.
    robot_state_publisher_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[
            {
                'robot_description': robot_description
            }
        ]
    )

    # --------------------------------------------------------
    # JOINT STATE PUBLISHER
    # --------------------------------------------------------

    # Start the joint_state_publisher node.
    #
    # It reads joint information from the configured source topic.
    #
    # source_list:
    # /arm_status/arm_joint
    #
    # The joint positions are used by robot_state_publisher
    # to calculate and publish the corresponding robot transforms.
    joint_publisher_node = Node(
        package='joint_state_publisher',
        executable='joint_state_publisher',
        parameters=[
            {
                'source_list': [
                    "/arm_status/arm_joint"
                ]
            }
        ]
    )

    # ========================================================
    # 4. LASER SCAN MERGER NODE
    # ========================================================

    # Start the laser scan merger node.
    #
    # Package:
    # ira_laser_tools
    #
    # Executable:
    # laserscan_multi_merger
    #
    # Name:
    # laserscan_multi_merger
    #
    # Parameters:
    # laserscan_merge.yaml
    #
    # This node combines multiple laser scan sources into
    # a single LaserScan message according to the YAML configuration.
    laser_merge = Node(
        package="ira_laser_tools",
        executable="laserscan_multi_merger",
        name="laserscan_multi_merger",
        parameters=[
            laser_params_file
        ]
    )

    # ========================================================
    # 5. LASER FILTER NODE
    # ========================================================

    # Start the Yahboom laser filter node.
    #
    # The node receives laser scan data and applies the filtering
    # behavior implemented in the yahboom_laser_filter package.
    laser_filter_node = Node(
        package='yahboom_laser_filter',
        executable='laser_filter_node',
        name='laser_filter_node',

        # Set the minimum and maximum filter angles.
        #
        # angle_min = -180 degrees
        # angle_max =  180 degrees
        #
        # This specifies the full angular range.
        parameters=[
            {
                'angle_min': -180.0,
                'angle_max': 180.0
            }
        ]
    )

    # ========================================================
    # 6. ORBBEC CAMERA LAUNCH
    # ========================================================

    # Start the Orbbec camera using another ROS 2 launch file.
    #
    # ExecuteProcess runs the following command:
    #
    # ros2 launch m3pro_bringup dabai_dcw2.launch.py
    #
    # output='screen' displays the camera launch output
    # directly in the terminal.
    bringup_camera = ExecuteProcess(
        cmd=[
            'ros2',
            'launch',
            'm3pro_bringup',
            'dabai_dcw2.launch.py'
        ],
        output='screen'
    )

    # ========================================================
    # 7. EKF ODOMETRY LAUNCH
    # ========================================================

    # Find the installed share directory of the ekf_bringup package.
    #
    # Locate its EKF launch file:
    # launch/ekf.launch.py
    #
    # EKF stands for Extended Kalman Filter.
    #
    # An EKF can combine different sensor measurements
    # to estimate the robot's position, orientation and velocity.
    ekf_odom_launch_file = os.path.join(
        get_package_share_directory('ekf_bringup'),
        'launch',
        'ekf.launch.py'
    )

    # ========================================================
    # 8. STATIC TF LAUNCH
    # ========================================================

    # Find the static TF launch file inside m3pro_bringup.
    #
    # Static transforms describe fixed relationships between
    # robot coordinate frames.
    #
    # For example, a fixed camera-to-robot or sensor-to-base
    # relationship can be published using static transforms.
    static_tf_launch_file = os.path.join(
        get_package_share_directory('m3pro_bringup'),
        'launch',
        'static_tf.launch.py'
    )

    # ========================================================
    # 9. ARM STATUS NODE
    # ========================================================

    # Start the arm_status node.
    #
    # Package:
    # arm_util
    #
    # Executable:
    # arm_status
    #
    # Name:
    # arm_status
    #
    # output='screen':
    # Displays the node's logs in the terminal.
    #
    # common.yaml:
    # Contains the configuration parameters used by this node.
    arm_status_node = Node(
        package='arm_util',
        executable='arm_status',
        name='arm_status',
        output='screen',
        parameters=[
            os.path.join(
                get_package_share_directory('m3pro_bringup'),
                'config',
                'common.yaml'
            )
        ]
    )

    # ========================================================
    # 10. APRILTAG DETECTION AND RELOCATION
    # ========================================================

    # Include the AprilTag relocation launch file.
    #
    # This launch file is responsible for starting the
    # AprilTag detection and relocation-related components.
    aritag_detect_relocation = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory('m3pro_bringup'),
                'launch',
                'apriltag_relocalization.launch.py'
            )
        ),

        # Pass launch arguments to the included launch file.
        launch_arguments={

            # Set the logging level to INFO.
            'log_level': 'info',

            # Pass the detection_enabled argument from this launch file.
            'detection_enabled': LaunchConfiguration(
                'detection_enabled'
            ),

            # Pass the relocation argument from this launch file.
            'relocation': LaunchConfiguration(
                'relocation'
            )

        }.items()
    )

    # ========================================================
    # 11. RETURN THE COMPLETE LAUNCH DESCRIPTION
    # ========================================================

    # Launch all the components defined above.
    #
    # *declared_arguments:
    # Adds both launch arguments:
    # relocation and detection_enabled.
    #
    # The remaining actions start the camera, robot description,
    # joint publisher, laser processing, EKF, static TF,
    # arm status and AprilTag relocation components.
    return LaunchDescription([

        *declared_arguments,

        # Orbbec camera driver.
        bringup_camera,

        # Robot URDF and TF publisher.
        robot_state_publisher_node,

        # Robotic arm joint state publisher.
        joint_publisher_node,

        # Combine laser scan data.
        laser_merge,

        # Filter laser scan data.
        laser_filter_node,

        # Start EKF odometry.
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                ekf_odom_launch_file
            )
        ),

        # Start static TF publishers.
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                static_tf_launch_file
            )
        ),

        # Start arm status node.
        arm_status_node,

        # Start AprilTag detection and relocation.
        aritag_detect_relocation

    ])
