# Self-contained E-AIRA: migration plan

Audit date: 2026-11-17. Proposal only; nothing in it has been implemented.
Each step ends at a gate that needs your approval. Steps that move the robot
or change the Jetson also need explicit authorization.

## 1. Principles

1. **The factory image is never modified.** The Yahboom workspaces stay
   installed: they are the fallback and the reference to test against.
2. **Side by side, then switch.** An E-AIRA component is introduced next to
   the factory one and compared with it. Only then does E-AIRA stop using the
   factory one.
3. **The vendor component is the test oracle.** Its behaviour is recorded
   before it is replaced (bags, IK answers, TF trees), and the replacement must
   reproduce it within stated tolerances.
4. **Small, reversible steps,** each committed separately once you approve
   committing.
5. **No motion without authorization.** Steps that move the base or the arm
   are marked.
6. **No Yahboom code is copied into the repository** until its licence is
   known. Configurations are re-expressed as E-AIRA files that record where
   each value came from. Values are facts about this robot; code is not
   copied.

## 2. Target layout

```text
eira_ws/
├── src/
│   ├── eira_interfaces/        new, ament_cmake: E-AIRA's own typed messages, services, actions
│   ├── vendor_compat/
│   │   └── arm_msgs/           new, ament_cmake: exact copy of the firmware's message types
│   ├── third_party/            optional: ira_laser_tools ROS 2 port with its BSD licence
│   ├── eira_description/       new: URDF/xacro, frames; simple shapes, optional mesh path
│   ├── eira_bringup/           launch: robot (base, scans, camera, TF), agent start, teleop
│   │   └── config/robot/       robot-specific values with their origin noted
│   ├── eira_navigation/        new by extraction: Nav2 and SLAM Toolbox launch and parameters,
│   │                           map tools, localization monitor, relocalization
│   ├── eira_manipulation/      + IK/FK and the servo-angle conventions, hand-eye calibration
│   ├── eira_perception/        model files located through a data-directory parameter
│   ├── eira_brain/
│   ├── eira_evaluation/
│   └── eira_simulation/
├── tools/
│   ├── system_requirements.md  every external dependency with version and install steps
│   ├── udev/                   rule files and install notes
│   ├── agent/                  micro-ROS agent source list, build notes, headless start unit
│   └── dependency_audit.sh     fails if anything resolves into a factory workspace
└── docs/
```

Large or arena-specific data stays outside the source tree, in a data
directory referenced by parameters (proposed `~/eira_data/` on the Jetson):
maps, model weights, TensorRT engines, results, bags. Small calibration values
are committed under `eira_bringup/config/robot/`, because they belong to the
reproducible record.

## 3. Laptop-to-Jetson deployment

The laptop repository `~/NeuroBotics` stays the single source of truth.
`~/eira_ws` is where E-AIRA is built and run on the Jetson. Two options:

| Option | How | For | Against |
|---|---|---|---|
| A | Clone the repository on the Jetson and make `~/eira_ws` a link to `~/NeuroBotics/eira_ws` | The exact commit is known on the robot | The whole repository, including the exercise pages and meshes, lives on the robot |
| B | Copy `eira_ws/src` and `tools` to `~/eira_ws` with `rsync`, plus a file recording the commit | Small | The commit is recorded by hand |

Either way, build on the Jetson; never copy `build/` or `install/` between
machines. Each mission log should record the deployed commit.

## 4. Steps

| Step | Work | Changes | Gate | Done when |
|---|---|---|---|---|
| M0 | Commit the present `eira_ws`, plus these audit documents, on a branch | Git only | Your approval to commit | Clean `git status` on the branch |
| M1 | You run the read-only inventory script; optionally the live-graph section with the agent running | Nothing (output saved on the laptop) | You run it | Inventory documents completed; this plan revised |
| M2 | Decisions N1–N9 below | — | Your answers | Recorded in the plan |
| M3 | Reference capture: copy from the Jetson to the laptop the installed message definitions, real URDF, static-TF launch, Nav2/EKF/IMU/merger/filter parameters, `common.yaml`, hand-eye offsets, tag map. Record path and hash of each. Keep the copies out of the public repository until licences are known | Laptop only (reads on the Jetson) | Approval | Reference set with hashes |
| M4 | Oracle recordings with the robot powered and stationary, under the factory bring-up: a bag of raw and processed topics (`/scan0`, `/scan1`, `/scan`, IMU, odometry, `/tf`, `/tf_static`, camera info, a few frames); `get_kinemarics` answers over a grid of targets (service calls only; the arm does not move); a TF snapshot at the current arm pose | Bag files on the laptop | **Hardware authorization (stationary)** | Oracle data set |
| M5 | Interface compatibility: create `vendor_compat/arm_msgs`. Prove the definitions match the installed ones text for text. On the robot, with no factory workspace sourced, `ros2 topic info -v /arm6_joints` shows a single matching type; then one supervised arm command | `eira_ws`; robot | Approval; **authorization for the arm command** | Arm moves to a known pose from an E-AIRA-only environment |
| M6 | `eira_description`: URDF facts from M3, simple shapes, optional mesh path; `robot_state_publisher` launch | `eira_ws` | Approval | TF matches the M4 snapshot within 1 mm and 0.1° |
| M7 | Base pipeline from apt `robot_localization`, `imu_filter_madgwick`, `laser_filters`, plus the merger (option N8), with E-AIRA parameter files | `eira_ws`; apt packages on the Jetson | Approval for apt installs on the Jetson | M4 bag replayed through both pipelines gives matching `/odom` and `/scan` within tolerance; then live rates on the stationary robot |
| M8 | Camera: compare apt `ros-humble-orbbec-camera` 2.10.7 with the factory build (topics, encodings, resolution, intrinsics, frame names, registration). Choose one and pin it | Jetson (apt install) | Approval; **stationary authorization** | Comparison table recorded; E-AIRA camera launch uses the chosen driver |
| M9 | Navigation: E-AIRA Nav2 parameters (values copied once, origin noted); SLAM Toolbox mapping launch; map saving into the data directory. Simulation on the laptop first, then the robot | `eira_ws`; laptop needs Nav2 installed | Approval for laptop installs; **motion authorization** | Map built with E-AIRA; navigation trials recorded |
| M10 | Arm: E-AIRA IK/FK and servo conventions, checked offline against the M4 IK answers; E-AIRA hand-eye calibration; then free-space moves and a grasp at a fixed pose | `eira_ws`; robot | Approval; **arm-motion authorization per stage** | IK agreement report; calibration within tolerance of the factory offsets; recorded grasp trials |
| M11 | Joint-state source (per the inventory); teleop through apt packages and the gate; joystick takeover flag; headless agent start unit | `eira_ws`; Jetson for the unit | Approval to install the unit | Robot boots and connects without a desktop session |
| M12 | Relocalization and tracker, as decided in N2 and N3 | `eira_ws` | Approval | Per decision |
| M13 | **Clean-environment check.** (a) On the Jetson, open a shell with no profile, source only `/opt/ros/humble`, the agent workspace and `~/eira_ws/install`, and run the dependency audit (§5). (b) Optional: install JetPack, ROS and the documented system dependencies on a spare drive, then build and run E-AIRA there | Nothing for (a); a spare drive for (b) | Approval; spare drive for (b) | All audit criteria pass |
| M14 | Remove factory `exec_depend` entries; keep the exercise profiles as a separate, clearly labelled optional launch, or remove them; finish `tools/system_requirements.md` | `eira_ws` | Approval | `rosdep` resolves every key; documents current |

Effort: M0–M3 small; M4 one robot session; M5–M8 medium; M9 medium; M10 is
the largest; M11–M14 small to medium.

## 5. When E-AIRA counts as independent

The dependency audit passes when all of these hold in the clean shell of M13:

1. `colcon build` of `eira_ws` succeeds with only `/opt/ros/humble` and the
   agent workspace sourced.
2. `rosdep check --from-paths src --ignore-src` reports nothing missing except
   items listed in `tools/system_requirements.md`.
3. Every package that an E-AIRA launch file uses resolves to `/opt/ros/humble`,
   `~/eira_ws/install` or the agent workspace (`ros2 pkg prefix`).
4. No file under `eira_ws/src` refers to `yahboomcar_ws`, `M3Pro_ws`,
   `~/MODELS` or `mircoROS_agent`, except documentation and the optional
   factory-profiles launch.
5. The master launch reports no `[dependency_missing]` lines.
6. Stationary acceptance checks pass: topic rates, TF tree, camera
   information, scans.
7. Supervised motion acceptance passes, under its own authorization.

## 6. Decisions needed

| # | Decision | Recommendation |
|---|---|---|
| N1 | Localization for experiments: AMCL (exercises 17–18) or SLAM Toolbox localization (exercise 24) | AMCL to start, since E-AIRA already uses it; revisit if relocalization is needed |
| N2 | Relocalization: AprilTag (like exercise 24, rebuilt on apt `apriltag_ros`), ArUco (E-AIRA code, never run), or none | AprilTag, because it matches what you have tested; ArUco code frozen |
| N3 | Transformer tracker: replace `smart_tracker` with an open tracker, or drop the claim | Decide with the research scope (previous question Q6) |
| N4 | May Yahboom meshes be stored in the repository? | Simple shapes by default; meshes from a local path |
| N5 | Deployment: option A or B (§3) | A, for the commit record on the robot |
| N6 | Data directory location | `~/eira_data` on both machines |
| N7 | Is a spare drive available for a true fresh-image test? | Useful but not required |
| N8 | Scan merger: vendor the BSD ROS 2 port, or write an E-AIRA node | Vendor the port first (tested on this robot); replace only if needed |
| N9 | May the laptop get Nav2, SLAM Toolbox, `laser_filters`, `imu_tools`, `apriltag_ros` from apt for simulation? | Yes; needed for M9 and for the simulation phase |

## 7. Relation to the research phases

- M0–M4 can run alongside Phase 1, the research definition.
- M5–M12 replace the earlier roadmap's consolidation step.
- M13 must pass before Phase 6 hardware validation, so that every experiment
  runs on the self-contained system.
- The paper's software artifact is the state after M14.
