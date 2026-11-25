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

  /* Spin drift measured from the zero, inches, before the twist's sign: a rifle zeroed at zeroYd already has the drift there in its
     sights, and that correction is an angle, so it grows in a straight line with range. drift(tof) - drift(tofZero) x yd / zeroYd:
     exactly 0 at the zero, a little negative (the other side) inside it. NaN when any input is not a finite number above 0. */
  function fromZero(sg, tof, yd, tofZero, zeroYd) {
    if (![yd, zeroYd].every(pos)) return NaN;
    const here = drift(sg, tof), there = drift(sg, tofZero);
    if (!Number.isFinite(here) || !Number.isFinite(there)) return NaN;
    if (yd === zeroYd && tof === tofZero) return 0;
    return here - there * (yd / zeroYd);
  }

  function grade(sg) {
    if (!(sg >= UNSTABLE_BELOW)) return 'unstable';   // also NaN
    return sg < MARGINAL_BELOW ? 'marginal' : 'stable';
  }

  /* The stability figure as printed: rounded DOWN to one decimal, so a figure under a threshold never prints as the threshold
     (1.38 is "1.3", not "1.4"). The 1e-9 keeps a value that is exactly one decimal from losing a step to binary error
     (2.3 * 10 is not always 23). '' for anything that is not a finite number. */
  const text = sg => typeof sg === 'number' && Number.isFinite(sg) ? (Math.floor(sg * 10 + 1e-9) / 10).toFixed(1) : '';

  /* profile: { w, mv, twist, twistDir, blen, bdia }; air: { temp, press (station) }.
     Either { sg, grade, sign } or { missing: [...] }: the names of what is absent (twist, bullet length, bullet diameter, bullet
     weight, muzzle velocity, in that order), or an empty list when only the air is unusable. Callers treat any `missing`, even an
     empty one, as "spin drift not applied"; sg is always a finite number. */
  function of(profile, air) {
    const p = profile || {};
    const missing = [['twist', p.twist], ['bullet length', p.blen], ['bullet diameter', p.bdia], ['bullet weight', p.w], ['muzzle velocity', p.mv]]
      .filter(([, v]) => !pos(v)).map(([name]) => name);
    if (missing.length) return { missing };
    const a = air || {};
    const sg = stability({ w: p.w, dia: p.bdia, len: p.blen, twist: p.twist, mv: p.mv, temp: a.temp, press: a.press });
    if (!Number.isFinite(sg)) return { missing: [] };
    return { sg, grade: grade(sg), sign: p.twistDir === 'L' ? -1 : 1 };
  }

  return { stability, drift, fromZero, grade, of, text };
})();
