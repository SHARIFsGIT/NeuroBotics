/* ============ folder-14 anim — steer14 (part 12, v1 layer) ============
   follow_line.py L232-L290. onMouse L232-243: event 1 (left-press) ->
   Track_state='init', select_flags=True, Mouse_XY=(x,y); event 4
   (release) -> select_flags=False, Track_state='mouse'; while held ->
   Roi_init=(minx,miny,maxx,maxy). execute L245-290: L247-252 Joy gate
   (Joy_active -> PID_init once, then RETURN, zero motion); L253-257
   color_radius==0 -> "Not Found" + follow_line_clear_future_done +
   empty Twist() stop; L261 z_Pid=update([(point_x-320)*1.0/16, 0]) with
   Kp 0.05 Ki 0 Kd 0.01; L263/265 img_flip sign; L269 linear.x=0.1
   hardcoded; L270-275 front_warning>10 -> "Obstacles ahead !!!" +
   Twist() stop + buzzer 1; L276-280 clear -> buzzer 0 published 3x
   (for i in range(3)); L282-284 abs(point_x-320)<40 -> angular.z=0.0
   deadzone; L285-286 publish. Canonical frames: F1 260 -> e=-3.75 ->
   -0.1875; F2 300 -> e=-1.25 but |dx|=20<40 -> 0.0; F3 380 -> +0.1875;
   F4 320 -> 0. Unique id prefix sr14- ; no emoji ; no arrow chars in
   stage text ; caption+formula before first await ; static backbone. */


/* ---------- steer14 ---------- */
ANIMS.steer14 = async function (host) {
  const svg = host.setStage(
    txt(450, 26, 'মাউসে একবার টেনে দাও — তারপর চালনা পুরো PID-এর হাতে', { anchor: 'middle', size: 14.5, weight: 600, fill: '#7ee787' }) +
    rrect(30, 44, 330, 322, 8, '#0d1117', '#2a3442') +
    txt(46, 64, 'follow_line.py L232-L290 — onMouse + execute', { size: 10, weight: 700, fill: '#e6edf3' }) +
    rrect(46, 72, 298, 26, 4, '#161b22', '#30363d', ' id="sr14-mouse"') +
    txt(54, 85, 'L232-243  def onMouse(...):  # event 1 / 4', { size: 7.6, mono: true, weight: 700, fill: '#d2a8ff' }) +
    txt(54, 96, 'চাপলে init, টেনে ছাড়লে mouse — ROI তৈরি', { size: 7.2, fill: '#8b949e', id: 'sr14-mouset', op: 0 }) +
    rrect(46, 104, 298, 30, 4, '#161b22', '#ff7b72', ' id="sr14-joy"') +
    txt(54, 118, 'L247-252  if self.Joy_active == True:', { size: 7.6, mono: true, weight: 700, fill: '#ff7b72' }) +
    txt(62, 130, '...PID_init(); return  # joystick-ই বস', { size: 7.4, mono: true, fill: '#ff7b72' }) +
    rrect(46, 138, 298, 28, 4, '#161b22', '#30363d', ' id="sr14-nf"') +
    txt(54, 152, 'L253-257  if color_radius == 0:', { size: 7.6, mono: true, fill: '#e3b341' }) +
    txt(62, 163, '"Not Found" + Twist()  # স্টপ', { size: 7.4, mono: true, fill: '#e3b341', id: 'sr14-nft', op: 0 }) +
    rrect(46, 170, 298, 34, 4, '#161b22', '#7ee787', ' id="sr14-pid"') +
    txt(54, 184, "L261  z_Pid = PID.update(", { size: 7.6, mono: true, weight: 700, fill: '#7ee787' }) +
    txt(62, 196, '  [(point_x-320)*1.0/16, 0])[0]', { size: 7.6, mono: true, weight: 700, fill: '#7ee787' }) +
    txt(356, 184, 'Kp .05', { anchor: 'end', size: 6.8, mono: true, fill: '#6e7681', id: 'sr14-kp', op: 0 }) +
    txt(54, 208, 'L269  twist.linear.x = 0.1  # স্থির', { size: 7.6, mono: true, fill: '#4fc3f7', id: 'sr14-lin', op: 0 }) +
    rrect(46, 216, 298, 28, 4, '#161b22', '#ffb454', ' id="sr14-obs"') +
    txt(54, 230, 'L270-275  if front_warning > 10:', { size: 7.6, mono: true, weight: 700, fill: '#ffb454' }) +
    txt(62, 241, '"Obstacles ahead !!!" Twist() buzzer 1', { size: 7.4, mono: true, fill: '#ffb454', id: 'sr14-obst', op: 0 }) +
    rrect(46, 248, 298, 26, 4, '#161b22', '#30363d', ' id="sr14-clr"') +
    txt(54, 262, 'L276-280  for i in range(3): publish(0)', { size: 7.6, mono: true, fill: '#8b949e', id: 'sr14-clrt', op: 0 }) +
    rrect(46, 278, 298, 28, 4, '#161b22', '#4fc3f7', ' id="sr14-dz"') +
    txt(54, 292, 'L282-284  if abs(point_x-320)<40:', { size: 7.6, mono: true, weight: 700, fill: '#4fc3f7' }) +
    txt(62, 303, 'twist.angular.z = 0.0  # deadzone', { size: 7.4, mono: true, fill: '#4fc3f7', id: 'sr14-dzt', op: 0 }) +
    txt(54, 322, 'L285-286  Joy_active==False হলে publish', { size: 7.4, mono: true, fill: '#c9d1d9', id: 'sr14-pub', op: 0 }) +
    txt(54, 348, 'একটাই ফাংশন — চারটা নিয়ম: gate, হারালে স্টপ,', { size: 7.6, weight: 700, fill: '#e6edf3', id: 'sr14-sum', op: 0 }) +
    txt(54, 360, 'PID-ঘূর্ণন + স্থির গতি, বাধা পেলে স্টপ+বিপ', { size: 7.6, weight: 700, fill: '#e6edf3', id: 'sr14-sum2', op: 0 }) +
    rrect(376, 44, 494, 322, 8, '#111', '#30363d') +
    txt(623, 64, 'ক্যামেরার চোখ — 640 চওড়া, কেন্দ্র 320', { anchor: 'middle', size: 9.6, weight: 700, fill: '#e6edf3' }) +
    rrect(392, 76, 300, 190, 4, '#0d1117', '#30363d') +
    txt(692, 86, '640 x 480', { anchor: 'end', size: 6.4, mono: true, fill: '#6e7681' }) +
    path('M542 80v182', '#4fc3f7', 1, ' id="sr14-cx" opacity="0" stroke-dasharray="5 4"') +
    txt(542, 270, '320 = কেন্দ্র', { anchor: 'middle', size: 6.8, mono: true, fill: '#4fc3f7', id: 'sr14-cxt', op: 0 }) +
    path('M420 200 l30 12 l-6 10 l22 8', '#7ee787', 4, ' id="sr14-line" opacity="0" fill="none" stroke-linecap="round"') +
    rrect(408, 196, 66, 44, 3, 'none', '#d2a8ff', ' id="sr14-roi" opacity="0" stroke-dasharray="4 3"') +
    txt(441, 188, 'ROI — মাউসে টানা বাক্স', { anchor: 'middle', size: 6.6, fill: '#d2a8ff', id: 'sr14-roit', op: 0 }) +
    txt(441, 252, 'Roi_init = (minx, miny, maxx, maxy)', { anchor: 'middle', size: 6.4, mono: true, fill: '#d2a8ff', id: 'sr14-roiL', op: 0 }) +
    path('M532 222a4 4 0 1 0 8 0a4 4 0 1 0 -8 0', '#7ee787', 0, ' fill="#7ee787" id="sr14-pxdot" opacity="0"') +
    txt(536, 240, 'point_x', { anchor: 'middle', size: 6.4, mono: true, fill: '#7ee787', id: 'sr14-pxt', op: 0 }) +
    rrect(704, 76, 158, 190, 4, '#0d1117', '#30363d') +
    txt(783, 92, 'চারটা নমুনা ফ্রেম', { anchor: 'middle', size: 8.2, weight: 700, fill: '#e6edf3' }) +
    rrect(712, 102, 142, 32, 3, '#161b22', '#7ee787', ' id="sr14-f1"') +
    txt(718, 114, 'F1  point_x = 260', { size: 7, mono: true, weight: 700, fill: '#7ee787' }) +
    txt(718, 126, 'e = -3.75 -> z = -0.1875', { size: 6.8, mono: true, fill: '#7ee787', id: 'sr14-f1t', op: 0 }) +
    rrect(712, 138, 142, 32, 3, '#161b22', '#4fc3f7', ' id="sr14-f2"') +
    txt(718, 150, 'F2  point_x = 300', { size: 7, mono: true, weight: 700, fill: '#4fc3f7' }) +
    txt(718, 162, 'dx 20 < 40 -> z = 0.0', { size: 6.8, mono: true, fill: '#4fc3f7', id: 'sr14-f2t', op: 0 }) +
    rrect(712, 174, 142, 32, 3, '#161b22', '#7ee787', ' id="sr14-f3"') +
    txt(718, 186, 'F3  point_x = 380', { size: 7, mono: true, weight: 700, fill: '#7ee787' }) +
    txt(718, 198, 'e = +3.75 -> z = +0.1875', { size: 6.8, mono: true, fill: '#7ee787', id: 'sr14-f3t', op: 0 }) +
    rrect(712, 210, 142, 32, 3, '#161b22', '#4fc3f7', ' id="sr14-f4"') +
    txt(718, 222, 'F4  point_x = 320', { size: 7, mono: true, weight: 700, fill: '#4fc3f7' }) +
    txt(718, 234, 'e = 0 -> z = 0.0', { size: 6.8, mono: true, fill: '#4fc3f7', id: 'sr14-f4t', op: 0 }) +
    txt(783, 258, 'linear.x = 0.1 সর্বদা', { anchor: 'middle', size: 7, mono: true, weight: 700, fill: '#ffb454', id: 'sr14-linx', op: 0 }) +
    rrect(392, 274, 470, 26, 4, '#161b22', '#30363d', ' id="sr14-math"') +
    txt(627, 290, 'e = (point_x - 320) / 16 ;  z_Pid = 0.05 * e  (Ki = 0, Kd = 0.01)', { anchor: 'middle', size: 7.6, mono: true, weight: 700, fill: '#e6edf3', id: 'sr14-matht', op: 0 }) +
    rrect(392, 306, 470, 46, 4, '#0d1117', '#30363d', ' id="sr14-bz"') +
    path('M402 329a8 8 0 1 0 16 0a8 8 0 1 0 -16 0', '#ffb454', 1.4, ' fill="#30363d" id="sr14-bzc"') +
    txt(410, 355, 'buzzer', { anchor: 'middle', size: 6.2, fill: '#8b949e' }) +
    txt(430, 322, 'front_warning > 10: স্টপ + Beep(1)', { size: 7.2, mono: true, weight: 700, fill: '#ffb454', id: 'sr14-bz1', op: 0 }) +
    txt(430, 336, 'পথ খোলা: Beep(0) তিনবার প্রকাশ', { size: 7.2, mono: true, fill: '#8b949e', id: 'sr14-bz0', op: 0 }) +
    txt(430, 348, 'Joy_active হলে execute-ই ফিরে যায়', { size: 7, fill: '#ff7b72', id: 'sr14-bzj', op: 0 }) +
    txt(450, 386, 'রঙ-নিয়ম: সবুজ = PID, নীল = deadzone/কেন্দ্র, হলুদ = বাধা, বেগুনি = ROI, লাল = Joy-gate', { anchor: 'middle', size: 8.5, fill: '#8b949e' }) +
    txt(450, 440, 'source: follow_line.py L232-L290 (onMouse L232-243, Joy gate L247-252, Not Found L253-257, PID L261-269, obstacle L270-280, deadzone L282-288)', { anchor: 'middle', size: 7.8, mono: true, fill: '#6e7681' })
  );
  const q = id => svg.querySelector('#' + id);
  const show = id => q(id).setAttribute('opacity', 1);
  const edge = id => q(id).setAttribute('stroke', '#e3b341');
  host.caption('রেখা অনুসরণের চালনা-ইঞ্জিন এই দুই ফাংশনেই বাঁধা। শুরু <code>onMouse</code> (L232): প্রথম ফ্রেমে মাউস চেপে রেখাটার ওপর বাক্স টানো — event 1 মানে টানা শুরু, event 4 মানে ছেড়ে দেওয়া।');
  host.formula('onMouse: press -> Track_state=init + ROI grows ; release -> Track_state=mouse');
  await host.sleep(1500);
  edge('sr14-mouse'); show('sr14-mouset'); show('sr14-roi'); show('sr14-roit'); show('sr14-roiL');
  host.caption('টানা বাক্সটাই <b>ROI</b> — (minx, miny, maxx, maxy)। এর ভেতরের রঙই robot-এর লক্ষ্য; সেখান থেকে আসে <code>point_x</code> — রেখাটা ফ্রেমের কোন কলামে পড়ছে, সেটাই তার সংখ্যা।');
  await host.sleep(1600);
  edge('sr14-joy');
  host.caption('এবার <code>execute</code>-এর প্রথম দরজা (L247): <code>Joy_active</code> সত্য হলে প্রথমবার <code>PID_init</code> সেট করে সোজা <b>return</b> — কোনো গতি নেই। joystick হাতে থাকলে keyboard/রেখা-র কেউই চালাবে না; এক সময়ে এক মালিক।');
  await host.sleep(1700);
  edge('sr14-pid'); show('sr14-kp'); show('sr14-lin'); show('sr14-cx'); show('sr14-cxt'); show('sr14-pxdot'); show('sr14-pxt'); show('sr14-math'); show('sr14-matht');
  host.caption('চালনার মূল গণিত (L261): ফ্রেম 640 চওড়া, কেন্দ্র 320। ভুল <code>e = (point_x − 320) / 16</code>, ঘূর্ণন <code>z = 0.05 × e</code>। সামনে যাওয়ার গতি কড়া নয় — L269-এ <b>0.1 লেখা-বাঁধা</b>; PID শুধু বাঁ-ডান ঠিক করে, জোর ঠিক করে না।');
  host.formula('e = (point_x-320)/16 ; z = 0.05*e ; linear.x = 0.1 (hardcoded, not PID)');
  await host.sleep(1800);
  edge('sr14-f1'); show('sr14-f1t');
  host.caption('ফ্রেম F1: রেখা <code>point_x = 260</code>-এ — কেন্দ্রের ৬০ পিক্সেল বাঁয়ে। e = −60/16 = −3.75, তাই z = −0.1875: robot বাঁদিকে বাঁক নেবে, রেখার দিকে ফিরবে।');
  await host.sleep(1600);
  edge('sr14-f2'); show('sr14-f2t'); edge('sr14-f4'); show('sr14-f4t');
  host.caption('কিন্তু F2 (point_x 300) আর F4 (320)? <b>deadzone</b> (L282): |point_x − 320| < 40 হলে angular.z জোর করে 0.0। ২০ পিক্সেলের এদিক-ওদিক সরা মানে "যথেষ্ট সোজা" — ছোটখাটো দোলায় চাকা নাড়ানো বৃথা।');
  host.formula('deadzone: abs(point_x-320) < 40 -> angular.z = 0.0 (dead-calm straight)');
  await host.sleep(1800);
  edge('sr14-f3'); show('sr14-f3t'); show('sr14-linx');
  host.caption('F3: রেখা 380-এ — ৬০ ডানে। e = +3.75, z = +0.1875, ডানদিকে বাঁক। আর সব ফ্রেমে linear.x = 0.1 অবিচল — ধীরে, মেপে মেপে এগোনো।');
  await host.sleep(1600);
  edge('sr14-nf'); show('sr14-nft');
  host.caption('যদি রেখাই হারিয়ে যায়? <code>color_radius == 0</code> — "Not Found" ছাপো, <code>follow_line_clear_future_done</code> জানাও, আর <b>খালি Twist()</b> প্রকাশ: শূন্য গতি, দাঁড়িয়ে থাকো। অনুমান করে চলা নয়।');
  await host.sleep(1700);
  edge('sr14-obs'); show('sr14-obst'); show('sr14-bz1');
  host.caption('সামনে বাধা ধরা পড়লে (L270): <code>front_warning > 10</code> — "Obstacles ahead !!!", Twist() স্টপ, আর buzzer-এ <b>1</b>: তীব্র সতর্ক-বিপ। PID-এর হিসাব যা-ই বলুক, বাধার সামনে সব বাতিল।');
  await host.sleep(1700);
  edge('sr14-clr'); show('sr14-clrt'); show('sr14-bz0'); show('sr14-bzj'); show('sr14-pub');
  host.caption('পথ খুললে বিপ বন্ধের নিয়মও মজার — 0 একবার নয়, <b>তিনবার</b> প্রকাশ (L279)। শেষ দরজা: Joy_active না হলেই twist বেরোয়। পরের part-এ এই ফাংশনের মালিক Track_state মেশিন — identify, tracking, AprilTag, আর বাধা সরানোর আর্ম।');
  await host.sleep(1800);
};
