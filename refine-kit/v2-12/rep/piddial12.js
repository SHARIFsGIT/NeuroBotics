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
