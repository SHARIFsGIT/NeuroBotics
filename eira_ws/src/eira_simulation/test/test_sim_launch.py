"""Inspect real Gazebo launch composition without executing simulator processes.

Author: E-AIRA contributors.
Hardware target: ROSMASTER M3 Pro / ROS 2 Humble Gazebo Classic, hardware-free tests.
"""

import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any
from unittest.mock import Mock

from launch import LaunchContext, LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
import pytest
import yaml


def load_simulation(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> ModuleType:
    """Import the actual launch and resolve source shares without installation.

    Args:
        monkeypatch: Test patch manager.
        tmp_path: Temporary directory for launch logging.

    Returns:
        Imported simulation launch module.
    """
    monkeypatch.setenv('ROS_LOG_DIR', str(tmp_path / 'logs'))
    source_root = Path(__file__).resolve().parents[2]
    path = source_root / 'eira_simulation/launch/sim_bringup.launch.py'
    spec = importlib.util.spec_from_file_location('eira_sim_launch_test', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    shares = {'eira_simulation': source_root / 'eira_simulation',
              'eira_bringup': source_root / 'eira_bringup',
              'gazebo_ros': Path('/opt/ros/humble/share/gazebo_ros')}
    monkeypatch.setattr(module, 'get_package_share_directory', lambda name: str(shares[name]))
    return module


def launch_context(module: ModuleType, **overrides: str) -> LaunchContext:
    """Evaluate actual declared defaults while leaving deferred processes untouched.

    Args:
        module: Simulation launch module.
        **overrides: Explicit experiment launch settings.

    Returns:
        Launch context containing declared defaults and supplied overrides.
    """
    context = LaunchContext()
    description = module.generate_launch_description()
    for action in description.entities:
        if isinstance(action, DeclareLaunchArgument):
            action.execute(context)
    context.launch_configurations.update(overrides)
    return context


def test_launch_import_declares_yolo_as_the_default(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Ground truth remains an explicit control-regression mode, not the default."""
    module = load_simulation(monkeypatch, tmp_path)
    description = module.generate_launch_description()
    assert isinstance(description, LaunchDescription)
    assert any(isinstance(action, OpaqueFunction) for action in description.entities)
    context = launch_context(module)
    assert context.launch_configurations['use_sim_time'] == 'true'
    assert context.launch_configurations['perception_mode'] == 'yolo'
    assert context.launch_configurations['use_evaluation'] == 'true'
    assert context.launch_configurations['randomize'] == 'false'


def test_hardware_branch_never_prepares_or_spawns_simulation(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The false-clock branch delegates to hardware bringup without touching Gazebo assets."""
    module = load_simulation(monkeypatch, tmp_path)
    forbidden = Mock(side_effect=AssertionError('hardware branch must not prepare simulation'))
    monkeypatch.setattr(module, 'write_world', forbidden)
    monkeypatch.setattr(module, 'prepare_robot', forbidden)
    context = launch_context(module, use_sim_time='false', use_recording='true')
    actions = module._bringup(context)
    assert len(actions) == 1 and isinstance(actions[0], IncludeLaunchDescription)
    arguments = dict(actions[0].launch_arguments)
    assert arguments == {'use_sim_time': 'false', 'use_evaluation': 'true',
                         'use_recording': 'true'}
    forbidden.assert_not_called()


@pytest.mark.parametrize('mode,learned,environment', [
    ('yolo', 'true', 'simulation'), ('ground_truth', 'false', 'simulation_oracle'),
])
def test_simulation_composes_real_assets_and_preserves_public_interfaces(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path, native_robot: Path,
        mode: str, learned: str, environment: str) -> None:
    """Generate actual assets and inspect process definitions without running them.

    Args:
        monkeypatch: Test patch manager.
        tmp_path: Temporary generated asset directory.
        native_robot: Actual exercise-08 M3 Pro description.
        mode: Explicit perception mode.
        learned: Expected learned-perception switch in master bringup.
        environment: Required evaluation label for this mode.
    """
    module = load_simulation(monkeypatch, tmp_path)
    original_node = module.Node
    captured = []

    def capture_node(**kwargs: Any) -> object:
        """Keep real Node actions while capturing their argument contracts.

        Args:
            **kwargs: Actual simulation Node constructor settings.

        Returns:
            Real Node action; execution remains deferred.
        """
        captured.append(kwargs)
        return original_node(**kwargs)

    monkeypatch.setattr(module, 'Node', capture_node)
    directory = tmp_path / 'condition'
    context = launch_context(module, seed='51', randomize='true', perception_mode=mode,
                             output_dir=str(directory), robot_urdf=str(native_robot),
                             use_recording='true', yolo_model='/models/local-cup.pt')
    actions = module._bringup(context)
    metadata = json.loads((directory / 'condition.json').read_text())
    assert metadata['seed'] == 51
    assert metadata['perception_mode'] == mode
    assert metadata['use_sim_time'] is True
    assert metadata['robot_urdf'] == str(native_robot.resolve())
    assert (directory / 'm3pro.urdf').is_file()
    assert (directory / 'room.world').is_file()
    assert (directory / 'room.pgm').is_file()
    assert (directory / 'map.yaml').is_file()
    parameters = yaml.safe_load((directory / 'eira.yaml').read_text())['/**']
    assert parameters['vision_manager']['ros__parameters']['model_path'] == '/models/local-cup.pt'
    assert parameters['grasp_executor']['ros__parameters']['joint_feedback_is_measured'] is True
    nav = yaml.safe_load((directory / 'nav2.yaml').read_text())
    navigator = nav['bt_navigator']['ros__parameters']
    assert Path(navigator['default_nav_through_poses_bt_xml']).is_file()
    assert Path(navigator['default_nav_to_pose_bt_xml']).is_file()
    master = next(action for action in actions if isinstance(action, IncludeLaunchDescription)
                  and 'params_file' in dict(action.launch_arguments))
    arguments = dict(master.launch_arguments)
    assert arguments['use_sim_time'] == 'true'
    assert arguments['use_perception'] == learned
    assert arguments['logger_environment'] == environment
    assert arguments['random_seed'] == '51'
    assert arguments['use_recording'] == 'true'
    for name in ('use_base', 'use_robot_tf', 'use_camera', 'use_arm'):
        assert arguments[name] == 'false'
    executables = {definition['executable'] for definition in captured}
    assert {'robot_state_publisher', 'spawn_entity.py', 'sim_arm_bridge', 'sim_depth_noise'} <= (
        executables)
    assert ('sim_perception_oracle' in executables) == (mode == 'ground_truth')
    for definition in captured:
        if definition['executable'] != 'spawn_entity.py':
            assert definition['parameters'][0]['use_sim_time'] is True


def test_invalid_perception_mode_fails_before_asset_creation(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Unknown perception modes cannot silently substitute oracle detections."""
    module = load_simulation(monkeypatch, tmp_path)
    context = launch_context(module, perception_mode='fake_model')
    with pytest.raises(ValueError, match='perception_mode'):
        module._bringup(context)


def test_missing_robot_asset_is_not_replaced_with_a_generic_model(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Explicit absent vendor models produce a clear source-asset error."""
    module = load_simulation(monkeypatch, tmp_path)
    context = launch_context(module, robot_urdf=str(tmp_path / 'missing.urdf'),
                             output_dir=str(tmp_path / 'condition'))
    with pytest.raises(FileNotFoundError, match='missing.urdf'):
        module._bringup(context)
