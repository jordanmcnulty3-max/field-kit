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

  /* ---------- Screen wake lock (own lock; silent where unsupported) ---------- */
  let lock = null, lockPending = false;
  async function wakeOn() {
    if (lock || lockPending || !openName || document.hidden || !navigator.wakeLock) return;
    lockPending = true;
    try {
      const l = await navigator.wakeLock.request('screen');
      if (!openName) { l.release().catch(() => {}); return; }
      lock = l;
      l.addEventListener('release', () => { if (lock === l) lock = null; });
    } catch { /* denied or unsupported: the screen just times out as usual */ }
    finally { lockPending = false; }
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
      wakeOff();
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
  let tqSeq = 0, tqInt = null, confirmId = null, confirmT = null;
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
    strip.innerHTML = tqs.map(t => '<button type="button" class="em-btn em-active" data-tool="tq" aria-label="Open tourniquet timer: ' +
      esc(t.limb) + '"><span>TQ ' + esc(t.limb.toLowerCase()) + '</span><b data-t="' + t.start + '">' + hms(Date.now() - t.start) + '</b></button>').join('');
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
    confirmId = id; clearTimeout(confirmT);
    if (id) confirmT = setTimeout(() => { confirmId = null; paintTq(); }, 6000);
  }

  tools.tq = {
    label: 'Tourniquet timers',
    render(el, opts) {
      const pick = LIMBS.includes(opts.limb) ? opts.limb : LIMBS[0];
      el.innerHTML = '<div class="row" style="margin-top:0"><select id="tqLimb" aria-label="Limb">' +
        LIMBS.map(l => '<option' + (l === pick ? ' selected' : '') + '>' + l + '</option>').join('') + '</select>' +
        '<button type="button" class="btn" id="tqStart">Start timer</button></div><div id="tqList"></div>' +
        '<p class="hint" style="margin-top:8px">Timers keep running if you close the app. Tell responders the time each tourniquet went on, and write it on the tourniquet or casualty if you can.</p>';
      el.querySelector('#tqStart').addEventListener('click', () => {
        const limb = el.querySelector('#tqLimb').value;
        tqs.push({ id: Date.now().toString(36) + (tqSeq++ % 36).toString(36), limb, start: Date.now() });
        saveTq(); paintTq(); sync();
        if (typeof FK.log === 'function') FK.log('Tourniquet applied: ' + limb);
      });
      el.querySelector('#tqList').addEventListener('click', e => {
        const b = e.target.closest('button[data-act]'); if (!b) return;
        const id = b.closest('.timer').dataset.id;
        if (b.dataset.act === 'clear') { setConfirm(id); paintTq(); return; }
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
  let cpr = null;   // live state of the open coach, or null
  let ac = null;
  function beep(high) {
    try {
      const AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) return;
      ac = ac || new AC();
      if (ac.state === 'suspended' && ac.resume) ac.resume().catch(() => {});
      const o = ac.createOscillator(), g = ac.createGain();
      o.frequency.value = high ? 1320 : 880;
      g.gain.setValueAtTime(0.0001, ac.currentTime);
      g.gain.exponentialRampToValueAtTime(0.6, ac.currentTime + 0.005);
      g.gain.exponentialRampToValueAtTime(0.0001, ac.currentTime + 0.08);
      o.connect(g).connect(ac.destination); o.start(); o.stop(ac.currentTime + 0.09);
    } catch { /* audio is optional */ }
  }
  const buzz = p => { try { if (navigator.vibrate) navigator.vibrate(p); } catch { /* optional */ } };
  const setText = (el, t) => { if (el.textContent !== t) el.textContent = t; };
  const plural = (n, w) => n + ' ' + w + (n === 1 ? '' : 's');

  function cprStop() {
    if (!cpr) return;
    clearInterval(cpr.iv);
    cpr.running = false;
  }

  tools.cpr = {
    label: 'CPR coach',
    render(el, opts) {
      const fromProto = /^cpr-(adult|child|infant)$/.exec(opts.protocol || '');
      const mode = CPR_MODES.some(m => m[0] === opts.mode) ? opts.mode : fromProto ? fromProto[1] : 'adult';
      cpr = { mode, compressionOnly: false, running: false, t0: 0, iv: null, lastBeat: 0, lastPhase: 'compress', swapAck: 0, swapsSeen: 0, from: opts.protocol || null };
      el.innerHTML =
        '<div class="seg cpr-modes" role="group" aria-label="Who is it for">' +
        CPR_MODES.map(([id, label]) => '<button type="button" data-mode="' + id + '" aria-pressed="' + (id === mode) + '">' + label + '</button>').join('') + '</div>' +
        '<button type="button" class="cpr-opt" id="cprOnly" aria-pressed="false">Compression only (no breaths)</button>' +
        '<div class="cpr-face" id="cprFace" aria-hidden="true"><div class="cpr-count" id="cprCount">0</div><div class="cpr-cycle" id="cprCycle"></div></div>' +
        '<p class="cpr-swap" id="cprSwap" hidden><span>Swap rescuers now</span><button type="button" class="btn" id="cprSwapped">Swapped</button></p>' +
        '<button type="button" class="btn pp-wide" id="cprBtn">Start</button>' +
        '<button type="button" class="btn ghost pp-wide" id="cprSteps" hidden>Open steps</button>' +
        '<p class="hint">Clicks at ' + CPR_RATE + ' per minute. Turn your volume up. If the casualty is not breathing, call 911 if you have signal. If not, send someone for help.</p>' +
        '<div class="sr-live" id="cprLive" role="status" aria-live="polite"></div>';
      const q = s => el.querySelector(s);
      const paint = () => {
        const r = cprRatio(cpr.mode), cfg = { ...r, compressionOnly: cpr.compressionOnly };
        const s = cpr.running ? cprState(performance.now() - cpr.t0, cfg) : null;
        const breathing = s && s.phase === 'breaths';
        setText(q('#cprCount'), !s ? '0' : breathing ? plural(r.breaths, 'breath') : String(s.count));
        q('#cprCount').classList.toggle('breaths', !!breathing);
        setText(q('#cprCycle'), s ? 'Cycle ' + s.cycle : '');
        setText(q('#cprBtn'), cpr.running ? 'Stop' : 'Start');
        el.querySelectorAll('[data-mode]').forEach(b => { b.disabled = cpr.running; b.setAttribute('aria-pressed', String(b.dataset.mode === cpr.mode)); });
        q('#cprOnly').disabled = cpr.running;
        q('#cprOnly').setAttribute('aria-pressed', String(cpr.compressionOnly));
        q('#cprSwap').hidden = !(s && s.swaps > cpr.swapAck);
        q('#cprSteps').hidden = !(FK.protocol && FK.protocol.get && FK.protocol.get('cpr-' + cpr.mode));
        return s;
      };
      const tick = () => {
        const s = paint(); if (!s) return;
        const live = q('#cprLive');
        if (s.beats > cpr.lastBeat) { cpr.lastBeat = s.beats; if (s.phase === 'compress') { beep(s.count === 1); buzz(25); } }
        if (s.phase !== cpr.lastPhase) { cpr.lastPhase = s.phase; live.textContent = s.phase === 'breaths' ? plural(cprRatio(cpr.mode).breaths, 'breath') : 'Compressions'; buzz([120, 80, 120]); }
        if (s.swaps > cpr.swapsSeen) { cpr.swapsSeen = s.swaps; live.textContent = 'Swap rescuers now'; beep(true); buzz([300, 150, 300]); }
      };
      q('#cprBtn').addEventListener('click', () => {
        if (cpr.running) { cprStop(); paint(); return; }
        Object.assign(cpr, { running: true, t0: performance.now(), lastBeat: 0, lastPhase: 'compress', swapAck: 0, swapsSeen: 0 });
        tick();
        cpr.iv = setInterval(tick, 50);
      });
      el.addEventListener('click', e => {
        const m = e.target.closest('[data-mode]');
        if (m && !cpr.running) { cpr.mode = m.dataset.mode; paint(); }
      });
      q('#cprOnly').addEventListener('click', () => { if (!cpr.running) { cpr.compressionOnly = !cpr.compressionOnly; paint(); } });
      q('#cprSwapped').addEventListener('click', () => { cpr.swapAck = cpr.swapsSeen; paint(); });
      q('#cprSteps').addEventListener('click', () => {
        const id = 'cpr-' + cpr.mode;
        if (cpr.from === id) close();   // came here from these steps: Back returns to the same step
        else FK.protocol.open(id);
      });
      paint();
    },
    stop() { cprStop(); cpr = null; }
  };
  FK.tools.cpr = { state: cprState };

  /* ---------- Start ---------- */
  FK.on('route', r => { onRoute(r); sync(); });
  queueMicrotask(() => { onRoute(FK.route.current()); paintStrip(); sync(); });   // after every module has loaded and registered its tools
})();
