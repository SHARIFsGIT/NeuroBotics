#!/usr/bin/env python3
"""Assemble v1_base_13.html (v1 layer, no exec-spec yet) for folder 13.

Inputs (all frozen): t1_base_head.html + t2_body.html + t3_main_13.js,
filedata-13.json, parts/part-01..15.json, rep/*.js (8 anim bodies).
t3 edits: L3 header, L8 FILEDATA, L9 PARTS, L316-317 hero, L330 footer,
L587-613 pre-ANIMS banner, 7 anim region swaps + alarm13 insertion.
Every boundary is sentinel-asserted; the script refuses to build on drift.
"""
import json, subprocess, sys
from pathlib import Path

KIT = Path("/home/shariful/NeuroBotics/refine-kit/v2-13")

# ---------- inputs ----------
fd = json.load(open(KIT / "filedata-13.json", encoding="utf-8"))
assert list(fd) == ["README.md", "laser_driver.launch.py", "laser_Warning.py"], list(fd)
assert [len(fd[k]) for k in fd] == [5, 42, 145], [len(fd[k]) for k in fd]

parts = []
for n in range(1, 16):
    p = KIT / f"parts/part-{n:02d}.json"
    if not p.exists():
        sys.exit(f"MISSING {p}")
    parts.append(json.load(open(p, encoding="utf-8")))
assert [p["n"] for p in parts] == list(range(1, 16)), [p["n"] for p in parts]

def rep(name):
    p = KIT / "rep" / name
    if not p.exists():
        sys.exit(f"MISSING {p}")
    lines = p.read_text(encoding="utf-8").rstrip("\n").split("\n")
    assert lines[0].startswith("/* ---------- "), (name, lines[0])
    assert lines[-1] == "};", (name, lines[-1])
    return lines

RUNBOOK, INCLUDE, SUBPUB = rep("runbook13.js"), rep("include13.js"), rep("subpub13.js")
BEAMSWEEP, ALARM = rep("beamsweep13.js"), rep("alarm13.js")
PIDDIAL, CMDVEL, SAFETY = rep("piddial13.js"), rep("cmdvel13.js"), rep("safety13.js")
# no duplicated helper declarations across rep files (cmdvel owns cvPt etc.)
decls = {}
for nm, ls in (("runbook", RUNBOOK), ("include", INCLUDE), ("subpub", SUBPUB),
               ("beam", BEAMSWEEP), ("alarm", ALARM), ("pid", PIDDIAL),
               ("cmd", CMDVEL), ("safety", SAFETY)):
    for ln in ls:
        for key in ("function cvPt", "function cvN", "function cvWedge",
                    "function cvArcArrow", "function rfDots"):
            if key + "(" in ln or ln.startswith(key):
                decls.setdefault(key, []).append(nm)
dup = {k: v for k, v in decls.items() if len(v) > 1}
assert not dup, f"duplicate helpers: {dup}"

t3 = (KIT / "t3_main_13.js").read_text(encoding="utf-8").split("\n")
if t3 and t3[-1] == "":
    t3.pop()
assert len(t3) == 1761, len(t3)

# ---------- scattered identity edits (1-based -> index-1) ----------
def idx(n):  # 1-based line number
    return n - 1

assert "12. lidar tracking — Line-by-Line Code Analysis" in t3[idx(3)], t3[idx(3)]
t3[idx(3)] = "   13. lidar guard — Line-by-Line Code Analysis"

assert t3[idx(8)].startswith("const FILEDATA = ") and t3[idx(8)].endswith("};")
t3[idx(8)] = "const FILEDATA = " + json.dumps(fd, ensure_ascii=False, separators=(",", ":")) + ";"

assert t3[idx(9)].startswith("const PARTS = ") and t3[idx(9)].endswith("];")
t3[idx(9)] = "const PARTS = " + json.dumps(parts, ensure_ascii=False, separators=(",", ":")) + ";"

assert t3[idx(316)].startswith("    '<h1>12. lidar tracking"), t3[idx(316)][:60]
t3[idx(316)] = (
    "    '<h1>13. lidar guard <span class=\"path\">— fused 360 scan-এর সামনের cone-এর সবচেয়ে কাছের "
    "object-এর দিকে ঘুরে 0.55 m Danger Zone-এ ঢুকলেই /beep-এ সাইরেন — নিজ জায়গায় দাঁড়িয়ে "
    "spin-only পাহারা</span></h1>' +"
)
assert t3[idx(317)].startswith("    '<div class=\"intro-desc bn\">"), t3[idx(317)][:60]
t3[idx(317)] = (
    "    '<div class=\"intro-desc bn\">এই application-টি <code>13. lidar guard</code> folder-এর তিনটি "
    "source file — <code>README.md</code> (তিন command-এর runbook), <code>laser_driver.launch.py</code> "
    "(folder 10-এর merger আর filter launch file দুটিকে এক সঙ্গে চালানোর orchestrator) আর "
    "<code>laser_Warning.py</code> (fused scan-এর সামনের cone থেকে সবচেয়ে কাছের object ধরে single "
    "PID-এ <code>/cmd_vel</code>-এ spin কমান্ড আর <code>/beep</code>-এ Danger Zone সাইরেন দেওয়া guard "
    "node) — কে কেন্দ্র করে তৈরি। ভেতরে আছে <code>IncludeLaunchDescription</code> দিয়ে chained launch, "
    "subscription-publisher graph, declare/get parameter জোড়া, প্রতিটি beam-এর angle math ও front-cone "
    "inequality, alarm threshold-এর level-signal আচরণ ও latch, single PID-এর target-current হিসাব, আর "
    "turn deadzone- damping-এর ধাপে ধাপে বিশ্লেষণ। প্রতিটি Part-এ আছে original code card, line-by-line "
    "Bangla explanation, Math derivation, Real Robot behavior এবং interactive animation।</div>' +"
)

assert "12. lidar tracking · line-by-line analysis" in t3[idx(330)], t3[idx(330)][:60]
t3[idx(330)] = (
    "    '13. lidar guard · line-by-line analysis · source preserved verbatim from "
    "/home/shariful/NeuroBotics/13. lidar guard';"
)

# ---------- banner + anim region splice ----------
S = {  # sentinel assertions: (line, expected)
    587: "/* ================= folder-12 anims",
    613: "first await. */",
    616: "/* ---------- runbookFlow ---------- */",
    740: "};",
    742: "/* ---------- includeChain ---------- */",
    872: "};",
    874: "/* ---------- subPubGraph ---------- */",
    1026: "};",
    1028: "/* ---------- beamSweep ---------- */",
    1215: "};",
    1216: "/* ---------- pidDial ---------- */",
    1359: "};",
    1360: "/* ---------- cmdVelVectors ---------- */",
    1570: "};",
    1571: "/* ---------- safetyHalt ---------- */",
    1730: "};",
}
for n, expect in S.items():
    got = t3[idx(n)]
    assert got == expect or got.startswith(expect) or got.rstrip().endswith(expect.rstrip()), (n, got[:70])

BANNER = """/* ================= folder-13 anims (v1 layer, 8 total) ================
   runbookFlow (part 1) · includeChain (part 3) · subPubGraph (part 6)
   beamSweep (part 10) · alarmBuzzer (part 12) · pidDial (part 13)
   cmdVelVectors (part 14) · safetyHalt (part 15)
   Facts from the three source files (README sha 7de1ece640db /
   driver dadf5ff3f9b1 / warning b1cf2d67a4d5) + FACTS-13: README =
   3-command runbook (L1/L3/L5, L2/L4 blank); driver = constructor with
   two EAGER os.path.join paths to ira_laser_tools merge_multi.launch.py
   + yahboom_laser_filter laser_filter_node.launch.py (folder 10 chain,
   byte-identical driver to folders 11+12) and a 2-include return — the
   launch NEVER starts the warning node (README L5 ros2 run does);
   guard node laser_Warnning_a1 (typo as-is) subscribes /scan (fused
   360) + /JoyState, publishes /cmd_vel Twist AND /beep UInt16 (1 =
   BEEP, default UInt16() = 0 = silence); parameters linear 0.5 ·
   angular 1.0 · LaserAngle 45.0 deg · ResponseDist 0.55 m — linear/
   angular declared then NEVER read (no clamp anywhere); ONE ang
   SinglePID(3.0, 0.0, 5.0) L48, no linear PID, no snap (vendor
   internals not in folder; all pid numbers Kp-only illustrative);
   front cone |angle| < 45 strict = 89 beams, ranges[i] != 0.0 passes
   inf; empty cone L73 = silent early return, NO /beep refresh — the
   buzzer LATCHES its last value; Joy gate L81-83 zero-Twist brake,
   return BEFORE the alarm; alarm L89 minDist <= 0.55 and != 0.0;
   /72 magic number; sign branch L106-110; turn deadzone |u| < 0.5
   (~12 deg Kp-only); x0.5 damping (ceiling 0.9375 rad/s); linear.x
   NEVER set — spin-only, no forward arrow ever; print at scan rate;
   publish per scan, motors keep last command; exit_pro() shell-brakes
   /cmd_vel only, /beep untouched. No __main__ guard, main() never
   called (setup.py entry, inferred).
   Stage = setStage 900x460 grammar. No emoji; arrow chars NEVER in
   stage <text> — only in the caption/formula strips below the stage
   (entities or words elsewhere). Unique id prefix per anim: rf- ic-
   sp- bs- ab- pd- cv- sh-. Static backbone visible at setStage, first
   caption + formula set before the first await. */""".split("\n")

new = (t3[:idx(587)]
       + BANNER                       # replaces L587-613
       + t3[idx(614):idx(616)]        # blanks L614-615
       + RUNBOOK                      # replaces L616-740
       + t3[idx(741):idx(742)]        # blank L741
       + INCLUDE                      # replaces L742-872
       + t3[idx(873):idx(874)]        # blank L873
       + SUBPUB                       # replaces L874-1026
       + t3[idx(1027):idx(1028)]      # blank L1027
       + BEAMSWEEP                    # replaces L1028-1215
       + [""]                         # separator
       + ALARM                        # NEW — part 12 alarmBuzzer
       + [""]                         # separator
       + PIDDIAL                      # replaces L1216-1359
       + CMDVEL                       # replaces L1360-1570
       + SAFETY                       # replaces L1571-1730
       + t3[idx(1731):])              # L1731-end

joined = "\n".join(new)
(KIT / "t3_final_13.js").write_text(joined + "\n", encoding="utf-8")

# ---------- integrity ----------
ANIM_NAMES = ["runbookFlow", "includeChain", "subPubGraph", "beamSweep",
              "alarmBuzzer", "pidDial", "cmdVelVectors", "safetyHalt"]
for a in ANIM_NAMES:
    assert f"ANIMS.{a} = async function" in joined, f"missing ANIMS.{a}"
assert joined.count("ANIMS.") == len(ANIM_NAMES), joined.count("ANIMS.")
assert "12. lidar tracking" not in joined, "stale folder-12 title"
assert "folder-12 anim" not in joined, "stale folder-12 anim header"
assert "d414af8d12da" not in joined, "stale folder-12 tracker sha"
for bad in ("3433bd6ce68a",):
    assert bad not in joined, f"stale sha {bad}"
tracker_hits = [i + 1 for i, ln in enumerate(new)
                if "laser_Tracker" in ln or "folder-12" in ln.lower()]

r = subprocess.run(["node", "--check", str(KIT / "t3_final_13.js")],
                   capture_output=True, text=True)
if r.returncode != 0:
    sys.exit("node --check FAILED:\n" + r.stderr[:2000])

# ---------- html assembly ----------
t1 = (KIT / "t1_base_head.html").read_text(encoding="utf-8")
old_title = "<title>11. lidar obstacle avoidance</title>"
assert old_title in t1
t1 = t1.replace(old_title, "<title>13. lidar guard</title>")
t2 = (KIT / "t2_body.html").read_text(encoding="utf-8")
if not t2.endswith("\n"):
    t2 += "\n"
html = t1 + t2 + "<script>\n" + joined + "\n</script>\n</body>\n</html>\n"
out = KIT / "v1_base_13.html"
out.write_text(html, encoding="utf-8")

print(f"t3_final_13.js: {len(new)} lines, {(KIT / 't3_final_13.js').stat().st_size} bytes, node --check OK")
print(f"ANIMS: 8 registered; alarm13 inserted after beamSweep")
print(f"cross-folder refs (laser_Tracker / folder-12 mentions) at lines: {tracker_hits[:12]}"
      f"{' ...' if len(tracker_hits) > 12 else ''} — verify each is comparative, not identity")
print(f"v1_base_13.html: {out.stat().st_size} bytes, {html.count(chr(10))} lines")
