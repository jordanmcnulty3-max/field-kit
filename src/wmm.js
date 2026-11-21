/* ---------- World Magnetic Model: magnetic declination from a position and a date. No DOM. ----------
   Coefficients: WMM2025 (epoch 2025.0, valid 2025.0 to 2030.0), Table 2 of "The US/UK World Magnetic Model for
   2025-2030: Technical Report" (NOAA NCEI and British Geological Survey), opened 2026-11-20 at
   https://s3.us-east-1.amazonaws.com/library.oarcloud.noaa.gov/noaa_documents.lib/NESDIS/NCEI/WWM_Report_2025.pdf
   Checked against NOAA's "Test Values for WMM2025" (tests/test_wmm.py). Public domain (US Government work).
   Each row: n, m, g, h, g-dot, h-dot (nT and nT per year); h and h-dot are 0 where m is 0. */
const WMM = (() => {
  const C = [
    1, 0, -29351.8, 0, 12, 0,
    1, 1, -1410.8, 4545.4, 9.7, -21.5,
    2, 0, -2556.6, 0, -11.6, 0,
    2, 1, 2951.1, -3133.6, -5.2, -27.7,
    2, 2, 1649.3, -815.1, -8, -12.1,
    3, 0, 1361, 0, -1.3, 0,
    3, 1, -2404.1, -56.6, -4.2, 4,
    3, 2, 1243.8, 237.5, 0.4, -0.3,
    3, 3, 453.6, -549.5, -15.6, -4.1,
    4, 0, 895, 0, -1.6, 0,
    4, 1, 799.5, 278.6, -2.4, -1.1,
    4, 2, 55.7, -133.9, -6, 4.1,
    4, 3, -281.1, 212, 5.6, 1.6,
    4, 4, 12.1, -375.6, -7, -4.4,
    5, 0, -233.2, 0, 0.6, 0,
    5, 1, 368.9, 45.4, 1.4, -0.5,
    5, 2, 187.2, 220.2, 0, 2.2,
    5, 3, -138.7, -122.9, 0.6, 0.4,
    5, 4, -142, 43, 2.2, 1.7,
    5, 5, 20.9, 106.1, 0.9, 1.9,
    6, 0, 64.4, 0, -0.2, 0,
    6, 1, 63.8, -18.4, -0.4, 0.3,
    6, 2, 76.9, 16.8, 0.9, -1.6,
    6, 3, -115.7, 48.8, 1.2, -0.4,
    6, 4, -40.9, -59.8, -0.9, 0.9,
    6, 5, 14.9, 10.9, 0.3, 0.7,
    6, 6, -60.7, 72.7, 0.9, 0.9,
    7, 0, 79.5, 0, 0, 0,
    7, 1, -77, -48.9, -0.1, 0.6,
    7, 2, -8.8, -14.4, -0.1, 0.5,
    7, 3, 59.3, -1, 0.5, -0.8,
    7, 4, 15.8, 23.4, -0.1, 0,
    7, 5, 2.5, -7.4, -0.8, -1,
    7, 6, -11.1, -25.1, -0.8, 0.6,
    7, 7, 14.2, -2.3, 0.8, -0.2,
    8, 0, 23.2, 0, -0.1, 0,
    8, 1, 10.8, 7.1, 0.2, -0.2,
    8, 2, -17.5, -12.6, 0, 0.5,
    8, 3, 2, 11.4, 0.5, -0.4,
    8, 4, -21.7, -9.7, -0.1, 0.4,
    8, 5, 16.9, 12.7, 0.3, -0.5,
    8, 6, 15, 0.7, 0.2, -0.6,
    8, 7, -16.8, -5.2, 0, 0.3,
    8, 8, 0.9, 3.9, 0.2, 0.2,
    9, 0, 4.6, 0, 0, 0,
    9, 1, 7.8, -24.8, -0.1, -0.3,
    9, 2, 3, 12.2, 0.1, 0.3,
    9, 3, -0.2, 8.3, 0.3, -0.3,
    9, 4, -2.5, -3.3, -0.3, 0.3,
    9, 5, -13.1, -5.2, 0, 0.2,
    9, 6, 2.4, 7.2, 0.3, -0.1,
    9, 7, 8.6, -0.6, -0.1, -0.2,
    9, 8, -8.7, 0.8, 0.1, 0.4,
    9, 9, -12.9, 10, -0.1, 0.1,
    10, 0, -1.3, 0, 0.1, 0,
    10, 1, -6.4, 3.3, 0, 0,
    10, 2, 0.2, 0, 0.1, 0,
    10, 3, 2, 2.4, 0.1, -0.2,
    10, 4, -1, 5.3, 0, 0.1,
    10, 5, -0.6, -9.1, -0.3, -0.1,
    10, 6, -0.9, 0.4, 0, 0.1,
    10, 7, 1.5, -4.2, -0.1, 0,
    10, 8, 0.9, -3.8, -0.1, -0.1,
    10, 9, -2.7, 0.9, 0, 0.2,
    10, 10, -3.9, -9.1, 0, 0,
    11, 0, 2.9, 0, 0, 0,
    11, 1, -1.5, 0, 0, 0,
    11, 2, -2.5, 2.9, 0, 0.1,
    11, 3, 2.4, -0.6, 0, 0,
    11, 4, -0.6, 0.2, 0, 0.1,
    11, 5, -0.1, 0.5, -0.1, 0,
    11, 6, -0.6, -0.3, 0, 0,
    11, 7, -0.1, -1.2, 0, 0.1,
    11, 8, 1.1, -1.7, -0.1, 0,
    11, 9, -1, -2.9, -0.1, 0,
    11, 10, -0.2, -1.8, -0.1, 0,
    11, 11, 2.6, -2.3, -0.1, 0,
    12, 0, -2, 0, 0, 0,
    12, 1, -0.2, -1.3, 0, 0,
    12, 2, 0.3, 0.7, 0, 0,
    12, 3, 1.2, 1, 0, -0.1,
    12, 4, -1.3, -1.4, 0, 0.1,
    12, 5, 0.6, 0, 0, 0,
    12, 6, 0.6, 0.6, 0.1, 0,
    12, 7, 0.5, -0.1, 0, 0,
    12, 8, -0.1, 0.8, 0, 0,
    12, 9, -0.4, 0.1, 0, 0,
    12, 10, -0.2, -1, -0.1, 0,
    12, 11, -1.3, 0.1, 0, 0,
    12, 12, -0.7, 0.2, -0.1, -0.1,
  ];
  const N = 12, EPOCH = 2025.0, VALID_UNTIL = 2030.0;
  const A_REF = 6371.2;                                   // geomagnetic reference radius, km
  const WGS_A = 6378.137, WGS_F = 1 / 298.257223563;      // WGS84 ellipsoid
  const E2 = WGS_F * (2 - WGS_F);
  const D2R = Math.PI / 180;

  /* Declination in degrees, east positive, at geodetic lat/lon (degrees), altitude above the ellipsoid (km) and
     decimal year. Null where it is undefined (exactly at a geographic pole) or the input is not a number.
     Dates outside the model's validity still give a number: the caller decides what to say. */
  function declination(lat, lon, altKm, year) {
    if (![lat, lon, altKm, year].every(Number.isFinite) || Math.abs(lat) > 90) return null;
    const phi = lat * D2R, lam = lon * D2R;
    // Geodetic to geocentric spherical.
    const sp = Math.sin(phi), cp = Math.cos(phi);
    const Rc = WGS_A / Math.sqrt(1 - E2 * sp * sp);
    const p = (Rc + altKm) * cp, z = (Rc * (1 - E2) + altKm) * sp;
    const r = Math.hypot(p, z), phic = Math.asin(z / r);
    const x = Math.sin(phic), c = Math.cos(phic);        // cos and sin of geocentric colatitude
    if (c < 1e-10) return null;
    // Schmidt semi-normalised associated Legendre functions P[n][m] of cos(colatitude), and dP/d(colatitude).
    const P = [], dP = [];
    for (let n = 0; n <= N; n++) { P.push(new Array(N + 1).fill(0)); dP.push(new Array(N + 1).fill(0)); }
    P[0][0] = 1;
    for (let n = 1; n <= N; n++) {
      for (let m = 0; m <= n; m++) {
        if (n === m) {
          const k = n === 1 ? 1 : Math.sqrt((2 * n - 1) / (2 * n));
          P[n][n] = k * c * P[n - 1][n - 1];
          dP[n][n] = k * (c * dP[n - 1][n - 1] + x * P[n - 1][n - 1]);
        } else {
          const k1 = Math.sqrt(n * n - m * m), k2 = n >= 2 ? Math.sqrt((n - 1) * (n - 1) - m * m) : 0;
          const Pn2 = n >= 2 ? P[n - 2][m] : 0, dPn2 = n >= 2 ? dP[n - 2][m] : 0;
          P[n][m] = ((2 * n - 1) * x * P[n - 1][m] - k2 * Pn2) / k1;
          dP[n][m] = ((2 * n - 1) * (x * dP[n - 1][m] - c * P[n - 1][m]) - k2 * dPn2) / k1;
        }
      }
    }
    const dt = year - EPOCH;
    let X = 0, Y = 0, Z = 0;
    for (let i = 0; i < C.length; i += 6) {
      const n = C[i], m = C[i + 1];
      const g = C[i + 2] + dt * C[i + 4], h = C[i + 3] + dt * C[i + 5];
      const ar = Math.pow(A_REF / r, n + 2);
      const cm = Math.cos(m * lam), sm = Math.sin(m * lam);
      const gh = g * cm + h * sm;
      X += ar * gh * dP[n][m];                            // north, geocentric frame
      Y += ar * m * (g * sm - h * cm) * P[n][m] / c;      // east
      Z -= ar * (n + 1) * gh * P[n][m];                   // down
    }
    // Rotate north and down back to the geodetic frame (east is unchanged); declination needs only north.
    const psi = phic - phi;
    const Xg = X * Math.cos(psi) - Z * Math.sin(psi);
    return Math.atan2(Y, Xg) / D2R;
  }

  return { name: 'WMM2025', epoch: EPOCH, validUntil: VALID_UNTIL, declination };
})();
