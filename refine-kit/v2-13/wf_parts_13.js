export const meta = {
  name: 'nb13-parts',
  description: 'Author + adversarially verify the 15 v1 PARTS JSON files for folder 13 lidar guard',
  phases: [
    { title: 'Author', detail: 'one author agent per Part writes parts/part-NN.json' },
    { title: 'Verify', detail: 'adversarial verifier re-reads source + facts and checks the file' },
    { title: 'Fix', detail: 'one repair round for failed parts using the issue list' },
  ],
}

const K = '/home/shariful/NeuroBotics/refine-kit/v2-13/'
const SRC = '/home/shariful/NeuroBotics/13. lidar guard/'

const SUMMARY = {
  type: 'object',
  properties: {
    n: { type: 'integer' },
    file: { type: 'string' },
    explainItems: { type: 'integer' },
    hasMath: { type: 'boolean' },
    mathKeys: { type: 'array', items: { type: 'string' } },
    quirksCovered: { type: 'array', items: { type: 'string' } },
    notes: { type: 'string' },
  },
  required: ['n', 'file', 'explainItems', 'hasMath', 'quirksCovered'],
}

const VERDICT = {
  type: 'object',
  properties: {
    pass: { type: 'boolean' },
    issues: { type: 'array', items: { type: 'string' } },
    checkedLines: { type: 'array', items: { type: 'integer' } },
  },
  required: ['pass', 'issues'],
}

const PARTS = [
  { n: 1,  fname: 'README.md',             enTitle: 'Runbook — Three Commands',               start: 1,   end: 5,   anim: 'runbookFlow',  math: 'none',
    brief: 'Three-command runbook. L1 sh start_agent.sh (vendor bringup, illustrative), L3 ros2 launch laser_driver.launch.py (sensor chain), L5 ros2 run laser_Warning (the guard node). L2/L4 blank separators. IDENTICAL to folders 11/12 except L5 names laser_Warning instead of laser_Tracker / laser_Avoidance — say that explicitly. Downstream semantics: THIS node is a sentry — it watches the nearest front object, BEEPS when it is inside 0.55 m, and spins in place to face it; it never drives forward.' },
  { n: 2,  fname: 'laser_driver.launch.py', enTitle: 'Driver Launch — Imports',               start: 1,   end: 7,   anim: null,           math: 'none',
    brief: 'Six imports; the launch_ros Node import is unused in this file (comment admits just-in-case). Byte-identical driver to folders 11 and 12 — you may say that.' },
  { n: 3,  fname: 'laser_driver.launch.py', enTitle: 'Two Paths — Merger & Filter',            start: 8,   end: 24,  anim: 'includeChain', math: 'none',
    brief: 'generate_launch_description() def; two EAGER os.path.join(get_package_share_directory(...)) path builds: ira_laser_tools merge_multi.launch.py and yahboom_laser_filter laser_filter_node.launch.py. Constructor phase framing: strings are built, nothing runs yet.' },
  { n: 4,  fname: 'laser_driver.launch.py', enTitle: 'Return — Two Includes, Zero Nodes',      start: 26,  end: 42,  anim: null,           math: 'none',
    brief: 'LaunchDescription list with two IncludeLaunchDescription entries; blanks inside the list literal; run-phase order: merger then filter; the warning node is NOT started by this file — README L5 does that.' },
  { n: 5,  fname: 'laser_Warning.py',      enTitle: 'Warning Node — Module Head',              start: 1,   end: 16,  anim: null,           math: 'light',
    brief: 'ros lib + commom lib (typo IN SOURCE) comment blocks; rclpy/Twist/LaserScan/UInt16 imports — L6 comment explains UInt16 is the buzzer ON/OFF message; VERIFIED QUIRK: import time and from time import sleep are both dead (never used); star-import yahboom_M3Pro_laser.common gives Bool and SinglePID, module NOT in this folder — internals unknown, label inferred; print ("improt done") typo at import time L15; RAD2DEG = 180/math.pi L16. Math: Level 1-2 only — radian-to-degree unit conversion (pi rad = 180 deg), numeric example 0.0174533 rad -> 1.0 deg.' },
  { n: 6,  fname: 'laser_Warning.py',      enTitle: 'Constructor — Subscriptions & Publishers', start: 17, end: 32,  anim: 'subPubGraph',  math: 'none',
    brief: 'class laserWarning(Node); __init__(self,name) takes the name as an explicit argument; super().__init__(name); sub_laser /scan -> registerScan depth 1; sub_JoyState /JoyState -> JoyStateCallback depth 1, Bool is the yahboom common Bool not std_msgs; pub_vel /cmd_vel Twist depth 1; pub_Buzzer /beep UInt16 depth 1 — THE NEW CHANNEL vs the tracker: a guard needs a voice. Two pubs, two subs, same topology as folders 11/12 plus /beep.' },
  { n: 7,  fname: 'laser_Warning.py',      enTitle: 'Four Parameters — Declare & Get',         start: 33,  end: 43,  anim: null,           math: 'none',
    brief: 'Four declare_parameter + get_parameter pairs: linear 0.5, angular 1.0, LaserAngle 45.0, ResponseDist 0.55. VERIFIED QUIRK: self.linear (L36) and self.angular (L38) are assigned then NEVER read again — the declared speed limits are not enforced, no clamp exists anywhere; L35 comment itself admits linear is "not actually used in this script". get_parameter(...).get_parameter_value().double_value chain explained. LaserAngle and ResponseDist ARE used downstream.' },
  { n: 8,  fname: 'laser_Warning.py',      enTitle: 'State & the Aggressive PID',              start: 44,  end: 48,  anim: null,           math: 'full',
    brief: 'Joy_active = False; ang_pid = SinglePID(3.0, 0.0, 5.0) — the ONLY PID (no linear PID exists in this file). Comment L46 says "controls the steering wheel" — no steering wheel exists on a differential drive; stale wording, quote it, do not endorse. Comment L47 references the tracker (folder 12) — REAL cross-folder reference. Math = the GENERIC PID law: u = Kp*e + Ki*integral(e) + Kd*de/dt, what Ki=0 removes, what the LARGE Kd=5 reacts to (step changes), why a guard wants a harder P than a tracker (3 vs 2); vendor internals unknown, structure inferred.' },
  { n: 9,  fname: 'laser_Warning.py',      enTitle: 'JoyStateCallback — Human Override',       start: 49,  end: 53,  anim: null,           math: 'none',
    brief: 'isinstance guard against the custom Bool; self.Joy_active = msg.data; True means human drives, AI pauses. When/why this fires. Forward-reference: the gate is checked deep inside registerScan (L81), AFTER the cone scan — and the Joy return skips the alarm block too, so /beep is not refreshed while a human drives.' },
  { n: 10, fname: 'laser_Warning.py',      enTitle: 'registerScan — Beam Loop & Front Cone',   start: 54,  end: 70,  anim: 'beamSweep',    math: 'full',
    brief: 'THE angle math part. Type guard; ranges = np.array(scan_data.ranges); two parallel lists minDistList/minDistIDList (distance + DEGREE angle) — note this file collects into lists then takes min later (the tracker folded it differently); L58 comment says "front 90-degree cone" — with ±45 strict the total is just under 90, wording vs inequality; for i in range(len(ranges)) visits every beam; angle = (angle_min + angle_increment*i) * RAD2DEG; with the fused ring from folder 10 (angle_min = -3.14159, increment = 0.0174533) angle_i = -180 + i degrees (illustrative); front cone abs(angle) < 45.0 STRICT open interval -> i in (135,225) -> 89 beams; ranges[i] != 0.0 passes inf (no-return) readings — honest inf edge case. Math Levels 1-5 + numeric (i=194 -> +14 deg) + mapping + failure (wrong increment shifts every angle, cone misaligned).' },
  { n: 11, fname: 'laser_Warning.py',      enTitle: 'Closest Beam, Empty Guard & Joy Gate',    start: 71,  end: 85,  anim: null,           math: 'light',
    brief: 'Empty-list guard L73 (bare return — NO publish and NO buzzer write: motors hold the last /cmd_vel AND /beep latches its last value — the buzzer-stays-on trap); minDist = min(minDistList); minDistID = minDistIDList[minDistList.index(minDist)] — the angle OF the closest beam, argmin semantics via index(), ties resolve to FIRST occurrence (lowest i, most-negative angle in the cone); Joy_active branch L81-83 publishes an all-zero Twist() on EVERY scan while held (active brake) then returns — BEFORE the alarm block, so /beep is not refreshed under Joy either; L85 print minDist at scan rate.' },
  { n: 12, fname: 'laser_Warning.py',      enTitle: 'Alarm Logic — Danger Zone & Buzzer',      start: 86,  end: 95,  anim: 'alarmBuzzer',  math: 'full',
    brief: 'THE guard-specific part. L89 condition: minDist <= ResponseDist AND minDist != 0.0 — the second clause is belt-and-suspenders (the cone filter already excluded exact 0.0); inf <= 0.55 is False; NaN fails both comparisons. L90-92 b = UInt16(); b.data = 1; pub_Buzzer.publish(b) -> BEEP ON; else L95 pub_Buzzer.publish(UInt16()) — default-constructed UInt16 carries value 0 -> BEEP OFF, published EVERY scan while an object is visible outside the zone. Buzzer is a LEVEL signal refreshed per scan, not an edge event — and the two early returns (empty cone, Joy) skip the refresh, latching the last state. Math: threshold comparison as a half-open band [0, 0.55]; hysteresis ABSENT — an object hovering at exactly 0.55 m can toggle beep on/off at scan rate (chatter); numeric: 0.48 in-zone, 0.55 exactly (<= is TRUE -> beep), 0.70 out-zone; failure: ResponseDist too large => constant beeping, too small => guard silent until contact.' },
  { n: 13, fname: 'laser_Warning.py',      enTitle: 'Tracking — PID Compute & Sign Branches',  start: 96,  end: 110, anim: 'pidDial',      math: 'full',
    brief: 'THE math heart. velocity = Twist(); print minDistID L99 (source line ends with a TAB character — preserve verbatim); ang_pid_compute = self.ang_pid.pid_compute(abs(minDistID) / 72, 0) — 72 is a bare magic number the file never explains; abs() makes the error sign-free and the target is 0; NOTE: no snap logic here (the tracker L96 snapped minDist := 0.55 — the guard has none). Kp-view: u = 3*(|a|/72) = |a|/24. Sign branch: 0 < minDistID -> z = +compute (left/CCW), minDistID < 0 -> z = -compute (right/CW), exactly 0.0 -> neither, z stays 0. Math Levels 1-6 full progressive derivation + numeric Waves B and D (20 deg -> e 0.278 -> u 0.833 -> +/-z) + mapping + failure (sign flip spins away from the object, wrong 72 changes responsiveness, Kd=5 transient on step changes labeled illustrative).' },
  { n: 14, fname: 'laser_Warning.py',      enTitle: 'Deadzone, Damping & Spin-Only Publish',   start: 111, end: 124, anim: 'cmdVelVectors', math: 'full',
    brief: 'print orin_angular.z; deadzone abs(ang_pid_compute) < 0.5 -> z = 0 — with the Kp=3 term 3*(|a|/72) < 0.5 -> |a| < 12 deg means NO turn (illustrative Kp-only view; Kd transient can differ on step changes; boundary |a| exactly 12 -> u exactly 0.5 -> `< 0.5` False -> passes -> z 0.25); damping angular.z *= 0.5 — comment says 50% and the code MATCHES (tracker used 0.6 with the same comment style); effective ceiling 3*(45/72)*0.5 = 0.9375 rad/s; print angular.z; pub_vel.publish(velocity). L123 comment: linear.x is never set — Twist default 0.0 — the robot ONLY spins in place, it never approaches. Numeric Wave A: 14 deg -> 0.583 -> passes -> x0.5 -> +0.292 rad/s. Wave F: 8 deg -> 0.333 -> deadzone -> 0.' },
  { n: 15, fname: 'laser_Warning.py',      enTitle: 'exit_pro & main — Brake and Shutdown',    start: 125, end: 145, anim: 'safetyHalt',   math: 'none',
    brief: 'exit_pro builds cmd = ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist (trailing space) + quoted zero-YAML string, os.system shell one-shot brake from outside the node — NOTE the brake zeroes /cmd_vel but does NOT touch /beep (a beeping guard killed with Ctrl+C keeps its last buzzer state until something else writes it — observable consequence worth teaching). main(): rclpy.init, laserWarning("laser_Warnning_a1") — typo IN SOURCE (double n); print ("start it") with a space; try/spin/except KeyboardInterrupt pass, finally exit_pro -> destroy_node -> rclpy.shutdown. VERIFIED: the file never calls main() and has no __main__ guard — ros2 run works via the package setup.py console_scripts entry point (NOT in this folder; label inferred).' },
]

function authorPrompt(p) {
  const mathLine = p.math === 'none'
    ? 'math MUST be null (no genuine mathematics in this part).'
    : (p.math === 'light'
      ? 'math REQUIRED but compact: intro + 1-2 levels + at least one numeric + mapping or failure (use both if they earn their place).'
      : 'math REQUIRED and FULL: intro + Levels (as many as the derivation honestly supports, up to 6) + numeric examples computed from FACTS-13 section 3 values (label illustrative) + code-to-math mapping + failure list.')
  let refs = ''
  if (p.n <= 4) refs += '\n- ADAPTATION REFERENCE: ' + K + 'parts-12-refs-1-4.json — folder 12 shipped parts 1-4 for this SAME README shape and the byte-identical driver. Reuse their verified structure and cross-folder context where still true, but UPDATE every downstream reference: folder 12 said the L5 node laser_Tracker FOLLOWS the nearest front object at 0.55 m; folder 13 runs laser_Warning which BEEPS inside 0.55 m and spins in place to face the object (never drives forward). Update folder self-references to say folder 12 (past app) vs this app folder 13.'
  if (p.n === 6 || p.n === 15) refs += '\n- STYLE REFERENCE: ' + K + 'parts-12-refs-6-15.json — shipped folder-12 parts 6 and 15 for tone/depth calibration (their line refs and animType differ; do not copy line numbers).'
  return 'You are authoring ONE Part of a Bangla line-by-line code-analysis app for the ROS 2 robot folder "13. lidar guard".\n' +
    'Work in ' + K + ' . Output file: ' + K + 'parts/part-' + String(p.n).padStart(2, '0') + '.json\n\n' +
    'BINDING INPUTS — read all of these first (they are short):\n' +
    '1. ' + K + 'FACTS-13.md  — verified ground truth. Every quirk stated there for your line range MUST appear in your explanations. Never contradict it; never invent beyond it.\n' +
    '2. ' + K + 'schema-part.md — exact JSON schema, renderer-supported math keys (NEVER a "blocks" key), house style, terminology rules.\n' +
    '3. The source file ' + SRC + p.fname + ' — READ-ONLY. Quote fragments verbatim. Your part covers REAL source lines ' + p.start + ' to ' + p.end + ' (1-based, splitlines numbering; laser_Warning.py has 145 lines).' + refs + '\n\n' +
    'PART SPEC:\n' +
    '- n: ' + p.n + ', id: part-' + String(p.n).padStart(2, '0') + ', fname: ' + p.fname + ', lang: ' + (p.fname === 'README.md' ? 'bash' : 'python') + '\n' +
    '- enTitle: "' + p.enTitle + '" (keep exactly)\n' +
    '- start: ' + p.start + ', end: ' + p.end + ', flags: []\n' +
    '- animType: ' + (p.anim === null ? 'null' : '"' + p.anim + '"') + '\n' +
    '- math: ' + mathLine + '\n' +
    '- content brief (binding, weave into explain items + robot + math): ' + p.brief + '\n\n' +
    'REQUIREMENTS:\n' +
    '- explain items: {a,b,text} with a..b real contiguous lines inside [' + p.start + ',' + p.end + ']; together they must cover every line of the part that carries meaning (blank/comment lines may be folded into a neighboring item or given a short item when they matter structurally). 3-8 items typical. Explain fragments verbatim in <code>.\n' +
    '- Bangla prose, English technical terms (hyphen suffixes like PID-টি). No emoji, no arrow characters (use -&gt; entity if ever needed). No placeholder text.\n' +
    '- robot.correct and robot.incorrect: concrete physical outcomes (wheels, lidar, buzzer, console), not generic filler.\n' +
    '- Write the file with the Write tool as strict JSON (UTF-8, raw Bangla). Validate it parses before finishing (python3 -c json.load).\n' +
    'Your final output is data, not prose for a human.'
}

function verifyPrompt(p) {
  return 'You are an ADVERSARIAL verifier for one Part JSON of the folder-13 code-analysis app. Default to skepticism.\n' +
    'Files to read:\n' +
    '1. ' + K + 'FACTS-13.md (ground truth)\n' +
    '2. ' + K + 'schema-part.md (schema + validation rules)\n' +
    '3. Source: ' + SRC + p.fname + ' (lines ' + p.start + '-' + p.end + ')\n' +
    '4. The artifact under review: ' + K + 'parts/part-' + String(p.n).padStart(2, '0') + '.json\n\n' +
    'Verify mechanically:\n' +
    '- JSON parses; exact key set; id/part number match; fname valid; start/end within file; animType matches the plan (' + (p.anim === null ? 'null' : p.anim) + ').\n' +
    '- Every explain {a,b} range is inside [' + p.start + ',' + p.end + '] and the union covers the meaningful lines of the part.\n' +
    '- Every factual claim about the source is TRUE per the source and FACTS-13 (line numbers quoted, verbatim code fragments, quirks present: ' + (p.brief.match(/QUIRK|never called|inf|magic|dead|typo|latch|never set/i) ? 'the quirks named in the part brief' : 'any the facts file lists for this range') + ').\n' +
    '- No invented behavior; vendor-unknown items (SinglePID internals, setup.py entry point, start_agent.sh contents) are labeled inferred/illustrative.\n' +
    '- math: ' + (p.math === 'none' ? 'must be null' : 'uses ONLY intro/levels/numeric/mapping/failure keys; LaTeX delimiters balanced; numerics match FACTS-13 section 3 arithmetic (recompute them yourself); failure list concrete') + '.\n' +
    '- Language rules: Bangla prose, English technical terms, no emoji, no arrow chars, no placeholder.\n' +
    '- robot blocks concrete (wheels/lidar/buzzer/console outcomes).\n\n' +
    'If ANY check fails: pass=false and list each issue as a one-line actionable fix instruction (cite the JSON path). Only pass=true when you could not refute the part on any axis. checkedLines = the source lines you actually re-read.'
}

function fixPrompt(p, issues) {
  return 'The Part JSON ' + K + 'parts/part-' + String(p.n).padStart(2, '0') + '.json failed adversarial verification for folder-13 part ' + p.n + '.\n' +
    'Read ' + K + 'FACTS-13.md, ' + K + 'schema-part.md, the source ' + SRC + p.fname + ' (lines ' + p.start + '-' + p.end + '), and the current JSON. Then REWRITE the JSON fixing every issue below while keeping everything that was already correct. Keep the same schema and animType.\n\n' +
    'ISSUES (each is actionable; fix all):\n' + issues.map((s, i) => (i + 1) + '. ' + s).join('\n') + '\n\n' +
    'Original part brief for context: ' + p.brief + '\n' +
    'Validate the rewritten file parses as JSON before finishing.'
}

const results = await pipeline(
  PARTS,
  (p) => agent(authorPrompt(p), { label: 'author:p' + p.n, phase: 'Author', schema: SUMMARY }),
  (authored, p) => agent(verifyPrompt(p), { label: 'verify:p' + p.n, phase: 'Verify', schema: VERDICT }),
  async (verdict, p) => {
    if (verdict && verdict.pass) return { n: p.n, outcome: 'pass', issues: [] }
    const issues = (verdict && verdict.issues) ? verdict.issues : ['verifier died or returned no issues — re-check the file against FACTS-13 and schema yourself']
    const fixed = await agent(fixPrompt(p, issues), { label: 'fix:p' + p.n, phase: 'Fix', schema: SUMMARY })
    const recheck = await agent(verifyPrompt(p), { label: 'reverify:p' + p.n, phase: 'Fix', schema: VERDICT })
    return { n: p.n, outcome: recheck && recheck.pass ? 'fixed' : 'STILL-FAILING', issues, fixed: fixed && fixed.notes }
  }
)

const summary = results.filter(Boolean).map(r => r.n + ':' + r.outcome)
log('parts outcomes: ' + summary.join(' '))
return { results, summary }
