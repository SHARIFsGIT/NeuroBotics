/* ==================================================================
   SURGICAL REFINEMENT LAYER — engine (appended; original script above
   is untouched). Drives the SAME per-animation state machine created by
   the original harness (HOSTS[...]) — no second loop, no duplicates.
   Adds:
     1. Icon control bars (inline SVG, aria-labelled, focusable)
     2. Hero title cleanup (English primary title only)
     3. "Complete Execution — Code → Debug → Robot" final section
        driven by an embedded per-app EXEC spec with REAL line numbers.
   ================================================================== */
(function () {
  'use strict';

  /* ---------- shared inline SVG icons (self-contained, no text) ---- */
  var IC = {
    play: '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M7.5 4.8v14.4L20 12z"/></svg>',
    /* speed family: all triangles point forward; SIZE/COUNT encodes magnitude
       (1 large = 1x, 1 small = 0.5x, 2 medium = 1.5x) so the glyphs stay
       distinguishable at 15px where mirrored needles were not */
    slow: '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M9.7 8.6v6.8l5.6-3.4z"/></svg>',
    fast: '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M4.9 7.4v9.2L11.4 12zM12.6 7.4v9.2L19.1 12z"/></svg>',
    pause: '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M6.6 4.8h4.1v14.4H6.6zM13.3 4.8h4.1v14.4h-4.1z"/></svg>',
    stop: '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><rect x="5.6" y="5.6" width="12.8" height="12.8" rx="2.2"/></svg>'
  };
  var AC_TIP = {
    play: 'Play (1× speed)', slow: 'Slow (0.5× speed)',
    fast: 'Fast (1.5× speed)', pause: 'Pause', stop: 'Stop'
  };
  function iconBtn(ac) {
    return '<button type="button" class="ac-btn ic" data-ac="' + ac + '" ' +
      'title="' + AC_TIP[ac] + '" aria-label="' + AC_TIP[ac] + '" aria-pressed="false">' +
      IC[ac] + '</button>';
  }
  function iconRow() {
    return iconBtn('play') + iconBtn('slow') + iconBtn('fast') +
      '<span class="ac-sep" aria-hidden="true"></span>' +
      iconBtn('pause') + iconBtn('stop');
  }
  function setActive(bar, btn) {
    bar.querySelectorAll('.ac-btn').forEach(function (x) {
      x.classList.remove('active');
      x.setAttribute('aria-pressed', 'false');
    });
    if (btn) { btn.classList.add('active'); btn.setAttribute('aria-pressed', 'true'); }
  }

  function esc(s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  /* ---------- 1. retrofit existing animation control bars ---------- */
  function retrofitControls() {
    if (typeof HOSTS === 'undefined') return;
    document.querySelectorAll('.anim-controls').forEach(function (bar) {
      try {
        var sec = bar.closest('.sec-anim');
        if (!sec || !sec.id) return;
        var pid = sec.id.replace(/^anim-/, '');
        var host = HOSTS[pid];
        if (!host) return;
        bar.querySelectorAll('.ac-btn').forEach(function (n) { n.remove(); });
        bar.insertAdjacentHTML('afterbegin', iconRow());
        bar.querySelectorAll('.ac-btn').forEach(function (b) {
          b.addEventListener('click', function () {
            var a = b.dataset.ac;
            setActive(bar, a === 'stop' ? null : b);
            if (a === 'play') { host.userPaused ? host.resume() : host.start(1); }
            else if (a === 'slow') { host.setSpeed(0.5); }
            else if (a === 'fast') { host.setSpeed(1.5); }
            else if (a === 'pause') { host.pause(); }
            else if (a === 'stop') { host.stop(); }
          });
        });
      } catch (e) { console.error('control retrofit failed', e); }
    });
  }

  /* ---------- 2. hero title: English primary only ------------------- */
  function fixHero() {
    try {
      var sub = document.querySelector('.intro-banner h1 .path');
      if (sub) sub.remove();
    } catch (e) { /* cosmetic only */ }
  }

  /* ---------- 3. Complete Execution — Code → Debug → Robot --------- */
  var EXEC_SPEC = /*__EXEC_SPEC__*/ null;

  function dbgRows(rows) {
    if (!rows || !rows.length) return '<div class="dbg-empty">— এই step-এ নতুন debug value নেই —</div>';
    return rows.map(function (r) {
      var tag = r[2] === 'ill'
        ? '<span class="dbg-ill" title="illustrative — actual runtime value">illustrative</span>'
        : '';
      var cls = r[2] === 'err' ? 'dbg-v err' : 'dbg-v';
      return '<div class="dbg-row"><span class="dbg-k">' + r[0] + '</span>' +
        '<span class="' + cls + '">' + r[1] + '</span>' + tag + '</div>';
    }).join('');
  }

  function buildExec() {
    if (!EXEC_SPEC) return;
    var lines = (typeof FILEDATA !== 'undefined') ? FILEDATA[EXEC_SPEC.file] : null;
    if (!lines) { console.error('exec spec: unknown file', EXEC_SPEC.file); return; }
    var spec = EXEC_SPEC;
    var W = spec.w || 440, H = spec.h || 320;
    var N = spec.steps.length;
    /* idle DEBUG content: spec may prefill the program's initial state (dbg0) */
    var DBG_IDLE_HTML = (spec.dbg0 && spec.dbg0.length)
      ? dbgRows(spec.dbg0)
      : '<div class="dbg-empty">Play চাপলে প্রতিটি step-এর variable value এখানে দেখা যাবে।</div>';
    function dbgIdle() { return DBG_IDLE_HTML; }

    var codeHtml = '';
    for (var i = 1; i <= lines.length; i++) {
      codeHtml += '<span class="exl" id="exl-' + i + '"><span class="eln">' + i +
        '</span>' + esc(lines[i - 1]) + '</span>';
    }

    var sec = document.createElement('section');
    sec.className = 'sec exec-sec';
    sec.id = 'exec-final';
    sec.innerHTML =
      '<div class="sec-head">' +
        '<span class="badge badge-anim">EXE</span>' +
        '<h3>Complete Execution — Code → Debug → Robot</h3>' +
        '<span class="exec-sub">' + esc(spec.file) + ' · real line numbers · conceptual runtime</span>' +
      '</div>' +
      '<div class="exec-note bn">' + (spec.note || 'নিচের panel-এ সম্পূর্ণ source code ধরে ধরে চলবে — কোন line execute হচ্ছে, তখন variable-এর value কত, math কী বলছে এবং robot তখন কী করছে সব একসাথে দেখা যাবে। Debug value গুলো <b>conceptual</b> — source থেকে derived, runtime log নয়।') + '</div>' +
      '<div class="exec-frame">' +
        '<div class="exec-col code-col">' +
          '<div class="exec-panel">' +
            '<div class="exec-panel-head">' +
              '<span class="ep-title">CODE</span>' +
              '<span class="ep-chip src">' + esc(spec.file) + '</span>' +
              '<span class="ep-chip live" id="exec-live">LINE —</span>' +
            '</div>' +
            '<pre class="exec-code" id="exec-code">' + codeHtml + '</pre>' +
          '</div>' +
        '</div>' +
        '<div class="exec-col">' +
          '<div class="exec-panel">' +
            '<div class="exec-panel-head">' +
              '<span class="ep-title">DEBUG</span>' +
              '<span class="ep-chip concept">conceptual values</span>' +
            '</div>' +
            '<div class="exec-dbg-body" id="exec-dbg">' + dbgIdle() + '</div>' +
          '</div>' +
        '</div>' +
        '<div class="exec-col">' +
          '<div class="exec-panel">' +
            '<div class="exec-panel-head"><span class="ep-title">ROBOT / SYSTEM</span></div>' +
            '<div class="exec-robot" id="exec-rob"></div>' +
          '</div>' +
        '</div>' +
      '</div>' +
      '<div class="anim-controls" id="exec-controls">' + iconRow() +
        '<span class="ac-sep" aria-hidden="true"></span>' +
        '<span class="ac-step" id="exec-step">STEP 00 / ' + N + '</span>' +
        '<span class="anim-state" id="exec-state">IDLE</span>' +
      '</div>' +
      '<div class="exec-complete" id="exec-done">EXECUTION COMPLETE' +
        '<div class="bn" id="exec-done-bn"></div></div>' +
      '<div class="anim-caption bn" id="exec-cap">Play চাপলে সম্পূর্ণ execution শুরু হবে।</div>' +
      '<div class="anim-formula" id="exec-fx"></div>';

    var main = document.getElementById('main');
    if (!main) return;
    main.appendChild(sec);

    var el = {
      code: sec.querySelector('#exec-code'),
      dbg: sec.querySelector('#exec-dbg'),
      rob: sec.querySelector('#exec-rob'),
      cap: sec.querySelector('#exec-cap'),
      fx: sec.querySelector('#exec-fx'),
      state: sec.querySelector('#exec-state'),
      step: sec.querySelector('#exec-step'),
      live: sec.querySelector('#exec-live'),
      done: sec.querySelector('#exec-done'),
      doneBn: sec.querySelector('#exec-done-bn'),
      controls: sec.querySelector('#exec-controls')
    };

    function robSvg(inner) {
      return '<svg viewBox="0 0 ' + W + ' ' + H + '" preserveAspectRatio="xMidYMid meet" role="img">' +
        (spec.defs || '') + inner + '</svg>';
    }
    function setRob(inner) {
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
    function setState(t) { el.state.textContent = t; }
    function clearCur() {
      var c = el.code.querySelector('.exl.cur');
      if (c) c.classList.remove('cur');
    }
    function applyStep(idx) {
      var st = spec.steps[idx];
      clearCur();
      var row = el.code.querySelector('#exl-' + st.ln);
      if (row) {
        row.classList.add('cur');
        try {
          el.code.scrollTop = row.offsetTop - el.code.clientHeight / 2 + row.offsetHeight / 2;
        } catch (e) { /* keep going without scroll */ }
      }
      el.live.textContent = 'LINE ' + st.ln;
      el.step.textContent = 'STEP ' + (idx + 1 < 10 ? '0' : '') + (idx + 1) + ' / ' + N +
        ' · LINE ' + st.ln;
      el.dbg.innerHTML = dbgRows(st.dbg);
      el.cap.innerHTML = st.cap || '';
      el.fx.innerHTML = st.fx || '';
      if (st.rob) setRob(st.rob);
    }
    function complete() {
      X.done = true; X.running = false; X.started = false;
      clearCur();
      setState('COMPLETE');
      el.step.textContent = 'EXECUTION COMPLETE · ' + N + ' STEPS';
      el.live.textContent = 'LINE —';
      el.doneBn.innerHTML = spec.finalCap || '';
      el.done.classList.add('show');
      if (spec.finalDbg) el.dbg.innerHTML = dbgRows(spec.finalDbg);
      if (spec.finalRob) setRob(spec.finalRob);
      if (spec.finalFx !== undefined) el.fx.innerHTML = spec.finalFx;
      setActive(el.controls, null);
    }
    function sched(ms) {
      return new Promise(function (resolve) {
        var g = X.gen;
        var total = ms / X.speed, elapsed = 0, last = null;
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
      setState('IDLE');
      el.step.textContent = 'STEP 00 / ' + N;
      el.live.textContent = 'LINE —';
      el.done.classList.remove('show');
      el.cap.innerHTML = 'Play চাপলে সম্পূর্ণ execution শুরু হবে।';
      el.fx.innerHTML = '';
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
        await sched(st.dur != null ? st.dur : (spec.stepDur || 2200));
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
      setState('RUN ' + s + 'x');
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

  /* ---------- boot -------------------------------------------------- */
  function boot() {
    try { fixHero(); } catch (e) { console.error(e); }
    try { retrofitControls(); } catch (e) { console.error(e); }
    try { buildExec(); } catch (e) { console.error('exec build failed', e); }
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else { boot(); }
})();
