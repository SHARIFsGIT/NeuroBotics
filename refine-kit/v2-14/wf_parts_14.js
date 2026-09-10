export const meta = {
  name: 'parts-14',
  description: 'Author 15 v1 Parts for folder 14 SLAM Gmapping (author -> adversarial verify -> fix, waves of 5)',
  phases: [
    { title: 'Wave1', detail: 'parts 1-5: README, gmapping x2, slam_view, keyboard bindings' },
    { title: 'Wave2', detail: 'parts 6-10: keyboard class/main, camera, follow_line head' },
    { title: 'Wave3', detail: 'parts 11-15: follow_line body + save_map' },
  ],
}

const KIT = '/home/shariful/NeuroBotics/refine-kit/v2-14'
const SRC = '/home/shariful/NeuroBotics/14. SLAM Gmapping'

const PLAN = [
 {n:1,  fname:'README.md',              lang:'bash',   start:1,   end:15,  anim:'runbook14', math:false, en:'Runbook — Eight Commands, One Map',
  focus:'8 commands on ODD lines 1/3/5/7/9/11/13/15 (blanks between). Chronology: start_agent environment -> gmapping 5-program SLAM stack -> slam_view RViz -> yahboom_keyboard teleop -> camera_arm_kin -> follow_line -> L13 one-shot /arm6_joints pub {joint1:90, joint2:140, joint3:20, joint4:10, joint5:90, joint6:180, time:1500} --once (inline YAML unquoted, as-is) -> save_map. Drive-then-save story: map only grows while the robot MOVES.'},
 {n:2,  fname:'gmapping.launch.py',     lang:'python', start:1,   end:49,  anim:'chain14',   math:false, en:'Imports & Four Eager Paths',
  focus:'Duplicate `from launch_ros.actions import Node` at L2 AND L9 (source note L11 admits it); L3 LaunchConfiguration + L4 DeclareLaunchArgument imported never used; L15-19 dead template lists declared_arguments/declared_env_vars/declared_parameters (comment L15-16 says leftover); FOUR eager os.path.join paths INSIDE generate_launch_description: L24-28 ira_laser_tools merge_multi.launch.py (dual-lidar stitch, /scan fused 360, folders 10-13 lineage), L31-35 yahboom_laser_filter laser_filter_node.launch.py (strips robot body), L38-42 ekf_bringup ekf.launch.py, L45-49 slam_gmapping slam_gmapping.launch.py. Missing package => PackageNotFoundError BEFORE anything starts.'},
 {n:3,  fname:'gmapping.launch.py',     lang:'python', start:51,  end:94,  anim:'ekf14',     math:false, en:'IMU Remap & the Five-Program Launch',
  focus:'L53-62 the ONE direct Node: imu_filter_madgwick / imu_filter_madgwick_node, remappings=[("/imu","/imu/data_raw")] at L60 — source metaphor L56-59 mail forwarder; name L61. L66-93 LaunchDescription with EXACTLY 5 entries in order: merger include L69-71, filter include L74-76, imu node bare L79, ekf include L82-84, gmapping include L90-92. Data flow: merger -> /scan -> gmapping; imu /imu -> /imu/data_raw -> EKF (+wheel odom) -> /odometry/filtered -> gmapping; gmapping needs BOTH.'},
 {n:4,  fname:'slam_view.launch.py',    lang:'python', start:1,   end:59,  anim:'rviz14',    math:false, en:'RViz — Watching the Map Grow',
  focus:'Self-acknowledged unused imports L2-3 (IfCondition, ExecuteProcess, SetRemap, FindPackageShare, Shutdown, UnlessCondition, PythonLaunchDescriptionSource, IncludeLaunchDescription all unused); L24 use_sim_time default false (real robot wall clock); L30-34 rviz_config default slam_mapping/rviz/slam_rviz.rviz; L37 DeclareLaunchArgument; L41-52 rviz2/rviz2 name rviz2 output screen arguments [-d rviz_config, use_sim_time]; L56-59 two-entry return.'},
 {n:5,  fname:'yahboom_keyboard.py',    lang:'python', start:1,   end:64,  anim:'teleop14',  math:true,  en:'Menu & Key Bindings',
  focus:'L17-45 menu string (base i/, j/l rotate, a/d strafe mecanum, u/o/m/. diagonals, arm 1-0 ±5 deg, g/h gripper, SPACE e-stop, s pause toggle, r home, q/z w/x e/c speed ±10%, CTRL+C); L48-58 moveBindings key->(forward_back, strafe, rotate) unit ints — quirk: M mirrors , (both back), m = back-LEFT diagonal, . = back-right; u=(1,1,0). L60-64 speedBindings (linear_factor, angular_factor) 1.1/0.9. MATH: repeated ×1.1 growth 0.2*1.1^n vs clamp 1.0 (L190), turn 1.0*1.1^n vs 5.0; and twist = speed × unit int later.'},
 {n:6,  fname:'yahboom_keyboard.py',    lang:'python', start:66,  end:148, anim:null,       math:true,  en:'Node Constructor, Raw Keys & Arm Safety',
  focus:'L71 cmd_vel publisher topic is RELATIVE name (resolves under namespace) depth 1; arm_joint depth 100 ArmJoint + arm6_joints depth 100 ArmJoints; L76-79 declare linear_speed_limit 1.0 angular_speed_limit 5.0 read to attrs; L82 home [90,90,0,0,90,90]; L83 termios.tcgetattr; L86 reset_arm at construction (arm homes on node start); L88-96 getKey: tty.setraw, select 0.1 s timeout ~10 Hz, read(1), tcsetattr TCSADRAIN — Ctrl+C arrives as \\x03 raw not SIGINT; L98-99 vels f-string; L101-121 step_arm_joint: += delta then CLAMPS j5 0..270 (max(0,min(270,...))), j6 30..180, others 0..180; ArmJoint id/joint=int/time=500; action words Up/Down, joint6 Open/Close; L123-134 reset_arm time=2000; L136-148 emergency_stop zero Twist + current joints time=100, no print. MATH: clamp min/max boundary cases.'},
 {n:7,  fname:'yahboom_keyboard.py',    lang:'python', start:150, end:242, anim:null,       math:true,  en:'Main Loop — Drive, Pause, Emergency',
  focus:'L151-158 init: node yahboom_keyboard_ctrl, speed/turn 0.2/1.0, x/y/th 0, stop False, count 0; L161-162 print menu+vels; loop: s/S TOGGLE stop (+emergency_stop entering, x y th zero); SPACE one-shot e-stop (does NOT latch stop); elif not stop: moveBindings -> x,y,th count=0; speedBindings -> ×factors + min() clamp upper-only (×0.9 forever approaches 0, never negative), print vels; 1-0 arm ±5; g/G close h/H open; r/R reset; else count+=1, >4 => x,y,th=0 (deadman), \\x03 break; paused else: only \\x03 or pause msg; L226-228 EVERY iteration twist.linear.x=speed*x, linear.y=speed*y (strafe), angular.z=turn*th; L230-233 running -> publish twist, paused -> publish Twist() zero at ~10 Hz; finally emergency_stop + tcsetattr restore + destroy + shutdown. MATH: deadman 5 empty polls × 0.1 s = 0.5 s to auto-stop; publish cadence 10 Hz.'},
 {n:8,  fname:'camera_arm_kin.launch.py', lang:'python', start:1, end:40,  anim:null,       math:false, en:'Camera Driver & Arm Kinematics Service',
  focus:'L2-7 imports with inline beginner comments; L17-23 camera_driver_launch = IncludeLaunchDescription(PythonLaunchDescriptionSource([os.path.join(get_package_share_directory("orbbec_camera"), "launch"), "/dabai_dcw2.launch.py"]) — LIST argument (substitution list concatenated), different style from gmapping plain-string join; dabai = Orbbec model; L29-34 kin_node arm_kin/kin_srv name kin_ik_fk (srv = service, ik inverse + fk forward kinematics); L40 two-entry return.'},
 {n:9,  fname:'follow_line.py',         lang:'python', start:1,   end:57,  anim:null,       math:true,  en:'Imports, Wildcard & the Blocking Arm Wait',
  focus:'L11 from M3Pro_demo.follow_common import * WILDCARD supplies cv (L14-15 BEFORE cv2 import L17!), time, simplePID, color_follow, read_HSV/write_HSV, ManyImgs, and self.cancel() at L301 — vendor module not in folder, internals illustrative; L12 RAD2DEG = 180/math.pi; L13 print space-before-paren; L19 TimeSynchronizer imported unused; L21 encoding list only [1] used; L22 dt_apriltags; L25 arm_interface AprilTagInfo CurJoints; L26 compute_joint5 wildcard. L34-36 pubs /cmd_vel /linefollow/rgb /beep; L38-40 DUPLICATE sub_JoyState (same /JoyState sub created twice, second replaces first attribute — template scar, net one live sub) around L39 /scan1 registerScan (RAW single lidar, NOT merged /scan); L42-50 message_filters subs + pubs incl TargetJoint6_pub never published (dead), /action_feedback String; L51 init_joints [90,90,12,20,90,0]; L52-55 BLOCKING while not get_subscription_count(): pubSixArm + sleep(0.1) — constructor stalls until arm driver subscribes arm6_joints, publishing home pose every 0.1 s; L55 final pubSixArm; L56-57 ApproximateTimeSynchronizer queue 1 slop 0.5 s registerCallback. MATH: RAD2DEG identity 57.29578 like FACTS §8.'},
 {n:10, fname:'follow_line.py',         lang:'python', start:58,  end:145, anim:null,       math:true,  en:'Detector, State Defaults & Scan Callback',
  focus:'L59-60 two CvBridge; L62-69 Detector(searchpath apriltags, families tag36h11, nthreads 8, quad_decimate 2.0, quad_sigma 0.0, refine_edges 1, decode_sharpening 0.25, debug 0); L70-71 flags; L73 declare_param() call; L74-97 defaults: Track_state identify (NOT init!), warning=1 dead, hsv_text absolute /home/jetson/.../LineFollowHSV.text, color_follow(), scale 1000, FollowLinePID (50,0,10), RemovePID (40,0,15.0), linear 0.2, PID_init(), img_flip False, L97 self.refresh double-space+tab; L99-114: pubCurrentJoints, tags [], joint6.data=120, start_time, count True, front_warning 0, Joy_active False AGAIN (L74 dup), prints LaserAngle 60 ResponseDist 0.25; L118-120 JoyStateCallback #1 isinstance guard; L122-131 registerScan: front_warning=0 per scan, angle=(angle_min+angle_increment*i)*RAD2DEG, cone (abs(angle)<LaserAngle*0.5 or abs(angle)>360-LaserAngle*0.5) with 60 => |a|<30 or >330, ranges[i]!=0.0, <= ResponseDist*1.5 = 0.375 m -> front_warning+=1; L134-137 pubCurrentJoints Curjoints; L140-145 grasp callback resumes tracking. MATH: cone inequality incl wrap side, 0.25*1.5.'},
 {n:11, fname:'follow_line.py',         lang:'python', start:147, end:230, anim:null,       math:true,  en:'Synced Frames, Arm Mirror & Parameters',
  focus:'L148 Chinese comment verbatim + translate in prose; L149-155 rgb8 + np.copy + depth 32FC1 + resize 640x480 + self.depth_image_info float32 (mm); L157-159 detect(cvtColor RGB2GRAY, False, None, 0.025) sorted tag_id draw_tags red/green; L161-165 DEAD DUPLICATE second depth conversion into local never used; L166 waitKey(1); L167-170 3-second arming count/Start_ -> tracking; L171-174 process + RGB2BGR + imshow ManyImgs; L176-185 pubSixArm MIRROR joint1 = 180 - joints[0] (90->90 but 60->120), runtime default 2000, id/angle params unused; L187-218 declare_param ALL declare+read: HSV H0/S85/V126/H9/S253/V253 RED line, Kp 60 Ki 0 Kd 20 NEVER WIRED (tuple 50,0,10 wins; get_param would rebuild but never called), scale 1000, LaserAngle 60 int, linear 0.18 OVERWRITES L93 0.2 (effective 0.18), ResponseDist 0.25, refresh False; L220-230 PID_init simplePID Kp 50/1000=0.05 Ki 0 Kd 10/1000=0.01 targets [0,0]; Remove Kp 0.04 Kd 0.015 both channels. MATH: /1000 scaling derivation.'},
 {n:12, fname:'follow_line.py',         lang:'python', start:232, end:290, anim:'steer14',  math:true,  en:'Mouse ROI & the Steering Brain',
  focus:'L232-243 onMouse event 1 down -> init/select/Mouse_XY, event 4 up -> mouse, cols/rows min/max Roi_init; L245-252 Joy_active -> PID_init once + return (pause re-inits PID), Start_state=True normal path; L253-257 radius 0 line lost: Not Found + /action_feedback String follow_line_clear_future_done + Twist() stop; L258-289: z_Pid from update([(point_x-320)*1.0/16, 0]); img_flip -> -z else +z; L269 linear.x = 0.1 HARDCODED (self.linear 0.18 param dead for driving); L270-275 front_warning > 10 -> Obstacles ahead + stop + Buzzer_state + b.data=1; L276-280 else buzzer clear ×3; L282-284 deadzone abs(point_x-320)<40 -> angular.z=0.0; L285-289 Joy_active False -> publish else z=0 dead branch never publishes. MATH: pixel error /16 => PID input, ±40 px deadzone straightens, 11+ beams inside 0.375 m stops.'},
 {n:13, fname:'follow_line.py',         lang:'python', start:291, end:380, anim:'states14', math:true,  en:'State Machine — Init, Identify, Track, Remove',
  focus:'L293-297 resize + flip + keys action 32 SPACE->tracking, i/105 identify, r/114 Reset, q/113 cancel() WILDCARD-else-AttributeError; L302-314 init: namedWindow AUTOSIZE + setMouseCallback, select -> line+rectangle, Roi non-degenerate -> color.Roi_hsv -> hsv_range dyn_update, else stays init; L315-318 identify: hsv_text exists -> read_HSV reuse else init; L319-333 line_follow -> (rgb, binary, circle), dyn_update -> write_HSV + 6 Parameters + set_parameters; L334-340 tracking: circle -> threading.Thread(execute, circle[0], circle[2]) NEW THREAD PER FRAME, else Start_state False (L339 commented publish); L341-345 AprilTag pivot len(tags)>0 and != Remove -> identify + Twist stop + Find the apriltag + Remove; L346-379 Remove: adjusting (|cx-320|>10 or |cy-400|>10) and move_flag -> remove_obstacle; centered both <10 -> pubVel(0,0) + start crawling + sleep(3) BLOCKS + c_dist = depth[int(cy),int(cx)]/1000 mm->m; valid + pubPos_flag -> flags off, AprilTagInfo id/x/y/z, vx/vy corners[0]-corners[1], compute_joint5(vx,vy), joint5 int, publishes PosInfo + joint5 TWICE L375+L376; else Invalid distance. MATH: centering ±10 px around (320,400), mm/1000.'},
 {n:14, fname:'follow_line.py',         lang:'python', start:382, end:485, anim:null,       math:false, en:'Helpers, Reset & Main Shutdown',
  focus:'L382-387 pubVel sets linear.x AND linear.y (mecanum strafe); L389-395 remove_obstacle [y,x] = update([ (px-320)/10.0, (py-400)/10.0 ]) DESTRUCTURING SWAP (ch0 lands in y), clamps ±0.10 both, pubVel(x,y) — linear.x gets ch1 output, as-is; L397-399 JoyStateCallback #2 identical, second definition wins; L403-410 Reset PID_init/init/()/False/(0,0)/Twist/print Reset succes!!! TYPO AS-IS; L412-430 get_param re-reads + rebuilds FollowLinePID NEVER CALLED; L433-470 main banner BEGINNER STARTUP SCREEN pure prints + rclpy.init + LineDetect(follow_line) CONSTRUCTOR BLOCKS HERE on arm wait + OK prints; L471-474 spin except KeyboardInterrupt; L475-485 finally zero Twist + destroy + shutdown.'},
 {n:15, fname:'save_map.launch.py',     lang:'python', start:1,   end:49,  anim:'savemap14', math:true,  en:'Saving the Map — Free 0.196, Occ 0.65',
  focus:'L5 get_package_share_directory imported UNUSED, L8 get_package_share_path the used one; L14 map_name yahboom_map; L18 default_map_path M3Pro_navigation/map/yahboom_map; L23-27 map_arg DeclareLaunchArgument map_path str(default) description; L31-42 map_saver_node nav2_map_server/map_saver_cli arguments [-f LaunchConfiguration(map_path), --free 0.196, --occ 0.65] — source comments L39-40 phrase free as less than 19.6% sure wall -> White, occ more than 65% -> Black, BETWEEN stays unknown gray; map_saver_cli ONE-SHOT saves PGM+YAML then exits; L46-49 two-entry return. MATH: trichotomy p<=0.196 free 0, p>=0.65 occupied 100, else unknown -1.'},
]

const META = {type:'object', required:['file','bytes'], properties:{file:{type:'string'}, bytes:{type:'integer'}, concerns:{type:'string'}}}
const VERDICT = {type:'object', required:['verdict','issues','summary'], properties:{
  verdict:{type:'string', enum:['pass','fail']},
  issues:{type:'array', maxItems:40, items:{type:'object', required:['loc','problem'], properties:{
    loc:{type:'string'}, problem:{type:'string'}, fix_hint:{type:'string'}}}},
  summary:{type:'string'}}}
const FIX = {type:'object', required:['file','fixed_count'], properties:{file:{type:'string'}, fixed_count:{type:'integer'}, remaining_concerns:{type:'string'}}}

const PRE = `You are authoring ONE Part of the v1 layer of a Bangla ROS 2 line-by-line code-analysis app for folder "14. SLAM Gmapping".
BINDING, read before writing:
1. ${KIT}/FACTS-14.md (ground truth — canonical numbers live in §8, quirks in §9, conventions in §10)
2. The source file (READ-ONLY; modifying it is a hard failure): ${SRC}/<fname below>
3. Genre calibration (match DENSITY and VOICE, never their folder-13 facts): ${KIT}/../v2-13/parts/part-01.json (README part), part-05.json (math-bearing import part), part-03.json (launch-include part).
Output: write EXACTLY one file ${KIT}/parts/part-NN.json (UTF-8, real Bangla chars, ensure_ascii false). Nothing else; never touch the source folder.

SCHEMA (exact keys, same as calibration files):
{"n":NN,"id":"part-NN","fname":"<file>","enTitle":"<given>","lang":"<given>","start":S,"end":E,"flags":[],
 "explain":[{"a":<line>,"b":<line>,"text":"Bangla..."},...],
 "math":null | {"intro":"...","levels":[{"label":"Level 1 — ...","latex":"\\\\[ ... \\\\]","text":"..."},...],
   "numeric":[{"latex":"...","text":"..."},...],"mapping":[{"code":"<exact source expr>","math":"\\\\( ... \\\\)","text":"..."},...],
   "failure":["...","..."]},
 "robot":{"correct":"...","incorrect":"..."},
 "animType":null | "<given>"}

RULES:
- explain ranges tile start..end EXACTLY: contiguous, non-overlapping, ascending, EVERY line covered (dense Python: 2-6 lines per entry; launch/readme: 1-3). Big parts (57-104 lines) need ~14-25 entries.
- Every <code> quote is a CHARACTER-EXACT substring of the real source (follow_line.py uses TAB indentation — preserve tabs; trailing tabs/spaces preserved where you quote them).
- Line numbers REAL (gutter never renumbered). Facts only from source + FACTS-14; vendor/follow_common internals ILLUSTRATIVE and said so.
- Bangla prose; English technical terms Latin with hyphen-suffix (PID-টি, scan-এ, launch-এর). Tolerated transliterations ONLY টেস্ট/রেজিস্টার/ডিগ্রি/স্কিপ/রিসেট/স্টিয়ারিং. No emoji. No Unicode arrows anywhere in this layer.
- Quirks (FACTS §9) explained as-is, never "fixed" in quotes.
- math: ONLY if plan says math:true — else null. levels 2-4 progressive; numeric 1-3 worked examples with REAL source numbers; mapping 2-4 code->formula pairs; failure 1-2 wrong-sign/wrong-constant intuitions.
- robot: correct = what really happens on the physical robot; incorrect = the classic wrong expectation, grounded in THIS code.
- animType: exactly the plan value (null if none).
Self-check before finishing: JSON parses; ranges tile exactly; spot-check 6 quotes char-exact against source.
Return metadata only: {"file":"part-NN.json","bytes":<size>,"concerns":"..."}`

const AUTHOR = (p) => PRE.replace('NN', String(p.n).padStart(2,'0')).replace('<fname below>', p.fname)
 + `

YOUR PART: n=${p.n}, fname=${p.fname}, lang=${p.lang}, start=${p.start}, end=${p.end}, enTitle="${p.en}", animType=${p.anim ? `'${p.anim}'` : 'null'}, math=${p.math ? 'REQUIRED (see plan focus for the derivation)' : 'null'}.
FOCUS FACTS (weave these; full depth in FACTS-14): ${p.focus}`

const VERIFY = (p) => `You are an ADVERSARIAL verifier for ${KIT}/parts/part-${String(p.n).padStart(2,'0')}.json (folder "14. SLAM Gmapping" v1 layer).
Read first: ${KIT}/FACTS-14.md, the source ${SRC}/${p.fname}, the part file, calibration ${KIT}/../v2-13/parts/part-05.json.
Expected frame: n=${p.n} fname=${p.fname} start=${p.start} end=${p.end} anim=${p.anim} math=${p.math}.
Hard checks (any failure => verdict fail):
1. JSON parses; keys exactly the schema; fname/lang/start/end/animType match the frame; explain ranges tile start..end contiguously with NO gaps/overlaps.
2. Quote fidelity: for >=10 entries, every <code> fragment is a character-exact substring of the real source at those lines (tabs preserved; follow_line L44/L95/L97/L131 trailing tabs, keyboard L185 tab, gmapping trailing spaces).
3. Fact safety: canonical numbers match FACTS-14 §8 (50/0/10 -> 0.05/0/0.01; 40/0/15.0 -> 0.04/0.015; 60-deg cone |a|<30 or >330; 0.375 m; front_warning>10; /16 error; ±40 px; ±10 px centering at (320,400); depth /1000; 0.196/0.65; limits 1.0/5.0; factors 1.1/0.9; clamps j5 0-270 j6 30-180; times 500/2000/100; linear.x hardcoded 0.1; Kp 60 dead; linear param 0.18 effective-but-unused). No invented vendor internals; quirks from FACTS §9 preserved not fixed.
4. Bangla style: English technical terms Latin hyphen-suffix; NO emoji; NO Unicode arrows; only the 6 tolerated transliterations; Bangla text natural.
5. math block (if required): LaTeX delimiters \\\\[, \\\\], \\\\(, \\\\) balanced; levels progressive; numeric uses REAL source numbers; mapping code strings are source-exact; failure entries are wrong-input intuitions. If plan says math:false, math MUST be null.
6. robot: correct/incorrect grounded in this code (no forward-driving claims for pause paths, no invented hardware behavior).
Report every defect {loc:"explain[i] a-b" | "math.levels[1]" | "robot.correct" | ..., problem, fix_hint}. Write nothing to disk.
Return verdict pass only if zero blocking issues.`

const FIXER = (p, issues) => `You are the repair agent for ${KIT}/parts/part-${String(p.n).padStart(2,'0')}.json (folder 14 v1 layer). It failed verification:
${issues}
Read ${KIT}/FACTS-14.md, source ${SRC}/${p.fname}, and the part file. Repair EXACTLY the flagged elements (and direct collisions); leave passing elements byte-identical. Keep schema, tiling, and all rules (quotes char-exact, Bangla style, no arrows/emoji).
Overwrite the same path with the full corrected JSON. Re-run the author self-check.
Return {"file":"part-NN.json","fixed_count":<n>,"remaining_concerns":"..."}.`

const waves = [PLAN.slice(0,5), PLAN.slice(5,10), PLAN.slice(10,15)]
const all = []
for (let w = 0; w < waves.length; w++) {
  phase(['Wave1','Wave2','Wave3'][w])
  log(`wave ${w+1}: parts ${waves[w][0].n}-${waves[w][waves[w].length-1].n}`)
  const res = await pipeline(waves[w],
    (p) => agent(AUTHOR(p), {label:`part-${String(p.n).padStart(2,'0')}:author`, phase:['Wave1','Wave2','Wave3'][w], schema:META}),
    async (meta, p) => {
      if (!meta || !meta.file) return {n:p.n, status:'author-died', concerns:meta ? meta.concerns : ''}
      const v = await agent(VERIFY(p), {label:`part-${String(p.n).padStart(2,'0')}:verify`, phase:['Wave1','Wave2','Wave3'][w], schema:VERDICT})
      return {n:p.n, meta, verdict:v}
    },
    async (r, p) => {
      if (!r) return null
      if (r.status === 'author-died') return r
      if (r.verdict && r.verdict.verdict === 'pass') {
        log(`part-${String(p.n).padStart(2,'0')} PASS`)
        return {n:p.n, status:'pass', summary:r.verdict.summary, concerns:r.meta.concerns||''}
      }
      const issues = JSON.stringify((r.verdict && r.verdict.issues) || [{loc:'file', problem:'verifier died'}])
      log(`part-${String(p.n).padStart(2,'0')} fail (${((r.verdict&&r.verdict.issues)||[]).length}) -> fix`)
      const f = await agent(FIXER(p, issues), {label:`part-${String(p.n).padStart(2,'0')}:fix`, phase:['Wave1','Wave2','Wave3'][w], schema:FIX})
      return {n:p.n, status:(f && f.fixed_count !== undefined) ? 'fixed' : 'fix-failed',
              issues:((r.verdict&&r.verdict.issues)||[]).length, summary:r.verdict?r.verdict.summary:'none',
              fixed:f?f.fixed_count:0, concerns:(r.meta&&r.meta.concerns)||'', remaining:f?f.remaining_concerns:''}
    })
  all.push(...res.filter(Boolean))
}
const clean = all.filter(r => r.status === 'pass' || r.status === 'fixed')
log(`done: ${clean.length}/15 parts clean`)
return all
