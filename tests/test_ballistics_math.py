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


# ---------- The built-in loads: each number comes from a page that was opened ----------

# Copied from docs/content-review.md ("Built-in loads"). Coefficient and drag model, and velocity with its barrel length, from
# the maker's page for the cartridge the name gives; sight height and zero are the app's own starting values, not sourced.
SOURCED = [
    {'id': 'p556m193', 'name': 'Sellier & Bellot 5.56×45 M193 55 gr FMJ, 23.5″ barrel', 'bc': 0.127, 'model': 'G7', 'w': 55,
     'mv': 3301, 'sight': 2.6, 'zero': 100},
    {'id': 'p556ss109', 'name': 'RWS 5.56x45 NATO Ball SS109 62 gr, 20″ barrel', 'bc': 0.151, 'model': 'G7', 'w': 62,
     'mv': 3035, 'sight': 2.6, 'zero': 100},
    {'id': 'p223', 'name': 'Federal Gold Medal .223 Rem 77 gr SMK, 24″ barrel', 'bc': 0.188, 'model': 'G7', 'w': 77, 'mv': 2720,
     'sight': 2.6, 'zero': 100},
    {'id': 'p76239sb', 'name': 'Sellier & Bellot 7.62×39 124 gr FMJ, 20.5″ barrel', 'bc': 0.286, 'model': 'G1', 'w': 124,
     'mv': 2421, 'sight': 2.0, 'zero': 100},
    {'id': 'p65cm', 'name': 'Hornady 6.5 Creedmoor 140 gr ELD-M, 24″ barrel', 'bc': 0.326, 'model': 'G7', 'w': 140, 'mv': 2710,
     'sight': 1.5, 'zero': 100},
    {'id': 'p308', 'name': 'Federal Gold Medal .308 Win 175 gr SMK, 24″ barrel', 'bc': 0.25, 'model': 'G7', 'w': 175, 'mv': 2600,
     'sight': 1.5, 'zero': 100},
]
REMOVED_IDS = ['p556', 'p76239']   # ids retired, never reused (their numbers had no source): see docs/ballistics-rulings.md


def test_built_in_loads_are_the_sourced_values(ready):
    assert ready.evaluate('FK._test.presets()') == SOURCED


def test_every_built_in_load_names_its_barrel_length(ready):
    for p in ready.evaluate('FK._test.presets()'):
        assert '″ barrel' in p['name'], p['name']


def test_a_removed_load_is_not_offered_and_its_id_is_not_reused(ready):
    ids = [p['id'] for p in ready.evaluate('FK._test.presets()')]
    assert not set(REMOVED_IDS) & set(ids)
    assert len(ids) == len(set(ids))


# ---------- Zero conditions: the zero angle is found in the air the rifle was zeroed in ----------

def test_zero_conditions_same_as_today_change_nothing(ready):
    same = dict(temp=59, alt=0, press=0, rh=50)
    assert solve(ready, **DEFAULT_308, ranges=[600], zeroAtm=same)['rows'] == solve(ready, **DEFAULT_308, ranges=[600])['rows']


def test_zeroed_warm_shot_cold_needs_more_elevation(ready):
    cold = {**DEFAULT_308, 'temp': 10}
    warm_zero = solve(ready, **cold, ranges=[100, 600], zeroAtm=dict(temp=90, alt=0, press=0, rh=50))['rows']
    same_air = solve(ready, **cold, ranges=[100, 600])['rows']
    assert warm_zero[1]['elevMil'] > same_air[1]['elevMil']
    assert abs(same_air[0]['elevMil']) < 0.005 and abs(warm_zero[0]['elevMil']) < 0.1


def test_zero_conditions_absent_or_incomplete_mean_today(ready):
    base = solve(ready, **DEFAULT_308, ranges=[600])['rows']
    for za in [None, dict(temp=None, alt=0, press=0, rh=50), dict(temp=90, alt=0, press=0)]:
        assert solve(ready, **DEFAULT_308, ranges=[600], zeroAtm=za)['rows'] == base


# ---------- Correcting the velocity from one real shot (BAL.trueMv) ----------

def true_mv(page, p, yd, angle):
    return page.evaluate('([p, yd, a]) => BAL.trueMv(p, yd, a)', [p, yd, angle])


def need_angle(page, yd, **kw):
    seen = solve(page, **{**DEFAULT_308, **kw}, ranges=[yd])['rows'][0]
    return math.atan(-seen['dropIn'] / (yd * 36))


def test_true_recovers_a_known_velocity(ready):
    for real in (2550, 2600, 2680):
        got = true_mv(ready, DEFAULT_308, 600, need_angle(ready, 600, mv=real))
        assert 'error' not in got, got
        assert abs(got['mv'] - real) <= 2
        assert got['mv'] == int(got['mv'])
        assert got['change'] == pytest.approx((got['mv'] - 2600) / 2600)


def test_true_ignores_the_wind_and_incline_p_carries(ready):
    flat = true_mv(ready, DEFAULT_308, 600, need_angle(ready, 600, mv=2560, wind=0))
    windy = true_mv(ready, {**DEFAULT_308, 'wind': 25, 'clock': 9, 'angle': 30}, 600, need_angle(ready, 600, mv=2560, wind=0))
    assert flat['mv'] == windy['mv'] and abs(flat['mv'] - 2560) <= 2


def test_true_refusals(ready):
    assert true_mv(ready, DEFAULT_308, 250, 0.001) == {'error': 'near'}
    assert true_mv(ready, DEFAULT_308, 299.9, 0.001) == {'error': 'near'}
    assert true_mv(ready, DEFAULT_308, 1100, need_angle(ready, 1100)) == {'error': 'slow'}
    assert true_mv(ready, DEFAULT_308, 600, 2 * need_angle(ready, 600)) == {'error': 'far'}
    # more than 15% off is refused even where some velocity in the search range comes close
    assert true_mv(ready, DEFAULT_308, 600, need_angle(ready, 600, mv=2150)) == {'error': 'far'}


def test_true_warns_past_five_percent(ready):
    got = true_mv(ready, DEFAULT_308, 600, need_angle(ready, 600, mv=2450))
    assert got['warn'] is True and abs(got['mv'] - 2450) <= 2 and got['change'] < -0.05
    quiet = true_mv(ready, DEFAULT_308, 600, need_angle(ready, 600, mv=2550))
    assert 'warn' not in quiet or quiet['warn'] is False


def test_true_bad_input(ready):
    bad = {'error': 'bad'}
    for yd, ang in [(None, 0.01), (0, 0.01), (-600, 0.01), (600, None), (600, 0), (600, -0.01), ('x', 0.01)]:
        assert true_mv(ready, DEFAULT_308, yd, ang) == bad, (yd, ang)
    assert true_mv(ready, {**DEFAULT_308, 'mv': 0}, 600, 0.01) == bad
    assert true_mv(ready, {**DEFAULT_308, 'mv': None}, 600, 0.01) == bad


def test_true_uses_the_zero_conditions(ready):
    cold = {'temp': -20, 'alt': 9000, 'press': 0, 'rh': 50}
    p = {**DEFAULT_308, 'zero': 500, 'zeroAtm': cold}
    angle = math.atan(-solve(ready, **p, ranges=[700])['rows'][0]['dropIn'] / (700 * 36))
    got = true_mv(ready, p, 700, angle)
    assert abs(got['mv'] - 2600) <= 1
    other = true_mv(ready, {**p, 'zeroAtm': None}, 700, angle)     # the same shot read without the zero air gives another velocity
    assert abs(other['mv'] - 2600) > 3


def test_true_fifteen_percent_boundary(ready):
    for real, fine in [(2213, True), (2207, False), (2987, True), (2993, False)]:   # -14.9 %, -15.1 %, +14.9 %, +15.1 % of 2600
        got = true_mv(ready, DEFAULT_308, 600, need_angle(ready, 600, mv=real))
        if fine:
            assert got.get('warn') is True and abs(got['mv'] - real) <= 2, (real, got)
        else:
            assert got == {'error': 'far'}, (real, got)


def test_need_falls_as_velocity_rises_for_every_built_in_load(ready):
    """Bisection in trueMv needs the angle to fall strictly as velocity rises, wherever it can be asked."""
    bad = ready.evaluate("""() => {
      const bad = [], seen = [];
      for (const l of FK._test.presets()) for (const yd of [300, 500, 800]) {
        const base = { bc: l.bc, model: l.model, w: l.w, sight: l.sight, zero: l.zero, temp: 59, alt: 0, press: 0, rh: 50, wind: 0, clock: 12, ranges: [yd] };
        const at = k => { const r = BAL.solve({ ...base, mv: l.mv * k }).rows[0]; return { need: Math.atan(-r.dropIn / (yd * 36)), mach: r.mach }; };
        if (at(1).mach < 1.2) continue;
        const ks = [0.85, 0.925, 1, 1.075, 1.15].map(k => at(k).need);
        seen.push(l.id + yd);
        if (!ks.every((v, i) => i === 0 || v < ks[i - 1])) bad.push([l.id, yd, ks]);
      }
      return { bad, n: seen.length }; }""")
    assert ready.evaluate('FK._test.presets().length') == 6
    assert bad['n'] >= 6 and bad['bad'] == []
