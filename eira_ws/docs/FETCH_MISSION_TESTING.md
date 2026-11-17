# Test a requested object from a named place

Use this after the stationary vision, navigation and calibrated arm stages in
[FRESH_START_TESTING.md](FRESH_START_TESTING.md) pass separately. The CLI sends a
command to the Brain; the Brain starts Vision only when its `find` action begins.
A quiet detector while the robot is navigating is expected in demand mode.

For `bring me a bottle from kitchen`, the required sequence is:

1. Capture the robot's current map pose as this mission's `mission_start`.
2. Navigate to the measured `kitchen` approach waypoint and settle.
3. Search for `bottle`, using RGB detection, registered depth and camera TF.
4. Align and grasp using fresh measurements of that requested target.
5. Navigate to the captured starting pose and release.

The saved `home` waypoint can be somewhere else. A fresh start pose is captured
for each mission when it begins, including missions that waited in the queue.
If the starting pose is unavailable, the fetch fails before movement. Object
names come from commands; the detector still needs weights trained for those
classes. Custom models also require the Brain's `known_object_classes` list to
match their labels. Detection support does not establish that every class is
physically graspable by this arm.

## Build and configure

In every terminal, source Humble, your working vendor underlay and the updated
E-AIRA overlay. Build after updating the source:

```bash
source /opt/ros/humble/setup.bash
source "$HOME/yahboomcar_ws/install/setup.bash"
cd "$HOME/NeuroBotics/eira_ws"
colcon build --symlink-install
source install/setup.bash
```

Use your actual vendor path if it differs. In the parameter file you launch,
verify `vision_manager` has the actual local `model_path`, `target_class: ''`,
`continuous_mode: false`, and `bbox_depth_enabled: false`. A copied older YAML
can override the new defaults. Keep the registered depth, intrinsics, arm
calibration and freshness checks used in the earlier acceptance stages.

Start one master with your measured parameter, waypoint and map files, applying
the external-driver ownership flags from the fresh-start guide:

```bash
ros2 launch eira_bringup eira_master.launch.py \
  params_file:=/absolute/path/params.yaml \
  waypoints_file:=/absolute/path/waypoints.yaml \
  map:=/absolute/path/arena.yaml
```

Before the first fetch, complete the stationary find test and confirm the
Vision model-ready message. Resolve model loading/import failures in
[YOLO_RVIZ_DIAGNOSTICS.md](YOLO_RVIZ_DIAGNOSTICS.md) before adding navigation.
The Brain's 75-second outer find budget allows cold model startup plus a bounded
search; a matching found/failure event advances or ends the action immediately.
Update an older copied Brain `find_timeout_s` value as well.

The waypoint's yaw must point the camera toward the search area. The search can
rotate through the configured bounded scan arc when `scan_enabled` is true;
it does not independently explore every location in a room.

## Preview and check the graph

Replace the waypoint file path with the one given to the master:

```bash
ros2 run eira_brain eira_cli --plan-only \
  --waypoints-file /absolute/path/waypoints.yaml \
  "bring me a bottle from kitchen"
ros2 topic info /eira/command --verbose
ros2 topic info /eira/vision_target --verbose
ros2 action info /navigate_through_poses
ros2 param get /vision_manager continuous_mode
ros2 run tf2_ros tf2_echo map base_link
```

Expect a preview with source navigation before `find bottle`, then grasp,
navigation to symbolic `mission_start`, and release. Preview sends no mission
and captures no live pose. The live graph must connect CLI commands to one
planner, planner target requests to one Vision node, and navigation to an active
Nav2 server. Use your actual configured base frame when inspecting TF.

Start observers in separate terminals before the command:

```bash
ros2 topic echo /eira/plan --field data
ros2 topic echo /eira/vision_target --field data
ros2 topic echo /eira/vision/event --field data
```

## Run and assess

Place a supported, reachable bottle at the source. Start the robot from a
measured pose that differs from `home`, then run:

```bash
ros2 run eira_brain eira_cli --timeout 600 "bring me a bottle from kitchen"
```

Check the live evidence:

| Stage | Expected observation |
|---|---|
| Plan | `navigate kitchen`, `find bottle`, `grasp`, `navigate mission_start`, `release` |
| Source navigation | No active bottle search until the navigation action completes |
| Acquisition | Request and `found` event both say `bottle`, with matching mission/action IDs |
| Geometry | Fresh finite `/target_pose`; measured depth source and valid camera-to-base TF |
| Grasp | Fresh requested-target updates and a correlated manipulation completion |
| Return | Base returns to its captured initial position and heading, then releases |
| Result | Terminal state/report agrees with the observed steps; verify physical holding and delivery separately |

Repeat with a second supported, graspable class such as `cup` or `apple`,
without changing a target in YAML. Keep another object class visible to verify
that it does not satisfy the requested search. Then remove the requested
object: acquisition must exhaust its bounded search/retry budget and report
failure, without grasping a different object or claiming delivery. Stop remains
available throughout:

```bash
ros2 run eira_brain eira_cli "stop"
```

A CLI timeout only stops waiting; it does not cancel the running mission. Send
the explicit stop command if needed. Missing objects and navigation/grasp
failures end the mission through the failure policy; automatic return after a
failed action is not a successful fetch. Preserve the failure reason and report.

The simulator's optional `ground_truth` oracle contains a red-cup fixture. Use
learned `perception_mode:=yolo` and suitable scene/model assets to assess other
classes; the oracle cannot establish arbitrary-object vision support.
