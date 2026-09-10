/* ============ folder-14 anim — teleop14 (part 5, v1 layer) ============
   yahboom_keyboard.py L1-L64. msg banner L16-45 (the printed menu).
   moveBindings L47-58: 12 keys, tuples (forward_back, strafe, rotate) —
   i/I (1,0,0) fwd; ,/M (-1,0,0) back; a/A (0,1,0) left-strafe; d/D
   (0,-1,0) right; j/J (0,0,1) rotate left; l/L (0,0,-1) rotate right;
   u/U (1,1,0) diag fwd-left; o/O (1,-1,0) diag fwd-right; m (-1,1,0)
   back-left; . (-1,-1,0) back-right. NOTE: 'M' mirrors ',' (both back);
   lowercase 'm' is the diagonal — case matters! speedBindings L60-64:
   Q/Z both (1.1,1.1)/(.9,.9); W/X (1.1,1)/(.9,1); E/C (1,1.1)/(1,.9)
   and their lowercase twins. Menu math preview (part-7 executes it):
   twist.linear.x = speed*x, .y = speed*y, .angular.z = turn*th with
   speed 0.2, turn 1.0. Unique id prefix tl14- ; no emoji ; no arrow
   chars in stage text (words/ASCII only) ; caption+formula before the
   first await ; static backbone at setStage. */


/* ---------- teleop14 ---------- */
ANIMS.teleop14 = async function (host) {
  const svg = host.setStage(
    txt(450, 26, '১২টা key-এর মানচিত্র — আর প্রতিটার পেছনে একটা (x, y, th) ভেক্টর', { anchor: 'middle', size: 14.5, weight: 600, fill: '#d2a8ff' }) +
    rrect(30, 44, 330, 322, 8, '#0d1117', '#2a3442') +
    txt(46, 64, 'yahboom_keyboard.py L16-L64 — banner + 2 dict', { size: 9.6, weight: 700, fill: '#e6edf3' }) +
    rrect(46, 72, 298, 24, 4, '#161b22', '#30363d', ' id="tl14-ban"') +
    txt(54, 86, 'L16-45  msg = f""" ... মেনু-ব্যানার ... """', { size: 7.8, mono: true, fill: '#8b949e' }) +
    txt(54, 108, "L47  # Maps keys to (forward_back, strafe, rotate)", { size: 7.4, mono: true, fill: '#6e7681', id: 'tl14-mbcom', op: 0 }) +
    rrect(46, 116, 298, 30, 4, '#161b22', '#d2a8ff', ' id="tl14-mb"') +
    txt(54, 130, "moveBindings = {", { size: 8, mono: true, weight: 700, fill: '#d2a8ff' }) +
    txt(62, 142, "'i': (1,0,0),  'a': (0,1,0),  'u': (1,1,0), ...", { size: 7.6, mono: true, fill: '#d2a8ff' }) +
    rrect(46, 152, 298, 30, 4, '#161b22', '#4fc3f7', ' id="tl14-sb"') +
    txt(54, 166, 'speedBindings = {', { size: 8, mono: true, weight: 700, fill: '#4fc3f7' }) +
    txt(62, 178, "'Q': (1.1, 1.1),  'W': (1.1, 1),  'E': (1, 1.1), ...", { size: 7.6, mono: true, fill: '#4fc3f7' }) +
    txt(46, 202, 'tuple-এর ৩টা ঘর = চাকার ৩ স্বাধীনতা', { size: 8.2, weight: 700, fill: '#e6edf3', id: 'tl14-tup', op: 0 }) +
    txt(54, 216, 'ঘর 1 — forward_back: x (+1 সামনে, -1 পেছনে)', { size: 7.5, fill: '#7ee787', id: 'tl14-t1', op: 0 }) +
    txt(54, 229, 'ঘর 2 — strafe_left_right: y (+1 বাঁয়ে, -1 ডানে)', { size: 7.5, fill: '#4fc3f7', id: 'tl14-t2', op: 0 }) +
    txt(54, 242, 'ঘর 3 — rotate_left_right: th (+1 বাঁদিকে ঘূর্ণন)', { size: 7.5, fill: '#ff7b72', id: 'tl14-t3', op: 0 }) +
    rrect(46, 254, 298, 26, 4, '#161b22', '#30363d', ' id="tl14-case"') +
    txt(54, 270, "case-এর ফাঁদ: 'M' = back,  'm' = back-left diagonal", { size: 7.6, mono: true, weight: 700, fill: '#e3b341', id: 'tl14-caset', op: 0 }) +
    txt(46, 296, 'স্কেল-গুণকের সূত্র (main loop L226-228):', { size: 7.8, weight: 700, fill: '#e6edf3', id: 'tl14-math', op: 0 }) +
    txt(54, 310, 'twist.linear.x  = speed * x', { size: 7.8, mono: true, fill: '#7ee787', id: 'tl14-m1', op: 0 }) +
    txt(54, 323, 'twist.linear.y  = speed * y', { size: 7.8, mono: true, fill: '#4fc3f7', id: 'tl14-m2', op: 0 }) +
    txt(54, 336, 'twist.angular.z = turn  * th', { size: 7.8, mono: true, fill: '#ff7b72', id: 'tl14-m3', op: 0 }) +
    txt(54, 352, 'শুরুতে speed = 0.2, turn = 1.0 (L154)', { size: 7.4, fill: '#8b949e', id: 'tl14-m4', op: 0 }) +
    rrect(376, 44, 494, 322, 8, '#111', '#30363d') +
    txt(623, 64, 'KEYPAD — চাপলে যে ভেক্টর ছোড়ে', { anchor: 'middle', size: 9.6, weight: 700, fill: '#e6edf3' }) +
    rrect(430, 80, 44, 30, 4, '#161b22', '#7ee787', ' id="tl14-ku"') +
    txt(452, 99, 'u', { anchor: 'middle', size: 11, mono: true, weight: 700, fill: '#e6edf3' }) +
    txt(452, 122, '(1,1,0)', { anchor: 'middle', size: 7, mono: true, fill: '#7ee787', id: 'tl14-kut', op: 0 }) +
    rrect(392, 80, 30, 30, 4, '#161b22', '#30363d', ' id="tl14-kq"') +
    txt(407, 99, 'Q', { anchor: 'middle', size: 10, mono: true, weight: 700, fill: '#4fc3f7' }) +
    rrect(482, 80, 44, 30, 4, '#161b22', '#7ee787', ' id="tl14-ki"') +
    txt(504, 99, 'i', { anchor: 'middle', size: 11, mono: true, weight: 700, fill: '#e6edf3' }) +
    txt(504, 122, '(1,0,0)', { anchor: 'middle', size: 7, mono: true, fill: '#7ee787', id: 'tl14-kit', op: 0 }) +
    rrect(534, 80, 44, 30, 4, '#161b22', '#7ee787', ' id="tl14-ko"') +
    txt(556, 99, 'o', { anchor: 'middle', size: 11, mono: true, weight: 700, fill: '#e6edf3' }) +
    txt(556, 122, '(1,-1,0)', { anchor: 'middle', size: 7, mono: true, fill: '#7ee787', id: 'tl14-kot', op: 0 }) +
    rrect(430, 132, 44, 30, 4, '#161b22', '#30363d', ' id="tl14-ka"') +
    txt(452, 151, 'a', { anchor: 'middle', size: 11, mono: true, weight: 700, fill: '#e6edf3' }) +
    txt(452, 174, '(0,1,0)', { anchor: 'middle', size: 7, mono: true, fill: '#4fc3f7', id: 'tl14-kat', op: 0 }) +
    rrect(482, 132, 44, 30, 4, '#161b22', '#d2a8ff', ' id="tl14-kj"') +
    txt(504, 151, 'j', { anchor: 'middle', size: 11, mono: true, weight: 700, fill: '#e6edf3' }) +
    txt(504, 174, '(0,0,1)', { anchor: 'middle', size: 7, mono: true, fill: '#ff7b72', id: 'tl14-kjt', op: 0 }) +
    rrect(534, 132, 44, 30, 4, '#161b22', '#30363d', ' id="tl14-kd"') +
    txt(556, 151, 'd', { anchor: 'middle', size: 11, mono: true, weight: 700, fill: '#e6edf3' }) +
    txt(556, 174, '(0,-1,0)', { anchor: 'middle', size: 7, mono: true, fill: '#4fc3f7', id: 'tl14-kdt', op: 0 }) +
    rrect(430, 184, 44, 30, 4, '#161b22', '#30363d', ' id="tl14-km"') +
    txt(452, 203, 'm', { anchor: 'middle', size: 11, mono: true, weight: 700, fill: '#e6edf3' }) +
    txt(452, 226, '(-1,1,0)', { anchor: 'middle', size: 7, mono: true, fill: '#7ee787', id: 'tl14-kmt', op: 0 }) +
    rrect(482, 184, 44, 30, 4, '#161b22', '#7ee787', ' id="tl14-kc"') +
    txt(504, 203, ',', { anchor: 'middle', size: 11, mono: true, weight: 700, fill: '#e6edf3' }) +
    txt(504, 226, '(-1,0,0)', { anchor: 'middle', size: 7, mono: true, fill: '#7ee787', id: 'tl14-kct', op: 0 }) +
    rrect(534, 184, 44, 30, 4, '#161b22', '#30363d', ' id="tl14-kdot"') +
    txt(556, 203, '.', { anchor: 'middle', size: 11, mono: true, weight: 700, fill: '#e6edf3' }) +
    txt(556, 226, '(-1,-1,0)', { anchor: 'middle', size: 7, mono: true, fill: '#7ee787', id: 'tl14-kdott', op: 0 }) +
    rrect(606, 80, 122, 66, 4, '#161b22', '#4fc3f7') +
    txt(667, 95, 'speed keys', { anchor: 'middle', size: 8, weight: 700, fill: '#4fc3f7' }) +
    txt(667, 110, 'Q/Z  x1.1 / x0.9  দুই-ই', { anchor: 'middle', size: 7.2, mono: true, fill: '#8b949e' }) +
    txt(667, 123, 'W/X  speed x1.1, turn স্থির', { anchor: 'middle', size: 7.2, mono: true, fill: '#8b949e' }) +
    txt(667, 136, 'E/C  turn x1.1, speed স্থির', { anchor: 'middle', size: 7.2, mono: true, fill: '#8b949e' }) +
    txt(667, 152, 'ছোট হাতের q..c-ও একই কাজ করে', { anchor: 'middle', size: 7, fill: '#8b949e' }) +
    rrect(392, 244, 222, 102, 4, '#0d1117', '#30363d', ' id="tl14-rob"') +
    rrect(488, 272, 30, 36, 3, '#161b22', '#4fc3f7') +
    path('M495 272l8-9 8 9z', '#4fc3f7', 0, ' fill="#4fc3f7" id="tl14-rhead" opacity="0"') +
    rrect(482, 268, 7, 12, 1.5, '#8b949e', '#21262d') +
    rrect(517, 268, 7, 12, 1.5, '#8b949e', '#21262d') +
    rrect(482, 302, 7, 12, 1.5, '#8b949e', '#21262d') +
    rrect(517, 302, 7, 12, 1.5, '#8b949e', '#21262d') +
    txt(503, 340, '৪ mecanum চাকা = y-strafe সম্ভব', { anchor: 'middle', size: 6.8, fill: '#8b949e', id: 'tl14-mec', op: 0 }) +
    path('M640 268l52-14', '#7ee787', 2.4, ' id="tl14-vx" opacity="0"') +
    path('M692 254l-9-1 5 8z', '#7ee787', 0, ' fill="#7ee787" id="tl14-vxa" opacity="0"') +
    path('M640 296h54', '#4fc3f7', 2.4, ' id="tl14-vy" opacity="0"') +
    path('M694 296l-8-4v8z', '#4fc3f7', 0, ' fill="#4fc3f7" id="tl14-vya" opacity="0"') +
    path('M640 326a30 30 0 0 1 40-18', '#ff7b72', 2.4, ' id="tl14-vz" opacity="0"') +
    path('M680 308l-10 0 5 8z', '#ff7b72', 0, ' fill="#ff7b72" id="tl14-vza" opacity="0"') +
    txt(706, 268, 'x', { size: 8, mono: true, weight: 700, fill: '#7ee787', id: 'tl14-vxt', op: 0 }) +
    txt(706, 296, 'y', { size: 8, mono: true, weight: 700, fill: '#4fc3f7', id: 'tl14-vyt', op: 0 }) +
    txt(706, 326, 'th', { size: 8, mono: true, weight: 700, fill: '#ff7b72', id: 'tl14-vzt', op: 0 }) +
    txt(450, 386, 'রঙ-নিয়ম: সবুজ = x-চালা key, নীল = strafe, লাল = ঘূর্ণন, বেগুনি = বাঁকা-সম্মিলিত নোট, গোল্ড = case-ফাঁদ', { anchor: 'middle', size: 8.5, fill: '#8b949e' }) +
    txt(450, 440, 'source: yahboom_keyboard.py L16-L64 (banner L16-45, moveBindings L47-58, speedBindings L60-64; scale math L154, L226-228)', { anchor: 'middle', size: 7.8, mono: true, fill: '#6e7681' })
  );
  const q = id => svg.querySelector('#' + id);
  const show = id => q(id).setAttribute('opacity', 1);
  const edge = id => q(id).setAttribute('stroke', '#e3b341');
  host.caption('program চালু হলে প্রথম যা দেখবে — L16-45-এর বানানো <b>মেনু-ব্যানার</b>: কোন key কী করে। আর ব্যানারের পেছনে দুটি dict — আসল নিয়ন্ত্রণের নাক-গন্ডা ওখানেই।');
  host.formula('L16-45 msg banner | L47-58 moveBindings (12 keys) | L60-64 speedBindings (12 keys)');
  await host.sleep(1500);
  edge('tl14-mb'); show('tl14-mbcom'); show('tl14-tup'); show('tl14-t1'); show('tl14-t2'); show('tl14-t3');
  host.caption('L47-এর মন্তব্যটাই চাবি: <code>(forward_back, strafe_left_right, rotate_left_right)</code>। প্রতিটা key একটা তিন-ঘরের tuple — ঘর ১ সামনে-পেছনে, ঘর ২ পাশে সরে (strafe), ঘর ৩ জায়গায় ঘূর্ণন। মান শুধু -1, 0, +1 — দিক, বেগ নয়।');
  host.formula('moveBindings tuple = (x_dir, y_dir, th_dir) with each in {-1, 0, +1}');
  await host.sleep(1700);
  edge('tl14-ki'); show('tl14-kit'); show('tl14-kj'); show('tl14-kjt'); show('tl14-kd'); show('tl14-kdt');
  host.caption('সোজা সম্পর্কগুলো আগে: <code>i</code> = (1,0,0) সামনে, <code>,</code> = (-1,0,0) পেছনে, <code>j</code> = (0,0,1) বাঁদিকে ঘূর্ণন, <code>l</code> = (0,0,-1) ডানদিকে, <code>a</code>/<code>d</code> = (0,±1,0) পাশে সরা। এক-একটা key ঠিক এক-একটা অক্ষ।');
  await host.sleep(1700);
  edge('tl14-ku'); show('tl14-kut'); show('tl14-ko'); show('tl14-kot'); show('tl14-km'); show('tl14-kmt'); show('tl14-kdot'); show('tl14-kdott');
  host.caption('তারপর <b>বাঁকা</b> চারজন — দুই অক্ষ একসাথে: <code>u</code> = (1,1,0) সামনে-বাঁয়ে, <code>o</code> = (1,-1,0) সামনে-ডানে, <code>m</code> = (-1,1,0) পেছনে-বাঁয়ে, <code>.</code> = (-1,-1,0) পেছনে-ডানে। চারটা দিকের কোণাকুণি — একটাও কম নয়।');
  host.formula('diagonals: u (1,1,0) | o (1,-1,0) | m (-1,1,0) | . (-1,-1,0)');
  await host.sleep(1700);
  edge('tl14-case'); show('tl14-caset');
  host.caption('এবার <b>case-এর ফাঁদ</b>: বড় হাতের <code>M</code> আর কমা — দুই-ই (-1,0,0) পেছনে যাওয়া; কিন্তু ছোট হাতের <code>m</code> (-1,1,0) পেছনে-বাঁয়ে! একই অক্ষরের দুই রূপ, দুই আলাদা কাজ। caps-lock ভুল করলে robot অন্য দিকে যাবে — এ নিয়েই সাবধান।');
  await host.sleep(1700);
  edge('tl14-sb'); show('tl14-math'); show('tl14-m1'); show('tl14-m2'); show('tl14-m3'); show('tl14-m4');
  host.caption('tuple-এর মান দিক মাত্র — বেগ বানায় গুণিতক। main loop-এর L226-228: <code>linear.x = speed*x</code>, <code>linear.y = speed*y</code>, <code>angular.z = turn*th</code>। শুরুতে speed 0.2, turn 1.0 — তাই <code>i</code> চাপলে 0.20 m/s সামনে, <code>u</code> চাপলে (0.20, 0.20) কোণাকুণি।');
  host.formula('start speed 0.2 turn 1.0 -> i: (0.20, 0, 0) | u: (0.20, 0.20, 0) rad-in-waiting');
  await host.sleep(1700);
  show('tl14-vx'); show('tl14-vxa'); show('tl14-vxt'); show('tl14-vy'); show('tl14-vya'); show('tl14-vyt'); show('tl14-vz'); show('tl14-vza'); show('tl14-vzt'); show('tl14-rhead'); show('tl14-mec');
  host.caption('robot-এর শরীরে ফিরিয়ে আনি — সবুজ লম্বা তির্যক = x, নীল পাশের = y, লাল বাঁকা = ঘূর্ণন th। y-অক্ষটাই এই chassis-এর বিশেষত্ব: <b>৪টা mecanum চাকা</b> পাশে পাশে সরতে পারে — folder 10-এর পাহারাদার শুধু ঘুরতে পারত, এ চলতে-সরতে-ঘুরতে সব পারে।');
  host.formula('mecanum: vx, vy, wz all real | 12 keys cover all 8 directions + 2 rotations');
  await host.sleep(1700);
  host.caption('দুই dict, ২৪টা entry, একটাও বেজায় না — পরের দুই part-এ দেখব node-এর constructor আর main loop: raw mode-এ key পড়া, arm-এর clamp, আর SPACE-এর emergency stop।');
  await host.sleep(1500);
};
