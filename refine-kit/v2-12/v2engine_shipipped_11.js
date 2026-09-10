
  function dbgRows(rows, shadow) {
    /* BEFORE→AFTER: rows are the AFTER state of this line; when the shadow
       state already holds a different value for a key, render
       old → new so the state transition is visible (#52). */
    if (!rows || !rows.length) return '<div class="dbg-empty">— এই line-এ নতুন debug value নেই —</div>';
    return rows.map(function (r) {
      var k = r[0], v = r[1];
      var tag = r[2] === 'ill'
        ? '<span class="dbg-ill" title="illustrative — actual runtime value">illustrative</span>'
        : '';
      var cls = r[2] === 'err' ? 'dbg-v err' : 'dbg-v';
      var val;
      var before = Object.prototype.hasOwnProperty.call(shadow, k) ? shadow[k] : undefined;
      if (before !== undefined && before !== v) {
        val = '<span class="dbg-old">' + before + '</span> <span class="dbg-arrow">→</span> ' + v;
        cls += ' chg';
      } else {
        val = v;
      }
      shadow[k] = v;
      return '<div class="dbg-row"><span class="dbg-k">' + k + '</span>' +
        '<span class="' + cls + '">' + val + '</span>' + tag + '</div>';
    }).join('');
  }

  function buildExec() {
    if (!EXEC_SPEC) return;
    var spec = EXEC_SPEC;
    var FILES = (typeof FILEDATA !== 'undefined')
      ? spec.files.map(function (f) { return { name: f, lines: FILEDATA[f] }; })
      : null;
    if (!FILES || FILES.some(function (f) { return !f.lines; })) {
      console.error('exec spec: unknown files', spec.files); return;
    }
    var W = spec.w || 440, H = spec.h || 320;
    var N = spec.steps.length;
    var NL = FILES.map(function (f) { return f.lines.length; }); /* per file */
    var TOTL = FILES.reduce(function (a, f) { return a + f.lines.length; }, 0);
    function fidxOf(st) { return Math.max(0, spec.files.indexOf(st.file)); }
    var DUR = spec.defaultDurs || { struct: 480, exec: 2200, event: 2200 };
    var KIND_BN = { struct: 'structural', exec: 'exec', event: 'event' };
    function dbgIdle() {
      return (spec.dbg0 && spec.dbg0.length)
        ? dbgRows(spec.dbg0.slice(), {})
        : '<div class="dbg-empty">Play চাপলে প্রতিটি line-এর variable value এখানে দেখা যাবে — লাল চিহ্নিত <span class="dbg-old">পুরনো</span> → <span class="dbg-arrow">→</span> নতুন value আকারে।</div>';
    }

    /* stacked multi-file code card: every file in its own .exfile block,
       line ids exl-<fidx>-<ln>; the separator head names the file */
    var codeHtml = '';
    for (var fi = 0; fi < FILES.length; fi++) {
      var fl = FILES[fi].lines;
      codeHtml += '<span class="exfile-head">FILE ' + (fi + 1) + ' / ' + FILES.length +
        ' — ' + esc(FILES[fi].name) + ' (' + fl.length + ' lines)</span>' +
        '<div class="exfile" id="exfile-' + fi + '">';
      for (var i = 1; i <= fl.length; i++) {
        codeHtml += '<span class="exl" id="exl-' + fi + '-' + i + '"><span class="eln">' + i +
          '</span>' + esc(fl[i - 1]) + '</span>';
      }
      codeHtml += '</div>';
    }

    var sec = document.createElement('section');
    sec.className = 'sec exec-sec';
    sec.id = 'exec-final';
    sec.innerHTML =
      '<div class="sec-head">' +
        '<span class="badge badge-anim">EXE</span>' +
        '<h3>Complete Execution — Code → Debug → Robot</h3>' +
        '<span class="exec-sub">' + FILES.length + ' files · ' + TOTL + ' lines · ' + N + ' steps · conceptual simulation</span>' +
      '</div>' +
      '<div class="exec-note bn">' + (spec.note || '') + '</div>' +
      '<div class="exec-frame">' +
        '<div class="exec-col code-col">' +
          '<div class="exec-panel">' +
            '<div class="exec-panel-head">' +
              '<span class="ep-title">COMPLETE SOURCE CODE</span>' +
              '<span class="ep-chip src" id="exec-file">' + esc(spec.file) + '</span>' +
              '<span class="ep-chip live" id="exec-live">LINE —</span>' +
              '<span class="exec-legend" aria-hidden="true">' +
                '<i class="lg lg-exec"></i>exec' +
                '<i class="lg lg-struct"></i>structural' +
                '<i class="lg lg-event"></i>event' +
              '</span>' +
            '</div>' +
            '<pre class="exec-code" id="exec-code">' + codeHtml + '</pre>' +
          '</div>' +
        '</div>' +
        '<div class="exec-col dbg-col">' +
          '<div class="exec-panel">' +
            '<div class="exec-panel-head">' +
              '<span class="ep-title">LIVE DEBUG</span>' +
              '<span class="ep-chip concept">conceptual values</span>' +
            '</div>' +
            '<div class="exec-op" id="exec-op" hidden></div>' +
            '<div class="exec-dbg-body" id="exec-dbg">' + dbgIdle() + '</div>' +
          '</div>' +
        '</div>' +
        '<div class="exec-col rob-col">' +
          '<div class="exec-panel">' +
            '<div class="exec-panel-head"><span class="ep-title">ROBOT / SYSTEM STATE</span>' +
            '<span class="ep-chip live" id="exec-phase">IDLE</span></div>' +
            '<div class="exec-robot" id="exec-rob"></div>' +
          '</div>' +
        '</div>' +
      '</div>' +
      '<div class="exec-complete" id="exec-done">EXECUTION COMPLETE' +
        '<div class="bn" id="exec-done-bn"></div></div>' +
      '<div class="exec-fx-row" id="exec-fx-row" hidden><div class="anim-formula" id="exec-fx"></div></div>' +
      '<div class="anim-caption bn" id="exec-cap">Play চাপলে line-by-line execution শুরু হবে।</div>' +
      '<div class="anim-controls" id="exec-controls">' + iconRow() +
        '<span class="ac-sep" aria-hidden="true"></span>' +
        '<span class="ac-step" id="exec-step">STEP 000 / ' + N + '</span>' +
        '<span class="anim-state" id="exec-state">IDLE</span>' +
      '</div>' +
      '<div class="exec-progress" aria-hidden="true"><i id="exec-bar"></i></div>';

    var main = document.getElementById('main');
    if (!main) return;
    main.appendChild(sec);

    var el = {
      code: sec.querySelector('#exec-code'),
      dbg: sec.querySelector('#exec-dbg'),
      op: sec.querySelector('#exec-op'),
      rob: sec.querySelector('#exec-rob'),
      cap: sec.querySelector('#exec-cap'),
      fxRow: sec.querySelector('#exec-fx-row'),
      fx: sec.querySelector('#exec-fx'),
      state: sec.querySelector('#exec-state'),
      phase: sec.querySelector('#exec-phase'),
      step: sec.querySelector('#exec-step'),
      live: sec.querySelector('#exec-live'),
      fchip: sec.querySelector('#exec-file'),
      done: sec.querySelector('#exec-done'),
      doneBn: sec.querySelector('#exec-done-bn'),
      bar: sec.querySelector('#exec-bar'),
      controls: sec.querySelector('#exec-controls')
    };

    function robSvg(inner) {
      return '<svg viewBox="0 0 ' + W + ' ' + H + '" preserveAspectRatio="xMidYMid meet" role="img">' +
        (spec.defs || '') + inner + '</svg>';
    }
    function setRob(inner) {
      if (!inner) return;
      el.rob.innerHTML = robSvg(inner);
      el.rob.classList.remove('exec-rob-fade');
      void el.rob.offsetWidth;
      el.rob.classList.add('exec-rob-fade');
    }
    setRob(spec.rob0 || (spec.steps[0] && spec.steps[0].rob) || '');

    /* ---- one coherent exec state machine ---- */
    var X = {
      started: false, running: false, paused: false, done: false,
      stopFlag: false, speed: 1, _raf: null, gen: 0
    };
    var shadow = {};   /* accumulated variable state for BEFORE→AFTER   */
    function setState(t) { el.state.textContent = t; }
    function clearCur() {
      el.code.querySelectorAll('.exl.cur,.exl.cur-g').forEach(function (n) {
        n.classList.remove('cur', 'cur-g', 'cur-struct', 'cur-event');
      });
    }
    /* folder-10 idle: the first step's file starts active so the panel
       is never fully dimmed before Play (the idle chip already names it) */
    (function () {
      var fi0 = fidxOf(spec.steps[0]);
      el.code.querySelectorAll('.exfile').forEach(function (b, i) {
        b.classList.toggle('active', i === fi0);
      });
    })();
    function lineChip(st) {
      var nl = NL[fidxOf(st)];
      var grp = st.lns && st.lns.length > 1;
      return grp
        ? 'LINES ' + st.lns[0] + '–' + st.lns[st.lns.length - 1] + ' / ' + nl
        : 'LINE ' + st.ln + ' / ' + nl;
    }
    function applyStep(idx) {
      var st = spec.steps[idx];
      clearCur();
      var fi = fidxOf(st);
      /* file switching: chip + dimming follow the step's own file */
      if (el.fchip) el.fchip.textContent = st.file;
      el.code.querySelectorAll('.exfile').forEach(function (blk, bi) {
        blk.classList.toggle('active', bi === fi);
      });
      var primary = el.code.querySelector('#exl-' + fi + '-' + st.ln);
      var kcls = st.kind === 'struct' ? 'cur-struct' : (st.kind === 'event' ? 'cur-event' : '');
      (st.lns || [st.ln]).forEach(function (n) {
        var row = el.code.querySelector('#exl-' + fi + '-' + n);
        if (!row) return;
        /* classList.add() THROWS on an empty token (exec steps have no
           kind class) — pass it conditionally, never as '' */
        var base = n === st.ln ? 'cur' : 'cur-g';
        if (kcls) { row.classList.add(base, kcls); }
        else { row.classList.add(base); }
      });
      if (primary) {
        try {
          el.code.scrollTop = primary.offsetTop - el.code.clientHeight / 2 + primary.offsetHeight / 2;
        } catch (e) { /* keep going without scroll */ }
      }
      el.live.textContent = lineChip(st);
      el.phase.textContent = KIND_BN[st.kind] || 'exec';
      el.step.textContent = 'STEP ' + (idx + 1 < 10 ? '00' : idx + 1 < 100 ? '0' : '') + (idx + 1) +
        ' / ' + N + ' · ' + lineChip(st);
      el.bar.style.width = ((idx + 1) / N * 100).toFixed(2) + '%';
      if (st.op) { el.op.hidden = false; el.op.textContent = st.op; }
      else { el.op.hidden = true; }
      el.dbg.innerHTML = dbgRows(st.dbg, shadow);
      el.cap.innerHTML = st.cap || '';
      if (st.fx) { el.fxRow.hidden = false; el.fx.innerHTML = st.fx; }
      else { el.fxRow.hidden = true; }
      if (st.rob) setRob(st.rob);
    }
    function complete() {
      X.done = true; X.running = false; X.started = false;
      clearCur();
      setState('COMPLETE');
      el.phase.textContent = 'DONE';
      el.step.textContent = 'EXECUTION COMPLETE · ' + N + ' STEPS · ' + TOTL +
        ' LINES · ' + FILES.length + ' FILES';
      if (el.fchip) el.fchip.textContent = FILES.length + ' files';
      el.live.textContent = 'LINE —';
      el.bar.style.width = '100%';
      el.doneBn.innerHTML = spec.finalCap || '';
      el.done.classList.add('show');
      if (spec.finalOp) { el.op.hidden = false; el.op.textContent = spec.finalOp; }
      if (spec.finalDbg) el.dbg.innerHTML = dbgRows(spec.finalDbg, shadow);
      if (spec.finalRob) setRob(spec.finalRob);
      if (spec.finalFx !== undefined && spec.finalFx !== null) {
        el.fxRow.hidden = false; el.fx.innerHTML = spec.finalFx;
      }
      setActive(el.controls, null);
    }
    function sched(ms) {
      return new Promise(function (resolve) {
        var g = X.gen;
        var total = ms / X.speed, elapsed = 0, last = null;
        /* QA hook (#qa-vt): headless Chrome's virtual-time clock drives
           timers but never issues BeginFrames, so requestAnimationFrame
           stalls and automated runs freeze on step 1. Under the hash the
           identical accumulator runs on a 40ms interval instead. Real
           pages never carry the hash, so they always use rAF below. */
        if (/qa-vt/.test(location.hash)) {
          var iv = setInterval(function () {
            if (X.stopFlag || X.gen !== g) { clearInterval(iv); resolve('stopped'); return; }
            if (X.running) elapsed += 40;
            if (elapsed >= total) { clearInterval(iv); resolve(); }
          }, 40);
          return;
        }
        function tick(t) {
          if (X.stopFlag || X.gen !== g) { resolve('stopped'); return; }
          if (!X.running) { last = null; X._raf = requestAnimationFrame(tick); return; }
          if (last === null) last = t;
          elapsed += t - last; last = t;
          if (elapsed >= total) { resolve(); return; }
          X._raf = requestAnimationFrame(tick);
        }
        X._raf = requestAnimationFrame(tick);
      });
    }
    function resetIdle() {
      X.started = false; X.running = false; X.paused = false;
      X.stopFlag = false; X.done = false;
      if (X._raf) cancelAnimationFrame(X._raf);
      clearCur();
      shadow = {};
      setState('IDLE');
      el.phase.textContent = 'IDLE';
      el.step.textContent = 'STEP 000 / ' + N;
      el.live.textContent = 'LINE —';
      el.bar.style.width = '0%';
      el.op.hidden = true;
      el.done.classList.remove('show');
      el.cap.innerHTML = 'Play চাপলে line-by-line execution শুরু হবে।';
      el.fxRow.hidden = true; el.fx.innerHTML = '';
      el.dbg.innerHTML = dbgIdle();
      setRob(spec.rob0 || (spec.steps[0] && spec.steps[0].rob) || '');
      setActive(el.controls, null);
    }
    async function run() {
      var g = X.gen;
      for (var idx = 0; idx < N; idx++) {
        if (X.stopFlag || X.gen !== g) return;
        try { applyStep(idx); } catch (e) { console.error('exec step failed', idx, e); }
        var st = spec.steps[idx];
        var base = st.dur != null ? st.dur : (DUR[st.kind] != null ? DUR[st.kind] : (spec.stepDur || 2200));
        await sched(base);
        if (X.stopFlag || X.gen !== g) return;
      }
      if (X.gen !== g) return;
      complete();
    }
    function start(speed) {
      X.gen++;
      X.done = false;
      if (speed) X.speed = speed;
      X.started = true; X.stopFlag = false; X.running = true; X.paused = false;
      shadow = {};
      el.done.classList.remove('show');
      setState('RUN ' + X.speed + 'x');
      setTimeout(function () {
        run().catch(function (e) {
          console.error('exec run error', e);
          setState('ERROR');
        });
      }, 30);
    }
    function pause() { if (!X.started) return; X.running = false; X.paused = true; setState('PAUSED'); }
    function resume() {
      if (!X.started || !X.paused) return;
      X.running = true; X.paused = false; setState('RUN ' + X.speed + 'x');
    }
    function setSpeed(s) {
      X.speed = s;
      if (!X.started) { start(s); return; }
      if (X.paused) { X.running = true; X.paused = false; }
      setState('RUN ' + X.speed + 'x');
    }
    function stop() { X.gen++; X.stopFlag = true; resetIdle(); }

    el.controls.querySelectorAll('.ac-btn').forEach(function (b) {
      b.addEventListener('click', function () {
        var a = b.dataset.ac;
        setActive(el.controls, a === 'stop' ? null : b);
        if (a === 'play') { X.paused ? resume() : start(1); }
        else if (a === 'slow') setSpeed(0.5);
        else if (a === 'fast') setSpeed(1.5);
        else if (a === 'pause') pause();
        else if (a === 'stop') stop();
      });
    });
  }

  /* ---------- multi-file code-card styles (folder 10) --------------- */
  function injectExecCss() {
    var css = '.exec-code .exfile-head{display:block;padding:5px 10px 4px;margin:6px 0 2px;' +
      'font:600 9.5px/1.3 ui-monospace,Consolas,monospace;letter-spacing:.06em;' +
      'color:#79c0ff;background:#10151d;border:1px solid #21262d;border-radius:6px}' +
      '.exec-code .exfile{transition:opacity .35s;opacity:.34}' +
      '.exec-code .exfile.active{opacity:1}' +
      '.exec-code .exfile.active .eln{color:#e3b341}';
    var s = document.createElement('style');
    s.textContent = css;
    document.head.appendChild(s);
  }

  /* ---------- boot -------------------------------------------------- */
  function boot() {
    try { injectExecCss(); } catch (e) { console.error(e); }
    try { fixHero(); } catch (e) { console.error(e); }
    try { retrofitControls(); } catch (e) { console.error(e); }
    try { buildExec(); } catch (e) { console.error('exec build failed', e); }
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else { boot(); }
})();

