"""BALS (src/bal-sight.js): one solved row plus a sight in, the words for the screen out. The sight never changes
the trajectory; these tests pin the wording, the rounding and the unit conversions."""
import math

import pytest

ROW = {'yd': 500, 'dropIn': -64.3, 'windIn': -21.9}
MIL_FORM = {'elev': {'main': 'U 3.6 mil', 'sub': ''}, 'wind': {'main': 'R 1.2 mil', 'sub': ''}}
BANNED = ('-0', 'NaN', 'Infinity', 'undefined', 'null')


@pytest.fixture
def ready(page, app_url):
    page.goto(app_url)
    page.wait_for_function('typeof BALS !== "undefined"')
    return page


def answer(page, row, sight):
    return page.evaluate('([r, s]) => BALS.answer(r, s)', [row, sight])


def cols(page, sight):
    return page.evaluate('s => BALS.cols(s)', sight)


def cells(page, row, sight):
    return page.evaluate('([r, s]) => BALS.cells(r, s)', [row, sight])


def clean(x):
    s = str(x)
    return not any(b in s for b in BANNED)


def test_turret_mil(ready):
    assert answer(ready, ROW, {'type': 'turret', 'unit': 'mil', 'click': 0.1}) == {
        'elev': {'main': 'U 3.6 mil', 'sub': '36 clicks'}, 'wind': {'main': 'R 1.2 mil', 'sub': '12 clicks'}}


def test_turret_true_moa_and_inches_per_100(ready):
    # the angle shown is what is dialled: clicks x click size (it read 'U 12.3 MOA' and 'U 12.9 in/100 yd', the exact need)
    assert answer(ready, ROW, {'type': 'turret', 'unit': 'moa', 'click': 0.25})['elev'] == {'main': 'U 12.25 MOA', 'sub': '49 clicks'}
    assert answer(ready, ROW, {'type': 'turret', 'unit': 'iphy', 'click': 0.25})['elev'] == {'main': 'U 12.75 in/100 yd', 'sub': '51 clicks'}


def test_turret_angle_is_the_dialled_value_with_decimals_to_suit_the_click(ready):
    got = lambda u, c, row=ROW: answer(ready, row, {'type': 'turret', 'unit': u, 'click': c})
    assert got('mil', 0.1)['elev'] == {'main': 'U 3.6 mil', 'sub': '36 clicks'}
    assert got('mil', 0.05)['elev'] == {'main': 'U 3.55 mil', 'sub': '71 clicks'}
    assert got('moa', 0.125)['elev'] == {'main': 'U 12.250 MOA', 'sub': '98 clicks'}
    assert got('moa', 0.5)['elev'] == {'main': 'U 12.5 MOA', 'sub': '25 clicks'}
    assert got('moa', 1)['elev'] == {'main': 'U 12.0 MOA', 'sub': '12 clicks'}
    assert got('moa', 0.25)['wind'] == {'main': 'R 4.25 MOA', 'sub': '17 clicks'}
    # one click is never shown as a zero angle without a direction (it read '0.0 mil / 1 click')
    assert got('mil', 0.05, {'yd': 100, 'dropIn': -0.108, 'windIn': 0})['elev'] == {'main': 'U 0.05 mil', 'sub': '1 click'}
    assert got('mil', 0.05, {'yd': 100, 'dropIn': 0.108, 'windIn': 0})['elev'] == {'main': 'D 0.05 mil', 'sub': '1 click'}
    # no clicks: zero in the click's decimals, no letter
    assert got('moa', 0.25, {'yd': 100, 'dropIn': -0.05, 'windIn': 0.05})['elev'] == {'main': '0.00 MOA', 'sub': '0 clicks'}
    assert got('moa', 0.125, {'yd': 100, 'dropIn': 0.05, 'windIn': 0})['elev'] == {'main': '0.000 MOA', 'sub': '0 clicks'}
    # the dope card's angle cells follow the same rule; every unit and no sight stay the true angle to one decimal
    assert cells(ready, ROW, {'type': 'turret', 'unit': 'moa', 'click': 0.25})['elev'][0] == 'U 12.25'
    assert cells(ready, ROW, {'type': 'turret', 'unit': 'mil', 'click': 0.05})['wind'][0] == 'R 1.20'
    assert answer(ready, ROW, None)['elev']['main'] == 'U 3.6 mil'
    assert ready.evaluate('r => BALS.all(r)', ROW)['elev'][1] == 'U 12.3 MOA'


def test_turret_one_click_is_singular(ready):
    r = {'yd': 100, 'dropIn': -0.36, 'windIn': 0}
    assert answer(ready, r, {'type': 'turret', 'unit': 'mil', 'click': 0.1})['elev']['sub'] == '1 click'


def test_reticle_nearest_mark_and_hold(ready):
    s = {'type': 'reticle', 'unit': 'mil', 'marks': [1.5, 3.0, 4.6, 6.3]}
    assert answer(ready, ROW, s)['elev'] == {'main': 'Mark 2', 'sub': 'hold 10 in high'}
    assert answer(ready, ROW, s)['wind'] == {'main': 'R 1.2 mil', 'sub': 'hold 22 in right'}     # a reticle's windage is a hold (it read '22 in')


def test_reticle_before_first_mark_and_past_last(ready):
    s = {'type': 'reticle', 'unit': 'mil', 'marks': [1.5, 3.0, 4.6, 6.3]}
    assert answer(ready, {'yd': 200, 'dropIn': -4.2, 'windIn': 0}, s)['elev'] == {'main': 'Centre', 'sub': 'hold 4.2 in high'}
    # past the last mark: a hold in the reticle's unit and in inches, never a dial reading (it read 'U 7.9 mil')
    assert answer(ready, {'yd': 800, 'dropIn': -227.9, 'windIn': 0}, s)['elev'] == {'main': 'Past last mark', 'sub': 'hold 7.9 mil (228 in) high'}
    moa = {'type': 'reticle', 'unit': 'moa', 'marks': [2, 4, 6]}
    assert answer(ready, {'yd': 800, 'dropIn': -226.4, 'windIn': 0}, moa)['elev'] == {'main': 'Past last mark', 'sub': 'hold 27.0 MOA (226 in) high'}
    assert answer(ready, {'yd': 400, 'dropIn': -20.5, 'windIn': -20.4}, moa)['wind'] == {'main': 'R 4.9 MOA', 'sub': 'hold 20 in right'}


def test_reticle_target_inside_the_zero(ready):   # bullet above the line of sight
    s = {'type': 'reticle', 'unit': 'mil', 'marks': [1.5, 3.0]}
    assert answer(ready, {'yd': 100, 'dropIn': 1.7, 'windIn': 0}, s)['elev'] == {'main': 'Centre', 'sub': 'hold 1.7 in low'}


def test_reticle_hold_under_half_inch_is_left_out(ready):
    s = {'type': 'reticle', 'unit': 'mil', 'marks': [1.5, 3.0]}
    # need 3.0 mil exactly at 100 yd = 10.8 in of drop: sits on mark 2
    assert answer(ready, {'yd': 100, 'dropIn': -10.8, 'windIn': 0}, s)['elev'] == {'main': 'Mark 2', 'sub': ''}


def test_reticle_one_mark_past_is_beyond_one_and_a_half_times(ready):
    s = {'type': 'reticle', 'unit': 'mil', 'marks': [2.0]}
    # 3.0 mil at 100 yd = 10.8 in: exactly 1.5 x the mark, still on the mark; 3.2 mil is past
    assert answer(ready, {'yd': 100, 'dropIn': -10.8, 'windIn': 0}, s)['elev']['main'] == 'Mark 1'
    assert answer(ready, {'yd': 100, 'dropIn': -11.6, 'windIn': 0}, s)['elev']['main'] == 'Past last mark'


def test_reticle_in_moa(ready):
    s = {'type': 'reticle', 'unit': 'moa', 'marks': [4.0, 8.0, 12.0]}
    a = answer(ready, ROW, s)
    assert a['elev']['main'] == 'Mark 3'            # 12.28 MOA against 12.0
    assert a['wind']['main'] == 'R 4.2 MOA'


def test_dot(ready):
    assert answer(ready, ROW, {'type': 'dot'}) == {
        'elev': {'main': 'Hold 64 in high', 'sub': ''}, 'wind': {'main': 'Hold 22 in right', 'sub': ''}}
    assert answer(ready, {'yd': 7, 'dropIn': -2.3, 'windIn': 0}, {'type': 'dot'})['elev']['main'] == 'Hold 2.3 in high'
    assert answer(ready, {'yd': 100, 'dropIn': -0.02, 'windIn': 0.01}, {'type': 'dot'}) == {
        'elev': {'main': 'Hold on', 'sub': ''}, 'wind': {'main': 'No hold', 'sub': ''}}


def test_dot_low_and_left(ready):
    a = answer(ready, {'yd': 100, 'dropIn': 3.4, 'windIn': 12.6}, {'type': 'dot'})
    assert a == {'elev': {'main': 'Hold 3.4 in low', 'sub': ''}, 'wind': {'main': 'Hold 13 in left', 'sub': ''}}


def test_all_units(ready):
    assert ready.evaluate('r => BALS.all(r)', ROW) == {
        'elev': ['U 3.6 mil', 'U 12.3 MOA', 'Hold 64 in high'], 'wind': ['R 1.2 mil', 'R 4.2 MOA', 'Hold 22 in right']}


def test_rounding_edges(ready):
    t = {'type': 'turret', 'unit': 'mil', 'click': 0.1}
    assert answer(ready, {'yd': 100, 'dropIn': -0.14, 'windIn': 0}, t)['elev'] == {'main': '0.0 mil', 'sub': '0 clicks'}   # 0.04 mil
    assert answer(ready, {'yd': 100, 'dropIn': -0.56, 'windIn': 0}, t)['elev'] == {'main': 'U 0.2 mil', 'sub': '2 clicks'}   # 0.156 mil: past half a click rounds up


def test_inches_switch_from_one_decimal_to_whole_at_ten(ready):
    d = {'type': 'dot'}
    assert answer(ready, {'yd': 100, 'dropIn': -9.94, 'windIn': 0}, d)['elev']['main'] == 'Hold 9.9 in high'
    assert answer(ready, {'yd': 100, 'dropIn': -9.96, 'windIn': 0}, d)['elev']['main'] == 'Hold 10 in high'
    assert answer(ready, {'yd': 100, 'dropIn': -10.4, 'windIn': 0}, d)['elev']['main'] == 'Hold 10 in high'


def test_bad_input_gives_dashes(ready):
    for row in [{'yd': 0, 'dropIn': -1, 'windIn': 0}, {'yd': 500, 'dropIn': None, 'windIn': 0}]:
        a = answer(ready, row, {'type': 'turret', 'unit': 'mil', 'click': 0.1})
        assert a['elev']['main'] == '—' and 'NaN' not in str(a)


def test_bad_rows_are_dashes_everywhere(ready):
    for row in [{'yd': 0, 'dropIn': -1, 'windIn': 0}, {'yd': 500, 'dropIn': None, 'windIn': 0},
                {'yd': 500, 'dropIn': -1}, {'yd': 500, 'dropIn': -1, 'windIn': float('inf')}, None]:
        for s in [None, {'type': 'dot'}, {'type': 'turret', 'unit': 'moa', 'click': 0.25},
                  {'type': 'reticle', 'unit': 'mil', 'marks': [1, 2]}]:
            a = answer(ready, row, s)
            assert a['elev']['main'] == '—' and a['wind']['main'] == '—' and clean(a), (row, s, a)
            c = cells(ready, row, s)
            assert all(x == '—' for x in c['elev'] + c['wind']), (row, s, c)
            assert [len(c['elev']), len(c['wind'])] == [len(cols(ready, s)['elev']), len(cols(ready, s)['wind'])]
        assert all(x == '—' for x in ready.evaluate('r => BALS.all(r)', row)['elev'])


@pytest.mark.parametrize('sight', [
    {'type': 'scope'}, {'type': 'turret', 'unit': 'furlong', 'click': 0.1}, {'type': 'turret', 'unit': 'mil'},
    {'type': 'turret', 'unit': 'mil', 'click': 0}, {'type': 'turret', 'unit': 'mil', 'click': -0.1},
    {'type': 'reticle', 'unit': 'mil', 'marks': []}, {'type': 'reticle', 'unit': 'mil'},
    {'type': 'reticle', 'unit': 'bogus', 'marks': [1]}, {}, 'turret', 5,
    {'type': 'turret', 'unit': 'constructor', 'click': 0.1}, {'type': 'turret', 'unit': 'toString', 'click': 0.1},
    {'type': 'reticle', 'unit': 'valueOf', 'marks': [1]}, {'type': 'turret', 'unit': '__proto__', 'click': 0.1},
])
def test_malformed_sight_is_no_sight(ready, sight):
    assert answer(ready, ROW, sight) == MIL_FORM
    assert cells(ready, ROW, sight) == cells(ready, ROW, None)
    assert cols(ready, sight) == cols(ready, None)


def test_never_minus_zero_or_nan(ready):
    sights = [None, {'type': 'dot'}, {'type': 'turret', 'unit': 'mil', 'click': 0.1},
              {'type': 'reticle', 'unit': 'moa', 'marks': [2, 4]}]
    for yd, d, w in [(100, 0.001, -0.001), (100, -0.001, 0.001), (100, 0, 0), (300, 0.04, -0.04), (1, -1e-9, 1e-9)]:
        row = {'yd': yd, 'dropIn': d, 'windIn': w}
        for s in sights:
            assert clean(answer(ready, row, s)) and clean(cells(ready, row, s))
        assert clean(ready.evaluate('r => BALS.all(r)', row))


def test_no_sight_is_the_mil_form_with_a_moa_cell(ready):
    assert answer(ready, ROW, None) == MIL_FORM


# ---------- dope-card columns and cells ----------

def test_cols_and_cells_turret(ready):
    t = {'type': 'turret', 'unit': 'mil', 'click': 0.1}
    # headings say elevation or wind, and click cells carry the direction (they read 'Clicks' and '36')
    assert cols(ready, t) == {'elev': ['Elev mil', 'Elev clicks'], 'wind': ['Wind mil', 'Wind clicks']}
    assert cells(ready, ROW, t) == {'elev': ['U 3.6', 'U 36'], 'wind': ['R 1.2', 'R 12']}
    assert cells(ready, {'yd': 100, 'dropIn': 0.1, 'windIn': -0.1}, t) == {'elev': ['0.0', '0'], 'wind': ['0.0', '0']}
    assert cells(ready, {'yd': 300, 'dropIn': 2, 'windIn': 2}, t) == {'elev': ['D 0.2', 'D 2'], 'wind': ['L 0.2', 'L 2']}
    assert cols(ready, {**t, 'unit': 'moa'})['elev'] == ['Elev MOA', 'Elev clicks']
    assert cols(ready, {**t, 'unit': 'iphy'})['wind'] == ['Wind in/100 yd', 'Wind clicks']


def test_cols_and_cells_reticle(ready):
    s = {'type': 'reticle', 'unit': 'mil', 'marks': [1.5, 3.0, 4.6, 6.3]}
    assert cols(ready, s) == {'elev': ['Mark', 'Elev hold in'], 'wind': ['Wind mil', 'Wind hold in']}
    assert cells(ready, ROW, s) == {'elev': ['2', '10 high'], 'wind': ['R 1.2', '22 right']}
    assert cells(ready, {'yd': 200, 'dropIn': -4.2, 'windIn': 0}, s)['elev'] == ['C', '4.2 high']
    assert cells(ready, {'yd': 100, 'dropIn': 1.7, 'windIn': 0}, s)['elev'] == ['C', '1.7 low']
    assert cells(ready, {'yd': 800, 'dropIn': -227.9, 'windIn': 0}, s)['elev'] == ['Past', '228 high']     # inches, as its heading says
    assert cells(ready, {'yd': 100, 'dropIn': -10.8, 'windIn': 0}, s)['elev'] == ['2', '']


def test_cols_and_cells_dot(ready):
    assert cols(ready, {'type': 'dot'}) == {'elev': ['Elev hold in'], 'wind': ['Wind hold in']}
    assert cells(ready, ROW, {'type': 'dot'}) == {'elev': ['64 high'], 'wind': ['22 right']}
    assert cells(ready, {'yd': 100, 'dropIn': -0.02, 'windIn': 0.01}, {'type': 'dot'}) == {'elev': ['0'], 'wind': ['0']}


def test_cols_and_cells_no_sight(ready):
    assert cols(ready, None) == {'elev': ['Elev mil', 'Elev MOA'], 'wind': ['Wind mil', 'Wind MOA']}
    assert cells(ready, ROW, None) == {'elev': ['U 3.6', 'U 12.3'], 'wind': ['R 1.2', 'R 4.2']}


# ---------- typed elevation to radians ----------

def test_to_angle_every_unit_gives_the_same_angle(ready):
    want = math.atan(64.3 / 18000)
    for v, u in [(3.572, 'mil'), (12.28, 'moa'), (12.86, 'iphy'), (64.3, 'in')]:
        got = ready.evaluate('([v, u]) => BALS.toAngle(v, u, 500)', [v, u])
        assert abs(got - want) < 1e-5, (v, u, got, want)


def test_to_angle_bad_input_is_nan(ready):
    for args in [[None, 'mil', 500], ['', 'mil', 500], ['x', 'mil', 500], [float('inf'), 'mil', 500],
                 [1, 'furlong', 500], [1, 'constructor', 500], [1, 'toString', 500], [1, 'valueOf', 500], [1, 'in', 0], [1, 'in', None], [1, None, 500]]:
        assert ready.evaluate('a => Number.isNaN(BALS.toAngle(a[0], a[1], a[2]))', args), args
    assert ready.evaluate('Number.isNaN(BALS.toAngle(undefined, "mil", 500))')


def test_reticle_wind_drift_under_a_twentieth_inch_matches_the_cell(ready):
    s = {'type': 'reticle', 'unit': 'mil', 'marks': [1.5, 3.0]}
    r = {'yd': 100, 'dropIn': -4.2, 'windIn': -0.03}
    assert answer(ready, r, s)['wind']['sub'] == 'No hold'
    assert cells(ready, r, s)['wind'][1] == '0'


# ---------- The lines under the profile picker ----------

def describe(page, sight):
    return page.evaluate('s => BALS.describe(s)', sight)


def test_describe_turrets_and_their_clicks(ready):
    got = {(u, c): describe(ready, {'type': 'turret', 'unit': u, 'click': c})
           for u, c in [('mil', 0.1), ('mil', 0.05), ('moa', 0.25), ('moa', 0.125), ('moa', 0.5), ('moa', 1), ('iphy', 0.25), ('iphy', 0.125), ('iphy', 0.5), ('iphy', 1)]}
    assert got[('mil', 0.1)] == 'Mil turrets, 0.1 mil clicks'
    assert got[('mil', 0.05)] == 'Mil turrets, 0.05 mil clicks'
    assert got[('moa', 0.25)] == 'MOA turrets, 1/4 MOA clicks'
    assert got[('moa', 0.125)] == 'MOA turrets, 1/8 MOA clicks'
    assert got[('moa', 0.5)] == 'MOA turrets, 1/2 MOA clicks'
    assert got[('moa', 1)] == 'MOA turrets, 1 MOA clicks'
    assert got[('iphy', 0.25)] == 'Turrets in inches per 100 yd, 1/4 in clicks'
    assert got[('iphy', 1)] == 'Turrets in inches per 100 yd, 1 in clicks'
    assert describe(ready, {'type': 'turret', 'unit': 'mil', 'click': 0.25}) == 'Mil turrets, 0.25 mil clicks'


def test_describe_reticles_dots_and_no_sight(ready):
    assert describe(ready, {'type': 'reticle', 'unit': 'mil', 'marks': [1.5, 3, 4.6, 6.3]}) == 'Drop reticle, 4 marks in mil'
    assert describe(ready, {'type': 'reticle', 'unit': 'moa', 'marks': [2, 4]}) == 'Drop reticle, 2 marks in MOA'
    assert describe(ready, {'type': 'reticle', 'unit': 'iphy', 'marks': [5]}) == 'Drop reticle, 1 mark in inches per 100 yd'
    assert describe(ready, {'type': 'dot'}) == 'Red dot or iron sights'
    for none in (None, {}, 'x', {'type': 'turret', 'unit': 'mil'}, {'type': 'reticle', 'unit': 'mil', 'marks': []}):
        assert describe(ready, none) == 'No sight set: showing every unit'


def test_zero_line(ready):
    line = lambda a: ready.evaluate('a => BALS.zeroLine(a)', a)
    assert line({'temp': 90, 'alt': 400, 'rh': 50}) == 'Zeroed at 90°F, 400 ft'
    assert line({'temp': 90, 'alt': 400, 'press': 29.5, 'rh': 50}) == 'Zeroed at 90°F, 29.50 inHg'
    assert line({'temp': 41.5, 'alt': -50}) == 'Zeroed at 41.5°F, -50 ft'
    for bad in (None, {}, {'temp': 90}, {'alt': 3}, 'x'):
        assert line(bad) == ''


# ---------- The sentence under the card and the load line ----------

def test_path_says_high_or_low_and_drift_says_which_way(ready):
    path = lambda row: ready.evaluate('r => BALS.path(r)', row)
    assert path({'yd': 500, 'dropIn': -63.62, 'windIn': -21.2}) == '63.6 in low, drift 21.2 in left'
    assert path({'yd': 100, 'dropIn': 1.7, 'windIn': 0.66}) == '1.7 in high, drift 0.7 in right'
    assert path({'yd': 100, 'dropIn': -0.02, 'windIn': 0.04}) == 'on the line of sight, drift 0.0 in'
    assert path({'yd': 100, 'dropIn': None, 'windIn': 0}) == ''


def test_load_line(ready):
    line = lambda p: ready.evaluate('p => BALS.loadLine(p)', p)
    assert line({'bc': 0.25, 'model': 'G7', 'w': 175, 'mv': 2600, 'zero': 100}) == '175 gr · G7 0.25 · 2,600 fps · zero 100 yd'
    assert line({'bc': 0.3, 'model': 'G1', 'w': 0, 'mv': 950, 'zero': 36.5}) == 'G1 0.3 · 950 fps · zero 36.5 yd'
    assert line({'bc': 0.3, 'mv': 2800}) == 'G7 0.3 · 2,800 fps'
    assert line(None) == '' and clean(line({'bc': float('nan'), 'mv': 'x', 'zero': None}))


def test_path_without_spinIn_is_unchanged(ready):
    path = lambda row: ready.evaluate('r => BALS.path(r)', row)
    base = {'yd': 500, 'dropIn': -63.62, 'windIn': -21.2}
    for extra in ({}, {'spinIn': None}, {'spinIn': float('nan')}, {'spinIn': 'x'}):
        assert path({**base, **extra}) == '63.6 in low, drift 21.2 in left'
    assert ready.evaluate('r => BALS.path(r)', {**base, 'spinIn': None}) == '63.6 in low, drift 21.2 in left'
    assert ready.evaluate('r => BALS.path({ ...r, spinIn: Infinity })', base) == '63.6 in low, drift 21.2 in left'


def test_path_names_the_spin_share_and_its_side(ready):
    path = lambda row: ready.evaluate('r => BALS.path(r)', row)
    assert path({'yd': 500, 'dropIn': -63.62, 'windIn': -21.2, 'spinIn': 5.24}) == '63.6 in low, drift 21.2 in left (spin drift 5.2 in right included)'
    assert path({'yd': 500, 'dropIn': -63.62, 'windIn': 5.2, 'spinIn': -3.04}) == '63.6 in low, drift 5.2 in right (spin drift 3.0 in left included)'


def test_path_drops_a_spin_share_that_rounds_to_zero(ready):
    path = lambda row: ready.evaluate('r => BALS.path(r)', row)
    for spin in (0, 0.04, -0.04, -0):
        assert path({'yd': 100, 'dropIn': 1.7, 'windIn': 0.66, 'spinIn': spin}) == '1.7 in high, drift 0.7 in right', spin
    assert path({'yd': 100, 'dropIn': 1.7, 'windIn': 0.66, 'spinIn': 0.05}).endswith('(spin drift 0.1 in right included)')
