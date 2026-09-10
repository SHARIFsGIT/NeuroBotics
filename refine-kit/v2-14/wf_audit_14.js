export const meta = {
  name: 'audit-14-deliverable',
  description: 'Adversarial truth-audit of the assembled folder-14 deliverable vs its read-only sources',
  phases: [
    { title: 'Audit', detail: '9 dimension auditors over the built HTML + spec + parts' },
    { title: 'Confirm', detail: '3-lens refute-panel per finding; only >=2-vote defects survive' },
  ],
}

const KIT = '/home/shariful/NeuroBotics/refine-kit/v2-14'
const DELIV = '/home/shariful/NeuroBotics/14. SLAM Gmapping/14. SLAM Gmapping.html'
const SRC = '/home/shariful/NeuroBotics/14. SLAM Gmapping'

const COMMON = `You are auditing the FINAL assembled deliverable ${DELIV} for folder "14. SLAM Gmapping" (a Bangla ROS 2 line-by-line code-analysis app, two layers: v1 Parts + v2 Complete Execution).
Ground truth, read first:
1. ${KIT}/FACTS-14.md
2. ${KIT}/exec/exec-brief-14.md (the binding authoring contract)
3. the READ-ONLY sources in ${SRC}/: README.md (15 lines, sha 1246ab7881c6), gmapping.launch.py (94, e9d107d1fa6d), slam_view.launch.py (59, ff4b1234ffdd), yahboom_keyboard.py (242, 536b2850bd2a), camera_arm_kin.launch.py (40, 6b2b105f277e), follow_line.py (485, 88a485372c54, TAB-indented, Chinese comment L148), save_map.launch.py (49, 3601e4887d57)
The deliverable is large. Extract the layer you need from the built HTML: the v1 PARTS const and the v2 "var EXEC_SPEC = ..." line are both single minified lines inside <script> tags — parse with python3 (strip the "const PARTS = "/"var EXEC_SPEC = " prefix and trailing ";", then json.loads) or read the pre-assembly kit files which are byte-identical to what was embedded:
- v1 parts: ${KIT}/parts/part-01..15.json
- v2 spec: ${KIT}/exec/exec-spec-14.json (423 steps; spine = U1..U23 concatenated)
Write NOTHING to disk. Report findings only.`

const DIMENSIONS = [
  {key: 'exec-truth-1', prompt: `${COMMON}
YOUR DIMENSION: v2 exec steps, spine indices 0..78 (README runbook odd lines L1/3/5/7, gmapping.launch.py constructor + run, slam_view.launch.py constructor + run). Hard checks: quoted code in cap/fx must be a character-exact substring of the real source lines at lns (preserve quirks: dup Node import L2+L9, unused LaunchConfiguration/Declare L3-4, three dead lists L17-19, TAB indentation in follow_line not here); the four eager joins L24-49 color-story (merger/filter/ekf/gmapping) must be path resolution at CONSTRUCTION, never node start; five-entry list L66-93 = 4 includes + imu Node L53-62 with remap L60 ('/imu' to/from '/imu/data_raw'); slam_view rviz Node L41-52 arguments=['-d', rviz_config, use_sim_time] L48-52 with 7 self-acknowledged unused imports L2-3; every non-source-true number flagged ill. Report each defect as a finding.`},
  {key: 'exec-truth-2', prompt: `${COMMON}
YOUR DIMENSION: v2 exec steps, spine indices 79..185 (yahboom_keyboard.py import pass: banner L16-45, moveBindings L47-58 12 keys, speedBindings L60-64; class body pubs/params/getKey/step_arm_joint clamps L66-121; L122-242 reset_arm/e-stop/main; main-pass replays; waves i/u/q/1/g/r/SPACE/s/deadman/Ctrl+C). Canonical table from exec-brief-14.md must hold: i -> (0.20,0.00,0.00); u -> (0.20,0.20,0.00); q -> speed x1.1 (0.22); 1 -> joint1 85 time 500; g -> joint6 85 Closing; SPACE -> zero Twist + brake time 100; s pause/resume; deadman count 1..5; Ctrl+C clean halt. Quote fidelity character-exact; every invented number flagged ill. Report each defect as a finding.`},
  {key: 'exec-truth-3', prompt: `${COMMON}
YOUR DIMENSION: v2 exec steps, spine indices 186..289 (README L8-9 + camera_arm_kin.launch.py L1-40 include-with-LIST-arg + kin node; README L10-11 + follow_line.py import passes L1-244 compiled: class head, pubs/subs/sync/Detector, registerScan cone, callbacks, declare_param, PID_init, execute + process head). Hard checks: registerScan cone bounds <30 deg / >330 deg + ranges[i] != 0.0 + <=0.375 m; FollowLinePID Kp 0.05 Ki 0 Kd 0.01; e = (point_x-320)*1.0/16 L261; deadzone abs(point_x-320) < 40 -> z=0 L282-284; linear.x = 0.1 hardcoded L269; front_warning > 10 -> stop + buzzer 1; clear -> buzzer 0 x3 L279. TAB indentation of follow_line.py is source truth. Report each defect as a finding.`},
  {key: 'exec-truth-4', prompt: `${COMMON}
YOUR DIMENSION: v2 exec steps, spine indices 290..422 (follow_line process tail + remove_obstacle swap + Reset typo + get_param; main pass: banner L434-468, blocking arm-wait, 14 params, spin; waves JoyState gate / scan cone counts / synced frames F1 260->(0.1,-0.1875), F2 300 deadzone->(0.1,0.0), F3 380->(0.1,+0.1875), F4 320->(0.1,0.0); obstacle beep, clear 3x off; AprilTag R1 (350,430)->clamp (0.10,0.10), R2 (328,405)->SWAP linear.x 0.020/linear.y 0.032, centered +-10 -> sleep 3 + c_dist/1000 + joint5 TWICE L375-376; grasp + Ctrl+C halt prints L475-485 with zero-Twist L483 AFTER prints, NO cv destroy; README L12-13 arm topic-pub --once; save_map ctor + run: map_saver one-shot, --free 0.196/--occ 0.65, yaml+pgm written, launch exits). Report each defect as a finding.`},
  {key: 'v1-parts-1', prompt: `${COMMON}
YOUR DIMENSION: v1 parts 1-8 (kit files part-01..08.json). Verify every claim that names a source fact: line numbers cited match the real files, code quotes are character-exact substrings, numbers consistent with FACTS-14 (speed 0.2 turn 1.0, Kp 0.05/0/0.01, 0.196/0.65, x1.1/x0.9, clamp values, joint values 85/500, 0.375 m, cone bounds). Math sections must derive from source constants only; illustrative numbers flagged conceptual/illustrative. Report each defect as a finding.`},
  {key: 'v1-parts-2', prompt: `${COMMON}
YOUR DIMENSION: v1 parts 9-15 (kit files part-09..15.json). Same hard checks as parts 1-8 plus: Real Robot correct/incorrect blocks must match source behavior (e.g. keyboard no-clamp-at-birth quirks, follow_line linear.x hardcoded so PID never slows the robot, remove_obstacle SWAP story, joint5 twice); no claim that gmapping.launch.py starts the viewer/teleop (README L5/L7 do); no invented vendor internals (compute_joint5 internals, Jetson, SinglePID-like modules are illustrative if flagged). Report each defect as a finding.`},
  {key: 'cross-layer', prompt: `${COMMON}
YOUR DIMENSION: cross-layer consistency. The v1 Parts (parts/part-*.json) and the v2 exec spec (exec/exec-spec-14.json) must never contradict: same canonical numbers (0.2/1.0, 0.05/0/0.01, 16, 40, 10, 0.375, 30/330, 0.196/0.65, 85/500, 1.1/0.9, 0.020/0.032, 320/400 +-10), same story (dup import + dead lists + eager joins; imu remap; -d rviz config; hardcoded linear.x; joint5 twice; zero-Twist after prints; one-shot map_saver exits), same file order (README, gmapping, slam_view, keyboard, camera_arm_kin, follow_line, save_map). Also check hero/intro/footer embedded in the built HTML matches folder-14 identity. Report each contradiction as a finding.`},
  {key: 'stale-identity', prompt: `${COMMON}
YOUR DIMENSION: stale-identity sweep over the BUILT HTML itself (read ${DELIV} in chunks with python3). Any folder-11/12/13 identity leakage: "laser_Avoidance", "laser_Tracker", "laser_Warning", "obstacle avoidance"/"lidar tracking"/"lidar guard" as this app's title/identity (allowed ONLY as small explicit comparative cross-references like "folder 10-এর merger" — flag anything that reads as identity, not comparison), tracker sha d414af8d12da, folder-11 sha 3433bd6ce68a, folder-13 shas 7de1ece640db/dadf5ff3f9b1/b1cf2d67a4d5, engine header counts "178 steps"/"234 lines" (must now read 423/984). Also verify title tag = "14. SLAM Gmapping", hero h1 names folder 14, footer names folder 14. Report each finding.`},
  {key: 'bangla-style', prompt: `${COMMON}
YOUR DIMENSION: Bangla style sweep across both kit layers (parts/*.json + exec/exec-spec-14.json). Rules: English technical terms stay Latin with hyphen-suffix attachment (PID-টি, scan-এ); NO emoji anywhere; NO Unicode arrows in exec spec dbg values or v1 stage <text> (ASCII -> allowed in fx); no Bangla numerals inside dbg values or SVG coordinates (Bangla numerals fine in captions/Bangla prose); tolerated transliterations are ONLY টেস্ট/রেজিস্টার/ডিগ্রি/স্কিপ/রিসেট — flag any OTHER English technical term rendered in Bangla script (like ল্যাচ, ডেডজোন, কলব্যাক, স্টেপ is fine only inside Bangla prose, not as a technical-term replacement). Report each violation with file+location.`},
]

const FINDINGS_SCHEMA = {
  type: 'object', required: ['findings'],
  properties: {
    findings: {type: 'array', maxItems: 25, items: {
      type: 'object', required: ['where', 'claim', 'problem'],
      properties: {
        where: {type: 'string'}, claim: {type: 'string'},
        problem: {type: 'string'}, evidence: {type: 'string'},
      },
    }},
    checked: {type: 'string'},
  },
}
const VERDICT_SCHEMA = {
  type: 'object', required: ['real'],
  properties: {real: {type: 'boolean'}, reason: {type: 'string'}, severity: {type: 'string', enum: ['blocker', 'should-fix', 'polish']}},
}

phase('Audit')
log('9 dimension auditors over the assembled deliverable')
const results = await pipeline(DIMENSIONS,
  (d) => agent(d.prompt, {label: `audit:${d.key}`, phase: 'Audit', schema: FINDINGS_SCHEMA}),
  async (res, d) => {
    if (!res || !res.findings || !res.findings.length) return {dim: d.key, confirmed: [], checked: res ? res.checked : 'agent died'}
    log(`${d.key}: ${res.findings.length} raw findings -> refute panel`)
    const judged = await parallel(res.findings.map(f => () =>
      parallel([1, 2, 3].map(n => () =>
        agent(`${COMMON}
A fellow auditor reported this defect in the folder-14 deliverable:
WHERE: ${f.where}
CLAIM UNDER AUDIT: ${f.claim}
PROBLEM: ${f.problem}
EVIDENCE: ${f.evidence || '(none given)'}
Lens ${n} of 3 (${n === 1 ? 'source-truth: re-read the actual source lines and re-derive the number/quote' : n === 2 ? 'context: is the flagged text perhaps an explicit illustrative/comparative statement already flagged ill, or shipped-convention wording?' : 'rendered-surface: does this text actually reach the user, or is it kit-side metadata/comments that never render?'}).
Adversarially try to REFUTE the finding. real=true only if the defect is genuine, user-visible or spec-level, and not excused by convention/flagging. Assign severity: blocker = factually wrong about the source; should-fix = style/consistency defect in rendered content; polish = borderline.`,
          {label: `confirm:${d.key}`, phase: 'Confirm', schema: VERDICT_SCHEMA})))
        .then(vs => ({f, votes: vs.filter(Boolean).filter(v => v.real)}))
    ))
    const confirmed = judged.filter(Boolean).filter(j => j.votes.length >= 2)
      .map(j => ({where: j.f.where, claim: j.f.claim, problem: j.f.problem,
                   severity: (j.votes.map(v => v.severity).filter(s => s === 'blocker').length ? 'blocker'
                            : j.votes.map(v => v.severity).filter(s => s === 'should-fix').length ? 'should-fix' : 'polish'),
                   reasons: j.votes.map(v => v.reason).slice(0, 3)}))
    log(`${d.key}: ${confirmed.length}/${res.findings.length} confirmed`)
    return {dim: d.key, confirmed, checked: res.checked}
  }
)
const out = results.filter(Boolean)
const all = out.flatMap(r => r.confirmed)
log(`audit done: ${all.length} confirmed findings (${all.filter(f => f.severity === 'blocker').length} blockers)`)
return {confirmed: all, dims: out.map(r => ({dim: r.dim, n: r.confirmed.length, checked: r.checked}))}
