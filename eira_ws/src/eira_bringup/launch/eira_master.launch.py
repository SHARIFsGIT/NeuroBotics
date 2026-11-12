#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
eira_master.launch.py — single-command bringup of the complete E-AIRA stack.

Philosophy: **never re-implement a driver**. Every hardware component is
started by including the exact launch files already validated in the course
workspace; E-AIRA only adds the three cognition nodes on top:

    ┌─────────────────────────── eira_bringup (this file) ──────────────┐
    │  base:   imu_filter_madgwick + ira_laser_tools merge +            │
    │          yahboom_laser_filter + ekf_bringup   (= base_bringup)    │
    │  camera: orbbec_camera/dabai_dcw2.launch.py                       │
    │  arm:    arm_kin kin_srv (kin_ik_fk) + arm_util arm_status        │
    │  nav:    M3Pro_navigation navigation2.launch.py  (optional)       │
    │  tracker: smart_tracker super_tracker.launch.py (optional)        │
    │  ──────────────────────────────────────────────────────────────── │
    │  eira_brain.llm_task_planner + eira_perception.vision_manager +   │
    │  eira_manipulation.grasp_executor                                 │
    └────────────────────────────────────────────────────────────────────┘

Every robot-driver include is guarded: if a package is missing (e.g. running
in simulation or on a dev PC), a warning is printed and the rest of the
system still starts — this is what makes CI-style smoke tests possible.

Usage
-----
    # full system on the robot:
    ros2 launch eira_bringup eira_master.launch.py map:=$HOME/map/map.yaml

    # cognition only (drivers already running in other terminals):
    ros2 launch eira_bringup eira_master.launch.py \
        use_base:=false use_camera:=false use_arm:=false

    # everything except Nav2 + RViz (e.g. for a grasping-only experiment):
    ros2 launch eira_bringup eira_master.launch.py use_nav:=false use_rviz:=false
"""

import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration

from launch_ros.actions import Node


# ============================================================
# GUARDED INCLUDE HELPER
# ============================================================


def include_or_warn(package: str, launch_path: str, description: str,
                    condition=None, launch_arguments=None):
    """Include a robot-stack launch file; warn-and-skip when absent.

    Returning None instead of raising keeps the E-AIRA nodes runnable on
    machines without the Yahboom packages (simulation, CI, laptops).
    """
    try:
        full_path = os.path.join(
            get_package_share_directory(package), launch_path)
    except Exception:  # PackageNotFoundError — not installed here
        print(f"[eira_bringup] WARNING: package '{package}' not found — "
              f"skipping {description}. (Expected on non-robot machines.)")
        return None
    return IncludeLaunchDescription(
        PythonLaunchDescriptionSource(full_path),
        condition=condition,
        launch_arguments=launch_arguments or {},
    )


# ============================================================
# LAUNCH DESCRIPTION
# ============================================================


def generate_launch_description():

    eira_share = get_package_share_directory("eira_bringup")
    params_file = os.path.join(eira_share, "config", "eira_params.yaml")
    waypoints_file = os.path.join(eira_share, "config", "waypoints.yaml")

    # --------------------------------------------------------
    # LAUNCH ARGUMENTS
    # --------------------------------------------------------
    arguments = [
        DeclareLaunchArgument(
            "use_base", default_value="true",
            description="Start the proven base stack (IMU+LiDAR+EKF)."),
        DeclareLaunchArgument(
            "use_camera", default_value="true",
            description="Start the Dabai_DCW2 (orbbec_camera) driver."),
        DeclareLaunchArgument(
            "use_arm", default_value="true",
            description="Start arm_kin kin service + arm_util status."),
        DeclareLaunchArgument(
            "use_nav", default_value="true",
            description="Start Nav2 via M3Pro_navigation."),
        DeclareLaunchArgument(
            "use_tracker", default_value="false",
            description="Also start the smart_tracker transformer tracker."),
        DeclareLaunchArgument(
            "use_rviz", default_value="false",
            description="Start RViz2."),
        DeclareLaunchArgument(
            "map", default_value=os.path.expanduser("~/map/map.yaml"),
            description="Occupancy grid for Nav2 localization."),
        DeclareLaunchArgument(
            "params_file", default_value=params_file,
            description="E-AIRA node parameters."),
        DeclareLaunchArgument(
            "waypoints_file", default_value=waypoints_file,
            description="Named-pose database for the navigate action."),
    ]

    actions = [*arguments]

    # --------------------------------------------------------
    # 1. BASE STACK  (exact composition of base_bringup.launch.py,
    #    folders 17/18/22/23: IMU → laser merge → laser filter → EKF)
    # --------------------------------------------------------
    base_condition = IfCondition(LaunchConfiguration("use_base"))
    base_parts = [
        include_or_warn(
            "imu_filter_madgwick", "launch/imu_filter.launch.py",
            "IMU filter", condition=base_condition),
        include_or_warn(
            "ira_laser_tools", "launch/merge_multi.launch.py",
            "dual-LiDAR merger", condition=base_condition),
        include_or_warn(
            "yahboom_laser_filter", "launch/laser_filter_node.launch.py",
            "arm-masking laser filter", condition=base_condition),
        include_or_warn(
            "ekf_bringup", "launch/ekf.launch.py", "EKF odometry",
            condition=base_condition),
    ]
    actions.extend(part for part in base_parts if part is not None)

    # --------------------------------------------------------
    # 2. CAMERA  (dabai_dcw2.launch.py — folders 25-31 pattern)
    # --------------------------------------------------------
    camera = include_or_warn(
        "orbbec_camera", "launch/dabai_dcw2.launch.py", "Dabai_DCW2 camera",
        condition=IfCondition(LaunchConfiguration("use_camera")))
    if camera is not None:
        actions.append(camera)

    # --------------------------------------------------------
    # 3. ARM  (camera_arm_kin.launch.py pattern, folders 01/14/15/22/23)
    # --------------------------------------------------------
    arm_condition = IfCondition(LaunchConfiguration("use_arm"))
    kin_node = Node(
        package="arm_kin",
        executable="kin_srv",
        name="kin_ik_fk",                 # audited node name
        output="screen",
        condition=arm_condition,
    )
    actions.append(kin_node)

    arm_status = Node(
        package="arm_util",
        executable="arm_status",
        name="arm_status",                # from car_base.launch.py, folder 33
        output="screen",
        condition=arm_condition,
    )
    actions.append(arm_status)

    # --------------------------------------------------------
    # 4. NAV2  (navigation2.launch.py + yahboom_M3Pro.yaml, folder 17/18/19)
    # --------------------------------------------------------
    nav = include_or_warn(
        "M3Pro_navigation", "launch/navigation2.launch.py", "Nav2 stack",
        condition=IfCondition(LaunchConfiguration("use_nav")),
        # The audited launch file takes the map as "map" (folder 24 usage);
        # an argument-name mismatch only warns, it never crashes the launch.
        launch_arguments={"map": LaunchConfiguration("map")})
    if nav is not None:
        actions.append(nav)

    # --------------------------------------------------------
    # 5. TRANSFORMER TRACKER  (folder 33, optional)
    # --------------------------------------------------------
    tracker = include_or_warn(
        "smart_tracker", "launch/super_tracker.launch.py",
        "transformer tracker",
        condition=IfCondition(LaunchConfiguration("use_tracker")))
    if tracker is not None:
        actions.append(tracker)

    # --------------------------------------------------------
    # 6. RVIZ  (optional)
    # --------------------------------------------------------
    actions.append(Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="screen",
        condition=IfCondition(LaunchConfiguration("use_rviz")),
    ))

    # --------------------------------------------------------
    # 7. E-AIRA COGNITION LAYER
    # --------------------------------------------------------
    eira_common = {
        "parameters": [LaunchConfiguration("params_file")],
        "output": "screen",
        "emulate_tty": True,
    }

    actions.append(Node(
        package="eira_brain",
        executable="llm_task_planner",
        name="llm_task_planner",
        parameters=[*eira_common["parameters"],
                    {"waypoints_file": LaunchConfiguration("waypoints_file")}],
        output="screen",
        emulate_tty=True,
    ))

    actions.append(Node(
        package="eira_perception",
        executable="vision_manager",
        name="vision_manager",
        **eira_common,
    ))

    actions.append(Node(
        package="eira_manipulation",
        executable="grasp_executor",
        name="grasp_executor",
        **eira_common,
    ))

    return LaunchDescription(actions)
