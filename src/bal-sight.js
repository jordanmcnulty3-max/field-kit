/* ---------- Ballistics: the words for each sight ---------- */
/* Pure formatting. One solved row plus a sight in, strings out. The sight never changes the trajectory.
   row: { yd, dropIn, windIn }. sight: null | { type: 'turret', unit, click } | { type: 'reticle', unit, marks }
   | { type: 'dot' }, unit one of 'mil' | 'moa' | 'iphy'. Anything else is treated as no sight. */
const BALS = (() => {
  const DASH = '—', HOLD_MIN = 0.5;
  const LABEL = { mil: 'mil', moa: 'MOA', iphy: 'in/100 yd' };
  const known = u => typeof u === 'string' && Object.prototype.hasOwnProperty.call(LABEL, u);

  /* ---- the one place for conversions and rounding ---- */
  const fin = Number.isFinite;
  const fromRad = (rad, unit) => unit === 'mil' ? rad * 1000 : unit === 'moa' ? rad * 180 / Math.PI * 60 : Math.tan(rad) * 3600;
  const toRad = (v, unit) => unit === 'mil' ? v / 1000 : unit === 'moa' ? v / 60 * Math.PI / 180 : Math.atan(v / 3600);
  const needRad = (inches, yd) => Math.atan(inches / (yd * 36));       // inches of fall (positive = up) at yd
  const rows = r => r && fin(r.yd) && r.yd > 0 && fin(r.dropIn) && fin(r.windIn);
  const ang = v => Math.abs(v).toFixed(1);                             // angles: one decimal, never signed
  const angZero = v => Number(ang(v)) === 0;
  const inch = a => { a = Math.abs(a); return a < 9.95 ? a.toFixed(1) : String(Math.round(a)); };
  const inchZero = a => Number(inch(a)) === 0;
  const dir = (v, pos, neg) => angZero(v) ? '' : v > 0 ? pos : neg;
  const withDir = (v, pos, neg) => { const d = dir(v, pos, neg); return (d ? d + ' ' : '') + ang(v); };
  const clicks = (v, click) => Math.round(Math.abs(v) / click);
  const clicksText = n => n + (n === 1 ? ' click' : ' clicks');
  /* A turret shows what is dialled: clicks x click size, with the click's own decimals (0.1 mil, 1/2 and 1: one; 0.05 mil and 1/4:
     two; 1/8: three), and the direction letter whenever at least one click is dialled. */
  const clickDec = click => Math.max(1, Math.min(3, (String(click).split('.')[1] || '').length));
  const dialled = (v, click, pos, neg) => {
    const n = clicks(v, click);
    return (n > 0 ? (v > 0 ? pos : neg) + ' ' : '') + (n * click).toFixed(clickDec(click));
  };

  /* Normalise a sight: null means no sight (mil form). */
  function sightOf(s) {
    if (!s || typeof s !== 'object' || !known(s.unit) && s.type !== 'dot') return null;
    if (s.type === 'dot') return { type: 'dot' };
    if (s.type === 'turret' && fin(s.click) && s.click > 0) return { type: 'turret', unit: s.unit, click: s.click };
    if (s.type === 'reticle' && Array.isArray(s.marks)) {
      const marks = s.marks.filter(m => fin(m) && m > 0).sort((a, b) => a - b);
      if (marks.length) return { type: 'reticle', unit: s.unit, marks };
    }
    return null;
  }

  /* Everything one axis needs, from the fall (or drift) in inches. elev: need = fall; wind: need = -windIn. */
  function axis(row, which) {
    const up = which === 'elev' ? -row.dropIn : -row.windIn;
    const rad = needRad(up, row.yd);
    return { up, rad, hold: Math.abs(which === 'elev' ? row.dropIn : row.windIn),
      pos: which === 'elev' ? 'U' : 'R', neg: which === 'elev' ? 'D' : 'L',
      holdPos: which === 'elev' ? 'high' : 'right', holdNeg: which === 'elev' ? 'low' : 'left' };
  }

  /* Reticle: mark index (-1 = Centre, marks.length = past the last one), and the hold left over, in inches. */
  function reticleMark(a, row, sight) {
    const marks = sight.marks, v = fromRad(a.rad, sight.unit), n = marks.length;
    const last = marks[n - 1], gap = n > 1 ? last - marks[n - 2] : last;
    if (v > last + gap / 2 + 1e-9) return { at: n, v };
    if (v < marks[0] / 2) return { at: -1, v, hold: a.up };
    let best = 0;
    for (let i = 1; i < n; i++) if (Math.abs(v - marks[i]) < Math.abs(v - marks[best])) best = i;
    return { at: best, v, hold: (Math.tan(a.rad) - Math.tan(toRad(marks[best], sight.unit))) * row.yd * 36 };
  }
  const holdWords = (h, up, down) => Math.abs(h) < HOLD_MIN ? '' : inch(h) + ' ' + (h > 0 ? up : down);
  /* Past a reticle's last mark the whole elevation is a hold: in the reticle's unit, then inches. */
  const pastHold = (a, unit) => 'hold ' + ang(fromRad(a.rad, unit)) + ' ' + LABEL[unit] + ' (' + inch(a.up) + ' in) ' + (a.up > 0 ? a.holdPos : a.holdNeg);

  const dotText = (a, ax) => Math.abs(a.up) < HOLD_MIN ? (ax === 'elev' ? 'Hold on' : 'No hold')
    : 'Hold ' + inch(a.up) + ' in ' + (a.up > 0 ? a.holdPos : a.holdNeg);

  const bad = () => ({ elev: { main: DASH, sub: '' }, wind: { main: DASH, sub: '' } });

  function one(row, sight, ax) {
    const a = axis(row, ax), unit = sight ? sight.unit : 'mil';
    const angle = withDir(fromRad(a.rad, unit), a.pos, a.neg) + ' ' + LABEL[unit];
    if (!sight) return { main: angle, sub: '' };
    if (sight.type === 'turret') {
      const v = fromRad(a.rad, unit);
      return { main: dialled(v, sight.click, a.pos, a.neg) + ' ' + LABEL[unit], sub: clicksText(clicks(v, sight.click)) };
    }
    if (sight.type === 'dot') return { main: dotText(a, ax), sub: '' };
    if (ax === 'wind') return { main: angle, sub: inchZero(a.up) ? 'No hold' : 'hold ' + inch(a.up) + ' in ' + (a.up > 0 ? a.holdPos : a.holdNeg) };
    const m = reticleMark(a, row, sight);
    if (m.at === sight.marks.length) return { main: 'Past last mark', sub: pastHold(a, sight.unit) };
    const h = holdWords(m.hold, 'high', 'low');
    return { main: m.at < 0 ? 'Centre' : 'Mark ' + (m.at + 1), sub: h && 'hold ' + h.replace(' ', ' in ') };
  }

  function answer(row, sight) {
    if (!rows(row)) return bad();
    const s = sightOf(sight);
    return { elev: one(row, s, 'elev'), wind: one(row, s, 'wind') };
  }

  /* No sight / "Show all units": mil, MOA and a hold in inches, for each axis. */
  function all(row) {
    if (!rows(row)) return { elev: [DASH, DASH, DASH], wind: [DASH, DASH, DASH] };
    const side = ax => { const a = axis(row, ax);
      return [withDir(fromRad(a.rad, 'mil'), a.pos, a.neg) + ' mil', withDir(fromRad(a.rad, 'moa'), a.pos, a.neg) + ' MOA', dotText(a, ax)]; };
    return { elev: side('elev'), wind: side('wind') };
  }

  function cols(sight) {
    const s = sightOf(sight);
    if (s && s.type === 'dot') return { elev: ['Elev hold in'], wind: ['Wind hold in'] };
    if (s && s.type === 'reticle') return { elev: ['Mark', 'Elev hold in'], wind: ['Wind ' + LABEL[s.unit], 'Wind hold in'] };
    if (s) return { elev: ['Elev ' + LABEL[s.unit], 'Elev clicks'], wind: ['Wind ' + LABEL[s.unit], 'Wind clicks'] };
    return { elev: ['Elev mil', 'Elev MOA'], wind: ['Wind mil', 'Wind MOA'] };
  }

  function cells(row, sight) {
    const s = sightOf(sight), n = cols(s);
    if (!rows(row)) return { elev: n.elev.map(() => DASH), wind: n.wind.map(() => DASH) };
    const e = axis(row, 'elev'), w = axis(row, 'wind');
    const dir1 = (a, unit) => withDir(fromRad(a.rad, unit), a.pos, a.neg);
    if (!s) return { elev: [dir1(e, 'mil'), dir1(e, 'moa')], wind: [dir1(w, 'mil'), dir1(w, 'moa')] };
    const hold = (a, min) => Math.abs(a.up) < min || inchZero(a.up) ? '0' : inch(a.up) + ' ' + (a.up > 0 ? a.holdPos : a.holdNeg);
    if (s.type === 'dot') return { elev: [hold(e, HOLD_MIN)], wind: [hold(w, HOLD_MIN)] };
    if (s.type === 'turret') {
      const c = a => { const v = fromRad(a.rad, s.unit), n = clicks(v, s.click); return n > 0 ? (v > 0 ? a.pos : a.neg) + ' ' + n : '0'; };
      const d = a => dialled(fromRad(a.rad, s.unit), s.click, a.pos, a.neg);
      return { elev: [d(e), c(e)], wind: [d(w), c(w)] };
    }
    const m = reticleMark(e, row, s);
    const elev = m.at === s.marks.length ? ['Past', inch(e.up) + ' ' + (e.up > 0 ? 'high' : 'low')]
      : [m.at < 0 ? 'C' : String(m.at + 1), holdWords(m.hold, 'high', 'low')];
    return { elev, wind: [dir1(w, s.unit), hold(w, 0)] };
  }

  /* A typed elevation to radians. unit: 'mil' | 'moa' | 'iphy' | 'in' (inches of drop at yd). NaN if unusable. */
  function toAngle(value, unit, yd) {
    if (!fin(value)) return NaN;
    if (unit === 'in') return fin(yd) && yd > 0 ? needRad(value, yd) : NaN;
    return known(unit) ? toRad(value, unit) : NaN;
  }

  /* ---- the lines under the profile picker ---- */
  const FRACTION = { 0.25: '1/4', 0.125: '1/8', 0.5: '1/2', 1: '1' };
  const clickWord = (click, unit) => (Object.prototype.hasOwnProperty.call(FRACTION, click) && unit !== 'mil' ? FRACTION[click] : String(click))
    + ' ' + (unit === 'mil' ? 'mil' : unit === 'moa' ? 'MOA' : 'in');
  const unitWords = { mil: 'mil', moa: 'MOA', iphy: 'inches per 100 yd' };

  /* What the profile's sight is, in one line. */
  function describe(sight) {
    const s = sightOf(sight);
    if (!s) return 'No sight set: showing every unit';
    if (s.type === 'dot') return 'Red dot or iron sights';
    if (s.type === 'turret') return (s.unit === 'mil' ? 'Mil turrets' : s.unit === 'moa' ? 'MOA turrets' : 'Turrets in inches per 100 yd') + ', ' + clickWord(s.click, s.unit) + ' clicks';
    const n = s.marks.length;
    return 'Drop reticle, ' + n + (n === 1 ? ' mark' : ' marks') + ' in ' + unitWords[s.unit];
  }
  /* The air the rifle was zeroed in: temperature, then the pressure when it was given, otherwise the altitude. '' when unusable. */
  function zeroLine(atm) {
    if (!atm || typeof atm !== 'object' || !fin(atm.temp)) return '';
    const t = String(Number(atm.temp.toFixed(1))) + '°F';
    if (fin(atm.press) && atm.press > 0) return 'Zeroed at ' + t + ', ' + atm.press.toFixed(2) + ' inHg';
    return fin(atm.alt) ? 'Zeroed at ' + t + ', ' + Math.round(atm.alt) + ' ft' : '';
  }

  /* Where the bullet is at the target, for the sentence under the card: "63.6 in low, drift 21.2 in left". Path is measured from the
     line of sight (positive up), drift from it (positive right); one decimal. '' for a bad row. */
  function path(row) {
    if (!rows(row)) return '';
    const p = Math.abs(row.dropIn).toFixed(1), d = Math.abs(row.windIn).toFixed(1);
    return (Number(p) === 0 ? 'on the line of sight' : p + ' in ' + (row.dropIn > 0 ? 'high' : 'low'))
      + ', drift ' + d + ' in' + (Number(d) === 0 ? '' : row.windIn > 0 ? ' right' : ' left');
  }
  /* The load, in one line: "175 gr · G7 0.25 · 2,600 fps · zero 100 yd" (the weight left out when 0 or missing). '' when unusable. */
  function loadLine(p) {
    if (!p || typeof p !== 'object') return '';
    const n = v => fin(v) ? Number(v.toFixed(3)) : null;
    const parts = [];
    if (n(p.w) > 0) parts.push(n(p.w) + ' gr');
    if (n(p.bc) !== null) parts.push((p.model === 'G1' ? 'G1' : 'G7') + ' ' + n(p.bc));
    if (n(p.mv) !== null) parts.push(Math.round(p.mv).toLocaleString('en-US') + ' fps');
    if (n(p.zero) !== null) parts.push('zero ' + n(p.zero) + ' yd');
    return parts.join(' \u00b7 ');
  }

  return { answer, all, cols, cells, toAngle, describe, zeroLine, path, loadLine, clickWord };
})();
