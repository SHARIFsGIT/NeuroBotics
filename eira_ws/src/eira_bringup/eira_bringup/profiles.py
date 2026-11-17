"""Exercise-to-runtime catalog using native hardware packages and E-AIRA adapters.

Author: E-AIRA maintainers.
Hardware target: ROSMASTER M3 Pro / Jetson Orin NX, ROS 2 Humble.
"""

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class Profile:
    """Describe a bounded, explicitly selected exercise workflow.

    Args:
        exercises: Actual source-folder numbers covered by this workflow.
        package: Existing ROS package or E-AIRA adapter package.
        resource: Native launch filename or executable.
        launch: Whether resource is a launch file.
        motion: Whether the profile can command the mobile base.
        description: Operator-facing purpose.
    """

    exercises: tuple[int, ...]
    package: str
    resource: str
    launch: bool
    motion: bool
    description: str


PROFILES: dict[str, Profile] = {
    'arm_calibration': Profile((1,), 'M3Pro_demo', 'arm_offset', False, True,
                               'Native AprilTag arm-offset calibration; operator supervised.'),
    'joystick': Profile((2,), 'yahboomcar_ctrl', 'yahboom_joy_M3Pro', False, True,
                        'Native joystick arm/base control; run joy/joy_node alongside.'),
    'keyboard': Profile((3,), 'yahboomcar_ctrl', 'yahboom_keyboard', False, True,
                        'Native interactive keyboard arm/base control.'),
    'calibrate_angular': Profile((4,), 'calibration', 'calibrate_angular', False, True,
                                 'Native measured angular calibration; no firmware changes.'),
    'calibrate_linear': Profile((5,), 'calibration', 'calibrate_linear', False, True,
                                'Native measured linear calibration; no firmware changes.'),
    'sensor_skills': Profile((6, 7, 11, 12, 13), 'eira_bringup', 'exercise_skills', False, True,
                             'Adapted line-follow, LiDAR avoidance, tracking, and guard.'),
    'robot_display': Profile((8,), 'M3Pro', 'display.launch.py', True, False,
                             'Physical robot model and TF visualization.'),
    'simulation': Profile((8,), 'neurobotics', 'gazebo.launch.py', True, False,
                          'Original exercise simulation; separate differential-drive model.'),
    'lidar_view': Profile((9,), 'rviz2', 'rviz2', False, False,
                          'Inspect the existing /scan stream with RViz.'),
    'lidar_fusion': Profile((10,), 'ira_laser_tools', 'merge_multi.launch.py', True, False,
                            'Native dual-scan fusion and robot-body filtering.'),
    'gmapping': Profile((14,), 'slam_mapping', 'gmapping.launch.py', True, False,
                        'Native Gmapping SLAM; keep mapping separate from localization.'),
    'cartographer': Profile((15,), 'slam_mapping', 'cartographer.launch.py', True, False,
                            'Native Cartographer SLAM with the robot calibration.'),
    'slam_toolbox': Profile((16,), 'slam_mapping', 'online_async_launch.py', True, False,
                            'Native asynchronous SLAM Toolbox mapping.'),
    'save_map': Profile((14, 15, 16), 'nav2_map_server', 'map_saver_cli', False, False,
                        'Save occupancy map; pass -f via profile_arguments.'),
    'navigation': Profile((17, 18), 'eira_bringup', 'eira_master.launch.py', True, True,
                          'Gated Nav2 with named single/multiple waypoint plans.'),
    'cartographer_localization': Profile((19,), 'M3Pro_navigation',
                                         'cartographer_localization.launch.py', True, False,
                                         'Native localization against a recorded posegraph.'),
    'rtabmap_mapping': Profile((20,), 'rtabmap_launch', 'rtabmap.launch.py', True, False,
                               'RGB-D/LiDAR mapping with existing odometry.'),
    'rtabmap_localization': Profile((21,), 'rtabmap_launch', 'rtabmap.launch.py', True, False,
                                    'RGB-D localization using an existing RTAB-Map database.'),
    'tag_recording': Profile((22, 24), 'm3pro_bringup', 'record_tag.launch.py', True, False,
                             'Record measured fiducial map poses with the native tool.'),
    'camera': Profile((25,), 'orbbec_camera', 'dabai_dcw2.launch.py', True, False,
                      'Registered RGB-D driver without redundant point-cloud processing.'),
    'depth_tools': Profile((26, 27), 'eira_perception', 'vision_manager', False, False,
                           'Metric depth probe and pseudocolor outputs.'),
    'gesture': Profile((29,), 'eira_perception', 'gesture_recognizer', False, False,
                       'Local MediaPipe confirmation/cancellation.'),
    'edge': Profile((30,), 'eira_bringup', 'edge_monitor', False, False,
                    'Calibrated ground-plane drop-off interlock.'),
    'perception': Profile((28, 31, 32, 33), 'eira_perception', 'vision_manager', False, False,
                          'Persistent YOLO/transformer tracking, color, width and volume.'),
    'manipulation': Profile((22, 23), 'eira_manipulation', 'grasp_executor', False, True,
                            'Correlated grasp/release, calibrated gripper and color sorting.'),
}


def launch_argument_values(values: object) -> dict[str, str]:
    """Normalize JSON scalar values to ROS launch substitution strings.

    Args:
        values: Decoded profile_launch_arguments JSON.
    Returns:
        String-to-string launch argument mapping.
    Raises:
        ValueError: If keys or values are not supported finite scalars.
    """
    if not isinstance(values, dict) or not all(isinstance(key, str) for key in values):
        raise ValueError('profile_launch_arguments must be a JSON object with string keys')
    result = {}
    for key, value in values.items():
        if isinstance(value, bool):
            result[key] = 'true' if value else 'false'
        elif isinstance(value, str):
            result[key] = value
        elif isinstance(value, (int, float)) and math.isfinite(value):
            result[key] = str(value)
        else:
            raise ValueError(f'launch argument {key} must be a finite scalar')
    return result
