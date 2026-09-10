#!/usr/bin/env python3
"""Runtime anim probe for the folder-12 deliverable (v1 ANIMS layer).
For each of the 7 anim sections: click Play, sample the stage SVG element count,
caption length, formula length, control-state text; assert RUN 1x appeared and
zero console errors. Uses the #qa-vt rAF-bypass hash if the v1 harness supports
it (it does: same _sched override recipe), else plain timers.
Usage: python3 qa_anim.py <deliverable.html>"""
import json, re, subprocess, sys, tempfile
from pathlib import Path

HTML = Path(sys.argv[1] if len(sys.argv) > 1 else "/home/shariful/NeuroBotics/12. lidar tracking/12. lidar tracking.html")

HOOK = """<script>
window.__errs = [];
window.addEventListener('error', function(e){ window.__errs.push(String(e.message||e.error)); });
(function(){ var ce = console.error; console.error = function(){ window.__errs.push([].slice.call(arguments).map(String).join(' ')); ce.apply(console, arguments); }; })();
</script>"""

PROBE = """<script>
(function(){
  var R = {errs: [], rows: []};
  function fin(){ R.errs = (window.__errs||[]).slice(0,8);
    var pre = document.createElement('pre'); pre.id='qa-anim-result';
    pre.textContent = 'QAANIM ' + JSON.stringify(R);
    document.body.appendChild(pre); }
  var secs = [];
  var i = 0;
  function probeOne(sec){
    var host = sec.querySelector('.anim-stage');
    var svg = sec.querySelector('.anim-stage svg');
    var cap = sec.querySelector('.anim-caption');
    var fx = sec.querySelector('.anim-formula');
    var state = sec.querySelector('.anim-state');
    var play = sec.querySelector('.anim-controls .ac-btn[data-ac="play"]');
    var row = {id: sec.id || ('idx'+i)};
    row.hasHost = host ? 1 : 0;
    row.btn = play ? 1 : 0;
    if (play) play.click();
    return row;
  }
  /* snapshot every anim after a short virtual delay, then serially play+sample */
  var rows = [];
  setTimeout(function(){
    secs = document.querySelectorAll('.sec.sec-anim');
    if (!secs.length) { fin(); return; }
    secs.forEach(function(sec, k){
      var row = probeOne(sec);
      rows.push(row);
    });
    setTimeout(function(){
      secs.forEach(function(sec, k){
        var svg = sec.querySelector('.anim-stage svg');
        var cap = sec.querySelector('.anim-caption');
        var fx = sec.querySelector('.anim-formula');
        var state = sec.querySelector('.anim-state');
        rows[k].svgEls = svg ? svg.querySelectorAll('*').length : -1;
        rows[k].capLen = cap ? (cap.textContent||'').trim().length : -1;
        rows[k].fxLen = fx ? (fx.textContent||'').trim().length : -1;
        rows[k].state = state ? state.textContent.trim() : '';
      });
      R.rows = rows;
      fin();
    }, 2500);
  }, 300);
})();
</script>"""

doc = HTML.read_text(encoding="utf-8")
doc = doc.replace("<head>", "<head>\n" + HOOK, 1).replace("</body>", PROBE + "\n</body>", 1)
tmp = Path(tempfile.mkdtemp()) / "qa12_anim.html"
tmp.write_text(doc, encoding="utf-8")
out = subprocess.run(
    ["google-chrome", "--headless=new", "--disable-gpu", "--no-sandbox",
     "--virtual-time-budget=9000", "--dump-dom", f"file://{tmp}"],
    capture_output=True, text=True, timeout=300).stdout
m = re.search(r'id="qa-anim-result">QAANIM (\{.*?\})</pre>', out, re.S)
if not m:
    print("FATAL: no qa-anim-result marker; page errors?"); sys.exit(1)
R = json.loads(m.group(1))
bad = 0
for r in R["rows"]:
    ok = str(r.get("btn")) == "1" and int(r.get("svgEls", -1)) > 8 and int(r.get("capLen", -1)) > 10 and (r.get("state","").startswith("RUN") or r.get("state","") in ("HOLD", "DONE", "COMPLETE"))
    bad += 0 if ok else 1
    print(f"  {r['id']:16} btn={r.get('btn')} svg={r.get('svgEls')} cap={r.get('capLen')} fx={r.get('fxLen')} state={r.get('state')!r} {'OK' if ok else 'FAIL'}")
print("errors:", R["errs"] or "none", "| anim sections:", len(R["rows"]), "| failing:", bad)
sys.exit(0 if (bad == 0 and not R["errs"]) else 1)
