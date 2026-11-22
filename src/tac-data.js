/* ---------- Tactical data: markers, routes, areas and rings, the navigation target, and the distance unit ----------
   Storage keys stay as they were in v7.7 (wps, target); shapes and distUnit are new. Everything read from storage is
   checked, so an old version or a hand-edited backup can't stop the app from starting or inject markup. */
(() => {
  const { store, fin, okId, okLatLon, list, toast, emit, FULL_MSG } = FK;
  const KINDS = [
    ['point', 'Point', 'place'], ['camp', 'Camp', 'place'], ['vehicle', 'Vehicle', 'place'], ['water', 'Water', 'place'],
    ['cache', 'Cache', 'place'], ['hazard', 'Hazard', 'place'], ['rally', 'Rally point', 'place'],
    ['observe', 'Observation point', 'place'], ['medical', 'Medical', 'place'],
    ['friend', 'Friend', 'affil'], ['hostile', 'Hostile', 'affil'], ['neutral', 'Neutral', 'affil'], ['unknown', 'Unknown', 'affil']
  ].map(([id, label, group]) => ({ id, label, group }));
  const kindOk = k => KINDS.some(x => x.id === k);
  const MAX_PTS = 200, MAX_SHAPES = 100, MAX_NOTE = 500, MAX_NAME = 60;
  const TYPES = { route: { min: 2, name: 'Route' }, area: { min: 3, name: 'Area' }, ring: { min: 1, name: 'Ring' } };

  /* ---------- Markers ---------- */
  /* A shared marker carries net, its record on the radio mesh (src/tac-share.js): wid (the waypoint number, 1..0xFFFFFFFF),
     from (the maker's radio number; 0 = this phone, before any radio was known), by (the maker's name), t (last sent or
     received, ms), chBy and chT (who changed it last from the mesh, and when), icon (another app's emoji, kept only on a
     Point; 0 otherwise), expire (epoch SECONDS as on the wire; 0 never), pending (to send on the next connection), rx (t is
     when it arrived, not when it was marked), mine (this phone chose to share it; a record without it counts as mine only
     when from is 0, which only this phone's unsent share can have). Kept only when every field has the right type; otherwise the marker is
     private. Markers saved before the radio link have no net, and a marker with no net is never sent. */
  const NET_STR = 40;
  const u32 = v => Number.isInteger(v) && v >= 0 && v <= 0xFFFFFFFF;
  function cleanNet(n, kind) {
    if (!n || typeof n !== 'object' || Array.isArray(n)) return null;
    const { wid, from, by, t, chBy, chT, icon, expire, pending, rx } = n;
    const mine = n.mine === undefined ? from === 0 : n.mine;
    if (!(u32(wid) && wid >= 1) || !u32(from) || typeof by !== 'string' || !fin(t) || typeof chBy !== 'string' || !fin(chT) ||
        !u32(icon) || !u32(expire) || typeof pending !== 'boolean' || typeof rx !== 'boolean' || typeof mine !== 'boolean') return null;
    return { wid, from, by: by.slice(0, NET_STR), t, chBy: chBy.slice(0, NET_STR), chT,
      icon: kind === 'point' && !MMK.kindFor(icon) ? icon : 0, expire, pending, rx, mine };
  }
  const cleanMarker = w => {
    const kind = kindOk(w.kind) ? w.kind : 'point';
    const m = {
      id: w.id, name: String(w.name ?? 'Marker').slice(0, MAX_NAME), lat: w.lat, lon: w.lon, alt: fin(w.alt) ? w.alt : null, t: fin(w.t) ? w.t : 0,
      kind, note: typeof w.note === 'string' ? w.note.slice(0, MAX_NOTE) : ''
    };
    const net = cleanNet(w.net, kind);
    if (net) m.net = net;
    return m;
  };
  /* Keep the first record of any repeated id. */
  const firsts = arr => { const seen = new Set(); return arr.filter(x => !seen.has(x.id) && seen.add(x.id)); };
  let wps = firsts(list('wps', w => okId(w.id) && okLatLon(w.lat, w.lon))).map(cleanMarker);
  { const wids = new Set(); wps.forEach(w => { if (w.net && (wids.has(w.net.wid) || !wids.add(w.net.wid))) delete w.net; }); }   // a repeated wid: the first keeps it
  /* Inside batch() a change is only marked: the batch writes once and emits 'wps' once at its end. */
  let batching = 0, dirty = false;
  const saveWps = () => {
    if (batching) { dirty = true; return true; }
    const ok = store.set('wps', wps); emit('wps'); return ok;
  };
  /* A new id that no marker or shape holds, however many are added in the same millisecond. */
  let seq = 0;
  const newId = prefix => {
    const used = id => wps.some(w => w.id === id) || shapes.some(s => s.id === id);   // no Set per call: a burst adds thousands
    let id;
    do id = prefix + Date.now().toString(36) + (seq++).toString(36); while (used(id));
    return id;
  };

  /* Returns the marker, or null if it couldn't be saved (it stays on screen until the app closes). */
  function addMarker(o) {
    if (!o || !okLatLon(o.lat, o.lon)) return null;
    const m = cleanMarker({ ...o, net: null, id: newId('m'), name: String(o.name || '').trim() || `WP ${wps.length + 1}`, t: Date.now() });
    wps.push(m);
    const ok = saveWps();
    if (!ok) { toast(FULL_MSG); return null; }
    return m;
  }
  /* A marker time from a file is kept when it is a real date from 1990 to a day ahead (an affiliation marker fades by its age);
     otherwise the marker is timed now. */
  const okTime = t => fin(t) && t >= Date.UTC(1990, 0, 1) && t <= Date.now() + 86400000;
  /* Many markers in one save (an import): each one as addMarker makes it (o.t, when given, is kept if okTime), one storage
     write and one 'wps' event for all.
     Returns { added, ok }: ok false when storage refused (the markers stay on screen this session; the full-storage message shows). */
  function addMarkers(arr) {
    const added = [];
    (Array.isArray(arr) ? arr : []).forEach(o => {
      if (!o || !okLatLon(o.lat, o.lon)) return;
      const m = cleanMarker({ ...o, net: null, id: newId('m'), name: String(o.name || '').trim() || `WP ${wps.length + 1}`, t: okTime(o.t) ? o.t : Date.now() });
      wps.push(m); added.push(m);
    });
    if (!added.length) return { added, ok: true };
    const ok = saveWps();
    if (!ok) toast(FULL_MSG);
    return { added, ok };
  }
  /* Only these fields can change; a bad value refuses the whole patch. */
  const PATCH = {
    name: v => typeof v === 'string' && v.trim() !== '', lat: v => fin(v) && Math.abs(v) <= 90, lon: v => fin(v) && Math.abs(v) <= 180,
    alt: v => v === null || fin(v), kind: kindOk, note: v => typeof v === 'string', t: fin
  };
  const own = (o, k) => Object.prototype.hasOwnProperty.call(o, k);
  function patchOk(patch) {
    const ks = patch && typeof patch === 'object' ? Object.keys(patch) : [];
    return ks.length > 0 && ks.every(k => own(PATCH, k) && PATCH[k](patch[k]));
  }
  function updateMarker(id, patch) {
    const i = wps.findIndex(w => w.id === id);
    if (i < 0 || !patchOk(patch)) return false;
    wps[i] = cleanMarker({ ...wps[i], ...patch, name: patch.name === undefined ? wps[i].name : patch.name.trim() });
    const ok = saveWps();
    if (!ok) toast(FULL_MSG);
    return ok;
  }
  function removeMarker(id) {
    if (!wps.some(w => w.id === id)) return;
    wps = wps.filter(w => w.id !== id);
    fixTarget();
    saveWps();
  }
  const widHeld = (wid, exceptId) => wps.some(w => w.net && w.net.wid === wid && w.id !== exceptId);
  /* Set (or with null, clear) a marker's shared record. False when there is no such marker, the record is malformed, another
     marker holds its wid, or storage refused; then the marker is left exactly as it was (a record that is not saved must not
     be sent later). */
  function setNet(id, n) {
    const i = wps.findIndex(w => w.id === id);
    if (i < 0) return false;
    let next;
    if (n === null) { next = { ...wps[i] }; delete next.net; }
    else {
      const c = cleanNet(n, wps[i].kind);
      if (!c || widHeld(c.wid, id)) return false;
      next = { ...wps[i], net: c };
    }
    const prev = wps[i];
    wps[i] = next;
    const ok = saveWps();
    if (!ok) { wps[i] = prev; toast(FULL_MSG); }
    return ok;
  }
  /* A marker that came from the mesh: { name, lat, lon, kind, note, t, net }. Name and note are cut to this app's limits
     (they are another person's text: whoever draws them escapes them). Returns the marker, or null (bad place, malformed or
     already held wid, storage refused). */
  function addShared(o) {
    if (!o || !okLatLon(o.lat, o.lon)) return null;
    const kind = kindOk(o.kind) ? o.kind : 'point', net = cleanNet(o.net, kind);
    if (!net || widHeld(net.wid)) return null;
    const m = cleanMarker({ id: newId('m'), name: String(o.name ?? '').trim() || 'Marker', lat: o.lat, lon: o.lon, alt: null,
      t: fin(o.t) ? o.t : Date.now(), kind, note: o.note, net });
    wps.push(m);
    const ok = saveWps();
    if (!ok) { toast(FULL_MSG); return null; }
    return m;
  }
  /* Many marker changes (addShared, updateMarker, removeMarker, setNet) as one: fn runs them, then one storage write and one
     'wps' event, only if something changed. Returns what fn returns. */
  function batch(fn) {
    batching++;
    let r;
    try { r = fn(); } finally { batching--; }
    if (!batching && dirty) {
      dirty = false;
      fixTarget();
      if (!saveWps()) toast(FULL_MSG);
    }
    return r;
  }

  /* ---------- Shapes ---------- */
  const okPts = (pts, min) => Array.isArray(pts) && pts.length >= min && pts.length <= MAX_PTS &&
    pts.every(p => Array.isArray(p) && p.length === 2 && okLatLon(p[0], p[1]));
  const okRadii = r => Array.isArray(r) && r.length >= 1 && r.length <= 3 && r.every(x => fin(x) && x > 0);
  const okShape = s => !!TYPES[s.type] && okPts(s.pts, TYPES[s.type].min) && (s.type !== 'ring' || (s.pts.length === 1 && okRadii(s.r)));
  const freeName = (type, others) => { const names = new Set(others.map(s => s.name)); let n = 1; while (names.has(`${TYPES[type].name} ${n}`)) n++; return `${TYPES[type].name} ${n}`; };
  const cleanShape = (s, others) => {
    const o = { id: s.id, type: s.type, name: typeof s.name === 'string' && s.name.trim() ? s.name.trim().slice(0, MAX_NAME) : freeName(s.type, others),
      pts: s.pts.map(p => [p[0], p[1]]) };
    if (s.type === 'ring') o.r = s.r.slice();
    o.t = fin(s.t) ? s.t : 0;
    return o;
  };
  let shapes = [];
  firsts(list('shapes', s => okId(s.id) && okShape(s))).slice(0, MAX_SHAPES).forEach(s => shapes.push(cleanShape(s, shapes)));
  const saveShapes = () => { const ok = store.set('shapes', shapes); emit('shapes'); return ok; };

  /* Returns the shape, 'limit' when MAX_SHAPES are already saved, or null (invalid, or it couldn't be saved). */
  function addShape(o) {
    if (!o || typeof o !== 'object' || !okShape({ ...o, name: '' })) return null;
    if (shapes.length >= MAX_SHAPES) return 'limit';
    const s = cleanShape({ ...o, id: newId('s'), t: Date.now() }, shapes);
    shapes.push(s);
    if (!saveShapes()) { toast(FULL_MSG); return null; }
    return s;
  }
  /* Many shapes in one save (an import). Invalid ones are left out; once MAX_SHAPES are held the rest are counted in over.
     Returns { added, over, ok } (ok as addMarkers). */
  function addShapes(arr) {
    const added = [];
    let over = 0;
    (Array.isArray(arr) ? arr : []).forEach(o => {
      if (!o || typeof o !== 'object' || !okShape({ ...o, name: '' })) return;
      if (shapes.length >= MAX_SHAPES) { over++; return; }
      const s = cleanShape({ ...o, id: newId('s'), t: Date.now() }, shapes);
      shapes.push(s); added.push(s);
    });
    if (!added.length) return { added, over, ok: true };
    const ok = saveShapes();
    if (!ok) toast(FULL_MSG);
    return { added, over, ok };
  }
  function updateShape(id, patch) {
    const i = shapes.findIndex(s => s.id === id);
    if (i < 0 || !patch || typeof patch !== 'object') return false;
    const next = { ...shapes[i] };
    if ('name' in patch) { if (typeof patch.name !== 'string' || !patch.name.trim()) return false; next.name = patch.name.trim(); }
    if ('type' in patch) next.type = patch.type;
    if ('pts' in patch) next.pts = patch.pts;
    if ('r' in patch) next.r = patch.r;
    if (!okShape(next)) return false;
    shapes[i] = cleanShape(next, shapes.filter((_, j) => j !== i));
    fixTarget();
    const ok = saveShapes();
    if (!ok) toast(FULL_MSG);
    return ok;
  }
  function removeShape(id) {
    if (!shapes.some(s => s.id === id)) return;
    shapes = shapes.filter(s => s.id !== id);
    fixTarget();
    saveShapes();
  }

  /* ---------- Target: a marker, the next point of a route, or a bare point (never saved as a marker) ----------
     Stored in 'target'. A marker target is the plain id string v7.7 wrote, so a backup still reads in the old version. */
  function cleanTarget(t) {
    if (typeof t === 'string') t = { type: 'marker', id: t };
    if (!t || typeof t !== 'object') return null;
    if (t.type === 'marker') return wps.some(w => w.id === t.id) ? { type: 'marker', id: t.id } : null;
    if (t.type === 'route') {
      const s = shapes.find(x => x.id === t.id && x.type === 'route');
      return s && Number.isInteger(t.i) && t.i >= 0 && t.i < s.pts.length ? { type: 'route', id: s.id, i: t.i } : null;
    }
    if (t.type === 'point') return okLatLon(t.lat, t.lon) ? { type: 'point', lat: t.lat, lon: t.lon, name: typeof t.name === 'string' && t.name ? t.name.slice(0, MAX_NAME) : 'Point' } : null;
    return null;
  }
  let target = cleanTarget(store.get('target', null));
  const saveTarget = () => store.set('target', target && target.type === 'marker' ? target.id : target);
  function setTarget(t) {
    const c = t === null ? null : cleanTarget(t);
    if (t !== null && !c) return false;
    target = c;
    saveTarget();
    emit('target');
    return true;
  }
  /* After markers or shapes change: a route target past the end moves to the last point; one whose marker or route is gone,
     or is no longer a route, is cleared. Emits 'target' only if it changed. */
  function fixTarget() {
    if (!target) return;
    let next = target;
    if (target.type === 'marker') next = wps.some(w => w.id === target.id) ? target : null;
    else if (target.type === 'route') {
      const s = shapes.find(x => x.id === target.id && x.type === 'route');
      next = s ? { ...target, i: Math.max(0, Math.min(target.i, s.pts.length - 1)) } : null;
    }
    if (JSON.stringify(next) === JSON.stringify(target)) return;
    target = next; saveTarget(); emit('target');
  }
  /* step is [i, n]: the route's current index (from 0) and its point count. */
  function targetPoint() {
    if (!target) return null;
    if (target.type === 'point') return { lat: target.lat, lon: target.lon, name: target.name };
    if (target.type === 'marker') { const w = wps.find(x => x.id === target.id); return w ? { lat: w.lat, lon: w.lon, name: w.name } : null; }
    const s = shapes.find(x => x.id === target.id && x.type === 'route'), p = s && s.pts[target.i];
    return p ? { lat: p[0], lon: p[1], name: s.name, step: [target.i, s.pts.length] } : null;
  }

  /* ---------- Unit ---------- */
  let unit = store.get('distUnit', 'metric') === 'us' ? 'us' : 'metric';
  function setUnit(u) {
    if (u !== 'metric' && u !== 'us') return;
    unit = u; store.set('distUnit', u); emit('unit');
  }

  FK.tac = {
    KINDS, MAX_PTS, MAX_SHAPES,
    MAX_NAME, MAX_NOTE,
    markers: () => wps.slice(), addMarker, addMarkers, updateMarker, removeMarker, setNet, addShared, batch,
    shapes: () => shapes.slice(), addShape, addShapes, updateShape, removeShape,
    target: () => target && { ...target }, setTarget, targetPoint,
    unit: () => unit, setUnit
  };
  emit('wps');   // app.js loads first and had nothing to draw: draw the Position count now
})();
