"""TGEOM: sphere geometry for the tactical map. Reference pairs are recorded in docs/content-review.md (v7.8 Tactical)."""
import pytest

# (label, lat1, lon1, lat2, lon2, published ellipsoid distance in metres, published initial azimuth in degrees)
REF = [
    ('Prince George\'s CC to the Great Pyramid', 38.888019, -76.823094, 29.979175, 31.134358, 9351378.858, 55.910048),
    ('Vincenty test case 00', 37.331932, 0.0, 26.128567, 41.476530, 4085966.7026, 95.4666),
    ('Vincenty test case 01', 35.269791, 0.0, 67.370771, 137.791198, 8084823.8383, 15.7399),
]


@pytest.fixture
def ready(page, app_url):
    page.goto(app_url)
    page.wait_for_function('window.FK && typeof TGEOM !== "undefined"')
    return page


def ev(page, expr, arg=None):
    return page.evaluate(expr, arg)


@pytest.mark.parametrize('ref', REF, ids=[r[0] for r in REF])
def test_distance_matches_published_reference_pairs(ready, ref):
    _, la1, lo1, la2, lo2, dist, az = ref
    d = ev(ready, '([a, b, c, e]) => GEO.distance(a, b, c, e)', [la1, lo1, la2, lo2])
    assert abs(d / dist - 1) < 0.005
    b = ev(ready, '([a, b, c, e]) => GEO.bearing(a, b, c, e)', [la1, lo1, la2, lo2])
    assert abs(b - az) < 0.5   # sphere against ellipsoid: bearings differ by a fraction of a degree


def test_dest_round_trips_through_distance_and_bearing(ready):
    d, b = ev(ready, """() => { const p = TGEOM.dest(43, -76, 73, 1000);
      return [GEO.distance(43, -76, p.lat, p.lon), GEO.bearing(43, -76, p.lat, p.lon)]; }""")
    assert abs(d - 1000) < 1
    assert abs(b - 73) < 0.1


def test_ring_is_closed_and_round(ready):
    pts, ds = ev(ready, """() => { const r = TGEOM.ring(43, -76, 500);
      return [r, r.map(p => GEO.distance(43, -76, p[0], p[1]))]; }""")
    assert len(pts) == 73
    assert pts[0] == pts[-1]
    assert all(abs(d - 500) < 5 for d in ds)


def test_area_of_a_kilometre_square(ready):
    a = ev(ready, """() => { let p = { lat: 43, lon: -76 }; const pts = [[p.lat, p.lon]];
      for (const b of [90, 0, 270]) { p = TGEOM.dest(p.lat, p.lon, b, 1000); pts.push([p.lat, p.lon]); }
      return TGEOM.areaM2(pts); }""")
    assert abs(a - 1e6) < 1e4
    assert ev(ready, 'TGEOM.areaM2([[43, -76], [43.01, -76]])') == 0
    assert ev(ready, 'TGEOM.areaM2([])') == 0


def test_path_length_adds_the_legs(ready):
    d = ev(ready, """() => { const a = TGEOM.dest(43, -76, 0, 300), b = TGEOM.dest(a.lat, a.lon, 90, 400);
      return TGEOM.pathLength([[43, -76], [a.lat, a.lon], [b.lat, b.lon]]); }""")
    assert abs(d - 700) < 1
    assert ev(ready, 'TGEOM.pathLength([[43, -76]])') == 0


@pytest.mark.parametrize('m,unit,want', [(412, 'metric', '412 m'), (1240, 'metric', '1.24 km'), (12400, 'metric', '12.4 km'),
                                          (412, 'us', '451 yd'), (2000, 'us', '1.24 mi'), (999.7, 'metric', '1.00 km')])
def test_fmt_dist(ready, m, unit, want):
    assert ev(ready, '([m, u]) => TGEOM.fmtDist(m, u)', [m, unit]) == want


@pytest.mark.parametrize('m,unit,want', [
    (5, 'metric', '5 m'), (412, 'metric', '412 m'), (999.4, 'metric', '999 m'),
    (999.6, 'metric', '1.00 km'),    # v7.7 printed "1000 m" here; a value that belongs to the next band reads in that band
    (1000, 'metric', '1.00 km'), (9999, 'metric', '10.0 km'),   # v7.7 printed "10.00 km" for 9999
    (9994, 'metric', '9.99 km'), (10000, 'metric', '10.0 km'), (25000, 'metric', '25.0 km'),
    (999.4 * 0.9144, 'us', '999 yd'), (999.6 * 0.9144, 'us', '0.57 mi'), (1609.344 * 9.999, 'us', '10.0 mi'),
    (1609.344 * 9.994, 'us', '9.99 mi'), (1609.344 * 25, 'us', '25.0 mi')])
def test_fmt_dist_never_prints_a_value_from_the_next_band(ready, m, unit, want):
    assert ev(ready, '([m, u]) => TGEOM.fmtDist(m, u)', [m, unit]) == want


@pytest.mark.parametrize('m2,unit,want', [(8094, 'us', '2.0 acres'), (24000, 'metric', '2.4 ha'), (850, 'metric', '850 m²'),
                                           (8500, 'us', '2.1 acres'), (390, 'us', '4,198 sq ft')])
def test_fmt_area(ready, m2, unit, want):
    assert ev(ready, '([m, u]) => TGEOM.fmtArea(m, u)', [m2, unit]) == want


def test_scale_bar_picks_1_2_5(ready):
    s = ev(ready, 'TGEOM.scale(1.9, 120, "metric")')
    assert s['label'] == '200 m'
    assert abs(s['px'] - 105) <= 1
    u = ev(ready, 'TGEOM.scale(1.9, 120, "us")')
    assert u['label'].endswith(' yd') and u['px'] <= 120
    big = ev(ready, 'TGEOM.scale(100, 120, "us")')
    assert big['label'].endswith(' mi') and big['px'] <= 120
    km = ev(ready, 'TGEOM.scale(20, 120, "metric")')
    assert km['label'] == '2 km'


def test_fifty_km_ring_is_round_to_one_percent(ready):
    # The ring is drawn on the same sphere as GEO.distance, whose agreement with the ellipsoid is the 0.5% shown by the
    # reference pairs above, so the 1% bound on a 50 km ring follows from that check.
    ds, ext = ev(ready, """() => { const r = TGEOM.ring(43, -76, 50000);
      const lat = r.map(p => p[0]), lon = r.map(p => p[1]);
      const ns = GEO.distance(Math.min(...lat), -76, Math.max(...lat), -76);
      const ew = Math.max(...r.map(p => GEO.distance(43, -76, p[0], p[1]))) * 2;
      const east = r.reduce((a, p) => p[1] > a[1] ? p : a), west = r.reduce((a, p) => p[1] < a[1] ? p : a);
      return [r.map(p => GEO.distance(43, -76, p[0], p[1])), [ns, GEO.distance(east[0], east[1], west[0], west[1])]]; }""")
    assert all(abs(d / 50000 - 1) < 0.001 for d in ds)
    assert all(abs(e / 100000 - 1) < 0.01 for e in ext)
