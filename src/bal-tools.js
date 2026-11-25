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
  /* The one line both sheets show for a profile with no sight height (blank or 0). */
  const NO_SIGHT = 'This profile has no sight height, so these figures assume the sight sits on the bore. Tap Edit and set it.';
  text('clNoSight', NO_SIGHT);
  text('zsNoSight', NO_SIGHT);
  /* The note under the close-range holds: the second sentence only holds when the sight sits above the bore. */
  const NOTE = 'Level, no wind.', NOTE_HIGH = ' Inside the zero the bullet strikes low, so the hold is high.';

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
    text('clNote', NOTE + (noSight ? '' : NOTE_HIGH));
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

  /* The sentence for one zero (N the zero as shown, X the other crossing, P the highest point, Y its yard). A crossing beyond the zero is
     "again", one before it is "first". With no other crossing: still rising at 500 yd; out of reach before 500 yd; a path that starts
     on the line of sight (no sight height) and only comes down through the zero; or one that only touches it there. */
  const line = c => {
    const n = `${yd(c.zero)} yd zero`, top = c.peak ? ` Highest ${fx(c.peak.pathIn, 1)} in above it, at ${c.peak.yd} yd.` : '';
    if (c.other !== null && c.other > c.zero) return `${n}: crosses the line of sight again at ${c.other} yd.${top}`;
    if (c.other !== null) return `${n}: first crosses the line of sight at ${c.other} yd.${top}`;
    if (c.past) return `${n}: does not cross it again inside 500 yd.`;   // the path is still rising at 500 yd: its "peak" is only the last yard
    if (!(c.last >= BALZ.LIMIT)) return `${n}: does not cross it again before the bullet runs out of reach.`;
    if (c.peak) return `${n}: crosses the line of sight only there.`;
    return `${n}: touches the line of sight there and stays below it.`;
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
    F('zsNoSight').hidden = !res || p.sight > 0;                 // with the table only: no sight height (blank or 0)
    lastRes = res;
    drawChart();                                                 // the chart is shown and hidden with the table, and drawn from the same figures
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

  /* ---------- The chart above the table: the same figures, drawn. Each path joins the table's own points with straight segments
     (nothing is solved again), starts at its 5 yd point, and is told apart by its dash pattern, never by colour. The picture is
     laid out in CSS pixels (the SVG is as wide as its box), so its text is real text size, and the box and font are read each time
     it is drawn. Labels sit at the right-hand end of each path; two that would touch are moved apart with a short leader. ---------- */
  const NS = 'http://www.w3.org/2000/svg';
  const DASHES = [null, '10 6', '0.1 5.5'];            // solid, long dash, dot (round caps make the dot)
  const GAP = 1.2;                                     // text rows keep this many font sizes between centres
  let lastRes = null;
  const node = (name, attrs, parent) => {
    const e = document.createElementNS(NS, name);
    for (const k in attrs) if (attrs[k] !== null) e.setAttribute(k, String(attrs[k]));
    if (parent) parent.appendChild(e);
    return e;
  };
  const px = v => String(Math.round(v * 100) / 100 + 0);   // two decimals, never "-0"
  const sgn = v => (v > 0 ? '+' + v : String(v));
  const list = a => a.length < 2 ? a.join('') : a.slice(0, -1).join(', ') + ' and ' + a[a.length - 1];

  /* Push rows that touch apart (only those whose columns overlap), each by half the overshoot, inside lo..hi. */
  function spread(items, gap, lo, hi) {
    const clamp = () => items.forEach(i => { i.c = Math.min(hi, Math.max(lo, i.c)); });
    const hit = (a, b) => a.x0 < b.x1 && b.x0 < a.x1 && Math.abs(b.c - a.c) < gap - 0.01;
    for (let n = 0; n < 80; n++) {
      items.sort((a, b) => a.c - b.c);
      let moved = false;
      for (let i = 0; i < items.length - 1; i++) {
        const a = items[i], b = items[i + 1];
        if (hit(a, b)) { const d = (gap - (b.c - a.c)) / 2; a.c -= d; b.c += d; moved = true; }
      }
      clamp();
      if (!moved) break;
    }
    items.sort((a, b) => a.c - b.c);                                   // last: push down, then back up from the bottom edge
    for (let i = 0; i < items.length - 1; i++) if (hit(items[i], items[i + 1])) items[i + 1].c = items[i].c + gap;
    for (let i = items.length - 1; i > 0; i--) if (items[i].c > hi) { items[i].c = hi; if (hit(items[i - 1], items[i])) items[i - 1].c = hi - gap; }
  }

  function drawChart() {
    const svg = F('zsSvg'), box = F('zsChart');
    svg.textContent = '';
    box.hidden = !lastRes;
    if (!lastRes) { svg.removeAttribute('aria-label'); return; }
    const cols = lastRes.cols;
    svg.setAttribute('aria-label', `Chart of the bullet's path for ${list(cols.map(c => yd(c.zero)))} yd zeros, 5 to 300 yd. The table below has the figures.`);
    const base = parseFloat(getComputedStyle(svg).fontSize);
    const fs = Math.max(12, 13 * (Number.isFinite(base) && base > 0 ? base : 16) / 16);
    const W = Math.floor(box.clientWidth) || 320;
    const measure = (t, cls) => {                                       // the text's real width; an estimate where nothing is laid out
      const e = node('text', { class: cls, 'font-size': px(fs) }, svg);
      e.textContent = t;
      const w = e.getComputedTextLength ? e.getComputedTextLength() : 0;
      svg.removeChild(e);
      return w > 0 ? w : t.length * fs * 0.62;
    };
    const vals = cols.flatMap(c => c.path.filter(Number.isFinite));
    let lo = 0, hi = 0;
    if (vals.length) {
      const top = Math.max(...vals), bottom = Math.min(...vals);
      lo = Math.min(0, Math.floor(bottom)); hi = Math.max(0, Math.ceil(top));
      if (hi - top < 0.5) hi++;                                         // no path touches the frame: one more inch where it is within half an inch
      if (bottom - lo < 0.5) lo--;
    }
    if (hi === lo) hi = lo + 1;
    const MT = Math.ceil(fs * 0.7) + 3, MB = Math.ceil(fs) + 9;
    const H = Math.round(230 + (fs - 13) * 8), PH = H - MT - MB;
    for (let n = 0; n < 200; n++) {                                     // room for the caption on both sides of the line of sight, even when one path runs far above it
      if (-lo * PH / (hi - lo) < fs + 8) lo--;
      else if (hi * PH / (hi - lo) < fs + 8) hi++;
      else break;
    }
    const ymarks = [...new Set([lo, 0, hi])].map(v => ({ v, t: sgn(v) + (v === hi || v === lo ? ' in' : '') }));
    const names = cols.map(c => `${yd(c.zero)} yd`);
    const ML = Math.ceil(Math.max(...ymarks.map(m => measure(m.t, 'zs-ax')))) + 8;
    const MR = Math.ceil(Math.max(...names.map(n => measure(n, 'zs-lab')))) + 10;
    const PW = Math.max(60, W - ML - MR);
    const X = y => ML + y / 300 * PW, Y = v => MT + (hi - v) / (hi - lo) * PH;
    svg.setAttribute('width', String(W)); svg.setAttribute('height', String(H));
    svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
    // frame: the lowest and highest inch, and a light line at each 100 yd
    [lo, hi].forEach(v => node('line', { class: 'zs-hgrid', x1: px(ML), x2: px(ML + PW), y1: px(Y(v)), y2: px(Y(v)) }, svg));
    [0, 100, 200, 300].forEach(d => node('line', { class: 'zs-grid', 'data-yd': d, x1: px(X(d)), x2: px(X(d)), y1: px(MT), y2: px(MT + PH) }, svg));
    // axis labels: the inches on the left (kept a row apart), the yards under the chart
    const rows = ymarks.map(m => ({ m, c: Y(m.v), x0: 0, x1: 1 }));
    spread(rows, fs * GAP, MT, MT + PH + fs * 0.4);
    rows.forEach(r => {
      const t = node('text', { class: 'zs-ax zs-ay', x: px(ML - 5), y: px(r.c + fs * 0.35), 'text-anchor': 'end', 'font-size': px(fs) }, svg);
      t.textContent = r.m.t;
    });
    [[0, '0', 'start'], [100, '100', 'middle'], [200, '200', 'middle'], [300, '300 yd', 'end']].forEach(([d, t, a]) => {
      const e = node('text', { class: 'zs-ax', x: px(X(d)), y: px(MT + PH + fs + 3), 'text-anchor': a, 'font-size': px(fs) }, svg);
      e.textContent = t;
    });
    // the line of sight, and the paths over it
    node('line', { class: 'zs-los', x1: px(ML), x2: px(ML + PW), y1: px(Y(0)), y2: px(Y(0)), 'stroke-width': 1 }, svg);
    const ends = [], pts = [];
    cols.forEach((c, k) => {
      const dash = DASHES[k % DASHES.length];
      let d = '', pen = false, last = null, n = 0;
      BALZ.YDS.forEach((y, i) => {
        const v = c.path[i];
        if (!Number.isFinite(v)) { pen = false; return; }               // the bullet does not reach: no point, no line
        const here = { x: X(y), y: Y(v) };
        d += `${pen ? 'L' : 'M'}${px(here.x)} ${px(here.y)}`;
        if (pen) for (let t = 2; t < Math.hypot(here.x - last.x, here.y - last.y); t += 2) {   // the line itself, for keeping the caption off it
          const f = t / Math.hypot(here.x - last.x, here.y - last.y);
          pts.push({ x: last.x + (here.x - last.x) * f, y: last.y + (here.y - last.y) * f });
        }
        pen = true; last = here; n++;
        pts.push(here);
      });
      if (n === 0) {                                                    // nothing reached: no path, but the zero keeps its label, at the line of sight
        last = { x: X(300), y: Y(0) };
      } else if (n === 1) {                                             // one point: a dot, so it can be seen
        node('circle', { class: 'zs-dot', 'data-zero': yd(c.zero), cx: px(last.x), cy: px(last.y), r: 3.5 }, svg);
      } else node('path', { class: 'zs-path', 'data-zero': yd(c.zero), d, fill: 'none', 'stroke-width': dash && dash.startsWith('0.') ? 3 : 2.5,
        'stroke-dasharray': dash, 'stroke-linecap': dash && dash.startsWith('0.') ? 'round' : 'butt', 'stroke-linejoin': 'round' }, svg);
      if (last) ends.push({ k, name: names[k], zero: yd(c.zero), at: last, c: last.y, x0: last.x + 8, x1: last.x + 8 + measure(names[k], 'zs-lab') });
    });
    spread(ends, fs * GAP, MT, MT + PH + fs * 0.4);
    ends.forEach(e => {
      const x = Math.min(e.x0, W - (e.x1 - e.x0) - 1);
      if (Math.abs(e.c - e.at.y) > 2) node('line', { class: 'zs-lead', x1: px(e.at.x + 1.5), y1: px(e.at.y), x2: px(x - 2), y2: px(e.c) }, svg);
      const t = node('text', { class: 'zs-lab', 'data-zero': e.zero, x: px(x), y: px(e.c + fs * 0.35), 'font-size': px(fs) }, svg);
      t.textContent = e.name;
    });
    // "line of sight": on the right half of the rule if there is room, above or below it, wherever it is furthest from every path and label
    const text = 'line of sight', tw = measure(text, 'zs-ax'), y0 = Y(0);
    ends.forEach(e => { for (let x = e.x0; x < e.x1; x += 4) for (let y = e.c - fs * 0.6; y <= e.c + fs * 0.6; y += 4) pts.push({ x, y }); });
    const clear = (x, top, bottom) => pts.reduce((m, p) => Math.min(m, Math.hypot(Math.max(x - p.x, 0, p.x - (x + tw)), Math.max(top - p.y, 0, p.y - bottom))), 99);
    const cands = [], half = ML + PW / 2;
    for (const above of [true, false]) {
      const base = above ? y0 - 5 : y0 + fs + 1, top = base - fs * 0.95, bottom = base + fs * 0.3;
      if (top < MT || bottom > MT + PH) continue;                       // inside the plot
      for (let x = ML + 4; x + tw <= ML + PW - 4; x += 3) cands.push({ cl: Math.min(clear(x, top, bottom), 12), x, base, right: x + tw / 2 >= half });
    }
    const most = list => list.reduce((m, c) => (!m || c.cl > m.cl + 0.01 ? c : m), null);
    const best = most(cands.filter(c => c.right && c.cl >= 4)) || most(cands);
    if (best) {
      const t = node('text', { class: 'zs-ax zs-name', x: px(best.x), y: px(best.base), 'font-size': px(fs) }, svg);
      t.textContent = text;
    }
  }
  const redraw = () => { if (zdlg.open && lastRes) drawChart(); };
  if (window.ResizeObserver) { const ro2 = new ResizeObserver(redraw); ro2.observe(F('zsChart')); }
  addEventListener('resize', redraw);

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
      note = `Zero set to ${yd(zero)} yd.` + (cur.zeroAtm ? ' Update the zero conditions in Edit after you re-zero.' : '');   // the toast sits under a sheet: say it here as well
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
