/* ---------- Ballistics tools: the sheets under the dope card. Close-range holds here; Compare zeros is added below.
   Loads after bal-edit.js and reaches the screen only through FK.bal (load, selected); the paths come from BALZ and the words
   from BALS. Each sheet reads the profile and today's air when it opens and has nothing to save. ---------- */
(() => {
  const FK = window.FK;
  const { $ } = FK;
  const F = id => $('#' + id);
  const dlg = F('dlgClose');
  const yd = v => String(Number(v.toFixed(1)));      // 100 -> "100", 36.5 -> "36.5"
  const inches = v => String(Number(v.toFixed(2)));  // 2.6 -> "2.6", 2 -> "2"
  const text = (id, t) => { F(id).textContent = t; };

  /* The hold for one row the way the red dot answer words it ("Hold 2.4 in high", "Hold on"). */
  const hold = r => BALS.answer({ yd: r.yd, dropIn: r.dropIn, windIn: 0 }, { type: 'dot' }).elev.main;

  function fill() {
    const p = FK.bal.selected(), load = FK.bal.load();
    text('clProfile', p.name);                                   // user data: text, never markup
    const noSight = !(p.sight > 0);
    text('clSight', `Sight height ${noSight ? 'not set' : inches(p.sight) + ' in'} · zero ${Number.isFinite(p.zero) ? yd(p.zero) + ' yd' : 'not set'}`);
    const res = load.error ? { error: load.error } : BALZ.close(load);
    const rows = res.error ? [] : res.rows;
    F('clNoSight').hidden = !!res.error || !noSight;
    text('clMsg', res.error || '');
    F('clMsg').hidden = !res.error;
    F('clWrap').hidden = !!res.error;
    F('clNote').hidden = !!res.error;
    const body = F('clTable'), head = document.createElement('thead'), tb = document.createElement('tbody');
    body.textContent = '';
    if (res.error) return;
    const tr = (tag, cells) => { const r = document.createElement('tr'); cells.forEach(c => { const d = document.createElement(tag); d.textContent = c; r.appendChild(d); }); return r; };
    head.appendChild(tr('th', ['Yd', 'Hold']));
    rows.forEach(r => tb.appendChild(tr('td', [yd(r.yd), noSight ? 'Hold on' : hold(r)])));   // no sight height: the line above the table says every hold reads zero
    body.append(head, tb);
  }

  F('bClose').addEventListener('click', () => FK.sheet.open(dlg, { onOpen: () => { fill(); F('clTitle').focus(); } }));
  F('clClose').addEventListener('click', () => FK.sheet.close(dlg));
})();
