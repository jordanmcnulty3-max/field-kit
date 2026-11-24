"""Spin drift and gyroscopic stability (src/bal-spin.js) checked against the published formulas and worked examples.
Sources are recorded in docs/content-review.md ("Ballistics") and tests/fixtures/spin_reference.json; decisions are in
docs/ballistics-rulings.md ("Release 2")."""
import json
import math
import os

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, 'fixtures', 'spin_reference.json')) as f:
    REF = json.load(f)

CASE = dict(w=175, dia=0.308, len=1.24, twist=10, mv=2600, temp=59, press=29.92)


def miller(c):
    """Courtney & Miller equation 1, written out here and not copied from the app."""
    t, L = c['twist'] / c['dia'], c['len'] / c['dia']
    return (30 * c['w'] / (t ** 2 * c['dia'] ** 3 * L * (1 + L * L))
            * (c['mv'] / 2800) ** (1 / 3) * (c['temp'] + 460) / (59 + 460) * 29.92 / c['press'])


@pytest.fixture
def ready(page, app_url):
    page.goto(app_url)
    page.wait_for_function('typeof BSPIN !== "undefined"')
    return page


@pytest.fixture
def ref():
    return REF


def js_stability(page, c):
    return page.evaluate('c => BSPIN.stability(c)', c)


def js_drift(page, sg, tof):
    return page.evaluate('([a, b]) => BSPIN.drift(a, b)', [sg, tof])


def test_stability_matches_every_source_example(ready, ref):
    for ex in ref['stability']['examples']:
        assert js_stability(ready, ex) == pytest.approx(ex['sg'], abs=0.01)


def test_stability_matches_the_formula_written_out_in_python(ready):
    # 175 gr, .308, 1.24 in, 1:10, 2600 fps, 59 F, 29.92 inHg; expected computed here, not copied from the app
    assert js_stability(ready, CASE) == pytest.approx(miller(CASE), rel=1e-9)
    odd = dict(CASE, w=62, dia=0.224, len=0.9, twist=7, mv=3000, temp=20, press=27.5)
    assert js_stability(ready, odd) == pytest.approx(miller(odd), rel=1e-9)


def test_colder_denser_air_lowers_stability(ready):
    sg = lambda **k: js_stability(ready, dict(CASE, **k))
    assert sg(temp=0) < sg(temp=59) < sg(temp=100)
    assert sg(press=29.92) < sg(press=25.0)


def test_stability_is_nan_for_bad_input(ready):
    for key in ('w', 'dia', 'len', 'twist', 'mv', 'press'):
        for bad in (0, -1, None, 'x', '8', 'Infinity'):
            value = float('inf') if bad == 'Infinity' else bad
            r = ready.evaluate('([k, v]) => BSPIN.stability(Object.assign({}, %s, { [k]: v }))' % json.dumps(CASE), [key, value])
            assert r is None or (isinstance(r, float) and math.isnan(r)), (key, bad, r)
    # temperature: any finite number, zero and below included; but not a missing or non-number one
    assert js_stability(ready, dict(CASE, temp=-40)) > 0
    assert js_stability(ready, dict(CASE, temp=0)) > 0
    assert ready.evaluate('c => Number.isNaN(BSPIN.stability(Object.assign({}, c, { temp: "59" })))', CASE)
    assert ready.evaluate('c => Number.isNaN(BSPIN.stability(Object.assign({}, c, { temp: null })))', CASE)


def test_drift_matches_every_source_example(ready, ref):
    for ex in ref['drift']['examples']:
        assert js_drift(ready, ex['sg'], ex['tof']) == pytest.approx(ex['inches'], abs=0.05)


def test_drift_is_never_negative_and_is_nan_for_bad_input(ready):
    assert js_drift(ready, 1.5, 1.0) > 0
    for bad in (0, -1, 'x', '2'):
        assert ready.evaluate('([a, b]) => Number.isNaN(BSPIN.drift(a, b))', [bad, 1.0]), bad
        assert ready.evaluate('([a, b]) => Number.isNaN(BSPIN.drift(a, b))', [1.5, bad]), bad
    for js in ('BSPIN.drift(null, 1)', 'BSPIN.drift(1.5, null)', 'BSPIN.drift(Infinity, 1)', 'BSPIN.drift(1.5, Infinity)',
               'BSPIN.drift(NaN, 1)', 'BSPIN.drift()'):
        assert ready.evaluate('Number.isNaN(%s)' % js), js
    for sg in (0.5, 1.0, 3.0):
        assert ready.evaluate('([a]) => BSPIN.drift(a, 0.5) >= 0', [sg])


def test_grade_uses_the_source_thresholds(ready, ref):
    s = ref['stability']
    grade = lambda sg: ready.evaluate('sg => BSPIN.grade(sg)', sg)
    lo, hi = s['unstableBelow'], s['marginalBelow']
    assert grade(lo - 0.001) == 'unstable'
    assert grade(lo) == 'marginal'
    assert grade(hi - 0.001) == 'marginal'
    assert grade(hi) == 'stable'
    assert grade(2.5) == 'stable'
    assert grade(float('nan')) == 'unstable'


GOOD = dict(w=175, mv=2600, twist=10, twistDir='R', blen=1.24, bdia=0.308)
AIR = dict(temp=59, press=29.92)


def js_of(page, profile, air=AIR):
    return page.evaluate('([p, a]) => BSPIN.of(p, a)', [profile, air])


def test_of_returns_sg_grade_and_sign(ready):
    r = js_of(ready, GOOD)
    assert r['sg'] == pytest.approx(miller(dict(CASE)), rel=1e-9)
    assert r['grade'] in ('unstable', 'marginal', 'stable')
    assert r['sign'] == 1


def test_of_lists_what_is_missing_in_order(ready):
    assert js_of(ready, {'mv': 2600}) == {'missing': ['twist', 'bullet length', 'bullet diameter', 'bullet weight']}
    assert js_of(ready, {'mv': 2600, 'twist': 10}) == {'missing': ['bullet length', 'bullet diameter', 'bullet weight']}
    assert js_of(ready, dict(GOOD, blen=0, w=None)) == {'missing': ['bullet length', 'bullet weight']}


def test_of_left_twist_is_minus_one(ready):
    assert js_of(ready, dict(GOOD, twistDir='L'))['sign'] == -1
    assert js_of(ready, dict(GOOD, twistDir='R'))['sign'] == 1
    assert js_of(ready, {k: v for k, v in GOOD.items() if k != 'twistDir'})['sign'] == 1


def test_of_ignores_strings_and_negatives(ready):
    r = js_of(ready, dict(GOOD, twist='8', blen=-1))
    assert r == {'missing': ['twist', 'bullet length']}


def test_of_without_a_usable_muzzle_velocity_is_missing_it(ready):
    # after the four named items, in the same order rule; the list is the whole answer (no sg, no grade)
    assert js_of(ready, dict(GOOD, mv=None)) == {'missing': ['muzzle velocity']}
    assert js_of(ready, dict(GOOD, mv=0)) == {'missing': ['muzzle velocity']}
    assert js_of(ready, dict(GOOD, mv=-5)) == {'missing': ['muzzle velocity']}
    assert js_of(ready, dict(GOOD, mv='2600')) == {'missing': ['muzzle velocity']}
    assert js_of(ready, {k: v for k, v in GOOD.items() if k != 'mv'}) == {'missing': ['muzzle velocity']}
    assert js_of(ready, dict(GOOD, twist=None, mv=None)) == {'missing': ['twist', 'muzzle velocity']}
    assert js_of(ready, {}) == {'missing': ['twist', 'bullet length', 'bullet diameter', 'bullet weight', 'muzzle velocity']}


def test_of_with_unusable_air_is_an_empty_missing_list_never_a_nan(ready):
    for air in (None, {}, dict(temp=59), dict(press=29.92), dict(temp=59, press=0), dict(temp=59, press=-3),
                dict(temp='59', press=29.92), dict(temp=None, press=29.92)):
        r = js_of(ready, GOOD, air)
        assert r == {'missing': []}, (air, r)


@pytest.mark.parametrize('sg,text', [(1.38, '1.3'), (1.4, '1.4'), (0.97, '0.9'), (1.0, '1.0'), (2.3, '2.3'), (2.4003, '2.4'),
                                     (1.99999, '1.9'), (0.05, '0.0'), (12.34, '12.3')])
def test_text_rounds_the_figure_down_to_one_decimal(ready, sg, text):
    assert ready.evaluate('sg => BSPIN.text(sg)', sg) == text


def test_text_is_empty_for_anything_that_is_not_a_finite_number(ready):
    for js in ('NaN', 'Infinity', '-Infinity', 'null', 'undefined', '"2.4"'):
        assert ready.evaluate('BSPIN.text(%s)' % js) == '', js


def test_text_survives_binary_floating_error_at_exact_decimals(ready):
    # every one-decimal value from 0.1 to 9.9 prints as itself, however the division that made it rounded
    bad = ready.evaluate("""() => { const out = [];
      for (let i = 1; i < 100; i++) { const v = i / 10; for (const x of [v, v * 1.0000000001 - 1e-12, +(v / 3 * 3).toPrecision(15)]) if (BSPIN.text(x) !== v.toFixed(1)) out.push([x, BSPIN.text(x)]); }
      return out; }""")
    assert bad == []
