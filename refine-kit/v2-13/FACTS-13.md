# FACTS-13 — verified ground truth for folder "13. lidar guard"

BINDING for all authoring (v1 PARTS + v2 exec spec). Sources are READ-ONLY.
Every claim below was verified against the files on disk. Never contradict; never invent beyond.

## 1. Files (splitlines numbering; both .py files have NO trailing newline)

| file | lines | sha256[:12] |
|---|---|---|
| README.md | 5 | 7de1ece640db |
| laser_driver.launch.py | 42 | dadf5ff3f9b1 — BYTE-IDENTICAL to folders 11 and 12 |
| laser_Warning.py | 145 | b1cf2d67a4d5 |

README differs from folder 12's ONLY at L5: `ros2 run yahboom_M3Pro_laser laser_Warning`
(tracker's said laser_Tracker). L1/L3 identical commands; L2/L4 blank separators.
Driver: six imports (Node L6 unused, comment admits just-in-case); two EAGER
os.path.join path builds (ira_laser_tools merge_multi.launch.py, yahboom_laser_filter
laser_filter_node.launch.py); returns LaunchDescription with 2 IncludeLaunchDescription;
starts ZERO nodes itself; runs merger then filter (run phase, illustrative); the warning
node is NOT started by it — README L5 does that.

## 2. laser_Warning.py — verified quirks (line numbers real)

- L1 `#ros lib`, L8 `#commom lib` — typo "commom" IN SOURCE.
- L6 UInt16 import comment: buzzer ON/OFF message type. NEW vs tracker: the guard's
  extra channel. `UInt16()` default value is 0 = beep OFF.
- L11 `import time`, L12 `from time import sleep` — BOTH DEAD (never used).
- L13 star-import `yahboom_M3Pro_laser.common` supplies `Bool` and `SinglePID`;
  module NOT in this folder — internals unknown, label inferred. Vendor comment on L13.
- L15 `print ("improt done")` — typo IN SOURCE ("improt"), space after print.
- L16 `RAD2DEG = 180 / math.pi` ≈ 57.29578 deg/rad.
- L18 class `laserWarning(Node)`; L19 `def __init__(self,name)` — name passed in;
  L20 `super().__init__(name)`.
- Subs: L24 `/scan` LaserScan → registerScan depth 1; L26 `/JoyState` Bool →
  JoyStateCallback depth 1. Pubs: L30 `/cmd_vel` Twist depth 1; L32 `/beep` UInt16
  depth 1 (THE guard channel).
- Params L35-42: linear 0.5, angular 1.0, LaserAngle 45.0, ResponseDist 0.55.
  VERIFIED QUIRK: `self.linear` (L36) and `self.angular` (L38) are read once and NEVER
  used again — no clamp exists anywhere (L35's own comment admits for linear:
  "not actually used in this script, but declared"). LaserAngle/ResponseDist ARE used.
- L45 `self.Joy_active = False`.
- L46 comment "controls the steering wheel" — there is no steering wheel on a
  differential-drive robot; stale/loose wording, quote it, do not endorse it.
- L47 comment "tuned a bit more aggressively than the tracker (3.0, 0.0, 5.0)" —
  REAL cross-folder reference: the tracker is folder 12's laser_Tracker (ang Kp=2, Kd=2).
- L48 `self.ang_pid = SinglePID(3.0, 0.0, 5.0)` — the ONLY PID; no linear PID exists.
- L50-52 JoyStateCallback: isinstance guard against custom Bool; `Joy_active = msg.data`.
- registerScan L54-124:
  - L56 `ranges = np.array(scan_data.ranges)`.
  - L58 comment says "front 90-degree cone" — with ±45 strict that is UP TO just
    under 90 degrees total; wording is the author's, the inequality is the truth.
  - L59-60 two PARALLEL lists: minDistList (distances) + minDistIDList (DEGREE angles).
  - L63 loop over every beam; L65 `angle = (angle_min + angle_increment*i) * RAD2DEG`.
  - L68 cone STRICT `abs(angle) < self.LaserAngle` AND `ranges[i] !=0.0` (space before
    colon at line end; `!=0.0` no space — source fidelity). inf PASSES (!=0.0 true);
    0.0 readings (vendor no-return) are excluded.
  - L73 `if len(minDistList) == 0: return` — NO publish, NO buzzer write: motors hold
    last /cmd_vel AND /beep latches its last value.
  - L76 `minDist = min(minDistList)`; L78 `minDistID = minDistIDList[minDistList.index(minDist)]`
    — argmin via index(); ties resolve to the FIRST occurrence = lowest i = most
    negative qualifying angle (beam order runs −44.0…+44.0 for the fused ring).
  - L81-83 Joy gate: publishes all-zero `Twist()` EVERY scan while held (active brake),
    then returns — BEFORE the alarm block, so /beep is NOT refreshed under Joy either.
  - L85 `print("minDist: ", minDist)`.
  - L89 alarm: `if minDist <= self.ResponseDist and minDist != 0.0` — second clause is
    belt-and-suspenders (cone already excluded exact 0.0); inf ≤ 0.55 is False; NaN
    fails both comparisons.
  - L90-92 `b = UInt16(); b.data = 1; pub_Buzzer.publish(b)` — BEEP ON.
    L95 else `pub_Buzzer.publish(UInt16())` — default 0, BEEP OFF (trailing space
    after `UInt16()) ` in source).
  - L98 `velocity = Twist()`; L99 `print("minDistID: ", minDistID)` — source line ends
    with a TAB character (fidelity; preserve verbatim).
  - L103 `ang_pid_compute = self.ang_pid.pid_compute(abs(minDistID) / 72, 0)` — 72 is
    a bare magic number the file never explains; abs() → error is always ≥ 0;
    target 0. NOTE: no snap logic here (tracker L96 had the 0.55 snap — guard has none).
  - L106-110 sign branches: `0 < minDistID` → z = +compute (left/CCW); `minDistID < 0`
    → z = −compute; exactly 0.0 → neither, z stays 0.0.
  - L112 `print("orin_angular.z: ", ...)`.
  - L115 deadzone `abs(ang_pid_compute) < 0.5` → z = 0.0.
  - L118 damping `velocity.angular.z = velocity.angular.z * 0.5` — comment says 50%,
    code matches (tracker used 0.6).
  - L120 `print("angular.z: ", ...)`.
  - L123 comment: "linear.x is never set here, so the robot stays perfectly still and
    just spins in place!" — TRUE: no linear PID, linear.x never assigned; Twist default
    0.0. The guard NEVER drives forward.
  - L124 `self.pub_vel.publish(velocity)`.
- exit_pro L127-132: cmd1 = `ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist `
  (trailing space) + cmd2 zero-YAML quoted string; `os.system(cmd)` shell brake from
  outside the node. Note: the brake zeroes /cmd_vel but does NOT touch /beep.
- main L134-145: rclpy.init(); `laserWarning("laser_Warnning_a1")` — typo "Warnning"
  (double n) IN SOURCE at L136; `print ("start it")` L137 (space after print);
  try/spin/except KeyboardInterrupt: pass/finally: exit_pro → destroy_node → shutdown.
  VERIFIED: file never calls main() and has no __main__ guard — ros2 run works via the
  package setup.py entry point (NOT in this folder; label inferred).

## 3. Canonical math (Kp-term view, Ki=0; label illustrative)

Fused ring (illustrative, consistent with folders 10/11/12): 360 beams,
`angle_i = -180 + i` deg (angle_min = -pi, increment = pi/180).
Cone strict |angle| < 45.0 AND ranges[i] != 0.0 → beams i = 136..224 = 89 beams;
exactly-45.0-degree beams EXCLUDED; inf passes the != 0.0 test.

Steering chain: e = |minDistID| / 72 → u = pid_compute(e, 0) → sign branch →
deadzone |u| < 0.5 → z = 0 → damping z ×= 0.5 → publish.

- Kp-view: u = 3·e = 3·(|a|/72) = |a|/24.
- Deadzone: |a|/24 < 0.5 ⟺ |a| < 12 deg (tracker: 18 deg with Kp=2 — guard is tighter).
- Boundary: |a| exactly 12 → u = 0.5, `< 0.5` is False → passes → z = ±0.25.
- Ceiling: |a| → 45⁻ → u → 3·(45/72) = 1.875 → z → ±0.9375 rad/s (tracker: ±0.75).
- Alarm: minDist ≤ 0.55 (and ≠ 0.0) → /beep 1, else /beep 0.
- Kd caveat: SinglePID(3.0, 0.0, 5.0) has a LARGE Kd; on a STEP change (first call
  after a scene change) the derivative term adds a same-sign transient — every u/z
  number above carries `ill` in exec dbg; caps may mention the transient once
  (first call of a wave), never dwelt on.
- argmin ties: first occurrence = lowest i = most-negative angle in the cone.

### Canonical wave table (EXACT numbers — Kp-view, Ki=0; label illustrative)

| wave | scene | minDist | minDistID | beep | e=|a|/72 | u=3e | z sign | deadzone L115 | z final ×0.5 | /cmd_vel |
|---|---|---|---|---|---|---|---|---|---|---|
| gate | JoyState False arrives first | — | — | — | — | — | — | — | — | — |
| A | pillar 0.90 m @ +14 deg (far, left) | 0.90 | +14.0 | 0 (0.90 > 0.55) | 0.194 | 0.583 | + | pass | +0.292 | (0.0, +0.292) spin left |
| B | 0.70 m @ +20 deg | 0.70 | +20.0 | 0 | 0.278 | 0.833 | + | pass | +0.417 | (0.0, +0.417) |
| C | 0.48 m @ 0 deg (INSIDE zone) | 0.48 | 0.0 | 1 | 0 | 0 | — | 0 < 0.5 → 0.0 | 0.0 | (0.0, 0.0) still + beeping |
| D | 0.50 m @ −20 deg (right, in zone) | 0.50 | −20.0 | 1 | 0.278 | 0.833 | − | pass | −0.417 | (0.0, −0.417) spin right + beeping |
| E | nothing valid in front | — | — | LATCH 1 | — | — | — | — | — | NO publish; /beep stays at 1 from D; motors hold last cmd |
| F | 0.80 m @ +8 deg (clear) | 0.80 | +8.0 | 0 (else branch publishes UInt16()) | 0.111 | 0.333 | + | 0.333 < 0.5 → 0.0 | 0.0 | (0.0, 0.0) quiet |
| Joy | /JoyState True (human) | — | — | LATCH (not refreshed) | — | — | — | — | — | zero Twist EVERY scan, L83 return before alarm |
| halt | Ctrl+C | — | — | — | — | — | — | — | — | except pass → finally → exit_pro brake (/cmd_vel zero; /beep untouched) → destroy → shutdown |

Wave order for the exec spine: gate → A → B → C → D → E → F → Joy → Joy-release
(JoyState False again, tracking resumes next scan) → halt.

## 4. Cross-folder context (guard vs tracker, folder 12)

Same: runbook shape; byte-identical driver; /scan + /JoyState subs; /cmd_vel pub;
4 params (2 unused); Joy_active gate semantics (zero-Twist brake, return); cone
strict <45 & !=0.0 with inf pass; /72 magic; sign branches; |u|<0.5 deadzone;
print trio cadence; exit_pro brake; no __main__ guard; "improt done" + "commom"
typos; dead time/sleep imports.

Different: class laserWarning; node "laser_Warnning_a1" (typo); NEW /beep UInt16
pub + alarm block; NO linear PID and NO snap — linear.x never set, spin-in-place
only; ang_pid (3.0, 0.0, 5.0) vs tracker (2.0, 0.0, 2.0); damping ×0.5 vs ×0.6;
deadzone edge 12 deg vs 18 deg (Kp-view); turn ceiling ±0.9375 vs ±0.75 rad/s;
Joy/empty returns leave /beep latched (tracker's returns only froze /cmd_vel).

## 5. Labeling rules

SinglePID internals, Bool message source module, setup.py entry point,
start_agent.sh contents, merger/filter internals — NOT in this folder → inferred /
illustrative. Never "fix" source bugs. Never claim the driver starts the warning
node (README L5 does). The 72, 0.5, 0.5 (L115/L118) are bare magic numbers the file
never explains — say exactly that, then the observable arithmetic. Numbers derived
from the Kp-only view are illustrative.
