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

  /* The button warns (a "!" dot drawn in CSS) whenever Field Kit cannot share: the link is lost, the radio is connected on a
     channel that is not private, or it cannot transmit. Connected and sharing has no mark. */
  function look() {
    const s = FK.mesh.status().state, w = STATE[s] || 'off';
    if (s === 'lost') return { w, label: w, warn: true };
    if (s !== 'on') return { w, label: w, warn: false };
    const ch = FK.mesh.channel();
    if (ch === 'public') return { w, label: 'connected, not sharing (public channel)', warn: true };
    if (ch !== 'private') return { w, label: 'connected, not sharing', warn: true };
    if (FK.mesh.radioProblem()) return { w, label: 'connected, can’t transmit', warn: true };
    return { w, label: w, warn: false };
  }
  let shape = '';
  function drawButton() {
    if (!FK.mesh.enabled()) { dropButton(); return; }
    ensureButton();
    const k = look(), key = k.w + '|' + k.label + '|' + k.warn;
    if (key === shape) return;
    shape = key;
    btn.setAttribute('aria-label', 'Radio: ' + k.label);
    btn.title = 'Radio: ' + k.label;
    btn.classList.toggle('warn', k.warn);
    btn.innerHTML = FK.markers.line(ICON[k.w]);
  }

  /* ---- the sheet ---- */
  const show = (el, text) => { el.hidden = !text; el.textContent = text || ''; };
  const ageOf = t => FK.team.age(t).text;   // one rule with the map pins (tac-team.js)
  const relOf = (lat, lon) => FK.relText(lat, lon, m => TGEOM.fmtDist(m, FK.tac.unit())) || 'distance unknown';
  const distOf = m => { const f = FK.getFix(); return f && m.lat !== null ? GEO.distance(f.lat, f.lon, m.lat, m.lon) : null; };

  /* A row with a position is a button: it closes this sheet, centres the map on the teammate and opens the teammate sheet. */
  function rows(list) {
    const withPos = list.filter(m => m.lat !== null).map(m => ({ m, d: distOf(m) }));
    withPos.sort((a, b) => (a.d === null) - (b.d === null) || (a.d - b.d) || a.m.name.localeCompare(b.m.name));
    const none = list.filter(m => m.lat === null).sort((a, b) => a.name.localeCompare(b.name));
    return withPos.map(x => `<li><button type="button" data-num="${x.m.num}">${esc(x.m.name)} · ${esc(relOf(x.m.lat, x.m.lon))} · ${esc(ageOf(x.m.t))}</button></li>`)
      .concat(none.map(m => `<li>${esc(m.name)} · no position yet</li>`)).join('');
  }
  const PROBLEM = { region: 'This radio has no region set, so it can’t transmit. Set the region in the Meshtastic app.',
    txoff: 'This radio’s transmitter is switched off in its settings.' };

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
    $('#rdDisconnect').hidden = !isOn;   // always the quiet style; while lost, Connect again is the one action
    // what to do first, and why a connection failed
    const info = $('#rdInfo');
    if (s.state !== 'off') info.textContent = '';
    else if (unsupported) info.innerHTML = '<p>This phone’s browser can’t reach a radio. The Meshtastic app will still share your position and markers with the group.</p>';
    else info.innerHTML = '<p>You need a Meshtastic radio that is already set up in the Meshtastic app.</p><p>Close the Meshtastic app first: a radio talks to one app at a time.</p>';
    show($('#rdErr'), s.state === 'off' && s.reason === 'failed' ? 'Couldn’t connect. If the Meshtastic app is open, close it and try again.' : '');
    // the channel, only while the link is on (the last verdict is kept when it is lost)
    const ch = isOn ? FK.mesh.channel() : '', pos = isOn ? FK.mesh.positions() : '';
    show($('#rdChannel'), ch ? 'Channel: ' + ch : '');
    show($('#rdProblem'), isOn ? PROBLEM[FK.mesh.radioProblem()] || '' : '');
    show($('#rdWarn'), ch === 'public' ? 'This radio’s main channel is public, so Field Kit is not sending or showing anything. In the Meshtastic app, make your private channel the main (primary) one, share it with your group, then connect again.' : '');
    show($('#rdPos'), ch === 'private' && pos === 'off' ? 'This channel is set to send no positions: yours isn’t shared and teammates’ won’t arrive.'
      : ch === 'private' && pos === 'approx' ? 'This channel sends approximate positions, so teammates may show in the wrong place.' : '');
    /* Connected on the private channel: the teammates heard. Not connected: the stored list, as last known (the pins stay
       on the map too; none when the last verdict was a public channel, as on the map). */
    const stored = !isOn && FK.mesh.channel() !== 'public' ? FK.mesh.teammates() : [];
    const team = ch === 'private' ? FK.mesh.teammates() : stored.length ? stored : null;
    $('#rdTeamBox').hidden = !team;
    if (team) {
      $('#rdTeamH').textContent = isOn ? `Teammates (${team.length})` : `Teammates, last known (${team.length})`;
      $('#rdTeam').innerHTML = team.length ? rows(team) : '<li class="hint">No teammates heard yet.</li>';
    }
    // shared markers: the cap's line, and sending this phone's own shared markers again (src/tac-share.js)
    show($('#rdDropped'), FK.share.dropped() > 0 ? 'Some older markers from teammates were dropped: this phone holds 500.' : '');
    $('#rdResend').hidden = !(FK.mesh.canShare() && FK.tac.markers().some(m => m.net && FK.share.mine(m.id)));
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
  /* Send all my shared markers again: the button itself says what happens (a toast would sit behind this sheet), and it is
     disabled while its markers go out, one every few seconds. */
  const RESEND = 'Send all my shared markers again';
  const markersWord = n => `${n} ${n === 1 ? 'marker' : 'markers'}`;
  let resendTimer = 0;
  $('#rdResend').addEventListener('click', async () => {
    const b = $('#rdResend');
    if (b.disabled) return;
    clearTimeout(resendTimer);
    const n = FK.share.resendMine();
    if (!n) { b.textContent = 'Nothing to send'; resendTimer = setTimeout(() => { b.textContent = RESEND; }, 4000); return; }
    b.disabled = true;
    b.textContent = `Sending ${markersWord(n)}…`;
    await FK.share.whenIdle();
    const sent = FK.share.batchSent();
    b.disabled = false;
    b.textContent = sent >= n ? `Sent ${markersWord(n)}` : `Sent ${sent} of ${n}. The rest go out when the radio connects.`;
    resendTimer = setTimeout(() => { b.textContent = RESEND; }, 4000);
  });
  $('#rdTeam').addEventListener('click', e => {
    const b = e.target.closest('button[data-num]');
    if (!b) return;
    const num = Number(b.dataset.num), m = FK.mesh.teammates().find(x => x.num === num);
    if (!m || m.lat === null) return;
    FK.sheet.close(dlg);
    FK.mapShow(m.lat, m.lon);
    FK.team.open(num);   // FK.sheet.open waits for this sheet's step back
  });

  /* While the sheet is open its ages move on with the clock, not only when a teammate is heard. */
  let tick = 0;
  function open() {
    if (!FK.mesh.enabled()) return;
    FK.sheet.open(dlg, {
      onOpen: () => { drawSheet(); $('#rdTitle').focus(); clearInterval(tick); tick = setInterval(drawSheet, 60000); },
      onClose: () => { clearInterval(tick); tick = 0; if (btn && !(FK.sheet.top && FK.sheet.top())) btn.focus(); }
    });
  }

  on('mesh', () => { if (!FK.mesh.enabled() && dlg.open) FK.sheet.close(dlg); redraw(); });
  on('team', () => { if (dlg.open) redraw(); });
  on('wps', () => { if (dlg.open) redraw(); });
  drawButton();

  FK.radioSheet = { open };
})();
