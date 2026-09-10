#!/usr/bin/env python3
"""Static QA for the folder-14 deliverable + source integrity.
1) sha256 12-hex prefixes of the 7 source files vs the frozen FACTS-14 table
   (source is READ-ONLY; the deliverable must have been built from these bytes)
2) deliverable statics: app identity, 423-step/984-line counts, 8 ANIMS,
   no stale folder-11/12/13 identity strings, refine seams present
3) headless h-scroll probe: page must never scroll horizontally.
Usage: python3 qa_static_14.py [deliverable.html]"""
import hashlib, json, re, subprocess, sys, tempfile
from pathlib import Path

SRC = Path("/home/shariful/NeuroBotics/14. SLAM Gmapping")
HTML = Path(sys.argv[1] if len(sys.argv) > 1 else SRC / "14. SLAM Gmapping.html")

EXPECT_SHA = {  # frozen at survey time (FACTS-14)
    "README.md": "1246ab7881c6",
    "gmapping.launch.py": "e9d107d1fa6d",
    "slam_view.launch.py": "ff4b1234ffdd",
    "yahboom_keyboard.py": "536b2850bd2a",
    "camera_arm_kin.launch.py": "6b2b105f277e",
    "follow_line.py": "88a485372c54",
    "save_map.launch.py": "3601e4887d57",
}

fail = 0

print("=== 1) source sha verify (read-only) ===")
for name, want in EXPECT_SHA.items():
    got = hashlib.sha256((SRC / name).read_bytes()).hexdigest()[:12]
    ok = got == want
    fail += 0 if ok else 1
    print(f"  {name:26} {got} {'OK' if ok else 'MISMATCH want ' + want}")

print("=== 2) deliverable statics ===")
doc = HTML.read_text(encoding="utf-8")
checks = [
    ('id="refine-style"', 1), ('id="refine-script"', 1),
    ('"app":"14. SLAM Gmapping"', 1),
    ("<title>14. SLAM Gmapping</title>", 1),
    ("14. SLAM Gmapping · line-by-line analysis", 1),
    ("ANIMS.runbook14 = async function", 1),
    ("ANIMS.chain14 = async function", 1),
    ("ANIMS.ekf14 = async function", 1),
    ("ANIMS.rviz14 = async function", 1),
    ("ANIMS.teleop14 = async function", 1),
    ("ANIMS.steer14 = async function", 1),
    ("ANIMS.states14 = async function", 1),
    ("ANIMS.savemap14 = async function", 1),
    ("423 steps over the real 7-file", 1),   # engine header re-pointed
    ("source, 984 lines", 1),
    ("finalRob", None),
    ("gmapping.launch.py", None),
    ("follow_line.py", None),
    ("yahboom_keyboard.py", None),
    ("save_map.launch.py", None),
]
for needle, want_n in checks:
    n = doc.count(needle)
    if want_n is None:
        ok = n > 0
    else:
        ok = n == want_n
    fail += 0 if ok else 1
    print(f"  {needle[:44]!r:48} x{n} {'OK' if ok else 'FAIL (want %s)' % want_n}")

anims = len(re.findall(r"ANIMS\.\w+ = async function", doc))
print(f"  ANIMS registrations: {anims} {'OK' if anims == 8 else 'FAIL (want 8)'}")
fail += 0 if anims == 8 else 1

stale = [s for s in ("11. lidar obstacle avoidance", "12. lidar tracking", "13. lidar guard",
                     "laser_Avoidance", "laser_Tracker", "laser_Warning",
                     "folder-12 anim", "folder-13 anim") if s in doc]
print(f"  stale identity strings: {stale or 'none'} {'OK' if not stale else 'FAIL'}")
fail += 0 if not stale else 1

print("=== 3) h-scroll probe ===")
PROBE = """<script>
(function(){
  function fin(){
    var d = document.documentElement, b = document.body;
    var m = Math.max(d.scrollWidth, b ? b.scrollWidth : 0);
    var pre = document.createElement('pre'); pre.id = 'qa-hs-result';
    pre.textContent = 'QAHS ' + JSON.stringify({scrollW: m, innerW: window.innerWidth,
      over: Math.max(0, m - window.innerWidth)});
    document.body.appendChild(pre);
  }
  if (window.__qaWait) { window.__qaWait(fin); } else { setTimeout(fin, 400); }
})();
</script>"""
tmpd = Path(tempfile.mkdtemp())
tmp = tmpd / "qa14_hs.html"
tmp.write_text(doc.replace("<head>", "<head>\n<script>window.__errs=[];window.addEventListener('error',function(e){window.__errs.push(String(e.message||e.error))});</script>", 1)
                   .replace("</body>", PROBE + "\n</body>", 1), encoding="utf-8")
out = subprocess.run(["google-chrome", "--headless=new", "--disable-gpu", "--no-sandbox",
                      "--virtual-time-budget=9000", "--dump-dom", f"file://{tmp}"],
                     capture_output=True, text=True, timeout=300).stdout
m = re.search(r'id="qa-hs-result">QAHS (\{.*?\})</pre>', out, re.S)
if not m:
    print("  FATAL: probe marker missing"); fail += 1
else:
    r = json.loads(m.group(1))
    ok = r["over"] <= 2
    fail += 0 if ok else 1
    print(f"  scrollW={r['scrollW']} innerW={r['innerW']} over={r['over']} {'OK' if ok else 'FAIL'}")

print("RESULT:", "ALL OK" if fail == 0 else f"{fail} FAILURES")
sys.exit(0 if fail == 0 else 1)
