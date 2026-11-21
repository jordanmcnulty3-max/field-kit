/* ---------- Tactical map tools: the scale bar, the Tools sheet, the tool modes (Measure, Route, Area, Move a marker) and Go to grid ----------
   The map is crosshair-driven: a mode places points where the crosshair is when the user presses Add point. A mode is not a
   dialog (the map must stay pannable), so it holds one history entry through FK.sheet.layer: Back leaves it (asking first when
   a route or area has points that would be lost), and so does any navigation. Drawn shapes, the shape sheet and the Range ring
   sheet are in tac-shapes.js. */
(() => {
  const FK = window.FK;
  const { $, toast } = FK;

  /* ---------- Scale bar ---------- */
  const MAX_PX = 120;
  let hooked = null;

  /* Metres in one pixel at the map centre, from Leaflet's own projection. */
  function mPerPx(map) {
    const c = map.getSize().divideBy(2);
    return map.distance(map.containerPointToLatLng(c), map.containerPointToLatLng(c.add([100, 0]))) / 100;
  }

  function drawScale() {
    const map = FK.leafletMap(), el = $('#mapScale');
    if (!map || !el || !map.getSize().x) return;
    const mp = mPerPx(map);
    if (!(mp > 0)) return;
    const s = TGEOM.scale(mp, MAX_PX, FK.tac.unit());
    el.querySelector('.lab').textContent = s.label;
    el.querySelector('.line').style.width = s.px.toFixed(2) + 'px';
  }

  function hook() {
    const map = FK.leafletMap();
    if (!map) return;
    if (hooked !== map) { hooked = map; map.on('zoomend moveend', drawScale); map.on('move', onMove); map.on('moveend', announce); }
    drawScale();
  }

  FK.on('shown', s => { if (s.tab === 'tactical' && s.view === 'map') requestAnimationFrame(hook); });
  FK.on('unit', () => { drawScale(); if (mode) paint(); });
  if (FK.tab() === 'tactical' && FK.view() === 'map') requestAnimationFrame(hook);   // the map is made a frame after the first show

  /* ---------- Shared wording ---------- */
  const LIMIT_MSG = 'You have 100 shapes, the most the app can hold. Delete one first.';
  const fd = m => TGEOM.fmtDist(m, FK.tac.unit());
  const deg = b => Math.round(b) % 360;
  const dist = (a, b) => GEO.distance(a[0], a[1], b[0], b[1]);
  const brg = (a, b) => GEO.bearing(a[0], a[1], b[0], b[1]);
  /* The lowest free default name: Route 1, Area 2, ... (the same rule tac-data uses when a name is missing). */
  function freeName(type) {
    const word = { route: 'Route', area: 'Area', ring: 'Ring' }[type], names = new Set(FK.tac.shapes().map(s => s.name));
    let n = 1;
    while (names.has(`${word} ${n}`)) n++;
    return `${word} ${n}`;
  }

  /* ---------- Tools sheet ----------
     Rows are { id, label, hint, run, icon? }. A later file adds its own with FK.mapTools.addRow({ id, label, hint, run }):
     the row is appended (in the order added) and run() is called once the Tools sheet has closed. A row whose id is already
     listed, or that has no run function, is ignored, so a tool without a handler never shows. A row with now: true runs at once,
     inside the tap, as the sheet starts closing (for a file picker, which a browser opens only from a user's tap). */
  const tdlg = $('#dlgTools');
  const rows = [];
  const SVG = d => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${d}</svg>`;
  function addRow(r) {
    if (!r || typeof r.id !== 'string' || typeof r.run !== 'function' || rows.some(x => x.id === r.id)) return false;
    rows.push({ id: r.id, label: String(r.label || r.id), hint: String(r.hint || ''), run: r.run, icon: r.icon || '', now: !!r.now });
    if (tdlg.open) fillRows();
    return true;
  }
  function fillRows() {
    $('#tlList').innerHTML = rows.map(r => `<li><button type="button" data-tool="${FK.esc(r.id)}">${r.icon || SVG('<circle cx="12" cy="12" r="3"/>')}
      <span>${FK.esc(r.label)}<span class="hint">${FK.esc(r.hint)}</span></span></button></li>`).join('');
  }
  function open() {
    fillRows();
    FK.sheet.open(tdlg, { onOpen: () => $('#tlTitle').focus() });
  }
  $('#tlList').addEventListener('click', e => {
    const b = e.target.closest('[data-tool]'), r = b && rows.find(x => x.id === b.dataset.tool);
    if (!r) return;
    FK.sheet.close(tdlg);
    if (r.now) { r.run(); return; }      // still inside the tap (a file picker opens only from one)
    FK.sheet.afterStep(() => r.run());   // a sheet the row opens, or a mode's history entry, comes after the Tools sheet's step back
  });
  $('#tlClose').addEventListener('click', () => FK.sheet.close(tdlg));
  $('#mTools').addEventListener('click', open);

  /* ---------- Tool modes ---------- */
  const MODES = ['measure', 'route', 'area', 'move'];
  const WORD = { measure: 'measurement', route: 'route', area: 'area', move: 'move' };
  let mode = null, pts = [], layer = null, moveId = null, draft = null, band = null, closer = null, from = null;

  const map = () => FK.leafletMap();
  const crosshair = () => { const c = map().getCenter().wrap(); return [c.lat, c.lng]; };
  /* Leaflet draws longitudes as given: across the date line, unwrap each point against the one before so lines take the short way. */
  const unwrapTo = (lon, ref) => { while (lon - ref > 180) lon -= 360; while (lon - ref < -180) lon += 360; return lon; };
  const unwrap = list => { const out = []; list.forEach((p, i) => out.push([p[0], i ? unwrapTo(p[1], out[i - 1][1]) : p[1]])); return out; };
  const live = () => { const c = map().getCenter(); return [c.lat, c.lng]; };   // the crosshair as drawn (not wrapped)

  function start(m, opts) {
    if (!MODES.includes(m) || !map()) return false;
    if (mode) { toast(`Finish or cancel the ${WORD[mode]} first`); return false; }
    if ((m === 'route' || m === 'area') && FK.tac.shapes().length >= FK.tac.MAX_SHAPES) { toast(LIMIT_MSG); return false; }
    mode = m; pts = []; moveId = m === 'move' ? opts && opts.id : null;
    layer = FK.sheet.layer('tool', { onBack, onEnd: finish });
    draft = L.layerGroup().addTo(map());
    const bar = $('#toolBar');
    $('#tbAdd').hidden = m === 'move';
    $('#tbUndo').hidden = m === 'move';
    $('#tbClear').hidden = m !== 'measure';   // a measurement is thrown away freely: start again from the crosshair
    $('#tbPlace').hidden = m !== 'move';
    $('#tbSaveRoute').hidden = m !== 'measure';
    $('#tbDone').hidden = m === 'move';
    $('#tbCancel').hidden = m === 'measure';
    bar.hidden = false;
    $('#mMark').hidden = true;
    setRoom(true);
    if (m === 'move') {
      const w = FK.tac.markers().find(x => x.id === moveId);
      from = w ? [w.lat, w.lon] : null;
    }
    draw();
    announce();
    $(m === 'move' ? '#tbPlace' : '#tbAdd').focus();
    return true;
  }

  /* End the mode and step back off its history entry. Nothing is stored here: callers store first. */
  function leave() {
    const l = layer;
    finish();
    if (l) l.close();
  }
  /* The mode's state and its bar, without touching history (Back and navigation already moved off the entry).
     A navigation (a tab, a screen, Search: why 'nav') keeps an unfinished route or area in memory; it comes back, with its
     points and a fresh history entry, the next time the map shows (resume). A reload loses it. */
  let kept = null;   // { mode, pts } of a route or area left by a navigation
  function finish(why) {
    if (!mode) return;
    kept = why === 'nav' && (mode === 'route' || mode === 'area') && pts.length ? { mode, pts: pts.slice() } : null;
    mode = null; pts = []; moveId = null; from = null; layer = null;
    if (draft) { draft.remove(); draft = band = closer = null; }
    $('#toolBar').hidden = true;
    $('#mMark').hidden = false;
    setRoom(false);
    $('#mTools').focus();
  }
  /* While a mode is on the Map / Position / Ballistics switch is hidden (Back or the tab bar still leave), so the map keeps
     at least 300 px between the top of the screen and the mode bar on a 360 x 640 phone. The centre stays where it was. */
  function setRoom(on) {
    document.body.classList.toggle('maptool', on);
    FK.map.resize();
  }
  const unsaved = () => (mode === 'route' || mode === 'area') && pts.length >= 2;
  function askDiscard() {
    const kind = mode;
    FK.sheet.confirm({ title: `Discard this ${kind}?`, text: `The ${pts.length} points placed are not kept.`, ok: 'Discard', cancel: 'Keep editing', danger: true })
      .then(yes => { if (yes && mode === kind) leave(); });
  }
  /* Back off the mode's entry: stay and ask while a route or area has points to lose; otherwise the mode ends (finish). */
  function onBack() { return unsaved() ? askDiscard : false; }

  /* ---------- Drawing the draft: placed points as dots, placed legs solid, the leg to the crosshair dashed ---------- */
  function draw() {
    if (!draft) return;
    draft.clearLayers(); band = closer = null;
    const c = live();
    if (mode === 'move') {
      if (from) band = L.polyline([from, [c[0], unwrapTo(c[1], from[1])]], { className: 'tool-move', interactive: false }).addTo(draft);
      paint();
      return;
    }
    const u = unwrap(pts);
    if (u.length > 1) L.polyline(u, { className: 'tool-done', interactive: false }).addTo(draft);
    u.forEach(p => L.circleMarker(p, { radius: 5, className: 'tool-dot', interactive: false }).addTo(draft));
    if (u.length) band = L.polyline([], { className: 'tool-band', interactive: false }).addTo(draft);
    if (mode === 'area' && u.length >= 2) closer = L.polyline([], { className: 'tool-close', interactive: false }).addTo(draft);
    paint();
  }
  /* What follows the crosshair: the dashed legs and the reading. Runs on every Leaflet move. */
  function paint() {
    if (!mode || !map()) return;
    const c = live();
    if (mode === 'move') { if (band && from) band.setLatLngs([from, [c[0], unwrapTo(c[1], from[1])]]); }
    else {
      const u = unwrap(pts), last = u[u.length - 1];
      const cc = last ? [c[0], unwrapTo(c[1], last[1])] : c;
      if (band) band.setLatLngs([last, cc]);
      if (closer) closer.setLatLngs([cc, [u[0][0], unwrapTo(u[0][1], cc[1])]]);
    }
    $('#tbRead').textContent = reading();
    $('#tbUndo').disabled = !pts.length;
    $('#tbClear').disabled = !pts.length;
  }
  /* The visible reading follows every move; the screen-reader copy (#tbLive, aria-live) only when the map stops and after
     Add point or Undo, so a pan is not read out sixty times a second. */
  function announce() { if (mode) $('#tbLive').textContent = reading(); }
  function onMove() { if (mode) paint(); }

  function reading() {
    if (mode === 'move') return 'Move the map until the crosshair is on the new spot';
    if (!pts.length) return 'Move the map so the crosshair is on the first point.';
    const c = crosshair(), last = pts[pts.length - 1];
    let leg = dist(last, c), b = brg(last, c);
    if (pts.length === 1) return `${fd(leg)} at ${deg(b)}° true`;
    const placed = TGEOM.pathLength(pts);
    let total = placed + leg;
    // The crosshair still on the last point (just added): the leg worth reading is the last one placed.
    if (leg < 1) { const p = pts[pts.length - 2]; leg = dist(p, last); b = brg(p, last); total = placed; }
    // An area's outline closes: its figure is the perimeter, with the side from the crosshair (or the last point) back to the first.
    if (mode === 'area') return `Leg ${fd(leg)} at ${deg(b)}° true. Perimeter ${fd(total + dist(total === placed ? last : c, pts[0]))}.` +
      (pts.length >= 3 ? ` Area ${TGEOM.fmtArea(TGEOM.areaM2(pts), FK.tac.unit())}` : '');
    let t = `Leg ${fd(leg)} at ${deg(b)}° true. Total ${fd(total)}.`;
    return t;
  }

  /* ---------- The bar's buttons ---------- */
  $('#tbAdd').addEventListener('click', () => {
    if (!mode || mode === 'move' || asking) return;
    const c = crosshair(), last = pts[pts.length - 1];
    if (pts.length >= FK.tac.MAX_PTS) { toast(`That's the most points one ${mode === 'area' ? 'area' : 'route'} can hold (${FK.tac.MAX_PTS})`); return; }
    if (last && dist(last, c) < 1) { toast('That point is already placed'); return; }
    pts.push(c);
    draw();
    announce();
  });
  $('#tbUndo').addEventListener('click', () => { if (mode && pts.length && !asking) { pts.pop(); draw(); announce(); } });
  $('#tbClear').addEventListener('click', () => { if (mode === 'measure' && pts.length && !asking) { pts = []; draw(); announce(); } });
  $('#tbCancel').addEventListener('click', () => {
    if (!mode || asking) return;
    if (unsaved()) askDiscard(); else leave();
  });
  $('#tbDone').addEventListener('click', () => {
    if (!mode || asking) return;
    if (mode === 'measure') { leave(); return; }
    save(mode);
  });
  $('#tbSaveRoute').addEventListener('click', () => { if (mode === 'measure' && !asking) save('route'); });
  $('#tbPlace').addEventListener('click', () => {
    if (mode !== 'move') return;
    const id = moveId, w = FK.tac.markers().find(x => x.id === id), c = crosshair();
    if (w) {
      // A failed save still moves the marker for this session; tac-data shows the full-storage message itself.
      if (FK.tac.updateMarker(id, { lat: c[0], lon: c[1], alt: null })) toast(`Moved ${w.name}`);
    }
    leave();
  });

  /* Done (Route, Area) and Save as route (Measure): name it, then store it. Cancel on the name sheet goes back to the mode with
     every point. */
  let asking = false;
  function save(type) {
    const min = type === 'area' ? 3 : 2;
    if (pts.length < min) { toast(type === 'area' ? 'An area needs at least three points' : 'A route needs at least two points'); return; }
    const was = mode, keep = pts.slice();
    asking = true;
    FK.sheet.ask({ title: `Name this ${type}`, label: 'Name', value: freeName(type), ok: 'Save' }).then(name => {
      asking = false;
      if (!name || mode !== was) return;
      const s = FK.tac.addShape({ type, name, pts: keep });
      if (s === 'limit') { toast(LIMIT_MSG); return; }
      if (s) toast(`Saved ${s.name}`);   // when storage is full tac-data has said so and the shape stays on screen this session
      leave();
    });
  }

  function moveMarker(id) {
    const w = FK.tac.markers().find(x => x.id === id);
    if (!w || !map()) return false;
    if (mode) { toast(`Finish or cancel the ${WORD[mode]} first`); return false; }
    FK.mapShow(w.lat, w.lon);
    return start('move', { id });
  }

  /* A restore replaces everything and reloads: leave the mode with nothing stored. */
  FK.on('restoring', () => { kept = null; if (mode) leave(); });

  /* Bring a kept route or area back once the map is on screen again. The router reports 'shown' before 'route' (which ends
     any layer), and the map is made a frame after 'shown', so wait two frames; Search closing changes no route at all. */
  function resume() {
    if (!kept || mode || !map() || FK.tab() !== 'tactical' || FK.view() !== 'map' || FK.route.isSearch()) return;
    if (FK.sheet.top()) return;   // a sheet (a Search result's list or Saved maps) is open: wait until it closes ('sheetsClosed')
    const k = kept;
    kept = null;
    if (!start(k.mode)) return;
    pts = k.pts;
    draw(); announce();
    toast(`Your unfinished ${k.mode} is still here`);
  }
  const resumeSoon = () => requestAnimationFrame(() => requestAnimationFrame(resume));
  FK.on('shown', s => { if (s.tab === 'tactical' && s.view === 'map') resumeSoon(); });
  FK.on('search', e => { if (e && !e.open) resumeSoon(); });
  /* 'sheetsClosed' is emitted before the sheet's step back is queued, so wait a microtask: afterStep then really runs after
     that step lands, and a sheet opened straight after the close (a list row) is seen by resume(). */
  FK.on('sheetsClosed', () => { if (kept) queueMicrotask(() => FK.sheet.afterStep(resumeSoon)); });

  /* ---------- Go to grid ---------- */
  const gdlg = $('#dlgGoto');
  function openGoto() {
    $('#gtInput').value = ''; $('#gtMsg').textContent = '';
    FK.sheet.open(gdlg, { onOpen: () => $('#gtInput').focus() });
  }
  $('#gtForm').addEventListener('submit', e => {
    e.preventDefault();
    const p = GEO.parseAny($('#gtInput').value);
    if (!p) { $('#gtMsg').textContent = FK.GRID_HELP; return; }
    FK.sheet.close(gdlg);
    FK.sheet.afterStep(() => goTo(p.lat, p.lon));
  });
  $('#gtInput').addEventListener('input', () => { $('#gtMsg').textContent = ''; });
  $('#gtCancel').addEventListener('click', () => FK.sheet.close(gdlg));
  /* The jump puts the crosshair on the place: the map's own bar then shows its grid and Mark, so there is one panel, not two. */
  function goTo(lat, lon) {
    if (!map()) return;
    FK.mapShow(lat, lon);   // follow off, zoom at least 15
  }

  /* ---------- Rows of this file. Range ring is tac-shapes.js; Import and Export are tac-io.js; QR rows are added by their own file. ---------- */
  addRow({ id: 'measure', label: 'Measure', hint: 'Distance and bearing between points', run: () => start('measure'),
    icon: SVG('<path d="M3 17 17 3l4 4L7 21z"/><path d="m7 13 2 2M10 10l2 2M13 7l2 2"/>') });
  addRow({ id: 'route', label: 'Route', hint: 'Points in order, saved with a name', run: () => start('route'),
    icon: SVG('<circle cx="5" cy="19" r="2"/><circle cx="19" cy="5" r="2"/><path d="M7 19h6a3 3 0 0 0 0-6h-2a3 3 0 0 1 0-6h6"/>') });
  addRow({ id: 'area', label: 'Area', hint: 'An outline and its size', run: () => start('area'),
    icon: SVG('<path d="M4 7 11 3l9 5-2 11-12 2z"/>') });
  addRow({ id: 'ring', label: 'Range ring', hint: 'Up to three circles around one point', run: () => FK.shapes.openRing(),
    icon: SVG('<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1" fill="currentColor"/>') });
  addRow({ id: 'goto', label: 'Go to grid', hint: 'Centre the map on a grid or coordinates', run: openGoto,
    icon: SVG('<path d="M12 22s7-6.5 7-12a7 7 0 0 0-14 0c0 5.5 7 12 7 12z"/><circle cx="12" cy="10" r="2.5"/>') });
  addRow({ id: 'track', label: 'Track recording', hint: 'Record where you go', run: () => FK.map.openTrack(),
    icon: SVG('<path d="M4 19c3 0 3-6 7-6s3 4 6 4"/><circle cx="19" cy="6" r="3"/><circle cx="4" cy="19" r="1.5" fill="currentColor"/>') });
  addRow({ id: 'save', label: 'Save map for offline', hint: 'Keep the map on screen for use without signal', run: () => FK.map.openSave(),
    icon: SVG('<path d="M12 3v12"/><path d="m7 10 5 5 5-5"/><path d="M4 20h16"/>') });

  FK.mapTools = {
    open, addRow, start, moveMarker, LIMIT_MSG, freeName,
    mode: () => mode,
    points: () => pts.map(p => p.slice()),
    cancel: () => { if (mode) leave(); }
    // editShape is added by tac-shapes.js
  };
})();
