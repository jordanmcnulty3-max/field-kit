/* ---------- Survival tools: ordinary Survival pages at #/survival/tool/<name>, key u:<name>. Adding a tool is one entry in TOOLS. ---------- */
(() => {
  const FK = window.FK;

  /* name -> { label, keywords?, draw(el) }. draw fills el and may return a function that undoes everything it started;
     survival.js calls that on every way of leaving the page (Back, tab switch, opening another page). */
  const TOOLS = {
    sos: { label: 'SOS light', keywords: 'morse signal distress flash flashlight rescue screen light', draw: drawSos },
    daylight: { label: 'Daylight and moon', keywords: 'sunrise sunset sun moon moonrise moonset moon phase full moon new moon daylight day length twilight first light last light dawn dusk almanac', draw: drawDaylight },
    water: { label: 'Water planner', keywords: 'water how much water drinking water gallons litres liters storage store stock up emergency supply jugs containers drums barrels group people days calculator', draw: drawWater },
    windchill: { label: 'Wind chill', keywords: 'wind chill windchill feels like how cold frostbite frostbite time exposed skin cold weather temperature wind speed mph freezing winter exposure chart national weather service', draw: drawWindChill }
  };

  /* ---------- Water planner ----------
     People and days (the saved group) in; the water to store out, in gallons and litres, pounds and container counts.
     Every number comes from FK_DATA.tooldata.water (src/tooldata/water.json, sourced and release-gated). Missing, draft or
     unusable data shows no totals at all: the planner never falls back to a number nobody sourced. */
  const NO_WATER_DATA = 'The water planner’s numbers are not available yet. No totals are shown until they have been checked against sources.';
  const GALLONS = /^gal(lons?)?$/i;
  const EXTRA = /^extra[A-Z][A-Za-z0-9]*PerPersonDay$/;
  const plain = v => !!v && typeof v === 'object' && !Array.isArray(v);
  const filled = v => typeof v === 'string' && v.trim() !== '';
  function waterData() {
    const all = window.FK_DATA && plain(window.FK_DATA.tooldata) ? window.FK_DATA.tooldata : null;
    const w = all && Object.hasOwn(all, 'water') ? all.water : null;
    if (!plain(w) || w.draft === true || !plain(w.values)) return null;
    const val = name => { const v = Object.hasOwn(w.values, name) ? w.values[name] : null; return plain(v) && FK.fin(v.value) && v.value > 0 ? v : null; };
    const drink = val('drinkPerPersonDay'), lpg = val('litersPerGallon'), lbg = val('lbPerGallon');
    if (!drink || !GALLONS.test(String(drink.unit)) || !lpg || !lbg) return null;
    // physical constants: a slipped decimal point must not give a plausible, understated weight or volume
    if (lbg.value < 8.2 || lbg.value > 8.4 || lpg.value < 3.78 || lpg.value > 3.79) return null;
    const extras = Object.keys(w.values).filter(k => EXTRA.test(k)).map(k => ({ k, v: val(k) }))
      .filter(x => x.v && GALLONS.test(String(x.v.unit)) && filled(x.v.note));
    return { w, drink, lpg: lpg.value, lbg: lbg.value, extras };
  }

  function drawWater(el) {
    const S = FK.survival, esc = FK.esc, d = waterData();
    if (!d) { el.innerHTML = '<p class="sv-warn">' + esc(NO_WATER_DATA) + '</p>'; return; }
    const on = new Set();   // extras chosen for today: not saved, they describe the situation now
    const perDay = () => d.extras.reduce((s, x) => s + (on.has(x.k) ? x.v.value : 0), d.drink.value);
    const n = v => S.fmt(Number(v.toPrecision(12)));   // a figure from the data, shown as it is
    const counted = (v, one, many) => S.fmt(v) + ' ' + (v === 1 ? one : many);
    function totals(g) {
      const gal = S.roundUp(g.people * g.days * perDay());
      const t = { gal, litres: S.roundUp(gal * d.lpg), lb: S.roundUp(gal * d.lbg), jugs: gal, fives: Math.ceil(gal / 5), drums: Math.ceil(gal / 55) };
      return Object.values(t).every(Number.isSafeInteger) ? t : null;   // null: too large to show exactly, so no totals
    }
    const sources = (Array.isArray(d.w.sources) ? d.w.sources : []).filter(s => plain(s) && filled(s.name)).map(s => s.name);
    const row = (k, label, value) => '<div><dt>' + label + '</dt><dd data-k="' + k + '">' + esc(value) + '</dd></div>';
    el.innerHTML = '<div class="sv-gwrap"></div>' +
      (d.extras.length ? '<fieldset class="wp-extras"><legend>Add for today’s conditions</legend>' + d.extras.map(x =>
        '<label class="sv-check"><input type="checkbox" data-extra="' + esc(x.k) + '"><span>' + esc(x.v.note) + '</span></label>').join('') + '</fieldset>' : '') +
      '<section class="wp-out" aria-labelledby="wpTitle"><h3 id="wpTitle">Water to store</h3><div class="wp-res"></div><p class="wp-basis"></p>' +
      [d.w.title, d.drink.note].filter(filled).map(t => '<p class="wp-note">' + esc(t) + '</p>').join('') + '</section>' + S.footHTML(d.w);   // what the total covers and does not, in the data's words
    const res = el.querySelector('.wp-res'), basis = el.querySelector('.wp-basis');
    function render(g) {
      const t = totals(g), extra = perDay() - d.drink.value;
      if (!t) { res.innerHTML = '<p class="sv-warn">' + esc(NO_WATER_DATA) + '</p>'; basis.textContent = ''; return; }
      res.innerHTML = '<p class="wp-big"><span data-k="gal">' + esc(counted(t.gal, 'gallon', 'gallons')) + '</span> <span class="wp-l">(<span data-k="litres">' + esc(counted(t.litres, 'litre', 'litres')) + '</span>)</span></p>' +
        '<dl>' + row('lb', 'Weight', S.fmt(t.lb) + ' lb') + row('jugs', '1-gallon jugs', counted(t.jugs, 'jug', 'jugs')) +
        row('fives', '5-gallon containers', counted(t.fives, 'container', 'containers')) + row('drums', '55-gallon drums', counted(t.drums, 'drum', 'drums')) + '</dl>';
      basis.textContent = 'Based on ' + n(d.drink.value) + ' gal per person per day' + (extra > 0 ? ', plus ' + n(extra) + ' gal for today’s conditions' : '') +
        ', for ' + S.groupWords(g) + '.' + (sources.length ? ' Source: ' + sources[0] + (sources.length > 1 ? ', and ' + (sources.length - 1) + ' more under Sources.' : '.') : '');
    }
    const ed = S.mountGroup(el.querySelector('.sv-gwrap'), g => { const t = totals(g); return !t ? NO_WATER_DATA : counted(t.gal, 'gallon', 'gallons') + ' (' + counted(t.litres, 'litre', 'litres') + ') for ' + S.groupWords(g); }, render);
    el.addEventListener('change', e => {
      const b = e.target.closest('[data-extra]');
      if (!b) return;
      if (b.checked) on.add(b.dataset.extra); else on.delete(b.dataset.extra);
      render(S.group());
      ed.refresh();
    });
    render(S.group());
    return ed.stop;
  }

  /* ---------- Wind chill ----------
     Air temperature (whole °F) and wind (whole mph) in; "feels like" out, with the frostbite time the chart shades for that cell.
     Every number comes from FK_DATA.tooldata.windchill (src/tooldata/windchill.json, sourced and release-gated) and is checked
     again here: missing, draft or damaged data shows no figure at all. */
  const NO_WC_DATA = 'The wind chill tool’s numbers are not available yet. Nothing is shown until they have been checked against sources.';
  const OFF_CHART = 'Off the National Weather Service chart. No figure is shown.';
  const WHOLE = 'Enter a whole number.';
  const WC_CONSTS = ['c0', 'cT', 'cV', 'cTV', 'exp'];
  const numArr = a => Array.isArray(a) && a.length > 0 && a.every(FK.fin);
  const rising = a => a.every((x, i) => i === 0 || x > a[i - 1]);
  function windChillData() {
    const all = window.FK_DATA && plain(window.FK_DATA.tooldata) ? window.FK_DATA.tooldata : null;
    const w = all && Object.hasOwn(all, 'windchill') ? all.windchill : null;
    if (!plain(w) || w.draft === true || !plain(w.values) || !plain(w.grid)) return null;
    const c = {};
    for (const k of WC_CONSTS) {
      const v = Object.hasOwn(w.values, k) ? w.values[k] : null;
      if (!plain(v) || !FK.fin(v.value)) return null;
      c[k] = v.value;
    }
    const g = w.grid, { temps, winds, chill, bands, bandMinutes } = g;
    if (!numArr(temps) || !numArr(winds) || !numArr(bandMinutes)) return null;
    if (!rising(temps.slice().reverse()) || !rising(winds) || winds[0] <= 0) return null;   // temps strictly descending, winds strictly ascending and above 0
    if (!rising(bandMinutes) || bandMinutes[0] <= 0) return null;
    const grid = x => Array.isArray(x) && x.length === winds.length && x.every(r => Array.isArray(r) && r.length === temps.length);
    if (!grid(chill) || !grid(bands) || !chill.every(r => r.every(FK.fin))) return null;
    if (!bands.every(r => r.every(b => b === 0 || bandMinutes.includes(b)))) return null;
    return { w, c, temps, winds, bands };
  }
  /* A typed field: an optional minus and digits, after trimming. Anything else (blank, 12.7, 1e9, abc) is null. */
  const wholeNumber = text => { const t = String(text).trim(); return /^-?\d+$/.test(t) ? Number(t) : null; };

  function drawWindChill(el) {
    const S = FK.survival, esc = FK.esc, d = windChillData();
    if (!d) { el.innerHTML = '<p class="sv-warn">' + esc(NO_WC_DATA) + '</p>'; return; }
    const { c, temps, winds, bands } = d;
    const hi = temps[0], lo = temps[temps.length - 1];
    const field = (k, id, label, less, more) => '<div class="wc-row"><div class="sv-gfield"><label for="' + id + '">' + label + '</label><div class="sv-step">' +
      '<button type="button" data-wstep="' + k + '" data-d="-1" aria-label="' + less + '">−</button>' +
      '<input id="' + id + '" type="text" inputmode="numeric" autocomplete="off" spellcheck="false" data-wfield="' + k + '" aria-describedby="' + id + 'Err">' +
      '<button type="button" data-wstep="' + k + '" data-d="1" aria-label="' + more + '">+</button></div></div>' +
      '<p class="dl-err wc-err" id="' + id + 'Err" role="status"></p></div>';
    const sources = (Array.isArray(d.w.sources) ? d.w.sources : []).filter(s => plain(s) && filled(s.name)).map(s => s.name);
    const links = ['s:surv-wind-chill', 'p:hypothermia', 'p:frostbite'].map(k => [k, FK.search && FK.search.describe(k)]).filter(([, t]) => t && filled(t.title))
      .map(([k, t]) => '<button type="button" class="sv-link" data-link="' + esc(k) + '"><span>' + esc(t.title) + '</span></button>').join('');
    el.innerHTML = '<fieldset class="sv-group"><legend>Conditions</legend>' +
      field('temp', 'wcT', 'Air temperature (°F)', 'One degree colder', 'One degree warmer') + field('wind', 'wcV', 'Wind (mph)', 'One mph less', 'One mph more') + '</fieldset>' +
      '<section class="wp-out" aria-labelledby="wcTitle"><h3 id="wcTitle">Result</h3><div class="wc-res" role="status"></div></section>' +
      (links ? '<div class="wc-links">' + links + '</div>' : '') + S.footHTML(d.w);
    const input = k => el.querySelector('[data-wfield="' + k + '"]');
    const res = el.querySelector('.wc-res');
    const touched = { temp: false, wind: false };

    function compute(T, V) {
      if (T > hi || T < lo || V > winds[winds.length - 1] || V < winds[0]) return null;
      const e = Math.pow(V, c.exp);
      const chill = Math.round(c.c0 + c.cT * T - c.cV * e + c.cTV * T * e);
      const ti = temps.findIndex(x => x <= T), wi = winds.findIndex(x => x >= V);   // the next colder chart temperature, the next higher chart wind
      return Number.isFinite(chill) && ti >= 0 && wi >= 0 ? { chill, band: bands[wi][ti] } : null;
    }
    function render() {
      const v = { temp: wholeNumber(input('temp').value), wind: wholeNumber(input('wind').value) };
      for (const k of ['temp', 'wind']) {
        const bad = touched[k] && v[k] === null, i = input(k);
        el.querySelector('#' + i.id + 'Err').textContent = bad ? WHOLE : '';
        if (bad) i.setAttribute('aria-invalid', 'true'); else i.removeAttribute('aria-invalid');
      }
      if (v.temp === null || v.wind === null) { res.innerHTML = ''; return; }
      const r = compute(v.temp, v.wind);
      if (!r) { res.innerHTML = '<p class="sv-warn">' + esc(OFF_CHART) + '</p>'; return; }
      const line = r.band ? 'Frostbite possible in about ' + r.band + ' minutes on exposed skin' : d.w.title;   // no band: the data's own wording
      if (!filled(line)) { res.innerHTML = '<p class="sv-warn">' + esc(NO_WC_DATA) + '</p>'; return; }
      res.innerHTML = '<p class="wp-big" data-k="chill">' + esc('Feels like ' + r.chill + '°F') + '</p><p data-k="band">' + esc(line) + '</p>' +
        (sources.length ? '<p class="wp-basis">' + esc('Source: ' + sources[0]) + '</p>' : '');
    }
    const touch = k => { touched[k] = true; render(); };
    el.addEventListener('input', e => { const i = e.target.closest('[data-wfield]'); if (i) touch(i.dataset.wfield); });
    el.addEventListener('change', e => { const i = e.target.closest('[data-wfield]'); if (i) touch(i.dataset.wfield); });
    el.addEventListener('click', e => {
      const b = e.target.closest('[data-wstep]');
      if (!b) return;
      const i = input(b.dataset.wstep), n = wholeNumber(i.value);
      i.value = String((n === null ? 0 : n) + Number(b.dataset.d));   // a blank or unreadable field starts from 0
      touch(b.dataset.wstep);
    });
  }

  /* ---------- SOS light ---------- */
  const UNIT_MS = 200;
  /* Morse S O S in units, alternating on and off and starting on: ... --- ... then 7 units off before it repeats. */
  const SOS_UNITS = [1, 1, 1, 1, 1, 3, 3, 1, 3, 1, 3, 3, 1, 1, 1, 1, 1, 7];
  const WARNING = 'A flashing screen can be seen from far away and gives away your position.';
  /* Whether a light is on, for the update bar: its Reload would end the light (app.js waits while this is true). */
  let lightRunning = false;
  const setLight = on => { if (lightRunning !== on) { lightRunning = on; FK.emit('activity'); } };

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
      startBtn.textContent = steady ? 'Stop light' : 'Stop SOS';
      panel.hidden = false;
      document.addEventListener('visibilitychange', onVisibility);
      document.addEventListener('keydown', onKey);
      wakeOn();
      if (steady) light(true); else flash(0);
      panel.focus();
      setLight(true);
    }
    function end(refocus) {
      if (!running) return;
      running = false;
      clearTimeout(timer); timer = null;
      document.removeEventListener('visibilitychange', onVisibility);
      document.removeEventListener('keydown', onKey);
      wakeOff();
      light(false);
      panel.hidden = true;
      startBtn.textContent = 'Start SOS';
      if (refocus && opener && opener.isConnected) opener.focus();
      opener = null;
      setLight(false);
    }
    function onVisibility() { if (document.hidden) end(true); }   // a hidden tab cannot show the light, so it stops rather than flash unseen
    function onKey(e) { if (e.key === 'Escape') { e.preventDefault(); end(true); } }

    startBtn.addEventListener('click', () => { if (running) end(true); else begin(false, startBtn); });
    steadyBtn.addEventListener('click', () => begin(true, steadyBtn));
    panel.addEventListener('click', () => end(true));
    return () => end(false);
  }

  /* ---------- Daylight and moon ----------
     Sun and moon times for today and the next six days, worked out on the phone by FK_ASTRO (src/astro.js) from the
     last GPS fix (read only; this page never starts GPS) or from a position the user typed, which is kept as
     daylightPos = { lat, lon, on } and used only while on is true. */
  const NO_POS_HTML = 'No position yet. Get a fix on the <button type="button" class="dl-inline" data-act="position">Position screen</button>, or type one here.';
  const DASH = '<span aria-hidden="true">—</span><span class="dl-sr">none this day</span>';

  const validFix = () => { const f = FK.store.get('lastFix', null); return f && typeof f === 'object' && FK.okLatLon(f.lat, f.lon) && FK.fin(f.t) ? f : null; };
  const validTyped = () => { const p = FK.store.get('daylightPos', null); return p && typeof p === 'object' && FK.okLatLon(p.lat, p.lon) ? { lat: p.lat, lon: p.lon, on: p.on === true } : null; };
  /* A typed coordinate: plain decimal degrees with no sign (the direction is chosen beside it); a comma works as the decimal point. */
  function parseDeg(text, limit) {
    const t = String(text).trim().replace(',', '.');
    if (!/^(\d+(\.\d*)?|\.\d+)$/.test(t)) return null;
    const v = parseFloat(t);
    return v <= limit ? v : null;
  }
  const signed = (v, negative) => (negative && v ? -v : v);
  function ago(ms) {
    const min = Math.floor(Math.max(0, ms) / 60000);
    if (min < 1) return 'less than a minute ago';
    if (min < 60) return min + ' min ago';
    const h = Math.floor(min / 60);
    return h < 48 ? h + ' h ago' : Math.floor(h / 24) + ' days ago';
  }
  const coords = p => Math.abs(p.lat).toFixed(4) + '° ' + (p.lat < 0 ? 'S' : 'N') + ', ' + Math.abs(p.lon).toFixed(4) + '° ' + (p.lon < 0 ? 'W' : 'E');
  /* A number field and its two-way direction choice. Stored positions stay signed degrees; the form shows size and direction. */
  function coordField(id, label, value, dirs, on) {
    const radio = ([v, name]) => '<label><input type="radio" name="' + id + 'Dir" value="' + v + '" aria-label="' + name + '"' + (v === on ? ' checked' : '') + '><span aria-hidden="true">' + v + '</span></label>';
    return '<div class="dl-coord"><label class="f">' + label + '<input id="' + id + '" type="text" inputmode="decimal" autocomplete="off" spellcheck="false" aria-describedby="dlHint" value="' + FK.esc(value) + '"></label>' +
      '<div class="dl-dir" role="radiogroup" aria-label="' + label + ': ' + dirs[0][1].toLowerCase() + ' or ' + dirs[1][1].toLowerCase() + '">' + dirs.map(radio).join('') + '</div></div>';
  }

  function drawDaylight(el) {
    const A = window.FK_ASTRO;
    const timeFmt = new Intl.DateTimeFormat(undefined, { hour: 'numeric', minute: '2-digit' });
    const dayFmt = new Intl.DateTimeFormat(undefined, { weekday: 'short', month: 'short', day: 'numeric' });
    let editing = false, kept = null, shownDay = '';   // kept: the last position accepted on this page, used if storage could not keep it
    const typedPos = () => kept || validTyped();
    const dayKey = () => new Date().toDateString();

    const time = ms => ms === null ? DASH : FK.esc(timeFmt.format(new Date(ms)));
    const length = ms => { const m = Math.round(ms / 60000); return Math.floor(m / 60) + ' h ' + (m % 60) + ' min'; };
    const row = (k, label, value) => '<div data-k="' + k + '"><dt>' + FK.esc(label) + '</dt><dd>' + value + '</dd></div>';

    function dayCard(i, start, lat, lon) {
      const s = A.sun(start, lat, lon), m = A.moon(start, lat, lon);
      const midAlt = A.sunAlt(start + 12 * 3600000, lat, lon);   // with no crossing all day, any moment tells up or down
      let rise = time(s.rise), set = time(s.set), dawn = time(s.dawn), dusk = time(s.dusk);
      if (s.rise === null && s.set === null) {
        if (midAlt > A.SUN_RISE_ALT) { rise = 'Up all day'; set = 'Does not set'; } else { rise = 'Does not rise'; set = 'Down all day'; }
      }
      if (s.dawn === null && s.dusk === null) dawn = dusk = midAlt > A.CIVIL_ALT ? 'Light all night' : 'Dark all day';
      const name = (i === 0 ? 'Today · ' : i === 1 ? 'Tomorrow · ' : '') + dayFmt.format(new Date(start));
      return '<section class="dl-day" aria-labelledby="dlDay' + i + '"><h3 id="dlDay' + i + '">' + FK.esc(name) + '</h3><dl>' +
        row('dawn', 'First light', dawn) + row('rise', 'Sunrise', rise) + row('set', 'Sunset', set) + row('dusk', 'Last light', dusk) +
        row('len', 'Day length', FK.esc(length(A.dayLength(start, lat, lon)))) +
        row('moonrise', 'Moonrise', time(m.rise)) + row('moonset', 'Moonset', time(m.set)) +
        row('phase', 'Moon', FK.esc(m.name + ', ' + Math.round(m.illum * 100) + '% lit')) + '</dl></section>';
    }

    function render() {
      const fix = validFix(), typed = typedPos();
      shownDay = dayKey();
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
        html += '<p>' + NO_POS_HTML + '</p>';
      }
      html += '</div>';
      if (!use || editing) {
        html += '<form class="dl-form" novalidate>' +
          coordField('dlLat', 'Latitude', typed ? Math.abs(typed.lat) : '', [['N', 'North'], ['S', 'South']], typed && typed.lat < 0 ? 'S' : 'N') +
          coordField('dlLon', 'Longitude', typed ? Math.abs(typed.lon) : '', [['W', 'West'], ['E', 'East']], typed && typed.lon >= 0 ? 'E' : 'W') +
          '<p id="dlHint" class="sv-cnote">Decimal degrees, no minus sign: choose the direction beside each number. Syracuse is 43.05 N, 76.15 W.</p>' +
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
      const bad = lat === null ? [latIn, 'Latitude must be a number from 0 to 90.'] : lon === null ? [lonIn, 'Longitude must be a number from 0 to 180.'] : null;
      if (bad) { bad[0].setAttribute('aria-invalid', 'true'); err.textContent = bad[1]; bad[0].focus(); return; }
      const dir = name => { const r = el.querySelector('input[name="' + name + '"]:checked'); return r ? r.value : ''; };
      keep({ lat: signed(lat, dir('dlLatDir') === 'S'), lon: signed(lon, dir('dlLonDir') !== 'E'), on: true });
      editing = false;
      render();
    }
    function keep(pos) {   // the page uses the position even when the phone's storage is full; the toast says it was not saved
      kept = pos;
      if (!FK.store.set('daylightPos', pos)) FK.toast(FK.FULL_MSG);
    }
    /* Redraw when the local date changes while the page is open, and when it is shown again after being in the background.
       An open form is left alone unless the date changed, so typing is not lost. */
    const refresh = dayChanged => { if (dayChanged || !el.querySelector('.dl-form')) render(); };
    const onVisible = () => { if (!document.hidden) refresh(dayKey() !== shownDay); };
    const dayTimer = setInterval(() => { if (dayKey() !== shownDay) refresh(true); }, 30000);
    document.addEventListener('visibilitychange', onVisible);

    el.addEventListener('submit', e => { e.preventDefault(); submit(); });
    el.addEventListener('click', e => {
      const act = e.target.closest('[data-act]');
      if (!act) return;
      if (act.dataset.act === 'type') { editing = true; render(); el.querySelector('#dlLat').focus(); }
      else if (act.dataset.act === 'cancel') { editing = false; render(); }
      else if (act.dataset.act === 'gps') { const t = typedPos(); if (t) keep({ lat: t.lat, lon: t.lon, on: false }); render(); }
      else if (act.dataset.act === 'position') FK.search.go('a:position');
    });
    render();
    return () => { clearInterval(dayTimer); document.removeEventListener('visibilitychange', onVisible); };
  }

  /* ---------- Registration ---------- */
  FK.survival.lightOn = () => lightRunning;
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
