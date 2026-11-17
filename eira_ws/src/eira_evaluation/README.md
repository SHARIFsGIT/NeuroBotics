# E-AIRA evaluation

Author: E-AIRA maintainers. Target: ROSMASTER M3 Pro / Jetson Orin NX,
ROS 2 Humble / Python 3.10.

This package records observations and generates reproducible reports. It does
not invent physical success labels or claim an empirical performance result.

## Mission evidence

```bash
ros2 run eira_evaluation mission_logger
# Optional simulation provenance:
ros2 run eira_evaluation mission_logger --ros-args \
  -p environment:=simulation -p random_seed:=42
```

Parameters: `results_dir=~/eira_ws/results`, `archive_prefix=mission_log`,
`flush_interval_s=1.0`, `environment=hardware`, `random_seed=-1`.
Supported environments are `hardware`, `simulation`, and `simulation_oracle`.
Oracle simulation is a separate condition, not learned-perception evidence.

The logger subscribes to `/eira/command`, `/eira/plan`, `/eira/status`,
`/eira/vision/event`, and `/eira/manipulation/event`. Messages require actual
Brain mission IDs before they are assigned to a mission. Legacy plain commands
are retained as unassigned evidence until a matching Brain identity arrives.

Daily UTC archives are `mission_log_YYYYMMDD.csv` and `.json`. CSV columns have
stable headers; per-action attempts, perception samples, contact outcomes and
recoveries use JSON array cells. JSON additionally retains the full event trace,
producer/receiver times, environment and seed. Writes are atomic and fsynced.
JSON is authoritative; missing/partial CSV projections are repaired on startup.
A writer lock prevents two logger processes from clobbering the same prefix.
Logger shutdown does not label still-running missions as failures.

## Metrics, PNG charts and LaTeX

```bash
ros2 run eira_evaluation metrics_calculator \
  ~/eira_ws/results/mission_log_20261114.csv --output-dir ~/eira_ws/results/report
```

The input may instead be the detailed JSON archive. Multiple inputs are accepted;
identical duplicate missions are deduplicated, conflicting duplicates are
rejected. Mixed hardware/simulation/oracle records require an explicit
`--environment` filter. The output contains `summary.txt`, `summary.json`,
`summary.tex` and three labelled PNG charts using matplotlib's headless Agg
backend. The LaTeX table uses `booktabs`; include `\usepackage{booktabs}`.

Definitions:

- **Task success:** controller-reported completion of all planned logical steps
  in eligible terminal missions,
  divided by eligible terminal missions. `DONE` alone is
  insufficient. Setup resets and explicit stop/control missions are excluded.
  Unsupported tasks acknowledged only by speech are failed benchmark trials.
  This metric does not establish physical object delivery; report it alongside
  independently verified grasp outcomes.
- **Logical action success:** successful logical steps divided by observed
  logical steps of that type in terminal missions. Retry attempts are grouped.
  A separate attempt-level metric preserves individual failed attempts.
- **Planning latency:** the Brain's measured complete planning time. LLM response
  latency includes the measured LLM-call budget, including calls that end in a
  fallback; selected-LLM response latency is also available separately in JSON.
- **Perception latency:** correlated search/find dispatch to found, including
  transport and any intervening active search. It is not GPU inference-only time.
- **Grasp accuracy:** verified held/not-held labels only; unknown contact outcomes
  are excluded and counted explicitly. A timed `grasped` event is insufficient.
- **MTBF:** observed active mission wall time divided by failed missions, excluding
  idle periods. With no observed failures the estimate is unavailable; the
  exposure is reported as a censored lower-bound observation, not infinity.
- **Recovery success:** logical steps eventually successful after retry/scan,
  divided by logical steps with any such recovery episode. Repeated scans of
  one step do not inflate the denominator.

Binomial rates include Wilson 95% intervals. Repeated commands in one environment
need not be independent; these intervals do not establish independent trials,
causal superiority, or publication-level external validity. Unfinished missions
are right-censored and listed separately from terminal denominators.

## Physical grasp labels

When an actual contact sensor or video/operator review establishes the outcome,
attach a provenance-labelled result to the logger:

```bash
ros2 topic pub --once /eira/evaluation/grasp_truth std_msgs/msg/String \
  '{data: "{\"mission_id\":\"ACTUAL_ID\",\"action_id\":\"1:1\",\"object_held\":true,\"source\":\"operator video review\"}"}'
```

This interface requires IDs, a boolean `object_held`, and a nonempty `source`.
It updates an unknown contact outcome without deleting the original event trace.
Re-run `metrics_calculator` after annotations. The benchmark's initial report can
remain NA until evidence has been supplied to the daily logger's archive.

## Serial benchmark

```bash
ros2 run eira_evaluation benchmark --command "Bring me a cup" --iterations 20 \
  --start-waypoint home --results-dir ~/eira_ws/results
```

Before each trial, a deterministic `purpose=benchmark_reset` Brain command
executes exactly one validated navigation action to the measured start waypoint.
This physically navigates the base; it never teleports hardware or fakes an AMCL
pose reset. Reset and trial records have separate IDs and phases. Ordinary trial
planning remains LLM-first with deterministic fallback.

The runner waits for matching mission terminal states and ignores unrelated
status messages. A failed/rejected reset aborts before the next trial. On a
trial/reset timeout it sends stop, waits for matching stop acknowledgement plus
a post-request zero `/cmd_vel`, records whether that handshake succeeded, and
ends the campaign. This confirms controller state, not a physical emergency stop
or object contact. No next trial is automatically started after a timeout.

Options include `--timeout` (600 s), `--reset-timeout` (300 s), `--stop-timeout`
(10 s), `--ready-timeout` (15 s), `--event-grace` (1 s), `--environment`,
`--seed`, and explicit
`--skip-reset`. Run against an isolated experiment graph: other frontends should
not inject missions during a campaign. A report and `benchmark_run.json` record
requested versus completed trials, reset IDs, timeouts and abort reason. A
calibrated `home` waypoint and operational Nav2 are required for default resets.
The observation grace period collects late plan/action messages after a terminal
status because delivery order across different DDS topics is not guaranteed.

## Tests

```bash
source /opt/ros/humble/setup.bash
python3 -m pytest -q src/eira_evaluation/test
python3 -m flake8 --max-line-length=99 src/eira_evaluation
```

Unit/integration tests use synthetic evidence and mocked ROS interfaces. Their
charts are test artifacts, not experimental results. No real benchmark trials
are run by tests.
