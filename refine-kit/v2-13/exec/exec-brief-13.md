# exec-brief-13 — binding style contract for exec-spec-13 authoring

You are authoring content for the v2 "Complete Execution — Code → Debug → Robot"
section of the folder-13 app. `/home/shariful/NeuroBotics/refine-kit/v2-13/FACTS-13.md`
is BINDING ground truth. The three source files are READ-ONLY:
- `/home/shariful/NeuroBotics/13. lidar guard/README.md` (5 lines)
- `/home/shariful/NeuroBotics/13. lidar guard/laser_driver.launch.py` (42 lines)
- `/home/shariful/NeuroBotics/13. lidar guard/laser_Warning.py` (145 lines)
Read them yourself; quote code EXACTLY (typos "improt", "commom", "Warnning" are
source; L99 ends with a TAB; L129 cmd1 has a trailing space).

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
  `->` is allowed in cap/dbg/op/fx/rob (folder-11/12 precedent); UNICODE arrow
  characters (→ ← ↑ ↓ ⇒ ⇄ and any lookalike) are BANNED everywhere in the spec.
- `op` — short English imperative for the op-strip, ASCII only, e.g.
  `run start_agent.sh script`, `bind class laserWarning`, `publish UInt16 1 to /beep`.
- `dbg` — debug rows `[key, value]` or `[key, value, flag]` with flag
  `"ill"` (illustrative value — engine dims it) or `"err"` (wrong/stale-as-written
  value — engine reddens it). 2-5 rows per step. Keys MUST come from the
  registry below (new key allowed only if genuinely needed; then note it).
  On repeated keys across consecutive steps the engine renders BEFORE → AFTER
  — use this deliberately. Values: ASCII digits for measurements; may carry
  units (`0.90 m`, `+14.0 deg`, `0.292 rad/s`). Non-source-true numbers → flag
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
pub · param · pid_ang · Joy_active · ranges · cone_beams · angle · minDist ·
minDistID · alarm · beep · e_ang · u_ang · angular.z · deadzone · damping ·
linear.x · publish · cmd_vel · twist · cmd · shell · exit

(No pid_lin/e_lin/snap keys — this node has NO linear PID and NO snap. linear.x
exists as a key precisely because it is NEVER set: rows show 0.0 with the
spin-only story. alarm = the L89 boolean outcome; beep = the /beep UInt16
value on the wire.)

## Canonical wave table (EXACT numbers — Kp-term view, Ki=0; label illustrative)

Fused ring (illustrative, consistent with folder-10 chain + folders 11/12):
360 beams, `angle_i = -180 + i` deg, angle_min = -pi, increment = pi/180.
Cone `abs(angle) < 45.0` STRICT and `ranges[i] != 0.0`: beams i = 136..224
= 89 beams; exactly-45.0-degree beams EXCLUDED; inf PASSES the != 0.0 test.

| wave | scene | minDist | minDistID | alarm L89 | beep | e_ang=abs(a)/72 | u_ang=3e | z after sign | deadzone L115 | z final ×0.5 L118 | publish |
|---|---|---|---|---|---|---|---|---|---|---|---|
| gate | JoyState False arrives first | — | — | — | — | — | — | — | — | — | — |
| A | pillar 0.90 m @ +14 deg (far, left) | 0.90 | +14.0 | 0.90 > 0.55 no | 0 | 0.194 | 0.583 | +0.583 | 0.583 ≥ 0.5 pass | +0.292 | (0.0, +0.292) spin left, quiet |
| B | 0.70 m @ +20 deg | 0.70 | +20.0 | no | 0 | 0.278 | 0.833 | +0.833 | pass | +0.417 | (0.0, +0.417) spin left faster |
| C | 0.48 m @ 0 deg (INSIDE zone) | 0.48 | 0.0 | 0.48 ≤ 0.55 YES | 1 | 0 | 0 | 0.0 (neither branch) | 0 < 0.5 → 0.0 | 0.0 | (0.0, 0.0) still + BEEPING |
| D | 0.50 m @ −20 deg (right, in zone) | 0.50 | −20.0 | YES | 1 | 0.278 | 0.833 | −0.833 (L109-110) | pass | −0.417 | (0.0, −0.417) spin right + BEEPING |
| E | nothing valid in front | — | — | not reached | LATCH 1 | — | — | — | — | — | NO publish — motors hold last cmd AND /beep stays 1 |
| F | 0.80 m @ +8 deg (clear again) | 0.80 | +8.0 | no | 0 (else L95) | 0.111 | 0.333 | +0.333 | 0.333 < 0.5 → 0.0 | 0.0 | (0.0, 0.0) quiet, buzzer OFF |
| Joy | /JoyState True (human) | — | — | skipped | LATCH (not refreshed) | — | — | — | — | — | Twist() all-zero EVERY scan, L83 return BEFORE alarm |
| Joy2 | /JoyState False again | — | — | — | — | — | — | — | — | — | guarding resumes next scan |
| halt | Ctrl+C | — | — | — | — (untouched) | — | — | — | — | — | except: pass → finally → exit_pro shell brake (zeroes /cmd_vel only; /beep untouched) → destroy_node → rclpy.shutdown |

Boundaries: deadzone edge |a| = 12 deg → u = 0.5 → `< 0.5` False → passes →
z = ±0.25. Ceiling |a| → 45⁻ → u → 1.875 → z → ±0.9375 rad/s. Alarm boundary:
0.55 exactly → `<=` TRUE → beep ON (no hysteresis — an object hovering there
can chatter the buzzer at scan rate; say once, in wave C or F context, never
dwelt on).

Kp-only caveat: real `SinglePID(3.0, 0.0, 5.0)` has a LARGE Kd; on a STEP
change the first call adds a same-sign Kd transient — every PID number above
carries `ill` and the cap may mention the transient once (wave A first call
only), never dwelt on.

Buzzer semantics (teach across waves, this is THE guard signature): /beep is a
LEVEL signal refreshed per scan — L90-92 publish 1 inside the zone, L95
publishes default-0 every scan while the object is outside. The two early
returns (L73 empty cone, L81-83 Joy) skip the refresh, so /beep LATCHES its
last value. exit_pro brakes /cmd_vel but never writes /beep.

## rob panel — exact grammar (calibrate against `exec/ref-*.json` "rob" fields)

Canvas 440×330. TWO cards + 3 Bangla bottom lines. Copy this chrome VERBATIM
into every non-empty rob (then edit the marked parts):

- TERMINAL card: `<rect x="16" y="22" width="196" height="228" rx="9" fill="#161b22" fill-opacity=".55" stroke="#4fc3f7" stroke-width="1.4"/><text x="26" y="34" text-anchor="start" font-family="monospace" font-size="10" fill="#e6edf3" font-weight="bold">TERMINAL</text><text x="202" y="34" text-anchor="end" font-family="monospace" font-size="5.8" fill="#6e7681">STATUS-WORD</text><text x="26" y="45" font-family="monospace" font-size="5.8" fill="#6e7681">jetson@yahboom: ~ (illustrative)</text>`
  then console lines at y = 56, 67, 78, … (11 px pitch), monospace 5.8-6.5,
  colors: command echo `#e6edf3`, normal output `#8b949e`, live/highlight
  `#7ee787`, warning `#ffb454`, error `#ff7b72`. Prefix prompt
  `jetson@yahboom:~$ ` only on a NEW command line. Max ~15 lines; older lines
  may be elided with `…` row. The guard's console cadence per scan is THREE
  prints: `minDist: 0.9` (L85), `minDistID: 14.0` (L99), `orin_angular.z: …`
  (L112), `angular.z: …` (L120) — four rows actually; use them deliberately.
- SYSTEM card: `<rect x="216" y="22" width="208" height="228" rx="9" fill="#161b22" fill-opacity=".55" stroke="#30363d" stroke-width="1.4"/><text x="226" y="34" text-anchor="start" font-family="monospace" font-size="10" fill="#e6edf3" font-weight="bold">SYSTEM</text><text x="414" y="34" text-anchor="end" font-family="monospace" font-size="5.8" fill="#6e7681">STATE-WORD</text><rect x="224" y="42" width="192" height="196" rx="4" fill="#0d1117" fill-opacity=".8" stroke="#21262d" stroke-width="1"/>`
  then draw the scene INSIDE x 224..416, y 42..238 (keep ~4 px padding):
  robot top-view = rounded rect ~28×34 `fill="url(#egB)" stroke="#4fc3f7"`;
  heading wedge `fill="#4fc3f7"` opacity .8 (NO Unicode arrows in SVG text —
  draw a small triangle `path` with marker-less tip, or write `fwd`); lidar
  ring arc `stroke="#7ee787"` opacity .35; beams `stroke="#7ee783"` thin lines
  or `#7ee787`; pillar = small square/rect `fill="#ffb454"`; danger zone band
  around the robot (radius 0.55 m to scale) `stroke="#ff7b72"`
  `stroke-dasharray="3 3"` opacity .5 — the guard's signature visual; cone
  edges `stroke="#4fc3f7" stroke-dasharray="3 3"` opacity .5; velocity vector =
  bold CURVED arc + triangle tip `#d2a8ff` (angular ONLY — the robot never
  drives forward; never draw a straight linear arrow); BUZZER glyph = small
  circle at robot rear/top with 2-3 concentric arcs `#ffb454` when beeping
  (visible pulse), dim `#484f58` when off; danger flash `#ff7b72`.
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

## Sequence context (all units) — the 184-step spine

U1 README-open (steps 1-3) + README-mid (steps 174-175 region) · U2 driver ctor
(steps 4-19) + run (20-25) · U3 import-pass a: warning L1-48 (26-44) · U4
import-pass b: L49-100 (45-63) · U5 import-pass c: L101-145 (64-81) · U6
main-pass (82-97) · U7 gate+wave A (98-121) · U8 waves B+C (122-142) · U9
waves D+E+F (143-163) · U10 Joy+release+halt (164-184).

Incoming/outgoing panel + dbg state each unit MUST match:
- U1 ends: TERMINAL shows `sh start_agent.sh` ran (vendor bringup,
  illustrative); cursor ready. SYSTEM: robot off, `ros2 launch` next.
- U2 ends: both includes FIRED (run phase); SYSTEM shows merger+filter
  chain up (folder-10 story, illustrative), `/scan` fused ring flowing;
  TERMINAL: launch line echoed, no node of its own. README-mid then runs
  `ros2 run … laser_Warning` (U1's second half).
- U3 ends: import pass through L48 — TERMINAL got `improt done` (L15,
  typo as-is); SYSTEM: class bound, no instance yet; dbg pass=import.
- U4 ends: bodies through L100 defined — Joy callback, registerScan cone
  + lists + alarm block compiled-not-run; dbg note beep/alarm bodies dormant.
- U5 ends: file fully defined incl. exit_pro + main; still nothing ran
  beyond L1-16.
- U6 ends: constructor LIVE — node `laser_Warnning_a1` (typo as-is),
  sub /scan + /JoyState, pub /cmd_vel + /beep, four params (linear/angular
  read then dead), Joy_active=False, ang_pid(3.0, 0.0, 5.0) built; `start it`
  printed; spin parked. dbg has node/sub/pub/param/pid rows.
- U7 ends: wave A published (0.0, +0.292) — dbg linear.x=0.0,
  angular.z=+0.292, beep=0.
- U8 ends: wave C stand-off — dbg (0.0, 0.0), beep=1, robot still +
  buzzer ON.
- U9 ends: wave F quiet — dbg (0.0, 0.0), beep=0 (else-branch), E's latch
  already shown between D and F.
- U10 ends: shutdown complete — dbg exit=clean; SYSTEM `complete`;
  TERMINAL brake line; final rob: robot parked, zero cmd_vel, buzzer note
  (last /beep state left as-is by exit_pro).

## Global prohibitions

No emoji. No UNICODE arrow characters anywhere (ASCII `->` is fine). No Bangla
numerals in dbg values or SVG text (prose may use ৩টা style sparingly). No
invented vendor internals — SinglePID/Bool/yahboom common module are NOT in
this folder: any claim about their internals must carry illustrative/inferred.
Never "fix" source bugs. Never claim the warning node is started by the launch
file (README L5 does that). The 72 in L103 and 0.5/0.5 in L115/L118 are bare
magic numbers in the source — the file never explains them; say exactly that,
then the observable arithmetic. linear/angular params (0.5/1.0) are declared
L35/L37, read L36/L38, and NEVER used again — no clamp exists (real ceiling:
3×(45/72)×0.5 = 0.9375 rad/s angular; linear.x is never set at all — the guard
is spin-only). Never draw or claim a forward-driving arrow. Never say the
buzzer is an edge event — it is a level signal, refreshed per scan, latched by
the two early returns.
