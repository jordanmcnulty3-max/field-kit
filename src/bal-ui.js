/* ---------- Ballistics screen: the profile, the shot, the answer card and the dope card. The solver is BAL (ballistics.js);
   the words for each sight are BALS (bal-sight.js). The load lives in the profile and is edited in the profile editor only. ---------- */
(() => {
  const FK = window.FK;
  const { $, $$, store, toast, esc, okId } = FK;
  const num = el => { const v = parseFloat(el.value); return Number.isFinite(v) ? v : 0; };

  const PRESETS = [
    { id: 'p556m193', name: 'Sellier & Bellot 5.56×45 M193 55 gr FMJ, 23.5″ barrel', bc: 0.127, model: 'G7', w: 55, mv: 3301, sight: 2.6, zero: 100 },
    { id: 'p556ss109', name: 'RWS 5.56x45 NATO Ball SS109 62 gr, 20″ barrel', bc: 0.151, model: 'G7', w: 62, mv: 3035, sight: 2.6, zero: 100 },
    { id: 'p223', name: 'Federal Gold Medal .223 Rem 77 gr SMK, 24″ barrel', bc: 0.188, model: 'G7', w: 77, mv: 2720, sight: 2.6, zero: 100 },
    { id: 'p76239sb', name: 'Sellier & Bellot 7.62×39 124 gr FMJ, 20.5″ barrel', bc: 0.286, model: 'G1', w: 124, mv: 2421, sight: 2.0, zero: 100 },
    { id: 'p65cm', name: 'Hornady 6.5 Creedmoor 140 gr ELD-M, 24″ barrel', bc: 0.326, model: 'G7', w: 140, mv: 2710, sight: 1.5, zero: 100 },
    { id: 'p308', name: 'Federal Gold Medal .308 Win 175 gr SMK, 24″ barrel', bc: 0.25, model: 'G7', w: 175, mv: 2600, sight: 1.5, zero: 100 }
  ];
  const F = id => $('#' + id);
  const SHOT_FIELDS = ['bRange', 'bAngle', 'bWind', 'bClock', 'bTemp', 'bAlt', 'bPress', 'bRH', 'bMax', 'bStep'];   // what the screen stores besides the profile id
  let showAll = false;                           // "Show all units": off whenever the screen opens or the profile changes; never stored
  let frozen = false;                            // a backup is being restored: nothing is written over it

  /* ---------- Profiles ----------
     A profile: { id, name, bc, model, w, mv, sight (height, in), zero, optic?, zeroAtm?, mv0? }. The built-in loads (PRESETS) are
     read-only; the person's own profiles are stored under 'profiles'. Whatever comes out of storage or a backup goes through
     clean() first, so a hand-edited or damaged entry cannot break the screen or inject markup. */
  const RETIRED = ['p556', 'p76239'];                    // ids that were once built in; a stored selection naming one is treated as Custom
  const UNITS = ['mil', 'moa', 'iphy'], CLICKS = [0.1, 0.05, 0.25, 0.125, 0.5, 1];
  const has = (o, k) => Object.prototype.hasOwnProperty.call(o, k);
  const isObj = v => !!v && typeof v === 'object' && !Array.isArray(v);
  const fin = FK.fin;
  const copy = p => JSON.parse(JSON.stringify(p));

  function cleanOptic(o) {
    if (!isObj(o)) return null;
    if (o.type === 'dot') return o.unit === undefined ? { type: 'dot' } : UNITS.includes(o.unit) ? { type: 'dot', unit: o.unit } : null;
    if (!UNITS.includes(o.unit)) return null;
    if (o.type === 'turret') return CLICKS.includes(o.click) ? { type: 'turret', unit: o.unit, click: o.click } : null;
    if (o.type === 'reticle' && Array.isArray(o.marks)) {
      const marks = o.marks.filter(m => fin(m) && m > 0).slice(0, 10);
      return marks.length && marks.every((m, i) => i === 0 || m > marks[i - 1]) ? { type: 'reticle', unit: o.unit, marks } : null;
    }
    return null;
  }
  const ZT = [-60, 140], ZA = [-2000, 30000];     // zero conditions a person could really have: temperature °F, altitude ft
  function cleanAtm(z) {
    if (!isObj(z) || !fin(z.temp) || z.temp < ZT[0] || z.temp > ZT[1]) return null;
    const alt = fin(z.alt) && z.alt >= ZA[0] && z.alt <= ZA[1], press = fin(z.press) && z.press > 0;
    if (!alt && !press) return null;
    const out = { temp: z.temp };
    if (alt) out.alt = z.alt;
    if (press) out.press = z.press;
    out.rh = fin(z.rh) ? z.rh : 50;
    return out;
  }
  /* A safe profile, or null (no usable id or name, or the id belongs to a built-in load). */
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
    SHOT_FIELDS.forEach(id => { if (typeof s[id] === 'string' || typeof s[id] === 'number') F(id).value = s[id]; });
    let keepStored = false;                      // a failed profile write leaves the stored selection as it was, so the next open retries
    if (anyProfile(s.profile)) cur = s.profile;
    else if (s.profile === 'custom' || RETIRED.includes(s.profile)) {
      const old = storedLoad(s);
      const c = old.bc > 0 && old.mv > 0 ? clean({ id: 'ucustom', name: 'Custom', ...old }) : null;
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
  const given = id => F(id).value.trim() !== '';
  const inside = (v, lo, hi) => v >= lo && v <= hi;
  const label = yd => String(Number(yd.toFixed(1)));          // 500 -> "500", 36.5 -> "36.5"
  const fx = (v, d) => { const t = v.toFixed(d); return /^-0(\.0+)?$/.test(t) ? t.slice(1) : t; };   // never "-0.0"

  /* A column of the answer card: label, then the lines. */
  function paint(el, name, lines) {
    el.textContent = '';
    const add = (cls, text) => { const d = document.createElement('div'); d.className = cls; d.textContent = text; el.appendChild(d); };
    add('k', name);
    lines.forEach((t, i) => { if (t) add(i === 0 ? 'v' : lines.length === 3 ? 'v2' : 's', t); });
  }
  function nothing(text) {
    paint(F('solElev'), 'ELEVATION', ['—']); paint(F('solWind'), 'WINDAGE', ['—']);
    F('solSub').textContent = text;
    F('solution').classList.add('msg');
    $('#dope').innerHTML = '';
    fitDope();
  }
  /* The air the zero was made in, with the fields the solver wants all present (no pressure = from altitude). */
  const zeroAir = z => z && { temp: z.temp, alt: z.alt === undefined ? 0 : z.alt, press: z.press === undefined ? 0 : z.press, rh: z.rh };
  /* The profile row's sight and zero lines and the Show all units button. Returns whether the profile has a sight. */
  function head(p) {
    F('bSight').textContent = BALS.describe(p && p.optic);
    const z = BALS.zeroLine(p && p.zeroAtm);
    F('bZeroLine').textContent = z; F('bZeroLine').hidden = !z;
    const sighted = !!(p && p.optic);
    F('bAll').hidden = !sighted;
    F('bAll').setAttribute('aria-pressed', String(sighted && showAll));
    return sighted;
  }
  function condLine() {
    const t = given('bTemp') ? num(F('bTemp')) : 59, press = num(F('bPress')), alt = num(F('bAlt'));
    F('bCond').textContent = `${label(t)}°F · ${given('bPress') && press > 0 ? press.toFixed(2) + ' inHg' : label(alt) + ' ft'} · ${label(given('bRH') ? num(F('bRH')) : 50)}%`;
  }

  function calc() {
    const p = anyProfile(cur);
    const sighted = head(p);
    condLine();
    F('solution').classList.remove('msg');
    const optic = sighted && !showAll ? p.optic : null;          // null: every unit
    const target = given('bRange') ? parseFloat(F('bRange').value) : NaN;
    if (!(inside(target, 1, 3000))) return nothing(MSG.range);
    if (!p || !(p.bc > 0) || !(p.mv > 0) || !(p.zero > 0)) return nothing(MSG.profile);
    const temp = given('bTemp') ? num(F('bTemp')) : 59, alt = num(F('bAlt')), press = num(F('bPress')), rh = given('bRH') ? num(F('bRH')) : 50;
    if (!inside(temp, -60, 140) || !inside(alt, -2000, 30000) || (given('bPress') && !(press > 0)) || !inside(rh, 0, 100)) return nothing(MSG.cond);
    const wind = num(F('bWind'));
    if (!inside(wind, 0, 100)) return nothing(MSG.wind);
    const angle = num(F('bAngle'));
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
      const a = BALS.answer(t, optic), lines = side => optic ? [a[side].main, a[side].sub] : BALS.all(t)[side === 'elev' ? 'elev' : 'wind'];
      paint(F('solElev'), 'ELEVATION', lines('elev')); paint(F('solWind'), 'WINDAGE', lines('wind'));
      F('solSub').textContent = `At ${label(target)} yd: drop ${Math.abs(t.dropIn).toFixed(1)} in, drift ${Math.abs(t.windIn).toFixed(1)} in, `
        + `${Math.round(t.fps)} fps, ${Math.round(t.ftlb)} ft-lb, ${t.tof.toFixed(2)} s flight`
        + (t.mach < 1 ? '. Subsonic: expect larger errors.' : '.');
    } else {
      paint(F('solElev'), 'ELEVATION', ['—']); paint(F('solWind'), 'WINDAGE', ['—']);
      F('solSub').textContent = MSG.reach;
      F('solution').classList.add('msg');
    }
    const c = BALS.cols(optic), generic = !!optic && optic.type === 'reticle';   // a reticle's wind columns already carry the drift
    const heads = ['Yd', ...c.elev, ...c.wind, 'Drop in', ...(generic ? [] : ['Drift in']), 'fps', 'ft-lb', 'Time s'];
    const rows = at.map(rowFor).filter(Boolean).map(r => {
      const x = BALS.cells(r, optic);
      return `<tr class="${r.yd === p.zero ? 'zero' : ''} ${r.mach < 1.2 ? 'trans' : ''}"><td>${label(r.yd)}</td>` +
        [...x.elev, ...x.wind, fx(r.dropIn, 1), ...(generic ? [] : [fx(Math.abs(r.windIn), 1)]), Math.round(r.fps), Math.round(r.ftlb), r.tof.toFixed(2)]
          .map(v => `<td>${esc(String(v))}</td>`).join('') + '</tr>';
    });
    $('#dope').innerHTML = `<thead><tr>${heads.map(h => `<th>${esc(h)}</th>`).join('')}</tr></thead><tbody>${rows.join('')}</tbody>`;
    fitDope();
  }
  /* Only a table wider than its box shows the swipe cue and a sticky first column (the Survival tables' pattern). Measured when the
     screen is visible: after each calculation, when the screen is shown and when the phone turns. */
  function fitDope() {
    const w = $('#dope').closest('.tablewrap');
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
  /* On a short screen (keyboard up) the answer card is pinned under the header; the header's height sets where. */
  const view = $('#view-ballistics'), card = F('solution');
  view.addEventListener('focusin', e => {
    const top = $('.top');
    document.documentElement.style.setProperty('--balTop', (top ? top.getBoundingClientRect().bottom : 73) + 'px');
    if (e.target.matches('input, select') && !e.target.closest('.bal-profile')) card.classList.add('compact');
  });
  view.addEventListener('focusout', e => {
    if (!e.relatedTarget || !view.contains(e.relatedTarget) || !e.relatedTarget.matches('input, select')) card.classList.remove('compact');
  });
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

  /* ---------- Profile editor: load, the sight on it, and the conditions it was zeroed in ----------
     One sheet (#dlgRifle). An own profile can be saved in place, saved as a new profile or deleted; a built-in load only
     saved as a new profile. The sight and the zero conditions are stored on the profile and never reach BAL.solve. */
  const dlg = F('dlgRifle');
  const CLICK_CHOICES = {
    mil: [[0.1, '0.1 mil'], [0.05, '0.05 mil']],
    moa: [[0.25, '1/4 MOA'], [0.125, '1/8 MOA'], [0.5, '1/2 MOA'], [1, '1 MOA']],
    iphy: [[0.25, '1/4 in'], [0.125, '1/8 in'], [0.5, '1/2 in'], [1, '1 in']]
  };
  const E = ['rfName', 'rfBC', 'rfModel', 'rfW', 'rfMV', 'rfSH', 'rfZero', 'rfOptic', 'rfUnit', 'rfClick', 'rfMarks', 'rfZTemp', 'rfZAlt', 'rfZPress'];
  let editing = null;        // { base: profile, own: bool } while the sheet is open
  let opened = null;         // what the sheet showed when it opened
  let deleting = false;      // Delete has been confirmed: nothing else in the sheet may act

  function fillClicks(unitKey, want) {
    const list = CLICK_CHOICES[unitKey].slice();
    if (want !== undefined && !list.some(c => c[0] === want)) list.push([want, String(want)]);
    F('rfClick').innerHTML = list.map(c => `<option value="${c[0]}">${c[1]}</option>`).join('');
    F('rfClick').value = String(want !== undefined ? want : list[0][0]);
  }
  function showSight() {
    const t = F('rfOptic').value;
    F('rfUnitRow').hidden = F('rfUnitHint').hidden = !(t === 'turret' || t === 'reticle');
    F('rfClickRow').hidden = t !== 'turret';
    F('rfMarksRow').hidden = F('rfMarksHint').hidden = t !== 'reticle';
  }
  const showZHint = () => { F('rfZHint').hidden = ['rfZTemp', 'rfZAlt', 'rfZPress'].some(i => F(i).value.trim() !== ''); };
  const typed = () => E.map(i => F(i).value).join('\u0001');
  const say = text => { F('rfMsg').textContent = text; };

  function openEditor(p, own) {
    const o = p.optic, z = p.zeroAtm;
    editing = { base: p, own }; deleting = false;
    F('rfTitle').textContent = own ? 'Edit profile' : 'Built-in load';
    F('rfBuiltIn').hidden = own;
    F('rfSave').hidden = F('rfDelete').hidden = !own;
    const set = (id, v) => { F(id).value = v === undefined || v === null ? '' : v; };
    set('rfName', p.name); set('rfBC', p.bc); set('rfModel', p.model || 'G7'); set('rfW', p.w); set('rfMV', p.mv); set('rfSH', p.sight); set('rfZero', p.zero);
    set('rfOptic', o && o.type !== 'dot' ? o.type : o ? 'dot' : 'none');
    const u = o && o.unit ? o.unit : 'mil';
    set('rfUnit', u);
    fillClicks(u, o && o.type === 'turret' ? o.click : undefined);
    set('rfMarks', o && o.type === 'reticle' ? o.marks.join(', ') : '');
    set('rfZTemp', z && z.temp); set('rfZAlt', z && z.alt); set('rfZPress', z && z.press);
    say(''); showSight(); showZHint();
    dlg.querySelector('.mk-body').scrollTop = 0;
    opened = null;
    FK.sheet.open(dlg, {
      onClose: () => { editing = null; deleting = false; dlg.inert = false; opened = null; },
      onOpen: () => { F('rfTitle').focus(); opened = typed(); },    // no keyboard popping up on a phone
      guard: { dirty: () => !!editing && opened !== null && !deleting && typed() !== opened, title: 'Discard changes to this profile?', text: 'What you typed is not kept.' }
    });
  }
  function edit(id) {
    const p = anyProfile(id === undefined ? cur : id);
    if (p) openEditor(copy(p), !!ownProfile(p.id));
  }

  /* The marks box: pieces split on commas and spaces, each a number above 0, at most 10, each larger than the one before. */
  function parseMarks(text) {
    const parts = text.split(/[\s,]+/).filter(Boolean);
    if (!parts.length) return { error: 'A reticle needs at least one mark.' };
    if (!parts.every(x => /^(\d+\.?\d*|\.\d+)$/.test(x) && parseFloat(x) > 0)) return { error: 'Marks must be numbers, like 1.5, 3, 4.6.' };
    if (parts.length > 10) return { error: 'Up to 10 marks.' };
    const marks = parts.map(parseFloat);
    if (!marks.every((m, i) => i === 0 || m > marks[i - 1])) return { error: 'Marks must get larger down the list.' };
    return { marks };
  }
  const numOf = id => { const t = F(id).value.trim(); const v = parseFloat(t); return t !== '' && Number.isFinite(v) ? v : null; };
  /* What the sheet holds as a profile (without an id), or { error, focus } for the first thing at fault. */
  function readEditor() {
    const bad = (error, focus) => ({ error, focus });
    const name = F('rfName').value.trim();
    if (!name) return bad('Give the profile a name.', 'rfName');
    const bc = numOf('rfBC'), mv = numOf('rfMV'), zero = numOf('rfZero'), sh = numOf('rfSH'), w = numOf('rfW');
    if (!(bc > 0)) return bad('Ballistic coefficient must be more than 0.', 'rfBC');
    if (!(mv > 0)) return bad('Muzzle velocity must be more than 0.', 'rfMV');
    if (!(zero > 0)) return bad('Zero range must be more than 0.', 'rfZero');
    if (w !== null && w < 0) return bad('Bullet weight can’t be below 0.', 'rfW');
    if (sh !== null && sh < 0) return bad('Sight height can’t be below 0.', 'rfSH');
    const out = { name, bc, model: F('rfModel').value, w: w || 0, mv, sight: sh || 0, zero, optic: null, zeroAtm: null };
    const t = F('rfOptic').value, unit = F('rfUnit').value;
    if (t === 'turret') out.optic = { type: 'turret', unit, click: parseFloat(F('rfClick').value) };
    else if (t === 'dot') out.optic = { type: 'dot' };
    else if (t === 'reticle') {
      const m = parseMarks(F('rfMarks').value);
      if (m.error) return bad(m.error, 'rfMarks');
      out.optic = { type: 'reticle', unit, marks: m.marks };
    }
    const temp = numOf('rfZTemp'), alt = numOf('rfZAlt'), press = numOf('rfZPress');
    if (temp !== null || alt !== null || press !== null) {
      if (temp !== null && (temp < ZT[0] || temp > ZT[1])) return bad('Temperature must be between -60 and 140 \u00b0F.', 'rfZTemp');
      if (alt !== null && (alt < ZA[0] || alt > ZA[1])) return bad('Altitude must be between -2,000 and 30,000 ft.', 'rfZAlt');
      if (press !== null && !(press > 0)) return bad('Station pressure must be more than 0.', 'rfZPress');
      if (temp === null || (alt === null && press === null)) return bad('Zero conditions need a temperature and an altitude or a pressure.', temp === null ? 'rfZTemp' : 'rfZAlt');
      const base = editing.base.zeroAtm;
      out.zeroAtm = { temp, rh: base && fin(base.rh) ? base.rh : 50 };
      if (alt !== null) out.zeroAtm.alt = alt;
      if (press !== null) out.zeroAtm.press = press;
    }
    return out;
  }
  /* Save what the sheet shows, in place or as a new profile. Stays open (with the reason in #rfMsg) if it cannot. */
  function commitEditor(asNew) {
    if (!editing || deleting || (!asNew && !editing.own)) return;
    const v = readEditor();
    if (v.error) { say(v.error); F(v.focus).focus(); return; }
    say('');
    const p = { ...editing.base, ...v, id: asNew ? newId() : editing.base.id };
    ['optic', 'zeroAtm'].forEach(k => { if (!p[k]) delete p[k]; });
    const saved = save(p);
    if (!saved) { say('Could not save the profile.'); return; }     // the storage-full message has been shown
    select(saved.id);
    FK.sheet.close(dlg);
    toast(`Saved ${saved.name}`);
  }
  F('rfForm').addEventListener('submit', e => { e.preventDefault(); commitEditor(false); });
  F('rfSaveNew').addEventListener('click', () => commitEditor(true));
  F('rfCancel').addEventListener('click', () => FK.sheet.close(dlg));
  F('rfOptic').addEventListener('change', showSight);
  F('rfUnit').addEventListener('change', () => fillClicks(F('rfUnit').value));
  ['rfZTemp', 'rfZAlt', 'rfZPress'].forEach(i => F(i).addEventListener('input', showZHint));
  F('rfDelete').addEventListener('click', async () => {
    if (!editing || !editing.own || deleting) return;
    const id = editing.base.id, p = ownProfile(id);
    if (!p) return;
    deleting = true;
    const yes = await FK.sheet.confirm({ title: 'Delete the profile?', text: `Delete the ${p.name} profile? This can’t be undone.`, ok: 'Delete profile', danger: true });
    if (!yes || !editing || editing.base.id !== id) { deleting = false; return; }
    remove(id);
    if (ownProfile(id)) { deleting = false; return; }                // storage refused: the profile is still there
    dlg.inert = true;
    FK.sheet.afterStep(() => FK.sheet.close(dlg));                   // the confirm's own step back is still on its way
  });
  F('bEdit').addEventListener('click', () => edit());

  /* The surface other screens and tests use. */
  function init() {
    restoreInputs();
    calc();
  }
  FK.bal = {
    init, calc, clean, save, remove, select, edit,
    profiles: () => profiles.map(copy),
    selected: () => copy(anyProfile(cur))
  };
  FK._test.presets = () => PRESETS.map(p => ({ ...p }));
  FK._test.balState = () => ({ profile: cur, showAll });
  init();
})();
