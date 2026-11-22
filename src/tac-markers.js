/* ---------- Markers on the map: kind icons, the marker sheet (new and existing), the list sheet, and drawing ----------
   The data lives in tac-data.js (FK.tac). Nothing is stored until the user presses Save. */
(() => {
  const FK = window.FK;
  const { $, toast, esc } = FK;

  /* ---------- Icons: 24 px line drawings in the map buttons' stroke style ---------- */
  const LINE = d => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${d}</svg>`;
  const PLACE = {
    point: '<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="3" fill="currentColor"/>',
    camp: '<path d="M2.5 20h19M4 20 13.5 3M20 20 10.5 3"/><path d="M9 20l3-5.5 3 5.5"/>',
    vehicle: '<path d="M5 16H2V6h11v10M13 9h4l4 4v3h-2M9 16h6"/><circle cx="7" cy="16.5" r="2"/><circle cx="17" cy="16.5" r="2"/>',
    water: '<path d="M12 3C9.5 7.5 6 10.8 6 15a6 6 0 0 0 12 0c0-4.2-3.5-7.5-6-12z"/>',
    cache: '<path d="M3 6h18v4H3zM5 10v10h14V10M10 14h4"/>',
    hazard: '<path d="M12 3 2 20h20z"/><path d="M12 9.5v4.5"/><circle cx="12" cy="17" r=".6" fill="currentColor"/>',
    rally: '<path d="M5 21V3M5 4h13l-3 4.5 3 4.5H5"/>',
    observe: '<circle cx="6.5" cy="15.5" r="4"/><circle cx="17.5" cy="15.5" r="4"/><path d="M10.5 15h3M4 12.5 6.5 5h3l.8 6.5M20 12.5 17.5 5h-3l-.8 6.5"/>',
    medical: '<rect x="2.5" y="2.5" width="19" height="19" rx="4.5"/><path d="M10 6h4v4h4v4h-4v4h-4v-4H6v-4h4z"/>'   // a badge, so the cross never reads as "add"
  };
  /* Affiliation frames (APP-6 / MIL-STD-2525: friend blue rectangle, hostile red diamond, neutral green square, unknown
     yellow quatrefoil). Shape carries the meaning, so they stay distinct where colour cannot: the red night theme and a
     colour-blind reader. The fill is the standard's light tint, outlined in near-black so it reads on topo and imagery. */
  const FRAME = {
    friend: ['#80E0FF', '<rect x="1.5" y="6" width="21" height="12" rx="1"'],   // 1.75 : 1, plainly a rectangle beside the neutral square
    hostile: ['#FF8080', '<path d="M12 2.5 21.5 12 12 21.5 2.5 12z"'],
    neutral: ['#AAFFAA', '<rect x="4" y="4" width="16" height="16"'],
    unknown: ['#FFFF80', '<path d="M8.5 8.5A4 4 0 1 1 15.5 8.5 4 4 0 1 1 15.5 15.5 4 4 0 1 1 8.5 15.5 4 4 0 1 1 8.5 8.5z"']
  };
  /* A light halo under the dark outline keeps the frame visible on dark imagery, including a stale one with no fill. */
  function icon(kind, o) {
    const f = FRAME[kind];
    if (!f) return LINE(PLACE[kind] || PLACE.point);
    const stale = !!(o && o.stale);
    return `<svg viewBox="0 0 24 24" aria-hidden="true">${f[1]} class="afh" fill="none" stroke="#FFFFFF" stroke-width="4.5" stroke-linejoin="round"/>` +
      `${f[1]} class="af${stale ? ' stale' : ''}" fill="${stale ? 'none' : f[0]}" stroke="#1A1A1A" stroke-width="2" stroke-linejoin="round"/></svg>`;
  }

  const KIND = id => FK.tac.KINDS.find(k => k.id === id) || FK.tac.KINDS[0];
  const isAffil = kind => KIND(kind).group === 'affil';
  const DAY = 24 * 3600 * 1000;
  const ageText = t => {
    if (t > Date.now()) return '';   // timed in the future (a phone with a wrong clock, a file): no age rather than a wrong one
    const m = Math.floor((Date.now() - t) / 60000);
    if (m < 60) return `${Math.max(1, m)} min ago`;
    if (m < 1440) return `${Math.floor(m / 60)} h ago`;
    const d = Math.floor(m / 1440);
    return `${d} ${d === 1 ? 'day' : 'days'} ago`;
  };
  const known = w => w.t > 0;
  const isStale = w => isAffil(w.kind) && known(w) && Date.now() - w.t > DAY;
  const hm = t => new Date(t).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
  const markedText = t => {
    const d = new Date(t), same = d.toDateString() === new Date().toDateString();
    const age = ageText(t);
    return `Marked ${same ? '' : d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) + ' '}${hm(t)}${age ? ', ' + age : ''}`;
  };
  const gridText = (lat, lon) => { const g = GEO.toMGRS(lat, lon); return g ? g.text : `${lat.toFixed(5)}, ${lon.toFixed(5)}`; };
  const relText = (lat, lon) => FK.relText(lat, lon, m => TGEOM.fmtDist(m, FK.tac.unit()));   // app.js: one rule for live and last fixes
  const targetId = () => { const t = FK.tac.target(); return t && t.type === 'marker' ? t.id : null; };

  /* ---------- Drawing on the map ---------- */
  function render() {
    const map = FK.leafletMap();
    if (!map || !map._fkWps) return;
    const g = map._fkWps; g.clearLayers();
    const tid = targetId();
    FK.tac.markers().forEach(w => {
      const stale = isStale(w);
      const cls = 'mk-pin' + (w.id === tid ? ' tgt' : '') + (stale ? ' stale' : '');
      const html = `<div class="${cls}" data-id="${esc(w.id)}" data-kind="${w.kind}"><i>${icon(w.kind, { stale })}</i><b>${esc(w.name)}</b></div>`;
      L.marker([w.lat, w.lon], { icon: L.divIcon({ className: 'mk-icon', iconSize: [30, 30], iconAnchor: [15, 15], html }), title: w.name,
        zIndexOffset: w.id === tid ? 500 : 0 }).on('click', () => { if (!FK.mapTools.mode()) edit(w.id); }).addTo(g);   // inert while a tool mode is on
    });
  }

  /* ---------- Marker sheet ---------- */
  const dlg = $('#dlgMarker'), nameEl = $('#mkName'), noteEl = $('#mkNote');
  let cur = null;   // { id (null for new), lat, lon, kind, typed (the name was edited by hand), t }
  const kindBtn = k => `<button type="button" class="mk-kind" data-kind="${k.id}" aria-pressed="false">${icon(k.id)}<span>${esc(k.label)}</span></button>`;
  $('#mkPlaces').innerHTML = FK.tac.KINDS.filter(k => k.group === 'place').map(kindBtn).join('');
  $('#mkAffil').innerHTML = FK.tac.KINDS.filter(k => k.group === 'affil').map(kindBtn).join('');

  function defaultName(kind) {
    const all = FK.tac.markers();
    if (!isAffil(kind)) return `WP ${all.length + 1}`;
    return `${KIND(kind).label} ${all.filter(w => w.kind === kind).length + 1}`;
  }
  function setKind(kind) {
    cur.kind = kind;
    dlg.querySelectorAll('.mk-kind').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.kind === kind)));
    if (!cur.id && !cur.typed) nameEl.value = defaultName(kind);
    renderAge();
  }
  function renderLeft() {
    const left = 500 - noteEl.value.length;
    $('#mkLeft').hidden = left >= 50;
    $('#mkLeft').textContent = `${left} ${left === 1 ? 'character' : 'characters'} left`;
  }
  function renderAge() {
    const show = !!cur.id && isAffil(cur.kind) && cur.t > 0;
    $('#mkAge').hidden = !show;
    $('#mkAge').textContent = show ? markedText(cur.t) : '';
  }
  function fill(o) {
    cur = o;
    $('#mkTitle').textContent = o.id ? 'Marker' : 'New marker';
    nameEl.value = o.name; noteEl.value = o.note;
    setKind(o.kind);
    renderLeft();
    $('#mkGrid').textContent = gridText(o.lat, o.lon);
    const rel = relText(o.lat, o.lon);
    $('#mkRel').hidden = !rel; $('#mkRel').textContent = rel;
    $('#mkDel').hidden = !o.id;
    $('#mkMove').hidden = !o.id;
    $('#mkGo').textContent = o.id && o.id === targetId() ? 'Stop' : 'Go to';
    dlg.querySelector('.mk-body').scrollTop = 0;
    opened = null;
    FK.sheet.open(dlg, { onClose: () => { cur = null; deleting = false; dlg.inert = false; opened = null; }, onOpen: () => { $('#mkTitle').focus(); snap(); },   // no keyboard popping up on a phone
      guard: { dirty: changed, title: 'Discard this marker?', text: 'The name, note and kind are not kept.' } });
  }
  /* What the sheet showed when it opened, so Back, Escape or a backdrop tap can ask before losing what was typed. */
  let opened = null;
  const snap = () => { if (cur) opened = { name: nameEl.value, note: noteEl.value, kind: cur.kind }; };
  const changed = () => !!cur && !!opened && !deleting && (nameEl.value !== opened.name || noteEl.value !== opened.note || cur.kind !== opened.kind);
  function create(lat, lon) {
    if (!Number.isFinite(lat) || !Number.isFinite(lon)) return;
    lon = ((lon + 540) % 360) - 180;
    const kind = 'point';   // every new marker starts as a Point: a kind carried over (a Friend after a Friend) was easy to miss
    fill({ id: null, lat, lon, kind, typed: false, t: 0, name: '', note: '' });
    nameEl.value = defaultName(kind);
  }
  function edit(id) {
    const w = FK.tac.markers().find(x => x.id === id);
    if (w) fill({ id, lat: w.lat, lon: w.lon, kind: w.kind, typed: true, t: w.t, name: w.name, note: w.note });
  }

  dlg.querySelector('.mk-kinds').addEventListener('click', e => { const b = e.target.closest('[data-kind]'); if (b && cur) setKind(b.dataset.kind); });
  nameEl.addEventListener('input', () => { if (cur) cur.typed = true; });
  noteEl.addEventListener('input', renderLeft);
  $('#mkGrid').addEventListener('click', async () => {
    const t = $('#mkGrid').textContent;
    try { await navigator.clipboard.writeText(t); toast('Copied ' + t); } catch { toast(t); }
  });
  /* Save what the sheet shows. Returns the marker's id, also when phone storage is full: tac-data keeps the marker for this
     session and shows the full-storage message itself, every time.
     With onlyIfChanged, an existing marker whose fields are unchanged is not written. */
  let deleting = false;   // Delete has been pressed: nothing else in the sheet may act
  const exists = id => FK.tac.markers().some(x => x.id === id);
  function commit(onlyIfChanged) {
    const name = nameEl.value.trim(), note = noteEl.value.slice(0, 500), kind = cur.kind;
    if (cur.id) {
      const w = FK.tac.markers().find(x => x.id === cur.id);
      const patch = { kind, note };
      if (name) patch.name = name;
      if (onlyIfChanged && w.kind === kind && w.note === note && (!name || name === w.name)) return cur.id;
      FK.tac.updateMarker(cur.id, patch);
      return cur.id;
    }
    const before = new Set(FK.tac.markers().map(x => x.id));
    const m = FK.tac.addMarker({ lat: cur.lat, lon: cur.lon, name: name || defaultName(kind), kind, note });
    if (m) { toast(`Added ${m.name}`); return m.id; }
    const kept = FK.tac.markers().find(x => !before.has(x.id));   // not saved, but on screen until the app closes
    return kept ? kept.id : null;
  }
  /* The marker was removed some other way while its sheet was open. */
  function gone() { FK.sheet.close(dlg); toast('That marker no longer exists.'); }
  const blocked = () => !cur || deleting;

  $('#mkForm').addEventListener('submit', e => {
    e.preventDefault();
    if (blocked()) return;
    if (cur.id && !exists(cur.id)) { gone(); return; }
    commit(false);
    FK.sheet.close(dlg);
  });
  $('#mkCancel').addEventListener('click', () => FK.sheet.close(dlg));
  /* Go to and Stop keep what was typed: they save first. If storage is full the target still holds for this session. */
  $('#mkGo').addEventListener('click', () => {
    if (blocked()) return;
    if (cur.id && !exists(cur.id)) { gone(); return; }
    const stop = !!cur.id && cur.id === targetId();
    const id = commit(true);
    if (stop) FK.tac.setTarget(null);
    else if (id) FK.tac.setTarget({ type: 'marker', id });
    FK.sheet.close(dlg);
  });
  /* Move saves what was typed, like Go to, then hands the marker to the map's move mode (tac-tools.js). */
  $('#mkMove').addEventListener('click', () => {
    if (blocked() || !cur.id) return;
    if (!exists(cur.id)) { gone(); return; }
    const id = commit(true);
    FK.sheet.close(dlg);
    FK.mapTools.moveMarker(id);   // its history entry waits for this sheet's step back
  });
  $('#mkDel').addEventListener('click', async () => {
    if (blocked() || !cur.id) return;
    const id = cur.id, w = FK.tac.markers().find(x => x.id === id);
    if (!w) { gone(); return; }
    deleting = true;
    const yes = await FK.sheet.confirm({ title: 'Delete the marker?', text: `Delete marker ${w.name}? This can’t be undone.`, ok: 'Delete marker', danger: true });
    if (!yes || !cur || cur.id !== id) { deleting = false; return; }
    FK.tac.removeMarker(id);
    dlg.inert = true;
    // The confirm's own step back is still on its way: close the marker sheet once it has landed.
    FK.sheet.afterStep(() => FK.sheet.close(dlg));
  });

  /* ---------- List sheet: markers and drawn shapes (tac-shapes.js) together ---------- */
  const ldlg = $('#dlgList');
  const SHAPE_CHIPS = [{ id: 'route', label: 'Routes' }, { id: 'area', label: 'Areas' }, { id: 'ring', label: 'Rings' }];
  let filter = 'all';
  /* Rows to list: { kind (a marker kind, or route/area/ring), t, at: [lat, lon] for distance, w (marker) or s (shape) }.
     With a fix, nearest first (a shape by its first point, a ring by its centre); otherwise newest first. */
  function sorted() {
    const f = FK.getFix();
    const all = FK.tac.markers().map(w => ({ kind: w.kind, t: w.t, at: [w.lat, w.lon], w }))
      .concat(FK.tac.shapes().map(s => ({ kind: s.type, t: s.t, at: s.pts[0], s })));
    const d = r => GEO.distance(f.lat, f.lon, r.at[0], r.at[1]);
    return f ? all.sort((a, b) => d(a) - d(b)) : all.sort((a, b) => b.t - a.t);
  }
  function renderList() {
    const body = ldlg.querySelector('.mk-body'), top = body.scrollTop, left = $('#lsChips').scrollLeft;
    fillList();
    body.scrollTop = top; $('#lsChips').scrollLeft = left;
  }
  function fillList() {
    const all = FK.tac.markers(), shapes = FK.tac.shapes();
    const chips = FK.tac.KINDS.filter(k => all.some(w => w.kind === k.id)).concat(SHAPE_CHIPS.filter(c => shapes.some(s => s.type === c.id)));
    if (filter !== 'all' && !chips.some(k => k.id === filter)) filter = 'all';
    const empty = !all.length && !shapes.length;
    $('#lsChips').hidden = empty;
    $('#lsChips').innerHTML = [{ id: 'all', label: 'All' }, ...chips].map(k =>
      `<button type="button" data-kind="${k.id}" aria-pressed="${k.id === filter}">${esc(k.label)}</button>`).join('');
    const rows = sorted().filter(r => filter === 'all' || r.kind === filter), tid = targetId(), t = FK.tac.target();
    const rtid = t && t.type === 'route' ? t.id : null;
    const ul = $('#lsList');
    if (empty) { ul.innerHTML = '<li class="mk-empty">No markers yet. Move the map so the crosshair is where you want one, then press Mark.</li>'; return; }
    ul.innerHTML = rows.map(r => {
      if (r.s) {
        const s = r.s, rel = relText(r.at[0], r.at[1]);
        const meta = [FK.shapes.summary(s), rel].filter(Boolean).map(esc).join('<br>');
        return `<li class="${s.id === rtid ? 'tgt' : ''}"><button type="button" data-shape="${esc(s.id)}">
          <i class="mk-ic sh-ic">${FK.shapes.glyph(s.type)}</i>
          <span><span class="mk-name">${esc(s.name)}</span>${s.id === rtid ? ' <span class="mk-tag">Walking</span>' : ''}<br><span class="hint">${meta}</span></span></button></li>`;
      }
      const w = r.w, rel = relText(w.lat, w.lon), age = isAffil(w.kind) && known(w) ? ageText(w.t) : '';
      const meta = [gridText(w.lat, w.lon), rel, age].filter(Boolean).map(esc).join('<br>');
      return `<li class="${w.id === tid ? 'tgt' : ''}"><button type="button" data-id="${esc(w.id)}">
        <i class="mk-ic${isStale(w) ? ' stale' : ''}">${icon(w.kind, { stale: isStale(w) })}</i>
        <span><span class="mk-name">${esc(w.name)}</span>${w.id === tid ? ' <span class="mk-tag">Going to</span>' : ''}<br><span class="hint">${meta}</span></span></button></li>`;
    }).join('');
  }
  $('#lsChips').addEventListener('click', e => { const b = e.target.closest('[data-kind]'); if (b) { filter = b.dataset.kind; renderList(); } });
  /* A row centres the map and opens its sheet; while a tool mode is on it only centres the map (a point can then be placed there). */
  $('#lsList').addEventListener('click', e => {
    const sb = e.target.closest('[data-shape]');
    if (sb) {
      const s = FK.tac.shapes().find(x => x.id === sb.dataset.shape);
      if (!s) return;
      FK.sheet.close(ldlg);
      if (FK.mapTools.mode()) { const a = FK.shapes.anchor(s); FK.mapShow(a[0], a[1]); return; }
      FK.shapes.fit(s.id);
      FK.mapTools.editShape(s.id);   // FK.sheet.open waits for the list's step back
      return;
    }
    const b = e.target.closest('[data-id]');
    if (!b) return;
    const w = FK.tac.markers().find(x => x.id === b.dataset.id);
    if (!w) return;
    FK.sheet.close(ldlg);
    FK.mapShow(w.lat, w.lon);
    if (!FK.mapTools.mode()) edit(w.id);   // FK.sheet.open waits for the list's step back
  });
  $('#lsClose').addEventListener('click', () => FK.sheet.close(ldlg));

  /* Open the list once the map screen is showing (callers may have just asked to navigate there). */
  function openList(tries = 60) {
    const ready = FK.tab() === 'tactical' && FK.view() === 'map' && FK.leafletMap() && !$('#view-map').hidden;
    if (!ready) { if (tries > 0) requestAnimationFrame(() => openList(tries - 1)); return; }
    filter = 'all';
    fillList();
    ldlg.querySelector('.mk-body').scrollTop = 0;
    FK.sheet.open(ldlg, { onOpen: () => $('#lsTitle').focus() });
  }
  $('#mList').addEventListener('click', () => openList());

  FK.on('wps', () => { render(); if (ldlg.open) renderList(); });
  FK.on('target', () => { render(); if (ldlg.open) renderList(); });
  FK.on('unit', () => { if (ldlg.open) renderList(); });
  FK.on('shapes', () => { if (ldlg.open) renderList(); });

  /* A new fix moves distances, bearings and the order: redraw an open list, at most every 2 s so a row isn't replaced under a finger. */
  let fixAt = 0, fixTimer = 0;
  FK.on('fix', () => {
    if (!ldlg.open || fixTimer) return;
    const wait = Math.max(0, fixAt + 2000 - Date.now());
    fixTimer = setTimeout(() => { fixTimer = 0; fixAt = Date.now(); if (ldlg.open) renderList(); }, wait);
  });

  /* Ages and the 24 h fade change with time alone: refresh once a minute while the map is on screen. */
  let tick = 0;
  function refresh() {
    render();
    if (ldlg.open) renderList();
    if (dlg.open && cur) {
      renderAge();
      const rel = relText(cur.lat, cur.lon);
      $('#mkRel').hidden = !rel; $('#mkRel').textContent = rel;
    }
  }
  function syncTimer() {
    const want = !document.hidden && FK.tab() === 'tactical' && FK.view() === 'map';
    if (want && !tick) tick = setInterval(refresh, 60000);
    else if (!want && tick) { clearInterval(tick); tick = 0; }
  }
  FK.on('shown', syncTimer);
  FK.on('fixlive', refresh);
  document.addEventListener('visibilitychange', () => { syncTimer(); if (tick) refresh(); });
  syncTimer();

  FK.markers = { icon, line: LINE, edit, create, openList, render, ageText, timerOn: () => !!tick };
})();
