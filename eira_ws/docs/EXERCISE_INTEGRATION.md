# Exercise integration ledger

Author: E-AIRA maintainers. Target: ROSMASTER M3 Pro / Jetson Orin NX / ROS 2 Humble.

This ledger follows the **actual folder contents**, not the numbering assigned
in the feature request. Existing hardware drivers and SLAM implementations are
reused. E-AIRA adapters change orchestration, validation and data contracts;
course scripts were not copied into the workspace.

Launch native tools with
`ros2 launch eira_bringup exercise_profiles.launch.py profile:=NAME`.
Only one motion-owning profile/master should run at a time. Native profiles
require the existing package and its real configuration on the robot. Missing
packages/files produce an explicit dependency diagnostic rather than an invented
implementation. Sensor skills require a subsequent `/eira/skill/request`.

| Folder | Actual exercise | Integration |
|---|---|---|
| 01 | Arm calibration | `arm_calibration` profile reuses `M3Pro_demo/arm_offset`; E-AIRA stores calibrated mount and joint limits. Firmware/servo transport remains native. |
| 02 | Joystick controller | `joystick` profile starts native joystick control and `joy_node`, routing base commands through the gate. |
| 03 | Keyboard control | `keyboard` profile starts the gate and prints the native foreground control command for a second terminal; stdin is never assumed forwarded by launch. |
| 04 | Angular velocity calibration | `calibrate_angular` profile starts the existing measured calibration tool; no automatic firmware writes. |
| 05 | Linear velocity calibration | `calibrate_linear` profile starts the existing measured calibration tool; no automatic firmware writes. |
| 06 | Line following | Adapted `exercise_skills` line follower uses a parameterized HSV ROI centroid, bounded speed and sensor watchdogs. |
| 07 | Obstacle avoidance | Adapted LiDAR avoidance skill replaces unsafe open-loop branches with finite-sector reasoning and stop-on-unknown. This folder contains no gripper safety table. |
| 08 | Robot model | `robot_display` uses the real M3Pro model. `simulation` reuses the exercise's separate `neurobotics` Gazebo model; this is differential drive and is not claimed dynamically equivalent to the mecanum robot. |
| 09 | LiDAR introduction | `lidar_view` exposes RViz inspection of the existing `/scan`; E-AIRA skills consume the native scan stream. |
| 10 | LiDAR fusion | `lidar_fusion` and master base bringup reuse native dual-scan merger/filter configuration. |
| 11 | LiDAR obstacle avoidance | `sensor_skills`: `lidar_avoid`; no blind backing or driving through a trapped sector. |
| 12 | LiDAR tracking | `sensor_skills`: `lidar_track`; metric standoff/bearing feedback and velocity limits. |
| 13 | LiDAR guard | `sensor_skills`: `lidar_guard`; bounded rotation-only tracking and rate-limited buzzer. |
| 14 | Gmapping | `gmapping` / `save_map` profiles reuse the installed SLAM/map-saver tools. |
| 15 | Cartographer mapping | `cartographer` / `save_map` profiles reuse the robot's Lua calibration and native SLAM. |
| 16 | SLAM Toolbox | `slam_toolbox` / `save_map` profiles; mapping remains separate from runtime AMCL localization. |
| 17 | Single-goal Nav2 | Master Brain sends `NavigateThroughPoses` with one measured waypoint; native Nav2 velocity smoother routes into gate. |
| 18 | Multi-goal Nav2 | Brain sequences named navigation actions, each with independent identity, deadline and cancellation. |
| 19 | Repositioning navigation | `cartographer_localization` reuses recorded-map localization. This is not a large-language-model exercise. |
| 20 | RTAB-Map mapping | `rtabmap_mapping` profile sets RGB-D, intrinsics, scan and external-odometry contracts. This is not a Whisper exercise. |
| 21 | RTAB-Map navigation | `rtabmap_localization` profile consumes an existing database; run master navigation with `use_nav_localization:=false` alongside that localization, avoiding simultaneous AMCL. |
| 22 | Fiducial transport | Correlated Brain→Vision→Arm missions replace tutorial command chains; `tag_recording` preserves native fiducial recording. |
| 23 | Color-block transport | Vision color filtering plus Brain color-aware fetch/sort plans and Arm measured color-bin poses. |
| 24 | Pose-constrained visual relocalization | Optional `visual_relocalization` monitors AMCL uncertainty and gates measured ArUco or external AprilTag poses into `/initialpose`. |
| 25 | Dabai DCW2 camera | Master/`camera` profile requests registered RGB-D and disables unused IR/point-cloud load. |
| 26 | Depth pseudocolor | Vision optional `/eira/depth_image`, rate-limited and independent of successful YOLO initialization. |
| 27 | Depth distance | Vision optional `/eira/depth_distance`, ROI-median metric probe with uint16-mm/float-m conversion. |
| 28 | Wood-block volume | Found metadata carries projected width/height and a cuboid/cylinder estimate using explicitly configured thickness; unknown hidden thickness produces null volume. |
| 29 | MediaPipe gestures | Optional debounced OK confirmation / Thumb_down cancellation node. |
| 30 | Edge detection | Adapted geometric floor monitor uses metric depth, intrinsics, measurement-time TF and a protected ground corridor; unknown data blocks the enabled gate. |
| 31 | YOLOv8 detection | Asynchronous local model initialization/inference, bounded rates and annotated output. |
| 32 | Deep-learning tracking | Persistent ID association, bounded positional smoothing and target-identity retention. |
| 33 | Transformer tracking | Parameter-selected backend with YOLO acquisition/reacquisition, OpenCV ViT or vendor adapter factory; explicit fallback when the model ABI/dependency is unavailable. |

## Additional requested features absent from the course source

- Local Whisper ASR: new `voice_input`/`voice_activation` adapter, local weights,
  optional microphone, bounded model/transcription worker, wake word and `/eira/voice`.
- Mobile application commands: optional rosbridge WebSocket with restricted
  command/status topics, localhost binding by default.
- Gripper width calibration: measured interpolation table required; no made-up
  table or unrestricted extrapolation.

## Native profile arguments

`profile_launch_arguments` is a JSON object passed as key/value pairs to the
native launch. `profile_arguments` is a shell-tokenized executable argument
string passed as an argument list; no shell is executed.

For example, RTAB-Map localization requires your real database path:

```bash
ros2 launch eira_bringup exercise_profiles.launch.py \
  profile:=rtabmap_localization \
  profile_launch_arguments:='{"database_path":"/home/jetson/rtabmap.db"}'
```

Mapping profiles expect hardware/TF/odometry to be running. Do not run mapping
and AMCL for the same map-to-odom transform. Gmapping/Cartographer configuration,
posegraphs, calibration values and proprietary model assets remain dependencies
of their original packages.
