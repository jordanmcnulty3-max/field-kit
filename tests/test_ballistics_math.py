"""Ballistics solver (src/ballistics.js) checked against published single-coefficient trajectories, the textbook parabola,
the standard atmospheres and the published drag-table values. Every source is recorded in docs/content-review.md
("Ballistics"); the rulings are in docs/ballistics-rulings.md."""
import json
import math
import os

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, 'fixtures', 'ballistics_reference.json')) as f:
    CASES = json.load(f)
JUDGED_CASES = [c for c in CASES if c['judged']]
with open(os.path.join(HERE, 'fixtures', 'ballistics_drag_tables.json')) as f:
    DRAG = json.load(f)

G = 9.80665
FPS = 0.3048
DEFAULT_308 = dict(bc=0.243, model='G7', w=175, mv=2600, sight=1.5, zero=100, temp=59, alt=0, press=0, rh=50,
                   wind=10, clock=3)
INPUT_KEYS = ('model', 'bc', 'w', 'mv', 'sight', 'zero', 'temp', 'alt', 'press', 'rh', 'wind', 'clock')


@pytest.fixture
def ready(page, app_url):
    page.goto(app_url)
    page.wait_for_function('typeof BAL !== "undefined"')
    return page


def solve(page, ranges, **p):
    q = dict(w=0, temp=59, alt=0, press=0, rh=0, wind=0, clock=3)
    q.update(p)
    q['ranges'] = ranges
    r = page.evaluate('p => BAL.solve(p)', q)
    assert 'error' not in r, r
    return r


def mil(inches, yd):
    """Angle in mil subtended by `inches` at `yd` yards."""
    return math.atan(inches / (yd * 36)) * 1000


# ---------- Physics without a source: the vacuum parabola and the step size ----------

def test_no_drag_is_the_textbook_parabola(ready):
    # bc 1e9 removes drag: drop below the bore line at time t is g*t*t/2
    r = solve(ready, bc=1e9, model='G7', mv=2600, sight=0, zero=100, ranges=[100, 500, 1000], wind=0)
    assert [row['yd'] for row in r['rows']] == [100, 500, 1000]
    t100 = 100 * 0.9144 / (2600 * FPS)
    for row in r['rows']:
        t = row['yd'] * 0.9144 / (2600 * FPS)
        assert row['tof'] == pytest.approx(t, rel=1e-4)
        # zeroed at 100 yd with no sight height: path at x is -(g/2)(t^2 - t*t100), in inches
        path = -(G / 2) * (t * t - t * t100) / 0.0254
        assert abs(row['dropIn'] - path) < 0.05, (row['yd'], row['dropIn'], path)


def test_halving_the_time_step_moves_nothing(ready):
    a = solve(ready, ranges=[300, 600, 1000], **DEFAULT_308)
    b = solve(ready, ranges=[300, 600, 1000], dt=0.0005, **DEFAULT_308)
    c = solve(ready, ranges=[300, 600, 1000], dt=0.004, **DEFAULT_308)
    for x, y in zip(a['rows'], b['rows']):
        assert abs(x['elevMil'] - y['elevMil']) < 0.01 and abs(x['windMil'] - y['windMil']) < 0.01
    # the option is really used: a step four times coarser changes the figures (a little)
    assert any(x['tof'] != z['tof'] for x, z in zip(a['rows'], c['rows']))


# ---------- Standard atmospheres ----------

# U.S. Standard Atmosphere (same as ICAO below 11 km), English units: Anderson, Introduction to Flight, Appendix E.
# (geometric altitude ft, temperature R, pressure lb/ft2, density slug/ft3)
STD_ATM = [(0, 518.69, 2116.2, 2.3769e-3), (5000, 500.86, 1760.9, 2.0482e-3), (10000, 483.04, 1455.6, 1.7556e-3)]
SLUG_FT3 = 515.3788   # kg/m3 per slug/ft3
PSF_PER_INHG = 70.7262


def test_air_density_matches_the_standard_atmosphere(ready):
    atm = lambda *a: ready.evaluate('a => BAL.atmosphere(...a)', list(a))
    # ICAO sea level, 59 F, 29.92 inHg, dry: 1.225 kg/m3, speed of sound 340.29 m/s (ballistics-engine constants.rs)
    icao = atm(59, 0, 29.92, 0)
    assert icao['rho'] == pytest.approx(1.225, rel=1e-3)
    assert icao['c'] == pytest.approx(340.29, abs=0.05)
    # Army Standard Metro, 59 F, 29.53 inHg, 78 %: 0.0751265 lb/ft3 (Dexadine Ballistic Explorer help)
    metro = atm(59, 0, 29.53, 78)
    assert metro['rho'] == pytest.approx(0.0751265 * 16.018463, rel=1e-3)


@pytest.mark.parametrize('row', STD_ATM, ids=[f'{r[0]}ft' for r in STD_ATM])
def test_air_density_at_altitude_matches_the_standard_atmosphere(ready, row):
    """Pressure left blank (0) is worked out from altitude; at the table's temperature, dry air, the density is the table's."""
    alt, t_rankine, p_psf, rho_slug = row
    a = ready.evaluate('a => BAL.atmosphere(...a)', [t_rankine - 459.67, alt, 0, 0])
    assert a['pIn'] == pytest.approx(p_psf / PSF_PER_INHG, rel=1e-3)
    assert a['rho'] == pytest.approx(rho_slug * SLUG_FT3, rel=1e-3)


# ---------- Drag tables ----------

def test_drag_tables_match_their_published_values(ready):
    """Every [Mach, Cd] pair of BAL.tables against the G1 and G7 tables printed by ballistics-engine (data/g1.csv,
    data/g7.csv; origin BRL / Lowry 1965 / McCoy, as its data README states)."""
    tables = ready.evaluate('BAL.tables')
    assert set(tables) == {'G1', 'G7'}
    for name in ('G1', 'G7'):
        ours = {m: cd for m, cd in tables[name]}
        published = {m: cd for m, cd in DRAG[name]}
        assert len(ours) == len(tables[name]), name          # no Mach number twice
        not_covered = sorted(set(ours) - set(published))     # pairs in BAL.tables that the source does not print
        missing = sorted(set(published) - set(ours))         # pairs the source prints that BAL.tables lacks
        assert not_covered == [] and missing == [], (name, not_covered, missing)
        wrong = [(m, ours[m], published[m]) for m in published if ours[m] != published[m]]
        assert wrong == [], (name, wrong)
        assert [m for m, _ in tables[name]] == sorted(ours), name
    # Applied Ballistics, ABDOC130 Custom Drag Models, a second source for one point each: at Mach 3 the G1 projectile has
    # a drag coefficient of 0.51, the G7 projectile only 0.24 (printed to two decimals).
    assert round(dict(map(tuple, tables['G1']))[3], 2) == 0.51 and round(dict(map(tuple, tables['G7']))[3], 2) == 0.24
    # The exported tables are the ones the solver flies: changing one changes the answer.
    before = solve(ready, ranges=[500], **DEFAULT_308)['rows'][0]['fps']
    ready.evaluate('BAL.tables.G7.forEach(r => { r[1] *= 2; })')
    after = solve(ready, ranges=[500], **DEFAULT_308)['rows'][0]['fps']
    assert after < before - 100


# ---------- Published trajectories ----------

def _supersonic(row, c_fps, solver_row):
    """Judged only while the bullet is above Mach 1.2 (by the source's own velocity where it gives one)."""
    v = row.get('fps', solver_row['fps'])
    return v / c_fps > 1.2


@pytest.mark.parametrize('case', JUDGED_CASES, ids=lambda c: c['id'])
def test_reference_trajectory(ready, case):
    # rows above Mach 1.2 only: elevation and wind as angles within 0.1 mil to 600 yd, 0.2 mil to 1000 yd; fps within 1 %
    p = {k: case[k] for k in INPUT_KEYS}
    rows = [row for row in case['rows'] if 0 < row['yd'] <= 1000]
    r = solve(ready, ranges=[row['yd'] for row in rows], **p)
    got = {row['yd']: row for row in r['rows']}
    c_fps = r['atm']['c'] / FPS
    judged = 0
    for ref in rows:
        s = got[ref['yd']]
        if not _supersonic(ref, c_fps, s):
            continue
        judged += 1
        yd = ref['yd']
        tol = 0.1 if yd <= 600 else 0.2
        if 'dropIn' in ref:
            assert abs(mil(-ref['dropIn'], yd) - s['elevMil']) <= tol, (yd, 'elevation', ref['dropIn'], s['dropIn'])
        if 'windIn' in ref:
            want = mil(-ref['windIn'], yd)
            have = s['windMil']
            if case.get('windBySize'):
                want, have = abs(want), abs(have)
            assert abs(want - have) <= tol, (yd, 'wind', ref['windIn'], s['windIn'])
        if 'fps' in ref:
            assert s['fps'] == pytest.approx(ref['fps'], rel=0.01), (yd, 'velocity')
    assert judged >= 3, 'too few rows above Mach 1.2 to judge this case'


def test_judged_cases_cover_what_the_check_needs():
    """Two independent sources; a .308 match load to 1,000 yd; a 5.56 load to 600 yd; a table that goes subsonic."""
    assert len({c['url'] for c in JUDGED_CASES}) >= 2
    assert {c['model'] for c in JUDGED_CASES} == {'G1', 'G7'}
    ids = {c['id']: c for c in JUDGED_CASES}
    assert max(r['yd'] for r in ids['zdziarski-308-175-smk']['rows']) == 1000
    assert max(r['yd'] for r in ids['steiner-3tr-556-m855']['rows']) >= 600
    assert min(r['fps'] for r in ids['steiner-3tr-556-m855']['rows']) < 1116  # below Mach 1 at 59 F


def test_every_case_records_where_it_came_from():
    for c in CASES:
        assert c['url'].startswith('https://') and c['opened'] == '2026-11-21' and c['source'], c['id']
        assert c['model'] in ('G1', 'G7') and isinstance(c['judged'], bool), c['id']
        assert all(set(r) <= {'yd', 'dropIn', 'windIn', 'fps', 'tof'} for r in c['rows']), c['id']
