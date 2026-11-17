# E-AIRA fresh-start testing: what to run and why

Author: E-AIRA maintainers.
Hardware target: ROSMASTER M3 Pro, Jetson Orin NX, Dabai DCW2,
Ubuntu 22.04, ROS 2 Humble, Python 3.10.

Follow this guide after updating `~/NeuroBotics/eira_ws`. The first goal is a
**stationary cup detection with a verified depth source**. Navigation, arm motion
and complete missions follow after their prerequisites pass.

If RViz shows raw RGB but no object boxes, follow the isolated
[YOLO/RViz diagnostic procedure](YOLO_RVIZ_DIAGNOSTICS.md) first. It distinguishes
the annotated detector topic from raw RGB and tests detection without mission motion.

Fresh start means a new test session, not a factory reset. Preserve your map,
waypoints, servo limits, arm calibration, model weights and vendor installation.
Do not delete build/install directories or reset Git to follow this guide.
The fixed `logger.info(format_status(payload))` call is already in the source
and protected by regression tests; no manual logger edit is needed.

This guide assumes the robot's working Humble/vendor image is installed. It
does not reinstall Ubuntu/JetPack or replace Yahboom drivers. No scripts from
the numbered exercise folders are required.

## 0. Prepare the robot and terminals

Initially inhibit wheel motion and keep the arm disabled. Use a clear, level
area and keep the physical emergency stop accessible during later motion tests.

Run the hardware commands on the Jetson, using its desktop or your normal SSH
connection. From a laptop, an SSH session can be opened with:

```bash
ssh ROBOT_USER@ROBOT_IP
```

**Why:** opens a shell on the actual robot instead of testing a different
computer. Replace both placeholders with your robot's real login and address.
RViz needs a working desktop/display; plain headless SSH does not provide one.
For launches below using `use_rviz:=true`, use a connected desktop or an already
configured remote RViz station. Set that flag false on a headless robot.

| Terminal | Purpose |
|---|---|
| T0 | Existing native hardware transport/agent and required raw sensors |
| T1 | One E-AIRA master launch |
| T2 | Read-only checks and event observers |
| T3 | Commands; keep an extra tab ready for stop |
| T4 | RViz or additional observers |

Once the master runs, stop a mission with:

```bash
ros2 run eira_brain eira_cli "stop"
```

**Why:** explicitly invalidates planning, cancels navigation and requests an arm
stop. Closing the CLI, Ctrl+C in the CLI, or a CLI timeout does not cancel a
mission. A software acknowledgement does not establish mechanical stopping
distance; retain the physical emergency stop.

## 1. Load ROS and the vendor environment in T1

Replace the example vendor path with the actual installed workspace on your
robot. It must provide the real `arm_msgs`, `arm_interface` and native packages.

```bash
source /opt/ros/humble/setup.bash
source "$HOME/yahboomcar_ws/install/setup.bash"
export EIRA_WS="$HOME/NeuroBotics/eira_ws"
cd "$EIRA_WS"
```

| Command | Reason | Expected result |
|---|---|---|
| First `source` | Loads Humble tools, Python packages and libraries | No file-not-found error |
| Vendor `source` | Makes the existing robot interfaces available | No error; use your actual vendor path |
| `export EIRA_WS=...` | Gives later commands a consistent workspace path | Your current `eira_ws` source directory |
| `cd "$EIRA_WS"` | Selects the workspace colcon should build | Shell is inside `eira_ws` |

Check the platform and interface discovery:

```bash
uname -m
python3 --version
printenv ROS_DISTRO
ros2 pkg prefix arm_msgs
ros2 pkg prefix arm_interface
```

| Command | Reason | Expected result |
|---|---|---|
| `uname -m` | Confirms target architecture | `aarch64` on the Jetson |
| Python version | Confirms the Humble Python environment | Python 3.10 |
| ROS distribution | Detects an unsourced/wrong ROS environment | `humble` |
| Both package-prefix checks | Confirms actual vendor definitions are discoverable | Valid installed package directories |

If interface discovery fails, correct the underlay before arm tests. Do not
substitute fabricated message types or desktop CUDA/PyTorch wheels.

## 2. Build and select the current E-AIRA code

```bash
colcon list
colcon build --symlink-install
source "$EIRA_WS/install/setup.bash"
ros2 pkg prefix eira_brain
ros2 pkg executables eira_bringup
ros2 launch eira_bringup eira_master.launch.py --show-args
```

| Command | Reason | Expected result |
|---|---|---|
| `colcon list` | Checks package discovery | Six E-AIRA packages |
| Build | Installs the updated code and executable entry points | Six packages finish successfully |
| Overlay `source` | Selects this build in the current terminal | No setup error |
| Brain prefix | Detects an older overlay still being selected | Path under this workspace's `install/`, not another workspace or `/tmp/` |
| Executable listing | Checks node registration | Includes `arm_state_relay` and `visualization_markers` |
| `--show-args` | Checks launch loading without starting the robot | Lists the available switches |

For missing resolvable ROS dependencies, after sourcing the vendor underlay:

```bash
rosdep install --from-paths src --ignore-src -r -y
```

**Why:** installs available dependencies described by package manifests.
Vendor-specific packages and compatible model/audio libraries still come from
the robot installation; inspect unresolved dependencies rather than replacing
the native driver stack.

## 3. Run software checks before physical testing

```bash
python3 -m pytest -p no:cacheprovider -q src --ignore=src/eira_simulation
python3 -m flake8 --max-line-length=99 src
colcon test --packages-select eira_brain eira_bringup eira_manipulation \
  eira_perception eira_evaluation --return-code-on-test-failure \
  --test-result-base "$EIRA_WS/robot_test/fresh_start/test_results" \
  --event-handlers console_direct+
colcon test-result \
  --test-result-base "$EIRA_WS/robot_test/fresh_start/test_results" --verbose
```

| Command | Reason | Expected result |
|---|---|---|
| Source `pytest` | Checks hardware orchestration, geometry, logger compatibility and mocked ROS integration | Current five-package baseline: 568 passing tests |
| `flake8` | Checks style and the requested line limit | No findings |
| `colcon test` | Tests those five packages; the flag makes failures return a nonzero exit code | All selected packages pass |
| Test-result report | Reads this session's results separately from old build/test outputs | Zero errors, failures and skips |

These checks start no physical drivers and do not establish a real grasp or
availability of optional model weights on your robot.

The full development baseline is 612 tests. Its 44 simulation tests include
fixtures that require the supplied exercise-08 CAD assets at their expected
location. A robot containing only `eira_ws` may lack those assets; this is why
the initial hardware check selects five packages. Run the full suite later in
the configured simulation environment, rather than misclassifying absent CAD
files as a hardware-orchestration failure. No exercise scripts are run here.

## 4. Prepare a protected test configuration

```bash
export EIRA_TEST="$EIRA_WS/robot_test/fresh_start"
export EIRA_PARAMS="$EIRA_TEST/params.yaml"
export EIRA_WAYPOINTS="$EIRA_TEST/waypoints.yaml"
export EIRA_MAP="$EIRA_TEST/maps/arena.yaml"
mkdir -p "$EIRA_TEST/maps" "$HOME/eira_ws/results" "$HOME/eira_ws/bags"
cp -n "$EIRA_WS/src/eira_bringup/config/eira_params.yaml" "$EIRA_PARAMS"
cp -n "$EIRA_WS/src/eira_bringup/config/waypoints.yaml" "$EIRA_WAYPOINTS"
```

| Command | Reason | Expected result |
|---|---|---|
| Four exports | Selects explicit test, parameter, waypoint and map paths | Same values will be used in other terminals |
| `mkdir -p` | Creates test/output directories while retaining existing content | Directories exist |
| Parameter copy | Starts a test file without overwriting an existing one | Copy exists; old content is preserved |
| Waypoint copy | Separates test destinations from source configuration | File exists; sample coordinates still require measurement |

`cp -n` also preserves **obsolete settings**. Compare/update an existing copy:

```bash
diff -u "$EIRA_WS/src/eira_bringup/config/eira_params.yaml" "$EIRA_PARAMS"
nano "$EIRA_PARAMS"
```

**Why:** the comparison shows changed defaults; exit code 1 means differences,
not a failed comparison. Edit the existing node entries under `/**` -> node
name -> `ros__parameters`, retaining deliberate calibration and tuning.

| Node / parameter | Initial setting | Reason |
|---|---|---|
| Brain `scan_enabled` | `false` | A failed search must not rotate the base during stationary testing |
| Brain `llm_timeout_s` | `30.0` | Uses the updated Phi-3 request budget |
| Vision `model_path` | Actual absolute weights path | The default `/home/jetson/...` may not exist for your user |
| Vision `depth_roi_half` | `10` | Uses the 21x21 center depth window |
| Vision `sync_slop_s` | `2.0` | Applies the updated synchronizer tolerance at startup |
| Vision `image_freshness_s` | `5.0` | Uses the active advisory age threshold |
| Vision `depth_camera_info_topic` | `/camera/depth/camera_info` | Selects matching depth calibration when available |
| Vision `continuous_mode` | `false` | Avoids idle inference load |
| Vision `bbox_depth_enabled` | `false` for the first depth test | Prevents an assumed-height estimate from hiding invalid measured depth |
| Vision `depth_debug` | `false` initially | Starts with ordinary readable logs |
| Gate `max_linear_mps` / `max_angular_radps` | `0.10` / `0.30` | Bounds initial supervised base tests |

Verify your chosen weights file with `ls -lh /your/actual/yolov8n.pt`.
**Why:** a path written in YAML does not prove the file exists.

Before later arm motion, transfer and verify measured mount/TF, joint limits,
home/transport poses, gripper calibration and bin poses into this copy. Keep
the arm's feedback and actuator-subscriber checks enabled.

The paths are deliberately different:

```text
Workspace: ~/NeuroBotics/eira_ws/
Reports and evaluation: ~/eira_ws/results/
Bags: ~/eira_ws/bags/
```

Keep storage parameters at those defaults, or record intentional overrides.

## 5. Set up every other terminal consistently

After building, run this block in T2, T3 and T4, replacing the vendor path as
before:

```bash
source /opt/ros/humble/setup.bash
source "$HOME/yahboomcar_ws/install/setup.bash"
export EIRA_WS="$HOME/NeuroBotics/eira_ws"
source "$EIRA_WS/install/setup.bash"
export EIRA_TEST="$EIRA_WS/robot_test/fresh_start"
export EIRA_PARAMS="$EIRA_TEST/params.yaml"
export EIRA_WAYPOINTS="$EIRA_TEST/waypoints.yaml"
export EIRA_MAP="$EIRA_TEST/maps/arena.yaml"
cd "$EIRA_WS"
```

**Why:** sourced overlays and variables belong to a terminal, not the entire
desktop. Every terminal needs Humble, the vendor interfaces, the updated overlay
and the same paths. Keep the robot's existing `ROS_DOMAIN_ID` consistent across
live terminals; do not change it for this hardware session.

## 6. Start transport, then a stationary master

In T0, use the robot image's existing working transport/agent and raw sensor
startup procedure. Its exact command is image-specific and not supplied by
`eira_ws`; do not guess or replace it.

Decide who owns each existing component:

| Component already running in T0 | Add to the master command |
|---|---|
| Filters, scan merger, EKF/odometry | `use_base:=false` |
| Robot description and robot/static TF | `use_robot_tf:=false` |
| Camera driver | `use_camera:=false` |
| Complete native robot-state/TF/`/joint_states` stack | `use_robot_tf:=false use_arm_state_relay:=false` |
| IK/status during later arm tests | `use_arm:=false`, keeping `use_manipulation:=true` |

**Why:** duplicate drivers, controllers and TF publishers make the graph
ambiguous. `use_base` starts processing components, not serial transport.
`use_arm` starts native IK/status; `use_manipulation` starts the grasp executor.
Before any E-AIRA test, stop separate autonomous/teleop workflows and retain
only the native hardware components you intend T0 to supply. Keep a single
mission-producing stack; `use_nav:=false` does not stop an external Nav2 server.

Joint-state detail: with `use_robot_tf:=true`, disabling the relay enables the
master's legacy joint-state publisher. Therefore `use_arm_state_relay:=false`
alone does not avoid duplicate publishers. If only a native `/joint_states`
source exists without robot-state/TF bringup, first establish a known working
external robot-state/TF stack or resolve ownership before motion; the current
master has no separate switch for just its legacy joint-state publisher.

In T1, run the following, adding relevant ownership flags from the table:

```bash
ros2 launch eira_bringup eira_master.launch.py \
  params_file:="$EIRA_PARAMS" waypoints_file:="$EIRA_WAYPOINTS" \
  use_sim_time:=false use_nav:=false \
  use_arm:=false use_manipulation:=false \
  use_evaluation:=true use_recording:=false
```

**Why these arguments:** explicit files select your test configuration; hardware
uses wall time; navigation and arm execution are disabled; evaluation records
evidence; bag writing is deferred to reduce initial load. The Brain remains
running, so `scan_enabled=false` is still essential.

Readable reports, arm display relay and marker publication start automatically.
The relay invents no startup pose. Leave optional adapters disabled initially.

## 7. Verify the live configuration and velocity ownership

In T2:

```bash
ros2 node list
ros2 param get /llm_task_planner use_sim_time
ros2 param get /llm_task_planner scan_enabled
ros2 param get /vision_manager model_path
ros2 param get /vision_manager depth_roi_half
ros2 param get /vision_manager sync_slop_s
ros2 param get /vision_manager image_freshness_s
ros2 param get /vision_manager bbox_depth_enabled
ros2 topic info /cmd_vel --verbose
ros2 topic echo /cmd_vel --once
```

| Command | Reason | Expected result |
|---|---|---|
| Node list | Confirms the intended graph started | Brain, Vision, safety, gate and observers; no grasp executor yet |
| Simulation-time query | Detects an incorrect clock configuration | `false` |
| Scan query | Confirms searches cannot scan the base | `false` |
| Model-path query | Confirms the actual loaded configuration | Your real weights path |
| ROI / sync / freshness queries | Detects an outdated copied YAML or stale launch | `10`, `2.0`, `5.0` |
| Bbox switch query | Confirms the first range test checks real depth | `false` |
| Verbose velocity info | Finds competing final-command publishers | Gate is the sole managed `/cmd_vel` publisher |
| Velocity echo | Checks idle output | All linear/angular components zero |

Read dependency/model/calibration diagnostics before advancing. The first depth
message should report its actual encoding and native dimensions.

## 8. Check camera metadata, intrinsics and TF

Run these observations sequentially in T2:

```bash
timeout 8s ros2 topic hz /camera/color/image_raw
timeout 8s ros2 topic hz /camera/depth/image_raw
ros2 topic echo /camera/color/image_raw --once --no-arr
ros2 topic echo /camera/depth/image_raw --once --no-arr
ros2 topic echo /camera/color/camera_info --once
timeout 8s ros2 topic echo /camera/depth/camera_info --once
ros2 run tf2_ros tf2_echo base_link camera_color_optical_frame
```

| Command | Reason | Expected result |
|---|---|---|
| Color rate | Checks RGB delivery | Ongoing stream; nominal setting 30 fps |
| Depth rate | Checks depth delivery independently | Ongoing stream; nominal setting 10 fps |
| Image metadata echoes | Shows encoding, dimensions, frame and stamp without image bytes | Typically color 640x480 and depth 640x400 in your configuration |
| Color CameraInfo | Checks the calibration matrix and raster dimensions | Positive finite focal lengths and plausible principal point |
| Depth CameraInfo | Checks for the matching depth model | Valid model; absence selects the logged color approximation |
| Camera-to-base TF | Checks geometry needed for target poses | A plausible transform using the actual optical frame name |

`timeout 8s` stops only an observer. Exit code 124 means its time limit expired;
it does not stop a robot mission. Ctrl+C ends continuous observers such as TF
echo. Use the actual optical frame from your messages if its name differs.

Rates depend on load/QoS. On this depth input, `16UC1`/`mono16` are interpreted
as millimetres and `32FC1` as metres. Unknown 8-bit units do not become metric
depth without a documented explicit scale.

Resizing 640x400 to 640x480 changes sampling dimensions and scales intrinsics.
It does not perform camera registration or correct cropping/parallax. Native
registration and measured TF/calibration still matter.

## 9. Check Ollama and preview without execution

```bash
curl --max-time 5 http://localhost:11434/api/tags
ollama list
ros2 run eira_brain eira_cli --plan-only "find a cup"
```

| Command | Reason | Expected result |
|---|---|---|
| HTTP tags | Checks whether the local server answers | Installed model inventory or a clear connection error |
| Model listing | Checks the exact installed model tag | Matches Brain `llm_model`, normally `phi3` |
| CLI preview | Tests local planning/formatting without publishing a mission | `Preview only; nothing sent to robot` and readable steps |

If the server is absent, start your existing Ollama service or `ollama serve`
in a separate terminal; do not start both. Provision missing models before
offline trials. The timeout is per HTTP attempt, and a cold model can be slower.

Preview can use your robot-specific waypoint file with
`--waypoints-file "$EIRA_WAYPOINTS"`. It does not capture a live starting pose
or freeze the live plan. Running Brain commands execute immediately after live
validation. A preview's symbolic `mission_start` is resolved by the running
Brain when a mission starts.
For LLM acceptance, require a live `Plan ready: LLM` result. A working
`rule-based fallback` shows backup planning, not successful model planning.

## 10. Make the first stationary cup detection

Place a visible cup at a measured comfortable distance, initially around 0.5–1 m
and inside the camera's useful range. Keep `bbox_depth_enabled=false`. In T3:

```bash
ros2 run eira_brain eira_cli "find a cup"
```

**Why:** tests Brain -> explicit Vision request -> detector -> depth -> TF ->
correlated result while navigation, manipulation and scanning remain disabled.

Expected: a readable plan, searching, a found range and terminal completion.
Measured range sources are `roi_median` or `bbox_median`. Compare the result with
your measured scene; an assumed-height estimate is not a measured-depth pass.

If needed, start this one-message observer before repeating the find:

```bash
ros2 topic echo /eira/vision/event --once --field data
```

**Why:** intentionally inspects one machine event for `depth_source`,
`depth_estimated`, `intrinsics_source`, timing and IDs. Normal terminal logs stay
readable. If the event is a timeout, inspect its reason instead of assuming found.

## 11. Diagnose depth holes without hiding them

While still stationary:

```bash
ros2 param set /vision_manager depth_debug true
ros2 param set /vision_manager continuous_mode true
```

| Command | Reason | Expected result |
|---|---|---|
| Debug on | Enables depth statistics | Five lines on every tenth detected-target frame |
| Continuous mode on | Supplies enough frames after the first found result for diagnosis | Explicit continuous tracking for this stationary test |

| Diagnostic | Meaning |
|---|---|
| Center value / encoding | Whether the center pixel is a hole and how units are interpreted |
| ROI median / valid count | Whether nearby returns recover the range |
| Full-box min/max | Whether other box pixels contain depth or background |
| Native dimensions | Whether the resize path is being used |
| `fx, fy, cx, cy` | Actual scaled sampling intrinsics |

`Depth unavailable at ROI, trying full box` indicates the first region failed.
`Using color intrinsics for depth (approximation)` identifies missing matching
depth calibration. Globally invalid pixels require camera/scene diagnosis;
medians cannot manufacture measured returns.

After observing, restore the normal state:

```bash
ros2 run eira_brain eira_cli "stop"
ros2 param set /vision_manager continuous_mode false
ros2 param set /vision_manager depth_debug false
```

**Why:** explicit stop cancels work, demand mode removes idle inference load,
and debug-off restores concise logs.

Test the optional estimate separately:

```bash
ros2 param set /vision_manager bbox_depth_class cup
ros2 param set /vision_manager real_object_height_m 0.1
ros2 param set /vision_manager bbox_depth_enabled true
ros2 run eira_brain eira_cli "find a cup"
```

**Why:** explicitly selects a cup-height prior only when measured regions
fail. Replace 0.1 with the actual measured cup height in metres. A fallback
must say `estimated from bbox` and `depth_estimated=true`.
That validates fallback behavior, not a repaired depth sensor. Leave the switch
off when your experiment requires measured depth only.

Old frames warn but still process without new capture timestamps. The arm can
still reject a 3.5-second-old pose under its independent 1.5-second limit.
Resolve actual latency before physical grasping. See
[the depth guide](DABAI_DEPTH_DEBUG.md) for details.

## 12. Check stop, reports and sound before enabling motion

```bash
ros2 run eira_brain eira_cli --quiet "find a cup"
ros2 run eira_brain eira_cli "stop"
```

**Why:** `--quiet` returns after publishing so another command can interrupt
planning/search. It is not a preview. Expect cancellation, stop acknowledgement,
and no delayed execution when the old LLM request eventually returns.

```bash
ros2 topic echo /cmd_vel --once
ls -lt "$HOME/eira_ws/results"
ros2 topic info /beep --verbose
```

| Command | Reason | Expected result |
|---|---|---|
| Velocity echo | Confirms gate output after stop | Zero components |
| Results listing | Finds evidence after terminal grace/flush | `mission_*.txt` and evaluation CSV/JSON |
| Buzzer info | Checks for the native buzzer subscriber | Connected driver for audible cues |

A successful find-only mission gives one short start beep and three short found
beeps. To mute it, run `ros2 param set /llm_task_planner sound_feedback false`.
**Why:** separates visual diagnosis from sound and clears queued software cues.

## 13. Prepare real navigation data

Stop the mission, then Ctrl+C T1 before changing launch composition. Put your
measured map YAML and its referenced image in `$EIRA_TEST/maps/`, or set
`EIRA_MAP` to the existing actual YAML. Preserve its image-path relationship.
Replace sample waypoints with measured free-space base approach poses.

If you have no map, follow
[robot guide stage 10](ROBOT_TESTING_GUIDE.md#10-prepare-a-real-map-and-measured-waypoints).
It uses native SLAM through E-AIRA wrappers, with working odometry/TF and
supervised teleoperation. Do not run mapping and AMCL as competing map-to-odom
publishers.

In T1, start a navigation-only configuration:

```bash
ros2 launch eira_bringup eira_master.launch.py \
  params_file:="$EIRA_PARAMS" waypoints_file:="$EIRA_WAYPOINTS" \
  map:="$EIRA_MAP" use_sim_time:=false use_rviz:=true \
  use_camera:=false use_perception:=false \
  use_arm:=false use_manipulation:=false \
  use_evaluation:=true use_recording:=false
```

**Why:** isolates LiDAR/odometry/Nav2 from camera inference and arm execution.
Use the ownership flags from stage 6 when appropriate. If native Nav2 parameters
are not found automatically, pass your calibrated `nav_params_file`; that is a
different file from the E-AIRA `params_file`.

In RViz, set Fixed Frame to `map`, add Map/LaserScan/RobotModel, and use **2D
Pose Estimate** at the measured robot position and heading. Check scan/map walls.
Then inspect:

```bash
ros2 lifecycle get /amcl
ros2 lifecycle get /controller_server
ros2 action info /navigate_through_poses
timeout 8s ros2 topic hz /scan
timeout 8s ros2 topic hz /odom
ros2 run tf2_ros tf2_echo map base_link
```

| Command | Reason | Expected result |
|---|---|---|
| AMCL lifecycle | Checks localization activation | `active` |
| Controller lifecycle | Checks execution readiness | `active` |
| Action info | Checks the Brain's actual Nav2 interface | One expected server |
| Scan rate | Checks ongoing LiDAR input for localization and obstacle handling | Continuing scan messages |
| Odometry rate | Checks ongoing motion estimates for Nav2/AMCL | Continuing odometry messages |
| Map-to-base TF | Checks localization and odometry form a coherent chain | Plausible measured pose |

For namespaced native nodes, use their actual names from `ros2 node list`.

In T4:

```bash
ros2 run eira_brain waypoint_recorder --ros-args \
  -p waypoints_file:="$EIRA_WAYPOINTS"
```

**Why:** stores RViz **Publish Point** clicks in the Brain's exact database.
Record measured `home`, `kitchen`, `table1`, etc. The recorder saves x/y with
yaw defaulting to zero; manually enter measured yaw in radians. It does not
capture a dragged orientation arrow or measure the robot's current pose.

```bash
ros2 run eira_brain eira_cli --list-waypoints --waypoints-file "$EIRA_WAYPOINTS"
ros2 param get /llm_task_planner waypoints_file
```

**Why:** the first checks the saved values; the second confirms the running
Brain uses the same file. The Brain reloads waypoints per mission.

## 14. Test navigation and markers

Release the base motion inhibit only after localization, stop and measured
destinations pass. Run one command at a time:

```bash
ros2 run eira_brain eira_cli "go to kitchen"
ros2 run eira_brain eira_cli "go home"
ros2 run eira_brain eira_cli "go to kitchen and then go home"
```

| Command | Reason | Expected result |
|---|---|---|
| First goal | Tests one destination | Correct goal, bounded motion, completion |
| Return home | Tests measured start-pose navigation | Base returns; this does not home the arm |
| Two goals | Tests sequencing after goal completion | Three-second settling before the next action |

An abort gets a readable hint and up to two additional attempts with ten-second
waits. Stop/heartbeats must remain responsive. Fixed waits do not prove AMCL
convergence. Repeat one active navigation with `--quiet`, then send `stop` from
another terminal: final velocity must become zero without later restart.

In RViz, add **MarkerArray** on `/eira/visualization_markers`.
**Why:** green target sphere/text shows the active waypoint, yellow shows AMCL
heading, and red shows an object during later active perception missions.
Existing TF must support the actual marker frames.

## 15. Test the calibrated arm separately

Before servo commands, verify measured mount/TF, safe limits, home/transport
poses and gripper settings in your copied YAML. Keep feedback/subscriber checks
enabled. Never set `joint_feedback_is_measured=true` merely to bypass a failure:
the `/joint_states` display relay is not measured feedback.
Use a fresh range checked against the actual scene; an estimated-only find is
not proof that depth alignment or measurement is correct.

After stopping and closing T1, launch:

```bash
ros2 launch eira_bringup eira_master.launch.py \
  params_file:="$EIRA_PARAMS" waypoints_file:="$EIRA_WAYPOINTS" \
  use_sim_time:=false use_nav:=false \
  use_arm:=true use_manipulation:=true \
  use_evaluation:=true use_recording:=false
```

**Why:** enables native IK/status and the grasp executor while keeping Nav2 out.
Apply external-component flags if those services already run. Supervise native
arm startup with the workspace clear.

```bash
ros2 service type /get_kinemarics
ros2 interface show arm_interface/srv/ArmKinemarics
ros2 topic info /arm6_joints --verbose
ros2 topic info /arm_joint --verbose
ros2 topic echo /Curjoints --once
```

| Command | Reason | Expected result |
|---|---|---|
| Service type | Checks the preserved IK name/type | Native service; spelling remains `get_kinemarics` |
| Interface display | Checks installed vendor fields | Real request/response definition |
| Both topic-info commands | Checks actuator connections | Native driver subscribers |
| Feedback echo | Checks fresh plausible reports | Six valid angles; trace measured/commanded provenance |

With Brain idle and the configured home pose verified safe, this diagnostic
moves the arm:

```bash
ros2 topic pub --once /eira/manipulation/request std_msgs/msg/String \
  '{data: "{\"command\":\"home\",\"mission_id\":\"manual-home-001\",\"action_id\":\"1\"}"}'
```

**Why:** isolates home from model interpretation. Use a new mission ID on each
repetition because completed IDs are deduplicated. This direct diagnostic is
not a complete Brain mission or paper benchmark.

Then use a light empty cup at a measured reachable pose:

```bash
ros2 run eira_brain eira_cli "pick up a cup"
ros2 run eira_brain eira_cli "release"
```

**Why:** pick-up checks acquisition, fresh target, base alignment, IK and servo
sequencing; release checks the configured receiving/return sequence. Run one at
a time, with a suitable receiving area. Grasp alignment can move the base even
with Nav2 disabled. Verify actual holding independently of `grasped`.

Observe `/joint_states` and RobotModel during that supervised operation to test
display motion. The relay uses command degrees converted to radians and the six
specified URDF joint names. Configure model zero/sign mapping if needed; a
correct display is not contact or encoder evidence.

## 16. Test one complete mission, then add recording

After navigation and arm tests pass separately, stop/close T1 and start:

```bash
ros2 launch eira_bringup eira_master.launch.py \
  params_file:="$EIRA_PARAMS" waypoints_file:="$EIRA_WAYPOINTS" \
  map:="$EIRA_MAP" use_sim_time:=false use_rviz:=true \
  use_evaluation:=true use_recording:=false
```

**Why:** combines proven components, without bag-writing load in the first full
trial. Reuse the verified ownership flags and initialize localization as needed.

```bash
ros2 run eira_brain eira_cli "bring me a cup from kitchen"
```

**Why:** tests navigate -> find -> grasp -> return to captured mission-start
pose -> release. This return is independent of the saved `home` waypoint. Monitor
the actual live plan; it executes after validation without an approval pause.
Expect readable progress, cues/markers, a terminal result and a text report.
Preserve failures as well as successes.

Repeat with another supported class, such as `bring me a bottle from kitchen`,
to check that detection follows the request. See
[the requested-object fetch procedure](FETCH_MISSION_TESTING.md) for the
ordered assertions and failure cases.

When stable, repeat the launch with `use_recording:=true`.
**Why:** adds sensor/event evidence and disk load as a separate test variable.
Before sending the recorded mission, start this continuous observer in T2:

```bash
ros2 topic echo /eira/recording/status --field data
```

**Why:** recording status is an event stream, not a retained final value. An
observer started after completion may wait indefinitely for another event.

Restore the same cup placement and safe arm state, then repeat the verified
mission from T3:

```bash
ros2 run eira_brain eira_cli "bring me a cup from kitchen"
```

**Why:** repeats a known mission with recording as the additional load. After
its finalization event, Ctrl+C only the recording observer and inspect:

```bash
ls -lt "$HOME/eira_ws/bags"
ros2 bag info "$HOME/eira_ws/bags/ACTUAL_MISSION_DIRECTORY/bag"
```

| Command | Reason | Expected result |
|---|---|---|
| Bag listing | Finds the saved mission directory | Timestamped folder |
| Bag info | Checks metadata and topic counts after finalization | Actual recorded samples |

Replace `ACTUAL_MISSION_DIRECTORY` with a listed folder. Very short missions
may finish before discovery; inspect their manifests.

## 17. Generate metrics and test one benchmark iteration

```bash
export EIRA_DAY="$(date -u +%Y%m%d)"
ros2 run eira_evaluation metrics_calculator \
  "$HOME/eira_ws/results/mission_log_${EIRA_DAY}.csv" \
  --environment hardware --output-dir "$HOME/eira_ws/results/manual_report"
```

**Why:** the UTC date matches daily archive names; the calculator produces
text/JSON, labelled PNGs and LaTeX from collected evidence. After a UTC-midnight
rollover, choose the earlier actual filename instead. Missing measurements or
physical grasp labels remain unknown, not success.

After reset navigation is verified, begin with one trial:

```bash
ros2 run eira_evaluation benchmark --command "find a cup" \
  --iterations 1 --start-waypoint home --environment hardware \
  --results-dir "$HOME/eira_ws/results"
```

**Why:** checks automated reset, correlated execution and reporting without
immediately repeating grasps. It physically navigates to `home` before finding.
Increase N only after this passes. The runner resets the base, not cup placement
or arm/object state; define a scene reset protocol before repeated fetch trials.

Inspect a playback plan without starting replay:

```bash
ros2 run eira_brain mission_replayer \
  "$HOME/eira_ws/bags/ACTUAL_MISSION_DIRECTORY" --dry-run
```

**Why:** checks metadata and remapping without ROS playback. For actual offline
reprocessing, follow the isolated-domain procedure in `RESEARCH_PROTOCOL.md`;
do not replay original actuator commands against the live hardware graph.

## 18. Add optional features individually

These come after the core sequence, not in your first launch.

| Feature / switch | Why separate it? | Detailed procedure |
|---|---|---|
| `use_voice:=true` | Distinguishes transcript, local-file ASR and microphone failures | Robot guide stage 16 |
| `use_gestures:=true` | Checks OK/Thumb_down recognition before gating a grasp | Robot guide stage 15 |
| `use_edge:=true` | Requires calibrated floor geometry; unknown coverage blocks motion | Robot guide stage 17 |
| `use_relocalization:=true` | Requires measured fiducials and pose-quality checks | Robot guide stage 18 |
| `use_rosbridge:=true` | Checks restricted remote commands independently | Robot guide stage 19 |
| `tracking_backend:=transformer` | Distinguishes a working backend from YOLO fallback | Robot guide stage 9 |
| Width grip / color sorting | Requires measured width-angle and bin poses | Robot guide stage 14 |
| Exercise profiles | Alternative workflows may own their own gate | Robot guide stage 22 |
| `ros2 launch eira_simulation sim_bringup.launch.py` | Requires simulation dependencies and a graph isolated from physical drivers | Simulation README |

References: [complete robot guide](ROBOT_TESTING_GUIDE.md),
[operator interface](OPERATOR_INTERFACE.md), [research protocol](RESEARCH_PROTOCOL.md),
[simulation README](../src/eira_simulation/README.md).

## 19. Shut down and preserve evidence

```bash
ros2 run eira_brain eira_cli "stop"
ros2 topic echo /cmd_vel --once
```

**Why:** explicitly ends high-level work and checks final velocity before
closing processes. Verify the physical arm state too. Wait for report/logger
flush and recorder finalization, then Ctrl+C T1 and shut down native hardware
using the robot's normal procedure.

Record each stage as PASS, FAIL or NOT TESTED, with software/model versions,
parameter file, mission ID, observed result and evidence path. A unit test,
controller completion or bbox estimate is not a measured physical grasp result.

## Quick fault isolation

| Symptom | First check | Reason |
|---|---|---|
| Old settings | Overlay prefix and live parameters | Source/install and copied YAML may select different versions |
| Box but no measured range | Encoding, valid-pixel counts, camera models and TF | Detection and metric geometry are different stages |
| Found only with fallback on | `depth_source=bbox_estimate` | A size prior is masking unavailable depth |
| Found but stale-arm error | Capture age and actual sensor/CPU latency | Vision's advisory window does not override arm freshness |
| Cannot connect to Nav2 | Lifecycle and action server | Sensor/Brain readiness does not imply navigation activation |
| Input velocity but no output | Gate reason, owner, heartbeat, enabled edge state | Motion may be intentionally revoked/expired |
| Competing motion | `/cmd_vel --verbose` | Another workflow can bypass or compete with the gate |
| Wrong arm display | Joint names, zero/sign calibration, publishers | Relay displays requested poses, not encoder state |
| Missing artifacts | Actual storage parameters and writer diagnostics | Default results are outside the source workspace |
