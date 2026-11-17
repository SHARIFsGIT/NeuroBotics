# Jetson factory-image inventory

Audit date: 2026-11-17.

## 1. Status: partly complete, pending one read-only run on the Jetson

The Jetson could not be inspected during this audit:

- Tailscale listed the peer as **offline**.
- Ping and SSH to the address given timed out.
- This laptop holds no SSH key for the Jetson, so a login needs the password,
  which only you can type.

Each fact below is therefore labelled by its source:

| Label | Meaning |
|---|---|
| **Seen** | Read in this repository: exercise file copies, READMEs, scripts |
| **Public** | Checked against the upstream project or the ROS Humble apt index on 2026-11-17 |
| **Inferred** | Deduced from evidence, not observed directly |
| **Pending §N** | Answered by section N of the inventory script below |

## 2. How to complete the inventory

The script `jetson_inventory/jetson_readonly_inventory.sh` only reads. It uses
no `sudo`, writes no file and starts no ROS node. It never opens the serial
port or the camera, and never prints environment variables or secrets. Run it
from the laptop so that even its output file is written on the laptop:

```bash
cd ~/NeuroBotics/eira_ws/docs/audit/jetson_inventory
ssh jetson@<jetson-host> 'bash -s' < jetson_readonly_inventory.sh \
    > jetson_inventory_output.txt 2>&1
```

Optional extra, with the robot powered and the micro-ROS agent running: add
`EIRA_LIVE_GRAPH=1` to list which nodes publish and subscribe the robot topics.

```bash
ssh jetson@<jetson-host> 'EIRA_LIVE_GRAPH=1 bash -s' < jetson_readonly_inventory.sh \
    > jetson_inventory_output_live.txt 2>&1
```

That section publishes nothing and calls no service. The ROS command-line tool
does write its own log files under `~/.ros/log` on the Jetson; that is the
only write and the reason it is off by default.

The script was dry-run on this laptop. It produced 580 lines in all ten
sections, and a modification-time check found no file changed by the run.

| Script section | Collects |
|---|---|
| 1 | Module model, L4T/JetPack, kernel, CUDA/TensorRT packages, power mode, memory, disk |
| 2 | Python library versions (metadata only), OpenCV CUDA/ArUco support, PyTorch CUDA |
| 3 | Installed `ros-humble-*` packages relevant to the exercises |
| 4 | ROS lines of `~/.bashrc`: sourced workspaces, `ROS_DOMAIN_ID`, RMW |
| 5 | Serial, camera and joystick device names; USB devices; udev rules |
| 6 | Enabled services, desktop autostart entries, cron, Docker containers |
| 7 | Running ROS and robot processes |
| 8 | Ollama version and installed models |
| 9.1–9.4 | Every colcon workspace; every source package with version, build type, licence, git origin; installed packages without source; all packages outside `/opt/ros` |
| 9.5 | For each package the exercises use: install prefix, executables (script or compiled), share directory contents |
| 9.6 | Every message, service and action definition outside `/opt/ros` |
| 9.7–9.11 | Static TF launch, `common.yaml`, tag map, display launch, scan merger configuration, EKF and IMU filter configuration, Nav2 parameter key lines, real URDF joint table |
| 9.12 | Which source files mention `/scan0`, `/scan1`, `/imu/data_raw`, `arm6_joints` and similar topics, plus any LiDAR driver package |
| 9.13 | Key lines of `arm_kin`, `arm_util`, `calibration`, `yahboom_laser_filter`, `updatecostmap`, `yahboom_nav2_bringup` sources |
| 9.14 | Calibration, map and model files |
| 9.15 | Whether `~/eira_ws` exists on the Jetson, with per-file hashes to compare with the laptop |
| 10 | Optional live graph (off by default) |

## 3. Platform

| Item | Known | Label |
|---|---|---|
| Compute module | Jetson Orin NX (user). Memory size unknown (8 or 16 GB) | Pending §1 |
| OS, JetPack, L4T | Unknown | Pending §1 |
| ROS | ROS 2 Humble (every command uses `ros2`; scripts source `/opt/ros/humble/setup.bash`) | Seen |
| User and host | `jetson@yahboom` (prompt in README 02) | Seen |
| ROS domain | `ROS_DOMAIN_ID=30` in `start_agent.sh` and `joy.sh` | Seen; `~/.bashrc` pending §4 |
| Desktop session | Needed by `start_agent.sh` and `joy.sh` (`gnome-terminal`) and by the OpenCV, RViz and rqt windows | Seen |
| Docker | Yahboom paths under `/root/M3Pro_ws` (README 22, 23) suggest Docker or a root-user image appears in Yahboom's documentation | Inferred; pending §4, §6 |
| CUDA, cuDNN, TensorRT, PyTorch, Ultralytics versions | Unknown; TensorRT and PyTorch are used by exercise 32 | Pending §1, §2 |
| Ollama | Unknown (E-AIRA expects `phi3`) | Pending §8 |

## 4. Hardware and how it reaches ROS

| Component | Path to ROS | Evidence | Label |
|---|---|---|---|
| Controller board | Runs micro-ROS firmware. Linked to the Jetson over serial `/dev/myserial` at 2,000,000 baud through `micro_ros_agent` | `start_agent.sh`, `config_robot.py` | Seen |
| Firmware settings | Non-volatile, written by `config_robot.py`: car type, ROS domain ID, ROS namespace, odometry scale (line, angular), motor PID, IMU yaw PID, arm torque, arm offsets, arm mid-values (default `[2000, 2000, 2000, 2000, 1486, 3100]`), reboot, factory reset, firmware version | `config_robot.py` | Seen |
| Odometry scale in firmware | The copy in folder 04 writes line 1.0 and angular 1.05. Current firmware values have not been read; reading them needs the serial port with the agent stopped | `config_robot.py` main block | Seen (as written) |
| Mecanum base, encoders | Commands on `/cmd_vel`; odometry raw topic name unknown, fused by the EKF into `/odom` | exercise launch files | Inferred; pending §9.10, §10 |
| IMU | Raw topic `/imu/data_raw`, filtered to `/imu/data` | `gmapping.launch.py` remap; `cartographer_localization.launch.py` remap | Seen |
| Arm: 5 joints and a gripper on bus servos | `/arm6_joints` and `/arm_joint` (`arm_msgs`); no ROS node in the exercises subscribes, so the firmware is inferred to | exercise nodes | Inferred; pending §10 |
| Servo zero calibration | Stored by the controller, written by `calibrate_arm.py` | `calibrate_arm.py` | Seen |
| Buzzer, RGB light | `/beep` (`UInt16`), `rgb` (`ColorRGBA`) | exercise 02, 06, 13 nodes | Seen (topics) |
| Two 2D LiDARs | Raw `/scan0`, `/scan1`; merged into `/scan`. No exercise starts a LiDAR driver, so they probably come through the controller firmware | READMEs 09, 10; launch files 10–13 | Inferred; pending §9.12, §10 |
| RGB-D camera, Dabai DCW2 | USB; `orbbec_camera` driver; topics `/camera/color/image_raw`, `/camera/depth/image_raw`, `/camera/color/camera_info` | README 25, launch copies | Seen; driver build pending §9.5 |
| Gamepad receiver | USB; `joy_node` | README 02 | Seen |
| Udev rules | `/dev/myserial` symlink; Orbbec rules | — | Pending §5 |

## 5. Workspaces, scripts and files known from paths

| Location | Known content | Evidence | Label |
|---|---|---|---|
| `~/yahboomcar_ws` | `M3Pro_demo`, `arm_kin`, `yahboom_yolov8`, `slam_view` in `src/` | hard-coded paths in 01, 06, 21, 22, 23, 31, 32 | Seen; full list pending §9.2 |
| `~/M3Pro_ws` | `m3pro_bringup`, `M3Pro_navigation` in `src/` | README 24 paths; `joy.sh` sources it | Seen; full list pending §9.2 |
| `~/mircoROS_agent` | `micro_ros_agent` build (directory name spelt "mirco") | `start_agent.sh` | Seen |
| `~/joy_control` | `joy.sh`, `start_joy_controller.py` | README 02 | Seen |
| `~` | `start_agent.sh`, `calibrate_arm.py` and, by import, `config_robot.py` | README 01, 02 | Seen |
| `~/map` | SLAM Toolbox grid and pose graph | `save_slamtoolbox_map.launch.py` | Seen (path) |
| `~/MODELS/tracker` | `super_track_sim.onnx` | `super_tracker.launch.py` | Seen (path) |
| `/root/M3Pro_ws` | `yahboom_mapping/maps/yahboom_map.yaml` | README 22, 23 | Seen (path only) |
| `~/eira_ws` | E-AIRA deployment; version relative to the laptop unknown | earlier robot runs | Pending §9.15 |

## 6. Vendor ROS packages

Workspace is given where a path proves it. Source availability and licence
are pending §9.2 for every Yahboom package. Yahboom code carries no licence in
the copies kept here, so redistribution rights are unknown until the
`package.xml` licence fields are read.

### 6.1 Yahboom application packages

| Package | Role | Used in | Items referenced | Workspace |
|---|---|---|---|---|
| `M3Pro_demo` | Demonstration nodes | 01, 06, 14–16, 22, 23, 28, 29 | Nodes `arm_offset`, `follow_line`, `grasp_transport`, `apriltag_transport_V2`, `color_transport`, `estimate_volume`, `mediapipe_gesture`; launch `camera_arm_kin.launch.py`; modules `vutils`, `compute_joint5`, `Robot_Move`, `compute_pose`, `color_common`, `follow_common`, `media_library`; data `LineFollowHSV.text` | `~/yahboomcar_ws` |
| `M3Pro_navigation` | Navigation bring-up and parameters | 17–24 | Launch `base_bringup`, `navigation2`, `nav_rviz`, `cartographer_localization`, `rtab_bringup`, `toolbox_location_nav`, `bringup_mod`; params `yahboom_M3Pro.yaml`, `yahboom_M3Pro_carto.yaml`, `yahboom_M3Pro.lua`; `map/yahboom_map`; `rviz/nav2.rviz` | `~/M3Pro_ws` |
| `m3pro_bringup` | Newer whole-robot bring-up | 24, 33 | Launch `car_base`, `static_tf`, `dabai_dcw2` (own copy), `record_tag`, `apriltag_relocalization`, `super_tracker`; config `common.yaml`, `aritag_relocation.yaml`; RViz configurations | `~/M3Pro_ws` |
| `M3Pro` | Robot description | 10, 33; E-AIRA master launch | `urdf/m3pro.urdf`, meshes, `display.launch.py` | Pending |
| `yahboomcar_ctrl` | Teleoperation | 02, 03, 14–16, 20 | `yahboom_keyboard`, `yahboom_joy_M3Pro`, `yahboomcar_joy_launch.py` | Pending |
| `calibration` | Odometry calibration | 04, 05 | `calibrate_angular`, `calibrate_linear` | Pending |
| `patrol` | Patrol behaviour | 07 | `patrol` | Pending |
| `yahboom_M3Pro_laser` | LiDAR behaviours | 11–13, 32 | `laser_driver.launch.py`, `laser_Avoidance`, `laser_Tracker`, `laser_Warning`, module `common` | Pending |
| `yahboom_laser_filter` | Scan filter | 10; every base bring-up; E-AIRA master launch | `laser_filter_node`, launch file | Pending |
| `ekf_bringup` | Odometry fusion launch and parameters for `robot_localization` | every base bring-up; E-AIRA master launch | `ekf.launch.py`, configuration | Pending |
| `slam_mapping` | Mapping launch files and parameters | 14–16, 24 | `gmapping`, `bringup`, `cartographer`, `slam_toolbox`, `slam_view`, `save_map`, `save_slamtoolbox_map`, `online_async_launch`, `localization_launch`, `occupancy_grid_launch`; `config/lds_2d.lua`; RViz files | Pending |
| `slam_view` | RViz launch and configuration | 21–23 | `slam_view.launch.py`, `rviz/slam_rviz.rviz` | `~/yahboomcar_ws` |
| `yahboom_nav2_bringup` | Transport-demo helpers | 22, 23 | `rotation_detect_V2`, `get_nav2_status_V2` | Pending |
| `updatecostmap` | Costmap helper | 20, 21 | `update_costmap` (purpose unknown) | Pending |
| `apriltag_localization` | AprilTag relocalization | 24, 33 | `apriltag_recorder`, relocalization node, service `ControlDetection` | Pending |
| `yahboom_M3Pro_DepthCam` | Depth demos | 26, 27, 30 | `GetDepthColor`, `Measure_Distance`, `edge_detection` | Pending |
| `yahboom_yolov8` | YOLO demos | 31, 32 | `yolov8_detect`, `yolov8_track`, `yolov8_deep_track.launch.py`, `common`, `Robot_Move`, `tracker_trt`, weights `yolov8n.pt`, `yolov8s.trt` | `~/yahboomcar_ws` |
| `smart_tracker` | Transformer tracker | 33 | `super_tracker`, `pcl_segment`, ONNX model | Pending; source availability is the key question |
| `arm_kin` | Arm IK/FK service | 01, 22, 23, 28; E-AIRA grasp | `kin_srv` → `get_kinemarics`; `param/offset_value.yaml` | `~/yahboomcar_ws` |
| `arm_util` | Arm status | 33; E-AIRA master launch | `arm_status` → `/arm_status/arm_joint` | Pending; whether it reports measured angles is a key question |
| `yahboom_mapping` | Maps | 22, 23 (path only) | `maps/yahboom_map.yaml` | `/root/M3Pro_ws` (documentation path) |

### 6.2 Yahboom interface packages

| Package | Definitions (fields as used in code) | Who needs it | Label |
|---|---|---|---|
| `arm_msgs` | `ArmJoints` (`joint1`…`joint6`, `time`); `ArmJoint` (`id`, `joint`, `time`) | Every arm command; the controller firmware (inferred); E-AIRA manipulation, bring-up, simulation | Seen (usage); definitions pending §9.6 |
| `arm_interface` | `AprilTagInfo` (`id`, `x`, `y`, `z`); `CurJoints` (`joints`); service `ArmKinemarics` (`kin_name`, `tar_x/y/z`, `roll/pitch/yaw`, `cur_joint1…5` → `joint1…`, `x/y/z`, `roll/pitch/yaw`) | Vendor demos; E-AIRA grasp executor | Seen (usage); pending §9.6 |
| `apriltag_localization` | Service `ControlDetection` (`command`) | Exercise 24 | Seen (usage); pending §9.6 |

### 6.3 Third-party packages built from source

None of these is in the Humble apt repository.

| Package | Used for | Upstream facts | Label |
|---|---|---|---|
| `micro_ros_agent` (+ `micro_ros_msgs`, Micro XRCE-DDS Agent) | Hardware bridge | micro-ROS-Agent `humble` branch, version 3.0.6, Apache-2.0 | Public; local version pending §9.2 |
| `ira_laser_tools` (ROS 2 port) | Merging the two scans | Upstream is ROS 1 only (branches `kinetic`, `ros1-master`; version 1.0.7, BSD). The robot's copy is a port of unknown origin, modified to include `M3Pro/display.launch.py` | Public + Seen; origin pending §9.2 |
| `slam_gmapping`, `openslam_gmapping` | Exercise 14 | ROS 2 port of unknown origin | Pending §9.2 |
| `orbbec_camera` (+ `orbbec_camera_msgs`) | Camera driver | OrbbecSDK_ROS2, Apache-2.0. Branch `main` = v1 (1.5.22); branch `v2-main` = v2 (2.10.7, also in Humble apt). Both branches ship `dabai_dcw2.launch.py` | Public; which one the robot uses is pending §9.2, §9.7 |
| `imu_filter_madgwick` | IMU filtering | In Humble apt (2.1.6, licence GPL-3.0-or-later); the robot may use a vendor copy | Public; pending §9.5 |

## 7. ROS 2 apt packages used by the exercises

Versions are the candidates in the laptop's Humble apt index on 2026-11-17.
Licences are from upstream `package.xml` files or installed copies.

| Package | Candidate version | Licence | Used in |
|---|---|---|---|
| `navigation2`, `nav2_bringup`, `nav2_map_server` | 1.1.20 | Apache-2.0 | 14–24 |
| `slam_toolbox` | 2.6.10 | LGPL | 16, 24 |
| `cartographer_ros` | 2.0.9002 | Apache-2.0 | 15, 19 |
| `rtabmap_ros`, `rtabmap_launch` | 0.23.13 | BSD | 20, 21 |
| `robot_localization` | 3.5.5 | Apache-2.0 | EKF (via `ekf_bringup`) |
| `imu_filter_madgwick` | 2.1.6 | GPL-3.0-or-later | base bring-up |
| `laser_filters` | 2.0.9 | BSD | candidate replacement for `yahboom_laser_filter` |
| `orbbec_camera` | 2.10.7 | Apache-2.0 | candidate replacement for the factory camera build |
| `apriltag`, `apriltag_ros` | 3.4.5, 3.4.0 | upstream AprilTag library BSD-2-Clause | candidate replacement for `apriltag_localization` |
| `tf_transformations` | 1.1.1 | not checked | 01, 22, 23, 28 |
| `joy`, `teleop_twist_joy`, `teleop_twist_keyboard` | 3.3.0, 2.4.8, 2.4.1 | BSD | 02, 03 |
| `rviz2`, `rqt_graph`, `rqt_reconfigure`, `rqt_image_view` | 11.2.29, 1.3.2, 1.1.4, 1.2.0 | BSD (rqt_reconfigure BSD/Apache-2.0) | diagnostics |
| `robot_state_publisher`, `joint_state_publisher`, `xacro` | 3.0.3, 2.4.0, 2.1.1 | BSD | robot model |
| `rosbridge_server` | 2.0.8 | not checked | E-AIRA option |

Not in apt: `micro_ros_agent`, `ira_laser_tools`, `slam_gmapping`.

## 8. Python libraries imported by the exercise code

Versions on the Jetson are pending §2.

| Library | Used in | Licence (where checked) |
|---|---|---|
| `ultralytics` | 31, 32; E-AIRA perception | AGPL-3.0 (upstream LICENSE) |
| `torch`, `tensorrt` | 32 | NVIDIA Jetson builds; not checked |
| `mediapipe` | 29 (through `M3Pro_demo.media_library`); E-AIRA gestures | Apache-2.0 (upstream LICENSE) |
| `dt_apriltags` | 01, 06, 22, 23, 28 | wraps the AprilTag library (BSD-2-Clause) |
| `transforms3d`, `tf_transformations` | 01, 22, 23, 28 | not checked |
| `PyQt5` | 02 (`start_joy_controller.py`) | GPL v3 (laptop metadata) |
| `psutil`, `colorama`, `numpy` | 02, 24, many | BSD (laptop metadata) |
| `pyserial` | 01, 04, 05 (`config_robot.py`) | not checked |
| `cv2`, `cv_bridge`, `message_filters`, `yaml` | most | OpenCV Apache-2.0 (4.5+); ROS packages BSD/Apache |

## 9. Calibration, map and model data on the robot

| Artifact | Location | Produced by | Needed by E-AIRA | Label |
|---|---|---|---|---|
| Hand-eye offsets | `~/yahboomcar_ws/src/arm_kin/param/offset_value.yaml` | 01 #5 | Yes, or re-measure | Seen (path); values pending §9.14 |
| Servo zero calibration | Controller and servos | 01 #2 | Yes (implicit in every arm command) | Seen |
| Odometry scale, motor and IMU PID, arm mid-values | Controller firmware | 04, 05, `config_robot.py` | Yes (implicit in odometry and arm accuracy) | Seen (tool); current values unread |
| Line HSV thresholds | `M3Pro_demo/M3Pro_demo/LineFollowHSV.text` | 06 | No | Seen (path) |
| Occupancy grid `yahboom_map` | `M3Pro_navigation/map/` | 14–16 (K9) | Only if the arena is unchanged | Seen (path) |
| SLAM Toolbox grid and pose graph | `~/map/` | 24 | Only if the arena is unchanged | Seen (path) |
| Cartographer state | `~/yahboom_map.pbstream` | 15, 19 | No | Seen (path) |
| RTAB-Map database | `~/.ros/rtabmap.db`, `~/rtabmap.db` | 20, 21 | No | Seen (path) |
| AprilTag map | `m3pro_bringup/config/aritag_relocation.yaml` | 24 | Optional | Seen (path) |
| YOLO weights | `yahboom_yolov8/.../weights/yolov8n.pt`, `yolov8s.trt` | vendor | E-AIRA default points here today; to be replaced | Seen (path) |
| Tracker model | `~/MODELS/tracker/super_track_sim.onnx` | vendor | Only if `smart_tracker` is kept | Seen (path) |
| Shared parameters | `m3pro_bringup/config/common.yaml` | vendor; edited in 24 | To be read | Pending §9.7 |

## 10. Questions the script answers

1. Which workspaces exist, and which packages does each contain? (§9.1–9.3)
2. Is Yahboom source present for every package, or are some binary-only?
   This matters especially for `smart_tracker`, `arm_kin` and `arm_util`. (§9.2, §9.5)
3. What licence does each vendor `package.xml` declare? (§9.2)
4. Exact `arm_msgs` and `arm_interface` definitions. (§9.6)
5. Is there a LiDAR driver on the Jetson, or do scans come from the firmware? (§9.12; §10)
6. Does `arm_status` report measured servo angles? (§9.13; §10)
7. Is `imu_filter_madgwick` the apt package or a modified copy? Is `nav2_bringup` modified? (§9.5)
8. Which Orbbec driver version is installed? (§9.2, §9.7)
9. The real URDF, static transforms and Nav2/EKF parameters. (§9.7–9.11)
10. Are the agent or the joystick started at boot? (§6)
11. Is the E-AIRA copy on the Jetson the same as the laptop's? (§9.15)
