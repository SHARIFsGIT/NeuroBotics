# Audit remediation and validation

Author: E-AIRA maintainers. Target: ROSMASTER M3 Pro / Jetson Orin NX / ROS 2 Humble.

## YOLO/RViz pipeline: validation on 2026-11-15

The source suite and isolated `colcon test-result` pass with
**612 tests, 0 errors, 0 failures, 0 skipped**: Brain 261,
bringup 89, evaluation 37, manipulation 48, perception 133, simulation 44.
A clean isolated six-package build, flake8 with maximum line length 99,
`git diff --check` and installed master launch loading pass. Artifacts use
`/tmp/eira-yolo-*`; the robot's existing install was not replaced.

All three exercise-31 files were compared with the mission pipeline. Regression
coverage includes independent RGB inference without depth, actual cv_bridge and
OpenCV annotation rendering without calibration/TF, preserved image headers and
BGR colors, invalid/empty depth, original measurement timestamps and duplicate
depth suppression, cold-model acquisition timing, geometry failures isolated
from model retries, vendor Ultralytics import paths, bounded warmup, missing
optional tracker dependencies, identity retention through missed detections,
and small-object ROIs excluding background. RViz asset tests verify separate raw
and annotated topics and package installation of the preset.

The development host has no Torch, Ultralytics, model weights or live camera.
Model API boundaries use test doubles; these checks do not establish actual
GPU detection accuracy, Jetson throughput or the robot's current DDS graph.
Use [YOLO_RVIZ_DIAGNOSTICS.md](YOLO_RVIZ_DIAGNOSTICS.md) for the stationary
robot-side acceptance test. Raw RGB remains unannotated; `/eira/detect_image`
is the detector preview, and normal demand mode needs an active find request.

## Dabai depth and Humble logger fixes: validation on 2026-11-15

The full source suite and isolated six-package `colcon test` pass with
**569 tests, 0 errors, 0 failures, 0 skipped**: Brain 261, bringup 87, evaluation 37,
manipulation 48, perception 92, simulation 44. A clean isolated build succeeds;
flake8 at maximum line length 99, `git diff --check`, default/YAML coverage and
installed master launch loading pass. Outputs use `/tmp/eira-depth-*`; the
existing robot install was not replaced.

New tests cover fixed INFO status logging across changes in human severity,
explicit metric encodings, 21x21 ROI/full-box medians, invalid depth and the
optional cup-height estimate, 640x400/640x480 resize with intrinsics scaling,
depth/color CameraInfo selection and frame conflicts, calibration snapshots,
processing old frames without retimestamping, and every-tenth-frame diagnostics.
Depth CameraInfo is included in recording/replay sensor inventories.

These are mocked/synthetic checks, not a live Dabai calibration or physical
grasp trial. Resizing cannot register two physical cameras. Full-box samples
may include background; bbox ranging uses an assumed height and is labelled
estimated. Original capture timestamps remain intact, and the arm's independent
staleness rules are unchanged. See [DABAI_DEPTH_DEBUG.md](DABAI_DEPTH_DEBUG.md).

## Operator interface: validation on 2026-11-15

The source suite and isolated `colcon test` have **512 passing tests**, with no
errors, failures or skips: Brain 257, bringup 87, evaluation 37,
manipulation 48, perception 39, simulation 44. Flake8 with maximum line length
99 and `git diff --check` pass. A clean isolated six-package build succeeds;
artifacts are under `/tmp/eira-ux-*`. Installed entry points include
`mission_reporter`, `arm_state_relay` and `visualization_markers`, and the
installed master launch loads with `--show-args` using a writable temporary ROS
log directory. The robot's existing install was not replaced.

New tests exercise color/plain output, terminal control sanitization, actionable
errors with unchanged ROS evidence, quiet repeated perception updates, command
degree/radian display mapping, no fabricated startup/feedback, atomic mission
reports and late messages, bounded write retries, marker frames/colors/geometry,
stale-marker deletion, and nonblocking buzzer patterns including sound disable.
The simulator disables the command-state relay and retains measured simulated
joint feedback. Native drivers and actuator interfaces remain unchanged.

No physical servo/display calibration, buzzer trial or live RViz demonstration
was run here. The relay's joint states describe commanded poses and cannot
verify mechanical convergence or object holding. Marker correctness depends on
measured waypoint data and the existing TF tree. See
[OPERATOR_INTERFACE.md](OPERATOR_INTERFACE.md) for runtime use and acceptance.

## Jetson runtime fixes: validation on 2026-11-15

The full source suite and isolated six-package `colcon test` pass with
**359 tests, 0 errors, 0 failures, 0 skipped**: Brain 171, bringup 33,
manipulation 39, perception 35, evaluation 37, simulation 44. A clean isolated
six-package build, `flake8 --max-line-length=99 src`, parameter-default/YAML
coverage and `git diff --check` pass. Build/test/install outputs are under
`/tmp/eira-runtime-fix-*`; the robot's existing install was not replaced.

Added regressions exercise wrapped Phi-3 arrays, raw-response observability,
30-second default timeout, cancellation during nonblocking navigation settling
and retries, AMCL age/frame/covariance checks, bounded additional navigation
attempts, idle frame drops, demand-search termination, stale worker rejection,
request deduplication and explicit grasp/scan refresh tokens. Completed grasp
events cannot accidentally start another search. Stop cancels pending refreshes.

These are software checks with mocked interfaces. No Jetson CPU saving, actual
Phi-3 response reliability or physical AMCL recovery rate was measured here.
Covariance warnings are advisory; Nav2 status 6 is a generic abort and can have
causes beyond localization. Fixed waits do not establish that AMCL has converged.
The hardware test guide now distinguishes demand acquisition from continuous
tracking diagnostics. Existing copied parameter files must be updated separately.

## Research additions: validation on 2026-11-14

The six-package source suite and isolated `colcon test-result` report
**309 tests, 0 errors, 0 failures, 0 skipped**.

| Package | Passing tests |
|---|---:|
| eira_brain | 135 |
| eira_bringup | 33 |
| eira_manipulation | 39 |
| eira_perception | 21 |
| eira_evaluation | 37 |
| eira_simulation | 44 |

`flake8 --max-line-length=99 src` and `git diff --check` pass. A clean isolated
`colcon build --symlink-install` succeeds for all six packages. Build, install
and test artifacts use `/tmp/eira-research-*`; the existing workspace install
was not replaced. Installed evaluation/simulation entry points resolve, and
the simulation launch description loads with `--show-args`. Gazebo's native
`gz sdf -k` validator accepts the generated room and adapted M3 Pro URDF.

Coverage includes strict grounded prompting and repair/fallback, correlated
mission evidence, archive recovery, out-of-order terminal events, benchmark
reset/stop handling, metric denominators and confidence intervals, PNG/LaTeX
generation, bag lifecycle/replay isolation, seeded world generation, simulated
sensor processing, FK/IK and measured-feedback arm trajectory streaming.
Tests use synthetic data and mocked ROS interfaces; generated test charts are
not empirical research results.

Full Gazebo/Nav2 execution was not performed in this environment: Nav2 and the
vendor `arm_msgs`/`arm_interface` packages are unavailable locally. No hardware
benchmark or physical grasp trial was run. The planar base and arm bridge are
kinematic simulation components, not calibrated dynamics or contact models.
Default perception uses the learned detector; the optional oracle mode is
labelled and evaluated as a separate condition. Task completion is a controller
metric; actual grasp accuracy requires provenance-labelled held/not-held evidence.
See [RESEARCH_PROTOCOL.md](RESEARCH_PROTOCOL.md) for collection and reporting.

## Audit-finding mapping

| Finding | Implementation / regression coverage |
|---|---|
| Planning resumes after stop | Serialized mission generations; stopped/superseded workers cannot install plans. |
| CLI plan-only executes | Local preview path does not initialize ROS or publish a command. |
| Late Nav2 acceptance/result | Mission+attempt tokens; all accepted handles canceled, stale acceptances canceled immediately. |
| Reentrant FSM overlap | RLock serializes state changes; external LLM work stays outside the lock; server discovery uses nonblocking polling. |
| Last velocity outlives watchdog window | Independent watchdog no longer requires recent motion; gate also expires every velocity source. |
| Competing zero/nonzero writers | Managed launch routes controllers into one gate; explicit source ownership, stop and hazard precedence. |
| Bad launch-argument iteration | Includes use key/value pairs; launch tests exercise this contract. |
| Missing TF registration | Manipulation imports tf2_geometry_msgs; explicit clock/frame/staleness validation. |
| Hanging/stale IK | Finite response deadline, bounded retries, request generations; stop invalidates old callbacks. |
| Arm stop | Clears sequencer/IK and attempts a hold only from fresh, explicitly measured joint feedback. Reports whether hold was sent. |
| Uncorrelated events | Mission/action IDs required for Brain completion; exact expected event type; duplicate request suppression. |
| Late grasp success triggers timeout | Success handler returns after advancing; no stale deadline evaluation. |
| Silent release/home timeout success | Explicit matching completion required; timeout follows failure/retry policy. |
| Vision callback failures | Specific exception guards, model lifecycle diagnostics and bounded worker recovery. |
| Frozen image stream | Housekeeping checks last camera/target timestamps independently of callbacks. |
| Geometry timestamp/frame mismatch | Measurement-time TF; stale/wrong-frame/nonfinite pose rejection. |
| Object changes between frames | Persistent ID/IoU association; bounded smoothing and explicit reacquisition after loss. |
| Missing grasp prerequisites / partial invalid plans | Whole-plan validation, closed vocabulary and preceding-find prerequisite. |
| Unverified arm completion / premature sequence overlap | Minimum driver runtime, reported convergence checks, per-step deadline and contact-verification field. |
| Malformed YAML/JSON/Ollama responses | Schema/finite-value checks and bounded fallback/failure paths. |
| Recorder frame/database errors | Explicit paths respected, wrong-frame clicks rejected, atomic unique-temp replacement; Brain reloads per mission. |
| CLI unrelated status / short iteration-based timeout | Mission-correlated terminal state and monotonic waiting. |
| Missing TF/base startup / shared params_file | Optional robot/static TF; hardware arm-status parameters; separate scoped Nav2 parameter path. |
| Continuous unbounded inference | Active/idle frame-rate controls, bounded input backlog, configurable device/image size. |

## Previous orchestration baseline

The previous four-package source suite and `colcon test-result` reported **174 tests, 0 errors,
0 failures, 0 skipped**: Brain 85, manipulation 39, perception 21, bringup 29.
All 49 Python modules pass syntax/docstring/type-annotation structure checks.
`flake8 --max-line-length=99 src` and `git diff --check` pass. A clean isolated
`colcon build --symlink-install` succeeds for all four packages. The installed
master launch loads with `--show-args`, and the installed CLI help resolves.
Build/test outputs were isolated under `/tmp/eira-final-*`; no hardware processes
were launched and no low-level drivers were modified.

## What automated validation establishes

- All six packages build with `colcon build --symlink-install` using clean
  isolated build/install directories.
- Tests use pure numerical cases and mocked ROS topic/service/action interfaces.
- `test_launch.py` loads the real master description without starting hardware
  and verifies deferred dependency resolution and include-argument structure.
- Flake8 uses the requested maximum line length of 99.
- None of these checks establishes mechanical calibration, an ARM64 wheel/model
  ABI, servo stopping distance, encoder provenance, or a successful physical grasp.

## Remaining physical acceptance work

The repository lacks the vendor message definitions/driver source, gripper
width-angle table, measured arm mount/bin poses, robot map, fiducial poses,
transformer tensor ABI, and local model weights. The implementation reports
missing dependencies and rejects uncalibrated operations rather than claiming
they were validated.

`Curjoints` must be traced to an actual measured source before enabling
`joint_feedback_is_measured`. A published hold is a best-effort position command;
there is no verified Yahboom servo cancel interface in the supplied materials.
Use the robot's physical emergency stop for mechanical emergency stopping.

A single RGB-D view provides visible geometry, not hidden object thickness.
Volume metadata includes its model/uncertainty and is null without a supplied
thickness prior. A transformer fallback event means YOLO is running; it is not
proof that the proprietary model has been integrated.

The gate owns the final command only within the managed graph. Starting an
unmanaged publisher directly on `/cmd_vel` bypasses any software mux. Do not
run a second native controller/master/profile against the same hardware.

Optional rosbridge binds localhost and limits topics to commands/transcripts and
observability. Native driver topics, ownership and direct arm commands are not
part of that mobile interface. Generated build logs/environment snapshots may
contain secrets from the build environment and should not be published.
