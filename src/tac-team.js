/* ---------- Teammates on the map (FK.team) ----------
   Each teammate with a position (FK.mesh.teammates()) is a blue ring with the radio's name and how long ago it was heard under
   it; not heard for 30 minutes, or the time unknown, it is dashed and hollow. Tapping one opens the Teammate sheet (read only:
   Go to, Close). The group is map._fkTeam, under the marker pins. Redraws from 'team' events are coalesced to one per animation
   frame (a start-up download sends 100+ in one tick) and happen only while the map exists; a one-minute timer, running only while
   the Settings switch is on and the map is showing, moves a pin past 30 minutes without waiting for news. Names come from other
   people's radios: everything that reaches innerHTML goes through FK.esc. */
(() => {
  const FK = window.FK;
  const { $, esc, on } = FK;
  const OLD_MS = 30 * 60000;
  const dlg = $('#dlgMate');

  /* The one rule for a teammate's age, used by the pins, the sheet and the Radio sheet's list: { text, old }.
     t is ms (0 = unknown). A time up to 2 min ahead of the phone clock is a radio clock a little fast: it counts as now
     (the youngest age, a fresh pin). Further ahead, or 0: "age unknown" and an old pin. Never a wrong age. */
  const SKEW_MS = 2 * 60000;
  function age(t, now = Date.now()) {
    if (!(t > 0) || t > now + SKEW_MS) return { text: 'age unknown', old: true };
    const at = Math.min(t, now);
    return { text: FK.markers.ageText(Date.now() - (now - at)), old: now - at > OLD_MS };
  }
  const shows = () => FK.mesh.enabled() && FK.mesh.channel() !== 'public';
  const list = () => shows() ? FK.mesh.teammates().filter(m => m.lat !== null && m.lon !== null) : [];
  /* The Lucide user-round icon (vendor/lucide/comms-icons.json). */
  const USER = '<circle cx="12" cy="8" r="5"/><path d="M20 21a8 8 0 0 0-16 0"/>';

  function render() {
    const map = FK.leafletMap();
    if (!map || !map._fkTeam) return;
    const g = map._fkTeam; g.clearLayers();
    list().forEach(m => {
      const { text: words, old } = age(m.t);
      const html = `<div class="tm-pin${old ? ' old' : ''}" data-num="${m.num}"><i>${FK.markers.line(USER)}</i><b>${esc(m.name)}</b><em>${esc(words)}</em></div>`;
      L.marker([m.lat, m.lon], { icon: L.divIcon({ className: 'tm-icon', iconSize: [30, 30], iconAnchor: [15, 15], html }),
        title: `${m.name}, ${words}`, zIndexOffset: -500 })   // marker pins have 0: theirs sit on top
        .on('click', () => { if (!(FK.mapTools && FK.mapTools.mode())) open(m.num); }).addTo(g);   // inert while a tool mode is on
    });
  }

  /* ---- the sheet ---- */
  let curNum = null;
  const find = num => list().find(m => m.num === num);
  const gridText = (lat, lon) => { const g = GEO.toMGRS(lat, lon); return g ? g.text : `${lat.toFixed(5)}, ${lon.toFixed(5)}`; };
  function fill() {
    const m = find(curNum);
    if (!m) { FK.sheet.close(dlg); return; }
    $('#tmTitle').textContent = m.name;
    $('#tmGrid').textContent = gridText(m.lat, m.lon);
    $('#tmApprox').hidden = !m.approx;   // the channel or the radio sends it with reduced precision (the pin looks the same)
    const rel = FK.relText(m.lat, m.lon, d => TGEOM.fmtDist(d, FK.tac.unit()));
    $('#tmRel').hidden = !rel; $('#tmRel').textContent = rel;
    const a = age(m.t);
    $('#tmAge').textContent = a.text === 'age unknown' ? 'Position time unknown' : `Position from ${a.text}`;
  }
  function open(num) {
    curNum = num;
    if (!find(num)) return;
    fill();
    FK.sheet.open(dlg, { onOpen: () => $('#tmTitle').focus(), onClose: () => { curNum = null; } });
  }
  $('#tmGo').addEventListener('click', () => {
    const m = find(curNum);
    if (m) FK.tac.setTarget({ type: 'point', lat: m.lat, lon: m.lon, name: m.name });
    FK.sheet.close(dlg);
  });
  $('#tmClose').addEventListener('click', () => FK.sheet.close(dlg));

  /* ---- redraws ---- */
  let queued = 0;
  function schedule() {
    if (queued) return;
    queued = requestAnimationFrame(() => { queued = 0; FK.team.render(); if (dlg.open && curNum !== null) fill(); });
  }
  let tick = 0;
  function syncTimer() {
    const want = FK.mesh.enabled() && !document.hidden && FK.tab() === 'tactical' && FK.view() === 'map';
    if (want && !tick) tick = setInterval(() => { FK.team.render(); if (dlg.open && curNum !== null) fill(); }, 60000);
    else if (!want && tick) { clearInterval(tick); tick = 0; }
  }
  on('team', schedule);
  on('mesh', () => { schedule(); syncTimer(); if (!FK.mesh.enabled() && dlg.open) FK.sheet.close(dlg); });
  on('shown', () => { syncTimer(); });
  on('unit', () => { if (dlg.open) fill(); });
  on('fix', () => { if (dlg.open && curNum !== null) schedule(); });
  document.addEventListener('visibilitychange', () => { syncTimer(); if (tick) FK.team.render(); });
  syncTimer();

  FK.team = { render, open, age, timerOn: () => !!tick };
})();
