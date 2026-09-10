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
