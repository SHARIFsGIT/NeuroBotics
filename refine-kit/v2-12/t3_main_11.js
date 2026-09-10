'use strict';
/* ================================================================
   01. arm calibration — Line-by-Line Code Analysis
   Single source of truth: FILEDATA (exact source lines from disk)
   + PARTS (authored analysis content). All rendering is generated.
   ================================================================ */

const FILEDATA = {"README.md":["sh start_agent.sh","","ros2 launch yahboom_M3Pro_laser laser_driver.launch.py","","ros2 run yahboom_M3Pro_laser laser_Avoidance"],"laser_driver.launch.py":["import os   # (System file operations) - Lets Python interact with computer folders and file paths","from ament_index_python.packages import get_package_share_directory  # A ROS 2 tool that finds where a package is installed","from launch import LaunchDescription  # The main container that holds our list of programs to start","from launch.actions import IncludeLaunchDescription  # A tool to run ANOTHER launch file inside this one","from launch.launch_description_sources import PythonLaunchDescriptionSource  # Tells ROS the other launch file is written in Python","from launch_ros.actions import Node  # A tool to start a single ROS 2 program (Node) - imported just in case it's needed later","","def generate_launch_description():","","    # --- PROGRAM 1: THE LASER MERGER ---","    # Find the path to the 'ira_laser_tools' package, go into the 'launch' folder, and find 'merge_multi.launch.py'","    laser_merge_launch_file = os.path.join(","        get_package_share_directory('ira_laser_tools'),","        'launch',","        'merge_multi.launch.py'","    )","    ","    # --- PROGRAM 2: THE LASER FILTER ---","    # Find the path to the 'yahboom_laser_filter' package, go into the 'launch' folder, and find 'laser_filter_node.launch.py'","    laser_filter_launch_file = os.path.join(","        get_package_share_directory('yahboom_laser_filter'),","        'launch',","        'laser_filter_node.launch.py'","    )","","    # --- THE FINAL LIST ---","    # Hand the list of programs back to ROS 2 to start them all at once.","    return LaunchDescription([","","        # 1. Start the Laser Merger","        # This runs the file we found above. It stitches the front and back lasers together into one 360-degree map.","        IncludeLaunchDescription(","            PythonLaunchDescriptionSource(laser_merge_launch_file)","        ),","        ","        # 2. Start the Laser Filter","        # This runs the file we found above. It cleans up the data by removing \"blind spots\" (like the robot's own arm).","        IncludeLaunchDescription(","            PythonLaunchDescriptionSource(laser_filter_launch_file)","        )","","    ])"],"laser_Avoidance.py":["#ros lib","import rclpy","from rclpy.node import Node","from geometry_msgs.msg import Twist","from sensor_msgs.msg import LaserScan","","#commom lib","import math","import numpy as np","import time","from time import sleep","from yahboom_M3Pro_laser.common import *  # Custom Yahboom tools (like the Bool message type)","import os","print (\"improt done\")  # (Typo in original code, means \"import done\")","RAD2DEG = 180 / math.pi  # Conversion factor: multiply radians by this to get degrees","","class laserAvoid(Node):","    def __init__(self,name):","        super().__init__(name)","        ","        # --- CREATING SUBSCRIBERS (Listeners) ---","        # Listen to the 360-degree LiDAR scanner","        self.sub_laser = self.create_subscription(LaserScan,\"/scan\",self.registerScan,1)","        # Listen to the joystick (so you can pause the AI and drive manually)","        self.sub_JoyState = self.create_subscription(Bool,'/JoyState', self.JoyStateCallback,1)","        ","        # --- CREATING PUBLISHERS (Radio Stations) ---","        # Tell the wheels to move","        self.pub_vel = self.create_publisher(Twist,'/cmd_vel',1)","             ","        # --- ROS 2 PARAMETERS (Safety & Speed Limits) ---","        self.declare_parameter(\"linear\",0.2)      # Forward speed (0.2 m/s)","        self.linear = self.get_parameter('linear').get_parameter_value().double_value","        self.declare_parameter(\"angular\",0.2)     # Turning speed (0.2 rad/s)","        self.angular = self.get_parameter('angular').get_parameter_value().double_value","        self.declare_parameter(\"LaserAngle\",20.0) # Width of the \"front\" cone (20 degrees to the left and right)","        self.LaserAngle = self.get_parameter('LaserAngle').get_parameter_value().double_value","        self.declare_parameter(\"ResponseDist\",0.3) # How close an obstacle must be to trigger a warning (0.3 meters)","        self.ResponseDist = self.get_parameter('ResponseDist').get_parameter_value().double_value","        ","        # --- STATE TRACKERS ---","        # These count how many laser beams hit something close in each zone","        self.Right_warning = 0","        self.Left_warning = 0","        self.front_warning = 0","        self.Joy_active = False  # Is a human driving with a joystick?","        self.conut = 3  # (Typo for \"count\"). If more than 3 beams hit an object, we consider it a real wall.","","    def JoyStateCallback(self, msg):","        if not isinstance(msg, Bool): return","        self.Joy_active = msg.data  # If True, human is driving, AI should pause","","    def registerScan(self, scan_data):","        if not isinstance(scan_data, LaserScan): return","        ranges = np.array(scan_data.ranges)  # The array of distances from the LiDAR","        ","        # Reset the counters every time a new scan comes in","        self.Right_warning = 0","        self.Left_warning = 0","        self.front_warning = 0","        ","        # Loop through every single laser beam (there are usually 360 or 720 of them!)","        for i in range(len(ranges)):","            # Calculate which direction (in degrees) this specific laser beam is pointing","            angle = (scan_data.angle_min + scan_data.angle_increment * i) * RAD2DEG","            ","            # FRONT ZONE: If the beam is pointing near straight ahead (within +/- 30 degrees)","            if abs(angle) < self.LaserAngle and ranges[i] !=0.0:","                if ranges[i] <= self.ResponseDist*1.5:  # And it hits something closer than 0.825 meters","                    self.front_warning += 1  # Add to the front counter!","                    ","            # LEFT ZONE: If the beam is pointing to the left (between 60 and 90 degrees)","            if angle < (90 - self.LaserAngle) < 90 and angle>0 and ranges[i] !=0.0:","                if ranges[i] <= self.ResponseDist*1.5:","                    self.Left_warning += 1","                    ","            # RIGHT ZONE: If the beam is pointing to the right (between -90 and -60 degrees)","            if -90 < -(90 - self.LaserAngle) < angle and angle<0 and ranges[i] !=0.0:","                if ranges[i] <= self.ResponseDist*1.5:","                    self.Right_warning += 1","","        # If a human is driving, stop the AI and do nothing","        if self.Joy_active:","            self.pub_vel.publish(Twist())","            return","","        twist = Twist()","        ","        # --- THE GIANT DECISION TREE ---","        # Based on the counts in the three zones, decide what to do.","        # (self.conut is 10. So > self.conut means \"a wall is there\", <= means \"path is clear\")","        ","        # 1. Blocked in front, left, AND right! (Trapped) -> Back up and turn right","        if self.front_warning > self.conut and self.Left_warning > self.conut and self.Right_warning > self.conut:","            print ('1, there are obstacles in the left and right, turn right')","            twist.linear.x = self.linear      # Drive forward to push through? (Actually, this is a bit of a code bug, it should be negative to reverse, but we follow the original logic)","            twist.angular.z = -self.angular    # Turn right","            self.pub_vel.publish(twist)","            sleep(0.2)  # Pause for 0.2 seconds to let the robot execute the turn","        ","        # 2. Blocked in front and right, but LEFT is clear -> Turn left","        elif self.front_warning > self.conut and self.Left_warning <= self.conut and self.Right_warning > self.conut:","            print ('2, there is an obstacle in the middle right, turn left')","            twist.linear.x = 0.0              # Stop forward motion","            twist.angular.z = self.angular     # Turn left","            self.pub_vel.publish(twist)","            sleep(0.2)","            # Double-check logic: If left is now blocked but right is clear, turn right instead","            if self.Left_warning > self.conut and self.Right_warning <= self.conut:","                twist.linear.x = 0.0","                twist.angular.z = -self.angular","                self.pub_vel.publish(twist)","                sleep(0.5)","                ","        # 4. Blocked in front and left, but RIGHT is clear -> Turn right","        elif self.front_warning > self.conut and self.Left_warning > self.conut and self.Right_warning <= self.conut:","            print ('4. There is an obstacle in the middle left, turn right')","            twist.linear.x = 0.0","            twist.angular.z = -self.angular    # Turn right","            self.pub_vel.publish(twist)","            sleep(0.2)","            if self.Left_warning <= self.conut and self.Right_warning > self.conut:","                twist.linear.x = 0.0","                twist.angular.z = self.angular","                self.pub_vel.publish(twist)","                sleep(0.5)","                ","        # 6. Blocked ONLY in front -> Turn left to find a way around","        elif self.front_warning > self.conut and self.Left_warning < self.conut and self.Right_warning < self.conut:","            print ('6, there is an obstacle in the middle, turn left')","            twist.linear.x = 0.0","            twist.angular.z = self.angular","            self.pub_vel.publish(twist)","            sleep(0.2)","            ","        # 7. Front is clear, but blocked on left AND right (narrow hallway) -> Turn right to follow the wall","        elif self.front_warning < self.conut and self.Left_warning > self.conut and self.Right_warning > self.conut:","            print ('7. There are obstacles on the left and right, turn right')","            twist.linear.x = 0.0","            twist.angular.z = -self.angular","            self.pub_vel.publish(twist)","            sleep(0.4)","            ","        # 8. Front is clear, but blocked ONLY on the left -> Turn right to avoid the left wall","        elif self.front_warning < self.conut and self.Left_warning > self.conut and self.Right_warning <= self.conut:","            print ('8, there is an obstacle on the left, turn right')","            twist.linear.x = 0.0","            twist.angular.z = -self.angular","            self.pub_vel.publish(twist)","            sleep(0.2)","            ","        # 9. Front is clear, but blocked ONLY on the right -> Turn left to avoid the right wall","        elif self.front_warning < self.conut and self.Left_warning <= self.conut and self.Right_warning > self.conut:","            print ('9, there is an obstacle on the right, turn left')","            twist.linear.x = 0.0","            twist.angular.z = self.angular","            self.pub_vel.publish(twist)","            sleep(0.2)","            ","        # 10. EVERYTHING IS CLEAR! -> Drive forward happily","        elif self.front_warning <= self.conut and self.Left_warning <= self.conut and self.Right_warning <= self.conut:","            print ('10, no obstacles, go forward')","            twist.linear.x = self.linear","            twist.angular.z = 0.0","            self.pub_vel.publish(twist)","","    # --- SAFETY SHUTDOWN FUNCTION ---","    def exit_pro(self):","        # When you press Ctrl+C, this runs a terminal command in the background to force the robot to stop","        cmd1 = \"ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist \"","        cmd2 = '''\"{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}\"'''","        cmd = cmd1 +cmd2","        os.system(cmd)","","","def main():","    rclpy.init()","    laser_avoid = laserAvoid(\"laser_Avoidance_a1\")","    print (\"start it\")","    try:","        rclpy.spin(laser_avoid)","    except KeyboardInterrupt:","        pass","    finally:","        laser_avoid.exit_pro()  # Force stop the wheels","        laser_avoid.destroy_node()","        rclpy.shutdown()"]};
const PARTS = [{"n":1,"id":"part-01","fname":"README.md","enTitle":"Runbook — Three Commands","lang":"bash","start":1,"end":5,"flags":[],"explain":[{"a":1,"b":1,"text":"<code>sh start_agent.sh<\/code> — runbook-এর প্রথম command: <code>sh<\/code> interpreter দিয়ে vendor-এর bringup script-টা চালানো হলো। মনে রাখতে হবে এই script-টা আমাদের কোনো project folder-এর ভেতরে নেই, তাই ভেতরে ঠিক কী লেখা আছে তা আমরা দেখিনি — illustrative ধারণা: এটা robot-এর base driver আর সামনে-পেছনের দুটো lidar-এর vendor driver তুলে দেয়, যাতে কাঁচা scan data বেরোতে শুরু করে। folder 10-এর README-এর প্রথম line-ও হুবহু এই command-ই — মানে series-এর প্রতিটা lidar পরীক্ষার গোড়ায় একই bringup, folder 11 কিছু নতুন করে যোগ করেনি এখানে। README-টা মোট ৫ line-এর: L2 আর L4 blank line, শুধু তিনটা স্তরকে চোখে আলাদা দেখানোর separator — আসল content তিনটা command, আর তিনটাই পরেরটার পূর্বশর্ত।"},{"a":3,"b":3,"text":"<code>ros2 launch yahboom_M3Pro_laser laser_driver.launch.py<\/code> — দ্বিতীয় স্তর। এবারের রূপ <code>ros2 launch package_name launch_file<\/code>: ROS 2 আগে <code>yahboom_M3Pro_laser<\/code> package-টা খোঁজে, তার share directory থেকে <code>laser_driver.launch.py<\/code> হাতে নিয়ে তার <code>generate_launch_description()<\/code> চালায়। launch file-টাই এই folder-এর প্রথম source file — পরের part-গুলোতে দেখব এর ভেতরে কোনো node সরাসরি লেখা নেই; দুটো <code>IncludeLaunchDescription<\/code> দিয়ে folder 10-এর গোটা fusion pipeline চেইন করা হয়েছে — <code>ira_laser_tools<\/code>-এর merger launch সামনে-পেছনের lidar জোড়ে একটা 360-degree scan বানায়, <code>yahboom_laser_filter<\/code> blind spot সরিয়ে data পরিষ্কার করে। ফলে <code>/scan<\/code> topic-এ merged stream প্রস্তুত হয়। <code>ros2 launch<\/code>-এর ক্ষমতা এখানেই — এক command-এ একাধিক node-এর পুরো chain একসাথে ওঠে।"},{"a":5,"b":5,"text":"<code>ros2 run yahboom_M3Pro_laser laser_Avoidance<\/code> — তৃতীয় ও শেষ স্তর: behavior node। এবার <code>ros2 launch<\/code> নয়, <code>ros2 run package_name executable_name<\/code> — কোনো launch file ছাড়াই package-এর একটাই executable সরাসরি চালানো হয়েছে, নাম <code>laser_Avoidance<\/code> (বড় হাতের A লক্ষ্য করুন)। node-টা <code>laser_Avoidance_a1<\/code> নাম নিয়ে জন্মায়, L3-এর chain থেকে আসা merged <code>/scan<\/code> আর joystick-এর <code>/JoyState<\/code> subscribe করে, প্রতিটা scan-এ তিনটা angular zone-এ কাছের beam গুনে ৯-branch decision tree দিয়ে <code>/cmd_vel<\/code>-এ command publish করে। এই folder-এর আসল নতুনত্ব এখানেই — folder 10 পর্যন্ত আমরা data জোগাড় করেছি, এবার সেই data-র উপর সিদ্ধান্ত নিয়ে চাকা ঘোরানো হয়। ক্রমটা সৌন্দর্যের নয়: L3 না উঠলে এই node কোনো scan পায় না, উঠে চুপচাপ বসে থাকে।"}],"math":null,"robot":{"correct":"বাস্তব robot-এ তিনটা command ঠিক এই ক্রমে দিন। L1-এর vendor bringup base আর দুটো lidar driver জাগায় (illustrative), L3-এর launch folder 10-এর merger ও filter chain তুলে <code>/scan<\/code>-এ 360-degree data পাঠাতে শুরু করে, তারপর L5-এর node প্রতিটা scan পেয়ে <code>/cmd_vel<\/code>-এ velocity দেয় — তিন স্তর পূর্ণ হলে robot নিজে থেকেই obstacle এড়িয়ে ঘোরে। একটা স্তর বাদ গেলে পরের স্তরের খাবারই আসে না।","incorrect":"সাধারণ ভুল: L5 আগে চালানো। ROS 2-এ subscription এমন topic-এও সফল হয় যার publisher এখনো নেই, তাই node ত্রুটিমুক্ত উঠে বসে থাকে — <code>registerScan<\/code> একবারও চলে না, <code>/cmd_vel<\/code>-এ কিছু যায় না, আর মনে হয় node-টাই নষ্ট। আসল কারণ: fusion chain ওঠেনি বলে <code>/scan<\/code> চুপ। একই ফল হয় L1 বাদ দিলে — lidar থেকে কাঁচা scan-ই আসে না।"},"animType":"runbookFlow"},{"n":2,"id":"part-02","fname":"laser_driver.launch.py","enTitle":"Driver Launch — Imports","lang":"python","start":1,"end":7,"flags":[],"explain":[{"a":1,"b":2,"text":"<code>import os<\/code> — Python-এর standard library-র file ও path টুল, author-এর comment বলছে (System file operations)। কাজ একটাই: L12 আর L20-এ <code>os.path.join<\/code> দিয়ে folder 10-এর <code>merge_multi.launch.py<\/code> ও <code>laser_filter_node.launch.py<\/code>-এর path জোড়া দেওয়া। <code>from ament_index_python.packages import get_package_share_directory<\/code> এনেছে সেই ROS 2 function যেটাকে package-এর নাম দিলে — L13-এ <code>ira_laser_tools<\/code>, L21-এ <code>yahboom_laser_filter<\/code> — সে ওই package-এর install হওয়া share directory-র পথ ফিরিয়ে দেয়। এটা plain function call: <code>generate_launch_description()<\/code> চলার সময়েই, মানে construction time-এ, পথ মিলে যায় — folder 10-এর <code>LaunchConfiguration<\/code> substitution-এর lazy আচরণের ঠিক উল্টো; এজন্যই package install না থাকলে launch পড়ার মুহূর্তেই error আসে।"},{"a":3,"b":5,"text":"<code>from launch import LaunchDescription<\/code> — প্রধান container; L28-এ <code>return LaunchDescription<\/code> দিয়ে যে list-টা launch framework-এর হাতে ফিরে যায় সেটাই এই class-এর object, তাই এই import ছাড়া পুরো file-টাই অর্থহীন। <code>from launch.actions import IncludeLaunchDescription<\/code> এই file-এর আসল অস্ত্র: একটা launch file-এর ভেতরে আরেকটা launch file চালানোর action, নামেরই মানে Include — L32 আর L38-এ একটা করে বসেছে। এই একটা tool-ই এখানকার পুরো design: নিজে কোনো node না চালিয়ে folder 10-এর merger ও filter launch-কে chain করা। <code>from launch.launch_description_sources import PythonLaunchDescriptionSource<\/code> বাইরের path string-টাকে wrap করে framework-কে জানায় যে ওই file-টা Python launch file — ROS 2-এ XML বা YAML launch source-ও আছে, কিন্তু এখানে দুটোই Python। এই তিনটি মিলেই launch-chaining pattern: container, include action, আর Python source declaration।"},{"a":6,"b":6,"text":"<code>from launch_ros.actions import Node<\/code> — author-এর নিজের comment-ই স্বীকার করছে \"imported just in case it's needed later\", আর সত্যিই গোটা file-এ <code>Node<\/code> আর কোথাও ব্যবহার হয়নি: L28-42-এর list-এ শুধু দুটো <code>IncludeLaunchDescription<\/code>, কোনো <code>Node<\/code> action নেই। এটা একটা দামি পাঠ — import দেখেই মনে করা যাবে না জিনিসটা কাজে লাগছে; Python নামটাকে module scope-এ bind করে চুপচাপ বসে থাকে, কোনো warning বা error নেই, তাই dead import সহজে চোখে পড়ে না। পার্থক্যটা ধরো: folder 10-এর <code>merge_multi.launch.py<\/code> একইভাবে <code>Node<\/code> import করে সরাসরি node চালু করেছিল, কিন্তু এই file সব কাজ অন্য দুই launch file-কে দিয়ে করায়। শেষ সূক্ষ্ম পয়েন্ট: <code>launch<\/code> আর <code>launch_ros<\/code> দুটো আলাদা package — <code>Node<\/code> পাওয়া যায় শুধু দ্বিতীয়টায়, তাই ভবিষ্যতে সত্যিই কোনো node যোগ করতে হলে এই লাইনটাই আগে থেকে প্রস্তুত ছিল।"}],"math":null,"robot":{"correct":"এই file তুললেই <code>get_package_share_directory<\/code> construction time-এ robot-এর install tree থেকে <code>ira_laser_tools<\/code> ও <code>yahboom_laser_filter<\/code>-এর share directory খুঁজে দেয়, তাই merger ও filter-এর launch file-এর path আগেই ঠিক হয়। এরপর দুটো IncludeLaunchDescription chain হয়ে folder 10-এর পুরো fusion pipeline ওঠে — front আর back lidar মিলে 360-degree fused <code>/scan<\/code> তৈরি হয়, যা ছাড়া <code>laser_Avoidance<\/code> node কোনো data-ই পেত না।","incorrect":"ভুল পড়া: L6-এর <code>Node<\/code> import দেখে ধরে নেওয়া যে এই launch file নিজে obstacle-avoidance node-ও চালু করে। Robot-এ এই ধারণা বিপদজনক: মনে করা হবে robot নিজে নিজে বাধা এড়াচ্ছে, অথচ <code>/cmd_vel<\/code> publish করার node চালুই হয়নি — <code>ros2 run yahboom_M3Pro_laser laser_Avoidance<\/code> আলাদাভাবে না চালালে merger-filter উঠুক, <code>/scan<\/code> প্রস্তুত হোক, robot চুপচাপ দাঁড়িয়ে থাকবে। আর unused ভেবে এই import মুছলে কিছু ভাঙে না, কিন্তু author-এর just-in-case দরজাটা বন্ধ হয়।"},"animType":null},{"n":3,"id":"part-03","fname":"laser_driver.launch.py","enTitle":"Two Paths — Merger & Filter","lang":"python","start":8,"end":24,"flags":[],"explain":[{"a":8,"b":8,"text":"<code>def generate_launch_description():<\/code> — এই নামটাই ros2 launch-এর সঙ্গে চুক্তি। <code>ros2 launch yahboom_M3Pro_laser laser_driver.launch.py<\/code> চালালে framework এই file-কে import করে ঠিক এই নামের function-টাকে ডাকে; নাম বদলালে launch ভেঙে পড়বে। Function-এর ভেতরের প্রতিটা লাইন চলে CONSTRUCTION phase-এ — run phase শুরু হওয়ার আগে, একবার, উপর থেকে নিচে। Folder 10-এর বিখ্যাত lesson মনে করো: <code>LaunchConfiguration<\/code> substitution ছিল lazy, run phase-এ গিয়ে মান মেলে; এই file-এ তার উল্টো ঘটবে — যা লেখা সব এখনই eagerly চলে। কাজ শেষে function-টা একটা <code>LaunchDescription<\/code> ফেরাবে (L28), সেটাকেই framework পরে run করায়।"},{"a":10,"b":11,"text":"দুটো লাইনই <code>#<\/code> দিয়ে শুরু — comment, Python এগুলো execute করে না, তবু author-এর নকশা হিসেবে এরা file-টার কাঠামো পরিষ্কার করে। L10 হলো banner: <code>PROGRAM 1: THE LASER MERGER<\/code> — এর পরের কয়েকটা লাইন প্রথম program-এর জন্য। L11 কাজ বলে: <code>ira_laser_tools<\/code> package-এর path খুঁজে, তার <code>launch<\/code> folder-এ ঢুকে <code>merge_multi.launch.py<\/code> বের করা। Comment-এ যা বলা হলো L12-16 হুবহু তা-ই করে — comment মানচিত্র, code পথ। এই <code>merge_multi.launch.py<\/code>-ই folder 10-এ লাইন ধরে পড়া প্রথম file: সেখানে সামনে-পেছনে দুই lidar-এর raw scan (folder 09-এ যেমন একট lidar-এর নিজস্ব stream দেখেছি) এক 360-degree <code>/scan<\/code>-এ জোড়া লাগে।"},{"a":12,"b":13,"text":"<code>laser_merge_launch_file = os.path.join(<\/code> — assignment শুরু, আর bracket L16 পর্যন্ত খোলা থাকায় তার সব argument একসঙ্গে মূল্যায়ন হবে। প্রথম argument <code>get_package_share_directory('ira_laser_tools')<\/code>: এটা launch-এর কোনো magic নয়, ament-এর package index-কে জিজ্ঞেস করা একটা সাধারণ Python function call — আর সে চলে এখনই, construction phase-এ, string হিসেবে installed share directory-র path ফেরিয়ে দেয় (illustrative: <code>install/ira_laser_tools/share/ira_laser_tools<\/code> — যা <code>ros2 pkg prefix<\/code> দেখায়)। Package না মিললে এখনই error ওঠে, run phase শুরু হওয়ার অনেক আগেই।"},{"a":14,"b":16,"text":"পরের দুটো argument <code>'launch'<\/code> আর <code>'merge_multi.launch.py'<\/code>। <code>os.path.join<\/code> এদের মাঝে ঠিক separator (<code>/<\/code>) বসিয়ে একটা পূর্ণ path বানায় — string <code>+<\/code> দিয়ে জোড়া দিলে separator ভুল হওয়ার ঝুঁকি থাকে, <code>os.path.join<\/code> সেই ভার নিজে নেয়, তাই কোন OS-এ চলুক না কেন path ঠিক থাকে। ফল: folder 10-এর প্রথম launch file-এর absolute path, জমা রইল variable <code>laser_merge_launch_file<\/code>-এ। খেয়াল করো, এখনো কিছুই launch হয়নি — এটা নিছক একটা string। Merger-এর আসল কাজ হবে run phase-এ, Part 04-এর <code>IncludeLaunchDescription<\/code> action থেকে।"},{"a":18,"b":19,"text":"সেই একই pattern-এর দ্বিতীয় কপি। L18 banner: <code>PROGRAM 2: THE LASER FILTER<\/code>; L19 বলে — <code>yahboom_laser_filter<\/code> package-এর path, তার <code>launch<\/code> folder, ভেতরে <code>laser_filter_node.launch.py<\/code>। ভাষা ও গঠন ইচ্ছা করেই আগের ব্লকের মতো রাখা: দুটো আলাদা program, কিন্তু খোঁজার নিয়ম এক। ভূমিকাও স্পষ্ট — merger দুই lidar-এর মিলিত scan বানায়, filter তার পরে সেই stream পরিষ্কার করে blind spot সরায়; এই ক্রমটাই folder 10-এ দেখা pipeline, এখন এক launch file থেকে পুরোটা একসঙ্গে চালানো হচ্ছে।"},{"a":20,"b":21,"text":"<code>laser_filter_launch_file = os.path.join(<\/code> — নামে শুধু merge-এর জায়গায় filter, বাকি আদল হুবহু আগের ব্লক। <code>get_package_share_directory('yahboom_laser_filter')<\/code> এবার অন্য একটা package খোঁজে — Yahboom-এর নিজের laser filter package, <code>ira_laser_tools<\/code> নয়। এটাও একই সাধারণ function call: চলে এখনই, eagerly, construction phase-এ — তাই দুটো path-ই সঙ্গে সঙ্গে মিলে যায় আর দুটোই যাচাই হয়ে যায় launch নামানোর আগেই। এক launch-এ একাধিক package-এর tool এভাবেই এক জায়গায় জড়ো করা যায় — এই file-টা তারই ছোট উদাহরণ।"},{"a":22,"b":24,"text":"শেষ দুটো segment: <code>'launch'<\/code> আর <code>'laser_filter_node.launch.py'<\/code> — মিলে folder 10-এর দ্বিতীয় launch file-এর পূর্ণ path, জমা <code>laser_filter_launch_file<\/code>-এ। এই মুহূর্তে file-টার অবস্থা দাঁড়াল এমন: দুটো string variable তৈরি, দুটোতেই বাস্তব path, কিন্তু একটাও program এখনো চালু হয়নি। এরপর L26 থেকে আসবে সেই তালিকা তৈরির পর্ব, যেখানে এই দুই path <code>IncludeLaunchDescription<\/code> দিয়ে run phase-এ নামানো হবে। সহজ কথায়: L12-24 হলো দুইটা ঠিকানা খুঁজে লিখে রাখা — বাড়ি বানানোর কাজ পরের part-এ।"}],"math":null,"robot":{"correct":"আসল robot-এ <code>ros2 launch yahboom_M3Pro_laser laser_driver.launch.py<\/code> চালালে সবার আগে চলে এই দুইটা path lookup — ament index থেকে <code>ira_laser_tools<\/code> আর <code>yahboom_laser_filter<\/code>-এর installed share directory মিলে যায়, তারপরই merger+filter pipeline নামে। Terminal-এ workspace source থাকলে path কখনো ভুল হয় না, workspace অন্য জায়গায় থাকলেও ঠিক থাকে। কোনো package না মিললে robot চলতে শুরু করার আগেই construction-এ error ওঠে — early failure, নিরাপদ।","incorrect":"বিভ্রান্তি: অনেকে ভাবে এই লাইনেই merger আর filter চালু হয়ে গেছে, বা source folder-এর <code>merge_multi.launch.py<\/code> এডিট করলেই robot-এর আচরণ বদলাবে। আসলে path-টা পড়ে install/share-এর কপি থেকে — rebuild না করে এডিট করলে পুরনো fusion config-ই চলে, ফলে ভুল lidar topic বা ভুল frame-এ scan আসে, <code>/scan<\/code> ভরে না, obstacle avoidance অন্ধ হয়ে যায়।"},"animType":"includeChain"},{"n":4,"id":"part-04","fname":"laser_driver.launch.py","enTitle":"Return — Two Includes, Zero Nodes","lang":"python","start":26,"end":42,"flags":[],"explain":[{"a":26,"b":27,"text":"শেষ পর্বের ঘোষণা — L26-এর <code># --- THE FINAL LIST ---<\/code> ঠিক আগের দুটো section header-এর (<code>PROGRAM 1<\/code>, <code>PROGRAM 2<\/code>) মতোই একই dash-ঘেরা format-এ লেখা। তফাত হলো: আগের দুই পর্ব শুধু দুটো file path string বানিয়েছিল (L12-16, L20-24), এই পর্ব সেই path-গুলো কাজে লাগায়। L27 বলছে program-এর list ROS 2-কে ফিরিয়ে দিয়ে সব একসাথে চালু করতে হবে — কিন্তু এই ফাইলের নিজস্ব কোনো program নেই; list-এ ঢুকবে শুধু দুটো include action। অর্থাৎ পুরো ফাইলটা একটা pure orchestrator: নিজে কোনো node চালায় না, শুধু অন্য দুটো launch file-এর ঠিকানা হাজির করে দেয়।"},{"a":28,"b":28,"text":"L28 একটা পুরো বাক্যের দরজা খুলে দেয় — <code>return<\/code> মানে <code>generate_launch_description()<\/code>-এর ফল হিসেবে ros2 launch tool পাবে ঠিক এই object-টাই। <code>LaunchDescription<\/code> হলো L3-এ import করা container class, আর তার constructor-কে সরাসরি একটা list literal দেওয়া হচ্ছে: opening <code>[<\/code> এই লাইনে, element-গুলো L30-40-এ, closing <code>]<\/code> L42-তে। Folder 10-এর <code>merge_multi.launch.py<\/code> আলাদা আলাদা list বানিয়ে জোড়া দিয়েছিল; এখানে পথ উল্টো — inline list, দুটো element সরাসরি বন্ধনীর ভেতরে। ছোট ফাইলে এর সুবিধা যে list-এর সব উপাদান একসাথে চোখের সামনে থাকে, কোথায় কী যোগ হচ্ছে আলাদা করে খুঁজতে হয় না।"},{"a":30,"b":31,"text":"List-এর প্রথম element-এর আগের comment। <code># 1.<\/code> নম্বরটা ক্রম শেখাচ্ছে: merger আগে, filter পরে — এই ক্রম পাইপলাইনের গল্পের সাথে মেলে। L31 বলছে এই include <code>the file we found above<\/code> চালাবে, আর তার কাজ দুটো lidar-এর data জোড়া দেওয়া — comment-এর ভাষায় ওটা <code>stitches the front and back lasers together into one 360-degree map<\/code>। <code>found above<\/code> মানে L12-16-এ construction time-এই বসে যাওয়া <code>laser_merge_launch_file<\/code> path — কোনো lazy substitution নয়, string তখনই final। Folder 10-এ আমরা এই ফাইলের ভেতরটা পড়েছি, folder 09-এ দেখেছি একটা lidar একটাই দিক দেখে — তাই 360-degree দেখতে হলে এই জোড়া ছাড়া উপায় নেই।"},{"a":32,"b":34,"text":"তিন লাইনের nested গঠন। বাইরে <code>IncludeLaunchDescription<\/code> (L4-এর import) — launch জগতের recursion tool: এক launch file-এর ভেতরে আরেকটা launch file চালানোর একমাত্র পরিষ্কার উপায়। ভেতরে <code>PythonLaunchDescriptionSource(laser_merge_launch_file)<\/code> (L5-এর import) — এটা জানিয়ে দেয় অন্তর্ভুক্ত ফাইলটা Python launch file, YAML নয়। সবচেয়ে ভেতরে path string। Run phase-এ framework এই action execute করতে গিয়ে ওই ফাইল import করে তার নিজের <code>generate_launch_description()<\/code> ডাকে — অর্থাৎ প্রতিটা included ফাইলের নিজের constructor phase আর run phase আলাদা করে চলে; ভেতরের গল্পটা folder 10-এর, এখানে সেটা illustrative। L34-এর <code>),<\/code> এই include-টা বন্ধ করে কমা সহ — কমাটাই list-এর দুই element-এর বিভাজক।"},{"a":36,"b":37,"text":"দ্বিতীয় element-এর comment — <code># 2.<\/code> বলছে এটা পাইপলাইনের দ্বিতীয় ধাপ। L37-এর ব্যাখ্যা folder 10-এর filter-এর কাজের সাথে মেলে: ওটা <code>removes \"blind spots\" (like the robot's own arm)<\/code> — মানে fused scan-এর ভেতর robot-এর নিজের গা, হাত কিংবা arm-এর reflection থেকে আসা ভুয়া কাছের রিডিং বাদ দেওয়া হয়। এটা শুধু data সাজানোর ব্যাপার নয়: filter না থাকলে <code>laser_Avoidance<\/code> node robot-এর নিজের হাতকেই বাধা ভেবে সামনে যাওয়া ছেড়ে দিতে পারত। আর <code>the file we found above<\/code> এখানে L20-24-এর <code>laser_filter_launch_file<\/code> path-কেই বোঝায় — একই construction-time নিয়ম, string আগেই বসে আছে।"},{"a":38,"b":40,"text":"দ্বিতীয় include — গঠনে হুবহু প্রথমটার মতো, শুধু সবচেয়ে ভেতরের argument আলাদা: <code>laser_filter_launch_file<\/code>। দুটো action দেখতে অভিন্ন হলেও ওরা দুটো সম্পূর্ণ আলাদা ফাইল খুলবে — একটা <code>ira_laser_tools<\/code> package থেকে, আরেকটা <code>yahboom_laser_filter<\/code> package থেকে। Run phase-এ framework list-এর ভেতর দিয়ে উপর থেকে নিচে action execute করে, তাই merger আগে চালু, filter পরে — আর ক্রমটা অর্থবহ, কারণ merger-এর output stream-ই filter-এর input। তবে এটা শুধু action-এর ক্রম, কোনো synchronization নয়: ROS 2-তে একটা process সামান্য আগে-পরে উঠলেও publisher-subscriber পরে মিলে যায়, এই কারণে launch ভেঙে পড়ে না।"},{"a":42,"b":42,"text":"ফাইলের শেষ লাইন, দুটো bracket একসাথে বন্ধ — bracket ladder-এর শেষ ধাপ। ভেতরের <code>]<\/code> L28-এ খোলা list literal বন্ধ করে, বাইরের <code>)<\/code> <code>LaunchDescription<\/code> constructor call বন্ধ করে, আর তখনই <code>return<\/code> statement সম্পূর্ণ হয়। গুনে দেখো হিসাবটা: L28-এর <code>LaunchDescription([<\/code> দুটো খুলেছিল, L34 আর L40-এর <code>),<\/code> প্রতিটা include বন্ধ করেছে, L42 বাকি দুটো বন্ধ করে সব মিলিয়ে দিয়েছে। পুরো ফাইলের সারমর্ম এখানেই: constructor phase-এ দুটো path string, run phase-এ দুটো include action, আর নিজের node একদম zero — L6-এ import করা <code>Node<\/code> কখনো ব্যবহারই হয়নি, ওই লাইনের comment নিজেই বলে দিয়েছিল এটা রাখা হয়েছে শুধু সতর্কতার জন্য।"}],"math":null,"robot":{"correct":"Real robot-এ এক কমান্ডে পুরো sensing পাইপলাইন ওঠে: merger আগে চালু হয়ে সামনে-পেছনের দুটো lidar-এর raw scan জুড়ে 360-degree fused view বানায়, তারপর filter তা থেকে robot-এর নিজের arm-এর ভুয়া কাছের রিডিং বাদ দেয়। ফলে আলাদাভাবে চালু করা <code>laser_Avoidance<\/code> node একটা পরিষ্কার <code>/scan<\/code> পায়। এই ফাইল নিজে কোনো <code>/cmd_vel<\/code> message পাঠায় না, তাই এটা চালু করলেই robot নড়ে না — শুধু তার চোখ খোলে।","incorrect":"সাধারণ ভুল: এই launch file-টাই obstacle avoidance চালায় ভেবে নেওয়া। আসলে এর ভেতরে একটাও Node action নেই, শুধু দুটো include; avoidance node README-র শেষ কমান্ডে আলাদা করে <code>ros2 run<\/code> করতে হয়। আরও একটা ভুল: filter include বাদ দিলে সময় বাঁচে ভাবা — blind spot রিডিং fused scan-এ থেকে গেলে robot নিজের arm-কেই বাধা ভেবে বারবার ঘুরতে শুরু করবে।"},"animType":null},{"n":5,"id":"part-05","fname":"laser_Avoidance.py","enTitle":"Avoidance Node — Module Head","lang":"python","start":1,"end":15,"flags":[],"explain":[{"a":1,"b":2,"text":"<code>#ros lib<\/code> — ফাইলের একদম শুরুর এই comment-টা আসলে একটা section-header: লেখক নিচের import-গুলোকে দুই ভাগে সাজিয়েছেন — প্রথম ভাগ ROS 2-এর নিজস্ব জিনিস (L2-5), পরের ভাগ (L7-এর পরে) সাধারণ Python library। <code>#<\/code> দিয়ে শুরু বলে এই লাইনে কিছুই execute হয় না, এটা শুধু পাঠকের জন্য চিহ্ন। <code>import rclpy<\/code> হলো এই পুরো behavior node-এর ভিত্তি — ROS 2-এর Python client library: <code>rclpy.init()<\/code>, <code>rclpy.spin()<\/code>, publisher আর subscription-এর সব যন্ত্রপাতি এখান থেকেই আসে (L177, L181)। folder 10-এ আমরা launch ফাইলের বাইরে থেকে কাজ করেছি; এই ফাইলে প্রথমবার একটা চালু node-এর ভেতরে ঢুকছি, আর তার প্রাণ <code>rclpy<\/code>।"},{"a":3,"b":4,"text":"<code>from rclpy.node import Node<\/code> — <code>rclpy<\/code> বিশাল একটা library, তাই ঠিক যে class-টা দরকার সেটাই বের করে আনা হলো: <code>Node<\/code>। L17-তে <code>class laserAvoid(Node)<\/code> লিখে এটাকে inherit করা হবে — ROS 2-এ প্রতিটি node আসলে <code>Node<\/code>-এর subclass, তাই <code>create_subscription<\/code>, <code>create_publisher<\/code>, <code>declare_parameter<\/code>-এর মতো প্রস্তুত সব ক্ষমতা হাতে আসে। <code>from geometry_msgs.msg import Twist<\/code> — velocity-র বাহন message: ভেতরে <code>linear<\/code> আর <code>angular<\/code> দুটো field, প্রতিটাতে x, y, z তিনটা axis। L29-এ <code>/cmd_vel<\/code> topic-এ publisher বানানো হবে ঠিক এই <code>Twist<\/code> দিয়ে, আর decision tree-র প্রতিটা branch <code>linear.x<\/code> ও <code>angular.z<\/code> ভরে publish করবে — চাকার motor driver একই message শুনে robot-কে ঘোরায়।"},{"a":5,"b":7,"text":"<code>from sensor_msgs.msg import LaserScan<\/code> — LiDAR-র ফলাফলের আদর্শ message: <code>angle_min<\/code>, <code>angle_increment<\/code>, <code>ranges<\/code> এই সব field এর ভেতরে থাকে। L23-এ <code>/scan<\/code> topic-এ subscription নেওয়া হবে — সেটা folder 10-এর merger+filter chain-এর শেষ প্রান্ত, মানে সামনে-পেছনে দুই lidar-এর মিলেমিশে পরিষ্কার করা 360-degree stream। L65-এ <code>angle_min + angle_increment * i<\/code> হিসেবে প্রতিটা beam-এর কোণ বের করা হবে। একটা জরুরি সংস্কৃতি-তথ্য: <code>LaserScan<\/code>-এর সব কোণ field radian এককে থাকে — folder 09-এর echo-তে দেখা গিয়েছিল <code>angle_min<\/code> মান <code>-3.14159<\/code> আর increment <code>0.0174533<\/code>; সেজন্যই L15-এ <code>RAD2DEG<\/code> বানানোর দরকার পড়েছে। আর L7-এর comment <code>#commom lib<\/code> — 'common'-এর বানান-ভুল source-এ যেমন আছে তেমনই রাখা হয়েছে; এখান থেকে সাধারণ Python library-র ভাগ শুরু।"},{"a":8,"b":10,"text":"<code>import math<\/code> — Python-এর গাণিতিক library; এই ফাইলে তার চাকরি L15-এ: <code>math.pi<\/code> থেকে <code>RAD2DEG<\/code> constant-টা বানানো। <code>import numpy as np<\/code> — numeric Python-কে ছোট নামে ডেকে আনা হলো; আসল কাজ হবে L55-এ — <code>ranges = np.array(scan_data.ranges)<\/code> — মানে lidar-র দূরত্ব-list-কে vector-এ রূপ দেওয়া, যাতে 360/720 beam-এর প্রতিটা মান <code>ranges[i]<\/code> দিয়ে সরাসরি ধরা যায়। <code>import time<\/code> — ঘড়ি-library; লক্ষ করো নিচের পুরো কোডে ব্যবহার হয়েছে তার <code>sleep<\/code>-ই (L11 থেকে এসে L99-এ কাজে লাগা), <code>time.<\/code> লেখা আর কোথাও নেই — vendor code-এ এমন বাড়তি import থেকে যাওয়া খুবই সাধারণ। তিনটাই খাঁটি Python, ROS-এর কোনো জিনিস নয়।"},{"a":11,"b":13,"text":"<code>from time import sleep<\/code> — একই <code>time<\/code> module থেকে শুধু <code>sleep<\/code> function-টা বের করে আনা, তাই L99-এ <code>sleep(0.2)<\/code> সরাসরি লেখা যায়, <code>time.sleep(0.2)<\/code> লেখার দরকার নেই। L12 <code>from yahboom_M3Pro_laser.common import *<\/code> — wildcard import: robot vendor-এর নিজের package-এর <code>common<\/code> module থেকে সব public নাম এই ফাইলের namespace-এ ঢেলে দেওয়া। inline comment বলছে এখান থেকেই <code>Bool<\/code> message type আসে — L25-এ <code>/JoyState<\/code> subscription-এ ঠিক সেই <code>Bool<\/code> লাগবে, কারণ এই ফাইলে <code>Bool<\/code> আলাদা করে আর কোথাও import করা নেই। সুবিধা হলো ছোট-করে-লেখা; বিপদ হলো কোন নাম কোথা থেকে এল তা আর চোখে পড়ে না, namespace নীরবে ভরে যায় — এটাই wildcard import-এর আসল tradeoff। <code>import os<\/code> — L173-এর <code>os.system()<\/code> (shutdown-এর brake) চালানোর অস্ত্র এখানেই জমা রাখা।"},{"a":14,"b":14,"text":"<code>print (\"improt done\")<\/code> — এক লাইনে দুটো কৌতূহল। প্রথমটা বানান: হওয়ার কথা 'import done', আর লেখক নিজেই comment-এ স্বীকার করেছেন — <code># (Typo in original code, means \"import done\")<\/code>; আমরা source যেমন আছে তেমনই শিখছি, ঠিক করছি না। দ্বিতীয়টা syntax: <code>print<\/code>-এর নাম আর বন্ধনীর মাঝে একটা space আছে — Python-এ এটা একদম legal, interpreter বিরক্ত হয় না, শুধু style-guide এটা পছন্দ করে না। সবচেয়ে বড় শিক্ষা: লাইনটা কোনো function-এর ভেতরে নয়, module-এর top level-এ বসেছে — তাই এটা run হবে import-এর মুহূর্তেই, <code>main()<\/code>-এর ডাক আসার আগেই। README-র <code>ros2 run yahboom_M3Pro_laser laser_Avoidance<\/code> চালালে terminal-এ node-এর জন্মের আগেই এই লেখা ফুটে উঠবে — import-পথ বেঁচে আছে কি না তার একটা সস্তা সংকেত।"},{"a":15,"b":15,"text":"<code>RAD2DEG = 180 / math.pi<\/code> — একটা সংখ্যা মাত্র (প্রায় 57.29578), কিন্তু এই ফাইলের দুই জগতের অনুবাদক। ROS 2-এর <code>LaserScan<\/code> message-এর কোণ field গুলো radian-এ থাকে (folder 09-এর echo: <code>angle_min<\/code> = <code>-3.14159<\/code>), অথচ এই কোডের মানুষে-পড়া সীমানা ডিগ্রিতে — <code>LaserAngle<\/code> parameter-এর default মান 20.0 মানে 20 degree (L36)। L65-এ <code>(angle_min + angle_increment * i) * RAD2DEG<\/code> হিসেবে প্রতিটা beam-এর কোণ ডিগ্রিতে রূপ নেবে, তারপর L68-এর <code>abs(angle) &lt; self.LaserAngle<\/code> তুলনায় দুই পাশেই একই একক দাঁড়ায়। সূত্রটা মনে রাখার সহজ রাস্তা: অর্ধবৃত্ত = 180 degree = <code>pi<\/code> radian, তাই 1 radian = <code>180/pi<\/code> degree। <code>math.degrees()<\/code>-ও একই কাজ করত, লেখক নিজের হাতে constant বানিয়ে নিয়েছেন।"}],"math":null,"robot":{"correct":"Real robot-এ <code>ros2 run yahboom_M3Pro_laser laser_Avoidance<\/code> চালানোর সাথে সাথে আগে এই ১৫ লাইন execute হয়: rclpy লোড হয়, vendor package-এর <code>common<\/code> module থেকে <code>Bool<\/code> এসে পৌঁছায়, আর terminal-এ <code>improt done<\/code> লেখা ওঠে — node-এর নাম তৈরি হওয়ার (L177-178) আগেই। লেখাটা sanity-check: এলে বোঝা যায় ঠিক environment-এ ঠিক package চলছে। <code>RAD2DEG<\/code> হিসেব হয় একবারই (57.29578), তারপর প্রতিটা scan-এর শত শত beam সেই এক constant দিয়েই ডিগ্রিতে যায়।","incorrect":"ভুল ধারণা: এগুলো 'নিছক import, কিছুই হয় না'। বাস্তবে L12-এর import ব্যর্থ হলে — package build করা হয়নি বা ভুল workspace source করা হয়েছে — পুরো module-ই মারা যায়, <code>main()<\/code>-এ পৌঁছায় না, <code>/cmd_vel<\/code>-এ কোনো publisher জন্মায় না; robot তখন আগের শেষ velocity-ই ধরে রাখে, কেউ থামাতে পারে না। আর wildcard import-কে হালকাভাবে নিলে <code>Bool<\/code>-এর উৎস হারিয়ে যায় — একই নামে ভিন্ন কিছু ঢুকলে সমস্যা L25-এ গিয়ে ধরা পড়ে, এই লাইনে নয়।"},"animType":null},{"n":6,"id":"part-06","fname":"laser_Avoidance.py","enTitle":"Subscriptions & Publisher","lang":"python","start":17,"end":30,"flags":[],"explain":[{"a":17,"b":18,"text":"<code>class laserAvoid(Node):<\/code> — এই folder-এর প্রাণ: একটা চালু robot-behavior class। L3-এ আনা <code>Node<\/code>-কে inherit করায় নিচের সব প্রস্তুত যন্ত্রপাতি — <code>create_subscription<\/code>, <code>create_publisher<\/code>, <code>declare_parameter<\/code> — এই class-এর হাতে এসে যায়। <code>def __init__(self,name):<\/code> — constructor-এর একটাই argument: <code>name<\/code>। মজার তথ্য: এই <code>name<\/code>-ই পরে <code>main()<\/code> থেকে আসবে (<code>laserAvoid(\"laser_Avoidance_a1\")<\/code>, L179), মানে ROS 2-এর নাম-জগতে node-এর নাম <code>laser_Avoidance_a1<\/code>, কিন্তু Python class-এর নাম <code>laserAvoid<\/code> — দুটো আলাদা জিনিস, একটাও অন্যটা থেকে আসে না। folder 08-এ robot-এর নাম URDF-এ ছিল; এখানে নামটা constructor call-এর ভেতর দিয়ে বয়ে আনা হয়।"},{"a":19,"b":19,"text":"<code>super().__init__(name)<\/code> — inheritance-এর সবচেয়ে জরুরি লাইন। এটা না চালালে <code>Node<\/code>-এর নিজের constructor কখনোই চলে না, তাই <code>self<\/code>-এর ভেতরে node-হওয়ার অভ্যন্তরীণ তালিকাই তৈরি হয় না — পরের লাইনে <code>self.create_subscription(...)<\/code> ডাকতেই <code>AttributeError<\/code> বা <code>NotInitialized<\/code>-জাতীয় error উঠে আসত। <code>super()<\/code> মানে \"আমার parent class\", এখানে <code>Node<\/code>; আর <code>name<\/code> হাতবদল করে দেওয়া মানে node-এর নাম এখানেই পাকা হয়ে যায়। ক্রমও নিয়মমাফিক: parent-এর constructor সবার আগে, তার পরে নিজের জিনিসপত্র — Python-এর inheritance-এ এটাই প্রথাগত নিয়ম।"},{"a":21,"b":22,"text":"<code># --- CREATING SUBSCRIBERS (Listeners) ---<\/code> আর <code># Listen to the 360-degree LiDAR scanner<\/code> — দুটোই comment, কিছুই চলে না; কিন্তু লেখকের নিজের শব্দচয়ন বোঝা দরকার: <b>Listeners<\/b>। প্রতিমানটা এই — publisher একটা রেডিও স্টেশন, subscription একটা শ্রোতা; শ্রোতা নিজে কিছু বলে না, শোনে আর শুনেই স্পর্শে জেগে ওঠে (callback চালায়)। এই ফাইলে দুই শ্রোতা: একটা চোখের জন্য (<code>/scan<\/code>), একটা মানুষের হাতের জন্য (<code>/JoyState<\/code>)। \"360-degree\" কথাটা এই মুহূর্তে প্রায় সত্যি — নিচে দেখা যাবে এই stream-টা আসলে folder 10-এর merger+filter chain-এর ফল, যেখানে সামনে-পেছনে দুই lidar জুড়ে পূর্ণ বৃত্ত তৈরি হয়েছিল।"},{"a":23,"b":23,"text":"<code>self.sub_laser = self.create_subscription(LaserScan,\"/scan\",self.registerScan,1)<\/code> — প্রথম শ্রোতা। চারটা argument: message-এর ধরন <code>LaserScan<\/code> (L4), topic-এর নাম <code>\"/scan\"<\/code>, কোন callback জাগবে — <code>self.registerScan<\/code> (L53-এ সংজ্ঞাত, এই ফাইলের মগজ), আর শেষের <code>1<\/code> = queue depth: পুরনো message জমিয়ে না রেখে সবসময় সবচেয়ে নতুনটাই ধরা হালকা আচরণ। <code>/scan<\/code> নামটাই সূত্রপাত-বিন্দু: এই ফাইল নিজে কোনো lidar চালায় না — folder 10-এর <code>laserscan_multi_merger<\/code> আর <code>laser_filter_node<\/code> মিলে বানানো একীভূত stream-টাই এখানে খাওয়া হয়। সেজন্যই এই ফাইলটা folder 10-এর ঠিক পরের গল্প: চোখ ওখানে, সিদ্ধান্ত এখানে।"},{"a":24,"b":25,"text":"<code># Listen to the joystick (so you can pause the AI and drive manually)<\/code> আর <code>self.sub_JoyState = self.create_subscription(Bool,'/JoyState', self.JoyStateCallback,1)<\/code> — দ্বিতীয় শ্রোতা: মানুষ। message ধরন <code>Bool<\/code> (L5-এ <code>std_msgs.msg<\/code> থেকে) — মাত্র সত্যি/মিথ্যা একটা বিট: joystick ধরা হয়েছে কি না। <code>True<\/code> এলে <code>JoyStateCallback<\/code> (L49) শুধু একটা flag উল্টে দেয়, আর <code>registerScan<\/code>-এর শুরুতেই সেই flag চেক করে <b>zero Twist<\/b> publish করে ফিরে আসে — মানে AI-এর পুরো decision tree এক বিটের কাছে হার মানে। খেয়াল করুন সাবস্ক্রিপশন-ক্রম: চোখ আগে (L23), হাত পরে — চলার ক্রমে কোনো ভূমিকা নেই, দুটোই ঠিক একইভাবে কাজ করত, ক্রমটা লেখকের পাঠের-সুবিধার পছন্দ।"},{"a":27,"b":28,"text":"<code># --- CREATING PUBLISHERS (Radio Stations) ---<\/code> আর <code># Tell the wheels to move<\/code> — আবার comment, আবার সেই প্রতিমান উল্টো দিক থেকে: শ্রোতার পাল্লায় এবার <b>রেডিও স্টেশন<\/b>। এই class-এর একটাই কথা বলার মুখ: চাকার motor driver-কে বলা <code>/cmd_vel<\/code>। প্রতিমানটা মনে রাখলে পুরো ফাইলের কঙ্কাল পরিষ্কার: <b>দুই কান ভেতরে, এক মুখ বাইরে<\/b> — <code>/scan<\/code> আর <code>/JoyState<\/code> শুনে, ঠিক একটা <code>Twist<\/code> বলে <code>/cmd_vel<\/code>-এ পাঠানো। folder 10-এ আমরা এই বাহনটা শুধু নামে চিনতাম; সেই একই <code>Twist<\/code>-ই এখানে decision tree-র প্রতিটা branch-এ ভরা হয় (L103 থেকে L163 পর্যন্ত বারবার)।"},{"a":29,"b":29,"text":"<code>self.pub_vel = self.create_publisher(Twist,'/cmd_vel',1)<\/code> — মুখ। message ধরন <code>Twist<\/code> (L4): ভেতরে <code>linear<\/code> আর <code>angular<\/code> দুই field, প্রতিটাতে x, y, z; মেঝেতে চলা robot-এর আসলে দুইটাই লাগে — <code>linear.x<\/code> (সামনে-পেছনে মিটার/সেকেন্ডে) আর <code>angular.z<\/code> (নিজের কেন্দ্র ঘিরে ঘোরা, radian/সেকেন্ডে)। queue depth আবার <code>1<\/code>: পুরনো কমান্ড জমানোর দরকার নেই, সবচেয়ে শেষ সিদ্ধান্তটাই সব। constructor-এর এই শেষ লাইন পর্যন্ত এলে node-টা হাত-পা-চোখ সব পেয়ে যায়; L31 থেকে শুরু হবে parameter-ঘোষণা — গতি আর সতর্কতার সীমা।"}],"math":null,"robot":{"correct":"laserAvoid class inherits Node and super().__init__(name) runs first; node registers two subscriptions (/scan for fused vision, /JoyState for human override) and one publisher (/cmd_vel for wheels). spin-এর পরে প্রতিটা আসা message নিজ নিজ callback-এ যায়, আর প্রতিটা callback-এর একটাই বাহির-পথ: pub_vel।","incorrect":"super().__init__(name) বাদ দিলে বা শ্রোতা-মুখ বানানোর আগে publisher ডাকলে node-টা কখনো পুরো হয় না — create_subscription একটাই error হয়ে বসে থাকবে। আরেকটা সাধারণ ভুল: merger-এর কাঁচা topic-এ কান দেওয়া — তখন পেছনের অর্ধেক খালি আসে; এই node-এর চোখ হতে হবে folder 10-এর chain-এর শেষ ফল /scan-ই।"},"animType":"subPubGraph"},{"n":7,"id":"part-07","fname":"laser_Avoidance.py","enTitle":"Four Parameters & State","lang":"python","start":31,"end":48,"flags":[],"explain":[{"a":31,"b":31,"text":"L31 হলো একটা banner comment: <code># --- ROS 2 PARAMETERS (Safety & Speed Limits) ---<\/code>। Python এই লাইনে কিছুই execute করে না, তবু এটা constructor-এর তৃতীয় block-এর সীমানা এঁকে দেয় — প্রথম block-এ L23 ও L25-এর দুটো subscription, দ্বিতীয় block-এ L29-এর <code>/cmd_vel<\/code> publisher, আর এখান থেকে শুরু হবে চারটা parameter-এর জোড়া। বিষয়টা গুরুত্বপূর্ণ এই কারণে: এই node-এর প্রতিটা সিদ্ধান্ত — কত দ্রুত এগোবে, কত জোরে ঘুরবে, কোন angle-কে সামনে ধরবে, কত কাছে বাধা পেলে সাড়া দেবে — সব দাঁড়িয়ে আছে এই চারটা সংখ্যার উপর। ROS 2-এ parameter মানে runtime-এ বদলানোর যোগ্য knob: code edit ছাড়াই <code>ros2 run<\/code> বা <code>ros2 launch<\/code>-এ <code>--ros-args -p<\/code> দিয়ে অন্য মান বসানো যায়, আর সে সুবিধা পেতেই প্রতিটা মান আগে declare করা হয়।"},{"a":32,"b":33,"text":"<code>self.declare_parameter(\"linear\",0.2)<\/code> দিয়ে node-এর parameter store-এ <code>linear<\/code> নামে একটা entry খোলা হলো, default মান 0.2 — একক meter per second, মানে সোজা এগোনোর সময় robot সেকেন্ডে 20 cm যাবে। পরের লাইনে সেই মান ফিরে পড়া হয়: <code>self.get_parameter('linear')<\/code> একটা Parameter object দেয়, <code>.get_parameter_value()<\/code> তার type-সহ value বের করে, আর শেষের <code>.double_value<\/code> সেটাকে Python float-এ ভাঙে। তিন ধাপের chain ভারী লাগলেও কারণ আছে: declare না করে <code>get_parameter<\/code> করলে ROS 2 exception ছোড়ে, আর কেউ <code>-p linear:=0.1<\/code> দিয়ে override করলে <code>self.linear<\/code>-এ ঠিক সেই overridden মানই বসবে, hardcode নয়। পরে L96 ও L163-এ এই <code>self.linear<\/code>-ই <code>twist.linear.x<\/code> হয়ে চাকায় পৌঁছাবে।"},{"a":34,"b":35,"text":"একই declare-then-get জোড়া এবার ঘূর্ণনের জন্য: <code>self.declare_parameter(\"angular\",0.2)<\/code> default 0.2 নিয়ে entry খোলে, আর পরের লাইনের তিন-ধাপের chain (<code>get_parameter<\/code>, <code>get_parameter_value<\/code>, <code>double_value<\/code>) সেটাকে <code>self.angular<\/code>-এ float হিসেবে তোলে। একক radian per second — degree নয়; এই পার্থক্য মাথায় রাখো, কারণ <code>Twist<\/code> message-এর <code>angular.z<\/code> field radian-ই চায়। L15-এর <code>RAD2DEG<\/code> দিয়ে হিসাব করলে 0.2 rad/s মানে সেকেন্ডে প্রায় 11.5 degree — বেশ ধীর, সাবধানি ঘূর্ণন। Decision tree-র প্রতিটা branch-এ এই <code>self.angular<\/code>-ই বসবে, শুধু sign বদলাবে: L97 ও L119-এ <code>-self.angular<\/code> মানে ডানে, L105 ও L132-এ <code>+self.angular<\/code> মানে বাঁয়ে ঘোরা।"},{"a":36,"b":37,"text":"তৃতীয় knob <code>LaserAngle<\/code>, default 20.0 degree। Comment বলছে এটা সামনের cone-এর চওড়া, বাঁয়ে-ডানে 20 degree করে — front zone-এর জন্য সত্যি: L68-এ <code>abs(angle) &lt; self.LaserAngle<\/code> মানে -20 থেকে +20 degree-এর ভেতরের beam সামনে গণনা হবে। কিন্তু গোপন তথ্য: একই মান side zone-এর inner edge-ও ঠিক করে — L73-এ <code>90 - self.LaserAngle<\/code> মানে 70, L78-এ <code>-(90 - self.LaserAngle)<\/code> মানে -70। একটা knob, দুটো কাজ: LaserAngle বদলালে সামনের cone-এর সাথে পাশের zone-এর সীমানাও একসাথে সরে যায়। আর সামনের অংশের author-comment (L67) বলে ±30 degree — সেটা stale; code-ই সত্যি, LaserAngle=20 মানে ±20।"},{"a":38,"b":39,"text":"চতুর্থ knob <code>ResponseDist<\/code>, default 0.3 meter, আর চেনা তিন-ধাপের chain-এ <code>self.ResponseDist<\/code>-এ float হিসেবে বসে যায়। Comment বলছে বাধা 0.3 meter-এর মধ্যে এলেই warning — কিন্তু এখানেই comment আর code আলাদা হয়ে যায়। আসল gate loop-এর ভেতরে: L69, L74, L79-এ চেক হয় <code>ranges[i] &lt;= self.ResponseDist*1.5<\/code>, মানে default-এ 0.3*1.5 = 0.45 meter। মজার ব্যাপার, L69-এর নিজের comment বলে 0.825 meter — সেটাও stale (0.55*1.5 হলে 0.825 হতো)। দুটো comment-ই ভুল, code-ই সত্যি: robot আসলে 0.45 meter-এর ভেতরের beam গুনে warning তোলে। কেন 1.5 গুণ ধরা হলো source ব্যাখ্যা করে না — সম্ভবত একটা safety margin (illustrative অনুমান মাত্র)।"},{"a":41,"b":42,"text":"<code># --- STATE TRACKERS ---<\/code> banner-টা constructor-এর চতুর্থ block শুরু করে, আর L42-এর comment বলে এরা প্রতি zone-এ কতগালো laser beam কাছাকাছি কিছুতে আঘাত করেছে তার গণনা রাখে। Parameter আর state-এর পার্থক্য এখানেই পরিষ্কার হোক: ওপরের চারটা parameter হলো configuration, জন্মের পর সাধারণত অপরিবর্তিত থাকে; নিচের পাঁচটা variable হলো ক্রমাগত বদলানো সত্য — প্রতিটা নতুন <code>/scan<\/code> message-এ (folder 10-এর merger+filter chain-এর শেষ ধারা) registerScan-এর L58-60 তিনটা counter আবার 0-এ ফেলে দেয়, তারপর per-beam loop (L63) একে একে বাড়ায়, আর সেই তিনটা সংখ্যাই decision tree-র (L94-165) একমাত্র ইনপুট। পুরো avoidance আচরণটা বলতে গেলে এই কয়েকটা integer-এর খেলা।"},{"a":43,"b":45,"text":"তিনটা counter constructor-এ 0 দিয়ে জন্ম নেয়: <code>self.Right_warning<\/code>, <code>self.Left_warning<\/code>, <code>self.front_warning<\/code>। নামকরণে অমিল লক্ষ করো — প্রথম দুটোর প্রথম অক্ষর বড় হাতের, কিন্তু <code>front_warning<\/code> ছোট হাতের; source যেমন তেমনই রাখা হয়েছে, আর পরের সব ব্যবহারেও এই বানান মানতে হবে। এই 0-মানের দুটো কাজ আছে: Python-এ attribute আগে থেকে তৈরি না থাকলে পরে পড়তে গিয়ে error আসে, তাই constructor-এ এদের অস্তিত্ব নিশ্চিত হয়; আর প্রথম <code>/scan<\/code> পৌঁছানোর আগে পর্যন্ত এদের একটা নিরাপদ শূন্য অবস্থা থাকে। তবে মনে রেখো, এই মান বেশিক্ষণ টেকে না — L58-60 প্রতি scan-এ এদের মুছে আবার 0 করে দেয়, তাই প্রতিটা counter-এর আয়ু মাত্র একটা scan।"},{"a":46,"b":46,"text":"<code>self.Joy_active = False<\/code> — চতুর্থ state variable, comment প্রশ্ন করে মানুষ কি joystick দিয়ে চালাচ্ছে? এটা boolean flag: জন্মের সময় False, মানে node উঠলেই autonomous mode সক্রিয়। একমাত্র লেখার জায়গা <code>JoyStateCallback<\/code> (L51), যেখানে <code>/JoyState<\/code> topic-এর <code>Bool<\/code> message-এর <code>msg.data<\/code> সরাসরি এতে বসে — মনে করো, <code>Bool<\/code> type-টা L12-এর wildcard import থেকে এসেছে। True হলে registerScan-এর L83-85 প্রতিটা scan-এ একটা zero <code>Twist()<\/code> publish করে সরাসরি return করে ফেলে — মানে মানুষ হাত দিলে robot থেমে যায়, AI স্থগিত। এই flag না থাকলে joystick আর AI একসাথে <code>/cmd_vel<\/code>-এ টানাটানি করত।"},{"a":47,"b":47,"text":"<code>self.conut = 3<\/code> — নামটা ভুল বানান, count হওয়ার কথা, আর source-এর নিজের comment-ই স্বীকার করে <code>(Typo for \"count\")<\/code>। কিন্তু সাবধান — এই ভুল বানান এখন load-bearing: L94 থেকে L161 পর্যন্ত প্রতিটা branch-এ <code>self.conut<\/code> হুবহু এই বানানে লেখা, তাই কোনো এক জায়গায় ঠিক করে দিলে বাকি জায়গাগুলো <code>AttributeError<\/code>-এ আটকে যাবে। মানে 3 হলো সন্দেহের সীমা: comment বলছে একটা zone-এ 3-এর বেশি beam বাধা ছুঁলে সেটাকে আসল দেয়াল ধরা হয়। পরে L91-এর comment বলবে <code>self.conut is 10<\/code> — সেটাও stale; code-ই সত্যি, মান 3, আর 3 বনাম 4-এর এই এক-বিমের পার্থক্যই পুরো decision tree-র হাত ঘুরিয়ে দেয়।"}],"math":null,"robot":{"correct":"আসল robot-এ এই চারটা সংখ্যাই আচরণের সীমা এঁকে দেয়: <code>linear<\/code> 0.2 মানে সেকেন্ডে 20 cm এগোয়, <code>angular<\/code> 0.2 rad/s মানে সেকেন্ডে মাত্র 11.5 degree ঘোরে — দুটোই ধীর, তাই ভুল সিদ্ধান্তেও ধাক্কা খাওয়ার আগে সময় থাকে। সবচেয়ে বড় সুবিধা: code ছোঁয়া ছাড়াই <code>ros2 run yahboom_M3Pro_laser laser_Avoidance --ros-args -p linear:=0.1<\/code> চালালে robot আরও সাবধানি হয়ে যায় — declare/get pattern-এর আসল ফল এটাই।","incorrect":"দুটো ভ্রান্তি বিপজ্জনক। এক: L38-এর comment পড়ে বিশ্বাস করা robot 0.3 m-এ সাড়া দেয় — আসল gate <code>ResponseDist*1.5 = 0.45 m<\/code> (L69), মানে comment-এর চেয়ে 15 cm দূর থেকেই warning ওঠে; stopping distance-এর হিসাব যেই করুক, সে ভুল জায়গায় করবে। দুই: ভাবা যে <code>LaserAngle<\/code> শুধু সামনের cone চওড়া করে — আসলে side zone-এর inner edge (90-20=70) একই মানে ঠিক হয়, তাই এটা বদলালে পাশের beam-গণনাও নীরবে বদলে যায়।"},"animType":null},{"n":8,"id":"part-08","fname":"laser_Avoidance.py","enTitle":"Joystick Callback & Scan Reset","lang":"python","start":49,"end":60,"flags":[],"explain":[{"a":49,"b":50,"text":"<code>def JoyStateCallback(self, msg):<\/code> — এই method-টাই L25-এর <code>create_subscription(Bool,'/JoyState',self.JoyStateCallback,1)<\/code>-এ register হয়েছিল; নিজে নিজে চলে না, <code>/JoyState<\/code> topic-তে নতুন <code>Bool<\/code> message এলে middleware একে call করে আর <code>msg<\/code> হিসেবে সেই message-টা পৌঁছে দেয়। এই node-এর মোট দুটো callback — এটা আর <code>registerScan<\/code> — দুটোই এক single-threaded executor-এ (<code>rclpy.spin<\/code>) পালা করে চলে, কখনো একসাথে নয়; কে আগে চলবে তা message আসার ক্রম ঠিক করে। <code>if not isinstance(msg, Bool): return<\/code> হলো defensive guard — message-টা সত্যিই <code>Bool<\/code> কিনা যাচাই করে, না হলে কিছু না করেই ফিরে যায়, তাই ভুল type-এর delivery কখনো <code>self.Joy_active<\/code> নষ্ট করতে পারে না। মনে রেখো <code>Bool<\/code> এসেছে L12-এর wildcard import <code>from yahboom_M3Pro_laser.common import *<\/code> থেকে।"},{"a":51,"b":51,"text":"<code>self.Joy_active = msg.data<\/code> — <code>Bool<\/code> message-এর আসল মান থাকে <code>.data<\/code> field-এ (একটা Python bool), আর এই এক লাইনেই সেটা <code>self.Joy_active<\/code> attribute-এ জমা হয়। লাইনের comment বলছে সেটাই: True মানে মানুষ joystick ধরে চালাচ্ছে, AI pause করবে। খেয়াল করো এই callback নিজে কিছুই publish করে না — শুধু একটা flag উল্টে দেয়; আসল stop কাজটা হয় পরের <code>registerScan<\/code> call-এ, যেখানে <code>if self.Joy_active:<\/code> শাখায় zero <code>Twist<\/code> publish করে সোজা <code>return<\/code>। তাই human override-এর প্রভাব ফুটে ওঠে পরের scan-এর সাথে সাথে, আর এখানে কোনো debouncing বা hysteresis নেই — শেষ পাঠানো <code>/JoyState<\/code> message-ই জেতে; দ্রুত flip করলে প্রতি scan-এ stop আর AI mode-এর মধ্যে দোলা লাগবে।"},{"a":53,"b":55,"text":"<code>def registerScan(self, scan_data):<\/code> — এটাই পুরো node-টার মস্তিষ্ক: L23-এ <code>/scan<\/code> subscription-এ register করা, আর সেই <code>/scan<\/code> হলো folder 10-এর merger (সামনে-পেছনের lidar এক করা) তারপর filter chain ঘুরে বেরিয়ে আসা 360-degree দূরত্বের stream — folder 11-এর launch file ঠিক এই pipeline-টাই include করে চালায়। এখানে কোনো timer বা আলাদা control loop নেই: নতুন scan এলেই সিদ্ধান্ত, সম্পূর্ণ event-driven। <code>if not isinstance(scan_data, LaserScan): return<\/code> — L50-এর guard-এরই mirror, type ভুল হলে নীরবে ফেরত। <code>ranges = np.array(scan_data.ranges)<\/code> — message-এর <code>ranges<\/code> field হলো beam-প্রতি float32 দূরত্বের sequence; NumPy array-তে wrap করলে নিচের <code>ranges[i]<\/code> indexing দ্রুত হয় আর message নিজে untouched থাকে। Folder 09-এর একক lidar-এর raw <code>/scan0<\/code>-এর মতো নয়, এটা fused data — সামনে-পেছনে সব দিকের beam।"},{"a":57,"b":60,"text":"L57-এর comment: <code># Reset the counters every time a new scan comes in<\/code> — আর এবার comment-টা সত্যি (L67 বা L91-এর মতো stale নয়), কারণ পরের তিন লাইন ঠিক সেটাই করে। <code>self.Right_warning = 0<\/code>, <code>self.Left_warning = 0<\/code>, <code>self.front_warning = 0<\/code> — constructor-এর L43-45-এ জন্মানো তিনটা counter <code>registerScan<\/code>-এর একদম শুরুতেই প্রতিবার zero। ফল: এই node-এর এই state-এর আয়ু ঠিক এক scan — গত scan-এ গোনা দেয়াল এই scan-এর count-এ মিশে যায় না, কোনো accumulation বা rolling average নেই। L94-165-এর পুরো decision tree বিচার করে কেবল বর্তমান scan-এর তাজা তিনটা সংখ্যা দিয়ে, তাই দেয়াল সরে গেলে পরের scan-এই পথ আবার পরিষ্কার দেখায়। আরেকটা সূক্ষ্ম কথা: reset আর পুরো counting ঘটে <code>Joy_active<\/code> True থাকলেও, কারণ human-override চেক (L83) আসে অনেক পরে — pause-এর সময়ের গণনাটা শেষে ফেলে দেওয়া হয়।"}],"math":null,"robot":{"correct":"Robot-এর উপর বাস্তবে এভাবে চলে: মানুষ joystick ধরলে <code>/JoyState<\/code> থেকে <code>True<\/code> আসে, আর পরের <code>registerScan<\/code> call-এ আগে তিনটা counter zero হয়, তারপর <code>if self.Joy_active:<\/code> শাখায় zero <code>Twist<\/code> publish হয় — চাকা 0 m/s আর 0 rad/s পায়, মানে মোটর কার্যত সাথে সাথে থেমে যায় আর AI সিদ্ধান্ত নেওয়া বন্ধ থাকে। joystick ছাড়ার পরের scan থেকেই zero count দিয়ে নতুন করে decision tree চলে — পুরনো কোনো warning আটকে থাকে না।","incorrect":"ভুল ধারণা: joystick-এর callback নাকি motor সরাসরি থামায়, বা দুই callback parallel চলে। আসলে <code>rclpy.spin<\/code>-এর executor single-threaded — callback গুলো queue-তে দাঁড়ায়, আর এই callback শুধু flag বদলায়; stop publish হয় পরের <code>registerScan<\/code>-এ। lidar stream থেমে গেলে বা ভুল type-এর message <code>/JoyState<\/code>-এ এলে guard নীরবে return করে আর <code>Joy_active<\/code> পুরনো মানেই থাকে: True-তে আটকে থাকলে joystick ছেড়ে দিলেও robot pause-ই থাকবে, যেন সিস্টেম জমে গেছে।"},"animType":null},{"n":9,"id":"part-09","fname":"laser_Avoidance.py","enTitle":"Beam Loop — Angle & Zones","lang":"python","start":61,"end":80,"flags":[],"explain":[{"a":62,"b":63,"text":"<code># Loop through every single laser beam (there are usually 360 or 720 of them!)<\/code> — L62-এর comment-এর 360/720 সংখ্যাটা illustrative ইঙ্গিত মাত্র; কোথাও hardcode করা নেই, আসল সংখ্যা নির্ভর করে <code>/scan<\/code> message-এর <code>ranges<\/code> array-র length-এর উপর, আর সেই fused stream বানায় folder 10-এর merger — দুটি lidar-এর scan জোড়া দিয়ে তৈরি 360-degree data। L63 <code>for i in range(len(ranges)):<\/code> — এটা value-loop নয়, index-loop: <code>i<\/code> হলো beam-এর ক্রমিক নম্বর, 0 থেকে <code>len(ranges)-1<\/code> পর্যন্ত। শুধু দূরত্ব পেলে চলত না — পরের লাইনে এই <code>i<\/code> দিয়েই হিসাব হবে beam-টা কোন দিকে তাক করা, তাই index জরুরি। প্রতিটা beam ঠিক একবার আসে, আর L80 পর্যন্ত পুরো loop-এর ভেতরেই তিনটা counter ভরে যায়।"},{"a":64,"b":65,"text":"<code># Calculate which direction (in degrees) this specific laser beam is pointing<\/code> — L64-এর comment বলে দিচ্ছে: দূরত্ব তো <code>ranges[i]<\/code>-এ আছেই, এবার দিক বের করা হবে। L65 <code>angle = (scan_data.angle_min + scan_data.angle_increment * i) * RAD2DEG<\/code> — LaserScan-এর <code>angle_min<\/code> ও <code>angle_increment<\/code> দুটো field-ই radian unit-এ থাকে (folder 09-এর echo-তে মান ছিল <code>-3.14159<\/code> আর <code>0.0174533<\/code>, মানে প্রতি beam-এ 1 degree; এই fused <code>/scan<\/code>-এর নিজের মান merger-নির্ভর, illustrative)। প্রথমে <code>angle_min + angle_increment * i<\/code> দিয়ে i-তম beam-এর radian-angle, তারপর L15-এর <code>RAD2DEG = 180 / math.pi<\/code> (প্রায় 57.29578) গুণ করে degree। ফলে <code>angle<\/code> signed: 0 মানে সোজা সামনে, positive মানে বাঁয়ে (L73), negative মানে ডানে (L78)।"},{"a":67,"b":68,"text":"<code># FRONT ZONE: If the beam is pointing near straight ahead (within +/- 30 degrees)<\/code> — L67-এর comment-টা stale: লেখক বলেছেন plus/minus 30 degrees, কিন্তু code is truth — L68-এ তুলনা চলছে <code>self.LaserAngle<\/code>-এর সাথে, যার default মান L36-এ declare হয়েছে 20.0; মানে আসল front সীমা ±20 degree। L68 <code>if abs(angle) < self.LaserAngle and ranges[i] !=0.0:<\/code> — দুটো শর্ত AND। প্রথমটায় <code>abs(angle)<\/code> negative চিহ্নটা সরিয়ে দেয়, তাই শর্তের মানে দাঁড়ায় <code>-20 < angle < 20<\/code> — খোলা interval, ঠিক ±20-এ পড়া beam front-এ গণনা পাবে না। দ্বিতীয় শর্ত <code>ranges[i] !=0.0<\/code>: lidar-এ 0.0 reading প্রায়ই no-return বা invalid মাপের চিহ্ন, তাই ঠিক 0.0 দূরত্বের beam পুরো হিসাব থেকেই বাদ; <code>inf<\/code> বা <code>NaN<\/code> আলাদা করে check করা হয়নি — তবে পরের লাইনের দূরত্বের gate-এ তাদের তুলনা ফেল করায় সেখানেই তারা আটকে যায়।"},{"a":69,"b":70,"text":"<code>if ranges[i] <= self.ResponseDist*1.5:<\/code> — L69-এর inline comment-ও ভুল: লেখা <code>closer than 0.825 meters<\/code>, অথচ <code>ResponseDist<\/code>-এর default মান L38-এ 0.3, তাই আসল gate হলো 0.3 * 1.5 = 0.45 m। 0.825 এসেছে 0.55 * 1.5 থেকে — পুরনো কোনো মানের দাগ, stale comment; আর L38-এর comment-এর 0.3 m-ও একা সত্য নয়, code সবসময় 1.5 গুণ margin রাখে। L70 <code>self.front_warning += 1<\/code> — gate পাস হলে front-এর counter এক বাড়ে। counter-গুলো L58-60-এ প্রতি scan-এর শুরুতে 0 করা হয়েছিল, কাজেই <code>front_warning<\/code>-এর মানে দাঁড়ায়: এই এক scan-এ সামনের ±20 degree-র ভেতরে কতটা beam 0.45 m-এর সমান বা কম দূরত্বে বাধা দেখেছে। এই পূর্ণসংখ্যাই পরে <code>self.conut<\/code> (=3) threshold-এর সঙ্গে তুলনা হয়ে সিদ্ধান্ত হবে।"},{"a":72,"b":73,"text":"<code># LEFT ZONE: If the beam is pointing to the left (between 60 and 90 degrees)<\/code> — L72-ও stale: লেখক বলছেন 60 আর 90 degree-এর মাঝে, কিন্তু সংখ্যাগুলো অন্য কথা বলে। L73 <code>if angle < (90 - self.LaserAngle) < 90 and angle>0 and ranges[i] !=0.0:<\/code> — মাঝখানের অংশটা Python-এর chained comparison: <code>a < b < c<\/code> লেখার মানেই <code>(a < b) and (b < c)<\/code>। মান বসালে পাওয়া যায় <code>angle < 70<\/code> (কারণ 90 - 20 = 70) এবং <code>70 < 90<\/code>; দ্বিতীয় টুকরোতে কোনো variable নেই, সবসময় True — কার্যত ফাঁকা শর্ত। বাকি থাকে <code>angle > 0<\/code> আর nonzero দূরত্ব, মানে আসল left zone <code>0 < angle < 70<\/code> — 60 থেকে 90 নয়। আরেকটা সূক্ষ্ম ব্যাপার: একই <code>LaserAngle<\/code> parameter-এর দুই চাকরি — সামনের cone-এর অর্ধ-প্রস্থ (20), আবার পাশের zone-এর ভেতরের ধারও (90 - 20 = 70); একটা knob ঘোরালে দুই জায়গার জ্যামিতি একসঙ্গে বদলায়।"},{"a":74,"b":75,"text":"<code>if ranges[i] <= self.ResponseDist*1.5:<\/code> — front zone-এর হুবহু একই দূরত্বের gate, এবার বাঁ দিকের জন্য; এখানে comment নেই কিন্তু হিসাব এক: 0.3 * 1.5 = 0.45 m। তিনটা zone তিনবার একই expression লিখেছে — অর্থাৎ বাধা মানে 0.45 m-এর ভেতরের কিছু, এই সংজ্ঞা দিক নির্বিশেষে এক; দিক শুধু কোন counter বাড়বে সেটা বেছে নেয়। L75 <code>self.Left_warning += 1<\/code> — বাঁ দিকের counter বাড়ল। কিন্তু আসল খবরটা আরও বড়: এই তিনটা zone-check হলো তিনটা স্বতন্ত্র <code>if<\/code> — কোনো <code>elif<\/code> নয়। তাই একটা beam দুই zone-এ পড়লে দুই counter-ই বাড়ে। যেমন <code>angle = +10<\/code> degree আর দূরত্ব 0.4 m (illustrative) হলে front শর্ত সত্য (<code>abs(10) < 20<\/code>), left শর্তও সত্য (<code>0 < 10 < 70<\/code>) — একই scan-এ <code>front_warning<\/code> এবং <code>Left_warning<\/code> দুটোতেই এই একটা beam গোনা হয়ে যায়: double-count।"},{"a":77,"b":78,"text":"<code># RIGHT ZONE: If the beam is pointing to the right (between -90 and -60 degrees)<\/code> — তৃতীয় stale comment: লেখা -90 থেকে -60, আসল ঘটনা L78-এ। <code>if -90 < -(90 - self.LaserAngle) < angle and angle<0 and ranges[i] !=0.0:<\/code> — chained comparison খুললে: <code>-90 < -70<\/code> (দুটোই নিছক সংখ্যা, সবসময় True) এবং <code>-70 < angle<\/code>; সঙ্গে <code>angle < 0<\/code>। কার্যত right zone = <code>-70 < angle < 0<\/code>। left-র mirror image, কিন্তু unary minus পড়া কঠিন করে দিয়েছে: <code>-(90 - self.LaserAngle)<\/code> মানে -(70) অর্থাৎ -70, আর কথা হচ্ছে <code>angle<\/code> তার চেয়ে বড় হতে হবে — মানে beam-টা -70-এর ভেতরের দিকে, সামনের দিকের দিকে ঘেঁষা। শর্তের সাজানোও উল্টো: প্রথম দুটি মিলে নিচের সীমা, তারপর <code>angle<0<\/code> উপরের সীমা; ভুল comment-এর পাশে এমন লাইনে সত্যিকারের সীমা বোঝার একটাই উপায় — নিজে সংখ্যা বসিয়ে খোলা।"},{"a":79,"b":80,"text":"<code>if ranges[i] <= self.ResponseDist*1.5:<\/code> — আরেকবার সেই এক gate, এবার ডান দিকের জন্য; তিন zone-এ তিনবার একই শর্ত লেখা, কোনো helper function বানানো হয়নি — source যেমন আছে আমরা তেমনই পড়ছি। L80 <code>self.Right_warning += 1<\/code> — ডান দিকের counter বাড়ল। L63 থেকে L80: প্রতিটা beam এই তিনটা check পেরিয়ে যায়, আর loop শেষে তিনটা পূর্ণসংখ্যা দাঁড়িয়ে যায় — সেগুলোই L94 থেকে শুরু হওয়া decision tree-র একমাত্র input। শেষ কথা সীমানার: সব inequality strict, তাই <code>angle<\/code> ঠিক 0 হলে beam কেবল front-এর (left চায় >0, right চায় <0), আর ঠিক +70 বা -70 হলে কোনো zone-ই পায় না — সেই beam কোনো counter-এ গণনা হয় না, নীরবে হিসাবের বাইরে থেকে যায়।"}],"math":{"blocks":[{"latex":"\\[ \\theta_i = \\left(\\theta_{\\min} + i \\cdot \\Delta\\theta\\right) \\cdot \\frac{180}{\\pi} \\approx -180^{\\circ} + i \\cdot 1^{\\circ} \\]","text":"L65-এর হিসাবের বীজগণিত। LaserScan-এর <code>angle_min<\/code> ও <code>angle_increment<\/code> থাকে radian unit-এ, তাই degree পেতে <code>RAD2DEG = 180 / math.pi<\/code> (প্রায় 57.29578) দিয়ে গুণ। folder 09-এর echo-তে মান ছিল angle_min = -3.14159 আর increment = 0.0174533 (মানে pi/180, প্রতি beam-এ ঠিক 1 degree) — সেই মানে হলে i-তম beam-এর দিক দাঁড়ায় -180 + i degree। <code>i<\/code> শুধু array-র index, কিন্তু এই সূত্র তাকে জ্যামিতিক দিকে বদলে দেয় — পরের তিনটা zone-check সেই দিকের উপরেই দাঁড়িয়ে।"},{"latex":"\\[ \\text{front: } |\\theta| < 20 \\;\\wedge\\; d_i \\ne 0.0 \\;\\wedge\\; d_i \\le 1.5 \\times 0.3 = 0.45\\,\\mathrm{m} \\]","text":"front zone-এর পূর্ণ শর্ত তিনটা টুকরোর AND। <code>abs(angle) < self.LaserAngle<\/code> মানে -20 < theta < 20 — খোলা interval, L67-এর comment-এর ±30 নয় (stale)। দূরত্বের দুই শর্ত একসঙ্গে বলছে: মান 0.0 নয়, এবং 0.45 m বা তার কম — কারণ <code>self.ResponseDist * 1.5<\/code> = 0.3 * 1.5 = 0.45; L69-এর comment-এর 0.825 এসেছে পুরনো 0.55 মানের দাগ থেকে। অর্থাৎ সামনে সতর্ক হওয়ার বাধা মানে আধ মিটারেরও কম দূরত্বে কিছু ধরা পড়া।"},{"latex":"\\[ \\theta < (90-20) < 90 \\quad\\text{means}\\quad (\\theta < 70) \\wedge (70 < 90) \\quad\\text{so}\\quad 0 < \\theta < 70 \\]","text":"L73-এর chained comparison খোলা রূপে। Python-এ <code>a < b < c<\/code> লেখার মানেই <code>(a < b) and (b < c)<\/code> — গণিতের প্রথার মতোই। মান বসালে প্রথম টুকরো angle < 70 (কারণ 90 - LaserAngle = 90 - 20 = 70), দ্বিতীয় টুকরো 70 < 90 — এতে কোনো variable নেই, তাই সবসময় সত্য, শর্ত হিসেবে অকেজো। কার্যকর শর্ত কেবল angle > 0-টাই। সুতরাং আসল left zone খোলা interval (0, 70) — L72-এর comment-এর 60 আর 90 কোনোটাই প্রকৃত সীমা নয়; আবারও code is truth।"},{"latex":"\\[ -90 < -(90-20) < \\theta \\quad\\text{means}\\quad (-90 < -70) \\wedge (-70 < \\theta) \\quad\\text{so}\\quad -70 < \\theta < 0 \\]","text":"L78-এর right zone একই কৌশলে খোলা। <code>-(90 - self.LaserAngle)<\/code> মানে -(70) অর্থাৎ -70, তাই chained অংশ দাঁড়ায় -90 < -70 (দুটোই নিছক সংখ্যা, সবসময় সত্য) এবং -70 < angle। সঙ্গে <code>angle < 0<\/code> শর্তটা নিলে পুরো zone = (-70, 0)। L77-এর comment বলে -90 থেকে -60 — বাস্তবের সঙ্গে মেলে না। লক্ষ করুন, left আর right মিলে সামনের 140 degree জুড়ে তিনটা zone, আর |theta| > 70 হলে বা পেছনের 180 degree-তে beam পড়লে কোনো counter-ই বাড়ে না — সেই দিক এই node-এর কাছে অন্ধ।"},{"latex":"\\[ (-20,\\,20) \\cap (0,\\,70) = (0,\\,20) \\qquad (-20,\\,20) \\cap (-70,\\,0) = (-20,\\,0) \\]","text":"তিনটা শর্তই স্বতন্ত্র <code>if<\/code>, <code>elif<\/code> নয়, তাই zone-গুলোর overlap কেউ আটকায়নি। front (-20, 20) আর left (0, 70)-এর সাধারণ অংশ (0, 20): এই দিকের কোনো beam 0.45 m-এর ভেতরে বাধা পেলে একই scan-এ <code>front_warning<\/code> ও <code>Left_warning<\/code> দুটোই বাড়ে। ডান পাশে সেই একই ঘটনা (-20, 0) অংশে। ফলে সামনে সামান্য বাঁ-ঘেঁষা একটা বাধাও left-এর দেয়াল হিসেবে গোনা হয়ে যেতে পারে, আর decision tree সেই ফোলা counter-ই দেখে। এক beam-এর দুইবার গণনা এখানে geometry-ই বাধ্য করছে — zone-এর সংজ্ঞাই এমন।"}]},"robot":{"correct":"আসল robot-এ প্রতিটা scan-এ এই loop চালু হয়: folder 10-এর merger+filter-এর বানানো 360-degree <code>/scan<\/code>-এর প্রতিটা beam-এর দিক আর দূরত্ব মিলিয়ে তিনটা counter ভরে যায়, তারপরই decision tree। সামনে ±20 degree-তে 0.45 m-এর ভেতরে বাধা মানে <code>front_warning<\/code> বাড়ছে; বাঁ-য়ে 0 থেকে 70, ডানে -70 থেকে 0। সীমানার কাছের বাধা দুই counter-এ পড়ায় robot সামান্য পাশে-সরা বাধাকেও দ্রুত দেয়াল ভেবে ঘুরতে পারে। counter প্রতি scan-এ reset হয়, তাই প্রতিক্রিয়ার delay মোটামুটি এক scan period।","incorrect":"বিপদ হলো comment-এর অংক বিশ্বাস করা: যে ভাববে trigger প্রায় ±30 degree আর 0.825 m দূরত্বে, তার চোখে robot অকারণে আগেভাগে ঘুরবে — কারণ আসল zone ±20 degree, আসল gate 0.45 m। দ্বিতীয় ভুল: তিনটা zone-কে পরস্পরছিন্ন ভাবা। +10 degree-র একটা কাছের beam একই scan-এ <code>front_warning<\/code> ও <code>Left_warning<\/code> দুটোই বাড়ায়, ফলে মাত্র 4-5টা beam-এর সামনের পাতলা বাধাও <code>Left_warning<\/code>-কে 3-এর সীমা ছাড়াতে পারে — robot-এর বিবেচনায় সেটা তখন দেয়াল, আর সে অপ্রয়োজনে ঘুরে যায়।"},"animType":"beamSweep"},{"n":10,"id":"part-10","fname":"laser_Avoidance.py","enTitle":"Human Override — Full Stop","lang":"python","start":82,"end":87,"flags":[],"explain":[{"a":82,"b":83,"text":"<code># If a human is driving, stop the AI and do nothing<\/code> — L82-এর comment এই block-এর নীতি বলে দিচ্ছে: মানুষ joystick ধরলে AI নিজের ইচ্ছা চালাবে না। <code>if self.Joy_active:<\/code> শুধু একটা boolean flag পরীক্ষা করছে, কিন্তু flag-টার জন্ম এখানে নয় — <code>/JoyState<\/code> topic-এর <code>JoyStateCallback<\/code> (L49-51) থেকে <code>msg.data<\/code> এসে সরাসরি এখানে বসে। খেয়াল রাখুন, এই পরীক্ষাটা হচ্ছে পুরো beam-counting loop (L63-80) শেষ হওয়ার পরে: মানুষ drive করুক বা না-ই করুক, তিনটা warning counter আগে গুনে ফেলা হয়, তারপর সেই হিসাব বাদ দিয়ে এই জায়গায় এসে সিদ্ধান্ত প্রক্রিয়া আটকে দেওয়া হয়। Single-threaded executor একসাথে দুটো callback চালায় না, তাই flag পড়ার সময়ে কোনো race হয় না।"},{"a":84,"b":85,"text":"<code>self.pub_vel.publish(Twist())<\/code> — override-এর আসল কাজ এই এক লাইনে। খালি <code>Twist()<\/code> constructor ছয়টা field-ই (linear-এর তিনটা, angular-এর তিনটা) 0.0 দিয়ে ভরে দেয়, আর সেই শূন্য message যায় <code>/cmd_vel<\/code>-এ — L29-এ বানানো <code>self.pub_vel<\/code> publisher দিয়েই। স্বাভাবিক প্রশ্ন: শুধু <code>return<\/code> করলেই তো AI চুপ হয়ে যেত, publish কেন দরকার? কারণ wheel driver সবসময় শেষ পাওয়া command-ই মেনে চলে — নতুন message না এলে আগেরটা নিজে নিজে বাতিল হয় না। Human takeover-এর ঠিক আগের scan-এ কোনো branch যদি 0.2 m/s forward পাঠিয়ে থাকে, publish ছাড়া ফিরে গেলে সেই গতিই কার্যকর থেকে যেত। প্রতি scan শূন্য পাঠানোয় takeover-এর প্রথম scan-তেই আগের command মুছে যায়, আর প্রতিটা নতুন scan সেই থামা-অবস্থা আবার জানিয়ে দেয় — একবারের one-shot publish-এর চেয়ে এটা অনেক বেশি নিরাপদ।"},{"a":86,"b":87,"text":"L86 ফাঁকা লাইনটা দুই জগতের সীমানা: উপরে human override block, নিচে AI-র নিজের সিদ্ধান্তের জায়গা। <code>twist = Twist()<\/code> চলতে পারলে বোঝা যায় <code>Joy_active<\/code> False — মানুষ হাত ছেড়েছে, বা শুরু থেকেই ধরেইনি। প্রতি scan-এর জন্য একদম টাটকা একটা Twist object বানানো হচ্ছে, কারণ নিচের decision tree (L94-165) এই খালি container-টাকেই ভরবে। লক্ষ করুন, পুরো tree জুড়ে শুধু <code>twist.linear.x<\/code> আর <code>twist.angular.z<\/code> ছোঁয়া হয় — বাকি চারটা field এই সম্পূর্ণ program-এ কোথাও সেট-ই হয় না, 0.0-ই থেকে যায়। নতুন object বানানোটা ছোট কিন্তু জরুরি অভ্যাস: আগের scan-এর কোনো branch যা বসিয়েছিল তা এই scan-এ চুপিচুপি ঢুকে পড়তে পারত — টাটকা object-এ সেই সুযোগটাই বন্ধ।"}],"math":null,"robot":{"correct":"Real robot-এ joystick-এর নিয়ন্ত্রণ ধরা মাত্র <code>/JoyState<\/code> message-এ <code>Joy_active<\/code> True হয়ে যায়, আর তখন থেকে প্রতিটা scan-এ <code>/cmd_vel<\/code>-এ শূন্য Twist যেতে থাকে। Motor driver শেষ command ধরে রাখে বলে এই repeated শূন্যগুলোই কার্যকর brake — takeover-এর আগের মুহূর্তের 0.2 m/s forward বা কোনো কড়া মোড় আর চলতে পারে না। <code>return<\/code> থাকায় sleep-যুক্ত কোনো branch-এ ঢোকা পর্যন্ত হয় না, তাই মানুষের চালনার মাঝে AI-র কোনো বিলম্বিত মুভমেন্টও প্রবেশ করতে পারে না।","incorrect":"প্রচলিত ভুল ধারণা: human override মানে callback-কে চুপ করানো, অর্থাৎ শুধু <code>return<\/code> করলেই robot থেমে যাবে। বাস্তবে publish না করলে wheel driver শেষ AI command-ই ধরে রাখে — মানুষ joystick হাতে রেখেই robot আগের scan-এর বলা গতিতে এগোতে বা ঘুরতে থাকত। আরেকটা ভুল: takeover শনাক্ত হলে একবারই শূন্য publish করলে যথেষ্ট ভাবা — এখানে প্রতি scan বারবার শূন্য পাঠানো হয়, কারণ একটা message হারালে বা race করলে one-shot থেমে থাকার নিশ্চয়তাই হারিয়ে যেত।"},"animType":null},{"n":11,"id":"part-11","fname":"laser_Avoidance.py","enTitle":"Decision Tree — Trapped Branch","lang":"python","start":89,"end":99,"flags":[],"explain":[{"a":89,"b":90,"text":"L89-90 হলো banner comment — <code># --- THE GIANT DECISION TREE ---<\/code> আর তার ব্যাখ্যা-লাইন: তিন zone-এর count থেকেই এবার সিদ্ধান্ত। উপরের <code>for<\/code> loop (L63-80) শেষে তিনটা integer রেডি — <code>front_warning<\/code>, <code>Left_warning<\/code>, <code>Right_warning<\/code> — প্রতিটা বলে সেই zone-এ কয়টা beam 0.45 m gate-এর ভেতরে আটকেছে। এবার শুরু এই file-এর মূল ইঞ্জিন: লম্বা একটা <code>if/elif<\/code> ladder, প্রতিটা branch তিন count-এর একটা combination পরীক্ষা করে ঠিক করে robot কোথায় যাবে। প্রতি scan-এ ঠিক একটা branch জেতে, সেটাই L87-এর <code>twist<\/code> object-এ মান ভরে দেয়। Folder 09-10 ছিল data-র গল্প — single lidar-এর <code>/scan0<\/code>, তারপর merger+filter-এর fused <code>/scan<\/code>; এই লাইন থেকে সেই data প্রথমবার behavior হয়ে ওঠে।"},{"a":91,"b":91,"text":"L91-এর comment নিজেই একটা বড় শিক্ষা: <code># (self.conut is 10. So > self.conut means \"a wall is there\", ...)<\/code> — comment অনুযায়ী মান 10 হওয়ার কথা, অথচ L47-এ <code>self.conut = 3<\/code> set হয়েছে। Code is truth: মান 3, তাই কোনো zone-এ 4টা বা বেশি near beam থাকলেই এই code সেটাকে wall ভাবে, আর 3 বা তার নিচে হলে clear — comment-এর বাকি অংশেও তাই বলা: সমান-বা-কম মানে path clear। নামটাও typo — <code>conut<\/code>, \"count\" হওয়ার কথা, L47-এর comment সেটাও স্বীকার করে। এই ছোট্ট variable-টাই নিচের পুরো ladder-এর অভিধান: প্রতিটা branch তিনটা warning counter-কে ঠিক <code>self.conut<\/code>-এর সাথে তুলনা করে। তাই এখানে 10 ধরে পড়লে হিসাব পুরো ভুল হয় — 5-beam-এর দেয়াল আসলে branch জেতে, ভুল পাঠে সেটা এখনো clear মনে হবে।"},{"a":93,"b":94,"text":"L93-এর comment পরিস্থিতির নাম দিয়েছে: <code># 1. Blocked in front, left, AND right! (Trapped)<\/code>, আর শেষে লেখা আছে <code>Back up and turn right<\/code> — অর্থাৎ তিনদিকই বন্ধ হলে পিছিয়ে যাওয়ার পরামর্শ। L94 সেই পরীক্ষা: <code>if self.front_warning > self.conut and self.Left_warning > self.conut and self.Right_warning > self.conut:<\/code> — তিনটা strict comparison <code>and<\/code> দিয়ে জোড়া, তিনটাই সত্য হলেই branch জেতে। <code>conut<\/code> = 3 হওয়ায় মানে দাঁড়ায়: front, left, right প্রতিটা zone-এই কমপক্ষে 4টা beam 0.45 m-এর মধ্যে। এটাকে ladder-এর একদম প্রথমে রাখা অর্থবহ — উপর থেকে নিচে মেলানো হয়, আর trapped সবচেয়ে বিপজ্জনক state বলে সবার আগে ছাঁকা হয়। মনে রেখো zone-গুলো overlap করে (front -20 থেকে +20, left 0-70, right -70 থেকে 0 degree), তাই একটা বড় বাধাই একাধিক counter একসাথে বাড়াতে পারে।"},{"a":95,"b":95,"text":"L95: <code>print ('1, there are obstacles in the left and right, turn right')<\/code> — branch জিতলেই terminal-এ এই লাইন বসে; node তো <code>ros2 run yahboom_M3Pro_laser laser_Avoidance<\/code> দিয়ে চলে, তাই console-ই বাইরের একমাত্র জানালা। Message-এ নিজের একটা অসঙ্গতি আছে: condition-এ front, left, right তিনটাই, অথচ message শুধু \"left and right\" বলছে — আসল state টা trapped, শুধু নাম্বার <code>1<\/code> সেটা মনে করায়। এই print-ই decision tree-এর live trace: পরের branch-গুলোও 2, 4, 6, 7, 8, 9, 10 নাম্বার ছাপে (3 আর 5 comment-এই নেই, source যেমন)। Motion-এর সাথে print-এর কোনো সম্পর্ক নেই — এটা শুধু মানুষের জন্য; কিন্তু debug-এ দরকারি: কোন branch কত ঘন ঘন জিতছে তা এখান থেকেই বোঝা যায়।"},{"a":96,"b":96,"text":"L96 এই folder-এর সবচেয়ে আলোচিত লাইন: <code>twist.linear.x = self.linear<\/code>। <code>self.linear<\/code> এসেছে L32-33-এর parameter থেকে, ডিফল্ট <code>0.2<\/code> m/s, আর ROS convention-এ <code>Twist<\/code>-এর ধনাত্মক <code>linear.x<\/code> মানে সামনে যাওয়া — অর্থাৎ তিনদিক বন্ধ trapped অবস্থায় robot-কে গেল সামনে এগোনোর আদেশ! Source-এর নিজের inline comment-ই স্বীকার করে: <code># Drive forward to push through? (Actually, this is a bit of a code bug, it should be negative to reverse, but we follow the original logic)<\/code> — ইচ্ছা ছিল <code>-self.linear<\/code> দিয়ে পিছনে নেওয়া, কিন্তু original logic অনুসরণ করে ধনাত্মকই রাখা হয়েছে। খেয়াল রাখো: CLI বা launch থেকে parameter override করে 0.2 বদলালে শুধু মান বদলায়, sign নয় — bug টা মানেতে না, sign-এ।"},{"a":97,"b":99,"text":"L97: <code>twist.angular.z = -self.angular<\/code> — <code>self.angular<\/code> ডিফল্ট <code>0.2<\/code> rad/s (L34-35), ঋণাত্মক <code>angular.z<\/code> মানে clockwise অর্থাৎ ডানে ঘোরা; comment-ও বলছে <code># Turn right<\/code>। L98: <code>self.pub_vel.publish(twist)<\/code> — L29-এ বানানো publisher <code>/cmd_vel<\/code> topic-এ message ছাড়ে, wheel-এর base controller সেখান থেকেই আদেশ পায়; L96-97-এর আদেশ এখনই কার্যকর: সামনে +0.2 m/s, ডানে -0.2 rad/s, মানে একটা forward-right arc। L99: <code>sleep(0.2)<\/code> — 0.2 second ব্লক করে বসে থাকা। <code>rclpy.spin<\/code> (L181) single-threaded, তাই এই সময় নতুন <code>registerScan<\/code> চলবে না; scan-গুলো queue-তে জমবে, কিন্তু L23-এর QoS depth 1 থাকায় পুরনোগুলো বাদ পড়ে শুধু সর্বশেষটা থাকবে — sleep শেষে সিদ্ধান্ত হবে freshest data দিয়েই।"}],"math":{"blocks":[{"latex":"\\[ d_{\\max} = 0.3 \\times 1.5 = 0.45\\ \\mathrm{m}, \\qquad \\text{wall: } n \\ge 4, \\qquad \\text{clear: } n \\le 3 \\]","text":"প্রতিটা beam হলো একটা ভোট, আর ভোটের যোগ্যতা হলো দূরত্বের gate — <code>ResponseDist*1.5 = 0.3*1.5 = 0.45 m<\/code>-এর মধ্যে beam আটকেছে কি না (L69, L74, L79 একই gate ব্যবহার করে)। একটা stray reading-এ রায় বদলায় না: দরকার <code>conut<\/code> পার করা। কিন্তু comparison strict, তাই 3-এ থাকলে এখনো clear, 4-এ পৌঁছালেই zone-টা wall। ডিফল্ট মানে wall-এর সংজ্ঞা দাঁড়ায়: ঐ দিকে কমপক্ষে 4টা beam 0.45 m-এর মধ্যে। 3 আর 4-এর মাঝের এই এক-বিমের ব্যবধানই নিচের প্রতিটা branch-এর রায় নিয়ন্ত্রণ করে।"},{"latex":"\\[ B_1 \\equiv (F > 3) \\,\\land\\, (L > 3) \\,\\land\\, (R > 3), \\qquad \\text{i.e. } F \\ge 4, \\ L \\ge 4, \\ R \\ge 4 \\]","text":"Branch 1-এর শর্ত তিনটা strict inequality-র conjunction — front, left, right প্রতিটা counter আলাদাভাবে 4-এ বা উপরে। সূক্ষ্ম ফাঁদ: zone overlap করে — front হলো -20 থেকে +20 degree, left 0-70, right -70 থেকে 0। তাই +10 degree-এর একটা near beam একই scan-এ <code>front_warning<\/code> আর <code>Left_warning<\/code> দুটোই বাড়ায় (L68 আর L73 দুটোই মেলে)। ফলে B1-এর জন্য 12টা আলাদা beam-দিক লাগে না: সামনের একটাই চওড়া wall, যদি -70 থেকে +70 degree জুড়ে 0.45 m-এর মধ্যে থাকে, তিনটা counter-ই একসাথে ভরে যেতে পারে। Trapped রায় তাই ঘিরে ফেলাও হতে পারে, আবার শুধু সামনের বিশাল বাধাও।"},{"latex":"\\[ x_{\\mathrm{cmd}} = +0.2\\ \\mathrm{m/s}, \\qquad x_{\\mathrm{intended}} = -0.2\\ \\mathrm{m/s}, \\qquad r = \\left| \\frac{v}{\\omega} \\right| = \\frac{0.2}{0.2} = 1\\ \\mathrm{m} \\]","text":"L96-এর sign bug-এর হিসাব। Commanded মান <code>+self.linear = +0.2<\/code> m/s সামনে; comment বলে ইচ্ছা ছিল <code>-self.linear = -0.2<\/code> m/s, অর্থাৎ reverse। সাথে L97-এর <code>angular.z = -0.2<\/code> rad/s থাকায় সম্মিলিত আদেশ দাঁড়ায় একটা forward-right arc, যার ব্যাসার্ধ হলো velocity আর angular rate-এর অনুপাত: 0.2 ভাগ 0.2 মানে 1 m। Trapped robot তাই বেরোনোর বদলে চারপাশের বাধার দিকেই 1 m ব্যাসার্ধের পথে ঢুকে পড়ে। Parameter দিয়ে linear বদলালে r বদলায়, কিন্তু সামনে-যাওয়ার sign বদলায় না।"},{"latex":"\\[ (F = 3) \\land (L > 3) \\land (R > 3) \\quad : \\quad \\text{branch 1, 7, 10 all false, no publish} \\]","text":"Ladder-এর guard-গুলোতে তিন রকম comparison মেশানো: branch 1, 2, 4, 6 চায় front কঠোরভাবে 3-এর বড়; branch 7, 8, 9 চায় কঠোরভাবে ছোট; branch 10 চায় তিনটাই 3 বা নিচে। Front ঠিক 3 হলে বড়ও না ছোটও না — শুধু branch 10-এর দরজা খোলা, কিন্তু সেখানে left আর right-ও 3 বা নিচে চাই। তাই tuple (F=3, L=5, R=5) কোনো branch-ই মেলে না: সেই scan-এ একটাও publish হয় না, <code>/cmd_vel<\/code>-এ আগের আদেশ ঝুলে থাকে, robot বাসি গতিতেই চলতে থাকে। Counter ছোট পূর্ণসংখ্যা হওয়ায় F=3 খুবই স্বাভাবিক — একটা beam কমবেশি হলেই রায় পাল্টায়।"},{"latex":"\\[ \\Delta\\theta = 0.2\\ \\mathrm{rad/s} \\times 0.2\\ \\mathrm{s} = 0.04\\ \\mathrm{rad} \\approx 2.3^{\\circ} \\]","text":"L99-এর <code>sleep(0.2)<\/code>-এর হিসাব। Single-threaded <code>rclpy.spin<\/code>-এর ভিতরে callback ব্লক হওয়ায় এই 0.2 second-এ নতুন <code>registerScan<\/code> চলে না — সময়টা আসলে আদেশ কার্যকর হওয়ার জন্য: -0.2 rad/s হারে 0.2 s মানে commanded ঘূর্ণন 0.04 rad, প্রায় 2.3 degree (মান দুটো source-এর ধ্রুবক থেকে হিসাব; আসল ঘূর্ণন base controller-নির্ভর)। Sleep শেষে queue-তে অনেক scan জমার প্রবণতা, কিন্তু L23-এর QoS depth 1 থাকায় শুধু সর্বশেষটা বাঁচে — পরের সিদ্ধান্ত freshest data দিয়েই হয়, পুরনো scan একে একে আর প্রক্রিয়া হয় না।"}]},"robot":{"correct":"আসল robot-এ এই branch যখন জেতে যে তিনটা zone-এই কমপক্ষে 4টা beam 0.45 m-এর মধ্যে (যেমন কোণে আটকে গিয়ে), তখন L98-এর publish করা আদেশ হলো সামনে +0.2 m/s আর ডানে -0.2 rad/s — ব্যাসার্ধ 1 m-এর একটা forward-right arc। L99-এর <code>sleep(0.2)<\/code> আদেশটাকে কার্যকর হওয়ার সময় দেয়: এই সময়ে commanded ঘূর্ণন প্রায় 0.04 rad বা 2.3 degree। Single-threaded executor থামলেও QoS depth 1 নিশ্চিত করে পরের সিদ্ধান্ত সবচেয়ে নতুন scan দিয়েই হবে। Terminal-এ <code>print ('1, ...')<\/code>-ও বসে।","incorrect":"সবচেয়ে বিপজ্জনক ভুল ধারণা: comment পড়ে ভাবা যে trapped অবস্থায় robot পিছাবে, কারণ L93 শেষে লেখা <code>Back up and turn right<\/code>। আসলে L96-এ <code>twist.linear.x = self.linear<\/code> মানে +0.2 m/s সামনে — source-এর নিজের comment-ই বলছে এটা code bug, হওয়া উচিত ছিল negative। ফলে তিনদিক বন্ধ অবস্থায় robot বাধার দিকেই এগিয়ে যায়, wheel আর chassis-এ চাপ পড়ে। দ্বিতীয় ফাঁদ: L91-এর comment অনুযায়ী conut = 10 ধরা — আসলে 3, তাই মাত্র 4টা beam-ই wall বানায়।"},"animType":"decisionTree"},{"n":12,"id":"part-12","fname":"laser_Avoidance.py","enTitle":"Branches 2, 4, 6 — Turn Away","lang":"python","start":101,"end":134,"flags":[],"explain":[{"a":101,"b":102,"text":"<code># 2. Blocked in front and right, but LEFT is clear<\/code> — এই comment-টি সত্য (L67 বা L69-এর মতো stale নয়), কারণ নিচের শর্তই ঠিক সেটাই যাচাই করছে। <code>elif<\/code> মানে এটি তখনই চলবে যখন L94-এর branch 1 False হবে — chain-এর ক্রম জরুরি। শর্তের তিনটি অংশ: <code>front_warning > self.conut<\/code> মানে সামনে 3-এর বেশি beam 0.45 m gate-এর ভেতরে, <code>Left_warning <= self.conut<\/code> মানে বাঁ দিক ফাঁকা, <code>Right_warning > self.conut<\/code> মানে ডানে বাধা। এই count-গুলোর উৎস folder 10-এর merger+filter চেইন থেকে আসা fused <code>/scan<\/code> — সিদ্ধান্তের চোখ আসলে পুরো fusion pipeline-এর ওপরেই দাঁড়িয়ে।"},{"a":103,"b":104,"text":"<code>print ('2, there is an obstacle in the middle right, turn left')<\/code> — terminal-এ 2 নম্বর দেখলেই বুঝবেন এই branch সিদ্ধান্ত নিয়েছে; প্রতিটি branch-এ এমন আলাদা বার্তা আছে, ডিবাগের সময় এটাই দ্রুততম সূচক। লক্ষ করুন branch-এর নম্বর চলছে 1, 2, 4, 6, 7, 8, 9, 10 — 3 আর 5 কোথাও নেই; author-এর গণনায় দুটি নম্বর বাদ, আমরা source-কে as-is পড়ি, নিজে থেকে ঠিক করে ফেলি না। <code>twist.linear.x = 0.0<\/code> (comment: Stop forward motion) সামনের গতি শূন্য করছে — obstacle-এর দিকে এগোনো বন্ধ। ফলে এই branch-এর মুভ pure rotation: শরীর একই জায়গায় রেখে শুধু ঘুরবে, সরু ফাঁকা পথ খুঁজতে এটাই নিরাপদ প্রথম পদক্ষেপ।"},{"a":105,"b":107,"text":"<code>twist.angular.z = self.angular<\/code> — চিহ্নের নিয়মটা মুখস্থ করুন: ROS-এ <code>angular.z<\/code> ধনাত্মক মানে counterclockwise বাঁ দিকে (z-অক্ষ উপরে ধরে right-hand rule), ঋণাত্মক মানে clockwise অর্থাৎ ডানে। <code>self.angular<\/code> = 0.2, তাই বাঁয়ে ঘোরা — comment-ও বলছে Turn left। <code>self.pub_vel.publish(twist)<\/code> — এই Twist message গেল <code>/cmd_vel<\/code> topic-এ, যেখানে wheel driver শোনে; publisher টি L29-এ depth 1 নিয়ে তৈরি হয়েছিল। তারপর <code>sleep(0.2)<\/code> — callback-এর ভেতরে 0.2 s ব্লক; single-threaded <code>spin<\/code> হওয়ায় এই সময়ে নতুন <code>registerScan<\/code> ঢুকতে পারে না, আর QoS depth 1-এর জন্য জমানো scan-এর মধ্যে শুধু সর্বশেষটিই টিকে থাকে — sleep শেষে সিদ্ধান্ত হবে সবচেয়ে নতুন তথ্যে।"},{"a":108,"b":109,"text":"Comment বলছে <code>Double-check logic: If left is now blocked but right is clear, turn right instead<\/code> — author ভেবেছিলেন robot ঘুরে গিয়ে আবার তাকাবে। কিন্তু <code>if self.Left_warning > self.conut and self.Right_warning <= self.conut:<\/code> লাইনে বৈপরীত্য লুকিয়ে আছে: L102-এর guard নিশ্চিত করেই দিয়েছে <code>Left_warning <= 3<\/code>, আর এই inner if চায় <code>Left_warning > 3<\/code> — একই callback-এ দুটো একসাথে অসম্ভব। Counter-গুলো L58-60-এ reset হয়ে L63-80-এর loop-এ জমে, এরপর আর বদলায় না; <code>sleep<\/code>-এর ভেতরে নতুন scan ঢুকতে পারে না, ঢুকলেও পরের <code>registerScan<\/code> শুরু থেকে পুরো tree আবার চালাত — L109-এ কখনো ফেরত আসার পথ নেই। তাই এই শর্ত কার্যত dead code।"},{"a":110,"b":113,"text":"এই চার লাইন বাস্তবে কখনো চলবে না, তবু পড়া দরকার — author-এর ইচ্ছাটা এখানেই লেখা। <code>twist.linear.x = 0.0<\/code> আবার শূন্য, <code>twist.angular.z = -self.angular<\/code> — ঋণাত্মক মানে ডানে ঘোরা: প্রথমে বাঁয়ে ঘুরিয়ে দেওয়ার পর যদি হঠাৎ বাঁ দিক ব্লক আর ডান ফাঁকা দেখা যেত, তাহলে উল্টো দিকে শোধরানোর পরিকল্পনা। <code>self.pub_vel.publish(twist)<\/code> আগের left-turn command-এর ওপর নতুন right-turn command লিখে দিত, তারপর <code>sleep(0.5)<\/code> — branch-এর শুরুর 0.2 s-এর চেয়ে দেড় গুণ লম্বা অপেক্ষা। শর্ত যেহেতু কখনো মেলে না, পুরো block অকেজো থাকে — code is truth নিয়মে আমরা source-কে যেমন আছে তেমনই শিখি, নিজে থেকে ঠিকও করি না।"},{"a":115,"b":117,"text":"Branch 4 হলো branch 2-এর আয়না-চিত্র। <code>elif<\/code> — তাই এটি তখনই মূল্যায়ন হবে যখন branch 1 (L94) এবং branch 2 (L102) দুটোই False। শর্ত: <code>front_warning > self.conut<\/code> সামনে বাধা, <code>Left_warning > self.conut<\/code> বাঁয়েও বাধা, <code>Right_warning <= self.conut<\/code> ডান দিক ফাঁকা — অর্থাৎ সামনে-বাঁয়ে দেয়াল, একমাত্র বাঁচার পথ ডান দিক। <code>print ('4. There is an obstacle in the middle left, turn right')<\/code> — এখানেও 4-এর পরে 6, মাঝের 3 আর 5 নেই। Comment-টি সঠিক। দুই branch-এর গঠন প্রায় একই; তফাত শুধু কোন পাশ block আর কোনটা clear — এবং সেই অনুযায়ী ঘোরার দিক ও <code>angular.z<\/code>-এর চিহ্ন উল্টে যায়।"},{"a":118,"b":121,"text":"<code>twist.linear.x = 0.0<\/code> — সামনের গতি শূন্য, মুভ pure rotation। <code>twist.angular.z = -self.angular<\/code> — ঋণাত্মক, মানে clockwise অর্থাৎ ডানে pivot (comment: Turn right)। খেয়াল করুন <code>twist<\/code> object-টি L87-এ জন্মেছিল এবং branch 2 সেটিই পুনর্ব্যবহার করেছিল — এখানেও নতুন object বানানো হয় না, পুরনোর field বসিয়েই কাজ চলে; প্রতিটি branch দুটি field-ই সেট করে বলে আগের মান পরের কাউকে বিভ্রান্ত করে না। <code>self.pub_vel.publish(twist)<\/code> command পাঠাল <code>/cmd_vel<\/code>-এ, তারপর <code>sleep(0.2)<\/code> — এই 0.2 s robot পাঠানো command-ই মেনে চলে; 0.2 rad/s গতিতে হিসাব বলে ঘোরা 0.04 rad, বাস্তব কোণ acceleration ও wheel slip-এ কিছুটা কম (illustrative)।"},{"a":122,"b":126,"text":"<code>if self.Left_warning <= self.conut and self.Right_warning > self.conut:<\/code> — branch 2-এর L109-এর হুবহু মিরর, এবং একই কারণে dead: L116-এর guard বলেই ঢুকেছি যে <code>Left_warning > 3<\/code>, inner শর্ত চায় <code>Left_warning <= 3<\/code>। এক callback-এ counter frozen — দুটো একসাথে হয় না। ভেতরের body-র পরিকল্পনা ছিল: <code>twist.linear.x = 0.0<\/code>, <code>twist.angular.z = self.angular<\/code> (ধনাত্মক, বাঁয়ে), publish, তারপর <code>sleep(0.5)<\/code> — ডানে ঘুরিয়ে দেওয়ার পর বাঁয়ে শোধরানো। কিন্তু ঢোকার শর্তেই বাঁ দিক ব্লক ছিল, তাই বাঁ দিক কি এখন ফাঁকা — এই প্রশ্ন এখানে কখনো হ্যাঁ পায় না। দুটি mirror bug, একই গোড়া থেকে: একই callback-এর ভেতরে পুরনো শর্তের সঙ্গে নতুন শর্তের সংঘর্ষ।"},{"a":128,"b":130,"text":"Branch 6: শুধু সামনে বাধা, দুই পাশই ফাঁকা। এবার তুলনার চিহ্নটা খেয়াল করুন — <code>Left_warning < self.conut<\/code> এবং <code>Right_warning < self.conut<\/code>: এখানে STRICT less-than, অথচ branch 2-এ (L102) ছিল <code><=<\/code>। পার্থক্যটা ফল বদলে দেয়: কোনো side-এর count ঠিক 3 হলে (যেমন front > 3, Left ঠিক 3, Right 2) branch 6-ও মিস করবে — আর এই মিশ্রণে অন্য কোনো branch-ও নেই, ফলে সেই scan-এ একটাও publish হয় না এবং robot <code>/cmd_vel<\/code>-এর আগের পুরনো command মেনে চলতে থাকে — এটাই এই tree-র fall-through gap। <code>print ('6, there is an obstacle in the middle, turn left')<\/code> — নম্বর 6, আগের 5 নেই, as-is।"},{"a":131,"b":134,"text":"চূড়ান্ত action: জায়গায় দাঁড়িয়ে বাঁয়ে ঘোরা। <code>twist.linear.x = 0.0<\/code> — 0.45 m-এর ভেতরের বস্তুর দিকে এক পাও এগোনো নেই; <code>twist.angular.z = self.angular<\/code> — ধনাত্মক, তাই বাঁ দিক। ডান না বাঁ কেন, তার কোনো হিসাব tree-তে নেই — author-এর পছন্দ, branch 2-ও তো বাঁয়েই ঘুরে। <code>self.pub_vel.publish(twist)<\/code> পাঠানোর পর <code>sleep(0.2)<\/code> — executor 0.2 s থামে, এই ফাঁকেই robot pivot কার্যকর করে; পরের <code>registerScan<\/code> এলে নতুন count নিয়ে tree-র শুরু থেকে আবার সিদ্ধান্ত আসে — বাঁ দিকে ফাঁকা পথ পড়লে branch 10 (L161) এগিয়ে যাবে, তখন <code>linear.x<\/code> = 0.2 নিয়ে সোজা চলা।"}],"math":null,"robot":{"correct":"সত্যিকারের robot-এ branch 2 মানে সামনে ও ডানে 0.45 m-এর ভেতরে 3-এর বেশি beam, বাঁ ফাঁকা: robot সামনের গতি শূন্য করে জায়গায় বাঁয়ে pivot করে 0.2 rad/s গতিতে; sleep-এর 0.2 s-এ হিসাব বলে 0.04 rad ঘোরা, বাস্তবে acceleration আর wheel slip-এ কিছুটা কম (illustrative)। পরের scan-গুলোতেও একই শর্ত এলে pivot জমা হতে থাকে, ডানের বাধা দৃষ্টিসীমার বাইরে গেলে branch 6 বা branch 10 দায়িত্ব নেয় — বাঁ দিকে ফাঁকা পথ এভাবেই খুঁজে পাওয়া হয়।","incorrect":"দুটি প্রচলিত ভুল। এক: ভাবা যে L109 ও L122-এর double-check robot-কে ঘুরে আবার তাকিয়ে দিক বদলাতে দেয় — করে না; এক callback-এর ভেতরে counter বদলায় না, branch guard-ই বৈপরীত্য তৈরি করে, block দুটি dead। দুই: strict less-than আর less-than-or-equal একই ভেবে ফেলা — কোনো side-এর count ঠিক 3 হলে branch 6-ও মেলে না, সেই scan-এ কোনো publish হয় না, ফলে robot <code>/cmd_vel<\/code>-এর আগের পুরনো command মেনেই চলতে থাকে — প্রয়োজনে বাধার দিকেও সরতে পারে।"},"animType":"cmdVelVectors"},{"n":13,"id":"part-13","fname":"laser_Avoidance.py","enTitle":"Branches 7-10 — Front Clear","lang":"python","start":136,"end":165,"flags":[],"explain":[{"a":136,"b":137,"text":"<code># 7. Front is clear, but blocked on left AND right (narrow hallway)<\/code> — comment ছবিটা এঁকে দেয়: সামনে ফাঁকা, দুই পাশেই দেয়াল, মানে robot একটা সরু গলিতে ঢুকেছে। Condition-এ চোখ রাখো <code>self.front_warning < self.conut<\/code> — এখানে STRICT less-than, branch 1-এর <code>front_warning > self.conut<\/code>-এর ঠিক উল্টো দিক। ফলে <code>front_warning<\/code> ঠিক 3 হলে (দুই পাশ যতই blocked হোক) branch 1-ও ধরে না, branch 7-ও ধরে না — <code>front_warning == 3<\/code> হলো দুই branch-এর মাঝের no-man's land। আরেকটা সূক্ষ্মতা: front zone (|angle| < 20 degree) আর left zone (0 থেকে 70 degree) ওভারল্যাপ করে, তাই 0-20 degree-র কোনো beam একসাথে front আর Left দুটো counter-ই বাড়ায়; পাশের দেয়াল মূলত 20-70 degree ব্যান্ডে পড়লেই branch 7-এর মতো count-ছবি (front কম, দুই পাশ বেশি) দাঁড়ায়।"},{"a":138,"b":139,"text":"<code>print ('7. There are obstacles on the left and right, turn right')<\/code> — console-এর জন্য trace, motion-এর সাথে এর সরাসরি সম্পর্ক নেই; তবে চালানোর সময় terminal-এ কোন branch নিচ্ছে সেটার এটাই একমাত্র বাইরের সাক্ষী। তারপর <code>twist.linear.x = 0.0<\/code> — সরু গলিতে মুড়ানোর আগে forward speed শূন্য, মানে এই command-এ wheel শুধু নিজ জায়গায় ঘুরবে, এগোবে না। L87-এ বানানো সেই একই <code>Twist()<\/code> object-এর field overwrite হচ্ছে — প্রতিটা branch নতুন message বানায় না, পুরনোটাই রি-ইউজ হয়। সাধারণ একটা ভুল ধারণা: <code>linear.x = 0.0<\/code> লিখলেই robot 'থেমে গেল' না — এটা শুধু এই একটা message-এর কথা; নতুন command publish না হলে পর্যন্ত wheel আগের অবস্থাতেই থাকতে পারে।"},{"a":140,"b":142,"text":"<code>twist.angular.z = -self.angular<\/code> — negative মানে clockwise ঘোরা, মানে turn RIGHT; দুই পাশ blocked হলে code-এর পছন্দ ডান দিকে মুড়ানো। <code>self.pub_vel.publish(twist)<\/code> — command গেল <code>/cmd_vel<\/code> topic-এ, আর তারপর <code>sleep(0.4)<\/code> হলো গোটা tree-র সবচেয়ে লম্বা ঘুম: branch 1, 2, 4, 6, 8, 9 সবগুলো 0.2 s ঘুমায়, branch 10 একদমই ঘুমায় না, আর এখানে দ্বিগুণ 0.4 s। কারণ physical: দুই পাশে দেয়াল মানে ছোট ঠেলা নয়, বড় heading change দরকার। sleep চলাকালীন single-threaded executor এই callback-এই আটকে থাকে, নতুন <code>registerScan<\/code> ঢোকে না — তাই wheel এই একটা publish-কেই পুরো 0.4 s মানে; default angular 0.2 rad/s হলে হিসাব 0.2*0.4 = 0.08 rad, অর্থাৎ 4 degree-এর বেশি একটা মোড়।"},{"a":144,"b":145,"text":"Branch 8-এর comment: <code># 8. Front is clear, but blocked ONLY on the left<\/code> — সামনে ফাঁকা, শুধু বাঁ দিকে বাধা। Condition: <code>self.front_warning < self.conut and self.Left_warning > self.conut and self.Right_warning <= self.conut<\/code>। অসমতাগুলোর মিশ্রণ দেখো — front আর Left strict, কিন্তু Right-এ <code><=<\/code>; branch 9-এ ঠিক উল্টো সাজানো। এই mixed strict/non-strict-ই fall-through gap বানায়: যেমন <code>front_warning<\/code> 4, <code>Left_warning<\/code> ঠিক 3, <code>Right_warning<\/code> 1 হলে branch 2 চায় Right>3 (নেই), branch 6 চায় Left<3 strict (3 তো <3 নয়), branch 8 চায় front<3 (উল্টো) — কেউই ম্যাচ করে না, সেই scan-এ একটাও publish হয় না। মনে রেখো conut=3 এত ছোট যে ==3 আর >3-এর ব্যবধান মাত্র একটা beam।"},{"a":146,"b":148,"text":"<code>print ('8, there is an obstacle on the left, turn right')<\/code> — আবার console trace; ছোট কৌতূহল: এই নম্বরের পরে comma, অথচ branch 7-এর print-এ ছিল dot — author-এর ছোটখাটো অসামঞ্জস্য, আচরণে প্রভাব শূন্য। <code>twist.linear.x = 0.0<\/code> — বাঁ দিকের দেয়াল এড়ানোর আগে এগোনো বন্ধ। <code>twist.angular.z = -self.angular<\/code> — negative, ডানে ঘোরা। লজিক সরল: বাঁ blocked, ডান clear, তাই open side-এর দিকে মোড়। branch 2-এর সাথে মিল আছে (সেখানেও বাঁ ও সামনে-ডান বাধা মানে ডানে turn), পার্থক্য এই যে branch 8-এ front এখনো clear, তাই সিদ্ধান্ত আরও আগে থেকে নেওয়া হচ্ছে — দেয়ালের খুব কাছে যাওয়ার আগেই সংশোধন, এটাই ভালো avoidance-এর চেহারা: যত দূর থেকে মোড়, পথ তত মসৃণ।"},{"a":149,"b":150,"text":"<code>self.pub_vel.publish(twist)<\/code> — stop-and-turn command <code>/cmd_vel<\/code>-এ গেল; base controller এটাকে এখনই নিয়ে নেবে। তারপর <code>sleep(0.2)<\/code> — branch 7-এর অর্ধেক সময়, কারণ এখানে এক পাশ সামলানোর ছোট correction, বড় মোড় নয়। খেয়াল করো sleep মানে robot থামা নয় — মানে নতুন সিদ্ধান্ত আটকে রাখা: ঘুমের পুরো সময় শেষ publish করা command-ই wheel চালায়। এই সময়ে নতুন scan queue-তে অপেক্ষা করে, আর QoS depth 1 থাকায় পুরনো queued scan ঝরে গিয়ে শুধু সর্বশেষটা থাকে — তাই ঘুম ভাঙার পর <code>registerScan<\/code> প্রায়-টাটকা data নিয়েই চলে। সেই fused data-র উৎস folder 10-এর merger+filter chain, যার শেষ প্রান্ত এই <code>/scan<\/code> subscription।"},{"a":152,"b":153,"text":"Branch 9 প্রায় আয়নার ছবি: <code># 9. Front is clear, but blocked ONLY on the right<\/code>। Condition: <code>self.front_warning < self.conut and self.Left_warning <= self.conut and self.Right_warning > self.conut<\/code> — এবার Left-এ <code><=<\/code>, Right-এ strict <code>><\/code>, branch 8-এর উল্টো। এখানেও gap লুকানো: <code>front_warning<\/code> ঠিক 3, <code>Right_warning<\/code> 5, Left যা-ই হোক — branch 2 চায় front>3 (না), branch 9 চায় front<3 (না), branch 10 চায় তিনটাই <=3 (Right 5-এ ভাঙে) — কোনো branch-ই নেয় না। বড় ছবিটাও মনে রাখো: source-এর comment-এ branch নম্বর 1, 2, 4, 6, 7, 8, 9, 10 — 3 আর 5 নেই-ই, এবং থাকা আটটাও সব count-combination cover করে না; তাই decision tree মানেই সব case-এর উত্তর আছে — এই ধারণা এই code-এ খাটে না।"},{"a":154,"b":156,"text":"<code>print ('9, there is an obstacle on the right, turn left')<\/code> — branch 9-এর স্বাক্ষর console-এ। <code>twist.linear.x = 0.0<\/code> — ডান দিকে বাধা, তাই আগে এগোনো বন্ধ। <code>twist.angular.z = self.angular<\/code> — এবার positive, মানে counter-clockwise, মানে turn LEFT। ROS 2-এ <code>angular.z<\/code>-এর চিহ্নই দিক বলে দেয়: positive বাঁয়ে, negative ডানে (z-অক্ষ robot-এর উপরের দিকে, right-hand rule)। আর লক্ষ্য করো — একই <code>self.angular<\/code> parameter, default 0.2 rad/s, পুরো tree জুড়ে; শুধু চিহ্ন বদলে দিক বদলানো হয়েছে, আলাদা করে ধীর বা দ্রুত ঘোরার কোনো ব্যবস্থা নেই। ফলে 'কাছের বাধায় ধীরে ঘুরবে' জাতীয় প্রত্যাশা এই code পূরণ করে না — ঘোরার গতি সব সময় একই।"},{"a":157,"b":158,"text":"<code>self.pub_vel.publish(twist)<\/code> — turn-left command গেল, তারপর <code>sleep(0.2)<\/code> — branch 8-এর সমান, single-side branch দুটোতে একই ছোট বিরতি। sleep-এর asymmetry-টা এখন পুরো হিসাবে দাঁড়ায়: ছয়টা branch-এ 0.2 s, শুধু branch 7-তে দ্বিগুণ 0.4 s, আর branch 10-এ কোনো sleep নেই। এর শারীরিক অর্থ — যত বড় মোড় দিতে হবে, তত লম্বা সময় নতুন সিদ্ধান্ত আটকে রেখে সেই মোড় শেষ করা; আর যখন কিছুই করার নেই, তখন এক মুহূর্তও দাঁড়ানো নয়। ঘুমের মধ্যে wheel থামে না — শেষ publish-ই চলে; sleep-কে ব্রেক ভাবাটাই এখানকার ক্লাসিক ভুল, আসলে এটা পুরোদস্তুর চলমান অবস্থায় সিদ্ধান্তের বিরতি।"},{"a":160,"b":161,"text":"শেষ branch-এর comment উচ্ছ্বাসী: <code># 10. EVERYTHING IS CLEAR!<\/code>। Condition: <code>self.front_warning <= self.conut and self.Left_warning <= self.conut and self.Right_warning <= self.conut<\/code> — তিন zone-ই <code><= 3<\/code>, আর কোথাও strict <code><<\/code> নেই, তাই (3, 3, 3)-এর মতো count-ও cruise পায়। কিন্তু এই <code><=<\/code>-ই gap-এর অন্য মুখ: <code>front_warning<\/code> ঠিক 3 আর <code>Left_warning<\/code> 4 হলে (3, 4, 1-এর মতো ছবিতে) branch 4 চায় front>3, branch 8 চায় front<3, branch 10 চায় Left<=3 — তিনটাই মিস, publish শূন্য। অর্থাৎ 'সব পরিষ্কার' আর 'এক পাশ বাধা' — এই দুই দুনিয়ার সীমানায় কোনো counter ঠিক 3 বসলেই robot এক scan-এর জন্য সিদ্ধান্তহীন হয়ে যায়।"},{"a":162,"b":165,"text":"<code>print ('10, no obstacles, go forward')<\/code>, তারপর <code>twist.linear.x = self.linear<\/code> — parameter থেকে আসা default 0.2 m/s, আর <code>twist.angular.z = 0.0<\/code> — সোজা, কোনো মোড় নেই। <code>self.pub_vel.publish(twist)<\/code> দিয়ে cruise command গেল, এবং এরপর কোনো <code>sleep<\/code> নেই — callback সঙ্গে সঙ্গে return করে, ফলে executor সাথে সাথেই পরের fused scan নিয়ে আবার গোটা tree ছোটে। এটাই branch 10-এর সবচেয়ে বড় শক্তি: খোলা জায়গায় robot প্রতি scan-ই নিজের 'চলো' সিদ্ধান্ত টাটকা করে আবার নেয়, stale command জমে না। আর এখানেই gap-এর পরিণতিও বোঝা যায়: কোনো branch-ই না ম্যাচ করলে publish হয় না, তখন wheel-এ শেষ পড়া এই 0.2 m/s forward-টাই আরও এক scan-period চলতে থাকে — এক ধাপের জন্য চোখ বন্ধ করে এগোনো।"}],"math":null,"robot":{"correct":"সত্যিকারের robot-এ এই চার branch মিলে খোলা-জায়গার আচরণ গড়ে: narrow hallway-তে branch 7 pure rotation publish করে আর <code>sleep(0.4)<\/code> জুড়ে wheel সেই এক command-ই মানে — default angular 0.2 rad/s হলে প্রায় 0.08 rad ঘোরা, তারপর টাটকা scan-এ ফের মূল্যায়ন। এক-পাশ blocked হলে 0.2 s-এর ছোট correction (branch 8/9), আর সব পরিষ্কার হলে branch 10 কোনো sleep ছাড়াই প্রতি scan-এ 0.2 m/s forward আবার publish করে — cruise টানা self-refresh-এ চলে।","incorrect":"প্রধান ভুল ধারণা: এতগুলো branch তাহলে সব situation-ই cover। আসলে elif chain exhaustive নয় — কোনো counter ঠিক 3 হলে blocked-ish mix-এ কোনো branch-ই ম্যাচ করে না, সেই scan-এ একটাও publish হয় না। ফলে robot আগের scan-এর শেষ command মেনেই চলতে থাকে: আগেরটা branch 10-এর 0.2 m/s forward হলে সামনে দেয়াল থাকলেও এক scan-period এগোয়, console-এ কোনো নতুন branch নম্বরও ছাপা হয় না। ==3 আর >3-এর ব্যবধান মাত্র এক beam, তাই এই stale-motion মুহূর্ত নিয়মিতই ঘটে।"},"animType":null},{"n":14,"id":"part-14","fname":"laser_Avoidance.py","enTitle":"exit_pro — Shell Brake","lang":"python","start":167,"end":173,"flags":[],"explain":[{"a":167,"b":168,"text":"<code># --- SAFETY SHUTDOWN FUNCTION ---<\/code> — header comment জোর দিয়ে বলছে এটা সাধারণ কোনো helper নয়, বন্ধ হওয়ার সময়ের safety পথ। <code>def exit_pro(self):<\/code> class <code>laserAvoid<\/code>-এর ভেতরে একটা method define করছে, নামটা exit procedure-র মতোই পড়া যায়। বৈশিষ্ট্য হলো এটা চলন্ত অবস্থায় কেউ স্বেচ্ছায় ডাকে না — ডাকে <code>main<\/code>-এর <code>finally<\/code> block (L185), অর্থাৎ স্বাভাবিক শেষ হোক বা <code>Ctrl+C<\/code> দিয়ে <code>KeyboardInterrupt<\/code> (L182) হোক, node বন্ধ হওয়ার আগে এই function ঠিক একবার চলবেই। এটা কোনো ROS callback নয়, তাই এর ভেতরে ROS-এর বাইরের কাজ করাও বৈধ — পরের লাইনগুলো ঠিক সেই সুযোগটাই নেয়।"},{"a":169,"b":170,"text":"L169-এর comment বলছে: <code>Ctrl+C<\/code> চাপলে এটা একটা terminal command চালিয়ে robot-কে থামাতে বাধ্য করবে। <code>cmd1 = \"ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist \"<\/code> — সাধারণ একটা Python string, যার ভেতরে লেখা পুরো একটা CLI command। <code>ros2 topic pub<\/code> হলো ROS 2-এর নিজস্ব command-line publisher: প্রথমে topic (<code>/cmd_vel<\/code>), তারপর message type (<code>geometry_msgs/msg/Twist<\/code>), আর <code>--once<\/code> flag বলে দিচ্ছে ঠিক একটা message পাঠিয়েই command নিজে শেষ হয়ে যাবে। খেয়াল করুন string-এর একদম শেষে একটা space আছে — এটা ভুল নয়; পরের টুকরোর সাথে জোড়া লাগানোর সময় এই space-ই দুই অংশের মাঝের বিভাজক হবে, না থাকলে command-টা ভেঙে যেত।"},{"a":171,"b":172,"text":"<code>cmd2<\/code> নেওয়া হয়েছে triple single-quote দিয়ে, আর তার ভেতরে double-quote-এ মোড়ানো একটা YAML-style inline message: <code>\"{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}\"<\/code> — ছয়টা field-ই শূন্য, মানে এটা L84-এর <code>Twist()<\/code>-এর মতোই একটা পূর্ণ brake message, শুধু লেখার ভঙ্গি YAML। <code>ros2 topic pub<\/code> CLI এই লেখাকে parse করে সত্যিকারের Twist object বানিয়ে publish করে। <code>cmd = cmd1 +cmd2<\/code> — plus-এর দুই পাশে space নেই, Python-এ সম্পূর্ণ বৈধ, আর ফলাফল এক লাইনের সম্পূর্ণ shell command; cmd1-এর শেষে রাখা সেই space-ই double-quote-এর আগে বিভাজনটা ঠিক রেখেছে।"},{"a":173,"b":173,"text":"<code>os.system(cmd)<\/code> — shutdown brake-এর শেষ ধাপ। Python-এর <code>os.system<\/code> string-টাকে একটা shell-এ পাঠিয়ে দেয় আর command শেষ না হওয়া পর্যন্ত অপেক্ষা করে (L169-এর comment-এর background শব্দটা আসলে এই synchronous চলাকেই ইঙ্গিত করছে)। বড় প্রশ্ন: নিজের <code>self.pub_vel<\/code> publisher (L29) হাতে রেখেও কেন shell মারফত? কারণ এই মুহূর্তে পুরো node ভেঙে আসছে — <code>finally<\/code> block-এ, <code>KeyboardInterrupt<\/code>-এর পরে, পরের লাইনেই <code>destroy_node()<\/code> আর <code>rclpy.shutdown()<\/code> অপেক্ষা করছে। <code>os.system<\/code> চালু করে একটা আলাদা process, যার নিজস্ব ROS context আছে — মূল node যতটা ছেঁড়া-ফাটা অবস্থাতেই থাকুক, সে স্বাধীনভাবে শূন্য Twist পাঠিয়ে দিতে পারে। Wheel driver শেষ command ধরে রাখে বলে <code>--once<\/code>-এর একটা message-ই robot থামানোর জন্য যথেষ্ট।"}],"math":null,"robot":{"correct":"Ctrl+C চাপলে <code>KeyboardInterrupt<\/code> ধরা পড়ে (L182), তারপর <code>finally<\/code> (L185) এই function ডাকে — shell থেকে <code>ros2 topic pub --once<\/code> ঠিক একটা শূন্য Twist পাঠায়। Motor driver সর্বশেষ command-ই ধরে রাখে, তাই node বন্ধ হওয়ার আগের এই একটা message-ই robot-কে থামিয়ে দেয় — robot 0.2 m/s গতিতে চলতে চলতে বন্ধ করা হলেও wheel আর ঘোরে না। Node-এর নিজের publisher নয়, আলাদা CLI process কাজটা করে বলে teardown-এর মুহূর্তেও brake টা পৌঁছে যায়।","incorrect":"সাধারণ ভুল ধারণা: node বন্ধ হলেই <code>/cmd_vel<\/code> ফাঁকা হয়ে যাবে আর robot আপনা-আপনি থেমে যাবে। বাস্তবে <code>rclpy.shutdown()<\/code> publisher-কে সরিয়ে দেয় ঠিকই, কিন্তু motor driver-এ জমানো শেষ command মুছে দেয় না — এই শূন্য publish না থাকলে Ctrl+C-এর অনেক পরেও robot শেষ গতিতেই এগিয়ে যেত, দেয়াল বা টেবিলে ধাক্কা খাওয়া পর্যন্ত। আরেকটা ভুল: নিজের publisher দিয়েই শেষ message পাঠানো যাবে ভাবা — teardown চলাকালে সেটা অনির্ভরযোগ্য, shell পথটাই এখানে নিরাপদ।"},"animType":null},{"n":15,"id":"part-15","fname":"laser_Avoidance.py","enTitle":"main — Spin & Shutdown","lang":"python","start":176,"end":187,"flags":[],"explain":[{"a":176,"b":177,"text":"<code>def main():<\/code> — পুরো file-এর entry point। লক্ষ করো, এই file নিজে কোথাও <code>main()<\/code>-কে call করে না — L187-এ এসেই source শেষ; call করে ROS 2-র executable mechanism: README-র L5 command <code>ros2 run yahboom_M3Pro_laser laser_Avoidance<\/code> চালালে ওই executable এই <code>main()<\/code>-কে খুঁজে run করে, package-এর entry point এমনটাই করে (setup.py এই folder-এ source হিসেবে নেই — standard কাঠামো)। ভেতরে প্রথম কাজ <code>rclpy.init()<\/code> — এটা ছাড়া একটাও <code>Node<\/code> বানানো যায় না। এটা global rclpy context তৈরি করে, যার উপর পরের সবকিছু দাঁড়ায়; Ctrl+C-র signal ধরার ব্যবস্থাও এখান থেকেই আসে। L187-এর <code>rclpy.shutdown()<\/code> এই context-কেই বন্ধ করবে — init আর shutdown একই জোড়ার দুই প্রান্ত।"},{"a":178,"b":179,"text":"<code>laser_avoid = laserAvoid(\"laser_Avoidance_a1\")<\/code> — L17-এর class-এর instance জন্মাল, মানে L18 থেকে L47 পর্যন্ত পুরো constructor এই এক line-এর মধ্যেই সম্পন্ন হয়ে যায়: <code>super().__init__(name)<\/code> নাম বসায়, <code>/scan<\/code> আর <code>/JoyState<\/code> subscription (L23, L25), <code>/cmd_vel<\/code> publisher (L29), চারটা parameter read — সব। নাম-string <code>\"laser_Avoidance_a1\"<\/code> terminal-এ <code>ros2 node list<\/code> দিলে দেখা যাবে। <code>print (\"start it\")<\/code> — print আর বন্ধনীর মাঝে space, L14-এর <code>print (\"improt done\")<\/code>-এর মতোই author-এর style; Python-এ বৈধ। এই line-টা একটা কাজের checkpoint: এটা দেখলে বুঝবে constructor ঠিকঠাক শেষ, এখন <code>/scan<\/code>-এ folder 10-এর merger+filter chain-এর fused data এলেই সিদ্ধান্ত নেওয়া শুরু হবে।"},{"a":180,"b":181,"text":"<code>try:<\/code>-এর ভেতরে <code>rclpy.spin(laser_avoid)<\/code> — এই একটা line-ই পুরো program-এর হৃদপিণ্ড। এর আগ পর্যন্ত আমরা শুধু structure বানিয়েছিলাম; <code>spin<\/code> হলো event loop: main thread এখানে চিরকালের জন্য block হয়ে যায়, আর executor ভেতরে ভেতরে message এলে callback ছোড়ে — <code>/scan<\/code>-এ নতুন scan এলে <code>registerScan<\/code>, <code>/JoyState<\/code> এলে <code>JoyStateCallback<\/code>। অর্থাৎ L94-165-এর দশ-branch-এর decision tree আসলে এই দুই line-এর ভেতরেই ঘটে চলে। <code>spin<\/code> স্বাভাবিক পথে ফেরে না, তাই একে <code>try<\/code>-তে মুড়িয়ে রাখা হয়েছে যাতে Ctrl+C-র মতো interrupt ধরা পড়ে। Executor single-threaded — তাই callback-এর ভেতরের <code>sleep(0.2)<\/code> পুরো loop-কে সাময়িক থামিয়ে দেয়।"},{"a":182,"b":183,"text":"<code>except KeyboardInterrupt: pass<\/code> — terminal-এ Ctrl+C চাপলে SIGINT signal আসে, rclpy-র signal handler সেটাকে <code>KeyboardInterrupt<\/code> exception-এ রূপ দেয়, আর সেই exception ঠিক <code>spin<\/code>-এর ভেতরে ফেটে ওঠে। এই <code>except<\/code> সেটাকে ধরে <code>pass<\/code> দিয়ে চুপচাপ সামলে নেয় — terminal-এ লম্বা traceback ছাপা হয় না, execution শান্তভাবে নিচে নামে। সূক্ষ্ম একটা পয়েন্ট: এই <code>except<\/code> না থাকলেও <code>finally<\/code> তো চলতই — unhandled exception-এর ক্ষেত্রেও <code>finally<\/code> block চালু হয়। তাহলে <code>except<\/code> কী কাজ করল? exception-কে handled বানাল: নচেৎ process শেষে nonzero exit code ফিরত, আর কোনো script সেটাকে বড় বিপদ ভেবে ভুল ব্যবস্থা নিতে পারত। আর <code>pass<\/code> মানে শরীর খালি — করার কিছু নেই, শুধু গিলে যাওয়া।"},{"a":184,"b":185,"text":"<code>finally:<\/code> — গ্যারান্টি এটাই: <code>try<\/code> block যেভাবেই শেষ হোক (এখানে বাস্তবে একমাত্র পথটা হলো Ctrl+C), এই block অবশ্যই চলবে। প্রথম কাজ <code>laser_avoid.exit_pro()<\/code>, L168-173: shell-এ <code>ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist<\/code> command চালিয়ে সব-শূন্য একটা Twist একবার publish করে। প্রশ্ন হতে পারে — node-এর নিজের <code>pub_vel<\/code> দিয়ে পাঠালেই তো হয়? কিন্তু teardown-এর মুহূর্তে নিজের publisher আর context অনিশ্চিত অবস্থায় থাকতে পারে; <code>os.system<\/code> একেবারে আলাদা process চালায়, node-এর কোনো অবস্থার উপর দাঁড়ানো নেই। শারীরিক অর্থে এটাই ব্রেক: শেষ branch যদি <code>+0.2<\/code> m/s সামনে যাওয়ার command দিয়ে থাকে, চাকা সেটা ধরে রাখত — zero Twist এসে থামায়।"},{"a":186,"b":187,"text":"<code>laser_avoid.destroy_node()<\/code> তারপর <code>rclpy.shutdown()<\/code> — ক্রম এখানে বদলানো চলে না। <code>destroy_node()<\/code> আগে: node-এর <code>/cmd_vel<\/code> publisher, দুটো subscription, parameter — সব cleanly ভেঙে মুক্ত করে, DDS-এর দখল ছাড়ে। এরপর <code>rclpy.shutdown()<\/code>: L177-এর <code>rclpy.init()<\/code>-এ জন্মানো global context বন্ধ করে। উল্টো করলে বিপদ — context আগে মরলে node-এর teardown নিজের মেঝেটাই হারায়। সাজানোটা LIFO: জন্মানোর সময় আগে context, পরে node; বন্ধের সময় আগে node, পরে context — nested জিনিস গোটানোর স্বাভাবিক নিয়ম, nested bracket বন্ধ করার মতোই। এই line-এ এসে 187-line-এর file-এর জীবন শেষ — জন্ম (init), কর্ম (spin), বিদায় (shutdown): একটা behavior node-এর পূর্ণ চক্র।"}],"math":null,"robot":{"correct":"Real robot-এ Ctrl+C চাপলে SIGINT যায়, <code>spin<\/code>-এর ভেতরে <code>KeyboardInterrupt<\/code> ওঠে, আর <code>finally<\/code>-র ভেতরে <code>exit_pro()<\/code> shell থেকে সব-শূন্য Twist একবার publish করে — চাকা থামার স্পষ্ট আদেশ পায়, তাই শেষ branch যদি <code>+0.2<\/code> m/s সামনে যাওয়ার command দিয়ে থাকে তবু robot দাঁড়িয়ে যায়। এরপর <code>destroy_node()<\/code> publisher-subscription ছাড়ে, <code>rclpy.shutdown()<\/code> context বন্ধ করে — পরিষ্কার, নিরাপদ শেষ।","incorrect":"বিপজ্জনক ভুল ধারণা: node কিল করলেই robot থামবে ভাবা। <code>kill -9<\/code> মারলে <code>finally<\/code> চলেই না — <code>exit_pro()<\/code>-র zero Twist যায় না, base তখন শেষ <code>/cmd_vel<\/code> command ধরে রাখে: branch 1-এর মতো সামনে <code>+0.2<\/code> m/s চলতেই থাকে যতক্ষণ না অন্য কিছু থামায়। আরেকটা ভুল: <code>rclpy.shutdown()<\/code> আগে ডেকে <code>destroy_node()<\/code> পরে করা — context মরে যাওয়ার পর node teardown করতে গিয়ে error।"},"animType":"safetyHalt"}];



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
    '<h1>11. lidar obstacle avoidance <span class="path">— fused 360-degree scan-এর three-zone warning count, তারপর 9-branch decision tree-র কমান্ড /cmd_vel-এ</span></h1>' +
    '<div class="intro-desc bn">এই application-টি <code>11. lidar obstacle avoidance</code> folder-এর তিনটি source file — <code>README.md</code> (তিন command-এর runbook), <code>laser_driver.launch.py</code> (folder 10-এর merger আর filter launch file দুটিকে এক সঙ্গে চালানোর orchestrator) আর <code>laser_Avoidance.py</code> (fused scan পড়ে three-zone counting করে <code>/cmd_vel</code>-এ কমান্ড দেওয়া behavior node) — কে কেন্দ্র করে তৈরি। ভেতরে আছে <code>IncludeLaunchDescription</code> দিয়ে chained launch, subscription-publisher graph, declare/get parameter জোড়া, প্রতিটি beam-এর angle math ও zone inequality, আর 9-branch decision tree-র ধাপে ধাপে বিশ্লেষণ। প্রতিটি Part-এ আছে original code card, line-by-line Bangla explanation, Math derivation, Real Robot behavior এবং interactive animation।</div>' +
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
    '11. lidar obstacle avoidance · line-by-line analysis · source preserved verbatim from /home/shariful/NeuroBotics/11. lidar obstacle avoidance';
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

/* ================= folder-11 anims (v1 layer, 7 total) ================
   runbookFlow (part 1) · includeChain (part 3) · subPubGraph (part 6)
   beamSweep (part 9) · decisionTree (part 11) · cmdVelVectors (part 12)
   safetyHalt (part 15)
   Facts from the three source files (sha a14cc05fee6f / dadf5ff3f9b1 /
   04cb3a590eec) + FACTS-11: README = 3-command runbook (L1/L3/L5, L2/L4
   blank); driver = constructor with two EAGER os.path.join paths to
   ira_laser_tools merge_multi.launch.py + yahboom_laser_filter
   laser_filter_node.launch.py (folder 10 chain) and a 2-include return;
   avoidance node laser_Avoidance_a1 subscribes /scan (fused 360) +
   /JoyState, publishes /cmd_vel; parameters linear 0.2 · angular 0.2 ·
   LaserAngle 20.0 deg · ResponseDist 0.3 m (gate 0.45 m); conut = 3;
   zones front |a|<20 · left 0<a<70 · right -70<a<0 (chained cmp; stale
   comments say ±30 / 0.825 / 60-90 / -90..-60 / conut 10); 9-branch
   first-match-wins tree; branch 1 forward-despite-trapped bug admitted
   in its own comment; exit_pro() shell-brakes via ros2 topic pub --once.
   Stage = setStage 900x460 grammar. No emoji; arrow chars NEVER in stage
   <text> — only in the caption/formula strips below the stage. Unique id
   prefix per anim: rf- ic- sp- bs- dt- cv- sh-. Static backbone visible
   at setStage, first caption + formula set before the first await. */

/* ---------- runbookFlow ---------- */
/* ============ folder-11 anim — runbookFlow (part 1, v1 layer) ============
   README.md L1-L5 (5 lines, 3 nonblank): L1 sh start_agent.sh, L3 ros2
   launch yahboom_M3Pro_laser laser_driver.launch.py, L5 ros2 run
   yahboom_M3Pro_laser laser_Avoidance; L2/L4 blank-line pauses.
   laser_driver.launch.py L8 generate_launch_description(), L28-41 list,
   IncludeLaunchDescription #1 (L32, ira_laser_tools merge_multi.launch.py,
   folder 10) + #2 (L38, yahboom_laser_filter laser_filter_node.launch.py).
   laser_Avoidance.py: sub /scan L23 + /JoyState L25, pub /cmd_vel L29,
   node name laser_Avoidance_a1 L178, Joy_active gate L83-85.
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
    txt(66, 241, '  laser_Avoidance', { size: 9.5, mono: true, weight: 700, fill: '#4fc3f7' }) +
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
    txt(452, 294, 'behavior process: laser_Avoidance — node name laser_Avoidance_a1 (L178)', { size: 7.5, mono: true, weight: 700, fill: '#4fc3f7', id: 'rf-proct', op: 0 }) +
    txt(452, 312, 'sub: /scan + /JoyState (L23, L25)', { size: 8, mono: true, fill: '#4fc3f7', id: 'rf-sub', op: 0 }) +
    txt(452, 326, 'pub: /cmd_vel (L29) -&gt; wheels', { size: 8, mono: true, fill: '#ff7b72', id: 'rf-pub', op: 0 }) +
    rrect(444, 336, 400, 22, 5, '#161b22', '#30363d', ' id="rf-gbox" opacity="0"') +
    txt(452, 351, 'front+rear raw -&gt; merger -&gt; filter -&gt; /scan -&gt; laser_Avoidance -&gt; /cmd_vel', { size: 7.5, mono: true, weight: 700, fill: '#e3b341', id: 'rf-gtxt', op: 0 }) +
    txt(450, 386, 'রঙ-নিয়ম: সবুজ = driver ও raw, হলুদ = launch ও merger, বেগুনি = filter, নীল = behavior, লাল = /cmd_vel', { anchor: 'middle', size: 8.5, fill: '#8b949e' }) +
    txt(450, 440, 'source: README.md L1-L5 + laser_driver.launch.py L8-L41 + laser_Avoidance.py L23-L29, L178', { anchor: 'middle', size: 8, mono: true, fill: '#6e7681' })
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
  host.caption('<b>ros2 run yahboom_M3Pro_laser laser_Avoidance</b> (L5) — এই folder-এর behavior process: subscribe করে <code>/scan</code> + <code>/JoyState</code> (L23, L25), publish করে <code>/cmd_vel</code> (L29) — চাকার হুকুম এখান থেকেই।');
  await host.sleep(1700);
  show('rf-d1'); show('rf-d2'); show('rf-d3');
  host.caption('<code>ros2 launch</code> বনাম <code>ros2 run</code>: launch একটা file-এর ভেতরের action-তালিকা চালায় (L3-এ দুইটা include উঠেছিল), run সরাসরি একটা executable তোলে (L5)। দুই command-ই একই <code>yahboom_M3Pro_laser</code> package-র ভেতর থেকে।');
  host.formula('ros2 launch = actions from a launch file  |  ros2 run = one executable, no file');
  await host.sleep(1700);
  show('rf-gbox'); show('rf-gtxt');
  host.caption('পুরো chain এক line-এ: front+rear raw → merger → filter → /scan → laser_Avoidance → /cmd_vel। আর <code>/JoyState</code> true হলে মানুষের joystick জিতে যায় (L83-85) — নাহলে চলে beam-গুনে হিসাব।');
  host.formula('folder 10: 2 raw -> merger -> filter -> /scan  |  folder 11: /scan -> laser_Avoidance -> /cmd_vel');
  await host.sleep(1700);
  host.caption('৩টা command, ৫টা line — একটাও এলোমেলো নয়: প্রত্যেকটা আগের ধাপের ফলের ওপর দাঁড়িয়েছে। এবার ঢুকব laser_Avoidance-এর ভেতরে — পরের part-এ সেই হিসাব।');
  await host.sleep(1500);
};

/* ---------- includeChain ---------- */
/* ===== folder-11 part 3 — includeChain (prefix ic-) ================
   laser_driver.launch.py L8-L24: constructor builds TWO eager paths via
   os.path.join(get_package_share_directory(pkg), 'launch', file) for
   ira_laser_tools/merge_multi.launch.py (L12-16) and
   yahboom_laser_filter/laser_filter_node.launch.py (L20-24); each then
   wrapped PythonLaunchDescriptionSource -> IncludeLaunchDescription and
   queued for the L28 LaunchDescription return (run = next part).
   Contrast per FACTS-11: plain call = EAGER at constructor time, unlike
   folder 10's lazy LaunchConfiguration. Share-dir prefixes illustrative.
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
/* ===== folder-11 anim — subPubGraph (part 6, laser_Avoidance.py L17-L30) =====
   দুই ear (/scan, /JoyState) + এক mouth (/cmd_vel) — constructor-এর পুরো নকশা।
   Facts: L17 class laserAvoid(Node), L18 def __init__(self,name), L19
   super().__init__(name), L23 create_subscription(LaserScan,"/scan",
   self.registerScan,1), L25 create_subscription(Bool,'/JoyState',
   self.JoyStateCallback,1), L29 create_publisher(Twist,'/cmd_vel',1),
   L30 blank, L31 declare_parameter শুরু; node name laser_Avoidance_a1
   আসে main() L178 থেকে। /scan = folder 10 chain-এর fused 360 ফল।
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
    txt(56, 64, 'LASER_AVOIDANCE.PY — CONSTRUCTOR', { size: 9.5, weight: 700, fill: '#e6edf3' }) +
    rrect(50, 74, 342, 58, 4, '#161b22', '#e3b341', ' id="sp-h1" opacity="0"') +
    rrect(50, 131, 342, 58, 4, '#161b22', '#7ee787', ' id="sp-h2" opacity="0"') +
    rrect(50, 188, 342, 40, 4, '#161b22', '#4fc3f7', ' id="sp-h3" opacity="0"') +
    rrect(50, 226, 342, 58, 4, '#161b22', '#e3b341', ' id="sp-h4" opacity="0"') +
    txt(56, 86, 'class laserAvoid(Node):', { size: 8.5, mono: true, weight: 700, fill: '#e6edf3' }) +
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
    txt(656, 190, 'laserAvoid', { anchor: 'middle', size: 12, mono: true, weight: 700, fill: '#e6edf3', id: 'sp-nodeT', op: 0 }) +
    txt(656, 204, 'class — L17', { anchor: 'middle', size: 7, fill: '#8b949e', id: 'sp-nodeC', op: 0 }) +
    rrect(598, 214, 116, 20, 4, '#161b22', '#d2a8ff', ' id="sp-nameB" opacity="0"') +
    txt(656, 228, 'laser_Avoidance_a1', { anchor: 'middle', size: 7.5, mono: true, weight: 700, fill: '#d2a8ff', id: 'sp-nameT', op: 0 }) +
    txt(656, 250, 'parent: super().__init__(name)', { anchor: 'middle', size: 6.5, mono: true, fill: '#8b949e', id: 'sp-supT', op: 0 }) +
    txt(656, 268, 'নামটা পাঠাবে main() — L178', { anchor: 'middle', size: 6.5, fill: '#6e7681', id: 'sp-nameN', op: 0 }) +
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
    txt(760, 337, 'NEXT L31: declare_parameter', { anchor: 'middle', size: 7, mono: true, fill: '#d2a8ff', id: 'sp-nextT', op: 0 }) +
    txt(450, 386, 'রঙ-নিয়ম: সবুজ = /scan, নীল = /JoyState, হলুদ = /cmd_vel ও parent, বেগুনি = নাম ও msg টাইপ', { anchor: 'middle', size: 8.5, fill: '#8b949e' }) +
    txt(450, 440, 'source: laser_Avoidance.py L17-L30 + main() L178', { anchor: 'middle', size: 8, mono: true, fill: '#6e7681' })
  );
  const q = id => svg.querySelector('#' + id);
  const show = id => q(id).setAttribute('opacity', 1);
  const dimc = id => q(id).setAttribute('stroke', '#30363d');
  host.caption('Constructor-এর পুরো নকশা এই কয়েকটা beat-এ: L17-এ class জন্ম, তারপর দুটো subscription আর একটা publisher। বাঁয়ে আসল code, ডানে তার graph।');
  host.formula('constructor = class birth + super wiring + 2 subscriptions + 1 publisher');
  await host.sleep(1400);

  show('sp-h1'); show('sp-nodeB'); show('sp-nodeT'); show('sp-nodeC');
  show('sp-parentB'); show('sp-parentT'); show('sp-pwire'); show('sp-supT');
  host.caption('<b>class laserAvoid(Node)</b> (L17) — rclpy-র <code>Node</code> থেকে inherit করে নতুন class জন্মাল। <b>super().__init__(name)</b> (L19) parent-এর constructor ডেকে এই বাচ্চাটাকে ROS graph-এ সত্যিকারের node বানিয়ে দেয়।');
  host.formula('super().__init__(name) -> laserAvoid instance becomes a live node');
  await host.sleep(1600);

  show('sp-nameB'); show('sp-nameT'); show('sp-nameN');
  host.caption('একটা সূক্ষ্ম পয়েন্ট: class-এর নাম <code>laserAvoid</code>, কিন্তু node-এর নাম আলাদা — <code>laser_Avoidance_a1</code>। এই নামটা constructor নিজে বানায় না; পরে <b>main()</b> (L178) argument হিসেবে পাঠাবে। দুটো আলাদা জিনিস।');
  host.formula('class name: laserAvoid   |   node name: laser_Avoidance_a1 (main, L178)');
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
  host.caption('Mouth-এর ভাষাও ঠিক করা: <code>Twist</code> message-এর এখানে দুটো ঘরই কাজে লাগে — <code>linear.x</code> (সামনের গতি, m/s) আর <code>angular.z</code> (ঘোরা, rad/s)। এই দুটোর মান পরের অংশের parameter থেকে আসবে (L33, L35)।');
  host.formula('Twist = linear.x (m/s) + angular.z (rad/s)');
  await host.sleep(1700);

  show('sp-nextB'); show('sp-nextT');
  host.caption('পুরো ছবি দাঁড়াল: দুই ear, এক mouth। Constructor-এর নিজের কাজ L30-এই শেষ — L31 থেকে শুরু <code>declare_parameter</code>-এর সারি: linear 0.2, angular 0.2, LaserAngle 20.0, ResponseDist 0.3। সেটাই পরের অংশের গল্প।');
  host.formula('graph: 2 in (/scan, /JoyState) + 1 out (/cmd_vel) -> decision in, wheels out');
  await host.sleep(1700);
};

/* ---------- beamSweep ---------- */
/* ============ folder-11 v1 anim — beamSweep (part 9) ================
   laser_Avoidance.py registerScan beam loop, L61-L80. Stage: top-down
   fused 360 ring (laser_driver.launch.py L31/L37: merger stitches the
   front and back lasers into one 360 map, then filter -> /scan), deg 0
   up, +deg LEFT (ROS ccw). Beats: L63 sweep, L65 rad->deg formula,
   L68-70 front zone (|deg| < 20, gate 0.3*1.5 = 0.45 m), L73-75 left
   (0 < deg < 70), L78-80 right (-70 < deg < 0), overlap band 0..20
   double-counts front + Left. Stale comments L67 (+/-30), L69 (0.825),
   L72 (60-90), L77 (-90..-60) vs real code. Ring ranges illustrative.
   Prefix bs-. No emoji, no arrow chars in stage, entities for &lt; &gt;. */

/* --- prefixed polar helpers (deg: 0 = up, +deg = screen left) --- */
function bsBeam(deg) {
  const a = (deg + 180) % 360 - 180;
  if (Math.abs(a) < 26) return 0.36;                    /* front card */
  if (Math.abs(a) < 75) return 0.95;                    /* side walls */
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
  const p5 = bsXY(266, 226, 95, 5, 0.36);
  const l20 = bsXY(266, 226, 1, 20, 176);
  const lm20 = bsXY(266, 226, 1, -20, 176);
  const l70 = bsXY(266, 226, 1, 70, 163);
  const lm70 = bsXY(266, 226, 1, -70, 163);
  const svg = host.setStage(
    txt(450, 26, 'beam loop: এক এক করে প্রতিটি beam, তিন zone-এর বিচার — L63-L80', { anchor: 'middle', size: 14.5, weight: 600, fill: '#ffb454' }) +
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
    '<path d="' + bsArcD(266, 226, 150, -20, 20) + '" fill="none" stroke="#7ee787" stroke-width="8" opacity="0.9" id="bs-fa" />' +
    '<path d="' + bsArcD(266, 226, 137, 2, 70) + '" fill="none" stroke="#e3b341" stroke-width="6" opacity="0" id="bs-la"/>' +
    '<path d="' + bsArcD(266, 226, 137, -70, -2) + '" fill="none" stroke="#4fc3f7" stroke-width="6" opacity="0" id="bs-ba"/>' +
    '<path d="' + bsArcD(266, 226, 163, 0, 20) + '" fill="none" stroke="#d2a8ff" stroke-width="5" opacity="0" id="bs-pa"/>' +
    txt(l20[0], l20[1], '20', { anchor: 'middle', size: 7, weight: 700, fill: '#7ee787' }) +
    txt(lm20[0], lm20[1], '-20', { anchor: 'middle', size: 7, weight: 700, fill: '#7ee787' }) +
    txt(l70[0], l70[1], '70', { anchor: 'middle', size: 7, weight: 700, fill: '#e3b341' }) +
    txt(lm70[0], lm70[1], '-70', { anchor: 'middle', size: 7, weight: 700, fill: '#4fc3f7' }) +
    '<path id="bs-hit1" d="' + bsSquares(266, 226, 95, 2, -18, -8) + '" fill="#ff7b72" opacity="0"/>' +
    '<path id="bs-hit2" d="' + bsSquares(266, 226, 95, 2, -6, 6) + '" fill="#ff7b72" opacity="0"/>' +
    '<path id="bs-hit3" d="' + bsSquares(266, 226, 95, 2, 8, 18) + '" fill="#ff7b72" opacity="0"/>' +
    '<path id="bs-lo" d="' + bsSquares(266, 226, 95, 2, 2, 24) + '" fill="none" stroke="#e3b341" stroke-width="0.9" opacity="0"/>' +
    '<path id="bs-ro" d="' + bsSquares(266, 226, 95, 2, -24, -2) + '" fill="none" stroke="#4fc3f7" stroke-width="0.9" opacity="0"/>' +
    circ(p5[0], p5[1], 5.5, 'none', ' stroke="#d2a8ff" stroke-width="1" id="bs-ov5r" opacity="0"') +
    circ(p5[0], p5[1], 3, '#d2a8ff', ' id="bs-ov5" opacity="0"') +
    txt(p5[0] - 10, p5[1] - 8, '+5 deg = দুই গণনা', { anchor: 'end', size: 7.5, weight: 700, fill: '#d2a8ff', id: 'bs-ov5t', op: 0 }) +
    txt(302, 186, 'ranges[i] &lt;= 0.45 m', { size: 7.5, weight: 700, fill: '#ff7b72', id: 'bs-gate', op: 0 }) +
    txt(302, 198, 'demo beam = 0.36 m', { size: 7, fill: '#8b949e', id: 'bs-gate2', op: 0 }) +
    rrect(257, 216, 18, 20, 3, '#30363d', '#8b949e') +
    '<path d="M266 216L266 207" stroke="#7ee787" stroke-width="2" fill="none"/>' +
    txt(285, 207, 'front', { size: 6.5, fill: '#8b949e' }) +
    txt(54, 328, 'SCAN CURSOR', { size: 7, weight: 700, fill: '#6e7681' }) +
    txt(54, 344, 'i = 0', { size: 9, mono: true, weight: 700, fill: '#e6edf3', id: 'bs-ri' }) +
    txt(54, 358, 'angle = -180 deg', { size: 8.5, mono: true, fill: '#8b949e', id: 'bs-ra' }) +
    txt(54, 372, 'ranges[i] = 1.25 m', { size: 8.5, mono: true, fill: '#8b949e', id: 'bs-rr' }) +
    txt(160, 344, '+deg = বাঁদিক', { size: 7.5, fill: '#6e7681' }) +
    '<g id="bs-cur" transform="rotate(180 266 226)"><line x1="266" y1="226" x2="266" y2="90" stroke="#e6edf3" stroke-width="1.2" opacity="0.9"/><circle cx="266" cy="90" r="3" fill="#e6edf3"/></g>' +
    /* ---------- right: code L63-L80 ---------- */
    rrect(516, 44, 344, 252, 8, '#0d1117', '#30363d') +
    txt(688, 62, 'registerScan — beam loop (L63-L80)', { anchor: 'middle', size: 9, weight: 700, fill: '#e6edf3' }) +
    rrect(522, 70, 332, 13, 3, '#21262d', 'none', ' id="bs-hl1" opacity="0"') +
    rrect(522, 84, 332, 27, 3, '#21262d', 'none', ' id="bs-hl2" opacity="0"') +
    rrect(522, 112, 332, 42, 3, '#21262d', 'none', ' id="bs-hl3" opacity="0"') +
    rrect(522, 154, 332, 56, 3, '#21262d', 'none', ' id="bs-hl4" opacity="0"') +
    rrect(522, 210, 332, 56, 3, '#21262d', 'none', ' id="bs-hl5" opacity="0"') +
    rrect(522, 140, 332, 13, 3, 'none', '#d2a8ff', ' id="bs-hl6a" opacity="0"') +
    rrect(522, 196, 332, 13, 3, 'none', '#d2a8ff', ' id="bs-hl6b" opacity="0"') +
    txt(530, 80, 'for i in range(len(ranges)):', { size: 8, mono: true, fill: '#8b949e' }) +
    txt(530, 94, 'angle = (scan_data.angle_min +', { size: 8, mono: true, fill: '#8b949e' }) +
    txt(530, 108, 'scan_data.angle_increment * i) * RAD2DEG', { size: 8, mono: true, fill: '#8b949e' }) +
    txt(530, 122, 'if abs(angle) &lt; self.LaserAngle and ranges[i] != 0.0:', { size: 8, mono: true, fill: '#8b949e' }) +
    txt(530, 136, 'if ranges[i] &lt;= self.ResponseDist*1.5:', { size: 8, mono: true, fill: '#8b949e' }) +
    txt(530, 150, 'self.front_warning += 1', { size: 8, mono: true, fill: '#8b949e' }) +
    txt(530, 164, 'if angle &lt; (90 - self.LaserAngle) &lt; 90 and', { size: 8, mono: true, fill: '#8b949e' }) +
    txt(530, 178, 'angle&gt;0 and ranges[i] != 0.0:', { size: 8, mono: true, fill: '#8b949e' }) +
    txt(530, 192, 'if ranges[i] &lt;= self.ResponseDist*1.5:', { size: 8, mono: true, fill: '#8b949e' }) +
    txt(530, 206, 'self.Left_warning += 1', { size: 8, mono: true, fill: '#8b949e' }) +
    txt(530, 220, 'if -90 &lt; -(90 - self.LaserAngle) &lt; angle and', { size: 8, mono: true, fill: '#8b949e' }) +
    txt(530, 234, 'angle&lt;0 and ranges[i] != 0.0:', { size: 8, mono: true, fill: '#8b949e' }) +
    txt(530, 248, 'if ranges[i] &lt;= self.ResponseDist*1.5:', { size: 8, mono: true, fill: '#8b949e' }) +
    txt(530, 262, 'self.Right_warning += 1', { size: 8, mono: true, fill: '#8b949e' }) +
    txt(848, 80, 'L63', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    txt(848, 94, 'L65', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    txt(848, 122, 'L68', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    txt(848, 136, 'L69', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    txt(848, 150, 'L70', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    txt(848, 164, 'L73', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    txt(848, 192, 'L74', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    txt(848, 206, 'L75', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    txt(848, 220, 'L78', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    txt(848, 248, 'L79', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    txt(848, 262, 'L80', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    /* ---------- right: counters ---------- */
    rrect(516, 306, 344, 78, 8, '#111', '#30363d') +
    txt(688, 322, 'warning counters — প্রতি scan-এ reset (L58-60)', { anchor: 'middle', size: 8.5, weight: 700, fill: '#e6edf3' }) +
    rrect(528, 332, 104, 42, 5, '#161b22', '#7ee787') +
    txt(580, 346, 'front_warning', { anchor: 'middle', size: 7, mono: true, weight: 700, fill: '#7ee787' }) +
    txt(580, 366, '0', { anchor: 'middle', size: 15, mono: true, weight: 700, fill: '#e6edf3', id: 'bs-fw' }) +
    txt(612, 348, '+1', { size: 8, weight: 700, fill: '#d2a8ff', id: 'bs-dfw', op: 0 }) +
    rrect(636, 332, 104, 42, 5, '#161b22', '#e3b341') +
    txt(688, 346, 'Left_warning', { anchor: 'middle', size: 7, mono: true, weight: 700, fill: '#e3b341' }) +
    txt(688, 366, '0', { anchor: 'middle', size: 15, mono: true, weight: 700, fill: '#e6edf3', id: 'bs-lw' }) +
    txt(720, 348, '+1', { size: 8, weight: 700, fill: '#d2a8ff', id: 'bs-dlw', op: 0 }) +
    rrect(744, 332, 104, 42, 5, '#161b22', '#4fc3f7') +
    txt(796, 346, 'Right_warning', { anchor: 'middle', size: 7, mono: true, weight: 700, fill: '#4fc3f7' }) +
    txt(796, 366, '0', { anchor: 'middle', size: 15, mono: true, weight: 700, fill: '#e6edf3', id: 'bs-rw' }) +
    /* ---------- bottom strip: legend + notes ---------- */
    '<path d="M48 393h7v7h-7z" fill="#7ee787"/><path d="M156 393h7v7h-7z" fill="#e3b341"/><path d="M262 393h7v7h-7z" fill="#4fc3f7"/><path d="M368 393h7v7h-7z" fill="#d2a8ff"/><path d="M476 393h7v7h-7z" fill="#ff7b72"/>' +
    txt(60, 400, 'front |deg| &lt; 20', { size: 8, fill: '#8b949e' }) +
    txt(168, 400, 'left 0..70', { size: 8, fill: '#8b949e' }) +
    txt(274, 400, 'right -70..0', { size: 8, fill: '#8b949e' }) +
    txt(380, 400, 'overlap 0..20', { size: 8, fill: '#8b949e' }) +
    txt(488, 400, 'hit &lt;= 0.45 m', { size: 8, fill: '#8b949e' }) +
    txt(48, 416, ' ', { size: 7.5, weight: 700, fill: '#e3b341', id: 'bs-stale', op: 0 }) +
    txt(48, 430, 'LaserAngle = 20.0 (L36) · ResponseDist = 0.3 (L38) · conut = 3 (L47) — ring-এর range মান illustrative', { size: 7.5, fill: '#6e7681' }) +
    txt(450, 450, 'source: laser_Avoidance.py L53-L80 · laser_driver.launch.py L31-40', { anchor: 'middle', size: 8, mono: true, fill: '#6e7681' })
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
  host.caption('laser_driver.launch.py দুই lidar-এর ফল merge করে এক 360-degree map বানায়, filter সেটিকেই <code>/scan</code>-এ দেয় (L31-40) — তাই <code>registerScan</code>-এর <code>ranges</code> একটাই fused বৃত্ত। প্রতি scan-এ তিন counter শূন্য (L58-60), তারপর L63-এর loop। ছবিতে deg 0 = সামনে, +deg = বাঁদিক (ROS convention)।');
  host.formula('angle_i = (angle_min + angle_increment * i) * RAD2DEG   [rad -> deg, RAD2DEG = 180/pi]');
  /* --- beat 1: L63 sweep --- */
  show('bs-hl1');
  host.caption('L63 <code>for i in range(len(ranges))</code> — cursor-টা i=0 (deg -180, একদম পেছনে) থেকে বেয়ে বেয়ে হাঁটে; প্রতিটি i মানে <code>ranges</code> অ্যারের একটা দূরত্ব-মান।');
  await host.sleep(700);
  const bsHops = [-180, -144, -108, -72, -36, 0, 36, 72, 108, 144];
  for (let k = 0; k < bsHops.length; k++) { bsAim(bsHops[k]); await host.sleep(230); }
  /* --- beat 2: L65 formula --- */
  host.caption('L65: <code>angle = (scan_data.angle_min + scan_data.angle_increment * i) * RAD2DEG</code> — message-এ কোণ radian-এ (folder 09-এর echo), কিন্তু zone-এর তুলনাগুলো degree-তে; <code>RAD2DEG = 180 / pi</code> (L15)। উদাহরণে (illustrative) i=180 হলে angle = 0 deg — ঠিক সামনের beam।');
  host.formula('i = 180:  (-pi + (pi/180)*180) * (180/pi) = 0 deg   (front)');
  hide('bs-hl1'); show('bs-hl2'); bsAim(0);
  await host.sleep(1700);
  /* --- beat 3: L68-70 front zone --- */
  host.caption('FRONT zone (L68): <code>abs(angle) &lt; self.LaserAngle</code>, LaserAngle = 20.0 (L36) — সবুজ arc মানে ±20 deg। সাথে <code>ranges[i] &lt;= ResponseDist*1.5</code> = 0.3 * 1.5 = 0.45 m — gate-এর ভেতরের beam-গুলো লাল, প্রতিটিতে <code>front_warning += 1</code> (L70)।');
  host.formula('front: |angle| < 20 deg  AND  ranges[i] <= 0.3 * 1.5 = 0.45 m');
  hide('bs-hl2'); show('bs-hl3'); show('bs-fa'); show('bs-gate'); show('bs-gate2');
  bsAim(-12); show('bs-hit1'); q('bs-fw').textContent = '6';
  await host.sleep(650);
  bsAim(0); show('bs-hit2'); q('bs-fw').textContent = '13';
  await host.sleep(650);
  bsAim(12); show('bs-hit3'); q('bs-fw').textContent = '19';
  await host.sleep(900);
  q('bs-stale').textContent = 'stale comment L67: "+/- 30 degrees", L69: "0.825 meters" — আসল code: 20 deg, 0.45 m';
  show('bs-stale');
  host.caption('সতর্কতা: comment বলে ±30 degrees (L67) আর 0.825 meters (L69) — আসল code বলে <b>20 deg</b> আর <b>0.45 m</b>। পুরনো comment, নতুন parameter-মান; code-ই মানা যাবে।');
  await host.sleep(1600);
  /* --- beat 4: L73-75 left zone --- */
  host.caption('LEFT zone (L73): chained comparison <code>angle &lt; (90 - LaserAngle) &lt; 90</code> সাথে <code>angle&gt;0</code> — কার্যত 0 &lt; deg &lt; 70, বাঁ দিকের লম্বা amber অংশ। Comment (L72) বলে 60-90; আসল 0-70 — মানে সামনের zone-এর সাথেই জায়গা ভাগ।');
  host.formula('left: 0 < angle < 90 - 20 = 70 deg   |   right: -70 < angle < 0');
  hide('bs-hl3'); show('bs-hl4'); show('bs-la'); show('bs-lo');
  bsAim(40); q('bs-lw').textContent = '12';
  q('bs-stale').textContent = 'stale comment L72: "between 60 and 90" — আসল span: 0..70';
  await host.sleep(1700);
  /* --- beat 5: L78-80 right zone --- */
  host.caption('RIGHT zone (L78): <code>-90 &lt; -(90 - LaserAngle) &lt; angle</code> সাথে <code>angle&lt;0</code> — চেইনের মাঝের -(90-20) = -70 ধ্রুবক, কার্যত -70 &lt; deg &lt; 0। Comment (L77) বলে -90..-60। তিনটাই আলাদা <code>if</code>, <code>elif</code> নয় — এক beam একাধিক zone-এ ধরা পড়তে পারে।');
  hide('bs-hl4'); show('bs-hl5'); show('bs-ba'); show('bs-ro');
  bsAim(-40); q('bs-rw').textContent = '12';
  q('bs-stale').textContent = 'stale comment L77: "-90..-60" — আসল span: -70..0';
  await host.sleep(1700);
  /* --- beat 6: overlap 0..20 double count --- */
  host.caption('ফাঁদ: 0 &lt; deg &lt; 20 ব্যান্ডটা front আর LEFT দুই zone-এই পড়ে। +5 deg-এর এই beam (0.36 m) দুই শর্তই পূরণ করে — <code>front_warning += 1</code> এবং <code>Left_warning += 1</code>: এক beam, দুই গণনা। (-20..0 ব্যান্ড একই ভাবে RIGHT-এর সাথে ভাগ।)');
  host.formula('0 < angle < 20  ->  front_warning+1 AND Left_warning+1  (double count)');
  hide('bs-hl5'); show('bs-hl6a'); show('bs-hl6b'); show('bs-pa');
  show('bs-ov5'); show('bs-ov5r'); show('bs-ov5t');
  bsAim(5); q('bs-fw').textContent = '20'; q('bs-lw').textContent = '13';
  show('bs-dfw'); show('bs-dlw');
  q('bs-stale').textContent = 'overlap band 0..20 — এক beam, দুই counter-এ গণনা';
  await host.sleep(1900);
  /* --- close --- */
  host.caption('হিসেব: এই demo ring-এ কাছের beam 25টা, কিন্তু গণনা 43 (illustrative) — দুই দিকের overlap থেকে 18টা বাড়তি। L94-এর decision tree এই ফোঁলা সংখ্যাই পড়ে; প্রতি নতুন scan-এ আবার সব শূন্য (L58-60)।');
  await host.sleep(1500);
};

/* ---------- decisionTree ---------- */
/* ---------- decisionTree (part 11) — laser_Avoidance.py L89-L99 ----------
   Decision-ladder head: three counters vs conut = 3 (stale comment L91
   says 10), branch 1 trapped body incl. the comment-admitted forward bug
   (L96), first-match-wins elif semantics, the ==3 boundary gap (strict <
   in branches 6-9) with a truth table, then preview of the lower ladder.
   Counter values in the meters are illustrative. Prefix dt-. */

function dtMeter(x, y, label, colr, idp) {
  let s = txt(x, y + 10, label, { size: 8, mono: true, weight: 700, fill: colr });
  for (let i = 1; i <= 8; i++) {
    const sx = x + 70 + (i - 1) * 21;
    s += rrect(sx, y, 19, 13, 2, '#161b22', '#30363d');
    s += rrect(sx, y, 19, 13, 2, i <= 3 ? colr : '#ff7b72', 'none',
               ' id="' + idp + i + '" opacity="0"');
  }
  s += txt(x + 248, y + 10, '= 0', { size: 8.5, mono: true, weight: 700, fill: '#e6edf3', id: idp + 'v' });
  s += rrect(x + 272, y - 1, 92, 15, 3, '#0d1117', '#30363d', ' id="' + idp + 'c"');
  s += txt(x + 318, y + 10, 'waiting', { anchor: 'middle', size: 6.5, mono: true, fill: '#8b949e', id: idp + 'ct' });
  return s;
}

ANIMS.decisionTree = async function (host) {
  /* lower ladder preview rows (revealed in the last beat) */
  const dtRows = [
    ['4', 'F&gt;3 · L&gt;3 · R&lt;=3 — ডানে ঘোরা', 'L116'],
    ['6', 'F&gt;3 · L&lt;3 · R&lt;3 — বাঁয়ে ঘোরা', 'L129'],
    ['7', 'F&lt;3 · L&gt;3 · R&gt;3 — ডানে ঘোরা · sleep(0.4)', 'L137'],
    ['8', 'F&lt;3 · L&gt;3 · R&lt;=3 — ডানে ঘোরা', 'L145'],
    ['9', 'F&lt;3 · L&lt;=3 · R&gt;3 — বাঁয়ে ঘোরা', 'L153'],
    ['10', 'F&lt;=3 · L&lt;=3 · R&lt;=3 — সব clear, এগোনো', 'L161']
  ];
  const dtYs = [296, 314, 332, 350, 368, 386];
  let dtPrev = '';
  for (let k = 0; k < dtRows.length; k++) {
    const y = dtYs[k];
    dtPrev += '<g id="dt-g' + dtRows[k][0] + '" opacity="0">' +
      rrect(62, y, 362, 16, 3, '#0d1117', '#30363d') +
      txt(70, y + 11.5, dtRows[k][0] + ' ·', { size: 7.5, mono: true, weight: 700, fill: '#e3b341' }) +
      txt(92, y + 11.5, dtRows[k][1], { size: 7.5, mono: true, fill: '#c9d1d9' }) +
      txt(416, y + 11.5, dtRows[k][2], { anchor: 'end', size: 6.5, mono: true, fill: '#6e7681' }) +
      '</g>';
  }
  /* boundary-gap truth table (illustrative combos, checked against the code) */
  const dtTab = [
    ['front=5 · Left=2 · Right=2', 'branch 6', '#7ee787'],
    ['front=5 · Left=3 · Right=2', 'NO MATCH', '#ff7b72'],
    ['front=5 · Left=2 · Right=3', 'NO MATCH', '#ff7b72'],
    ['front=5 · Left=3 · Right=3', 'NO MATCH', '#ff7b72'],
    ['front=3 · Left=5 · Right=5', 'NO MATCH', '#ff7b72'],
    ['front=3 · Left=2 · Right=2', 'branch 10', '#7ee787']
  ];
  let dtTable = '';
  for (let k = 0; k < dtTab.length; k++) {
    const y = 292 + k * 16;
    dtTable += '<g id="dt-q' + (k + 1) + '" opacity="0">' +
      rrect(472, y, 250, 14, 3, '#0d1117', '#30363d') +
      txt(480, y + 10.5, dtTab[k][0], { size: 7.5, mono: true, fill: '#c9d1d9' }) +
      rrect(732, y, 100, 14, 3, '#0d1117', dtTab[k][2]) +
      txt(782, y + 10.5, dtTab[k][1], { anchor: 'middle', size: 7.5, mono: true, weight: 700, fill: dtTab[k][2] }) +
      '</g>';
  }

  const svg = host.setStage(
    txt(450, 26, 'সিদ্ধান্ত-বৃক্ষের মাথা: তিন counter বনাম conut = 3 — প্রথম ম্যাচই জেতে', { anchor: 'middle', size: 14, weight: 600, fill: '#e3b341' }) +

    rrect(40, 44, 400, 134, 8, '#0d1117', '#2a3442') +
    txt(56, 62, 'COUNTERS — illustrative মান', { size: 9.5, weight: 700, fill: '#e6edf3' }) +
    txt(424, 62, 'vs conut = 3 (L47)', { anchor: 'end', size: 8, mono: true, weight: 700, fill: '#e3b341' }) +
    dtMeter(56, 76, 'front_warning', '#e3b341', 'dt-f') +
    dtMeter(56, 104, 'Left_warning', '#4fc3f7', 'dt-l') +
    dtMeter(56, 132, 'Right_warning', '#d2a8ff', 'dt-r') +
    path('M188 70L188 150', '#e3b341', 1.2, ' stroke-dasharray="3 2"') +
    '<g id="dt-stale" opacity="0">' +
      rrect(56, 152, 206, 24, 4, '#0d1117', '#e3b341') +
      txt(64, 163, 'L91 comment: "self.conut is 10"', { size: 7, mono: true, fill: '#e3b341' }) +
      txt(64, 173, '— STALE: আসল মান 3 (L47), code-ই truth', { size: 6.5, fill: '#8b949e' }) +
    '</g>' +
    '<g id="dt-leg" opacity="0">' +
      txt(286, 165, '&lt;3 clear', { size: 7, mono: true, weight: 700, fill: '#7ee787' }) +
      txt(334, 165, '==3 GAP', { size: 7, mono: true, weight: 700, fill: '#e3b341' }) +
      txt(380, 165, '&gt;3 blocked', { size: 7, mono: true, weight: 700, fill: '#ff7b72' }) +
    '</g>' +

    rrect(40, 190, 400, 220, 8, '#0d1117', '#2a3442') +
    txt(56, 208, 'DECISION LADDER (L94-L165)', { size: 9.5, weight: 700, fill: '#e6edf3' }) +
    txt(424, 208, 'if/elif — উপর থেকে নিচে', { anchor: 'end', size: 7.5, fill: '#8b949e' }) +
    path('M52 226L52 400', '#30363d', 2) +
    circ(52, 242, 4, '#e3b341', ' id="dt-probe" opacity="0"') +
    rrect(62, 222, 362, 40, 5, '#161b22', '#30363d', ' id="dt-r1"') +
    rrect(68, 230, 16, 24, 3, '#0d1117', '#ff7b72') +
    txt(76, 246, '1', { anchor: 'middle', size: 10, mono: true, weight: 700, fill: '#ff7b72' }) +
    txt(92, 240, 'front&gt;3 · Left&gt;3 · Right&gt;3', { size: 8.5, mono: true, weight: 700, fill: '#c9d1d9' }) +
    txt(92, 256, 'L94 — তিন দিকই বন্ধ: TRAPPED', { size: 7, fill: '#8b949e' }) +
    txt(416, 240, 'TRUE', { anchor: 'end', size: 8, mono: true, weight: 700, fill: '#7ee787', id: 'dt-j1', op: 0 }) +
    '<g id="dt-g2" opacity="0">' +
      rrect(62, 268, 362, 20, 4, '#161b22', '#30363d', ' id="dt-r2"') +
      txt(70, 282, '2 ·', { size: 7.5, mono: true, weight: 700, fill: '#7ee787' }) +
      txt(90, 282, 'front&gt;3 · Left&lt;=3 · Right&gt;3 — বাঁয়ে ঘোরা', { size: 7.5, mono: true, fill: '#c9d1d9' }) +
      txt(416, 282, 'L102', { anchor: 'end', size: 6.5, mono: true, fill: '#6e7681' }) +
      txt(380, 282, 'TRUE', { anchor: 'end', size: 7.5, mono: true, weight: 700, fill: '#7ee787', id: 'dt-j2' }) +
    '</g>' +
    dtPrev +
    txt(62, 407, 'স্ক্যান শেষ: কোনো শাখাই TRUE নয়', { size: 7, mono: true, weight: 700, fill: '#ff7b72', id: 'dt-nope', op: 0 }) +
    txt(416, 407, 'পরের part: প্রতিটা শাখার twist vector', { anchor: 'end', size: 7, weight: 700, fill: '#d2a8ff', id: 'dt-next', op: 0 }) +

    rrect(456, 44, 404, 190, 8, '#111', '#30363d') +
    txt(472, 62, 'BRANCH 1 — শরীর (L95-L99)', { size: 9.5, weight: 700, fill: '#e6edf3' }) +
    txt(844, 62, 'publish হলে চাকা চলে', { anchor: 'end', size: 7, fill: '#8b949e' }) +
    txt(472, 84, 'print (\'1, there are obstacles in the left and right, turn right\')', { size: 8, mono: true, fill: '#7ee787', id: 'dt-a95', op: 0 }) +
    txt(844, 84, 'L95', { anchor: 'end', size: 6.5, mono: true, fill: '#6e7681', id: 'dt-a95r', op: 0 }) +
    txt(472, 106, 'twist.linear.x = self.linear', { size: 8.5, mono: true, fill: '#e6edf3', id: 'dt-a96', op: 0 }) +
    '<g id="dt-b96" opacity="0">' +
      rrect(622, 96, 42, 14, 3, '#0d1117', '#7ee787') +
      txt(643, 106, '+0.2', { anchor: 'middle', size: 8, mono: true, weight: 700, fill: '#7ee787' }) +
      txt(674, 106, 'FORWARD', { size: 7.5, weight: 700, fill: '#7ee787' }) +
    '</g>' +
    '<g id="dt-bug" opacity="0">' +
      rrect(726, 96, 118, 14, 3, '#0d1117', '#ff7b72') +
      txt(785, 106, 'BUG — comment-স্বীকৃত', { anchor: 'middle', size: 6.5, fill: '#ff7b72' }) +
    '</g>' +
    txt(472, 122, 'L96 comment: "it should be negative to reverse" — তবু সামনে যাওয়া', { size: 7, fill: '#e3b341', id: 'dt-bugx', op: 0 }) +
    txt(472, 144, 'twist.angular.z = -self.angular', { size: 8.5, mono: true, fill: '#e6edf3', id: 'dt-a97', op: 0 }) +
    txt(844, 144, 'L97', { anchor: 'end', size: 6.5, mono: true, fill: '#6e7681', id: 'dt-a97r', op: 0 }) +
    '<g id="dt-b97" opacity="0">' +
      rrect(640, 134, 42, 14, 3, '#0d1117', '#e3b341') +
      txt(661, 144, '-0.2', { anchor: 'middle', size: 8, mono: true, weight: 700, fill: '#e3b341' }) +
      txt(692, 144, 'ডানে ঘোরা', { size: 7.5, weight: 700, fill: '#e3b341' }) +
    '</g>' +
    txt(472, 166, 'self.pub_vel.publish(twist)', { size: 8.5, mono: true, fill: '#e6edf3', id: 'dt-a98', op: 0 }) +
    txt(844, 166, 'L98', { anchor: 'end', size: 6.5, mono: true, fill: '#6e7681', id: 'dt-a98r', op: 0 }) +
    '<g id="dt-b98" opacity="0">' +
      rrect(640, 156, 62, 14, 3, '#0d1117', '#4fc3f7') +
      txt(671, 166, '/cmd_vel', { anchor: 'middle', size: 7.5, mono: true, weight: 700, fill: '#4fc3f7' }) +
    '</g>' +
    txt(472, 188, 'sleep(0.2)', { size: 8.5, mono: true, fill: '#e6edf3', id: 'dt-a99', op: 0 }) +
    txt(844, 188, 'L99', { anchor: 'end', size: 6.5, mono: true, fill: '#6e7681', id: 'dt-a99r', op: 0 }) +
    txt(540, 188, '0.2s executor অবরুদ্ধ — নতুন scan লাইনে দাঁড়ায়', { size: 7, fill: '#8b949e', id: 'dt-b99', op: 0 }) +

    rrect(456, 246, 404, 164, 8, '#111', '#30363d') +
    txt(472, 264, 'BOUNDARY GAP — == 3 কোন পক্ষেই নয়', { size: 9.5, weight: 700, fill: '#e3b341' }) +
    txt(844, 264, 'strict &lt;: L129 L137 L145 L153', { anchor: 'end', size: 7, mono: true, fill: '#8b949e' }) +
    txt(472, 282, '&gt;3 = blocked আর &lt;3 = clear — কড়া &lt; হলে ==3 দুই-ই নয়', { size: 7.5, fill: '#c9d1d9', id: 'dt-dleg', op: 0 }) +
    dtTable +
    txt(472, 398, 'NO MATCH scan-এ publish নেই — /cmd_vel-এ আগের commandই থাকে (stale motion)', { size: 7.5, weight: 700, fill: '#e3b341', id: 'dt-dres', op: 0 }) +

    txt(450, 440, 'source: laser_Avoidance.py L89-L99 · conut L47 · stale comment L91 · ladder L94-L165', { anchor: 'middle', size: 8, mono: true, fill: '#6e7681' })
  );

  const q = id => svg.querySelector('#' + id);
  const show = id => q(id).setAttribute('opacity', 1);
  const dtSet = (idp, n) => {
    for (let i = 1; i <= 8; i++) q(idp + i).setAttribute('opacity', i <= n ? 1 : 0);
    q(idp + 'v').textContent = '= ' + n;
  };
  const dtChip = (idp, s, colr) => {
    q(idp + 'ct').textContent = s;
    q(idp + 'ct').setAttribute('fill', colr);
    q(idp + 'c').setAttribute('stroke', colr);
  };
  const dtVerdict = (id, s, colr) => {
    q(id).textContent = s;
    q(id).setAttribute('fill', colr);
  };

  host.caption('registerScan-এর শেষ পর্ব: তিনটা counter — <code>front_warning</code>, <code>Left_warning</code>, <code>Right_warning</code> — প্রত্যেকটা <code>conut = 3</code>-এর সঙ্গে তুলনা হয় (L47)। প্রতি scan-এ গণনা শূন্য থেকে শুরু (L57-60) — মিটারের সংখ্যা <b>illustrative</b>।');
  host.formula('conut = 3 (L47) · branch 1 test (L94): front_warning > 3 and Left_warning > 3 and Right_warning > 3');
  await host.sleep(1500);

  show('dt-stale');
  host.caption('প্রথম ফাঁদটাই comment-এ: L91 দাবি করে <code>self.conut is 10</code> — অথচ constructor-এ আসল মান <b>3</b> (L47)। এই সিরিজে বারবার দেখা নিয়ম: comment নয়, <b>code-ই truth</b>। সব তুলনা এই 3-এর সঙ্গেই।');
  host.formula('L91 comment: conut is 10 · code truth (L47): self.conut = 3');
  await host.sleep(1500);

  dtSet('dt-f', 5); dtSet('dt-l', 4); dtSet('dt-r', 6);
  dtChip('dt-f', 'BLOCKED', '#ff7b72');
  dtChip('dt-l', 'BLOCKED', '#ff7b72');
  dtChip('dt-r', 'BLOCKED', '#ff7b72');
  q('dt-r1').setAttribute('stroke', '#ff7b72');
  q('dt-r1').setAttribute('stroke-width', '1.6');
  show('dt-probe');
  show('dt-j1'); dtVerdict('dt-j1', 'TRUE', '#7ee787');
  show('dt-a95'); show('dt-a95r');
  host.caption('তিন দিকের counter-ই 3 ছাড়িয়ে গেছে (illustrative: 5, 4, 6) → L94-এর শর্ত TRUE: branch 1, <b>trapped</b>। Terminal-এ ছাপে <code>1, there are obstacles in the left and right, turn right</code> (L95)।');
  host.formula('illustrative: front=5 > 3 and Left=4 > 3 and Right=6 > 3 -> branch 1 TRUE');
  await host.sleep(1600);

  show('dt-a96'); show('dt-b96'); show('dt-bug'); show('dt-bugx');
  host.caption('এবার শরীরের প্রথম লাইনটাই সবচেয়ে মজার: <code>twist.linear.x = self.linear</code> = <b>+0.2</b> — অর্থাৎ <b>সামনে</b> যাওয়া! আটকে-যাওয়া অবস্থায় পেছনাতে চাইলে negative লাগত। Source-এর নিজের comment-ই স্বীকার করে (L96): <i>it should be negative to reverse, but we follow the original logic</i>।');
  await host.sleep(1700);

  show('dt-a97'); show('dt-a97r'); show('dt-b97');
  show('dt-a98'); show('dt-a98r'); show('dt-b98');
  show('dt-a99'); show('dt-a99r'); show('dt-b99');
  host.caption('বাকি তিন লাইন: <code>twist.angular.z = -self.angular</code> = <b>-0.2</b> (ঘড়ির কাঁটার দিকে — ডানে ঘোরা), <code>self.pub_vel.publish(twist)</code> চাকাকে <code>/cmd_vel</code>-এ বলে, তারপর <code>sleep(0.2)</code> (L97-L99)। Sleep শেষ না হওয়া পর্যন্ত পরের scan লাইনে অপেক্ষা করে।');
  host.formula('twist.linear.x = +0.2 · twist.angular.z = -0.2 · publish(/cmd_vel) · sleep(0.2)');
  await host.sleep(1700);

  host.caption('<code>if/elif</code> চেইন মানে উপর-থেকে-নিচে স্ক্যান — <b>প্রথম TRUE শাখাই চলে</b>, তার নিচের সব শাখা ওই scan-এ বাদ। এখানে তিন counter-ই &gt; 3, তাই স্ক্যান প্রথম ধাপেই থেমে যায়: branch 1।');
  host.formula('if/elif ladder = top-down scan · first TRUE row runs · rows below skipped');
  await host.sleep(1600);

  dtSet('dt-l', 2); dtSet('dt-r', 5);
  dtChip('dt-l', 'CLEAR', '#7ee787');
  dtChip('dt-r', 'BLOCKED', '#ff7b72');
  q('dt-r1').setAttribute('stroke', '#30363d');
  q('dt-r1').setAttribute('stroke-width', '1');
  dtVerdict('dt-j1', 'FALSE', '#ff7b72');
  show('dt-g2');
  q('dt-r2').setAttribute('stroke', '#7ee787');
  dtVerdict('dt-j2', 'TRUE', '#7ee787');
  q('dt-probe').setAttribute('cy', 278);
  host.caption('পরের scan (counter প্রতি বার reset, L57-60): এবার illustrative 5, 2, 5 — বাঁ দিক clear। Branch 1-এর শর্ত ভাঙে, স্ক্যান এক ধাপ নামে, branch 2 (L102) TRUE: বাঁয়ে ঘোরা। প্রথম ম্যাচেই থামা — এটাই <b>first match wins</b>।');
  await host.sleep(1700);

  dtSet('dt-l', 3); dtSet('dt-r', 2);
  dtChip('dt-l', 'GAP ==3', '#e3b341');
  dtChip('dt-r', 'CLEAR', '#7ee787');
  q('dt-r2').setAttribute('stroke', '#30363d');
  dtVerdict('dt-j2', 'FALSE', '#ff7b72');
  q('dt-probe').setAttribute('cy', 402);
  show('dt-nope');
  show('dt-leg'); show('dt-dleg');
  host.caption('এবার সবচেয়ে সূক্ষ্ম ফাঁদ: branch 6-9-এ কড়া <code>&lt;</code> (L129, L137, L145, L153)। Counter ঠিক <b>== 3</b> হলে সে দিক blocked-ও নয় (<code>&gt;3</code> লাগে), clear-ও নয় (<code>&lt;3</code> লাগে)। illustrative 5, 3, 2: branch 1 নয়, 2 নয়, 6-ও নয়… <b>কোনো শাখাই TRUE নয়</b>।');
  host.formula('counter == conut: not > 3 (blocked) and not < 3 (clear) -> neither · branches 6-9 use strict <');
  await host.sleep(1800);

  show('dt-q1'); show('dt-q2'); show('dt-q3'); show('dt-q4'); show('dt-q5'); show('dt-q6');
  show('dt-dres');
  host.caption('ফল: সেই scan-এ <code>publish</code>-ই হয় না, তাই <code>/cmd_vel</code>-এ আগের command বসে থাকে — <b>stale motion</b>। conut = 3 ছোট সংখ্যা, একটা beam-এর বাড়া-কমাতেই গণনা ==3-এ পড়তে পারে। টেবিলে কম্বোগুলো — আর খেয়াল করুন branch 10-এর <code>&lt;=</code> কিন্তু ==3-কে নেয়।');
  host.formula('no branch TRUE -> no publish that scan -> previous /cmd_vel command stays (stale motion)');
  await host.sleep(1800);

  show('dt-g4'); show('dt-g6'); show('dt-g7'); show('dt-g8'); show('dt-g9'); show('dt-g10');
  show('dt-next');
  host.caption('ল্যাডার এখানেই শেষ নয়: 2, 4, 6, 7, 8, 9, 10 নিচে সাজানো — 3 আর 5 নম্বর শাখা source-এই নেই (numbering jump, as-is)। পরের part-এ প্রতিটা শাখার <code>twist</code> vector আলাদা করে আঁকা হবে।');
  host.formula('ladder order: 1, 2, 4, 6, 7, 8, 9, 10 (no 3, no 5) · strict < in 6 and 7/8/9 (front)');
  await host.sleep(1600);
};

/* ---------- cmdVelVectors ---------- */
/* ============ folder-11 v1 anim - cmdVelVectors (part 12) ============
   laser_Avoidance.py L101-L134: branches 2, 4 and 6 - the three
   zero-linear turn branches - plus the two DEAD inner double-checks
   (L109-113, L122-126) and the sleep()-blocks-the-spin executor note.
   Grounding: linear=0.2 (L32), angular=0.2 (L34), conut=3 (L47),
   gate = ResponseDist*1.5 = 0.45 m (L69). Prints: L103 "2, there is
   an obstacle in the middle right, turn left", L117 "4. There is an
   obstacle in the middle left, turn right", L130 "6, there is an
   obstacle in the middle, turn left". Zone ifs: front L68, left L73,
   right L78. Stage 900x460, id prefix cv- on every element and every
   local helper. No emoji, no Unicode arrows in stage text, &lt;/&gt;
   entities inside setStage strings, raw ASCII math only in formula. */

/* deg: 0 = up (robot front), +90 = screen left (robot left) */
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

ANIMS.cmdVelVectors = async function (host) {
  const svg = host.setStage(
    txt(450, 24, 'শাখা ২ / ৪ / ৬ — ঘুরপাকের তিন আদেশ: linear.x = 0.0, দিক ঠিক করে angular.z', { anchor: 'middle', size: 14.5, weight: 600, fill: '#ffb454' }) +
    rrect(40, 42, 260, 300, 8, '#0d1117', '#2a3442') +
    txt(170, 60, 'TOP VIEW — তিন zone-এর গণনা (সংখ্যা illustrative)', { anchor: 'middle', size: 9.5, weight: 700, fill: '#e6edf3' }) +
    cvWedge(170, 210, 88, -20, 20, 'cv-zf') +
    cvWedge(170, 210, 88, 70, 90, 'cv-zl') +
    cvWedge(170, 210, 88, -90, -70, 'cv-zr') +
    txt(170, 112, 'front · L68', { anchor: 'middle', size: 7.5, mono: true, fill: '#8b949e' }) +
    txt(44, 178, 'left · L73', { size: 7.5, mono: true, fill: '#8b949e' }) +
    txt(296, 178, 'right · L78', { anchor: 'end', size: 7.5, mono: true, fill: '#8b949e' }) +
    txt(170, 156, '?', { anchor: 'middle', size: 13, weight: 700, mono: true, fill: '#8b949e', id: 'cv-cf' }) +
    txt(104, 206, '?', { anchor: 'middle', size: 13, weight: 700, mono: true, fill: '#8b949e', id: 'cv-cl' }) +
    txt(236, 206, '?', { anchor: 'middle', size: 13, weight: 700, mono: true, fill: '#8b949e', id: 'cv-cr' }) +
    rrect(158, 186, 24, 48, 5, '#21262d', '#8b949e') +
    '<path d="M170 176 L176 188 L164 188 Z" fill="#4fc3f7"/>' +
    txt(170, 250, 'robot', { anchor: 'middle', size: 7, fill: '#8b949e' }) +
    cvArcArrow(170, 210, 36, -55, 150, 'cv-tccw', 'cv-tccwh', '#4fc3f7', 2.2) +
    cvArcArrow(170, 210, 36, 55, -150, 'cv-tcw', 'cv-tcwh', '#e3b341', 2.2) +
    cvArcArrow(170, 210, 48, 50, -140, 'cv-never', 'cv-neverh', '#ff7b72', 1.8, 'stroke-dasharray="5 4"') +
    cvArcArrow(170, 210, 48, -50, 140, 'cv-never2', 'cv-never2h', '#ff7b72', 1.8, 'stroke-dasharray="5 4"') +
    txt(170, 286, 'ভেতরের চেক চায়: ডানপাশ খালি — right কম', { anchor: 'middle', size: 7.5, fill: '#ff7b72', id: 'cv-nev1', op: 0 }) +
    txt(170, 299, 'কিন্তু ঢোকার শর্তই ছিল: ডানপাশ ভরা — right বেশি', { anchor: 'middle', size: 7.5, fill: '#ff7b72', id: 'cv-nev2', op: 0 }) +
    txt(170, 312, 'দুটো একসাথে অসম্ভব — L109-113 কখনো চলে না', { anchor: 'middle', size: 7.5, weight: 700, fill: '#ff7b72', id: 'cv-nev3', op: 0 }) +
    txt(170, 336, 'লাল = বাধা · সবুজ = খোলা · সীমা conut = 3 (L47)', { anchor: 'middle', size: 7.5, fill: '#8b949e' }) +
    rrect(312, 42, 170, 300, 8, '#0d1117', '#2a3442') +
    txt(397, 60, 'VECTOR DIAL', { anchor: 'middle', size: 9.5, weight: 700, fill: '#e6edf3' }) +
    txt(397, 78, 'linear.x — সোজা তীর', { anchor: 'middle', size: 8, weight: 700, fill: '#c9d1d9' }) +
    '<path d="M397 96 L397 152" stroke="#6e7681" stroke-width="1.5" fill="none"/>' +
    '<path d="M397 86 L402 96 L392 96 Z" fill="#8b949e"/>' +
    '<path d="M397 162 L402 152 L392 152 Z" fill="#8b949e"/>' +
    '<path d="M397 148 L397 104" stroke="#7ee787" stroke-width="2.4" opacity="0.14" fill="none"/>' +
    '<path d="M397 97 L403 108 L391 108 Z" fill="#7ee787" opacity="0.14"/>' +
    txt(408, 97, '+ সামনে', { size: 7.5, fill: '#7ee787' }) +
    txt(408, 153, '- পেছনে', { size: 7.5, fill: '#ff7b72' }) +
    rrect(347, 168, 100, 18, 9, '#161b22', '#30363d', ' id="cv-linp"') +
    txt(397, 180.5, 'linear.x = 0.0', { anchor: 'middle', size: 8, mono: true, fill: '#e6edf3' }) +
    txt(397, 202, 'তিন শাখাতেই 0.0 — সোজা তীর জন্মায় না', { anchor: 'middle', size: 7.5, fill: '#8b949e', id: 'cv-lnote', op: 0 }) +
    txt(397, 222, 'angular.z — বাঁকা তীর', { anchor: 'middle', size: 8, weight: 700, fill: '#c9d1d9' }) +
    circ(397, 262, 26, 'none', ' stroke="#30363d" stroke-width="1.5"') +
    cvArcArrow(397, 262, 26, -35, 175, 'cv-acw', 'cv-acwh', '#4fc3f7', 2.4) +
    cvArcArrow(397, 262, 26, 35, -175, 'cv-aw', 'cv-awh', '#e3b341', 2.4) +
    txt(350, 265, 'CCW +', { anchor: 'end', size: 7.5, weight: 700, fill: '#4fc3f7' }) +
    txt(444, 265, 'CW -', { size: 7.5, weight: 700, fill: '#e3b341' }) +
    rrect(332, 298, 130, 20, 10, '#161b22', '#30363d', ' id="cv-angp"') +
    txt(397, 311.5, 'angular.z = ?', { anchor: 'middle', size: 8.5, weight: 700, mono: true, fill: '#e6edf3', id: 'cv-angv' }) +
    txt(397, 334, 'ROS নিয়ম: CCW = ধনাত্মক = বাঁয়ে ঘোরা', { anchor: 'middle', size: 7.5, fill: '#8b949e', id: 'cv-angnote', op: 0 }) +
    rrect(494, 42, 366, 300, 8, '#0d1117', '#2a3442') +
    txt(677, 60, 'শাখা-খাতা — কোন শর্তে কোন Twist (L101-L134)', { anchor: 'middle', size: 9.5, weight: 700, fill: '#e6edf3' }) +
    rrect(506, 70, 342, 80, 6, '#161b22', '#30363d', ' id="cv-r2"') +
    rrect(514, 78, 74, 16, 8, '#0d1117', '#4fc3f7') +
    txt(551, 89.5, 'branch 2', { anchor: 'middle', size: 7.5, weight: 700, fill: '#4fc3f7' }) +
    txt(600, 89, 'L101-107', { size: 7.5, mono: true, fill: '#6e7681' }) +
    txt(514, 106, 'front&gt;conut · left&lt;=conut · right&gt;conut  (L102)', { size: 8, mono: true, fill: '#c9d1d9' }) +
    txt(514, 121, 'linear.x = 0.0 (L104) · angular.z = +angular = +0.2 (L105)', { size: 8, mono: true, weight: 700, fill: '#4fc3f7' }) +
    txt(514, 135, 'publish /cmd_vel L106 · sleep(0.2) L107 · print L103', { size: 7.5, fill: '#8b949e' }) +
    rrect(742, 78, 96, 16, 8, '#3d1d20', '#f85149', ' id="cv-d2" opacity="0"') +
    txt(790, 89.5, 'DEAD L109-113', { anchor: 'middle', size: 7, weight: 700, fill: '#ff7b72', id: 'cv-d2t', op: 0 }) +
    rrect(506, 158, 342, 80, 6, '#161b22', '#30363d', ' id="cv-r4"') +
    rrect(514, 166, 74, 16, 8, '#0d1117', '#e3b341') +
    txt(551, 177.5, 'branch 4', { anchor: 'middle', size: 7.5, weight: 700, fill: '#e3b341' }) +
    txt(600, 177, 'L115-121', { size: 7.5, mono: true, fill: '#6e7681' }) +
    txt(514, 194, 'front&gt;conut · left&gt;conut · right&lt;=conut  (L116)', { size: 8, mono: true, fill: '#c9d1d9' }) +
    txt(514, 209, 'linear.x = 0.0 (L118) · angular.z = -angular = -0.2 (L119)', { size: 8, mono: true, weight: 700, fill: '#e3b341' }) +
    txt(514, 223, 'publish /cmd_vel L120 · sleep(0.2) L121 · print L117', { size: 7.5, fill: '#8b949e' }) +
    rrect(742, 166, 96, 16, 8, '#3d1d20', '#f85149', ' id="cv-d4" opacity="0"') +
    txt(790, 177.5, 'DEAD L122-126', { anchor: 'middle', size: 7, weight: 700, fill: '#ff7b72', id: 'cv-d4t', op: 0 }) +
    rrect(506, 246, 342, 80, 6, '#161b22', '#30363d', ' id="cv-r6"') +
    rrect(514, 254, 74, 16, 8, '#0d1117', '#7ee787') +
    txt(551, 265.5, 'branch 6', { anchor: 'middle', size: 7.5, weight: 700, fill: '#7ee787' }) +
    txt(600, 265, 'L128-134', { size: 7.5, mono: true, fill: '#6e7681' }) +
    txt(514, 282, 'front&gt;conut · left&lt;conut · right&lt;conut  (L129)', { size: 8, mono: true, fill: '#c9d1d9' }) +
    txt(840, 282, '&lt; কঠোর', { anchor: 'end', size: 7.5, weight: 700, fill: '#e3b341', id: 'cv-strict', op: 0 }) +
    txt(514, 297, 'linear.x = 0.0 (L131) · angular.z = +angular = +0.2 (L132)', { size: 8, mono: true, weight: 700, fill: '#7ee787' }) +
    txt(514, 311, 'publish /cmd_vel L133 · sleep(0.2) L134 · print L130', { size: 7.5, fill: '#8b949e' }) +
    rrect(742, 254, 96, 16, 8, '#161b22', '#30363d', ' id="cv-nb6" opacity="0"') +
    txt(790, 265.5, 'ভেতরের চেক নেই', { anchor: 'middle', size: 7, fill: '#8b949e', id: 'cv-nb6t', op: 0 }) +
    rrect(40, 352, 820, 84, 8, '#111', '#30363d') +
    txt(60, 370, 'EXECUTOR — single-thread spin-এর সময়রেখা (illustrative)', { size: 9, weight: 700, fill: '#e6edf3' }) +
    '<path d="M70 406 L830 406" stroke="#30363d" stroke-width="2" fill="none"/>' +
    txt(830, 394, 'সময় -&gt;', { anchor: 'end', size: 7, fill: '#6e7681' }) +
    circ(96, 406, 5, '#4fc3f7') +
    txt(96, 394, '/scan', { anchor: 'middle', size: 7, mono: true, fill: '#4fc3f7' }) +
    circ(210, 406, 5, '#7ee787') +
    txt(210, 394, 'publish /cmd_vel', { anchor: 'middle', size: 7, mono: true, fill: '#7ee787' }) +
    rrect(258, 398, 210, 16, 3, '#f85149', '#ff7b72', ' fill-opacity="0.12" stroke-dasharray="4 3" id="cv-frz" opacity="0"') +
    txt(363, 426, 'sleep(0.2) — callback আটকে', { anchor: 'middle', size: 7.5, fill: '#ff7b72', id: 'cv-frzt', op: 0 }) +
    circ(300, 406, 5, '#e3b341', ' id="cv-q1" opacity="0"') +
    txt(300, 388, 'নতুন /scan অপেক্ষায়', { anchor: 'middle', size: 6.5, fill: '#e3b341', id: 'cv-q1t', op: 0 }) +
    circ(420, 406, 5, '#d2a8ff', ' id="cv-q2" opacity="0"') +
    txt(445, 388, '/JoyState অপেক্ষায়', { anchor: 'middle', size: 6.5, fill: '#d2a8ff', id: 'cv-q2t', op: 0 }) +
    circ(500, 406, 5, '#7ee787', ' id="cv-res" opacity="0"') +
    txt(500, 426, 'ঘুম শেষ — spin আবার', { anchor: 'middle', size: 7, fill: '#7ee787', id: 'cv-rest', op: 0 }) +
    circ(590, 406, 5, '#4fc3f7', ' id="cv-ns" opacity="0"') +
    txt(590, 426, 'পরের /scan ঢোকে', { anchor: 'middle', size: 7, fill: '#4fc3f7', id: 'cv-nst', op: 0 }) +
    txt(830, 426, 'pause শেষ না হলে কিছুই না', { anchor: 'end', size: 7, fill: '#8b949e', id: 'cv-tnote', op: 0 }) +
    txt(450, 450, 'source: laser_Avoidance.py L101-L134 · linear=0.2 L32 · angular=0.2 L34 · conut=3 L47 · gate 0.45m L69', { anchor: 'middle', size: 7.5, mono: true, fill: '#6e7681' })
  );
  const q = id => svg.querySelector('#' + id);
  const show = id => q(id).setAttribute('opacity', 1);
  const hide = id => q(id).setAttribute('opacity', 0);
  const cvZone = (wid, cid, n, ok) => {
    const w = q(wid), col = ok ? '#7ee787' : '#f85149';
    w.setAttribute('stroke', ok ? '#7ee787' : '#ff7b72');
    w.setAttribute('fill', col);
    w.setAttribute('fill-opacity', 0.18);
    w.setAttribute('opacity', 1);
    q(cid).textContent = String(n);
    q(cid).setAttribute('fill', ok ? '#7ee787' : '#ff7b72');
  };
  const cvRow = (id, col) => q(id).setAttribute('stroke', col);

  show('cv-angnote');
  host.caption('এই অংশের তিনটা শাখায় (২, ৪, ৬) <code>linear.x = 0.0</code> — সোজা এগোনোর তীর নেই, ফয়সালা করে <code>angular.z</code>-এর বাঁকা তীর। ROS-এর নিয়মে ধনাত্মক <code>angular.z</code> = বাঁয়ে ঘোরা (CCW), ঋণাত্মক = ডানে (CW)।');
  host.formula('cmd_vel message = (linear.x, angular.z) ; angular.z > 0 = CCW = left , angular.z < 0 = CW = right');
  await host.sleep(1500);

  cvZone('cv-zf', 'cv-cf', 26, false);
  cvZone('cv-zl', 'cv-cl', 2, true);
  cvZone('cv-zr', 'cv-cr', 31, false);
  show('cv-tccw'); show('cv-tccwh');
  show('cv-acw'); show('cv-acwh');
  q('cv-angv').textContent = 'angular.z = +0.2';
  q('cv-angp').setAttribute('stroke', '#4fc3f7');
  q('cv-linp').setAttribute('stroke', '#4fc3f7');
  cvRow('cv-r2', '#4fc3f7');
  show('cv-lnote');
  host.caption('<b>শাখা ২ (L101-107):</b> সামনে ও ডানে বাধা, বাঁয়ে খোলা — <code>print</code> বলে <i>2, there is an obstacle in the middle right, turn left</i> (L103)। <code>twist.linear.x = 0.0</code> (L104), <code>twist.angular.z = self.angular</code> (L105) = <b>+0.2</b> — dial-এ নীল CCW তীর, robot জায়গায় দাঁড়িয়ে বাঁয়ে ঘোরে। <code>publish</code> L106, <code>sleep(0.2)</code> L107।');
  host.formula('branch 2 @ L102: front>3 AND left<=3 AND right>3 -> Twist (0.0, +0.2) -> publish L106 -> sleep 0.2 s L107');
  await host.sleep(1600);

  show('cv-d2'); show('cv-d2t');
  show('cv-never'); show('cv-neverh');
  show('cv-nev1'); show('cv-nev2'); show('cv-nev3');
  host.caption('ভেতরের double-check (L108-113): <code>if Left_warning &gt; conut and Right_warning &lt;= conut</code> হলে ডানে ঘুরিয়ে দিত — কিন্তু শাখায় ঢোকতেই তো <code>Right_warning &gt; conut</code> লেগেছিল (L102)। দুটো একসাথে সত্য হতে পারে না — <b>এই অংশ কখনো চলে না (dead code)</b>, ভেতরের <code>sleep(0.5)</code>-ও (L113) অবজ্ঞাত।');
  host.formula('L102 gate: Right_warning > conut ; L109 gate: Right_warning <= conut -> A AND NOT A = false -> dead code');
  await host.sleep(1700);
  hide('cv-never'); hide('cv-neverh');
  hide('cv-nev1'); hide('cv-nev2'); hide('cv-nev3');
  cvRow('cv-r2', '#30363d');
  cvRow('cv-r4', '#e3b341');
  cvZone('cv-zf', 'cv-cf', 26, false);
  cvZone('cv-zl', 'cv-cl', 27, false);
  cvZone('cv-zr', 'cv-cr', 1, true);
  hide('cv-acw'); hide('cv-acwh'); hide('cv-tccw'); hide('cv-tccwh');
  show('cv-aw'); show('cv-awh'); show('cv-tcw'); show('cv-tcwh');
  q('cv-angv').textContent = 'angular.z = -0.2';
  q('cv-angp').setAttribute('stroke', '#e3b341');
  q('cv-linp').setAttribute('stroke', '#e3b341');
  host.caption('<b>শাখা ৪ (L115-121):</b> আয়নার ছবি — সামনে ও বাঁয়ে বাধা, ডানে খোলা। <code>print</code>: <i>4. There is an obstacle in the middle left, turn right</i> (L117)। <code>twist.linear.x = 0.0</code> (L118), <code>twist.angular.z = -self.angular</code> (L119) = <b>-0.2</b> — এবার ডানদিকে CW বাঁকা তীর। <code>publish</code> L120, <code>sleep(0.2)</code> L121।');
  host.formula('branch 4 @ L116: front>3 AND left>3 AND right<=3 -> Twist (0.0, -0.2) -> publish L120 -> sleep 0.2 s L121');
  await host.sleep(1600);

  show('cv-d4'); show('cv-d4t');
  show('cv-never2'); show('cv-never2h');
  q('cv-nev1').textContent = 'শাখা ৪-এর ভেতরের চেক (L122): চায় বাঁপাশ খালি';
  q('cv-nev2').textContent = 'কিন্তু ঢোকার শর্তই ছিল: বাঁপাশ ভরা — অসম্ভব';
  q('cv-nev3').textContent = 'একই যুক্তি — L122-126-ও dead code';
  show('cv-nev1'); show('cv-nev2'); show('cv-nev3');
  host.caption('শাখা ৪-এর ভেতরের চেক (L122-126) একই কারণে dead: ঢোকার শর্ত <code>Left_warning &gt; conut</code> (L116), আর ভেতরে চাই <code>Left_warning &lt;= conut</code> — কখনোই মেলে না। বাঁয়ে ঘুরিয়ে দেওয়ার <code>+angular</code> (L124) আর <code>sleep(0.5)</code> (L126) অবজ্ঞাতই থাকে।');
  host.formula('L116 gate: Left_warning > conut ; L122 gate: Left_warning <= conut -> contradiction -> dead (mirror of L109)');
  await host.sleep(1700);

  hide('cv-never2'); hide('cv-never2h');
  hide('cv-nev1'); hide('cv-nev2'); hide('cv-nev3');
  cvRow('cv-r4', '#30363d');
  cvRow('cv-r6', '#7ee787');
  cvZone('cv-zf', 'cv-cf', 18, false);
  cvZone('cv-zl', 'cv-cl', 2, true);
  cvZone('cv-zr', 'cv-cr', 1, true);
  hide('cv-aw'); hide('cv-awh'); hide('cv-tcw'); hide('cv-tcwh');
  q('cv-acw').setAttribute('stroke', '#7ee787');
  q('cv-acwh').setAttribute('fill', '#7ee787');
  q('cv-tccw').setAttribute('stroke', '#7ee787');
  q('cv-tccwh').setAttribute('fill', '#7ee787');
  show('cv-acw'); show('cv-acwh'); show('cv-tccw'); show('cv-tccwh');
  q('cv-angv').textContent = 'angular.z = +0.2';
  q('cv-angp').setAttribute('stroke', '#7ee787');
  q('cv-linp').setAttribute('stroke', '#7ee787');
  show('cv-strict'); show('cv-nb6'); show('cv-nb6t');
  host.caption('<b>শাখা ৬ (L128-134):</b> শুধু সামনে বাধা — <code>print</code>: <i>6, there is an obstacle in the middle, turn left</i> (L130)। জায়গায় pivot: <code>linear.x = 0.0</code> (L131), <code>angular.z = self.angular</code> = <b>+0.2</b> (L132), <code>sleep(0.2)</code> (L134)। সূক্ষ্ম তফাত: এই শর্তে বাঁয়ে-ডানে <code>&lt;</code> (কঠোর, L129) — শাখা ২/৪-এর <code>&lt;=</code> নয়, আর ভেতরের চেকও নেই।');
  host.formula('branch 6 @ L129: front>3 AND left<3 AND right<3 -> Twist (0.0, +0.2) -> publish L133 -> sleep 0.2 s L134');
  await host.sleep(1600);

  show('cv-frz'); show('cv-frzt'); show('cv-q1'); show('cv-q1t');
  show('cv-q2'); show('cv-q2t'); show('cv-res'); show('cv-rest');
  show('cv-ns'); show('cv-nst'); show('cv-tnote');
  host.caption('<b>executor-এর খরচ:</b> <code>registerScan</code> callback-এর ভেতরের <code>sleep(0.2)</code> পুরো single-threaded লুপ আটকে রাখে — <code>rclpy.spin</code> (L181) একটাই thread চালায়, তাই এই pause-এ নতুন <code>/scan</code>-এর callback চলে না, <code>/JoyState</code>-ও না (timeline-টা illustrative)। ঘুম শেষ হলে তবেই পরের scan ঢোকে।');
  host.formula('single-thread spin: /scan -> registerScan -> publish -> sleep(0.2) [BLOCKED] -> /JoyState queued -> next /scan late');
  await host.sleep(1700);

  host.caption('তিন শাখার হিসাব এক খাতায়: সবকটিতে <code>linear.x = 0.0</code> — এগোনোর আদেশ নেই, শুধু ঘোরা। দিক ঠিক করে <code>angular.z</code>-এর চিহ্ন: বাঁ = <code>+self.angular</code>, ডান = <code>-self.angular</code>; মান দুটো parameter থেকে (L32/L34: 0.2, 0.2), আর সীমা <code>conut = 3</code> (L47)।');
  host.formula('Twist: branch 2 = (0.0, +0.2) ; branch 4 = (0.0, -0.2) ; branch 6 = (0.0, +0.2) ; linear stays 0 in all three');
  await host.sleep(1500);
};

/* ---------- safetyHalt ---------- */
/* ============ folder-11 anim: safetyHalt (part 15) ==================
   laser_Avoidance.py L176-187 (main + try/except/finally), with L168-173
   exit_pro and L14 print as grounding. Source sha 04cb3a590eec.
   Facts: L177 rclpy.init(); L178 laserAvoid("laser_Avoidance_a1");
   L179 print ("start it"); L181 rclpy.spin(laser_avoid); L182-183
   except KeyboardInterrupt: pass; L184 finally: L185 exit_pro(),
   L186 destroy_node(), L187 rclpy.shutdown(). L14 print("improt done")
   fires at import time - two prints, two different times. exit_pro:
   cmd1 (L170) + cmd2 (L171 zero-yaml) joined L172, os.system(cmd)
   L173 = a shell outside the node = process-level brake. README L5
   (sha a14cc05fee6f): ros2 run yahboom_M3Pro_laser laser_Avoidance.
   Id prefix sh-; no emoji, no Unicode arrows in stage strings; static
   backbone visible at setStage; first caption + formula before the
   first await. */

function shCodeLine(n, ind, s, id) {
  const y = 84 + (n - 176) * 20;
  return txt(66, y, String(n), { anchor: 'end', size: 7.5, mono: true, fill: '#6e7681' }) +
         txt(74 + ind * 13, y, s, { size: 8.5, mono: true, fill: '#8b949e', id: id });
}

ANIMS.safetyHalt = async function (host) {
  const svg = host.setStage(
    txt(450, 26, 'main(): জন্ম, ঘূর্ণন, নীরব থামা আর finally-র নিরাপদ ব্রেক', { anchor: 'middle', size: 14, weight: 600, fill: '#ffb454' }) +
    rrect(40, 44, 372, 316, 8, '#0d1117', '#2a3442') +
    txt(56, 64, 'CODE — laser_Avoidance.py L176-187', { size: 10, weight: 700, fill: '#e6edf3' }) +
    rrect(50, 73, 352, 76, 4, '#7ee787', 'none', ' id="sh-h1" fill-opacity="0.10" opacity="0"') +
    rrect(50, 153, 352, 36, 4, '#4fc3f7', 'none', ' id="sh-h2" fill-opacity="0.10" opacity="0"') +
    rrect(50, 193, 352, 36, 4, '#ff7b72', 'none', ' id="sh-h3" fill-opacity="0.12" opacity="0"') +
    rrect(50, 233, 352, 36, 4, '#e3b341', 'none', ' id="sh-h4" fill-opacity="0.12" opacity="0"') +
    rrect(50, 273, 352, 36, 4, '#7ee787', 'none', ' id="sh-h5" fill-opacity="0.10" opacity="0"') +
    shCodeLine(176, 0, 'def main():', 'sh-c176') +
    shCodeLine(177, 1, 'rclpy.init()', 'sh-c177') +
    shCodeLine(178, 1, 'laser_avoid = laserAvoid("laser_Avoidance_a1")', 'sh-c178') +
    shCodeLine(179, 1, 'print ("start it")', 'sh-c179') +
    shCodeLine(180, 1, 'try:', 'sh-c180') +
    shCodeLine(181, 2, 'rclpy.spin(laser_avoid)', 'sh-c181') +
    shCodeLine(182, 1, 'except KeyboardInterrupt:', 'sh-c182') +
    shCodeLine(183, 2, 'pass', 'sh-c183') +
    shCodeLine(184, 1, 'finally:', 'sh-c184') +
    shCodeLine(185, 2, 'laser_avoid.exit_pro()', 'sh-c185') +
    shCodeLine(186, 2, 'laser_avoid.destroy_node()', 'sh-c186') +
    shCodeLine(187, 1, 'rclpy.shutdown()', 'sh-c187') +
    txt(56, 326, 'L185-এর exit_pro() = L168-173 — ডানের SHELL কার্ড', { size: 7.5, fill: '#6e7681' }) +
    txt(56, 342, 'README L5: ros2 run yahboom_M3Pro_laser laser_Avoidance', { size: 7.5, mono: true, fill: '#6e7681' }) +
    rrect(428, 44, 432, 316, 8, '#111', '#30363d') +
    txt(644, 64, 'RUNTIME — জীবনচক্র (illustrative)', { anchor: 'middle', size: 10, weight: 700, fill: '#e6edf3' }) +
    txt(702, 84, 'TERMINAL', { size: 8, weight: 700, fill: '#6e7681' }) +
    rrect(702, 90, 142, 58, 5, '#0d1117', '#30363d') +
    txt(712, 108, 'improt done', { size: 8, mono: true, fill: '#8b949e', id: 'sh-pol1', op: 0 }) +
    txt(712, 128, 'start it', { size: 8.5, mono: true, weight: 700, fill: '#7ee787', id: 'sh-pol2', op: 0 }) +
    txt(702, 160, 'দুই print, দুই সময়', { size: 7.5, fill: '#6e7681', id: 'sh-pon1', op: 0 }) +
    txt(702, 172, '(L14) আর (L179)', { size: 7.5, fill: '#6e7681', id: 'sh-pon2', op: 0 }) +
    txt(444, 84, 'rclpy.init() (L177) — library চালু', { size: 8.5, mono: true, fill: '#7ee787', id: 'sh-r1', op: 0 }) +
    rrect(444, 92, 250, 62, 6, '#161b22', '#7ee787', ' id="sh-node" opacity="0"') +
    txt(456, 110, 'laserAvoid — node জন্ম', { size: 9.5, weight: 700, fill: '#e6edf3', id: 'sh-nt1', op: 0 }) +
    txt(456, 124, 'name: "laser_Avoidance_a1" (L178)', { size: 8, mono: true, fill: '#d2a8ff', id: 'sh-nt2', op: 0 }) +
    txt(456, 138, 'sub /scan, /JoyState + pub /cmd_vel', { size: 7.5, mono: true, fill: '#8b949e', id: 'sh-nt3', op: 0 }) +
    txt(444, 174, 'rclpy.spin(laser_avoid) (L181) — event loop', { size: 8.5, mono: true, fill: '#4fc3f7', id: 'sh-r2', op: 0 }) +
    rrect(444, 182, 250, 30, 5, '#161b22', '#30363d', ' id="sh-loop" opacity="0"') +
    circ(468, 197, 5, '#0d1117', ' id="sh-s1" stroke="#4fc3f7" stroke-width="1" opacity="0"') +
    circ(508, 197, 5, '#0d1117', ' id="sh-s2" stroke="#4fc3f7" stroke-width="1" opacity="0"') +
    circ(549, 197, 5, '#0d1117', ' id="sh-s3" stroke="#4fc3f7" stroke-width="1" opacity="0"') +
    circ(589, 197, 5, '#0d1117', ' id="sh-s4" stroke="#4fc3f7" stroke-width="1" opacity="0"') +
    circ(630, 197, 5, '#0d1117', ' id="sh-s5" stroke="#4fc3f7" stroke-width="1" opacity="0"') +
    circ(670, 197, 5, '#0d1117', ' id="sh-s6" stroke="#4fc3f7" stroke-width="1" opacity="0"') +
    circ(468, 197, 8, 'none', ' id="sh-cur" stroke="#4fc3f7" stroke-width="2" opacity="0"') +
    txt(702, 190, 'tick 1: /scan', { size: 8, mono: true, fill: '#4fc3f7', id: 'sh-ls', op: 0 }) +
    txt(702, 204, 'এলে registerScan (L53)', { size: 7.5, fill: '#8b949e', id: 'sh-ls2', op: 0 }) +
    rrect(444, 218, 64, 22, 5, '#161b22', '#ff7b72', ' id="sh-ctrl" opacity="0"') +
    txt(476, 233, 'Ctrl+C', { anchor: 'middle', size: 8.5, weight: 700, fill: '#ff7b72', id: 'sh-ctrlt', op: 0 }) +
    txt(516, 233, 'KeyboardInterrupt (L182) — except: pass (L183)', { size: 7.5, fill: '#8b949e', id: 'sh-ctrnote', op: 0 }) +
    rrect(444, 248, 400, 52, 6, '#0d1117', '#e3b341', ' id="sh-shell" opacity="0"') +
    txt(454, 262, 'SHELL — os.system(cmd) (L173)', { size: 8, weight: 700, fill: '#e3b341', id: 'sh-sht', op: 0 }) +
    txt(454, 278, '$ ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist', { size: 8, mono: true, fill: '#7ee787', id: 'sh-sc1', op: 0 }) +
    txt(454, 292, '"{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"', { size: 7.5, mono: true, fill: '#7ee787', id: 'sh-sc2', op: 0 }) +
    txt(444, 312, 'shell = node-এর বাইরের process — teardown চলাকালেও ব্রেক কাজ করে', { size: 8, fill: '#e3b341', id: 'sh-shn', op: 0 }) +
    txt(444, 324, 'ফল: চাকায় zero Twist (L171) — শেষ velocity মুছে গেল', { size: 8, fill: '#7ee787', id: 'sh-wz', op: 0 }) +
    txt(444, 338, 'destroy_node() (L186): নাম আর subscription ছাড়া', { size: 8, fill: '#8b949e', id: 'sh-r5a', op: 0 }) +
    txt(444, 350, 'rclpy.shutdown() (L187): library বন্ধ — নিরাপদ প্রস্থান', { size: 8, weight: 700, fill: '#7ee787', id: 'sh-r5b', op: 0 }) +
    txt(450, 386, 'রঙ-নিয়ম: সবুজ = জন্ম ও প্রস্থান, নীল = spin loop, লাল = Ctrl+C, হলুদ = shell ব্রেক, বেগুনি = নাম', { anchor: 'middle', size: 8.5, fill: '#8b949e' }) +
    txt(450, 440, 'source: laser_Avoidance.py L176-187 + L168-173 + L14 - README L5', { anchor: 'middle', size: 8, mono: true, fill: '#6e7681' })
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

  host.caption('এই anim-এ <code>main()</code>-এর পুরো জীবনকাল — L176 থেকে L187। বাঁয়ে কোড, ডানে তার runtime ছবি। শুরুতেই একটা কথা: file-টা <b>import</b>-হওয়ার মুহূর্তেই একটা print বেরিয়ে গেছে (L14), আর README L5-এর <code>ros2 run yahboom_M3Pro_laser laser_Avoidance</code> ডাক দেয় এই <code>main()</code>-কে।');
  host.formula('life = import (L14) -> main (L176) -> rclpy.init (L177) -> spin (L181) -> finally (L184-187)');
  await host.sleep(1500);

  show('sh-pol1'); show('sh-pon1'); show('sh-pon2');
  host.caption('টার্মিনালের প্রথম লাইনটা তাই আগেই এসে গেছে: <code>improt done</code> (L14) — বানানটা source-এ এমনই, <b>import</b> শব্দের typo। মানে দুটি print দুই <b>আলাদা সময়ে</b>: L14 import-এর সময়, L179 পরে main()-এর ভেতরে।');
  await host.sleep(1500);

  show('sh-h1'); shGlow(['sh-c176', 'sh-c177', 'sh-c178', 'sh-c179'], '#e6edf3');
  show('sh-r1'); show('sh-node'); show('sh-nt1'); show('sh-nt2'); show('sh-nt3'); show('sh-pol2');
  host.caption('<code>main()</code> শুরু (L176)। <code>rclpy.init()</code> (L177) — rclpy library চালু। তারপর <code>laserAvoid("laser_Avoidance_a1")</code> (L178): constructor সাবস্ক্রিপশন আর publisher সব সেট করে node জন্মায় (আগের part-এর গল্প)। সঙ্গে দ্বিতীয় print: <b>start it</b> (L179)।');
  await host.sleep(1700);

  show('sh-h2'); shGlow(['sh-c180', 'sh-c181'], '#4fc3f7');
  show('sh-r2'); show('sh-loop'); shSlotIds.forEach(show); show('sh-cur'); show('sh-ls'); show('sh-ls2'); shTick(1);
  host.caption('<code>rclpy.spin(laser_avoid)</code> (L181) — এই হলো event loop। <code>/scan</code> এলে <code>registerScan</code> (L53) ছোটে, <code>/JoyState</code> এলে <code>JoyStateCallback</code> (L49)। নীল রিং ঘুরছে = callback একের পর এক (illustrative)।');
  host.formula('spin = wait + dispatch: /scan -> registerScan (L53), /JoyState -> JoyStateCallback (L49)');
  await host.sleep(700);
  shTick(2); await host.sleep(420);
  shTick(3); await host.sleep(420);
  shTick(4); await host.sleep(420);
  shTick(5); await host.sleep(420);
  shTick(6); await host.sleep(420);
  shTick(7); await host.sleep(500);
  host.caption('প্রতি tick-এই সিদ্ধান্তের গাছ চলে — এগোবে, ঘুরবে না পিছাবে (আগের part-গুলোর গল্প)। <code>spin</code> নিজে থেমে না; Ctrl+C ছাড়া এই ঘূর্ণন চলতেই থাকত।');
  await host.sleep(1500);

  show('sh-h3'); shGlow(['sh-c182', 'sh-c183'], '#ff7b72');
  show('sh-ctrl'); show('sh-ctrlt'); show('sh-ctrnote');
  hide('sh-cur');
  shSlotIds.forEach(sid => { q(sid).setAttribute('fill', '#0d1117'); q(sid).setAttribute('stroke', '#6e7681'); });
  q('sh-loop').setAttribute('stroke', '#30363d');
  q('sh-ls').textContent = 'loop থেমে গেল';
  host.caption('Ctrl+C চাপলে <code>KeyboardInterrupt</code> ওঠে (L182) — except block শুধু <code>pass</code> (L183), একটা শব্দও না। কিন্তু Python-এর কঠিন নিয়ম: <b>finally সব পথেই চলে</b> — exception হোক বা না হোক।');
  host.formula('Ctrl+C -> KeyboardInterrupt -> except: pass (L183) -> finally STILL runs (L184)');
  await host.sleep(1600);

  show('sh-h4'); shGlow(['sh-c184', 'sh-c185'], '#e3b341');
  show('sh-shell'); show('sh-sht'); show('sh-sc1'); show('sh-sc2');
  host.caption('<code>finally</code> (L184)-এর প্রথম কাজ <code>exit_pro()</code> (L185)। ভেতরে (L168-173): <code>cmd1</code> (L170) + <code>cmd2</code> (L171) জোড়া লেগে (L172) একটাই লাইন — <code>ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist</code>, সঙ্গে সব-শূন্য yaml string।');
  host.formula('cmd = cmd1 (L170) + cmd2 (L171); os.system(cmd) (L173) = zero Twist via shell');
  await host.sleep(1800);

  show('sh-shn'); show('sh-wz');
  host.caption('<code>os.system(cmd)</code> (L173) লাইনটা একটা <b>shell</b>-এ চালায় — node-এর rclpy জগতের বাইরে, আলাদা <b>process</b>-এর ব্রেক। তাই <code>destroy_node()</code> ভাঙতে শুরু করলেও চাকা শূন্য <code>Twist</code> পেয়ে থেমে যায়।');
  await host.sleep(1700);

  show('sh-h5'); shGlow(['sh-c186', 'sh-c187'], '#7ee787');
  show('sh-r5a'); show('sh-r5b');
  q('sh-node').setAttribute('stroke', '#30363d');
  shGlow(['sh-nt1', 'sh-nt2', 'sh-nt3'], '#6e7681');
  q('sh-ls').textContent = 'spin শেষ';
  host.caption('শেষ ধাপ: <code>destroy_node()</code> (L186) node-এর নাম আর সাবস্ক্রিপশন ছেড়ে দেয়, <code>rclpy.shutdown()</code> (L187) library বন্ধ করে। চাকা আগেই শূন্য — তাই প্রস্থানটা নিরাপদ।');
  host.formula('safe exit = zero wheels (L185) + free names (L186) + close library (L187)');
  await host.sleep(1700);

  host.caption('পুরো সারি: জন্ম L177-178, ঘূর্ণন L181, নীরব থামা L182-183, shell ব্রেক L184-185 + L168-173, বিদায় L186-187। সাধারণ নিয়মে velocity-আদেশ নিজে নিজে ফিরে আসে না — তাই <code>finally</code> না থাকলে Ctrl+C-র পরেও চাকা শেষ আদেশের বেগে চলতেই থাকত। এই নকশাটাই safety shutdown।');
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

