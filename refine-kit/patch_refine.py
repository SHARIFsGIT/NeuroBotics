#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Surgical refinement patcher for the four NeuroBotics analysis HTMLs.

Inserts (and only inserts):
  1. <style id="refine-style">…</style>  immediately before </head>
  2. <script id="refine-script">…</script>  immediately before </body>
     (engine JS with the per-app EXEC spec injected at its marker)

Guarantees:
  - ZERO byte changes to anything already in the file: the original
    <style> block and the original <script> block are hash-verified
    identical before and after patching (FILEDATA/PARTS untouched).
  - Idempotent: skips files already carrying the refinement layer.
  - Inserted script must pass node --check; inserted style+script must
    pass the banned-glyph (emoji/dingbat) scan.
"""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path('/home/shariful/NeuroBotics')
KIT = Path('/tmp/nbref')
APPS = {
    1: '01. arm calibration.html',
    2: '02. joystick controller.html',
    3: '03. keyboard control.html',
    4: '04. angular velocity calibration.html',
}
EMOJI = re.compile(r'[\U0001F000-\U0001FAFF☀-➿⬀-⯿✀-➿]')


def fail(msg):
    print('FAIL:', msg)
    sys.exit(1)


def main():
    only = {int(a) for a in sys.argv[1:]} if len(sys.argv) > 1 else set(APPS)
    engine = (KIT / 'refine_engine.js').read_text(encoding='utf-8')
    css = (KIT / 'refine_style.css').read_text(encoding='utf-8')
    if '/*__EXEC_SPEC__*/ null' not in engine:
        fail('engine marker missing')
    if EMOJI.search(engine) or EMOJI.search(css):
        fail('emoji/dingbat found in kit')

    for n, fname in APPS.items():
        if only and n not in only:
            continue
        f = ROOT / fname
        spec_path = KIT / ('exec-spec-%02d.json' % n)
        if not spec_path.exists():
            fail('%s: spec missing %s' % (fname, spec_path))
        html = f.read_text(encoding='utf-8')

        if 'id="refine-style"' in html:
            print('%-42s already refined — skipped' % fname)
            continue

        # ---- preconditions ----
        if html.count('</head>') != 1 or html.count('</body>') != 1:
            fail('%s: head/body anchor not unique' % fname)
        m = re.search(r'<script>\n(.*)\n</script>\n</body>', html, re.S)
        if not m:
            fail('%s: main script block not found' % fname)
        orig_script_hash = hashlib.sha256(m.group(0).encode()).hexdigest()[:12]
        orig_style_hash = hashlib.sha256(
            re.search(r'<style>.*?</style>', html, re.S).group(0).encode()).hexdigest()[:12]

        # ---- build inserts ----
        spec = json.loads(spec_path.read_text(encoding='utf-8'))
        if not (20 <= len(spec['steps']) <= 32):
            fail('%s: spec has %d steps' % (fname, len(spec['steps'])))
        lines = (json.loads((KIT / ('filedata-%02d.json' % n)).read_text(encoding='utf-8'))
                 [spec['file']])
        for st in spec['steps']:
            if not (1 <= st['ln'] <= len(lines)) or not lines[st['ln'] - 1].strip():
                fail('%s: bad ln %s' % (fname, st['ln']))
        spec_js = json.dumps(spec, ensure_ascii=False, separators=(',', ':'))
        spec_js = spec_js.replace('</', '<\\/')
        if EMOJI.search(spec_js):
            fail('%s: emoji in spec' % fname)
        engine_js = engine.replace('/*__EXEC_SPEC__*/ null', spec_js, 1)

        tmp = KIT / ('.engine-check-%d.js' % n)
        tmp.write_text(engine_js, encoding='utf-8')
        r = subprocess.run(['node', '--check', str(tmp)], capture_output=True, text=True)
        if r.returncode != 0:
            fail('%s: engine node --check failed:\n%s' % (fname, r.stderr[:800]))

        style_block = '\n<style id="refine-style">\n' + css + '\n</style>'
        script_block = '<script id="refine-script">\n' + engine_js + '\n</script>\n'

        patched = html.replace('</head>', style_block + '\n</head>', 1)
        patched = patched.replace('<script>\n' + m.group(1) + '\n</script>\n</body>',
                                  '<script>\n' + m.group(1) + '\n</script>\n' + script_block + '</body>', 1)

        # ---- post-conditions ----
        m2 = re.search(r'<script>\n(.*)\n</script>\n<script id="refine-script">', patched, re.S)
        if not m2 or m2.group(1) != m.group(1):
            fail('%s: original script mutated by insertion' % fname)
        if hashlib.sha256(re.search(r'<style>.*?</style>', patched, re.S).group(0).encode()).hexdigest()[:12] != orig_style_hash:
            fail('%s: original style mutated' % fname)
        # FILEDATA must still be present and identical
        if 'const FILEDATA = {' not in patched:
            fail('%s: FILEDATA lost' % fname)
        f.write_text(patched, encoding='utf-8')
        print('%-42s %7s → %7s bytes · %2d steps · script-hash %s (unchanged)' % (
            fname, f'{len(html.encode()):,}', f'{len(patched.encode()):,}',
            len(spec['steps']), orig_script_hash))
    print('OK')


if __name__ == '__main__':
    main()
