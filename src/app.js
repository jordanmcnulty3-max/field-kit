/* ---------- App ---------- */
(() => {
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const root = document.documentElement;
  const APP_VERSION = '7.8';
  /* What a grid that GEO.parseAny cannot read gets: the Position Add row and the map's Go to grid both show it. */
  const GRID_HELP = 'Couldn’t read that location. Try a grid like 18T VN 12345 67890, or 43.0000, -76.0000, or 43°00′00″N 76°00′00″W.';
  const BLOCKED_MSG = 'Location is blocked. Allow location for this site in Chrome’s site settings, then reload.';
  const FULL_MSG = 'Couldn’t save: phone storage for Field Kit is full. Back up, then delete old tracks or saved maps.';
  let warnedAt = 0;
  const store = {
    get(k, d) { try { const v = localStorage.getItem('fk.' + k); return v === null ? d : JSON.parse(v); } catch { return d; } },
    set(k, v) {
      try { localStorage.setItem('fk.' + k, JSON.stringify(v)); return true; }
      catch {
        // Never fail silently: unsaved waypoints or tracks are real data loss. Background saves
        // (GPS, track points) can fail every second, so repeat the warning at most once a minute;
        // things the user just did report their own failure.
        if (Date.now() - warnedAt > 60000) { warnedAt = Date.now(); setTimeout(() => toast(FULL_MSG), 0); }
        return false;
      }
    }
  };
  /* Saved data can come from an old version or a hand-edited backup. Keep only well-formed
     records so one bad entry can't stop the app from starting or inject markup. */
  const fin = v => typeof v === 'number' && Number.isFinite(v);
  const okId = v => typeof v === 'string' && /^[\w-]{1,40}$/.test(v);
  const list = (k, ok) => { const v = store.get(k, []); return Array.isArray(v) ? v.filter(x => x && typeof x === 'object' && ok(x)) : []; };
  const okLatLon = (lat, lon) => fin(lat) && fin(lon) && Math.abs(lat) <= 90 && Math.abs(lon) <= 180;
  const esc = s => String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const num = el => { const v = parseFloat(el.value); return Number.isFinite(v) ? v : 0; };
  const bus = {};
  const on = (ev, fn) => (bus[ev] = bus[ev] || []).push(fn);
  const emit = (ev, d) => (bus[ev] || []).forEach(fn => { try { fn(d); } catch (e) { console.error(e); } });
  function download(name, text, type) {
    const url = URL.createObjectURL(new Blob([text], { type }));
    const el = Object.assign(document.createElement('a'), { href: url, download: name });
    document.body.appendChild(el); el.click(); el.remove();
    setTimeout(() => URL.revokeObjectURL(url), 5000);
  }

  let toastT;
  function toast(msg) {
    const t = $('#toast'); t.textContent = msg; t.classList.add('show');
    clearTimeout(toastT); toastT = setTimeout(() => t.classList.remove('show'), 2200);
  }

  /* ---------- Theme ---------- */
  function setNight(on) {
    if (on) root.dataset.theme = 'night'; else delete root.dataset.theme;
    $('#nightBtn').setAttribute('aria-pressed', String(on));
    store.set('night', on);
    requestAnimationFrame(() => {
      $('meta[name="theme-color"]').content = getComputedStyle(root).getPropertyValue('--paper').trim() || '#000';
    });
  }
  $('#nightBtn').addEventListener('click', () => setNight(root.dataset.theme !== 'night'));
  matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => setNight(root.dataset.theme === 'night'));

  /* ---------- Navigation ---------- */
  const TITLES = { survival: 'Survival', tactical: 'Tactical', emergency: 'Emergency' };
  let view = store.get('view', 'map');
  function showTab(id) {
    if (!TITLES[id]) id = 'tactical';
    $$('.tab').forEach(t => { t.hidden = t.id !== 'tab-' + id; });
    $$('.tabbar button').forEach(b => b.setAttribute('aria-current', b.dataset.tab === id ? 'page' : 'false'));
    root.dataset.tab = id;
    $('#title').textContent = TITLES[id];
    store.set('tab', id);
    window.scrollTo(0, 0);
    shown();
  }
  function showView(v) {
    view = ['map', 'position', 'ballistics'].includes(v) ? v : 'map';
    ['map', 'position', 'ballistics'].forEach(x => { $('#view-' + x).hidden = view !== x; });
    $$('#tacSeg button').forEach(b => b.setAttribute('aria-selected', String(b.dataset.view === view)));
    store.set('view', view);
    window.scrollTo(0, 0);
    shown();
  }
  function shown() {
    document.body.classList.toggle('mapmode', root.dataset.tab === 'tactical' && view === 'map');
    sensors();
    emit('shown', { tab: root.dataset.tab, view });
  }
  /* Taps change the address; the router (router.js) calls showTab / showView, so Back works. */
  $$('.tabbar button').forEach(b => b.addEventListener('click', () => FK.route.go('/' + b.dataset.tab + (b.dataset.tab === 'tactical' ? '/' + view : ''))));
  $$('#tacSeg button').forEach(b => b.addEventListener('click', () => FK.route.go('/tactical/' + b.dataset.view)));

  /* ---------- GPS ---------- */
  let watchId = null, fix = store.get('lastFix', null), llFormat = store.get('llFormat', 'dec') === 'dms' ? 'dms' : 'dec';
  if (!fix || !okLatLon(fix.lat, fix.lon)) fix = null;
  const navVisible = () => root.dataset.tab === 'tactical' && (view === 'position' || view === 'map') && !document.hidden;
  /* GPS also runs in every tab while a track records or a navigation target is set (tac-nav.js shows the target). */
  const gpsWanted = () => !document.hidden && (navVisible() || !!(window.FK && FK.isRecording && FK.isRecording()) || !!(window.FK && FK.tac && FK.tac.target()));

  function setStatus(msg, warn) { const s = $('#gpsStatus'); if (s.textContent !== msg) s.textContent = msg; s.classList.toggle('warn', !!warn); }

  /* ---------- How fresh the stored fix is: ONE rule for every figure measured from it ----------
     A fix up to 30 s old is live: "Your position", "from you", its speed. An older one (a stored fix from an earlier visit,
     or the GPS has gone quiet) is the last position: "Last position, 3 days ago", "from last position", no speed. */
  const LIVE_FIX_MS = 30000;
  const fixLive = (f = fix) => !!f && fin(f.t) && Date.now() - f.t <= LIVE_FIX_MS;
  const MON3 = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  function fixAgeWords(ms) {
    const s = Math.max(0, Math.round(ms / 1000));
    if (s < 90) return `${s} s`;
    if (s < 5400) return `${Math.round(s / 60)} min`;
    if (s < 129600) return `${Math.round(s / 3600)} h`;
    const d = Math.round(s / 86400);
    return `${d} ${d === 1 ? 'day' : 'days'}`;
  }
  /* "Last position, 5 min ago", with the date when the fix is not from today. */
  function lastPosText(f = fix) {
    if (!f) return '';
    if (!fin(f.t)) return 'Last position, time unknown';
    const d = new Date(f.t), today = d.toDateString() === new Date().toDateString();
    return `Last position, ${fixAgeWords(Date.now() - f.t)} ago${today ? '' : `, ${MON3[d.getMonth()]} ${d.getDate()}`}`;
  }
  const fromWords = () => fixLive() ? 'from you' : 'from last position';
  /* The line under the grid at a spot (the map's crosshair, a marker): '' with no fix. */
  function relText(lat, lon, fmtDist) {
    if (!fix) return '';
    const d = GEO.distance(fix.lat, fix.lon, lat, lon);
    if (d < 3) return fixLive() ? 'Your position' : lastPosText();
    return `${fmtDist(d)} at ${Math.round(GEO.bearing(fix.lat, fix.lon, lat, lon))}° true ${fromWords()}`;
  }
  let gpsErr = null, gpsBlocked = false;   // the standing GPS message (blocked, no signal...) until a fix arrives
  function renderStatus() {
    if (gpsErr) { setStatus(fix && !fixLive() ? `${lastPosText()}. ${gpsErr}` : gpsErr, true); return; }
    if (fixLive()) setStatus('Live fix, ' + new Date(fix.t).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }));
    else if (fix) setStatus(lastPosText() + (watchId !== null ? '. Updating…' : ''));
    else if (watchId !== null) setStatus('Getting a GPS fix. Open sky helps.');
  }
  /* The live/last switch happens with time alone: check every 2 s, redraw what depends on it when it flips, and keep the
     Position line's age current. */
  let wasLive = fixLive();
  setInterval(() => {
    if (document.hidden) return;
    const now = fixLive();
    if (now !== wasLive) { wasLive = now; renderFix(); emit('fixlive', now); }
    if (root.dataset.tab === 'tactical' && view === 'position') renderStatus();
  }, 2000);
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) return;
    wasLive = fixLive(); renderFix(); renderStatus(); emit('fixlive', wasLive);
  });

  function startGps() {
    if (watchId !== null) return;
    if (!('geolocation' in navigator)) { gpsErr = 'This browser has no location support.'; renderStatus(); return; }
    if (!window.isSecureContext) { gpsErr = 'Location needs HTTPS. Open the app from its GitHub Pages address.'; renderStatus(); return; }
    watchId = navigator.geolocation.watchPosition(onFix, onGpsErr, { enableHighAccuracy: true, maximumAge: 2000, timeout: 30000 });
    renderStatus();
  }
  function stopGps() { if (watchId !== null) { navigator.geolocation.clearWatch(watchId); watchId = null; } }

  function onFix(p) {
    const c = p.coords;
    fix = { lat: c.latitude, lon: c.longitude, alt: c.altitude, acc: c.accuracy, spd: c.speed, t: p.timestamp };
    store.set('lastFix', fix);
    liveFix = true;
    gpsErr = null; wasLive = fixLive();
    if (gpsBlocked) { gpsBlocked = false; emit('gpsBlocked', false); }
    renderStatus();
    renderFix(); renderWps();
    declFromFix();   // before 'fix' goes out, so the navigate arrow uses the new declination
    emit('fix', fix);
  }
  function onGpsErr(e) {
    const msgs = {
      1: BLOCKED_MSG,
      2: 'No GPS signal. Move to open sky.',
      3: 'Still searching for satellites. Move to open sky.'
    };
    gpsErr = msgs[e.code] || 'Location error: ' + e.message;
    renderStatus();
    if ((e.code === 1) !== gpsBlocked) { gpsBlocked = e.code === 1; emit('gpsBlocked', gpsBlocked); }
    emit('gpsError', msgs[e.code] || e.message);
  }

  function renderFix() {
    const m = $('#mgrs'), ll = $('#latlon');
    if (!fix) { m.classList.add('empty'); m.textContent = 'No fix yet'; ll.textContent = ''; return; }
    const g = GEO.toMGRS(fix.lat, fix.lon);
    m.classList.remove('empty');
    m.innerHTML = g ? `<span class="gz">${g.gzd} ${g.sq}</span>${g.e} ${g.n}` : 'Polar region (UPS)';
    ll.textContent = llFormat === 'dms'
      ? `${GEO.dms(fix.lat, 'N', 'S')}  ${GEO.dms(fix.lon, 'E', 'W')}`
      : `${fix.lat.toFixed(6)}, ${fix.lon.toFixed(6)}`;
    $('#sAlt').textContent = fix.alt == null ? '—' : `${Math.round(fix.alt * 3.28084).toLocaleString()} ft`;
    $('#sAcc').textContent = fix.acc == null ? '—' : `±${Math.round(fix.acc)} m`;
    $('#sSpd').textContent = fix.spd == null || Number.isNaN(fix.spd) || !fixLive() ? '—' : `${(fix.spd * 2.23694).toFixed(1)} mph`;
  }

  $('#mgrs').addEventListener('click', () => {
    if (!fix) return;
    const g = GEO.toMGRS(fix.lat, fix.lon);
    copy(g ? g.text : `${fix.lat.toFixed(6)}, ${fix.lon.toFixed(6)}`);
  });
  $('#latlon').addEventListener('click', () => {
    llFormat = llFormat === 'dec' ? 'dms' : 'dec'; store.set('llFormat', llFormat); renderFix();
  });
  async function copy(text) {
    try { await navigator.clipboard.writeText(text); toast('Copied ' + text); } catch { toast(text); }
  }

  /* ---------- Compass ---------- */
  let heading = null, compassOn = false, gotOri = false, oriTimer = null;
  /* Declination: 'auto' works it out from the position with the World Magnetic Model (wmm.js); 'manual' uses the number
     typed in #decl (east positive), stored as 'decl'. The worked-out value is never written to 'decl'. A phone that has a
     typed non-zero value from before v7.8 and no mode stays on the typed value. */
  let decl = store.get('decl', 0);
  if (!fin(decl)) decl = 0;
  let declMode = store.get('declMode', null);
  if (declMode !== 'auto' && declMode !== 'manual') { declMode = decl ? 'manual' : 'auto'; store.set('declMode', declMode); }
  let liveFix = false;   // has a GPS fix arrived in this session (else the position is the stored last one)
  let auto = null;   // { lat, lon, day, value }: the last worked-out declination and where and when it was worked out
  const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
  const decimalYear = ms => {
    const y = new Date(ms).getUTCFullYear(), a = Date.UTC(y, 0, 1), b = Date.UTC(y + 1, 0, 1);
    return y + (ms - a) / (b - a);
  };
  /* The model's last day, from its decimal valid-until year (2030.0 is the start of 2030, so the last month is December 2029). */
  const validUntilText = () => {
    const y = Math.floor(WMM.validUntil), a = Date.UTC(y, 0, 1), b = Date.UTC(y + 1, 0, 1);
    const d = new Date(a + (WMM.validUntil - y) * (b - a) - 1);
    return `${MONTHS[d.getUTCMonth()]} ${d.getUTCFullYear()}`;
  };
  /* Work the declination out again only when the position has moved more than 10 km or the date has changed. */
  function autoDecl() {
    if (!fix || typeof WMM === 'undefined') return null;
    const day = new Date().toDateString();
    if (auto && auto.day === day && GEO.distance(auto.lat, auto.lon, fix.lat, fix.lon) <= 10000) return auto.value;
    const altKm = fin(fix.alt) ? fix.alt / 1000 : 0;
    // A clock outside the model's years (a phone set to 1970 or 2099) uses the model at its nearest valid date: straight-line
    // extrapolation drifts by degrees. The line still says the model is out of date (renderDecl reads the real clock).
    const y = Math.min(WMM.validUntil, Math.max(WMM.epoch, decimalYear(Date.now())));
    const v = WMM.declination(fix.lat, fix.lon, altKm, y);
    auto = { lat: fix.lat, lon: fix.lon, day, value: fin(v) ? v : null };
    return auto.value;
  }
  /* The declination applied to the compass, or null for none (the heading is then magnetic). */
  const appliedDecl = () => declMode === 'manual' ? (decl ? decl : null) : autoDecl();
  const declText = v => {
    const r = Math.round(v * 10) / 10;
    return r === 0 ? '0.0°' : `${Math.abs(r).toFixed(1)}° ${r < 0 ? 'W' : 'E'}`;
  };
  let lastApplied;
  function renderDecl() {
    $$('#declSeg button').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.decl === declMode)));
    $('#declField').hidden = declMode === 'auto';
    const line = $('#declLine');
    line.hidden = declMode !== 'auto';
    if (declMode === 'auto') {
      const v = autoDecl();
      if (v == null) line.textContent = fix ? 'Declination: not available at this position' : 'Declination: waiting for a position';
      else {
        const y = decimalYear(Date.now()), old = y >= WMM.validUntil || y < WMM.epoch;
        line.textContent = `Declination ${declText(v)} (worked out from your ${liveFix ? '' : 'last known '}position, model valid to ${validUntilText()})` +
          (old ? '\nThe magnetic model is out of date. Check a current map.' : '');
      }
    }
  }
  /* After anything that may change the applied declination: redraw what depends on it, and tell the navigate panel. */
  function declChanged() {
    renderDecl();
    const a = appliedDecl();
    if (a === lastApplied) return;
    lastApplied = a;
    renderCompass(); renderWps();
    if (heading != null) emit('heading', trueHeading());
    emit('decl', a);
  }
  function declFromFix() { if (declMode === 'auto') declChanged(); }
  $('#decl').value = decl || '';
  $('#decl').addEventListener('input', e => { decl = num(e.target); store.set('decl', decl); declChanged(); });
  $$('#declSeg button').forEach(b => b.addEventListener('click', () => {
    if (b.dataset.decl === declMode) return;
    declMode = b.dataset.decl; store.set('declMode', declMode); declChanged();
  }));

  // Build rose: ticks every 10°, cardinal letters
  (function buildRose() {
    const g = $('#rose'); let s = '';
    for (let d = 0; d < 360; d += 10) {
      const major = d % 90 === 0, mid = d % 30 === 0;
      s += `<line x1="100" y1="${major ? 6 : 6}" x2="100" y2="${major ? 22 : mid ? 18 : 13}" stroke="var(--ink)" stroke-width="${major ? 2.5 : 1.2}" transform="rotate(${d} 100 100)"/>`;
      if (mid && !major) s += `<text x="100" y="34" font-size="11" text-anchor="middle" fill="var(--muted)" transform="rotate(${d} 100 100)">${d}</text>`;
    }
    [['N', 0], ['E', 90], ['S', 180], ['W', 270]].forEach(([l, d]) => {
      s += `<text x="100" y="42" font-size="${l === 'N' ? 22 : 18}" font-weight="700" text-anchor="middle" fill="${l === 'N' ? 'var(--c)' : 'var(--ink)'}" transform="rotate(${d} 100 100)">${l}</text>`;
    });
    s += `<g id="tgtMark" hidden><circle cx="100" cy="58" r="7" fill="var(--blaze)"/></g>`;
    g.innerHTML = s;
  })();

  /* Motion permission. Safari on iPhone sends no readings until the page has called DeviceOrientationEvent.requestPermission()
     from inside a tap, so where that function exists the compass shows Turn on compass (#compassAsk, and #nvCompassAsk in the
     navigate panel), from 800 ms after the compass starts with no reading, until permission is given or a reading arrives. Chrome 152 and later also has the function but sends
     readings without it, so the listener is added anyway and the first reading hides the buttons. The 4-second "no sensor"
     message waits for the permission. Nothing is stored: iPhone may forget the permission on reload, so it is asked again. */
  const askable = () => typeof DeviceOrientationEvent !== 'undefined' && typeof DeviceOrientationEvent.requestPermission === 'function';
  let calib = false;   // the last reading had a negative webkitCompassAccuracy
  let oriAllowed = false, asking = false, oriBlocked = false, askDue = false, askTimer = null;
  /* Permission is the way forward: the function exists, it has not been granted and no reading has come. */
  const pending = () => askable() && !oriAllowed && !gotOri;
  /* The button shows only after 800 ms with no reading, so on Android Chrome (whose first reading comes sooner) it never
     appears. Once shown it stays until granted or a reading comes. */
  const needAsk = () => pending() && askDue;
  function renderAsk() {
    const ask = needAsk();
    $('#compassAskWrap').hidden = !ask;
    $$('.compass-blocked').forEach(p => { p.hidden = !(ask && oriBlocked); });
    emit('compassAsk', ask);
  }
  function armAsk() {
    clearTimeout(askTimer); askTimer = null;
    if (!pending() || askDue) return;
    askTimer = setTimeout(() => { askTimer = null; if (pending()) { askDue = true; renderAsk(); } }, 800);
  }
  function askCompass() {
    if (asking || !needAsk()) return;
    asking = true;
    // A question that never answers must not leave the button dead: after 10 s a tap asks again.
    const freed = setTimeout(() => { asking = false; }, 10000);
    let p;
    // Called straight from the tap: no await or timer before it, or Safari refuses.
    try { p = DeviceOrientationEvent.requestPermission(); } catch (e) { p = Promise.reject(e); }
    // Only "denied" or a failure is a refusal; any other answer (Chrome can say "prompt") leaves the button as it was.
    Promise.resolve(p).then(r => r, () => 'denied').then(r => {
      clearTimeout(freed);
      asking = false;
      if (r === 'granted') {
        oriAllowed = true; oriBlocked = false;
        if (compassOn) { removeOri(); addOri(); armNoSensor(); }
      } else oriBlocked = r === 'denied';
      renderAsk();
    });
  }
  $$('.compass-ask-btn').forEach(b => b.addEventListener('click', askCompass));
  renderAsk();

  function onOri(e) {
    // iPhone's webkitCompassAccuracy below 0 is taken to mean the compass may need calibrating. That meaning is not checked
    // (no source opened says it), so the reading is still used; only a hint is added under it, until a reading without one.
    let h = null;
    if (typeof e.webkitCompassHeading === 'number') h = e.webkitCompassHeading;
    else if (e.alpha != null && (e.absolute || e.type === 'deviceorientationabsolute')) h = 360 - e.alpha;
    if (h == null) return;
    calib = typeof e.webkitCompassAccuracy === 'number' && e.webkitCompassAccuracy < 0;
    const scr = (screen.orientation && screen.orientation.angle) || 0;
    h = (h + scr + 360) % 360;
    if (!gotOri) { gotOri = true; clearTimeout(askTimer); if (askable()) renderAsk(); }
    if (heading == null) heading = h;
    else { const d = ((h - heading + 540) % 360) - 180; heading = (heading + d * 0.25 + 360) % 360; }
    renderCompass();
    emit('heading', trueHeading());
  }
  function addOri() {
    if ('ondeviceorientationabsolute' in window) window.addEventListener('deviceorientationabsolute', onOri);
    else window.addEventListener('deviceorientation', onOri);
  }
  function removeOri() {
    window.removeEventListener('deviceorientationabsolute', onOri);
    window.removeEventListener('deviceorientation', onOri);
  }
  function armNoSensor() {
    clearTimeout(oriTimer);
    oriTimer = setTimeout(() => { if (!gotOri) $('#hdgRef').textContent = 'No compass sensor found. Distances and bearings to markers still work.'; }, 4000);
  }
  function startCompass() {
    if (compassOn) return;
    compassOn = true;
    addOri();
    clearTimeout(oriTimer);
    if (pending()) armAsk(); else armNoSensor();
  }
  function stopCompass() {
    if (!compassOn) return;
    compassOn = false;
    clearTimeout(askTimer); askTimer = null;
    removeOri();
  }
  const trueHeading = () => heading == null ? null : (heading + (appliedDecl() ?? 0) + 360) % 360;
  function renderCompass() {
    const th = trueHeading();
    if (th == null) return;
    $('#rose').style.transform = `rotate(${-th}deg)`;
    $('#hdg').textContent = Math.round(th) % 360 + '°';
    const mils = Math.round(th * 6400 / 360) % 6400;
    $('#hdgRef').textContent = `${GEO.cardinal(th)}, ${mils} mils, ${appliedDecl() == null ? 'magnetic' : 'true'}` +
      (calib ? '. Compass may need calibrating: move the phone in a figure-8.' : '');
  }

  /* ---------- Position as text ---------- */
  const MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const p2 = n => String(n).padStart(2, '0');
  /* The block to read aloud or paste: grid, lat/long, altitude, accuracy, the fix's time (local and Zulu), and its age when
     older than a minute. A line whose value is unknown is left out. */
  function positionText(f, now) {
    const c5 = v => { const t = v.toFixed(5); return t === '-0.00000' ? '0.00000' : t; };
    const g = GEO.toMGRS(f.lat, f.lon), ll = `${c5(f.lat)}, ${c5(f.lon)}`;
    const lines = g ? [`Position ${g.text}`, ll] : [`Position ${ll}`];
    if (fin(f.alt)) lines.push(`Altitude ${Math.round(f.alt * 3.28084)} ft`);
    if (fin(f.acc)) lines.push(`Accuracy ±${Math.round(f.acc)} m`);
    if (fin(f.t)) {
      const d = new Date(f.t);
      lines.push(`Time ${p2(d.getHours())}:${p2(d.getMinutes())} local, ${p2(d.getUTCHours())}:${p2(d.getUTCMinutes())}Z ${p2(d.getUTCDate())} ${MON[d.getUTCMonth()]} ${d.getUTCFullYear()}`);
      const age = now - f.t, s = Math.round(age / 1000);
      if (age > 60000) {
        lines.push(`Position is ${s < 90 ? s + ' s' : s < 5400 ? Math.round(s / 60) + ' min' : s < 129600 ? Math.round(s / 3600) + ' h' : Math.round(s / 86400) + ' days'} old`);
      }
    }
    return lines.join('\n');
  }
  async function copyShare(text) {
    try { await navigator.clipboard.writeText(text); $('#psMsg').textContent = 'Copied.'; }
    catch { $('#psMsg').textContent = 'Not copied. Press and hold the text to select it.'; }
  }
  function showShare(text) {
    $('#psText').textContent = text;
    $('#psMsg').textContent = '';
    FK.sheet.open($('#dlgShare'), { onOpen: () => $('#psTitle').focus() });
    copyShare(text);
  }
  $('#shareBtn').addEventListener('click', async () => {
    if (!fix) { toast(gpsBlocked ? BLOCKED_MSG : 'No position yet. Wait for a GPS fix.'); return; }
    const text = positionText(fix, Date.now());
    if (typeof navigator.share === 'function') {
      try { await navigator.share({ text }); return; }
      catch (e) { if (e && e.name === 'AbortError') return; }
    }
    showShare(text);
  });
  $('#psCopy').addEventListener('click', () => copyShare($('#psText').textContent));
  $('#psClose').addEventListener('click', () => FK.sheet.close($('#dlgShare')));

  /* ---------- Screen wake lock ---------- */
  let wakeWanted = false, wakeLock = null;
  const NO_WAKE = 'Couldn’t keep the screen on. Raise the screen timeout in the phone’s Display settings instead.';
  async function acquireWake() {
    try { wakeLock = await navigator.wakeLock.request('screen'); wakeLock.addEventListener('release', () => { wakeLock = null; }); }
    catch { wakeWanted = false; toast(NO_WAKE); }
    $('#wakeBtn').setAttribute('aria-pressed', String(wakeWanted));
    $('#wakeBtn').textContent = wakeWanted ? 'Screen stays on' : 'Keep screen on';
  }
  async function setWake(on) {
    wakeWanted = on;
    if (on) { if (!('wakeLock' in navigator)) { wakeWanted = false; toast(NO_WAKE); } else await acquireWake(); }
    else if (wakeLock) { await wakeLock.release(); wakeLock = null; }
    $('#wakeBtn').setAttribute('aria-pressed', String(wakeWanted));
    $('#wakeBtn').textContent = wakeWanted ? 'Screen stays on' : 'Keep screen on';
  }
  $('#wakeBtn').addEventListener('click', () => setWake(!wakeWanted));

  /* ---------- Markers on Position ----------
     The data lives in tac-data.js (FK.tac), which loads after this file and redraws the list through the 'wps' event. */
  $('#wpMark').addEventListener('click', () => {
    if (!fix) { $('#wpMsg').textContent = 'No GPS fix yet. Wait for a position, then mark.'; return; }
    const m = FK.tac.addMarker({ lat: fix.lat, lon: fix.lon, name: $('#wpName').value, alt: fix.alt });
    $('#wpName').value = ''; $('#wpMsg').textContent = m ? `Marked ${m.name}.` : FULL_MSG;
  });
  $('#wpAdd').addEventListener('click', () => {
    const p = GEO.parseAny($('#wpCoord').value);
    if (!p) { $('#wpMsg').textContent = GRID_HELP; return; }
    const m = FK.tac.addMarker({ lat: p.lat, lon: p.lon, name: $('#wpName').value });
    $('#wpCoord').value = ''; $('#wpName').value = ''; $('#wpMsg').textContent = m ? `Added ${m.name}.` : FULL_MSG;
  });

  /* The list itself is a sheet on the map (tac-markers.js); this block shows how many there are and opens it. */
  function renderWps() {
    if (!FK.tac) return;   // before tac-data.js has loaded
    const n = FK.tac.markers().length;
    $('#wpCount').textContent = n ? `${n} ${n === 1 ? 'marker' : 'markers'}` : 'No markers yet';
    $('#wpOpenList').disabled = !n;
  }
  $('#wpOpenList').addEventListener('click', () => { FK.route.go('/tactical/map'); FK.markers.openList(); });
  on('wps', renderWps);
  /* The navigation target and its display live in tac-nav.js; here only the GPS follows it. */
  on('target', () => sensors());

  /* Export (GPX or KML) is one sheet in tac-io.js. */
  $('#posExport').addEventListener('click', () => FK.io.openExport());

  /* ---------- Sensors on/off with visibility (saves battery) ---------- */
  function sensors() {
    if (gpsWanted()) startGps(); else stopGps();
    if (navVisible()) startCompass(); else stopCompass();
  }
  document.addEventListener('visibilitychange', () => {
    sensors();
    if (!document.hidden && wakeWanted && !wakeLock) acquireWake();
  });

  /* ---------- Ballistics ---------- */
  const PRESETS = [
    { id: 'p556', name: '5.56 NATO 62 gr M855, 20″ barrel', bc: 0.304, model: 'G1', w: 62, mv: 3020, sight: 2.6, zero: 100 },
    { id: 'p223', name: '.223 Rem 77 gr OTM', bc: 0.372, model: 'G1', w: 77, mv: 2750, sight: 2.6, zero: 100 },
    { id: 'p76239', name: '7.62×39 123 gr FMJ', bc: 0.29, model: 'G1', w: 123, mv: 2350, sight: 2.0, zero: 100 },
    { id: 'p65cm', name: '6.5 Creedmoor 140 gr ELD-M', bc: 0.326, model: 'G7', w: 140, mv: 2710, sight: 1.5, zero: 100 },
    { id: 'p308', name: '.308 Win 175 gr SMK', bc: 0.243, model: 'G7', w: 175, mv: 2600, sight: 1.5, zero: 100 }
  ];
  let profiles = list('profiles', p => okId(p.id) && typeof p.name === 'string');
  let unit = store.get('unit', 'mil') === 'moa' ? 'moa' : 'mil';
  const F = id => $('#' + id);
  const LOAD_FIELDS = { bc: 'bBC', model: 'bModel', w: 'bW', mv: 'bMV', sight: 'bSH', zero: 'bZero' };
  const ALL_FIELDS = ['bRange', 'bAngle', 'bWind', 'bClock', 'bBC', 'bModel', 'bW', 'bMV', 'bSH', 'bZero', 'bTemp', 'bAlt', 'bPress', 'bRH', 'bMax', 'bStep'];

  function fillProfiles(sel) {
    const opt = p => `<option value="${p.id}">${esc(p.name)}</option>`;
    F('bProfile').innerHTML =
      (profiles.length ? `<optgroup label="My profiles">${profiles.map(opt).join('')}</optgroup>` : '') +
      `<optgroup label="Starting points">${PRESETS.map(opt).join('')}</optgroup>` +
      `<option value="custom">Custom (unsaved)</option>`;
    F('bProfile').value = sel || 'custom';
    if (!F('bProfile').value) F('bProfile').value = 'custom';
    F('bDel').hidden = !profiles.some(p => p.id === F('bProfile').value);
  }
  function loadProfile(id) {
    const p = profiles.find(x => x.id === id) || PRESETS.find(x => x.id === id);
    if (!p) return;
    for (const [k, fid] of Object.entries(LOAD_FIELDS)) F(fid).value = p[k];
    F('bDel').hidden = !profiles.some(x => x.id === id);
  }
  F('bProfile').addEventListener('change', e => { loadProfile(e.target.value); saveInputs(); calc(); });
  F('bSave').addEventListener('click', async () => {
    const name = await FK.sheet.ask({ title: 'Name this profile', label: 'Name, e.g. Tikka .308 – 175 SMK' });
    if (!name) return;
    const p = { id: 'u' + Date.now().toString(36), name };
    for (const [k, fid] of Object.entries(LOAD_FIELDS)) p[k] = k === 'model' ? F(fid).value : num(F(fid));
    profiles.push(p); store.set('profiles', profiles); fillProfiles(p.id); saveInputs(); toast(`Saved ${name}`);
  });
  F('bDel').addEventListener('click', async () => {
    const id = F('bProfile').value, p = profiles.find(x => x.id === id);
    if (!p || !await FK.sheet.confirm({ title: 'Delete the profile?', text: `Delete the ${p.name} profile? This can’t be undone.`, ok: 'Delete profile', danger: true })) return;
    profiles = profiles.filter(x => x.id !== id); store.set('profiles', profiles); fillProfiles('custom'); saveInputs();
  });

  function saveInputs() {
    const s = { profile: F('bProfile').value };
    ALL_FIELDS.forEach(id => { s[id] = F(id).value; });
    store.set('bal', s);
  }
  function restoreInputs() {
    const s = store.get('bal', null);
    if (!s) { fillProfiles('p308'); loadProfile('p308'); return; }
    fillProfiles(s.profile);
    ALL_FIELDS.forEach(id => { if (s[id] !== undefined) F(id).value = s[id]; });
  }

  const fmtAng = v => Math.abs(v).toFixed(1);
  function calc() {
    const max = Math.min(3000, Math.max(50, num(F('bMax')) || 1000));
    const step = +F('bStep').value || 50;
    const target = num(F('bRange'));
    const ranges = [];
    for (let r = step; r <= max; r += step) ranges.push(r);
    const zero = num(F('bZero'));
    if (zero && !ranges.includes(zero)) ranges.push(zero);
    if (target > 0) ranges.push(target);

    const res = BAL.solve({
      bc: num(F('bBC')), model: F('bModel').value, w: num(F('bW')), mv: num(F('bMV')),
      sight: num(F('bSH')), zero, temp: F('bTemp').value === '' ? 59 : num(F('bTemp')), alt: num(F('bAlt')),
      press: num(F('bPress')), rh: num(F('bRH')), wind: num(F('bWind')), clock: +F('bClock').value,
      angle: num(F('bAngle')), ranges
    });
    const U = unit === 'mil' ? 'mil' : 'MOA';
    const ev = r => unit === 'mil' ? r.elevMil : r.elevMoa;
    const wv = r => unit === 'mil' ? r.windMil : r.windMoa;
    const dirE = v => Math.abs(v) < 0.05 ? '' : v > 0 ? 'U ' : 'D ';
    const dirW = v => Math.abs(v) < 0.05 ? '' : v > 0 ? 'R ' : 'L ';

    if (res.error) {
      $('#solElev').textContent = '—'; $('#solWind').textContent = '—';
      $('#solSub').textContent = res.error; $('#dope').innerHTML = ''; return;
    }
    const t = res.rows.find(r => r.yd === Math.round(target));
    if (t) {
      $('#solElev').innerHTML = `${dirE(ev(t))}${fmtAng(ev(t))} <small>${U}</small>`;
      $('#solWind').innerHTML = `${dirW(wv(t))}${fmtAng(wv(t))} <small>${U}</small>`;
      $('#solSub').textContent = `At ${t.yd} yd: drop ${Math.abs(t.dropIn).toFixed(1)} in, drift ${Math.abs(t.windIn).toFixed(1)} in, `
        + `${Math.round(t.fps)} fps, ${Math.round(t.ftlb)} ft-lb, ${t.tof.toFixed(2)} s flight`
        + (t.mach < 1 ? '. Subsonic: expect larger errors.' : '.');
    } else {
      $('#solElev').textContent = '—'; $('#solWind').textContent = '—';
      $('#solSub').textContent = target > 0 ? 'Bullet doesn’t reach that range with these inputs.' : 'Enter a target range.';
    }
    const rows = res.rows.filter(r => r.yd % step === 0 || r.yd === zero);
    $('#dope').innerHTML = `<thead><tr><th>Yd</th><th>Elev ${U}</th><th>Wind ${U}</th><th>Drop in</th><th>Drift in</th><th>fps</th><th>ft-lb</th><th>Time s</th></tr></thead><tbody>` +
      rows.map(r => `<tr class="${r.yd === zero ? 'zero' : ''} ${r.mach < 1.2 ? 'trans' : ''}"><td>${r.yd}</td>` +
        `<td>${dirE(ev(r))}${fmtAng(ev(r))}</td><td>${dirW(wv(r))}${fmtAng(wv(r))}</td>` +
        `<td>${r.dropIn.toFixed(1)}</td><td>${Math.abs(r.windIn).toFixed(1)}</td><td>${Math.round(r.fps)}</td>` +
        `<td>${Math.round(r.ftlb)}</td><td>${r.tof.toFixed(2)}</td></tr>`).join('') + '</tbody>';
  }
  let calcT;
  ALL_FIELDS.forEach(id => F(id).addEventListener('input', e => {
    if (Object.values(LOAD_FIELDS).includes(id)) { F('bProfile').value = 'custom'; F('bDel').hidden = true; }
    clearTimeout(calcT); calcT = setTimeout(() => { saveInputs(); calc(); }, 150);
  }));
  $$('#unitSeg button').forEach(b => b.addEventListener('click', () => {
    unit = b.dataset.unit; store.set('unit', unit);
    $$('#unitSeg button').forEach(x => x.setAttribute('aria-selected', String(x === b)));
    calc();
  }));

  /* ---------- Online status, install, offline cache ---------- */
  const net = () => { $('#netChip').hidden = navigator.onLine; };
  addEventListener('online', net); addEventListener('offline', net); net();

  let installEvt = null;
  addEventListener('beforeinstallprompt', e => { e.preventDefault(); installEvt = e; $('#installBtn').hidden = false; });
  $('#installBtn').addEventListener('click', async () => {
    if (!installEvt) return; installEvt.prompt(); await installEvt.userChoice; installEvt = null; $('#installBtn').hidden = true;
  });
  addEventListener('appinstalled', () => { $('#installBtn').hidden = true; toast('Installed. Field Kit now works offline.'); });

  if ('serviceWorker' in navigator && window.isSecureContext) {
    navigator.serviceWorker.register('sw.js').catch(() => { /* offline cache unavailable */ });
  }

  /* ---------- Protocol data: one accessor for the player, Emergency home and search. Only well-formed protocols
     come out of it (an object with an id, a title and at least one step, every step an object with string id and text),
     so a malformed entry is skipped instead of drawing an empty screen. ---------- */
  const filled = v => typeof v === 'string' && v.trim() !== '';
  const okStep = s => !!s && typeof s === 'object' && filled(s.id) && typeof s.text === 'string';
  const okProtocol = p => !!p && typeof p === 'object' && filled(p.id) && filled(p.title) && Array.isArray(p.steps) && p.steps.length > 0 && p.steps.every(okStep);
  let protoSrc = null, protoLen = -1, protoList = [];
  function protocols() {
    const src = window.FK_DATA && Array.isArray(window.FK_DATA.protocols) ? window.FK_DATA.protocols : null;
    if (src !== protoSrc || (src && src.length !== protoLen)) { protoSrc = src; protoLen = src ? src.length : -1; protoList = src ? src.filter(okProtocol) : []; }
    return protoList;
  }

  /* ---------- Focus after an overlay closes: back to the control that opened it, else the screen heading ---------- */
  const visible = el => !!el && el.isConnected && el.getClientRects().length > 0 && !el.closest('[hidden],[inert]');
  const OPENER_KEYS = ['data-open', 'data-tool', 'data-resume', 'data-key', 'data-act'];
  /* Remember an opener so it can be found again after its list is redrawn. */
  function opener(el) {
    if (!el || el === document.body || !(el instanceof Element)) return null;
    const k = OPENER_KEYS.find(a => el.hasAttribute(a));
    return { el, sel: k ? '[' + k + '="' + CSS.escape(el.getAttribute(k)) + '"]' : null };
  }
  /* Runs after the current navigation has settled, and only if nothing else has taken focus. */
  function refocus(o) {
    setTimeout(() => {
      const a = document.activeElement;
      if (a && a !== document.body && visible(a)) return;
      let t = o && visible(o.el) ? o.el : null;
      if (!t && o && o.sel) t = [...document.querySelectorAll('main ' + o.sel)].find(visible) || null;
      if (!t) { t = $('#title'); if (!visible(t)) return; }
      t.focus({ preventScroll: true });
    }, 0);
  }

  /* ---------- Shared API for the map module ---------- */
  window.FK = {
    protocols, opener, refocus, updateAvailable,
    $, $$, store, toast, esc, on, emit, download, sensors, fin, okId, list, okLatLon, FULL_MSG, GRID_HELP,
    getFix: () => fix,
    gpsBlocked: () => gpsBlocked, BLOCKED_MSG,
    fixLive: () => fixLive(), lastPosText: () => lastPosText(), fromWords, relText,
    trueHeading, compassAsk: needAsk, setWake, wakeOn: () => wakeWanted,
    tab: () => root.dataset.tab, view: () => view, showTab, showView,
    /* Test hooks: the same code paths as a real GPS fix and a real compass reading (the reading is taken as-is, not smoothed
       against the previous one). They change no stored data on their own. */
    _test: {
      fix: f => onFix({ coords: { latitude: f.lat, longitude: f.lon, accuracy: f.acc ?? 5, altitude: f.alt ?? null, speed: f.spd ?? null }, timestamp: f.t ?? Date.now() }),
      heading: deg => { heading = null; onOri({ webkitCompassHeading: deg }); },
      positionText
    }
  };

  /* ---------- Segmented controls: arrow keys move between options ---------- */
  document.addEventListener('keydown', e => {
    const tab = e.target.closest && e.target.closest('[role="tablist"] [role="tab"]');
    if (!tab || !['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(e.key)) return;
    const tabs = [...tab.parentElement.querySelectorAll('[role="tab"]')];
    let i = tabs.indexOf(tab);
    i = e.key === 'Home' ? 0 : e.key === 'End' ? tabs.length - 1 : (i + (e.key === 'ArrowRight' ? 1 : -1) + tabs.length) % tabs.length;
    e.preventDefault(); tabs[i].focus(); tabs[i].click();
  });

  /* ---------- Errors surface instead of failing silently ---------- */
  let lastErr = 0;
  const showErr = msg => { if (Date.now() - lastErr > 8000) { lastErr = Date.now(); toast(`Something went wrong (${String(msg).slice(0, 60)}). If anything looks off, close and reopen Field Kit.`); } };
  addEventListener('error', e => showErr(e.message));
  addEventListener('unhandledrejection', e => showErr(e.reason && e.reason.message || e.reason));

  /* ---------- Keep this phone’s data from being evicted ---------- */
  if (navigator.storage && navigator.storage.persist) navigator.storage.persist().catch(() => {});

  /* ---------- Settings, backup and restore ---------- */
  async function diag() {
    const bits = [`Version ${APP_VERSION}`];
    if (navigator.storage && navigator.storage.estimate) {
      const e = await navigator.storage.estimate();
      bits.push(`using ${((e.usage || 0) / 1e6).toFixed(1)} MB`);
    }
    if (navigator.storage && navigator.storage.persisted) bits.push(await navigator.storage.persisted() ? 'storage protected from clean-up' : 'storage not yet protected (install the app to protect it)');
    bits.push(navigator.serviceWorker && navigator.serviceWorker.controller ? 'works offline' : 'offline mode not active yet');
    $('#diag').textContent = bits.join(' · ');
  }
  const syncUnitSeg = () => $$('#unitDist button').forEach(x => x.setAttribute('aria-selected', String(FK.tac.unit() === x.dataset.unit)));
  $$('#unitDist button').forEach(b => b.addEventListener('click', () => { FK.tac.setUnit(b.dataset.unit); syncUnitSeg(); }));
  $('#menuBtn').addEventListener('click', () => { $('#bkMsg').textContent = ''; diag(); syncUnitSeg(); $('#dlgMenu').showModal(); });
  $('#menuClose').addEventListener('click', () => $('#dlgMenu').close());
  /* Keys that stay on this phone: never written to a backup and never touched by a restore. A half-finished
     protocol must not reappear on another phone, a stale position must not pass as current, and a backup handed
     to someone else must not skip their advanced-procedures warning. */
  const SESSION_ONLY = ['fk.proto.active', 'fk.lastFix', 'fk.advAck'];
  const backedUp = k => k.startsWith('fk.') && !SESSION_ONLY.includes(k);
  const phoneKeys = () => { const ks = []; for (let i = 0; i < localStorage.length; i++) { const k = localStorage.key(i); if (backedUp(k)) ks.push(k); } return ks; };
  const hasPatients = data => { try { const v = JSON.parse(data['fk.patients']); return Array.isArray(v) && v.length > 0; } catch { return false; } };
  $('#bkSave').addEventListener('click', () => {
    const data = {};
    phoneKeys().forEach(k => { data[k] = localStorage.getItem(k); });
    const day = new Date().toISOString().slice(0, 10);
    download(`fieldkit-backup-${day}.json`, JSON.stringify({ app: 'Field Kit', version: APP_VERSION, saved: new Date().toISOString(), data }, null, 1), 'application/json');
    $('#bkMsg').textContent = `Saved ${Object.keys(data).length} items to Downloads. Saved map tiles aren’t included; download those saved maps again on a new phone.` +
      (hasPatients(data) ? ' This file includes patient logs. Keep it private.' : '');
  });

  /* Restore: pick a file, read the two-step confirm timing at click time (emergency-tools.js loads after this file),
     then replace every backed-up key on this phone with the file's. All or nothing. */
  const NOT_BACKUP = 'That file isn’t a Field Kit backup. Pick the .json file the Back up button saved.';
  let pendingRestore = null, restoreSure = false, restoreAt = 0, restoreT = null;
  const confirmTiming = () => (window.FK && FK.tools && FK.tools.confirm) || { ignoreMs: 700, revertMs: 5000 };
  function paintRestore() {
    $('#bkConfirm').hidden = !pendingRestore;
    $('#bkGo').textContent = restoreSure ? 'Confirm restore' : 'Restore';
    $('#bkGo').classList.toggle('ghost', !restoreSure);
  }
  function setRestoreSure(on) {
    clearTimeout(restoreT); restoreSure = on; restoreAt = performance.now();
    if (on) restoreT = setTimeout(() => { restoreSure = false; paintRestore(); }, confirmTiming().revertMs);
    paintRestore();
  }
  function cancelRestore() { pendingRestore = null; setRestoreSure(false); }
  const tqArray = raw => { try { const v = JSON.parse(raw); return Array.isArray(v) ? v.filter(t => t && typeof t === 'object' && okId(t.id)) : []; } catch { return []; } };
  /* Returns 'ok', 'undone' (a write failed and every key was put back) or 'partial' (a put-back failed too). */
  function applyRestore(file) {
    const before = new Map(phoneKeys().map(k => [k, localStorage.getItem(k)]));
    const touched = new Set();
    try {
      before.forEach((_, k) => { if (!(k in file)) { touched.add(k); localStorage.removeItem(k); } });
      Object.entries(file).forEach(([k, v]) => { touched.add(k); localStorage.setItem(k, v); });
      // A tourniquet timer running on this phone is never deleted: merge by id, this phone's entries win.
      const mine = tqArray(before.get('fk.tq'));
      if (mine.length) {
        const ids = new Set(mine.map(t => t.id));
        touched.add('fk.tq');
        localStorage.setItem('fk.tq', JSON.stringify([...mine, ...tqArray(file['fk.tq']).filter(t => !ids.has(t.id))]));
      }
      return 'ok';
    } catch {
      let clean = true;
      touched.forEach(k => { try { if (before.has(k)) localStorage.setItem(k, before.get(k)); else localStorage.removeItem(k); } catch { clean = false; } });
      return clean ? 'undone' : 'partial';
    }
  }
  /* Versions are 'major' or 'major.minor' (6, 6.1, 6.10); each part compares as a whole number, so 6.10 is newer than 6.9. */
  const versionParts = v => { const [a, b] = String(v).split('.'); return [parseInt(a, 10), parseInt(b || '0', 10)]; };
  const newerVersion = (a, b) => { const [a1, a2] = versionParts(a), [b1, b2] = versionParts(b); return a1 > b1 || (a1 === b1 && a2 > b2); };
  $('#bkFile').addEventListener('change', async e => {
    const f = e.target.files && e.target.files[0]; e.target.value = '';
    cancelRestore();
    if (!f) return;
    const msg = $('#bkMsg');
    let b;
    try { b = JSON.parse(await f.text()); } catch { msg.textContent = NOT_BACKUP; return; }
    const d = b && b.data;
    if (!b || b.app !== 'Field Kit' || !d || typeof d !== 'object' || Array.isArray(d) || !Object.values(d).every(v => typeof v === 'string')) { msg.textContent = NOT_BACKUP; return; }
    if (b.version !== undefined && !/^\d+(\.\d+)?$/.test(String(b.version))) { msg.textContent = NOT_BACKUP; return; }   // a missing version counts as older
    if (b.version !== undefined && newerVersion(b.version, APP_VERSION)) { msg.textContent = 'This backup is from a newer version of Field Kit. Update the app first.'; return; }
    const file = {};
    Object.entries(d).forEach(([k, v]) => { if (backedUp(k)) file[k] = v; });
    if (!Object.keys(file).length) { msg.textContent = 'That backup is empty, so nothing was restored.'; return; }
    const when = new Date(b.saved);
    pendingRestore = file;
    msg.textContent = '';
    $('#bkAsk').textContent = `Restore the backup${isNaN(when) ? '' : ' from ' + when.toLocaleString()}? It replaces the markers, routes and areas, tracks, profiles, patient logs and settings on this phone. Running tourniquet timers on this phone are kept.`;
    paintRestore();
  });
  $('#bkGo').addEventListener('click', () => {
    if (!pendingRestore) return;
    if (!restoreSure) { setRestoreSure(true); return; }
    if (performance.now() - restoreAt < confirmTiming().ignoreMs) return;   // a bounced second tap must not replace everything
    const file = pendingRestore;
    emit('restoring');   // let screens drop pending saves so they can't land on top of the restored data
    const r = applyRestore(file);
    if (r !== 'ok') {
      cancelRestore(); emit('restoreFailed');
      $('#bkMsg').textContent = r === 'undone' ? 'Phone storage is full, so nothing was changed. Free some space and try again.'
        : 'Restore failed and some data on this phone may have changed. Back up now if you can, then try again.';
      return;
    }
    location.reload();
  });
  $('#bkNo').addEventListener('click', cancelRestore);
  $('#dlgMenu').addEventListener('close', cancelRestore);

  /* ---------- Updates: tell the user instead of making them relaunch twice ---------- */
  /* The bar never covers or interrupts an emergency: it waits while a protocol, tool or report is open, or while
     the CPR coach, a tourniquet timer, a step timer or the Survival SOS light runs (its Reload would end them), then shows again. */
  let updateReady = false;
  const emergencyBusy = () => {
    const F = window.FK, b = document.body.classList;
    if (b.contains('playing') || b.contains('tooling')) return true;
    if (!F) return false;
    const st = F.protocol && F.protocol.timer && F.protocol.timer();
    return !!((F.tools && F.tools.cpr && F.tools.cpr.running()) || (F.tools && F.tools.tq && F.tools.tq.active().length) || (st && !st.done) ||
      (F.survival && F.survival.lightOn && F.survival.lightOn()));
  };
  /* Search is a full-screen overlay: the bar would sit on top of it, so it waits there and shows again when search closes. */
  const searchOpen = () => !!(window.FK && FK.route && FK.route.isSearch && FK.route.isSearch());
  function paintUpdate() { $('#updBar').hidden = !(updateReady && !emergencyBusy() && !searchOpen()); }
  function updateAvailable() { updateReady = true; paintUpdate(); }
  on('activity', paintUpdate);
  on('route', paintUpdate);
  on('search', paintUpdate);
  if ('serviceWorker' in navigator && window.isSecureContext) {
    let hadController = !!navigator.serviceWorker.controller;
    navigator.serviceWorker.addEventListener('controllerchange', () => {
      if (hadController) updateAvailable();
      hadController = true;
    });
  }
  $('#updReload').addEventListener('click', () => location.reload());
  $('#updBtn').addEventListener('click', async () => {
    if (!navigator.onLine) { toast('Connect to the internet to check for updates.'); return; }
    const reg = navigator.serviceWorker && await navigator.serviceWorker.getRegistration();
    if (!reg) { toast('Updates work once the app is installed from its web address.'); return; }
    await reg.update().catch(() => {});
    if (reg.installing || reg.waiting) { toast('Downloading the update. A Reload bar appears when it’s ready.'); return; }
    setTimeout(() => {
      if (updateReady) return;
      toast(reg.installing || reg.waiting ? 'Downloading the update. A Reload bar appears when it’s ready.' : 'You have the latest version.');
    }, 2500);
  });

  /* ---------- Start ---------- */
  setNight(store.get('night', false));
  $$('#unitSeg button').forEach(x => x.setAttribute('aria-selected', String(x.dataset.unit === unit)));
  restoreInputs();
  calc();
  renderFix(); renderStatus();
  renderDecl(); lastApplied = appliedDecl();
  showView(view);
  showTab(store.get('tab', 'tactical'));
})();
