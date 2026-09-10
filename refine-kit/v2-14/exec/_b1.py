# Build out-U17.json — unit U17: follow_line L245-340, 22 struct steps (import-pass compile)
import json

T = ('<rect x="16" y="22" width="196" height="228" rx="9" fill="#161b22" fill-opacity=".55" stroke="#4fc3f7" stroke-width="1.4"/>'
     '<text x="26" y="34" text-anchor="start" font-family="monospace" font-size="10" fill="#e6edf3" font-weight="bold">TERMINAL</text>'
     '<text x="202" y="34" text-anchor="end" font-family="monospace" font-size="5.8" fill="#6e7681">{s}</text>'
     '<text x="26" y="45" font-family="monospace" font-size="5.8" fill="#6e7681">jetson@yahboom: ~ (illustrative)</text>')
S = ('<rect x="216" y="22" width="208" height="228" rx="9" fill="#161b22" fill-opacity=".55" stroke="#30363d" stroke-width="1.4"/>'
     '<text x="226" y="34" text-anchor="start" font-family="monospace" font-size="10" fill="#e6edf3" font-weight="bold">SYSTEM</text>'
     '<text x="414" y="34" text-anchor="end" font-family="monospace" font-size="5.8" fill="#6e7681">{s}</text>'
     '<rect x="224" y="42" width="192" height="196" rx="4" fill="#0d1117" fill-opacity=".8" stroke="#21262d" stroke-width="1"/>')

def tl(y, t, c):
    return '<text x="26" y="%d" font-family="monospace" font-size="6.2" fill="%s">%s</text>' % (y, c, t)

CMD = 'jetson@yahboom:~$ ros2 run M3Pro_demo follow_line'
G = '#7ee787'; D = '#8b949e'; DIM = '#484f58'; P = '#d2a8ff'; A = '#ffb454'

def bot(l1, l2, l3):
    return ('<text x="16" y="262" font-family="Hind Siliguri, sans-serif" font-size="7.2" fill="#e6edf3">' + l1 + '</text>'
            '<text x="16" y="273" font-family="Hind Siliguri, sans-serif" font-size="7.2" fill="#8b949e">' + l2 + '</text>'
            '<text x="16" y="284" font-family="Hind Siliguri, sans-serif" font-size="7.2" fill="#8b949e">' + l3 + '</text>')

TCOMMON = tl(56, CMD, G) + tl(67, 'import finish', G)

# ---------- robs ----------
rob_i0 = (T.format(s='compile') + TCOMMON
    + tl(78, 'cv 4.10.0 (cv_edition print, illustrative)', D)
    + tl(89, 'class LineDetect: import-pass compile', D)
    + tl(100, 'def execute bound L245', P)
    + tl(111, '(no runtime output - define only)', DIM)
    + S.format(s='import pass')
    + '<rect x="236" y="56" width="168" height="168" rx="5" fill="#161b22" stroke="#4fc3f7"/>'
    + '<text x="320" y="68" text-anchor="middle" font-family="monospace" font-size="6.2" fill="#e6edf3">follow_line.py - IMPORT PASS</text>'
    + '<text x="246" y="84" font-family="monospace" font-size="5.8" fill="#8b949e">callbacks L118-232 bound (U16)</text>'
    + '<text x="246" y="95" font-family="monospace" font-size="5.8" fill="#7ee787">def execute L245 - NOW</text>'
    + '<text x="246" y="106" font-family="monospace" font-size="5.8" fill="#8b949e">def process L291 - next</text>'
    + '<text x="246" y="117" font-family="monospace" font-size="5.8" fill="#d2a8ff">params: point_x = circle[0]</text>'
    + '<text x="246" y="130" font-family="monospace" font-size="5.8" fill="#d2a8ff">color_radius = circle[2]</text>'
    + '<text x="246" y="143" font-family="monospace" font-size="5.8" fill="#ffb454">nothing runs yet - defs only</text>'
    + bot('execute-ফাংশনটি এখন শুধু বাঁধা পড়ল।',
          'L245-290 দেহ bytecode হয়ে ঘুমিয়ে আছে।',
          'ডাক আসবে প্রতি frame-এর thread থেকে (L336)।'))

rob_i5 = (T.format(s='compile') + TCOMMON
    + tl(78, 'class LineDetect: import-pass compile', D)
    + tl(89, 'def execute L245-290 compiling', D)
    + tl(100, 'L269: twist.linear.x = 0.1', P)
    + S.format(s='import pass')
    + '<text x="320" y="58" text-anchor="middle" font-family="monospace" font-size="6" fill="#8b949e">who reaches the wheels?</text>'
    + '<rect x="248" y="66" width="144" height="17" rx="3" fill="#161b22" stroke="#484f58"/>'
    + '<text x="320" y="77" text-anchor="middle" font-family="monospace" font-size="5.8" fill="#6e7681">ros param linear = 0.18 (L214)</text>'
    + '<rect x="248" y="90" width="144" height="17" rx="3" fill="#161b22" stroke="#484f58"/>'
    + '<text x="320" y="101" text-anchor="middle" font-family="monospace" font-size="5.8" fill="#6e7681">self.linear = 0.2 (L93 last write)</text>'
    + '<rect x="248" y="124" width="144" height="17" rx="3" fill="#161b22" stroke="#7ee787"/>'
    + '<text x="320" y="135" text-anchor="middle" font-family="monospace" font-size="5.8" fill="#7ee787">twist.linear.x = 0.1 (L269)</text>'
    + '<text x="320" y="154" text-anchor="middle" font-family="monospace" font-size="5.8" fill="#ffb454">only the third is published</text>'
    + '<text x="320" y="165" text-anchor="middle" font-family="monospace" font-size="5.8" fill="#484f58">0.18 and 0.2 never read in execute</text>'
    + bot('গতির তিন সংখ্যা তিন জগতে গেল।',
          'parameter 0.18, attribute 0.2 — কেউই চাকায় পৌঁছায় না।',
          'হুইল পায় শুধু L269-এর hardcoded 0.1 m/s।'))
