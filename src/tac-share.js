/* ---------- FK.share: shared markers (Meshtastic waypoints) and the rules for incoming ones ----------
   A marker is shared when it has a net record (src/tac-data.js). Sharing is opt-in per marker: nothing saved before the radio
   link has a record, so nothing old is ever sent. Every shared marker is open: anyone holding it can change, send or delete
   it. Storage: meshTombs [{ wid, t }], the waypoint numbers deleted here or by a teammate, kept 30 days; anything arriving
   under one of them is ignored, so a teammate who missed the delete cannot bring the marker back.
   "Mine" is net.mine: this phone chose to share the marker. It does not depend on the radio number (a marker shared before
   any radio was known, or before a radio change, stays mine). A marker that is mine is never destroyed from the mesh: a
   teammate's delete or a passing expiry leaves it here as a private marker with a line in its note.
   With the Settings switch off this module does nothing (no expiry, no cap, no queue, no sending); Stop sharing and delete
   still work on this phone, and expiry and tomb pruning catch up when the switch is turned on.
   A delete on the wire (neither form is confirmed by the official apps' documentation): this app sends the whole waypoint
   again already expired (expire = 1, epoch seconds). On receipt, that form (any expiry at or before now) is a delete, and so
   is the reference package's form for a number this phone holds: only the id, no position, no name, expire 0. */
(() => {
  const { store, fin, on } = FK;
  const DAY = 864e5, TOMB_MS = 30 * DAY, MAX_TOMBS = 2000, CAP = 500, GAP = 3000;
  const okWid = v => Number.isInteger(v) && v >= 1 && v <= 0xFFFFFFFF;
  let stopped = false;                 // a restore is replacing storage: write nothing more (the page reloads)

  /* ---- tombs ---- */
  const loadTombs = () => {
    const seen = new Set(), now = Date.now(), v = store.get('meshTombs', []);
    return (Array.isArray(v) ? v : [])
      .filter(x => x && typeof x === 'object' && okWid(x.wid) && fin(x.t) && !seen.has(x.wid) && seen.add(x.wid))
      .map(x => ({ wid: x.wid, t: Math.min(x.t, now) }))   // a time ahead (another phone's clock) would never run out
      .slice(-MAX_TOMBS);
  };
  let tombs = loadTombs(), tombSet = new Set(tombs.map(x => x.wid)), tombsDirty = false;
  function tomb(wid) {
    if (tombSet.has(wid)) return;
    tombs.push({ wid, t: Date.now() }); tombSet.add(wid); tombsDirty = true;
    if (tombs.length > MAX_TOMBS) tombSet.delete(tombs.shift().wid);
  }
  function pruneTombs(now) {
    const keep = tombs.filter(x => now - x.t < TOMB_MS);
    if (keep.length === tombs.length) return;
    tombs = keep; tombSet = new Set(tombs.map(x => x.wid)); tombsDirty = true;
  }
  const saveTombs = () => { if (tombsDirty && !stopped) { tombsDirty = false; store.set('meshTombs', tombs); } };

  /* ---- who holds what ---- */
  const find = id => FK.tac.markers().find(m => m.id === id) || null;
  const me = () => FK.mesh.myNum();
  const isMine = m => !!(m && m.net && m.net.mine === true);
  const on_ = () => FK.mesh.enabled();
  const newWid = () => {
    const held = new Set(FK.tac.markers().filter(m => m.net).map(m => m.net.wid));
    let w;
    do w = 1 + Math.floor(Math.random() * 0xFFFFFFFF); while (held.has(w) || tombSet.has(w) || !okWid(w));
    return w;
  };
  /* The waypoint for a marker: its stored expiry and foreign icon go out again unchanged. */
  const wpOf = (m, expire) => MMK.toWaypoint(m, m.net.wid, { icon: m.net.icon, expire: expire === undefined ? m.net.expire : expire });

  /* ---- sending ---- */
  let lastSend = -Infinity;
  /* Send a shared marker as it is now. 'no' (no such shared marker), 'toolong' (nothing changed), 'pending' (no link, or the
     radio refused: sent on the next connection) or 'sent'. A record made before any radio was known (from 0) takes this
     radio's number when it first goes out. */
  async function sendNow(id) {
    const m = find(id);
    if (!on_() || !m || !m.net) return 'no';
    if (!MMK.fits(m).ok) return 'toolong';
    if (!FK.mesh.canShare()) {
      if (!m.net.pending) FK.tac.setNet(id, { ...m.net, pending: true });
      return 'pending';
    }
    const who = m.net.from === 0 && me() !== null ? { from: me(), by: FK.mesh.nameOf(me()) } : {};
    lastSend = Date.now();
    const ok = await FK.mesh.sendWaypoint(wpOf(m));
    if (stopped) return ok ? 'sent' : 'pending';                 // a restore replaced storage meanwhile: write nothing
    const after = find(id);
    if (after && after.net && after.net.wid === m.net.wid) {   // still held and shared under the same number
      if (ok) FK.tac.setNet(id, { ...after.net, ...who, pending: false, t: Date.now() });
      else if (!after.net.pending) FK.tac.setNet(id, { ...after.net, pending: true });
    }
    return ok ? 'sent' : 'pending';
  }

  async function share(id) {
    const m = find(id);
    if (!on_() || !m) return 'no';
    if (!MMK.fits(m).ok) return 'toolong';
    if (!m.net) {
      const n = me();
      const net = { wid: newWid(), from: n === null ? 0 : n, by: n === null ? '' : FK.mesh.nameOf(n), t: Date.now(), chBy: '', chT: 0,
        icon: 0, expire: 0, pending: true, rx: false, mine: true };
      if (!FK.tac.setNet(id, net)) return 'no';
    }
    return sendNow(id);
  }
  /* After this phone saved or moved a shared marker: send it again under the same number. This phone's own change is not
     "changed by" anyone, so that line clears. */
  async function changed(id) {
    const m = find(id);
    if (!on_() || !m || !m.net) return 'no';
    if (!MMK.fits(m).ok) return 'toolong';
    if (m.net.chBy || m.net.chT) FK.tac.setNet(id, { ...m.net, chBy: '', chT: 0 });
    return sendNow(id);
  }
  /* Stop sharing: the copy here becomes private and nothing is sent. The number is remembered (tomb), so a teammate's later
     send of it does not come back beside the private copy. */
  function unshare(id) {
    const m = find(id);
    if (!m || !m.net || !FK.tac.setNet(id, null)) return false;
    tomb(m.net.wid); saveTombs();
    return true;
  }
  /* Delete a marker here; a shared one is remembered (tomb). With everyone, the delete also goes out when the link can send.
     Resolves 'sent' (the delete went out), 'local' (removed here only: teammates still have it) or 'no' (no such marker). */
  async function remove(id, everyone) {
    const m = find(id);
    if (!m) return 'no';
    if (!m.net) { FK.tac.removeMarker(id); return 'local'; }
    const wp = everyone ? wpOf(m, 1) : null;
    tomb(m.net.wid); saveTombs();
    FK.tac.removeMarker(id);
    if (!wp || !FK.mesh.canShare()) return 'local';
    lastSend = Date.now();
    return (await FK.mesh.sendWaypoint(wp)) ? 'sent' : 'local';
  }

  /* ---- the spaced queue: pending markers on connection, and "send all mine again", one every GAP ms ---- */
  let queue = [], qTimer = 0, busy = false;
  function enqueue(ids) {
    let n = 0;
    ids.forEach(id => { if (!queue.includes(id)) { queue.push(id); n++; } });
    kick();
    return n;
  }
  function kick() {
    if (busy || qTimer || !queue.length || stopped) return;
    qTimer = setTimeout(step, Math.max(0, lastSend + GAP - Date.now()));
  }
  async function step() {
    qTimer = 0;
    if (stopped) return;
    if (!FK.mesh.canShare()) { queue = []; return; }   // pending ones stay pending for the next connection
    const id = queue.shift(), m = find(id);
    if (m && m.net && MMK.fits(m).ok) {
      busy = true;
      try { await sendNow(id); } finally { busy = false; }
    }
    kick();
  }
  function resendMine() {
    if (!FK.mesh.canShare()) return 0;
    return enqueue(FK.tac.markers().filter(m => isMine(m) && MMK.fits(m).ok).map(m => m.id));
  }
  /* The link can send again: queue every pending marker. Never from inside the radio's message handler (a channel verdict
     can arrive there): a timer starts it. */
  let could = false, wasOn = on_();
  on('mesh', () => {
    if (on_() !== wasOn) { wasOn = on_(); if (wasOn) sweepNow(); syncTimer(); }   // switched on: expiry and tombs catch up
    const can = FK.mesh.canShare();
    if (can && !could) setTimeout(() => {
      if (FK.mesh.canShare()) enqueue(FK.tac.markers().filter(m => m.net && m.net.pending).map(m => m.id));
    }, 0);
    could = can;
  });

  /* ---- held markers over time: expiry, tombs' age, the cap ---- */
  /* The end of sharing for a marker from the mesh (a delete, or its expiry): a marker that is mine stays here, private, its
     note starting with why; any other is removed. The number is tombed either way. */
  function endShared(m, line) {
    tomb(m.net.wid);
    if (isMine(m)) {
      FK.tac.setNet(m.id, null);
      FK.tac.updateMarker(m.id, { note: (line + (m.note ? ' ' + m.note : '')).slice(0, FK.tac.MAX_NOTE) });
    } else FK.tac.removeMarker(m.id);
  }
  let dropped = 0;
  /* Inside a FK.tac.batch. idx: wid -> marker for every shared marker (kept up to date by the caller). Only markers that are
     not mine count and can go, never the navigation target. */
  function enforceCap(idx) {
    const tgt = FK.tac.target(), tid = tgt && tgt.type === 'marker' ? tgt.id : null;
    for (;;) {
      let n = 0, oldest = null;
      idx.forEach(m => {
        if (isMine(m)) return;
        n++;
        if (m.id !== tid && (!oldest || m.net.t < oldest.net.t)) oldest = m;
      });
      if (n <= CAP || !oldest) return;
      FK.tac.removeMarker(oldest.id); idx.delete(oldest.net.wid); dropped++;
    }
  }
  const indexShared = () => new Map(FK.tac.markers().filter(m => m.net).map(m => [m.net.wid, m]));
  function sweep(now, idx) {
    idx.forEach((m, wid) => {
      if (m.net.expire > 0 && m.net.expire * 1000 <= now) { endShared(m, 'Sharing expired.'); idx.delete(wid); }
    });
    pruneTombs(now);
    enforceCap(idx);
  }
  function sweepNow() {
    if (stopped || !on_()) return;
    FK.tac.batch(() => sweep(Date.now(), indexShared()));
    saveTombs();
  }

  /* ---- incoming ---- */
  /* One received waypoint (inside a batch). d: the 'meshWaypoint' detail { wp, from, name }. */
  function receive(d, now, idx) {
    const wp = d.wp, wid = wp.id;
    if (!okWid(wid) || tombSet.has(wid)) return;
    if (d.from === me()) return;                 // our own radio's number: an echo of what this phone sent
    const m = idx.get(wid);
    const expired = fin(wp.expire) && wp.expire > 0 && wp.expire * 1000 <= now;
    /* The reference package's delete: no position, no name, no expiry. For a number not held it is ignored and leaves no
       tomb (it cannot be told from a malformed packet). Checked before fromWaypoint, which rejects 0, 0. */
    const bare = !!m && wp.lat === 0 && wp.lon === 0 && !wp.name && !(wp.expire > 0);
    if (expired || bare) {   // a delete: the maker keeps a private copy saying who deleted it
      if (!m) { tomb(wid); return; }
      idx.delete(wid);
      endShared(m, `Deleted by ${d.name}.`);
      return;
    }
    const f = MMK.fromWaypoint(wp, now);
    if (!f) return;
    if (f.t > now) f.t = now;                    // a sighting cannot be in the future (rx stays false: it had a time)
    const icon = f.kind === 'point' && f.icon && !MMK.kindFor(f.icon) ? f.icon : 0;
    if (m) {
      const patch = { name: f.name, note: f.note, kind: f.kind, lat: f.lat, lon: f.lon };
      if (m.lat !== f.lat || m.lon !== f.lon) patch.alt = null;
      if (!f.rx) patch.t = f.t;
      FK.tac.updateMarker(m.id, patch);
      FK.tac.setNet(m.id, { ...m.net, chBy: d.name, chT: now, t: now, icon, expire: f.expire, rx: f.rx ? m.net.rx : false });
      idx.set(wid, find(m.id));
      return;
    }
    const added = FK.tac.addShared({ name: f.name, lat: f.lat, lon: f.lon, kind: f.kind, note: f.note, t: f.t,
      net: { wid, from: d.from, by: d.name, t: now, chBy: '', chT: 0, icon, expire: f.expire, pending: false, rx: f.rx, mine: false } });
    if (added) { idx.set(wid, added); if (!isMine(added)) enforceCap(idx); }
  }
  /* Waypoints arrive in bursts: they wait here and apply once per animation frame (a timer stands in while the page is hidden,
     when frames stop), so a burst costs one storage write and one 'wps' event. */
  let inbox = [], raf = 0, tmr = 0;
  function flush() {
    cancelAnimationFrame(raf); clearTimeout(tmr); raf = tmr = 0;
    const got = inbox;
    inbox = [];
    if (stopped || !got.length) return;
    const now = Date.now();
    FK.tac.batch(() => {
      const idx = indexShared();
      got.forEach(d => receive(d, now, idx));
      sweep(now, idx);
    });
    saveTombs();
  }
  on('meshWaypoint', d => {
    if (stopped || !d || !d.wp) return;
    inbox.push(d);
    if (!raf) raf = requestAnimationFrame(flush);
    if (!tmr) tmr = setTimeout(flush, 1000);
  });

  /* Expiry is checked on load, on each incoming message, and each minute while the map shows. */
  let tick = 0;
  function syncTimer() {
    const want = !stopped && on_() && !document.hidden && FK.tab() === 'tactical' && FK.view() === 'map';
    if (want && !tick) tick = setInterval(sweepNow, 60000);
    else if (!want && tick) { clearInterval(tick); tick = 0; }
  }
  on('shown', syncTimer);
  document.addEventListener('visibilitychange', syncTimer);
  on('restoring', () => {
    stopped = true; inbox = []; queue = [];
    clearTimeout(qTimer); clearTimeout(tmr); cancelAnimationFrame(raf); clearInterval(tick); tick = 0;
  });
  on('restoreFailed', () => { stopped = false; syncTimer(); });
  sweepNow();
  syncTimer();

  FK.share = {
    share, resend: sendNow, resendMine, unshare, remove, changed,
    isShared: id => !!(find(id) || {}).net,
    mine: id => isMine(find(id)),
    dropped: () => dropped
  };
  FK._test.share = { flush };
})();
