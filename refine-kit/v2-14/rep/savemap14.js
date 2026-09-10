/* ============ folder-14 anim — savemap14 (part 15, v1 layer) ============
   save_map.launch.py L1-L49. L14 map_name = "yahboom_map". L18
   default_map_path = os.path.join(get_package_share_path(
   "M3Pro_navigation"), 'map', map_name). L23-27 DeclareLaunchArgument
   map_path with that default — THIS file is the one launch in the
   folder that actually uses LaunchConfiguration lazily (L37), unlike
   gmapping's unused import. L31-42 Node: package nav2_map_server,
   executable map_saver_cli, arguments ['-f', LaunchConfiguration(
   'map_path'), '--free', '0.196', '--occ', '0.65']. Threshold math:
   occupancy grid stores probability p in [0,1] per cell; p < 0.196 ->
   WHITE free; p > 0.65 -> BLACK occupied; in-between -> GRAY unknown.
   Note asymmetry: 0.196 is NOT 1-0.65; the gray band is deliberately
   wide — unsure cells stay unknown. Output: yahboom_map.yaml (metadata
   + image ref + thresholds + origin) + yahboom_map.pgm (bitmap).
   map_saver_cli is a ONE-SHOT tool: writes files, exits — the launch
   itself then ends. Unique id prefix sv14- ; no emoji ; no arrow chars
   in stage text ; caption+formula before first await ; static backbone. */


/* ---------- savemap14 ---------- */
ANIMS.savemap14 = async function (host) {
  const svg = host.setStage(
    txt(450, 26, 'মানচিত্র তো হলো — এবার তাকে ডিস্কে লিখে রাখার শেষ দফা', { anchor: 'middle', size: 14.5, weight: 600, fill: '#ffb454' }) +
    rrect(30, 44, 330, 322, 8, '#0d1117', '#2a3442') +
    txt(46, 64, 'save_map.launch.py L1-L49 — নাম থেকে ফাইল-লেখা', { size: 10, weight: 700, fill: '#e6edf3' }) +
    rrect(46, 72, 298, 26, 4, '#161b22', '#30363d', ' id="sv14-nm"') +
    txt(54, 85, 'L14  map_name = "yahboom_map"', { size: 7.6, mono: true, weight: 700, fill: '#7ee787' }) +
    rrect(46, 102, 298, 30, 4, '#161b22', '#30363d', ' id="sv14-mp"') +
    txt(54, 116, 'L18  os.path.join(gpsh_path("M3Pro_..."),', { size: 7.4, mono: true, weight: 700, fill: '#4fc3f7' }) +
    txt(62, 127, "'map', map_name)", { size: 7.4, mono: true, weight: 700, fill: '#4fc3f7' }) +
    txt(356, 116, 'share_path', { anchor: 'end', size: 6.6, mono: true, fill: '#6e7681', id: 'sv14-mpt', op: 0 }) +
    rrect(46, 136, 298, 34, 4, '#161b22', '#7ee787', ' id="sv14-arg"') +
    txt(54, 150, "L23-27  DeclareLaunchArgument(", { size: 7.4, mono: true, weight: 700, fill: '#7ee787' }) +
    txt(62, 161, "name='map_path', default_value=...)", { size: 7.4, mono: true, fill: '#7ee787' }) +
    txt(356, 150, 'আসল ব্যবহার!', { anchor: 'end', size: 6.8, weight: 700, fill: '#7ee787', id: 'sv14-argt', op: 0 }) +
    rrect(46, 174, 298, 44, 4, '#161b22', '#30363d', ' id="sv14-node"') +
    txt(54, 188, 'L31-33  Node(package=nav2_map_server,', { size: 7.4, mono: true, fill: '#c9d1d9' }) +
    txt(62, 199, "executable='map_saver_cli')", { size: 7.4, mono: true, fill: '#c9d1d9' }) +
    txt(62, 211, 'Nav2-র অফিসিয়াল সেভ-টুল', { size: 7, fill: '#8b949e', id: 'sv14-nodet', op: 0 }) +
    rrect(46, 222, 298, 60, 4, '#161b22', '#ffb454', ' id="sv14-fa"') +
    txt(54, 236, "L36-41  arguments=[", { size: 7.4, mono: true, weight: 700, fill: '#ffb454' }) +
    txt(62, 247, "'-f', LaunchConfiguration('map_path'),", { size: 7.2, mono: true, weight: 700, fill: '#ffb454' }) +
    txt(62, 258, "'--free', '0.196',", { size: 7.2, mono: true, weight: 700, fill: '#7ee787' }) +
    txt(62, 269, "'--occ',  '0.65']", { size: 7.2, mono: true, weight: 700, fill: '#ff7b72' }) +
    rrect(46, 286, 298, 26, 4, '#161b22', '#30363d', ' id="sv14-list"') +
    txt(54, 300, 'L46-49  return LaunchDescription([map_arg,', { size: 7.4, mono: true, fill: '#c9d1d9' }) +
    txt(62, 310, 'map_saver_node])', { size: 7.4, mono: true, fill: '#c9d1d9' }) +
    txt(54, 330, 'এক argument + এক one-shot node — পুরো file এটুকুই', { size: 7.4, weight: 700, fill: '#e6edf3', id: 'sv14-sum', op: 0 }) +
    rrect(376, 44, 494, 322, 8, '#111', '#30363d') +
    txt(623, 64, 'দুই সংখ্যা কীভাবে রঙ ঠিক করে — আর কী লেখা পড়ে', { anchor: 'middle', size: 9.6, weight: 700, fill: '#e6edf3' }) +
    rrect(392, 78, 300, 120, 4, '#0d1117', '#30363d') +
    txt(542, 92, 'প্রতিটা ঘরে একটা সম্ভাবনা p (0 থেকে 1)', { anchor: 'middle', size: 7.4, weight: 700, fill: '#e6edf3', id: 'sv14-pt', op: 0 }) +
    rrect(404, 104, 82, 26, 3, '#f8f9fa', '#7ee787') +
    txt(445, 120, 'সাদা', { anchor: 'middle', size: 7.4, weight: 700, fill: '#21262d' }) +
    txt(445, 144, 'p < 0.196', { anchor: 'middle', size: 7, mono: true, fill: '#7ee787', id: 'sv14-pf', op: 0 }) +
    txt(445, 156, 'free — হাঁটা যায়', { anchor: 'middle', size: 6.6, fill: '#8b949e', id: 'sv14-pf2', op: 0 }) +
    rrect(501, 104, 82, 26, 3, '#6e7681', '#8b949e') +
    txt(542, 120, 'ধূসর', { anchor: 'middle', size: 7.4, weight: 700, fill: '#e6edf3' }) +
    txt(542, 144, '0.196 - 0.65', { anchor: 'middle', size: 7, mono: true, fill: '#8b949e', id: 'sv14-pg', op: 0 }) +
    txt(542, 156, 'unknown — অনিশ্চিত', { anchor: 'middle', size: 6.6, fill: '#8b949e', id: 'sv14-pg2', op: 0 }) +
    rrect(598, 104, 82, 26, 3, '#0a0a0a', '#ff7b72') +
    txt(639, 120, 'কালো', { anchor: 'middle', size: 7.4, weight: 700, fill: '#ff7b72' }) +
    txt(639, 144, 'p > 0.65', { anchor: 'middle', size: 7, mono: true, fill: '#ff7b72', id: 'sv14-po', op: 0 }) +
    txt(639, 156, 'occupied — দেয়াল', { anchor: 'middle', size: 6.6, fill: '#8b949e', id: 'sv14-po2', op: 0 }) +
    txt(542, 194, '0.196 মানে 1 - 0.65 নয় — ধূসর বলয়টা ইচ্ছাকৃত চওড়া', { anchor: 'middle', size: 6.8, weight: 700, fill: '#e3b341', id: 'sv14-asym', op: 0 }) +
    rrect(704, 78, 158, 120, 4, '#0d1117', '#30363d') +
    txt(783, 92, 'terminal-এ চাইলে', { anchor: 'middle', size: 7.4, weight: 700, fill: '#e6edf3' }) +
    rrect(712, 100, 142, 40, 3, '#161b22', '#30363d', ' id="sv14-cli"') +
    txt(783, 116, 'ros2 launch ... map_path:=', { anchor: 'middle', size: 6.6, mono: true, fill: '#7ee787' }) +
    txt(783, 128, 'আমার_নতুন_নাম', { anchor: 'middle', size: 6.6, mono: true, weight: 700, fill: '#7ee787' }) +
    txt(783, 152, 'না লিখলে default:', { anchor: 'middle', size: 6.8, fill: '#8b949e', id: 'sv14-clit', op: 0 }) +
    txt(783, 164, 'M3Pro_navigation/map/yahboom_map', { anchor: 'middle', size: 6.2, mono: true, fill: '#8b949e', id: 'sv14-clit2', op: 0 }) +
    txt(783, 186, '(path অনুযায়ী illustrative)', { anchor: 'middle', size: 6, fill: '#6e7681', id: 'sv14-clit3', op: 0 }) +
    rrect(392, 206, 470, 64, 4, '#0d1117', '#7ee787', ' id="sv14-files" opacity="0"') +
    txt(400, 220, 'লেখা পড়ে দুটি ফাইল (one-shot, তারপর টুল বেরিয়ে যায়):', { size: 7.4, weight: 700, fill: '#e6edf3', id: 'sv14-fhead', op: 0 }) +
    rrect(400, 228, 222, 32, 3, '#161b22', '#7ee787') +
    txt(406, 241, 'yahboom_map.yaml', { size: 7, mono: true, weight: 700, fill: '#7ee787' }) +
    txt(406, 253, 'থ্রেশহোল্ড, origin, রেজোলিউশন, pgm-এর রেফারেন্স', { size: 6.2, fill: '#8b949e' }) +
    rrect(632, 228, 222, 32, 3, 'none', '#30363d', ' id="sv14-pgm2" opacity="0"') +
    txt(638, 241, 'yahboom_map.pgm', { size: 7, mono: true, weight: 700, fill: '#d2a8ff' }) +
    txt(638, 253, 'সাদা-কালো-ধূসর বিটম্যাপ — আসল মানচিত্রের ছবি', { size: 6.2, fill: '#8b949e' }) +
    rrect(392, 276, 470, 26, 4, '#161b22', '#ff7b72', ' id="sv14-exit" opacity="0"') +
    txt(627, 292, 'map_saver_cli একবারের টুল: লিখেই বিদায় — launch-ও সেখানেই শেষ', { anchor: 'middle', size: 7.4, weight: 700, fill: '#ff7b72', id: 'sv14-exitt', op: 0 }) +
    txt(623, 318, 'gmapping-এর সারা পরিশ্রম এতটুকু ফাইলে জমা — পরের যুগের navigation তার ওপরেই দাঁড়াবে', { anchor: 'middle', size: 7.6, weight: 700, fill: '#e6edf3', id: 'sv14-fin', op: 0 }) +
    txt(450, 386, 'রঙ-নিয়ম: সবুজ = নাম/free, নীল = path, হলুদ = -f, লাল = occupied/প্রস্থান, বেগুনি = pgm', { anchor: 'middle', size: 8.5, fill: '#8b949e' }) +
    txt(450, 440, 'source: save_map.launch.py L1-L49 (map_name L14, path L18, map_arg L23-27, map_saver_cli L31-42, thresholds L37-40, list L46-49)', { anchor: 'middle', size: 7.8, mono: true, fill: '#6e7681' })
  );
  const q = id => svg.querySelector('#' + id);
  const show = id => q(id).setAttribute('opacity', 1);
  const edge = id => q(id).setAttribute('stroke', '#e3b341');
  host.caption('gmapping-এর বানানো মানচিত্র শুধু মেমোরিতে ভাসলে চলবে না — বিদ্যুৎ গেলেই সব শেষ। এই ৪৯ লাইনের launch file-টাই মানচিত্রটাকে <b>ডিস্কে লিখে</b> দেয়, চিরস্থায়ী করে।');
  host.formula('save_map.launch.py = 1 name + 1 arg + 1 one-shot node -> 2 files');
  await host.sleep(1500);
  edge('sv14-nm'); edge('sv14-mp'); show('sv14-mpt');
  host.caption('শুরু নাম দিয়ে (L14): <code>map_name = "yahboom_map"</code>। তারপর ঠিকানা (L18): <code>M3Pro_navigation</code> package-এর <code>map</code> ফোল্ডার — লক্ষ করো এখানে <code>get_package_share_path</code>, gmapping-এর <code>...directory</code> নয়; একই কাজ, আলাদা ফাংশন।');
  await host.sleep(1700);
  edge('sv14-arg'); show('sv14-argt');
  host.caption('মজার তুলনা: gmapping.launch.py <code>LaunchConfiguration</code> import করেও কখনো ব্যবহার করেনি; এই file-টা <b>সত্যিই</b> ব্যবহার করে (L23-27, L37)। terminal-এ <code>map_path:=নতুন_নাম</code> লিখলে অন্য নামে সেভ, না লিখলে default yahboom_map।');
  host.formula("map_path:=my_name overrides default ; LaunchConfiguration('map_path') resolves AT RUN TIME (lazy)");
  await host.sleep(1800);
  edge('sv14-node'); show('sv14-nodet');
  host.caption('সেভ-টুলটা নিজের লেখা নয় — Nav2-র অফিসিয়াল <code>map_saver_cli</code> (L31-33)। launch file-টা কেবল তাকে ডেকে সঠিক argument হাতে তুলে দেয়।');
  await host.sleep(1600);
  edge('sv14-fa'); show('sv14-pt'); show('sv14-pf'); show('sv14-pf2'); show('sv14-pg'); show('sv14-pg2'); show('sv14-po'); show('sv14-po2'); show('sv14-asym');
  host.caption('দুই সংখ্যার জাদু (L37-40): মানচিত্রের প্রতিটা ঘরে একটা সম্ভাবনা p — "এই ঘরটা দেয়াল, কতটা নিশ্চিত?" <code>p < 0.196</code> সাদা (হাঁটা যায়), <code>p > 0.65</code> কালো (দেয়াল), মাঝেরটা ধূসর (অজানা)। আর খেয়াল করো — 0.196 মানে 1 − 0.65 <b>নয়</b>; ধূসর বলয় ইচ্ছাকৃতভাবে চওড়া, দ্বিধাগ্রস্ত ঘর সরাসরি "অজানা" থাকে।');
  host.formula('p < 0.196 -> white free ; p > 0.65 -> black occupied ; else gray unknown');
  await host.sleep(2000);
  show('sv14-cli'); show('sv14-clit'); show('sv14-clit2'); show('sv14-clit3');
  host.caption('নাম বদলানোর রাস্তাও এখানেই — <code>ros2 launch ... map_path:=আমার_নাম</code>। default রেখে দিলে ফাইল পড়ে যাবে M3Pro_navigation-এর map ফোল্ডারে, ঠিক যেখানে পরের ধাপের navigation খুঁজে নেবে।');
  await host.sleep(1700);
  show('sv14-files'); show('sv14-fhead'); show('sv14-pgm2');
  host.caption('কাজ শেষে ডিস্কে <b>দুটি ফাইল</b>: <code>yahboom_map.yaml</code> — থ্রেশহোল্ড, রেজোলিউশন, origin, ছবির রেফারেন্স; আর <code>yahboom_map.pgm</code> — সাদা-কালো-ধূসর বিটম্যাপ, আসল মানচিত্রের ছবি। যে দুটি সংখ্যা রঙ ঠিক করল, সেই মানই yaml-এ লেখা থাকে — পরে খুললে একই মানচিত্র ফের পাওয়া যায়।');
  await host.sleep(1800);
  show('sv14-exit'); show('sv14-exitt'); show('sv14-sum'); show('sv14-fin');
  host.caption('শেষ কথা: <code>map_saver_cli</code> একবারের টুল — লিখেই বেরিয়ে যায়, launch-ও সেখানেই সমাপ্ত। README-র শেষ command এভাবেই সমাপ্তি টানে: আটটা ধাপ, সাতটা file, চার program-এর চেইন, এক মানচিত্র — ডিস্কে চিরস্থায়ী।');
  await host.sleep(1800);
};
