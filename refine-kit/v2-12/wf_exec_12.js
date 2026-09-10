export const meta = {
  name: 'exec-spec-12',
  description: 'Author + adversarially verify 180 exec-spec steps for folder 12 lidar tracking',
  phases: [
    { title: 'Author', detail: '10 unit authors write out-U*.json' },
    { title: 'Verify', detail: 'adversarial check per unit vs FACTS + brief' },
    { title: 'Fix', detail: 'repair flagged steps, rewrite file' },
  ],
}

const KIT = '/home/shariful/NeuroBotics/refine-kit/v2-12'
const SRC = '/home/shariful/NeuroBotics/12. lidar tracking'

const UNITS = [
  {u:'U1',  title:'README open + README mid (5 steps)',                      refs:'ref-open.json'},
  {u:'U2',  title:'driver constructor + driver run phase (22 steps)',        refs:'ref-driver.json'},
  {u:'U3',  title:'tracker import-pass a: L1-57 (21 steps)',                 refs:'ref-import.json'},
  {u:'U4',  title:'tracker import-pass b: L58-102 (21 steps)',               refs:'ref-import.json'},
  {u:'U5',  title:'tracker import-pass c: L103-146 (21 steps)',              refs:'ref-import.json'},
  {u:'U6',  title:'tracker main-pass: constructor truly runs (16 steps)',    refs:'ref-main.json'},
  {u:'U7',  title:'Joy gate + event wave A 0.90m@+12deg (22 steps)',         refs:'ref-wave.json'},
  {u:'U8',  title:'event waves B 0.70@+20 + C 0.58@0 snap (22 steps)',       refs:'ref-wave.json'},
  {u:'U9',  title:'wave D 0.70@-20 + E empty front + Joy override (20 steps)', refs:'ref-wave.json'},
  {u:'U10', title:'Ctrl+C + finally + exit_pro shutdown (10 steps)',         refs:'ref-wave.json'},
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

const PREAMBLE = `You are authoring content for the v2 "Complete Execution" section of a Bangla ROS 2 code-analysis app for folder "12. lidar tracking".
BINDING, read in this order before writing anything:
1. ${KIT}/FACTS-12.md  (verified ground truth; if it conflicts with your reading, the SOURCE files win but note it)
2. ${KIT}/exec/exec-brief-12.md  (the style contract: field rules, canonical wave table, dbg registry, rob SVG grammar, sequence context, prohibitions)
3. ${KIT}/exec/shell-12.json  (rob0 = the panel chrome starting state; reuse its cards verbatim)
Source files (READ-ONLY — modifying them is a hard failure):
${SRC}/README.md · ${SRC}/laser_driver.launch.py · ${SRC}/laser_Tracker.py
You may WRITE exactly one file: ${KIT}/exec/out-UNIT.json — nothing else. Never touch the source folder.`

const AUTHOR = (x) => `${PREAMBLE.replace('UNIT', x.u)}

YOUR UNIT: ${x.u} — ${x.title}.
4. Your frozen step skeleton: ${KIT}/exec/unit-${x.u}.json — array of {file,ln,lns,kind}; ORDER, COUNT, and these four keys are immutable.
5. Calibration (folder-11 SHIPPED examples of exactly this genre — match their density and voice, not their folder-11 facts): ${KIT}/exec/${x.refs}

Task: author cap/op/dbg/fx/rob for EVERY skeleton step and write the result as a single-line-valid JSON object:
{"steps": [{"i": <0-based index>, "cap": "...", "op": "...", "dbg": [["k","v"],["k","v","ill"]], "fx": "...", "rob": "<svg-fragment-or-empty>"}, ...]}
to ${KIT}/exec/out-${x.u}.json (UTF-8, ensure_ascii false — write real Bangla characters, escaped only per JSON rules).
Every i from 0 to N-1 exactly once; N = skeleton length. Follow exec-brief-12.md exactly: canonical wave numbers verbatim, dbg keys from the registry, rob full-redraw with the verbatim chrome, kind-appropriate voice, no emoji, no Unicode arrows, ASCII -> allowed, technical terms English.
Self-check before finishing: JSON parses, count matches skeleton, i-set exact, spot-check 5 steps' quoted code against the real source lines.
Return metadata only: {"file":"out-${x.u}.json","count":N,"bytes":<size>,"concerns":"..."}. Your structured output is the metadata, NOT the steps.`

const VERIFY = (x) => `${PREAMBLE.replace('UNIT', x.u)}

You are an ADVERSARIAL verifier. Another agent authored ${KIT}/exec/out-${x.u}.json for unit ${x.u} (${x.title}). Your job is to FAIL it if at all possible; pass only what survives.
Read: FACTS-12.md, exec-brief-12.md, exec/unit-${x.u}.json (skeleton), exec/${x.refs} (calibration), the three source files, then out-${x.u}.json.

Hard checks (any failure = verdict fail):
1. out-${x.u}.json parses as JSON; steps length == skeleton length; i-set == {0..N-1} exactly; file/ln/lns/kind were NOT altered (compare against skeleton).
2. Quote fidelity: for at least 8 steps, every code fragment inside <code> in cap (and any code echoed in fx) matches the REAL source lines at lns character-for-character (typos "improt", "commom" preserved).
3. Canonical table: wave steps' dbg numeric values match exec-brief-12.md's table EXACTLY (A: 0.90/+12.0/e-0.35/x+0.35/u0.333/z0.0 pub(0.35,0); B: 0.70/+20.0/+0.15/u0.556/z+0.333 pub(0.15,+0.333); C: 0.58->0.55/0.0/snap yes/x0.0 pub(0,0); D: 0.70/-20.0/z-0.333 pub(0.15,-0.333); E: no publish; Joy: zero Twist every scan; halt: shell brake chain). Every non-source-true number flagged "ill".
4. Fact safety: no invented vendor internals (SinglePID/Bool/common module), no claim that the launch file starts the tracker, no "fix" of source bugs, linear/angular dead-param story only where the brief schedules it, no emoji, no Unicode arrows anywhere, Bangla style rules (English technical terms, hyphen-suffix).
5. rob: non-empty ones start with the verbatim chrome rects/texts; all tags closed, attributes quoted, coordinates within 440x330, exactly 3 bottom Bangla lines at y 262/273/284, no ids re-declared, no scripts. Empty-string rob allowed (keeps prior panel).
6. Boundary continuity per exec-brief-12.md "Sequence context": the unit's first step picks up the stated incoming state; the last step leaves the stated outgoing state (dbg keys + panel).
7. kind voice: struct steps speak define/bind/not-run; exec steps show a state change NOW; event steps are message/framework-driven.
Report every defect as {i, field, problem, fix_hint} (i = step index, -1 for file-level). Also list up to 3 non-blocking polish suggestions inside summary. Write nothing to disk.
Return: verdict pass only if zero blocking issues.`

const FIX = (x, issuesJson) => `${PREAMBLE.replace('UNIT', x.u)}

You are the repair agent. ${KIT}/exec/out-${x.u}.json (unit ${x.u}, ${x.title}) failed verification. The verifier reported these issues:
${issuesJson}

Read FACTS-12.md, exec-brief-12.md, exec/unit-${x.u}.json (skeleton), the source files, and the current out-${x.u}.json. Repair EXACTLY the flagged steps (and any directly-colliding neighbors) while leaving passing steps byte-identical. Keep the JSON single-object {"steps":[...]} shape, full Bangla content, all brief rules.
Overwrite ${KIT}/exec/out-${x.u}.json with the corrected full file. Re-run the author self-check (parse, count, i-set, quote fidelity on what you touched).
Return {"file":"out-${x.u}.json","fixed_count":<n>,"remaining_concerns":"..."}.`

phase('Author')
log('10 unit authors fanning out (skeletons frozen: 180 steps total)')
const results = await pipeline(UNITS,
  (x) => agent(AUTHOR(x), {label: `author:${x.u}`, phase: 'Author', schema: META_SCHEMA}),
  async (meta, x) => {
    if (!meta || !meta.file) {
      return {u: x.u, ok: false, stage: 'author', steps: 0,
        verdict: {verdict: 'fail', issues: [{i: -1, field: 'file', problem: 'author returned no file'}], summary: 'author stage died'}}
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
log(`done: ${out.filter(r => r.status === 'pass' || r.status === 'fixed').length}/10 units clean`)
return out