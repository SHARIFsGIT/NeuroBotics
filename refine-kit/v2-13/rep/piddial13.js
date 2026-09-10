/* ---------- pidDial ---------- */
/* ===== folder-13 anim — pidDial (part 13) ============================
   laser_Warning.py L96-L110, the SINGLE-PID heart (the tracker's
   folder-12 twin had two). Left: code card L96-L110 (L98 velocity =
   Twist(), L99 print minDistID, L103 angular call, L106-110 sign
   branch). Right: ONE PID card — ang SinglePID(3.0, 0.0, 5.0) born
   L48, constructed once, state persists across scans; the tracker's
   freed LIN space goes to a wider u-dial (0..2.0, ceiling tick
   1.875) + a Kp/Ki/Kd gain strip + the L47 cross-folder note
   "tuned a bit more aggressively than the tracker" (REAL: tracker
   = folder 12 ang SinglePID(2.0, 0.0, 2.0)). NO snap (tracker L96
   snapped minDist := 0.55 before its linear PID) and NO linear PID
   — linear.x is never assigned anywhere. Wave-B illustrative
   numbers: minDist 0.70, minDistID +20 -> e = 20/72 = 0.278 ->
   u = 3*0.278 = 0.833 -> z = +0.833 (pre-damping); Wave D 0.50 m
   @ -20 deg -> u = 0.833 -> z = -0.833. abs() makes the error
   sign-free, target 0 (L102 comment); 72 is a bare magic number
   the file never explains; ceiling |a| -> 45- -> u -> 3*(45/72) =
   1.875. Optional one-line Kd caveat: large Kd = 5 adds a
   same-sign transient on the first call after a scene change
   (illustrative). STOPS at ang_pid_compute + sign branch —
   deadzone/damping/publish belong to cmdVelVectors. Prefix pd-.
   No emoji, no arrow chars in stage strings, entities for
   &lt; &gt;. */

ANIMS.pidDial = async function (host) {
  const svg = host.setStage(
    txt(450, 26, 'একটাই PID: মুখ ঘোরাও (angular) — linear PID নেই, snap নেই — L98-L99, L103, L106-110', { anchor: 'middle', size: 13.5, weight: 600, fill: '#ffb454' }) +
    /* ---------- left: code L96-L110 ---------- */
    rrect(40, 44, 340, 316, 8, '#0d1117', '#2a3442') +
    txt(56, 62, 'CODE — laser_Warning.py L96-L110', { size: 9.5, weight: 700, fill: '#e6edf3' }) +
    rrect(50, 104, 320, 29, 3, '#21262d', 'none', ' id="pd-hl1" opacity="0"') +
    rrect(50, 168, 320, 29, 3, '#21262d', 'none', ' id="pd-hl2" opacity="0"') +
    rrect(50, 216, 320, 29, 3, '#21262d', 'none', ' id="pd-hl3" opacity="0"') +
    rrect(50, 253, 320, 29, 3, '#21262d', 'none', ' id="pd-hl4" opacity="0"') +
    txt(58, 86, '# --- THE TRACKING LOGIC ---', { size: 7, mono: true, fill: '#6e7681' }) +
    txt(58, 104, 'velocity = Twist()', { size: 8, mono: true, fill: '#c9d1d9' }) +
    txt(368, 104, 'L98', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    txt(58, 117, 'print("minDistID: ", minDistID)', { size: 8, mono: true, fill: '#c9d1d9' }) +
    txt(368, 117, 'L99', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    txt(58, 134, '# Calculate how much to turn to face the object.', { size: 7, mono: true, fill: '#6e7681' }) +
    txt(58, 147, '# Target Angle is 0 ... Current Angle is minDistID', { size: 7, mono: true, fill: '#6e7681' }) +
    txt(368, 147, 'L101-102', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    txt(58, 168, 'ang_pid_compute = self.ang_pid.pid_compute(', { size: 8, mono: true, fill: '#c9d1d9' }) +
    txt(58, 181, '    abs(minDistID) / 72, 0)', { size: 8, mono: true, fill: '#c9d1d9' }) +
    txt(368, 181, 'L103', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    txt(58, 216, 'if 0 &lt; minDistID :', { size: 8, mono: true, fill: '#c9d1d9' }) +
    txt(58, 230, 'velocity.angular.z = ang_pid_compute', { size: 8, mono: true, fill: '#c9d1d9' }) +
    txt(368, 230, 'L106-107', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    txt(58, 253, 'elif minDistID &lt; 0:', { size: 8, mono: true, fill: '#c9d1d9' }) +
    txt(58, 267, 'velocity.angular.z = -ang_pid_compute', { size: 8, mono: true, fill: '#c9d1d9' }) +
    txt(368, 267, 'L109-110', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    txt(58, 290, 'L105/L108-এর comment: বাঁ = positive angle, ডান = negative', { size: 7, fill: '#6e7681' }) +
    txt(58, 306, 'minDistID = 0.0 হলে দুই branch-ই মিস — z জন্মলগ্ন 0.0-ই', { size: 7, fill: '#6e7681', id: 'pd-zero', op: 0 }) +
    txt(58, 330, 'minDist = 0.70 m · minDistID = +20° (Wave B, illustrative)', { size: 7.5, weight: 700, mono: true, fill: '#e3b341', id: 'pd-wave', op: 0 }) +
    txt(58, 348, 'vendor SinglePID-এর ভেতরটা এই folder-এ নেই — pid ফল Kp-only illustrative', { size: 6.8, fill: '#6e7681' }) +
    /* ---------- right-top: the ONE ANG PID card (tracker-এর LIN জায়গা মিলে বড়) ---------- */
    rrect(396, 44, 464, 148, 8, '#0d1117', '#e3b341') +
    txt(408, 62, 'ANG PID — SinglePID(3.0, 0.0, 5.0) — guard-এর একমাত্র PID', { size: 8.5, mono: true, weight: 700, fill: '#e3b341' }) +
    txt(408, 74, 'জন্ম L48-এ, একবারই — state scan-এ স্ক্যানে বাঁচে', { size: 6.8, fill: '#8b949e' }) +
    rrect(408, 82, 224, 16, 3, '#161b22', '#30363d') +
    txt(414, 93, 'call: pid_compute(abs(minDistID) / 72, 0)', { size: 7, mono: true, fill: '#c9d1d9' }) +
    txt(638, 92, 'gains:', { anchor: 'end', size: 6.8, fill: '#8b949e' }) +
    rrect(644, 82, 66, 14, 3, '#161b22', '#30363d') +
    txt(677, 92, 'Kp = 3.0', { anchor: 'middle', size: 7, mono: true, fill: '#c9d1d9' }) +
    rrect(714, 82, 66, 14, 3, '#161b22', '#30363d') +
    txt(747, 92, 'Ki = 0.0', { anchor: 'middle', size: 7, mono: true, fill: '#c9d1d9' }) +
    rrect(784, 82, 64, 14, 3, '#161b22', '#30363d') +
    txt(816, 92, 'Kd = 5.0', { anchor: 'middle', size: 7, mono: true, fill: '#c9d1d9' }) +
    rrect(408, 102, 140, 14, 3, '#161b22', '#30363d', ' id="pd-aeB" opacity="0"') +
    txt(414, 112, 'e = abs(+20)/72 = 0.278', { size: 7, mono: true, fill: '#8b949e', id: 'pd-ae', op: 0 }) +
    rrect(554, 102, 150, 14, 3, '#161b22', '#30363d', ' id="pd-auB" opacity="0"') +
    txt(560, 112, 'u ~= 3.0 * 0.278 = 0.833', { size: 7, mono: true, fill: '#8b949e', id: 'pd-au', op: 0 }) +
    txt(644, 112, 'L47 comment: tracker-এর (2, 0, 2)-এর চেয়ে aggressive', { size: 6.8, fill: '#8b949e' }) +
    '<path d="M420 142L838 142" stroke="#30363d" stroke-width="2"/>' +
    txt(420, 136, '0', { size: 6.5, mono: true, fill: '#6e7681' }) +
    txt(629, 136, '1.0', { anchor: 'middle', size: 6.5, mono: true, fill: '#6e7681' }) +
    txt(838, 136, '2.0', { anchor: 'end', size: 6.5, mono: true, fill: '#6e7681' }) +
    '<path d="M812 135L812 149" stroke="#f85149" stroke-width="1.5" stroke-dasharray="3 2" id="pd-ctick" opacity="0"/>' +
    txt(812, 130, 'ceiling 1.875', { anchor: 'middle', size: 6, mono: true, fill: '#ff7b72', id: 'pd-ceil', op: 0 }) +
    '<path d="M420 142L594 142" stroke="#e3b341" stroke-width="3" id="pd-an" opacity="0"/>' +
    circ(594, 142, 4, '#e3b341', ' id="pd-and" opacity="0"') +
    txt(594, 158, 'u = 0.833 (magnitude)', { anchor: 'middle', size: 6.5, mono: true, fill: '#8b949e', id: 'pd-ant', op: 0 }) +
    rrect(408, 166, 226, 18, 9, '#161b22', '#e3b341', ' id="pd-axB" opacity="0"') +
    txt(521, 178, 'ang_pid_compute = 0.833 (pre-damping)', { anchor: 'middle', size: 7.5, mono: true, weight: 700, fill: '#e3b341', id: 'pd-ax', op: 0 }) +
    txt(712, 178, 'target = 0 — সোজা সামনে (L102)', { size: 6.8, fill: '#8b949e' }) +
    /* ---------- right-middle: sign branch ---------- */
    rrect(396, 200, 464, 96, 8, '#111', '#30363d') +
    txt(408, 218, 'SIGN BRANCH — L106-110: direction ফেরাও abs() যা ফেলে দিয়েছিল', { size: 8.5, weight: 700, fill: '#e6edf3' }) +
    rrect(408, 226, 144, 26, 5, '#161b22', '#4fc3f7', ' id="pd-br1" opacity="0"') +
    txt(416, 238, '0 &lt; minDistID  (+20)', { size: 7.5, mono: true, weight: 700, fill: '#4fc3f7' }) +
    txt(416, 249, 'z = +0.833 — বাঁ CCW', { size: 7.5, mono: true, fill: '#4fc3f7' }) +
    rrect(558, 226, 144, 26, 5, '#161b22', '#e3b341', ' id="pd-br2" opacity="0"') +
    txt(566, 238, 'minDistID &lt; 0  (-20)', { size: 7.5, mono: true, weight: 700, fill: '#e3b341' }) +
    txt(566, 249, 'z = -0.833 — ডান CW', { size: 7.5, mono: true, fill: '#e3b341' }) +
    rrect(708, 226, 140, 26, 5, '#161b22', '#30363d', ' id="pd-br3" opacity="0"') +
    txt(716, 238, 'minDistID == 0.0', { size: 7.5, mono: true, weight: 700, fill: '#8b949e' }) +
    txt(716, 249, 'কোনোটাই না — z = 0.0', { size: 7.5, mono: true, fill: '#8b949e' }) +
    txt(408, 272, 'ROS নিয়ম: ধনাত্মক angular.z = CCW = বাঁয়ে ঘোরা — L105/L108-এর comment-ই বলছে সেটা', { size: 7, fill: '#8b949e', id: 'pd-bnote', op: 0 }) +
    txt(408, 286, 'দুই branch-এ |z| সমান 0.833 — শুধু চিহ্ন বদলায়, PID একবারই চলে', { size: 7, fill: '#8b949e', id: 'pd-bnote2', op: 0 }) +
    /* ---------- right-bottom: warnings ---------- */
    rrect(396, 304, 464, 56, 8, '#0d1117', '#f85149') +
    txt(408, 322, 'snap নেই, linear PID নেই', { size: 8.5, weight: 700, fill: '#ff7b72' }) +
    txt(408, 336, 'tracker (folder 12)-এর L96 snap আর lin_pid এই file-এ নেই —', { size: 7.5, fill: '#c9d1d9' }) +
    txt(408, 348, 'linear.x কেউ লেখেই না: Twist()-এর জন্মলগ্ন 0.0-ই থাকে, শুধু ঘোরা', { size: 7.5, fill: '#c9d1d9' }) +
    txt(700, 322, '/72 = magic number', { anchor: 'middle', size: 8.5, weight: 700, fill: '#d2a8ff' }) +
    txt(700, 336, 'file কোথাও 72 ব্যাখ্যা করে না — শুধু কোণকে ছোট', { anchor: 'middle', size: 7.5, fill: '#c9d1d9' }) +
    txt(700, 348, 'সংখ্যায় নামায়; কার্যকর সর্বোচ্চ e &lt; 45/72 = 0.625', { anchor: 'middle', size: 7.5, fill: '#c9d1d9' }) +
    txt(450, 386, 'রঙ-নিয়ম: হলুদ = angular channel (একটাই PID), নীল = বাঁ, কমলা = ডান, লাল = সতর্কতা', { anchor: 'middle', size: 8, fill: '#8b949e' }) +
    txt(450, 440, 'source: laser_Warning.py L96-L110 · ang_pid L48 (3.0, 0.0, 5.0) · comment L47 · RAD2DEG L16', { anchor: 'middle', size: 7.5, mono: true, fill: '#6e7681' })
  );
  const q = id => svg.querySelector('#' + id);
  const show = ids => ids.forEach(i => q(i).setAttribute('opacity', 1));
  host.caption('registerScan-এর হিসাবের হৃদয় — এবার একটাই PID controller, একটাই প্রশ্ন। Tracker-এ (folder 12) দুটো PID ছিল — দূরত্ব মেলানো আর মুখ ঘোরানো; guard-এ <code>lin_pid</code> নেই, snap নেই — শুধু <code>ang_pid</code> (L48) জিজ্ঞেস করে object মুখ থেকে কত বাঁয়ে-ডানে। Constructor-এ একবার জন্মেছে — ভেতরের state scan-এ স্ক্যানে বেঁচে থাকে।');
  host.formula('ang_pid = SinglePID(3.0, 0.0, 5.0) @L48  [state persists]  |  no lin_pid, no snap — tracker-এর L96 snap এখানে নেই');
  await host.sleep(1700);
  /* --- beat 1: L98-99 fresh Twist + print --- */
  show(['pd-hl1', 'pd-wave']);
  host.caption('<b>L98</b>: <code>velocity = Twist()</code> — প্রতি scan-এ টাটকা একটা Twist, সব ঘর জন্মলগ্ন 0.0। <b>L99</b> console-এ minDistID ছাপে। Wave B (illustrative): minDist = 0.70 m, minDistID = +20 — object বাঁয়ে। খেয়াল রেখো: এই পুরো block-এ <code>linear.x</code> কেউ লেখেই না — এই anim স্রেফ <code>ang_pid_compute</code> আর sign branch-এ থেমে যাবে; deadzone, damping, publish পরের part-ের ব্যাপার।');
  host.formula('Wave B (illustrative): minDist = 0.70 m · minDistID = +20 deg  |  linear.x: never assigned (no lin_pid)');
  await host.sleep(2100);
  /* --- beat 2: L103 the one compute --- */
  show(['pd-hl2', 'pd-aeB', 'pd-ae', 'pd-auB', 'pd-au', 'pd-an', 'pd-and', 'pd-ant', 'pd-axB', 'pd-ax']);
  host.caption('<b>L103</b>: <code>ang_pid_compute = self.ang_pid.pid_compute(abs(minDistID) / 72, 0)</code> — <code>abs()</code> কোণের চিহ্ন ছুড়ে দেয় (দিক পরের branch-এ ফিরবে), target 0 অর্থাৎ সোজা সামনে (L102-এর comment)। <code>/ 72</code>? File কোথাও ব্যাখ্যা করে না — bare magic number, কাজ শুধু কোণকে ছোট সংখ্যায় নামানো। হিসাব (Kp-only view, illustrative — vendor <code>SinglePID</code>-এর ভেতরটা এই folder-এ নেই): 20/72 = 0.278, u ~= 3.0 × 0.278 = <b>0.833</b>।');
  host.formula('ang_pid_compute ~= 3.0 * (abs(+20)/72 - 0) = 3.0 * 0.278 = 0.833   [72 = magic, unexplained]');
  await host.sleep(2100);
  /* --- beat 3: L106-107 left --- */
  show(['pd-hl3', 'pd-br1', 'pd-bnote']);
  host.caption('এবার দিক ফেরানো — <b>L106-107</b>: <code>if 0 &lt; minDistID : velocity.angular.z = ang_pid_compute</code>। Wave B-তে minDistID = +20 (বাঁয়ে), তাই <code>angular.z = +0.833</code> — ROS-এ ধনাত্মক angular.z মানে CCW মানে বাঁয়ে ঘোরা (L105-এর comment-ই বলছে)। Object যেদিকে, মুখ সেদিকে — এটা মুখ মেলানোর হিসাব, এখনও pre-damping।');
  host.formula('0 < minDistID (+20)  ->  angular.z = +u = +0.833  (CCW, left; pre-damping)');
  await host.sleep(1900);
  /* --- beat 4: L109-110 right --- */
  show(['pd-hl4', 'pd-br2', 'pd-bnote2']);
  host.caption('আয়নার শাখা — <b>L109-110</b>: <code>elif minDistID &lt; 0: velocity.angular.z = -ang_pid_compute</code>। Wave D-তে object ডানে: minDist 0.50 m, minDistID = -20 — একই হিসাব, একই 0.833 magnitude, চিহ্ন উল্টো: <code>angular.z = -0.833</code> — ডানে ঘোরা (CW)। PID একবারই চলে; শাখা শুধু চিহ্ন বসায়।');
  host.formula('minDistID < 0 (Wave D: -20, 0.50 m)  ->  angular.z = -u = -0.833  (CW, right)');
  await host.sleep(1900);
  /* --- beat 5: exactly zero --- */
  show(['pd-br3', 'pd-zero']);
  host.caption('আর তৃতীয় কোণা: minDistID ঠিক <b>0.0</b> হলে — object হুবহু সামনে — কোনো branch-ই মেলে না (<code>0 &lt; 0</code> মিথ্যা, <code>0 &lt; 0</code> মিথ্যা)। <code>angular.z</code>-এ কেউ হাত দেয় না, L98-এর <code>Twist()</code>-এর জন্মলগ্ন মান <b>0.0</b>-ই থাকে — ঘোরার নির্দেশ নেই। আর linear.x তো সবসময়ই 0.0।');
  host.formula('minDistID == 0.0  ->  neither branch  ->  angular.z stays 0.0  |  linear.x = 0.0 always');
  await host.sleep(1900);
  /* --- close: ceiling + Kd + boundary of this part --- */
  show(['pd-ctick', 'pd-ceil']);
  host.caption('সীমার হিসাব (illustrative): cone-এর কিনারায় |angle| 45-র দিকে গেলে e ছুঁয়ে আসে 45/72 = 0.625, u ছুঁয়ে আসে 3 × 0.625 = <b>1.875</b> — এটাই কাঁচা ceiling; declared <code>angular</code> 1.0 (L37-38) কোথাও enforce হয় না। এক লাইনের Kd-সতর্কতা: Kd = 5 বেশ বড় — scene বদলে যাওয়ার পর প্রথম call-এ derivative term একটা same-sign transient যোগ করতে পারে (illustrative)। এই anim এখানেই থামে: turn deadzone (|u| &lt; 0.5), ×0.5 damping আর publish — পরের part-এর গল্প।');
  host.formula('ceiling: |a| -> 45-  ->  u -> 3*(45/72) = 1.875  |  declared angular = 1.0 (L37-38) unused  |  next: |u| < 0.5 deadzone + x0.5');
  await host.sleep(2100);
};
