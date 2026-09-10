export const meta = {
  name: 'exec-spec-14',
  description: 'Author + adversarially verify 423 exec-spec steps (23 units) for folder 14 SLAM Gmapping',
  phases: [
    { title: 'Author', detail: '23 unit authors write out-U*.json (fresh authoring; folder-11 refs are calibration only)' },
    { title: 'Verify', detail: 'adversarial check per unit vs FACTS + brief' },
    { title: 'Fix', detail: 'repair flagged steps, rewrite file' },
  ],
}

const KIT = '/home/shariful/NeuroBotics/refine-kit/v2-14'
const SRC = '/home/shariful/NeuroBotics/14. SLAM Gmapping'

const UNITS = [
  {u:'U1',  title:'README L1-3 + gmapping L1-23: bringup, launch typed, imports, dead lists (14 steps)', refs:'ref-open.json + ref-driver.json'},
  {u:'U2',  title:'gmapping L24-49: four eager share-path joins (merger/filter/ekf/gmapping) (11 steps)', refs:'ref-driver.json'},
  {u:'U3',  title:'gmapping L50-94: imu Node + FINAL LIST ctor + 5 run-phase events (15 steps)',          refs:'ref-driver.json'},
  {u:'U4',  title:'README L4-5 + slam_view L1-29: rviz typed, imports (7 unused), use_sim_time (11 steps)', refs:'ref-open.json'},
  {u:'U5',  title:'slam_view L30-59: rviz_config join + rviz Node + 2 run events (9 steps)',               refs:'ref-driver.json'},
  {u:'U6',  title:'README L6-7 + keyboard L1-65: teleop typed, banner + bindings compiled (19 steps)',      refs:'ref-import.json'},
  {u:'U7',  title:'keyboard L66-121: class head, pubs/params, getKey, step_arm_joint clamps (20 steps)',   refs:'ref-import.json'},
  {u:'U8',  title:'keyboard L122-242: reset_arm, e-stop, main head + loop compiled (17 steps)',            refs:'ref-import.json'},
  {u:'U9',  title:'keyboard main pass: ctor replays, limits read, reset_arm publish, loop parked (16 steps)', refs:'ref-main.json'},
  {u:'U10', title:'keyboard waves: i forward, u diagonal, q speed x1.1, 1 joint1 -5 (17 steps)',           refs:'ref-wave.json'},
  {u:'U11', title:'keyboard waves: g gripper close, r reset, SPACE e-stop (15 steps)',                     refs:'ref-wave.json'},
  {u:'U12', title:'keyboard waves: s pause, s resume, deadman 5 polls, Ctrl+C halt (22 steps)',            refs:'ref-wave.json'},
  {u:'U13', title:'README L8-9 + camera L1-40: LIST-arg include + kin node + 2 run events (17 steps)',     refs:'ref-open.json + ref-driver.json'},
  {u:'U14', title:'README L10-11 + follow_line L1-58: typed, wildcard imports, class head (16 steps)',     refs:'ref-import.json'},
  {u:'U15', title:'follow_line L59-115: pubs/subs/sync/Detector/state compiled (22 steps)',                refs:'ref-import.json'},
  {u:'U16', title:'follow_line L116-244: registerScan cone, callbacks, declare_param, PID_init (27 steps)', refs:'ref-import.json'},
  {u:'U17', title:'follow_line L245-321: execute + process head compiled (22 steps)',                      refs:'ref-import.json'},
  {u:'U18', title:'follow_line L322-431: process tail, remove_obstacle swap, Reset typo, get_param (21 steps)', refs:'ref-import.json'},
  {u:'U19', title:'follow_line main pass: banner, blocking arm-wait, 18 params, spin parked (29 steps)',   refs:'ref-main.json'},
  {u:'U20', title:'follow_line waves: JoyState gate, /scan1 cone counts, synced pair F1-F4 (24 steps)',    refs:'ref-wave.json'},
  {u:'U21', title:'follow_line waves: obstacle beep, clear 3x-off, apriltag R1/R2/centered/joint5-twice (28 steps)', refs:'ref-wave.json'},
  {u:'U22', title:'follow_line grasp + Ctrl+C halt + README L12-15 arm topic-pub + save_map typed (13 steps)', refs:'ref-wave.json'},
  {u:'U23', title:'save_map ctor + run: map_saver one-shot fires, map written, launch exits (18 steps)',   refs:'ref-driver.json'},
]

const META_SCHEMA = {
  type: 'object', required: ['file', 'count'],
  properties: {
    file: {type: 'string'}, count: {type: 'integer'}, bytes: {type: 'integer'},
    concerns: {type: 'string'},
  },
}
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

const PREAMBLE = `You are authoring content for the v2 "Complete Execution" section of a Bangla ROS 2 code-analysis app for folder "14. SLAM Gmapping".
BINDING, read in this order before writing anything:
1. ${KIT}/FACTS-14.md  (verified ground truth; if it conflicts with your reading, the SOURCE files win but note it)
2. ${KIT}/exec/exec-brief-14.md  (the style contract: field rules, canonical tables, dbg registry, rob SVG grammar, 23-unit sequence context, prohibitions)
3. ${KIT}/exec/shell-14.json  (rob0 = the panel chrome starting state; reuse its cards verbatim)
Source files (READ-ONLY — modifying them is a hard failure; 7 files, 984 lines):
${SRC}/README.md · ${SRC}/gmapping.launch.py · ${SRC}/slam_view.launch.py · ${SRC}/yahboom_keyboard.py · ${SRC}/camera_arm_kin.launch.py · ${SRC}/follow_line.py · ${SRC}/save_map.launch.py
You may WRITE exactly one file: ${KIT}/exec/out-UNIT.json — nothing else. Never touch the source folder.`

const AUTHOR = (x) => `${PREAMBLE.replace('UNIT', x.u)}

YOUR UNIT: ${x.u} — ${x.title}.
4. Your frozen step skeleton: ${KIT}/exec/unit-${x.u}.json — array of {file,ln,lns,kind}; ORDER, COUNT, and these four keys are immutable.
5. Calibration (folder-11 SHIPPED examples of exactly this genre — match their density and voice, NOT their folder-11 facts): ${KIT}/exec/${x.refs}

Task: author cap/op/dbg/fx/rob for EVERY skeleton step and write the result as a single-line-valid JSON object:
{"steps": [{"i": <0-based index>, "cap": "...", "op": "...", "dbg": [["k","v"],["k","v","ill"]], "fx": "...", "rob": "<svg-fragment-or-empty>"}, ...]}
to ${KIT}/exec/out-${x.u}.json (UTF-8, ensure_ascii false — write real Bangla characters, escaped only per JSON rules).
Every i from 0 to N-1 exactly once; N = skeleton length. Follow exec-brief-14.md exactly: canonical numbers verbatim (keyboard wave table, follow_line frame table F1-F4, Remove table R1/R2), dbg keys from the registry, rob full-redraw with the verbatim chrome, kind-appropriate voice, no emoji, no Unicode arrows, ASCII -> allowed, technical terms English, Bangla hyphen-suffix grammar.
Self-check before finishing: JSON parses, count matches skeleton, i-set exact, spot-check 5 steps' quoted code against the real source lines.
Return metadata only: {"file":"out-${x.u}.json","count":N,"bytes":<size>,"concerns":"..."}. Your structured output is the metadata, NOT the steps.`

const VERIFY = (x) => `${PREAMBLE.replace('UNIT', x.u)}

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

const FIX = (x, issuesJson) => `${PREAMBLE.replace('UNIT', x.u)}

You are the repair agent. ${KIT}/exec/out-${x.u}.json (unit ${x.u}, ${x.title}) failed verification. The verifier reported these issues:
${issuesJson}

Read FACTS-14.md, exec-brief-14.md, exec/unit-${x.u}.json (skeleton), the 7 source files, and the current out-${x.u}.json. Repair EXACTLY the flagged steps (and any directly-colliding neighbors) while leaving passing steps byte-identical. Keep the JSON single-object {"steps":[...]} shape, full Bangla content, all brief rules.
Overwrite ${KIT}/exec/out-${x.u}.json with the corrected full file. Re-run the author self-check (parse, count, i-set, quote fidelity on what you touched).
Return {"file":"out-${x.u}.json","fixed_count":<n>,"remaining_concerns":"..."}.`

phase('Author')
log('23 unit authors fanning out (skeletons frozen: 423 steps, 984 lines, all covered)')
const results = await pipeline(UNITS,
  async (x) => {
    let meta = await agent(AUTHOR(x), {label: `author:${x.u}`, phase: 'Author', schema: META_SCHEMA})
    if (!meta || !meta.file) {
      log(`${x.u} author died — one retry`)
      meta = await agent(AUTHOR(x) + '\n(RETRY — a previous attempt died before returning metadata. If out-' + x.u + '.json already exists on disk and is complete, verify it against the skeleton yourself instead of rewriting from scratch.)',
        {label: `author-retry:${x.u}`, phase: 'Author', schema: META_SCHEMA})
    }
    return {x, meta}
  },
  async (r, x) => {
    const meta = r && r.meta
    if (!meta || !meta.file) {
      return {u: x.u, ok: false, stage: 'author', steps: 0,
        verdict: {verdict: 'fail', issues: [{i: -1, field: 'file', problem: 'author returned no file after retry'}], summary: 'author stage died twice'}}
    }
    const v = await agent(VERIFY(x), {label: `verify:${x.u}`, phase: 'Verify', schema: VERDICT_SCHEMA})
    return {u: x.u, ok: true, stage: 'verified', steps: meta.count, concerns: meta.concerns || '', verdict: v}
  },
  async (r, x) => {
    if (!r) return null
    if (r.verdict && r.verdict.verdict === 'pass') {
      log(`${x.u} passed verification (${r.steps} steps)`)
      return {u: x.u, status: 'pass', steps: r.steps, fixed: false, issues: 0, summary: r.verdict.summary, concerns: r.concerns}
    }
    const issues = (r.verdict && r.verdict.issues) || []
    log(`${x.u} failed with ${issues.length} issues — repairing`)
    const f = await agent(FIX(x, JSON.stringify(issues)), {label: `fix:${x.u}`, phase: 'Fix', schema: FIX_SCHEMA})
    const fixed = !!(f && f.fixed_count !== undefined)
    return {u: x.u, status: fixed ? 'fixed' : 'fix-failed', steps: r.steps, fixed,
      issues: issues.length, fixedCount: fixed ? f.fixed_count : 0,
      summary: r.verdict ? r.verdict.summary : 'no verdict', concerns: r.concerns || '',
      remaining: f && f.remaining_concerns ? f.remaining_concerns : ''}
  }
)
const out = results.filter(Boolean)
log(`done: ${out.filter(r => r.status === 'pass' || r.status === 'fixed').length}/23 units clean`)
return out
