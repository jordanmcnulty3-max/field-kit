/* ---------- Ballistics tools: the sheets under the dope card, Close-range holds and Compare zeros.
   Loads after bal-edit.js and reaches the screen only through FK.bal (load, selected, profiles, save); the paths come from BALZ and
   the words from BALS. Each sheet reads the profile and today's air when it opens. Close-range holds has nothing to save; Compare
   zeros saves one thing, the zero, on the person's own profile, and only after a question. ---------- */
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
    const msg = res.error || (rows.length ? '' : 'No holds to show for this profile.');
    F('clSight').hidden = !!res.error;                           // the sight line belongs to a profile that can be solved
    F('clNoSight').hidden = !!msg || !noSight;
    text('clMsg', msg);
    F('clMsg').hidden = !msg;
    F('clWrap').hidden = !!msg;
    F('clNote').hidden = !!msg;
    const body = F('clTable'), head = document.createElement('thead'), tb = document.createElement('tbody');
    body.textContent = '';
    if (msg) return;
    const tr = (tag, cells) => { const r = document.createElement('tr'); cells.forEach(c => { const d = document.createElement(tag); d.textContent = c; r.appendChild(d); }); return r; };
    head.appendChild(tr('th', ['Yd', 'Hold']));
    rows.forEach(r => tb.appendChild(tr('td', [yd(r.yd), hold(r)])));   // the solver's own figures, whatever the profile carries
    body.append(head, tb);
  }

  F('bClose').addEventListener('click', () => FK.sheet.open(dlg, { onOpen: () => { fill(); F('clTitle').focus(); } }));
  F('clClose').addEventListener('click', () => FK.sheet.close(dlg));

  /* ---------- Compare zeros ---------- */
  const zdlg = F('dlgZeros');
  const BOXES = [25, 36, 50, 100, 200];
  const LOW = 10, HIGH = 300, MOST = 3;
  const FEW = 'Pick two or three zeros.', MANY = 'Up to three at a time.', BAD = 'Enter a zero from 10 to 300 yd.';
  const DASH = '—';
  const one = v => Number(v.toFixed(1));              // a zero as the sheet shows it (one decimal): the one helper for picks, labels and the current-zero test
  const fx = (v, d) => { const t = v.toFixed(d); return /^-0(\.0+)?$/.test(t) ? t.slice(1) : t; };   // never "-0.0"
  let ctx = null;          // the profile and the air as they were when the sheet opened (and after a save)
  let session = 0;         // one per opening: an answer that comes back to a sheet that has been closed is dropped
  let asking = false;      // a Use question is open or its answer is still on its way
  let note = '';           // "Zero set to 50 yd", shown until the person changes the picks

  const isOwn = p => FK.bal.profiles().some(x => x.id === p.id);
  const boxes = () => [...zdlg.querySelectorAll('.zs-ticks input')];

  /* Other (yd): blank is not used; a number from 10 to 300 is kept to a tenth of a yard (so 100.04 is the 100 yd box); the browser's
     "bad input" (a lone "1e") and anything outside the range are refused. */
  function readOther() {
    const o = F('zsOther'), t = o.value.trim();
    if (t === '') return o.validity.badInput ? { bad: true } : { blank: true };
    const n = Number(t);                                         // the range is checked on what was typed, before it is kept to a tenth
    return Number.isFinite(n) && n >= LOW && n <= HIGH ? { value: one(n) } : { bad: true };
  }
  const chosen = () => {
    const ticks = boxes().filter(b => b.checked).map(b => Number(b.value)), o = readOther(), zeros = ticks.slice();
    if (o.value !== undefined && !zeros.includes(o.value)) zeros.push(o.value);
    return { ticks, o, zeros };
  };
  /* The zeros to compare and what is wrong with the picks, if anything. A refused Other is left out; so is a typed fourth. */
  function selection() {
    const { ticks, o, zeros } = chosen();
    let use = zeros, problem = '';
    if (o.bad) { problem = BAD; use = ticks; }
    else if (zeros.length > MOST) { problem = MANY; use = ticks; }
    if (!problem && use.length < 2) problem = FEW;
    return { zeros: use.slice().sort((a, b) => a - b), problem };
  }

  const line = c => {
    const n = `${yd(c.zero)} yd zero`;
    if (c.other !== null && c.peak) return `${n}: crosses the line of sight again at ${c.other} yd. Highest ${fx(c.peak.pathIn, 1)} in above it, at ${c.peak.yd} yd.`;
    if (c.other !== null) return `${n}: crosses the line of sight again at ${c.other} yd.`;
    if (c.past) return `${n}: does not cross it again inside 500 yd.`;   // the path is still rising at 500 yd: its "peak" is only the last yard
    if (!c.peak) return `${n}: touches the line of sight there and stays below it.`;
    return `${n}: does not cross it again before the bullet runs out of reach.`;
  };

  function render(forced) {
    const { p, load } = ctx, err = load.error || '';
    const sel = err ? null : selection();
    // the column that stands for the profile's own zero is worked with the stored zero itself: the table is the rifle's real path
    const same = z => Number.isFinite(p.zero) && one(z) === one(p.zero);
    let res = err || sel.zeros.length < 2 ? null : BALZ.compare(load, sel.zeros.map(z => same(z) ? p.zero : z));
    let msg = err || forced || sel.problem || '';
    if (res && res.error) { msg = res.error; res = null; }
    if (!msg && note) msg = note;
    const own = !err && isOwn(p);
    text('zsProfile', p.name);                                   // user data: text, never markup
    text('zsNow', `Current zero: ${Number.isFinite(p.zero) ? yd(p.zero) + ' yd' : 'not set'}`);
    F('zsNow').hidden = !!err;
    F('zsPicks').hidden = !!err;
    text('zsMsg', msg);
    F('zsMsg').hidden = !msg;
    F('zsMsg').classList.toggle('zs-note', !!msg && msg === note && !err && !forced && !sel.problem);   // a note is not an error
    ['zsWrap', 'zsKey', 'zsLines'].forEach(id => { F(id).hidden = !res; });
    F('zsCue').hidden = true;
    F('zsUse').hidden = !res || !own;
    F('zsBuiltin').hidden = !!err || own;
    const table = F('zsTable'), lines = F('zsLines'), use = F('zsUse');
    table.textContent = ''; lines.textContent = ''; use.textContent = '';
    if (!res) return;
    const tr = (tag, cells) => { const r = document.createElement('tr'); cells.forEach(c => { const d = document.createElement(tag); d.textContent = c; r.appendChild(d); }); return r; };
    const head = document.createElement('thead'), tb = document.createElement('tbody');
    head.appendChild(tr('th', ['Yd', ...res.cols.map(c => `${yd(c.zero)} yd zero`)]));
    BALZ.YDS.forEach((y, i) => tb.appendChild(tr('td', [String(y), ...res.cols.map(c => Number.isFinite(c.path[i]) ? fx(c.path[i], 1) : DASH)])));
    table.append(head, tb);
    res.cols.forEach(c => {
      const li = document.createElement('li'); li.textContent = line(c); lines.appendChild(li);
      if (own && !same(c.zero)) {              // never offer to "use" the zero the person reads as the one they have
        const b = document.createElement('button');
        b.type = 'button'; b.className = 'btn ghost'; b.textContent = `Use ${yd(c.zero)} yd zero`;
        b.addEventListener('click', () => useZero(c.zero));
        use.appendChild(b);
      }
    });
    fit();
  }

  /* Only a table wider than its box shows the swipe cue (the dope card's pattern). */
  function fit() {
    const w = F('zsWrap');
    F('zsCue').hidden = w.hidden || !(w.scrollWidth > w.clientWidth + 1);
  }
  if (window.ResizeObserver) { const ro = new ResizeObserver(() => { if (zdlg.open) fit(); }); ro.observe(F('zsWrap')); ro.observe(F('zsTable')); }
  addEventListener('resize', () => { if (zdlg.open) fit(); });

  /* The boxes the sheet opens with: the profile's own zero (in a box, or typed into Other when it is none of the five), 50 and 200,
     and 36 in the place of a 50 or 200 that is the profile's own. */
  function defaults() {
    const z = ctx.p.zero, zr = Number.isFinite(z) ? one(z) : NaN, want = new Set(BOXES.includes(zr) ? [zr] : []);
    [50, 200].forEach(b => want.add(b));
    if (want.size < MOST && (zr === 50 || zr === 200)) want.add(36);
    boxes().forEach(b => { b.checked = want.has(Number(b.value)); });
    F('zsOther').value = !BOXES.includes(zr) && Number.isFinite(z) && z >= LOW && z <= HIGH ? String(zr) : '';
  }

  boxes().forEach(b => b.addEventListener('change', () => {
    note = '';
    if (b.checked && chosen().zeros.length > MOST) { b.checked = false; render(MANY); return; }   // the last tick is refused
    render();
  }));
  F('zsOther').addEventListener('input', () => { note = ''; render(); });

  /* Set the profile's zero to one the person compared. Asks first; saves only on yes, and only the zero. The question has a history
     step of its own, so the save waits until that step has landed (as the profile editor's questions do). */
  async function useZero(zero) {
    if (asking) return;
    asking = true;
    const mine = session, id = ctx.p.id;
    const yes = await FK.sheet.confirm({ title: `Set the zero to ${yd(zero)} yd?`, text: 'The card changes now. The rifle itself still has to be re-zeroed at the range.', ok: 'Set zero' });
    if (!yes) { asking = false; return; }
    zdlg.inert = true;                                           // a Close tap before the question's step lands would drop the confirmed save
    FK.sheet.afterStep(() => {
      asking = false;
      zdlg.inert = false;                                        // every way out of here: the rest runs at once
      if (mine !== session || !zdlg.open) return;
      const cur = FK.bal.selected();
      if (cur.id !== id || !isOwn(cur)) return;
      if (!FK.bal.save({ ...cur, zero })) return;                // storage refused: it has said so, and the sheet stays as it was
      FK.toast(`Zero set to ${yd(zero)} yd`);
      note = `Zero set to ${yd(zero)} yd`;                       // the toast sits under a sheet: say it here as well
      ctx = { p: FK.bal.selected(), load: FK.bal.load() };
      render();
      F('zsTitle').focus();                                      // the Use button that had focus has been rebuilt
    });
  }

  F('bZeros').addEventListener('click', () => FK.sheet.open(zdlg, { onOpen: () => {
    session++; asking = false; note = ''; zdlg.inert = false;
    ctx = { p: FK.bal.selected(), load: FK.bal.load() };
    defaults(); render(); F('zsTitle').focus();
  } }));
  F('zsClose').addEventListener('click', () => FK.sheet.close(zdlg));
})();
