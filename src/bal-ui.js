/* ---------- Ballistics screen: the profile, the shot, the answer card and the dope card. The solver is BAL (ballistics.js);
   the words for each sight are BALS (bal-sight.js). The load lives in the profile and is edited in the profile editor only
   (bal-edit.js, which loads after this file and reaches the screen through FK.bal). ---------- */
(() => {
  const FK = window.FK;
  const { $, $$, store, toast, esc, okId } = FK;
  /* The one reader of a typed number: blank is null, a plain decimal is its value (a leading typographic minus, U+2212, counts as a
     minus: the fields that can be below zero open the ordinary keyboard), anything else is NaN, which no range accepts. */
  const parseNum = text => {
    const t = String(text === undefined || text === null ? '' : text).trim().replace(/^\u2212/, '-');
    if (t === '') return null;
    return /^[+-]?(\d+\.?\d*|\.\d+)$/.test(t) ? Number(t) : NaN;
  };
  const read = id => parseNum($('#' + id).value);
  const num = el => { const v = parseNum(el.value); return Number.isFinite(v) ? v : 0; };   // blank or unreadable as 0 (wind, card length)

  const PRESETS = [
    { id: 'p556m193', name: 'Sellier & Bellot 5.56×45 M193 55 gr FMJ, 23.5″ barrel', bc: 0.127, model: 'G7', w: 55, mv: 3301, sight: 2.6, zero: 100 },
    { id: 'p556ss109', name: 'RWS 5.56x45 NATO Ball SS109 62 gr, 20″ barrel', bc: 0.151, model: 'G7', w: 62, mv: 3035, sight: 2.6, zero: 100 },
    { id: 'p223', name: 'Federal Gold Medal .223 Rem 77 gr SMK, 24″ barrel', bc: 0.188, model: 'G7', w: 77, mv: 2720, sight: 2.6, zero: 100 },
    { id: 'p76239sb', name: 'Sellier & Bellot 7.62×39 124 gr FMJ, 20.5″ barrel', bc: 0.286, model: 'G1', w: 124, mv: 2421, sight: 2.0, zero: 100 },
    { id: 'p65cm', name: 'Hornady 6.5 Creedmoor 140 gr ELD-M, 24″ barrel', bc: 0.326, model: 'G7', w: 140, mv: 2710, sight: 1.5, zero: 100 },
    { id: 'p308', name: 'Federal Gold Medal .308 Win 175 gr SMK, 24″ barrel', bc: 0.25, model: 'G7', w: 175, mv: 2600, sight: 1.5, zero: 100 }
  ];
  const F = id => $('#' + id);
  /* What can be seen: the visual viewport where there is one (a phone keyboard shrinks only that), else the window. */
  const seen = () => { const v = window.visualViewport; return v && Number.isFinite(v.height) ? { top: v.offsetTop || 0, height: v.height } : { top: 0, height: innerHeight }; };
  const SHOT_FIELDS = ['bRange', 'bAngle', 'bWind', 'bClock', 'bTemp', 'bAlt', 'bPress', 'bRH', 'bMax', 'bStep'];   // what the screen stores besides the profile id
  let showAll = false;                           // "Show all units": off whenever the screen opens or the profile changes; never stored
  let frozen = false;                            // a backup is being restored: nothing is written over it

  /* ---------- Profiles ----------
     A profile: { id, name, bc, model, w, mv, sight (height, in), zero, optic?, zeroAtm?, mv0? }. The built-in loads (PRESETS) are
     read-only; the person's own profiles are stored under 'profiles'. Whatever comes out of storage or a backup goes through
     clean() first, so a hand-edited or damaged entry cannot break the screen or inject markup. */
  /* Ids that were once built in. A stored selection naming one becomes an own profile named for what it was. */
  const RETIRED = { p556: '5.56 NATO 62 gr (old built-in)', p76239: '7.62\u00d739 123 gr (old built-in)' };
  /* The click sizes the editor offers for each unit; a stored turret may carry any of them under any unit (as before). */
  const UNITS = ['mil', 'moa', 'iphy'];
  const CLICK_SIZES = Object.freeze({ mil: Object.freeze([0.1, 0.05]), moa: Object.freeze([0.25, 0.125, 0.5, 1]), iphy: Object.freeze([0.25, 0.125, 0.5, 1]) });
  const CLICKS = [...new Set([].concat(CLICK_SIZES.mil, CLICK_SIZES.moa, CLICK_SIZES.iphy))];
  const has = (o, k) => Object.prototype.hasOwnProperty.call(o, k);
  const isObj = v => !!v && typeof v === 'object' && !Array.isArray(v);
  const fin = FK.fin;
  const copy = p => JSON.parse(JSON.stringify(p));

  /* ---------- The shared rules: one definition each, used here and by the editor (through FK.balHost) ----------
     RANGE: what a real rifle, load and air can have. [low, high], both allowed. */
  const RANGE = Object.freeze({
    temp: [-60, 140], alt: [-2000, 30000], press: [8, 33], rh: [0, 100],                 // °F, ft, inHg (station), %
    bc: [0.05, 1.2], w: [1, 1000], mv: [300, 5000], zero: [5, 1000], sight: [0, 6]       // -, gr (blank or 0 also), fps, yd, in
  });
  const within = (v, k) => fin(v) && v >= RANGE[k][0] && v <= RANGE[k][1];
  /* A load the screen can solve: coefficient, velocity and zero inside their ranges; weight blank, 0 or inside; sight height blank or inside. */
  const loadOk = p => !!p && within(p.bc, 'bc') && within(p.mv, 'mv') && within(p.zero, 'zero')
    && (p.w === undefined || p.w === 0 || within(p.w, 'w')) && (p.sight === undefined || within(p.sight, 'sight'));
  /* A drop reticle's marks: 1 to 10 numbers, each above 0 and larger than the one before. */
  const marksOk = m => Array.isArray(m) && m.length >= 1 && m.length <= 10 && m.every((x, i) => fin(x) && x > 0 && (i === 0 || x > m[i - 1]));

  function cleanOptic(o) {
    if (!isObj(o)) return null;
    if (o.type === 'dot') return o.unit === undefined ? { type: 'dot' } : UNITS.includes(o.unit) ? { type: 'dot', unit: o.unit } : null;
    if (!UNITS.includes(o.unit)) return null;
    if (o.type === 'turret') return CLICKS.includes(o.click) ? { type: 'turret', unit: o.unit, click: o.click } : null;
    if (o.type === 'reticle') return marksOk(o.marks) ? { type: 'reticle', unit: o.unit, marks: o.marks.slice() } : null;   // one bad mark drops the sight
    return null;
  }
  function cleanAtm(z) {
    if (!isObj(z) || !within(z.temp, 'temp')) return null;
    const alt = within(z.alt, 'alt'), press = within(z.press, 'press');
    if (!alt && !press) return null;
    const out = { temp: z.temp };
    if (alt) out.alt = z.alt;
    if (press) out.press = z.press;
    out.rh = fin(z.rh) ? z.rh : 50;
    return out;
  }
  /* A safe profile, or null (no usable id or name, or the id belongs to a built-in load). Load numbers outside RANGE are kept as
     they are (the person can still open and fix them); the screen will not solve with them (loadOk). */
  function clean(raw) {
    if (!isObj(raw) || !okId(raw.id) || typeof raw.name !== 'string' || PRESETS.some(x => x.id === raw.id)) return null;
    const p = { id: raw.id, name: raw.name.slice(0, 60) };
    ['bc', 'w', 'mv', 'sight', 'zero'].forEach(k => { if (fin(raw[k])) p[k] = raw[k]; });
    if (raw.model === 'G1' || raw.model === 'G7') p.model = raw.model;
    const optic = cleanOptic(raw.optic), zeroAtm = cleanAtm(raw.zeroAtm);
    if (optic) p.optic = optic;
    if (zeroAtm) p.zeroAtm = zeroAtm;
    if (fin(raw.mv0) && raw.mv0 > 0) p.mv0 = raw.mv0;
    return p;
  }
  /* Key order of a stored profile: the fields every profile has first, in the order v7.8 wrote them. */
  const ordered = p => {
    const out = {};
    ['id', 'name', 'bc', 'model', 'w', 'mv', 'sight', 'zero', 'optic', 'zeroAtm', 'mv0'].forEach(k => { if (has(p, k)) out[k] = p[k]; });
    return out;
  };

  let profiles = [];
  (() => {
    const raw = store.get('profiles', []), seen = new Set();
    (Array.isArray(raw) ? raw : []).forEach(r => { const p = clean(r); if (p && !seen.has(p.id)) { seen.add(p.id); profiles.push(ordered(p)); } });
  })();
  const firstBuiltIn = () => PRESETS.find(x => x.id === 'p308') || PRESETS[0];
  const ownProfile = id => profiles.find(x => x.id === id) || null;
  const anyProfile = id => ownProfile(id) || PRESETS.find(x => x.id === id) || null;
  let cur = firstBuiltIn().id;                 // the selected profile: always a real one, own or built in

  const persist = () => store.set('profiles', profiles);

  function fillProfiles() {
    const opt = p => `<option value="${esc(p.id)}">${esc(p.name)}</option>`;
    F('bProfile').innerHTML =
      (profiles.length ? `<optgroup label="My profiles">${profiles.map(opt).join('')}</optgroup>` : '') +
      `<optgroup label="Starting points">${PRESETS.map(opt).join('')}</optgroup>`;
    F('bProfile').value = cur;
  }
  function choose(id) {
    if (id !== cur) showAll = false;               // a save of the same profile keeps it
    cur = id;
    fillProfiles();
    saveInputs();
  }
  function select(id) {
    if (!anyProfile(id)) return;
    choose(id);
    calc();
  }
  /* Add or replace by id. Nothing changes if the phone's storage refuses the write. Returns the cleaned profile, or null. */
  function save(raw) {
    const p = clean(raw);
    if (!p) return null;
    const before = profiles, at = profiles.findIndex(x => x.id === p.id), q = ordered(p);
    profiles = at < 0 ? profiles.concat([q]) : profiles.map(x => x.id === p.id ? q : x);
    if (!persist()) { profiles = before; toast(FK.FULL_MSG); return null; }
    fillProfiles();
    if (cur === p.id) { saveInputs(); calc(); }
    return copy(q);
  }
  function remove(id) {
    if (!ownProfile(id)) return;
    const before = profiles;
    profiles = profiles.filter(x => x.id !== id);
    if (!persist()) { profiles = before; toast(FK.FULL_MSG); return; }
    if (cur === id) { choose(firstBuiltIn().id); calc(); }
    fillProfiles();
  }
  const newId = () => {
    let id;
    do id = 'u' + Date.now().toString(36) + Math.floor(Math.random() * 1296).toString(36); while (anyProfile(id));
    return id;
  };

  F('bProfile').addEventListener('change', e => select(e.target.value));
  function saveInputs() {
    if (frozen) return;
    const s = { profile: cur };
    SHOT_FIELDS.forEach(id => { s[id] = F(id).value; });
    store.set('bal', s);
  }
  /* The load a stored copy from before v7.9 carried in its own keys (bBC, bModel, ...); only the migration to "Custom" reads it. */
  function storedLoad(s) {
    const n = k => { const v = parseFloat(s[k]); return Number.isFinite(v) ? v : undefined; };
    return { bc: n('bBC'), model: s.bModel, w: n('bW'), mv: n('bMV'), sight: n('bSH'), zero: n('bZero') };
  }
  /* The stored selection decides what is selected, and the profile always shows its own numbers. The shot, conditions and
     card fields are restored as stored; older copies carry extra keys, which are ignored. A stored "custom" (v7.8's unsaved
     entry) or a retired built-in becomes the profile "Custom" when a BC and a velocity were stored, otherwise the default
     built-in load is selected. */
  function restoreInputs() {
    const s = store.get('bal', null);
    if (!isObj(s)) { cur = firstBuiltIn().id; fillProfiles(); return; }
    SHOT_FIELDS.forEach(id => {
      const el = F(id);
      if (typeof s[id] === 'string' || typeof s[id] === 'number') el.value = s[id];
      if (el.tagName === 'SELECT' && el.selectedIndex < 0) {         // a value that is not one of the choices: the field's default
        const d = [...el.options].find(o => o.defaultSelected) || el.options[0];
        el.value = d.value;
      }
    });
    let keepStored = false;                      // a failed profile write leaves the stored selection as it was, so the next open retries
    if (anyProfile(s.profile)) cur = s.profile;
    else if (s.profile === 'custom' || (typeof s.profile === 'string' && has(RETIRED, s.profile))) {
      const old = storedLoad(s), name = s.profile === 'custom' ? 'Custom' : RETIRED[s.profile];
      const c = old.bc > 0 && old.mv > 0 ? clean({ id: 'ucustom', name, ...old }) : null;
      if (c) {
        const q = ordered(c);
        profiles = ownProfile('ucustom') ? profiles.map(x => x.id === 'ucustom' ? q : x) : profiles.concat([q]);
        if (!persist()) keepStored = true;
        cur = 'ucustom';
      } else cur = firstBuiltIn().id;
    } else cur = firstBuiltIn().id;
    fillProfiles();
    if (!keepStored) saveInputs();               // the stored copy now holds the selected profile and the shot only
  }

  /* ---------- The answer ---------- */
  const MSG = {
    range: 'Enter a range from 1 to 3,000 yd.',
    profile: 'This profile needs a ballistic coefficient, a velocity and a zero range. Tap Edit.',
    reach: "Bullet doesn't reach that range with these inputs.",
    cond: 'Check the conditions: temperature, altitude, pressure or humidity is out of range.',
    wind: 'Enter a wind speed from 0 to 100 mph.',
    angle: 'Enter an incline from -60 to 60 degrees.'
  };
  const inside = (v, lo, hi) => v >= lo && v <= hi;
  const label = yd => String(Number(yd.toFixed(1)));          // 500 -> "500", 36.5 -> "36.5"
  const fx = (v, d) => { const t = v.toFixed(d); return /^-0(\.0+)?$/.test(t) ? t.slice(1) : t; };   // never "-0.0"

  /* A column of the answer card: label, then the lines. lines: [main, sub] for a sight, or the three every-unit lines; more: the
     other units added beneath a sight's own lines (Show all units). */
  function paint(el, name, lines, more) {
    el.textContent = '';
    const add = (cls, text) => { const d = document.createElement('div'); d.className = cls; d.textContent = text; el.appendChild(d); };
    add('k', name);
    lines.forEach((t, i) => { if (t) add(i === 0 ? 'v' : lines.length === 3 ? 'v2' : 's', t); });
    (more || []).forEach(t => add('v2 more', t));
  }
  function nothing(text) {
    paint(F('solElev'), 'ELEVATION', ['—']); paint(F('solWind'), 'WINDAGE', ['—']);
    F('solSub').textContent = text;
    F('solution').classList.add('msg');
    $('#dope').innerHTML = '';
    F('dopeKey').textContent = '';
    fitDope();
  }
  /* The air the zero was made in, with the fields the solver wants all present (no pressure = from altitude). */
  const zeroAir = z => z && { temp: z.temp, alt: z.alt === undefined ? 0 : z.alt, press: z.press === undefined ? 0 : z.press, rh: z.rh };
  /* The profile row's sight and zero lines and the Show all units button. Returns whether the profile has a sight. */
  function head(p) {
    const load = BALS.loadLine(p);
    F('bLoad').textContent = load; F('bLoad').hidden = !load;
    F('bStart').hidden = !(p && PRESETS.some(x => x.id === p.id));      // a built-in load: urge a chronograph reading
    F('bSight').textContent = BALS.describe(p && p.optic);
    const z = BALS.zeroLine(p && p.zeroAtm);
    F('bZeroLine').textContent = z; F('bZeroLine').hidden = !z;
    const sighted = !!(p && p.optic);
    F('bAll').hidden = !sighted;
    F('bAll').setAttribute('aria-pressed', String(sighted && showAll));
    F('bAll').textContent = sighted && showAll ? 'Hide other units' : 'Show all units';
    return sighted;
  }
  function condLine() {
    const or = (v, d) => v === null ? d : v, show = v => fin(v) ? label(v) : '—';         // something unreadable shows as a dash
    const t = or(read('bTemp'), 59), press = read('bPress'), alt = or(read('bAlt'), 0), rh = or(read('bRH'), 50);
    F('bCond').textContent = `${show(t)}°F · ${press !== null && fin(press) && press > 0 ? press.toFixed(2) + ' inHg' : show(alt) + ' ft'} · ${show(rh)}%`;
  }

  /* Today's conditions from the screen's fields, with the screen's defaults (59 °F, sea level, 50 %), or null when one is out of range. */
  function shotAir() {
    const or = (v, d) => v === null ? d : v;
    const temp = or(read('bTemp'), 59), alt = or(read('bAlt'), 0), p = read('bPress'), rh = or(read('bRH'), 50);
    if (!within(temp, 'temp') || !within(alt, 'alt') || (p !== null && !within(p, 'press')) || !within(rh, 'rh')) return null;
    return { temp, alt, press: p === null ? 0 : p, rh };
  }

  function calc() {
    const p = anyProfile(cur);
    const sighted = head(p);
    condLine();
    F('solution').classList.remove('msg');
    const optic = sighted ? p.optic : null;                      // null: every unit
    const cardSight = showAll ? null : optic;                    // the dope card shows every unit while Show all units is on
    const target = read('bRange') === null ? NaN : read('bRange');
    if (!(inside(target, 1, 3000))) return nothing(MSG.range);
    if (!loadOk(p)) return nothing(MSG.profile);
    const air = shotAir();
    if (!air) return nothing(MSG.cond);
    const { temp, alt, press, rh } = air;
    const wind = num(F('bWind'));
    if (!inside(wind, 0, 100)) return nothing(MSG.wind);
    const angle = read('bAngle') === null ? 0 : read('bAngle');      // unreadable: NaN, refused below
    if (!inside(angle, -60, 60)) return nothing(MSG.angle);

    const max = Math.min(3000, Math.max(50, num(F('bMax')) || 1000));
    const step = +F('bStep').value || 50;
    const table = [];                                            // the yardages shown on the dope card
    for (let r = step; r <= max; r += step) table.push(r);
    const at = table.filter(r => Math.round(r) !== Math.round(p.zero) || r === p.zero);   // the zero's own row, once
    if (!at.includes(p.zero)) at.push(p.zero);
    at.sort((a, b) => a - b);
    const ranges = at.concat([target]);
    const res = BAL.solve({
      bc: p.bc, model: p.model || 'G7', w: p.w || 0, mv: p.mv, sight: p.sight || 0, zero: p.zero, zeroAtm: zeroAir(p.zeroAtm),
      temp, alt, press, rh, wind, clock: +F('bClock').value, angle, ranges
    });
    if (res.error) return nothing(res.error);

    const xs = [...new Set(ranges.filter(r => r > 0))].sort((a, b) => a - b);   // the solver's own order: row i belongs to xs[i]
    const rowFor = x => { const i = xs.indexOf(x); return i >= 0 && res.rows[i] ? { ...res.rows[i], yd: x } : null; };
    const t = rowFor(target);
    if (t) {
      const a = BALS.answer(t, optic), every = BALS.all(t);
      const lines = side => optic ? [a[side].main, a[side].sub] : every[side];
      const more = side => optic && showAll ? every[side].filter(x => x !== a[side].main) : [];     // the sight's own lines stay
      paint(F('solElev'), 'ELEVATION', lines('elev'), more('elev')); paint(F('solWind'), 'WINDAGE', lines('wind'), more('wind'));
      F('solSub').textContent = `At ${label(target)} yd: ${BALS.path(t)}, `
        + `${Math.round(t.fps)} fps, ${Math.round(t.ftlb)} ft-lb, ${t.tof.toFixed(2)} s flight`
        + (t.mach < 1 ? '. Subsonic: expect larger errors.' : '.');
    } else {
      paint(F('solElev'), 'ELEVATION', ['—']); paint(F('solWind'), 'WINDAGE', ['—']);
      F('solSub').textContent = MSG.reach;
      F('solution').classList.add('msg');
    }
    const c = BALS.cols(cardSight), generic = !!cardSight && cardSight.type === 'reticle';   // a reticle's wind columns already carry the drift
    const heads = ['Yd', ...c.elev, ...c.wind, 'Path in', ...(generic ? [] : ['Drift in']), 'fps', 'ft-lb', 'Time s'];
    const rows = at.map(rowFor).filter(Boolean).map(r => {
      const x = BALS.cells(r, cardSight), trans = r.mach < 1.2;
      return `<tr class="${r.yd === p.zero ? 'zero' : ''} ${trans ? 'trans' : ''}"><td>${label(r.yd)}${trans ? ' \u2020' : ''}</td>` +
        [...x.elev, ...x.wind, fx(r.dropIn, 1), ...(generic ? [] : [fx(Math.abs(r.windIn), 1)]), Math.round(r.fps), Math.round(r.ftlb), r.tof.toFixed(2)]
          .map(v => `<td>${esc(String(v))}</td>`).join('') + '</tr>';
    });
    $('#dope').innerHTML = `<thead><tr>${heads.map(h => `<th>${esc(h)}</th>`).join('')}</tr></thead><tbody>${rows.join('')}</tbody>`;
    F('dopeKey').textContent = 'Path: inches above the line of sight; a minus means below.'
      + (generic ? '' : ' Drift: inches the wind moves the bullet, shown without a sign.');
    fitDope();
  }
  /* Only a table wider than its box shows the swipe cue and a sticky first column (the Survival tables' pattern). Measured when the
     screen is visible: after each calculation, when the screen is shown and when the phone turns. */
  function fitDope() {
    const w = $('#dope').closest('.tablewrap');
    w.style.maxHeight = Math.round(Math.max(240, 0.7 * seen().height)) + 'px';     // scrolls in its own box: at most 70 % of what can be seen
    w.classList.remove('wide');
    const wide = w.scrollWidth > w.clientWidth + 1;
    w.classList.toggle('wide', wide);
    F('dopeCue').hidden = !wide;
  }
  let calcT;
  const later = () => { clearTimeout(calcT); calcT = setTimeout(() => { saveInputs(); calc(); }, 150); };
  SHOT_FIELDS.forEach(id => F(id).addEventListener('input', later));
  F('bAll').addEventListener('click', () => { showAll = !showAll; calc(); });
  F('bCondBtn').addEventListener('click', () => {
    const open = F('bCondFields').hidden;
    F('bCondFields').hidden = !open;
    F('bCondBtn').setAttribute('aria-expanded', String(open));
  });
  /* A backup is being restored: drop the pending save so it cannot land on top of it. */
  FK.on('restoring', () => { frozen = true; clearTimeout(calcT); });
  FK.on('restoreFailed', () => { frozen = false; later(); });
  /* A short screen (keyboard up): while a Ballistics input has focus and the VISIBLE height is 480 px or less, the answer card is
     compact and pinned at the top of what can be seen, and the focused field is kept between the card and whatever covers the
     bottom (the tab bar when it is inside the visible viewport, otherwise the bottom of the visible viewport). A phone keyboard
     shrinks only the visual viewport, so the height comes from window.visualViewport where there is one, else innerHeight. */
  const view = $('#view-ballistics'), card = F('solution'), SHORT = 480, GAP = 4;
  const balShort = h => typeof h === 'number' && Number.isFinite(h) && h <= SHORT;
  const typing = el => !!el && !view.hidden && view.contains(el) && el.matches('input, select') && !el.closest('.bal-profile');
  function pin() {
    const el = document.activeElement, vis = seen(), on = typing(el) && balShort(vis.height);
    card.classList.toggle('compact', on);
    if (!on) return;
    const top = $('.top');
    document.documentElement.style.setProperty('--balTop', Math.max(top ? top.getBoundingClientRect().bottom : 0, vis.top) + 'px');
    const bar = $('.tabbar'), barTop = bar ? bar.getBoundingClientRect().top : Infinity, visBottom = vis.top + vis.height;
    const cover = barTop < visBottom ? barTop : visBottom;
    for (let i = 0; i < 4; i++) {                              // the card sticks part way through a scroll: measure again
      const c = card.getBoundingClientRect(), f = el.getBoundingClientRect();
      let d = 0;
      if (f.bottom > cover - GAP) d = f.bottom - (cover - GAP);
      if (f.top - d < c.bottom + GAP) d = f.top - (c.bottom + GAP);
      if (Math.abs(d) < 1) break;
      const y = scrollY;
      scrollBy(0, d);
      if (scrollY === y) break;                                // nothing more to scroll
    }
  }
  const pinSoon = () => { pin(); requestAnimationFrame(pin); setTimeout(pin, 150); };   // after the browser's own scroll to the field
  view.addEventListener('focusin', pinSoon);
  view.addEventListener('focusout', () => setTimeout(pin, 0));
  addEventListener('resize', () => { if (!view.hidden) pin(); });
  if (window.visualViewport) {
    visualViewport.addEventListener('resize', () => { pin(); if (!view.hidden) fitDope(); });
    visualViewport.addEventListener('scroll', pin);
  }
  /* The screen opens with every unit hidden again and the conditions folded away. */
  let was = false;
  FK.on('shown', s => {
    const now = s.tab === 'tactical' && s.view === 'ballistics';
    if (now && !was) {
      showAll = false;
      F('bCondFields').hidden = true; F('bCondBtn').setAttribute('aria-expanded', 'false');
      calc();
    }
    was = now;
  });
  addEventListener('resize', () => { if (!view.hidden) fitDope(); });

  function init() {
    restoreInputs();
    calc();
  }
  /* The surface other screens and tests use (edit is added by bal-edit.js). */
  FK.bal = {
    init, calc, clean, save, remove, select, shotAir,
    profiles: () => profiles.map(copy),
    selected: () => copy(anyProfile(cur))
  };
  /* For src/bal-edit.js only: its read-only seam to the screen's profiles and the one definition of each shared rule. FK.bal stays
     the public surface; nothing else may depend on this. find gives a copy of a profile, own or built in, with whether it is the
     person's own. RANGE, CLICK_SIZES, within, marksOk, parseNum and zeroAir are the rules the editor must apply exactly as the screen
     does; nameTaken and freeName keep names unique. */
  const nameKey = n => String(n).trim().slice(0, 60).toLowerCase();
  /* Whether another profile (own, except exceptId, or built in) already has this name, trimmed and compared without regard to case. */
  const nameTaken = (name, exceptId) => profiles.concat(PRESETS).some(p => p.id !== exceptId && nameKey(p.name) === nameKey(name));
  /* A free name for a copy of a built-in load: its name + " (mine)", then " (mine 2)" and so on, cut to fit 60 characters. */
  function freeName(base) {
    for (let n = 1; ; n++) {
      const tail = n === 1 ? ' (mine)' : ` (mine ${n})`, name = base.slice(0, 60 - tail.length).trimEnd() + tail;
      if (!nameTaken(name)) return name;
    }
  }
  FK.balHost = {
    newId, RANGE, CLICK_SIZES, within, marksOk, nameTaken, freeName, parseNum, zeroAir,
    find: id => { const p = anyProfile(id); return p ? { profile: copy(p), own: !!ownProfile(id) } : null; }
  };
  FK._test.presets = () => PRESETS.map(p => ({ ...p }));
  FK._test.balState = () => ({ profile: cur, showAll });
  FK._test.balShort = balShort;
  init();
})();
