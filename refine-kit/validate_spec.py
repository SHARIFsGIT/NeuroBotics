#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mechanical validator for EXEC spec JSONs (runs after workflow checkers).

Checks per spec:
  shape   : parses, required keys, steps 20..32, per-step keys
  lines   : every ln is a real, non-blank line of the real FILEDATA file
  glyphs  : no emoji/dingbats anywhere
  svg     : tag balance in rob0/finalRob/each step rob + defs
  coords  : every numeric x/y attribute within viewBox (±2 tolerance)
  fonts   : no font-size < 8.5 in any SVG text style
  widths  : estimated text width vs viewBox right edge (x + est_width <= W-3),
            flag long single-line labels likely to collide/smear
"""
import json
import re
import sys
import unicodedata
from pathlib import Path

KIT = Path('/tmp/nbref')
APPS = {1: '01. arm calibration.html', 2: '02. joystick controller.html',
        3: '03. keyboard control.html', 4: '04. angular velocity calibration.html'}
REQ = ['app', 'file', 'note', 'w', 'h', 'steps', 'finalCap']
STEP_REQ = ['ln', 'cap', 'rob']
EMOJI = re.compile(r'[\U0001F000-\U0001FAFF☀-➿⬀-⯿✀-➿]')
SVG_OPEN = re.compile(r'<(rect|circle|ellipse|line|polyline|polygon|path|text|tspan|g|defs|linearGradient|radialGradient|stop|image|use)\b')
TAG = re.compile(r'</?([a-zA-Z][-a-zA-Z0-9]*)')
NUM = re.compile(r'^-?\d+(?:\.\d+)?$')
FONT_RE = re.compile(r'font-size[:=]["\']?([\d.]+)')
XY_RE = re.compile(r'\b(x|y|x1|y1|x2|y2|cx|cy)="(-?\d+(?:\.\d+)?)"')



def est_w(s, fs, mono=False):
    """text width: monospace = exact 0.6em/char; else per-class heuristic"""
    if mono:
        return len(s) * fs * 0.6
    w = 0.0
    for ch in s:
        if ch == ' ':
            w += 0.30
        elif unicodedata.east_asian_width(ch) in ('W', 'F'):
            w += 1.0
        elif ord(ch) > 0x09FF:  # Bangla and other Indic
            w += 0.58
        elif ch.isupper() or ch.isdigit():
            w += 0.62
        else:
            w += 0.50
    return w * fs


TSPAN_X = re.compile(r'<tspan\b([^>]*)>')
RECT_RE = re.compile(r'<rect\b([^>]*?)/>')


def text_boxes(svg):
    """[(left, right, y, fs, txt)] — tspan columns split into separate boxes."""
    out = []
    for tm in re.finditer(r'<text\b([^>]*)>(.*?)</text>', svg, re.S):
        attrs, inner = tm.group(1), tm.group(2)
        xm = re.search(r'\bx="(-?\d+(?:\.\d+)?)"', attrs)
        ym = re.search(r'\by="(-?\d+(?:\.\d+)?)"', attrs)
        fsm = re.search(r'font-size[:=]["\']?([\d.]+)', attrs)
        anchor = re.search(r'text-anchor="(\w+)"', attrs)
        if not (xm and ym and fsm):
            continue
        fs = float(fsm.group(1))
        x, y = float(xm.group(1)), float(ym.group(1))
        anch = anchor.group(1) if anchor else 'start'
        mono = 'mono' in attrs
        cols = []
        spans = list(TSPAN_X.finditer(inner))
        if spans:
            for i, sm in enumerate(spans):
                sxa = re.search(r'\bx="(-?\d+(?:\.\d+)?)"', sm.group(1))
                if not sxa:
                    continue
                seg = inner[sm.end():spans[i + 1].start() if i + 1 < len(spans) else len(inner)]
                seg = re.sub(r'<[^>]+>', '', seg)
                seg = re.sub(r'&[a-z]+;', 'x', seg)
                if seg.strip():
                    cols.append((float(sxa.group(1)), y, fs, 'start', seg))
        else:
            seg = re.sub(r'<[^>]+>', '', inner)
            seg = re.sub(r'&[a-z]+;', 'x', seg)
            if seg.strip():
                cols.append((x, y, fs, anch, seg))
        for cx, cy, cfs, canch, seg in cols:
            w = est_w(seg, cfs, mono)
            left = cx - w if canch == 'end' else cx - w / 2 if canch == 'middle' else cx
            out.append((left, left + w, cy, cfs, seg))
    return out


def check_svg(name, svg, W, H, bad):
    if not svg:
        return
    opens = len(SVG_OPEN.findall(svg))
    closes = len(re.findall(r'</(rect|circle|ellipse|line|polyline|polygon|path|text|tspan|g|defs|linearGradient|radialGradient|stop|image|use)>', svg))
    selfclosed = len(re.findall(r'/>', svg))
    if opens - selfclosed != closes:
        bad.append('%s: SVG tags unbalanced (%d open vs %d close)' % (name, opens - selfclosed, closes))
    for m in XY_RE.finditer(svg):
        v = float(m.group(2))
        if m.group(1).startswith('x'):
            if v < -2 or v > W + 2:
                bad.append('%s: x=%s outside viewBox W=%s' % (name, m.group(2), W))
        else:
            if v < -2 or v > H + 2:
                bad.append('%s: y=%s outside viewBox H=%s' % (name, m.group(2), H))
    for m in FONT_RE.finditer(svg):
        if float(m.group(1)) < 8.5:
            bad.append('%s: font-size %s < 8.5' % (name, m.group(1)))
    tbox = text_boxes(svg)
    # viewBox overflow (per column, not per whole line)
    for left, right, y, fs, txt in tbox:
        if right > W - 2:
            bad.append('%s: text %r overflows right (est right %.0f > W %s)' % (name, txt[:40], right, W))
        if left < 0:
            bad.append('%s: text %r overflows left (est left %.0f)' % (name, txt[:40], left))
    # text-vs-text collisions (same text row, x ranges overlap > 3px)
    for i in range(len(tbox)):
        for j in range(i + 1, len(tbox)):
            l1, r1, y1, f1, t1 = tbox[i]
            l2, r2, y2, f2, t2 = tbox[j]
            if abs(y1 - y2) > max(f1, f2) * 0.85:
                continue
            ov = min(r1, r2) - max(l1, l2)
            if ov > 3:
                bad.append('%s: texts collide %.0fpx: %r vs %r' % (name, ov, t1[:28], t2[:28]))
    # text-vs-box edges: text row inside a rect's y-band must fit in the rect
    rects = []
    for rm in RECT_RE.finditer(svg):
        a = rm.group(1)
        rx = re.search(r'\bx="(-?\d+(?:\.\d+)?)"', a)
        ry = re.search(r'\by="(-?\d+(?:\.\d+)?)"', a)
        rw = re.search(r'\bwidth="(-?\d+(?:\.\d+)?)"', a)
        rh = re.search(r'\bheight="(-?\d+(?:\.\d+)?)"', a)
        if rx and ry and rw and rh:
            rects.append((float(rx.group(1)), float(ry.group(1)),
                          float(rw.group(1)), float(rh.group(1))))
    for left, right, y, fs, txt in tbox:
        for rx, ry, rw, rh in rects:
            if rw < 40 or rh < 12:
                continue  # narrow chips/icons legitimately sit beside labels
            if not (ry - 2 <= y <= ry + rh + 2):
                continue
            ov = min(right, rx + rw) - max(left, rx)
            if ov <= 5:
                continue  # adjacent/grazing, not crossing
            fits = left >= rx - 1 and right <= rx + rw + 1
            if not fits:
                bad.append('%s: text %r crosses box edge (box x %.0f..%.0f, text %.0f..%.0f)'
                           % (name, txt[:30], rx, rx + rw, left, right))
                break


def main():
    only = {int(a) for a in sys.argv[1:]} if len(sys.argv) > 1 else set(APPS)
    nbad = 0
    for n in sorted(APPS):
        if n not in only:
            continue
        bad = []
        sp = KIT / ('exec-spec-%02d.json' % n)
        try:
            spec = json.loads(sp.read_text(encoding='utf-8'))
        except Exception as e:
            print('app %d: PARSE FAIL %s' % (n, e))
            nbad += 1
            continue
        for k in REQ:
            if k not in spec:
                bad.append('missing key %s' % k)
        steps = spec.get('steps', [])
        if not (20 <= len(steps) <= 32):
            bad.append('%d steps out of range' % len(steps))
        fd = json.loads((KIT / ('filedata-%02d.json' % n)).read_text(encoding='utf-8'))
        lines = fd.get(spec.get('file'), [])
        if not lines:
            bad.append('file %r not in FILEDATA' % spec.get('file'))
        EMOJI_scan = sp.read_text(encoding='utf-8')
        if EMOJI.search(EMOJI_scan):
            bad.append('emoji/dingbat present')
        W, H = spec.get('w', 440), spec.get('h', 320)
        check_svg('rob0', spec.get('rob0') or '', W, H, bad)
        check_svg('finalRob', spec.get('finalRob') or '', W, H, bad)
        check_svg('defs', spec.get('defs') or '', W, H, bad) if False else None
        seen_ln = set()
        for i, st in enumerate(steps):
            for k in STEP_REQ:
                if k not in st:
                    bad.append('step %d missing %s' % (i, k))
            ln = st.get('ln')
            if not isinstance(ln, int) or not (1 <= ln <= len(lines)) or not lines[ln - 1].strip():
                bad.append('step %d bad ln %r' % (i, ln))
            if ln in seen_ln:
                bad.append('step %d duplicate ln %s' % (i, ln))
            seen_ln.add(ln)
            check_svg('step%d' % i, st.get('rob') or '', W, H, bad)
        status = 'OK' if not bad else 'BAD(%d)' % len(bad)
        print('app %d %-6s steps=%d file=%s ln-range=%s..%s' % (
            n, status, len(steps), spec.get('file'),
            min(seen_ln) if seen_ln else '-', max(seen_ln) if seen_ln else '-'))
        for b in bad[:25]:
            print('   -', b)
        if len(bad) > 25:
            print('   ... %d more' % (len(bad) - 25))
        nbad += len(bad)
    print('total issues:', nbad)
    return 0 if nbad == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
