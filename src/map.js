/* ---------- Map: offline topo, tracks, saved maps (markers are drawn by tac-markers.js) ---------- */
(() => {
  const FK = window.FK;
  const { $, store, toast, esc, fin, okId, list, okLatLon } = FK;
  const TILE_CACHE = 'fk-tiles';
  const USGS = 'https://basemap.nationalmap.gov/arcgis/rest/services/';
  const LAYERS = {
    topo: { name: 'USGS Topo', note: 'US and territories. Saves for offline.',
      url: USGS + 'USGSTopo/MapServer/tile/{z}/{y}/{x}', maxNative: 16, offline: true, kb: 20,
      attr: '<a href="https://www.usgs.gov/programs/national-geospatial-program/national-map">USGS The National Map</a>' },
    sat: { name: 'USGS Imagery', note: 'US satellite photos, no contours or names. Saves for offline.',
      url: USGS + 'USGSImageryOnly/MapServer/tile/{z}/{y}/{x}', maxNative: 16, offline: true, kb: 45,
      attr: '<a href="https://www.usgs.gov/programs/national-geospatial-program/national-map">USGS The National Map</a>' },
    otm: { name: 'OpenTopoMap', note: 'Worldwide, online only. Its terms don’t allow bulk downloads.',
      url: 'https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', subdomains: 'abc', maxNative: 17, offline: false, kb: 30,
      attr: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, SRTM | © <a href="https://opentopomap.org">OpenTopoMap</a> (CC-BY-SA)' },
    /* USGS retired this service on 2026-11-16. The entry stays so that areas saved before then keep their
       tiles and their place in the list; it is offered only while such an area exists, and never for saving. */
    imagery: { name: 'USGS Imagery + Topo (retired)', note: 'USGS switched this map off on November 16, 2026. Only maps you saved before then still show.',
      url: USGS + 'USGSImageryTopo/MapServer/tile/{z}/{y}/{x}', maxNative: 16, offline: false, retired: true, kb: 45,
      attr: '<a href="https://www.usgs.gov/programs/national-geospatial-program/national-map">USGS The National Map</a>' }
  };

  let map = null, base = null, layerId = 'topo';
  let me = null, acc = null, tgtLine = null, trackLine = null;
  const areaGroup = () => map._fkAreas;
  let follow = store.get('mapFollow', true), zoomedToFix = false;
  let areas = list('areas', a => okId(a.id) && LAYERS[a.layer] && ['s', 'w', 'n', 'e', 'zMin', 'zMax'].every(k => fin(a[k])))
    .map(a => ({ ...a, name: String(a.name ?? 'Saved map'), tiles: fin(a.tiles) ? a.tiles : 0, bytes: fin(a.bytes) ? a.bytes : 0 }));
  const offered = id => !!LAYERS[id] && (!LAYERS[id].retired || areas.some(a => a.layer === id));
  {
    // A phone left on the retired satellite map with nothing saved from it moves to the satellite map that remains.
    const want = store.get('mapLayer', 'topo');
    layerId = offered(want) ? want : LAYERS[want] && LAYERS[want].retired ? 'sat' : 'topo';
  }
  let track = store.get('track', []);
  track = Array.isArray(track) ? track.filter(p => Array.isArray(p) && okLatLon(p[0], p[1]) && fin(p[3])) : [];
  let recording = store.get('recording', false) === true;
  FK.isRecording = () => recording;
  FK.leafletMap = () => map;

  /* ---------- Sizing ---------- */
  function sizeMap() {
    const wrap = $('#mapWrap');
    if (!wrap || $('#view-map').hidden) return;
    const top = wrap.getBoundingClientRect().top;
    const tb = $('.tabbar').offsetHeight;
    wrap.style.height = Math.max(260, window.innerHeight - top - tb) + 'px';
    if (map) map.invalidateSize();
  }
  addEventListener('resize', sizeMap);

  /* ---------- Init ---------- */
  const visible = () => !!map && !$('#view-map').hidden && FK.tab() === 'tactical';
  const savedView = () => { const v = store.get('mapView', null); return v && okLatLon(v.lat, v.lon) && fin(v.z) ? v : null; };
  function init() {
    if (map) {
      // Re-show: read the last view first (the resize below reports a move, and its moveend would store the shifted centre
      // over it: each Map -> Position -> Map moved the map), resize, then restore the view exactly.
      const v = savedView(), f = FK.getFix();
      const wrap = $('#mapWrap'), top = wrap.getBoundingClientRect().top;
      wrap.style.height = Math.max(260, window.innerHeight - top - $('.tabbar').offsetHeight) + 'px';
      map.invalidateSize({ pan: false });
      if (follow && f) map.setView([f.lat, f.lon], map.getZoom(), { animate: false });
      else if (v) map.setView([v.lat, v.lon], v.z, { animate: false, reset: true });   // reset: a pan would round to whole pixels
      FK.markers.render(); FK.team.render(); renderTarget(); renderMe(); renderCenter();
      return;
    }
    if (!window.L) { $('#mapWrap').innerHTML = '<p class="hint" style="padding:16px">The map library didn’t load. Reload the app while online.</p>'; return; }
    sizeMap();
    const v = savedView(), f = FK.getFix();
    map = L.map('map', { zoomControl: false, maxZoom: 18, minZoom: 3, worldCopyJump: true })
      .setView(v ? [v.lat, v.lon] : f ? [f.lat, f.lon] : [39.5, -98.35], v ? v.z : f ? 14 : 4);
    L.control.zoom({ position: 'topleft' }).addTo(map);
    map.attributionControl.setPrefix(false);
    map._fkAreas = L.layerGroup().addTo(map);
    map._fkTeam = L.layerGroup().addTo(map);   // teammates (tac-team.js): before the markers' group, and their pins sit lower
    map._fkWps = L.layerGroup().addTo(map);
    trackLine = L.polyline([], { className: 'trk', interactive: false }).addTo(map);
    tgtLine = L.polyline([], { className: 'tgt-line', interactive: false }).addTo(map);
    setBase(layerId);

    map.on('move', renderCenter);
    map.on('moveend', () => {
      if (!visible()) return;
      const c = map.getCenter();
      store.set('mapView', { lat: c.lat, lon: c.lng, z: map.getZoom() });
      renderCenter();
    });
    map.on('dragstart', () => setFollow(false));
    map.on('contextmenu', e => {   // press and hold; does nothing while a tool mode is on
      if (FK.mapTools && FK.mapTools.mode()) return;
      const ll = e.latlng.wrap(); FK.markers.create(ll.lat, ll.lng);
    });

    renderAreas(); FK.markers.render(); FK.team.render(); renderTarget(); renderTrack(); renderMe(); renderCenter(); setFollow(follow);
  }

  /* Tile layer that, when a tile is missing (e.g. offline past the saved zoom), scales up the
     nearest saved lower-zoom tile instead of leaving a blank square. */
  const FallbackLayer = L.TileLayer.extend({
    createTile(coords, done) {
      const tile = L.TileLayer.prototype.createTile.call(this, coords, done);
      tile._fk = { x: coords.x, y: coords.y, z: this._getZoomForUrl(), depth: 0 };
      return tile;
    },
    _tileOnError(done, tile, e) {
      const f = tile._fk;
      if (!f || f.depth >= 6 || f.z - f.depth <= 0) return L.TileLayer.prototype._tileOnError.call(this, done, tile, e);
      f.depth++;
      const k = 2 ** f.depth, px = Math.floor(f.x / k), py = Math.floor(f.y / k), size = this.getTileSize();
      const W = size.x * k, H = size.y * k, ox = (f.x - px * k) * size.x, oy = (f.y - py * k) * size.y;
      tile.style.width = W + 'px';
      tile.style.height = H + 'px';
      tile.style.marginLeft = -ox + 'px';
      tile.style.marginTop = -oy + 'px';
      // Show only this tile's own square of the enlarged parent, so neighbours don't overlap.
      tile.style.clipPath = `inset(${oy}px ${W - ox - size.x}px ${H - oy - size.y}px ${ox}px)`;
      tile.src = L.Util.template(this._url, L.extend({ x: px, y: py, z: f.z - f.depth, s: this._getSubdomain({ x: px, y: py }) }, this.options));
    }
  });

  function setBase(id) {
    layerId = LAYERS[id] ? id : 'topo';
    store.set('mapLayer', layerId);
    const L0 = LAYERS[layerId];
    if (base) map.removeLayer(base);
    base = new FallbackLayer(L0.url, { maxNativeZoom: L0.maxNative, maxZoom: 18, subdomains: L0.subdomains || 'abc',
      attribution: L0.attr, keepBuffer: 3 });
    // Say so when a whole screen of tiles fails, instead of leaving a blank map. A tile that fell back to a
    // saved lower zoom counts as loaded; tileerror fires only once every fallback has failed too.
    let ok = 0, bad = 0;
    note(null);
    base.on('loading', () => { ok = bad = 0; });
    base.on('tileload', () => { ok++; note(null); });
    base.on('tileerror', () => { bad++; });
    base.on('load', () => note(bad && !ok ? L0 : null));
    base.addTo(map);
    $('#mLayerName').textContent = L0.name;
  }
  function note(L0) {
    $('#mapNote').hidden = !L0;
    if (!L0) return;
    $('#mapNoteText').textContent = L0.retired ? 'USGS switched this map off on November 16, 2026. It shows only inside maps you saved before then.'
      : !navigator.onLine ? 'You’re offline and this spot is outside your saved maps.'
      : 'This map isn’t loading (service down or weak signal). Maps saved for offline still show.';
  }
  $('#mapNoteLayers').addEventListener('click', () => $('#mLayers').click());

  /* ---------- Position marker ---------- */
  const meIcon = () => L.divIcon({ className: 'me-icon', iconSize: [64, 64], iconAnchor: [32, 32],
    html: '<div class="me"><svg class="cone" viewBox="0 0 64 64" hidden><path d="M32 32 L20 2 H44 Z"/></svg><span class="dot"></span></div>' });
  function renderMe() {
    const f = FK.getFix();
    if (!map || !f) return;
    const ll = [f.lat, f.lon];
    if (!me) {
      acc = L.circle(ll, { radius: f.acc || 0, className: 'acc', interactive: false }).addTo(map);
      me = L.marker(ll, { icon: meIcon(), interactive: false, keyboard: false, zIndexOffset: 1000 }).addTo(map);
    } else { me.setLatLng(ll); acc.setLatLng(ll).setRadius(f.acc || 0); }
    renderHeading(FK.trueHeading());
    if (visible() && map.getZoom() < 9 && !zoomedToFix) { zoomedToFix = true; map.setView(ll, 14, { animate: false }); setFollow(true); }
    else if (follow && visible()) map.panTo(ll, { animate: true });
    renderTarget(); renderCenter();
  }
  function renderHeading(h) {
    if (!me || !me.getElement()) return;
    const cone = me.getElement().querySelector('.cone');
    if (h == null) { cone.setAttribute('hidden', ''); return; }
    cone.removeAttribute('hidden');
    cone.style.transform = `rotate(${h}deg)`;
  }
  /* Pressed only while it can follow something: with no position yet it does not look switched on. */
  const paintLocate = () => $('#mLocate').setAttribute('aria-pressed', String(follow && !!FK.getFix()));
  function setFollow(on) {
    follow = on; store.set('mapFollow', on);
    paintLocate();
  }
  $('#mLocate').addEventListener('click', () => {
    const f = FK.getFix();
    if (!f) { toast(FK.gpsBlocked() ? FK.BLOCKED_MSG : 'No position yet, so the map can’t follow you. Waiting for a GPS fix: open sky helps.'); return; }
    setFollow(true);
    map.setView([f.lat, f.lon], Math.max(map.getZoom(), 15));
  });

  /* ---------- Center readout ---------- */
  const fmtDist = m => TGEOM.fmtDist(m, FK.tac.unit());
  function renderCenter() {
    if (!visible()) return;
    const c = map.getCenter().wrap(), g = GEO.toMGRS(c.lat, c.lng);
    $('#mCenter').textContent = g ? g.text : `${c.lat.toFixed(5)}, ${c.lng.toFixed(5)}`;
    // the accessible name starts with the text on the button, so a voice command that says what it shows hits it
    $('#mCenter').setAttribute('aria-label', (g ? g.text + '. ' : '') + 'Grid at crosshair. Tap to copy.');
    $('#mCenterRel').textContent = FK.relText(c.lat, c.lng, fmtDist) || 'Grid at the crosshair';
  }
  $('#mCenter').addEventListener('click', async () => {
    const t = $('#mCenter').textContent;
    try { await navigator.clipboard.writeText(t); toast('Copied ' + t); } catch { toast(t); }
  });
  $('#mMark').addEventListener('click', () => { if (map) { const c = map.getCenter().wrap(); FK.markers.create(c.lat, c.lng); } });
  /* Centre the map on a point and stop following the GPS (the list does this before opening a marker). */
  FK.mapShow = (lat, lon) => { if (!map) return; setFollow(false); map.setView([lat, lon], Math.max(map.getZoom(), 15), { animate: false }); };

  /* ---------- Navigation target line ---------- */
  function renderTarget() {
    if (!map) return;
    const w = FK.tac.targetPoint(), f = FK.getFix();
    tgtLine.setLatLngs(w && f ? [[f.lat, f.lon], [w.lat, w.lon]] : []);
  }

  /* ---------- Track recording ---------- */
  const MS_TO_MPH = 2.23694;   // metres a second to mph, as the speed readout in app.js
  const trackDist = () => TGEOM.pathLength(track);
  const fmtSpan = ms => { const m = Math.round(ms / 60000); return `${m >= 60 ? Math.floor(m / 60) + ' h ' : ''}${m % 60} min`; };
  /* The Track dialog's summary: distance and time, then average speed while moving. */
  function trackText() {
    const st = TGEOM.trackStats(track), n = track.length;
    const moving = st.elapsedMs - st.movingMs > 60000 ? ` (${st.movingMs < 60000 ? 'under 1 min' : fmtSpan(st.movingMs)} moving)` : '';
    let t = `${TGEOM.fmtDist(st.dist, FK.tac.unit())} over ${fmtSpan(st.elapsedMs)}${moving}, ${n} ${n === 1 ? 'point' : 'points'}.`;
    if (st.movingMs >= 10000 && st.movingDist >= 10) t += ` Moving average ${(st.movingDist / (st.movingMs / 1000) * MS_TO_MPH).toFixed(1)} mph.`;
    return t;
  }
  function renderTrack() {
    if (map) trackLine.setLatLngs(track.map(p => [p[0], p[1]]));
    const d = trackDist();
    $('#recChip').hidden = !recording;
    const blocked = recording && FK.gpsBlocked();   // it can record nothing: say why instead of a distance that never grows
    $('#recChip').textContent = blocked ? FK.BLOCKED_MSG : `Recording, ${fmtDist(d)}`;
    $('#recChip').setAttribute('aria-label', `Recording, ${blocked ? FK.BLOCKED_MSG : fmtDist(d) + '.'} Open Track recording.`);
    if (track.length) {
      $('#trkInfo').textContent = trackText();
    } else $('#trkInfo').textContent = 'No track recorded yet.';
    $('#trkToggle').textContent = recording ? 'Stop recording' : 'Start recording';
    $('#trkClear').disabled = !track.length || recording;
    $('#trkRoute').disabled = track.length < 2;
    FK.emit('track');   // tac-nav.js shows Back to start from this
  }
  /* A point is recorded only when it is further from the last recorded point than the two fixes' errors could explain:
     at least 5 m and twice the larger accuracy of the two. Accuracy is the 95% radius (the Geolocation spec's meaning), so
     GPS scatter while standing still adds no points, no distance and no moving time; a walk is recorded every 2 x accuracy.
     (Once is not enough: 30 min of correlated scatter at 1 x read as 30 min moving.) The last point's accuracy is kept for
     this session only; after a reload the new fix's own stands in for it. */
  let lastAcc = null;
  function onFixTrack(f) {
    if (!recording || f.acc == null || f.acc > 50) return;
    const last = track[track.length - 1];
    if (last && GEO.distance(last[0], last[1], f.lat, f.lon) < Math.max(5, 2 * f.acc, 2 * (lastAcc ?? f.acc))) return;
    lastAcc = f.acc;
    track.push([+f.lat.toFixed(6), +f.lon.toFixed(6), f.alt == null ? null : Math.round(f.alt * 10) / 10, f.t || Date.now()]);
    store.set('track', track);
    renderTrack();
  }
  function openTrack() { $('#trkMsg').textContent = ''; renderTrack(); FK.sheet.open($('#dlgTrack')); }
  $('#recChip').addEventListener('click', openTrack);
  /* A recorded track as a route: thinned to the most points a route holds, first and last kept, evenly sampled between. */
  $('#trkRoute').addEventListener('click', () => {
    if (track.length < 2) return;
    const n = Math.min(FK.tac.MAX_PTS, track.length);
    const pts = Array.from({ length: n }, (_, i) => track[Math.round(i * (track.length - 1) / (n - 1))]).map(p => [p[0], p[1]]);
    const name = 'Track ' + new Date(track[0][3]).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    const s = FK.tac.addShape({ type: 'route', name, pts });
    if (s === 'limit') { toast(FK.mapTools.LIMIT_MSG); return; }
    const kept = s || FK.tac.shapes().find(x => x.name === name && x.pts.length === n);   // not saved, but on screen this session
    FK.sheet.close($('#dlgTrack'));
    if (s) toast(`Saved as route ${s.name}`);
    if (kept && map) map.fitBounds(pts, { padding: [40, 40], maxZoom: 16 });
  });
  /* Starting again after a break of over 30 min: the old track is kept only if the person says so (never cleared without it). */
  const OLD_MS = 30 * 60000;
  const odlg = $('#dlgTrkOld');
  let oldChoice = null;
  function askOld() {
    const last = track[track.length - 1], ago = Date.now() - last[3];
    const d = new Date(last[3]), today = d.toDateString() === new Date().toDateString();
    $('#toText').textContent = `The track you have (${fmtDist(trackDist())}) ended ${today ? 'at ' + d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      : d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}, ${fmtSpan(ago)} ago. Recording on would join it to where you are now with a straight line.`;
    oldChoice = null;
    FK.sheet.open(odlg, { onClose: () => { const c = oldChoice; oldChoice = null; if (c) FK.sheet.afterStep(() => startRec(c === 'new')); }, onOpen: () => $('#toCancel').focus() });
  }
  $('#toContinue').addEventListener('click', () => { oldChoice = 'continue'; FK.sheet.close(odlg); });
  $('#toNew').addEventListener('click', () => { oldChoice = 'new'; FK.sheet.close(odlg); });
  $('#toCancel').addEventListener('click', () => FK.sheet.close(odlg));
  function startRec(fresh) {
    if (recording) return;
    if (fresh) { track = []; lastAcc = null; store.set('track', track); }
    recording = true; store.set('recording', true);
    FK.setWake(true); toast('Recording. The screen stays on so GPS keeps running.');
    FK.sensors(); renderTrack();
  }
  $('#trkToggle').addEventListener('click', () => {
    if (!recording && FK.gpsBlocked()) { $('#trkMsg').textContent = FK.BLOCKED_MSG; return; }   // it could never record a point
    $('#trkMsg').textContent = '';
    const last = track[track.length - 1];
    if (!recording && last && fin(last[3]) && Date.now() - last[3] > OLD_MS) { askOld(); return; }
    if (!recording) { startRec(false); return; }
    recording = !recording; store.set('recording', recording);
    if (recording) { FK.setWake(true); toast('Recording. The screen stays on so GPS keeps running.'); }
    else FK.setWake(false);
    FK.sensors(); renderTrack();
  });
  $('#trkClear').addEventListener('click', async () => {
    if (!await FK.sheet.confirm({ title: 'Clear the track?', text: `Clear the recorded track (${fmtDist(trackDist())}, ${track.length} points)? Export it first to keep a copy. This can’t be undone.`, ok: 'Clear track', danger: true })) return;
    track = []; store.set('track', track); renderTrack();
  });
  /* Export (GPX or KML) is one sheet in tac-io.js; the Track dialog hands over to it. */
  $('#trkExportOpen').addEventListener('click', () => { FK.sheet.close($('#dlgTrack')); FK.sheet.afterStep(() => FK.io.openExport()); });
  $('#trkClose').addEventListener('click', () => $('#dlgTrack').close());

  /* ---------- Layers ---------- */
  $('#mLayers').addEventListener('click', () => {
    $('#layerList').innerHTML = Object.entries(LAYERS).filter(([id]) => offered(id) || id === layerId).map(([id, l]) => `<label class="opt">
      <input type="radio" name="layer" value="${id}" ${id === layerId ? 'checked' : ''}>
      <span><b>${l.name}</b><br><span class="hint">${l.note}</span></span></label>`).join('');
    FK.sheet.open($('#dlgLayers'));
  });
  $('#layerList').addEventListener('change', e => { setBase(e.target.value); $('#dlgLayers').close(); });
  $('#layersClose').addEventListener('click', () => $('#dlgLayers').close());

  /* ---------- Offline areas ---------- */
  const lon2x = (lon, z) => Math.floor((lon + 180) / 360 * 2 ** z);
  const lat2y = (lat, z) => {
    const r = Math.max(-85.0511, Math.min(85.0511, lat)) * Math.PI / 180;
    return Math.floor((1 - Math.log(Math.tan(r) + 1 / Math.cos(r)) / Math.PI) / 2 * 2 ** z);
  };
  function ranges(a) {
    const out = [];
    for (let z = a.zMin; z <= a.zMax; z++) {
      const n = 2 ** z - 1;
      out.push({ z, x1: Math.max(0, lon2x(a.w, z)), x2: Math.min(n, lon2x(a.e, z)), y1: Math.max(0, lat2y(a.n, z)), y2: Math.min(n, lat2y(a.s, z)) });
    }
    return out;
  }
  const countTiles = a => ranges(a).reduce((s, r) => s + (r.x2 - r.x1 + 1) * (r.y2 - r.y1 + 1), 0);
  const tileUrl = (layer, z, x, y) => LAYERS[layer].url.replace('{z}', z).replace('{x}', x).replace('{y}', y);
  function* tiles(a) {
    for (const r of ranges(a)) for (let x = r.x1; x <= r.x2; x++) for (let y = r.y1; y <= r.y2; y++) yield [r.z, x, y];
  }
  const covers = (a, z, x, y) => {
    if (z < a.zMin || z > a.zMax) return false;
    return x >= lon2x(a.w, z) && x <= lon2x(a.e, z) && y >= lat2y(a.n, z) && y <= lat2y(a.s, z);
  };
  const MAX_TILES = 30000;
  const fmtMB = b => b < 1e6 ? `${Math.max(1, Math.round(b / 1e3))} KB` : `${(b / 1e6).toFixed(b < 1e8 ? 1 : 0)} MB`;

  function currentArea() {
    // After panning across the date line Leaflet reports longitudes past ±180; wrap the view
    // back, then clip what still overhangs (a saved area can't straddle the date line).
    const b = map.wrapLatLngBounds(map.getBounds()), zMax = +$('#saveZ').value;
    const w = Math.max(-180, b.getWest()), e = Math.min(180, b.getEast());
    return { s: b.getSouth(), w, n: b.getNorth(), e, zMax, zMin: Math.max(3, zMax - 9), layer: layerId };
  }
  function estimate() {
    const L0 = LAYERS[layerId];
    const go = $('#saveGo');
    if (L0.retired) { $('#saveEst').textContent = 'USGS switched this map off, so it can’t be saved. Switch to another USGS map in Layers.'; go.disabled = true; return; }
    if (!L0.offline) { $('#saveEst').textContent = `${L0.name} can’t be saved. Switch to a USGS map in Layers.`; go.disabled = true; return; }
    const a = currentArea(), n = countTiles(a);
    if (n > MAX_TILES) { $('#saveEst').textContent = `${n.toLocaleString()} tiles is too many. Zoom in on the map or pick less detail.`; go.disabled = true; return; }
    $('#saveEst').textContent = `${L0.name}: about ${n.toLocaleString()} tiles, roughly ${fmtMB(n * L0.kb * 1024)}.`;
    go.disabled = false;
  }
  async function renderAreaList() {
    $('#areaList').innerHTML = areas.length ? areas.map(a => `<li data-id="${a.id}">
      <span><b>${esc(a.name)}</b><br><span class="hint">${LAYERS[a.layer] ? LAYERS[a.layer].name : a.layer}, zoom ${a.zMax}, ${a.tiles.toLocaleString()} tiles, ${fmtMB(a.bytes)}${a.partial ? ', incomplete' : ''}</span></span>
      <span class="wact"><button class="btn small ghost" data-area="show">Show</button><button class="btn small ghost" data-area="del">Delete</button></span></li>`).join('')
      : '<li><span class="hint">No saved maps yet. Frame the map on what you need, then download it here.</span></li>';
    if (navigator.storage && navigator.storage.estimate) {
      const e = await navigator.storage.estimate();
      $('#storeUse').textContent = `Field Kit is using ${fmtMB(e.usage || 0)} of storage on this phone.`;
    }
  }
  function renderAreas() {
    if (!map) return;
    const g = areaGroup(); g.clearLayers();
    areas.forEach(a => L.rectangle([[a.s, a.w], [a.n, a.e]], { className: 'area-rect', interactive: false }).addTo(g));
  }

  let busy = false, cancel = false;
  function openSave() {
    if (!map) return;
    if (!busy) { $('#saveName').value = ''; $('#saveProg').hidden = true; $('#saveStatus').textContent = ''; }
    estimate(); renderAreaList(); FK.sheet.open($('#dlgSave'));
  }
  $('#saveZ').addEventListener('change', estimate);
  $('#saveClose').addEventListener('click', () => $('#dlgSave').close());

  /* A signal that aborts after ms. AbortSignal.timeout is missing on older Safari for iPhone, so build one from an
     AbortController and a timer there; with no AbortController either, undefined (the fetch then has no time limit). The timer
     is left to fire even when the request has finished: aborting a finished request does nothing. */
  function timeoutSignal(ms) {
    if (typeof AbortSignal !== 'undefined' && typeof AbortSignal.timeout === 'function') return AbortSignal.timeout(ms);
    if (typeof AbortController !== 'function') return undefined;
    const c = new AbortController();
    setTimeout(() => c.abort(), ms);
    return c.signal;
  }
  async function probe(layer) {
    const u = tileUrl(layer, 0, 0, 0);
    try { const r = await fetch(u, { mode: 'cors', cache: 'no-store', signal: timeoutSignal(10000) }); if (r.ok) return 'cors'; } catch { /* try opaque */ }
    try { await fetch(u, { mode: 'no-cors', cache: 'no-store', signal: timeoutSignal(10000) }); return 'no-cors'; } catch { return null; }
  }

  $('#saveGo').addEventListener('click', async () => {
    if (busy) { cancel = true; return; }
    const a = currentArea(), L0 = LAYERS[a.layer], total = countTiles(a);
    if (!L0.offline || total > MAX_TILES) return;
    if (!navigator.onLine) { $('#saveStatus').textContent = 'You’re offline. Connect to download maps.'; return; }
    busy = true; cancel = false;
    $('#saveGo').textContent = 'Cancel';
    $('#saveStatus').textContent = 'Checking the map server…';
    const mode = await probe(a.layer);
    if (!mode) { done('Couldn’t reach the map server. Check your connection and try again.'); return; }
    // Without CORS, Chrome counts each stored tile as much larger than it is, so keep areas small.
    if (mode === 'no-cors' && total > 3000) { done('This map server only allows small saved maps. Zoom in or pick less detail (under 3,000 tiles).'); return; }
    if (navigator.storage && navigator.storage.persist) navigator.storage.persist().catch(() => {});
    let lock = null;
    if ('wakeLock' in navigator) { try { lock = await navigator.wakeLock.request('screen'); } catch { /* ignore */ } }

    const cache = await caches.open(TILE_CACHE);
    const it = tiles(a);
    let finished = 0, failed = 0, bytes = 0, full = false;
    const prog = $('#saveProg'); prog.hidden = false; prog.max = total; prog.value = 0;
    const update = () => { prog.value = finished; $('#saveStatus').textContent = `${finished.toLocaleString()} of ${total.toLocaleString()} tiles. Keep Field Kit open.`; };
    async function one(z, x, y) {
      const url = tileUrl(a.layer, z, x, y);
      if (await cache.match(url, { ignoreVary: true })) return;
      for (let t = 0; t < 3; t++) {
        try {
          // A stalled request would otherwise hang this download worker forever.
          const res = await fetch(url, { mode, signal: timeoutSignal(15000) });
          if (res.type === 'opaque' || res.ok) {
            bytes += res.type === 'opaque' ? L0.kb * 1024 : (await res.clone().blob()).size;
            try { await cache.put(url, res); }
            catch { cancel = full = true; failed++; return; }
            return;
          }
          if (res.status === 404) return;
        } catch { /* retry */ }
        await new Promise(r => setTimeout(r, 600 * (t + 1)));
      }
      failed++;
    }
    async function worker() {
      for (let n = it.next(); !n.done && !cancel; n = it.next()) {
        await one(...n.value); finished++;
        if (finished % 10 === 0) update();
      }
    }
    await Promise.all(Array.from({ length: 6 }, worker));
    update();
    if (lock) lock.release().catch(() => {});

    const name = $('#saveName').value.trim() || `Saved map ${areas.length + 1}`;
    if (finished > 0) {
      areas.push({ id: Date.now().toString(36), name, layer: a.layer, s: a.s, w: a.w, n: a.n, e: a.e, zMin: a.zMin, zMax: a.zMax,
        tiles: total, bytes, partial: cancel || failed > 0, date: Date.now() });
      store.set('areas', areas); renderAreas();
    }
    done(full ? `Phone storage is full, so the download stopped. ${name} is incomplete. Delete a saved map you don’t need or free space on the phone, then download again to finish.`
      : cancel ? `Stopped. Kept the ${finished.toLocaleString()} tiles already saved.`
      : failed ? `Saved ${name}, but ${failed} tiles failed. Download it again to fill the gaps.`
      : `Saved ${name}. It works offline now.`);
  });
  function done(msg) {
    busy = false; cancel = false;
    $('#saveGo').textContent = 'Download';
    $('#saveStatus').textContent = msg;
    renderAreaList();
  }

  $('#areaList').addEventListener('click', async e => {
    const b = e.target.closest('[data-area]'); if (!b) return;
    const id = b.closest('li').dataset.id, a = areas.find(x => x.id === id); if (!a) return;
    if (b.dataset.area === 'show') { $('#dlgSave').close(); map.fitBounds([[a.s, a.w], [a.n, a.e]]); setFollow(false); return; }
    if (!await FK.sheet.confirm({ title: 'Delete the saved map?', text: `Delete the saved map ${a.name}? You’ll need internet to download it again.`, ok: 'Delete saved map', danger: true })) return;
    b.disabled = true;
    const others = areas.filter(x => x.id !== id && x.layer === a.layer);
    const cache = await caches.open(TILE_CACHE);
    for (const [z, x, y] of tiles(a)) {
      if (!others.some(o => covers(o, z, x, y))) await cache.delete(tileUrl(a.layer, z, x, y), { ignoreVary: true });
    }
    areas = areas.filter(x => x.id !== id); store.set('areas', areas);
    renderAreas(); renderAreaList(); toast(`Deleted ${a.name}`);
  });

  /* ---------- Wiring ---------- */
  FK.on('shown', s => { if (s.tab === 'tactical' && s.view === 'map') requestAnimationFrame(init); });
  FK.on('fix', f => { onFixTrack(f); renderMe(); paintLocate(); });
  FK.on('heading', renderHeading);
  /* Location blocked: the map says what Position says, instead of showing nothing. */
  const renderGps = () => { const b = FK.gpsBlocked(); $('#mapGps').hidden = !b; $('#mapGps').textContent = b ? FK.BLOCKED_MSG : ''; };
  FK.on('gpsBlocked', () => { renderGps(); renderTrack(); });
  FK.on('wps', () => { renderTarget(); renderTrack(); });
  FK.on('target', renderTarget);
  /* Navigation starting (a new target, not the next point of the same route) turns follow on, so the map moves with the walker. */
  const targetKey = () => { const t = FK.tac.target(); return t ? `${t.type}:${t.id || t.lat + ',' + t.lon}` : null; };
  let lastTarget = targetKey();
  FK.on('target', () => {
    const k = targetKey(), was = lastTarget;
    lastTarget = k;
    if (!k || k === was || !map) return;
    setFollow(true);
    const f = FK.getFix();
    if (f && visible()) map.panTo([f.lat, f.lon], { animate: false });
  });
  FK.on('shapes', renderTarget);   // a route target's point can move when the route is edited
  FK.on('unit', () => { renderCenter(); renderTrack(); });
  FK.on('fixlive', renderCenter);   // a fix just went stale (or live): "from you" becomes "from last position"
  /* Track recording and Save map for offline open from the Tools sheet (tac-tools.js), search and the recording chip. */
  /* Show these [lat, lon] points (follow off), as after an import. */
  function fit(pts) {
    if (!map || !pts || !pts.length) return;
    setFollow(false);
    map.fitBounds(pts, { padding: [40, 40], maxZoom: 16, animate: false });
  }
  FK.map = { openTrack, openSave, resize: sizeMap, fit, timeoutSignal, track: () => track.map(p => p.slice()),
    trackStart: () => track.length ? { lat: track[0][0], lon: track[0][1] } : null };
  renderTrack();
  if (recording) { FK.sensors(); if (!FK.wakeOn()) FK.setWake(true); }
  if (FK.tab() === 'tactical' && FK.view() === 'map') requestAnimationFrame(init);
})();
