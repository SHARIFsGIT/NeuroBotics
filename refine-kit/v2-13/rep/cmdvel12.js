/* ---------- cmdVelVectors ---------- */

function cvPt(cx, cy, r, deg) {
  const t = deg * Math.PI / 180;
  return [cx - r * Math.sin(t), cy - r * Math.cos(t)];
}
function cvN(n) { return n.toFixed(1); }
/* pie-slice wedge, dim at birth, mutated per beat */
function cvWedge(cx, cy, r, a0, a1, id) {
  const p0 = cvPt(cx, cy, r, a0), p1 = cvPt(cx, cy, r, a1);
  return '<path id="' + id + '" d="M' + cx + ' ' + cy + ' L' + cvN(p0[0]) + ' ' + cvN(p0[1]) +
    ' A' + r + ' ' + r + ' 0 0 0 ' + cvN(p1[0]) + ' ' + cvN(p1[1]) +
    ' Z" fill="#8b949e" fill-opacity="0.07" stroke="#6e7681" stroke-width="1.2" opacity="0.5"/>';
}
/* curved arrow (arc + head), opacity 0 at birth */
function cvArcArrow(cx, cy, r, a0, a1, idA, idH, stroke, wpx, extra) {
  const p0 = cvPt(cx, cy, r, a0), p1 = cvPt(cx, cy, r, a1);
  const ccw = a1 > a0;
  const t1 = a1 * Math.PI / 180;
  let ux = -Math.cos(t1), uy = Math.sin(t1);
  if (!ccw) { ux = -ux; uy = -uy; }
  const tip = [p1[0] + ux * 8, p1[1] + uy * 8];
  const b1 = [p1[0] - uy * 4.2, p1[1] + ux * 4.2];
  const b2 = [p1[0] + uy * 4.2, p1[1] - ux * 4.2];
  const large = Math.abs(a1 - a0) > 180 ? 1 : 0;
  const sweep = ccw ? 0 : 1;
  return '<path id="' + idA + '" d="M' + cvN(p0[0]) + ' ' + cvN(p0[1]) +
    ' A' + r + ' ' + r + ' 0 ' + large + ' ' + sweep + ' ' + cvN(p1[0]) + ' ' + cvN(p1[1]) +
    '" fill="none" stroke="' + stroke + '" stroke-width="' + wpx + '" ' + (extra || 'opacity="0"') + '/>' +
    '<path id="' + idH + '" d="M' + cvN(tip[0]) + ' ' + cvN(tip[1]) + ' L' + cvN(b1[0]) + ' ' + cvN(b1[1]) +
    ' L' + cvN(b2[0]) + ' ' + cvN(b2[1]) + ' Z" fill="' + stroke + '" opacity="0"/>';
}

/* ===== folder-12 v1 anim — cmdVelVectors (part 14) ===================
   laser_Tracker.py L115-L125: turn deadzone (|ang_pid_compute| < 0.5
   -> angular.z = 0.0), x0.6 damping (whip-around comment L119), print
   L122, publish L125. Scenarios (illustrative, Kp-only): Wave B
   +20 deg / 0.70 m -> u = 0.556 >= 0.5 pass -> x0.6 -> +0.333 rad/s
   CCW with linear.x +0.15; Wave A +12 deg / 0.90 m -> u = 0.333 <
   0.5 -> z = 0.0, straight only (|angle| < 18 deg equivalent); Wave C
   dead ahead 0.55 m -> L96 snap -> both zero, locked stand-off.
   Ceiling 2*0.625*0.6 = 0.75 rad/s; declared angular 1.0 (L35) never
   enforced. Motors keep the last command (no publish on the empty
   L80-83 and Joy L86-88 paths). Prefix cv-. No emoji, no arrow chars
   in stage strings, entities for &lt; &gt;. */

ANIMS.cmdVelVectors = async function (host) {
  const svg = host.setStage(
    txt(450, 24, 'deadzone যাচাই, ×0.6 damping, তারপর publish — চূড়ান্ত Twist-এর জন্ম, L116-L125', { anchor: 'middle', size: 13.5, weight: 600, fill: '#ffb454' }) +
    /* ---------- left: top view ---------- */
    rrect(40, 42, 268, 300, 8, '#0d1117', '#2a3442') +
    txt(174, 60, 'TOP VIEW — robot আর object', { anchor: 'middle', size: 9.5, weight: 700, fill: '#e6edf3' }) +
    cvWedge(174, 210, 96, -45, 45, 'cv-cone') +
    txt(174, 106, 'cone ±45° (L36)', { anchor: 'middle', size: 7, mono: true, fill: '#8b949e' }) +
    cvWedge(174, 210, 96, -18, 18, 'cv-dz') +
    txt(174, 300, 'deadzone-এর নীরবতা &lt; ±18° (Kp-only, illustrative)', { anchor: 'middle', size: 7, fill: '#6e7681', id: 'cv-dzt', op: 0 }) +
    circ(174, 210, 4, '#ff7b72', ' id="cv-obj" opacity="0"') +
    txt(174, 322, 'Wave B: +20° · 0.70 m', { anchor: 'middle', size: 8.5, weight: 700, mono: true, fill: '#e3b341', id: 'cv-scen' }) +
    rrect(162, 186, 24, 48, 5, '#21262d', '#8b949e') +
    '<path d="M174 176 L180 188 L168 188 Z" fill="#4fc3f7"/>' +
    txt(174, 250, 'robot', { anchor: 'middle', size: 7, fill: '#8b949e' }) +
    '<path d="M174 172L174 148" stroke="#7ee787" stroke-width="2.4" fill="none" id="cv-fwd" opacity="0"/>' +
    '<path d="M174 148 L179 158 L169 158 Z" fill="#7ee787" id="cv-fwdh" opacity="0"/>' +
    txt(182, 154, 'linear.x', { size: 6.5, fill: '#7ee787', id: 'cv-fwdt', op: 0 }) +
    cvArcArrow(174, 210, 34, -40, 130, 'cv-tccw', 'cv-tccwh', '#4fc3f7', 2.2) +
    txt(174, 266, 'angular.z CCW', { anchor: 'middle', size: 6.5, fill: '#4fc3f7', id: 'cv-tccwt', op: 0 }) +
    /* ---------- middle: vector dial ---------- */
    rrect(318, 42, 172, 300, 8, '#0d1117', '#30363d') +
    txt(404, 60, 'VECTOR DIAL', { anchor: 'middle', size: 9.5, weight: 700, fill: '#e6edf3' }) +
    txt(404, 78, 'linear.x — সোজা তীর (m/s)', { anchor: 'middle', size: 7.5, weight: 700, fill: '#c9d1d9' }) +
    '<path d="M404 96 L404 152" stroke="#6e7681" stroke-width="1.5" fill="none"/>' +
    '<path d="M404 86 L409 96 L399 96 Z" fill="#8b949e"/>' +
    '<path d="M404 162 L409 152 L399 152 Z" fill="#8b949e"/>' +
    txt(412, 97, '+ সামনে', { size: 7, fill: '#7ee787' }) +
    txt(412, 153, '- পেছনে', { size: 7, fill: '#ff7b72' }) +
    '<path d="M404 148 L404 112" stroke="#7ee787" stroke-width="2.4" opacity="0.14" fill="none"/>' +
    rrect(344, 168, 120, 18, 9, '#161b22', '#30363d', ' id="cv-linp"') +
    txt(404, 180.5, 'linear.x = +0.15', { anchor: 'middle', size: 8, mono: true, fill: '#e6edf3', id: 'cv-linv' }) +
    txt(404, 202, 'angular.z — বাঁকা তীর (rad/s)', { anchor: 'middle', size: 7.5, weight: 700, fill: '#c9d1d9' }) +
    circ(404, 244, 26, 'none', ' stroke="#30363d" stroke-width="1.5"') +
    cvArcArrow(404, 244, 26, -35, 175, 'cv-acw', 'cv-acwh', '#4fc3f7', 2.4) +
    cvArcArrow(404, 244, 26, 35, -175, 'cv-aw', 'cv-awh', '#e3b341', 2.4) +
    txt(357, 247, 'CCW +', { anchor: 'end', size: 7, weight: 700, fill: '#4fc3f7' }) +
    txt(451, 247, 'CW -', { size: 7, weight: 700, fill: '#e3b341' }) +
    rrect(339, 282, 130, 20, 10, '#161b22', '#30363d', ' id="cv-angp"') +
    txt(404, 295.5, 'angular.z = +0.556', { anchor: 'middle', size: 8, weight: 700, mono: true, fill: '#e6edf3', id: 'cv-angv' }) +
    txt(404, 320, 'PID-এর ফল এখনো কাঁচা — damping বাকি', { anchor: 'middle', size: 6.5, fill: '#6e7681', id: 'cv-angnote', op: 0 }) +
    txt(404, 332, 'ROS নিয়ম: CCW = ধনাত্মক = বাঁয়ে ঘোরা', { anchor: 'middle', size: 6.5, fill: '#8b949e' }) +
    /* ---------- right: pipeline ---------- */
    rrect(500, 42, 360, 300, 8, '#0d1117', '#2a3442') +
    txt(680, 60, 'PIPELINE — L116-L125', { anchor: 'middle', size: 9.5, weight: 700, fill: '#e6edf3' }) +
    rrect(510, 68, 340, 15, 3, '#21262d', 'none', ' id="cv-hl1" opacity="0"') +
    txt(518, 79, 'if abs(ang_pid_compute) &lt; 0.5: velocity.angular.z = 0.0', { size: 7.5, mono: true, fill: '#8b949e' }) +
    txt(848, 79, 'L117', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    rrect(510, 84, 340, 15, 3, '#21262d', 'none', ' id="cv-hl2" opacity="0"') +
    txt(518, 95, 'velocity.angular.z = velocity.angular.z * 0.6', { size: 7.5, mono: true, fill: '#8b949e' }) +
    txt(848, 95, 'L120', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    rrect(510, 100, 340, 15, 3, '#21262d', 'none', ' id="cv-hl3" opacity="0"') +
    txt(518, 111, 'print("angular.z: ", velocity.angular.z)', { size: 7.5, mono: true, fill: '#8b949e' }) +
    txt(848, 111, 'L122', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    rrect(510, 116, 340, 15, 3, '#21262d', 'none', ' id="cv-hl4" opacity="0"') +
    txt(518, 127, 'self.pub_vel.publish(velocity)', { size: 7.5, mono: true, fill: '#8b949e' }) +
    txt(848, 127, 'L125', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    rrect(510, 142, 164, 40, 6, '#161b22', '#4fc3f7', ' id="cv-ch1" opacity="0"') +
    txt(592, 155, '1) DEADZONE |u| &lt; 0.5?', { anchor: 'middle', size: 7.5, weight: 700, fill: '#4fc3f7' }) +
    txt(592, 172, 'Wave B: 0.556 - পাস', { anchor: 'middle', size: 7.5, mono: true, fill: '#e6edf3', id: 'cv-ch1t' }) +
    rrect(686, 142, 164, 40, 6, '#161b22', '#e3b341', ' id="cv-ch2" opacity="0"') +
    txt(768, 155, '2) DAMPING ×0.6', { anchor: 'middle', size: 7.5, weight: 700, fill: '#e3b341' }) +
    txt(768, 172, '+0.556 -&gt; +0.333', { anchor: 'middle', size: 7.5, mono: true, fill: '#e6edf3', id: 'cv-ch2t' }) +
    rrect(510, 190, 340, 40, 6, '#161b22', '#7ee787', ' id="cv-ch3" opacity="0"') +
    txt(680, 203, '3) PUBLISH L125 — pub_vel.publish(velocity)', { anchor: 'middle', size: 7.5, weight: 700, fill: '#7ee787' }) +
    txt(680, 220, '/cmd_vel: (+0.15, +0.333) — চাকা পরের scan পর্যন্ত এটাই ধরে রাখে', { anchor: 'middle', size: 7.5, mono: true, fill: '#e6edf3', id: 'cv-ch3t' }) +
    txt(510, 248, 'ceiling (illustrative): cone-এর কিনারায় |a| প্রায় 45° হলে', { size: 7, fill: '#8b949e', id: 'cv-cnote', op: 0 }) +
    txt(510, 261, 'u প্রায় 1.25, ×0.6 করলে 0.75 rad/s — declared angular 1.0 (L35) কোথাও enforce হয় না', { size: 7, fill: '#8b949e', id: 'cv-cnote2', op: 0 }) +
    txt(510, 284, 'L116/L119-এর comment: সামান্য বাঁক চুপ, whip around ঠেকাও', { size: 7, fill: '#6e7681', id: 'cv-cnote3', op: 0 }) +
    txt(510, 297, 'সব সংখ্যা Kp-only illustrative — vendor SinglePID এই folder-এ নেই', { size: 7, fill: '#6e7681', id: 'cv-cnote4', op: 0 }) +
    txt(510, 326, '0.5 · 0.6 — দুটোই hard-coded, parameter নয়', { size: 7, fill: '#d2a8ff', id: 'cv-cnote5', op: 0 }) +
    /* ---------- bottom: publish cadence ---------- */
    rrect(40, 352, 820, 84, 8, '#111', '#30363d') +
    txt(60, 370, 'PUBLISH CADENCE — প্রতি scan-এ এক publish (illustrative)', { size: 9, weight: 700, fill: '#e6edf3' }) +
    '<path d="M70 406 L830 406" stroke="#30363d" stroke-width="2" fill="none"/>' +
    txt(830, 394, 'সময় -&gt;', { anchor: 'end', size: 7, fill: '#6e7681' }) +
    circ(96, 406, 5, '#4fc3f7') +
    txt(96, 394, '/scan', { anchor: 'middle', size: 7, mono: true, fill: '#4fc3f7' }) +
    circ(170, 406, 5, '#7ee787', ' id="cv-p1" opacity="0"') +
    txt(170, 394, 'publish', { anchor: 'middle', size: 7, mono: true, fill: '#7ee787', id: 'cv-p1t', op: 0 }) +
    circ(280, 406, 5, '#4fc3f7', ' id="cv-s2" opacity="0"') +
    txt(280, 394, '/scan', { anchor: 'middle', size: 7, mono: true, fill: '#4fc3f7', id: 'cv-s2t', op: 0 }) +
    circ(354, 406, 5, '#7ee787', ' id="cv-p2" opacity="0"') +
    txt(354, 394, 'publish', { anchor: 'middle', size: 7, mono: true, fill: '#7ee787', id: 'cv-p2t', op: 0 }) +
    rrect(420, 398, 130, 16, 3, '#3d1d20', '#f85149', ' fill-opacity="0.35" stroke-dasharray="4 3" id="cv-none" opacity="0"') +
    txt(485, 426, 'সামনে খালি (L80-83) — publish নেই', { anchor: 'middle', size: 7, fill: '#ff7b72', id: 'cv-nonet', op: 0 }) +
    circ(610, 406, 5, '#d2a8ff', ' id="cv-joy" opacity="0"') +
    txt(610, 394, '/JoyState True', { anchor: 'middle', size: 7, mono: true, fill: '#d2a8ff', id: 'cv-joyt', op: 0 }) +
    circ(700, 406, 5, '#7ee787', ' id="cv-zp" opacity="0"') +
    txt(700, 394, 'শূন্য Twist', { anchor: 'middle', size: 7, mono: true, fill: '#7ee787', id: 'cv-zpt', op: 0 }) +
    txt(830, 426, 'publish না এলে চাকা শেষ কমান্ডেই চলে', { anchor: 'end', size: 7, fill: '#8b949e', id: 'cv-lastt', op: 0 }) +
    txt(450, 450, 'source: laser_Tracker.py L115-L125 · linear PID L102 · angular PID L107 · snap L96 · Joy gate L86-88', { anchor: 'middle', size: 7.5, mono: true, fill: '#6e7681' })
  );
  const q = id => svg.querySelector('#' + id);
  const show = ids => ids.forEach(i => q(i).setAttribute('opacity', 1));
  const hide = ids => ids.forEach(i => q(i).setAttribute('opacity', 0));
  const cvObj = (deg, dist) => {
    const p = cvPt(174, 210, 96 * dist, deg);
    q('cv-obj').setAttribute('cx', p[0]); q('cv-obj').setAttribute('cy', p[1]);
  };

  show(['cv-angnote']);
  host.caption('Part 13-এর শেষে Twist-এর দুই ঘর বসেছিল (illustrative): <code>linear.x = +0.15</code>, <code>angular.z = +0.556</code>। এই Part-এর তিনটা নিয়ম সেই কাঁচা মানটাকে বাজারে পাঠানোর আগে গুছিয়ে নেয় — deadzone যাচাই, ×0.6 damping, তারপর publish। ROS-এ ধনাত্মক <code>angular.z</code> = বাঁয়ে ঘোরা (CCW)।');
  host.formula('final angular.z = (|u| >= 0.5 ? u_signed : 0.0) * 0.6   |   publish linear.x + angular.z at L125');
  cvObj(20, 0.70);
  show(['cv-obj']);
  await host.sleep(1700);
  /* --- beat 1: deadzone pass Wave B --- */
  show(['cv-hl1', 'cv-ch1']);
  host.caption('<b>Wave B (ধরে নিই): object +20°-এ, 0.70 m।</b> <b>L117</b>: <code>abs(ang_pid_compute) &lt; 0.5</code>? হিসাব: 0.556 — 0.5-এর বেশি, তাই deadzone <b>পাস</b>; <code>angular.z</code> কাটা পড়ে না, 0.556-ই থাকে। (সব pid ফল Kp-only illustrative — vendor <code>SinglePID</code> এই folder-এ নেই।)');
  host.formula('Wave B: |0.556| >= 0.5  ->  keep u  (deadzone pass)');
  await host.sleep(1800);
  /* --- beat 2: damping Wave B --- */
  show(['cv-hl2', 'cv-ch2']);
  q('cv-angv').textContent = 'angular.z = +0.333';
  q('cv-angp').setAttribute('stroke', '#4fc3f7');
  q('cv-linp').setAttribute('stroke', '#4fc3f7');
  show(['cv-acw', 'cv-acwh', 'cv-tccw', 'cv-tccwh', 'cv-tccwt', 'cv-fwd', 'cv-fwdh', 'cv-fwdt']);
  host.caption('<b>L120</b>: <code>velocity.angular.z = velocity.angular.z * 0.6</code> — সর্বজনীন 60% স্কেল, comment (L119) বলে robot যেন <i>whip around</i> না করে। 0.556 × 0.6 = <b>+0.333 rad/s</b>। Dial-এ এখন চূড়ান্ত ছবি: সামনে তীর (+0.15 m/s) + বাঁয়ে বাঁক (+0.333) — object-এর দিকে বেঁকে এগোনো।');
  host.formula('Wave B final: angular.z = 0.556 * 0.6 = +0.333 rad/s  |  linear.x = +0.15 m/s');
  await host.sleep(2000);
  /* --- beat 3: publish Wave B --- */
  show(['cv-hl3', 'cv-hl4', 'cv-ch3']);
  host.caption('<b>L122</b> console-এ চূড়ান্ত মান ছাপে, <b>L125</b> <code>self.pub_vel.publish(velocity)</code> — একটাই <code>Twist</code>, <code>/cmd_vel</code>-এ (L29-এর publisher)। এই মুহূর্ত থেকে পরের scan না আসা পর্যন্ত চাকা এই কমান্ডই মানবে।');
  host.formula('publish (linear.x = +0.15, angular.z = +0.333) -> /cmd_vel -> wheels hold it until next scan');
  await host.sleep(2000);
  /* --- beat 4: Wave A deadzone kill --- */
  q('cv-scen').textContent = 'Wave A: +12° · 0.90 m';
  q('cv-ch1t').textContent = 'Wave A: 0.333 - কাটা পড়ল';
  q('cv-ch1').setAttribute('stroke', '#f85149');
  q('cv-ch2t').textContent = '0.0 × 0.6 = 0.0';
  q('cv-angv').textContent = 'angular.z = 0.0';
  q('cv-linv').textContent = 'linear.x = +0.35';
  cvObj(12, 0.90);
  hide(['cv-acw', 'cv-acwh', 'cv-tccw', 'cv-tccwh', 'cv-tccwt']);
  show(['cv-dzt']);
  q('cv-ch3t').textContent = '/cmd_vel: (+0.35, 0.0) — সোজা এগোও, ঘুরো না';
  host.caption('এবার <b>Wave A</b>: object +12°-এ, 0.90 m। angular PID দিয়েছে 2 × 12/72 = <b>0.333</b> — সেটা 0.5-এর কাছে পৌঁছায়নি, তাই <b>L117-এর deadzone কাটা দেয়</b>: <code>angular.z = 0.0</code>। Kp-only view-এ এই সীমা কার্যত <b>|angle| &lt; 18°</b> (2·a/72 &lt; 0.5; illustrative) — ওই নীরব পাল্লার ভেতরে robot ঘুরবেই না, শুধু সোজা এগোবে (+0.35 m/s; দূরত্ব বেশি, তাই গতিও বেশি — clamp নেই)।');
  host.formula('Wave A: u = 2*12/72 = 0.333 < 0.5  ->  angular.z = 0.0 ; linear.x = -1*(0.55-0.90) = +0.35');
  await host.sleep(2300);
  /* --- beat 5: ceiling --- */
  show(['cv-cnote', 'cv-cnote2', 'cv-cnote3', 'cv-cnote4', 'cv-cnote5']);
  host.caption('দুই ধাপের সীমাহিসাব: damping না থাকলে cone-এর কিনারায় (|angle| প্রায় 45°) কাঁচা u প্রায় <b>1.25 rad/s</b>-এ উঠত — ×0.6 করে বাস্তব ceiling <b>0.75 rad/s</b> (illustrative)। খেয়াল করো: declared <code>angular</code> parameter 1.0 (L35) কোথাও enforce হয় না — সীমা দুটো এসেছে deadzone (0.5) আর damping (0.6) থেকে, দুটোই hard-coded সংখ্যা।');
  host.formula('ceiling: u_max ~= 2 * (45/72) = 1.25 ; 1.25 * 0.6 = 0.75 rad/s  |  declared angular = 1.0 unused');
  await host.sleep(2200);
  /* --- beat 6: Wave C locked --- */
  q('cv-scen').textContent = 'Wave C: 0° · 0.55 m — stand-off';
  q('cv-ch1t').textContent = 'Wave C: 0.0 - নির্বিঘ্ন';
  q('cv-ch1').setAttribute('stroke', '#4fc3f7');
  q('cv-ch2t').textContent = '0.0 × 0.6 = 0.0';
  q('cv-angv').textContent = 'angular.z = 0.0';
  q('cv-linv').textContent = 'linear.x = 0.0';
  cvObj(0, 0.55);
  q('cv-ch3t').textContent = '/cmd_vel: (0.0, 0.0) — দাঁড়িয়ে থাকা stand-off';
  host.caption('<b>Wave C</b>: object হুবহু সামনে, 0.55 m। L96-এর snap (Part 12) minDist-কে 0.55-ই ধরেছে — linear PID-এর error শূন্য, <code>linear.x = 0.0</code>; কোণ 0 বলে sign branch-ও না (Part 13), তাই <code>angular.z = 0.0</code>। Publish হয় <b>(0.0, 0.0)</b> — robot জায়গায় দাঁড়িয়ে object-কে 0.55 m দূরত্বে আটকে রাখে: এটাই tracking-এর stand-off।');
  host.formula('Wave C: snap -> e = 0 -> linear.x = 0 ; angle = 0 -> no branch -> angular.z = 0  -> (0.0, 0.0)');
  await host.sleep(2300);
  /* --- beat 7: cadence --- */
  show(['cv-p1', 'cv-p1t', 'cv-s2', 'cv-s2t', 'cv-p2', 'cv-p2t', 'cv-none', 'cv-nonet', 'cv-joy', 'cv-joyt', 'cv-zp', 'cv-zpt', 'cv-lastt']);
  host.caption('ছন্দটা মনে রাখো: <b>প্রতি scan-এ এক publish</b> — compute শেষ হলেই L125 চলে (timeline illustrative)। সামনে কিছু না থাকলে L80-83-এর <code>return</code>-এ publish-ই হয় না — চাকা তখন <b>শেষ কমান্ডেই</b> চলতে থাকে; আর <code>/JoyState</code> True হলে L86-88 প্রতি scan-এ শূন্য <code>Twist()</code> ঠেলে দেয় — মানুষের brake।');
  host.formula('scan -> compute -> publish  |  empty front (L80-83): no publish, last command persists  |  Joy (L86-88): zero Twist');
  await host.sleep(2200);
  host.caption('তিনটা Wave-এর মোদ্দা কথা: 18°-র বেশি বাঁকে ঘুরে সামনে এগোয় (B), সামান্য বাঁক উপেক্ষা করে সোজা ছোটে (A), আর 0.55 m-এ গিয়ে থামে (C) — damping সব ঘোরাকে মার্জিত রাখে। এরপর আর কোনো হিসাব নেই: শুধু বন্ধ হওয়ার পালা — <code>exit_pro</code> আর <code>main()</code>, শেষ Part-এর গল্প।');
  await host.sleep(1800);
};
