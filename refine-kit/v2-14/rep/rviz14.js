/* ============ folder-14 anim — rviz14 (part 4, v1 layer) ============
   slam_view.launch.py L1-L59. L2-3 comment: seven unused imports the
   source ITSELF acknowledges ("unused imports... for reference" per
   source comment). L24 use_sim_time LaunchConfiguration (declared in
   ctor, passed as an argument later). L30-34 rviz_config = os.path.join
   (gpshd('slam_mapping'), 'rviz', 'slam_rviz.rviz'). L41-52 rviz Node:
   package rviz2, executable rviz2, name rviz, output log; L48-52
   arguments=['-d', rviz_config, use_sim_time] — the '-d' flag loads a
   display-config file. Two-entry list L56-59: rviz_config_arg (declare)
   + rviz_node. Run phase: arg processes, node fires — RViz opens the
   saved layout: Grid + Map (/map) + LaserScan (/scan) + TF, fixed
   frame /map. Unique id prefix rv14- ; no emoji ; no arrow chars in
   stage text ; caption+formula before the first await ; static
   backbone at setStage. */


/* ---------- rviz14 ---------- */
ANIMS.rviz14 = async function (host) {
  const svg = host.setStage(
    txt(450, 26, 'একটা file-পড়া node অথচ চোখের জানালা — RViz আর তার -d চাবি', { anchor: 'middle', size: 14.5, weight: 600, fill: '#4fc3f7' }) +
    rrect(30, 44, 330, 322, 8, '#0d1117', '#2a3442') +
    txt(46, 64, 'slam_view.launch.py L1-L59', { size: 10, weight: 700, fill: '#e6edf3' }) +
    rrect(46, 72, 298, 30, 4, '#161b22', '#30363d', ' id="rv14-imp"') +
    txt(54, 86, 'L2-3  # NOTE: unused imports...', { size: 7.6, mono: true, fill: '#8b949e' }) +
    txt(54, 97, 'সাতটা import — source নিজেই স্বীকার করে', { size: 7.2, fill: '#8b949e', id: 'rv14-impt', op: 0 }) +
    rrect(46, 106, 298, 24, 4, '#161b22', '#30363d', ' id="rv14-st"') +
    txt(54, 120, "L24  use_sim_time = LaunchConfiguration('...')", { size: 7.6, mono: true, weight: 700, fill: '#e3b341' }) +
    txt(54, 142, 'L30-34 — একটাই আসল path', { size: 8.4, weight: 700, fill: '#e6edf3' }) +
    rrect(46, 150, 298, 40, 4, '#161b22', '#4fc3f7', ' id="rv14-cfg"') +
    txt(54, 165, "rviz_config = os.path.join(", { size: 7.8, mono: true, weight: 700, fill: '#4fc3f7' }) +
    txt(62, 177, "gpshd('slam_mapping'), 'rviz',", { size: 7.6, mono: true, weight: 700, fill: '#4fc3f7' }) +
    txt(62, 189, "'slam_rviz.rviz')", { size: 7.6, mono: true, weight: 700, fill: '#4fc3f7' }) +
    txt(54, 210, 'L41-52 — rviz Node + arguments', { size: 8.4, weight: 700, fill: '#e6edf3' }) +
    rrect(46, 218, 298, 30, 4, '#161b22', '#30363d', ' id="rv14-node"') +
    txt(54, 232, 'Node(package=rviz2, executable=rviz2,', { size: 7.6, mono: true, fill: '#8b949e' }) +
    txt(54, 243, "  name='rviz', output='log')", { size: 7.6, mono: true, fill: '#8b949e' }) +
    rrect(46, 254, 298, 34, 4, '#161b22', '#ffb454', ' id="rv14-args"') +
    txt(54, 268, "arguments=['-d', rviz_config,", { size: 7.8, mono: true, weight: 700, fill: '#ffb454' }) +
    txt(62, 280, '            use_sim_time]', { size: 7.6, mono: true, weight: 700, fill: '#ffb454' }) +
    txt(356, 268, 'L48-52', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    rrect(46, 294, 298, 26, 4, '#161b22', '#30363d', ' id="rv14-list"') +
    txt(54, 311, 'L56-59  return [... দুই entry ...]', { size: 7.8, mono: true, fill: '#c9d1d9' }) +
    txt(54, 340, 'launch নয়, চোখ — এখানে কোনো robot-চালনা নেই', { size: 7.4, fill: '#8b949e', id: 'rv14-note', op: 0 }) +
    rrect(376, 44, 494, 322, 8, '#111', '#30363d') +
    txt(623, 64, 'RViz — slam_rviz.rviz খুললে যা দেখা যায়', { anchor: 'middle', size: 9.6, weight: 700, fill: '#e6edf3' }) +
    rrect(392, 76, 462, 218, 4, '#0d1117', '#4fc3f7', ' id="rv14-win" opacity="0"') +
    rrect(392, 76, 462, 18, 4, '#161b22', '#30363d', ' id="rv14-titlebar" opacity="0"') +
    txt(400, 88, 'RViz - slam_rviz.rviz', { size: 7.4, mono: true, weight: 700, fill: '#e6edf3', id: 'rv14-title', op: 0 }) +
    rrect(398, 102, 78, 186, 3, '#0d1117', '#21262d', ' id="rv14-side" opacity="0"') +
    txt(404, 114, 'Displays', { size: 6.6, weight: 700, fill: '#e6edf3', id: 'rv14-sideT', op: 0 }) +
    txt(404, 128, 'Grid', { size: 6.4, mono: true, fill: '#8b949e', id: 'rv14-d1', op: 0 }) +
    txt(404, 140, 'Map /map', { size: 6.4, mono: true, fill: '#7ee787', id: 'rv14-d2', op: 0 }) +
    txt(404, 152, 'LaserScan', { size: 6.4, mono: true, fill: '#ffb454', id: 'rv14-d3', op: 0 }) +
    txt(404, 164, 'TF', { size: 6.4, mono: true, fill: '#d2a8ff', id: 'rv14-d4', op: 0 }) +
    txt(404, 176, 'RobotModel', { size: 6.4, mono: true, fill: '#8b949e', id: 'rv14-d5', op: 0 }) +
    txt(404, 196, 'Global', { size: 6.6, weight: 700, fill: '#e6edf3', id: 'rv14-gT', op: 0 }) +
    txt(404, 208, 'Fixed:', { size: 6.2, fill: '#8b949e', id: 'rv14-fxT', op: 0 }) +
    txt(404, 219, '/map', { size: 6.6, mono: true, weight: 700, fill: '#7ee787', id: 'rv14-fx', op: 0 }) +
    path('M484 196h36v92h-36z', '#30363d', 0.8, ' id="rv14-mapgrid" opacity="0"') +
    path('M484 220h12v44h-12z M484 268h12v20h-12z', '#7ee787', 0, ' id="rv14-mapfree" opacity="0.75" fill="#7ee787"') +
    path('M508 196h12v28h-12z M508 240h12v24h-12z', '#ff7b72', 0, ' id="rv14-mapocc" opacity="0.75" fill="#ff7b72"') +
    rrect(530, 240, 22, 26, 3, '#161b22', '#4fc3f7', ' id="rv14-robot" opacity="0"') +
    path('M541 240l5-8 5 8z', '#4fc3f7', 0, ' id="rv14-head" fill="#4fc3f7" opacity="0"') +
    path('M546 236l16-10 M546 236l-14-12 M546 236l20 8', '#ffb454', 1, ' id="rv14-beams" opacity="0"') +
    path('M541 262c-8 6-18 8-26 4', '#d2a8ff', 1.2, ' id="rv14-trail" opacity="0"') +
    txt(560, 300, 'সাদা = free, লাল = occupied, ধূসর = unknown', { size: 6.6, fill: '#8b949e', id: 'rv14-legend', op: 0 }) +
    rrect(392, 302, 462, 24, 4, '#161b22', '#e3b341', ' id="rv14-live" opacity="0"') +
    txt(623, 317, 'gmapping যত এগোয়, /map তত টাইলে টাইলে এখানে জমে — লাইভ', { anchor: 'middle', size: 7.6, weight: 700, fill: '#e3b341', id: 'rv14-livet', op: 0 }) +
    txt(623, 342, '-d মানে: layout-ফাইল বলে দেওয়া — কোন কোন display, কোন রঙ, কোন frame', { anchor: 'middle', size: 7.6, fill: '#c9d1d9', id: 'rv14-dflag', op: 0 }) +
    txt(450, 386, 'রঙ-নিয়ম: নীল = rviz/config, হলুদ = arguments/-d, সবুজ = map, লাল = দেয়াল, বেগুনি = tf-পথ', { anchor: 'middle', size: 8.5, fill: '#8b949e' }) +
    txt(450, 440, 'source: slam_view.launch.py L1-L59 (unused imports L2-3, use_sim_time L24, rviz_config L30-34, Node L41-52, list L56-59)', { anchor: 'middle', size: 7.8, mono: true, fill: '#6e7681' })
  );
  const q = id => svg.querySelector('#' + id);
  const show = id => q(id).setAttribute('opacity', 1);
  const edge = id => q(id).setAttribute('stroke', '#e3b341');
  host.caption('gmapping মানচিত্র বানায় — কিন্তু বানানো দেখার জানালা দরকার। সেই জানালার নাম <b>RViz</b>, আর এই 59-line-এর launch file-টা শুধুই সেই জানালা খোলার কাজ করে।');
  host.formula('slam_view.launch.py = 1 node (rviz2) + 1 arg + 1 config path = the eyes');
  await host.sleep(1500);
  edge('rv14-imp'); show('rv14-impt');
  host.caption('শুরুতেই মজার স্বীকারোক্তি — L2-3-এর মন্তব্যে <b>source নিজেই</b> বলে দিয়েছে সাতটা import অব্যবহৃত। লজ্জা নয়, সততা; ওদের রেখে দেওয়ার কারণ হয়তো ভবিষ্যতের কপি-পেস্ট — আমরা শুধু দেখে নিই, ঠিক করি না।');
  await host.sleep(1600);
  edge('rv14-st');
  host.caption('L24: <code>use_sim_time</code> — একটা lazy সেটিংস-বাক্স। ব্যাগ-ফাইল বা সিমুলেশন চালালে ROS-ঘড়ি সিরিয়াল হতে পারে; এই পতাকা সেটাই ঠিক করে দেয়। এখানে সেটা rviz-কে পাঠানো হয়েছে arguments-এর ভেতর দিয়ে।');
  await host.sleep(1600);
  edge('rv14-cfg');
  host.caption('L30-34: একটাই আসল path — <code>slam_mapping</code> package-এর <code>rviz</code> ফোল্ডারের <code>slam_rviz.rviz</code>। এই ফাইলটা কোনো প্রোগ্রাম নয়; একটা <b>সাজানোর নকশা</b> — কোন কোন display খোলা থাকবে, কোন রঙে, কোন frame-এ।');
  host.formula("rviz_config = share/slam_mapping/rviz/slam_rviz.rviz (a layout, not code)");
  await host.sleep(1700);
  edge('rv14-node'); edge('rv14-args');
  host.caption('L41-52: Node নিজে সাদামাটা — <code>rviz2</code> package, <code>rviz2</code> executable। আসল চাবি <code>arguments</code>-এ (L48-52): <b>-d</b> পতাকা পেলে RViz উঠতেই ওই নকশা-ফাইল খুলে বসে। না থাকলে খালি পর্দা নিয়ে হাত-পা গুটিয়ে বসে থাকত।');
  host.formula("arguments = ['-d', rviz_config, use_sim_time]  # -d = load display config");
  await host.sleep(1700);
  edge('rv14-list'); show('rv14-win'); show('rv14-titlebar'); show('rv14-title'); show('rv14-side'); show('rv14-sideT'); show('rv14-d1');
  host.caption('run phase: দুই entry চলে — আগে arg-টা প্রক্রিয়া হয়, তারপর node ফায়ার করে। RViz উঠল, <code>-d</code>-এর নকশা মতোই Displays-প্যানেল সাজাল — শুরুতে Grid।');
  await host.sleep(1600);
  show('rv14-d2'); show('rv14-d3'); show('rv14-d4'); show('rv14-d5'); show('rv14-gT'); show('rv14-fxT'); show('rv14-fx'); show('rv14-mapgrid');
  host.caption('তারপর আসল মেহমানেরা: <b>Map</b> (সবুজ — <code>/map</code> topic থেকে), <b>LaserScan</b> (হলুদ — <code>/scan</code>), <b>TF</b> (বেগুনি — কোথায় কোন frame), RobotModel। Fixed frame <code>/map</code> — মানে পুরো দৃশ্যের কেন্দ্র-সূত্র মানচিত্রটাই।');
  host.formula('fixed frame /map ; displays: Grid + Map(/map) + LaserScan(/scan) + TF');
  await host.sleep(1700);
  show('rv14-mapfree'); show('rv14-mapocc'); show('rv14-robot'); show('rv14-head'); show('rv14-beams'); show('rv14-trail'); show('rv14-legend');
  host.caption('টাইল-এর ভাষা: সাদা-সবুজ ঘর = হাঁটা যায় (free), লাল ঘর = দেয়াল (occupied), বাকি ধূসর = এখনো অজানা। robot নীল, তার সামনে হলুদ beam-গুচ্ছ, পেছনে বেগুনি বাঁকা পথচিহ্ন — যেটা দিয়ে সে ঘুরে এসেছে।');
  await host.sleep(1600);
  show('rv14-live'); show('rv14-livet'); show('rv14-dflag');
  host.caption('আর সবচেয়ে সুন্দর অংশ: এটা স্থির ছবি নয়। gmapping যত এগোয়, <code>/map</code> তত টাইলে টাইলে এখানে জমতে থাকে — <b>লাইভ</b>। SLAM চলতে চলতে মানচিত্র ফুটতে দেখা, এই launch file-এর একটাই কাজ সেটাই।');
  await host.sleep(1700);
  host.caption('মানচিত্র হলো, দেখাও হলো — এবার robot-কে নিজের হাতে নেওয়ার পালা। পরের part: yahboom_keyboard, ১২টা key-এর ম্যাপিং আর তার গণিত।');
  await host.sleep(1500);
};
