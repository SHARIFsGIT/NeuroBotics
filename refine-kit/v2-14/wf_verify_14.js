export const meta = {
  name: 'verify-14-units',
  description: 'Adversarially verify the 12 exec units left unverified by the 429-storm run; repair flagged steps',
  phases: [
    { title: 'Verify', detail: '12 adversarial verifiers over out-U*.json vs skeleton + sources' },
    { title: 'Fix', detail: 'repair only flagged steps, passing steps byte-identical' },
  ],
}

const KIT = '/home/shariful/NeuroBotics/refine-kit/v2-14'
const SRC = '/home/shariful/NeuroBotics/14. SLAM Gmapping'

const UNITS = [
  {u:'U2',  title:'gmapping L24-49: four eager share-path joins (merger/filter/ekf/gmapping) (11 steps)', refs:'ref-driver.json'},
  {u:'U3',  title:'gmapping L50-94: imu Node + FINAL LIST ctor + 5 run-phase events (15 steps)', refs:'ref-driver.json'},
  {u:'U5',  title:'slam_view L30-59: rviz_config join + rviz Node + 2 run events (9 steps)', refs:'ref-driver.json'},
  {u:'U7',  title:'keyboard L66-121: class head, pubs/params, getKey, step_arm_joint clamps (20 steps)', refs:'ref-import.json'},
  {u:'U8',  title:'keyboard L122-242: reset_arm, e-stop, main head + loop compiled (17 steps)', refs:'ref-import.json'},
  {u:'U9',  title:'keyboard main pass: ctor replays, limits read, reset_arm publish, loop parked (16 steps)', refs:'ref-main.json'},
  {u:'U12', title:'keyboard waves: s pause, s resume, deadman 5 polls, Ctrl+C halt (22 steps)', refs:'ref-wave.json'},
  {u:'U13', title:'README L8-9 + camera L1-40: LIST-arg include + kin node + 2 run events (17 steps)', refs:'ref-open.json + ref-driver.json'},
  {u:'U16', title:'follow_line L116-244: registerScan cone, callbacks, declare_param, PID_init (27 steps)', refs:'ref-import.json'},
  {u:'U17', title:'follow_line L245-321: execute + process head compiled (22 steps)', refs:'ref-import.json'},
  {u:'U19', title:'follow_line main pass: banner, blocking arm-wait, 14 params, spin parked (29 steps)', refs:'ref-main.json'},
  {u:'U20', title:'follow_line waves: JoyState gate, /scan1 cone counts, synced pair F1-F4 (24 steps)', refs:'ref-wave.json'},
]

const VERDICT_SCHEMA = {
  type: 'object', required: ['verdict', 'issues', 'summary'],
  properties: {
    verdict: {type: 'string', enum: ['pass', 'fail']},
    pass_steps: {type: 'integer'},
    issues: {type: 'array', maxItems: 40, items: {
      type: 'object', required: ['i', 'field', 'problem'],
      properties: {
        i: {type: 'integer'}, field: {type: 'string'},
        problem: {type: 'string'}, fix_hint: {type: 'string'},
      },
    }},
    summary: {type: 'string'},
  },
}
const FIX_SCHEMA = {
  type: 'object', required: ['file', 'fixed_count'],
  properties: {file: {type: 'string'}, fixed_count: {type: 'integer'}, remaining_concerns: {type: 'string'}},
}

const PREAMBLE = (u) => `You are auditing content for the v2 "Complete Execution" section of a Bangla ROS 2 code-analysis app for folder "14. SLAM Gmapping".
BINDING, read in this order before judging anything:
1. ${KIT}/FACTS-14.md  (verified ground truth; if it conflicts with your reading, the SOURCE files win)
2. ${KIT}/exec/exec-brief-14.md  (the style contract: field rules, canonical tables, dbg registry, rob SVG grammar, 23-unit sequence context, prohibitions)
3. ${KIT}/exec/shell-14.json  (rob0 = the panel chrome starting state)
Source files (READ-ONLY — modifying them is a hard failure; 7 files, 984 lines):
${SRC}/README.md · ${SRC}/gmapping.launch.py · ${SRC}/slam_view.launch.py · ${SRC}/yahboom_keyboard.py · ${SRC}/camera_arm_kin.launch.py · ${SRC}/follow_line.py · ${SRC}/save_map.launch.py
Unit ${u} lives in ${KIT}/exec/out-${u}.json (write scope: verifier = nothing; fixer = exactly that one file). Never touch the source folder.`

const VERIFY = (x) => `${PREAMBLE(x.u)}

You are an ADVERSARIAL verifier. Another agent authored ${KIT}/exec/out-${x.u}.json for unit ${x.u} (${x.title}). Your job is to FAIL it if at all possible; pass only what survives.
Read: FACTS-14.md, exec-brief-14.md, exec/unit-${x.u}.json (skeleton), exec/${x.refs} (calibration), the 7 source files, then out-${x.u}.json.

Hard checks (any failure = verdict fail):
1. out-${x.u}.json parses as JSON; steps length == skeleton length; i-set == {0..N-1} exactly; file/ln/lns/kind were NOT altered (compare against skeleton).
2. Quote fidelity: for at least 8 steps, every code fragment inside <code> in cap (and any code echoed in fx) matches the REAL source lines at lns character-for-character (duplicate Node import, dead lists, /JoyState duplicate sub L38/L40, "Reset succes!!!" typo, TAB indentation in follow_line.py — all preserved, never fixed).
3. Canonical numbers: keyboard waves (i -> (0.20, 0.00, 0.00); u -> (0.20, 0.20, 0.00); q -> speed 0.22 turn 1.10; 1 -> joint1 85 time 500 clamp 0..180; g -> joint6 85 Closing clamp 30..180; SPACE -> zero Twist + arm brake time 100; s pause -> PAUSED True + e-stop; deadman count 1..5 -> zeros); follow_line frames (F1 260 -> z -0.1875 publish (0.1,-0.1875); F2 300 deadzone -> (0.1, 0.0); F3 380 -> +0.1875; F4 320 -> 0.0); registerScan cone (|angle|<30 or >330, ranges != 0.0, <= 0.375 -> count; obstacle at >10 -> beep 1); Remove (R1 (350,430) -> raw 0.12 clamp 0.10 pubVel(0.10,0.10); R2 (328,405) -> swap: linear.x 0.020 linear.y 0.032); centered (|dx|<10 and |dy|<10 -> pubVel 0,0, sleep 3, c_dist depth/1000, joint5 published TWICE); save_map (--free 0.196 --occ 0.65 yahboom_map one-shot). Every non-source-true number flagged "ill".
4. Fact safety: no invented vendor internals (start_agent.sh / follow_common helpers / ira_laser_tools / slam_gmapping / orbbec / arm driver), no claim that gmapping.launch.py starts keyboard or follow_line (README L7/L11 do), no "fix" of source bugs, Kp-60-never-wired and linear-0.18-never-used facts only where the brief schedules them, no emoji, no Unicode arrows anywhere, Bangla style rules (English technical terms, hyphen-suffix, transliteration tolerance ONLY টেস্ট/রেজিস্টার/ডিগ্রি/স্কিপ/রিসেট/স্টিয়ারিং).
5. rob: non-empty ones start with the verbatim chrome rects/texts; all tags closed, attributes quoted, coordinates within 440x330, exactly 3 bottom Bangla lines at y 262/273/284, no ids re-declared, no scripts, no Unicode arrows in SVG text. Empty-string rob allowed (keeps prior panel).
6. Boundary continuity per exec-brief-14.md "Sequence context" (the 23-unit table): the unit's first step picks up the stated incoming state; the last step leaves the stated outgoing state (dbg keys + panel).
7. kind voice: struct steps speak define/bind/not-run; exec steps show a state change NOW; event steps are message/framework/key/command driven.
Report every defect as {i, field, problem, fix_hint} (i = step index, -1 for file-level). Also list up to 3 non-blocking polish suggestions inside summary. Write nothing to disk.
Return: verdict pass only if zero blocking issues.`

const FIX = (x, issuesJson) => `${PREAMBLE(x.u)}

You are the repair agent. ${KIT}/exec/out-${x.u}.json (unit ${x.u}, ${x.title}) failed verification. The verifier reported these issues:
${issuesJson}

Read FACTS-14.md, exec-brief-14.md, exec/unit-${x.u}.json (skeleton), the 7 source files, and the current out-${x.u}.json. Repair EXACTLY the flagged steps (and any directly-colliding neighbors) while leaving passing steps byte-identical. Keep the JSON single-object {"steps":[...]} shape, full Bangla content, all brief rules.
Overwrite ${KIT}/exec/out-${x.u}.json with the corrected full file. Re-run the author self-check (parse, count, i-set, quote fidelity on what you touched).
Return {"file":"out-${x.u}.json","fixed_count":<n>,"remaining_concerns":"..."}.`

phase('Verify')
log('12 adversarial verifiers over the storm-survivor + fresh units')
const results = await pipeline(UNITS,
  (x) => agent(VERIFY(x), {label: `verify:${x.u}`, phase: 'Verify', schema: VERDICT_SCHEMA}),
  async (v, x) => {
    if (!v) return {u: x.u, verdict: 'verifier-died', fixed: false}
    if (v.verdict === 'pass' || !v.issues || !v.issues.length) {
      log(`${x.u}: PASS (${v.pass_steps ?? 'all'} steps)`)
      return {u: x.u, verdict: 'pass', issues: 0, fixed: false, summary: (v.summary || '').slice(0, 200)}
    }
    log(`${x.u}: FAIL with ${v.issues.length} issues -> fixer`)
    const fx = await agent(FIX(x, JSON.stringify(v.issues, null, 1)),
      {label: `fix:${x.u}`, phase: 'Fix', schema: FIX_SCHEMA})
    if (!fx) return {u: x.u, verdict: 'fail', issues: v.issues.length, fixed: false,
                     summary: 'fixer died — issues: ' + v.issues.map(i2 => `#${i2.i} ${i2.field}`).join('; ').slice(0, 400)}
    return {u: x.u, verdict: v.verdict, issues: v.issues.length, fixed: true,
            fixedCount: fx.fixed_count, concerns: (fx.remaining_concerns || '').slice(0, 300)}
  }
)
const out = results.filter(Boolean)
log(`verify round done: ${out.filter(r => r.verdict === 'pass').length} pass, ` +
    `${out.filter(r => r.fixed).length} repaired, ${out.filter(r => r.verdict !== 'pass' && !r.fixed).length} UNRESOLVED`)
return {units: out}
