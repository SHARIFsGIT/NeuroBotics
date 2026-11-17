"""Verify reproducible room geometry, depth noise, and native robot sensor contracts.

Author: E-AIRA contributors.
Hardware target: ROSMASTER M3 Pro / ROS 2 Humble Gazebo Classic, hardware-free tests.
"""

import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

from ament_index_python.packages import PackageNotFoundError
import numpy as np
import pytest
import yaml

from eira_simulation.robot_description import locate_robot, prepare_robot
from eira_simulation.sensor_noise import noisy_depth
from eira_simulation.world_builder import WorldSettings, write_map, write_world


def values(element: ET.Element, path: str) -> tuple[float, ...]:
    """Read numeric SDF coordinates for geometric comparisons.

    Args:
        element: SDF parent element.
        path: Relative element path.

    Returns:
        Parsed numeric coordinates.
    """
    return tuple(float(value) for value in element.findtext(path).split())


def test_seed_reproduces_every_generated_asset(tmp_path: Path) -> None:
    """Repeated seeded conditions produce byte-identical worlds, maps and metadata."""
    left, right = tmp_path / 'left', tmp_path / 'right'
    settings = WorldSettings(seed=321, randomize=True)
    assert write_world(left, settings) == write_world(right, settings)
    for name in ('room.world', 'room.pgm', 'map.yaml', 'condition.json'):
        assert (left / name).read_bytes() == (right / name).read_bytes()


def test_randomized_conditions_remain_inside_calibrated_bounds(tmp_path: Path) -> None:
    """Randomization perturbs declared quantities without moving the table or walls."""
    first = write_world(tmp_path / 'one', WorldSettings(seed=1, randomize=True))
    second = write_world(tmp_path / 'two', WorldSettings(seed=2, randomize=True))
    assert first['cup_position'] != second['cup_position']
    for metadata in (first, second):
        assert abs(metadata['cup_position'][0] - 0.8) <= 0.15
        assert abs(metadata['cup_position'][1]) <= 0.15
        assert metadata['cup_position'][2] == pytest.approx(0.56)
        assert 0.45 <= metadata['illumination'] <= 0.95
        assert 0.001 <= metadata['depth_noise_stddev_m'] <= 0.008
        assert 0.002 <= metadata['lidar_noise_stddev_m'] <= 0.02


def test_room_walls_table_and_cup_geometry(tmp_path: Path) -> None:
    """The 5 m room, 2 m walls and 0.5 m tabletop match the published condition."""
    metadata = write_world(tmp_path, WorldSettings())
    world = ET.parse(tmp_path / 'room.world').getroot().find('world')
    models = {model.attrib['name']: model for model in world.findall('model')}
    for name in ('north', 'south', 'east', 'west'):
        size = values(models[name], 'link/collision/geometry/box/size')
        pose = values(models[name], 'pose')
        assert size[2] == 2.0
        assert pose[2] == 1.0
    north = models['north']
    south = models['south']
    inner_north = values(north, 'pose')[1] - values(north, 'link/collision/geometry/box/size')[1]/2
    inner_south = values(south, 'pose')[1] + values(south, 'link/collision/geometry/box/size')[1]/2
    assert inner_north - inner_south == pytest.approx(5.0)
    table = models['table']
    assert (values(table, 'pose')[2]
            + values(table, 'link/collision/geometry/box/size')[2]/2) == pytest.approx(0.5)
    cup = models['cup']
    center = values(cup, 'pose')[:3]
    length = float(cup.findtext('link/collision/geometry/cylinder/length'))
    assert center == pytest.approx(metadata['cup_position'])
    assert center[2] - length/2 == pytest.approx(0.5)
    assert float(cup.findtext('link/inertial/mass')) > 0.0
    assert models['start_marker'].find('link/collision') is None
    assert json.loads((tmp_path / 'condition.json').read_text()) == metadata


def test_pgm_map_matches_wall_and_table_footprints(tmp_path: Path) -> None:
    """Rasterized occupied pixels block room exterior and table while leaving home free."""
    write_world(tmp_path, WorldSettings())
    header, dimensions, maximum, raw = (tmp_path / 'room.pgm').read_bytes().split(b'\n', 3)
    width, height = (int(value) for value in dimensions.split())
    pixels = np.frombuffer(raw, dtype=np.uint8).reshape(height, width)
    metadata = yaml.safe_load((tmp_path / 'map.yaml').read_text())
    assert header == b'P5' and maximum == b'255'
    assert pixels.shape == (108, 108)
    assert set(np.unique(pixels)) == {0, 254}
    origin_x, origin_y, _ = metadata['origin']
    resolution = metadata['resolution']

    def sample(x: float, y: float) -> int:
        """Read the map occupancy at a world location.

        Args:
            x: World x coordinate.
            y: World y coordinate.

        Returns:
            PGM intensity at the corresponding pixel.
        """
        column = int(math.floor((x - origin_x)/resolution))
        row = height - 1 - int(math.floor((y - origin_y)/resolution))
        return int(pixels[row, column])

    assert sample(-1.5, 0.0) == 254
    assert sample(0.8, 0.0) == 0
    assert sample(2.6, 0.0) == 0
    assert sample(0.0, -2.6) == 0


@pytest.mark.parametrize('settings', [
    WorldSettings(room_size=2.0), WorldSettings(wall_height=0.0),
    WorldSettings(table_height=0.0), WorldSettings(cup_jitter=0.21),
])
def test_invalid_world_geometry_is_rejected(tmp_path: Path, settings: WorldSettings) -> None:
    """Unsafe configured dimensions cannot produce an apparently valid world.

    Args:
        tmp_path: Test output directory.
        settings: Invalid geometry settings.
    """
    with pytest.raises(ValueError):
        write_world(tmp_path, settings)


def test_invalid_map_resolution_is_rejected(tmp_path: Path) -> None:
    """A zero pixel resolution cannot enter map generation."""
    with pytest.raises(ValueError):
        write_map(tmp_path, WorldSettings(), resolution=0.0)


def test_depth_noise_is_seeded_metric_and_preserves_invalid_returns() -> None:
    """Noise never manufactures a valid range from an invalid camera return."""
    depth = np.full((100, 100), 1.0, dtype=np.float32)
    depth[0, :4] = [0.0, np.nan, np.inf, -1.0]
    left = noisy_depth(depth, 0.008, np.random.default_rng(77))
    right = noisy_depth(depth, 0.008, np.random.default_rng(77))
    assert np.array_equal(left, right, equal_nan=True)
    assert left.dtype == np.float32
    assert left[0, 0] == 0.0 and math.isnan(left[0, 1])
    assert math.isinf(left[0, 2]) and left[0, 3] == -1.0
    measured = left[1:] - depth[1:]
    assert float(np.std(measured)) == pytest.approx(0.008, rel=0.04)
    assert abs(float(np.mean(measured))) < 0.0003
    assert np.array_equal(noisy_depth(depth, 0.0, np.random.default_rng(1)), depth, equal_nan=True)


@pytest.mark.parametrize('sigma', [-0.1, math.inf, math.nan])
def test_invalid_depth_noise_is_rejected(sigma: float) -> None:
    """Nonfinite or negative sensor noise must be rejected.

    Args:
        sigma: Invalid standard deviation.
    """
    with pytest.raises(ValueError):
        noisy_depth(np.ones((2, 2)), sigma, np.random.default_rng(0))


def test_prepared_model_reuses_native_geometry_and_exact_sensor_contracts(
        tmp_path: Path, native_robot: Path) -> None:
    """Keep M3 Pro joints/CAD while replacing conflicting native Gazebo controllers."""
    original = ET.parse(native_robot).getroot()
    output = prepare_robot(native_robot, tmp_path / 'm3pro.urdf')
    prepared = ET.fromstring(output)
    original_links = {link.attrib['name'] for link in original.findall('link')}
    prepared_links = {link.attrib['name'] for link in prepared.findall('link')}
    assert original_links <= prepared_links
    assert {'arm1', 'arm2', 'arm3', 'arm4', 'arm5', 'Gripping'} <= prepared_links
    original_joints = {joint.attrib['name'] for joint in original.findall('joint')}
    assert original_joints <= {joint.attrib['name'] for joint in prepared.findall('joint')}
    assert prepared.find('ros2_control') is None
    plugins = {item.attrib['name']: item for item in prepared.iter('plugin')}
    assert 'gazebo_ros2_control' not in plugins
    assert len([plugin for plugin in plugins.values()
                if plugin.attrib['filename'] == 'libgazebo_ros_planar_move.so']) == 1
    remaps = {item.text for item in prepared.iter('remapping')}
    assert {'cmd_vel:=/cmd_vel', 'odom:=/odom', '~/out:=/scan',
            '/eira_rgbd/image_raw:=/camera/color/image_raw',
            '/eira_rgbd/camera_info:=/camera/color/camera_info',
            '/eira_rgbd/depth/image_raw:=/eira/sim/depth_raw',
            'set_joint_trajectory:=/eira/sim/joint_trajectory'} <= remaps
    assert plugins['eira_rgbd_plugin'].findtext('frame_name') == 'camera_color_optical_frame'
    optical = prepared.find("joint[@name='camera_color_optical_frame_fixed']")
    assert optical.find('parent').attrib['link'] == 'camera_link'
    assert optical.find('child').attrib['link'] == 'camera_color_optical_frame'
    assert np.asarray(optical.find('origin').attrib['rpy'].split(), dtype=float) == pytest.approx(
        [-math.pi/2, 0.0, -math.pi/2])
    for mesh in prepared.iter('mesh'):
        assert mesh.attrib['filename'].startswith('file:///')
    assert (tmp_path / 'm3pro.urdf').read_text() == output


def test_missing_explicit_robot_and_mesh_errors_are_actionable(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Missing native assets fail explicitly rather than substituting a generic robot."""
    with pytest.raises(FileNotFoundError):
        locate_robot(str(tmp_path / 'absent.urdf'))
    source = tmp_path / 'urdf/robot.urdf'
    source.parent.mkdir()
    source.write_text('<robot name="M3Pro"><link name="base_link"><visual><geometry>'
                      '<mesh filename="package://missing_vendor/meshes/base.STL"/>'
                      '</geometry></visual></link></robot>')

    def missing_package(name: str) -> str:
        """Simulate an unavailable vendor mesh package.

        Args:
            name: Missing ROS package.

        Raises:
            PackageNotFoundError: Always raised for this fixture.
        """
        raise PackageNotFoundError(name)

    monkeypatch.setattr('eira_simulation.robot_description.get_package_share_directory',
                        missing_package)
    with pytest.raises(FileNotFoundError, match='missing mesh'):
        prepare_robot(source, tmp_path / 'prepared.urdf')


def test_robot_requires_a_real_base_link(tmp_path: Path) -> None:
    """An unrelated robot description cannot silently masquerade as M3 Pro geometry."""
    source = tmp_path / 'unrelated.urdf'
    source.write_text('<robot name="other"><link name="body"/></robot>')
    with pytest.raises(ValueError, match='base_link'):
        prepare_robot(source, tmp_path / 'prepared.urdf')


def test_state_namespace_and_camera_visibility_at_grasp_standoff(
        tmp_path: Path, native_robot: Path) -> None:
    """Oracle discovery and real RGB-D geometry remain valid during final approach."""
    write_world(tmp_path, WorldSettings())
    plugin = ET.parse(tmp_path/'room.world').find('.//plugin[@name="gazebo_ros_state"]')
    assert plugin.findtext('ros/namespace') == '/gazebo'
    robot = ET.fromstring(prepare_robot(native_robot, tmp_path/'robot.urdf'))
    sensor = robot.find('.//sensor[@name="eira_rgbd"]')
    sx, _, sz, _, pitch, _ = values(sensor, 'pose')
    horizontal = float(sensor.findtext('camera/horizontal_fov'))
    vertical_half = math.atan(math.tan(horizontal/2)*480/640)
    for distance in (0.19, 0.5, 1.0, 3.0):
        for cup_height in (0.5, 0.56, 0.62):
            bearing = math.atan2(sz-cup_height, distance-sx)
            assert abs(bearing-pitch) < vertical_half


def test_nonfinite_world_geometry_is_rejected(tmp_path: Path) -> None:
    """NaN world dimensions cannot silently enter generated SDF assets."""
    with pytest.raises(ValueError):
        write_world(tmp_path, WorldSettings(room_size=math.nan))
