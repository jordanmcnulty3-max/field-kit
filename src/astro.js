/* ---------- Astro: sun and moon times worked out on the phone, no network. Pure functions on window.FK_ASTRO. ----------
   Methods, so a later reader can check them:
   - Sun position: NOAA Solar Calculator equations (NOAA Global Monitoring Laboratory, "General Solar Position
     Calculations" / the NOAA_Solar_Calculations spreadsheet, after Meeus): declination and equation of time, then the
     hour angle from true solar time.
   - Moon position: Jean Meeus, Astronomical Algorithms (2nd ed.), chapter 47 (ELP-2000/82 series), keeping the
     largest terms of tables 47.A and 47.B (about 10 arc seconds in longitude); sidereal time from chapter 12;
     equatorial coordinates from chapter 13.
   - Rise and set altitudes (Meeus chapter 15): sun -0.833 degrees (refraction and the sun's half-width), civil
     twilight -6 degrees, moon 0.7275 x horizontal parallax - 0.5667 degrees.
   - Illuminated fraction from the phase angle (Meeus chapter 48).
   Rise and set times are found by sampling the altitude every 10 minutes across the local day and halving the
   bracket around each crossing until it is under a second.
   A "local day" runs from dayStartMs (local midnight, epoch ms) to the next local midnight, which this file gets from
   the phone's own clock rules (so a 23 or 25 hour day at a clock change is handled). Times out are epoch ms, or null
   when the event does not happen within that local day. */
(() => {
  const RAD = Math.PI / 180;
  const sin = d => Math.sin(d * RAD), cos = d => Math.cos(d * RAD), tan = d => Math.tan(d * RAD);
  const asin = x => Math.asin(Math.max(-1, Math.min(1, x))) / RAD;
  const atan2 = (y, x) => Math.atan2(y, x) / RAD;
  const norm = d => ((d % 360) + 360) % 360;

  const SUN_RISE_ALT = -0.833, CIVIL_ALT = -6;
  const STEP_MS = 10 * 60000;
  const AU_KM = 149597870.7, EARTH_RADIUS_KM = 6378.14;

  const julianDay = ms => ms / 86400000 + 2440587.5;
  const centuries = ms => (julianDay(ms) - 2451545) / 36525;

  /* The next local midnight after dayStartMs, by the phone's time zone rules. */
  function dayEnd(dayStartMs) {
    const d = new Date(dayStartMs);
    return new Date(d.getFullYear(), d.getMonth(), d.getDate() + 1).getTime();
  }

  /* ---------- Sun (NOAA) ---------- */
  function sunCoords(ms) {
    const T = centuries(ms);
    const L0 = norm(280.46646 + T * (36000.76983 + T * 0.0003032));       // geometric mean longitude
    const M = 357.52911 + T * (35999.05029 - 0.0001537 * T);               // geometric mean anomaly
    const e = 0.016708634 - T * (0.000042037 + 0.0000001267 * T);          // orbit eccentricity
    const C = sin(M) * (1.914602 - T * (0.004817 + 0.000014 * T)) + sin(2 * M) * (0.019993 - 0.000101 * T) + sin(3 * M) * 0.000289;
    const omega = 125.04 - 1934.136 * T;
    const appLong = L0 + C - 0.00569 - 0.00478 * sin(omega);              // apparent longitude
    const meanObliq = 23 + (26 + (21.448 - T * (46.815 + T * (0.00059 - T * 0.001813))) / 60) / 60;
    const obliq = meanObliq + 0.00256 * cos(omega);
    const decl = asin(sin(obliq) * sin(appLong));
    const y = tan(obliq / 2) ** 2;
    const eqTimeMin = 4 * (y * sin(2 * L0) - 2 * e * sin(M) + 4 * e * y * sin(M) * cos(2 * L0)
      - 0.5 * y * y * sin(4 * L0) - 1.25 * e * e * sin(2 * M)) / RAD;
    return { appLong, decl, eqTimeMin };
  }

  /* Sun altitude in degrees (no refraction) at a moment, for a place. */
  function sunAlt(ms, lat, lon) {
    const { decl, eqTimeMin } = sunCoords(ms);
    const utcMin = ((ms % 86400000) + 86400000) % 86400000 / 60000;
    const trueSolarMin = ((utcMin + eqTimeMin + 4 * lon) % 1440 + 1440) % 1440;
    const hourAngle = trueSolarMin / 4 - 180;
    return asin(sin(lat) * sin(decl) + cos(lat) * cos(decl) * cos(hourAngle));
  }

  /* ---------- Moon (Meeus chapter 47, main terms) ---------- */
  // [D, M, M', F, longitude (1e-6 deg), distance (1e-3 km)]
  const LR = [
    [0, 0, 1, 0, 6288774, -20905355], [2, 0, -1, 0, 1274027, -3699111], [2, 0, 0, 0, 658314, -2955968],
    [0, 0, 2, 0, 213618, -569925], [0, 1, 0, 0, -185116, 48888], [0, 0, 0, 2, -114332, -3149],
    [2, 0, -2, 0, 58793, 246158], [2, -1, -1, 0, 57066, -152138], [2, 0, 1, 0, 53322, -170733],
    [2, -1, 0, 0, 45758, -204586], [0, 1, -1, 0, -40923, -129620], [1, 0, 0, 0, -34720, 108743],
    [0, 1, 1, 0, -30383, 104755], [2, 0, 0, -2, 15327, 10321], [0, 0, 1, 2, -12528, 0],
    [0, 0, 1, -2, 10980, 79661], [4, 0, -1, 0, 10675, -34782], [0, 0, 3, 0, 10034, -23210],
    [4, 0, -2, 0, 8548, -21636], [2, 1, -1, 0, -7888, 24208], [2, 1, 0, 0, -6766, 30824],
    [1, 0, -1, 0, -5163, -8379], [1, 1, 0, 0, 4987, -16675], [2, -1, 1, 0, 4036, -12831],
    [2, 0, 2, 0, 3994, -10445], [4, 0, 0, 0, 3861, -11650], [2, 0, -3, 0, 3665, 14403],
    [0, 1, -2, 0, -2689, -7003], [2, 0, -1, 2, -2602, 0], [2, -1, -2, 0, 2390, 10056],
    [1, 0, 1, 0, -2348, 6322], [2, -2, 0, 0, 2236, -9884]
  ];
  // [D, M, M', F, latitude (1e-6 deg)]
  const B = [
    [0, 0, 0, 1, 5128122], [0, 0, 1, 1, 280602], [0, 0, 1, -1, 277693], [2, 0, 0, -1, 173237],
    [2, 0, -1, 1, 55413], [2, 0, -1, -1, 46271], [2, 0, 0, 1, 32573], [0, 0, 2, 1, 17198],
    [2, 0, 1, -1, 9266], [0, 0, 2, -1, 8822], [2, -1, 0, -1, 8216], [2, 0, -2, -1, 4324],
    [2, 0, 1, 1, 4200], [2, 1, 0, -1, -3359], [2, -1, -1, 1, 2463], [2, -1, 0, 1, 2211],
    [2, -1, -1, -1, 2065], [0, 1, -1, -1, -1870], [4, 0, -1, -1, 1828], [0, 1, 0, 1, -1794]
  ];

  function moonCoords(ms) {
    const T = centuries(ms);
    const Lp = norm(218.3164477 + 481267.88123421 * T);   // mean longitude
    const D = norm(297.8501921 + 445267.1114034 * T);     // mean elongation
    const M = norm(357.5291092 + 35999.0502909 * T);      // sun's mean anomaly
    const Mp = norm(134.9633964 + 477198.8675055 * T);    // moon's mean anomaly
    const F = norm(93.2720950 + 483202.0175233 * T);      // argument of latitude
    const E = 1 - 0.002516 * T - 0.0000074 * T * T;
    const A1 = 119.75 + 131.849 * T, A2 = 53.09 + 479264.290 * T, A3 = 313.45 + 481266.484 * T;
    const ecc = m => (m === 0 ? 1 : Math.abs(m) === 1 ? E : E * E);
    let sl = 0, sr = 0, sb = 0;
    for (const [d, m, mp, f, l, r] of LR) {
      const arg = d * D + m * M + mp * Mp + f * F;
      sl += l * ecc(m) * sin(arg);
      sr += r * ecc(m) * cos(arg);
    }
    for (const [d, m, mp, f, b] of B) sb += b * ecc(m) * sin(d * D + m * M + mp * Mp + f * F);
    sl += 3958 * sin(A1) + 1962 * sin(Lp - F) + 318 * sin(A2);
    sb += -2235 * sin(Lp) + 382 * sin(A3) + 175 * sin(A1 - F) + 175 * sin(A1 + F) + 127 * sin(Lp - Mp) - 115 * sin(Lp + Mp);
    const omega = 125.04452 - 1934.136261 * T;
    const lon = norm(Lp + sl / 1e6 - 0.004778 * sin(omega));   // apparent: plus nutation in longitude (main term)
    const lat = sb / 1e6;
    const distKm = 385000.56 + sr / 1000;
    const obliq = 23.439291 - 0.0130042 * T + 0.002560 * cos(omega);
    const ra = norm(atan2(sin(lon) * cos(obliq) - tan(lat) * sin(obliq), cos(lon)));
    const decl = asin(sin(lat) * cos(obliq) + cos(lat) * sin(obliq) * sin(lon));
    return { lon, lat, distKm, ra, decl };
  }

  function siderealDeg(ms) {   // Greenwich mean sidereal time (Meeus 12.4)
    const jd = julianDay(ms), T = (jd - 2451545) / 36525;
    return norm(280.46061837 + 360.98564736629 * (jd - 2451545) + 0.000387933 * T * T - T * T * T / 38710000);
  }

  /* Moon's geocentric altitude above its own rise/set altitude (which allows for parallax and refraction). */
  function moonAboveHorizon(ms, lat, lon) {
    const c = moonCoords(ms);
    const parallax = asin(EARTH_RADIUS_KM / c.distKm);
    const hourAngle = siderealDeg(ms) + lon - c.ra;
    const alt = asin(sin(lat) * sin(c.decl) + cos(lat) * cos(c.decl) * cos(hourAngle));
    return alt - (0.7275 * parallax - 0.5667);
  }

  /* Phase: 0 new, 0.25 first quarter, 0.5 full, 0.75 last quarter. Illuminated fraction 0 to 1. */
  function phaseAt(ms) {
    const m = moonCoords(ms), s = sunCoords(ms);
    const elong = Math.acos(Math.max(-1, Math.min(1, cos(m.lat) * cos(m.lon - s.appLong)))) / RAD;
    const phaseAngle = atan2(AU_KM * sin(elong), m.distKm - AU_KM * cos(elong));
    return { phase: norm(m.lon - s.appLong) / 360, illum: (1 + cos(phaseAngle)) / 2 };
  }

  const PRIMARY = [[0, 'New moon'], [0.25, 'First quarter'], [0.5, 'Full moon'], [0.75, 'Last quarter']];
  const BETWEEN = ['Waxing crescent', 'Waxing gibbous', 'Waning gibbous', 'Waning crescent'];
  /* A primary phase is named on the local day it happens; other days take the in-between name. */
  function phaseName(startPhase, endPhase, midPhase) {
    const span = (endPhase - startPhase + 1) % 1;
    for (const [q, name] of PRIMARY) if ((q - startPhase + 1) % 1 < span) return name;
    return BETWEEN[Math.min(3, Math.floor(midPhase * 4))];
  }

  /* ---------- Crossings ---------- */
  /* First upward and first downward crossing of f(t) = 0 within [start, end). */
  function crossings(f, start, end) {
    let up = null, down = null, t0 = start, v0 = f(start);
    while (t0 < end && (up === null || down === null)) {
      const t1 = Math.min(t0 + STEP_MS, end), v1 = f(t1);
      if ((v0 <= 0) !== (v1 <= 0)) {
        let a = t0, b = t1, va = v0;
        while (b - a > 500) {
          const mid = (a + b) / 2, vm = f(mid);
          if ((va <= 0) === (vm <= 0)) { a = mid; va = vm; } else b = mid;
        }
        const t = Math.round((a + b) / 2);
        if (v0 <= 0) { if (up === null) up = t; } else if (down === null) down = t;
      }
      t0 = t1; v0 = v1;
    }
    return { up, down };
  }

  function sun(dayStartMs, lat, lon) {
    const end = dayEnd(dayStartMs);
    const day = crossings(t => sunAlt(t, lat, lon) - SUN_RISE_ALT, dayStartMs, end);
    const civil = crossings(t => sunAlt(t, lat, lon) - CIVIL_ALT, dayStartMs, end);
    return { dawn: civil.up, rise: day.up, set: day.down, dusk: civil.down };
  }

  /* Time the sun's centre is above -0.833 degrees within the local day, in ms (whole day when it never sets). */
  function dayLength(dayStartMs, lat, lon) {
    const { rise, set } = sun(dayStartMs, lat, lon);
    if (rise !== null && set !== null && rise < set) return set - rise;
    const end = dayEnd(dayStartMs);   // no simple rise-then-set (polar days): add up the minutes the sun is up
    let total = 0;
    for (let t = dayStartMs; t < end; t += 60000) if (sunAlt(t + 30000, lat, lon) > SUN_RISE_ALT) total += Math.min(60000, end - t);
    return total;
  }

  function moon(dayStartMs, lat, lon) {
    const end = dayEnd(dayStartMs);
    const { up, down } = crossings(t => moonAboveHorizon(t, lat, lon), dayStartMs, end);
    const mid = phaseAt((dayStartMs + end) / 2);
    const name = phaseName(phaseAt(dayStartMs).phase, phaseAt(end).phase, mid.phase);
    return { rise: up, set: down, phase: mid.phase, illum: mid.illum, name };
  }

  window.FK_ASTRO = { sun, moon, sunAlt, dayLength, SUN_RISE_ALT, CIVIL_ALT };
})();
