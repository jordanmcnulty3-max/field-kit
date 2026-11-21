/* ---------- Ballistics screen: the inputs, the profiles and the answer card and table. The solver is BAL (ballistics.js). ---------- */
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
  const LOAD_FIELDS = { bc: 'bBC', model: 'bModel', w: 'bW', mv: 'bMV', sight: 'bSH', zero: 'bZero' };
  const ALL_FIELDS = ['bRange', 'bAngle', 'bWind', 'bClock', 'bBC', 'bModel', 'bW', 'bMV', 'bSH', 'bZero', 'bTemp', 'bAlt', 'bPress', 'bRH', 'bMax', 'bStep'];
  let unit = store.get('unit', 'mil') === 'moa' ? 'moa' : 'mil';

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
  function cleanAtm(z) {
    if (!isObj(z) || !fin(z.temp) || !(fin(z.alt) || fin(z.press))) return null;
    const out = { temp: z.temp };
    if (fin(z.alt)) out.alt = z.alt;
    if (fin(z.press)) out.press = z.press;
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
    F('bDel').hidden = !ownProfile(cur);
  }
  /* Put a profile's load numbers on the screen. A field the profile has no number for keeps what it shows. */
  function loadFields(p) {
    for (const [k, fid] of Object.entries(LOAD_FIELDS)) if (p[k] !== undefined) F(fid).value = p[k];
  }
  /* The six load values on the screen. A field that does not hold a number yet (being retyped) keeps the profile's value. */
  function readLoad(base) {
    const out = {};
    for (const [k, fid] of Object.entries(LOAD_FIELDS)) {
      if (k === 'model') out[k] = F(fid).value;
      else { const v = parseFloat(F(fid).value); out[k] = Number.isFinite(v) ? v : base && base[k]; }
    }
    return out;
  }
  function choose(id) {
    cur = id;
    fillProfiles();
    saveInputs();
  }
  function select(id) {
    const p = anyProfile(id);
    if (!p) return;
    loadFields(p);                               // before choose(): the stored screen state pairs the id with its own numbers
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
    if (cur === p.id) { loadFields(q); saveInputs(); calc(); }
    return copy(q);
  }
  function remove(id) {
    if (!ownProfile(id)) return;
    const before = profiles;
    profiles = profiles.filter(x => x.id !== id);
    if (!persist()) { profiles = before; toast(FK.FULL_MSG); return; }
    if (cur === id) { cur = firstBuiltIn().id; loadFields(anyProfile(cur)); saveInputs(); calc(); }
    fillProfiles();
  }
  /* Typing in a load field: an own profile takes the numbers; a built-in load becomes the profile "Custom" (made or overwritten). */
  function writeLoad() {
    const mine = ownProfile(cur);
    const p = { ...(mine || { id: 'ucustom', name: 'Custom' }), ...readLoad(mine || anyProfile(cur)) };
    const c = clean(p);
    if (!c) return;
    const q = ordered(c);
    profiles = ownProfile(q.id) ? profiles.map(x => x.id === q.id ? q : x) : profiles.concat([q]);
    persist();                                   // a full phone shows its own message through store.set
    if (cur !== q.id) choose(q.id); else fillProfiles();
  }
  const newId = () => {
    let id;
    do id = 'u' + Date.now().toString(36) + Math.floor(Math.random() * 1296).toString(36); while (anyProfile(id));
    return id;
  };

  F('bProfile').addEventListener('change', e => select(e.target.value));
  F('bSave').addEventListener('click', async () => {
    const name = await FK.sheet.ask({ title: 'Name this profile', label: 'Name, e.g. Tikka .308 – 175 SMK' });
    if (!name) return;
    const base = copy(anyProfile(cur) || {});
    const p = save({ ...base, ...readLoad(base), id: newId(), name });
    if (!p) return;
    select(p.id);
    toast(`Saved ${p.name}`);
  });
  F('bDel').addEventListener('click', async () => {
    const id = F('bProfile').value, p = ownProfile(id);
    if (!p || !await FK.sheet.confirm({ title: 'Delete the profile?', text: `Delete the ${p.name} profile? This can’t be undone.`, ok: 'Delete profile', danger: true })) return;
    remove(id);
  });

  function saveInputs() {
    const s = { profile: cur };
    ALL_FIELDS.forEach(id => { s[id] = F(id).value; });
    store.set('bal', s);
  }
  /* The stored selection decides what is selected. A built-in or own profile shows its own numbers; every other input is restored
     as stored. A stored "custom" (v7.8's unsaved entry) or a retired built-in becomes the profile "Custom" when a BC and a velocity
     were stored, otherwise the default built-in load is selected. */
  function restoreInputs() {
    const s = store.get('bal', null);
    if (!isObj(s)) { cur = firstBuiltIn().id; loadFields(anyProfile(cur)); fillProfiles(); return; }
    ALL_FIELDS.forEach(id => { if (s[id] !== undefined) F(id).value = s[id]; });
    let keepStored = false;                      // a failed profile write leaves the stored selection as it was, so the next open retries
    if (anyProfile(s.profile)) cur = s.profile;
    else if (s.profile === 'custom' || RETIRED.includes(s.profile)) {
      const bc = parseFloat(s.bBC), mv = parseFloat(s.bMV);
      const c = Number.isFinite(bc) && bc > 0 && Number.isFinite(mv) && mv > 0 ? clean({ id: 'ucustom', name: 'Custom', ...readLoad(null) }) : null;
      if (c) {
        const q = ordered(c);
        profiles = ownProfile('ucustom') ? profiles.map(x => x.id === 'ucustom' ? q : x) : profiles.concat([q]);
        if (!persist()) keepStored = true;
        cur = 'ucustom';
      } else cur = firstBuiltIn().id;
    } else cur = firstBuiltIn().id;
    loadFields(anyProfile(cur));
    fillProfiles();
    if (!keepStored) saveInputs();               // the stored copy now holds the selected profile's own numbers
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
    if (Object.values(LOAD_FIELDS).includes(id)) writeLoad();
    clearTimeout(calcT); calcT = setTimeout(() => { saveInputs(); calc(); }, 150);
  }));
  $$('#unitSeg button').forEach(b => b.addEventListener('click', () => {
    unit = b.dataset.unit; store.set('unit', unit);
    $$('#unitSeg button').forEach(x => x.setAttribute('aria-selected', String(x === b)));
    calc();
  }));

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
    $$('#unitSeg button').forEach(x => x.setAttribute('aria-selected', String(x.dataset.unit === unit)));
    restoreInputs();
    calc();
  }
  FK.bal = {
    init, calc, clean, save, remove, select, edit,
    profiles: () => profiles.map(copy),
    selected: () => copy(anyProfile(cur))
  };
  FK._test.presets = () => PRESETS.map(p => ({ ...p }));
  init();
})();
