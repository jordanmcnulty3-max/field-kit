/* ---------- Geo: WGS84 UTM / MGRS, distance, bearing ---------- */
const GEO = (() => {
  const a = 6378137, f = 1 / 298.257223563, k0 = 0.9996;
  const e2 = f * (2 - f), ep2 = e2 / (1 - e2);
  const D2R = Math.PI / 180, R2D = 180 / Math.PI;
  const BANDS = 'CDEFGHJKLMNPQRSTUVWX';
  const COLS = ['ABCDEFGH', 'JKLMNPQR', 'STUVWXYZ'];
  const ROWS = 'ABCDEFGHJKLMNPQRSTUV';

  function zoneFor(lat, lon) {
    let z = Math.floor((lon + 180) / 6) + 1;
    if (z > 60) z = 60;
    if (lat >= 56 && lat < 64 && lon >= 3 && lon < 12) z = 32;
    if (lat >= 72 && lat < 84) {
      if (lon >= 0 && lon < 9) z = 31;
      else if (lon >= 9 && lon < 21) z = 33;
      else if (lon >= 21 && lon < 33) z = 35;
      else if (lon >= 33 && lon < 42) z = 37;
    }
    return z;
  }

  function toUTM(lat, lon, forceZone) {
    const zone = forceZone || zoneFor(lat, lon);
    const lon0 = ((zone - 1) * 6 - 180 + 3) * D2R;
    const p = lat * D2R, l = lon * D2R;
    const sp = Math.sin(p), cp = Math.cos(p), tp = Math.tan(p);
    const N = a / Math.sqrt(1 - e2 * sp * sp);
    const T = tp * tp, C = ep2 * cp * cp, A = cp * (l - lon0);
    const M = a * ((1 - e2 / 4 - 3 * e2 * e2 / 64 - 5 * e2 ** 3 / 256) * p
      - (3 * e2 / 8 + 3 * e2 * e2 / 32 + 45 * e2 ** 3 / 1024) * Math.sin(2 * p)
      + (15 * e2 * e2 / 256 + 45 * e2 ** 3 / 1024) * Math.sin(4 * p)
      - (35 * e2 ** 3 / 3072) * Math.sin(6 * p));
    const easting = k0 * N * (A + (1 - T + C) * A ** 3 / 6
      + (5 - 18 * T + T * T + 72 * C - 58 * ep2) * A ** 5 / 120) + 500000;
    let northing = k0 * (M + N * tp * (A * A / 2 + (5 - T + 9 * C + 4 * C * C) * A ** 4 / 24
      + (61 - 58 * T + T * T + 600 * C - 330 * ep2) * A ** 6 / 720));
    if (lat < 0) northing += 10000000;
    return { zone, hemi: lat < 0 ? 'S' : 'N', easting, northing };
  }

  function fromUTM(zone, hemi, E, N) {
    const x = E - 500000, y = hemi === 'S' ? N - 10000000 : N;
    const lon0 = ((zone - 1) * 6 - 180 + 3) * D2R;
    const mu = (y / k0) / (a * (1 - e2 / 4 - 3 * e2 * e2 / 64 - 5 * e2 ** 3 / 256));
    const e1 = (1 - Math.sqrt(1 - e2)) / (1 + Math.sqrt(1 - e2));
    const p1 = mu + (3 * e1 / 2 - 27 * e1 ** 3 / 32) * Math.sin(2 * mu)
      + (21 * e1 * e1 / 16 - 55 * e1 ** 4 / 32) * Math.sin(4 * mu)
      + (151 * e1 ** 3 / 96) * Math.sin(6 * mu)
      + (1097 * e1 ** 4 / 512) * Math.sin(8 * mu);
    const sp = Math.sin(p1), cp = Math.cos(p1), tp = Math.tan(p1);
    const N1 = a / Math.sqrt(1 - e2 * sp * sp);
    const T1 = tp * tp, C1 = ep2 * cp * cp;
    const R1 = a * (1 - e2) / Math.pow(1 - e2 * sp * sp, 1.5);
    const D = x / (N1 * k0);
    const lat = p1 - (N1 * tp / R1) * (D * D / 2
      - (5 + 3 * T1 + 10 * C1 - 4 * C1 * C1 - 9 * ep2) * D ** 4 / 24
      + (61 + 90 * T1 + 298 * C1 + 45 * T1 * T1 - 252 * ep2 - 3 * C1 * C1) * D ** 6 / 720);
    const lon = lon0 + (D - (1 + 2 * T1 + C1) * D ** 3 / 6
      + (5 - 2 * C1 + 28 * T1 - 3 * C1 * C1 + 8 * ep2 + 24 * T1 * T1) * D ** 5 / 120) / cp;
    return { lat: lat * R2D, lon: lon * R2D };
  }

  /* MGRS (WGS84, AA lettering). Polar UPS regions are not covered. */
  function toMGRS(lat, lon, digits = 5) {
    if (!(lat >= -80 && lat < 84)) return null;
    const u = toUTM(lat, lon);
    const band = BANDS[Math.min(19, Math.floor((lat + 80) / 8))];
    const col = Math.floor(u.easting / 1e5);
    const colL = COLS[(u.zone - 1) % 3][col - 1];
    const rowL = ROWS[(Math.floor(u.northing / 1e5) + (u.zone % 2 === 0 ? 5 : 0)) % 20];
    const div = Math.pow(10, 5 - digits);
    // 1 mm tolerance so round-tripped grids don't floor 25000 down to 24999
    const e = String(Math.floor(((u.easting + 1e-3) % 1e5) / div)).padStart(digits, '0');
    const n = String(Math.floor(((u.northing + 1e-3) % 1e5) / div)).padStart(digits, '0');
    return { gzd: `${u.zone}${band}`, sq: colL + rowL, e, n, text: `${u.zone}${band} ${colL}${rowL} ${e} ${n}` };
  }

  function parseMGRS(str) {
    const s = String(str).toUpperCase().replace(/\s+/g, '');
    const m = s.match(/^(\d{1,2})([C-HJ-NP-X])([A-HJ-NP-Z])([A-HJ-NP-V])(\d*)$/);
    if (!m) return null;
    const zone = +m[1], band = m[2], colL = m[3], rowL = m[4], digs = m[5];
    if (zone < 1 || zone > 60 || digs.length % 2 || digs.length > 10) return null;
    const half = digs.length / 2;
    const scale = Math.pow(10, 5 - half);
    const centre = half < 5 ? scale / 2 : 0; // middle of the square at reduced precision
    const eVal = (half ? +digs.slice(0, half) : 0) * scale + centre;
    const nVal = (half ? +digs.slice(half) : 0) * scale + centre;
    const colIdx = COLS[(zone - 1) % 3].indexOf(colL);
    if (colIdx < 0) return null;
    let rowIdx = ROWS.indexOf(rowL);
    if (zone % 2 === 0) rowIdx = (rowIdx - 5 + 20) % 20;
    const E = (colIdx + 1) * 1e5 + eVal;
    let N = rowIdx * 1e5 + nVal;
    const latBand = BANDS.indexOf(band) * 8 - 80;
    const hemi = latBand >= 0 ? 'N' : 'S';
    const cm = (zone - 1) * 6 - 180 + 3;
    const nBand = Math.floor(toUTM(latBand, cm, zone).northing / 1e5) * 1e5;
    let n2M = 0;
    while (n2M + N < nBand) n2M += 2e6;
    N += n2M;
    return fromUTM(zone, hemi, E, N);
  }

  /* Degrees with hemisphere letters, in any of the usual shapes:
     38°53′51.6″N 77°02′11.4″W · 38 53 51.6 N, 77 2 11.4 W · 38.8977N 77.0365W · N38.8977 W77.0365 · 38°53.86'N */
  function parseHemi(str) {
    const s = String(str).toUpperCase().replace(/[′’‘]/g, "'").replace(/[″”“]/g, '"').replace(/º/g, '°').replace(/,/g, ' ').trim();
    if (/[^0-9.°'"\sNSEW]/.test(s)) return null;
    const letters = s.match(/[NSEW]/g);
    if (!letters || letters.length !== 2) return null;
    // Split into the two coordinates: after the first letter if letters trail the numbers, before the second if they lead.
    const i1 = s.search(/[NSEW]/), i2 = s.slice(i1 + 1).search(/[NSEW]/) + i1 + 1;
    const parts = /^[NSEW]/.test(s) ? [s.slice(0, i2), s.slice(i2)] : [s.slice(0, i1 + 1), s.slice(i1 + 1)];
    const out = {};
    for (const part of parts) {
      const h = part.match(/[NSEW]/)[0], nums = part.match(/\d+(?:\.\d+)?/g);
      if (!nums || nums.length > 3 || nums.slice(0, -1).some(n => n.includes('.'))) return null;
      const [d, m = 0, sec = 0] = nums.map(Number);
      if (m >= 60 || sec >= 60) return null;
      const v = (d + m / 60 + sec / 3600) * (h === 'S' || h === 'W' ? -1 : 1);
      const axis = h === 'N' || h === 'S' ? 'lat' : 'lon';
      if (axis in out) return null;
      out[axis] = v;
    }
    if (Math.abs(out.lat) > 90 || Math.abs(out.lon) > 180) return null;
    return { lat: out.lat, lon: out.lon };
  }

  /* Accepts MGRS, "lat, lon" in decimal degrees, or degrees/minutes/seconds with N/S/E/W. */
  function parseAny(str) {
    const ll = String(str).trim().match(/^(-?\d+(?:\.\d+)?)\s*[,\s]\s*(-?\d+(?:\.\d+)?)$/);
    if (ll) {
      const lat = +ll[1], lon = +ll[2];
      if (Math.abs(lat) <= 90 && Math.abs(lon) <= 180) return { lat, lon };
      return null;
    }
    return parseMGRS(str) || parseHemi(str);
  }

  function distance(lat1, lon1, lat2, lon2) {
    const R = 6371008.8;
    const dp = (lat2 - lat1) * D2R, dl = (lon2 - lon1) * D2R;
    const h = Math.sin(dp / 2) ** 2 + Math.cos(lat1 * D2R) * Math.cos(lat2 * D2R) * Math.sin(dl / 2) ** 2;
    return 2 * R * Math.asin(Math.min(1, Math.sqrt(h)));
  }

  function bearing(lat1, lon1, lat2, lon2) {
    const p1 = lat1 * D2R, p2 = lat2 * D2R, dl = (lon2 - lon1) * D2R;
    const y = Math.sin(dl) * Math.cos(p2);
    const x = Math.cos(p1) * Math.sin(p2) - Math.sin(p1) * Math.cos(p2) * Math.cos(dl);
    return (Math.atan2(y, x) * R2D + 360) % 360;
  }

  function dms(v, pos, neg) {
    const h = v < 0 ? neg : pos;
    v = Math.abs(v);
    let d = Math.floor(v), m = Math.floor((v - d) * 60), s = ((v - d) * 60 - m) * 60;
    if (s >= 59.95) { s = 0; m += 1; }
    if (m >= 60) { m = 0; d += 1; }
    return `${d}°${String(m).padStart(2, '0')}′${s.toFixed(1).padStart(4, '0')}″${h}`;
  }

  const CARD = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW'];
  const cardinal = deg => CARD[Math.round(((deg % 360) + 360) % 360 / 22.5) % 16];

  return { toUTM, fromUTM, toMGRS, parseMGRS, parseAny, distance, bearing, dms, cardinal };
})();
