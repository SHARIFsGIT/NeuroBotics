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
