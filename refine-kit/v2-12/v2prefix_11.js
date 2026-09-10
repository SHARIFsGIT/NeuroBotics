
/* ==================================================================
   SURGICAL REFINEMENT LAYER — engine v2 (line-by-line, multi-file)
   Appended; the original application script above is untouched.
   Drives the SAME per-animation state machine created by the original
   harness (HOSTS[...]) — no second loop, no duplicates. Adds:
     1. Icon control bars (inline SVG, aria-labelled, focusable)
     2. Hero title cleanup (English primary title only)
     3. "Complete Execution — Code → Debug → Robot" final section,
        v2: TRUE line-by-line stepping (178 steps over the real 3-file
        source, 234 lines — runbook debugger + python-node two-pass),
        Code+Debug as the first row and the robot/system row below it,
        BEFORE→OPERATION→AFTER debug diff, structural/exec/event line
        kinds — and PER-STEP FILE SWITCHING (folder 10). All three
        files are stacked in one code panel; every step carries its own
        file, the panel chip + LINE n / NL denominator follow it,
        inactive files dim, launch constructor/run phases revisit lines
        like breakpoints, and the behavior node runs import pass then
        main pass then event waves on revisited lines. Line ids are
        exl-<fidx>-<ln> (collision-free).
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
  