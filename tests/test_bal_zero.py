"""Zero and close-range paths (src/bal-zero.js): the pure module behind the two Ballistics sheets. Decisions are in
docs/ballistics-rulings.md ("Release 2", Task 4)."""
import math

import pytest


@pytest.fixture
def ready(page, app_url):
    page.goto(app_url)
    page.wait_for_function('typeof BALZ !== "undefined" && typeof BAL !== "undefined" && !!FK._test.presets', timeout=10000)
    return page


# The built-in load p556m193 (src/bal-ui.js, PRESETS) in standard air: 59 F, altitude 0, pressure 0 (= from altitude),
# humidity 50, the screen's defaults. Read from the app so the test cannot drift from the preset.
LOAD_JS = """(over) => {
  const p = FK._test.presets().find(x => x.id === 'p556m193');
  return Object.assign({ bc: p.bc, model: p.model, w: p.w, mv: p.mv, sight: p.sight, zero: p.zero,
                         temp: 59, alt: 0, press: 0, rh: 50 }, over || {});
}"""


def load(page, **over):
    return page.evaluate(LOAD_JS, over)


def compare(page, zeros, **over):
    return page.evaluate(f'([zs, over]) => BALZ.compare(({LOAD_JS})(over), zs)', [zeros, over])


def solve(page, ranges, **over):
    return page.evaluate(f'([rs, over]) => BAL.solve(Object.assign(({LOAD_JS})(over), '
                         '{ wind: 0, clock: 12, angle: 0, ranges: rs }))', [ranges, over])


def finite(x):
    """True when no number anywhere inside x is NaN or infinite."""
    if isinstance(x, float):
        return math.isfinite(x)
    if isinstance(x, dict):
        return all(finite(v) for v in x.values())
    if isinstance(x, list):
        return all(finite(v) for v in x)
    return True


def test_the_constants_are_the_briefs(ready):
    c = ready.evaluate('({ close: BALZ.CLOSE, yds: BALZ.YDS, limit: BALZ.LIMIT })')
    assert c['close'] == [3, 5, 7, 10, 15, 25]
    assert c['yds'] == [5, 10, 15, 25, 36, 50, 75, 100, 125, 150, 175, 200, 225, 250, 275, 300]
    assert c['limit'] == 500


def test_close_rows_are_the_solver_rows(ready):
    got = ready.evaluate(f'BALZ.close(({LOAD_JS})())')
    want = solve(ready, [3, 5, 7, 10, 15, 25])['rows']
    assert [r['yd'] for r in got['rows']] == [3, 5, 7, 10, 15, 25]
    assert got['rows'] == [{'yd': r['yd'], 'dropIn': r['dropIn']} for r in want]
    assert finite(got)


def test_at_three_yards_the_bullet_is_nearly_a_sight_height_low(ready):
    r = ready.evaluate(f'BALZ.close(({LOAD_JS})())')['rows'][0]
    sight = load(ready)['sight']
    assert r['yd'] == 3
    assert -sight < r['dropIn'] < -sight * 0.9


def test_the_other_crossing_is_a_real_zero(ready):
    col = compare(ready, [36, 100])['cols'][0]
    assert col['zero'] == 36
    assert 200 <= col['other'] <= 400 and col['other'] == int(col['other'])
    # Zeroing at that other distance puts the bullet on the line of sight at 36 yd too.
    path = solve(ready, [36], zero=col['other'])['rows'][0]['dropIn']
    assert abs(path) < 0.15


def test_a_200_yard_zero_first_crosses_inside_100(ready):
    col = compare(ready, [200, 100])['cols'][0]
    assert 0 < col['other'] < 100
    # and that near crossing is a real zero as well
    assert abs(solve(ready, [200], zero=col['other'])['rows'][0]['dropIn']) < 0.15


def test_a_zero_that_is_itself_the_far_crossing(ready):
    near = compare(ready, [36, 100])['cols'][0]['other']          # about 250 yd: the far crossing of the 36 yd zero
    col = compare(ready, [near, 100])['cols'][0]
    assert abs(col['other'] - 36) <= 6                              # the near crossing is back at about 36 yd
    assert col['past'] is False
    assert col['peak'] is not None and col['other'] < col['peak']['yd'] < near


def test_peak_sits_between_the_two_crossings_and_is_positive(ready):
    for z in (36, 200):   # not 100: M193's 100 yd zero is nearly the apex zero (peak 0.06 in), too close to the 0.05 floor
        col = compare(ready, [z, 300])['cols'][0]
        lo, hi = sorted([z, col['other']])
        assert col['peak']['pathIn'] > 0.05
        assert lo < col['peak']['yd'] < hi
        assert col['peak']['yd'] == int(col['peak']['yd'])
    # the peak really is the highest sampled value
    path = [r['dropIn'] for r in solve(ready, list(range(1, 501)), zero=100)['rows']]
    top = compare(ready, [100, 200])['cols'][0]['peak']
    assert top['pathIn'] == pytest.approx(max(path), abs=1e-9)
    assert top['yd'] == path.index(max(path)) + 1


def test_a_zero_at_the_top_of_the_path_has_no_other_crossing_and_no_peak(ready):
    # Scan for the zero whose path just touches the line of sight at its highest point.
    z = ready.evaluate(f"""() => {{
      const L = ({LOAD_JS})();
      for (let z = 100; z <= 450; z += 0.5) {{
        const c = BALZ.compare(L, [z, z + 0.25]).cols[0];
        if (c.other === null && c.past === false && c.peak === null) return z;
      }}
      return null;
    }}""")
    assert z is not None
    col = compare(ready, [z, z + 100])['cols'][0]
    assert col['other'] is None and col['past'] is False and col['peak'] is None
    assert finite(col)


def test_a_value_within_five_thousandths_of_zero_has_no_sign(ready):
    # A path that wobbles +/-0.004 in about zero early on is noise, not three crossings: the near crossing is where the path
    # really changes sign (between 20 yd, below, and 26 yd, above), and the zero itself is the crossing at 400.
    got = ready.evaluate(f"""() => {{
      const real = BAL.solve;
      BAL.solve = () => ({{ rows: Array.from({{ length: 500 }}, (_, i) => {{
        const yd = i + 1;
        const dropIn = yd <= 20 ? -0.5 : yd <= 25 ? (yd % 2 ? 0.004 : -0.004) : yd <= 400 ? 0.5 : -0.5;
        return {{ yd, dropIn }};
      }}) }});
      try {{ return BALZ.compare(({LOAD_JS})(), [400, 100]).cols[0]; }} finally {{ BAL.solve = real; }}
    }}""")
    assert got['other'] == 23


def test_past_the_limit_is_reported_not_invented(ready):
    col = compare(ready, [10, 100])['cols'][0]
    assert load(ready)['sight'] == 2.6
    assert col['other'] is None and col['past'] is True
    assert col['peak'] is not None and col['peak']['pathIn'] > 0.05
    assert finite(col)


def test_bullet_that_stops_short_gives_what_it_has(ready):
    over = dict(bc=0.01, model='G1', mv=400)   # the brief's bc 0.05 with the preset's G7 never stops short: all 500 rows
    res = compare(ready, [25, 50], **over)
    assert 'error' not in res and finite(res)
    for col in res['cols']:
        rows = solve(ready, list(range(1, 501)), zero=col['zero'], **over)['rows']
        assert 0 < len(rows) < 300                                   # the premise: the solver gives fewer rows
        reach = {r['yd'] for r in rows}
        assert col['past'] is False
        for yd, v in zip(ready.evaluate('BALZ.YDS'), col['path']):
            assert (v is not None) == (yd in reach)


def test_path_lines_up_with_YDS_even_with_fewer_rows(ready):
    over = dict(bc=0.01, model='G1', mv=400)   # the brief's bc 0.05 with the preset's G7 never stops short: the solver gives all 500 rows
    yds = ready.evaluate('BALZ.YDS')
    direct = {r['yd']: r['dropIn'] for r in solve(ready, yds, zero=25, **over)['rows']}
    path = compare(ready, [25, 50], **over)['cols'][0]['path']
    assert len(path) == len(yds)
    assert any(v is None for v in path) and any(v is not None for v in path)
    for yd, v in zip(yds, path):
        if yd in direct:
            assert v == pytest.approx(direct[yd], abs=1e-9)
        else:
            assert v is None


def test_path_has_one_value_per_YDS_and_zero_at_its_own_row(ready):
    yds = ready.evaluate('BALZ.YDS')
    cols = compare(ready, [50, 100, 200])['cols']
    assert [c['zero'] for c in cols] == [50, 100, 200]
    for c in cols:
        assert len(c['path']) == len(yds) and all(isinstance(v, float) for v in c['path'])
    assert abs(cols[0]['path'][yds.index(50)]) < 0.01
    assert abs(cols[1]['path'][yds.index(100)]) < 0.01
    assert abs(cols[2]['path'][yds.index(200)]) < 0.01


@pytest.mark.parametrize('zeros', [[100], [], [1, 2, 3, 4], [100, 100], [0, 100], [-5, 100], ['x', 100], [None, 100],
                                   [float('nan'), 100], [float('inf'), 100], None, 'ab', [100, '200']])
def test_bad_zero_lists_are_an_error(ready, zeros):
    r = compare(ready, zeros)
    assert isinstance(r.get('error'), str) and r['error'] and 'cols' not in r


def test_solver_error_is_passed_through(ready):
    r = compare(ready, [36, 100], bc=0)
    assert r == {'error': solve(ready, [100], bc=0)['error']}
    c = ready.evaluate(f'BALZ.close(Object.assign(({LOAD_JS})(), {{ bc: 0 }}))')
    assert c == {'error': r['error']}


def test_compare_does_not_change_the_load(ready):
    same = ready.evaluate(f"""() => {{
      const L = ({LOAD_JS})(), before = JSON.stringify(L);
      BALZ.compare(L, [36, 100]); BALZ.close(L);
      return JSON.stringify(L) === before;
    }}""")
    assert same is True


@pytest.mark.parametrize('pid', ['p556m193', 'p308'])
def test_zeros_near_the_apex_zero_never_report_themselves_as_the_other_crossing(ready, pid):
    """Task 4 review: near the top of the path the zero's own crossing can slide by more than the 2 yd the near-crossing test allows.
    Sweep 15 yd either side of the apex zero in 1 yd steps: `other` is null or at least 5 yd from the zero, and a zero set at `other`
    puts the path back on the line of sight at the original zero."""
    got = ready.evaluate("""(pid) => {
      const p = FK._test.presets().find(x => x.id === pid);
      const L = { bc: p.bc, model: p.model, w: p.w, mv: p.mv, sight: p.sight, zero: p.zero, temp: 59, alt: 0, press: 0, rh: 50 };
      let apex = null;
      for (let z = 20; z <= 480 && apex === null; z += 0.5) {
        const c = BALZ.compare(L, [z, z + 0.25]).cols[0];
        if (c.other === null && c.past === false && c.peak === null) apex = z;
      }
      if (apex === null) return { apex };
      const out = [];
      for (let z = Math.max(10, Math.round(apex) - 15); z <= Math.round(apex) + 15; z++) {
        const c = BALZ.compare(L, [z, z + 1]).cols[0];
        let back = null;
        if (c.other !== null) {
          const s = BAL.solve(Object.assign({}, L, { zero: c.other, wind: 0, clock: 12, angle: 0, ranges: [z] }));
          back = s.rows[0].dropIn;
        }
        out.push({ z, other: c.other, back });
      }
      return { apex, out };
    }""", pid)
    assert got['apex'] is not None, pid
    assert len(got['out']) >= 30
    for r in got['out']:
        assert r['other'] is None or abs(r['other'] - r['z']) >= 5, (pid, r)
        assert r['back'] is None or abs(r['back']) <= 0.15, (pid, r)


def test_each_column_carries_the_last_whole_yard_the_solve_returned(ready):
    cols = compare(ready, [36, 100])['cols']
    assert [c['last'] for c in cols] == [500, 500]                    # the bullet reaches the limit
    over = dict(bc=0.01, model='G1', mv=400)
    for col in compare(ready, [25, 50], **over)['cols']:
        rows = solve(ready, list(range(1, 501)), zero=col['zero'], **over)['rows']
        assert col['last'] == rows[-1]['yd'] and col['last'] < 500
