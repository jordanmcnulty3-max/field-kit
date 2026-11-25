/* ---------- Ballistics: zero comparison and close-range paths (pure; the two sheets on the Ballistics screen call this) ---------- */
const BALZ = (() => {
  const CLOSE = [3, 5, 7, 10, 15, 25];
  const YDS = [5, 10, 15, 25, 36, 50, 75, 100, 125, 150, 175, 200, 225, 250, 275, 300];
  const LIMIT = 500;
  const NOISE = 0.005;     // in: a path value this close to the line of sight has no sign
  const PEAK_MIN = 0.05;   // in: the path has no peak unless it rises this far above the line of sight
  const NEAR = 2;          // yd: a crossing this close to the zero is the zero itself
  const ALL = Array.from({ length: LIMIT }, (_, i) => i + 1);
  const num = x => typeof x === 'number' && Number.isFinite(x);

  /* Level, no wind, whatever else the load carries (the screen's angle, wind and clock never reach these sheets). */
  function run(load, zero, ranges) {
    const l = load || {};
    return BAL.solve({ bc: l.bc, model: l.model, w: l.w, mv: l.mv, sight: l.sight, zero, zeroAtm: l.zeroAtm,
      temp: l.temp, alt: l.alt, press: l.press, rh: l.rh, wind: 0, clock: 12, angle: 0, ranges });
  }

  /* load: BAL.solve input without ranges, wind, clock, angle. The path at CLOSE with the load's own zero.
     Rows the solver does not give (a bullet that stops short) are left out. */
  function close(load) {
    const r = run(load, (load || {}).zero, CLOSE);
    if (r.error) return { error: r.error };
    return { rows: r.rows.filter(x => num(x.yd) && num(x.dropIn)).map(x => ({ yd: x.yd, dropIn: x.dropIn })) };
  }

  /* One zero: its path at YDS (null where the bullet never got), the other crossing, past, peak, and the last yard solved. */
  function column(load, zero) {
    const r = run(load, zero, ALL);
    if (r.error) return { error: r.error };
    const pts = r.rows.filter(x => num(x.yd) && num(x.dropIn)).map(x => ({ yd: x.yd, v: x.dropIn }));
    const at = new Map(pts.map(p => [p.yd, p.v]));
    const path = YDS.map(yd => at.has(yd) ? at.get(yd) : null);

    // Sign changes, ignoring values within NOISE of zero (they have no sign): between one signed sample and the next.
    const crossings = [];
    let prev = null, top = null;
    for (const p of pts) {
      if (!top || p.v > top.v) top = p;
      if (Math.abs(p.v) < NOISE) continue;
      if (prev && (p.v > 0) !== (prev.v > 0)) crossings.push(prev.yd + (0 - prev.v) / (p.v - prev.v) * (p.yd - prev.yd));
      prev = p;
    }
    const far = crossings.find(x => Math.abs(x - zero) > NEAR);
    const other = far === undefined ? null : Math.round(far);
    const last = pts[pts.length - 1];
    const past = other === null && !!last && last.yd === LIMIT && last.v >= NOISE;
    const peak = top && top.v >= PEAK_MIN ? { yd: top.yd, pathIn: top.v } : null;
    return { zero, path, other, past, peak, last: last ? last.yd : null };   // last: the last whole yard solved (LIMIT when it gets there)
  }

  /* zeros: 2 or 3 distinct finite numbers above 0 (yd). */
  function compare(load, zeros) {
    if (!Array.isArray(zeros) || zeros.length < 2 || zeros.length > 3 || !zeros.every(z => num(z) && z > 0)
      || new Set(zeros).size !== zeros.length) return { error: 'Pick two or three different zero ranges.' };
    const cols = [];
    for (const z of zeros) {
      const c = column(load, z);
      if (c.error) return { error: c.error };
      cols.push(c);
    }
    return { cols };
  }

  return { CLOSE, YDS, LIMIT, close, compare };
})();
