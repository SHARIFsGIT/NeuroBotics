#!/usr/bin/env python3
"""Headless QA for the folder-12 deliverable's exec section (and page smoke).
Pass A (mid-run): #qa-vt clock, play -> sample -> pause (stable?) -> resume -> stop (reset?)
Pass B (full-run): play, run to COMPLETE, verify finals + counts.
Usage: python3 qa_exec.py <deliverable.html>"""
import json, re, subprocess, sys, tempfile
from pathlib import Path

HTML = Path(sys.argv[1] if len(sys.argv) > 1 else "/home/shariful/NeuroBotics/12. lidar tracking/12. lidar tracking.html")

HOOK = """<script>
window.__errs = [];
window.addEventListener('error', function(e){ window.__errs.push(String(e.message||e.error)); });
(function(){ var ce = console.error; console.error = function(){ window.__errs.push([].slice.call(arguments).map(String).join(' ')); ce.apply(console, arguments); }; })();
</script>"""

PROBE_A = """<script>
(function(){
  var R = {errs: [], log: []};
  function m(k, v){ R.log.push(k + '=' + v); }
  function fin(tag){ R.errs = (window.__errs||[]).slice(0,6);
    var pre = document.createElement('pre'); pre.id = 'qa-result-' + tag;
    pre.textContent = 'QA' + tag.toUpperCase() + ' ' + JSON.stringify(R);
    document.body.appendChild(pre); }
  setTimeout(function(){
    var sec = document.getElementById('exec-final');
    m('section', sec ? 1 : 0);
    if (!sec) { fin('a'); return; }
    var q = function(id){ return document.getElementById(id); };
    var step = q('exec-step'), state = q('exec-state'), dbg = q('exec-dbg'),
        rob = q('exec-rob'), live = q('exec-live'), cap = q('exec-cap');
    m('title', document.title);
    m('sb-folder', (document.getElementById('sb-folder')||{}).textContent || '');
    m('init-state', state.textContent.trim());
    m('code-spans', document.querySelectorAll('#exec-code .exl').length);
    m('code-files', document.querySelectorAll('#exec-code .exfile').length);
    m('rob0-children', rob.querySelector('svg') ? rob.querySelector('svg').children.length : -1);
    var play = document.querySelector('#exec-controls .ac-btn[data-ac="play"]');
    var pause = document.querySelector('#exec-controls .ac-btn[data-ac="pause"]');
    var stopb = document.querySelector('#exec-controls .ac-btn[data-ac="stop"]');
    m('btns', (play?1:0)+','+(pause?1:0)+','+(stopb?1:0));
    play.click();
    setTimeout(function(){
      m('run-state', state.textContent.trim());
      m('run-step', step.textContent.trim());
      m('run-live', live.textContent.trim());
      m('run-dbg-rows', dbg.querySelectorAll('.dbg-row').length);
      m('run-cap-len', (cap.textContent||'').trim().length);
      m('run-rob-children', rob.querySelector('svg') ? rob.querySelector('svg').children.length : -1);
      m('run-err-count', (window.__errs||[]).length);
      pause.click();
      var s1 = step.textContent.trim();
      setTimeout(function(){
        m('pause-state', state.textContent.trim());
        m('pause-stable', step.textContent.trim() === s1 ? 1 : 0);
        play.click();
        setTimeout(function(){
          m('resume-state', state.textContent.trim());
          stopb.click();
          setTimeout(function(){
            m('stop-state', state.textContent.trim());
            m('stop-step', step.textContent.trim());
            m('stop-dbg-rows', dbg.querySelectorAll('.dbg-row').length);
            m('stop-live', live.textContent.trim());
            fin('a');
          }, 600);
        }, 900);
      }, 400);
    }, 1500);
  }, 400);
})();
</script>"""

PROBE_B = """<script>
(function(){
  var R = {errs: [], log: []};
  function m(k, v){ R.log.push(k + '=' + v); }
  function fin(){ R.errs = (window.__errs||[]).slice(0,6);
    var pre = document.createElement('pre'); pre.id = 'qa-result-b';
    pre.textContent = 'QAB ' + JSON.stringify(R);
    document.body.appendChild(pre); }
  setTimeout(function(){
    var step = document.getElementById('exec-step'), state = document.getElementById('exec-state'),
        dbg = document.getElementById('exec-dbg'), rob = document.getElementById('exec-rob'),
        doneBn = document.getElementById('exec-done-bn'), fx = document.getElementById('exec-fx'),
        done = document.getElementById('exec-done'), fchip = document.getElementById('exec-file');
    if (!step) { fin(); return; }
    document.querySelector('#exec-controls .ac-btn[data-ac="play"]').click();
    var t0 = null, samples = 0;
    var iv = setInterval(function(){
      samples++;
      if (!t0 && step.textContent.indexOf('STEP') === 0) t0 = step.textContent.trim();
      if (state.textContent.trim() === 'COMPLETE' || samples > 6000) {
        clearInterval(iv);
        m('first-step-seen', t0 || 'none');
        m('final-state', state.textContent.trim());
        m('final-step', step.textContent.trim());
        m('final-phase', (document.getElementById('exec-phase')||{}).textContent || '');
        m('done-shown', done.classList.contains('show') ? 1 : 0);
        m('doneBn-len', (doneBn.textContent||'').trim().length);
        m('final-dbg-rows', dbg.querySelectorAll('.dbg-row').length);
        m('final-rob-children', rob.querySelector('svg') ? rob.querySelector('svg').children.length : -1);
        m('final-fx-len', (fx.textContent||'').trim().length);
        m('fchip', (fchip||{}).textContent || '');
        m('samples', samples);
        m('errs-total', (window.__errs||[]).length);
        fin();
      }
    }, 50);
  }, 400);
})();
</script>"""

def run(pass_name, probe, budget, frag):
    doc = HTML.read_text(encoding="utf-8")
    doc = doc.replace("<head>", "<head>\n" + HOOK, 1)
    doc = doc.replace("</body>", probe + "\n</body>", 1)
    tmp = Path(tempfile.mkdtemp()) / f"qa12_{pass_name}.html"
    tmp.write_text(doc, encoding="utf-8")
    url = f"file://{tmp}#{frag}"
    out = subprocess.run(
        ["google-chrome", "--headless=new", "--disable-gpu", "--no-sandbox",
         "--virtual-time-budget=" + str(budget), "--dump-dom", url],
        capture_output=True, text=True, timeout=600).stdout
    tag = "qa-result-" + pass_name
    m = re.search(r"id=\"" + tag + r"\">(QA[AB] \{.*?\})</pre>", out, re.S)
    if not m:
        return {"FATAL": f"no {tag} in dump (page never reached probe end)",
                "dump-tail": out[-400:], "stderr-hint": out.count("qa-result")}
    return json.loads(m.group(1)[3:])

A = run("a", PROBE_A, 12000, "qa-vt")
print("=== PASS A (mid/pause/stop) ===")
for k, v in A.items():
    print(f"  {k}: {v if not isinstance(v, list) else v}")
logA = dict(x.split("=", 1) for x in A.get("log", []))
ok_a = (logA.get("section") == "1" and logA.get("run-state", "").startswith("RUN")
        and logA.get("pause-stable") == "1" and logA.get("stop-state") in ("IDLE", "STOPPED")
        and not A.get("errs"))
B = run("b", PROBE_B, 400000, "qa-vt")
print("=== PASS B (full run) ===")
for k, v in B.items():
    print(f"  {k}: {v if not isinstance(v, list) else v}")
logB = dict(x.split("=", 1) for x in B.get("log", []))
ok_b = (logB.get("final-state") == "COMPLETE" and logB.get("done-shown") == "1"
        and int(logB.get("final-dbg-rows", "0")) >= 8
        and int(logB.get("doneBn-len", "0")) > 200
        and int(logB.get("final-rob-children", "-1")) > 5
        and not B.get("errs"))
print("PASS A:", "OK" if ok_a else "FAIL", "| PASS B:", "OK" if ok_b else "FAIL")
sys.exit(0 if (ok_a and ok_b) else 1)
