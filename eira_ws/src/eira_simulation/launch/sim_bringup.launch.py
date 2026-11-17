"""Launch seeded M3 Pro Gazebo experiments with the existing E-AIRA interfaces.

Author: E-AIRA maintainers.
Hardware target: ROS 2 Humble / Gazebo Classic, no physical robot required.
"""

import hashlib
import json
from pathlib import Path
import tempfile

from ament_index_python.packages import get_package_share_directory
from launch import LaunchContext, LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, LogInfo, OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
import yaml

from eira_simulation.robot_description import locate_robot, prepare_robot
from eira_simulation.world_builder import WorldSettings, write_world


def _bool(context: LaunchContext, name: str) -> bool:
    """Read a strict boolean launch value.

    Args:
        context: Active launch configuration.
        name: Argument name.
    Returns:
        Parsed boolean.
    Raises:
        ValueError: For invalid boolean text.
    """
    value = LaunchConfiguration(name).perform(context).lower()
    if value not in ('true', 'false', '1', '0'):
        raise ValueError(f'{name} must be true or false')
    return value in ('true', '1')


def _bringup(context: LaunchContext) -> list:
    """Create reproducible assets and compose Gazebo, native Nav2 and E-AIRA.

    Args:
        context: Launch argument values.
    Returns:
        Complete launch graph for the selected time domain.
    Raises:
        ValueError: If an unsupported perception mode is selected.
        FileNotFoundError: If required model assets are missing.
    """
    share = Path(get_package_share_directory('eira_simulation'))
    bringup = Path(get_package_share_directory('eira_bringup'))
    master = PythonLaunchDescriptionSource(str(bringup / 'launch/eira_master.launch.py'))
    if not _bool(context, 'use_sim_time'):
        return [IncludeLaunchDescription(master, launch_arguments={
            'use_sim_time': 'false',
            'use_evaluation': LaunchConfiguration('use_evaluation').perform(context),
            'use_recording': LaunchConfiguration('use_recording').perform(context)}.items())]
    mode = LaunchConfiguration('perception_mode').perform(context)
    if mode not in ('yolo', 'ground_truth'):
        raise ValueError('perception_mode must be yolo or ground_truth')
    seed = int(LaunchConfiguration('seed').perform(context))
    output = LaunchConfiguration('output_dir').perform(context)
    directory = Path(output).expanduser() if output else Path(tempfile.mkdtemp(prefix='eira_sim_'))
    metadata = write_world(directory, WorldSettings(
        seed=seed, randomize=_bool(context, 'randomize')))
    robot = locate_robot(LaunchConfiguration('robot_urdf').perform(context))
    description = prepare_robot(robot, directory / 'm3pro.urdf',
                                metadata['lidar_noise_stddev_m'],
                                metadata['depth_noise_stddev_m'])
    metadata.update(robot_urdf=str(robot), perception_mode=mode,
                    use_sim_time=True, source_description=str(directory / 'm3pro.urdf'),
                    robot_source_sha256=hashlib.sha256(robot.read_bytes()).hexdigest(),
                    generated_urdf_sha256=hashlib.sha256(description.encode()).hexdigest())
    (directory / 'condition.json').write_text(json.dumps(metadata, indent=2) + '\n')
    nav = yaml.safe_load((share / 'config/nav2_params.yaml').read_text())
    bt = nav['bt_navigator']['ros__parameters']
    bt['default_nav_to_pose_bt_xml'] = str(share / 'behavior_trees/navigate_to_pose.xml')
    bt['default_nav_through_poses_bt_xml'] = str(
        share / 'behavior_trees/navigate_through_poses.xml')
    (directory / 'nav2.yaml').write_text(yaml.safe_dump(nav))
    params = yaml.safe_load((bringup / 'config/eira_params.yaml').read_text())
    nodes = params['/**']
    nodes['grasp_executor']['ros__parameters'].update({
        'arm_base_frame': 'base_link', 'joint_feedback_is_measured': True,
        'init_joints': [90, 90, 90, 90, 90, 90],
        'transport_joints': [90, 70, 90, 90, 90, 30],
        'max_pose_age_s': 3.0, 'target_timeout_s': 3.0})
    nodes['vision_manager']['ros__parameters'].update({
        'device': 'cpu', 'max_fps': 4.0, 'idle_fps': 1.0, 'max_image_age_s': 5.0,
        'image_freshness_s': 5.0})
    model_path = LaunchConfiguration('yolo_model').perform(context)
    if model_path:
        nodes['vision_manager']['ros__parameters']['model_path'] = model_path
    (directory / 'eira.yaml').write_text(yaml.safe_dump(params))
    waypoints = {'frame': 'map', 'waypoints': {
        'home': {'x': -1.5, 'y': 0.0, 'yaw': 0.0},
        'table': {'x': 0.0, 'y': 0.0, 'yaw': 0.0},
        'kitchen': {'x': 0.0, 'y': 0.0, 'yaw': 0.0}}}
    (directory / 'waypoints.yaml').write_text(yaml.safe_dump(waypoints))
    gazebo = IncludeLaunchDescription(PythonLaunchDescriptionSource(str(
        Path(get_package_share_directory('gazebo_ros')) / 'launch/gazebo.launch.py')),
        launch_arguments={'world': str(directory / 'room.world'), 'seed': str(seed),
                          'gui': LaunchConfiguration('gui').perform(context)}.items())
    actions = [LogInfo(msg=f'[simulation_condition] {directory / "condition.json"}'), gazebo,
               Node(package='robot_state_publisher', executable='robot_state_publisher',
                    parameters=[{'robot_description': description, 'use_sim_time': True}],
                    output='screen'),
               Node(package='gazebo_ros', executable='spawn_entity.py', output='screen',
                    arguments=['-topic', 'robot_description', '-entity', 'eira_m3pro',
                               '-x', '-1.5', '-y', '0', '-z', '0.01', '-timeout', '60']),
               Node(package='eira_simulation', executable='sim_arm_bridge', output='screen',
                    parameters=[{'use_sim_time': True,
                                 'robot_description_file': str(directory / 'm3pro.urdf')}]),
               Node(package='eira_simulation', executable='sim_depth_noise', output='screen',
                    parameters=[{'use_sim_time': True, 'seed': seed,
                                 'depth_noise_stddev_m': metadata['depth_noise_stddev_m']}]),
               IncludeLaunchDescription(master, launch_arguments={
                   'use_sim_time': 'true', 'use_base': 'false', 'use_robot_tf': 'false',
                   'use_camera': 'false', 'use_arm': 'false',
                   'use_arm_state_relay': 'false',
                   'use_perception': 'true' if mode == 'yolo' else 'false',
                   'use_evaluation': LaunchConfiguration('use_evaluation').perform(context),
                   'use_recording': LaunchConfiguration('use_recording').perform(context),
                   'logger_environment': 'simulation' if mode == 'yolo' else 'simulation_oracle',
                   'random_seed': str(seed), 'params_file': str(directory / 'eira.yaml'),
                   'nav_params_file': str(directory / 'nav2.yaml'),
                   'waypoints_file': str(directory / 'waypoints.yaml'),
                   'map': str(directory / 'map.yaml')}.items())]
    if mode == 'ground_truth':
        actions.append(Node(package='eira_simulation', executable='sim_perception_oracle',
                            parameters=[{'use_sim_time': True}], output='screen'))
    return actions


def generate_launch_description() -> LaunchDescription:
    """Declare portable simulation controls without launching processes during inspection.

    Returns:
        Deferred simulation launch graph.
    """
    defaults = {'use_sim_time': 'true', 'gui': 'true', 'randomize': 'false', 'seed': '0',
                'robot_urdf': '', 'output_dir': '', 'yolo_model': '', 'perception_mode': 'yolo',
                'use_evaluation': 'true', 'use_recording': 'false'}
    return LaunchDescription([
        *[DeclareLaunchArgument(name, default_value=value) for name, value in defaults.items()],
        OpaqueFunction(function=_bringup)])
