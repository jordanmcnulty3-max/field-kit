/* ---------- Ballistics: point-mass solver, G1/G7 standard drag ---------- */
const BAL = (() => {
  // [Mach, Cd] standard projectile drag tables
  const G1 = [[0,.2629],[.05,.2558],[.1,.2487],[.15,.2413],[.2,.2344],[.25,.2278],[.3,.2214],[.35,.2155],[.4,.2104],[.45,.2061],[.5,.2032],[.55,.202],[.6,.2034],[.7,.2165],[.725,.223],[.75,.2313],[.775,.2417],[.8,.2546],[.825,.2706],[.85,.2901],[.875,.3136],[.9,.3415],[.925,.3734],[.95,.4084],[.975,.4448],[1,.4805],[1.025,.5136],[1.05,.5427],[1.075,.5677],[1.1,.5883],[1.125,.6053],[1.15,.6191],[1.2,.6393],[1.25,.6518],[1.3,.6589],[1.35,.6621],[1.4,.6625],[1.45,.6607],[1.5,.6573],[1.55,.6528],[1.6,.6474],[1.65,.6413],[1.7,.6347],[1.75,.628],[1.8,.621],[1.85,.6141],[1.9,.6072],[1.95,.6003],[2,.5934],[2.05,.5867],[2.1,.5804],[2.15,.5743],[2.2,.5685],[2.25,.563],[2.3,.5577],[2.35,.5527],[2.4,.5481],[2.45,.5438],[2.5,.5397],[2.6,.5325],[2.7,.5264],[2.8,.5211],[2.9,.5168],[3,.5133],[3.1,.5105],[3.2,.5084],[3.3,.5067],[3.4,.5054],[3.5,.504],[3.6,.503],[3.7,.5022],[3.8,.5016],[3.9,.501],[4,.5006],[4.2,.4998],[4.4,.4995],[4.6,.4992],[4.8,.499],[5,.4988]];
  const G7 = [[0,.1198],[.05,.1197],[.1,.1196],[.15,.1194],[.2,.1193],[.25,.1194],[.3,.1194],[.35,.1194],[.4,.1193],[.45,.1193],[.5,.1194],[.55,.1193],[.6,.1194],[.65,.1197],[.7,.1202],[.725,.1207],[.75,.1215],[.775,.1226],[.8,.1242],[.825,.1266],[.85,.1306],[.875,.1368],[.9,.1464],[.925,.166],[.95,.2054],[.975,.2993],[1,.3803],[1.025,.4015],[1.05,.4043],[1.075,.4034],[1.1,.4014],[1.125,.3987],[1.15,.3955],[1.2,.3884],[1.25,.381],[1.3,.3732],[1.35,.3657],[1.4,.358],[1.5,.344],[1.55,.3376],[1.6,.3315],[1.65,.326],[1.7,.3209],[1.75,.316],[1.8,.3117],[1.85,.3078],[1.9,.3042],[1.95,.301],[2,.298],[2.05,.2951],[2.1,.2922],[2.15,.2892],[2.2,.2864],[2.25,.2835],[2.3,.2807],[2.35,.2779],[2.4,.2752],[2.45,.2725],[2.5,.2697],[2.55,.267],[2.6,.2643],[2.65,.2615],[2.7,.2588],[2.75,.2561],[2.8,.2533],[2.85,.2506],[2.9,.2479],[2.95,.2451],[3,.2424],[3.1,.2368],[3.2,.2313],[3.3,.2258],[3.4,.2205],[3.5,.2154],[3.6,.2106],[3.7,.206],[3.8,.2017],[3.9,.1975],[4,.1935],[4.2,.1861],[4.4,.1793],[4.6,.173],[4.8,.1672],[5,.1618]];
  const TABLES = { G1, G7 };

  const G = 9.80665, IN = 0.0254, YD = 0.9144, FPS = 0.3048, MPH = 0.44704;
  const LBIN2 = 703.0696; // lb/in² → kg/m²

  function cd(t, m) {
    if (m <= t[0][0]) return t[0][1];
    const last = t.length - 1;
    if (m >= t[last][0]) return t[last][1];
    let lo = 0, hi = last;
    while (hi - lo > 1) { const mid = (lo + hi) >> 1; if (t[mid][0] <= m) lo = mid; else hi = mid; }
    const [m0, c0] = t[lo], [m1, c1] = t[hi];
    return c0 + (c1 - c0) * (m - m0) / (m1 - m0);
  }

  /* Air density (kg/m³) and speed of sound (m/s) at the shooter. */
  function atmosphere(tempF, altFt, pressInHg, rh) {
    const Tc = (tempF - 32) * 5 / 9, T = Tc + 273.15;
    const pIn = pressInHg > 0 ? pressInHg : 29.92126 * Math.pow(1 - 6.8755856e-6 * altFt, 5.2558797);
    const P = pIn * 3386.389;
    const Psat = 610.78 * Math.exp(17.27 * Tc / (Tc + 237.3));
    const Pv = Math.min(1, Math.max(0, rh / 100)) * Psat;
    const rho = (P - Pv) / (287.058 * T) + Pv / (461.495 * T);
    const c = 331.3 * Math.sqrt(1 + Tc / 273.15);
    return { rho, c, pIn };
  }

  /* Integrate in a frame aligned with the line of sight (x downrange, y up, z right).
     Returns the state interpolated at each requested x (metres, ascending). */
  function fly(s, alpha, theta, wx, wz, xs) {
    const gx = -G * Math.sin(theta), gy = -G * Math.cos(theta);
    const t = TABLES[s.model];
    const acc = (vx, vy, vz) => {
      const rx = vx - wx, rz = vz - wz;
      const vr = Math.hypot(rx, vy, rz);
      const k = s.K * s.rho * cd(t, vr / s.c) * vr;
      return [-k * rx + gx, -k * vy + gy, -k * rz];
    };
    let st = [0, -s.h, 0, s.v0 * Math.cos(alpha), s.v0 * Math.sin(alpha), 0, 0];
    const out = [];
    let i = 0;
    const dt = 0.001;
    while (i < xs.length && st[6] < 15) {
      const [x, y, z, vx, vy, vz, tm] = st;
      const a1 = acc(vx, vy, vz);
      const a2 = acc(vx + a1[0] * dt / 2, vy + a1[1] * dt / 2, vz + a1[2] * dt / 2);
      const a3 = acc(vx + a2[0] * dt / 2, vy + a2[1] * dt / 2, vz + a2[2] * dt / 2);
      const a4 = acc(vx + a3[0] * dt, vy + a3[1] * dt, vz + a3[2] * dt);
      const nvx = vx + dt / 6 * (a1[0] + 2 * a2[0] + 2 * a3[0] + a4[0]);
      const nvy = vy + dt / 6 * (a1[1] + 2 * a2[1] + 2 * a3[1] + a4[1]);
      const nvz = vz + dt / 6 * (a1[2] + 2 * a2[2] + 2 * a3[2] + a4[2]);
      const nst = [x + dt * (vx + nvx) / 2, y + dt * (vy + nvy) / 2, z + dt * (vz + nvz) / 2, nvx, nvy, nvz, tm + dt];
      if (nvx <= 0) break;
      while (i < xs.length && nst[0] >= xs[i]) {
        const r = (xs[i] - x) / (nst[0] - x);
        const L = k => st[k] + (nst[k] - st[k]) * r;
        out.push({ x: xs[i], y: L(1), z: L(2), v: Math.hypot(L(3), L(4), L(5)), t: L(6) });
        i++;
      }
      st = nst;
    }
    return out;
  }

  /* p: { bc, model, w (gr), mv (fps), sight (in), zero (yd), temp (°F), alt (ft),
          press (inHg, 0 = from altitude), rh (%), wind (mph), clock (1–12), angle (°),
          ranges: [yd,...] } */
  function solve(p) {
    if (!(p.bc > 0) || !(p.mv > 0) || !(p.zero > 0)) return { error: 'Enter a BC, muzzle velocity and zero range.' };
    const atm = atmosphere(p.temp, p.alt || 0, p.press, p.rh || 0);
    const s = { model: p.model === 'G7' ? 'G7' : 'G1', K: (Math.PI / 8) / (p.bc * LBIN2),
      rho: atm.rho, c: atm.c, v0: p.mv * FPS, h: (p.sight || 0) * IN };

    // Zero under current conditions, level, no wind.
    const zx = p.zero * YD;
    let alpha = Math.atan(s.h / zx);
    for (let n = 0; n < 25; n++) {
      const r = fly(s, alpha, 0, 0, 0, [zx])[0];
      if (!r) return { error: 'Bullet never reaches the zero range with these inputs.' };
      if (Math.abs(r.y) < 1e-6) break;
      alpha -= r.y / zx;
    }

    const ang = ((p.clock || 12) % 12) * 30 * Math.PI / 180;
    const W = (p.wind || 0) * MPH;
    const wx = -W * Math.cos(ang), wz = -W * Math.sin(ang);
    const theta = (p.angle || 0) * Math.PI / 180;
    const xs = [...new Set(p.ranges.filter(r => r > 0))].sort((a, b) => a - b).map(r => r * YD);
    const pts = fly(s, alpha, theta, wx, wz, xs);

    const rows = pts.map(q => {
      const vf = q.v / FPS;
      const elev = -Math.atan2(q.y, q.x), wind = -Math.atan2(q.z, q.x);
      return { yd: Math.round(q.x / YD), dropIn: q.y / IN, windIn: q.z / IN,
        elevMil: elev * 1000, elevMoa: elev * 180 / Math.PI * 60,
        windMil: wind * 1000, windMoa: wind * 180 / Math.PI * 60,
        fps: vf, ftlb: (p.w || 0) * vf * vf / 450240, tof: q.t, mach: q.v / s.c };
    });
    return { rows, atm, cross: W / MPH * Math.sin(ang), head: W / MPH * Math.cos(ang) };
  }

  return { solve, atmosphere };
})();
