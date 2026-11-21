/* ---------- Tactical geometry: sphere maths for markers, routes, areas, rings and the scale bar. No DOM. ---------- */
const TGEOM = (() => {
  const R = 6371008.8;   // the same radius GEO.distance uses
  const D2R = Math.PI / 180, R2D = 180 / Math.PI;
  const YD = 0.9144, MI = 1609.344, ACRE = 4046.8564224, SQFT = 0.09290304;

  /* The point distM metres from (lat, lon) along the great circle that leaves at bearingDeg (true). */
  function dest(lat, lon, bearingDeg, distM) {
    const p1 = lat * D2R, l1 = lon * D2R, b = bearingDeg * D2R, dr = distM / R;
    const p2 = Math.asin(Math.sin(p1) * Math.cos(dr) + Math.cos(p1) * Math.sin(dr) * Math.cos(b));
    const l2 = l1 + Math.atan2(Math.sin(b) * Math.sin(dr) * Math.cos(p1), Math.cos(dr) - Math.sin(p1) * Math.sin(p2));
    return { lat: p2 * R2D, lon: ((l2 * R2D + 540) % 360) - 180 };
  }

  /* A circle of n segments as [lat, lon] pairs; the first point is repeated at the end so it closes. */
  function ring(lat, lon, rM, n = 72) {
    const pts = [];
    for (let i = 0; i < n; i++) { const p = dest(lat, lon, i * 360 / n, rM); pts.push([p.lat, p.lon]); }
    pts.push(pts[0].slice());
    return pts;
  }

  const pathLength = pts => pts.reduce((s, p, i) => i ? s + GEO.distance(pts[i - 1][0], pts[i - 1][1], p[0], p[1]) : 0, 0);

  /* What a recorded track tells: track is [lat, lon, alt|null, timeMs] points. Elapsed is latest time minus earliest over
     the points with a usable time. A leg between neighbours counts as moving when its time gap is more than 0 and at most
     10 min AND its own speed (leg distance / leg time) is at least 0.3 m/s; any other leg is a pause. Points are recorded
     only past twice the accuracy (map.js), so in poor accuracy a steady walk leaves legs of a minute or more: the speed, not
     the gap, tells walking from standing. movingDist is the distance across the moving legs only. */
  const PAUSE_MS = 600000, MIN_MOVING_V = 0.3;
  function trackStats(track) {
    const times = track.map(p => p[3]).filter(t => Number.isFinite(t));
    const out = { dist: pathLength(track), elapsedMs: 0, movingMs: 0, movingDist: 0 };
    if (times.length < 2) return out;
    out.elapsedMs = Math.max(...times) - Math.min(...times);
    for (let i = 1; i < track.length; i++) {
      const g = track[i][3] - track[i - 1][3];
      if (!(g > 0 && g <= PAUSE_MS)) continue;
      const d = GEO.distance(track[i - 1][0], track[i - 1][1], track[i][0], track[i][1]);
      if (d / (g / 1000) >= MIN_MOVING_V) { out.movingMs += g; out.movingDist += d; }
    }
    out.movingMs = Math.min(out.movingMs, out.elapsedMs);   // out-of-order times can't make more moving time than time
    return out;
  }

  /* Flat projection around the shape's own centre: within 1% for anything under 100 km2. */
  function areaM2(pts) {
    if (!pts || pts.length < 3) return 0;
    const lat0 = pts.reduce((s, p) => s + p[0], 0) / pts.length, lon0 = pts.reduce((s, p) => s + p[1], 0) / pts.length;
    const k = Math.cos(lat0 * D2R);
    const xy = pts.map(p => [R * D2R * (p[1] - lon0) * k, R * D2R * (p[0] - lat0)]);
    let a = 0;
    for (let i = 0; i < xy.length; i++) { const q = xy[(i + 1) % xy.length]; a += xy[i][0] * q[1] - q[0] * xy[i][1]; }
    return Math.abs(a) / 2;
  }

  /* Two decimals under 10, one above; a value that rounds up to 10 reads as "10.0", never "10.00". */
  const big = v => { const s = v.toFixed(2); return v < 10 && +s < 10 ? s : v.toFixed(1); };
  function fmtDist(m, unit) {
    if (unit === 'us') {
      const yd = m / YD;
      return Math.round(yd) < 1000 ? `${Math.round(yd)} yd` : `${big(m / MI)} mi`;
    }
    return Math.round(m) < 1000 ? `${Math.round(m)} m` : `${big(m / 1000)} km`;
  }

  function fmtArea(m2, unit) {
    if (unit === 'us') {
      const ac = m2 / ACRE;
      return ac < 0.1 ? `${Math.round(m2 / SQFT).toLocaleString('en-US')} sq ft` : `${ac.toFixed(1)} acres`;
    }
    return m2 < 10000 ? `${Math.round(m2)} m²` : `${(m2 / 10000).toFixed(1)} ha`;
  }

  /* The longest 1, 2 or 5 x 10^n that fits in maxPx at mPerPx metres a pixel. */
  function nice(max) {
    const e = Math.pow(10, Math.floor(Math.log10(max))), f = max / e;
    return (f >= 5 ? 5 : f >= 2 ? 2 : 1) * e;
  }
  function scale(mPerPx, maxPx, unit) {
    const maxM = mPerPx * maxPx;
    let n, m, label;
    if (unit === 'us') {
      if (maxM / YD < 1760) { n = nice(maxM / YD); m = n * YD; label = `${n} yd`; }
      else { n = nice(maxM / MI); m = n * MI; label = `${n} mi`; }
    } else if (maxM < 1000) { n = nice(maxM); m = n; label = `${n} m`; }
    else { n = nice(maxM / 1000); m = n * 1000; label = `${n} km`; }
    return { px: m / mPerPx, label };
  }

  return { dest, ring, pathLength, trackStats, areaM2, fmtDist, fmtArea, scale };
})();
