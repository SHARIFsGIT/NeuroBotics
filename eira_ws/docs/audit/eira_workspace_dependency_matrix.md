# E-AIRA workspace dependency matrix

Audit date: 2026-11-17. Built from every `package.xml`, the Python imports
of all production modules (tests excluded), package lookups in launch and
Python code, and the topic, service and action names in the source. The
current state is described; nothing was changed.

Kind codes:

| Code | Meaning |
|---|---|
| ROS-APT | ROS 2 Humble apt package |
| SYS-APT | Ubuntu apt package |
| PIP | Python wheel installed with pip |
| JETPACK | NVIDIA platform software |
| YB-IF | Yahboom interface package |
| YB-APP | Yahboom application package or file |
| HW-DRV | Driver or firmware |
| SERVICE | A running program E-AIRA talks to |
| USER | The user's own work outside `eira_ws` |

## 1. Dependencies between E-AIRA packages

```mermaid
flowchart BT
    brain[eira_brain<br/>shared console and planner modules]
    perception[eira_perception] --> brain
    manipulation[eira_manipulation] --> brain
    evaluation[eira_evaluation] --> brain
    bringup[eira_bringup] --> brain
    bringup -. launches .-> perception
    bringup -. launches .-> manipulation
    bringup -. launches .-> evaluation
    simulation[eira_simulation] --> brain
    simulation --> perception
    simulation -. includes master launch .-> bringup
    brain -. reads waypoints.yaml at run time .-> bringup
```

Solid arrows are Python imports; dotted arrows are launch-time or file
lookups. The import graph has no cycles. Two loose ends:

- `eira_brain` falls back to reading `eira_bringup/config/waypoints.yaml`,
  a run-time dependency in the opposite direction.
- Two `eira_brain` test files import `eira_manipulation` and
  `eira_perception` without declaring them.

## 2. External dependencies, package by package

"Declared" means listed in `package.xml`. "Clean Jetson" says how the item
would be obtained on a Jetson without the factory workspaces.

### `eira_brain`

| Dependency | Declared | Used for | Kind | Clean Jetson |
|---|---|---|---|---|
| `rclpy`, `rcl_interfaces`, `std_msgs`, `geometry_msgs`, `sensor_msgs`, `action_msgs`, `tf2_ros`, `cv_bridge`, `ament_index_python` | yes | Nodes | ROS-APT | apt |
| `nav2_msgs` | yes (`depend`) | `NavigateThroughPoses` client; import guarded | ROS-APT | apt (`navigation2`) |
| `ros2bag`, `rosbag2_transport`, `rosbag2_storage_default_plugins` | yes (`exec_depend`) | `mission_recorder` runs `ros2 bag record` | ROS-APT | apt |
| `python3-numpy`, `python3-opencv`, `python3-yaml` | yes | general; `cv2.aruco` for relocalization | SYS-APT | apt |
| `whisper`, `sounddevice` | **no** | `voice_activation` (optional) | PIP (+ PortAudio, FFmpeg) | pip; no rosdep key |
| `espeak` executable | **no** | spoken status (`tts_enabled` default true) | SYS-APT | apt `espeak` |
| Ollama server and model | — | planning | SERVICE | Ollama installer |
| `navigate_through_poses`, `/amcl_pose`, `/initialpose` | — | navigation and localization checks | ROS-APT (Nav2) | apt; parameters must come from E-AIRA |
| `beep` (`UInt16`) | — | buzzer | HW-DRV (firmware topic) | through the agent |

### `eira_perception`

| Dependency | Declared | Used for | Kind | Clean Jetson |
|---|---|---|---|---|
| `rclpy`, `rcl_interfaces`, `sensor_msgs`, `std_msgs`, `geometry_msgs`, `cv_bridge`, `message_filters`, `tf2_ros`, `tf2_geometry_msgs` | yes | `vision_manager` | ROS-APT | apt |
| `python3-numpy`, `python3-opencv` | yes | image processing | SYS-APT | apt |
| `ultralytics` | yes, as `python3-ultralytics`, a key `rosdep` cannot resolve | detection and tracking | PIP (AGPL-3.0) | pip, pinned |
| PyTorch with CUDA | **no** | required by Ultralytics on the GPU | JETPACK | NVIDIA wheel for the installed JetPack |
| `mediapipe` | **no** | `gesture_node` (optional) | PIP | ARM64 build needed |
| Default `model_path` `/home/jetson/yahboomcar_ws/src/yahboom_yolov8/.../yolov8n.pt` | — | weights | **YB-APP (factory path)** | to be replaced by an E-AIRA model directory |
| Default `transformer_model_path` `~/MODELS/tracker/super_track_sim.onnx` | — | transformer backend | **YB-APP data** | to be replaced or removed |
| `/camera/color/image_raw`, `/camera/depth/image_raw`, `/camera/color/camera_info`, `/camera/depth/camera_info` | — | input | HW-DRV (Orbbec driver) | system driver |
| TF from `camera_color_optical_frame` to `base_link` | — | 3D target pose | robot description + driver | `eira_description` after migration |

### `eira_manipulation`

| Dependency | Declared | Used for | Kind | Clean Jetson |
|---|---|---|---|---|
| `rclpy`, `std_msgs`, `geometry_msgs`, `tf2_ros`, `tf2_geometry_msgs` | yes | node | ROS-APT | apt |
| `arm_msgs` (`ArmJoints`, `ArmJoint`) | yes | servo commands on `arm6_joints`, `arm_joint` | **YB-IF**, consumed by the firmware (inferred) | `vendor_compat/arm_msgs` after migration |
| `arm_interface` (`ArmKinemarics`, `CurJoints`) | yes | IK service client; joint feedback | **YB-IF** | dropped once E-AIRA has its own IK |
| Service `get_kinemarics` | — | inverse kinematics | **YB-APP** (`arm_kin/kin_srv`) | E-AIRA IK after migration |
| Topic `Curjoints` | — | joint feedback | unknown publisher (vendor demo nodes publish it) | to be decided after the inventory |
| `python3-transforms3d`, `python3-tf-transformations` | yes | **not imported** | SYS-APT / ROS-APT | unused; the second key does not resolve in `rosdep` |
| `beep`, `grasp_done`, `cmd_vel` (remapped to the gate) | — | buzzer, vendor completion flag, alignment | firmware / vendor convention / E-AIRA gate | — |

### `eira_bringup`

| Dependency | Declared | Used for | Kind | Clean Jetson |
|---|---|---|---|---|
| `ament_index_python`, `rclpy`, `geometry_msgs`, `sensor_msgs`, `std_msgs`, `visualization_msgs`, `tf2_ros`, `cv_bridge`, `launch`, `launch_ros` | yes | nodes and launch | ROS-APT | apt |
| `robot_state_publisher`, `joint_state_publisher`, `xacro`, `rviz2` | yes | robot model, display | ROS-APT | apt |
| `nav2_bringup`, `nav2_controller`, `nav2_smoother`, `nav2_planner`, `nav2_behaviors`, `nav2_bt_navigator`, `nav2_waypoint_follower`, `nav2_velocity_smoother`, `nav2_lifecycle_manager` | yes | navigation | ROS-APT | apt |
| `imu_filter_madgwick` | yes | master launch includes its `imu_filter.launch.py` | ROS-APT (GPL-3.0) or factory copy | apt |
| `rosbridge_server` | yes (but optional at run time) | mobile commands | ROS-APT | apt |
| `orbbec_camera` | yes | master launch includes `dabai_dcw2.launch.py` | HW-DRV | apt or pinned source |
| `arm_msgs` | yes | `arm_state_relay` | **YB-IF** | `vendor_compat/arm_msgs` |
| `arm_kin` | yes | starts `kin_srv` | **YB-APP** | E-AIRA IK |
| `arm_util` | yes | starts `arm_status` | **YB-APP** | E-AIRA joint-state source |
| `ira_laser_tools` | yes | merger node and `config/laserscan_merge.yaml` | **3P-SRC (factory build)** | vendored port or E-AIRA merger |
| `yahboom_laser_filter` | yes | scan filter launch | **YB-APP** | apt `laser_filters` with E-AIRA configuration |
| `ekf_bringup` | yes | EKF launch | **YB-APP** | apt `robot_localization` with E-AIRA configuration |
| `M3Pro` | yes | `urdf/m3pro.urdf` | **YB-APP** | `eira_description` |
| `m3pro_bringup` | yes | `launch/static_tf.launch.py`, `config/common.yaml` | **YB-APP** | E-AIRA bring-up |
| `M3Pro_navigation` | yes | default Nav2 `param/yahboom_M3Pro.yaml` | **YB-APP** | E-AIRA Nav2 parameters |
| `joy` | **no** | joystick profile | ROS-APT | apt |
| Profiles: `M3Pro_demo`, `yahboomcar_ctrl`, `calibration`, `slam_mapping`, `rtabmap_launch`, `nav2_map_server`, `neurobotics` | **no** | `exercise_profiles.launch.py` | YB-APP, ROS-APT, USER | optional factory-profiles launch, or removed |
| Default `map` argument `~/map/map.yaml` | — | AMCL map | output location of exercise 24 | E-AIRA data directory |
| `/JoyState`, `/scan`, colour image | — | `exercise_skills` | factory joystick node; scan pipeline; driver | E-AIRA teleop flag |

### `eira_evaluation`

| Dependency | Declared | Used for | Kind | Clean Jetson |
|---|---|---|---|---|
| `rclpy`, `std_msgs`, `geometry_msgs` | yes | nodes | ROS-APT | apt |
| `python3-matplotlib` | yes | charts | SYS-APT | apt |
| Results directory `~/eira_ws/results` | — | output | — | E-AIRA data directory |

No factory dependency.

### `eira_simulation`

| Dependency | Declared | Used for | Kind | Clean Jetson / laptop |
|---|---|---|---|---|
| `rclpy`, `ament_index_python`, `launch`, `launch_ros`, `sensor_msgs`, `std_msgs`, `geometry_msgs`, `trajectory_msgs`, `gazebo_msgs`, `tf2_ros`, `cv_bridge` | yes | nodes | ROS-APT | apt |
| `gazebo_ros`, `gazebo_plugins`, `robot_state_publisher`, `xacro`, `nav2_bringup`, `dwb_core`, `dwb_plugins`, `dwb_critics`, `nav2_navfn_planner` | yes | Gazebo Classic and Nav2 | ROS-APT | apt |
| `arm_msgs`, `arm_interface` | yes | emulates the vendor arm contracts | **YB-IF** | `vendor_compat/arm_msgs`; `ArmKinemarics` emulation replaced by E-AIRA's IK interface |
| Robot model | — | URDF lookup: installed `M3Pro`, then `neurobotics`, then `08. robot model/neurobotics_ws/...` in this repository | **YB-APP**, USER, path outside `eira_ws` | `eira_description` |
| Gazebo Classic 11 | — | simulator | SYS-APT | apt |

## 3. Declaration problems

| Package | Problem | Effect on a clean install |
|---|---|---|
| `eira_brain` | `whisper`, `sounddevice`, `espeak` used but not declared | Optional voice and speech silently unavailable |
| `eira_brain` | Tests import `eira_manipulation` and `eira_perception`, not declared as `test_depend` | Works only from the source tree |
| `eira_perception` | `python3-ultralytics` has no `rosdep` rule; PyTorch not declared; `mediapipe` not declared | `rosdep install` errors; the GPU stack must be installed by hand |
| `eira_manipulation` | `python3-transforms3d`, `python3-tf-transformations` declared, never imported; the second key does not resolve | Needless installs; `rosdep` error |
| `eira_bringup` | Nine factory packages declared as `exec_depend` (`arm_msgs`, `arm_kin`, `arm_util`, `ira_laser_tools`, `yahboom_laser_filter`, `ekf_bringup`, `M3Pro_navigation`, `M3Pro`, `m3pro_bringup`) | `rosdep install` fails on a clean Jetson |
| `eira_bringup` | `joy` used by a profile, not declared | Joystick profile fails without notice |
| all | Maintainer e-mail `example.com`; no `LICENSE` file although `package.xml` says MIT | Packaging metadata incomplete |

`ament_python` builds do not check run dependencies. That is why all six
packages build on this laptop although Nav2 and the vendor packages are
missing.

## 4. Interfaces that cross the E-AIRA boundary

| Interface | Type | Direction | Other party today | Owner after migration |
|---|---|---|---|---|
| `/cmd_vel` | `geometry_msgs/Twist` | out (from the velocity gate) | controller firmware via the agent | system driver; unchanged |
| `/arm6_joints`, `/arm_joint` | `arm_msgs/ArmJoints`, `ArmJoint` | out | controller firmware (inferred) | `vendor_compat/arm_msgs` |
| `/beep` | `std_msgs/UInt16` | out | controller firmware | unchanged |
| `/scan` | `sensor_msgs/LaserScan` | in | factory merger and filter | E-AIRA scan pipeline |
| `/odom`, TF `odom → base_footprint` | `nav_msgs/Odometry`, TF | in | factory EKF configuration | E-AIRA EKF configuration |
| Robot TF | TF | in | `robot_state_publisher` with the factory URDF; factory static TF | `eira_description` |
| `/camera/...` | `sensor_msgs/Image`, `CameraInfo` | in | Orbbec driver | system driver |
| `get_kinemarics` | `arm_interface/srv/ArmKinemarics` | client | `arm_kin` | E-AIRA IK |
| `Curjoints` | `arm_interface/CurJoints` | in | unknown | decided after the inventory |
| `/arm_status/arm_joint` | `sensor_msgs/JointState` (factory) | in (through `joint_state_publisher` when the relay is off) | `arm_util/arm_status` | E-AIRA joint-state source |
| `navigate_through_poses`, `/amcl_pose`, `/initialpose` | Nav2 action and messages | both | Nav2 (apt) with factory parameters | Nav2 (apt) with E-AIRA parameters |
| `/JoyState` | `std_msgs/Bool` | in | factory joystick node | E-AIRA teleop flag |
| `grasp_done` | `std_msgs/Bool` | out | vendor convention; no E-AIRA consumer | keep or drop |

## 5. Factory dependencies per package, now and after migration

| Package | Now | After the migration plan |
|---|---|---|
| `eira_brain` | none (only firmware topics) | none |
| `eira_perception` | two default file paths into factory locations | none |
| `eira_manipulation` | `arm_msgs`, `arm_interface`, `arm_kin` service | `vendor_compat/arm_msgs` only |
| `eira_bringup` | nine packages in the master launch and `package.xml`; eight more through profiles | none in the master launch; profiles optional and separate |
| `eira_evaluation` | none | none |
| `eira_simulation` | `arm_msgs`, `arm_interface`, factory URDF lookup, folder-08 path | `vendor_compat/arm_msgs`, `eira_description` |
