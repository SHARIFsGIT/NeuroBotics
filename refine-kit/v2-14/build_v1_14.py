#!/usr/bin/env python3
"""Assemble v1_base_14.html (v1 layer, no exec-spec yet) for folder 14.

Inputs (all frozen): t1_base_head.html + t2_body.html + t3_main_14.js,
filedata-14.json, parts/part-01..15.json (15 parts — the wf_parts plan),
rep/*.js (8 anim bodies).
t3 edits: L3 header, L8 FILEDATA, L9 PARTS, L316-317 hero, L330 footer,
L587-613 pre-ANIMS banner, 7 anim region swaps + teleop14 insertion.
Every boundary is sentinel-asserted; the script refuses to build on drift.
"""
import json, subprocess, sys
from pathlib import Path

KIT = Path("/home/shariful/NeuroBotics/refine-kit/v2-14")

# ---------- inputs ----------
fd = json.load(open(KIT / "filedata-14.json", encoding="utf-8"))
assert list(fd) == ["README.md", "gmapping.launch.py", "slam_view.launch.py",
                    "yahboom_keyboard.py", "camera_arm_kin.launch.py",
                    "follow_line.py", "save_map.launch.py"], list(fd)
assert [len(fd[k]) for k in fd] == [15, 94, 59, 242, 40, 485, 49], [len(fd[k]) for k in fd]

parts = []
for n in range(1, 16):
    p = KIT / f"parts/part-{n:02d}.json"
    if not p.exists():
        sys.exit(f"MISSING {p}")
    parts.append(json.load(open(p, encoding="utf-8")))
assert [p["n"] for p in parts] == list(range(1, 16)), [p["n"] for p in parts]

def rep(name):
    """Slice one anim body from its marker line to the closing '};'."""
    p = KIT / "rep" / name
    if not p.exists():
        sys.exit(f"MISSING {p}")
    lines = p.read_text(encoding="utf-8").rstrip("\n").split("\n")
    start = next((i for i, ln in enumerate(lines) if ln.startswith("/* ---------- ")), None)
    assert start is not None, (name, "no marker line")
    assert lines[-1] == "};", (name, lines[-1])
    return lines[start:]

RUNBOOK, CHAIN, EKF = rep("runbook14.js"), rep("chain14.js"), rep("ekf14.js")
RVIZ, TELEOP = rep("rviz14.js"), rep("teleop14.js")
STEER, STATES, SAVEMAP = rep("steer14.js"), rep("states14.js"), rep("savemap14.js")
# no local helper declarations inside anim bodies (only ANIMS.x = async function)
for nm, ls in (("runbook", RUNBOOK), ("chain", CHAIN), ("ekf", EKF), ("rviz", RVIZ),
               ("teleop", TELEOP), ("steer", STEER), ("states", STATES), ("savemap", SAVEMAP)):
    for ln in ls:
        assert "function cv" not in ln and "function rf" not in ln, (nm, ln[:60])

t3 = (KIT / "t3_main_14.js").read_text(encoding="utf-8").split("\n")
if t3 and t3[-1] == "":
    t3.pop()
assert len(t3) == 1761, len(t3)

# ---------- scattered identity edits (1-based -> index-1) ----------
def idx(n):  # 1-based line number
    return n - 1

assert "12. lidar tracking — Line-by-Line Code Analysis" in t3[idx(3)], t3[idx(3)]
t3[idx(3)] = "   14. SLAM Gmapping — Line-by-Line Code Analysis"

assert t3[idx(8)].startswith("const FILEDATA = ") and t3[idx(8)].endswith("};")
t3[idx(8)] = "const FILEDATA = " + json.dumps(fd, ensure_ascii=False, separators=(",", ":")) + ";"

assert t3[idx(9)].startswith("const PARTS = ") and t3[idx(9)].endswith("];")
t3[idx(9)] = "const PARTS = " + json.dumps(parts, ensure_ascii=False, separators=(",", ":")) + ";"

assert t3[idx(316)].startswith("    '<h1>12. lidar tracking"), t3[idx(316)][:60]
t3[idx(316)] = (
    "    '<h1>14. SLAM Gmapping <span class=\"path\">— দুই lidar-এর মিশ্রিনি scan আর IMU-মিশ্রিত odom থেকে "
    "gmapping দিয়ে লাইভ মানচিত্র, RViz-চোখে তার ফুটে ওঠা, keyboard-হাতে চালনা — শেষে রেখা ধরে এগিয়ে "
    "AprilTag-বাধা সরিয়ে মানচিত্রটাকেই ডিস্কে লিখে রাখা</span></h1>' +"
)
assert t3[idx(317)].startswith("    '<div class=\"intro-desc bn\">"), t3[idx(317)][:60]
t3[idx(317)] = (
    "    '<div class=\"intro-desc bn\">এই application-টি <code>14. SLAM Gmapping</code> folder-এর সাতটি "
    "source file — <code>README.md</code> (আটটি command-এর runbook: bringup থেকে save_map পর্যন্ত পুরো "
    "জীবনচক্র), <code>gmapping.launch.py</code> (merger, filter, imu, ekf আর gmapping — পাঁচ program-এর "
    "SLAM stack এক launch-এ সাজানোর orchestrator), <code>slam_view.launch.py</code> (RViz viewer), "
    "<code>yahboom_keyboard.py</code> (১২-key mecanum teleop আর arm-নিয়ন্ত্রণ), "
    "<code>camera_arm_kin.launch.py</code> (camera driver + arm kinematics service), "
    "<code>follow_line.py</code> (HSV রেখা-শনাক্তকরণ, PID steering, AprilTag বাধা-অপসারণ আর সহায়ক "
    "ফাইল), আর <code>save_map.launch.py</code> (map_saver_cli দিয়ে মানচিত্র ডিস্কে লেখা) — কে কেন্দ্র "
    "করে তৈরি। ভেতরে আছে constructor-বনাম-run দুই দফার launch জীবন, eager path join আর অব্যবহৃত "
    "import-এর সত্যি-স্বীকারোক্তি, <code>/imu</code> remap-সেতু, publish-subscribe graph, tuple-to-Twist "
    "গুণিতক ম্যাপিং, arm-এর clamp-সীমা, PID-এর e=(point_x-320)/16 হিসাব ও deadzone, স্টেট-মেশিনের "
    "init-identify-tracking-Remove পরিক্রমা, দুইবার-প্রকাশিত joint5, আর occupancy grid-এর 0.196/0.65 "
    "থ্রেশহোল্ড-গণিতের ধাপে ধাপে বিশ্লেষণ। প্রতিটি Part-এ আছে original code card, line-by-line Bangla "
    "explanation, Math derivation, Real Robot behavior এবং interactive animation।</div>' +"
)

assert "12. lidar tracking · line-by-line analysis" in t3[idx(330)], t3[idx(330)][:60]
t3[idx(330)] = (
    "    '14. SLAM Gmapping · line-by-line analysis · source preserved verbatim from "
    "/home/shariful/NeuroBotics/14. SLAM Gmapping';"
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

BANNER = """/* ================= folder-14 anims (v1 layer, 8 total) ================
   runbook14 (part 1) · chain14 (part 2) · ekf14 (part 3) · rviz14 (part 4)
   teleop14 (part 5) · steer14 (part 12) · states14 (part 13) · savemap14 (part 15)
   Facts from the seven source files (README 1246ab7881c6 / gmapping
   e9d107d1fa6d / slam_view ff4b1234ffdd / keyboard 536b2850bd2a /
   camera_arm 6b2b105f277e / follow_line 88a485372c54 / save_map
   3601e4887d57) + FACTS-14: README = 8-command runbook (L1/3/5/7/9/11/
   13/15 odd lines; evens blank). gmapping.launch.py ctor: dup Node
   import L2+L9, unused LaunchConfiguration/Declare L3-4, three dead
   lists L17-19, FOUR eager joins (ira_laser_tools merge_multi,
   yahboom_laser_filter laser_filter_node, robot_localization ekf,
   slam_gmapping gmapping); run phase = 5-entry list, imu Node L53-62
   with remap /imu <-> /imu/data_raw naming bridge. slam_view: rviz2
   Node + arguments=['-d', rviz_config, use_sim_time], 7 self-
   acknowledged unused imports L2-3. yahboom_keyboard: 12 moveBindings
   (forward_back, strafe, rotate) triples + speedBindings x1.1/x0.9,
   speed 0.2 turn 1.0, twist = speed*x / speed*y / turn*th, arm keys
   1-6 joints 7/8/9/0 presets with clamps, SPACE zero-Twist, deadman
   count 1..5, s pause/resume, Ctrl+C clean exit. follow_line:
   FollowLinePID 0.05/0/0.01, e=(point_x-320)/16, deadzone |dx|<40 ->
   angular.z=0, linear.x=0.1 hardcoded, front_warning>10 stop+beep 1 /
   clear beep 0 x3, Track_state init/identify/tracking/Remove, AprilTag
   pivot L341-345, centering +-10 at (320,400), c_dist=depth/1000,
   joint5 published TWICE L375-376, RemovePID 0.04/0/0.015, R1 (350,430)
   clamp (0.10,0.10), R2 (328,405) swap linear.x 0.020 / linear.y 0.032,
   halt prints L475-485 with zero-Twist AFTER prints, no cv destroy.
   save_map: map_saver_cli one-shot, -f LaunchConfiguration('map_path')
   (the one launch that really uses it), --free 0.196 / --occ 0.65,
   yahboom_map.yaml + .pgm, tool writes and exits.
   Stage = setStage 900x460 grammar. No emoji; arrow chars NEVER in
   stage <text> — only ASCII -> in formula strips or words elsewhere.
   Unique id prefix per anim: rb14- ch14- ek14- rv14- tl14- sr14-
   sd14- sv14-. Static backbone visible at setStage, first caption +
   formula set before the first await. */""".split("\n")

new = (t3[:idx(587)]
       + BANNER                       # replaces L587-613
       + t3[idx(614):idx(616)]        # blanks L614-615
       + RUNBOOK                      # replaces L616-740
       + t3[idx(741):idx(742)]        # blank L741
       + CHAIN                        # replaces L742-872
       + t3[idx(873):idx(874)]        # blank L873
       + EKF                          # replaces L874-1026
       + t3[idx(1027):idx(1028)]      # blank L1027
       + RVIZ                         # replaces L1028-1215
       + [""]                         # separator
       + TELEOP                       # NEW — part 5 teleop14
       + [""]                         # separator
       + STEER                        # replaces L1216-1359
       + STATES                       # replaces L1360-1570
       + SAVEMAP                      # replaces L1571-1730
       + t3[idx(1731):])              # L1731-end

joined = "\n".join(new)
(KIT / "t3_final_14.js").write_text(joined + "\n", encoding="utf-8")

# ---------- integrity ----------
ANIM_NAMES = ["runbook14", "chain14", "ekf14", "rviz14", "teleop14",
              "steer14", "states14", "savemap14"]
for a in ANIM_NAMES:
    assert f"ANIMS.{a} = async function" in joined, f"missing ANIMS.{a}"
assert joined.count("ANIMS.") == len(ANIM_NAMES), joined.count("ANIMS.")
for stale in ("12. lidar tracking", "13. lidar guard"):
    assert stale not in joined, f"stale title {stale}"
for stale_hdr in ("folder-12 anim", "folder-13 anim"):
    assert stale_hdr not in joined, f"stale anim header {stale_hdr}"
for bad_sha in ("d414af8d12da",            # folder-12 laser_Tracker
                "7de1ece640db", "dadf5ff3f9b1", "b1cf2d67a4d5"):  # folder-13 trio
    assert bad_sha not in joined, f"stale sha {bad_sha}"
prior_hits = [i + 1 for i, ln in enumerate(new)
              if "folder-1" in ln and "folder-14" not in ln]
# these are expected to be comparative lineage mentions only (folder 10's
# merger/filter chain) — reported below for eyeball verification, not fatal

r = subprocess.run(["node", "--check", str(KIT / "t3_final_14.js")],
                   capture_output=True, text=True)
if r.returncode != 0:
    sys.exit("node --check FAILED:\n" + r.stderr[:2000])

# ---------- html assembly ----------
t1 = (KIT / "t1_base_head.html").read_text(encoding="utf-8")
assert "<title>14. SLAM Gmapping</title>" in t1, "t1 title not folder-14"
t2 = (KIT / "t2_body.html").read_text(encoding="utf-8")
if not t2.endswith("\n"):
    t2 += "\n"
html = t1 + t2 + "<script>\n" + joined + "\n</script>\n</body>\n</html>\n"
out = KIT / "v1_base_14.html"
out.write_text(html, encoding="utf-8")

print(f"t3_final_14.js: {len(new)} lines, {(KIT / 't3_final_14.js').stat().st_size} bytes, node --check OK")
print(f"ANIMS: 8 registered; teleop14 inserted after rviz14")
print(f"cross-folder refs (non-folder-14 'folder-1x' mentions) at lines: {prior_hits[:12]}"
      f"{' ...' if len(prior_hits) > 12 else ''} — verify each is comparative, not identity")
print(f"v1_base_14.html: {out.stat().st_size} bytes, {html.count(chr(10))} lines")
