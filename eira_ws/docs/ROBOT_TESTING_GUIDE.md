# E-AIRA: testing the robot from a fresh terminal

Author: E-AIRA maintainers.
Hardware target: Yahboom ROSMASTER M3 Pro, Jetson Orin NX, ROS 2 Humble,
Ubuntu 22.04, Python 3.10.

For a new session with command reasons and expected outcomes, begin with
[FRESH_START_TESTING.md](FRESH_START_TESTING.md), then use this document as the
complete optional-feature reference.

This guide tests the six packages in `~/NeuroBotics/eira_ws`. You do not need to
run scripts from the numbered exercise folders. Native Yahboom transport,
sensor drivers, interface packages and calibrated robot assets remain required.
These instructions describe tests to perform; they are not a record of tests
already completed on your robot.

Follow the numbered stages in order. Advance only when the stated result is
observed. Start with drive motion inhibited and the arm disabled; release those
inhibits only for the explicitly identified motion stages. Use an open, level
test area and keep the physical emergency stop within reach during motion.

## 1. Understand the terminals and stop command

Use separate terminals:

| Terminal | Purpose |
|---|---|
| T0 | Your existing vendor hardware transport/agent and raw LiDAR bringup |
| T1 | One E-AIRA master launch; keep its logs visible |
| T2 | Observation: status, plans, events, topic checks |
| T3 | Commands; keep a separate tab ready for `stop` |
| T4 | RViz, optional adapters or offline analysis when needed |

During a mission, explicitly stop with:

```bash
ros2 run eira_brain eira_cli "stop"
```

Expected: the interrupted mission reports cancellation/failure, the stop
command receives its own `DONE` acknowledgement, and final `/cmd_vel` becomes
zero. Arm hold is attempted only with fresh measured joint feedback. A software
acknowledgement does not establish mechanical stopping distance.

**Ctrl+C in a command CLI, or its `--timeout`, does not cancel the mission.**
Send the explicit stop command before shutting down the master. Stopping the
master during servo motion cannot guarantee cancellation inside the vendor driver.

## 2. Source the environment in every terminal

Replace the vendor setup path below if your image uses another workspace.
Source the workspace containing the real `arm_msgs` and `arm_interface` packages.

```bash
source /opt/ros/humble/setup.bash
source ~/yahboomcar_ws/install/setup.bash
export EIRA_WS="$HOME/NeuroBotics/eira_ws"
cd "$EIRA_WS"
```

After building in stage 3, also run:

```bash
source "$EIRA_WS/install/setup.bash"
export EIRA_PARAMS="$EIRA_WS/robot_test/params.yaml"
export EIRA_WAYPOINTS="$EIRA_WS/robot_test/waypoints.yaml"
export EIRA_MAP="$EIRA_WS/robot_test/maps/arena.yaml"
```

Run these in each terminal used for E-AIRA. Use the robot's existing
`ROS_DOMAIN_ID` consistently across the live hardware terminals; do not change
it in just one terminal. The isolated replay tests later use a separate domain.

Check:

```bash
uname -m
python3 --version
printenv ROS_DISTRO
ros2 pkg prefix arm_msgs
ros2 pkg prefix arm_interface
```

Expected on the robot: `aarch64`, Python 3.10, `humble`, and valid package paths.
If interface packages are missing, resolve/source them before arm testing.
Do not replace Jetson's CUDA/PyTorch stack with desktop Python wheels.

## 3. Build and run software tests without starting robot missions

```bash
cd "$EIRA_WS"
colcon list
colcon build --symlink-install
source install/setup.bash
python3 -m pytest -p no:cacheprovider -q src
python3 -m flake8 --max-line-length=99 src
colcon test --event-handlers console_direct+
colcon test-result --verbose
ros2 launch eira_bringup eira_master.launch.py --show-args
```

Expected: six packages (`eira_brain`, `eira_bringup`, `eira_manipulation`,
`eira_perception`, `eira_evaluation`, `eira_simulation`), successful build and
tests, no flake8 findings. The current validation baseline has 612 tests.
`--show-args` lists launch arguments without starting the robot.

If a dependency is missing, inspect the error and the package manifests. ROS
dependencies can be resolved with the following after your vendor underlay is
sourced; vendor-specific packages still come from the robot image/workspace:

```bash
rosdep install --from-paths src --ignore-src -r -y
```

Optional ASR, MediaPipe, transformer assets and local YOLO/Ollama weights need
their own compatible installation. A passing mocked test is not proof that
those optional runtime assets are installed.

## 4. Make a dedicated robot test configuration

Run once; subsequent tests should preserve your measured values:

```bash
mkdir -p "$EIRA_WS/robot_test/maps" "$EIRA_WS/results" "$EIRA_WS/bags"
cp -n "$EIRA_WS/src/eira_bringup/config/eira_params.yaml" "$EIRA_PARAMS"
cp -n "$EIRA_WS/src/eira_bringup/config/waypoints.yaml" "$EIRA_WAYPOINTS"
```

Edit `robot_test/params.yaml`. Parameters are nested under `/**`, then the node
name, then `ros__parameters`. Make these initial changes in the existing entries:

| Node | Parameter | Initial test setting |
|---|---|---|
| `llm_task_planner` | `scan_enabled` | `false`, so a failed find cannot rotate the base |
| `llm_task_planner` | `llm_timeout_s` | `30.0`, including in an older copied test YAML |
| `vision_manager` | `model_path` | Absolute path to your actual local YOLO weights |
| `vision_manager` | `continuous_mode` | `false` for demand-only inference |
| `mission_logger` | `results_dir` | Absolute `~/NeuroBotics/eira_ws/results` path |
| `mission_recorder` | `bags_directory` | Absolute `~/NeuroBotics/eira_ws/bags` path |
| `velocity_gate` | `max_linear_mps` | `0.10` for initial base trials |
| `velocity_gate` | `max_angular_radps` | `0.30` for initial base trials |

Expand `~` in the two storage paths when writing them, or use your real absolute
home path. Verify the weights exist with `ls -lh /your/actual/yolov8n.pt`.
The software's original defaults write results/bags to `~/eira_ws/`, which is
different from `~/NeuroBotics/eira_ws/`; this guide overrides those defaults.

Keep the arm's feedback, actuator-subscriber, joint-limit and calibration checks
enabled. Keep optional voice/gesture/edge/relocalization disabled initially.
After changing configuration, stop and restart the relevant launch; not all
parameters are dynamically applied.

## 5. Start native transport, then stationary E-AIRA

In T0, use your robot's existing working command/service for the base hardware
transport/agent and raw LiDAR. The exact transport command is image-specific
and is not implemented by `eira_ws`; do not invent or replace it here.

Choose one ownership arrangement:

- If only transport/raw sensors run in T0, let E-AIRA start its native
  filters/EKF, robot TF and registered camera using their installed packages.
- If your working vendor bringup already starts those components, append
  `use_base:=false use_robot_tf:=false use_camera:=false` to each hardware
  master command below. Keep their existing publishers running.

Do not run a second Nav2 stack, camera driver, TF publisher or velocity gate.
The `use_base` flag starts filters/EKF/scan processing, not the serial hardware
transport itself. `use_arm` controls IK/arm status, not the manipulation node.

In T1, start the initial stationary configuration:

```bash
ros2 launch eira_bringup eira_master.launch.py \
  params_file:="$EIRA_PARAMS" waypoints_file:="$EIRA_WAYPOINTS" \
  use_sim_time:=false use_nav:=false \
  use_arm:=false use_manipulation:=false \
  use_evaluation:=true use_recording:=false
```

In T2:

```bash
ros2 node list
ros2 param get /llm_task_planner use_sim_time
ros2 param get /llm_task_planner scan_enabled
ros2 param get /vision_manager model_path
ros2 topic info /cmd_vel --verbose
ros2 topic echo /cmd_vel --once
```

Expected: Brain, vision, safety monitor, velocity gate and logger are present;
simulation time and scan are false; final velocity is zero. Within the managed
graph, `velocity_gate` should be the sole publisher of final `/cmd_vel`. If
another controller/teleop publishes directly there, stop that competing workflow.
Read every `[dependency_missing]`/calibration/model diagnostic before advancing.

## 6. Verify sensors and geometry before using AI

Run these sequentially in T2; Ctrl+C stops each continuous observer:

```bash
ros2 topic list -t
ros2 topic hz /scan
ros2 topic hz /odom
ros2 topic hz /camera/color/image_raw
ros2 topic hz /camera/depth/image_raw
ros2 topic echo /camera/color/camera_info --once --no-arr
ros2 topic echo /camera/depth/image_raw --once --no-arr
ros2 topic echo /camera/color/image_raw --once --field header
ros2 run tf2_ros tf2_echo base_link camera_color_optical_frame
```

Expected: ongoing sensor messages, advancing timestamps, nonzero image
dimensions, finite nonzero camera focal lengths, correct optical frame, and a
plausible camera-to-base transform. Confirm actual intrinsics using an echo
without `--no-arr` on CameraInfo if its matrix is hidden.

Depth must be registered to color: corresponding rays must describe the same
object. Unequal dimensions are now resampled with scaled camera intrinsics, but
resizing alone cannot perform geometric registration. Supported metric encodings
include millimetre `16UC1`/`mono16` and metre `32FC1`. The names alone do not
prove registration. Check an object's outline in RGB and depth using RViz Image
displays or `rqt_image_view` if installed.

See `DABAI_DEPTH_DEBUG.md` for the 21x21 ROI/full-box/optional cup-height fallback,
depth CameraInfo input, 5-second advisory freshness window and `depth_debug` mode.
Estimated ranges are labelled; actual capture timestamps are preserved.

The default depth input is `/camera/depth/image_raw`. If your driver uses another
registered topic, set `vision_manager.depth_topic` and `edge_monitor.depth_topic`
and update the recorder topic list. Do not relabel unregistered depth as registered.
Topic inspection uses the standard [Humble CLI workflow](https://github.com/ros2/ros2_documentation/blob/humble/source/Tutorials/Beginner-CLI-Tools/Understanding-ROS2-Topics/Understanding-ROS2-Topics.rst).

## 7. Test planning preview, LLM and fallback

In T2, start observers before sending commands, using separate tabs as needed:

```bash
ros2 topic echo /eira/plan --field data
ros2 topic echo /eira/status --field data
```

In T3, preview without execution:

```bash
ros2 run eira_brain eira_cli --plan-only "find a red cup"
ros2 run eira_brain eira_cli --plan-only "bring me a red cup from kitchen"
```

Expected: a readable `Preview only; nothing sent to robot` message with numbered
steps; no new live mission should appear. Add `--json` for the original envelope
containing `execute: false`. Preview is a local convenience path; the complete dynamic
waypoint-grounded prompt/repair telemetry is tested through the running Brain.

Check your installed Ollama:

```bash
curl --max-time 5 http://localhost:11434/api/tags
ollama list
```

If no server runs, start your installed Ollama service or `ollama serve` in a
separate terminal. Do not start both. Confirm the model tag matches
`llm_task_planner.llm_model` (`phi3` by default). Provision a model before an
offline experiment rather than relying on an implicit download.

Put a clearly visible cup in front of the stationary robot, then:

```bash
ros2 run eira_brain eira_cli "find a cup"
```

Expected plan: a `find` action; plan fields include `source`/`planner`,
`planner_reason`, `fallback_reason`, `llm_response_ms`, `planning_latency_ms`
and `llm_attempts`. A healthy valid model result uses `llm`; an invalid or
unavailable model uses validated fallback and explains why. Elapsed values are
milliseconds, not seconds.
Debug-level `Model reply` logs retain the model answer before fence/prose cleanup;
normal output shows readable mission progress. `llm_log_raw_response=false`
disables the raw debug messages.

For a repeatable fallback test, temporarily set the copied YAML's `ollama_url`
to an unused loopback endpoint such as `http://127.0.0.1:1`, restart the same
stationary launch, and repeat `find a cup`. Expected: `fallback`, a nonempty
reason, and the supported task still works. Restore the real URL and restart.
CLI `--ollama-url` affects only preview, not the running Brain.

While fallback is forced, you can also test speech acknowledgement:

```bash
ros2 topic echo /eira/speech --field data
```

In a second terminal send `ros2 run eira_brain eira_cli "say hello"`.
The deterministic parser does not implement that request; expected output is
its `command not understood` speech acknowledgement. With `tts_enabled=true`
and a working installed `espeak`/speaker, it should be audible; otherwise the
bounded buzzer fallback is used. Observe `/beep` if testing the native buzzer
interface. This is not successful completion of the requested task. Restore
the real Ollama URL after the fallback tests.

Invalid JSON/fences, repair-once behavior and unknown-target rejection have
deterministic software coverage in `test_grounded_prompt.py`; do not depend on
prompting a real model into a particular malformed answer to test them.

For the mission queue, stay in the stationary configuration and hide the blue
cup so the first find lasts long enough to enqueue a second command:

```bash
ros2 run eira_brain eira_cli --quiet "find a blue cup"
ros2 run eira_brain eira_cli --quiet "find a red cup"
```

Expected: distinct mission IDs, a queued acknowledgement for the second
instruction, and execution in arrival order after the first completes/fails.
On a separate run enqueue the same pair and send `stop`: the queue must clear
and neither canceled/queued instruction may start later. `--quiet` only returns
after publishing; it is not a dry run.

## 8. Test detection, colors, tracking, depth and volume

Keep navigation/manipulation disabled and `scan_enabled=false` for these tests.
In observer tabs:

```bash
ros2 topic echo /eira/vision/event --field data
ros2 topic echo /target_pose
```

View `/eira/detect_image` in an Image display. Annotation is produced when a
viewer subscribes. Send commands one at a time and wait for each terminal state:

```bash
ros2 run eira_brain eira_cli "find a cup"
ros2 run eira_brain eira_cli "find a red cup"
ros2 run eira_brain eira_cli "find a blue cup"
```

Test with both colored cups visible. Expected: the requested color is selected;
the found event has matching IDs/target/color, confidence, track ID,
measurement stamp, dimensions and depth. `/target_pose` must be finite, in
`base_link`, and consistent with measured geometry: x forward, y left, z up.
Color masks depend on lighting and visible colored area; inspect the annotated
detection rather than assuming every patterned cup qualifies.

Default `continuous_mode=false` deliberately stops inference after found or
timeout and logs `idle (no active search)`. One acquisition produces a real pose;
it does not keep publishing that pose with invented new timestamps. During a
grasp, the Brain requests fresh one-shot acquisitions using optional `refresh_id`
tokens; stop/action completion cancels remaining work. Repeated keepalives do not
extend a search deadline. Idle and navigation should submit no YOLO inference.
To test persistent tracking and frozen-camera loss below, explicitly enable the
diagnostic continuous mode:

```bash
ros2 param set /vision_manager continuous_mode true
```

For tracking, slowly move one cup while keeping it visible. Expected: the
selected annotation keeps a stable ID during an uninterrupted track and pose
updates remain smooth. Briefly occlude it and remove it completely. Expected:
loss after the configured interval, then reacquisition when visible again.
Do not require the same ID after complete loss/reacquisition. Found metadata is
an acquisition event, not a per-frame trajectory stream; observe annotations
and `/target_pose` for motion.

For camera-staleness testing, keep the robot stationary and stop only the camera
source through its own supervised launch, then restart it. An existing track
must produce `lost` (for example `camera_stale`), and no stale pose should keep
driving downstream operations. A new search must timeout/fail rather than
reporting a fresh acquisition from frozen frames.

After the tracking/frozen-stream tests, restore demand mode before navigation:

```bash
ros2 param set /vision_manager continuous_mode false
```

An intentional demand-mode pause after found does not emit a spurious `lost`.

For optional depth outputs, edit the copied YAML and restart:

```yaml
# Existing vision_manager.ros__parameters entries:
publish_depth_image: true
depth_probe_u: 320
depth_probe_v: 240
```

Use pixels inside your actual image; 320/240 is only an example for 640x480.
View `/eira/depth_image`; echo `/eira/depth_distance --field data` and compare
with a measured object distance along the selected pixel ray. Disable unused
visualization outputs after testing to reduce Jetson load.

If JetPack's `tegrastats` is installed, observe it during idle, YOLO, LLM
planning and later ASR/recording trials. Record memory, CPU/GPU load and thermal
behavior. Keep model loading bounded, sensor timestamps fresh and command/stop
response usable under combined load. Reduce optional image publications,
`max_fps`/`idle_fps`, image size or ASR load before relaxing freshness checks.

With `volume_thickness_m: 0.0`, expected `volume_m3` is null, with a reason for
unobserved hidden thickness. To test the estimate, measure an object's thickness
and set that positive metre value plus `volume_shape: cuboid` or `cylinder`.
Reacquire the target. Compare projected width/height and estimated volume with
manual measurements. This is bounding geometry with a thickness prior, not a
complete 3D reconstruction or the capacity of an empty cup.

## 9. Test transformer mode separately

Stop T1 and restart its same stationary command with
`tracking_backend:=transformer`. Configure `transformer_model_path` or
`tracker_factory` in your copied YAML to the actual compatible backend.

Repeat stage 8's acquisition, motion and occlusion tests. Pass only when logs
show the transformer backend actually initialized and tracked. A model-load or
ABI failure must emit an explicit fallback diagnostic and permit YOLO operation;
that verifies graceful degradation, not successful transformer integration.
The supplied ONNX filename alone does not define a usable tensor ABI.
Return to `tracking_backend:=yolo` for the initial full-system trials.
Use `continuous_mode=true` only for the continuous tracking portion and restore
false afterwards, as in stage 8.

## 10. Prepare a real map and measured waypoints

If you already have a calibrated arena map, copy its YAML and referenced image
into `robot_test/maps/`, keeping the YAML image path valid. Set `EIRA_MAP` to it.
Do not use the repository's sample waypoint coordinates as real destinations.

If you need to build a map, stop the E-AIRA master and leave the required native
sensor/TF/odometry bringup running. Use the E-AIRA wrapper for your installed SLAM:

```bash
ros2 launch eira_bringup exercise_profiles.launch.py profile:=slam_toolbox
```

Use your already verified supervised, gated teleoperation workflow to cover the
arena. Do not run AMCL and a mapping process as competing map-to-odom sources.
Save the completed map using another terminal:

```bash
ros2 launch eira_bringup exercise_profiles.launch.py profile:=save_map \
  profile_arguments:="-f $EIRA_WS/robot_test/maps/arena"
```

Expected: `arena.yaml` and an occupancy image. Stop SLAM before the AMCL test.
Missing native SLAM packages are reported; these wrappers do not implement a
new mapping stack. See stage 22 for the separate keyboard/profile workflow.

In T1, restart hardware master with navigation but without arm/manipulation:

```bash
ros2 launch eira_bringup eira_master.launch.py \
  params_file:="$EIRA_PARAMS" waypoints_file:="$EIRA_WAYPOINTS" \
  map:="$EIRA_MAP" use_sim_time:=false use_rviz:=true \
  use_arm:=false use_manipulation:=false \
  use_evaluation:=true use_recording:=false
```

Apply the external-driver flags from stage 5 if appropriate. Nav2 parameters
come from installed `M3Pro_navigation` by default. If necessary, pass your
calibrated native YAML through `nav_params_file:=/absolute/path/nav2.yaml`;
`params_file` is the E-AIRA node YAML, not the Nav2 YAML.

Set RViz Fixed Frame to `map`, add Map/LaserScan/RobotModel, and use **2D Pose
Estimate** to place the robot at its measured current map pose. Check that scan
walls overlay map walls. Confirm:

```bash
ros2 lifecycle get /amcl
ros2 lifecycle get /controller_server
ros2 action list -t
ros2 action info /navigate_through_poses
ros2 run tf2_ros tf2_echo map base_link
```

Expected: active localization/controller, one available navigation action
server, and a coherent map-to-base transform. Confirm native node names with
`ros2 node list` if your installed Nav2 configuration namespaces them.
The RViz initialization workflow is described in the
[Nav2 quickstart](https://docs.nav2.org/lyrical/getting_started/quickstart/quickstart/);
use your installed Humble stack and this workspace's launch commands.

In T4:

```bash
ros2 run eira_brain waypoint_recorder --ros-args \
  -p waypoints_file:="$EIRA_WAYPOINTS"
```

Use RViz **Publish Point**, click a free base approach position, then type its
name in the recorder terminal. Record `home`, `kitchen`, and `table1` as needed.
This tool records x/y, defaulting yaw to **0.0**. Manually set the measured yaw
in radians in the same YAML; it does not record a dragged orientation arrow.
Place base goals with clearance for the chassis and arm, not at the cup center
or inside a table obstacle. Preserve `frame: map` and the `waypoints` dictionary.
Delete/replace unmeasured sample destinations in your copied file.

```bash
ros2 run eira_brain eira_cli --list-waypoints --waypoints-file "$EIRA_WAYPOINTS"
ros2 param get /llm_task_planner waypoints_file
```

Expected: both reference the same file. The Brain reloads waypoints per mission.

## 11. Test base navigation, cancellation and recovery

Release the base motion inhibit only after localization and stop checks pass.
Keep the arm disabled. Observe `/eira/status`, `/eira/motion/event` and `/cmd_vel`.

```bash
ros2 run eira_brain eira_cli "go to kitchen"
ros2 run eira_brain eira_cli "go home"
ros2 run eira_brain eira_cli "go to kitchen and then go home"
```

Run one at a time. Expected: correct waypoint goals, bounded final velocity,
correlated `action_started`/`action_finished`, then mission `DONE`.
`go home` navigates the base; it is not an arm-homing command.
After each successful navigate, expect `NAV_SETTLE` for 3 seconds with zero
velocity before the next action. Failed navigation gets two additional attempts
with `NAV_RETRY_WAIT` for 10 seconds between attempts. Stop/heartbeats must remain
responsive throughout both waits. High, missing, invalid or stale AMCL covariance
produces the warning `AMCL uncertainty high, navigation may fail` before dispatch;
the check is advisory so external localization remains usable. Configure
`amcl_check_enabled=false` when deliberately using a non-AMCL localizer.

For cancellation, send a navigation command with `--quiet`, then stop while it
is active from another terminal:

```bash
ros2 run eira_brain eira_cli --quiet "go to kitchen"
ros2 run eira_brain eira_cli "stop"
```

Expected: old goal canceled, zero final velocity, no delayed acceptance/result
restarts that mission. Repeat stopping during the observed `PLANNING` state;
after the LLM timeout/response window, the canceled plan must still not execute.
Keep the test area clear; do not assume planning always lasts long enough to
catch with manual timing. Deterministic race coverage is in software tests.

For search recovery, re-enable `scan_enabled` in YAML, restart, and issue a find
with the cup initially just outside the view but within a safe scan arc. Expected:
bounded scan/retry events and acquisition if the cup enters view. Then remove the
cup: retries/scans must terminate as failure, leaving zero velocity. This test
can rotate the base. Do not use a person as an obstacle or test at a drop-off.

## 12. Verify arm prerequisites before commanding the arm

Stop the master, keep the base stationary, and inspect your actual arm model:

- Configure the real `arm_base_frame` with correct camera/base/arm TF. Alternatively
  enter measured mount offsets/yaw and set `static_mount_calibrated=true` only
  after measurement. The uncalibrated defaults intentionally reject a grasp.
- Verify six joint limits and the configured `init_joints`, `transport_joints`,
  gripper open/close angles and runtimes against your arm's safe poses.
- Trace `/Curjoints` to its producer. A commanded-angle echo is not an encoder.
  Keep `joint_feedback_is_measured=false` unless its provenance is measured;
  do not change it merely to make a hold test pass.
- Keep `require_joint_feedback=true` and `require_actuator_subscribers=true`.
  Software joint convergence and true object contact are separate observations.

Restart with manipulation/IK enabled, navigation initially disabled:

```bash
ros2 launch eira_bringup eira_master.launch.py \
  params_file:="$EIRA_PARAMS" waypoints_file:="$EIRA_WAYPOINTS" \
  use_sim_time:=false use_nav:=false \
  use_arm:=true use_manipulation:=true \
  use_evaluation:=true use_recording:=false
```

If native IK/arm status are already running, use `use_arm:=false` while retaining
`use_manipulation:=true`. Supply `hardware_params_file` for your measured native
`common.yaml` when it is not the installed default. Inspect any native startup
behavior with the arm workspace clear before releasing its power inhibit.

```bash
ros2 service list -t
ros2 service type /get_kinemarics
ros2 interface show arm_interface/srv/ArmKinemarics
ros2 topic info /arm6_joints --verbose
ros2 topic info /arm_joint --verbose
ros2 topic echo /Curjoints --once
ros2 topic echo /eira/manipulation/event --field data
```

Expected: the exact `/get_kinemarics` spelling, existing vendor service type,
real subscribers to both arm command topics, and fresh plausible joint reports.
Check TF to the configured actual arm frame using `tf2_echo` before proceeding.

## 13. Test arm home, grasp, hold and release

The following direct home test moves the arm. Run with Brain idle and its queue
empty, after checking the calibrated `init_joints` pose:

```bash
ros2 topic pub --once /eira/manipulation/request std_msgs/msg/String \
  '{data: "{\"command\":\"home\",\"mission_id\":\"manual-home-001\",\"action_id\":\"1\"}"}'
```

Expected: `homed` with those IDs after runtime and required reported convergence.
Use a new mission ID if you repeat the test; completed requests are deduplicated.
This direct diagnostic bypasses Brain mission planning and is not a benchmark.

Place a light, empty, robust cup at a measured reachable pose. Initial grasping
can also move the base for PID alignment. Observe pose, velocity and events:

```bash
ros2 run eira_brain eira_cli "pick up a red cup"
```

Expected sequence: find -> fresh correlated target -> optional confirmation ->
bounded base alignment -> IK -> gripper open -> reach -> close -> transport ->
`grasped` -> `DONE`. Confirm actual holding by inspection/sensor evidence.
`object_contact_verified=false` is expected without an actual contact source;
the software does not infer a successful hold from elapsed servo time.

With a suitable receiving area under the arm:

```bash
ros2 run eira_brain eira_cli "release"
```

Expected: configured release/transport pose, opening and return to home,
`released`, then `DONE`. Do not assume release happens at the current pose.

For stop/hold, use a supervised calibrated low-risk move and send `stop` during
the arm sequence. Expected: sequence and pending IK invalidated, base zero,
`stopped` event showing whether `arm_hold_sent` was possible. A missing measured
feedback source must not generate a fabricated measured hold. If IK is absent
or a response never arrives, the bounded service/request timeout must fail the
action rather than hang; inject that fault in simulation or a stationary
supervised setup, not while carrying an object.

## 14. Test calibrated width control, color sorting and complete fetch

For width-based grip, measure your own safe `[width_metres, servo_degrees]`
pairs across the intended object-width range. Put their JSON array in
`gripper_width_table` and select `gripper_mode: width`; restart. The provided
example file intentionally has no factory calibration values.

Reacquire a measured cup and grasp. Compare the issued gripper angle with your
table interpolation. An out-of-range/missing width must fail; do not widen the
table with invented points to bypass rejection. Compare against `gripper_mode:
fixed` only with physically safe objects and separately recorded conditions.

For color-bin placement, set `sort_poses` to a JSON object mapping `red`, `blue`,
etc. to your measured six-angle bin poses. A color-specific pose is used during
release when calibrated destinations exist. Empty `sort_poses` uses the standard
transport/release pose; it is not proof of color-bin placement. Ensure every
requested color has a valid calibrated pose.

Restart the master with both navigation and manipulation enabled, using the
same measured files and your chosen external-driver flags:

```bash
ros2 launch eira_bringup eira_master.launch.py \
  params_file:="$EIRA_PARAMS" waypoints_file:="$EIRA_WAYPOINTS" \
  map:="$EIRA_MAP" use_sim_time:=false use_rviz:=true \
  use_evaluation:=true use_recording:=true
```

Reinitialize localization if necessary. Inspect a preview first, then run one
mission at a time with the cup initially visible for sorting:

```bash
ros2 run eira_brain eira_cli "sort red cup into table1"
ros2 run eira_brain eira_cli "sort blue cup into table1"
ros2 run eira_brain eira_cli "bring me a red cup from kitchen"
```

The sort fallback is find -> grasp -> navigate to `table1` -> release using the
color pose when configured. A fetch navigates to `kitchen`, finds and grasps the
requested object, returns to the actual pose captured at mission start
(`mission_start`), then releases. This pose is independent of the saved `home`
waypoint. Monitor the live plan: the Brain executes
validated actions immediately. A preview is not an approval gate or a frozen
plan; generated plans can differ between calls. Avoid ambiguous commands that
do not name the source waypoint for a fetch test.
The color context must be retained within that sort/fetch mission. A separate
later `release` mission uses the standard release pose; it does not inherit the
previous mission's detected color.

Repeat fetch with another class supported by your loaded model, such as
`bring me a bottle from kitchen`; there is no fixed cup target. Follow
[FETCH_MISSION_TESTING.md](FETCH_MISSION_TESTING.md) for target propagation,
navigation order, return-pose and missing-object checks.

## 15. Test gesture detection and confirmation

First add `use_gestures:=true` to a restarted stationary launch with manipulation
disabled. Echo `/eira/gesture --field data`, show a stable OK gesture and then
Thumb_down. Expected: debounced, correlated events with cooldown; a missing
MediaPipe build reports unavailability. Thumb_down also issues a Brain stop by
default, so no other mission should be active during initial recognition tests.

Then set `grasp_executor.require_gesture_confirmation: true`, restart with
manipulation, and issue `pick up a red cup`. When the target is acquired and
the arm executor is waiting for confirmation:

1. Show OK: alignment/grasp may proceed.
2. On a separate trial, show nothing: confirmation times out and fails safely.
3. On another trial, show Thumb_down: cancellation and base zero are expected.

Always inspect the hand recognizer's event and active mission/action IDs.
An injected String alone would test the control interface, not camera-based
gesture recognition. Reset the parameter if confirmations are no longer wanted.

## 16. Test transcript input, file ASR and microphone ASR

Start with the stationary `find` configuration. Direct transcript input needs
no ASR installation:

```bash
ros2 topic pub --once /eira/voice std_msgs/msg/String "{data: 'find a red cup'}"
```

Expected: an ordinary Brain mission. Direct transcripts do not require the wake
word. This validates the subscriber, not Whisper or microphone capture.

Install/provision the local Whisper model and optional audio dependencies for
your ARM64 environment. Configure `voice_input.model`, `model_dir`, `device`
and language. Default `tiny.en` expects local weights; no automatic download is
attempted. Start with CPU ASR and conservative vision rates to observe load.

Restart master with `use_voice:=true`, leaving `microphone_enabled=false`.
Record a local WAV saying **“Eira, find a red cup.”** Then:

```bash
ros2 topic echo /eira/voice/event --field data
```

In another terminal:

```bash
ros2 topic pub --once /eira/audio_file std_msgs/msg/String \
  "{data: '/absolute/path/eira_find_red_cup.wav'}"
```

Expected: ready/transcribed diagnostics, transcript beginning with the configured
wake word, stripped command on `/eira/voice`, then a mission. A transcript that
does not start with `eira` is not forwarded with the default wake-word setting.

Finally set `voice_input.microphone_enabled: true`, restart and repeat aloud.
Verify the selected system microphone, signal level and emitted transcript.
With `use_voice` master launch, edit the `voice_input` selector, not just the
separate `voice_activation` alias. Test negative/silent audio and a missing file:
there should be a diagnostic and no unintended mission. Keep manual stop
available independently of voice recognition.

## 17. Test floor-edge protection

First calibrate `floor_z_m`, camera TF, corridor dimensions and depth registration.
With the chassis stationary and physically restrained, add `use_edge:=true`
to the master and observe:

```bash
ros2 topic echo /eira/safety/edge --field data
ros2 topic echo /eira/motion/event --field data
ros2 topic echo /cmd_vel
```

Expected on a visible calibrated level floor: enough valid corridor samples
and `blocked=false`. Missing/stale depth or insufficient ground evidence must
produce blocked/unknown behavior and zero gated velocity. The feature is not
working correctly if it always blocks on your normal floor.

Test a drop-off only with the base fixed in place or on a secured test fixture;
present a safe representative scene to the depth camera. Expected:
`blocked=true`, gate revocation and zero velocity. Never drive toward stairs
to discover whether it works. After clearance returns, send a new mission;
clearing the condition must not revive a revoked mission by itself.

## 18. Test visual relocalization

Measure a fiducial marker's size and complete map-frame pose and populate a
copy of `marker_map.example.yaml`. Configure `marker_map_file`, dictionary,
thresholds and actual camera TF. Add `use_relocalization:=true` to the restarted
master. An empty marker map is not a working ArUco localization setup.

Observe `/eira/localization/event`, `/amcl_pose` and `/initialpose`. First verify
the marker is detectable with the robot stationary and healthy localization:
no unnecessary correction should be published. Then perform a supervised
stationary localization-recovery experiment using a measured starting pose.
A recent confident visual estimate may correct AMCL only when its covariance
exceeds the configured uncertainty thresholds. Verify the correction against
the measured pose, and verify stale/wrong-frame/too-distant estimates are rejected.

Do not publish invented poses/covariances into the live AMCL graph to make the
test pass. If natural controlled recovery cannot be established yet, validate
the gating rules with mocked tests and label the hardware feature untested.
This node does not itself command navigation or guarantee a lost robot will
reach a marker. External tag localization can instead supply a valid measured
`/eira/visual_pose`.

## 19. Test rosbridge/mobile commands

Restart stationary master with `use_rosbridge:=true`. Default bind is localhost
on port 9090. On a client with SSH access, use a tunnel where supported:

```bash
ssh -L 9090:127.0.0.1:9090 ROBOT_USER@ROBOT_IP
```

Connect a rosbridge-compatible WebSocket client to `ws://127.0.0.1:9090` through
that tunnel. Send these frames in order:

```json
{"op":"subscribe","id":"status","topic":"/eira/status","type":"std_msgs/msg/String"}
{"op":"advertise","id":"commands","topic":"/eira/command","type":"std_msgs/msg/String"}
{"op":"publish","topic":"/eira/command","msg":{"data":"find a red cup"}}
```

Expected: the same mission/status behavior as CLI input. Then send `stop` as
the command data. Mobile clients without SSH support need your explicitly
configured network endpoint. The bridge allowlist exposes commands, transcripts,
status/plans and speech; it is not a remote arm/velocity/service control panel.

## 20. Test evaluation, ground-truth labels and reports

Ensure master has `use_evaluation:=true`; do not start a second logger using the
same archive prefix. Send one successful find and one intentionally unsuccessful
find with scans disabled. Wait for each terminal state and the logger flush.

```bash
ls -lh "$EIRA_WS/results"
ros2 param get /mission_logger results_dir
```

Expected: UTC daily `mission_log_YYYYMMDD.csv` and `.json`, CSV headers, distinct
mission IDs, planner/reason/times, actions/attempts, success and error reason.
Use a viewer/text tool to verify successful and failed records. Keep setup,
simulation and hardware evidence distinguishable.

After a real grasp outcome is observed, copy the exact grasp `mission_id` and
`action_id` from the event. Replace the placeholders below and label both
positive and negative results honestly:

```bash
ros2 topic pub --once /eira/evaluation/grasp_truth std_msgs/msg/String \
  '{data: "{\"mission_id\":\"ACTUAL_ID\",\"action_id\":\"ACTUAL_GRASP_ACTION_ID\",\"object_held\":true,\"source\":\"operator video review\"}"}'
```

Use `false` for an observed failed hold. Define in advance what counts as held
and when it is checked. Unknown labels remain excluded from grasp accuracy.

Choose an actual generated CSV filename; do not type `YYYYMMDD` literally:

```bash
ros2 run eira_evaluation metrics_calculator \
  "$EIRA_WS/results/mission_log_YYYYMMDD.csv" \
  --environment hardware --output-dir "$EIRA_WS/results/manual_report"
```

Expected: `summary.txt`, `summary.json`, `summary.tex` and labelled/grid PNG
charts. Inspect task/action rates, planning/LLM/perception latency, verified
grasp accuracy, active-operation MTBF and recovery success. With no observations,
or no failures for an MTBF estimate, NA/censoring is expected. LaTeX tables use
`booktabs`. Task success is controller-reported completion, not independent
proof of physical delivery. See the evaluation README for denominators.

For the automated benchmark, first use a single find trial:

```bash
ros2 run eira_evaluation benchmark --command "find a red cup" \
  --iterations 1 --start-waypoint home \
  --results-dir "$EIRA_WS/results" --environment hardware
```

This still navigates the base to `home` before the find. To test only collection
while stationary, explicitly add `--skip-reset`; that does not validate reset.
After independent reset/mission tests pass, increase to 3, then your planned N:

```bash
ros2 run eira_evaluation benchmark \
  --command "bring me a red cup from kitchen" --iterations 20 \
  --start-waypoint home --results-dir "$EIRA_WS/results" --environment hardware
```

Expected: reset and trial IDs separated, summary table/charts, campaign manifest,
and bounded stop on timeout. A failed reset aborts. Resets physically navigate
the base; they do not reset cup location or arm state. The runner has no manual
scene-reset pause between trials: use one-iteration campaigns when an operator
must reset the scene, or establish a repeatable scene-reset procedure before N
fetches. Repeatedly released/moved cups otherwise define a different experiment.
Do not send voice/mobile/CLI missions during a benchmark.

## 21. Test mission bags and offline replay

Restart the master with `use_recording:=true`. Observe:

```bash
ros2 topic echo /eira/recording/status --field data
```

Send a modest-duration find/navigation mission already verified above. Expected:
recording -> discovered/ready when observed -> complete/incomplete diagnostics
after termination. Wait for finalization before copying or opening the bag:

```bash
ls -lt "$EIRA_WS/bags"
ros2 bag info "$EIRA_WS/bags/ACTUAL_MISSION_DIRECTORY/bag"
cat "$EIRA_WS/bags/ACTUAL_MISSION_DIRECTORY/mission.json"
```

Verify compressed RGB, depth/intrinsics, scan, TF, velocity, plans/status and
other configured topics actually have samples. Very short missions can finish
before discovery. Inspect startup/discovery gaps and capture result in the
manifest; sidecars preserve event boundaries, not missing camera frames.

Safe default analysis remaps every recorded topic under `/eira/replay`:

```bash
ros2 run eira_brain mission_replayer \
  "$EIRA_WS/bags/ACTUAL_MISSION_DIRECTORY" --dry-run
ros2 run eira_brain mission_replayer \
  "$EIRA_WS/bags/ACTUAL_MISSION_DIRECTORY" --decode-color
```

Observe `/eira/replay/eira/status` and replay image topics. This tests playback;
it does not automatically run vision/arm again. Original actuator commands
remain remapped. Do not use raw `ros2 bag play` against the live hardware graph
for a bag that contains original commands.

For actual vision reprocessing, stop the physical master and use an unused
domain different from the physical domain. Example below assumes 42 is unused
and differs from your normal domain. In a new T4, source stage 2 and run:

```bash
export ROS_DOMAIN_ID=42
export ROS_LOCALHOST_ONLY=1
ros2 run eira_perception vision_manager --ros-args \
  --params-file "$EIRA_PARAMS" -p use_sim_time:=true
```

In a separate playback terminal retain the original parent domain, source
stage 2, and run:

```bash
ros2 run eira_brain mission_replayer \
  "$EIRA_WS/bags/ACTUAL_MISSION_DIRECTORY" \
  --mode isolated --domain-id 42 --clock --decode-color
```

In another domain-42 observer echo `/eira/vision/event`. The replay publishes
recorded sensor/TF/search inputs on original names inside the separate domain;
the decoder restores RGB, and `/clock` establishes recorded time. Start nodes
before playback. Playback after mission start may lack startup TF/CameraInfo;
inspect samples, stamps and manifest rather than relaxing validity checks.

Arm recomputation additionally requires a simulation bridge, simulated measured
feedback and `grasp_executor` in that unused domain; use `--include-requests`
only there. Recorded physical actuator outputs are never emitted on original
names in isolated mode. Do not launch physical drivers in the replay domain.

## 22. Test the remaining E-AIRA exercise adapters

These are optional alternative workflows, not extra nodes to pile onto the
master. Stop the master and leave the minimum required native hardware/TF
bringup running. Motion profiles own their own gate. Non-motion viewers can
observe an existing stream, but do not duplicate its driver or TF publisher.

```bash
ros2 launch eira_bringup exercise_profiles.launch.py profile:=keyboard \
  params_file:="$EIRA_PARAMS"
```

In an attached second terminal:

```bash
ros2 run yahboomcar_ctrl yahboom_keyboard --ros-args \
  -r cmd_vel:=/eira/cmd_vel/exercise
```

Expected: supervised native controls, commands through the gate, and zero after
input timeout. Native keyboard/joystick tools may also control the arm; read
their controls before pressing keys. Launch does not forward interactive stdin.

For bounded line/LiDAR skills:

```bash
ros2 launch eira_bringup exercise_profiles.launch.py profile:=sensor_skills \
  params_file:="$EIRA_PARAMS"
```

Then issue one five-second request while observing `/eira/skill/event` and velocity:

```bash
ros2 topic pub --once /eira/skill/request std_msgs/msg/String \
  '{data: "{\"command\":\"lidar_track\",\"mission_id\":\"skill-001\",\"action_id\":\"1\",\"duration_s\":5}"}'
```

Repeat with new IDs for `lidar_guard`, `lidar_avoid`, and `line_follow`. Guard
rotates/beeps; track regulates standoff; avoidance uses valid LiDAR sectors;
line following requires your calibrated HSV floor line. Use a fixed safe object,
not a person, for initial tracking. Expected: bounded velocities/duration,
stop-on-stale/unknown inputs and explicit result. No request should run forever.

Other profile acceptance criteria:

| Profile | What to verify |
|---|---|
| `joystick` | Native joystick/joy input, expected controls, timeout stop through gate |
| `calibrate_linear`, `calibrate_angular` | Actual measured distance/angle versus reported values; follow native tool prompts |
| `arm_calibration` | Native fiducial calibration with real target/mount; preserve measured output |
| `robot_display` | Actual model and link alignment; avoid duplicate robot TF |
| `lidar_view`, `lidar_fusion` | Correct scans/frames and native dual-scan overlap, without duplicate merger |
| `gmapping`, `cartographer`, `slam_toolbox` | Run one mapper; consistent map and valid saved assets |
| `cartographer_localization` | Real recorded posegraph and native localization parameters |
| `rtabmap_mapping`, `rtabmap_localization` | Valid registered RGB-D/odom and database; do not compete with AMCL |
| `tag_recording` | Measured tag poses in the correct map frame |
| `camera`, `depth_tools`, `perception`, `gesture`, `edge`, `manipulation` | Standalone forms of the corresponding stages above |

For RTAB-Map localization, pass the actual database via
`profile_launch_arguments` and use master `use_nav_localization:=false` if its
navigation stack runs alongside. The profile named `simulation` is the old
exercise model; use the new `eira_simulation` package in stage 23 for research.
The exact 01–33 mapping is in `EXERCISE_INTEGRATION.md`; no exercise folder
execution is required by this guide.

## 23. Test the research simulator separately from the robot

Stop hardware mission processes. Run simulation on a development machine or an
unused localhost-only ROS domain with no physical drivers. Source the vendor
interface/model underlay and E-AIRA overlay there; message definitions are
required, motor drivers are not.

```bash
export ROS_DOMAIN_ID=43
export ROS_LOCALHOST_ONLY=1
ros2 launch eira_simulation sim_bringup.launch.py \
  perception_mode:=ground_truth seed:=42 randomize:=false \
  output_dir:="$EIRA_WS/results/sim_oracle_seed42"
```

Use a domain different from the hardware/replay domain; source and set it in
each simulation command terminal. Expected: room, robot, LiDAR/RGB-D, simulated
TF/odom/joint feedback, Nav2 and E-AIRA, all using simulation time. Check `/clock`,
`/scan`, `/camera/color/image_raw`, `/joint_states`, `/get_kinemarics` and the
navigation action. This explicitly labelled oracle tests control contracts,
not detector accuracy or actual object contact.

After that launch works, stop it and test learned perception with your model:

```bash
ros2 launch eira_simulation sim_bringup.launch.py \
  yolo_model:=/absolute/path/yolov8n.pt seed:=42 randomize:=true \
  output_dir:="$EIRA_WS/results/sim_yolo_seed42"
```

Compare `condition.json` and generated assets across seeds for lighting, cup
position and metric sensor noise; the same configured seed should reproduce
the generated condition. Conditions are resampled per launch, not per mission.
A plain simulated cylinder may not be recognized as a cup by photographic
COCO weights. Report that failure or train a suitable detector; do not mix
oracle and learned-perception results. The simulator supplies kinematic base/arm
models, not a validated gripper-contact model. See its README for display,
dependencies and model limitations; full end-to-end runtime remains to be
validated on your configured machine.

## 24. Exercise regression tests and save acceptance evidence

Race conditions and malformed/stale messages are best tested deterministically
without forcing faults during a real lift. These targeted suites start no
physical drivers or missions:

```bash
python3 -m pytest -q src/eira_brain/test/test_mission_safety.py \
  src/eira_brain/test/test_velocity_gate.py \
  src/eira_brain/test/test_grounded_prompt.py
python3 -m pytest -q src/eira_perception/test src/eira_manipulation/test
python3 -m pytest -q src/eira_evaluation/test \
  src/eira_brain/test/test_mission_recording.py src/eira_simulation/test
```

They cover planning-stop races, stale Nav2/IK results, lock/state behavior,
event correlation, command lease/heartbeat/safety precedence, frozen sensors,
malformed responses, recording boundaries and replay isolation. Do not publish
fake ownership, heartbeat, TF, found events or joint feedback into the live
robot graph to reproduce these cases.

For a ROS-level watchdog integration demonstration, use an unused domain and
remap the gate's final output away from actuators. In every test terminal set
`ROS_DOMAIN_ID=44` and `ROS_LOCALHOST_ONLY=1`, assuming 44 is unused. Start a
heartbeat publisher first in one terminal:

```bash
ros2 topic pub -r 2 /eira/heartbeat std_msgs/msg/Empty '{}'
```

In a second terminal, start only the gate with its output redirected:

```bash
ros2 run eira_brain velocity_gate --ros-args \
  -r /cmd_vel:=/eira/test/cmd_vel
```

After heartbeat discovery, explicitly select the test owner in another terminal:

```bash
ros2 topic pub --once /eira/motion_owner std_msgs/msg/String \
  '{data: "{\"owner\":\"brain\",\"mission_id\":\"gate-test-001\",\"action_id\":\"1\"}"}'
```

Then publish input; in another terminal observe `/eira/test/cmd_vel`:

```bash
ros2 topic pub -r 10 /eira/cmd_vel/brain geometry_msgs/msg/Twist \
  '{linear: {x: 0.05}, angular: {z: 0.0}}'
```

Expected: test output forwards 0.05 m/s. Stop only the Twist publisher:
test output goes zero after the default 0.5 s command lease. Restart it, then
stop heartbeat: output goes zero after the default 5 s heartbeat timeout,
and resuming heartbeat alone must not restore ownership. Restart the gate for
a new independent case. Inspect `ros2 topic info /cmd_vel --verbose` inside this
test domain to confirm the gate publishes only the redirected test output.
Close all test-domain terminals afterwards; keep the normal hardware domain
unchanged.

Record acceptance for every stage as PASS/FAIL/NOT TESTED with date, software
revision, platform/model versions, configuration path/hash, mission ID, observed
behavior and evidence filename. Preserve failed trials as well as successes.
For final paper trials retain parameter/waypoint/map/calibration files, actual
prompts/model identifiers, CSV/JSON, bags, grasp annotations and reset protocol.
The adjacent `RESEARCH_PROTOCOL.md` explains experimental denominators and
reporting limits.

## Troubleshooting by symptom

| Symptom | First checks |
|---|---|
| `Package ... not found` | Source Humble, correct vendor underlay, then this workspace overlay in that terminal |
| No planner subscription | Master running, same DDS domain, no second stale overlay |
| Camera visible but no target pose | Actual YOLO weights, class/color, registered finite depth, intrinsics, measurement-time camera TF |
| Camera/pose stale | Timestamp clock agreement, Jetson load, sensor rate, inference backlog; hardware uses `use_sim_time=false` |
| LLM always falls back | `/api/tags`, actual model tag, URL, timeout and raw diagnostics; CLI preview flags do not configure the node |
| Navigation unavailable | Map/image path, native Nav2 params, lifecycle activation, correct action server, initialized AMCL |
| Nonzero source but zero final velocity | Motion owner, heartbeat, source age, enabled edge state, stop revocation; inspect `/eira/motion/event` |
| Unexpected `/cmd_vel` movement | Find competing publishers; stop unmanaged controllers before continuing |
| IK/arm TF rejected | Exact service/type, actual arm frame/mount calibration, reachable target, finite joint limits |
| Joint convergence timeout | Real feedback source/rate, angle mapping, safe target and driver subscribers; do not disable checks to hide it |
| Gesture never confirms | Actual MediaPipe backend, OK recognition, confirmation state and matching IDs |
| ASR transcript but no mission | Default wake word must be at start, correct `voice_input` selector, model/audio source |
| Edge always blocks | Actual floor height/TF, valid corridor coverage, registration, frozen depth |
| Missing results/bags | Configured directory versus original `~/eira_ws` default, disk reserve, recorder status, finalization |
| Metrics show NA | Missing eligible trials/verified grasp labels, no recovery or failures observed; inspect denominators |
| Replay yields no new detections | Correct isolated domain, `/clock`, JPEG decoder, recorded search/TF/intrinsics, nodes started before playback |

## Shutdown

1. Send `eira_cli "stop"` and verify zero velocity and arm state.
2. Wait for recorder finalization/metadata and logger flush.
3. Ctrl+C the master and optional adapters; stop native hardware through its
   normal shutdown procedure.
4. Preserve experiment artifacts, then power down using the robot's procedure.
