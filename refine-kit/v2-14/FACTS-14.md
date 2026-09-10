# FACTS-14 — "14. SLAM Gmapping" ground truth (VERIFIED against sources 2026-08-30)

Folder: `/home/shariful/NeuroBotics/14. SLAM Gmapping/` — READ-ONLY. 7 files, 983 lines, ~38 KB.
This file is BINDING for both layers (v1 Parts + v2 exec spec). If anything here conflicts with a
source file, the SOURCE wins — but these facts were extracted from the sources directly, so a
conflict means one of them was mis-transcribed: fix this file first, then re-derive.

| file | lines | bytes | sha256-12 |
|---|---|---|---|
| README.md | 15 | 426 | 1246ab7881c6 |
| gmapping.launch.py | 94 | 3,421 | e9d107d1fa6d |
| slam_view.launch.py | 59 | 2,704 | ff4b1234ffdd |
| yahboom_keyboard.py | 242 | 9,040 | 536b2850bd2a |
| camera_arm_kin.launch.py | 40 | 2,375 | 6b2b105f277e |
| follow_line.py | 485 | 18,491 | 88a485372c54 |
| save_map.launch.py | 49 | 2,099 | 3601e4887d57 |

`wc -l` prints the same numbers here (all files end with a newline). follow_line.py is indented with
real TAB characters (399 lines contain tabs) — quoted code MUST preserve them. Trailing-whitespace
quirks that MUST survive quoting: gmapping L15/L20/L22/L36/L43/L50/L56/L67/L77/L80/L85;
follow_line L44 (`joints", 10)\t\t`), L50 (`_feedback',1)\t`), L62, L70, L95 (`PID_init()\t`),
L97 (`self.refresh  = False\t` — TWO spaces before `=`), L129, L131 (`arning += 1\t\t\t`), L133
(whole line = one tab), L139, L156, L158, L160, L225, L230, L231, L253, L281, L289, L311;
keyboard L185 (`count = 0\t`) + 21 more indentation-only tabs. follow_line L148 comment is Chinese
(`# 将画面转为 opencv 格式` = "convert the image to opencv format") — quote verbatim, translate in prose.

## §1 README.md — the 8-command SLAM journey (runbook chronology)

Commands sit on ODD lines 1/3/5/7/9/11/13/15, blanks between:

1. L1  `sh start_agent.sh` — vendor agent (NOT in this folder; starts ROS environment)
2. L3  `ros2 launch slam_mapping gmapping.launch.py` — THE SLAM STACK (5 programs, §2)
3. L5  `ros2 launch slam_mapping slam_view.launch.py` — RViz viewer (§3)
4. L7  `ros2 run yahboomcar_ctrl yahboom_keyboard` — keyboard teleop node (§4)
5. L9  `ros2 launch M3Pro_demo camera_arm_kin.launch.py` — camera + arm math (§5)
6. L11 `ros2 run M3Pro_demo follow_line` — line-follow + AprilTag node (§6)
7. L13 `ros2 topic pub /arm6_joints arm_msgs/msg/ArmJoints {"joint1: 90, joint2: 140, joint3: 20, joint4: 10, joint5: 90, joint6: 180, time: 1500"} --once` — one-shot arm pose
   (the `{...}` YAML is unquoted in the source — as-is; arm_msgs is also the package of follow_line's ArmJoints)
8. L15 `ros2 launch slam_mapping save_map.launch.py` — persist the map (§7)

Chronology of the whole journey: start environment → start SLAM → look at it → drive (teleop or
line-follow) → save the map. L13's pub is a manual arm-pose demo between follow_line and save.

## §2 gmapping.launch.py — 94 lines, 5 programs, THE orchestrator

- Import block L1-11: L2 `from launch_ros.actions import Node` DUPLICATED at L9 (source's own note
  L11 admits it: "harmless, just a bit messy"). L3 `LaunchConfiguration` and L4
  `DeclareLaunchArgument` are imported and NEVER used. L5 os, L6 get_package_share_directory,
  L7 LaunchDescription, L8 PythonLaunchDescriptionSource, L10 IncludeLaunchDescription.
- L14 `def generate_launch_description():` — the entry point `ros2 launch` calls.
- L15-19 DEAD TEMPLATE LISTS: `declared_arguments = []`, `declared_env_vars = []`,
  `declared_parameters = []` — created, never read again (source comment L15-16 says so itself).
- FOUR EAGER `os.path.join` paths computed INSIDE the function (all before any program starts):
  - L24-28 `laser_merge_launch_file` = ira_laser_tools `launch/merge_multi.launch.py` (dual-lidar
    stitch → fused 360° /scan; same merger as folders 10-13)
  - L31-35 `laser_filter_launch_file` = yahboom_laser_filter `launch/laser_filter_node.launch.py`
    (strips robot-body hits)
  - L38-42 `ekf_odom_launch_file` = ekf_bringup `launch/ekf.launch.py` (Extended Kalman Filter odometry)
  - L45-49 `gmapping_launch_file` = slam_gmapping `launch/slam_gmapping.launch.py` (the SLAM core)
  If any of these 4 packages is missing, `get_package_share_directory` raises PackageNotFoundError
  at description-build time — launch dies BEFORE starting anything.
- L51-62 IMU filter is the ONE program started directly as a Node (no launch file):
  package `imu_filter_madgwick`, executable `imu_filter_madgwick_node`,
  `remappings=[('/imu','/imu/data_raw')]` L60 — the source's own metaphor L56-59: a mail
  forwarder; node publishes on /imu, consumer expects /imu/data_raw. `name='imu_filter_madgwick_node'` L61.
- L66-93 `return LaunchDescription([...])` — exactly 5 entries in order:
  1. L69-71 IncludeLaunchDescription(merger) — "Stitch the 360 radar together"
  2. L74-76 IncludeLaunchDescription(laser filter) — "Remove the robot's own body from the radar"
  3. L79 imu_filter_madgwick_node (bare Node)
  4. L82-84 IncludeLaunchDescription(EKF) — "Calculate exactly how far the robot has driven"
  5. L90-92 IncludeLaunchDescription(gmapping) — "Start Gmapping SLAM!"
- Data flow (for diagrams): merger → /scan (fused 360) → gmapping; imu node /imu→/imu/data_raw →
  EKF (with wheel odom) → /odometry/filtered → gmapping. Gmapping needs BOTH scan + odom to map.

## §3 slam_view.launch.py — 59 lines, RViz viewer

- L1-15 import block, self-documented L2-3 ("a lot of tools here that they didn't actually end up
  using... normal when copying from templates"). ACTUALLY UNUSED: L8's IncludeLaunchDescription +
  ExecuteProcess, L9 IfCondition + UnlessCondition, L11's SetRemap (Node IS used), L12
  FindPackageShare, L13 PythonLaunchDescriptionSource, L14 Shutdown. USED: Node, DeclareLaunchArgument,
  get_package_share_directory, LaunchDescription, LaunchConfiguration, os.
- L24 `use_sim_time = LaunchConfiguration('use_sim_time', default='false')` — real robot, wall clock.
- L30-34 `rviz_config = LaunchConfiguration('rviz_config', default=os.path.join(
  get_package_share_directory('slam_mapping'),'rviz','slam_rviz.rviz'))` — the pre-configured RViz layout.
- L37 `rviz_config_arg = DeclareLaunchArgument('rviz_config', default_value=rviz_config)`.
- L41-52 `rviz_node = Node(package='rviz2', executable='rviz2', name='rviz2', output='screen',
  arguments=['-d', rviz_config, use_sim_time])` — `-d` loads the config automatically; last arg
  passes use_sim_time through.
- L56-59 `return LaunchDescription([rviz_config_arg, rviz_node])` — 2 entries.

## §4 yahboom_keyboard.py — 242 lines, mecanum + 6-DOF arm teleop

- L5-13 imports: sys, select, termios, tty, time, rclpy, Node, Twist,
  `arm_msgs.msg import ArmJoint, ArmJoints` (BOTH single- and all-joint message).
- L17-45 `msg` menu string (printed in main): base i/, forward/back; j/l rotate; a/d strafe
  (mecanum); u/o/m/. diagonals; arm 1-0 joints ±5 deg per press (1/2 j1, 3/4 j2, 5/6 j3, 7/8 j4,
  9/0 j5), g/h gripper close/open; SPACE emergency stop; s pause/resume toggle; r arm home; q/z
  overall ±10%; w/x linear ±10%; e/c angular ±10%; CTRL+C quit.
- L48-58 `moveBindings` — key → (forward_back, strafe_left_right, rotate_left_right), unit ints.
  12 lowercase + uppercase twins for i , a d j l u o; NOTE 'M' mirrors ',' (back), 'm' is the
  diagonal back-left, '.' is back-right. E.g. 'u' = (1,1,0) forward-left diagonal.
- L60-64 `speedBindings` — key → (linear_factor, angular_factor): q/Q/z/Z (1.1,1.1)/(.9,.9),
  w/W/x/X (1.1,1)/(.9,1), e/E/c/C (1,1.1)/(1,.9).
- L66 `class YahboomKeyboard(Node)`; L67 `__init__(self, name)`; L68 `super().__init__(name)`.
- L71-73 publishers: `pub_cmd_vel` Twist 'cmd_vel' 1 (RELATIVE topic name — resolves under node
  namespace), `pub_arm_single` ArmJoint "arm_joint" 100, `pub_arm_all` ArmJoints "arm6_joints" 100.
- L76-79 parameters: declare linear_speed_limit 1.0, angular_speed_limit 5.0, read back to attrs.
- L82 `self.arm_joints = [90, 90, 0, 0, 90, 90]` home; L83 `settings = termios.tcgetattr(sys.stdin)`.
- L86 `self.reset_arm()` at construction — arm physically homes on node start.
- L88-96 `getKey`: `tty.setraw(sys.stdin.fileno())`, `select.select([sys.stdin],[],[],0.1)`
  (0.1 s timeout → ~10 Hz poll), `sys.stdin.read(1)`, restore termios `TCSADRAIN`. Raw mode:
  keys arrive WITHOUT Enter; Ctrl+C arrives as '\x03' instead of raising SIGINT.
- L98-99 `vels` f-string "Current Speed -> Linear: {speed:.2f} m/s | Angular: {turn:.2f} rad/s".
- L101-121 `step_arm_joint(joint_id, delta)`: `arm_joints[joint_id-1] += delta`; SAFETY CLAMPS —
  joint 5: `max(0, min(270, ...))` (0..270°), joint 6: `max(30, min(180, ...))` (30..180°),
  others: `max(0, min(180, ...))` (0..180°). Publishes ArmJoint {id, joint=int(...), time=500};
  prints "[ARM] Joint {id} -> {Up/Down, or Close side: Open/Close for joint 6} -> {deg} deg".
  action word: joint 6 → "Opening" if delta>0 else "Closing"; others "Up"/"Down".
- L123-134 `reset_arm`: arm_joints = [90,90,0,0,90,90], ArmJoints joint1..6 with time=2000, publish
  on arm6_joints, print "[SYSTEM] Arm reset to Home Position."
- L136-148 `emergency_stop`: 1) `pub_cmd_vel.publish(Twist())` zero Twist; 2) ArmJoints with the
  CURRENT positions and time=100 ("force immediate braking"). No print.
- L150-242 `main`: L151 `rclpy.init()`; L152 node "yahboom_keyboard_ctrl"; L154-158
  speed, turn = 0.2, 1.0; x, y, th = 0,0,0; stop = False; count = 0; twist = Twist().
  L160-162 print menu + vels. Loop L164:
  - L165 getKey
  - L168-173 's'/'S' TOGGLES stop; print "[SYSTEM] ALL CONTROLS PAUSED: {stop}"; entering pause →
    emergency_stop() + x,y,th = 0.
  - L176-179 ' ' (space) emergency_stop + zero + print "[SYSTEM] EMERGENCY STOP ENGAGED." —
    one-shot, does NOT set stop.
  - L182-223 `elif not stop:` (only when running):
    - L183-185 moveBindings hit → x,y,th = binding, count = 0
    - L186-192 speedBindings hit → speed *= f[0], turn *= f[1], count = 0, then CLAMP
      `speed = min(speed, linear_speed_limit)` (≤1.0), `turn = min(turn, angular_speed_limit)`
      (≤5.0) — upper clamp only, no lower bound (×0.9 forever approaches 0, never negative);
      print vels
    - L195-204 '1'..'0' → step_arm_joint(j, ±5) per menu
    - L207-208 'g'/'G' → step_arm_joint(6,-5) close; 'h'/'H' → step_arm_joint(6,+5) open
    - L210 'r'/'R' → reset_arm
    - L211-216 else: count += 1; count > 4 → x,y,th = 0 (deadman: ~5 empty polls stop motion);
      '\x03' → break
  - L219-223 else (paused): '\x03' → break; any non-empty key → "[SYSTEM] System paused. Press 's' to resume."
  - L226-228 EVERY iteration: twist.linear.x = speed*x, twist.linear.y = speed*y (strafe — mecanum),
    twist.angular.z = turn*th
  - L230-233 publish: running → twist; paused → `publish(Twist())` zero (keeps sending stop at ~10 Hz)
  - L235-236 except Exception → print "[ERROR] {e}"
  - L237-241 finally: emergency_stop(), `termios.tcsetattr(sys.stdin, TCSADRAIN, settings)`
    (restore terminal), destroy_node(), rclpy.shutdown()
- Quirk: while paused, arm keys are IGNORED (only s and Ctrl+C work) — pause is total.

## §5 camera_arm_kin.launch.py — 40 lines, camera + arm math

- L2-7 imports, each with an inline beginner comment (LaunchDescription "container", Node "start a
  single ROS 2 program", os, IncludeLaunchDescription, PythonLaunchDescriptionSource,
  get_package_share_directory "finds where a package is installed").
- L12 generate_launch_description. L17-23 PROGRAM 1 camera:
  `camera_driver_launch = IncludeLaunchDescription(PythonLaunchDescriptionSource([os.path.join(
  get_package_share_directory('orbbec_camera'), 'launch'), '/dabai_dcw2.launch.py']]))` — NOTE the
  LIST argument: PythonLaunchDescriptionSource receives `[joined_path, '/dabai_dcw2.launch.py']`
  (substitution list, concatenated) — a different style than gmapping's plain-string join.
  "dabai" = the Orbbec camera model (source comment L24: "likely the model name of your camera").
- L29-34 PROGRAM 2 math brain: `kin_node = Node(package='arm_kin', executable='kin_srv',
  name='kin_ik_fk')` — kinematics SERVICE (srv); ik = inverse, fk = forward kinematics.
- L40 `return LaunchDescription([camera_driver_launch, kin_node])` — 2 entries.

## §6 follow_line.py — 485 lines, the BIG node (line-follow + AprilTag + obstacle buzzer + arm)

### imports L1-27
- L2-6 rclpy/Node; std_msgs Bool,Int16,UInt16,String; Twist; CompressedImage, LaserScan, Image.
- L8-10 os, threading, math.
- L11 `from M3Pro_demo.follow_common import *` — WILDCARD. From it this file uses (none defined
  locally!): `cv` (L14-15!), `time` (L54, L106, L168, L356), `simplePID` (L221, L226),
  `color_follow` (L89), `read_HSV`/`write_HSV` (L317, L322), `ManyImgs` (L173), and `self.cancel()`
  (L301) must also live there or pressing 'q' raises AttributeError. Vendor module, not in this
  folder — say "follow_common থেকে আসে" and mark internals illustrative.
- L12 `RAD2DEG = 180 / math.pi` ≈ 57.29578. L13 `print ("import finish")` (space before paren).
- L14 `cv_edition = cv.__version__` uses wildcard cv BEFORE cv2's own import at L17; L15 prints it.
- L18 ArmJoints; L19 message_filters Subscriber, TimeSynchronizer (UNUSED), ApproximateTimeSynchronizer;
  L20 CvBridge; L21 `encoding = ['16UC1', '32FC1']` (only [1] used); L22 dt_apriltags Detector;
  L23 draw_tags; L24 numpy as np; L25 arm_interface.msg AprilTagInfo, CurJoints; L26
  `from M3Pro_demo.compute_joint5 import *` (compute_joint5, L368).

### constructor L28-115
- L34-36 pubs: `/cmd_vel` Twist 1, `/linefollow/rgb` Image 1, `/beep` UInt16 1.
- L38-40 subs: `/JoyState` Bool → JoyStateCallback (L38), `/scan1` LaserScan → registerScan (L39),
  then L40 RE-ASSIGNS `self.sub_JoyState` — the SAME /JoyState subscription created AGAIN; second
  object replaces the first attribute (rclpy unsubscribes the orphan on GC). Same topic+callback →
  net effect one live subscription; a template-edit scar, harmless but real.
- L42-43 message_filters Subscribers: `/camera/color/image_raw`, `/camera/depth/image_raw` (Image).
- L44-50 more pubs: `pub_SixTargetAngle` ArmJoints "arm6_joints" 10 (L44, trailing tabs);
  `pos_info_pub` AprilTagInfo "PosInfo" 1; `TargetJoint5_pub` Int16 "set_joint5" 10;
  `TargetJoint6_pub` Int16 "set_joint6" 10 (declared, NEVER published in this file — dead);
  `pub_cur_joints` CurJoints "Curjoints" 1; sub `grasp_done` Bool → get_graspStatusCallBack 100;
  `largemodel_arm_done_pub` String '/action_feedback' 1.
- L51 `init_joints = [90, 90, 12, 20, 90, 0]`.
- L52-55 **BLOCKING ARM WAIT**: `while not self.pub_SixTargetAngle.get_subscription_count():`
  `self.pubSixArm(self.init_joints)`; `time.sleep(0.1)` — constructor LOOPS (publishing the home
  pose every 0.1 s) until some node subscribes to arm6_joints (the arm driver from L9's launch).
  Until then the node never finishes init and never spins. Final L55 pubSixArm once more after.
- L56-57 `ApproximateTimeSynchronizer([rgb_image_sub, depth_image_sub], 1, 0.5)` — queue 1,
  slop 0.5 s; registerCallback(self.callback). Color+depth pairs within 0.5 s fire callback.
- L59-60 two CvBridge instances (rgb_bridge, depth_bridge).
- L62-69 `at_detector = Detector(searchpath=['apriltags'], families='tag36h11', nthreads=8,
  quad_decimate=2.0, quad_sigma=0.0, refine_edges=1, decode_sharpening=0.25, debug=0)`.
- L70-71 move_flag True, pubPos_flag True.
- L73 `self.declare_param()` (defined L187) — ALL parameters declared+read here.
- L74-97 state defaults: Joy_active False, img None, circle (), hsv_range (), Roi_init (),
  warning 1 (NEVER used again — dead), Start_state True, dyn_update False, Buzzer_state False,
  select_flags False, **Track_state 'identify'** (NOT 'init' — starts in identify!),
  windows_name 'frame', cols/rows 0,0, Mouse_XY (0,0),
  hsv_text "/home/jetson/yahboomcar_ws/src/M3Pro_demo/M3Pro_demo/LineFollowHSV.text" (absolute
  Jetson path), color = color_follow(), scale 1000, FollowLinePID (50, 0, 10), RemovePID
  (40, 0, 15.0), linear 0.2 (declare_param ran EARLIER at the L73 call writing 0.18 into
  self.linear; this L93 write is the LAST one — attribute ends 0.2), L94 commented LaserAngle, PID_init(),
  img_flip False, refresh False (L97 `self.refresh  = False` two spaces + tab).
- L99 pubCurrentJoints() — publishes CurJoints(init_joints) once.
- L100-110: tags [], depth_image_info [], joint5 Int16(), joint6 Int16(), joint6.data = 120,
  Start_ True, start_time = time.time(), count True, L108 commented ResponseDist, front_warning 0,
  Joy_active False (SECOND assignment — L74 duplicate).
- L111-114 prints: "Init Done.", "----------------------------", "self.LaserAngle:  60.0"? — NO:
  LaserAngle is declared INTEGER 60 → prints `60`; ResponseDist 0.25.

### callbacks L118-145
- L118-120 JoyStateCallback #1: `if not isinstance(msg, Bool): return; self.Joy_active = msg.data`.
- L122-131 registerScan: front_warning = 0 each scan; isinstance guard; `ranges = np.array(
  scan_data.ranges)`; per-beam `angle = (scan_data.angle_min + scan_data.angle_increment * i) *
  RAD2DEG`; **front cone**: `(abs(angle) < self.LaserAngle*0.5 or abs(angle) > 360 -
  self.LaserAngle*0.5)` with LaserAngle=60 → |angle|<30° or |angle|>330° (60° cone incl. the
  ±180 wrap side guard) **and** `ranges[i] != 0.0`; then `if ranges[i] <= self.ResponseDist * 1.5`
  → 0.25*1.5 = **0.375 m** → `front_warning += 1`. Subscribes /scan1 (raw single lidar, NOT the
  merged /scan!).
- L134-137 pubCurrentJoints: CurJoints with joints = init_joints, publish on Curjoints.
- L140-145 get_graspStatusCallBack: msg.data True → move_flag True, pubPos_flag True, and if no
  tags yet → Track_state = 'tracking' (upstream "grasp finished, resume following" handshake).

### synchronized callback L147-175
- L148 Chinese comment. L149 `rgb_image = self.rgb_bridge.imgmsg_to_cv2(color_frame,'rgb8')`;
  L150 np.copy. L152 depth with encoding[1]='32FC1'; L154 resize (640,480); L155
  `self.depth_image_info = depth_img.astype(np.float32)` (mm floats).
- L157 `self.tags = self.at_detector.detect(cv2.cvtColor(rgb_image, cv2.COLOR_RGB2GRAY), False,
  None, 0.025)`; L158 sorted by tag_id; L159 draw_tags (red corners, green center).
- L161-165 **DEAD DUPLICATE**: converts depth_frame a SECOND time into a LOCAL
  `depth_image_info` (L165) that is never used again — self.depth_image_info (L155) is the live one.
- L166 `action = cv2.waitKey(1)` — keyboard from the cv window.
- L167-170 3-second arming: `if self.count==True and self.Start_==True:` and
  `(time.time() - self.start_time)>3` → Track_state='tracking', count=False. After 3 s of synced
  frames the robot STARTS FOLLOWING by itself.
- L171 `result_img, bin_img = self.process(rgb_image, action)`; L172 RGB2BGR for display;
  L173-174 cv.imshow('frame', ManyImgs(1,([result_img, bin_img]))) or plain result_img if no binary.

### pubSixArm L176-185
`joints, id=6, angle=180.0, runtime=2000` (id/angle params UNUSED in body); ArmJoints with
**`joint1 = 180 - joints[0]`** (mirror! init 90 → 90, but 60 → 120), joint2..6 = joints[1..5]
direct, time = runtime. Publish on arm6_joints.

### declare_param L187-218 (ALL declare+immediate read)
- HSV: Hmin 0, Smin 85, Vmin 126, Hmax 9, Smax 253, Vmax 253 — a RED line (H 0-9).
- PID params: Kp 60, Ki 0, Kd 20 — **NEVER WIRED**: FollowLinePID tuple (50,0,10) from L91 is what
  PID_init uses; get_param() (L412) would rebuild the tuple from Kp/Ki/Kd but NOTHING calls
  get_param. Declared ≠ effective: Kp param 60, actual controller Kp 50.
- other: scale 1000, LaserAngle 60 (int), linear 0.18 (**declare_param is CALLED at L73, BEFORE
  L93: L214 writes 0.18 first, then L93's 0.2 is the LAST write — the attribute ends at 0.2 while
  the ros parameter stays 0.18; and neither value ever drives, execute() hardcodes 0.1 at L269**),
  ResponseDist 0.25, refresh False.

### PID_init L220-230 (called at L95 and re-called on Joy cycle / Reset)
- `PID_controller = simplePID([0,0], [50/1000, 0], [0/1000, 0], [10/1000, 0])` → Kp 0.05, Ki 0.0,
  Kd 0.01, 2-channel, targets [0,0].
- `Remove_PID_controller = simplePID([0,0], [40/1000, 40/1000], [0/1000, 0/1000],
  [15.0/1000, 15.0/1000])` → Kp 0.04, Ki 0.0, Kd 0.015 both channels.
- simplePID itself is follow_common vendor code — internals illustrative, update() returns
  [out_ch0, out_ch1]; execute uses [z_Pid, _].

### onMouse L232-243
cv mouse events: event 1 (left down) → Track_state='init', select_flags=True, Mouse_XY=(x,y);
event 4 (left up) → select_flags=False, Track_state='mouse'; while selecting:
cols = (min x, min y), rows = (max x, max y), Roi_init = (x0,y0,x1,y1).

### execute L245-290 (the steering brain — runs INSIDE A THREAD, one per tracking frame)
- L247-252 Joy_active → if Start_state: PID_init(), Start_state=False; return (Joy pauses
  following; PID re-inits each pause). L252 Start_state=True on the normal path.
- L253-257 color_radius == 0 (line lost): print "Not Found";
  `/action_feedback` String **'follow_line_clear_future_done'** (tell the upstream state machine);
  `pub_cmdVel.publish(Twist())` full stop.
- L258-289 else: twist = Twist(); b = UInt16();
  - L261 `[z_Pid, _] = self.PID_controller.update([(point_x - 320)*1.0/16, 0])` — error = pixel
    offset from image center 320, scaled by /16.
  - L263-265 img_flip True → `twist.angular.z = -z_Pid` else `= +z_Pid`.
  - L269 **`twist.linear.x = 0.1` HARDCODED** — self.linear (written 0.18 at L214 via the L73
    call, then reset to 0.2 by L93; final attribute 0.2) is NEVER used here; the parameter is
    effectively dead for driving.
  - L270-275 `if self.front_warning > 10:` print "Obstacles ahead !!!", publish Twist() (stop),
    Buzzer_state=True, b.data=1, publish buzzer. (11+ beams inside 0.375 m ⇒ stop+siren.)
  - L276-280 else: if Buzzer_state: b.data=0, publish buzzer 3× (debounce), Buzzer_state=False.
  - L282-284 deadzone `if abs(point_x-320)<40:` → `twist.angular.z = 0.0` (±40 px ≈ ±2.5° of
    steering need — straighten).
  - L285-289 `if self.Joy_active == False: pub_cmdVel.publish(twist)` **else: `twist.angular.z =
    0.0`** — and NOTHING else: the else branch zeroes a local and never publishes (dead branch).

### process L291-380 (state machine, called per synced frame)
- L293 binary = []; L294 resize 640×480; L296 img_flip → cv.flip(rgb_img, 1).
- L297-301 keys from the cv window: action 32 (SPACE) → Track_state='tracking'; 'i'/105 →
  'identify'; 'r'/114 → Reset(); 'q'/113 → **self.cancel()** — not defined in this file, must come
  from follow_common wildcard (else AttributeError).
- L302-314 'init': namedWindow('frame', WINDOW_AUTOSIZE) + setMouseCallback; while select_flags:
  draw cv.line (cols→rows, blue) + cv.rectangle (green); if Roi non-degenerate (x0≠x1 and y0≠y1):
  `rgb_img, self.hsv_range = self.color.Roi_hsv(rgb_img, self.Roi_init)` (wildcard color object),
  dyn_update=True; else (L313-314) Track_state stays 'init'.
- L315-318 'identify': if the hsv_text file EXISTS on disk → `self.hsv_range = read_HSV(
  self.hsv_text)` (reuse last calibration); else → 'init' (force user to draw ROI).
- L319-333 if state != 'init' AND hsv_range non-empty: `rgb_img, binary, self.circle =
  self.color.line_follow(rgb_img, self.hsv_range)` — the HSV mask + centroid; circle = (cx, cy, r).
  If dyn_update: write_HSV(hsv_text, hsv_range) (persist), build 6 rclpy Parameter objects from
  hsv_range ([[Hmin,Smin,Vmin],[Hmax,Smax,Vmax]]), `set_parameters(all_new_parameters)`,
  dyn_update=False. NOTE: reads back L316's commented `self.circle[0]` — circle set ONLY here.
- L334-340 'tracking': if circle non-empty → `threading.Thread(target=self.execute,
  args=(self.circle[0], self.circle[2])).start()` — a NEW thread per frame (cx, radius); else
  if Start_state: Start_state=False (L339 commented-out stop publish — comment only).
- L341-345 **AprilTag pivot**: `if len(self.tags)>0 and self.Track_state!="Remove":` →
  Track_state='identify', pub Twist() stop, print "Find the apriltag.", Track_state='Remove'.
  (Any detected tag while following ⇒ abandon line, switch to removal/crawl mode.)
- L346-379 'Remove': print "len(tags) = N"; if tags: `center_x, center_y = self.tags[0].center`;
  - adjusting: `if (abs(center_x-320) >10 or abs(center_y-400)>10) and self.move_flag == True:`
    print "adjusting."; `self.remove_obstacle(center_x, center_y)` (drive so tag centers).
  - centered (|cx-320|<10 AND |cy-400|<10): `pubVel(0.0, 0.0)`, print "start crawling.",
    `time.sleep(3)` (BLOCKS this thread 3 s), `c_dist = self.depth_image_info[int(center_y),
    int(center_x)]/1000` (mm→m); if c_dist != 0 and pubPos_flag: move_flag=False, pubPos_flag=False,
    AprilTagInfo{id=tag_id, x=cx, y=cy, z=c_dist}; `vx = corners[0][0]-corners[1][0]`,
    `vy = corners[0][1]-corners[1][1]` (tag edge vector); `target_joint5 = compute_joint5(vx,vy)`
    (wildcard); joint5.data = int(target_joint5); prints tag_id / center / depth; publish pos on
    PosInfo; **TargetJoint5_pub.publish(self.joint5) TWICE (L375+L376)** — duplicate publish in
    source; else → print "Invalid distance.".
- L380 `return rgb_img, binary`.

### helpers L382-430
- L382-387 pubVel(vx,vy): Twist with linear.x=vx AND **linear.y=vy** (strafe — mecanum base), publish.
- L389-395 remove_obstacle(point_x, point_y): `[y, x] = Remove_PID_controller.update([(point_x-320)
  /10.0, (point_y-400)/10.0])`; clamp x to ±0.10 (if ≥0.10→0.10; ≤-0.10→-0.10), clamp y to ±0.10;
  `pubVel(x, y)`. NOTE the destructuring: PID ch0 (x-error) lands in variable `y`, ch1 (y-error)
  lands in `x` — then pubVel(x, y) → linear.x gets the ch1 output. Swap is in the source.
- L397-399 JoyStateCallback #2 — IDENTICAL body to L118; SECOND definition wins at class creation.
- L403-410 Reset: PID_init(), Track_state='init', hsv_range=(), Joy_active=False, Mouse_XY=(0,0),
  pub Twist(), print "Reset succes!!!" (typo as-is).
- L412-430 get_param: re-reads all 14 parameters and REBUILDS FollowLinePID=(Kp,Ki,Kd) — **NEVER
  CALLED anywhere in this file** (would-be external hook; dead in this folder).

### main L433-485
- L434-459 banner: "M3Pro ROBOT - LINE FOLLOW + APRILTAG", what-it-does list [1]-[4], keyboard
  controls (SPACE/I/R/Q), safety notes ("Keep the robot area clear", "robot will stop when an
  obstacle is detected") — pure prints ("Only display messages are added here; robot logic is
  unchanged", L436).
- L461 rclpy.init(); L462 `linedetect = LineDetect("follow_line")` — constructor (incl. the
  BLOCKING arm wait) runs HERE; L463-470 [OK] prints + ">>> System is RUNNING. <<<".
- L471-474 try rclpy.spin(linedetect) except KeyboardInterrupt: pass.
- L475-485 finally: prints "Stopping robot safely...", "[OK] Zero velocity command sent",
  "[OK] ROS 2 node stopped", "Goodbye!"; `linedetect.pub_cmdVel.publish(Twist())` (one final zero),
  destroy_node(), rclpy.shutdown().

## §7 save_map.launch.py — 49 lines, persist the map

- L2-8 imports: LaunchDescription, DeclareLaunchArgument, LaunchConfiguration,
  get_package_share_directory (L5, UNUSED here), Node, os, get_package_share_path (L8, the one used).
- L14 `map_name = "yahboom_map"`.
- L18 `default_map_path = os.path.join(get_package_share_path("M3Pro_navigation"), 'map',
  map_name)` — save target lives in the NAVIGATION package's share dir.
- L23-27 `map_arg = DeclareLaunchArgument(name='map_path', default_value=str(default_map_path),
  description='The path of the map')` — override with `map_path:=...`.
- L31-42 `map_saver_node = Node(package='nav2_map_server', executable='map_saver_cli',
  arguments=['-f', LaunchConfiguration('map_path'), '--free', '0.196', '--occ', '0.65'])`.
  - `-f` output path (PGM+YAML pair).
  - `--free 0.196`: cell with occupancy probability ≤ 0.196 → FREE (white, 0). Source comment L39
    phrases it "less than 19.6% sure a spot is a wall → White".
  - `--occ 0.65`: probability ≥ 0.65 → OCCUPIED (black, 100). Comment L40: "more than 65% sure →
    Black". Between 0.196 and 0.65 → UNKNOWN (gray, -1/nan). map_saver_cli is one-shot: saves and exits.
- L46-49 `return LaunchDescription([map_arg, map_saver_node])`.

## §8 Canonical numbers (single source of truth — NEVER contradict)

- 5 programs in gmapping.launch.py; 4 includes + 1 direct Node; 4 eager paths.
- /imu → /imu/data_raw remap; imu_filter_madgwick_node named same.
- rviz: slam_mapping/rviz/slam_rviz.rviz; use_sim_time 'false'; rviz2/rviz2.
- camera: orbbec_camera dabai_dcw2.launch.py; kin: arm_kin/kin_srv/kin_ik_fk.
- map: yahboom_map in M3Pro_navigation/map; --free 0.196 --occ 0.65; map_saver_cli one-shot.
- keyboard: speed 0.2, turn 1.0; limits 1.0 / 5.0; factors 1.1 / 0.9; arm step 5°; clamps j5 0..270,
  j6 30..180, others 0..180; time 500 / 2000 / 100; home [90,90,0,0,90,90]; poll 0.1 s; deadman
  count > 4; node yahboom_keyboard_ctrl; select timeout 0.1.
- follow_line: node "follow_line"; init_joints [90,90,12,20,90,0]; pubSixArm mirror 180-j0;
  sync slop 0.5 s queue 1; Detector tag36h11 nthreads 8 quad_decimate 2.0 quad_sigma 0.0
  refine_edges 1 decode_sharpening 0.25 debug 0; FollowLinePID (50,0,10) → 0.05/0/0.01;
  RemovePID (40,0,15.0) → 0.04/0/0.015; scale 1000; HSV red 0-9/85-253/126-253; Kp param 60 (dead);
  linear param 0.18 declared (L73 call writes 0.18 at L214, then L93 resets the attribute to 0.2;
  neither reaches the wheels), drive speed hardcoded 0.1; LaserAngle 60 →
  cone |angle|<30 or >330; ResponseDist 0.25 → warning range 0.375 m; stop when front_warning > 10;
  PID input (point_x-320)/16; deadzone ±40 px; buzzer clear ×3; AprilTag centering ±10 px around
  (320,400); crawl sleep 3 s; depth mm/1000; joint5 published twice; 3-second auto-arm to tracking;
  remove_obstacle inputs /10, clamps ±0.10, pubVel linear.x+linear.y.
- README L13 arm pose {90, 140, 20, 10, 90, 180, time 1500} --once.
- Everything from follow_common / compute_joint5 / vendor internals is ILLUSTRATIVE — never assert
  their private algorithms; describe only the call as seen in this file.

## §9 Known quirks to PRESERVE (explain, never "fix")

1. gmapping L2/L9 duplicate Node import; L3/L4 unused; L17-19 dead lists.
2. slam_view: 7 unused imports, self-acknowledged L2-3.
3. save_map: get_package_share_directory imported (L5) but get_package_share_path used (L8).
4. follow_line L38/L40 duplicate /JoyState subscription; L118/L397 duplicate JoyStateCallback.
5. follow_line L161-165 dead second depth conversion; L131 trailing tabs; L97 double-space.
6. Kp 60 / linear 0.18 params effectively bypassed (FollowLinePID 50 tuple; drive 0.1 hardcoded).
7. get_param never called; TargetJoint6_pub never published; warning attr never read.
8. L375-376 double joint5 publish; L287-289 dead else (z=0, no publish); L148 Chinese comment;
   "Reset succes!!!" typo; execute() spawned as a new Thread per tracking frame.
9. remove_obstacle [y,x] destructuring swap — pubVel(x, y) feeds ch1 to linear.x.
10. keyboard: 'M' mirrors ',' (both back); pause blocks arm keys; space is one-shot, pause is latching.
11. README L13 unquoted inline YAML dict (shell-dependent; preserved as-is).
12. yahboom_keyboard L185 `count = 0\t` trailing tab; gmapping 11 trailing-space lines.

## §10 Conventions (binding for BOTH layers)

- Bangla prose; English technical terms stay Latin with hyphen-suffix (PID-টি, scan-এ, topic-টার).
- Tolerated transliterations ONLY: টেস্ট/রেজিস্টার/ডিগ্রি/স্কিপ/রিসেট/স্টিয়ারিং (shipped convention).
- No emoji anywhere. No Unicode arrows in the exec spec or v1 stage <text> (ASCII -> allowed).
- No Bangla numerals inside dbg values or SVG coordinates (Western digits only there).
- Illustrative/vendor-derived numbers flagged "ill" in dbg triples.
- Source bugs NEVER fixed in prose — explained as-is; "ঠিক করলে" language only in Real Robot
  incorrect-block contrast, never editing the quoted code.
