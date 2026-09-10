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

/* ===== folder-13 anim — cmdVelVectors (part 14) =====================
   laser_Warning.py L111-L124, now SPIN-ONLY. Code card: L112 print
   orin_angular.z; L115 deadzone abs(ang_pid_compute) < 0.5 ->
   velocity.angular.z = 0.0 (Kp-view: |a| < 12 deg means NO turn;
   boundary |a| exactly 12 -> u exactly 0.5 -> '< 0.5' False ->
   passes -> z = 0.25); L118 damping x0.5 (comment says 50%, code
   matches; tracker used 0.6); L120 print angular.z; L124 publish.
   L123's comment admits linear.x is never set — Twist default 0.0
   — THE GUARD NEVER DRIVES FORWARD: every vector visual is pure
   rotation (curved arrows around the robot top view), NO forward
   translation arrow, linear.x = 0.0 readout everywhere the tracker
   showed an approach value. Waves (exact, Kp-only, illustrative):
   A 0.90 m @ +14 deg -> u = 3*(14/72) = 0.583 -> passes -> z =
   +0.292 rad/s spin left, beep OFF (0.90 > 0.55, else-branch L95
   published UInt16()); F 0.80 m @ +8 deg -> u = 0.333 < 0.5 ->
   deadzone -> z = 0.0, quiet; C 0.48 m @ 0 deg -> u = 0 ->
   deadzone -> z = 0.0, robot STILL + BEEPING (alarm L89-95 fired
   earlier, 0.48 <= 0.55); D 0.50 m @ -20 deg -> u = 0.833 -> z =
   -0.417 spin right + beeping. Ceiling 3*(45/72)*0.5 = 0.9375
   rad/s; declared angular 1.0 (L38) never enforced. Cadence beat
   kept but updated: empty front (L72-73) = NO publish, last
   command persists AND /beep latches; Joy (L81-83) = zero Twist
   every scan, return BEFORE the alarm block. One scenario beat
   more than folder 12 (four waves vs three). Prefix cv-. No
   emoji, no arrow chars in stage strings, entities for
   &lt; &gt;. */

ANIMS.cmdVelVectors = async function (host) {
  const svg = host.setStage(
    txt(450, 24, 'deadzone যাচাই, ×0.5 damping, তারপর publish — শুধু ঘোরা, এগোনো নেই — L111-L124', { anchor: 'middle', size: 13.5, weight: 600, fill: '#ffb454' }) +
    /* ---------- left: top view (spin only) ---------- */
    rrect(40, 42, 268, 300, 8, '#0d1117', '#2a3442') +
    txt(174, 60, 'TOP VIEW — robot আর object', { anchor: 'middle', size: 9.5, weight: 700, fill: '#e6edf3' }) +
    rrect(116, 66, 116, 16, 3, '#3d1d20', '#f85149', ' fill-opacity="0.25" id="cv-beepB" opacity="0"') +
    txt(174, 77, '/beep: OFF (0.90 &gt; 0.55)', { anchor: 'middle', size: 6.5, mono: true, fill: '#ff7b72', id: 'cv-beep' }) +
    cvWedge(174, 210, 96, -45, 45, 'cv-cone') +
    txt(174, 106, 'cone ±45° (LaserAngle L39)', { anchor: 'middle', size: 7, mono: true, fill: '#8b949e' }) +
    cvWedge(174, 210, 96, -12, 12, 'cv-dz') +
    txt(174, 300, 'deadzone-এর নীরবতা &lt; ±12° (Kp-only, illustrative)', { anchor: 'middle', size: 7, fill: '#6e7681', id: 'cv-dzt', op: 0 }) +
    circ(174, 210, 4, '#ff7b72', ' id="cv-obj" opacity="0"') +
    txt(174, 322, 'Wave A: +14° · 0.90 m', { anchor: 'middle', size: 8.5, weight: 700, mono: true, fill: '#e3b341', id: 'cv-scen' }) +
    rrect(162, 186, 24, 48, 5, '#21262d', '#8b949e') +
    '<path d="M174 176 L180 188 L168 188 Z" fill="#4fc3f7"/>' +
    txt(174, 250, 'robot', { anchor: 'middle', size: 7, fill: '#8b949e' }) +
    cvArcArrow(174, 210, 34, -40, 130, 'cv-tccw', 'cv-tccwh', '#4fc3f7', 2.2) +
    txt(174, 262, 'angular.z CCW', { anchor: 'middle', size: 6.5, fill: '#4fc3f7', id: 'cv-tccwt', op: 0 }) +
    cvArcArrow(174, 210, 34, 40, -130, 'cv-tcw', 'cv-tcwh', '#e3b341', 2.2) +
    txt(174, 274, 'angular.z CW', { anchor: 'middle', size: 6.5, fill: '#e3b341', id: 'cv-tcwt', op: 0 }) +
    txt(174, 337, 'সামনের তীর নেই — linear.x কখনো set হয় না (L123)', { anchor: 'middle', size: 6.5, fill: '#6e7681', id: 'cv-nofwd', op: 0 }) +
    /* ---------- middle: vector dial (spin only) ---------- */
    rrect(318, 42, 172, 300, 8, '#0d1117', '#30363d') +
    txt(404, 60, 'VECTOR DIAL', { anchor: 'middle', size: 9.5, weight: 700, fill: '#e6edf3' }) +
    txt(404, 78, 'linear.x — স্থির শূন্য (m/s)', { anchor: 'middle', size: 7.5, weight: 700, fill: '#c9d1d9' }) +
    '<path d="M404 96 L404 152" stroke="#6e7681" stroke-width="1.5" fill="none"/>' +
    '<path d="M404 86 L409 96 L399 96 Z" fill="#8b949e"/>' +
    '<path d="M404 162 L409 152 L399 152 Z" fill="#8b949e"/>' +
    txt(412, 97, '+ সামনে', { size: 7, fill: '#7ee787' }) +
    txt(412, 153, '- পেছনে', { size: 7, fill: '#ff7b72' }) +
    circ(404, 124, 3, '#8b949e') +
    txt(412, 127, '0.0 — সবসময়', { size: 6.5, fill: '#8b949e' }) +
    rrect(344, 168, 120, 18, 9, '#161b22', '#30363d', ' id="cv-linp"') +
    txt(404, 180.5, 'linear.x = 0.0', { anchor: 'middle', size: 8, mono: true, fill: '#e6edf3', id: 'cv-linv' }) +
    txt(404, 202, 'angular.z — ঘোরার তীর (rad/s)', { anchor: 'middle', size: 7.5, weight: 700, fill: '#c9d1d9' }) +
    circ(404, 244, 26, 'none', ' stroke="#30363d" stroke-width="1.5"') +
    cvArcArrow(404, 244, 26, -35, 175, 'cv-acw', 'cv-acwh', '#4fc3f7', 2.4) +
    cvArcArrow(404, 244, 26, 35, -175, 'cv-aw', 'cv-awh', '#e3b341', 2.4) +
    txt(357, 247, 'CCW +', { anchor: 'end', size: 7, weight: 700, fill: '#4fc3f7' }) +
    txt(451, 247, 'CW -', { size: 7, weight: 700, fill: '#e3b341' }) +
    rrect(339, 282, 130, 20, 10, '#161b22', '#30363d', ' id="cv-angp"') +
    txt(404, 295.5, 'angular.z = +0.583', { anchor: 'middle', size: 8, weight: 700, mono: true, fill: '#e6edf3', id: 'cv-angv' }) +
    txt(404, 320, 'PID-এর ফল এখনো কাঁচা — damping বাকি', { anchor: 'middle', size: 6.5, fill: '#6e7681', id: 'cv-angnote', op: 0 }) +
    txt(404, 332, 'ROS নিয়ম: CCW = ধনাত্মক = বাঁয়ে ঘোরা', { anchor: 'middle', size: 6.5, fill: '#8b949e' }) +
    /* ---------- right: pipeline ---------- */
    rrect(500, 42, 360, 300, 8, '#0d1117', '#2a3442') +
    txt(680, 60, 'PIPELINE — L111-L124', { anchor: 'middle', size: 9.5, weight: 700, fill: '#e6edf3' }) +
    rrect(510, 68, 340, 15, 3, '#21262d', 'none', ' id="cv-hl1" opacity="0"') +
    txt(518, 79, 'print("orin_angular.z: ", velocity.angular.z)', { size: 7.5, mono: true, fill: '#8b949e' }) +
    txt(848, 79, 'L112', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    rrect(510, 84, 340, 15, 3, '#21262d', 'none', ' id="cv-hl2" opacity="0"') +
    txt(518, 95, 'if abs(ang_pid_compute) &lt; 0.5: velocity.angular.z = 0.0', { size: 7.5, mono: true, fill: '#8b949e' }) +
    txt(848, 95, 'L115', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    rrect(510, 100, 340, 15, 3, '#21262d', 'none', ' id="cv-hl3" opacity="0"') +
    txt(518, 111, 'velocity.angular.z = velocity.angular.z * 0.5', { size: 7.5, mono: true, fill: '#8b949e' }) +
    txt(848, 111, 'L118', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    rrect(510, 116, 340, 15, 3, '#21262d', 'none', ' id="cv-hl4" opacity="0"') +
    txt(518, 127, 'print("angular.z: ", velocity.angular.z)', { size: 7.5, mono: true, fill: '#8b949e' }) +
    txt(848, 127, 'L120', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    rrect(510, 132, 340, 15, 3, '#21262d', 'none', ' id="cv-hl5" opacity="0"') +
    txt(518, 143, 'self.pub_vel.publish(velocity)', { size: 7.5, mono: true, fill: '#8b949e' }) +
    txt(848, 143, 'L124', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    rrect(510, 152, 164, 40, 6, '#161b22', '#4fc3f7', ' id="cv-ch1" opacity="0"') +
    txt(592, 165, '1) DEADZONE |u| &lt; 0.5?', { anchor: 'middle', size: 7.5, weight: 700, fill: '#4fc3f7' }) +
    txt(592, 182, 'Wave A: 0.583 - পাস', { anchor: 'middle', size: 7.5, mono: true, fill: '#e6edf3', id: 'cv-ch1t' }) +
    rrect(686, 152, 164, 40, 6, '#161b22', '#e3b341', ' id="cv-ch2" opacity="0"') +
    txt(768, 165, '2) DAMPING ×0.5', { anchor: 'middle', size: 7.5, weight: 700, fill: '#e3b341' }) +
    txt(768, 182, '+0.583 -&gt; +0.292', { anchor: 'middle', size: 7.5, mono: true, fill: '#e6edf3', id: 'cv-ch2t' }) +
    rrect(510, 200, 340, 40, 6, '#161b22', '#7ee787', ' id="cv-ch3" opacity="0"') +
    txt(680, 213, '3) PUBLISH L124 — pub_vel.publish(velocity)', { anchor: 'middle', size: 7.5, weight: 700, fill: '#7ee787' }) +
    txt(680, 230, '/cmd_vel: (0.0, +0.292) — শুধু বাঁয়ে ঘোরা, এগোবে না', { anchor: 'middle', size: 7.5, mono: true, fill: '#e6edf3', id: 'cv-ch3t' }) +
    txt(510, 254, 'ceiling (illustrative): cone-এর কিনারায় |a| প্রায় 45° হলে', { size: 7, fill: '#8b949e', id: 'cv-cnote', op: 0 }) +
    txt(510, 267, 'u প্রায় 1.875, ×0.5 করলে 0.9375 rad/s — declared angular 1.0 (L38) enforce হয় না', { size: 7, fill: '#8b949e', id: 'cv-cnote2', op: 0 }) +
    txt(510, 290, 'L114/L117-এর comment: প্রায় সোজা হলে ঘুরো না, whip around ঠেকাও', { size: 7, fill: '#6e7681', id: 'cv-cnote3', op: 0 }) +
    txt(510, 303, 'সব সংখ্যা Kp-only illustrative — vendor SinglePID এই folder-এ নেই', { size: 7, fill: '#6e7681', id: 'cv-cnote4', op: 0 }) +
    txt(510, 330, '0.5 · 0.5 — দুটোই hard-coded, parameter নয়', { size: 7, fill: '#d2a8ff', id: 'cv-cnote5', op: 0 }) +
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
    rrect(420, 398, 150, 16, 3, '#3d1d20', '#f85149', ' fill-opacity="0.35" stroke-dasharray="4 3" id="cv-none" opacity="0"') +
    txt(495, 426, 'সামনে খালি (L72-73) — publish নেই, /beep আটকে', { anchor: 'middle', size: 7, fill: '#ff7b72', id: 'cv-nonet', op: 0 }) +
    circ(610, 406, 5, '#d2a8ff', ' id="cv-joy" opacity="0"') +
    txt(610, 394, '/JoyState True', { anchor: 'middle', size: 7, mono: true, fill: '#d2a8ff', id: 'cv-joyt', op: 0 }) +
    circ(700, 406, 5, '#7ee787', ' id="cv-zp" opacity="0"') +
    txt(700, 394, 'শূন্য Twist', { anchor: 'middle', size: 7, mono: true, fill: '#7ee787', id: 'cv-zpt', op: 0 }) +
    txt(830, 426, 'publish না এলে চাকা শেষ কমান্ডে · /beep লাইভ থাকে', { anchor: 'end', size: 7, fill: '#8b949e', id: 'cv-lastt', op: 0 }) +
    txt(450, 450, 'source: laser_Warning.py L111-L124 · deadzone L115 · damping L118 · linear.x-নোট L123 · alarm L89-95 · Joy L81-83', { anchor: 'middle', size: 7.5, mono: true, fill: '#6e7681' })
  );
  const q = id => svg.querySelector('#' + id);
  const show = ids => ids.forEach(i => q(i).setAttribute('opacity', 1));
  const hide = ids => ids.forEach(i => q(i).setAttribute('opacity', 0));
  const cvObj = (deg, dist) => {
    const p = cvPt(174, 210, 96 * dist, deg);
    q('cv-obj').setAttribute('cx', p[0]); q('cv-obj').setAttribute('cy', p[1]);
  };

  show(['cv-angnote', 'cv-hl1']);
  host.caption('আগের Part থেমে গিয়েছিল sign branch-এর ঠিক পরে, কাঁচা <code>angular.z</code>-এ (Wave B-তে +0.833, pre-damping)। <b>L112</b> সেই কাঁচা মানটাই console-এ ছাপে (<i>orin</i> = original)। এই Part-এর তিনটা ধাপ সেটাকে চূড়ান্ত করে: deadzone যাচাই, ×0.5 damping, তারপর publish। আর গার্ডের খোদাই-করা সত্য — L123-এর comment নিজেই স্বীকার করে — <code>linear.x</code> কোনোদিন set হয় না: robot শুধু জায়গায় ঘুরে, কখনো এগোয় না। ROS-এ ধনাত্মক <code>angular.z</code> = বাঁয়ে ঘোরা (CCW)।');
  host.formula('final angular.z = (|u| >= 0.5 ? u_signed : 0.0) * 0.5   |   linear.x = 0.0 — never set (L123)');
  cvObj(14, 0.90);
  show(['cv-obj']);
  await host.sleep(1700);
  /* --- beat 1: deadzone pass Wave A --- */
  show(['cv-hl2', 'cv-ch1']);
  host.caption('<b>Wave A (ধরে নিই): object +14°-এ, 0.90 m।</b> <b>L115</b>: <code>abs(ang_pid_compute) &lt; 0.5</code>? হিসাব (Kp-only view, illustrative): u = 3 × 14/72 = <b>0.583</b> — 0.5-এর বেশি, তাই deadzone <b>পাস</b>; <code>angular.z</code> কাটা পড়ে না, 0.583-ই থাকে। (সব pid ফল Kp-only illustrative — vendor <code>SinglePID</code> এই folder-এ নেই।)');
  host.formula('Wave A: u = 3*(14/72) = 0.583 >= 0.5  ->  keep u  (deadzone pass)');
  await host.sleep(1800);
  /* --- beat 2: damping Wave A --- */
  show(['cv-hl3', 'cv-ch2']);
  q('cv-angv').textContent = 'angular.z = +0.292';
  q('cv-angp').setAttribute('stroke', '#4fc3f7');
  q('cv-linp').setAttribute('stroke', '#4fc3f7');
  show(['cv-acw', 'cv-acwh', 'cv-tccw', 'cv-tccwh', 'cv-tccwt', 'cv-nofwd']);
  host.caption('<b>L118</b>: <code>velocity.angular.z = velocity.angular.z * 0.5</code> — comment (L117) বলে 50%, code-ও ঠিক তাই (tracker-টা ছিল ×0.6)। 0.583 × 0.5 = <b>+0.292 rad/s</b>। Dial-এ চূড়ান্ত ছবি: সামনের তীর <b>নেই-ই</b> — <code>linear.x = 0.0</code>, শুধু বাঁয়ে ঘোরার বাঁক, robot জায়গায় দাঁড়িয়ে ঘুরছে।');
  host.formula('Wave A final: angular.z = 0.583 * 0.5 = +0.292 rad/s  |  linear.x = 0.0 m/s (never set)');
  await host.sleep(2000);
  /* --- beat 3: publish Wave A --- */
  show(['cv-hl4', 'cv-hl5', 'cv-ch3', 'cv-beepB', 'cv-beep']);
  host.caption('<b>L120</b> console-এ চূড়ান্ত মান ছাপে, <b>L124</b> <code>self.pub_vel.publish(velocity)</code> — একটাই <code>Twist</code>, <code>/cmd_vel</code>-এ (L30-এর publisher)। Alarm-ও একই scan-এ আগেই হিসাব হয়ে গেছে (L89-95): 0.90 &gt; 0.55, তাই else-branch <code>/beep</code>-এ 0 পাঠিয়েছে (L95) — নীরবে ঘোরা। এই মুহূর্ত থেকে পরের scan না আসা পর্যন্ত চাকা এই কমান্ডই মানবে।');
  host.formula('publish (linear.x = 0.0, angular.z = +0.292) -> /cmd_vel  |  /beep 0 (0.90 > 0.55, L95)');
  await host.sleep(2000);
  /* --- beat 4: Wave F deadzone kill + boundary --- */
  q('cv-scen').textContent = 'Wave F: +8° · 0.80 m';
  q('cv-ch1t').textContent = 'Wave F: 0.333 - কাটা পড়ল';
  q('cv-ch1').setAttribute('stroke', '#f85149');
  q('cv-ch2t').textContent = '0.0 × 0.5 = 0.0';
  q('cv-angv').textContent = 'angular.z = 0.0';
  q('cv-beep').textContent = '/beep: OFF (0.80 > 0.55)';
  cvObj(8, 0.80);
  hide(['cv-acw', 'cv-acwh', 'cv-tccw', 'cv-tccwh', 'cv-tccwt']);
  show(['cv-dzt']);
  q('cv-ch3t').textContent = '/cmd_vel: (0.0, 0.0) — দাঁড়িয়ে, চুপ';
  host.caption('এবার <b>Wave F</b>: object +8°-এ, 0.80 m। u = 3 × 8/72 = <b>0.333</b> — 0.5 ছোঁয়নি, তাই <b>L115-এর deadzone কাটা দেয়</b>: <code>angular.z = 0.0</code>। Kp-only view-এ এই সীমা কার্যত <b>|angle| &lt; 12°</b> (3·a/72 &lt; 0.5; illustrative) — tracker-এর 18°-র চেয়ে চেটে। সীমানার ঠিক ওপরে |a| = 12° হলে u ঠিক 0.5 — <code>&lt; 0.5</code> মিথ্যা, তাই মানটা বাঁচে: z = 0.25। আর 0.80 &gt; 0.55 — zone-এর বাইরে, else-branch <code>/beep</code> 0: চুপচাপ দাঁড়িয়ে।');
  host.formula('Wave F: u = 3*8/72 = 0.333 < 0.5  ->  angular.z = 0.0  |  boundary |a| = 12 -> u = 0.5 -> passes -> z = 0.25');
  await host.sleep(2300);
  /* --- beat 5: ceiling --- */
  show(['cv-cnote', 'cv-cnote2', 'cv-cnote3', 'cv-cnote4', 'cv-cnote5']);
  host.caption('দুই ধাপের সীমাহিসাব: damping না থাকলে cone-এর কিনারায় (|angle| প্রায় 45°) কাঁচা u প্রায় <b>1.875</b>-এ উঠত — ×0.5 করে বাস্তব ceiling <b>0.9375 rad/s</b> (illustrative)। খেয়াল করো: declared <code>angular</code> parameter 1.0 (L38) কোথাও enforce হয় না — সীমা দুটো এসেছে deadzone (0.5) আর damping (0.5) থেকে, দুটোই hard-coded সংখ্যা।');
  host.formula('ceiling: u_max = 3 * (45/72) = 1.875 ; 1.875 * 0.5 = 0.9375 rad/s  |  declared angular = 1.0 (L38) unused');
  await host.sleep(2200);
  /* --- beat 6: Wave C still + beeping --- */
  q('cv-scen').textContent = 'Wave C: 0° · 0.48 m — দাঁড়িয়ে + বিঁপ';
  q('cv-ch1t').textContent = 'Wave C: u = 0 — শূন্যই';
  q('cv-ch1').setAttribute('stroke', '#4fc3f7');
  q('cv-ch2t').textContent = '0.0 × 0.5 = 0.0';
  q('cv-angv').textContent = 'angular.z = 0.0';
  q('cv-beep').textContent = '/beep: ON (0.48 <= 0.55)';
  cvObj(0, 0.48);
  q('cv-ch3t').textContent = '/cmd_vel: (0.0, 0.0) — দাঁড়িয়ে থাকা + বিঁপ';
  host.caption('<b>Wave C</b>: object হুবহু সামনে, 0.48 m — Danger zone-এর ভেতরে। কোণ 0 বলে u = 0, deadzone-ও তাকে 0.0-ই রাখে: <code>angular.z = 0.0</code>। কিন্তু হিসাবের আগেই alarm block (L89-95) চলে গেছে: 0.48 &lt;= 0.55 — <code>/beep</code>-এ 1 (L90-92)। robot দাঁড়িয়ে আছে, বিঁপ বাজছে — গার্ডের "একদম কাছে" ভঙ্গি: এগোয় না, পালায় না, শুধু সতর্ক করে।');
  host.formula('Wave C: u = 0 -> angular.z = 0.0  |  0.48 <= 0.55 -> /beep 1 (L89-92) — still + beeping');
  await host.sleep(2300);
  /* --- beat 7: Wave D spin right + beeping --- */
  q('cv-scen').textContent = 'Wave D: -20° · 0.50 m — ঘুরছে + বিঁপ';
  q('cv-ch1t').textContent = 'Wave D: 0.833 - পাস';
  q('cv-ch2t').textContent = '-0.833 -> -0.417';
  q('cv-angv').textContent = 'angular.z = -0.417';
  q('cv-angp').setAttribute('stroke', '#e3b341');
  q('cv-beep').textContent = '/beep: ON (0.50 <= 0.55)';
  cvObj(-20, 0.50);
  show(['cv-aw', 'cv-awh', 'cv-tcw', 'cv-tcwh', 'cv-tcwt', 'cv-nofwd']);
  q('cv-ch3t').textContent = '/cmd_vel: (0.0, -0.417) — ডানে ঘোরা + বিঁপ';
  host.caption('<b>Wave D</b>: object ডানে, -20°, 0.50 m — একই ভাবে zone-এর ভেতরে। u = 3 × 20/72 = <b>0.833</b> — deadzone পাস; sign branch চিহ্নটা উল্টে দিয়েছিল (আগের Part), ×0.5 করে <b>-0.417 rad/s</b>: ডানে ঘোরা (CW), বিঁপ সহ। মানে zone-এ ঢুকলেও মুখ মেলানো থেমে নেই — গার্ড ঘুরতে ঘুরতেই সতর্ক করে, আর কখনো এগোয় না।');
  host.formula('Wave D: u = 3*(20/72) = 0.833 -> z = 0.833*0.5 = -0.417 rad/s (CW, right)  |  /beep 1 (0.50 <= 0.55)');
  await host.sleep(2300);
  /* --- beat 8: cadence --- */
  show(['cv-p1', 'cv-p1t', 'cv-s2', 'cv-s2t', 'cv-p2', 'cv-p2t', 'cv-none', 'cv-nonet', 'cv-joy', 'cv-joyt', 'cv-zp', 'cv-zpt', 'cv-lastt']);
  host.caption('ছন্দটা মনে রাখো: <b>প্রতি scan-এ এক publish</b> — compute শেষ হলেই L124 চলে (timeline illustrative)। সামনে valid কিছু না থাকলে L72-73-এর <code>return</code>-এ publish-ই হয় না — চাকা তখন <b>শেষ কমান্ডেই</b> চলে, আর <code>/beep</code> তার শেষ মানে আটকে থাকে (লেখেও না, মুছেও না)। <code>/JoyState</code> True হলে L81-83 প্রতি scan-এ শূন্য <code>Twist()</code> ঠেলে alarm block-এর <b>আগেই</b> return করে — /beep তখনও refresh হয় না: মানুষের brake।');
  host.formula('scan -> compute -> publish  |  empty front (L72-73): no publish, last cmd persists, /beep latches  |  Joy (L81-83): zero Twist, return before alarm');
  await host.sleep(2200);
  host.caption('মোদ্দা কথা: 12°-র বেশি বাঁকে ঘুরে যায় (A: +0.292), সামান্য বাঁকে চুপ (F), zone-এ ঢুকলে বিঁপ — সোজা সামনে হলে দাঁড়িয়ে (C), বাঁকানো হলে ঘুরতে ঘুরতে (D) — আর প্রতিটা ক্ষেত্রেই <code>linear.x = 0.0</code>: গার্ড কখনো এগোয় না। এরপর আর কোনো হিসাব নেই — শুধু বন্ধ হওয়ার পালা: <code>exit_pro</code> আর <code>main()</code>, শেষ Part-এর গল্প।');
  await host.sleep(1800);
};
