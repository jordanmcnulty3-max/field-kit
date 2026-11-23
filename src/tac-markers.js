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
  const markedText = (t, word = 'Marked') => {
    const d = new Date(t), same = d.toDateString() === new Date().toDateString();
    const age = ageText(t);
    return `${word} ${same ? '' : d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) + ' '}${hm(t)}${age ? ', ' + age : ''}`;
  };
  const gridText = (lat, lon) => { const g = GEO.toMGRS(lat, lon); return g ? g.text : `${lat.toFixed(5)}, ${lon.toFixed(5)}`; };
  const relText = (lat, lon) => FK.relText(lat, lon, m => TGEOM.fmtDist(m, FK.tac.unit()));   // app.js: one rule for live and last fixes
  const targetId = () => { const t = FK.tac.target(); return t && t.type === 'marker' ? t.id : null; };

  /* A shared marker's corner mark, only while the Settings switch is on (Lucide share-2; clock while it has not gone out). */
  const SHARE2 = '<circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.59" x2="15.42" y1="13.51" y2="17.49"/><line x1="15.41" x2="8.59" y1="6.51" y2="10.49"/>';
  const CLOCK = '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>';
  function netBadge(w) {
    if (!w.net || !FK.mesh || !FK.mesh.enabled()) return '';
    const label = w.net.pending ? 'Shared, not sent yet' : 'Shared with teammates';
    return `<span class="mk-net" role="img" aria-label="${label}" title="${label}">${LINE(w.net.pending ? CLOCK : SHARE2)}</span>`;
  }
  /* A Point received with another app's emoji keeps showing that emoji (one code point; a number, drawn as text). */
  function foreignEmoji(w, kind = w.kind) {
    if (!FK.mesh || !FK.mesh.enabled()) return '';   // with the switch off, pins and rows are as they always were
    const c = w && w.net ? w.net.icon : 0;
    if (kind !== 'point' || !Number.isInteger(c) || c <= 0x20 || c > 0x10FFFF || (c >= 0xD800 && c <= 0xDFFF) || MMK.kindFor(c)) return '';
    return String.fromCodePoint(c);
  }
  const glyph = (w, o) => { const e = foreignEmoji(w); return e ? `<span class="mk-emoji">${esc(e)}</span>` : icon(w.kind, o); };

  /* ---------- Drawing on the map ---------- */
  function render() {
    const map = FK.leafletMap();
    if (!map || !map._fkWps) return;
    const g = map._fkWps; g.clearLayers();
    const tid = targetId();
    FK.tac.markers().forEach(w => {
      const stale = isStale(w);
      const cls = 'mk-pin' + (w.id === tid ? ' tgt' : '') + (stale ? ' stale' : '');
      const html = `<div class="${cls}" data-id="${esc(w.id)}" data-kind="${w.kind}"><i>${glyph(w, { stale })}</i>${netBadge(w)}<b>${esc(w.name)}</b></div>`;
      L.marker([w.lat, w.lon], { icon: L.divIcon({ className: 'mk-icon', iconSize: [30, 30], iconAnchor: [15, 15], html }), title: w.name,
        zIndexOffset: w.id === tid ? 500 : 0 }).on('click', () => { if (!FK.mapTools.mode()) edit(w.id); }).addTo(g);   // inert while a tool mode is on
    });
  }

  /* ---------- Marker sheet ---------- */
  const dlg = $('#dlgMarker'), nameEl = $('#mkName'), noteEl = $('#mkNote'), shareEl = $('#mkShare');
  let cur = null;   // { id (null for new), lat, lon, kind, typed (the name was edited by hand), t, rx (t is when it arrived) }
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
    renderShare();
  }

  /* ---------- Share (src/tac-share.js): the switch, a shared marker's limits and its status lines ----------
     The row shows only while the Settings switch is on and either a radio can send now or the marker is already shared (or
     the user has just turned Share on). With the Settings switch off it stays hidden and the sheet is as it always was.
     With Share on, a name and a note are counted in bytes against what a waypoint can carry (MMK): nothing is ever cut;
     anything that would save over the limit is refused (the message above the buttons) until it is shortened or Share is turned off. */
  const setText = (el, text) => { el.hidden = !text; el.textContent = text || ''; };
  const storedOf = () => cur && cur.id ? FK.tac.markers().find(x => x.id === cur.id) || null : null;
  const netOf = () => { const w = storedOf(); return w && w.net ? w.net : null; };
  const rowShown = () => !!cur && FK.mesh.enabled() && (FK.mesh.canShare() || !!netOf() || shareEl.checked || !!conflict);
  const shareOn = () => rowShown() && shareEl.checked;
  /* What Save will do about sharing: with the row hidden (the Settings switch off), whatever the marker was. */
  const wantShare = () => rowShown() ? shareEl.checked : !!(opened ? opened.share : netOf());
  const TOO_LONG = 'Too long to share. Accents and emoji count extra. Shorten the name or note, or turn Share off.';
  const NOT_SENT = 'Saved. Not sent yet: it goes out when the radio connects.';
  const EXPIRED_LINE = 'This shared marker has expired. Save keeps what you typed as a private marker of your own.';
  const EXPIRED_TOAST = 'This shared marker expired. Your changes were kept as a private marker.';
  /* The open marker's expiry passed while its sheet was open (the sweep spares the open marker): nothing of it is sent again. */
  const expiredOpen = () => !!cur && !!cur.id && FK.mesh.enabled() && !!FK.share && FK.share.expired(cur.id);
  const MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const p2 = n => String(n).padStart(2, '0');
  const dayTime = t => { const d = new Date(t); return `${d.getDate()} ${MON[d.getMonth()]} ${p2(d.getHours())}:${p2(d.getMinutes())}`; };
  /* The name Save will store: what is typed, else the marker's own name (existing) or the default (new). */
  const finalName = () => nameEl.value.trim() || (cur.id ? (storedOf() || { name: '' }).name : defaultName(cur.kind));
  const room = () => ({ name: MMK.NAME_MAX - MMK.bytes(finalName()), note: MMK.noteRoom(cur.kind) - MMK.bytes(noteEl.value.slice(0, 500)) });
  const over = () => { const r = room(); return r.name < 0 || r.note < 0; };
  /* Counted in bytes (what a waypoint carries), so the words never say "characters". */
  function count(el, n) {
    el.hidden = false;
    el.textContent = n >= 0 ? `Room for ${n} more` : `${-n} over the limit`;
    el.classList.toggle('mk-over', n < 0);
  }
  /* The one fixed place above the buttons: what a teammate did while the user typed, and why Save was refused. */
  let refused = false;   // Save was refused for length; the message stays until the name and note fit (or Share is off)
  function renderNotice() {
    if (refused && !(cur && shareOn() && over())) refused = false;
    const lapsed = expiredOpen() && changed() ? EXPIRED_LINE : '';
    setText($('#mkNotice'), [conflict, lapsed, refused ? TOO_LONG : ''].filter(Boolean).join('\n'));
  }
  function renderLeft() {
    const nameLeft = $('#mkNameLeft'), noteLeft = $('#mkLeft');
    $('#mkSeenHint').hidden = !(cur && shareOn() && isAffil(cur.kind));
    if (cur && shareOn()) {
      const r = room();
      count(nameLeft, r.name); count(noteLeft, r.note);
      renderNotice();
      return;
    }
    nameLeft.hidden = true; nameLeft.textContent = '';
    renderNotice();
    const left = 500 - noteEl.value.length;
    noteLeft.classList.remove('mk-over');
    noteLeft.hidden = left >= 50;
    noteLeft.textContent = `${left} ${left === 1 ? 'character' : 'characters'} left`;
  }
  /* A teammate changed or deleted this marker while the user was typing: this line shows above the buttons until the sheet
     closes or refills. */
  let conflict = '';
  function renderShare() {
    if (!cur) return;
    const show = rowShown(), n = netOf(), w = storedOf();
    $('#mkShareBox').hidden = !show;
    setText($('#mkShareHint'), show && n && !shareEl.checked ? 'Your copy becomes private. Teammates keep theirs.' : '');
    const lines = [];
    if (n) {
      lines.push(`Shared by ${n.mine ? 'you' : n.by || 'a teammate'}`);
      if (n.chBy) { const a = ageText(n.chT); lines.push(`Changed by ${n.chBy}${a ? ', ' + a : ''}`); }
      if (n.pending) lines.push('Not sent yet: no radio connected');
      if (n.expire > 0) lines.push(`Expires ${dayTime(n.expire * 1000)}`);
    }
    setText($('#mkShareLine'), show ? lines.join('\n') : '');   // textContent: these names come from other people's radios
    /* Send again sends what is saved: offered only with nothing unsaved, Share on and a marker that fits; with unsaved
       changes a hint takes its place. */
    const can = show && !!n && shareEl.checked && FK.mesh.canShare() && !!w && MMK.fits(w).ok && !expiredOpen();
    const dirty = can && changed();
    $('#mkResend').hidden = !can || dirty;
    $('#mkSendHint').hidden = !dirty;
    const e = w ? foreignEmoji(w, cur.kind) : '';
    setText($('#mkEmoji'), e ? `Sender’s icon: ${e}` : '');
    renderLeft();
  }

  function renderAge() {
    const show = !!cur.id && isAffil(cur.kind) && cur.t > 0;
    $('#mkAge').hidden = !show;
    $('#mkAge').textContent = show ? markedText(cur.t, cur.rx ? 'Received' : 'Marked') : '';
  }
  function fill(o) {
    cur = o;
    $('#mkTitle').textContent = o.id ? 'Marker' : 'New marker';
    nameEl.value = o.name; noteEl.value = o.note;
    shareEl.checked = !!netOf();   // a new marker starts with Share off
    conflict = ''; refused = false;
    $('#mkResend').textContent = 'Send again';
    setKind(o.kind);
    renderShare();
    $('#mkGrid').textContent = gridText(o.lat, o.lon);
    const rel = relText(o.lat, o.lon);
    $('#mkRel').hidden = !rel; $('#mkRel').textContent = rel;
    $('#mkDel').hidden = !o.id;
    $('#mkMove').hidden = !o.id;
    $('#mkGo').textContent = o.id && o.id === targetId() ? 'Stop' : 'Go to';
    dlg.querySelector('.mk-body').scrollTop = 0;
    opened = null;
    FK.sheet.open(dlg, { onClose: () => { cur = null; deleting = false; dlg.inert = false; opened = null; conflict = ''; refused = false;
                                            if (FK.mesh.enabled() && FK.share && FK.share.sweep) setTimeout(FK.share.sweep, 0); },   // what was spared while open (expiry, the cap) catches up
                         onOpen: () => { $('#mkTitle').focus(); snap(); renderShare(); },   // no keyboard popping up on a phone
      guard: { dirty: changed, title: 'Discard this marker?', text: 'The name, note and kind are not kept.' } });
  }
  /* What the sheet showed when it opened, so Back, Escape or a backdrop tap can ask before losing what was typed. */
  let opened = null;
  const snap = () => { if (cur) opened = { name: nameEl.value, note: noteEl.value, kind: cur.kind, share: shareEl.checked }; };
  const changed = () => !!cur && !!opened && !deleting && (!!cur.orphan ||   // a draft left by a teammate's delete: all of it is unsaved
    nameEl.value !== opened.name || noteEl.value !== opened.note || cur.kind !== opened.kind || shareEl.checked !== opened.share);
  /* The open sheet shows the marker as it is stored now (a teammate changed it and nothing here was typed). */
  function refill() {
    const w = storedOf();
    if (!w) return;
    cur = { ...cur, lat: w.lat, lon: w.lon, t: w.t, typed: true, rx: !!(w.net && w.net.rx) };
    nameEl.value = w.name; noteEl.value = w.note;
    shareEl.checked = !!w.net;
    conflict = ''; refused = false;
    setKind(w.kind);
    renderShare();
    $('#mkGrid').textContent = gridText(w.lat, w.lon);
    const rel = relText(w.lat, w.lon);
    $('#mkRel').hidden = !rel; $('#mkRel').textContent = rel;
    snap();
  }
  function create(lat, lon) {
    if (!Number.isFinite(lat) || !Number.isFinite(lon)) return;
    lon = ((lon + 540) % 360) - 180;
    const kind = 'point';   // every new marker starts as a Point: a kind carried over (a Friend after a Friend) was easy to miss
    fill({ id: null, lat, lon, kind, typed: false, t: 0, name: '', note: '' });
    nameEl.value = defaultName(kind);
  }
  function edit(id) {
    const w = FK.tac.markers().find(x => x.id === id);
    if (w) fill({ id, lat: w.lat, lon: w.lon, kind: w.kind, typed: true, t: w.t, name: w.name, note: w.note, rx: !!(w.net && w.net.rx) });
  }

  dlg.querySelector('.mk-kinds').addEventListener('click', e => { const b = e.target.closest('[data-kind]'); if (b && cur) setKind(b.dataset.kind); });
  nameEl.addEventListener('input', () => { if (cur) { cur.typed = true; renderShare(); } });
  noteEl.addEventListener('input', () => { if (cur) renderShare(); });
  shareEl.addEventListener('change', renderShare);
  $('#mkGrid').addEventListener('click', async () => {
    const t = $('#mkGrid').textContent;
    try { await navigator.clipboard.writeText(t); toast('Copied ' + t); } catch { toast(t); }
  });
  /* Save what the sheet shows. Returns the marker's id, also when phone storage is full: tac-data keeps the marker for this
     session and shows the full-storage message itself, every time.
     With onlyIfChanged, an existing marker whose fields are unchanged is not written. */
  let deleting = false;   // Delete has been pressed: nothing else in the sheet may act
  let wrote = false;      // the last commit() changed the marker (or made it)
  const exists = id => FK.tac.markers().some(x => x.id === id);
  function commit(onlyIfChanged) {
    const name = nameEl.value.trim(), kind = cur.kind;
    let note = noteEl.value.slice(0, 500);
    /* A teammate deleted this phone's own marker while a new note was typed: the line saying so is kept in front of it. */
    if (cur.delLine && !note.startsWith(cur.delLine)) note = (cur.delLine + (note ? ' ' + note : '')).slice(0, FK.tac.MAX_NOTE);
    wrote = false;
    if (cur.id) {
      const w = FK.tac.markers().find(x => x.id === cur.id);
      const patch = { kind, note };
      if (name) patch.name = name;
      const same = w.kind === kind && w.note === note && (!name || name === w.name);
      if (onlyIfChanged && same) return cur.id;
      FK.tac.updateMarker(cur.id, patch);
      wrote = !same;
      return cur.id;
    }
    wrote = true;
    const before = new Set(FK.tac.markers().map(x => x.id));
    const m = FK.tac.addMarker({ lat: cur.lat, lon: cur.lon, name: name || defaultName(kind), kind, note });
    if (m) { toast(`Added ${m.name}`); return m.id; }
    const kept = FK.tac.markers().find(x => !before.has(x.id));   // not saved, but on screen until the app closes
    return kept ? kept.id : null;
  }
  /* The marker was removed some other way while its sheet was open. */
  function gone() { FK.sheet.close(dlg); toast('That marker no longer exists.'); }
  const blocked = () => !cur || deleting;

  /* After this phone changed a shared marker (a save here, or a move on the map): send it again under its number. */
  /* moved: the marker's name after a Move on the map, for one toast that says both ("Moved X. Sent to teammates."). */
  function sendChange(id, moved) {
    FK.share.changed(id).then(r => {
      if (r === 'sent') toast(moved ? `Moved ${moved}. Sent to teammates.` : 'Sent to teammates');
      else if (r === 'pending') toast(moved ? `Moved ${moved}. Not sent yet: it goes out when the radio connects.` : NOT_SENT);
      else if (r === 'toolong') toast(TOO_LONG);
      else if (moved) toast(`Moved ${moved}`);
    });
  }
  /* commit() with Share around it. false: refused (Share is on and the name or note is over a shared marker's limit; the
     sheet stays open with the message). Otherwise what commit() returned, after: Share newly on shares the marker; Share
     turned off stops sharing it (the copy here becomes private); a shared marker that changed is sent again. A shared marker
     saved unchanged is not sent (Send again is there for that): an old copy must not overwrite a teammate's newer edit. */
  /* Save on a marker whose expiry passed while its sheet was open: nothing is sent. With typing, what the sheet shows is kept
     as a private marker (a teammate's becomes a new private marker of this phone's, like a teammate's delete while typing; this
     phone's own becomes private with "Sharing expired." in front of the typed note); with no typing, the sheet just closes and
     the marker ends as the sweep would have ended it. */
  function saveExpired() {
    const id = cur.id, typed = changed(), mine = FK.share.mine(id);
    FK.share.expire(id);
    if (!typed) return exists(id) ? id : null;
    if (mine) cur.delLine = 'Sharing expired.';
    else cur = { ...cur, id: null };
    const kept = commit(false);
    toast(EXPIRED_TOAST);
    return kept;
  }
  function save(onlyIfChanged) {
    if (expiredOpen()) return saveExpired();
    if (shareOn() && over()) {
      refused = true;
      renderNotice();   // above the buttons, always on screen; the first field over the limit comes into view with its counter
      const r = room();
      if (r.name < 0) { nameEl.scrollIntoView({ block: 'nearest' }); $('#mkNameLeft').scrollIntoView({ block: 'nearest' }); }
      else { noteEl.scrollIntoView({ block: 'nearest' }); $('#mkLeft').scrollIntoView({ block: 'nearest' }); }
      return false;
    }
    const want = wantShare(), was = !!(opened ? opened.share : netOf());
    const id = commit(onlyIfChanged);
    if (!id) return id;
    const shared = FK.share.isShared(id);
    if (want && !was && !shared) {
      FK.share.share(id).then(r => {
        if (r === 'sent') toast('Shared');
        else if (r === 'pending') toast(NOT_SENT);
        else if (r === 'toolong') toast(TOO_LONG);
      });   // 'no': storage refused (tac-data said so) or the switch is off
    } else if (!want && was && shared) FK.share.unshare(id);
    else if (want && shared && wrote) sendChange(id);
    return id;
  }

  $('#mkForm').addEventListener('submit', e => {
    e.preventDefault();
    if (blocked()) return;
    if (cur.id && !exists(cur.id)) { gone(); return; }
    if (save(false) === false) return;
    FK.sheet.close(dlg);
  });
  // Cancel throws the edits away, except in a draft left by a teammate's delete: there it asks first, as Back does.
  $('#mkCancel').addEventListener('click', () => { if (cur && cur.orphan) FK.sheet.dismiss(dlg); else FK.sheet.close(dlg); });
  /* Go to and Stop keep what was typed: they save first. If storage is full the target still holds for this session. */
  $('#mkGo').addEventListener('click', () => {
    if (blocked()) return;
    if (cur.id && !exists(cur.id)) { gone(); return; }
    const stop = !!cur.id && cur.id === targetId();
    const id = save(true);
    if (id === false) return;
    if (stop) FK.tac.setTarget(null);
    else if (id) FK.tac.setTarget({ type: 'marker', id });
    FK.sheet.close(dlg);
  });
  /* Move saves what was typed, like Go to, then hands the marker to the map's move mode (tac-tools.js). */
  $('#mkMove').addEventListener('click', () => {
    if (blocked() || !cur.id) return;
    if (!exists(cur.id)) { gone(); return; }
    const id = save(true);
    if (id === false) return;
    FK.sheet.close(dlg);
    if (id) FK.mapTools.moveMarker(id);   // its history entry waits for this sheet's step back
  });
  $('#mkDel').addEventListener('click', async () => {
    if (blocked() || !cur.id) return;
    const id = cur.id, w = FK.tac.markers().find(x => x.id === id);
    if (!w) { gone(); return; }
    deleting = true;
    if (w.net) { deleteShared(id, w); return; }
    const yes = await FK.sheet.confirm({ title: 'Delete the marker?', text: `Delete marker ${w.name}? This can’t be undone.`, ok: 'Delete marker', danger: true });
    if (!yes || !cur || cur.id !== id) { deleting = false; return; }
    FK.tac.removeMarker(id);
    dlg.inert = true;
    // The confirm's own step back is still on its way: close the marker sheet once it has landed.
    FK.sheet.afterStep(() => FK.sheet.close(dlg));
  });
  /* A shared marker: for everyone (offered only when a radio can send now) or on this phone only. Either way it goes through
     FK.share.remove, which remembers its number so a teammate's later send cannot bring it back. */
  const ddlg = $('#dlgMkDel');
  function askDelete(w) {
    const all = FK.mesh.canShare();
    $('#mdText').textContent = `Delete marker ${w.name}? This can’t be undone.`;
    $('#mdAll').hidden = !all;
    $('#mdHere').classList.toggle('danger', !all);
    $('#mdHere').classList.toggle('ghost', all);
    return new Promise(resolve => {
      let result = null;   // Cancel, Back, Escape and a backdrop tap all leave it null
      $('#mdAll').onclick = () => { result = 'all'; FK.sheet.close(ddlg); };
      $('#mdHere').onclick = () => { result = 'here'; FK.sheet.close(ddlg); };
      $('#mdCancel').onclick = () => FK.sheet.close(ddlg);
      FK.sheet.open(ddlg, { onClose: () => resolve(result), onOpen: () => $('#mdTitle').focus() });   // a stray Enter takes no choice
    });
  }
  async function deleteShared(id, w) {
    const choice = await askDelete(w);
    if (!choice || !cur || cur.id !== id || dlg.inert) { if (cur && !dlg.inert) deleting = false; return; }
    const everyone = choice === 'all';
    const done = FK.share.remove(id, everyone);   // the marker is gone from this phone before this returns
    dlg.inert = true;
    // The question's own step back is still on its way: close the marker sheet once it has landed.
    FK.sheet.afterStep(() => FK.sheet.close(dlg));
    const r = await done;
    if (r === 'no') toast('That marker no longer exists.');
    else if (everyone && r !== 'private') toast(r === 'sent' ? 'Deleted for everyone' : 'Deleted on this phone. Couldn’t reach the radio, so teammates still have it.');
  }
  /* Send again: the marker as it is stored goes out again under its number (it is offered only with nothing unsaved). The
     result shows on the button: a toast would sit behind the open sheet. */
  let resending = false, sentTimer = 0;
  $('#mkResend').addEventListener('click', async () => {
    if (blocked() || !cur.id || resending) return;
    if (!exists(cur.id)) { gone(); return; }
    const id = cur.id;
    resending = true;
    let r;
    try { r = await FK.share.resend(id); } finally { resending = false; }
    if (r !== 'sent') return;   // 'pending': the status line now says "Not sent yet"
    const b = $('#mkResend');
    b.textContent = 'Sent';
    clearTimeout(sentTimer);
    sentTimer = setTimeout(() => { b.textContent = 'Send again'; }, 2000);
  });

  /* A teammate changed or deleted the marker whose sheet is open (src/tac-share.js 'shareIn'). Deleted (and not this
     phone's own marker): the sheet closes, whatever was typed. Otherwise, with nothing typed, the sheet shows the marker as
     it is now; with typing, the typing stays and a line says what happened (Save keeps the typed version). */
  FK.on('shareIn', d => {
    if (!d || !dlg.open || !cur || !cur.id || d.id !== cur.id || dlg.inert) return;
    if (d.what === 'deleted' && !d.kept && changed()) { orphan(d.name); return; }
    if (d.what === 'deleted' && !d.kept) {
      deleting = true;   // no "Discard?" for a marker that is gone, and nothing else in the sheet may act
      dlg.inert = true;
      toast(`${d.name} deleted this marker`);
      FK.sheet.afterStep(() => FK.sheet.close(dlg));   // closes the delete question too, if it is open
      return;
    }
    if (deleting) return;   // the delete question is open: its answer decides
    const typed = changed();
    if (!typed) { refill(); return; }
    if (d.what === 'deleted') {   // this phone's own marker: it is private now
      shareEl.checked = false;
      if (opened) opened.share = false;
      cur.delLine = `Deleted by ${d.name}.`;
      conflict = `${d.name} deleted this marker for everyone. Your copy is now private.`;
    } else conflict = `This marker was changed by ${d.name} while you were editing. Saving keeps your version.`;
    renderShare();
  });
  /* A teammate deleted a teammate's marker while this sheet held unsaved typing: the typing is never thrown away. The sheet
     becomes an unsaved new private marker at the same place, holding what is typed; Save makes it, Cancel and Back ask. */
  function orphan(name) {
    cur = { ...cur, id: null, typed: true, t: 0, rx: false, orphan: true };
    $('#mkTitle').textContent = 'New marker';
    $('#mkDel').hidden = true;
    $('#mkMove').hidden = true;
    $('#mkGo').textContent = 'Go to';
    shareEl.checked = false;
    if (opened) opened.share = false;
    conflict = `${name} deleted this marker for everyone. Save keeps what you typed as a private marker of your own.`;
    renderAge();
    renderShare();
  }
  let badges = !!(FK.mesh && FK.mesh.enabled());
  FK.on('mesh', () => {
    if (dlg.open && cur) renderShare();
    const now = FK.mesh.enabled();
    if (now !== badges) { badges = now; render(); if (ldlg.open) renderList(); }   // the corner marks come and go with the switch
  });
  FK.on('wps', () => { if (dlg.open && cur && !dlg.inert) renderShare(); });

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
        <i class="mk-ic${isStale(w) ? ' stale' : ''}">${glyph(w, { stale: isStale(w) })}${netBadge(w)}</i>
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
      renderShare();
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

  FK.markers = { icon, line: LINE, edit, create, openList, render, ageText, sendChange, timerOn: () => !!tick,
                 openId: () => (dlg.open && cur && cur.id) || null };
})();
