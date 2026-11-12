
import os

# ROS 2 imports
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node


def generate_launch_description():

    # =====================================================
    # 1. FIND ALL REQUIRED LAUNCH FILES
    # =====================================================

    # LiDAR merging launch file
    laser_merge_launch_file = os.path.join(
        get_package_share_directory('ira_laser_tools'),
        'launch',
        'merge_multi.launch.py'
    )

    # LiDAR filtering launch file
    laser_filter_launch_file = os.path.join(
        get_package_share_directory('yahboom_laser_filter'),
        'launch',
        'laser_filter_node.launch.py'
    )

    # IMU filtering launch file
    imu_filter_madgwick_launch_file = os.path.join(
        get_package_share_directory('imu_filter_madgwick'),
        'launch',
        'imu_filter.launch.py'
    )

    # EKF localization launch file
    ekf_odom_launch_file = os.path.join(
        get_package_share_directory('ekf_bringup'),
        'launch',
        'ekf.launch.py'
    )

    # Orbbec camera launch file
    camera_launch_file = os.path.join(
        get_package_share_directory('orbbec_camera'),
        'launch',
        'dabai_dcw2.launch.py'
    )


    # =====================================================
    # 2. START THE CUSTOM COSTMAP NODE
    # =====================================================

    updatecostmap = Node(
        package='updatecostmap',
        executable='update_costmap',
        name='update_costmap',
        output='screen'
    )


    # =====================================================
    # 3. PUBLISH STATIC TRANSFORM: BASE_LINK -> CAMERA_LINK
    # =====================================================

    base_link_camera_tf = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='static_transform_publisher_camera',
        arguments=[
            '0.05', '0.0', '0.38',  # X, Y, Z position (meters)
            '0', '0', '0',          # Yaw, Pitch, Roll (radians)
            'base_link',            # Parent frame
            'camera_link'           # Child frame
        ],
        output='screen'
    )


    # =====================================================
    # 4. START ALL ROS 2 NODES AND LAUNCH FILES
    # =====================================================

    return LaunchDescription([

        # Start IMU filtering
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                imu_filter_madgwick_launch_file
            )
        ),

        # Merge multiple LiDAR scans
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                laser_merge_launch_file
            )
        ),

        # Filter LiDAR data
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                laser_filter_launch_file
            )
        ),

        # Start EKF sensor fusion / odometry
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                ekf_odom_launch_file
            )
        ),

        # Start Orbbec camera
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                camera_launch_file
            )
        ),

        # Start custom costmap node
        updatecostmap,

        # Publish camera-to-robot static transform
        base_link_camera_tf,

    ])
