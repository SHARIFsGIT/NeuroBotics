# E-AIRA: Edge-based AI Robot Assistant for Multimodal Human–Robot Interaction and Autonomous Manipulation

**Target platform:** Yahboom ROSMASTER M3 Pro — Jetson Orin NX, dual 2-D LiDAR, Dabai_DCW2 (Orbbec) RGB-D camera, 6-DoF arm, mecanum base · **Middleware:** ROS 2 Humble

---

## Abstract

*E-AIRA* is an edge-deployed embodied-AI layer that converts natural-language
instructions into grounded mobile-manipulation behaviour on a commodity
research robot. The system adds a **cognitive orchestration layer** on top of
an existing, fully validated driver and skill stack — Nav2 navigation, YOLOv8
object detection, a transformer-based visual tracker, and analytic arm
kinematics — without modifying any low-level driver. A local LLM (Phi-3 via
Ollama) maps free-form commands onto a closed, seven-action vocabulary that
is validated against a waypoint database before execution; a deterministic
rule-based planner serves as the fallback and as the ablation baseline.
Perception fuses YOLOv8 acquisition, transformer-tracker following and RGB-D
depth into a 3-D target centroid in `base_link`, which a PID base-alignment
stage and the robot's existing inverse-kinematics service consume to grasp.
Every stage publishes machine-readable status events, giving the evaluation
harness end-to-end observability. This repository contains the complete
system: four ROS 2 packages, a single-command bringup, an IEEE-style
evaluation plan, and the audit trail linking every design constant to the
underlying validated course experiment.

**Keywords** — embodied AI, edge robotics, LLM task planning, mobile
manipulation, ROS 2, human–robot interaction

---

## 1. Introduction

Large language models unlock flexible task specification for household
robots, but award-winning systems must demonstrate more than prompting: they
must be *grounded* (plans validated against real robot capabilities),
*fully on-edge* (no cloud dependency — a privacy and latency claim), and
*reproducible* (every component measurable on standard hardware).

E-AIRA contributes:

1. **A validated-interface architecture.** The cognitive layer speaks only
   through ROS 2 interfaces that were first audited and confirmed working on
   this exact robot (course folders 01–33 of the parent workspace). No driver
   was rewritten; integration risk is isolated to four new packages.
2. **Resilient LLM planning with a deterministic baseline.** Phi-3 via
   Ollama plans; a template parser takes over on any LLM failure, and the
   same task set run under both planners yields the paper's planning
   ablation (H1, §6).
3. **A depth-fused target-pose contract.** YOLOv8 acquisition, transformer
   tracker following and pinhole depth reprojection converge on a single
   topic — `/target_pose` in `base_link` — decoupling "where is the object"
   from "how to grasp it".
4. **End-to-end observability.** `/eira/status`, `/eira/vision/event` and
   `/eira/manipulation/event` emit JSON event streams suitable for
   automatic success-rate and latency scoring.

## 2. System Architecture

```
                         ┌──────────────────────────────┐
   user (CLI / voice) ──►│        eira_brain            │
   /eira/command         │  LLM (Ollama/Phi-3) ⇄ rules  │
                         │  plan validation · FSM        │
                         └───┬──────────┬──────────┬───┘
             NavigateThroughPoses   /eira/vision/req   /eira/manipulation/req
                  (action)              │  ▲                │        ▲
                       ▼                ▼  │                ▼        │
        ┌────────────────────┐  ┌──────────────────┐  ┌──────────────────┐
        │  Nav2 (existing)   │  │ eira_perception  │  │ eira_manipulation │
        │  M3Pro_navigation  │  │ YOLOv8 acquire → │  │ PID base align → │
        │                    │  │ tracker follow → │  │ get_kinemarics   │
        │                    │  │ depth → TF →     │  │ IK + folder-23   │
        │                    │  │ /target_pose     │─►│ joint rules      │
        │                    │  └──────────────────┘  └──────────────────┘
        └─────────▲──────────┘          │                     │
                  │                     ▼                     ▼
        ┌─────────┴───────────────────────────────────────────────┐
        │ base stack (IMU→LiDAR merge→filter→EKF) · orbbec camera │
        │ arm_kin (kin_ik_fk) · arm_util  — all UNCHANGED drivers │
        └─────────────────────────────────────────────────────────┘
```

### 2.1 Package map

| Package | Role | Key files |
|---|---|---|
| `eira_brain` | LLM task planner, plan validation, action sequencing, Nav2 client | `llm_task_planner.py`, `ollama_client.py`, `eira_cli.py` |
| `eira_perception` | YOLOv8 acquisition + tracker handoff + 3-D centroid | `vision_manager.py` |
| `eira_manipulation` | PID base alignment, IK grasp via existing service | `grasp_executor.py`, `pid.py` |
| `eira_bringup` | One-command master launch + parameters + waypoints | `launch/eira_master.launch.py`, `config/*.yaml` |

### 2.2 Topic / service contract

| Interface | Type | Producer → Consumer | Provenance |
|---|---|---|---|
| `/eira/command` | `std_msgs/String` | CLI/voice → brain | new |
| `/eira/plan`, `/eira/status` | `String` (JSON) | brain → world | new |
| `navigate_through_poses` | `nav2_msgs/action/NavigateThroughPoses` | brain → Nav2 | folder 22 |
| `/eira/vision/request` · `/eira/vision/event` | `String` | brain ↔ perception | new |
| `/target_pose` | `geometry_msgs/PoseStamped` (`base_link`) | perception → manipulation | new |
| `/camera/{color,depth}/image_raw`, `camera_info` | `sensor_msgs` | orbbec → perception | folders 25–33 |
| `/eira/manipulation/request` · `…/event` | `String` | brain ↔ manipulation | new |
| `cmd_vel` | `geometry_msgs/Twist` | manipulation → base | folders 22–23 |
| `arm6_joints` / `arm_joint` | `arm_msgs/ArmJoints` / `ArmJoint` | manipulation → arm driver | folder 23 |
| `get_kinemarics` | `arm_interface/srv/ArmKinemarics` | manipulation → `kin_ik_fk` | folder 23 |
| `grasp_done`, `Curjoints`, `beep`, `set_joint5` | `Bool`/`CurJoints`/`UInt16`/`Int16` | legacy ecosystem | folders 22–23 |

## 3. Methodology

### 3.1 LLM task planner (`eira_brain`)

A fixed system prompt exposes the closed action vocabulary
(`navigate | find | grasp | release | home | speak | stop`) with few-shot
examples; sampling uses temperature 0.1. The answer passes through a
defensive JSON extractor (fences, prose, brace salvage) and a validator that
drops unknown or target-less actions **before** anything executes — the
vocabulary is the system's safety envelope. `navigate` targets are checked
against `waypoints.yaml`; unknown places abort with a diagnosable status
rather than a silent timeout.

The planner runs in a worker thread off the ROS executor; execution is a
10 Hz non-blocking FSM with per-action deadlines and a retry policy. On any
LLM failure (server down, timeout, unparseable answer) the deterministic
template parser takes over transparently — the run is tagged
`"planner": "fallback"` on `/eira/plan`, which is precisely the data needed
for the H1 ablation.

### 3.2 Multimodal perception (`eira_perception`)

YOLOv8 (`yolov8n.pt`, the exact audited weights path) runs
`model.track(persist=True, conf=0.4)` on every synchronized color+depth
pair — the proven folder-31/32 inference path, subscribed with sensor-data
QoS so best-effort camera publishers actually match. The target class is a
parameter (default `cup`) with case-insensitive bidirectional label
matching ("red cup" ↔ COCO `cup`); the brain's `find` request re-arms the
search session and overrides the class. The pipeline is never headless:
every frame is annotated (boxes, class, confidence, live distance) and
published on `/eira/detect_image`.

3-D estimation follows the audited grasp pipeline: pinhole deprojection with
the **live** `camera_info` K (rather than the course code's hard-coded
intrinsics), ROI-median depth at the bounding-box center handling both
`16UC1` (mm) and `32FC1` (m), and a live TF lookup through the eye-in-hand
chain to `base_link`. `/target_pose` publishes whenever the target is
visible with valid depth; `lost`/`timeout` events let downstream stages
abort safely.

### 3.3 Manipulation (`eira_manipulation`)

Stage 1 aligns the base: angular PID on the target bearing, linear PID on
the range error to a pre-grasp standoff (0.19 m), SI-rescaled from the
proven folder-32 gains, with hard velocity clamps, a settle-count exit
criterion and stale-target/watchdog aborts. Stage 2 transforms the target
into the arm base frame (live TF when `arm_base_frame` is set, calibrated
static mount offset otherwise) and sends the **unchanged** IK request to
`get_kinemarics` — including the audited conventions of `grasp_transport.py`
(folder 23): −1.5 cm X pre-compensation, 1.396 rad grasp pitch, the
`180 − joint1` base reflection, the joint-4 ≤ 90° clamp, and the joint-5
wrap rules. Grasp completion re-publishes the legacy `grasp_done` topic so
the pre-existing transport ecosystem remains composable.

## 4. Reproduction

```bash
# 1. On the Jetson (robot packages + map present):
cd ~/eira_ws
colcon build --symlink-install
source install/setup.bash

# 2. Local LLM (optional — fallback planner works without it):
ollama pull phi3 && ollama serve

# 3. Record waypoints interactively from RViz ("Publish Point" tool):
ros2 run eira_brain waypoint_recorder     # then name each click in the
                                           # terminal; updates waypoints.yaml
#    (or edit src/eira_bringup/config/waypoints.yaml by hand, § file header)
#    Rebuild afterwards so a non-symlinked install picks up the file.

# 4. Full system:
ros2 launch eira_bringup eira_master.launch.py map:=$HOME/map/map.yaml

# 5. Issue a task:
ros2 run eira_brain eira_cli "bring me a cup from the kitchen"
```

Monitoring: `ros2 topic echo /eira/status`, `ros2 topic echo /eira/plan`,
RViz on `/target_pose` + `/eira/detect_image`. Driver-only development
machines: all robot-driver includes degrade to warnings
(`use_base:=false` …).

## 5. Limitations

- The transformer tracker of folder 33 (`smart_tracker`) is not yet in the
  loop; YOLOv8's own tracking carries both acquisition and following.
  Re-adding it as an external box source is future work once its output
  topic is confirmed on the robot.
- `arm_base_frame` (or the static mount offset) must be calibrated once;
  the audited TF tree from `car_base.launch.py` is expected to provide it.
- No active search: `find` does not sweep the base when the object is out
  of view (planned extension — rotational scan behaviour in the brain).
- Nav2 and the alignment stage both write `cmd_vel`; the brain sequences
  them so they never overlap, but a mux (twist_mux) would harden this.

## 6. Evaluation Plan

**Hypotheses.**
- **H1** (planning): LLM plans complete unseen task phrasings at a higher
  end-to-end success rate than the deterministic baseline; both ≥ 90 % on
  the in-grammar set.
- **H2** (latency): total planning latency (command → first action) stays
  under 3 s at the edge for ≥ 95 % of commands.
- **H3** (perception): depth-fused centroid error ≤ 3 cm RMS against
  motion-capture / tape-measured ground truth at 0.3–1.5 m.
- **H4** (manipulation): grasp success ≥ 80 % over 50 trials across 5
  object classes and 3 placements, with no unsafe base speeds (logged
  `cmd_vel` envelope).

**Protocol.** 30-command benchmark (10 in-grammar, 10 paraphrase, 10
out-of-domain — measuring safe refusal); each logged via
`/eira/plan`, `/eira/status`, `/target_pose` (rosbag2) and scored offline.
Baselines: rule-based planner (H1), cloud LLM vs. edge Phi-3 (H2,
connectivity-ablated), flat-icondetector vs. E-AIRA acquisition (H3),
fixed-pose grasping vs. E-AIRA alignment (H4).

**Metrics.** task success rate; plan validity; command→first-action
latency; centroid RMSE; grasp success; interventions per task; unsafe-event
count; mean Jetson power draw (telemetry `tegrastats`) for the edge claim.

## 7. Repository Layout

```
eira_ws/
├── README.md                      ← this document
└── src/
    ├── eira_brain/                LLM planning + sequencing + CLI
    ├── eira_perception/           YOLOv8 + tracker + 3-D target pose
    ├── eira_manipulation/         PID alignment + IK grasping
    └── eira_bringup/              master launch, parameters, waypoints
```

Every non-obvious constant in the code carries a comment naming the audited
course file it comes from — the audit trail doubles as the reproducibility
appendix of the paper.
