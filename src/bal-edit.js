/* ---------- Profile editor: load, the sight on it, the conditions it was zeroed in, and a velocity corrected from one real shot ----------
   Loads after bal-ui.js and reaches the screen only through FK.bal (save, select, remove, selected, shotAir) and FK.balHost (find, newId,
   and the shared rules: RANGE, within, marksOk, nameTaken, freeName); it adds FK.bal.edit. ---------- */
(() => {
  const FK = window.FK;
  const { $, toast } = FK;
  const { within } = FK.balHost;
  const fin = FK.fin;
  const copy = p => JSON.parse(JSON.stringify(p));
  const F = id => $('#' + id);
  /* ---------- the sheet ----------
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
  /* The shot correction. The part's own fields (rfTrueYd, rfTrueVal, rfTrueUnit) are not the profile and never make the sheet dirty.
     editing.openMv: the velocity the sheet opened with. editing.applied: a correction has been applied since the last Put back.
     editing.undone: Put back was pressed (and no correction since). What the profile carries as mv0 comes from these at Save. */
  let result = null;         // { mv } while a worked-out velocity is waiting for "Use"
  let unitTouched = false;   // the person chose the unit in rfTrueUnit; otherwise it follows the Sight and Unit fields

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
  const fmt = n => Math.round(n).toLocaleString('en-US');
  const say = text => { F('rfMsg').textContent = text; };

  function openEditor(p, own) {
    const o = p.optic, z = p.zeroAtm;
    editing = { base: p, own, openMv: p.mv, applied: false, undone: false }; deleting = false;
    result = null; unitTouched = false;
    F('rfTitle').textContent = own ? 'Edit profile' : 'Built-in load';
    F('rfBuiltIn').hidden = own;
    F('rfSave').hidden = F('rfDelete').hidden = !own;
    const set = (id, v) => { F(id).value = v === undefined || v === null ? '' : v; };
    set('rfName', own ? p.name : FK.balHost.freeName(p.name));      // a copy of a built-in starts with a name of its own
    set('rfBC', p.bc); set('rfModel', p.model || 'G7'); set('rfW', p.w); set('rfMV', p.mv); set('rfSH', p.sight); set('rfZero', p.zero);
    set('rfOptic', o && o.type !== 'dot' ? o.type : o ? 'dot' : 'none');
    const u = o && o.unit ? o.unit : 'mil';
    set('rfUnit', u);
    fillClicks(u, o && o.type === 'turret' ? o.click : undefined);
    set('rfMarks', o && o.type === 'reticle' ? o.marks.join(', ') : '');
    set('rfZTemp', z && z.temp); set('rfZAlt', z && z.alt); set('rfZPress', z && z.press);
    F('rfTrueYd').value = F('rfTrueVal').value = '';
    say(''); showSight(); showZHint(); fillTrueUnits(); clearResult();
    dlg.querySelector('.mk-body').scrollTop = 0;
    opened = null;
    FK.sheet.open(dlg, {
      onClose: () => { editing = null; deleting = false; dlg.inert = false; opened = null; result = null; },
      onOpen: () => { F('rfTitle').focus(); opened = typed(); },    // no keyboard popping up on a phone
      guard: { dirty: () => !!editing && opened !== null && !deleting && (typed() !== opened || nextMv0(false) !== editing.base.mv0), title: 'Discard changes to this profile?', text: 'What you typed is not kept.' }
    });
  }
  function edit(id) {
    const f = FK.balHost.find(id === undefined ? FK.bal.selected().id : id);
    if (f) openEditor(f.profile, f.own);
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
  function readEditor(forShot) {
    const bad = (error, focus) => ({ error, focus });
    const name = F('rfName').value.trim();
    if (!name && !forShot) return bad('Give the profile a name.', 'rfName');
    const bc = numOf('rfBC'), mv = numOf('rfMV'), zero = numOf('rfZero'), sh = numOf('rfSH'), w = numOf('rfW');
    if (!within(bc, 'bc')) return bad('Ballistic coefficient must be between 0.05 and 1.2.', 'rfBC');
    if (!within(mv, 'mv')) return bad('Muzzle velocity must be between 300 and 5,000 fps.', 'rfMV');
    if (!within(zero, 'zero')) return bad('Zero range must be between 5 and 1,000 yd.', 'rfZero');
    if (w !== null && w !== 0 && !within(w, 'w')) return bad('Bullet weight must be between 1 and 1,000 gr, or blank.', 'rfW');
    if (sh !== null && !within(sh, 'sight')) return bad('Sight height must be between 0 and 6 in.', 'rfSH');
    const out = { name, bc, model: F('rfModel').value, w: w || 0, mv, sight: sh || 0, zero, optic: null, zeroAtm: null };
    const t = forShot ? 'none' : F('rfOptic').value, unit = F('rfUnit').value;     // the sight never reaches the solver
    if (t === 'turret') out.optic = { type: 'turret', unit, click: parseFloat(F('rfClick').value) };
    else if (t === 'dot') out.optic = { type: 'dot' };
    else if (t === 'reticle') {
      const m = parseMarks(F('rfMarks').value);
      if (m.error) return bad(m.error, 'rfMarks');
      out.optic = { type: 'reticle', unit, marks: m.marks };
    }
    const temp = numOf('rfZTemp'), alt = numOf('rfZAlt'), press = numOf('rfZPress');
    if (temp !== null || alt !== null || press !== null) {
      if (temp !== null && !within(temp, 'temp')) return bad('Temperature must be between -60 and 140 \u00b0F.', 'rfZTemp');
      if (alt !== null && !within(alt, 'alt')) return bad('Altitude must be between -2,000 and 30,000 ft.', 'rfZAlt');
      if (press !== null && !within(press, 'press')) return bad('Station pressure must be between 8 and 33 inHg.', 'rfZPress');
      if (temp === null || (alt === null && press === null)) return bad('Zero conditions need a temperature and an altitude or a pressure.', temp === null ? 'rfZTemp' : 'rfZAlt');
      const base = editing.base.zeroAtm;
      out.zeroAtm = { temp, rh: base && fin(base.rh) ? base.rh : 50 };
      if (alt !== null) out.zeroAtm.alt = alt;
      if (press !== null) out.zeroAtm.press = press;
    }
    return out;
  }
  /* The mv0 a Save would write (undefined: none). mv: the velocity being saved (the field's, when not given).
     In place: the profile's own mv0 is kept, unless Put back was pressed; a profile without one gets the velocity the sheet
     opened with, but only when a correction was applied and the velocity actually differs from it. A copy never inherits one. */
  function nextMv0(asNew, mv) {
    const now = mv === undefined ? numOf('rfMV') : mv, ed = editing, moved = ed.applied && now !== null && now !== ed.openMv;
    if (asNew) return moved ? ed.openMv : undefined;
    if (ed.applied) return ed.base.mv0 !== undefined ? ed.base.mv0 : moved ? ed.openMv : undefined;
    return ed.undone ? undefined : ed.base.mv0;
  }
  /* Save what the sheet shows, in place or as a new profile. Stays open (with the reason in #rfMsg) if it cannot. A velocity worked
     out and not used is never dropped silently: Save asks first (decided: true once the question has been answered). */
  let asking = false;        // the question about an unused correction is open
  function commitEditor(asNew, decided) {
    if (!editing || deleting || asking || (!asNew && !editing.own)) return;
    const v = readEditor();
    if (v.error) { say(v.error); F(v.focus).focus(); return; }
    if (FK.balHost.nameTaken(v.name, asNew ? undefined : editing.base.id)) { say('Give the profile its own name.'); F('rfName').focus(); return; }
    say('');
    if (result && !decided) { askUse(asNew); return; }
    const p = { ...editing.base, ...v, id: asNew ? FK.balHost.newId() : editing.base.id };
    ['optic', 'zeroAtm'].forEach(k => { if (!p[k]) delete p[k]; });
    /* The original velocity: kept through every correction, gone once put back. A copy carries one only when a correction was applied here. */
    const mv0 = nextMv0(asNew, v.mv);
    if (mv0 === undefined) delete p.mv0; else p.mv0 = mv0;
    const saved = FK.bal.save(p);
    if (!saved) { say('Could not save the profile.'); return; }     // the storage-full message has been shown
    FK.bal.select(saved.id);
    FK.sheet.close(dlg);
    toast(`Saved ${saved.name}`);
  }

  async function askUse(asNew) {
    const mv = result.mv, base = editing;
    asking = true;
    const how = await FK.sheet.confirm({ title: 'Use the corrected velocity?', text: `You worked out ${fmt(mv)} fps but haven't used it.`,
      ok: 'Use it and save', cancel: 'Save without it', choice: true });
    asking = false;
    if (!how || editing !== base) return;                        // closed: back to the sheet, nothing saved
    FK.sheet.afterStep(() => {                                   // the question's own step back is still on its way
      if (editing !== base) return;
      if (how === 'ok' && result) useResult();
      commitEditor(asNew, true);
    });
  }

  /* ---------- Correct from a real shot ---------- */
  const MORE = {
    near: 'Use a shot at 300 yd or more. Closer in, a small error gives a wild velocity.',
    slow: "At that distance the bullet is near the speed of sound, where velocity isn't the thing in doubt.",
    far: 'That needs a velocity change of more than 15%. Check the distance, the zero and the sight height first.',
    warn: "That's a change of more than 5%. Check the distance, the zero and the sight height first.",
    ask: 'Enter the distance and the elevation the rifle needed.',
    rifle: 'Fill in the rifle and load first.',
    air: 'Check the conditions on the Ballistics screen first.'
  };
  const UNIT_NAME = { mil: 'Mil', moa: 'MOA', iphy: 'Inches per 100 yd', in: 'Inches of drop' };
  /* A sight that has its own unit puts it first; with a red dot or no sight, inches of drop come first. */
  function fillTrueUnits() {
    const t = F('rfOptic').value, own = t === 'turret' || t === 'reticle' ? F('rfUnit').value : null;
    const order = own ? [own, ...['mil', 'moa', 'iphy'].filter(u => u !== own), 'in'] : ['in', 'mil', 'moa', 'iphy'];
    const keep = F('rfTrueUnit').value;
    F('rfTrueUnit').innerHTML = order.map(u => `<option value="${u}">${UNIT_NAME[u]}</option>`).join('');
    F('rfTrueUnit').value = unitTouched && order.includes(keep) ? keep : order[0];
  }
  /* The part's buttons: Use shows with a result; Put back shows when the profile will carry an original velocity. */
  function showTrue() {
    F('rfTruePart').hidden = !editing || !editing.own;
    const s = F('rfTrueSave');
    s.hidden = !result;
    if (result) s.textContent = `Use ${fmt(result.mv)} fps`;
    const u = F('rfTrueUndo'), has = !!editing && !editing.undone && editing.base.mv0 !== undefined;
    u.hidden = !has;
    if (has) u.textContent = `Put back ${fmt(editing.base.mv0)} fps`;
  }
  function clearResult() { result = null; F('rfTrueOut').textContent = ''; showTrue(); }
  const signed = pct => { const t = Math.abs(pct).toFixed(1); return Number(t) === 0 ? '0.0' : (pct < 0 ? '-' : '+') + t; };

  /* The result (or the refusal) and its Use button, scrolled into the sheet's visible part above the sticky buttons (and above a
     keyboard: the visible viewport), never past the top of the result line. */
  function reveal() {
    const body = dlg.querySelector('.mk-body'), out = F('rfTrueOut'), last = F('rfTrueSave').hidden ? out : F('rfTrueSave');
    if (!out.textContent) return;
    const b = body.getBoundingClientRect(), vv = window.visualViewport, GAP = 8;
    const bottom = Math.min(b.bottom, vv ? vv.offsetTop + vv.height : innerHeight) - GAP;
    const need = last.getBoundingClientRect().bottom - bottom, room = out.getBoundingClientRect().top - (b.top + GAP);
    if (need > 0) body.scrollTop += Math.ceil(Math.max(0, Math.min(need, room)));
  }
  function workItOut() {
    if (!editing || deleting || !editing.own) return;
    clearResult();
    const show = text => { F('rfTrueOut').textContent = text; reveal(); };
    const yd = numOf('rfTrueYd'), val = numOf('rfTrueVal');
    if (!(yd > 0) || !(val > 0)) return show(MORE.ask);
    const angle = BALS.toAngle(val, F('rfTrueUnit').value, yd);
    if (!(angle > 0)) return show(MORE.ask);
    const v = readEditor(true);
    if (v.error) return show(MORE.rifle);
    const air = FK.bal.shotAir();
    if (!air) return show(MORE.air);
    const za = v.zeroAtm;
    const p = { bc: v.bc, model: v.model, w: v.w, mv: v.mv, sight: v.sight, zero: v.zero, ...air,
      zeroAtm: za && { temp: za.temp, alt: za.alt === undefined ? 0 : za.alt, press: za.press === undefined ? 0 : za.press, rh: za.rh } };
    const r = BAL.trueMv(p, yd, angle);
    if (r.error) return show(r.error === 'bad' ? MORE.ask : MORE[r.error]);
    /* BAL.trueMv checks Mach 1.2 at the profile's velocity; the velocity found must be above it there too, or the answer is mostly
       the drag table's error (the same rule, applied here so the solver and its tests stay as they are). */
    const there = BAL.solve({ ...p, mv: r.mv, wind: 0, clock: 12, angle: 0, ranges: [yd] });
    if (there.error || there.rows.length !== 1 || !(there.rows[0].mach >= 1.2)) return show(MORE.slow);
    const orig = editing.base.mv0 !== undefined ? editing.base.mv0 : editing.openMv;    // two corrections cannot add up past the limit
    if (Math.abs(r.mv - orig) / orig > 0.15) return show(MORE.far);
    result = { mv: r.mv };
    showTrue();
    show(`Velocity ${fmt(v.mv)} fps \u2192 ${fmt(r.mv)} fps (${signed(r.change * 100)}%).` + (r.warn ? ' ' + MORE.warn : ''));
  }
  /* Both buttons write into the velocity field; the profile is stored only by the sheet's own Save. */
  function setVelocity(mv, text) {
    F('rfMV').value = String(mv);
    clearResult();
    say(text);
  }
  F('rfTrueGo').addEventListener('click', workItOut);
  function useResult() {
    const mv = result.mv;
    editing.applied = true; editing.undone = false;
    setVelocity(mv, `Velocity set to ${fmt(mv)} fps. Press Save to keep it.`);
  }
  F('rfTrueSave').addEventListener('click', () => { if (result && editing && !asking) useResult(); });
  F('rfTrueUndo').addEventListener('click', () => {
    if (!editing || editing.base.mv0 === undefined) return;
    editing.undone = true; editing.applied = false;
    setVelocity(editing.base.mv0, `Velocity put back to ${fmt(editing.base.mv0)} fps. Press Save to keep it.`);
  });
  F('rfTrueUnit').addEventListener('change', () => { unitTouched = true; });
  /* What the answer was worked out from has changed: it no longer holds. */
  F('rfForm').addEventListener('input', clearResult);
  F('rfForm').addEventListener('change', clearResult);
  F('rfForm').addEventListener('submit', e => { e.preventDefault(); commitEditor(false); });
  F('rfSaveNew').addEventListener('click', () => commitEditor(true));
  F('rfCancel').addEventListener('click', () => FK.sheet.dismiss(dlg));     // asks Keep editing / Discard when something changed, as Back does
  F('rfOptic').addEventListener('change', () => { showSight(); fillTrueUnits(); });
  F('rfUnit').addEventListener('change', () => { fillClicks(F('rfUnit').value); fillTrueUnits(); });
  ['rfZTemp', 'rfZAlt', 'rfZPress'].forEach(i => F(i).addEventListener('input', showZHint));
  F('rfDelete').addEventListener('click', async () => {
    if (!editing || !editing.own || deleting) return;
    const id = editing.base.id, f = FK.balHost.find(id), p = f && f.own ? f.profile : null;
    if (!p) return;
    deleting = true;
    const yes = await FK.sheet.confirm({ title: 'Delete the profile?', text: `Delete the ${p.name} profile? This can’t be undone.`, ok: 'Delete profile', danger: true });
    if (!yes || !editing || editing.base.id !== id) { deleting = false; return; }
    FK.bal.remove(id);
    { const g = FK.balHost.find(id); if (g && g.own) { deleting = false; return; } }                // storage refused: the profile is still there
    dlg.inert = true;
    FK.sheet.afterStep(() => FK.sheet.close(dlg));                   // the confirm's own step back is still on its way
  });
  F('bEdit').addEventListener('click', () => edit());
  FK.bal.edit = edit;
})();

