"""Visualise the robot description in RViz2 (no Gazebo needed).

By default the joint_state_publisher_gui lets you move every joint with
sliders - useful for checking the URDF before simulating.

Usage:
  ros2 launch neurobotics display.launch.py            # sliders + RViz
  ros2 launch neurobotics display.launch.py sim:=true # next to a running
                                                      # Gazebo sim (live state)
"""

import os
import re
from subprocess import check_output

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import UnlessCondition
from launch.substitutions import LaunchConfiguration

from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def load_urdf(urdf_file):
    """Run xacro on the URDF and return it as a clean parameter string.

    Same normalisation as gazebo.launch.py: strips the XML declaration,
    comments and newlines so the string is safe to pass through rcl
    parameter overrides (gazebo_ros2_control issue #247).
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

    robot_description = ParameterValue(
        load_urdf(urdf_file),
        value_type=str,
    )

    use_sim_time = LaunchConfiguration('use_sim_time')

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[{
            'robot_description': robot_description,
            'use_sim_time': use_sim_time,
        }],
        output='screen',
    )

    # The slider GUI only makes sense when no simulator publishes states.
    joint_state_publisher_gui = Node(
        package='joint_state_publisher_gui',
        executable='joint_state_publisher_gui',
        condition=UnlessCondition(use_sim_time),
    )

    rviz2 = Node(
        package='rviz2',
        executable='rviz2',
        arguments=['-d', rviz_config],
        parameters=[{'use_sim_time': use_sim_time}],
        output='screen',
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time', default_value='false',
            description='Set true when Gazebo is running simultaneously'),
        robot_state_publisher,
        joint_state_publisher_gui,
        rviz2,
    ])
