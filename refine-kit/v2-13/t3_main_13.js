'use strict';
/* ================================================================
   12. lidar tracking — Line-by-Line Code Analysis
   Single source of truth: FILEDATA (exact source lines from disk)
   + PARTS (authored analysis content). All rendering is generated.
   ================================================================ */

const FILEDATA = {"README.md":["sh start_agent.sh","","ros2 launch yahboom_M3Pro_laser laser_driver.launch.py","","ros2 run yahboom_M3Pro_laser laser_Tracker"],"laser_driver.launch.py":["import os   # (System file operations) - Lets Python interact with computer folders and file paths","from ament_index_python.packages import get_package_share_directory  # A ROS 2 tool that finds where a package is installed","from launch import LaunchDescription  # The main container that holds our list of programs to start","from launch.actions import IncludeLaunchDescription  # A tool to run ANOTHER launch file inside this one","from launch.launch_description_sources import PythonLaunchDescriptionSource  # Tells ROS the other launch file is written in Python","from launch_ros.actions import Node  # A tool to start a single ROS 2 program (Node) - imported just in case it's needed later","","def generate_launch_description():","","    # --- PROGRAM 1: THE LASER MERGER ---","    # Find the path to the 'ira_laser_tools' package, go into the 'launch' folder, and find 'merge_multi.launch.py'","    laser_merge_launch_file = os.path.join(","        get_package_share_directory('ira_laser_tools'),","        'launch',","        'merge_multi.launch.py'","    )","    ","    # --- PROGRAM 2: THE LASER FILTER ---","    # Find the path to the 'yahboom_laser_filter' package, go into the 'launch' folder, and find 'laser_filter_node.launch.py'","    laser_filter_launch_file = os.path.join(","        get_package_share_directory('yahboom_laser_filter'),","        'launch',","        'laser_filter_node.launch.py'","    )","","    # --- THE FINAL LIST ---","    # Hand the list of programs back to ROS 2 to start them all at once.","    return LaunchDescription([","","        # 1. Start the Laser Merger","        # This runs the file we found above. It stitches the front and back lasers together into one 360-degree map.","        IncludeLaunchDescription(","            PythonLaunchDescriptionSource(laser_merge_launch_file)","        ),","        ","        # 2. Start the Laser Filter","        # This runs the file we found above. It cleans up the data by removing \"blind spots\" (like the robot's own arm).","        IncludeLaunchDescription(","            PythonLaunchDescriptionSource(laser_filter_launch_file)","        )","","    ])"],"laser_Tracker.py":["#ros lib","import rclpy","from rclpy.node import Node","from geometry_msgs.msg import Twist","from sensor_msgs.msg import LaserScan","","#commom lib","import math","import numpy as np","import time","from time import sleep","from yahboom_M3Pro_laser.common import *  # Custom Yahboom tools (like Bool message and SinglePID)","import os","print (\"improt done\")  # (Typo in original: means \"import done\")","RAD2DEG = 180 / math.pi  # Conversion factor: radians to degrees","","class laserTracker(Node):","    def __init__(self,name):","        super().__init__(name)","        ","        # --- CREATING SUBSCRIBERS (Listeners) ---","        # Listen to the 360-degree LiDAR scanner","        self.sub_laser = self.create_subscription(LaserScan,\"/scan\",self.registerScan,1)","        # Listen to the joystick (so you can pause the AI and drive manually)","        self.sub_JoyState = self.create_subscription(Bool,'/JoyState', self.JoyStateCallback,1)","        ","        # --- CREATING PUBLISHERS (Radio Stations) ---","        # Tell the wheels to move","        self.pub_vel = self.create_publisher(Twist,'/cmd_vel',1)","        ","        # --- ROS 2 PARAMETERS (Speed & Distance Limits) ---","        self.declare_parameter(\"linear\",0.5)       # Max forward speed (0.5 m/s)","        self.linear = self.get_parameter('linear').get_parameter_value().double_value","        self.declare_parameter(\"angular\",1.0)      # Max turning speed (1.0 rad/s)","        self.angular = self.get_parameter('angular').get_parameter_value().double_value","        self.declare_parameter(\"LaserAngle\",45.0)  # Width of the front cone (45 degrees left and right)","        self.LaserAngle = self.get_parameter('LaserAngle').get_parameter_value().double_value","        self.declare_parameter(\"ResponseDist\",0.55) # The \"Sweet Spot\" distance to keep from the object (0.55 meters)","        self.ResponseDist = self.get_parameter('ResponseDist').get_parameter_value().double_value","        ","        # --- STATE TRACKERS & PID CONTROLLERS ---","        self.Joy_active = False","        ","        # PID controllers are math algorithms that help the robot move smoothly toward a target ","        # without overshooting or stuttering.","        # This one controls forward/backward speed to maintain the 0.55m distance.","        self.lin_pid = SinglePID(1.0, 0.0, 1.0)  # (Kp, Ki, Kd)","        # This one controls left/right turning to keep the object centered in the camera.","        self.ang_pid = SinglePID(2.0, 0.0, 2.0)","        ","","    def JoyStateCallback(self, msg):","        if not isinstance(msg, Bool): return","        self.Joy_active = msg.data  # If True, human is driving, AI should pause","","    def registerScan(self, scan_data):","        if not isinstance(scan_data, LaserScan): return","        ranges = np.array(scan_data.ranges)  # Array of distances from the LiDAR","        ","        # We will search for the absolute closest object in the front 90-degree cone","        minDistList = []    # A list to hold all the close distances","        minDistIDList = []  # A list to hold the angles of those close distances","        ","        # Loop through every single laser beam","        for i in range(len(ranges)):","            # Calculate which direction (in degrees) this specific laser beam is pointing","            angle = (scan_data.angle_min + scan_data.angle_increment * i) * RAD2DEG","            ","            # FRONT ZONE: If the beam is pointing forward (within +/- 45 degrees) and hits something valid","            if abs(angle) < self.LaserAngle and ranges[i] !=0.0 : ","                minDistList.append(ranges[i])     # Save the distance","                minDistIDList.append(angle)       # Save the angle","        ","        # If we found at least one object in front of us...","        if len(minDistList) != 0:","            # Find the absolute closest distance out of all the beams","            minDist = min(minDistList)","            # Find out what angle that closest object is sitting at","            minDistID = minDistIDList[minDistList.index(minDist)]","        else:","            # If nothing is in front of us, do nothing and wait","            print(\"-----------------------\")","            return","","        # If a human is driving, stop the AI and do nothing","        if self.Joy_active :","            self.pub_vel.publish(Twist())","            return","","        velocity = Twist()","        print(\"minDist: \", minDist)       # Print how far away the object is","        print(\"minDistID: \", minDistID)   # Print the angle of the object","        ","        # Create a tiny deadzone: If we are already almost perfectly at 0.55m, pretend we are exactly at 0.55m ","        # so the motors don't jitter back and forth.","        if abs(minDist - self.ResponseDist) < 0.1: minDist = self.ResponseDist","        ","        # LINEAR PID: Calculate how fast to drive forward.","        # We feed it our Target (0.55m) and our Current Distance (minDist).","        # The negative sign is because if we are too far away, the error is positive, ","        # but we need a positive forward speed to drive toward it.","        velocity.linear.x = -self.lin_pid.pid_compute(self.ResponseDist, minDist)","        ","        # ANGULAR PID: Calculate how much to turn.","        # We feed it our Target Angle (0 degrees = straight ahead) and the Current Angle (minDistID).","        # Dividing by 72 just scales the angle down to a number the PID likes.","        ang_pid_compute = self.ang_pid.pid_compute(abs(minDistID) / 72, 0)","        ","        # If the object is to the left (positive angle), turn left (positive angular z)","        if 0 < minDistID : ","            velocity.angular.z = ang_pid_compute","        # If the object is to the right (negative angle), turn right (negative angular z)","        elif minDistID < 0:","            velocity.angular.z = -ang_pid_compute","            ","        # Deadzone for turning: If the object is almost directly in front, don't turn.","        if abs(ang_pid_compute) < 0.5: velocity.angular.z = 0.0","        ","        # Slow down the turning speed to 60% so the robot doesn't whip around too fast.","        velocity.angular.z = velocity.angular.z * 0.6","        ","        print(\"angular.z: \", velocity.angular.z)","        ","        # Send the movement command to the wheels!","        self.pub_vel.publish(velocity)","","    # --- SAFETY SHUTDOWN FUNCTION ---","    def exit_pro(self):","        # When you press Ctrl+C, this runs a terminal command in the background to force the robot to stop","        cmd1 = \"ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist \"","        cmd2 = '''\"{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}\"'''","        cmd = cmd1 + cmd2","        os.system(cmd)","","def main():","    rclpy.init()","    laser_tracker = laserTracker(\"laser_Tracker_a1\")","    print (\"start it\")","    try:","        rclpy.spin(laser_tracker)","    except KeyboardInterrupt:","        pass","    finally:","        laser_tracker.exit_pro()  # Force stop the wheels","        laser_tracker.destroy_node()","        rclpy.shutdown()"]};
const PARTS = [{"n":1,"id":"part-01","fname":"README.md","enTitle":"Runbook — Three Commands","lang":"bash","start":1,"end":5,"flags":[],"explain":[{"a":1,"b":1,"text":"<code>sh start_agent.sh</code> — runbook-এর প্রথম command: <code>sh</code> interpreter দিয়ে vendor-এর bringup script-টা চালানো হলো। মনে রাখতে হবে এই script-টা আমাদের কোনো source file-এর ভেতরে নেই, তাই ভেতরে ঠিক কী লেখা আছে তা আমরা দেখিনি — illustrative ধারণা: এটা robot-এর base driver আর সামনে-পেছনের দুটো lidar-এর vendor driver তুলে দেয়, যাতে কাঁচা scan data বেরোতে শুরু করে। folder 10 আর folder 11 — দুই আগের app-এর README-এর প্রথম line-ও হুবহু এই command-ই — মানে series-এর প্রতিটা lidar পরীক্ষার গোড়ায় একই bringup। README-টা মোট ৫ line-এর: L2 আর L4 blank line, শুধু তিনটা স্তরকে চোখে আলাদা দেখানোর separator — আসল content তিনটা command, আর তিনটাই পরেরটার পূর্বশর্ত।"},{"a":3,"b":3,"text":"<code>ros2 launch yahboom_M3Pro_laser laser_driver.launch.py</code> — দ্বিতীয় স্তর: sensor chain। রূপটা <code>ros2 launch package_name launch_file</code>: ROS 2 আগে <code>yahboom_M3Pro_laser</code> package-টা খোঁজে, তার share directory থেকে <code>laser_driver.launch.py</code> হাতে নিয়ে তার <code>generate_launch_description()</code> চালায়। launch file-টাই এই folder-এর দ্বিতীয় source file, আর এটা folder 11-এর driver-এর সঙ্গে byte-identical — ভেতরে কোনো node সরাসরি লেখা নেই; দুটো <code>IncludeLaunchDescription</code> দিয়ে folder 10-এর গোটা fusion pipeline চেইন করা হয়েছে — <code>ira_laser_tools</code>-এর merger সামনে-পেছনের lidar জোড়ে একটা 360-degree scan বানায়, <code>yahboom_laser_filter</code> robot-এর নিজের শরীর-হাতের blind-spot reading সরিয়ে data পরিষ্কার করে। ফলে <code>/scan</code> topic-এ merged, filtered stream প্রস্তুত হয়। একটা জরুরি সীমা মনে রাখো — এই launch file tracking node-টা চালু করে না; L3 শুধু sensor chain-ই তোলে, behavior node-এর জন্য আলাদা L5 লাগবে। <code>ros2 launch</code>-এর ক্ষমতা এখানেই — এক command-এ একাধিক node-এর পুরো chain একসাথে ওঠে।"},{"a":5,"b":5,"text":"<code>ros2 run yahboom_M3Pro_laser laser_Tracker</code> — তৃতীয় ও শেষ স্তর: tracking node। এবার <code>ros2 launch</code> নয়, <code>ros2 run package_name executable_name</code> — কোনো launch file ছাড়াই package-এর একটাই executable সরাসরি চালানো হয়েছে, নাম <code>laser_Tracker</code> (বড় হাতের T লক্ষ্য করুন)। এই এক শব্দেই আগের app-এর README-র সঙ্গে পুরো তফাত — বাকি চার line (L1-L4) হুবহু এক, কিন্তু folder 11-এর L5-এ ছিল <code>laser_Avoidance</code>। অর্থের তফাত আরও গভীর: folder 11-এর node বাধা এড়াতো (avoidance), এই node সামনের জিনিস এড়ায় না — ফলো করে। node-টা <code>laser_Tracker_a1</code> নাম নিয়ে জন্মায় (laser_Tracker.py-র L137), L3-এর chain থেকে আসা merged <code>/scan</code> আর joystick-এর <code>/JoyState</code> subscribe করে, প্রতিটা scan-এ সামনের ±45° cone-এর সবচেয়ে কাছের valid object খুঁজে তার দিকে এগোয় — dual PID (linear + angular) মিলে <code>ResponseDist</code> parameter-এর মান 0.55 m stand-off দূরত্ব ধরে রাখে আর object-টাকে সামনে কেন্দ্রে রাখতে ঘোরায়, command যায় <code>/cmd_vel</code>-এ। ক্রমটা সৌন্দর্যের নয়: L3 না উঠলে এই node কোনো scan পায় না, উঠে চুপচাপ বসে থাকে।"}],"math":null,"robot":{"correct":"বাস্তব robot-এ তিনটা command ঠিক এই ক্রমে দিন। L1-এর vendor bringup base আর দুটো lidar driver জাগায় (illustrative), L3-এর launch folder 10-এর merger ও filter chain তুলে <code>/scan</code>-এ পরিষ্কার 360-degree data পাঠাতে শুরু করে, তারপর L5-এর <code>laser_Tracker</code> node প্রতিটা scan পেয়ে সামনের ±45° cone-এর সবচেয়ে কাছের object-টার দিকে এগোয় — দুটো PID মিলে চাকা ঘুরিয়ে 0.55 m দূরত্ব ধরে রাখে ও object-কে সামনে কেন্দ্রে রাখে, velocity যায় <code>/cmd_vel</code>-এ, আর console-এ প্রতিটা scan-এ সামনের object-এর দূরত্ব ও angle ছাপাতে থাকে। ফলে robot বাধা এড়ায় না — সামনের কাছের জিনিসটাকেই টার্গেট ধরে তার 0.55 m দূরে ঘুরে-ঘুরে লেগে থাকে। একটা স্তর বাদ গেলে পরের স্তরের খাবারই আসে না।","incorrect":"সাধারণ ভুল: L5 আগে চালানো। ROS 2-এ subscription এমন topic-এও সফল হয় যার publisher এখনো নেই, তাই node ত্রুটিমুক্ত উঠে বসে থাকে — <code>registerScan</code> একবারও চলে না, <code>/cmd_vel</code>-এ কিছু যায় না, চাকা নড়ে না; আসল কারণ L3-এর fusion chain ওঠেনি বলে <code>/scan</code> চুপ। দ্বিতীয় ভুল প্রত্যাশা: folder 11-এর <code>laser_Avoidance</code> দেখে এটাকেও বাধা এড়ানোর node ভাবা — বাস্তবে <code>laser_Tracker</code> সামনের object-এর দিকেই এগিয়ে যায়, তাই robot-কে দেয়াল বা মানুষের দিকে মুখ করে ছেড়ে দিলে সে ওটার 0.55 m দূরে গিয়ে থেমে সেটাকে ফলো করতে থাকবে। একই রকম চুপচাপ ফল হয় L1 বাদ দিলে — lidar থেকে কাঁচা scan-ই আসে না।"},"animType":"runbookFlow"},{"n":2,"id":"part-02","fname":"laser_driver.launch.py","enTitle":"Driver Launch — Imports","lang":"python","start":1,"end":7,"flags":[],"explain":[{"a":1,"b":2,"text":"<code>import os</code> — Python-এর standard library-র file ও path টুল, author-এর comment বলছে <code>(System file operations)</code>। কাজ একটাই: L12 আর L20-এ <code>os.path.join</code> দিয়ে folder 10-এর <code>merge_multi.launch.py</code> ও <code>laser_filter_node.launch.py</code>-এর path জোড়া দেওয়া। <code>from ament_index_python.packages import get_package_share_directory</code> এনেছে সেই ROS 2 function যেটাকে package-এর নাম দিলে — L13-এ <code>ira_laser_tools</code>, L21-এ <code>yahboom_laser_filter</code> — সে ওই package-এর install হওয়া share directory-র পথ ফিরিয়ে দেয়। এটা plain function call: <code>generate_launch_description()</code> চলার সময়েই, মানে construction time-এ, পথ মিলে যায় — folder 10-এর <code>LaunchConfiguration</code> substitution-এর lazy আচরণের ঠিক উল্টো; এজন্যই package install না থাকলে launch পড়ার মুহূর্তেই error আসে। শুরুতেই একটা কথা দিয়ে রাখি: গোটা driver file-টা আগের app folder 11-এর <code>laser_driver.launch.py</code>-এর সঙ্গে byte-identical — এই ছয়টা import থেকে শেষ bracket পর্যন্ত এক বাইট তফাতও নেই, কারণ দুই app-ই চায় একই sensor chain।"},{"a":3,"b":5,"text":"<code>from launch import LaunchDescription</code> — প্রধান container; L28-এ <code>return LaunchDescription</code> দিয়ে যে list-টা launch framework-এর হাতে ফিরে যায় সেটাই এই class-এর object, তাই এই import ছাড়া পুরো file-টাই অর্থহীন। <code>from launch.actions import IncludeLaunchDescription</code> এই file-এর আসল অস্ত্র: একটা launch file-এর ভেতরে আরেকটা launch file চালানোর action, নামেরই মানে Include — L32 আর L38-এ একটা করে বসেছে। এই একটা tool-ই এখানকার পুরো design: নিজে কোনো node না চালিয়ে folder 10-এর merger ও filter launch-কে chain করা। <code>from launch.launch_description_sources import PythonLaunchDescriptionSource</code> বাইরের path string-টাকে wrap করে framework-কে জানায় যে ওই file-টা Python launch file — ROS 2-এ XML বা YAML launch source-ও আছে, কিন্তু এখানে দুটোই Python। এই তিনটি মিলেই launch-chaining pattern: container, include action, আর Python source declaration।"},{"a":6,"b":7,"text":"<code>from launch_ros.actions import Node</code> — ছয়টা import-এর শেষটা, আর author-এর নিজের comment-ই স্বীকার করছে <code>imported just in case it's needed later</code>; সত্যিই গোটা file-এ <code>Node</code> আর কোথাও ব্যবহার হয়নি — L28-42-এর list-এ শুধু দুটো <code>IncludeLaunchDescription</code>, কোনো <code>Node</code> action নেই। এটা একটা দামি পাঠ — import দেখেই মনে করা যাবে না জিনিসটা কাজে লাগছে; Python নামটাকে module scope-এ bind করে চুপচাপ বসে থাকে, কোনো warning বা error নেই, তাই dead import সহজে চোখে পড়ে না। এই app-এর জন্য তার মানেও স্পষ্ট: এই launch file শুধু sensor chain ওঠায়, tracking node-টা চালু করে না — README-র L5 command <code>ros2 run yahboom_M3Pro_laser laser_Tracker</code> সেটাকে আলাদাভাবে তোলে, আর সেই node fused <code>/scan</code> থেকে সামনের সবচেয়ে কাছের object খুঁজে 0.55 m দূরত্বে ফলো করে (আগের app folder 11-এ একই chain-এর উপর ছিল <code>laser_Avoidance</code> — বাধা এড়িয়ে চলা; driver দুই app-এই এক, শুধু ভোক্তা আলাদা)। পার্থক্যটা আরেকটু ধরো: folder 10-এর <code>merge_multi.launch.py</code> একইভাবে <code>Node</code> import করে সরাসরি node চালু করেছিল, কিন্তু এই file সব কাজ অন্য দুই launch file-কে দিয়ে করায়। শেষ সূক্ষ্ম পয়েন্ট: <code>launch</code> আর <code>launch_ros</code> দুটো আলাদা package — <code>Node</code> পাওয়া যায় শুধু দ্বিতীয়টায়, তাই ভবিষ্যতে সত্যিই কোনো node যোগ করতে হলে এই লাইনটাই আগে থেকে প্রস্তুত ছিল। L7 একটা blank line — ছয়টা import-এর block-কে L8-এর <code>def generate_launch_description():</code> থেকে আলাদা দেখানোর separator, নিজে কিছুই execute করে না।"}],"math":null,"robot":{"correct":"এই file তুললেই <code>get_package_share_directory</code> construction time-এ robot-এর install tree থেকে <code>ira_laser_tools</code> ও <code>yahboom_laser_filter</code>-এর share directory খুঁজে দেয়, তাই merger ও filter-এর launch file-এর path আগেই ঠিক হয়। এরপর দুটো IncludeLaunchDescription chain হয়ে folder 10-এর পুরো fusion pipeline ওঠে — front আর back lidar মিলে 360-degree fused <code>/scan</code> তৈরি হয়, blind spot-এর ভুয়া রিডিংও কাটা পড়ে। এই stage-এ robot-এর চাকা একদম স্থির থাকে: import-গুলো কোনো <code>/cmd_vel</code> message পাঠায় না, শুধু <code>laser_Tracker</code> node-এর খাবার তৈরি হয় — সেই node পরে এই fused scan থেকে সামনের সবচেয়ে কাছের object ধরে 0.55 m দূরত্বে ফলো করে।","incorrect":"ভুল পড়া: L6-এর <code>Node</code> import দেখে ধরে নেওয়া যে এই launch file নিজে tracking node-টাও চালু করে। Robot-এ এই ধারণা বিপদজনক: মনে করা হবে robot নিজে নিজে সামনের object ফলো করছে, অথচ <code>/cmd_vel</code> publish করার node চালুই হয়নি — <code>ros2 run yahboom_M3Pro_laser laser_Tracker</code> আলাদাভাবে না চালালে merger-filter উঠুক, <code>/scan</code> প্রস্তুত হোক, lidar ঘুরতে থাকুক, robot চুপচাপ দাঁড়িয়ে থাকবে — চাকায় কোনো command যাবে না। আর unused ভেবে এই import মুছলে কিছু ভাঙে না, কিন্তু author-এর just-in-case দরজাটা বন্ধ হয়।"},"animType":null},{"n":3,"id":"part-03","fname":"laser_driver.launch.py","enTitle":"Two Paths — Merger & Filter","lang":"python","start":8,"end":24,"flags":[],"explain":[{"a":8,"b":8,"text":"<code>def generate_launch_description():</code> — এই নামটাই <code>ros2 launch</code>-এর সঙ্গে চুক্তি। README L3-এর <code>ros2 launch yahboom_M3Pro_laser laser_driver.launch.py</code> চালালে framework এই file-কে import করে ঠিক এই নামের function-টাকে একবার ডাকে; launch file-এ কোনো <code>main()</code> বা spin loop নেই, তাই নাম বদলালেই launch ভেঙে পড়ে। Function-এর ভেতরের প্রতিটা লাইন চলে CONSTRUCTION phase-এ — run phase শুরুর আগে, একবার, উপর থেকে নিচে। Folder 10-এর lesson মনে করো: <code>LaunchConfiguration</code> substitution ছিল lazy, মান মিলত run phase-এ; এই file-এ উল্টো — যা লেখা সব এখনই eagerly চলে। Driver-টা গত app folder 11-এর সঙ্গে byte-identical — ওখানেও এই একই দুই path build হত; তফাত শুধু downstream-এ: ওই app-এর L5 node <code>laser_Avoidance</code> বাধা এড়াত, এই folder 12-এর <code>laser_Tracker</code> সামনের কাছের object-কে 0.55 m দূরত্বে ফলো করে। কাজ শেষে function-টা একটা <code>LaunchDescription</code> ফেরাবে (L28), সেটাকেই framework পরে run করায়।"},{"a":10,"b":11,"text":"দুটো লাইনই <code>#</code> দিয়ে শুরু — comment, Python এগুলো execute করে না, তবু author-এর নকশা হিসেবে file-টার কাঠামো পরিষ্কার করে। L10 banner: <code>PROGRAM 1: THE LASER MERGER</code>; L11 কাজ বলে — <code>ira_laser_tools</code> package-এর path খুঁজে, তার <code>launch</code> folder-এ ঢুকে <code>merge_multi.launch.py</code> বের করা। Comment-এ যা বলা L12-16 হুবহু তা-ই করে — comment মানচিত্র, code পথ। এই <code>merge_multi.launch.py</code>-ই folder 10-এ লাইন ধরে পড়া merger: সেখানে সামনে-পেছনে দুই lidar-এর raw scan (folder 09-এ যেমন একটা lidar-এর নিজের stream দেখেছি) এক 360-degree <code>/scan</code>-এ জোড়া লাগে — সেই fused ring-ই পরে এই app-এর <code>laser_Tracker</code>-এর খাবার।"},{"a":12,"b":13,"text":"<code>laser_merge_launch_file = os.path.join(</code> — assignment শুরু, bracket L16 পর্যন্ত খোলা থাকায় তার সব argument একসঙ্গে মূল্যায়ন হবে। প্রথম argument <code>get_package_share_directory('ira_laser_tools')</code>: এটা launch-এর কোনো magic নয়, ament-এর package index-কে জিজ্ঞেস করা একটা সাধারণ Python function call — আর সে চলে এখনই, construction phase-এ, installed share directory-র path string ফেরিয়ে দেয় (illustrative: <code>install/ira_laser_tools/share/ira_laser_tools</code> — যা <code>ros2 pkg prefix</code> দেখায়)। Package না মিললে এখনই error ওঠে — robot-এর কোনো lidar বা চাকা নড়ার অনেক আগেই, তাই এটা safe early failure।"},{"a":14,"b":16,"text":"পরের দুটো argument <code>'launch'</code> আর <code>'merge_multi.launch.py'</code>। <code>os.path.join</code> এদের মাঝে ঠিক separator বসিয়ে একটা পূর্ণ path বানায় — string <code>+</code> দিয়ে জোড়া দিলে separator ভুল হওয়ার ঝুঁকি থাকে, <code>os.path.join</code> সেই ভার নিজে নেয়, তাই কোন OS-এ চলুক না কেন path ঠিক থাকে। ফল: merger launch file-এর absolute path, জমা রইল variable <code>laser_merge_launch_file</code>-এ। খেয়াল করো, এই মুহূর্তে কিছুই launch হয়নি — এটা নিছক একটা string। Merger-এর আসল কাজ হবে run phase-এ, Part 04-এর <code>IncludeLaunchDescription</code> action থেকে।"},{"a":18,"b":19,"text":"সেই একই pattern-এর দ্বিতীয় কপি। L18 banner: <code>PROGRAM 2: THE LASER FILTER</code>; L19 বলে — <code>yahboom_laser_filter</code> package-এর path, তার <code>launch</code> folder, ভেতরে <code>laser_filter_node.launch.py</code>। ভাষা ও গঠন ইচ্ছা করেই আগের ব্লকের মতো রাখা: দুটো আলাদা program, কিন্তু খোঁজার নিয়ম এক। ভূমিকাও স্পষ্ট — merger দুই lidar-এর মিলিত scan বানায়, filter তার পরে blind spot সরিয়ে (robot-এর নিজের গা বা arm-এর ভুয়া কাছের রিডিং) stream পরিষ্কার করে; এই ক্রমটাই folder 10-এ দেখা pipeline, এখন এক launch file থেকে পুরোটা একসাথে চালানো হচ্ছে।"},{"a":20,"b":21,"text":"<code>laser_filter_launch_file = os.path.join(</code> — নামে শুধু merge-এর জায়গায় filter, বাকি আদল হুবহু আগের ব্লক। <code>get_package_share_directory('yahboom_laser_filter')</code> এবার অন্য একটা package খোঁজে — Yahboom-এর নিজের laser filter package, <code>ira_laser_tools</code> নয়। এটাও একই সাধারণ function call: চলে এখনই, eagerly, construction phase-এ — তাই দুটো path-ই সঙ্গে সঙ্গে মিলে যায় আর দুটোই যাচাই হয়ে যায় কোনো node ওঠার আগেই। এক launch-এ একাধিক package-এর tool এভাবেই এক জায়গায় জড়ো করা যায় — এই file-টা তারই ছোট উদাহরণ।"},{"a":22,"b":24,"text":"শেষ দুটো segment: <code>'launch'</code> আর <code>'laser_filter_node.launch.py'</code> — মিলে filter launch file-এর পূর্ণ path, জমা <code>laser_filter_launch_file</code>-এ। এই মুহূর্তে file-টার অবস্থা দাঁড়াল এমন: দুটো string variable তৈরি, দুটোতেই বাস্তব path, কিন্তু একটাও program চালু হয়নি — কোনো node এখনো exist করে না। এই chain থেকে আসা fused, filtered <code>/scan</code>-ই পরে README L5-এর <code>ros2 run yahboom_M3Pro_laser laser_Tracker</code> node-টা subscribe করবে; এই launch file শুধু তার খাবার তৈরি করে, tracker-কে নিজে চালু করে না। এরপর L26 থেকে আসবে সেই তালিকা তৈরির পর্ব, যেখানে এই দুই path <code>IncludeLaunchDescription</code> দিয়ে run phase-এ নামানো হবে। সহজ কথায়: L12-24 হলো দুইটা ঠিকানা খুঁজে লিখে রাখা — বাড়ি বানানোর কাজ পরের part-এ।"}],"math":null,"robot":{"correct":"আসল robot-এ README L3-এর <code>ros2 launch yahboom_M3Pro_laser laser_driver.launch.py</code> চালালে সবার আগে চলে এই দুইটা path lookup — ament index থেকে <code>ira_laser_tools</code> আর <code>yahboom_laser_filter</code>-এর installed share directory মিলে যায়, তারপরই merger+filter pipeline নামে। Terminal-এ workspace source থাকলে path কখনো ভুল হয় না, workspace অন্য জায়গায় থাকলেও ঠিক থাকে। সামনে-পেছনের দুই lidar-এর scan জুড়ে 360-degree <code>/scan</code> তৈরি হয় আর filter blind spot সরায় — এই পরিষ্কার stream-ই পরে <code>laser_Tracker</code> node পেয়ে সামনের কাছের object-টাকে 0.55 m দূরত্বে ফলো করে। কোনো package না মিললে robot চলতে শুরু করার আগেই construction-এ error ওঠে — early failure, নিরাপদ।","incorrect":"বিভ্রান্তি: অনেকে ভাবে এই লাইনেই merger আর filter চালু হয়ে গেছে, বা source folder-এর <code>merge_multi.launch.py</code> এডিট করলেই robot-এর আচরণ বদলাবে। আসলে path-টা পড়ে install/share-এর কপি থেকে — rebuild না করে এডিট করলে পুরনো fusion config-ই চলে, ফলে ভুল lidar topic বা ভুল frame-এ scan আসে আর <code>/scan</code> ভরে না; তখন <code>laser_Tracker</code>-এর <code>registerScan</code> একবারও চলে না — ফলো করার মতো কোনো object তার চোখেই পড়ে না, robot নিশ্চল দাঁড়িয়ে থাকে। আরেকটা ভুল: launch হয়ে গেছে মানেই tracking শুরু — আসলে এই file tracker node-কে চালুই করে না, সেটা README L5-এর আলাদা <code>ros2 run</code> command ছাড়া ওঠে না।"},"animType":"includeChain"},{"n":4,"id":"part-04","fname":"laser_driver.launch.py","enTitle":"Return — Two Includes, Zero Nodes","lang":"python","start":25,"end":42,"flags":[],"explain":[{"a":26,"b":27,"text":"শেষ পর্বের ঘোষণা — L26-এর <code># --- THE FINAL LIST ---</code> ঠিক আগের দুটো section header-এর (<code>PROGRAM 1</code>, <code>PROGRAM 2</code>) মতোই একই dash-ঘেরা format-এ লেখা। তফাত হলো: আগের দুই পর্ব শুধু দুটো file path string বানিয়েছিল (L12-16, L20-24), এই পর্ব সেই path-গুলো কাজে লাগায়। L27 বলছে program-এর list ROS 2-কে ফিরিয়ে দিয়ে সব একসাথে চালু করতে হবে — কিন্তু এই ফাইলের নিজস্ব কোনো program নেই; list-এ ঢুকবে শুধু দুটো include action। অর্থাৎ পুরো ফাইলটা একটা pure orchestrator: নিজে কোনো node চালায় না, শুধু অন্য দুটো launch file-এর ঠিকানা হাজির করে দেয়।"},{"a":28,"b":28,"text":"L28 একটা পুরো বাক্যের দরজা খুলে দেয় — <code>return</code> মানে <code>generate_launch_description()</code>-এর ফল হিসেবে ros2 launch tool পাবে ঠিক এই object-টাই। <code>LaunchDescription</code> হলো L3-এ import করা container class, আর তার constructor-কে সরাসরি একটা list literal দেওয়া হচ্ছে: opening <code>[</code> এই লাইনে, element-গুলো L30-40-এ, closing <code>]</code> L42-তে। এই list literal-এর ভেতরেই ঢুকে আছে তিনটা blank line — L29, L35, L41; bracket খোলা থাকায় Python-এর চোখে এরা সম্পূর্ণ বৈধ, কাজ শুধু দুটো element-কে চোখে আলাদা করে দেখানো। Folder 10-এর <code>merge_multi.launch.py</code> আলাদা আলাদা list বানিয়ে জোড়া দিয়েছিল; এখানে পথ উল্টো — inline list, দুটো element সরাসরি বন্ধনীর ভেতরে। আর মনে রেখো: এই লাইন চলছে construction phase-এ — list-টা এখন শুধু বানানো হচ্ছে, কিছুই চালু হচ্ছে না; চালু করার কাজ পরে run phase-এ ঘটবে।"},{"a":30,"b":31,"text":"List-এর প্রথম element-এর আগের comment। <code># 1.</code> নম্বরটা ক্রম শেখাচ্ছে: merger আগে, filter পরে — এই ক্রম পাইপলাইনের গল্পের সাথে মেলে। L31 বলছে এই include <code>the file we found above</code> চালাবে, আর তার কাজ দুটো lidar-এর data জোড়া দেওয়া — comment-এর ভাষায় ওটা <code>stitches the front and back lasers together into one 360-degree map</code>। <code>found above</code> মানে L12-16-এ construction time-এই বসে যাওয়া <code>laser_merge_launch_file</code> path — কোনো lazy substitution নয়, string তখনই final। Folder 10-এ আমরা এই ফাইলের ভেতরটা পড়েছি, folder 09-এ দেখেছি একটা lidar একটাই দিক দেখে — তাই 360-degree দেখতে হলে এই জোড়া ছাড়া উপায় নেই।"},{"a":32,"b":34,"text":"তিন লাইনের nested গঠন। বাইরে <code>IncludeLaunchDescription</code> (L4-এর import) — launch জগতের recursion tool: এক launch file-এর ভেতরে আরেকটা launch file চালানোর একমাত্র পরিষ্কার উপায়। ভেতরে <code>PythonLaunchDescriptionSource(laser_merge_launch_file)</code> (L5-এর import) — এটা জানিয়ে দেয় অন্তর্ভুক্ত ফাইলটা Python launch file, YAML নয়। সবচেয়ে ভেতরে path string। Run phase-এ framework এই action execute করতে গিয়ে ওই ফাইল import করে তার নিজের <code>generate_launch_description()</code> ডাকে — অর্থাৎ প্রতিটা included ফাইলের নিজের constructor phase আর run phase আলাদা করে চলে; ভেতরের গল্পটা folder 10-এর, এখানে সেটা illustrative। L34-এর <code>),</code> এই include-টা বন্ধ করে কমা সহ — কমাটাই list-এর দুই element-এর বিভাজক।"},{"a":36,"b":37,"text":"দ্বিতীয় element-এর comment — <code># 2.</code> বলছে এটা পাইপলাইনের দ্বিতীয় ধাপ। L37-এর ব্যাখ্যা folder 10-এর filter-এর কাজের সাথে মেলে: ওটা <code>removing \"blind spots\" (like the robot's own arm)</code> — মানে fused scan-এর ভেতর robot-এর নিজের গা বা arm-এর reflection থেকে আসা ভুয়া কাছের রিডিং বাদ দেওয়া হয়। এই app-ে এই ধাপটা বিশেষ গুরুত্ব পায়, কারণ <code>laser_Tracker</code> node সামনের ±45-degree cone-এর মধ্যে সবচেয়ে কাছের object-টাকেই খুঁজে তার থেকে 0.55 m দূরত্ব ধরে রাখে — filter না থাকলে node-টা robot-এর নিজের arm-এর ভুয়া রিডিংকেই সবচেয়ে কাছের object ভেবে ফেলত, আর তখন একটা অদৃশ্য target থেকে দূরে থাকতে চাকা পেছনে ঘোরানোর command চলত (illustrative)। আর <code>the file we found above</code> এখানে L20-24-এর <code>laser_filter_launch_file</code> path-কেই বোঝায় — একই construction-time নিয়ম, string আগেই বসে আছে।"},{"a":38,"b":40,"text":"দ্বিতীয় include — গঠনে হুবহু প্রথমটার মতো, শুধু সবচেয়ে ভেতরের argument আলাদা: <code>laser_filter_launch_file</code>। দুটো action দেখতে অভিন্ন হলেও ওরা দুটো সম্পূর্ণ আলাদা ফাইল খুলবে — একটা <code>ira_laser_tools</code> package থেকে, আরেকটা <code>yahboom_laser_filter</code> package থেকে। Run phase-এ framework list-এর ভেতর দিয়ে উপর থেকে নিচে action execute করে, তাই merger আগে চালু, filter পরে — আর ক্রমটা অর্থবহ, কারণ merger-এর output stream-ই filter-এর input। ছোট নজরদারি: L34 প্রথম element-এর পরে কমা দিয়েছিল, কিন্তু L40-এ <code>)</code>-এর পরে কমা নেই — শেষ element-এর পরে Python কমা ছাড়াই চলে যায়। তবে এটা শুধু action-এর ক্রম, কোনো synchronization নয়: ROS 2-তে একটা process সামান্য আগে-পরে উঠলেও publisher-subscriber পরে মিলে যায়, এই কারণে launch ভেঙে পড়ে না।"},{"a":42,"b":42,"text":"ফাইলের শেষ লাইন <code>])</code> — দুটো bracket একসাথে বন্ধ, bracket ladder-এর শেষ ধাপ। ভেতরের <code>]</code> L28-এ খোলা list literal বন্ধ করে, বাইরের <code>)</code> <code>LaunchDescription</code> constructor call বন্ধ করে, আর তখনই <code>return</code> statement সম্পূর্ণ হয়। হিসাবটা গুনে দেখো: L28-এর <code>LaunchDescription([</code> দুটো bracket খুলেছিল, L34-এর <code>),</code> প্রথম include বন্ধ করেছে, L40-এর <code>)</code> দ্বিতীয়টা, L42 বাকি দুটো বন্ধ করে সব মিলিয়ে দিয়েছে। পুরো ফাইলের সারমর্ম এখানেই: construction phase-এ দুটো path string, run phase-এ merger-তারপর-filter দুটো include action, আর নিজের node একদম zero — L6-এ import করা <code>Node</code> কখনো ব্যবহারই হয়নি, ওই লাইনের comment নিজেই বলে দিয়েছিল এটা রাখা হয়েছে শুধু সতর্কতার জন্য। একটা ঐতিহাসিক মন্তব্য: folder 11-এ হুবহু এই একই driver file (byte-identical) laser_Avoidance-কে সেবা দিয়েছিল — সেখানে node-টা বাধা এড়াত; এই app-এ node বদলে <code>laser_Tracker</code>, যে সামনের কাছের object অনুসরণ করে। Driver অপরিবর্তিত থাকতে পারে কারণ sensor chain দুই ক্ষেত্রেই এক — পার্থক্য শুধু সেই fused <code>/scan</code> কে খায়। আর স্পষ্ট থাকো: <code>laser_Tracker</code>-কে এই launch file তোলে না — README-র L3 command শুধু sensor chain জাগায়; tracking node-টা আসে README L5-এর <code>ros2 run yahboom_M3Pro_laser laser_Tracker</code> থেকে।"}],"math":null,"robot":{"correct":"Real robot-এ এক command-এ পুরো sensing pipeline ওঠে: run phase-এ list-এর ক্রম মেনে merger আগে চালু হয়ে সামনে-পেছনের দুটো lidar-এর raw scan জুড়ে 360-degree fused <code>/scan</code> বানায়, তারপর filter robot-এর নিজের arm-এর ভুয়া কাছের রিডিং বাদ দিয়ে stream পরিষ্কার করে — terminal-এ দুটো included launch-এর process log নামতে থাকে (illustrative)। ফলে আলাদাভাবে <code>ros2 run</code> করা <code>laser_Tracker</code> node একটা পরিষ্কার <code>/scan</code> পায়, যেটা সামনের কাছের object খুঁজে 0.55 m দূরত্ব ধরে রাখতে <code>/cmd_vel</code> publish করে। এই ফাইল নিজে কোনো <code>/cmd_vel</code> message পাঠায় না, তাই এটা চালু করলেই robot-এর চাকা নড়ে না — শুধু তার চোখ খোলে।","incorrect":"সাধারণ ভুল: এই launch file-টাই tracking চালায় ভেবে নেওয়া। আসলে এর ভেতরে একটাও Node action নেই, শুধু দুটো include; <code>laser_Tracker</code> node README-র শেষ command-এ আলাদা করে <code>ros2 run</code> করতে হয় — সেটা না চালালে sensor chain পুরো চলুক, <code>/scan</code> ভরে থাকুক, robot চুপচাপ দাঁড়িয়ে থাকবে। আরেকটা ভুল: filter include বাদ দিলে সময় বাঁচে ভাবা — blind spot রিডিং fused scan-এ থেকে গেলে tracker robot-এর নিজের arm-কেই সামনের সবচেয়ে কাছের object ভেবে 0.55 m দূরত্ব ধরতে চাইবে, ফলে অদৃশ্য target থেকে সরতে চাকা বারবার পেছনে ঘুরতে থাকবে (illustrative)।"},"animType":null},{"n":5,"id":"part-05","fname":"laser_Tracker.py","enTitle":"Tracker Node — Module Head","lang":"python","start":1,"end":15,"flags":[],"explain":[{"a":1,"b":1,"text":"ফাইলের একদম শুরুর section-marker comment: <code>#ros lib</code>। কাজ শুধু পাঠকের দিকনির্দেশ — নিচের চারটা import ROS 2-এর core লাইব্রেরির গ্রুপ বোঝাচ্ছে। Comment হওয়ায় Python এটাকে execute করে না; machine-এর ওপর এর কোনো প্রভাব নেই, ফাইলটা মানুষের পড়ার সুবিধার জন্য ভাগ করাই এর একমাত্র উদ্দেশ্য।"},{"a":2,"b":5,"text":"চারটা ROS 2 import, আর পরের অংশে প্রতিটার সরাসরি ব্যবহার আছে। <code>import rclpy</code> — client library-র core; পরে <code>rclpy.init()</code> (L136) আর spin-loop এটার ওপর দাঁড়াবে। <code>from rclpy.node import Node</code> — L17-এ <code>class laserTracker(Node)</code> এই base class-টা এখান থেকেই পাবে। <code>from geometry_msgs.msg import Twist</code> — velocity-command message; L29-এর <code>/cmd_vel</code> publisher ঠিক এই type publish করবে, চাকা কত দ্রুত ঘুরবে সেই নির্দেশ এই message-এর ঘরে লেখা হবে। <code>from sensor_msgs.msg import LaserScan</code> — LiDAR-র scan message; L23-এর <code>/scan</code> subscription থেকে প্রতিটা beam-এর distance এই type-এই আসবে। এক কথায়: tracker-এর INPUT (LaserScan) আর OUTPUT (Twist) — দুটোরই উৎস এই চার লাইন।"},{"a":7,"b":7,"text":"দ্বিতীয় section-marker: <code>#commom lib</code>। বানানে খেয়াল করুন — লেখা “commom”, “common” শব্দের typo, আর এই typo-টা source-এ নিজেই আছে; আমরা source কখনো ঠিক করি না, শুধু চিনিয়ে দিই। অর্থ: নিচের import-গুলো ROS-এর বাইরের সাধারণ লাইব্রেরি আর vendor-এর নিজস্ব package।"},{"a":8,"b":9,"text":"<code>import math</code> আর <code>import numpy as np</code>। math-এর এই part-এ সরাসরি ব্যবহার একটাই — L15-এর <code>math.pi</code>, একটা scalar constant বানানোর জন্য। numpy আসছে ছদ্মনাম <code>np</code> নিয়ে: L58-এ <code>np.array(scan_data.ranges)</code> পুরো beam-distance list-টাকে numpy array-তে রূপান্তর করবে। scalar-এর কাজ math-এর, পুরো distance-array-র কাজ numpy-র — দুই লাইব্রেরির ভূমিকা গুছানো করে রাখা।"},{"a":10,"b":11,"text":"এখানে এই ফাইলের একটা VERIFIED QUIRK: <code>import time</code> আর <code>from time import sleep</code> — দুটোই import করা হয়েছে, কিন্তু পুরো ১৪৬ লাইনে এই দুটো নাম আর কোথাও ব্যবহৃত হয় না; দুটোই dead import। ফলাফল: behavior-এ শূন্য প্রভাব, খরচ শুধু import-এর মুহূর্তে সামান্য সময়। সম্ভাবনা এটাই যে অন্য কোনো স্ক্রিপ্ট থেকে copy-paste করতে গিয়ে বাড়তি লাইন দুটো রয়ে গেছে (inferred)। জরুরি তথ্যটা উল্টোদিকে: registerScan callback-এর গতি কোনো <code>sleep()</code> দিয়ে throttle করা হয় না — /scan-এ message আসার হারই loop-এর pace ঠিক করে।"},{"a":12,"b":12,"text":"<code>from yahboom_M3Pro_laser.common import *</code> — star-import: ওই module-এর সব public নাম এই ফাইলের namespace-এ ঢুকে যায়। পাশের comment বলছে <code># Custom Yahboom tools (like Bool message and SinglePID)</code>, আর এই ফাইল আসলে ঠিক দুটো নামই সেখান থেকে নেয়: <code>Bool</code> (L25-এর /JoyState subscription আর L53-এর type guard) আর <code>SinglePID</code> (L47, L49 — linear আর angular দুটো PID controller)। মনে রাখতে হবে এই <code>Bool</code> Yahboom-এর common-module-এর Bool, std_msgs-এর Bool নয়। QUIRK: <code>yahboom_M3Pro_laser.common</code> module-টা এই folder-এ নেই, ভেতরের implementation আমাদের দেখা হয়নি — তাই SinglePID-এর ভেতরের হিসাব (sign convention সহ) যা-ই বলা হোক তা inferred/illustrative হিসেবেই থাকবে; এই ফাইল থেকে নিশ্চিতভাবে শুধু এতটুকু বলা যায় — constructor-কে কোন argument দিয়ে ডাকা হয়েছে আর method-এর নাম <code>pid_compute</code>।"},{"a":13,"b":13,"text":"<code>import os</code> — পুরো ফাইলে এর ব্যবহার একটাই জায়গায়: exit_pro-র L133-এ <code>os.system(cmd)</code>। node বন্ধ হওয়ার সময় shell-এর ভেতর দিয়ে একবার zero-velocity <code>/cmd_vel</code> message publish করা হয় — node মরে যাওয়ার পথেও যেন চাকা থেমে যায়, সেই বাইরের নিরাপত্তা-ব্যবস্থা। এই head-অংশে os-এর আর কোনো কাজ নেই।"},{"a":14,"b":15,"text":"<code>print (\"improt done\")</code> — সব import শেষে console-এ ছাপা হয়; বানানের দিকে তাকান: “improt” — typo-টা source-এ নিজেই, আর পাশের comment <code># (Typo in original: means \"import done\")</code> নিজেই স্বীকার করে এর অর্থ “import done”। লাইনটা module-এর top level-এ বলে node তৈরি হওয়ার আগেই, import-এর মুহূর্তে চলে — console-এ এই লাইন দেখা মানেই module লোড হয়েছে, এটুকুই এর কাজ। এরপর <code>RAD2DEG = 180 / math.pi</code> — module-level constant, মান 57.29577951…; radian থেকে degree-তে যাওয়ার গুণন-factor। LaserScan message-এর সব কোণ radian unit-এ আসে, কিন্তু L70-এর cone-test <code>abs(angle)</code>-এর মান <code>self.LaserAngle</code> (45.0, degree unit) parameter-এর সাথে তুলনা করে — দুই unit-এর এই মেলানোই L15-এর constant L67-এ গিয়ে করে দেয়।"}],"math":{"intro":"এই Part-এর গণিত একটাই প্রশ্নের উত্তর দেয়: L15-এর RAD2DEG constant-টা কোথা থেকে আসে আর এর মান কেন 57.2958 — অর্থাৎ radian থেকে degree-র unit-conversion-ই মূল বিষয়।","levels":[{"label":"Level 1 — Symbols & units","latex":"\\[ \\pi\\ \\mathrm{rad} = 180^{\\circ}, \\qquad 2\\pi\\ \\mathrm{rad} = 360^{\\circ} \\]","text":"radian হলো কোণের প্রাকৃতিক unit: অর্ধবৃত্ত = π rad = 180°, পূর্ণ বৃত্ত = 2π rad = 360°। LaserScan message-এর angle_min আর angle_increment এই unit-েই আসে — তাই fused ring-এ প্রথম beam-এর কোণ angle_min = -π হয় (illustrative, folder 09-এ রেকর্ড করা echo-র সাথে consistent)। θ চিহ্নটা যেকোনো কোণ, subscript শুধু unit-টা বোঝায়।"},{"label":"Level 2 — মৌলিক সম্পর্ক","latex":"\\[ \\theta_{\\mathrm{deg}} = \\theta_{\\mathrm{rad}} \\times \\frac{180}{\\pi}, \\qquad \\frac{180}{\\pi} \\approx 57.29577951 \\]","text":"দুই unit-এর অনুপাত থেকে গুণন-factor বের হয়: 180/π ≈ 57.2958, আর এটাই RAD2DEG-এর মান। কোণ ঋণাত্মক হলেও একই factor কাজ করে — চিহ্ন বাসী থাকে, মান গুণ হয়; তাই -π rad হয়ে যায় ঠিক -180°।"}],"numeric":[{"latex":"\\[ 0.0174533\\ \\mathrm{rad} \\times 57.29577951 \\approx 1.0^{\\circ} \\]","text":"illustrative: fused ring-এ প্রতিটা beam-এর ধাপ angle_increment = 0.0174533 rad (π/180-এর কাছাকাছি; folder 09-এ রেকর্ড করা echo-র সাথে consistent)। একে RAD2DEG দিয়ে গুণ করলে পাওয়া যায় প্রায় ঠিক 1.0° — অর্থাৎ প্রতিটা beam ঠিক ১ ডিগ্রি করে এগোয়, ৩৬০টা beam-এ পুরো বৃত্ত শেষ হয়।"},{"latex":"\\[ (-\\pi)\\ \\mathrm{rad} \\times 57.29577951 = -180^{\\circ} \\]","text":"illustrative: ring-এর প্রথম beam-এর কোণ angle_min = -π; রূপান্তরের পর সেটি -180°। L67-এর সূত্রে i = 0 হলে ঠিক এই মানই বের হবে, আর i প্রতি ধাপে বাড়লে কোণ ~1° করে বাড়ে — এই রূপান্তরই degree-জগতের পুরো scale-টা তৈরি করে।"}],"mapping":[{"code":"RAD2DEG = 180 / math.pi","math":"\\( k = \\frac{180}{\\pi} \\approx 57.2958\\ \\mathrm{deg/rad} \\)","text":"import-এর মুহূর্তে একবার হিসাব হয়ে মানটা constant হয়ে যায়; পরে L67-এ প্রতিটা beam-এর radian কোণের সাথে গুণ হয়ে সেটাকে degree-তে আনে — কারণ L70-এর cone-test করে LaserAngle parameter-এর (45.0, degree unit) সাথে তুলনা। unit না মিললে ওই তুলনাটাই অর্থহীন হয়ে যেত।"}],"failure":["গুণকটা উল্টে যদি কেউ RAD2DEG-এর জায়গায় math.pi / 180 (মান 0.01745) বসাত, তাহলে L67 সেই ছোট গুণকটাকে beam-এর radian মানের সাথেই গুণ করত — সত্যিকারের 45° beam-এর radian মান 0.7854, আর 0.7854-কে 0.01745 দিয়ে গুণ করলে আসে 0.0137, অর্থাৎ 45°-এর বদলে রূপান্তরিত মান আসত মাত্র ~0.014 (এমনকি 180° মানে π rad beam-ও নামত মাত্র ~0.055-এ) — L70-এর cone-test (রূপান্তরিত কোণ কি 45-এর কম?) প্রায় পুরো 360° ring-এর beam-কেই “সামনে” মেনে নিত; robot পেছনে বা পাশের object-ও follow করার চেষ্টা করত, একটার পর একটার দিকে ঘুরতে ঘুরতে দিশেহারা হয়ে যেত (illustrative)।","উল্টো দিকের ভুল — conversion একটা কোণের ওপর দুবার প্রয়োগ (degree-কে আবার degree-এ রূপান্তর) — হলে প্রতিটা কোণ 57.3 গুণ ফুলে যায়: cone-টা ±45° থেকে সেঁটে যায় মাত্র ±0.785°-এ। minDistList তখন প্রায় সবসময় ফাঁকা, L82-এর dashes-branch-এ return — robot সামনের object-টাকেই আর দেখত না, চাকা এক মিলিমিটারও এগোত না (illustrative)।"]},"robot":{"correct":"Import pass-এ এই ১৫ লাইন চলার সময় robot সম্পূর্ণ নিস্ক্রিয় থাকে — কোনো node তৈরি হয়নি, কোনো /cmd_vel publish হয়নি, চাকা স্থির; README L3-এর launch থেকে LiDAR chain আগেই চলছে থাকলে sensor-রা ঘুরতে থাকে, কিন্তু এই module তখনও কিছু শুনছে না। Console-এ এই অংশের একমাত্র দৃশ্যমান ফল হলো \"improt done\" লাইনটা ছাপা — module ওই পর্যন্ত এসেছে এটাই প্রমাণ। এখানে বাঁধা RAD2DEG constant-টাই পরে L67-এ প্রতিটা beam-এর কোণ degree-তে এনে ±45° সামনের cone-টা সঠিক রাখবে, আর সেই cone থেকেই laser_Tracker_a1 সবচেয়ে কাছের object-টা খুঁজে 0.55 m দূরত্বে তাকে follow করবে।","incorrect":"ধরুন machine-এ yahboom_M3Pro_laser package-টাই install করা নেই — L12-এর star-import-এ module-টা সেখানেই আটকে যাবে: console-এ \"improt done\" ছাপা হবে না (L14-এ পৌঁছানোই হয়নি), কোনো node তৈরি হবে না, ros2 run command-টা import error নিয়ে মরবে, /cmd_vel-এ কিছু যাবে না — চাকা এক মুহূর্তও নড়বে না। আবার RAD2DEG-এর মান ভুল হলে রূপান্তর পরে beam-বাছাইকে ভুল করাবে: উল্টো গুণকে robot পেছনের object-ও follow করার চেষ্টা করে এলোমেলো ঘুরবে, দুবার প্রয়োগে সামনের সব object-ই তার কাছে অদৃশ্য হয়ে যাবে। আর dead import দুটো (time, sleep) মুছলেও বা রাখলেও behavior-এ তিলমাত্র পরিবর্তন নেই — এরা কোনো চাকা বা lidar-কে স্পর্শ করে না।"},"animType":null},{"n":6,"id":"part-06","fname":"laser_Tracker.py","enTitle":"Constructor — Subscriptions & Publisher","lang":"python","start":16,"end":29,"flags":[],"explain":[{"a":16,"b":18,"text":"<code>class laserTracker(Node):</code> — L15-এর <code>RAD2DEG</code> constant-এর পরে L16 একটা blank line দিয়ে module-এর মাথা (L1-15: comment, import, print, constant) শেষ, এখান থেকে ফাইলের আসল দেহ — behavior class-টা। L3-এ আনা <code>Node</code>-কে inherit করাতেই <code>create_subscription</code>, <code>create_publisher</code>, <code>declare_parameter</code> — node-হওয়ার সব যন্ত্রপাতি এই class-এর হাতে এসে যায়। <code>def __init__(self,name):</code> — constructor-এর একটাই argument: <code>name</code>, বাইরে থেকে স্পষ্ট করে দিতে হয়। এই <code>name</code>-ই পরে <code>main()</code> থেকে আসবে — <code>laserTracker(\"laser_Tracker_a1\")</code> (L137) — মানে ROS 2-এর নাম-জগতে node-টার নাম <code>laser_Tracker_a1</code>, অথচ Python class-এর নাম <code>laserTracker</code>; দুটো আলাদা জিনিস, একটাও অন্যটা থেকে তৈরি হয় না।"},{"a":19,"b":19,"text":"<code>super().__init__(name)</code> — inheritance-এর সবচেয়ে জরুরি লাইন। এটা না চললে <code>Node</code>-এর নিজের constructor চলেই না, <code>self</code>-এর ভেতরে node-হওয়ার অভ্যন্তরীণ তালিকাই তৈরি হয় না — পরের লাইনে <code>self.create_subscription(...)</code> ডাকতেই <code>AttributeError</code>-জাতীয় error উঠে আসত। <code>super()</code> মানে এখানে parent class <code>Node</code>; <code>name</code> হাতবদল হতেই node-এর নাম পাকা হয়ে যায়। ক্রমটাও নিয়মমাফিক: parent-এর constructor আগে, নিজের জিনিসপত্র পরে — Python inheritance-এর প্রথা। আর মনে রাখুন, import pass-এ শুধু class-টা ও তার def-গুলো bind হয়; এই constructor-এর দেহ চলে run phase-এ, <code>main()</code> যখন instance বানায় তখন।"},{"a":21,"b":22,"text":"<code># --- CREATING SUBSCRIBERS (Listeners) ---</code> আর <code># Listen to the 360-degree LiDAR scanner</code> — দুটোই comment, কিছু চালায় না; কিন্তু লেখকের প্রতিমানটা এখানেই: publisher একটা রেডিও স্টেশন, subscription একটা শ্রোতা — শ্রোতা নিজে কথা বলে না, message এলেই শুধু নিজের callback জাগায়। \"360-degree\" দাবিটা এই ফাইল নিজে সত্যি করে দেখাতে পারে না: এই node কোনো lidar চালায় না। README-র L3 launch চালালে folder 10-এর merger+filter chain সামনে-পেছনে দুই lidar-এর কাঁচা scan জুড়ে একটা পূর্ণ 360-degree ring বানায়, blind-spot পাকা করে — tracker শুনবে সেই ফলাফল। চোখ ওই chain-এর, সিদ্ধান্ত এই ফাইলের।"},{"a":23,"b":23,"text":"<code>self.sub_laser = self.create_subscription(LaserScan,\"/scan\",self.registerScan,1)</code> — প্রথম শ্রোতা: চোখ। চারটা argument: message-এর ধরন <code>LaserScan</code> (L5-এ আনা), topic <code>\"/scan\"</code> — merger+filter chain-এর শেষ ফলাফলের ঠিকানা, কোনো raw lidar topic নয়; callback <code>self.registerScan</code> (L56-এ সংজ্ঞাত; এই ফাইলের মগজ — সামনের ±45-degree cone-এর মধ্যে সবচেয়ে কাছের object খুঁজে তাকে 0.55 m দূরত্বে রেখে অনুসরণ করার পুরো হিসাব ওখানে); আর শেষের <code>1</code> = queue depth — পুরনো message জমিয়ে না রেখে সবসময় সবচেয়ে নতুন scan-টাই কাজে লাগানো। tracking-এ এটাই চাই: কয়েক scan পুরনো দূরত্ব মানে object-টা আসলে আর ওখানেই নেই।"},{"a":24,"b":25,"text":"<code># Listen to the joystick (so you can pause the AI and drive manually)</code> আর <code>self.sub_JoyState = self.create_subscription(Bool,'/JoyState', self.JoyStateCallback,1)</code> — দ্বিতীয় শ্রোতা: মানুষের হাত। <code>True</code> এলে <code>JoyStateCallback</code> (L52-54) শুধু একটা flag উল্টে দেয়, আর <code>registerScan</code> সেই flag পেলে প্রতিটা scan-তে সব-শূন্য <code>Twist</code> publish করে ফিরে আসে (L86-88) — AI pause, চাকা joystick-এর হাতে। সূক্ষ্ম জায়গাটা <code>Bool</code>-এর পরিচয়: এটা std_msgs-এর চেনা Bool নয়। L12-এর <code>from yahboom_M3Pro_laser.common import *</code> star-import থেকে আসা yahboom-এর নিজস্ব <code>Bool</code> — এই ফাইলে <code>std_msgs</code> নামে কোনো import-ই নেই। আর এই উৎস folder 11-এর সাথে মেলালে ছবিটা আরও পরিষ্কার হয়: laser_Avoidance-এর L12-তেও হুবহু এই একই star-import লাইন, ওই ফাইলেও <code>std_msgs</code> নামে কোনো import নেই — দুই node-ই নিজের <code>Bool</code> আনে একই yahboom common module থেকে, কোনো ফাইলই std_msgs/Bool ব্যবহার করে না। common module-টা এই folder-এ নেই, তাই <code>.data</code>-র বাইরে তার ভেতরটা অজানা — field-এর নাম আন্দাজে বানানো যাবে না। টপোলজি তবু folder 11-এর সাথে হুবহু এক: একই <code>/JoyState</code> শ্রোতা, depth-ও <code>1</code>।"},{"a":27,"b":28,"text":"<code># --- CREATING PUBLISHERS (Radio Stations) ---</code> আর <code># Tell the wheels to move</code> — শ্রোতার পাল্লায় এবার উল্টো দিক: রেডিও স্টেশন। এই class-এর একটাই কথা বলার মুখ — চাকার motor-কে <code>/cmd_vel</code>-এ বলা। কঙ্কালটা এক নিঃশ্বাসে মনে রাখুন: দুই কান ভেতরে (<code>/scan</code>, <code>/JoyState</code>), এক মুখ বাইরে (<code>/cmd_vel</code>)। folder 11-এর laser_Avoidance-এর সাথে wiring হুবহু এই — ফারাক কোথায়? avoidance node এই একই দুই কানের data দিয়ে বাধা এড়িয়ে পথ বানাত; tracker node একই data দিয়ে সবচেয়ে কাছের object-টাকেই ধরে পিছু নেয়। একই শরীর, উল্টো প্রবৃত্তি।"},{"a":29,"b":29,"text":"<code>self.pub_vel = self.create_publisher(Twist,'/cmd_vel',1)</code> — মুখ। message-এর ধরন <code>Twist</code> (L4): ভেতরে <code>linear</code> আর <code>angular</code> দুই field, প্রতিটাতে x, y, z; মেঝের robot-এ কাজে লাগে দুটোই — <code>linear.x</code> (সামনে-পেছনে, মিটার/সেকেন্ড) আর <code>angular.z</code> (নিজের কেন্দ্র ঘিরে ঘোরা, radian/সেকেন্ড)। পরের Part-গুলোর dual PID ঠিক এই দুই field-এই ভরবে। queue depth আবার <code>1</code>: পুরনো কমান্ড জমানোর দরকার নেই, শেষ সিদ্ধান্তটাই সব। এই লাইন শেষ হতেই node-টা হাত-পা-চোখ সব পেয়ে যায়; L31 থেকে শুরু হবে parameter-ঘোষণা — গতি আর দূরত্বের সীমা নিয়ে।"}],"math":null,"robot":{"correct":"main()-এর L137-এ <code>laserTracker(\"laser_Tracker_a1\")</code> call হলে ঠিক এই constructor-টাই চলে: <code>super().__init__(name)</code> node-কে নাম দেয়, তারপর দুই subscription আর এক publisher রেজিস্টার হয়ে যায়। README-র L3 launch আগে চালানো থাকলে folder 10-এর merger+filter chain-এর পূর্ণ 360-degree <code>/scan</code> ring আসতে শুরু করে — প্রতিটা scan <code>registerScan</code>-কে জাগায়, joystick ধরলে <code>/JoyState</code> <code>JoyStateCallback</code>-কে জাগায়, আর সিদ্ধান্ত বেরোয় এক পথে: <code>/cmd_vel</code>-এ <code>Twist</code>, যা সোজা চাকার motor পায়। lidar এই node-এর নিজের হাতে নয় — চোখ ওপরের chain-এর, এখানে শোনা আর চালানো।","incorrect":"<code>super().__init__(name)</code> বাদ পড়লে পরের লাইনেই <code>AttributeError</code> — console-এ traceback, <code>ros2 node list</code>-এ <code>laser_Tracker_a1</code> নামটা আসবেই না, <code>/cmd_vel</code>-এ publisher জন্মাবে না, চাকা স্থির। আরেকটা ভুল ধারণা: <code>Bool</code>-কে std_msgs-এর Bool ভেবে অন্য ধরনের message পাঠানো — তখন হয় message-ই callback পর্যন্ত পৌঁছাবে না, নয়তো L53-এর isinstance guard সেটাকে ফেরত দেবে; <code>Joy_active</code> কখনো <code>True</code> হবে না, মানুষ joystick ধরেও AI-কে থামাতে পারবে না — robot শেষ সিদ্ধান্তের চাকা-গতিতেই চলতে থাকবে। আর merger-এর কাঁচা topic-এ কান দিলে ring-এর অর্ধেক খালি আসবে — tracker অপূর্ণ দুনিয়া দেখে হিসাব করবে।"},"animType":"subPubGraph"},{"n":7,"id":"part-07","fname":"laser_Tracker.py","enTitle":"Four Parameters — Declare & Get","lang":"python","start":30,"end":39,"flags":[],"explain":[{"a":30,"b":31,"text":"L30-এর ফাঁকা লাইনটা publisher block-এর পরে বিভাজক মাত্র। L31-এর section comment <code># --- ROS 2 PARAMETERS (Speed &amp; Distance Limits) ---</code> ঘোষণা করে: constructor-এর এই অংশ চারটা ROS 2 parameter নথিভুক্ত করবে। Parameter মানে নাম-দেওয়া একটা value, যা node চালুর সময় <code>--ros-args -p linear:=0.8</code>-এর মতো করে code edit ছাড়াই override করা যায়। কিন্তু comment-এর 'Limits' শব্দে ভরসা করবেন না — নিচের লাইনগুলোতে দেখা যাবে, চারটার মধ্যে speed-সংক্রান্ত দুটো limit আসলে আর কোথাও পড়াই হয় না।"},{"a":32,"b":32,"text":"L32-এ প্রথম declare: <code>self.declare_parameter(\"linear\",0.5)</code> — node-এর parameter store-এ <code>linear</code> নামে default 0.5 সহ একটা entry খোলে; পাশের comment <code># Max forward speed (0.5 m/s)</code> একে সর্বোচ্চ সামনে-যাওয়ার গতি বলে পরিচয় করায়। Declare না করে get করলে rclpy exception ওঠে, তাই প্রতিটা get-এর আগে তার declare থাকা জরুরি। Default-টা Python float (0.5) বলে store-এ type হয় DOUBLE — পরের লাইনে ঠিক সেই কারণেই double field পড়া হবে।"},{"a":33,"b":33,"text":"L33-এ declare করা value ফেরানোর তিন-ধাপ chain: <code>self.get_parameter('linear').get_parameter_value().double_value</code>। ধাপ ১ — <code>self.get_parameter('linear')</code> node-এর parameter store থেকে ওই নামের <code>Parameter</code> object ধরে আনে। ধাপ ২ — <code>.get_parameter_value()</code> সেই object-এর type-সহ value-container বের করে। ধাপ ৩ — <code>.double_value</code> floating-point field-টা টেনে দেয়, ফলে <code>self.linear</code> = 0.5। VERIFIED QUIRK: <code>self.linear</code> এই assignment-এর পর পুরো file-এ আর কখনো পড়া হয় না — L102-এ <code>velocity.linear.x</code> সরাসরি PID-এর ফলাফল থেকে বসে, কোথাও কোনো clamp নেই। অর্থাৎ 0.5 m/s সীমা শুধু comment-এ বাঁচে, motor পর্যন্ত পৌঁছায় না।"},{"a":34,"b":35,"text":"L34-35 একই ছাঁচের দ্বিতীয় pair: <code>self.declare_parameter(\"angular\",1.0)</code> (comment <code># Max turning speed (1.0 rad/s)</code>), তারপর হুবহু একই chain <code>self.get_parameter('angular').get_parameter_value().double_value</code> দিয়ে <code>self.angular</code> = 1.0। এখানেও সেই এক VERIFIED QUIRK — <code>self.angular</code>-ও আর কখনো পড়া হয় না। L110-120-এ angular.z নির্ধারিত হয় PID-ফলাফল, sign branch আর <code>* 0.6</code> damping মিলিয়ে; declared 1.0 rad/s-এর ছোঁয়া সেখানে নেই। দুটো speed pair তাই সত্যিকারের safety limit নয় — নথি হয়ে বসে আছে শুধু।"},{"a":36,"b":37,"text":"L36-37 তৃতীয় pair, এবং এটাই প্রথম সত্যিকারের ব্যবহার: <code>self.declare_parameter(\"LaserAngle\",45.0)</code> (comment <code># Width of the front cone (45 degrees left and right)</code>), তারপর একই chain-এ <code>self.LaserAngle</code> = 45.0। এটি কাজে লাগে L70-এ: <code>if abs(angle) &lt; self.LaserAngle and ranges[i] !=0.0 :</code> — ডিগ্রিতে মাপা beam-এর angle কঠোরভাবে (strict <code>&lt;</code>) 45.0-এর কম হলে তবেই সে beam সামনের cone-এর ভেতরে গণ্য হয়। বামে-ডানে 45° মানে সামনের মোট 90° জানালা; ঠিক 45.0°-এ পড়া beam ভেতরে ঢোকে না।"},{"a":38,"b":39,"text":"L38-39 চতুর্থ ও শেষ pair: <code>self.declare_parameter(\"ResponseDist\",0.55)</code> — comment <code># The \"Sweet Spot\" distance to keep from the object (0.55 meters)</code> বলে object থেকে যে দূরত্ব ধরে রাখতে হবে; একই chain-এ <code>self.ResponseDist</code> = 0.55। এই value-ই node-এর মূল আচরণ চালায়: L96-এর deadzone যাচাই <code>abs(minDist - self.ResponseDist) &lt; 0.1</code>, আর L102-এ linear PID-এর target হিসেবে <code>-self.lin_pid.pid_compute(self.ResponseDist, minDist)</code>। মনে রাখুন: get হয় constructor-এ মাত্র একবার — launch-এর সময় <code>--ros-args</code> দিয়ে override করলে নতুন value attribute-এ ঢোকে, কিন্তু node চালু হয়ে যাওয়ার পরে <code>ros2 param set</code> করলে store বদলালেও সেই কপি আর বদলায় না।"}],"math":null,"robot":{"correct":"এই লাইনগুলো চলার পর node-এর parameter store-এ চারটা নাম বসে — linear 0.5, angular 1.0, LaserAngle 45.0, ResponseDist 0.55 — আর console-এ এরা নিজেরা কিছুই ছাপে না। পরের কাজে দুটো সত্যিই কাজে লাগে: LaserAngle 45.0 ঠিক করে LiDAR-এর সামনের ±45° cone-এর ভেতরের কোন কোন beam tracking-এর জন্য গণ্য হবে (L70), আর ResponseDist 0.55 হলো সেই stand-off দূরত্ব যেখানে object-কে ধরে রাখতে চায় robot (L96, L102)। ফলে tracking চালু থাকলে wheel-গুলো object-কে প্রায় 0.55 m দূরে রেখে এগিয়ে যায় ও ঘোরে।","incorrect":"ভুল অনুমান হলে যা হয়: 'linear 0.5 আর angular 1.0 হলো গতির ceiling' ভেবে বসা — আসলে <code>self.linear</code> আর <code>self.angular</code> কেউ আর পড়ে না, কোথাও কোনো clamp নেই। Illustrative হিসেবে: object 1.6 m দূরে হলে linear error অনুযায়ী Kp-view ফল প্রায় +1.05 m/s — declared 0.5-এর দ্বিগুণের বেশি কমান্ড wheel-এ গিয়ে robot-কে দ্রুত ছুটতে বাধ্য করে। উল্টো দিকে, launch-এ <code>-p linear:=0.2</code> দিয়ে সীমা নামালেও গতিতে তিলমাত্র পরিবর্তন আসে না — value-টা মরা attribute-এ কপি হয়ে শুধু পড়ে থাকে।"},"animType":null},{"n":8,"id":"part-08","fname":"laser_Tracker.py","enTitle":"State & Dual PID Controllers","lang":"python","start":40,"end":49,"flags":[],"explain":[{"a":40,"b":41,"text":"<code># --- STATE TRACKERS &amp; PID CONTROLLERS ---</code> — constructor-এর শেষ অংশের banner। L31 দিয়ে শুরু হওয়া parameter-ব্লক L39-এ শেষ; L40-এর blank line দুই অংশের মাঝের separator। এই নতুন অংশে constructor মোট তিনটা attribute জমা দেবে: একটা bool state flag আর দুটো PID controller object। নামের ভাগাভাগিই নকশাটা বোঝায়: STATE TRACKER মানে সময়ের সঙ্গে বদলে যাওয়া পরিস্থিতি ধরে রাখার ঘর, PID CONTROLLERS মানে সেই পরিস্থিতি থেকে চাকার গতির হিসাব বানানোর যন্ত্র — এই লাইনের পর থেকেই behavior-এর আসল ইঞ্জিন বসতে শুরু করে।"},{"a":42,"b":42,"text":"<code>self.Joy_active = False</code> — প্রথম state tracker: node-টার জন্মমুহূর্তের মোড। <code>False</code> মানে AI নিজেই গাড়ি চালাবে। এই মান সারা জীবনে বদলায় ঠিক এক জায়গায়: <code>/JoyState</code> topic-এ message এলে <code>JoyStateCallback</code> (L52-54) এটাকে <code>msg.data</code> দিয়ে overwrite করে। আর পড়া হয় <code>registerScan</code>-এর ভেতরে L86-তে: <code>True</code> হলে প্রতিটা scan-এ all-zero <code>Twist</code> publish করে সোজা return — মানুষ joystick ধরলে AI প্রতি scan-এ চাকা সক্রিয়ভাবে ব্রেক করে সরে দাঁড়ায়। কাজেই L42-এর এই একটা শব্দই ঠিক করে দেয় node-টা জন্ম থেকে কার হাতে থাকবে — joystick থেকে প্রথম message না আসা পর্যন্ত robot পুরোপুরি AI-এর নিয়ন্ত্রণে।"},{"a":43,"b":46,"text":"L43 blank line-এর পরে তিন লাইনের comment block — কোনো code চলে না, কিন্তু লেখক এখানে পুরো ফাইলের সবচেয়ে দামি ধারণাটা নিজের ভাষায় বুঝিয়ে রেখেছেন। <code># PID controllers are math algorithms that help the robot move smoothly toward a target</code> আর <code># without overshooting or stuttering.</code> — PID মানে এমন হিসাব যা target-এর দিকে মসৃণভাবে এগোয়: লাপিয়ে পার হয়ে যাওয়া (overshoot) নয়, আটকে আটকে কাঁপাও (stutter) নয়। তৃতীয় লাইন <code># This one controls forward/backward speed to maintain the 0.55m distance.</code> পরের লাইনে জন্মানো <code>lin_pid</code>-এর কাজ বেঁধে দেয়: L39-এর <code>ResponseDist</code> = 0.55 m দূরত্ব ধরে রাখা। এই comment block-টাই math section-এর সূত্রগুলোর সঙ্গে মেলানোর চাবিকাঠি।"},{"a":47,"b":47,"text":"<code>self.lin_pid = SinglePID(1.0, 0.0, 1.0)</code> — প্রথম controller; inline comment বলে তিনটা positional argument হলো <code># (Kp, Ki, Kd)</code> = (1.0, 0.0, 1.0)। <code>SinglePID</code> class এই ফাইলে লেখা নয় — এসেছে L12-এর star-import <code>from yahboom_M3Pro_laser.common import *</code> থেকে, আর সেই vendor module এই folder-এ নেই; ভেতরের হিসাব আমরা দেখিনি, তাই SinglePID-এর আচরণ সবটাই inferred। সংখ্যাগুলোর মানে: proportional gain 1, integral gain 0, derivative gain 1 — মাঝের শূন্যটা integral term-কে পুরো বাদ দেয়, কার্যত এটা একটা PD controller। আর সবচেয়ে জরুরি তথ্য: controller-টা এই constructor-এ মাত্র একবার জন্মায়, কিন্তু তার ভেতরের state পুরো জীবন টিকে থাকে — প্রতিটা scan callback-এ L102-এ <code>pid_compute</code> ডাকলেও object একই, আগের callback-এর স্মৃতি হারায় না। Ki আর Kd term যে স্মৃতির উপর চলে তার ব্যবস্থা এখানেই — Ki = 0 হওয়ায় জমা বলে কিছু থাকে না, কিন্তু Kd-এর হিসাব চলছে।"},{"a":48,"b":48,"text":"<code># This one controls left/right turning to keep the object centered in the camera.</code> — এই comment-এ একটা পুরোনো (stale) শব্দ লুকিয়ে আছে: <b>camera</b>। এই node-এ কোনো camera নেই — একমাত্র sensor subscription হলো L23-এর LiDAR-এর <code>/scan</code>, আর object-এর বামে-ডানে কতদূর সেটা মাপা হয় scan-এর angle থেকে (<code>minDistID</code>, ডিগ্রিতে)। comment-টা যে কাজের কথা বলছে তা সঠিক — পরের লাইনের controller-ই বামে-ডানে ঘুরিয়ে object-কে সামনে কেন্দ্রে রাখে — কিন্তু sensor-এর নামটা ভুল; সম্ভবত অন্য কোনো camera-ওয়ালা প্রজেক্ট থেকে শব্দটা বয়ে এসেছে (inferred)। এই একটা শব্দের ভুলের বিভ্রান্তি বড় — পাঠক camera topic খুঁজতে শুরু করলে পুরো debug ভুল পথে ঢুকে যাবে।"},{"a":49,"b":49,"text":"<code>self.ang_pid = SinglePID(2.0, 0.0, 2.0)</code> — দ্বিতীয় controller: একই <code>SinglePID</code> class, কিন্তু তিনটা gain-ই দুই গুণ — (2.0, 0.0, 2.0), এটাও PD। দুটো সম্পূর্ণ আলাদা instance: একটার ভেতরের state অন্যটাকে ছোঁয় না, দুই হিসাব পাশাপাশি চলে — একটার চোখ দূরত্বে (মিটারে), অন্যটার চোখ কোণে (পরে L107-এ দেখা যাবে, কোণকে 72 দিয়ে ভাগ করে ছোট সংখ্যায় নামানো হয়)। ইনপুটের এই স্কেল-পার্থক্যই gain দুই গুণ হওয়ার মূল কারণ — পূর্ণ যুক্তি math section-এ। এই লাইনেই constructor-এর সব কাজ শেষ: node-টা এখন চারটা parameter, একটা mode flag আর দুটো সজ্জিত PID নিয়ে ব্যবহারের জন্য প্রস্তুত; L50-51-এর blank-এর পরেই আসবে পরের def — <code>JoyStateCallback</code> (L52)।"}],"math":{"intro":"এই Part-এর গণিত একটাই প্রশ্নের উত্তর দেয়: <code>SinglePID(1.0, 0.0, 1.0)</code> আর <code>SinglePID(2.0, 0.0, 2.0)</code> — এই দুই ডাকের ভেতরে কোন হিসাব-ইঞ্জিন বসে আছে, আর তিনটা সংখ্যা ইঞ্জিনের কোন স্ক্রু ঘোরায়। vendor-এর SinglePID source এই folder-এ নেই, তাই নিচের গঠনটা standard PID আইন থেকে inferred — আউটপুটের সংখ্যাগুলো illustrative।","levels":[{"label":"Level 1 — Symbols ও units","latex":"\\[ e(t) = r(t) - y(t), \\qquad u(t), \\qquad K_p,\\ K_i,\\ K_d \\]","text":"প্রতিটা symbol: r = setpoint (target), y = measurement (বর্তমান মান), তাদের বিয়োগফল e = error, আর u = controller-এর আউটপুট। এই node-এ দুটো স্বাধীন loop: linear loop-এ r = 0.55 m (L39-এর ResponseDist), e মিটারে, u হয়ে যায় <code>linear.x</code> (m/s); angular loop-এ e পরে normalized কোণ থেকে আসবে, u হয়ে যায় <code>angular.z</code> (rad/s)। দুই loop-এর unit আলাদা — একই gain দুই জায়গায় একই আচরণ করবে না; এটাই Level 5-এর আলোচনার বীজ।"},{"label":"Level 2 — মূল PID আইন","latex":"\\[ u(t) = K_p\\,e(t) + K_i \\int_0^t e(\\tau)\\,d\\tau + K_d\\,\\frac{de(t)}{dt} \\]","text":"তিনটা term, তিন রকম দৃষ্টি: Kp-term দেখে শুধু এই মুহূর্তের ভুল (present); Ki-term দেখে জন্ম থেকে জমা ভুলের সমষ্টি (past); Kd-term দেখে ভুল কত দ্রুত বদলাচ্ছে (rate of change)। বড় ভুল মানে বড় ধাক্কা, আর ভুল শূন্য হলে তিনটা term-ই শূন্য — tracking-এর সুখসমাচার এখানেই: object 0.55 m দূরে ঠিক সামনে থাকলে দুই loop-ই চুপ।"},{"label":"Level 3 — Ki = 0: integral বাদ","latex":"\\[ u(t) = K_p\\,e(t) + K_d\\,\\frac{de(t)}{dt} \\qquad \\text{(PD controller)} \\]","text":"দুই controller-ই মাঝের সংখ্যাটা 0.0 রেখেছে — অতীতের ভুল জমার রাস্তা বন্ধ। ফলে কোনো স্থায়ী ছোট ভুল ফুলে উঠবে না (integral windup নেই) — আর এখানে সেই অনুপস্থিতি ক্ষতিও করে না, কারণ L96-এর deadzone যাবতীয় ছোট ভুল আগেই ক্ষমা করে শূন্য করে দেয়। মনে রাখার কথা: ভুল-জমা বন্ধ করাটা gain-এর গুণ নয়, গঠনের গুণ — দুই object-এর জন্মসনদে (L47, L49) সেটা লেখাই আছে।"},{"label":"Level 4 — Kd কী দেখে","latex":"\\[ \\dot{e} = \\frac{de}{dt}, \\qquad e_{k-1} = 0,\\ e_k = -0.35 \\ \\text{(step change)} \\]","text":"Kd-term ভুলের হার মাপে। নতুন controller-এ আগের ভুল শূন্য ধরা যাক (inferred) — তাহলে প্রথম scan callback-এ ভুল শূন্য থেকে লাফিয়ে সরাসরি e-তে ওঠে: এটা step change, আর step-এর হার বিশাল। সেইজন্যই প্রথম ডাকে Kd-term Kp-term-এর একই সাইনে একটা বড় অস্থায়ী ধাক্কা (transient) যোগ করে — Wave A-তে ঠিক এটাই ঘটে (নিচে numeric)। এর পরে robot এগোলে ভুল কমার হার অনুযায়ী এটা পথে ব্রেকের ভূমিকা নেয় — L44-45 comment-এর overshoot-নয় প্রতিশ্রুতির ভিত্তি এই term-ই (গঠন inferred)।"},{"label":"Level 5 — দুই loop, দুই gain","latex":"\\[ u_{lin} = 1.0\\,e_{lin}\\ (\\text{m}), \\qquad u_{ang} = 2.0 \\cdot \\frac{|a|}{72},\\quad |a| &lt; 45^\\circ \\]","text":"angular loop-এর কাঁচা ইনপুট হলো কোণ a ডিগ্রি — কিন্তু L107-এ তাকে 72 দিয়ে ভাগ করা হয়, তাই 45 ডিগ্রির বড় ভুলও মাত্র 45/72 = 0.625। linear loop-এর ভুল কিন্তু মিটারে সরাসরি — সহজেই 0.35 বা তার বেশি। অর্থাৎ angular-এর ইনপুট-স্কেল অনেক ছোট, আর সেই ঘাটতি পূরণেই gain দুই গুণ: 2.0 x 0.625 = 1.25 পর্যন্ত যাওয়া সম্ভব (L120-এর 0.6 damping-এর আগে)। 72 সংখ্যাটা কোথা থেকে এলো ফাইল কখনো বলে না — একটা bare magic number; gain-অনুপাতের এই ব্যাখ্যাটাও inferred tuning-যুক্তি, প্রমাণ নয়।"},{"label":"Level 6 — Discrete রূপ ও persistent state","latex":"\\[ u_k = K_p\\,e_k + K_i \\sum_{j=1}^{k} e_j\\,\\Delta t + K_d\\,\\frac{e_k - e_{k-1}}{\\Delta t} \\]","text":"robot-এর জগৎ অবিচ্ছিন্ন নয় — হিসাব চলে scan callback ধরে ধরে, ব্যবধান Δt। তখন integral হয় জমা যোগফল, derivative হয় পরপর দুই ভুলের পার্থক্য ভাগ Δt। দুই term-এরই স্মৃতি দরকার: যোগফলের খাতা আর আগের ভুল — আর সেই স্মৃতি জমে থাকে controller object-এর ভেতরে। L47/L49-এ controller-দের একবারই জন্ম দেওয়ার মানে এখানে খুলে যায়: registerScan-এর ভেতরে প্রতি scan-এ নতুন করে বানালে খাতা প্রতিবার শূন্য থেকে শুরু হতো। (SinglePID-এর আসল discrete রূপ vendor module-এ — এটা standard textbook রূপ, inferred।)"}],"numeric":[{"latex":"\\[ e_{lin} = 0.55 - 0.90 = -0.35\\ \\mathrm{m}, \\qquad u_{lin} \\approx 1.0 \\times (-0.35) = -0.35 \\]","text":"Wave A (illustrative): pillar সামনে 0.90 m, +12 ডিগ্রি। Kp-term একা ধরলে lin_pid-এর আউটপুট প্রায় -0.35; L102-এর সামনের minus চিহ্ন এটাকে <code>linear.x = +0.35</code> m/s করে দেয় — কাছে যাওয়ার দিক। দিক-সিদ্ধান্তটা L100-101 comment-এর বক্তব্য থেকে inferred: vendor-এর ভেতরের sign convention ফাইল দেখে প্রমাণ করা যায় না।"},{"latex":"\\[ e_{k-1} = 0,\\ e_k = -0.35 \\ \\Rightarrow\\ K_d\\text{-term} = 1.0 \\cdot \\frac{-0.35 - 0}{\\Delta t} \\]","text":"প্রথম callback-এর step (illustrative): নতুন controller-এ আগের ভুল 0 ধরলে (inferred) Kd-term দাঁড়ায় -0.35/Δt — Δt ছোট বলে মানটা বড়, সাইনে Kp-term-এর মতোই ঋণাত্মক; অর্থাৎ প্রথম ডাকে approach-এর ধাক্কা একটু বাড়ে। পরের callback-গুলোতে ভুল আর step নয় — transient শান্ত হয়ে আসে।"},{"latex":"\\[ e_{ang} = \\tfrac{12}{72} - 0 = 0.1667, \\qquad u_{ang} \\approx 2.0 \\times 0.1667 = 0.333 \\]","text":"একই Wave A-র কোণ-হিসাব (illustrative): object কেন্দ্র থেকে +12 ডিগ্রি। ang_pid-এর Kp-term 0.333 — gain দুই গুণ হওয়ায় এই মান; Kp = 1 হলে হতো 0.167। এই 0.333 পরে L117-এর turn deadzone-এর 0.5 থ্রেশহোল্ড ছুঁতে পারে না, তাই angular.z শূন্য হয়ে যাবে — 12 ডিগ্রি এত ছোট ভুল যে robot এই মুহূর্তে শুধু দূরত্ব কমাবে, ঘুরবে না।"},{"latex":"\\[ e_{lin} = 0.55 - 0.70 = -0.15\\ \\mathrm{m}, \\qquad u_{ang} = 2 \\times \\tfrac{20}{72} = 0.556 \\ge 0.5 \\]","text":"Wave B (illustrative): 0.70 m, +20 ডিগ্রি। linear.x প্রায় +0.15 m/s — ধীরে এগোনো; angular এবার deadzone পার হয়: 0.556 থ্রেশহোল্ড ছাড়ায়, L120-এর 0.6 গুণ হয়ে angular.z প্রায় +0.33 rad/s — বাঁয়ে ঘোরা। এই Part-এ জন্মানো দুই controller প্রথমবার একসাথে অশূন্য আউটপুট দেয়।"},{"latex":"\\[ |0.58 - 0.55| = 0.03 &lt; 0.1 \\ \\Rightarrow\\ e_{lin} := 0 \\Rightarrow\\ u_{lin} = 0,\\ u_{ang} = 0 \\]","text":"Wave C (illustrative): 0.58 m, ঠিক 0 ডিগ্রি। L96-এর deadzone দূরত্বকে 0.55-এ snap করে — ভুল শূন্য, আর শূন্য ভুলে আইনের তিনটা term-ই শূন্য; কোণটাও ঠিক 0 বলে কোনো sign branch চলেই না। চাকা থেমে থাকে — এটাই lock-on অবস্থা। আর Ki = 0 বলে অতীতে কিছু জমেও নেই যে এখন বেরিয়ে এসে গড়াবে।"}],"mapping":[{"code":"self.Joy_active = False","math":"\\( s_{\\mathrm{AI}} = 1 \\)","text":"জন্মমান False মানে AI-loop চালু। flag-টা আসলে পুরো PID-হিসাবের উপরে বসানো একটা enable switch: <code>/JoyState</code> থেকে True এলে L86-তে হিসাব শুরুর আগেই loop বন্ধ, প্রতিটা scan-এ all-zero <code>Twist</code>।"},{"code":"self.lin_pid = SinglePID(1.0, 0.0, 1.0)  # (Kp, Ki, Kd)","math":"\\( u_{lin} = 1.0\\,e_{lin} + 0 \\cdot \\int e\\,dt + 1.0\\,\\dot{e}_{lin} \\)","text":"তিনটা positional argument ঠিক আইনের তিনটা coefficient — বাঁ থেকে Kp, Ki, Kd। মাঝের 0.0 বসানো মাত্রই integral term গুণে শূন্য: দুই term-এর হিসাবই টিকে থাকে। এই object-টাই পরে L102-এ <code>pid_compute</code> হয়।"},{"code":"self.ang_pid = SinglePID(2.0, 0.0, 2.0)","math":"\\( u_{ang} = 2.0\\,e_{ang} + 2.0\\,\\dot{e}_{ang} \\)","text":"গঠন হুবহু আগেরটার মতো, শুধু দুইটা coefficient-ই দুই গুণ — angular-এর ছোট normalized ইনপুট (|angle|/72) থেকে যথেষ্ট ঘুরা বের করার জন্য। call হয় L107-এ।"},{"code":"pid_compute(target, current)","math":"\\( e = \\text{first} - \\text{second} \\)","text":"ফাইলে ডাকের ক্রম লেখা আছে (target, current): linear-এ (0.55, minDist), angular-এ (|minDistID|/72, 0)। ভেতরে বিয়োগটা কোন দিকে হয় তা vendor module না দেখে অনিশ্চিত — as-written পাঠে first-second (inferred)।"}],"failure":["Ki-এর জায়গায় বড় মান বসালে (যেমন 1.0): object অনেকক্ষণ 0.90 m দূরে দাঁড়িয়ে থাকলে প্রতি scan callback-এ e = -0.35 জমে যেত, আউটপুট সীমাহীন বাড়ত — আর L33-এর declared linear limit কোথাও enforce হয় না বলে চাকা ক্রমবর্ধমান বেগে pillar-এ গিয়ে ধাক্কা লাগত (illustrative; আসল কোডে Ki = 0)।","দুই controller-এর gain অদল-বদল হলে (linear-এ 2.0): মাত্র 0.90 m ভুলেই u = 2 x (-0.35) = -0.70, অর্থাৎ linear.x = +0.70 m/s — declared max 0.5-ও ছাড়িয়ে গেল। robot 0.55 m stand-off-এ না থেমিয়ে জোরে এগিয়ে গিয়ে overshoot করবে; সামনে মানুষ থাকলে বিপজ্জনক।","L48-এর camera শব্দটা সত্যি ধরে নিলে: এই node কোনো camera topic subscribe-ই করে না, centering-এর একমাত্র সংকেত LiDAR <code>/scan</code>-এর angle (minDistID)। ভুল sensor-এর পিছনে debug করলে সমাধান আর আসবে না — robot ততক্ষণ ঢেলে বসে থাকবে।","<code>Joy_active</code>-এর জন্যমান True হলে, আর <code>/JoyState</code> থেকে কোনো message না এলে: L86-এর gate চিরকাল মানুষের মোডে আটকে থাকবে — প্রতিটা scan-এ all-zero Twist ঢালা হবে, চাকা এক মুহূর্তের জন্যও ঘুরবে না, console-এ scan-প্রতি দূরত্বের ছাপও পড়বে না (L86 আগেই return করে ফেলে, L91-92 আর পৌঁছায় না)।","controller-দুটো constructor-এর বদলে registerScan-এর ভেতরে বানালে: প্রতি scan-এ object-এর স্মৃতি (আগের ভুল, জমা যোগফল) শূন্য থেকে শুরু — Kd-term তখন প্রতিবার প্রথম-ডাকের step-transient-ই দেয়, গতির প্রকৃত হার কখনো মাপতে পারে না; চলা হয়ে ওঠে কাঁপা (গঠন inferred)।"]},"robot":{"correct":"এই দশ লাইন চলার মুহূর্তে robot স্থির — constructor-অংশ, চাকায় কোনো command যায় না, এই লাইনগুলোর নিজস্ব কোনো console-ছাপও নেই। node জন্মায় AI-মোডে (<code>Joy_active = False</code>) আর হাতে নেয় দুটো সজ্জিত PD ইঞ্জিন: lin_pid (1, 0, 1) দূরত্বের জন্য, ang_pid (2, 0, 2) কোণের জন্য। sensor chain থেকে প্রথম fused scan এলেই ইঞ্জিন-দুটি কাজে নামে (illustrative): Wave A-তে (0.90 m, +12 ডিগ্রি) lin_pid বের করে প্রায় -0.35, L102-এর minus চাকাকে দেয় +0.35 m/s সামনে; ang_pid-এর 0.333 পরের deadzone-এ শূন্য হয়, তাই robot সোজা এগিয়ে যায়, ঘোরে না। Wave C-তে (0.58 m, 0 ডিগ্রি) দুই ইঞ্জিনই শূন্য আউটপুট দেয় — চাকা থেমে, robot 0.55 m stand-off-এ বসে থাকে।","incorrect":"এই অংশকে প্রতি scan-এ চলতে ভাবাটাই প্রথম ভুল — এটা node জন্মানোর সময় একবারই চলে, তাই এখানকার ভুল জন্ম থেকে আটকে থাকে। <code>Joy_active</code>-এর জন্মমান True হলে আর joystick থেকে কোনো message না এলে প্রতিটা scan-এ all-zero Twist ঢালা হবে — চাকা এক মুহূর্তও ঘুরবে না, LiDAR ঘুরতে থাকলেও console-এ scan-প্রতি দূরত্বের ছাপ আসবে না কারণ L86 আগেই return করে ফেলে। gain অদল-বদল করলে (linear-এ 2.0) 0.90 m ভুলেই linear.x প্রায় +0.70 m/s — কোনো clamp নেই বলে robot দ্রুত ছুটে গিয়ে 0.55 m পার হয়ে যাবে, সামনের মানুষকে ধাক্কা দেবে। আর L48-এর camera শব্দে বিভ্রান্ত হয়ে camera-র দিকে তাকালে debug ভুল পথে যাবে — centering-এর একমাত্র সংকেত LiDAR-এর <code>/scan</code> angle।"},"animType":null},{"n":9,"id":"part-09","fname":"laser_Tracker.py","lang":"python","enTitle":"JoyStateCallback — Human Override","start":50,"end":54,"flags":[],"explain":[{"a":50,"b":52,"text":"L49-এ constructor শেষ হওয়ার পর L50-L51 দুটি blank line class-body-কে ভাগ করে রাখে — এখানে কোনো execution নেই, শুধু readability-র separator। এরপর L52-তে প্রথম method-এর header: <code>def JoyStateCallback(self, msg):</code>। Import-pass-এ Python শুধু def-টি compile করে <code>JoyStateCallback</code> নামটি class-body-তে bind করে — body তখন চলে না। নামটির ব্যবহার ছিল L25-এ: <code>self.create_subscription(Bool,'/JoyState', self.JoyStateCallback,1)</code>। অর্থাৎ <code>/JoyState</code> topic-এ নতুন message এলেই rclpy-র executor এই function-টিকে <code>msg</code> আর্গুমেন্ট দিয়ে ডাকে — joystick যখন pause-request পাঠায়, ঠিক তখনই এটি fire করে।"},{"a":53,"b":53,"text":"L53 হলো type guard, এক লাইনে লেখা combined if+return: <code>if not isinstance(msg, Bool): return</code>। এই <code>Bool</code> বলতে std_msgs-এর Bool নয় — L12-এর star-import <code>from yahboom_M3Pro_laser.common import *</code> থেকে আসা Yahboom-এর custom Bool class (L12-এর comment নিজেই বলে: like Bool message)। ওই common module-টি এই folder-এ নেই, তাই <code>.data</code> ছাড়া এর ভেতরের layout জানা যায় না — অজানা জিনিস নিয়ে অনুমানও করা হবে না। Guard-এর কাজ: কোনোভাবে <code>Bool</code> নয় এমন object ঢুকলে function-টি সঙ্গে সঙ্গে ফিরে যায়, <code>self.Joy_active</code>-এর আগের মান অপরিবর্তিত থাকে — ভুল ধরনের message দিয়ে state নষ্ট হয় না। একই defensive প্যাটার্ন scan-callback-এর শুরুতেও আছে (L57: <code>if not isinstance(scan_data, LaserScan): return</code>)।"},{"a":54,"b":54,"text":"L54-তেই callback-এর আসল state-changing কাজ: <code>self.Joy_active = msg.data</code> — message-এর boolean payload-টি instance-flag-এ জমা হয়। Flag-টির জন্ম L42-তে <code>self.Joy_active = False</code> হিসেবে, অর্থাৎ node চালু হলে শুরুতে AI-ই নিয়ন্ত্রণে থাকে। Trailing comment-টি (verbatim): <code># If True, human is driving, AI should pause</code> — <code>True</code> মানে মানুষ গাড়ি চালাচ্ছে, tracking-AI pause হবে; <code>False</code> এলে AI আবার নিয়ন্ত্রণ ফিরে পায়। এই একটি assignment-ই পুরো callback-এর সব পার্শ্বপ্রভাব।"},{"a":52,"b":54,"text":"সমগ্র callback-টি মোটে দুই লাইনের কাজ — message validate করা, তারপর একটি boolean save করা; এখানে কোনো motor command বা publish নেই। Override কার্যকর হয় পরের scan-এ: registerScan-এর L86 <code>if self.Joy_active :</code> দেখে True হলে L87 <code>self.pub_vel.publish(Twist())</code> পাঠায় (সব মান zero একটি Twist — চুপচাপ বসে থাকা নয়, প্রতিটি scan-এ বারবার পাঠানো একটি active brake) এবং return করে। L25-এ queue depth 1, তাই একগুচ্ছ পুরনো message জমে জীবিত থাকে না — flag সাধারণত সবচেয়ে নতুন অবস্থাটিই reflect করে। Illustrative Wave D: মানুষ stick ধরলে <code>/JoyState</code>-এ data True আসে, প্রতিটি /scan-এ zero-Twist যেতে থাকে; stick ছাড়ার সাথে False আসে এবং পরের scan থেকে dual-PID tracking আবার চালু হয়।"}],"math":null,"robot":{"correct":"চালু হওয়ার সময় flag-টি False (L42) ছিল, তাই wheels স্বাভাবিক tracking করছিল। মানুষ joystick-এর stick ধরলে <code>/JoyState</code>-এ <code>msg.data = True</code> publish হয় এবং এই callback-টি flag ঘুরিয়ে দেয়। এরপর প্রতিটি /scan message-তে node-টি <code>/cmd_vel</code>-এ সব-zero Twist পাঠায় (L86-88) — wheel motor-গুলো 0 velocity command পায়, robot স্থির হয়ে যায়। Lidar-এর ঘূর্ণন ও /scan flow অপরিবর্তিত থাকে, কিন্তু console-এ <code>minDist:</code> ও <code>minDistID:</code> লাইনগুলো বন্ধ হয়ে যায়, কারণ early return সেগুলোর আগেই বেরিয়ে আসে। Stick ছাড়ার সাথে সাথে False এলে পরের scan থেকেই PID tracking আবার শুরু হয়।","incorrect":"ধরুন guard-টি ভুল ধরনের <code>Bool</code>-এর বিরুদ্ধে মিলিয়ে দেখত (যেমন কেউ এটিকে std_msgs-এর Bool করে দিল) — তাহলে প্রতিটি incoming message-এ <code>isinstance(msg, Bool)</code> False হতো, callback প্রতিবার L53-তেই return করত, আর <code>self.Joy_active</code> চিরকাল L42-এর False-ই থাকত। ফলে pause path (L86-88) কখনোই চালু হতো না: মানুষ stick ধরে আছে, অথচ robot তখনও সামনের সবচেয়ে কাছের object ছুটে গিয়ে 0.55 m stand-off ধরার চেষ্টা করছে — wheels PID-command মানছে, console-এ minDist লাইন দৌড়চ্ছে, হাতের নিয়ন্ত্রণ আর machine-এর ধাওয়ার মধ্যে টানাপোড়েন। উল্টো দিকে flag যদি কোনোভাবে আটকে True হয়ে থাকে (মানুষ ছেড়ে দিলেও False না আসে), তাহলে tracker-টি scan-rate-এ zero-Twist পাঠানো একটি স্থায়ী brake হয়ে দাঁড়ায় — object সামনে থাকুক বা না থাকুক, wheels আর ঘোরে না।"},"animType":null},{"n":10,"id":"part-10","fname":"laser_Tracker.py","enTitle":"registerScan — Beam Loop & Front Cone","lang":"python","start":55,"end":72,"flags":[],"explain":[{"a":55,"b":56,"text":"L55 নিছক একটা blank line — JoyStateCallback (L52-54) আর নতুন function-এর মাঝের দৃশ্যমান বিভাজক। L56-তে <code>def registerScan(self, scan_data):</code> — এই node-এর পুরো behavior core। L23-এর subscription ঠিক এই নামটাই (<code>self.registerScan</code>) register করেছিল, তাই folder-10-এর merge+filter chain থেকে আসা fused <code>/scan</code>-এর প্রতিটি message-এ ROS 2 executor এই function-টাকে ডাকে। INPUT হলো একটা <code>LaserScan</code> message; যাত্রা L125-এর <code>Twist</code> publish-এ গিয়ে শেষ হবে — কিন্তু তার আগে এই Part-এ চলবে candidate-খোঁজার পর্ব।"},{"a":57,"b":57,"text":"L57 <code>if not isinstance(scan_data, LaserScan): return</code> — type guard। L53-এর JoyStateCallback guard-এর ঠিক একই প্যাটার্ন: message-টা যদি কোনো কারণে <code>LaserScan</code> না হয়, callback কিছু না করেই return করে — crash নয়, শুধু ওই একটা scan বাদ। ফলে ভুল type-এর কোনো stray message পুরো node-কে ফেলে দিতে পারে না।"},{"a":58,"b":58,"text":"L58 <code>ranges = np.array(scan_data.ranges)</code> — message field-এর Python list-টাকে numpy array-তে convert করা হলো। প্রতিটি element একটা beam-এর measured distance, unit meter; পরের loop সরাসরি <code>ranges[i]</code> দিয়ে index করবে। array-র length N মানে beam-সংখ্যা — fused ring-এ 360 (illustrative), অর্থাৎ নিচের loop-টি প্রতি scan-এ 360 বার ঘুরবে।"},{"a":59,"b":62,"text":"L60-এর comment ঘোষণা করে <code># We will search for the absolute closest object in the front 90-degree cone</code> — 90° মানে মোট window: বাঁয়ে 45° আর ডানে 45°। L61-62-তে সেই খোঁজার জন্য দুটো PARALLEL খালি list: <code>minDistList = []</code> distance-গুলোর জন্য, <code>minDistIDList = []</code> angle-গুলোর জন্য। নামে 'ID' হলেও এখানে beam-এর index নয় — beam-এর DEGREE angle জমা হবে। একই list-position-এ থাকবে একই beam-এর distance আর angle-এর জোড়া; L77 ও L79-এর min-search পুরোপুরি এই pairing-এর উপরেই দাঁড়িয়ে। প্রতিটা scan-এ fresh খালি list দিয়ে শুরু হয়, তাই আগের scan-এর পুরোনো data কখনো মেশে না।"},{"a":63,"b":65,"text":"L64-এর comment যেমন বলছে, L65-এর <code>for i in range(len(ranges)):</code> প্রতিটা beam-কে ঠিক একবার করে ঘুরে দেখে — i = 0 থেকে N-1, কোনো আগাম বাদ নেই। সামনে-পেছনে-পাশে সব beam-ই এই pass-এ আসে; বাছাই করবে ভেতরের L70 filter। এটি একটা linear sweep — প্রতি scan-এ N-টা (illustrative 360) iteration।"},{"a":66,"b":67,"text":"L67-এ এই Part-এর মূল সূত্র: <code>angle = (scan_data.angle_min + scan_data.angle_increment * i) * RAD2DEG</code>। header-এর দুটি field — <code>angle_min</code> (প্রথম beam-এর direction, radian unit-এ) আর <code>angle_increment</code> (পরপর দুটো beam-এর কৌণিক ফাঁক, radian-এ) — আর L15-এর <code>RAD2DEG = 180 / math.pi</code> (= 57.2958…) মিলে index i-কে degree angle-এ বদলায়। folder-10 chain-এর echo values বসালে (angle_min = -3.14159, angle_increment = 0.0174533, illustrative) প্রতিটা beam ঠিক 1° করে ওঠে: angle_i = -180 + i degree — i = 180 মানে dead-ahead 0°, i = 0 মানে একেবারে পেছনে -180°। মনে রাখো, code নিজে কিছুই hard-code করে না — সব মান message header থেকে পড়ে।"},{"a":68,"b":70,"text":"L70-এর filter: <code>if abs(angle) &lt; self.LaserAngle and ranges[i] !=0.0 :</code> — দুটো শর্ত AND দিয়ে যুক্ত। প্রথমটা front cone test: LaserAngle = 45.0 (L36-37), কিন্তু inequality-টা STRICT, তাই window-টা open interval (-45°, +45°) — ঠিক -45.0° বা ঠিক +45.0°-র beam বাদ। illustrative ring-এ মানে i = 136…224, মোট 89টা beam ভেতরে। দ্বিতীয়টা validity test: <code>ranges[i] !=0.0</code> exact 0.0-কে invalid sentinel ধরে বাদ দেয়। Honest edge: LaserScan convention-এ no-return beam-এর মান +inf, আর Python-এ <code>inf != 0.0</code> হলো True — তাই inf reading এই filter পেরিয়েই যায়। code-এর প্রকাশ্য assumption: upstream chain no-return-গুলোকে আগেই 0.0 বানিয়ে রেখেছে; না বানালে খোলা corridor-এ inf সোজা list-এ ঢুকবে।"},{"a":71,"b":72,"text":"শর্ত পাস করা beam এবার জমা হয়: L71 <code>minDistList.append(ranges[i])</code> distance-টা রাখে, L72 <code>minDistIDList.append(angle)</code> ওই beam-এর degree angle-টা রাখে। দুটো append সবসময় জোড়ায় জোড়ায় চলে, তাই দুই list-এর same position-এ সবসময় একই beam-এর দুটো মান। এই ধাপে এখনো কোনো min নেই, wheel-এ কিছুই যায় না — শুধু পরের Part-এর min-search-এর candidate shortlist তৈরি হলো। Wave A-এর pillar (0.90 m, +12°, illustrative) ঠিক এভাবেই list-এ ঢুকে পরে minDist = 0.90, minDistID = +12 হবে।"}],"math":{"intro":"এই Part-এর গণিত দুটো প্রশ্নের উত্তর দেয়: beam index i থেকে ওই beam-এর direction-angle degree-এ কত হয়, আর কোন কোন beam front cone-এর ভেতরে পড়ে shortlist-এ ঢোকে।","levels":[{"label":"Level 1 — Symbols & units","latex":"\\[ i = \\text{beam index},\\qquad \\theta_{\\min} = \\texttt{angle\\_min}\\ [\\mathrm{rad}],\\qquad \\Delta\\theta = \\texttt{angle\\_increment}\\ \\left[\\tfrac{\\mathrm{rad}}{\\mathrm{beam}}\\right],\\qquad \\mathrm{RAD2DEG} = \\frac{180}{\\pi} = 57.2958\\ \\left[\\tfrac{^{\\circ}}{\\mathrm{rad}}\\right] \\]","text":"i dimensionless index — কোন beam, তার নম্বর। theta_min হলো প্রথম beam-এর direction, unit radian। Delta theta হলো পরপর দুটো beam-এর কৌণিক ফাঁক, unit radian per beam। RAD2DEG হলো L15-এর module-level constant — radian-কে degree-এ নেওয়ার conversion factor, মান 57.29577951…। আর r_i মানে ranges[i] — beam i-এর measured distance, unit meter।"},{"label":"Level 2 — মূল সূত্র (index to angle)","latex":"\\[ \\theta_i = \\left(\\theta_{\\min} + \\Delta\\theta \\cdot i\\right) \\times \\frac{180}{\\pi} \\quad [^{\\circ}] \\]","text":"L67-এর expression-এর math রূপ। base angle-এর সাথে (ধাপ × index) যোগ হয়, তারপর পুরোটা একসাথে radian থেকে degree-এ convert হয়। i এক বাড়লে theta_i বাড়ে ঠিক Delta theta × 57.2958 degree করে — evenly spaced ring-এ সব beam সমান কৌণিক দূরত্বে সাজানো।"},{"label":"Level 3 — fused ring-এ substitution (illustrative)","latex":"\\[ \\theta_i = (-3.14159 + 0.0174533\\, i) \\times 57.2958 \\approx -180^{\\circ} + 1^{\\circ} \\cdot i \\]","text":"folder-10-এর merge+filter chain থেকে আসা ring-এর echo values বসালে (illustrative, folder 09-এ recorded মানের সাথে consistent): angle_min = -3.14159 মানে প্রায় -pi, angle_increment = 0.0174533 মানে প্রায় pi/180 — তাই 360 beam, দুটোর মাঝে ঠিক 1°। এই identity-র সুবিধে: i = 180 মানে 0° (dead ahead), i = 192 মানে +12°। কিন্তু code এই মানগুলো জানে না — সে header থেকে পড়ে; identity-টা শুধু আমাদের reasoning-এর সুবিধে, তাই illustrative।"},{"label":"Level 4 — front cone-এর geometry","latex":"\\[ -45^{\\circ} < \\theta_i < 45^{\\circ},\\quad \\theta_i = -180^{\\circ} + i \\quad\\Rightarrow\\quad 135 < i < 225 \\quad\\Rightarrow\\quad i = 136, 137, \\dots, 224 \\]","text":"cone test-এর geometry। ভেতরে পড়ে মোট 224 - 136 + 1 = 89টা beam। inequality STRICT থাকায় i = 135 (theta = ঠিক -45.0°) আর i = 225 (theta = ঠিক +45.0°) — দুই সীমানাই বাদ। 45.0 মানটা আসে <code>LaserAngle</code> parameter থেকে (L36-37), তাই window চাইলে launch-এর সময় override করা যায়।"},{"label":"Level 5 — validity predicate আর inf edge","latex":"\\[ r_i \\neq 0.0 \\;\\;\\mathrm{and}\\;\\; (+\\infty \\neq 0.0) = \\mathrm{True} \\quad\\Rightarrow\\quad \\text{no-return inf beam passes the filter} \\]","text":"validity test-টা শুধু exact 0.0 বাদ দেয় — কিন্তু LaserScan convention-এ no-return beam-এর মান +inf। Python-এ <code>inf != 0.0</code> evaluate হয় True, তাই inf beam পাশ কেটে list-এ ঢোকে। code-এর assumption: upstream filter no-return-কে 0.0 করে দিয়েছে (folder-10 chain-এর কাজ)। সেই assumption ভাঙলে খোলা corridor-এর 89টা beam-ই inf হতে পারে, আর তখন L77-এর min-ও inf হয়ে যাবে।"}],"numeric":[{"latex":"\\[ i = 192:\\quad \\theta_{192} = -180^{\\circ} + 192^{\\circ} = +12^{\\circ},\\qquad |12| < 45 \\;\\Rightarrow\\; \\text{cone pass} \\]","text":"Wave A (illustrative): pillar 0.90 m সামনের সামান্য বাঁয়ে +12°-তে। সেই beam-এর index উল্টো হিসে বের হয় i = 192। cone test পাস, তাই 0.90 যাবে minDistList-এ আর +12 যাবে minDistIDList-এ — পরের Part-এ এটাই minDist আর minDistID হবে।"},{"latex":"\\[ \\theta_{135} = -45.0^{\\circ}\\ (\\text{excluded}),\\qquad \\theta_{225} = +45.0^{\\circ}\\ (\\text{excluded}),\\qquad 224 - 136 + 1 = 89\\ \\text{beams in the cone} \\]","text":"সীমানার হিসাব (illustrative): STRICT inequality থাকায় ঠিক ±45.0°-র দুটো beam cone-এর বাইরে — সীমানায় ঠিক বসানো object-এর beam কখনো list-এ আসবে না। ভেতরে থাকে 89টা beam।"},{"latex":"\\[ \\text{header claims } \\Delta\\theta = 1^{\\circ},\\ \\text{real spacing } 0.5^{\\circ}:\\quad \\text{code: } \\theta_{192} = +12^{\\circ},\\quad \\text{reality: } -180^{\\circ} + 0.5 \\times 192 = -84^{\\circ} \\]","text":"ভুল increment-এর হিসাব (illustrative): header যদি আসল spacing-এর দ্বিগুণ মান দেয়, তাহলে code-এর চোখে সামনে (+12°) এমন beam শরীরে আসলে বাঁয়ে-পেছনে (-84°) পড়ে। প্রতিটা angle একসাথে shift হয়ে যায়, আর cone শারীরিকভাবে সামনের দিকটা ছেড়ে অন্য দিক জুড়ে বসে।"}],"mapping":[{"code":"for i in range(len(ranges)):","math":"\\( i = 0, 1, 2, \\dots, N-1 \\)","text":"N মানে len(ranges), অর্থাৎ beam-সংখ্যা। প্রতিটা beam ঠিক একবার — কোনো skipping বা early exit নেই।"},{"code":"angle = (scan_data.angle_min + scan_data.angle_increment * i) * RAD2DEG","math":"\\( \\theta_i = (\\theta_{\\min} + \\Delta\\theta\\, i)\\cdot\\frac{180}{\\pi} \\)","text":"message header-এর দুটি field আর L15-এর constant — তিনটা উপাদান মিলে index-কে degree direction-এ বদলায়।"},{"code":"if abs(angle) &lt; self.LaserAngle and ranges[i] !=0.0 :","math":"\\( |\\theta_i| < 45^{\\circ} \\;\\wedge\\; r_i \\neq 0 \\)","text":"প্রথম clause-টা geometry (open interval), দ্বিতীয়টা sentinel-filter — কিন্তু দ্বিতীয়টা inf ধরতে পারে না।"},{"code":"minDistIDList.append(angle)","math":"\\( \\Theta_{\\mathrm{new}} = \\Theta \\cup \\{\\theta_i\\} \\)","text":"নামে 'ID' হলেও store হয় degree angle — L79-এ এটাই minDistID হয়ে পরের Part-এর angular PID-এর input।"}],"failure":["Header-এ ভুল angle_increment থাকলে প্রতিটা beam-এর হিসে করা angle একসাথে shift বা scale হয়ে যায় — ±45° cone আর শরীরের সামনের দিকে থাকে না। ফলে সামনের মানুষটার beam-গুলো minDistList-এ ঢোকেই না, পাশে বা পেছনের দেয়াল ঢুকে যায়; পরের Part-এ robot সেই ভুল object-কেই কেন্দ্র করে wheel ঘোরায়।","inf passthrough: upstream chain no-return-গুলোকে 0.0 না করে থাকলে খোলা corridor-এ cone-এর সব beam inf হয়ে minDistList-এ জমে, min(minDistList) = inf হয়ে যায় — L96-এর deadzone snap অকেজো, linear PID-এর error infinite, আর কোনো clamp না থাকায় linear.x-এ বিশাল value গিয়ে motor পূর্ণ গতিতে ছুটতে পারে।","STRICT inequality-র কারণে ঠিক 45.0°-তে বসানো object-এর beam চিরকাল বাদ পড়ে — একমাত্র object যদি সীমানায় থাকে, minDistList খালি থাকে, L82-এর dashes line console-এ ছাপা হতে থাকে, আর robot স্থির দাঁড়িয়ে।"]},"robot":{"correct":"প্রতিটা fused /scan message-এ lidar-এর 360টা (illustrative) beam এই loop দিয়ে যায়, আর সামনের 89টা beam-এর valid distance-গুলো দুটো parallel list-এ জমা হয়। Wave A-তে (illustrative) pillar 0.90 m, +12° — অর্থাৎ beam i = 192 — তাই 0.90 আর +12 জোড়া হয়ে তালিকায় ঢোকে। এই ধাপে wheel এখনও স্থির: /cmd_vel-এ কিছু publish হয় না, console-এও এই Part-এর কোনো print নেই (print আসে L91-92, পরের Part-এ)। শুধু পরের ধাপের min-search-এর জন্য shortlist তৈরি হয়, আর প্রতিটা নতুন scan-এ খালি list দিয়ে আবার শুরু।","incorrect":"Header-এর angle_increment যদি আসল beam spacing-এর সাথে না মেলে, তাহলে প্রতিটা angle একসাথে সরে যায় — cone শরীরের সামনে না থেকে অন্য দিকে বসে, আর robot পাশের দেয়াল বা পেছনের object-কে সামনের target ভেবে wheel সেই দিকে ঘোরায়। আবার upstream no-return-গুলো 0.0 না হলে খোলা corridor-এ inf ঢুকে minDist = inf হয় — পরের Part-এ error অসীম হয়ে linear.x-এ অর্থহীন বিশাল value যায়, আর clamp না থাকায় motor হঠাৎ পূর্ণ গতিতে ছুটতে শুরু করে। আর একমাত্র object ঠিক 45.0° সীমানায় থাকলে সে কখনো তালিকায় আসে না — console-এ শুধু L82-এর dashes line পড়তে থাকে, robot স্থির।"},"animType":"beamSweep"},{"n":11,"id":"part-11","fname":"laser_Tracker.py","enTitle":"Closest Beam & Override Gates","lang":"python","start":73,"end":88,"flags":[],"explain":[{"a":73,"b":75,"text":"Beam-লুপ (L65-72) শেষ হওয়ার পর এই decision point-এ আসা হয়। লুপ থেকে <code>minDistList</code> আর <code>minDistIDList</code> দুটো parallel list ভরে গেছে — প্রতিটা গ্রহণকৃত বিমের জন্য distance আর angle একসাথে append হয় (L71-72), তাই দুটোর দৈর্ঘ্য সবসময় সমান। L75-এর <code>if len(minDistList) != 0:</code> guard শুধু distance-list-এর দৈর্ঘ্য দেখে। List ফাঁকা মানে একটাও বিম L70-এর দুই শর্ত — <code>abs(angle) &lt; self.LaserAngle</code> আর <code>ranges[i] !=0.0</code> — পাস করেনি; অর্থাৎ tracker-এর চোখে সামনের ±45° cone-এ ট্র্যাক করার মতো কিছু নেই।"},{"a":76,"b":77,"text":"<code>minDist = min(minDistList)</code> — Python-এর built-in <code>min()</code> পুরো list একবার স্ক্যান করে সবচেয়ে ছোট দূরত্বটা বের করে; ইউনিট মিটার। Illustrative fused ring-এ front cone-এ ৮৯টা বিম থাকতে পারে, কিন্তু ট্র্যাকিং-এর জন্য দরকার একটাই সংখ্যা: সবচেয়ে কাছের বস্তুর দূরত্ব। এই মানটাই পরে <code>self.ResponseDist</code> (0.55 m) এর সাথে তুলনা হবে (L96, L102), তাই min বেছে নেওয়াটাই আসল টার্গেট-নির্বাচন সিদ্ধান্ত।"},{"a":78,"b":79,"text":"<code>minDistID = minDistIDList[minDistList.index(minDist)]</code> — এটা হাতে-লেখা argmin, দুই ধাপে: <code>minDistList.index(minDist)</code> খুঁজে দেয় সবচেয়ে ছোট দূরত্ব list-এর কোন position-এ আছে, তারপর parallel list থেকে ঠিক সেই position-এর angle-টা তোলা হয়। নাম দেখে বিভ্রান্ত হবেন না — <code>minDistID</code> কোনো index নয়, এটা ওই বিমের angle, degree-তে (L67-এ গণনা করা)। Tie-এর ক্ষেত্রে <code>index()</code> FIRST occurrence ফেরত দেয়: একাধিক বিম একই দূরত্বে থাকলে যে বিমের i সবচেয়ে ছোট সেটাই জেতে; illustrative ring-এ angle = -180 + i হওয়ায় জেতে সবচেয়ে negative angle-এর বিমটা।"},{"a":80,"b":83,"text":"else-branch মানে cone একদম খালি। L82-এর <code>print(\"-----------------------\")</code> console-এ dashes-এর একটা লাইন ছাপে — এই callback প্রতিটা /scan message-এ চলে, তাই সামনে কিছু না থাকলে এই লাইনটা scan rate-এ বারবার terminal-এ ভাসতে থাকবে। এরপর L83-এর bare <code>return</code> callback থেকে বেরিয়ে যায়। সবচেয়ে গুরুত্বপূর্ণ ব্যাপার: এই পথে কোনো publish নেই — <code>/cmd_vel</code>-এ শেষ পাঠানো command-টাই জ্যান্ত থাকে, মোটর এখানে stop করা হয় না। শেষ command সামনে যাওয়ার হলে চাকা সেই গতিতেই ঘুরতে থাকবে; এটা নীরবতা, active brake নয়। আর যেহেতু return-টা L86-এর আগেই, Joy_active-এর brake-ও এই পথে আর ডাকা হয় না।"},{"a":84,"b":86,"text":"Search-এর পরের দ্বিতীয় gate: <code>if self.Joy_active :</code> (colon-এর আগের space-টা source-এই আছে, পরিষ্কার করা হয়নি)। Flag-টা set করে <code>JoyStateCallback</code> (L54), যেটা /JoyState topic-এ human-এর joystick-এর Bool পায় — True মানে human ড্রাইভ করছে, AI pause। লক্ষণীয়, guard-টা search-এর পরে বসানো: minDist/minDistID হিসাব হয়ে যাওয়ার পরেও ফল ব্যবহার হবে না। Flag hold থাকাকালীন এই branch প্রতিটা scan-এ আবার আবার চলবে।"},{"a":87,"b":88,"text":"<code>self.pub_vel.publish(Twist())</code> — fresh <code>Twist()</code> মানে সব field শূন্য (<code>linear.x</code>, <code>angular.z</code> সবকটা 0.0), অর্থাৎ এটা একটা active brake। Else-branch-এর নীরবতার ঠিক উল্টো: এখানে flag hold করা অবস্থায় প্রতিটা /scan-এ zero-Twist আবার পাঠানো হয় — brake-টা scan rate-এ বারবার refresh হয়, তাই একটা পুরনো অ-শূন্য command এই channel-এ টিকে থাকতে পারে না। এরপর L88-এর <code>return</code> বাকি সব স্কিপ করে দেয়: velocity-বিল্ডিং (L90-125), minDist/minDistID-এর console print (L91-92), PID-দের চলা — কোনোটাই এই scan-এ ঘটবে না।"}],"math":{"intro":"এই Part-এর গণিত argmin-এর প্রশ্নের উত্তর দেয়: সামনের cone-এর গ্রহণকৃত বিমগুলোর ভিড় থেকে সবচেয়ে কাছের বিমটা কোনটা, তার angle কত, tie-তে কে জেতে, আর list ফাঁকা হলে কোন পথটা খোলে।","levels":[{"label":"Level 1 — Symbols & units","latex":"\\[ d^{*}=\\min_k d_k\\ \\mathrm{(m)}, \\qquad \\theta^{*}=\\theta_{k^{*}}\\ \\mathrm{(deg)}, \\qquad k^{*}=\\mathrm{index}(d^{*}) \\]","text":"minDistList-এর k-তম entry হলো d_k (মিটারে দূরত্ব), parallel list minDistIDList-এর ওই একই entry হলো theta_k (degree-তে angle, L67-এ বের করা)। k* মানে জয়ী বিমের list-position — source সেটাকে minDistList.index(minDist) দিয়ে খুঁজে তারপর minDistIDList থেকে angle তোলে।"},{"label":"Level 2 — argmin ও tie-break","latex":"\\[ k^{*}=\\min\\{\\,k:\\ d_k=d^{*}\\,\\} \\]","text":"Tie-এর নিয়ম: একাধিক বিম একই দূরত্বে থাকলে Python-এর index() প্রথম occurrence ফেরত দেয়, তাই k* হলো সবচেয়ে ছোট i-এর বিম (np.argmin-ও একই আচরণ করে)। Illustrative fused ring-এ angle_i = -180 + i, তাই ছোট i মানে বেশি negative angle — tie-এ জেতে সবচেয়ে negative angle-এর বিম, মানে robot-এর ডান-সামনের দিকটা। খেয়াল রাখুন, min() আর index() মিলে মোট দুইবার list স্ক্যান হয়।"}],"numeric":[{"latex":"\\[ \\min(\\mathrm{minDistList})=0.90\\ \\mathrm{m}, \\qquad \\mathrm{minDistID}=+12^{\\circ} \\]","text":"Wave A (illustrative): সামনে একটাই pillar, 0.90 m দূরে +12 ডিগ্রিতে। Guard পাস করে, minDist = 0.90, minDistID = +12 — এই দুটো মানই পরের Part-গুলোর linear ও angular PID-এর ইনপুট হয়ে যায়।"},{"latex":"\\[ \\mathrm{minDistList}=[0.90,\\,0.70,\\,0.70], \\quad \\mathrm{index}(0.70)=1 \\ \\Rightarrow\\ \\theta^{*}=-15^{\\circ} \\]","text":"Tie (illustrative): minDistIDList = [-29, -15, +20] ধরুন — ডান-সামনে -15 ডিগ্রিতে আর বাঁ-দিকে +20 ডিগ্রিতে দুটো বস্তুই 0.70 m দূরে। index() প্রথম occurrence নেয় (ছোট i, negative angle), তাই minDistID = -15 — ডান-দিকের বস্তু জেতে, ঠিক সমান কাছের বাঁ-দিকেরটা বাদ পড়ে।"}],"mapping":[{"code":"minDist = min(minDistList)","math":"\\( d^{*}=\\min_k d_k \\)","text":"পুরো front-cone ভিড় একটা scalar-এ ভাঁজ হয়ে যায়; L96-এর deadzone আর L102-এর linear PID এই d*-ই ব্যবহার করে।"},{"code":"minDistID = minDistIDList[minDistList.index(minDist)]","math":"\\( \\theta^{*}=\\theta_{k^{*}},\\;\\; k^{*}=\\text{first } k \\text{ with } d_k=d^{*} \\)","text":"দুই পাসের argmin: min() খোঁজে মান, index() খোঁজে position, তারপর parallel list থেকে angle। np.argmin না ব্যবহার করে list-idiom-এই কাজটা করা হয়েছে।"}],"failure":["List ফাঁকা হলে else-branch-এ কোনো publish হয় না — শেষ command যদি Wave B-এর মতো সামনে যাওয়ার হয়, তাহলে সামনের corridor খালি হয়ে গেলেও চাকা সেই পুরনো গতিতেই ঘুরতে থাকে; মোটর stop করার দায়িত্ব এই branch-এর নেই, সেটা শুধু Joy_active-এর zero-Twist (L87) বা exit_pro-র shell brake (L133) করে।","Tie-তে সবসময় most-negative angle জেতে: দুটি সমান-দূরত্বের বস্তুর ক্ষেত্রে robot ডান-দিকেরটাকে lock করে ডানে ঘোরে, যদিও বাঁ-দিকের বস্তু ঠিক ততটাই কাছে — বাছাইটা শুধু distance-ভিত্তিক, মাঝামাঝি বা সাম্প্রতিকতার কোনো নীতি নেই।","L70-এর ছাঁকনি শুধু ঠিক 0.0-ই বাদ দেয়; upstream chain যদি no-return বিমের inf-কে 0.0 করে না দেয়, তাহলে খোলা corridor-এ inf-ও minDistList-এ ঢুকতে পারে। সব গ্রহণকৃত রিডিং-ই inf হলে min(minDistList) = inf — len-guard পাস করে যায়, কিন্তু পরের Part-গুলোর PID-এর ইনপুট আবর্জনা হয়ে যায়।"]},"robot":{"correct":"সামনে 0.90 m দূরে +12°-এ pillar থাকলে (Wave A, illustrative) guard পাস করে: minDist = 0.90 আর minDistID = +12 বের হয়, আর পরের লাইনে console-এ সেই মানগুলো ছাপা হয়। Human joystick-এ pause দিলে (Joy_active = True) প্রতিটা scan-এ শূন্য Twist /cmd_vel-এ যায় — দুই চাকা সক্রিয়ভাবে শূন্য গতিতে আটকে থাকে, robot দাঁড়িয়ে থাকে আর lidar ঘুরতেই থাকে। সামনে কিছু না থাকলে console-এ শুধু dashes-এর লাইন আসে, চাকায় নতুন কোনো command যায় না।","incorrect":"সামনের corridor খালি হওয়ার আগে শেষ command যদি সামনে যাওয়ার হয়, তাহলে else-branch নতুন কিছু না পাঠিয়ে নীরব হয়ে যায় — মোটর পুরনো গতিতেই চালিয়ে যায়, robot বাধা ছাড়া এগিয়ে যেতে থাকে। দুটি সমান-দূরত্বের বস্তুতে (0.70 m at -15° ও +20°, illustrative) tie নিয়মে ডান-দিকেরটা জেতে — robot বাঁ-দিকের সমান-কাছের বস্তুটাকে ফেলে ডানে ঘুরে যায়। আর inf যদি একমাত্র গ্রহণকৃত রিডিং হয়, minDist = inf হয়ে পরের PID-গুলো অর্থহীন মান নিয়ে চলে।"},"animType":null},{"n":12,"id":"part-12","fname":"laser_Tracker.py","enTitle":"Velocity & Stand-off Deadzone","lang":"python","start":89,"end":96,"flags":[],"explain":[{"a":89,"b":90,"text":"L89-এর blank line গার্ড-ব্লক (L75-88) আর compute-ব্লককে আলাদা করে; এখানে নামতে পারাই মানে তিনটা gate পাস — L57-এর type check, L75-এর <code>len(minDistList) != 0</code> (নইলে L82-83 ছেপে <code>return</code> করত), আর L86-এর <code>self.Joy_active</code> False — মানুষের joystick নয়, AI চালাচ্ছে। তাই <code>minDist</code> (L77) আর <code>minDistID</code> (L79) দুটোই valid মান হাতে রাখছে। L90-এ <code>velocity = Twist()</code> — প্রতিটা scan-callback-এর জন্য টাটকা একটা command message, ছয়টা field-ই (linear ও angular-এর x, y, z) 0.0 নিয়ে শুরু হয়। এই শূন্য-শুরু নিজেই নিরাপত্তা: এই Part-এর পরে ঠিক দুটো field-এ লেখা হয় (L102-এ <code>linear.x</code>, L110-114-এ <code>angular.z</code>), বাকিগুলো শূন্যই থেকে L125-এ <code>self.pub_vel.publish(velocity)</code> হয়ে <code>/cmd_vel</code>-এ যায়। Variable-টা callback-local, তাই আগের scan-এর পুরনো মান কোথাও carry হয় না।"},{"a":91,"b":92,"text":"<code>print(\"minDist: \", minDist)</code> আর <code>print(\"minDistID: \", minDistID)</code> — দুটো debug print। <code>registerScan</code> প্রতিটা <code>/scan</code> message-এ চলে, তাই এই দুই line-ও scan rate-এ বারবার ছাপা হয় — console-এ প্রতি scan-এ নতুন জোড়া লাইন জমে। Input হলো L77/L79-এর খোঁজা ফল: <code>minDist</code> সামনের cone-এর সবচেয়ে কাছের object-এর দূরত্ব মিটারে, <code>minDistID</code> সেই beam-টার কোণ ডিগ্রিতে। একটা সূক্ষ্ম ক্রম-বিন্দু: print দুটো L96-এর deadzone snap-এর আগে বসে, তাই terminal সবসময় কাঁচা মাপা মান দেখায়। Illustrative Wave C-তে object 0.58 m দূরে: console ছাপবে <code>minDist: 0.58</code>, অথচ নিচে L102-এর PID পাবে snapped 0.55 — console-এর সংখ্যা আর control-এর সংখ্যা ইচ্ছা করেই আলাদা রাখা হয়েছে।"},{"a":93,"b":95,"text":"L93 blank line-এর পর L94-95-এর comment দুটো পরের statement-এর পুরো উদ্দেশ্য লিখে রাখে, verbatim: <code># Create a tiny deadzone: If we are already almost perfectly at 0.55m, pretend we are exactly at 0.55m</code> এবং <code># so the motors don't jitter back and forth.</code> অর্থ: দূরত্ব প্রায় ঠিক থাকলে মাপকে ইচ্ছা করে ঠিক 0.55 ধরে নেওয়া হবে — <code>pretend</code> শব্দটা source-এর নিজের স্বীকারোক্তি যে এটা সচেতন একটা ভান, মাপার কোনো সংশোধন নয়। কারণও বলা: এই ভান না করলে প্রতিটা scan-এ দূরত্বের ছোট ওঠানামা PID-এ ঢুকে চাকাকে বারবার উল্টো দিকে ঠালত, motor সামনে-পিছনে jitter করত। Comment-এর '0.55m' হলো <code>ResponseDist</code>-এর default মান (L38) — parameter-টা টিউন করলে কোড বদলাবে না, comment-এর সংখ্যা ওইরকমই থেকে যাবে।"},{"a":96,"b":96,"text":"মূল লাইন: <code>if abs(minDist - self.ResponseDist) &lt; 0.1: minDist = self.ResponseDist</code> — one-line if, else নেই। শর্ত সত্য হলে local variable <code>minDist</code>-কে ওভাররাইট করে ঠিক stand-off মান (default 0.55) বসিয়ে দেওয়া হয়, ফলে ছয় লাইন নিচে L102-এর <code>pid_compute(self.ResponseDist, minDist)</code> কলে target আর current দুটোই 0.55 — linear error শূন্য, <code>velocity.linear.x</code> শূন্য, সামনে-পিছনের সংশোধন বন্ধ। Band হিসাব করলে সীমা 0.45 থেকে 0.65 m। তিনটা সূক্ষ্মতা: (১) তুলনা strict <code>&lt;</code> — ঠিক 0.45 বা ঠিক 0.65 হলে পার্থক্য 0.10, শর্ত মিথ্যা, snap হয় না (L70-এর cone test-এর মতোই কিনারা বাদ); (২) snap শুধু <code>minDist</code>-কে ছোঁয়, <code>minDistID</code> অপরিবর্তিত — এই deadzone কেবল linear অক্ষের, ঘূর্ণনের নিজস্ব deadzone L117-এ আলাদা; (৩) 0.1 সংখ্যাটা hard-coded literal — <code>ResponseDist</code> runtime parameter-এ বদলালে band তার সাথে সরে যায়, কিন্তু প্রস্থ 0.1 কোড edit ছাড়া বদলানো যায় না। Illustrative Wave C: 0.58 m সোজা সামনে — |0.58 - 0.55| = 0.03, snap হয়; Wave A-র 0.90 m — |0.90 - 0.55| = 0.35, snap হয় না।"}],"math":{"intro":"এই Part-এর গণিত একটাই প্রশ্নের উত্তর দেয়: কোন দূরত্ব-ব্যবধানে L96-এর deadzone robot-কে 'আমি ঠিক জায়গায় আছি' বলিয়ে থামিয়ে দেয়, আর সেই snap L102-এর linear PID-এর error-কে ঠিক কী করে শূন্য করে ফেলে।","levels":[{"label":"Level 1 — Symbols & units","latex":"\\[ d = \\text{minDist}\\ (\\mathrm{m}), \\qquad d^{*} = \\text{ResponseDist} = 0.55\\ \\mathrm{m}, \\qquad \\varepsilon = 0.1\\ \\mathrm{m} \\]","text":"তিনটা symbol। <code>d</code> — L77-এ <code>min(minDistList)</code> থেকে পাওয়া কাছের object-এর মাপা দূরত্ব, মিটারে। <code>d*</code> — L38-39-এর <code>ResponseDist</code> parameter-এর মান, stand-off বা 'sweet spot'। <code>ε</code> — deadzone-এর অর্ধ-প্রস্থ (half-width); source-তে এর কোনো নাম নেই, সরাসরি 0.1 লেখা। তিনটাই মিটার ঘরে, তাই <code>|d - d*|</code>-ও মিটারে — তুলনাটা একই ঘরের সংখ্যার। কোণ <code>minDistID</code> এই সমীকরণে ঢোকে না: deadzone-টা পুরোটা দূরত্বের অক্ষের জিনিস।"},{"label":"Level 2 — Snap-এর শর্ত","latex":"\\[ d_{\\text{PID}} = d^{*} \\ \\text{when } |d - d^{*}| \\lt 0.1; \\qquad d_{\\text{PID}} = d \\ \\text{otherwise} \\]","text":"L96-এর পুরো লজিক দুই টুকরোয়: শর্ত (absolute-value তুলনা) আর কাজ (snap assignment)। শর্ত সত্য হলে PID যে মান পায় সেটা আর মাপা দূরত্ব নয়, টার্গেট নিজেই — L94-এর comment-এর ভাষায় <code>pretend we are exactly at 0.55m</code>। এখানে কোনো hysteresis নেই: কোনো state আলাদা করে জমা থাকে না, প্রতিটা scan-এ শর্তটা তাজা মান দিয়ে নতুন করে মাপা হয়।"},{"label":"Level 3 — Band-এর বীজগণিত","latex":"\\[ -0.1 \\lt d - 0.55 \\lt 0.1 \\quad \\text{i.e.} \\quad 0.45 \\lt d \\lt 0.65\\ \\mathrm{m} \\]","text":"absolute value-এর অসমতা দুই পাশে খুললে band বেরোয়: 0.45 থেকে 0.65 m। প্রান্ত দুটো বাদ — strict inequality-র জন্য ঠিক 0.45 বা ঠিক 0.65 হলে snap হয় না। আর interval-টা খোলা বলে band-এর ভিতরের যেকোনো বিন্দু (0.58 হোক, 0.46 হোক) সমানভাবে 0.55 হয়ে যায় — snap-এর পরে PID ভিতরের অবস্থান আলাদা করে জানতেই পারে না। একই strict-তুলনার স্বভাব L70-এর cone test-এও দেখা গিয়েছিল (ঠিক 45.0° beam বাদ)।"},{"label":"Level 4 — PID error শূন্যকরণ","latex":"\\[ e_{\\text{lin}} = d^{*} - d_{\\text{PID}} = 0.55 - 0.55 = 0, \\qquad K_p = 1,\\ K_i = 0,\\ K_d = 1 \\]","text":"Snap হলে L102-এর consumer-এর কাছে দুই argument-ই 0.55। Call order (target, current) ধরে error = প্রথমটা থেকে দ্বিতীয়টা (inferred — <code>SinglePID</code>-এর ভেতরটা এই folder-এ নেই), তাই e ঠিক শূন্য। Kp-term শূন্য; Kd-term error-এর পরিবর্তনের উপর চলে — স্থির অবস্থায় সেটাও শান্ত, শুধু snap-এর প্রথম scan-এ ক্ষুদ্র transient আসতে পারে (illustrative)। ফল <code>velocity.linear.x = -0 = 0</code>: band-এর ভিতরে থাকা অবধি robot সামনে-পিছনে কিছুই করে না।"},{"label":"Level 5 — Noise rejection: jitter-এর মৃত্যু","latex":"\\[ d = d^{*} + \\delta: \\quad \\text{with snap } e_{\\text{lin}} = 0; \\qquad \\text{without snap } e_{\\text{lin}} = -\\delta \\]","text":"স্থির দাঁড়ানো robot-এর সামনে স্থির object-ও প্রতিটা scan-এ সামান্য ভিন্ন দূরত্ব ফেরায় — সেই ওঠানামা δ (illustrative)। Snap থাকলে |δ| &lt; 0.1 পর্যন্ত পুরো noise এক ঘরে গিলে যায়, প্রতি scan-ে linear.x ঠিক 0। Snap মুছে দিলে error হয় -δ: δ-এর চিহ্ন scan থেকে scan-এ বদলায়, তাই linear.x-এর চিহ্নও বদলায় — চাকা সামনে-পিছনে কাঁপতে থাকে। Control-এর ভাষায় এটা deadband nonlinearity: ছোট signal-কে ইচ্ছা করে শূন্যে ফেলা; L95-এর comment যে <code>jitter back and forth</code> এড়াতে চেয়েছে তার গাণিতিক রূপ এটাই।"},{"label":"Level 6 — Tolerance-এর trade-off","latex":"\\[ |d_{\\text{rest}} - d^{*}| \\lt \\varepsilon = 0.1\\ \\mathrm{m} \\quad \\text{i.e.} \\quad 0.45 \\lt d_{\\text{rest}} \\lt 0.65\\ \\mathrm{m} \\]","text":"Deadzone ফ্রি নয় — এটা একটা tolerance ঘোষণা: এই band-এর ভিতরের যেকোনো জায়গায় থেমে robot নিজেকে লক্ষ্যে ধরে নেয়, তাই stand-off-এর সর্বোচ্চ স্থায়ী ভুল প্রায় 0.1 m (illustrative)। ε = 0 করলে (snap মুছলে) tolerance শূন্য, jitter ফেরে; ε বড় করলে শান্তি বাড়ে কিন্তু robot দৃশ্যমানভাবে off-target থেমেও 'locked' বিশ্বাস করে। 0.1 m হলো vendor-এর বাছাই করা মাঝামাঝি মান — কেন ঠিক 0.1, source ব্যাখ্যা করে না (L107-এর 72-এর মতোই explanation-হীন সংখ্যা)। পাশাপাশি L117-এর angular deadzone মিলে দুটো একসঙ্গে দ্বিমাত্রিক acceptance region বানায় — দূরত্ব ও কোণ দুটোই যথেষ্ট কাছে থাকলে robot একেবারে থেমে যায়।"}],"numeric":[{"latex":"\\[ |0.90 - 0.55| = 0.35 \\geq 0.1 \\quad \\text{no snap (Wave A)} \\]","text":"Wave A (illustrative): pillar 0.90 m সামনে, +12°-এ। ব্যবধান 0.35 — band-এর অনেক বাইরে, শর্ত মিথ্যা; minDist 0.90-ই থাকে। L102-এর linear PID পায় e = 0.55 - 0.90 = -0.35 (Kp-view, illustrative) — দূরত্ব কমানোর আদেশ আসবে।"},{"latex":"\\[ |0.70 - 0.55| = 0.15 \\geq 0.1 \\quad \\text{no snap (Wave B)} \\]","text":"Wave B (illustrative): 0.70 m at +20° — মাত্র 0.15 m বেশি দূরত্বেও snap নেই, e = -0.15; robot এখনো সক্রিয়ভাবে এগোবে। Deadzone-এর ছোঁয়া 0.65 m-এর নিচে নামলেই শুরু হয়।"},{"latex":"\\[ |0.58 - 0.55| = 0.03 \\lt 0.1, \\quad d_{\\text{PID}} = 0.55, \\quad e_{\\text{lin}} = 0 \\quad \\text{(Wave C)} \\]","text":"Wave C (illustrative): 0.58 m, সোজা সামনে (0°)। Snap হয়ে minDist := 0.55; linear error শূন্য, linear.x = 0; minDistID = 0 অপরিবর্তিত। Console-এ তবু <code>minDist: 0.58</code> ছাপা হয় — print (L91) snap-এর (L96) আগে। এটাই held state: stand-off ধরে রাখা, দুই deadzone মিলে robot-কে থামিয়ে রাখা।"},{"latex":"\\[ |0.45 - 0.55| = 0.10, \\quad 0.10 \\lt 0.1 \\ \\text{is false} \\quad \\text{no snap at the edge} \\]","text":"প্রান্ত-পরীক্ষা (illustrative): মাপা দূরত্ব ঠিক 0.45 (বা ঠিক 0.65) হলে পার্থক্য ঠিক 0.10 — strict তুলনায় শর্ত মিথ্যা, snap নেই; কিন্তু 0.46 হলে পার্থক্য 0.09, snap আছে। Band-এর ঠিক কিনারায় আচরণ লাফিয়ে বদলায় — খোলা interval-এর স্বভাব।"}],"mapping":[{"code":"abs(minDist - self.ResponseDist)","math":"\\( |d - d^{*}| \\)","text":"মাপা দূরত্ব আর stand-off-এর বিচ্যুতির magnitude — 'কতটা ভুল জায়গায় আছি' তার একমাত্র মাপ। absolute value নেওয়ায় বেশি-দূর আর বেশি-কাছে দুই দিকই একই শর্তে ধরা পড়ে।"},{"code":"if abs(minDist - self.ResponseDist) &lt; 0.1","math":"\\( |d - d^{*}| \\lt \\varepsilon,\\ \\varepsilon = 0.1\\ \\mathrm{m} \\)","text":"Band টেস্ট। 0.1 টা hard-coded literal — <code>ResponseDist</code> (L38) runtime-এ টিউনযোগ্য, কিন্তু এই প্রস্থ নয়; stand-off বদলালে band সরে যায়, মোটা-পাতলা হয় না।"},{"code":"minDist = self.ResponseDist","math":"\\( d_{\\text{PID}} = d^{*} \\)","text":"Snap: local variable-কে ওভাররাইট করা — নিচের সব ব্যবহার (L102) এই নতুন মান দেখে। <code>minDistID</code> আলাদা, তাকে কেউ ছোঁয় না।"},{"code":"self.lin_pid.pid_compute(self.ResponseDist, minDist)","math":"\\( e_{\\text{lin}} = d^{*} - d_{\\text{PID}} \\)","text":"Consumer — L102, পরের Part। Argument order (target, current); snap থাকলে দুটো সমান, তাই error শূন্য এবং linear.x = 0। SinglePID-এর sign convention এই folder-এ নেই — inferred।"}],"failure":["Snap মুছে দিলে বা 0.1-এর জায়গায় 0 বসালে: 0.55 m-এর গা-ঘেঁষে থাকা অবস্থাতেও প্রতি scan-এর ছোট noise linear.x-এর চিহ্ন ঘুরিয়ে দেয় — চাকা সামনে-পিছনে twitch করতে থাকে, chassis দুলে, motor chatter-এ গরম হয়; L95-এর comment যে <code>jitter back and forth</code> আটকাতে চেয়েছিল সেই কাঁপুনিই ফিরে আসে।","0.1-কে অকারণে বড় করলে (যেমন 0.3): robot 0.25 m থেকে 0.85 m-এর যেকোনো বিন্দুতে থেমে নিজেকে 'locked' ভেবে বসে থাকে — সামনের object থেকে চোখে দেখা দূরত্ব হলেও আর কাছে আসে না, following আচরণ নষ্ট।","মাপা দূরত্ব ঠিক 0.45 বা ঠিক 0.65 হলে snap পাওয়া যায় না (0.10 টা <code>&lt; 0.1</code> পূরণ করে না) — band-এর ঠিক কিনারায় deadzone নীরবে উঠে যায়, সেখানে আবার ছোট error-এর jitter-ই নিয়ন্ত্রণ করে।","<code>ResponseDist</code> runtime-এ বদলালে band তার সাথে সরে যায় (যেমন 0.80 হলে [0.70, 0.90]) কিন্তু প্রস্থ 0.1-ই থাকে, কারণ সেটা hard-coded — ছোট stand-off-এ band আপেক্ষিকভাবে মোটা, বড় stand-off-এ পাতলা দেখাবে; আলাদা করে টিউন করার রাস্তা source edit ছাড়া নেই।"]},"robot":{"correct":"Wave C (illustrative): object 0.58 m সোজা সামনে। L96 minDist-কে 0.55 বসিয়ে দেয়, তাই L102-এর linear PID শূন্য error পায় — linear.x = 0, চাকা সামনে-পিছনে হেলে না, motor শান্ত, robot stand-off-এ দাঁড়িয়ে থাকে। LiDAR প্রতি scan-এ মাপতেই থাকে আর console-এ প্রতি scan-ে <code>minDist: 0.58</code> ছাপা হতে থাকে (print snap-এর আগে) — অথচ চাকা নড়ে না। মাপার সামান্য ওঠানামা এই band-এ গিলে যায়: দূরত্ব 0.50-এ নাকি 0.60-এ, PID-এর কাছে এক। Band-এর বাইরে (illustrative Wave A: 0.90 m) snap হয় না, কাঁচা মানই PID-এ যায়, robot এগিয়ে ব্যবধান কমায় যতক্ষণ না 0.65-এর নিচে নামে।","incorrect":"Deadzone না থাকলে বা band শূন্য করলে: 0.55 m লক্ষ্যের কাছে দাঁড়ানো অবস্থায় প্রতি scan-এ মাপা দূরত্ব 0.54/0.56 এদিক-ওদিক কাঁপে (illustrative noise) — linear PID-এর error-এর চিহ্ন বদলায়, linear.x এক scan-এ ধনাত্মক, পরেরটায় ঋণাত্মক, চাকা সামনে-পিছনে কাঁপতে থাকে; L95-এর comment-এর ভাষায় jitter, motor-এর দিক থেকে chatter আর অপচয়। উল্টো দিকে 0.1-কে অতিরিক্ত বড় করলে (যেমন 0.3) robot object থেকে 0.25 m দূরেও এসে থেমে যেতে পারে — 'locked' বিশ্বাসে স্পষ্ট off-target দাঁড়িয়ে থাকবে, আর কাছে আসার আদেশ পাঠাবে না। আরেকটা পাঠ-ভুল: console-এ <code>minDist: 0.58</code> দেখে ভাবা যে PID-ও 0.58 পাচ্ছে — আসলে সে পাচ্ছে 0.55, তাই console-এর সংখ্যা দিয়ে আগে থেকে linear.x হিসাব করলে মিথ্যা ভবিষ্যদ্বাণী হবে।"},"animType":null},{"n":13,"id":"part-13","fname":"laser_Tracker.py","lang":"python","enTitle":"Dual PID — Approach & Centering","start":97,"end":114,"flags":[],"explain":[{"a":97,"b":99,"text":"L96-এর deadzone snap-এর পরে registerScan-এর এই অংশটা linear PID block। L97 শুধু একটা blank line — দুই ধাপের মাঝে পড়ার ফাঁক, কোনো code নেই। L98-99-এর comment দুটি input পরিষ্কার করে দিচ্ছে: <code>We feed it our Target (0.55m) and our Current Distance (minDist)</code> — target মানে <code>self.ResponseDist</code> (L39-এ declare করা 0.55 m stand-off), current মানে <code>minDist</code> (L77-এ পাওয়া front cone-এর closest beam-এর দূরত্ব)। প্রতিটা /scan message-এ এই জোড়া নতুন করে তৈরি হয়, কারণ এই পুরো function-টা per-scan callback (L56)।"},{"a":100,"b":101,"text":"এই দুই লাইনের comment-টাই file-এর সবচেয়ে সূক্ষ্ম sign-প্রশ্নটা তোলে: <code>The negative sign is because if we are too far away, the error is positive, but we need a positive forward speed to drive toward it</code>। অর্থাৎ comment-এর দাবি — দূরে থাকলে error positive। কিন্তু পরের লাইনের call order যদি হয় (target, current) আর SinglePID-এর ভেতরে error = first - second হয়, তাহলে দূরে থাকলে (minDist বড়) error দাঁড়ায় negative — comment-এর এই দাবির সঙ্গে ওই convention পরিষ্কারভাবে খাটে না। মনে রাখো: vendor-এর SinglePID source এই folder-এ নেই (L12-এর star-import যে module থেকে এসেছে সেটা বাইরের), তাই ভেতরের sign এই file থেকে প্রমাণ করা যায় না — নিচের direction-উপসংহার comment-এর intent থেকে inferred।"},{"a":102,"b":102,"text":"Linear channel-এর মূল লাইন: <code>velocity.linear.x = -self.lin_pid.pid_compute(self.ResponseDist, minDist)</code>। Call-এর order as written হলো (target, current); controller-টা L47-এর <code>SinglePID(1.0, 0.0, 1.0)</code>। Kp-term view-এ pid প্রায় 1×(0.55 - minDist), আর সামনের minus sign-টা সেটাকে উল্টে দেয়: linear.x ≈ minDist - 0.55। সুতরাং দূরের object (minDist &gt; 0.55) মানে positive linear.x — সামনে এগোনো (approach); কাছের object মানে negative — পিছিয়ে সরা; L96-এর snap-এ minDist = 0.55 হয়ে গেলে ফল শূন্য। আর একটা জিনিস — এখানে কোনো clamp নেই: L33-এর <code>self.linear</code> (declared 0.5) পুরো file-এ আর কোথাও পড়াই হয় না, তাই error যত বড়, output-ও তত বড় হয়ে সোজা <code>/cmd_vel</code>-এ চলে যায়।"},{"a":103,"b":106,"text":"L103 blank; এরপর angular PID block-এর comment। L104-105 বলছে <code>We feed it our Target Angle (0 degrees = straight ahead) and the Current Angle (minDistID)</code> — কিন্তু পরের লাইনের actual call এই বর্ণনা মানে না: সেখানে first argument হয় <code>abs(minDistID) / 72</code>, second হয় <code>0</code> — অর্থাৎ normalized |angle| target হিসেবে যায়, 0 current হিসেবে। L106-এর ব্যাখ্যা: <code>Dividing by 72 just scales the angle down to a number the PID likes</code> — 72 সম্পর্কে file-এর এই এক লাইনটুকুই আছে; কেন ঠিক 72, তা কোথাও বলা নেই। এটা একটা bare magic number — এর অর্থ শুধু observable effect থেকেই বোঝা যায় (পরের item-এ)।"},{"a":107,"b":107,"text":"Angular channel-এর মূল লাইন: <code>ang_pid_compute = self.ang_pid.pid_compute(abs(minDistID) / 72, 0)</code>। <code>abs()</code> কোণের sign ফেলে দেয় — হিসাব হয় শুধু magnitude-এর, direction নয়; direction পরের if/elif ফিরিয়ে দেবে। Controller-টা L49-এর <code>SinglePID(2.0, 0.0, 2.0)</code>। Observable effect: L70-এর strict <code>&lt;</code>-এর কারণে cone-এর ভেতরে max |minDistID| কখনো 45.0 হয় না — সবে মাত্র নিচে; ফলে PID-এর কাছে যাওয়া target-এর সর্বোচ্চও সবে মাত্র 45/72 = 0.625-এর নিচে। 72-এর মান বদলালে ঠিক এই scale-টাই বদলে যায় — আর কিছু না; কেন 72, সেটা file কিছু বলে না।"},{"a":108,"b":111,"text":"L108 blank; L109-এর comment নীতিটা বলে দেয়: object বাঁয়ে থাকলে (positive angle) বাঁ দিকে ঘুরতে হবে। Fused ring-এ কোণ ডিগ্রিতে মাপা (L67), positive মানে front থেকে বাঁ-দিক (CCW)। L110-111: <code>if 0 &lt; minDistID :</code> হলে <code>velocity.angular.z = ang_pid_compute</code> — ROS convention-এ positive angular.z মানে CCW বাঁ ঘোরা, তাই বাঁয়ের object-এর জন্য z = +ang_pid_compute। L107-এর <code>abs()</code>-এ হারিয়ে যাওয়া sign-টাই এই branch হাতে করে আবার লাগানো হচ্ছে।"},{"a":112,"b":114,"text":"ডান পাশের শাখা: <code>elif minDistID &lt; 0:</code> হলে <code>velocity.angular.z = -ang_pid_compute</code> — negative angle মানে object ডানে, তখন z negative (CW) হয়, robot ডান দিকে ঘোরে। আর তৃতীয় সম্ভাবনাটা দুই branch-এর ফাঁকে: minDistID ঠিক 0.0 হলে (object একদম সোজা সামনে) কোনো শাখাই চলে না — <code>velocity.angular.z</code> L90-এ বানানো <code>Twist()</code>-এর default 0.0-ই থাকে। ঘোরার কোনো command যায় না, যা এই অবস্থায় ঠিকও বটে।"}],"math":{"intro":"এই Part-এর গণিত দুটো প্রশ্নের উত্তর দেয়: দূরত্বের error কীভাবে L102-এর minus sign-এর ভেতর দিয়ে একটা signed linear.x হয়ে দাঁড়ায়, আর কোণটা কীভাবে abs(), 72 ভাগ আর if/elif sign branch মিলে angular.z বানায়।","levels":[{"label":"Level 1 — Symbols ও units","latex":"\\[ d^{*} = 0.55\\ \\mathrm{m},\\quad d = \\text{minDist},\\quad \\alpha = \\text{minDistID}\\ (\\text{deg}),\\quad s = \\frac{|\\alpha|}{72} \\]","text":"d* হলো target stand-off — <code>self.ResponseDist</code> (L39), unit মিটার। d হলো front cone-এর closest beam-এর দূরত্ব (L77)। α হলো সেই beam-এর কোণ, ডিগ্রিতে (L79)। s হলো 72 দিয়ে ভাগ করা normalized কোণ — dimensionless। Gains: <code>lin_pid</code> = (Kp, Ki, Kd) = (1, 0, 1) (L47), <code>ang_pid</code> = (2, 0, 2) (L49)। SinglePID-এর ভেতরের সূত্র inferred — vendor source এই folder-এ নেই।"},{"label":"Level 2 — PID-এর মৌলিক সম্পর্ক","latex":"\\[ u = K_p\\,e + K_i \\int e\\,dt + K_d\\,\\dot{e} \\]","text":"সাধারণ PID-এর output। দুই controller-এই Ki = 0, তাই integral term নেই; steady দৃশ্যে u ≈ Kp·e। error-এর সংজ্ঞা এই file-এর call order থেকে আসে: <code>pid_compute(first, second)</code> মানে e = first - second (target - current) — এই internal convention-টা inferred, কারণ SinglePID-এর code আমাদের হাতে নেই। Kd-র ভূমিকা শুধু প্রথম call-এর transient-এ দেখা যায় (illustrative)।"},{"label":"Level 3 — Linear channel-এর sign algebra","latex":"\\[ e_{lin} = d^{*} - d,\\qquad x = -u_{lin} \\approx -K_p\\,(d^{*} - d) = K_p\\,(d - d^{*}) \\]","text":"L102-এর সামনের minus sign-টা distribute করলে Kp-view-এ linear.x ≈ Kp(d - d*)। দূরে (d &gt; d*) হলে x &gt; 0: সামনে এগোনো। কাছে (d &lt; d*) হলে x &lt; 0: পিছিয়ে সরা। L96-এর deadzone snap d-কে d* বানিয়ে দিলে x = 0। L100-101-এর comment দাবি করে error positive-when-far — (target, current) convention-এ সেই দাবি পরিষ্কারভাবে খাটে না; approach-দিকনির্ণয় comment-এর intent থেকে inferred।"},{"label":"Level 4 — /72 normalization ও কোণের সীমা","latex":"\\[ e_{ang} = \\frac{|\\alpha|}{72} - 0 = s,\\qquad |\\alpha| \\lt 45 \\;\\Rightarrow\\; 0 \\le s \\lt \\frac{45}{72} = 0.625,\\qquad u_{ang} \\approx 2s = \\frac{|\\alpha|}{36} \\]","text":"L70-এর strict <code>&lt;</code>-এর কারণে cone-এর ভেতরের কোণ কখনো 45.0 হয় না — সবে নিচে। তাই s-এর সর্বোচ্চ সবে মাত্র 0.625-এর নিচে: PID-এর কাছে যাওয়া target-এর ছাদ এটাই। Kp = 2 হলে u_ang ≈ |α|/36। 72 কেন ঠিক 72 — file কোথাও ব্যাখ্যা করে না; এটা bare magic number, শুধু এই observable effect-টুকুই বলা যায়।"},{"label":"Level 5 — Sign re-attach: piecewise angular.z","latex":"\\[ z = \\begin{cases} +u_{ang}, & \\alpha \\gt 0\\ \\text{(left, CCW)} \\\\ 0, & \\alpha = 0 \\\\ -u_{ang}, & \\alpha \\lt 0\\ \\text{(right, CW)} \\end{cases} \\]","text":"L107-এর <code>abs()</code> direction-এর তথ্য ফেলে দেয়; L110-114-এর if/elif সেই direction ফিরিয়ে আনে। α ঠিক 0.0 হলে কোনো শাখাই চলে না — z, <code>Twist()</code>-এর default 0.0-ই থাকে (L90)। ROS convention: positive z মানে CCW বাঁ ঘোরা, negative z মানে CW ডান ঘোরা।"},{"label":"Level 6 — Magnitude envelope ও declared limit","latex":"\\[ x \\approx d - d^{*}\\ (K_p = 1),\\qquad x \\gt 0.5 \\iff d \\gt 1.05\\ \\mathrm{m};\\qquad |z| \\approx 0.6 \\cdot \\frac{|\\alpha|}{36} = \\frac{|\\alpha|}{60} \\]","text":"L102-এ clamp নেই এবং <code>self.linear</code> (declared 0.5, L33) কোথাও পড়া হয় না: d = 1.6 m হলে Kp-view x ≈ +1.05 m/s — declared max-এর দ্বিগুণের বেশি। Angular দিকে এই part-এর output পরে L117-এর turn deadzone (u_ang &lt; 0.5 হলে z = 0, মানে Kp-term view-এ |α| &lt; 18°, illustrative) আর L120-এর 60% damping ছুঁয়ে যায় — তাই চূড়ান্ত |z| ≈ |α|/60।"}],"numeric":[{"latex":"\\[ e_{lin} = 0.55 - 0.90 = -0.35\\ \\mathrm{m},\\qquad u_{lin} \\approx 1 \\times (-0.35) = -0.35,\\qquad x = -u_{lin} = +0.35\\ \\mathrm{m/s} \\]","text":"Wave A (illustrative): সামনের pillar 0.90 m, +12°। Deadzone snap হয় না (|0.90 - 0.55| = 0.35 ≥ 0.1)। Kp-term view-এ linear.x = +0.35 m/s — মানে approach; প্রথম call-এ Kp আর Kd মিলে same-sign একটা transient যোগ করতে পারে (illustrative)।"},{"latex":"\\[ s = \\frac{12}{72} = 0.1667,\\qquad u_{ang} \\approx 2 \\times 0.1667 = 0.333 \\lt 0.5 \\Rightarrow z = 0 \\]","text":"Wave A-র কোণ দিয়ে (illustrative): 12° error এখনো ছোট — L117-এর turn deadzone 0.333-কে ধরে ফেলে, তাই z = 0। এই ধাপে robot শুধু দূরত্ব কমায়, ঘোরে না।"},{"latex":"\\[ e_{lin} = 0.55 - 0.70 = -0.15 \\Rightarrow x \\approx +0.15,\\qquad u_{ang} \\approx 2 \\times \\frac{20}{72} = 0.556 \\ge 0.5 \\Rightarrow z = 0.556 \\times 0.6 \\approx +0.33\\ \\mathrm{rad/s} \\]","text":"Wave B (illustrative): 0.70 m, +20° — দুই output-ই nonzero: সামনে +0.15 m/s, আর L120-এর 60% damping-এর পরে বাঁ দিকে (CCW) প্রায় +0.33 rad/s। Console-এ L91-92-এর minDist/minDistID আর L122-এর angular.z ছাপা হবে।"}],"mapping":[{"code":"-self.lin_pid.pid_compute(self.ResponseDist, minDist)","math":"\\( x = -K_p\\,(d^{*} - d) = K_p\\,(d - d^{*}) \\)","text":"Call order as written: (target, current)। Kp-view-এ minus sign-টা error উল্টে দেয় — দূরের object মানে positive linear.x = approach। Direction-উপসংহার inferred: vendor SinglePID source এই folder-এ নেই; L100-101-এর comment ঠিক এই intent-ই দাবি করে।"},{"code":"self.ang_pid.pid_compute(abs(minDistID) / 72, 0)","math":"\\( e_{ang} = \\frac{|\\alpha|}{72} - 0 = s \\)","text":"First argument = normalized |angle| (target), second = 0 (current)। 72 একটা bare magic number — file এর কারণ ব্যাখ্যা করে না; observable effect: max |angle| সবে 45-এর নিচে হলে target সবে 0.625-এর নিচে।"},{"code":"if 0 &lt; minDistID : velocity.angular.z = ang_pid_compute","math":"\\( \\alpha \\gt 0 \\Rightarrow z = +u_{ang} \\)","text":"বাঁয়ের object: positive degree মানে front থেকে CCW দিক, আর positive z মানে ROS convention-এ বাঁ ঘোরা — <code>abs()</code>-এ হারানো sign এই branch-এ ফিরে আসে।"},{"code":"elif minDistID &lt; 0: velocity.angular.z = -ang_pid_compute","math":"\\( \\alpha \\lt 0 \\Rightarrow z = -u_{ang};\\ \\alpha = 0 \\Rightarrow z = 0 \\)","text":"ডানের object-এর জন্য sign উল্টো হয় (CW ডান ঘোরা)। আর α ঠিক 0.0 হলে কোনো branch-ই চলে না — z, <code>Twist()</code>-এর default 0.0-ই থাকে।"}],"failure":["SinglePID-এর internal error-sign যদি উল্টো হয়, বা কেউ L102-এর সামনের minus তুলে দিয়ে comment-এর কথামতো 'ঠিক' করে ফেলে — দূরের object-এ linear.x negative হয়ে যাবে: wheel-রা উল্টো ঘুরবে, robot লক্ষ্য ছেড়ে পিছু হটবে, object যত দূরে তত জোরে পিছিয়ে যাবে। এই দিকনির্ণয় inferred — vendor source এই folder-এ নেই।","72-এর জায়গায় ভুল সংখ্যা বসালে responsiveness নীরবে বদলে যায়: 36 করলে target-এর ছাদ দাঁড়ায় প্রায় 1.25 এবং L117-এর deadzone threshold কোণ 18° থেকে নেমে আসে 9°-এ (Kp-term view, illustrative) — ছোট বিচ্যুতিতেই robot ঘুরতে শুরু করবে; উল্টো দিকে 144 করলে threshold ওঠে 36°-এ — বড় বিচ্যুতি পর্যন্ত সোজা থাকবে। File 72-এর কারণ বলে না, তাই এই tuning ভাঙলে ধরাও কঠিন।","L102-এ কোনো clamp নেই এবং declared <code>self.linear</code> = 0.5 (L33) কোথাও পড়া হয় না: 1.6 m দূরের object মানে Kp-view linear.x ≈ +1.05 m/s (illustrative) — declared max-এর দ্বিগুণের বেশি command সরাসরি /cmd_vel-এ যাবে, robot হঠাৎ লাফিয়ে এগোবে।"]},"robot":{"correct":"লেখা অবস্থায় চালালে (illustrative Wave A থেকে Wave B): lidar-এর fused /scan-এ সামনের closest object ধরা পড়ে, 0.90 m দূরে থাকলে দুই wheel-ই সামনে ঘুরে robot প্রায় +0.35 m/s এগোয় — 12° বিচ্যুতি এখনো turn deadzone-এর ভেতরে, তাই ঘূর্ণন শূন্য। Object 0.70 m আর +20°-এ গেলে ডান wheel দ্রুত ও বাঁ wheel ধীর হয়ে robot বাঁ দিকে (CCW) প্রায় +0.33 rad/s ঘুরতে শুরু করে। Console-এ প্রতি scan-এ minDist, minDistID আর (L122-এ) angular.z ছাপা হতে থাকে; লক্ষ্য 0.55 m stand-off-এ object-কে সামনে রেখে আটকে থাকা।","incorrect":"Sign-এর সিদ্ধান্ত উল্টো হলে (vendor internal উল্টো, বা L102-এর minus তুলে দিলে) দূরের object দেখে wheel-রা পেছনে ঘুরবে — robot object থেকে দূরে সরে যাবে, /cmd_vel-এ negative linear.x যাবে, console-এ minDist বাড়তেই থাকবে। Clamp না থাকায় বড় error-এ (যেমন 1.6 m, illustrative) wheel-রা declared 0.5 m/s-এর বদলে প্রায় +1.05 m/s command পাবে — প্রথম দর্শনেই robot লাফিয়ে এগোবে। আর 72-এর ভুল মান হলে ছোট কোণেও ঘুরবে বা বড় কোণেও সোজা থাকবে — tracking আলগা হয়ে object cone-এর ধারে হারিয়ে যাবে।"},"animType":"pidDial"},{"n":14,"id":"part-14","fname":"laser_Tracker.py","enTitle":"Turn Deadzone, Damping & Publish","lang":"python","start":115,"end":125,"flags":[],"explain":[{"a":116,"b":117,"text":"Turning-এর deadzone: <code>if abs(ang_pid_compute) &lt; 0.5: velocity.angular.z = 0.0</code> — এক লাইনে লেখা combined if+statement। Part 13-এর <code>ang_pid_compute</code>-এর মান যদি জোড়া-লাইনের মানের চেয়ে ছোট হয়, তাহলে আগের দুই branch-এ যে <code>angular.z</code>-ই set হোক না কেন, এখানে তাকে <code>0.0</code> করে দিয়ে বলা হচ্ছে — এত ছোট turn-কে মোটেও turn ধরব না। Kp-item দিয়ে হিসাব করলে (Kp=2, target = |angle|/72): <code>2 × |angle|/72 = |angle|/36</code>, তাই শর্ত হয়ে দাঁড়ায় <code>|angle| &lt; 18°</code> — মানে object সামনের দিক থেকে 18 degree-এর কমে সরে থাকলে robot একদম ঘুরবেই না, শুধু সোজা এগোবে (illustrative — Kd=2 term প্রথম call-এ step change-এ কিছু ক্ষণিক বাড়তি যোগ করতে পারে, vendor <code>SinglePID</code>-এর ভেতরটা এই folder-এ নেই)। L118-এর blank line দুই ধাপের মাঝে শুধু পাঠ-গোছানোর ফাঁক।"},{"a":119,"b":120,"text":"Turn damping: <code>velocity.angular.z = velocity.angular.z * 0.6</code> — comment-এর ভাষায় robot যেন <i>whip around</i> না করে। যেকোনো চূড়ান্ত <code>angular.z</code>-এর উপর সর্বজনীন 60% স্কেল — deadzone-এ পড়ে 0.0 হয়ে যাওয়া মানের উপরেও এটা চলে (0 × 0.6 = 0, ক্ষতি নেই), আর বাকি সব মান সত্যিই ছোট হয়। সর্বোচ্চ মানের হিসাব (illustrative): cone-এর কিনারায় |angle| যখন 45-এর একটু নিচে, তখন PID-এর target হয় 45/72 = 0.625-এর একটু নিচে; Kp-item দিয়ে u দাঁড়ায় প্রায় 2 × 0.625 = 1.25-এ, আর তার উপর ×0.6 করলে চূড়ান্ত <code>angular.z</code> নামে আসে প্রায় 0.75 rad/s-এ — declared <code>angular</code> parameter-টা (1.0, Part 7) কোথাও enforce হয় না, বাস্তব ceiling এই দুই ধাপ (deadzone নয়, damping) থেকেই আসে।"},{"a":122,"b":122,"text":"<code>print(\"angular.z: \", velocity.angular.z)</code> — প্রতিটা scan message-তে console-এ চূড়ান্ত turn-মান ছাপা হয়, ঠিক আগের <code>minDist</code>/<code>minDistID</code> print-এর মতোই (L91-92)। Lidar-এর scan rate-এ এটা প্রতি সেকেন্ডে বহুবার চলে — debugging-এ সুবিধা, কিন্তু terminal-এ টানা লাইন-বৃষ্টি। L121/L123-এর blank line-গুলো কেবল ভিজ্যুয়াল বিভাজক।"},{"a":124,"b":125,"text":"<code>self.pub_vel.publish(velocity)</code> — এই callback-এর শেষ কাজটাই আসল আউটপুট: একটাই <code>Twist</code>, যার <code>linear.x</code> (Part 13-এর approach মান) আর <code>angular.z</code> (এই Part-এর চূড়ান্ত damped মান) একসঙ্গে বসে <code>/cmd_vel</code>-এ যায় (L29-এর publisher, queue depth 1)। Comment বলে <i>Send the movement command to the wheels!</i> — wheel-দের base driver এই topic-ই শোনে। পরের scan message আসা পর্যন্ত motor এই কমান্ডই ধরে রাখে; সামনে কিছু না থাকলে (Part 11-এর <code>return</code>) নতুন কোনো publish হয় না, শেষ কমান্ড জমে থাকে।"}],"math":{"intro":"এই Part-টা দুটো সরল কিন্তু শক্তিশালী post-processing নিয়ম — একটা deadzone আর একটা স্কেল — তাই গণিতটাও দুই ধাপে: শর্তটা inequality রূপে খোলা, তারপর তার কার্যকর সীমা বের করা।","levels":[{"label":"Level 1 — Symbols","latex":"\\[ u = \\text{ang\\_pid\\_compute}, \\quad \\omega = \\text{velocity.angular.z}, \\quad \\omega_{\\max} = 0.75\\ \\tfrac{\\mathrm{rad}}{\\mathrm{s}} \\]","text":"<code>u</code> হলো Part 13-এর angular PID-এর রা (এখানে Kp-item দিয়ে u ≈ 2|a|/72 = |a|/36, illustrative), <code>ω</code> চূড়ান্ত turn rate (rad/s)। 0.5 হলো deadzone-এর threshold, 0.6 হলো damping factor — দুটোই source-এর hard-coded সংখ্যা।"},{"label":"Level 2 — দুই নিয়ম","latex":"\\[ \\omega_1 = \\begin{cases} 0 & |u| < 0.5 \\\\ u & |u| \\ge 0.5 \\end{cases} \\qquad \\omega = 0.6\\,\\omega_1 \\]","text":"L117 piecewise-ভাবে deadzone, L120 সব ক্ষেত্রে 60% স্কেল। দুই নিয়ম ক্রমান্বয়ে লাগে — আগে কাট-টু-জিরো, তারপর স্কেল।"},{"label":"Level 3 — Substitution: কত degree পর্যন্ত চুপ?","latex":"\\[ \\frac{|a|}{36} < 0.5 \\;\\Longleftrightarrow\\; |a| < 18^{\\circ} \\qquad\\text{and}\\qquad \\omega \\to \\max: \\; 0.6 \\times 2 \\times \\frac{45^{-}}{72} = 0.75 \\tfrac{\\mathrm{rad}}{\\mathrm{s}} \\]","text":"Kp-item পেতে deadzone-এর কার্যকর সীমা: 18 degree-এর নিচে কোনো turn নেই; cone-এর কিনারা (|a| যখন 45-এর একটু নিচে) চূড়ান্ত ceiling 0.75 rad/s।"},{"label":"Level 4 — জ্যামিতিক অর্থ","latex":"\\[ v = \\omega \\cdot r \\;\\Rightarrow\\; \\text{chassis center turn radius} \\; r = \\frac{v_{\\mathrm{lin}}}{\\omega} \\]","text":"Robot একই সাথে এগোয় (v = linear.x) আর ঘোরে (ω) — মিলিত গতির পথ বৃত্তচাপ, যার ব্যাসার্ধ r = v/ω। যেমন Wave B-তে v ≈ 0.15 m/s, ω ≈ 0.33 rad/s হলে r ≈ 0.45 m — object-এর দিকে বেঁকে এগোনোর মসৃণ বাঁক (illustrative)।"}],"numeric":[{"latex":"\\[ u = 2 \\times \\frac{20}{72} = 0.5556 \\;\\ge\\; 0.5 \\;\\Rightarrow\\; \\text{deadzone pass}, \\quad \\omega = 0.5556 \\times 0.6 = 0.333\\ \\tfrac{\\mathrm{rad}}{\\mathrm{s}} \\;(\\text{left, } +) \\]","text":"Wave B (illustrative): object 20° বাঁয়ে, 0.70 m — u = 0.556, deadzone পার হয়, ×0.6-এ ω ≈ +0.33 rad/s। এক কথায়: 20° এখনো যথেষ্ট বড় যে robot ঘুরবে, কিন্তু damping-এ ঘূর্ণন মার্জিত লেভেলে নেমে আসে।"},{"latex":"\\[ u = 2 \\times \\frac{12}{72} = 0.3333 \\;\\lt\\; 0.5 \\;\\Rightarrow\\; \\omega = 0 \\;\\; (\\text{Wave A: } 12^{\\circ} \\text{ error, no turn}) \\]","text":"Wave A (illustrative): 12° বাঁয়ে — u = 0.333, deadzone-এর ভিতরে, তাই ω = 0। Robot শুধু সামনে এগোয়; ত্রুটি 18° ছাড়ানো পর্যন্ত ঘোরা শুরুই হবে না। এই তুলনাটাই (A বনাম B) deadzone-এর সীমার বাস্তব প্রদর্শন।"}],"mapping":[{"code":"if abs(ang_pid_compute) < 0.5: velocity.angular.z = 0.0","math":"\\( |u| < 0.5 \\Rightarrow \\omega_1 = 0 \\)","text":"abs() নিয়ে তুলনা — বাঁয়ে হোক ডানে হোক, মানের বিশালতাই দেখে। ঠিক এই কারণে sign branch (L110-114) আগে, deadzone পরে — sign ঠিক করে, deadzone সেটাকে চুপ করাতে পারে।"},{"code":"velocity.angular.z = velocity.angular.z * 0.6","math":"\\( \\omega = 0.6\\,\\omega_1 \\)","text":"নিজের উপরেই গুণ — self-scaling idiom। PID-এর Kp-এর সঙ্গে এটা কার্যত গুণিত হয়ে যায়: সামগ্রিক লাভ হয় 0.6 × Kp = 1.2 — অথচ PID-এর ভিতরের state অপরিবর্তিত থাকে, তাই damping-টা tune করতে PID আবার গড়তে হয় না।"}],"failure":["Threshold 0.5 কমিয়ে যেমন 0.05 করা হলে: মাত্র 1-2 degree-এর সামান্য সরও turn জাগিয়ে দিত — scan noise-এর সঙ্গে মিলে motor সারাক্ষণ ছোট ছোট কাঁপা (jitter) শুরু করত, যে জিনিসটা এই deadzone আটকাতেই চেয়েছে।","Threshold আরও বাড়ালে (যেমন 0.8): turn শুরু হতে |a| ≥ 29° লাগত — object প্রায় পাশে চলে যাওয়ার আগে robot সোজা এগোতেই থাকত, 0.55 m stand-off ঠিক রাখলেও centering প্রায় অচল।","0.6 damping বাদ দিলে ceiling হয়ে যেত 1.25 rad/s — comment-এর ভাষায় whip around: হঠাৎ বড় turn, মাঝপথে center ছাড়িয়ে যাওয়া, আর Kd=2-এর transient-এর সঙ্গে মিলে বাঁয়ে-ডানে দোলা (oscillation) শুরু হতে পারত।","এই সব সীমা যেহেতু hard-coded (0.5, 0.6) আর declared <code>angular</code> parameter (1.0) কোথাও enforce-ই হয় না — field-এ আসল চূড়ান্ত turn গতি 0.75 rad/s পর্যন্ত উঠতে পারে, যা parameter-এর দাবির সঙ্গে মেলে না (Part 7-এর dead-parameter তথ্য)।"]},"robot":{"correct":"Wave B-র মতো মুহূর্তে robot পায় একটাই যৌথ আদেশ — সামনে ধীরে এগোনো (linear.x ≈ +0.15 m/s) সঙ্গে বাঁদিকে মার্জিত ঘূর্ণন (angular.z ≈ +0.33 rad/s), damping-এর কারণে ঝটকা ছাড়া। Object 18°-এর ভিতরে থাকলে robot ঘোরে না, শুধু দূরত্ব গুছিয়ে 0.55 m stand-off-এ থামে; console-এ প্রতিটা scan-এ angular.z-এর মান ছাপা হতে থাকে।","incorrect":"Deadzone বা damping-এর মান ভুল হলে আচরণ দুই দিকেই ভেঙে পড়ে: threshold ছোট হলে বা 0.6 না থাকলে robot object-এর দিকে ঝাঁকিয়ে ঘোরে, center পেরিয়ে ওপারে গিয়ে আবার ফিরে আসে — বাঁয়ে-ডানে দোলা; threshold বড় হলে object স্পষ্ট সরে গেলেও robot সোজা এগিয়ে stand-off-টা ভুল দিক থেকে মেলে — tracking নামের আচরণটাই অর্ধেক নিষ্ক্রিয়।"},"animType":"cmdVelVectors"},{"n":15,"id":"part-15","fname":"laser_Tracker.py","enTitle":"exit_pro & main — Brake and Shutdown","lang":"python","start":126,"end":146,"flags":[],"explain":[{"a":126,"b":128,"text":"L125-এর <code>self.pub_vel.publish(velocity)</code> দিয়ে <code>registerScan</code>-এর দীর্ঘ কাজ শেষ; L126-এর blank line class-এর শেষ অংশটাকে আলাদা করে দেয়। <code># --- SAFETY SHUTDOWN FUNCTION ---</code> — comment নিজেই ঘোষণা করছে এবার কী আসছে: বিদায়ের যন্ত্রপাতি। <code>def exit_pro(self):</code> — <code>laserTracker</code> class-এর শেষ method; নামটা সম্ভবত \"exit procedure\"-র ছোট রূপ। Argument শুধু <code>self</code>, কোনো return নেই — এর একটাই কাজ, নিচের লাইনগুলো দিয়ে robot-কে থামানো। Import-pass-এ (module প্রথমবার পড়ানোর সময়) শুধু এই <code>def</code>-টা bind হয়, body চলে না; body চলবে শুধু তখন, যখন L144-এর <code>finally</code> থেকে একে ডাকা হবে।"},{"a":129,"b":130,"text":"<code># When you press Ctrl+C, this runs a terminal command in the background to force the robot to stop</code> — comment-টা পুরো পরিকল্পনা বলে দিচ্ছে: Ctrl+C-র পরে terminal command-এর মাধ্যমে জোর করে থামানো। <code>cmd1 = \"ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist \"</code> — লক্ষ করো closing quote-এর ঠিক আগে একটা <b>trailing space</b> আছে; চোখে প্রায় অদৃশ্য, কিন্তু এটাই message type আর পরের payload-র মাঝের separator — বাদ পড়লে জোড়া লাগানো command-টা ভেঙে যেত। চার টুকরো: <code>ros2 topic pub</code> — ROS 2-র command-line publisher tool; <code>--once</code> — ঠিক একটা message দিয়েই process বেরিয়ে যাবে; <code>/cmd_vel</code> — L29-এ নিজের publisher-এর সেই একই topic, মানে চাকার motor driver-এর কান; আর <code>geometry_msgs/msg/Twist</code> — message-এর ধরন। মানে এই বাহন node-এর ভেতরের Python publisher নয় — ros2 CLI নিজেই একটা সম্পূর্ণ আলাদা publisher process হয়ে উঠবে।"},{"a":131,"b":132,"text":"<code>cmd2 = '''\"{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}\"'''</code> — বাইরে তিনটা single quote, ভেতরে পুরো payload double quote-এর মধ্যে। Triple-quote ব্যবহারের সুবিধা: ভেতরের double quote-গুলো escape ছাড়াই বসানো যায়; আর ওই double quote-গুলো shell-কে বোঝায় braces-এর পুরো মালাটা একটাই argument। ভেতরের বিষয়বস্তু YAML: <code>linear</code> আর <code>angular</code> দুই field-group, প্রতিটাতে x, y, z তিনটা করে — মোট ছয়টা সংখ্যা, সবগুলোই <code>0.0</code>; ros2 CLI এই YAML-কে parse করে একটা সম্পূর্ণ শূন্য <code>Twist</code> message বানাবে, অর্থাৎ L90-এর <code>Twist()</code>-এর মতোই \"কোনো অংশ নড়বে না\"। L132 <code>cmd = cmd1 + cmd2</code> — দুই টুকরো জোড়া লাগালেই সম্পূর্ণ shell command প্রস্তুত: <code>ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist \"{linear: ...}\"</code>।"},{"a":133,"b":133,"text":"<code>os.system(cmd)</code> — L13-এ <code>import os</code>-এর একমাত্র ব্যবহার এই লাইনেই (বাকি পুরো file-এ <code>os</code> আর কোথাও নেই)। Python এখানে একটা shell খুলে command-টা চালায়; ফলে সম্পূর্ণ আলাদা একটা process নিজেই <code>/cmd_vel</code>-এ একবার শূন্য-Twist publish করে বেরিয়ে যায়। প্রশ্ন উঠতেই পারে: L29-এর নিজের <code>pub_vel</code> দিয়ে <code>Twist()</code> পাঠালেই তো হতো? কিন্তু এই মুহূর্তটা teardown-এর মুহূর্ত — নিজের publisher আর rclpy context তখন অনিশ্চিত দশায় থাকতে পারে; <code>os.system</code>-এর brake node-এর কোনো অবস্থার উপর দাঁড়ানো নেই, node মরতে থাকলেও কাজ করে। শারীরিক অর্থে এটাই আসল ব্রেক: motor driver সর্বশেষ <code>/cmd_vel</code> command-ই ধরে রাখে, তাই শেষ scan-এর সিদ্ধান্ত Wave B-এর মতো <code>linear.x</code> ≈ +0.15 m/s হলে এই শূন্য-সংবাদ এসে চাকা থামায়। আর <code>--once</code>-এর কারণে এটা one-shot: L86-88-এর <code>Joy_active</code> brake যেখানে প্রতি scan-এ বারবার শূন্য publish করে, <code>exit_pro()</code> ঠিক একবারই।"},{"a":134,"b":136,"text":"L134-এর blank line-এর পরে class-এর বাইরে প্রথম ও একমাত্র top-level function: <code>def main():</code> — indent নেই, তাই এটা module-এর জিনিস, class-এর নয়। <b>এই file-এর সবচেয়ে বড় কৌতূহল এখানেই</b>: গোটা file-এ কোথাও <code>main()</code>-কে call করা হয় না, আর <code>if __name__ == '__main__':</code> guard-ও নেই — L146-এ এসে source শেষ, শেষ লাইনটাও <code>main()</code>-এর body-র ভেতরেই। তবু README L5-এর command <code>ros2 run yahboom_M3Pro_laser laser_Tracker</code> কাজ করে, কারণ package-এর <code>setup.py</code>-এর console_scripts entry point এই module-কে import করে <code>main()</code>-কে callable হিসেবে ডাকে — ROS 2-র standard কাঠামো (<code>setup.py</code> এই folder-এ নেই, তাই mechanism-টা <i>inferred</i>)। Function-এর প্রথম কাজ <code>rclpy.init()</code>: global rclpy context জন্মায় — এর উপরেই পরে প্রতিটা <code>Node</code> দাঁড়াবে, আর Ctrl+C-র signal ধরার ব্যবস্থাও এখান থেকেই আসে; L146-এর <code>rclpy.shutdown()</code> এই জোড়ার দ্বিতীয় প্রান্ত।"},{"a":137,"b":138,"text":"<code>laser_tracker = laserTracker(\"laser_Tracker_a1\")</code> — L18 থেকে L49 পর্যন্ত পুরো constructor এই এক লাইনের মধ্যে সম্পন্ন: <code>super().__init__(name)</code> নাম বসায়, <code>/scan</code> আর <code>/JoyState</code> দুই subscription (L23, L25), <code>/cmd_vel</code> publisher (L29), চারটা parameter read (L32-39), <code>Joy_active</code> flag আর দুটি <code>SinglePID</code> instance (L42-49)। Node-এর নাম <code>laser_Tracker_a1</code> — terminal-এ <code>ros2 node list</code> দিলে এই নামই দেখা যাবে; Python class-এর নাম <code>laserTracker</code> পৃথক জিনিস, একটা থেকে আরেকটা আসে না। <code>print (\"start it\")</code> — print আর বন্ধনীর মাঝে space, L14-এর <code>print (\"improt done\")</code>-এর মতোই author-এর style; Python-এ বৈধ। এই লাইনটা একটা কাজের checkpoint: console-এ \"start it\" দেখলে বুঝবে constructor নিঃশব্দে সফল, এখন folder 10-এর merger+filter chain-এর fused <code>/scan</code> এলেই follow-আচরণ শুরু হবে।"},{"a":139,"b":142,"text":"<code>try:</code>-এর ভেতরে <code>rclpy.spin(laser_tracker)</code> — পুরো program-এর হৃদপিণ্ড এই এক লাইন। এর আগ পর্যন্ত সব ছিল প্রস্তুতি; <code>spin</code> হলো event loop: main thread এখানেই block হয়ে যায়, আর executor ভেতরে ভেতরে message-এর অপেক্ষা করে — <code>/scan</code>-এ নতুন fused ring এলে <code>registerScan</code> (L56-125), <code>/JoyState</code> এলে <code>JoyStateCallback</code> (L52-54)। অর্থাৎ tracking-এর প্রতিটা সিদ্ধান্ত আসলে এই লাইনের ভেতরেই ঘটে চলে; callback-গুলো একটার পর একটা, single-threaded নিয়মে। <code>spin</code> স্বাভাবিক পথে ফেরে না, তাই <code>try</code>-তে মোড়ানো — terminal-এ Ctrl+C চাপলে SIGINT signal আসে, rclpy-র signal handler সেটাকে <code>KeyboardInterrupt</code> exception-এ রূপ দেয়, আর exception ঠিক <code>spin</code>-এর ভেতরে ফাটে। <code>except KeyboardInterrupt:</code> সেটাকে ধরে <code>pass</code> দিয়ে চুপচাপ গিলে যায় — terminal-এ লম্বা traceback ছাপা হয় না, execution শান্তভাবে নিচে <code>finally</code>-তে নামে।"},{"a":143,"b":146,"text":"<code>finally:</code> — গ্যারান্টি এটাই: <code>try</code> block যেভাবেই শেষ হোক (বাস্তবে এখানে একমাত্র পথটা Ctrl+C), এই block অবশ্যই চলবে। প্রথম কাজ <code>laser_tracker.exit_pro()</code> — পাশের comment <code># Force stop the wheels</code> উদ্দেশ্য বলে দিচ্ছে; L128-133-এর পুরো shell brake এই একটা call-এই চলে। এরপর <code>laser_tracker.destroy_node()</code>: <code>/cmd_vel</code> publisher, দুটো subscription, parameter — node-এর সব সরঞ্জাম cleanly ভেঙে DDS-এর দখল ছাড়ে। শেষে <code>rclpy.shutdown()</code>: L136-এর <code>rclpy.init()</code>-এ জন্মানো global context বন্ধ হয়। ক্রম বদলানো চলে না, নিয়ম LIFO: জন্মানোর সময় আগে context, পরে node; বন্ধের সময় আগে node, পরে context — nested জিনিস গোটানোর স্বাভাবিক নিয়ম, nested bracket বন্ধ করার মতোই। আর L146-ই এই file-এর শেষ লাইন — নিচে আর কিছু নেই, এমনকি trailing newline-ও নেই (তাই <code>wc -l</code> গুনে দেয় 145, সত্যি কথা splitlines-ই বলে: 146)। জন্ম (<code>init</code>), কর্ম (<code>spin</code>), বিদায় (<code>exit_pro</code>, <code>destroy_node</code>, <code>shutdown</code>): একটা tracking node-এর পূর্ণ জীবনচক্র, folder 11-এর <code>laser_Avoidance</code>-এর মতোই একই ছাঁচে সমাপ্ত।"}],"math":null,"robot":{"correct":"Terminal-এ Ctrl+C চাপলে SIGINT যায়, <code>spin</code>-এর ভেতরে <code>KeyboardInterrupt</code> ওঠে, <code>pass</code> সেটা গিলে যায়, তারপর <code>finally</code> থেকে <code>exit_pro()</code> একেবারে আলাদা shell process চালিয়ে <code>/cmd_vel</code>-এ ঠিক একবার সব-শূন্য Twist পাঠায় — শেষ scan-এর সিদ্ধান্ত Wave B-এর মতো <code>linear.x</code> ≈ +0.15 m/s সামনে ও <code>angular.z</code> ≈ +0.33 rad/s ঘোরা হলেও চাকা স্পষ্ট থামার আদেশ পেয়ে দাঁড়িয়ে যায়। এরপর <code>destroy_node()</code> publisher-subscription ছাড়ে, <code>rclpy.shutdown()</code> context বন্ধ করে; console-এ কোনো traceback ছাপা হয় না। Lidar-এর sensor-chain (README L3-এর launch-এর merger+filter) আলাদা process — সে চলতেই থাকে; বন্ধ হয় শুধু এই tracking node-টা।","incorrect":"বিপজ্জনক ভুল ধারণা: node মারলেই robot থামবে ভাবা। Terminal-এ <code>kill -9</code> মারলে <code>finally</code> চলেই না — <code>exit_pro()</code>-র শূন্য-Twist যায় না, আর base তখন শেষ <code>/cmd_vel</code> command ধরে রাখে: Wave B-এর <code>+0.15</code> m/s সামনের গতি চলতেই থাকে, robot নজরে রাখা object-এর দিকেই এগোতে থাকে যতক্ষণ না অন্য কিছু থামায়। আরেকটা ভুল: ফাইলটা সরাসরি <code>python3 laser_Tracker.py</code> দিয়ে চালানো — file-এর ভেতরে <code>main()</code> call করার কোনো লাইন নেই আর <code>__main__</code> guard-ও নেই, তাই import-time-এর <code>print (\"improt done\")</code> ছাপার পরেই সব থেমে যায়: কোনো node জন্মায় না, <code>/cmd_vel</code>-এ কিছু যায় না, চাকা একবারও নড়ে না। আর <code>rclpy.shutdown()</code>-কে <code>destroy_node()</code>-এর আগে ডাকলে context মরে যাওয়ার পর node teardown করতে গিয়ে error ছাপাবে।"},"animType":"safetyHalt"}];



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
    '<h1>12. lidar tracking <span class="path">— fused 360 scan-এর সামনের cone-এর সবচেয়ে কাছের object ধরে dual PID-এ 0.55 m stand-off-এ ফলো</span></h1>' +
    '<div class="intro-desc bn">এই application-টি <code>12. lidar tracking</code> folder-এর তিনটি source file — <code>README.md</code> (তিন command-এর runbook), <code>laser_driver.launch.py</code> (folder 10-এর merger আর filter launch file দুটিকে এক সঙ্গে চালানোর orchestrator) আর <code>laser_Tracker.py</code> (fused scan-এর সামনের cone থেকে সবচেয়ে কাছের object ধরে dual PID-এ <code>/cmd_vel</code>-এ কমান্ড দেওয়া behavior node) — কে কেন্দ্র করে তৈরি। ভেতরে আছে <code>IncludeLaunchDescription</code> দিয়ে chained launch, subscription-publisher graph, declare/get parameter জোড়া, প্রতিটি beam-এর angle math ও front-cone inequality, dual PID-এর target-current হিসাব, আর turn deadzone- damping-এর ধাপে ধাপে বিশ্লেষণ। প্রতিটি Part-এ আছে original code card, line-by-line Bangla explanation, Math derivation, Real Robot behavior এবং interactive animation।</div>' +
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
    '12. lidar tracking · line-by-line analysis · source preserved verbatim from /home/shariful/NeuroBotics/12. lidar tracking';
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

/* ================= folder-12 anims (v1 layer, 7 total) ================
   runbookFlow (part 1) · includeChain (part 3) · subPubGraph (part 6)
   beamSweep (part 10) · pidDial (part 13) · cmdVelVectors (part 14)
   safetyHalt (part 15)
   Facts from the three source files (README sha 3433bd6ce68a /
   driver dadf5ff3f9b1 / tracker d414af8d12da) + FACTS-12: README =
   3-command runbook (L1/L3/L5, L2/L4 blank); driver = constructor with
   two EAGER os.path.join paths to ira_laser_tools merge_multi.launch.py
   + yahboom_laser_filter laser_filter_node.launch.py (folder 10 chain,
   byte-identical driver to folder 11) and a 2-include return; tracker
   node laser_Tracker_a1 subscribes /scan (fused 360) + /JoyState,
   publishes /cmd_vel; parameters linear 0.5 · angular 1.0 · LaserAngle
   45.0 deg · ResponseDist 0.55 m — linear/angular are declared then
   NEVER read (no clamp anywhere); dual PID lin SinglePID(1,0,1) L47 /
   ang SinglePID(2,0,2) L49 (vendor internals not in folder; all pid
   numbers Kp-only illustrative); front cone |angle| < 45 strict = 89
   beams, ranges[i] != 0.0 passes inf; deadzone snap |d-0.55| < 0.1;
   /72 magic number; sign branch L110-114; turn deadzone |u| < 0.5
   (~18 deg Kp-only); x0.6 damping (ceiling ~0.75 rad/s); print at scan
   rate; publish per scan, motors keep last command; exit_pro()
   shell-brakes via ros2 topic pub --once. No __main__ guard, main()
   never called (setup.py entry, inferred).
   Stage = setStage 900x460 grammar. No emoji; arrow chars NEVER in
   stage <text> — only in the caption/formula strips below the stage
   (entities or words elsewhere). Unique id prefix per anim: rf- ic-
   sp- bs- pd- cv- sh-. Static backbone visible at setStage, first
   caption + formula set before the first await. */


/* ---------- runbookFlow ---------- */
/* ============ folder-12 anim — runbookFlow (part 1, v1 layer) ============
   README.md L1-L5 (5 lines, 3 nonblank): L1 sh start_agent.sh, L3 ros2
   launch yahboom_M3Pro_laser laser_driver.launch.py, L5 ros2 run
   yahboom_M3Pro_laser laser_Tracker; L2/L4 blank-line pauses.
   laser_driver.launch.py L8 generate_launch_description(), L28-42 list,
   IncludeLaunchDescription #1 (L32, ira_laser_tools merge_multi.launch.py,
   folder 10) + #2 (L38, yahboom_laser_filter laser_filter_node.launch.py)
   — byte-identical driver to folder 11. laser_Tracker.py: sub /scan L23
   + /JoyState L25, pub /cmd_vel L29, node name laser_Tracker_a1 L137,
   Joy_active gate L86-88; downstream semantics = FOLLOW the nearest
   front object at a 0.55 m stand-off (folder 11 avoided instead).
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
    txt(450, 26, 'README-র ৩টা command-ই এক runbook — bringup, launch chain, behavior', { anchor: 'middle', size: 14.5, weight: 600, fill: '#ffb454' }) +
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
    txt(66, 241, '  laser_Tracker', { size: 9.5, mono: true, weight: 700, fill: '#4fc3f7' }) +
    txt(384, 231, 'L5', { anchor: 'end', size: 8, mono: true, fill: '#6e7681' }) +
    txt(66, 255, 'launch file ছাড়া সরাসরি behavior executable', { size: 7.5, fill: '#8b949e', id: 'rf-c3s', op: 0 }) +
    txt(56, 278, 'ros2 launch বনাম ros2 run', { size: 8.5, weight: 700, fill: '#e6edf3' }) +
    txt(56, 296, 'L3 = ros2 launch — launch file-এর action তালিকা চালায়', { size: 8, fill: '#8b949e', id: 'rf-d1', op: 0 }) +
    txt(56, 312, 'L5 = ros2 run — সরাসরি একটা executable তোলে', { size: 8, fill: '#8b949e', id: 'rf-d2', op: 0 }) +
    txt(56, 332, 'দুই-ই এক package: yahboom_M3Pro_laser', { size: 8, mono: true, fill: '#c9d1d9', id: 'rf-d3', op: 0 }) +
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
    txt(452, 294, 'behavior process: laser_Tracker — node name laser_Tracker_a1 (L137)', { size: 7.5, mono: true, weight: 700, fill: '#4fc3f7', id: 'rf-proct', op: 0 }) +
    txt(452, 312, 'sub: /scan + /JoyState (L23, L25)', { size: 8, mono: true, fill: '#4fc3f7', id: 'rf-sub', op: 0 }) +
    txt(452, 326, 'pub: /cmd_vel (L29) -&gt; wheels', { size: 8, mono: true, fill: '#ff7b72', id: 'rf-pub', op: 0 }) +
    rrect(444, 336, 400, 22, 5, '#161b22', '#30363d', ' id="rf-gbox" opacity="0"') +
    txt(452, 351, 'front+rear raw -&gt; merger -&gt; filter -&gt; /scan -&gt; laser_Tracker -&gt; /cmd_vel', { size: 7.5, mono: true, weight: 700, fill: '#e3b341', id: 'rf-gtxt', op: 0 }) +
    txt(450, 386, 'রঙ-নিয়ম: সবুজ = driver ও raw, হলুদ = launch ও merger, বেগুনি = filter, নীল = behavior, লাল = /cmd_vel', { anchor: 'middle', size: 8.5, fill: '#8b949e' }) +
    txt(450, 440, 'source: README.md L1-L5 + laser_driver.launch.py L8-L42 + laser_Tracker.py L23-L29, L137', { anchor: 'middle', size: 8, mono: true, fill: '#6e7681' })
  );
  const q = id => svg.querySelector('#' + id);
  const show = id => q(id).setAttribute('opacity', 1);
  const edge = id => q(id).setAttribute('stroke', '#e3b341');
  host.caption('README-র ৩টা command-ই এক runbook: L1 bringup, L3 launch chain, L5 behavior। মাঝের L2/L4 ফাঁকা line — ধাপ দেখে নেওয়ার pause।');
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
  host.caption('include #1 ওঠায় folder 10-এর <code>laserscan_multi_merger</code>, include #2 ওঠায় <code>laser_filter_node</code> — chain: 2 raw → merger → filter → <code>/scan</code>। folder 10-এর chain-এর ফলই এই folder-এর node-এর চোখ।');
  await host.sleep(1700);
  edge('rf-c3'); show('rf-c3s'); show('rf-proc'); show('rf-proct'); show('rf-sub'); show('rf-pub');
  host.caption('<b>ros2 run yahboom_M3Pro_laser laser_Tracker</b> (L5) — এই folder-এর behavior process: subscribe করে <code>/scan</code> + <code>/JoyState</code> (L23, L25), publish করে <code>/cmd_vel</code> (L29) — চাকার হুকুম এখান থেকেই।');
  await host.sleep(1700);
  show('rf-d1'); show('rf-d2'); show('rf-d3');
  host.caption('<code>ros2 launch</code> বনাম <code>ros2 run</code>: launch একটা file-এর ভেতরের action-তালিকা চালায় (L3-এ দুইটা include উঠেছিল), run সরাসরি একটা executable তোলে (L5)। দুই command-ই একই <code>yahboom_M3Pro_laser</code> package-র ভেতর থেকে।');
  host.formula('ros2 launch = actions from a launch file  |  ros2 run = one executable, no file');
  await host.sleep(1700);
  show('rf-gbox'); show('rf-gtxt');
  host.caption('পুরো chain এক line-এ: front+rear raw → merger → filter → /scan → laser_Tracker → /cmd_vel। আর <code>/JoyState</code> true হলে মানুষের joystick জিতে যায় (L86-88) — নাহলে চলে সামনের cone-এর সবচেয়ে কাছের object-এর হিসাব।');
  host.formula('folder 10: 2 raw -> merger -> filter -> /scan  |  folder 12: /scan -> laser_Tracker -> /cmd_vel');
  await host.sleep(1700);
  host.caption('৩টা command, ৫টা line — একটাও এলোমেলো নয়: প্রত্যেকটা আগের ধাপের ফলের ওপর দাঁড়িয়েছে। এবার ঢুকব laser_Tracker-এর ভেতরে — পরের part-এ সেই হিসাব।');
  await host.sleep(1500);
};

/* ---------- includeChain ---------- */
/* ===== folder-12 part 3 — includeChain (prefix ic-) ================
   laser_driver.launch.py L8-L24: constructor builds TWO eager paths via
   os.path.join(get_package_share_directory(pkg), 'launch', file) for
   ira_laser_tools/merge_multi.launch.py (L12-16) and
   yahboom_laser_filter/laser_filter_node.launch.py (L20-24); each then
   wrapped PythonLaunchDescriptionSource -> IncludeLaunchDescription and
   queued for the L28 LaunchDescription return (run = next part).
   Driver byte-identical to folder 11 (same sensor chain for the
   tracking node). Contrast per FACTS-12: plain call = EAGER at
   constructor time, unlike folder 10's lazy LaunchConfiguration.
   Share-dir prefixes illustrative.
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
    txt(450, 448, 'source: laser_driver.launch.py L8-L24, L28, L32-34, L38-40 (imports L2/L4/L5) + README L3', { anchor: 'middle', size: 8, mono: true, fill: '#6e7681' })
  );
  const q = id => svg.querySelector('#' + id);
  const show = id => q(id).setAttribute('opacity', 1);
  const edge = id => q(id).setAttribute('stroke', '#e3b341');
  host.caption('README-র L3 command চালালে <code>ros2 launch</code> এই file-টা পড়ে তার <code>generate_launch_description()</code>-কে ডাকে। এই anim-এ দেখব ভেতরে কী হয় — এই মুহূর্তে কোনো process এখনও জন্মায়নি।');
  host.formula('ros2 launch yahboom_M3Pro_laser laser_driver.launch.py -> constructor NOW -> run actions later');
  await host.sleep(1500);
  edge('ic-cA'); show('ic-k1'); show('ic-k1t'); show('ic-k1b');
  host.caption('<b>L8</b> — <code>def generate_launch_description():</code>। এটাই constructor: LaunchDescription-এর নকশা এখন তৈরি হবে, একটাও process এখন run হচ্ছে না — run আলাদা phase, পরের part-এর গল্প।');
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
  host.caption('মোদ্দা কথা: README-র এক command (L3) দুটো অন্য package-এর launch file নিজের ভেতরে টেনে আনে — folder 10-এর পুরো merger + filter chain এক আঁজলায়। দুই path EAGER বলে সব মান constructor-এই ঠিকঠাক বসে গেছে; স্ক্রিন এখন run-এর আগের নীরব ছবি।');
  await host.sleep(1500);
};

/* ---------- subPubGraph ---------- */
/* ===== folder-12 anim — subPubGraph (part 6, laser_Tracker.py L17-L30) =====
   দুই ear (/scan, /JoyState) + এক mouth (/cmd_vel) — constructor-এর পুরো নকশা।
   Facts: L17 class laserTracker(Node), L18 def __init__(self,name),
   L19 super().__init__(name), L23 create_subscription(LaserScan,
   "/scan", self.registerScan,1), L25 create_subscription(Bool,
   '/JoyState', self.JoyStateCallback,1), L29 create_publisher(Twist,
   '/cmd_vel',1), L30 blank, L31-32 declare_parameter শুরু; node name
   laser_Tracker_a1 আসে main() L137 থেকে। /scan = folder 10 chain-এর
   fused 360 ফল। Same sub/pub topology as folder 11's avoidance node —
   the difference is downstream (follow vs avoid), not the wiring.
   Stage strings-এ arrow character নেই; id prefix sp-. */


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
    txt(450, 26, 'constructor L17-L30: class জন্ম, দুই ear, এক mouth', { anchor: 'middle', size: 14, weight: 600, fill: '#ffb454' }) +
    rrect(40, 44, 372, 316, 8, '#0d1117', '#2a3442') +
    txt(56, 64, 'LASER_TRACKER.PY — CONSTRUCTOR', { size: 9.5, weight: 700, fill: '#e6edf3' }) +
    rrect(50, 74, 342, 58, 4, '#161b22', '#e3b341', ' id="sp-h1" opacity="0"') +
    rrect(50, 131, 342, 58, 4, '#161b22', '#7ee787', ' id="sp-h2" opacity="0"') +
    rrect(50, 188, 342, 40, 4, '#161b22', '#4fc3f7', ' id="sp-h3" opacity="0"') +
    rrect(50, 226, 342, 58, 4, '#161b22', '#e3b341', ' id="sp-h4" opacity="0"') +
    txt(56, 86, 'class laserTracker(Node):', { size: 8.5, mono: true, weight: 700, fill: '#e6edf3' }) +
    txt(392, 86, 'L17', { anchor: 'end', size: 7.5, mono: true, fill: '#6e7681' }) +
    txt(64, 105, 'def __init__(self,name):', { size: 8.5, mono: true, fill: '#c9d1d9' }) +
    txt(76, 124, 'super().__init__(name)', { size: 8.5, mono: true, fill: '#c9d1d9' }) +
    txt(392, 124, 'L19', { anchor: 'end', size: 7.5, mono: true, fill: '#6e7681' }) +
    txt(64, 143, '# --- CREATING SUBSCRIBERS (Listeners) ---', { size: 7.5, mono: true, fill: '#6e7681' }) +
    txt(72, 162, 'self.sub_laser = self.create_subscription(', { size: 8.5, mono: true, fill: '#7ee787' }) +
    txt(392, 162, 'L23', { anchor: 'end', size: 7.5, mono: true, fill: '#6e7681' }) +
    txt(84, 181, 'LaserScan,"/scan",self.registerScan,1)', { size: 8.5, mono: true, fill: '#7ee787' }) +
    txt(72, 200, 'self.sub_JoyState = self.create_subscription(', { size: 8.5, mono: true, fill: '#4fc3f7' }) +
    txt(392, 200, 'L25', { anchor: 'end', size: 7.5, mono: true, fill: '#6e7681' }) +
    txt(84, 219, 'Bool,\'/JoyState\', self.JoyStateCallback,1)', { size: 8.5, mono: true, fill: '#4fc3f7' }) +
    txt(64, 238, '# --- CREATING PUBLISHERS (Radio Stations) ---', { size: 7.5, mono: true, fill: '#6e7681' }) +
    txt(72, 257, 'self.pub_vel = self.create_publisher(', { size: 8.5, mono: true, fill: '#e3b341' }) +
    txt(392, 257, 'L29', { anchor: 'end', size: 7.5, mono: true, fill: '#6e7681' }) +
    txt(84, 276, 'Twist,\'/cmd_vel\',1)', { size: 8.5, mono: true, fill: '#e3b341' }) +
    txt(56, 310, 'L20 L26 L30 = ফাঁকা line — constructor-এর সীমানা L30-এ শেষ', { size: 7.5, fill: '#6e7681' }) +
    txt(56, 326, 'L22 L24 L28-এ শুধু ইংরেজি ব্যাখ্যা-মন্তব্য', { size: 7.5, fill: '#6e7681' }) +
    rrect(428, 44, 432, 316, 8, '#111', '#30363d') +
    txt(644, 64, 'ROS GRAPH — দুই ear, এক mouth', { anchor: 'middle', size: 9.5, weight: 700, fill: '#e6edf3' }) +
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
    txt(506, 296, 'msg: Bool, cb: JoyStateCallback', { anchor: 'middle', size: 6.5, mono: true, fill: '#8b949e', id: 'sp-joyL', op: 0 }) +
    txt(506, 308, 'queue depth 1 — মানুষের override bit', { anchor: 'middle', size: 6.5, fill: '#6e7681', id: 'sp-joyL2', op: 0 }) +
    rrect(584, 168, 144, 118, 10, '#161b22', '#e3b341', ' id="sp-nodeB" opacity="0"') +
    txt(656, 190, 'laserTracker', { anchor: 'middle', size: 12, mono: true, weight: 700, fill: '#e6edf3', id: 'sp-nodeT', op: 0 }) +
    txt(656, 204, 'class — L17', { anchor: 'middle', size: 7, fill: '#8b949e', id: 'sp-nodeC', op: 0 }) +
    rrect(598, 214, 116, 20, 4, '#161b22', '#d2a8ff', ' id="sp-nameB" opacity="0"') +
    txt(656, 228, 'laser_Tracker_a1', { anchor: 'middle', size: 7.5, mono: true, weight: 700, fill: '#d2a8ff', id: 'sp-nameT', op: 0 }) +
    txt(656, 250, 'parent: super().__init__(name)', { anchor: 'middle', size: 6.5, mono: true, fill: '#8b949e', id: 'sp-supT', op: 0 }) +
    txt(656, 268, 'নামটা পাঠাবে main() — L137', { anchor: 'middle', size: 6.5, fill: '#6e7681', id: 'sp-nameN', op: 0 }) +
    txt(749, 196, 'MOUTH', { anchor: 'middle', size: 6.5, weight: 700, fill: '#e3b341', id: 'sp-mouthT', op: 0 }) +
    spArrow(730, 227, 768, 227, '#e3b341', 'sp-a3') +
    txt(749, 217, '/cmd_vel', { anchor: 'middle', size: 7, mono: true, weight: 700, fill: '#e3b341', id: 'sp-cmdT', op: 0 }) +
    rrect(772, 202, 72, 50, 8, '#0d1117', '#e3b341', ' id="sp-whB" opacity="0"') +
    txt(808, 221, 'wheels', { anchor: 'middle', size: 8.5, mono: true, weight: 700, fill: '#e3b341', id: 'sp-whT', op: 0 }) +
    txt(808, 236, 'base driver', { anchor: 'middle', size: 6.5, fill: '#8b949e', id: 'sp-whT2', op: 0 }) +
    rrect(764, 264, 88, 34, 4, '#161b22', '#d2a8ff', ' id="sp-twB" opacity="0"') +
    txt(808, 277, 'Twist', { anchor: 'middle', size: 7.5, mono: true, weight: 700, fill: '#d2a8ff', id: 'sp-twT', op: 0 }) +
    txt(808, 290, 'linear.x + angular.z', { anchor: 'middle', size: 6.2, mono: true, fill: '#d2a8ff', id: 'sp-twT2', op: 0 }) +
    rrect(690, 322, 140, 24, 4, '#161b22', '#d2a8ff', ' id="sp-nextB" opacity="0"') +
    txt(760, 337, 'NEXT L32: declare_parameter', { anchor: 'middle', size: 7, mono: true, fill: '#d2a8ff', id: 'sp-nextT', op: 0 }) +
    txt(450, 386, 'রঙ-নিয়ম: সবুজ = /scan, নীল = /JoyState, হলুদ = /cmd_vel ও parent, বেগুনি = নাম ও msg টাইপ', { anchor: 'middle', size: 8.5, fill: '#8b949e' }) +
    txt(450, 440, 'source: laser_Tracker.py L17-L30 + main() L137', { anchor: 'middle', size: 8, mono: true, fill: '#6e7681' })
  );
  const q = id => svg.querySelector('#' + id);
  const show = id => q(id).setAttribute('opacity', 1);
  const dimc = id => q(id).setAttribute('stroke', '#30363d');
  host.caption('Constructor-এর পুরো নকশা এই কয়েকটা beat-এ: L17-এ class জন্ম, তারপর দুটো subscription আর একটা publisher। বাঁয়ে আসল code, ডানে তার graph।');
  host.formula('constructor = class birth + super wiring + 2 subscriptions + 1 publisher');
  await host.sleep(1400);

  show('sp-h1'); show('sp-nodeB'); show('sp-nodeT'); show('sp-nodeC');
  show('sp-parentB'); show('sp-parentT'); show('sp-pwire'); show('sp-supT');
  host.caption('<b>class laserTracker(Node)</b> (L17) — rclpy-র <code>Node</code> থেকে inherit করে নতুন class জন্মাল। <b>super().__init__(name)</b> (L19) parent-এর constructor ডেকে এই বাচ্চাটাকে ROS graph-এ সত্যিকারের node বানিয়ে দেয়।');
  host.formula('super().__init__(name) -> laserTracker instance becomes a live node');
  await host.sleep(1600);

  show('sp-nameB'); show('sp-nameT'); show('sp-nameN');
  host.caption('একটা সূক্ষ্ম পয়েন্ট: class-এর নাম <code>laserTracker</code>, কিন্তু node-এর নাম আলাদা — <code>laser_Tracker_a1</code>। এই নামটা constructor নিজে বানায় না; পরে <b>main()</b> (L137) argument হিসেবে পাঠাবে। দুটো আলাদা জিনিস।');
  host.formula('class name: laserTracker   |   node name: laser_Tracker_a1 (main, L137)');
  await host.sleep(1700);

  dimc('sp-h1');
  show('sp-h2'); show('sp-ear1'); show('sp-scanB'); show('sp-scanT');
  show('sp-ring'); show('sp-scanL1'); show('sp-scanL2'); show('sp-a1');
  show('sp-a1m'); show('sp-a1cb'); show('sp-q1');
  host.caption('প্রথম ear (L23): <code>create_subscription(LaserScan, "/scan", self.registerScan, 1)</code>। Folder 10-এর পুরো chain (merge + filter) যে fused 360 ring বানিয়েছিল, সেটাই <code>/scan</code> topic-এ বয়ে আসে — এই node তার প্রথম কান খোলে। Queue depth 1: পুরনো frame জমা রাখার দরকার নেই।');
  host.formula('sub_laser = create_subscription(LaserScan, /scan, registerScan, depth 1)');
  await host.sleep(1800);

  dimc('sp-h2');
  show('sp-h3'); show('sp-ear2'); show('sp-joyB'); show('sp-joyT');
  show('sp-a2'); show('sp-joyL'); show('sp-joyL2');
  host.caption('দ্বিতীয় ear (L25): <code>Bool</code> টাইপের <code>/JoyState</code> — মানুষ joystick ধরলে কি না, এই এক bit। <code>JoyStateCallback</code> সেটা <code>Joy_active</code> flag-এ জমা রাখে (L46, L51); flag সত্যি হলে AI থেমে শূন্য <code>Twist</code> পাঠিয়ে দাঁড়িয়ে থাকে (L83-85)।');
  host.formula('sub_JoyState = create_subscription(Bool, /JoyState, JoyStateCallback, depth 1)');
  await host.sleep(1800);

  dimc('sp-h3');
  show('sp-h4'); show('sp-mouthT'); show('sp-a3'); show('sp-cmdT');
  show('sp-whB'); show('sp-whT'); show('sp-whT2');
  host.caption('এবং একমাত্র mouth (L29): <code>create_publisher(Twist, \'/cmd_vel\', 1)</code> — registerScan-এর ভেতরে নেওয়া সিদ্ধান্ত এই wire দিয়ে বেরোয়, base driver-এর কাছে গিয়ে wheels-কে ঘোরায়।');
  host.formula('pub_vel = create_publisher(Twist, /cmd_vel, depth 1)');
  await host.sleep(1700);

  show('sp-twB'); show('sp-twT'); show('sp-twT2');
  host.caption('Mouth-এর ভাষাও ঠিক করা: <code>Twist</code> message-এর এখানে দুটো ঘরই কাজে লাগে — <code>linear.x</code> (সামনের গতি, m/s) আর <code>angular.z</code> (ঘোরা, rad/s)। এই দুটোর মান আসবে পরের অংশের দুই PID হিসাব থেকে — declared <code>linear</code>/<code>angular</code> parameter-এর মান (L33, L35-এ পড়া হয়) পরে আর কোথাও ব্যবহারই হয় না।');
  host.formula('Twist = linear.x (m/s) + angular.z (rad/s)');
  await host.sleep(1700);

  show('sp-nextB'); show('sp-nextT');
  host.caption('পুরো ছবি দাঁড়াল: দুই ear, এক mouth। Constructor-এর নিজের কাজ L30-এই শেষ — L32 থেকে শুরু <code>declare_parameter</code>-এর সারি: linear 0.5, angular 1.0, LaserAngle 45.0, ResponseDist 0.55। সেটাই পরের অংশের গল্প।');
  host.formula('graph: 2 in (/scan, /JoyState) + 1 out (/cmd_vel) -> decision in, wheels out');
  await host.sleep(1700);
};

/* ---------- beamSweep ---------- */
/* ============ folder-12 v1 anim — beamSweep (part 10) ================
   laser_Tracker.py registerScan beam loop, L56-L72. Stage: top-down
   fused 360 ring (folder 10 merger+filter -> /scan), deg 0 up, +deg
   LEFT (ROS ccw). Beats: L56 def + L57 guard, L58 ranges np.array,
   L61-62 two empty parallel lists, L65 cursor sweep i=0.., L67
   rad->deg formula (i=192 -> +12 deg), L70 front cone gate
   abs(angle) < LaserAngle (45.0, L36) strict -> 89 beams i=136..224,
   ranges[i] !=0.0 skips no-return zeros but passes inf, L71-72
   parallel appends. Wave-B object 0.70 m @ +20 deg, second 0.90 m @
   -10 deg; min() preview belongs to next part. Ring ranges
   illustrative. Prefix bs-. No emoji, no arrow chars in stage
   strings, entities for &lt; &gt;. */

/* --- prefixed polar helpers (deg: 0 = up, +deg = screen left) --- */
function bsBeam(deg) {
  const a = (deg + 180) % 360 - 180;
  if (Math.abs(a) < 45) {                              /* front cone */
    if (Math.abs(a - 20) <= 3) return 0.70;            /* tracked object */
    if (Math.abs(a + 10) <= 3) return 0.90;            /* second object */
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
  const objA = bsXY(266, 226, 95, -10, 0.90);
  const l45 = bsXY(266, 226, 1, 45, 176);
  const lm45 = bsXY(266, 226, 1, -45, 176);
  const zBand = bsXY(266, 226, 1, 66, 130);
  const svg = host.setStage(
    txt(450, 26, 'beam loop: সামনের cone-এর ভেতরে সবচেয়ে কাছের object-এর খোঁজ — L56-L72', { anchor: 'middle', size: 14, weight: 600, fill: '#ffb454' }) +
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
    txt(objA[0] - 8, objA[1] - 8, '0.90 m @ -10', { anchor: 'end', size: 7.5, weight: 700, fill: '#d2a8ff', id: 'bs-objAt', op: 0 }) +
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
    /* ---------- right: code L56-L72 ---------- */
    rrect(516, 44, 344, 252, 8, '#0d1117', '#30363d') +
    txt(688, 62, 'registerScan — beam loop (L56-L72)', { anchor: 'middle', size: 9, weight: 700, fill: '#e6edf3' }) +
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
    txt(848, 80, 'L56', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    txt(848, 94, 'L57', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    txt(848, 105, 'L58', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    txt(848, 119, 'L61', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    txt(848, 132, 'L62', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    txt(848, 145, 'L65', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    txt(848, 159, 'L67', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    txt(848, 186, 'L70', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    txt(848, 199, 'L71', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    txt(848, 212, 'L72', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    /* ---------- right: the two parallel lists ---------- */
    rrect(516, 306, 344, 78, 8, '#111', '#30363d') +
    txt(688, 322, 'দুই parallel list — cone-এ ধরা পড়া বীম', { anchor: 'middle', size: 8.5, weight: 700, fill: '#e6edf3' }) +
    rrect(528, 330, 118, 46, 5, '#161b22', '#7ee787') +
    txt(587, 343, 'minDistList (m)', { anchor: 'middle', size: 7, mono: true, weight: 700, fill: '#7ee787' }) +
    txt(538, 360, '0.90', { size: 9, mono: true, weight: 700, fill: '#e6edf3', id: 'bs-v1', op: 0 }) +
    txt(570, 371, '0.70', { size: 9, mono: true, weight: 700, fill: '#ff7b72', id: 'bs-v2', op: 0 }) +
    rrect(654, 330, 118, 46, 5, '#161b22', '#e3b341') +
    txt(713, 343, 'minDistIDList (deg)', { anchor: 'middle', size: 7, mono: true, weight: 700, fill: '#e3b341' }) +
    txt(664, 360, '-10', { size: 9, mono: true, weight: 700, fill: '#e6edf3', id: 'bs-v3', op: 0 }) +
    txt(696, 371, '+20', { size: 9, mono: true, weight: 700, fill: '#ff7b72', id: 'bs-v4', op: 0 }) +
    txt(790, 360, 'len', { anchor: 'middle', size: 7, mono: true, fill: '#8b949e' }) +
    txt(790, 374, '2', { anchor: 'middle', size: 11, mono: true, weight: 700, fill: '#e6edf3', id: 'bs-len' }) +
    /* ---------- bottom strip: legend + notes ---------- */
    '<path d="M48 393h7v7h-7z" fill="#7ee787"/><path d="M156 393h7v7h-7z" fill="#ff7b72"/><path d="M262 393h7v7h-7z" fill="#d2a8ff"/><path d="M368 393h7v7h-7z" fill="#6e7681"/>' +
    txt(60, 400, 'ring beam &lt; 45° বাইরে', { size: 8, fill: '#8b949e' }) +
    txt(168, 400, 'tracked 0.70 m @ +20°', { size: 8, fill: '#8b949e' }) +
    txt(274, 400, 'দ্বিতীয় 0.90 m @ -10°', { size: 8, fill: '#8b949e' }) +
    txt(380, 400, 'ranges = 0.0 (skip)', { size: 8, fill: '#8b949e' }) +
    txt(48, 416, ' ', { size: 7.5, weight: 700, fill: '#e3b341', id: 'bs-note', op: 0 }) +
    txt(48, 430, 'LaserAngle = 45.0 (L36) · কঠোর &lt; মানে cone-এ 89 beam (i = 136..224) — ring-এর মান illustrative', { size: 7.5, fill: '#6e7681' }) +
    txt(450, 450, 'source: laser_Tracker.py L56-L72 · laser_driver.launch.py L28-L42 (folder 10 chain)', { anchor: 'middle', size: 8, mono: true, fill: '#6e7681' })
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
  host.caption('folder 10-এর merger দুই lidar জোড়ে এক fused 360 ring বানায়, filter সেটিকেই <code>/scan</code>-এ দেয় — তাই <code>registerScan</code>-এর <code>ranges</code> একটাই পূর্ণ বৃত্ত। এই anim-এ L56-72: সেই বৃত্ত ঘেঁটে সামনের cone-এর সবচেয়ে কাছের object-এর খোঁজ। ছবিতে deg 0 = সামনে, +deg = বাঁদিক (ROS convention)।');
  host.formula('angle_i = (angle_min + angle_increment * i) * RAD2DEG   [rad -> deg, RAD2DEG = 180/pi]');
  /* --- beat 1: L56 def + L57 guard + L58 ranges --- */
  show('bs-hl1'); show('bs-hl2');
  host.caption('<b>L56</b> <code>def registerScan(self, scan_data)</code> — /scan-এর প্রতিটা message এই callback-এ আসবে (subscription L23)। <b>L57</b> পাহারা: message-টা সত্যিই <code>LaserScan</code> না হলে সোজা <code>return</code>। <b>L58</b> <code>ranges = np.array(scan_data.ranges)</code> — দূরত্বের মানগুলো numpy array-তে তোলা।');
  await host.sleep(1700);
  hide('bs-hl1'); hide('bs-hl2'); show('bs-hl3');
  host.caption('দুটো খালি list জন্মাল (<b>L61-62</b>): <code>minDistList</code> রাখবে দূরত্ব, <code>minDistIDList</code> রাখবে সেই দূরত্বের beam-এর কোণ — একই beam-এর দুটো পাশ, index-এ index। এদের জোড়া পরে <code>min()</code>-এর সময় কাজে লাগবে।');
  host.formula('minDistList[k] = distance of beam k  |  minDistIDList[k] = angle of beam k');
  await host.sleep(1700);
  /* --- beat 2: L65 sweep --- */
  hide('bs-hl3'); show('bs-hl4');
  host.caption('L65 <code>for i in range(len(ranges))</code> — cursor-টা i=0 (deg -180, একদম পেছনে) থেকে বেয়ে বেয়ে হাঁটে; প্রতিটি i মানে <code>ranges</code> অ্যারের একটা দূরত্ব-মান। tracking-এর খোঁজও শুরু এখান থেকেই — সামনে, পেছনে সব beam-ই ঘোরা হবে।');
  await host.sleep(700);
  const bsHops = [-180, -144, -108, -72, -36, 0, 36, 72, 108, 144];
  for (let k = 0; k < bsHops.length; k++) { bsAim(bsHops[k]); await host.sleep(230); }
  /* --- beat 3: L67 formula --- */
  host.caption('L67: <code>angle = (scan_data.angle_min + scan_data.angle_increment * i) * RAD2DEG</code> — message-এ কোণ radian-এ (folder 09-এর echo), কিন্তু cone-এর তুলনা degree-তে; <code>RAD2DEG = 180 / pi</code> (L15)। এই fused ring-এ (illustrative) angle_min = -180 deg আর increment = 1 deg বীমপ্রতি, তাই angle = -180 + i।');
  host.formula('i = 192:  (-180 + 192) = +12 deg   (front-left beam)');
  hide('bs-hl4'); show('bs-hl5'); bsAim(12);
  await host.sleep(1700);
  /* --- beat 4: L70 cone gate --- */
  host.caption('FRONT cone (L70): <code>abs(angle) &lt; self.LaserAngle</code>, LaserAngle = 45.0 (L36) — সবুজ arc মানে ±45 deg। সঙ্গে <code>ranges[i] !=0.0</code>: 0.0 মানে beam কিছুই পায়নি — সেই beam-গুলো বাদ; কিন্তু <code>inf</code> (no-return) এই চেক পাস করে ফেলে — 0 আর inf এক নয়।');
  host.formula('cone: |angle| < 45.0 deg AND ranges[i] != 0.0   ->  i = 136..224 = 89 beams');
  hide('bs-hl5'); show('bs-hl6'); show('bs-fa'); show('bs-zt'); show('bs-objBt'); show('bs-objAt');
  bsAim(66);
  await host.sleep(1800);
  /* --- beat 5: L71-72 appends --- */
  host.caption('gate পাস করলেই দুটো append (<b>L71-72</b>): দূরত্ব যায় <code>minDistList</code>-এ, কোণ যায় <code>minDistIDList</code>-এ। ডেমো ring-এ cone-এ দুটো object: 0.90 m @ -10° আর 0.70 m @ +20° (illustrative) — দুজনের দূরত্ব-কোণ জোড়া পাশাপাশি বসছে।');
  host.formula('append pair: (0.90, -10) then (0.70, +20)  |  len(minDistList) = len(minDistIDList)');
  hide('bs-hl6'); show('bs-hl7'); show('bs-v1'); show('bs-v2'); show('bs-v3'); show('bs-v4');
  bsAim(-10); await host.sleep(650);
  bsAim(20); q('bs-len').textContent = '2';
  await host.sleep(1600);
  /* --- close --- */
  q('bs-note').textContent = 'loop শেষ — এবার min(minDistList) (L77) আর argmin জোড়া (L79): minDist = 0.70, minDistID = +20';
  show('bs-note');
  host.caption('loop শেষে দুই list-এ cone-এর সব ধরা-পড়া beam। পরের ধাপ (L77-79): <code>minDist = min(minDistList)</code> = <b>0.70 m</b>, আর <code>minDistID</code> = সেই কাছের beam-এর কোণ = <b>+20 deg</b> — argmin-এর মতো জোড়া, tie হলে প্রথমটা জেতে। List শূন্য হলে (L80-83) সামনে কিছু নেই — <code>return</code>, কোনো publish নেই।');
  host.formula('minDist = min(list) = 0.70 m  |  minDistID = list[index(minDist)] = +20 deg');
  await host.sleep(1700);
  host.caption('মোদ্দা কথা: avoidance (folder 11) গুনত কত beam কাছে — এই node বরং খোঁজে কোন beam-টা সবচেয়ে কাছে। 89 beam-এর ভেতরের min-ই tracking-এর টার্গেট: ওই object-কেই 0.55 m দূরত্বে ফেলে রাখতে হবে, মুখ তার দিকেই রাখতে হবে।');
  await host.sleep(1600);
};
/* ---------- pidDial ---------- */
/* ===== folder-12 v1 anim — pidDial (part 13) =========================
   laser_Tracker.py L97-L114, the dual-PID heart. Left: code card
   L98-L114 (L102 linear call, L107 angular call, L110-114 sign
   branch). Right: two PID cards — lin SinglePID(1.0,0,1.0) born L47,
   ang SinglePID(2.0,0,2.0) born L49, constructed once, state
   persists across scans. Wave-B illustrative numbers: minDist 0.70,
   minDistID +20 -> lin (0.55,0.70) e=-0.15 u~=-0.15, minus sign ->
   linear.x ~ +0.15 approach; ang (20/72, 0) u ~= 2*0.278 = 0.556.
   Vendor SinglePID internals NOT in this folder — all pid outputs
   are Kp-only illustrative views. Sign branch: 0 < id -> +u (CCW
   left), id < 0 -> -u (CW right), id == 0.0 -> neither, angular.z
   stays 0.0. No clamp anywhere: declared linear 0.5 (L33) never
   enforced; /72 magic number, only explanation L106, max target
   < 45/72 = 0.625. Prefix pd-. No emoji, no arrow chars in stage
   strings, entities for &lt; &gt;. */

ANIMS.pidDial = async function (host) {
  const svg = host.setStage(
    txt(450, 26, 'dual PID: দূরত্ব মেলাও (linear), মুখ ঘোরাও (angular) — L102, L107, L110-114', { anchor: 'middle', size: 13.5, weight: 600, fill: '#ffb454' }) +
    /* ---------- left: code L97-L114 ---------- */
    rrect(40, 44, 340, 316, 8, '#0d1117', '#2a3442') +
    txt(56, 62, 'CODE — laser_Tracker.py L97-L114', { size: 9.5, weight: 700, fill: '#e6edf3' }) +
    rrect(50, 92, 320, 15, 3, '#21262d', 'none', ' id="pd-hl1" opacity="0"') +
    rrect(50, 168, 320, 15, 3, '#21262d', 'none', ' id="pd-hl2" opacity="0"') +
    rrect(50, 216, 320, 27, 3, '#21262d', 'none', ' id="pd-hl3" opacity="0"') +
    rrect(50, 253, 320, 27, 3, '#21262d', 'none', ' id="pd-hl4" opacity="0"') +
    txt(58, 86, '# LINEAR PID: ... Target (0.55m) ... Current (minDist)', { size: 7, mono: true, fill: '#6e7681' }) +
    txt(58, 104, '# The negative sign is because if we are too', { size: 7, mono: true, fill: '#6e7681' }) +
    txt(58, 117, '# far away, ... positive forward speed ... (L100-101)', { size: 7, mono: true, fill: '#6e7681' }) +
    txt(58, 134, 'velocity.linear.x = -self.lin_pid.', { size: 8, mono: true, fill: '#c9d1d9' }) +
    txt(58, 147, '  pid_compute(self.ResponseDist, minDist)', { size: 8, mono: true, fill: '#c9d1d9' }) +
    txt(368, 147, 'L102', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    txt(58, 168, '# ANGULAR PID ... Dividing by 72 just scales', { size: 7, mono: true, fill: '#6e7681' }) +
    txt(58, 181, 'ang_pid_compute = self.ang_pid.pid_compute(', { size: 8, mono: true, fill: '#c9d1d9' }) +
    txt(58, 194, '  abs(minDistID) / 72, 0)', { size: 8, mono: true, fill: '#c9d1d9' }) +
    txt(368, 194, 'L107', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    txt(58, 216, 'if 0 &lt; minDistID :', { size: 8, mono: true, fill: '#c9d1d9' }) +
    txt(58, 230, 'velocity.angular.z = ang_pid_compute', { size: 8, mono: true, fill: '#c9d1d9' }) +
    txt(368, 230, 'L110-111', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    txt(58, 253, 'elif minDistID &lt; 0:', { size: 8, mono: true, fill: '#c9d1d9' }) +
    txt(58, 267, 'velocity.angular.z = -ang_pid_compute', { size: 8, mono: true, fill: '#c9d1d9' }) +
    txt(368, 267, 'L113-114', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    txt(58, 290, 'L109/L112-এর comment: বাঁ = positive angle, ডান = negative', { size: 7, fill: '#6e7681' }) +
    txt(58, 306, 'minDistID = 0.0 হলে দুই branch-ই মিস — z আগের মানে', { size: 7, fill: '#6e7681', id: 'pd-zero', op: 0 }) +
    txt(58, 330, 'minDist = 0.70 m · minDistID = +20° (Wave B, illustrative)', { size: 7.5, weight: 700, mono: true, fill: '#e3b341', id: 'pd-wave', op: 0 }) +
    txt(58, 348, 'vendor SinglePID-এর ভেতরটা এই folder-এ নেই — pid ফল Kp-only illustrative', { size: 6.8, fill: '#6e7681' }) +
    /* ---------- right-top: LIN PID card ---------- */
    rrect(396, 44, 234, 148, 8, '#0d1117', '#7ee787') +
    txt(408, 62, 'LIN PID — SinglePID(1.0, 0.0, 1.0)', { size: 8.5, mono: true, weight: 700, fill: '#7ee787' }) +
    txt(408, 74, 'জন্ম L47-এ, একবারই — state scan-এ স্ক্যানে বাঁচে', { size: 6.8, fill: '#8b949e' }) +
    rrect(408, 82, 210, 16, 3, '#161b22', '#30363d') +
    txt(414, 93, 'call: pid_compute(0.55, 0.70)  (target, current)', { size: 7, mono: true, fill: '#c9d1d9' }) +
    rrect(408, 102, 100, 14, 3, '#161b22', '#30363d', ' id="pd-leB" opacity="0"') +
    txt(414, 112, 'e = 0.55 - 0.70 = -0.15', { size: 7, mono: true, fill: '#8b949e', id: 'pd-le', op: 0 }) +
    rrect(514, 102, 104, 14, 3, '#161b22', '#30363d', ' id="pd-luB" opacity="0"') +
    txt(520, 112, 'u ~= 1.0 * e = -0.15', { size: 7, mono: true, fill: '#8b949e', id: 'pd-lu', op: 0 }) +
    '<path d="M420 142L610 142" stroke="#30363d" stroke-width="2"/>' +
    txt(420, 136, '-0.5', { size: 6.5, mono: true, fill: '#6e7681' }) +
    txt(515, 136, '0', { anchor: 'middle', size: 6.5, mono: true, fill: '#6e7681' }) +
    txt(610, 136, '+0.5', { anchor: 'end', size: 6.5, mono: true, fill: '#6e7681' }) +
    '<path d="M515 142L493 142" stroke="#7ee787" stroke-width="3" id="pd-ln" opacity="0"/>' +
    circ(493, 142, 4, '#7ee787', ' id="pd-lnd" opacity="0"') +
    txt(493, 158, 'u = -0.15 (error view)', { anchor: 'middle', size: 6.5, mono: true, fill: '#8b949e', id: 'pd-lnt', op: 0 }) +
    rrect(408, 166, 210, 18, 9, '#161b22', '#7ee787', ' id="pd-lxB" opacity="0"') +
    txt(513, 178, 'minus sign -&gt; linear.x = +0.15 m/s', { anchor: 'middle', size: 7.5, mono: true, weight: 700, fill: '#7ee787', id: 'pd-lx', op: 0 }) +
    /* ---------- right-top: ANG PID card ---------- */
    rrect(642, 44, 218, 148, 8, '#0d1117', '#e3b341') +
    txt(654, 62, 'ANG PID — SinglePID(2.0, 0.0, 2.0)', { size: 8.5, mono: true, weight: 700, fill: '#e3b341' }) +
    txt(654, 74, 'জন্ম L49-এ, একবারই — ঘুরার নিয়ন্ত্রক', { size: 6.8, fill: '#8b949e' }) +
    rrect(654, 82, 194, 16, 3, '#161b22', '#30363d') +
    txt(660, 93, 'call: pid_compute(+20/72, 0)', { size: 7, mono: true, fill: '#c9d1d9' }) +
    rrect(654, 102, 92, 14, 3, '#161b22', '#30363d', ' id="pd-aeB" opacity="0"') +
    txt(660, 112, 'target = 0.278', { size: 7, mono: true, fill: '#8b949e', id: 'pd-ae', op: 0 }) +
    rrect(752, 102, 96, 14, 3, '#161b22', '#30363d', ' id="pd-auB" opacity="0"') +
    txt(758, 112, 'u ~= 2 * 0.278 = 0.556', { size: 7, mono: true, fill: '#8b949e', id: 'pd-au', op: 0 }) +
    '<path d="M666 142L838 142" stroke="#30363d" stroke-width="2"/>' +
    txt(666, 136, '0', { size: 6.5, mono: true, fill: '#6e7681' }) +
    txt(838, 136, '1.25', { anchor: 'end', size: 6.5, mono: true, fill: '#6e7681' }) +
    '<path d="M666 142L708 142" stroke="#e3b341" stroke-width="3" id="pd-an" opacity="0"/>' +
    circ(708, 142, 4, '#e3b341', ' id="pd-and" opacity="0"') +
    txt(708, 158, 'u = 0.556 (magnitude)', { anchor: 'middle', size: 6.5, mono: true, fill: '#8b949e', id: 'pd-ant', op: 0 }) +
    rrect(654, 166, 194, 18, 9, '#161b22', '#e3b341', ' id="pd-axB" opacity="0"') +
    txt(751, 178, 'ang_pid_compute = 0.556', { anchor: 'middle', size: 7.5, mono: true, weight: 700, fill: '#e3b341', id: 'pd-ax', op: 0 }) +
    /* ---------- right-middle: sign branch ---------- */
    rrect(396, 200, 464, 96, 8, '#111', '#30363d') +
    txt(408, 218, 'SIGN BRANCH — L110-114: direction ফেরাও abs() যা ফেলে দিয়েছিল', { size: 8.5, weight: 700, fill: '#e6edf3' }) +
    rrect(408, 226, 144, 26, 5, '#161b22', '#4fc3f7', ' id="pd-br1" opacity="0"') +
    txt(416, 238, '0 &lt; minDistID  (+20)', { size: 7.5, mono: true, weight: 700, fill: '#4fc3f7' }) +
    txt(416, 249, 'z = +0.556 — বাঁ CCW', { size: 7.5, mono: true, fill: '#4fc3f7' }) +
    rrect(558, 226, 144, 26, 5, '#161b22', '#e3b341', ' id="pd-br2" opacity="0"') +
    txt(566, 238, 'minDistID &lt; 0  (-20)', { size: 7.5, mono: true, weight: 700, fill: '#e3b341' }) +
    txt(566, 249, 'z = -0.556 — ডান CW', { size: 7.5, mono: true, fill: '#e3b341' }) +
    rrect(708, 226, 140, 26, 5, '#161b22', '#30363d', ' id="pd-br3" opacity="0"') +
    txt(716, 238, 'minDistID == 0.0', { size: 7.5, mono: true, weight: 700, fill: '#8b949e' }) +
    txt(716, 249, 'কোনোটাই না — z = 0.0', { size: 7.5, mono: true, fill: '#8b949e' }) +
    txt(408, 272, 'ROS নিয়ম: ধনাত্মক angular.z = CCW = বাঁয়ে ঘোরা — L109-112-এর comment-ই বলছে সেটা', { size: 7, fill: '#8b949e', id: 'pd-bnote', op: 0 }) +
    txt(408, 286, 'দুই branch-এ |z| সমান 0.556 — শুধু চিহ্ন বদলায়, PID একবারই চলে', { size: 7, fill: '#8b949e', id: 'pd-bnote2', op: 0 }) +
    /* ---------- right-bottom: warnings ---------- */
    rrect(396, 304, 464, 56, 8, '#0d1117', '#f85149') +
    txt(408, 322, 'কোনো clamp নেই', { size: 8.5, weight: 700, fill: '#ff7b72' }) +
    txt(408, 336, 'declared linear = 0.5 (L33) পুরো file-এ আর পড়া হয় না — object 2.0 m হলে', { size: 7.5, fill: '#c9d1d9' }) +
    txt(408, 348, 'e = -1.45, linear.x ~= +1.45 m/s (illustrative) — সোজা /cmd_vel-এ', { size: 7.5, fill: '#c9d1d9' }) +
    txt(700, 322, '/72 = magic number', { anchor: 'middle', size: 8.5, weight: 700, fill: '#d2a8ff' }) +
    txt(700, 336, 'file-এর একমাত্র ব্যাখ্যা L106-এর এক লাইন;', { anchor: 'middle', size: 7.5, fill: '#c9d1d9' }) +
    txt(700, 348, 'কার্যকর সর্বোচ্চ target &lt; 45/72 = 0.625', { anchor: 'middle', size: 7.5, fill: '#c9d1d9' }) +
    txt(450, 386, 'রঙ-নিয়ম: সবুজ = linear channel, হলুদ = angular channel, নীল = বাঁ, কমলা = ডান, লাল = no-clamp সতর্কতা', { anchor: 'middle', size: 8, fill: '#8b949e' }) +
    txt(450, 440, 'source: laser_Tracker.py L97-L114 · PIDs L47/L49 · ResponseDist 0.55 L38-39 · RAD2DEG L15', { anchor: 'middle', size: 7.5, mono: true, fill: '#6e7681' })
  );
  const q = id => svg.querySelector('#' + id);
  const show = ids => ids.forEach(i => q(i).setAttribute('opacity', 1));
  host.caption('registerScan-এর হিসাবের হৃদয় — দুটো PID controller, দুটো আলাদা প্রশ্ন। <code>lin_pid</code> (L47) জিজ্ঞেস করে 0.55 m দূরত্ব থেকে আমি কত দূরে, <code>ang_pid</code> (L49) জিজ্ঞেস করে object মুখ থেকে কত বাঁয়ে-ডানে। দুটোই constructor-এ একবার জন্মেছিল — ভেতরের state scan-এ স্ক্যানে বেঁচে থাকে।');
  host.formula('lin_pid = SinglePID(1.0, 0.0, 1.0) @L47  |  ang_pid = SinglePID(2.0, 0.0, 2.0) @L49  [state persists]');
  await host.sleep(1700);
  /* --- beat 1: L102 linear --- */
  show(['pd-hl1', 'pd-wave', 'pd-leB', 'pd-le', 'pd-luB', 'pd-lu', 'pd-ln', 'pd-lnd', 'pd-lnt', 'pd-lxB', 'pd-lx']);
  host.caption('<b>L102</b>: <code>velocity.linear.x = -self.lin_pid.pid_compute(self.ResponseDist, minDist)</code> — call-এর ক্রম (target, current) = (0.55, 0.70)। Error view-এ e = 0.55 - 0.70 = <b>-0.15</b>; Kp-only view-এ pid ফল ~= -0.15 (illustrative — vendor <code>SinglePID</code>-এর ভেতরটা এই folder-এ নেই), আর সামনের <b>minus sign</b> সেটাকে উল্টে দেয়: <code>linear.x = +0.15</code> — object দূরে, তাই এগোনো। Comment (L99-101) ঠিক এই গল্পটাই বলে; দিক-সিদ্ধান্তটা বাইরে থেকে দেখা observable ফল থেকে inferred।');
  host.formula('linear.x = -pid(0.55, 0.70) ~= -(-0.15) = +0.15 m/s   [far -> approach]');
  await host.sleep(2100);
  /* --- beat 2: L107 angular --- */
  show(['pd-hl2', 'pd-aeB', 'pd-ae', 'pd-auB', 'pd-au', 'pd-an', 'pd-and', 'pd-ant', 'pd-axB', 'pd-ax']);
  host.caption('<b>L107</b>: <code>ang_pid_compute = self.ang_pid.pid_compute(abs(minDistID) / 72, 0)</code> — <code>abs()</code> কোণের চিহ্ন ফেলে দেয় (দিক পরের branch-এ ফিরবে), <code>/ 72</code> কোণকে ছোট সংখ্যায় নামায় — file-এর একমাত্র ব্যাখ্যা L106-এর এক লাইন। হিসাব: 20/72 = 0.278 target, current 0, Kp-only view-ে u ~= 2 × 0.278 = <b>0.556</b> (illustrative)।');
  host.formula('ang_pid_compute ~= 2.0 * (abs(+20)/72 - 0) = 2.0 * 0.278 = 0.556');
  await host.sleep(2100);
  /* --- beat 3: L110-111 left --- */
  show(['pd-hl3', 'pd-br1', 'pd-bnote']);
  host.caption('এবার দিক ফেরানো — <b>L110-111</b>: <code>if 0 &lt; minDistID: velocity.angular.z = ang_pid_compute</code>। Wave B-তে minDistID = +20 (বাঁয়ে), তাই <code>angular.z = +0.556</code> — ROS-এ ধনাত্মক angular.z মানে CCW মানে বাঁয়ে ঘোরা। Object যেদিকে, মুখ সেদিকে।');
  host.formula('0 < minDistID (+20)  ->  angular.z = +u = +0.556  (CCW, left)');
  await host.sleep(1900);
  /* --- beat 4: L113-114 right --- */
  show(['pd-hl4', 'pd-br2', 'pd-bnote2']);
  host.caption('আয়নার শাখা — <b>L113-114</b>: <code>elif minDistID &lt; 0: velocity.angular.z = -ang_pid_compute</code>। Object ডানে হলে (যেমন -20°) একই 0.556 magnitude, চিহ্ন উল্টো: <code>angular.z = -0.556</code> — ডানে ঘোরা (CW)। PID একবারই চলে; শাখা শুধু চিহ্ন বসায়।');
  host.formula('minDistID < 0 (-20)  ->  angular.z = -u = -0.556  (CW, right)');
  await host.sleep(1900);
  /* --- beat 5: exactly zero --- */
  show(['pd-br3', 'pd-zero']);
  host.caption('আর তৃতীয় কোণা: minDistID ঠিক <b>0.0</b> হলে — object হুবহু সামনে — কোনো branch-ই মেলে না (<code>0 &lt; 0</code> মিথ্যা, <code>0 &lt; 0</code> মিথ্যা)। <code>angular.z</code>-এ কেউ হাত দেয় না, L90-এর <code>Twist()</code>-এর জন্মলগ্ন মান <b>0.0</b>-ই থেকে যায় — সোজা তাকানো, ঘোরার দরকার নেই।');
  host.formula('minDistID == 0.0  ->  neither branch  ->  angular.z stays 0.0');
  await host.sleep(1900);
  /* --- close --- */
  host.caption('এই মুহূর্তে Twist-এর দুই ঘর বসে গেছে (illustrative): <code>linear.x = +0.15</code> আর <code>angular.z = +0.556</code> — এগোও আর বাঁয়ে ঘুরো। কিন্তু খেয়াল করো: কোথাও কোনো clamp নেই, declared <code>linear = 0.5</code> (L33) পুরো file-এ পড়াই হয় না — দূরের object মানে বিশাল error, বিশাল command। পরের part-এ দুটো শান্ত-করার নিয়ম: turn deadzone আর ×0.6 damping।');
  host.formula('Twist so far (Wave B): (+0.15, +0.556)  |  no clamp: e.g. d=2.0 -> linear.x ~= +1.45 m/s');
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

/* ===== folder-12 v1 anim — cmdVelVectors (part 14) ===================
   laser_Tracker.py L115-L125: turn deadzone (|ang_pid_compute| < 0.5
   -> angular.z = 0.0), x0.6 damping (whip-around comment L119), print
   L122, publish L125. Scenarios (illustrative, Kp-only): Wave B
   +20 deg / 0.70 m -> u = 0.556 >= 0.5 pass -> x0.6 -> +0.333 rad/s
   CCW with linear.x +0.15; Wave A +12 deg / 0.90 m -> u = 0.333 <
   0.5 -> z = 0.0, straight only (|angle| < 18 deg equivalent); Wave C
   dead ahead 0.55 m -> L96 snap -> both zero, locked stand-off.
   Ceiling 2*0.625*0.6 = 0.75 rad/s; declared angular 1.0 (L35) never
   enforced. Motors keep the last command (no publish on the empty
   L80-83 and Joy L86-88 paths). Prefix cv-. No emoji, no arrow chars
   in stage strings, entities for &lt; &gt;. */

ANIMS.cmdVelVectors = async function (host) {
  const svg = host.setStage(
    txt(450, 24, 'deadzone যাচাই, ×0.6 damping, তারপর publish — চূড়ান্ত Twist-এর জন্ম, L116-L125', { anchor: 'middle', size: 13.5, weight: 600, fill: '#ffb454' }) +
    /* ---------- left: top view ---------- */
    rrect(40, 42, 268, 300, 8, '#0d1117', '#2a3442') +
    txt(174, 60, 'TOP VIEW — robot আর object', { anchor: 'middle', size: 9.5, weight: 700, fill: '#e6edf3' }) +
    cvWedge(174, 210, 96, -45, 45, 'cv-cone') +
    txt(174, 106, 'cone ±45° (L36)', { anchor: 'middle', size: 7, mono: true, fill: '#8b949e' }) +
    cvWedge(174, 210, 96, -18, 18, 'cv-dz') +
    txt(174, 300, 'deadzone-এর নীরবতা &lt; ±18° (Kp-only, illustrative)', { anchor: 'middle', size: 7, fill: '#6e7681', id: 'cv-dzt', op: 0 }) +
    circ(174, 210, 4, '#ff7b72', ' id="cv-obj" opacity="0"') +
    txt(174, 322, 'Wave B: +20° · 0.70 m', { anchor: 'middle', size: 8.5, weight: 700, mono: true, fill: '#e3b341', id: 'cv-scen' }) +
    rrect(162, 186, 24, 48, 5, '#21262d', '#8b949e') +
    '<path d="M174 176 L180 188 L168 188 Z" fill="#4fc3f7"/>' +
    txt(174, 250, 'robot', { anchor: 'middle', size: 7, fill: '#8b949e' }) +
    '<path d="M174 172L174 148" stroke="#7ee787" stroke-width="2.4" fill="none" id="cv-fwd" opacity="0"/>' +
    '<path d="M174 148 L179 158 L169 158 Z" fill="#7ee787" id="cv-fwdh" opacity="0"/>' +
    txt(182, 154, 'linear.x', { size: 6.5, fill: '#7ee787', id: 'cv-fwdt', op: 0 }) +
    cvArcArrow(174, 210, 34, -40, 130, 'cv-tccw', 'cv-tccwh', '#4fc3f7', 2.2) +
    txt(174, 266, 'angular.z CCW', { anchor: 'middle', size: 6.5, fill: '#4fc3f7', id: 'cv-tccwt', op: 0 }) +
    /* ---------- middle: vector dial ---------- */
    rrect(318, 42, 172, 300, 8, '#0d1117', '#30363d') +
    txt(404, 60, 'VECTOR DIAL', { anchor: 'middle', size: 9.5, weight: 700, fill: '#e6edf3' }) +
    txt(404, 78, 'linear.x — সোজা তীর (m/s)', { anchor: 'middle', size: 7.5, weight: 700, fill: '#c9d1d9' }) +
    '<path d="M404 96 L404 152" stroke="#6e7681" stroke-width="1.5" fill="none"/>' +
    '<path d="M404 86 L409 96 L399 96 Z" fill="#8b949e"/>' +
    '<path d="M404 162 L409 152 L399 152 Z" fill="#8b949e"/>' +
    txt(412, 97, '+ সামনে', { size: 7, fill: '#7ee787' }) +
    txt(412, 153, '- পেছনে', { size: 7, fill: '#ff7b72' }) +
    '<path d="M404 148 L404 112" stroke="#7ee787" stroke-width="2.4" opacity="0.14" fill="none"/>' +
    rrect(344, 168, 120, 18, 9, '#161b22', '#30363d', ' id="cv-linp"') +
    txt(404, 180.5, 'linear.x = +0.15', { anchor: 'middle', size: 8, mono: true, fill: '#e6edf3', id: 'cv-linv' }) +
    txt(404, 202, 'angular.z — বাঁকা তীর (rad/s)', { anchor: 'middle', size: 7.5, weight: 700, fill: '#c9d1d9' }) +
    circ(404, 244, 26, 'none', ' stroke="#30363d" stroke-width="1.5"') +
    cvArcArrow(404, 244, 26, -35, 175, 'cv-acw', 'cv-acwh', '#4fc3f7', 2.4) +
    cvArcArrow(404, 244, 26, 35, -175, 'cv-aw', 'cv-awh', '#e3b341', 2.4) +
    txt(357, 247, 'CCW +', { anchor: 'end', size: 7, weight: 700, fill: '#4fc3f7' }) +
    txt(451, 247, 'CW -', { size: 7, weight: 700, fill: '#e3b341' }) +
    rrect(339, 282, 130, 20, 10, '#161b22', '#30363d', ' id="cv-angp"') +
    txt(404, 295.5, 'angular.z = +0.556', { anchor: 'middle', size: 8, weight: 700, mono: true, fill: '#e6edf3', id: 'cv-angv' }) +
    txt(404, 320, 'PID-এর ফল এখনো কাঁচা — damping বাকি', { anchor: 'middle', size: 6.5, fill: '#6e7681', id: 'cv-angnote', op: 0 }) +
    txt(404, 332, 'ROS নিয়ম: CCW = ধনাত্মক = বাঁয়ে ঘোরা', { anchor: 'middle', size: 6.5, fill: '#8b949e' }) +
    /* ---------- right: pipeline ---------- */
    rrect(500, 42, 360, 300, 8, '#0d1117', '#2a3442') +
    txt(680, 60, 'PIPELINE — L116-L125', { anchor: 'middle', size: 9.5, weight: 700, fill: '#e6edf3' }) +
    rrect(510, 68, 340, 15, 3, '#21262d', 'none', ' id="cv-hl1" opacity="0"') +
    txt(518, 79, 'if abs(ang_pid_compute) &lt; 0.5: velocity.angular.z = 0.0', { size: 7.5, mono: true, fill: '#8b949e' }) +
    txt(848, 79, 'L117', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    rrect(510, 84, 340, 15, 3, '#21262d', 'none', ' id="cv-hl2" opacity="0"') +
    txt(518, 95, 'velocity.angular.z = velocity.angular.z * 0.6', { size: 7.5, mono: true, fill: '#8b949e' }) +
    txt(848, 95, 'L120', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    rrect(510, 100, 340, 15, 3, '#21262d', 'none', ' id="cv-hl3" opacity="0"') +
    txt(518, 111, 'print("angular.z: ", velocity.angular.z)', { size: 7.5, mono: true, fill: '#8b949e' }) +
    txt(848, 111, 'L122', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    rrect(510, 116, 340, 15, 3, '#21262d', 'none', ' id="cv-hl4" opacity="0"') +
    txt(518, 127, 'self.pub_vel.publish(velocity)', { size: 7.5, mono: true, fill: '#8b949e' }) +
    txt(848, 127, 'L125', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    rrect(510, 142, 164, 40, 6, '#161b22', '#4fc3f7', ' id="cv-ch1" opacity="0"') +
    txt(592, 155, '1) DEADZONE |u| &lt; 0.5?', { anchor: 'middle', size: 7.5, weight: 700, fill: '#4fc3f7' }) +
    txt(592, 172, 'Wave B: 0.556 - পাস', { anchor: 'middle', size: 7.5, mono: true, fill: '#e6edf3', id: 'cv-ch1t' }) +
    rrect(686, 142, 164, 40, 6, '#161b22', '#e3b341', ' id="cv-ch2" opacity="0"') +
    txt(768, 155, '2) DAMPING ×0.6', { anchor: 'middle', size: 7.5, weight: 700, fill: '#e3b341' }) +
    txt(768, 172, '+0.556 -&gt; +0.333', { anchor: 'middle', size: 7.5, mono: true, fill: '#e6edf3', id: 'cv-ch2t' }) +
    rrect(510, 190, 340, 40, 6, '#161b22', '#7ee787', ' id="cv-ch3" opacity="0"') +
    txt(680, 203, '3) PUBLISH L125 — pub_vel.publish(velocity)', { anchor: 'middle', size: 7.5, weight: 700, fill: '#7ee787' }) +
    txt(680, 220, '/cmd_vel: (+0.15, +0.333) — চাকা পরের scan পর্যন্ত এটাই ধরে রাখে', { anchor: 'middle', size: 7.5, mono: true, fill: '#e6edf3', id: 'cv-ch3t' }) +
    txt(510, 248, 'ceiling (illustrative): cone-এর কিনারায় |a| প্রায় 45° হলে', { size: 7, fill: '#8b949e', id: 'cv-cnote', op: 0 }) +
    txt(510, 261, 'u প্রায় 1.25, ×0.6 করলে 0.75 rad/s — declared angular 1.0 (L35) কোথাও enforce হয় না', { size: 7, fill: '#8b949e', id: 'cv-cnote2', op: 0 }) +
    txt(510, 284, 'L116/L119-এর comment: সামান্য বাঁক চুপ, whip around ঠেকাও', { size: 7, fill: '#6e7681', id: 'cv-cnote3', op: 0 }) +
    txt(510, 297, 'সব সংখ্যা Kp-only illustrative — vendor SinglePID এই folder-এ নেই', { size: 7, fill: '#6e7681', id: 'cv-cnote4', op: 0 }) +
    txt(510, 326, '0.5 · 0.6 — দুটোই hard-coded, parameter নয়', { size: 7, fill: '#d2a8ff', id: 'cv-cnote5', op: 0 }) +
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
    rrect(420, 398, 130, 16, 3, '#3d1d20', '#f85149', ' fill-opacity="0.35" stroke-dasharray="4 3" id="cv-none" opacity="0"') +
    txt(485, 426, 'সামনে খালি (L80-83) — publish নেই', { anchor: 'middle', size: 7, fill: '#ff7b72', id: 'cv-nonet', op: 0 }) +
    circ(610, 406, 5, '#d2a8ff', ' id="cv-joy" opacity="0"') +
    txt(610, 394, '/JoyState True', { anchor: 'middle', size: 7, mono: true, fill: '#d2a8ff', id: 'cv-joyt', op: 0 }) +
    circ(700, 406, 5, '#7ee787', ' id="cv-zp" opacity="0"') +
    txt(700, 394, 'শূন্য Twist', { anchor: 'middle', size: 7, mono: true, fill: '#7ee787', id: 'cv-zpt', op: 0 }) +
    txt(830, 426, 'publish না এলে চাকা শেষ কমান্ডেই চলে', { anchor: 'end', size: 7, fill: '#8b949e', id: 'cv-lastt', op: 0 }) +
    txt(450, 450, 'source: laser_Tracker.py L115-L125 · linear PID L102 · angular PID L107 · snap L96 · Joy gate L86-88', { anchor: 'middle', size: 7.5, mono: true, fill: '#6e7681' })
  );
  const q = id => svg.querySelector('#' + id);
  const show = ids => ids.forEach(i => q(i).setAttribute('opacity', 1));
  const hide = ids => ids.forEach(i => q(i).setAttribute('opacity', 0));
  const cvObj = (deg, dist) => {
    const p = cvPt(174, 210, 96 * dist, deg);
    q('cv-obj').setAttribute('cx', p[0]); q('cv-obj').setAttribute('cy', p[1]);
  };

  show(['cv-angnote']);
  host.caption('Part 13-এর শেষে Twist-এর দুই ঘর বসেছিল (illustrative): <code>linear.x = +0.15</code>, <code>angular.z = +0.556</code>। এই Part-এর তিনটা নিয়ম সেই কাঁচা মানটাকে বাজারে পাঠানোর আগে গুছিয়ে নেয় — deadzone যাচাই, ×0.6 damping, তারপর publish। ROS-এ ধনাত্মক <code>angular.z</code> = বাঁয়ে ঘোরা (CCW)।');
  host.formula('final angular.z = (|u| >= 0.5 ? u_signed : 0.0) * 0.6   |   publish linear.x + angular.z at L125');
  cvObj(20, 0.70);
  show(['cv-obj']);
  await host.sleep(1700);
  /* --- beat 1: deadzone pass Wave B --- */
  show(['cv-hl1', 'cv-ch1']);
  host.caption('<b>Wave B (ধরে নিই): object +20°-এ, 0.70 m।</b> <b>L117</b>: <code>abs(ang_pid_compute) &lt; 0.5</code>? হিসাব: 0.556 — 0.5-এর বেশি, তাই deadzone <b>পাস</b>; <code>angular.z</code> কাটা পড়ে না, 0.556-ই থাকে। (সব pid ফল Kp-only illustrative — vendor <code>SinglePID</code> এই folder-এ নেই।)');
  host.formula('Wave B: |0.556| >= 0.5  ->  keep u  (deadzone pass)');
  await host.sleep(1800);
  /* --- beat 2: damping Wave B --- */
  show(['cv-hl2', 'cv-ch2']);
  q('cv-angv').textContent = 'angular.z = +0.333';
  q('cv-angp').setAttribute('stroke', '#4fc3f7');
  q('cv-linp').setAttribute('stroke', '#4fc3f7');
  show(['cv-acw', 'cv-acwh', 'cv-tccw', 'cv-tccwh', 'cv-tccwt', 'cv-fwd', 'cv-fwdh', 'cv-fwdt']);
  host.caption('<b>L120</b>: <code>velocity.angular.z = velocity.angular.z * 0.6</code> — সর্বজনীন 60% স্কেল, comment (L119) বলে robot যেন <i>whip around</i> না করে। 0.556 × 0.6 = <b>+0.333 rad/s</b>। Dial-এ এখন চূড়ান্ত ছবি: সামনে তীর (+0.15 m/s) + বাঁয়ে বাঁক (+0.333) — object-এর দিকে বেঁকে এগোনো।');
  host.formula('Wave B final: angular.z = 0.556 * 0.6 = +0.333 rad/s  |  linear.x = +0.15 m/s');
  await host.sleep(2000);
  /* --- beat 3: publish Wave B --- */
  show(['cv-hl3', 'cv-hl4', 'cv-ch3']);
  host.caption('<b>L122</b> console-এ চূড়ান্ত মান ছাপে, <b>L125</b> <code>self.pub_vel.publish(velocity)</code> — একটাই <code>Twist</code>, <code>/cmd_vel</code>-এ (L29-এর publisher)। এই মুহূর্ত থেকে পরের scan না আসা পর্যন্ত চাকা এই কমান্ডই মানবে।');
  host.formula('publish (linear.x = +0.15, angular.z = +0.333) -> /cmd_vel -> wheels hold it until next scan');
  await host.sleep(2000);
  /* --- beat 4: Wave A deadzone kill --- */
  q('cv-scen').textContent = 'Wave A: +12° · 0.90 m';
  q('cv-ch1t').textContent = 'Wave A: 0.333 - কাটা পড়ল';
  q('cv-ch1').setAttribute('stroke', '#f85149');
  q('cv-ch2t').textContent = '0.0 × 0.6 = 0.0';
  q('cv-angv').textContent = 'angular.z = 0.0';
  q('cv-linv').textContent = 'linear.x = +0.35';
  cvObj(12, 0.90);
  hide(['cv-acw', 'cv-acwh', 'cv-tccw', 'cv-tccwh', 'cv-tccwt']);
  show(['cv-dzt']);
  q('cv-ch3t').textContent = '/cmd_vel: (+0.35, 0.0) — সোজা এগোও, ঘুরো না';
  host.caption('এবার <b>Wave A</b>: object +12°-এ, 0.90 m। angular PID দিয়েছে 2 × 12/72 = <b>0.333</b> — সেটা 0.5-এর কাছে পৌঁছায়নি, তাই <b>L117-এর deadzone কাটা দেয়</b>: <code>angular.z = 0.0</code>। Kp-only view-এ এই সীমা কার্যত <b>|angle| &lt; 18°</b> (2·a/72 &lt; 0.5; illustrative) — ওই নীরব পাল্লার ভেতরে robot ঘুরবেই না, শুধু সোজা এগোবে (+0.35 m/s; দূরত্ব বেশি, তাই গতিও বেশি — clamp নেই)।');
  host.formula('Wave A: u = 2*12/72 = 0.333 < 0.5  ->  angular.z = 0.0 ; linear.x = -1*(0.55-0.90) = +0.35');
  await host.sleep(2300);
  /* --- beat 5: ceiling --- */
  show(['cv-cnote', 'cv-cnote2', 'cv-cnote3', 'cv-cnote4', 'cv-cnote5']);
  host.caption('দুই ধাপের সীমাহিসাব: damping না থাকলে cone-এর কিনারায় (|angle| প্রায় 45°) কাঁচা u প্রায় <b>1.25 rad/s</b>-এ উঠত — ×0.6 করে বাস্তব ceiling <b>0.75 rad/s</b> (illustrative)। খেয়াল করো: declared <code>angular</code> parameter 1.0 (L35) কোথাও enforce হয় না — সীমা দুটো এসেছে deadzone (0.5) আর damping (0.6) থেকে, দুটোই hard-coded সংখ্যা।');
  host.formula('ceiling: u_max ~= 2 * (45/72) = 1.25 ; 1.25 * 0.6 = 0.75 rad/s  |  declared angular = 1.0 unused');
  await host.sleep(2200);
  /* --- beat 6: Wave C locked --- */
  q('cv-scen').textContent = 'Wave C: 0° · 0.55 m — stand-off';
  q('cv-ch1t').textContent = 'Wave C: 0.0 - নির্বিঘ্ন';
  q('cv-ch1').setAttribute('stroke', '#4fc3f7');
  q('cv-ch2t').textContent = '0.0 × 0.6 = 0.0';
  q('cv-angv').textContent = 'angular.z = 0.0';
  q('cv-linv').textContent = 'linear.x = 0.0';
  cvObj(0, 0.55);
  q('cv-ch3t').textContent = '/cmd_vel: (0.0, 0.0) — দাঁড়িয়ে থাকা stand-off';
  host.caption('<b>Wave C</b>: object হুবহু সামনে, 0.55 m। L96-এর snap (Part 12) minDist-কে 0.55-ই ধরেছে — linear PID-এর error শূন্য, <code>linear.x = 0.0</code>; কোণ 0 বলে sign branch-ও না (Part 13), তাই <code>angular.z = 0.0</code>। Publish হয় <b>(0.0, 0.0)</b> — robot জায়গায় দাঁড়িয়ে object-কে 0.55 m দূরত্বে আটকে রাখে: এটাই tracking-এর stand-off।');
  host.formula('Wave C: snap -> e = 0 -> linear.x = 0 ; angle = 0 -> no branch -> angular.z = 0  -> (0.0, 0.0)');
  await host.sleep(2300);
  /* --- beat 7: cadence --- */
  show(['cv-p1', 'cv-p1t', 'cv-s2', 'cv-s2t', 'cv-p2', 'cv-p2t', 'cv-none', 'cv-nonet', 'cv-joy', 'cv-joyt', 'cv-zp', 'cv-zpt', 'cv-lastt']);
  host.caption('ছন্দটা মনে রাখো: <b>প্রতি scan-এ এক publish</b> — compute শেষ হলেই L125 চলে (timeline illustrative)। সামনে কিছু না থাকলে L80-83-এর <code>return</code>-এ publish-ই হয় না — চাকা তখন <b>শেষ কমান্ডেই</b> চলতে থাকে; আর <code>/JoyState</code> True হলে L86-88 প্রতি scan-এ শূন্য <code>Twist()</code> ঠেলে দেয় — মানুষের brake।');
  host.formula('scan -> compute -> publish  |  empty front (L80-83): no publish, last command persists  |  Joy (L86-88): zero Twist');
  await host.sleep(2200);
  host.caption('তিনটা Wave-এর মোদ্দা কথা: 18°-র বেশি বাঁকে ঘুরে সামনে এগোয় (B), সামান্য বাঁক উপেক্ষা করে সোজা ছোটে (A), আর 0.55 m-এ গিয়ে থামে (C) — damping সব ঘোরাকে মার্জিত রাখে। এরপর আর কোনো হিসাব নেই: শুধু বন্ধ হওয়ার পালা — <code>exit_pro</code> আর <code>main()</code>, শেষ Part-এর গল্প।');
  await host.sleep(1800);
};
/* ---------- safetyHalt ---------- */
/* ============ folder-12 anim: safetyHalt (part 15) ==================
   laser_Tracker.py L135-146 (main + try/except/finally), with L128-133
   exit_pro and L14 print as grounding. Source sha d414af8d12da.
   Facts: L136 rclpy.init(); L137 laserTracker("laser_Tracker_a1");
   L138 print ("start it"); L140 rclpy.spin(laser_tracker); L141-142
   except KeyboardInterrupt: pass; L143 finally: L144 exit_pro(),
   L145 destroy_node(), L146 rclpy.shutdown(). L14 print("improt done")
   (typo in source) fires at import time - two prints, two different
   times. exit_pro: cmd1 (L130) + cmd2 (L131 zero-yaml) joined L132,
   os.system(cmd) L133 = a shell outside the node = process-level
   brake. The file never calls main() and has no __main__ guard -
   ros2 run reaches it via the package setup.py console_scripts entry
   (not in this folder; inferred). README L5: ros2 run
   yahboom_M3Pro_laser laser_Tracker.
   Id prefix sh-; no emoji, no Unicode arrows in stage strings; static
   backbone visible at setStage; first caption + formula before the
   first await. */


function shCodeLine(n, ind, s, id) {
  const y = 84 + (n - 135) * 20;
  return txt(66, y, String(n), { anchor: 'end', size: 7.5, mono: true, fill: '#6e7681' }) +
         txt(74 + ind * 13, y, s, { size: 8.5, mono: true, fill: '#8b949e', id: id });
}

ANIMS.safetyHalt = async function (host) {
  const svg = host.setStage(
    txt(450, 26, 'main(): জন্ম, ঘূর্ণন, নীরব থামা আর finally-র নিরাপদ ব্রেক', { anchor: 'middle', size: 14, weight: 600, fill: '#ffb454' }) +
    rrect(40, 44, 372, 316, 8, '#0d1117', '#2a3442') +
    txt(56, 64, 'CODE — laser_Tracker.py L135-146', { size: 10, weight: 700, fill: '#e6edf3' }) +
    rrect(50, 73, 352, 76, 4, '#7ee787', 'none', ' id="sh-h1" fill-opacity="0.10" opacity="0"') +
    rrect(50, 153, 352, 36, 4, '#4fc3f7', 'none', ' id="sh-h2" fill-opacity="0.10" opacity="0"') +
    rrect(50, 193, 352, 36, 4, '#ff7b72', 'none', ' id="sh-h3" fill-opacity="0.12" opacity="0"') +
    rrect(50, 233, 352, 36, 4, '#e3b341', 'none', ' id="sh-h4" fill-opacity="0.12" opacity="0"') +
    rrect(50, 273, 352, 36, 4, '#7ee787', 'none', ' id="sh-h5" fill-opacity="0.10" opacity="0"') +
    shCodeLine(135, 0, 'def main():', 'sh-c135') +
    shCodeLine(136, 1, 'rclpy.init()', 'sh-c136') +
    shCodeLine(137, 1, 'laser_tracker = laserTracker("laser_Tracker_a1")', 'sh-c137') +
    shCodeLine(138, 1, 'print ("start it")', 'sh-c138') +
    shCodeLine(139, 1, 'try:', 'sh-c139') +
    shCodeLine(140, 2, 'rclpy.spin(laser_tracker)', 'sh-c140') +
    shCodeLine(141, 1, 'except KeyboardInterrupt:', 'sh-c141') +
    shCodeLine(142, 2, 'pass', 'sh-c142') +
    shCodeLine(143, 1, 'finally:', 'sh-c143') +
    shCodeLine(144, 2, 'laser_tracker.exit_pro()', 'sh-c144') +
    shCodeLine(145, 2, 'laser_tracker.destroy_node()', 'sh-c145') +
    shCodeLine(146, 1, 'rclpy.shutdown()', 'sh-c146') +
    txt(56, 326, 'L144-এর exit_pro() = L128-133 — ডানের SHELL কার্ড', { size: 7.5, fill: '#6e7681' }) +
    txt(56, 342, 'README L5: ros2 run yahboom_M3Pro_laser laser_Tracker', { size: 7.5, mono: true, fill: '#6e7681' }) +
    rrect(428, 44, 432, 316, 8, '#111', '#30363d') +
    txt(644, 64, 'RUNTIME — জীবনচক্র (illustrative)', { anchor: 'middle', size: 10, weight: 700, fill: '#e6edf3' }) +
    txt(702, 84, 'TERMINAL', { size: 8, weight: 700, fill: '#6e7681' }) +
    rrect(702, 90, 142, 58, 5, '#0d1117', '#30363d') +
    txt(712, 108, 'improt done', { size: 8, mono: true, fill: '#8b949e', id: 'sh-pol1', op: 0 }) +
    txt(712, 128, 'start it', { size: 8.5, mono: true, weight: 700, fill: '#7ee787', id: 'sh-pol2', op: 0 }) +
    txt(702, 160, 'দুই print, দুই সময়', { size: 7.5, fill: '#6e7681', id: 'sh-pon1', op: 0 }) +
    txt(702, 172, '(L14) আর (L138)', { size: 7.5, fill: '#6e7681', id: 'sh-pon2', op: 0 }) +
    txt(444, 84, 'rclpy.init() (L136) — library চালু', { size: 8.5, mono: true, fill: '#7ee787', id: 'sh-r1', op: 0 }) +
    rrect(444, 92, 250, 62, 6, '#161b22', '#7ee787', ' id="sh-node" opacity="0"') +
    txt(456, 110, 'laserTracker — node জন্ম', { size: 9.5, weight: 700, fill: '#e6edf3', id: 'sh-nt1', op: 0 }) +
    txt(456, 124, 'name: "laser_Tracker_a1" (L137)', { size: 8, mono: true, fill: '#d2a8ff', id: 'sh-nt2', op: 0 }) +
    txt(456, 138, 'sub /scan, /JoyState + pub /cmd_vel', { size: 7.5, mono: true, fill: '#8b949e', id: 'sh-nt3', op: 0 }) +
    txt(444, 174, 'rclpy.spin(laser_tracker) (L140) — event loop', { size: 8.5, mono: true, fill: '#4fc3f7', id: 'sh-r2', op: 0 }) +
    rrect(444, 182, 250, 30, 5, '#161b22', '#30363d', ' id="sh-loop" opacity="0"') +
    circ(468, 197, 5, '#0d1117', ' id="sh-s1" stroke="#4fc3f7" stroke-width="1" opacity="0"') +
    circ(508, 197, 5, '#0d1117', ' id="sh-s2" stroke="#4fc3f7" stroke-width="1" opacity="0"') +
    circ(549, 197, 5, '#0d1117', ' id="sh-s3" stroke="#4fc3f7" stroke-width="1" opacity="0"') +
    circ(589, 197, 5, '#0d1117', ' id="sh-s4" stroke="#4fc3f7" stroke-width="1" opacity="0"') +
    circ(630, 197, 5, '#0d1117', ' id="sh-s5" stroke="#4fc3f7" stroke-width="1" opacity="0"') +
    circ(670, 197, 5, '#0d1117', ' id="sh-s6" stroke="#4fc3f7" stroke-width="1" opacity="0"') +
    circ(468, 197, 8, 'none', ' id="sh-cur" stroke="#4fc3f7" stroke-width="2" opacity="0"') +
    txt(702, 190, 'tick 1: /scan', { size: 8, mono: true, fill: '#4fc3f7', id: 'sh-ls', op: 0 }) +
    txt(702, 204, 'এলে registerScan (L56)', { size: 7.5, fill: '#8b949e', id: 'sh-ls2', op: 0 }) +
    rrect(444, 218, 64, 22, 5, '#161b22', '#ff7b72', ' id="sh-ctrl" opacity="0"') +
    txt(476, 233, 'Ctrl+C', { anchor: 'middle', size: 8.5, weight: 700, fill: '#ff7b72', id: 'sh-ctrlt', op: 0 }) +
    txt(516, 233, 'KeyboardInterrupt (L141) — except: pass (L142)', { size: 7.5, fill: '#8b949e', id: 'sh-ctrnote', op: 0 }) +
    rrect(444, 248, 400, 52, 6, '#0d1117', '#e3b341', ' id="sh-shell" opacity="0"') +
    txt(454, 262, 'SHELL — os.system(cmd) (L133)', { size: 8, weight: 700, fill: '#e3b341', id: 'sh-sht', op: 0 }) +
    txt(454, 278, '$ ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist', { size: 8, mono: true, fill: '#7ee787', id: 'sh-sc1', op: 0 }) +
    txt(454, 292, '"{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"', { size: 7.5, mono: true, fill: '#7ee787', id: 'sh-sc2', op: 0 }) +
    txt(444, 312, 'shell = node-এর বাইরের process — teardown চলাকালেও ব্রেক কাজ করে', { size: 8, fill: '#e3b341', id: 'sh-shn', op: 0 }) +
    txt(444, 324, 'ফল: চাকায় zero Twist (L131) — শেষ velocity মুছে গেল', { size: 8, fill: '#7ee787', id: 'sh-wz', op: 0 }) +
    txt(444, 338, 'destroy_node() (L145): নাম আর subscription ছাড়া', { size: 8, fill: '#8b949e', id: 'sh-r5a', op: 0 }) +
    txt(444, 350, 'rclpy.shutdown() (L146): library বন্ধ — নিরাপদ প্রস্থান', { size: 8, weight: 700, fill: '#7ee787', id: 'sh-r5b', op: 0 }) +
    txt(450, 386, 'রঙ-নিয়ম: সবুজ = জন্ম ও প্রস্থান, নীল = spin loop, লাল = Ctrl+C, হলুদ = shell ব্রেক, বেগুনি = নাম', { anchor: 'middle', size: 8.5, fill: '#8b949e' }) +
    txt(450, 440, 'source: laser_Tracker.py L135-146 + L128-133 + L14 - README L5', { anchor: 'middle', size: 8, mono: true, fill: '#6e7681' })
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

  host.caption('এই anim-এ <code>main()</code>-এর পুরো জীবনকাল — L135 থেকে L146। বাঁয়ে কোড, ডানে তার runtime ছবি। শুরুতেই একটা কথা: file-টা <b>import</b>-হওয়ার মুহূর্তেই একটা print বেরিয়ে গেছে (L14), আর README L5-এর <code>ros2 run yahboom_M3Pro_laser laser_Tracker</code> ডাক দেয় এই <code>main()</code>-কে।');
  host.formula('life = import (L14) -> main (L135) -> rclpy.init (L136) -> spin (L140) -> finally (L143-146)');
  await host.sleep(1500);

  show('sh-pol1'); show('sh-pon1'); show('sh-pon2');
  host.caption('টার্মিনালের প্রথম লাইনটা তাই আগেই এসে গেছে: <code>improt done</code> (L14) — বানানটা source-এ এমনই, <b>import</b> শব্দের typo। মানে দুটি print দুই <b>আলাদা সময়ে</b>: L14 import-এর সময়, L138 পরে main()-এর ভেতরে।');
  await host.sleep(1500);

  show('sh-h1'); shGlow(['sh-c135', 'sh-c136', 'sh-c137', 'sh-c138'], '#e6edf3');
  show('sh-r1'); show('sh-node'); show('sh-nt1'); show('sh-nt2'); show('sh-nt3'); show('sh-pol2');
  host.caption('<code>main()</code> শুরু (L135)। <code>rclpy.init()</code> (L136) — rclpy library চালু। তারপর <code>laserTracker("laser_Tracker_a1")</code> (L137): constructor সাবস্ক্রিপশন আর publisher সব সেট করে node জন্মায় (আগের part-এর গল্প)। সঙ্গে দ্বিতীয় print: <b>start it</b> (L138)।');
  await host.sleep(1700);

  show('sh-h2'); shGlow(['sh-c139', 'sh-c140'], '#4fc3f7');
  show('sh-r2'); show('sh-loop'); shSlotIds.forEach(show); show('sh-cur'); show('sh-ls'); show('sh-ls2'); shTick(1);
  host.caption('<code>rclpy.spin(laser_tracker)</code> (L140) — এই হলো event loop। <code>/scan</code> এলে <code>registerScan</code> (L56) ছোটে, <code>/JoyState</code> এলে <code>JoyStateCallback</code> (L52)। নীল রিং ঘুরছে = callback একের পর এক (illustrative)।');
  host.formula('spin = wait + dispatch: /scan -> registerScan (L56), /JoyState -> JoyStateCallback (L52)');
  await host.sleep(700);
  shTick(2); await host.sleep(420);
  shTick(3); await host.sleep(420);
  shTick(4); await host.sleep(420);
  shTick(5); await host.sleep(420);
  shTick(6); await host.sleep(420);
  shTick(7); await host.sleep(500);
  host.caption('প্রতি tick-এই সিদ্ধান্তের গাছ চলে — এগোবে, ঘুরবে না পিছাবে (আগের part-গুলোর গল্প)। <code>spin</code> নিজে থেমে না; Ctrl+C ছাড়া এই ঘূর্ণন চলতেই থাকত।');
  await host.sleep(1500);

  show('sh-h3'); shGlow(['sh-c141', 'sh-c142'], '#ff7b72');
  show('sh-ctrl'); show('sh-ctrlt'); show('sh-ctrnote');
  hide('sh-cur');
  shSlotIds.forEach(sid => { q(sid).setAttribute('fill', '#0d1117'); q(sid).setAttribute('stroke', '#6e7681'); });
  q('sh-loop').setAttribute('stroke', '#30363d');
  q('sh-ls').textContent = 'loop থেমে গেল';
  host.caption('Ctrl+C চাপলে <code>KeyboardInterrupt</code> ওঠে (L141) — except block শুধু <code>pass</code> (L142), একটা শব্দও না। কিন্তু Python-এর কঠিন নিয়ম: <b>finally সব পথেই চলে</b> — exception হোক বা না হোক।');
  host.formula('Ctrl+C -> KeyboardInterrupt -> except: pass (L142) -> finally STILL runs (L143)');
  await host.sleep(1600);

  show('sh-h4'); shGlow(['sh-c143', 'sh-c144'], '#e3b341');
  show('sh-shell'); show('sh-sht'); show('sh-sc1'); show('sh-sc2');
  host.caption('<code>finally</code> (L143)-এর প্রথম কাজ <code>exit_pro()</code> (L144)। ভেতরে (L128-133): <code>cmd1</code> (L130) + <code>cmd2</code> (L131) জোড়া লেগে (L132) একটাই লাইন — <code>ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist</code>, সঙ্গে সব-শূন্য yaml string।');
  host.formula('cmd = cmd1 (L130) + cmd2 (L131); os.system(cmd) (L133) = zero Twist via shell');
  await host.sleep(1800);

  show('sh-shn'); show('sh-wz');
  host.caption('<code>os.system(cmd)</code> (L133) লাইনটা একটা <b>shell</b>-এ চালায় — node-এর rclpy জগতের বাইরে, আলাদা <b>process</b>-এর ব্রেক। তাই <code>destroy_node()</code> ভাঙতে শুরু করলেও চাকা শূন্য <code>Twist</code> পেয়ে থেমে যায়।');
  await host.sleep(1700);

  show('sh-h5'); shGlow(['sh-c145', 'sh-c146'], '#7ee787');
  show('sh-r5a'); show('sh-r5b');
  q('sh-node').setAttribute('stroke', '#30363d');
  shGlow(['sh-nt1', 'sh-nt2', 'sh-nt3'], '#6e7681');
  q('sh-ls').textContent = 'spin শেষ';
  host.caption('শেষ ধাপ: <code>destroy_node()</code> (L145) node-এর নাম আর সাবস্ক্রিপশন ছেড়ে দেয়, <code>rclpy.shutdown()</code> (L146) library বন্ধ করে। চাকা আগেই শূন্য — তাই প্রস্থানটা নিরাপদ।');
  host.formula('safe exit = zero wheels (L144) + free names (L145) + close library (L146)');
  await host.sleep(1700);

  host.caption('পুরো সারি: জন্ম L136-137, ঘূর্ণন L140, নীরব থামা L141-142, shell ব্রেক L143-144 + L128-133, বিদায় L145-146। সাধারণ নিয়মে velocity-আদেশ নিজে নিজে ফিরে আসে না — তাই <code>finally</code> না থাকলে Ctrl+C-র পরেও চাকা শেষ আদেশের বেগে চলতেই থাকত। এই নকশাটাই safety shutdown।');
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

