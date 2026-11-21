/* ---------- Drawn shapes: routes, areas and range rings on the map, the shape sheet, and the Range ring sheet ----------
   The data lives in tac-data.js (FK.tac). Rings are drawn with TGEOM.ring, so a ring on screen matches the app's own distance
   maths. A shape is chosen by a tap on its line (an invisible wider twin, .shp-hit, so a fingertip finds it) or on its name
   label; fills never take taps. Markers sit in a pane above the shapes, so when both are under a tap the marker wins. */
(() => {
  const FK = window.FK;
  const { $, toast, esc } = FK;
  const fd = m => TGEOM.fmtDist(m, FK.tac.unit());
  const deg = b => Math.round(b) % 360;
  const TYPE = { route: 'Route', area: 'Area', ring: 'Ring' };
  const dist = (a, b) => GEO.distance(a[0], a[1], b[0], b[1]);

  const unwrapTo = (lon, ref) => { while (lon - ref > 180) lon -= 360; while (lon - ref < -180) lon += 360; return lon; };
  const unwrap = list => { const out = []; list.forEach((p, i) => out.push([p[0], i ? unwrapTo(p[1], out[i - 1][1]) : p[1]])); return out; };
  const closedLen = pts => TGEOM.pathLength(pts.concat([pts[0]]));
  /* The point halfway along a line (on the drawn, unwrapped points): where a route's name goes, once, clear of the markers
     that so often sit at its ends. */
  function midway(u) {
    const legs = u.slice(1).map((p, i) => GEO.distance(u[i][0], u[i][1], p[0], p[1]));
    let left = legs.reduce((a, b) => a + b, 0) / 2;
    for (let i = 0; i < legs.length; i++) {
      if (left <= legs[i] && legs[i] > 0) { const k = left / legs[i], a = u[i], b = u[i + 1]; return [a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k]; }
      left -= legs[i];
    }
    return u[u.length - 1];
  }
  /* Where a shape is, for distances and the list: a route's first point, an area's middle, a ring's centre. */
  function anchor(s) {
    if (s.type !== 'area') return s.pts[0];
    const u = unwrap(s.pts);
    return [u.reduce((a, p) => a + p[0], 0) / u.length, ((u.reduce((a, p) => a + p[1], 0) / u.length + 540) % 360) - 180];
  }
  const radii = s => s.r.map(fd).join(', ');
  function summary(s) {
    if (s.type === 'route') return fd(TGEOM.pathLength(s.pts));
    if (s.type === 'area') return TGEOM.fmtArea(TGEOM.areaM2(s.pts), FK.tac.unit());
    return radii(s);
  }
  const SVG = d => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${d}</svg>`;
  const GLYPH = {
    route: SVG('<circle cx="5" cy="19" r="2"/><circle cx="19" cy="5" r="2"/><path d="M7 18 12 9l3 4 3-6"/>'),
    area: SVG('<path d="M4 7 11 3l9 5-2 11-12 2z" fill="currentColor" fill-opacity=".15"/>'),
    ring: SVG('<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1" fill="currentColor"/>')
  };
  const routeTarget = () => { const t = FK.tac.target(); return t && t.type === 'route' ? t.id : null; };

  /* ---------- Drawing ----------
     Fills never take taps: a shape is chosen by its line (an invisible twin at least 24 px wide, .shp-hit) or its name label.
     All hit lines are drawn after every visible stroke and fill, the longest shape's first, so where lines cross under one
     tap the smaller shape wins whatever order the shapes were saved in. A label's tap box sits in a pane just under the lines
     (a 44 px label must not swallow taps meant for another shape's line) and its text in one above them; markers are above everything, so a marker still
     beats any shape. */
  let vis = null, hits = null;
  const lineLength = s => s.type === 'route' ? TGEOM.pathLength(s.pts) : s.type === 'area' ? closedLen(s.pts) : s.r.reduce((a, r) => a + 2 * Math.PI * r, 0);
  function render() {
    const map = FK.leafletMap();
    if (!map) return;
    if (!map.getPane('shpLabels')) map.createPane('shpLabels').style.zIndex = 390;   // label tap boxes: under the lines (overlayPane 400), so a line beats a label
    if (!map.getPane('shpText')) map.createPane('shpText').style.zIndex = 450;      // label text: above the lines, under the markers (600)
    if (!vis || vis._map !== map) { vis = L.layerGroup().addTo(map); hits = L.layerGroup().addTo(map); }
    vis.clearLayers(); hits.clearLayers();
    const tid = routeTarget(), all = FK.tac.shapes();
    all.forEach(s => draw(s, s.id === tid));
    const len = new Map(all.map(s => [s, lineLength(s)]));   // once per shape, not once per comparison
    all.slice().sort((a, b) => len.get(b) - len.get(a)).forEach(drawHits);
  }
  const tag = (l, s) => { const el = l.getElement && l.getElement(); if (el) el.setAttribute('data-id', s.id); return l; };
  const tapFor = s => () => { if (!FK.mapTools.mode()) edit(s.id); };
  const lineOpt = className => ({ className, interactive: false });
  const geom = s => {   // drawn lines, each a list of points: the route, the area's closed outline, each ring circle
    if (s.type === 'route') return [unwrap(s.pts)];
    if (s.type === 'area') { const u = unwrap(s.pts); return [u.concat([[u[0][0], unwrapTo(u[0][1], u[u.length - 1][1])]])]; }
    const c = s.pts[0];
    return s.r.map(r => unwrap(TGEOM.ring(c[0], c[1], r)).map(p => [p[0], unwrapTo(p[1], c[1])]));
  };
  function draw(s, isTarget) {
    /* A label is drawn twice: the text in a pane above the lines (never under a stroke, never taking a tap), and an
       invisible 44 px box of the same size in a pane under the lines that takes the tap. */
    const label = (ll, cls, text, interactive) => {
      const icon = c => L.divIcon({ className: 'shp-lab-icon', iconSize: [0, 0], html: `<span class="${c}" data-id="${esc(s.id)}">${esc(text)}</span>` });
      L.marker(ll, { pane: 'shpText', interactive: false, keyboard: false, icon: icon(cls + ' shp-text') }).addTo(vis);
      if (!interactive) return;
      L.marker(ll, { pane: 'shpLabels', interactive: true, keyboard: false, bubblingMouseEvents: false, icon: icon(cls) }).on('click', tapFor(s)).addTo(vis);
    };
    const g = geom(s);
    if (s.type === 'route') {
      tag(L.polyline(g[0], lineOpt('shp-route' + (isTarget ? ' tgt' : ''))).addTo(vis), s);
      tag(L.circleMarker(g[0][0], { radius: 5, ...lineOpt('shp-start') }).addTo(vis), s);
      label(midway(g[0]), 'shp-lab', s.name, true);
    } else if (s.type === 'area') {
      tag(L.polygon(unwrap(s.pts), lineOpt('shp-area')).addTo(vis), s);
      const a = anchor(s);
      label([a[0], unwrapTo(a[1], g[0][0][1])], 'shp-lab', s.name, true);
    } else {
      const c = s.pts[0];
      g.forEach((u, i) => {
        tag(L.polygon(u, lineOpt('shp-ring' + (i === g.length - 1 ? ' outer' : ''))).addTo(vis), s);
        const top = TGEOM.dest(c[0], c[1], 0, s.r[i]);
        label([top.lat, unwrapTo(top.lon, c[1])], 'shp-rlab', fd(s.r[i]), false);
      });
      label(c, 'shp-lab', s.name, true);
    }
  }
  function drawHits(s) {
    geom(s).forEach(u => tag(L.polyline(u, { className: 'shp-hit', interactive: true, bubblingMouseEvents: false }).on('click', tapFor(s)).addTo(hits), s));
  }
  /* The map's view of a shape: what the list does before opening its sheet. */
  function fit(id) {
    const s = FK.tac.shapes().find(x => x.id === id), map = FK.leafletMap();
    if (!s || !map) return;
    const pts = s.type === 'ring' ? TGEOM.ring(s.pts[0][0], s.pts[0][1], Math.max(...s.r), 36).map(p => [p[0], unwrapTo(p[1], s.pts[0][1])]) : unwrap(s.pts);
    const a = anchor(s);
    FK.mapShow(a[0], a[1]);   // follow off
    map.fitBounds(pts, { padding: [40, 40], maxZoom: 16, animate: false });
  }

  /* ---------- Shape sheet ---------- */
  const dlg = $('#dlgShape');
  let curId = null, deleting = false;
  const cur = () => FK.tac.shapes().find(x => x.id === curId);
  function fill() {
    const s = cur();
    if (!s) return;
    $('#shName').textContent = s.name;
    const n = s.type === 'ring' ? s.r.length : s.pts.length;
    $('#shType').textContent = s.type === 'ring' ? `Ring, ${n} ${n === 1 ? 'circle' : 'circles'}` : `${TYPE[s.type]}, ${n} points`;
    const info = $('#shInfo'), legs = $('#shLegs');
    if (s.type === 'route') info.textContent = `Length ${fd(TGEOM.pathLength(s.pts))}`;
    else if (s.type === 'area') info.innerHTML = `Perimeter ${esc(fd(closedLen(s.pts)))}<br>Area ${esc(TGEOM.fmtArea(TGEOM.areaM2(s.pts), FK.tac.unit()))}`;
    else info.textContent = `${s.r.length === 1 ? 'Radius' : 'Radii'} ${radii(s)}`;
    legs.innerHTML = s.type !== 'route' ? '' : s.pts.slice(1).map((p, i) => {
      const a = s.pts[i];
      return `<li><b>${i + 1} → ${i + 2}</b>&nbsp; ${esc(fd(dist(a, p)))} at ${deg(GEO.bearing(a[0], a[1], p[0], p[1]))}° true</li>`;
    }).join('');
    $('#shWalk').hidden = s.type !== 'route';
    $('#shWalk').textContent = routeTarget() === s.id ? 'Stop walking' : 'Walk this route';
  }
  function edit(id) {
    if (!FK.tac.shapes().some(x => x.id === id)) return;
    curId = id; deleting = false;
    fill();
    dlg.querySelector('.mk-body').scrollTop = 0;
    FK.sheet.open(dlg, { onClose: () => { curId = null; deleting = false; dlg.inert = false; }, onOpen: () => $('#shName').focus() });
  }
  const blocked = () => !curId || deleting || !cur();
  $('#shClose').addEventListener('click', () => FK.sheet.close(dlg));
  $('#shRename').addEventListener('click', async () => {
    if (blocked()) return;
    const s = cur(), id = s.id;
    const name = await FK.sheet.ask({ title: `Rename ${s.type}`, label: 'Name', value: s.name, ok: 'Save' });
    if (name && curId === id) FK.tac.updateShape(id, { name });   // kept for this session when storage is full; tac-data says so
  });
  $('#shDelete').addEventListener('click', async () => {
    if (blocked()) return;
    const s = cur(), id = s.id;
    deleting = true;
    const yes = await FK.sheet.confirm({ title: `Delete the ${s.type}?`, text: `Delete ${s.type} ${s.name}? This can’t be undone.`, ok: `Delete ${s.type}`, danger: true });
    if (!yes || curId !== id) { deleting = false; return; }
    FK.tac.removeShape(id);
    dlg.inert = true;
    FK.sheet.afterStep(() => FK.sheet.close(dlg));   // after the confirm's own step back
  });
  $('#shWalk').addEventListener('click', () => {
    if (blocked()) return;
    const s = cur();
    if (s.type !== 'route') return;
    if (routeTarget() === s.id) { FK.tac.setTarget(null); toast(`Stopped walking ${s.name}`); }
    else if (FK.tac.setTarget({ type: 'route', id: s.id, i: 0 })) toast(`Walking ${s.name}. Open Position for the arrow.`);
    FK.sheet.close(dlg);
  });

  /* ---------- Range ring sheet ---------- */
  const rdlg = $('#dlgRing'), RIDS = ['#rgR1', '#rgR2', '#rgR3'];
  const YD = 0.9144, MAX_R = 50000;
  function openRing() {
    const map = FK.leafletMap();
    if (!map) return;
    if (FK.tac.shapes().length >= FK.tac.MAX_SHAPES) { toast(FK.mapTools.LIMIT_MSG); return; }
    const f = FK.getFix(), all = FK.tac.markers();
    const d = w => GEO.distance(f.lat, f.lon, w.lat, w.lon);
    const ms = f ? all.sort((a, b) => d(a) - d(b)) : all.sort((a, b) => b.t - a.t);
    $('#rgCentre').innerHTML = '<option value="">The crosshair</option>' +
      ms.map(w => `<option value="${esc(w.id)}">${esc(w.name)}${f ? ` (${esc(fd(d(w)))} ${FK.fixLive() ? 'away' : 'from last position'})` : ''}</option>`).join('');
    const u = FK.tac.unit() === 'us' ? 'yd' : 'm';
    rdlg.querySelectorAll('.rg-u').forEach(e => { e.textContent = u; });
    RIDS.forEach(s => { $(s).value = ''; });
    $('#rgMsg').textContent = '';
    FK.sheet.open(rdlg, { onOpen: () => $('#rgTitle').focus(),
      guard: { dirty: () => RIDS.some(s => $(s).value.trim() !== ''), title: 'Discard this ring?', text: 'The radii you typed are not kept.' } });
  }
  $('#rgForm').addEventListener('submit', e => {
    e.preventDefault();
    const msg = $('#rgMsg');
    const typed = RIDS.map(s => $(s).value.trim()).filter(v => v !== '');
    if (!typed.length) { msg.textContent = 'Enter at least one radius'; return; }
    const nums = typed.map(Number);
    if (nums.some(n => !Number.isFinite(n) || n <= 0)) { msg.textContent = 'A radius must be more than zero'; return; }
    const r = nums.map(n => FK.tac.unit() === 'us' ? n * YD : n).sort((a, b) => a - b);
    if (r.some(x => x > MAX_R)) { msg.textContent = FK.tac.unit() === 'us' ? 'Rings can be up to 54,680 yd (31 mi)' : 'Rings can be up to 50 km'; return; }
    const id = $('#rgCentre').value, w = id && FK.tac.markers().find(x => x.id === id);
    const c = w ? [w.lat, w.lon] : (ll => [ll.lat, ll.lng])(FK.leafletMap().getCenter().wrap());
    const before = new Set(FK.tac.shapes().map(x => x.id));
    const s = FK.tac.addShape({ type: 'ring', name: FK.mapTools.freeName('ring'), pts: [c], r });
    if (s === 'limit') { msg.textContent = FK.mapTools.LIMIT_MSG; return; }
    const kept = s || FK.tac.shapes().find(x => !before.has(x.id));   // not saved, but on screen this session
    FK.sheet.close(rdlg);
    if (s) toast(`Added ${s.name}`);
    if (kept) FK.sheet.afterStep(() => fit(kept.id));
  });
  RIDS.forEach(s => $(s).addEventListener('input', () => { $('#rgMsg').textContent = ''; }));
  $('#rgCancel').addEventListener('click', () => FK.sheet.close(rdlg));

  /* ---------- Wiring ---------- */
  FK.on('shapes', () => {
    render();
    if (dlg.open && curId) { if (cur()) fill(); else if (!deleting) { FK.sheet.close(dlg); toast('That shape no longer exists.'); } }
  });
  FK.on('target', () => { render(); if (dlg.open && curId) fill(); });
  FK.on('unit', () => { render(); if (dlg.open && curId) fill(); });
  FK.on('shown', s => { if (s.tab === 'tactical' && s.view === 'map') requestAnimationFrame(() => { if (!vis || vis._map !== FK.leafletMap()) render(); }); });
  if (FK.tab() === 'tactical' && FK.view() === 'map') requestAnimationFrame(() => requestAnimationFrame(render));

  FK.shapes = { render, edit, fit, openRing, summary, anchor, glyph: type => GLYPH[type] || '' };
  FK.mapTools.editShape = edit;
})();
