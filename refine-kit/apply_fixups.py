#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Post-workflow spec fixups (run AFTER the spec workflow has fully completed).

  1. font bump: every SVG font-size="8.5" -> "9" (readability at panel scale;
     8.6 is the QA-passed subtitle size and is left alone)
  2. validate: mechanical validator must pass afterwards (exact mono widths)
Idempotent; writes only /tmp/nbref/exec-spec-0N.json.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

KIT = Path('/tmp/nbref')


def bump(svg):
    return re.sub(r'font-size="8\.5"', 'font-size="9"', svg)


def main():
    apps = [int(a) for a in sys.argv[1:]] or [1, 2, 3, 4]
    for n in apps:
        p = KIT / ('exec-spec-%02d.json' % n)
        spec = json.loads(p.read_text(encoding='utf-8'))
        before = json.dumps(spec, ensure_ascii=False)
        for key in ('rob0', 'finalRob'):
            if spec.get(key):
                spec[key] = bump(spec[key])
        for st in spec['steps']:
            if st.get('rob'):
                st['rob'] = bump(st['rob'])
        after = json.dumps(spec, ensure_ascii=False)
        if after != before:
            p.write_text(json.dumps(spec, ensure_ascii=False, indent=1),
                         encoding='utf-8')
            print('app %d: bumped 8.5->9, rewritten' % n)
        else:
            print('app %d: nothing to bump' % n)
    r = subprocess.run(['python3', str(KIT / 'validate_spec.py')] +
                       [str(a) for a in apps], capture_output=True, text=True)
    print(r.stdout)
    return r.returncode


if __name__ == '__main__':
    sys.exit(main())
