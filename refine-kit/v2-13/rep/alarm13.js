/* ---------- alarmBuzzer ---------- */
/* ===== folder-13 v1 anim — alarmBuzzer (part 12) =====================
   laser_Warning.py L87-L95, THE alarm block — the channel the
   tracker (folder 12) never had. Source sha b1cf2d67a4d5. L87
   comment header, L88 danger-zone comment, L89 test
   `if minDist <= self.ResponseDist and minDist != 0.0:` —
   ResponseDist 0.55 born L41-42 (declare + read, "Danger Zone"
   comment in source); second clause is belt-and-suspenders: the
   cone filter L68 already excluded exact 0.0 readings. inf <= 0.55
   is False -> else -> OFF; NaN fails both comparisons -> else ->
   OFF. L90-92 `b = UInt16(); b.data = 1; pub_Buzzer.publish(b)` =
   BEEP ON; L93-L95 else `pub_Buzzer.publish(UInt16())` = default 0
   = BEEP OFF, published EVERY scan while an object is visible
   outside the zone (trailing space after the call IN SOURCE, noted
   in-card, not quoted). pub_Buzzer born L32 (/beep, UInt16, depth
   1); UInt16 import L6 ("buzzer ON/OFF message type").
   Semantics taught: /beep is a LEVEL refreshed per scan, not an
   edge. Skip paths never refresh it: empty cone L73 return, Joy
   gate L81-83 (zero Twist + return BEFORE the alarm block) — /beep
   latches its last value, the buzzer-stays-on trap; exit_pro
   L127-132 brakes /cmd_vel only, never touches /beep. No
   hysteresis: boundary 0.55 exactly -> `<=` is TRUE -> ON; a hover
   at the line toggles at scan rate (chatter; 0.55/0.56 jitter
   illustrative). Wave numbers from the canonical table
   (illustrative): C 0.48 m @ 0 deg -> beep 1, u = 0 so deadzone
   zeroes z — robot still + beeping; D 0.50 m @ -20 deg -> beep 1,
   z = -0.417; B 0.70 m @ +20 deg -> else, UInt16() = 0, z = +0.417;
   E empty front -> LATCH 1 from D; A 0.90 / F 0.80 timeline only.
   Timeline cadence illustrative. Prefix ab-, helper abX. No emoji,
   no Unicode arrows in stage strings, entities for &lt; &gt;.
   Static backbone visible at setStage; first caption + formula
   before the first await. */

ANIMS.alarmBuzzer = async function (host) {
  const svg = host.setStage(
    txt(450, 24, 'alarm: ResponseDist-এর ভেতরে এলেই বিপ — একটা level, প্রতি scan-এ refresh, L89-L95', { anchor: 'middle', size: 13.5, weight: 600, fill: '#ffb454' }) +
    /* ---------- left: code L87-L95 ---------- */
    rrect(40, 42, 302, 306, 8, '#0d1117', '#2a3442') +
    txt(54, 60, 'CODE — laser_Warning.py L87-L95', { size: 9.5, weight: 700, fill: '#e6edf3' }) +
    rrect(50, 108, 282, 88, 4, '#f85149', 'none', ' fill-opacity="0.12" id="ab-hif" opacity="0"') +
    rrect(50, 197, 282, 54, 4, '#7ee787', 'none', ' fill-opacity="0.10" id="ab-hel" opacity="0"') +
    txt(58, 84, '# --- THE ALARM LOGIC ---', { size: 7.5, mono: true, fill: '#6e7681' }) +
    txt(58, 99, '# ... inside the Danger Zone (0.55m)...', { size: 7.5, mono: true, fill: '#6e7681' }) +
    txt(88, 120, 'if minDist &lt;= self.ResponseDist and', { size: 8, mono: true, fill: '#e6edf3' }) +
    txt(100, 133, 'minDist != 0.0:', { size: 8, mono: true, fill: '#e6edf3' }) +
    txt(100, 152, 'b = UInt16()', { size: 8, mono: true, fill: '#c9d1d9' }) +
    txt(100, 171, 'b.data = 1        # 1 means BEEP!', { size: 8, mono: true, fill: '#c9d1d9' }) +
    txt(100, 190, 'self.pub_Buzzer.publish(b)', { size: 8, mono: true, fill: '#c9d1d9' }) +
    txt(88, 209, 'else:', { size: 8, mono: true, fill: '#e6edf3' }) +
    txt(100, 224, '# ... turn the buzzer off (0).', { size: 7.5, mono: true, fill: '#6e7681' }) +
    txt(100, 243, 'self.pub_Buzzer.publish(UInt16())', { size: 8, mono: true, fill: '#c9d1d9' }) +
    txt(82, 120, 'L89', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    txt(82, 152, 'L90', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    txt(82, 171, 'L91', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    txt(82, 190, 'L92', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    txt(82, 209, 'L93', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    txt(82, 243, 'L95', { anchor: 'end', size: 7, mono: true, fill: '#6e7681' }) +
    rrect(50, 258, 282, 66, 4, '#161b22', '#30363d') +
    txt(58, 272, 'দুই SKIP পথ — alarm block পর্যন্ত পৌঁছায়ই না', { size: 7.5, weight: 700, fill: '#ff7b72' }) +
    txt(58, 287, 'L73     if len(minDistList) == 0: return', { size: 7, mono: true, fill: '#c9d1d9' }) +
    txt(58, 301, 'L81-83  Joy_active: publish(Twist()) + return', { size: 7, mono: true, fill: '#c9d1d9' }) +
    txt(58, 315, 'দুই-ই /beep-এ হাত দেয় না — শেষ মান latched', { size: 7, fill: '#ff7b72', id: 'ab-skipn', op: 0 }) +
    txt(58, 338, 'L95-এর শেষে source-এ একটা ফাঁকা space আছে', { size: 6.8, fill: '#6e7681' }) +
    /* ---------- middle: distance axis ---------- */
    rrect(356, 42, 248, 306, 8, '#0d1117', '#30363d') +
    txt(480, 60, 'DISTANCE — minDist অক্ষ (m)', { anchor: 'middle', size: 9.5, weight: 700, fill: '#e6edf3' }) +
    rrect(406, 70, 148, 26, 13, '#161b22', '#30363d', ' id="ab-verd"') +
    txt(480, 87, '— শুরু হয়নি —', { anchor: 'middle', size: 8, weight: 700, fill: '#8b949e', id: 'ab-verdt' }) +
    rrect(376, 228, 114.4, 36, 3, '#f85149', 'none', ' fill-opacity="0.16"') +
    txt(433, 242, 'DANGER ZONE', { anchor: 'middle', size: 6.5, weight: 700, fill: '#ff7b72' }) +
    txt(433, 255, '0 .. 0.55 m', { anchor: 'middle', size: 6, mono: true, fill: '#ff7b72' }) +
    txt(490.4, 202, 'ResponseDist 0.55 m (L41-42)', { anchor: 'middle', size: 7, mono: true, weight: 700, fill: '#ff7b72' }) +
    line(490.4, 208, 490.4, 268, '#f85149', 1.2, ' stroke-dasharray="4 3"') +
    line(376, 264, 584, 264, '#6e7681', 1.5) +
    line(376, 264, 376, 270, '#6e7681', 1.5) +
    line(428, 264, 428, 270, '#6e7681', 1.5) +
    line(480, 264, 480, 270, '#6e7681', 1.5) +
    line(532, 264, 532, 270, '#6e7681', 1.5) +
    line(584, 264, 584, 270, '#6e7681', 1.5) +
    txt(376, 281, '0.0', { anchor: 'middle', size: 6.5, mono: true, fill: '#6e7681' }) +
    txt(428, 281, '0.25', { anchor: 'middle', size: 6.5, mono: true, fill: '#6e7681' }) +
    txt(480, 281, '0.5', { anchor: 'middle', size: 6.5, mono: true, fill: '#6e7681' }) +
    txt(532, 281, '0.75', { anchor: 'middle', size: 6.5, mono: true, fill: '#6e7681' }) +
    txt(584, 281, '1.0', { anchor: 'middle', size: 6.5, mono: true, fill: '#6e7681' }) +
    rrect(362, 236, 16, 20, 3, '#21262d', '#8b949e') +
    '<path d="M378 240L388 246L378 252Z" fill="#4fc3f7"/>' +
    txt(370, 296, 'robot', { anchor: 'middle', size: 7, fill: '#8b949e' }) +
    circ(475.8, 246, 6, '#e3b341', ' id="ab-obj" opacity="0" stroke="#0d1117" stroke-width="1"') +
    txt(475.8, 222, '0.48 m — Wave C', { anchor: 'middle', size: 7.5, weight: 700, mono: true, fill: '#e3b341', id: 'ab-objt', op: 0 }) +
    txt(480, 316, 'minDist = —', { anchor: 'middle', size: 8, mono: true, fill: '#e6edf3', id: 'ab-dist', op: 0 }) +
    txt(480, 332, '—', { anchor: 'middle', size: 7.5, fill: '#8b949e', id: 'ab-behav', op: 0 }) +
    txt(480, 344, '—', { anchor: 'middle', size: 7, mono: true, fill: '#7ee787', id: 'ab-cmp', op: 0 }) +
    /* ---------- right: buzzer + /beep channel ---------- */
    rrect(618, 42, 242, 306, 8, '#0d1117', '#2a3442') +
    txt(739, 60, 'CHANNEL — pub_Buzzer -&gt; /beep', { anchor: 'middle', size: 9.5, weight: 700, fill: '#e6edf3' }) +
    circ(700, 128, 18, '#161b22', ' id="ab-bz" stroke="#30363d" stroke-width="2"') +
    circ(700, 128, 7, '#30363d', ' id="ab-bzc"') +
    path('M678 114 A 26 26 0 0 1 722 114', '#ff7b72', 2, ' id="ab-w1" opacity="0"') +
    path('M666 108 A 36 36 0 0 1 734 108', '#ff7b72', 2, ' id="ab-w2" opacity="0"') +
    path('M656 104 A 46 46 0 0 1 744 104', '#ff7b72', 1.6, ' id="ab-w3" opacity="0"') +
    txt(726, 124, 'নীরব', { size: 8, weight: 700, fill: '#8b949e', id: 'ab-bzt' }) +
    txt(700, 166, 'buzzer', { anchor: 'middle', size: 7, fill: '#8b949e' }) +
    line(700, 172, 700, 196, '#6e7681', 1.5) +
    txt(710, 188, '/beep', { size: 7, mono: true, fill: '#ff7b72' }) +
    rrect(644, 198, 190, 26, 13, '#161b22', '#30363d', ' id="ab-chip"') +
    txt(739, 215, 'UInt16 data = —', { anchor: 'middle', size: 8.5, weight: 700, mono: true, fill: '#8b949e', id: 'ab-chipt' }) +
    txt(739, 240, 'publish এসেছে: এখনো নয়', { anchor: 'middle', size: 7.5, fill: '#8b949e', id: 'ab-pubsrc', op: 0 }) +
    txt(739, 254, 'pub_Buzzer জন্ম L32-এ · QoS depth 1', { anchor: 'middle', size: 6.8, fill: '#6e7681' }) +
    txt(739, 267, 'UInt16 import L6 — buzzer ON/OFF message type', { anchor: 'middle', size: 6.8, fill: '#6e7681' }) +
    rrect(630, 276, 218, 66, 4, '#161b22', '#f85149', ' id="ab-trap" opacity="0"') +
    txt(739, 291, 'LATCH ফাঁদ — Wave E', { anchor: 'middle', size: 7.5, weight: 700, fill: '#ff7b72', id: 'ab-trapt', op: 0 }) +
    txt(739, 305, 'সামনে খালি: L73 return — কোনো publish নেই', { anchor: 'middle', size: 7, fill: '#c9d1d9', id: 'ab-trap2', op: 0 }) +
    txt(739, 317, 'Joy L81-83-ও একই; exit_pro-ও /beep ছোঁয় না', { anchor: 'middle', size: 7, fill: '#c9d1d9', id: 'ab-trap3', op: 0 }) +
    txt(739, 331, '/beep শেষ মানে আটকে থাকে — বিপ চলতেই থাকে', { anchor: 'middle', size: 7, weight: 700, fill: '#ff7b72', id: 'ab-trap4', op: 0 }) +
    /* ---------- bottom: /beep timeline ---------- */
    rrect(40, 356, 820, 84, 8, '#111', '#30363d') +
    txt(60, 372, 'LEVEL, NOT EDGE — /beep-এর সময়রেখা (illustrative)', { size: 8.5, weight: 700, fill: '#e6edf3' }) +
    txt(840, 372, 'লাল = ON, ধূসর = OFF, ড্যাশ = latched', { anchor: 'end', size: 7, fill: '#8b949e' }) +
    txt(88, 390, 'ON', { anchor: 'end', size: 6.5, weight: 700, fill: '#ff7b72' }) +
    txt(88, 418, 'OFF', { anchor: 'end', size: 6.5, fill: '#6e7681' }) +
    circ(96, 414, 2.5, '#4fc3f7') +
    circ(226, 414, 2.5, '#4fc3f7') +
    circ(356, 414, 2.5, '#4fc3f7') +
    circ(486, 414, 2.5, '#4fc3f7') +
    circ(616, 414, 2.5, '#4fc3f7') +
    circ(716, 414, 2.5, '#4fc3f7') +
    circ(816, 414, 2.5, '#4fc3f7') +
    line(96, 414, 226, 414, '#6e7681', 2.5) +
    line(226, 414, 356, 414, '#6e7681', 2.5) +
    line(356, 386, 356, 414, '#ff7b72', 2) +
    line(356, 386, 486, 386, '#ff7b72', 2.5) +
    line(486, 386, 616, 386, '#ff7b72', 2.5) +
    line(616, 386, 716, 386, '#ff7b72', 2.5, ' stroke-dasharray="5 4" id="ab-tE"') +
    line(716, 386, 716, 414, '#ff7b72', 2) +
    line(716, 414, 816, 414, '#6e7681', 2.5) +
    txt(161, 432, 'A 0.90', { anchor: 'middle', size: 6.5, mono: true, fill: '#6e7681' }) +
    txt(291, 432, 'B 0.70', { anchor: 'middle', size: 6.5, mono: true, fill: '#6e7681' }) +
    txt(421, 432, 'C 0.48', { anchor: 'middle', size: 6.5, mono: true, fill: '#ff7b72' }) +
    txt(551, 432, 'D 0.50', { anchor: 'middle', size: 6.5, mono: true, fill: '#ff7b72' }) +
    txt(666, 432, 'E খালি', { anchor: 'middle', size: 6.5, mono: true, fill: '#ff7b72' }) +
    txt(766, 432, 'F 0.80', { anchor: 'middle', size: 6.5, mono: true, fill: '#6e7681' }) +
    txt(666, 378, 'latched — publish নেই', { anchor: 'middle', size: 6, fill: '#ff7b72' }) +
    rrect(348, 368, 146, 60, 4, '#f85149', 'none', ' fill-opacity="0.10" id="ab-cur" opacity="0"') +
    txt(450, 452, 'source: laser_Warning.py L87-L95 · ResponseDist L41-42 · pub_Buzzer L32 · UInt16 L6 · skip পথ L73 + L81-83 · exit_pro L127-132', { anchor: 'middle', size: 7.5, mono: true, fill: '#6e7681' })
  );
  const q = id => svg.querySelector('#' + id);
  const show = i => q(i).setAttribute('opacity', 1);
  const hide = i => q(i).setAttribute('opacity', 0);
  const abX = d => 376 + 208 * d;
  /* buzzer + chip + arcs as one LEVEL state */
  const abBeep = (on, label) => {
    q('ab-bzc').setAttribute('fill', on ? '#ff7b72' : '#30363d');
    q('ab-bz').setAttribute('stroke', on ? '#ff7b72' : '#30363d');
    q('ab-bzt').textContent = label || (on ? 'বিপ চালু' : 'নীরব');
    q('ab-bzt').setAttribute('fill', on ? '#ff7b72' : '#8b949e');
    q('ab-chipt').textContent = 'UInt16 data = ' + (on ? '1' : '0');
    q('ab-chipt').setAttribute('fill', on ? '#ff7b72' : '#8b949e');
    q('ab-chip').setAttribute('stroke', on ? '#f85149' : '#30363d');
    ['ab-w1', 'ab-w2', 'ab-w3'].forEach(i => { if (on) show(i); else hide(i); });
  };
  const abVerdict = (t, col) => {
    q('ab-verdt').textContent = t;
    q('ab-verdt').setAttribute('fill', col);
    q('ab-verd').setAttribute('stroke', col);
  };
  const abObj = (d, label) => {
    const x = abX(d);
    q('ab-obj').setAttribute('cx', x);
    q('ab-objt').setAttribute('x', x);
    q('ab-objt').textContent = label;
  };
  const abCur = (x, w) => {
    q('ab-cur').setAttribute('x', x);
    q('ab-cur').setAttribute('width', w);
    show('ab-cur');
  };

  host.caption('guard-এর স্বাক্ষর — <b>alarm block</b>, part 12। বাঁয়ে L87-L95-এর কোড, মাঝে minDist-অক্ষ, ডানে <code>/beep</code> চ্যানেল, নিচে পুরো সময়রেখা। প্রশ্ন একটাই: সামনের সবচেয়ে কাছের object-টা <code>ResponseDist</code> <b>0.55 m</b>-এর (L41-42) ভেতরে কি না। ভেতরে হলে <code>UInt16</code> মান 1, বাইরে হলে 0 — আর দুটোই <b>প্রতি scan-এ নতুন করে লেখা হয়</b>: এটা level, edge নয়।');
  host.formula('alarm = (minDist &lt;= 0.55 and minDist != 0.0) ? /beep 1 : /beep 0   [level, refreshed every scan]');
  await host.sleep(1800);

  /* --- beat 1: Wave C inside -> ON --- */
  show('ab-hif'); show('ab-obj'); show('ab-objt'); show('ab-dist'); show('ab-behav'); show('ab-cmp'); show('ab-pubsrc');
  abObj(0.48, '0.48 m — Wave C');
  q('ab-dist').textContent = 'minDist = 0.48 m · minDistID = 0.0°';
  q('ab-cmp').textContent = '0.48 &lt;= 0.55 -&gt; TRUE   and   0.48 != 0.0 -&gt; TRUE';
  q('ab-behav').textContent = 'robot: দাঁড়িয়ে বিপ — u = 0, deadzone-এ z = 0.0';
  q('ab-pubsrc').textContent = 'publish এসেছে: L92 (b.data = 1)';
  abVerdict('ON — বিপ', '#ff7b72');
  abBeep(true);
  abCur(348, 146);
  host.caption('<b>Wave C</b>: object হুবহু সামনে, <b>0.48 m</b> — লাল zone-এর ভেতরে। <b>L89</b>-এর দুই শর্ত: <code>0.48 &lt;= 0.55</code> সত্য, <code>0.48 != 0.0</code>-ও সত্য — তাই ভেতরের branch: <code>b = UInt16()</code>, <code>b.data = 1</code> (L90-91), <code>pub_Buzzer.publish(b)</code> (L92)। <b>/beep = 1, বিপ ON।</b> আর এই wave-এ ঘোরার হিসাবটাও মনে করো: কোণ 0° বলে u = 0, deadzone-এ পড়ে <code>angular.z = 0.0</code>, আর <code>linear.x</code> এই file-এ কোনোদিন সেট-ই হয় না (L123) — robot দাঁড়িয়ে দাঁড়িয়েই বিপ দেয় (z-সংখ্যা illustrative)।');
  host.formula('C: 0.48 &lt;= 0.55 and 0.48 != 0.0 -> b.data = 1 -> /beep ON  |  z = 0.0 — দাঁড়িয়ে বিপ');
  await host.sleep(2400);

  /* --- beat 2: Wave D still inside --- */
  abObj(0.50, '0.50 m — Wave D');
  q('ab-dist').textContent = 'minDist = 0.50 m · minDistID = -20.0°';
  q('ab-cmp').textContent = '0.50 &lt;= 0.55 -&gt; TRUE   and   0.50 != 0.0 -&gt; TRUE';
  q('ab-behav').textContent = 'robot: ডানে ঘুরছে z = -0.417 (illustrative), বিপ চালু';
  q('ab-pubsrc').textContent = 'publish এসেছে: L92 (b.data = 1)';
  abCur(478, 146);
  host.caption('<b>Wave D</b>: object এবার <b>0.50 m</b>, ডানে -20°। দূরত্ব এখনো 0.55-এর ভেতরে — রায় একই: <b>/beep = 1</b>। খেয়াল করো, alarm-এর হিসাবে <code>minDistID</code>-র <b>কোনো ভূমিকাই নেই</b> — কোণ যা-ই হোক, দূরত্ব ভেতরে থাকলেই বিপ। এই scan-এ ঘোরার দিক বদলে গেছে (<code>z = -0.417</code>, illustrative), কিন্তু বিপের অবস্থা বদলায়নি — ঘোরানো আর সতর্কধ্বনি দুটো সম্পূর্ণ আলাদা পথ।');
  host.formula('D: 0.50 &lt;= 0.55 -> /beep ON  |  angle irrelevant — z = -0.417 (ill), beep unchanged');
  await host.sleep(2200);

  /* --- beat 3: boundary 0.55 — inclusive, no hysteresis, chatter --- */
  abObj(0.55, '0.55 m — সীমানায়');
  q('ab-dist').textContent = 'minDist = 0.55 m · সীমানায় দোলা (illustrative)';
  q('ab-cmp').textContent = '0.55 &lt;= 0.55 -&gt; TRUE (সমতাও গ্রহণ)  ·  0.56 &lt;= 0.55 -&gt; FALSE';
  q('ab-behav').textContent = 'robot: সীমানায় — বিপ দ্রুত টগল (chatter)';
  abCur(470, 160);
  host.caption('এবার সীমানার রহস্য। Object ঠিক <b>0.55 m</b>-এ ঝুলছে ধরে নাও (illustrative)। <code>&lt;=</code> চিহ্নটা <b>সমতাও গ্রহণ করে</b> — 0.55 হলে শর্ত সত্য, বিপ ON। কিন্তু সামান্য নড়লেই 0.56 — শর্ত মিথ্যা, OFF। lidar-এর মাপে এমন সূক্ষ্ম দোলা সাধারণ, আর code-এ <b>কোনো hysteresis নেই</b> (ON আর OFF-এর আলাদা দুটো সীমা নেই) — তাই সীমানায় বিপ scan-এর গতিতে টগল করতে থাকে: <b>chatter</b>।');
  host.formula('boundary: 0.55 &lt;= 0.55 = TRUE -> ON  |  0.56 &lt;= 0.55 = FALSE -> OFF  |  no hysteresis -> chatter');
  await host.sleep(2300);
  abBeep(true);
  await host.sleep(420);
  abObj(0.56, '0.56 m — সীমানার ওপারে');
  abBeep(false);
  await host.sleep(420);
  abObj(0.55, '0.55 m — সীমানায়');
  abBeep(true);
  await host.sleep(420);
  abObj(0.56, '0.56 m — সীমানার ওপারে');
  abBeep(false);
  await host.sleep(420);
  abObj(0.55, '0.55 m — সীমানায়');
  abBeep(true, 'টগল... টগল...');
  q('ab-chipt').textContent = 'UInt16 data = ?';
  host.caption('চ্যাটার চোখের সামনে: একই জায়গায় দাঁড়িয়ে object, আর বিপ অন-অফ-অন-অফ — প্রতি scan-এ নতুন রায়, কোনো স্মৃতি নেই। সীমানা এড়াতে হলে দরকার দুই সীমার নকশা (যেমন ON 0.50, OFF 0.60) — এই file-এ তা নেই; 0.55 একাই দুই দিকের রায় দেয়।');
  await host.sleep(2100);

  /* --- beat 4: Wave B outside -> else publishes 0 --- */
  show('ab-hel');
  abObj(0.70, '0.70 m — Wave B');
  q('ab-dist').textContent = 'minDist = 0.70 m · minDistID = +20.0°';
  q('ab-cmp').textContent = '0.70 &lt;= 0.55 -&gt; FALSE — দ্বিতীয় শর্ত দেখাই হয় না';
  q('ab-behav').textContent = 'robot: বাঁয়ে ঘুরছে z = +0.417 (illustrative), বিপ বন্ধ';
  q('ab-pubsrc').textContent = 'publish এসেছে: L95 (UInt16() = 0)';
  abVerdict('OFF — নীরব', '#8b949e');
  abBeep(false);
  abCur(218, 146);
  host.caption('<b>Wave B</b>: object <b>0.70 m</b>-এ — zone-এর বাইরে। প্রথম শর্তই মিথ্যা, তাই <b>else</b> (L93): <code>pub_Buzzer.publish(UInt16())</code> (L95) — default-নির্মিত <code>UInt16</code>-এর মান <b>0</b>, বিপ OFF। দুটো কথা মনে রাখো। <b>এক</b>, OFF-ও প্রতি scan-এ publish হয় — নীরবতা মানে চুপ করে যাওয়া নয়, প্রতিবার নতুন করে 0 লেখা। <b>দুই</b>, L89-এর দ্বিতীয় শর্ত <code>minDist != 0.0</code> আসলে belt-and-suspenders — cone-ফিল্টার (L68) আগেই হুবহু 0.0 বাদ দিয়েছে। আর <code>inf</code>? <code>inf &lt;= 0.55</code> মিথ্যা — else-এ OFF; <code>NaN</code> দুই তুলনাতেই ব্যর্থ — একইভাবে else, OFF।');
  host.formula('B: 0.70 &lt;= 0.55 FALSE -> else L95: UInt16() = 0 -> /beep OFF  |  inf/NaN -> else -> OFF');
  await host.sleep(2500);

  /* --- beat 5: Wave E empty front -> no publish, latch trap --- */
  hide('ab-obj'); hide('ab-objt');
  q('ab-dist').textContent = 'minDist = নেই — minDistList খালি (L73)';
  q('ab-cmp').textContent = 'L89 পর্যন্ত পৌঁছায়ইনি — L73-এ return';
  q('ab-behav').textContent = 'robot: শেষ আদেশেই চলে; বিপ থামে না';
  q('ab-pubsrc').textContent = 'publish: এই scan-এ কোনোটাই নয়';
  abVerdict('LATCH — 1 আটকে', '#d2a8ff');
  abBeep(true, 'latched — কেউ লেখেনি');
  q('ab-chipt').textContent = 'UInt16 data = 1 (পুরনো)';
  q('ab-chipt').setAttribute('fill', '#d2a8ff');
  show('ab-trap'); show('ab-trapt'); show('ab-trap2'); show('ab-trap3'); show('ab-trap4'); show('ab-skipn');
  abCur(608, 116);
  host.caption('<b>Wave E</b>: সামনের cone একদম খালি। <code>registerScan</code> <b>L73</b>-এই <code>return</code> করে — alarm block পর্যন্ত পৌঁছায়ই না, কোনো publish নেই। তাহলে <code>/beep</code>? সে আগের মানেই বসে থাকে — Wave D-এর <b>1</b>। <b>Object নেই তবু বিপ বাজতেই থাকে।</b> একই ফাঁদ Joy gate-এও (L81-83 — প্রতি scan-এ zero <code>Twist()</code> ঠেলে alarm-এর আগেই return), এমনকি Ctrl+C-র <code>exit_pro</code> brake-ও (L127-132) শুধু <code>/cmd_vel</code> লেখে, <code>/beep</code> ছোঁয় না। folder 12-এর tracker-এ এই ফাঁদটা ছিল শুধু চাকার — guard-এ এসে কণ্ঠও আটকে যায়।');
  host.formula('E: L73 return -> NO publish -> /beep stays 1 (latched)  |  Joy L81-83 + exit_pro L127-132: same gap');
  await host.sleep(2500);

  /* --- beat 6: close — the level rule --- */
  host.caption('পুরো গল্পটা এক লাইনে: <b>/beep একটা level, edge নয়</b>। Object ভেতরে থাকার প্রতিটি scan-এ 1 লেখা হয়, বাইরের প্রতিটি scan-এ 0 — নিজে নিজে "মনে" থাকে না, প্রতি বার নতুন করে লেখে। আর যে scan-এ লেখাই হয় না — খালি cone, Joy, বা node-এর মৃত্যু — সেখানে সর্বশেষ লেখাটাই জমে থাকে। সীমানায় <code>&lt;=</code>-এর সমতা আর hysteresis-এর অনুপস্থিতি মিলে chatter বানায়। এবার বাকি শুধু ঘোরানোর হিসাব — যার জন্ম হয়ে গেছে এই block-এর ঠিক পরেই, L98 থেকে।');
  host.formula('level rule: inside -> write 1 · outside -> write 0 · no write -> last value stays  |  0.55 itself = ON');
  await host.sleep(2100);
};
