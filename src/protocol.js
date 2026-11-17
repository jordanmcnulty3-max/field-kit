/* ---------- Protocol player: one step per screen. Section-agnostic: Emergency today, Survival later ---------- */
(() => {
  const FK = window.FK;
  const esc = FK.esc;
  const root = document.getElementById('player');
  const SECTION = 'emergency';
  const RESERVED = ['tool', 'report'];   // addresses owned by other features; the player stays out of them
  const LISTS = [['donts', 'Do not'], ['evacuate', 'Evacuate when']];   // [protocol key, button label and list heading]
  const ACK_TEXT = 'These procedures can kill if done wrong or when they are not needed. They are a reference for people who have trained on them hands-on. Reading this is not training.';
  const OPENING = [['indications', 'When to do this'], ['contraindications', 'When not to'],
    ['equipment', 'Equipment'], ['complications', 'What can go wrong']];
  const enc = encodeURIComponent;

  /* ---------- Data ---------- */
  const get = id => FK.protocols().find(p => p.id === id);   // well-formed protocols only (app.js)
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
  /* The acknowledgement is kept in memory as well as in storage, so it still works when phone storage is full. */
  let acked = false;
  const needsAck = p => p.tier === 'advanced' && !acked && FK.store.get('advAck', false) !== true;
  const base = p => '/' + SECTION + '/' + enc(p.id);
  const stepPath = (p, i) => (i === 0 && !hasIntro(p)) ? base(p) : base(p) + '/' + enc(p.steps[i].id);

  /* ---------- Saved progress: { id, step, started, timer?, logged? } for the one protocol run in progress.
     timer = { step, label, end, done } (a started step timer, so it survives a reload);
     logged = ids of steps already written to the patient log in this run. ---------- */
  const rawActive = () => { const a = FK.store.get('proto.active', null); return a && typeof a === 'object' && !Array.isArray(a) ? a : null; };
  function active() {
    const a = rawActive();
    if (!a) return null;
    const p = typeof a.id === 'string' ? get(a.id) : null;
    if (!p || stepIndex(p, a.step) < 0) { FK.store.set('proto.active', null); return null; }   // stale: protocol changed since
    return { id: a.id, step: a.step, started: a.started };
  }
  /* Rewrite the run record, keeping what belongs to the same run. */
  function writeActive(p, stepId) {
    const raw = rawActive(), same = !!raw && raw.id === p.id;
    const rec = { id: p.id, step: stepId, started: same && Number.isFinite(raw.started) ? raw.started : Date.now() };
    const logged = run.id === p.id ? [...run.logged] : [];
    if (logged.length) rec.logged = logged;
    if (timer && timer.id === p.id) rec.timer = { step: timer.step, label: timer.label, end: timer.end, done: timer.done };
    FK.store.set('proto.active', rec);
  }
  function saveProgress(p, i) {
    if (run.id !== p.id) run = { id: p.id, logged: new Set() };   // a different protocol: a new run
    writeActive(p, p.steps[i].id);
  }
  function syncActive() {   // after the timer or the logged steps changed
    const raw = rawActive();
    const p = raw && typeof raw.id === 'string' ? get(raw.id) : null;
    if (p && stepIndex(p, raw.step) >= 0) writeActive(p, raw.step);
  }
  const clearProgress = () => { run = { id: null, logged: new Set() }; if (FK.store.get('proto.active', null) !== null) FK.store.set('proto.active', null); };
  let run = { id: null, logged: new Set() };   // the run in progress: which steps it has logged

  /* One patient-log entry per step per run, with a short toast so the user knows it was written. */
  function logStep(p, i) {
    const s = p.steps[i];
    if (typeof s.log !== 'string' || !s.log.trim() || typeof FK.log !== 'function') return;
    if (run.id !== p.id) run = { id: p.id, logged: new Set() };
    if (run.logged.has(s.id)) return;
    if (FK.log(s.log) === false) return;   // the log said why (storage full, log full)
    run.logged.add(s.id);
    syncActive();
    FK.toast('Logged: ' + s.log);
  }

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

  /* ---------- Step timer: one at a time, owned by the protocol run, not the screen. It keeps running while the player
     is hidden for a tool, report or search, across steps and over a reload; only Done, End protocol, leaving by the
     header back button or opening a different protocol stop it. ---------- */
  let timer = null;   // { id, title, step, label, end, done, iv }
  const mmss = ms => { const s = Math.max(0, Math.ceil(ms / 1000)); return Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0'); };
  const showingRun = () => isOpen && cur && timer && cur.p.id === timer.id;
  function stopTimer() {
    if (!timer) return;
    clearInterval(timer.iv); timer = null;
    syncActive(); paintTimer(); FK.emit('activity');
  }
  function paintTimer() {
    const bar = root.querySelector('.pp-timerbar');
    if (!bar) return;
    const on = !!timer && !!cur && cur.p.id === timer.id;
    bar.hidden = !on;
    if (!on) return;
    bar.querySelector('.pp-timerlabel').textContent = timer.label;
    bar.querySelector('.pp-timerval').textContent = timer.done ? 'Done' : mmss(timer.end - Date.now());
  }
  function finishTimer() {
    timer.done = true; clearInterval(timer.iv);
    const live = showingRun() ? root.querySelector('#ppLive') : null;
    if (live) live.textContent = timer.label + ' finished';
    else FK.toast(timer.title + ': ' + timer.label + ' finished');   // the toast is a live region, on every screen
    try { if (navigator.vibrate) navigator.vibrate([300, 150, 300]); } catch { /* optional */ }
    syncActive(); FK.emit('activity');
  }
  function runTimer(t) {
    timer = t;
    if (timer.end - Date.now() <= 0 && !timer.done) { finishTimer(); paintTimer(); return; }
    if (!timer.done) {
      timer.iv = setInterval(() => {
        if (timer.end - Date.now() <= 0 && !timer.done) finishTimer();
        paintTimer();
      }, 250);
    }
    paintTimer(); FK.emit('activity');
  }
  function startTimer(p, i) {
    const spec = p.steps[i].timer;
    if (timer) { clearInterval(timer.iv); timer = null; }
    runTimer({ id: p.id, title: p.title, step: p.steps[i].id, label: spec.label || 'Timer', end: Date.now() + spec.seconds * 1000, done: false });
    syncActive();
  }
  /* A timer saved with the run comes back after a reload. */
  function restoreTimer() {
    const a = active(), raw = rawActive();
    const t = a && raw.timer;
    if (!t || typeof t !== 'object' || !Number.isFinite(t.end) || typeof t.label !== 'string' || typeof t.step !== 'string') return;
    const p = get(a.id);
    if (stepIndex(p, t.step) < 0) return;
    runTimer({ id: p.id, title: p.title, step: t.step, label: t.label, end: t.end, done: t.done === true });
  }

  /* ---------- Rendering ---------- */
  let cur = null;                // { p, mode: 'ack' | 'intro' | 'step' | 'all', i, open: { donts, evacuate } }
  const from = {};               // 'protocolId:stepIndex' -> where the user came from, so Back follows branches

  const paras = t => String(t).split(/\n\s*\n/).map(x => x.trim()).filter(Boolean).map(x => '<p>' + esc(x) + '</p>').join('');
  const list = (items, tag) => '<' + tag + '>' + items.map(x => '<li>' + esc(x) + '</li>').join('') + '</' + tag + '>';
  const listItems = (p, k) => (Array.isArray(p[k]) ? p[k].filter(x => typeof x === 'string' && x.trim()) : []);
  const hasList = (p, k) => listItems(p, k).length > 0;
  const blocks = p => openingBlocks(p).map(([k, h]) => '<section class="pp-sec"><h3>' + h + '</h3>' + list(p[k], 'ul') + '</section>').join('');

  function head(p) {
    const pins = FK.pins;
    const pinned = !!(pins && pins.has && pins.has('p:' + p.id));
    return '<header class="pp-head"><div class="pp-row">' +
      '<button class="pp-btn" data-act="home" aria-label="Close protocol and go back to Emergency">‹</button>' +
      '<h2 class="pp-title" id="ppTitle" tabindex="-1">' + esc(p.title) + '</h2>' +
      (pins ? '<button class="pp-btn" data-act="pin" aria-pressed="' + pinned + '" aria-label="Pin this protocol">' + (pinned ? '★' : '☆') + '</button>' : '') +
      '<button class="pp-btn" data-act="search" aria-label="Search">⌕</button>' +
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
    const toolLabel = tools && typeof FK.tools.label === 'function' ? FK.tools.label(s.tool) : null;   // the registry's own name for it
    return '<p class="pp-action" id="ppAction" tabindex="-1">' + esc(s.text) + '</p>' +
      (s.warn ? '<p class="pp-warn"><span aria-hidden="true">⚠ </span>' + esc(s.warn) + '</p>' : '') +
      (s.figSvg ? '<figure class="pp-fig">' + s.figSvg + '</figure>' : '') +
      listRow(p) + '<div id="ppListPanels">' + listPanels(p) + '</div>' +
      (s.detail ? '<div class="pp-detail">' + paras(s.detail) + '</div>' : '') +
      (tools ? '<button class="btn pp-wide" data-act="tool">' + esc(toolLabel || 'Open tool') + '</button>' : '') +
      (s.timer && Number.isFinite(s.timer.seconds) && s.timer.seconds > 0
        ? '<button class="btn ghost pp-wide" data-act="timer">Start timer: ' + esc(s.timer.label || 'Timer') + ' (' + mmss(s.timer.seconds * 1000) + ')</button>' : '') +
      (isAsk(s) && s.ask.q && s.ask.q !== s.text ? '<p class="pp-q">' + esc(s.ask.q) + '</p>' : '');
  }

  /* Do not / Evacuate when: one tap from every step. The buttons sit in the step body after the figure; an open list shows directly below them. */
  const marker = open => open ? '▴' : '▾';
  function listRow(p) {
    const ks = LISTS.filter(([k]) => hasList(p, k));
    if (!ks.length) return '';
    return '<div class="pp-lists" id="ppLists">' + ks.map(([k, label]) =>
      '<button type="button" class="pp-listbtn" data-act="list" data-list="' + k + '" aria-expanded="' + !!cur.open[k] + '" aria-controls="ppList-' + k + '">' + esc(label) + ' (' + listItems(p, k).length + ')' +
      ' <span aria-hidden="true">' + marker(cur.open[k]) + '</span></button>').join('') + '</div>';
  }
  function listPanels(p) {
    return LISTS.filter(([k]) => hasList(p, k) && cur.open[k]).map(([k, label]) =>
      '<section class="pp-list" id="ppList-' + k + '" data-list="' + k + '" tabindex="-1" aria-label="' + esc(label) + '"><h3>' + esc(label) + '</h3>' + list(listItems(p, k), 'ul') +
      '<button type="button" class="pp-listbtn pp-wide" data-act="list" data-list="' + k + '" aria-label="Close the ' + esc(label) + ' list">Close ▴</button></section>').join('');
  }
  function toggleList(k) {
    const body = root.querySelector('#ppBody'), box = root.querySelector('#ppListPanels');
    const was = body ? body.scrollTop : 0;
    cur.open[k] = !cur.open[k];
    const opening = cur.open[k];
    root.querySelectorAll('#ppLists [data-list="' + k + '"]').forEach(b => {
      b.setAttribute('aria-expanded', String(opening));
      b.querySelector('span').textContent = marker(opening);
    });
    if (!box) return;
    box.innerHTML = listPanels(cur.p);
    const panel = box.querySelector('.pp-list[data-list="' + k + '"]');
    if (opening && panel) { panel.scrollIntoView({ block: 'nearest' }); panel.focus({ preventScroll: true }); }
    else { body.scrollTop = was; const b = root.querySelector('#ppLists [data-list="' + k + '"]'); if (b) b.focus({ preventScroll: true }); }
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
        (s.warn ? '<p class="pp-warn"><span aria-hidden="true">⚠ </span>' + esc(s.warn) + '</p>' : '') +
        (s.detail ? '<div class="pp-detail">' + paras(s.detail) + '</div>' : '') + ask + '</div>';
    }).join('');
    if (Array.isArray(p.donts) && p.donts.length) h += '<section class="pp-sec"><h3>Do not</h3>' + list(p.donts, 'ul') + '</section>';
    if (Array.isArray(p.evacuate) && p.evacuate.length) h += '<section class="pp-sec"><h3>Evacuate when</h3>' + list(p.evacuate, 'ul') + '</section>';
    if (hasList(p, 'notes')) h += '<section class="pp-sec pp-notes"><h3>Notes</h3>' + listItems(p, 'notes').map(x => '<p>' + esc(x) + '</p>').join('') + '</section>';
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
  }
  function focusTop() {
    const a = root.querySelector('#ppAction') || root.querySelector('#ppTitle');
    if (a) a.focus({ preventScroll: true });
  }

  /* ---------- History. The router numbers every entry (FK.route.index()). Each player entry carries, in
     history.state.pp, { from, root, prev, at }: from = the entry the protocol was opened from (null after a deep link,
     when nothing in the app is before it), root = the run's first player entry, at/prev = the screen on this/the previous
     entry. Leaving is a jump by the difference of two numbers, so a duplicated entry, a same-address search result or a
     reload cannot throw the count off. ---------- */
  let curState = null, curIdx = 0, pendingStamp = null, pendingDeep = false, pendingLeave = false, leaving = false, leaveT = null, booted = false;
  const LEAVE_FALLBACK_MS = 500;
  const okStamp = (st, idx) => !!st && typeof st === 'object' && Number.isInteger(st.root) && st.root <= idx &&
    (st.from === null || (Number.isInteger(st.from) && st.from < st.root)) && 'at' in st;
  function writeStamp(st) { history.replaceState({ ...(history.state && typeof history.state === 'object' ? history.state : {}), pp: st }, '', location.href); }
  function stamp(key) {
    const idx = FK.route.index();
    const own = history.state && history.state.pp;
    let st;
    if (pendingStamp) { st = { ...pendingStamp, at: key }; pendingStamp = null; }                       // a replace inside the player keeps the entry's place in the run
    else if (okStamp(own, idx)) st = own.at === key ? own : { ...own, at: key };                     // an entry of this run, reached by Back/Forward or after a reload
    else if (isOpen && curState) st = { from: curState.from, root: curState.root, prev: idx > curIdx ? curState.at : curState.prev, at: key };
    else if (!booted || pendingDeep) st = { from: null, root: idx, prev: null, at: key };             // deep link: nothing in the app before it
    else st = { from: idx - 1, root: idx, prev: null, at: key };                                      // opened from the entry before this one
    pendingDeep = false;
    if (st !== own) writeStamp(st);
    curState = st; curIdx = idx;
  }
  /* Replace this entry with Emergency home, and drop the player's mark from it. */
  function goHome() {
    if (history.state && typeof history.state === 'object' && 'pp' in history.state) {
      const { pp, ...rest } = history.state;
      history.replaceState(rest, '', location.href);
    }
    FK.route.go('/' + SECTION, { replace: true });
  }
  /* Leave the player without ever landing back inside it. */
  function leave() {
    if (leaving) return;   // history.go is asynchronous: a second tap must not unwind twice
    leaving = true;
    stopTimer();
    const st = curState, idx = FK.route.index();
    clearTimeout(leaveT);
    // If history did not move (an out-of-range jump does nothing in an installed app), go home anyway.
    leaveT = setTimeout(() => { if (leaving && isOpen) { leaving = false; pendingLeave = false; goHome(); } }, LEAVE_FALLBACK_MS);
    if (st && st.from !== null && st.from < idx) history.go(st.from - idx);
    else if (st && st.from === null && st.root < idx) { pendingLeave = true; history.go(st.root - idx); }   // deep link: unwind to its first entry, then replace it
    else goHome();
  }
  function goReplace(path) { pendingStamp = curState; FK.route.go(path, { replace: true }); pendingStamp = null; }

  /* ---------- Open / close ---------- */
  let opener = null;
  function show(p, sub) {
    if (timer && timer.id !== p.id) stopTimer();   // a different protocol ends the other run's timer
    const mode = needsAck(p) ? 'ack' : sub === 'all' ? 'all' : (sub || !hasIntro(p)) ? 'step' : 'intro';
    const was = isOpen;
    cur = { p, mode, i: mode === 'step' ? (sub ? stepIndex(p, sub) : 0) : -1, open: { donts: false, evacuate: false } };
    if (!was) opener = FK.opener(document.activeElement);
    stamp(mode === 'step' ? cur.i : mode);
    render();                      // render first: the player is only shown with something in it
    isOpen = true;
    root.hidden = false;
    document.body.classList.add('playing');
    focusTop();
    if (!was) FK.emit('activity');
    if (mode === 'step') saveProgress(p, cur.i);
    wakeOn();
  }
  function hide() {
    if (!isOpen) return;
    isOpen = false; cur = null; curState = null; leaving = false; clearTimeout(leaveT);
    wakeOff();
    root.hidden = true; root.innerHTML = '';
    document.body.classList.remove('playing');
    FK.emit('activity');
    FK.refocus(opener); opener = null;
  }
  /* Fix a bad address after the router has finished with it (it re-writes the address after its event). */
  function redirect(r, path) {
    const atBoot = !booted;   // a repaired deep link has nothing before it in the app
    queueMicrotask(() => {
      if (FK.route.current() !== r) return;
      if (path === '/' + SECTION) { goHome(); return; }
      pendingDeep = atBoot;
      FK.route.go(path, { replace: true });
      pendingDeep = false;
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
  /* Same screen, another history entry (Back over a duplicate, or off a search entry): take that entry's place in the run. */
  function onHistory() {
    if (!isOpen || !curState) return;
    if (pendingLeave) { pendingLeave = false; leaving = false; hide(); goHome(); return; }
    leaving = false;
    stamp(curState.at);
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
    logStep(p, i);
    from[p.id + ':' + to] = i;
    FK.route.go(stepPath(p, to));
  }

  root.addEventListener('click', e => {
    const b = e.target.closest('[data-act]');
    if (!b || !cur) return;
    const { p, i } = cur;
    switch (b.dataset.act) {
      case 'home': leave(); break;
      case 'search': FK.route.go('/search'); break;
      case 'start': from[p.id + ':0'] = 'intro'; FK.route.go(stepPath(p, 0)); break;
      case 'ack': acked = true; FK.store.set('advAck', true); onRoute(FK.route.current()); break;   // a full store shows its toast; the screen still opens
      case 'next': advance(p, i, successors(p, i)[0]); break;
      case 'yes': case 'no': { const to = stepIndex(p, p.steps[i].ask[b.dataset.act]); if (to >= 0) advance(p, i, to); break; }
      case 'back': {
        const prev = prevOf(p, i);
        if (prev === null) leave();
        else if (curState && curIdx > curState.root && curState.prev === prev) history.back();   // same as Android Back
        else FK.route.go(prev === 'intro' ? base(p) : stepPath(p, prev));
        break;
      }
      case 'done': logStep(p, i); clearProgress(); leave(); break;
      case 'end': clearProgress(); leave(); break;
      case 'toggleAll': {
        if (cur.mode === 'all') { const a = active(); const j = a && a.id === p.id ? stepIndex(p, a.step) : 0; goReplace(stepPath(p, j)); }
        else goReplace(base(p) + '/all');
        break;
      }
      case 'open': FK.route.go(stepPath(p, +b.dataset.i)); break;
      case 'list': if (LISTS.some(([k]) => k === b.dataset.list)) toggleList(b.dataset.list); break;
      case 'tool': if (FK.tools && FK.tools.start) FK.tools.start(p.steps[i].tool, { protocol: p.id }); break;
      case 'timer': startTimer(p, i); root.querySelector('#ppTimerBar').focus({ preventScroll: true }); break;
      case 'pin': if (FK.pins && FK.pins.toggle) { FK.pins.toggle('p:' + p.id); const on = !!(FK.pins.has && FK.pins.has('p:' + p.id)); b.setAttribute('aria-pressed', String(on)); b.textContent = on ? '★' : '☆'; } break;
    }
  });

  FK.protocol = {
    get,
    open: (id, stepId, opts) => { const p = get(id); if (p) FK.route.go(stepId && stepIndex(p, stepId) >= 0 ? base(p) + '/' + enc(stepId) : base(p), opts && opts.replace ? { replace: true } : undefined); },
    close: () => { if (isOpen) leave(); },
    active,
    /* The running (or finished) step timer of the run in progress, for the Emergency home strip. */
    timer: () => timer ? { id: timer.id, title: timer.title, step: timer.step, label: timer.label, end: timer.end, done: timer.done } : null
  };
  FK.on('route', onRoute);
  FK.on('history', onHistory);
  if (active()) {                // drop stale progress at startup, then pick the run back up
    const raw = rawActive();
    run = { id: raw.id, logged: new Set(Array.isArray(raw.logged) ? raw.logged.filter(x => typeof x === 'string') : []) };
    restoreTimer();
  }
  onRoute(FK.route.current());   // the router's first route ran before this file loaded
})();
