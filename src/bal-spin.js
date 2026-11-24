/* ---------- Ballistics: gyroscopic stability (Miller) and spin drift (Litz estimate) ---------- */
const BSPIN = (() => {
  const MARGINAL_BELOW = 1.4, UNSTABLE_BELOW = 1.0;   // Courtney & Miller: recommended Sg 1.4 to 2.0; tumbling expected near 1.0
  const pos = x => Number.isFinite(x) && x > 0;

  /* Miller stability factor with the velocity and air corrections (Courtney & Miller, equation 1).
     w grains, dia and len inches, twist inches per turn, mv fps, temp °F, press station inHg.
     NaN when any is not a finite number above 0 (temp: any finite number). */
  function stability(p) {
    const { w, dia, len, twist, mv, temp, press } = p || {};
    if (![w, dia, len, twist, mv, press].every(pos) || !Number.isFinite(temp)) return NaN;
    const t = twist / dia, L = len / dia;
    return 30 * w / (t * t * dia * dia * dia * L * (1 + L * L))
      * Math.cbrt(mv / 2800) * (temp + 460) / (59 + 460) * 29.92 / press;
  }

  /* Litz spin drift estimate, inches, unsigned: 1.25 (Sg + 1.2) tof^1.83. */
  function drift(sg, tof) {
    return pos(sg) && pos(tof) ? 1.25 * (sg + 1.2) * Math.pow(tof, 1.83) : NaN;
  }

  function grade(sg) {
    if (!(sg >= UNSTABLE_BELOW)) return 'unstable';   // also NaN
    return sg < MARGINAL_BELOW ? 'marginal' : 'stable';
  }

  /* profile: { w, mv, twist, twistDir, blen, bdia }; air: { temp, press (station) }. */
  function of(profile, air) {
    const p = profile || {};
    const missing = [['twist', p.twist], ['bullet length', p.blen], ['bullet diameter', p.bdia], ['bullet weight', p.w]]
      .filter(([, v]) => !pos(v)).map(([name]) => name);
    if (missing.length) return { missing };
    const a = air || {};
    const sg = stability({ w: p.w, dia: p.bdia, len: p.blen, twist: p.twist, mv: p.mv, temp: a.temp, press: a.press });
    return { sg, grade: grade(sg), sign: p.twistDir === 'L' ? -1 : 1 };
  }

  return { stability, drift, grade, of };
})();
