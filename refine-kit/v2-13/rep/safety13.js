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
