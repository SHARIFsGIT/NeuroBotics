
# ============================================================
# 1. IMPORTS
# ============================================================

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration

from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare

from pathlib import Path


# ============================================================
# 2. MAIN FUNCTION
# ============================================================

def generate_launch_description():

    # --------------------------------------------------------
    # 3. LAUNCH ARGUMENTS
    # --------------------------------------------------------

    # Saved Cartographer map/state file (.pbstream)
    load_state_filename_arg = DeclareLaunchArgument(
        'load_state_filename',
        default_value='/home/jetson/yahboom_map.pbstream',
        description='Path to the saved Cartographer state file'
    )

    # Enable or disable RViz
    use_rviz_arg = DeclareLaunchArgument(
        'use_rviz',
        default_value='true',
        description='Start RViz if true'
    )

    # --------------------------------------------------------
    # 4. CARTOGRAPHER CONFIGURATION DIRECTORY
    # --------------------------------------------------------

    # Find the installed M3Pro_navigation package
    package_share = FindPackageShare('M3Pro_navigation')

    # Locate the param directory containing the Lua file
    configuration_directory = Path(
        str(package_share.find('M3Pro_navigation'))
    ) / 'param'

    # --------------------------------------------------------
    # 5. CARTOGRAPHER NODE
    # --------------------------------------------------------

    cartographer_node = Node(

        package='cartographer_ros',
        executable='cartographer_node',
        name='cartographer_node',

        # Use the real robot clock
        parameters=[
            {'use_sim_time': False}
        ],

        # Cartographer configuration arguments
        arguments=[

            # Configuration directory
            '-configuration_directory',
            str(configuration_directory),

            # Lua configuration filename
            '-configuration_basename',
            'yahboom_M3Pro.lua',

            # Load previously saved map/state
            '-load_state_filename',
            LaunchConfiguration('load_state_filename')
        ],

        # Remap IMU topic
        remappings=[
            ('imu', '/imu/data')
        ],

        # Display logs in terminal
        output='screen'
    )

    # --------------------------------------------------------
    # 6. OCCUPANCY GRID NODE
    # --------------------------------------------------------

    cartographer_occupancy_grid_node = Node(

        package='cartographer_ros',
        executable='cartographer_occupancy_grid_node',
        name='cartographer_occupancy_grid_node',

        parameters=[

            # Use real robot time
            {'use_sim_time': False},

            # Map resolution: 5 centimeters per cell
            {'resolution': 0.05}
        ],

        output='screen'
    )

    # --------------------------------------------------------
    # 7. RVIZ NODE
    # --------------------------------------------------------

    rviz_node = Node(

        package='rviz2',
        executable='rviz2',
        name='rviz2',

        parameters=[
            {'use_sim_time': False}
        ],

        # Start RViz only when use_rviz is true
        condition=IfCondition(
            LaunchConfiguration('use_rviz')
        ),

        output='screen'
    )

    # --------------------------------------------------------
    # 8. RETURN LAUNCH DESCRIPTION
    # --------------------------------------------------------

    return LaunchDescription([

        # Launch arguments
        load_state_filename_arg,
        use_rviz_arg,

        # ROS 2 nodes
        cartographer_node,
        cartographer_occupancy_grid_node,
        rviz_node
    ])


# ============================================================
# END OF LAUNCH FILE
# ============================================================
