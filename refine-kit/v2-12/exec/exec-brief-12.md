# exec-brief-12 — binding style contract for exec-spec-12 authoring

You are authoring content for the v2 "Complete Execution — Code → Debug → Robot"
section of the folder-12 app. `/home/shariful/NeuroBotics/refine-kit/v2-12/FACTS-12.md`
is BINDING ground truth. The three source files are READ-ONLY:
- `/home/shariful/NeuroBotics/12. lidar tracking/README.md` (5 lines)
- `/home/shariful/NeuroBotics/12. lidar tracking/laser_driver.launch.py` (42 lines)
- `/home/shariful/NeuroBotics/12. lidar tracking/laser_Tracker.py` (146 lines)
Read them yourself; quote code EXACTLY (typos "improt", "commom" are source).

## Your work unit

You get `exec/unit-<U>.json`: an ordered array of step skeletons
`{"file","ln","lns","kind"}`. These are FROZEN — file/ln/lns/kind must not
change, order must not change, no step added or dropped. You author FIVE content
fields per step and return them keyed by the step's index `i` (0-based, position
in the array). Output schema:

```json
{"steps": [{"i":0,"cap":"…","op":"…","dbg":[["k","v"],["k","v","ill"]],"fx":"…","rob":"…"}, …],
 "notes": "optional concerns for the reviewer"}
```

- `cap` — 1-3 sentence Bangla explanation of THESE lines AT THIS MOMENT of the
  trace (what happens now, not a general lecture). Technical terms English,
  Bangla hyphen-suffix grammar (`PID-টি`, `callback-এ`, `parameter-গুলো`).
  `<code>…</code>` for code fragments; escape `<`/`>` as `&lt;`/`&gt;` inside
  code tags when quoting source comparisons. Line references always REAL source
  lines. No emoji; no transliteration of technical terms. Arrow policy: ASCII
  `->` is allowed in cap/dbg/op/fx/rob (folder-11 precedent); UNICODE arrow
  characters (→ ← ↑ ↓ ⇒ ⇄ and any lookalike) are BANNED everywhere in the spec.
- `op` — short English imperative for the op-strip, ASCII only, e.g.
  `run start_agent.sh script`, `bind class laserTracker`, `publish Twist to /cmd_vel`.
- `dbg` — debug rows `[key, value]` or `[key, value, flag]` with flag
  `"ill"` (illustrative value — engine dims it) or `"err"` (wrong/stale-as-written
  value — engine reddens it). 2-5 rows per step. Keys MUST come from the
  registry below (new key allowed only if genuinely needed; then note it).
  On repeated keys across consecutive steps the engine renders BEFORE → AFTER
  — use this deliberately. Values: ASCII digits for measurements; may carry
  units (`0.90 m`, `+12.0 deg`, `0.35 m/s`). Non-source-true numbers → flag
  `ill`.
- `fx` — compact fixed-strip line, ASCII + `·` separators, plain `->` ALLOWED
  here (only here). Pattern: `<op echo>   · <subject>, illustrative` when any
  part is illustrative. e.g. `minDist = 0.90   · wave A, Kp-only, illustrative`.
- `rob` — inner SVG fragment (NO `<svg>` wrapper) for the 440×330 robot panel;
  `""` (empty string) to keep the previous panel. FULL redraw — repeat the
  chrome, do not reference earlier fragments. Rules below.

## kind semantics (voice + pacing)

- `struct` — define/bind/compile/gloss moment: blank lines, comments, def
  headers, class body during import pass. Voice: "এখনো শুধু define হচ্ছে /
  চলবে না / নীরব সাক্ষী". dbg optional (may be `[]`).
- `exec` — module-level or constructor statement that runs NOW with a side
  effect (import binding, print, RAD2DEG, eager path build, declare_parameter
  during main pass, PID construction, publish). dbg should show the state change.
- `event` — external world drives it (message arrival, callback dispatch,
  launch run-phase action, Ctrl+C, main() entry). Voice: "message এলো /
  framework ডাকল / ঘটনা ঘটল"। dbg shows the incoming payload + new state.

## dbg key registry (use consistently; BEFORE → AFTER across steps)

phase · command · file · pass · import · module · class · def · node · sub ·
pub · param · pid_lin · pid_ang · Joy_active · ranges · cone_beams · angle ·
minDist · minDistID · snap · e_lin · linear.x · ang_target · u_ang · angular.z
· deadzone · damping · publish · cmd_vel · twist · cmd · shell · exit

## Canonical wave table (EXACT numbers — Kp-term view, Ki=0; label illustrative)

Fused ring (illustrative, consistent with folder-10 chain + folder-09 echo):
360 beams, `angle_i = -180 + i` deg, angle_min = -pi, increment = pi/180.
Cone `abs(angle) < 45.0` STRICT and `ranges[i] != 0.0`: beams i = 136..224
= 89 beams; exactly-45.0-degree beams EXCLUDED; inf PASSES the != 0.0 test.

| wave | scene | minDist | minDistID | snap L96 | e_lin | linear.x | ang target | u_ang | z after sign | z after deadzone L117 | z final ×0.6 L120 | publish |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gate | JoyState False arrives first | — | — | — | — | — | — | — | — | — | — | — |
| A | pillar 0.90 m @ +12 deg (far, left) | 0.90 | +12.0 | 0.35 ≥ 0.1 no | −0.35 | +0.35 | 12/72 = 0.167 | 2×0.167 = 0.333 | +0.333 | 0.333 < 0.5 → 0.0 | 0.0 | (0.35, 0.0) straight approach |
| B | 0.70 m @ +20 deg | 0.70 | +20.0 | 0.15 ≥ 0.1 no | −0.15 | +0.15 | 0.278 | 0.556 | +0.556 | pass | +0.333 | (0.15, +0.333) curve left |
| C | 0.58 m @ 0 deg | 0.58 → 0.55 | 0.0 | 0.03 < 0.1 YES minDist := 0.55 | 0 | 0.0 | 0 | 0 | 0.0 (neither branch) | — | 0.0 | (0.0, 0.0) stand-off lock |
| D | 0.70 m @ −20 deg (right) | 0.70 | −20.0 | 0.15 no | −0.15 | +0.15 | 0.278 | 0.556 | −0.556 (L113-114) | pass | −0.333 | (0.15, −0.333) curve right |
| E | nothing valid in front | — | — | — | — | — | — | — | — | — | — | NO publish — motors hold last command |
| Joy | /JoyState True (human) | — | — | — | — | — | — | — | — | — | — | Twist() all-zero EVERY scan, L88 return before math |
| Joy2 | /JoyState False again | — | — | — | — | — | — | — | — | — | — | tracking resumes next scan |
| halt | Ctrl+C | — | — | — | — | — | — | — | — | — | — | except: pass → finally → exit_pro shell brake → destroy_node → rclpy.shutdown |

Kp-only caveat: real `SinglePID(Kp,Ki,Kd)` has Kd=1/2; on a STEP change the
first call adds a same-sign Kd transient — every PID number above carries
`ill` and the cap may mention the transient once (wave A first call only),
never dwelt on.

## rob panel — exact grammar (calibrate against `exec/ref-*.json` "rob" fields)

Canvas 440×330. TWO cards + 3 Bangla bottom lines. Copy this chrome VERBATIM
into every non-empty rob (then edit the marked parts):

- TERMINAL card: `<rect x="16" y="22" width="196" height="228" rx="9" fill="#161b22" fill-opacity=".55" stroke="#4fc3f7" stroke-width="1.4"/><text x="26" y="34" text-anchor="start" font-family="monospace" font-size="10" fill="#e6edf3" font-weight="bold">TERMINAL</text><text x="202" y="34" text-anchor="end" font-family="monospace" font-size="5.8" fill="#6e7681">STATUS-WORD</text><text x="26" y="45" font-family="monospace" font-size="5.8" fill="#6e7681">jetson@yahboom: ~ (illustrative)</text>`
  then console lines at y = 56, 67, 78, … (11 px pitch), monospace 5.8-6.5,
  colors: command echo `#e6edf3`, normal output `#8b949e`, live/highlight
  `#7ee787`, warning `#ffb454`, error `#ff7b72`. Prefix prompt
  `jetson@yahboom:~$ ` only on a NEW command line. Max ~15 lines; older lines
  may be elided with `…` row.
- SYSTEM card: `<rect x="216" y="22" width="208" height="228" rx="9" fill="#161b22" fill-opacity=".55" stroke="#30363d" stroke-width="1.4"/><text x="226" y="34" text-anchor="start" font-family="monospace" font-size="10" fill="#e6edf3" font-weight="bold">SYSTEM</text><text x="414" y="34" text-anchor="end" font-family="monospace" font-size="5.8" fill="#6e7681">STATE-WORD</text><rect x="224" y="42" width="192" height="196" rx="4" fill="#0d1117" fill-opacity=".8" stroke="#21262d" stroke-width="1"/>`
  then draw the scene INSIDE x 224..416, y 42..238 (keep ~4 px padding):
  robot top-view = rounded rect ~28×34 `fill="url(#egB)" stroke="#4fc3f7"`;
  heading wedge `fill="#4fc3f7"` opacity .8 (NO Unicode arrows in SVG text —
  draw a small triangle `path` with marker-less tip, or write `fwd`); lidar
  ring arc `stroke="#7ee787"` opacity .35; beams `stroke="#7ee783"` thin lines
  or `#7ee787`; pillar = small square/rect `fill="#ffb454"`; deadzone band /
  cone edges `stroke="#4fc3f7" stroke-dasharray="3 3"` opacity .5; velocity
  vector = bold line + triangle tip `#ff7b72` (linear) / `#d2a8ff` (angular,
  curved arrow drawn as path arc); danger flash `#ff7b72`.
  Small labels inside the stage: monospace 5.8, `#8b949e`; values `#e6edf3`.
- Bottom 3 Bangla lines (always present, always exactly three):
  `<text x="16" y="262" font-family="Hind Siliguri, sans-serif" font-size="7.2" fill="#e6edf3">…</text>`
  `<text x="16" y="273" font-family="Hind Siliguri, sans-serif" font-size="7.2" fill="#8b949e">…</text>`
  `<text x="16" y="284" font-family="Hind Siliguri, sans-serif" font-size="7.2" fill="#8b949e">…</text>`
  Line 1 = current action in plain words; lines 2-3 = consequence/context.
  NO arrows, no emoji, no Latin-only jargon dumps — readable Bangla.

Shared defs (already in the engine, usable by id): gradients `egB`, `egW`,
marker `ea` (small arrowhead — usable on PATHS, never as text).
Palette: #4fc3f7 blue · #7ee787 green · #ffb454 amber · #d2a8ff purple ·
#ff7b72 red · #e6edf3 fg · #8b949e mid · #6e7681 dim · #484f58 faint ·
#161b22 card · #0d1117 stage · #21262d/#30363d borders.
Rules: every tag closed, every attribute quoted, no `<`/`>` inside text nodes
(use `&lt;`/`&gt;`), coordinates within 440×330, no `<script>`, no external
refs, no ids other than egB/egW/ea (ids must stay unique — do not re-declare
them inside rob). Keep each rob ≤ ~2.5 KB; short and legible beats dense.

## Sequence context (all units) — the 180-step spine

U1 README-open (steps 1-3) + README-mid (steps 174-175) · U2 driver ctor
(4-19) + run (20-25) · U3 import-pass a: tracker L1-57 (26-46) · U4
import-pass b: L58-102 (47-67) · U5 import-pass c: L103-146 (68-88) · U6
main-pass (89-104) · U7 gate+wave A (105-126) · U8 waves B+C (127-148) ·
U9 waves D+E+Joy (149-168) · U10 Ctrl+C+finally (169-180).

Incoming/outgoing panel + dbg state each unit MUST match:
- U1 ends: TERMINAL shows `sh start_agent.sh` ran (vendor bringup,
  illustrative); cursor ready. SYSTEM: robot off, `ros2 launch` next.
- U2 ends: both includes FIRED (run phase); SYSTEM shows merger+filter
  chain up (folder-10 story, illustrative), `/scan` fused ring flowing;
  TERMINAL: launch line echoed, no node of its own. README-mid then runs
  `ros2 run … laser_Tracker` (U1's second half).
- U3 ends: import pass through L57 — TERMINAL got `improt done` (L14,
  typo as-is); SYSTEM: class bound, no instance yet; dbg pass=import.
- U4 ends: bodies through L102 defined; dbg note Joy/Twist/snap/linear-PID
  bodies compiled-not-run.
- U5 ends: file fully defined incl. exit_pro + main; still nothing ran
  beyond L1-15.
- U6 ends: constructor LIVE — node `laser_Tracker_a1`, sub /scan + /JoyState,
  pub /cmd_vel, four params, Joy_active=False, both PIDs built; `start it`
  printed; spin parked. dbg has node/sub/pub/param/pid rows.
- U7 ends: wave A published (0.35, 0.0) — dbg linear.x=+0.35, angular.z=0.0.
- U8 ends: wave C stand-off lock — dbg (0.0, 0.0), minDist 0.55 after snap.
- U9 ends: Joy released (Joy_active False again) — dbg Joy_active=false,
  next scan would track again.
- U10 ends: shutdown complete — dbg exit=clean; SYSTEM `complete`;
  TERMINAL brake line; final rob: robot parked, zero cmd_vel.

## Global prohibitions

No emoji. No UNICODE arrow characters anywhere (ASCII `->` is fine). No Bangla
numerals in dbg values or SVG text (prose may use ৩টা style sparingly). No
invented vendor internals —
SinglePID/Bool/yahboom common module are NOT in this folder: any claim about
their internals must carry illustrative/inferred. Never "fix" source bugs.
Never claim the tracker node is started by the launch file (README L5 does
that). The 72 in L107 and 0.5/0.6 in L117/L120 are bare magic numbers in the
source — the file never explains them; say exactly that, then the observable
arithmetic. linear/angular params (0.5/1.0) are declared L32-35, read L33/L35,
and NEVER used again — no clamp exists (real ceiling: 2×(45/72)×0.6 = 0.75
rad/s for angular; linear unbounded in code).
