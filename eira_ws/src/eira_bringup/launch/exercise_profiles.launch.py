"""Select one audited exercise workflow without replacing native drivers.

Author: E-AIRA maintainers.
Hardware target: ROSMASTER M3 Pro / Jetson Orin NX, ROS 2 Humble.
"""

import json
from pathlib import Path
import shlex

from ament_index_python.packages import PackageNotFoundError, get_package_share_directory
from launch import LaunchContext, LaunchDescription
from launch.actions import (
    DeclareLaunchArgument, GroupAction, IncludeLaunchDescription, LogInfo, OpaqueFunction,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node, SetRemap

from eira_bringup.profiles import PROFILES, launch_argument_values


def _profile(context: LaunchContext) -> list:
    """Resolve one installed native workflow and route its motion through a gate.

    Args:
        context: Active launch configuration.
    Returns:
        Launch actions for the selected profile or an actionable dependency message.
    Raises:
        ValueError: If the profile or argument JSON is invalid.
    """
    name = LaunchConfiguration('profile').perform(context)
    if name not in PROFILES:
        raise ValueError(f'unknown profile {name}; choose from {sorted(PROFILES)}')
    spec = PROFILES[name]
    try:
        share = Path(get_package_share_directory(spec.package))
    except PackageNotFoundError:
        return [LogInfo(msg=f'[dependency_missing] profile={name}, package={spec.package}')]
    params = LaunchConfiguration('params_file').perform(context)
    params_list = [params] if params else []
    extra = launch_argument_values(json.loads(
        LaunchConfiguration('profile_launch_arguments').perform(context)))
    nodes = []
    if name == 'joystick':
        try:
            get_package_share_directory('joy')
        except PackageNotFoundError:
            return [LogInfo(msg='[dependency_missing] joystick requires joy/joy_node')]
        nodes.append(Node(package='joy', executable='joy_node', name='joy_node', output='screen'))
    if spec.launch:
        path = share / 'launch' / spec.resource
        if not path.is_file():
            return [LogInfo(msg=f'[dependency_missing] profile={name}, file={path}')]
        if name.startswith('rtabmap_'):
            extra = {
                'rgb_topic': '/camera/color/image_raw', 'depth_topic': '/camera/depth/image_raw',
                'camera_info_topic': '/camera/color/camera_info', 'odom_topic': '/odom',
                'frame_id': 'base_link', 'visual_odometry': 'false', 'icp_odometry': 'false',
                'subscribe_scan': 'true', 'approx_sync': 'true', 'qos': '2',
                'rtabmap_args': ('--Mem/IncrementalMemory false'
                                 if name.endswith('localization') else ''), **extra}
        if name == 'camera':
            extra = {'depth_registration': 'true', 'enable_point_cloud': 'false',
                     'enable_colored_point_cloud': 'false', 'enable_ir': 'false', **extra}
        nodes.append(GroupAction(actions=[IncludeLaunchDescription(
            PythonLaunchDescriptionSource(str(path)), launch_arguments=extra.items())],
            forwarding=False))
    elif name == 'keyboard':
        nodes.append(LogInfo(msg=(
            '[keyboard] In an attached second terminal run: ros2 run yahboomcar_ctrl '
            'yahboom_keyboard --ros-args -r cmd_vel:=/eira/cmd_vel/exercise')))
    else:
        overrides = {}
        if name == 'depth_tools':
            overrides = {'publish_depth_image': True}
        nodes.append(Node(package=spec.package, executable=spec.resource, output='screen',
                          parameters=[*params_list, overrides],
                          arguments=shlex.split(LaunchConfiguration('profile_arguments').perform(
                              context)),
                          emulate_tty=True))
    # Master navigation already contains the gate and explicit Nav2 smoother routing.
    if spec.motion and name != 'navigation':
        gate = Node(package='eira_brain', executable='velocity_gate', name='velocity_gate',
                    output='screen', parameters=[*params_list, {
                        'require_heartbeat': False, 'initial_owner': 'exercise'}])
        return [LogInfo(msg=f'[exercise_profile] {name}: {spec.description}'), gate,
                GroupAction(actions=[SetRemap(src='/cmd_vel', dst='/eira/cmd_vel/exercise'),
                                     SetRemap(src='cmd_vel', dst='/eira/cmd_vel/exercise'),
                                     *nodes])]
    return [LogInfo(msg=f'[exercise_profile] {name}: {spec.description}'), *nodes]


def generate_launch_description() -> LaunchDescription:
    """Declare an explicit profile selector; no autonomous profile is enabled by default.

    Returns:
        Deferred profile launch description.
    """
    return LaunchDescription([
        DeclareLaunchArgument('profile', default_value='lidar_view',
                              description=', '.join(sorted(PROFILES))),
        DeclareLaunchArgument('params_file', default_value=''),
        DeclareLaunchArgument('profile_arguments', default_value=''),
        DeclareLaunchArgument('profile_launch_arguments', default_value='{}'),
        OpaqueFunction(function=_profile),
    ])
