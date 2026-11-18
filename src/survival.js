/* ---------- Survival: topics from FK_DATA.topics, the Survival home and pages (#/survival/<topicId>, /list/<id>, /tool/<name>) ---------- */
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

  function topicHTML(t) {
    const secs = t.sections.filter(s => s && typeof s === 'object');
    const pinned = FK.pins.has('s:' + t.id);
    const head = '<div class="sv-head"><h2 class="sv-title" id="svTitle" tabindex="-1">' + esc(t.title) + '</h2>' + draftTag(t) +
      '<button type="button" class="sv-pin" data-act="pin" aria-pressed="' + pinned + '" aria-label="Pin this topic">' + (pinned ? '★' : '☆') + '</button></div>';
    const first = strs(t.doFirst).length ? '<div class="sv-first"><h3>Do first</h3><ol class="steps">' + items(t.doFirst) + '</ol></div>' : '';
    const jump = secs.length >= JUMP_MIN ? '<nav class="sv-jump" aria-label="Sections in this topic">' +
      secs.map((s, i) => '<button type="button" data-jump="' + i + '">' + esc(typeof s.h === 'string' ? s.h : '') + '</button>').join('') + '</nav>' : '';
    const body = secs.map((s, i) => '<section class="sv-sec"><h3 id="svSec' + i + '" tabindex="-1">' + esc(typeof s.h === 'string' ? s.h : '') + '</h3>' +
      (Array.isArray(s.blocks) ? s.blocks.map(block).join('') : '') + '</section>').join('');
    const sources = (Array.isArray(t.sources) ? t.sources : []).filter(s => s && filled(s.name));
    const foot = '<footer class="sv-foot">' +
      (sources.length ? '<h3>Sources</h3><ul>' + sources.map(s => '<li><b>' + esc(s.name) + '</b>' + (filled(s.used) ? ': ' + esc(s.used) : '') + '</li>').join('') + '</ul>' : '') +
      (filled(t.reviewed) ? '<p>Reviewed ' + esc(t.reviewed) + '</p>' : '') +
      (filled(t.asOf) ? '<p>As of ' + esc(t.asOf) + '</p>' : '') + '</footer>';
    return '<article class="sv-page">' + head + first + jump + body + foot + '</article>';
  }

  /* Stub home: category names with their topics as buttons (Task 5 builds the real home). Redrawn only when the markup changes,
     so the button that opened a page is still there to take focus back. */
  let homeHTML = null;
  function renderHome() {
    const html = CATS.map(([cat, label]) => {
      const ts = topics().filter(t => t.category === cat);
      return ts.length ? '<h2 class="sv-cat">' + label + '</h2><div class="sv-list">' + ts.map(t =>
        '<button type="button" class="em-btn" data-key="s:' + esc(t.id) + '"><span>' + esc(t.title) + '</span>' + draftTag(t) + '</button>').join('') + '</div>' : '';
    }).join('');
    if (html !== homeHTML) { homeEl.innerHTML = html; homeHTML = html; }
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
    return showPage(el => {
      for (const fn of providers[segment]) {
        const out = fn(id, el);
        if (out !== false) return out;
        el.innerHTML = '';
      }
      return false;
    });
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

  /* Open a key: s:<topicId> (c: and u: arrive with Tasks 8 to 10). Returns false for anything it cannot open. */
  function open(key, opts) {
    const m = typeof key === 'string' ? KEY.exec(key) : null;
    if (!m || m[1] !== 's' || !topic(m[2])) return false;
    FK.route.go('/survival/' + m[2], opts && opts.replace ? { replace: true } : undefined);
    return true;
  }
  function openLink(key) {
    if (open(key)) return;
    if (/^p:[\w-]+$/.test(key)) FK.protocol.open(key.slice(2));
    else if (FK.search) FK.search.go(key);
  }

  /* ---------- Events ---------- */
  homeEl.addEventListener('click', e => {
    const b = e.target.closest('[data-key]');
    if (b) open(b.dataset.key);
  });
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
      const r = FK.route.current();
      if (r.tab === 'survival' && topic(r.parts[0])) FK.pins.toggle('s:' + r.parts[0]);
    }
  });
  FK.on('pins', () => {
    const star = pageEl.querySelector('.sv-head [data-act="pin"]'), r = FK.route.current();
    if (!star || r.tab !== 'survival' || !topic(r.parts[0])) return;
    const on = FK.pins.has('s:' + r.parts[0]);
    star.setAttribute('aria-pressed', String(on));
    star.textContent = on ? '★' : '☆';
  });
  FK.on('route', onRoute);

  FK.survival = { topics, topic, open, renderHome, registerPage };
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
