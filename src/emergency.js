/* ---------- Emergency home: life-threat buttons, resume, pinned, recent, categories (all driven by FK_DATA) ---------- */
(() => {
  const FK = window.FK;
  const esc = FK.esc;
  const $ = id => document.getElementById(id);
  const RESERVED = ['tool', 'report'];   // addresses owned by other features, not protocols
  const KEY = /^[ptsracu]:[\w-]{1,60}$/;   // p:<protocolId>, t:<toolName>, r:<reportName>, s:<survivalTopicId>, a:<appScreen>, c:<checklistId>, u:<survivalTool>
  const RECENT_MAX = 20;   // stored
  const SHOWN = 5;         // listed on a home
  const SECTION_KINDS = { emergency: 'ptsracu', survival: 'scu' };   // which key kinds each home lists
  const forSection = (list, section) => Object.hasOwn(SECTION_KINDS, section) ? list.filter(k => SECTION_KINDS[section].includes(k[0])) : [];
  FK.keyPattern = KEY;
  const PIN_FULL = 'Couldn’t change the pin: phone storage for Field Kit is full. Back up, then delete old tracks or saved maps.';
  const LIFE = [['bleeding', 'Bleeding'], ['choking', 'Choking']];
  const CHOOSER = [['cpr-adult', 'Adult'], ['cpr-child', 'Child'], ['cpr-infant', 'Infant']];
  const CATS = [['life', 'More life threats'], ['injury', 'Injuries'], ['environment', 'Heat, cold, environment'],
    ['bites', 'Bites, stings, poison'], ['illness', 'Sudden illness'], ['advanced', 'Advanced procedures']];

  /* ---------- Pins and recent: a list of keys in storage. Anything malformed is ignored, never rendered. ---------- */
  const keys = name => {
    const v = FK.store.get(name, []);
    return Array.isArray(v) ? [...new Set(v.filter(k => typeof k === 'string' && KEY.test(k)))] : [];
  };
  FK.pins = {
    all: () => keys('pins'),
    forSection: section => forSection(keys('pins'), section),
    has: key => keys('pins').includes(key),
    toggle(key) {
      if (typeof key !== 'string' || !KEY.test(key)) return;
      const cur = keys('pins');
      // A failed pin says so every time (the storage toast alone repeats only once a minute).
      if (!FK.store.set('pins', cur.includes(key) ? cur.filter(k => k !== key) : [...cur, key])) setTimeout(() => FK.toast(PIN_FULL), 0);
      FK.emit('pins');
    }
  };
  FK.recent = {
    all: () => keys('recent').slice(0, RECENT_MAX),
    /* ok, if given, drops keys before the list is cut to SHOWN, so keys that no longer open anything do not shorten it. */
    forSection: (section, ok) => forSection(keys('recent'), section).filter(k => !ok || ok(k)).slice(0, SHOWN),
    add(key) {
      if (typeof key !== 'string' || !KEY.test(key)) return;
      const cur = keys('recent');
      if (cur[0] === key) return;
      FK.store.set('recent', [key, ...cur.filter(k => k !== key)].slice(0, RECENT_MAX));
      FK.emit('recent');
    },
    clear() { FK.store.set('recent', []); FK.emit('recent'); }
  };

  /* ---------- Data ---------- */
  const protocols = () => FK.protocols();   // well-formed protocols only (app.js)
  const get = id => protocols().find(p => p.id === id);
  const fixed = new Set([...LIFE.map(x => x[0]), ...CHOOSER.map(x => x[0])]);

  /* ---------- Rendering ---------- */
  const openCats = new Set();
  let chooserOpen = false;
  const draft = p => p.draft === true ? '<small class="em-draft">Draft</small>' : '';
  const protoBtn = p => '<button type="button" class="em-btn" data-open="' + esc(p.id) + '"><span>' + esc(p.title) + '</span>' + draft(p) + '</button>';
  const toolLabel = name => FK.tools && FK.tools.label ? FK.tools.label(name) : null;
  const toolBtn = name => '<button type="button" class="em-btn" data-tool="' + esc(name) + '"><span>' + esc(toolLabel(name)) + '</span></button>';
  /* Pinned and recent keys: p:<protocol>, t:<tool>, r:<report>, s:<survival topic>, c:<checklist>, u:<survival tool>, a:<app screen>. Anything that no longer exists is skipped. */
  const keyBtns = list => list.map(k => {
    if (k[0] === 'p') { const p = get(k.slice(2)); return p ? protoBtn(p) : ''; }
    if (k[0] === 't' || k[0] === 'r') {   // a tool or a report; the key must match where the name lives
      const name = k.slice(2);
      return toolLabel(name) && FK.tools.segment(name) === (k[0] === 'r' ? 'report' : 'tool') ? toolBtn(name) : '';
    }
    if ('sacu'.includes(k[0])) {   // a survival topic, checklist or tool, or an app screen: search knows its label and how to open it
      const d = FK.search && FK.search.describe(k);
      return d ? '<button type="button" class="em-btn" data-key="' + esc(k) + '"><span>' + esc(d.title) + '</span></button>' : '';
    }
    return '';
  }).filter(Boolean);
  /* Redraw a block only when its markup changed, so a button that opened a screen is still there to take focus back. */
  const drawn = new WeakMap();   // element -> markup last written into it
  const setHTML = (el, html) => { if (drawn.get(el) !== html) { el.innerHTML = html; drawn.set(el, html); } };
  const group = (id, title, btns, extra) => setHTML($(id), btns.length ? '<div class="em-hrow"><h3 class="em-h">' + title + '</h3>' + (extra || '') + '</div><div class="em-grid">' + btns.join('') + '</div>' : '');
  const CLEAR_RECENT = '<button type="button" class="em-clear" data-act="clear-recent" aria-label="Clear recent list">Clear</button>';

  function renderResume() {
    const a = FK.protocol && FK.protocol.active();
    const p = a && get(a.id);
    if (!p) { setHTML($('emResume'), ''); return; }
    const i = p.steps.findIndex(s => s.id === a.step);
    setHTML($('emResume'), '<button type="button" class="em-resume" data-resume="' + esc(a.id) + '" data-step="' + esc(a.step) +
      '">Resume: ' + esc(p.title) + ', ' + (i + 1) + '/' + p.steps.length + '</button>');
  }

  function lifeHTML() {
    const fixedBtn = id => {
      const p = get(id), label = LIFE.find(x => x[0] === id)[1];
      return p ? '<button type="button" data-open="' + esc(id) + '"><span>' + label + '</span>' + draft(p) + '</button>' : '';
    };
    const breathing = CHOOSER.some(([id]) => get(id)) ? '<button type="button" data-act="breathing" aria-expanded="' + chooserOpen +
      '" aria-controls="emChooser"><span>Not breathing</span></button>' : '';
    return fixedBtn('bleeding') + breathing + fixedBtn('choking');
  }
  function renderLife() {
    const opts = CHOOSER.filter(([id]) => get(id));
    setHTML($('emLife'), lifeHTML());
    $('emChooser').hidden = !(chooserOpen && opts.length);
    setHTML($('emChooser'), opts.map(([id, label]) => '<button type="button" class="em-btn" data-open="' + esc(id) + '"><span>' + label + '</span>' + draft(get(id)) + '</button>').join(''));
  }
  /* Open or close the "Not breathing" chooser in place: nothing is redrawn, so the button keeps focus. */
  function toggleChooser(btn) {
    chooserOpen = !chooserOpen;
    btn.setAttribute('aria-expanded', String(chooserOpen));
    $('emChooser').hidden = !(chooserOpen && CHOOSER.some(([id]) => get(id)));
    drawn.set($('emLife'), lifeHTML());   // the markup now on screen
  }

  function renderCats() {
    document.querySelectorAll('#emCatsDyn details').forEach(d => { if (d.open) openCats.add(d.dataset.cat); else openCats.delete(d.dataset.cat); });   // keep what the user opened
    setHTML($('emCatsDyn'), CATS.map(([cat, label]) => {
      const ps = protocols().filter(p => p.category === cat && !(cat === 'life' && fixed.has(p.id)));
      if (!ps.length) return '';
      return '<details class="ref" data-cat="' + cat + '"' + (openCats.has(cat) ? ' open' : '') + '><summary data-cat="' + cat + '">' + label +
        '</summary><div class="body em-grid">' + ps.map(protoBtn).join('') + '</div></details>';
    }).join(''));
  }

  function render() {
    renderResume();
    renderLife();
    group('emPinned', '★ Pinned', keyBtns(FK.pins.forSection('emergency')));
    group('emRecent', 'Recent', keyBtns(FK.recent.forSection('emergency', k => keyBtns([k]).length > 0)), CLEAR_RECENT);
    renderCats();
  }

  /* ---------- Events ---------- */
  $('emHome').addEventListener('click', e => {
    const open = e.target.closest('[data-open]');
    if (open) { FK.protocol.open(open.dataset.open); return; }
    const key = e.target.closest('[data-key]');
    if (key) { FK.search.go(key.dataset.key); return; }
    const tool = e.target.closest('[data-tool]');
    if (tool) { FK.tools.start(tool.dataset.tool); return; }
    const res = e.target.closest('[data-resume]');
    if (res) { FK.protocol.open(res.dataset.resume, res.dataset.step); return; }
    const breathing = e.target.closest('[data-act="breathing"]');
    if (breathing) { toggleChooser(breathing); return; }
    if (e.target.closest('[data-act="clear-recent"]')) {   // the button goes with the list, so hand focus to the first life-threat button
      FK.recent.clear();
      const first = $('emLife').querySelector('button');
      if (first) first.focus();
    }
  });
  FK.on('pins', render);
  FK.on('recent', render);
  FK.on('route', onRoute);
  function onRoute(r) {
    if (r.tab !== 'emergency') return;
    const id = r.parts[0];
    if (!id) { chooserOpen = false; render(); return; }
    if (!RESERVED.includes(id) && get(id)) FK.recent.add('p:' + id);
  }
  // Runs after the whole script has loaded, so FK.protocol (defined by the player) exists.
  queueMicrotask(() => { render(); onRoute(FK.route.current()); });
})();
