"""The Tools block under the dope card and its first sheet, Close-range holds: six rows from the solver, worded as the red dot answer is."""
import pytest
from playwright.sync_api import expect

from .test_bal_screen import LOAD, NASTY, open_screen, shot_now
from .test_tactical_layout import clipped_buttons, enlarge_text, overflow, too_small

DLG = '#dlgClose'
NOTE = 'Level, no wind. Inside the zero the bullet strikes low, so the hold is high.'
NO_SIGHT = 'This profile has no sight height, so these holds assume the sight sits on the bore. Tap Edit and set it.'
PROFILE_MSG = 'This profile needs a ballistic coefficient, a velocity and a zero range. Tap Edit.'
COND_MSG = 'Check the conditions: temperature, altitude, pressure or humidity is out of range.'
YDS = ['3', '5', '7', '10', '15', '25']
# Where #bWind's top sat at 360 x 640 with the default profile in the v7.11 build (commit f74c5db, built outside this tree and measured).
V711_WIND_TOP = 525.17
STATE = "[location.hash, history.state && history.state.fkIdx, history.state && !!history.state.fkSheet, document.querySelector('#solElev').textContent, scrollY]"


def reach_tools(page):
    """The Tools block is under the dope card: bring it into view first, so a later scroll position is the person's, not the click's."""
    page.locator('#bClose').scroll_into_view_if_needed()
    page.wait_for_function("(() => { const r = document.querySelector('#bClose').getBoundingClientRect(); return r.top >= 0 && r.bottom <= innerHeight; })()")


def open_sheet(page, again=False):
    """A real tap on Close-range holds. A second tap at the same spot just after a sheet closed is swallowed on purpose (sheet.js, a double tap
    on Save must not land underneath), so a reopen sends the click to the button without coordinates instead of waiting out the 350 ms."""
    if again:
        page.locator('#bClose').dispatch_event('click')
    else:
        page.click('#bClose')
    expect(page.locator(DLG)).to_be_visible()


def rows(page):
    return page.evaluate("[...document.querySelectorAll('#clTable tbody tr')].map(r => [...r.children].map(c => c.textContent))")


def wait_closed(page):
    """The sheet has really closed and its history step has landed (no sleep: the conditions are waited for)."""
    page.wait_for_function('FK.sheet.top() === null')
    page.evaluate('new Promise(done => FK.sheet.afterStep(done))')


def test_six_rows_and_each_hold_matches_the_solver(page, app_url):
    open_screen(page, app_url)
    open_sheet(page)
    expect(page.locator('#clTitle')).to_have_text('Close-range holds')
    expect(page.locator('#clProfile')).to_have_text('Federal Gold Medal .308 Win 175 gr SMK, 24″ barrel')
    expect(page.locator('#clSight')).to_have_text('Sight height 1.5 in · zero 100 yd')
    expect(page.locator('#clNote')).to_have_text(NOTE)
    expect(page.locator('#clClose')).to_have_text('Close')
    expect(page.locator('#clTable th')).to_have_text(['Yd', 'Hold'])
    got = rows(page)
    assert [r[0] for r in got] == YDS
    # Worked out here from the solver itself: the .308 starting point, level, no wind, 59 F, sea level, 50 %.
    want = page.evaluate("""() => {
      const p = FK.bal.selected(), a = FK.bal.shotAir();
      const r = BAL.solve({ bc: p.bc, model: p.model, w: p.w, mv: p.mv, sight: p.sight, zero: p.zero, temp: a.temp, alt: a.alt, press: a.press, rh: a.rh,
        wind: 0, clock: 12, angle: 0, ranges: [3, 5, 7, 10, 15, 25] });
      return r.rows.map(x => BALS.answer({ yd: x.yd, dropIn: x.dropIn, windIn: 0 }, { type: 'dot' }).elev.main); }""")
    assert [r[1] for r in got] == want
    assert [r[1] for r in got] == ['Hold 1.4 in high', 'Hold 1.3 in high', 'Hold 1.2 in high', 'Hold 1.1 in high', 'Hold 0.9 in high', 'Hold 0.6 in high']


@pytest.mark.parametrize('profile', ['p556m193', 'p556ss109', 'p223', 'p76239sb', 'p65cm', 'p308'])
def test_every_hold_is_high_for_a_100_yard_zero(page, app_url, profile):
    open_screen(page, app_url, profile=profile)
    open_sheet(page)
    got = rows(page)
    assert [r[0] for r in got] == YDS
    for yd, hold in got:
        assert hold.startswith('Hold ') and hold.endswith(' in high'), (profile, yd, hold)


@pytest.mark.parametrize('sight', [0, None], ids=['zero', 'blank'])
def test_no_sight_height_says_so(page, app_url, sight):
    mine = {**LOAD, 'id': 'unosh', 'name': 'No sight height'}
    if sight is None:
        del mine['sight']
    else:
        mine['sight'] = sight
    open_screen(page, app_url, profile='unosh', profiles=[mine])
    open_sheet(page)
    expect(page.locator('#clNoSight')).to_have_text(NO_SIGHT)
    expect(page.locator('#clSight')).to_have_text('Sight height not set · zero 100 yd')
    got = rows(page)
    assert [r[0] for r in got] == YDS                       # shown, not blocked
    want = page.evaluate("""() => BALZ.close(FK.bal.load()).rows.map(r => BALS.answer({ yd: r.yd, dropIn: r.dropIn, windIn: 0 }, { type: 'dot' }).elev.main)""")
    assert [r[1] for r in got] == want                      # the solver's own figures, never replaced
    assert any(h != 'Hold on' for h in want), want          # and at least one is a real hold (25 yd reads low with the sight on the bore)


def test_the_no_sight_line_is_hidden_when_there_is_a_sight(page, app_url):
    open_screen(page, app_url)
    open_sheet(page)
    expect(page.locator('#clNoSight')).to_be_hidden()
    expect(page.locator('#clMsg')).to_be_hidden()


def test_unusable_profile_shows_the_message_and_no_table(page, app_url):
    bad = {**LOAD, 'id': 'ubad', 'name': 'Broken load', 'bc': 0}
    open_screen(page, app_url, profile='ubad', profiles=[bad])
    open_sheet(page)
    expect(page.locator('#clMsg')).to_have_text(PROFILE_MSG)
    expect(page.locator('#clTable')).to_be_hidden()
    expect(page.locator('#clNote')).to_be_hidden()
    expect(page.locator('#clProfile')).to_have_text('Broken load')
    assert rows(page) == []


def test_bad_conditions_show_the_conditions_message(page, app_url):
    open_screen(page, app_url)
    page.click('#bCondBtn')
    shot_now(page, bTemp=500)
    open_sheet(page)
    expect(page.locator('#clMsg')).to_have_text(COND_MSG)
    expect(page.locator('#clTable')).to_be_hidden()
    assert rows(page) == []
    # The sheet reads the profile and the air when it opens: mend the air, open it again.
    page.click('#clClose')
    wait_closed(page)
    shot_now(page, bTemp=59)
    open_sheet(page, again=True)
    expect(page.locator('#clMsg')).to_be_hidden()
    assert [r[0] for r in rows(page)] == YDS


def test_the_load_helper_answers_with_the_screens_own_messages(page, app_url):
    open_screen(page, app_url)
    load = page.evaluate('FK.bal.load()')
    assert 'error' not in load
    assert {k: load[k] for k in ('bc', 'model', 'w', 'mv', 'sight', 'zero')} == {'bc': 0.25, 'model': 'G7', 'w': 175, 'mv': 2600, 'sight': 1.5, 'zero': 100}
    assert {k: load[k] for k in ('temp', 'alt', 'press', 'rh')} == {'temp': 59, 'alt': 0, 'press': 0, 'rh': 50}
    assert sorted(load) == sorted(['bc', 'model', 'w', 'mv', 'sight', 'zero', 'zeroAtm', 'temp', 'alt', 'press', 'rh'])
    page.evaluate('FK.bal.save({ id: "ubad", name: "Broken load", bc: 0, mv: 2600, zero: 100, model: "G7" })')
    page.evaluate('FK.bal.select("ubad")')
    assert page.evaluate('FK.bal.load()') == {'error': PROFILE_MSG}


def test_profile_name_is_text_not_markup(page, app_url):
    evil = {**LOAD, 'id': 'uevil', 'name': '<img src=x onerror="window.pwned=1"><b>bold</b>'}
    open_screen(page, app_url, profile='uevil', profiles=[evil])
    open_sheet(page)
    expect(page.locator('#clProfile')).to_have_text(evil['name'])
    assert page.evaluate("document.querySelectorAll('#dlgClose img, #dlgClose b').length") == 0
    assert page.evaluate('window.pwned') is None


def test_the_sheet_never_prints_nan_or_minus_zero(page, app_url):
    for profile, profiles in (('p308', []), ('ubad', [{**LOAD, 'id': 'ubad', 'name': 'Broken', 'bc': 0}]), ('uz', [{**LOAD, 'id': 'uz', 'name': 'Flat', 'sight': 0}])):
        open_screen(page, app_url, profile=profile, profiles=profiles)
        open_sheet(page)
        assert not NASTY.search(page.inner_text(DLG)), profile


def test_back_and_close_both_close_it_and_leave_the_screen_as_it_was(page, app_url):
    open_screen(page, app_url)
    reach_tools(page)
    before = page.evaluate(STATE)
    open_sheet(page)
    assert page.evaluate(STATE)[2] is True                 # it owns one history entry
    page.go_back()
    wait_closed(page)
    expect(page.locator(DLG)).to_be_hidden()
    assert page.evaluate(STATE) == before
    expect(page.locator('#bClose')).to_be_visible()
    open_sheet(page, again=True)
    page.click('#clClose')
    wait_closed(page)
    expect(page.locator(DLG)).to_be_hidden()
    assert page.evaluate(STATE) == before
    assert page.evaluate('FK.view()') == 'ballistics'


def test_escape_and_a_tap_outside_close_it_too(page, app_url):
    open_screen(page, app_url)
    reach_tools(page)
    before = page.evaluate(STATE)
    open_sheet(page)
    page.keyboard.press('Escape')
    wait_closed(page)
    expect(page.locator(DLG)).to_be_hidden()
    assert page.evaluate(STATE) == before
    open_sheet(page, again=True)
    page.mouse.click(180, 10)                              # the backdrop above the sheet
    wait_closed(page)
    expect(page.locator(DLG)).to_be_hidden()
    assert page.evaluate(STATE) == before


@pytest.mark.parametrize('night', [False, True], ids=['day', 'night'])
def test_fits_360_day_night_with_enlarged_text_and_44px_controls(page, app_url, night):
    long_name = {**LOAD, 'id': 'ulong', 'name': 'A rather long profile name that goes on and on and on and on and on', 'sight': 2.6}
    open_screen(page, app_url, profile='ulong', profiles=[long_name], night=night)
    assert overflow(page, '#view-ballistics') == []
    assert too_small(page, '#view-ballistics') == []
    assert clipped_buttons(page, '#view-ballistics') == []
    open_sheet(page)
    assert page.evaluate("document.documentElement.dataset.theme === 'night'") == night
    assert overflow(page, DLG) == []
    assert too_small(page, DLG) == []
    assert clipped_buttons(page, DLG) == []
    enlarge_text(page)
    assert overflow(page, DLG) == []
    assert clipped_buttons(page, DLG) == []
    assert too_small(page, DLG) == []
    box = page.locator('#clClose').bounding_box()           # the button is on the screen and the table scrolls inside the sheet
    assert box['y'] >= 0 and box['y'] + box['height'] <= 640 and box['x'] >= 0 and box['x'] + box['width'] <= 360
    top = page.locator('#clTitle').bounding_box()
    assert top['y'] >= 0
    # the same with no sight height (the extra line) and with a message in place of the table
    page.click('#clClose')
    wait_closed(page)


def test_fits_360_with_the_no_sight_line_and_a_message(page, app_url):
    flat = {**LOAD, 'id': 'uflat', 'name': 'Flat', 'sight': 0}
    bad = {**LOAD, 'id': 'ubad', 'name': 'Broken', 'bc': 0}
    for pid in ('uflat', 'ubad'):
        open_screen(page, app_url, profile=pid, profiles=[flat, bad])
        open_sheet(page)
        enlarge_text(page)
        assert overflow(page, DLG) == [] and clipped_buttons(page, DLG) == [] and too_small(page, DLG) == [], pid
        box = page.locator('#clClose').bounding_box()
        assert box['y'] + box['height'] <= 640, pid


def test_the_tools_block_does_not_move_the_first_screen(page, app_url):
    open_screen(page, app_url)
    top = page.evaluate("document.querySelector('#bWind').getBoundingClientRect().top")
    assert top == pytest.approx(V711_WIND_TOP, abs=0.5)
    assert page.evaluate('scrollY') == 0
    # the block is under the dope card, after the line about spin drift
    order = page.evaluate("""() => [...document.querySelectorAll('#view-ballistics [id]')].map(e => e.id).filter(i => ['bSpin', 'bClose', 'bZeros'].includes(i))""")
    assert order == ['bSpin', 'bClose', 'bZeros']
    expect(page.locator('#bClose')).to_have_text('Close-range holds')
    expect(page.locator('#bZeros')).to_have_text('Compare zeros')
    expect(page.locator('#bZeros')).to_be_hidden()           # Task 6 wires it
