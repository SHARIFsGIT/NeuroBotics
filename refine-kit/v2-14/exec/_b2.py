
rob_i8 = (T.format(s='compile') + TCOMMON
    + tl(78, 'class LineDetect: import-pass compile', D)
    + tl(89, 'L276-280: buzzer clear branch', P)
    + tl(100, 'for i in range(3): publish(b)', P)
    + S.format(s='import pass')
    + '<path d="M300 96 L262 62" stroke="#4fc3f7" stroke-dasharray="3 3" opacity=".5"/>'
    + '<path d="M300 96 L338 62" stroke="#4fc3f7" stroke-dasharray="3 3" opacity=".5"/>'
    + '<rect x="286" y="96" width="28" height="34" rx="6" fill="url(#egB)" stroke="#4fc3f7" stroke-width="1.2"/>'
    + '<path d="M300 88 L294 98 L306 98 Z" fill="#4fc3f7" opacity=".8"/>'
    + '<circle cx="366" cy="86" r="5" fill="none" stroke="#484f58"/>'
    + '<path d="M374 79 a10 10 0 0 1 0 14" stroke="#484f58" fill="none"/>'
    + '<text x="366" y="102" text-anchor="middle" font-family="monospace" font-size="5.4" fill="#484f58">/beep</text>'
    + '<rect x="240" y="150" width="160" height="13" rx="3" fill="#161b22" stroke="#ff7b72"/>'
    + '<text x="320" y="159" text-anchor="middle" font-family="monospace" font-size="5.4" fill="#ff7b72">STOP side: /beep 1, one per frame</text>'
    + '<rect x="240" y="168" width="160" height="13" rx="3" fill="#161b22" stroke="#7ee787"/>'
    + '<text x="320" y="177" text-anchor="middle" font-family="monospace" font-size="5.4" fill="#7ee787">CLEAR side: /beep 0, three times</text>'
    + '<text x="320" y="196" text-anchor="middle" font-family="monospace" font-size="5.4" fill="#8b949e">folder 13 latched level - this one is an edge</text>'
    + bot('buzzer-এর দুই নিয়ম লেখা হয়ে গেল।',
          'বাধায় প্রতি frame-এ 1, সাফ হলে 0 তিনবার।',
          'folder 13-এর latched-level নয় — এটা per-frame edge।'))

rob_i9 = (T.format(s='compile') + TCOMMON
    + tl(78, 'class LineDetect: import-pass compile', D)
    + tl(89, 'L282: abs(point_x-320) < 40', P)
    + tl(100, 'L284: twist.angular.z = 0.0', P)
    + S.format(s='import pass')
    + '<rect x="236" y="64" width="168" height="56" rx="3" fill="#161b22" stroke="#30363d"/>'
    + '<rect x="309.5" y="66" width="21" height="52" fill="#7ee787" opacity=".16"/>'
    + '<line x1="320" y1="66" x2="320" y2="118" stroke="#4fc3f7" stroke-width="1.2"/>'
    + '<circle cx="304" cy="112" r="3" fill="#ffb454"/>'
    + '<circle cx="315" cy="112" r="3" fill="#7ee787"/>'
    + '<circle cx="336" cy="112" r="3" fill="#ffb454"/>'
    + '<circle cx="320" cy="106" r="3" fill="#7ee787"/>'
    + '<text x="304" y="133" text-anchor="middle" font-family="monospace" font-size="5.2" fill="#ffb454">F1 260</text>'
    + '<text x="336" y="133" text-anchor="middle" font-family="monospace" font-size="5.2" fill="#ffb454">F3 380</text>'
    + '<text x="320" y="142" text-anchor="middle" font-family="monospace" font-size="5.2" fill="#7ee787">F2 300 / F4 320 in band</text>'
    + '<text x="320" y="158" text-anchor="middle" font-family="monospace" font-size="5.8" fill="#ffb454">outside band: angular.z = z_Pid</text>'
    + '<text x="320" y="169" text-anchor="middle" font-family="monospace" font-size="5.8" fill="#7ee787">inside +/-40 px: angular.z = 0.0</text>'
    + '<text x="320" y="182" text-anchor="middle" font-family="monospace" font-size="5.4" fill="#484f58">F1-F4 = U20 frames (illustrative)</text>'
    + bot('ছবির কেন্দ্র 320, মৃত-অঞ্চল ±40 pixel।',
          'ব্যান্ডে centroid পড়লে স্টিয়ারিং শূন্য।',
          'F1-F4 বিন্দুগুলোই U20-এ এই অঙ্ক করবে।'))

rob_i11 = (T.format(s='compile') + TCOMMON
    + tl(78, 'class LineDetect: import-pass compile', D)
    + tl(89, 'def execute L245-290 compiled', G)
    + tl(100, 'def process bound L291', P)
    + S.format(s='import pass')
    + '<rect x="236" y="56" width="168" height="168" rx="5" fill="#161b22" stroke="#4fc3f7"/>'
    + '<text x="320" y="68" text-anchor="middle" font-family="monospace" font-size="6.2" fill="#e6edf3">follow_line.py - IMPORT PASS</text>'
    + '<text x="246" y="84" font-family="monospace" font-size="5.8" fill="#7ee787">execute L245-290 compiled</text>'
    + '<text x="246" y="95" font-family="monospace" font-size="5.8" fill="#7ee787">process L291 compiling</text>'
    + '<text x="246" y="106" font-family="monospace" font-size="5.8" fill="#8b949e">states: init / identify / tracking</text>'
    + '<text x="246" y="117" font-family="monospace" font-size="5.8" fill="#484f58">Remove pivot - U18</text>'
    + '<text x="246" y="130" font-family="monospace" font-size="5.8" fill="#d2a8ff">caller: sync callback L171</text>'
    + '<text x="246" y="141" font-family="monospace" font-size="5.8" fill="#d2a8ff">input: rgb_img + waitKey action</text>'
    + '<text x="246" y="154" font-family="monospace" font-size="5.8" fill="#ffb454">state machine dormant</text>'
    + bot('দ্বিতীয় মস্তিষ্ক process() বাঁধা পড়ল।',
          'প্রতি synced frame-এ callback L171 ডাকবে।',
          'Track_state-এর দশা এখানেই বদলাবে।'))

rob_i15 = (T.format(s='compile') + TCOMMON
    + tl(78, 'class LineDetect: import-pass compile', D)
    + tl(89, 'L302-310: init ROI branch', P)
    + tl(100, 'Roi_hsv -> hsv_range', P)
    + S.format(s='import pass')
    + '<rect x="252" y="58" width="120" height="88" rx="3" fill="#0d1117" stroke="#30363d"/>'
    + '<text x="312" y="68" text-anchor="middle" font-family="monospace" font-size="5.4" fill="#8b949e">frame</text>'
    + '<path d="M270 134 L290 118 L320 122 L360 100" stroke="#ff7b72" stroke-width="3" fill="none"/>'
    + '<line x1="282" y1="132" x2="334" y2="92" stroke="#4fc3f7" stroke-width="1"/>'
    + '<rect x="282" y="92" width="52" height="40" fill="none" stroke="#7ee787" stroke-dasharray="3 2" stroke-width="1.2"/>'
    + '<circle cx="334" cy="92" r="2" fill="#e6edf3"/>'
    + '<text x="320" y="158" text-anchor="middle" font-family="monospace" font-size="5.4" fill="#8b949e">drag ROI -> Roi_hsv -> hsv_range</text>'
    + '<text x="320" y="169" text-anchor="middle" font-family="monospace" font-size="5.4" fill="#484f58">onMouse L232-243 feeds the rectangle</text>'
    + '<text x="320" y="180" text-anchor="middle" font-family="monospace" font-size="5.4" fill="#d2a8ff">dyn_update = True after extract</text>'
    + bot('init দশা — ROI আঁকার নিয়ম লেখা হলো।',
          'মাউসের টানা rectangle থেকে hsv_range বেরোবে।',
          'সঙ্গে dyn_update মোহর — calibration সেভ হবে।'))
