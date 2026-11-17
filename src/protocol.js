/* ---------- Protocol player: one step per screen. Section-agnostic: Emergency today, Survival later ---------- */
(() => {
  const FK = window.FK;
  const esc = FK.esc;
  const root = document.getElementById('player');
  const SECTION = 'emergency';
  const RESERVED = ['tool', 'report'];   // addresses owned by other features; the player stays out of them
  const TOOL_LABEL = { tq: 'Tourniquet timer', cpr: 'CPR metronome', rate: 'Rate counter', burn: 'Burn area' };
  const ACK_TEXT = 'These procedures can kill if done wrong or when they are not needed. They are a reference for people who have trained on them hands-on. Reading this is not training.';
  const OPENING = [['indications', 'When to do this'], ['contraindications', 'When not to'],
    ['equipment', 'Equipment'], ['complications', 'What can go wrong']];
  const enc = encodeURIComponent;

  /* ---------- Data ---------- */
  const all = () => (window.FK_DATA && Array.isArray(FK_DATA.protocols)) ? FK_DATA.protocols : [];
  const get = id => all().find(p => p.id === id);
  const stepIndex = (p, sid) => p.steps.findIndex(s => s.id === sid);
  const isAsk = s => !!s.ask && typeof s.ask === 'object';
  /* Same rule as the build validator: next array item, unless the step asks yes/no or ends. */
  const successors = (p, i) => {
    const s = p.steps[i];
    if (isAsk(s)) return [stepIndex(p, s.ask.yes), stepIndex(p, s.ask.no)].filter(j => j >= 0);
    return s.end === true || i + 1 >= p.steps.length ? [] : [i + 1];
  };
  const openingBlocks = p => OPENING.filter(([k]) => Array.isArray(p[k]) && p[k].length);
  const hasIntro = p => openingBlocks(p).length > 0;
  const needsAck = p => p.tier === 'advanced' && FK.store.get('advAck', false) !== true;
  const base = p => '/' + SECTION + '/' + enc(p.id);
  const stepPath = (p, i) => (i === 0 && !hasIntro(p)) ? base(p) : base(p) + '/' + enc(p.steps[i].id);

  /* ---------- Saved progress ---------- */
  function active() {
    const a = FK.store.get('proto.active', null);
    if (!a || typeof a !== 'object') return null;
    const p = typeof a.id === 'string' ? get(a.id) : null;
    if (!p || stepIndex(p, a.step) < 0) { FK.store.set('proto.active', null); return null; }   // stale: protocol changed since
    return { id: a.id, step: a.step, started: a.started };
  }
  function saveProgress(p, i) {
    const raw = FK.store.get('proto.active', null);
    const started = raw && raw.id === p.id && Number.isFinite(raw.started) ? raw.started : Date.now();
    FK.store.set('proto.active', { id: p.id, step: p.steps[i].id, started });
  }
  const clearProgress = () => { if (FK.store.get('proto.active', null) !== null) FK.store.set('proto.active', null); };

  /* ---------- Screen wake lock (own lock; silent where unsupported) ---------- */
  let lock = null, lockPending = false, isOpen = false;
  async function wakeOn() {
    if (lock || lockPending || !isOpen || document.hidden || !('wakeLock' in navigator) || !navigator.wakeLock) return;
    lockPending = true;
    try {
      const l = await navigator.wakeLock.request('screen');
      if (!isOpen) { l.release().catch(() => {}); return; }
      lock = l;
      l.addEventListener('release', () => { if (lock === l) lock = null; });
    } catch { /* denied or unsupported: the screen just times out as usual */ }
    finally { lockPending = false; }
  }
  function wakeOff() { if (lock) { const l = lock; lock = null; l.release().catch(() => {}); } }
  document.addEventListener('visibilitychange', () => { if (!document.hidden) wakeOn(); });

  /* ---------- Step timer (one at a time; keeps running across steps until the protocol closes) ---------- */
  let timer = null;   // { end, label, iv, done }
  const mmss = ms => { const s = Math.max(0, Math.ceil(ms / 1000)); return Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0'); };
  function stopTimer() { if (timer) clearInterval(timer.iv); timer = null; }
  function paintTimer() {
    const bar = root.querySelector('.pp-timerbar');
    if (!bar) return;
    bar.hidden = !timer;
    if (!timer) return;
    bar.querySelector('.pp-timerlabel').textContent = timer.label;
    bar.querySelector('.pp-timerval').textContent = timer.done ? 'Done' : mmss(timer.end - Date.now());
  }
  function startTimer(spec) {
    stopTimer();
    const label = spec.label || 'Timer';
    timer = { end: Date.now() + spec.seconds * 1000, label, done: false };
    timer.iv = setInterval(() => {
      if (timer.end - Date.now() <= 0 && !timer.done) {
        timer.done = true; clearInterval(timer.iv);
        const live = root.querySelector('#ppLive');
        if (live) live.textContent = label + ' finished';
        try { if (navigator.vibrate) navigator.vibrate([300, 150, 300]); } catch { /* optional */ }
      }
      paintTimer();
    }, 250);
    paintTimer();
  }

  /* ---------- Rendering ---------- */
  let cur = null;                // { p, mode: 'ack' | 'intro' | 'step' | 'all', i }
  const from = {};               // 'protocolId:stepIndex' -> where the user came from, so Back follows branches

  const paras = t => String(t).split(/\n\s*\n/).map(x => x.trim()).filter(Boolean).map(x => '<p>' + esc(x) + '</p>').join('');
  const list = (items, tag) => '<' + tag + '>' + items.map(x => '<li>' + esc(x) + '</li>').join('') + '</' + tag + '>';
  const blocks = p => openingBlocks(p).map(([k, h]) => '<section class="pp-sec"><h3>' + h + '</h3>' + list(p[k], 'ul') + '</section>').join('');

  function head(p) {
    const pins = FK.pins;
    const pinned = !!(pins && pins.has && pins.has(p.id));
    return '<header class="pp-head"><div class="pp-row">' +
      '<button class="pp-btn" data-act="home" aria-label="Close protocol and go back to Emergency">‹</button>' +
      '<h2 class="pp-title" id="ppTitle" tabindex="-1">' + esc(p.title) + '</h2>' +
      (pins ? '<button class="pp-btn" data-act="pin" aria-pressed="' + pinned + '" aria-label="Pin this protocol">' + (pinned ? '★' : '☆') + '</button>' : '') +
      '<button class="pp-btn" data-act="toggleAll" aria-pressed="' + (cur.mode === 'all') + '" aria-label="All steps on one page">☰</button>' +
      '</div>' + (p.draft === true ? '<p class="pp-draft">Draft, not source-checked</p>' : '') + '</header>';
  }

  function progress(p, i) {
    return '<div class="pp-prog"><p class="pp-count">' + (i + 1) + ' of ' + p.steps.length + '</p>' +
      '<div class="pp-bar" role="progressbar" aria-valuemin="1" aria-valuemax="' + p.steps.length + '" aria-valuenow="' + (i + 1) +
      '"><i style="width:' + Math.round((i + 1) / p.steps.length * 100) + '%"></i></div></div>';
  }

  function stepBody(p, i) {
    const s = p.steps[i];
    const tools = FK.tools && typeof FK.tools.start === 'function' && s.tool;
    return '<p class="pp-action" id="ppAction" tabindex="-1">' + esc(s.text) + '</p>' +
      (s.detail ? '<div class="pp-detail">' + paras(s.detail) + '</div>' : '') +
      (s.warn ? '<p class="pp-warn"><span aria-hidden="true">⚠ </span>' + esc(s.warn) + '</p>' : '') +
      (s.figSvg ? '<figure class="pp-fig">' + s.figSvg + '</figure>' : '') +
      (tools ? '<button class="btn pp-wide" data-act="tool">' + esc((Object.hasOwn(TOOL_LABEL, s.tool) ? TOOL_LABEL[s.tool] : 'Open tool')) + '</button>' : '') +
      (s.timer && Number.isFinite(s.timer.seconds) && s.timer.seconds > 0
        ? '<button class="btn ghost pp-wide" data-act="timer">Start timer: ' + esc(s.timer.label || 'Timer') + ' (' + mmss(s.timer.seconds * 1000) + ')</button>' : '') +
      (isAsk(s) && s.ask.q && s.ask.q !== s.text ? '<p class="pp-q">' + esc(s.ask.q) + '</p>' : '');
  }

  function stepFoot(p, i) {
    const s = p.steps[i];
    const back = '<button class="btn ghost back" data-act="back">Back</button>';
    if (isAsk(s)) return back + '<button class="btn" data-act="yes">Yes</button><button class="btn" data-act="no">No</button>';
    return back + (successors(p, i).length ? '<button class="btn" data-act="next">NEXT</button>' : '<button class="btn" data-act="done">Done</button>');
  }

  function allView(p) {
    const label = j => 'step ' + (j + 1);
    let h = blocks(p);
    h += p.steps.map((s, i) => {
      const ask = isAsk(s) ? '<p><b>' + esc(s.ask.q || s.text) + '</b> Yes: ' + label(stepIndex(p, s.ask.yes)) + '. No: ' + label(stepIndex(p, s.ask.no)) + '.</p>' : '';
      return '<div class="pp-step"><button class="pp-stepbtn" data-act="open" data-i="' + i + '"><span>' + (i + 1) + '</span><span>' + esc(s.text) + '</span></button>' +
        (s.detail ? '<div class="pp-detail">' + paras(s.detail) + '</div>' : '') +
        (s.warn ? '<p class="pp-warn"><span aria-hidden="true">⚠ </span>' + esc(s.warn) + '</p>' : '') + ask + '</div>';
    }).join('');
    if (Array.isArray(p.donts) && p.donts.length) h += '<section class="pp-sec"><h3>Do not</h3>' + list(p.donts, 'ul') + '</section>';
    if (Array.isArray(p.evacuate) && p.evacuate.length) h += '<section class="pp-sec"><h3>Evacuate when</h3>' + list(p.evacuate, 'ul') + '</section>';
    const src = (Array.isArray(p.sources) ? p.sources : []).map(x => esc([x.name, x.year, x.url].filter(Boolean).join(', ')));
    h += '<section class="pp-sec"><h3>Sources</h3>' + (src.length ? '<ul>' + src.map(x => '<li>' + x + '</li>').join('') + '</ul>' : '') +
      (p.reviewed ? '<p class="hint">Reviewed ' + esc(p.reviewed) + '</p>' : '') + '</section>';
    return h + '<button class="btn ghost pp-wide" data-act="end">End protocol</button>';
  }

  function render() {
    const { p, mode, i } = cur;
    let body, foot = '', prog = '';
    if (mode === 'ack') {
      body = '<p class="pp-action" id="ppAction" tabindex="-1">' + esc(ACK_TEXT) + '</p>';
      foot = '<button class="btn" data-act="ack">I understand, show procedures</button>';
    } else if (mode === 'intro') {
      body = blocks(p);
      foot = '<button class="btn" data-act="start">Start steps</button>';
    } else if (mode === 'all') {
      body = allView(p);
    } else {
      prog = progress(p, i);
      body = stepBody(p, i);
      foot = stepFoot(p, i);
    }
    root.innerHTML = head(p) + prog + '<div class="pp-body" id="ppBody">' + body + '</div>' +
      '<div class="pp-timerbar" id="ppTimerBar" tabindex="-1" hidden><span class="grow pp-timerlabel"></span><b class="pp-timerval"></b></div>' +
      (foot ? '<div class="pp-foot">' + foot + '</div>' : '') +
      '<div class="sr-live" id="ppLive" role="status" aria-live="polite"></div>';
    paintTimer();
    const body_ = root.querySelector('#ppBody');
    if (body_) body_.scrollTop = 0;
    const a = root.querySelector('#ppAction') || root.querySelector('#ppTitle');
    if (a) a.focus({ preventScroll: true });
  }

  /* ---------- History depth: each player entry carries { pp, out, prev, at } in history.state.
     pp = player entries pushed since the first one, out = first one was pushed from outside the player
     (so there is an entry before it to unwind to), at/prev = screen on this/the previous entry. ---------- */
  let curState = null, pendingState = null, pendingLeave = false, leaving = false, booted = false;
  function stamp(key) {
    let st = history.state;
    if (pendingState) { st = { ...pendingState, at: key }; pendingState = null; }
    else if (!st || typeof st.pp !== 'number') {
      st = isOpen && curState ? { pp: curState.pp + 1, out: curState.out, prev: curState.at, at: key }
        : { pp: 0, out: booted, prev: null, at: key };
    } else if (st.at !== key) st = { ...st, at: key };
    else { curState = st; return; }
    history.replaceState(st, '', location.href);
    curState = st;
  }
  /* Leave the player without ever landing back inside it. */
  function leave() {
    if (leaving) return;   // history.go is asynchronous: a second tap must not unwind twice
    leaving = true;
    const st = curState;
    if (!st) { FK.route.go('/' + SECTION, { replace: true }); return; }
    if (st.out) history.go(-(st.pp + 1));
    else if (st.pp > 0) { pendingLeave = true; history.go(-st.pp); }   // deep link: unwind to its first entry, then replace it
    else FK.route.go('/' + SECTION, { replace: true });
  }
  function goReplace(path) { pendingState = curState; FK.route.go(path, { replace: true }); pendingState = null; }

  /* ---------- Open / close ---------- */
  function show(p, sub) {
    if (cur && cur.p.id !== p.id) stopTimer();
    const mode = needsAck(p) ? 'ack' : sub === 'all' ? 'all' : (sub || !hasIntro(p)) ? 'step' : 'intro';
    cur = { p, mode, i: mode === 'step' ? (sub ? stepIndex(p, sub) : 0) : -1 };
    stamp(mode === 'step' ? cur.i : mode);
    isOpen = true;
    root.hidden = false;
    document.body.classList.add('playing');
    render();
    if (mode === 'step') saveProgress(p, cur.i);
    wakeOn();
  }
  function hide() {
    if (!isOpen) return;
    isOpen = false; cur = null; curState = null; leaving = false;
    stopTimer(); wakeOff();
    root.hidden = true; root.innerHTML = '';
    document.body.classList.remove('playing');
  }
  /* Fix a bad address after the router has finished with it (it re-writes the address after its event). */
  function redirect(r, path) {
    const atBoot = !booted;   // a repaired deep link has nothing before it in the app
    queueMicrotask(() => {
      if (FK.route.current() !== r) return;
      if (atBoot) pendingState = { pp: 0, out: false, prev: null, at: null };
      FK.route.go(path, { replace: true });
      pendingState = null;
    });
  }
  function onRoute(r) {
    leaving = false;
    try { route(r); } finally { booted = true; }
  }
  function route(r) {
    if (pendingLeave) {
      pendingLeave = false;
      if (r.tab === SECTION && r.parts[0]) { hide(); return redirect(r, '/' + SECTION); }
    }
    const id = r.tab === SECTION ? r.parts[0] : undefined;
    if (!id || RESERVED.includes(id)) return hide();
    const p = get(id);
    if (!p) { hide(); return redirect(r, '/' + SECTION); }
    const sub = r.parts[1];
    if (sub && sub !== 'all' && stepIndex(p, sub) < 0) { hide(); return redirect(r, base(p)); }
    show(p, sub);
  }

  /* ---------- Navigation ---------- */
  function prevOf(p, i) {
    const f = from[p.id + ':' + i];
    const preds = p.steps.map((_, j) => j).filter(j => successors(p, j).includes(i));
    if (f === 'intro' && i === 0) return 'intro';
    if (Number.isInteger(f) && preds.includes(f)) return f;
    if (i === 0) return hasIntro(p) ? 'intro' : null;
    return preds.includes(i - 1) ? i - 1 : preds.length ? preds[0] : i - 1;
  }
  function advance(p, i, to) {
    const log = p.steps[i].log;
    if (log && typeof FK.log === 'function') FK.log(log);
    from[p.id + ':' + to] = i;
    FK.route.go(stepPath(p, to));
  }
  
  root.addEventListener('click', e => {
    const b = e.target.closest('[data-act]');
    if (!b || !cur) return;
    const { p, i } = cur;
    switch (b.dataset.act) {
      case 'home': leave(); break;
      case 'start': from[p.id + ':0'] = 'intro'; FK.route.go(stepPath(p, 0)); break;
      case 'ack': FK.store.set('advAck', true); onRoute(FK.route.current()); break;
      case 'next': advance(p, i, successors(p, i)[0]); break;
      case 'yes': case 'no': { const to = stepIndex(p, p.steps[i].ask[b.dataset.act]); if (to >= 0) advance(p, i, to); break; }
      case 'back': {
        const prev = prevOf(p, i);
        if (prev === null) leave();
        else if (curState && curState.pp > 0 && curState.prev === prev) history.back();   // same as Android Back
        else FK.route.go(prev === 'intro' ? base(p) : stepPath(p, prev));
        break;
      }
      case 'done': {
        const log = p.steps[i].log;
        if (log && typeof FK.log === 'function') FK.log(log);
        clearProgress(); leave(); break;
      }
      case 'end': clearProgress(); leave(); break;
      case 'toggleAll': {
        if (cur.mode === 'all') { const a = active(); const j = a && a.id === p.id ? stepIndex(p, a.step) : 0; goReplace(stepPath(p, j)); }
        else goReplace(base(p) + '/all');
        break;
      }
      case 'open': FK.route.go(stepPath(p, +b.dataset.i)); break;
      case 'tool': if (FK.tools && FK.tools.start) FK.tools.start(p.steps[i].tool, { protocol: p.id }); break;
      case 'timer': startTimer(p.steps[i].timer); root.querySelector('#ppTimerBar').focus({ preventScroll: true }); break;
      case 'pin': if (FK.pins && FK.pins.toggle) { FK.pins.toggle(p.id); const on = !!(FK.pins.has && FK.pins.has(p.id)); b.setAttribute('aria-pressed', String(on)); b.textContent = on ? '★' : '☆'; } break;
    }
  });

  FK.protocol = {
    get,
    open: (id, stepId) => { const p = get(id); if (p) FK.route.go(stepId && stepIndex(p, stepId) >= 0 ? base(p) + '/' + enc(stepId) : base(p)); },
    close: () => { if (isOpen) leave(); },
    active
  };
  FK.on('route', onRoute);
  active();                      // drop stale progress at startup
  onRoute(FK.route.current());   // the router's first route ran before this file loaded
})();
