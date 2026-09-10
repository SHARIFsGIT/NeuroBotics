#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Post-patch smoke + visual QA harness for the refined NeuroBotics HTMLs.

Per app:
  1. headless-Chrome DOM dump of the REAL file — structural assertions +
     console-error scan (counts are exact: rendered DOM minus the known
     single occurrences that live inside the inline engine source).
  2. a QA copy (intro/parts hidden + geometry probe injected) — asserts the
     exec code panel really scrolls horizontally and does not overflow the
     page, then takes desktop + mobile screenshots of the exec section
     (fragment anchors do not scroll in headless screenshots, so isolation
     via CSS is the reliable way to frame the section).
"""
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path('/home/shariful/NeuroBotics')
OUT = Path('/tmp/nbref/qa')
OUT.mkdir(exist_ok=True)
APPS = {  # n: (file, parts, anims)
    1: ('01. arm calibration.html', 16, 15),
    2: ('02. joystick controller.html', 16, 10),
    3: ('03. keyboard control.html', 11, 8),
    4: ('04. angular velocity calibration.html', 21, 8),
}
CHROME = ['google-chrome', '--headless=new', '--disable-gpu', '--no-sandbox',
          '--virtual-time-budget=25000']

PROBE = """<style id="qa-isolate">.intro-banner, section.part{display:none!important}</style>
<script id="qa-probe">
(function(){
  function go(){
    try {
      var c = document.getElementById('exec-code');
      var d = document.createElement('div');
      d.id = 'qa-probe-out';
      d.dataset.hscroll = c.scrollWidth > c.clientWidth ? 'YES' : 'NO';
      d.dataset.vscroll = c.scrollHeight > c.clientHeight ? 'YES' : 'NO';
      d.dataset.pageOverflow = document.documentElement.scrollWidth > document.documentElement.clientWidth ? 'YES' : 'NO';
      d.dataset.dbgIdle = (document.getElementById('exec-dbg').textContent || '').trim().length > 40 ? 'YES' : 'NO';
      document.body.appendChild(d);
    } catch(e) {
      var d = document.createElement('div'); d.id = 'qa-probe-out'; d.dataset.err = String(e);
      document.body.appendChild(d);
    }
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', function(){ setTimeout(go, 500); });
  else setTimeout(go, 500);
})();
</script>"""


def run_chrome(url, args):
    with tempfile.TemporaryDirectory() as td:
        cmd = CHROME + ['--user-data-dir=' + td] + args + [url]
        return subprocess.run(cmd, capture_output=True, text=True, timeout=240)


def check(cond, msg, bad):
    if not cond:
        bad.append(msg)
    return cond


def main():
    only = {int(a) for a in sys.argv[1:]} if len(sys.argv) > 1 else set(APPS)
    for n, (fname, nparts, nanims) in APPS.items():
        if only and n not in only:
            continue
        f = ROOT / fname
        url = 'file://' + str(f)
        bad = []

        # ---- 1. real-file DOM dump ------------------------------------
        r = run_chrome(url, ['--enable-logging=stderr', '--v=0', '--dump-dom'])
        dom = r.stdout
        cons = [l for l in (r.stderr or '').splitlines()
                if 'CONSOLE' in l and ('error' in l.lower() or 'uncaught' in l.lower())]
        cons = [l for l in cons if 'favicon' not in l.lower() and 'net::' not in l]
        check(not cons, 'console errors: %s' % cons[:4], bad)

        check(dom.count('<section class="part"') >= nparts,
              'sections %d < %d' % (dom.count('<section class="part"'), nparts), bad)
        check(dom.count('id="exec-final"') == 1, 'exec-final missing/dup', bad)
        check('Complete Execution — Code → Debug → Robot' in dom, 'exec title missing', bad)
        check('STEP 00 /' in dom, 'exec step chip missing', bad)
        h1 = re.search(r'<h1>(.*?)</h1>', dom, re.S)
        check(h1 is not None and 'path' not in h1.group(1),
              'h1 still has Bangla subtitle: %r' % (h1 and h1.group(1)[:120]), bad)
        check('mjx-container' in dom, 'MathJax not rendering', bad)

        plays = dom.count('title="Play (1× speed)"')
        check(plays == nanims + 1,
              'play icon buttons %d != anims %d + 1' % (plays, nanims), bad)
        check(dom.count('>Play</button>') == 1,
              'old text play buttons remain: %d' % dom.count('>Play</button>'), bad)
        exl = dom.count('<span class="exl"')
        check(exl > 100, 'exec code lines %d too few' % exl, bad)

        # ---- 2. QA copy: probe + exec screenshots ---------------------
        qa = OUT / ('a%d-execonly.html' % n)
        html = f.read_text(encoding='utf-8')
        if 'id="qa-probe"' not in html:
            qa.write_text(html.replace('</head>', PROBE + '\n</head>', 1), encoding='utf-8')
        qurl = 'file://' + str(qa)
        r2 = run_chrome(qurl, ['--dump-dom'])
        qdom = r2.stdout
        m = re.search(r'id="qa-probe-out"[^>]*', qdom)
        if not check(m is not None, 'probe marker missing in QA copy', bad):
            pass
        else:
            attrs = m.group(0)
            check('data-hscroll="YES"' in attrs, 'code panel not h-scrollable: %s' % attrs, bad)
            check('data-vscroll="YES"' in attrs, 'code panel not v-scrollable: %s' % attrs, bad)
            check('data-page-overflow="NO"' in attrs, 'page overflows horizontally: %s' % attrs, bad)
            check('data-err' not in attrs, 'probe errored: %s' % attrs, bad)

        for tag, size in (('exec', '1440,1400'), ('mob', '390,1600')):
            shot = OUT / ('a%d-%s.png' % (n, tag))
            run_chrome(qurl, ['--window-size=%s' % size, '--screenshot=%s' % shot])
            check(shot.exists() and shot.stat().st_size > 20000,
                  'screenshot %s missing/tiny' % shot.name, bad)
        # hero (top of the real page)
        shot = OUT / ('a%d-hero.png' % n)
        run_chrome(url, ['--window-size=1440,1000', '--screenshot=%s' % shot])
        check(shot.exists(), 'hero screenshot missing', bad)

        status = 'GREEN' if not bad else 'RED'
        print('app %d %-42s %s  (play-btns %d · exec-lines %d · probe %s)' % (
            n, fname, status, plays, exl, (m.group(0)[:90] if m else 'MISSING')))
        for b in bad:
            print('   -', b)
    print('done. screenshots in', OUT)


if __name__ == '__main__':
    main()
