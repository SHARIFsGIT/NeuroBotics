# Reproducible evaluation and paper preparation

Author: E-AIRA maintainers. Target: ROSMASTER M3 Pro / Jetson Orin NX / ROS 2 Humble.

These tools provide evidence collection and analysis, not a claim of conference
acceptance, superiority or an achieved experimental result. Software tests use
synthetic evidence; their charts are never paper results.

## End-to-end collection

```bash
ros2 launch eira_bringup eira_master.launch.py \
  use_evaluation:=true use_recording:=true map:=/absolute/path/measured_map.yaml

ros2 run eira_evaluation benchmark --command "Bring me a cup" --iterations 20 \
  --start-waypoint home --results-dir ~/eira_ws/results
```

`home` must be measured and navigable. Each reset is a trusted navigation-only
mission, excluded from trial denominators. Reset failure aborts the campaign.
Trials remain LLM-first; invalid model output gets one repair attempt before
validated deterministic fallback. Ordinary unsupported instructions are not
silently converted into success. A terminal observation grace period handles
late plan/action messages across separate DDS topics.

Benchmark timeouts issue stop and require a matching control acknowledgement
and a fresh zero velocity before ending the campaign. This is controller-level
stop evidence, not verification of physical stopping distance. Do not run other
mission producers in the same experiment graph.

The benchmark resets the **base pose**, not the scene or held object. Define and
apply a repeatable cup/arm/environment reset protocol between independent trials.
A repeated command on a changed scene is a sequential-task experiment and must
be described as such. Domain-randomized simulation is resampled per launch;
record every condition's seed and retain `condition.json` plus generated assets.

## Output and metrics

Daily UTC files are `~/eira_ws/results/mission_log_YYYYMMDD.csv` and `.json`.
Benchmark archives have their own unique prefix to avoid conflicting with the
live logger. CSV headers include mission identity, command, planner/reason,
actions/attempt durations, terminal state, error reason, seed and environment.
The detailed JSON retains the message trace and producer/receiver timestamps.

```bash
ros2 run eira_evaluation metrics_calculator \
  ~/eira_ws/results/mission_log_YYYYMMDD.csv --output-dir ~/eira_ws/results/paper_report
```

Reports include task success, logical and attempt action success, planning/LLM
and search-to-found latency, verified held-object accuracy, recovery success,
and active-operation MTBF. PNG charts have titles, axis labels, grids and sample
counts; LaTeX output is an escaped `booktabs` table. Binomial estimates include
Wilson 95% intervals. Zero observations and unverified contact are NA, not zero.
No-failure exposure is reported as censored observation rather than infinite MTBF.
See the [evaluation package](../src/eira_evaluation/README.md) for denominators.

Latencies are observed wall/monotonic processing durations, distinct from ROS
sensor time. Plan/status messages also carry ROS timestamps for synchronization.
Do not compare simulation wall latency with Jetson hardware latency without
reporting real-time factor, host CPU/GPU and rendering load.

## Grounded prompting and ablation evidence

The system prompt lists currently loaded waypoint names, configured detector
classes, supported colors, the closed primary action vocabulary and three valid
examples. It requests an array-only answer. Responses are parsed as complete
JSON arrays after removing Markdown fence markers and text before the first
`[` and after the last `]`, then all actions,
resources and grasp prerequisites are validated together. Legacy `speak` is
retained for existing clients/fallback acknowledgements.

`/eira/plan` retains existing fields and adds `planner_reason`, `fallback_reason`,
`llm_response_ms`, `planning_latency_ms`, `llm_attempts`, `benchmark_reset`,
`wall_time`, `monotonic_ns`, and `ros_stamp_ns`. LLM time is the cumulative observed
call budget, including transport retry/repair time; it is not token-generation
throughput. Separate model planning failure from downstream perception/navigation
failure when reporting causal claims.

Phi-3 calls use a 30-second per-request timeout by default. The client omits
Ollama's legacy object-only `format: json` option because the plan root is an
array. Model replies are available in readable debug-level `Model reply` logs;
normal terminal output is concise. CLI `--json` explicitly selects machine output.
Demand-only vision stops after each acquisition; additional one-shot updates
are explicitly requested during a grasp. Record `continuous_mode` and refresh
period as experimental settings. Idle inference is disabled by default; CPU
savings must be measured rather than inferred as a fixed percentage.

Navigation adds a configurable 3-second post-success settling interval and
10-second retry backoff, with two additional navigation attempts. These waits
contribute to mission duration but are not part of a completed navigation
attempt's controller duration. AMCL covariance is an advisory confidence check,
not independent evidence that localization or a physical destination is correct.

Plan ablations before looking at results: fixed command sets and environments,
randomized/counterbalanced run order, identical resets, explicit inference/model
versions, and a declared statistical unit. Preserve hardware, learned simulation,
and oracle control regression as separate cohorts. Repeated trials on one robot
may be correlated; Wilson intervals alone do not establish independent samples.

## Grasp truth

The manipulation sequencer reports completion separately from contact evidence.
Annotate actual held/not-held outcomes from a sensor or documented operator/video
review on `/eira/evaluation/grasp_truth`, with the exact mission/action IDs.
Unknown outcomes remain excluded from grasp accuracy and counted as unverified.
Retain both positive and negative labels and their provenance. A `grasped` event,
measured joint convergence, or simulated kinematic reach does not prove holding.

## Recording and replay

`mission_recorder` starts per mission, recording compressed RGB, registered depth,
CameraInfo, scan, TF/static TF, velocity, plans, status, requests and outcomes.
Storage is `~/eira_ws/bags/mission_UTC_ID/bag/`; `mission.json`, recorder logs,
QoS overrides and `boundary_events.jsonl` live alongside it. Finalization uses
SIGINT with bounded TERM/KILL fallback. A manifest distinguishes complete,
incomplete and failed recordings and discloses process/discovery startup gaps.
Two recorders may briefly overlap across rapid mission transitions. Sidecar
status/plan evidence preserves boundaries but does not invent missing camera
frames. Retain parameter files corresponding to the hashes in the manifest.

```bash
# Default analysis: all topics, including actuators/TF, are remapped under /eira/replay.
ros2 run eira_brain mission_replayer ~/eira_ws/bags/mission_UTC_ID --dry-run
ros2 run eira_brain mission_replayer ~/eira_ws/bags/mission_UTC_ID

# Explicit isolated-domain reprocessing; no recorded actuator commands are replayed.
ros2 run eira_brain mission_replayer ~/eira_ws/bags/mission_UTC_ID \
  --mode isolated --domain-id 42 --clock --decode-color --include-requests
```

For the second mode, launch reprocessing nodes in the same **unused, localhost-only**
domain with `ROS_DOMAIN_ID=42 ROS_LOCALHOST_ONLY=1` and `use_sim_time=true`.
Do not launch physical drivers there. The replayer requires a domain different
from its parent and never publishes recorded `/cmd_vel` or arm joint commands
on their original names. Use the simulation bridge for arm recomputation.
Original actuator trajectories remain available in the default remapped analysis.
ROS TF frame IDs are preserved, so remap both TF topics when using namespaced
perception-only replay rather than domain isolation.

## Recommended paper artifact set

Retain software revision, model/weights identifiers, exact prompts and parameters,
map/waypoints/calibration, platform/JetPack/ROS versions, all condition seeds,
trial/reset manifests, CSV/JSON, bags and grasp labels. State exclusions, censored
trials, recovery definitions, failed recordings, annotation criteria and missing
labels. Report raw counts and uncertainty with summary rates. Publish only
consented/redacted sensor data and never generated environment snapshots that
contain credentials. No real performance numbers are supplied by this change.
