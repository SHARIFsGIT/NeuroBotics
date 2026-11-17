# Technical debt and risk register

Audit date: 2026-11-17. Each item states what was observed, where, why it
matters and what is proposed. Nothing here has been changed.

Severity:

- **Critical** — can damage hardware, lose work, or invalidate the paper.
- **High** — blocks a research question or a reliable end-to-end run.
- **Medium** — slows the work or weakens maintainability.
- **Low** — cosmetic or easily fixed.

## Top five, in the order they should be handled

1. **H1** Uncommitted work: commit before anything else.
2. **G1–G3** The camera-to-arm geometry is unverified and, by default, probably wrong.
3. **R1** No measured result exists; every claim so far is a design intention.
4. **R2** The contribution is not yet distinguishable from published work.
5. **S6** The plan validator accepts unsafe grasp targets.

Since the factory-independence decision of 2026-11-17, **F1–F3** join this
group: they decide whether E-AIRA can run on a Jetson without the factory
workspaces.

## R — Research validity

| ID | Severity | Observation | Consequence | Proposed remedy |
|---|---|---|---|---|
| R1 | Critical | No mission log, bag, map or measurement from the robot or a simulator exists in the repository or on this machine | The paper has no data. Several documents describe a finished system; a reviewer would ask for evidence none of which exists yet | Treat the system as unvalidated until Phase 6. Record every hardware session with the existing logger and recorder from the first run |
| R2 | Critical | Turning language into a validated list of robot skills with an LLM is established (SayCan 2022, Code as Policies 2022, ProgPrompt 2022, Inner Monologue 2022, SayPlan 2023). A ROS framework for it exists (ROS-LLM 2024). Open-vocabulary fetch on a mobile manipulator has been measured at scale (OK-Robot 2024, HomeRobot 2023) | "LLM plans, ROS executes" is not a contribution on its own | Define the contribution around what is measurable and less studied: small models running on the robot's own computer, the cost of that in latency and reliability, and failure recovery. See `reuse_and_integration_plan.md` §5 |
| R3 | High | For a fetch command the validator requires the plan to equal the rule-based plan step for step (`_validate_command_plan`) | On the headline task the LLM cannot do better than the rule parser; it can only match it or be rejected. Research question 1 would measure agreement with a template, not planning ability | Decide what freedom the LLM is given, then design the instruction set so that rule-based and LLM planners can be compared fairly |
| R4 | High | The title promises transformer tracking. The vendor tracker is a closed binary; the `eira_ws` adapter has never loaded a model | A title claim with no implementation behind it | Either integrate a tracker whose interface is known and measure it against YOLO-only tracking, or drop the term from the title |
| R5 | High | Detection uses COCO-pretrained `yolov8n`; colour is a pixel-fraction heuristic. There is no labelled test set from the robot's environment | Precision, recall and mAP cannot be reported | Collect and label a small test set in the experiment arena, or report task-level detection success only and say so |
| R6 | High | No ground truth exists for 3D position error or for grasp success | Experiments E and H cannot be scored | Position: measured object placements on a grid. Grasp: operator or video label through the existing `/eira/evaluation/grasp_truth` topic |
| R7 | Medium | The arm is described as 6-DoF and the robot as having one LiDAR | Inaccurate system description | Describe five positioning joints plus a gripper, and two merged LiDARs |
| R8 | Medium | The literature search for directly overlapping work (local LLM, ROS 2, Jetson, mobile manipulation) was not possible during this audit | Novelty is not yet assessed against the closest papers | First task of Phase 1 |

## G — Geometry and calibration

| ID | Severity | Observation | Consequence | Proposed remedy |
|---|---|---|---|---|
| G1 | Critical | In the hardware launch `use_arm_state_relay` defaults to true. `arm_state_relay` then becomes the `/joint_states` source, converting commanded servo degrees to radians with offsets 0 and signs +1 (`eira_params.yaml`). The simulator bridge uses offsets of 90 for the same joints. The camera link is on `arm4` | If the camera frame hangs off the arm chain, every `/target_pose` is computed with each arm joint about 90° wrong. The documents present the relay as a display aid only | On the robot, with the arm still: compare `tf2_echo base_link <camera frame>` with a tape measure for two arm poses. Then choose one joint-state source and calibrate it |
| G2 | Critical | The vendor grasp chain is hand-eye matrix → forward kinematics → offsets calibrated in exercise 01. `grasp_executor` uses none of these; it needs `arm_base_frame` or a measured static mount, both unset | Out of the box a grasp aborts with "arm frame unavailable". Once a frame is set, accuracy depends on a URDF chain nobody has checked, while the calibration that exercise 01 produced goes unused | Reuse the vendor chain inside the pose estimate (same service, same offsets file), or show by measurement that the TF chain is at least as accurate |
| G3 | High | Camera frame attachment is unknown: URDF puts `DCW2` on `arm4`; exercise 20 publishes a fixed `base_link → camera_link`; `static_tf.launch.py` is unseen | Possible duplicate or conflicting transforms | Dump the live TF tree (`view_frames`) under each bring-up family |
| G4 | High | `/target_pose` is the front surface of the object at the box centre, identity orientation | The gripper is aimed at the near face, not the grasp centre; error grows with object size. The master prompt asks for this to be defined | Define the reference point explicitly; add a per-class depth offset or use the depth region inside the box |
| G5 | Medium | Colour and depth are paired with a tolerance of 2.0 s (`sync_slop_s`). Registration is requested, but the vendor default is off and resolutions differ (640×480 vs 640×400) | A moving base or arm can pair a box with stale depth; unregistered depth is offset from colour pixels | Verify registration on the robot; reduce the tolerance to a few frame periods once rates are known |
| G6 | Medium | Parameters hold numbers of unknown origin: PID gains, stand-off 0.19 m, joint limits 0–180 for all six servos, gripper angles, x compensation −0.015 m | The master prompt forbids unverified coordinates, limits and gains. Some are vendor values, some are placeholders; the file does not say which | Add a provenance note per value: vendor source line, measured, or placeholder. Measure the placeholders |
| G7 | Medium | `waypoints.yaml` holds example poses; the marker map is empty | Navigation targets are fictional until recorded | Record with the existing `waypoint_recorder` after mapping |

## S — Safety

| ID | Severity | Observation | Consequence | Proposed remedy |
|---|---|---|---|---|
| S1 | High | The velocity gate controls `/cmd_vel` only for nodes launched through it. Vendor nodes publish to `/cmd_vel` directly. No hardware emergency stop is referenced anywhere | Two publishers can fight over the base; software alone cannot guarantee a stop | Confirm the physical stop. Never run vendor motion nodes beside the master launch. Consider remapping the driver's input topic so the gate is the only route |
| S2 | High | Arm motion is a list of point-to-point servo commands. There is no collision model, no workspace limit beyond 0–180° per servo, no approach or retreat path | The arm can strike the table, the object or the robot itself | Start with a measured safe workspace box in the arm frame and reject targets outside it; add staged approach heights |
| S3 | High | No topic is known to carry measured joint positions. The vendor `Curjoints` is published by the demo nodes with their own commanded pose | "Convergence" checks may compare a command with its own echo | Find out on the robot what `arm_status` publishes; until then treat all arm completion as time-based |
| S4 | High | Grasp success is never verified | A failed grasp is carried through navigation and reported as success by the controller | Minimum: re-detect the object in the gripper view or check it has left its place. Keep reporting contact as unverified until then |
| S5 | Medium | The joystick node's `/JoyState` takeover flag is honoured by `exercise_skills` only | A human cannot take over the base from a running mission with the joystick | Feed `/JoyState` into the gate as a highest-priority owner |
| S6 | High | `validate_actions` accepts any detector class before `grasp`. Verified during the audit: `find person → grasp`, `find knife → grasp` and `find refrigerator → grasp` all validate | The robot can be told to drive its arm at a person, or at objects it cannot hold | Add a graspable-class list and size limits to plan validation. This also strengthens the capability-grounding contribution |
| S7 | Medium | Stopping the arm is a best-effort "hold current pose" command, sent only if joint feedback is declared measured | The arm may finish its current move after a stop | Document the limit; use short motion segments |

## A — Architecture

| ID | Severity | Observation | Consequence | Proposed remedy |
|---|---|---|---|---|
| A1 | High | All E-AIRA contracts are JSON in `std_msgs/String`; find, grasp and release are topic pairs, not actions | No type checking, no standard feedback or cancel, hand-written correlation IDs. Departs from the master prompt's rules 10–12 | Add an `eira_interfaces` package and move the three long operations to actions, one at a time, keeping the JSON topics until each is proven |
| A2 | Medium | `llm_task_planner.py` is 1,546 lines covering planning, validation, execution, recovery, speech, buzzer and localization checks. It contains 43 `getattr(self, …)` guards so that tests can build the object without running `__init__` | Hard to review and to test honestly; production code is shaped by test shortcuts | Split along the seams that already exist (planner, validator, executor, recovery) without changing behaviour |
| A3 | Medium | No lifecycle nodes, start-up ordering or health checks | Start-up races have already caused bugs (model loading, IK service) | Add a readiness check that gates missions on the presence of required servers and topics |
| A4 | Low | 41 absolute and 18 relative topic names | Nodes cannot be namespaced as a group | Make names relative and set the namespace in the launch file |
| A5 | Medium | Capabilities are static lists in YAML (80 COCO names, 7 colours) | The planner may offer objects the loaded model cannot detect, or actions whose servers are down | Build the capability list at run time from the model's class names and from server availability |
| A6 | Medium | `eira_ws` re-implements exercises 06, 07, 11–13, 26–30 and adds voice, gestures, a mobile bridge, bag replay, sound patterns and RViz markers | About a fifth of the production code (2,812 of 13,472 lines) is outside the research path, untested on hardware, and partly duplicates vendor code that the master prompt says to preserve | Freeze these modules. Keep them out of the experiment launch. Decide later whether to keep or remove |
| A7 | Medium | The master launch recomposes Nav2 server by server and mixes pieces of two vendor bring-up families | Behaviour can differ from the tested vendor navigation in ways that are hard to see | Decide on one vendor bring-up as the base and document every deviation from it |
| A8 | Low | Result and bag directories default to `~/eira_ws/...`, but the workspace is `~/NeuroBotics/eira_ws` | Data lands outside the repository tree | Make the paths relative to a configured data root |
| A9 | Low | `package.xml` uses rosdep keys that do not resolve (`python3-ultralytics`, `python3-tf-transformations`); `nav2_msgs` is a hard dependency although its import is guarded | `rosdep install` reports errors | Correct the keys; document pip-only dependencies |

## T — Testing

| ID | Severity | Observation | Consequence | Proposed remedy |
|---|---|---|---|---|
| T1 | High | All 666 tests are unit tests with mocks. None starts `rclpy`, spins a node or uses `launch_testing` | Topic names, QoS, parameter declaration and timing between nodes are untested. Past robot failures were all of this kind | Add a small set of graph-level tests with stub hardware nodes |
| T2 | High | The simulation cannot run on the development laptop: Nav2 and the vendor interface packages are missing | Phase 5 is blocked | Install Nav2; copy `arm_msgs` and `arm_interface` sources from the robot and build them here |
| T3 | Low | README and validation report state 612 tests and clean lint; actual is 666 and 34 findings | Documentation drift | Generate these figures at release time, do not hand-write them |
| T4 | Medium | No continuous integration | Regressions are found by hand | A single workflow running tests and lint on push |

## H — Repository hygiene

| ID | Severity | Observation | Consequence | Proposed remedy |
|---|---|---|---|---|
| H1 | Critical | 31 modified and 106 untracked files since 2026-11-13, about 16,000 new lines, two whole packages | One disk fault or bad command loses several days of work; no way to roll back a change | Commit on a branch as the first approved action. Nothing else should be edited before that |
| H2 | Medium | Folder 08: `autopilot.py`, `traffic.py`, `city.launch.py`, `city_street.world` are gone; `.pyc` files and four broken symlinks remain | Earlier simulation work is unrecoverable from source | Confirm whether the deletion was intended |
| H3 | Low | Stray `log/` and `.pytest_cache/` at the repository root and in three packages | Clutter | Add ignore rules |
| H4 | Medium | No `LICENSE` file; placeholder maintainer e-mail. The exercise folders contain vendor source in a repository with a GitHub remote | Unclear terms for publishing a research artifact | Add a licence for the E-AIRA code; check the vendor's terms before the repository is cited in a paper |
| H5 | Low | Ten documents, one of 321 kB, already carry stale numbers | Drift | Keep one authoritative document per topic |

## F — Factory dependency (added 2026-11-17)

| ID | Severity | Observation | Consequence | Proposed remedy |
|---|---|---|---|---|
| F1 | High | The master launch includes or starts nine factory packages (`imu_filter_madgwick` launch, `yahboom_laser_filter`, `ekf_bringup`, `ira_laser_tools` configuration, `m3pro_bringup`, `M3Pro`, `arm_kin`, `arm_util`, `M3Pro_navigation`). `eira_bringup/package.xml` declares them. A missing one is logged as `[dependency_missing]` and the launch continues | E-AIRA silently depends on the factory workspaces; on a clean Jetson `rosdep` fails, and a launch can come up without its base pipeline | Migration plan M6–M11 and M14; a strict mode that refuses missions while a required component is missing |
| F2 | High | Inverse and forward kinematics exist only as the vendor service `get_kinemarics` (`arm_kin`) | The grasp path cannot run without the factory workspace | E-AIRA IK/FK checked against recorded vendor answers (M4, M10) |
| F3 | High | The arm command types (`arm_msgs`) belong to the vendor, and the firmware (inferred) is compiled against them | Any arm command needs the vendor interface package | Exact copy in `vendor_compat/arm_msgs`, verified against the installed definitions and live type information (M5) |
| F4 | Medium | Default `model_path` points into `~/yahboomcar_ws`; default `transformer_model_path` into `~/MODELS` | Perception depends on factory files | E-AIRA data directory with official weights (M9, M12) |
| F5 | Medium | Calibration and maps live inside vendor package trees: `arm_kin/param/offset_value.yaml`; maps written into `M3Pro_navigation/map/`; `common.yaml` edited in place | Values are not version-controlled and can be lost in a vendor update or reflash | Capture into E-AIRA configuration with origin noted (M3) |
| F6 | Medium | The firmware's ROS domain (30 in `start_agent.sh` and `joy.sh`) is recorded nowhere in E-AIRA | A shell with another domain sees no robot topics, and nothing reports why | State it in the system requirements; check it at launch |
| F7 | Medium | Licence of Yahboom code, URDF, meshes and message definitions is unknown, while copies sit in a repository with a GitHub remote (see H4) | Redistribution may not be permitted | Read the licence fields (inventory §9.2); ask Yahboom; use simple geometry by default |
| F8 | Medium | Licence duties of dependencies: Ultralytics AGPL-3.0 (imported in-process); `imu_filter_madgwick` GPL-3.0-or-later and `slam_toolbox` LGPL (separate processes) | Obligations for the published artifact | State them in the artifact's licence notes |
| F9 | Low | Undeclared dependencies (`whisper`, `sounddevice`, `espeak`, `mediapipe`, `joy`, PyTorch); declared but unused or unresolvable keys | Clean installs fail or silently lose features | Correct the `package.xml` files (M14) |
| F10 | Medium | Starting the hardware bridge requires a desktop session (`gnome-terminal` in `start_agent.sh`) and manual ordering | No unattended or remote start | Headless start unit (M11) |
| F11 | Medium | Which Orbbec driver version the robot uses (v1 or v2) is unknown; its defaults (registration off, point clouds on) differ from what E-AIRA requests | Behaviour can change silently if the driver is swapped | A/B comparison and a pinned version (M8) |

## V — Vendor code behaviour that affects reuse

These are observations about the course code. They are not fixed in place:
the exercise folders and the factory image stay unchanged. E-AIRA's
recreations must not inherit them.

| ID | Observation | Where |
|---|---|---|
| V1 | Demo nodes need a display and keyboard focus (`cv2.imshow`, `waitKey`) and are driven by key presses | 01, 22, 23, 27–30 |
| V2 | Callbacks block with `time.sleep` and join worker threads inside the callback | 22, 23, 29, 30 |
| V3 | Camera intrinsics and the hand-eye matrix are hard-coded; file paths are absolute under `/home/jetson` | 01, 22, 23, 28, 31, 32 |
| V4 | Depth is read at colour pixel coordinates without registration, after resizing 640×400 to 640×480 | 01, 22, 23 |
| V5 | `calibrate_arm.py` tests `adjust == 'y' or 'Y'`, which is always true: the calibration is written whatever is typed | 01 |
| V6 | `base_bringup.launch.py` builds an `update_costmap` node and never launches it | 17–19, 22, 23 |
| V7 | No timeouts, cancellation or error reporting in the transport state machines | 22, 23 |
