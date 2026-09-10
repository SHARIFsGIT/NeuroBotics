'use strict';
/* ================================================================
   13. lidar guard — Line-by-Line Code Analysis
   Single source of truth: FILEDATA (exact source lines from disk)
   + PARTS (authored analysis content). All rendering is generated.
   ================================================================ */

const FILEDATA = {"README.md":["sh start_agent.sh","","ros2 launch yahboom_M3Pro_laser laser_driver.launch.py","","ros2 run yahboom_M3Pro_laser laser_Warning"],"laser_driver.launch.py":["import os   # (System file operations) - Lets Python interact with computer folders and file paths","from ament_index_python.packages import get_package_share_directory  # A ROS 2 tool that finds where a package is installed","from launch import LaunchDescription  # The main container that holds our list of programs to start","from launch.actions import IncludeLaunchDescription  # A tool to run ANOTHER launch file inside this one","from launch.launch_description_sources import PythonLaunchDescriptionSource  # Tells ROS the other launch file is written in Python","from launch_ros.actions import Node  # A tool to start a single ROS 2 program (Node) - imported just in case it's needed later","","def generate_launch_description():","","    # --- PROGRAM 1: THE LASER MERGER ---","    # Find the path to the 'ira_laser_tools' package, go into the 'launch' folder, and find 'merge_multi.launch.py'","    laser_merge_launch_file = os.path.join(","        get_package_share_directory('ira_laser_tools'),","        'launch',","        'merge_multi.launch.py'","    )","    ","    # --- PROGRAM 2: THE LASER FILTER ---","    # Find the path to the 'yahboom_laser_filter' package, go into the 'launch' folder, and find 'laser_filter_node.launch.py'","    laser_filter_launch_file = os.path.join(","        get_package_share_directory('yahboom_laser_filter'),","        'launch',","        'laser_filter_node.launch.py'","    )","","    # --- THE FINAL LIST ---","    # Hand the list of programs back to ROS 2 to start them all at once.","    return LaunchDescription([","","        # 1. Start the Laser Merger","        # This runs the file we found above. It stitches the front and back lasers together into one 360-degree map.","        IncludeLaunchDescription(","            PythonLaunchDescriptionSource(laser_merge_launch_file)","        ),","        ","        # 2. Start the Laser Filter","        # This runs the file we found above. It cleans up the data by removing \"blind spots\" (like the robot's own arm).","        IncludeLaunchDescription(","            PythonLaunchDescriptionSource(laser_filter_launch_file)","        )","","    ])"],"laser_Warning.py":["#ros lib","import rclpy","from rclpy.node import Node","from geometry_msgs.msg import Twist","from sensor_msgs.msg import LaserScan","from std_msgs.msg import UInt16  # The message type used to turn the buzzer ON/OFF","","#commom lib","import math","import numpy as np","import time","from time import sleep","from yahboom_M3Pro_laser.common import *  # Custom Yahboom tools (Bool message and SinglePID)","import os","print (\"improt done\")  # (Typo in original: means \"import done\")","RAD2DEG = 180 / math.pi  # Conversion factor: radians to degrees","","class laserWarning(Node):","    def __init__(self,name):","        super().__init__(name)","        ","        # --- CREATING SUBSCRIBERS (Listeners) ---","        # Listen to the 360-degree LiDAR scanner","        self.sub_laser = self.create_subscription(LaserScan,\"/scan\",self.registerScan,1)","        # Listen to the joystick (so you can pause the AI and drive manually)","        self.sub_JoyState = self.create_subscription(Bool,'/JoyState', self.JoyStateCallback,1)","        ","        # --- CREATING PUBLISHERS (Radio Stations) ---","        # Tell the wheels to move","        self.pub_vel = self.create_publisher(Twist,'/cmd_vel',1)","        # Tell the buzzer to beep!","        self.pub_Buzzer = self.create_publisher(UInt16,'/beep',1)","","        # --- ROS 2 PARAMETERS (Speed & Distance Limits) ---","        self.declare_parameter(\"linear\",0.5)       # Max forward speed (not actually used in this script, but declared)","        self.linear = self.get_parameter('linear').get_parameter_value().double_value","        self.declare_parameter(\"angular\",1.0)      # Max turning speed","        self.angular = self.get_parameter('angular').get_parameter_value().double_value","        self.declare_parameter(\"LaserAngle\",45.0)  # Width of the front cone (45 degrees left and right)","        self.LaserAngle = self.get_parameter('LaserAngle').get_parameter_value().double_value","        self.declare_parameter(\"ResponseDist\",0.55) # The \"Danger Zone\" distance (0.55 meters)","        self.ResponseDist = self.get_parameter('ResponseDist').get_parameter_value().double_value","        ","        # --- STATE TRACKERS & PID CONTROLLER ---","        self.Joy_active = False","        # This PID controller controls the steering wheel to keep the closest object centered.","        # It is tuned a bit more aggressively than the tracker (3.0, 0.0, 5.0)","        self.ang_pid = SinglePID(3.0, 0.0, 5.0)","","    def JoyStateCallback(self, msg):","        if not isinstance(msg, Bool): return","        self.Joy_active = msg.data  # If True, human is driving, AI should pause","","    def registerScan(self, scan_data):","        if not isinstance(scan_data, LaserScan): return","        ranges = np.array(scan_data.ranges)  # Array of distances from the LiDAR","        ","        # We will search for the absolute closest object in the front 90-degree cone","        minDistList = []    # A list to hold all the close distances","        minDistIDList = []  # A list to hold the angles of those close distances","        ","        # Loop through every single laser beam","        for i in range(len(ranges)):","            # Calculate which direction (in degrees) this specific laser beam is pointing","            angle = (scan_data.angle_min + scan_data.angle_increment * i) * RAD2DEG","            ","            # FRONT ZONE: If the beam is pointing forward (within +/- 45 degrees) and hits something valid","            if abs(angle) < self.LaserAngle and ranges[i] !=0.0 : ","                minDistList.append(ranges[i])     # Save the distance","                minDistIDList.append(angle)       # Save the angle","        ","        # If nothing is in front of us, do nothing and wait","        if len(minDistList) == 0: return","        ","        # Find the absolute closest distance out of all the beams","        minDist = min(minDistList)","        # Find out what angle that closest object is sitting at","        minDistID = minDistIDList[minDistList.index(minDist)]","        ","        # If a human is driving, stop the AI and do nothing","        if self.Joy_active :","            self.pub_vel.publish(Twist())","            return","","        print(\"minDist: \", minDist)   # Print how far away the object is","        ","        # --- THE ALARM LOGIC ---","        # If the closest object is inside the Danger Zone (0.55m)...","        if minDist <= self.ResponseDist and minDist != 0.0:","            b = UInt16()","            b.data = 1               # 1 means BEEP!","            self.pub_Buzzer.publish(b)","        else:","            # If the object is outside the danger zone, turn the buzzer off (0).","            self.pub_Buzzer.publish(UInt16()) ","","        # --- THE TRACKING LOGIC ---","        velocity = Twist()","        print(\"minDistID: \", minDistID)\t","        ","        # Calculate how much to turn to face the object.","        # Target Angle is 0 (straight ahead). Current Angle is minDistID.","        ang_pid_compute = self.ang_pid.pid_compute(abs(minDistID) / 72, 0)","        ","        # If the object is to the left (positive angle), turn left","        if 0 < minDistID :","            velocity.angular.z = ang_pid_compute","        # If the object is to the right (negative angle), turn right","        elif minDistID < 0:","            velocity.angular.z = -ang_pid_compute","            ","        print(\"orin_angular.z: \", velocity.angular.z)  # Original calculated turn speed","        ","        # Deadzone: If the object is almost directly in front, don't turn.","        if abs(ang_pid_compute) < 0.5: velocity.angular.z = 0.0","        ","        # Slow down the turning speed to 50% so the robot doesn't whip around too fast.","        velocity.angular.z = velocity.angular.z * 0.5","        ","        print(\"angular.z: \", velocity.angular.z)  # Final turn speed","        ","        # Send the movement command to the wheels!","        # Note: linear.x is never set here, so the robot stays perfectly still and just spins in place!","        self.pub_vel.publish(velocity)","","    # --- SAFETY SHUTDOWN FUNCTION ---","    def exit_pro(self):","        # When you press Ctrl+C, this runs a terminal command in the background to force the robot to stop","        cmd1 = \"ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist \"","        cmd2 = '''\"{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}\"'''","        cmd = cmd1 + cmd2","        os.system(cmd)","","def main():","    rclpy.init()","    laser_warn = laserWarning(\"laser_Warnning_a1\")","    print (\"start it\")","    try:","        rclpy.spin(laser_warn)","    except KeyboardInterrupt:","        pass","    finally:","        laser_warn.exit_pro()  # Force stop the wheels","        laser_warn.destroy_node()","        rclpy.shutdown()"]};
const PARTS = [{"n":1,"id":"part-01","fname":"README.md","enTitle":"Runbook — Three Commands","lang":"bash","start":1,"end":5,"flags":[],"explain":[{"a":1,"b":1,"text":"<code>sh start_agent.sh</code> — runbook-এর প্রথম command: <code>sh</code> interpreter দিয়ে vendor-এর bringup script-টা চালানো হলো। মনে রাখতে হবে এই script-টা আমাদের কোনো source file-এর ভেতরে নেই, তাই ভেতরে ঠিক কী লেখা আছে তা আমরা দেখিনি — illustrative ধারণা: এটা robot-এর base driver আর সামনে-পেছনের দুটো lidar-এর vendor driver তুলে দেয়, যাতে কাঁচা scan data বেরোতে শুরু করে। folder 11 আর folder 12 — দুই আগের app-এর README-এর প্রথম line-ও হুবহু এই command-ই — মানে folder 10-13 — চার lidar পরীক্ষা app-এর প্রতিটার গোড়ায় একই bringup। README-টা মোট ৫ line-এর: L2 আর L4 blank line, শুধু তিনটা স্তরকে চোখে আলাদা দেখানোর separator — আসল content তিনটা command, আর তিনটাই পরেরটার পূর্বশর্ত।"},{"a":3,"b":3,"text":"<code>ros2 launch yahboom_M3Pro_laser laser_driver.launch.py</code> — দ্বিতীয় স্তর: sensor chain। রূপটা <code>ros2 launch package_name launch_file</code>: ROS 2 আগে <code>yahboom_M3Pro_laser</code> package-টা খোঁজে, তার share directory থেকে <code>laser_driver.launch.py</code> হাতে নিয়ে তার <code>generate_launch_description()</code> চালায়। launch file-টাই এই folder-এর দ্বিতীয় source file, আর এটা folder 11 ও folder 12 — দুই আগের app-এর driver-এর সঙ্গে byte-identical — ভেতরে কোনো node সরাসরি লেখা নেই; দুটো <code>IncludeLaunchDescription</code> দিয়ে folder 10-এর গোটা fusion pipeline চেইন করা হয়েছে — <code>ira_laser_tools</code>-এর merger সামনে-পেছনের lidar জোড়ে একটা 360-degree scan বানায়, <code>yahboom_laser_filter</code> robot-এর নিজের শরীর-হাতের blind-spot reading সরিয়ে data পরিষ্কার করে। ফলে <code>/scan</code> topic-এ merged, filtered stream প্রস্তুত হয়। একটা জরুরি সীমা মনে রাখো — এই launch file guard node-টা চালু করে না; L3 শুধু sensor chain-ই তোলে, behavior node-এর জন্য আলাদা L5 লাগবে। <code>ros2 launch</code>-এর ক্ষমতা এখানেই — এক command-এ একাধিক node-এর পুরো chain একসাথে ওঠে।"},{"a":5,"b":5,"text":"<code>ros2 run yahboom_M3Pro_laser laser_Warning</code> — তৃতীয় ও শেষ স্তর: guard node। এবার <code>ros2 launch</code> নয়, <code>ros2 run package_name executable_name</code> — কোনো launch file ছাড়াই package-এর একটাই executable সরাসরি চালানো হয়েছে, নাম <code>laser_Warning</code> (বড় হাতের W লক্ষ্য করুন)। এই এক শব্দেই আগের app-গুলোর README-র সঙ্গে পুরো তফাত — L1-L4 হুবহু এক, কিন্তু folder 11-এর L5-এ ছিল <code>laser_Avoidance</code>, আর folder 12-এর L5-এ <code>laser_Tracker</code>; এই app-এ সেই জায়গায় <code>laser_Warning</code>। অর্থের তফাত আরও গভীর: folder 11-এর node বাধা এড়িয়ে চলত, folder 12-এর node সামনের কাছের object-টাকে 0.55 m দূরত্বে ফলো করত; এই node সেই দুই কাজের কোনোটাই করে না — এটা একটা sentry। node-টা জন্মায় <code>laser_Warnning_a1</code> নাম নিয়ে (laser_Warning.py-র L136; Warnning বানানে double n — source-এর নিজের typo), L3-এর chain থেকে আসা merged <code>/scan</code> আর joystick-এর <code>/JoyState</code> subscribe করে, আর publish করে <code>/cmd_vel</code> ও নতুন একটা <code>/beep</code> topic-এ — এই <code>/beep</code>-ই এই app-এর নতুন guard channel। প্রতিটা scan-এ সামনের ±45° cone-এর সবচেয়ে কাছের valid object-টা খোঁজে: তার দূরত্ব <code>ResponseDist</code> parameter-এর মান 0.55 m বা তার কম হলে buzzer-এ BEEP বাজে, নাহলে চুপ; আর file-এর একমাত্র PID-টা (angular) robot-কে ঘুরিয়ে object-টার দিকে মুখ করে দেয় — linear.x কোথাও set-ই হয় না, তাই robot কখনো সামনে এগোয় না, শুধু এক জায়গায় দাঁড়িয়ে ঘোরে। ক্রমটা সৌন্দর্যের নয়: L3 না উঠলে এই node কোনো scan পায় না, উঠে চুপচাপ বসে থাকে।"}],"math":null,"robot":{"correct":"বাস্তব robot-এ তিনটা command ঠিক এই ক্রমে দিন। L1-এর vendor bringup base আর দুটো lidar driver জাগায় (illustrative), L3-এর launch folder 10-এর merger ও filter chain তুলে <code>/scan</code>-এ পরিষ্কার 360-degree data আসতে শুরু করে, তারপর L5-এর <code>laser_Warning</code> node প্রতিটা scan পেয়ে সামনের ±45° cone-এর সবচেয়ে কাছের object-টা চিনতে থাকে। Object-টা 0.55 m-এর সমান বা কাছে এলেই <code>/beep</code>-এ 1 যাওয়ায় buzzer BEEP দিতে থাকে, object দূরে গেলে চুপ হয়ে যায়; আর angular PID দুই চাকা বিপরীত দিকে ঘুরিয়ে robot-কে object-টার দিকে মুখ করে দেয় — linear.x কখনো set হয় না বলে শরীর জায়গা থেকে নড়ে না, robot এক জায়গায় ঘুরে sentry-র মতো পাহারা দেয়। Console-এ প্রতিটা scan-এ সামনের object-এর দূরত্ব ও angle ছাপাতে থাকে। একটা স্তর বাদ গেলে পরের স্তরের খাবারই আসে না।","incorrect":"সাধারণ ভুল: L5 আগে চালানো। ROS 2-এ subscription এমন topic-এও সফল হয় যার publisher এখনো নেই, তাই node ত্রুটিমুক্ত উঠে বসে থাকে — <code>registerScan</code> একবারও চলে না, <code>/cmd_vel</code> বা <code>/beep</code>-এ কিছু যায় না, চাকা নড়ে না, buzzer-ও শব্দ করে না; আসল কারণ L3-এর fusion chain ওঠেনি বলে <code>/scan</code> চুপ। দ্বিতীয় ভুল প্রত্যাশা: folder 12-এর <code>laser_Tracker</code> দেখে এটাকে ফলো-করা, বা folder 11-এর <code>laser_Avoidance</code> দেখে বাধা এড়ানোর node ভাবা — বাস্তবে <code>laser_Warning</code> কখনো সামনে এগোয় না: object-কে সরিয়ে নিলে robot পিছু নেবে না, জায়গায় দাঁড়িয়ে থাকবে, object 0.55 m-এর মধ্যে এলে BEEP দেবে আর ঘুরে তার দিকে তাকাবে। তৃতীয় ভুল: L3-এর launch-ই গোটা কাজ করে ভেবে node-টা চালু না করা — driver নিজে একটাও node তোলে না, তাই lidar ঘুরুক, <code>/scan</code> ভরুক, চাকা আর buzzer কেউ কিছুই করবে না। একই রকম চুপচাপ ফল হয় L1 বাদ দিলে — lidar থেকে কাঁচা scan-ই আসে না।"},"animType":"runbookFlow"},{"n":2,"id":"part-02","fname":"laser_driver.launch.py","enTitle":"Driver Launch — Imports","lang":"python","start":1,"end":7,"flags":[],"explain":[{"a":1,"b":2,"text":"<code>import os</code> — Python-এর standard library-র file ও path টুল, author-এর comment বলছে <code>(System file operations)</code>। কাজ একটাই: L12 আর L20-এ <code>os.path.join</code> দিয়ে folder 10-এর <code>merge_multi.launch.py</code> ও <code>laser_filter_node.launch.py</code>-এর path জোড়া দেওয়া। <code>from ament_index_python.packages import get_package_share_directory</code> এনেছে সেই ROS 2 function যেটাকে package-এর নাম দিলে — L13-এ <code>ira_laser_tools</code>, L21-এ <code>yahboom_laser_filter</code> — সে ওই package-এর install হওয়া share directory-র পথ ফিরিয়ে দেয়। এটা plain function call: <code>generate_launch_description()</code> চলার সময়েই, মানে construction time-এ, পথ মিলে যায় — folder 10-এর <code>LaunchConfiguration</code> substitution-এর lazy আচরণের ঠিক উল্টো; এজন্যই package install না থাকলে launch পড়ার মুহূর্তেই error আসে। শুরুতেই একটা কথা দিয়ে রাখি: গোটা driver file-টা আগের দুই app-এর — folder 11 ও folder 12-এর — <code>laser_driver.launch.py</code>-এর সঙ্গে byte-identical, এই ছয়টা import থেকে শেষ bracket পর্যন্ত এক বাইট তফাতও নেই, কারণ তিনটা app-ই চায় একই sensor chain।"},{"a":3,"b":5,"text":"<code>from launch import LaunchDescription</code> — প্রধান container; L28-এ <code>return LaunchDescription</code> দিয়ে যে list-টা launch framework-এর হাতে ফিরে যায় সেটাই এই class-এর object, তাই এই import ছাড়া পুরো file-টাই অর্থহীন। <code>from launch.actions import IncludeLaunchDescription</code> এই file-এর আসল অস্ত্র: একটা launch file-এর ভেতরে আরেকটা launch file চালানোর action, নামেরই মানে Include — L32 আর L38-এ একটা করে বসেছে। এই একটা tool-ই এখানকার পুরো design: নিজে কোনো node না চালিয়ে folder 10-এর merger ও filter launch-কে chain করা। <code>from launch.launch_description_sources import PythonLaunchDescriptionSource</code> বাইরের path string-টাকে wrap করে framework-কে জানায় যে ওই file-টা Python launch file — ROS 2-ে XML বা YAML launch source-ও আছে, কিন্তু এখানে দুটোই Python। এই তিনটি মিলেই launch-chaining pattern: container, include action, আর Python source declaration।"},{"a":6,"b":7,"text":"<code>from launch_ros.actions import Node</code> — ছয়টা import-এর শেষটা, আর author-এর নিজের comment-ই স্বীকার করছে <code>imported just in case it's needed later</code>; সত্যিই গোটা file-ে <code>Node</code> আর কোথাও ব্যবহার হয়নি — L28-42-এর list-এ শুধু দুটো <code>IncludeLaunchDescription</code>, কোনো <code>Node</code> action নেই। এটা একটা দামি পাঠ — import দেখেই মনে করা যাবে না জিনিসটা কাজে লাগছে; Python নামটাকে module scope-এ bind করে চুপচাপ বসে থাকে, কোনো warning বা error নেই, তাই dead import সহজে চোখে পড়ে না। এই app-এর জন্য তার মানেও স্পষ্ট: এই launch file শুধু sensor chain ওঠায়, guard node-টা চালু করে না — README-র L5 command <code>ros2 run yahboom_M3Pro_laser laser_Warning</code> সেটাকে আলাদাভাবে তোলে, আর সেই node fused <code>/scan</code> থেকে সামনের কাছের object ধরে: জিনিস 0.55 m-এর ভেতরে এলে <code>/beep</code>-এ message গিয়ে buzzer বাজে, আর angular PID-এর হিসাবে robot জায়গায় ঘুরে দিক বদলায় — <code>linear.x</code> কখনো set-ই হয় না, তাই guard কখনো সামনে চালায় না। আগের দুই app-এর সঙ্গে তফাতটা এখানেই: একই chain-এর উপর folder 11-এ <code>laser_Avoidance</code> বাধা এড়াত, folder 12-এ <code>laser_Tracker</code> object ফলো করত — driver তিন app-এই এক, শুধু ভোক্তা আলাদা। পার্থক্যটা আরেকটু ধরো: folder 10-এর <code>merge_multi.launch.py</code> একইভাবে <code>Node</code> import করে সরাসরি node চালু করেছিল, কিন্তু এই file সব কাজ অন্য দুই launch file-কে দিয়ে করায়। শেষ সূক্ষ্ম পয়েন্ট: <code>launch</code> আর <code>launch_ros</code> দুটো আলাদা package — <code>Node</code> পাওয়া যায় শুধু দ্বিতীয়টায়, তাই ভবিষ্যতে সত্যিই কোনো node যোগ করতে হলে এই লাইনটাই আগে থেকে প্রস্তুত ছিল। L7 একটা blank line — ছয়টা import-এর block-কে L8-এর <code>def generate_launch_description():</code> থেকে আলাদা দেখানোর separator, নিজে কিছুই execute করে না।"}],"math":null,"robot":{"correct":"এই file তুললেই <code>get_package_share_directory</code> construction time-এ robot-এর install tree থেকে <code>ira_laser_tools</code> ও <code>yahboom_laser_filter</code>-এর share directory খুঁজে দেয়, তাই merger ও filter-এর launch file-এর path আগেই ঠিক হয়। এরপর দুটো IncludeLaunchDescription chain হয়ে folder 10-এর পুরো fusion pipeline ওঠে — front আর back lidar মিলে 360-degree fused <code>/scan</code> তৈরি হয়, blind spot-এর ভুয়া রিডিংও কাটা পড়ে, console-এ included দুই process-এর log নামতে থাকে (illustrative)। এই stage-এ robot একদম স্থির: import-গুলো কোনো <code>/cmd_vel</code> message পাঠায় না বলে চাকা নড়ে না, আর <code>/beep</code>-এ এখনো কোনো publisher নেই বলে buzzer চুপ — শুধু guard node-টার খাবার তৈরি হয়। README L5-এর <code>laser_Warning</code> পরে এই fused scan থেকেই সামনের কাছের object ধরে: 0.55 m-এর ভেতরে এলে buzzer বাজায় আর জায়গায় ঘুরে দিক বদলায় — সামনে কখনো চালায় না।","incorrect":"ভুল পড়া: L6-এর <code>Node</code> import দেখে ধরে নেওয়া যে এই launch file নিজে guard node-টাও চালু করে। Robot-এ এই ধারণা বিপদজনক: মনে করা হবে robot নিজে নিজে পাহারা দিচ্ছে, অথচ <code>ros2 run yahboom_M3Pro_laser laser_Warning</code> আলাদাভাবে না চালালে merger-filter উঠুক, <code>/scan</code> ভরে থাকুক, lidar ঘুরতে থাকুক — হাত আড়াল থেকে 0.3 m-এ এগিয়ে দিলেও buzzer একটা শব্দ করবে না, চাকায় কোনো command যাবে না, robot চুপচাপ দাঁড়িয়ে থাকবে। আর unused ভেবে এই import মুছলে কিছু ভাঙে না, কিন্তু author-এর just-in-case দরজাটা বন্ধ হয়।"},"animType":null},{"n":3,"id":"part-03","fname":"laser_driver.launch.py","enTitle":"Two Paths — Merger & Filter","lang":"python","start":8,"end":24,"flags":[],"explain":[{"a":8,"b":8,"text":"<code>def generate_launch_description():</code> — এই নামটাই <code>ros2 launch</code>-এর সঙ্গে চুক্তি। README L3-এর <code>ros2 launch yahboom_M3Pro_laser laser_driver.launch.py</code> চালালে framework এই file-কে import করে ঠিক এই নামের function-টাকে একবার ডাকে; launch file-এ কোনো <code>main()</code> বা spin loop নেই, তাই নাম বদলালেই launch ভেঙে পড়ে। Function-এর ভেতরের প্রতিটা লাইন চলে CONSTRUCTION phase-এ — run phase শুরুর আগে, একবার, উপর থেকে নিচে। Folder 10-এর lesson মনে করো: <code>LaunchConfiguration</code> substitution ছিল lazy, মান মিলত run phase-এ; এই file-এ উল্টো — যা লেখা সব এখনই eagerly চলে। Driver file-টা আগের দুই app-এর সঙ্গেই byte-identical — folder 11 আর folder 12, দুই জায়গাতেই এই একই দুই path build হত; তফাত শুধু downstream-এ: folder 11-এর L5 node <code>laser_Avoidance</code> বাধা এড়াত, আগের app folder 12-এর <code>laser_Tracker</code> সামনের কাছের object-কে 0.55 m দূরত্বে ফলো করত; এই folder 13-এর <code>laser_Warning</code> সেই একই 0.55 m সংখ্যাটাকে ব্যবহার করে অন্য কাজে — alarm সীমা হিসেবে: object সীমার ভেতরে এলেই buzzer বাজে আর robot জায়গায় ঘুরে object-এর দিকে মুখ ফেরায়, সামনে এক পাও এগোয় না। কাজ শেষে function-টা একটা <code>LaunchDescription</code> ফেরাবে (L28), সেটাকেই framework পরে run করায়।"},{"a":10,"b":11,"text":"দুটো লাইনই <code>#</code> দিয়ে শুরু — comment, Python এগুলো execute করে না, তবু author-এর নকশা হিসেবে file-টার কাঠামো পরিষ্কার করে। L10 banner: <code>PROGRAM 1: THE LASER MERGER</code>; L11 কাজ বলে — <code>ira_laser_tools</code> package-এর path খুঁজে, তার <code>launch</code> folder-এ ঢুকে <code>merge_multi.launch.py</code> বের করা। Comment-এ যা বলা L12-16 হুবহু তা-ই করে — comment মানচিত্র, code পথ। এই <code>merge_multi.launch.py</code>-ই folder 10-এ লাইন ধরে পড়া merger: সেখানে সামনে-পেছনে দুই lidar-এর raw scan (folder 09-এ যেমন একটা lidar-এর নিজের stream দেখেছি) এক 360-degree <code>/scan</code>-এ জোড়া লাগে — সেই fused ring-ই পরে এই app-এর <code>laser_Warning</code> node-টার খাবার: ওই data থেকেই সে সামনের cone-এর সবচেয়ে কাছের object ধরে বিপদ-সংকেত দেয়।"},{"a":12,"b":13,"text":"<code>laser_merge_launch_file = os.path.join(</code> — assignment শুরু, bracket L16 পর্যন্ত খোলা থাকায় তার সব argument একসঙ্গে মূল্যায়ন হবে। প্রথম argument <code>get_package_share_directory('ira_laser_tools')</code>: এটা launch-এর কোনো magic নয়, ament-এর package index-কে জিজ্ঞেস করা একটা সাধারণ Python function call — আর সে চলে এখনই, construction phase-এ, installed share directory-র path string ফেরিয়ে দেয় (illustrative: <code>install/ira_laser_tools/share/ira_laser_tools</code> — যা <code>ros2 pkg prefix</code> দেখায়)। Package না মিললে এখনই error ওঠে — robot-এর কোনো lidar, buzzer বা চাকা নড়ার অনেক আগেই, তাই এটা safe early failure।"},{"a":14,"b":16,"text":"পরের দুটো argument <code>'launch'</code> আর <code>'merge_multi.launch.py'</code>। <code>os.path.join</code> এদের মাঝে ঠিক separator বসিয়ে একটা পূর্ণ path বানায় — string <code>+</code> দিয়ে জোড়া দিলে separator ভুল হওয়ার ঝুঁকি থাকে, <code>os.path.join</code> সেই ভার নিজে নেয়, তাই কোন OS-এ চলুক না কেন path ঠিক থাকে। ফল: merger launch file-এর absolute path, জমা রইল variable <code>laser_merge_launch_file</code>-এ। খেয়াল করো, এই মুহূর্তে কিছুই launch হয়নি — এটা নিছক একটা string; lidar এখনো ঘুরছে না, buzzer চুপ, চাকা স্থির। Merger-এর আসল কাজ হবে run phase-এ, Part 04-এর <code>IncludeLaunchDescription</code> action থেকে।"},{"a":18,"b":19,"text":"সেই একই pattern-এর দ্বিতীয় কপি। L18 banner: <code>PROGRAM 2: THE LASER FILTER</code>; L19 বলে — <code>yahboom_laser_filter</code> package-এর path, তার <code>launch</code> folder, ভেতরে <code>laser_filter_node.launch.py</code>। ভাষা ও গঠন ইচ্ছা করেই আগের ব্লকের মতো রাখা: দুটো আলাদা program, কিন্তু খোঁজার নিয়ম এক। ভূমিকাও স্পষ্ট — merger দুই lidar-এর মিলিত scan বানায়, filter তার পরে blind spot সরিয়ে (robot-এর নিজের গা বা arm-এর ভুয়া কাছের রিডিং) stream পরিষ্কার করে; এই ক্রমটাই folder 10-এ দেখা pipeline, এখন এক launch file থেকে পুরোটা একসাথে চালানো হচ্ছে। Guard-এর দৃষ্টিতে এই ধুয়ে-মুছে দেওয়াটা বাড়তি জরুরি — <code>laser_Warning</code> সামনের cone-এর সবচেয়ে কাছের valid reading-ই alarm হিসেবে ধরে, তাই filter না থাকলে robot নিজের arm-এর ভুয়া রিডিংকেই বিপদ ভেবে buzzer বাজিয়ে ঘুরত (illustrative)।"},{"a":20,"b":21,"text":"<code>laser_filter_launch_file = os.path.join(</code> — নামে শুধু merge-এর জায়গায় filter, বাকি আদল হুবহু আগের ব্লক। <code>get_package_share_directory('yahboom_laser_filter')</code> এবার অন্য একটা package খোঁজে — Yahboom-এর নিজের laser filter package, <code>ira_laser_tools</code> নয়। এটাও একই সাধারণ function call: চলে এখনই, eagerly, construction phase-এ — তাই দুটো path-ই সঙ্গে সঙ্গে মিলে যায় আর দুটোই যাচাই হয়ে যায় কোনো node ওঠার আগেই। এক launch-এ একাধিক package-এর tool এভাবেই এক জায়গায় জড়ো করা যায় — এই file-টা তারই ছোট উদাহরণ।"},{"a":22,"b":24,"text":"শেষ দুটো segment: <code>'launch'</code> আর <code>'laser_filter_node.launch.py'</code> — মিলে filter launch file-এর পূর্ণ path, জমা <code>laser_filter_launch_file</code>-এ। এই মুহূর্তে file-টার অবস্থা দাঁড়াল এমন: দুটো string variable তৈরি, দুটোতেই বাস্তব path, কিন্তু একটাও program চালু হয়নি — কোনো node এখনো exist করে না। এই chain থেকে আসা fused, filtered <code>/scan</code>-ই পরে README L5-এর <code>ros2 run yahboom_M3Pro_laser laser_Warning</code> node-টা subscribe করবে; এই launch file শুধু তার খাবার তৈরি করে, warning node-কে নিজে চালু করে না। আগের app-এর প্রত্যাশা এখানে বদলে গেছে — folder 12-এর <code>laser_Tracker</code> object ফলো করত, তাই robot এগিয়ে চলত; <code>laser_Warning</code> কখনো সামনে চালায় না, object 0.55 m-এর মধ্যে থাকলে শুধু buzzer বাজায় আর জায়গায় ঘুরে সেদিকে তাকায়। এরপর L26 থেকে আসবে সেই তালিকা তৈরির পর্ব, যেখানে এই দুই path <code>IncludeLaunchDescription</code> দিয়ে run phase-এ নামানো হবে। সহজ কথায়: L12-24 হলো দুইটা ঠিকানা খুঁজে লিখে রাখা — বাড়ি বানানোর কাজ পরের part-এ।"}],"math":null,"robot":{"correct":"আসল robot-এ README L3-এর <code>ros2 launch yahboom_M3Pro_laser laser_driver.launch.py</code> চালালে সবার আগে চলে এই দুইটা path lookup — ament index থেকে <code>ira_laser_tools</code> আর <code>yahboom_laser_filter</code>-এর installed share directory মিলে যায়, তারপরই merger+filter pipeline নামে। Terminal-এ workspace source থাকলে path কখনো ভুল হয় না, workspace অন্য জায়গায় থাকলেও ঠিক থাকে। সামনে-পেছনের দুই lidar-এর scan জুড়ে 360-degree <code>/scan</code> তৈরি হয় আর filter blind spot সরায় — এই পরিষ্কার stream-ই পরে আলাদা command-এ ওঠা <code>laser_Warning</code> node পায়, যে সামনের cone-এর সবচেয়ে কাছের object 0.55 m-এর মধ্যে এলে <code>/beep</code>-এ buzzer command দেয় আর জায়গায় ঘুরে object-মুখী হয় — আগের app folder 12-এর tracker এগিয়ে ফলো করত, guard কখনো সামনে চালায় না। L8-24 নিজে কোনো <code>/cmd_vel</code> message পাঠায় না, তাই এই পর্বে চাকা স্থির; কোনো package না মিললে robot চলতে শুরু করার আগেই construction-এ error ওঠে — early failure, নিরাপদ।","incorrect":"বিভ্রান্তি: অনেকে ভাবে এই লাইনেই merger আর filter চালু হয়ে গেছে, বা source folder-এর <code>merge_multi.launch.py</code> এডিট করলেই robot-এর আচরণ বদলাবে। আসলে path-টা পড়ে install/share-এর কপি থেকে — rebuild না করে এডিট করলে পুরনো fusion config-ই চলে, ফলে ভুল lidar topic বা ভুল frame-এ scan আসে আর <code>/scan</code> ভরে না; তখন <code>laser_Warning</code>-এর <code>registerScan</code> একবারও চলে না — সামনে দেয়াল থাকলেও buzzer নিরব, চাকা এক পাতও ঘোরে না। আরেকটা ভুল: launch হয়ে গেছে মানেই পাহারা শুরু — আসলে এই file warning node-কে চালুই করে না, সেটা README L5-এর আলাদা <code>ros2 run yahboom_M3Pro_laser laser_Warning</code> command ছাড়া ওঠে না।"},"animType":"includeChain"},{"n":4,"id":"part-04","fname":"laser_driver.launch.py","enTitle":"Return — Two Includes, Zero Nodes","lang":"python","start":26,"end":42,"flags":[],"explain":[{"a":26,"b":27,"text":"শেষ পর্বের ঘোষণা — L26-এর <code># --- THE FINAL LIST ---</code> আগের দুটো section header-এর (<code>PROGRAM 1</code>, <code>PROGRAM 2</code>) মতোই একই dash-ঘেরা format-এ লেখা। তফাত হলো: আগের দুই পর্ব শুধু দুটো file path string বানিয়েছিল (L12-16, L20-24), এই পর্ব সেই path-গুলো কাজে লাগায়। L27 বলছে program-এর list ROS 2-কে ফিরিয়ে দিয়ে <code>to start them all at once</code> — কিন্তু এই file-এর নিজস্ব একটাও program নেই; list-এ ঢুকবে শুধু দুটো include action। অর্থাৎ পুরো file-টা একটা pure orchestrator: নিজে কোনো node চালায় না, শুধু অন্য দুটো launch file-এর ঠিকানা হাজির করে দেয় — guard-এর নিজস্ব কোড এই file-এ ঢুকেই নেই।"},{"a":28,"b":28,"text":"L28 পুরো file-এর ফলাফল বয়ে আনে — <code>return</code> মানে <code>generate_launch_description()</code> (L8)-এর ফল হিসেবে ros2 launch tool পাবে ঠিক এই object-টাই। <code>LaunchDescription</code> হলো L3-এ import করা container class, আর তার constructor-কে সরাসরি একটা list literal দেওয়া হচ্ছে: opening <code>[</code> এই লাইনে, element-গুলো L30-40-এ, closing <code>]</code> L42-তে। এই list literal-এর ভেতরেই তিনটা blank line ঢুকে আছে — L29, L35, L41; bracket খোলা থাকায় Python-এর চোখে তিনটাই সম্পূর্ণ বৈধ, কাজ শুধু দুটো element-কে চোখে আলাদা করে দেখানো, execution-এ কোনো প্রভাব নেই (L35-এর শেষে কিছু trailing space-ও আছে — source fidelity)। Folder 10-এর <code>merge_multi.launch.py</code> আলাদা আলাদা list বানিয়ে জোড়া দিয়েছিল; এখানে পথ উল্টো — inline list, দুটো element সরাসরি বন্ধনীর ভেতরে। আর মনে রেখো: এই লাইন চলছে construction phase-এ — list-টা এখন শুধু বানানো হচ্ছে, কিছুই চালু হচ্ছে না; চালু করার কাজ পরে run phase-এ ঘটবে।"},{"a":30,"b":31,"text":"List-এর প্রথম element-এর আগের comment। <code># 1.</code> নম্বরটা ক্রম শেখাচ্ছে: merger আগে, filter পরে — এই ক্রম পাইপলাইনের গল্পের সাথে মেলে। L31 বলছে এই include <code>the file we found above</code> চালাবে, আর তার কাজ দুটো lidar-এর data জোড়া দেওয়া — comment-এর ভাষায় ওটা <code>stitches the front and back lasers together into one 360-degree map</code>। <code>found above</code> মানে L12-16-এ construction time-এই বসে যাওয়া <code>laser_merge_launch_file</code> path — কোনো lazy substitution নয়, string তখনই final। Folder 10-এ আমরা এই file-এর ভেতরটা লাইন ধরে পড়েছি, folder 09-এ দেখেছি একটা lidar একটাই দিক দেখে — তাই 360-degree দেখতে হলে এই জোড়া ছাড়া উপায় নেই। আর এই পর্বের ফল এই app-এর আসল খাবার: folder 13-এর guard পরে তার <code>/scan</code> subscription-এ (laser_Warning.py-র L24) ঠিক এই merged stream-ই <code>registerScan</code> callback-এ পাবে।"},{"a":32,"b":34,"text":"তিন লাইনের nested গঠন। বাইরে <code>IncludeLaunchDescription</code> (L4-এর import) — launch জগতের recursion tool: এক launch file-এর ভেতরে আরেকটা launch file চালানোর একমাত্র পরিষ্কার উপায়। ভেতরে <code>PythonLaunchDescriptionSource(laser_merge_launch_file)</code> (L5-এর import) — এটা জানিয়ে দেয় অন্তর্ভুক্ত file-টা Python launch file, YAML বা XML launch source নয়। সবচেয়ে ভেতরে path string। Run phase-এ framework এই action execute করতে গিয়ে ওই file import করে তার নিজের <code>generate_launch_description()</code> ডাকে — অর্থাৎ প্রতিটা included file-এর নিজের construction আর run phase আলাদা করে চলে; ভেতরের গল্পটা folder 10-এর, এখানে সেটা illustrative। L34-এর <code>),</code> এই include-টা বন্ধ করে কমা সহ — কমাটাই list-এর দুই element-এর বিভাজক।"},{"a":36,"b":37,"text":"দ্বিতীয় element-এর comment — <code># 2.</code> বলছে এটা পাইপলাইনের দ্বিতীয় ধাপ। L37-এর ব্যাখ্যা folder 10-এর filter-এর কাজের সাথে মেলে: ওটা <code>removing \"blind spots\" (like the robot's own arm)</code> — মানে fused scan-এর ভেতর robot-এর নিজের গা বা arm-এর reflection থেকে আসা ভুয়া কাছের রিডিং বাদ দেওয়া হয়। এই app-ে ধাপটা বিশেষ গুরুত্ব পায়, কারণ guard <code>laser_Warning</code> সামনের cone-এর সবচেয়ে কাছের object-এর দূরত্ব <code>ResponseDist</code> মান 0.55 m-এ পৌঁছালে বা তার নিচে নামলেই <code>/beep</code> topic-এ buzzer command পাঠায় আর জায়গায় ঘুরতে শুরু করে — filter না থাকলে node-টা robot-এর নিজের arm-এর ভুয়া রিডিংকেই সবচেয়ে কাছের object ভেবে বসে, ফলে alarm zone-এর ভেতর অদৃশ্য শত্রু দেখে buzzer আটকে বাজতে থাকবে আর robot অনবরত জায়গায় ঘুরবে (illustrative)। আর <code>the file we found above</code> এখানে L20-24-এর <code>laser_filter_launch_file</code> path-কেই বোঝায় — একই construction-time নিয়ম, string আগেই বসে আছে।"},{"a":38,"b":40,"text":"দ্বিতীয় include — গঠনে হুবহু প্রথমটার মতো, শুধু সবচেয়ে ভেতরের argument আলাদা: <code>laser_filter_launch_file</code>। দুটো action দেখতে অভিন্ন হলেও ওরা দুটো সম্পূর্ণ আলাদা file খুলবে — একটা <code>ira_laser_tools</code> package থেকে, আরেকটা <code>yahboom_laser_filter</code> package থেকে। Run phase-এ framework list-এর ভেতর দিয়ে উপর থেকে নিচে action execute করে, তাই merger আগে চালু, filter পরে (এই run-phase ক্রম illustrative), আর ক্রমটা অর্থবহ — merger-এর output stream-ই filter-এর input। ছোট নজরদারি: L34 প্রথম element-এর পরে কমা দিয়েছিল, কিন্তু L40-এ <code>)</code>-এর পরে কমা নেই — শেষ element-এর পরে Python কমা ছাড়াই চলে যায়। তবে এটা শুধু action-এর ক্রম, কোনো synchronization নয়: ROS 2-তে একটা process সামান্য আগে-পরে উঠলেও publisher-subscriber পরে মিলে যায়, এই কারণে launch ভেঙে পড়ে না।"},{"a":42,"b":42,"text":"File-এর শেষ লাইন <code>])</code> — দুটো bracket একসাথে বন্ধ, bracket ladder-এর শেষ ধাপ (এই লাইনের পরে file-এ কোনো trailing newline-ও নেই)। ভেতরের <code>]</code> L28-এ খোলা list literal বন্ধ করে, বাইরের <code>)</code> <code>LaunchDescription</code> constructor call বন্ধ করে, আর তখনই <code>return</code> statement সম্পূর্ণ হয়। হিসাবটা গুনে দেখো: L28-এর <code>LaunchDescription([</code> দুটো bracket খুলেছিল, L34-এর <code>),</code> প্রথম include বন্ধ করেছে, L40-এর <code>)</code> দ্বিতীয়টা, L42 বাকি দুটো বন্ধ করে সব মিলিয়ে দিয়েছে; L41-এর blank তার স্বভাবসিদ্ধ purely visual ভূমিকাতেই ছিল। পুরো file-এর সারমর্ম এখানেই: construction phase-এ দুটো path string, run phase-এ merger-তারপর-filter দুটো include action (illustrative), আর নিজের node একদম zero — L6-এ import করা <code>Node</code> কখনো ব্যবহারই হয়নি, ওই লাইনের comment নিজেই বলে দিয়েছিল <code>imported just in case it's needed later</code>। একটা ঐতিহাসিক মন্তব্য: এই driver file-টা আগের দুই app-এর সঙ্গেই byte-identical — folder 11-এ একই chain <code>laser_Avoidance</code>-কে (বাধা এড়ানো), folder 12-এ <code>laser_Tracker</code>-কে (object ফলো করা) সেবা দিয়েছিল; এই folder 13-এ node-টা <code>laser_Warning</code> — 0.55 m-এর ভেতরে ঢুকলে বেজে ওঠে আর জায়গায় ঘুরে নিজেকে সামলায়। Driver অপরিবর্তিত থাকতে পারে কারণ sensor chain সব ক্ষেত্রেই এক — পার্থক্য শুধু সেই fused <code>/scan</code> কে খায়। আর স্পষ্ট থাকো: <code>laser_Warning</code>-কে এই launch file তোলে না — README-র L3 command শুধু sensor chain জাগায়; warning node-টা আসে README L5-এর <code>ros2 run yahboom_M3Pro_laser laser_Warning</code> থেকে।"}],"math":null,"robot":{"correct":"Real robot-এ এক command-এ পুরো sensing pipeline ওঠে: run phase-এ list-এর ক্রম মেনে merger আগে চালু হয়ে সামনে-পেছনের দুটো lidar-এর raw scan জুড়ে 360-degree fused <code>/scan</code> বানায়, তারপর filter robot-এর নিজের arm-এর ভুয়া কাছের রিডিং বাদ দিয়ে stream পরিষ্কার করে (ক্রমটা illustrative) — terminal-এ দুটো included launch-এর process log নামতে থাকে (illustrative)। ফলে আলাদাভাবে <code>ros2 run</code> করা <code>laser_Warning</code> node-এর <code>registerScan</code> একটা পরিষ্কার <code>/scan</code> পায়: সামনের cone-এর সবচেয়ে কাছের valid object 0.55 m-এর বাইরে থাকলে <code>/beep</code>-এ 0 যায়, buzzer চুপ; 0.55 m-এ পৌঁছালে বা তার নিচে নামলে buzzer বেজে ওঠে, আর object-টা মোটামুটি সোজা সামনে না থাকলে (L115-এর turn deadzone পেরোলে) robot দাঁড়িয়ে সেই দিকে ঘোরে — linear.x কখনোই সেট হয় না, তাই এক পা-ও এগোয় না। এই file নিজে কোনো <code>/cmd_vel</code> বা <code>/beep</code> message পাঠায় না, তাই এটা চালু করলেই robot-এর চাকা নড়ে না, buzzer-ও শব্দ করে না — শুধু তার চোখ খোলে।","incorrect":"সাধারণ ভুল: এই launch file-টাই guard চালায় ভেবে নেওয়া। আসলে এর ভেতরে একটাও Node action নেই, শুধু দুটো include; <code>laser_Warning</code> node README L5-এর আলাদা <code>ros2 run yahboom_M3Pro_laser laser_Warning</code> command ছাড়া ওঠে না — সেটা না চালালে sensor chain পুরো চলুক, <code>/scan</code> ভরে থাকুক, lidar ঘুরতে থাকুক, সামনে হাত 0.4 m দূরে ধরে রাখলেও buzzer একটা শব্দও করবে না, চাকা নড়বে না। আরেকটা ভুল: filter include বাদ দিলে সময় বাঁচে ভাবা — blind spot রিডিং fused scan-এ থেকে গেলে guard robot-এর নিজের arm-কেই সামনের সবচেয়ে কাছের object ভেবে ফেলতে পারে, ফলে 0.55 m alarm zone-এর ভেতর অদৃশ্য target দেখে buzzer আটকে বাজতে থাকবে আর robot অনবরত জায়গায় ঘুরতে থাকবে (illustrative)।"},"animType":null},{"n":5,"id":"part-05","fname":"laser_Warning.py","enTitle":"Warning Node — Module Head","lang":"python","start":1,"end":16,"flags":[],"explain":[{"a":1,"b":3,"text":"L1-এর <code>#ros lib</code> হলো দুই comment-block-এর প্রথম নামফলক — নিচের পাঁচটা ROS 2 import এর অধীনে সাজানো। <code>import rclpy</code> মূল ROS 2 client library-টি লোড করে, আর <code>from rclpy.node import Node</code> base class Node-টি আনে যেটার উপর L18-এ <code>class laserWarning(Node)</code> দাঁড়াবে। node-এর spin, parameter, subscription, publisher — সবের শিকড় এই দুই লাইনে; এদের ছাড়া script-টি ROS 2 graph-এ ঢুকতেই পারত না।"},{"a":4,"b":5,"text":"<code>from geometry_msgs.msg import Twist</code> হলো velocity message-এর type: <code>linear.x</code> আর <code>angular.z</code> field বহন করে, L30-এর <code>/cmd_vel</code> publisher পরে চাকার দিকে ঠিক এটাই পাঠাবে। <code>from sensor_msgs.msg import LaserScan</code> হলো lidar-এর <code>/scan</code> message-এর type — শুধু <code>ranges</code> array নয়, <code>angle_min</code> আর <code>angle_increment</code> metadata-ও সঙ্গে থাকে, যেগুলোর উপর L65-এর degree-হিসাব দাঁড়াবে। guard-এর পুরো সিদ্ধান্ত-চক্র এই দুই data-source মিলিয়েই চলে: দূরত্ব LaserScan থেকে, প্রতিক্রিয়া Twist-এ।"},{"a":6,"b":6,"text":"<code>from std_msgs.msg import UInt16</code> — L6-এর নিজের comment-টিই ব্যাখ্যা করে: এটি buzzer ON/OFF করার message type। folder 12-এর laser_Tracker-এ এই channel ছিলই না; guard-এর সবচেয়ে বড় সংযোজন এখানেই, কারণ L32-তে <code>/beep</code> publisher এই type-ই ব্যবহার করে। unsigned 16-bit পূর্ণসংখ্যা হিসেবে এর মান ঋণাত্মক হতে পারে না; <code>UInt16()</code> constructor-এর default value হলো 0, অর্থাৎ beep OFF — L95-এর else-branch ঠিক এই default-এ ভর করেই buzzer চুপ করায়, আর alarm-এ <code>b.data = 1</code> মানে beep ON।"},{"a":8,"b":10,"text":"L8-এর দ্বিতীয় নামফলক <code>#commom lib</code> — <code>common</code>-এর typo source-এই আছে, কখনো ঠিক করা হয়নি। <code>import math</code> দেয় <code>math.pi</code>, যেটা মাত্র কয়েক লাইন পরেই L16-এর conversion factor-এ কাজে লাগবে। <code>import numpy as np</code> array-গণিতের জন্য — L56-এ <code>np.array(scan_data.ranges)</code> দিয়ে beam-দের দূরত্বের array তৈরি হয়, তারপর min আর index-খোঁজার হিসাব ওই array-র উপরেই চলে।"},{"a":11,"b":12,"text":"L11 <code>import time</code> আর L12 <code>from time import sleep</code> — verified সত্য: পুরো file-এ এই দুটি আর কোথাও ব্যবহৃত হয় না, দুটোই dead import। সম্ভবত vendor-এর অন্য কোনো script থেকে পাওয়া উত্তরাধিকার। runtime-খরচ নগণ্য, কিন্তু পাঠক ভাবে নিচে কোথাও delay বা timing-লজিক আছে — সেই ভুল ইঙ্গিতটাই আসল ক্ষতি, কারণ guard-এর timing আসলে একটিই: প্রতিটি <code>/scan</code> message-এর আগমন।"},{"a":13,"b":13,"text":"<code>from yahboom_M3Pro_laser.common import *</code> — vendor-এর comment বলছে custom Yahboom tools। এই star-import থেকে মূলত দুটি নাম এই script-এ কাজে লাগে: <code>Bool</code> (L26-এর <code>/JoyState</code> subscription-এর message type) আর <code>SinglePID</code> (L48-এ <code>SinglePID(3.0, 0.0, 5.0)</code>)। module-টি এই folder-এ নেই, তাই এর ভেতরের implementation অজানা — এই label inferred। star-import নিজেই ঝুঁকি: কোন কোন নাম namespace-এ ঢুকছে, শুধু এই লাইন পড়ে বলা যায় না।"},{"a":14,"b":15,"text":"<code>import os</code> পরে exit_pro function-এ (L127-132) কাজে লাগবে — <code>os.system(cmd)</code> দিয়ে node-এর বাইরে থেকে shell-এ zero <code>/cmd_vel</code> পাঠানো brake-টি সেখানেই চলে। এরপরই import-পর্ব শেষের স্বীকৃতি: L15 <code>print (\"improt done\")</code> — <code>import</code>-এর typo এবং print-এর নামের পরের space দুটোই source-এ আছে, পাশের comment-টিও নিজেই স্বীকার করে typo-টা। module load-এর মুহূর্তে console-এ ঠিক এই লাইনটি ছাপা পড়ে, তাই এটি দেখা মানে L2 থেকে L14 পর্যন্ত প্রতিটি import সফল হয়েছে।"},{"a":16,"b":16,"text":"L16 <code>RAD2DEG = 180 / math.pi</code> — module-level constant, মান প্রায় 57.29578 degree per radian। LaserScan-এর সব angle raw অবস্থায় radian-এ আসে, অথচ guard-এর প্রতিটি সিদ্ধান্ত degree-এ: 45.0-এর <code>LaserAngle</code> cone, minDistIDList-এ জমা কোণ। L65-এ <code>(scan_data.angle_min + scan_data.angle_increment * i) * RAD2DEG</code> হিসাবে ঠিক এই constant-টিই প্রতিটি beam-এর কোণ একক-বদল করে দেয় — একবার define, তারপর প্রতিটি scan-এর প্রতিটি beam-এ একবার করে ব্যবহার।"}],"math":{"intro":"L16-এর এক লাইনেই এই Part-এর গণিত: LaserScan-এর angle আসে radian-এ, কিন্তু guard-এর cone-যাচাই আর steering-হিসাব degree-এ। প্রশ্ন হলো 180/math.pi সংখ্যাটি কেন ঠিক দুই এককের সেতু, এবং একটি beam-এর উপর এটি ঠিক কী মান দেয়।","levels":[{"label":"Level 1 — Units ও π-identity","latex":"\\[ \\pi\\ \\mathrm{rad} = 180^{\\circ}, \\qquad 1\\ \\mathrm{rad} = \\frac{180}{\\pi}\\ \\mathrm{deg} \\approx 57.29578\\ \\mathrm{deg} \\]","text":"একটি অর্ধবৃত্ত একই সাথে π radian আর 180 degree — এই identity-টিই একক-বদলের factor দেয়: 180/pi। L16-এর <code>RAD2DEG = 180 / math.pi</code> সংখ্যাটি module load-এর সময় একবার হিসাব হয়ে যায়, আর আর কখনো বদলায় না; radian-কে degree-এ নিতে হলে শুধু এটি দিয়ে গুণ করতে হয়।"},{"label":"Level 2 — Linear রূপান্তর","latex":"\\[ \\theta_{\\mathrm{deg}} = \\theta_{\\mathrm{rad}} \\times \\frac{180}{\\pi} = \\theta_{\\mathrm{rad}} \\times \\mathit{RAD2DEG} \\]","text":"রূপান্তরটি একটি বিশুদ্ধ রৈখিক গুণ — কোনো offset নেই, শূন্য শূন্যেই থাকে, ঋণাত্মক কোণ ঋণাত্মকই থাকে। এ কারণেই L65-এ raw radian-মানের উপর একবার গুণ করলেই beam-এর কোণ degree-এ চলে আসে, আর সেটি সরাসরি 45.0-এর <code>LaserAngle</code> parameter-এর সাথে তুলনা করা যায় — degree-এর ভেতরে থাকলে গুণ করলে মান বাড়ে, ভাগ করলে কমে, এটাই পরে ভুল ধরার মূল লক্ষণ।"}],"numeric":[{"latex":"\\[ 0.0174533\\ \\mathrm{rad} \\times 57.29578 = 1.0^{\\circ} \\]","text":"illustrative fused-ring convention ধরে (FACTS-13 §3): <code>angle_increment = π/180</code>, মানে প্রতি ধাপে কোণ বাড়ে ঠিক 0.0174533 radian। এই এক ধাপকে RAD2DEG দিয়ে গুণ করলে ফল দাঁড়ায় ঠিক 1.0 degree — অর্থাৎ 360-beam ring-এ beam index i প্রতিবার এক পূর্ণ degree-ধাপে এগোয়, আর minDistIDList-এ জমা কোণগুলো পূর্ণসংখ্যা degree-এ পড়ে (যেমন +14 বা -20)। module-head-এর এই ধ্রুবকটিই scan-এর অবিন্যস্ত radian-ভিড়কে পড়ার মতো degree-স্কেলে সাজায়।"}],"mapping":[{"code":"angle = (scan_data.angle_min + scan_data.angle_increment * i) * RAD2DEG","math":"\\( \\theta_i = \\left(\\theta_{\\min} + i\\,\\Delta\\theta\\right) \\times 57.29578\\ \\mathrm{deg} \\)","text":"L16-এ define হওয়া constant-টির কাজে নামার জায়গা L65: scan-এর radian metadata (<code>angle_min</code>, <code>angle_increment</code>) আর beam index i জুড়ে গুণ করে beam-এর degree angle বানায়। এর ঠিক পরেই L68-এর cone-টেস্ট <code>abs(angle) &lt; self.LaserAngle</code> সেই degree-মানটিকে 45.0-এর সাথে তুলনা করে — অর্থাৎ module-head-এর এই এক ধ্রুবক ছাড়া সামনের cone-এর পুরো ধারণাটাই অর্থ হারাত।"}],"failure":["factor উল্টে দিলে — যেমন <code>math.pi / 180</code> লেখা হলে (মান প্রায় 0.01745) — কোণের পুরো স্কেলটাই স্থূল হয়ে যায়: প্রতি degree-ধাপে ফল নামে মাত্র ~0.0003 মাপে (1 degree beam পড়ে 0.0003046-তে, 14 degree-রটা 0.00427-তে, 45 degree-রটা 0.0137-তে), তাই ±180 degree-র পুরো ring-টাই ±0.055-এর ভেতরে এসে পড়ে (180 degree beam = 0.0548) — সবচেয়ে চরম beam-ও 45-এর অনেক নিচে। ফলে L68-এর <code>abs(angle) &lt; self.LaserAngle</code> পুরো ring-এর প্রতিটি beam-এর জন্যই সত্য হয়ে যায়, front cone আর front থাকে না — পেছনের obstacle-এও robot হঠাৎ জায়গায় ঘুরে দাঁড়ায় আর বিনা কারণে buzzer বাজে।","একই কোণে RAD2DEG দুইবার গুণ করা হলে (double conversion) 1 degree হয়ে যায় প্রায় 57.3 degree, তাই <code>abs(angle) &lt; 45</code> আর কারও জন্য সত্য নয় — কেবল সোজা সামনের 0 degree beam-টি ঢোকে। এক পাশে সরে থাকা obstacle প্রতিটি scan-এ বাদ পড়ে, minDistList অনেক scan-এই খালি থাকে বলে L73-এর <code>return</code> চলে যায় — robot নড়েও না, beep-ও করে না, যদিও বাধা ধাক্কা খাওয়ার দূরত্বে।"]},"robot":{"correct":"ros2 run দিয়ে node চালালে module load-এর সময়েই এই Part-টি চলে এবং console-এ <code>improt done</code> ছাপা পড়ে — এটাই এই পর্যায়ের একমাত্র দৃশ্যমান ফল। এই চালানোর পথটি আসে package-এর setup.py entry point থেকে — ফাইলটি এই folder-এ নেই, আর script-এ <code>__main__</code> guard-ও নেই, তাই সংযোগটি inferred। চাকা, lidar driver, buzzer — কারো দিকেই এখনো কোনো command যায় না, কারণ node instance তৈরি হয় অনেক পরে (L18-এর class, পরে main-এর instantiate)। কিন্তু বাক্সগুলো তৈরি হয়ে যায়: <code>/scan</code>-এর LaserScan, <code>/JoyState</code>-এর vendor Bool, <code>/cmd_vel</code>-এর Twist, আর guard-এর নিজের <code>/beep</code> channel-এর UInt16 — পরের Part-গুলোর প্রতিটি subscription আর publisher এই import-গুলোর উপর দাঁড়ায়। <code>RAD2DEG</code>-ও এখানে একবার 57.29578 মানে সেট হয়ে যায়, যেটা L65-এ প্রতিটি beam-এর degree-হিসাবে খরচ হবে।","incorrect":"vendor package-টি robot-এ install করা না থাকলে L13-এর star-import-ই <code>ImportError</code> ছুড়ে দেয় — <code>improt done</code> কখনো ছাপা হয় না, node জন্মায়ই না; obstacle 10 cm দূরত্বে এসেও buzzer শব্দ করে না, চাকায় কোনো ব্রেক-বা-মোড় পড়ে না, lidar যা পাঠাচ্ছে তা শোনার কেউ থাকে না। আর factor-টি ভুল হলে শরীরে লক্ষণ আরও প্রকট: cone পুরো ring হয়ে গেলে পেছনের obstacle-এও robot হঠাৎ জায়গায় ঘুরে যায় আর বিনা কারণে beep বাজে; double conversion হলে উল্টোটা ঘটে — সামনে সরে থাকা বাধায় সাড়া নেই, robot পর্যন্ত এগিয়ে ধাক্কা মারে।"},"animType":null},{"n":6,"id":"part-06","fname":"laser_Warning.py","enTitle":"Constructor — Subscriptions & Publishers","lang":"python","start":17,"end":32,"flags":[],"explain":[{"a":17,"b":19,"text":"<code>class laserWarning(Node):</code> — L16-এর <code>RAD2DEG</code> constant-এর পরে L17-এর blank line দিয়ে module-এর মাথা (L1-16: comment, import, <code>print</code>, constant) শেষ, এখান থেকে ফাইলের আসল দেহ — behavior class-টা। L3-এ আনা <code>Node</code>-কে inherit করাতেই <code>create_subscription</code>, <code>create_publisher</code>, <code>declare_parameter</code> — node-হওয়ার সব যন্ত্রপাতি এই class-এর হাতে এসে যায়। <code>def __init__(self,name):</code> — constructor-এর একটাই argument: <code>name</code>, বাইরে থেকে স্পষ্ট করে দিতে হয়। এই <code>name</code>-ই পরে <code>main()</code> থেকে আসবে — <code>laserWarning(\"laser_Warnning_a1\")</code> (L136) — মানে ROS 2-এর নাম-জগতে node-টার নাম <code>laser_Warnning_a1</code> (source-এ double-n typo), অথচ Python class-এর নাম <code>laserWarning</code>; দুটো আলাদা জিনিস, একটাও অন্যটা থেকে তৈরি হয় না।"},{"a":20,"b":20,"text":"<code>super().__init__(name)</code> — inheritance-এর সবচেয়ে জরুরি লাইন। এটা না চললে <code>Node</code>-এর নিজের constructor চলেই না, <code>self</code>-এর ভেতরে node-হওয়ার অভ্যন্তরীণ তালিকাই তৈরি হয় না — পরের লাইনে <code>self.create_subscription(...)</code> ডাকতেই <code>AttributeError</code>-জাতীয় error উঠে আসত। <code>super()</code> মানে এখানে parent class <code>Node</code>; <code>name</code> হাতবদল হতেই node-এর নাম পাকা হয়ে যায়। ক্রমটাও নিয়মমাফিক: parent-এর constructor আগে, নিজের জিনিসপত্র পরে — Python inheritance-এর প্রথা। আর মনে রাখুন, import pass-এ শুধু class-টা ও তার def-গুলো bind হয়; এই constructor-এর দেহ চলে run phase-এ, <code>main()</code> যখন instance বানায় তখন।"},{"a":21,"b":23,"text":"<code># --- CREATING SUBSCRIBERS (Listeners) ---</code> আর <code># Listen to the 360-degree LiDAR scanner</code> — দুটোই comment, কিছু চালায় না; কিন্তু লেখকের প্রতিমানটা এখানেই: publisher একটা রেডিও স্টেশন, subscription একটা শ্রোতা — শ্রোতা নিজে কথা বলে না, message এলেই শুধু নিজের callback জাগায়। (ছোট একটা source-fidelity নোট: L21-এর blank line-টার শেষে কিছু trailing space আছে — চোখে প্রায় অদৃশ্য, চালানোয় কিছু যায় আসে না।) \"360-degree\" দাবিটা এই ফাইল নিজে সত্যি করে দেখাতে পারে না: এই node কোনো lidar চালায় না। README-র L3 launch চালালে এই folder-এরই <code>laser_driver.launch.py</code> (folder 11/12-এর সাথে byte-identical) folder 10-এর merger+filter chain জাগায় — সামনে-পেছনে দুই lidar-এর কাঁচা scan জুড়ে একটা পূর্ণ 360-degree ring বানায়, blind-spot পাকা করে — guard শুনবে সেই ফলাফল। চোখ ওই chain-এর, সিদ্ধান্ত এই ফাইলের; আর warning node-টা launch নিজে চালায় না — তাকে জাগায় README-র L5 command।"},{"a":24,"b":24,"text":"<code>self.sub_laser = self.create_subscription(LaserScan,\"/scan\",self.registerScan,1)</code> — প্রথম শ্রোতা: চোখ। চারটা argument: message-এর ধরন <code>LaserScan</code> (L5-এ আনা), topic <code>\"/scan\"</code> — merger+filter chain-এর শেষ ফলাফলের ঠিকানা, কোনো raw lidar topic নয়; callback <code>self.registerScan</code> (L54-এ সংজ্ঞাত, দেহ L124 পর্যন্ত — এই ফাইলের মগজ: সামনের ±45-degree cone-এর মধ্যে সবচেয়ে কাছের object খুঁজে 0.55 m-এর danger zone-এ বিপদ নির্ণয়, বাঁশির সিদ্ধান্ত, আর ঘুরে ওই object-টার দিকে মুখ ফেরানোর পুরো হিসাব ওখানে); আর শেষের <code>1</code> = queue depth — পুরনো message জমিয়ে না রেখে সবসময় সবচেয়ে নতুন scan-টাই কাজে লাগানো। পাহারায় এটাই চাই: কয়েক scan আগের দূরত্ব মানে অতিথি আসলে আর ওই দূরত্বে নেই।"},{"a":25,"b":26,"text":"<code># Listen to the joystick (so you can pause the AI and drive manually)</code> আর <code>self.sub_JoyState = self.create_subscription(Bool,'/JoyState', self.JoyStateCallback,1)</code> — দ্বিতীয় শ্রোতা: মানুষের হাত। <code>True</code> এলে <code>JoyStateCallback</code> (L50-52) শুধু একটা flag উল্টে দেয়, আর <code>registerScan</code> সেই flag পেলে প্রতিটা scan-তে সব-শূন্য <code>Twist</code> publish করে ফিরে আসে (L81-83) — AI pause, চাকা joystick-এর হাতে। সূক্ষ্ম জায়গাটা <code>Bool</code>-এর পরিচয়: এটা std_msgs-এর চেনা Bool নয়। L13-এর <code>from yahboom_M3Pro_laser.common import *</code> star-import থেকে আসা yahboom-এর নিজস্ব <code>Bool</code> — std_msgs থেকে এই ফাইলে এসেছে শুধু <code>UInt16</code> (L6, buzzer-এর message) — <code>Bool</code> নয়; L13-এর vendor comment-ও ঠিক সেই কথাই বলে দেয়। common module-টা এই folder-এ নেই, তাই <code>.data</code>-র বাইরে তার ভেতরটা অজানা — field-এর নাম আন্দাজে বানানো যাবে না। টপোলজি তবু folder 11/12-এর সাথে হুবহু এক: একই <code>/JoyState</code> শ্রোতা, depth-ও <code>1</code>। আর এই app-এর নিজস্ব টুইস্ট: L83-এর return এসে alarm block-এর (L89-95) <i>আগে</i> — মানে Joy ধরা অবস্থায় <code>/beep</code>-ও refresh হয় না, buzzer তার শেষ মানটায় latched থাকে।"},{"a":27,"b":29,"text":"<code># --- CREATING PUBLISHERS (Radio Stations) ---</code> আর <code># Tell the wheels to move</code> — L27-এর blank line (এর শেষেও trailing space) পার করে শ্রোতার পাল্লায় উল্টো দিক: রেডিও স্টেশন। বাক্সের বাইরে যাওয়ার রাস্তা এই class-এ দুটো — চাকা আর বাঁশি। কঙ্কালটা এক নিঃশ্বাসে মনে রাখুন: দুই কান ভেতরে (<code>/scan</code>, <code>/JoyState</code>), দুই মুখ বাইরে (<code>/cmd_vel</code>, <code>/beep</code>)। folder 11-এর laser_Avoidance-ও, folder 12-এর laser_Tracker-ও — দুজনেরই wiring ছিল দুই কান-এক মুখ; guard-এ সেই চেনা শরীরে নতুন একটা মুখ যোগ হলো: পাহারাদারের গলা। সঙ্গের graph-এ চোখে পড়ার মতো পরিবর্তন এটাই — বাকি সব পথ আগের folder থেকে চেনা।"},{"a":30,"b":30,"text":"<code>self.pub_vel = self.create_publisher(Twist,'/cmd_vel',1)</code> — প্রথম মুখ: হাত। message-এর ধরন <code>Twist</code> (L4): ভেতরে <code>linear</code> আর <code>angular</code> দুই field, প্রতিটাতে x, y, z; মেঝের robot-এ কাজে লাগে দুটোই — <code>linear.x</code> (সামনে-পেছনে, মিটার/সেকেন্ড) আর <code>angular.z</code> (নিজের কেন্দ্র ঘিরে ঘোরা, radian/সেকেন্ড)। তবে এই ফাইলের চরিত্রটা এখানেই ফুটে ওঠে: গোটা <code>registerScan</code>-এ <code>linear.x</code> কোথাও assign-ই হয় না (L123-এর comment নিজেই স্বীকার করে) — মানে <code>/cmd_vel</code>-এর সব message চলে যাবে শুধু ঘোরা নিয়ন্ত্রণ করতে; guard কখনো সামনে এগোয় না, জায়গায় ঘুরে মুখ ফেরায়। queue depth আবার <code>1</code>: পুরনো কমান্ড জমানোর দরকার নেই, শেষ সিদ্ধান্তটাই সব।"},{"a":31,"b":32,"text":"<code># Tell the buzzer to beep!</code> আর <code>self.pub_Buzzer = self.create_publisher(UInt16,'/beep',1)</code> — দ্বিতীয় মুখ: গলা। folder 12-এর tracker-এর সাথে পার্থক্যের মূল এই এক লাইনেই: ওখানে চোখ-কান-হাত সব ছিল, গলা ছিল না; পাহারাদারের গলা লাগবেই, আর সেটা <code>/beep</code>। <code>UInt16</code> L6-এ আনা — ওই লাইনের vendor comment বলে দেয়, এটাই buzzer ON/OFF-এর message type। 16-bit unsigned integer হিসেবে মান 0 থেকে 65535 পর্যন্ত যেতে পারলেও এই ফাইল ব্যবহার করে মাত্র দুটো মান: <code>UInt16()</code>-এর default 0 = beep OFF (L95-এর else-শাখা প্রতি scan-এ এই শূন্যই পাঠায়), আর <code>b.data = 1</code> = ON (L90-92) — অর্থাৎ বাঁশির সিদ্ধান্ত সর্বদা দুই-মানের: সবচেয়ে কাছের object 0.55 m-এর danger zone-এ ঢুকলে 1, নাহলে 0। আর cone ফাঁকা হলে L73-এর return-এ দুই মুখই চুপ — <code>/beep</code> তখন শেষ মানেই latched। এই লাইন শেষ হতেই node-টার নেটওয়ার্ক-কঙ্কাল পাকা; L34 থেকে শুরু হবে parameter-ঘোষণা — গতি আর দূরত্বের সীমা নিয়ে।"}],"math":null,"robot":{"correct":"main()-এর L136-এ <code>laserWarning(\"laser_Warnning_a1\")</code> call হলে ঠিক এই constructor-টাই চলে: <code>super().__init__(name)</code> node-কে নাম দেয় — <code>ros2 node list</code>-এ <code>laser_Warnning_a1</code> দেখা যায় — তারপর দুই subscription আর <b>দুই</b> publisher রেজিস্টার হয়ে যায়; console-এ L137-এর <code>start it</code> ছাপা হলে বোঝা যায় জন্ম নিঃশব্দে সফল। README-র L3 launch আগে চালানো থাকলে merger+filter chain-এর পূর্ণ 360-degree <code>/scan</code> ring আসতে শুরু করে — প্রতিটা scan <code>registerScan</code>-কে জাগায়, joystick ধরলে <code>/JoyState</code> <code>JoyStateCallback</code>-কে জাগায়, আর সিদ্ধান্ত বেরোয় দুই পথে: <code>/cmd_vel</code>-এ <code>Twist</code> যায় চাকার motor-এ, <code>/beep</code>-এ <code>UInt16</code> যায় buzzer-এ। উদাহরণ-দৃশ্যে (illustrative) সোজা সামনে 0.48 m দূরে object হলে (Wave C) বাঁশি বাজে আর চাকা স্থির — <code>linear.x</code> কখনো সেট হয় না, এবং 0° কোণে <code>angular.z</code>-ও deadzone-এ শূন্য; 0.50 m @ -20° হলে (Wave D) বাঁশির সঙ্গে জায়গায় ডানে ঘোরা, <code>angular.z</code> ≈ -0.417 rad/s।","incorrect":"<code>super().__init__(name)</code> বাদ পড়লে পরের লাইনেই <code>AttributeError</code> — console-এ traceback, <code>ros2 node list</code>-এ <code>laser_Warnning_a1</code> নামটা আসবেই না, <code>/cmd_vel</code>-ও <code>/beep</code>-ও জন্মাবে না: চাকা স্থির, বাঁশি চির-নীরব। আরেকটা ভুল ধারণা: <code>Bool</code>-কে std_msgs-এর Bool ভেবে অন্য ধরনের message পাঠানো — তখন হয় message-ই callback পর্যন্ত পৌঁছাবে না, নয়তো L51-এর isinstance guard সেটাকে ফেরত দেবে; <code>Joy_active</code> কখনো <code>True</code> হবে না, মানুষ joystick ধরেও AI-কে থামাতে পারবে না — robot শেষ সিদ্ধান্তের ঘোরা আর বাঁশির বাজনাতেই থাকবে। এই app-এর নিজস্ব ভুল: <code>UInt16()</code> বানালেই বাঁশি বাজবে ভাবা — default মান 0 মানে beep OFF; কাছের object 0.48 m-এ danger zone-এর ভেতরে ঢুকে console-এ <code>minDist: </code>-এর পাশে 0.48 ছাপা হচ্ছে, অথচ বাঁশি চুপ — <code>b.data = 1</code> (L91) ছাড়া আওয়াজ ওঠে না, পাহারাদার চোখে দেখছে কিন্তু গলা দিয়ে সতর্কতা বেরোচ্ছে না। আর merger-এর কাঁচা topic-এ কান দিলে ring-এর অর্ধেক খালি আসবে (illustrative) — guard অপূর্ণ দুনিয়া পাহারা দেবে।"},"animType":"subPubGraph"},{"n":7,"id":"part-07","fname":"laser_Warning.py","enTitle":"Four Parameters — Declare & Get","lang":"python","start":33,"end":43,"flags":[],"explain":[{"a":33,"b":34,"text":"L33 হলো publisher-ব্লকের পরের blank separator — এখান থেকে constructor-এর parameter-সেকশন শুরু। L34-এর banner comment ঘোষণা করে <code># --- ROS 2 PARAMETERS</code> এবং বন্ধনীতে বলে এগুলো Speed ও Distance Limits — অর্থাৎ দুটো speed-সীমা আর দুটো distance/angle-সীমা আসতে চলেছে। নিচে ঠিক চারটা declare+get pair আছে (linear, angular, LaserAngle, ResponseDist), কিন্তু verified quirk — শিরোনামের speed-অংশটি ফাঁকা প্রতিশ্রুতি: <code>self.linear</code> আর <code>self.angular</code> দুটোই assign হয়ে আর কখনো read হয় না, তাই কোনো speed limit কার্যকরই হয় না। আসল কাজ করে distance/angle জোড়া দুটি — সেগুলোই নিচের item-গুলোয়।"},{"a":35,"b":36,"text":"প্রথম জোড়া: <code>self.declare_parameter(\"linear\",0.5)</code> — node-এর parameter registry-তে <code>linear</code> নামে একটা parameter ভর্তি হয়, default 0.5 (কল্পিত অর্থে max forward speed, m/s)। পরের লাইনে <code>self.linear = self.get_parameter('linear').get_parameter_value().double_value</code> — three-step chain-টি এভাবে পড়েন: <code>get_parameter('linear')</code> নোডের Parameter object ফেরত দেয়, তার <code>get_parameter_value()</code> টাইপ-বহনকারী ParameterValue container দেয়, আর শেষের <code>.double_value</code> field plain Python float (0.5) বের করে আনে — declare-এ default যেহেতু float, তাই double variant-ই পড়তে হয়। declare না করে get করলে ROS 2 exception ছোঁড়ে, তাই প্রতিটা জোড়ায় আগে declare, পরে get; বাইরে থেকেও override করা যায় (<code>-p linear:=0.2</code> ধরনের ros-args দিয়ে)। কিন্তু L35-এর নিজের comment-ই স্বীকার করে <code>not actually used in this script, but declared</code> — verified quirk: <code>self.linear</code> এই একবারই বসে, পুরো file-এ আর read হয় না, আর কোথাও কোনো clamp নেই। ফলে এই সংখ্যার robot-এ কোনো ভৌত অস্তিত্ব নেই — guard তো আসলে কখনো forward-ই চালায় না (L123: linear.x কখনো set হয় না)।"},{"a":37,"b":38,"text":"দ্বিতীয় জোড়া একই ছাঁচে: <code>self.declare_parameter(\"angular\",1.0)</code> (comment: max turning speed), তারপর <code>self.angular = self.get_parameter('angular').get_parameter_value().double_value</code> — একই chain, মান 1.0 rad/s। এখানেও সেই verified quirk: <code>self.angular</code> assign-এর পর আর কোথাও read হয় না — এবং linear-এর মতো স্বীকারোক্তিমূলক comment-ও নেই। বাস্তবে turn কত জোরে হবে সেটা ঠিক করে অন্য পথ: L48-এর <code>SinglePID(3.0, 0.0, 5.0)</code>, তারপর L103-118-এর compute, sign-branch, deadzone আর 0.5-damping — সেই পথে কোথাও 1.0-এর সঙ্গে তুলনাই হয় না। illustrative Kp-view-এ turn-এর ceiling আসে প্রায় ±0.94 rad/s, যা কাকতালে 1.0-এর নিচে — কিন্তু সেটা enforcement নয়; gain বাড়ালে বা বড় Kd transient এলে output 1.0 পেরোতে পারে, আটকানোর কেউ নেই।"},{"a":39,"b":40,"text":"তৃতীয় জোড়া — এবার সত্যিকারের ব্যবহৃত parameter: <code>self.declare_parameter(\"LaserAngle\",45.0)</code>, read-back <code>self.LaserAngle = self.get_parameter('LaserAngle').get_parameter_value().double_value</code>। মানে front cone-এর half-width — comment বলছে <code>Width of the front cone (45 degrees left and right)</code>: robot-এর সামনের কেন্দ্র-রেখা থেকে বামে ও ডানে ৪৫ ডিগ্রি করে। একমাত্র read হয় L68-এ: <code>abs(angle) &lt; self.LaserAngle</code> — strict less-than, তাই ঠিক 45.0-ডিগ্রির beam-টি cone-এ ঢোকে না; illustrative fused ring-এ (৩৬০ beam) এই ছাঁকনি রেখে যায় মোট ৮৯টা beam। এই parameter বদলালে hardware সত্যিই অনুভব করে — যেমন LaserAngle 60 করলে পাশের object-ও tracking-এ ধরা পড়বে, robot আরও আগে ঘুরতে শুরু করবে।"},{"a":41,"b":43,"text":"চতুর্থ জোড়া: <code>self.declare_parameter(\"ResponseDist\",0.55)</code> — comment বলছে <code>The \"Danger Zone\" distance (0.55 meters)</code> — আর read-back chain <code>self.get_parameter('ResponseDist').get_parameter_value().double_value</code> দিয়ে <code>self.ResponseDist</code>-এ 0.55 বসে। এটাও সত্যিই ব্যবহৃত: L89-এর alarm শর্ত <code>minDist &lt;= self.ResponseDist and minDist != 0.0</code> — সামনের সবচেয়ে কাছের object 0.55 m বা তার কমে এলেই /beep-এ 1 যায়, buzzer বাজে (illustrative wave C: 0.48 m — beep; wave A: 0.90 m — নীরব)। L43 blank — parameter-সেকশন এখানে শেষ, constructor এবার state tracker ও PID-এর দিকে যায় (L45-এ <code>Joy_active</code>, L48-এ ang_pid)।"}],"math":null,"robot":{"correct":"Node তৈরির সময়, প্রথম /scan আসার আগেই, চারটা parameter declare হয়ে attributes-এ ওঠে — এই মুহূর্তে চাকা স্থির, lidar ঘুরছে, buzzer চুপ, console-এ নতুন কোনো print নেই। পরে কাজে লাগে দুটি: LaserAngle 45.0 ঠিক করে দেয় কোন beam-গুলো সামনে গণ্য হবে (illustrative fused ring-এ ৮৯টা), আর ResponseDist 0.55 ঠিক করে কত কাছে এলে buzzer বাজবে — 0.48 m-এ সোজা সামনে এলে (wave C, illustrative) বাজনা ওঠে আর চাকা স্থির — u = 0-তে deadzone; একটু কাত হয়ে 0.50 m-এ এলে (wave D) বাজতে বাজতে সেই দিকে ঘোরে; 0.90 m-এ বাজনা থামে — ঘূর্ণন আলাদা হিসাব, কোণ বাঁচলে তখনও ধীরে ঘুরতে পারে (wave A)। linear 0.5 আর angular 1.0 কেবল registry-র রেকর্ডে বাস করে — চাকার জগতে তাদের কোনো ভূমিকা নেই।","incorrect":"শিরোনামের Speed Limits কথাটা বিশ্বাস করে launch-এ <code>-p linear:=0.2</code> দিলে কিছুই বদলায় না — linear.x কোথাও set-ই হয় না, robot আগের মতোই একই রকম জায়গায় ঘুরে। angular-কে আসল cap ভাবলে সেটাও ভুল: PID gain বাড়ালে বা step-এ বড় Kd transient এলে angular.z সহজেই 1.0 rad/s ছাড়িয়ে যেতে পারে — কোথাও clamp নেই, সেই মানই হুবহু /cmd_vel-এ গিয়ে চাকা দুটোকে হঠাৎ জোরে ঘুরিয়ে দেয়। উল্টোদিকে ResponseDist টাইপো করে 5.5 লিখলে ৫.৫ মিটার দূরের valid object-ও বাজাতে থাকবে (সামনে কিছু না থাকলে অবশ্য চুপ — L73-এর early return), আর LaserAngle 10 করে ফেললে দৃষ্টি সংকীর্ণ হয় — সোজা সামনের object তখনও চোখে পড়ে (abs(angle) তো প্রায় 0), 0.55 m-এর ভেতরে এলে বাজেও; হারায় পার্শ্বের object — 10 ডিগ্রির বাইরের beam-গুলোই আর গণ্য হয় না, তাই কাত হয়ে আসা কাছের বাধা না দেখে robot চুপ করে থাকে।"},"animType":null},{"n":8,"id":"part-08","fname":"laser_Warning.py","enTitle":"State & the Aggressive PID","lang":"python","start":44,"end":48,"flags":[],"explain":[{"a":44,"b":44,"text":"L44 হলো constructor-এর শেষ block-এর নামফলক: <code># --- STATE TRACKERS &amp; PID CONTROLLER ---</code>। এর নিচের চারটি লাইনে দুটি জিনিস জন্মায় — একটি state flag আর একটি PID controller। এই block শেষ হলে L19-এ শুরু হওয়া <code>__init__</code>-ও শেষ: subscription দুটি (L24, L26), publisher দুটি (L30, L32), parameter-চারটি (L35-42) সব আগেই তৈরি — node-টি এখন প্রথম <code>/scan</code> message-র অপেক্ষায় সম্পূর্ণ armed।"},{"a":45,"b":45,"text":"L45 <code>self.Joy_active = False</code> — node-এর জন্মলগ্ন state। <code>/JoyState</code> subscription (L26) থেকে JoyStateCallback (L50-52) এসে এটি বদলায়: মানুষ joystick ধরলে True, ছেড়ে দিলে আবার False। ডিফল্ট False মানে চালু হওয়ার প্রথম মুহূর্ত থেকেই AI autonomous — L81-এর gate (<code>if self.Joy_active :</code>) এখনো বন্ধ নয়, তাই প্রথম <code>/scan</code> থেকেই steering চালু। উল্টো দিকটিও গুরুত্বপূর্ণ: flag-এর মান কেউ না বদলালে এই default-ই কায়েম থাকে — কোনো timeout বা স্বয়ংক্রিয় পুনরায়-সেট নেই।"},{"a":46,"b":46,"text":"L46-এর comment হুবহু: <code># This PID controller controls the steering wheel to keep the closest object centered.</code> — কিন্তু <b>steering wheel</b> অংশটি stale wording, যেমন আছে তেমনই উদ্ধৃত, সমর্থন করা হলো না: differential-drive robot-এ কোনো steering wheel নেই; মোড় আসে দুই চাকার গতির পার্থক্য থেকে, আর সেই নির্দেশ L30-এর <code>/cmd_vel</code> message-এর <code>angular.z</code> field-ই বহন করে। বাক অংশটুকু ঠিক — PID-টির লক্ষ্য সবচেয়ে কাছের object-কে সামনে কেন্দ্রে আনা; wheel ঘোরানো নয়, পুরো শরীর ঘুরে সেই কাজটি হয়।"},{"a":47,"b":47,"text":"L47 <code># It is tuned a bit more aggressively than the tracker (3.0, 0.0, 5.0)</code> — এটি একটি আসল cross-folder reference: tracker মানে folder 12-এর laser_Tracker, যার angular PID ছিল <code>SinglePID(2.0, 0.0, 2.0)</code> (Kp = 2, Kd = 2)। এখানে Kp = 3 আর Kd = 5 — দুটিই বড়, তাই comment-এর \"a bit more aggressively\" দাবিটি সংখ্যায় সমর্থিত। এই কড়া টিউনিং কেন দরকার, তার পরিমাপযোগ্য ফল নিচের math-অংশে: deadzone 12 ডিগ্রি বনাম tracker-এর 18 ডিগ্রি, আর turn ceiling ±0.9375 rad/s বনাম ±0.75 rad/s।"},{"a":48,"b":48,"text":"L48 <code>self.ang_pid = SinglePID(3.0, 0.0, 5.0)</code> — এই file-এর <b>একমাত্র</b> PID; linear PID-এর কোনো অস্তিত্বই এখানে নেই (tracker-এর lin_pid-এর মতো কিছু নেই), আর সে কারণেই পরে <code>linear.x</code> কখনো সেটই হয় না — robot সবসময় জায়গায় ঘুরে (L123-এর comment নিজেই স্বীকার করে)। <code>SinglePID</code> class-টি L13-এর star-import থেকে এসেছে; vendor module-টি এই folder-এ নেই, তাই তিনটি positional argument-কে (Kp, Ki, Kd) ধরা হচ্ছে inferred হিসেবে। এই object-এর একটিই কাজজায়গা: L103-এ <code>pid_compute(abs(minDistID) / 72, 0)</code>।"}],"math":{"intro":"constructor-এর এই এক লাইনে তিনটি সংখ্যা (3.0, 0.0, 5.0) ঠিক করে দেয় robot-এর প্রতিটি মোড় কেমন হবে। এই Part-এর গণিত সেটাই খোলে: generic PID law-টি কী, Ki = 0 কোন শক্তিটি কেটে দেয়, বড় Kd = 5 ঠিক কখন জ্বলে ওঠে, আর guard কেন tracker-এর চেয়ে কড়া gain নিয়েছে।","levels":[{"label":"Level 1 — Symbols ও একক","latex":"\\[ u(t),\\quad e(t),\\quad K_p = 3.0,\\quad K_i = 0.0,\\quad K_d = 5.0 \\]","text":"u হলো controller-এর আউটপুট, e হলো error — কতটা ভুল দিকে তাকিয়ে আছি। এই file-এ e আসে dimensionless আকারে: L103-এ <code>abs(minDistID) / 72</code>, মানে degree-সংখ্যাকে 72 দিয়ে ভাগ। 72 কেন 72 — file কোথাও ব্যাখ্যা করে না, bare magic number। u পরে <code>angular.z</code>-এর স্কেলে যায় (rad/s, তার আগে L118-এর ×0.5 damping পেরিয়ে)।"},{"label":"Level 2 — Generic PID law","latex":"\\[ u(t) = K_p\\,e(t) + K_i \\int_0^t e(\\tau)\\,\\mathrm{d}\\tau + K_d\\,\\frac{\\mathrm{d}e(t)}{\\mathrm{d}t} \\]","text":"তিনটি term তিন দিকে তাকায়: P দেখে বর্তমান error, I জমায় রাখে অতীতের পুরো ভাগ, D আঁচ করে error এখন কোন দিকে যাচ্ছে। SinglePID-এর ভেতরের implementation অজানা (vendor module এই folder-এ নেই, inferred), কিন্তু constructor-এর তিনটি gain এই law-এর তিন সহগ হিসেবেই বসে — সেটাই সব downstream আচরণের ভিত্তি।"},{"label":"Level 3 — Ki = 0 কী কেটে দেয়","latex":"\\[ K_i = 0 \\;\\Longrightarrow\\; u(t) = K_p\\,e(t) + K_d\\,\\frac{\\mathrm{d}e}{\\mathrm{d}t} \\]","text":"integral term পুরোপুরি অনুপস্থিত — controller-এর কোনো স্মৃতি নেই, প্রতিটি scan নিজের হিসাব নিজেই করে। লাভ: windup হয় না — object দীর্ঘক্ষণ এক পাশে আটকে থাকলেও জমা হওয়া error হঠাৎ বিস্ফোরিত হয়ে চাকায় ধাক্কা দেয় না। মূল্য: ছোট কিন্তু স্থায়ী error কেউ জমিয়ে তুলে শুধরে দেয় না। guard-এর কাজ অবশ্য অপেক্ষা নয় — প্রতিটি scan-এ হুমকির দিকে ঘুরে তাকানো; সেখানে PD-ই যথেষ্ট।"},{"label":"Level 4 — Discrete scan আর বড় Kd","latex":"\\[ u_k \\;=\\; 3\\,e_k \\;+\\; 5\\,\\frac{e_k - e_{k-1}}{\\Delta t} \\]","text":"<code>pid_compute</code> প্রতি scan-এ একবার ডাকা হয়, তাই derivative-কে পার্থক্য-কে-সময়-দিয়ে-ভাগ দিয়ে approximate করতে হয় (illustrative)। দৃশ্য বদলালে — নতুন object প্রথম scan-এ cone-এ ঢুকলে — e এক ধাপে লাফিয়ে ওঠে, আর ঠিক সেই step change-এই Kd = 5 term-টি একটি same-sign transient যোগ করে। Kp-এর তুলনায় Kd বড় হওয়ায় প্রথম call-এর এই ধাক্কাটি চোখে পড়ে; পরের scan-গুলোতে e শান্ত হলে হিসাব আবার নিচের Kp-view-এ ফেরে।"},{"label":"Level 5 — Kp-view বন্ধ রূপ","latex":"\\[ u = 3\\cdot\\frac{|a|}{72} = \\frac{|a|}{24},\\qquad |u| < 0.5 \\;\\Longleftrightarrow\\; |a| < 12^{\\circ} \\]","text":"transient কেটে যাওয়ার পর steady হিসাব pure proportional: e = |a|/72 ঢুকলে u = |a|/24 (illustrative)। L115-এর deadzone <code>abs(ang_pid_compute) &lt; 0.5</code> তাই |a| < 12 ডিগ্রিতে রূপ নেয়। ঠিক সীমানায় |a| = 12 হলে u = 0.5 — strict <code>&lt;</code> মিথ্যা হওয়ায় beam-টি পাস করে যায়, ×0.5 damping-এর পর z = ±0.25 rad/s। আর cone-এর কিনারা ছুঁতে ছুঁতে (|a| যখন 45-এর নিচ দিকে) u পৌঁছায় 1.875-এ, z পৌঁছায় ±0.9375 rad/s-এ — এটাই guard-এর turn ceiling; exactly 45.0-র beam L68-এর strict শর্তে বাদই পড়ে।"},{"label":"Level 6 — Guard বনাম tracker: কড়া টিউনিংয়ের ফল","latex":"\\[ K_p:\\ \\frac{3}{2} \\;\\Longrightarrow\\; \\text{deadzone } \\frac{12^{\\circ}}{18^{\\circ}},\\qquad \\text{ceiling } \\frac{\\pm 0.9375}{\\pm 0.75}\\ \\frac{\\mathrm{rad}}{\\mathrm{s}} \\]","text":"tracker (folder 12) নিয়েছিল Kp = 2 আর damping ×0.6; guard নিয়েছে Kp = 3 আর damping ×0.5। ফল দুই মাথায়: deadzone 18 ডিগ্রি থেকে সঙ্কুচিত হয়ে 12 ডিগ্রি — guard আরও ছোট বাঁকে সাড়া দেয়; ceiling 0.75 থেকে উঠে 0.9375 rad/s — জরুরি মুহূর্তে আরও দ্রুত ঘোরে। tracker-এর কাজ ছিল শান্তভাবে লক্ষ্য অনুসরণ করা; guard-এর কাজ হুমকির দিকে সঙ্গে সঙ্গে ঘুরে তাকানো আর প্রয়োজনে বাজনার সাথে নজর রাখা — L47-এর \"aggressively\" শব্দটির সত্যতা এই দুটি সংখ্যাতেই খুঁজে পাওয়া যায়।"}],"numeric":[{"latex":"\\[ e = \\frac{14}{72} = 0.194,\\qquad u = 3 \\times 0.194 = 0.583,\\qquad z = 0.5 \\times 0.583 = +0.292\\ \\frac{\\mathrm{rad}}{\\mathrm{s}} \\]","text":"illustrative Wave A (pillar 0.90 m, +14 ডিগ্রি, বাঁদিকে): L48-এর gain-গুলো প্রথম কাজে নামলে এই সংখ্যাগুলো আসে। u = 0.583 deadzone পাস করে (0.5-এর উপরে), ×0.5 damping-এর পর চাকার কাছে যায় +0.292 rad/s — robot স্থির জায়গায় বাঁদিকে ধীরে ঘোরে। দৃশ্য বদলের প্রথম call-এ Kd- transient একই দিকে একটু ঠেলে দিতে পারে (illustrative)।"},{"latex":"\\[ e = \\frac{8}{72} = 0.111,\\qquad u = 3 \\times 0.111 = 0.333,\\qquad 0.333 < 0.5 \\;\\Rightarrow\\; z = 0.0 \\]","text":"illustrative Wave F (0.80 m @ +8 ডিগ্রি, পরিষ্কার সামনে): একই PID, কিন্তু error ছোট হওয়ায় Kp = 3-ও u-কে 0.5-এর ঘরে তুলতে পারে না — deadzone গিলে দেয়, z = 0.0। robot ঘুরবে না; object 0.55 m-এর বাইরে বলে beep-ও বাজবে না — সব ঠিক থাকার নীরব ছবি।"},{"latex":"\\[ u_{\\max} = 3 \\times \\frac{45}{72} = 1.875,\\qquad z_{\\max} = \\pm\\,0.9375\\ \\frac{\\mathrm{rad}}{\\mathrm{s}} \\]","text":"illustrative ceiling: cone-এর সীমানার কাছে |a| 45-এর নিচ দিকে গেলে (exactly 45.0-র beam strict <code>&lt;</code> শর্তে বাদ)। একই জায়গায় tracker-এর ছাদ ছিল 2 × (45/72) × 0.6 = 0.75 rad/s — guard-এর ঘোরা প্রায় 25% দ্রুত, L47-এর কড়া টিউনিংয়ের সরাসরি মাপ।"}],"mapping":[{"code":"self.ang_pid = SinglePID(3.0, 0.0, 5.0)","math":"\\( K_p = 3.0,\\; K_i = 0.0,\\; K_d = 5.0 \\)","text":"তিনটি positional argument-ই generic PID law-এর তিন সহগ। ক্রমটি (Kp, Ki, Kd) — inferred: SinglePID-এর vendor module এই folder-এ নেই, ভেতরটা দেখা যাচ্ছে না; তাই এই ক্রম নিয়ে সতর্ক থাকতে হয়।"},{"code":"ang_pid_compute = self.ang_pid.pid_compute(abs(minDistID) / 72, 0)","math":"\\( u = 3\\,e + 5\\,\\dot{e},\\qquad e = |a|/72 \\)","text":"এই object-টির একমাত্র call — L103-এ, error হিসেবে degree-কে 72 দিয়ে ভাগ করা dimensionless মান, দ্বিতীয় argument target শূন্য। L48-এ বসানো gain-গুলো ঠিক এই এক লাইন দিয়েই চাকার কাছে পৌঁছায়; এর পরে sign branch (L106-110), deadzone (L115), damping (L118) — সব এই u-এর উপরে দাঁড়িয়ে।"}],"failure":["Joy_active-এর default True করে দিলে জন্মের প্রথম scan থেকেই L81-82 চলে যেত: প্রতিটি scan-এ zero Twist — চাকা সারাজীবন brake-এ, obstacle যত কাছেই আসুক কোনো মোড় নেই, beep-ও নেই (L83-এর return alarm-এর আগেই), আর print trio-ও আসে না বলে console নীরব — দেখতে মনে হয় node মরে গেছে।","tracker-এর নরম gain (2.0, 0.0, 2.0) এখানে বসালে deadzone-এর ধার 18 ডিগ্রিতে সরে যেত: illustrative Wave A-র +14 ডিগ্রির obstacle-এর জন্য u = 2 × (14/72) = 0.389, যা 0.5-এর নিচে — z = 0.0, অর্থাৎ বাধা মাত্র 14 ডিগ্রি পাশে থাকলেও guard চুপচাপ বসে থাকত।","Ki &gt; 0 রাখলে object দীর্ঘক্ষণ এক পাশে আটকে থাকা মাত্র integral term error জমিয়ে রাখত, তারপর হঠাৎ overshoot — steering wheel না থাকায় পুরো chassis এক পাশ থেকে আরেক পাশে দুলতে থাকত, আর প্রতি scan-এ জমা চলতে থাকায় দোলন সহজে থামত না। Ki = 0 রাখাই windup-মুক্ত রাখার উপায়।","Kd = 5-এর step-transient: নতুন object প্রথম scan-এ cone-এ ঢুকলে e শূন্য থেকে লাফিয়ে ওঠে, derivative-এর ধাক্কায় প্রথম z হঠাৎ বড় হয় — chassis এক ঝাঁকুনি খায়; পরের scan-গুলোতে e শান্ত হয়ে Kp-view ফিরে আসলেও প্রথম সেই ধাক্কাটি এড়ানো যায় না।","constructor-এর argument-ক্রম সম্পর্কে ধারণাটাই যদি ভুল হয় — vendor যদি আসলে (Kp, Kd, Ki) নেয় — তাহলে বাস্তবে Kd = 0 আর Ki = 5: deadzone, ceiling, transient সব downstream সংখ্যা এক লাথিতে বদলে যেত। module এই folder-এ নেই বলে ক্রমটি inferred — এই label-টাই সাবধানতার জায়গা।"]},"robot":{"correct":"constructor-এর এই শেষ block-টি চালানোর পর node-টি সম্পূর্ণ armed: Joy_active = False থাকায় প্রথম <code>/scan</code> message থেকেই AI-এর steering চালু — joystick থেকে /JoyState True না আসা পর্যন্ত L81-এর gate-এ ঢোকার প্রশ্নই ওঠে না। ang_pid-টি gain (3.0, 0.0, 5.0) নিয়ে জন্মায় আর প্রতিটি scan-এ L103-এ ডাকা হয়: illustrative Wave A-তে (0.90 m @ +14 ডিগ্রি) এটি u = 0.583 বের করে, ×0.5 damping-এর পর +0.292 rad/s — দুই চাকা বিপরীত গতিতে ঘুরে robot স্থির জায়গায় বাঁদিকে মোড়ে, সামনে যায় না (linear PID নেই, linear.x কখনো সেট হয় না)। নিজে এই Part-টি কোনো চাকা নাড়ায় না, console-এও কিছু ছাপে না — এটি শুধু state flag আর controller তৈরি করে রাখে; পরের Part-গুলোর callback সেগুলো খরচ করে।","incorrect":"Joy_active-এর default True হলে robot জন্মের মুহূর্ত থেকে প্রতিটি scan-এ zero Twist খেত — চাকা সদা-brake, obstacle যত কাছেই আসুক মোড় নেই, buzzer-ও শব্দ করে না। tracker-এর নরম gain (2.0, 0.0, 2.0) রাখলে 14 ডিগ্রি পাশের obstacle-ই deadzone-এ বাদ পড়ে (u = 0.389, 0.5-এর নিচে) — guard হিসেবে নিরীহ হয়ে বসে থাকে। আর বড় Kd = 5-এর দরুন নতুন object প্রথম দেখা দেওয়া scan-টিতে derivative-এর ধাক্কা z-কে হঠাৎ ফুলিয়ে দেয় — chassis এক ঝাঁকুনি খায়, পরের scan-গুলোতে ঘোরা আবার স্থির হয়।"},"animType":null},{"n":9,"id":"part-09","fname":"laser_Warning.py","enTitle":"JoyStateCallback — Human Override","lang":"python","start":49,"end":53,"flags":[],"explain":[{"a":49,"b":50,"text":"L49 একটা blank line — আগের Part-এর <code>__init__</code>-এর শেষ (L48-এ <code>SinglePID</code> তৈরি) আর এই প্রথম callback-এর মাঝে বিভাজক মাত্র। L50: <code>def JoyStateCallback(self, msg):</code> — L26-এ <code>create_subscription(Bool,'/JoyState', self.JoyStateCallback,1)</code> ঠিক এই নামটাই register করেছিল, তাই <code>/JoyState</code> topic-তে নতুন message পৌঁছালেই executor এই function-টিকে ডাকে (queue depth 1 — জমে থাকা পুরনো message বাদ পড়ে)। Input হলো message object <code>msg</code>; callback-টি নিজে কিছুই publish করে না, শুধু একটা অবস্থা flag আপডেট করে।"},{"a":51,"b":51,"text":"<code>if not isinstance(msg, Bool): return</code> — type-guard। এই <code>Bool</code>-টি std_msgs-এরটা নয়; L13-এর star-import <code>from yahboom_M3Pro_laser.common import *</code> থেকে আসা vendor-এর custom message, আর সেই module-টি এই folder-এ নেই বলে ভেতরের গঠন আমাদের জানা নেই (label inferred)। কোনোভাবে অন্য type-এর object ঢুকে পড়লে callback তৎক্ষণাৎ ফিরে যায় — <code>Joy_active</code>-এর আগের মান (L45-এ বসানো <code>False</code>) অপরিবর্তিত থাকে। registerScan-এর শুরুতেও একই defensive pattern আছে: L55 <code>if not isinstance(scan_data, LaserScan): return</code>।"},{"a":52,"b":52,"text":"<code>self.Joy_active = msg.data</code> — message-এর boolean মানটি instance attribute-এ জমা হলো। Source-এর নিজের কমেন্ট বলছে: <code># If True, human is driving, AI should pause</code>। অর্থাৎ <code>True</code> মানে মানুষ joystick ধরেছে — এখন human চালাবে, AI pause; <code>False</code> এলে আবার AI-এর হাতে নিয়ন্ত্রণ। এটি trigger হয় যখন human remote-এ নিয়ন্ত্রণ নেওয়ার মুহূর্তে joystick পাশের node <code>/JoyState</code>-এ মানটি পাঠায়। খেয়াল রাখুন — এই লাইনটি robot-এর wheel বা buzzer-এ সরাসরি কিছুই করে না; এটি শুধু switch-টা ঘোরায়, switch-এর ফল পরে registerScan-এর ভেতরে দেখা যায়।"},{"a":53,"b":53,"text":"L53-এর blank line এই callback-কে পরের function থেকে আলাদা করে রাখে — পরের L54 থেকেই <code>registerScan</code>, অর্থাৎ এই flag-এর আসল consumer। গুরুত্বপূর্ণ forward-reference: gate-টি registerScan-এর খুব গভীরে, L81 <code>if self.Joy_active :</code> — অর্থাৎ পুরো cone scan-টা (L63-70-এর beam loop, L76 <code>minDist</code>, L78 <code>minDistID</code>) আগে সম্পূর্ণ হয়, তারপর Joy check আসে। <code>True</code> থাকলে L82 প্রতি scan-এ all-zero <code>Twist()</code> publish করে (active brake) এবং L83-এ <code>return</code>। এই return alarm block-টিকেও skip করে, তাই human চালানোর সময় <code>/beep</code> refresh হয় না — buzzer তার শেষ value-তে latch করে থাকে; L85-এর <code>print(\"minDist: \", minDist)</code>-ও console-এ আর ছাপা হয় না। <code>False</code> ফিরে এলে পরের scan থেকেই tracking আবার চালু। Folder 12-এর tracker-এও একই gate semantics ছিল, কিন্তু ওখানে return শুধু <code>/cmd_vel</code> freeze করত — এই guard-এ <code>/beep</code> channel যোগ হওয়ায় Joy-চলাকালীন সেটিও latch হয়ে যায়।"}],"math":null,"robot":{"correct":"নিয়মমতো চললে: human joystick ধরলে তার পাশের node <code>/JoyState</code>-এ <code>True</code> পাঠায়, এই callback সেটি <code>Joy_active</code>-এ জমায়, আর তখন থেকে প্রতিটি <code>/scan</code>-এ registerScan L82-তে all-zero <code>Twist()</code> পাঠিয়ে wheel দুটোকে থামিয়ে রাখে — lidar ঘুরতেই থাকে আর <code>/scan</code> আসতেই থাকে, কিন্তু AI-এর কোনো spin command আর <code>/cmd_vel</code>-এ যায় না, console-এ <code>minDist</code> print-ও চুপ। Human ছেড়ে দিলে <code>False</code> আসে, পরের scan থেকেই PID-নিয়ন্ত্রিত ঘূর্ণন আবার শুরু হয়।","incorrect":"ধরুন vendor-এর custom <code>Bool</code>-এর জায়গায় ভুল type মিলে গেল — isinstance-guard সব message ফিরিয়ে দেবে, <code>Joy_active</code> চিরকাল <code>False</code> থাকবে: human joystick ধরলেও AI pause হবে না, registerScan প্রতি scan-এ নিজের spin command <code>/cmd_vel</code>-এ পাঠাবে আর human-এর teleop command-ও একই topic-এ বসবে — দুই publisher-এর টানাটানিতে wheel ছটফট করবে, obstacle-এর কাছে গেলে alarm block-ও (তখন skip হয় না) buzzer বাজিয়ে যাবে। উল্টো দিকে <code>msg.data</code> কোথাও আটকে <code>False</code> আর ফিরলে না, তাহলে human হাত ছেড়ে দেওয়ার পরেও robot প্রতি scan-এ zero Twist পাঠিয়ে জমে বসে থাকবে — buzzer শেষ value-তে latch করা অবস্থায়।"},"animType":null},{"n":10,"id":"part-10","fname":"laser_Warning.py","enTitle":"registerScan — Beam Loop & Front Cone","lang":"python","start":54,"end":70,"flags":[],"explain":[{"a":54,"b":55,"text":"L54: <code>def registerScan(self, scan_data):</code> — এই node-এর মূল workhorse। L24-এর <code>create_subscription(LaserScan,\"/scan\",self.registerScan,1)</code> ঠিক এই নামটাই register করেছিল, তাই fused lidar থেকে প্রতিটা scan message (<code>/scan</code>, queue depth 1) এলেই executor এটিকে ডাকে। Input <code>scan_data</code> শুধু distance বহন করে না — নিজের header-এ <code>angle_min</code> আর <code>angle_increment</code>-ও আনে, L65-এ সেগুলোই লাগবে। L55: <code>if not isinstance(scan_data, LaserScan): return</code> — type-guard, L51-এর JoyStateCallback-এর মতোই defensive pattern। ভুল type এলে function নীরবে ফিরে যায়: কোনো list তৈরি হয় না, কিছুই publish হয় না — wheel তার শেষ <code>/cmd_vel</code> command মতোই চলতে থাকে, আর buzzer-এ এই node আর কিছু লেখে না।"},{"a":56,"b":58,"text":"L56: <code>ranges = np.array(scan_data.ranges)</code> — message-এর distance sequence-টাকে numpy array-তে তোলা হচ্ছে; নিজের কমেন্ট <code># Array of distances from the LiDAR</code>। index <code>i</code> মানে i-তম beam, <code>ranges[i]</code> মানে সেই দিকে প্রথম যেটায় লেগেছে তার দূরত্ব, meter-এ। Folder 10-এর merger+filter চেইন থেকে আসা fused রিং-এ এটা 360-ঘরের array (illustrative)। L57 blank। L58-এর কমেন্ট: <code># We will search for the absolute closest object in the front 90-degree cone</code> — সাবধান, এই \"90-degree\" কথাটা author-এর wording; সত্যি সীমা L68-এর inequality। <code>&lt;</code> strict থাকায় ঠিক ±45 ডিগ্রির beam দুটি বাদ পড়ে, ঢোকে -44 থেকে +44 ডিগ্রি (illustrative) — মোট ৯০-এর চেয়ে সামান্য কম; মন্তব্য উদ্দেশ্য বোঝায়, সীমা গণিতই ঠিক করে।"},{"a":59,"b":60,"text":"দুটো খালি list: <code>minDistList = []</code> (দূরত্বের জন্য, কমেন্ট <code># A list to hold all the close distances</code>) আর <code>minDistIDList = []</code> (কোণের জন্য, <code># A list to hold the angles of those close distances</code>)। কৌশলটা collect-first, decide-later: লুপ সামনের cone-এর প্রতিটা বৈধ beam-এর দূরত্ব প্রথম list-এ আর তার কোণটা দ্বিতীয় list-এ জমাবে — দুটো parallel list, একই iteration-এ পাশাপাশি append হয় বলে সাধারণ index-টাই দূরত্ব-কোণ জোড়ার সেতু। কোণগুলো degree unit-এ জমা হবে, কারণ L65-ই সেগুলোকে <code>* RAD2DEG</code> করে রাখে। আসল সিদ্ধান্ত পরে: L76 <code>min(minDistList)</code> আর L78 <code>minDistIDList[minDistList.index(minDist)]</code> এই ভাণ্ডার থেকেই nearest object-এর দূরত্ব আর দিক বের করবে।"},{"a":61,"b":63,"text":"L61 blank। L62-এর কমেন্ট <code># Loop through every single laser beam</code>, আর L63: <code>for i in range(len(ranges)):</code> — লুপটা শুধু সামনের beam নয়, রিং-এর প্রতিটা beam-ই ঘোরে (fused রিং-এ i = 0 থেকে 359, illustrative)। সামনে-না-পেছনের বাছাই লুপের ভেতরের শর্তে (L68) — অর্থাৎ প্রতিটা beam-এর কোণ আগে হিসাব হয়, তারপর সেটা cone-এ পড়লে কেবল তখনই list-এ জমা হয়। ৩৬০টার মধ্যে (illustrative হিসাবে) মাত্র ৮৯টা ঢুকবে — বাকিগুলো শুধু হিসাব হয়ে বাদ; এই ছাঁকুনিই এই Part-এর মূল গণিত।"},{"a":64,"b":65,"text":"L64-এর কমেন্ট বলছে এই beam-টা কোন দিকে তাক করছে সেটা বের করতে হবে; L65: <code>angle = (scan_data.angle_min + scan_data.angle_increment * i) * RAD2DEG</code>। অর্থ: প্রথম beam-এর কোণ <code>angle_min</code>-এর সাথে i-বার per-beam ধাপ <code>angle_increment</code> যোগ, তারপর L16-এর <code>RAD2DEG = 180 / math.pi</code> (প্রায় 57.29578 degree/radian) দিয়ে গুণ করে degree-এ নামানো। গুরুত্বপূর্ণ: কোণটা কোনো hardcoded টেবিল থেকে নয়, message-এর নিজের header field থেকে — driver চেইন যা পাঠাবে, গণিত তাই অনুসরণ করবে। Folder 10-এর fused রিংয়ের illustrative মানে (angle_min = -3.14159, increment = 0.0174533) সূত্রটা সরল হয়ে দাঁড়ায়: প্রতি beam প্রায় ঠিক ১ ডিগ্রি এগোয়, <code>angle</code> হয় -180 + i ডিগ্রি — i=0 পেছনে, i=180 ঠিক সামনে।"},{"a":66,"b":68,"text":"L66 blank; L67-এর কমেন্ট: <code># FRONT ZONE: If the beam is pointing forward (within +/- 45 degrees) and hits something valid</code>। L68-এ আসল শর্ত: <code>if abs(angle) &lt; self.LaserAngle and ranges[i] !=0.0 : </code> — দুটো clause। প্রথমটা cone-membership: <code>abs(angle)</code> নিলে বাঁ-ডান দুই দিক একসাথে ধরা পড়ে, আর <code>&lt;</code> strict বলে ঠিক ±45.0-এ বসে থাকা beam দুটি বাদ — <code>self.LaserAngle</code> L40-এ declare করা parameter, মান 45.0। দ্বিতীয়টা validity-check: vendor firmware no-return reading-কে 0.0 করে পাঠায়, সেগুলো এভাবে ছাঁকো হয়। কিন্তু সতর্ক প্রান্ত — <code>inf !=0.0</code> সত্য, তাই কোনো beam <code>inf</code> হয়ে এলে সেটি শর্ত পাস করে list-এ ঢুকে যায়; ভুল বিপদ-সংকেত তখনও হয় না, কারণ পরে L89-এ <code>minDist &lt;= self.ResponseDist</code> তুলনায় inf মিথ্যা হয়ে যায়। Source-fidelity-র ছোট দাগ: <code>!=0.0</code>-এর ভেতরে কোনো space নেই, কিন্তু লাইনের শেষে colon-এর আগে একটা space আছে।"},{"a":69,"b":70,"text":"শর্ত সত্য হলে দুটো append: <code>minDistList.append(ranges[i])</code> (দূরত্ব, কমেন্ট <code># Save the distance</code>) আর <code>minDistIDList.append(angle)</code> (সেই beam-এর কোণ, <code># Save the angle</code>)। দুটো একই iteration-এ, পাশাপাশি বসে — তাই list দুটোর k-তম ঘর সবসময় একই beam-এর দূরত্ব-কোণ জোড়া। লুপ শেষে ফল: সামনের cone-এর সব বৈধ প্রার্থীর সেট — wave A-এর pillar-এর মতো ক্ষেত্রে (0.90, +14.0) জোড়াটা এখানেই জমে থাকবে। এই Part-এর সীমায় আর কিছু ঘটে না — কোনো publish নেই, buzzer-write নেই, print নেই; আউটপুট হলো পরের ধাপের (L73-এর empty-check, L76-L78-এর min/argmin) কাঁচা উপাদান।"}],"math":{"intro":"এই Part-এর গণিত দুটো প্রশ্নের উত্তর দেয়: i-তম beam ঠিক কোন দিকে তাক করে আছে, আর সামনের cone-এর ভেতরে গণ্য হওয়ার — অর্থাৎ list-এ ঢোকার — শর্তটা কী।","levels":[{"label":"Level 1 — Symbols ও units","latex":"\\[ \\theta_{\\min},\\ \\Delta\\theta\\ [\\mathrm{rad}],\\qquad i,\\qquad C=\\frac{180}{\\pi}\\approx 57.29578\\ \\tfrac{\\mathrm{deg}}{\\mathrm{rad}},\\qquad r_i\\ [\\mathrm{m}] \\]","text":"<code>scan_data.angle_min</code> = θ_min (প্রথম beam-এর কোণ), <code>angle_increment</code> = Δθ (প্রতি beam-ধাপ, radian-এ), i = beam index (0 থেকে শুরু), C = L16-এর RAD2DEG = 180/π প্রায় 57.29578 degree/radian, আর r_i = <code>ranges[i]</code>, meter-এ। Sign convention: ধনাত্মক কোণ মানে obstacle বাঁ দিকে — wave A-এর pillar-এর +14 ডিগ্রি তাই বাঁয়ে। Cone-এর সীমা <code>self.LaserAngle</code> = 45.0 degree (L40-এর parameter)।"},{"label":"Level 2 — Beam-এর দিক: linear রূপান্তর","latex":"\\[ \\theta_i = \\left(\\theta_{\\min} + \\Delta\\theta \\cdot i\\right)\\cdot C \\]","text":"L65-এর হুবহু বীজগণিত রূপ: শুরুর কোণে i ধাপ যোগ (প্রতি ধাপ Δθ), তারপর C দিয়ে গুণ করে degree-এ নামানো। এটা একটা arithmetic progression — i এক বাড়লে কোণ ঠিক Δθ·C বাড়ে, তাই beam-গুলোর দিক সমান ব্যবধানে সাজে; কোনো beam-এর দিক আলাদা করে মনে রাখতে হয় না, index থেকেই বের হয়।"},{"label":"Level 3 — Fused রিং-এ সরল রূপ","latex":"\\[ \\theta_i = \\left(-\\pi + \\frac{\\pi}{180}\\,i\\right)\\cdot\\frac{180}{\\pi} = -180^{\\circ} + i \\]","text":"Folder 10-এর fused রিং-এর illustrative মান বসালে (angle_min = -3.14159, increment = 0.0174533, 360 beam) π-গুলো কেটে যায়: θ_i = -180 + i degree। অর্থাৎ i=0 ঠিক পেছনে, i=180 ঠিক সামনে, প্রতি ধাপে ১ ডিগ্রি — index-ই কোণ হয়ে দাঁড়ায়, ফলে পরের লেভেলের cone-হিসাব পূর্ণসংখ্যায় মেলে।"},{"label":"Level 4 — Cone-membership: strict inequality","latex":"\\[ -45^{\\circ} < \\theta_i < 45^{\\circ},\\qquad 135 < i < 225,\\qquad i \\in \\{136,\\dots,224\\} \\]","text":"θ_i = -180 + i বসালে শর্তটা index-এর ভাষায় নামে: 135 < i < 225, মানে i = 136 থেকে 224 — মোট 89 beam। কঠোর < বলে সীমানার beam দুটি (i=135 মানে ঠিক -45.0°, i=225 মানে ঠিক +45.0°) বাদ; ঢোকে -44° থেকে +44°। L58-এর \"front 90-degree cone\" কমেন্ট উদ্দেশ্য বোঝায়, কিন্তু inequality-ই সত্য: সেটা open interval (-45, +45), আর beam-বিস্তার ৮৮ ডিগ্রি — ৯০-এর চেয়ে সামান্য কম।"},{"label":"Level 5 — Validity-predicate আর inf-প্রান্ত","latex":"\\[ |\\theta_i| < 45^{\\circ}\\ \\wedge\\ r_i \\ne 0 \\]","text":"দ্বিতীয় clause-টা দূরত্বের মান দেখে: vendor-এর no-return reading যারা 0.0 কোডে আসে তারা বাদ। কিন্তু r_i = inf হলে <code>inf !=0.0</code> সত্য — সেই beam-ও দুই list-এ ঢুকে পড়ে; এটাই এই ছাঁকনির honest edge case। বিপদ ছড়ায় না, কারণ পরে L89-এ inf মানে 0.55 তুলনায় মিথ্যা, আর তালিকায় সত্যিকার দূরত্ব থাকলে min() কখনো inf-কে বেছে নেয় না। এখানে guard-এর দৃষ্টিতে inf মানে \"বৈধ, অনেক দূরের কিছু\" — বাতিল নয়।"}],"numeric":[{"latex":"\\[ \\Delta\\theta \\cdot C = 0.0174533 \\times 57.29578 \\approx 1.000^{\\circ} \\]","text":"প্রতি ধাপে কোণ-অগ্রগতি: fused রিং-এর illustrative increment-কে RAD2DEG দিয়ে গুণ করলে প্রায় ঠিক ১ ডিগ্রি — এই জন্যই Level 3-এর -180 + i রূপটা খাঁটি পূর্ণসংখ্যায় দাঁড়ায় (illustrative)।"},{"latex":"\\[ \\theta_{194} = -180^{\\circ} + 194 = +14^{\\circ},\\qquad |{+14^{\\circ}}| < 45^{\\circ} \\]","text":"Wave A-এর pillar beam (illustrative): i = 194 হলে কোণ +14 ডিগ্রি — strict cone-এর ভেতরে, দূরত্ব 0.90 আর 0.0 নয়; তাই (0.90, +14.0) জোড়াটা দুই list-এ জমা হয়।"},{"latex":"\\[ 224 - 136 + 1 = 89,\\qquad \\theta_{\\text{first}} = -44^{\\circ},\\ \\theta_{\\text{last}} = +44^{\\circ} \\]","text":"Cone-এর দখল (illustrative): খোলা ব্যবধান 135 < i < 225-এ পূর্ণসংখ্যা ৮৯টা; কোণ-বিস্তার -44° থেকে +44°, span ৮৮° — \"90-degree\" কমেন্টের চেয়ে সামান্য কম, কারণ ঠিক ±45-এর beam দুটি strict inequality বাদ দেয়।"}],"mapping":[{"code":"scan_data.angle_min + scan_data.angle_increment * i","math":"\\( \\theta_i^{\\mathrm{rad}} = \\theta_{\\min} + \\Delta\\theta\\,i \\)","text":"index থেকে radian-কোণ — দুটোই message header-এর field; node নিজে কোনো কোণ-টেবিল জানে না, যা এলে তাই মানে।"},{"code":"* RAD2DEG","math":"\\( \\theta_i = C\\,\\theta_i^{\\mathrm{rad}},\\quad C = 180/\\pi \\approx 57.29578 \\)","text":"L16-এর module-level constant; প্রতিটা beam-এ একই গুণ, তাই list-এ জমা কোণ এবং পরে sign-branch/deadzone-এর সব হিসাব degree unit-এ থাকে।"},{"code":"abs(angle) < self.LaserAngle","math":"\\( |\\theta_i| < 45^{\\circ} \\)","text":"বাঁ-ডান দুই দিক এক ঝাড়ায়: abs নেওয়ার পর একটাই সীমা; strict inequality, আর 45.0 মানটা L40-এর LaserAngle parameter থেকে।"},{"code":"ranges[i] !=0.0","math":"\\( r_i \\ne 0 \\)","text":"validity-predicate: 0.0 বাদ, finite দূরত্ব ঢোকে, inf-ও ঢোকে (inf কে 0 থেকে আলাদা ধরা হয়)।"},{"code":"minDistList.append(ranges[i]) + minDistIDList.append(angle)","math":"\\( S = \\{(r_i,\\theta_i)\\ :\\ |\\theta_i| < 45^{\\circ},\\ r_i \\ne 0\\} \\)","text":"লুপ শেষে S-ই সামনের cone-এর বৈধ প্রার্থী-সেট; L76/L78 পরে এখান থেকে min আর argmin বের করবে।"}],"failure":["Message-এ আসল রিং-এর সাথে না মেলা <code>angle_increment</code> (যেমন merger-filter চেইন অন্য spacing দিলে) প্রতিটা θ_i-কে সরিয়ে দেয়: হিসাবের \"সামনে\" কাত হয়ে বসে, সত্যিকারের সামনের obstacle cone-এর বাইরে গণ্য হয় — robot পরে ভুল দিকে ঘুরতে থাকে, আর সামনের জিনিস 0.55 m zone-এ ঢোকার আগেই beam বাদ পড়ে থাকায় বাঁশি পর্যন্ত বাজে না।","কমেন্টের \"90-degree\" কথায় ভরসা করে <code>&lt;</code>-এর জায়গায় <code>&lt;=</code> বসালে (বা LaserAngle বদলে 90.0 করলে) সীমানার beam ঢুকে যায়: ৮৯-এর জায়গায় ৯১ beam — কোণ-প্রান্তের obstacle এখন \"সামনে\" গণ্য হয়ে steering আর alarm দুটোই তার প্রতিক্রিয়া দেখায়।","<code>ranges[i] !=0.0</code> clause-টা বাদ দিলে vendor-এর 0.0 no-return reading-রা list-এ ঢুকে পড়ে: <code>min(minDistList)</code> হয় 0.0, আর <code>minDistID</code> হয় সেই ফাঁকা beam-এর কোণ — L89-এর দ্বিতীয় শর্ত ভুল বিপদ-বাঁশি ঠেকালেও steering-এর input ভুয়া কোণ থেকে তৈরি হয়, robot এমন দিকে ঘুরতে থাকে যেখানে কিছুই নেই।"]},"robot":{"correct":"নিয়মমতো চললে: প্রতিটা <code>/scan</code> message-এ (depth 1) type-guard পাস করে 360-beam-এর fused রিং (illustrative) থেকে <code>ranges</code> array দাঁড়ায়, লুপ প্রতিটা beam-এর কোণ degree-এ হিসাব করে সামনের কঠোর ±45° cone-এর বৈধ beam-গুলো (illustrative হিসাবে ৮৯টা) দুটো list-এ জমা করে। এই ১৭টা লাইনে কোনো wheel-command বা buzzer-write নেই — lidar ঘুরতেই থাকে, motor শেষ <code>/cmd_vel</code> command মতোই চলতে থাকে, console এখনো চুপ (প্রথম print L85-এ)। ফল: পরের argmin-ধাপের জন্য প্রস্তুত দূরত্ব-কোণ জোড়ার ভাণ্ডার — যেমন wave A-তে (0.90, +14.0)।","incorrect":"ধরুন merger-filter চেইন message-এ আসল রিংয়ের চেয়ে ভিন্ন <code>angle_increment</code> দিল: হিসাব-করা প্রতিটা কোণ আসল দিক থেকে সরে যায়, \"সামনের\" cone আসলে কাত হয়ে বসে — robot প্রকৃত সামনের দেয়াল দেখতে পায় না, পাশের জিনিসকে সামনে ভেবে সেই দিকে ঘুরতে থাকে, আর সত্যিকারের obstacle cone-এ না ঢুকে বাঁশি পর্যন্ত বাজে না। উল্টো প্রান্তে, type-guard যদি সব message ফিরিয়ে দেয়, L55-তেই callback শেষ — list তৈরিই হয় না: wheel শেষ command মতো চলতেই থাকে, buzzer তার আগের অবস্থাতেই থেকে যায়, console-এ <code>minDist</code> লাইন আর আসে না।"},"animType":"beamSweep"},{"n":11,"id":"part-11","fname":"laser_Warning.py","enTitle":"Closest Beam, Empty Guard & Joy Gate","lang":"python","start":71,"end":85,"flags":[],"explain":[{"a":71,"b":73,"text":"Loop শেষে দুটি parallel list-এ cone-এর (L68-এর strict শর্ত পাস করা) সব valid beam জমা থাকে। L72-এর comment বলে <code># If nothing is in front of us, do nothing and wait</code>, আর L73 সেটাই কোডে করে: <code>if len(minDistList) == 0: return</code> — bare <code>return</code>, কোনো value ছাড়া। মানে খালি list-এ <code>min()</code> ডাকার আগেই callback থেমে যায়, আর এই পথে <b>কোনো</b> publish হয় না — <code>/cmd_vel</code>-এ নতুন কিছু না গেলে wheel গুলো শেষ command-ই মেনে চলে, আর <code>/beep</code>-এ কিছু না লেখালে buzzer-টি তার শেষ value-তে latch হয়ে থাকে। আগের scan-এ alarm যদি beep ON করে থাকে, তবে সামনে এখন কিছু না থাকা সত্ত্বেও buzzer বাজতেই থাকে — empty-guard-এর পাশেই এই buzzer-stays-on trap-টি লুকানো।"},{"a":75,"b":76,"text":"L76 <code>minDist = min(minDistList)</code> — cone-এর ভেতরের সব valid distance থেকে সংক্ষিপ্তটি বেছে আনে। এটিই পরের block-গুলোর ইনপুট: alarm-এর শর্ত <code>minDist &lt;= self.ResponseDist</code> (L89) থেকে steering chain পর্যন্ত সব এই একটি সংখ্যার উপরে দাঁড়ানো। L68-এর <code>!=0.0</code> শর্তের কারণে vendor-এর no-return 0.0 গুলো list-এ ঢোকেইনি; <code>inf</code> কিন্তু ঢোকে — finite কোনো beam থাকলে <code>min()</code> কখনো <code>inf</code> বাছে না, ছোট finite টিই জেতে; আর সব qualifying beam-ই <code>inf</code> হলে <code>minDist = inf</code> হয়, তখন L89-এ <code>inf &lt;= 0.55</code> False হয়ে else branch-ই beep OFF করে।"},{"a":77,"b":78,"text":"L78 <code>minDistID = minDistIDList[minDistList.index(minDist)]</code> — সবচেয়ে কাছের object-টি কোন angle-এ বসে আছে সেটি বের করে: <code>index()</code> আগে খুঁজে দেয় ছোট distance-টি list-এর কোন position-এ, তারপর parallel list minDistIDList থেকে ঠিক সেই position-এর degree সংখ্যাটি তোলা হয়। এটি আসলে হাতে-লেখা একটি argmin। Tie-এ (একই distance দুটি beam-এ) <code>index()</code> FIRST occurrence ফেরত দেয় — list-টি angle-এর ascending ক্রমে সাজানো (beam-এর ক্রম -44.0 থেকে +44.0 ডিগ্রি, illustrative), তাই জেতে tied দলের সবচেয়ে negative angle-ওয়ালা beam-টি, অর্থাৎ cone-এর একেবারে ডান-দিকের qualifying beam।"},{"a":80,"b":81,"text":"L80-এর comment <code># If a human is driving, stop the AI and do nothing</code> আর L81-এর শর্ত <code>if self.Joy_active :</code> (colon-এর আগের space-টি source-এই আছে)। <code>/JoyState</code> subscription (L26) থেকে JoyStateCallback (L50-52) এই flag-টি set করে — মানুষ joystick ধরলে True, ছেড়ে দিলে False; ডিফল্ট False (L45)। Flag True হলেই নিচের brake branch চলে, নাহলে কোড একে এড়িয়ে L85-এ চলে যায়।"},{"a":82,"b":83,"text":"L82 <code>self.pub_vel.publish(Twist())</code> — সব field default 0.0 এমন একটি zero Twist publish করে, তারপর L83 <code>return</code>। মানুষ joystick চেপে রাখা অবস্থায় <b>প্রতিটি</b> scan-এ এই zero-Twist বারবার বেরোয় — একবারের brake নয়, scan rate-এ active brake; ফলে wheel গুলো সক্রিয়ভাবে থেমে থাকে, পুরনো command-এর ভরসায় ভাসে না। আর <code>return</code>-টি নেমে যায় alarm block-এর (L89-95) <b>আগেই</b>, তাই Joy-এর নিচেও <code>/beep</code> refresh হয় না — buzzer শেষ state-এ latch করে থাকে, ঠিক empty-guard পথের মতোই।"},{"a":85,"b":85,"text":"L85 <code>print(\"minDist: \", minDist)</code> — প্রতি scan-এ console-এ সবচেয়ে কাছের distance ছাপা হয়; এটি এই script-এর চার-print-এর প্রথমটি (পরে L99-এ minDistID, L112 ও L120-এ angular.z)। খেয়াল করো: empty guard (L73) বা Joy branch (L83) যে পথেই return নেয়, সেই পথে এই print আসেই না — console হঠাৎ নীরব হয়ে গেলে বোঝা যায় এই দুই পথের কোনো একটিতে কোড ঢুকেছে।"}],"math":{"intro":"এই Part-এর গণিত দুটি প্রশ্নের উত্তর দেয় — cone-এর কোন beam-টি সবচেয়ে কাছে, আর tie থাকলে কোন angle-টি জেতে।","levels":[{"label":"Level 1 — min ও argmin-এর symbol","latex":"\\[ d_{min} = \\min_{i}\\, d_i\\ \\text{[m]}, \\qquad a_{min} = a_{j},\\; j = \\mathrm{index}(d_{min})\\ \\text{[deg]} \\]","text":"minDistList-এর i-তম entry d_i হলো i-তম qualifying beam-এর distance (মিটার), আর minDistIDList-এর a_i সেই beam-এর angle (ডিগ্রি)। Python-এ আলাদা argmin function নেই, তাই L78 দুই ধাপে কাজটি করে — <code>index()</code> দিয়ে position, তারপর parallel list থেকে সেই position-এর angle।"},{"label":"Level 2 — tie-এর first-occurrence নিয়ম","latex":"\\[ a_1 < a_2 < \\dots < a_n, \\qquad d_j = d_k,\\; j < k \\;\\Rightarrow\\; \\mathrm{index}(d_{min}) = j \\]","text":"list-টি angle-এর ascending ক্রমে সাজানো (beam order -44.0 থেকে +44.0 ডিগ্রি, illustrative), তাই সমান distance-এর ভাগ্যে প্রথম entry-ই জেতে — অর্থাৎ tied দলের মধ্যে সবচেয়ে negative angle, cone-এর একেবারে ডান-দিকের beam-টি। পরের Part-গুলোর sign branch এই sign-এর উপরেই ঘোরে।"}],"numeric":[{"latex":"\\[ d_{min} = \\min(0.55,\\, 0.50,\\, 0.50,\\, 0.62) = 0.50\\ \\mathrm{m}, \\qquad \\mathrm{index}(0.50) = 1 \\Rightarrow a_{min} = -6.0^{\\circ} \\]","text":"illustrative tie-উদাহরণ: minDistIDList = [-20.0, -6.0, +12.0, +30.0] আর minDistList = [0.55, 0.50, 0.50, 0.62] হলে 0-ভিত্তিক <code>index()</code> প্রথম 0.50-এর position 1 দেয়, ফলে minDistID = -6.0 — +12.0 নয়। এই angle-ই পরের Part-এ e = |a|/72 chain-কে চালাবে।"}],"mapping":[{"code":"minDist = min(minDistList)","math":"\\( d_{min} = \\min_i d_i \\)","text":"এই call-টি কোনো angle জানে না — শুধু ছোট distance ফেরত দেয়; angle পেতে হলে parallel list-এ আবার ফিরে যেতে হয়, যেটি পরের লাইনের কাজ।"},{"code":"minDistID = minDistIDList[minDistList.index(minDist)]","math":"\\( a_{min} = a_{\\arg\\min_i d_i} \\)","text":"argmin-এর হাতে-লেখা রূপ: <code>index()</code> position দেয়, সেই position-এর subscript দুটি parallel list-কে sync রাখে — L69-70 যেহেতু দুটিতে একসাথে append করে, দুই list-এর দৈর্ঘ্য সবসময় সমান, তাই lookup-টি কখনো ভুল জায়গায় পড়ে না।"}],"failure":["Tie-এ শেষ occurrence নেওয়া কোনো বদলে-লেখা রূপ হলে উপরের উদাহরণে minDistID = +12.0 আসত — sign branch (L106-110) তখন উল্টো দিক বেছে robot-কে tied object-এর ভুল পাশে spin করাত।","L73-এর empty guard না থাকলে খালি list-এ <code>min()</code> প্রতি scan-এ ValueError ছুড়ত — callback crash, console-এ traceback ভরে যেত, আর wheel সাথে buzzer দুটোই last state-এ আটকে থাকত; guard-টিই এই Part-কে crash-safe রাখে।"]},"robot":{"correct":"সামনে valid object থাকলে (illustrative Wave B: 0.70 m @ +20 deg) L76-78 ঠিক সেই beam-টি বেছে নেয় — প্রতিটি scan-এ console-এ <code>minDist: 0.7</code> লাইন আসে আর নিচের alarm-steering chain চালু থাকে। Cone খালি হয়ে গেলে (Wave E) L73-এ সব থেমে যায়: wheel গুলো শেষ /cmd_vel মেনেই চলতে থাকে, buzzer আগের state-এ latch করে থাকে — beep ON থাকলে সামনে কিছু নেই তবু বাজতেই থাকে। মানুষ joystick চেপে ধরলে প্রতি scan-এ zero Twist যাওয়ায় motor সক্রিয়ভাবে brake খায় — robot স্থির দাঁড়িয়ে থাকে, শুধু /beep refresh হয় না বলে latch হয়ে থাকে।","incorrect":"Guard-টা বাদ দিলে খালি cone-এর প্রতিটি scan-এ <code>min()</code> ValueError ছুড়ত — registerScan মরে যেত, console traceback-এ ভরে যেত, ঘুরন্ত robot আর থামত না (last /cmd_vel জমে থাকে) আর বেজে-ওয়া buzzer কখনো বন্ধ হতো না। Joy gate উঠে গেলে মানুষের হাতে চালানোর সময়ও AI-এর steering /cmd_vel-এ publish করত — joystick আর AI-এর command টানাটানি করে robot-কে ঝাঁকুনি খাওয়াত। Tie-এর first-occurrence নিয়ম ভেঙে দিলে minDistID-এর sign উল্টে যেত — robot সবচেয়ে কাছের object-এর উল্টো পাশে spin করত।"},"animType":null},{"n":12,"id":"part-12","fname":"laser_Warning.py","enTitle":"Alarm Logic — Danger Zone & Buzzer","lang":"python","start":86,"end":95,"flags":[],"explain":[{"a":87,"b":88,"text":"L87-এর banner <code># --- THE ALARM LOGIC ---</code> block-টির নাম দেয়, আর L88 কাজটা বলে: <code># If the closest object is inside the Danger Zone (0.55m)...</code> — Danger Zone মানে সামনের 0.55 মিটারের ব্যান্ড, যার সংখ্যাটি L41-42-এ <code>ResponseDist</code> parameter থেকে আসে। folder 12-এর laser_Tracker-এ এই block-টিই ছিল না — <code>/beep</code> channel নতুন, আর এই কয়েক লাইনই guard-কে tracker থেকে আলাদা করে এমন সিদ্ধান্ত-অংশ। নিচের tracking logic-এর (L97-এর পর) সাথে এর সম্পর্ক সম্পূর্ণ parallel: alarm শুধু distance দেখে, steering শুধু angle — একই <code>minDist</code>-এর দুই জন আলাদা ভোক্তা।"},{"a":89,"b":89,"text":"L89 <code>if minDist &lt;= self.ResponseDist and minDist != 0.0:</code> — দুটি clause একটি <code>and</code>-এ বাঁধা। প্রথমটিই মূল প্রশ্ন: সবচেয়ে কাছের object কি 0.55 m-এর ভেতরে বা ঠিক সীমানায়? <code>&lt;=</code> inclusive, তাই হুবহু 0.55 m-ও zone-এর ভেতরে গণ্য। দ্বিতীয় clause-টি belt-and-suspenders — L68-এর cone filter <code>ranges[i] !=0.0</code> ইতিমধ্যেই exact 0.0-কে list-এ ঢুকতে দেয়নি, তাই এখানে <code>minDist</code> আসলে কখনো 0.0 হতেই পারে না; clause-টি কেবল দ্বিতীয় প্রহরী। বিশেষ মানগুলো: <code>inf &lt;= 0.55</code> False, তাই সব-ইনফ cone নিচের else-এ গিয়ে buzzer চুপ করায়; আর NaN-এর সাথে কোনো comparison-ই সত্য হয় না — <code>minDist &lt;= self.ResponseDist</code> False হয়ে পুরো শর্ত False, ফলে NaN-ও else branch-এ পড়ে।"},{"a":90,"b":91,"text":"L90 <code>b = UInt16()</code> — খালি constructor-এ default <code>data = 0</code> সহ একটি message তৈরি হয়, তারপর L91 <code>b.data = 1               # 1 means BEEP!</code> সেই মানটিকে 1 করে (১-এর পরে comment-অবধি লম্বা space-run-টি source-এই আছে)। UInt16-এর একটিই field — <code>data</code>, unsigned 16-bit, সীমা 0 থেকে 65535; কিন্তু vendor convention এখানে মাত্র দুটি মান চেনে: 1 = beep ON, 0 = beep OFF — L6-এর comment বলেই এটি buzzer ON/OFF-এর message type। খেয়াল করো, ON-এর পথ দুই লাইনে লেখা — construct করা, তারপর assign করা; নিচের OFF-পথ দেখবে একই কাজ এক লাইনেই সেরে ফেলে।"},{"a":92,"b":92,"text":"L92 <code>self.pub_Buzzer.publish(b)</code> — তৈরি করা message-টি <code>/beep</code> topic-এ বেরোয়; publisher-টি L32-তে <code>create_publisher(UInt16,'/beep',1)</code> দিয়ে বানানো, queue depth 1। hardware-এর দিক থেকে এটি কোনো one-shot trigger নয় — একটি level command, যেটি object zone-এ থাকা অবধি প্রতিটি scan-এ বারবার যায়। illustrative Wave C-তে (0.48 m @ 0 deg) এই branch-ই চলে: console-এ <code>minDist: 0.48</code> লাইনের পরপরই buzzer বাজতে থাকে, আর একই scan-এর steering chain deadzone-এ গিয়ে <code>angular.z</code>-কে 0.0 রাখে — অর্থাৎ robot জায়গায় স্থির দাঁড়িয়ে বাজতে থাকে।"},{"a":93,"b":94,"text":"L93 <code>else:</code> — উপরের শর্ত মিথ্যা হলেই এই পথ: object zone-এর বাইরে, কিংবা মানটি <code>inf</code>/NaN-এর মতো তুলনায় টেকে না এমন কিছু — সবাই এখানেই নামে। L94-এর comment <code># If the object is outside the danger zone, turn the buzzer off (0).</code> পরের লাইনের কাজ আগেই ব্যাখ্যা করে দেয়: এখন buzzer বন্ধ করতে হবে, আর বন্ধের মান 0।"},{"a":95,"b":95,"text":"L95 <code>self.pub_Buzzer.publish(UInt16()) </code> — নতুন <code>UInt16()</code> inline বানিয়ে সরাসরি publish করা হলো (লাইনের শেষে একটি trailing space source-এ আছে); default constructor-এর <code>data</code> মান 0, তাই এটিই BEEP OFF। L90-91-এর দুই-লাইন কাজ এখানে এক লাইনে — কোনো variable লাগে না, কারণ 0-ই তো default। আসল তফাতটা অন্য জায়গায়: এই OFF মানটি object visible থাকা অবধি <b>প্রতিটি</b> scan-এ বারবার publish হয় — buzzer-এর signal level-ধর্মী, প্রতি scan-এ refresh হয়, edge event নয়। আর ঠিক এ কারণেই দুটি early return বিপজ্জনক: L73 (খালি cone) ও L81-83 (Joy) — দুটোই alarm block-এর আগেই ফিরে যায়, refresh বাদ পড়ে, আর <code>/beep</code> তার শেষ state-এ latch হয়ে থাকে — এটাই buzzer-stays-on trap; illustrative Wave E-তে D-এর beep ON ঠিক এভাবেই আটকে থাকে।"}],"math":{"intro":"এই Part-এর গণিত একটিই প্রশ্নের চারপাশে — এই scan-এ buzzer বাজবে কি না — আর উত্তরটি দাঁড়ায় দূরত্ব-অক্ষে একটি half-open ব্যান্ড, একটি inclusive সীমানা, আর hysteresis-এর সম্পূর্ণ অনুপস্থিতি মিলিয়ে।","levels":[{"label":"Level 1 — তিনটি symbol ও তাদের unit","latex":"\\[ d_{min}\\ \\text{[m]}, \\qquad R = \\mathit{ResponseDist} = 0.55\\ \\text{[m]}, \\qquad b \\in \\{0,\\, 1\\} \\]","text":"d_min হলো L76-এর <code>min(minDistList)</code>-এর ফল — এই scan-এ সামনের cone-এর সবচেয়ে কাছের valid দূরত্ব। R হলো L41-42-এ declare করা <code>ResponseDist</code> parameter, ডিফল্ট 0.55 মিটার — vendor-এর ভাষায় Danger Zone-এর সীমা। b হলো <code>/beep</code>-এ পাঠানো UInt16 message-এর <code>data</code> মান; type-টি 0 থেকে 65535 ধরলেও vendor convention মাত্র দুটি মান ব্যবহার করে — 1 = beep ON, 0 = beep OFF।"},{"label":"Level 2 — সিদ্ধান্ত-সমীকরণ (predicate)","latex":"\\[ b = \\begin{cases} 1, & (d_{min} \\le R) \\wedge (d_{min} \\ne 0) \\\\ 0, & \\text{otherwise} \\end{cases} \\]","text":"L89-এর দুই clause-এর AND-ই পুরো সমীকরণ। truth table ছোট: প্রথম clause False হলেই পুরো শর্ত False — Python-এর <code>and</code> short-circuit করে, দ্বিতীয়টি তখন আর মূল্যায়নই হয় না — আর else branch-এ যাওয়ার পথ তৈরি। দ্বিতীয় clause-টি ব্যবহারিকভাবে redundant (L68-এর cone filter আগেই exact 0.0 বাদ দিয়েছে), কিন্তু ভবিষ্যতে কেউ filter-টা বদলালে এটিই দ্বিতীয় প্রহরী হয়ে দাঁড়ায়।"},{"label":"Level 3 — দূরত্ব-অক্ষে half-open ব্যান্ড","latex":"\\[ \\mathcal{D}_{\\mathrm{ON}} = \\{\\, d \\in \\mathbb{R} : 0 < d \\le 0.55 \\,\\} = (0,\\ 0.55]\\ \\text{[m]} \\]","text":"সংখ্যা-রেখায় ON-অঞ্চল একটি half-open interval — দূরের প্রান্তে closed (<code>&lt;=</code> বলে ঠিক 0.55 অন্তর্ভুক্ত), কাছের প্রান্তে open (0 বাদ)। অর্থাৎ object ঠিক 0.55 m-এ দাঁড়ালেও beep হবে, কিন্তু মান 0 হলে হবে না — যে অবস্থাটি প্রয়োগে কখনো আসেই না, কারণ cone filter 0.0-কে আগেই ফেলে দিয়েছে। এই ব্যান্ডটাই animation-এর distance-axis-এ রঙিন zone হিসেবে দেখা যায়: 0-এর ঠিক পরে থেকে 0.55-সহ পর্যন্ত।"},{"label":"Level 4 — Hysteresis সম্পূর্ণ অনুপস্থিত","latex":"\\[ H = R_{\\mathrm{off}} - R_{\\mathrm{on}} = 0.55 - 0.55 = 0 \\]","text":"থার্মোস্ট্যাট-ধাঁচের alarm দুটি সীমা রাখে — কাছে গেলে ON (R_on), আরও দূরে গেলে OFF (R_off &gt; R_on); ফলে সীমানার গায়ে মান কাঁপলেও অবস্থা সহজে বদলায় না। এখানে ON আর OFF দুটোই একই 0.55 পড়ে — hysteresis-এর প্রস্থ H = 0। সুতরাং 0.55 m-এর গায়ে hover করা object-এর দূরত্ব lidar-এর noise-এ সামান্য দুললেই b প্রতি scan-এ উল্টে যেতে পারে — এটাই chatter।"},{"label":"Level 5 — Scan-দৃষ্টিতে level signal ও latch","latex":"\\[ b_k = \\begin{cases} 1, & 0 < d_k \\le 0.55 \\\\ 0, & \\text{else} \\end{cases} \\quad \\text{(each scan)}, \\qquad \\text{refresh skipped} \\Rightarrow b_k = b_{k-1} \\]","text":"k নম্বর scan-এ callback যদি L89 পর্যন্ত পৌঁছায়, buzzer-এর মান সেই scan-এর d_k থেকে নতুন করে হিসাব হয় — level signal, প্রতি scan-এ refresh। কিন্তু L73 (খালি cone) বা L81-83 (Joy) পথে callback আগেই ফিরলে refresh-ই হয় না; <code>/beep</code> topic-এ শেষ publish-কৃত মানটি পড়ে থাকে — b_k = b_{k-1}, অর্থাৎ latch। এই একটি সমীকরণই ব্যাখ্যা করে কেন সামনে কিছু না থাকা বা মানুষের joystick ধরার সময়ও বেজে-ওয়া buzzer চুপ হয়ে যায় না।"},{"label":"Level 6 — সীমানায় chatter-এর সম্ভাবনা","latex":"\\[ d_k = R + \\varepsilon_k, \\quad \\varepsilon_k\\ \\text{zero-mean noise} \\ \\Rightarrow\\ P(b_k = 1) = P(\\varepsilon_k \\le 0) = \\tfrac{1}{2} \\]","text":"object হুবহু সীমানায় (d = 0.55 m) থাকলে আর measurement noise ε শূন্য-কেন্দ্রিক হলে (illustrative ধরে নেওয়া) যেকোনো একটি scan-এ beep হওয়ার সম্ভাবনা অর্ধেক — scan-গুলোর একটি বড় অংশে 1, বাকিটায় 0। ফলে দীর্ঘ সময় ধরে buzzer scan rate-এ on-off করা একটা কাঁপা শব্দ ছাড়া আর কিছু না। hysteresis থাকলে (যেমন R_on = 0.55, R_off = 0.65) object-কে সত্যিই 0.65 m পেরোতে হতো OFF হতে — এই সম্ভাবনা-ঘড়ি তখন বন্ধ।"}],"numeric":[{"latex":"\\[ 0.48 \\le 0.55\\ (\\text{True}) \\ \\wedge\\ 0.48 \\ne 0.0\\ (\\text{True}) \\ \\Rightarrow\\ b = 1 \\]","text":"illustrative Wave C (0.48 m @ 0 deg): দুই clause-ই True, তাই if-branch — <code>b.data = 1</code>, buzzer বাজে। একই scan-এ steering chain-এ e = 0/72 = 0 হওয়ায় deadzone robot-কে স্থির রাখে: শরীর থেমে আছে, শব্দ চালু আছে।"},{"latex":"\\[ 0.55 \\le 0.55\\ (\\text{True}) \\ \\Rightarrow\\ b = 1 \\quad \\text{(closed boundary)} \\]","text":"boundary-numeric: <code>&lt;=</code> inclusive বলে ঠিক 0.55 m-এ বসে থাকা object-ও zone-এর ভেতরে গণ্য — buzzer বাজবে। vendor L41-এর comment যে সংখ্যাটিকে The \"Danger Zone\" distance (0.55 meters) বলে, L89-এর তুলনা সেই সংখ্যাটিকেই ON-অঞ্চলের ভেতরে রাখে, বাইরে নয়।"},{"latex":"\\[ 0.70 \\le 0.55\\ (\\text{False}) \\ \\Rightarrow\\ \\text{else}: b = 0, \\qquad \\infty \\le 0.55\\ (\\text{False}) \\ \\Rightarrow\\ b = 0 \\]","text":"illustrative Wave B (0.70 m @ +20 deg): প্রথম clause-ই False, else branch <code>UInt16()</code>-এর default 0 পাঠায় — buzzer চুপ, আর এই OFF object visible থাকা অবধি প্রতিটি scan-এ বারবার publish হয়। সব qualifying beam-ই <code>inf</code> এমন cone-ও একই পথে নামে — <code>inf &lt;= 0.55</code> False।"},{"latex":"\\[ d_k = 0.5499 \\Rightarrow b_k = 1, \\qquad d_k = 0.5501 \\Rightarrow b_k = 0 \\]","text":"illustrative chatter: পরপর দুই scan-এ দূরত্ব 0.5499 আর 0.5501 হলে buzzer প্রথমটায় বাজে, দ্বিতীয়টায় চুপ; তৃতীয় scan-এ আবার 0.5499 হলে আবার বাজে। hysteresis H = 0 বলে মাত্র 0.2 mm দোলাতেই অবস্থা উল্টে যায় — scan rate-এ চলা এই toggling-ই chatter, আর animation-এর distance-axis-এ object-টি সীমানা-রেখার ঠিক গায়ে দাঁড়িয়ে থাকলে বাজার-থামার এই কাঁপুনি দেখা যায়।"}],"mapping":[{"code":"if minDist <= self.ResponseDist and minDist != 0.0:","math":"\\( b = \\mathbf{1}\\left[ (d_{min} \\le R) \\wedge (d_{min} \\ne 0) \\right] \\)","text":"দুই clause-এর AND-কে একটি indicator-এ ভাঁজ করা যায় — শর্ত সত্য হলে 1, নাহলে 0। কল-অর্ডার খেয়াল করো: তুলনাটি <code>minDist &lt;= self.ResponseDist</code> — বাঁয়ে এই scan-এর মাপা মান, ডানে parameter; দ্বিতীয় clause-টি L68-এর আগের ছাঁকনির সাথে মিলে গিয়ে কার্যত প্রতিরক্ষামূলক।"},{"code":"b.data = 1               # 1 means BEEP!","math":"\\( b = 1 \\)","text":"L90-এর <code>UInt16()</code> প্রথমে default 0 নিয়ে জন্মায়, তারপর এই assignment সেটিকে 1 করে — অর্থাৎ ON বানাতে দুই ধাপ লাগে। <code>data</code> ছাড়া UInt16-এর আর কোনো field নেই, তাই message-টির একটাই অস্তিত্ব: এই সংখ্যাটি।"},{"code":"self.pub_Buzzer.publish(UInt16()) ","math":"\\( b = 0 \\)","text":"else-পথে variable নেই — default constructor-এর <code>data = 0</code> মানটাই inline temporary হিসেবে সোজা publish হয়ে যায়; লাইনের শেষ trailing space-টি source-fidelity। গাণিতিকভাবে এটি Level 2-এর সমীকরণের দ্বিতীয় লাইন: otherwise-এর মান 0।"}],"failure":["<code>ResponseDist</code> খুব বড় করে দিলে (যেমন 5.0) ঘরের দেয়াল বা 2 m দূরের জিনিসও zone-এ পড়ে — প্রতিটি scan-এ b = 1, buzzer সত্যিকারের constant বাজতে থাকে। alarm তখন তথ্য দেয় না, শুধু শব্দ দেয়; কিছুক্ষণ পরেই মানুষ beep-কে উপেক্ষা করা শিখে ফেলে।","<code>ResponseDist</code> খুব ছোট করলে (যেমন 0.05) উল্টো বিপদ: obstacle প্রায় contact-এর দূরত্বে না এলে শর্তই সত্য হয় না — buzzer প্রায় সবসময় চুপ, ঠিক ধাক্কার আগ মুহূর্তে হয়তো কয়েকটি scan বাজে। কার্যত silent-until-contact: guard নামের script-টি সতর্কতার কাজটাই করতে পারে না।","Hysteresis না থাকায় (H = 0) ঠিক 0.55 m-এ hover করা object-এ noise-এর দোলায় b প্রতি scan-এ flip করে — buzzer scan rate-এ on-off করে কাঁপতে থাকে (chatter)। শব্দটা অসংলগ্ন শোনায়, আর বারবার চালু-বন্ধ হওয়া buzzer-এর নিজের আয়ুও কমে।","else branch-টি মুছে ফেললে out-of-zone scan-গুলোতে আর কেউ 0 publish করে না — প্রথমবার b = 1 যাওয়ার পরই <code>/beep</code>-এ সেই 1 latch হয়ে যায়। খোলা মাঠে একা দাঁড়িয়েও robot বাজতেই থাকে; L73/L83-এর সাময়িক latch-ফাঁদ তখন স্থায়ী রূপ নেয়।","<code>&lt;=</code>-এর জায়গায় <code>&lt;</code> লিখে ফেললে closed সীমানাটি খুলে যায় — ঠিক 0.55 m দূরত্বে থাকা object-এর জন্য শর্ত False হয়ে else-এ পড়ে, buzzer চুপ থাকে। vendor নিজেই যে সংখ্যাটিকে Danger Zone-এর সীমা বলে চিহ্নিত করেছে, সীমানার ঠিক ওই বিন্দুতে দাঁড়ানো object সেটিকে বিশ্বাস করাতে পারে না।"]},"robot":{"correct":"illustrative Wave C-তে (0.48 m @ 0 deg) L89 সত্যি হওয়ায় প্রতিটি scan-এ <code>/beep</code>-এ 1 যায় — buzzer টানা বাজতে থাকে, console-এ <code>minDist: 0.48</code> লাইন নামে, আর deadzone-এর কারণে <code>angular.z = 0.0</code> হওয়ায় চাকা স্থির — lidar ঘুরছে, শরীর দাঁড়িয়ে, শব্দ চালু। Wave B-তে (0.70 m @ +20 deg) else branch প্রতিটি scan-ে default-0 publish করে buzzer চুপ রাখে, আর robot একই scan-এর steering chain মেনে +0.417 rad/s-এ বাঁদিকে ঘোরে। Wave D-এর (0.50 m, in-zone) পরে Wave E এলে (সামনে কোনো valid beam নেই) L73-এর return আসার আগে alarm block পড়েই না — <code>/beep</code> D-এর 1-ই latch করে রাখে: buzzer বাজতেই থাকে, চাকা শেষ command মেনে চলে, শুধু console-এর minDist লাইনটুকু হঠাৎ থেমে যায়।","incorrect":"<code>ResponseDist</code> 5.0 করে দিলে 2 m দূরের দেয়ালও zone-এ পড়ে — buzzer বিরতিহীন বাজতে থাকে, robot সেই দিকে ঘুরে দাঁড়ায়, আর alarm-এর শব্দ অল্প সময়েই অর্থহীন হয়ে যায়। 0.05 করলে উল্টোটা ঘটে — object একেবারে গায়ের কাছে না এলে buzzer চুপ, robot নীরবে spin করে প্রায় ধাক্কা খায়। Hysteresis না থাকায় ঠিক 0.55 m-এ hover করা object-এ প্রতি scan-এ beep চালু-বন্ধ হয়ে buzzer কাঁপা শব্দ ছাড়ে। আর else branch উঠিয়ে দিলে প্রথম beep-এর পর খোলা মাঠেও buzzer চিরকাল বাজে — Joy-এর zero-Twist brake চাকা থামালেও শব্দ থামে না, কারণ L83-এর return <code>/beep</code> ছুঁয়েই দেখে না; Ctrl+C-র পরেও শব্দ থামে না — exit_pro-র brake শুধু <code>/cmd_vel</code> শূন্য করে, <code>/beep</code>-কে নয়।"},"animType":"alarmBuzzer"},{"n":13,"id":"part-13","fname":"laser_Warning.py","enTitle":"Tracking — PID Compute & Sign Branches","lang":"python","start":96,"end":110,"flags":[],"explain":[{"a":97,"b":98,"text":"L97-এর banner <code># --- THE TRACKING LOGIC ---</code> ঘোষণা করে buzzer-এর ফয়সালা শেষ — L89-95-এর alarm block-এর পরে এবার steering-এর পালা। L98 <code>velocity = Twist()</code> দিয়ে একেবারে fresh message তৈরি হয়, সব field-এর default 0.0। এই zero-start-টাই পুরো design-এর ভিত্তি: নিচের লাইনগুলো শুধু <code>angular.z</code> set করবে, <code>linear.x</code> কোথাও ছোঁয়া হবে না — ফলে guard-এর robot কখনও সামনে আগায় না, জায়গায় বসে pivot করে (spin-in-place)।"},{"a":99,"b":99,"text":"L99 <code>print(\"minDistID: \", minDistID)\t</code> — closing paren-এর পরে সোর্স লাইনের একেবারে শেষে একটা TAB অক্ষর বসে আছে, verbatim এমনই রাখা হয়েছে (console-এ অদৃশ্য, editor-এ column একটু সরে থাকতে দেখা যায়)। registerScan-এর চারটা debug print-এর মধ্যে এটি দ্বিতীয়: L85-এ দূরত্ব (<code>minDist</code>), এখানে কোণ, তারপর L112 ও L120-এ deadzone-আর-damping-এর আগে-পরের মান। অর্থাৎ প্রতি scan-এ console-এ দেখা যায় সবচেয়ে কাছের object কত degree পাশে — ঘুরার হিসাব ঠিক দিকে যাচ্ছে কি না, এই ছাপ থেকেই ট্র্যাক করা যায়।"},{"a":101,"b":102,"text":"দুইটি comment-ই এই অংশের control law-এর সার বলে দেয়: <code>Target Angle is 0 (straight ahead)</code> — robot-এর নাক যেখানে, সেটাই লক্ষ্য; <code>Current Angle is minDistID</code> — ±45° cone-এর ভেতরের closest object এখন যে কোণে বসে (L78-এ বের করা)। কাজ একটাই: এই দুইয়ের ফারক শূন্যে নামানো। এখানে একটা অনুপস্থিতি খেয়াল করুন — folder 12-র tracker closest object-কে 0.55 m দূরত্বে ধরে রাখত (minDist-এ snap বসিয়ে), guard-এ সেই snap-এর কোনো চিহ্ন নেই: দূরত্ব নিয়ে এই ফাইল কিছুই করে না, শুধু মুখ ঘোরায়।"},{"a":103,"b":103,"text":"L103 এই Part-এর হৃদয়: <code>ang_pid_compute = self.ang_pid.pid_compute(abs(minDistID) / 72, 0)</code>। এক লাইনে তিনটি সিদ্ধান্ত। প্রথমত <code>abs(minDistID)</code> — error সবসময় sign-মুক্ত; PID-টিকে শুধু \"কতটা ঘুরতে হবে\" জানানো হয়, \"কোন দিকে\" সেই ভার পরের if/elif-এর ঘাড়ে। দ্বিতীয়ত দ্বিতীয় argument <code>0</code> — target কোণ শূন্য, সোজা সামনে, তাই effective error দাঁড়ায় |a|/72 − 0। তৃতীয়ত <code>/ 72</code> — একটি bare magic number; ফাইল কোথাও এর ব্যাখ্যা দেয় না, degree-কে unitless scale-এ নামানো ছাড়া আর কিছুই নিশ্চিত করে বলা যায় না। SinglePID vendor module (L13-এর star-import) থেকে এসেছে, internal এই folder-এ নেই — L48 শুধু gain (3.0, 0.0, 5.0) জানায়; নিচের সব সংখ্যা তাই Kp-only ভাবে illustrative।"},{"a":105,"b":107,"text":"L105-এর comment নিয়মটি বলে দেয়: <code>If the object is to the left (positive angle), turn left</code>। fused ring-এ কোণ −44…+44 degree পর্যন্ত চলে, ROS convention-এ positive দিক মানে বাঁ দিক। L106-এর শর্ত <code>if 0 &lt; minDistID :</code> — colon-এর আগে একটা space, সোর্স verbatim এমনই। শর্ত সত্য হলে L107 <code>velocity.angular.z = ang_pid_compute</code>: PID-এর অঋণাত্মক ফল positive z হয়ে বসে, positive angular.z মানে CCW — বাঁ দিকের wheel পিছনে, ডান দিকের wheel সামনে, robot জায়গায় বাঁ দিকে pivot করে object-মুখী হয়।"},{"a":108,"b":110,"text":"L108-এর comment উল্টো কেসটি বলে: <code>If the object is to the right (negative angle), turn right</code>। L109 <code>elif minDistID &lt; 0:</code> — এখানে colon-এর আগে space নেই, L106-এর সঙ্গে তফাতটা খেয়াল করুন (দুটোই সোর্স fidelity)। L110 <code>velocity.angular.z = -ang_pid_compute</code> — একই magnitude, sign উল্টো; negative z মানে CW, ডান দিকে pivot। আর <code>minDistID</code> ঠিক 0.0 হলে দুই শর্তই false — কোনো branch ঢোকে না, L98-এর fresh Twist-এর default 0.0-ই z হয়ে থাকে, robot নড়ে না। ডিজাইনের সার: magnitude PID থেকে, direction এই sign-branch দুটি থেকে — <code>abs()</code> আর if/elif মিলে একটি mirror-symmetric steering বানায়।"}],"math":{"intro":"এই Part-টিই ফাইলের গণিতের হৃদয়: সামনের closest object কত degree পাশে (a), তা থেকে কত জোরে (u = ang_pid_compute) কোন দিকে (z) ঘুরতে হবে — L103 প্রথম প্রশ্নের উত্তর দেয়, L106-110 বাকি দুটির।","levels":[{"label":"Level 1 — Symbols ও units","latex":"\\[ a = \\texttt{minDistID}\\ [\\deg], \\qquad e = \\dfrac{|a|}{72}\\ [\\text{unitless}], \\qquad u = \\texttt{ang\\_pid\\_compute}, \\qquad z = \\texttt{velocity.angular.z}\\ \\left[\\tfrac{\\mathrm{rad}}{\\mathrm{s}}\\right] \\]","text":"a হলো cone-এর ভেতরের closest object-এর কোণ, fused ring-এ degree-তে, মান −44 থেকে +44-এর ভেতর। 72 দিয়ে ভাগ হয়ে e-এর কোনো unit থাকে না। u হলো PID-এর বের করা turn-demand, z হলো তাতে sign বসিয়ে wheel-এ পাঠানো ঘূর্ণন। Gain: Kp = 3.0, Ki = 0.0, Kd = 5.0 (L48)।"},{"label":"Level 2 — Error তৈরি","latex":"\\[ e = \\dfrac{|a|}{72} - 0 = \\dfrac{|a|}{72} \\]","text":"pid_compute-এর দ্বিতীয় argument 0 — target কোণ শূন্য, সোজা সামনে (L102-এর comment-ই তা বলে)। শূন্য বিয়োগে কিছু বদলায় না, তাই e শুধু |a|/72। abs() থাকায় e কখনও ঋণাত্মক হয় না — দিকের দায় PID-এর বাইরে, L106/L109-এর sign-branch-এর কাঁধে।"},{"label":"Level 3 — Kp-view algebra (illustrative)","latex":"\\[ u = K_p\\,e = 3\\cdot\\dfrac{|a|}{72} = \\dfrac{|a|}{24} \\]","text":"Ki = 0 বলে Kp-only view-তে u-তে বাঁচে শুধু proportional term (SinglePID-এর ভেতরের হিসাব এই folder-এ নেই)। 3/72 = 1/24 — অর্থাৎ object প্রতি 24 degree করে পাশে সরলে u এক করে বাড়ে; a = 20° হলে u = 20/24 ≈ 0.833।"},{"label":"Level 4 — Sign-branch geometry","latex":"\\[ z = \\begin{cases} +u, & a > 0 \\quad (\\text{left, CCW}) \\\\ -u, & a < 0 \\quad (\\text{right, CW}) \\\\ 0, & a = 0 \\quad (\\text{no branch}) \\end{cases} \\]","text":"PID magnitude দেয়, if/elif direction দেয়। ROS convention-এ positive angular.z মানে CCW (বাঁ দিকে), negative মানে CW (ডান দিকে)। দুই দিকের |z| হুবহু সমান — +20° আর −20° একই জোরে ঘুরায়, শুধু দিক উল্টো: আচরণ mirror-symmetric। a ঠিক 0.0 হলে দুই শর্তই false, L98-এর default 0.0-ই থেকে যায়।"},{"label":"Level 5 — Range ও ceiling (pre-damping)","latex":"\\[ 0 \\le |a| < 45^{\\circ}: \\qquad 0 \\le e < \\tfrac{45}{72} = 0.625, \\qquad 0 \\le u < 3\\cdot\\tfrac{45}{72} = 1.875 \\]","text":"cone strict &lt; 45° (L68) বলে e-এর সীমা 0.625-এর নিচে, u-এর সীমা 1.875-এর নিচে; এই illustrative ring-এ কোণ পূর্ণ degree-তে পড়ে, তাই বাস্তবে সবচেয়ে বড় |a| = 44, u = 44/24 ≈ 1.83 — 1.875 গাণিতিক সীমা মাত্র। হিসাব এখানেই থামে: L115-এর deadzone আর L118-এর ×0.5 damping পরের Part-এর ব্যাপার, তাই এই স্তরের সব সংখ্যা pre-damping।"},{"label":"Level 6 — পূর্ণ P-D form ও Kd transient","latex":"\\[ u_n = K_p\\,e_n + K_d\\,(e_n - e_{n-1}), \\qquad K_i = 0, \\quad K_d = 5 \\]","text":"প্রকৃত SinglePID (vendor internal, illustrative) derivative term-ও রাখে। Kd = 5 বেশ বড়: scene বদলের পরে প্রথম call-এ e হঠাৎ লাফায় কিন্তু e_{n-1} এখনও পুরোনো দৃশ্যের মান — derivative term তখন একটা same-sign transient যোগ করে, ঘুরার শুরুতে সাময়িক overshoot লাগে; দ্বিতীয় call থেকে স্থির। ঠিক এই অনিশ্চয়তাই উপরের সব u/z সংখ্যাকে illustrative করে রাখে।"}],"numeric":[{"latex":"\\[ e = \\tfrac{|+20|}{72} = \\tfrac{20}{72} = 0.278, \\qquad u = 3 \\times 0.278 = 0.833, \\qquad z = +0.833\\ \\tfrac{\\mathrm{rad}}{\\mathrm{s}} \\]","text":"Wave B (0.70 m @ +20 deg): 0.70 &gt; 0.55, তাই buzzer চুপ করেই tracking চলে। a positive বলে L106-এর branch — এই স্তরে z = +0.833 (pre-damping; ×0.5 পরের Part), robot বাঁ দিকে CCW pivot করে মুখ ঘোরায়। সব সংখ্যা Kp-view, illustrative।"},{"latex":"\\[ e = \\tfrac{|-20|}{72} = 0.278, \\qquad u = 3 \\times 0.278 = 0.833, \\qquad z = -0.833\\ \\tfrac{\\mathrm{rad}}{\\mathrm{s}} \\]","text":"Wave D (0.50 m @ −20 deg): 0.50 ≤ 0.55, তাই buzzer বাজছে। একই magnitude, শুধু L109-এর branch sign উল্টে দেয় — z = −0.833, ডান দিকে CW pivot, বাজতে বাজতেই ঘোরা। B আর D-র পাশাপাশি তুলনাই abs()+sign-branch জোড়ার কাজ দেখিয়ে দেয় (illustrative)।"},{"latex":"\\[ a = 0.0: \\qquad e = \\tfrac{0}{72} = 0, \\qquad u = 0, \\qquad z = 0.0\\ (\\text{no branch, default kept}) \\]","text":"Wave C (0.48 m @ 0 deg): object হুবহু সামনে, danger zone-এর ভেতরে — buzzer বাজছে কিন্তু a = 0.0। L106 ও L109 দুটোই false, তাই L98-এর default 0.0-ই z: robot দাঁড়িয়ে শুধু বিঁপবিঁপ করে; linear.x-ও কোথাও set হয় না, তাই এগোনোর প্রশ্নই ওঠে না।"},{"latex":"\\[ |a| = 44: \\;\\; e = \\tfrac{44}{72} = 0.611, \\;\\; u = 1.833; \\qquad \\text{limit } |a| = 45: \\;\\; u = 1.875 \\]","text":"Cone-এর কিনারা (illustrative): এই ring-এ সবচেয়ে পাশের valid beam 44°, তাই u-এর বাস্তব সর্বোচ্চ ≈ 1.83; strict &lt; 45° হওয়ায় ঠিক 45° beam cone-এ ঢোকেই না — 1.875 সীমা মাত্র। declare করা angular = 1.0 parameter (L38) কোথাও enforce হয় না, তাই এই ceiling কেটে দেওয়ার কোনো clamp নেই।"}],"mapping":[{"code":"velocity = Twist()","math":"\\( x_0 = 0,\\; z_0 = 0 \\)","text":"প্রতি scan-এ fresh শূন্য message; linear.x এরপর আর কোনোদিন set হয় না, তাই x চিরকাল 0 — guard-এর spin-in-place আচরণের বীজ এখানেই বোনা।"},{"code":"abs(minDistID) / 72","math":"\\( e = |a|/72 \\)","text":"degree থেকে unitless-এ scaling; 72-এর কোনো named constant বা ব্যাখ্যা ফাইলে নেই — bare magic number, শুধু পর্যবেক্ষণযোগ্য পাটিগণিতটুকুই বলা যায়।"},{"code":"self.ang_pid.pid_compute(abs(minDistID) / 72, 0)","math":"\\( u = K_p\\,(|a|/72 - 0) = |a|/24 \\)","text":"প্রথম argument current (normalized কোণ), দ্বিতীয়টা target 0; Kp = 3 (L48)। SinglePID-এর internal এই folder-এ নেই — u-সূত্রটি Kp-view, illustrative।"},{"code":"if 0 < minDistID :","math":"\\( a > 0 \\;\\Rightarrow\\; z = +u \\)","text":"বাঁ-পাশের object: positive z, CCW ঘূর্ণন। শর্তে colon-এর আগের space-সহ যেটা সোর্সে আছে সেটাই এখানে।"},{"code":"elif minDistID < 0:","math":"\\( a < 0 \\;\\Rightarrow\\; z = -u \\)","text":"ডান-পাশের object: negative z, CW ঘূর্ণন। a = 0 হলে দুই mapping-ই প্রযোজ্য হয় না — z তার default 0.0-এ থেকে যায়।"}],"failure":["দুই branch-এর sign উল্টে গেলে robot object-এর উল্টো দিকে ঘুরতে থাকে — Wave B-র pillar বাঁয়ে থাকতে ডানে spin করবে; কয়েক scan-এর মধ্যেই object ±45° cone-এর বাইরে চলে যাবে, তখন L73-এর empty return এসে /cmd_vel আর /beep দুটোই শেষ মানে latch করে রাখবে: wheel বিপথে ঘুরতেই থাকবে, buzzer আটকে থাকবে।","72 ভুল হলে responsiveness সরাসরি বদলে যায় — 7.2 বসালে e দশগুণ: 5° পাশের object-এও u ≈ 2.08, ঘূর্ণন whip-এর মতো হঠাৎ; 720 বসালে 40° পাশে থাকলেও u ≈ 0.17, পরের Part-এর |u| &lt; 0.5 deadzone সব গিলে ফেলবে — robot মুখই ঘোরাবে না, শুধু বিঁপবিঁপ করবে।","abs() বাদ দিয়ে সরাসরি minDistID পাঠালে ডান-পাশের object-এর u ঋণাত্মক হয়ে যায়, আর L110 সেটাকে আবার উল্টো করে — a = −20° হলে z = +0.833: object ডানে, ঘূর্ণন বাঁয়ে। abs() আর sign-branch এক যুগল; একটা বাদ গেলেই দিক ওলটে যায়।","কোনো clamp নেই — L38-এ declare করা angular = 1.0 পড়ার পর আর কখনও ব্যবহার হয়নি। cone-এর কিনারায় এই স্তরের z 1.83 পর্যন্ত (সীমায় 1.875) উঠতে পারে, কিন্তু publish-এর আগেই L118-এর x0.5 damping সেটাকে অর্ধেক করে দেয় — wheel-এ সর্বোচ্চ যায় ~0.9375 rad/s, declared 1.0-এর ঠিক নিচে। বিপদটা সংখ্যায় নয়, ভরসায়: cap-টা parameter-এ নেই, damping-এর coincidence-এ।","বড় Kd = 5 থাকায় scene বদলানোর পরের প্রথম call-এ derivative term একটা same-sign transient যোগ করে (illustrative) — ঘুরার শুরুতে সাময়িক overshoot; দ্বিতীয় call থেকে e স্থির হয়ে transient মিলিয়ে যায়, তাই tuning-এর সিদ্ধান্ত প্রথম ছাপ দেখে নেওয়া ঠিক নয়।"]},"robot":{"correct":"প্রতি fused scan-এ alarm block-এর ঠিক পরেই এই অংশ চলে: console-এ L85-এর <code>minDist</code>-এর পাশে L99-এর <code>minDistID</code> ছাপ হয়, তারপর fresh Twist-এ শুধু angular.z বসে। Wave B-তে (0.70 m @ +20 deg) PID দেয় u = 0.833, L106-এর branch সেটাকে positive করে বসায় — বাঁ দিকের wheel পিছনে, ডান দিকের wheel সামনে, robot জায়গায় CCW pivot করে pillar-মুখী হয় (এই স্তরে z = +0.833, damping পরে); buzzer চুপ, কারণ 0.70 &gt; 0.55। Wave D-তে (0.50 m @ −20 deg) একই magnitude উল্টো দিকে — ডানে CW ঘুরা, বাজতে বাজতে। Object হুবহু সামনে (a = 0.0) হলে কোনো branch-ই ঢোকে না, দুই পাশের wheel সমান থেমে থাকে; linear.x কখনও set না হওয়ায় robot এক চুলও সামনে যায় না।","incorrect":"Branch-এর sign উল্টে গেলে robot ঠিক উল্টো কাজ করে — বাঁয়ে pillar থাকতে ডানে spin, কয়েক সেকেন্ডেই object cone-এর বাইরে; তখন L73-এর return শেষ /cmd_vel latch করে রাখে: wheel ঘুরতেই থাকে, /beep-ও আটকে থাকে, robot কখনও স্থির হয় না। 72 ভুল হলে হয় whip নয় অবশ — 720 করলে 40° পাশের object-ও ঘুরাতে পারে না (u ≈ 0.17, পরের deadzone-এ শূন্য), ফলে robot মুখ ঘুরিয়ে দাঁড়িয়ে শুধু বিঁপবিঁপ করে। আর কোনো clamp নেই বলে cone-এর কিনারায় u 1.83 ছুঁলেও publish-এর আগে L118-এর x0.5 damping তা অর্ধেক করে দেয় — wheel-এ যায় ~0.9375 rad/s: declared angular 1.0 কেউ আটকায় না, সীমার মধ্যে থাকাটা damping-এর ভাগ্য"},"animType":"pidDial"},{"n":14,"id":"part-14","fname":"laser_Warning.py","enTitle":"Deadzone, Damping & Spin-Only Publish","lang":"python","start":111,"end":124,"flags":[],"explain":[{"a":112,"b":112,"text":"L112 <code>print(\"orin_angular.z: \", velocity.angular.z)</code> — sign branch (L106-110) যে মান বসিয়েছে ঠিক সেটাই ছাপা হয়; লাইনের comment <code># Original calculated turn speed</code> বলে দেয় এটি এখনো \"original\": deadzone-ও প্রযোজ্য হয়নি, damping-ও নয়। এটি console debugging-এর baseline — L85-এর <code>minDist</code> আর L99-এর <code>minDistID</code>-এর পরে steering pipeline-এর আগে-পরে দেখানো print জোড়ার প্রথম সদস্য, শেষটি L120-এ। minDistID ঠিক 0.0 হলে কোনো sign branch-ই ঢোকেনি, তাই এখানে 0.0 ছাপা হবে; minDistID positive হলে +u, negative হলে −u।"},{"a":114,"b":115,"text":"L114-এর comment <code># Deadzone: If the object is almost directly in front, don't turn.</code> আর L115 সেটাই কোডে করে: <code>if abs(ang_pid_compute) &lt; 0.5: velocity.angular.z = 0.0</code> — এক লাইনেই লেখা compound statement, শর্ত সত্য হলে body সেই লাইনেই চলে। খেয়াল করো: শর্তটি z-কে নয়, PID-এর raw output <code>ang_pid_compute</code>-কে পরীক্ষা করে, আর <code>abs()</code> থাকায় মানটির magnitude-ই দেখা হয় — Kp-view-তে u সাধারণত অঋণাত্মক (illustrative), কিন্তু বড় Kd-এর কোনো transient কখনো ঋণাত্মক করলেও deadzone-টি ঠিকই কাজ করে। 0.5-টি একটি bare magic number, ফাইল কোথাও এর ব্যাখ্যা দেয় না। Kp-only view-তে (illustrative) u = 3·(|a|/72) = |a|/24, তাই শর্তটি আসলে <b>|a| &lt; 12 ডিগ্রি</b>-র সমান: object সামনের দিক থেকে ১২ ডিগ্রির মধ্যে থাকলে turn-ই হবে না। সীমানায় ঠিক 12 ডিগ্রি হলে u = 0.5 ঠিক পড়ে, <code>&lt; 0.5</code> False হয়ে value pass করে যায়, z = ±0.25 বেঁচে থাকে। folder 12-র tracker-এ (Kp=2) এই edge ছিল 18 ডিগ্রি — guard-এর deadzone-টি লক্ষ্যমুখী আরও সরু।"},{"a":117,"b":118,"text":"L117-এর comment <code># Slow down the turning speed to 50% so the robot doesn't whip around too fast.</code> আর L118 <code>velocity.angular.z = velocity.angular.z * 0.5</code> — comment ৫০% বলছে আর কোড হুবহু তাই করে (folder 12-র tracker-এ এই জায়গায় 0.6 ছিল, guard আরও ধীরে ঘোরে)। Damping-টি deadzone-এর <b>পরে</b> বসেছে, তাই deadzone-এ শূন্য হওয়া z এখানে 0.0×0.5 = 0.0-ই থাকে — নতুন কোনো turn জন্মায় না; আর pass করা মান অর্ধেক হয়ে যায়। ফলে effective ceiling: cone-এর ধারে |a| 45 ডিগ্রির একেবারে নিচে গেলে u প্রায় 3·(45/72) = 1.875 হয়, damping-এর পরে z প্রায় ±0.9375 rad/s (tracker-টিতে ছিল ±0.75)। Wave A-তে u = 0.583 pass করেছে, তাই এই লাইনের পরে z = +0.292 rad/s।"},{"a":120,"b":120,"text":"L120 <code>print(\"angular.z: \", velocity.angular.z)</code> — comment <code># Final turn speed</code>: deadzone ও damping দুই ধাপের পরের চূড়ান্ত মান। L112-এর <code>orin_angular.z</code>-এর সাথে জোড়া বাঁধলে এই দুটি লাইন console-এ পুরো pipeline-টি দেখিয়ে দেয়: Wave D-তে orin −0.833 থেকে final −0.417 (শুধু damping খেয়েছে), Wave F-এ orin +0.333 থেকে final 0.0 (deadzone-ই খেয়ে গেছে)। Debugging-এ orin-কেই final ভেবে নেওয়া সবচেয়ে সহজ ভুল — মানটি এই দুই ধাপে বদলে গেছে।"},{"a":122,"b":124,"text":"L122-এর comment <code># Send the movement command to the wheels!</code> আর L124 <code>self.pub_vel.publish(velocity)</code> — L30-এ তৈরি <code>/cmd_vel</code> publisher-এ (depth 1) এই Twist-টি যায়, base driver সেটিকে wheel-এর গতিতে ভাঙে। মাঝের L123-এর comment-টি এই script-এর সবচেয়ে গুরুত্বপূর্ণ স্বীকারোক্তি: <code># Note: linear.x is never set here, so the robot stays perfectly still and just spins in place!</code> — সত্যিই সত্যি: পুরো ফাইলে linear.x কোথাও assign হয় না, linear PID-ও নেই, তাই L98-এর <code>velocity = Twist()</code>-এর default 0.0-ই রয়ে যায়। ফলে publish হওয়া command সবসময় (0, z) আকারের pure-rotation: robot জায়গায় ঘুরে সবচেয়ে কাছের object-মুখী হয়, কিন্তু কখনো তার দিকে এগোয় না — folder 12-র tracker-এর approach আচরণটি এই guard-এ নেই। এটি warning node: মুখ ফেরানো আর বাজানোই কাজ, এগিয়ে গিয়ে ধরা নয়।"}],"math":{"intro":"এই Part-এর গণিত তিনটি প্রশ্নের উত্তর দেয় — PID output কত ছোট হলে turn বাতিল হয় (deadzone), বেঁচে থাকা মান কত হয় (damping), আর publish হওয়া command-এর চূড়ান্ত আকার কী (spin-only Twist)।","levels":[{"label":"Level 1 — Symbols ও units","latex":"\\[ u = \\texttt{ang\\_pid\\_compute}, \\qquad z = \\texttt{velocity.angular.z}\\ \\left[\\tfrac{\\mathrm{rad}}{\\mathrm{s}}\\right], \\qquad T_d = 0.5,\\quad \\gamma = 0.5 \\]","text":"u হলো L103-এর <code>pid_compute</code>-এর raw output — deadzone-এর আগের, damping-এর আগের মান; z হলো শেষে publish হওয়া angular velocity। T_d হলো deadzone-এর threshold আর γ হলো damping factor — দুটোর মানই 0.5, দুটোই bare magic number, ফাইল কোনোটিরই ব্যাখ্যা দেয় না।"},{"label":"Level 2 — Kp-view মৌলিক সম্পর্ক (illustrative)","latex":"\\[ u = K_p\\,e = 3\\cdot\\frac{|a|}{72} = \\frac{|a|}{24}, \\qquad e = \\frac{|\\mathrm{minDistID}|}{72} \\]","text":"L103-এ e = |minDistID|/72 ঢুকে গিয়েছিল; Ki = 0 হওয়ায় Kp-only view-তে u দাঁড়ায় শুধু |a|/24 — a হলো সবচেয়ে কাছের object-এর angle (ডিগ্রি)। SinglePID-এর ভেতরের হিসাব এই folder-এ নেই, তাই রূপটি illustrative।"},{"label":"Level 3 — Deadzone-এর algebra","latex":"\\[ \\frac{|a|}{24} < 0.5 \\;\\Longleftrightarrow\\; |a| < 12^{\\circ} \\;\\Rightarrow\\; z = 0 \\]","text":"object সামনের দিক থেকে ১২ ডিগ্রির মধ্যে থাকলে turn হয় না — L115 আসলে এই সরু band-টিকেই কোডে লিখেছে। সীমানায় |a| = 12° হলে u = 0.5 ঠিক সমান, <code>&lt; 0.5</code> False হয়ে শর্তটি pass করে — তখন z = ±0.25 বেঁচে যায়। folder 12-র tracker (Kp = 2) একই শর্তে পেয়েছিল 18° — guard-এর deadzone কাছাকাছি offset-গুলোতে আরও strict।"},{"label":"Level 4 — Damping ও effective ceiling","latex":"\\[ z_{final} = 0.5\\,z_{pre}, \\qquad |a| \\to 45^{-}:\\;\\; z \\to 0.5\\times 3\\times\\tfrac{45}{72} = 0.9375\\ \\tfrac{\\mathrm{rad}}{\\mathrm{s}} \\]","text":"damping deadzone-এর পরে বসেছে, তাই শূন্য থাকা মান শূন্যই থাকে (0×0.5 = 0), আর cone-এর ধারের সর্বোচ্চ মানও অর্ধেক হয়ে যায় — সর্বোচ্চ প্রায় ±0.9375 rad/s (tracker-টিতে ছিল ±0.75)। Comment-এর ৫০% আর কোডের <code>* 0.5</code> হুবহু মিলে যায়।"}],"numeric":[{"latex":"\\[ e = \\tfrac{14}{72} = 0.194, \\quad u = 3e = 0.583 \\ge 0.5 \\;\\Rightarrow\\; z = 0.5\\times 0.583 = +0.292\\ \\tfrac{\\mathrm{rad}}{\\mathrm{s}} \\]","text":"Wave A (pillar 0.90 m @ +14 deg): deadzone pass, sign branch positive — robot বাঁয়ে (CCW) ঘোরে; 0.90 &gt; 0.55 হওয়ায় buzzer চুপ। সব সংখ্যা Kp-view, illustrative।"},{"latex":"\\[ e = \\tfrac{0}{72} = 0, \\quad u = 0 < 0.5 \\;\\Rightarrow\\; z = 0.0, \\qquad 0.48 \\le 0.55 \\Rightarrow /beep = 1 \\]","text":"Wave C (0.48 m @ 0 deg): object একেবারে সামনে আর danger zone-এর ভেতরে — L115 deadzone-টি z = 0.0 করে, কিন্তু alarm (L89-95) আগেই fire করে রেখেছে, তাই robot দাঁড়িয়ে শুধু বাজতে থাকে (illustrative)।"},{"latex":"\\[ u = 3\\cdot\\tfrac{8}{72} = 0.333 < 0.5 \\;\\Rightarrow\\; z = 0.0 \\]","text":"Wave F (0.80 m @ +8 deg): 8 ডিগ্রি ১২ ডিগ্রির band-এর ভেতরে, তাই ছোট offset-টি deadzone-এ চাপা পড়ে — ঘোরে না; দূরত্ব 0.55 m-এর বাইরে বলে buzzer-ও চুপ (illustrative)।"},{"latex":"\\[ u = 3\\cdot\\tfrac{20}{72} = 0.833 \\ge 0.5 \\;\\Rightarrow\\; z = -0.5\\times 0.833 = -0.417\\ \\tfrac{\\mathrm{rad}}{\\mathrm{s}} \\]","text":"Wave D (0.50 m @ −20 deg): sign branch (L109-110) মানটি ঋণাত্মক করেছে, damping-এর পর −0.417 — robot ডানে (CW) ঘোরে, আর 0.50 ≤ 0.55 হওয়ায় বাজতে বাজতেই ঘোরে (illustrative)।"}],"mapping":[{"code":"if abs(ang_pid_compute) < 0.5: velocity.angular.z = 0.0","math":"\\( |u| < T_d \\;\\Rightarrow\\; z = 0 \\)","text":"শর্তটি চলে z-এর উপরে নয়, damping-এর আগের u-এর উপরে — কোন turn বাতিল হবে সেই সিদ্ধান্তটি এখানেই হয়; 0.5 threshold-এর কোনো ব্যাখ্যা ফাইলে নেই।"},{"code":"velocity.angular.z = velocity.angular.z * 0.5","math":"\\( z_{final} = \\gamma\\, z_{pre}, \\;\\gamma = 0.5 \\)","text":"comment ৫০% বলে আর কোড হুবহু তাই ঘটায় — tracker-এর 0.6-এর বদলে 0.5, অর্থাৎ একই u-তে guard-এর wheel আরও ধীরে ঘোরে।"},{"code":"self.pub_vel.publish(velocity)","math":"\\( v = (\\,\\underbrace{0,\\ 0}_{\\mathrm{linear}},\\ z\\,) \\)","text":"linear.x কোথাও set হয়নি বলে published Twist-টির linear অংশ সবসময় সব-শূন্য — একমাত্র অশূন্য field হলো z; এটিই pure rotation, কোনো translation নেই।"}],"failure":["Deadzone-এর threshold বাড়িয়ে দিলে ব্যান্ডটি চওড়া হয়ে যায় — সামনের দিকের কাছাকাছি object-গুলোর দিকে robot আর মুখ ফেরায় না, অথচ 0.55 m-এর ভেতরে এলে buzzer বাজতেই থাকে: শব্দ আছে, movement নেই।","L118-এর damping বাদ দিলে ceiling 0.9375 থেকে লাফিয়ে 1.875 rad/s হয় — comment-এর \"whip around too fast\" সত্যি হয়ে দাঁড়ায়: robot হঠাৎ জোরে ঘুরে যায়, wheel-এর grip আর lidar-এর steering দুটোই খারাপ হয়।","Deadzone-এর শর্তটি damping-এর পরের z-এর উপরে বসিয়ে দিলে সীমা দ্বিগুণ চওড়া হয়ে যায় — |a| &lt; 24 deg পর্যন্ত সব turn বাতিল হয়ে robot কাছের object-কে ফিরেও তাকায় না।","Console-এ orin_angular.z-কেই final ভেবে নিলে turn speed দ্বিগুণ বড় মনে হয় — Wave A-তে 0.583 ছাপা হলেও wheel-এ আসলে 0.292 যায়; deadzone ও damping দুই ধাপের ফারাক মিলিয়ে না দেখলে tuning-এ ভুল হয়।","L123-এর অনুমান ভেঙে কেউ linear.x set করে দিলে spin-only আচরণটি হারিয়ে যায় — robot যে object-এর জন্য warning দিচ্ছে ঠিক তার দিকেই এগোতে শুরু করে, 0.55 m-এর danger zone-এ ঢুকে পড়ে।"]},"robot":{"correct":"Wave A-তে (pillar 0.90 m @ +14 deg) console-এ পরপর <code>orin_angular.z: 0.583</code> আর <code>angular.z: 0.292</code> ছাপা হয়, আর wheel-গুলো pure spin-এ চলে — বাম দিক পিছনে, ডান দিক সামনে — robot জায়গায় বসে CCW ঘুরে object-মুখী হয়, এক চুলও সামনে যায় না (linear.x = 0.0); 0.90 &gt; 0.55 হওয়ায় buzzer চুপ। Wave C-তে (0.48 m, একেবারে সামনে) deadzone z = 0.0 করে দেয় — robot দাঁড়িয়ে থেকে শুধু বাজতে থাকে, lidar-এর ring ঘুরতেই থাকে। Wave D-তে (0.50 m @ −20 deg) বাজতে বাজতে −0.417 rad/s-এ ডানে ঘোরে। প্রতিটি scan-এ এই chain আবার চলে, তাই object সরলে দিক বদলে যায় — এগোনো কখনো হয় না।","incorrect":"Damping-টি (L118) উঠে গেলে প্রতিটি publish-এ wheel-এ 1.875 rad/s পর্যন্ত যেতে পারত — robot হঠাৎ ঝাঁকুনি দিয়ে ঘুরে যেত, ঘুরন্ত অবস্থায় lidar-এর scan-ও ঘোলা হয়ে object-এর দিক নির্ভুল বের করতে ভুল করত। Deadzone-এর threshold বেশি চওড়া হলে সামনের কাছের object-কে ফিরে তাকানোই বাদ পড়ত — buzzer বাজছে কিন্তু robot নীরব-স্থির, মনে হতো warning-টি ভুল। আর এই node-এর উপরে approach আশা করা ভুল — linear.x কোথাও set হয়নি, তাই object এগিয়ে এলে দূরত্ব কমার একমাত্র কারণ object-নিজেই এগিয়ে আসা; কেউ linear drive যোগ করে দিলে robot danger zone-এ ঢুকে যাওয়া বিপদটিকেই নিজে তৈরি করত।"},"animType":"cmdVelVectors"},{"n":15,"id":"part-15","fname":"laser_Warning.py","enTitle":"exit_pro & main — Brake and Shutdown","lang":"python","start":125,"end":145,"flags":[],"explain":[{"a":125,"b":127,"text":"L124-এর <code>self.pub_vel.publish(velocity)</code> দিয়ে <code>registerScan</code>-এর দীর্ঘ কাজ শেষ; L125-এর blank line class-এর শেষ অংশটাকে আলাদা করে দেয়। <code># --- SAFETY SHUTDOWN FUNCTION ---</code> — comment নিজেই ঘোষণা করছে এবার কী আসছে: বিদায়ের যন্ত্রপাতি। <code>def exit_pro(self):</code> — <code>laserWarning</code> class-এর শেষ method, নামটা সম্ভবত \"exit procedure\"-র ছোট রূপ; argument শুধু <code>self</code>, কোনো return নেই — এর একটাই কাজ, নিচের লাইনগুলো দিয়ে robot-কে থামানো। Import-pass-এ শুধু এই <code>def</code>-টা bind হয়, body চলে না; body চলবে শুধু তখন, যখন L143-এর <code>finally</code> থেকে একে ডাকা হবে।"},{"a":128,"b":129,"text":"L128-এর comment পুরো পরিকল্পনা টানটান করে দিচ্ছে: <code>this runs a terminal command in the background to force the robot to stop</code> — Ctrl+C-র পরে terminal command-এর মাধ্যমে জোর করে থামানো। <code>cmd1 = \"ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist \"</code> — লক্ষ করুন closing quote-এর ঠিক আগে একটা <b>trailing space</b> আছে; চোখে প্রায় অদৃশ্য, কিন্তু এটাই message type আর পরের payload-র মাঝের separator — বাদ পড়লে L131-এ জোড়া লাগানো command-টা ভেঙে যেত। চার টুকরো: <code>ros2 topic pub</code> — ROS 2-র command-line publisher tool; <code>--once</code> — ঠিক একটা message দিয়েই process বেরিয়ে যাবে; <code>/cmd_vel</code> — L30-এ নিজের <code>pub_vel</code>-এর সেই একই topic, মানে চাকার motor driver-এর কান; আর <code>geometry_msgs/msg/Twist</code> — message-এর ধরন। মানে বাহন node-এর ভেতরের Python publisher নয় — ros2 CLI নিজেই একটা সম্পূর্ণ আলাদা publisher process হয়ে উঠবে।"},{"a":130,"b":131,"text":"<code>cmd2 = '''\"{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}\"'''</code> — বাইরে তিনটা single quote, ভেতরে পুরো payload double quote-এর মধ্যে। Triple-quote-এর সুবিধা: ভেতরের double quote-গুলো escape ছাড়াই বসানো যায়, আর ওই double quote shell-কে বোঝায় braces-এর পুরো মালাটা একটাই argument। ভেতরের বিষয়বস্তু YAML: <code>linear</code> আর <code>angular</code> দুই field-group, প্রতিটাতে x, y, z তিনটা করে — মোট ছয়টা সংখ্যা, সবগুলোই <code>0.0</code>; ros2 CLI এই YAML-কে parse করে একটা সম্পূর্ণ শূন্য <code>Twist</code> message বানাবে, অর্থাৎ L98-এর <code>velocity = Twist()</code>-এর মতোই \"কোনো অংশ নড়বে না\"। L131 <code>cmd = cmd1 + cmd2</code> — দুই টুকরো জোড়া লাগালেই সম্পূর্ণ shell command প্রস্তুত।"},{"a":132,"b":132,"text":"<code>os.system(cmd)</code> — L14-এ <code>import os</code>-এর একমাত্র ব্যবহার এই লাইনেই, গোটা file-এ <code>os</code> আর কোথাও নেই। Python এখানে একটা shell খুলে command-টা চালায়; ফলে সম্পূর্ণ আলাদা একটা process নিজেই <code>/cmd_vel</code>-এ একবার শূন্য-Twist publish করে বেরিয়ে যায়। প্রশ্ন উঠতেই পারে: L30-এর নিজের <code>pub_vel</code> দিয়ে <code>Twist()</code> পাঠালেই তো হতো? কিন্তু এই মুহূর্তটা teardown-এর মুহূর্ত — নিজের publisher আর rclpy context তখন অনিশ্চিত দশায় থাকতে পারে; <code>os.system</code>-এর brake node-এর কোনো অবস্থার উপর দাঁড়ানো নেই, node মরতে থাকলেও কাজ করে। শারীরিক অর্থে এটাই আসল ব্রেক: motor driver সর্বশেষ <code>/cmd_vel</code> command-ই ধরে রাখে, তাই শেষ scan-এর সিদ্ধান্ত Wave D-এর মতো <code>(0.0, -0.417)</code> ডানে ঘোরা হলে এই শূন্য-সংবাদ এসে চাকা থামায় — আর guard-এর শেষ command-এ <code>linear.x</code> কখনোই থাকে না (L123-এর comment নিজেই স্বীকার করে), তাই থামানোর হিসাবটাও শুধু ঘূর্ণনের। কিন্তু কী থামে না, সেটাই এই file-এর নিজস্ব শিক্ষা: brake শুধু <code>/cmd_vel</code> ছোঁয়, <code>/beep</code>-এ হাত দেয় না। Wave C বা D-এর মতো alarm-অবস্থায় বিপ ON ছিল (L90-92); Ctrl+C-র পরেও buzzer তার শেষ মানেই latch করে রাখে — node মরে গেছে, তাই L95-এর else branch (একমাত্র যেটা <code>UInt16()</code> দিয়ে 0 লেখে) আর চলবে না, ফলে অন্য কিছু <code>/beep</code>-এ না লেখা পর্যন্ত robot থেমে গিয়েও বাজতেই থাকে। folder 12-এর laser_Tracker-এ এই ফাঁকটাই ছিল না — তার ছাড়ার মতো buzzer ছিল না; আর <code>--once</code>-এর কারণে brake-টা one-shot: L81-83-এর Joy_active brake যেখানে প্রতি scan-এ শূন্য publish করে, <code>exit_pro()</code> ঠিক একবারই।"},{"a":133,"b":134,"text":"L133-এর blank line class-এর সীমানা টেনে দেয়; এরপর file-এর প্রথম ও একমাত্র top-level function: <code>def main():</code> — indent নেই, তাই module-এর জিনিস, class-এর নয়। <b>এই file-এর সবচেয়ে বড় কৌতূহল এখানেই</b>: গোটা file-এ কোথাও <code>main()</code>-কে call করা হয় না, আর <code>if __name__ == '__main__':</code> guard-ও নেই — L145-এ এসেই source শেষ, শেষ লাইনটাও <code>main()</code>-এর body-র ভেতরেই। তবু README-র L5 command <code>ros2 run yahboom_M3Pro_laser laser_Warning</code> কাজ করে, কারণ package-এর <code>setup.py</code>-এর console_scripts entry point এই module-কে import করে <code>main()</code>-কে callable হিসেবে ডাকে — ROS 2-র standard কাঠামো (<code>setup.py</code> এই folder-এ নেই, তাই mechanism-টা <i>inferred</i>)।"},{"a":135,"b":137,"text":"Function-এর প্রথম কাজ <code>rclpy.init()</code>: global rclpy context জন্মায় — এর উপরেই পরে প্রতিটা <code>Node</code> দাঁড়াবে, আর Ctrl+C-র signal ধরার ব্যবস্থাও এখান থেকেই আসে; L145-এর <code>rclpy.shutdown()</code> এই জোড়ার দ্বিতীয় প্রান্ত। এরপর <code>laser_warn = laserWarning(\"laser_Warnning_a1\")</code> — L19 থেকে L48 পর্যন্ত পুরো constructor এই এক লাইনের মধ্যে সম্পন্ন: <code>/scan</code> আর <code>/JoyState</code> দুই subscription (L24, L26), <code>/cmd_vel</code> আর <code>/beep</code> দুই publisher (L30, L32), চারটা parameter (L35-42), <code>Joy_active</code> flag আর একটাই <code>SinglePID(3.0, 0.0, 5.0)</code> (L45, L48)। Node-এর নামে source-এর একটা typo লুকিয়ে আছে: <code>laser_Warnning_a1</code> — <b>Warnning</b>-এ দুটো n, source-এ বানানটা যেমন তেমনই আছে; <code>ros2 node list</code>-এ ঠিক এই double-n নামটাই দেখা যাবে, অথচ executable আর file-এর নাম <code>laser_Warning</code> — একটা n। Python class-এর নাম <code>laserWarning</code>, variable-এর নাম <code>laser_warn</code> — চারটা নাম, প্রত্যেকে পৃথক জিনিস, একটা থেকে আরেকটা তৈরি হয় না। <code>print (\"start it\")</code> — print আর বন্ধনীর মাঝে space, L15-এর <code>print (\"improt done\")</code>-এর মতোই author-এর style; Python-এ বৈধ। এই লাইনটা কাজের checkpoint: console-এ \"start it\" দেখলে বুঝবে constructor নিঃশব্দে সফল, এখন merger+filter chain-এর fused <code>/scan</code> এলেই guard-আচরণ শুরু হবে।"},{"a":138,"b":139,"text":"<code>try:</code>-এর ভেতরে <code>rclpy.spin(laser_warn)</code> — পুরো program-এর হৃদপিণ্ড এই এক লাইন। এর আগ পর্যন্ত সব ছিল প্রস্তুতি; <code>spin</code> হলো event loop: main thread এখানেই block হয়ে যায়, আর executor ভেতরে ভেতরে message-এর অপেক্ষা করে — <code>/scan</code>-এ নতুন fused ring এলে <code>registerScan</code> (L54-124), <code>/JoyState</code> এলে <code>JoyStateCallback</code> (L50-52)। অর্থাৎ বিপ-আর-ঘোরার প্রতিটা সিদ্ধান্ত আসলে এই লাইনের ভেতরেই ঘটে চলে; callback-গুলো একটার পর একটা, single-threaded নিয়মে। <code>spin</code> স্বাভাবিক পথে ফেরে না, তাই <code>try</code>-তে মোড়ানো — terminal-এ Ctrl+C চাপলে SIGINT signal আসে, rclpy-র signal handler সেটাকে <code>KeyboardInterrupt</code> exception-এ রূপ দেয়, আর exception ঠিক <code>spin</code>-এর ভেতরে ফাটে।"},{"a":140,"b":145,"text":"<code>except KeyboardInterrupt:</code> সেই exception ধরে <code>pass</code> দিয়ে চুপচাপ গিলে যায় — terminal-এ লম্বা traceback ছাপা হয় না। তারপর <code>finally:</code> — গ্যারান্টি এটাই: <code>try</code> block যেভাবেই শেষ হোক (বাস্তবে এখানে একমাত্র পথটা Ctrl+C), এই block অবশ্যই চলবে। প্রথম কাজ <code>laser_warn.exit_pro()</code> — পাশের comment <code># Force stop the wheels</code> উদ্দেশ্য বলে দিচ্ছে; L127-132-এর পুরো shell brake এই একটা call-এই চলে। এরপর <code>laser_warn.destroy_node()</code>: <code>/cmd_vel</code> আর <code>/beep</code> দুই publisher, দুই subscription, parameter — node-এর সব সরঞ্জাম cleanly ভেঙে DDS-এর দখল ছাড়ে। শেষে <code>rclpy.shutdown()</code>: L135-এর <code>rclpy.init()</code>-এ জন্মানো global context বন্ধ হয়। ক্রম বদলানো চলে না, নিয়ম LIFO: জন্মানোর সময় আগে context, পরে node; বন্ধের সময় আগে node, পরে context — nested bracket বন্ধ করার মতোই। আর L145-ই এই file-এর শেষ লাইন — নিচে আর কিছু নেই, এমনকি trailing newline-ও নেই (তাই <code>wc -l</code> গুনে দেয় 144, সত্যি কথা splitlines-ই বলে: 145)। জন্ম (<code>init</code>), কর্ম (<code>spin</code>), বিদায় (<code>exit_pro</code>, <code>destroy_node</code>, <code>shutdown</code>): একটা guard node-এর পূর্ণ জীবনচক্র — folder 12-এর laser_Tracker-এর মতোই একই ছাঁচে সমাপ্ত, শুধু বিদায়বেলায় buzzer-এর latch-হিসাবটা এই file-এই নতুন।"}],"math":null,"robot":{"correct":"Terminal-এ Ctrl+C চাপলে SIGINT যায়, <code>spin</code>-এর ভেতরে <code>KeyboardInterrupt</code> ওঠে, <code>pass</code> সেটা গিলে যায়, তারপর <code>finally</code> থেকে <code>exit_pro()</code> সম্পূর্ণ আলাদা একটা shell process চালিয়ে <code>/cmd_vel</code>-এ ঠিক একবার সব-শূন্য Twist পাঠায় — শেষ scan Wave D-এর মতো <code>(0.0, -0.417)</code> ডানে ঘোরার command চলছিল থাকলেও চাকা স্পষ্ট থামার আদেশ পেয়ে দাঁড়িয়ে যায় (guard কোনোদিন সামনে যায় না, তাই থামানোর বিষয়টাও শুধু ঘূর্ণনের)। এরপর <code>destroy_node()</code> দুই publisher-দুই subscription ছাড়ে, <code>rclpy.shutdown()</code> context বন্ধ করে; console-এ কোনো traceback ছাপা হয় না। কিন্তু buzzer-এর হিসাব আলাদা: brake শুধু <code>/cmd_vel</code> ছোঁয় — Wave C বা D-এর মতো alarm চলাকালে বিপ ON ছিল, আর node মরে যাওয়ায় L95-এর else branch আর চলবে না, তাই robot থেমে গিয়েও <code>/beep</code> তার শেষ মানেই ধরে রাখে, অন্য কিছু সেই topic-এ না লেখা পর্যন্ত বাজতেই থাকে। Lidar-এর merger+filter chain (README L3-এর launch) আলাদা process — সে চলতেই থাকে; বন্ধ হয় শুধু এই guard node-টা।","incorrect":"বিপজ্জনক ভুল ধারণা: node মারলেই সব থেমে যাবে ভাবা। Terminal-এ <code>kill -9</code> মারলে <code>finally</code> চলেই না — শূন্য-Twist যায় না, আর base তখন শেষ <code>/cmd_vel</code> command ধরে রাখে: Wave D-এর <code>-0.417</code> rad/s ডানে ঘোরা চলতেই থাকে, সঙ্গে alarm-এর বিপও তার শেষ অবস্থাতেই latch হয়ে বাজতে থাকে। আরেকটা ভুল: Ctrl+C চাপলেই বিপ থেমে যাবে ভেবে হাত গুটিয়ে নেওয়া — brake <code>/beep</code>-এ কিছুই লেখে না, তাই robot দাঁড়িয়ে গিয়েও বিপ করতেই থাকে। ফাইলটা সরাসরি <code>python3 laser_Warning.py</code> দিয়ে চালালে আরেক ধরনের নীরবতা: file-এর ভেতরে <code>main()</code> call-এর কোনো লাইন নেই, <code>__main__</code> guard-ও নেই — import-time-এর <code>print (\"improt done\")</code> ছাপার পরেই সব থেমে যায়: কোনো node জন্মায় না, <code>/cmd_vel</code> বা <code>/beep</code>-এ কিছু যায় না, চাকা একবারও নড়ে না; চালাতে হয় README L5-এর <code>ros2 run yahboom_M3Pro_laser laser_Warning</code> দিয়ে। আর <code>ros2 node list</code>-এ <code>laser_Warning_a1</code> খুঁজলে পাওয়া যাবে না — আসল নাম source-এর typo-সহ <code>laser_Warnning_a1</code>, double n।"},"animType":"safetyHalt"}];



/* ---------------- utilities ---------------- */
function escHtml(s) {
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
const pad2 = n => String(n).padStart(2, '0');

/* ---------------- syntax highlighting (presentation-only) --------
   A single-pass scanner over the RAW line that groups characters into
   tokens and only afterwards escapes them. The underlying text is
   never altered — spans are purely cosmetic.                        */
const PY_KW = new Set(['False','None','True','and','as','assert','async','await','break','class','continue','def','del','elif','else','except','finally','for','from','global','if','import','in','is','lambda','nonlocal','not','or','pass','raise','return','try','while','with','yield']);
const PY_BLT = new Set(['print','input','range','float','int','str','len','open','sorted','super','set','list','dict','type','abs','min','max','round','enumerate','isinstance','self']);
const SH_KW = new Set(['if','then','else','elif','fi','for','while','do','done','case','esac','function','export','return','in','local']);
const SH_CMD = new Set(['docker','ros2','gnome-terminal','bash','sh','python3','sleep','source','export','echo','cat','run','launch','pub','topic','start','stop','exec']);
function tokXml(line) {
  const toks = []; const push = (t, c) => { if (t) toks.push({ t: t, c: c }); };
  let i = 0; const n = line.length;
  while (i < n) {
    const c = line[i];
    if (c === '<') {
      let j = i + 1; if (line[j] === '/') j++;
      let k = j; while (k < n && /[A-Za-z0-9_.-]/.test(line[k])) k++;
      if (k > j) { push(line.slice(i, j), ''); push(line.slice(j, k), 'kw'); i = k; continue; }
      push('<', ''); i++; continue;
    }
    if (c === '"' || c === "'") {
      let j = i + 1; while (j < n && line[j] !== c) j++;
      const end = Math.min(j + 1, n); push(line.slice(i, end), 'str'); i = end; continue;
    }
    if (/[0-9]/.test(c) && !(i > 0 && /[A-Za-z0-9_]/.test(line[i - 1]))) {
      let j = i; while (j < n && /[0-9eE+.-]/.test(line[j])) j++;
      push(line.slice(i, j), 'num'); i = j; continue;
    }
    if (/[A-Za-z_]/.test(c)) {
      let j = i; while (j < n && /[A-Za-z0-9_.-]/.test(line[j])) j++;
      let k = j; while (k < n && line[k] === ' ') k++;
      push(line.slice(i, j), line[k] === '=' ? 'blt' : ''); i = j; continue;
    }
    let j = i; while (j < n && !/[<"'.0-9A-Za-z_-]/.test(line[j])) j++;
    if (j === i) j = i + 1;
    push(line.slice(i, j), ''); i = j;
  }
  return toks;
}
function tokYaml(line) {
  const toks = []; const push = (t, c) => { if (t) toks.push({ t: t, c: c }); };
  const hash = line.indexOf('#');
  const head = hash >= 0 ? line.slice(0, hash) : line;
  const m = head.match(/^(\s*(?:-\s+)?)([A-Za-z_][\w.]*)(\s*:\s*)([\s\S]*)$/);
  if (m) {
    push(m[1], ''); push(m[2], 'kw'); push(m[3], '');
    const v = m[4];
    let i = 0; const n = v.length;
    while (i < n) {
      const c = v[i];
      if (c === '"' || c === "'") {
        let j = i + 1; while (j < n && v[j] !== c) j++;
        const end = Math.min(j + 1, n); push(v.slice(i, end), 'str'); i = end; continue;
      }
      if (/[0-9]/.test(c) && !(i > 0 && /[A-Za-z0-9_]/.test(v[i - 1]))) {
        let j = i; while (j < n && /[0-9eE+.-]/.test(v[j])) j++;
        push(v.slice(i, j), 'num'); i = j; continue;
      }
      if (/[A-Za-z_]/.test(c)) {
        let j = i; while (j < n && /[A-Za-z0-9_/.-]/.test(v[j])) j++;
        const w = v.slice(i, j);
        push(w, (w === 'true' || w === 'false') ? 'kw' : ''); i = j; continue;
      }
      let j = i; while (j < n && !/[["'.0-9A-Za-z_-]/.test(v[j])) j++;
      if (j === i) j = i + 1;
      push(v.slice(i, j), ''); i = j;
    }
  } else {
    push(head, '');
  }
  if (hash >= 0) push(line.slice(hash), 'com');
  return toks;
}

function tokenizeLine(line, lang) {
  if (lang === 'text') return line === '' ? [] : [{ t: line, c: '' }];
  if (lang === 'xml') return tokXml(line);
  if (lang === 'yaml') return tokYaml(line);
  const toks = [];
  const push = (t, c) => { if (t) toks.push({ t: t, c: c }); };
  let i = 0;
  const n = line.length;
  while (i < n) {
    const c = line[i];
    if (c === '#') { push(line.slice(i), 'com'); break; }
    if (c === '\'' || c === '"') {
      let j = i + 1;
      while (j < n && line[j] !== c) j++;
      const end = Math.min(j + 1, n);
      push(line.slice(i, end), 'str');
      i = end; continue;
    }
    if (/[0-9]/.test(c) && !(i > 0 && /[A-Za-z0-9_]/.test(line[i - 1]))) {
      let j = i;
      while (j < n && /[0-9a-fA-FxXoObB._]/.test(line[j])) j++;
      push(line.slice(i, j), 'num');
      i = j; continue;
    }
    if (/[A-Za-z_]/.test(c)) {
      let j = i;
      while (j < n && /[A-Za-z0-9_]/.test(line[j])) j++;
      const word = line.slice(i, j);
      if (/^[fFrRbBuU]{1,2}$/.test(word) && j < n && (line[j] === '\'' || line[j] === '"')) {
        const q = line[j];
        let k = j + 1;
        while (k < n && line[k] !== q) k++;
        const end = Math.min(k + 1, n);
        push(line.slice(i, end), 'str');
        i = end; continue;
      }
      let cls = '';
      const KW = lang === 'python' ? PY_KW : SH_KW;
      const BLT = lang === 'python' ? PY_BLT : SH_CMD;
      if (KW.has(word)) cls = 'kw';
      else if (BLT.has(word)) cls = 'blt';
      else if (lang === 'python' && j < n && line[j] === '(') cls = 'fn';
      push(word, cls);
      i = j; continue;
    }
    let j = i;
    while (j < n && !/[#'"0-9A-Za-z_]/.test(line[j])) j++;
    if (j === i) j = i + 1;
    push(line.slice(i, j), '');
    i = j;
  }
  return toks;
}
function hl(line, lang, com) {
  if (line === '') return '';
  if (com) return '<span class="tok-com">' + escHtml(line) + '</span>';
  return tokenizeLine(line, lang).map(t =>
    t.c ? '<span class="tok-' + t.c + '">' + escHtml(t.t) + '</span>' : escHtml(t.t)
  ).join('');
}
function rawLines(fname, a, b) {
  return FILEDATA[fname].slice(a - 1, b);
}

/* ---------------- sidebar ---------------- */
function renderSidebar() {
  const total = PARTS.length;
  const files = Object.keys(FILEDATA).length;
  document.getElementById('sb-meta').textContent = files + ' files · ' + total + ' Parts';
  const nav = document.getElementById('sb-nav');
  nav.innerHTML = PARTS.map(p =>
    '<a class="sb-item" href="#' + p.id + '" data-target="' + p.id + '">' +
      '<span class="sb-num">' + pad2(p.n) + '</span>' +
      '<span class="sb-name">' + escHtml(p.enTitle) + '</span>' +
    '</a>'
  ).join('');
}

/* ---------------- part sections ---------------- */
function codeCard(p) {
  const lines = rawLines(p.fname, p.start, p.end);
  const comSet = (p.lang === 'xml' && XML_COM[p.fname]) || null;
  const rows = lines.map((ln, i) => {
    const no = p.start + i;
    return '<div class="cl"><span class="cln">' + no + '</span><span class="clc">' + hl(ln, p.lang, comSet && comSet.has(no)) + '</span></div>';
  }).join('');
  const raw = lines.join('\n');
  return '' +
  '<div class="code-card" data-copy-src="' + p.id + '">' +
    '<div class="code-card-head">' +
      '<span class="dots"><i></i><i></i><i></i></span>' +
      '<span class="code-fname">' + escHtml(p.fname) + '</span>' +
      '<button class="copy-btn" data-copy="' + p.id + '">Copy</button>' +
      '<span class="code-lines-chip">L' + p.start + (p.end > p.start ? '–' + p.end : '') + '</span>' +
    '</div>' +
    '<div class="code-scroll"><pre class="code"><code>' + rows + '</code></pre></div>' +
  '</div>';
}

function explainBlock(p) {
  if (!p.explain || !p.explain.length) return '';
  const entries = p.explain.map(e => {
    const snippetLines = rawLines(p.fname, e.a, e.b);
    const rendered = snippetLines.map(ln => hl(ln, p.lang)).join('\n');
    const label = e.a === e.b ? ('L ' + e.a) : ('L ' + e.a + '–' + e.b);
    return '' +
    '<div class="ex-entry">' +
      '<div class="ex-snippet"><span class="ex-lines">' + label + '</span>' +
        '<pre>' + rendered + '</pre></div>' +
      '<div class="ex-arrow">↓</div>' +
      '<div class="ex-text bn">' + e.text + '</div>' +
    '</div>';
  }).join('');
  return '' +
  '<div class="sec sec-ex">' +
    '<div class="sec-head"><span class="badge badge-ex">EX</span><h3>Line-by-Line Explanation</h3></div>' +
    '<div class="sec-body">' + entries + '</div>' +
  '</div>';
}

function mathBlock(p) {
  const m = p.math;
  if (!m) return '';
  const levels = (m.levels || []).map(v =>
    '<div class="math-level">' +
      '<div class="ml-label">' + v.label + '</div>' +
      '<div class="mathy">' + v.latex + '</div>' +
      '<div class="ml-text bn">' + v.text + '</div>' +
    '</div>'
  ).join('');
  const numeric = (m.numeric || []).map(v =>
    '<div class="math-level">' +
      '<div class="mathy">' + v.latex + '</div>' +
      '<div class="ml-text bn">' + v.text + '</div>' +
    '</div>'
  ).join('');
  const mapping = (m.mapping || []).map(v =>
    '<div class="map-row">' +
      '<div class="map-code"><code>' + escHtml(v.code) + '</code></div>' +
      '<div class="map-math mathy">' + v.math + '</div>' +
      '<div class="map-text bn">' + v.text + '</div>' +
    '</div>'
  ).join('');
  const failure = (m.failure || []).map(v => '<li>' + v + '</li>').join('');
  let html = '<div class="sec sec-math">' +
    '<div class="sec-head"><span class="badge badge-math">Σ</span><h3>Math Behind This Code</h3></div>' +
    '<div class="sec-body">';
  if (m.intro) html += '<div class="math-intro bn">' + m.intro + '</div>';
  if (levels) html += levels;
  if (numeric) html += '<div class="math-subhead">Numerical Example — ধাপে ধাপে হিসাব</div>' + numeric;
  if (mapping) html += '<div class="math-subhead">Code → Math Mapping</div>' + mapping;
  if (failure) html += '<div class="math-subhead">Failure Intuition — ভুল হলে কী হবে</div><ul class="failure-list">' + failure + '</ul>';
  html += '</div></div>';
  return html;
}

function robotBlock(p) {
  if (!p.robot) return '';
  return '' +
  '<div class="sec sec-rb">' +
    '<div class="sec-head"><span class="badge badge-rb">RB</span><h3><span class="bn-inline">Real Robot/System এই code অনুযায়ী কী করবে</span></h3></div>' +
    '<div class="sec-body"><div class="rb-grid">' +
      '<div class="rb-card rb-ok"><h4>Correct behavior</h4><div class="bn">' + p.robot.correct + '</div></div>' +
      '<div class="rb-card rb-bad"><h4>Incorrect behavior</h4><div class="bn">' + p.robot.incorrect + '</div></div>' +
    '</div></div>' +
  '</div>';
}

function animBlock(p) {
  if (!p.animType) return '';
  return '' +
  '<div class="sec sec-anim" id="anim-' + p.id + '">' +
    '<div class="sec-head"><span class="badge badge-anim">AN</span><h3>Interactive Animation</h3></div>' +
    '<div class="anim-stage" id="stage-' + p.id + '"></div>' +
    '<div class="anim-controls">' +
      '<button class="ac-btn" data-ac="play">Play</button>' +
      '<button class="ac-btn" data-ac="slow">Slow</button>' +
      '<button class="ac-btn" data-ac="fast">Fast</button>' +
      '<button class="ac-btn" data-ac="pause">Pause</button>' +
      '<button class="ac-btn" data-ac="stop">Stop</button>' +
      '<span class="anim-state" id="state-' + p.id + '">IDLE</span>' +
    '</div>' +
    '<div class="anim-caption bn" id="cap-' + p.id + '">Play চাপলে animation শুরু হবে।</div>' +
    '<div class="anim-formula" id="fx-' + p.id + '"></div>' +
  '</div>';
}

function partNav(p) {
  const prev = p.n > 1 ? PARTS[p.n - 2] : null;
  const next = p.n < PARTS.length ? PARTS[p.n] : null;
  const btn = (t, cls) => !t
    ? '<span class="pn-btn disabled"><span class="pn-dir">' + cls + '</span><span class="pn-title">—</span></span>'
    : '<a class="pn-btn ' + cls + '" href="#' + t.id + '"><span class="pn-dir">' +
      (cls === 'next' ? 'Next →' : '← Previous') + '</span><span class="pn-title">' +
      pad2(t.n) + ' · ' + escHtml(t.enTitle) + '</span></a>';
  return '<div class="part-nav">' + btn(prev, 'prev') + btn(next, 'next') + '</div>';
}

function partSection(p) {
  const flags = (p.flags || []).map(f => '<span class="meta-chip flag">' + escHtml(f) + '</span>').join('');
  return '' +
  '<section class="part" id="' + p.id + '">' +
    '<header class="part-head">' +
      '<div class="eyebrow">PART ' + pad2(p.n) + ' / ' + pad2(PARTS.length) + ' · ' + escHtml(p.fname) + '</div>' +
      '<h2 class="part-title">' + escHtml(p.enTitle) + '</h2>' +
      '<div class="part-meta">' +
        '<span class="meta-chip">L' + p.start + (p.end > p.start ? '–' + p.end : '') + '</span>' +
        '<span class="meta-chip lang">' + p.lang + '</span>' + flags +
      '</div>' +
    '</header>' +
    codeCard(p) +
    explainBlock(p) +
    mathBlock(p) +
    robotBlock(p) +
    animBlock(p) +
    partNav(p) +
  '</section>';
}

function introBanner() {
  return '' +
  '<div class="intro-banner">' +
    '<div class="intro-eyebrow">NeuroBotics · Interactive Code Analysis</div>' +
    '<h1>13. lidar guard <span class="path">— fused 360 scan-এর সামনের cone-এর সবচেয়ে কাছের object-এর দিকে ঘুরে 0.55 m Danger Zone-এ ঢুকলেই /beep-এ সাইরেন — নিজ জায়গায় দাঁড়িয়ে spin-only পাহারা</span></h1>' +
    '<div class="intro-desc bn">এই application-টি <code>13. lidar guard</code> folder-এর তিনটি source file — <code>README.md</code> (তিন command-এর runbook), <code>laser_driver.launch.py</code> (folder 10-এর merger আর filter launch file দুটিকে এক সঙ্গে চালানোর orchestrator) আর <code>laser_Warning.py</code> (fused scan-এর সামনের cone থেকে সবচেয়ে কাছের object ধরে single PID-এ <code>/cmd_vel</code>-এ spin কমান্ড আর <code>/beep</code>-এ Danger Zone সাইরেন দেওয়া guard node) — কে কেন্দ্র করে তৈরি। ভেতরে আছে <code>IncludeLaunchDescription</code> দিয়ে chained launch, subscription-publisher graph, declare/get parameter জোড়া, প্রতিটি beam-এর angle math ও front-cone inequality, alarm threshold-এর level-signal আচরণ ও latch, single PID-এর target-current হিসাব, আর turn deadzone- damping-এর ধাপে ধাপে বিশ্লেষণ। প্রতিটি Part-এ আছে original code card, line-by-line Bangla explanation, Math derivation, Real Robot behavior এবং interactive animation।</div>' +
    '<div class="intro-stats">' +
      '<span class="stat-chip"><b>' + Object.keys(FILEDATA).length + '</b> files</span>' +
      '<span class="stat-chip"><b>' + PARTS.length + '</b> Parts</span>' +
      '<span class="stat-chip"><b>' + PARTS.reduce((s, p) => s + (p.explain ? p.explain.length : 0), 0) + '</b> explained blocks</span>' +
      '<span class="stat-chip"><b>' + PARTS.filter(p => p.animType).length + '</b> animations</span>' +
    '</div>' +
  '</div>';
}

function renderParts() {
  document.getElementById('main').innerHTML = introBanner() + PARTS.map(partSection).join('');
  document.getElementById('site-footer').textContent =
    '13. lidar guard · line-by-line analysis · source preserved verbatim from /home/shariful/NeuroBotics/13. lidar guard';
}

/* ---------------- copy buttons (code without line numbers) -------- */
const RAW_CODE = {};
function setupCopy() {
  PARTS.forEach(p => { RAW_CODE[p.id] = rawLines(p.fname, p.start, p.end).join('\n'); });
  document.addEventListener('click', ev => {
    const b = ev.target.closest('.copy-btn');
    if (!b) return;
    const txt = RAW_CODE[b.dataset.copy];
    const done = () => {
      b.textContent = 'Copied';
      b.classList.add('done');
      setTimeout(() => { b.textContent = 'Copy'; b.classList.remove('done'); }, 1600);
    };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(txt).then(done).catch(() => fallbackCopy(txt, done));
    } else fallbackCopy(txt, done);
  });
}
function fallbackCopy(txt, done) {
  const ta = document.createElement('textarea');
  ta.value = txt;
  ta.style.position = 'fixed'; ta.style.opacity = '0';
  document.body.appendChild(ta);
  ta.select();
  try { document.execCommand('copy'); done(); } catch (e) { /* noop */ }
  document.body.removeChild(ta);
}

/* ---------------- navigation & active state ---------------- */
function setupNavigation() {
  const items = Array.from(document.querySelectorAll('.sb-item'));
  const setActive = id => {
    items.forEach(it => it.classList.toggle('active', it.dataset.target === id));
  };
  const io = new IntersectionObserver(entries => {
    entries.forEach(en => {
      if (en.isIntersecting) setActive(en.target.id);
    });
  }, { rootMargin: '-15% 0px -75% 0px', threshold: 0 });
  PARTS.forEach(p => {
    const el = document.getElementById(p.id);
    if (el) io.observe(el);
  });
  document.querySelectorAll('.sb-item').forEach(it => {
    it.addEventListener('click', () => document.body.classList.remove('sb-open'));
  });
  document.getElementById('menu-btn').addEventListener('click', () =>
    document.body.classList.toggle('sb-open'));
  document.getElementById('sb-overlay').addEventListener('click', () =>
    document.body.classList.remove('sb-open'));
}

/* ---------------- MathJax: typeset + graceful fallback ----------- */
function mathFallback() {
  if (window.MathJax && window.MathJax.startup && window.MathJax.startup.document) return;
  document.body.classList.add('no-mathjax');
  document.querySelectorAll('.mathy').forEach(el => {
    let t = el.textContent;
    t = t.replace(/\\\[/g, '').replace(/\\\]/g, '').replace(/\\\(/g, '').replace(/\\\)/g, '');
    el.textContent = t;
  });
}
function setupMathJaxWatchdog() {
  window.__mathFailed = false;
  const s = document.getElementById('Mathjax-script');
  if (s) s.addEventListener('error', () => { window.__mathFailed = true; });
  let tries = 0;
  const timer = setInterval(() => {
    tries++;
    if (window.MathJax && window.MathJax.startup && window.MathJax.startup.document) {
      clearInterval(timer);
    } else if (window.__mathFailed || tries > 40) {
      clearInterval(timer);
      mathFallback();
    }
  }, 150);
}

/* ================================================================
   ANIMATION SYSTEM
   Engine: cancellable, speed-scaled, pause-aware rAF scheduler.
   Every animation renders inline SVG, updates a live Bangla caption
   and a live formula bar. No animation libraries are used.
   ================================================================ */

const easeInOutCubic = t => t < .5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
const easeOutCubic = t => 1 - Math.pow(1 - t, 3);
const easeOutBounce = t => {
  const n1 = 7.5625, d1 = 2.75;
  if (t < 1 / d1) return n1 * t * t;
  if (t < 2 / d1) return n1 * (t -= 1.5 / d1) * t + .75;
  if (t < 2.5 / d1) return n1 * (t -= 2.25 / d1) * t + .9375;
  return n1 * (t -= 2.625 / d1) * t + .984375;
};
const fmt = (v, d) => Number(v).toFixed(d === undefined ? 3 : d);

/* ---------------- small SVG string helpers ---------------- */
function rrect(x, y, w, h, rx, fill, stroke, extra) {
  return '<rect x="' + x + '" y="' + y + '" width="' + w + '" height="' + h +
    '" rx="' + (rx === undefined ? 8 : rx) + '" fill="' + fill + '"' +
    (stroke ? ' stroke="' + stroke + '" stroke-width="1"' : '') +
    (extra || '') + '/>';
}
function txt(x, y, s, o) {
  o = o || {};
  return '<text' + (o.id ? ' id="' + o.id + '"' : '') + ' x="' + x + '" y="' + y + '" fill="' + (o.fill || '#c9d1d9') +
    '" font-size="' + (o.size || 13) + '"' +
    ' font-family="' + (o.mono ? "'JetBrains Mono',monospace" : "'Hind Siliguri','Inter',sans-serif") + '"' +
    (o.anchor ? ' text-anchor="' + o.anchor + '"' : '') +
    (o.weight ? ' font-weight="' + o.weight + '"' : '') +
    (o.op !== undefined ? ' opacity="' + o.op + '"' : '') + '>' + s + '</text>';
}
function line(x1, y1, x2, y2, stroke, w, extra) {
  return '<line x1="' + x1 + '" y1="' + y1 + '" x2="' + x2 + '" y2="' + y2 +
    '" stroke="' + stroke + '" stroke-width="' + (w || 1.5) + '"' +
    (extra || '') + '/>';
}
function circ(x, y, r, fill, extra) {
  return '<circle cx="' + x + '" cy="' + y + '" r="' + r + '" fill="' + fill + '"' + (extra || '') + '/>';
}
function arrow(x1, y1, x2, y2, color, marker, w) {
  return '<line x1="' + x1 + '" y1="' + y1 + '" x2="' + x2 + '" y2="' + y2 +
    '" stroke="' + color + '" stroke-width="' + (w || 2) +
    '" marker-end="url(#' + marker + ')"' + '/>';
}
function path(d, stroke, w, extra) {
  return '<path d="' + d + '" fill="none" stroke="' + stroke + '" stroke-width="' + (w || 2) + '" stroke-linecap="round" stroke-linejoin="round"' + (extra || '') + '/>';
}

/* ---------------- host ---------------- */
function createAnimHost(part) {
  const id = part.id;
  const host = {
    part: part,
    stageEl: document.getElementById('stage-' + id),
    capEl: document.getElementById('cap-' + id),
    fxEl: document.getElementById('fx-' + id),
    stateEl: document.getElementById('state-' + id),
    secEl: document.getElementById('anim-' + id),
    speed: 1, running: false, stopFlag: false, started: false,
    staticOnly: false, inView: false, autoPaused: false, userPaused: false,
    _raf: null
  };
  host.setStage = function (inner, w, h) {
    host.stageEl.innerHTML = '<svg viewBox="0 0 ' + (w || 900) + ' ' + (h || 460) +
      '" preserveAspectRatio="xMidYMid meet" role="img">' + inner + '</svg>';
    return host.stageEl.querySelector('svg');
  };
  host.caption = t => { host.capEl.innerHTML = t; };
  host.formula = t => { host.fxEl.innerHTML = t; };
  host.setState = t => { host.stateEl.textContent = t; };
  host._sched = function (dur, onFrame) {
    return new Promise((res, rej) => {
      let elapsed = 0, last = null;
      const step = t => {
        if (host.stopFlag) { rej(new Error('anim-stopped')); return; }
        if (!host.running) { last = null; host._raf = requestAnimationFrame(step); return; }
        if (last === null) last = t;
        elapsed += t - last; last = t;
        const k = Math.min(1, elapsed / (dur / host.speed));
        try { onFrame(k, elapsed); } catch (e) { rej(e); return; }
        if (k >= 1) { res(); return; }
        host._raf = requestAnimationFrame(step);
      };
      host._raf = requestAnimationFrame(step);
    });
  };
  host.sleep = ms => host._sched(ms, () => {});
  host.tween = (dur, fn) => host._sched(dur, k => fn(k));
  host.start = function (speed) {
    if (speed) host.speed = speed;
    if (host.started) { host.stopFlag = true; }
    host.started = true; host.stopFlag = false; host.running = true; host.userPaused = false;
    host.setState('RUN ' + host.speed + 'x');
    setTimeout(() => {
      ANIMS[part.animType](host).catch(e => {
        if (e && e.message === 'anim-stopped') host.setState('STOPPED');
        else console.error('anim error', part.id, e);
      });
    }, 30);
  };
  host.pause = function () {
    if (!host.started) return;
    host.running = false; host.userPaused = true;
    host.setState('PAUSED');
  };
  host.resume = function () {
    if (!host.started || !host.userPaused) return;
    host.running = true; host.userPaused = false;
    host.setState('RUN ' + host.speed + 'x');
  };
  host.stop = function () {
    host.stopFlag = true; host.running = false; host.started = false; host.userPaused = false;
    if (host._raf) cancelAnimationFrame(host._raf);
    host.setState('IDLE');
    host.renderStatic();
  };
  host.renderStatic = function () {
    host.staticOnly = true;
    try { ANIMS[part.animType](host); } catch (e) { /* static render is best-effort */ }
    host.staticOnly = false;
  };
  host.setSpeed = function (s) {
    host.speed = s;
    if (!host.started) { host.start(s); return; }
    if (host.userPaused) { host.running = true; host.userPaused = false; }
    host.setState('RUN ' + s + 'x');
  };
  /* controls */
  host.secEl.querySelectorAll('.ac-btn').forEach(b => {
    b.addEventListener('click', () => {
      const a = b.dataset.ac;
      host.secEl.querySelectorAll('.ac-btn').forEach(x => x.classList.remove('active'));
      b.classList.add('active');
      if (a === 'play') host.userPaused ? host.resume() : host.start(1);
      else if (a === 'slow') host.setSpeed(0.5);
      else if (a === 'fast') host.setSpeed(1.5);
      else if (a === 'pause') host.pause();
      else if (a === 'stop') { host.stop(); b.classList.remove('active'); }
    });
  });
  /* auto start / auto pause with visibility */
  const io = new IntersectionObserver(entries => {
    entries.forEach(en => {
      host.inView = en.isIntersecting;
      if (en.isIntersecting) {
        if (host.autoPaused && host.started) {
          host.running = true; host.autoPaused = false; host.setState('RUN ' + host.speed + 'x');
        } else if (!host.started && !host.autoStarted && !window.__prefersReducedMotion) {
          host.autoStarted = true; host.start(1);
        }
      } else if (host.started && host.running) {
        host.running = false; host.autoPaused = true; host.setState('HOLD');
      }
    });
  }, { threshold: 0.25 });
  io.observe(host.secEl);
  return host;
}

const ANIMS = {};
const HOSTS = {};

function setupAnimations() {
  window.__prefersReducedMotion = window.matchMedia &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  PARTS.forEach(p => {
    if (p.animType && ANIMS[p.animType]) {
      HOSTS[p.id] = createAnimHost(p);
      HOSTS[p.id].renderStatic();
    }
  });
}

/* ================= folder-13 anims (v1 layer, 8 total) ================
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
   caption + formula set before the first await. */


/* ---------- runbookFlow ---------- */
/* ============ folder-13 anim — runbookFlow (part 1, v1 layer) ============
   README.md L1-L5 (5 lines, 3 nonblank): L1 sh start_agent.sh, L3 ros2
   launch yahboom_M3Pro_laser laser_driver.launch.py, L5 ros2 run
   yahboom_M3Pro_laser laser_Warning; L2/L4 blank-line pauses. L1 is the
   first line of folders 10/11/12 READMEs too; L3 matches folders 11/12
   only (folder 10 launched ira_laser_tools merge_multi.launch.py
   directly, no laser_driver). laser_driver.launch.py L8
   generate_launch_description(), L28-42 list, IncludeLaunchDescription
   #1 (L32, ira_laser_tools merge_multi.launch.py, folder 10) + #2 (L38,
   yahboom_laser_filter laser_filter_node.launch.py) — byte-identical
   driver to folders 11 AND 12 (sha256[:12] dadf5ff3f9b1, verified on
   disk). laser_Warning.py: sub /scan L24 + /JoyState L26, pub /cmd_vel
   L30 + /beep L32 (UInt16, the guard's own buzzer channel), node name
   laser_Warnning_a1 L136 (double-n typo IN SOURCE, kept verbatim),
   Joy_active gate L81-83; downstream semantics = GUARD the nearest
   front-cone object: /beep 1 once it is inside ResponseDist 0.55 m
   (declare L41, alarm test L89), spin in place to keep facing it —
   angular only, linear.x never set (L123), never drives forward
   (folder 12 followed, folder 11 avoided). Ring and raw topic names
   illustrative.
   Unique id prefix rf- ; helper prefixed rfDots ; no emoji ; no arrow
   chars in stage text (entities or words instead) ; first caption +
   formula before the first await ; static backbone at setStage. */


/* full-circle dot ring (fused /scan view); deg step controls density */
function rfDots(cx, cy, r, step, idp, fill) {
  let d = '';
  for (let i = 0; i < 360; i += step) {
    const a = i * Math.PI / 180;
    const x = cx + r * Math.sin(a);
    const y = cy - r * Math.cos(a);
    d += 'M' + x.toFixed(1) + ' ' + y.toFixed(1) + 'h2.2v2.2h-2.2z';
  }
  return '<path id="' + idp + '" d="' + d + '" fill="' + fill + '" opacity="0"/>';
}

/* ---------- runbookFlow ---------- */
ANIMS.runbookFlow = async function (host) {
  const svg = host.setStage(
    txt(450, 26, 'README-র ৩টা command-ই এক runbook — bringup, launch chain, guard node', { anchor: 'middle', size: 14.5, weight: 600, fill: '#ffb454' }) +
    rrect(40, 44, 370, 316, 8, '#0d1117', '#2a3442') +
    txt(56, 64, 'TERMINAL — README L1-L5 (3 command + 2 blank)', { size: 10, weight: 700, fill: '#e6edf3' }) +
    rrect(56, 74, 336, 40, 5, '#161b22', '#30363d', ' id="rf-c1"') +
    txt(66, 91, '$ sh start_agent.sh', { size: 9.5, mono: true, weight: 700, fill: '#7ee787' }) +
    txt(384, 99, 'L1', { anchor: 'end', size: 8, mono: true, fill: '#6e7681' }) +
    txt(66, 104, 'vendor bringup (illustrative)', { size: 7.5, fill: '#8b949e', id: 'rf-c1s', op: 0 }) +
    txt(224, 129, '— L2: blank line, ধাপের pause —', { anchor: 'middle', size: 7, mono: true, fill: '#6e7681' }) +
    rrect(56, 136, 336, 52, 5, '#161b22', '#30363d', ' id="rf-c2"') +
    txt(66, 153, '$ ros2 launch yahboom_M3Pro_laser', { size: 9.5, mono: true, weight: 700, fill: '#ffb454' }) +
    txt(66, 167, '  laser_driver.launch.py', { size: 9.5, mono: true, weight: 700, fill: '#ffb454' }) +
    txt(384, 157, 'L3', { anchor: 'end', size: 8, mono: true, fill: '#6e7681' }) +
    txt(66, 181, 'এক launch file আরও দুই launch file চালায় (L32, L38)', { size: 7.5, fill: '#8b949e', id: 'rf-c2s', op: 0 }) +
    txt(224, 201, '— L4: blank line, ধাপের pause —', { anchor: 'middle', size: 7, mono: true, fill: '#6e7681' }) +
    rrect(56, 210, 336, 52, 5, '#161b22', '#30363d', ' id="rf-c3"') +
    txt(66, 227, '$ ros2 run yahboom_M3Pro_laser', { size: 9.5, mono: true, weight: 700, fill: '#4fc3f7' }) +
    txt(66, 241, '  laser_Warning', { size: 9.5, mono: true, weight: 700, fill: '#4fc3f7' }) +
    txt(384, 231, 'L5', { anchor: 'end', size: 8, mono: true, fill: '#6e7681' }) +
    txt(66, 255, 'launch file ছাড়া সরাসরি guard executable', { size: 7.5, fill: '#8b949e', id: 'rf-c3s', op: 0 }) +
    txt(56, 278, 'ros2 launch বনাম ros2 run', { size: 8.5, weight: 700, fill: '#e6edf3' }) +
    txt(56, 296, 'L3 = ros2 launch — launch file-এর action তালিকা চালায়', { size: 8, fill: '#8b949e', id: 'rf-d1', op: 0 }) +
    txt(56, 312, 'L5 = ros2 run — সরাসরি একটা executable তোলে', { size: 8, fill: '#8b949e', id: 'rf-d2', op: 0 }) +
    txt(56, 331, 'L1 folder 10-12-এর README-ও হুবহু, L3 folder 11-12-এর মতোই', { size: 8, fill: '#c9d1d9', id: 'rf-d3', op: 0 }) +
    txt(56, 348, 'দুই-ই এক package: yahboom_M3Pro_laser', { size: 8, mono: true, fill: '#c9d1d9', id: 'rf-d4', op: 0 }) +
    rrect(428, 44, 432, 316, 8, '#111', '#30363d') +
    txt(644, 64, 'SYSTEM — ধাপে ধাপে যা জন্মায়', { anchor: 'middle', size: 10, weight: 700, fill: '#e6edf3' }) +
    rrect(444, 74, 192, 28, 5, '#161b22', '#7ee787', ' id="rf-drvF" opacity="0"') +
    txt(452, 92, 'front lidar driver', { size: 8.5, mono: true, weight: 700, fill: '#7ee787', id: 'rf-drvFt', op: 0 }) +
    rrect(652, 74, 192, 28, 5, '#161b22', '#7ee787', ' id="rf-drvR" opacity="0"') +
    txt(660, 92, 'rear lidar driver', { size: 8.5, mono: true, weight: 700, fill: '#7ee787', id: 'rf-drvRt', op: 0 }) +
    path('M452 112h176', '#7ee787', 1.4, ' id="rf-flowF" opacity="0" stroke-dasharray="4 4"') +
    path('M660 112h176', '#7ee787', 1.4, ' id="rf-flowR" opacity="0" stroke-dasharray="4 4"') +
    txt(452, 126, 'raw scan topic #1 (নাম illustrative)', { size: 7.5, fill: '#8b949e', id: 'rf-rawF', op: 0 }) +
    txt(660, 126, 'raw scan topic #2 (নাম illustrative)', { size: 7.5, fill: '#8b949e', id: 'rf-rawR', op: 0 }) +
    rrect(444, 136, 400, 24, 5, '#161b22', '#e3b341', ' id="rf-ldf" opacity="0"') +
    txt(452, 152, 'laser_driver.launch.py — generate_launch_description() L8', { size: 8, mono: true, weight: 700, fill: '#e3b341', id: 'rf-ldft', op: 0 }) +
    rrect(444, 168, 196, 44, 5, '#161b22', '#30363d', ' id="rf-inc1" opacity="0"') +
    txt(452, 183, 'IncludeLaunchDescription #1 (L32)', { size: 7, fill: '#8b949e', id: 'rf-inc1a', op: 0 }) +
    txt(452, 196, 'ira_laser_tools', { size: 8, mono: true, weight: 700, fill: '#ffb454', id: 'rf-inc1b', op: 0 }) +
    txt(452, 207, 'merge_multi.launch.py (folder 10)', { size: 7, mono: true, fill: '#ffb454', id: 'rf-inc1c', op: 0 }) +
    rrect(652, 168, 192, 44, 5, '#161b22', '#30363d', ' id="rf-inc2" opacity="0"') +
    txt(660, 183, 'IncludeLaunchDescription #2 (L38)', { size: 7, fill: '#8b949e', id: 'rf-inc2a', op: 0 }) +
    txt(660, 196, 'yahboom_laser_filter', { size: 8, mono: true, weight: 700, fill: '#d2a8ff', id: 'rf-inc2b', op: 0 }) +
    txt(660, 207, 'laser_filter_node.launch.py', { size: 7, mono: true, fill: '#d2a8ff', id: 'rf-inc2c', op: 0 }) +
    rrect(444, 218, 152, 30, 5, '#161b22', '#ffb454', ' id="rf-merg" opacity="0"') +
    txt(520, 237, 'laserscan_multi_merger', { anchor: 'middle', size: 7.5, mono: true, weight: 700, fill: '#ffb454', id: 'rf-mergt', op: 0 }) +
    path('M596 233h14', '#8b949e', 1.3, ' id="rf-lnk1" opacity="0"') +
    rrect(610, 218, 150, 30, 5, '#161b22', '#d2a8ff', ' id="rf-filt" opacity="0"') +
    txt(685, 237, 'laser_filter_node', { anchor: 'middle', size: 7.5, mono: true, weight: 700, fill: '#d2a8ff', id: 'rf-filtt', op: 0 }) +
    path('M760 233h14', '#8b949e', 1.3, ' id="rf-lnk2" opacity="0"') +
    rfDots(800, 233, 21, 15, 'rf-ring', '#7ee787') +
    txt(800, 268, '/scan', { anchor: 'middle', size: 8, mono: true, weight: 700, fill: '#7ee787', id: 'rf-scan', op: 0 }) +
    rrect(444, 278, 400, 24, 5, '#161b22', '#4fc3f7', ' id="rf-proc" opacity="0"') +
    txt(452, 294, 'guard process: laser_Warning — node laser_Warnning_a1 (L136)', { size: 7.5, mono: true, weight: 700, fill: '#4fc3f7', id: 'rf-proct', op: 0 }) +
    txt(452, 312, 'sub: /scan + /JoyState (L24, L26)', { size: 8, mono: true, fill: '#4fc3f7', id: 'rf-sub', op: 0 }) +
    txt(452, 326, 'pub: /cmd_vel (L30) -&gt; wheels + /beep (L32) buzzer', { size: 8, mono: true, fill: '#ff7b72', id: 'rf-pub', op: 0 }) +
    rrect(444, 336, 400, 22, 5, '#161b22', '#30363d', ' id="rf-gbox" opacity="0"') +
    txt(452, 351, 'front+rear raw -&gt; merger -&gt; filter -&gt; /scan -&gt; laser_Warning -&gt; /cmd_vel + /beep', { size: 7.5, mono: true, weight: 700, fill: '#e3b341', id: 'rf-gtxt', op: 0 }) +
    txt(450, 386, 'রঙ-নিয়ম: সবুজ = driver ও raw, হলুদ = launch ও merger, বেগুনি = filter, নীল = guard, লাল = /cmd_vel ও /beep', { anchor: 'middle', size: 8.5, fill: '#8b949e' }) +
    txt(450, 440, 'source: README.md L1-L5 + laser_driver.launch.py L8-L42 + laser_Warning.py L24-L32, L41, L81-83, L89, L123, L136', { anchor: 'middle', size: 8, mono: true, fill: '#6e7681' })
  );
  const q = id => svg.querySelector('#' + id);
  const show = id => q(id).setAttribute('opacity', 1);
  const edge = id => q(id).setAttribute('stroke', '#e3b341');
  host.caption('README-র ৩টা command-ই এক runbook: L1 bringup, L3 launch chain, L5 guard node। মাঝের L2/L4 ফাঁকা line — ধাপ দেখে নেওয়ার pause।');
  host.formula('README = 5 lines = 3 commands: L1 sh + L3 ros2 launch + L5 ros2 run');
  await host.sleep(1400);
  edge('rf-c1'); show('rf-c1s'); show('rf-drvF'); show('rf-drvFt'); show('rf-drvR'); show('rf-drvRt');
  show('rf-flowF'); show('rf-flowR'); show('rf-rawF'); show('rf-rawR');
  host.caption('<b>sh start_agent.sh</b> (L1) — vendor bringup (<b>illustrative</b>, script এই folder-এ নেই): front আর rear — দুই lidar-এর driver ওঠে, দুই raw scan topic প্রবাহিত হতে শুরু করে (নাম illustrative)।');
  await host.sleep(1600);
  edge('rf-c2'); show('rf-c2s'); show('rf-ldf'); show('rf-ldft');
  show('rf-inc1'); show('rf-inc1a'); show('rf-inc1b'); show('rf-inc1c');
  show('rf-inc2'); show('rf-inc2a'); show('rf-inc2b'); show('rf-inc2c');
  host.caption('<b>ros2 launch yahboom_M3Pro_laser laser_driver.launch.py</b> (L3) — launch file-টা পড়ে <code>generate_launch_description()</code> (L8) চালায়; তার তালিকায় (L28) ঠিক দুইটা <code>IncludeLaunchDescription</code> action — L32 আর L38।');
  host.formula('ros2 launch pkg file.launch.py -> read file + run its LaunchDescription actions');
  await host.sleep(1700);
  show('rf-merg'); show('rf-mergt'); show('rf-lnk1'); show('rf-filt'); show('rf-filtt'); show('rf-lnk2'); show('rf-ring'); show('rf-scan');
  host.caption('include #1 ওঠায় folder 10-এর <code>laserscan_multi_merger</code>, include #2 ওঠায় <code>laser_filter_node</code> — chain: 2 raw -> merger -> filter -> <code>/scan</code>। এই driver file হুবহু এক চলে folder 11 আর 12-তেও — তিন folder-এই এক sensor chain, বদলায় শুধু যে node <code>/scan</code> পড়বে সেটাই।');
  await host.sleep(1700);
  edge('rf-c3'); show('rf-c3s'); show('rf-proc'); show('rf-proct');
  host.caption('<b>ros2 run yahboom_M3Pro_laser laser_Warning</b> (L5) — এই folder-এর guard process। node-এর নাম <code>laser_Warnning_a1</code> (L136) — source-এই double-n বানান, ঠিক না করে ওইটাই থাকবে। কাজ একটাই: সামনের cone-এর সবচেয়ে কাছের object-কে চোখে রাখা — object ResponseDist 0.55 m-এর ভেতরে এলে <code>/beep</code>-এ 1 যায় (alarm test L89), আর মুখ তার দিকে ঘুরিয়ে রাখতে robot শুধু জায়গায় ঘোরে। folder 12-এর tracker ছিল অনুসরণকারী — এ পাহারাদার, এক পা-ও এগোয় না।');
  host.formula('L5 guard = watch nearest front-cone object: within 0.55 m -> /beep 1; turn to face it');
  await host.sleep(1700);
  show('rf-sub'); show('rf-pub');
  host.caption('channel-হিসেব: subscribe <code>/scan</code> + <code>/JoyState</code> (L24, L26), publish <code>/cmd_vel</code> (L30) আর <code>/beep</code> (L32) — <code>UInt16</code>, মান 1 মানে buzzer ON, 0 মানে OFF। মোড়ার হিসাব শুধু <code>angular.z</code>-এর: <code>linear.x</code> কোথাও সেট-ই হয় না (L123) — তাই সব সময় 0.0, robot জায়গায় ঘুরে ঘুরে পাহারা দেয়।');
  await host.sleep(1700);
  show('rf-d1'); show('rf-d2'); show('rf-d3'); show('rf-d4');
  host.caption('<code>ros2 launch</code> বনাম <code>ros2 run</code>: launch একটা file-এর ভেতরের action-তালিকা চালায় (L3-এ দুইটা include উঠেছিল), run সরাসরি একটা executable তোলে (L5)। আর runbook-টা পুরো series-এর চেনা: L1-এর <code>sh</code> command folder 10, 11 আর 12-এর README-ও হুবহু এই line-ই, L3-এর launch command folder 11 ও 12-এর L3-এর মতোই (ওখানকার driver file-ও byte-হুবহু এক) — বদল শুধু L5: laser_Tracker-এর জায়গায় laser_Warning।');
  host.formula('ros2 launch = actions from a launch file  |  ros2 run = one executable, no file');
  await host.sleep(1700);
  show('rf-gbox'); show('rf-gtxt');
  host.caption('পুরো chain এক line-এ: front+rear raw -> merger -> filter -> /scan -> laser_Warning -> /cmd_vel + /beep। আর <code>/JoyState</code> true হলে মানুষের joystick জিতে যায় (L81-83) — gate-টা alarm block-এর আগেই return করে, তাই চলাকালীন <code>/beep</code>-ও refresh হয় না: শেষ মান latched থাকে।');
  host.formula('folder 10: 2 raw -> merger -> filter -> /scan  |  folder 13: /scan -> laser_Warning -> /cmd_vel + /beep');
  await host.sleep(1700);
  host.caption('৩টা command, ৫টা line — একটাও এলোমেলো নয়: প্রত্যেকটা আগের ধাপের ফলের ওপর দাঁড়িয়েছে। এবার ঢুকব laser_Warning-এর ভেতরে — পরের part-এ cone, alarm আর ঘোরার হিসাব।');
  await host.sleep(1500);
};

/* ---------- includeChain ---------- */
/* ===== folder-13 part 3 — includeChain (prefix ic-) ================
   laser_driver.launch.py L8-L24: constructor builds TWO eager paths via
   os.path.join(get_package_share_directory(pkg), 'launch', file) for
   ira_laser_tools/merge_multi.launch.py (L12-16) and
   yahboom_laser_filter/laser_filter_node.launch.py (L20-24); each then
   wrapped PythonLaunchDescriptionSource -> IncludeLaunchDescription and
   queued for the L28-L42 LaunchDescription return (run = next part).
   Driver BYTE-IDENTICAL to folders 11 AND 12 (sha256[:12] dadf5ff3f9b1,
   verified on disk) — same sensor chain all three times; this folder's
   downstream consumer is the guard laser_Warning, which the driver
   never starts: zero own nodes, the Node import (L6) is unused and its
   own comment admits just-in-case; README L5 does the starting.
   Contrast: plain call = EAGER at constructor time, unlike folder 10's
   lazy LaunchConfiguration. Share-dir prefixes illustrative.
   No emoji, no arrow chars in stage strings, ids all ic-prefixed. */


function icCode(x, y, s, fill) {          /* one mono source line */
  return txt(x, y, s, { size: 8, mono: true, fill: fill });
}
function icLn(y, n) {                     /* right-aligned line tag */
  return txt(388, y, n, { anchor: 'end', size: 7, mono: true, fill: '#6e7681' });
}

ANIMS.includeChain = async function (host) {
  const svg = host.setStage(
    txt(450, 26, 'দুই EAGER path, দুই include — সব ঠিক হয় constructor-এ, run আসে পরে', { anchor: 'middle', size: 14, weight: 600, fill: '#ffb454' }) +
    rrect(40, 44, 368, 274, 8, '#0d1117', '#2a3442') +
    txt(56, 64, 'SOURCE — laser_driver.launch.py (L8-L24)', { size: 10, weight: 700, fill: '#e6edf3' }) +
    rrect(52, 74, 344, 24, 5, '#161b22', '#30363d', ' id="ic-cA"') +
    txt(64, 89, 'def generate_launch_description():', { size: 8.5, mono: true, weight: 700, fill: '#e6edf3' }) +
    icLn(89, 'L8') +
    txt(64, 108, '# --- PROGRAM 1: THE LASER MERGER ---', { size: 7, mono: true, fill: '#6e7681' }) +
    rrect(52, 116, 344, 86, 5, '#161b22', '#30363d', ' id="ic-cB"') +
    icCode(64, 130, 'laser_merge_launch_file = os.path.join(', '#e6edf3') + icLn(130, 'L12') +
    icCode(64, 144, '    get_package_share_directory(\'ira_laser_tools\'),', '#4fc3f7') + icLn(144, 'L13') +
    icCode(64, 158, '    \'launch\',', '#7ee787') + icLn(158, 'L14') +
    icCode(64, 172, '    \'merge_multi.launch.py\'', '#7ee787') + icLn(172, 'L15') +
    icCode(64, 186, '    )', '#8b949e') + icLn(186, 'L16') +
    txt(64, 212, '# --- PROGRAM 2: THE LASER FILTER ---', { size: 7, mono: true, fill: '#6e7681' }) +
    rrect(52, 220, 344, 86, 5, '#161b22', '#30363d', ' id="ic-cC"') +
    icCode(64, 234, 'laser_filter_launch_file = os.path.join(', '#e6edf3') + icLn(234, 'L20') +
    icCode(64, 248, '    get_package_share_directory(\'yahboom_laser_filter\'),', '#4fc3f7') + icLn(248, 'L21') +
    icCode(64, 262, '    \'launch\',', '#7ee787') + icLn(262, 'L22') +
    icCode(64, 276, '    \'laser_filter_node.launch.py\'', '#7ee787') + icLn(276, 'L23') +
    icCode(64, 290, '    )', '#8b949e') + icLn(290, 'L24') +
    txt(64, 314, 'L28: return LaunchDescription([ ... ]) — নিচের সারিতে', { size: 7.5, fill: '#6e7681', id: 'ic-cDd', op: 0 }) +
    rrect(428, 44, 432, 274, 8, '#111', '#30363d') +
    txt(644, 64, 'CONSTRUCTOR-এর ভেতরে — দুই path তৈরি', { anchor: 'middle', size: 10, weight: 700, fill: '#e6edf3' }) +
    rrect(444, 72, 400, 22, 5, '#161b22', '#30363d', ' id="ic-k1" opacity="0"') +
    txt(456, 86, 'def generate_launch_description():', { size: 9, mono: true, weight: 700, fill: '#e3b341', id: 'ic-k1t', op: 0 }) +
    txt(832, 86, 'constructor', { anchor: 'end', size: 7.5, fill: '#8b949e', id: 'ic-k1b', op: 0 }) +
    txt(444, 110, 'PROGRAM 1 — merger path (L12-16)', { size: 8.5, weight: 700, fill: '#ffb454', id: 'ic-s1', op: 0 }) +
    rrect(444, 116, 400, 21, 5, '#161b22', '#4fc3f7', ' id="ic-a1" opacity="0"') +
    txt(456, 130, 'get_package_share_directory(\'ira_laser_tools\')', { size: 8.5, mono: true, weight: 700, fill: '#4fc3f7', id: 'ic-a1t', op: 0 }) +
    txt(832, 130, 'L13', { anchor: 'end', size: 7, mono: true, fill: '#6e7681', id: 'ic-a1n', op: 0 }) +
    txt(456, 152, 'ament index থেকে resolve: .../share/ira_laser_tools (illustrative)', { size: 7.5, fill: '#8b949e', id: 'ic-a1r', op: 0 }) +
    rrect(444, 158, 156, 17, 4, '#161b22', '#ffb454', ' id="ic-ch1" opacity="0"') +
    txt(452, 170, '.../share/ira_laser_tools', { size: 6.8, mono: true, fill: '#ffb454', id: 'ic-ch1t', op: 0 }) +
    txt(606, 170, '+', { size: 9, fill: '#8b949e', id: 'ic-p1', op: 0 }) +
    rrect(614, 158, 64, 17, 4, '#161b22', '#ffb454', ' id="ic-ch2" opacity="0"') +
    txt(622, 170, 'launch', { size: 6.8, mono: true, fill: '#ffb454', id: 'ic-ch2t', op: 0 }) +
    txt(684, 170, '+', { size: 9, fill: '#8b949e', id: 'ic-p2', op: 0 }) +
    rrect(692, 158, 152, 17, 4, '#161b22', '#ffb454', ' id="ic-ch3" opacity="0"') +
    txt(700, 170, 'merge_multi.launch.py', { size: 6.8, mono: true, fill: '#ffb454', id: 'ic-ch3t', op: 0 }) +
    rrect(444, 179, 400, 19, 4, '#161b22', '#ffb454', ' id="ic-j1" opacity="0"') +
    txt(452, 192, '.../ira_laser_tools/launch/merge_multi.launch.py', { size: 7, mono: true, weight: 700, fill: '#ffb454', id: 'ic-j1t', op: 0 }) +
    txt(836, 192, '= laser_merge_launch_file', { anchor: 'end', size: 6.8, mono: true, fill: '#e6edf3', id: 'ic-j1v', op: 0 }) +
    txt(644, 212, 'EAGER — মান এখনই মূল্যায়িত, run-এর জন্য অপেক্ষা নয়', { anchor: 'middle', size: 7.5, weight: 700, fill: '#e3b341', id: 'ic-e1', op: 0 }) +
    txt(444, 230, 'PROGRAM 2 — filter path (L20-24)', { size: 8.5, weight: 700, fill: '#ffb454', id: 'ic-s2', op: 0 }) +
    rrect(444, 236, 400, 21, 5, '#161b22', '#4fc3f7', ' id="ic-a2" opacity="0"') +
    txt(456, 250, 'get_package_share_directory(\'yahboom_laser_filter\')', { size: 8.5, mono: true, weight: 700, fill: '#4fc3f7', id: 'ic-a2t', op: 0 }) +
    txt(832, 250, 'L21', { anchor: 'end', size: 7, mono: true, fill: '#6e7681', id: 'ic-a2n', op: 0 }) +
    rrect(444, 263, 156, 17, 4, '#161b22', '#d2a8ff', ' id="ic-dh1" opacity="0"') +
    txt(452, 275, '.../share/yahboom_laser_filter', { size: 6.8, mono: true, fill: '#d2a8ff', id: 'ic-dh1t', op: 0 }) +
    txt(606, 275, '+', { size: 9, fill: '#8b949e', id: 'ic-p3', op: 0 }) +
    rrect(614, 263, 64, 17, 4, '#161b22', '#d2a8ff', ' id="ic-dh2" opacity="0"') +
    txt(622, 275, 'launch', { size: 6.8, mono: true, fill: '#d2a8ff', id: 'ic-dh2t', op: 0 }) +
    txt(684, 275, '+', { size: 9, fill: '#8b949e', id: 'ic-p4', op: 0 }) +
    rrect(692, 263, 152, 17, 4, '#161b22', '#d2a8ff', ' id="ic-dh3" opacity="0"') +
    txt(700, 275, 'laser_filter_node.launch.py', { size: 6.8, mono: true, fill: '#d2a8ff', id: 'ic-dh3t', op: 0 }) +
    rrect(444, 284, 400, 19, 4, '#161b22', '#d2a8ff', ' id="ic-j2" opacity="0"') +
    txt(452, 297, '.../yahboom_laser_filter/launch/laser_filter_node.launch.py', { size: 7, mono: true, weight: 700, fill: '#d2a8ff', id: 'ic-j2t', op: 0 }) +
    txt(836, 297, '= laser_filter_launch_file', { anchor: 'end', size: 6.8, mono: true, fill: '#e6edf3', id: 'ic-j2v', op: 0 }) +
    rrect(40, 326, 820, 92, 8, '#0d1117', '#2a3442') +
    txt(56, 346, 'RETURN QUEUE — L28: LaunchDescription([...]) দুইটা wrapper action পাশাপাশি', { size: 9.5, weight: 700, fill: '#e6edf3' }) +
    rrect(56, 356, 388, 50, 6, '#161b22', '#ffb454', ' id="ic-w1" opacity="0"') +
    txt(68, 374, 'IncludeLaunchDescription(', { size: 8.5, mono: true, weight: 700, fill: '#e6edf3', id: 'ic-w1a', op: 0 }) +
    txt(80, 389, 'PythonLaunchDescriptionSource(laser_merge_launch_file)', { size: 7.5, mono: true, fill: '#ffb454', id: 'ic-w1b', op: 0 }) +
    txt(68, 402, ')', { size: 8.5, mono: true, fill: '#e6edf3', id: 'ic-w1c', op: 0 }) +
    txt(832, 374, 'L32-34', { anchor: 'end', size: 7, mono: true, fill: '#6e7681', id: 'ic-w1n', op: 0 }) +
    rrect(452, 356, 388, 50, 6, '#161b22', '#d2a8ff', ' id="ic-w2" opacity="0"') +
    txt(464, 374, 'IncludeLaunchDescription(', { size: 8.5, mono: true, weight: 700, fill: '#e6edf3', id: 'ic-w2a', op: 0 }) +
    txt(476, 389, 'PythonLaunchDescriptionSource(laser_filter_launch_file)', { size: 7.5, mono: true, fill: '#d2a8ff', id: 'ic-w2b', op: 0 }) +
    txt(464, 402, ')', { size: 8.5, mono: true, fill: '#e6edf3', id: 'ic-w2c', op: 0 }) +
    txt(832, 374, 'L38-40', { anchor: 'end', size: 7, mono: true, fill: '#6e7681', id: 'ic-w2n', op: 0 }) +
    txt(450, 434, 'রঙ-নিয়ম: হলুদ = merger path (ira_laser_tools), বেগুনি = filter path (yahboom_laser_filter), নীল = ament lookup', { anchor: 'middle', size: 8, fill: '#8b949e' }) +
    txt(450, 448, 'source: laser_driver.launch.py L8-L24, L28, L32-34, L38-40 (imports L1-L6, Node L6 unused) + README L3/L5', { anchor: 'middle', size: 8, mono: true, fill: '#6e7681' })
  );
  const q = id => svg.querySelector('#' + id);
  const show = id => q(id).setAttribute('opacity', 1);
  const edge = id => q(id).setAttribute('stroke', '#e3b341');
  host.caption('README-র L3 command চালালে <code>ros2 launch</code> এই file-টা পড়ে তার <code>generate_launch_description()</code>-কে ডাকে — আর file-টা নতুন কিছু নয়: folder 11 আর 12-এর driver-এর সাথে byte-হুবহু এক। এই anim-এ দেখব ভেতরে কী হয় — এই মুহূর্তে কোনো process এখনও জন্মায়নি।');
  host.formula('ros2 launch yahboom_M3Pro_laser laser_driver.launch.py -> constructor NOW -> run actions later');
  await host.sleep(1500);
  edge('ic-cA'); show('ic-k1'); show('ic-k1t'); show('ic-k1b');
  host.caption('<b>L8</b> — <code>def generate_launch_description():</code>। এটাই constructor: LaunchDescription-এর নকশা এখন তৈরি হবে, একটাও process এখন run হচ্ছে না — run আলাদা phase, পরের part-এর গল্প। আর ছটা import-এর (L1-L6) মধ্যে <code>Node</code> (L6) একবারও ব্যবহার পড়ে না — comment নিজেই বলে, just in case রাখা হয়েছে; launch file-টা নিজে একটাও node চালায় না, তাই ওটা কাজেও আসে না।');
  await host.sleep(1500);
  edge('ic-cB'); show('ic-s1'); show('ic-a1'); show('ic-a1t'); show('ic-a1n');
  host.caption('<b>L13</b> — <code>get_package_share_directory(\'ira_laser_tools\')</code> (import আছে L2-তে, ament_index_python থেকে)। ament index ঘেঁটে install করা package-টার share directory কোথায়, সেটা বের করে।');
  await host.sleep(1400);
  show('ic-a1r'); show('ic-ch1'); show('ic-ch1t'); show('ic-p1'); show('ic-ch2'); show('ic-ch2t'); show('ic-p2'); show('ic-ch3'); show('ic-ch3t');
  host.caption('তারপর <code>os.path.join</code> (L12) তিনটা টুকরো জোড়ে — share dir + <code>\'launch\'</code> folder (L14) + <code>\'merge_multi.launch.py\'</code> (L15)। তিনটাই plain string: কোনোটাই runtime option নয়।');
  await host.sleep(1400);
  show('ic-j1'); show('ic-j1t'); show('ic-j1v'); show('ic-e1');
  host.caption('ফল একটাই absolute path, বসে গেল <code>laser_merge_launch_file</code>-এ (প্রকৃত prefix machine-ভেদে আলাদা — <b>illustrative</b>)। এটা <b>EAGER</b>: constructor চলার মুহূর্তেই মান মূল্যায়ন হয় — folder 10-এর <code>LaunchConfiguration</code> ছিল lazy, run-এ মূল্যায়ন হত।');
  host.formula('os.path.join(share_dir, \'launch\', \'merge_multi.launch.py\') = one absolute path, computed NOW');
  await host.sleep(1600);
  edge('ic-cC'); show('ic-s2'); show('ic-a2'); show('ic-a2t'); show('ic-a2n');
  show('ic-dh1'); show('ic-dh1t'); show('ic-p3'); show('ic-dh2'); show('ic-dh2t'); show('ic-p4'); show('ic-dh3'); show('ic-dh3t');
  show('ic-j2'); show('ic-j2t'); show('ic-j2v');
  host.caption('<b>L20-24</b> — ঠিক একই পদ্ধতিতে দ্বিতীয় path: এবার package <code>yahboom_laser_filter</code>, file <code>laser_filter_node.launch.py</code>, ফল <code>laser_filter_launch_file</code>। দুই join-ই EAGER — constructor শেষ হতেই দুটো মানই বসা।');
  host.formula('eager: plain call at L12/L20, value fixed at constructor  vs  lazy: LaunchConfiguration, value fixed at run (folder 10)');
  await host.sleep(1600);
  show('ic-w1'); show('ic-w1a'); show('ic-w1b'); show('ic-w1c'); show('ic-w1n');
  show('ic-w2'); show('ic-w2a'); show('ic-w2b'); show('ic-w2c'); show('ic-w2n');
  show('ic-cDd');
  host.caption('এবার wrapper: <code>PythonLaunchDescriptionSource(path)</code> বলে সেই file একটা Python launch source (import L5), আর <code>IncludeLaunchDescription</code> (import L4) বলে সেটা এই launch-এর ভেতরেই চালাতে হবে। দুটো wrapper-ই দাঁড়িয়ে গেল <b>L28</b>-এর তালিকায় — return আর আসল run পরের part-এ।');
  host.formula('LaunchDescription([ IncludeLaunchDescription(PythonLaunchDescriptionSource(p1)), same(p2) ]) = 2 queued actions');
  await host.sleep(1600);
  host.caption('মোদ্দা কথা: README-র এক command (L3) দুটো অন্য package-এর launch file নিজের ভেতরে টেনে আনে — folder 10-এর পুরো merger + filter chain এক আঁজলায়। এই একই file হুবহু চলে folder 11 ও 12-তেও; বদলায় শুধু downstream-এর ভোক্তা — এই বার <code>/scan</code>-এর কথা শোনে guard <code>laser_Warning</code>। তবে launch-টা তাকে ওঠায় না (নিজের একটাও node নেই) — README-র L5 <code>ros2 run</code> আলাদা করে তোলে।');
  await host.sleep(1500);
};

/* ---------- subPubGraph ---------- */
/* ===== folder-13 anim — subPubGraph (laser_Warning.py L18-L32) =====
   দুই ear (/scan, /JoyState) + দুই mouth (/cmd_vel, /beep) — constructor-এর
   পুরো নকশা; tracker-এর topology-র উপর একটা নতুন কণ্ঠ।
   Facts: L18 class laserWarning(Node) (NOT laserTracker), L19
   def __init__(self,name) — name arrives as an explicit argument, L20
   super().__init__(name) names the node from outside, L24
   create_subscription(LaserScan, "/scan", self.registerScan,1), L26
   create_subscription(Bool, '/JoyState', self.JoyStateCallback,1),
   L30 create_publisher(Twist, '/cmd_vel',1), L32 create_publisher(
   UInt16,'/beep',1) — THE NEW GUARD CHANNEL the tracker lacked:
   the buzzer ON/OFF line. UInt16() default value 0 = beep OFF;
   b.data = 1 (L91) = ON; else branch republishes UInt16() (L95).
   Bool is the yahboom common Bool from the L13 star-import, NOT
   std_msgs (UInt16 IS std_msgs, L6). Twist here carries angular.z
   only — linear.x is never set (L123); declared linear/angular
   (L36, L38) are read once and never used again. Node name
   laser_Warnning_a1 — "Warnning" typo IN SOURCE — comes from
   main() L136. /scan = folder 10 chain-এর fused 360 ফল। L17 L21
   L27 L33 ফাঁকা line। Stage strings-এ arrow character নেই; id
   prefix sp-. */


function spArrow(x1, y1, x2, y2, c, id) {
  const a = Math.atan2(y2 - y1, x2 - x1);
  const bx = x2 - 7 * Math.cos(a), by = y2 - 7 * Math.sin(a);
  const p1x = bx - 2.8 * Math.sin(a), p1y = by + 2.8 * Math.cos(a);
  const p2x = bx + 2.8 * Math.sin(a), p2y = by - 2.8 * Math.cos(a);
  return '<g id="' + id + '" opacity="0">' +
    '<path d="M' + x1 + ' ' + y1 + 'L' + bx.toFixed(1) + ' ' + by.toFixed(1) + '" stroke="' + c + '" stroke-width="1.6" fill="none"/>' +
    '<path d="M' + x2 + ' ' + y2 + 'L' + p1x.toFixed(1) + ' ' + p1y.toFixed(1) + 'L' + p2x.toFixed(1) + ' ' + p2y.toFixed(1) + 'Z" fill="' + c + '"/></g>';
}

function spRing(cx, cy, r, id, fill) {
  let d = '';
  for (let i = 0; i < 360; i += 30) {
    const x = cx + r * Math.cos(i * Math.PI / 180);
    const y = cy + r * Math.sin(i * Math.PI / 180);
    d += 'M' + (x - 1.2).toFixed(1) + ' ' + (y - 1.2).toFixed(1) + 'h2.4v2.4h-2.4z';
  }
  return '<path id="' + id + '" d="' + d + '" fill="' + fill + '" opacity="0"/>';
}

ANIMS.subPubGraph = async function (host) {
  const svg = host.setStage(
    txt(450, 26, 'constructor L18-L32: class জন্ম, দুই ear, দুই mouth — guard-এর নিজের কণ্ঠ', { anchor: 'middle', size: 14, weight: 600, fill: '#ffb454' }) +
    rrect(40, 44, 372, 316, 8, '#0d1117', '#2a3442') +
    txt(56, 64, 'LASER_WARNING.PY — CONSTRUCTOR', { size: 9.5, weight: 700, fill: '#e6edf3' }) +
    rrect(50, 74, 342, 58, 4, '#161b22', '#e3b341', ' id="sp-h1" opacity="0"') +
    rrect(50, 131, 342, 58, 4, '#161b22', '#7ee787', ' id="sp-h2" opacity="0"') +
    rrect(50, 188, 342, 40, 4, '#161b22', '#4fc3f7', ' id="sp-h3" opacity="0"') +
    rrect(50, 226, 342, 58, 4, '#161b22', '#e3b341', ' id="sp-h4" opacity="0"') +
    rrect(50, 284, 342, 40, 4, '#161b22', '#ff7b72', ' id="sp-h5" opacity="0"') +
    txt(56, 86, 'class laserWarning(Node):', { size: 8.5, mono: true, weight: 700, fill: '#e6edf3' }) +
    txt(392, 86, 'L18', { anchor: 'end', size: 7.5, mono: true, fill: '#6e7681' }) +
    txt(64, 105, 'def __init__(self,name):', { size: 8.5, mono: true, fill: '#c9d1d9' }) +
    txt(76, 124, 'super().__init__(name)', { size: 8.5, mono: true, fill: '#c9d1d9' }) +
    txt(392, 124, 'L20', { anchor: 'end', size: 7.5, mono: true, fill: '#6e7681' }) +
    txt(64, 143, '# --- CREATING SUBSCRIBERS (Listeners) ---', { size: 7.5, mono: true, fill: '#6e7681' }) +
    txt(72, 162, 'self.sub_laser = self.create_subscription(', { size: 8.5, mono: true, fill: '#7ee787' }) +
    txt(392, 162, 'L24', { anchor: 'end', size: 7.5, mono: true, fill: '#6e7681' }) +
    txt(84, 181, 'LaserScan,"/scan",self.registerScan,1)', { size: 8.5, mono: true, fill: '#7ee787' }) +
    txt(72, 200, 'self.sub_JoyState = self.create_subscription(', { size: 8.5, mono: true, fill: '#4fc3f7' }) +
    txt(392, 200, 'L26', { anchor: 'end', size: 7.5, mono: true, fill: '#6e7681' }) +
    txt(84, 219, 'Bool,\'/JoyState\', self.JoyStateCallback,1)', { size: 8.5, mono: true, fill: '#4fc3f7' }) +
    txt(64, 238, '# --- CREATING PUBLISHERS (Radio Stations) ---', { size: 7.5, mono: true, fill: '#6e7681' }) +
    txt(72, 257, 'self.pub_vel = self.create_publisher(', { size: 8.5, mono: true, fill: '#e3b341' }) +
    txt(392, 257, 'L30', { anchor: 'end', size: 7.5, mono: true, fill: '#6e7681' }) +
    txt(84, 276, 'Twist,\'/cmd_vel\',1)', { size: 8.5, mono: true, fill: '#e3b341' }) +
    txt(72, 295, 'self.pub_Buzzer = self.create_publisher(', { size: 8.5, mono: true, fill: '#ff7b72' }) +
    txt(392, 295, 'L32', { anchor: 'end', size: 7.5, mono: true, fill: '#6e7681' }) +
    txt(84, 314, 'UInt16,\'/beep\',1)', { size: 8.5, mono: true, fill: '#ff7b72' }) +
    txt(56, 340, 'L17 L21 L27 L33 = ফাঁকা line — constructor-এর সীমানা L33-এ শেষ', { size: 7.5, fill: '#6e7681' }) +
    txt(56, 353, 'L22 L23 L25 L28 L29 L31-এ শুধু ইংরেজি ব্যাখ্যা-মন্তব্য', { size: 7.5, fill: '#6e7681' }) +
    rrect(428, 44, 432, 316, 8, '#111', '#30363d') +
    txt(644, 64, 'ROS GRAPH — দুই ear, দুই mouth', { anchor: 'middle', size: 9.5, weight: 700, fill: '#e6edf3' }) +
    rrect(748, 84, 100, 24, 12, '#0d1117', '#e3b341', ' id="sp-parentB" opacity="0"') +
    txt(798, 99, 'Node (rclpy)', { anchor: 'middle', size: 8, mono: true, weight: 700, fill: '#e3b341', id: 'sp-parentT', op: 0 }) +
    '<path d="M798 108L712 168" stroke="#e3b341" stroke-width="1.2" stroke-dasharray="3 3" fill="none" opacity="0" id="sp-pwire"/>' +
    spRing(476, 104, 10, 'sp-ring', '#7ee787') +
    txt(492, 100, 'fused 360 ring', { size: 6.5, fill: '#8b949e', id: 'sp-scanL1', op: 0 }) +
    txt(492, 111, 'folder 10 chain-এর ফল', { size: 6.5, fill: '#6e7681', id: 'sp-scanL2', op: 0 }) +
    txt(452, 121, 'EAR 1', { size: 7, weight: 700, fill: '#7ee787', id: 'sp-ear1', op: 0 }) +
    rrect(452, 128, 108, 30, 15, '#0d1117', '#7ee787', ' id="sp-scanB" opacity="0"') +
    txt(506, 147, '/scan', { anchor: 'middle', size: 9.5, mono: true, weight: 700, fill: '#7ee787', id: 'sp-scanT', op: 0 }) +
    spArrow(560, 150, 582, 198, '#7ee787', 'sp-a1') +
    txt(506, 176, 'msg: LaserScan', { anchor: 'middle', size: 6.5, mono: true, fill: '#8b949e', id: 'sp-a1m', op: 0 }) +
    txt(506, 188, 'cb: registerScan', { anchor: 'middle', size: 6.5, mono: true, fill: '#8b949e', id: 'sp-a1cb', op: 0 }) +
    txt(506, 200, 'queue depth 1', { anchor: 'middle', size: 6.5, mono: true, fill: '#6e7681', id: 'sp-q1', op: 0 }) +
    txt(452, 243, 'EAR 2', { size: 7, weight: 700, fill: '#4fc3f7', id: 'sp-ear2', op: 0 }) +
    rrect(452, 250, 108, 30, 15, '#0d1117', '#4fc3f7', ' id="sp-joyB" opacity="0"') +
    txt(506, 269, '/JoyState', { anchor: 'middle', size: 9.5, mono: true, weight: 700, fill: '#4fc3f7', id: 'sp-joyT', op: 0 }) +
    spArrow(560, 262, 582, 238, '#4fc3f7', 'sp-a2') +
    txt(506, 296, 'msg: Bool (vendor L13), cb: JoyStateCallback', { anchor: 'middle', size: 6.5, mono: true, fill: '#8b949e', id: 'sp-joyL', op: 0 }) +
    txt(506, 308, 'queue depth 1 — মানুষের override bit', { anchor: 'middle', size: 6.5, fill: '#6e7681', id: 'sp-joyL2', op: 0 }) +
    rrect(584, 168, 144, 118, 10, '#161b22', '#e3b341', ' id="sp-nodeB" opacity="0"') +
    txt(656, 190, 'laserWarning', { anchor: 'middle', size: 12, mono: true, weight: 700, fill: '#e6edf3', id: 'sp-nodeT', op: 0 }) +
    txt(656, 204, 'class — L18', { anchor: 'middle', size: 7, fill: '#8b949e', id: 'sp-nodeC', op: 0 }) +
    rrect(598, 214, 116, 20, 4, '#161b22', '#d2a8ff', ' id="sp-nameB" opacity="0"') +
    txt(656, 228, 'laser_Warnning_a1', { anchor: 'middle', size: 7.5, mono: true, weight: 700, fill: '#d2a8ff', id: 'sp-nameT', op: 0 }) +
    txt(656, 250, 'parent: super().__init__(name)', { anchor: 'middle', size: 6.5, mono: true, fill: '#8b949e', id: 'sp-supT', op: 0 }) +
    txt(656, 268, 'নামটা পাঠাবে main() — L136', { anchor: 'middle', size: 6.5, fill: '#6e7681', id: 'sp-nameN', op: 0 }) +
    txt(796, 148, 'MOUTH 1', { anchor: 'middle', size: 6.5, weight: 700, fill: '#e3b341', id: 'sp-m1T', op: 0 }) +
    spArrow(728, 172, 750, 172, '#e3b341', 'sp-a3') +
    txt(739, 163, '/cmd_vel', { anchor: 'middle', size: 7, mono: true, weight: 700, fill: '#e3b341', id: 'sp-cmdT', op: 0 }) +
    rrect(752, 154, 88, 38, 8, '#0d1117', '#e3b341', ' id="sp-whB" opacity="0"') +
    txt(796, 171, 'wheels', { anchor: 'middle', size: 8.5, mono: true, weight: 700, fill: '#e3b341', id: 'sp-whT', op: 0 }) +
    txt(796, 184, 'base driver', { anchor: 'middle', size: 6.5, fill: '#8b949e', id: 'sp-whT2', op: 0 }) +
    rrect(752, 198, 88, 30, 4, '#161b22', '#d2a8ff', ' id="sp-twB" opacity="0"') +
    txt(796, 210, 'Twist', { anchor: 'middle', size: 7.5, mono: true, weight: 700, fill: '#d2a8ff', id: 'sp-twT', op: 0 }) +
    txt(796, 221, 'angular.z only — L123', { anchor: 'middle', size: 6.2, mono: true, fill: '#d2a8ff', id: 'sp-twT2', op: 0 }) +
    txt(796, 230, 'MOUTH 2', { anchor: 'middle', size: 6.5, weight: 700, fill: '#ff7b72', id: 'sp-m2T', op: 0 }) +
    spArrow(728, 254, 750, 254, '#ff7b72', 'sp-a4') +
    txt(739, 245, '/beep', { anchor: 'middle', size: 7, mono: true, weight: 700, fill: '#ff7b72', id: 'sp-beepT', op: 0 }) +
    rrect(752, 236, 88, 38, 8, '#0d1117', '#ff7b72', ' id="sp-bzB" opacity="0"') +
    txt(796, 253, 'buzzer', { anchor: 'middle', size: 8.5, mono: true, weight: 700, fill: '#ff7b72', id: 'sp-bzT', op: 0 }) +
    txt(796, 266, 'ON=1 OFF=0', { anchor: 'middle', size: 6.5, mono: true, fill: '#8b949e', id: 'sp-bzT2', op: 0 }) +
    rrect(752, 280, 88, 30, 4, '#161b22', '#d2a8ff', ' id="sp-u16B" opacity="0"') +
    txt(796, 292, 'UInt16', { anchor: 'middle', size: 7.5, mono: true, weight: 700, fill: '#d2a8ff', id: 'sp-u16T', op: 0 }) +
    txt(796, 303, 'std_msgs — L6', { anchor: 'middle', size: 6.2, mono: true, fill: '#d2a8ff', id: 'sp-u16T2', op: 0 }) +
    rrect(688, 322, 148, 24, 4, '#161b22', '#d2a8ff', ' id="sp-nextB" opacity="0"') +
    txt(762, 337, 'NEXT L35: declare_parameter', { anchor: 'middle', size: 7, mono: true, fill: '#d2a8ff', id: 'sp-nextT', op: 0 }) +
    txt(450, 386, 'রঙ-নিয়ম: সবুজ = /scan, নীল = /JoyState, হলুদ = /cmd_vel ও parent, লাল = /beep (guard-এর কণ্ঠ), বেগুনি = নাম ও msg টাইপ', { anchor: 'middle', size: 8.5, fill: '#8b949e' }) +
    txt(450, 440, 'source: laser_Warning.py L18-L32 + main() L136', { anchor: 'middle', size: 8, mono: true, fill: '#6e7681' })
  );
  const q = id => svg.querySelector('#' + id);
  const show = id => q(id).setAttribute('opacity', 1);
  const dimc = id => q(id).setAttribute('stroke', '#30363d');
  host.caption('Constructor-এর পুরো নকশা এই কয়েকটা beat-এ: L18-এ class জন্ম, তারপর দুটো subscription আর — tracker-এর চেয়ে একটা বেশি — দুটো publisher। বাঁয়ে আসল code, ডানে তার graph।');
  host.formula('constructor = class birth + super wiring + 2 subscriptions + 2 publishers');
  await host.sleep(1400);

  show('sp-h1'); show('sp-nodeB'); show('sp-nodeT'); show('sp-nodeC');
  show('sp-parentB'); show('sp-parentT'); show('sp-pwire'); show('sp-supT');
  host.caption('<b>class laserWarning(Node)</b> (L18) — rclpy-র <code>Node</code> থেকে inherit করে নতুন class জন্মাল। <b>super().__init__(name)</b> (L20) parent-এর constructor ডেকে এই বাচ্চাটাকে ROS graph-এ সত্যিকারের node বানিয়ে দেয় — আর নামটা বাইরে থেকে আসে: L19-এ <code>def __init__(self,name)</code>, name একটা explicit argument।');
  host.formula('super().__init__(name) -> laserWarning instance becomes a live node');
  await host.sleep(1600);

  show('sp-nameB'); show('sp-nameT'); show('sp-nameN');
  host.caption('একটা সূক্ষ্ম পয়েন্ট: class-এর নাম <code>laserWarning</code>, কিন্তু node-এর নাম আলাদা — <code>laser_Warnning_a1</code> (বানানটা source-এ এমনই, "Warnning"-এ double-n)। এই নামটা constructor নিজে বানায় না; পরে <b>main()</b> (L136) argument হিসেবে পাঠাবে। দুটো আলাদা জিনিস।');
  host.formula('class name: laserWarning   |   node name: laser_Warnning_a1 (main, L136)');
  await host.sleep(1700);

  dimc('sp-h1');
  show('sp-h2'); show('sp-ear1'); show('sp-scanB'); show('sp-scanT');
  show('sp-ring'); show('sp-scanL1'); show('sp-scanL2'); show('sp-a1');
  show('sp-a1m'); show('sp-a1cb'); show('sp-q1');
  host.caption('প্রথম ear (L24): <code>create_subscription(LaserScan, "/scan", self.registerScan, 1)</code>। Folder 10-এর পুরো chain (merge + filter) যে fused 360 ring বানিয়েছিল, সেটাই <code>/scan</code> topic-এ বয়ে আসে — এই node তার প্রথম কান খোলে। Queue depth 1: পুরনো frame জমা রাখার দরকার নেই।');
  host.formula('sub_laser = create_subscription(LaserScan, /scan, registerScan, depth 1)');
  await host.sleep(1800);

  dimc('sp-h2');
  show('sp-h3'); show('sp-ear2'); show('sp-joyB'); show('sp-joyT');
  show('sp-a2'); show('sp-joyL'); show('sp-joyL2');
  host.caption('দ্বিতীয় ear (L26): <code>Bool</code> টাইপের <code>/JoyState</code> — মানুষ joystick ধরলে কি না, এই এক bit। খুঁটিনাটি: এই <code>Bool</code> std_msgs-এর নয় — আসছে L13-এর star-import <code>yahboom_M3Pro_laser.common</code> থেকে (vendor-এর নিজেস্ব; module এই folder-এ নেই)। <code>JoyStateCallback</code> (L50-52) সেটা <code>Joy_active</code> flag-এ জমা রাখে (L45-এ জন্ম False); flag সত্যি হলে AI থেমে শূন্য <code>Twist</code> পাঠিয়ে দাঁড়িয়ে থাকে (L81-83)।');
  host.formula('sub_JoyState = create_subscription(Bool, /JoyState, JoyStateCallback, depth 1)');
  await host.sleep(1800);

  dimc('sp-h3');
  show('sp-h4'); show('sp-m1T'); show('sp-a3'); show('sp-cmdT');
  show('sp-whB'); show('sp-whT'); show('sp-whT2');
  host.caption('প্রথম mouth (L30): <code>create_publisher(Twist, \'/cmd_vel\', 1)</code> — registerScan-এর ভেতরে নেওয়া সিদ্ধান্ত এই wire দিয়ে বেরোয়, base driver-এর কাছে গিয়ে wheels-কে ঘোরায়। Tracker পর্যন্ত এটাই একমাত্র mouth ছিল — guard এখানে থেমে থাকে না।');
  host.formula('pub_vel = create_publisher(Twist, /cmd_vel, depth 1)');
  await host.sleep(1700);

  show('sp-twB'); show('sp-twT'); show('sp-twT2');
  host.caption('Mouth-এর ভাষাও ঠিক করা: <code>Twist</code> — কিন্তু guard এখানে <code>linear.x</code> কোনোদিন সেটই করে না (L123-এর মন্তব্য নিজেই বলে: robot জায়গায় দাঁড়িয়ে শুধু ঘোরে)। linear PID-ই নেই; কাজে আছে শুধু <code>angular.z</code> (rad/s)। Declared <code>linear</code> 0.5 (L36) আর <code>angular</code> 1.0 (L38) একবার পড়েই আর কোথাও ব্যবহার হয় না।');
  host.formula('guard Twist = angular.z only; linear.x stays 0.0 (L123) - spin in place');
  await host.sleep(1700);

  dimc('sp-h4');
  show('sp-h5'); show('sp-m2T'); show('sp-beepT'); show('sp-a4');
  show('sp-bzB'); show('sp-bzT'); show('sp-bzT2');
  host.caption('আর এইটাই guard-এর নতুন সংযোজন — দ্বিতীয় mouth (L32): <code>create_publisher(UInt16, \'/beep\', 1)</code>, tracker-এ যেটা ছিলই না। <code>UInt16()</code>-এর default মান 0 = বিপ বন্ধ; <code>b.data = 1</code> (L91) = বিপ চালু। সিদ্ধান্ত নেয় registerScan-এর ALARM ডাল: <code>minDist &lt;= ResponseDist (0.55)</code> হলে 1 পাঠায় (L89-92), নাহলে else-ডাল আবার <code>UInt16()</code> পাঠায় — 0, বিপ বন্ধ (L95)। Guard-এর দরকার কণ্ঠ — দুই pub, দুই sub।');
  host.formula('pub_Buzzer = create_publisher(UInt16, /beep, depth 1); 1 = beep ON, 0 = OFF');
  await host.sleep(1800);

  show('sp-u16B'); show('sp-u16T'); show('sp-u16T2'); show('sp-nextB'); show('sp-nextT');
  host.caption('<code>UInt16</code> আসছে <code>std_msgs</code> থেকে (L6, কমেন্টেই বলা: buzzer ON/OFF-এর message) — অর্থাৎ দুই রকম উৎস পাশাপাশি: /JoyState-এর Bool vendor-এর (L13), /beep-এর UInt16 std_msgs-এর। Constructor-এর নিজের কাজ L32-তেই শেষ — L33 ফাঁকা, L35 থেকে <code>declare_parameter</code>-এর সারি: linear 0.5, angular 1.0, LaserAngle 45.0, ResponseDist 0.55। সেটাই পরের অংশের গল্প।');
  host.formula('graph: 2 in (/scan, /JoyState) + 2 out (/cmd_vel, /beep) -> decision in, wheels + voice out');
  await host.sleep(1700);
};

/* ---------- beamSweep ---------- */
/* ============ folder-13 anim — beamSweep (part 10) ==================
   laser_Warning.py registerScan beam loop, L54-L70. Stage: top-down
   fused 360 ring (folder 10 merger+filter -> /scan), deg 0 up, +deg
   LEFT (ROS ccw). Beats: L54 def + L55 guard (subscription L24),
   L56 ranges np.array, L59-60 two empty parallel lists (collection
   shape is the SAME as folder 12's tracker, so the list beats
   stay), L63 cursor sweep i=0.., L65 rad->deg formula (i=192 ->
   +12 deg), L68 cone gate abs(angle) < LaserAngle (45.0, L39-40)
   strict -> 89 beams i=136..224, ranges[i] !=0.0 skips no-return
   zeros but passes inf (inf DOES enter the lists; with any finite
   companion it can never be the min), L69-70 parallel appends.
   Demo objects wave A + wave B: 0.90 m @ +14 deg then 0.70 m @
   +20 deg (illustrative, loop order) -> min 0.70 @ +20, outside
   ResponseDist 0.55. KEY DELTA vs folder 12: the empty guard is
   an EARLY RETURN (L72 comment, L73: if len(minDistList) == 0:
   return) - NO publish, NO buzzer write: motors hold the last
   /cmd_vel AND /beep LATCHES its last value (the buzzer-stays-on
   trap; red chip + final beat; folder 12 printed dashes inside an
   else-branch instead). Close previews L76 min + L78 argmin (ties
   -> first occurrence = lowest i) plus one line of downstream
   framing: the pair feeds alarm L89 + the spin-only PID (later
   parts). Ring ranges illustrative. Prefix bs-. No emoji, no
   Unicode arrows in stage strings, entities for &lt; &gt;. */

/* --- prefixed polar helpers (deg: 0 = up, +deg = screen left) --- */
function bsBeam(deg) {
  const a = (deg + 180) % 360 - 180;
  if (Math.abs(a) < 45) {                              /* front cone */
    if (Math.abs(a - 20) <= 3) return 0.70;            /* wave-B object (min) */
    if (Math.abs(a - 14) <= 3) return 0.90;            /* wave-A pillar */
    return 1.05;
  }
  if (deg > 55 && deg < 80) return 0.0;                /* no-return band */
  if (deg < -55 && deg > -80) return 0.0;              /* no-return band */
  return 1.25 + 0.07 * Math.sin(5 * a * Math.PI / 180); /* rear ring */
}
function bsXY(cx, cy, pxm, deg, r) {
  const th = deg * Math.PI / 180;
  return [cx - r * pxm * Math.sin(th), cy - r * pxm * Math.cos(th)];
}
function bsArcD(cx, cy, r, a0, a1) {
  const p0 = bsXY(cx, cy, 1, a0, r), p1 = bsXY(cx, cy, 1, a1, r);
  return 'M' + p0[0].toFixed(1) + ' ' + p0[1].toFixed(1) +
         'A' + r + ' ' + r + ' 0 0 0 ' + p1[0].toFixed(1) + ' ' + p1[1].toFixed(1);
}
/* square-dot bag for beam squares in [a0..a1] on the even-degree grid */
function bsSquares(cx, cy, pxm, step, a0, a1) {
  let d = '';
  for (let deg = a0; deg <= a1; deg += step) {
    const r = bsBeam(deg);
    if (r === null) continue;
    const p = bsXY(cx, cy, pxm, deg, r);
    d += 'M' + (p[0] - 1.2).toFixed(1) + ' ' + (p[1] - 1.2).toFixed(1) + 'h2.4v2.4h-2.4z';
  }
  return d;
}

ANIMS.beamSweep = async function (host) {
  const objB = bsXY(266, 226, 95, 20, 0.70);
  const objA = bsXY(266, 226, 95, 14, 0.90);
  const l45 = bsXY(266, 226, 1, 45, 176);
  const lm45 = bsXY(266, 226, 1, -45, 176);
  const zBand = bsXY(266, 226, 1, 66, 130);
  const svg = host.setStage(
    txt(450, 26, 'beam loop: সামনের cone-এর ভেতরে সবচেয়ে কাছের object-এর খোঁজ — L54-L70', { anchor: 'middle', size: 14, weight: 600, fill: '#ffb454' }) +
    /* ---------- left: fused ring, top view ---------- */
    rrect(40, 44, 452, 340, 8, '#0d1117', '#2a3442') +
    txt(54, 62, 'FUSED 360 RING (top view)', { size: 9, weight: 700, fill: '#e6edf3' }) +
    txt(54, 75, 'merge + filter থেকে /scan — দুই lidar এক চোখ', { size: 7.5, fill: '#8b949e' }) +
    '<path d="M266 210L266 70" stroke="#6e7681" stroke-width="1" stroke-dasharray="3 4" fill="none"/>' +
    txt(266, 64, 'deg 0', { anchor: 'middle', size: 7, fill: '#8b949e' }) +
    txt(104, 229, '+90', { anchor: 'middle', size: 7, fill: '#8b949e' }) +
    txt(428, 229, '-90', { anchor: 'middle', size: 7, fill: '#8b949e' }) +
    txt(266, 372, '180', { anchor: 'middle', size: 7, fill: '#8b949e' }) +
    '<path id="bs-ring" d="' + bsSquares(266, 226, 95, 2, -178, 178) + '" fill="#7ee787" opacity="0.4"/>' +
    '<path d="' + bsArcD(266, 226, 150, -45, 45) + '" fill="none" stroke="#7ee787" stroke-width="8" opacity="0.9" id="bs-fa" />' +
    txt(l45[0], l45[1], '+45', { anchor: 'middle', size: 7, weight: 700, fill: '#7ee787' }) +
    txt(lm45[0], lm45[1], '-45', { anchor: 'middle', size: 7, weight: 700, fill: '#7ee787' }) +
    circ(objB[0], objB[1], 4.5, '#ff7b72', ' id="bs-objB" opacity="0.9"') +
    txt(objB[0] + 8, objB[1] - 6, '0.70 m @ +20', { size: 7.5, weight: 700, fill: '#ff7b72', id: 'bs-objBt', op: 0 }) +
    circ(objA[0], objA[1], 4, '#d2a8ff', ' id="bs-objA" opacity="0.9"') +
    txt(objA[0] - 8, objA[1] - 8, '0.90 m @ +14', { anchor: 'end', size: 7.5, weight: 700, fill: '#d2a8ff', id: 'bs-objAt', op: 0 }) +
    txt(zBand[0] - 6, zBand[1], 'ranges = 0.0', { anchor: 'end', size: 7, mono: true, fill: '#6e7681', id: 'bs-zt', op: 0 }) +
    rrect(257, 216, 18, 20, 3, '#30363d', '#8b949e') +
    '<path d="M266 216L266 207" stroke="#7ee787" stroke-width="2" fill="none"/>' +
    txt(285, 207, 'front', { size: 6.5, fill: '#8b949e' }) +
    txt(54, 328, 'SCAN CURSOR', { size: 7, weight: 700, fill: '#6e7681' }) +
    txt(54, 344, 'i = 0', { size: 9, mono: true, weight: 700, fill: '#e6edf3', id: 'bs-ri' }) +
    txt(54, 358, 'angle = -180 deg', { size: 8.5, mono: true, fill: '#8b949e', id: 'bs-ra' }) +
    txt(54, 372, 'ranges[i] = 1.25 m', { size: 8.5, mono: true, fill: '#8b949e', id: 'bs-rr' }) +
    txt(160, 344, '+deg = বাঁদিক', { size: 7.5, fill: '#6e7681' }) +
    '<g id="bs-cur" transform="rotate(180 266 226)"><line x1="266" y1="226" x2="266" y2="90" stroke="#e6edf3" stroke-width="1.2" opacity="0.9"/><circle cx="266" cy="90" r="3" fill="#e6edf3"/></g>' +
    /* ---------- left: empty-cone latch chip (final beat) ---------- */
    '<g id="bs-latch" opacity="0">' +
    rrect(330, 328, 152, 48, 5, '#161b22', '#ff7b72') +
    txt(406, 342, 'খালি cone: L72-73 return', { anchor: 'middle', size: 7.5, weight: 700, fill: '#ff7b72' }) +
    txt(406, 355, 'publish নেই, /beep write নেই', { anchor: 'middle', size: 7, mono: true, fill: '#e6edf3' }) +
    txt(406, 368, 'buzzer শেষ মানেই LATCH - বাজতে থাকে', { anchor: 'middle', size: 7, fill: '#8b949e' }) +
    '</g>' +
    /* ---------- right: code L54-L70 ---------- */
    rrect(516, 44, 344, 252, 8, '#0d1117', '#30363d') +
    txt(688, 62, 'registerScan — beam loop (L54-L70)', { anchor: 'middle', size: 9, weight: 700, fill: '#e6edf3' }) +
    rrect(522, 70, 332, 27, 3, '#21262d', 'none', ' id="bs-hl1" opacity="0"') +
    rrect(522, 96, 332, 13, 3, '#21262d', 'none', ' id="bs-hl2" opacity="0"') +
    rrect(522, 109, 332, 27, 3, '#21262d', 'none', ' id="bs-hl3" opacity="0"') +
    rrect(522, 136, 332, 13, 3, '#21262d', 'none', ' id="bs-hl4" opacity="0"') +
    rrect(522, 149, 332, 27, 3, '#21262d', 'none', ' id="bs-hl5" opacity="0"') +
    rrect(522, 176, 332, 13, 3, '#21262d', 'none', ' id="bs-hl6" opacity="0"') +
    rrect(522, 189, 332, 27, 3, '#21262d', 'none', ' id="bs-hl7" opacity="0"') +
    txt(530, 80, 'def registerScan(self, scan_data):', { size: 8, mono: true, fill: '#8b949e' }) +
    txt(530, 94, 'if not isinstance(scan_data, LaserScan): return', { size: 8, mono: true, fill: '#8b949e' }) +
    txt(530, 105, 'ranges = np.array(scan_data.ranges)', { size: 8, mono: true, fill: '#8b949e' }) +
    txt(530, 119, 'minDistList = []', { size: 8, mono: true, fill: '#8b949e' }) +
    txt(530, 132, 'minDistIDList = []', { size: 8, mono: true, fill: '#8b949e' }) +
    txt(530, 145, 'for i in range(len(ranges)):', { size: 8, mono: true, fill: '#8b949e' }) +
    txt(530, 159, 'angle = (scan_data.angle_min +', { size: 8, mono: true, fill: '#8b949e' }) +
    txt(530, 173, 'scan_data.angle_increment * i) * RAD2DEG', { size: 8, mono: true, fill: '#8b949e' }) +
    txt(530, 186, 'if abs(angle) &lt; self.LaserAngle and ranges[i] !=0.0 :', { size: 8, mono: true, fill: '#8b949e' }) +
    txt(530, 199, 'minDistList.append(ranges[i])', { size: 8, mono: true, fill: '#8b949e' }) +
    txt(530, 212, 'minDistIDList.append(angle)', { size: 8, mono: true, fill: '#8b949e' }) +
    txt(848, 80, 'L54', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    txt(848, 94, 'L55', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    txt(848, 105, 'L56', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    txt(848, 119, 'L59', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    txt(848, 132, 'L60', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    txt(848, 145, 'L63', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    txt(848, 159, 'L65', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    txt(848, 186, 'L68', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    txt(848, 199, 'L69', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    txt(848, 212, 'L70', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    /* ---------- right: the two parallel lists ---------- */
    rrect(516, 306, 344, 78, 8, '#111', '#30363d') +
    txt(688, 322, 'দুই parallel list — cone-এ ধরা পড়া বীম', { anchor: 'middle', size: 8.5, weight: 700, fill: '#e6edf3' }) +
    rrect(528, 330, 118, 46, 5, '#161b22', '#7ee787') +
    txt(587, 343, 'minDistList (m)', { anchor: 'middle', size: 7, mono: true, weight: 700, fill: '#7ee787' }) +
    txt(538, 360, '0.90', { size: 9, mono: true, weight: 700, fill: '#e6edf3', id: 'bs-v1', op: 0 }) +
    txt(570, 371, '0.70', { size: 9, mono: true, weight: 700, fill: '#ff7b72', id: 'bs-v2', op: 0 }) +
    rrect(654, 330, 118, 46, 5, '#161b22', '#e3b341') +
    txt(713, 343, 'minDistIDList (deg)', { anchor: 'middle', size: 7, mono: true, weight: 700, fill: '#e3b341' }) +
    txt(664, 360, '+14', { size: 9, mono: true, weight: 700, fill: '#e6edf3', id: 'bs-v3', op: 0 }) +
    txt(696, 371, '+20', { size: 9, mono: true, weight: 700, fill: '#ff7b72', id: 'bs-v4', op: 0 }) +
    txt(790, 360, 'len', { anchor: 'middle', size: 7, mono: true, fill: '#8b949e' }) +
    txt(790, 374, '2', { anchor: 'middle', size: 11, mono: true, weight: 700, fill: '#e6edf3', id: 'bs-len' }) +
    /* ---------- bottom strip: legend + notes ---------- */
    '<path d="M48 393h7v7h-7z" fill="#7ee787"/><path d="M156 393h7v7h-7z" fill="#ff7b72"/><path d="M262 393h7v7h-7z" fill="#d2a8ff"/><path d="M368 393h7v7h-7z" fill="#6e7681"/>' +
    txt(60, 400, 'ring beam — cone-এর বাইরে', { size: 8, fill: '#8b949e' }) +
    txt(168, 400, 'min 0.70 m @ +20°', { size: 8, fill: '#8b949e' }) +
    txt(274, 400, 'দ্বিতীয় 0.90 m @ +14°', { size: 8, fill: '#8b949e' }) +
    txt(380, 400, 'ranges = 0.0 (skip)', { size: 8, fill: '#8b949e' }) +
    txt(48, 416, ' ', { size: 7.5, weight: 700, fill: '#e3b341', id: 'bs-note', op: 0 }) +
    txt(48, 430, 'LaserAngle = 45.0 (L39-40) · কঠোর &lt; মানে cone-এ 89 beam (i = 136..224) — ring-এর মান illustrative', { size: 7.5, fill: '#6e7681' }) +
    txt(450, 450, 'source: laser_Warning.py L54-L78 · laser_driver.launch.py L28-L42 (folder 10 chain)', { anchor: 'middle', size: 8, mono: true, fill: '#6e7681' })
  );
  const q = id => svg.querySelector('#' + id);
  const show = id => q(id).setAttribute('opacity', 1);
  const hide = id => q(id).setAttribute('opacity', 0);
  function bsAim(d) {
    q('bs-cur').setAttribute('transform', 'rotate(' + (-d) + ' 266 226)');
    q('bs-ri').textContent = 'i = ' + (d + 180);
    q('bs-ra').textContent = 'angle = ' + (d > 0 ? '+' : '') + d + ' deg';
    q('bs-rr').textContent = 'ranges[i] = ' + bsBeam(d).toFixed(2) + ' m';
  }
  host.caption('folder 10-এর merger দুই lidar জোড়ে এক fused 360 ring বানায়, filter সেটিকেই <code>/scan</code>-এ দেয় — তাই <code>registerScan</code>-এর <code>ranges</code> একটাই পূর্ণ বৃত্ত। এই anim-এ L54-70: সেই বৃত্ত ঘেঁটে সামনের cone-এ ধরা পড়া beam দুটো parallel list-এ তোলা; শেষে এক পলকে L72-78-এর খালি-cone পাহারা আর min। ছবিতে deg 0 = সামনে, +deg = বাঁদিক (ROS convention)।');
  host.formula('angle_i = (angle_min + angle_increment * i) * RAD2DEG   [rad -> deg, RAD2DEG = 180/pi]');
  /* --- beat 1: L54 def + L55 guard + L56 ranges --- */
  show('bs-hl1'); show('bs-hl2');
  host.caption('<b>L54</b> <code>def registerScan(self, scan_data)</code> — /scan-এর প্রতিটা message এই callback-এ আসবে (subscription L24)। <b>L55</b> পাহারা: message-টা সত্যিই <code>LaserScan</code> না হলে সোজা <code>return</code>। <b>L56</b> <code>ranges = np.array(scan_data.ranges)</code> — দূরত্বের মানগুলো numpy array-তে তোলা।');
  await host.sleep(1700);
  hide('bs-hl1'); hide('bs-hl2'); show('bs-hl3');
  host.caption('দুটো খালি list জন্মাল (<b>L59-60</b>): <code>minDistList</code> রাখবে দূরত্ব, <code>minDistIDList</code> রাখবে সেই দূরত্বের beam-এর কোণ — একই beam-এর দুটো পাশ, index-এ index। সংগ্রহের আকার folder 12-র tracker-এর হুবহু — এদের জোড়া <code>min()</code>-এর সময় কাজে লাগবে।');
  host.formula('minDistList[k] = distance of beam k  |  minDistIDList[k] = angle of beam k');
  await host.sleep(1700);
  /* --- beat 2: L63 sweep --- */
  hide('bs-hl3'); show('bs-hl4');
  host.caption('L63 <code>for i in range(len(ranges))</code> — cursor-টা i=0 (deg -180, একদম পেছনে) থেকে বেয়ে বেয়ে হাঁটে; প্রতিটি i মানে <code>ranges</code> অ্যারের একটা দূরত্ব-মান। guard-এর খোঁজও শুরু এখান থেকেই — সামনে, পেছনে সব beam-ই ঘোরা হবে।');
  await host.sleep(700);
  const bsHops = [-180, -144, -108, -72, -36, 0, 36, 72, 108, 144];
  for (let k = 0; k < bsHops.length; k++) { bsAim(bsHops[k]); await host.sleep(230); }
  /* --- beat 3: L65 formula --- */
  host.caption('L65: <code>angle = (scan_data.angle_min + scan_data.angle_increment * i) * RAD2DEG</code> — message-এ কোণ radian-এ, কিন্তু cone-এর তুলনা degree-তে; <code>RAD2DEG = 180 / math.pi</code> (L16)। এই fused ring-এ (illustrative) angle_min = -180 deg আর increment = 1 deg বীমপ্রতি, তাই angle = -180 + i।');
  host.formula('i = 192:  (-180 + 192) = +12 deg   (front-left beam)');
  hide('bs-hl4'); show('bs-hl5'); bsAim(12);
  await host.sleep(1700);
  /* --- beat 4: L68 cone gate --- */
  host.caption('FRONT cone (L68): <code>abs(angle) &lt; self.LaserAngle</code>, LaserAngle = 45.0 (L39-40) — সবুজ arc মানে ±45 deg। L58-এর comment বলে "front 90-degree cone", কিন্তু কঠোর <code>&lt;</code> বললে cone-এর পুরো পরিধি 90-এর একটু কম — author-এর কথা নয়, inequality-ই সত্যি। সঙ্গে <code>ranges[i] !=0.0</code>: 0.0 মানে beam কিছুই পায়নি — বাদ; কিন্তু <code>inf</code> (no-return) এই চেক পাস করে ফেলে — list-এ ঢোকে, তবে পাশে যেকোনো সসীম মান থাকলে inf কখনো min হতে পারে না।');
  host.formula('cone: |angle| < 45.0 deg AND ranges[i] != 0.0   ->  i = 136..224 = 89 beams');
  hide('bs-hl5'); show('bs-hl6'); show('bs-fa'); show('bs-zt'); show('bs-objBt'); show('bs-objAt');
  bsAim(66);
  await host.sleep(1800);
  /* --- beat 5: L69-70 appends --- */
  host.caption('gate পাস করলেই দুটো append (<b>L69-70</b>): দূরত্ব যায় <code>minDistList</code>-এ, কোণ যায় <code>minDistIDList</code>-এ। ডেমো ring-এ cone-এ দুটো object: 0.90 m @ +14° আর 0.70 m @ +20° (illustrative) — loop ক্রম বলে +14 আগে (i ছোট), +20 পরে; append-এর ক্রমও তাই।');
  host.formula('append pair: (0.90, +14) then (0.70, +20)  |  len(minDistList) = len(minDistIDList)');
  hide('bs-hl6'); show('bs-hl7'); show('bs-v1'); show('bs-v2'); show('bs-v3'); show('bs-v4');
  bsAim(14); await host.sleep(650);
  bsAim(20); q('bs-len').textContent = '2';
  await host.sleep(1600);
  /* --- close: L76/L78 min + argmin, then the L72-73 buzzer latch --- */
  q('bs-note').textContent = 'loop শেষ — L76 min + L78 argmin: minDist = 0.70, minDistID = +20 (0.55-এর বাইরে)';
  show('bs-note');
  host.caption('loop শেষে দুই list-এ cone-এর সব ধরা-পড়া beam। <b>L76</b> <code>minDist = min(minDistList)</code> = <b>0.70 m</b>, <b>L78</b> <code>minDistID = minDistIDList[minDistList.index(minDist)]</code> = <b>+20 deg</b> — argmin-এর মতো জোড়া; tie হলে <code>index()</code> প্রথম মিলটা ধরে = সবচেয়ে ছোট i। এই (minDist, minDistID) জোড়াই guard-এর পরের খাবার: alarm check (L89: <code>minDist &lt;= self.ResponseDist</code>, 0.55) আর spin-only PID — 0.70 এখনো 0.55-এর বাইরে, বিস্তারিত পরের part-এ।');
  host.formula('minDist = min(list) = 0.70 m  |  minDistID = list[index(minDist)] = +20 deg');
  await host.sleep(1700);
  host.caption('আর cone-এ কিছুই ধরা না পড়লে? <b>L72-73</b>: <code>if len(minDistList) == 0: return</code> — নীরব early return: কোনো <code>/cmd_vel</code> publish নেই, কোনো <code>/beep</code> write নেই (folder 12-র tracker তখন else-এ dash ছাপত — guard একদম চুপ)। ফল: motors শেষ <code>/cmd_vel</code> command-ই মেনে চলতে থাকে, আর <code>/beep</code>-এ নতুন কিছু না লেখা মানে তার শেষ মানই থেকে যায় — buzzer ON থাকা অবস্থায় সামনে খালি হয়ে গেলে সে বাজতেই থাকবে। guard-এর এই buzzer-latch ফাঁদটাই এই anim-এর শেষ কথা।');
  show('bs-latch');
  await host.sleep(1600);
};

/* ---------- alarmBuzzer ---------- */
/* ===== folder-13 v1 anim — alarmBuzzer (part 12) =====================
   laser_Warning.py L87-L95, THE alarm block — the channel the
   tracker (folder 12) never had. Source sha b1cf2d67a4d5. L87
   comment header, L88 danger-zone comment, L89 test
   `if minDist <= self.ResponseDist and minDist != 0.0:` —
   ResponseDist 0.55 born L41-42 (declare + read, "Danger Zone"
   comment in source); second clause is belt-and-suspenders: the
   cone filter L68 already excluded exact 0.0 readings. inf <= 0.55
   is False -> else -> OFF; NaN fails both comparisons -> else ->
   OFF. L90-92 `b = UInt16(); b.data = 1; pub_Buzzer.publish(b)` =
   BEEP ON; L93-L95 else `pub_Buzzer.publish(UInt16())` = default 0
   = BEEP OFF, published EVERY scan while an object is visible
   outside the zone (trailing space after the call IN SOURCE, noted
   in-card, not quoted). pub_Buzzer born L32 (/beep, UInt16, depth
   1); UInt16 import L6 ("buzzer ON/OFF message type").
   Semantics taught: /beep is a LEVEL refreshed per scan, not an
   edge. Skip paths never refresh it: empty cone L73 return, Joy
   gate L81-83 (zero Twist + return BEFORE the alarm block) — /beep
   latches its last value, the buzzer-stays-on trap; exit_pro
   L127-132 brakes /cmd_vel only, never touches /beep. No
   hysteresis: boundary 0.55 exactly -> `<=` is TRUE -> ON; a hover
   at the line toggles at scan rate (chatter; 0.55/0.56 jitter
   illustrative). Wave numbers from the canonical table
   (illustrative): C 0.48 m @ 0 deg -> beep 1, u = 0 so deadzone
   zeroes z — robot still + beeping; D 0.50 m @ -20 deg -> beep 1,
   z = -0.417; B 0.70 m @ +20 deg -> else, UInt16() = 0, z = +0.417;
   E empty front -> LATCH 1 from D; A 0.90 / F 0.80 timeline only.
   Timeline cadence illustrative. Prefix ab-, helper abX. No emoji,
   no Unicode arrows in stage strings, entities for &lt; &gt;.
   Static backbone visible at setStage; first caption + formula
   before the first await. */

ANIMS.alarmBuzzer = async function (host) {
  const svg = host.setStage(
    txt(450, 24, 'alarm: ResponseDist-এর ভেতরে এলেই বিপ — একটা level, প্রতি scan-এ refresh, L89-L95', { anchor: 'middle', size: 13.5, weight: 600, fill: '#ffb454' }) +
    /* ---------- left: code L87-L95 ---------- */
    rrect(40, 42, 302, 306, 8, '#0d1117', '#2a3442') +
    txt(54, 60, 'CODE — laser_Warning.py L87-L95', { size: 9.5, weight: 700, fill: '#e6edf3' }) +
    rrect(50, 108, 282, 88, 4, '#f85149', 'none', ' fill-opacity="0.12" id="ab-hif" opacity="0"') +
    rrect(50, 197, 282, 54, 4, '#7ee787', 'none', ' fill-opacity="0.10" id="ab-hel" opacity="0"') +
    txt(58, 84, '# --- THE ALARM LOGIC ---', { size: 7.5, mono: true, fill: '#6e7681' }) +
    txt(58, 99, '# ... inside the Danger Zone (0.55m)...', { size: 7.5, mono: true, fill: '#6e7681' }) +
    txt(88, 120, 'if minDist &lt;= self.ResponseDist and', { size: 8, mono: true, fill: '#e6edf3' }) +
    txt(100, 133, 'minDist != 0.0:', { size: 8, mono: true, fill: '#e6edf3' }) +
    txt(100, 152, 'b = UInt16()', { size: 8, mono: true, fill: '#c9d1d9' }) +
    txt(100, 171, 'b.data = 1        # 1 means BEEP!', { size: 8, mono: true, fill: '#c9d1d9' }) +
    txt(100, 190, 'self.pub_Buzzer.publish(b)', { size: 8, mono: true, fill: '#c9d1d9' }) +
    txt(88, 209, 'else:', { size: 8, mono: true, fill: '#e6edf3' }) +
    txt(100, 224, '# ... turn the buzzer off (0).', { size: 7.5, mono: true, fill: '#6e7681' }) +
    txt(100, 243, 'self.pub_Buzzer.publish(UInt16())', { size: 8, mono: true, fill: '#c9d1d9' }) +
    txt(82, 120, 'L89', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    txt(82, 152, 'L90', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    txt(82, 171, 'L91', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    txt(82, 190, 'L92', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    txt(82, 209, 'L93', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    txt(82, 243, 'L95', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    rrect(50, 258, 282, 66, 4, '#161b22', '#30363d') +
    txt(58, 272, 'দুই SKIP পথ — alarm block পর্যন্ত পৌঁছায়ই না', { size: 7.5, weight: 700, fill: '#ff7b72' }) +
    txt(58, 287, 'L73     if len(minDistList) == 0: return', { size: 7, mono: true, fill: '#c9d1d9' }) +
    txt(58, 301, 'L81-83  Joy_active: publish(Twist()) + return', { size: 7, mono: true, fill: '#c9d1d9' }) +
    txt(58, 315, 'দুই-ই /beep-এ হাত দেয় না — শেষ মান latched', { size: 7, fill: '#ff7b72', id: 'ab-skipn', op: 0 }) +
    txt(58, 338, 'L95-এর শেষে source-এ একটা ফাঁকা space আছে', { size: 6.8, fill: '#6e7681' }) +
    /* ---------- middle: distance axis ---------- */
    rrect(356, 42, 248, 306, 8, '#0d1117', '#30363d') +
    txt(480, 60, 'DISTANCE — minDist অক্ষ (m)', { anchor: 'middle', size: 9.5, weight: 700, fill: '#e6edf3' }) +
    rrect(406, 70, 148, 26, 13, '#161b22', '#30363d', ' id="ab-verd"') +
    txt(480, 87, '— শুরু হয়নি —', { anchor: 'middle', size: 8, weight: 700, fill: '#8b949e', id: 'ab-verdt' }) +
    rrect(376, 228, 114.4, 36, 3, '#f85149', 'none', ' fill-opacity="0.16"') +
    txt(433, 242, 'DANGER ZONE', { anchor: 'middle', size: 6.5, weight: 700, fill: '#ff7b72' }) +
    txt(433, 255, '0 .. 0.55 m', { anchor: 'middle', size: 6, mono: true, fill: '#ff7b72' }) +
    txt(490.4, 202, 'ResponseDist 0.55 m (L41-42)', { anchor: 'middle', size: 7, mono: true, weight: 700, fill: '#ff7b72' }) +
    line(490.4, 208, 490.4, 268, '#f85149', 1.2, ' stroke-dasharray="4 3"') +
    line(376, 264, 584, 264, '#6e7681', 1.5) +
    line(376, 264, 376, 270, '#6e7681', 1.5) +
    line(428, 264, 428, 270, '#6e7681', 1.5) +
    line(480, 264, 480, 270, '#6e7681', 1.5) +
    line(532, 264, 532, 270, '#6e7681', 1.5) +
    line(584, 264, 584, 270, '#6e7681', 1.5) +
    txt(376, 281, '0.0', { anchor: 'middle', size: 6.5, mono: true, fill: '#6e7681' }) +
    txt(428, 281, '0.25', { anchor: 'middle', size: 6.5, mono: true, fill: '#6e7681' }) +
    txt(480, 281, '0.5', { anchor: 'middle', size: 6.5, mono: true, fill: '#6e7681' }) +
    txt(532, 281, '0.75', { anchor: 'middle', size: 6.5, mono: true, fill: '#6e7681' }) +
    txt(584, 281, '1.0', { anchor: 'middle', size: 6.5, mono: true, fill: '#6e7681' }) +
    rrect(362, 236, 16, 20, 3, '#21262d', '#8b949e') +
    '<path d="M378 240L388 246L378 252Z" fill="#4fc3f7"/>' +
    txt(370, 296, 'robot', { anchor: 'middle', size: 7, fill: '#8b949e' }) +
    circ(475.8, 246, 6, '#e3b341', ' id="ab-obj" opacity="0" stroke="#0d1117" stroke-width="1"') +
    txt(475.8, 222, '0.48 m — Wave C', { anchor: 'middle', size: 7.5, weight: 700, mono: true, fill: '#e3b341', id: 'ab-objt', op: 0 }) +
    txt(480, 316, 'minDist = —', { anchor: 'middle', size: 8, mono: true, fill: '#e6edf3', id: 'ab-dist', op: 0 }) +
    txt(480, 332, '—', { anchor: 'middle', size: 7.5, fill: '#8b949e', id: 'ab-behav', op: 0 }) +
    txt(480, 344, '—', { anchor: 'middle', size: 7, mono: true, fill: '#7ee787', id: 'ab-cmp', op: 0 }) +
    /* ---------- right: buzzer + /beep channel ---------- */
    rrect(618, 42, 242, 306, 8, '#0d1117', '#2a3442') +
    txt(739, 60, 'CHANNEL — pub_Buzzer -&gt; /beep', { anchor: 'middle', size: 9.5, weight: 700, fill: '#e6edf3' }) +
    circ(700, 128, 18, '#161b22', ' id="ab-bz" stroke="#30363d" stroke-width="2"') +
    circ(700, 128, 7, '#30363d', ' id="ab-bzc"') +
    path('M678 114 A 26 26 0 0 1 722 114', '#ff7b72', 2, ' id="ab-w1" opacity="0"') +
    path('M666 108 A 36 36 0 0 1 734 108', '#ff7b72', 2, ' id="ab-w2" opacity="0"') +
    path('M656 104 A 46 46 0 0 1 744 104', '#ff7b72', 1.6, ' id="ab-w3" opacity="0"') +
    txt(726, 124, 'নীরব', { size: 8, weight: 700, fill: '#8b949e', id: 'ab-bzt' }) +
    txt(700, 166, 'buzzer', { anchor: 'middle', size: 7, fill: '#8b949e' }) +
    line(700, 172, 700, 196, '#6e7681', 1.5) +
    txt(710, 188, '/beep', { size: 7, mono: true, fill: '#ff7b72' }) +
    rrect(644, 198, 190, 26, 13, '#161b22', '#30363d', ' id="ab-chip"') +
    txt(739, 215, 'UInt16 data = —', { anchor: 'middle', size: 8.5, weight: 700, mono: true, fill: '#8b949e', id: 'ab-chipt' }) +
    txt(739, 240, 'publish এসেছে: এখনো নয়', { anchor: 'middle', size: 7.5, fill: '#8b949e', id: 'ab-pubsrc', op: 0 }) +
    txt(739, 254, 'pub_Buzzer জন্ম L32-এ · QoS depth 1', { anchor: 'middle', size: 6.8, fill: '#6e7681' }) +
    txt(739, 267, 'UInt16 import L6 — buzzer ON/OFF message type', { anchor: 'middle', size: 6.8, fill: '#6e7681' }) +
    rrect(630, 276, 218, 66, 4, '#161b22', '#f85149', ' id="ab-trap" opacity="0"') +
    txt(739, 291, 'LATCH ফাঁদ — Wave E', { anchor: 'middle', size: 7.5, weight: 700, fill: '#ff7b72', id: 'ab-trapt', op: 0 }) +
    txt(739, 305, 'সামনে খালি: L73 return — কোনো publish নেই', { anchor: 'middle', size: 7, fill: '#c9d1d9', id: 'ab-trap2', op: 0 }) +
    txt(739, 317, 'Joy L81-83-ও একই; exit_pro-ও /beep ছোঁয় না', { anchor: 'middle', size: 7, fill: '#c9d1d9', id: 'ab-trap3', op: 0 }) +
    txt(739, 331, '/beep শেষ মানে আটকে থাকে — বিপ চলতেই থাকে', { anchor: 'middle', size: 7, weight: 700, fill: '#ff7b72', id: 'ab-trap4', op: 0 }) +
    /* ---------- bottom: /beep timeline ---------- */
    rrect(40, 356, 820, 84, 8, '#111', '#30363d') +
    txt(60, 372, 'LEVEL, NOT EDGE — /beep-এর সময়রেখা (illustrative)', { size: 8.5, weight: 700, fill: '#e6edf3' }) +
    txt(840, 372, 'লাল = ON, ধূসর = OFF, ড্যাশ = latched', { anchor: 'end', size: 7, fill: '#8b949e' }) +
    txt(88, 390, 'ON', { anchor: 'end', size: 6.5, weight: 700, fill: '#ff7b72' }) +
    txt(88, 418, 'OFF', { anchor: 'end', size: 6.5, fill: '#6e7681' }) +
    circ(96, 414, 2.5, '#4fc3f7') +
    circ(226, 414, 2.5, '#4fc3f7') +
    circ(356, 414, 2.5, '#4fc3f7') +
    circ(486, 414, 2.5, '#4fc3f7') +
    circ(616, 414, 2.5, '#4fc3f7') +
    circ(716, 414, 2.5, '#4fc3f7') +
    circ(816, 414, 2.5, '#4fc3f7') +
    line(96, 414, 226, 414, '#6e7681', 2.5) +
    line(226, 414, 356, 414, '#6e7681', 2.5) +
    line(356, 386, 356, 414, '#ff7b72', 2) +
    line(356, 386, 486, 386, '#ff7b72', 2.5) +
    line(486, 386, 616, 386, '#ff7b72', 2.5) +
    line(616, 386, 716, 386, '#ff7b72', 2.5, ' stroke-dasharray="5 4" id="ab-tE"') +
    line(716, 386, 716, 414, '#ff7b72', 2) +
    line(716, 414, 816, 414, '#6e7681', 2.5) +
    txt(161, 432, 'A 0.90', { anchor: 'middle', size: 6.5, mono: true, fill: '#6e7681' }) +
    txt(291, 432, 'B 0.70', { anchor: 'middle', size: 6.5, mono: true, fill: '#6e7681' }) +
    txt(421, 432, 'C 0.48', { anchor: 'middle', size: 6.5, mono: true, fill: '#ff7b72' }) +
    txt(551, 432, 'D 0.50', { anchor: 'middle', size: 6.5, mono: true, fill: '#ff7b72' }) +
    txt(666, 432, 'E খালি', { anchor: 'middle', size: 6.5, mono: true, fill: '#ff7b72' }) +
    txt(766, 432, 'F 0.80', { anchor: 'middle', size: 6.5, mono: true, fill: '#6e7681' }) +
    txt(666, 378, 'latched — publish নেই', { anchor: 'middle', size: 6, fill: '#ff7b72' }) +
    rrect(348, 368, 146, 60, 4, '#f85149', 'none', ' fill-opacity="0.10" id="ab-cur" opacity="0"') +
    txt(450, 452, 'source: laser_Warning.py L87-L95 · ResponseDist L41-42 · pub_Buzzer L32 · UInt16 L6 · skip পথ L73 + L81-83 · exit_pro L127-132', { anchor: 'middle', size: 7.5, mono: true, fill: '#6e7681' })
  );
  const q = id => svg.querySelector('#' + id);
  const show = i => q(i).setAttribute('opacity', 1);
  const hide = i => q(i).setAttribute('opacity', 0);
  const abX = d => 376 + 208 * d;
  /* buzzer + chip + arcs as one LEVEL state */
  const abBeep = (on, label) => {
    q('ab-bzc').setAttribute('fill', on ? '#ff7b72' : '#30363d');
    q('ab-bz').setAttribute('stroke', on ? '#ff7b72' : '#30363d');
    q('ab-bzt').textContent = label || (on ? 'বিপ চালু' : 'নীরব');
    q('ab-bzt').setAttribute('fill', on ? '#ff7b72' : '#8b949e');
    q('ab-chipt').textContent = 'UInt16 data = ' + (on ? '1' : '0');
    q('ab-chipt').setAttribute('fill', on ? '#ff7b72' : '#8b949e');
    q('ab-chip').setAttribute('stroke', on ? '#f85149' : '#30363d');
    ['ab-w1', 'ab-w2', 'ab-w3'].forEach(i => { if (on) show(i); else hide(i); });
  };
  const abVerdict = (t, col) => {
    q('ab-verdt').textContent = t;
    q('ab-verdt').setAttribute('fill', col);
    q('ab-verd').setAttribute('stroke', col);
  };
  const abObj = (d, label) => {
    const x = abX(d);
    q('ab-obj').setAttribute('cx', x);
    q('ab-objt').setAttribute('x', x);
    q('ab-objt').textContent = label;
  };
  const abCur = (x, w) => {
    q('ab-cur').setAttribute('x', x);
    q('ab-cur').setAttribute('width', w);
    show('ab-cur');
  };

  host.caption('guard-এর স্বাক্ষর — <b>alarm block</b>, part 12। বাঁয়ে L87-L95-এর কোড, মাঝে minDist-অক্ষ, ডানে <code>/beep</code> চ্যানেল, নিচে পুরো সময়রেখা। প্রশ্ন একটাই: সামনের সবচেয়ে কাছের object-টা <code>ResponseDist</code> <b>0.55 m</b>-এর (L41-42) ভেতরে কি না। ভেতরে হলে <code>UInt16</code> মান 1, বাইরে হলে 0 — আর দুটোই <b>প্রতি scan-এ নতুন করে লেখা হয়</b>: এটা level, edge নয়।');
  host.formula('alarm = (minDist &lt;= 0.55 and minDist != 0.0) ? /beep 1 : /beep 0   [level, refreshed every scan]');
  await host.sleep(1800);

  /* --- beat 1: Wave C inside -> ON --- */
  show('ab-hif'); show('ab-obj'); show('ab-objt'); show('ab-dist'); show('ab-behav'); show('ab-cmp'); show('ab-pubsrc');
  abObj(0.48, '0.48 m — Wave C');
  q('ab-dist').textContent = 'minDist = 0.48 m · minDistID = 0.0°';
  q('ab-cmp').textContent = '0.48 &lt;= 0.55 -&gt; TRUE   and   0.48 != 0.0 -&gt; TRUE';
  q('ab-behav').textContent = 'robot: দাঁড়িয়ে বিপ — u = 0, deadzone-এ z = 0.0';
  q('ab-pubsrc').textContent = 'publish এসেছে: L92 (b.data = 1)';
  abVerdict('ON — বিপ', '#ff7b72');
  abBeep(true);
  abCur(348, 146);
  host.caption('<b>Wave C</b>: object হুবহু সামনে, <b>0.48 m</b> — লাল zone-এর ভেতরে। <b>L89</b>-এর দুই শর্ত: <code>0.48 &lt;= 0.55</code> সত্য, <code>0.48 != 0.0</code>-ও সত্য — তাই ভেতরের branch: <code>b = UInt16()</code>, <code>b.data = 1</code> (L90-91), <code>pub_Buzzer.publish(b)</code> (L92)। <b>/beep = 1, বিপ ON।</b> আর এই wave-এ ঘোরার হিসাবটাও মনে করো: কোণ 0° বলে u = 0, deadzone-এ পড়ে <code>angular.z = 0.0</code>, আর <code>linear.x</code> এই file-এ কোনোদিন সেট-ই হয় না (L123) — robot দাঁড়িয়ে দাঁড়িয়েই বিপ দেয় (z-সংখ্যা illustrative)।');
  host.formula('C: 0.48 &lt;= 0.55 and 0.48 != 0.0 -> b.data = 1 -> /beep ON  |  z = 0.0 — দাঁড়িয়ে বিপ');
  await host.sleep(2400);

  /* --- beat 2: Wave D still inside --- */
  abObj(0.50, '0.50 m — Wave D');
  q('ab-dist').textContent = 'minDist = 0.50 m · minDistID = -20.0°';
  q('ab-cmp').textContent = '0.50 &lt;= 0.55 -&gt; TRUE   and   0.50 != 0.0 -&gt; TRUE';
  q('ab-behav').textContent = 'robot: ডানে ঘুরছে z = -0.417 (illustrative), বিপ চালু';
  q('ab-pubsrc').textContent = 'publish এসেছে: L92 (b.data = 1)';
  abCur(478, 146);
  host.caption('<b>Wave D</b>: object এবার <b>0.50 m</b>, ডানে -20°। দূরত্ব এখনো 0.55-এর ভেতরে — রায় একই: <b>/beep = 1</b>। খেয়াল করো, alarm-এর হিসাবে <code>minDistID</code>-র <b>কোনো ভূমিকাই নেই</b> — কোণ যা-ই হোক, দূরত্ব ভেতরে থাকলেই বিপ। এই scan-এ ঘোরার দিক বদলে গেছে (<code>z = -0.417</code>, illustrative), কিন্তু বিপের অবস্থা বদলায়নি — ঘোরানো আর সতর্কধ্বনি দুটো সম্পূর্ণ আলাদা পথ।');
  host.formula('D: 0.50 &lt;= 0.55 -> /beep ON  |  angle irrelevant — z = -0.417 (ill), beep unchanged');
  await host.sleep(2200);

  /* --- beat 3: boundary 0.55 — inclusive, no hysteresis, chatter --- */
  abObj(0.55, '0.55 m — সীমানায়');
  q('ab-dist').textContent = 'minDist = 0.55 m · সীমানায় দোলা (illustrative)';
  q('ab-cmp').textContent = '0.55 &lt;= 0.55 -&gt; TRUE (সমতাও গ্রহণ)  ·  0.56 &lt;= 0.55 -&gt; FALSE';
  q('ab-behav').textContent = 'robot: সীমানায় — বিপ দ্রুত টগল (chatter)';
  abCur(470, 160);
  host.caption('এবার সীমানার রহস্য। Object ঠিক <b>0.55 m</b>-এ ঝুলছে ধরে নাও (illustrative)। <code>&lt;=</code> চিহ্নটা <b>সমতাও গ্রহণ করে</b> — 0.55 হলে শর্ত সত্য, বিপ ON। কিন্তু সামান্য নড়লেই 0.56 — শর্ত মিথ্যা, OFF। lidar-এর মাপে এমন সূক্ষ্ম দোলা সাধারণ, আর code-এ <b>কোনো hysteresis নেই</b> (ON আর OFF-এর আলাদা দুটো সীমা নেই) — তাই সীমানায় বিপ scan-এর গতিতে টগল করতে থাকে: <b>chatter</b>।');
  host.formula('boundary: 0.55 &lt;= 0.55 = TRUE -> ON  |  0.56 &lt;= 0.55 = FALSE -> OFF  |  no hysteresis -> chatter');
  await host.sleep(2300);
  abBeep(true);
  await host.sleep(420);
  abObj(0.56, '0.56 m — সীমানার ওপারে');
  abBeep(false);
  await host.sleep(420);
  abObj(0.55, '0.55 m — সীমানায়');
  abBeep(true);
  await host.sleep(420);
  abObj(0.56, '0.56 m — সীমানার ওপারে');
  abBeep(false);
  await host.sleep(420);
  abObj(0.55, '0.55 m — সীমানায়');
  abBeep(true, 'টগল... টগল...');
  q('ab-chipt').textContent = 'UInt16 data = ?';
  host.caption('চ্যাটার চোখের সামনে: একই জায়গায় দাঁড়িয়ে object, আর বিপ অন-অফ-অন-অফ — প্রতি scan-এ নতুন রায়, কোনো স্মৃতি নেই। সীমানা এড়াতে হলে দরকার দুই সীমার নকশা (যেমন ON 0.50, OFF 0.60) — এই file-এ তা নেই; 0.55 একাই দুই দিকের রায় দেয়।');
  await host.sleep(2100);

  /* --- beat 4: Wave B outside -> else publishes 0 --- */
  show('ab-hel');
  abObj(0.70, '0.70 m — Wave B');
  q('ab-dist').textContent = 'minDist = 0.70 m · minDistID = +20.0°';
  q('ab-cmp').textContent = '0.70 &lt;= 0.55 -&gt; FALSE — দ্বিতীয় শর্ত দেখাই হয় না';
  q('ab-behav').textContent = 'robot: বাঁয়ে ঘুরছে z = +0.417 (illustrative), বিপ বন্ধ';
  q('ab-pubsrc').textContent = 'publish এসেছে: L95 (UInt16() = 0)';
  abVerdict('OFF — নীরব', '#8b949e');
  abBeep(false);
  abCur(218, 146);
  host.caption('<b>Wave B</b>: object <b>0.70 m</b>-এ — zone-এর বাইরে। প্রথম শর্তই মিথ্যা, তাই <b>else</b> (L93): <code>pub_Buzzer.publish(UInt16())</code> (L95) — default-নির্মিত <code>UInt16</code>-এর মান <b>0</b>, বিপ OFF। দুটো কথা মনে রাখো। <b>এক</b>, OFF-ও প্রতি scan-এ publish হয় — নীরবতা মানে চুপ করে যাওয়া নয়, প্রতিবার নতুন করে 0 লেখা। <b>দুই</b>, L89-এর দ্বিতীয় শর্ত <code>minDist != 0.0</code> আসলে belt-and-suspenders — cone-ফিল্টার (L68) আগেই হুবহু 0.0 বাদ দিয়েছে। আর <code>inf</code>? <code>inf &lt;= 0.55</code> মিথ্যা — else-এ OFF; <code>NaN</code> দুই তুলনাতেই ব্যর্থ — একইভাবে else, OFF।');
  host.formula('B: 0.70 &lt;= 0.55 FALSE -> else L95: UInt16() = 0 -> /beep OFF  |  inf/NaN -> else -> OFF');
  await host.sleep(2500);

  /* --- beat 5: Wave E empty front -> no publish, latch trap --- */
  hide('ab-obj'); hide('ab-objt');
  q('ab-dist').textContent = 'minDist = নেই — minDistList খালি (L73)';
  q('ab-cmp').textContent = 'L89 পর্যন্ত পৌঁছায়ইনি — L73-এ return';
  q('ab-behav').textContent = 'robot: শেষ আদেশেই চলে; বিপ থামে না';
  q('ab-pubsrc').textContent = 'publish: এই scan-এ কোনোটাই নয়';
  abVerdict('LATCH — 1 আটকে', '#d2a8ff');
  abBeep(true, 'latched — কেউ লেখেনি');
  q('ab-chipt').textContent = 'UInt16 data = 1 (পুরনো)';
  q('ab-chipt').setAttribute('fill', '#d2a8ff');
  show('ab-trap'); show('ab-trapt'); show('ab-trap2'); show('ab-trap3'); show('ab-trap4'); show('ab-skipn');
  abCur(608, 116);
  host.caption('<b>Wave E</b>: সামনের cone একদম খালি। <code>registerScan</code> <b>L73</b>-এই <code>return</code> করে — alarm block পর্যন্ত পৌঁছায়ই না, কোনো publish নেই। তাহলে <code>/beep</code>? সে আগের মানেই বসে থাকে — Wave D-এর <b>1</b>। <b>Object নেই তবু বিপ বাজতেই থাকে।</b> একই ফাঁদ Joy gate-এও (L81-83 — প্রতি scan-এ zero <code>Twist()</code> ঠেলে alarm-এর আগেই return), এমনকি Ctrl+C-র <code>exit_pro</code> brake-ও (L127-132) শুধু <code>/cmd_vel</code> লেখে, <code>/beep</code> ছোঁয় না। folder 12-এর tracker-এ এই ফাঁদটা ছিল শুধু চাকার — guard-এ এসে কণ্ঠও আটকে যায়।');
  host.formula('E: L73 return -> NO publish -> /beep stays 1 (latched)  |  Joy L81-83 + exit_pro L127-132: same gap');
  await host.sleep(2500);

  /* --- beat 6: close — the level rule --- */
  host.caption('পুরো গল্পটা এক লাইনে: <b>/beep একটা level, edge নয়</b>। Object ভেতরে থাকার প্রতিটি scan-এ 1 লেখা হয়, বাইরের প্রতিটি scan-এ 0 — নিজে নিজে "মনে" থাকে না, প্রতি বার নতুন করে লেখে। আর যে scan-এ লেখাই হয় না — খালি cone, Joy, বা node-এর মৃত্যু — সেখানে সর্বশেষ লেখাটাই জমে থাকে। সীমানায় <code>&lt;=</code>-এর সমতা আর hysteresis-এর অনুপস্থিতি মিলে chatter বানায়। এবার বাকি শুধু ঘোরানোর হিসাব — যার জন্ম হয়ে গেছে এই block-এর ঠিক পরেই, L98 থেকে।');
  host.formula('level rule: inside -> write 1 · outside -> write 0 · no write -> last value stays  |  0.55 itself = ON');
  await host.sleep(2100);
};

/* ---------- pidDial ---------- */
/* ===== folder-13 anim — pidDial (part 13) ============================
   laser_Warning.py L96-L110, the SINGLE-PID heart (the tracker's
   folder-12 twin had two). Left: code card L96-L110 (L98 velocity =
   Twist(), L99 print minDistID, L103 angular call, L106-110 sign
   branch). Right: ONE PID card — ang SinglePID(3.0, 0.0, 5.0) born
   L48, constructed once, state persists across scans; the tracker's
   freed LIN space goes to a wider u-dial (0..2.0, ceiling tick
   1.875) + a Kp/Ki/Kd gain strip + the L47 cross-folder note
   "tuned a bit more aggressively than the tracker" (REAL: tracker
   = folder 12 ang SinglePID(2.0, 0.0, 2.0)). NO snap (tracker L96
   snapped minDist := 0.55 before its linear PID) and NO linear PID
   — linear.x is never assigned anywhere. Wave-B illustrative
   numbers: minDist 0.70, minDistID +20 -> e = 20/72 = 0.278 ->
   u = 3*0.278 = 0.833 -> z = +0.833 (pre-damping); Wave D 0.50 m
   @ -20 deg -> u = 0.833 -> z = -0.833. abs() makes the error
   sign-free, target 0 (L102 comment); 72 is a bare magic number
   the file never explains; ceiling |a| -> 45- -> u -> 3*(45/72) =
   1.875. Optional one-line Kd caveat: large Kd = 5 adds a
   same-sign transient on the first call after a scene change
   (illustrative). STOPS at ang_pid_compute + sign branch —
   deadzone/damping/publish belong to cmdVelVectors. Prefix pd-.
   No emoji, no arrow chars in stage strings, entities for
   &lt; &gt;. */

ANIMS.pidDial = async function (host) {
  const svg = host.setStage(
    txt(450, 26, 'একটাই PID: মুখ ঘোরাও (angular) — linear PID নেই, snap নেই — L98-L99, L103, L106-110', { anchor: 'middle', size: 13.5, weight: 600, fill: '#ffb454' }) +
    /* ---------- left: code L96-L110 ---------- */
    rrect(40, 44, 340, 316, 8, '#0d1117', '#2a3442') +
    txt(56, 62, 'CODE — laser_Warning.py L96-L110', { size: 9.5, weight: 700, fill: '#e6edf3' }) +
    rrect(50, 104, 320, 29, 3, '#21262d', 'none', ' id="pd-hl1" opacity="0"') +
    rrect(50, 168, 320, 29, 3, '#21262d', 'none', ' id="pd-hl2" opacity="0"') +
    rrect(50, 216, 320, 29, 3, '#21262d', 'none', ' id="pd-hl3" opacity="0"') +
    rrect(50, 253, 320, 29, 3, '#21262d', 'none', ' id="pd-hl4" opacity="0"') +
    txt(58, 86, '# --- THE TRACKING LOGIC ---', { size: 7, mono: true, fill: '#6e7681' }) +
    txt(58, 104, 'velocity = Twist()', { size: 8, mono: true, fill: '#c9d1d9' }) +
    txt(368, 104, 'L98', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    txt(58, 117, 'print("minDistID: ", minDistID)', { size: 8, mono: true, fill: '#c9d1d9' }) +
    txt(368, 117, 'L99', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    txt(58, 134, '# Calculate how much to turn to face the object.', { size: 7, mono: true, fill: '#6e7681' }) +
    txt(58, 147, '# Target Angle is 0 ... Current Angle is minDistID', { size: 7, mono: true, fill: '#6e7681' }) +
    txt(368, 147, 'L101-102', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    txt(58, 168, 'ang_pid_compute = self.ang_pid.pid_compute(', { size: 8, mono: true, fill: '#c9d1d9' }) +
    txt(58, 181, '    abs(minDistID) / 72, 0)', { size: 8, mono: true, fill: '#c9d1d9' }) +
    txt(368, 181, 'L103', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    txt(58, 216, 'if 0 &lt; minDistID :', { size: 8, mono: true, fill: '#c9d1d9' }) +
    txt(58, 230, 'velocity.angular.z = ang_pid_compute', { size: 8, mono: true, fill: '#c9d1d9' }) +
    txt(368, 230, 'L106-107', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    txt(58, 253, 'elif minDistID &lt; 0:', { size: 8, mono: true, fill: '#c9d1d9' }) +
    txt(58, 267, 'velocity.angular.z = -ang_pid_compute', { size: 8, mono: true, fill: '#c9d1d9' }) +
    txt(368, 267, 'L109-110', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    txt(58, 290, 'L105/L108-এর comment: বাঁ = positive angle, ডান = negative', { size: 7, fill: '#6e7681' }) +
    txt(58, 306, 'minDistID = 0.0 হলে দুই branch-ই মিস — z জন্মলগ্ন 0.0-ই', { size: 7, fill: '#6e7681', id: 'pd-zero', op: 0 }) +
    txt(58, 330, 'minDist = 0.70 m · minDistID = +20° (Wave B, illustrative)', { size: 7.5, weight: 700, mono: true, fill: '#e3b341', id: 'pd-wave', op: 0 }) +
    txt(58, 348, 'vendor SinglePID-এর ভেতরটা এই folder-এ নেই — pid ফল Kp-only illustrative', { size: 6.8, fill: '#6e7681' }) +
    /* ---------- right-top: the ONE ANG PID card (tracker-এর LIN জায়গা মিলে বড়) ---------- */
    rrect(396, 44, 464, 148, 8, '#0d1117', '#e3b341') +
    txt(408, 62, 'ANG PID — SinglePID(3.0, 0.0, 5.0) — guard-এর একমাত্র PID', { size: 8.5, mono: true, weight: 700, fill: '#e3b341' }) +
    txt(408, 74, 'জন্ম L48-এ, একবারই — state scan-এ স্ক্যানে বাঁচে', { size: 6.8, fill: '#8b949e' }) +
    rrect(408, 82, 224, 16, 3, '#161b22', '#30363d') +
    txt(414, 93, 'call: pid_compute(abs(minDistID) / 72, 0)', { size: 7, mono: true, fill: '#c9d1d9' }) +
    txt(638, 92, 'gains:', { anchor: 'end', size: 6.8, fill: '#8b949e' }) +
    rrect(644, 82, 66, 14, 3, '#161b22', '#30363d') +
    txt(677, 92, 'Kp = 3.0', { anchor: 'middle', size: 7, mono: true, fill: '#c9d1d9' }) +
    rrect(714, 82, 66, 14, 3, '#161b22', '#30363d') +
    txt(747, 92, 'Ki = 0.0', { anchor: 'middle', size: 7, mono: true, fill: '#c9d1d9' }) +
    rrect(784, 82, 64, 14, 3, '#161b22', '#30363d') +
    txt(816, 92, 'Kd = 5.0', { anchor: 'middle', size: 7, mono: true, fill: '#c9d1d9' }) +
    rrect(408, 102, 140, 14, 3, '#161b22', '#30363d', ' id="pd-aeB" opacity="0"') +
    txt(414, 112, 'e = abs(+20)/72 = 0.278', { size: 7, mono: true, fill: '#8b949e', id: 'pd-ae', op: 0 }) +
    rrect(554, 102, 150, 14, 3, '#161b22', '#30363d', ' id="pd-auB" opacity="0"') +
    txt(560, 112, 'u ~= 3.0 * 0.278 = 0.833', { size: 7, mono: true, fill: '#8b949e', id: 'pd-au', op: 0 }) +
    txt(644, 112, 'L47 comment: tracker-এর (2, 0, 2)-এর চেয়ে aggressive', { size: 6.8, fill: '#8b949e' }) +
    '<path d="M420 142L838 142" stroke="#30363d" stroke-width="2"/>' +
    txt(420, 136, '0', { size: 6.5, mono: true, fill: '#6e7681' }) +
    txt(629, 136, '1.0', { anchor: 'middle', size: 6.5, mono: true, fill: '#6e7681' }) +
    txt(838, 136, '2.0', { anchor: 'end', size: 6.5, mono: true, fill: '#6e7681' }) +
    '<path d="M812 135L812 149" stroke="#f85149" stroke-width="1.5" stroke-dasharray="3 2" id="pd-ctick" opacity="0"/>' +
    txt(812, 130, 'ceiling 1.875', { anchor: 'middle', size: 6, mono: true, fill: '#ff7b72', id: 'pd-ceil', op: 0 }) +
    '<path d="M420 142L594 142" stroke="#e3b341" stroke-width="3" id="pd-an" opacity="0"/>' +
    circ(594, 142, 4, '#e3b341', ' id="pd-and" opacity="0"') +
    txt(594, 158, 'u = 0.833 (magnitude)', { anchor: 'middle', size: 6.5, mono: true, fill: '#8b949e', id: 'pd-ant', op: 0 }) +
    rrect(408, 166, 226, 18, 9, '#161b22', '#e3b341', ' id="pd-axB" opacity="0"') +
    txt(521, 178, 'ang_pid_compute = 0.833 (pre-damping)', { anchor: 'middle', size: 7.5, mono: true, weight: 700, fill: '#e3b341', id: 'pd-ax', op: 0 }) +
    txt(712, 178, 'target = 0 — সোজা সামনে (L102)', { size: 6.8, fill: '#8b949e' }) +
    /* ---------- right-middle: sign branch ---------- */
    rrect(396, 200, 464, 96, 8, '#111', '#30363d') +
    txt(408, 218, 'SIGN BRANCH — L106-110: direction ফেরাও abs() যা ফেলে দিয়েছিল', { size: 8.5, weight: 700, fill: '#e6edf3' }) +
    rrect(408, 226, 144, 26, 5, '#161b22', '#4fc3f7', ' id="pd-br1" opacity="0"') +
    txt(416, 238, '0 &lt; minDistID  (+20)', { size: 7.5, mono: true, weight: 700, fill: '#4fc3f7' }) +
    txt(416, 249, 'z = +0.833 — বাঁ CCW', { size: 7.5, mono: true, fill: '#4fc3f7' }) +
    rrect(558, 226, 144, 26, 5, '#161b22', '#e3b341', ' id="pd-br2" opacity="0"') +
    txt(566, 238, 'minDistID &lt; 0  (-20)', { size: 7.5, mono: true, weight: 700, fill: '#e3b341' }) +
    txt(566, 249, 'z = -0.833 — ডান CW', { size: 7.5, mono: true, fill: '#e3b341' }) +
    rrect(708, 226, 140, 26, 5, '#161b22', '#30363d', ' id="pd-br3" opacity="0"') +
    txt(716, 238, 'minDistID == 0.0', { size: 7.5, mono: true, weight: 700, fill: '#8b949e' }) +
    txt(716, 249, 'কোনোটাই না — z = 0.0', { size: 7.5, mono: true, fill: '#8b949e' }) +
    txt(408, 272, 'ROS নিয়ম: ধনাত্মক angular.z = CCW = বাঁয়ে ঘোরা — L105/L108-এর comment-ই বলছে সেটা', { size: 7, fill: '#8b949e', id: 'pd-bnote', op: 0 }) +
    txt(408, 286, 'দুই branch-এ |z| সমান 0.833 — শুধু চিহ্ন বদলায়, PID একবারই চলে', { size: 7, fill: '#8b949e', id: 'pd-bnote2', op: 0 }) +
    /* ---------- right-bottom: warnings ---------- */
    rrect(396, 304, 464, 56, 8, '#0d1117', '#f85149') +
    txt(408, 322, 'snap নেই, linear PID নেই', { size: 8.5, weight: 700, fill: '#ff7b72' }) +
    txt(408, 336, 'tracker (folder 12)-এর L96 snap আর lin_pid এই file-এ নেই —', { size: 7.5, fill: '#c9d1d9' }) +
    txt(408, 348, 'linear.x কেউ লেখেই না: Twist()-এর জন্মলগ্ন 0.0-ই থাকে, শুধু ঘোরা', { size: 7.5, fill: '#c9d1d9' }) +
    txt(700, 322, '/72 = magic number', { anchor: 'middle', size: 8.5, weight: 700, fill: '#d2a8ff' }) +
    txt(700, 336, 'file কোথাও 72 ব্যাখ্যা করে না — শুধু কোণকে ছোট', { anchor: 'middle', size: 7.5, fill: '#c9d1d9' }) +
    txt(700, 348, 'সংখ্যায় নামায়; কার্যকর সর্বোচ্চ e &lt; 45/72 = 0.625', { anchor: 'middle', size: 7.5, fill: '#c9d1d9' }) +
    txt(450, 386, 'রঙ-নিয়ম: হলুদ = angular channel (একটাই PID), নীল = বাঁ, কমলা = ডান, লাল = সতর্কতা', { anchor: 'middle', size: 8, fill: '#8b949e' }) +
    txt(450, 440, 'source: laser_Warning.py L96-L110 · ang_pid L48 (3.0, 0.0, 5.0) · comment L47 · RAD2DEG L16', { anchor: 'middle', size: 7.5, mono: true, fill: '#6e7681' })
  );
  const q = id => svg.querySelector('#' + id);
  const show = ids => ids.forEach(i => q(i).setAttribute('opacity', 1));
  host.caption('registerScan-এর হিসাবের হৃদয় — এবার একটাই PID controller, একটাই প্রশ্ন। Tracker-এ (folder 12) দুটো PID ছিল — দূরত্ব মেলানো আর মুখ ঘোরানো; guard-এ <code>lin_pid</code> নেই, snap নেই — শুধু <code>ang_pid</code> (L48) জিজ্ঞেস করে object মুখ থেকে কত বাঁয়ে-ডানে। Constructor-এ একবার জন্মেছে — ভেতরের state scan-এ স্ক্যানে বেঁচে থাকে।');
  host.formula('ang_pid = SinglePID(3.0, 0.0, 5.0) @L48  [state persists]  |  no lin_pid, no snap — tracker-এর L96 snap এখানে নেই');
  await host.sleep(1700);
  /* --- beat 1: L98-99 fresh Twist + print --- */
  show(['pd-hl1', 'pd-wave']);
  host.caption('<b>L98</b>: <code>velocity = Twist()</code> — প্রতি scan-এ টাটকা একটা Twist, সব ঘর জন্মলগ্ন 0.0। <b>L99</b> console-এ minDistID ছাপে। Wave B (illustrative): minDist = 0.70 m, minDistID = +20 — object বাঁয়ে। খেয়াল রেখো: এই পুরো block-এ <code>linear.x</code> কেউ লেখেই না — এই anim স্রেফ <code>ang_pid_compute</code> আর sign branch-এ থেমে যাবে; deadzone, damping, publish পরের part-ের ব্যাপার।');
  host.formula('Wave B (illustrative): minDist = 0.70 m · minDistID = +20 deg  |  linear.x: never assigned (no lin_pid)');
  await host.sleep(2100);
  /* --- beat 2: L103 the one compute --- */
  show(['pd-hl2', 'pd-aeB', 'pd-ae', 'pd-auB', 'pd-au', 'pd-an', 'pd-and', 'pd-ant', 'pd-axB', 'pd-ax']);
  host.caption('<b>L103</b>: <code>ang_pid_compute = self.ang_pid.pid_compute(abs(minDistID) / 72, 0)</code> — <code>abs()</code> কোণের চিহ্ন ছুড়ে দেয় (দিক পরের branch-এ ফিরবে), target 0 অর্থাৎ সোজা সামনে (L102-এর comment)। <code>/ 72</code>? File কোথাও ব্যাখ্যা করে না — bare magic number, কাজ শুধু কোণকে ছোট সংখ্যায় নামানো। হিসাব (Kp-only view, illustrative — vendor <code>SinglePID</code>-এর ভেতরটা এই folder-এ নেই): 20/72 = 0.278, u ~= 3.0 × 0.278 = <b>0.833</b>।');
  host.formula('ang_pid_compute ~= 3.0 * (abs(+20)/72 - 0) = 3.0 * 0.278 = 0.833   [72 = magic, unexplained]');
  await host.sleep(2100);
  /* --- beat 3: L106-107 left --- */
  show(['pd-hl3', 'pd-br1', 'pd-bnote']);
  host.caption('এবার দিক ফেরানো — <b>L106-107</b>: <code>if 0 &lt; minDistID : velocity.angular.z = ang_pid_compute</code>। Wave B-তে minDistID = +20 (বাঁয়ে), তাই <code>angular.z = +0.833</code> — ROS-এ ধনাত্মক angular.z মানে CCW মানে বাঁয়ে ঘোরা (L105-এর comment-ই বলছে)। Object যেদিকে, মুখ সেদিকে — এটা মুখ মেলানোর হিসাব, এখনও pre-damping।');
  host.formula('0 < minDistID (+20)  ->  angular.z = +u = +0.833  (CCW, left; pre-damping)');
  await host.sleep(1900);
  /* --- beat 4: L109-110 right --- */
  show(['pd-hl4', 'pd-br2', 'pd-bnote2']);
  host.caption('আয়নার শাখা — <b>L109-110</b>: <code>elif minDistID &lt; 0: velocity.angular.z = -ang_pid_compute</code>। Wave D-তে object ডানে: minDist 0.50 m, minDistID = -20 — একই হিসাব, একই 0.833 magnitude, চিহ্ন উল্টো: <code>angular.z = -0.833</code> — ডানে ঘোরা (CW)। PID একবারই চলে; শাখা শুধু চিহ্ন বসায়।');
  host.formula('minDistID < 0 (Wave D: -20, 0.50 m)  ->  angular.z = -u = -0.833  (CW, right)');
  await host.sleep(1900);
  /* --- beat 5: exactly zero --- */
  show(['pd-br3', 'pd-zero']);
  host.caption('আর তৃতীয় কোণা: minDistID ঠিক <b>0.0</b> হলে — object হুবহু সামনে — কোনো branch-ই মেলে না (<code>0 &lt; 0</code> মিথ্যা, <code>0 &lt; 0</code> মিথ্যা)। <code>angular.z</code>-এ কেউ হাত দেয় না, L98-এর <code>Twist()</code>-এর জন্মলগ্ন মান <b>0.0</b>-ই থাকে — ঘোরার নির্দেশ নেই। আর linear.x তো সবসময়ই 0.0।');
  host.formula('minDistID == 0.0  ->  neither branch  ->  angular.z stays 0.0  |  linear.x = 0.0 always');
  await host.sleep(1900);
  /* --- close: ceiling + Kd + boundary of this part --- */
  show(['pd-ctick', 'pd-ceil']);
  host.caption('সীমার হিসাব (illustrative): cone-এর কিনারায় |angle| 45-র দিকে গেলে e ছুঁয়ে আসে 45/72 = 0.625, u ছুঁয়ে আসে 3 × 0.625 = <b>1.875</b> — এটাই কাঁচা ceiling; declared <code>angular</code> 1.0 (L37-38) কোথাও enforce হয় না। এক লাইনের Kd-সতর্কতা: Kd = 5 বেশ বড় — scene বদলে যাওয়ার পর প্রথম call-এ derivative term একটা same-sign transient যোগ করতে পারে (illustrative)। এই anim এখানেই থামে: turn deadzone (|u| &lt; 0.5), ×0.5 damping আর publish — পরের part-এর গল্প।');
  host.formula('ceiling: |a| -> 45-  ->  u -> 3*(45/72) = 1.875  |  declared angular = 1.0 (L37-38) unused  |  next: |u| < 0.5 deadzone + x0.5');
  await host.sleep(2100);
};
/* ---------- cmdVelVectors ---------- */

function cvPt(cx, cy, r, deg) {
  const t = deg * Math.PI / 180;
  return [cx - r * Math.sin(t), cy - r * Math.cos(t)];
}
function cvN(n) { return n.toFixed(1); }
/* pie-slice wedge, dim at birth, mutated per beat */
function cvWedge(cx, cy, r, a0, a1, id) {
  const p0 = cvPt(cx, cy, r, a0), p1 = cvPt(cx, cy, r, a1);
  return '<path id="' + id + '" d="M' + cx + ' ' + cy + ' L' + cvN(p0[0]) + ' ' + cvN(p0[1]) +
    ' A' + r + ' ' + r + ' 0 0 0 ' + cvN(p1[0]) + ' ' + cvN(p1[1]) +
    ' Z" fill="#8b949e" fill-opacity="0.07" stroke="#6e7681" stroke-width="1.2" opacity="0.5"/>';
}
/* curved arrow (arc + head), opacity 0 at birth */
function cvArcArrow(cx, cy, r, a0, a1, idA, idH, stroke, wpx, extra) {
  const p0 = cvPt(cx, cy, r, a0), p1 = cvPt(cx, cy, r, a1);
  const ccw = a1 > a0;
  const t1 = a1 * Math.PI / 180;
  let ux = -Math.cos(t1), uy = Math.sin(t1);
  if (!ccw) { ux = -ux; uy = -uy; }
  const tip = [p1[0] + ux * 8, p1[1] + uy * 8];
  const b1 = [p1[0] - uy * 4.2, p1[1] + ux * 4.2];
  const b2 = [p1[0] + uy * 4.2, p1[1] - ux * 4.2];
  const large = Math.abs(a1 - a0) > 180 ? 1 : 0;
  const sweep = ccw ? 0 : 1;
  return '<path id="' + idA + '" d="M' + cvN(p0[0]) + ' ' + cvN(p0[1]) +
    ' A' + r + ' ' + r + ' 0 ' + large + ' ' + sweep + ' ' + cvN(p1[0]) + ' ' + cvN(p1[1]) +
    '" fill="none" stroke="' + stroke + '" stroke-width="' + wpx + '" ' + (extra || 'opacity="0"') + '/>' +
    '<path id="' + idH + '" d="M' + cvN(tip[0]) + ' ' + cvN(tip[1]) + ' L' + cvN(b1[0]) + ' ' + cvN(b1[1]) +
    ' L' + cvN(b2[0]) + ' ' + cvN(b2[1]) + ' Z" fill="' + stroke + '" opacity="0"/>';
}

/* ===== folder-13 anim — cmdVelVectors (part 14) =====================
   laser_Warning.py L111-L124, now SPIN-ONLY. Code card: L112 print
   orin_angular.z; L115 deadzone abs(ang_pid_compute) < 0.5 ->
   velocity.angular.z = 0.0 (Kp-view: |a| < 12 deg means NO turn;
   boundary |a| exactly 12 -> u exactly 0.5 -> '< 0.5' False ->
   passes -> z = 0.25); L118 damping x0.5 (comment says 50%, code
   matches; tracker used 0.6); L120 print angular.z; L124 publish.
   L123's comment admits linear.x is never set — Twist default 0.0
   — THE GUARD NEVER DRIVES FORWARD: every vector visual is pure
   rotation (curved arrows around the robot top view), NO forward
   translation arrow, linear.x = 0.0 readout everywhere the tracker
   showed an approach value. Waves (exact, Kp-only, illustrative):
   A 0.90 m @ +14 deg -> u = 3*(14/72) = 0.583 -> passes -> z =
   +0.292 rad/s spin left, beep OFF (0.90 > 0.55, else-branch L95
   published UInt16()); F 0.80 m @ +8 deg -> u = 0.333 < 0.5 ->
   deadzone -> z = 0.0, quiet; C 0.48 m @ 0 deg -> u = 0 ->
   deadzone -> z = 0.0, robot STILL + BEEPING (alarm L89-95 fired
   earlier, 0.48 <= 0.55); D 0.50 m @ -20 deg -> u = 0.833 -> z =
   -0.417 spin right + beeping. Ceiling 3*(45/72)*0.5 = 0.9375
   rad/s; declared angular 1.0 (L38) never enforced. Cadence beat
   kept but updated: empty front (L72-73) = NO publish, last
   command persists AND /beep latches; Joy (L81-83) = zero Twist
   every scan, return BEFORE the alarm block. One scenario beat
   more than folder 12 (four waves vs three). Prefix cv-. No
   emoji, no arrow chars in stage strings, entities for
   &lt; &gt;. */

ANIMS.cmdVelVectors = async function (host) {
  const svg = host.setStage(
    txt(450, 24, 'deadzone যাচাই, ×0.5 damping, তারপর publish — শুধু ঘোরা, এগোনো নেই — L111-L124', { anchor: 'middle', size: 13.5, weight: 600, fill: '#ffb454' }) +
    /* ---------- left: top view (spin only) ---------- */
    rrect(40, 42, 268, 300, 8, '#0d1117', '#2a3442') +
    txt(174, 60, 'TOP VIEW — robot আর object', { anchor: 'middle', size: 9.5, weight: 700, fill: '#e6edf3' }) +
    rrect(116, 66, 116, 16, 3, '#3d1d20', '#f85149', ' fill-opacity="0.25" id="cv-beepB" opacity="0"') +
    txt(174, 77, '/beep: OFF (0.90 &gt; 0.55)', { anchor: 'middle', size: 6.5, mono: true, fill: '#ff7b72', id: 'cv-beep' }) +
    cvWedge(174, 210, 96, -45, 45, 'cv-cone') +
    txt(174, 106, 'cone ±45° (LaserAngle L39)', { anchor: 'middle', size: 7, mono: true, fill: '#8b949e' }) +
    cvWedge(174, 210, 96, -12, 12, 'cv-dz') +
    txt(174, 300, 'deadzone-এর নীরবতা &lt; ±12° (Kp-only, illustrative)', { anchor: 'middle', size: 7, fill: '#6e7681', id: 'cv-dzt', op: 0 }) +
    circ(174, 210, 4, '#ff7b72', ' id="cv-obj" opacity="0"') +
    txt(174, 322, 'Wave A: +14° · 0.90 m', { anchor: 'middle', size: 8.5, weight: 700, mono: true, fill: '#e3b341', id: 'cv-scen' }) +
    rrect(162, 186, 24, 48, 5, '#21262d', '#8b949e') +
    '<path d="M174 176 L180 188 L168 188 Z" fill="#4fc3f7"/>' +
    txt(174, 250, 'robot', { anchor: 'middle', size: 7, fill: '#8b949e' }) +
    cvArcArrow(174, 210, 34, -40, 130, 'cv-tccw', 'cv-tccwh', '#4fc3f7', 2.2) +
    txt(174, 262, 'angular.z CCW', { anchor: 'middle', size: 6.5, fill: '#4fc3f7', id: 'cv-tccwt', op: 0 }) +
    cvArcArrow(174, 210, 34, 40, -130, 'cv-tcw', 'cv-tcwh', '#e3b341', 2.2) +
    txt(174, 274, 'angular.z CW', { anchor: 'middle', size: 6.5, fill: '#e3b341', id: 'cv-tcwt', op: 0 }) +
    txt(174, 337, 'সামনের তীর নেই — linear.x কখনো set হয় না (L123)', { anchor: 'middle', size: 6.5, fill: '#6e7681', id: 'cv-nofwd', op: 0 }) +
    /* ---------- middle: vector dial (spin only) ---------- */
    rrect(318, 42, 172, 300, 8, '#0d1117', '#30363d') +
    txt(404, 60, 'VECTOR DIAL', { anchor: 'middle', size: 9.5, weight: 700, fill: '#e6edf3' }) +
    txt(404, 78, 'linear.x — স্থির শূন্য (m/s)', { anchor: 'middle', size: 7.5, weight: 700, fill: '#c9d1d9' }) +
    '<path d="M404 96 L404 152" stroke="#6e7681" stroke-width="1.5" fill="none"/>' +
    '<path d="M404 86 L409 96 L399 96 Z" fill="#8b949e"/>' +
    '<path d="M404 162 L409 152 L399 152 Z" fill="#8b949e"/>' +
    txt(412, 97, '+ সামনে', { size: 7, fill: '#7ee787' }) +
    txt(412, 153, '- পেছনে', { size: 7, fill: '#ff7b72' }) +
    circ(404, 124, 3, '#8b949e') +
    txt(412, 127, '0.0 — সবসময়', { size: 6.5, fill: '#8b949e' }) +
    rrect(344, 168, 120, 18, 9, '#161b22', '#30363d', ' id="cv-linp"') +
    txt(404, 180.5, 'linear.x = 0.0', { anchor: 'middle', size: 8, mono: true, fill: '#e6edf3', id: 'cv-linv' }) +
    txt(404, 202, 'angular.z — ঘোরার তীর (rad/s)', { anchor: 'middle', size: 7.5, weight: 700, fill: '#c9d1d9' }) +
    circ(404, 244, 26, 'none', ' stroke="#30363d" stroke-width="1.5"') +
    cvArcArrow(404, 244, 26, -35, 175, 'cv-acw', 'cv-acwh', '#4fc3f7', 2.4) +
    cvArcArrow(404, 244, 26, 35, -175, 'cv-aw', 'cv-awh', '#e3b341', 2.4) +
    txt(357, 247, 'CCW +', { anchor: 'end', size: 7, weight: 700, fill: '#4fc3f7' }) +
    txt(451, 247, 'CW -', { size: 7, weight: 700, fill: '#e3b341' }) +
    rrect(339, 282, 130, 20, 10, '#161b22', '#30363d', ' id="cv-angp"') +
    txt(404, 295.5, 'angular.z = +0.583', { anchor: 'middle', size: 8, weight: 700, mono: true, fill: '#e6edf3', id: 'cv-angv' }) +
    txt(404, 320, 'PID-এর ফল এখনো কাঁচা — damping বাকি', { anchor: 'middle', size: 6.5, fill: '#6e7681', id: 'cv-angnote', op: 0 }) +
    txt(404, 332, 'ROS নিয়ম: CCW = ধনাত্মক = বাঁয়ে ঘোরা', { anchor: 'middle', size: 6.5, fill: '#8b949e' }) +
    /* ---------- right: pipeline ---------- */
    rrect(500, 42, 360, 300, 8, '#0d1117', '#2a3442') +
    txt(680, 60, 'PIPELINE — L111-L124', { anchor: 'middle', size: 9.5, weight: 700, fill: '#e6edf3' }) +
    rrect(510, 68, 340, 15, 3, '#21262d', 'none', ' id="cv-hl1" opacity="0"') +
    txt(518, 79, 'print("orin_angular.z: ", velocity.angular.z)', { size: 7.5, mono: true, fill: '#8b949e' }) +
    txt(848, 79, 'L112', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    rrect(510, 84, 340, 15, 3, '#21262d', 'none', ' id="cv-hl2" opacity="0"') +
    txt(518, 95, 'if abs(ang_pid_compute) &lt; 0.5: velocity.angular.z = 0.0', { size: 7.5, mono: true, fill: '#8b949e' }) +
    txt(848, 95, 'L115', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    rrect(510, 100, 340, 15, 3, '#21262d', 'none', ' id="cv-hl3" opacity="0"') +
    txt(518, 111, 'velocity.angular.z = velocity.angular.z * 0.5', { size: 7.5, mono: true, fill: '#8b949e' }) +
    txt(848, 111, 'L118', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    rrect(510, 116, 340, 15, 3, '#21262d', 'none', ' id="cv-hl4" opacity="0"') +
    txt(518, 127, 'print("angular.z: ", velocity.angular.z)', { size: 7.5, mono: true, fill: '#8b949e' }) +
    txt(848, 127, 'L120', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    rrect(510, 132, 340, 15, 3, '#21262d', 'none', ' id="cv-hl5" opacity="0"') +
    txt(518, 143, 'self.pub_vel.publish(velocity)', { size: 7.5, mono: true, fill: '#8b949e' }) +
    txt(848, 143, 'L124', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    rrect(510, 152, 164, 40, 6, '#161b22', '#4fc3f7', ' id="cv-ch1" opacity="0"') +
    txt(592, 165, '1) DEADZONE |u| &lt; 0.5?', { anchor: 'middle', size: 7.5, weight: 700, fill: '#4fc3f7' }) +
    txt(592, 182, 'Wave A: 0.583 - পাস', { anchor: 'middle', size: 7.5, mono: true, fill: '#e6edf3', id: 'cv-ch1t' }) +
    rrect(686, 152, 164, 40, 6, '#161b22', '#e3b341', ' id="cv-ch2" opacity="0"') +
    txt(768, 165, '2) DAMPING ×0.5', { anchor: 'middle', size: 7.5, weight: 700, fill: '#e3b341' }) +
    txt(768, 182, '+0.583 -&gt; +0.292', { anchor: 'middle', size: 7.5, mono: true, fill: '#e6edf3', id: 'cv-ch2t' }) +
    rrect(510, 200, 340, 40, 6, '#161b22', '#7ee787', ' id="cv-ch3" opacity="0"') +
    txt(680, 213, '3) PUBLISH L124 — pub_vel.publish(velocity)', { anchor: 'middle', size: 7.5, weight: 700, fill: '#7ee787' }) +
    txt(680, 230, '/cmd_vel: (0.0, +0.292) — শুধু বাঁয়ে ঘোরা, এগোবে না', { anchor: 'middle', size: 7.5, mono: true, fill: '#e6edf3', id: 'cv-ch3t' }) +
    txt(510, 254, 'ceiling (illustrative): cone-এর কিনারায় |a| প্রায় 45° হলে', { size: 7, fill: '#8b949e', id: 'cv-cnote', op: 0 }) +
    txt(510, 267, 'u প্রায় 1.875, ×0.5 করলে 0.9375 rad/s — declared angular 1.0 (L38) enforce হয় না', { size: 7, fill: '#8b949e', id: 'cv-cnote2', op: 0 }) +
    txt(510, 290, 'L114/L117-এর comment: প্রায় সোজা হলে ঘুরো না, whip around ঠেকাও', { size: 7, fill: '#6e7681', id: 'cv-cnote3', op: 0 }) +
    txt(510, 303, 'সব সংখ্যা Kp-only illustrative — vendor SinglePID এই folder-এ নেই', { size: 7, fill: '#6e7681', id: 'cv-cnote4', op: 0 }) +
    txt(510, 330, '0.5 · 0.5 — দুটোই hard-coded, parameter নয়', { size: 7, fill: '#d2a8ff', id: 'cv-cnote5', op: 0 }) +
    /* ---------- bottom: publish cadence ---------- */
    rrect(40, 352, 820, 84, 8, '#111', '#30363d') +
    txt(60, 370, 'PUBLISH CADENCE — প্রতি scan-এ এক publish (illustrative)', { size: 9, weight: 700, fill: '#e6edf3' }) +
    '<path d="M70 406 L830 406" stroke="#30363d" stroke-width="2" fill="none"/>' +
    txt(830, 394, 'সময় -&gt;', { anchor: 'end', size: 7, fill: '#6e7681' }) +
    circ(96, 406, 5, '#4fc3f7') +
    txt(96, 394, '/scan', { anchor: 'middle', size: 7, mono: true, fill: '#4fc3f7' }) +
    circ(170, 406, 5, '#7ee787', ' id="cv-p1" opacity="0"') +
    txt(170, 394, 'publish', { anchor: 'middle', size: 7, mono: true, fill: '#7ee787', id: 'cv-p1t', op: 0 }) +
    circ(280, 406, 5, '#4fc3f7', ' id="cv-s2" opacity="0"') +
    txt(280, 394, '/scan', { anchor: 'middle', size: 7, mono: true, fill: '#4fc3f7', id: 'cv-s2t', op: 0 }) +
    circ(354, 406, 5, '#7ee787', ' id="cv-p2" opacity="0"') +
    txt(354, 394, 'publish', { anchor: 'middle', size: 7, mono: true, fill: '#7ee787', id: 'cv-p2t', op: 0 }) +
    rrect(420, 398, 150, 16, 3, '#3d1d20', '#f85149', ' fill-opacity="0.35" stroke-dasharray="4 3" id="cv-none" opacity="0"') +
    txt(495, 426, 'সামনে খালি (L72-73) — publish নেই, /beep আটকে', { anchor: 'middle', size: 7, fill: '#ff7b72', id: 'cv-nonet', op: 0 }) +
    circ(610, 406, 5, '#d2a8ff', ' id="cv-joy" opacity="0"') +
    txt(610, 394, '/JoyState True', { anchor: 'middle', size: 7, mono: true, fill: '#d2a8ff', id: 'cv-joyt', op: 0 }) +
    circ(700, 406, 5, '#7ee787', ' id="cv-zp" opacity="0"') +
    txt(700, 394, 'শূন্য Twist', { anchor: 'middle', size: 7, mono: true, fill: '#7ee787', id: 'cv-zpt', op: 0 }) +
    txt(830, 426, 'publish না এলে চাকা শেষ কমান্ডে · /beep লাইভ থাকে', { anchor: 'end', size: 7, fill: '#8b949e', id: 'cv-lastt', op: 0 }) +
    txt(450, 450, 'source: laser_Warning.py L111-L124 · deadzone L115 · damping L118 · linear.x-নোট L123 · alarm L89-95 · Joy L81-83', { anchor: 'middle', size: 7.5, mono: true, fill: '#6e7681' })
  );
  const q = id => svg.querySelector('#' + id);
  const show = ids => ids.forEach(i => q(i).setAttribute('opacity', 1));
  const hide = ids => ids.forEach(i => q(i).setAttribute('opacity', 0));
  const cvObj = (deg, dist) => {
    const p = cvPt(174, 210, 96 * dist, deg);
    q('cv-obj').setAttribute('cx', p[0]); q('cv-obj').setAttribute('cy', p[1]);
  };

  show(['cv-angnote', 'cv-hl1']);
  host.caption('আগের Part থেমে গিয়েছিল sign branch-এর ঠিক পরে, কাঁচা <code>angular.z</code>-এ (Wave B-তে +0.833, pre-damping)। <b>L112</b> সেই কাঁচা মানটাই console-এ ছাপে (<i>orin</i> = original)। এই Part-এর তিনটা ধাপ সেটাকে চূড়ান্ত করে: deadzone যাচাই, ×0.5 damping, তারপর publish। আর গার্ডের খোদাই-করা সত্য — L123-এর comment নিজেই স্বীকার করে — <code>linear.x</code> কোনোদিন set হয় না: robot শুধু জায়গায় ঘুরে, কখনো এগোয় না। ROS-এ ধনাত্মক <code>angular.z</code> = বাঁয়ে ঘোরা (CCW)।');
  host.formula('final angular.z = (|u| >= 0.5 ? u_signed : 0.0) * 0.5   |   linear.x = 0.0 — never set (L123)');
  cvObj(14, 0.90);
  show(['cv-obj']);
  await host.sleep(1700);
  /* --- beat 1: deadzone pass Wave A --- */
  show(['cv-hl2', 'cv-ch1']);
  host.caption('<b>Wave A (ধরে নিই): object +14°-এ, 0.90 m।</b> <b>L115</b>: <code>abs(ang_pid_compute) &lt; 0.5</code>? হিসাব (Kp-only view, illustrative): u = 3 × 14/72 = <b>0.583</b> — 0.5-এর বেশি, তাই deadzone <b>পাস</b>; <code>angular.z</code> কাটা পড়ে না, 0.583-ই থাকে। (সব pid ফল Kp-only illustrative — vendor <code>SinglePID</code> এই folder-এ নেই।)');
  host.formula('Wave A: u = 3*(14/72) = 0.583 >= 0.5  ->  keep u  (deadzone pass)');
  await host.sleep(1800);
  /* --- beat 2: damping Wave A --- */
  show(['cv-hl3', 'cv-ch2']);
  q('cv-angv').textContent = 'angular.z = +0.292';
  q('cv-angp').setAttribute('stroke', '#4fc3f7');
  q('cv-linp').setAttribute('stroke', '#4fc3f7');
  show(['cv-acw', 'cv-acwh', 'cv-tccw', 'cv-tccwh', 'cv-tccwt', 'cv-nofwd']);
  host.caption('<b>L118</b>: <code>velocity.angular.z = velocity.angular.z * 0.5</code> — comment (L117) বলে 50%, code-ও ঠিক তাই (tracker-টা ছিল ×0.6)। 0.583 × 0.5 = <b>+0.292 rad/s</b>। Dial-এ চূড়ান্ত ছবি: সামনের তীর <b>নেই-ই</b> — <code>linear.x = 0.0</code>, শুধু বাঁয়ে ঘোরার বাঁক, robot জায়গায় দাঁড়িয়ে ঘুরছে।');
  host.formula('Wave A final: angular.z = 0.583 * 0.5 = +0.292 rad/s  |  linear.x = 0.0 m/s (never set)');
  await host.sleep(2000);
  /* --- beat 3: publish Wave A --- */
  show(['cv-hl4', 'cv-hl5', 'cv-ch3', 'cv-beepB', 'cv-beep']);
  host.caption('<b>L120</b> console-এ চূড়ান্ত মান ছাপে, <b>L124</b> <code>self.pub_vel.publish(velocity)</code> — একটাই <code>Twist</code>, <code>/cmd_vel</code>-এ (L30-এর publisher)। Alarm-ও একই scan-এ আগেই হিসাব হয়ে গেছে (L89-95): 0.90 &gt; 0.55, তাই else-branch <code>/beep</code>-এ 0 পাঠিয়েছে (L95) — নীরবে ঘোরা। এই মুহূর্ত থেকে পরের scan না আসা পর্যন্ত চাকা এই কমান্ডই মানবে।');
  host.formula('publish (linear.x = 0.0, angular.z = +0.292) -> /cmd_vel  |  /beep 0 (0.90 > 0.55, L95)');
  await host.sleep(2000);
  /* --- beat 4: Wave F deadzone kill + boundary --- */
  q('cv-scen').textContent = 'Wave F: +8° · 0.80 m';
  q('cv-ch1t').textContent = 'Wave F: 0.333 - কাটা পড়ল';
  q('cv-ch1').setAttribute('stroke', '#f85149');
  q('cv-ch2t').textContent = '0.0 × 0.5 = 0.0';
  q('cv-angv').textContent = 'angular.z = 0.0';
  q('cv-beep').textContent = '/beep: OFF (0.80 > 0.55)';
  cvObj(8, 0.80);
  hide(['cv-acw', 'cv-acwh', 'cv-tccw', 'cv-tccwh', 'cv-tccwt']);
  show(['cv-dzt']);
  q('cv-ch3t').textContent = '/cmd_vel: (0.0, 0.0) — দাঁড়িয়ে, চুপ';
  host.caption('এবার <b>Wave F</b>: object +8°-এ, 0.80 m। u = 3 × 8/72 = <b>0.333</b> — 0.5 ছোঁয়নি, তাই <b>L115-এর deadzone কাটা দেয়</b>: <code>angular.z = 0.0</code>। Kp-only view-এ এই সীমা কার্যত <b>|angle| &lt; 12°</b> (3·a/72 &lt; 0.5; illustrative) — tracker-এর 18°-র চেয়ে চেটে। সীমানার ঠিক ওপরে |a| = 12° হলে u ঠিক 0.5 — <code>&lt; 0.5</code> মিথ্যা, তাই মানটা বাঁচে: z = 0.25। আর 0.80 &gt; 0.55 — zone-এর বাইরে, else-branch <code>/beep</code> 0: চুপচাপ দাঁড়িয়ে।');
  host.formula('Wave F: u = 3*8/72 = 0.333 < 0.5  ->  angular.z = 0.0  |  boundary |a| = 12 -> u = 0.5 -> passes -> z = 0.25');
  await host.sleep(2300);
  /* --- beat 5: ceiling --- */
  show(['cv-cnote', 'cv-cnote2', 'cv-cnote3', 'cv-cnote4', 'cv-cnote5']);
  host.caption('দুই ধাপের সীমাহিসাব: damping না থাকলে cone-এর কিনারায় (|angle| প্রায় 45°) কাঁচা u প্রায় <b>1.875</b>-এ উঠত — ×0.5 করে বাস্তব ceiling <b>0.9375 rad/s</b> (illustrative)। খেয়াল করো: declared <code>angular</code> parameter 1.0 (L38) কোথাও enforce হয় না — সীমা দুটো এসেছে deadzone (0.5) আর damping (0.5) থেকে, দুটোই hard-coded সংখ্যা।');
  host.formula('ceiling: u_max = 3 * (45/72) = 1.875 ; 1.875 * 0.5 = 0.9375 rad/s  |  declared angular = 1.0 (L38) unused');
  await host.sleep(2200);
  /* --- beat 6: Wave C still + beeping --- */
  q('cv-scen').textContent = 'Wave C: 0° · 0.48 m — দাঁড়িয়ে + বিঁপ';
  q('cv-ch1t').textContent = 'Wave C: u = 0 — শূন্যই';
  q('cv-ch1').setAttribute('stroke', '#4fc3f7');
  q('cv-ch2t').textContent = '0.0 × 0.5 = 0.0';
  q('cv-angv').textContent = 'angular.z = 0.0';
  q('cv-beep').textContent = '/beep: ON (0.48 <= 0.55)';
  cvObj(0, 0.48);
  q('cv-ch3t').textContent = '/cmd_vel: (0.0, 0.0) — দাঁড়িয়ে থাকা + বিঁপ';
  host.caption('<b>Wave C</b>: object হুবহু সামনে, 0.48 m — Danger zone-এর ভেতরে। কোণ 0 বলে u = 0, deadzone-ও তাকে 0.0-ই রাখে: <code>angular.z = 0.0</code>। কিন্তু হিসাবের আগেই alarm block (L89-95) চলে গেছে: 0.48 &lt;= 0.55 — <code>/beep</code>-এ 1 (L90-92)। robot দাঁড়িয়ে আছে, বিঁপ বাজছে — গার্ডের "একদম কাছে" ভঙ্গি: এগোয় না, পালায় না, শুধু সতর্ক করে।');
  host.formula('Wave C: u = 0 -> angular.z = 0.0  |  0.48 <= 0.55 -> /beep 1 (L89-92) — still + beeping');
  await host.sleep(2300);
  /* --- beat 7: Wave D spin right + beeping --- */
  q('cv-scen').textContent = 'Wave D: -20° · 0.50 m — ঘুরছে + বিঁপ';
  q('cv-ch1t').textContent = 'Wave D: 0.833 - পাস';
  q('cv-ch2t').textContent = '-0.833 -> -0.417';
  q('cv-angv').textContent = 'angular.z = -0.417';
  q('cv-angp').setAttribute('stroke', '#e3b341');
  q('cv-beep').textContent = '/beep: ON (0.50 <= 0.55)';
  cvObj(-20, 0.50);
  show(['cv-aw', 'cv-awh', 'cv-tcw', 'cv-tcwh', 'cv-tcwt', 'cv-nofwd']);
  q('cv-ch3t').textContent = '/cmd_vel: (0.0, -0.417) — ডানে ঘোরা + বিঁপ';
  host.caption('<b>Wave D</b>: object ডানে, -20°, 0.50 m — একই ভাবে zone-এর ভেতরে। u = 3 × 20/72 = <b>0.833</b> — deadzone পাস; sign branch চিহ্নটা উল্টে দিয়েছিল (আগের Part), ×0.5 করে <b>-0.417 rad/s</b>: ডানে ঘোরা (CW), বিঁপ সহ। মানে zone-এ ঢুকলেও মুখ মেলানো থেমে নেই — গার্ড ঘুরতে ঘুরতেই সতর্ক করে, আর কখনো এগোয় না।');
  host.formula('Wave D: u = 3*(20/72) = 0.833 -> z = 0.833*0.5 = -0.417 rad/s (CW, right)  |  /beep 1 (0.50 <= 0.55)');
  await host.sleep(2300);
  /* --- beat 8: cadence --- */
  show(['cv-p1', 'cv-p1t', 'cv-s2', 'cv-s2t', 'cv-p2', 'cv-p2t', 'cv-none', 'cv-nonet', 'cv-joy', 'cv-joyt', 'cv-zp', 'cv-zpt', 'cv-lastt']);
  host.caption('ছন্দটা মনে রাখো: <b>প্রতি scan-এ এক publish</b> — compute শেষ হলেই L124 চলে (timeline illustrative)। সামনে valid কিছু না থাকলে L72-73-এর <code>return</code>-এ publish-ই হয় না — চাকা তখন <b>শেষ কমান্ডেই</b> চলে, আর <code>/beep</code> তার শেষ মানে আটকে থাকে (লেখেও না, মুছেও না)। <code>/JoyState</code> True হলে L81-83 প্রতি scan-এ শূন্য <code>Twist()</code> ঠেলে alarm block-এর <b>আগেই</b> return করে — /beep তখনও refresh হয় না: মানুষের brake।');
  host.formula('scan -> compute -> publish  |  empty front (L72-73): no publish, last cmd persists, /beep latches  |  Joy (L81-83): zero Twist, return before alarm');
  await host.sleep(2200);
  host.caption('মোদ্দা কথা: 12°-র বেশি বাঁকে ঘুরে যায় (A: +0.292), সামান্য বাঁকে চুপ (F), zone-এ ঢুকলে বিঁপ — সোজা সামনে হলে দাঁড়িয়ে (C), বাঁকানো হলে ঘুরতে ঘুরতে (D) — আর প্রতিটা ক্ষেত্রেই <code>linear.x = 0.0</code>: গার্ড কখনো এগোয় না। এরপর আর কোনো হিসাব নেই — শুধু বন্ধ হওয়ার পালা: <code>exit_pro</code> আর <code>main()</code>, শেষ Part-এর গল্প।');
  await host.sleep(1800);
};
/* ---------- safetyHalt ---------- */
/* ============ folder-13 anim: safetyHalt (part 15) ==================
   laser_Warning.py L134-145 (main + try/except/finally), with L127-132
   exit_pro and L15 print as grounding. Source sha b1cf2d67a4d5.
   Facts: L135 rclpy.init(); L136 laserWarning("laser_Warnning_a1") -
   node name typo "Warnning" (double n) IN SOURCE, preserved verbatim;
   L137 print ("start it"); L139 rclpy.spin(laser_warn); L140-141
   except KeyboardInterrupt: pass; L142 finally: L143 exit_pro()  #
   (two spaces before # in source), L144 destroy_node(), L145
   rclpy.shutdown(). L15 print ("improt done") (typo in source) fires
   at import time - two prints, two different times. exit_pro: cmd1
   (L129, trailing space IN SOURCE) + cmd2 (L130 zero-yaml) joined
   L131, os.system(cmd) L132 = a shell outside the node = process-
   level brake. THE GUARD CAVEAT: the brake zeroes /cmd_vel but does
   NOT touch /beep - a beeping guard killed with Ctrl+C keeps its
   last buzzer state (1 from L92 or 0 from L95) until something else
   writes /beep. The file never calls main() and has no __main__
   guard - ros2 run reaches it via the package setup.py
   console_scripts entry (not in this folder; inferred). README L5:
   ros2 run yahboom_M3Pro_laser laser_Warning.
   shCodeLine base 134 (was 135 in folder 12). Id prefix sh-; no
   emoji, no Unicode arrows in stage strings; static backbone visible
   at setStage; first caption + formula before the first await. */


function shCodeLine(n, ind, s, id) {
  const y = 84 + (n - 134) * 20;
  return txt(66, y, String(n), { anchor: 'end', size: 7.5, mono: true, fill: '#6e7681' }) +
         txt(74 + ind * 13, y, s, { size: 8.5, mono: true, fill: '#8b949e', id: id });
}

ANIMS.safetyHalt = async function (host) {
  const svg = host.setStage(
    txt(450, 26, 'main(): জন্ম, ঘূর্ণন, নীরব থামা, finally-র ব্রেক — আর যে কণ্ঠ ব্রেক হয় না', { anchor: 'middle', size: 14, weight: 600, fill: '#ffb454' }) +
    rrect(40, 44, 372, 316, 8, '#0d1117', '#2a3442') +
    txt(56, 64, 'CODE — laser_Warning.py L134-145', { size: 10, weight: 700, fill: '#e6edf3' }) +
    rrect(50, 73, 352, 76, 4, '#7ee787', 'none', ' id="sh-h1" fill-opacity="0.10" opacity="0"') +
    rrect(50, 153, 352, 36, 4, '#4fc3f7', 'none', ' id="sh-h2" fill-opacity="0.10" opacity="0"') +
    rrect(50, 193, 352, 36, 4, '#ff7b72', 'none', ' id="sh-h3" fill-opacity="0.12" opacity="0"') +
    rrect(50, 233, 352, 36, 4, '#e3b341', 'none', ' id="sh-h4" fill-opacity="0.12" opacity="0"') +
    rrect(50, 273, 352, 36, 4, '#7ee787', 'none', ' id="sh-h5" fill-opacity="0.10" opacity="0"') +
    shCodeLine(134, 0, 'def main():', 'sh-c134') +
    shCodeLine(135, 1, 'rclpy.init()', 'sh-c135') +
    shCodeLine(136, 1, 'laser_warn = laserWarning("laser_Warnning_a1")', 'sh-c136') +
    shCodeLine(137, 1, 'print ("start it")', 'sh-c137') +
    shCodeLine(138, 1, 'try:', 'sh-c138') +
    shCodeLine(139, 2, 'rclpy.spin(laser_warn)', 'sh-c139') +
    shCodeLine(140, 1, 'except KeyboardInterrupt:', 'sh-c140') +
    shCodeLine(141, 2, 'pass', 'sh-c141') +
    shCodeLine(142, 1, 'finally:', 'sh-c142') +
    shCodeLine(143, 2, 'laser_warn.exit_pro()  # Force stop the wheels', 'sh-c143') +
    shCodeLine(144, 2, 'laser_warn.destroy_node()', 'sh-c144') +
    shCodeLine(145, 1, 'rclpy.shutdown()', 'sh-c145') +
    txt(56, 326, 'L143-এর exit_pro() = L127-132 — ডানের SHELL কার্ড', { size: 7.5, fill: '#6e7681' }) +
    txt(56, 342, 'README L5: ros2 run yahboom_M3Pro_laser laser_Warning', { size: 7.5, mono: true, fill: '#6e7681' }) +
    rrect(428, 44, 432, 316, 8, '#111', '#30363d') +
    txt(644, 64, 'RUNTIME — জীবনচক্র (illustrative)', { anchor: 'middle', size: 10, weight: 700, fill: '#e6edf3' }) +
    txt(702, 84, 'TERMINAL', { size: 8, weight: 700, fill: '#6e7681' }) +
    rrect(702, 90, 142, 58, 5, '#0d1117', '#30363d') +
    txt(712, 108, 'improt done', { size: 8, mono: true, fill: '#8b949e', id: 'sh-pol1', op: 0 }) +
    txt(712, 128, 'start it', { size: 8.5, mono: true, weight: 700, fill: '#7ee787', id: 'sh-pol2', op: 0 }) +
    txt(702, 160, 'দুই print, দুই সময়', { size: 7.5, fill: '#6e7681', id: 'sh-pon1', op: 0 }) +
    txt(702, 172, '(L15) আর (L137)', { size: 7.5, fill: '#6e7681', id: 'sh-pon2', op: 0 }) +
    txt(444, 84, 'rclpy.init() (L135) — library চালু', { size: 8.5, mono: true, fill: '#7ee787', id: 'sh-r1', op: 0 }) +
    rrect(444, 92, 250, 62, 6, '#161b22', '#7ee787', ' id="sh-node" opacity="0"') +
    txt(456, 110, 'laserWarning — node জন্ম', { size: 9.5, weight: 700, fill: '#e6edf3', id: 'sh-nt1', op: 0 }) +
    txt(456, 124, 'name: "laser_Warnning_a1" (L136)', { size: 8, mono: true, fill: '#d2a8ff', id: 'sh-nt2', op: 0 }) +
    txt(456, 138, 'sub /scan, /JoyState + pub /cmd_vel, /beep', { size: 7.5, mono: true, fill: '#8b949e', id: 'sh-nt3', op: 0 }) +
    txt(444, 174, 'rclpy.spin(laser_warn) (L139) — event loop', { size: 8.5, mono: true, fill: '#4fc3f7', id: 'sh-r2', op: 0 }) +
    rrect(444, 182, 250, 30, 5, '#161b22', '#30363d', ' id="sh-loop" opacity="0"') +
    circ(468, 197, 5, '#0d1117', ' id="sh-s1" stroke="#4fc3f7" stroke-width="1" opacity="0"') +
    circ(508, 197, 5, '#0d1117', ' id="sh-s2" stroke="#4fc3f7" stroke-width="1" opacity="0"') +
    circ(549, 197, 5, '#0d1117', ' id="sh-s3" stroke="#4fc3f7" stroke-width="1" opacity="0"') +
    circ(589, 197, 5, '#0d1117', ' id="sh-s4" stroke="#4fc3f7" stroke-width="1" opacity="0"') +
    circ(630, 197, 5, '#0d1117', ' id="sh-s5" stroke="#4fc3f7" stroke-width="1" opacity="0"') +
    circ(670, 197, 5, '#0d1117', ' id="sh-s6" stroke="#4fc3f7" stroke-width="1" opacity="0"') +
    circ(468, 197, 8, 'none', ' id="sh-cur" stroke="#4fc3f7" stroke-width="2" opacity="0"') +
    txt(702, 190, 'tick 1: /scan', { size: 8, mono: true, fill: '#4fc3f7', id: 'sh-ls', op: 0 }) +
    txt(702, 204, 'এলে registerScan (L54)', { size: 7.5, fill: '#8b949e', id: 'sh-ls2', op: 0 }) +
    rrect(444, 218, 64, 22, 5, '#161b22', '#ff7b72', ' id="sh-ctrl" opacity="0"') +
    txt(476, 233, 'Ctrl+C', { anchor: 'middle', size: 8.5, weight: 700, fill: '#ff7b72', id: 'sh-ctrlt', op: 0 }) +
    txt(516, 233, 'KeyboardInterrupt (L140) — except: pass (L141)', { size: 7.5, fill: '#8b949e', id: 'sh-ctrnote', op: 0 }) +
    rrect(444, 246, 400, 48, 6, '#0d1117', '#e3b341', ' id="sh-shell" opacity="0"') +
    txt(454, 260, 'SHELL — os.system(cmd) (L132)', { size: 8, weight: 700, fill: '#e3b341', id: 'sh-sht', op: 0 }) +
    txt(454, 274, '$ ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist', { size: 8, mono: true, fill: '#7ee787', id: 'sh-sc1', op: 0 }) +
    txt(454, 287, '"{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"', { size: 7.5, mono: true, fill: '#7ee787', id: 'sh-sc2', op: 0 }) +
    txt(444, 305, 'shell = node-এর বাইরের process — teardown চলাকালেও ব্রেক কাজ করে', { size: 8, fill: '#e3b341', id: 'sh-shn', op: 0 }) +
    txt(444, 317, 'ফল: চাকায় zero Twist (L130) — শেষ velocity মুছে গেল', { size: 8, fill: '#7ee787', id: 'sh-wz', op: 0 }) +
    txt(444, 330, 'কিন্তু /beep-এ হাত দেয় না: buzzer শেষ মানে আটকে থাকে', { size: 8, weight: 700, fill: '#ff7b72', id: 'sh-bp', op: 0 }) +
    txt(444, 342, 'destroy_node() (L144): নাম আর subscription ছাড়া', { size: 8, fill: '#8b949e', id: 'sh-r5a', op: 0 }) +
    txt(444, 354, 'rclpy.shutdown() (L145): library বন্ধ', { size: 8, weight: 700, fill: '#7ee787', id: 'sh-r5b', op: 0 }) +
    txt(450, 386, 'রঙ-নিয়ম: সবুজ = জন্ম ও প্রস্থান, নীল = spin loop, লাল = Ctrl+C ও /beep-এর আটকে থাকা, হলুদ = shell ব্রেক, বেগুনি = নাম', { anchor: 'middle', size: 8.5, fill: '#8b949e' }) +
    txt(450, 440, 'source: laser_Warning.py L134-145 + L127-132 + L15 - README L5', { anchor: 'middle', size: 8, mono: true, fill: '#6e7681' })
  );
  const q = id => svg.querySelector('#' + id);
  const show = id => q(id).setAttribute('opacity', 1);
  const hide = id => q(id).setAttribute('opacity', 0);
  const shGlow = (ids, col) => ids.forEach(i => q(i).setAttribute('fill', col));
  const shX = [468, 508, 549, 589, 630, 670];
  const shSlotIds = ['sh-s1', 'sh-s2', 'sh-s3', 'sh-s4', 'sh-s5', 'sh-s6'];
  const shTick = n => {
    const k = (n - 1) % 6;
    shSlotIds.forEach((sid, i) => q(sid).setAttribute('fill', i === k ? '#4fc3f7' : '#0d1117'));
    q('sh-cur').setAttribute('cx', shX[k]);
    q('sh-ls').textContent = 'tick ' + n + ': /scan';
  };

  host.caption('এই anim-এ <code>main()</code>-এর পুরো জীবনকাল — L134 থেকে L145। বাঁয়ে কোড, ডানে তার runtime ছবি। শুরুতেই একটা কথা: file-টা <b>import</b>-হওয়ার মুহূর্তেই একটা print বেরিয়ে গেছে (L15), আর README L5-এর <code>ros2 run yahboom_M3Pro_laser laser_Warning</code> ডাক দেয় এই <code>main()</code>-কে।');
  host.formula('life = import (L15) -> main (L134) -> rclpy.init (L135) -> spin (L139) -> finally (L142-145)');
  await host.sleep(1500);

  show('sh-pol1'); show('sh-pon1'); show('sh-pon2');
  host.caption('টার্মিনালের প্রথম লাইনটা তাই আগেই এসে গেছে: <code>improt done</code> (L15) — বানানটা source-এ এমনই, <b>import</b> শব্দের typo। মানে দুটি print দুই <b>আলাদা সময়ে</b>: L15 import-এর সময়, L137 পরে main()-এর ভেতরে।');
  await host.sleep(1500);

  show('sh-h1'); shGlow(['sh-c134', 'sh-c135', 'sh-c136', 'sh-c137'], '#e6edf3');
  show('sh-r1'); show('sh-node'); show('sh-nt1'); show('sh-nt2'); show('sh-nt3'); show('sh-pol2');
  host.caption('<code>main()</code> শুরু (L134)। <code>rclpy.init()</code> (L135) — rclpy library চালু। তারপর <code>laserWarning("laser_Warnning_a1")</code> (L136): constructor দুই subscription আর দুই publisher সেট করে node জন্মায় (আগের part-এর গল্প)। Node-নামের বানান <b>Warnning</b> — double-n — source-এ এমনই, এখানে হুবহু রাখা হয়েছে। সঙ্গে দ্বিতীয় print: <b>start it</b> (L137, print-এর পরে space)।');
  await host.sleep(1700);

  show('sh-h2'); shGlow(['sh-c138', 'sh-c139'], '#4fc3f7');
  show('sh-r2'); show('sh-loop'); shSlotIds.forEach(show); show('sh-cur'); show('sh-ls'); show('sh-ls2'); shTick(1);
  host.caption('<code>rclpy.spin(laser_warn)</code> (L139) — এই হলো event loop। <code>/scan</code> এলে <code>registerScan</code> (L54) ছোটে, <code>/JoyState</code> এলে <code>JoyStateCallback</code> (L50)। নীল রিং ঘুরছে = callback একের পর এক (illustrative)।');
  host.formula('spin = wait + dispatch: /scan -> registerScan (L54), /JoyState -> JoyStateCallback (L50)');
  await host.sleep(700);
  shTick(2); await host.sleep(420);
  shTick(3); await host.sleep(420);
  shTick(4); await host.sleep(420);
  shTick(5); await host.sleep(420);
  shTick(6); await host.sleep(420);
  shTick(7); await host.sleep(500);
  host.caption('প্রতি tick-এই সিদ্ধান্তের গাছ চলে — ঘুরবে থামবে, আর দরকার হলে বিপ বাজবে (আগের part-গুলোর গল্প)। <code>spin</code> নিজে থেমে না; Ctrl+C ছাড়া এই ঘূর্ণন চলতেই থাকত।');
  await host.sleep(1500);

  show('sh-h3'); shGlow(['sh-c140', 'sh-c141'], '#ff7b72');
  show('sh-ctrl'); show('sh-ctrlt'); show('sh-ctrnote');
  hide('sh-cur');
  shSlotIds.forEach(sid => { q(sid).setAttribute('fill', '#0d1117'); q(sid).setAttribute('stroke', '#6e7681'); });
  q('sh-loop').setAttribute('stroke', '#30363d');
  q('sh-ls').textContent = 'loop থেমে গেল';
  host.caption('Ctrl+C চাপলে <code>KeyboardInterrupt</code> ওঠে (L140) — except block শুধু <code>pass</code> (L141), একটা শব্দও না। কিন্তু Python-এর কঠিন নিয়ম: <b>finally সব পথেই চলে</b> — exception হোক বা না হোক (L142)।');
  host.formula('Ctrl+C -> KeyboardInterrupt -> except: pass (L141) -> finally STILL runs (L142)');
  await host.sleep(1600);

  show('sh-h4'); shGlow(['sh-c142', 'sh-c143'], '#e3b341');
  show('sh-shell'); show('sh-sht'); show('sh-sc1'); show('sh-sc2');
  host.caption('<code>finally</code> (L142)-এর প্রথম কাজ <code>exit_pro()</code> (L143)। ভেতরে (L127-132): <code>cmd1</code> (L129) + <code>cmd2</code> (L130) জোড়া লেগে (L131) একটাই লাইন — <code>ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist</code>, সঙ্গে সব-শূন্য yaml string। L129-এর শেষে source-এ একটা ফাঁকা space আছে — cmd2-এর quoting-এর আগে দরকারি সেই ফাঁকটা।');
  host.formula('cmd = cmd1 (L129) + cmd2 (L130); os.system(cmd) (L132) = zero Twist via shell');
  await host.sleep(1800);

  show('sh-shn'); show('sh-wz');
  host.caption('<code>os.system(cmd)</code> (L132) লাইনটা একটা <b>shell</b>-এ চালায় — node-এর rclpy জগতের বাইরে, আলাদা <b>process</b>-এর ব্রেক। তাই <code>destroy_node()</code> ভাঙতে শুরু করলেও চাকা শূন্য <code>Twist</code> পেয়ে থেমে যায় (L130-এর zero-yaml)।');
  await host.sleep(1700);

  show('sh-bp');
  host.caption('কিন্তু guard-এর একটা নতুন কথা বাকি: ব্রেকটা শুধু <code>/cmd_vel</code> লেখে — <code>/beep</code>-এ হাতই দেয় না। Ctrl+C-র মুহূর্তে buzzer যদি ON থাকে (L91-এর <code>b.data = 1</code>, L92-এ publish), node মরে গেলেও সেই মানই <code>/beep</code>-এ আটকে থাকে — বিপ বাজতেই থাকে, যতক্ষণ না অন্য কেউ (বা পরের একটা run, নাহলে L95-এর 0) <code>/beep</code>-এ নতুন করে লেখে। চাকা থামল, কণ্ঠ থামল না — guard-এর বিদায়ে এই ফাঁকটা সত্যিকারের আচরণ।');
  host.formula('brake writes /cmd_vel only; /beep keeps its LAST value (1 from L91 or 0 from L95)');
  await host.sleep(1800);

  show('sh-h5'); shGlow(['sh-c144', 'sh-c145'], '#7ee787');
  show('sh-r5a'); show('sh-r5b');
  q('sh-node').setAttribute('stroke', '#30363d');
  shGlow(['sh-nt1', 'sh-nt2', 'sh-nt3'], '#6e7681');
  q('sh-ls').textContent = 'spin শেষ';
  host.caption('শেষ ধাপ: <code>destroy_node()</code> (L144) node-এর নাম আর সাবস্ক্রিপশন ছেড়ে দেয়, <code>rclpy.shutdown()</code> (L145) library বন্ধ করে। চাকা আগেই শূন্য — প্রস্থান নিরাপদ; শুধু বিপের হিসাবটা এই নকশায় ধরা নেই।');
  host.formula('safe exit = zero wheels (L143) + free names (L144) + close library (L145) - /beep NOT covered');
  await host.sleep(1700);

  host.caption('পুরো সারি: জন্ম L135-136, ঘূর্ণন L139, নীরব থামা L140-141, shell ব্রেক L142-143 + L127-132, বিদায় L144-145। সাধারণ নিয়মে velocity-আদেশ নিজে নিজে ফিরে আসে না — তাই <code>finally</code> না থাকলে Ctrl+C-র পরেও চাকা শেষ আদেশের বেগে চলতেই থাকত। <code>/beep</code>-ও একই নিয়মে আটকে থাকে — তবে তার জন্য এই file-এ ব্রেক লেখাই নেই। এই নকশাটাই safety shutdown, guard-এর সীমাসহ।');
  await host.sleep(1600);
};

/* ================================================================ */
const XML_COM = {};
function buildCommentLines() {
  Object.keys(FILEDATA).forEach(fn => {
    const set = new Set(); let inC = false;
    FILEDATA[fn].forEach((ln, i) => {
      const hasOpen = ln.indexOf('<!--') >= 0;
      const hasClose = ln.indexOf('-->') >= 0;
      if (inC || hasOpen) set.add(i + 1);
      if (hasOpen && !hasClose) inC = true;
      else if (hasClose) inC = false;
    });
    XML_COM[fn] = set;
  });
}
function init() {
  buildCommentLines();
  renderSidebar();
  renderParts();
  setupCopy();
  setupNavigation();
  setupAnimations();
  setupMathJaxWatchdog();
}
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}

