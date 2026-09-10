#!/usr/bin/env python3
"""Assemble the final folder-12 deliverable:
  v1_base_12.html
    + <style id="refine-style"> (kit refine_style.css)  before </head>
    + <script id="refine-script"> prefix11 + EXEC_SPEC_12 + engine11  before </body>
  -> "12. lidar tracking/12. lidar tracking.html"
Mirrors folder-11's shipped seams byte-for-byte (style seam '</style>\\n\\n\\n<style…',
script seam '</script>\\n<script id="refine-script">')."""
import json, sys
from pathlib import Path

KIT = Path("/home/shariful/NeuroBotics/refine-kit/v2-12")
OUT = Path("/home/shariful/NeuroBotics/12. lidar tracking/12. lidar tracking.html")

v1 = (KIT/"v1_base_12.html").read_text(encoding="utf-8")
css = (KIT/"refine_style.css").read_text(encoding="utf-8")
t4 = (KIT/"t4_engine_11.js").read_text(encoding="utf-8")

# --- split folder-11's refine body into prefix / spec-line / engine ---
i = t4.index("var EXEC_SPEC = ")
line_end = t4.index("\n", i)
prefix, engine = t4[:i], t4[line_end+1:]
assert "obstacle" not in prefix and "obstacle" not in engine, "engine not folder-agnostic!"

# --- folder-12 spec, minified single line (matches folder-11 embedding) ---
spec = json.load(open(KIT/"exec/exec-spec-12.json", encoding="utf-8"))
spec_line = "var EXEC_SPEC = " + json.dumps(spec, ensure_ascii=False, separators=(",", ":")) + ";"
assert "\n" not in spec_line

# --- seams (match folder-11 shipped bytes: '</style>\\n\\n\\n<style id="refine-style">') ---
style_block = '\n\n<style id="refine-style">\n' + css + '\n</style>\n'
assert v1.count("</head>") == 1 and v1.count("</body>") == 1
v2 = v1.replace("</head>", style_block + "</head>", 1)

script_block = '<script id="refine-script">\n' + prefix + spec_line + "\n" + engine + "</script>\n"
v2 = v2.replace("</body>", script_block + "</body>", 1)

OUT.write_text(v2, encoding="utf-8")
print(f"written {OUT} : {len(v2):,} bytes")
print(f"  style block {len(style_block):,} B | script block {len(script_block):,} B "
      f"(prefix {len(prefix):,} + spec {len(spec_line):,} + engine {len(engine):,})")
# quick landmarks
for lm in ('id="refine-style"', 'id="refine-script"', '"app":"12. lidar tracking"',
           '12. lidar tracking', 'laser_Tracker.py', 'finalRob'):
    print(f"  landmark {lm!r}: {v2.count(lm)}x")
stale = [s for s in ("laser_Avoidance", "obstacle avoidance") if s in v2]
print("  stale folder-11 strings:", stale or "none")
