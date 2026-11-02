/* ---------- App ---------- */
(() => {
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const root = document.documentElement;
  const APP_VERSION = '5';
  const FULL_MSG = 'Couldn’t save: phone storage for Field Kit is full. Back up, then delete old tracks or map areas.';
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
  $$('.tabbar button').forEach(b => b.addEventListener('click', () => showTab(b.dataset.tab)));
  $$('#tacSeg button').forEach(b => b.addEventListener('click', () => showView(b.dataset.view)));

  /* ---------- GPS ---------- */
  let watchId = null, fix = store.get('lastFix', null), llFormat = store.get('llFormat', 'dec') === 'dms' ? 'dms' : 'dec';
  if (!fix || !okLatLon(fix.lat, fix.lon)) fix = null;
  const navVisible = () => root.dataset.tab === 'tactical' && (view === 'position' || view === 'map') && !document.hidden;
  const gpsWanted = () => !document.hidden && (navVisible() || !!(window.FK && FK.isRecording && FK.isRecording()));

  function setStatus(msg, warn) { const s = $('#gpsStatus'); s.textContent = msg; s.classList.toggle('warn', !!warn); }

  function startGps() {
    if (watchId !== null) return;
    if (!('geolocation' in navigator)) { setStatus('This browser has no location support.', true); return; }
    if (!window.isSecureContext) { setStatus('Location needs HTTPS. Open the app from its GitHub Pages address.', true); return; }
    setStatus(fix ? 'Updating position…' : 'Getting a GPS fix. Open sky helps.');
    watchId = navigator.geolocation.watchPosition(onFix, onGpsErr, { enableHighAccuracy: true, maximumAge: 2000, timeout: 30000 });
  }
  function stopGps() { if (watchId !== null) { navigator.geolocation.clearWatch(watchId); watchId = null; } }

  function onFix(p) {
    const c = p.coords;
    fix = { lat: c.latitude, lon: c.longitude, alt: c.altitude, acc: c.accuracy, spd: c.speed, t: p.timestamp };
    store.set('lastFix', fix);
    setStatus('Live fix, ' + new Date(p.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }));
    renderFix(); renderWps(); renderTarget();
    emit('fix', fix);
  }
  function onGpsErr(e) {
    const msgs = {
      1: 'Location is blocked. Allow location for this site in Chrome’s site settings, then reload.',
      2: 'No GPS signal. Move to open sky.',
      3: 'Still searching for satellites. Move to open sky.'
    };
    setStatus(msgs[e.code] || 'Location error: ' + e.message, true);
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
    $('#sSpd').textContent = fix.spd == null || Number.isNaN(fix.spd) ? '—' : `${(fix.spd * 2.23694).toFixed(1)} mph`;
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
  let decl = store.get('decl', 0);
  if (!fin(decl)) decl = 0;
  $('#decl').value = decl || '';
  $('#decl').addEventListener('input', e => { decl = num(e.target); store.set('decl', decl); renderCompass(); renderWps(); renderTarget(); });

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

  function onOri(e) {
    let h = null;
    if (typeof e.webkitCompassHeading === 'number') h = e.webkitCompassHeading;
    else if (e.alpha != null && (e.absolute || e.type === 'deviceorientationabsolute')) h = 360 - e.alpha;
    if (h == null) return;
    const scr = (screen.orientation && screen.orientation.angle) || 0;
    h = (h + scr + 360) % 360;
    gotOri = true;
    if (heading == null) heading = h;
    else { const d = ((h - heading + 540) % 360) - 180; heading = (heading + d * 0.25 + 360) % 360; }
    renderCompass(); renderTarget();
    emit('heading', trueHeading());
  }
  function startCompass() {
    if (compassOn) return;
    compassOn = true;
    if ('ondeviceorientationabsolute' in window) window.addEventListener('deviceorientationabsolute', onOri);
    else window.addEventListener('deviceorientation', onOri);
    clearTimeout(oriTimer);
    oriTimer = setTimeout(() => { if (!gotOri) $('#hdgRef').textContent = 'No compass sensor found. Distances and bearings to waypoints still work.'; }, 4000);
  }
  function stopCompass() {
    if (!compassOn) return;
    compassOn = false;
    window.removeEventListener('deviceorientationabsolute', onOri);
    window.removeEventListener('deviceorientation', onOri);
  }
  const trueHeading = () => heading == null ? null : (heading + decl + 360) % 360;
  function renderCompass() {
    const th = trueHeading();
    if (th == null) return;
    $('#rose').style.transform = `rotate(${-th}deg)`;
    $('#hdg').textContent = Math.round(th) % 360 + '°';
    const mils = Math.round(th * 6400 / 360) % 6400;
    $('#hdgRef').textContent = `${GEO.cardinal(th)}, ${mils} mils, ${decl ? 'true' : 'magnetic'}`;
  }

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

  /* ---------- Waypoints ---------- */
  let wps = list('wps', w => okId(w.id) && okLatLon(w.lat, w.lon)).map(w => ({ ...w, name: String(w.name ?? 'Waypoint'), alt: fin(w.alt) ? w.alt : null }));
  let targetId = store.get('target', null);
  if (!wps.some(w => w.id === targetId)) targetId = null;
  const saveWps = () => { const ok = store.set('wps', wps) && store.set('target', targetId); emit('wps'); return ok; };
  const fmtDist = m => m < 1000 ? `${Math.round(m)} m` : `${(m / 1000).toFixed(m < 10000 ? 2 : 1)} km`;
  const fmtMi = m => `${(m / 1609.344).toFixed(m < 16093 ? 2 : 1)} mi`;

  /* Returns the waypoint's name, or null if it couldn't be saved (it stays on screen until the app closes). */
  let wpSeq = 0;
  function addWp(lat, lon, name, alt) {
    const n = String(name || '').trim() || `WP ${wps.length + 1}`;
    wps.push({ id: Date.now().toString(36) + (wpSeq++ % 36).toString(36), name: n, lat, lon, alt: fin(alt) ? alt : null, t: Date.now() });
    const ok = saveWps(); renderWps();
    if (!ok) toast(FULL_MSG);
    return ok ? n : null;
  }
  $('#wpMark').addEventListener('click', () => {
    if (!fix) { $('#wpMsg').textContent = 'No GPS fix yet. Wait for a position, then mark.'; return; }
    const n = addWp(fix.lat, fix.lon, $('#wpName').value, fix.alt);
    $('#wpName').value = ''; $('#wpMsg').textContent = n ? `Marked ${n}.` : FULL_MSG;
  });
  $('#wpAdd').addEventListener('click', () => {
    const p = GEO.parseAny($('#wpCoord').value);
    if (!p) { $('#wpMsg').textContent = 'Couldn’t read that location. Try a grid like 18S UJ 23394 07395, or 38.8977, -77.0365, or 38°53′52″N 77°02′11″W.'; return; }
    const n = addWp(p.lat, p.lon, $('#wpName').value);
    $('#wpCoord').value = ''; $('#wpName').value = ''; $('#wpMsg').textContent = n ? `Added ${n}.` : FULL_MSG;
  });

  function renderWps() {
    const ul = $('#wpList');
    if (!wps.length) { ul.innerHTML = '<li><span class="wmeta">No waypoints yet. Mark your position or add a grid.</span></li>'; $('#wpExport').disabled = true; return; }
    $('#wpExport').disabled = false;
    ul.innerHTML = wps.map(w => {
      const g = GEO.toMGRS(w.lat, w.lon);
      let rel = '';
      if (fix) {
        const d = GEO.distance(fix.lat, fix.lon, w.lat, w.lon);
        const b = GEO.bearing(fix.lat, fix.lon, w.lat, w.lon);
        rel = d < 3 ? '<br>You are here' : `<br>${fmtDist(d)} (${fmtMi(d)}) at ${Math.round(b)}° true`;
      }
      const isT = w.id === targetId;
      return `<li class="${isT ? 'target' : ''}" data-id="${w.id}">
        <span class="wname">${esc(w.name)}</span>
        <span class="wmeta">${g ? g.text : w.lat.toFixed(5) + ', ' + w.lon.toFixed(5)}${rel}</span>
        <span class="wact">
          <button class="btn small ${isT ? '' : 'ghost'}" data-act="nav">${isT ? 'Stop' : 'Go to'}</button>
          <button class="btn small ghost" data-act="del" aria-label="Delete ${esc(w.name)}">Delete</button>
        </span></li>`;
    }).join('');
  }
  $('#wpList').addEventListener('click', e => {
    const btn = e.target.closest('button'); if (!btn) return;
    const id = btn.closest('li').dataset.id, w = wps.find(x => x.id === id); if (!w) return;
    if (btn.dataset.act === 'nav') { targetId = targetId === id ? null : id; }
    if (btn.dataset.act === 'del') {
      if (!confirm(`Delete waypoint ${w.name}? This can’t be undone.`)) return;
      wps = wps.filter(x => x.id !== id); if (targetId === id) targetId = null;
    }
    saveWps(); renderWps(); renderTarget();
  });

  function renderTarget() {
    const w = wps.find(x => x.id === targetId), info = $('#tgtInfo'), mark = $('#tgtMark');
    if (!w || !fix) { info.hidden = true; mark.setAttribute('hidden', ''); return; }
    const d = GEO.distance(fix.lat, fix.lon, w.lat, w.lon);
    const b = GEO.bearing(fix.lat, fix.lon, w.lat, w.lon);
    mark.removeAttribute('hidden');
    mark.setAttribute('transform', `rotate(${b} 100 100)`);
    let turn = '';
    const th = trueHeading();
    if (th != null) {
      const off = ((b - th + 540) % 360) - 180;
      turn = Math.abs(off) < 5 ? 'Straight ahead' : `Turn ${Math.round(Math.abs(off))}° ${off > 0 ? 'right' : 'left'}`;
    }
    info.hidden = false;
    info.innerHTML = `<b style="font-size:20px">${esc(w.name)}</b><br>${fmtDist(d)} at ${Math.round(b)}° true${turn ? '<br>' + turn : ''}`;
  }

  $('#wpExport').addEventListener('click', () => {
    const pm = wps.map(w => `  <Placemark><name>${esc(w.name)}</name><Point><coordinates>${w.lon},${w.lat},${w.alt ?? 0}</coordinates></Point></Placemark>`).join('\n');
    const kml = `<?xml version="1.0" encoding="UTF-8"?>\n<kml xmlns="http://www.opengis.net/kml/2.2">\n<Document><name>Field Kit waypoints</name>\n${pm}\n</Document>\n</kml>\n`;
    download(`waypoints-${new Date().toISOString().slice(0, 10)}.kml`, kml, 'application/vnd.google-earth.kml+xml');
    toast('Saved to Downloads. In ATAK: Import → Local SD.');
  });

  /* ---------- Sensors on/off with visibility (saves battery) ---------- */
  function sensors() {
    if (gpsWanted()) startGps(); else stopGps();
    if (navVisible()) startCompass(); else stopCompass();
    tqTick();
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
  F('bSave').addEventListener('click', () => {
    const name = (prompt('Name this profile, e.g. "Tikka .308 – 175 SMK"') || '').trim();
    if (!name) return;
    const p = { id: 'u' + Date.now().toString(36), name };
    for (const [k, fid] of Object.entries(LOAD_FIELDS)) p[k] = k === 'model' ? F(fid).value : num(F(fid));
    profiles.push(p); store.set('profiles', profiles); fillProfiles(p.id); saveInputs(); toast(`Saved ${name}`);
  });
  F('bDel').addEventListener('click', () => {
    const id = F('bProfile').value, p = profiles.find(x => x.id === id);
    if (!p || !confirm(`Delete the ${p.name} profile? This can’t be undone.`)) return;
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

  /* ---------- Tourniquet timers ---------- */
  let tqs = list('tq', t => okId(t.id) && fin(t.start)).map(t => ({ ...t, limb: String(t.limb ?? 'Tourniquet') })), tqInt = null;
  const hms = ms => {
    const s = Math.max(0, Math.floor(ms / 1000));
    return `${Math.floor(s / 3600)}:${String(Math.floor(s / 60) % 60).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;
  };
  function renderTq() {
    $('#tqList').innerHTML = tqs.map(t => `<div class="timer" data-id="${t.id}">
      <b>${hms(Date.now() - t.start)}</b>
      <button class="btn small ghost x" data-act="clear">Clear</button>
      <span class="lbl">${esc(t.limb)}, on at ${new Date(t.start).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
    </div>`).join('');
  }
  function tqTick() {
    const want = root.dataset.tab === 'emergency' && tqs.length && !document.hidden;
    if (want && !tqInt) { renderTq(); tqInt = setInterval(renderTq, 1000); }
    if (!want && tqInt) { clearInterval(tqInt); tqInt = null; }
  }
  $('#tqStart').addEventListener('click', () => {
    tqs.push({ id: Date.now().toString(36), limb: $('#tqLimb').value, start: Date.now() });
    store.set('tq', tqs); renderTq(); tqTick();
  });
  $('#tqList').addEventListener('click', e => {
    const b = e.target.closest('button[data-act="clear"]'); if (!b) return;
    const id = b.closest('.timer').dataset.id, t = tqs.find(x => x.id === id);
    if (!t || !confirm(`Clear the ${t.limb} timer? Only do this once responders have the time.`)) return;
    tqs = tqs.filter(x => x.id !== id); store.set('tq', tqs); renderTq(); tqTick();
  });

  /* ---------- CPR metronome ---------- */
  let ac = null, cprInt = null, count = 0;
  function click() {
    const o = ac.createOscillator(), g = ac.createGain();
    o.frequency.value = count % 30 === 0 ? 1320 : 880;
    g.gain.setValueAtTime(0.0001, ac.currentTime);
    g.gain.exponentialRampToValueAtTime(0.6, ac.currentTime + 0.005);
    g.gain.exponentialRampToValueAtTime(0.0001, ac.currentTime + 0.08);
    o.connect(g).connect(ac.destination); o.start(); o.stop(ac.currentTime + 0.09);
  }
  $('#cprBtn').addEventListener('click', async () => {
    const beat = $('#beat');
    if (cprInt) {
      clearInterval(cprInt); cprInt = null; beat.classList.remove('on'); beat.textContent = '0';
      $('#cprBtn').textContent = 'Start metronome';
      if (!wakeWanted && wakeLock) { await wakeLock.release(); wakeLock = null; }
      return;
    }
    ac = ac || new (window.AudioContext || window.webkitAudioContext)();
    await ac.resume();
    count = 0;
    if ('wakeLock' in navigator && !wakeLock) { try { wakeLock = await navigator.wakeLock.request('screen'); } catch { /* ignore */ } }
    cprInt = setInterval(() => {
      count = count % 30 + 1; click();
      beat.textContent = count; beat.classList.add('on'); setTimeout(() => beat.classList.remove('on'), 120);
      if (navigator.vibrate) navigator.vibrate(25);
    }, 60000 / 110);
    $('#cprBtn').textContent = 'Stop metronome';
  });

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

  /* ---------- Shared API for the map module ---------- */
  window.FK = {
    $, $$, store, toast, esc, on, emit, download, sensors, fin, okId, list, okLatLon, FULL_MSG,
    getFix: () => fix, getWps: () => wps, getTarget: () => targetId,
    toggleTarget(id) { targetId = targetId === id ? null : id; saveWps(); renderWps(); renderTarget(); },
    addWp, trueHeading, setWake, wakeOn: () => wakeWanted,
    tab: () => root.dataset.tab, view: () => view
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
  $('#menuBtn').addEventListener('click', () => { $('#bkMsg').textContent = ''; diag(); $('#dlgMenu').showModal(); });
  $('#menuClose').addEventListener('click', () => $('#dlgMenu').close());
  $('#bkSave').addEventListener('click', () => {
    const data = {};
    for (let i = 0; i < localStorage.length; i++) {
      const k = localStorage.key(i);
      if (k.startsWith('fk.')) data[k] = localStorage.getItem(k);
    }
    const day = new Date().toISOString().slice(0, 10);
    download(`fieldkit-backup-${day}.json`, JSON.stringify({ app: 'Field Kit', version: APP_VERSION, saved: new Date().toISOString(), data }, null, 1), 'application/json');
    $('#bkMsg').textContent = `Saved ${Object.keys(data).length} items to Downloads. Saved map tiles aren’t included; re-download those areas on a new phone.`;
  });
  $('#bkFile').addEventListener('change', async e => {
    const f = e.target.files && e.target.files[0]; e.target.value = '';
    if (!f) return;
    let b;
    try { b = JSON.parse(await f.text()); } catch { $('#bkMsg').textContent = 'That file isn’t a Field Kit backup. Pick the .json file the Back up button saved.'; return; }
    if (!b || b.app !== 'Field Kit' || typeof b.data !== 'object') { $('#bkMsg').textContent = 'That file isn’t a Field Kit backup. Pick the .json file the Back up button saved.'; return; }
    const when = new Date(b.saved);
    if (!confirm(`Restore the backup${isNaN(when) ? '' : ' from ' + when.toLocaleString()}? It replaces the waypoints, tracks, profiles and settings on this phone.`)) return;
    try {
      Object.entries(b.data).forEach(([k, v]) => { if (k.startsWith('fk.')) localStorage.setItem(k, v); });
    } catch { $('#bkMsg').textContent = 'Phone storage is full, so the backup couldn’t be restored. Free some space and try again.'; return; }
    location.reload();
  });

  /* ---------- Updates: tell the user instead of making them relaunch twice ---------- */
  if ('serviceWorker' in navigator && window.isSecureContext) {
    let hadController = !!navigator.serviceWorker.controller;
    navigator.serviceWorker.addEventListener('controllerchange', () => {
      if (hadController) $('#updBar').hidden = false;
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
      if (!$('#updBar').hidden) return;
      toast(reg.installing || reg.waiting ? 'Downloading the update. A Reload bar appears when it’s ready.' : 'You have the latest version.');
    }, 2500);
  });

  /* ---------- Start ---------- */
  setNight(store.get('night', false));
  $$('#unitSeg button').forEach(x => x.setAttribute('aria-selected', String(x.dataset.unit === unit)));
  restoreInputs();
  calc();
  renderFix(); renderWps();
  showView(view);
  showTab(store.get('tab', 'tactical'));
})();
