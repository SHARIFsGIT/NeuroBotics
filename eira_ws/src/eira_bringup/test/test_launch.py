"""Validate Humble launch loading, routing, and child argument contracts.

Author: E-AIRA maintainers.
Hardware target: Jetson Orin NX / ROS 2 Humble; no processes are started.
"""

import importlib.util
from pathlib import Path
from types import ModuleType

from pytest import MonkeyPatch

from launch import LaunchContext, LaunchDescription
from launch.actions import IncludeLaunchDescription, LogInfo


def load_master(monkeypatch: MonkeyPatch, tmp_path: Path) -> ModuleType:
    """Load the real master launch while keeping launch logs in temporary storage."""
    monkeypatch.setenv('ROS_LOG_DIR', str(tmp_path))
    path = Path(__file__).resolve().parents[1] / 'launch/eira_master.launch.py'
    spec = importlib.util.spec_from_file_location('eira_master_test', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_master_loads_without_robot_packages(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    """Generating the launch graph must not require Yahboom packages or hardware."""
    module = load_master(monkeypatch, tmp_path)
    description = module.generate_launch_description()
    assert isinstance(description, LaunchDescription)
    names = [type(action).__name__ for action in description.entities]
    assert names.count('Node') >= 5
    assert 'OpaqueFunction' in names


def test_include_arguments_are_pairs(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    """Regression: a dictionary must not be iterated as bare map-key strings."""
    module = load_master(monkeypatch, tmp_path)
    path = tmp_path / 'launch'
    path.mkdir()
    (path / 'navigation.launch.py').write_text('')
    monkeypatch.setattr(module, 'get_package_share_directory', lambda _name: str(tmp_path))
    action = module.include_or_warn('nav', 'launch/navigation.launch.py', 'test',
                                    launch_arguments={'map': '/tmp/map.yaml'})
    assert isinstance(action, IncludeLaunchDescription)
    assert dict(action.launch_arguments) == {'map': '/tmp/map.yaml'}


def test_missing_launch_file_is_reported(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    """A package directory alone does not prove a launch file is installed."""
    module = load_master(monkeypatch, tmp_path)
    monkeypatch.setattr(module, 'get_package_share_directory', lambda _name: str(tmp_path))
    assert isinstance(module.include_or_warn('nav', 'absent.py', 'test'), LogInfo)


def test_disabled_hardware_resolves_no_packages(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    """Disabled components must not trigger dependency resolution or spurious warnings."""
    module = load_master(monkeypatch, tmp_path)
    context = LaunchContext()
    for key in ('use_base', 'use_robot_tf', 'use_camera', 'use_arm', 'use_nav',
                'use_rosbridge', 'use_rviz'):
        context.launch_configurations[key] = 'false'
    assert module._hardware(context) == []


def test_typed_clock_parameters_default_and_simulation(
        monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    """Use Humble's real parameter evaluator for deferred clock substitutions."""
    from launch_ros.utilities import evaluate_parameters, normalize_parameters
    module = load_master(monkeypatch, tmp_path)
    context = LaunchContext()
    assert module.simulation_clock(context) == {'use_sim_time': False}
    context.launch_configurations['use_sim_time'] = 'true'
    normalized = normalize_parameters([module.simulation_clock()])
    assert tuple(evaluate_parameters(context, normalized)) == ({'use_sim_time': True},)


def test_all_eira_nodes_receive_clock_and_optional_switches(
        monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    """Evaluate actual master Node definitions with simulation and recording enabled."""
    from launch.actions import DeclareLaunchArgument
    from launch_ros.utilities import evaluate_parameters, normalize_parameters
    module = load_master(monkeypatch, tmp_path)
    original_node = module.Node
    captured = []

    def capture_node(**kwargs: object) -> object:
        """Capture constructor parameters while preserving real launch Node actions.

        Args:
            **kwargs: Actual Node definition supplied by the master launch.

        Returns:
            Real Node launch action.
        """
        action = original_node(**kwargs)
        captured.append((action, kwargs))
        return action

    monkeypatch.setattr(module, 'Node', capture_node)
    description = module.generate_launch_description()
    context = LaunchContext()
    for action in description.entities:
        if isinstance(action, DeclareLaunchArgument):
            action.execute(context)
    context.launch_configurations.update({
        'use_sim_time': 'true', 'use_evaluation': 'true', 'use_recording': 'true',
        'use_perception': 'false', 'use_manipulation': 'false',
        'logger_environment': 'simulation', 'random_seed': '42'})
    checked = {}
    for action, kwargs in captured:
        dictionaries = evaluate_parameters(context, normalize_parameters(kwargs['parameters']))
        values = {}
        for item in dictionaries:
            if isinstance(item, dict):
                values.update(item)
        assert values['use_sim_time'] is True
        checked[kwargs['name']] = (action, values)
    assert checked['mission_logger'][1]['environment'] == 'simulation'
    assert checked['mission_logger'][1]['random_seed'] == 42
    recorder_files = checked['mission_recorder'][1]['capture_config_files']
    assert len(recorder_files) == 2
    assert recorder_files[0].endswith('eira_params.yaml')
    assert recorder_files[1].endswith('waypoints.yaml')
    assert checked['mission_logger'][0].condition.evaluate(context)
    assert checked['mission_recorder'][0].condition.evaluate(context)
    assert not checked['vision_manager'][0].condition.evaluate(context)
    assert not checked['grasp_executor'][0].condition.evaluate(context)


def test_native_child_clock_is_isolated(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    """A native child receives simulation time without inheriting E-AIRA params_file."""
    module = load_master(monkeypatch, tmp_path)
    launch_dir = tmp_path / 'launch'
    launch_dir.mkdir()
    (launch_dir / 'native.launch.py').write_text('')
    monkeypatch.setattr(module, 'get_package_share_directory', lambda _name: str(tmp_path))
    context = LaunchContext()
    context.launch_configurations.update({'use_sim_time': 'true', 'params_file': 'eira.yaml'})
    group = module.clocked_include(context, 'native', 'launch/native.launch.py', 'test')
    included = None
    for action in group.get_sub_entities():
        if isinstance(action, IncludeLaunchDescription):
            included = action
            assert 'params_file' not in context.launch_configurations
            assert ('use_sim_time', True) in context.launch_configurations['global_params']
            assert dict(action.launch_arguments) == {'use_sim_time': 'true'}
        else:
            action.execute(context)
    assert included is not None
    assert context.launch_configurations['params_file'] == 'eira.yaml'


def test_native_navigation_clock_and_velocity_routes(monkeypatch: MonkeyPatch,
                                                     tmp_path: Path) -> None:
    """Native Nav2 constructors receive simulation time and distinct smoother channels."""
    module = load_master(monkeypatch, tmp_path)
    parameters = tmp_path / 'nav.yaml'
    parameters.write_text('{}')
    launch_dir = tmp_path / 'launch'
    launch_dir.mkdir()
    (launch_dir / 'localization_launch.py').write_text('')
    monkeypatch.setattr(module, 'get_package_share_directory', lambda _name: str(tmp_path))
    original_node = module.available_node
    captured = []

    def capture_native(package: str, executable: str, **kwargs: object) -> object:
        """Preserve actual native Node definitions for parameter/routing inspection.

        Args:
            package: Native ROS package.
            executable: Installed executable name.
            **kwargs: Native Node settings.

        Returns:
            Real Node launch action.
        """
        captured.append((executable, kwargs))
        return original_node(package, executable, **kwargs)

    monkeypatch.setattr(module, 'available_node', capture_native)
    context = LaunchContext()
    context.launch_configurations.update({
        'nav_params_file': str(parameters), 'map': '/tmp/map.yaml',
        'use_sim_time': 'true', 'use_nav_localization': 'true'})
    group = module._navigation(context)[0]
    native = {name: values for name, values in captured}
    for values in native.values():
        assert any(isinstance(item, dict) and item.get('use_sim_time') is True
                   for item in values['parameters'])
    assert ('cmd_vel', '/eira/nav/controller_cmd') in native['controller_server']['remappings']
    assert ('cmd_vel', '/eira/nav/controller_cmd') in native['velocity_smoother']['remappings']
    assert ('cmd_vel_smoothed', '/eira/cmd_vel/nav') in (
        native['velocity_smoother']['remappings'])
    localization = next(action for action in group.get_sub_entities()
                        if isinstance(action, IncludeLaunchDescription))
    assert dict(localization.launch_arguments)['use_sim_time'] == 'true'
