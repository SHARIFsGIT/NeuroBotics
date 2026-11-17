# E-AIRA — Edge-based AI Robot Assistant

E-AIRA is the ROS 2 Humble orchestration layer for a Yahboom ROSMASTER M3 Pro
with Jetson Orin NX. Phi-3 through local Ollama plans missions; a deterministic
parser supplies a bounded fallback. Existing Yahboom drivers retain ownership
of hardware transport, inverse kinematics, and servo execution.

The six packages implement cognition (`eira_brain`), perception
(`eira_perception`), manipulation (`eira_manipulation`), system integration
(`eira_bringup`), reproducible evaluation (`eira_evaluation`), and Gazebo
simulation (`eira_simulation`). All Python targets Python 3.10 / ARM64; simulation also runs on a compatible development workstation.

**Starting a new robot test session?** Follow
[Fresh-start testing: commands, reasons and expected results](docs/FRESH_START_TESTING.md).
It starts with environment/build checks and stationary depth validation before
navigation, arm motion and complete missions.

**RViz shows only a raw image?** Use the
[YOLO/RViz diagnostic procedure](docs/YOLO_RVIZ_DIAGNOSTICS.md) and its two-image
preset to check `/eira/detect_image` separately from the raw camera stream.

**Testing a fetch from a named place?** Follow the
[requested-object fetch test](docs/FETCH_MISSION_TESTING.md). A request such as
`bring me a bottle from kitchen` navigates there before starting detection,
grasps the requested object, returns to the pose captured at mission start,
then releases. The object is selected by the command and must be a class your
installed detector supports.

## Evaluation, simulation, and reproducible replay

```bash
ros2 launch eira_bringup eira_master.launch.py use_evaluation:=true use_recording:=true
ros2 run eira_evaluation benchmark --command "Bring me a cup" --iterations 20
ros2 run eira_evaluation metrics_calculator ~/eira_ws/results/mission_log_YYYYMMDD.csv
ros2 launch eira_simulation sim_bringup.launch.py randomize:=true seed:=42
ros2 run eira_brain mission_replayer ~/eira_ws/bags/mission_UTC_ID --dry-run
```

The logger writes CSV plus detailed JSON, and exports text, PNG and LaTeX reports.
Action attempts, recovery and planner latency are correlated by IDs; actual
held-object accuracy requires explicit evidence. The new prompt is grounded in
live waypoints/classes and repairs one invalid response before fallback.

See the [research protocol](docs/RESEARCH_PROTOCOL.md),
[evaluation API/metric definitions](src/eira_evaluation/README.md), and
[simulation instructions and model limits](src/eira_simulation/README.md).
Existing hardware launch defaults are preserved: evaluation/recording are opt-in,
and `use_sim_time` defaults false. Simulation supplies true explicitly.

## Architecture

```text
 CLI / mobile rosbridge / local Whisper / external voice transcript
                         |
                   /eira/command or /eira/voice
                         v
       +--------------------------------------------+
       | Brain: LLM -> grounded plan -> locked FSM   |
       | mission IDs, action IDs, retries, FIFO      |
       +-------+----------------+-------------------+
               |                |                 |
      NavigateThroughPoses   vision_target    manipulation/request
               v                v                 v
       native Nav2       YOLO / transformer   base alignment PID
       controller ->     + RGB-D + color      -> existing Yahboom IK
       vel smoother      + pose smoothing     -> feedback-aware arm
               |           | target_pose          |
               |           +--------------------->|
               |                                  |
       /eira/cmd_vel/nav       /eira/cmd_vel/arm    |
               +---------------+------------------+
                               |
 Brain scan -> /eira/cmd_vel/brain
                               v
                     +------------------+
 motion_owner ------>| velocity gate    |<--- heartbeat watchdog
 depth floor edge -->| lease + priority |<--- stop command
                     +--------+---------+
                              | sole managed output
                           /cmd_vel
                              v
                      existing base driver
```

All accepted asynchronous results are correlated with a mission and action.
Stop invalidates planning, navigation and IK generations before releasing motion.
The gate forwards only the selected source, bounds velocity, expires stale
Twists, and blocks stale heartbeat or enabled floor-safety input. Revoked
missions cannot rearm from delayed ownership messages.

Vision defaults to `continuous_mode: false`: only an explicit find request starts
inference, and found/timeout/failure returns it to `idle (no active search)`.
During a grasp, the Brain requests bounded one-shot pose refreshes so alignment
uses current measurements. There is no background YOLO inference during navigation
or idle. Select `continuous_mode: true` for standalone tracking/occlusion tests.
Idle has no selected object (`target_class: ''`). Measured RGB-D ranging is the
default; an optional height estimate requires an explicitly configured
`bbox_depth_class` and measured height for that class.

The LLM request timeout defaults to 30 seconds. Phi-3 responses have Markdown and
surrounding prose removed before complete action/target validation; raw replies
are available as debug-level `Model reply` lines (`llm_log_raw_response` controls
this). Navigation
waits 3 seconds after success and uses two retries with 10-second backoff. These
waits are nonblocking. AMCL planar covariance/age is checked before each goal,
with an advisory warning when confidence is insufficient. External localization
can set `amcl_check_enabled: false`; these checks do not reset AMCL or repair an
incorrect map, odometry, or TF calibration.

PID controls **base alignment**. The existing arm driver executes degree-valued
servo targets; E-AIRA does not claim to add a joint torque/position controller.

## Hardware and software

- Ubuntu 22.04, ROS 2 Humble, Python 3.10, ARM64 Jetson Orin NX.
- ROSMASTER M3 Pro mecanum base, native hardware transport/agent, dual 2D LiDAR.
- Dabai DCW2 RGB-D camera with depth registered to color and valid intrinsics.
- Six-joint Yahboom arm; `arm_msgs`, `arm_interface`, `arm_kin`, and `arm_util`.
- Calibrated map/waypoints, camera-to-base TF, arm mount, servo limits and gripper.
- A fresh **measured** joint stream is required to issue a safe arm hold. The
  course `Curjoints` topic can contain commanded poses; it is not automatically
  treated as encoder feedback.

Native mapping/navigation profiles also need the corresponding course packages.
For RTAB-Map localization, disable AMCL with `use_nav_localization:=false` when
starting the master navigation stack alongside that localization profile.
Optional dependencies are not required for the basic deterministic planner.

## Installation

Build on the target; generated `build/`, `install/` and `log/` artifacts contain
host-specific paths and must not be copied from another machine.

```bash
source /opt/ros/humble/setup.bash
# Source the installed Yahboom workspace, including its interface packages.
source ~/yahboomcar_ws/install/setup.bash
cd ~/NeuroBotics/eira_ws
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash
```

Vendor-specific packages must be supplied by the robot image when rosdep cannot
resolve them. Install a JetPack-compatible PyTorch/Ultralytics build for YOLO;
avoid replacing the Jetson CUDA stack with an unrelated desktop wheel.

Optional features:

| Feature | Additional software/assets |
|---|---|
| Local LLM | Ollama and locally provisioned `phi3` |
| Voice | `openai-whisper`, FFmpeg; `sounddevice`/PortAudio for microphone capture; preinstalled Whisper `.pt` weights |
| Gestures | An ARM64-compatible MediaPipe build exposing `solutions.hands` |
| Transformer | Compatible OpenCV ViT model/build, or a `module:factory` adapter for the supplied tracker |
| Mobile commands | `ros-humble-rosbridge-server` |
| ArUco recovery | OpenCV ArUco module and measured marker map |

Model loaders use local files. Whisper does not download missing weights at
runtime. The exact default YOLO path remains:

```text
/home/jetson/yahboomcar_ws/src/yahboom_yolov8/yahboom_yolov8/yolov8/weights/yolov8n.pt
```

## Configuration and calibration

The node parameters are in `src/eira_bringup/config/eira_params.yaml`.
All node defaults are explicitly recorded there. Nav2 uses a separate
`nav_params_file`; its defaults are resolved from
`M3Pro_navigation/param/yahboom_M3Pro.yaml`.

Before physical grasping:

1. Supply live `base_link -> arm_base_frame` TF, or measure the static arm
   mount offsets and explicitly set `static_mount_calibrated: true`.
2. Check the six joint limits and the actual meaning/provenance of `/Curjoints`.
   Keep `require_joint_feedback` and `require_actuator_subscribers` enabled.
   Set `joint_feedback_is_measured: true` only for actual measured joint feedback.
3. Measure width-to-gripper-angle pairs before selecting `gripper_mode: width`.
   `gripper_calibration.example.yaml` intentionally contains no fabricated table.
   Out-of-range widths are rejected; interpolation never extrapolates.
4. Record real waypoint coordinates. The supplied kitchen/desk/table values
   are examples, not measurements of your arena. The Brain reloads the database
   before each mission.
5. For floor-edge protection, calibrate `floor_z_m`, the protected corridor,
   camera TF and registered-depth dimensions. Unknown floor or frozen depth
   blocks motion while this feature is enabled.

A `sort_poses` JSON parameter maps color names to measured six-angle bin poses.
No bin poses are invented. `marker_map.example.yaml` describes the measured
fiducial-map format; external AprilTag localization may instead publish a
map-frame pose on `/eira/visual_pose`.

## Launch and usage

For readable logs, mission text summaries, arm display, RViz markers and buzzer
patterns, see [the operator interface guide](docs/OPERATOR_INTERFACE.md).

For Dabai depth holes, encoding/resolution diagnostics, separate depth intrinsics
and the optional cup-height range fallback, see
[the depth debugging guide](docs/DABAI_DEPTH_DEBUG.md).

For the ordered robot acceptance procedure, commands and expected outcomes, see
[the robot testing guide](docs/ROBOT_TESTING_GUIDE.md).

The hardware transport/agent and raw sensor drivers must already be available.
The master composes the existing filters, odometry, registered camera,
robot/static TF, IK, arm status, and native Nav2 nodes when installed.

```bash
ros2 launch eira_bringup eira_master.launch.py map:=/absolute/path/map.yaml

# Existing drivers/TF already running:
ros2 launch eira_bringup eira_master.launch.py \
  use_base:=false use_robot_tf:=false use_camera:=false use_arm:=false

# Perception/manipulation without Nav2:
ros2 launch eira_bringup eira_master.launch.py use_nav:=false

ros2 run eira_brain eira_cli "bring me a red cup from the kitchen"
ros2 run eira_brain eira_cli "sort the blue cup into table1"
ros2 run eira_brain eira_cli "stop"

# Local planning preview: no ROS initialization or command publication.
ros2 run eira_brain eira_cli --plan-only "find a blue cup and pick up the blue cup"
ros2 run eira_brain eira_cli --list-waypoints
ros2 run eira_brain waypoint_recorder
```

Optional adapters are disabled by default to avoid unnecessary GPU/CPU load:

```bash
ros2 launch eira_bringup eira_master.launch.py \
  use_voice:=true use_gestures:=true use_relocalization:=true use_edge:=true

# Transformer backend; incompatible/missing models explicitly fall back to YOLO.
ros2 launch eira_bringup eira_master.launch.py tracking_backend:=transformer
```

`voice_input` defaults to local-file transcription with wake word `eira`.
Set `voice_input.microphone_enabled: true` in the parameter YAML to enable the
microphone, and configure the installed model/device. The standalone executable
alias `voice_activation` uses its own matching YAML selector.

```bash
ros2 topic pub --once /eira/audio_file std_msgs/msg/String \
  "{data: '/absolute/path/eira_command.wav'}"
# Already-transcribed speech can use the planner's voice subscriber directly:
ros2 topic pub --once /eira/voice std_msgs/msg/String "{data: 'find a red cup'}"
```

Gesture confirmation is opt-in through
`grasp_executor.require_gesture_confirmation`. A stable OK gesture confirms the
matching grasp; Thumb_down cancels. Visual recovery publishes `/initialpose`
only when AMCL uncertainty is excessive and the visual estimate satisfies age,
covariance, reprojection and correction-distance limits.

## Mobile/WebSocket commands

```bash
ros2 launch eira_bringup eira_master.launch.py use_rosbridge:=true
```

The default endpoint is `ws://127.0.0.1:9090`. Use an SSH tunnel for a remote
mobile device, or explicitly configure `rosbridge_address` for the robot's LAN.
The topic allowlist exposes commands, transcripts, plans, status and speech;
raw velocity, ownership, arm commands and direct Nav2 actions are not exposed.
A client publishes a standard rosbridge message:

```json
{"op":"publish","topic":"/eira/command","msg":{"data":"find a red cup"}}
```

See the upstream [rosbridge protocol implementation](https://github.com/RobotWebTools/rosbridge_suite/tree/humble)
for client transport details.

## Exercise workflows

The actual numbered directories differ from the feature labels in the request:
19 is Cartographer relocalization, 20 is RTAB-Map mapping, 29 is MediaPipe, and
33 is transformer tracking. All 33 are mapped in
[EXERCISE_INTEGRATION.md](docs/EXERCISE_INTEGRATION.md).

```bash
ros2 launch eira_bringup exercise_profiles.launch.py profile:=slam_toolbox
ros2 launch eira_bringup exercise_profiles.launch.py profile:=calibrate_angular
ros2 launch eira_bringup exercise_profiles.launch.py profile:=keyboard
ros2 launch eira_bringup exercise_profiles.launch.py profile:=sensor_skills
```

Use one motion-owning workflow at a time; do not run a second gate/profile
alongside the master. Mapping/diagnostic profiles assume existing hardware
bringup. The keyboard profile starts the gate and prints the foreground command; ROS
launch does not forward stdin to child nodes. Run in an attached second terminal:

```bash
ros2 run yahboomcar_ctrl yahboom_keyboard --ros-args -r cmd_vel:=/eira/cmd_vel/exercise
```
Sensor skills wait for an explicit bounded request:

```bash
ros2 topic pub --once /eira/skill/request std_msgs/msg/String \
  '{data: "{\"command\":\"lidar_track\",\"mission_id\":\"demo\",\"action_id\":\"1\",\"duration_s\":10}"}'
```

## API

Existing public topic names and ROS message types are preserved. String request
payloads now accept JSON correlation envelopes; legacy plain labels/arm commands
remain accepted by their skill nodes. The Brain requires correlated results.

| Interface | Type | Contract |
|---|---|---|
| `/eira/command`, `/eira/voice` | `std_msgs/msg/String` | Plain instruction or `{command, mission_id}` |
| `/eira/plan`, `/eira/status` | `std_msgs/msg/String` | JSON with mission identity; status includes action/step/queue |
| `/eira/vision_target` | `std_msgs/msg/String` | `{mission_id, action_id, target}`, optional `refresh_id`/`cancel`, or legacy label |
| `/eira/vision/event` | `std_msgs/msg/String` | `found/lost/timeout/tf_error/failed`, identity and measurement metadata |
| `/target_pose` | `geometry_msgs/msg/PoseStamped` | Finite metric pose in `base_link`, original measurement stamp |
| `/eira/detect_image`, `/eira/depth_image` | `sensor_msgs/msg/Image` | Annotated color / optional pseudocolor depth |
| `/eira/depth_distance` | `std_msgs/msg/String` | Optional metric probe JSON |
| `/eira/manipulation/request` | `std_msgs/msg/String` | `{mission_id, action_id, command, target}` or legacy command |
| `/eira/manipulation/event` | `std_msgs/msg/String` | `grasped/released/homed/failed/stopped`, IDs and verification fields |
| `/navigate_through_poses` | `nav2_msgs/action/NavigateThroughPoses` | Existing Nav2 action, no E-AIRA action server |
| `/get_kinemarics` | `arm_interface/srv/ArmKinemarics` | Existing IK service; spelling preserved |
| `/arm6_joints`, `/arm_joint` | `arm_msgs/msg/ArmJoints`, `ArmJoint` | Driver angles in degrees, runtime in milliseconds |
| `/Curjoints`, `/grasp_done`, `/beep` | `CurJoints`, `Bool`, `UInt16` | Existing feedback/completion/buzzer interfaces |
| `/joint_states` | `sensor_msgs/msg/JointState` | Optional commanded arm display relay; not measured servo feedback |
| `/eira/visualization_markers` | `visualization_msgs/msg/MarkerArray` | Observed waypoint/object/heading display with frame and age checks |
| `/eira/heartbeat`, `/eira/safety/stop` | `Empty`, `Bool` | Liveness and independent watchdog interlock |
| `/eira/safety/edge` | `std_msgs/msg/String` | JSON `blocked`, reason, coverage and mission context |
| `/eira/motion_owner`, `/eira/motion/event` | `std_msgs/msg/String` | Owner selection and correlated gate state |
| `/eira/cmd_vel/{brain,arm,nav,teleop,exercise}` | `geometry_msgs/msg/Twist` | Fresh source inputs to the gate |
| `/cmd_vel` | `geometry_msgs/msg/Twist` | Final gated command in the managed launch |
| `/eira/audio_file`, `/eira/voice/event` | `std_msgs/msg/String` | Audio-file requests and local ASR diagnostics |
| `/eira/gesture` | `std_msgs/msg/String` | Debounced OK/Thumb_down event with current identity |
| `/eira/visual_pose`, `/initialpose` | `geometry_msgs/msg/PoseWithCovarianceStamped` | Visual map-frame estimate / AMCL correction |
| `/eira/localization/event` | `std_msgs/msg/String` | Recovery diagnostics |
| `/eira/skill/request`, `/eira/skill/event` | `std_msgs/msg/String` | Explicit bounded line/LiDAR behavior requests/results |

A found event includes `width_m`, `height_m`, `volume_m3`, color/track metadata,
and the measurement stamp. Volume is a **model-based estimate**: a single frontal
RGB-D image cannot determine hidden thickness. With the default zero thickness
prior, volume is null with an uncertainty explanation. Supply a measured
`volume_thickness_m` and appropriate `volume_shape` for a cuboid/cylinder estimate.

The transformer adapter contract is `initialize(BGR, xyxy)` followed by
`update(BGR) -> xyxy | None`. Exercise 33 supplies an ONNX path and launch file,
but no tensor ABI. The implementation does not assume that an arbitrary ONNX
file is compatible with OpenCV ViT; use `tracker_factory` for a vendor adapter.

## Testing and validation

```bash
source /opt/ros/humble/setup.bash
cd ~/NeuroBotics/eira_ws
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider -q src
python3 -m flake8 --max-line-length=99 src
colcon build --symlink-install
```

The current suite has **612 passing tests** across six packages, with no failures
or skips. A clean isolated six-package build and flake8 checks pass. The prior
orchestration baseline had 174 tests across four packages. Details are recorded in
[the validation report](docs/SAFETY_AND_VALIDATION.md).

Tests cover pure algorithms and mocked ROS topic/service/action integration,
including late planning/Nav2/IK results, stop, event identity, CLI preview,
watchdog/gate precedence, frozen cameras, stale poses, color/track association,
calibration rejection, edge geometry and launch loading. They start no hardware
nodes. Build success does not establish ARM64 model availability or physical
calibration. See [SAFETY_AND_VALIDATION.md](docs/SAFETY_AND_VALIDATION.md) for the
audit-finding mapping and remaining hardware validation requirements.
