/* ---------- Map: offline topo, waypoints, tracks ---------- */
(() => {
  const FK = window.FK;
  const { $, store, toast, esc, fin, okId, list, okLatLon } = FK;
  const TILE_CACHE = 'fk-tiles';
  const USGS = 'https://basemap.nationalmap.gov/arcgis/rest/services/';
  const LAYERS = {
    topo: { name: 'USGS Topo', note: 'US and territories. Saves for offline.',
      url: USGS + 'USGSTopo/MapServer/tile/{z}/{y}/{x}', maxNative: 16, offline: true, kb: 20,
      attr: '<a href="https://www.usgs.gov/programs/national-geospatial-program/national-map">USGS The National Map</a>' },
    imagery: { name: 'USGS Imagery + Topo', note: 'US satellite imagery with contours. Saves for offline.',
      url: USGS + 'USGSImageryTopo/MapServer/tile/{z}/{y}/{x}', maxNative: 16, offline: true, kb: 45,
      attr: '<a href="https://www.usgs.gov/programs/national-geospatial-program/national-map">USGS The National Map</a>' },
    otm: { name: 'OpenTopoMap', note: 'Worldwide, online only. Its terms don’t allow bulk downloads.',
      url: 'https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', subdomains: 'abc', maxNative: 17, offline: false, kb: 30,
      attr: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, SRTM | © <a href="https://opentopomap.org">OpenTopoMap</a> (CC-BY-SA)' }
  };

  let map = null, base = null, layerId = LAYERS[store.get('mapLayer', 'topo')] ? store.get('mapLayer', 'topo') : 'topo';
  let me = null, acc = null, tgtLine = null, trackLine = null;
  const wpGroup = () => map._fkWps, areaGroup = () => map._fkAreas;
  let follow = store.get('mapFollow', true), zoomedToFix = false;
  let areas = list('areas', a => okId(a.id) && LAYERS[a.layer] && ['s', 'w', 'n', 'e', 'zMin', 'zMax'].every(k => fin(a[k])))
    .map(a => ({ ...a, name: String(a.name ?? 'Area'), tiles: fin(a.tiles) ? a.tiles : 0, bytes: fin(a.bytes) ? a.bytes : 0 }));
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
      // Re-show: resize without letting Leaflet shift the centre, then restore the last view.
      const wrap = $('#mapWrap'), top = wrap.getBoundingClientRect().top;
      wrap.style.height = Math.max(260, window.innerHeight - top - $('.tabbar').offsetHeight) + 'px';
      map.invalidateSize({ pan: false });
      const v = savedView(), f = FK.getFix();
      if (follow && f) map.setView([f.lat, f.lon], map.getZoom(), { animate: false });
      else if (v) map.setView([v.lat, v.lon], v.z, { animate: false });
      renderWps(); renderMe(); renderCenter();
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
    map.on('contextmenu', e => addWpAt(e.latlng.wrap()));
    map.getContainer().addEventListener('click', e => {
      const b = e.target.closest('[data-pop]');
      if (!b) return;
      if (b.dataset.pop === 'nav') FK.toggleTarget(b.dataset.id);
      map.closePopup();
    });

    renderAreas(); renderWps(); renderTrack(); renderMe(); renderCenter(); setFollow(follow);
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
      attribution: L0.attr, keepBuffer: 3 }).addTo(map);
    $('#mLayerName').textContent = L0.name;
  }

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
  function setFollow(on) {
    follow = on; store.set('mapFollow', on);
    $('#mLocate').setAttribute('aria-pressed', String(on));
  }
  $('#mLocate').addEventListener('click', () => {
    const f = FK.getFix();
    if (!f) { toast('Waiting for a GPS fix. Open sky helps.'); return; }
    setFollow(true);
    map.setView([f.lat, f.lon], Math.max(map.getZoom(), 15));
  });

  /* ---------- Center readout ---------- */
  const fmtDist = m => m < 1000 ? `${Math.round(m)} m` : `${(m / 1000).toFixed(m < 10000 ? 2 : 1)} km`;
  function renderCenter() {
    if (!visible()) return;
    const c = map.getCenter().wrap(), g = GEO.toMGRS(c.lat, c.lng);
    $('#mCenter').textContent = g ? g.text : `${c.lat.toFixed(5)}, ${c.lng.toFixed(5)}`;
    const f = FK.getFix();
    if (f) {
      const d = GEO.distance(f.lat, f.lon, c.lat, c.lng), b = GEO.bearing(f.lat, f.lon, c.lat, c.lng);
      $('#mCenterRel').textContent = d < 3 ? 'Your position' : `${fmtDist(d)} at ${Math.round(b)}° true from you`;
    } else $('#mCenterRel').textContent = 'Grid at the crosshair';
  }
  $('#mCenter').addEventListener('click', async () => {
    const t = $('#mCenter').textContent;
    try { await navigator.clipboard.writeText(t); toast('Copied ' + t); } catch { toast(t); }
  });
  $('#mMark').addEventListener('click', () => map && addWpAt(map.getCenter().wrap()));

  function addWpAt(ll) {
    const n = FK.getWps().length + 1;
    const name = prompt('Name this waypoint', `WP ${n}`);
    if (name === null) return;
    const saved = FK.addWp(ll.lat, ll.lng, name);
    if (saved) toast(`Added ${saved}`);
  }

  /* ---------- Waypoints and target ---------- */
  function renderWps() {
    if (!map) return;
    const g = wpGroup(); g.clearLayers();
    const tid = FK.getTarget(), f = FK.getFix();
    FK.getWps().forEach(w => {
      const isT = w.id === tid;
      const icon = L.divIcon({ className: 'wp-icon', iconSize: [18, 18], iconAnchor: [9, 9],
        html: `<div class="wp-pin${isT ? ' tgt' : ''}"><i></i><b>${esc(w.name)}</b></div>` });
      const m = GEO.toMGRS(w.lat, w.lon);
      let rel = '';
      if (f) {
        const d = GEO.distance(f.lat, f.lon, w.lat, w.lon);
        rel = `<br>${fmtDist(d)} at ${Math.round(GEO.bearing(f.lat, f.lon, w.lat, w.lon))}° true`;
      }
      L.marker([w.lat, w.lon], { icon, title: w.name }).addTo(g)
        .bindPopup(`<b>${esc(w.name)}</b><br>${m ? m.text : ''}${rel}<div class="pop-act">
          <button class="btn small" data-pop="nav" data-id="${w.id}">${isT ? 'Stop navigating' : 'Go to'}</button></div>`);
    });
    renderTarget();
  }
  function renderTarget() {
    if (!map) return;
    const w = FK.getWps().find(x => x.id === FK.getTarget()), f = FK.getFix();
    tgtLine.setLatLngs(w && f ? [[f.lat, f.lon], [w.lat, w.lon]] : []);
  }

  /* ---------- Track recording ---------- */
  const trackDist = () => track.reduce((s, p, i) => i ? s + GEO.distance(track[i - 1][0], track[i - 1][1], p[0], p[1]) : 0, 0);
  function renderTrack() {
    if (map) trackLine.setLatLngs(track.map(p => [p[0], p[1]]));
    const d = trackDist();
    $('#recChip').hidden = !recording;
    $('#recChip').textContent = `Recording, ${fmtDist(d)}`;
    $('#mTrack').setAttribute('aria-pressed', String(recording));
    if (track.length) {
      const mins = Math.round((track[track.length - 1][3] - track[0][3]) / 60000);
      $('#trkInfo').textContent = `${fmtDist(d)} over ${mins >= 60 ? Math.floor(mins / 60) + ' h ' : ''}${mins % 60} min, ${track.length} points.`;
    } else $('#trkInfo').textContent = 'No track recorded yet.';
    $('#trkToggle').textContent = recording ? 'Stop recording' : 'Start recording';
    $('#trkExport').disabled = !track.length && !FK.getWps().length;
    $('#trkClear').disabled = !track.length || recording;
  }
  function onFixTrack(f) {
    if (!recording || f.acc == null || f.acc > 50) return;
    const last = track[track.length - 1];
    if (last && GEO.distance(last[0], last[1], f.lat, f.lon) < 5) return;
    track.push([+f.lat.toFixed(6), +f.lon.toFixed(6), f.alt == null ? null : Math.round(f.alt * 10) / 10, f.t || Date.now()]);
    store.set('track', track);
    renderTrack();
  }
  $('#mTrack').addEventListener('click', () => { renderTrack(); $('#dlgTrack').showModal(); });
  $('#trkToggle').addEventListener('click', () => {
    recording = !recording; store.set('recording', recording);
    if (recording) { FK.setWake(true); toast('Recording. The screen stays on so GPS keeps running.'); }
    else FK.setWake(false);
    FK.sensors(); renderTrack();
  });
  $('#trkClear').addEventListener('click', () => {
    if (!confirm(`Clear the recorded track (${fmtDist(trackDist())}, ${track.length} points)? Export it first to keep a copy. This can’t be undone.`)) return;
    track = []; store.set('track', track); renderTrack();
  });
  $('#trkExport').addEventListener('click', () => {
    const x = s => esc(s);
    const wpts = FK.getWps().map(w => `<wpt lat="${w.lat}" lon="${w.lon}">${w.alt != null ? `<ele>${w.alt}</ele>` : ''}<name>${x(w.name)}</name></wpt>`).join('\n');
    const pts = track.map(p => `<trkpt lat="${p[0]}" lon="${p[1]}">${p[2] != null ? `<ele>${p[2]}</ele>` : ''}<time>${new Date(p[3]).toISOString()}</time></trkpt>`).join('\n');
    const day = new Date().toISOString().slice(0, 10);
    const gpx = `<?xml version="1.0" encoding="UTF-8"?>\n<gpx version="1.1" creator="Field Kit" xmlns="http://www.topografix.com/GPX/1/1">\n${wpts}\n` +
      (track.length ? `<trk><name>Field Kit track ${day}</name><trkseg>\n${pts}\n</trkseg></trk>\n` : '') + '</gpx>\n';
    FK.download(`fieldkit-${day}.gpx`, gpx, 'application/gpx+xml');
    toast('Saved to Downloads. ATAK imports GPX from Import → Local SD.');
  });
  $('#trkClose').addEventListener('click', () => $('#dlgTrack').close());

  /* ---------- Layers ---------- */
  $('#mLayers').addEventListener('click', () => {
    $('#layerList').innerHTML = Object.entries(LAYERS).map(([id, l]) => `<label class="opt">
      <input type="radio" name="layer" value="${id}" ${id === layerId ? 'checked' : ''}>
      <span><b>${l.name}</b><br><span class="hint">${l.note}</span></span></label>`).join('');
    $('#dlgLayers').showModal();
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
      : '<li><span class="hint">Nothing saved yet. Frame an area on the map, then download it here.</span></li>';
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
  $('#mSave').addEventListener('click', () => {
    if (!busy) { $('#saveName').value = ''; $('#saveProg').hidden = true; $('#saveStatus').textContent = ''; }
    estimate(); renderAreaList(); $('#dlgSave').showModal();
  });
  $('#saveZ').addEventListener('change', estimate);
  $('#saveClose').addEventListener('click', () => $('#dlgSave').close());

  async function probe(layer) {
    const u = tileUrl(layer, 0, 0, 0);
    try { const r = await fetch(u, { mode: 'cors', cache: 'no-store', signal: AbortSignal.timeout(10000) }); if (r.ok) return 'cors'; } catch { /* try opaque */ }
    try { await fetch(u, { mode: 'no-cors', cache: 'no-store', signal: AbortSignal.timeout(10000) }); return 'no-cors'; } catch { return null; }
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
    if (mode === 'no-cors' && total > 3000) { done('This map server only allows small offline areas. Zoom in or pick less detail (under 3,000 tiles).'); return; }
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
          const res = await fetch(url, { mode, signal: AbortSignal.timeout(15000) });
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

    const name = $('#saveName').value.trim() || `Area ${areas.length + 1}`;
    if (finished > 0) {
      areas.push({ id: Date.now().toString(36), name, layer: a.layer, s: a.s, w: a.w, n: a.n, e: a.e, zMin: a.zMin, zMax: a.zMax,
        tiles: total, bytes, partial: cancel || failed > 0, date: Date.now() });
      store.set('areas', areas); renderAreas();
    }
    done(full ? `Phone storage is full, so the download stopped. ${name} is incomplete. Delete an area you don’t need or free space on the phone, then download again to finish.`
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
    if (!confirm(`Delete the saved map ${a.name}? You’ll need internet to download it again.`)) return;
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
  FK.on('fix', f => { onFixTrack(f); renderMe(); });
  FK.on('heading', renderHeading);
  FK.on('wps', () => { renderWps(); renderTrack(); });
  renderTrack();
  if (recording) { FK.sensors(); if (!FK.wakeOn()) FK.setWake(true); }
  if (FK.tab() === 'tactical' && FK.view() === 'map') requestAnimationFrame(init);
})();
