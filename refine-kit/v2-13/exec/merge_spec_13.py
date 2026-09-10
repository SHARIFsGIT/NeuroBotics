#!/usr/bin/env python3
"""Merge out-U*.json into exec-spec-13.json against the frozen skeletons.
Chronology: U1[0:3] + U2 + U1[3:5] + U3 + U4 + U5 + U6 + U7 + U8 + U9 + U10.
Validates parse, counts, i-sets, skeleton equality, tiling, SVG sanity, arrows/emoji."""
import json, re, sys, unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path

KIT = Path("/home/shariful/NeuroBotics/refine-kit/v2-13")
EX = KIT / "exec"

UNITS = ["U1","U2","U3","U4","U5","U6","U7","U8","U9","U10"]
SKELETON = []   # (unit, i, {file,ln,lns,kind}) in spine order
for n in (1,2,3,4,5,6,7):
    SKELETON += json.load(open(EX/f"skeleton-{n}.json"))

# spine order of units maps to skeleton files:
# skeleton-1 (3) -> U1[0:3]; skeleton-2+3 (16+6) -> U2; skeleton-4 (2) -> U1[3:5];
# skeleton-5 (56) -> U3+U4+U5 (19+19+18); skeleton-6 (16) -> U6; skeleton-7 (85) -> U7..U10
spine = ([("U1", i) for i in range(0,3)] +
         [("U2", i) for i in range(0,22)] +
         [("U1", i) for i in range(3,5)] +
         [("U3", i) for i in range(0,19)] +
         [("U4", i) for i in range(0,19)] +
         [("U5", i) for i in range(0,18)] +
         [("U6", i) for i in range(0,16)] +
         [("U7", i) for i in range(0,24)] +
         [("U8", i) for i in range(0,21)] +
         [("U9", i) for i in range(0,21)] +
         [("U10", i) for i in range(0,19)])
assert len(spine) == len(SKELETON) == 184, (len(spine), len(SKELETON))

# load outs
OUT = {}
for u in UNITS:
    p = EX/f"out-{u}.json"
    if not p.exists():
        sys.exit(f"MISSING {p}")
    d = json.load(open(p, encoding="utf-8"))
    steps = d["steps"]
    idx = sorted(s["i"] for s in steps)
    if idx != list(range(len(steps))):
        sys.exit(f"{u}: bad i-set {idx[:5]}..{idx[-3:]} n={len(steps)}")
    OUT[u] = {s["i"]: s for s in steps}
UNIT_LEN = {"U1":5,"U2":22,"U3":19,"U4":19,"U5":18,"U6":16,"U7":24,"U8":21,"U9":21,"U10":19}
for u,n in UNIT_LEN.items():
    if len(OUT[u]) != n: sys.exit(f"{u}: has {len(OUT[u])} steps, expected {n}")

EMOJI = re.compile("[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F900-\U0001F9FF\U00002190-\U000021FF\U000027F5-\U000027FF\U00002B00-\U00002BFF\U0000FE0F]")
def scan_text(u, i, field, s):
    if not isinstance(s, str): sys.exit(f"{u}#{i} {field}: not a string")
    m = EMOJI.search(s)
    if m: sys.exit(f"{u}#{i} {field}: emoji/arrow char {m.group()!r} U+{ord(m.group()[0]):04X}")

steps = []
errors = []
for k, ((u, i), sk) in enumerate(zip(spine, SKELETON)):
    a = OUT[u][i]
    for f in ("cap","op","fx","rob"): scan_text(u, i, f, a.get(f,""))
    dbg = a.get("dbg", [])
    if not isinstance(dbg, list): sys.exit(f"{u}#{i} dbg: not a list")
    for r in dbg:
        if not (isinstance(r, list) and 2 <= len(r) <= 3 and all(isinstance(x, str) for x in r)):
            sys.exit(f"{u}#{i} dbg row malformed: {r!r}")
        if len(r) == 3 and r[2] not in ("ill","err"): sys.exit(f"{u}#{i} dbg flag {r[2]!r}")
        for x in r: scan_text(u, i, "dbg", x)
    rob = a.get("rob","")
    if rob:
        if "<script" in rob.lower(): sys.exit(f"{u}#{i} rob: contains script")
        try:
            ET.fromstring("<r>" + rob + "</r>")
        except ET.ParseError as e:
            errors.append(f"{u}#{i} rob: XML parse: {e}")
        for mm in re.finditer(r'\b(x|y|x1|y1|x2|y2|cx|cy|r|width|height)="(-?[\d.]+)"', rob):
            v = float(mm.group(2))
            if v > 441 or v < -1: errors.append(f"{u}#{i} rob: {mm.group(0)} out of 440x330")
    steps.append({"file": sk["file"], "ln": sk["ln"], "lns": sk["lns"], "kind": sk["kind"],
                  "cap": a["cap"], "op": a["op"], "dbg": dbg, "fx": a["fx"], "rob": rob})

# tiling: every source line appears at least once across all steps
fd = json.load(open(KIT/"filedata-13.json"))
cov = {fn: set() for fn in fd}
for s in steps: cov[s["file"]] |= set(s["lns"])
for fn, src in fd.items():
    want = set(range(1, len(src)+1))
    miss, extra = want - cov[fn], cov[fn] - want
    if miss or extra: sys.exit(f"tiling {fn}: missing {sorted(miss)[:8]} extra {sorted(extra)[:8]}")

# kind voice sanity: no struct step with publish claims in op
for s in steps:
    if s["kind"] == "struct" and re.search(r"publish|run |execute ", s["op"] or ""):
        errors.append(f"struct#{s['file']}:{s['ln']} op={s['op']!r} looks active")

shell = json.load(open(EX/"shell-13.json"))
finals = json.load(open(EX/"finals-13.json"))
spec = {**shell, "steps": steps, **finals}
(EX/"exec-spec-13.json").write_text(json.dumps(spec, ensure_ascii=False, indent=1), encoding="utf-8")

rob_n = sum(1 for s in steps if s["rob"])
kc = {}
for s in steps: kc[s["kind"]] = kc.get(s["kind"],0)+1
print(f"exec-spec-13.json written: {len(steps)} steps ({kc}), {rob_n} with rob, "
      f"{(EX/'exec-spec-13.json').stat().st_size} bytes")
print("warnings:", len(errors))
for e in errors[:20]: print("  -", e)
print("OK" if not errors else "REVIEW")
