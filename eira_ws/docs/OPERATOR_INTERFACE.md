# Live robot feedback and mission reports

Author: E-AIRA maintainers.
Hardware target: ROSMASTER M3 Pro / Jetson Orin NX, ROS 2 Humble / Python 3.10.

## Start the operator interface

Build/source the workspace as described in the main README, start the existing
native transport, then use the master with your calibrated files:

```bash
ros2 launch eira_bringup eira_master.launch.py \
  params_file:=/absolute/path/your_eira_params.yaml \
  waypoints_file:=/absolute/path/your_waypoints.yaml \
  map:=/absolute/path/your_map.yaml use_rviz:=true
```

Readable logging, mission reports, arm display relay, and RViz markers are on
by default. The additional launch flags are `use_mission_reports`,
`use_arm_state_relay`, and `use_visualization`; set any to false to omit that
observer. When a complete native robot-state/TF/`/joint_states` stack already
runs, use both `use_robot_tf:=false` and `use_arm_state_relay:=false`. With robot
TF enabled, disabling the relay enables the master's legacy joint-state
publisher, so relay-off alone does not resolve publisher ownership. The master
omits its legacy joint-state publisher
when the relay is enabled, and simulation explicitly disables the relay in
favor of its measured simulated joint state source.

## Read the terminal

Brain, Vision and Arm show labeled activity lines. Colors distinguish ordinary
activity, completion, warnings and errors. The master gives E-AIRA processes a
pseudo-terminal and a compact ROS console format. Direct execution also detects
terminal color support. `NO_COLOR=1` or CLI `--no-color` disables ANSI styling;
`FORCE_COLOR=1` enables it when a terminal is not detected.

Illustrative output, not an observed hardware trial:

```text
[BRAIN] Planning: bring me a red cup from kitchen
[BRAIN] Navigate to kitchen -> Find red cup -> Grasp -> Navigate to mission_start -> Release
[BRAIN] Plan ready: LLM (840 ms)
[BRAIN] [1/5] Navigating to kitchen
[VISION] Found red cup | 0.85 m away | 92% confidence | track 7
[ARM] Aligning base with target
[ARM] Opening gripper
[ARM] Moving arm to grasp pose
[ARM] Closing gripper
[ARM] Moving arm to transport pose
[BRAIN] Mission complete (42.0 s)
```

Repeated Vision refresh/search/idle observations go to debug level while their
ROS events continue to publish. Arm stages log when dispatched rather than on
each controller tick. Raw LLM responses are debug messages, controlled by the
existing `llm_log_raw_response` flag. To inspect them outside the master, run a
single planner with `--ros-args --log-level debug`; do not start a duplicate
planner against the live graph.

CLI commands, previews and waypoint listings are readable by default:

```bash
ros2 run eira_brain eira_cli --plan-only "find a red cup"
ros2 run eira_brain eira_cli --list-waypoints --waypoints-file /absolute/path/waypoints.yaml
```

Existing scripts can explicitly select CLI `--json`. Machine-readable ROS topic
contracts, including `/eira/status`, plans and correlated skill events, retain
their JSON payloads. Evaluation CSV/JSON, bags and manifests also retain their
structured evidence; terminal formatting does not alter robot commands.

## Act on errors

| Observation | Operator-facing guidance |
|---|---|
| Navigation abort status 6 | Robot may be lost; try 2D Pose Estimate in RViz |
| Nav2 discovery timeout | Cannot connect to Nav2; check that Nav2 is running |
| Invalid LLM response with valid fallback | Rule-based fallback is being used |
| Object acquisition timeout | Names the object and configured search duration; check visibility |
| Detected object with no usable depth | Try better lighting or move the object to a table |
| Missing arm feedback | Check that the native arm_status node is running |

These are recovery hints, not diagnoses. Status 6 can have causes other than
AMCL. Commanded arm display poses never satisfy the measured-feedback requirement
for a servo hold or physical grasp verification.

## See arm commands in RViz

`arm_state_relay` observes `/arm6_joints` and, after a complete pose exists,
`/arm_joint` updates. It publishes `/joint_states` with these exact names:

```text
arm1_Joint arm2_Joint arm3_Joint arm4_Joint arm5_Joint rlink1_Joint
```

Positions use degree-to-radian conversion. Defaults are zero offsets and positive
axis signs. If your URDF has different servo zero/axis conventions, configure
`servo_offsets_deg` and `servo_signs` in the `arm_state_relay` YAML selector and
restart. Check the display against your actual model; gripper linkage geometry
may need a calibrated mapping. The relay sends no motor commands, publishes no
`/Curjoints`, and invents no startup joint pose.

To test, observe a normal, already calibrated supervised arm operation:

```bash
ros2 topic info /joint_states --verbose
ros2 topic echo /joint_states --once
```

Add RobotModel in RViz and verify the arm responds to those commands. Display
motion shows requested poses; it is not encoder feedback. Do not send arbitrary
servo commands merely to exercise the display.

## Add planning markers to RViz

Set the RViz fixed frame to your map frame, add a **MarkerArray** display, and
select `/eira/visualization_markers`.

| Marker | Meaning |
|---|---|
| Green sphere and `TARGET: kitchen` | Current active navigation waypoint from your measured waypoint database |
| Red sphere and `OBJECT: ...` | Correlated object measurement in its actual source frame |
| Yellow arrow | Observed robot heading from `/amcl_pose` |

The object label distinguishes base-frame range from camera depth. RViz uses
your existing TF tree to render mixed frames. No coordinates or transforms are
invented. Markers for old missions/lost objects are explicitly deleted, and stale
observations expire. The heading disappears when AMCL evidence is stale; an
alternative localization source needs an equivalent observed pose interface.

```bash
ros2 topic type /eira/visualization_markers
ros2 topic echo /eira/visualization_markers --once --no-arr
```

Expected type: `visualization_msgs/msg/MarkerArray`. Configure marker sizes,
lifetimes and refresh rate in the `visualization_markers` YAML selector.

## Read the end-of-mission summary

`mission_reporter` observes plan/status topics and prints one summary per terminal
mission, after a short cross-topic observation grace interval. It includes the
command, selected planner, outcome, observed total duration, each action attempt,
retry count and error guidance. Missing observations are identified explicitly.
Controller completion does not assert successful physical object holding.

Each mission also creates an atomic UTF-8 report under:

```text
~/eira_ws/results/mission_UTC_TIMESTAMP_MISSION_ID_HASH.txt
```

The file includes original technical failure reasons alongside readable hints
for traceability. It contains no ANSI control sequences. Late correlated
evidence updates the same file without repeating the whole terminal summary.
Temporary write failures have a bounded retry budget and visible diagnostics.
Configure `mission_reporter.results_dir` if you intentionally use another path;
the default is `~/eira_ws/results`, not `~/NeuroBotics/eira_ws/results`.

```bash
ls -lt ~/eira_ws/results/mission_*.txt
```

The existing evaluation logger remains the source of CSV/JSON metrics and
annotation evidence. These text summaries are a readable companion for trial
review; retain the quantitative artifacts for the paper.

## Recognize buzzer patterns

| Event | Pattern |
|---|---|
| Mission starts | 1 short |
| Navigation succeeds | 2 short |
| Object is found | 3 short |
| Grasp sequence succeeds | 1 long |
| Mission fails | 1 long, then 1 short |

The Brain schedules duration-valued `std_msgs/UInt16` messages on the existing
`/beep` topic. Defaults are 100 ms short, 600 ms long, and a 150 ms gap.
Sequencing uses a timer, not sleeps in the controller. The standalone arm
sequencer no longer adds a competing completion beep. A grasp cue denotes
sequence completion; it does not establish contact.

Disable feedback without restarting:

```bash
ros2 param set /llm_task_planner sound_feedback false
```

Set `sound_feedback: false` in the Brain YAML for a persistent setting. Other
sound parameters are `sound_short_ms`, `sound_long_ms`, `sound_gap_s`, and
`sound_queue_size`. Keep the native buzzer subscriber running when testing;
software tests capture these messages and do not sound hardware.
