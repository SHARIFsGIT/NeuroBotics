# exec-brief-14 — binding style contract for exec-spec-14 authoring

You are authoring content for the v2 "Complete Execution — Code → Debug → Robot"
section of the folder-14 app. `/home/shariful/NeuroBotics/refine-kit/v2-14/FACTS-14.md`
is BINDING ground truth. The seven source files are READ-ONLY:
- `/home/shariful/NeuroBotics/14. SLAM Gmapping/README.md` (15 lines — 8 commands at ODD lines)
- `/home/shariful/NeuroBotics/14. SLAM Gmapping/gmapping.launch.py` (94 lines)
- `/home/shariful/NeuroBotics/14. SLAM Gmapping/slam_view.launch.py` (59 lines)
- `/home/shariful/NeuroBotics/14. SLAM Gmapping/yahboom_keyboard.py` (242 lines)
- `/home/shariful/NeuroBotics/14. SLAM Gmapping/camera_arm_kin.launch.py` (40 lines)
- `/home/shariful/NeuroBotics/14. SLAM Gmapping/follow_line.py` (485 lines, TAB-indented)
- `/home/shariful/NeuroBotics/14. SLAM Gmapping/save_map.launch.py` (49 lines)
Read them yourself; quote code EXACTLY. follow_line.py is TAB-indented — when you
quote fragments, keep the source's own spacing; never re-indent. L148 is a Chinese
comment (source, keep as-is if shown). save_map L40 is the whole return on one line.

## Your work unit

You get `exec/unit-<U>.json`: an ordered array of step skeletons
`{"file","ln","lns","kind"}`. These are FROZEN — file/ln/lns/kind must not
change, order must not change, no step added or dropped. You author FIVE content
fields per step and return them keyed by the step's index `i` (0-based, position
in the array). Output schema:

```json
{"steps": [{"i":0,"cap":"…","op":"…","dbg":[["k","v"],["k","v","ill"]],"fx":"…","rob":"…"}, …],
 "notes": "optional concerns for the reviewer"}
```

- `cap` — 1-3 sentence Bangla explanation of THESE lines AT THIS MOMENT of the
  trace (what happens now, not a general lecture). Technical terms English,
  Bangla hyphen-suffix grammar (`PID-টি`, `callback-এ`, `parameter-গুলো`).
  `<code>…</code>` for code fragments; escape `<`/`>` as `&lt;`/`&gt;` inside
  code tags when quoting source comparisons. Line references always REAL source
  lines. No emoji; no transliteration of technical terms (shipped tolerance set:
  টেস্ট/রেজিস্টার/ডিগ্রি/স্কিপ/রিসেট/স্টিয়ারিং only). Arrow policy: ASCII
  `->` is allowed in cap/dbg/op/fx/rob (folder-11/12/13 precedent); UNICODE
  arrow characters (→ ← ↑ ↓ ⇒ ⇄ and any lookalike) are BANNED everywhere.
- `op` — short English imperative for the op-strip, ASCII only, e.g.
  `type ros2 launch slam_mapping gmapping.launch.py`, `bind path merger launch`,
  `publish Twist 0.20 0.00 0.00 to cmd_vel`.
- `dbg` — debug rows `[key, value]` or `[key, value, flag]` with flag
  `"ill"` (illustrative value — engine dims it) or `"err"` (wrong/stale-as-written
  value — engine reddens it). 2-5 rows per step (struct steps may use fewer).
  Keys MUST come from the registry below (new key allowed only if genuinely
  needed; then note it). On repeated keys across consecutive steps the engine
  renders BEFORE -> AFTER — use this deliberately. Values: ASCII digits for
  measurements; may carry units (`0.20 m/s`, `0.375 m`, `+14.0 deg`).
  Non-source-true numbers -> flag `ill`.
- `fx` — compact fixed-strip line, ASCII + `·` separators, plain `->` ALLOWED
  here. Pattern: `<op echo>   · <subject>, illustrative` when any part is
  illustrative. e.g. `z_Pid = 0.125   · P-only view, Kd transient ignored, illustrative`.
- `rob` — inner SVG fragment (NO `<svg>` wrapper) for the 440×330 robot panel;
  `""` (empty string) to keep the previous panel. FULL redraw — repeat the
  chrome, do not reference earlier fragments. Rules below.

## kind semantics (voice + pacing)

- `struct` — define/bind/compile/gloss moment: blank lines, comments, def
  headers, class body during import pass, dead code being defined. Voice:
  "এখনো শুধু define হচ্ছে / চলবে না / নীরব সাক্ষী"। dbg optional (may be `[]`).
- `exec` — module-level or constructor statement that runs NOW with a side
  effect (import binding, print, eager path join, Node object built, return
  LaunchDescription, publish, PID construction, declare_parameter during main
  pass). dbg should show the state change.
- `event` — external world drives it (README command typed, launch run-phase
  entry firing, message arrival, callback dispatch, key press, Ctrl+C,
  main() entry). Voice: "message এলো / framework ডাকল / ঘটনা ঘটল"। dbg shows
  the incoming payload + new state.

## dbg key registry (use consistently; BEFORE -> AFTER across steps)

phase · command · file · pass · import · module · class · def · node · sub ·
pub · param · include · path · entry · launch · topic · key · x · y · th ·
speed · turn · linear.x · linear.y · angular.z · publish · cmd_vel · twist ·
clamp · arm_joints · joint · arm_msg · beep · front_warning · angle · cone ·
ranges · PID · z_Pid · point_x · deadzone · Track_state · hsv · circle ·
tags · c_dist · map · free · occ · exit

Notes: `arm_joints` = the keyboard node's six-value list; `arm_msg` = the
ArmJoint/ArmJoints message on the wire (`id/joint/time` or six joints + time);
`joint` = one joint's degree value; `beep` = /beep UInt16 on the wire (0/1);
`front_warning` = count of cone beams closer than 0.375 m; `point_x` = line
centroid x in the 640-wide frame; `tags` = `len(self.tags)`; `c_dist` = tag
depth in meters; `map`/`free`/`occ` = save_map values (map path / 0.196 / 0.65);
`th` = rotate component BEFORE turn-scaling; `z_Pid` = PID output before
deadzone/flip.

## README command table (chronology spine — quote EXACTLY)

| L | command | what it starts |
|---|---|---|
| 1 | `sh start_agent.sh` | vendor bringup (illustrative — script NOT in this folder) |
| 3 | `ros2 launch slam_mapping gmapping.launch.py` | dive into gmapping.launch.py (U1-U3) |
| 5 | `ros2 launch slam_mapping slam_view.launch.py` | dive into slam_view.launch.py (U4-U5) |
| 7 | `ros2 run yahboomcar_ctrl yahboom_keyboard` | dive into yahboom_keyboard.py (U6-U12) |
| 9 | `ros2 launch M3Pro_demo camera_arm_kin.launch.py` | dive into camera_arm_kin.launch.py (U13) |
| 11 | `ros2 run M3Pro_demo follow_line` | dive into follow_line.py (U14-U22) |
| 13 | `ros2 topic pub /arm6_joints arm_msgs/msg/ArmJoints {"joint1: 90, joint2: 140, joint3: 20, joint4: 10, joint5: 90, joint6: 180, time: 1500"} --once` | one-shot arm command (U22; subscriber = vendor arm driver, illustrative) |
| 15 | `ros2 launch slam_mapping save_map.launch.py` | dive into save_map.launch.py (U23) |

Even lines are blank (struct). The topic-pub payload is one line in source;
when quoting in cap/dbg you may elide the middle with `…`.

## Launch-file model (gmapping, slam_view, camera, save_map)

Two phases, folder-10/13 precedent:
- **ctor phase** (`generate_launch_description()` body runs once): imports and
  path joins EXEC (`os.path.join(...)` builds a string NOW); comments/blanks
  struct; `Node(...)` objects are BUILT (exec — "object built, not started");
  the `return LaunchDescription([...])` list assembles entry objects (exec for
  entry lines, struct for comment lines between them).
- **run phase** (event): each include/node entry FIRES — replay its lines as
  `event` steps; the program actually starts.

gmapping specifics (FACTS §2): duplicate `Node` import L2+L9; unused
LaunchConfiguration/DeclareLaunchArgument L3-4; three dead lists L17-19
(defined, never referenced — say it once, never dwell); FOUR eager joins
L24-28 merger `ira_laser_tools` merge_multi.launch.py, L31-35 filter
`yahboom_laser_filter` laser_filter_node.launch.py, L38-42 ekf
`robot_localization` ekf.launch.py, L45-49 gmapping `slam_gmapping`
gmapping.launch.py (share paths illustrative); imu Node L53-62 with
`remappings=[('/imu','/imu/data_raw')]` L60 (the "renaming bridge" comment
block L56-59 is source humor — quote once); FINAL LIST L66-93 in order
merger, filter, imu (bare Node, no include), ekf, gmapping — five entries,
five run-phase events. The "AI listens with five ears" comment L85-89 is
source; keep its spirit in one cap.

slam_view (FACTS §3): 7 unused imports acknowledged by source comment L2-3
(self-aware — quote it); `use_sim_time` LaunchConfiguration L24; rviz_config
join L30-34 to `slam_rviz.rviz`; rviz Node L41-52 `arguments=['-d', rviz_config,
use_sim_time]`; two entries. rviz_config_arg processes first (event), then
rviz_node fires — RViz window opens with the map+laserscan display config.

camera_arm_kin (FACTS §5): LIST-arg include —
`PythonLaunchDescriptionSource([os.path.join(get_package_share_directory("orbbec_camera"), "launch"), "/dabai_dcw2.launch.py"])`
L18-23 (both list elements join into ONE path — the `[...]` is a list arg);
kin Node L29-33 `arm_kin` package, `kin_srv` executable, name `kin_ik_fk`
(simple IK/FK math service). Two run events: camera driver up, kin service up.

save_map (FACTS §7): `get_package_share_path` (NOT directory) L8 — used;
`gpshd` L5 imported but UNUSED (dead). map_name `yahboom_map` L14;
default_map_path L15-18 to `M3Pro_navigation/map`; map_arg L23-27 with default
`map`; map_saver Node L31-40 `nav2_map_server`/`map_saver_cli` with
`-f map_path`, `--free 0.196`, `--occ 0.65`. map_saver_cli is ONE-SHOT: it
saves `/map` to `yahboom_map.yaml`+`.pgm` and the launch EXITS — the only
command in the folder that terminates itself (say exactly that).

## Python two-pass model (yahboom_keyboard, follow_line)

**import pass** (struct voice): module-level lines exec (imports, RAD2DEG,
prints); class body lines ALL struct — defined, dormant. **main pass**: main()
entry event -> rclpy.init exec -> constructor lines replay as exec (the ctor
runs for real now) -> spin/loop entry. **event waves**: each external input
replays the matching lines as event + exec steps.

### yahboom_keyboard canonical state

Defaults: `speed, turn = 0.2, 1.0`; x, y, th = 0; count = 0; stop = False;
arm_joints home `[90, 90, 0, 0, 90, 90]` (L124; the L82 initial is the same).
Limits: linear_speed_limit 1.0, angular_speed_limit 5.0 (declared L76-77,
read L78-79, used ONLY as clamps L190-191).

| key wave | binding / effect | exact numbers on the wire |
|---|---|---|
| i | (1,0,0) | twist (0.20, 0.00, 0.00) — `Current Speed -> Linear: 0.20 m/s \| Angular: 1.00 rad/s` (L99 format, ASCII -> in source) |
| u | (1,1,0) diagonal left-forward | (0.20, 0.20, 0.00) — linear.y nonzero, the mecanum signature |
| q | (1.1,1.1) | speed 0.2->0.22, turn 1.0->1.10, both under clamp; vels re-printed |
| 1 | step_arm_joint(1,-5) | arm_joints[0] 90->85 (clamp 0..180 L110); ArmJoint id=1 joint=85 time=500 on /arm_joint; print `[ARM] Joint 1 -> Down -> 85 deg`; wheels KEEP last x,y,th — count NOT reset (arm keys don't touch it) |
| g | step_arm_joint(6,-5) | arm_joints[5] 90->85 (clamp 30..180 L108); `Closing` (joint 6 is the gripper, L118-120); `[ARM] Joint 6 -> Closing -> 85 deg` |
| SPACE | emergency_stop one-shot | Twist() zero on /cmd_vel L138 + ArmJoints current joints time=100 L147 (brake); x,y,th=0; print L179; NOT latched — next move key resumes |
| s (pause) | stop=True | print `ALL CONTROLS PAUSED: True`; emergency_stop; x,y,th=0; from now every loop publishes Twist() zero L233 |
| s (resume) | stop=False | controls live again but x,y,th still 0 -> publishes (0,0,0) until a move key |
| deadman | 5 empty getKey polls | count 1..5 (L212); count>4 -> x,y,th=0 (L214) — release-to-stop; had a move key been held, motion zeroes here |
| Ctrl+C | '\x03' break L216 | except NOT hit; finally L237-242: emergency_stop again, termios restored, destroy_node, rclpy.shutdown — clean, no [ERROR] line |

getKey mechanics (L88-96): raw mode, `select` timeout 0.1 s — that 0.1 s IS
the loop's poll rate (approx 10 Hz publish while a key's direction is latched
in x/y/th, folder-standard teleop story, illustrative). getKey returning ''
is normal (no key), NOT the deadman key.

### follow_line canonical numbers

Ctor (main pass): pubs `/cmd_vel`, `/linefollow/rgb_image`, `/beep`; subs
`/JoyState` (L38) + `/scan1` (L39) + `/JoyState` DUPLICATE (L40 — the L40 sub
wins, same callback, say once); message_filters rgb `/camera/color/image_raw` +
depth `/camera/depth/image_raw` (L42-43 — rgb topic is /camera/COLOR/, not /rgb/); sync `Subscriber... queue 1, slop
0.5` (L56-57); init_joints `[90, 90, 12, 20, 90, 0]` (L51 — different from
keyboard's home!). BLOCKING WAIT L52-55: `while pubSixArm.get_subscription_count()
== 0: pass` — the ctor HANGS until an arm subscriber appears; then two
pubSixArm calls (L53-55) + sleep 0.1. Detector tag36h11 (L62-69, 8 params —
nthreads 8, quad_decimate 2.0, quad_sigma 0.0, refine_edges 1,
decode_sharpening 0.25, debug 0). declare_param() L73 -> 14 declares+reads (13 inside the L189-216 window + refresh L217-218)
L188-218: HSV Hmin/Hmax 0/9, Smin/Smax 85/253, Vmin/Vmax 126/253; Kp 60 Ki 0
Kd 20 — **Kp/Ki/Kd are declared, read, and NEVER WIRED** (PID_init uses the
hardcoded tuples — FACTS §8); scale 1000, LaserAngle 60, linear 0.18 (declare_param
is CALLED at L73, so L214 writes 0.18 FIRST and ctor L93's `self.linear = 0.2`
is the LAST write — attribute ends 0.2, ros param stays 0.18, and NEITHER is
used — execute hardcodes 0.1),
ResponseDist 0.25, refresh False. Prints L111-115: `Init Done.`,
`self.LaserAngle:  60`, `self.ResponseDist:  0.25`.

registerScan (L122-131): front_warning = 0 each scan; cone condition
`abs(angle) < 30 or abs(angle) > 330` (LaserAngle*0.5 = 30) AND `ranges[i] != 0.0`;
inside cone, `ranges[i] <= 0.375` (ResponseDist*1.5) -> front_warning += 1.
Illustrative /scan1 ring: 360 beams, `angle_i = -180 + i` deg (folder-10/11/12
consistent): cone beams i = 151..209 plus wrap group i = 330..359 & 0..29, all
values illustrative (no sum cited — shipped wording lists ranges only).

synced callback (L147-174): rgb `rgb8` + `np.copy` L149-150; depth `32FC1`
resize float32 L152-155; Detector detect + sort + draw_tags L157-159; DUPLICATE
depth block L161-165 (runs every synced callback, but writes LOCAL
depth_image_info that nothing reads — L155's stored self.depth_image_info is
what L357 c_dist uses); waitKey L166; 3-second arming L167-170
(start_time + 3 < time.time()); process + RGB2BGR + imshow L171-174.

process (L291-380) state machine — `Track_state` starts `'identify'` (L84):
- keys: SPACE->'tracking' L297, i->'identify' L299, r->Reset L300, q->cancel
  L301 (wildcard helper). identify L315: `read_HSV` loads saved hsv_range or
  stays init; tracking L334: `line_follow` L320 returns (rgb, binary, circle)
  then `threading.Thread(target=execute, args=(circle[0], circle[2]))` L336 —
  point_x = circle[0], color_radius = circle[2]; dyn HSV write-back L321-333.
- APRILTAG PIVOT L341-345: `len(tags)>0 and Track_state != "Remove"` ->
  Track_state='identify', publish Twist() zero, print `Find the apriltag.`,
  then Track_state='Remove'.

execute (L245-289):
- Joy_active True -> first call PID_init then early return L247-251 (joystick
  override story).
- color_radius == 0 -> `Not Found`, publish
  `follow_line_clear_future_done` String + Twist() zero L253-257.
- PID: `[z_Pid, _] = FollowLinePID.update([(point_x - 320)*1.0/16, 0])` L261;
  FollowLinePID = simplePID((50, 0, 10)/1000) = Kp 0.05 Ki 0 Kd 0.01 L222-225.
  P-only view (illustrative, Kd transient on first call — mention once):
  `e = (point_x-320)/16`, `z_Pid = 0.05*e`.
- `img_flip` False (L96) -> `twist.angular.z = +z_Pid` L265.
- `twist.linear.x = 0.1` L269 HARDCODED (the 0.18/0.2 params never reach here).
- `front_warning > 10` L270 -> `Obstacles ahead !!!`, Twist() zero,
  Buzzer_state=True, `/beep` UInt16 1 (once per frame).
- clear again L276-280: if Buzzer_state was True -> `/beep` 0 published 3x
  (range(3) L279), Buzzer_state=False. (Buzzer here = per-frame edge+triple-off,
  DIFFERENT from folder-13's latched level — contrast is a teaching moment, use once.)
- deadzone L282-284: `abs(point_x-320) < 40` -> angular.z = 0.0 (drive straight).
- publish L286.

Canonical line-follow frames (illustrative, consistent):

| frame | point_x | e=(px-320)/16 | z_Pid=0.05e | deadzone | publish (x, z) |
|---|---|---|---|---|---|
| F1 | 260 | -3.75 | -0.1875 | 60 not <40 pass | (0.1, -0.1875) turn right |
| F2 | 300 | -1.25 | -0.0625 | 20 <40 -> 0.0 | (0.1, 0.0) straight |
| F3 | 380 | +3.75 | +0.1875 | 60 pass | (0.1, +0.1875) turn left |
| F4 | 320 | 0.0 | 0.0 | 0 <40 -> 0.0 | (0.1, 0.0) dead center |

AprilTag Remove (L346-380): adjusting when `abs(cx-320) > 10 or abs(cy-400)
> 10` and move_flag L350 -> `remove_obstacle(cx, cy)` L352 with print
`adjusting.`. remove_obstacle L389-395: `[y, x] = RemovePID.update([(cx-320)/10.0,
(cy-400)/10.0])` — DESTRUCTURING SWAP: first output lands in `y` (lateral),
second in `x` (forward); RemovePID = simplePID((40, 0, 15.0)/1000) = Kp 0.04
Ki 0 Kd 0.015. Clamps ±0.10 each (L391-394); `pubVel(x, y)` L395 ->
vel.linear.x = x, vel.linear.y = y.

| Remove frame | cx, cy | inputs | raw out (P-only) | clamped | pubVel |
|---|---|---|---|---|---|
| R1 | 350, 430 | (3.0, 3.0) | (0.12, 0.12) | (0.10, 0.10) | creep forward+left AT CAP |
| R2 | 328, 405 | (0.8, 0.5) | (0.032, 0.020) | unchanged | (0.020 fwd, 0.032 left) — note swap |

R2 wire order: vel.linear.x = 0.020 (the SECOND channel), vel.linear.y =
0.032 (the FIRST channel) — the swap in action; make one cap teach it.

Centered L353-357: `abs(cx-320)<10 and abs(cy-400)<10` -> pubVel(0,0), print
`start crawling.`, `time.sleep(3)`, `c_dist = depth[int(cy), int(cx)]/1000`
L357 (mm -> m). If `c_dist != 0 and pubPos_flag` L358: move_flag=False,
pubPos_flag=False (one-shot latch), AprilTagInfo(id, x=cx, y=cy, z=c_dist),
vx/vy from corners[0]-corners[1] L366-367, `target_joint5 = compute_joint5(vx,
vy)` (wildcard helper — illustrative), joint5.data = int(target_joint5),
prints L369-373 (`target_joint5:`, `tag_id:`, `center_x, center_y:`, `depth:
`), `pos_info_pub.publish(pos)` L374, then `TargetJoint5_pub.publish(joint5)`
TWICE L375-376 (source duplicate — publish is not idempotent for subscribers;
say once, never fix). Else `Invalid distance.` L378.

grasp wave (L140-145): `get_graspStatusCallBack` msg True -> move_flag=True,
pubPos_flag=True, and if `len(tags)==0` -> Track_state='tracking' (arm done,
line-follow resumes).

halt (L471-485): Ctrl+C -> `except KeyboardInterrupt: pass` L473-474 (silent),
then finally L475-485: prints `"=" * 64`, `  Stopping robot safely...`,
`  [OK] Zero velocity command sent`, `  [OK] ROS 2 node stopped`,
`  Goodbye!`, `"=" * 64` — and the zero-Twist publish comes AFTER those prints
(L483 `pub_cmdVel.publish(Twist())`), then destroy_node + rclpy.shutdown. No
cv destroy call exists — do not invent one. The main banner (L434-459) reads
`M3Pro ROBOT - LINE FOLLOW + APRILTAG` with keyboard list `SPACE -> Start /
tracking mode`, `I -> Identify/load HSV settings`, `R -> Reset`, `Q -> Quit`
(source uses ASCII ->); startup prints `  [OK] ROS 2 node started:
follow_line` L463 and `  >>> System is RUNNING. <<<` L468 — quote exactly.

## rob panel — exact grammar (calibrate against `exec/ref-*.json` "rob" fields)

Canvas 440×330. TWO cards + 3 Bangla bottom lines. Copy this chrome VERBATIM
into every non-empty rob (then edit the marked parts):

- TERMINAL card: `<rect x="16" y="22" width="196" height="228" rx="9" fill="#161b22" fill-opacity=".55" stroke="#4fc3f7" stroke-width="1.4"/><text x="26" y="34" text-anchor="start" font-family="monospace" font-size="10" fill="#e6edf3" font-weight="bold">TERMINAL</text><text x="202" y="34" text-anchor="end" font-family="monospace" font-size="5.8" fill="#6e7681">STATUS-WORD</text><text x="26" y="45" font-family="monospace" font-size="5.8" fill="#6e7681">jetson@yahboom: ~ (illustrative)</text>`
  then console lines at y = 56, 67, 78, … (11 px pitch), monospace 5.8-6.5,
  colors: command echo `#e6edf3`, normal output `#8b949e`, live/highlight
  `#7ee787`, warning `#ffb454`, error `#ff7b72`. Prefix prompt
  `jetson@yahboom:~$ ` only on a NEW command line. Max ~15 lines; elide with
  `…` row. gmapping/slam_view/save_map phases: terminal shows the launch line
  + `[INFO]` style process lines (illustrative, ROS-conventional). keyboard:
  the banner lines + `[ARM]`/`[SYSTEM]` prints EXACTLY as source formats them.
  follow_line: `Init Done.` + the four per-frame prints when relevant.
- SYSTEM card: `<rect x="216" y="22" width="208" height="228" rx="9" fill="#161b22" fill-opacity=".55" stroke="#30363d" stroke-width="1.4"/><text x="226" y="34" text-anchor="start" font-family="monospace" font-size="10" fill="#e6edf3" font-weight="bold">SYSTEM</text><text x="414" y="34" text-anchor="end" font-family="monospace" font-size="5.8" fill="#6e7681">STATE-WORD</text><rect x="224" y="42" width="192" height="196" rx="4" fill="#0d1117" fill-opacity=".8" stroke="#21262d" stroke-width="1"/>`
  then draw the scene INSIDE x 224..416, y 42..238 (~4 px padding).
  Vocabulary by phase — pick what the step needs, never all at once:
  - robot top-view = rounded rect ~28×34 `fill="url(#egB)" stroke="#4fc3f7"`
    + heading wedge triangle `fill="#4fc3f7"` opacity .8 (NO Unicode arrows
    in SVG text — draw triangle `path`s, or write `fwd`/`left`/`right`);
  - mecanum wheels = 4 small rects `#8b949e` (linear.y strafe is REAL here —
    unlike folder-13, diagonal velocity arrows ARE correct for u/Remove waves);
  - twist vector = straight bold arrow + triangle tip `#d2a8ff` (linear) and
    curved arc + tip (angular) — BOTH allowed in this folder when the source
    publishes them;
  - lidar: front 60-deg cone edges `stroke="#4fc3f7" stroke-dasharray="3 3"`
    opacity .5, danger ring 0.375 m `stroke="#ff7b72" stroke-dasharray="3 3"`
    opacity .5, beam hits `#ffb454` dots;
  - SLAM map: occupancy grid = small rect tiles `#30363d` unknown / `#7ee787`
    free / `#ff7b72` occupied growing across gmapping steps + robot pose dot
    `#4fc3f7` with trail `#d2a8ff`; scan match lines thin `#7ee787` opacity .4;
  - RViz (slam_view): mini window frame `stroke="#30363d"` with map tiles +
    `/scan` dots inside;
  - arm = side-view stick of 6 segments `stroke="#4fc3f7"` 2px with joint
    dots `#e6edf3`, gripper open/closed V at the end `#ffb454`; joint5 (wrist)
    highlight `#d2a8ff` when it moves;
  - camera = FOV wedge `fill="#4fc3f7"` opacity .12 from robot front;
  - AprilTag = small square outline `stroke="#ffb454"` with corner ticks and
    id label; crosshair `(320,400)` target `+` marks `#7ee787`;
  - buzzer glyph = small circle + 2-3 concentric arcs `#ffb454` when beeping,
    dim `#484f58` when off;
  - keyboard glyph = small rounded rect with the pressed key letter `#e6edf3`
    on `#161b22`.
  Small labels inside the stage: monospace 5.8, `#8b949e`; values `#e6edf3`.
- Bottom 3 Bangla lines (always present, always exactly three):
  `<text x="16" y="262" font-family="Hind Siliguri, sans-serif" font-size="7.2" fill="#e6edf3">…</text>`
  `<text x="16" y="273" font-family="Hind Siliguri, sans-serif" font-size="7.2" fill="#8b949e">…</text>`
  `<text x="16" y="284" font-family="Hind Siliguri, sans-serif" font-size="7.2" fill="#8b949e">…</text>`
  Line 1 = current action in plain words; lines 2-3 = consequence/context.
  NO arrows, no emoji — readable Bangla.

Shared defs (already in the engine, usable by id): gradients `egB`, `egW`,
marker `ea` (small arrowhead — usable on PATHS, never as text).
Palette: #4fc3f7 blue · #7ee787 green · #ffb454 amber · #d2a8ff purple ·
#ff7b72 red · #e6edf3 fg · #8b949e mid · #6e7681 dim · #484f58 faint ·
#161b22 card · #0d1117 stage · #21262d/#30363d borders.
Rules: every tag closed, every attribute quoted, no `<`/`>` inside text nodes
(use `&lt;`/`&gt;`), coordinates within 440×330, no `<script>`, no external
refs, no ids other than egB/egW/ea (ids must stay unique — do not re-declare
them inside rob). Keep each rob ≤ ~2.5 KB; short and legible beats dense.

## Sequence context (all units) — the 423-step spine

U1 rd1-3 + gmapping L1-23 (14) · U2 gmapping L24-49 eager paths (11) ·
U3 gmapping imu+list+5 run events (15) · U4 rd4-5 + slam_view L1-29 (11) ·
U5 slam_view rviz + 2 events (9) · U6 rd6-7 + keyboard L1-65 (19) ·
U7 keyboard class L66-121 (20) · U8 keyboard L122-242 defined (17) ·
U9 keyboard main pass (16) · U10 key waves i/u/q/1 (17) · U11 waves g/r/SPACE
(15) · U12 waves s/s2/deadman/Ctrl+C (22) · U13 rd8-9 + camera ctor+run (17) ·
U14 rd10-11 + follow_line L1-58 (16) · U15 L59-115 ctor tail (22) ·
U16 L116-244 callbacks (27) · U17 L245-321 execute+process head (22) ·
U18 L322-431 process tail+helpers (21) · U19 follow_line main pass (29) ·
U20 waves joy/scan/sync (24) · U21 waves obstacle/clear/apriltag (28) ·
U22 grasp+halt + rd12-15 (13) · U23 save_map ctor+run (18).

Incoming/outgoing panel + dbg state each unit MUST match:
- U1 ends: TERMINAL `sh start_agent.sh` ran (illustrative) + gmapping launch
  line echoed; SYSTEM: robot on, parser entering gmapping ctor; imports bound,
  dead lists built (dbg import/module rows).
- U2 ends: FOUR share-path strings resolved (dbg path rows, ill); nothing
  launched; SYSTEM still idle robot + "5 entries pending".
- U3 ends: FIVE entries fired — merger, filter, imu, ekf, gmapping; SYSTEM
  shows dual-laser fused `/scan` + growing occupancy map + EKF fuse icon;
  TERMINAL launch running (no prompt back). dbg entry/node rows.
- U4 ends: slam_view command echoed; imports (incl. 7 unused) bound;
  use_sim_time string bound.
- U5 ends: RViz window open with slam_rviz.rviz, `/map` + `/scan` visible;
  TERMINAL rviz line.
- U6 ends: keyboard command echoed; banner printed (msg L20-45 compiled —
  the banner text appears when main runs, U9); bindings dicts compiled;
  dbg pass=import.
- U7 ends: class head through step_arm_joint body compiled; pubs/params/
  clamps all struct — "define-only" voice.
- U8 ends: file fully defined incl. emergency_stop + main; nothing ran
  beyond module level.
- U9 ends: node LIVE `yahboom_keyboard_ctrl`, pubs cmd_vel/arm_joint/
  arm6_joints, limits 1.0/5.0 read, reset_arm published `[90,90,0,0,90,90]`
  time 2000, banner + vels printed, loop parked at getKey. dbg node/pub/
  param/arm_joints rows.
- U10 ends: '1' wave — wheels carrying (0.20, 0.00, 0.00) while joint1
  85-deg msg on /arm_joint; dbg linear.x 0.20, joint 85.
- U11 ends: SPACE wave — e-stop engaged: zero Twist + arm brake time 100;
  dbg twist (0.00,0.00,0.00), arm_msg time 100.
- U12 ends: Ctrl+C halt — clean finally, no [ERROR]; TERMINAL prompt back;
  dbg exit=clean.
- U13 ends: camera include fired (orbbec driver up) + kin_ik_fk service up
  (illustrative); SYSTEM: camera FOV + arm service icon.
- U14 ends: follow_line command echoed; import pass through L58 — `import
  finish` L13 printed, wildcard supplies cv/color_follow/simplePID (their
  internals NOT in this folder — illustrative), class head compiled.
- U15 ends: ctor tail compiled through L115 (struct voice): pubs/subs/sync/
  Detector/state — the L52-55 blocking wait is defined-not-running here.
- U16 ends: callbacks compiled (registerScan cone, JoyState, get_grasp,
  pubSixArm, declare_param, PID_init, onMouse); dbg dormant rows.
- U17 ends: execute + process head compiled; the PID/deadzone/buzzer
  arithmetic is SOURCE TEXT now — numbers come alive in U20/U21.
- U18 ends: file fully defined incl. remove_obstacle swap, Reset typo
  ("Reset succes!!!" — source, never fix), get_param never-called.
- U19 ends: ctor LIVE follow_line: BLOCKING WAIT entered then released
  (subscriber appears, illustrative), pubSixArm x2, Detector built, 18
  params declared+read (Kp 60 read — flag the never-wired fact ONCE),
  `Init Done.` + 60/0.25 prints, spin parked. dbg param rows.
- U20 ends: sync wave — frame F3 published (0.1, +0.1875); dbg point_x 380,
  z_Pid +0.1875, linear.x 0.1, deadzone pass.
- U21 ends: apriltag wave — R1 clamp creep + centered + joint5 twice; dbg
  tags 1, c_dist e.g. 0.42 m (ill), Track_state Remove->done; front_warning
  12->0 with beep 1->0 (3x) shown across obstacle->clear.
- U22 ends: follow_line halted clean (zero Twist), then rd12-15 typed: arm
  topic-pub --once (one shot, subscriber illustrative) + save_map command
  echoed.
- U23 ends: map_saver fired ONE-SHOT — yahboom_map.yaml/.pgm written
  (illustrative), launch exits, TERMINAL prompt back; dbg map/free/occ rows;
  final rob: complete grid snapshot + robot parked. dbg exit=clean.

## Global prohibitions

No emoji. No UNICODE arrow characters anywhere (ASCII `->` is fine). No Bangla
numerals in dbg values or SVG text (prose may use ৪২৩-style sparingly). No
invented vendor internals — start_agent.sh, follow_common (color_follow/
simplePID/read_HSV/write_HSV/ManyImgs/cancel/compute_joint5), ira_laser_tools,
yahboom_laser_filter, robot_localization ekf, slam_gmapping, orbbec driver,
arm driver are NOT in this folder: any claim about their internals must carry
illustrative/inferred. Never "fix" source bugs (duplicate Node import, dead
lists L17-19, unused imports slam_view L2-12, /JoyState duplicate sub L38/L40,
dead depth block L161-165, linear 0.2->0.18 never used, Kp 60 never wired,
joint5 published twice L375-376, "Reset succes!!!" typo, gpshd dead in
save_map) — narrate them where the trace crosses them, once, never dwelt on.
Never claim gmapping.launch.py starts the keyboard/follow nodes (README does
that, L7/L11). gmapping's `ekf` include is `robot_localization` EKF fusing
imu+odometry (illustrative chain). The 0.375 threshold is ResponseDist*1.5 —
show the arithmetic. `ros2 topic pub` L13 payload is malformed-ish YAML-ish
(one string, source as-is) — quote verbatim, never fix. map_saver_cli is the
only self-terminating command — its run phase ends with process exit, not a
parked spin. Never draw a Unicode arrow; use triangle paths or ASCII `fwd`.
The keyboard node's cmd_vel publisher is RELATIVE 'cmd_vel' (L71) — resolved
against the node namespace, default `/cmd_vel`; keep one cap accurate about it.
