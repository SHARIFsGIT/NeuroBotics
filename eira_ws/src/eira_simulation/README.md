# E-AIRA simulation

Author: E-AIRA maintainers. Target: ROS 2 Humble / Gazebo Classic 11.

This package reuses the actual M3 Pro URDF/CAD description, preserving its links,
joint origins and original limits. It replaces conflicting simulator plugins with
an explicit holonomic planar base, measured joint-state/trajectory adapters,
LiDAR, and registered RGB-D sensor interfaces. It does not run Yahboom hardware
transport or modify low-level drivers.

## Installation and models

Install Gazebo Classic ROS plugins and Nav2 for Humble. Build the original
`arm_msgs` and `arm_interface` **message/interface packages** for the development
machine's architecture; the simulated arm implements the existing service and
message contracts without vendor motor drivers.

```bash
sudo apt install ros-humble-gazebo-ros-pkgs ros-humble-navigation2 ros-humble-nav2-bringup
source /opt/ros/humble/setup.bash
# Source your existing vendor interface and robot-description workspace.
cd ~/NeuroBotics/eira_ws
colcon build --symlink-install
source install/setup.bash
```

Robot selection order is an explicit `robot_urdf`, installed
`M3Pro/urdf/m3pro.urdf`, installed `neurobotics/urdf/neurobotics.urdf`, then the
supplied exercise-08 source model. Referenced mesh assets must exist. Missing
models are reported; a generic robot is never substituted silently. Model
joint-name conventions follow the supplied exercise-08 M3 Pro chain; a different
vendor model must provide equivalent arm/finger names or an explicit adapter.

The simulator loads YOLO from a locally installed compatible model. A primitive
red cylinder is the default cup; successful recognition by photographic COCO
weights is not guaranteed. Supply an appropriate trained model for learned-vision
experiments. Rendering RGB-D normally requires an available OpenGL/X display,
even with `gui:=false`; use a suitable virtual display on a headless workstation.

## Launch

```bash
ros2 launch eira_simulation sim_bringup.launch.py \
  yolo_model:=/absolute/path/yolov8n.pt \
  output_dir:=/absolute/path/results/sim_seed_42 randomize:=true seed:=42
```

The generated world is a 5 m × 5 m room with 2 m walls, a 0.5 m table,
a dynamic cylinder cup, and a visual start marker at (-1.5, 0). A matching
conservative 2D map and measured-in-world `home`, `table`, and `kitchen`
waypoints are generated with the condition. Native Nav2 uses a holonomic local
planner, explicit minimal behavior trees, and the existing velocity gate.

All E-AIRA nodes, robot state publishing, sensors, bridge and Nav2 receive
`use_sim_time=true`. No physical base/camera/arm drivers are launched. The
master's existing `use_sim_time=false` default is unchanged; selecting false in
the simulation launch explicitly delegates to real-hardware master bringup.

`condition.json` records the seed, exact cup pose, lighting, metric sensor noise,
perception mode, model source, and URDF hashes. Retain the complete output
directory together with evaluation CSV/JSON and bags. An omitted output directory
uses a temporary directory suitable for development, not permanent paper assets.
Gazebo receives the same seed as the Python asset/noise generators. Physics and
rendering reproducibility still depends on engine, drivers and platform versions.

Lighting, cup x/y and Gaussian LiDAR/depth noise are randomized per launch when
`randomize=true`. Depth noise is applied in metres and preserves invalid returns.
Run each independent condition with a recorded seed; repeating a benchmark in
one launched world does not automatically resample conditions or replace the cup.

## Explicit control-regression oracle

```bash
ros2 launch eira_simulation sim_bringup.launch.py perception_mode:=ground_truth \
  randomize:=true seed:=42 output_dir:=/absolute/path/results/oracle_seed_42
```

This mode replaces learned detection with observed Gazebo model poses. Its
`/eira/vision/event` messages explicitly identify `simulation_ground_truth`, and
the logger records `environment=simulation_oracle`. Metrics reject silently
pooling this with hardware or learned-perception results. It is useful for
navigation/planning/control regression, not for measuring detector accuracy,
perception latency, or sim-to-real generalization.

## Arm model limits

The simulation bridge solves bounded numerical IK from the real URDF. Position
constraints are enabled by default; optional orientation weighting does not
make a five-axis-plus-gripper chain capable of arbitrary 6D poses. Unreachable
requests fail rather than returning apparently valid zero angles.

Servo commands are mapped to native joints and streamed as interpolated
kinematic poses respecting configured duration and original velocity limits.
Only actual Gazebo `/joint_states` values produce `/Curjoints`. The base and arm
are **kinematic control models**, not calibrated mecanum traction, torque-control,
or gripper-contact models. Physical object holding is not asserted. Evaluate
real grasp accuracy with measured contact/held-object evidence on hardware.

## Resources and tests

`worlds/eira_room.world` and `maps/` provide the fixed seed-0 room/map. Runtime
conditions regenerate them deterministically. `config/nav2_params.yaml` and
`behavior_trees/` specify navigation; `robot_description.py` installs the exact
public sensor contracts.

Tests cover seeded world/map generation, native CAD preservation, camera view at
final standoff, noise units, numerical FK/IK, joint interpolation/feedback,
oracle provenance and real launch composition without starting hardware.

The plugins use the upstream [Gazebo ROS planar, camera and joint interfaces](https://github.com/ros-simulation/gazebo_ros_pkgs/tree/ros2/gazebo_plugins).
