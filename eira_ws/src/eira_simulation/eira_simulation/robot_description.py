"""Adapt the supplied M3 Pro URDF to Gazebo sensors and kinematic controls.

Author: E-AIRA maintainers.
Hardware target: M3 Pro geometry / ROS 2 Humble Gazebo Classic.
The native CAD geometry and joint origins are reused, not replaced by a generic
mobile robot. Planar motion and joint trajectories are kinematic abstractions;
this adapter does not claim calibrated mecanum traction or contact dynamics.
"""

from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

from ament_index_python.packages import PackageNotFoundError, get_package_share_directory


def locate_robot(explicit: str = '') -> Path:
    """Find the installed vendor model or the supplied exercise-08 M3Pro model.

    Args:
        explicit: Optional absolute URDF/Xacro path.
    Returns:
        Existing robot description path.
    Raises:
        FileNotFoundError: If no actual model is available.
    """
    if explicit:
        path = Path(explicit).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(path)
        return path
    for package, relative in (('M3Pro', 'urdf/m3pro.urdf'),
                              ('neurobotics', 'urdf/neurobotics.urdf')):
        try:
            path = Path(get_package_share_directory(package)) / relative
            if path.is_file():
                return path
        except PackageNotFoundError:
            continue
    for ancestor in Path(__file__).resolve().parents:
        path = ancestor / ('08. robot model/neurobotics_ws/src/neurobotics/'
                           'urdf/neurobotics.urdf')
        if path.is_file():
            return path
    raise FileNotFoundError('install M3Pro/neurobotics robot assets or pass robot_urdf:=PATH')


def _text(parent: ET.Element, tag: str, value: object) -> ET.Element:
    """Append a text element.

    Args:
        parent: XML parent.
        tag: Element name.
        value: Element value.
    Returns:
        Created element.
    """
    item = ET.SubElement(parent, tag)
    item.text = str(value)
    return item


def prepare_robot(source: Path, destination: Path, lidar_noise: float = 0.005,
                  depth_noise: float = 0.002) -> str:
    """Preserve native geometry and install explicit simulated sensor contracts.

    Args:
        source: Existing M3 Pro URDF or Xacro.
        destination: Output URDF file for robot_state_publisher and spawn_entity.
        lidar_noise: Seeded scan standard deviation in metres.
        depth_noise: Seeded RGB-D sensor standard deviation.
    Returns:
        Prepared XML robot description.
    Raises:
        OSError: If model assets are missing or cannot be written.
        ValueError: If the native model lacks required links.
        subprocess.SubprocessError: If Xacro expansion fails or times out.
    """
    if source.suffix == '.xacro':
        xml = subprocess.run(['xacro', str(source)], capture_output=True, text=True,
                             timeout=15.0, check=True).stdout
    else:
        xml = source.read_text()
    root = ET.fromstring(xml)
    links = {link.attrib['name'] for link in root.findall('link')}
    if 'base_link' not in links:
        raise ValueError('robot must define base_link')
    # Strip competing native simulation controllers and duplicate sensor plugins.
    for node in list(root):
        if node.tag == 'ros2_control' or (node.tag == 'gazebo' and (
                node.find('plugin') is not None or node.find('sensor') is not None)):
            root.remove(node)
    for mesh in root.iter('mesh'):
        value = mesh.attrib.get('filename', '')
        if value.startswith('package://'):
            package, _, relative = value[len('package://'):].partition('/')
            try:
                path = Path(get_package_share_directory(package)) / relative
            except PackageNotFoundError:
                path = source.parent.parent / relative
            if not path.is_file():
                raise FileNotFoundError(f'missing mesh: {value} ({path})')
            mesh.set('filename', path.resolve().as_uri())
    for name, xyz, rpy in (
            ('camera_link', '-0.05 0 0.65', '0 0.35 0'),
            ('camera_color_optical_frame', '0 0 0', '-1.57079632679 0 -1.57079632679'),
            ('eira_laser', '0 0 0.28', '0 0 0')):
        if name in links:
            raise ValueError(f'simulation sensor link already exists: {name}')
        ET.SubElement(root, 'link', name=name)
        joint = ET.SubElement(root, 'joint', name=f'{name}_fixed', type='fixed')
        ET.SubElement(joint, 'parent', link='camera_link' if 'optical' in name else 'base_link')
        ET.SubElement(joint, 'child', link=name)
        ET.SubElement(joint, 'origin', xyz=xyz, rpy=rpy)
    gazebo = ET.SubElement(root, 'gazebo')
    planar = ET.SubElement(gazebo, 'plugin', name='eira_holonomic',
                           filename='libgazebo_ros_planar_move.so')
    ros = ET.SubElement(planar, 'ros')
    _text(ros, 'remapping', 'cmd_vel:=/cmd_vel')
    _text(ros, 'remapping', 'odom:=/odom')
    for tag, value in (('update_rate', 50), ('publish_rate', 30), ('publish_odom', 'true'),
                       ('publish_odom_tf', 'true'), ('odometry_frame', 'odom'),
                       ('robot_base_frame', 'base_link')):
        _text(planar, tag, value)
    trajectory = ET.SubElement(gazebo, 'plugin', name='eira_joint_trajectory',
                               filename='libgazebo_ros_joint_pose_trajectory.so')
    _text(ET.SubElement(trajectory, 'ros'), 'remapping',
          'set_joint_trajectory:=/eira/sim/joint_trajectory')
    _text(trajectory, 'update_rate', 50)
    states = ET.SubElement(gazebo, 'plugin', name='eira_joint_states',
                           filename='libgazebo_ros_joint_state_publisher.so')
    _text(states, 'update_rate', 30)
    for joint in root.findall('joint'):
        if joint.attrib.get('type') in ('revolute', 'continuous', 'prismatic'):
            _text(states, 'joint_name', joint.attrib['name'])
    laser = ET.SubElement(ET.SubElement(root, 'gazebo', reference='eira_laser'),
                          'sensor', name='eira_scan', type='ray')
    _text(laser, 'always_on', 'true')
    _text(laser, 'update_rate', 10)
    ray = ET.SubElement(laser, 'ray')
    horizontal = ET.SubElement(ET.SubElement(ray, 'scan'), 'horizontal')
    for tag, value in (('samples', 360), ('resolution', 1), ('min_angle', -3.14159265359),
                       ('max_angle', 3.14159265359)):
        _text(horizontal, tag, value)
    range_element = ET.SubElement(ray, 'range')
    for tag, value in (('min', 0.10), ('max', 8.0), ('resolution', 0.01)):
        _text(range_element, tag, value)
    noise = ET.SubElement(ray, 'noise')
    for tag, value in (('type', 'gaussian'), ('mean', 0), ('stddev', lidar_noise)):
        _text(noise, tag, value)
    plugin = ET.SubElement(laser, 'plugin', name='eira_lidar',
                           filename='libgazebo_ros_ray_sensor.so')
    _text(ET.SubElement(plugin, 'ros'), 'remapping', '~/out:=/scan')
    _text(plugin, 'output_type', 'sensor_msgs/LaserScan')
    _text(plugin, 'frame_name', 'eira_laser')
    camera = ET.SubElement(ET.SubElement(root, 'gazebo', reference='base_link'),
                           'sensor', name='eira_rgbd', type='depth')
    _text(camera, 'pose', '-0.05 0 0.65 0 0.35 0')
    _text(camera, 'always_on', 'true')
    _text(camera, 'update_rate', 10)
    lens = ET.SubElement(camera, 'camera')
    _text(lens, 'horizontal_fov', 1.085)
    image = ET.SubElement(lens, 'image')
    for tag, value in (('width', 640), ('height', 480), ('format', 'R8G8B8')):
        _text(image, tag, value)
    clip = ET.SubElement(lens, 'clip')
    _text(clip, 'near', 0.05)
    _text(clip, 'far', 5.0)
    plugin = ET.SubElement(camera, 'plugin', name='eira_rgbd_plugin',
                           filename='libgazebo_ros_camera.so')
    ros = ET.SubElement(plugin, 'ros')
    for remap in ('/eira_rgbd/image_raw:=/camera/color/image_raw',
                  '/eira_rgbd/camera_info:=/camera/color/camera_info',
                  '/eira_rgbd/depth/image_raw:=/eira/sim/depth_raw',
                  '/eira_rgbd/depth/camera_info:=/camera/depth/camera_info'):
        _text(ros, 'remapping', remap)
    _text(plugin, 'camera_name', 'eira_rgbd')
    _text(plugin, 'frame_name', 'camera_color_optical_frame')
    destination.parent.mkdir(parents=True, exist_ok=True)
    output = ET.tostring(root, encoding='unicode')
    destination.write_text(output)
    return output
