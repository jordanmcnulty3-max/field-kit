/* ---------- App-wide search: one index over protocols, survival topics, tools, reports and app screens; overlay at #/search ---------- */
(() => {
  const FK = window.FK;
  const esc = FK.esc;
  const $ = id => document.getElementById(id);
  const MAX_RESULTS = 30;
  const SNIPPET = 90, LEAD = 30;   // characters of snippet, and how many of them may come before the first match
  const W = { title: 5, keywords: 4, summary: 3, body: 1 };
  const KINDS = ['Emergency', 'Advanced', 'Tool', 'Report', 'Survival', 'App'];   // order is only the tie-break for groups with equal rank

  /* App screens and what each opens. Keywords are fixed here; protocol synonyms live in each protocol's own keywords. */
  const SCREENS = {
    map: { title: 'Map', keywords: 'offline topo layers satellite imagery crosshair mark track recording gpx' },
    position: { title: 'Position and compass', keywords: 'gps mgrs grid coordinates latitude longitude lat lon heading bearing declination north' },
    ballistics: { title: 'Ballistics', keywords: 'dope card rifle bullet wind elevation windage mil moa range shot drop' },
    areas: { title: 'Saved areas', keywords: 'offline map download tiles saved region storage' },
    waypoints: { title: 'Waypoints', keywords: 'mark waypoint target kml atak coordinates' },
    settings: { title: 'Settings and backup', keywords: 'backup restore export import data night red light update version storage' }
  };
  const TOOL_WORDS = {
    tq: 'tourniquet bleeding limb timer', cpr: 'metronome compressions breaths cardiac arrest', rate: 'pulse breathing respiration heart rate count',
    burn: 'burns percent body surface rule of nines', log: 'patient casualty notes vitals avpu', '9line': 'medevac casevac nine line evacuation helicopter', mist: 'casualty report mechanism injury signs treatment'
  };

  /* ---------- Text handling: lowercase, no diacritics, no punctuation, apostrophes dropped ---------- */
  const norm = s => String(s).normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/['’]/g, '');
  const tokens = s => norm(s).match(/[\p{L}\p{N}]+/gu) || [];
  const WORD = /[\p{L}\p{N}]+(?:['’][\p{L}\p{N}]+)*/gu;   // words of the original text, with their positions
  const flat = s => String(s == null ? '' : s).replace(/\s+/g, ' ').trim();

  /* ---------- Index: built once, on first use ---------- */
  let docs = null;
  const field = (w, text, body) => ({ w, toks: [...new Set(tokens(text))], text: body ? flat(text) : '' });

  function build() {
    const out = [];
    const protocols = (window.FK_DATA && Array.isArray(FK_DATA.protocols)) ? FK_DATA.protocols : [];
    for (const p of protocols) {
      if (!p || typeof p.id !== 'string' || typeof p.title !== 'string') continue;
      const adv = p.tier === 'advanced' || p.category === 'advanced';
      const f = [field(W.title, p.title)];
      if (Array.isArray(p.keywords)) f.push(field(W.keywords, p.keywords.join(' ')));
      if (p.summary) f.push(field(W.summary, p.summary));
      for (const s of Array.isArray(p.steps) ? p.steps : []) {
        if (s && s.text) f.push(field(W.body, s.text, true));
        if (s && s.detail) f.push(field(W.body, Array.isArray(s.detail) ? s.detail.join(' ') : s.detail, true));
      }
      out.push({ key: 'p:' + p.id, title: p.title, kind: adv ? 'Advanced' : 'Emergency', draft: p.draft === true, fields: f });
    }
    for (const t of (FK.tools && FK.tools.list ? FK.tools.list() : [])) {
      const report = t.segment === 'report';
      out.push({ key: (report ? 'r:' : 't:') + t.name, title: t.label, kind: report ? 'Report' : 'Tool', draft: false,
        fields: [field(W.title, t.label), field(W.keywords, TOOL_WORDS[t.name] || '')] });
    }
    for (const d of topicEls()) {
      const clone = d.cloneNode(true);
      clone.querySelectorAll('summary,svg,figcaption').forEach(n => n.remove());
      out.push({ key: 's:' + d.id, title: topicTitle(d), kind: 'Survival', draft: false,
        fields: [field(W.title, topicTitle(d)), field(W.body, clone.textContent, true)] });
    }
    for (const [id, s] of Object.entries(SCREENS)) {
      out.push({ key: 'a:' + id, title: s.title, kind: 'App', draft: false, fields: [field(W.title, s.title), field(W.keywords, s.keywords)] });
    }
    return out;
  }
  const topicEls = () => [...document.querySelectorAll('#survTopics details.ref[id]')];
  const topicTitle = d => flat(d.querySelector('summary').textContent);
  const index = () => docs || (docs = build());

  /* ---------- Matching and ranking ---------- */
  const hits = (f, w) => f.toks.some(t => t.startsWith(w));
  function score(doc, words) {
    let total = 0;
    for (const w of words) {
      let best = 0;
      for (const f of doc.fields) {
        if (f.w <= best) continue;
        if (hits(f, w)) best = f.w;
      }
      if (!best) return 0;   // every word must match something
      total += best;
      if (doc.fields[0].toks.includes(w)) total += 0.5;   // a whole title word beats a mere prefix
    }
    return total;
  }

  /* Up to ~90 characters of body text around the first match, as safe markup: every piece goes through esc(). */
  function snippetFor(doc, words) {
    if (words.every(w => hits(doc.fields[0], w))) return '';   // the title already shows why it matched
    const isMatch = tok => { const n = norm(tok); return words.some(w => n.startsWith(w)); };
    for (const f of doc.fields) {
      if (f.w !== W.body || !f.toks.some(t => words.some(w => t.startsWith(w)))) continue;
      const text = f.text;
      let first = -1;
      for (const m of text.matchAll(WORD)) if (isMatch(m[0])) { first = m.index; break; }
      if (first < 0) continue;
      let a = Math.max(0, first - LEAD);
      if (a > 0 && text[a - 1] !== ' ') { const sp = text.indexOf(' ', a); a = sp >= 0 && sp < first ? sp + 1 : a; }
      let b = Math.min(text.length, a + SNIPPET);
      if (b < text.length && text[b] !== ' ') { const sp = text.lastIndexOf(' ', b); b = sp > first ? sp : b; }
      const piece = text.slice(a, b);
      let html = '', at = 0;
      for (const m of piece.matchAll(WORD)) {
        html += esc(piece.slice(at, m.index));
        html += isMatch(m[0]) ? '<mark>' + esc(m[0]) + '</mark>' : esc(m[0]);
        at = m.index + m[0].length;
      }
      return (a > 0 ? '…' : '') + html + esc(piece.slice(at)) + (b < text.length ? '…' : '');
    }
    return '';
  }

  const whereOf = doc => doc.kind;
  function query(q) {
    const words = [...new Set(tokens(q))];
    if (!words.length) return [];
    const scored = [];
    index().forEach((doc, i) => { const s = score(doc, words); if (s) scored.push({ doc, s, i }); });
    scored.sort((x, y) => y.s - x.s || x.i - y.i);
    return scored.slice(0, MAX_RESULTS).map(({ doc }) =>
      ({ key: doc.key, title: doc.title, where: whereOf(doc), snippet: snippetFor(doc, words), draft: doc.draft }));
  }

  /* What a stored key (pins, recent) shows as: { key, title, where, draft }, or null once the thing no longer exists. */
  function describe(key) {
    if (typeof key !== 'string' || key[1] !== ':') return null;
    const id = key.slice(2);
    switch (key[0]) {
      case 'p': {
        const p = FK.protocol && FK.protocol.get(id);
        return p ? { key, title: p.title, where: p.tier === 'advanced' || p.category === 'advanced' ? 'Advanced' : 'Emergency', draft: p.draft === true } : null;
      }
      case 't': case 'r': {
        const label = FK.tools && FK.tools.label(id);
        return label && FK.tools.segment(id) === (key[0] === 'r' ? 'report' : 'tool')
          ? { key, title: label, where: key[0] === 'r' ? 'Report' : 'Tool', draft: false } : null;
      }
      case 's': {
        const d = /^surv-[\w-]+$/.test(id) ? document.querySelector('#survTopics details.ref[id="' + id + '"]') : null;
        return d ? { key, title: topicTitle(d), where: 'Survival', draft: false } : null;
      }
      case 'a':
        return Object.hasOwn(SCREENS, id) ? { key, title: SCREENS[id].title, where: 'App', draft: false } : null;
    }
    return null;
  }

  /* ---------- Opening a result the way a user would. Inside the overlay the address entry is replaced, so Back returns to where the user was. ---------- */
  function whenMap(fn, tries = 30) {
    if (FK.leafletMap && FK.leafletMap()) fn();
    else if (tries > 0) requestAnimationFrame(() => whenMap(fn, tries - 1));
    else FK.toast('Open the map to see saved areas');
  }
  function go(key) {
    const d = describe(key);
    if (!d) return false;
    const replace = FK.route.isSearch();
    const nav = path => FK.route.go(path, replace ? { replace: true } : undefined);
    const id = key.slice(2);
    FK.recent.add(key);
    switch (key[0]) {
      case 'p': FK.protocol.open(id, undefined, { replace }); break;   // an advanced one still shows its one-time acknowledgement
      case 't': case 'r': FK.tools.start(id, { replace }); break;
      case 's': {
        nav('/survival');
        const el = document.getElementById(id);
        if (el.hidden) { const box = $('survSearch'); box.value = ''; box.dispatchEvent(new Event('input')); }   // the in-tab search had filtered it out
        el.open = true;
        el.scrollIntoView({ block: 'start' });
        el.querySelector('summary').focus({ preventScroll: true });
        break;
      }
      case 'a':
        if (id === 'settings') { if (replace) FK.route.closeSearch(); $('menuBtn').click(); }
        else if (id === 'areas') { nav('/tactical/map'); whenMap(() => $('mSave').click()); }   // the Saved areas list is in the Save map dialog
        else if (id === 'waypoints') { nav('/tactical/position'); $('blkWaypoints').scrollIntoView({ block: 'start' }); }
        else nav('/tactical/' + id);
        break;
    }
    return true;
  }

  /* ---------- Overlay ---------- */
  const pane = $('searchPane'), input = $('searchInput'), clearBtn = $('searchClear'), bodyEl = $('searchBody'), live = $('searchLive'), magnifier = $('searchBtn');
  const BEHIND = ['.top', 'main', '.tabbar'];
  let opener = null;

  const item = r => '<button type="button" class="sr-item" data-key="' + esc(r.key) + '"><span>' + esc(r.title) +
    (r.draft ? ' <span class="sr-tag muted">Draft</span>' : '') + '</span><small>' + esc(r.where) + (r.snippet ? ' · ' + r.snippet : '') + '</small></button>';

  /* Results are ranked; the list shows them in groups by kind, groups ordered by their best result. */
  function grouped(results) {
    const order = [];
    results.forEach(r => { if (!order.includes(r.where)) order.push(r.where); });
    return order.map(w => '<h3 class="sr-h">' + esc(w) + '</h3>' + results.filter(r => r.where === w).map(item).join('')).join('');
  }
  function render() {
    const q = input.value;
    clearBtn.hidden = !q;
    if (!tokens(q).length) {
      const section = (title, keys) => {
        const rs = keys.map(describe).filter(Boolean);
        return rs.length ? '<h3 class="sr-h">' + title + '</h3>' + rs.map(item).join('') : '';
      };
      const html = section('Pinned', FK.pins.all()) + section('Recent', FK.recent.all());
      bodyEl.innerHTML = html || '<p class="sr-empty">Type to find a protocol, survival topic, tool, report or screen.</p>';
      live.textContent = '';
      return;
    }
    const rs = query(q);
    bodyEl.innerHTML = rs.length ? grouped(rs) : '<p class="sr-empty">No matches for “' + esc(q.trim()) + '”.</p>';
    live.textContent = rs.length ? rs.length + (rs.length === 1 ? ' result' : ' results') : 'No matches';
  }

  function show() {
    if (!pane.hidden) return;
    opener = document.activeElement;
    index();
    BEHIND.forEach(s => document.querySelectorAll(s).forEach(n => { n.inert = true; }));
    document.body.classList.add('searching');
    input.value = '';
    render();
    pane.hidden = false;
    input.focus();
  }
  function hide() {
    if (pane.hidden) return;
    pane.hidden = true;
    document.body.classList.remove('searching');
    BEHIND.forEach(s => document.querySelectorAll(s).forEach(n => { n.inert = false; }));
    const back = magnifier.offsetParent ? magnifier : (opener && opener.isConnected && opener.offsetParent ? opener : null);   // the header is hidden behind a protocol or tool
    if (back) back.focus({ preventScroll: true });
    opener = null;
  }

  FK.on('search', s => (s.open ? show() : hide()));
  magnifier.addEventListener('click', () => FK.route.go('/search'));
  $('searchClose').addEventListener('click', () => history.back());
  clearBtn.addEventListener('click', () => { input.value = ''; render(); input.focus(); });
  input.addEventListener('input', render);

  bodyEl.addEventListener('click', e => {
    const b = e.target.closest('.sr-item');
    if (b) go(b.dataset.key);
  });
  pane.addEventListener('keydown', e => {
    if (e.key === 'Escape') { e.preventDefault(); history.back(); return; }
    const items = [...bodyEl.querySelectorAll('.sr-item')];
    if (e.key === 'Enter' && e.target === input) {
      e.preventDefault();
      if (items.length) go(items[0].dataset.key);
    } else if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      const at = items.indexOf(document.activeElement);
      const next = e.key === 'ArrowDown' ? at + 1 : at - 1;   // from the input (-1): Down goes to the first result
      e.preventDefault();
      if (next < 0) input.focus();
      else if (next < items.length) items[next].focus();
    }
  });

  FK.search = { query, describe, go, label: key => { const d = describe(key); return d ? d.title : null; } };
  FK.on('pins', () => { if (!pane.hidden) render(); });
  FK.on('recent', () => { if (!pane.hidden && !tokens(input.value).length) render(); });
})();
