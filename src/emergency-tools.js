/* ---------- Emergency tools: one shared overlay (#/emergency/tool/<name>), tourniquet timers, CPR coach ---------- */
(() => {
  const FK = window.FK;
  const esc = FK.esc;
  const pane = document.getElementById('toolPane');
  const body = document.getElementById('toolBody');
  const titleEl = document.getElementById('toolTitle');
  const pinBtn = document.getElementById('toolPin');
  const strip = document.getElementById('emActive');
  const SECTION = 'emergency';
  const NAME = /^[\w-]{1,30}$/;

  /* ---------- Registry. A tool is { label, render(el, opts), stop() }; Task 6 adds rate and burn through register(). ---------- */
  const tools = Object.create(null);
  let openName = null, pushed = false;
  const cpr = { mode: 'adult', compressionOnly: false, running: false, t0: 0, next: 0, iv: null, lastBeat: 0, lastPhase: 'compress', swapAck: 0, swapsSeen: 0, armed: 0, from: null };

  /* ---------- Screen wake lock (own lock; held while a tool is open or the CPR coach runs) ---------- */
  let lock = null, lockPending = false, wakeFailed = false;
  const wakeWanted = () => !!openName || cpr.running;
  async function wakeOn() {
    if (lock || lockPending || !wakeWanted() || document.hidden) return;
    if (!navigator.wakeLock) { wakeFailed = true; return; }
    lockPending = true;
    try {
      const l = await navigator.wakeLock.request('screen');
      if (!wakeWanted()) { l.release().catch(() => {}); return; }
      lock = l; wakeFailed = false;
      l.addEventListener('release', () => { if (lock === l) lock = null; });
    } catch { wakeFailed = true; /* denied: the coach tells the user */ }
    finally { lockPending = false; cprPaint(); }
  }
  function wakeOff() { if (lock) { const l = lock; lock = null; l.release().catch(() => {}); } }
  document.addEventListener('visibilitychange', () => { if (!document.hidden) wakeOn(); sync(); });

  /* ---------- Open / close ---------- */
  function show(name, opts) {
    const t = tools[name];
    if (openName && openName !== name) tools[openName].stop();
    else if (openName === name) t.stop();
    openName = name;
    titleEl.textContent = t.label;
    body.innerHTML = '';
    t.render(body, opts || {});
    pane.hidden = false;
    document.body.classList.add('tooling');
    syncPin();
    if (FK.recent) FK.recent.add('t:' + name);
    titleEl.focus({ preventScroll: true });
    wakeOn();
    sync();
  }
  function hide() {
    if (!openName) return;
    const t = tools[openName];
    openName = null; pushed = false;
    try { t.stop(); } finally {
      if (!cpr.running) wakeOff();
      pane.hidden = true; body.innerHTML = '';
      document.body.classList.remove('tooling');
      sync();
    }
  }
  const toolOpts = {};   // options for the open that the route handler is about to do (the address cannot carry them)
  function start(name, opts) {
    if (typeof name !== 'string' || !NAME.test(name) || !Object.hasOwn(tools, name)) return false;
    toolOpts[name] = opts || {};
    const r = FK.route.current();
    const inTool = r.tab === SECTION && r.parts[0] === 'tool';
    if (!inTool) pushed = true;
    FK.route.go('/' + SECTION + '/tool/' + name, inTool ? { replace: true } : undefined);
    delete toolOpts[name];   // the route handler took them if it ran; if the address was unchanged they must not linger
    return true;
  }
  /* Close button: step back to wherever the tool was opened from. A tool reached by a typed or reloaded address has nothing to go back to. */
  function close() {
    if (!openName) return;
    if (pushed) history.back();
    else FK.route.go('/' + SECTION, { replace: true });
  }
  function onRoute(r) {
    const isTool = r.tab === SECTION && r.parts[0] === 'tool';
    if (!isTool) { hide(); return; }
    const name = r.parts[1];
    if (!name || !Object.hasOwn(tools, name)) {   // unknown or not-yet-built tool: go home without adding history
      hide();
      queueMicrotask(() => { if (FK.route.current() === r) FK.route.go('/' + SECTION, { replace: true }); });
      return;
    }
    const opts = toolOpts[name]; delete toolOpts[name];
    if (openName === name && !opts) return;
    show(name, opts);
  }

  /* ---------- Overlay controls ---------- */
  function syncPin() {
    const pinned = !!(FK.pins && openName && FK.pins.has('t:' + openName));
    pinBtn.hidden = !FK.pins;
    pinBtn.setAttribute('aria-pressed', String(pinned));
    pinBtn.textContent = pinned ? '★' : '☆';
  }
  pinBtn.addEventListener('click', () => { if (openName && FK.pins) { FK.pins.toggle('t:' + openName); syncPin(); } });
  document.getElementById('toolClose').addEventListener('click', close);
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && openName && !e.defaultPrevented) close(); });

  FK.tools = {
    start,
    register(name, def) {
      if (typeof name !== 'string' || !NAME.test(name) || !def || typeof def.render !== 'function') return;
      tools[name] = { label: String(def.label || name), render: def.render, stop: typeof def.stop === 'function' ? def.stop : () => {} };
    },
    has: name => Object.hasOwn(tools, name),
    label: name => Object.hasOwn(tools, name) ? tools[name].label : null,
    close
  };

  /* ================= Tourniquet timers ================= */
  const LIMBS = ['Left arm', 'Right arm', 'Left leg', 'Right leg', 'Other'];
  let tqs = FK.list('tq', t => FK.okId(t.id) && FK.fin(t.start)).map(t => ({ ...t, limb: String(t.limb ?? 'Tourniquet') }));
  let tqSeq = 0, tqInt = null, confirmId = null, confirmT = null, confirmAt = 0, lastStart = { limb: '', at: 0 };
  const CONFIRM_IGNORE_MS = 700, CONFIRM_REVERT_MS = 5000;   // a bounced second tap must not delete or stop anything
  const hms = ms => {
    const s = Math.max(0, Math.floor(ms / 1000));
    return Math.floor(s / 3600) + ':' + String(Math.floor(s / 60) % 60).padStart(2, '0') + ':' + String(s % 60).padStart(2, '0');
  };
  const saveTq = () => { if (!FK.store.set('tq', tqs)) FK.toast(FK.FULL_MSG); };

  function tqRows() {
    return tqs.map(t => {
      const sure = confirmId === t.id;
      return '<div class="timer" data-id="' + esc(t.id) + '"><b data-t="' + t.start + '">' + hms(Date.now() - t.start) + '</b>' +
        '<button type="button" class="btn ' + (sure ? '' : 'ghost ') + 'x" data-act="' + (sure ? 'confirm' : 'clear') + '">' + (sure ? 'Confirm clear' : 'Clear') + '</button>' +
        '<span class="lbl">' + esc(t.limb) + ', on at ' + new Date(t.start).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) +
        (sure ? '. Only clear once responders have the time.' : '') + '</span></div>';
    }).join('');
  }
  function paintTq() {
    const list = body.querySelector('#tqList');
    if (list && openName === 'tq') list.innerHTML = tqRows();
    paintStrip();
  }
  function paintStrip() {
    if (!strip) return;
    const row = (label, time) => '<button type="button" class="em-btn em-active" data-tool="' + time.tool + '"><span>' + label + '</span>' + time.html + '</button>';
    strip.innerHTML = tqs.map(t => row('TQ ' + esc(t.limb.toLowerCase()), { tool: 'tq', html: '<b data-t="' + t.start + '">' + hms(Date.now() - t.start) + '</b>' })).join('') +
      (cpr.running ? row('CPR running, cycle ' + cprCycle(), { tool: 'cpr', html: '' }) : '');
  }
  /* Per-second update touches only the time text, so a focused button or open select is never rebuilt. */
  function tickTq() {
    document.querySelectorAll('#emActive b[data-t], #tqList b[data-t]').forEach(b => { b.textContent = hms(Date.now() - Number(b.dataset.t)); });
  }
  /* Run the per-second update only while a timer is on screen, the tab is showing and the page is visible (battery). */
  function sync() {
    const want = tqs.length && !document.hidden && FK.tab() === SECTION;
    if (want && !tqInt) { tickTq(); tqInt = setInterval(tickTq, 1000); }
    if (!want && tqInt) { clearInterval(tqInt); tqInt = null; }
  }
  function setConfirm(id) {
    confirmId = id; confirmAt = Date.now(); clearTimeout(confirmT);
    if (id) confirmT = setTimeout(() => { confirmId = null; paintTq(); }, CONFIRM_REVERT_MS);
  }

  tools.tq = {
    label: 'Tourniquet timers',
    render(el, opts) {
      el.innerHTML = '<p class="tq-ask">Which limb? Tap one to start its timer.</p><div class="em-grid">' +
        LIMBS.map(l => '<button type="button" class="btn pp-wide" data-limb="' + l + '">' + l + '</button>').join('') + '</div><div id="tqList"></div>' +
        '<p class="hint" style="margin-top:8px">Timers keep running if you close the app. Tell responders the time each tourniquet went on, and write it on the tourniquet or casualty if you can.</p>';
      el.querySelector('.em-grid').addEventListener('click', e => {
        const b = e.target.closest('[data-limb]'); if (!b) return;
        const limb = b.dataset.limb, now = Date.now();
        if (limb === lastStart.limb && now - lastStart.at < CONFIRM_IGNORE_MS) return;   // double tap: one timer
        lastStart = { limb, at: now };
        tqs.push({ id: now.toString(36) + (tqSeq++ % 36).toString(36), limb, start: now });
        saveTq(); paintTq(); sync();
        if (typeof FK.log === 'function') FK.log('Tourniquet applied: ' + limb);
      });
      el.querySelector('#tqList').addEventListener('click', e => {
        const b = e.target.closest('button[data-act]'); if (!b) return;
        const id = b.closest('.timer').dataset.id;
        if (b.dataset.act === 'clear') { setConfirm(id); paintTq(); return; }
        if (Date.now() - confirmAt < CONFIRM_IGNORE_MS) return;
        tqs = tqs.filter(x => x.id !== id); setConfirm(null);
        saveTq(); paintTq(); sync();
      });
      paintTq();
    },
    stop() { setConfirm(null); }
  };
  FK.tools.tq = { active: () => tqs.map(t => ({ id: t.id, limb: t.limb, start: t.start })) };

  /* ================= CPR coach ================= */
  const CPR_RATE = 110, CPR_HOLD_MS = 4000, CPR_SWAP_MS = 120000, CPR_DEFAULT = { compressions: 30, breaths: 2 };
  const CPR_MODES = [['adult', 'Adult'], ['child', 'Child'], ['infant', 'Infant']];
  const posInt = v => Number.isInteger(v) && v > 0 && v <= 99;

  /* Pure function of elapsed milliseconds: where the coach is, so a throttled timer can never drift the count.
     cfg: { compressions, breaths, compressionOnly }. Returns
     { phase: 'compress'|'breaths', count, cycle, beats, swaps }. */
  function cprState(elapsedMs, cfg) {
    const iv = 60000 / CPR_RATE, n = cfg.compressions, t = Math.max(0, elapsedMs);
    const work = n * iv, period = cfg.compressionOnly ? work : work + CPR_HOLD_MS;
    const cycles = Math.floor(t / period), r = t - cycles * period;
    const compressing = r < work;
    const count = compressing ? Math.min(n, Math.floor(r / iv) + 1) : n;
    const compressedMs = cycles * work + Math.min(r, work);
    return {
      phase: compressing ? 'compress' : 'breaths', count, cycle: cycles + 1,
      beats: cycles * n + count,                                  // compressions delivered so far
      swaps: Math.floor(compressedMs / CPR_SWAP_MS)               // swap prompts due so far
    };
  }
  /* Ratio from the protocol's optional coach object; anything malformed falls back to 30:2. */
  function cprRatio(mode) {
    const p = FK.protocol && FK.protocol.get ? FK.protocol.get('cpr-' + mode) : null;
    const c = p && p.coach;
    return c && posInt(c.compressions) && posInt(c.breaths) ? { compressions: c.compressions, breaths: c.breaths } : { ...CPR_DEFAULT };
  }
  /* The coach is session state, like the tourniquet timers: it keeps running (sound, count, cycles, swap timing)
     when its overlay closes, and only an explicit, confirmed Stop ends it. */
  const CPR_LOOKAHEAD_MS = 1500, CPR_LATE_MS = 200;
  let ac = null, cprView = null, armT = null, stripCycle = 0;
  function cprCfg() { return { ...cprRatio(cpr.mode), compressionOnly: cpr.compressionOnly }; }
  const cprCycle = () => cprState(performance.now() - cpr.t0, cprCfg()).cycle;
  /* Time in ms since the start at which beat number b (0-based) sounds. */
  function beatMs(b, cfg) {
    const iv = 60000 / CPR_RATE, work = cfg.compressions * iv, period = cfg.compressionOnly ? work : work + CPR_HOLD_MS;
    return Math.floor(b / cfg.compressions) * period + (b % cfg.compressions) * iv;
  }
  /* Queue one click on the audio clock, offsetMs from now. Late by more than a moment: drop it rather than bunch it. */
  function click(offsetMs, high) {
    try {
      if (!ac || offsetMs < -CPR_LATE_MS) return;
      const when = ac.currentTime + Math.max(0, offsetMs) / 1000;
      const o = ac.createOscillator(), g = ac.createGain();
      o.frequency.value = high ? 1320 : 880;
      g.gain.setValueAtTime(0.0001, when);
      g.gain.exponentialRampToValueAtTime(0.6, when + 0.005);
      g.gain.exponentialRampToValueAtTime(0.0001, when + 0.08);
      o.connect(g).connect(ac.destination); o.start(when); o.stop(when + 0.09);
    } catch { /* audio is optional */ }
  }
  const buzz = p => { try { if (navigator.vibrate) navigator.vibrate(p); } catch { /* optional */ } };
  const setText = (el, t) => { if (el.textContent !== t) el.textContent = t; };
  const plural = (n, w) => n + ' ' + w + (n === 1 ? '' : 's');
  const announce = t => { if (cprView) cprView.el.querySelector('#cprLive').textContent = t; };

  function cprPaint() {
    if (!cprView) return null;
    const q = s => cprView.el.querySelector(s);
    if (!q('#cprBtn')) return null;
    const r = cprRatio(cpr.mode);
    const s = cpr.running ? cprState(performance.now() - cpr.t0, cprCfg()) : null;
    const breathing = s && s.phase === 'breaths';
    setText(q('#cprCount'), !s ? '0' : breathing ? plural(r.breaths, 'breath') : String(s.count));
    q('#cprCount').classList.toggle('breaths', !!breathing);
    setText(q('#cprCycle'), s ? 'Cycle ' + s.cycle : '');
    setText(q('#cprBtn'), !cpr.running ? 'Start' : cpr.armed ? 'Confirm stop' : 'Stop');
    cprView.el.querySelectorAll('[data-mode]').forEach(b => { b.disabled = cpr.running; b.setAttribute('aria-pressed', String(b.dataset.mode === cpr.mode)); });
    q('#cprOnly').disabled = cpr.running;
    q('#cprOnly').setAttribute('aria-pressed', String(cpr.compressionOnly));
    q('#cprSwap').hidden = !(s && s.swaps > cpr.swapAck);
    q('#cprWake').hidden = !(cpr.running && wakeFailed);
    q('#cprSteps').hidden = !(FK.protocol && FK.protocol.get && FK.protocol.get('cpr-' + cpr.mode));
    return s;
  }
  function cprTick() {
    const cfg = cprCfg(), e = performance.now() - cpr.t0;
    // Sounds go onto the audio clock a moment ahead, so a late or throttled tick cannot drop or bunch beats.
    for (let ms = beatMs(cpr.next, cfg); ms <= e + CPR_LOOKAHEAD_MS; ms = beatMs(cpr.next, cfg)) {
      click(ms - e, cpr.next % cfg.compressions === 0);
      cpr.next++;
    }
    const s = cprPaint() || cprState(e, cfg);
    if (s.beats > cpr.lastBeat) { cpr.lastBeat = s.beats; if (s.phase === 'compress') buzz(25); }
    if (s.phase !== cpr.lastPhase) { cpr.lastPhase = s.phase; announce(s.phase === 'breaths' ? plural(cfg.breaths, 'breath') : 'Compressions'); buzz([120, 80, 120]); }
    if (s.swaps > cpr.swapsSeen) { cpr.swapsSeen = s.swaps; announce('Swap rescuers now'); click(0, true); buzz([300, 150, 300]); }
    if (s.cycle !== stripCycle) { stripCycle = s.cycle; paintStrip(); }
  }
  const cprDisarm = () => { clearTimeout(armT); cpr.armed = 0; };
  function cprStart() {
    cprDisarm();
    try {
      const AC = window.AudioContext || window.webkitAudioContext;
      if (AC) { ac = ac || new AC(); if (ac.resume) ac.resume().catch(() => {}); }
    } catch { ac = null; }
    Object.assign(cpr, { running: true, t0: performance.now(), next: 0, lastBeat: 0, lastPhase: 'compress', swapAck: 0, swapsSeen: 0 });
    stripCycle = 0;
    wakeFailed = false;
    wakeOn();
    cprTick();
    cpr.iv = setInterval(cprTick, 50);
    paintStrip();
  }
  function cprStop() {
    clearInterval(cpr.iv); cprDisarm();
    cpr.running = false;
    if (!openName) wakeOff();
    paintStrip(); cprPaint();
  }
  /* Stop takes two taps: a stray or bounced tap must never end the metronome. */
  function cprStopTap() {
    if (!cpr.armed) {
      cpr.armed = Date.now();
      armT = setTimeout(() => { cpr.armed = 0; cprPaint(); }, CONFIRM_REVERT_MS);
      cprPaint();
    } else if (Date.now() - cpr.armed >= CONFIRM_IGNORE_MS) cprStop();
  }

  tools.cpr = {
    label: 'CPR coach',
    render(el, opts) {
      if (!cpr.running) {
        const fromProto = /^cpr-(adult|child|infant)$/.exec(opts.protocol || '');
        cpr.mode = CPR_MODES.some(m => m[0] === opts.mode) ? opts.mode : fromProto ? fromProto[1] : cpr.mode;
      }
      cpr.from = opts.protocol || null;
      cprView = { el };
      el.innerHTML =
        '<div class="seg cpr-modes" role="group" aria-label="Who is it for">' +
        CPR_MODES.map(([id, label]) => '<button type="button" data-mode="' + id + '" aria-pressed="false">' + label + '</button>').join('') + '</div>' +
        '<button type="button" class="cpr-opt" id="cprOnly" aria-pressed="false">Compression only (no breaths)</button>' +
        '<p class="cpr-swap cpr-wake" id="cprWake" hidden>This phone may turn its screen off and stop the clicks. Keep the screen awake.</p>' +
        '<div class="cpr-face" id="cprFace" aria-hidden="true"><div class="cpr-count" id="cprCount">0</div><div class="cpr-cycle" id="cprCycle"></div></div>' +
        '<p class="cpr-swap" id="cprSwap" hidden><span>Swap rescuers now</span><button type="button" class="btn" id="cprSwapped">Swapped</button></p>' +
        '<button type="button" class="btn pp-wide" id="cprBtn">Start</button>' +
        '<button type="button" class="btn ghost pp-wide" id="cprSteps" hidden>Open steps</button>' +
        '<p class="hint">Clicks at ' + CPR_RATE + ' per minute. Turn your volume up. If the casualty is not breathing, call 911 if you have signal. If not, send someone for help.</p>' +
        '<div class="sr-live" id="cprLive" role="status" aria-live="polite"></div>';
      const q = s => el.querySelector(s);
      q('#cprBtn').addEventListener('click', () => { if (cpr.running) cprStopTap(); else cprStart(); cprPaint(); });
      el.addEventListener('click', e => {
        const m = e.target.closest('[data-mode]');
        if (m && !cpr.running) { cpr.mode = m.dataset.mode; cprPaint(); }
      });
      q('#cprOnly').addEventListener('click', () => { if (!cpr.running) { cpr.compressionOnly = !cpr.compressionOnly; cprPaint(); } });
      q('#cprSwapped').addEventListener('click', () => { cpr.swapAck = cpr.swapsSeen; cprPaint(); });
      q('#cprSteps').addEventListener('click', () => {
        const id = 'cpr-' + cpr.mode;
        if (cpr.from === id) close();   // came here from these steps: Back returns to the same step
        else FK.protocol.open(id);
      });
      cprPaint();
    },
    stop() { cprView = null; }   // closing the overlay never stops the coach
  };
  FK.tools.cpr = { state: cprState, running: () => cpr.running };

  /* ---------- Start ---------- */
  FK.on('route', r => { onRoute(r); sync(); });
  queueMicrotask(() => { onRoute(FK.route.current()); paintStrip(); sync(); });   // after every module has loaded and registered its tools
})();
