"""The Ballistics screen: the answer written for the profile's sight, the shot beside it, the dope card, the messages."""
import json
import os
import re

import pytest
from playwright.sync_api import expect

from .test_tactical_layout import clipped_buttons, enlarge_text, overflow, too_small
from .test_map import tiles_ok

LOAD = {'bc': 0.25, 'model': 'G7', 'w': 175, 'mv': 2600, 'sight': 1.5, 'zero': 100}      # the .308 starting point's numbers
TURRET = {**LOAD, 'id': 'ut', 'name': 'Turret rifle', 'optic': {'type': 'turret', 'unit': 'mil', 'click': 0.1}}
DOT = {**LOAD, 'id': 'ud', 'name': 'Dot rifle', 'optic': {'type': 'dot'}}
RET = {**LOAD, 'id': 'ur', 'name': 'Reticle rifle', 'optic': {'type': 'reticle', 'unit': 'mil', 'marks': [1.5, 3, 4.6, 6.3]}}
PLAIN = {**LOAD, 'id': 'un', 'name': 'No sight rifle'}
MINE = [TURRET, DOT, RET, PLAIN]
SHOT = {'bRange': '500', 'bAngle': '0', 'bWind': '10', 'bClock': '3', 'bTemp': '59', 'bAlt': '0', 'bPress': '', 'bRH': '50', 'bMax': '1000', 'bStep': '50'}
NASTY = re.compile(r'NaN|Infinity|undefined|-0\.0')


def open_screen(page, app_url, profile='p308', profiles=(), shot=None, night=False, view=(360, 640), **kv):
    """Open the screen with this storage and nothing else (it may be called again in one test: storage is replaced each time)."""
    page.set_viewport_size({'width': view[0], 'height': view[1]})
    tiles_ok(page)
    seed = {'advAck': True, 'night': night, 'mapFollow': False, 'profiles': list(profiles), 'bal': {'profile': profile, **SHOT, **(shot or {})}, **kv}
    page.goto(app_url)
    page.evaluate("kv => { localStorage.clear(); for (const k in kv) localStorage.setItem('fk.' + k, JSON.stringify(kv[k])); }", seed)
    page.goto(app_url + '#/tactical/ballistics')
    page.reload()
    page.wait_for_function('window.FK && FK.sheet && FK.view && FK.view() === "ballistics" && document.querySelector("#solElev").textContent.length > 3')
    page.wait_for_timeout(100)


def settle(page):
    page.wait_for_timeout(450)       # the 150 ms recalculation timer plus a margin


def shot(page, **kv):
    for k, v in kv.items():
        if k == 'bClock':
            page.select_option('#bClock', str(v))
        else:
            page.fill('#' + k, str(v))
    settle(page)


def lines(page, sel):
    return [x.strip() for x in page.inner_text(sel).split('\n') if x.strip()]


def card(page):
    return {'elev': lines(page, '#solElev'), 'wind': lines(page, '#solWind'), 'sub': page.inner_text('#solSub')}


def head(page):
    return [c.strip() for c in page.locator('#dope th').all_inner_texts()]


def body(page):
    return page.evaluate("[...document.querySelectorAll('#dope tbody tr')].map(r => [...r.children].map(c => c.textContent))")


def whole_page_is_clean(page):
    text = page.evaluate("document.querySelector('#view-ballistics').innerText")
    assert not NASTY.search(text), NASTY.search(text).group(0)


# ---------- First screen ----------

def test_first_screen_holds_profile_answer_and_shot_inputs(page, app_url):
    open_screen(page, app_url)
    nav_top = page.evaluate("document.querySelector('.tabbar').getBoundingClientRect().top")
    for sel in ['#bProfile', '#bEdit', '#solution', '#bRange', '#bAngle', '#bWind', '#bClock']:
        r = page.locator(sel).bounding_box()
        assert r['y'] >= 0 and r['y'] + r['height'] <= nav_top, (sel, r, nav_top)
    assert page.evaluate('window.scrollY') == 0


@pytest.mark.parametrize('profile', ['p308', 'ut', 'ud', 'ur'])
def test_first_screen_fits_for_every_kind_of_sight(page, app_url, profile):
    open_screen(page, app_url, profile=profile, profiles=MINE)
    nav_top = page.evaluate("document.querySelector('.tabbar').getBoundingClientRect().top")
    for sel in ['#bProfile', '#solution', '#bRange', '#bAngle', '#bWind', '#bClock']:
        r = page.locator(sel).bounding_box()
        assert r['y'] + r['height'] <= nav_top, (sel, r, nav_top)


def test_answer_stays_visible_with_the_keyboard_up(page, app_url):
    open_screen(page, app_url, profile='ud', profiles=MINE, view=(360, 340))
    page.focus('#bRange')
    page.wait_for_timeout(200)
    r = page.locator('#solution').bounding_box()
    assert r['y'] >= 0 and r['y'] + r['height'] <= 340, r


def test_load_fields_and_old_buttons_are_gone_from_the_main_screen(page, app_url):
    open_screen(page, app_url)
    for i in ['bBC', 'bModel', 'bW', 'bMV', 'bSH', 'bZero', 'bSave', 'bDel', 'unitSeg']:
        assert page.locator('#' + i).count() == 0, i
    assert 'writeLoad' not in page.evaluate('Object.keys(FK.bal).join()')
    assert page.evaluate('Object.keys(FK.bal).sort()') == ['calc', 'clean', 'edit', 'init', 'load', 'profiles', 'remove', 'save', 'select', 'selected', 'shotAir']
    expect(page.locator('#bEdit')).to_have_text('Edit')
    assert page.evaluate("document.querySelector('#bEdit').parentElement === document.querySelector('#bProfile').parentElement")
    order = page.evaluate("""() => ['#bProfile', '#bSight', '#solution', '#bRange', '#bCond', '#bMax', '#dope'].map(s => document.querySelector(s).getBoundingClientRect().top)""")
    assert order == sorted(order)


# ---------- The answer follows the sight ----------

def test_answer_follows_the_sight(page, app_url):
    open_screen(page, app_url, profile='ut', profiles=MINE)
    c = card(page)
    assert c['elev'] == ['ELEVATION', 'U 3.5 mil', '35 clicks'] and c['wind'] == ['WINDAGE', 'R 1.2 mil', '12 clicks'], c
    page.evaluate('FK.bal.select("ud")'); settle(page)
    c = card(page)
    assert c['elev'] == ['ELEVATION', 'Hold 64 in high'] and c['wind'][:2] == ['WINDAGE', 'Hold 21 in right'], c
    page.evaluate('FK.bal.select("ur")'); settle(page)
    c = card(page)
    assert c['elev'][:2] == ['ELEVATION', 'Mark 2'] and c['elev'][2].startswith('hold ') and c['elev'][2].endswith(' in high'), c
    assert c['wind'][:2] == ['WINDAGE', 'R 1.2 mil'] and c['wind'][2] == 'hold 21 in right'
    assert 'At 500 yd: 63.6 in low, drift 21.2 in left, 1782 fps, 1234 ft-lb, 0.70 s flight.' == c['sub']     # it read 'drop 63.6 in, drift 21.2 in'


def test_the_sight_never_changes_the_trajectory(page, app_url):
    """Four profiles with the same load and different sights give the same drop, drift, speed, energy and time."""
    subs, bodies = [], []
    for pid in ['ut', 'ud', 'ur', 'un']:
        open_screen(page, app_url, profile=pid, profiles=MINE)
        subs.append(card(page)['sub'])
        i = head(page).index('Path in')
        bodies.append([[r[0], r[i]] + r[-3:] for r in body(page)])      # yards, drop, fps, ft-lb, time
    assert len(set(subs)) == 1 and all(b == bodies[0] for b in bodies)


def test_sight_line_names_the_sight(page, app_url):
    cases = [('ut', 'Mil turrets, 0.1 mil clicks'), ('ud', 'Red dot or iron sights'), ('ur', 'Drop reticle, 4 marks in mil'),
             ('un', 'No sight set: showing every unit'), ('p308', 'No sight set: showing every unit')]
    for pid, want in cases:
        open_screen(page, app_url, profile=pid, profiles=MINE)
        expect(page.locator('#bSight')).to_have_text(want)
    open_screen(page, app_url, profile='ut', profiles=MINE)
    expect(page.locator('#bZeroLine')).to_be_hidden()


def test_zero_line_shows_the_zero_conditions(page, app_url):
    z = {**TURRET, 'id': 'uz', 'name': 'Z', 'zeroAtm': {'temp': 90, 'alt': 400, 'rh': 50}}
    zp = {**TURRET, 'id': 'uzp', 'name': 'ZP', 'zeroAtm': {'temp': 90, 'alt': 400, 'press': 29.5, 'rh': 50}}
    open_screen(page, app_url, profile='uz', profiles=[z, zp])
    expect(page.locator('#bZeroLine')).to_have_text('Zeroed at 90°F, 400 ft')
    page.evaluate('FK.bal.select("uzp")')
    expect(page.locator('#bZeroLine')).to_have_text('Zeroed at 90°F, 29.50 inHg')


def test_no_sight_shows_every_unit(page, app_url):
    open_screen(page, app_url, profile='un', profiles=MINE)
    c = card(page)
    assert c['elev'] == ['ELEVATION', 'U 3.5 mil', 'U 12.2 MOA', 'Hold 64 in high'], c
    assert c['wind'] == ['WINDAGE', 'R 1.2 mil', 'R 4.0 MOA', 'Hold 21 in right'], c
    expect(page.locator('#bAll')).to_be_hidden()
    assert head(page) == ['Yd', 'Elev mil', 'Elev MOA', 'Wind mil', 'Wind MOA', 'Path in', 'Drift in', 'fps', 'ft-lb', 'Time s']


def test_show_all_units_is_temporary(page, app_url):
    open_screen(page, app_url, profile='ut', profiles=MINE)
    b = page.locator('#bAll')
    expect(b).to_have_text('Show all units')
    expect(b).to_have_attribute('aria-pressed', 'false')
    assert page.evaluate('FK._test.balState()') == {'profile': 'ut', 'showAll': False}
    b.click()
    expect(b).to_have_attribute('aria-pressed', 'true')
    expect(b).to_have_text('Hide other units')
    c = card(page)
    # the sight's own lines stay and the other units are added beneath (a line the same as the sight's own is left out)
    assert c['elev'] == ['ELEVATION', 'U 3.5 mil', '35 clicks', 'U 12.2 MOA', 'Hold 64 in high'], c
    assert c['wind'] == ['WINDAGE', 'R 1.2 mil', '12 clicks', 'R 4.0 MOA', 'Hold 21 in right'], c
    assert head(page)[:3] == ['Yd', 'Elev mil', 'Elev clicks']        # the dope card keeps the sight's own columns (it turned to every unit)
    assert page.evaluate('FK._test.balState()') == {'profile': 'ut', 'showAll': True}
    page.select_option('#bProfile', 'ud')                         # a profile change turns it off
    expect(b).to_have_attribute('aria-pressed', 'false')
    expect(b).to_have_text('Show all units')
    assert card(page)['elev'] == ['ELEVATION', 'Hold 64 in high']
    b.click()
    assert card(page)['elev'] == ['ELEVATION', 'Hold 64 in high', 'U 3.5 mil', 'U 12.2 MOA']
    assert page.evaluate('FK._test.balState().showAll') is True
    stored = json.loads(page.evaluate("localStorage.getItem('fk.bal')"))
    assert 'showAll' not in stored and 'bAll' not in stored          # never stored
    page.reload()
    page.wait_for_selector('#dope tr')
    assert page.evaluate('FK._test.balState()') == {'profile': 'ud', 'showAll': False}
    expect(page.locator('#bAll')).to_have_attribute('aria-pressed', 'false')


def test_show_all_units_turns_off_when_the_screen_is_left_and_opened_again(page, app_url):
    open_screen(page, app_url, profile='ut', profiles=MINE)
    page.click('#bAll')
    page.evaluate("FK.route.go('/tactical/position')")
    page.wait_for_function('FK.view() === "position"')
    page.evaluate("FK.route.go('/tactical/ballistics')")
    page.wait_for_function('FK.view() === "ballistics"')
    assert page.evaluate('FK._test.balState().showAll') is False


# ---------- Dope card ----------

def test_dope_columns_follow_the_sight(page, app_url):
    open_screen(page, app_url, profile='ut', profiles=MINE)
    assert head(page) == ['Yd', 'Elev mil', 'Elev clicks', 'Wind mil', 'Wind clicks', 'Path in', 'Drift in', 'fps', 'ft-lb', 'Time s']
    assert body(page)[9][:5] == ['500', 'U 3.5', 'U 35', 'R 1.2', 'R 12']
    page.evaluate('FK.bal.select("ur")'); settle(page)
    assert head(page) == ['Yd', 'Mark', 'Elev hold in', 'Wind mil', 'Wind hold in', 'Path in', 'fps', 'ft-lb', 'Time s']      # no Drift in
    page.evaluate('FK.bal.select("ud")'); settle(page)
    assert head(page) == ['Yd', 'Elev hold in', 'Wind hold in', 'Path in', 'Drift in', 'fps', 'ft-lb', 'Time s']
    page.click('#bAll')                                       # other units on the answer card only: the dope card is unchanged
    assert head(page) == ['Yd', 'Elev hold in', 'Wind hold in', 'Path in', 'Drift in', 'fps', 'ft-lb', 'Time s']
    rows = body(page)
    assert all(len(r) == 8 for r in rows) and rows[0][0] == '50'


def test_dope_rows_keep_zero_and_transonic_marking(page, app_url):
    open_screen(page, app_url, profile='ut', profiles=MINE, shot={'bMax': '1500'})
    flags = page.evaluate("[...document.querySelectorAll('#dope tbody tr')].map(r => [r.children[0].textContent, r.classList.contains('zero'), r.classList.contains('trans')])")
    assert [f[0] for f in flags if f[1]] == ['100']
    assert any(f[2] for f in flags) and not flags[0][2]
    assert page.evaluate("getComputedStyle(document.querySelector('#dope tr.trans td')).color") != page.evaluate("getComputedStyle(document.querySelector('#dope tr:not(.trans):not(.zero) td')).color")


def test_dope_table_scrolls_with_the_cue_when_wide(page, app_url):
    open_screen(page, app_url, profile='ut', profiles=MINE)
    wrap = page.locator('.tablewrap').filter(has=page.locator('#dope'))
    cue = page.locator('.sv-swipe')
    expect(cue).to_be_visible()
    expect(cue).to_have_text('Swipe sideways to see more columns')
    assert page.evaluate("document.querySelector('#dope').closest('.tablewrap').classList.contains('wide')")
    assert page.evaluate("(w => w.scrollWidth > w.clientWidth)(document.querySelector('#dope').closest('.tablewrap'))")
    pos = page.evaluate("getComputedStyle(document.querySelector('#dope td')).position")
    assert pos == 'sticky'
    assert page.evaluate("document.querySelector('#dope').closest('.tablewrap').getAttribute('aria-label')") == 'Dope card table, scrolls both ways'
    wrap.evaluate('w => { w.scrollLeft = 300; }')
    first = page.evaluate("document.querySelector('#dope td').getBoundingClientRect().left - document.querySelector('#dope').closest('.tablewrap').getBoundingClientRect().left")
    assert -1 <= first <= 2        # the yard column stays at the left edge while the rest scrolls
    # nothing to scroll: no cue. The turret's headings now name elevation or wind ("Elev clicks"), so its table no longer fits even
    # at the widest the screen gets (640 px); the red dot's eight columns do. Tall enough that the box (it scrolls up and down too)
    # needs no scroll bar.
    page.evaluate('FK.bal.select("ud")')
    page.set_viewport_size({'width': 900, 'height': 1400})
    page.wait_for_timeout(200)
    expect(cue).to_be_hidden()


def test_no_minus_zero_anywhere(page, app_url):
    open_screen(page, app_url)
    ids = page.evaluate('FK._test.presets().map(p => p.id)')
    assert len(ids) == 6
    cells = lambda: page.evaluate("[...document.querySelectorAll('#dope td')].map(c => c.textContent)")
    for pid in ids:
        open_screen(page, app_url, profile=pid, profiles=[{**TURRET, 'id': 'ux', 'name': 'X'}])
        for sel in [None, 'ux']:
            if sel:
                page.evaluate('id => FK.bal.select(id)', sel)
                settle(page)
            for pressed in ([False, True] if sel else [False]):
                if pressed:
                    page.click('#bAll')
                assert len(cells()) > 50
                assert not [c for c in cells() if re.fullmatch(r'-0\.0+', c)], (pid, sel, pressed)
                whole_page_is_clean(page)


def test_zero_row_marked_for_a_fractional_zero(page, app_url):
    p = {**TURRET, 'id': 'uf', 'name': 'Fractional', 'zero': 36.5}
    open_screen(page, app_url, profile='uf', profiles=[p])
    n = page.evaluate("document.querySelectorAll('#dope tr.zero').length")
    assert n == 1
    row = page.evaluate("[...document.querySelector('#dope tr.zero').children].map(c => c.textContent)")
    assert row[0] in ('36.5', '37') and row[5] != '' and not NASTY.search(' '.join(row))


def test_short_range_for_a_dot(page, app_url):
    p = {**DOT, 'sight': 2.6}
    open_screen(page, app_url, profile='ud', profiles=[{**p, 'zero': 100}], shot={'bRange': '7', 'bWind': '0'})
    c = card(page)
    assert re.fullmatch(r'Hold 2\.\d in high', c['elev'][1]), c
    assert c['wind'][1] == 'No hold'
    whole_page_is_clean(page)


# ---------- Messages ----------

RANGE_MSG = 'Enter a range from 1 to 3,000 yd.'


def says(page, text):
    c = card(page)
    assert c['sub'] == text, c
    assert c['elev'][1:] == ['—'] and c['wind'][1:] == ['—'], c
    whole_page_is_clean(page)


def test_bad_shot_inputs_never_show_nan(page, app_url):
    open_screen(page, app_url, profile='ut', profiles=MINE)
    for bad in ('', '0', '-5', '99999', '3001', '0.5'):
        shot(page, bRange=bad)
        says(page, RANGE_MSG)
        assert page.locator('#dope tbody tr').count() == 0
    page.evaluate("document.querySelector('#bRange').value = 'abc'; document.querySelector('#bRange').dispatchEvent(new Event('input', { bubbles: true }))")
    settle(page)
    says(page, RANGE_MSG)
    shot(page, bRange=500)
    assert card(page)['elev'][1] == 'U 3.5 mil'
    for ok in ('1', '3000'):
        shot(page, bRange=ok)
        assert card(page)['elev'][1] != '—' or 'reach' in card(page)['sub']
    # a wind that is blank or not a number counts as 0 mph
    shot(page, bRange=500, bWind='')
    assert card(page)['wind'][1:] == ['0.0 mil', '0 clicks']
    page.evaluate("document.querySelector('#bWind').value = 'abc'; document.querySelector('#bWind').dispatchEvent(new Event('input', { bubbles: true }))")
    settle(page)
    assert card(page)['wind'][1:] == ['0.0 mil', '0 clicks']
    whole_page_is_clean(page)
    for w in ('-3', '101'):
        shot(page, bWind=w)
        says(page, 'Enter a wind speed from 0 to 100 mph.')
    shot(page, bWind=10)
    for a in ('61', '-61'):
        shot(page, bAngle=a)
        says(page, 'Enter an incline from -60 to 60 degrees.')
    shot(page, bAngle=0)
    assert card(page)['elev'][1] == 'U 3.5 mil'


def test_conditions_out_of_range_say_so(page, app_url):
    open_screen(page, app_url, profile='ut', profiles=MINE)
    msg = 'Check the conditions: temperature, altitude, pressure or humidity is out of range.'
    page.click('#bCondBtn')
    for k, v in [('bTemp', '141'), ('bTemp', '-61'), ('bAlt', '30001'), ('bAlt', '-2001'), ('bPress', '0'), ('bPress', '-3'), ('bRH', '101'), ('bRH', '-1'),
                 ('bPress', '2.992'), ('bPress', '0.1'), ('bPress', '7.9'), ('bPress', '33.1')]:
        shot(page, **{k: v})
        says(page, msg)
        shot(page, bTemp=59, bAlt=0, bPress='', bRH=50)
    shot(page, bTemp=140, bAlt=30000, bRH=100)
    assert card(page)['elev'][1] != '—'
    shot(page, bTemp=-60, bAlt=-2000, bRH=0, bPress='')
    assert card(page)['elev'][1] != '—'
    for v in ('8', '33'):
        shot(page, bPress=v)
        assert card(page)['elev'][1] != '—', v


def test_profile_without_numbers_asks_for_them(page, app_url):
    open_screen(page, app_url, profile='ubare', profiles=[{'id': 'ubare', 'name': 'Bare', 'mv': 2600}])
    assert page.evaluate('FK.bal.selected().id') == 'ubare'
    says(page, 'This profile needs a ballistic coefficient, a velocity and a zero range. Tap Edit.')
    assert page.locator('#dope tbody tr').count() == 0
    page.click('#bEdit')
    expect(page.locator('#dlgRifle')).to_be_visible()


def test_bullet_that_cannot_reach(page, app_url):
    nine = {'id': 'u9', 'name': '9 mm', 'bc': 0.15, 'model': 'G1', 'w': 124, 'mv': 1150, 'sight': 1.5, 'zero': 25, 'optic': {'type': 'turret', 'unit': 'mil', 'click': 0.1}}
    open_screen(page, app_url, profile='u9', profiles=[nine], shot={'bRange': '3000', 'bWind': '0', 'bMax': '3000'})
    says(page, "Bullet doesn't reach that range with these inputs.")
    text = page.inner_text('#solution')
    assert 'click' not in text and 'Mark' not in text
    whole_page_is_clean(page)
    page.evaluate('FK.bal.save({ ...FK.bal.selected(), optic: { type: "reticle", unit: "mil", marks: [1, 2] } })'); settle(page)
    assert 'Mark' not in page.inner_text('#solution')


def test_subsonic_says_so_for_every_sight(page, app_url):
    for pid in ['ut', 'ud', 'ur', 'un']:
        open_screen(page, app_url, profile=pid, profiles=MINE, shot={'bRange': '1500', 'bWind': '0'})
        sub = card(page)['sub']
        assert sub.startswith('At 1500 yd:') and sub.endswith('Subsonic: expect larger errors.'), (pid, sub)


# ---------- Conditions ----------

def test_conditions_line_and_change(page, app_url):
    open_screen(page, app_url, profile='ut', profiles=MINE)
    cond, btn = page.locator('#bCond'), page.locator('#bCondBtn')
    expect(cond).to_have_text('59°F · 0 ft · 50%')
    expect(btn).to_have_text('Change')
    expect(btn).to_have_attribute('aria-expanded', 'false')
    for i in ['bTemp', 'bAlt', 'bPress', 'bRH']:
        expect(page.locator('#' + i)).to_be_hidden()
    btn.click()
    expect(btn).to_have_attribute('aria-expanded', 'true')
    for i in ['bTemp', 'bAlt', 'bPress', 'bRH']:
        expect(page.locator('#' + i)).to_be_visible()
    shot(page, bTemp=30, bAlt=4000)
    expect(cond).to_have_text('30°F · 4000 ft · 50%')
    shot(page, bPress=25.5)
    expect(cond).to_have_text('30°F · 25.50 inHg · 50%')
    btn.click()
    expect(btn).to_have_attribute('aria-expanded', 'false')
    expect(page.locator('#bTemp')).to_be_hidden()
    page.reload()
    page.wait_for_selector('#dope tr')
    expect(page.locator('#bCondBtn')).to_have_attribute('aria-expanded', 'false')     # collapsed when the screen opens
    expect(page.locator('#bCond')).to_have_text('30°F · 25.50 inHg · 50%')


def test_zero_conditions_reach_the_answer(page, app_url):
    z = {**PLAIN, 'id': 'uz', 'name': 'Zeroed hot', 'zero': 500, 'zeroAtm': {'temp': 90, 'alt': 400, 'rh': 50}}
    open_screen(page, app_url, profile='uz', profiles=[z, {**PLAIN, 'zero': 500}], shot={'bRange': '600', 'bTemp': '10', 'bAlt': '0', 'bWind': '0'})
    mil = lambda: float(re.search(r'U (\d+\.\d)', card(page)['elev'][1]).group(1))
    hot = mil()
    page.evaluate('FK.bal.select("un")'); settle(page)
    assert hot > mil()


def test_conditions_given_as_pressure_only_are_used_for_the_zero_too(page, app_url):
    p = {**PLAIN, 'id': 'up', 'name': 'P', 'zero': 500, 'zeroAtm': {'temp': 90, 'press': 24.0, 'rh': 50}}
    open_screen(page, app_url, profile='up', profiles=[p, {**PLAIN, 'zero': 500}], shot={'bRange': '600', 'bTemp': '90', 'bAlt': '0', 'bWind': '0'})
    thin = card(page)['elev'][1]
    page.evaluate('FK.bal.select("un")'); settle(page)
    assert thin != card(page)['elev'][1]


# ---------- Saving, restoring, old data ----------

def test_save_while_recalculation_is_pending(page, app_url):
    open_screen(page, app_url, profile='ut', profiles=MINE)
    page.evaluate("""() => { const r = document.querySelector('#bRange'); r.value = '300'; r.dispatchEvent(new Event('input', { bubbles: true }));
      FK.bal.save({ ...FK.bal.selected(), mv: 2900 }); }""")
    settle(page)
    got = card(page)
    open_screen(page, app_url, profile='ut', profiles=[{**TURRET, 'mv': 2900}], shot={'bRange': '300'})
    assert card(page) == got and 'At 300 yd' in got['sub']
    assert json.loads(page.evaluate("localStorage.getItem('fk.bal')"))['bRange'] == '300'


def test_restore_backup_while_on_ballistics(page, app_url, tmp_path):
    from .test_migration import backup_file, pick, restore_now
    open_screen(page, app_url, profile='p308')
    page.evaluate("""() => { const r = document.querySelector('#bRange'); r.value = '350'; r.dispatchEvent(new Event('input', { bubbles: true })); }""")   # a save is pending
    mine = {**TURRET, 'id': 'ubk', 'name': 'From backup'}
    pick(page, tmp_path, backup_file({'fk.profiles': json.dumps([mine]), 'fk.bal': json.dumps({'profile': 'ubk', **SHOT, 'bRange': '400'})}, version='7.8'))
    restore_now(page)
    page.wait_for_selector('#dope tr')
    assert page.evaluate('FK.bal.selected().id') == 'ubk'
    expect(page.locator('#bProfile option:checked')).to_have_text('From backup')
    assert page.input_value('#bRange') == '400'


def test_stored_screen_state_holds_the_profile_and_the_shot_only(page, app_url):
    open_screen(page, app_url, profile='ut', profiles=MINE)
    shot(page, bRange=450)
    assert sorted(json.loads(page.evaluate("localStorage.getItem('fk.bal')"))) == sorted(['profile'] + list(SHOT))


def test_older_stored_copies_load_and_the_unit_key_is_left_alone(page, app_url):
    old = {'profile': 'p308', 'bBC': '0.1', 'bModel': 'G1', 'bW': '1', 'bMV': '999', 'bSH': '9', 'bZero': '9', 'extra': 'x', **SHOT, 'bRange': '650'}
    open_screen(page, app_url, profile='p308', unit='moa')
    page.evaluate("o => { localStorage.setItem('fk.bal', JSON.stringify(o)); }", old)
    page.reload()
    page.wait_for_selector('#dope tr')
    assert page.input_value('#bRange') == '650'
    assert card(page)['elev'][1] != '—' and page.evaluate('FK.bal.selected().mv') == 2600      # the built-in's own numbers
    assert page.evaluate("localStorage.getItem('fk.unit')") == '"moa"'
    assert 'U ' in card(page)['elev'][1] and 'mil' in card(page)['elev'][1]


def test_profile_names_are_text_not_markup(page, app_url):
    bad = {**TURRET, 'id': 'ux', 'name': '<img src=x onerror=alert(1)><b>x</b>'}
    open_screen(page, app_url, profile='ux', profiles=[bad])
    assert page.locator('#view-ballistics img').count() == 0 and page.locator('#bProfile b').count() == 0
    assert page.locator('#bProfile option:checked').inner_text().startswith('<img')


# ---------- Layout ----------

@pytest.mark.parametrize('night', [False, True], ids=['day', 'night'])
@pytest.mark.parametrize('profile', ['ut', 'ud', 'ur', 'p308'])
def test_ballistics_fits_360_day_night_large_text(page, app_url, night, profile):
    z = {**TURRET, 'id': 'uz', 'name': 'A rather long profile name that goes on and on', 'zeroAtm': {'temp': 90, 'alt': 400, 'rh': 50}}
    open_screen(page, app_url, profile=profile, profiles=MINE + [z], night=night)
    page.click('#bCondBtn')
    if profile == 'ut':
        page.evaluate('FK.bal.select("uz")')
    settle(page)
    assert overflow(page, '#view-ballistics') == []
    assert too_small(page, '#view-ballistics') == []
    assert clipped_buttons(page, '#view-ballistics') == []
    assert page.evaluate("document.documentElement.dataset.theme === 'night'") == night
    enlarge_text(page)
    page.wait_for_timeout(100)
    assert overflow(page, '#view-ballistics') == []
    assert clipped_buttons(page, '#view-ballistics') == []
    if page.locator('#bAll').is_visible():
        page.click('#bAll')
    assert overflow(page, '#view-ballistics') == []


# ---------- Fix round 1: the short-screen card, blank humidity, Show all units across a save ----------

def visible_in_view(page, sel, height):
    r = page.locator(sel).bounding_box()
    return r is not None and r['width'] > 0 and r['y'] >= 0 and r['y'] + r['height'] <= height


def test_message_is_visible_with_the_keyboard_up(page, app_url):
    open_screen(page, app_url, profile='ut', profiles=MINE, view=(360, 340))
    page.focus('#bRange')
    page.fill('#bRange', '0')
    settle(page)
    expect(page.locator('#solSub')).to_be_visible()
    expect(page.locator('#solSub')).to_have_text('Enter a range from 1 to 3,000 yd.')
    assert visible_in_view(page, '#solution', 340)


def test_answer_visible_with_the_keyboard_up_for_every_sight(page, app_url):
    for pid in ['ut', 'ud', 'ur', 'un']:
        open_screen(page, app_url, profile=pid, profiles=MINE, view=(360, 340))
        page.focus('#bRange')
        settle(page)
        expect(page.locator('#solElev .v')).to_be_visible()
        expect(page.locator('#solWind .v')).to_be_visible()
        assert visible_in_view(page, '#solution', 340), pid


def test_landscape_without_focus_shows_the_sentence_and_show_all_units(page, app_url):
    open_screen(page, app_url, profile='ut', profiles=MINE, view=(640, 360))
    expect(page.locator('#solSub')).to_be_visible()
    expect(page.locator('#bAll')).to_be_visible()
    bare = {'id': 'ubare', 'name': 'Bare', 'bc': 0.3, 'zero': 100}
    open_screen(page, app_url, profile='ubare', profiles=[bare], view=(640, 360))
    expect(page.locator('#solSub')).to_be_visible()
    expect(page.locator('#solSub')).to_have_text('This profile needs a ballistic coefficient, a velocity and a zero range. Tap Edit.')


def test_card_is_full_again_when_focus_leaves(page, app_url):
    open_screen(page, app_url, profile='ut', profiles=MINE, view=(360, 340))
    page.focus('#bRange')
    expect(page.locator('#bAll')).to_be_hidden()
    page.evaluate('document.activeElement.blur()')
    expect(page.locator('#bAll')).to_be_visible()
    expect(page.locator('#solSub')).to_be_visible()


def test_a_focused_condition_field_is_not_under_the_pinned_card(page, app_url):
    open_screen(page, app_url, profile='ut', profiles=MINE, view=(360, 340))
    page.click('#bCondBtn')
    for sel in ['#bTemp', '#bRH', '#bRange']:
        page.focus(sel)
        page.wait_for_timeout(200)
        card = page.locator('#solution').bounding_box()
        field = page.locator(sel).bounding_box()
        assert field['y'] >= card['y'] + card['height'], (sel, field, card)


def test_blank_humidity_means_50_percent(page, app_url):
    open_screen(page, app_url, profile='un', profiles=MINE, shot={'bRH': '50', 'bRange': '800'})
    page.click('#bCondBtn')
    with50 = (card(page), page.inner_text('#bCond'))
    shot(page, bRH='')
    assert page.inner_text('#bCond') == '59°F · 0 ft · 50%' and card(page) == with50[0]
    shot(page, bRH='0')
    assert page.inner_text('#bCond').endswith('· 0%')


def test_saving_the_same_profile_keeps_show_all_units(page, app_url):
    open_screen(page, app_url, profile='ut', profiles=MINE)
    page.click('#bAll')
    page.click('#bEdit')
    expect(page.locator('#dlgRifle')).to_be_visible()
    page.wait_for_timeout(250)
    page.click('#rfSave')
    expect(page.locator('#dlgRifle')).to_be_hidden()
    expect(page.locator('#bAll')).to_have_attribute('aria-pressed', 'true')
    page.select_option('#bProfile', 'ud')
    expect(page.locator('#bAll')).to_have_attribute('aria-pressed', 'false')


# ---------- The short state follows the visible height (a real keyboard does not shrink the page) ----------

def test_short_rule_is_480_px_of_visible_height(page, app_url):
    open_screen(page, app_url)
    got = page.evaluate('[200, 340, 479, 480, 481, 640, NaN, undefined].map(h => FK._test.balShort(h))')
    assert got == [True, True, True, True, False, False, False, False]


FAKE_VV = """(() => {
  const vv = new EventTarget();
  vv.width = 360; vv.height = %d; vv.offsetTop = 0; vv.offsetLeft = 0; vv.pageTop = 0; vv.scale = 1;
  Object.defineProperty(window, 'visualViewport', { configurable: true, get: () => vv });
  window.__vv = vv;
})()"""


def test_a_keyboard_that_only_shrinks_the_visible_viewport_pins_the_card(page, app_url):
    """The page stays 640 px tall (as on a phone with its keyboard up) and only visualViewport says 300 px are visible."""
    page.add_init_script(FAKE_VV % 300)
    open_screen(page, app_url, profile='ut', profiles=MINE)
    assert not page.evaluate("document.querySelector('#solution').classList.contains('compact')")
    for sel in ['#bRange', '#bWind']:
        page.focus(sel)
        page.wait_for_timeout(250)
        assert page.evaluate("document.querySelector('#solution').classList.contains('compact')"), sel
        c, f = page.locator('#solution').bounding_box(), page.locator(sel).bounding_box()
        assert c['y'] >= 0 and f['y'] >= c['y'] + c['height'] and f['y'] + f['height'] <= 300, (sel, c, f)
    # the keyboard goes down: the visible height grows past 480 and the card is full again
    page.evaluate("window.__vv.height = 640; window.__vv.dispatchEvent(new Event('resize'))")
    page.wait_for_timeout(100)
    assert not page.evaluate("document.querySelector('#solution').classList.contains('compact')")
    page.evaluate("window.__vv.height = 300; window.__vv.dispatchEvent(new Event('resize'))")
    page.wait_for_timeout(100)
    assert page.evaluate("document.querySelector('#solution').classList.contains('compact')")


def test_without_visual_viewport_the_window_height_decides(page, app_url):
    page.add_init_script("Object.defineProperty(window, 'visualViewport', { configurable: true, get: () => undefined })")
    open_screen(page, app_url, profile='ut', profiles=MINE, view=(360, 340))
    page.focus('#bRange')
    page.wait_for_timeout(250)
    assert page.evaluate("document.querySelector('#solution').classList.contains('compact')")
    open_screen(page, app_url, profile='ut', profiles=MINE)
    page.focus('#bRange')
    page.wait_for_timeout(250)
    assert not page.evaluate("document.querySelector('#solution').classList.contains('compact')")


def intersects(a, b):
    return a['x'] < b['x'] + b['width'] and b['x'] < a['x'] + a['width'] and a['y'] < b['y'] + b['height'] and b['y'] < a['y'] + a['height']


@pytest.mark.parametrize('view', [(360, 340), (640, 360)], ids=['short', 'landscape'])
def test_the_focused_field_is_clear_of_the_card_and_the_tab_bar(page, app_url, view):
    for sel in ['#bRange', '#bWind', '#bTemp', '#bRH']:
        open_screen(page, app_url, profile='ut', profiles=MINE, view=view)
        if sel in ('#bTemp', '#bRH'):
            page.click('#bCondBtn')
        page.focus(sel)
        page.wait_for_timeout(250)
        c, f = page.locator('#solution').bounding_box(), page.locator(sel).bounding_box()
        bar = page.locator('.tabbar').bounding_box()
        assert not intersects(f, c) and not intersects(f, bar), (sel, f, c, bar)
        assert f['y'] >= 0 and f['y'] + f['height'] <= view[1], (sel, f)



def test_the_typographic_minus_counts_on_the_screen(page, app_url):
    open_screen(page, app_url, profile='ut', profiles=MINE)
    page.click('#bCondBtn')
    shot(page, bTemp='-10', bAlt='-500', bAngle='-20')
    plain = (card(page), page.inner_text('#bCond'))
    shot(page, bTemp='\u221210', bAlt='\u2212500', bAngle='\u221220')
    assert (card(page), page.inner_text('#bCond')) == plain
    assert plain[1] == '-10°F · -500 ft · 50%'
    shot(page, bTemp='warm')                         # not a number: the conditions message, never 0 °F
    says(page, 'Check the conditions: temperature, altitude, pressure or humidity is out of range.')
    shot(page, bTemp='59', bAngle='steep')
    says(page, 'Enter an incline from -60 to 60 degrees.')
    whole_page_is_clean(page)



# ---------- The card's words, the dope card's box, the lines under the picker ----------

def test_the_sentence_says_high_or_low_and_the_way_the_wind_carries(page, app_url):
    p = {**DOT, 'sight': 2.6, 'zero': 50}
    open_screen(page, app_url, profile='ud', profiles=[p], shot={'bRange': '100'})
    sub = card(page)['sub']
    assert re.match(r'At 100 yd: \d+\.\d in high, drift \d+\.\d in left, ', sub), sub
    assert card(page)['elev'][1].endswith(' in low')               # the hold is the other way from where the bullet is
    shot(page, bClock=9)
    assert ' in right, ' in card(page)['sub']
    key = page.inner_text('#dopeKey')
    assert key == 'Path: inches above the line of sight; a minus means below. Drift: inches the wind moves the bullet, shown without a sign.'
    open_screen(page, app_url, profile='ur', profiles=MINE)
    assert page.inner_text('#dopeKey') == 'Path: inches above the line of sight; a minus means below.'     # no Drift column


def test_transonic_rows_carry_a_dagger_day_and_night(page, app_url):
    for night in (False, True):
        open_screen(page, app_url, profile='ut', profiles=MINE, night=night)
        rows = page.evaluate("[...document.querySelectorAll('#dope tbody tr')].map(r => [r.children[0].textContent, r.classList.contains('trans')])")
        assert rows[0] == ['50', False]
        assert all(y.endswith(' †') == t for y, t in rows) and any(t for _, t in rows), rows
        note = page.inner_text('#dopeTrans')
        assert note == '† Below Mach 1.2 (transonic): less certain. Confirm these with real shots.'
        assert 'orange' not in page.inner_text('#view-ballistics')
    open_screen(page, app_url, profile='ut', profiles=MINE)
    assert page.evaluate("getComputedStyle(document.querySelector('#dope tr.trans td')).color") != page.evaluate("getComputedStyle(document.querySelector('#dope tr:not(.trans):not(.zero) td')).color")


@pytest.mark.parametrize('night', [False, True], ids=['day', 'night'])
def test_dope_card_scrolls_in_its_own_box_with_sticky_headings(page, app_url, night):
    open_screen(page, app_url, profile='ut', profiles=MINE, night=night, shot={'bStep': '25'})
    wrap = page.locator('#dope').locator('xpath=..')
    h = page.evaluate("document.querySelector('#dope').closest('.tablewrap').getBoundingClientRect().height")
    assert 240 <= h <= 0.7 * 640 + 1, h
    assert page.evaluate("(w => w.scrollHeight > w.clientHeight + 10)(document.querySelector('#dope').closest('.tablewrap'))")
    wrap.evaluate('w => { w.scrollTop = 400; w.scrollLeft = 300; }')
    page.wait_for_timeout(50)
    got = page.evaluate("""() => { const w = document.querySelector('#dope').closest('.tablewrap').getBoundingClientRect();
      const th = document.querySelectorAll('#dope th')[3].getBoundingClientRect(), td = document.querySelectorAll('#dope tbody tr')[20].children[0].getBoundingClientRect();
      return { thTop: th.top - w.top, tdLeft: td.left - w.left }; }""")
    assert -1 <= got['thTop'] <= 2 and -1 <= got['tdLeft'] <= 2, got
    page.set_viewport_size({'width': 360, 'height': 900})
    page.wait_for_timeout(200)
    h = page.evaluate("document.querySelector('#dope').closest('.tablewrap').getBoundingClientRect().height")
    assert h <= 0.7 * 900 + 1 and h > 0.7 * 640, h


def test_lines_under_the_picker_name_the_load_and_ask_for_a_chronograph_on_a_built_in(page, app_url):
    open_screen(page, app_url, profile='p308', profiles=MINE)
    expect(page.locator('#bLoad')).to_have_text('175 gr · G7 0.25 · 2,600 fps · zero 100 yd')
    expect(page.locator('#bStart')).to_have_text('Built-in figures are a starting point. Chronograph your rifle and save your own profile.')
    order = page.evaluate("['#bProfile', '#bLoad', '#bSight', '#bStart', '#solution'].map(s => document.querySelector(s).getBoundingClientRect().top)")
    assert order == sorted(order)
    page.evaluate('FK.bal.select("ut")'); settle(page)
    expect(page.locator('#bStart')).to_be_hidden()
    expect(page.locator('#bLoad')).to_have_text('175 gr · G7 0.25 · 2,600 fps · zero 100 yd')
    page.evaluate('FK.bal.save({ ...FK.bal.selected(), w: 0 })'); settle(page)
    expect(page.locator('#bLoad')).to_have_text('G7 0.25 · 2,600 fps · zero 100 yd')


def test_pressure_help_says_when_to_leave_it_blank(page, app_url):
    open_screen(page, app_url)
    page.click('#bCondBtn')
    text = 'Leave blank unless you have a true station reading. Weather reports and phones give pressure corrected to sea level.'
    assert text in page.inner_text('#bCondFields')
    page.click('#bEdit')
    expect(page.locator('#dlgRifle')).to_be_visible()
    assert text in page.inner_text('#dlgRifle')
    below = page.evaluate("[document.querySelector('#rfZPress').getBoundingClientRect().bottom, [...document.querySelectorAll('#dlgRifle .hint')].find(e => e.textContent.startsWith('Leave blank')).getBoundingClientRect().top]")
    assert below[1] >= below[0]


@pytest.mark.parametrize('profile', ['p308', 'ut', 'ud', 'ur'])
def test_the_sentence_takes_the_full_width_and_the_button_sits_beneath(page, app_url, profile):
    for big in (False, True):
        open_screen(page, app_url, profile=profile, profiles=MINE)
        if big:
            enlarge_text(page)
            page.wait_for_timeout(100)
        sub, cardbox = page.locator('#solSub').bounding_box(), page.locator('#solution').bounding_box()
        assert sub['width'] >= cardbox['width'] - 40, (sub, cardbox)
        if page.locator('#bAll').is_visible():
            b = page.locator('#bAll').bounding_box()
            assert b['y'] >= sub['y'] + sub['height'] - 1 and b['height'] >= 44, (b, sub)


def test_first_screen_fits_with_the_load_line_and_the_zero_line(page, app_url):
    z = {**TURRET, 'id': 'uz', 'name': 'Zeroed turret', 'zeroAtm': {'temp': 90, 'alt': 400, 'rh': 50}}
    open_screen(page, app_url, profile='uz', profiles=[z])
    nav_top = page.evaluate("document.querySelector('.tabbar').getBoundingClientRect().top")
    expect(page.locator('#bZeroLine')).to_be_visible()
    expect(page.locator('#bAll')).to_be_visible()
    for sel in ['#bProfile', '#bLoad', '#solution', '#bRange', '#bAngle', '#bWind', '#bClock']:
        r = page.locator(sel).bounding_box()
        assert r['y'] >= 0 and r['y'] + r['height'] <= nav_top, (sel, r, nav_top)



# ---------- Second pass ----------

def test_other_units_leave_the_dope_card_with_the_sights_own_columns(page, app_url):
    open_screen(page, app_url, profile='ut', profiles=MINE)
    before = (head(page), body(page))
    page.click('#bAll')
    expect(page.locator('#bAll')).to_have_attribute('aria-pressed', 'true')
    assert 'Elev clicks' in head(page) and (head(page), body(page)) == before
    page.evaluate('FK.bal.select("ur")'); settle(page)
    page.click('#bAll')
    assert head(page)[:3] == ['Yd', 'Mark', 'Elev hold in']
    open_screen(page, app_url, profile='un', profiles=MINE)
    assert head(page)[:3] == ['Yd', 'Elev mil', 'Elev MOA']        # no sight: unchanged


def test_other_units_never_repeat_a_line_whatever_its_case(page, app_url):
    open_screen(page, app_url, profile='ur', profiles=MINE)
    page.click('#bAll')
    wind = [x.lower() for x in card(page)['wind'][1:]]
    assert wind[1].startswith('hold ') and len(wind) == len(set(wind)), wind


def test_the_load_line_is_hidden_for_a_profile_the_screen_cannot_use(page, app_url):
    odd = {'id': 'uo', 'name': 'Odd', 'bc': 0.00001, 'model': 'G7', 'w': 1e308, 'mv': 99999, 'sight': 1.5, 'zero': 0.001}
    open_screen(page, app_url, profile='uo', profiles=[odd])
    assert card(page)['sub'] == 'This profile needs a ballistic coefficient, a velocity and a zero range. Tap Edit.'
    expect(page.locator('#bLoad')).to_be_hidden()
    assert page.inner_text('#bLoad') == ''
    open_screen(page, app_url, profile='ubare', profiles=[{'id': 'ubare', 'name': 'Bare', 'mv': 2600}])
    expect(page.locator('#bLoad')).to_be_hidden()
    open_screen(page, app_url, profile='ut', profiles=MINE)
    expect(page.locator('#bLoad')).to_be_visible()


def test_a_swipe_at_the_end_of_the_dope_box_carries_on_to_the_page(page, app_url):
    open_screen(page, app_url, profile='ut', profiles=MINE)
    assert page.evaluate("getComputedStyle(document.querySelector('#dope').closest('.tablewrap')).overscrollBehaviorY") == 'auto'


# ---------- Spin drift ----------

def shot_now(page, **kv):
    """Type into the shot fields and wait for the real condition: the 150 ms timer has fired. `later()` runs `saveInputs(); calc()`
    in one tick and saveInputs stores every shot field (all ten, selects included), so once the stored copy holds each typed value
    the card and dope card have been recalculated. No fixed sleep."""
    for k, v in kv.items():
        if k == 'bClock':
            page.select_option('#bClock', str(v))
        else:
            page.fill('#' + k, str(v))
    page.wait_for_function("kv => { const s = JSON.parse(localStorage.getItem('fk.bal') || '{}'); return Object.keys(kv).every(k => String(s[k]) === kv[k]); }",
                           arg={k: str(v) for k, v in kv.items()})


SPIN = {**LOAD, 'id': 'us', 'name': 'Spin rifle', 'twist': 10, 'blen': 1.24, 'bdia': 0.308}
SPIN_L = {**SPIN, 'id': 'ul', 'name': 'Left rifle', 'twistDir': 'L'}
SPIN_MARGINAL = {**SPIN, 'id': 'um', 'name': 'Marginal rifle', 'twist': 14}       # Miller 1.22 (checked below)
SPIN_UNSTABLE = {**SPIN, 'id': 'uu', 'name': 'Unstable rifle', 'twist': 18}       # Miller 0.74
SPINNERS = [PLAIN, SPIN, SPIN_L, SPIN_MARGINAL, SPIN_UNSTABLE, {**LOAD, 'id': 'ub', 'name': 'Half rifle', 'bdia': 0.308}]
TAIL = ' Coriolis is not included.'


def miller(w, dia, length, twist, mv, temp=59, press=29.92126):
    """Courtney & Miller equation 1, written out here and not read from the app."""
    t, L = twist / dia, length / dia
    return 30 * w / (t * t * dia ** 3 * L * (1 + L * L)) * (mv / 2800) ** (1 / 3) * (temp + 460) / 519 * 29.92 / press


def sg_of(p):
    return miller(p['w'], p['bdia'], p['blen'], p['twist'], p['mv'])


def drift_col(page):
    """The dope card's Drift column as signed inches (right +), or the text when it carries no letter."""
    i = head(page).index('Drift in')
    return {r[0].split(' ')[0]: r[i] for r in body(page)}      # the yardage, without a transonic dagger


def signed(cell):
    m = re.fullmatch(r'(\d+\.\d)(?: ([RL]))?', cell)
    assert m, cell
    return float(m.group(1)) * (-1 if m.group(2) == 'L' else 1)


def times(page):
    i = head(page).index('Time s')
    return {r[0].split(' ')[0]: float(r[i]) for r in body(page)}


def test_the_test_inputs_sit_inside_their_bands():
    assert sg_of(SPIN) > 1.5 and 1.05 < sg_of(SPIN_MARGINAL) < 1.35 and sg_of(SPIN_UNSTABLE) < 0.9


def test_no_wind_gives_a_left_hold_that_grows_with_range(page, app_url):
    open_screen(page, app_url, profile='us', profiles=SPINNERS, shot={'bWind': '0', 'bRange': '600'})
    w = card(page)['wind']
    assert w[0] == 'WINDAGE' and w[1].startswith('L '), w                 # the bullet drifts right, so the hold is left
    d = drift_col(page)
    assert d['600'].endswith(' R') and d['1000'].endswith(' R'), d
    assert signed(d['1000']) > signed(d['600']) > signed(d['300']) > 0
    page.evaluate('FK.bal.select("un")')
    assert card(page)['wind'] == ['WINDAGE', '0.0 mil', '0.0 MOA', 'No hold'], card(page)['wind']     # no twist given: no windage at all
    assert set(drift_col(page).values()) == {'0.0'}


def test_windage_equals_wind_alone_plus_the_formula(page, app_url):
    """At 600 yd. The screen shows each figure rounded to 0.1 in. So (a) the spin share against the formula worked from the solver's
    own unrounded flight time: only the display rounding (0.05 in) can differ, tolerance 0.06; (b) the same from the flight time
    printed on the card (rounded to 0.01 s, worth up to 1.83 x drift / tof x 0.005 = about 0.06 in at 600 yd): 0.05 + 0.06, tolerance
    0.15; (c) SPIN minus PLAIN with a wind: two rounded readings add up to 0.1 in, plus the 0.06: tolerance 0.17."""
    open_screen(page, app_url, profile='us', profiles=SPINNERS, shot={'bWind': '0', 'bRange': '600'})
    sg = sg_of(SPIN)
    exact = page.evaluate("""p => BAL.solve({ bc: p.bc, model: p.model, w: p.w, mv: p.mv, sight: p.sight, zero: p.zero, temp: 59, alt: 0, press: 0, rh: 50,
      wind: 0, clock: 3, angle: 0, ranges: [600] }).rows[0].tof""", SPIN)
    shown = signed(drift_col(page)['600'])
    assert abs(shown - 1.25 * (sg + 1.2) * exact ** 1.83) < 0.06, (shown, exact)
    assert abs(shown - 1.25 * (sg + 1.2) * times(page)['600'] ** 1.83) < 0.15, (shown, times(page)['600'])
    for wind, clock in (('10', 3), ('8', 9)):
        shot_now(page, bWind=wind, bClock=clock, bRange=600)
        with_spin = signed(drift_col(page)['600'])
        page.evaluate('FK.bal.select("un")')
        plain = signed(drift_col(page)['600'])                              # the plain column has no letter: wind from 3 o'clock carries the bullet left
        plain *= -1 if clock == 3 else 1
        page.evaluate('FK.bal.select("us")')
        assert abs((with_spin - plain) - 1.25 * (sg + 1.2) * times(page)['600'] ** 1.83) < 0.17, (wind, clock, with_spin, plain)


def test_left_twist_mirrors_it(page, app_url):
    open_screen(page, app_url, profile='us', profiles=SPINNERS, shot={'bWind': '0'})
    right = drift_col(page)
    page.evaluate('FK.bal.select("ul")')
    left = drift_col(page)
    assert card(page)['wind'][1].startswith('R '), card(page)['wind']
    for yd, v in right.items():
        assert v.endswith(' R') == left[yd].endswith(' L') and v[:-2] == left[yd][:-2], (yd, v, left[yd])
    assert 'left-hand twist' in page.inner_text('#bSpin')


def test_spin_against_the_wind_changes_side_along_the_card(page, app_url):
    open_screen(page, app_url, profile='us', profiles=SPINNERS, shot={'bWind': '1.2', 'bClock': '3', 'bMax': '1500'})     # at 1.2 mph the sides cross near 1,000 yd
    cells = list(drift_col(page).values())
    sides = [c[-1] for c in cells if c[-1] in 'RL']
    assert 'L' in sides and 'R' in sides, cells
    first_r = next(i for i, s in enumerate(sides) if s == 'R')
    assert 'L' in sides[:first_r] and set(sides[first_r:]) == {'R'}, cells        # one change of side, wind first and spin after
    assert '0.0' in cells, cells                                                  # the crossing rounds to zero: no letter
    assert not [c for c in cells if NASTY.search(c) or re.search(r'[RL] 0\.0', c)], cells
    whole_page_is_clean(page)


def test_answer_line_names_the_spin_share(page, app_url):
    open_screen(page, app_url, profile='us', profiles=SPINNERS, shot={'bWind': '0', 'bRange': '500'})
    sub = card(page)['sub']
    m = re.match(r'At 500 yd: \d+\.\d in low, drift (\d+\.\d) in right \(spin drift (\d+\.\d) in right included\), ', sub)
    assert m and m.group(1) == m.group(2), sub
    shot_now(page, bWind=10)
    assert re.search(r'drift \d+\.\d in left \(spin drift \d+\.\d in right included\), ', card(page)['sub']), card(page)['sub']
    page.evaluate('FK.bal.select("ul")')
    assert re.search(r'\(spin drift \d+\.\d in left included\)', card(page)['sub']), card(page)['sub']
    page.evaluate('FK.bal.select("un")')
    assert 'spin' not in card(page)['sub']
    shot_now(page, bRange=1, bWind=0)                                             # a share that rounds to zero is not named
    page.evaluate('FK.bal.select("us")')
    assert 'spin' not in card(page)['sub'] and 'drift 0.0 in,' in card(page)['sub'], card(page)['sub']


def test_spin_line_three_texts(page, app_url):
    open_screen(page, app_url, profile='us', profiles=SPINNERS)
    g = f"stability {int(sg_of(SPIN) * 10) / 10:.1f}"
    assert page.inner_text('#bSpin') == f'Windage includes spin drift ({g}, right-hand twist).{TAIL}'
    page.evaluate('FK.bal.select("ul")')
    assert page.inner_text('#bSpin') == f'Windage includes spin drift ({g}, left-hand twist).{TAIL}'
    page.evaluate('FK.bal.select("uu")')
    assert page.inner_text('#bSpin') == f'Spin drift not included: by the Miller formula this bullet is not stable in this twist (stability 0.7).{TAIL}'
    page.evaluate('FK.bal.select("ub")')
    assert page.inner_text('#bSpin') == f'Spin drift not included: add twist and bullet length to the profile.{TAIL}'
    page.evaluate('FK.bal.select("un")')
    assert page.inner_text('#bSpin') == f'Spin drift not included: add twist, bullet length and bullet diameter to the profile.{TAIL}'
    one = {k: v for k, v in {**SPIN, 'id': 'uo', 'name': 'One short'}.items() if k != 'blen'}
    open_screen(page, app_url, profile='uo', profiles=[one])
    assert page.inner_text('#bSpin') == f'Spin drift not included: add bullet length to the profile.{TAIL}'


def test_unstable_bullet_gets_no_spin_drift(page, app_url):
    open_screen(page, app_url, profile='uu', profiles=SPINNERS, shot={'bWind': '0'})
    assert set(drift_col(page).values()) == {'0.0'} and 'spin' not in card(page)['sub']
    assert head(page).count('Drift in') == 1
    assert page.inner_text('#dopeKey').endswith('Drift: inches the wind moves the bullet, shown without a sign.')


def test_builtin_load_says_what_to_add(page, app_url):
    open_screen(page, app_url)
    assert page.inner_text('#bSpin') == f'Spin drift not included: add twist, bullet length and bullet diameter to the profile.{TAIL}'


def test_marginal_is_shown_and_still_applied(page, app_url):
    open_screen(page, app_url, profile='um', profiles=SPINNERS, shot={'bWind': '0'})
    assert page.inner_text('#bSpin') == f'Windage includes spin drift (stability {int(sg_of(SPIN_MARGINAL) * 10) / 10:.1f}, marginal, right-hand twist).{TAIL}'
    assert drift_col(page)['500'].endswith(' R') and 'spin drift' in card(page)['sub']
    marginal = signed(drift_col(page)['500'])
    page.evaluate('FK.bal.select("us")')
    assert signed(drift_col(page)['500']) > marginal > 0               # the stability figure is in the formula: steadier, more drift


def test_out_of_reach_says_the_dope_card_has_it_not_the_windage(page, app_url):
    nine = {'id': 'u9', 'name': '9 mm', 'bc': 0.15, 'model': 'G1', 'w': 124, 'mv': 1150, 'sight': 1.5, 'zero': 25,
            'twist': 10, 'blen': 0.72, 'bdia': 0.355}                           # Miller 7.5 (checked below)
    assert 7.5 <= miller(124, 0.355, 0.72, 10, 1150) < 7.6
    open_screen(page, app_url, profile='u9', profiles=[nine], shot={'bRange': '3000', 'bWind': '0', 'bMax': '3000'})
    says(page, "Bullet doesn't reach that range with these inputs.")
    assert card(page)['wind'] == ['WINDAGE', '—']
    assert page.inner_text('#bSpin') == f'The dope card includes spin drift (stability 7.5, right-hand twist).{TAIL}'
    assert any(c.endswith(' R') for c in drift_col(page).values())
    shot_now(page, bRange=100)                                                  # in reach again: the windage has it
    assert page.inner_text('#bSpin') == f'Windage includes spin drift (stability 7.5, right-hand twist).{TAIL}'


def test_spin_line_on_every_message_path(page, app_url):
    open_screen(page, app_url, profile='us', profiles=SPINNERS)
    for field, bad in (('bRange', '0'), ('bWind', '500'), ('bAngle', '99'), ('bTemp', '500')):
        if field == 'bTemp':
            page.click('#bCondBtn')
        shot_now(page, **{field: bad})
        assert re.match(r'Enter an? |Check the conditions', card(page)['sub']), card(page)['sub']
        assert page.inner_text('#bSpin') == f'Spin drift not included.{TAIL}', (field, page.inner_text('#bSpin'))
        open_screen(page, app_url, profile='us', profiles=SPINNERS)
    open_screen(page, app_url, profile='un', profiles=SPINNERS, shot={'bRange': '0'})
    assert page.inner_text('#bSpin') == f'Spin drift not included: add twist, bullet length and bullet diameter to the profile.{TAIL}'
    open_screen(page, app_url, profile='us', profiles=[{**SPIN, 'bc': 0}])
    assert 'needs a ballistic coefficient' in card(page)['sub']
    assert page.inner_text('#bSpin') == f'Spin drift not included.{TAIL}'


def test_card_without_spin_is_byte_for_byte_v711(page, app_url):
    """Headers, key, every body cell, the answer card and the sentence for a profile without spin fields, against what the v7.11 build
    (commit f74c5db) showed: tests/fixtures/ballistics_v711_plain_card.json, captured from that build, not from this one."""
    want = json.load(open(os.path.join(os.path.dirname(__file__), 'fixtures', 'ballistics_v711_plain_card.json')))
    open_screen(page, app_url, profile='un', profiles=SPINNERS)
    assert head(page) == want['head']
    assert page.inner_text('#dopeKey') == want['key']
    assert body(page) == want['body'] and len(want['body']) == 20
    assert card(page) == want['card']
    assert page.inner_text('#bSpin') == f'Spin drift not included: add twist, bullet length and bullet diameter to the profile.{TAIL}'   # the one line that changed


def test_spin_card_key_and_cells(page, app_url):
    open_screen(page, app_url, profile='us', profiles=SPINNERS, shot={'bWind': '0'})
    assert page.inner_text('#dopeKey') == 'Path: inches above the line of sight; a minus means below. Drift: inches the wind and the spin move the bullet; R right, L left.'
    d = drift_col(page)
    assert all(re.fullmatch(r'\d+\.\d [RL]|0\.0', v) for v in d.values()), d
    assert not [v for v in d.values() if NASTY.search(v)]


@pytest.mark.parametrize('sight', [None, {'type': 'turret', 'unit': 'mil', 'click': 0.1}, {'type': 'dot'},
                                   {'type': 'reticle', 'unit': 'mil', 'marks': [1.5, 3, 4.6, 6.3]}])
def test_every_sight_reads_the_adjusted_windage(page, app_url, sight):
    p = {**SPIN, 'id': 'ux', 'name': 'Sighted spin rifle', **({'optic': sight} if sight else {})}
    open_screen(page, app_url, profile='ux', profiles=[p], shot={'bWind': '0', 'bRange': '600'})
    w = ' '.join(card(page)['wind'])
    assert re.search(r'\bL\b|left', w) and not NASTY.search(w), w
    assert not NASTY.search(page.inner_text('#dope'))
    if sight and sight['type'] == 'reticle':
        assert 'Drift in' not in head(page)


@pytest.mark.parametrize('night', [False, True])
@pytest.mark.parametrize('profile', ['us', 'un', 'uu', 'um'])
def test_spin_line_fits_360_day_night_large_text(page, app_url, night, profile):
    open_screen(page, app_url, profile=profile, profiles=SPINNERS, night=night)
    enlarge_text(page)
    assert overflow(page, '#view-ballistics') == []
    box = page.locator('#bSpin').bounding_box()
    assert box['x'] >= 0 and box['x'] + box['width'] <= 360
    assert page.evaluate("(() => { const e = document.querySelector('#bSpin'); return e.scrollWidth <= e.clientWidth + 1; })()")
    whole_page_is_clean(page)
