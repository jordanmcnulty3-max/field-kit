/* ---------- Patient log: per-casualty timestamped entries, FK.patients, FK.log, and the "log" tool ---------- */
(() => {
  const FK = window.FK;
  const esc = FK.esc;
  const KEY = 'patients';
  const MAX_PATIENTS = 50, MAX_ENTRIES = 500, MAX_TEXT = 2000, MAX_NAME = 60;
  const KINDS = ['note', 'vitals', 'event'];
  const AVPU = [['A', 'Alert'], ['V', 'Voice'], ['P', 'Pain'], ['U', 'Unresponsive']];
  const intIn = (v, lo, hi) => Number.isInteger(v) && v >= lo && v <= hi;

  /* An entry is { t, kind, text, pulse?, resp?, avpu? }. Anything else is dropped, never rendered. */
  function okEntry(x) {
    return !!x && typeof x === 'object' && FK.fin(x.t) && KINDS.includes(x.kind) && typeof x.text === 'string' && x.text.trim() !== '' && x.text.length <= MAX_TEXT &&
      (x.pulse === undefined || intIn(x.pulse, 1, 300)) && (x.resp === undefined || intIn(x.resp, 1, 120)) &&
      (x.avpu === undefined || AVPU.some(a => a[0] === x.avpu));
  }
  const cleanEntry = x => {
    const o = { t: x.t, kind: x.kind, text: x.text };
    if (x.pulse !== undefined) o.pulse = x.pulse;
    if (x.resp !== undefined) o.resp = x.resp;
    if (x.avpu !== undefined) o.avpu = x.avpu;
    return o;
  };
  /* used = when the casualty was last selected or created; the largest is the current casualty. It survives reloads without a new storage key. */
  const read = () => FK.list(KEY, p => FK.okId(p.id) && typeof p.name === 'string').map(p => ({
    id: p.id, name: p.name.slice(0, MAX_NAME), created: FK.fin(p.created) ? p.created : 0,
    used: FK.fin(p.used) ? p.used : (FK.fin(p.created) ? p.created : 0),
    entries: Array.isArray(p.entries) ? p.entries.filter(okEntry).map(cleanEntry) : []
  }));
  function write(list) {
    if (FK.store.set(KEY, list)) return true;
    FK.toast(FK.FULL_MSG);
    return false;
  }
  let seq = 0, lastUsed = 0;
  const stamp = () => (lastUsed = Math.max(Date.now(), lastUsed + 1));   // strictly increasing, so the latest pick always wins
  const newId = () => Date.now().toString(36) + (seq++ % 36).toString(36) + Math.floor(Math.random() * 1296).toString(36);
  const nextName = list => 'Casualty ' + (list.reduce((m, p) => { const r = /^Casualty (\d{1,6})$/.exec(p.name); return r ? Math.max(m, +r[1]) : m; }, 0) + 1);
  const pickCurrent = list => list.reduce((best, p) => (!best || p.used >= best.used ? p : best), null);
  const hhmm = t => { const d = new Date(t); return String(d.getHours()).padStart(2, '0') + ':' + String(d.getMinutes()).padStart(2, '0'); };

  function create(name) {
    const list = read();
    if (list.length >= MAX_PATIENTS) { FK.toast('Patient log is full (' + MAX_PATIENTS + ' casualties). Delete one first.'); return null; }
    const now = stamp();
    const p = { id: newId(), name: typeof name === 'string' && name.trim() ? name.trim().slice(0, MAX_NAME) : nextName(list), created: now, used: now, entries: [] };
    list.push(p);
    if (!write(list)) return null;
    FK.emit('patients');
    return p;
  }
  function current() {
    return pickCurrent(read()) || create() || { id: '', name: 'Casualty 1', created: 0, used: 0, entries: [] };   // storage full: a throwaway, nothing is lost that was saved
  }
  function setCurrent(id) {
    const list = read(), p = list.find(x => x.id === id);
    if (!p) return false;
    p.used = stamp();
    if (!write(list)) return false;
    FK.emit('patients');
    return true;
  }
  function rename(id, name) {
    const list = read(), p = list.find(x => x.id === id);
    const n = typeof name === 'string' ? name.trim().slice(0, MAX_NAME) : '';
    if (!p || !n) return false;
    p.name = n;
    if (!write(list)) return false;
    FK.emit('patients');
    return true;
  }
  function remove(id) {
    const list = read();
    if (!list.some(x => x.id === id)) return false;
    if (!write(list.filter(x => x.id !== id))) return false;
    FK.emit('patients');
    return true;
  }
  /* Adds to the current casualty. False: invalid entry, full limits (with a toast saying so), or storage full (toast). Nothing is dropped silently. */
  function add(entry) {
    if (!entry || typeof entry !== 'object' || !okEntry({ ...entry, t: Date.now() })) return false;
    const list = read();
    let p = pickCurrent(list);
    if (!p) {
      if (!create()) return false;
      return add(entry);
    }
    if (p.entries.length >= MAX_ENTRIES) { FK.toast('This casualty’s log is full (' + MAX_ENTRIES + ' entries). Copy it, then start a new casualty.'); return false; }
    p.entries.push(cleanEntry({ ...entry, t: Date.now() }));
    if (!write(list)) return false;
    FK.emit('patients');
    return true;
  }
  /* Plain text, oldest first, one entry per line: "HH:MM text". */
  function text(id) {
    const p = read().find(x => x.id === id);
    if (!p) return '';
    const day = new Date(p.created || Date.now());
    const head = p.name + ' (' + day.getFullYear() + '-' + String(day.getMonth() + 1).padStart(2, '0') + '-' + String(day.getDate()).padStart(2, '0') + ')';
    const lines = p.entries.map((x, i) => [x, i]).sort((a, b) => a[0].t - b[0].t || a[1] - b[1]).map(([x]) => hhmm(x.t) + ' ' + x.text.replace(/\s*\n\s*/g, ' / '));
    return [head, ...lines].join('\n');
  }

  FK.patients = { all: read, current, setCurrent, create, rename, remove, add, text };
  FK.log = t => { if (typeof t === 'string') add({ kind: 'event', text: t }); };

  /* ================= The "log" tool ================= */
  let view = null, confirmT = null, confirmAt = 0, confirming = false, renaming = false, avpu = '', msg = '';
  const CONFIRM_IGNORE_MS = 700, CONFIRM_REVERT_MS = 5000;
  const confirmTimes = () => (FK.tools && FK.tools.confirm) || { ignoreMs: CONFIRM_IGNORE_MS, revertMs: CONFIRM_REVERT_MS };
  const q = s => view && view.querySelector(s);
  const setConfirm = on => {
    clearTimeout(confirmT); confirming = on; confirmAt = performance.now();
    if (on) confirmT = setTimeout(() => { confirming = false; paint(); }, confirmTimes().revertMs);
  };

  function paint() {
    if (!view || !q('#ptName')) return;
    const list = read(), p = pickCurrent(list);
    if (!p) return;
    q('#ptName').hidden = renaming;
    q('#ptName').textContent = p.name;
    q('#ptRenameBox').hidden = !renaming;
    q('#ptRename').hidden = renaming;
    q('#ptSel').innerHTML = list.map(x => '<option value="' + esc(x.id) + '"' + (x.id === p.id ? ' selected' : '') + '>' + esc(x.name) + '</option>').join('');
    q('#ptSel').hidden = list.length < 2;
    const d = q('#ptDelete');
    d.textContent = confirming ? 'Confirm delete' : 'Delete casualty';
    d.classList.toggle('ghost', !confirming);
    q('#ptWarn').hidden = !confirming;
    view.querySelectorAll('#ptAvpu button').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.avpu === avpu)));
    q('#ptMsg').textContent = msg;
    const rows = p.entries.map((x, i) => [x, i]).sort((a, b) => b[0].t - a[0].t || b[1] - a[1]);
    q('#ptList').innerHTML = rows.length
      ? rows.map(([x]) => '<li><b>' + hhmm(x.t) + '</b> <span>' + esc(x.text) + '</span></li>').join('')
      : '<li class="muted">Nothing logged yet.</li>';
  }
  const say = m => { msg = m; if (q('#ptMsg')) q('#ptMsg').textContent = m; };

  function addVitals() {
    const pr = q('#ptPulse').value.trim(), rr = q('#ptResp').value.trim();
    const pulse = pr === '' ? undefined : Number(pr), resp = rr === '' ? undefined : Number(rr);
    if (pulse === undefined && resp === undefined && !avpu) { say('Enter a pulse, a breathing rate or a level of response.'); return; }
    if (pulse !== undefined && !intIn(pulse, 1, 300)) { say('Pulse must be a whole number from 1 to 300.'); return; }
    if (resp !== undefined && !intIn(resp, 1, 120)) { say('Breathing must be a whole number from 1 to 120.'); return; }
    const bits = [];
    if (pulse !== undefined) bits.push('pulse ' + pulse);
    if (resp !== undefined) bits.push('breathing ' + resp);
    if (avpu) bits.push('AVPU ' + avpu + ' (' + AVPU.find(a => a[0] === avpu)[1].toLowerCase() + ')');
    const e = { kind: 'vitals', text: 'Vitals: ' + bits.join(', ') };
    if (pulse !== undefined) e.pulse = pulse;
    if (resp !== undefined) e.resp = resp;
    if (avpu) e.avpu = avpu;
    if (!add(e)) return;   // add() told the user why (storage full or log full); the typed values stay
    q('#ptPulse').value = ''; q('#ptResp').value = ''; avpu = ''; say('');
    paint();
  }

  FK.tools.register('log', {
    label: 'Patient log',
    render(el) {
      confirming = false; renaming = false; avpu = ''; msg = '';
      current();   // first use creates "Casualty 1"
      view = el.appendChild(document.createElement('div'));   // its own root, so listeners never pile up on the shared tool body
      view.innerHTML =
        '<div class="pt-top"><h3 id="ptName" tabindex="-1"></h3>' +
        '<div class="pt-rn" id="ptRenameBox" hidden><input id="ptRenameIn" maxlength="' + MAX_NAME + '" aria-label="Casualty name"><button type="button" class="btn" id="ptRenameSave">Save</button><button type="button" class="btn ghost" id="ptRenameCancel">Cancel</button></div></div>' +
        '<div class="pt-row"><select id="ptSel" aria-label="Switch casualty"></select>' +
        '<button type="button" class="btn ghost" id="ptRename">Rename</button><button type="button" class="btn" id="ptNew">New casualty</button></div>' +
        '<label class="f" for="ptNote">Note</label><textarea id="ptNote" rows="2" maxlength="' + MAX_TEXT + '"></textarea>' +
        '<button type="button" class="btn pp-wide" id="ptAddNote">Add note</button>' +
        '<div class="pt-vit"><label class="f">Pulse<input id="ptPulse" type="number" inputmode="numeric" min="1" max="300"></label>' +
        '<label class="f">Breathing<input id="ptResp" type="number" inputmode="numeric" min="1" max="120"></label></div>' +
        '<div class="seg pt-avpu" id="ptAvpu" role="group" aria-label="Level of response">' +
        AVPU.map(([k, n]) => '<button type="button" data-avpu="' + k + '" aria-pressed="false" aria-label="' + n + '">' + k + '</button>').join('') + '</div>' +
        '<button type="button" class="btn pp-wide" id="ptAddVitals">Add vitals</button>' +
        '<p class="hint" id="ptMsg" role="status"></p>' +
        '<ul class="pt-list" id="ptList"></ul>' +
        '<div class="pt-row"><button type="button" class="btn ghost" id="ptCopy">Copy as text</button>' +
        (navigator.share ? '<button type="button" class="btn ghost" id="ptShare">Share</button>' : '') + '</div>' +
        '<p class="hint" id="ptWarn" hidden>This deletes the casualty and every entry. Copy it first if you need it.</p>' +
        '<button type="button" class="btn ghost pp-wide" id="ptDelete">Delete casualty</button>';
      view.addEventListener('click', e => {
        const b = e.target.closest('button'); if (!b) return;
        const cur = pickCurrent(read());
        switch (b.id || (b.dataset.avpu ? 'avpu' : '')) {
          case 'avpu': avpu = avpu === b.dataset.avpu ? '' : b.dataset.avpu; paint(); break;
          case 'ptAddNote': {
            const t = q('#ptNote').value.trim();
            if (!t) { say('Type a note first.'); break; }
            if (add({ kind: 'note', text: t })) { q('#ptNote').value = ''; say(''); paint(); }
            break;
          }
          case 'ptAddVitals': addVitals(); break;
          case 'ptNew': setConfirm(false); renaming = false; if (create()) say(''); break;
          case 'ptRename': renaming = true; paint(); q('#ptRenameIn').value = cur ? cur.name : ''; q('#ptRenameIn').focus(); break;
          case 'ptRenameCancel': renaming = false; paint(); break;
          case 'ptRenameSave': if (cur && rename(cur.id, q('#ptRenameIn').value)) { renaming = false; paint(); } else say('Type a name.'); break;
          case 'ptCopy': copy(cur); break;
          case 'ptShare': share(cur); break;
          case 'ptDelete':
            if (!confirming) { setConfirm(true); paint(); }
            else if (performance.now() - confirmAt >= confirmTimes().ignoreMs && cur) { setConfirm(false); remove(cur.id); if (!read().length) create(); }
            break;
        }
      });
      view.addEventListener('change', e => { if (e.target.id === 'ptSel') { setConfirm(false); setCurrent(e.target.value); } });
      paint();
    },
    stop() { clearTimeout(confirmT); confirming = false; view = null; }
  });
  FK.on('patients', paint);

  async function copy(p) {
    if (!p) return;
    const t = FK.patients.text(p.id);
    try { await navigator.clipboard.writeText(t); FK.toast('Copied the log for ' + p.name); } catch { FK.toast('Couldn’t copy. Use Share, or select the text by hand.'); }
  }
  async function share(p) {
    if (!p || !navigator.share) return;
    try { await navigator.share({ title: p.name, text: FK.patients.text(p.id) }); } catch { /* cancelled */ }
  }
})();
