/* ============ folder-14 anim — runbook14 (part 1, v1 layer) ============
   README.md L1-L15 (15 lines, 8 commands at ODD lines L1/3/5/7/9/11/13/15,
   7 blank even lines as pauses). Three packages across the runbook:
   slam_mapping (L3 gmapping.launch.py, L5 slam_view.launch.py, L15
   save_map.launch.py), yahboomcar_ctrl (L7 yahboom_keyboard), M3Pro_demo
   (L9 camera_arm_kin.launch.py, L11 follow_line). L13 is a one-shot
   `ros2 topic pub /arm6_joints ... --once` with a brace payload (source
   as-is). Story = a SLAM session's life cycle: bringup (L1, vendor,
   illustrative) -> map (L3) -> watch (L5) -> drive (L7) -> perceive (L9)
   -> follow (L11) -> arm test (L13) -> save (L15). gmapping.launch.py
   itself launches FIVE programs (merger, filter, imu, ekf, gmapping) —
   covered by chain14/ekf14; here only the README view.
   Unique id prefix rb14- ; no emoji ; no arrow chars in stage text (ASCII
   -> or words) ; first caption + formula before the first await ; static
   backbone at setStage. */


/* ---------- runbook14 ---------- */
ANIMS.runbook14 = async function (host) {
  const svg = host.setStage(
    txt(450, 26, 'README-র ৮টা command = একটা SLAM session-এর পুরো জীবনচক্র', { anchor: 'middle', size: 14.5, weight: 600, fill: '#ffb454' }) +
    rrect(30, 44, 350, 322, 8, '#0d1117', '#2a3442') +
    txt(46, 64, 'TERMINAL — README L1-L15 (8 command + 7 blank)', { size: 10, weight: 700, fill: '#e6edf3' }) +
    rrect(46, 72, 318, 22, 4, '#161b22', '#30363d', ' id="rb14-c1"') +
    txt(54, 86, '$ sh start_agent.sh', { size: 8.8, mono: true, weight: 700, fill: '#7ee787' }) +
    txt(356, 86, 'L1', { anchor: 'end', size: 7.5, mono: true, fill: '#6e7681' }) +
    rrect(46, 97, 318, 22, 4, '#161b22', '#30363d', ' id="rb14-c2"') +
    txt(54, 111, '$ ros2 launch slam_mapping', { size: 8.8, mono: true, weight: 700, fill: '#ffb454' }) +
    txt(62, 122, '  gmapping.launch.py', { size: 8, mono: true, weight: 700, fill: '#ffb454' }) +
    txt(356, 111, 'L3', { anchor: 'end', size: 7.5, mono: true, fill: '#6e7681' }) +
    rrect(46, 133, 318, 22, 4, '#161b22', '#30363d', ' id="rb14-c3"') +
    txt(54, 147, '$ ros2 launch slam_mapping', { size: 8.8, mono: true, weight: 700, fill: '#4fc3f7' }) +
    txt(62, 158, '  slam_view.launch.py', { size: 8, mono: true, weight: 700, fill: '#4fc3f7' }) +
    txt(356, 147, 'L5', { anchor: 'end', size: 7.5, mono: true, fill: '#6e7681' }) +
    rrect(46, 169, 318, 22, 4, '#161b22', '#30363d', ' id="rb14-c4"') +
    txt(54, 183, '$ ros2 run yahboomcar_ctrl', { size: 8.8, mono: true, weight: 700, fill: '#d2a8ff' }) +
    txt(62, 194, '  yahboom_keyboard', { size: 8, mono: true, weight: 700, fill: '#d2a8ff' }) +
    txt(356, 183, 'L7', { anchor: 'end', size: 7.5, mono: true, fill: '#6e7681' }) +
    rrect(46, 205, 318, 22, 4, '#161b22', '#30363d', ' id="rb14-c5"') +
    txt(54, 219, '$ ros2 launch M3Pro_demo', { size: 8.8, mono: true, weight: 700, fill: '#e3b341' }) +
    txt(62, 230, '  camera_arm_kin.launch.py', { size: 8, mono: true, weight: 700, fill: '#e3b341' }) +
    txt(356, 219, 'L9', { anchor: 'end', size: 7.5, mono: true, fill: '#6e7681' }) +
    rrect(46, 241, 318, 22, 4, '#161b22', '#30363d', ' id="rb14-c6"') +
    txt(54, 255, '$ ros2 run M3Pro_demo', { size: 8.8, mono: true, weight: 700, fill: '#7ee787' }) +
    txt(62, 266, '  follow_line', { size: 8, mono: true, weight: 700, fill: '#7ee787' }) +
    txt(356, 255, 'L11', { anchor: 'end', size: 7.5, mono: true, fill: '#6e7681' }) +
    rrect(46, 277, 318, 30, 4, '#161b22', '#30363d', ' id="rb14-c7"') +
    txt(54, 290, '$ ros2 topic pub /arm6_joints', { size: 8.2, mono: true, weight: 700, fill: '#ff7b72' }) +
    txt(54, 302, '  arm_msgs/msg/ArmJoints {...} --once', { size: 7.5, mono: true, fill: '#ff7b72' }) +
    txt(356, 290, 'L13', { anchor: 'end', size: 7.5, mono: true, fill: '#6e7681' }) +
    rrect(46, 312, 318, 22, 4, '#161b22', '#30363d', ' id="rb14-c8"') +
    txt(54, 326, '$ ros2 launch slam_mapping', { size: 8.8, mono: true, weight: 700, fill: '#ffb454' }) +
    txt(62, 337, '  save_map.launch.py', { size: 8, mono: true, weight: 700, fill: '#ffb454' }) +
    txt(356, 326, 'L15', { anchor: 'end', size: 7.5, mono: true, fill: '#6e7681' }) +
    txt(46, 356, 'even line-গুলো (L2, L4, ... L14) ফাঁকা — ধাপের pause', { size: 7.5, fill: '#8b949e' }) +
    rrect(396, 44, 474, 322, 8, '#111', '#30363d') +
    txt(633, 64, 'SYSTEM — প্রতিটা command যা জন্ম দেয়', { anchor: 'middle', size: 10, weight: 700, fill: '#e6edf3' }) +
    rrect(412, 74, 222, 26, 4, '#161b22', '#7ee787', ' id="rb14-s1" opacity="0"') +
    txt(420, 90, 'vendor bringup — robot জাগল (illustrative)', { size: 7.5, mono: true, weight: 700, fill: '#7ee787', id: 'rb14-s1t', op: 0 }) +
    rrect(412, 106, 222, 40, 4, '#161b22', '#ffb454', ' id="rb14-s2" opacity="0"') +
    txt(420, 121, 'SLAM stack: ৫টা program একসাথে', { size: 7.5, mono: true, weight: 700, fill: '#ffb454', id: 'rb14-s2a', op: 0 }) +
    txt(420, 133, 'merger + filter + imu + ekf + gmapping', { size: 7.2, mono: true, fill: '#ffb454', id: 'rb14-s2b', op: 0 }) +
    txt(656, 121, '/map জন্মায়', { size: 7.5, mono: true, weight: 700, fill: '#ffb454', id: 'rb14-s2c', op: 0 }) +
    rrect(412, 152, 222, 34, 4, '#161b22', '#4fc3f7', ' id="rb14-s3" opacity="0"') +
    txt(420, 166, 'RViz — slam_rviz.rviz config নিয়ে', { size: 7.5, mono: true, weight: 700, fill: '#4fc3f7', id: 'rb14-s3a', op: 0 }) +
    txt(420, 178, 'মানচিত্র বাড়তে বাড়তে দেখা', { size: 7.2, fill: '#4fc3f7', id: 'rb14-s3b', op: 0 }) +
    rrect(412, 192, 222, 34, 4, '#161b22', '#d2a8ff', ' id="rb14-s4" opacity="0"') +
    txt(420, 206, 'teleop node — yahboom_keyboard_ctrl', { size: 7.5, mono: true, weight: 700, fill: '#d2a8ff', id: 'rb14-s4a', op: 0 }) +
    txt(420, 218, '12 key-এর ম্যাপিং, /cmd_vel + arm', { size: 7.2, fill: '#d2a8ff', id: 'rb14-s4b', op: 0 }) +
    rrect(412, 232, 222, 34, 4, '#161b22', '#e3b341', ' id="rb14-s5" opacity="0"') +
    txt(420, 246, 'camera driver + kin_ik_fk service', { size: 7.5, mono: true, weight: 700, fill: '#e3b341', id: 'rb14-s5a', op: 0 }) +
    txt(420, 258, 'rgb + depth + arm গণিত সার্ভিস', { size: 7.2, fill: '#e3b341', id: 'rb14-s5b', op: 0 }) +
    rrect(412, 272, 222, 34, 4, '#161b22', '#7ee787', ' id="rb14-s6" opacity="0"') +
    txt(420, 286, 'follow_line node — লাইন + AprilTag', { size: 7.5, mono: true, weight: 700, fill: '#7ee787', id: 'rb14-s6a', op: 0 }) +
    txt(420, 298, '+ /scan1 obstacle পাহারা', { size: 7.2, fill: '#7ee787', id: 'rb14-s6b', op: 0 }) +
    rrect(412, 312, 222, 22, 4, '#161b22', '#ff7b72', ' id="rb14-s7" opacity="0"') +
    txt(420, 326, 'one-shot arm কমান্ড, --once', { size: 7.5, mono: true, weight: 700, fill: '#ff7b72', id: 'rb14-s7t', op: 0 }) +
    rrect(412, 340, 222, 26, 4, '#161b22', '#ffb454', ' id="rb14-s8" opacity="0"') +
    txt(420, 356, 'map_saver — yahboom_map সেভ, launch বিদায়', { size: 7.5, mono: true, weight: 700, fill: '#ffb454', id: 'rb14-s8t', op: 0 }) +
    txt(660, 74, '৩টা package:', { size: 8, weight: 700, fill: '#e6edf3' }) +
    txt(660, 90, 'slam_mapping (L3, L5, L15)', { size: 7.8, mono: true, fill: '#ffb454', id: 'rb14-p1', op: 0 }) +
    txt(660, 104, 'yahboomcar_ctrl (L7)', { size: 7.8, mono: true, fill: '#d2a8ff', id: 'rb14-p2', op: 0 }) +
    txt(660, 118, 'M3Pro_demo (L9, L11)', { size: 7.8, mono: true, fill: '#7ee787', id: 'rb14-p3', op: 0 }) +
    txt(660, 140, 'জীবনচক্রের ৪ পর্ব:', { size: 8, weight: 700, fill: '#e6edf3' }) +
    txt(660, 155, '1. মানচিত্র বানাও — L1-L5', { size: 7.8, fill: '#c9d1d9', id: 'rb14-ph1', op: 0 }) +
    txt(660, 169, '2. নিজে চালাও — L7', { size: 7.8, fill: '#c9d1d9', id: 'rb14-ph2', op: 0 }) +
    txt(660, 183, '3. দেখতে দেখতে ফলো — L9-L11', { size: 7.8, fill: '#c9d1d9', id: 'rb14-ph3', op: 0 }) +
    txt(660, 197, '4. কাজ সেভ করো — L13-L15', { size: 7.8, fill: '#c9d1d9', id: 'rb14-ph4', op: 0 }) +
    txt(660, 219, 'একমাত্র L15-এর launch', { size: 7.8, weight: 700, fill: '#e6edf3', id: 'rb14-oneshot', op: 0 }) +
    txt(660, 232, 'নিজে নিজেই শেষ হয় —', { size: 7.8, fill: '#ffb454', id: 'rb14-oneshot2', op: 0 }) +
    txt(660, 245, 'map সেভ হলেই বিদায়', { size: 7.8, fill: '#ffb454', id: 'rb14-oneshot3', op: 0 }) +
    txt(450, 386, 'রঙ-নিয়ম: সবুজ = bringup/follow, হলুদ = SLAM পরিবার, নীল = RViz, বেগুনি = teleop, গোলাপি-হলুদ = camera, লাল = one-shot arm', { anchor: 'middle', size: 8.5, fill: '#8b949e' }) +
    txt(450, 440, 'source: README.md L1-L15 (commands at L1/3/5/7/9/11/13/15; blanks at even lines)', { anchor: 'middle', size: 8, mono: true, fill: '#6e7681' })
  );
  const q = id => svg.querySelector('#' + id);
  const show = id => q(id).setAttribute('opacity', 1);
  const edge = id => q(id).setAttribute('stroke', '#e3b341');
  host.caption('README-টা মোট ১৫ line-এর, তার মধ্যে ৮টা command — সবগুলোই odd line-এ (L1, L3, ... L15), মাঝের even line-গুলো ফাঁকা pause। এরা একা একেকটা command নয় — মিলে একটা <b>SLAM session</b>-এর জীবনচক্র।');
  host.formula('README = 15 lines = 8 commands at odd L1..L15 | 3 packages: slam_mapping, yahboomcar_ctrl, M3Pro_demo');
  await host.sleep(1500);
  edge('rb14-c1'); show('rb14-s1'); show('rb14-s1t'); show('rb14-ph1');
  host.caption('<b>sh start_agent.sh</b> (L1) — vendor bringup (<b>illustrative</b>, script-টা এই folder-এ নেই): chassis driver, arm driver, দুই lidar-এর raw প্রবাহ — সব ওঠে। এটাই session-এর ভিত।');
  await host.sleep(1600);
  edge('rb14-c2'); show('rb14-s2'); show('rb14-s2a'); show('rb14-s2b'); show('rb14-s2c'); show('rb14-p1');
  host.caption('<b>ros2 launch slam_mapping gmapping.launch.py</b> (L3) — এক command, কিন্তু ভেতরের launch file <b>পাঁচটা</b> program তোলে: dual-laser merger, filter, imu, ekf, আর gmapping নিজে। এই পাঁচ কান মিলে <code>/map</code> জন্ম দেয় — বিস্তারিত পরের part-এ।');
  host.formula('L3 = 1 command -> gmapping.launch.py -> 5 programs -> /map');
  await host.sleep(1700);
  edge('rb14-c3'); show('rb14-s3'); show('rb14-s3a'); show('rb14-s3b');
  host.caption('<b>ros2 launch slam_mapping slam_view.launch.py</b> (L5) — RViz খোলে <code>slam_rviz.rviz</code> config হাতে: মানচিত্র যেমন যেমন বাড়ে, তেমন তেমন দেখা যায়। এখানে কোনো নতুন robot-নিয়ন্ত্রণ জন্মায় না — জন্মায় একটা <b>দর্শক</b>।');
  await host.sleep(1600);
  edge('rb14-c4'); show('rb14-s4'); show('rb14-s4a'); show('rb14-s4b'); show('rb14-p2'); show('rb14-ph2');
  host.caption('<b>ros2 run yahboomcar_ctrl yahboom_keyboard</b> (L7) — মানুষের হাত। ১২টা key-এর mapping, <code>/cmd_vel</code>-এ Twist আর arm-এ ArmJoint/ArmJoints message। robot এবার নিজে হাঁটে — teleop পর্ব শুরু।');
  await host.sleep(1600);
  edge('rb14-c5'); show('rb14-s5'); show('rb14-s5a'); show('rb14-s5b'); show('rb14-p3'); show('rb14-ph3');
  host.caption('<b>ros2 launch M3Pro_demo camera_arm_kin.launch.py</b> (L9) — camera driver (rgb + depth) আর <code>kin_ik_fk</code> নামে arm-গণিতের service। L13-এর payload-এর চেয়ে জোরালো: LIST-argument দিয়ে include করা হয়েছে।');
  await host.sleep(1600);
  edge('rb14-c6'); show('rb14-s6'); show('rb14-s6a'); show('rb14-s6b');
  host.caption('<b>ros2 run M3Pro_demo follow_line</b> (L11) — এই folder-এর সবচেয়ে বড় file (485 line): লাইন ফলো, AprilTag দেখা, <code>/scan1</code> দিয়ে obstacle পাহারা, arm পর্যন্ত নাড়ানো — সব এক node-এ।');
  await host.sleep(1600);
  edge('rb14-c7'); show('rb14-s7'); show('rb14-s7t'); show('rb14-ph4');
  host.caption('<b>ros2 topic pub /arm6_joints ... --once</b> (L13) — ছোট্ট এক বারের কমান্ড: brace-এর ভেতরে joint1-6 আর time-এর মান, শেষে <code>--once</code>। মাত্র একটা message যাবে, তারপর command নিজেই থেমে যাবে।');
  host.formula('L13: ros2 topic pub ... --once = publish ONE message, then exit');
  await host.sleep(1600);
  edge('rb14-c8'); show('rb14-s8'); show('rb14-s8t'); show('rb14-oneshot'); show('rb14-oneshot2'); show('rb14-oneshot3');
  host.caption('<b>ros2 launch slam_mapping save_map.launch.py</b> (L15) — জীবনচক্রের শেষ কাজ: জমে থাকা <code>/map</code>-কে <code>yahboom_map</code> নামে ফাইলে লিখে রাখা। <code>map_saver_cli</code> একবারই চলে — কাজ শেষে launch নিজেই বেরিয়ে যায়, পুরো runbook-এর একমাত্র self-ending command।');
  host.formula('L15: map_saver_cli one-shot -> yahboom_map.yaml + yahboom_map.pgm -> launch exits');
  await host.sleep(1700);
  host.caption('৮টা command, ৩টা package, ৪টা পর্ব — bringup, মানচিত্র, চালানো-দেখা, সেভ। পরের part থেকে ডুবব gmapping.launch.py-এর ভেতরে: eager path আর পাঁচ-কানের launch তালিকা।');
  await host.sleep(1500);
};
