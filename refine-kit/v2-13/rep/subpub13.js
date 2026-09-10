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
