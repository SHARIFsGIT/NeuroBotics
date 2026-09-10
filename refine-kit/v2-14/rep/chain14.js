/* ============ folder-14 anim — chain14 (part 2, v1 layer) ============
   gmapping.launch.py L1-L49. L2 `from launch_ros.actions import Node` AND
   L9 duplicate `from launch import LaunchDescription` region: actually
   L2 = Node import #1, L9 = DUPLICATE Node import #2 (source quirk);
   L3-L4 LaunchConfiguration + DeclareLaunchArgument imported but UNUSED
   (no lazy args in this file). L17-L19 three dead lists (defined, never
   referenced). FOUR eager os.path.join(get_package_share_directory(...))
   calls at ctor time: L24-28 ira_laser_tools merge_multi.launch.py,
   L31-35 yahboom_laser_filter laser_filter_node.launch.py, L38-42
   robot_localization ekf.launch.py, L45-49 slam_gmapping
   gmapping.launch.py. Eager = path strings resolved WHEN THE LAUNCH FILE
   IS READ, not when nodes start (contrast: LaunchConfiguration would be
   lazy — imported at L3 but never used). Share paths illustrative.
   Unique id prefix ch14- ; no emoji ; no arrow chars in stage text ;
   first caption + formula before the first await ; static backbone. */


/* ---------- chain14 ---------- */
ANIMS.chain14 = async function (host) {
  const svg = host.setStage(
    txt(450, 26, 'constructor phase-এই চারটা path স্ট্রিং হয়ে যায় — eager, lazy নয়', { anchor: 'middle', size: 14.5, weight: 600, fill: '#ffb454' }) +
    rrect(30, 44, 400, 322, 8, '#0d1117', '#2a3442') +
    txt(46, 64, 'gmapping.launch.py L1-L49 — imports + dead lists + 4 joins', { size: 10, weight: 700, fill: '#e6edf3' }) +
    rrect(46, 72, 368, 26, 4, '#161b22', '#30363d', ' id="ch14-i1"') +
    txt(54, 85, 'L2  from launch_ros.actions import Node', { size: 8, mono: true, weight: 700, fill: '#7ee787' }) +
    txt(54, 95, 'L9  from launch_ros.actions import Node  # আবার!', { size: 8, mono: true, fill: '#7ee787', id: 'ch14-i2', op: 0 }) +
    rrect(46, 102, 368, 24, 4, '#161b22', '#30363d', ' id="ch14-i3"') +
    txt(54, 117, 'L3-4  LaunchConfiguration, Declare...', { size: 8, mono: true, fill: '#8b949e' }) +
    txt(356, 117, 'unused', { anchor: 'end', size: 7.2, mono: true, fill: '#ff7b72', id: 'ch14-i3t', op: 0 }) +
    rrect(46, 130, 368, 30, 4, '#161b22', '#30363d', ' id="ch14-dl"') +
    txt(54, 144, 'L17-19  laser_merge_nodes = [...]  ইত্যাদি', { size: 8, mono: true, fill: '#8b949e' }) +
    txt(54, 155, 'তিনটা list — একটাও আর পাত্তা পায় না', { size: 7.4, fill: '#8b949e', id: 'ch14-dlt', op: 0 }) +
    txt(356, 144, 'dead', { anchor: 'end', size: 7.2, mono: true, fill: '#ff7b72', id: 'ch14-dlb', op: 0 }) +
    rrect(46, 166, 368, 30, 4, '#161b22', '#30363d', ' id="ch14-j1"') +
    txt(54, 180, 'L24-28  os.path.join(gpshd(ira_laser_tools),', { size: 8, mono: true, weight: 700, fill: '#ffb454' }) +
    txt(62, 191, "launch, 'merge_multi.launch.py')", { size: 7.6, mono: true, weight: 700, fill: '#ffb454' }) +
    rrect(46, 200, 368, 30, 4, '#161b22', '#30363d', ' id="ch14-j2"') +
    txt(54, 214, 'L31-35  os.path.join(gpshd(yahboom_laser_filter),', { size: 8, mono: true, weight: 700, fill: '#d2a8ff' }) +
    txt(62, 225, "launch, 'laser_filter_node.launch.py')", { size: 7.6, mono: true, weight: 700, fill: '#d2a8ff' }) +
    rrect(46, 234, 368, 30, 4, '#161b22', '#30363d', ' id="ch14-j3"') +
    txt(54, 248, 'L38-42  os.path.join(gpshd(robot_localization),', { size: 8, mono: true, weight: 700, fill: '#4fc3f7' }) +
    txt(62, 259, "launch, 'ekf.launch.py')", { size: 7.6, mono: true, weight: 700, fill: '#4fc3f7' }) +
    rrect(46, 268, 368, 30, 4, '#161b22', '#30363d', ' id="ch14-j4"') +
    txt(54, 282, 'L45-49  os.path.join(gpshd(slam_gmapping),', { size: 8, mono: true, weight: 700, fill: '#7ee787' }) +
    txt(62, 293, "launch, 'gmapping.launch.py')", { size: 7.6, mono: true, weight: 700, fill: '#7ee787' }) +
    txt(46, 318, 'def generate_launch_description():  (L13)', { size: 8, mono: true, fill: '#c9d1d9' }) +
    txt(46, 332, 'এই শরীরটাই constructor phase — প্রতিটা join এখানেই চলে', { size: 7.6, fill: '#8b949e', id: 'ch14-ctor', op: 0 }) +
    rrect(446, 44, 424, 322, 8, '#111', '#30363d') +
    txt(658, 64, 'SYSTEM — path-গুলো যেভাবে বাঁধা পড়ে', { anchor: 'middle', size: 10, weight: 700, fill: '#e6edf3' }) +
    txt(462, 84, 'get_package_share_directory(pkg) + launch + file', { size: 7.6, mono: true, weight: 700, fill: '#e6edf3' }) +
    txt(462, 97, '= একটা লম্বা install-path string (illustrative)', { size: 7.2, fill: '#8b949e' }) +
    rrect(462, 106, 392, 34, 4, '#161b22', '#ffb454', ' id="ch14-p1" opacity="0"') +
    txt(470, 120, '.../ira_laser_tools/share/.../launch/merge_multi.launch.py', { size: 7.4, mono: true, weight: 700, fill: '#ffb454', id: 'ch14-p1t', op: 0 }) +
    txt(470, 132, 'dual-laser merger — folder 10-এর চেনা ফাইল', { size: 7, fill: '#ffb454', id: 'ch14-p1s', op: 0 }) +
    rrect(462, 146, 392, 34, 4, '#161b22', '#d2a8ff', ' id="ch14-p2" opacity="0"') +
    txt(470, 160, '.../yahboom_laser_filter/.../laser_filter_node.launch.py', { size: 7.4, mono: true, weight: 700, fill: '#d2a8ff', id: 'ch14-p2t', op: 0 }) +
    txt(470, 172, 'noise ঝেড়ে দেওয়া filter', { size: 7, fill: '#d2a8ff', id: 'ch14-p2s', op: 0 }) +
    rrect(462, 186, 392, 34, 4, '#161b22', '#4fc3f7', ' id="ch14-p3" opacity="0"') +
    txt(470, 200, '.../robot_localization/.../launch/ekf.launch.py', { size: 7.4, mono: true, weight: 700, fill: '#4fc3f7', id: 'ch14-p3t', op: 0 }) +
    txt(470, 212, 'imu + odom মিশিয়ে EKF — বিশ্বাসযোগ্য odom', { size: 7, fill: '#4fc3f7', id: 'ch14-p3s', op: 0 }) +
    rrect(462, 226, 392, 34, 4, '#161b22', '#7ee787', ' id="ch14-p4" opacity="0"') +
    txt(470, 240, '.../slam_gmapping/.../launch/gmapping.launch.py', { size: 7.4, mono: true, weight: 700, fill: '#7ee787', id: 'ch14-p4t', op: 0 }) +
    txt(470, 252, 'নিজেই SLAM — /scan + odom থেকে /map বানায়', { size: 7, fill: '#7ee787', id: 'ch14-p4s', op: 0 }) +
    rrect(462, 268, 392, 40, 4, '#0d1117', '#30363d', ' id="ch14-eager" opacity="0"') +
    txt(470, 283, 'eager মানে: file-টা পড়ার মুহূর্তেই string তৈরি', { size: 7.6, weight: 700, fill: '#e3b341', id: 'ch14-eagerA', op: 0 }) +
    txt(470, 295, 'launch হোক বা না হোক — join চলেই গেছে', { size: 7.4, fill: '#e3b341', id: 'ch14-eagerB', op: 0 }) +
    txt(470, 304, 'lazy হতে হলে লাগত LaunchConfiguration — import করেই রেখে দিয়েছে (L3)', { size: 7, fill: '#8b949e', id: 'ch14-eagerC', op: 0 }) +
    txt(658, 326, 'এখনো একটা program-ও চালু হয়নি — এরা শুধু ঠিকানা', { anchor: 'middle', size: 8, weight: 700, fill: '#ff7b72', id: 'ch14-notyet', op: 0 }) +
    txt(450, 386, 'রঙ-নিয়ম: সবুজ/হলুদ/বেগুনি/নীল = চার join-এর জিনিস, লাল = dead/unused, গোল্ড = eager-তত্ত্ব', { anchor: 'middle', size: 8.5, fill: '#8b949e' }) +
    txt(450, 440, 'source: gmapping.launch.py L1-L49 (dup Node import L2+L9, unused L3-4, dead lists L17-19, joins L24-28/31-35/38-42/45-49)', { anchor: 'middle', size: 7.8, mono: true, fill: '#6e7681' })
  );
  const q = id => svg.querySelector('#' + id);
  const show = id => q(id).setAttribute('opacity', 1);
  const edge = id => q(id).setAttribute('stroke', '#e3b341');
  host.caption('launch file-টা পড়ার সঙ্গে সঙ্গে <code>generate_launch_description()</code>-এর শরীর একবার চলে — এই <b>constructor phase</b>-এই আজকের সব কাজ ঘটে। imports, তিনটা dead list, তারপর চারটা <code>os.path.join</code>।');
  host.formula('ctor phase = generate_launch_description() body runs ONCE when file is read');
  await host.sleep(1500);
  edge('ch14-i1'); show('ch14-i2');
  host.caption('L2-এ <code>Node</code> import — আর L9-তে <b>আবার</b> একই import। দ্বিতীয়টা নিরীহ (Python দ্বিতীয়বার একই জিনিস বাঁধে, ক্ষতি নেই), কিন্তু এটা source-এর আসল বৈশিষ্ট্য — ঠিক না করে দেখিয়েই দিচ্ছি।');
  await host.sleep(1600);
  edge('ch14-i3'); show('ch14-i3t');
  host.caption('L3-L4-এ <code>LaunchConfiguration</code> আর <code>DeclareLaunchArgument</code> এসেছে — কিন্তু পুরো file-এ আর কোথাও ডাকা হয়নি। এই file-এ কোনো argument-ই lazy নয়; সব ঠিকানা সরাসরি বাঁধা।');
  await host.sleep(1600);
  edge('ch14-dl'); show('ch14-dlt'); show('ch14-dlb');
  host.caption('L17-19: তিনটা list সাজানো হয়েছে — নাম দিয়ে, মন্তব্য দিয়ে — অথচ পরের কোনো line-ই এদের দেখে না। লেখক বোধহয় পরে পরিকল্পনা বদলান; list-গুলো হয়ে রইল <b>মৃত</b>। বাগ নয়, কিন্তু পাঠকের সময় নষ্ট করে।');
  await host.sleep(1700);
  edge('ch14-j1'); show('ch14-p1'); show('ch14-p1t'); show('ch14-p1s');
  host.caption('প্রথম join (L24-28): <code>ira_laser_tools</code> package-এর <code>merge_multi.launch.py</code> — front আর rear দুই lidar-এর raw মিশিয়ে এক <code>/scan</code> বানায়। folder 10-এ যার পুরো গল্প দেখেছি — path-টা এখন একটা সাধারণ string।');
  await host.sleep(1600);
  edge('ch14-j2'); show('ch14-p2'); show('ch14-p2t'); show('ch14-p2s');
  host.caption('দ্বিতীয় join (L31-35): <code>yahboom_laser_filter</code> package-এর <code>laser_filter_node.launch.py</code> — merger-এর মিশ্রিনি scan-এর কোলাহল ঝেড়ে ফেলে। chain-এর দ্বিতীয় ধাপ।');
  await host.sleep(1600);
  edge('ch14-j3'); show('ch14-p3'); show('ch14-p3t'); show('ch14-p3s');
  host.caption('তৃতীয় join (L38-42): <code>robot_localization</code> package-এর <code>ekf.launch.py</code> — imu-র ঝোঁক আর wheel-এর odom একসাথে গুলে একটা স্থির, বিশ্বাসযোগ্য odom বানায় (গুলনির ভেতরের হিসাব vendor-এর, <b>illustrative</b>)।');
  host.formula('chain: 2 lidar raw -> merge -> filter -> /scan ; imu + wheel odom -> ekf -> fused odom');
  await host.sleep(1700);
  edge('ch14-j4'); show('ch14-p4'); show('ch14-p4t'); show('ch14-p4s'); show('ch14-ctor');
  host.caption('চতুর্থ join (L45-49): <code>slam_gmapping</code> package-এর নিজের <code>gmapping.launch.py</code> — আসল SLAM ইঞ্জিন। লক্ষ করো: আমরা যে file পড়ছি, সে-ই আবার অন্য package-এর একই নামের file-এর দিকে ইশারা করছে। চারটা ঠিকানাই এখন বাঁধা — কিন্তু কেউ চালু হয়নি।');
  await host.sleep(1600);
  show('ch14-eager'); show('ch14-eagerA'); show('ch14-eagerB'); show('ch14-eagerC'); show('ch14-notyet');
  host.caption('<b>eager</b> versus <b>lazy</b>: join-গুলো file পড়ার মুহূর্তেই চলে গেছে — launch পরে হোক বা না হোক। lazy করতে হলে লাগত <code>LaunchConfiguration</code>; সেটার import (L3) বাক্সবন্দি পড়ে আছে। ঠিকানা তৈরি আর প্রোগ্রাম চালু — দুই আলাদা পর্ব; চালুর পালা পরের part-এ, পাঁচ entry-র তালিকায়।');
  host.formula('eager join at ctor != node start at run ; 4 paths bound, 0 programs running');
  await host.sleep(1700);
  host.caption('এক নজরে: duplicate import, দুই unused import, তিন dead list, চার eager path — constructor phase-এর পুরো সিনেমা। এবার তালিকার দিকে — imu remap আর পাঁচ program-এর উদ্বোধন।');
  await host.sleep(1500);
};
