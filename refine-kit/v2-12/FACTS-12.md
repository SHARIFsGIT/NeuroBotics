# FACTS-12 — verified ground truth for folder "12. lidar tracking"

Every author/verify agent MUST treat this file as binding. If any statement here
conflicts with your reading of the source, the SOURCE wins — but flag it in your
report; do not silently deviate. Nothing outside the three source files may be
presented as fact; anything inferred must carry the word "illustrative" or
"inferred" (Bangla: "illustrative" stays English).

## 0. Files (READ-ONLY, never modify)

| file | lines (splitlines) | sha256[:12] | role |
|---|---|---|---|
| README.md | 5 | 3433bd6ce68a | 3-command runbook (L2/L4 blank) |
| laser_driver.launch.py | 42 | dadf5ff3f9b1 | orchestrator launch (BYTE-IDENTICAL to folder 11's driver) |
| laser_Tracker.py | 146 | d414af8d12da | the tracking behavior node (NEW subject of this app) |

Total 193 lines. README ends WITH a trailing newline; the other two files end
WITHOUT one (so `wc -l` says 5 / 41 / 145 — splitlines is the truth: 5 / 42 / 146).

README content (all 5 lines, verbatim):
```
L1: sh start_agent.sh
L2: (blank)
L3: ros2 launch yahboom_M3Pro_laser laser_driver.launch.py
L4: (blank)
L5: ros2 run yahboom_M3Pro_laser laser_Tracker
```
(No trailing content after L5 except the final newline.)

## 1. laser_driver.launch.py — verified facts (identical to folder 11)

- L1 `import os` … L6 `from launch_ros.actions import Node` — six imports; the
  L6 `Node` import is UNUSED in this file (comment admits "just in case").
- L8 `def generate_launch_description():` — the ONLY entry point; a launch file
  has no main/spin; ROS 2 calls this function once at launch time.
- L12-16 `laser_merge_launch_file = os.path.join(get_package_share_directory('ira_laser_tools'), 'launch', 'merge_multi.launch.py')`
- L20-24 `laser_filter_launch_file = os.path.join(get_package_share_directory('yahboom_laser_filter'), 'launch', 'laser_filter_node.launch.py')`
- L28-42 `return LaunchDescription([IncludeLaunchDescription(PythonLaunchDescriptionSource(laser_merge_launch_file)), IncludeLaunchDescription(PythonLaunchDescriptionSource(laser_filter_launch_file))])`
  with blank lines L29/L35/L41 inside the list literal and comments L30-31/L36-37.
- TWO-PHASE model (mandatory framing): **constructor phase** — ROS 2 imports the
  module and calls generate_launch_description() top-to-bottom (L1→L42): six
  import bindings, one def binding, two EAGER os.path.join string builds, the
  LaunchDescription list built, returned. NOTHING runs yet — no node exists.
  **run phase** — the launch system executes the returned list in order:
  include #1 (L32-34) spawns the ira_laser_tools merge_multi chain (folder 10's
  dual-laser merger), include #2 (L38-40) spawns yahboom_laser_filter's
  laser_filter_node. Downstream effect (illustrative, consistent with folder 10):
  front + rear raw scans merge into one 360° ring on `/scan`, then the filter
  removes blind-spot readings (robot's own body/arm) — the tracker subscribes to
  that fused, filtered `/scan`.
- The tracker node itself is NOT started by this launch file — README L3 starts
  the sensor chain only; README L5 (`ros2 run … laser_Tracker`) starts the node.

## 2. laser_Tracker.py — line-by-line verified semantics

Class `laserTracker(Node)` (L17). Node name at construction: `"laser_Tracker_a1"`
(L137). Purpose: find the CLOSEST valid object in the front ±45° cone of the
fused scan and FOLLOW it — keep 0.55 m stand-off distance (ResponseDist) and
keep it centered (turn toward its angle). Dual PID: linear + angular.

### Module head (L1-15)
- L1 `#ros lib` comment. L2 `import rclpy`, L3 `from rclpy.node import Node`,
  L4 `from geometry_msgs.msg import Twist`, L5 `from sensor_msgs.msg import LaserScan`.
- L7 `#commom lib` comment (typo "commom" is IN THE SOURCE — preserve, explain).
- L8 `import math`; L9 `import numpy as np`; L10 `import time`; L11 `from time import sleep`.
  **VERIFIED QUIRK: `time` and `sleep` are NEVER used again in the file — both
  dead imports.** L13 `import os` (used only in exit_pro L133).
- L12 `from yahboom_M3Pro_laser.common import *` with comment
  `# Custom Yahboom tools (like Bool message and SinglePID)`. Star-import; the
  names this file actually consumes from it are `Bool` (L25, L53) and
  `SinglePID` (L47, L49). That module is NOT in this folder — its internals are
  unknown; everything about SinglePID behavior must be labeled inferred/illustrative.
- L14 `print ("improt done")` — typo "improt" IS IN THE SOURCE; the trailing
  comment `# (Typo in original: means "import done")` admits it. Runs at import
  time (module top level), before any node exists.
- L15 `RAD2DEG = 180 / math.pi` = 57.29577951… module-level constant.

### Constructor __init__ (L18-49)
- L18 `def __init__(self,name):` → L19 `super().__init__(name)` — node base init.
- L23 `self.sub_laser = self.create_subscription(LaserScan,"/scan",self.registerScan,1)`
  — queue depth 1. L25 `self.sub_JoyState = self.create_subscription(Bool,'/JoyState', self.JoyStateCallback,1)`
  — NOTE: `Bool` here is the yahboom common-module Bool (per L12 comment), not
  std_msgs/Bool — the package is not in this folder, so its exact layout beyond
  `.data` is unknown; do not invent fields.
- L29 `self.pub_vel = self.create_publisher(Twist,'/cmd_vel',1)`.
- Parameters (declare + get pairs, L32-39), defaults verbatim:
  - `linear` = 0.5 (comment: "Max forward speed (0.5 m/s)")
  - `angular` = 1.0 ("Max turning speed (1.0 rad/s)")
  - `LaserAngle` = 45.0 ("Width of the front cone (45 degrees left and right)")
  - `ResponseDist` = 0.55 ("sweet spot" stand-off distance in meters)
  **VERIFIED QUIRK: `self.linear` (L33) and `self.angular` (L35) are assigned
  and then NEVER read again — the declared speed limits are NOT enforced
  anywhere; no clamp exists.** `self.LaserAngle` used L70; `self.ResponseDist`
  used L96, L102.
- L42 `self.Joy_active = False` (initial state: AI in control).
- L47 `self.lin_pid = SinglePID(1.0, 0.0, 1.0)` — gains (Kp, Ki, Kd) = (1, 0, 1);
  comment says it "controls forward/backward speed to maintain the 0.55m distance".
- L49 `self.ang_pid = SinglePID(2.0, 0.0, 2.0)` — gains (2, 0, 2); "controls
  left/right turning to keep the object centered in the camera" (comment says
  camera; the actual sensor is the LiDAR — stale wording, explain it).
- PID controllers are constructed ONCE and keep internal state across scan
  callbacks (that is what the Ki/Kd terms would act on; Ki=0 here).

### JoyStateCallback (L52-54)
- L53 `if not isinstance(msg, Bool): return` — type guard.
- L54 `self.Joy_active = msg.data` — True means a human is driving; AI pauses.

### registerScan(scan_data) (L56-125) — the behavior core, fired per /scan msg
- L57 type guard `if not isinstance(scan_data, LaserScan): return`.
- L58 `ranges = np.array(scan_data.ranges)` — distance array, one per beam.
- L61-62 `minDistList = []`, `minDistIDList = []` — parallel lists: distances and
  the DEGREE angle of each accepted front beam.
- L65 `for i in range(len(ranges)):` — visits every beam, 0..N-1.
- L67 `angle = (scan_data.angle_min + scan_data.angle_increment * i) * RAD2DEG`
  — beam direction in degrees. With the fused ring from the folder-10 chain the
  echo values are angle_min = -3.14159 (= -π) and angle_increment = 0.0174533
  (= π/180), i.e. 360 beams at exactly 1°: angle_i = -180 + i degrees
  (illustrative but consistent with folder 09's recorded echo).
- L70 `if abs(angle) < self.LaserAngle and ranges[i] !=0.0 :` — front cone test
  (|angle| < 45.0, STRICT inequality, open interval) AND a validity test that
  only excludes EXACT 0.0. **Honest edge: LaserScan uses +inf for no-return
  beams; inf != 0.0 is True, so inf readings PASS this filter. If the upstream
  chain did not already replace no-returns with 0.0, an open corridor would put
  inf into minDistList.** Present as a real consequence of the code as written;
  note the code's evident assumption that upstream zeroes invalid readings.
- L71-72 append distance and angle to the two lists.
- L75-83: `if len(minDistList) != 0:` → L77 `minDist = min(minDistList)`;
  L79 `minDistID = minDistIDList[minDistList.index(minDist)]` — the ANGLE of the
  closest beam. Ties: `list.index` returns the FIRST occurrence (lowest i →
  most-negative angle among equals). Else-branch L82 prints a dashes line
  `"-----------------------"` and RETURNS — no object in front ⇒ no publish at
  all (motors keep the last command; they are not actively stopped here).
- L86-88: `if self.Joy_active :` → L87 `self.pub_vel.publish(Twist())` (all-zero
  Twist — an ACTIVE brake) and return. Published again on EVERY scan while the
  flag is held.
- L90 `velocity = Twist()`; L91-92 print minDist and minDistID (console traffic
  at scan rate).
- L96 `if abs(minDist - self.ResponseDist) < 0.1: minDist = self.ResponseDist`
  — ±0.1 m deadzone: inside the band, snap to exactly 0.55 so the linear PID
  sees zero error (stops forward/backward jitter).
- L102 `velocity.linear.x = -self.lin_pid.pid_compute(self.ResponseDist, minDist)`
  — call order is (target, current) as written. The leading minus sign plus the
  code's own comment (L100-101: "if we are too far away … we need a positive
  forward speed") imply SinglePID returns target−current style error with
  positive = too-far… **BE PRECISE: as written, if error = first−second arg then
  far ⇒ pid negative ⇒ minus makes linear.x positive (approach). If the vendor
  convention were the opposite, the robot would back away. The file alone
  cannot prove the vendor's internal sign; state the code text, quote the
  comment's intent, and mark the direction conclusion as inferred from the
  comment.** NEVER claim SinglePID source we do not have.
- L107 `ang_pid_compute = self.ang_pid.pid_compute(abs(minDistID) / 72, 0)`
  — target = |angle|/72 (a NORMALIZATION: max |angle| just under 45 ⇒ target
  just under 0.625), current = 0. The 72 is a bare magic number — the file
  never explains it; say exactly that, then give the observable effect.
- L110-114 sign branch: `if 0 < minDistID : velocity.angular.z = ang_pid_compute`
  (object left ⇒ positive z = CCW/left turn) `elif minDistID < 0:
  velocity.angular.z = -ang_pid_compute` (right ⇒ negative). If minDistID is
  EXACTLY 0.0 neither branch runs and angular.z stays 0.0.
- L117 `if abs(ang_pid_compute) < 0.5: velocity.angular.z = 0.0` — LARGE turn
  deadzone. With Kp=2 dominating: 2·(|a|/72) < 0.5 ⇒ |a| < 18° ⇒ NO turn.
  So the object must be ≥ ~18° off-center before the robot turns at all
  (illustrative arithmetic, Kp-term only; Kd transient can differ on step
  changes — label it).
- L120 `velocity.angular.z = velocity.angular.z * 0.6` — 60% turn damping.
- L122 prints angular.z. L125 `self.pub_vel.publish(velocity)`.

### exit_pro (L128-133)
- L130-132 build the shell string:
  cmd1 = `ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist ` (trailing space),
  cmd2 = the quoted YAML `"{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"`,
  cmd = cmd1 + cmd2. L133 `os.system(cmd)` — a SHELL one-shot zero-velocity
  brake from outside the node (works even if the node is dying).

### main (L135-146)
- L136 `rclpy.init()`; L137 `laser_tracker = laserTracker("laser_Tracker_a1")`;
  L138 `print ("start it")`; L139-142 try/spin/except KeyboardInterrupt: pass;
  L143-146 finally: `exit_pro()` → `destroy_node()` → `rclpy.shutdown()`.
- **VERIFIED: the file never calls main() and has no `if __name__ == '__main__'`
  block. It ends at L146 inside main's body.** `ros2 run` works because the
  package's setup.py console_scripts entry point (NOT in this folder) imports
  this module and calls a callable — the standard ROS 2 pattern; label the
  entry-point mechanism "inferred (setup.py not in this folder)".

### Import-time vs run-time (for the exec trace)
Import pass executes ONLY module top level: L1-15 (comments, imports, print at
L14, RAD2DEG at L15) and binds the class (L17) + its three defs (`__init__` L18,
`JoyStateCallback` L52, `registerScan` L56, `exit_pro` L128) and `main` L135 —
function BODIES are compiled, not run. Everything else happens when main() runs
and callbacks fire.

## 3. Canonical illustrative scenario (label "illustrative" everywhere)

Fused /scan ring: 360 beams, angle_i = -180+i°. Front cone |angle| < 45 ⇒ beams
i = 136..224 (89 beams). All waves use ONE static pillar unless stated:

- Wave A (far + off-left): pillar 0.90 m at +12°. minDist=0.90, minDistID=+12.
  Deadzone |0.90-0.55|=0.35 ≥ 0.1 ⇒ no snap. Linear (Kp-term view):
  e = 0.55-0.90 = -0.35 ⇒ pid ≈ -0.35 ⇒ linear.x = +0.35 (approach; Kd adds a
  same-sign transient on first call — illustrative). Angular: target 12/72 =
  0.1667, Kp·e = 2×0.1667 = 0.333 < 0.5 ⇒ angular.z = 0 — the 12° error is
  INSIDE the turn deadzone; robot closes distance but does not yet turn.
- Wave B (closer + further left): 0.70 m at +20°. e_lin = -0.15 ⇒ linear.x ≈
  +0.15. ang: 2×(20/72) = 0.556 ≥ 0.5 ⇒ turn active; ×0.6 ⇒ angular.z ≈
  +0.33 rad/s (left). This wave shows BOTH outputs nonzero.
- Wave C (locked on): 0.58 m at 0°. |0.58-0.55| = 0.03 < 0.1 ⇒ snap minDist :=
  0.55 ⇒ linear error 0 ⇒ linear.x = 0; minDistID = 0 ⇒ neither sign branch ⇒
  angular.z = 0. The held state: stand-off held, deadzones doing their job.
- Wave D (human takes over): /JoyState Bool.data = True ⇒ every scan publishes
  all-zero Twist and returns — active brake while the stick is held.
- Wave E (Ctrl+C): KeyboardInterrupt swallowed by `pass`; finally ⇒ exit_pro
  shell brake ⇒ destroy_node ⇒ shutdown. EXECUTION COMPLETE state.

Also usable as failure-intuition material: the inf-passthrough edge (§2 L70),
the unclamped linear.x (0.90 m error ⇒ +0.35 > declared linear 0.5 would be
exceeded at larger errors — e.g. 1.6 m ⇒ Kp-view +1.05), declared-but-unused
params, dead imports, "improt" typo, stale "camera" comment (L48), stale
"72" magic number, ±45 strict `<` (exactly-45.0° beams are EXCLUDED).

## 4. Style rules (BINDING)

- Bangla prose; technical terms stay English (Camera-র মতো hyphen-suffix রূপ:
  `Function-টি`, `Matrix-এর`). NO transliteration of technical terms.
- Source NEVER rewritten; bug/quirk is explained, not fixed. Line references in
  explanations use the REAL file line numbers (README L1-5; driver L1-42;
  tracker L1-146 as splitlines — the tracker's last line is 146).
- No emoji anywhere. No arrow characters inside SVG stage <text> (use words or
  HTML entities like `-&gt;`); arrows are allowed in HTML caption/formula/fx
  strips (nav chrome uses them) — but NOT in `cap`/`op`/`dbg` strings of the
  exec spec (folder-11 rule); use `-&gt;` entity there if needed. Hmm — note:
  folder-11's finalFx DID use `->` plain arrows in fx; the stricter historical
  rule banned arrows in dbg/op/cap. Follow: plain `->` allowed ONLY in fx
  strips; everywhere else in spec text use `-&gt;` or Bangla prose.
- Bangla numerals may appear in prose (৩টা) but counts/measurements in code
  contexts stay ASCII digits.
- Every formula in math sections: LaTeX in `\[ ... \]` / `\( ... \)` (MathJax 3).
- dbg values that are not real runtime output carry "illustrative" marking.
- JSON strings must escape per JSON; inside JS single-quoted template contexts
  use standard HTML escaping for `<`/`>` as `&lt;`/`&gt;` where needed.

## 5. Deliverable schemas

### v1 part (parts-NN.json, one object per Part)
```json
{
  "n": 1, "id": "part-01", "fname": "README.md",
  "enTitle": "…", "lang": "bash|python",
  "start": 1, "end": 5, "flags": [],
  "explain": [ {"a": 1, "b": 1, "text": "Bangla …"} ],
  "math": null | {
    "intro": "…",
    "levels":  [ {"label": "Level 2 — মৌলিক সম্পর্ক", "latex": "\\[ … \\]", "text": "…"} ],
    "numeric": [ {"latex": "\\[ … \\]", "text": "…"} ],
    "mapping": [ {"code": "source expr", "math": "\\( … \\)", "text": "…"} ],
    "failure": [ "…", "…" ]
  },
  "robot": { "correct": "…", "incorrect": "…" },
  "animType": null | "runbookFlow"
}
```
`math` only where genuine math exists (parts: beam-angle formula, min-search,
deadzone, PID linear/angular, RAD2DEG — at minimum). The renderer supports
EXACTLY intro/levels/numeric/mapping/failure — never a `blocks` key.

### v2 exec-spec steps (each step, array `steps`)
```json
{"file":"laser_Tracker.py","ln":67,"lns":[67],"kind":"struct|exec|event",
 "cap":"Bangla explanation of THIS line at THIS moment","op":"short english op",
 "dbg":[["key","value"],…],"fx":"compact strip","rob":"<svg-inner>…</svg-inner>"}
```
- kinds: `struct` = declarative/skip/compile/bind/gloss (blank lines, comments,
  def headers, class body during import pass); `exec` = state-changing module
  top-level (imports evaluated, RAD2DEG, print) or launch constructor actions;
  `event` = runtime callbacks/main-pass/spawn actions (the run phase).
- `ln`/`lns` are REAL source lines; every one of the 193 lines must appear in
  the schedule (compile pass covers each line once, in order; run/event pass
  may REVISIT lines; total coverage check is exact-tile for the compile pass).
- `rob` = inner SVG markup string (no <svg> wrapper) drawn into the 440×330
  robot panel (viewBox), or "" — reuse the shared `defs` ids egB/egW etc.
- defaultDurs: struct 420 ms, exec 1800 ms, event 1800 ms.

### rob scene conventions (from folder-11 engine, reuse the visual grammar)
Panel: rect x=16 y=22 w=196 h=228 rx=9 fill #161b22 opacity .55 stroke colored
1.4; header text "ROBOT" bold 10 @ (26,34); status right-aligned @ (214,34).
Inner stage 224..416 x 42..238. Colors: #4fc3f7 blue (node/scan), #7ee787
green (ok/scan-data), #e3b341 yellow (launch/merger), #d2a8ff purple (filter),
#ff7b72 red (/cmd_vel danger), #8f98a3 gray. Text 5.8-8 monospace.
