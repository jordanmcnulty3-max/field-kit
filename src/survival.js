/* ---------- Survival: topics and checklists from FK_DATA, the Survival home and pages (#/survival/<topicId>, /list/<id>, /tool/<name>) ---------- */
(() => {
  const FK = window.FK;
  const esc = FK.esc;
  const $ = id => document.getElementById(id);
  const CATS = [['basics', 'Basics'], ['water', 'Water and sanitation'], ['heat', 'Heat, shelter and winter'], ['radiation', 'Radiation and fallout'],
    ['food', 'Food'], ['comms', 'Comms'], ['staying', 'Staying put'], ['moving', 'Moving'], ['town', 'Town hazards and health']];
  const KEY = /^([scu]):([\w-]{1,60})$/;
  const JUMP_MIN = 4;   // a topic with this many sections gets a jump list
  const homeEl = $('survHome'), pageEl = $('survPage'), live = $('survLive');

  /* ---------- Data: well-formed topics only (an object with a string id and title and a sections array) ---------- */
  const filled = v => typeof v === 'string' && v.trim() !== '';
  const okTopic = t => !!t && typeof t === 'object' && filled(t.id) && filled(t.title) && Array.isArray(t.sections);
  let src = null, srcLen = -1, list = [];
  function topics() {
    const s = window.FK_DATA && Array.isArray(window.FK_DATA.topics) ? window.FK_DATA.topics : null;
    if (s !== src || (s && s.length !== srcLen)) { src = s; srcLen = s ? s.length : -1; list = s ? s.filter(okTopic) : []; }
    return list;
  }
  const topic = id => topics().find(t => t.id === id) || null;

  /* Checklists: an object with a string id and title and at least one item that has a string id and text. Bad items are dropped. */
  const okItem = it => !!it && typeof it === 'object' && filled(it.id) && filled(it.text);
  let lsrc = null, llen = -1, lists = [];
  function checklists() {
    const s = window.FK_DATA && Array.isArray(window.FK_DATA.checklists) ? window.FK_DATA.checklists : null;
    if (s !== lsrc || (s && s.length !== llen)) {
      lsrc = s; llen = s ? s.length : -1;
      lists = s ? s.filter(c => !!c && typeof c === 'object' && filled(c.id) && filled(c.title) && Array.isArray(c.items))
        .map(c => ({ ...c, items: c.items.filter(okItem) })).filter(c => c.items.length) : [];
    }
    return lists;
  }
  const checklist = id => checklists().find(c => c.id === id) || null;

  /* Ticks live in store 'checks' = { [checklistId]: [itemId, ...] }. Anything that is not that shape counts as no ticks. */
  const plain = v => !!v && typeof v === 'object' && !Array.isArray(v);
  const allChecks = () => { const v = FK.store.get('checks', null); return plain(v) ? v : {}; };
  function ticks(id) {   // the ticked item ids of a checklist, in item order; ids that are not items of it are ignored
    const c = checklist(id), v = allChecks();
    if (!c || !Object.hasOwn(v, id) || !Array.isArray(v[id])) return [];
    const on = new Set(v[id].filter(x => typeof x === 'string'));
    return c.items.filter(it => on.has(it.id)).map(it => it.id);
  }
  function saveTicks(id, ids) {   // false when the phone's storage is full; other lists' valid ticks are kept as they are
    const out = {}, v = allChecks();
    for (const k of Object.keys(v)) if (k !== id && Array.isArray(v[k])) out[k] = v[k].filter(x => typeof x === 'string');
    if (ids.length) out[id] = ids;
    return FK.store.set('checks', out);
  }

  /* ---------- Page providers: Tasks 8 to 10 draw checklists and tools at #/survival/list/<id> and #/survival/tool/<name> ---------- */
  const providers = { list: [], tool: [] };
  function registerPage(segment, fn) {
    if (Object.hasOwn(providers, segment) && typeof fn === 'function') providers[segment].push(fn);
  }

  /* ---------- Rendering. Every string from the data goes through esc(); only figSvg (built from figs/) is trusted markup. ---------- */
  const strs = a => (Array.isArray(a) ? a.filter(x => typeof x === 'string') : []);
  const items = a => strs(a).map(x => '<li>' + esc(x) + '</li>').join('');
  const draftTag = t => (t.draft === true ? '<small class="sv-draft">Draft</small>' : '');

  function table(tb) {
    if (!tb || typeof tb !== 'object' || !Array.isArray(tb.rows)) return '';
    const cell = (tag, c) => '<' + tag + '>' + esc(c == null ? '' : c) + '</' + tag + '>';
    const head = Array.isArray(tb.head) && tb.head.length ? '<thead><tr>' + tb.head.map(c => cell('th', c)).join('') + '</tr></thead>' : '';
    const rows = tb.rows.filter(Array.isArray).map(r => '<tr>' + r.map(c => cell('td', c)).join('') + '</tr>').join('');
    return '<div class="tablewrap" tabindex="0" role="region" aria-label="Table, scrolls sideways"><table>' + head + '<tbody>' + rows + '</tbody></table></div>';
  }
  function block(b) {
    if (!b || typeof b !== 'object') return '';
    if (typeof b.p === 'string') return '<p>' + esc(b.p) + '</p>';
    if (Array.isArray(b.list)) return '<ul>' + items(b.list) + '</ul>';
    if (Array.isArray(b.steps)) return '<ol class="steps">' + items(b.steps) + '</ol>';
    if (typeof b.warn === 'string') return '<p class="sv-warn"><strong>Warning:</strong> ' + esc(b.warn) + '</p>';
    if (b.table) return table(b.table);
    if (typeof b.fig === 'string') {
      if (typeof b.figSvg !== 'string') return '';
      return '<figure class="fig"><button type="button" aria-label="Enlarge diagram: ' + esc(typeof b.figLabel === 'string' ? b.figLabel : b.fig) + '">' +
        b.figSvg + '</button>' + (typeof b.cap === 'string' ? '<figcaption>' + esc(b.cap) + '</figcaption>' : '') + '</figure>';
    }
    if (typeof b.link === 'string' && filled(b.label)) return '<button type="button" class="sv-link" data-link="' + esc(b.link) + '"><span>' + esc(b.label) + '</span></button>';
    return '';
  }

  /* Title, Draft tag and pin star: the same on a topic page and a checklist page. */
  function headHTML(key, t) {
    const pinned = FK.pins.has(key);
    return '<div class="sv-head"><h2 class="sv-title" id="svTitle" tabindex="-1">' + esc(t.title) + '</h2>' + draftTag(t) +
      '<button type="button" class="sv-pin" data-act="pin" aria-pressed="' + pinned + '" aria-label="Pin this ' + (key[0] === 'c' ? 'checklist' : 'topic') + '">' + (pinned ? '★' : '☆') + '</button></div>';
  }
  function footHTML(t) {
    const sources = (Array.isArray(t.sources) ? t.sources : []).filter(s => s && filled(s.name));
    return '<footer class="sv-foot">' +
      (sources.length ? '<h3>Sources</h3><ul>' + sources.map(s => '<li><b>' + esc(s.name) + '</b>' + (filled(s.used) ? ': ' + esc(s.used) : '') + '</li>').join('') + '</ul>' : '') +
      (filled(t.reviewed) ? '<p>Reviewed ' + esc(t.reviewed) + '</p>' : '') +
      (filled(t.asOf) ? '<p>As of ' + esc(t.asOf) + '</p>' : '') + '</footer>';
  }

  function topicHTML(t) {
    const secs = t.sections.filter(s => s && typeof s === 'object');
    const head = headHTML('s:' + t.id, t);
    const first = strs(t.doFirst).length ? '<div class="sv-first"><h3>Do first</h3><ol class="steps">' + items(t.doFirst) + '</ol></div>' : '';
    const jump = secs.length >= JUMP_MIN ? '<nav class="sv-jump" aria-label="Sections in this topic">' +
      secs.map((s, i) => '<button type="button" data-jump="' + i + '">' + esc(typeof s.h === 'string' ? s.h : '') + '</button>').join('') + '</nav>' : '';
    const body = secs.map((s, i) => '<section class="sv-sec"><h3 id="svSec' + i + '" tabindex="-1">' + esc(typeof s.h === 'string' ? s.h : '') + '</h3>' +
      (Array.isArray(s.blocks) ? s.blocks.map(block).join('') : '') + '</section>').join('');
    return '<article class="sv-page">' + head + first + jump + body + footHTML(t) + '</article>';
  }

  /* ---------- Checklist pages (#/survival/list/<id>): native checkboxes, a count, Clear ticks with an in-page second tap ---------- */
  const countOf = id => ticks(id).length + '/' + checklist(id).items.length;
  function checklistHTML(c) {
    const on = new Set(ticks(c.id));
    const rows = c.items.map((it, i) => '<li><label class="sv-check"><input type="checkbox" data-item="' + esc(it.id) + '" aria-labelledby="svCt' + i + '"' +
      (filled(it.note) ? ' aria-describedby="svCn' + i + '"' : '') + (on.has(it.id) ? ' checked' : '') + '><span><span id="svCt' + i + '" class="sv-ctext">' + esc(it.text) + '</span>' +
      (filled(it.note) ? '<small id="svCn' + i + '" class="sv-cnote">' + esc(it.note) + '</small>' : '') + '</span></label></li>').join('');
    return '<article class="sv-page" data-list="' + esc(c.id) + '">' + headHTML('c:' + c.id, c) +
      (filled(c.summary) ? '<p>' + esc(c.summary) + '</p>' : '') +
      '<div class="sv-checkbar"><p class="sv-count" role="status">' + esc(countOf(c.id)) + '</p>' +
      '<button type="button" class="btn ghost" data-act="clear-ticks" aria-disabled="' + (on.size ? 'false' : 'true') + '">Clear ticks</button></div>' +
      '<ul class="sv-checks">' + rows + '</ul>' + footHTML(c) + '</article>';
  }
  /* Draws a checklist into the page; false for an id that is not one. The returned function stops the Clear ticks timer. */
  function drawChecklist(id, el) {
    const c = checklist(id);
    if (!c) return false;
    el.innerHTML = checklistHTML(c);
    FK.recent.add('c:' + id);
    return () => { clearTimeout(clearT); clearT = null; clearSure = false; };
  }
  let clearT = null, clearSure = false;
  function paintClear(c) {
    const btn = pageEl.querySelector('[data-act="clear-ticks"]');
    if (!btn) return;
    const n = ticks(c.id).length;
    pageEl.querySelector('.sv-count').textContent = countOf(c.id);
    btn.setAttribute('aria-disabled', String(n === 0));
    btn.textContent = clearSure ? 'Confirm clear' : 'Clear ticks';
    btn.classList.toggle('ghost', !clearSure);
  }
  function setClearSure(c, on) {
    clearTimeout(clearT); clearT = null; clearSure = on;
    if (on) clearT = setTimeout(() => { clearSure = false; clearT = null; paintClear(c); }, FK.tools.confirm.revertMs);
    paintClear(c);
  }
  function onChecklistClick(e, c) {
    if (!e.target.closest('[data-act="clear-ticks"]') || !ticks(c.id).length) return;
    if (!clearSure) { setClearSure(c, true); return; }
    if (!saveTicks(c.id, [])) { FK.toast(FK.FULL_MSG); return; }
    pageEl.querySelectorAll('input[data-item]').forEach(b => { b.checked = false; });
    setClearSure(c, false);
  }
  function onChecklistChange(e, c) {
    const b = e.target.closest('input[data-item]');
    if (!b) return;
    const next = new Set(ticks(c.id));
    if (b.checked) next.add(b.dataset.item); else next.delete(b.dataset.item);
    if (!saveTicks(c.id, c.items.filter(it => next.has(it.id)).map(it => it.id))) { b.checked = !b.checked; FK.toast(FK.FULL_MSG); return; }
    setClearSure(c, false);   // a tick since the first tap: ask again
  }

  /* ---------- Home: filters, Pinned, Recent, Topics by category, then Tools and Checklists from homeItems providers ---------- */
  const WHERE = [['any', 'Any'], ['town', 'Town'], ['rural', 'Rural'], ['woods', 'Woods'], ['coast', 'Coast']];
  const WHEN = [['any', 'Any'], ['cold', 'Cold'], ['warm', 'Warm']];
  const DIMS = [['where', 'Where', WHERE], ['when', 'When', WHEN]];
  const ANY = () => ({ where: 'any', when: 'any' });
  /* A stored filter that is not an object, or has an unknown value, counts as Any (per dimension). */
  function filter() {
    const v = FK.store.get('survFilter', null), out = ANY();
    if (!v || typeof v !== 'object' || Array.isArray(v)) return out;
    for (const [dim, , opts] of DIMS) if (typeof v[dim] === 'string' && opts.some(o => o[0] === v[dim])) out[dim] = v[dim];
    return out;
  }
  const tagged = (t, dim, val) => val === 'any' || !Array.isArray(t[dim]) || !t[dim].length || t[dim].includes(val);
  const matches = (t, f) => tagged(t, 'where', f.where) && tagged(t, 'when', f.when);
  const byTitle = (a, b) => (a.id === 'surv-priorities' ? -1 : b.id === 'surv-priorities' ? 1 : a.title.localeCompare(b.title));

  const homeItemFns = { tool: [], list: [] };
  function homeItems(kind, fn) {
    if (Object.hasOwn(homeItemFns, kind) && typeof fn === 'function') homeItemFns[kind].push(fn);
  }
  function itemsFor(kind) {
    const out = [];
    for (const fn of homeItemFns[kind]) {
      let r;
      try { r = fn(); } catch (e) { console.warn('Survival home provider failed', e); continue; }
      if (Array.isArray(r)) for (const it of r) if (it && typeof it === 'object' && typeof it.key === 'string' && KEY.test(it.key) && filled(it.title)) out.push(it);
    }
    return out;
  }

  registerPage('list', drawChecklist);
  homeItems('list', () => checklists().map(c => ({ key: 'c:' + c.id, title: c.title, badge: countOf(c.id) })));

  /* Redraw a block only when its markup changed, so focus and opened categories survive. */
  const drawn = new WeakMap();
  const setHTML = (el, html) => { if (drawn.get(el) !== html) { el.innerHTML = html; drawn.set(el, html); } };
  const openCats = new Set();

  const itemBtn = it => '<button type="button" class="em-btn" data-key="' + esc(it.key) + '"><span>' + esc(it.title) + '</span>' +
    (filled(it.badge) ? '<span class="sv-badge">' + esc(it.badge) + '</span>' : '') + '</button>';
  const section = (el, title, its) => setHTML(el, its.length ? '<h2 class="sv-cat">' + title + '</h2><div class="sv-list">' + its.map(itemBtn).join('') + '</div>' : '');

  function catsHTML(f, withOpen) {
    return CATS.map(([cat, label]) => {
      const all = topics().filter(t => t.category === cat);
      if (!all.length) return '';
      const ts = all.filter(t => matches(t, f)).sort(byTitle);
      return '<details class="ref" data-cat="' + cat + '"' + (withOpen && openCats.has(cat) ? ' open' : '') + '><summary>' + label + '</summary><div class="body">' +
        (ts.length ? '<div class="sv-list">' + ts.map(t => '<button type="button" class="em-btn" data-key="s:' + esc(t.id) + '"><span>' + esc(t.title) + '</span>' + draftTag(t) + '</button>').join('') + '</div>'
          : '<p class="sv-none">No topics for this filter</p>') + '</div></details>';
    }).join('');
  }
  const CLEAR_RECENT = '<button type="button" class="em-clear" data-act="clear-recent" aria-label="Clear recent list">Clear</button>';
  /* Pinned and Recent: survival keys only, titled by search; a key whose thing no longer exists is skipped. */
  function keyed(list) {
    return list.map(key => {
      const d = FK.search && FK.search.describe(key);
      return d ? { key, title: d.title, badge: d.draft ? 'Draft' : '' } : null;
    }).filter(Boolean);
  }
  function renderKeyed() {
    if (!built) return;
    const row = (title, its, extra) => its.length ? '<div class="em-hrow"><h2 class="sv-cat">' + title + '</h2>' + (extra || '') + '</div><div class="sv-list">' + its.map(itemBtn).join('') + '</div>' : '';
    setHTML($('survPinned'), row('★ Pinned', keyed(FK.pins.forSection('survival'))));
    setHTML($('survRecent'), row('Recent', keyed(FK.recent.forSection('survival')), CLEAR_RECENT));
  }
  function markFilters(f) {   // toggle state in place: the buttons are never redrawn, so the one just pressed keeps focus
    for (const b of $('survFilters').querySelectorAll('button[data-dim]')) b.setAttribute('aria-pressed', String(f[b.dataset.dim] === b.dataset.val));
  }
  let built = false;
  function build() {
    homeEl.innerHTML = '<div id="survFilters" class="sv-filters">' + DIMS.map(([dim, label, opts]) =>
      '<div class="sv-frow" role="group" aria-label="' + label + '"><span class="sv-flabel" aria-hidden="true">' + label + ':</span>' +
      opts.map(([v, l]) => '<button type="button" data-dim="' + dim + '" data-val="' + v + '" aria-pressed="false">' + l + '</button>').join('') + '</div>').join('') +
      '</div><div id="survPinned"></div><div id="survRecent"></div><div id="survTopics"><h2 class="sv-cat">Topics</h2><div id="survCats"></div></div>' +
      '<div id="survTools"></div><div id="survLists"></div>';
    built = true;
  }
  function renderHome() {
    if (!built) build();
    const f = filter();
    markFilters(f);
    const cats = $('survCats');
    cats.querySelectorAll('details').forEach(d => { if (d.open) openCats.add(d.dataset.cat); else openCats.delete(d.dataset.cat); });   // keep what the user opened
    // Compare without the open state: a redraw that changes only which categories are open leaves the DOM (and focus) alone.
    const base = catsHTML(f, false);
    if (drawn.get(cats) !== base) { cats.innerHTML = catsHTML(f, true); drawn.set(cats, base); }
    renderKeyed();
    section($('survTools'), 'Tools', itemsFor('tool'));
    section($('survLists'), 'Checklists', itemsFor('list'));
  }

  /* ---------- Showing home or a page, decided only from the route ---------- */
  let cleanup = null, opener = null, homeY = 0, onPage = false;
  function closePage() {
    const fn = cleanup;
    cleanup = null;
    if (fn) fn();
    pageEl.innerHTML = '';
  }
  function showHome() {
    closePage();
    const back = onPage;
    onPage = false;
    pageEl.hidden = true;
    homeEl.hidden = false;
    renderHome();
    if (back) { window.scrollTo(0, homeY); FK.refocus(opener); opener = null; }
  }
  function showPage(draw) {
    if (!onPage) { homeY = window.scrollY; opener = FK.opener(document.activeElement); }
    closePage();
    const out = draw(pageEl);
    if (out === false) return false;
    if (typeof out === 'function') cleanup = out;
    onPage = true;
    live.textContent = '';
    homeEl.hidden = true;
    pageEl.hidden = false;
    window.scrollTo(0, 0);
    return true;
  }
  function drawProvided(segment, id) {
    const shown = showPage(el => {
      for (const fn of providers[segment]) {
        let out = false;
        try { out = fn(id, el); } catch (e) { console.warn('Survival page provider failed', e); }   // a broken provider counts as "unknown id"
        if (out !== false) return out;
        el.innerHTML = '';
      }
      return false;
    });
    const h = shown && $('svTitle');
    if (h) h.focus({ preventScroll: true });
    return shown;
  }
  function drawTopic(t) {
    showPage(el => { el.innerHTML = topicHTML(t); });
    FK.recent.add('s:' + t.id);
    $('svTitle').focus({ preventScroll: true });
  }

  /* A bad address is corrected after the router has finished with it (it re-writes the address after its event), with no new history entry. */
  function redirect(r) {
    showHome();
    live.textContent = 'That Survival page was not found.';
    queueMicrotask(() => { if (FK.route.current() === r) FK.route.go('/survival', { replace: true }); });
  }
  function onRoute(r) {
    if (r.tab !== 'survival') { if (onPage) { closePage(); onPage = false; opener = null; } return; }
    const [a, b, ...rest] = r.parts;
    if (!a) { showHome(); return; }
    if (Object.hasOwn(providers, a)) { if (b && !rest.length && drawProvided(a, b)) return; return redirect(r); }
    const t = !b ? topic(a) : null;
    if (t) drawTopic(t); else redirect(r);
  }

  /* Open a key: s:<topicId> or c:<checklistId> (u: arrives with Tasks 9 and 10). Returns false for anything it cannot open. */
  function open(key, opts) {
    const m = typeof key === 'string' ? KEY.exec(key) : null;
    const path = !m ? null : m[1] === 's' && topic(m[2]) ? '/survival/' + m[2] : m[1] === 'c' && checklist(m[2]) ? '/survival/list/' + m[2] : null;
    if (!path) return false;
    FK.route.go(path, opts && opts.replace ? { replace: true } : undefined);
    return true;
  }
  function openLink(key) {
    if (open(key)) return;
    if (/^p:[\w-]+$/.test(key)) FK.protocol.open(key.slice(2));
    else if (FK.search) FK.search.go(key);
  }

  /* ---------- Events ---------- */
  homeEl.addEventListener('click', e => {
    const fb = e.target.closest('button[data-dim]');
    if (fb) {
      const f = filter();
      f[fb.dataset.dim] = fb.dataset.val;
      if (!FK.store.set('survFilter', f)) FK.toast(FK.FULL_MSG);
      renderHome();
      return;
    }
    if (e.target.closest('[data-act="clear-recent"]')) {   // the button goes with the list, so hand focus to the first filter button
      FK.recent.clear();
      const first = $('survFilters').querySelector('button');
      if (first) first.focus();
      return;
    }
    const b = e.target.closest('[data-key]');
    if (b) FK.survival.open(b.dataset.key);
  });
  FK.on('pins', renderKeyed);
  FK.on('recent', renderKeyed);
  pageEl.addEventListener('click', e => {
    const link = e.target.closest('[data-link]');
    if (link) { openLink(link.dataset.link); return; }
    const jump = e.target.closest('[data-jump]');
    if (jump) {
      const h = $('svSec' + jump.dataset.jump);
      if (h) { h.scrollIntoView({ block: 'start' }); h.focus({ preventScroll: true }); }
      return;
    }
    const pin = e.target.closest('.sv-head [data-act="pin"]');
    if (pin) {
      const key = pageKey(FK.route.current());
      if (key) FK.pins.toggle(key);
      return;
    }
    const c = shownChecklist();
    if (c) onChecklistClick(e, c);
  });
  pageEl.addEventListener('change', e => { const c = shownChecklist(); if (c) onChecklistChange(e, c); });
  /* The key of the topic or checklist the page shows, or null. */
  function pageKey(r) {
    if (r.tab !== 'survival') return null;
    if (r.parts[0] === 'list') return r.parts.length === 2 && checklist(r.parts[1]) ? 'c:' + r.parts[1] : null;
    return r.parts.length === 1 && topic(r.parts[0]) ? 's:' + r.parts[0] : null;
  }
  const shownChecklist = () => { const k = pageKey(FK.route.current()); return k && k[0] === 'c' ? checklist(k.slice(2)) : null; };
  FK.on('pins', () => {
    const star = pageEl.querySelector('.sv-head [data-act="pin"]'), key = pageKey(FK.route.current());
    if (!star || !key) return;
    const on = FK.pins.has(key);
    star.setAttribute('aria-pressed', String(on));
    star.textContent = on ? '★' : '☆';
  });
  FK.on('route', onRoute);

  FK.survival = { topics, topic, checklists, checklist, ticks, open, renderHome, refreshHome: renderHome, registerPage, homeItems, filter };
  // The router's first route ran before this file loaded; wait until the rest of the script (page providers) has loaded too.
  queueMicrotask(() => onRoute(FK.route.current()));
})();

/* ---------- Diagrams: tap to enlarge ---------- */
(() => {
  const { $ } = window.FK;
  const dlg = $('#dlgFig');
  $('#tab-survival').addEventListener('click', e => {
    const b = e.target.closest('.fig button');
    if (!b) return;
    $('#figBody').innerHTML = b.innerHTML;
    const cap = b.parentElement.querySelector('figcaption');
    $('#figCap').textContent = cap ? cap.textContent : '';
    dlg.showModal();
  });
  $('#figClose').addEventListener('click', () => dlg.close());
  dlg.addEventListener('click', e => { if (e.target === dlg) dlg.close(); });
})();
