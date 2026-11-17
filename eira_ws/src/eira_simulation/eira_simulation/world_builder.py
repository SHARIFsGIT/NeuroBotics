"""Generate seeded room geometry and a matching occupancy map.

Author: E-AIRA maintainers.
Hardware target: ROSMASTER M3 Pro Gazebo Classic / ROS 2 Humble.
"""

from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path
import random
import xml.etree.ElementTree as ET

import numpy as np
import yaml


@dataclass(frozen=True)
class WorldSettings:
    """Describe one reproducible randomized condition, in SI units.

    Args:
        seed: Randomization seed saved alongside generated world assets.
        randomize: Whether cup, lighting and sensor noise are randomized.
        room_size: Inner room side length.
        wall_height: Wall height.
        table_height: Height of table surface.
        cup_x: Nominal cup/table x coordinate.
        cup_y: Nominal cup/table y coordinate.
        cup_jitter: Maximum cup displacement on the tabletop in each axis.
    """

    seed: int = 0
    randomize: bool = False
    room_size: float = 5.0
    wall_height: float = 2.0
    table_height: float = 0.5
    cup_x: float = 0.8
    cup_y: float = 0.0
    cup_jitter: float = 0.15


def _element(parent: ET.Element, tag: str, value: object) -> ET.Element:
    """Append an SDF value element.

    Args:
        parent: XML parent.
        tag: Element name.
        value: Text content.
    Returns:
        Created XML element.
    """
    node = ET.SubElement(parent, tag)
    node.text = str(value)
    return node


def _box(world: ET.Element, name: str, pose: tuple, size: tuple,
         color: str, collision: bool = True) -> None:
    """Create a static SDF box with deterministic collision geometry.

    Args:
        world: SDF world.
        name: Unique model name.
        pose: Model xyz coordinates.
        size: Box xyz dimensions.
        color: RGBA material string.
        collision: Whether the box is a physical obstacle.
    """
    model = ET.SubElement(world, 'model', name=name)
    _element(model, 'static', 'true')
    _element(model, 'pose', ' '.join(map(str, (*pose, 0, 0, 0))))
    link = ET.SubElement(model, 'link', name='body')
    for kind in (('collision', 'visual') if collision else ('visual',)):
        item = ET.SubElement(link, kind, name=kind)
        geometry = ET.SubElement(item, 'geometry')
        _element(ET.SubElement(geometry, 'box'), 'size', ' '.join(map(str, size)))
        if kind == 'visual':
            material = ET.SubElement(item, 'material')
            _element(material, 'ambient', color)
            _element(material, 'diffuse', color)


def write_world(directory: Path, settings: WorldSettings) -> dict:
    """Write a self-contained SDF world, occupancy grid and condition manifest.

    Args:
        directory: Destination directory.
        settings: Validated experiment geometry and seed.
    Returns:
        Condition metadata including actual cup pose and sensor noise levels.
    Raises:
        ValueError: If geometry is unsafe or inconsistent.
        OSError: If assets cannot be written.
    """
    dimensions = (settings.room_size, settings.wall_height, settings.table_height,
                  settings.cup_x, settings.cup_y, settings.cup_jitter)
    if (not all(math.isfinite(value) for value in dimensions)
            or settings.room_size <= 2 or settings.wall_height <= 0
            or settings.table_height <= 0.04 or not 0 <= settings.cup_jitter <= 0.2
            or max(abs(settings.cup_x), abs(settings.cup_y)) + 0.3 >= settings.room_size/2
            or settings.seed < 0):
        raise ValueError('invalid room/table/randomization dimensions')
    directory.mkdir(parents=True, exist_ok=True)
    rng = random.Random(settings.seed)
    jitter = settings.cup_jitter if settings.randomize else 0.0
    x = settings.cup_x + rng.uniform(-jitter, jitter)
    y = settings.cup_y + rng.uniform(-jitter, jitter)
    illumination = rng.uniform(0.45, 0.95) if settings.randomize else 0.8
    depth_noise = rng.uniform(0.001, 0.008) if settings.randomize else 0.002
    lidar_noise = rng.uniform(0.002, 0.02) if settings.randomize else 0.005
    metadata = {**asdict(settings), 'cup_position': [x, y, settings.table_height + 0.06],
                'illumination': illumination, 'depth_noise_stddev_m': depth_noise,
                'lidar_noise_stddev_m': lidar_noise, 'simulation_model': 'kinematic_holonomic'}
    sdf = ET.Element('sdf', version='1.6')
    world = ET.SubElement(sdf, 'world', name='eira_room')
    physics = ET.SubElement(world, 'physics', name='default_physics', type='ode')
    _element(physics, 'max_step_size', 0.001)
    _element(physics, 'real_time_update_rate', 1000)
    _element(world, 'gravity', '0 0 -9.81')
    scene = ET.SubElement(world, 'scene')
    _element(scene, 'ambient', f'{illumination} {illumination} {illumination} 1')
    _element(scene, 'background', '0.7 0.75 0.8 1')
    light = ET.SubElement(world, 'light', name='ceiling', type='point')
    _element(light, 'pose', '0 0 2.8 0 0 0')
    _element(light, 'diffuse', f'{illumination} {illumination} {illumination} 1')
    _element(light, 'cast_shadows', 'true')
    attenuation = ET.SubElement(light, 'attenuation')
    for tag, value in (('range', 20), ('constant', 0.8), ('linear', 0.01), ('quadratic', 0.001)):
        _element(attenuation, tag, value)
    half, wall = settings.room_size / 2.0, 0.1
    _box(world, 'floor', (0, 0, -0.05), (settings.room_size + 0.2,)*2 + (0.1,),
         '0.8 0.8 0.8 1')
    for name, pose, size in (
            ('north', (0, half+wall/2, settings.wall_height/2),
             (settings.room_size+2*wall, wall, settings.wall_height)),
            ('south', (0, -half-wall/2, settings.wall_height/2),
             (settings.room_size+2*wall, wall, settings.wall_height)),
            ('east', (half+wall/2, 0, settings.wall_height/2),
             (wall, settings.room_size, settings.wall_height)),
            ('west', (-half-wall/2, 0, settings.wall_height/2),
             (wall, settings.room_size, settings.wall_height))):
        _box(world, name, pose, size, '0.9 0.9 0.9 1')
    _box(world, 'table', (settings.cup_x, settings.cup_y, settings.table_height-0.02),
         (0.6, 0.6, 0.04), '0.5 0.3 0.15 1')
    for index, (dx, dy) in enumerate(((-0.25, -0.25), (-0.25, 0.25),
                                     (0.25, -0.25), (0.25, 0.25))):
        _box(world, f'table_leg_{index}',
             (settings.cup_x+dx, settings.cup_y+dy, (settings.table_height-0.04)/2),
             (0.04, 0.04, settings.table_height-0.04), '0.5 0.3 0.15 1')
    _box(world, 'start_marker', (-1.5, 0, 0.002), (0.35, 0.35, 0.002),
         '0.1 0.8 0.1 1', collision=False)
    cup = ET.SubElement(world, 'model', name='cup')
    _element(cup, 'pose', f'{x} {y} {settings.table_height + 0.06} 0 0 0')
    link = ET.SubElement(cup, 'link', name='cup_link')
    inertial = ET.SubElement(link, 'inertial')
    _element(inertial, 'mass', 0.04)
    inertia = ET.SubElement(inertial, 'inertia')
    for tag, value in (('ixx', 0.000057), ('iyy', 0.000057), ('izz', 0.000018),
                       ('ixy', 0), ('ixz', 0), ('iyz', 0)):
        _element(inertia, tag, value)
    for kind in ('collision', 'visual'):
        item = ET.SubElement(link, kind, name=kind)
        shape = ET.SubElement(ET.SubElement(item, 'geometry'), 'cylinder')
        _element(shape, 'radius', 0.03)
        _element(shape, 'length', 0.12)
        if kind == 'visual':
            material = ET.SubElement(item, 'material')
            _element(material, 'ambient', '0.8 0.03 0.03 1')
            _element(material, 'diffuse', '0.8 0.03 0.03 1')
    plugin = ET.SubElement(world, 'plugin', name='gazebo_ros_state',
                           filename='libgazebo_ros_state.so')
    _element(ET.SubElement(plugin, 'ros'), 'namespace', '/gazebo')
    _element(plugin, 'update_rate', 20)
    ET.ElementTree(sdf).write(directory / 'room.world', encoding='unicode', xml_declaration=True)
    (directory / 'condition.json').write_text(json.dumps(metadata, indent=2) + '\n')
    write_map(directory, settings)
    return metadata


def write_map(directory: Path, settings: WorldSettings, resolution: float = 0.05) -> None:
    """Rasterize the exact wall/pedestal footprints into a Nav2 occupancy map.

    Args:
        directory: Output directory.
        settings: World geometry matching the SDF.
        resolution: Metres per pixel.
    Raises:
        ValueError: If resolution is nonpositive.
    """
    if resolution <= 0:
        raise ValueError('map resolution must be positive')
    extent = settings.room_size + 0.4
    side = int(round(extent / resolution))
    pixels = np.full((side, side), 254, dtype=np.uint8)
    origin = -extent / 2
    for row in range(side):
        for col in range(side):
            x, y = origin + (col+0.5)*resolution, origin + (side-row-0.5)*resolution
            outside = abs(x) >= settings.room_size/2 or abs(y) >= settings.room_size/2
            table = abs(x-settings.cup_x) <= 0.3 and abs(y-settings.cup_y) <= 0.3
            if outside or table:
                pixels[row, col] = 0
    with (directory / 'room.pgm').open('wb') as handle:
        handle.write(f'P5\n{side} {side}\n255\n'.encode())
        handle.write(pixels.tobytes())
    (directory / 'map.yaml').write_text(yaml.safe_dump({
        'image': 'room.pgm', 'resolution': resolution, 'origin': [origin, origin, 0.0],
        'negate': 0, 'occupied_thresh': 0.65, 'free_thresh': 0.196}))
