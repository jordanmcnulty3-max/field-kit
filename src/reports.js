/* ---------- Reports: MEDEVAC 9-line and MIST. FK.reports, and the "9line" and "mist" tools at #/emergency/report/<name> ---------- */
(() => {
  const FK = window.FK;
  const esc = FK.esc;
  const KEY = 'nineLine';
  const FRESH_MS = 2 * 60 * 1000;   // a fix older than this is labelled with its age
  const REAGE_MS = 15000;           // while the 9-line is open, line 1 and its status are re-aged this often
  const MAX_TEXT = 2000, MAX_SHORT = 200, MAX_COUNT = 99;

  /* All 9-line wording lives here so it can be corrected from the published source in one place.
     kind: text | area (free text); counts (a number for each option); multi (any of the options); one (at most one option, then optional details).
     While `draft` is true the screen says so, and build.py --release refuses to build: it looks for the marker line below.
     Flip draft to false and delete the marker line once the wording is checked against its source. */
  /* REPORT_WORDING_DRAFT */
  const NINE_LINE = {
    draft: true,
    lines: [
      { n: 1, label: 'Location of pickup site (MGRS)', kind: 'text' },
      { n: 2, label: 'Radio frequency and call sign', kind: 'text' },
      { n: 3, label: 'Patients by precedence', kind: 'counts', options: [['A', 'Urgent'], ['B', 'Urgent surgical'], ['C', 'Priority'], ['D', 'Routine'], ['E', 'Convenience']] },
      { n: 4, label: 'Special equipment', kind: 'multi', options: [['A', 'None'], ['B', 'Hoist'], ['C', 'Extraction equipment'], ['D', 'Ventilator']], exclusive: 'A' },
      { n: 5, label: 'Patients by type', kind: 'counts', options: [['L', 'Litter'], ['A', 'Ambulatory']] },
      { n: 6, label: 'Security at pickup site', kind: 'one', options: [['N', 'No enemy troops in area'], ['P', 'Possible enemy troops'], ['E', 'Enemy troops in area'], ['X', 'Armed escort required']] },
      { n: 7, label: 'Method of marking pickup site', kind: 'one', detail: 'Details (colour, signal)', options: [['A', 'Panels'], ['B', 'Pyrotechnic signal'], ['C', 'Smoke signal'], ['D', 'None'], ['E', 'Other']] },
      { n: 8, label: 'Patient nationality and status', kind: 'one', detail: 'Details', options: [['A', 'US military'], ['B', 'US civilian'], ['C', 'Non-US military'], ['D', 'Non-US civilian'], ['E', 'Enemy prisoner of war']] },
      { n: 9, label: 'Terrain or hazards at pickup site', kind: 'area' }
    ]
  };
  const line = n => NINE_LINE.lines[n - 1];

  /* ================= Form: sanitise, then format ================= */
  const str = (v, max) => typeof v === 'string' ? v.slice(0, max) : '';
  const count = v => Number.isInteger(v) && v > 0 ? Math.min(v, MAX_COUNT) : 0;
  const codeOf = (v, n) => line(n).options.some(o => o[0] === v) ? v : '';
  const countsOf = (v, n) => Object.fromEntries(line(n).options.map(([c]) => [c, count(v && typeof v === 'object' ? v[c] : 0)]));
  /* Anything stored (old version, hand-edited backup) or passed in is reduced to this shape. l1auto: line 1 is still the app's own prefill. */
  function clean(f) {
    f = f && typeof f === 'object' ? f : {};
    const multi = Array.isArray(f.l4) ? [...new Set(f.l4.map(c => codeOf(c, 4)).filter(Boolean))] : [];
    return {
      l1: str(f.l1, MAX_SHORT), l1auto: f.l1auto !== false, l2: str(f.l2, MAX_SHORT), l3: countsOf(f.l3, 3), l4: multi, l5: countsOf(f.l5, 5),
      l6: codeOf(f.l6, 6), l7: codeOf(f.l7, 7), l7x: str(f.l7x, MAX_SHORT), l8: codeOf(f.l8, 8), l8x: str(f.l8x, MAX_SHORT), l9: str(f.l9, MAX_TEXT)
    };
  }
  const oneLine = s => s.replace(/\s*\n\s*/g, ' / ').trim();
  const nameOf = (n, c) => line(n).options.find(o => o[0] === c)[1];
  const countText = (n, c) => line(n).options.filter(([k]) => c[k] > 0).map(([k, name]) => k + ' ' + name + ' ' + c[k]).join(', ');
  const pick = (n, c, extra) => [c ? c + ' ' + nameOf(n, c) : '', oneLine(extra || '')].filter(Boolean).join(', ');

  /* Pure: nine lines "1. ..." to "9. ...", in order. An empty field leaves its number with nothing after it. */
  function nineLine(fields) {
    const f = clean(fields);
    const text = [
      oneLine(f.l1), oneLine(f.l2), countText(3, f.l3),
      line(4).options.filter(([c]) => f.l4.includes(c)).map(([c, name]) => c + ' ' + name).join(', '),
      countText(5, f.l5), pick(6, f.l6), pick(7, f.l7, f.l7x), pick(8, f.l8, f.l8x), oneLine(f.l9)
    ];
    return text.map((t, i) => (i + 1) + '.' + (t ? ' ' + t : '')).join('\n');
  }

  /* ================= MIST ================= */
  const hhmm = t => { const d = new Date(t); return String(d.getHours()).padStart(2, '0') + ':' + String(d.getMinutes()).padStart(2, '0'); };
  const AVPU_NAMES = { A: 'alert', V: 'voice', P: 'pain', U: 'unresponsive' };
  /* Latest entry (by time; the later one wins a tie) that has the field. */
  const latest = (entries, key) => entries.map((x, i) => [x, i]).filter(([x]) => x[key] !== undefined)
    .sort((a, b) => a[0].t - b[0].t || a[1] - b[1]).map(([x]) => x).pop();
  function buildMist(p) {
    const entries = p.entries || [];
    const said = (label, key, fmt) => { const e = latest(entries, key); return e ? label + ' ' + fmt(e[key]) + ' at ' + hhmm(e.t) : ''; };
    const signs = [said('pulse', 'pulse', v => v), said('breathing', 'resp', v => v), said('AVPU', 'avpu', v => v + ' (' + (AVPU_NAMES[v] || v) + ')')].filter(Boolean);
    const treat = entries.map((x, i) => [x, i]).filter(([x]) => x.kind === 'event').sort((a, b) => a[0].t - b[0].t || a[1] - b[1])
      .map(([x]) => hhmm(x.t) + ' ' + oneLine(x.text));
    const or = v => v && v.trim() ? oneLine(v) : 'not recorded';
    return ['M: ' + or(p.mech), 'I: ' + or(p.inj), 'S: ' + (signs.length ? signs.join(', ') : 'not recorded'), 'T: ' + (treat.length ? treat.join('; ') : 'not recorded')].join('\n');
  }
  /* Pure given the stored log: four lines M, I, S, T. */
  function mist(patientId) {
    const p = FK.patients.all().find(x => x.id === patientId);
    return p ? buildMist(p) : '';
  }

  FK.reports = { nineLine, mist };

  /* ================= Shared output: show, copy, share ================= */
  const outBlock = (id, label, withShare) =>
    '<label class="f" for="' + id + '">' + label + '</label><textarea class="rp-out" id="' + id + '" readonly></textarea>' +
    '<div class="pt-row"><button type="button" class="btn" data-rp="copy">Copy</button>' +
    (withShare && navigator.share ? '<button type="button" class="btn ghost" data-rp="share">Share</button>' : '') + '</div>';
  const setOut = (ta, text) => { ta.value = text; ta.rows = Math.min(14, text.split('\n').length + 1); };
  async function copyOut(ta, what) {
    try { await navigator.clipboard.writeText(ta.value); FK.toast('Copied the ' + what); return; } catch { /* clipboard unavailable or refused */ }
    ta.focus(); ta.select();
    try { ta.setSelectionRange(0, ta.value.length); } catch { /* optional */ }
    FK.toast('Couldn’t copy by itself. The text is selected: press and hold it, then tap Copy.');
  }
  async function shareOut(ta, title) {
    if (!navigator.share) return;
    try { await navigator.share({ title, text: ta.value }); } catch { /* cancelled */ }
  }
  function outClick(e, ta, what, title, before) {
    const b = e.target.closest('[data-rp]'); if (!b) return false;
    if (before) before();   // rebuild the text now, so it carries the age the screen shows at this moment
    if (b.dataset.rp === 'copy') copyOut(ta, what); else if (b.dataset.rp === 'share') shareOut(ta, title);
    return true;
  }

  /* ================= Location for line 1 ================= */
  let own = null;   // a fix this screen asked for itself, so the report never depends on the Tactical tab running GPS
  const okFix = f => !!f && FK.okLatLon(f.lat, f.lon) && FK.fin(f.t);
  const bestFix = () => {
    const f = FK.getFix(), a = own;
    const pick = okFix(a) && (!okFix(f) || a.t >= f.t) ? a : f;
    return okFix(pick) ? pick : null;
  };
  /* Fresh (under 2 minutes): MGRS alone. Older: MGRS then how old. */
  function fixText(f, now) {
    const g = GEO.toMGRS(f.lat, f.lon);
    const grid = g ? g.text : f.lat.toFixed(6) + ', ' + f.lon.toFixed(6);
    const age = now - f.t;
    if (age < 0) return grid + ' (fix time unknown)';   // a fix stamped in the future (clock skew) cannot be trusted
    return age < FRESH_MS ? grid : grid + ' (fix ' + Math.floor(age / 60000) + ' min old)';
  }
  /* The line beside line 1: always derived from the fix, whether or not the user typed over the field. */
  function fixStatus(f, now) {
    if (!f) return 'No GPS fix';
    const age = now - f.t, acc = FK.fin(f.acc) ? '±' + Math.round(f.acc) + ' m' : '';
    if (age < 0) return 'GPS fix time unknown';
    if (age < FRESH_MS) return 'GPS fix ' + Math.floor(age / 1000) + ' s ago' + (acc ? ', ' + acc : '');
    return 'GPS fix ' + Math.floor(age / 60000) + ' min old' + (acc ? ', ' + acc + ' at fix time' : '');
  }
  function requestFix(done) {
    try {
      if (!navigator.geolocation) return;
      navigator.geolocation.getCurrentPosition(pos => {
        const c = pos && pos.coords;
        if (!c) return;
        own = { lat: c.latitude, lon: c.longitude, acc: c.accuracy, t: pos.timestamp };
        done();
      }, () => { /* denied or no signal: the field stays as it is */ }, { enableHighAccuracy: true, maximumAge: 5000, timeout: 20000 });
    } catch { /* geolocation is optional */ }
  }

  /* ================= The 9-line tool ================= */
  let nl = null;   // { view, form } while open
  const nq = s => nl && nl.view.querySelector(s);
  let clearAt = 0, clearT = null, clearing = false;
  const saveForm = () => { if (!FK.store.set(KEY, nl.form)) FK.toast(FK.FULL_MSG); };
  const defaultForm = () => clean({});

  function optionBtns(n) {
    const l = line(n);
    return '<div class="rp-opts" data-n="' + n + '">' + l.options.map(([c, name]) =>
      '<button type="button" class="rp-opt" data-n="' + n + '" data-c="' + c + '" aria-pressed="false"><b>' + esc(c) + '</b> ' + esc(name) + '</button>').join('') + '</div>';
  }
  function countRows(n) {
    return line(n).options.map(([c, name]) =>
      '<div class="rp-count" data-n="' + n + '" data-c="' + c + '"><span><b>' + esc(c) + '</b> ' + esc(name) + '</span>' +
      '<button type="button" class="btn ghost" data-step="-1" aria-label="One fewer ' + esc(name) + '">−</button><output aria-live="polite"></output>' +
      '<button type="button" class="btn ghost" data-step="1" aria-label="One more ' + esc(name) + '">+</button></div>').join('');
  }
  function lineHtml(l) {
    const id = 'nl' + l.n, head = '<legend>' + l.n + '. ' + esc(l.label) + '</legend>';
    let body = '';
    if (l.n === 1) body = '<div class="rp-loc"><input id="nl1" type="text" maxlength="' + MAX_SHORT + '" autocomplete="off" aria-label="Line 1, location"></div><p class="rp-stat" id="nlStat"></p>';
    else if (l.kind === 'text') body = '<input id="' + id + '" type="text" maxlength="' + MAX_SHORT + '" autocomplete="off" aria-label="Line ' + l.n + ', ' + esc(l.label) + '">';
    else if (l.kind === 'area') body = '<textarea id="' + id + '" rows="2" maxlength="' + MAX_TEXT + '" aria-label="Line ' + l.n + ', ' + esc(l.label) + '"></textarea>';
    else if (l.kind === 'counts') body = countRows(l.n);
    else body = optionBtns(l.n) + (l.detail ? '<input id="' + id + 'x" type="text" maxlength="' + MAX_SHORT + '" autocomplete="off" aria-label="Line ' + l.n + ', ' + esc(l.detail) + '" placeholder="' + esc(l.detail) + '">' : '');
    return '<fieldset class="rp-line">' + head + body + '</fieldset>';
  }

  function paintLine1() {
    const f = nl.form, fix = bestFix();
    const el = nq('#nl1'); if (el && el.value !== f.l1) el.value = f.l1;
    nq('#nlStat').textContent = fixStatus(fix, Date.now());
  }
  function paintForm() {
    const f = nl.form;
    paintLine1();
    ['l2', 'l9'].forEach(k => { const el = nq('#nl' + k[1]); if (el.value !== f[k]) el.value = f[k]; });
    ['l7x', 'l8x'].forEach(k => { const el = nq('#nl' + k[1] + 'x'); if (el.value !== f[k]) el.value = f[k]; });
    nl.view.querySelectorAll('.rp-count').forEach(r => { r.querySelector('output').textContent = String(f['l' + r.dataset.n][r.dataset.c]); });
    nl.view.querySelectorAll('.rp-opt').forEach(b => {
      const v = f['l' + b.dataset.n];
      b.setAttribute('aria-pressed', String(Array.isArray(v) ? v.includes(b.dataset.c) : v === b.dataset.c));
    });
    const clr = nq('#nlClear');
    clr.textContent = clearing ? 'Confirm clear' : 'Clear form';
    clr.classList.toggle('ghost', !clearing);
    nq('#nlWarn').hidden = !clearing;
    paintOut();
  }
  function paintOut() { setOut(nq('#nlOut'), nineLine(nl.form)); }

  /* Prefill line 1 from the best fix, only while the field is still the app's own prefill. */
  function autoFill() {
    if (!nl || !nl.form.l1auto) return;
    const fix = bestFix();
    nl.form.l1 = fix ? fixText(fix, Date.now()) : '';
    saveForm(); paintForm();
  }
  /* Re-run the age logic: re-labels the app's own prefill only; typed text is never touched. The status line always updates. */
  function refresh() {
    if (!nl) return;
    if (nl.form.l1auto) autoFill(); else { paintLine1(); paintOut(); }
  }
  const setClear = on => {
    clearTimeout(clearT); clearing = on; clearAt = performance.now();
    if (on) clearT = setTimeout(() => { clearing = false; if (nl) paintForm(); }, FK.tools.confirm.revertMs);
  };

  function onNineClick(e) {
    if (outClick(e, nq('#nlOut'), '9-line', 'MEDEVAC 9-line', refresh)) return;
    const f = nl.form;
    const st = e.target.closest('[data-step]');
    if (st) {
      const row = st.closest('.rp-count'), key = 'l' + row.dataset.n;
      f[key][row.dataset.c] = Math.max(0, Math.min(MAX_COUNT, f[key][row.dataset.c] + Number(st.dataset.step)));
    }
    const op = e.target.closest('.rp-opt');
    if (op) {
      const n = Number(op.dataset.n), c = op.dataset.c, key = 'l' + n;
      if (line(n).kind === 'multi') {
        const ex = line(n).exclusive;
        f[key] = f[key].includes(c) ? f[key].filter(x => x !== c) : (c === ex ? [c] : [...f[key].filter(x => x !== ex), c]);
      } else f[key] = f[key] === c ? '' : c;
    }
    if (e.target.closest('#nlClear')) {
      if (!clearing) setClear(true);
      else if (performance.now() - clearAt >= FK.tools.confirm.ignoreMs) { setClear(false); nl.form = defaultForm(); saveForm(); autoFill(); }
      paintForm(); return;
    }
    if (st || op) { setClear(false); saveForm(); paintForm(); }
  }
  function onNineInput(e) {
    const m = /^nl(1|2|9|7x|8x)$/.exec(e.target.id); if (!m) return;
    const key = 'l' + m[1];
    nl.form[key] = e.target.value;
    if (key === 'l1') nl.form.l1auto = false;   // typed by the user: never overwritten again
    saveForm();
    if (clearing) { setClear(false); paintForm(); return; }   // typing cancels an armed Clear form
    if (key === 'l1') paintLine1();
    paintOut();
  }

  FK.tools.register('9line', {
    label: 'MEDEVAC 9-line',
    segment: 'report',
    render(el) {
      clearing = false;
      const view = el.appendChild(document.createElement('div'));
      nl = { view, form: clean(FK.store.get(KEY, null)) };
      view.innerHTML =
        (NINE_LINE.draft ? '<p class="rp-draft" role="note">Draft wording, not source-checked</p>' : '') +
        '<p class="hint">Fill in what you know and read the lines out in order. Line 1 fills in from GPS; you can type over it.</p>' +
        NINE_LINE.lines.map(lineHtml).join('') +
        outBlock('nlOut', 'Report text, read it out line by line', true) +
        '<p class="hint" id="nlWarn" hidden>This empties every line of the form.</p>' +
        '<button type="button" class="btn ghost pp-wide" id="nlClear">Clear form</button>';
      view.addEventListener('click', onNineClick);
      view.addEventListener('input', onNineInput);
      autoFill();           // also paints
      requestFix(autoFill);
      nl.iv = setInterval(refresh, REAGE_MS);
    },
    stop() { if (nl) clearInterval(nl.iv); clearTimeout(clearT); clearing = false; nl = null; }
  });
  FK.on('fix', () => { if (nl) autoFill(); });

  /* ================= The MIST tool ================= */
  let ms = null;   // { view, id, timer } while open
  const mq = s => ms && ms.view.querySelector(s);
  function flushMist() {
    if (!ms) return;
    if (!ms.timer && ms.saved !== false) return;   // nothing typed since the last save
    clearTimeout(ms.timer); ms.timer = null;
    if (ms.id) ms.saved = FK.patients.setMist(ms.id, { mech: mq('#msM').value, inj: mq('#msI').value });
    else { ms.saved = false; FK.toast(FK.FULL_MSG); }   // storage was full when this casualty was made: nothing can be saved
    paintUnsaved();
  }
  const paintUnsaved = () => { if (ms) mq('#msUnsaved').hidden = ms.saved !== false; };
  function paintMist() {
    if (!ms) return;
    const list = FK.patients.all(), cur = FK.patients.current();
    if (cur.id !== ms.id) {   // switched casualty: load theirs
      if (ms.timer) flushMist();
      ms.id = cur.id; ms.saved = cur.id ? true : false; paintUnsaved();
      mq('#msM').value = cur.mech || ''; mq('#msI').value = cur.inj || '';
    }
    mq('#msWho').textContent = cur.name;
    const sel = mq('#msSel');
    sel.innerHTML = list.map(x => '<option value="' + esc(x.id) + '"' + (x.id === cur.id ? ' selected' : '') + '>' + esc(x.name) + '</option>').join('');
    sel.hidden = list.length < 2;
    setOut(mq('#msOut'), buildMist({ ...cur, mech: mq('#msM').value, inj: mq('#msI').value }));
  }
  FK.tools.register('mist', {
    label: 'MIST report',
    segment: 'report',
    render(el) {
      const cur = FK.patients.current();
      const view = el.appendChild(document.createElement('div'));
      ms = { view, id: cur.id, timer: null, saved: cur.id ? true : false };
      view.innerHTML =
        '<div class="pt-top"><h3 id="msWho"></h3></div>' +
        '<select id="msSel" aria-label="Switch casualty" hidden></select>' +
        '<p class="rp-draft" id="msUnsaved" role="status" hidden>Not saved: phone storage is full. The text stays here; copy it before you leave.</p>' +
        '<label class="f" for="msM">M: Mechanism (what happened)</label><textarea id="msM" rows="2" maxlength="' + MAX_TEXT + '"></textarea>' +
        '<label class="f" for="msI">I: Injuries found</label><textarea id="msI" rows="2" maxlength="' + MAX_TEXT + '"></textarea>' +
        '<p class="hint">S (signs) and T (treatment) come from the Patient log for this casualty: vitals and timed events such as tourniquets.</p>' +
        outBlock('msOut', 'Report text, read it out line by line', true);
      view.querySelector('#msM').value = cur.mech || ''; view.querySelector('#msI').value = cur.inj || '';
      view.addEventListener('click', e => outClick(e, mq('#msOut'), 'MIST report', 'MIST report'));
      view.addEventListener('input', e => {
        if (e.target.id !== 'msM' && e.target.id !== 'msI') return;
        clearTimeout(ms.timer); ms.timer = setTimeout(flushMist, 300);
        paintMist();
      });
      view.addEventListener('change', e => { if (e.target.id === 'msSel') { flushMist(); FK.patients.setCurrent(e.target.value); } });
      paintMist();
      paintUnsaved();
      if (!cur.id) FK.toast(FK.FULL_MSG);
    },
    stop() { flushMist(); ms = null; }
  });
  document.addEventListener('visibilitychange', () => { if (document.hidden) flushMist(); });
  addEventListener('pagehide', flushMist);
  FK.on('patients', paintMist);
})();
