#!/usr/bin/env python3
"""Generate the frozen unit skeletons for the folder-14 exec spec.

Chronology = README runbook (8 commands at odd lines L1..L15). Launch files
are modeled two-phase (module import + generate_launch_description ctor, then
run-phase events firing the returned entries); ros2-run Python nodes are
modeled two-pass (import pass defines, main pass runs, event waves replay
callback/loop lines). Coverage validated against filedata-14.json: every one
of the 983 source lines appears in >=1 step. Target ~360 steps, 16 units.
"""
import json
from pathlib import Path

K = Path("/home/shariful/NeuroBotics/refine-kit/v2-14/exec")
fd = json.load(open("/home/shariful/NeuroBotics/refine-kit/v2-14/filedata-14.json", encoding="utf-8"))

R, G, V, KB, C, F, S = ("README.md", "gmapping.launch.py", "slam_view.launch.py",
                        "yahboom_keyboard.py", "camera_arm_kin.launch.py",
                        "follow_line.py", "save_map.launch.py")

def st(f, a, b, kind):
    return {"file": f, "ln": a, "lns": list(range(a, b + 1)), "kind": kind}

def one(f, n, kind):
    return {"file": f, "ln": n, "lns": [n], "kind": kind}

def rep(f, lns, kind):  # replay step (lns need not be contiguous)
    return {"file": f, "ln": lns[0], "lns": list(lns), "kind": kind}

rd = {n: one(R, n, "exec" if n % 2 else "struct") for n in range(1, 16)}

# ================= gmapping.launch.py — ctor then run =================
g_ctor = [
    st(G, 1, 2, "exec"),      # header + Node import #1
    st(G, 3, 4, "struct"),    # unused LaunchConfiguration + DeclareLaunchArgument
    st(G, 5, 6, "exec"),      # os + get_package_share_directory
    st(G, 7, 8, "exec"),      # LaunchDescription + PythonLaunchDescriptionSource
    st(G, 9, 9, "struct"),    # DUPLICATE Node import
    st(G, 10, 11, "exec"),    # IncludeLaunchDescription + self-note comment
    st(G, 12, 14, "struct"),  # blanks + def generate_launch_description
    st(G, 15, 19, "exec"),    # dead-list comments + three dead lists
    st(G, 20, 23, "struct"),  # blank + FINDING comment + "1. Laser Merger"
    st(G, 24, 28, "exec"),    # merger path join (eager)
    st(G, 29, 30, "struct"),  # blank + "2. Laser Filter"
    st(G, 31, 35, "exec"),    # filter path join
    st(G, 36, 37, "struct"),  # blank + "3. EKF"
    st(G, 38, 42, "exec"),    # ekf path join
    st(G, 43, 44, "struct"),  # blank + "4. Gmapping"
    st(G, 45, 49, "exec"),    # gmapping path join
    st(G, 50, 52, "struct"),  # blank + "5. IMU Filter Node" comments
    st(G, 53, 55, "exec"),    # Node( package= executable= (object built)
    st(G, 56, 59, "struct"),  # remap metaphor comments
    st(G, 60, 62, "exec"),    # remappings + name + close
    st(G, 63, 66, "struct"),  # blank + FINAL LIST comments + return LaunchDescription([
    st(G, 67, 68, "struct"),  # blank + merger comment
    st(G, 69, 71, "exec"),    # include #1 merger entry built
    st(G, 72, 73, "struct"),  # blank + filter comment
    st(G, 74, 76, "exec"),    # include #2 filter
    st(G, 77, 78, "struct"),  # blank + imu comment
    one(G, 79, "exec"),       # imu node entry
    st(G, 80, 81, "struct"),  # blank + ekf comment
    st(G, 82, 84, "exec"),    # include #3 ekf
    st(G, 85, 89, "struct"),  # blank + gmapping comments (AI listens...)
    st(G, 90, 92, "exec"),    # include #4 gmapping
    st(G, 93, 94, "struct"),  # blank + close
]
g_run = [
    rep(G, [69, 70, 71], "event"),  # merger include fires
    rep(G, [74, 75, 76], "event"),  # filter include fires
    rep(G, [79], "event"),          # imu node starts
    rep(G, [82, 83, 84], "event"),  # ekf include fires
    rep(G, [90, 91, 92], "event"),  # gmapping include fires
]

# ================= slam_view.launch.py =================
v_ctor = [
    st(V, 1, 3, "exec"),      # header + self-note unused comment
    st(V, 4, 7, "exec"),      # Node + Include(unused) + gpshd + LaunchDescription
    st(V, 8, 9, "struct"),    # ExecuteProcess(unused) + conditions(unused)
    st(V, 10, 11, "exec"),    # LaunchConfiguration + Node,SetRemap
    st(V, 12, 14, "struct"),  # FindPackageShare + PythonLaunchDescriptionSource + Shutdown (unused)
    st(V, 15, 17, "exec"),    # os + blank + def generate_launch_description
    st(V, 18, 24, "struct"),  # SETTING UP + use_sim_time comments + LaunchConfiguration
    st(V, 25, 29, "struct"),  # blank + rviz_config comments
    st(V, 30, 34, "exec"),    # rviz_config join slam_rviz.rviz
    st(V, 35, 37, "struct"),  # blank + declare comment + rviz_config_arg
    st(V, 38, 40, "struct"),  # blank + RVIZ NODE comments
    st(V, 41, 45, "exec"),    # Node( package executable name output
    st(V, 46, 47, "struct"),  # blank + startup-args comment
    st(V, 48, 52, "exec"),    # arguments=[ '-d' config, use_sim_time ]
    st(V, 53, 55, "struct"),  # blank + FINAL LIST comments
    st(V, 56, 59, "exec"),    # return + entries + close
]
v_run = [
    rep(V, [57], "event"),  # rviz_config_arg processed
    rep(V, [58], "event"),  # rviz_node fires — RViz opens with slam_rviz.rviz
]

# ================= yahboom_keyboard.py =================
kb_import = [
    st(KB, 1, 3, "exec"),     # shebang + encoding + blank
    st(KB, 4, 6, "exec"),     # comment + sys + select
    st(KB, 7, 10, "exec"),    # termios + tty + time + blank
    st(KB, 11, 12, "exec"),   # rclpy + Node
    st(KB, 13, 15, "exec"),   # Twist + ArmJoint,ArmJoints + blank
    st(KB, 16, 20, "struct"), # comment + msg open + banner
    st(KB, 21, 26, "struct"), # [ BASE MOTION ] block
    st(KB, 27, 31, "struct"), # blank + ARM header + joint1/2
    st(KB, 32, 35, "struct"), # joint3/4/5 + gripper
    st(KB, 36, 40, "struct"), # [ SYSTEM ] + SPACE + s + r
    st(KB, 41, 45, "struct"), # q/z w/x e/c + CTRL+C + close
    st(KB, 46, 49, "struct"), # blank + maps comment + moveBindings open + i
    st(KB, 50, 52, "struct"), # , a d
    st(KB, 53, 55, "struct"), # j l
    st(KB, 56, 59, "struct"), # u o m/. + blank
    st(KB, 60, 62, "struct"), # speedBindings Q Z W X
    st(KB, 63, 65, "struct"), # E C + lowercase twins + close
]
kb_class = [
    st(KB, 66, 68, "struct"), # class + def __init__ + super
    st(KB, 69, 73, "struct"), # comment + pub_cmd_vel + arm pubs
    st(KB, 74, 79, "struct"), # params comment + declare/read limits
    st(KB, 80, 83, "struct"), # state comment + home + settings
    st(KB, 84, 87, "struct"), # init comment + reset_arm() call + blank
    st(KB, 88, 90, "struct"), # def getKey + setraw + select
    st(KB, 91, 93, "struct"), # rlist / read / else
    st(KB, 94, 97, "struct"), # tcsetattr + return + blank
    st(KB, 98, 99, "struct"), # def vels + f-string
    st(KB, 100, 103, "struct"),  # blank + def step_arm_joint + += + comment
    st(KB, 104, 106, "struct"),  # safety comment + joint5 0..270
    st(KB, 107, 108, "struct"),  # joint6 30..180
    st(KB, 109, 111, "struct"),  # else 0..180 + blank
    st(KB, 112, 116, "struct"),  # ArmJoint msg build + publish
    st(KB, 117, 121, "struct"),  # blank + action words + print
    st(KB, 122, 126, "struct"),  # blank + def reset_arm + home + ArmJoints()
    st(KB, 127, 131, "struct"),  # joint1..5
    st(KB, 132, 135, "struct"),  # joint6 + time 2000 + publish + print + blank
    st(KB, 136, 139, "struct"),  # def emergency_stop + stop wheels
    st(KB, 140, 143, "struct"),  # arm brake comment + msg + joint1..3
    st(KB, 144, 149, "struct"),  # joint4..6 + time 100 + publish + blank
    st(KB, 150, 153, "struct"),  # def main + init + ctor + blank
    st(KB, 154, 158, "struct"),  # speed turn x y th stop count twist
    st(KB, 159, 163, "struct"),  # blank + try + print msg + vels
    st(KB, 164, 165, "struct"),  # while True + getKey
    st(KB, 166, 173, "struct"),  # blank + pause/resume toggle block
    st(KB, 174, 179, "struct"),  # blank + SPACE e-stop block
    st(KB, 180, 185, "struct"),  # blank + if not stop + moveBindings hit
    st(KB, 186, 192, "struct"),  # speedBindings + clamps + vels
    st(KB, 193, 200, "struct"),  # blank + arm keys 1..6
    st(KB, 201, 205, "struct"),  # arm keys 7/8/9/0 + blank
    st(KB, 206, 210, "struct"),  # gripper g/h + reset r
    st(KB, 211, 217, "struct"),  # else deadman + Ctrl+C + blank
    st(KB, 218, 224, "struct"),  # paused else + blank
    st(KB, 225, 229, "struct"),  # twist fill + blank
    st(KB, 230, 234, "struct"),  # publish running / paused zero + blank
    st(KB, 235, 242, "struct"),  # except + finally + shutdown
]
kb_main = [
    one(KB, 150, "event"),        # main() entered (setup.py entry, inferred)
    one(KB, 151, "exec"),         # rclpy.init()
    one(KB, 152, "exec"),         # YahboomKeyboard("yahboom_keyboard_ctrl")
    one(KB, 68, "exec"),          # super().__init__(name)
    one(KB, 71, "exec"),          # pub_cmd_vel (RELATIVE 'cmd_vel')
    st(KB, 72, 73, "exec"),       # arm pubs depth 100
    st(KB, 76, 77, "exec"),       # declare linear limit 1.0
    st(KB, 78, 79, "exec"),       # declare angular limit 5.0
    one(KB, 82, "exec"),          # arm_joints home
    one(KB, 83, "exec"),          # termios settings saved
    one(KB, 86, "exec"),          # reset_arm() call
    st(KB, 124, 131, "exec"),     # home list + ArmJoints joint1..5
    st(KB, 132, 134, "exec"),     # time 2000 + publish + print
    st(KB, 154, 158, "exec"),     # speed 0.2 turn 1.0 + locals
    st(KB, 161, 162, "exec"),     # print msg + vels (0.20 | 1.00)
    one(KB, 164, "exec"),         # loop entered
]
kbw_i = [one(KB, 165, "event"), st(KB, 183, 185, "exec"),       # 'i' forward
         st(KB, 226, 228, "exec"), st(KB, 230, 231, "exec")]
kbw_u = [one(KB, 165, "event"), st(KB, 183, 185, "exec"),       # 'u' (1,1,0) strafe+forward
         st(KB, 226, 228, "exec"), st(KB, 230, 231, "exec")]
kbw_q = [one(KB, 165, "event"), st(KB, 187, 189, "exec"),       # 'q' x1.1
         st(KB, 190, 192, "exec")]
kbw_1 = [one(KB, 165, "event"), one(KB, 195, "exec"),           # '1' joint1 -5
         one(KB, 102, "exec"), st(KB, 109, 110, "exec"),
         st(KB, 112, 116, "exec"), st(KB, 118, 121, "exec")]
kbw_g = [one(KB, 165, "event"), one(KB, 207, "exec"),           # 'g' gripper close
         one(KB, 102, "exec"), st(KB, 107, 108, "exec"),
         st(KB, 112, 116, "exec"), st(KB, 118, 121, "exec")]
kbw_r = [one(KB, 165, "event"), one(KB, 210, "exec"),           # 'r' reset arm
         st(KB, 124, 131, "exec"), st(KB, 132, 134, "exec")]
kbw_space = [one(KB, 165, "event"), st(KB, 176, 177, "exec"),   # SPACE one-shot e-stop
             one(KB, 138, "exec"), st(KB, 140, 148, "exec"),
             st(KB, 178, 179, "exec")]
kbw_s = [one(KB, 165, "event"), st(KB, 168, 170, "exec"),       # 's' pause ON
         one(KB, 172, "exec"), one(KB, 138, "exec"),
         st(KB, 140, 148, "exec"), one(KB, 173, "exec"),
         st(KB, 230, 233, "exec")]
kbw_s2 = [one(KB, 165, "event"), st(KB, 168, 170, "exec"),      # 's' again resume
          st(KB, 226, 228, "exec"), st(KB, 230, 231, "exec")]
kbw_dead = [one(KB, 165, "event"), st(KB, 211, 214, "exec"),    # deadman 5 empty polls
            st(KB, 226, 228, "exec"), st(KB, 230, 231, "exec")]
kbw_halt = [one(KB, 215, "event"), one(KB, 216, "exec"),        # Ctrl+C halt
            st(KB, 235, 236, "exec"), one(KB, 237, "exec"),
            one(KB, 239, "exec"), one(KB, 240, "exec"),
            st(KB, 241, 242, "exec")]
kb_waves = (kbw_i + kbw_u + kbw_q + kbw_1 + kbw_g + kbw_r + kbw_space +
            kbw_s + kbw_s2 + kbw_dead + kbw_halt)

# ================= camera_arm_kin.launch.py =================
c_ctor = [
    st(C, 1, 2, "exec"),      # header + LaunchDescription
    st(C, 3, 4, "exec"),      # Node + os
    st(C, 5, 7, "exec"),      # Include + PythonLaunchDescriptionSource + gpshd
    st(C, 8, 13, "struct"),   # blanks + must-have comments + def
    st(C, 14, 17, "struct"),  # PROGRAM 1 comments + include start
    st(C, 18, 20, "exec"),    # LIST-arg join head
    st(C, 21, 23, "exec"),    # dabai comment + '/dabai_dcw2.launch.py'])
    st(C, 24, 28, "struct"),  # model comment + blanks + PROGRAM 2
    st(C, 29, 30, "struct"),  # kin_node Node( + arm_kin
    st(C, 31, 32, "exec"),    # kin_srv + kin_ik_fk
    st(C, 33, 34, "struct"),  # ik/fk comment + close
    st(C, 35, 39, "struct"),  # blank + FINAL LIST comments
    st(C, 40, 40, "exec"),    # return LaunchDescription([...])
]
c_run = [
    rep(C, [40], "event"),  # camera include fires (dabai driver up)
    rep(C, [40], "event"),  # kin node fires (kin_ik_fk service up)
]

# ================= follow_line.py =================
f_import_a = [                 # L1-115 imports + class + ctor (struct after L28)
    st(F, 1, 2, "exec"),      # ros lib comment + rclpy
    st(F, 3, 6, "exec"),      # Node + std_msgs + Twist + sensor_msgs
    st(F, 7, 10, "exec"),     # common lib + os threading math
    one(F, 11, "exec"),       # WILDCARD follow_common
    one(F, 12, "exec"),       # RAD2DEG = 180/math.pi
    one(F, 13, "exec"),       # print ("import finish")
    st(F, 14, 15, "exec"),    # cv.__version__ + print (cv from wildcard!)
    st(F, 16, 18, "exec"),    # blank + cv2 + ArmJoints
    st(F, 19, 21, "exec"),    # message_filters + CvBridge + encoding
    st(F, 22, 26, "exec"),    # Detector + draw_tags + np + arm_interface + compute_joint5
    st(F, 27, 30, "struct"),  # blank + class + def init + super
    st(F, 31, 36, "struct"),  # blanks + publisher comment + 3 pubs
    one(F, 37, "struct"),     # subscriber comment
    one(F, 38, "struct"),     # sub /JoyState #1
    one(F, 39, "struct"),     # sub /scan1 registerScan
    one(F, 40, "struct"),     # sub /JoyState DUPLICATE
    st(F, 41, 43, "struct"),  # blank + mf rgb + depth subscribers
    st(F, 44, 50, "struct"),  # 4 pubs + grasp sub + action_feedback
    one(F, 51, "struct"),     # init_joints [90,90,12,20,90,0]
    one(F, 52, "struct"),     # BLOCKING while get_subscription_count
    one(F, 53, "struct"),     # pubSixArm(self.init_joints)
    one(F, 54, "struct"),     # time.sleep(0.1)
    one(F, 55, "struct"),     # final pubSixArm
    st(F, 56, 58, "struct"),  # sync pair + registerCallback + blank
    st(F, 59, 60, "struct"),  # two CvBridge
    st(F, 62, 69, "struct"),  # Detector( 8 params tag36h11
    st(F, 70, 73, "struct"),  # flags + declare_param() call
    st(F, 74, 79, "struct"),  # Joy_active img circle hsv_range Roi_init warning
    st(F, 80, 83, "struct"),  # Start_state dyn_update Buzzer_state select_flags
    st(F, 84, 88, "struct"),  # Track_state identify + window + cols + Mouse + hsv_text
    st(F, 89, 93, "struct"),  # color_follow scale PIDs linear 0.2
    st(F, 94, 97, "struct"),  # commented LaserAngle + PID_init + flip + refresh
    one(F, 99, "struct"),     # pubCurrentJoints() call
    st(F, 100, 104, "struct"),  # tags + depth_info + joint5/6 + data 120
    st(F, 105, 110, "struct"),  # Start_ start_time count front_warning Joy dup
    st(F, 111, 115, "struct"),  # prints Init Done / 60 / 0.25
]
f_import_b = [                 # L116-244 callbacks + helpers (struct)
    st(F, 116, 120, "struct"),  # blanks + JoyStateCallback #1
    st(F, 122, 124, "struct"),  # registerScan head + zero + guard
    st(F, 125, 127, "struct"),  # np array + loop + angle comment
    one(F, 128, "struct"),      # cone condition
    st(F, 129, 133, "struct"),  # 0.375 threshold + front_warning += 1 + blanks
    st(F, 134, 138, "struct"),  # pubCurrentJoints body
    st(F, 139, 145, "struct"),  # blank + get_graspStatusCallBack
    st(F, 146, 147, "struct"),  # blank + def callback
    one(F, 148, "struct"),      # Chinese comment
    st(F, 149, 150, "struct"),  # rgb8 + np.copy
    st(F, 151, 155, "struct"),  # blank + depth 32FC1 + resize + float32
    st(F, 156, 159, "struct"),  # blank + detect + sort + draw_tags
    st(F, 160, 165, "struct"),  # blank + DEAD duplicate depth block
    one(F, 166, "struct"),      # waitKey
    st(F, 167, 170, "struct"),  # 3-second arming
    st(F, 171, 174, "struct"),  # process + RGB2BGR + imshow
    st(F, 175, 178, "struct"),  # blank + pubSixArm def + ArmJoints
    st(F, 179, 187, "struct"),  # joint2..6 + runtime + publish + blank + def declare_param
    st(F, 188, 196, "struct"),  # HSV comment + H/S/V min/max
    st(F, 197, 200, "struct"),  # Smax + Vmax
    st(F, 201, 207, "struct"),  # PID params Kp Ki Kd
    st(F, 208, 218, "struct"),  # other + scale + LaserAngle + linear 0.18 + 0.25 + refresh
    st(F, 219, 221, "struct"),  # blank + def PID_init + simplePID
    st(F, 222, 225, "struct"),  # FollowLinePID channels /1000
    st(F, 226, 231, "struct"),  # Remove simplePID + channels /1000 + blank
    st(F, 232, 236, "struct"),  # onMouse event 1
    st(F, 237, 244, "struct"),  # event 4 + cols/rows/Roi_init + blank
]
f_import_c = [                 # L245-431 execute + process + helpers (struct)
    st(F, 245, 246, "struct"),  # def execute + blank
    st(F, 247, 252, "struct"),  # Joy gate + Start_state
    st(F, 253, 257, "struct"),  # Not Found + action_feedback + stop
    st(F, 258, 261, "struct"),  # else twist b + PID update /16
    st(F, 262, 268, "struct"),  # commented + img_flip ±z + comments
    one(F, 269, "struct"),      # linear.x = 0.1 HARDCODED
    one(F, 270, "struct"),      # front_warning > 10
    st(F, 271, 275, "struct"),  # stop + buzzer 1
    st(F, 276, 281, "struct"),  # else buzzer clear x3 + blank
    st(F, 282, 284, "struct"),  # deadzone ±40
    st(F, 285, 290, "struct"),  # publish + dead else + blank
    one(F, 291, "struct"),      # def process
    st(F, 292, 294, "struct"),  # binary + resize
    st(F, 295, 300, "struct"),  # flip + SPACE/i/r/q keys
    one(F, 301, "struct"),      # q cancel() wildcard
    st(F, 302, 310, "struct"),  # init: window + mouse + ROI + Roi_hsv
    st(F, 311, 314, "struct"),  # dyn_update + else stays init
    st(F, 315, 318, "struct"),  # identify: read_HSV or init
    st(F, 319, 321, "struct"),  # line_follow + dyn write
    st(F, 322, 333, "struct"),  # HSV parameters + set_parameters
    st(F, 334, 337, "struct"),  # tracking: circle thread
    st(F, 338, 340, "struct"),  # else Start_state + commented publish
    st(F, 341, 345, "struct"),  # APRILTAG PIVOT
    st(F, 346, 348, "struct"),  # Remove: print + tags
    st(F, 349, 352, "struct"),  # adjusting -> remove_obstacle
    st(F, 353, 356, "struct"),  # centered: pubVel 0 + crawl + sleep 3
    one(F, 357, "struct"),      # c_dist depth/1000
    st(F, 358, 362, "struct"),  # flags off + AprilTagInfo id/xy
    st(F, 363, 368, "struct"),  # pos z + vx vy + compute_joint5
    st(F, 369, 374, "struct"),  # prints + publish pos
    st(F, 375, 376, "struct"),  # joint5 published TWICE
    st(F, 377, 381, "struct"),  # else invalid + return + blank
    st(F, 382, 387, "struct"),  # pubVel x/y + publish
    st(F, 388, 390, "struct"),  # blank + def remove_obstacle + [y,x] SWAP
    st(F, 391, 394, "struct"),  # clamps ±0.10
    one(F, 395, "struct"),      # pubVel(x,y)
    st(F, 396, 401, "struct"),  # blank + JoyStateCallback #2 (wins) + dead pub + blank
    st(F, 402, 403, "struct"),  # blank + def Reset
    st(F, 404, 409, "struct"),  # reset body
    st(F, 410, 411, "struct"),  # Reset succes!!! typo + blank
    one(F, 412, "struct"),      # def get_param NEVER CALLED
    st(F, 413, 424, "struct"),  # HSV + PID re-reads + tuple rebuild
    st(F, 425, 431, "struct"),  # scale..refresh re-reads + blank
]
f_main = [
    st(F, 432, 433, "event"),    # blank + main() entered (setup.py entry, inferred)
    st(F, 434, 443, "exec"),     # banner comment + prints part 1
    st(F, 444, 459, "exec"),     # what-it-does + keyboard header + keys + notes
    st(F, 460, 462, "exec"),     # blank + rclpy.init() + ctor line
    one(F, 462, "exec"),         # LineDetect("follow_line") — ctor STARTS
    one(F, 30, "exec"),          # super().__init__(name)
    st(F, 34, 36, "exec"),       # pubs /cmd_vel /linefollow/rgb /beep
    one(F, 38, "exec"),          # sub /JoyState #1
    one(F, 39, "exec"),          # sub /scan1
    one(F, 40, "exec"),          # sub /JoyState DUPLICATE
    st(F, 42, 43, "exec"),       # mf rgb+depth subscribers
    st(F, 44, 50, "exec"),       # pubs + grasp sub + action_feedback
    one(F, 51, "exec"),          # init_joints
    one(F, 52, "event"),         # BLOCKING WAIT — arm subscriber absent
    st(F, 53, 54, "exec"),       # pubSixArm + sleep 0.1 (publishing home)
    one(F, 52, "event"),         # subscription_count 1 — loop exits
    one(F, 55, "exec"),          # final pubSixArm
    st(F, 56, 57, "exec"),       # sync queue 1 slop 0.5 + registerCallback
    st(F, 59, 69, "exec"),       # bridges + Detector built
    one(F, 73, "exec"),          # declare_param() call
    st(F, 189, 216, "exec"),     # 14 declares + reads (HSV/PID/other)
    one(F, 74, "exec"),          # Joy_active False
    one(F, 84, "exec"),          # Track_state identify
    st(F, 88, 95, "exec"),       # hsv_text color scale PIDs PID_init
    st(F, 96, 99, "exec"),       # flip refresh + pubCurrentJoints
    st(F, 100, 110, "exec"),     # tags joint5/6 start_time front_warning
    st(F, 111, 115, "exec"),     # prints 60 / 0.25
    st(F, 463, 470, "exec"),     # OK prints + RUNNING
    one(F, 472, "exec"),         # rclpy.spin parks
]
fw_joy = [rep(F, [118, 119, 120], "event"), one(F, 121, "exec")]        # JoyState False
fw_scan = [rep(F, [122, 123], "event"), one(F, 124, "exec"),             # /scan1 arrives
           one(F, 125, "exec"), one(F, 127, "exec"), one(F, 128, "exec"),
           one(F, 129, "exec"), one(F, 131, "exec")]                     # front_warning grows
fw_sync = [rep(F, [147], "event"), st(F, 149, 150, "exec"),              # synced rgb+depth
           st(F, 152, 155, "exec"), st(F, 157, 159, "exec"),
           one(F, 166, "exec"), one(F, 168, "exec"),
           one(F, 169, "exec"), one(F, 171, "exec"),                     # 3s arming -> tracking
           one(F, 320, "exec"), one(F, 336, "exec"),                     # line_follow + thread
           one(F, 245, "exec"), one(F, 261, "exec"),                     # execute + PID /16
           one(F, 269, "exec"), one(F, 282, "exec"), one(F, 286, "exec")]  # 0.1 + deadzone + publish
fw_obs = [rep(F, [122], "event"), one(F, 128, "exec"),                   # OBSTACLE scan
          one(F, 129, "exec"), one(F, 131, "exec"),                      # front_warning 12
          one(F, 270, "exec"), st(F, 271, 275, "exec"),                  # stop + beep 1
          one(F, 261, "exec"), one(F, 286, "exec")]                      # publish zero path
fw_clear = [rep(F, [147], "event"), one(F, 124, "exec"),                 # clear again
            one(F, 131, "exec"), st(F, 277, 280, "exec"),                # buzzer clear x3
            one(F, 261, "exec"), one(F, 286, "exec")]
fw_tag = [rep(F, [157], "event"), one(F, 158, "exec"),                   # APRILTAG wave
          one(F, 341, "exec"), one(F, 343, "exec"), one(F, 345, "exec"),   # pivot -> Remove
          one(F, 349, "exec"), one(F, 390, "exec"), one(F, 395, "exec"),   # adjusting PID
          one(F, 353, "exec"), one(F, 356, "exec"), one(F, 357, "exec"),   # centered + crawl
          st(F, 361, 365, "exec"), one(F, 368, "exec"),                    # info + joint5
          st(F, 374, 376, "exec")]                                         # pos + joint5 x2
fw_grasp = [rep(F, [140], "event"), st(F, 141, 145, "exec")]             # grasp_done resume
fw_haltf = [rep(F, [471, 473], "event"), one(F, 474, "exec"),            # Ctrl+C halt
            one(F, 475, "exec"), st(F, 476, 482, "exec"),
            one(F, 483, "exec"), one(F, 484, "exec"), one(F, 485, "exec")]
f_waves = (fw_joy + fw_scan + fw_sync + fw_obs + fw_clear + fw_tag +
           fw_grasp + fw_haltf)

# ================= save_map.launch.py =================
s_ctor = [
    st(S, 1, 3, "exec"),      # header + LaunchDescription + DeclareLaunchArgument
    st(S, 4, 6, "exec"),      # LaunchConfiguration + gpshd(unused) + Node
    st(S, 7, 9, "exec"),      # os + get_package_share_path (used) + blank
    st(S, 10, 11, "struct"),  # def generate_launch_description + blank
    st(S, 11, 13, "struct"),  # blank + NAMING comment
    one(S, 14, "exec"),       # map_name = "yahboom_map"
    st(S, 15, 18, "struct"),  # comments + default_map_path join
    st(S, 19, 22, "struct"),  # blank + ARGUMENT comments
    st(S, 23, 27, "exec"),    # map_arg DeclareLaunchArgument
    st(S, 28, 30, "struct"),  # blank + SAVER comments
    st(S, 31, 33, "exec"),    # Node( + nav2_map_server + map_saver_cli
    st(S, 34, 36, "struct"),  # blanks + instructions comment
    st(S, 37, 38, "exec"),    # -f map_path + --free 0.196
    st(S, 39, 40, "exec"),    # --occ 0.65 + close
    st(S, 41, 45, "struct"),  # close + blank + FINAL comments
    st(S, 46, 49, "exec"),    # return + entries
]
s_run = [
    rep(S, [47], "event"),  # map_arg processed
    rep(S, [48], "event"),  # map_saver fires — ONE-SHOT save + exit
]

# ================= spine (README chronology) =================
spine = (
    [rd[1], rd[2], rd[3]] + g_ctor + g_run +
    [rd[4], rd[5]] + v_ctor + v_run +
    [rd[6], rd[7]] + kb_import + kb_class + kb_main + kb_waves +
    [rd[8], rd[9]] + c_ctor + c_run +
    [rd[10], rd[11]] + f_import_a + f_import_b + f_import_c + f_main + f_waves +
    [rd[12], rd[13], rd[14], rd[15]] + s_ctor + s_run
)

cov = {fn: set() for fn in fd}
for s in spine:
    cov[s["file"]] |= set(s["lns"])
    assert s["lns"] == sorted(s["lns"]), s
    assert s["ln"] == s["lns"][0], s
for fn, lines in fd.items():
    want = set(range(1, len(lines) + 1))
    miss, extra = want - cov[fn], cov[fn] - want
    assert not miss and not extra, (fn, sorted(miss)[:8], sorted(extra)[:8])

UNITS = [
    ("U1",  [rd[1], rd[2], rd[3]] + g_ctor[:11]),
    ("U2",  g_ctor[11:22]),
    ("U3",  g_ctor[22:] + g_run),
    ("U4",  [rd[4], rd[5]] + v_ctor[:9]),
    ("U5",  v_ctor[9:] + v_run),
    ("U6",  [rd[6], rd[7]] + kb_import),
    ("U7",  kb_class[:20]),
    ("U8",  kb_class[20:]),
    ("U9",  kb_main),
    ("U10", kbw_i + kbw_u + kbw_q + kbw_1),
    ("U11", kbw_g + kbw_r + kbw_space),
    ("U12", kbw_s + kbw_s2 + kbw_dead + kbw_halt),
    ("U13", [rd[8], rd[9]] + c_ctor + c_run),
    ("U14", [rd[10], rd[11]] + f_import_a[:14]),
    ("U15", f_import_a[14:]),
    ("U16", f_import_b),
    ("U17", f_import_c[:22]),
    ("U18", f_import_c[22:]),
    ("U19", f_main),
    ("U20", fw_joy + fw_scan + fw_sync),
    ("U21", fw_obs + fw_clear + fw_tag),
    ("U22", fw_grasp + fw_haltf + [rd[12], rd[13], rd[14], rd[15]]),
    ("U23", s_ctor + s_run),
]
counts = {}
pos = {id(s): i for i, s in enumerate(spine)}
for name, steps in UNITS:
    assert steps, name
    (K / f"unit-{name}.json").write_text(json.dumps(steps, ensure_ascii=False), encoding="utf-8")
    counts[name] = len(steps)
    idxs = [pos[id(s)] for s in steps if id(s) in pos]
    assert idxs == sorted(idxs), (name, "unit order violates spine order")

print("spine:", len(spine), "steps |", sum(len(v) for v in fd.values()), "lines covered")
print("unit counts:", counts, "| sum:", sum(counts.values()))
print("kinds:", {k: sum(1 for s in spine if s["kind"] == k) for k in ("struct", "exec", "event")})
