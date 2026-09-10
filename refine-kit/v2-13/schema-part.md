# PART schema + house style — folder 12 (v1 layer)

One JSON object per Part, file `parts/part-NN.json` (NN = 2-digit part number).
UTF-8, `ensure_ascii=False` semantics — write raw Bangla, do NOT \\u-escape.

## Required shape

```json
{
  "n": 13,
  "id": "part-13",
  "fname": "laser_Tracker.py",
  "enTitle": "Dual PID — Approach & Centering",
  "lang": "python",
  "start": 97,
  "end": 114,
  "flags": [],
  "explain": [ { "a": 102, "b": 102, "text": "…" } ],
  "math": null,
  "robot": { "correct": "…", "incorrect": "…" },
  "animType": "pidDial"
}
```

- `lang`: "bash" for README, "python" for the two .py files.
- `flags`: [] (reserved; folder-11 shipped all empty).
- `math`: null when the part has no genuine mathematics; otherwise the object
  below. NEVER a "blocks" key — the renderer ignores unknown keys.
- `animType`: exactly the 7 routed names or null (runbookFlow, includeChain,
  subPubGraph, beamSweep, pidDial, cmdVelVectors, safetyHalt).

## explain items

- `{a, b, text}` — a..b is a REAL contiguous source line range inside
  [start..end] of THIS file. Every nonblank, non-pure-padding line of the part
  should be covered by some item; consecutive trivial lines may share one item.
- `text`: Bangla, technical terms English. Answer WHAT/HOW/WHY/WHEN/INPUT/
  OUTPUT/DEPENDENCY/CONSEQUENCE/FAILURE naturally in prose (no headings).
  Reference real line numbers as `L67` or `L98-102` (English L prefix).
  Inline code as `<code>…</code>` (HTML allowed: <b>, <i>, <code>; escape < as
  &lt; when literal).
- Quote source expressions VERBATIM inside <code> — never cleaned up.

## math object (all keys optional except at least one of levels/numeric/mapping)

```json
{
  "intro": "এক লাইনের Bangla ভূমিকা — এই Part-এর গণিত কী প্রশ্নের উত্তর দেয়।",
  "levels": [
    { "label": "Level 1 — Symbols & units", "latex": "\\[ e(t) = d_{target} - d(t) \\]", "text": "প্রতিটি symbol-এর অর্থ, unit, sign convention…" },
    { "label": "Level 2 — মৌলিক সম্পর্ক", "latex": "\\[ u = K_p\\,e \\]", "text": "…" }
  ],
  "numeric": [
    { "latex": "\\[ e = 0.55 - 0.90 = -0.35\\ \\mathrm{m} \\]", "text": "Wave A-এর সংখ্যা ধরে ধাপে ধাপে… (illustrative)" }
  ],
  "mapping": [
    { "code": "self.lin_pid.pid_compute(self.ResponseDist, minDist)", "math": "\\( u_{lin} = K_p (d^* - d) \\)", "text": "call order (target, current)…" }
  ],
  "failure": [
    "Kp ভুল হলে … (Bangla, concrete consequence)"
  ]
}
```

- Progression Level 1→6 when justified (symbols → basic → algebra → geometry →
  general → advanced). Never fake depth; RAD2DEG needs Level 1-2 only, the PID
  part earns Levels 1-6.
- `latex` values are LaTeX for MathJax 3: display `\\[ … \\]`, inline `\\( … \\)`.
  Backslashes arrive in JSON as `\\[`.
- numeric entries MUST compute with the canonical illustrative scenario values
  from FACTS-12 §3 and say "illustrative".
- failure list: concrete wrong-value consequences (§2/§3 quirks are the source
  material).

## robot object

- `correct`: what the physical robot does when this part runs as written
  (mention motors/wheels/lidar/console; use illustrative scenario outcomes).
- `incorrect`: the concrete misbehavior when values/assumptions are wrong
  (unclamped linear.x, inf passthrough, deadzone too wide, sign flipped …).
  Both Bangla, 2-5 sentences, technically specific — never generic filler.

## House style (from shipped folders)

- Prose register: teacher-to-engineer; ছোট ছোট বাক্য; hyphen-suffix pattern
  (`PID-টি`, `beam-এর`, `Twist-এ`)। English technical terms NEVER transliterated
  (write `parameter`, not প্যারামিটার; `subscription`, not সাবস্ক্রিপশন)।
  Bangla numerals fine in prose (৩টা command), ASCII digits inside code/math.
- Cross-folder context allowed where TRUE: folder 09 (echo values), folder 10
  (merger + filter chain), folder 11 (same driver byte-identical; avoidance
  contrast). Folder 11's node was laser_Avoidance (avoid); THIS app's node is
  laser_Tracker (follow) — any contrast sentence must keep that straight.
- No emoji, no arrow chars in any string except plain `->` inside fx-style
  strips (parts rarely need arrows at all; prefer prose or `-&gt;`).
- Do not repeat the whole source line in `text` — quote only the key fragment.
- Each part: 3-8 explain items typical (README part: 3; PID part: 6-8).

## Validation the verifier will run on your file

- JSON parses; keys exactly {n,id,fname,enTitle,lang,start,end,flags,explain,
  math,robot,animType}; id == "part-NN" matching n; fname in the 3 files;
  1 <= start <= end <= file length; explain ranges inside [start,end] and
  covering; math has no "blocks" key; no emoji; balanced <code> tags; LaTeX
  delimiters balanced; animType ∈ the 7 names ∪ {null} and matches the router
  plan for this part.
