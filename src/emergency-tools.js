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
  const SEGMENTS = ['tool', 'report'];   // address segment a tool lives under: #/emergency/tool/<name> or #/emergency/report/<name>

  /* ---------- Registry. A tool is { label, render(el, opts), stop() }; Task 6 adds rate and burn through register(). ---------- */
  const tools = Object.create(null);
  let openName = null, pushed = false;
  const cpr = { mode: 'adult', compressionOnly: false, running: false, t0: 0, next: 0, iv: null, lastBeat: 0, lastPhase: 'compress', swapAck: 0, swapsSeen: 0, armedAt: null, from: null, bus: null, nodes: [] };

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
    finally { lockPending = false; cprPaint(); if (cpr.running) paintStrip(); }
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
    if (FK.recent) FK.recent.add(keyOf(name));
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
  const segOf = name => tools[name].segment || 'tool';   // tools defined directly (tq, cpr) have no segment field
  const keyOf = name => (segOf(name) === 'report' ? 'r:' : 't:') + name;   // pins and recent
  const toolOpts = {};   // options for the open that the route handler is about to do (the address cannot carry them)
  /* opts.replace: take over the current address entry instead of adding one (search uses it, so Back skips the search entry). Not passed on to the tool. */
  function start(name, opts) {
    if (typeof name !== 'string' || !NAME.test(name) || !Object.hasOwn(tools, name)) return false;
    const { replace, ...toolArgs } = opts || {};
    toolOpts[name] = toolArgs;
    const r = FK.route.current();
    const inTool = r.tab === SECTION && SEGMENTS.includes(r.parts[0]);
    if (!inTool) pushed = true;
    FK.route.go('/' + SECTION + '/' + segOf(name) + '/' + name, inTool || replace ? { replace: true } : undefined);
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
    const isTool = r.tab === SECTION && SEGMENTS.includes(r.parts[0]);
    if (!isTool) { hide(); return; }
    const name = r.parts[1];
    if (!name || !Object.hasOwn(tools, name) || segOf(name) !== r.parts[0]) {   // unknown or not-yet-built tool: go home without adding history
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
    const pinned = !!(FK.pins && openName && FK.pins.has(keyOf(openName)));
    pinBtn.hidden = !FK.pins;
    pinBtn.setAttribute('aria-pressed', String(pinned));
    pinBtn.textContent = pinned ? '★' : '☆';
  }
  pinBtn.addEventListener('click', () => { if (openName && FK.pins) { FK.pins.toggle(keyOf(openName)); syncPin(); } });
  document.getElementById('toolClose').addEventListener('click', close);
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && openName && !e.defaultPrevented) close(); });

  FK.tools = {
    start,
    confirm: { ignoreMs: 700, revertMs: 5000 },   // shared two-step confirm timing (second tap ignored for ignoreMs, reverts after revertMs)
    register(name, def) {
      if (typeof name !== 'string' || !NAME.test(name) || !def || typeof def.render !== 'function') return;
      tools[name] = { label: String(def.label || name), segment: def.segment === 'report' ? 'report' : 'tool', render: def.render, stop: typeof def.stop === 'function' ? def.stop : () => {} };
    },
    has: name => Object.hasOwn(tools, name),
    list: () => Object.keys(tools).map(name => ({ name, label: tools[name].label, segment: segOf(name) })),
    label: name => Object.hasOwn(tools, name) ? tools[name].label : null,
    segment: name => Object.hasOwn(tools, name) ? segOf(name) : null,
    close
  };

  /* ================= Tourniquet timers ================= */
  const LIMBS = ['Left arm', 'Right arm', 'Left leg', 'Right leg', 'Other'];
  let tqs = FK.list('tq', t => FK.okId(t.id) && FK.fin(t.start)).map(t => ({ ...t, limb: String(t.limb ?? 'Tourniquet') }));
  let tqSeq = 0, tqInt = null, confirmId = null, confirmT = null, confirmAt = 0, lastStart = { limb: '', at: 0 };
  const CONFIRM_IGNORE_MS = FK.tools.confirm.ignoreMs, CONFIRM_REVERT_MS = FK.tools.confirm.revertMs;   // a bounced second tap must not delete or stop anything
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
      (cpr.running ? row('CPR running, cycle ' + cprCycle() + (wakeFailed ? ', screen may sleep' : ''), { tool: 'cpr', html: '' }) : '');
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
    confirmId = id; confirmAt = performance.now(); clearTimeout(confirmT);
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
        const limb = b.dataset.limb, now = Date.now(), mono = performance.now();
        if (limb === lastStart.limb && mono - lastStart.at < CONFIRM_IGNORE_MS) return;   // double tap: one timer
        lastStart = { limb, at: mono };
        tqs.push({ id: now.toString(36) + (tqSeq++ % 36).toString(36), limb, start: now });
        saveTq(); paintTq(); sync();
        if (typeof FK.log === 'function') FK.log('Tourniquet applied: ' + limb);
      });
      el.querySelector('#tqList').addEventListener('click', e => {
        const b = e.target.closest('button[data-act]'); if (!b) return;
        const id = b.closest('.timer').dataset.id;
        if (b.dataset.act === 'clear') { setConfirm(id); paintTq(); return; }
        if (performance.now() - confirmAt < CONFIRM_IGNORE_MS) return;
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
  /* Queue one click on the audio clock, offsetMs from now. Late by more than a moment: drop it rather than bunch it.
     Every click of a run goes through that run's own gain node, so Stop can silence what is already queued ahead. */
  function click(offsetMs, high) {
    try {
      if (!ac || !cpr.bus || offsetMs < -CPR_LATE_MS) return;
      const when = ac.currentTime + Math.max(0, offsetMs) / 1000;
      cpr.nodes = cpr.nodes.filter(n => n.end > ac.currentTime);
      const o = ac.createOscillator(), g = ac.createGain();
      o.frequency.value = high ? 1320 : 880;
      g.gain.setValueAtTime(0.0001, when);
      g.gain.exponentialRampToValueAtTime(0.6, when + 0.005);
      g.gain.exponentialRampToValueAtTime(0.0001, when + 0.08);
      o.connect(g).connect(cpr.bus); o.start(when); o.stop(when + 0.09);
      cpr.nodes.push({ o, end: when + 0.09 });
    } catch { /* audio is optional */ }
  }
  function silence() {
    const { nodes, bus } = cpr;
    cpr.nodes = []; cpr.bus = null;
    nodes.forEach(n => { try { n.o.stop(); } catch { /* already finished */ } });
    try { if (bus) bus.disconnect(); } catch { /* optional */ }
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
    setText(q('#cprBtn'), !cpr.running ? 'Start' : cpr.armedAt !== null ? 'Confirm stop' : 'Stop');
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
  const cprDisarm = () => { clearTimeout(armT); cpr.armedAt = null; };
  function cprStart() {
    cprDisarm();
    try {
      const AC = window.AudioContext || window.webkitAudioContext;
      if (AC) { ac = ac || new AC(); if (ac.resume) ac.resume().catch(() => {}); }
    } catch { ac = null; }
    silence();
    try { if (ac) { cpr.bus = ac.createGain(); cpr.bus.connect(ac.destination); } } catch { cpr.bus = null; }
    Object.assign(cpr, { running: true, t0: performance.now(), next: 0, lastBeat: 0, lastPhase: 'compress', swapAck: 0, swapsSeen: 0 });
    stripCycle = 0;
    wakeFailed = false;
    wakeOn();
    cprTick();
    cpr.iv = setInterval(cprTick, 50);
    paintStrip();
    if (typeof FK.log === 'function') FK.log('CPR started (' + cpr.mode + ')');
  }
  function cprStop() {
    const done = cprState(performance.now() - cpr.t0, cprCfg()).cycle - 1;   // whole cycles finished
    clearInterval(cpr.iv); cprDisarm(); silence();
    cpr.running = false;
    if (!openName) wakeOff();
    paintStrip(); cprPaint();
    if (typeof FK.log === 'function') FK.log('CPR stopped after ' + plural(done, 'cycle'));
  }
  /* Stop takes two taps: a stray or bounced tap must never end the metronome. */
  function cprStopTap() {
    if (cpr.armedAt === null) {
      cpr.armedAt = performance.now();
      armT = setTimeout(() => { cpr.armedAt = null; cprPaint(); }, CONFIRM_REVERT_MS);
      cprPaint();
    } else if (performance.now() - cpr.armedAt >= CONFIRM_IGNORE_MS) cprStop();
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
      q('#cprBtn').addEventListener('click', () => {
        if (cpr.running && performance.now() - cpr.t0 < CONFIRM_IGNORE_MS) return;   // a bounced tap right after Start
        if (cpr.running) cprStopTap(); else cprStart();
        cprPaint();
      });
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

  /* ================= Rate counter: tap each beat or breath for 15 seconds, result = taps x 4 ================= */
  const RATE_WINDOW_MS = 15000;
  const rate = { t0: null, taps: 0, iv: null, el: null };
  const rateDone = () => rate.t0 !== null && performance.now() - rate.t0 >= RATE_WINDOW_MS;
  function ratePaint() {
    const el = rate.el; if (!el || !el.querySelector('#rateTap')) return;
    const done = rateDone();
    if (done && rate.iv) { clearInterval(rate.iv); rate.iv = null; }
    const left = rate.t0 === null ? RATE_WINDOW_MS : Math.max(0, RATE_WINDOW_MS - (performance.now() - rate.t0));
    setText(el.querySelector('#rateClock'), done ? 'Time is up' : Math.ceil(left / 1000) + ' seconds left');
    setText(el.querySelector('#rateCount'), rate.taps + (rate.taps === 1 ? ' tap' : ' taps'));
    setText(el.querySelector('#rateResult'), done ? String(rate.taps * 4) : '');
    el.querySelector('#rateUnit').hidden = !done;
    el.querySelector('#rateTap').disabled = done;
    el.querySelector('#rateSave').hidden = !done || rate.taps === 0;
  }
  function rateReset() {
    clearInterval(rate.iv); rate.iv = null; rate.t0 = null; rate.taps = 0;
    ratePaint();
  }
  function rateTap() {
    const now = performance.now();
    if (rate.t0 === null) { rate.t0 = now; rate.iv = setInterval(ratePaint, 100); }
    else if (now - rate.t0 >= RATE_WINDOW_MS) { ratePaint(); return; }   // after the window: ignored
    rate.taps++;
    ratePaint();
  }
  function rateSave(kind) {
    if (!FK.patients || !rateDone() || !rate.taps) return;
    const n = rate.taps * 4;
    const ok = kind === 'pulse' ? n <= 300 : n <= 120;
    if (!ok) { FK.toast('That rate is too high to save. Count again.'); return; }
    const e = kind === 'pulse' ? { kind: 'vitals', text: 'Vitals: pulse ' + n + ' (counted for 15 seconds)', pulse: n } : { kind: 'vitals', text: 'Vitals: breathing ' + n + ' (counted for 15 seconds)', resp: n };
    if (FK.patients.add(e)) FK.toast('Saved to ' + FK.patients.current().name);
  }
  FK.tools.register('rate', {
    label: 'Rate counter',
    render(el) {
      rate.el = el; rate.t0 = null; rate.taps = 0;
      el.innerHTML =
        '<p class="tq-ask">Tap once for every beat or breath. The 15 seconds start on your first tap.</p>' +
        '<button type="button" class="rate-tap" id="rateTap">TAP</button>' +
        '<p class="rate-clock" id="rateClock" role="timer"></p><p class="rate-count" id="rateCount"></p>' +
        '<p class="rate-out"><b id="rateResult" aria-live="polite"></b> <span id="rateUnit" hidden>per minute</span></p>' +
        '<div id="rateSave" hidden><button type="button" class="btn pp-wide" id="rateSavePulse">Save as pulse</button>' +
        '<button type="button" class="btn pp-wide" id="rateSaveResp">Save as breathing</button></div>' +
        '<button type="button" class="btn ghost pp-wide" id="rateRestart">Restart</button>';
      el.querySelector('#rateTap').addEventListener('click', rateTap);
      el.querySelector('#rateRestart').addEventListener('click', rateReset);
      el.querySelector('#rateSavePulse').addEventListener('click', () => rateSave('pulse'));
      el.querySelector('#rateSaveResp').addEventListener('click', () => rateSave('resp'));
      ratePaint();
    },
    stop() { clearInterval(rate.iv); rate.iv = null; rate.el = null; }
  });

  /* ================= Burn area ================= */
  /* Region percentages by age group. Kept as one constant so it can be corrected from the medical source in one place.
     Every table must add up to 100. */
  const BURN_TABLES = {
    adult: [
      { id: 'head', name: 'Head', pct: 9 }, { id: 'armL', name: 'Left arm', pct: 9 }, { id: 'armR', name: 'Right arm', pct: 9 },
      { id: 'chest', name: 'Chest', pct: 9 }, { id: 'abdomen', name: 'Abdomen', pct: 9 },
      { id: 'upperBack', name: 'Upper back', pct: 9 }, { id: 'lowerBack', name: 'Lower back', pct: 9 },
      { id: 'legL', name: 'Left leg', pct: 18 }, { id: 'legR', name: 'Right leg', pct: 18 }, { id: 'groin', name: 'Groin', pct: 1 }
    ],
    child: [
      { id: 'head', name: 'Head', pct: 18 }, { id: 'armL', name: 'Left arm', pct: 9 }, { id: 'armR', name: 'Right arm', pct: 9 },
      { id: 'torsoF', name: 'Front of body', pct: 18 }, { id: 'torsoB', name: 'Back of body', pct: 18 },
      { id: 'legL', name: 'Left leg', pct: 14 }, { id: 'legR', name: 'Right leg', pct: 14 }
    ]
  };
  /* Figure layout, one 160 x 352 box per view (front above back): [region, view, x offset from the figure centre, y, width, height, short label, true if drawn only as a non-focusable duplicate of the region's main shape].
     A casualty's left is on the viewer's right in the front view and on the viewer's left in the back view. */
  const BURN_CX = 80;
  const burnBody = torso => {
    const arm = (id, view, label) => [id, view, (id === 'armL') === (view === 'front') ? 31 : -79, 54, 48, 146, label, view === 'back'];
    const leg = (id, view, label) => [id, view, (id === 'legL') === (view === 'front') ? 2 : -52, 230, 50, 122, label, view === 'back'];
    return [
      ['head', 'front', -24, 4, 48, 48, 'Head'], ['head', 'back', -24, 4, 48, 48, 'Head', true],
      arm('armL', 'front', 'L arm'), arm('armR', 'front', 'R arm'), arm('armL', 'back', 'L arm'), arm('armR', 'back', 'R arm'),
      leg('legL', 'front', 'L leg'), leg('legR', 'front', 'R leg'), leg('legL', 'back', 'L leg'), leg('legR', 'back', 'R leg'),
      ...torso
    ];
  };
  const BURN_LAYOUT = {
    adult: burnBody([
      ['chest', 'front', -28, 54, 56, 60, 'Chest'], ['abdomen', 'front', -28, 114, 56, 60, 'Abdomen'], ['groin', 'front', -24, 176, 48, 48, 'Groin'],
      ['upperBack', 'back', -28, 54, 56, 60, 'Upper back'], ['lowerBack', 'back', -28, 114, 56, 60, 'Lower back']
    ]),
    child: burnBody([['torsoF', 'front', -28, 54, 56, 170, 'Front'], ['torsoB', 'back', -28, 54, 56, 170, 'Back']])
  };
  const burn = { mode: 'adult', sel: new Set(), el: null };
  const burnTotal = () => BURN_TABLES[burn.mode].reduce((n, r) => n + (burn.sel.has(r.id) ? r.pct : 0), 0);
  function burnFigure() {
    const table = BURN_TABLES[burn.mode];
    const svg = (view, first) => {
      const shapes = BURN_LAYOUT[burn.mode].filter(r => r[1] === view).map(([id, , dx, y, w, h, label, dup]) => {
        const r = table.find(t => t.id === id), x = BURN_CX + dx, cx = x + w / 2, cy = y + h / 2;
        const body = '<rect class="bz" x="' + x + '" y="' + y + '" width="' + w + '" height="' + h + '" rx="8"/>' +
          '<text class="bz-t" x="' + cx + '" y="' + (cy - 9) + '" text-anchor="middle">' + esc(label) + '</text>' +
          '<text class="bz-t" x="' + cx + '" y="' + (cy + 5) + '" text-anchor="middle">' + r.pct + '%</text>' +
          '<text class="bz-c" x="' + cx + '" y="' + (cy + 20) + '" text-anchor="middle">✓</text>';
        return dup
          ? '<g class="bz-g dup" data-r="' + id + '" aria-hidden="true">' + body + '</g>'
          : '<g class="bz-g" data-r="' + id + '" role="button" tabindex="0" aria-pressed="false" aria-label="' + esc(r.name) + ', ' + r.pct + ' percent">' + body + '</g>';
      }).join('');
      return '<p class="burn-cap">' + (view === 'front' ? 'Front' : 'Back') + '</p><svg class="burn-svg" viewBox="0 0 160 352" role="group" aria-label="Body outline, ' + view + ' view">' +
        (first ? '<defs><pattern id="burnHatch" width="8" height="8" patternUnits="userSpaceOnUse"><rect width="8" height="8" style="fill:var(--surface)"/>' +
        '<path d="M-2 2L2 -2M0 8L8 0M6 10L10 6" style="stroke:var(--blaze);stroke-width:2.5"/></pattern></defs>' : '') + shapes + '</svg>';
    };
    return svg('front', true) + svg('back', false);
  }
  function burnNotes() {
    const p = FK.protocol && FK.protocol.get ? FK.protocol.get('burns') : null;
    const n = p && Array.isArray(p.notes) ? p.notes.filter(x => typeof x === 'string' && x.trim()) : [];
    return n.map(x => '<p>' + esc(x) + '</p>').join('');
  }
  function burnGuide() {
    const p = FK.protocol && FK.protocol.get ? FK.protocol.get('burns') : null;
    const ev = p && Array.isArray(p.evacuate) ? p.evacuate.filter(x => typeof x === 'string' && x.trim()) : [];
    return ev.length ? '<h3>Evacuate when</h3><ul>' + ev.map(x => '<li>' + esc(x) + '</li>').join('') + '</ul>' : '';
  }
  function burnPaint() {
    const el = burn.el; if (!el || !el.querySelector('#burnSvg')) return;
    el.querySelectorAll('#burnSvg [data-r]').forEach(g => {
      const on = burn.sel.has(g.dataset.r);
      g.classList.toggle('on', on);
      if (g.hasAttribute('role')) g.setAttribute('aria-pressed', String(on));
    });
    el.querySelectorAll('#burnMode [data-mode]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.mode === burn.mode)));
    const picked = BURN_TABLES[burn.mode].filter(r => burn.sel.has(r.id));
    el.querySelector('#burnTotal').textContent = burnTotal() + '%';
    el.querySelector('#burnList').textContent = picked.length ? 'Selected: ' + picked.map(r => r.name + ' ' + r.pct + '%').join(', ') : 'Nothing selected. Tap the burned areas.';
    el.querySelector('#burnSave').disabled = !picked.length;
    el.querySelector('#burnClear').disabled = !picked.length;
  }
  function burnSet(mode) {
    burn.mode = mode; burn.sel = new Set();
    burn.el.querySelector('#burnSvg').innerHTML = burnFigure();
    burnPaint();
  }
  function burnToggle(id) {
    if (!BURN_TABLES[burn.mode].some(r => r.id === id)) return;
    if (!burn.sel.delete(id)) burn.sel.add(id);
    burnPaint();
  }
  FK.tools.register('burn', {
    label: 'Burn area',
    render(el) {
      burn.el = el; burn.sel = new Set(); burn.mode = 'adult';
      el.innerHTML =
        '<div class="seg cpr-modes" id="burnMode" role="group" aria-label="Who is burned">' +
        '<button type="button" data-mode="adult" aria-pressed="false">Adult</button><button type="button" data-mode="child" aria-pressed="false">Child</button></div>' +
        '<div class="burn-total"><b id="burnTotal" aria-live="polite">0%</b><span>of the body surface (estimate)</span></div>' +
        '<div id="burnNotes" class="burn-notes">' + burnNotes() + '</div><div id="burnSvg"></div><p id="burnList" class="burn-list"></p>' +
        '<div class="burn-act"><button type="button" class="btn pp-wide" id="burnSave">Save to patient log</button>' +
        '<button type="button" class="btn ghost pp-wide" id="burnClear">Clear</button></div>' +
        '<div id="burnGuide" class="pp-sec">' + burnGuide() + '</div>';
      el.querySelector('#burnSvg').innerHTML = burnFigure();
      el.querySelector('#burnSvg').addEventListener('click', e => { const g = e.target.closest('[data-r]'); if (g) burnToggle(g.dataset.r); });
      el.querySelector('#burnSvg').addEventListener('keydown', e => {
        const g = e.target.closest('[role="button"][data-r]');
        if (g && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); burnToggle(g.dataset.r); }
      });
      el.querySelector('#burnMode').addEventListener('click', e => { const b = e.target.closest('[data-mode]'); if (b && b.dataset.mode !== burn.mode) burnSet(b.dataset.mode); });
      el.querySelector('#burnClear').addEventListener('click', () => { burn.sel = new Set(); burnPaint(); });
      el.querySelector('#burnSave').addEventListener('click', () => {
        const picked = BURN_TABLES[burn.mode].filter(r => burn.sel.has(r.id));
        if (!picked.length || !FK.patients) return;
        const t = 'Burn area about ' + burnTotal() + '% (' + burn.mode + '): ' + picked.map(r => r.name.toLowerCase()).join(', ');
        if (FK.patients.add({ kind: 'note', text: t })) FK.toast('Saved to ' + FK.patients.current().name);
      });
      burnPaint();
    },
    stop() { burn.el = null; }
  });

  /* ---------- Start ---------- */
  FK.on('route', r => { onRoute(r); sync(); });
  queueMicrotask(() => { onRoute(FK.route.current()); paintStrip(); sync(); });   // after every module has loaded and registered its tools
})();
