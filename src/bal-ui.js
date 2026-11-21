/* ---------- Ballistics screen: the inputs, the profiles and the answer card and table. The solver is BAL (ballistics.js). ---------- */
(() => {
  const FK = window.FK;
  const { $, $$, store, toast, esc, list, okId } = FK;
  const num = el => { const v = parseFloat(el.value); return Number.isFinite(v) ? v : 0; };

  const PRESETS = [
    { id: 'p556m193', name: 'Sellier & Bellot 5.56×45 M193 55 gr FMJ, 23.5″ barrel', bc: 0.127, model: 'G7', w: 55, mv: 3301, sight: 2.6, zero: 100 },
    { id: 'p556ss109', name: 'RWS 5.56x45 NATO Ball SS109 62 gr, 20″ barrel', bc: 0.151, model: 'G7', w: 62, mv: 3035, sight: 2.6, zero: 100 },
    { id: 'p223', name: 'Federal Gold Medal .223 Rem 77 gr SMK, 24″ barrel', bc: 0.188, model: 'G7', w: 77, mv: 2720, sight: 2.6, zero: 100 },
    { id: 'p76239sb', name: 'Sellier & Bellot 7.62×39 124 gr FMJ, 20.5″ barrel', bc: 0.286, model: 'G1', w: 124, mv: 2421, sight: 2.0, zero: 100 },
    { id: 'p65cm', name: 'Hornady 6.5 Creedmoor 140 gr ELD-M, 24″ barrel', bc: 0.326, model: 'G7', w: 140, mv: 2710, sight: 1.5, zero: 100 },
    { id: 'p308', name: 'Federal Gold Medal .308 Win 175 gr SMK, 24″ barrel', bc: 0.25, model: 'G7', w: 175, mv: 2600, sight: 1.5, zero: 100 }
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
    /* A stored built-in selection shows that load's current numbers: typing in a load field flips the selection to Custom, so
       the stored numbers are an older copy of the load, not the person's own. Every other input is restored as stored. */
    const built = PRESETS.find(x => x.id === s.profile);
    if (built) loadProfile(built.id);
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

  FK._test.presets = () => PRESETS.map(p => ({ ...p }));
  $$('#unitSeg button').forEach(x => x.setAttribute('aria-selected', String(x.dataset.unit === unit)));
  restoreInputs();
  calc();
})();
