/* ---------- Emergency home: life-threat buttons, resume, pinned, recent, categories (all driven by FK_DATA) ---------- */
(() => {
  const FK = window.FK;
  const esc = FK.esc;
  const $ = id => document.getElementById(id);
  const RESERVED = ['tool', 'report'];   // addresses owned by other features, not protocols
  const KEY = /^[pts]:[\w-]{1,60}$/;     // p:<protocolId>, t:<toolName>, s:<survivalTopicId>
  const RECENT_MAX = 5;
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
    has: key => keys('pins').includes(key),
    toggle(key) {
      if (typeof key !== 'string' || !KEY.test(key)) return;
      const cur = keys('pins');
      FK.store.set('pins', cur.includes(key) ? cur.filter(k => k !== key) : [...cur, key]);
      FK.emit('pins');
    }
  };
  FK.recent = {
    all: () => keys('recent').slice(0, RECENT_MAX),
    add(key) {
      if (typeof key !== 'string' || !KEY.test(key)) return;
      const cur = keys('recent');
      if (cur[0] === key) return;
      FK.store.set('recent', [key, ...cur.filter(k => k !== key)].slice(0, RECENT_MAX));
      FK.emit('recent');
    }
  };

  /* ---------- Data ---------- */
  const protocols = () => (window.FK_DATA && Array.isArray(FK_DATA.protocols)) ? FK_DATA.protocols : [];
  const get = id => protocols().find(p => p.id === id);
  const fixed = new Set([...LIFE.map(x => x[0]), ...CHOOSER.map(x => x[0])]);

  /* ---------- Rendering ---------- */
  const openCats = new Set();
  let chooserOpen = false;
  const draft = p => p.draft === true ? '<small class="em-draft">Draft</small>' : '';
  const protoBtn = p => '<button type="button" class="em-btn" data-open="' + esc(p.id) + '"><span>' + esc(p.title) + '</span>' + draft(p) + '</button>';
  const protoKeys = list => list.filter(k => k[0] === 'p').map(k => get(k.slice(2))).filter(Boolean);
  const group = (id, title, ps) => { $(id).innerHTML = ps.length ? '<h3 class="em-h">' + title + '</h3><div class="em-grid">' + ps.map(protoBtn).join('') + '</div>' : ''; };

  function renderResume() {
    const a = FK.protocol && FK.protocol.active();
    const p = a && get(a.id);
    if (!p) { $('emResume').innerHTML = ''; return; }
    const i = p.steps.findIndex(s => s.id === a.step);
    $('emResume').innerHTML = '<button type="button" class="em-resume" data-resume="' + esc(a.id) + '" data-step="' + esc(a.step) +
      '">Resume: ' + esc(p.title) + ', ' + (i + 1) + '/' + p.steps.length + '</button>';
  }

  function renderLife() {
    const fixedBtn = id => {
      const p = get(id), label = LIFE.find(x => x[0] === id)[1];
      return p ? '<button type="button" data-open="' + esc(id) + '"><span>' + label + '</span>' + draft(p) + '</button>' : '';
    };
    const opts = CHOOSER.filter(([id]) => get(id));
    const breathing = opts.length ? '<button type="button" data-act="breathing" aria-expanded="' + chooserOpen +
      '" aria-controls="emChooser"><span>Not breathing</span></button>' : '';
    $('emLife').innerHTML = fixedBtn('bleeding') + breathing + fixedBtn('choking');
    $('emChooser').hidden = !(chooserOpen && opts.length);
    $('emChooser').innerHTML = opts.map(([id, label]) => '<button type="button" class="em-btn" data-open="' + esc(id) + '"><span>' + label + '</span>' + draft(get(id)) + '</button>').join('');
  }

  function renderCats() {
    document.querySelectorAll('#emCatsDyn details').forEach(d => { if (d.open) openCats.add(d.dataset.cat); else openCats.delete(d.dataset.cat); });   // keep what the user opened
    $('emCatsDyn').innerHTML = CATS.map(([cat, label]) => {
      const ps = protocols().filter(p => p.category === cat && !(cat === 'life' && fixed.has(p.id)));
      if (!ps.length) return '';
      return '<details class="ref" data-cat="' + cat + '"' + (openCats.has(cat) ? ' open' : '') + '><summary data-cat="' + cat + '">' + label +
        '</summary><div class="body em-grid">' + ps.map(protoBtn).join('') + '</div></details>';
    }).join('');
  }

  function render() {
    renderResume();
    renderLife();
    group('emPinned', '★ Pinned', protoKeys(FK.pins.all()));
    group('emRecent', 'Recent', protoKeys(FK.recent.all()));
    renderCats();
  }

  /* ---------- Events ---------- */
  $('emHome').addEventListener('click', e => {
    const open = e.target.closest('[data-open]');
    if (open) { FK.protocol.open(open.dataset.open); return; }
    const res = e.target.closest('[data-resume]');
    if (res) { FK.protocol.open(res.dataset.resume, res.dataset.step); return; }
    if (e.target.closest('[data-act="breathing"]')) { chooserOpen = !chooserOpen; render(); }
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
