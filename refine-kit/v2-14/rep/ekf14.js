/* ============ folder-14 anim — ekf14 (part 3, v1 layer) ============
   gmapping.launch.py L51-L94. imu Node L53-62: package imu_filter_madgw-
   ick-style vendor node (name per source L61-62; internals illustrative)
   with remappings=[('/imu','/imu/data_raw')] at L60 — a topic RENAME
   bridge: node subscribes /imu, driver publishes /imu/data_raw (or vice
   versa per source order; the remap pair is verbatim). L56-59 comment
   block = source's own "renaming bridge" metaphor. FINAL LIST L66-93:
   return LaunchDescription([ merger include (L69-71), filter include
   (L74-76), imu Node bare (L79), ekf include (L82-84), gmapping include
   (L90-92) ]) — FIVE entries; L85-89 comments incl. the five-listeners
   metaphor. Run phase fires all five: merger+filter -> /scan ; imu ->
   /imu/data_raw ; ekf fuses imu+odom -> odom ; gmapping eats /scan +
   odom -> /map. Node-vs-Include distinction: imu is an inline Node (no
   launch file), the rest four are includes. Unique id prefix ek14- ;
   no emoji ; no arrow chars in stage text ; caption+formula before the
   first await ; static backbone. */


/* ---------- ekf14 ---------- */
ANIMS.ekf14 = async function (host) {
  const svg = host.setStage(
    txt(450, 26, 'imu-র নাম-বদল আর পাঁচ entry-র তালিকা — তারপর পাঁচজনের উদ্বোধন', { anchor: 'middle', size: 14.5, weight: 600, fill: '#ffb454' }) +
    rrect(30, 44, 330, 322, 8, '#0d1117', '#2a3442') +
    txt(46, 64, 'L53-L62 — imu Node, inline', { size: 10, weight: 700, fill: '#e6edf3' }) +
    rrect(46, 72, 298, 56, 4, '#161b22', '#30363d', ' id="ek14-imu"') +
    txt(54, 86, 'Node(', { size: 8.2, mono: true, weight: 700, fill: '#e6edf3' }) +
    txt(62, 98, "package=..., executable=...,", { size: 7.6, mono: true, fill: '#8b949e' }) +
    txt(62, 110, "remappings=[('/imu', '/imu/data_raw')],", { size: 7.6, mono: true, weight: 700, fill: '#ff7b72' }) +
    txt(62, 122, "name='imu_filter')", { size: 7.6, mono: true, fill: '#8b949e' }) +
    txt(54, 142, 'L60-এর remap: নাম-বদলের সেতু', { size: 7.8, weight: 700, fill: '#e3b341', id: 'ek14-rm', op: 0 }) +
    txt(54, 155, "node যা চায় '/imu' — সেটা আসবে '/imu/data_raw' থেকে", { size: 7.2, fill: '#8b949e', id: 'ek14-rm2', op: 0 }) +
    txt(46, 178, 'L66-L93 — FINAL LIST, পাঁচ entry', { size: 10, weight: 700, fill: '#e6edf3' }) +
    rrect(46, 186, 298, 22, 4, '#161b22', '#ffb454', ' id="ek14-e1" opacity="0"') +
    txt(54, 200, '1. merger include (L69-71)', { size: 7.8, mono: true, weight: 700, fill: '#ffb454', id: 'ek14-e1t', op: 0 }) +
    rrect(46, 212, 298, 22, 4, '#161b22', '#d2a8ff', ' id="ek14-e2" opacity="0"') +
    txt(54, 226, '2. filter include (L74-76)', { size: 7.8, mono: true, weight: 700, fill: '#d2a8ff', id: 'ek14-e2t', op: 0 }) +
    rrect(46, 238, 298, 22, 4, '#161b22', '#ff7b72', ' id="ek14-e3" opacity="0"') +
    txt(54, 252, '3. imu Node — inline, include নয় (L79)', { size: 7.8, mono: true, weight: 700, fill: '#ff7b72', id: 'ek14-e3t', op: 0 }) +
    rrect(46, 264, 298, 22, 4, '#161b22', '#4fc3f7', ' id="ek14-e4" opacity="0"') +
    txt(54, 278, '4. ekf include (L82-84)', { size: 7.8, mono: true, weight: 700, fill: '#4fc3f7', id: 'ek14-e4t', op: 0 }) +
    rrect(46, 290, 298, 22, 4, '#161b22', '#7ee787', ' id="ek14-e5" opacity="0"') +
    txt(54, 304, '5. gmapping include (L90-92)', { size: 7.8, mono: true, weight: 700, fill: '#7ee787', id: 'ek14-e5t', op: 0 }) +
    txt(46, 330, 'return LaunchDescription([ ... ])', { size: 8, mono: true, fill: '#c9d1d9' }) +
    txt(46, 344, 'শরীর চলা শেষ — এখন চালুর পালা (run phase)', { size: 7.4, fill: '#8b949e', id: 'ek14-run', op: 0 }) +
    rrect(376, 44, 494, 322, 8, '#111', '#30363d') +
    txt(623, 64, 'RUN PHASE — পাঁচজন একে একে জাগে, তারপর হাতে হাত মেলায়', { anchor: 'middle', size: 9.6, weight: 700, fill: '#e6edf3' }) +
    rrect(392, 76, 150, 30, 4, '#161b22', '#ffb454', ' id="ek14-n1" opacity="0"') +
    txt(467, 95, 'laserscan merger', { anchor: 'middle', size: 8, mono: true, weight: 700, fill: '#ffb454', id: 'ek14-n1t', op: 0 }) +
    rrect(556, 76, 150, 30, 4, '#161b22', '#d2a8ff', ' id="ek14-n2" opacity="0"') +
    txt(631, 95, 'laser_filter_node', { anchor: 'middle', size: 8, mono: true, weight: 700, fill: '#d2a8ff', id: 'ek14-n2t', op: 0 }) +
    rrect(720, 76, 134, 30, 4, '#161b22', '#ff7b72', ' id="ek14-n3" opacity="0"') +
    txt(787, 95, 'imu node', { anchor: 'middle', size: 8, mono: true, weight: 700, fill: '#ff7b72', id: 'ek14-n3t', op: 0 }) +
    rrect(392, 124, 200, 30, 4, '#161b22', '#4fc3f7', ' id="ek14-n4" opacity="0"') +
    txt(492, 143, 'ekf (robot_localization)', { anchor: 'middle', size: 8, mono: true, weight: 700, fill: '#4fc3f7', id: 'ek14-n4t', op: 0 }) +
    rrect(606, 124, 248, 30, 4, '#161b22', '#7ee787', ' id="ek14-n5" opacity="0"') +
    txt(730, 143, 'slam_gmapping', { anchor: 'middle', size: 8, mono: true, weight: 700, fill: '#7ee787', id: 'ek14-n5t', op: 0 }) +
    path('M542 91h10', '#8b949e', 1.4, ' id="ek14-l12" opacity="0"') +
    path('M542 150h60', '#8b949e', 1.4, ' id="ek14-l45" opacity="0"') +
    txt(467, 122, 'front raw + rear raw', { anchor: 'middle', size: 6.8, fill: '#8b949e', id: 'ek14-rawin', op: 0 }) +
    txt(631, 122, 'মিশ্রিনি scan', { anchor: 'middle', size: 6.8, fill: '#8b949e', id: 'ek14-mid', op: 0 }) +
    rrect(392, 168, 462, 26, 4, '#0d1117', '#7ee787', ' id="ek14-scanb" opacity="0"') +
    txt(623, 185, '/scan — filter করা, পরিষ্কার 360-deg ring', { anchor: 'middle', size: 8, mono: true, weight: 700, fill: '#7ee787', id: 'ek14-scan', op: 0 }) +
    txt(787, 122, '/imu/data_raw', { anchor: 'middle', size: 6.8, mono: true, fill: '#ff7b72', id: 'ek14-imut', op: 0 }) +
    txt(492, 170, 'imu + wheel odom', { anchor: 'middle', size: 6.8, fill: '#8b949e', id: 'ek14-ekfin', op: 0 }) +
    rrect(392, 204, 462, 26, 4, '#0d1117', '#4fc3f7', ' id="ek14-odomb" opacity="0"') +
    txt(623, 221, '/odom — EKF-এর গলিত অবস্থান-গতি (illustrative ভেতরের হিসাব)', { anchor: 'middle', size: 8, mono: true, weight: 700, fill: '#4fc3f7', id: 'ek14-odom', op: 0 }) +
    path('M730 160v8', '#7ee787', 1.4, ' id="ek14-s2g" opacity="0"') +
    path('M492 160v8', '#4fc3f7', 1.4, ' id="ek14-o2g" opacity="0"') +
    rrect(392, 236, 462, 40, 4, '#161b22', '#7ee787', ' id="ek14-mapb" opacity="0"') +
    txt(623, 252, 'gmapping: /scan দিয়ে দেয়াল আঁকে, /odom দিয়ে নিজের পা-চিহ্ন', { anchor: 'middle', size: 7.6, weight: 700, fill: '#7ee787', id: 'ek14-mapa', op: 0 }) +
    txt(623, 265, 'particle filter + scan matching (vendor, illustrative)', { anchor: 'middle', size: 7, fill: '#8b949e', id: 'ek14-mapb2', op: 0 }) +
    rrect(392, 284, 462, 34, 4, '#0d1117', '#e3b341', ' id="ek14-mapo" opacity="0"') +
    txt(623, 299, '/map — occupancy grid, প্রতি সেকেন্ডে বাড়তে থাকা', { anchor: 'middle', size: 8, mono: true, weight: 700, fill: '#e3b341', id: 'ek14-mapot', op: 0 }) +
    txt(623, 311, 'এটাই যে সম্পদ save_map পরে ফাইলে তুলে রাখবে (L15, README)', { anchor: 'middle', size: 7, fill: '#8b949e', id: 'ek14-mapos', op: 0 }) +
    txt(450, 386, 'রঙ-নিয়ম: হলুদ = merger, বেগুনি = filter, লাল = imu, নীল = ekf/odom, সবুজ = gmapping/map, গোল্ড = ফলাফল', { anchor: 'middle', size: 8.5, fill: '#8b949e' }) +
    txt(450, 440, 'source: gmapping.launch.py L51-L94 (imu Node L53-62, remap L60, list L66-93, five entries L69-92)', { anchor: 'middle', size: 7.8, mono: true, fill: '#6e7681' })
  );
  const q = id => svg.querySelector('#' + id);
  const show = id => q(id).setAttribute('opacity', 1);
  const edge = id => q(id).setAttribute('stroke', '#e3b341');
  host.caption('তালিকার ঠিক আগে একটা <b>inline Node</b> — imu। চারটা include ছিল অন্য launch file-এর ঠিকানা; এটা সরাসরি এই file-এই লেখা একটা program-এর বর্ণনা। আর তার ভেতরে আছে আজকের সবচেয়ে কৌতূহল-জাগানো জিনিসটা — <code>remappings</code>।');
  host.formula("imu Node L53-62: remappings=[('/imu', '/imu/data_raw')] L60");
  await host.sleep(1500);
  edge('ek14-imu'); show('ek14-rm'); show('ek14-rm2');
  host.caption('L60-এর remap জোড়াটা একটা <b>নাম-বদলের সেতু</b>: node-টা যেন বলে — আমি <code>/imu</code> শুনব, কিন্তু বাইরের দুনিয়ায় সেই খবর ছড়ায় <code>/imu/data_raw</code> নামে। সেতুটা দুই পাড় জোড়ে দেয়; source-এর নিজের মন্তব্যেই (L56-59) এই রূপক। vendor node-এর ভেতরের কাজ <b>illustrative</b>।');
  host.formula("remap: node-internal '/imu' <-> wire '/imu/data_raw'");
  await host.sleep(1700);
  show('ek14-e1'); show('ek14-e1t');
  host.caption('এবার মহাতালিকা (L66-93) — <code>return LaunchDescription([</code>। entry ১ (L69-71): merger include। constructor phase-এ এরা শুধু <b>বিকল্প-বস্তু</b> হয়ে তালিকায় সাজে; কেউ চালু হয় না।');
  await host.sleep(1300);
  show('ek14-e2'); show('ek14-e2t');
  host.caption('entry ২ (L74-76): filter include। পাশাপাশি সাজছে merger-filter জুটি — folder 10 থেকে চেনা সেন্সর-শৃঙ্খলার প্রথম দুই ধাপ।');
  await host.sleep(1300);
  show('ek14-e3'); show('ek14-e3t');
  host.caption('entry ৩ (L79): imu — <b>সরাসরি Node</b>, কোনো include নয়। একটাই entry যে নিজেই পুরো বর্ণনা বয়ে আনে; বাকি চারজনের পেছনে আলাদা launch file আছে।');
  await host.sleep(1300);
  show('ek14-e4'); show('ek14-e4t'); show('ek14-e5'); show('ek14-e5t');
  host.caption('entry ৪ (L82-84) ekf include, entry ৫ (L90-92) gmapping include — তালিকা সম্পূর্ণ, শরীর শেষ। source-এর মন্তব্য (L85-89) এই পাঁচজনকে একসাথে শোনা কান-রাজ্য হিসেবেই বোঝায়।');
  host.formula('LaunchDescription([ merger, filter, imu, ekf, gmapping ]) = 5 entries, 0 running (yet)');
  await host.sleep(1700);
  show('ek14-run'); show('ek14-n1'); show('ek14-n1t'); show('ek14-n2'); show('ek14-n2t'); show('ek14-n3'); show('ek14-n3t'); show('ek14-rawin'); show('ek14-imut');
  host.caption('<b>run phase</b> — পাঁচ entry পরপর ফায়ার হয়। merger দুই lidar-এর raw গিলে এক scan ছাড়ে, filter সেটায় ঝাড়ফুঁক করে, imu নিজের <code>/imu/data_raw</code> খাতা খোলে।');
  await host.sleep(1700);
  show('ek14-l12'); show('ek14-mid'); show('ek14-scanb'); show('ek14-scan');
  host.caption('সেন্সর-শৃঙ্খলা সম্পূর্ণ: <code>/scan</code> — 360-degree পরিষ্কার ring। এই একটাই topic gmapping-এর চোখ; আগের তিন folder-এ যে চেনা পথে পাইকারি scan এসেছে, এখানেও তা-ই।');
  await host.sleep(1600);
  show('ek14-n4'); show('ek14-n4t'); show('ek14-n5'); show('ek14-n5t'); show('ek14-l45'); show('ek14-ekfin');
  host.caption('ekf আর gmapping ওঠে। ekf-এর কাঁচামাল দুই রকম — imu-র ঝোঁক-মাপ আর wheel-এর গণনা-করা দূরি; দুটো গুলে সে দেয় এক স্থির <code>/odom</code> (গলানির ভেতরের অঙ্ক vendor-এর, <b>illustrative</b>)।');
  await host.sleep(1600);
  show('ek14-odomb'); show('ek14-odom'); show('ek14-s2g'); show('ek14-o2g');
  host.caption('gmapping-এর দুই ইনপুট তৈরি: <code>/scan</code> (দেয়াল চেনা) আর <code>/odom</code> (নিজে কোথায় দাঁড়িয়ে)। একটা ছাড়া আরেকটা অর্ধেক — দেয়াল জানা যায় কিন্তু নিজের পা-চিহ্ন না জানলে মানচিত্র জোড়া লাগে না।');
  host.formula('gmapping inputs: /scan (walls) + /odom (pose) -> scan match -> particles -> map');
  await host.sleep(1700);
  show('ek14-mapb'); show('ek14-mapa'); show('ek14-mapb2'); show('ek14-mapo'); show('ek14-mapot'); show('ek14-mapos');
  host.caption('আর ফল বেরোয় <code>/map</code> — occupancy grid, প্রতি নিঃশ্বাসে একটু একটু বাড়ে। README-র L15 পরে এই সম্পদকেই <code>yahboom_map</code> নামে ফাইলে তুলে রাখবে। পাঁচ entry, দুই ইনপুট, এক মানচিত্র — এই হলো SLAM stack-এর পুরো আঁকশো।');
  await host.sleep(1700);
  host.caption('এরপর মানচিত্রটা চোখে দেখার পালা — slam_view.launch.py RViz খুলবে। সেই গল্প পরের part-এ।');
  await host.sleep(1500);
};
