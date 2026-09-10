/* ============ folder-14 anim — states14 (part 13, v1 layer) ============
   follow_line.py L291-L380, def process(). Keys L297-301: action 32
   (SPACE) -> 'tracking'; 'i' -> 'identify'; 'r' -> Reset(); 'q' ->
   cancel(). 'init' L302-314: namedWindow + setMouseCallback(onMouse);
   drag draws blue line + green rect; nonzero ROI -> Roi_hsv ->
   hsv_range, dyn_update=True. 'identify' L315-318: read_HSV from file,
   else back to 'init'. L319-333: line_follow -> circle; dyn_update ->
   write_HSV + set_parameters Hmin..Vmax (6 dynamic params). 'tracking'
   L334-336: len(circle)!=0 -> Thread(execute, circle[0], circle[2]).
   AprilTag pivot L341-345: len(tags)>0 and state!='Remove' -> state
   'identify', Twist() stop, "Find the apriltag.", state='Remove'.
   'Remove' L346-378: center=tags[0].center; (|cx-320|>10 or
   |cy-400|>10) and move_flag -> "adjusting." + remove_obstacle;
   |cx-320|<10 and |cy-400|<10 -> pubVel(0,0), "start crawling.",
   sleep(3), c_dist=depth[cy,cx]/1000; c_dist!=0 and pubPos_flag ->
   AprilTagInfo(id,x,y,z), vx/vy from corners[0]-[1], joint5 =
   compute_joint5(vx,vy), pos_info_pub.publish + TargetJoint5_pub.
   publish(joint5) TWICE L375-376 (source quirk); else "Invalid
   distance.". Unique id prefix sd14- ; no emoji ; no arrow chars in
   stage text ; caption+formula before first await ; static backbone. */


/* ---------- states14 ---------- */
ANIMS.states14 = async function (host) {
  const svg = host.setStage(
    txt(450, 26, 'একটাই স্টেট-মেশিন — রেখা খোঁজা, রেখা ধরা, আর বাধা সরানো', { anchor: 'middle', size: 14.5, weight: 600, fill: '#d2a8ff' }) +
    rrect(30, 44, 330, 322, 8, '#0d1117', '#2a3442') +
    txt(46, 64, 'follow_line.py L291-L380 — process() + Track_state', { size: 10, weight: 700, fill: '#e6edf3' }) +
    rrect(46, 72, 298, 26, 4, '#161b22', '#30363d', ' id="sd14-keys"') +
    txt(54, 85, 'L297-301  SPACE=i রেখা | r=রিসেট | q=বাতিল', { size: 7.6, mono: true, weight: 700, fill: '#4fc3f7' }) +
    txt(54, 96, 'action মানে key-এর ASCII সংখ্যা (SPACE = 32)', { size: 7.2, fill: '#8b949e', id: 'sd14-keyst', op: 0 }) +
    rrect(46, 104, 298, 28, 4, '#161b22', '#7ee787', ' id="sd14-init"') +
    txt(54, 118, "L302-310  'init': window + onMouse", { size: 7.6, mono: true, weight: 700, fill: '#7ee787' }) +
    txt(62, 130, 'ROI টানা -> Roi_hsv -> hsv_range', { size: 7.4, mono: true, fill: '#7ee787', id: 'sd14-initt', op: 0 }) +
    rrect(46, 136, 298, 28, 4, '#161b22', '#30363d', ' id="sd14-iden"') +
    txt(54, 150, "L315-318  'identify': read_HSV(file)", { size: 7.6, mono: true, fill: '#d2a8ff' }) +
    txt(62, 161, 'ফাইল না থাকলে আবার init', { size: 7.3, fill: '#d2a8ff', id: 'sd14-ident', op: 0 }) +
    rrect(46, 168, 298, 28, 4, '#161b22', '#7ee787', ' id="sd14-trk"') +
    txt(54, 182, "L334-336  'tracking': circle পেলে", { size: 7.6, mono: true, weight: 700, fill: '#7ee787' }) +
    txt(62, 193, 'Thread(execute(circle[0], circle[2]))', { size: 7.4, mono: true, fill: '#7ee787', id: 'sd14-trkt', op: 0 }) +
    rrect(46, 200, 298, 30, 4, '#161b22', '#ffb454', ' id="sd14-tag"') +
    txt(54, 214, 'L341-345  if len(self.tags)>0 ...:', { size: 7.6, mono: true, weight: 700, fill: '#ffb454' }) +
    txt(62, 225, '"Find the apriltag." -> Remove', { size: 7.4, mono: true, fill: '#ffb454', id: 'sd14-tagt', op: 0 }) +
    rrect(46, 230, 298, 30, 4, '#161b22', '#30363d', ' id="sd14-adj"') +
    txt(54, 244, 'L350-352  (|cx-320|>10 or |cy-400|>10):', { size: 7.4, mono: true, weight: 700, fill: '#e3b341' }) +
    txt(62, 255, '"adjusting." -> remove_obstacle(cx, cy)', { size: 7.3, mono: true, fill: '#e3b341', id: 'sd14-adjt', op: 0 }) +
    rrect(46, 262, 298, 44, 4, '#161b22', '#4fc3f7', ' id="sd14-cen"') +
    txt(54, 276, 'L353-357  |cx-320|<10 and |cy-400|<10:', { size: 7.4, mono: true, weight: 700, fill: '#4fc3f7' }) +
    txt(62, 287, 'pubVel(0,0) "start crawling." sleep(3)', { size: 7.3, mono: true, fill: '#4fc3f7', id: 'sd14-cent', op: 0 }) +
    txt(62, 298, 'c_dist = depth[cy,cx] / 1000', { size: 7.3, mono: true, fill: '#4fc3f7', id: 'sd14-cend', op: 0 }) +
    rrect(46, 310, 298, 34, 4, '#161b22', '#ff7b72', ' id="sd14-j5"') +
    txt(54, 324, 'L374-376  pos_info_pub + joint5 প্রকাশ', { size: 7.4, mono: true, weight: 700, fill: '#ff7b72' }) +
    txt(62, 336, 'TargetJoint5_pub.publish - এক নয়, দুইবার!', { size: 7.3, mono: true, weight: 700, fill: '#ff7b72', id: 'sd14-j5t', op: 0 }) +
    rrect(376, 44, 494, 322, 8, '#111', '#30363d') +
    txt(623, 64, 'Track_state-এর মানচিত্র — কে কখন চালায়', { anchor: 'middle', size: 9.6, weight: 700, fill: '#e6edf3' }) +
    rrect(396, 84, 116, 40, 20, '#161b22', '#7ee787', ' id="sd14-s1"') +
    txt(454, 106, 'init', { anchor: 'middle', size: 10, mono: true, weight: 700, fill: '#7ee787' }) +
    txt(454, 140, 'ROI টানো', { anchor: 'middle', size: 6.6, fill: '#8b949e', id: 'sd14-s1t', op: 0 }) +
    rrect(536, 84, 116, 40, 20, '#161b22', '#d2a8ff', ' id="sd14-s2"') +
    txt(594, 106, 'identify', { anchor: 'middle', size: 10, mono: true, weight: 700, fill: '#d2a8ff' }) +
    txt(594, 140, 'HSV ফাইল পড়া', { anchor: 'middle', size: 6.6, fill: '#8b949e', id: 'sd14-s2t', op: 0 }) +
    rrect(676, 84, 116, 40, 20, '#161b22', '#7ee787', ' id="sd14-s3"') +
    txt(734, 106, 'tracking', { anchor: 'middle', size: 10, mono: true, weight: 700, fill: '#7ee787' }) +
    txt(734, 140, 'রেখা ধরে চালনা', { anchor: 'middle', size: 6.6, fill: '#8b949e', id: 'sd14-s3t', op: 0 }) +
    path('M512 104h20', '#8b949e', 1.6, ' id="sd14-e1" opacity="0"') +
    path('M532 104l-7-3v6z', '#8b949e', 0, ' fill="#8b949e" id="sd14-e1a" opacity="0"') +
    path('M652 104h20', '#8b949e', 1.6, ' id="sd14-e2" opacity="0"') +
    path('M672 104l-7-3v6z', '#8b949e', 0, ' fill="#8b949e" id="sd14-e2a" opacity="0"') +
    rrect(396, 156, 396, 34, 4, '#161b22', '#ffb454', ' id="sd14-piv" opacity="0"') +
    txt(594, 170, 'L341: AprilTag দেখা মাত্র — যে-ই স্টেটে থাক, রেখার খেলা থামে', { anchor: 'middle', size: 7.4, weight: 700, fill: '#ffb454', id: 'sd14-pivt', op: 0 }) +
    txt(594, 182, 'Twist() স্টপ + "Find the apriltag." + স্টেট = Remove', { anchor: 'middle', size: 7, fill: '#ffb454', id: 'sd14-pivt2', op: 0 }) +
    path('M594 190v14', '#ffb454', 1.6, ' id="sd14-pvar" opacity="0"') +
    path('M594 204l-3-7h6z', '#ffb454', 0, ' fill="#ffb454" id="sd14-pvara" opacity="0"') +
    rrect(488, 208, 212, 36, 18, '#161b22', '#e3b341', ' id="sd14-s4" opacity="0"') +
    txt(594, 230, 'Remove', { anchor: 'middle', size: 10, mono: true, weight: 700, fill: '#e3b341' }) +
    rrect(392, 254, 220, 104, 4, '#0d1117', '#4fc3f7', ' id="sd14-cam"') +
    txt(502, 268, 'ক্যামেরা ফ্রেম - কেন্দ্র (320, 400)', { anchor: 'middle', size: 7, weight: 700, fill: '#e6edf3' }) +
    path('M478 288h48', '#4fc3f7', 1, ' opacity="0.7"') +
    path('M502 274v28', '#4fc3f7', 1, ' opacity="0.7"') +
    rrect(492, 282, 20, 20, 2, 'none', '#4fc3f7', ' opacity="0.45" stroke-dasharray="3 2"') +
    rrect(430, 300, 28, 28, 2, '#21262d', '#ffb454', ' id="sd14-tagbox" opacity="0"') +
    txt(444, 318, 'tag', { anchor: 'middle', size: 6.4, mono: true, weight: 700, fill: '#ffb454' }) +
    txt(444, 340, 'adjusting. (L351)', { anchor: 'middle', size: 6.4, mono: true, fill: '#e3b341', id: 'sd14-adjL', op: 0 }) +
    txt(560, 348, 'ট্যাগ বাক্সে বসলে (±10):', { size: 7, weight: 700, fill: '#4fc3f7', id: 'sd14-cenL', op: 0 }) +
    txt(560, 360, '"start crawling." + ৩ সেকেন্ড থেমে', { size: 6.8, fill: '#4fc3f7', id: 'sd14-cenL2', op: 0 }) +
    txt(560, 372, 'depth / 1000 = মিটার দূরত্ব', { size: 6.8, mono: true, fill: '#4fc3f7', id: 'sd14-cenL3', op: 0 }) +
    rrect(624, 254, 238, 104, 4, '#0d1117', '#30363d', ' id="sd14-out"') +
    txt(743, 268, 'স্থির হওয়ার পর বেরোয় (L361-376)', { anchor: 'middle', size: 7, weight: 700, fill: '#e6edf3' }) +
    txt(632, 284, 'pos_info_pub: id, x, y, z=c_dist', { size: 6.8, mono: true, fill: '#7ee787', id: 'sd14-o1', op: 0 }) +
    txt(632, 298, 'joint5 = compute_joint5(vx, vy)', { size: 6.8, mono: true, fill: '#d2a8ff', id: 'sd14-o2', op: 0 }) +
    txt(632, 312, 'TargetJoint5_pub.publish - দুইবার', { size: 6.8, mono: true, weight: 700, fill: '#ff7b72', id: 'sd14-o3', op: 0 }) +
    txt(632, 328, 'দ্বিতীয়বারটা redundancy - ক্ষতি নেই,', { size: 6.6, fill: '#8b949e', id: 'sd14-o4', op: 0 }) +
    txt(632, 340, 'কিন্তু ডেটার ওপর কোনো ভূমিকাও নেই', { size: 6.6, fill: '#8b949e', id: 'sd14-o5', op: 0 }) +
    txt(632, 354, 'c_dist==0 হলে "Invalid distance."', { size: 6.6, mono: true, fill: '#e3b341', id: 'sd14-o6', op: 0 }) +
    txt(450, 386, 'রঙ-নিয়ম: সবুজ = চালু স্টেট, বেগুনি = identify, হলুদ = AprilTag পিভট, নীল = কেন্দ্রীভবন, লাল = দুইবার-প্রকাশ', { anchor: 'middle', size: 8.5, fill: '#8b949e' }) +
    txt(450, 440, 'source: follow_line.py L291-L380 (keys L297-301, init L302-314, identify L315-318, line_follow L319-333, tracking L334-336, tag pivot L341-345, Remove L346-378)', { anchor: 'middle', size: 7.8, mono: true, fill: '#6e7681' })
  );
  const q = id => svg.querySelector('#' + id);
  const show = id => q(id).setAttribute('opacity', 1);
  const edge = id => q(id).setAttribute('stroke', '#e3b341');
  host.caption('একটা ছবি, একটা key-press — আর তার ওপর দাঁড়িয়ে পুরো <b>স্টেট-মেশিন</b>। <code>process()</code> প্রতি ফ্রেমে ডাকা হয়, কিন্তু কে কাজ করবে ঠিক করে <code>Track_state</code> স্ট্রিংটা — init, identify, tracking, আর শেষে Remove।');
  host.formula("Track_state in {'init', 'identify', 'tracking', 'Remove'} ; action = ASCII of key press");
  await host.sleep(1500);
  edge('sd14-keys'); show('sd14-keyst');
  host.caption('দরজার চাবি L297-301: <code>SPACE</code> (ASCII 32) মানে tracking শুরু, <code>i</code> মানে identify, <code>r</code> সব রিসেট, <code>q</code> বাতিল। ছোট্ট সংখ্যার তুলনা — অথচ পুরো আচরণ বদলে দেয়।');
  await host.sleep(1600);
  edge('sd14-init'); show('sd14-s1'); show('sd14-s1t'); show('sd14-s2t'); show('sd14-initt');
  host.caption('<b>init</b> (L302): window খোলা, mouse callback বসানো। রেখার ওপর বাক্স টানলেই <code>Roi_hsv</code> সেই রঙের H-S-V সীমা বের করে — robot এখন জানে "কোন রঙটা আমার রেখা"। মানুষ একবার দেখিয়ে দেয়, মেশিন বাকিটা নেয়।');
  await host.sleep(1700);
  edge('sd14-iden'); show('sd14-s2'); show('sd14-ident');
  host.caption('<b>identify</b> (L315): সেই সীমা ফাইল থেকে ফের পড়া — আগের চালানোর HSV মনে রাখা থাকে, প্রতিবার নতুন করে টানতে হয় না। ফাইল না পেলে রাস্তা একটাই: ফিরে যাও init-এ।');
  host.formula("identify: hsv_range = read_HSV(file) ; no file -> back to 'init'");
  await host.sleep(1600);
  edge('sd14-trk'); show('sd14-s3'); show('sd14-s3t'); show('sd14-trkt'); show('sd14-e1'); show('sd14-e1a'); show('sd14-e2'); show('sd14-e2a');
  host.caption('<b>tracking</b> (L334): <code>line_follow</code> রেখার অবস্থান দেয় <code>circle</code>-এ, আর সেটা খালি না হলে নতুন <b>থ্রেডে</b> <code>execute(circle[0], circle[2])</code> ছোটে — আলাদা থ্রেড মানে দেখার কাজ আর চালার কাজ একসাথে চলে, একজন আরেকজনকে আটকায় না।');
  await host.sleep(1800);
  edge('sd14-tag'); show('sd14-piv'); show('sd14-pivt'); show('sd14-pivt2'); show('sd14-pvar'); show('sd14-pvara'); show('sd14-s4');
  host.caption('এখানেই নাটকের মোড় (L341): ক্যামেরায় <b>AprilTag</b> ধরা পড়লে যে-ই স্টেটে থাকুক — রেখার খেলা সেখানেই থামে। খালি Twist() স্টপ, "Find the apriltag." ছাপো, স্টেট = <b>Remove</b>। রেখা মানে গন্তব্য, ট্যাগ মানে মাঝপথের বাধা — বাধার অগ্রাধিকার বেশি।');
  host.formula('len(tags)>0 and state!="Remove" -> stop + "Find the apriltag." -> state="Remove"');
  await host.sleep(1900);
  edge('sd14-adj'); show('sd14-cam'); show('sd14-tagbox'); show('sd14-adjL');
  host.caption('<b>Remove</b> স্টেটের প্রথম কাজ (L350): ট্যাগের কেন্দ্র <code>(center_x, center_y)</code> ফ্রেমের লক্ষ্য-বিন্দু <code>(320, 400)</code>-এর তুলনায় বেশি সরে থাকলে (x-এ ±10 <b>বা</b> y-তে ±10) — "adjusting." ছাপো, <code>remove_obstacle(cx, cy)</code> ডাকো: robot নিজেকে ঠেলে ট্যাগের সামনে সোজা হয়ে দাঁড়ায়।');
  await host.sleep(1800);
  edge('sd14-cen'); show('sd14-cenL'); show('sd14-cenL2'); show('sd14-cenL3'); show('sd14-cent'); show('sd14-cend');
  host.caption('ট্যাগ বাক্সের মধ্যে বসেছে — <b>দুই অক্ষেই ±১০-এর ভেতর</b>? তাহলে থামো (pubVel 0,0), "start crawling." ছাপো, ঠিক ৩ সেকেন্ড অপেক্ষা — আর depth ক্যামেরা থেকে <code>depth[cy, cx] / 1000</code>: মিলিমিটার থেকে মিটার।');
  host.formula('centered: |cx-320|<10 AND |cy-400|<10 -> stop, sleep(3), c_dist = depth/1000 (mm to m)');
  await host.sleep(1800);
  edge('sd14-j5'); show('sd14-out'); show('sd14-o1'); show('sd14-o2'); show('sd14-o3'); show('sd14-o4'); show('sd14-o5'); show('sd14-o6'); show('sd14-j5t');
  host.caption('তারপর ফল দুই পথে বেরোয় (L361-376): <code>pos_info_pub</code>-এ ট্যাগের পরিচয়-দূরত্ব, আর ট্যাগের কোণ থেকে হিসাব করা <code>joint5</code> সোজা হাতের কব্জিতে। খেয়াল করো — <b>একই publish লাইন পরপর দুইবার</b> (L375-376)। সতর্ক হওয়ার লেখা নয়, source-এর আসল চেহারা; দ্বিতীয়টা নিরীহ, শুধু বাহুল্য। আর দূরত্ব ০ উঠলে সব বাতিল — "Invalid distance."।');
  await host.sleep(2000);
  host.caption('এক নজরে: key-press স্টেট বদলায়, HSV রঙ চেনায়, থ্রেড চালায়, AprilTag সব কেড়ে নেয়, আর দুইবার-প্রকাশিত joint5 বাধা তুলতে হাত পাঠায়। পরের part: শেষ ধাপ — বানানো মানচিত্র ডিস্কে লিখে রাখা।');
  await host.sleep(1500);
};
