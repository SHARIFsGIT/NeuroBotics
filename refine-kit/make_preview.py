#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a /tmp-only PREVIEW of any NeuroBotics app with the refinement kit.

Usage: make_preview.py N [specfile]

Touches nothing in ROOT and nothing the running spec workflow uses.
  - If the ROOT file already carries a refine layer (app 04 pilot), strip it
    first and verify the pristine reconstruction (byte size + script hash
    for app 04; for others just require the layer gone).
  - Insert CURRENT kit + the given spec (default exec-spec-0N.json).
  - Bake in QA isolation (exec section framed) + geometry probe.
"""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path('/home/shariful/NeuroBotics')
KIT = Path('/tmp/nbref')
OUT = KIT / 'qa'
OUT.mkdir(exist_ok=True)
APPS = {
    1: '01. arm calibration.html',
    2: '02. joystick controller.html',
    3: '03. keyboard control.html',
    4: '04. angular velocity calibration.html',
}
PRE = {4: (522817, 'c45cf814e31f')}  # byte size + script hash after strip

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
      d.dataset.gutter = document.querySelectorAll('.exec-code .eln').length;
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


def fail(msg):
    print('FAIL:', msg)
    sys.exit(1)


n = int(sys.argv[1])
spec_path = Path(sys.argv[2]) if len(sys.argv) > 2 else KIT / ('exec-spec-%02d.json' % n)
src = ROOT / APPS[n]
preview = OUT / ('a%d-preview.html' % n)

html = src.read_text(encoding='utf-8')
if 'id="refine-style"' in html:
    p = re.sub(r'\n<style id="refine-style">.*?</style>\n</head>', '</head>', html, flags=re.S)
    p = re.sub(r'<script id="refine-script">.*?</script>\n</body>', '</body>', p, flags=re.S)
    if 'refine-style' in p or 'refine-script' in p:
        fail('strip incomplete')
    if n in PRE:
        size, want = PRE[n]
        if len(p.encode()) != size:
            fail('pristine size %d != %d' % (len(p.encode()), size))
        m0 = re.search(r'<script>\n(.*)\n</script>\n</body>', p, re.S)
        h = hashlib.sha256(m0.group(0).encode()).hexdigest()[:12]
        if h != want:
            fail('pristine script hash %s != %s' % (h, want))
else:
    p = html

engine = (KIT / 'refine_engine.js').read_text(encoding='utf-8')
css = (KIT / 'refine_style.css').read_text(encoding='utf-8')
spec = json.loads(spec_path.read_text(encoding='utf-8'))
if not (20 <= len(spec['steps']) <= 32):
    fail('spec has %d steps' % len(spec['steps']))
spec_js = json.dumps(spec, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
engine_js = engine.replace('/*__EXEC_SPEC__*/ null', spec_js, 1)

tmpjs = KIT / ('.preview-engine-%d.js' % n)
tmpjs.write_text(engine_js, encoding='utf-8')
r = subprocess.run(['node', '--check', str(tmpjs)], capture_output=True, text=True)
if r.returncode != 0:
    fail('node --check:\n' + r.stderr[:800])

m = re.search(r'<script>\n(.*)\n</script>\n</body>', p, re.S)
if not m:
    fail('main script not found')
patched = p.replace('</head>', '\n<style id="refine-style">\n' + css + '\n</style>\n' + PROBE + '\n</head>', 1)
patched = patched.replace('<script>\n' + m.group(1) + '\n</script>\n</body>',
                          '<script>\n' + m.group(1) + '\n</script>\n<script id="refine-script">\n' +
                          engine_js + '\n</script>\n</body>', 1)
preview.write_text(patched, encoding='utf-8')
print('preview ok: %s · %s bytes · %d steps · spec %s' % (
    preview, f'{len(patched.encode()):,}', len(spec['steps']), spec_path.name))
