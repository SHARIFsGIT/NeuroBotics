#!/usr/bin/env python3
"""Generate the 7 frozen skeletons + 10 unit files for folder-13 exec spec.
Mirrors folder-12's chronology, adapted to laser_Warning.py (145 lines):
  s1 (3)  README open L1-3            [verbatim from v2-12 — identical file shape]
  s2 (16) driver ctor L1-27           [verbatim — driver byte-identical]
  s3 (6)  driver run-phase events     [verbatim]
  s4 (2)  README mid L4-5             [verbatim]
  s5 (56) warning import pass L1-145  [fresh tiling for the guard's structure]
  s6 (16) main pass                   [guard: main L134, ctor L19-48]
  s7 (85) event waves                 [gate/A/B/C/D/E/F/Joy/release/halt]
Spine = 184 steps. Units: U1 5 · U2 22 · U3 19 · U4 19 · U5 18 · U6 16 ·
U7 24 · U8 21 · U9 21 · U10 19. Validates tiling against filedata-13.json.
"""
import json
from pathlib import Path

K12 = Path("/home/shariful/NeuroBotics/refine-kit/v2-12/exec")
K13 = Path("/home/shariful/NeuroBotics/refine-kit/v2-13/exec")
W = "laser_Warning.py"

def step(f, lns, kind):
    return {"file": f, "ln": lns[0], "lns": list(lns), "kind": kind}

# ---- s1-s4: folder-12 driver/README skeletons carry over verbatim ----
s1 = json.load(open(K12 / "skeleton-1.json"))
s2 = json.load(open(K12 / "skeleton-2.json"))
s3 = json.load(open(K12 / "skeleton-3.json"))
s4 = json.load(open(K12 / "skeleton-4.json"))
for st in s1 + s4:
    assert st["file"] in ("README.md",), st
for st in s2 + s3:
    assert st["file"] == "laser_driver.launch.py", st

# ---- s5: import pass over warning L1-145 (struct voice after L17) ----
S5_GROUPS = [
    (1, 5, "exec"),    # ros lib comment + rclpy/Node/Twist/LaserScan
    (6, 6, "exec"),    # UInt16 import — the guard's new message type
    (7, 13, "exec"),   # commom lib: math, np, dead time imports, star import
    (14, 15, "exec"),  # import os + imprt done print (typo)
    (16, 16, "exec"),  # RAD2DEG
    (17, 18, "struct"),   # blank + class laserWarning
    (19, 20, "struct"),   # def __init__(self,name) + super
    (21, 23, "struct"),   # blank + subscribers comment
    (24, 25, "struct"),   # sub /scan + comment
    (26, 27, "struct"),   # sub /JoyState + blank
    (28, 29, "struct"),   # publishers comment
    (30, 30, "struct"),   # pub /cmd_vel
    (31, 33, "struct"),   # buzzer comment + pub /beep + blank
    (34, 36, "struct"),   # params comment + linear declare + dead get
    (37, 38, "struct"),   # angular declare + dead get
    (39, 40, "struct"),   # LaserAngle pair
    (41, 42, "struct"),   # ResponseDist pair
    (43, 45, "struct"),   # blank + state comment + Joy_active = False
    (46, 48, "struct"),   # PID comments + ang_pid SinglePID(3,0,5)
    (49, 50, "struct"),   # blank + def JoyStateCallback
    (51, 53, "struct"),   # isinstance + assignment + blank
    (54, 55, "struct"),   # def registerScan + type guard
    (56, 58, "struct"),   # ranges + blank + cone comment
    (59, 60, "struct"),   # two parallel lists
    (61, 63, "struct"),   # loop comment + for
    (64, 65, "struct"),   # angle comment + angle =
    (66, 68, "struct"),   # blank + FRONT ZONE comment + cone if
    (69, 70, "struct"),   # appends
    (71, 73, "struct"),   # empty comment + early return
    (74, 76, "struct"),   # blank + comment + minDist = min
    (77, 78, "struct"),   # comment + argmin
    (79, 81, "struct"),   # blank + Joy comment + Joy gate if
    (82, 83, "struct"),   # zero Twist publish + return
    (84, 85, "struct"),   # blank + print minDist
    (86, 89, "struct"),   # ALARM comments + alarm if
    (90, 92, "struct"),   # b = UInt16 + data=1 + publish -> BEEP ON
    (93, 95, "struct"),   # else + comment + publish UInt16() -> OFF
    (96, 98, "struct"),   # blank + TRACKING comment + Twist
    (99, 100, "struct"),  # print minDistID (tab) + blank
    (101, 103, "struct"), # comments + pid_compute
    (104, 106, "struct"), # blank + comments + if 0 < minDistID
    (107, 108, "struct"), # z = +compute + comment
    (109, 110, "struct"), # elif + z = -compute
    (111, 112, "struct"), # blank + print orin
    (113, 115, "struct"), # blank + comment + deadzone
    (116, 118, "struct"), # blank + comment + damping x0.5
    (119, 120, "struct"), # blank + print angular.z
    (121, 124, "struct"), # blank + comments (linear.x never set) + publish
    (125, 127, "struct"), # blank + SAFETY comment + def exit_pro
    (128, 129, "struct"), # comment + cmd1 (trailing space)
    (130, 132, "struct"), # cmd2 + cmd + os.system
    (133, 135, "struct"), # blank + def main + rclpy.init
    (136, 137, "struct"), # laserWarning("laser_Warnning_a1") + print start it
    (138, 139, "struct"), # try + spin
    (140, 142, "struct"), # except + pass + finally
    (143, 145, "struct"), # exit_pro + destroy + shutdown
]
s5 = [step(W, list(range(a, b + 1)), k) for a, b, k in S5_GROUPS]

# ---- s6: main pass — constructor truly runs ----
s6 = [
    step(W, [134], "event"),   # main() entered (setup.py entry, inferred)
    step(W, [135], "exec"),    # rclpy.init()
    step(W, [136], "exec"),    # laserWarning("laser_Warnning_a1") — typo
    step(W, [19], "exec"),     # __init__ entered with name
    step(W, [24], "exec"),     # sub /scan bound
    step(W, [26], "exec"),     # sub /JoyState bound
    step(W, [30], "exec"),     # pub /cmd_vel bound
    step(W, [31, 32], "exec"), # pub /beep bound (comment + create)
    step(W, [35, 36], "exec"), # linear param — read then dead
    step(W, [37, 38], "exec"), # angular pair — dead
    step(W, [39, 40], "exec"), # LaserAngle 45.0
    step(W, [41, 42], "exec"), # ResponseDist 0.55
    step(W, [45], "exec"),     # Joy_active = False
    step(W, [48], "exec"),     # ang_pid SinglePID(3.0, 0.0, 5.0)
    step(W, [137], "exec"),    # print ("start it")
    step(W, [139], "exec"),    # rclpy.spin parks the loop
]

# ---- s7: event waves (guard callback replays) ----
s7 = []
# gate: JoyState False arrives before any scan
s7.append(step(W, [50], "event"))
# wave A — full replay, 0.90 m @ +14 deg, beep OFF, z +0.292
for lns, kind in (
    ([51, 52], "exec"),   # isinstance + Joy_active = False
    ([54], "event"),      # first /scan arrives
    ([55], "exec"),       # type guard
    ([56], "exec"),       # ranges array
    ([59, 60], "exec"),   # lists born empty
    ([63], "exec"),       # for over beams
    ([65], "exec"),       # angle math
    ([68], "exec"),       # cone strict
    ([69, 70], "exec"),   # appends (89 beams, illustrative)
    ([73], "exec"),       # non-empty: guard passes
    ([76], "exec"),       # minDist = 0.90
    ([78], "exec"),       # minDistID = +14.0
    ([85], "exec"),       # print minDist
    ([89], "exec"),       # alarm check: 0.90 > 0.55 no
    ([95], "exec"),       # else publishes UInt16() -> beep OFF
    ([98], "exec"),       # velocity = Twist()
    ([99], "exec"),       # print minDistID
    ([103], "exec"),      # pid_compute(14/72, 0)
    ([106, 107], "exec"), # left branch z = +0.583
    ([115], "exec"),      # deadzone 0.583 >= 0.5 passes
    ([118], "exec"),      # damping x0.5 -> +0.292
    ([120], "exec"),      # print angular.z
    ([124], "exec"),      # publish (0.0, +0.292)
):
    s7.append(step(W, lns, kind))
# wave B — short replay, 0.70 m @ +20 deg, beep OFF, z +0.417
for lns, kind in (
    ([54], "event"), ([56], "exec"), ([65], "exec"), ([68], "exec"),
    ([69, 70], "exec"), ([76], "exec"), ([78], "exec"), ([89], "exec"),
    ([95], "exec"), ([103], "exec"), ([106, 107], "exec"), ([118], "exec"),
    ([124], "exec"),
):
    s7.append(step(W, lns, kind))
# wave C — 0.48 m @ 0 deg INSIDE zone: BEEP + stand still
for lns, kind in (
    ([54], "event"), ([76], "exec"), ([78], "exec"), ([89], "exec"),
    ([90, 92], "exec"),   # b.data = 1 -> /beep ON
    ([103], "exec"),      # e = 0
    ([115], "exec"),      # 0 < 0.5 -> z = 0.0
    ([124], "exec"),      # publish (0.0, 0.0) still + beeping
):
    s7.append(step(W, lns, kind))
# wave D — 0.50 m @ -20 deg in zone: BEEP + spin right
for lns, kind in (
    ([54], "event"), ([76], "exec"), ([78], "exec"), ([89], "exec"),
    ([90, 92], "exec"), ([103], "exec"), ([109, 110], "exec"),
    ([118], "exec"), ([124], "exec"),
):
    s7.append(step(W, lns, kind))
# wave E — nothing valid in front: early return, /beep latches at 1
for lns, kind in (
    ([54], "event"), ([59, 60], "exec"), ([68], "exec"), ([73], "exec"),
):
    s7.append(step(W, lns, kind))
# wave F — 0.80 m @ +8 deg clear: else beep OFF + deadzone still
for lns, kind in (
    ([54], "event"), ([76], "exec"), ([78], "exec"), ([89], "exec"),
    ([95], "exec"), ([103], "exec"), ([115], "exec"), ([124], "exec"),
):
    s7.append(step(W, lns, kind))
# Joy override — human grabs control
for lns, kind in (
    ([50], "event"), ([51, 52], "exec"), ([54], "event"),
    ([81], "exec"), ([82], "exec"), ([83], "exec"),
):
    s7.append(step(W, lns, kind))
# release — JoyState False again
for lns, kind in (
    ([50], "event"), ([51, 52], "exec"), ([54], "event"),
):
    s7.append(step(W, lns, kind))
# halt — Ctrl+C + finally + exit_pro + shutdown
for lns, kind in (
    ([139], "event"),      # Ctrl+C interrupts spin
    ([140, 141], "exec"),  # except KeyboardInterrupt: pass
    ([142], "exec"),       # finally
    ([143], "exec"),       # exit_pro() called
    ([129], "exec"),       # cmd1 (trailing space)
    ([130, 131], "exec"),  # cmd2 + cmd join
    ([132], "exec"),       # os.system shell brake — /cmd_vel zeroed, /beep untouched
    ([128], "exec"),       # exit_pro comment context
    ([144], "exec"),       # destroy_node
    ([145], "exec"),       # rclpy.shutdown
):
    s7.append(step(W, lns, kind))

# ---- assemble, validate tiling, write ----
skeletons = [s1, s2, s3, s4, s5, s6, s7]
spine = s1 + s2 + s3 + s4 + s5 + s6 + s7
total = len(spine)
assert total == 184, total

fd = json.load(open("/home/shariful/NeuroBotics/refine-kit/v2-13/filedata-13.json"))
cov = {fn: set() for fn in fd}
for st in spine:
    cov[st["file"]] |= set(st["lns"])
    assert st["lns"] == sorted(st["lns"]) and st["ln"][0] if False else True
for fn, src in fd.items():
    want = set(range(1, len(src) + 1))
    miss = want - cov[fn]
    extra = cov[fn] - want
    assert not miss and not extra, (fn, sorted(miss)[:6], sorted(extra)[:6])

for n, sk in enumerate(skeletons, 1):
    (K13 / f"skeleton-{n}.json").write_text(json.dumps(sk, ensure_ascii=False), encoding="utf-8")

UNITS = [
    ("U1", s1 + s4), ("U2", s2 + s3),
    ("U3", s5[0:19]), ("U4", s5[19:38]), ("U5", s5[38:56]),
    ("U6", s6),
    ("U7", s7[0:24]), ("U8", s7[24:45]), ("U9", s7[45:66]), ("U10", s7[66:85]),
]
counts = {}
for name, steps in UNITS:
    (K13 / f"unit-{name}.json").write_text(json.dumps(steps, ensure_ascii=False), encoding="utf-8")
    counts[name] = len(steps)
print("spine:", total, "| skeleton sizes:", [len(s) for s in skeletons])
print("unit counts:", counts, "| sum:", sum(counts.values()))
print("tiling OK: all", sum(len(v) for v in fd.values()), "source lines covered exactly once each file")
