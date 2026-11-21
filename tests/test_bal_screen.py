"""The Ballistics screen: the answer written for the profile's sight, the shot beside it, the dope card, the messages."""
import json
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
    assert page.evaluate('Object.keys(FK.bal).sort()') == ['calc', 'clean', 'edit', 'init', 'profiles', 'remove', 'save', 'select', 'selected']
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
    assert c['wind'][:2] == ['WINDAGE', 'R 1.2 mil'] and c['wind'][2] == '21 in'
    assert 'At 500 yd: drop 63.6 in, drift 21.2 in, 1782 fps, 1234 ft-lb, 0.70 s flight.' == c['sub']


def test_the_sight_never_changes_the_trajectory(page, app_url):
    """Four profiles with the same load and different sights give the same drop, drift, speed, energy and time."""
    subs, bodies = [], []
    for pid in ['ut', 'ud', 'ur', 'un']:
        open_screen(page, app_url, profile=pid, profiles=MINE)
        subs.append(card(page)['sub'])
        i = head(page).index('Drop in')
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
    assert head(page) == ['Yd', 'Elev mil', 'Elev MOA', 'Wind mil', 'Wind MOA', 'Drop in', 'Drift in', 'fps', 'ft-lb', 'Time s']


def test_show_all_units_is_temporary(page, app_url):
    open_screen(page, app_url, profile='ut', profiles=MINE)
    b = page.locator('#bAll')
    expect(b).to_have_text('Show all units')
    expect(b).to_have_attribute('aria-pressed', 'false')
    assert page.evaluate('FK._test.balState()') == {'profile': 'ut', 'showAll': False}
    b.click()
    expect(b).to_have_attribute('aria-pressed', 'true')
    c = card(page)
    assert c['elev'] == ['ELEVATION', 'U 3.5 mil', 'U 12.2 MOA', 'Hold 64 in high'], c
    assert head(page)[:3] == ['Yd', 'Elev mil', 'Elev MOA']
    assert page.evaluate('FK._test.balState()') == {'profile': 'ut', 'showAll': True}
    page.select_option('#bProfile', 'ud')                         # a profile change turns it off
    expect(b).to_have_attribute('aria-pressed', 'false')
    assert card(page)['elev'] == ['ELEVATION', 'Hold 64 in high']
    b.click()
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
    assert head(page) == ['Yd', 'Elev mil', 'Clicks', 'Wind mil', 'Clicks', 'Drop in', 'Drift in', 'fps', 'ft-lb', 'Time s']
    page.evaluate('FK.bal.select("ur")'); settle(page)
    assert head(page) == ['Yd', 'Mark', 'Hold in', 'Wind mil', 'Drift in', 'Drop in', 'fps', 'ft-lb', 'Time s']      # no second Drift in
    page.evaluate('FK.bal.select("ud")'); settle(page)
    assert head(page) == ['Yd', 'Hold in', 'Hold in', 'Drop in', 'Drift in', 'fps', 'ft-lb', 'Time s']
    page.click('#bAll')
    assert head(page) == ['Yd', 'Elev mil', 'Elev MOA', 'Wind mil', 'Wind MOA', 'Drop in', 'Drift in', 'fps', 'ft-lb', 'Time s']
    rows = body(page)
    assert all(len(r) == 10 for r in rows) and rows[0][0] == '50'


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
    assert page.evaluate("document.querySelector('#dope').closest('.tablewrap').getAttribute('aria-label')") == 'Dope card table, scrolls sideways'
    wrap.evaluate('w => { w.scrollLeft = 300; }')
    first = page.evaluate("document.querySelector('#dope td').getBoundingClientRect().left - document.querySelector('#dope').closest('.tablewrap').getBoundingClientRect().left")
    assert -1 <= first <= 2        # the yard column stays at the left edge while the rest scrolls
    page.set_viewport_size({'width': 900, 'height': 700})
    page.wait_for_timeout(200)
    expect(cue).to_be_hidden()    # nothing to scroll: no cue


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
    for k, v in [('bTemp', '141'), ('bTemp', '-61'), ('bAlt', '30001'), ('bAlt', '-2001'), ('bPress', '0'), ('bPress', '-3'), ('bRH', '101'), ('bRH', '-1')]:
        shot(page, **{k: v})
        says(page, msg)
        shot(page, bTemp=59, bAlt=0, bPress='', bRH=50)
    shot(page, bTemp=140, bAlt=30000, bRH=100)
    assert card(page)['elev'][1] != '—'
    shot(page, bTemp=-60, bAlt=-2000, bRH=0, bPress='')
    assert card(page)['elev'][1] != '—'


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
