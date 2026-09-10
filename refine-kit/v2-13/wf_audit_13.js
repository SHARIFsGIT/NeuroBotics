export const meta = {
  name: 'audit-13-deliverable',
  description: 'Adversarial truth-audit of the assembled folder-13 deliverable vs its read-only sources',
  phases: [
    { title: 'Audit', detail: '8 dimension auditors over the built HTML + spec + parts' },
    { title: 'Confirm', detail: 'refute-panel per finding; only confirmed defects survive' },
  ],
}

const KIT = '/home/shariful/NeuroBotics/refine-kit/v2-13'
const DELIV = '/home/shariful/NeuroBotics/13. lidar guard/13. lidar guard.html'
const SRC = '/home/shariful/NeuroBotics/13. lidar guard'

const COMMON = `You are auditing the FINAL assembled deliverable ${DELIV} for folder "13. lidar guard" (a Bangla ROS 2 line-by-line code-analysis app, two layers: v1 Parts + v2 Complete Execution).
Ground truth, read first:
1. ${KIT}/FACTS-13.md
2. the READ-ONLY sources: ${SRC}/README.md (5 lines, sha 7de1ece640db), ${SRC}/laser_driver.launch.py (42 lines, dadf5ff3f9b1), ${SRC}/laser_Warning.py (145 lines, b1cf2d67a4d5)
The deliverable is large (~1.3 MB). Extract the layer you need from the built HTML: the v1 PARTS const and the v2 "var EXEC_SPEC = ..." line are both single minified lines inside <script> tags — parse them with python3 (json.loads after stripping the "const PARTS = "/"var EXEC_SPEC = " prefix and trailing ";") or read the pre-assembly kit files which are byte-identical to what was embedded:
- v1 parts: ${KIT}/parts/part-01..15.json
- v2 spec: ${KIT}/exec/exec-spec-13.json
Write NOTHING to disk. Report findings only.`

const DIMENSIONS = [
  {key: 'exec-truth-1', prompt: `${COMMON}
YOUR DIMENSION: v2 exec steps, spine indices 0..61 (README runbook, driver constructor/run, warning import-pass a). For EVERY step: quoted code in cap/fx must be a character-exact substring of the real source lines at lns (typos "improt"/"commom"/"Warnning", L99 trailing TAB, L129 trailing space preserved as-is); every non-source-true number flagged "ill"; no launch-starts-warning-node claim; spin-only (linear.x never set). Report each defect as a finding.`},
  {key: 'exec-truth-2', prompt: `${COMMON}
YOUR DIMENSION: v2 exec steps, spine indices 62..122 (warning import-pass b/c, main pass constructor). Same hard checks: quote fidelity character-exact, ill flags, no invented vendor internals (SinglePID/Bool/common), no bug "fixes", dead-param story (linear/angular declared L35-38, never read). Report each defect as a finding.`},
  {key: 'exec-truth-3', prompt: `${COMMON}
YOUR DIMENSION: v2 exec steps, spine indices 123..183 (gate + waves A-F + Joy override + Ctrl+C shutdown). Canonical table from exec-brief-13.md must hold verbatim: A 0.90@+14.0 e 0.194 u 0.583 z +0.292 pub(0.0,+0.292) beep 0; B 0.70@+20.0 u 0.833 z +0.417 beep 0; C 0.48@0.0 BEEP still (0.0,0.0); D 0.50@-20.0 BEEP z -0.417; E empty cone no publish + /beep LATCHES 1; F 0.80@+8.0 deadzone -> (0.0,0.0) beep 0; Joy zero-Twist every scan return before alarm; halt brakes /cmd_vel only, /beep untouched. Check each wave step's dbg rows against this table. Report each mismatch as a finding.`},
  {key: 'v1-parts-1', prompt: `${COMMON}
YOUR DIMENSION: v1 parts 1-8 (kit files part-01..08.json). Verify every claim that names a source fact: line numbers cited match the real files, code quotes are character-exact substrings, numbers (0.55 m, 45.0 deg, /72, Kp 3.0, SinglePID(3.0,0.0,5.0), 89-beam cone illustrative, 0.9375 published ceiling) consistent with FACTS-13. Math sections: e=|a|/72, u=3e, deadzone |u|<0.5 (~12 deg), damping x0.5. Report each defect as a finding.`},
  {key: 'v1-parts-2', prompt: `${COMMON}
YOUR DIMENSION: v1 parts 9-15 (kit files part-09..15.json). Same checks as parts 1-8 plus: Real Robot correct/incorrect blocks must not claim forward driving (spin-only), the ~2x-declared-angular claim must NOT appear (L118 x0.5 damping caps published at 0.9375 < declared 1.0), buzzer described as LEVEL signal refreshed per scan and latched by L73/L83 early returns. Report each defect as a finding.`},
  {key: 'cross-layer', prompt: `${COMMON}
YOUR DIMENSION: cross-layer consistency. The v1 Parts (parts/part-*.json) and the v2 exec spec (exec/exec-spec-13.json) must never contradict: same canonical numbers (0.55, 45.0, /72, 3.0, 5.0, 0.5 deadzone, x0.5 damping, 0.9375 ceiling, 89 beams ill), same story (launch never starts warning node, README L5 does; linear/angular dead params; spin-only; latch semantics; node name typo laser_Warnning_a1). Also check the hero/intro/footer text embedded in the built HTML matches folder-13 identity. Report each contradiction as a finding.`},
  {key: 'stale-identity', prompt: `${COMMON}
YOUR DIMENSION: stale-identity sweep over the BUILT HTML itself (read ${DELIV} in chunks with python3). Any folder-11/12 identity leakage: "obstacle avoidance", "laser_Avoidance", "laser_Tracker" (allowed ONLY as small explicit comparative cross-references, e.g. "folder 12-এর tracker-এ ছিল snap, এখানে নেই" — flag anything that reads as identity, not comparison), "11. lidar"/"12. lidar" as this app's title/identity, tracker sha d414af8d12da, folder-11 sha 3433bd6ce68a, "laser_Tracking". Also verify title tag = "13. lidar guard", hero h1 names folder 13, footer names folder 13. Report each finding.`},
  {key: 'bangla-style', prompt: `${COMMON}
YOUR DIMENSION: Bangla style sweep across both kit layers (parts/*.json + exec/exec-spec-13.json). Rules: English technical terms stay Latin with hyphen-suffix attachment (PID-টি, scan-এ); NO emoji anywhere; NO Unicode arrows in exec spec (ASCII -> allowed) and none in v1 stage <text>; no Bangla numerals inside dbg values or SVG coordinates; tolerated transliterations are ONLY টেস্ট/রেজিস্টার/ডিগ্রি/স্কিপ/রিসেট — flag any OTHER English technical term rendered in Bangla script (like ল্যাচ, সিগনেচার, ডেডজোন, কলব্যাক). Report each violation with file+location.`},
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
log('8 dimension auditors over the assembled deliverable')
const results = await pipeline(DIMENSIONS,
  (d) => agent(d.prompt, {label: `audit:${d.key}`, phase: 'Audit', schema: FINDINGS_SCHEMA}),
  async (res, d) => {
    if (!res || !res.findings || !res.findings.length) return {dim: d.key, confirmed: [], checked: res ? res.checked : 'agent died'}
    log(`${d.key}: ${res.findings.length} raw findings -> refute panel`)
    const judged = await parallel(res.findings.map(f => () =>
      parallel([1, 2, 3].map(n => () =>
        agent(`${COMMON}
A fellow auditor reported this defect in the folder-13 deliverable:
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