/* ---------- beamSweep ---------- */
/* ============ folder-12 v1 anim — beamSweep (part 10) ================
   laser_Tracker.py registerScan beam loop, L56-L72. Stage: top-down
   fused 360 ring (folder 10 merger+filter -> /scan), deg 0 up, +deg
   LEFT (ROS ccw). Beats: L56 def + L57 guard, L58 ranges np.array,
   L61-62 two empty parallel lists, L65 cursor sweep i=0.., L67
   rad->deg formula (i=192 -> +12 deg), L70 front cone gate
   abs(angle) < LaserAngle (45.0, L36) strict -> 89 beams i=136..224,
   ranges[i] !=0.0 skips no-return zeros but passes inf, L71-72
   parallel appends. Wave-B object 0.70 m @ +20 deg, second 0.90 m @
   -10 deg; min() preview belongs to next part. Ring ranges
   illustrative. Prefix bs-. No emoji, no arrow chars in stage
   strings, entities for &lt; &gt;. */

/* --- prefixed polar helpers (deg: 0 = up, +deg = screen left) --- */
function bsBeam(deg) {
  const a = (deg + 180) % 360 - 180;
  if (Math.abs(a) < 45) {                              /* front cone */
    if (Math.abs(a - 20) <= 3) return 0.70;            /* tracked object */
    if (Math.abs(a + 10) <= 3) return 0.90;            /* second object */
    return 1.05;
  }
  if (deg > 55 && deg < 80) return 0.0;                /* no-return band */
  if (deg < -55 && deg > -80) return 0.0;              /* no-return band */
  return 1.25 + 0.07 * Math.sin(5 * a * Math.PI / 180); /* rear ring */
}
function bsXY(cx, cy, pxm, deg, r) {
  const th = deg * Math.PI / 180;
  return [cx - r * pxm * Math.sin(th), cy - r * pxm * Math.cos(th)];
}
function bsArcD(cx, cy, r, a0, a1) {
  const p0 = bsXY(cx, cy, 1, a0, r), p1 = bsXY(cx, cy, 1, a1, r);
  return 'M' + p0[0].toFixed(1) + ' ' + p0[1].toFixed(1) +
         'A' + r + ' ' + r + ' 0 0 0 ' + p1[0].toFixed(1) + ' ' + p1[1].toFixed(1);
}
/* square-dot bag for beam squares in [a0..a1] on the even-degree grid */
function bsSquares(cx, cy, pxm, step, a0, a1) {
  let d = '';
  for (let deg = a0; deg <= a1; deg += step) {
    const r = bsBeam(deg);
    if (r === null) continue;
    const p = bsXY(cx, cy, pxm, deg, r);
    d += 'M' + (p[0] - 1.2).toFixed(1) + ' ' + (p[1] - 1.2).toFixed(1) + 'h2.4v2.4h-2.4z';
  }
  return d;
}

ANIMS.beamSweep = async function (host) {
  const objB = bsXY(266, 226, 95, 20, 0.70);
  const objA = bsXY(266, 226, 95, -10, 0.90);
  const l45 = bsXY(266, 226, 1, 45, 176);
  const lm45 = bsXY(266, 226, 1, -45, 176);
  const zBand = bsXY(266, 226, 1, 66, 130);
  const svg = host.setStage(
    txt(450, 26, 'beam loop: সামনের cone-এর ভেতরে সবচেয়ে কাছের object-এর খোঁজ — L56-L72', { anchor: 'middle', size: 14, weight: 600, fill: '#ffb454' }) +
    /* ---------- left: fused ring, top view ---------- */
    rrect(40, 44, 452, 340, 8, '#0d1117', '#2a3442') +
    txt(54, 62, 'FUSED 360 RING (top view)', { size: 9, weight: 700, fill: '#e6edf3' }) +
    txt(54, 75, 'merge + filter থেকে /scan — দুই lidar এক চোখ', { size: 7.5, fill: '#8b949e' }) +
    '<path d="M266 210L266 70" stroke="#6e7681" stroke-width="1" stroke-dasharray="3 4" fill="none"/>' +
    txt(266, 64, 'deg 0', { anchor: 'middle', size: 7, fill: '#8b949e' }) +
    txt(104, 229, '+90', { anchor: 'middle', size: 7, fill: '#8b949e' }) +
    txt(428, 229, '-90', { anchor: 'middle', size: 7, fill: '#8b949e' }) +
    txt(266, 372, '180', { anchor: 'middle', size: 7, fill: '#8b949e' }) +
    '<path id="bs-ring" d="' + bsSquares(266, 226, 95, 2, -178, 178) + '" fill="#7ee787" opacity="0.4"/>' +
    '<path d="' + bsArcD(266, 226, 150, -45, 45) + '" fill="none" stroke="#7ee787" stroke-width="8" opacity="0.9" id="bs-fa" />' +
    txt(l45[0], l45[1], '+45', { anchor: 'middle', size: 7, weight: 700, fill: '#7ee787' }) +
    txt(lm45[0], lm45[1], '-45', { anchor: 'middle', size: 7, weight: 700, fill: '#7ee787' }) +
    circ(objB[0], objB[1], 4.5, '#ff7b72', ' id="bs-objB" opacity="0.9"') +
    txt(objB[0] + 8, objB[1] - 6, '0.70 m @ +20', { size: 7.5, weight: 700, fill: '#ff7b72', id: 'bs-objBt', op: 0 }) +
    circ(objA[0], objA[1], 4, '#d2a8ff', ' id="bs-objA" opacity="0.9"') +
    txt(objA[0] - 8, objA[1] - 8, '0.90 m @ -10', { anchor: 'end', size: 7.5, weight: 700, fill: '#d2a8ff', id: 'bs-objAt', op: 0 }) +
    txt(zBand[0] - 6, zBand[1], 'ranges = 0.0', { anchor: 'end', size: 7, mono: true, fill: '#6e7681', id: 'bs-zt', op: 0 }) +
    rrect(257, 216, 18, 20, 3, '#30363d', '#8b949e') +
    '<path d="M266 216L266 207" stroke="#7ee787" stroke-width="2" fill="none"/>' +
    txt(285, 207, 'front', { size: 6.5, fill: '#8b949e' }) +
    txt(54, 328, 'SCAN CURSOR', { size: 7, weight: 700, fill: '#6e7681' }) +
    txt(54, 344, 'i = 0', { size: 9, mono: true, weight: 700, fill: '#e6edf3', id: 'bs-ri' }) +
    txt(54, 358, 'angle = -180 deg', { size: 8.5, mono: true, fill: '#8b949e', id: 'bs-ra' }) +
    txt(54, 372, 'ranges[i] = 1.25 m', { size: 8.5, mono: true, fill: '#8b949e', id: 'bs-rr' }) +
    txt(160, 344, '+deg = বাঁদিক', { size: 7.5, fill: '#6e7681' }) +
    '<g id="bs-cur" transform="rotate(180 266 226)"><line x1="266" y1="226" x2="266" y2="90" stroke="#e6edf3" stroke-width="1.2" opacity="0.9"/><circle cx="266" cy="90" r="3" fill="#e6edf3"/></g>' +
    /* ---------- right: code L56-L72 ---------- */
    rrect(516, 44, 344, 252, 8, '#0d1117', '#30363d') +
    txt(688, 62, 'registerScan — beam loop (L56-L72)', { anchor: 'middle', size: 9, weight: 700, fill: '#e6edf3' }) +
    rrect(522, 70, 332, 27, 3, '#21262d', 'none', ' id="bs-hl1" opacity="0"') +
    rrect(522, 96, 332, 13, 3, '#21262d', 'none', ' id="bs-hl2" opacity="0"') +
    rrect(522, 109, 332, 27, 3, '#21262d', 'none', ' id="bs-hl3" opacity="0"') +
    rrect(522, 136, 332, 13, 3, '#21262d', 'none', ' id="bs-hl4" opacity="0"') +
    rrect(522, 149, 332, 27, 3, '#21262d', 'none', ' id="bs-hl5" opacity="0"') +
    rrect(522, 176, 332, 13, 3, '#21262d', 'none', ' id="bs-hl6" opacity="0"') +
    rrect(522, 189, 332, 27, 3, '#21262d', 'none', ' id="bs-hl7" opacity="0"') +
    txt(530, 80, 'def registerScan(self, scan_data):', { size: 8, mono: true, fill: '#8b949e' }) +
    txt(530, 94, 'if not isinstance(scan_data, LaserScan): return', { size: 8, mono: true, fill: '#8b949e' }) +
    txt(530, 105, 'ranges = np.array(scan_data.ranges)', { size: 8, mono: true, fill: '#8b949e' }) +
    txt(530, 119, 'minDistList = []', { size: 8, mono: true, fill: '#8b949e' }) +
    txt(530, 132, 'minDistIDList = []', { size: 8, mono: true, fill: '#8b949e' }) +
    txt(530, 145, 'for i in range(len(ranges)):', { size: 8, mono: true, fill: '#8b949e' }) +
    txt(530, 159, 'angle = (scan_data.angle_min +', { size: 8, mono: true, fill: '#8b949e' }) +
    txt(530, 173, 'scan_data.angle_increment * i) * RAD2DEG', { size: 8, mono: true, fill: '#8b949e' }) +
    txt(530, 186, 'if abs(angle) &lt; self.LaserAngle and ranges[i] !=0.0 :', { size: 8, mono: true, fill: '#8b949e' }) +
    txt(530, 199, 'minDistList.append(ranges[i])', { size: 8, mono: true, fill: '#8b949e' }) +
    txt(530, 212, 'minDistIDList.append(angle)', { size: 8, mono: true, fill: '#8b949e' }) +
    txt(848, 80, 'L56', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    txt(848, 94, 'L57', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    txt(848, 105, 'L58', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    txt(848, 119, 'L61', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    txt(848, 132, 'L62', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    txt(848, 145, 'L65', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    txt(848, 159, 'L67', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    txt(848, 186, 'L70', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    txt(848, 199, 'L71', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    txt(848, 212, 'L72', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    /* ---------- right: the two parallel lists ---------- */
    rrect(516, 306, 344, 78, 8, '#111', '#30363d') +
    txt(688, 322, 'দুই parallel list — cone-এ ধরা পড়া বীম', { anchor: 'middle', size: 8.5, weight: 700, fill: '#e6edf3' }) +
    rrect(528, 330, 118, 46, 5, '#161b22', '#7ee787') +
    txt(587, 343, 'minDistList (m)', { anchor: 'middle', size: 7, mono: true, weight: 700, fill: '#7ee787' }) +
    txt(538, 360, '0.90', { size: 9, mono: true, weight: 700, fill: '#e6edf3', id: 'bs-v1', op: 0 }) +
    txt(570, 371, '0.70', { size: 9, mono: true, weight: 700, fill: '#ff7b72', id: 'bs-v2', op: 0 }) +
    rrect(654, 330, 118, 46, 5, '#161b22', '#e3b341') +
    txt(713, 343, 'minDistIDList (deg)', { anchor: 'middle', size: 7, mono: true, weight: 700, fill: '#e3b341' }) +
    txt(664, 360, '-10', { size: 9, mono: true, weight: 700, fill: '#e6edf3', id: 'bs-v3', op: 0 }) +
    txt(696, 371, '+20', { size: 9, mono: true, weight: 700, fill: '#ff7b72', id: 'bs-v4', op: 0 }) +
    txt(790, 360, 'len', { anchor: 'middle', size: 7, mono: true, fill: '#8b949e' }) +
    txt(790, 374, '2', { anchor: 'middle', size: 11, mono: true, weight: 700, fill: '#e6edf3', id: 'bs-len' }) +
    /* ---------- bottom strip: legend + notes ---------- */
    '<path d="M48 393h7v7h-7z" fill="#7ee787"/><path d="M156 393h7v7h-7z" fill="#ff7b72"/><path d="M262 393h7v7h-7z" fill="#d2a8ff"/><path d="M368 393h7v7h-7z" fill="#6e7681"/>' +
    txt(60, 400, 'ring beam &lt; 45° বাইরে', { size: 8, fill: '#8b949e' }) +
    txt(168, 400, 'tracked 0.70 m @ +20°', { size: 8, fill: '#8b949e' }) +
    txt(274, 400, 'দ্বিতীয় 0.90 m @ -10°', { size: 8, fill: '#8b949e' }) +
    txt(380, 400, 'ranges = 0.0 (skip)', { size: 8, fill: '#8b949e' }) +
    txt(48, 416, ' ', { size: 7.5, weight: 700, fill: '#e3b341', id: 'bs-note', op: 0 }) +
    txt(48, 430, 'LaserAngle = 45.0 (L36) · কঠোর &lt; মানে cone-এ 89 beam (i = 136..224) — ring-এর মান illustrative', { size: 7.5, fill: '#6e7681' }) +
    txt(450, 450, 'source: laser_Tracker.py L56-L72 · laser_driver.launch.py L28-L42 (folder 10 chain)', { anchor: 'middle', size: 8, mono: true, fill: '#6e7681' })
  );
  const q = id => svg.querySelector('#' + id);
  const show = id => q(id).setAttribute('opacity', 1);
  const hide = id => q(id).setAttribute('opacity', 0);
  function bsAim(d) {
    q('bs-cur').setAttribute('transform', 'rotate(' + (-d) + ' 266 226)');
    q('bs-ri').textContent = 'i = ' + (d + 180);
    q('bs-ra').textContent = 'angle = ' + (d > 0 ? '+' : '') + d + ' deg';
    q('bs-rr').textContent = 'ranges[i] = ' + bsBeam(d).toFixed(2) + ' m';
  }
  host.caption('folder 10-এর merger দুই lidar জোড়ে এক fused 360 ring বানায়, filter সেটিকেই <code>/scan</code>-এ দেয় — তাই <code>registerScan</code>-এর <code>ranges</code> একটাই পূর্ণ বৃত্ত। এই anim-এ L56-72: সেই বৃত্ত ঘেঁটে সামনের cone-এর সবচেয়ে কাছের object-এর খোঁজ। ছবিতে deg 0 = সামনে, +deg = বাঁদিক (ROS convention)।');
  host.formula('angle_i = (angle_min + angle_increment * i) * RAD2DEG   [rad -> deg, RAD2DEG = 180/pi]');
  /* --- beat 1: L56 def + L57 guard + L58 ranges --- */
  show('bs-hl1'); show('bs-hl2');
  host.caption('<b>L56</b> <code>def registerScan(self, scan_data)</code> — /scan-এর প্রতিটা message এই callback-এ আসবে (subscription L23)। <b>L57</b> পাহারা: message-টা সত্যিই <code>LaserScan</code> না হলে সোজা <code>return</code>। <b>L58</b> <code>ranges = np.array(scan_data.ranges)</code> — দূরত্বের মানগুলো numpy array-তে তোলা।');
  await host.sleep(1700);
  hide('bs-hl1'); hide('bs-hl2'); show('bs-hl3');
  host.caption('দুটো খালি list জন্মাল (<b>L61-62</b>): <code>minDistList</code> রাখবে দূরত্ব, <code>minDistIDList</code> রাখবে সেই দূরত্বের beam-এর কোণ — একই beam-এর দুটো পাশ, index-এ index। এদের জোড়া পরে <code>min()</code>-এর সময় কাজে লাগবে।');
  host.formula('minDistList[k] = distance of beam k  |  minDistIDList[k] = angle of beam k');
  await host.sleep(1700);
  /* --- beat 2: L65 sweep --- */
  hide('bs-hl3'); show('bs-hl4');
  host.caption('L65 <code>for i in range(len(ranges))</code> — cursor-টা i=0 (deg -180, একদম পেছনে) থেকে বেয়ে বেয়ে হাঁটে; প্রতিটি i মানে <code>ranges</code> অ্যারের একটা দূরত্ব-মান। tracking-এর খোঁজও শুরু এখান থেকেই — সামনে, পেছনে সব beam-ই ঘোরা হবে।');
  await host.sleep(700);
  const bsHops = [-180, -144, -108, -72, -36, 0, 36, 72, 108, 144];
  for (let k = 0; k < bsHops.length; k++) { bsAim(bsHops[k]); await host.sleep(230); }
  /* --- beat 3: L67 formula --- */
  host.caption('L67: <code>angle = (scan_data.angle_min + scan_data.angle_increment * i) * RAD2DEG</code> — message-এ কোণ radian-এ (folder 09-এর echo), কিন্তু cone-এর তুলনা degree-তে; <code>RAD2DEG = 180 / pi</code> (L15)। এই fused ring-এ (illustrative) angle_min = -180 deg আর increment = 1 deg বীমপ্রতি, তাই angle = -180 + i।');
  host.formula('i = 192:  (-180 + 192) = +12 deg   (front-left beam)');
  hide('bs-hl4'); show('bs-hl5'); bsAim(12);
  await host.sleep(1700);
  /* --- beat 4: L70 cone gate --- */
  host.caption('FRONT cone (L70): <code>abs(angle) &lt; self.LaserAngle</code>, LaserAngle = 45.0 (L36) — সবুজ arc মানে ±45 deg। সঙ্গে <code>ranges[i] !=0.0</code>: 0.0 মানে beam কিছুই পায়নি — সেই beam-গুলো বাদ; কিন্তু <code>inf</code> (no-return) এই চেক পাস করে ফেলে — 0 আর inf এক নয়।');
  host.formula('cone: |angle| < 45.0 deg AND ranges[i] != 0.0   ->  i = 136..224 = 89 beams');
  hide('bs-hl5'); show('bs-hl6'); show('bs-fa'); show('bs-zt'); show('bs-objBt'); show('bs-objAt');
  bsAim(66);
  await host.sleep(1800);
  /* --- beat 5: L71-72 appends --- */
  host.caption('gate পাস করলেই দুটো append (<b>L71-72</b>): দূরত্ব যায় <code>minDistList</code>-এ, কোণ যায় <code>minDistIDList</code>-এ। ডেমো ring-এ cone-এ দুটো object: 0.90 m @ -10° আর 0.70 m @ +20° (illustrative) — দুজনের দূরত্ব-কোণ জোড়া পাশাপাশি বসছে।');
  host.formula('append pair: (0.90, -10) then (0.70, +20)  |  len(minDistList) = len(minDistIDList)');
  hide('bs-hl6'); show('bs-hl7'); show('bs-v1'); show('bs-v2'); show('bs-v3'); show('bs-v4');
  bsAim(-10); await host.sleep(650);
  bsAim(20); q('bs-len').textContent = '2';
  await host.sleep(1600);
  /* --- close --- */
  q('bs-note').textContent = 'loop শেষ — এবার min(minDistList) (L77) আর argmin জোড়া (L79): minDist = 0.70, minDistID = +20';
  show('bs-note');
  host.caption('loop শেষে দুই list-এ cone-এর সব ধরা-পড়া beam। পরের ধাপ (L77-79): <code>minDist = min(minDistList)</code> = <b>0.70 m</b>, আর <code>minDistID</code> = সেই কাছের beam-এর কোণ = <b>+20 deg</b> — argmin-এর মতো জোড়া, tie হলে প্রথমটা জেতে। List শূন্য হলে (L80-83) সামনে কিছু নেই — <code>return</code>, কোনো publish নেই।');
  host.formula('minDist = min(list) = 0.70 m  |  minDistID = list[index(minDist)] = +20 deg');
  await host.sleep(1700);
  host.caption('মোদ্দা কথা: avoidance (folder 11) গুনত কত beam কাছে — এই node বরং খোঁজে কোন beam-টা সবচেয়ে কাছে। 89 beam-এর ভেতরের min-ই tracking-এর টার্গেট: ওই object-কেই 0.55 m দূরত্বে ফেলে রাখতে হবে, মুখ তার দিকেই রাখতে হবে।');
  await host.sleep(1600);
};
