"""Launch E-AIRA with one gated base output and optional edge AI adapters.

Author: E-AIRA maintainers.
Hardware target: ROSMASTER M3 Pro / Jetson Orin NX, ROS 2 Humble.
"""

import os
from pathlib import Path
from typing import Any

from ament_index_python.packages import PackageNotFoundError, get_package_share_directory
from launch import LaunchContext, LaunchDescription
from launch.actions import (
    DeclareLaunchArgument, GroupAction, IncludeLaunchDescription, LogInfo, OpaqueFunction,
    SetLaunchConfiguration,
)
from launch.conditions import IfCondition, UnlessCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch_ros.actions import Node, SetParameter
from launch_ros.parameter_descriptions import ParameterValue
from launch.substitutions import Command


def include_or_warn(package: str, launch_path: str, description: str,
                    condition: Any = None, launch_arguments: dict | None = None
                    ) -> IncludeLaunchDescription | LogInfo:
    """Resolve a launch include without treating absent files as installed hardware.

    Args:
        package: ROS package owning the launch file.
        launch_path: Relative path inside the package share.
        description: Human-readable dependency role.
        condition: Optional launch condition.
        launch_arguments: Explicit child argument values.
    Returns:
        Include action or a structured warning action when unavailable.
    """
    try:
        path = Path(get_package_share_directory(package)) / launch_path
    except PackageNotFoundError:
        return LogInfo(msg=f'[dependency_missing] {description}: package={package}')
    if not path.is_file():
        return LogInfo(msg=f'[dependency_missing] {description}: file={path}')
    return IncludeLaunchDescription(
        PythonLaunchDescriptionSource(str(path)), condition=condition,
        launch_arguments=(launch_arguments or {}).items())


def available_node(package: str, executable: str, **kwargs: Any) -> Node | LogInfo:
    """Create a native driver/tool node only when its package is installed.

    Args:
        package: Existing ROS package, never an E-AIRA driver replacement.
        executable: Installed executable name.
        **kwargs: Launch Node options.
    Returns:
        Node action or a dependency warning.
    """
    try:
        get_package_share_directory(package)
    except PackageNotFoundError:
        return LogInfo(msg=f'[dependency_missing] node={package}/{executable}')
    return Node(package=package, executable=executable, output='screen', **kwargs)


def _enabled(context: LaunchContext, name: str) -> bool:
    """Resolve a validated boolean launch argument.

    Args:
        context: Active launch configuration.
        name: Argument name.
    Returns:
        Whether the option is enabled.
    Raises:
        ValueError: If the boolean text is invalid.
    """
    value = LaunchConfiguration(name).perform(context).lower()
    if value not in ('true', 'false', '1', '0'):
        raise ValueError(f'{name} must be true or false')
    return value in ('true', '1')


def simulation_clock(context: LaunchContext | None = None) -> dict[str, Any]:
    """Build one typed clock override shared by E-AIRA and native ROS nodes.

    Args:
        context: Runtime context, or None to defer substitution in the launch graph.

    Returns:
        A use_sim_time parameter override; legacy missing arguments default to false.

    Raises:
        ValueError: A resolved clock argument is not a supported boolean.
    """
    if context is None:
        value = ParameterValue(LaunchConfiguration('use_sim_time', default='false'),
                               value_type=bool)
    else:
        raw = LaunchConfiguration('use_sim_time', default='false').perform(context).lower()
        if raw not in ('true', 'false', '1', '0'):
            raise ValueError('use_sim_time must be true or false')
        value = raw in ('true', '1')
    return {'use_sim_time': value}


def clocked_include(context: LaunchContext, package: str, launch_path: str,
                    description: str, launch_arguments: dict | None = None) -> GroupAction:
    """Isolate a native child launch while explicitly propagating its ROS clock.

    Args:
        context: Runtime launch configuration.
        package: Existing native ROS package.
        launch_path: Relative launch path inside the package share.
        description: Dependency diagnostic description.
        launch_arguments: Explicit native child arguments.

    Returns:
        Scoped include with no inherited E-AIRA parameter-file configuration.
    """
    use_sim_time = bool(simulation_clock(context)['use_sim_time'])
    arguments = {**(launch_arguments or {}), 'use_sim_time': str(use_sim_time).lower()}
    return GroupAction(actions=[
        SetParameter('use_sim_time', use_sim_time),
        include_or_warn(package, launch_path, description, launch_arguments=arguments)],
        forwarding=False)


def _hardware(context: LaunchContext) -> list:
    """Resolve external packages only after disabled components are excluded.

    Args:
        context: Active launch configuration.
    Returns:
        Existing hardware and navigation actions.
    """
    actions = []
    clock = simulation_clock(context)
    if _enabled(context, 'use_base'):
        for package, filename in (
                ('imu_filter_madgwick', 'imu_filter.launch.py'),
                ('yahboom_laser_filter', 'laser_filter_node.launch.py'),
                ('ekf_bringup', 'ekf.launch.py')):
            # Isolate generic child params_file names from E-AIRA's params_file.
            actions.append(clocked_include(context, package, 'launch/' + filename, package))
        try:
            laser_config = Path(get_package_share_directory('ira_laser_tools')) / (
                'config/laserscan_merge.yaml')
            if laser_config.is_file():
                actions.append(available_node(
                    'ira_laser_tools', 'laserscan_multi_merger',
                    name='laserscan_multi_merger', parameters=[str(laser_config), clock]))
            else:
                actions.append(LogInfo(msg=f'[dependency_missing] {laser_config}'))
        except PackageNotFoundError:
            actions.append(LogInfo(msg='[dependency_missing] ira_laser_tools'))
    if _enabled(context, 'use_robot_tf'):
        actions.append(clocked_include(context, 'm3pro_bringup', 'launch/static_tf.launch.py',
                                       'robot static transforms'))
        try:
            model = Path(get_package_share_directory('M3Pro')) / 'urdf/m3pro.urdf'
        except PackageNotFoundError:
            model = Path('/nonexistent/eira_robot.urdf')
        if model.is_file():
            actions.extend([
                available_node('robot_state_publisher', 'robot_state_publisher', parameters=[{
                    'robot_description': ParameterValue(Command(['xacro ', str(model)]),
                                                        value_type=str), **clock}]),
                available_node('joint_state_publisher', 'joint_state_publisher', parameters=[{
                    'source_list': ['/arm_status/arm_joint'], **clock}],
                    condition=UnlessCondition(LaunchConfiguration('use_arm_state_relay')))])
        else:
            actions.append(LogInfo(msg='[dependency_missing] M3Pro URDF; TF must be external'))
    if _enabled(context, 'use_camera'):
        actions.append(clocked_include(context, 'orbbec_camera', 'launch/dabai_dcw2.launch.py',
                                       'registered RGB-D camera', launch_arguments={
                                           'depth_registration': 'true',
                                           'enable_point_cloud': 'false',
                                           'enable_colored_point_cloud': 'false',
                                           'enable_ir': 'false'}))
    if _enabled(context, 'use_arm'):
        actions.append(available_node('arm_kin', 'kin_srv', name='kin_ik_fk', parameters=[clock]))
        common = LaunchConfiguration('hardware_params_file').perform(context)
        if not common:
            try:
                common = str(Path(get_package_share_directory('m3pro_bringup')) /
                             'config/common.yaml')
            except PackageNotFoundError:
                common = ''
        parameters = [common] if common and Path(common).is_file() else []
        actions.append(available_node('arm_util', 'arm_status', name='arm_status',
                                      parameters=[*parameters, clock]))
        if not parameters:
            actions.append(LogInfo(msg='[calibration_missing] arm_status common.yaml absent'))
    if _enabled(context, 'use_nav'):
        actions.extend(_navigation(context))
    if _enabled(context, 'use_rosbridge'):
        try:
            get_package_share_directory('rosbridge_server')
            actions.append(Node(package='rosbridge_server', executable='rosbridge_websocket',
                                name='rosbridge_websocket', output='screen', parameters=[{
                                    'port': int(LaunchConfiguration('rosbridge_port').perform(
                                        context)),
                                    'address': LaunchConfiguration('rosbridge_address').perform(
                                        context),
                                    'topics_glob': ("['/eira/command','/eira/voice',"
                                                    "'/eira/status','/eira/plan',"
                                                    "'/eira/speech']"),
                                    'services_glob': "['/__eira_no_services__']",
                                    'actions_glob': "['/__eira_no_actions__']",
                                    'default_call_service_timeout': 5.0, **clock}]))
        except PackageNotFoundError:
            actions.append(LogInfo(msg='[dependency_missing] optional rosbridge_server'))
    if _enabled(context, 'use_rviz'):
        actions.append(available_node('rviz2', 'rviz2', name='rviz2', parameters=[clock]))
    return actions


def _navigation(context: LaunchContext) -> list:
    """Compose native Nav2 nodes with distinct smoother input/output channels.

    Args:
        context: Active launch configuration.
    Returns:
        Localization, navigation, and lifecycle manager actions.
    """
    params = LaunchConfiguration('nav_params_file').perform(context)
    if not params:
        try:
            params = str(Path(get_package_share_directory('M3Pro_navigation')) /
                         'param/yahboom_M3Pro.yaml')
        except PackageNotFoundError:
            return [LogInfo(msg='[dependency_missing] M3Pro_navigation/Nav2 parameters')]
    if not Path(params).is_file():
        return [LogInfo(msg=f'[dependency_missing] Nav2 parameters: {params}')]
    localization = include_or_warn(
        'nav2_bringup', 'launch/localization_launch.py', 'Nav2 localization',
        launch_arguments={'map': LaunchConfiguration('map').perform(context),
                          'params_file': params,
                          'use_sim_time': str(simulation_clock(context)['use_sim_time']).lower(),
                          'autostart': 'true', 'use_composition': 'false'})
    specs = (
        ('nav2_controller', 'controller_server'), ('nav2_smoother', 'smoother_server'),
        ('nav2_planner', 'planner_server'), ('nav2_behaviors', 'behavior_server'),
        ('nav2_bt_navigator', 'bt_navigator'), ('nav2_waypoint_follower', 'waypoint_follower'),
        ('nav2_velocity_smoother', 'velocity_smoother'))
    nodes = [localization] if _enabled(context, 'use_nav_localization') else []
    for package, executable in specs:
        remaps = []
        if executable in ('controller_server', 'behavior_server', 'velocity_smoother'):
            remaps.append(('cmd_vel', '/eira/nav/controller_cmd'))
        if executable == 'velocity_smoother':
            remaps.append(('cmd_vel_smoothed', '/eira/cmd_vel/nav'))
        nodes.append(available_node(package, executable, name=executable,
                                    parameters=[params, simulation_clock(context)],
                                    remappings=remaps))
    nodes.append(available_node('nav2_lifecycle_manager', 'lifecycle_manager',
                                name='lifecycle_manager_navigation', parameters=[{
                                    'autostart': True, **simulation_clock(context),
                                    'node_names': [executable for _, executable in specs]}]))
    return [GroupAction(actions=[SetLaunchConfiguration('params_file', params), *nodes])]


def generate_launch_description() -> LaunchDescription:
    """Build the launch graph without resolving absent optional robot packages.

    Returns:
        Master launch description with explicit component switches.
    """
    # Source fallback also makes the launch unit test independent of colcon install.
    try:
        share = Path(get_package_share_directory('eira_bringup'))
    except PackageNotFoundError:
        share = Path(__file__).resolve().parents[1]
    defaults = {
        'use_base': 'true', 'use_robot_tf': 'true', 'use_camera': 'true', 'use_arm': 'true',
        'use_nav': 'true', 'use_nav_localization': 'true', 'use_rviz': 'false',
        'use_tracker': 'false', 'use_sim_time': 'false',
        'use_evaluation': 'false', 'use_recording': 'false',
        'use_arm_state_relay': 'true', 'use_visualization': 'true',
        'use_mission_reports': 'true',
        'use_perception': 'true', 'use_manipulation': 'true',
        'logger_environment': 'hardware', 'random_seed': '-1',
        'use_voice': 'false', 'use_gestures': 'false', 'use_edge': 'false',
        'tracking_backend': 'yolo',
        'use_relocalization': 'false', 'use_rosbridge': 'false',
        'rosbridge_port': '9090', 'rosbridge_address': '127.0.0.1',
        'map': os.path.expanduser('~/map/map.yaml'), 'nav_params_file': '',
        'hardware_params_file': '', 'params_file': str(share / 'config/eira_params.yaml'),
        'waypoints_file': str(share / 'config/waypoints.yaml'),
    }
    descriptions = {
        'use_base': 'Start native IMU, scan filters/merger and EKF.',
        'use_sim_time': 'Use the ROS /clock source for node timestamps and ROS timers.',
        'use_evaluation': 'Start structured mission logging for research metrics.',
        'use_recording': 'Start bounded per-mission rosbag recording.',
        'use_arm_state_relay': 'Display commanded arm poses; these are not measured feedback.',
        'use_visualization': 'Publish target, object and heading markers for RViz.',
        'use_mission_reports': 'Print terminal summaries and save mission text reports.',
        'use_perception': 'Start actual model-based YOLO/transformer perception.',
        'use_manipulation': 'Start manipulation; disable only for navigation-only development.',
        'logger_environment': 'Label recorded provenance as hardware or simulation.',
        'random_seed': 'Random seed recorded in evaluation and bag provenance; -1 if unspecified.',
        'use_robot_tf': 'Start native robot/joint state and static TF publishers.',
        'use_camera': 'Start the registered Dabai DCW2 RGB-D driver.',
        'use_arm': 'Start existing Yahboom IK and calibrated arm status.',
        'use_nav': 'Start native Nav2 nodes through the velocity gate.',
        'use_nav_localization': 'Start AMCL/map server; disable for RTAB-Map localization.',
        'use_rviz': 'Start RViz2.',
        'use_tracker': 'Compatibility alias selecting the transformer backend.',
        'use_voice': 'Enable optional local Whisper ASR.',
        'use_gestures': 'Enable optional MediaPipe gestures.',
        'use_edge': 'Require calibrated, fresh floor clearance before motion.',
        'tracking_backend': 'Select yolo or transformer tracking.',
        'use_relocalization': 'Enable calibrated visual recovery for uncertain AMCL.',
        'use_rosbridge': 'Enable the restricted mobile command WebSocket.',
        'rosbridge_port': 'WebSocket TCP port.',
        'rosbridge_address': 'WebSocket bind address; localhost by default.',
        'map': 'Measured occupancy-grid YAML for AMCL.',
        'nav_params_file': 'Native Nav2 parameter YAML; separate from E-AIRA parameters.',
        'hardware_params_file': 'Measured arm_status common.yaml; native share by default.',
        'params_file': 'E-AIRA node parameters.',
        'waypoints_file': 'Measured named waypoint database.',
    }
    actions = [DeclareLaunchArgument(name, default_value=value,
                                     description=descriptions[name])
               for name, value in defaults.items()]
    actions.append(OpaqueFunction(function=_hardware))
    parameters = [LaunchConfiguration('params_file'), simulation_clock()]
    console_environment = {'RCUTILS_CONSOLE_OUTPUT_FORMAT': '{message}'}
    actions.extend([
        Node(package='eira_bringup', executable='arm_state_relay', name='arm_state_relay',
             output='screen', emulate_tty=True, parameters=parameters,
             additional_env=console_environment,
             condition=IfCondition(LaunchConfiguration('use_arm_state_relay'))),
        Node(package='eira_bringup', executable='visualization_markers',
             name='visualization_markers', output='screen', emulate_tty=True,
             additional_env=console_environment,
             parameters=[*parameters, {'waypoints_file': LaunchConfiguration('waypoints_file')}],
             condition=IfCondition(LaunchConfiguration('use_visualization'))),
        Node(package='eira_brain', executable='mission_reporter', name='mission_reporter',
             output='screen', emulate_tty=True, parameters=parameters,
             additional_env=console_environment,
             condition=IfCondition(LaunchConfiguration('use_mission_reports'))),
        Node(package='eira_brain', executable='llm_task_planner', name='llm_task_planner',
             output='screen', emulate_tty=True, parameters=[*parameters, {
                 'waypoints_file': LaunchConfiguration('waypoints_file')}],
             additional_env=console_environment,
             remappings=[('cmd_vel', '/eira/cmd_vel/brain')]),
        Node(package='eira_perception', executable='vision_manager', name='vision_manager',
             condition=IfCondition(LaunchConfiguration('use_perception')), output='screen',
             emulate_tty=True,
             additional_env=console_environment,
             parameters=[*parameters, {'tracking_backend': ParameterValue(
                 PythonExpression(["'transformer' if '", LaunchConfiguration('use_tracker'),
                                   "' == 'true' else '", LaunchConfiguration('tracking_backend'),
                                   "'"]), value_type=str)}]),
        Node(package='eira_manipulation', executable='grasp_executor', name='grasp_executor',
             condition=IfCondition(LaunchConfiguration('use_manipulation')), output='screen',
             emulate_tty=True,
             additional_env=console_environment,
             parameters=parameters,
             remappings=[('cmd_vel', '/eira/cmd_vel/arm')]),
        Node(package='eira_brain', executable='safety_monitor', name='safety_monitor',
             output='screen', emulate_tty=True, parameters=parameters,
             additional_env=console_environment,
             remappings=[('/cmd_vel', '/eira/cmd_vel/watchdog')]),
        Node(package='eira_brain', executable='velocity_gate', name='velocity_gate',
             output='screen', emulate_tty=True, parameters=[*parameters, {
                 'require_edge': ParameterValue(LaunchConfiguration('use_edge'),
                                                value_type=bool)}],
             additional_env=console_environment),
    ])
    for flag, package, executable in (
            ('use_voice', 'eira_brain', 'voice_input'),
            ('use_gestures', 'eira_perception', 'gesture_recognizer'),
            ('use_relocalization', 'eira_brain', 'visual_relocalization'),
            ('use_edge', 'eira_bringup', 'edge_monitor')):
        actions.append(Node(package=package, executable=executable, name=executable,
                            output='screen', emulate_tty=True, parameters=parameters,
                            additional_env=console_environment,
                            condition=IfCondition(LaunchConfiguration(flag))))
    provenance = {
        'environment': ParameterValue(LaunchConfiguration('logger_environment'), value_type=str),
        'random_seed': ParameterValue(LaunchConfiguration('random_seed'), value_type=int),
    }
    actions.extend([
        Node(package='eira_evaluation', executable='mission_logger', name='mission_logger',
             output='screen', emulate_tty=True, parameters=[*parameters, provenance],
             additional_env=console_environment,
             condition=IfCondition(LaunchConfiguration('use_evaluation'))),
        Node(package='eira_brain', executable='mission_recorder', name='mission_recorder',
             output='screen', emulate_tty=True, additional_env=console_environment,
             parameters=[*parameters, provenance, {
                 'capture_config_files': [[LaunchConfiguration('params_file')],
                                          [LaunchConfiguration('waypoints_file')]]}],
             condition=IfCondition(LaunchConfiguration('use_recording'))),
    ])
    return LaunchDescription(actions)
