export const meta = {
  name: 'nb12-parts',
  description: 'Author + adversarially verify the 15 v1 PARTS JSON files for folder 12 lidar tracking',
  phases: [
    { title: 'Author', detail: 'one author agent per Part writes parts/part-NN.json' },
    { title: 'Verify', detail: 'adversarial verifier re-reads source + facts and checks the file' },
    { title: 'Fix', detail: 'one repair round for failed parts using the issue list' },
  ],
}

const K = '/home/shariful/NeuroBotics/refine-kit/v2-12/'
const SRC = '/home/shariful/NeuroBotics/12. lidar tracking/'

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
  { n: 1,  fname: 'README.md',             enTitle: 'Runbook — Three Commands',              start: 1,   end: 5,   anim: 'runbookFlow',  math: 'none',
    brief: 'Three-command runbook. L1 sh start_agent.sh (vendor bringup, illustrative), L3 ros2 launch laser_driver.launch.py (sensor chain), L5 ros2 run laser_Tracker (the tracking node). L2/L4 blank separators. IDENTICAL to folder 11 except L5 names laser_Tracker instead of laser_Avoidance — say that explicitly. Downstream semantics: THIS node follows the nearest front object at 0.55 m stand-off (tracking), it does not avoid.' },
  { n: 2,  fname: 'laser_driver.launch.py', enTitle: 'Driver Launch — Imports',              start: 1,   end: 7,   anim: null,           math: 'none',
    brief: 'Six imports; the launch_ros Node import is unused in this file (comment admits just-in-case). Byte-identical driver to folder 11 — you may say that.' },
  { n: 3,  fname: 'laser_driver.launch.py', enTitle: 'Two Paths — Merger & Filter',           start: 8,   end: 24,  anim: 'includeChain', math: 'none',
    brief: 'generate_launch_description() def; two EAGER os.path.join(get_package_share_directory(...)) path builds: ira_laser_tools merge_multi.launch.py and yahboom_laser_filter laser_filter_node.launch.py. Constructor phase framing: strings are built, nothing runs yet.' },
  { n: 4,  fname: 'laser_driver.launch.py', enTitle: 'Return — Two Includes, Zero Nodes',     start: 26,  end: 42,  anim: null,           math: 'none',
    brief: 'LaunchDescription list with two IncludeLaunchDescription entries; blanks inside the list literal; run-phase order: merger then filter; the tracker node is NOT started by this file.' },
  { n: 5,  fname: 'laser_Tracker.py',       enTitle: 'Tracker Node — Module Head',            start: 1,   end: 15,  anim: null,           math: 'light',
    brief: 'ros lib + commom lib (typo IN SOURCE) comment blocks; rclpy/Twist/LaserScan imports; math, numpy; VERIFIED QUIRK: import time and from time import sleep are both dead (never used); star-import yahboom_M3Pro_laser.common gives Bool and SinglePID, module NOT in this folder — internals unknown, label inferred; print ("improt done") typo at import time L14; RAD2DEG = 180/math.pi L15. Math: Level 1-2 only — radian-to-degree unit conversion (pi rad = 180 deg), numeric example with 0.0174533 rad -> 1.0 deg.' },
  { n: 6,  fname: 'laser_Tracker.py',       enTitle: 'Constructor — Subscriptions & Publisher', start: 16, end: 29,  anim: 'subPubGraph',  math: 'none',
    brief: 'class laserTracker(Node); __init__(self,name) takes the name as an explicit argument; super().__init__(name); sub_laser /scan -> registerScan depth 1; sub_JoyState /JoyState -> JoyStateCallback depth 1, Bool is the yahboom common Bool not std_msgs; pub_vel /cmd_vel Twist depth 1. Same subscription/publisher topology as folder 11 avoidance node — contrast welcome.' },
  { n: 7,  fname: 'laser_Tracker.py',       enTitle: 'Four Parameters — Declare & Get',       start: 30,  end: 39,  anim: null,           math: 'none',
    brief: 'Four declare_parameter + get_parameter pairs: linear 0.5, angular 1.0, LaserAngle 45.0, ResponseDist 0.55. VERIFIED QUIRK: self.linear and self.angular are assigned then NEVER read again — the declared speed limits are not enforced, no clamp exists anywhere. get_parameter(...).get_parameter_value().double_value chain explained.' },
  { n: 8,  fname: 'laser_Tracker.py',       enTitle: 'State & Dual PID Controllers',          start: 40,  end: 49,  anim: null,           math: 'full',
    brief: 'Joy_active = False; lin_pid = SinglePID(1.0, 0.0, 1.0); ang_pid = SinglePID(2.0, 0.0, 2.0); controllers constructed once, internal state persists across scan callbacks; comment L48 says camera but the sensor is the LiDAR (stale wording). Math = the GENERIC PID law: u = Kp*e + Ki*integral(e) + Kd*de/dt, what Ki=0 removes, what Kd reacts to, why gains differ for distance vs angle; label vendor internals unknown, structure inferred.' },
  { n: 9,  fname: 'laser_Tracker.py',       enTitle: 'JoyStateCallback — Human Override',     start: 50,  end: 54,  anim: null,           math: 'none',
    brief: 'isinstance guard against the custom Bool; self.Joy_active = msg.data; True means human drives, AI pauses. When/why this fires.' },
  { n: 10, fname: 'laser_Tracker.py',       enTitle: 'registerScan — Beam Loop & Front Cone', start: 55,  end: 72,  anim: 'beamSweep',    math: 'full',
    brief: 'THE angle math part. Type guard; ranges = np.array(scan_data.ranges); two parallel lists minDistList/minDistIDList (distance + DEGREE angle); for i in range(len(ranges)) visits every beam; angle = (angle_min + angle_increment*i) * RAD2DEG; with the fused ring from folder 10 (angle_min = -3.14159, increment = 0.0174533) angle_i = -180 + i degrees (illustrative); front cone abs(angle) < 45.0 STRICT open interval -> i in (135,225) -> 89 beams; ranges[i] != 0.0 passes inf (no-return) readings — honest inf edge case. Math Levels 1-5 + numeric (i=192 -> +12 deg) + mapping + failure (wrong increment shifts every angle, cone misaligned).' },
  { n: 11, fname: 'laser_Tracker.py',       enTitle: 'Closest Beam & Override Gates',         start: 73,  end: 88,  anim: null,           math: 'light',
    brief: 'Empty-list guard; minDist = min(minDistList); minDistID = minDistIDList[minDistList.index(minDist)] — the angle OF the closest beam, argmin semantics, ties resolve to FIRST occurrence (lowest i, most negative angle); else-branch prints ----------------------- and bare returns (no publish — motors keep the last command, they are not stopped); Joy_active branch publishes an all-zero Twist() on EVERY scan while held (active brake) then returns.' },
  { n: 12, fname: 'laser_Tracker.py',       enTitle: 'Velocity & Stand-off Deadzone',         start: 89,  end: 96,  anim: null,           math: 'full',
    brief: 'velocity = Twist(); print minDist/minDistID at scan rate; deadzone abs(minDist - 0.55) < 0.1 snaps minDist := 0.55 so the linear PID sees zero error — kills forward/backward jitter. Math: the band [0.45, 0.65], snap sets e = 0; numeric Wave C 0.58 -> snapped; failure: band too wide stalls the robot off-target, band zero reintroduces jitter.' },
  { n: 13, fname: 'laser_Tracker.py',       enTitle: 'Dual PID — Approach & Centering',       start: 97,  end: 114, anim: 'pidDial',      math: 'full',
    brief: 'THE math heart. velocity.linear.x = -self.lin_pid.pid_compute(self.ResponseDist, minDist) — call order (target, current); the minus sign: with error = first - second, far object gives negative pid, minus makes linear.x positive = approach; the file comment claims positive-when-far which does not match that convention cleanly — present the code text, quote the comment intent, mark the direction conclusion inferred (vendor SinglePID source NOT in this folder). ang_pid_compute = pid_compute(abs(minDistID)/72, 0) — 72 is a bare magic number the file never explains; observable effect: max |angle| just under 45 -> target just under 0.625. Sign branch: 0 < minDistID -> z = +compute (left/CCW), minDistID < 0 -> z = -compute (right), exactly 0.0 -> neither, z stays 0. Math Levels 1-6 full progressive derivation + numeric Waves A and B + mapping + failure (sign flip backs away, wrong 72 changes responsiveness, unclamped output exceeds declared linear 0.5).' },
  { n: 14, fname: 'laser_Tracker.py',       enTitle: 'Turn Deadzone, Damping & Publish',      start: 115, end: 125, anim: 'cmdVelVectors', math: 'full',
    brief: 'if abs(ang_pid_compute) < 0.5: angular.z = 0 — LARGE turn deadzone; with the Kp=2 term 2*(|a|/72) < 0.5 -> |a| < 18 deg means NO turn (illustrative, Kp-only view; Kd transient can differ on step changes); angular.z *= 0.6 damping; effective ceiling ~ (2*0.625)*0.6 = 0.75 rad/s; print angular.z; pub_vel.publish(velocity). Numeric Wave B: 20 deg -> 0.556 -> passes deadzone -> x0.6 -> +0.33 rad/s left.' },
  { n: 15, fname: 'laser_Tracker.py',       enTitle: 'exit_pro & main — Brake and Shutdown',  start: 126, end: 146, anim: 'safetyHalt',   math: 'none',
    brief: 'exit_pro builds cmd = ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist (trailing space) + quoted zero-YAML string, os.system shell one-shot brake from outside the node; main(): rclpy.init, laserTracker("laser_Tracker_a1"), print start it, try/spin/except KeyboardInterrupt pass, finally exit_pro -> destroy_node -> rclpy.shutdown. VERIFIED: the file never calls main() and has no __main__ guard — ros2 run works via the package setup.py console_scripts entry point (NOT in this folder; label inferred).' },
]

function authorPrompt(p) {
  const mathLine = p.math === 'none'
    ? 'math MUST be null (no genuine mathematics in this part).'
    : (p.math === 'light'
      ? 'math REQUIRED but compact: intro + 1-2 levels + at least one numeric + mapping or failure (use both if they earn their place).'
      : 'math REQUIRED and FULL: intro + Levels (as many as the derivation honestly supports, up to 6) + numeric examples computed from FACTS-12 section 3 values (label illustrative) + code-to-math mapping + failure list.')
  let refs = ''
  if (p.n <= 4) refs += '\n- ADAPTATION REFERENCE: ' + K + 'parts-11-refs-1-4.json — folder 11 shipped parts 1-4 for this SAME README/driver (driver byte-identical). Reuse their verified structure and cross-folder context where still true, but UPDATE every downstream reference: folder 11 said the L5 node laser_Avoidance avoids obstacles; folder 12 runs laser_Tracker which FOLLOWS the nearest front object at 0.55 m. Also update any folder-11 self-reference to say folder 11 (past app) vs this app folder 12.'
  if (p.n === 6 || p.n === 15) refs += '\n- STYLE REFERENCE: ' + K + 'parts-11-refs-6-15.json — shipped folder-11 parts 6 and 15 for tone/depth calibration (their animType line refs differ; do not copy line numbers).'
  return 'You are authoring ONE Part of a Bangla line-by-line code-analysis app for the ROS 2 robot folder "12. lidar tracking".\n' +
    'Work in ' + K + ' . Output file: ' + K + 'parts/part-' + String(p.n).padStart(2, '0') + '.json\n\n' +
    'BINDING INPUTS — read all of these first (they are short):\n' +
    '1. ' + K + 'FACTS-12.md  — verified ground truth. Every quirk stated there for your line range MUST appear in your explanations. Never contradict it; never invent beyond it.\n' +
    '2. ' + K + 'schema-part.md — exact JSON schema, renderer-supported math keys (NEVER a "blocks" key), house style, terminology rules.\n' +
    '3. The source file ' + SRC + p.fname + ' — READ-ONLY. Quote fragments verbatim. Your part covers REAL source lines ' + p.start + ' to ' + p.end + ' (1-based, splitlines numbering).' + refs + '\n\n' +
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
    '- robot.correct and robot.incorrect: concrete physical outcomes (wheels, lidar, console), not generic filler.\n' +
    '- Write the file with the Write tool as strict JSON (UTF-8, raw Bangla). Validate it parses before finishing (python3 -c json.load).\n' +
    'Your final output is data, not prose for a human.'
}

function verifyPrompt(p) {
  return 'You are an ADVERSARIAL verifier for one Part JSON of the folder-12 code-analysis app. Default to skepticism.\n' +
    'Files to read:\n' +
    '1. ' + K + 'FACTS-12.md (ground truth)\n' +
    '2. ' + K + 'schema-part.md (schema + validation rules)\n' +
    '3. Source: ' + SRC + p.fname + ' (lines ' + p.start + '-' + p.end + ')\n' +
    '4. The artifact under review: ' + K + 'parts/part-' + String(p.n).padStart(2, '0') + '.json\n\n' +
    'Verify mechanically:\n' +
    '- JSON parses; exact key set; id/part number match; fname valid; start/end within file; animType matches the plan (' + (p.anim === null ? 'null' : p.anim) + ').\n' +
    '- Every explain {a,b} range is inside [' + p.start + ',' + p.end + '] and the union covers the meaningful lines of the part.\n' +
    '- Every factual claim about the source is TRUE per the source and FACTS-12 (line numbers quoted, verbatim code fragments, quirks present: ' + (p.brief.match(/QUIRK|never called|inf|magic|dead/) ? 'the quirks named in the part brief' : 'any the facts file lists for this range') + ').\n' +
    '- No invented behavior; vendor-unknown items (SinglePID internals, setup.py entry point, start_agent.sh contents) are labeled inferred/illustrative.\n' +
    '- math: ' + (p.math === 'none' ? 'must be null' : 'uses ONLY intro/levels/numeric/mapping/failure keys; LaTeX delimiters balanced; numerics match FACTS-12 section 3 arithmetic (recompute them yourself); failure list concrete') + '.\n' +
    '- Language rules: Bangla prose, English technical terms, no emoji, no arrow chars, no placeholder.\n' +
    '- robot blocks concrete.\n\n' +
    'If ANY check fails: pass=false and list each issue as a one-line actionable fix instruction (cite the JSON path). Only pass=true when you could not refute the part on any axis. checkedLines = the source lines you actually re-read.'
}

function fixPrompt(p, issues) {
  return 'The Part JSON ' + K + 'parts/part-' + String(p.n).padStart(2, '0') + '.json failed adversarial verification for folder-12 part ' + p.n + '.\n' +
    'Read ' + K + 'FACTS-12.md, ' + K + 'schema-part.md, the source ' + SRC + p.fname + ' (lines ' + p.start + '-' + p.end + '), and the current JSON. Then REWRITE the JSON fixing every issue below while keeping everything that was already correct. Keep the same schema and animType.\n\n' +
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
    const issues = (verdict && verdict.issues) ? verdict.issues : ['verifier died or returned no issues — re-check the file against FACTS-12 and schema yourself']
    const fixed = await agent(fixPrompt(p, issues), { label: 'fix:p' + p.n, phase: 'Fix', schema: SUMMARY })
    const recheck = await agent(verifyPrompt(p), { label: 'reverify:p' + p.n, phase: 'Fix', schema: VERDICT })
    return { n: p.n, outcome: recheck && recheck.pass ? 'fixed' : 'STILL-FAILING', issues, fixed: fixed && fixed.notes }
  }
)

const summary = results.filter(Boolean).map(r => r.n + ':' + r.outcome)
log('parts outcomes: ' + summary.join(' '))
return { results, summary }
