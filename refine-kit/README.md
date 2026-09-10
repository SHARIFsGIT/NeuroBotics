# Refinement kit — SURGICAL UI-UX layer for the four app HTMLs

The four root HTMLs (`01. arm calibration.html` … `04. angular velocity calibration.html`)
each carry an APPENDED refinement layer implementing the master prompt
("SURGICAL UI-UX & INTERACTIVE ANIMATION REFINEMENT"):

- `<style id="refine-style">` inserted before `</head>`
- `<script id="refine-script">` inserted before `</body>` (engine + per-app EXEC spec)

Everything else — original scripts, styles, FILEDATA/PARTS content — is byte-identical
(sha256 of each original main script verified unchanged after patching).

## Files

| file | role |
|---|---|
| `refine_style.css` | layer CSS: z-index token scale, halo-stroked SVG labels, icon control buttons, `exec-*` section styles, responsive breakpoints |
| `refine_engine.js` | layer JS: SVG icon set, tooltips, `retrofitControls()` over host anim bars, hero-title fix, `buildExec()` (reads spec injected at the `/*__EXEC_SPEC__*/ null` marker) |
| `exec-spec-0N.json` | per-app "Complete Execution" spec: 30 steps `{ln, cap, dbg, rob}`, `rob0`, `final*`, `defs` |
| `filedata-0N.json` | per-app source lines extracted from the HTML's own FILEDATA (read-only copy) |
| `patch_refine.py` | applies the layer to the root HTMLs (idempotent, hash-checked pre+post) |
| `validate_spec.py` | mechanical spec QA: line realism, SVG balance, coords, fonts, exact mono text widths, text-text/box-edge collisions |
| `smoke_refine.py` | post-patch harness: DOM assertions + geometry probe + screenshots |
| `make_preview.py` | /tmp-only preview builder (never touches root) |
| `apply_fixups.py` | one-time spec fixups (font 8.5→9) — kept for the record |

## Notes for reuse

- The root HTMLs are untracked in git; pristine restore is by stripping the two
  layer blocks (regex), not `git checkout`.
- Play-button counting: `title="Play (1× speed)"` appears once per retrofitted
  animation bar + once for the exec section ⇒ count = anims + 1 (16 / 11 / 9 / 9).
- QA-copy probe serializes dataset attrs lowercased in `--dump-dom`
  (`data-page-overflow`, not `data-pageOverflow`).
- Debug idle state deliberately has no `dbg0` in specs — the panel shows its
  Bangla idle placeholder until Play (avoids fabricating runtime values).
