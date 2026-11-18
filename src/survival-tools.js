/* ---------- Survival tools: ordinary Survival pages at #/survival/tool/<name>, key u:<name>. Adding a tool is one entry in TOOLS. ---------- */
(() => {
  const FK = window.FK;

  /* name -> { label, keywords?, draw(el) }. draw fills el and may return a function that undoes everything it started;
     survival.js calls that on every way of leaving the page (Back, tab switch, opening another page). */
  const TOOLS = {
    sos: { label: 'SOS light', keywords: 'morse signal distress flash flashlight rescue screen light', draw: drawSos },
    daylight: { label: 'Daylight and moon', keywords: 'sunrise sunset sun moon moonrise moonset moon phase full moon new moon daylight day length twilight first light last light dawn dusk almanac', draw: drawDaylight }
  };

  /* ---------- SOS light ---------- */
  const UNIT_MS = 200;
  /* Morse S O S in units, alternating on and off and starting on: ... --- ... then 7 units off before it repeats. */
  const SOS_UNITS = [1, 1, 1, 1, 1, 3, 3, 1, 3, 1, 3, 3, 1, 1, 1, 1, 1, 7];
  const WARNING = 'A flashing screen can be seen from far away and gives away your position.';

  function drawSos(el) {
    el.innerHTML = '<p class="sv-warn"><strong>Warning:</strong> ' + FK.esc(WARNING) + '</p>' +
      '<div class="sv-sos-btns"><button type="button" class="btn" id="svSosStart" aria-describedby="svSosNote">Start SOS</button>' +
      '<button type="button" class="btn ghost" id="svSosSteady">Steady light</button></div>' +
      '<p id="svSosNote" class="sv-cnote">Flashes the whole screen white in Morse S O S, or holds it steadily lit, and keeps the screen awake. ' +
      'Reduced motion settings do not change the flashing: it is how the light signals. Tap the screen to stop.</p>' +
      '<button type="button" class="sv-light" hidden data-on="0" aria-label="Stop the light"><span>Tap to stop</span></button>';
    const startBtn = el.querySelector('#svSosStart'), steadyBtn = el.querySelector('#svSosSteady'), panel = el.querySelector('.sv-light');
    let running = false, timer = null, opener = null, lock = null, lockPending = false;

    /* Screen wake lock, the same guards as the protocol player: no API, a refused request or a stop before it answers all leave the screen as it was. */
    async function wakeOn() {
      if (lock || lockPending || !running || document.hidden || !navigator.wakeLock) return;
      lockPending = true;
      try {
        const l = await navigator.wakeLock.request('screen');
        if (!running) { l.release().catch(() => {}); return; }
        lock = l;
        l.addEventListener('release', () => { if (lock === l) lock = null; });
      } catch { /* denied: the screen times out as usual */ }
      finally { lockPending = false; }
    }
    function wakeOff() { if (lock) { const l = lock; lock = null; l.release().catch(() => {}); } }

    const light = on => { panel.dataset.on = on ? '1' : '0'; };
    function flash(i) {
      light(i % 2 === 0);
      timer = setTimeout(() => flash((i + 1) % SOS_UNITS.length), SOS_UNITS[i] * UNIT_MS);
    }
    function begin(steady, from) {
      if (running) return;
      running = true; opener = from;
      startBtn.textContent = 'Stop SOS';
      panel.hidden = false;
      document.addEventListener('visibilitychange', onVisibility);
      wakeOn();
      if (steady) light(true); else flash(0);
      panel.focus();
    }
    function end(refocus) {
      if (!running) return;
      running = false;
      clearTimeout(timer); timer = null;
      document.removeEventListener('visibilitychange', onVisibility);
      wakeOff();
      light(false);
      panel.hidden = true;
      startBtn.textContent = 'Start SOS';
      if (refocus && opener && opener.isConnected) opener.focus();
      opener = null;
    }
    function onVisibility() { if (document.hidden) end(true); }   // a hidden tab cannot show the light, so it stops rather than flash unseen

    startBtn.addEventListener('click', () => { if (running) end(true); else begin(false, startBtn); });
    steadyBtn.addEventListener('click', () => begin(true, steadyBtn));
    panel.addEventListener('click', () => end(true));
    return () => end(false);
  }

  /* ---------- Daylight and moon ----------
     Sun and moon times for today and the next six days, worked out on the phone by FK_ASTRO (src/astro.js) from the
     last GPS fix (read only; this page never starts GPS) or from a position the user typed, which is kept as
     daylightPos = { lat, lon, on } and used only while on is true. */
  const NO_POS = 'No position yet. Get a fix on the Position screen, or type one here.';
  const DASH = '<span aria-hidden="true">—</span><span class="dl-sr">none this day</span>';
  const SUN_RISE_ALT = -0.833, CIVIL_ALT = -6;

  const validFix = () => { const f = FK.store.get('lastFix', null); return f && typeof f === 'object' && FK.okLatLon(f.lat, f.lon) && FK.fin(f.t) ? f : null; };
  const validTyped = () => { const p = FK.store.get('daylightPos', null); return p && typeof p === 'object' && FK.okLatLon(p.lat, p.lon) ? { lat: p.lat, lon: p.lon, on: p.on === true } : null; };
  /* A typed coordinate: plain decimal degrees, a typographic minus allowed. */
  function parseDeg(text, limit) {
    const t = String(text).trim().replace(/−/g, '-');
    if (!/^[+-]?(\d+(\.\d*)?|\.\d+)$/.test(t)) return null;
    const v = parseFloat(t);
    return Math.abs(v) <= limit ? v : null;
  }
  function ago(ms) {
    const min = Math.floor(Math.max(0, ms) / 60000);
    if (min < 1) return 'less than a minute ago';
    if (min < 60) return min + ' min ago';
    const h = Math.floor(min / 60);
    return h < 48 ? h + ' h ago' : Math.floor(h / 24) + ' days ago';
  }
  const coords = p => p.lat.toFixed(4) + ', ' + p.lon.toFixed(4);

  function drawDaylight(el) {
    const A = window.FK_ASTRO;
    const timeFmt = new Intl.DateTimeFormat(undefined, { hour: 'numeric', minute: '2-digit' });
    const dayFmt = new Intl.DateTimeFormat(undefined, { weekday: 'short', month: 'short', day: 'numeric' });
    let editing = false;

    const time = ms => ms === null ? DASH : FK.esc(timeFmt.format(new Date(ms)));
    const length = ms => { const m = Math.round(ms / 60000); return Math.floor(m / 60) + ' h ' + (m % 60) + ' min'; };
    const row = (k, label, value) => '<div data-k="' + k + '"><dt>' + FK.esc(label) + '</dt><dd>' + value + '</dd></div>';

    function dayCard(i, start, lat, lon) {
      const s = A.sun(start, lat, lon), m = A.moon(start, lat, lon);
      const midAlt = A.sunAlt(start + 12 * 3600000, lat, lon);   // with no crossing all day, any moment tells up or down
      let rise = time(s.rise), set = time(s.set), dawn = time(s.dawn), dusk = time(s.dusk);
      if (s.rise === null && s.set === null) {
        if (midAlt > SUN_RISE_ALT) { rise = 'Up all day'; set = 'Does not set'; } else { rise = 'Does not rise'; set = 'Down all day'; }
      }
      if (s.dawn === null && s.dusk === null) dawn = dusk = midAlt > CIVIL_ALT ? 'Light all night' : 'Dark all day';
      const name = (i === 0 ? 'Today · ' : i === 1 ? 'Tomorrow · ' : '') + dayFmt.format(new Date(start));
      return '<section class="dl-day" aria-labelledby="dlDay' + i + '"><h3 id="dlDay' + i + '">' + FK.esc(name) + '</h3><dl>' +
        row('dawn', 'First light', dawn) + row('rise', 'Sunrise', rise) + row('set', 'Sunset', set) + row('dusk', 'Last light', dusk) +
        row('len', 'Day length', FK.esc(length(A.dayLength(start, lat, lon)))) +
        row('moonrise', 'Moonrise', time(m.rise)) + row('moonset', 'Moonset', time(m.set)) +
        row('phase', 'Moon', FK.esc(m.name + ', ' + Math.round(m.illum * 100) + '% lit')) + '</dl></section>';
    }

    function render() {
      const fix = validFix(), typed = validTyped();
      const use = typed && typed.on ? { ...typed, kind: 'typed' } : fix ? { lat: fix.lat, lon: fix.lon, kind: 'gps', t: fix.t } : null;
      let html = '<div class="dl-pos">';
      if (use && use.kind === 'gps') {
        html += '<p><strong>Last GPS fix</strong>, ' + FK.esc(ago(Date.now() - use.t)) + ': ' + FK.esc(coords(use)) + '</p>';
        if (!editing) html += '<div class="row"><button type="button" class="btn ghost" data-act="type">Type a position</button></div>';
      } else if (use) {
        html += '<p><strong>Typed position</strong>: ' + FK.esc(coords(use)) + '</p>';
        if (!editing) html += '<div class="row"><button type="button" class="btn ghost" data-act="type">Change position</button>' +
          (fix ? '<button type="button" class="btn ghost" data-act="gps">Use last GPS fix</button>' : '') + '</div>';
      } else {
        html += '<p>' + FK.esc(NO_POS) + '</p>';
      }
      html += '</div>';
      if (!use || editing) {
        const pre = typed || { lat: '', lon: '' };
        html += '<form class="dl-form" novalidate><div class="grid2">' +
          '<label class="f">Latitude<input id="dlLat" type="text" inputmode="decimal" autocomplete="off" spellcheck="false" aria-describedby="dlHint" value="' + FK.esc(pre.lat) + '"></label>' +
          '<label class="f">Longitude<input id="dlLon" type="text" inputmode="decimal" autocomplete="off" spellcheck="false" aria-describedby="dlHint" value="' + FK.esc(pre.lon) + '"></label></div>' +
          '<p id="dlHint" class="sv-cnote">Decimal degrees. North and east are positive, south and west negative: Syracuse is 43.05, -76.15.</p>' +
          '<p class="dl-err" role="alert"></p>' +
          '<div class="row"><button type="submit" class="btn">Use this position</button>' +
          (use ? '<button type="button" class="btn ghost" data-act="cancel">Cancel</button>' : '') + '</div></form>';
      }
      if (use) {
        const now = new Date(), cards = [];
        for (let i = 0; i < 7; i++) cards.push(dayCard(i, new Date(now.getFullYear(), now.getMonth(), now.getDate() + i).getTime(), use.lat, use.lon));
        html += '<p class="sv-cnote">Times are in this phone’s time zone. First and last light are civil twilight, when the sun is 6° below the horizon.</p>' +
          '<div class="dl-days">' + cards.join('') + '</div>';
      }
      el.innerHTML = html;
    }

    function submit() {
      const latIn = el.querySelector('#dlLat'), lonIn = el.querySelector('#dlLon'), err = el.querySelector('.dl-err');
      const lat = parseDeg(latIn.value, 90), lon = parseDeg(lonIn.value, 180);
      latIn.removeAttribute('aria-invalid'); lonIn.removeAttribute('aria-invalid');
      const bad = lat === null ? [latIn, 'Latitude must be a number from -90 to 90.'] : lon === null ? [lonIn, 'Longitude must be a number from -180 to 180.'] : null;
      if (bad) { bad[0].setAttribute('aria-invalid', 'true'); err.textContent = bad[1]; bad[0].focus(); return; }
      FK.store.set('daylightPos', { lat, lon, on: true });
      editing = false;
      render();
    }

    el.addEventListener('submit', e => { e.preventDefault(); submit(); });
    el.addEventListener('click', e => {
      const act = e.target.closest('[data-act]');
      if (!act) return;
      if (act.dataset.act === 'type') { editing = true; render(); el.querySelector('#dlLat').focus(); }
      else if (act.dataset.act === 'cancel') { editing = false; render(); }
      else if (act.dataset.act === 'gps') { const t = validTyped(); if (t) FK.store.set('daylightPos', { lat: t.lat, lon: t.lon, on: false }); render(); }
    });
    render();
  }

  /* ---------- Registration ---------- */
  FK.survival.tools = () => Object.entries(TOOLS).map(([name, t]) => ({ name, label: t.label, ...(t.keywords ? { keywords: t.keywords } : {}) }));
  FK.survival.registerPage('tool', (name, el) => {
    if (!Object.hasOwn(TOOLS, name)) return false;
    const t = TOOLS[name];
    el.innerHTML = '<article class="sv-page" data-tool="' + FK.esc(name) + '">' + FK.survival.headHTML('u:' + name, { title: t.label }) + '<div class="sv-tool"></div></article>';
    const out = t.draw(el.querySelector('.sv-tool'));
    FK.recent.add('u:' + name);
    return typeof out === 'function' ? out : undefined;
  });
  FK.survival.homeItems('tool', () => FK.survival.tools().map(t => ({ key: 'u:' + t.name, title: t.label })));
})();
