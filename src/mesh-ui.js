/* ---------- The Radio button on the map and the Radio sheet (FK.radioSheet) ----------
   The button exists only while the Settings switch is on (FK.mesh.enabled()). Its label and its icon shape follow the link:
   off, connecting (also while the radio's list downloads), connected, lost. The sheet connects and disconnects, and shows the
   channel, the warnings about it and the teammates. Redraws are coalesced to one per animation frame (a start-up download
   can send 100+ events in one tick) and the sheet is only redrawn while it is open. Every name comes from another person's
   radio, so everything that reaches innerHTML goes through FK.esc. */
(() => {
  const { $, esc, on } = FK;
  const btn = $('#mRadio'), dlg = $('#dlgRadio');
  const STATE = { off: 'off', connecting: 'connecting', syncing: 'connecting', on: 'connected', lost: 'connection lost' };
  const MAST = '<path d="M12 12v9M9 21h6"/>';
  const ARCS = { in: '<path d="M8.5 6.5a5 5 0 0 0 0 7M15.5 6.5a5 5 0 0 1 0 7"/>', out: '<path d="M5.5 4a9 9 0 0 0 0 12M18.5 4a9 9 0 0 1 0 12"/>' };
  const ICON = {
    off: MAST + '<circle cx="12" cy="9" r="1.5"/><path d="M3 3l18 18"/>',
    connecting: MAST + '<circle cx="12" cy="10" r="1.5" fill="currentColor"/><g stroke-dasharray="2 3">' + ARCS.in + ARCS.out + '</g>',
    connected: MAST + '<circle cx="12" cy="10" r="1.5" fill="currentColor"/>' + ARCS.in + ARCS.out,
    'connection lost': MAST + '<circle cx="12" cy="10" r="1.5" fill="currentColor"/>' + ARCS.in + '<path d="M17 2l5 5M22 2l-5 5"/>'
  };
  const svg = d => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${d}</svg>`;

  let shape = '';
  function drawButton() {
    const en = FK.mesh.enabled();
    btn.hidden = !en;
    if (!en) { shape = ''; return; }
    const w = STATE[FK.mesh.status().state] || 'off';
    if (w === shape) return;
    shape = w;
    btn.setAttribute('aria-label', 'Radio: ' + w);
    btn.title = 'Radio: ' + w;
    btn.innerHTML = svg(ICON[w === 'off' ? 'off' : w]);
  }

  /* ---- the sheet ---- */
  const show = (el, text) => { el.hidden = !text; el.textContent = text || ''; };
  const ageOf = t => (t > 0 && FK.markers ? FK.markers.ageText(t) : '') || 'age unknown';
  const relOf = (lat, lon) => FK.relText(lat, lon, m => TGEOM.fmtDist(m, FK.tac.unit())) || 'distance unknown';
  const distOf = m => { const f = FK.getFix(); return f && m.lat !== null ? GEO.distance(f.lat, f.lon, m.lat, m.lon) : null; };

  function rows(list) {
    const withPos = list.filter(m => m.lat !== null).map(m => ({ m, d: distOf(m) }));
    withPos.sort((a, b) => (a.d === null) - (b.d === null) || (a.d - b.d) || a.m.name.localeCompare(b.m.name));
    const none = list.filter(m => m.lat === null).sort((a, b) => a.name.localeCompare(b.name));
    return withPos.map(x => `<li>${esc(x.m.name)} · ${esc(relOf(x.m.lat, x.m.lon))} · ${esc(ageOf(x.m.t))}</li>`)
      .concat(none.map(m => `<li>${esc(m.name)} · no position yet</li>`)).join('');
  }

  function drawSheet() {
    if (!dlg.open) return;
    const s = FK.mesh.status(), busy = s.state === 'connecting' || s.state === 'syncing', isOn = s.state === 'on', lost = s.state === 'lost';
    const connect = $('#rdConnect');
    const unsupported = s.state === 'off' && !FK.mesh.supported();
    // status line and the one action
    let status = '';
    if (busy) status = 'Connecting…';
    else if (isOn) status = `Connected to "${s.name}"`;
    else if (lost) status = 'Connection lost. Check that the radio is on and close by.';
    show($('#rdStatus'), status);
    connect.hidden = unsupported || isOn;
    connect.disabled = busy;
    connect.textContent = busy ? 'Connecting…' : lost ? 'Connect again' : 'Connect a radio';
    $('#rdDisconnect').hidden = !(isOn || lost);
    // what to do first, and why a connection failed
    const info = $('#rdInfo');
    if (s.state !== 'off') info.textContent = '';
    else if (unsupported) info.innerHTML = '<p>This phone’s browser can’t reach a radio. The Meshtastic app will still share your position and markers with the group.</p>';
    else info.innerHTML = '<p>You need a Meshtastic radio that is already set up in the Meshtastic app.</p><p>Close the Meshtastic app first: a radio talks to one app at a time.</p>';
    show($('#rdErr'), s.state === 'off' && s.reason === 'failed' ? 'Couldn’t connect. If the Meshtastic app is open, close it and try again.' : '');
    // the channel, only while the link is on (the last verdict is kept when it is lost)
    const ch = isOn ? FK.mesh.channel() : '', pos = isOn ? FK.mesh.positions() : '';
    show($('#rdChannel'), ch ? 'Channel: ' + ch : '');
    show($('#rdWarn'), ch === 'public' ? 'This radio is on a public channel, so Field Kit is not sending or showing anything. Set up a private channel in the Meshtastic app and share it with your group.' : '');
    show($('#rdPos'), ch === 'private' && pos === 'off' ? 'This channel is set to send no positions, so teammates won’t appear.'
      : ch === 'private' && pos === 'approx' ? 'This channel sends approximate positions, so teammates may show in the wrong place.' : '');
    const team = ch === 'private' ? FK.mesh.teammates() : null;
    $('#rdTeamBox').hidden = !team;
    if (team) {
      $('#rdTeamH').textContent = `Teammates (${team.length})`;
      $('#rdTeam').innerHTML = team.length ? rows(team) : '<li class="hint">No teammates heard yet.</li>';
    }
  }

  let queued = 0;
  function redraw() {
    if (queued) return;
    queued = requestAnimationFrame(() => { queued = 0; drawButton(); drawSheet(); });
  }

  let noDisc = 0, tapped = false;
  function connectTap() {
    if (tapped || btn.hidden) return;
    tapped = true;
    noDisc = performance.now() + 400;   // a second tap of a double tap must not land on Disconnect
    const s = FK.mesh.status().state;
    const p = s === 'lost' ? FK.mesh.reconnect() : FK.mesh.connect();   // called inside the tap: the device chooser needs it
    redraw();
    Promise.resolve(p).catch(e => console.warn('radio connect', e)).then(() => { tapped = false; redraw(); });
  }
  $('#rdConnect').addEventListener('click', connectTap);
  $('#rdDisconnect').addEventListener('click', () => { if (performance.now() >= noDisc) FK.mesh.disconnect(); });
  $('#rdClose').addEventListener('click', () => FK.sheet.close(dlg));

  function open() {
    if (!FK.mesh.enabled()) return;
    FK.sheet.open(dlg, { onOpen: () => { drawSheet(); $('#rdTitle').focus(); }, onClose: () => { if (!btn.hidden) btn.focus(); } });
  }
  btn.addEventListener('click', open);

  on('mesh', () => { if (!FK.mesh.enabled() && dlg.open) FK.sheet.close(dlg); redraw(); });
  on('team', () => { if (dlg.open) redraw(); });
  drawButton();

  FK.radioSheet = { open };
})();
