"""Bring up the Neurobotics robot in Gazebo Classic with ros2_control.

Starts:
  1. Gazebo (gzserver + gzclient) with the line-following world
  2. robot_state_publisher (URDF from xacro, so $(find ...) paths resolve)
  3. spawn_entity to insert the robot once Gazebo is ready
  4. All three controllers, but only AFTER the robot is spawned (event-driven,
     no guessed delays)

Usage:
  ros2 launch neurobotics gazebo.launch.py                 # full GUI
  ros2 launch neurobotics gazebo.launch.py gui:=false      # headless (fast)
  ros2 launch neurobotics gazebo.launch.py rviz:=true      # also open RViz2
"""

import os
import re
from subprocess import check_output

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, \
    RegisterEventHandler
from launch.conditions import IfCondition
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration

from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def load_urdf(urdf_file):
    """Run xacro on the URDF and return it as a clean parameter string.

    xacro resolves $(find neurobotics) inside the URDF (the controller YAML
    path). The XML declaration, comments and newlines must then be removed:
    gazebo_ros2_control on Humble forwards robot_description through rcl's
    argument parser, which rejects '<?xml' declarations and the '--' inside
    XML comments (see gazebo_ros2_control issue #247). The comments stay in
    the URDF file itself - they are only stripped from the runtime string.
    """
    xml = check_output(['xacro', urdf_file], text=True)
    if xml.lstrip().startswith('<?xml'):
        xml = xml.split('?>', 1)[1]
    xml = re.sub(r'<!--.*?-->', ' ', xml, flags=re.DOTALL)
    return ' '.join(xml.split())


def generate_launch_description():
    pkg = get_package_share_directory('neurobotics')
    urdf_file = os.path.join(pkg, 'urdf', 'neurobotics.urdf')
    rviz_config = os.path.join(pkg, 'rviz', 'neurobotics.rviz')
    world_file = os.path.join(pkg, 'worlds', 'line.world')

    robot_description = ParameterValue(
        load_urdf(urdf_file),
        value_type=str,
    )

    gui = LaunchConfiguration('gui')
    rviz = LaunchConfiguration('rviz')

    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('gazebo_ros'),
                         'launch', 'gazebo.launch.py')),
        launch_arguments={
            'world': world_file,
            'gui': gui,
        }.items(),
    )

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[{
            'robot_description': robot_description,
            'use_sim_time': True,
        }],
        output='screen',
    )

    spawn_robot = Node(
        package='gazebo_ros',
        executable='spawn_entity.py',
        arguments=['-topic', 'robot_description',
                   '-entity', 'neurobotics', '-z', '0.01'],
        output='screen',
    )

    # Controllers are loaded only after the robot exists in Gazebo.
    joint_state_broadcaster = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['joint_broad'],
        output='screen',
    )
    diff_drive_controller = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['diff_cont'],
        output='screen',
    )
    arm_controller = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['arm_cont'],
        output='screen',
    )

    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        arguments=['-d', rviz_config],
        parameters=[{'use_sim_time': True}],
        condition=IfCondition(rviz),
    )

    load_controllers_after_spawn = RegisterEventHandler(
        OnProcessExit(
            target_action=spawn_robot,
            on_exit=[
                joint_state_broadcaster,
                diff_drive_controller,
                arm_controller,
            ],
        )
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'gui', default_value='true',
            description='Start the Gazebo GUI (set false for headless runs)'),
        DeclareLaunchArgument(
            'rviz', default_value='false',
            description='Also start RViz2 with the package RViz config'),
        gazebo,
        robot_state_publisher,
        spawn_robot,
        load_controllers_after_spawn,
        rviz_node,
    ])
