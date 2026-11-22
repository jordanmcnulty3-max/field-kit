/* ---------- The Radio button on the map and the Radio sheet (FK.radioSheet) ----------
   The button exists only while the Settings switch is on (FK.mesh.enabled()). Its label and its icon shape follow the link:
   off, connecting (also while the radio's list downloads), connected, lost. The sheet connects and disconnects, and shows the
   channel, the warnings about it and the teammates. Redraws are coalesced to one per animation frame (a start-up download
   can send 100+ events in one tick) and the sheet is only redrawn while it is open. Every name comes from another person's
   radio, so everything that reaches innerHTML goes through FK.esc. */
(() => {
  const { $, esc, on } = FK;
  const dlg = $('#dlgRadio');
  /* The button is made here and only while the switch is on: with it off the map has its four buttons and nothing else. */
  let btn = null;
  function ensureButton() {
    if (btn) return btn;
    btn = document.createElement('button');
    btn.id = 'mRadio';
    btn.addEventListener('click', open);
    $('.mapctl').appendChild(btn);
    return btn;
  }
  const dropButton = () => { if (btn) { btn.remove(); btn = null; shape = ''; } };
  const STATE = { off: 'off', connecting: 'connecting', syncing: 'connecting', on: 'connected', lost: 'connection lost' };
  /* Lucide line icons (vendor/lucide/comms-icons.json), the inside of a 24 px icon; each state has its own shape. */
  const ICON = {
    off: '<path d="m17 17-5 5V12l-5 5"/><path d="m2 2 20 20"/><path d="M14.5 9.5 17 7l-5-5v4.5"/>',
    connecting: '<path d="m7 7 10 10-5 5V2l5 5L7 17"/><path d="M20.83 14.83a4 4 0 0 0 0-5.66"/><path d="M18 12h.01"/>',
    connected: '<path d="m7 7 10 10-5 5V2l5 5L7 17"/><line x1="18" x2="21" y1="12" y2="12"/><line x1="3" x2="6" y1="12" y2="12"/>',
    'connection lost': '<path d="m7 7 10 10-5 5V2l5 5L7 17"/>'
  };

  let shape = '';
  function drawButton() {
    if (!FK.mesh.enabled()) { dropButton(); return; }
    ensureButton();
    const w = STATE[FK.mesh.status().state] || 'off';
    if (w === shape) return;
    shape = w;
    btn.setAttribute('aria-label', 'Radio: ' + w);
    btn.title = 'Radio: ' + w;
    btn.innerHTML = FK.markers.line(ICON[w]);
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
    if (tapped) return;
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
    FK.sheet.open(dlg, { onOpen: () => { drawSheet(); $('#rdTitle').focus(); }, onClose: () => { if (btn) btn.focus(); } });
  }

  on('mesh', () => { if (!FK.mesh.enabled() && dlg.open) FK.sheet.close(dlg); redraw(); });
  on('team', () => { if (dlg.open) redraw(); });
  drawButton();

  FK.radioSheet = { open };
})();
