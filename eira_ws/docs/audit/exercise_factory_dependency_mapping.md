# Exercise factory-dependency mapping (01–33)

Audit date: 2026-11-17. Read-only analysis; no exercise file was changed.

## 1. Scope and evidence

Every line of every exercise `README.md` is listed below: 140 non-blank lines
from 31 README files. Folders 05 and 08 have no README; their contents are
described in their own rows. The README text is quoted exactly as recorded.
The two very long RTAB-Map commands are shortened in the table and given in
full in Appendix A.

According to the user (2026-11-17), all 33 exercises were run successfully on
the robot through Remmina. This repository holds no logs or outputs from those
runs, so that report is the only evidence of success.

"Actual Dependency" was traced from the copies of vendor files kept in each
exercise folder: launch includes, Python imports, topic names and hard-coded
paths. The Jetson was offline during the audit (see
`jetson_factory_image_inventory.md`). For each vendor package, the workspace
it lives in, its licence and whether its source is present will be confirmed
from the inventory script output.

## 2. Legend

**Dependency type**

| Code | Meaning |
|---|---|
| HW-DRV | Hardware driver or firmware: controller-board firmware, micro-ROS agent, camera driver, device names |
| YB-IF | Yahboom interface package: message or service definitions |
| YB-APP | Yahboom application package, launch file or script in the factory workspaces or home directory |
| YB-CFG | Yahboom configuration or data file: calibration, map, parameters, model weights |
| 3P-SRC | Third-party open-source package built from source in a factory workspace (not in the Humble apt repository) |
| ROS-APT | ROS 2 Humble package installable from the apt repository (verified on the laptop's Humble apt index, 2026-11-17) |
| SYS | Operating system or Python library outside ROS |
| USER | The user's own work in this repository |

**Required by E-AIRA?**

| Value | Meaning |
|---|---|
| Yes – core | The fetch pipeline cannot run without it |
| Yes – prerequisite | Needed once to calibrate or map; the result is reused |
| Optional | Useful for safety, operation or diagnosis; not on the critical path |
| No | Not needed by E-AIRA |

**Proposed action**

| Value | Meaning |
|---|---|
| Retain – system driver | Stays installed outside `eira_ws`, documented and version-pinned; E-AIRA only starts and configures it |
| Retain – maintenance tool | Vendor tool that writes firmware or servo settings; used rarely, never at E-AIRA run time |
| Install – apt | Standard Humble package, declared as an E-AIRA dependency |
| Recreate | E-AIRA-owned launch file, configuration or node in `eira_ws`; the vendor file serves only as reference and test oracle |
| Recreate – interface-compatible | E-AIRA-maintained message definitions with the same package and type names, needed so the firmware can be talked to |
| Capture data | Copy a calibration, map or model value into E-AIRA configuration with its origin noted, or re-measure it |
| Not required | Exercise stays as a historical reference only |

**Shared dependencies** (cited by key in the table)

| Key | What the command actually runs | Paths and packages involved | Type |
|---|---|---|---|
| K1 AGENT | `start_agent.sh`: waits 5 s, opens a `gnome-terminal`, sets `ROS_DOMAIN_ID=30`, sources `/opt/ros/humble/setup.bash` and `/home/jetson/mircoROS_agent/install/setup.bash`, runs `ros2 run micro_ros_agent micro_ros_agent serial --dev /dev/myserial -b 2000000`. The agent bridges the controller board, which runs micro-ROS firmware, to ROS 2 | `~/start_agent.sh`; workspace `~/mircoROS_agent`; device `/dev/myserial` (udev symlink); desktop session for `gnome-terminal` | HW-DRV |
| K2 ARM-TOPIC | Publishes `arm_msgs/msg/ArmJoints` (`joint1`…`joint6` in degrees, `time` in ms) on `/arm6_joints`. No exercise node subscribes to it, so the subscriber is inferred to be the controller firmware through K1. **Moves the arm** | `arm_msgs` in a factory workspace | YB-IF, HW-DRV |
| K3 CAM-KIN | `M3Pro_demo/camera_arm_kin.launch.py`: includes `orbbec_camera/launch/dabai_dcw2.launch.py` and starts `arm_kin/kin_srv` named `kin_ik_fk`, which serves `get_kinemarics` (IK and FK) | `M3Pro_demo`, `arm_kin` under `/home/jetson/yahboomcar_ws/src` (paths in 01, 06, 22) | YB-APP, HW-DRV |
| K4 CAM | `orbbec_camera/dabai_dcw2.launch.py`: Orbbec driver. Defaults in the copy kept in folder 25: colour 640×480 at 30 fps MJPG, depth 640×400 at 10 fps, `depth_registration` false, point clouds on | Workspace unknown. Upstream OrbbecSDK_ROS2 is Apache-2.0; `ros-humble-orbbec-camera` 2.10.7 is in apt, and its source branch ships `dabai_dcw2.launch.py` | HW-DRV |
| K5 BASE | `M3Pro_navigation/base_bringup.launch.py` includes four things. (1) `imu_filter_madgwick/imu_filter.launch.py`. (2) `ira_laser_tools/merge_multi.launch.py`, which includes `M3Pro/display.launch.py` and runs `laserscan_multi_merger` with `ira_laser_tools/config/laserscan_merge.yaml`. (3) `yahboom_laser_filter/laser_filter_node.launch.py` (angles −180…180). (4) `ekf_bringup/ekf.launch.py`. It also defines an `update_costmap` node but never starts it | `M3Pro_navigation` under `~/M3Pro_ws/src` (README 24); the other packages are in unknown workspaces | YB-APP, 3P-SRC, ROS-APT |
| K6 LASER | `yahboom_M3Pro_laser/laser_driver.launch.py`: includes the merger and the filter only. It starts no device driver | `yahboom_M3Pro_laser` | YB-APP |
| K7 KEYB | `yahboomcar_ctrl/yahboom_keyboard`: keyboard teleoperation publishing `cmd_vel`, `arm_joint` and `arm6_joints` | `yahboomcar_ctrl` | YB-APP |
| K8 SLAMVIEW | `slam_mapping/slam_view.launch.py`: RViz with `slam_mapping/rviz/slam_rviz.rviz` | `slam_mapping` | YB-APP |
| K9 SAVEMAP | `slam_mapping/save_map.launch.py`: `nav2_map_server/map_saver_cli -f <M3Pro_navigation share>/map/yahboom_map --free 0.196 --occ 0.65`. Writes into the factory package | `slam_mapping`, `M3Pro_navigation`, `nav2_map_server` | YB-APP, ROS-APT |
| K10 FOLLOW | `M3Pro_demo/follow_line`: HSV line following using `/scan1`, depth and `/JoyState`; publishes `/cmd_vel` and `/beep`. Reads `/home/jetson/yahboomcar_ws/src/M3Pro_demo/M3Pro_demo/LineFollowHSV.text` | `M3Pro_demo` (+ `follow_common`, `vutils`, `compute_joint5`), `dt_apriltags` | YB-APP, YB-CFG |
| K11 NAV2 | `M3Pro_navigation/navigation2.launch.py`: `nav2_bringup/bringup_launch.py` with map `M3Pro_navigation/map/yahboom_map.yaml` and parameters `M3Pro_navigation/param/yahboom_M3Pro.yaml`. Starts AMCL, map server and the Nav2 servers | `M3Pro_navigation`; `nav2_bringup` (apt) | YB-APP, YB-CFG, ROS-APT |
| K12 NAVRVIZ | `M3Pro_navigation/nav_rviz.launch.py`: RViz with `M3Pro_navigation/rviz/nav2.rviz` | `M3Pro_navigation` | YB-APP |
| K13 RTABBASE | `M3Pro_navigation/rtab_bringup.launch.py`: IMU filter, scan merger and filter, EKF, camera (K4), `updatecostmap/update_costmap`, and a static transform `base_link → camera_link` at (0.05, 0, 0.38) | `M3Pro_navigation`, `updatecostmap` | YB-APP |
| K14 TOOLS | `rviz2`, `rqt_graph`, `rqt_reconfigure`, `rqt_image_view`, `ros2 topic …` | `/opt/ros/humble` | ROS-APT |

## 3. Command table

| Exercise | Command / Operation | Purpose | Actual Dependency | Dependency Type | Required by E-AIRA? | Proposed Action |
|---|---|---|---|---|---|---|
| 01 #1 | `ros2 topic pub /arm6_joints arm_msgs/msg/ArmJoints {"joint1: 90, joint2: 90, joint3: 90, joint4: 90, joint5: 90, joint6: 180, time: 1500"} --once` | Move all servos to the calibration pose over 1.5 s | K2 | YB-IF, HW-DRV | Yes – core (E-AIRA commands the arm on this topic and type) | Recreate – interface-compatible `arm_msgs`; firmware retained |
| 01 #2 | `python3 ~/calibrate_arm.py` | Servo zero calibration: torque off, operator holds the pose, writes each servo's offset to the controller (`set_arm_calib_offset`) | `~/calibrate_arm.py` + `config_robot.py` (`MicroROS_Robot`, own serial protocol at 2 Mbaud on `/dev/myserial`; the agent must be stopped). The confirmation test `adjust == 'y' or 'Y'` is always true | YB-APP writing firmware settings | Yes – prerequisite (done) | Retain – maintenance tool |
| 01 #3 | `sh start_agent.sh` | Start the hardware bridge | K1 | HW-DRV | Yes – core | Retain – system driver; E-AIRA starts it without a desktop terminal |
| 01 #4 | `ros2 launch M3Pro_demo camera_arm_kin.launch.py` | Camera and IK service | K3 | YB-APP, HW-DRV | Yes – core | Recreate the launch (E-AIRA master launch already does this) and, later, the IK service; camera per K4 |
| 01 #5 | `ros2 run M3Pro_demo arm_offset` | Hand-eye offset calibration against an AprilTag at a known position; on SPACE writes `x/y/z_offset` | `M3Pro_demo/arm_offset` (+ `vutils`, `compute_joint5`, `Robot_Move`), `dt_apriltags`, `transforms3d`, `tf_transformations`, FK service, OpenCV window. Writes `/home/jetson/yahboomcar_ws/src/arm_kin/param/offset_value.yaml` | YB-APP, YB-CFG | Yes – prerequisite (target accuracy) | Capture data (current offsets); Recreate as an E-AIRA calibration tool that writes E-AIRA configuration |
| 02 #1 | `jetson@yahboom:~$ bash ~/start_agent.sh` | Start the hardware bridge | K1 | HW-DRV | Yes – core | Retain – system driver |
| 02 #2 | `jetson@yahboom:~$ bash ~/joy_control/joy.sh` | After 10 s: sources ROS, `/home/jetson/yahboomcar_ws/install/setup.bash` and `/home/jetson/M3Pro_ws/install/setup.bash`, sets `ROS_DOMAIN_ID=30`, opens `gnome-terminal` running `~/joy_control/start_joy_controller.py`. That PyQt5 window starts the next two commands as subprocesses | `~/joy_control/` scripts, PyQt5, psutil, both factory workspaces, desktop session | YB-APP | Optional (manual control) | Recreate – headless E-AIRA teleop launch |
| 02 #3 | `ros2 launch yahboomcar_ctrl yahboomcar_joy_launch.py` | Start `joy_node` | `yahboomcar_ctrl` launch file; `joy` | YB-APP, ROS-APT | Optional | Install – apt (`joy`); launch recreated |
| 02 #4 | `ros2 run yahboomcar_ctrl yahboom_joy_M3Pro` | Gamepad → `cmd_vel`, `arm_joint`, `arm6_joints`, `/beep`, `rgb`, `JoyState`. Also publishes `move_base/cancel`, a ROS 1 name with no effect on Nav2 | `yahboomcar_ctrl`, `arm_msgs`, `actionlib_msgs` | YB-APP | Optional (safety: manual takeover) | Recreate – `teleop_twist_joy` (apt) into the E-AIRA velocity gate, plus the takeover flag |
| 03 #1 | `sh start_agent.sh` | Start the hardware bridge | K1 | HW-DRV | Yes – core | Retain – system driver |
| 03 #2 | `ros2 run yahboomcar_ctrl yahboom_keyboard` | Keyboard drive and arm jog | K7 | YB-APP | Optional (driving while mapping) | Install – apt `teleop_twist_keyboard` through the gate; arm keys not needed |
| 03 #3 | `ros2 run rqt_graph rqt_graph` | Inspect the node graph | K14 | ROS-APT | Optional (diagnostic) | Install – apt |
| 03 #4 | `ros2 topic echo /cmd_vel` | Watch velocity commands | K14 | ROS-APT | Optional (diagnostic) | Install – apt |
| 03 #5 | `ros2 topic info /cmd_vel` | Count publishers and subscribers | K14 | ROS-APT | Optional (diagnostic) | Install – apt |
| 04 #1 | `sh start_agent.sh` | Start the hardware bridge | K1 | HW-DRV | Yes – core | Retain – system driver |
| 04 #2 | `ros2 launch calibration calibrate_angular.launch.py` | IMU filter + EKF + `calibration/calibrate_angular` (frames `base_footprint`, `odom`): turns the robot and compares odometry with the commanded angle. **Moves the base** | `calibration`, `ekf_bringup`, `imu_filter_madgwick` launch file (apt or factory copy: unknown) | YB-APP, ROS-APT | Yes – prerequisite (odometry scale; done) | Capture data (the result is stored in firmware, see next row); recreate the routine only if re-calibration is needed |
| 04 #3 | `ros2 run rqt_reconfigure rqt_reconfigure` | Tune the calibration node's parameters live | K14 | ROS-APT | Optional | Install – apt |
| 04 (folder file, not a README command) | `config_robot.py` | Writes odometry scale factors to the controller's non-volatile settings and reboots it. The copy here writes line 1.0 and angular 1.05. The same tool sets domain ID, namespace, motor and IMU-yaw PID, arm mid-values and arm offsets | Serial protocol on `/dev/myserial` (agent stopped) | YB-APP writing firmware settings | Yes – prerequisite (values live in firmware) | Retain – maintenance tool; read back the current values later, with approval |
| 05 (no README.md) | Folder holds `calibrate_linear.launch.py` and `config_robot.py` | Same as 04 with `calibration/calibrate_linear` (drives straight). The commands used were not recorded | `calibration`, `ekf_bringup`, `imu_filter_madgwick` | YB-APP | Yes – prerequisite (done) | Capture data (firmware value); not recreated now |
| 06 #1 | `sh start_agent.sh` | Start the hardware bridge | K1 | HW-DRV | Yes – core | Retain – system driver |
| 06 #2 | `ros2 launch M3Pro_demo camera_arm_kin.launch.py` | Camera and IK service | K3 | YB-APP, HW-DRV | Yes – core | Recreate (see 01 #4) |
| 06 #3 | `ros2 run M3Pro_demo follow_line` | Line following | K10 | YB-APP, YB-CFG | No | Not required (a frozen re-implementation exists in `exercise_skills`) |
| 06 #4 | `ros2 topic pub /arm6_joints arm_msgs/msg/ArmJoints {"joint1: 90, joint2: 90, joint3: 20, joint4: 0, joint5: 90, joint6: 180, time: 1500"} --once` | Tilt the camera toward the floor | K2 | YB-IF, HW-DRV | Yes – core (topic and type) | Recreate – interface-compatible |
| 06 #5 | `ros2 run rqt_graph rqt_graph` | Inspect the graph | K14 | ROS-APT | Optional (diagnostic) | Install – apt |
| 07 #1 | `sh start_agent.sh` | Start the hardware bridge | K1 | HW-DRV | Yes – core | Retain – system driver |
| 07 #2 | `ros2 launch patrol patrol.launch.py` | IMU filter + EKF + `patrol/patrol` patrol behaviour. **Moves the base.** The node's source is not in the folder | `patrol`, `imu_filter_madgwick`, `ekf_bringup` | YB-APP | No | Not required |
| 07 #3 | `ros2 run rqt_reconfigure rqt_reconfigure` | Tune patrol parameters | K14 | ROS-APT | Optional | Install – apt |
| 07 #4 | `ros2 run rqt_graph rqt_graph` | Inspect the graph | K14 | ROS-APT | Optional (diagnostic) | Install – apt |
| 08 (no README.md) | Folder holds the user's own Gazebo workspace `neurobotics_ws` | Laptop simulation built from the vendor URDF and meshes, converted to differential drive. On the robot, the vendor model is loaded by `M3Pro/display.launch.py` (included by `merge_multi.launch.py`) and by `car_base.launch.py`; no command for it was recorded | `neurobotics` (own package); vendor `M3Pro` package with `urdf/m3pro.urdf` and meshes | USER, YB-APP | Yes – core (robot description and TF) | Recreate – `eira_description` from the real `m3pro.urdf`; mesh redistribution needs a licence decision |
| 09 #1 | `ros2 topic echo /scan0` | Show LiDAR 0's raw scan | No exercise file starts a LiDAR driver, so `/scan0` is inferred to come from the controller firmware through K1. To be confirmed with the inventory's optional live-graph section | HW-DRV | Yes – core | Retain – system driver |
| 09 #2 | `rviz2` | Visualise | K14 | ROS-APT | Optional | Install – apt |
| 10 #1 | `sh start_agent.sh` | Start the hardware bridge | K1 | HW-DRV | Yes – core | Retain – system driver |
| 10 #2 | `ros2 launch ira_laser_tools merge_multi.launch.py` | Merge `/scan0` and `/scan1` into `/scan`; also starts the robot model display | `ira_laser_tools` ROS 2 port with `config/laserscan_merge.yaml`; `M3Pro/display.launch.py`. Upstream ira_laser_tools is BSD and ROS 1 only (branches `kinetic`, `ros1-master`); not in Humble apt | 3P-SRC, YB-APP, YB-CFG | Yes – core (Nav2 needs one merged scan) | Recreate launch and configuration; for the merger node, either vendor the BSD port as third-party code or write an E-AIRA merger |
| 10 #3 | `rviz2` | Visualise | K14 | ROS-APT | Optional | Install – apt |
| 10 #4 | `ros2 launch yahboom_laser_filter laser_filter_node.launch.py` | Scan filter with angle limits −180…180 | `yahboom_laser_filter` | YB-APP | Yes – core (scan pipeline) | Recreate – apt `laser_filters` angular-bounds filter, once the vendor node's topic names and behaviour are read on the Jetson |
| 10 #5 | `rviz2` | Visualise | K14 | ROS-APT | Optional | Install – apt |
| 10 #6 | `ros2 run rqt_graph rqt_graph` | Inspect the graph | K14 | ROS-APT | Optional (diagnostic) | Install – apt |
| 11 #1 | `sh start_agent.sh` | Start the hardware bridge | K1 | HW-DRV | Yes – core | Retain – system driver |
| 11 #2 | `ros2 launch yahboom_M3Pro_laser laser_driver.launch.py` | Scan merge and filter | K6 | YB-APP | Yes – core (same pipeline as 10) | Recreate (as 10) |
| 11 #3 | `ros2 run yahboom_M3Pro_laser laser_Avoidance` | Reactive avoidance on `/scan` → `/cmd_vel`; pauses on `/JoyState`. **Moves the base** | `yahboom_M3Pro_laser` (+ `common`) | YB-APP | No | Not required (frozen variant in `exercise_skills`) |
| 12 #1 | `sh start_agent.sh` | Start the hardware bridge | K1 | HW-DRV | Yes – core | Retain – system driver |
| 12 #2 | `ros2 launch yahboom_M3Pro_laser laser_driver.launch.py` | Scan merge and filter | K6 | YB-APP | Yes – core | Recreate (as 10) |
| 12 #3 | `ros2 run yahboom_M3Pro_laser laser_Tracker` | Follow the nearest object at a set distance. **Moves the base** | `yahboom_M3Pro_laser` | YB-APP | No | Not required (frozen variant exists) |
| 13 #1 | `sh start_agent.sh` | Start the hardware bridge | K1 | HW-DRV | Yes – core | Retain – system driver |
| 13 #2 | `ros2 launch yahboom_M3Pro_laser laser_driver.launch.py` | Scan merge and filter | K6 | YB-APP | Yes – core | Recreate (as 10) |
| 13 #3 | `ros2 run yahboom_M3Pro_laser laser_Warning` | Turn toward the nearest object and beep. **Moves the base** | `yahboom_M3Pro_laser` | YB-APP | No | Not required (frozen variant exists) |
| 14 #1 | `sh start_agent.sh` | Start the hardware bridge | K1 | HW-DRV | Yes – core | Retain – system driver |
| 14 #2 | `ros2 launch slam_mapping gmapping.launch.py` | Scan merge and filter, IMU filter (remap `/imu`→`/imu/data_raw`), EKF, GMapping | `slam_mapping`; `slam_gmapping` (ROS 2 port, not in Humble apt; origin unknown) | YB-APP, 3P-SRC | No (one mapping method suffices) | Not required |
| 14 #3 | `ros2 launch slam_mapping slam_view.launch.py` | Mapping view | K8 | YB-APP | Optional | Recreate (RViz configuration) |
| 14 #4 | `ros2 run yahboomcar_ctrl yahboom_keyboard` | Drive while mapping | K7 | YB-APP | Optional | Install – apt `teleop_twist_keyboard` |
| 14 #5 | `ros2 launch M3Pro_demo camera_arm_kin.launch.py` | Camera for line following during mapping | K3 | YB-APP, HW-DRV | No (for mapping) | Not required for mapping |
| 14 #6 | `ros2 run M3Pro_demo follow_line` | Drive autonomously along a line while mapping. Folder 14 holds a variant of this node that differs from 06 | K10 | YB-APP, YB-CFG | No | Not required |
| 14 #7 | `ros2 topic pub /arm6_joints arm_msgs/msg/ArmJoints {"joint1: 90, joint2: 140, joint3: 20, joint4: 10, joint5: 90, joint6: 180, time: 1500"} --once` | Arm parking pose while mapping. E-AIRA's `init_joints` is the same pose | K2 | YB-IF, HW-DRV | Yes – core | Recreate – interface-compatible (pose already in `eira_params.yaml`) |
| 14 #8 | `ros2 launch slam_mapping save_map.launch.py` | Save the occupancy grid | K9 | YB-APP, ROS-APT | Yes – prerequisite (map files) | Recreate – save into an E-AIRA maps directory |
| 15 #1 | `sh start_agent.sh` | Start the hardware bridge | K1 | HW-DRV | Yes – core | Retain – system driver |
| 15 #2 | `ros2 launch slam_mapping bringup.launch.py` | IMU filter, scan merge and filter, EKF | `slam_mapping`, `imu_filter_madgwick`, `ira_laser_tools`, `yahboom_laser_filter`, `ekf_bringup` | YB-APP, 3P-SRC | Yes – core (base pipeline) | Recreate (E-AIRA base bring-up) |
| 15 #3 | `ros2 launch slam_mapping cartographer.launch.py` | Cartographer with `slam_mapping/config/lds_2d.lua` and `occupancy_grid_launch.py` | `cartographer_ros` (apt, Apache-2.0); `slam_mapping` configuration | ROS-APT, YB-CFG | No (unless Cartographer is chosen) | Not required |
| 15 #4 | `ros2 launch slam_mapping slam_view.launch.py` | Mapping view | K8 | YB-APP | Optional | Recreate (RViz configuration) |
| 15 #5 | `ros2 run yahboomcar_ctrl yahboom_keyboard` | Drive while mapping | K7 | YB-APP | Optional | Install – apt `teleop_twist_keyboard` |
| 15 #6 | `ros2 launch M3Pro_demo camera_arm_kin.launch.py` | Camera for line following | K3 | YB-APP, HW-DRV | No (for mapping) | Not required for mapping |
| 15 #7 | `ros2 run M3Pro_demo follow_line` | Line-following drive while mapping | K10 | YB-APP, YB-CFG | No | Not required |
| 15 #8 | `ros2 topic pub /arm6_joints arm_msgs/msg/ArmJoints {"joint1: 90, joint2: 140, joint3: 20, joint4: 10, joint5: 90, joint6: 180, time: 1500"} --once` | Arm parking pose | K2 | YB-IF, HW-DRV | Yes – core | Recreate – interface-compatible |
| 15 #9 | `ros2 launch slam_mapping save_map.launch.py` | Save the occupancy grid | K9 | YB-APP, ROS-APT | Yes – prerequisite | Recreate |
| 16 #1 | `sh start_agent.sh` | Start the hardware bridge | K1 | HW-DRV | Yes – core | Retain – system driver |
| 16 #2 | `ros2 launch slam_mapping slam_toolbox.launch.py` | Scan merge and filter, IMU filter, EKF, SLAM Toolbox through `slam_mapping/launch/online_async_launch.py` with Yahboom parameters, RViz `slam_toolbox_rviz.rviz` | `slam_mapping` launch and parameters; `slam_toolbox` (apt, LGPL) | YB-APP, YB-CFG, ROS-APT | Yes – prerequisite (map for navigation and for 24) | Recreate – E-AIRA mapping launch on apt `slam_toolbox`, with parameters copied once and then owned by E-AIRA |
| 16 #3 | `ros2 launch slam_mapping slam_view.launch.py` | Mapping view | K8 | YB-APP | Optional | Recreate (RViz configuration) |
| 16 #4 | `ros2 run yahboomcar_ctrl yahboom_keyboard` | Drive while mapping | K7 | YB-APP | Optional | Install – apt `teleop_twist_keyboard` |
| 16 #5 | `ros2 launch M3Pro_demo camera_arm_kin.launch.py` | Camera for line following | K3 | YB-APP, HW-DRV | No (for mapping) | Not required for mapping |
| 16 #6 | `ros2 run M3Pro_demo follow_line` | Line-following drive while mapping | K10 | YB-APP, YB-CFG | No | Not required |
| 16 #7 | `ros2 topic pub /arm6_joints arm_msgs/msg/ArmJoints {"joint1: 90, joint2: 140, joint3: 20, joint4: 10, joint5: 90, joint6: 180, time: 1500"} --once` | Arm parking pose | K2 | YB-IF, HW-DRV | Yes – core | Recreate – interface-compatible |
| 16 #8 | `ros2 launch slam_mapping save_map.launch.py` | Save the occupancy grid | K9 | YB-APP, ROS-APT | Yes – prerequisite | Recreate |
| 17 #1 | `sh start_agent.sh` | Start the hardware bridge | K1 | HW-DRV | Yes – core | Retain – system driver |
| 17 #2 | `ros2 launch M3Pro_navigation base_bringup.launch.py` | IMU filter, scan merge and filter, EKF | K5 | YB-APP, 3P-SRC, ROS-APT | Yes – core | Recreate – E-AIRA base bring-up (the master launch still calls these vendor packages today) |
| 17 #3 | `ros2 launch M3Pro_navigation navigation2.launch.py` | Nav2 with AMCL on the saved map | K11 | YB-APP, YB-CFG, ROS-APT | Yes – core | Recreate – E-AIRA Nav2 launch (exists) with a parameter file copied from `yahboom_M3Pro.yaml`, owned and annotated by E-AIRA; Nav2 from apt |
| 17 #4 | `ros2 launch M3Pro_navigation nav_rviz.launch.py` | Navigation view | K12 | YB-APP | Optional | Recreate (RViz configuration) |
| 18 #1 | `sh start_agent.sh` | Start the hardware bridge | K1 | HW-DRV | Yes – core | Retain – system driver |
| 18 #2 | `ros2 launch M3Pro_navigation base_bringup.launch.py` | Base pipeline | K5 | YB-APP, 3P-SRC, ROS-APT | Yes – core | Recreate (as 17 #2) |
| 18 #3 | `ros2 launch M3Pro_navigation navigation2.launch.py` | Nav2; several goals given in RViz | K11 | YB-APP, YB-CFG, ROS-APT | Yes – core | Recreate (as 17 #3) |
| 18 #4 | `ros2 launch M3Pro_navigation nav_rviz.launch.py` | Navigation view | K12 | YB-APP | Optional | Recreate (RViz configuration) |
| 19 #1 | `sh start_agent.sh` | Start the hardware bridge | K1 | HW-DRV | Yes – core | Retain – system driver |
| 19 #2 | `ros2 launch M3Pro_navigation base_bringup.launch.py` | Base pipeline | K5 | YB-APP, 3P-SRC, ROS-APT | Yes – core | Recreate (as 17 #2) |
| 19 #3 | `ros2 launch M3Pro_navigation cartographer_localization.launch.py` | Cartographer pure localization in `/home/jetson/yahboom_map.pbstream` using `M3Pro_navigation/param/yahboom_M3Pro.lua`; remaps `imu`→`/imu/data` | `cartographer_ros` (apt); `M3Pro_navigation` configuration; `.pbstream` file in home | ROS-APT, YB-CFG | No (unless Cartographer localization is chosen) | Not required |
| 19 #4 | `ros2 launch M3Pro_navigation navigation2.launch.py` | Nav2. This also starts AMCL and the map server, so two `map → odom` sources run unless one is disabled | K11 | YB-APP, YB-CFG, ROS-APT | Yes – core (Nav2) | Recreate (as 17 #3) |
| 19 #5 | `ros2 launch M3Pro_navigation nav_rviz.launch.py` | Navigation view | K12 | YB-APP | Optional | Recreate (RViz configuration) |
| 20 #1 | `sh start_agent.sh` | Start the hardware bridge | K1 | HW-DRV | Yes – core | Retain – system driver |
| 20 #2 | `ros2 launch M3Pro_navigation rtab_bringup.launch.py` | Base pipeline + camera + costmap updater + fixed camera transform | K13 | YB-APP | No (unless RTAB-Map is chosen) | Not required |
| 20 #3 | `ros2 topic pub /arm6_joints arm_msgs/msg/ArmJoints {"joint1: 90,joint2: 180,joint3: 5,joint4: 0,joint5: 90,joint6: 0,time: 1500"} --once` | Point the arm camera forward for visual mapping | K2 | YB-IF, HW-DRV | Yes – core (topic and type) | Recreate – interface-compatible |
| 20 #4 | `ros2 launch rtabmap_launch rtabmap.launch.py rgb_topic:=/camera/color/image_raw … rtabmap_args:="--delete_db_on_start"` (full text: Appendix A) | RTAB-Map RGB-D and scan mapping with external odometry; clears the database at start | `rtabmap_launch` (apt, BSD) | ROS-APT | No | Not required |
| 20 #5 | `ros2 run yahboomcar_ctrl yahboom_keyboard` | Drive while mapping | K7 | YB-APP | Optional | Install – apt `teleop_twist_keyboard` |
| 21 #1 | `sh start_agent.sh` | Start the hardware bridge | K1 | HW-DRV | Yes – core | Retain – system driver |
| 21 #2 | `cp ~/.ros/rtabmap.db ~` | Keep the RTAB-Map database | `~/.ros/rtabmap.db` → `~/rtabmap.db` | SYS, YB-CFG | No | Not required (Capture data only if RTAB-Map is chosen) |
| 21 #3 | `ros2 launch M3Pro_navigation rtab_bringup.launch.py` | Base pipeline + camera | K13 | YB-APP | No | Not required |
| 21 #4 | `ros2 topic pub /arm6_joints arm_msgs/msg/ArmJoints {"joint1: 90,joint2: 180,joint3: 5,joint4: 0,joint5: 90,joint6: 0,time: 1500"} --once` | Camera forward | K2 | YB-IF, HW-DRV | Yes – core (topic and type) | Recreate – interface-compatible |
| 21 #5 | `ros2 launch rtabmap_launch rtabmap.launch.py … database_path:=/home/jetson/rtabmap.db … rviz_cfg:=/home/jetson/yahboomcar_ws/src/slam_view/rviz/slam_rviz.rviz rtabmap_args:="--Mem/IncrementalMemory false"` (full text: Appendix A) | RTAB-Map localization in the saved database | `rtabmap_launch` (apt); RViz file inside the factory `slam_view` package source | ROS-APT, YB-CFG | No | Not required |
| 21 #6 | `ros2 launch nav2_bringup navigation_launch.py` | Nav2 servers without map server or AMCL | `nav2_bringup` (apt). The copy in folder 21 is a Yahboom-modified version defaulting to `M3Pro_navigation/param/yahboom_M3Pro_carto.yaml`; which file the robot actually ran is unknown | ROS-APT (possibly modified) | No | Not required |
| 22 #1 | `sh start_agent.sh` | Start the hardware bridge | K1 | HW-DRV | Yes – core | Retain – system driver |
| 22 #2 | `ros2 launch M3Pro_demo camera_arm_kin.launch.py` | Camera and IK service | K3 | YB-APP, HW-DRV | Yes – core | Recreate (see 01 #4) |
| 22 #3 | `ros2 launch M3Pro_navigation base_bringup.launch.py` | Base pipeline | K5 | YB-APP, 3P-SRC, ROS-APT | Yes – core | Recreate (as 17 #2) |
| 22 #4 | `ros2 run M3Pro_demo grasp_transport` | Receives tag pixel and depth on `PosInfo`; computes the target with a hard-coded camera matrix, hand-eye matrix, FK and the 01 offsets; calls IK; drives the arm; publishes `grasp_done` | `M3Pro_demo`, `arm_kin` service and `offset_value.yaml`, `arm_interface`, `arm_msgs`, `transforms3d`, `tf_transformations` | YB-APP, YB-CFG | Reference: E-AIRA `grasp_executor` reproduces its IK-to-servo mapping | Recreate (partly done); keep the vendor node as test oracle only |
| 22 #5 | `ros2 run M3Pro_demo apriltag_transport_V2` | AprilTag search, base alignment and transport sequence, operated by keys in an OpenCV window; sends Nav2 goals | `M3Pro_demo`, `dt_apriltags`, `nav2_msgs` | YB-APP | No (orchestration replaced by the E-AIRA brain) | Not required |
| 22 #6 | `ros2 launch slam_view slam_view.launch.py` | RViz | `slam_view` package (factory, separate from `slam_mapping`) | YB-APP | Optional | Recreate (RViz configuration) |
| 22 #7 | `ros2 launch M3Pro_navigation navigation2.launch.py map_dir: = /root/M3Pro_ws/src/yahboom_mapping/maps/yahboom_map.yaml` | Nav2 on a saved map | K11. The map path is under `/root`, not the `jetson` home; the launch file declares `map`, not `map_dir` (see Appendix C) | YB-APP, YB-CFG, ROS-APT | Yes – core | Recreate (E-AIRA Nav2 and map location) |
| 22 #8 | `ros2 run yahboom_nav2_bringup rotation_detect_V2` | Rotate the base to search for tags (inferred from `/start_rotate` and `/rotation_done` in node 22 #5) | `yahboom_nav2_bringup` (source not in the folder) | YB-APP | No (the brain's SCAN state covers it) | Not required |
| 22 #9 | `ros2 run yahboom_nav2_bringup get_nav2_status_V2` | Watch Nav2 results and trigger the next step (inferred from flag topics) | `yahboom_nav2_bringup` | YB-APP | No (the brain monitors Nav2) | Not required |
| 23 #1 | `ros2 launch M3Pro_demo camera_arm_kin.launch.py` | Camera and IK service. This README does not start the agent first | K3 | YB-APP, HW-DRV | Yes – core | Recreate (see 01 #4) |
| 23 #2 | `ros2 launch M3Pro_navigation base_bringup.launch.py` | Base pipeline | K5 | YB-APP, 3P-SRC, ROS-APT | Yes – core | Recreate (as 17 #2) |
| 23 #3 | `ros2 run M3Pro_demo grasp_transport` | Grasp executor (as 22 #4) | as 22 #4 | YB-APP, YB-CFG | Reference | Recreate (partly done); vendor node as oracle |
| 23 #4 | `ros2 run M3Pro_demo color_transport` | HSV colour block detection, PID alignment, transport | `M3Pro_demo` (+ `color_common`, `compute_pose`), data path `/home/jetson/yahboomcar_ws/src/M3Pro_demo/M3Pro_demo/`, `dt_apriltags` | YB-APP, YB-CFG | No (colour filter already recreated in `vision_manager`) | Not required |
| 23 #5 | `ros2 launch slam_view slam_view.launch.py` | RViz | `slam_view` | YB-APP | Optional | Recreate (RViz configuration) |
| 23 #6 | `ros2 launch M3Pro_navigation navigation2.launch.py map_dir:=/root/M3Pro_ws/src/yahboom_mapping/maps/yahboom_map.yaml` | Nav2 on a saved map | K11; `map_dir` is not a declared argument, so the default map is loaded (Appendix C) | YB-APP, YB-CFG, ROS-APT | Yes – core | Recreate |
| 23 #7 | `ros2 run yahboom_nav2_bringup get_nav2_status_V2` | Watch Nav2 results | `yahboom_nav2_bringup` | YB-APP | No | Not required |
| 24 #1 | `sh start_agent.sh` | Start the hardware bridge (the folder copy is named `sh start_agent.sh`) | K1 | HW-DRV | Yes – core | Retain – system driver |
| 24 #2 | `ros2 launch slam_mapping slam_toolbox.launch.py` | Build the map (as 16 #2) | `slam_mapping`, `slam_toolbox` | YB-APP, YB-CFG, ROS-APT | Yes – prerequisite | Recreate |
| 24 #3 | `ros2 launch slam_mapping save_slamtoolbox_map.launch.py` | Save the occupancy grid to `~/map/map` | `slam_mapping`, `nav2_map_server` | YB-APP, ROS-APT | Yes – prerequisite | Recreate – E-AIRA map save |
| 24 #4 | `ros2 launch slam_mapping save_slamtoolbox_map.launch.py map_type:=posegraph` | Serialise the SLAM Toolbox pose graph to `~/map/map` via `/slam_toolbox/serialize_map` | `slam_mapping`, `slam_toolbox` | YB-APP, ROS-APT | Yes – prerequisite (only for SLAM Toolbox localization) | Recreate |
| 24 #5 | `$HOME/M3Pro_ws/src/m3pro_bringup/config/common.yaml` | File opened for editing in the lesson (not a command); shared parameters | `m3pro_bringup` configuration in `~/M3Pro_ws/src` | YB-CFG | Unknown until read | Capture data (read on the Jetson; copy the values E-AIRA needs) |
| 24 #6 | `ros2 launch m3pro_bringup record_tag.launch.py` | Record AprilTag poses in `map` into `aritag_relocation.yaml` while running SLAM Toolbox localization and Nav2; after 8 s calls `/control_detection {command: 1}` | `m3pro_bringup`, `apriltag_localization` (`apriltag_recorder`), `M3Pro_navigation` | YB-APP | Optional (localization recovery) | Recreate – E-AIRA tag-map recorder on apt `apriltag_ros`, or keep the vendor tool until replaced |
| 24 #7 | `$HOME/M3Pro_ws/src/m3pro_bringup/config/aritag_relocation.yaml` | Recorded tag map (file, not a command) | `m3pro_bringup` configuration | YB-CFG | Optional | Capture data (valid only while the tags stay in place) |
| 24 #8 | `ros2 launch M3Pro_navigation toolbox_location_nav.launch.py relocation:=True detection_enabled:=True` | Navigation with SLAM Toolbox localization (`~/map/map.yaml`, pose graph `~/map/map`) and AprilTag relocalization through `car_base.launch.py` | `M3Pro_navigation` (`bringup_mod.launch.py`), `slam_mapping` (`localization_launch.py`), `m3pro_bringup`, `apriltag_localization` | YB-APP | Yes – core if this localization method is chosen | Recreate |
| 24 #9 | `ros2 service call /control_detection apriltag_localization/srv/ControlDetection "{command: 0}"` | Control tag detection; the meaning of 0, 1 and 2 is not documented in the repository | `apriltag_localization` service type | YB-IF | Optional | Recreate (E-AIRA trigger; no firmware involved, so no type compatibility needed) |
| 24 #10 | `ros2 service call /control_detection apriltag_localization/srv/ControlDetection "{command: 1}"` | as 24 #9 | as 24 #9 | YB-IF | Optional | as 24 #9 |
| 24 #11 | `ros2 service call /control_detection apriltag_localization/srv/ControlDetection "{command: 2}"` | as 24 #9 | as 24 #9 | YB-IF | Optional | as 24 #9 |
| 24 #12 | `$HOME/M3Pro_ws/src/m3pro_bringup/launch/record_tag.launch.py` | Launch file studied in the lesson (not a command) | `m3pro_bringup` | YB-APP | — | Reference (copy kept in folder 24) |
| 24 #13 | `$HOME/M3Pro_ws/src/M3Pro_navigation/launch/toolbox_location_nav.launch.py` | Launch file studied in the lesson (not a command) | `M3Pro_navigation` | YB-APP | — | Reference (copy kept in folder 24) |
| 25 #1 | `ros2 launch orbbec_camera dabai_dcw2.launch.py` | Start the RGB-D camera | K4 | HW-DRV | Yes – core | Retain – system driver; prefer apt `ros-humble-orbbec-camera` after checking it on this camera; E-AIRA overrides registration and point-cloud settings |
| 26 #1 | `ros2 launch orbbec_camera dabai_dcw2.launch.py` | Start the camera | K4 | HW-DRV | Yes – core | Retain – system driver |
| 26 #2 | `ros2 run yahboom_M3Pro_DepthCam GetDepthColor` | Show colour-mapped depth | `yahboom_M3Pro_DepthCam` | YB-APP | Optional (diagnostic) | Not required (optional output in `vision_manager`) |
| 27 #1 | `ros2 launch orbbec_camera dabai_dcw2.launch.py` | Start the camera | K4 | HW-DRV | Yes – core | Retain – system driver |
| 27 #2 | `ros2 run yahboom_M3Pro_DepthCam Measure_Distance` | Depth at a clicked pixel | `yahboom_M3Pro_DepthCam` | YB-APP | Optional (diagnostic) | Not required (optional `/eira/depth_distance`) |
| 28 #1 | `ros2 launch M3Pro_demo camera_arm_kin.launch.py` | Camera and IK service | K3 | YB-APP, HW-DRV | Yes – core | Recreate (see 01 #4) |
| 28 #2 | `ros2 run M3Pro_demo estimate_volume` | Block dimensions from depth, FK and the 01 offsets; moves base and arm | `M3Pro_demo` (+ `compute_pose`), `arm_kin`, `offset_value.yaml` | YB-APP, YB-CFG | No | Not required |
| 29 #1 | `ros2 launch orbbec_camera dabai_dcw2.launch.py` | Start the camera | K4 | HW-DRV | Yes – core | Retain – system driver |
| 29 #2 | `ros2 run M3Pro_demo mediapipe_gesture` | Hand-gesture classification; moves the arm to a fixed pose at start | `M3Pro_demo.media_library` wrapping MediaPipe (Apache-2.0) | YB-APP, SYS | Optional | Not required (frozen `gesture_node` exists) |
| 30 #1 | `ros2 launch orbbec_camera dabai_dcw2.launch.py` | Start the camera | K4 | HW-DRV | Yes – core | Retain – system driver |
| 30 #2 | `ros2 run yahboom_M3Pro_DepthCam edge_detection` | After SPACE, drives forward at 0.1 m/s until the centre-pixel depth exceeds 0.5 m (a drop-off). **Moves the base** | `yahboom_M3Pro_DepthCam` | YB-APP | Optional (safety) | Not required (frozen `edge_monitor` exists) |
| 31 #1 | `ros2 launch orbbec_camera dabai_dcw2.launch.py` | Start the camera | K4 | HW-DRV | Yes – core | Retain – system driver |
| 31 #2 | `ros2 run yahboom_yolov8 yolov8_detect` | YOLOv8n tracking on the colour image; publishes `detect_image` | `yahboom_yolov8`; Ultralytics (AGPL-3.0); weights `/home/jetson/yahboomcar_ws/src/yahboom_yolov8/yahboom_yolov8/yolov8/weights/yolov8n.pt`; `sys.path` into the vendored `yolov8` directory | YB-APP, YB-CFG, SYS | Yes – core (detection) | Recreate (done in `vision_manager`); weights into an E-AIRA model directory from the official release; remove the default path into `yahboomcar_ws` |
| 31 #3 | `ros2 run rqt_image_view rqt_image_view` | View images | K14 | ROS-APT | Optional | Install – apt |
| 32 #1 | `ros2 launch yahboom_yolov8 yolov8_deep_track.launch.py` | Scan pipeline (`yahboom_M3Pro_laser/laser_driver.launch.py`) + camera | `yahboom_yolov8`, K6, K4 | YB-APP, HW-DRV | Optional | Recreate (covered by E-AIRA bring-up) |
| 32 #2 | `ros2 run yahboom_yolov8 yolov8_track` | TensorRT YOLOv8s engine (`yolov8s.trt`, batch 3) with `tracker_trt`; follows a chosen track ID keeping a LiDAR distance; publishes `/cmd_vel`; moves the arm to a fixed pose. This README does not start the agent | `yahboom_yolov8` (+ `common`, `Robot_Move`, `tracker_trt`), TensorRT, PyTorch, Ultralytics ops | YB-APP, SYS | Optional (relevant to the edge-latency research question) | Recreate – E-AIRA TensorRT engine built from official weights; no vendor code |
| 33 #1 | `sh start_agent.sh` | Start the hardware bridge | K1 | HW-DRV | Yes – core | Retain – system driver |
| 33 #2 | `ros2 launch m3pro_bringup car_base.launch.py` | Complete base bring-up: camera (`m3pro_bringup/dabai_dcw2.launch.py` as a subprocess), `robot_state_publisher` (xacro of `M3Pro/urdf/m3pro.urdf`), `joint_state_publisher` (source `/arm_status/arm_joint`), merger, filter, EKF, `static_tf.launch.py`, `arm_util/arm_status` (with `config/common.yaml`), AprilTag relocalization | `m3pro_bringup`, `M3Pro`, `arm_util`, `apriltag_localization`, `ira_laser_tools`, `yahboom_laser_filter`, `ekf_bringup`, K4 | YB-APP, YB-CFG | Yes – core (reference composition for the E-AIRA bring-up) | Recreate – E-AIRA bring-up reproducing this composition with E-AIRA-owned files |
| 33 #3 | `ros2 launch m3pro_bringup super_tracker.launch.py` | `smart_tracker/super_tracker` (model `~/MODELS/tracker/super_track_sim.onnx`, image remapped from `/camera/color/image_raw`), `smart_tracker/pcl_segment` (`common.yaml`), RViz | `smart_tracker` (source availability unknown), ONNX model in `~/MODELS` | YB-APP, YB-CFG | Not for fetching; the paper title mentions transformer tracking | Cannot be recreated without source. Replace with an open tracker or drop the claim (decision Q6) |

## 4. Summary counts

| | Count |
|---|---:|
| README lines listed | 140 (31 README files) |
| Folders without README | 2 (05, 08) |
| Lines that are file paths, not commands | 4 (24 #5, #7, #12, #13) |
| Lines starting the hardware bridge (K1) | 21 |
| Lines that move the arm directly (K2) | 7 |
| Lines needing a desktop session (`gnome-terminal`, RViz, rqt, OpenCV windows) | most; E-AIRA must run headless |

## Appendix A — Full text of shortened commands

20 #4:

```text
ros2 launch rtabmap_launch rtabmap.launch.py rgb_topic:=/camera/color/image_raw depth_topic:=/camera/depth/image_raw camera_info_topic:=/camera/color/camera_info odom_topic:=/odom frame_id:=base_link use_sim_time:=false rviz:=true rtabmap_viz:=false approx_sync:=true approx_sync_max_interval:=0.01 qos:=2 visual_odometry:=false icp_odometry:=false subscribe_scan:=true sync_queue_size:=50 topic_queue_size:=50 rtabmap_args:="--delete_db_on_start"
```

21 #5:

```text
ros2 launch rtabmap_launch rtabmap.launch.py rgb_topic:=/camera/color/image_raw depth_topic:=/camera/depth/image_raw camera_info_topic:=/camera/color/camera_info odom_topic:=/odom frame_id:=base_link use_sim_time:=false rviz:=true rtabmap_viz:=false approx_sync:=true approx_sync_max_interval:=0.01 qos:=2 frame_id:=base_link visual_odometry:=false icp_odometry:=false subscribe_scan:=true sync_queue_size:=50 topic_queue_size:=50 database_path:=/home/jetson/rtabmap.db namespace:=/ rviz_cfg:=/home/jetson/yahboomcar_ws/src/slam_view/rviz/slam_rviz.rviz rtabmap_args:="--Mem/IncrementalMemory false"
```

## Appendix B — Paths outside `eira_ws` that the exercises depend on

| Path | Used by | Kind |
|---|---|---|
| `~/start_agent.sh` | 01–04, 06, 07, 10–22, 24, 33 | Script |
| `/home/jetson/mircoROS_agent/install/setup.bash` | K1 | Driver workspace |
| `/dev/myserial` | K1, 01 #2, `config_robot.py` | Device symlink (udev) |
| `~/calibrate_arm.py`, `config_robot.py` (same directory) | 01 #2 | Maintenance tool |
| `~/joy_control/joy.sh`, `~/joy_control/start_joy_controller.py` | 02 #2 | Scripts |
| `/home/jetson/yahboomcar_ws/install/setup.bash` | 02 #2 (`joy.sh`) | Factory workspace |
| `/home/jetson/M3Pro_ws/install/setup.bash` | 02 #2 (`joy.sh`) | Factory workspace |
| `/home/jetson/yahboomcar_ws/src/arm_kin/param/offset_value.yaml` | 01 #5 (writes), 22, 23, 28 (read) | Calibration data inside a package source tree |
| `/home/jetson/yahboomcar_ws/src/M3Pro_demo/M3Pro_demo/LineFollowHSV.text` | 06, 14, 15 | Calibration data |
| `/home/jetson/yahboomcar_ws/src/M3Pro_demo/M3Pro_demo/` | 23 | Data directory |
| `/home/jetson/yahboomcar_ws/src/yahboom_yolov8/yahboom_yolov8/yolov8/` (+ `weights/yolov8n.pt`, `yolov8s.trt`) | 31, 32; **also the E-AIRA `vision_manager` default** | Model files and vendored library |
| `/home/jetson/yahboomcar_ws/src/slam_view/rviz/slam_rviz.rviz` | 21 #5 | RViz configuration |
| `$HOME/M3Pro_ws/src/m3pro_bringup/config/common.yaml`, `aritag_relocation.yaml` | 24, 33 | Configuration and tag map |
| `<M3Pro_navigation share>/map/yahboom_map.{yaml,pgm}` | K9 (writes), K11 (reads) | Map inside a factory package |
| `~/map/map.{yaml,pgm,posegraph,data}` | 24 (writes and reads); **also the E-AIRA master-launch default `map`** | Map files |
| `/home/jetson/yahboom_map.pbstream` | 19 #3 | Cartographer state |
| `~/.ros/rtabmap.db`, `~/rtabmap.db` | 20, 21 | RTAB-Map database |
| `~/MODELS/tracker/super_track_sim.onnx` | 33 #3; **also the E-AIRA `transformer_model_path` default** | Model file |
| `/root/M3Pro_ws/src/yahboom_mapping/maps/yahboom_map.yaml` | 22 #7, 23 #6 | Map path from Yahboom documentation |

## Appendix C — Observations on the recorded commands

These are notes for interpreting the records. The README files themselves are
left as they are.

1. **22 #7, 23 #6.** `navigation2.launch.py` declares an argument named `map`.
   `map_dir` is not declared, so it is ignored and the default map inside
   `M3Pro_navigation` is used. In 22 #7, `map_dir: =` is not in
   `name:=value` form. The `/root/M3Pro_ws/...` path belongs to a root user,
   not to `jetson`; it probably comes from Yahboom's documentation.
2. **19.** Both Cartographer localization and AMCL publish `map → odom` when
   these launch files are combined.
3. **23 and 32** do not start the agent in their README. The base and arm
   cannot move without it, so it was presumably already running.
4. **20 #4** clears the RTAB-Map database at start (`--delete_db_on_start`).
5. **14, 15, 16** drive the robot along a line while mapping. This is why the
   camera, IK service and line follower appear in mapping exercises.
6. **01 #2.** `calibrate_arm.py` writes the calibration whatever the operator
   types at its confirmation prompt.
7. **02 #4.** `yahboom_joy_M3Pro` cancels navigation through `move_base/cancel`,
   a ROS 1 topic that Nav2 does not use.
8. **21 #6.** The `navigation_launch.py` copy kept in folder 21 differs from
   stock `nav2_bringup`: it defaults to `yahboom_M3Pro_carto.yaml`.
