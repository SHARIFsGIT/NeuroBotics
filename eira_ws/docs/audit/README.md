# E-AIRA Phase 0 audit — index and progress report

First audit: 2026-11-17. Extended the same day with the factory-dependency
audit requested in your "Critical Clarification". Scope: the whole VS Code
workspace `~/NeuroBotics` (33 exercise folders, `eira_ws/`, tooling), read-only.

No existing file was modified. A hash of `eira_ws/src` and of `git status`
was taken before and after the audit's test and build runs and is identical.
Nothing has been staged or committed.

## Documents

| Document | Answers |
|---|---|
| [existing_work_audit.md](existing_work_audit.md) | What exists, what was executed during the audit, what evidence supports each capability |
| [exercise_mapping.md](exercise_mapping.md) | Exercises 01–33 and later work, mapped to the E-AIRA architecture |
| [exercise_factory_dependency_mapping.md](exercise_factory_dependency_mapping.md) | Every README command of exercises 01–33: purpose, actual dependency, type, need, action |
| [jetson_factory_image_inventory.md](jetson_factory_image_inventory.md) | Factory software and hardware on the Jetson, as far as known; what the inventory script will confirm |
| [jetson_inventory/jetson_readonly_inventory.sh](jetson_inventory/jetson_readonly_inventory.sh) | Read-only script that collects the Jetson facts (to be run by you) |
| [factory_independence_assessment.md](factory_independence_assessment.md) | What E-AIRA can recreate, what must stay a system dependency, licensing, feasibility verdict |
| [eira_self_contained_migration_plan.md](eira_self_contained_migration_plan.md) | Step-by-step plan to make E-AIRA independent of factory application files |
| [eira_workspace_dependency_matrix.md](eira_workspace_dependency_matrix.md) | Internal and external dependencies of every E-AIRA package |
| [current_system_architecture.md](current_system_architecture.md) | Hardware, vendor stack, `eira_ws` node graph, TF, interfaces as they are today |
| [reuse_and_integration_plan.md](reuse_and_integration_plan.md) | Reusable modules, missing components, proposed architecture, research opportunities, roadmap, open questions |
| [technical_debt.md](technical_debt.md) | Risk register and debt list with severity and proposed remedy |

Existing documents with an overlapping purpose were checked first and left
untouched: `docs/EXERCISE_INTEGRATION.md` (earlier exercise ledger),
`docs/RESEARCH_PROTOCOL.md` (evaluation protocol), `docs/SAFETY_AND_VALIDATION.md`
(validation history). The audit documents cite them instead of repeating them.

## Headline findings

1. **`eira_ws` already exists and is large.** Six `ament_python` packages,
   about 13,500 lines of source and 8,000 lines of tests. The master prompt's
   Phases 3–4 are therefore partly done; the real work is verification,
   consolidation and research definition, not greenfield construction.
2. **Most of that work is not committed.** The last commit is 2026-11-13.
   Since then 31 tracked files changed (+5,310 / −2,845 lines) and 106 files
   are untracked, including two whole packages. There is no Git checkpoint.
3. **Software checks pass on the development laptop.** 666 unit tests pass,
   all six packages build. Lint is not clean (34 flake8 findings), and the
   README's figures (612 tests, lint clean) are out of date.
4. **The exercises ran on the robot; E-AIRA has not been validated end to
   end.** You report that all 33 exercises ran successfully on the robot, and
   that E-AIRA was tested only in part. Neither is backed by logs, bags, maps
   or measurements in this repository.
5. **The exercise folders are command records plus copies of a few vendor
   files.** The software those commands run lives on the Jetson, in at least
   two factory workspaces (`~/yahboomcar_ws`, `~/M3Pro_ws`), the micro-ROS
   agent workspace and home-directory scripts. Of 140 README lines, 21 start
   the hardware bridge and 7 move the arm directly.
6. **The true hardware layer is small.** It consists of the controller-board
   firmware, reached through the micro-ROS agent over `/dev/myserial`, and
   the Orbbec camera driver. The board probably also carries both LiDARs (no
   exercise starts a LiDAR driver). Everything else the exercises use is
   application software that E-AIRA can own.
7. **E-AIRA still depends on factory software today.** The master launch
   calls nine factory packages and `package.xml` declares them, so `rosdep`
   would fail on a clean Jetson. The grasp path needs the vendor IK service.
   The default YOLO weights path points into `~/yahboomcar_ws`.
8. **Independence is feasible, with three conditions.** The firmware's arm
   message types must be reproduced exactly; an E-AIRA IK must match the
   vendor IK; the robot description and mesh licensing must be settled. See
   `factory_independence_assessment.md`.
9. **The camera is mounted on the arm (link `arm4`).** Every target pose in
   `base_link` depends on arm joint angles. This is the largest unverified
   link in the manipulation chain (`technical_debt.md` G1–G3).
10. **Some prompt assumptions differ from the workspace:**
    - "Transformer tracking" is a vendor binary;
    - relocalization is AprilTag, not ArUco;
    - the arm has five positioning joints plus a gripper;
    - there are two LiDARs.
11. **Research definition is the main open area.** Plan-level LLM-to-robot
    grounding is well-covered prior art; novelty must come from measured edge
    behaviour and reliability.

## The Jetson inventory is pending

The Jetson could not be reached during the audit: Tailscale listed it offline
and SSH timed out. The laptop also has no SSH key for it. Facts that need the
Jetson are marked "pending" in the documents. Running
`jetson_inventory/jetson_readonly_inventory.sh` once, as described in
`jetson_factory_image_inventory.md` §2, completes them.

## Phase status

| Phase | Status | Note |
|---|---|---|
| 0 — Codebase audit | Complete except the Jetson inventory; awaiting review | This folder |
| 1 — Research definition | Not started | Waits for approval and for answers to the open questions |
| 2 — Architecture design | Proposal only | `reuse_and_integration_plan.md` §4; `eira_self_contained_migration_plan.md` §2 |
| 3 — Workspace integration | Partly pre-existing; factory-independence migration planned | `eira_ws` exists, uncommitted, unvalidated end to end |
| 4 — Core implementation | Partly pre-existing | Same |
| 5 — Simulation and testing | Unit level only | Full simulation cannot run on this laptop (no Nav2, no vendor interfaces) |
| 6 — Hardware validation | Not started | Requires explicit authorization |
| 7 — Experimental evaluation | Not started | Tooling exists, no data |
| 8 — Paper and thesis | Not started | |

## What was executed during the audit

| Check | Command or method | Observed result |
|---|---|---|
| Unit tests | `python3 -m pytest -p no:cacheprovider -q src` (in `eira_ws/`) | 666 passed in 3.5 s |
| Per package | same, per `src/<pkg>` | brain 302, perception 146, bringup 89, manipulation 48, simulation 44, evaluation 37 |
| Lint | `python3 -m flake8 --max-line-length=99 src` | 34 findings (17 F811, 14 E501, 3 E128); exit code 1 |
| Build | `colcon build` with build/install/log redirected outside the workspace | 6 packages finished |
| Source integrity | md5 over `eira_ws/src` and `git status --porcelain --ignored`, before and after | identical |
| Literature IDs | 22 arXiv abstract pages fetched and titles compared | all 22 match |
| README coverage | per-folder count of non-blank README lines compared with the mapping table | 140 of 140 lines mapped; 2 folders without README noted |
| Jetson reachability | `tailscale status`, `ping`, `ssh -o BatchMode=yes` | peer offline; ping and SSH timed out |
| Inventory script | `bash -n`; full dry run on the laptop; modification-time check of `$HOME` | syntax OK; 580 lines; no file changed by the run |
| Apt availability | `apt-cache policy ros-humble-*` on the laptop's Humble index | Nav2, SLAM Toolbox, Cartographer, RTAB-Map, `robot_localization`, `imu_filter_madgwick`, `laser_filters`, `apriltag_ros`, `orbbec_camera` available; `micro_ros_agent`, `ira_laser_tools`, `slam_gmapping` not |
| Upstream licences | `package.xml` and `LICENSE` files fetched from the upstream repositories | listed in `jetson_factory_image_inventory.md` §6–8 |

Not executed: any ROS node, any launch file, any simulation, any command on
the Jetson, any hardware command. Web search was unavailable, so the search
for closely overlapping papers is still to be done in Phase 1.
