# Existing work audit

Audit date: 2026-11-17. Workspace: `~/NeuroBotics`. Read-only.

## 1. Method and evidence standard

Every file outside generated build output was listed. Launch files, scripts and
the six `eira_ws` packages were read; interfaces were extracted by search
across all sources. The `eira_ws` test suite, lint and an out-of-tree build were
run. Nothing was started on a ROS graph.

Each capability below carries an evidence level. A higher level is claimed
only when the repository contains the evidence.

| Level | Meaning |
|---|---|
| E0 | Named in a prompt or document only |
| E1 | Source read; logic and interfaces inspected |
| E2 | Unit-tested with mocks on the development laptop |
| E3 | Run end to end in simulation, result recorded |
| E4 | Run on the robot, result recorded in the repository |
| E4u | Reported by the user as run successfully on the robot; no output recorded |

**No capability in this workspace reaches E3 or E4.** On 2026-11-17 you
reported that all 33 exercises ran successfully on the robot (level E4u). You
also reported that E-AIRA was tested on the robot only in part. No outputs,
logs, maps or measurements from either were saved in the repository.

## 2. The machine the audit ran on

| Item | Value |
|---|---|
| Host | x86_64 laptop, Ubuntu 22.04.5, RTX 3060; **not the Jetson** |
| ROS | Humble installed, 347 packages |
| Present | Gazebo Classic, `ros_gz`, `ros2_control`, `robot_localization`, `cv_bridge`, `launch_testing`, OpenCV 4.5.4, NumPy 1.21.5 |
| Absent | **Nav2** (no `nav2_*`), SLAM Toolbox, Cartographer, RTAB-Map, all Yahboom packages, `arm_msgs`, `arm_interface`, Orbbec driver, Ultralytics, PyTorch, MediaPipe, Ollama |

Consequence: on this laptop only pure-Python logic can be exercised. Nav2
action clients, the arm IK service, the camera and the detector cannot be run
here, in simulation or otherwise, until Nav2 and the vendor interface packages
are installed.

## 3. Workspace inventory

| Path | Content | Tracked in Git |
|---|---|---|
| `01. …` to `33. …` | 33 exercise folders: copies of vendor launch files and scripts with learning comments, plus short command-list READMEs | Yes |
| `01`–`13` `*.html` | One self-contained Bangla code-walkthrough page per exercise (learning aid, unrelated to the robot runtime) | Yes |
| `08. robot model/neurobotics_ws/` | A separate Gazebo Classic workspace, package `neurobotics`: URDF, meshes, differential-drive simulation, teleop and calibration scripts | Source yes; `build/` and `install/` also present on disk |
| `eira_ws/` | The E-AIRA workspace: 6 packages, 10 documents | 37 files tracked; 106 untracked |
| `refine-kit/`, `Code analysis prompt.md` | Tooling and prompt for the HTML walkthrough pages | Yes |
| `log/` | A stray `colcon test-result` log directory from 2026-11-13 | No |
| `.vscode/`, `.claude/` | Editor and assistant settings | Partly |

Outside the VS Code workspace, for completeness:

- `~/neurobotics_ws` — an older copy of the folder-08 simulation workspace.
- `~/ros2_ws` — a 2024–2025 course workspace (`mobile_robotics_engineer`, nine
  packages on mapping, sensing, planning). Not referenced by E-AIRA. It was not
  audited; say so if it should be included.

There are **no numbered exercises after 33**. The only post-33 work is
`eira_ws` and a "city autopilot" extension of folder 08 (see §9).

## 4. What the exercise folders are

They are not ROS packages. Each folder holds a few files copied from packages
installed on the robot, annotated line by line for study.

| Measure | Count |
|---|---|
| Launch files | 57 (31 distinct by content) |
| Python nodes and scripts | 34 (28 distinct) |
| Vendor `package.xml`, `setup.py`, `CMakeLists.txt` | 0 |
| Vendor `.msg`, `.srv`, `.action` definitions | 0 |
| Vendor YAML, Lua, RViz, map, calibration files | 0 |
| Model weights | 0 |

The only buildable package among the exercises is `neurobotics` in folder 08.

### Duplicated files

The same file appears in several folders with identical content:

| File | Folders |
|---|---|
| `camera_arm_kin.launch.py` | 01, 14, 15, 22, 23 (28 has a reformatted variant) |
| `base_bringup.launch.py` | 17, 18, 19, 22, 23 |
| `navigation2.launch.py`, `nav_rviz.launch.py` | 17, 18, 19 |
| `dabai_dcw2.launch.py` | 25, 26, 27, 29, 30, 31 |
| `yahboom_keyboard.py` | 03, 14, 15, 16 |
| `laser_driver.launch.py` | 11, 12, 13 |
| `save_map.launch.py`, `slam_view.launch.py` | 14, 15, 16 |
| `grasp_transport.py`, `slam_view.launch.py` (variant) | 22, 23 |
| `follow_line.py` | 06, 15 (14 has a different variant) |
| `config_robot.py` | 04, 05 |
| `rtab_bringup.launch.py` | 20, 21 |
| `slam_toolbox.launch.py` | 16, 24 |
| `start_agent.sh` | 01, 24 |

Folders 17 and 18 are byte-identical apart from the README: single-goal and
multi-goal navigation use the same launch files and differ only in how goals
are given in RViz.

## 5. Robot-side software the sources depend on

None of these is in the workspace. They are named in launch files, imports or
hard-coded paths. Their workspaces, licences and source availability are
confirmed by the Jetson inventory (`jetson_factory_image_inventory.md`, still
pending). Each README command is traced in
`exercise_factory_dependency_mapping.md`.

| Package or module | Used for | Seen in |
|---|---|---|
| `micro_ros_agent` (`~/mircoROS_agent`) | Serial bridge to the motor/arm controller: `/dev/myserial`, 2,000,000 baud, `ROS_DOMAIN_ID=30` | 01, 24 |
| `M3Pro` | Robot description `urdf/m3pro.urdf`, `display.launch.py` | 10, 33 |
| `m3pro_bringup` | `car_base.launch.py`, `static_tf.launch.py`, `dabai_dcw2.launch.py`, `apriltag_relocalization.launch.py`, `config/common.yaml`, `config/aritag_relocation.yaml` | 24, 33 |
| `M3Pro_navigation` | Nav2 parameters `param/yahboom_M3Pro.yaml`, Cartographer `yahboom_M3Pro.lua`, map, `bringup_mod.launch.py` | 17–19, 24 |
| `M3Pro_demo` | `arm_offset`, `follow_line`, `grasp_transport`, `apriltag_transport_V2`, `color_transport`, `estimate_volume`, `mediapipe_gesture`; helper modules `vutils`, `compute_joint5`, `Robot_Move`, `compute_pose`, `color_common`, `media_library` | 01, 06, 22, 23, 28, 29 |
| `arm_kin` | `kin_srv` node offering service `get_kinemarics`; `param/offset_value.yaml` | 01, 22, 23, 28 |
| `arm_msgs`, `arm_interface` | `ArmJoints`, `ArmJoint`, `CurJoints`, `AprilTagInfo`, `ArmKinemarics` | 01–03, 06, 22, 23, 28–30, 32 |
| `arm_util` | `arm_status` node | 33 |
| `yahboomcar_ctrl` | Keyboard and joystick teleoperation | 02, 03 |
| `calibration`, `patrol` | Velocity calibration, patrol | 04, 05, 07 |
| `ira_laser_tools`, `yahboom_laser_filter`, `yahboom_M3Pro_laser` | Dual-scan merge, filter, LiDAR behaviours | 10–13 |
| `imu_filter_madgwick`, `ekf_bringup` | IMU filter and odometry fusion | 04, 07, 14–21 |
| `slam_gmapping`, `cartographer_ros`, `slam_mapping`, `rtabmap_launch` | Mapping and localization | 14–16, 19–21, 24 |
| `nav2_bringup`, `nav2_map_server` | Navigation | 14–19, 21, 24 |
| `apriltag_localization` | `apriltag_recorder`, service `/control_detection` | 24 |
| `yahboom_nav2_bringup` | `rotation_detect_V2`, `get_nav2_status_V2` | 22, 23 |
| `orbbec_camera` | Dabai DCW2 driver | 25–31 |
| `yahboom_M3Pro_DepthCam` | Depth demos | 26, 27, 30 |
| `yahboom_yolov8` | YOLOv8 nodes, `Robot_Move`, `common`, weights `yolov8n.pt`, `yolov8s.trt`; `tracker_trt` | 31, 32 |
| `smart_tracker` | `super_tracker`, `pcl_segment`; model `~/MODELS/tracker/super_track_sim.onnx` | 33 |
| `dt_apriltags`, `transforms3d`, `tf_transformations`, `ultralytics`, `torch`, TensorRT | Python libraries | several |

Robot paths appearing in sources: `/home/jetson/yahboomcar_ws`,
`/home/jetson/M3Pro_ws`, `/root/M3Pro_ws`, `/home/jetson/mircoROS_agent`,
`~/map`, `/home/jetson/yahboom_map.pbstream`, `/home/jetson/rtabmap.db`.

## 6. Hardware facts established from source

| Fact | Evidence |
|---|---|
| Low-level control is a micro-ROS node on a microcontroller, bridged by `micro_ros_agent` over serial | `01/start_agent.sh` |
| Tools in 04/05 also talk to the controller directly over `/dev/myserial` | `04/config_robot.py` |
| Two 2D LiDARs, `laser0_frame` rear-left and `laser1_frame` front-right, merged into `/scan`. No exercise starts a LiDAR driver, so the raw scans probably arrive through the controller board (to be confirmed) | folder-08 URDF; `10/merge_multi.launch.py`; raw topics `/scan0`, `/scan1` |
| The controller firmware keeps non-volatile settings written over serial by `config_robot.py`: ROS domain ID, namespace, odometry scale (line, angular), motor and IMU-yaw PID, arm mid-values and offsets | `04/config_robot.py` |
| The RGB-D camera link `DCW2` is fixed to arm link `arm4` | folder-08 URDF joint `DCW2_Joint` |
| The arm has five revolute joints (`arm1_Joint`…`arm5_Joint`) and one gripper servo; servo 6 is the gripper | folder-08 URDF; `22/grasp_transport.py` sets `joints[5]` to open/close angles |
| Servo commands are degrees, 0–180, with a duration in milliseconds | `ArmJoints.joint1..6`, `.time` usage |
| Mecanum base; vendor nodes command `linear.x`, `linear.y`, `angular.z` | `22/apriltag_transport_V2.py::pubVel` |
| Base frame `base_footprint`, coincident with `base_link`; odometry frame `odom` | folder-08 URDF; `04`, `07` launch parameters |
| Camera launch defaults: colour 640×480 at 30 fps MJPG, depth 640×400 at 10 fps, `depth_registration` **false** | `25/dabai_dcw2.launch.py` |
| Vendor grasping does not use TF. It deprojects a pixel with a hard-coded intrinsic matrix, applies a hard-coded end-effector-to-camera matrix, calls forward kinematics, then adds offsets from `offset_value.yaml` | `22/grasp_transport.py` lines 88–100, 299–349 |
| The offsets in `offset_value.yaml` are produced by exercise 01 (`arm_offset.py`) against an AprilTag at a known position | `01/arm_offset.py` lines 243–255 |

The folder-08 URDF is named `M3Pro` and carries the vendor CAD meshes, so it is
very likely derived from the real `m3pro.urdf`. It was modified for Gazebo
(differential-drive controller, plugins), so the real file must still be read
on the robot before any frame is relied on.

## 7. Vendor interface catalogue (inferred from call sites)

Message and service field lists come from how the code uses them. The
definition files have not been seen.

| Interface | Type | Direction in vendor code |
|---|---|---|
| `/cmd_vel` | `geometry_msgs/Twist` | Published by teleop, behaviours, transport nodes |
| `/scan0`, `/scan1`, `/scan` | `sensor_msgs/LaserScan` | Raw and merged scans |
| `/imu/data_raw`, `/imu/data` | `sensor_msgs/Imu` | Into and out of the Madgwick filter |
| `/odom` | `nav_msgs/Odometry` | From the EKF |
| `/camera/color/image_raw`, `/camera/depth/image_raw` | `sensor_msgs/Image` | Camera driver |
| `/camera/color/camera_info` | `sensor_msgs/CameraInfo` | Subscribed by 23 and 28; 01 and 22 use only a hard-coded intrinsic matrix |
| `arm6_joints` | `arm_msgs/ArmJoints` (`joint1..joint6`, `time`) | All six servos |
| `arm_joint` | `arm_msgs/ArmJoint` (`id`, `joint`, `time`) | One servo |
| `Curjoints` | `arm_interface/CurJoints` (`joints[]`) | **Published by the demo nodes themselves with their commanded pose**; not shown to be encoder feedback |
| `PosInfo` | `arm_interface/AprilTagInfo` (`id`, `x`, `y`, `z`) | Pixel u, v and depth in metres, from detector node to grasp node |
| `set_joint5`, `set_joint6` | `std_msgs/Int16` | Wrist and gripper hints |
| `grasp_done`, `/unload_done` | `std_msgs/Bool` | Hand-shakes between nodes |
| `/beep` | `std_msgs/UInt16` | Buzzer |
| `/JoyState` | `std_msgs/Bool` | Joystick takeover flag; behaviours pause when true |
| `get_kinemarics` | `arm_interface/srv/ArmKinemarics` (`kin_name` = `ik` or `fk`; `tar_x/y/z`, `roll/pitch/yaw`, `cur_joint1..5` → `joint1..`, `x/y/z`, `roll/pitch/yaw`) | IK and FK |
| `/control_detection` | `apriltag_localization/srv/ControlDetection` (`command` 0, 1, 2) | AprilTag relocalization control |
| `navigate_through_poses` | `nav2_msgs/action/NavigateThroughPoses` | Imported by `22/apriltag_transport_V2.py` |
| `/goal_pose`, `/initialpose` | `PoseStamped`, `PoseWithCovarianceStamped` | Navigation goals and origin capture |
| `/start_detect`, `/start_transport`, `/transport_done`, `/rotation_done`, `/start_rotate`, `/next_status`, `/back_orin`, `/No_found`, `/detect_result` | `Bool` / `Int16` | Flag topics that sequence the vendor transport demo |
| `detect_image` | `sensor_msgs/Image` | Annotated YOLO output |
| `/tracker_id` | `std_msgs/Int16` | Track selection in exercise 32 |

The vendor demos are sequenced by flag topics and by key presses in an OpenCV
window (`cv2.waitKey`). They need a display and an operator, and they have no
timeouts, cancellation or failure reporting. That is the gap an orchestration
layer fills.

## 8. `eira_ws` inventory

| Package | Source lines | Tests | Executables |
|---|---:|---:|---|
| `eira_brain` | 5,315 | 302 | `llm_task_planner`, `eira_cli`, `velocity_gate`, `safety_monitor`, `waypoint_recorder`, `visual_relocalization`, `voice_input`/`voice_activation`, `mission_recorder`, `mission_replayer`, `mission_reporter` |
| `eira_perception` | 2,274 | 146 | `vision_manager`, `gesture_recognizer` |
| `eira_manipulation` | 972 | 48 | `grasp_executor` |
| `eira_bringup` | 1,969 | 89 | `arm_state_relay`, `edge_monitor`, `exercise_skills`, `visualization_markers`; launch `eira_master`, `exercise_profiles` |
| `eira_evaluation` | 1,429 | 37 | `mission_logger`, `metrics_calculator`, `benchmark` |
| `eira_simulation` | 1,513 | 44 | `sim_arm_bridge`, `sim_depth_noise`, `sim_perception_oracle`; launch `sim_bringup` |

All six are `ament_python`. There is no interface package: every E-AIRA
contract is a JSON string in `std_msgs/String`.

Configuration: `eira_bringup/config/eira_params.yaml` (all node parameters),
`waypoints.yaml` (example poses, not measured), two empty calibration
templates, one RViz preset. Simulation adds its own Nav2 parameters, two
behaviour trees, a world and a map.

Documents in `eira_ws/docs/`: ten files, about 3,000 lines of operator and
testing guidance plus a 321 kB Bangla guide. They describe procedures and
expected results. They do not record results obtained on the robot.

### What each core node does today

- **`llm_task_planner`** (1,546 lines). Takes text on `/eira/command`, asks
  Ollama (`phi3`) for a JSON array over a closed vocabulary — `navigate`,
  `find`, `grasp`, `release`, `home`, `speak`, `stop` — with the prompt listing
  the loaded waypoint names, detector classes and colours. The reply is parsed,
  validated as a whole, repaired once, and otherwise replaced by a rule-based
  parser. A 10 Hz state machine then executes the plan with per-action
  timeouts, retries, a rotate-and-scan recovery, mission and action IDs, and a
  FIFO queue. Navigation uses the `NavigateThroughPoses` action; everything
  else is JSON over topics.
- **`vision_manager`** (1,124 lines). Runs Ultralytics `track` on demand, picks
  the requested class (and optionally dominant colour), takes the median depth
  in a window at the box centre, deprojects with live `CameraInfo`, transforms
  to `base_link` with TF and publishes `/target_pose`.
- **`grasp_executor`** (782 lines). Aligns the base to a stand-off distance
  with two PID loops, converts the target to the arm frame, calls the vendor IK
  service, maps the result to servo angles using the vendor's formulae, and
  runs an open–reach–close–carry sequence.
- **`velocity_gate`, `safety_monitor`**. One node owns `/cmd_vel`; sources
  publish on `/eira/cmd_vel/<source>` and are forwarded only while they hold a
  fresh lease and the planner's heartbeat is alive.

## 9. Status of each capability

| Capability | State | Evidence | Note |
|---|---|---|---|
| Vendor teleop, calibration, LiDAR behaviours, mapping, navigation, AprilTag and colour transport, depth demos, YOLO demos | Vendor code; ran successfully on the robot per your report | E1, E4u | Source read; no run record in the repository |
| Vendor transformer tracker (33) | Black box; ran on the robot per your report | E0–E1, E4u | Only launch files present |
| LLM plan generation and validation | Implemented | E2 | Never run against a real model on this laptop (no Ollama); no record from the Jetson |
| Rule-based fallback planner | Implemented | E2 | |
| Mission state machine, retries, queue, stop | Implemented | E2 | An earlier revision was smoke-run on this laptop against stub nodes (session notes only; nothing saved in the repository). The current uncommitted revision has no such run |
| Nav2 goal dispatch | Implemented | E2 | Nav2 absent here; action server mocked |
| Detection, depth fusion, pose publication | Implemented | E2 | Detector and camera mocked |
| Transformer tracking backend | Adapter only | E1 | Falls back to YOLO unless a compatible model or factory is supplied |
| Base alignment and grasp sequence | Implemented | E2 | Arm frame is unset by default, so a grasp stops with "arm frame unavailable" until calibrated |
| Grasp verification | Not implemented | — | Events always report `object_contact_verified: false` |
| Velocity gate and watchdog | Implemented | E2 | Bypassed by any node that publishes `/cmd_vel` directly |
| ArUco relocalization | Implemented | E2 | New code; marker map template is empty |
| Voice (Whisper), gestures (MediaPipe), rosbridge, floor-edge monitor | Implemented, optional, off by default | E2 | Dependencies absent here |
| Evaluation logger, metrics, benchmark runner | Implemented | E2 | Only synthetic data so far |
| Gazebo simulation | Implemented | E2 | Not runnable here: needs Nav2 and the vendor interface packages |
| Folder-08 `neurobotics` simulation | Built on this laptop | E1 | Differential drive; separate from E-AIRA |
| Folder-08 city autopilot (`autopilot.py`, `traffic.py`, `city.launch.py`, `city_street.world`) | **Source missing** | — | Only `.pyc` files and four dangling install symlinks remain |

E-AIRA as a whole has been tested on the robot only in part (your report) and
has not been validated end to end. An exercise working on its own does not
mean its E-AIRA counterpart has been integrated or tested. Per-exercise
status is in `factory_independence_assessment.md` §9.

## 10. Checks run during the audit

| Claim in `eira_ws/README.md` | Observed on 2026-11-17 |
|---|---|
| "612 passing tests" | 666 passed, 0 failed, 0 skipped |
| "flake8 checks pass" | 34 findings, all style: 13 in production code (11 long lines in `eira_brain`, 2 in `vision_manager.py`) and 21 in three test files (17 F811 fixture-name redefinitions, 2 E128, 2 long lines) |
| "clean isolated six-package build" | Confirmed. Note that `ament_python` does not check run dependencies at build time, so this passes without Nav2 or the vendor packages |

All tests construct nodes with mocks, many through `object.__new__` so that
`__init__` and ROS wiring are skipped. No test calls `rclpy.init`, spins a
node, or uses `launch_testing`. They verify logic, not integration.

## 11. Git state

- Branch `main`, in sync with `origin/main` at commit `9aa820d` (2026-11-13).
- 31 modified tracked files: +5,310 / −2,845 lines.
- 106 untracked files in `eira_ws`, about 16,000 lines of Python, including
  the whole of `eira_evaluation` and `eira_simulation`, all of `docs/`, and
  most tests.
- `eira_ws/build`, `install`, `log` are ignored correctly. The repository root
  has no ignore rule for the stray `log/` directory or `.pytest_cache/`.
- No `LICENSE` file, although every `package.xml` declares MIT. Maintainer
  e-mail is a placeholder.
- No continuous integration.
