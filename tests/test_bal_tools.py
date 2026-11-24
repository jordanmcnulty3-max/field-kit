"""The Tools block under the dope card and its two sheets: Close-range holds (six rows from the solver, worded as the red dot answer is)
and Compare zeros (two or three zero ranges side by side, and Use this zero on the person's own profile)."""
import math
import re

import pytest
from playwright.sync_api import expect

from .test_bal_screen import LOAD, NASTY, open_screen, shot_now
from .test_tactical_layout import clipped_buttons, contrast_ratio, enlarge_text, overflow, too_small

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
    expect(page.locator('#bZeros')).to_be_visible()          # Task 6 wired it


# ---------- Task 5 review items: the Close-range sheet with nothing to show, and with an unusable profile ----------

def test_no_rows_and_no_error_says_so_and_hides_the_table(page, app_url):
    open_screen(page, app_url)
    page.evaluate("BALZ.close = () => ({ rows: [] })")        # the solver gave nothing for the six ranges (and no error)
    open_sheet(page)
    expect(page.locator('#clMsg')).to_have_text('No holds to show for this profile.')
    expect(page.locator('#clTable')).to_be_hidden()
    expect(page.locator('#clNote')).to_be_hidden()
    assert rows(page) == []


def test_an_unusable_profile_does_not_print_the_sight_line(page, app_url):
    bad = {**LOAD, 'id': 'ubad', 'name': 'Broken load', 'bc': 0}
    open_screen(page, app_url, profile='ubad', profiles=[bad])
    open_sheet(page)
    expect(page.locator('#clMsg')).to_have_text(PROFILE_MSG)
    expect(page.locator('#clSight')).to_be_hidden()
    expect(page.locator('#clNoSight')).to_be_hidden()
    expect(page.locator('#clProfile')).to_have_text('Broken load')


# ---------- Compare zeros ----------

ZDLG = '#dlgZeros'
BOXES = ['25', '36', '50', '100', '200']
TOO_FEW = 'Pick two or three zeros.'
TOO_MANY = 'Up to three at a time.'
BAD_OTHER = 'Enter a zero from 10 to 300 yd.'
KEY = 'Inches above the line of sight; a minus means below. Level, no wind.'
BUILTIN_LINE = "Built-in loads can't be changed. Tap Edit, set the zero range and save it as a new profile."
SET_TEXT = 'The card changes now. The rifle itself still has to be re-zeroed at the range.'
MINE = {**LOAD, 'id': 'umine', 'name': 'My .308', 'zero': 100, 'zeroAtm': {'temp': 40, 'alt': 500, 'rh': 30}, 'mv0': 2550, 'twist': 10, 'blen': 1.2, 'bdia': 0.308}
# Browser side: a cell the way the sheet words it, and a column's summary data with the numbers already written out.
FX_JS = "const fx = v => v === null ? '\\u2014' : (t => /^-0(\\.0+)?$/.test(t) ? t.slice(1) : t)(v.toFixed(1));"


def open_zeros(page, again=False):
    if again:
        page.locator('#bZeros').dispatch_event('click')
    else:
        page.click('#bZeros')
    expect(page.locator(ZDLG)).to_be_visible()


def ticked(page):
    return page.evaluate("[...document.querySelectorAll('#dlgZeros input[type=checkbox]:checked')].map(c => c.value)")


def pick(page, ticks, other=''):
    """Set the boxes and the Other field the way a person does: real taps (the limit of three applies), unticks first."""
    want = [str(t) for t in ticks]
    for b in BOXES:
        if b not in want and page.locator(f'#zs{b}').is_checked():
            page.locator(f'#zs{b}').click()
    for b in BOXES:
        if b in want and not page.locator(f'#zs{b}').is_checked():
            page.locator(f'#zs{b}').click()
    page.fill('#zsOther', str(other))


def ztable(page):
    return page.evaluate("""() => ({ head: [...document.querySelectorAll('#zsTable th')].map(c => c.textContent),
      rows: [...document.querySelectorAll('#zsTable tbody tr')].map(r => [...r.children].map(c => c.textContent)) })""")


def zlines(page):
    return page.evaluate("[...document.querySelectorAll('#zsLines li')].map(l => l.textContent)")


def zbuttons(page):
    return page.evaluate("[...document.querySelectorAll('#zsUse button')].map(b => b.textContent)")


def want_table(page, zeros):
    """What the sheet must print for these zeros, worked out from BALZ in the page (zeros in the order they appear: smallest first)."""
    return page.evaluate("zs => { " + FX_JS + """
      const r = BALZ.compare(FK.bal.load(), zs);
      return { head: ['Yd', ...r.cols.map(c => Number(c.zero.toFixed(1)) + ' yd zero')],
               rows: BALZ.YDS.map((y, i) => [String(y), ...r.cols.map(c => fx(c.path[i]))]) }; }""", zeros)


def want_lines(page, zeros):
    """The summary sentences, written here from BALZ's own figures (the shapes are asserted by each test)."""
    cols = page.evaluate("zs => BALZ.compare(FK.bal.load(), zs).cols.map(c => ({ zero: c.zero, other: c.other, past: c.past, peak: c.peak && { yd: c.peak.yd, p: c.peak.pathIn.toFixed(1) } }))", zeros)
    out = []
    for c in cols:
        n = f"{c['zero']:g} yd zero"
        if c['other'] is not None and c['peak']:
            out.append(f"{n}: crosses the line of sight again at {c['other']} yd. Highest {c['peak']['p']} in above it, at {c['peak']['yd']} yd.")
        elif c['other'] is not None:
            out.append(f"{n}: crosses the line of sight again at {c['other']} yd.")
        elif c['past']:
            out.append(f"{n}: does not cross it again inside 500 yd.")
        elif not c['peak']:
            out.append(f"{n}: touches the line of sight there and stays below it.")
        else:
            out.append(f"{n}: does not cross it again before the bullet runs out of reach.")
    return cols, out


def own(pid='umine', **over):
    return {**MINE, 'id': pid, **over}


def test_opens_with_the_profiles_zero_and_two_more(page, app_url):
    for zero, boxes, other in [(100, ['50', '100', '200'], ''), (50, ['36', '50', '200'], ''), (200, ['36', '50', '200'], ''),
                               (36, ['36', '50', '200'], ''), (25, ['25', '50', '200'], ''), (75, ['50', '200'], '75'), (87.5, ['50', '200'], '87.5'), (87.25, ['50', '200'], '87.3'), (100.04, ['50', '100', '200'], '')]:
        open_screen(page, app_url, profile='umine', profiles=[own(zero=zero)])
        open_zeros(page)
        assert ticked(page) == boxes, zero
        assert page.input_value('#zsOther') == other, zero
        expect(page.locator('#zsMsg')).to_be_hidden()
        assert len(ztable(page)['head']) == 4, zero
    open_screen(page, app_url)                         # a built-in load opens the same way
    open_zeros(page)
    assert ticked(page) == ['50', '100', '200']
    expect(page.locator('#zsTitle')).to_have_text('Compare zeros')
    expect(page.locator('#zsProfile')).to_have_text('Federal Gold Medal .308 Win 175 gr SMK, 24″ barrel')
    expect(page.locator('#zsKey')).to_have_text(KEY)
    expect(page.locator('#zsClose')).to_have_text('Close')


def test_the_other_field_is_a_decimal_number_field_with_a_visible_label(page, app_url):
    open_screen(page, app_url)
    open_zeros(page)
    other = page.locator('#zsOther')
    assert other.get_attribute('type') == 'number' and other.get_attribute('inputmode') == 'decimal'
    expect(page.locator('label:has(#zsOther)')).to_contain_text('Other (yd)')
    for b in BOXES:                                    # real labels, one per box
        assert page.locator(f'label:has(#zs{b})').count() == 1
        expect(page.locator(f'label:has(#zs{b})')).to_have_text(f'{b} yd')


def test_table_cells_match_BALZ(page, app_url):
    open_screen(page, app_url)
    open_zeros(page)
    assert ztable(page) == want_table(page, [50, 100, 200])
    got = ztable(page)
    assert got['head'] == ['Yd', '50 yd zero', '100 yd zero', '200 yd zero']
    assert [r[0] for r in got['rows']] == [str(y) for y in page.evaluate('BALZ.YDS')] and len(got['rows']) == 16
    pick(page, [36, 200])
    assert ztable(page) == want_table(page, [36, 200])
    assert len(ztable(page)['head']) == 3
    pick(page, [25, 36], '87.5')
    assert ztable(page) == want_table(page, [25, 36, 87.5])
    assert ztable(page)['head'][-1] == '87.5 yd zero'
    cells = [c for r in ztable(page)['rows'] for c in r[1:]]
    assert any(c.startswith('-') for c in cells) and any(c and c[0].isdigit() for c in cells)     # below and above the line of sight
    assert not any(NASTY.search(c) for c in cells)


def test_a_bullet_that_does_not_reach_prints_a_dash(page, app_url):
    open_screen(page, app_url)
    # a load that stops inside 175 yd: the sheet reads the load when it opens
    page.evaluate("""() => { const real = FK.bal.load; FK.bal.load = () => Object.assign(real(), { bc: 0.01, model: 'G1', mv: 400, sight: 1.5 }); }""")
    open_zeros(page)
    pick(page, [25, 36])                                  # zeros the bullet can reach
    got = ztable(page)
    assert got == want_table(page, [25, 36])
    flat = [c for r in got['rows'] for c in r[1:]]
    assert '—' in flat and any(c != '—' for c in flat)
    assert [r[1] for r in got['rows']][-1] == '—'          # nothing at 300 yd
    assert not NASTY.search(page.inner_text(ZDLG))


def test_summary_lines_for_other_past_and_touch(page, app_url):
    open_screen(page, app_url, profile='p556m193')
    open_zeros(page)
    shapes_seen = set()
    for ticks, other in [([36], '10'), ([36], '105'), ([200], '111.5')]:
        pick(page, ticks, other)
        zs = sorted([float(t) for t in ticks] + [float(other)])
        cols, want = want_lines(page, zs)
        assert zlines(page) == want, (ticks, other)
        for c in cols:
            shapes_seen.add(('both' if c['other'] is not None and c['peak'] else 'other' if c['other'] is not None else 'past' if c['past'] else 'touch' if not c['peak'] else 'short'))
    assert shapes_seen == {'both', 'other', 'past', 'touch'}
    # the figures the brief quotes for this load
    pick(page, [36, 100])
    lines = zlines(page)
    assert lines[0].startswith('36 yd zero: crosses the line of sight again at 326 yd. Highest 5.5 in above it, at 191 yd.')
    assert lines[1].startswith('100 yd zero: crosses the line of sight again at 134 yd. Highest 0.1 in above it, at ')


def test_a_past_zero_never_prints_a_highest_point(page, app_url):
    open_screen(page, app_url, profile='p556m193')
    open_zeros(page)
    pick(page, [36], '10')
    ten = [l for l in zlines(page) if l.startswith('10 yd zero')]
    assert ten == ['10 yd zero: does not cross it again inside 500 yd.']
    assert all('Highest' not in l for l in ten)


def test_a_bullet_that_runs_out_of_reach_above_the_line_says_so(page, app_url):
    slow = own('uslow', name='Slow', bc=0.05, model='G1', mv=300, sight=1.5, zero=80, zeroAtm=None, mv0=None, twist=None, blen=None, bdia=None)
    for k in [k for k, v in slow.items() if v is None]:
        del slow[k]
    open_screen(page, app_url, profile='uslow', profiles=[slow])
    open_zeros(page)
    assert page.input_value('#zsOther') == '80'
    pick(page, [50], '80')
    cols, want = want_lines(page, [50, 80])
    assert cols[1]['other'] is None and cols[1]['past'] is False and cols[1]['peak'] is not None      # the shape under test
    assert zlines(page) == want
    assert want[1] == '80 yd zero: does not cross it again before the bullet runs out of reach.'


def test_one_zero_and_four_zeros_are_refused_with_their_messages(page, app_url):
    open_screen(page, app_url)
    open_zeros(page)
    # a fourth tick is refused: it does not stay ticked, the three stay, the table is the three
    page.locator('#zs25').click()
    assert ticked(page) == ['50', '100', '200']
    expect(page.locator('#zsMsg')).to_have_text(TOO_MANY)
    assert ztable(page) == want_table(page, [50, 100, 200])
    # the message goes when the person goes on
    page.locator('#zs200').click()
    expect(page.locator('#zsMsg')).to_be_hidden()
    assert ztable(page) == want_table(page, [50, 100])
    # one is not enough: the message, and no table
    page.locator('#zs100').click()
    assert ticked(page) == ['50']
    expect(page.locator('#zsMsg')).to_have_text(TOO_FEW)
    expect(page.locator('#zsTable')).to_be_hidden()
    expect(page.locator('#zsKey')).to_be_hidden()
    assert zlines(page) == [] and zbuttons(page) == []
    assert ztable(page) == {'head': [], 'rows': []}
    # none at all
    page.locator('#zs50').click()
    expect(page.locator('#zsMsg')).to_have_text(TOO_FEW)
    # and back to two: the table returns
    pick(page, [36, 50])
    expect(page.locator('#zsMsg')).to_be_hidden()
    assert ztable(page) == want_table(page, [36, 50])


def test_a_typed_fourth_zero_is_left_out_with_the_same_message(page, app_url):
    open_screen(page, app_url)
    open_zeros(page)
    page.fill('#zsOther', '75')
    expect(page.locator('#zsMsg')).to_have_text(TOO_MANY)
    assert ztable(page) == want_table(page, [50, 100, 200])
    page.locator('#zs50').click()
    expect(page.locator('#zsMsg')).to_be_hidden()
    assert ztable(page) == want_table(page, [75, 100, 200])


def test_typed_zero_same_as_a_ticked_one_counts_once(page, app_url):
    open_screen(page, app_url)
    open_zeros(page)
    for typed in ('50', '100', '100.0', '200.00', '100.04'):
        page.fill('#zsOther', typed)
        expect(page.locator('#zsMsg')).to_be_hidden()
        assert ztable(page) == want_table(page, [50, 100, 200]), typed
    pick(page, [50], '50')                               # one ticked and the same typed: one zero, so too few
    expect(page.locator('#zsMsg')).to_have_text(TOO_FEW)
    page.locator('#zs100').click()
    expect(page.locator('#zsMsg')).to_be_hidden()
    assert ztable(page) == want_table(page, [50, 100])


def test_junk_or_out_of_range_other_is_refused(page, app_url):
    open_screen(page, app_url)
    open_zeros(page)
    pick(page, [50, 100])
    base = want_table(page, [50, 100])
    for typed in ('5', '9.9', '9.95', '9.99', '300.01', '300.04', '301', '1000', '0', '-20'):
        page.fill('#zsOther', typed)
        expect(page.locator('#zsMsg')).to_have_text(BAD_OTHER)
        assert ztable(page) == base, typed               # left out: the two ticked zeros are still compared
    page.fill('#zsOther', '')
    page.locator('#zsOther').press_sequentially('1e')    # the browser keeps no value for this: it is unreadable
    assert page.evaluate("document.querySelector('#zsOther').validity.badInput") is True
    expect(page.locator('#zsMsg')).to_have_text(BAD_OTHER)
    assert ztable(page) == base
    page.fill('#zsOther', '')                            # blank is simply not used
    expect(page.locator('#zsMsg')).to_be_hidden()
    for typed, zs in (('10', [10, 50, 100]), ('300', [50, 100, 300]), ('10.0', [10, 50, 100]), ('300.00', [50, 100, 300]), ('150.5', [50, 100, 150.5])):    # the edges are inside, 9.99 and 300.01 are not
        page.fill('#zsOther', typed)
        expect(page.locator('#zsMsg')).to_be_hidden()
        assert ztable(page) == want_table(page, zs), typed
    # blank Other with only one box: the count message, not a complaint about the empty field
    pick(page, [50])
    expect(page.locator('#zsMsg')).to_have_text(TOO_FEW)


def test_use_this_zero_asks_then_writes_the_profile_and_the_card(page, app_url):
    open_screen(page, app_url, profile='umine', profiles=[own()])
    before = page.evaluate("JSON.parse(localStorage.getItem('fk.profiles'))")
    assert before[0]['zero'] == 100 and before[0]['mv0'] == 2550 and before[0]['zeroAtm']
    open_zeros(page)
    assert zbuttons(page) == ['Use 50 yd zero', 'Use 200 yd zero']          # not the zero it already has
    page.locator('#zsUse button', has_text='Use 50 yd zero').click()
    expect(page.locator('#dlgConfirm')).to_be_visible()
    expect(page.locator('#cfTitle')).to_have_text('Set the zero to 50 yd?')
    expect(page.locator('#cfText')).to_have_text(SET_TEXT)
    expect(page.locator('#cfOk')).to_have_text('Set zero')
    assert page.evaluate("JSON.parse(localStorage.getItem('fk.profiles'))") == before      # nothing written until yes
    page.click('#cfOk')
    expect(page.locator('#zsMsg')).to_have_text('Zero set to 50 yd')
    after = page.evaluate("JSON.parse(localStorage.getItem('fk.profiles'))")
    assert after[0]['zero'] == 50
    assert {k: v for k, v in after[0].items() if k != 'zero'} == {k: v for k, v in before[0].items() if k != 'zero'}     # zeroAtm, mv0, sight, spin fields kept
    expect(page.locator('#toast')).to_have_text('Zero set to 50 yd')
    expect(page.locator('#bLoad')).to_contain_text('zero 50 yd')
    # the sheet stays, redrawn: the button for the zero it now has is gone, the one for the old zero is there
    expect(page.locator(ZDLG)).to_be_visible()
    assert page.evaluate("FK.sheet.top() && FK.sheet.top().id") == 'dlgZeros'
    assert zbuttons(page) == ['Use 100 yd zero', 'Use 200 yd zero']
    assert ticked(page) == ['50', '100', '200']
    assert ztable(page) == want_table(page, [50, 100, 200])
    expect(page.locator('#zsNow')).to_have_text('Current zero: 50 yd')
    page.click('#zsClose')
    wait_closed(page)
    assert page.evaluate("history.state && !!history.state.fkSheet") is False


def test_declining_the_question_changes_nothing(page, app_url):
    open_screen(page, app_url, profile='umine', profiles=[own()])
    before = page.evaluate("localStorage.getItem('fk.profiles')")
    open_zeros(page)
    page.locator('#zsUse button', has_text='Use 200 yd zero').click()
    expect(page.locator('#cfTitle')).to_have_text('Set the zero to 200 yd?')
    page.click('#cfCancel')
    expect(page.locator('#dlgConfirm')).to_be_hidden()
    page.evaluate('new Promise(done => FK.sheet.afterStep(done))')
    assert page.evaluate("localStorage.getItem('fk.profiles')") == before
    assert page.evaluate("FK.sheet.top() && FK.sheet.top().id") == 'dlgZeros'
    assert zbuttons(page) == ['Use 50 yd zero', 'Use 200 yd zero']
    expect(page.locator('#zsMsg')).to_be_hidden()
    expect(page.locator('#toast')).not_to_have_text('Zero set to 200 yd')


def test_storage_full_leaves_the_profile_and_the_sheet(page, app_url):
    open_screen(page, app_url, profile='umine', profiles=[own()])
    before = page.evaluate("localStorage.getItem('fk.profiles')")
    open_zeros(page)
    page.evaluate("""() => { const o = Storage.prototype.setItem;
      Storage.prototype.setItem = function (k, v) { if (k === 'fk.profiles') throw new DOMException('full', 'QuotaExceededError'); return o.call(this, k, v); }; }""")
    page.locator('#zsUse button', has_text='Use 50 yd zero').click()
    page.click('#cfOk')
    expect(page.locator('#toast')).to_contain_text('storage for Field Kit is full')
    page.evaluate('new Promise(done => FK.sheet.afterStep(done))')
    assert page.evaluate("localStorage.getItem('fk.profiles')") == before
    assert page.evaluate('FK.bal.selected().zero') == 100
    expect(page.locator('#bLoad')).not_to_contain_text('zero 50 yd')
    expect(page.locator(ZDLG)).to_be_visible()
    expect(page.locator('#zsMsg')).to_be_hidden()               # no "Zero set to" when nothing was saved
    assert page.evaluate("document.querySelector('#dlgZeros').inert") is False
    assert zbuttons(page) == ['Use 50 yd zero', 'Use 200 yd zero']
    expect(page.locator('#zsNow')).to_have_text('Current zero: 100 yd')


def test_back_closes_the_question_first_then_the_sheet(page, app_url):
    open_screen(page, app_url, profile='umine', profiles=[own()])
    reach_tools(page)
    before_state = page.evaluate(STATE)
    page.evaluate("const g = history.go.bind(history); history.go = k => { setTimeout(() => g(k), 250); }; 0")     # a slow phone
    stored = page.evaluate("localStorage.getItem('fk.profiles')")
    open_zeros(page)
    page.locator('#zsUse button', has_text='Use 50 yd zero').click()
    expect(page.locator('#dlgConfirm')).to_be_visible()
    page.go_back()                                              # the question closes, the sheet stays
    expect(page.locator('#dlgConfirm')).to_be_hidden()
    page.evaluate('new Promise(done => FK.sheet.afterStep(done))')
    expect(page.locator(ZDLG)).to_be_visible()
    assert page.evaluate("FK.sheet.top() && FK.sheet.top().id") == 'dlgZeros'
    assert page.evaluate("localStorage.getItem('fk.profiles')") == stored
    expect(page.locator('#zsMsg')).to_be_hidden()
    page.go_back()                                              # now the sheet
    expect(page.locator(ZDLG)).to_be_hidden()
    wait_closed(page)
    assert page.evaluate(STATE) == before_state
    assert page.evaluate("localStorage.getItem('fk.profiles')") == stored


def test_pressing_use_twice_quickly_asks_once_and_saves_once(page, app_url):
    open_screen(page, app_url, profile='umine', profiles=[own()])
    open_zeros(page)
    page.evaluate("""() => { window.__w = 0; const o = Storage.prototype.setItem;
      Storage.prototype.setItem = function (k, v) { if (k === 'fk.profiles') window.__w++; return o.call(this, k, v); }; }""")
    page.evaluate("() => { const b = [...document.querySelectorAll('#zsUse button')].find(x => x.textContent === 'Use 50 yd zero'); b.click(); b.click(); }")
    expect(page.locator('#dlgConfirm')).to_be_visible()
    page.click('#cfOk')
    expect(page.locator('#zsMsg')).to_have_text('Zero set to 50 yd')
    page.evaluate('new Promise(done => FK.sheet.afterStep(done))')
    assert page.evaluate('window.__w') == 1
    assert page.evaluate('FK.bal.selected().zero') == 50
    assert page.evaluate("history.state && history.state.fkSheet") == 'dlgZeros'     # one sheet entry, the question's is gone
    # pressing "Set zero" twice quickly saves once as well
    page.locator('#zsUse button', has_text='Use 200 yd zero').click()
    page.evaluate("() => { const b = document.querySelector('#cfOk'); b.click(); b.click(); }")
    expect(page.locator('#zsMsg')).to_have_text('Zero set to 200 yd')
    page.evaluate('new Promise(done => FK.sheet.afterStep(done))')
    assert page.evaluate('window.__w') == 2
    assert page.evaluate('FK.bal.selected().zero') == 200


def test_a_profile_whose_zero_is_compared_has_no_button_for_it(page, app_url):
    open_screen(page, app_url, profile='umine', profiles=[own(zero=75)])
    open_zeros(page)
    assert ticked(page) == ['50', '200'] and page.input_value('#zsOther') == '75'
    assert zbuttons(page) == ['Use 50 yd zero', 'Use 200 yd zero']
    pick(page, [36, 50], '120')                                  # the profile's own zero (75) is not compared at all: a button for each
    assert zbuttons(page) == ['Use 36 yd zero', 'Use 50 yd zero', 'Use 120 yd zero']
    page.locator('#zsUse button', has_text='Use 120 yd zero').click()
    expect(page.locator('#cfTitle')).to_have_text('Set the zero to 120 yd?')
    page.click('#cfOk')
    expect(page.locator('#zsMsg')).to_have_text('Zero set to 120 yd')
    assert page.evaluate('FK.bal.selected().zero') == 120
    assert zbuttons(page) == ['Use 36 yd zero', 'Use 50 yd zero']


def test_builtin_load_has_no_use_buttons_and_says_why(page, app_url):
    open_screen(page, app_url)
    open_zeros(page)
    assert zbuttons(page) == []
    expect(page.locator('#zsBuiltin')).to_have_text(BUILTIN_LINE)
    expect(page.locator('#zsUse')).to_be_hidden()
    # a person's own profile is the other way round
    open_screen(page, app_url, profile='umine', profiles=[own()])
    open_zeros(page)
    expect(page.locator('#zsBuiltin')).to_be_hidden()
    expect(page.locator('#zsUse')).to_be_visible()


def test_unusable_profile_shows_the_message_and_nothing_to_compare(page, app_url):
    bad = {**LOAD, 'id': 'ubad', 'name': 'Broken load', 'bc': 0}
    open_screen(page, app_url, profile='ubad', profiles=[bad])
    open_zeros(page)
    expect(page.locator('#zsMsg')).to_have_text(PROFILE_MSG)
    expect(page.locator('#zsTable')).to_be_hidden()
    expect(page.locator('#zsKey')).to_be_hidden()
    expect(page.locator('#zsProfile')).to_have_text('Broken load')
    assert zlines(page) == [] and zbuttons(page) == [] and ztable(page) == {'head': [], 'rows': []}
    expect(page.locator('#zsBuiltin')).to_be_hidden()
    assert not NASTY.search(page.inner_text(ZDLG))
    # bad air: the screen's own message; mended, the sheet works again on the next open
    open_screen(page, app_url)
    page.click('#bCondBtn')
    shot_now(page, bTemp=500)
    open_zeros(page)
    expect(page.locator('#zsMsg')).to_have_text(COND_MSG)
    page.click('#zsClose')
    wait_closed(page)
    shot_now(page, bTemp=59)
    open_zeros(page, again=True)
    expect(page.locator('#zsMsg')).to_be_hidden()
    assert ztable(page) == want_table(page, [50, 100, 200])


def test_it_reads_the_profile_fresh_each_time_it_opens(page, app_url):
    open_screen(page, app_url, profile='umine', profiles=[own()])
    open_zeros(page)
    assert ticked(page) == ['50', '100', '200']
    page.click('#zsClose')
    wait_closed(page)
    page.evaluate('FK.bal.save({ ...FK.bal.selected(), zero: 75 })')
    open_zeros(page, again=True)
    assert ticked(page) == ['50', '200'] and page.input_value('#zsOther') == '75'


def test_profile_name_is_text_not_markup_here_too(page, app_url):
    evil = own('uevil', name='<img src=x onerror="window.pwned=1"><b>bold</b>')
    open_screen(page, app_url, profile='uevil', profiles=[evil])
    open_zeros(page)
    expect(page.locator('#zsProfile')).to_have_text(evil['name'])
    assert page.evaluate("document.querySelectorAll('#dlgZeros img, #dlgZeros b').length") == 0
    page.locator('#zsUse button', has_text='Use 50 yd zero').click()
    expect(page.locator('#cfText')).to_have_text(SET_TEXT)
    assert page.evaluate('window.pwned') is None


@pytest.mark.parametrize('night', [False, True], ids=['day', 'night'])
@pytest.mark.parametrize('count', [2, 3])
def test_zeros_sheet_fits_360_day_night_with_enlarged_text(page, app_url, night, count):
    long_name = own('ulong', name='A rather long profile name that goes on and on and on and on and on', zero=87.5)
    open_screen(page, app_url, profile='ulong', profiles=[long_name], night=night)
    open_zeros(page)
    assert page.evaluate("document.documentElement.dataset.theme === 'night'") == night
    pick(page, [100, 200] if count == 3 else [100], '87.5' if count == 3 else '')
    if count == 2:
        pick(page, [100, 200])
    assert len(ztable(page)['head']) == count + 1

    def check():
        assert overflow(page, ZDLG) == []
        assert too_small(page, ZDLG) == []
        assert clipped_buttons(page, ZDLG) == []
        # the table fits its box, or it carries the swipe cue (never a silent cut-off)
        fit = page.evaluate("""() => { const w = document.querySelector('#zsWrap'); return { wide: w.scrollWidth > w.clientWidth + 1, cue: !document.querySelector('#zsCue').hidden }; }""")
        assert fit['cue'] == fit['wide'], fit
        box = page.locator('#zsClose').bounding_box()           # the button stays on the screen; the body scrolls inside the sheet
        assert box['y'] >= 0 and box['y'] + box['height'] <= 640 and box['x'] >= 0 and box['x'] + box['width'] <= 360
        assert page.locator('#zsTitle').bounding_box()['y'] >= 0

    check()
    enlarge_text(page)
    page.evaluate("dispatchEvent(new Event('resize'))")
    check()
    # with enlarged text three zeros do not fit 328 px: the cue is on, and the first column is the yard column
    if count == 3:
        assert page.evaluate("!document.querySelector('#zsCue').hidden")
        expect(page.locator('#zsCue')).to_have_text('Swipe sideways to see more columns')
    # the Use buttons are reached by scrolling the body, and are 44 px or more high
    page.locator('#zsUse button').first.scroll_into_view_if_needed()
    assert page.locator('#zsUse button').first.bounding_box()['height'] >= 44


@pytest.mark.parametrize('night', [False, True], ids=['day', 'night'])
def test_zeros_sheet_with_a_message_fits_360(page, app_url, night):
    open_screen(page, app_url, night=night)
    open_zeros(page)
    pick(page, [50])
    page.fill('#zsOther', '301')
    enlarge_text(page)
    assert overflow(page, ZDLG) == [] and clipped_buttons(page, ZDLG) == [] and too_small(page, ZDLG) == []
    assert page.locator('#zsClose').bounding_box()['y'] + page.locator('#zsClose').bounding_box()['height'] <= 640
    expect(page.locator('#zsMsg')).to_have_text(BAD_OTHER)


@pytest.mark.parametrize('profile', ['p556m193', 'p556ss109', 'p223', 'p76239sb', 'p65cm', 'p308'])
def test_no_cell_or_line_is_nasty_for_any_builtin(page, app_url, profile):
    open_screen(page, app_url, profile=profile)
    open_zeros(page)
    for ticks, other in [([50, 200], ''), ([25, 36], '10'), ([100], '111.5'), ([200], '300'), ([36, 50], '10.5')]:
        pick(page, ticks, other)
        text = page.inner_text(ZDLG)
        assert not NASTY.search(text), (profile, ticks, other)
        cells = [c for r in ztable(page)['rows'] for c in r[1:]]
        assert cells and all(c == '—' or re.fullmatch(r'-?\d+\.\d', c) for c in cells), (profile, ticks, other)
        assert all(l.endswith('.') for l in zlines(page))


def test_the_sheet_does_not_change_what_the_screen_shows(page, app_url):
    open_screen(page, app_url)
    before = page.evaluate("[document.querySelector('#solElev').textContent, document.querySelector('#dope').textContent, localStorage.getItem('fk.bal')]")
    open_zeros(page)
    pick(page, [36, 100], '10')
    page.click('#zsClose')
    wait_closed(page)
    assert page.evaluate("[document.querySelector('#solElev').textContent, document.querySelector('#dope').textContent, localStorage.getItem('fk.bal')]") == before


@pytest.mark.parametrize('stored', [87.25, 100.04], ids=['87.25', '100.04'])
def test_a_zero_that_is_not_a_tenth_is_still_the_profiles_current_zero(page, app_url, stored):
    open_screen(page, app_url, profile='umine', profiles=[own(zero=stored)])
    before = page.evaluate("localStorage.getItem('fk.profiles')")
    shown = {87.25: '87.3', 100.04: '100'}[stored]
    open_zeros(page)
    expect(page.locator('#zsNow')).to_have_text(f'Current zero: {shown} yd')
    want = page.evaluate("""z => { """ + FX_JS + """
      const L = FK.bal.load(), r = BALZ.compare(L, [50, z, 200].sort((a, b) => a - b));
      return { head: ['Yd', ...r.cols.map(c => Number(c.zero.toFixed(1)) + ' yd zero')], rows: BALZ.YDS.map((y, i) => [String(y), ...r.cols.map(c => fx(c.path[i]))]) }; }""", stored)
    if stored == 87.25:
        assert ztable(page) == want and f'{shown} yd zero' in ztable(page)['head']
        assert page.evaluate("""() => { const L = FK.bal.load(), a = BALZ.compare(L, [87.25, 50]).cols.find(c => c.zero === 87.25);
          return L.zero === 87.25 && !!a; }""")
    assert zbuttons(page) == [b for b in ['Use 50 yd zero', 'Use 200 yd zero'] if b != f'Use {shown} yd zero']
    assert all(shown not in b for b in zbuttons(page))                      # no offer to "use" the zero it already has
    pick(page, [50, 200], shown)                                              # ticking and typing change nothing stored either
    assert all(f'Use {shown} yd' != b[:len(f'Use {shown} yd')] for b in zbuttons(page))
    page.click('#zsClose')
    wait_closed(page)
    assert page.evaluate("localStorage.getItem('fk.profiles')") == before
    assert page.evaluate('FK.bal.selected().zero') == stored


def test_the_current_zero_column_uses_the_stored_zero_for_its_maths(page, app_url):
    open_screen(page, app_url, profile='umine', profiles=[own(zero=87.25)])
    open_zeros(page)
    got = ztable(page)
    col = got['head'].index('87.3 yd zero')
    exact = page.evaluate("""() => { const r = BALZ.compare(FK.bal.load(), [50, 87.25, 200]); const c = r.cols[1];
      const t = BALZ.compare(FK.bal.load(), [50, 87.3, 200]).cols[1];
      return { exact: c.path.map(v => v === null ? null : Number(v.toFixed(1))), rounded: t.path.map(v => v === null ? null : Number(v.toFixed(1))) }; }""")
    cells = [float(r[col]) for r in got['rows']]
    assert cells == exact['exact']


def test_close_during_the_questions_step_does_not_drop_the_saved_zero(page, app_url):
    open_screen(page, app_url, profile='umine', profiles=[own()])
    page.evaluate("const g = history.go.bind(history); history.go = k => { setTimeout(() => g(k), 1200); }; 0")      # a slow phone
    open_zeros(page)
    box = page.locator('#zsClose').bounding_box()
    page.locator('#zsUse button', has_text='Use 50 yd zero').click()
    expect(page.locator('#dlgConfirm')).to_be_visible()
    page.click('#cfOk')
    page.wait_for_function("document.querySelector('#dlgZeros').inert === true")     # between Yes and the end of the question's step
    page.mouse.click(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)     # a real tap on Close: nothing is there to take it
    expect(page.locator('#zsMsg')).to_have_text('Zero set to 50 yd')
    assert page.evaluate('FK.bal.selected().zero') == 50
    page.evaluate('new Promise(done => FK.sheet.afterStep(done))')
    assert page.evaluate("document.querySelector('#dlgZeros').inert") is False
    expect(page.locator(ZDLG)).to_be_visible()
    assert page.evaluate("FK.sheet.top() && FK.sheet.top().id") == 'dlgZeros'
    assert page.evaluate("history.state && history.state.fkSheet") == 'dlgZeros'
    page.click('#zsClose')                                                           # and it closes normally afterwards
    wait_closed(page)
    expect(page.locator(ZDLG)).to_be_hidden()


def test_inert_is_cleared_when_the_profile_changed_or_the_sheet_went(page, app_url):
    open_screen(page, app_url, profile='umine', profiles=[own()])
    open_zeros(page)
    page.locator('#zsUse button', has_text='Use 50 yd zero').click()
    page.evaluate("FK.bal.save({ ...FK.bal.selected(), zero: 75 })")                 # the profile changes under the question
    page.click('#cfOk')
    page.evaluate('new Promise(done => FK.sheet.afterStep(done))')
    assert page.evaluate("document.querySelector('#dlgZeros').inert") is False
    assert page.evaluate('FK.bal.selected().zero') == 50            # same profile id: the saved zero is the one asked for
    page.click('#zsClose')
    wait_closed(page)
    page.evaluate("const g = history.go.bind(history); history.go = k => { setTimeout(() => g(k), 600); }; 0")
    open_zeros(page, again=True)
    zero_now = page.evaluate('FK.bal.selected().zero')
    page.locator('#zsUse button').first.click()
    page.click('#cfOk')
    page.wait_for_function("document.querySelector('#dlgZeros').inert === true")
    page.evaluate("FK.sheet.close(document.querySelector('#dlgZeros'))")             # the sheet goes underneath the confirmed question
    wait_closed(page)
    assert page.evaluate("document.querySelector('#dlgZeros').inert") is False
    assert page.evaluate('FK.bal.selected().zero') == zero_now                      # nothing is saved to a sheet that is gone


def test_the_zero_set_note_is_not_in_the_error_colour_and_focus_moves_to_the_title(page, app_url):
    for night in (False, True):
        open_screen(page, app_url, profile='umine', profiles=[own()], night=night)
        open_zeros(page)
        page.fill('#zsOther', '301')
        expect(page.locator('#zsMsg')).to_have_text(BAD_OTHER)
        err = page.evaluate("getComputedStyle(document.querySelector('#zsMsg')).color")
        page.fill('#zsOther', '')
        page.locator('#zsUse button', has_text='Use 50 yd zero').click()
        page.click('#cfOk')
        expect(page.locator('#zsMsg')).to_have_text('Zero set to 50 yd')
        ok = page.evaluate("getComputedStyle(document.querySelector('#zsMsg')).color")
        hint = page.evaluate("getComputedStyle(document.querySelector('#zsKey')).color")
        assert ok != err and ok == hint, (night, err, ok, hint)
        assert page.evaluate('document.activeElement.id') == 'zsTitle'              # the Use button it was on has been rebuilt
        assert page.evaluate("document.querySelector('#zsTitle').getAttribute('tabindex')") == '-1'
        assert page.evaluate("document.querySelector('#zsMsg').classList.contains('rf-msg')")    # still the error style class for errors
        page.fill('#zsOther', '301')
        expect(page.locator('#zsMsg')).to_have_text(BAD_OTHER)                       # an error is the error colour again
        assert page.evaluate("getComputedStyle(document.querySelector('#zsMsg')).color") == err


# ---------- Compare zeros: the chart above the table ----------

CHART_JS = """() => {
  const svg = document.querySelector('#zsSvg'), box = document.querySelector('#zsChart');
  const num = s => (s.match(/-?\\d+(?:\\.\\d+)?/g) || []).map(Number);
  const grid = Object.fromEntries([...svg.querySelectorAll('.zs-grid')].map(g => [g.dataset.yd, Number(g.getAttribute('x1'))]));
  const los = svg.querySelector('.zs-los');
  return {
    shown: !box.hidden, role: svg.getAttribute('role'), aria: svg.getAttribute('aria-label'),
    w: Number(svg.getAttribute('width')), h: Number(svg.getAttribute('height')), box: box.getBoundingClientRect().width,
    grid, losY: los ? Number(los.getAttribute('y1')) : null, losW: los ? los.getAttribute('stroke-width') : null,
    paths: [...svg.querySelectorAll('path.zs-path')].map(p => ({ zero: p.dataset.zero, d: p.getAttribute('d'), pts: num(p.getAttribute('d')),
      dash: p.getAttribute('stroke-dasharray') || '', width: Number(p.getAttribute('stroke-width')), fill: p.getAttribute('fill') })),
    labels: [...svg.querySelectorAll('text.zs-lab')].map(t => { const b = t.getBBox(); return { zero: t.dataset.zero, text: t.textContent, x: b.x, y: b.y, w: b.width, h: b.height, fs: parseFloat(getComputedStyle(t).fontSize) }; }),
    texts: [...svg.querySelectorAll('text')].map(t => { const b = t.getBBox(); return { text: t.textContent, cls: t.getAttribute('class'), x: b.x, y: b.y, w: b.width, h: b.height, fs: parseFloat(getComputedStyle(t).fontSize) }; }),
    ylabels: [...svg.querySelectorAll('text.zs-ay')].map(t => { const b = t.getBBox(); return { text: t.textContent, c: b.y + b.height / 2 }; }),
    hgrid: [...svg.querySelectorAll('.zs-hgrid')].map(l => Number(l.getAttribute('y1'))),
    dots: [...svg.querySelectorAll('circle.zs-dot')].map(c => ({ zero: c.dataset.zero, x: Number(c.getAttribute('cx')), y: Number(c.getAttribute('cy')) })),
    caption: (t => { if (!t) return null; const b = t.getBBox(); return { x: b.x, y: b.y, w: b.width, h: b.height }; })([...svg.querySelectorAll('text.zs-name')][0]),
    markup: svg.outerHTML };
}"""


def chart(page):
    return page.evaluate(CHART_JS)


def chart_sheet(page, app_url, zeros, night=False, **kw):
    kw.setdefault('profile', 'p556m193')                             # the load of the review pictures; the others are tried where a test says so
    open_screen(page, app_url, night=night, **kw)
    open_zeros(page)
    ticks = [z for z in zeros if str(z) in BOXES]
    pick(page, ticks, ([z for z in zeros if str(z) not in BOXES] or [''])[0])         # a zero that has no box is typed into Other
    page.wait_for_function("document.querySelectorAll('#zsSvg path.zs-path').length === %d" % len(zeros))


def y_at(path, x):
    """The path's y at x, by straight segments between its own points."""
    p = path['pts']
    pts = [(p[i], p[i + 1]) for i in range(0, len(p) - 1, 2)]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x0 <= x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return None


def subpaths(path):
    """The path's points, one list per pen-down run (an M starts a new run)."""
    runs = []
    for m in re.finditer(r'([ML])(-?[\d.]+) (-?[\d.]+)', path['d']):
        if m.group(1) == 'M':
            runs.append([])
        runs[-1].append((float(m.group(2)), float(m.group(3))))
    return runs


def trace(path, step=1.0):
    """Points along the drawn line, every `step` px."""
    out = []
    for run in subpaths(path):
        out.append(run[0])
        for (x0, y0), (x1, y1) in zip(run, run[1:]):
            n = max(1, int(((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5 / step))
            out += [(x0 + (x1 - x0) * i / n, y0 + (y1 - y0) * i / n) for i in range(1, n + 1)]
    return out


def want_range(page, zeros):
    """The lowest and highest whole inch the chart must show: the data's own range with 0, in whole inches, one more where a path is within half an inch."""
    vals = page.evaluate("zs => BALZ.compare(FK.bal.load(), zs).cols.flatMap(c => c.path.filter(v => v !== null))", zeros)
    top, bottom = max(vals), min(vals)
    lo, hi = min(0, math.floor(bottom)), max(0, math.ceil(top))
    if hi - top < 0.5:
        hi += 1
    if bottom - lo < 0.5:
        lo -= 1
    return lo, hi, bottom, top


def test_one_path_per_zero_each_with_its_own_dash_and_label(page, app_url):
    chart_sheet(page, app_url, [25, 50, 200])
    c = chart(page)
    assert c['shown']
    assert [p['zero'] for p in c['paths']] == ['25', '50', '200']
    dashes = [p['dash'] for p in c['paths']]
    assert len(set(dashes)) == 3 and dashes[0] == ''                 # solid, then two different patterns
    assert all(p['width'] >= 2 and p['fill'] == 'none' for p in c['paths'])
    assert sorted(l['text'] for l in c['labels']) == ['200 yd', '25 yd', '50 yd']
    assert {l['zero'] for l in c['labels']} == {'25', '50', '200'}
    assert any(t['text'] == 'line of sight' for t in c['texts'])
    assert c['losW'] is not None and float(c['losW']) <= 1.5
    assert not NASTY.search(c['markup']), NASTY.search(c['markup'])
    # two zeros: two paths; and the column heading style of a typed zero is the label's
    pick(page, [50], '87.5')
    page.wait_for_function("[...document.querySelectorAll('#zsSvg text.zs-lab')].some(t => t.textContent === '87.5 yd')")
    c = chart(page)
    assert [p['zero'] for p in c['paths']] == ['50', '87.5']
    assert len({p['dash'] for p in c['paths']}) == 2


@pytest.mark.parametrize('zeros', [[25, 50, 200], [36, 100], [25, 36, 100]], ids=['25-50-200', '36-100', '25-36-100'])
def test_each_path_meets_the_line_of_sight_at_its_zero(page, app_url, zeros):
    chart_sheet(page, app_url, zeros)
    c = chart(page)
    x0, x300 = c['grid']['0'], c['grid']['300']
    assert x300 > x0
    for p in c['paths']:
        x = x0 + float(p['zero']) / 300 * (x300 - x0)
        y = y_at(p, x)
        assert y is not None and abs(y - c['losY']) <= 1, (p['zero'], y, c['losY'])
        assert p['pts'][0] == pytest.approx(x0 + 5 / 300 * (x300 - x0), abs=0.02)   # it starts at its 5 yd point, not at the muzzle


def assert_chart_is_the_table(page, zeros):
    """Every path point sits at the table's own figure for these zeros, up is up, and one scale (pixels per inch, positive) holds for all of them."""
    c = chart(page)
    x0, x300 = c['grid']['0'], c['grid']['300']
    want = page.evaluate("zs => BALZ.compare(FK.bal.load(), zs).cols.map(c => ({ yds: BALZ.YDS, path: c.path }))", zeros)
    lo, hi, _, _ = want_range(page, zeros)
    top, bottom = [l for l in c['ylabels'] if l['text'].startswith('+')][0], [l for l in c['ylabels'] if l['text'].startswith('-')][0]
    k = (bottom['c'] - top['c']) / (hi - lo)                       # pixels per inch, read from the axis labels
    assert k > 0, k
    assert len(c['paths']) == len(want)
    for p, w in zip(c['paths'], want):
        pts = [pt for run in subpaths(p) for pt in run]
        have = [(y, v) for y, v in zip(w['yds'], w['path']) if v is not None]
        assert len(pts) == len(have)
        for (x, y), (yd_, v) in zip(pts, have):
            assert x == pytest.approx(x0 + yd_ / 300 * (x300 - x0), abs=0.02)
            assert c['losY'] - y == pytest.approx(k * v, abs=0.25)   # up is positive: a positive figure is above the rule (a smaller y)
            if v > 0.5:
                assert y < c['losY']
            if v < -0.5:
                assert y > c['losY']
    return c


@pytest.mark.parametrize('zeros', [[36, 100, 200], [25, 50, 200]], ids=['36-100-200', '25-50-200'])
def test_the_paths_are_the_tables_own_figures_and_up_is_up(page, app_url, zeros):
    chart_sheet(page, app_url, zeros)
    assert_chart_is_the_table(page, zeros)


@pytest.mark.parametrize('zeros', [[25, 50, 200], [36, 100], [10, 25, 36]], ids=['25-50-200', '36-100', '10-25-36'])
def test_axis_labels_are_the_lowest_whole_inch_zero_and_the_highest(page, app_url, zeros):
    chart_sheet(page, app_url, zeros)
    c = chart(page)
    lo, hi, bottom, top = want_range(page, zeros)
    labels = {l['text']: l['c'] for l in c['ylabels']}
    if zeros != [10, 25, 36]:                                       # the sets where the scale is the data's own, widened to whole inches
        assert set(labels) == {f'{lo} in', '0', f'+{hi} in'}, labels
        lo_y, hi_y = labels[f'{lo} in'], labels[f'+{hi} in']
        assert hi_y < labels['0'] < lo_y                            # the highest inch at the top, the lowest at the bottom
        k = (lo_y - hi_y) / (hi - lo)
        assert labels['0'] - hi_y == pytest.approx(hi * k, abs=1)
        assert c['losY'] == pytest.approx(labels['0'], abs=2)
        assert sorted(c['hgrid']) == pytest.approx(sorted([lo_y, hi_y]), abs=2)
        assert hi >= top + 0.5 and bottom - lo >= 0.5               # whole inches, and no path touches the frame
    else:                                                           # a very close zero: the scale is at least the data's, with room under the rule for the caption
        names = sorted(labels, key=labels.get)
        assert names[0].startswith('+') and names[-1].endswith(' in') and '0' in labels
        assert int(names[0][1:-3]) >= hi and int(names[-1][:-3]) <= lo
    assert all(t.endswith(' in') for t in labels if t != '0')       # the unit is on the top and the bottom label


def test_a_path_never_touches_the_frame(page, app_url):
    chart_sheet(page, app_url, [25, 50, 200])                       # the 25 yd path peaks at 11.97 in: the scale reaches 13, not 12
    c = chart(page)
    top = min(y for p in c['paths'] for _, y in [pt for run in subpaths(p) for pt in run])
    bottom = max(y for p in c['paths'] for _, y in [pt for run in subpaths(p) for pt in run])
    assert top - min(c['hgrid']) >= 4 and max(c['hgrid']) - bottom >= 4, (top, bottom, c['hgrid'])
    assert '+13 in' in [l['text'] for l in c['ylabels']]


@pytest.mark.parametrize('night', [False, True], ids=['day', 'night'])
def test_grid_lines_are_visible_against_the_sheet(page, app_url, night):
    chart_sheet(page, app_url, [36, 100], night=night)
    got = page.evaluate("""() => { const num = s => (s.match(/[\\d.]+/g) || []).map(Number), pc = s => s.startsWith('color(srgb') ? num(s).slice(0, 3).map(v => v * 255) : num(s).slice(0, 3);
      return [...document.querySelectorAll('#zsSvg .zs-grid, #zsSvg .zs-hgrid')].map(l => { const cs = getComputedStyle(l);
        return { fg: pc(cs.stroke), a: Number(cs.strokeOpacity), bg: pc(getComputedStyle(document.querySelector('#dlgZeros')).backgroundColor) }; }); }""")
    assert len(got) == 6
    for g in got:
        eff = [g['a'] * f + (1 - g['a']) * b for f, b in zip(g['fg'], g['bg'])]
        assert contrast_ratio(page, eff, g['bg']) >= 1.5, (night, g, eff)
    if not night:
        assert all(g['a'] <= 0.4 for g in got)                      # the day look is as it was


def test_chart_has_a_text_alternative(page, app_url):
    chart_sheet(page, app_url, [25, 50, 200])
    c = chart(page)
    assert c['role'] == 'img'
    assert c['aria'] == "Chart of the bullet's path for 25, 50 and 200 yd zeros, 5 to 300 yd. The table below has the figures."
    pick(page, [36, 100])
    page.wait_for_function("document.querySelectorAll('#zsSvg path.zs-path').length === 2")
    assert chart(page)['aria'] == "Chart of the bullet's path for 36 and 100 yd zeros, 5 to 300 yd. The table below has the figures."
    # the chart sits above the table
    assert page.evaluate("document.querySelector('#zsChart').compareDocumentPosition(document.querySelector('#zsWrap')) & Node.DOCUMENT_POSITION_FOLLOWING")


def test_chart_follows_the_table_and_hides_with_it(page, app_url):
    chart_sheet(page, app_url, [50, 200])
    assert chart(page)['shown']
    pick(page, [50])                                          # one zero: a message, no table, no chart
    expect(page.locator('#zsMsg')).to_have_text(TOO_FEW)
    assert not chart(page)['shown']
    assert page.evaluate("document.querySelector('#zsSvg').childElementCount") == 0
    page.fill('#zsOther', '36')                               # the Other field brings it back
    page.wait_for_function("document.querySelectorAll('#zsSvg path.zs-path').length === 2")
    assert chart(page)['shown']
    page.fill('#zsOther', '301')                              # refused: ticked 50 alone remains
    expect(page.locator('#zsMsg')).to_have_text(BAD_OTHER)
    assert not chart(page)['shown']


def test_chart_redraws_after_use_this_zero(page, app_url):
    open_screen(page, app_url, profile='umine', profiles=[own()])
    open_zeros(page)
    pick(page, [50, 100, 200])                                  # the profile's own zero (100) is one of the three
    page.wait_for_function("document.querySelectorAll('#zsSvg path.zs-path').length === 3")
    assert_chart_is_the_table(page, [50, 100, 200])
    before = chart(page)
    assert zbuttons(page) == ['Use 50 yd zero', 'Use 200 yd zero']      # no button for the zero the profile has now
    page.locator('#zsUse button', has_text='Use 50 yd zero').click()
    page.locator('#cfOk').click()
    page.wait_for_function("document.querySelector('#zsNow').textContent === 'Current zero: 50 yd'")
    assert zbuttons(page) == ['Use 100 yd zero', 'Use 200 yd zero']     # the table side has changed: 50 is the current zero now
    after = assert_chart_is_the_table(page, [50, 100, 200])       # and the chart equals the table's figures for the state on screen
    assert after['shown'] and [p['zero'] for p in after['paths']] == ['50', '100', '200']
    heads = [h.replace(' yd zero', ' yd') for h in ztable(page)['head'][1:]]
    assert sorted(l['text'] for l in after['labels']) == sorted(heads)
    assert after['aria'] == "Chart of the bullet's path for 50, 100 and 200 yd zeros, 5 to 300 yd. The table below has the figures."
    assert after['aria'] == before['aria'] and not NASTY.search(after['markup'])


@pytest.mark.parametrize('night', [False, True], ids=['day', 'night'])
@pytest.mark.parametrize('zeros', [[25, 50, 200], [36, 100], [25, 36, 50], [10, 25, 36], [36, 38, 100]], ids=['25-50-200', '36-100', '25-36-50', '10-25-36', '36-38-100'])
def test_labels_do_not_overlap_each_other_or_leave_the_box_at_360(page, app_url, night, zeros):
    chart_sheet(page, app_url, zeros, night=night)

    def check(strict=True):
        c = chart(page)
        assert c['w'] <= 360 and c['w'] == pytest.approx(c['box'], abs=1)
        rects = [(t['text'], t['x'], t['y'], t['x'] + t['w'], t['y'] + t['h']) for t in c['texts']]
        assert rects
        for name, x0, y0, x1, y1 in rects:
            assert x0 >= -0.5 and y0 >= -0.5 and x1 <= c['w'] + 0.5 and y1 <= c['h'] + 0.5, (name, x0, y0, x1, y1, c['w'], c['h'])
        for i, a in enumerate(rects):
            for b in rects[i + 1:]:
                gapx = min(a[3], b[3]) - max(a[1], b[1])
                gapy = min(a[4], b[4]) - max(a[2], b[2])
                assert not (gapx > 0.5 and gapy > 0.5), (a, b)       # no two texts share any area
        assert len(c['labels']) == len(zeros)                       # moved apart, never dropped
        cap = c['caption']
        assert cap is not None
        for p in c['paths'] if strict else []:                      # the caption shares no area with any path's stroke (half a stroke added); with enlarged text the caption is as wide as a third of the plot and only the texts-apart rule above holds
            for x, y in trace(p):
                assert not (cap['x'] - 1.5 < x < cap['x'] + cap['w'] + 1.5 and cap['y'] - 1.5 < y < cap['y'] + cap['h'] + 1.5), (p['zero'], x, y, cap)
        assert cap['x'] >= c['grid']['0'] and cap['x'] + cap['w'] <= c['grid']['300']      # inside the plot
        assert all(l['fs'] >= 12 for l in c['texts'])
        assert not NASTY.search(c['markup'])
        assert overflow(page, ZDLG) == []
        box = page.locator('#zsClose').bounding_box()               # the Close button stays on the screen
        assert box['y'] >= 0 and box['y'] + box['height'] <= 640

    check()
    page.locator('#zsChart').scroll_into_view_if_needed()
    check()
    before = chart(page)['texts'][0]['fs']
    enlarge_text(page)
    page.evaluate("dispatchEvent(new Event('resize'))")
    page.wait_for_function("fs => parseFloat(getComputedStyle(document.querySelector('#zsSvg text')).fontSize) > fs + 2", arg=before)
    check(strict=False)
    assert chart(page)['texts'][0]['fs'] >= before * 1.3


def test_a_label_that_moves_apart_keeps_a_leader_to_its_path_end(page, app_url):
    chart_sheet(page, app_url, [36, 36.5, 100])                 # 36 and 36.5 yd zeros end a few hundredths of an inch apart at 300 yd
    c = chart(page)
    ends = page.evaluate("""() => [...document.querySelectorAll('#zsSvg .zs-lead')].map(l => [Number(l.getAttribute('x1')), Number(l.getAttribute('y1')), Number(l.getAttribute('x2')), Number(l.getAttribute('y2'))])""")
    near = 0
    for p in c['paths']:
        end_y = p['pts'][-1]
        label = next(l for l in c['labels'] if l['zero'] == p['zero'])
        centre = label['y'] + label['h'] / 2
        if abs(centre - end_y) > 3:
            near += 1
            assert any(abs(e[0] - p['pts'][-2]) < 2 and abs(e[1] - end_y) < 1 for e in ends), (p['zero'], ends)
    assert near >= 1                                           # at least one label really had to move, so the leader is exercised


def stubbed_compare(page, zeros, edit):
    """Run the sheet with BALZ.compare replaced by the real one with its result edited (restored in a finally, as test_bal_zero's sign-noise test does)."""
    open_zeros(page)
    pick(page, zeros)
    page.wait_for_function("document.querySelectorAll('#zsSvg path.zs-path').length === %d" % len(zeros))
    page.evaluate("""edit => { window.__real = BALZ.compare; BALZ.compare = (l, z) => { const r = window.__real(l, z); (new Function('r', edit))(r); return r; }; }""", edit)
    try:
        page.locator('#zs36').click()                           # any pick redraws table and chart through the stub
        page.locator('#zs36').click()
        page.wait_for_function("document.querySelectorAll('#zsSvg .zs-lab').length === %d" % len(zeros))
        return chart(page)
    finally:
        page.evaluate("BALZ.compare = window.__real")


def test_a_column_with_no_points_keeps_its_label_and_has_no_path(page, app_url):
    open_screen(page, app_url)
    c = stubbed_compare(page, [25, 50, 200], "r.cols[0].path = r.cols[0].path.map(() => null); r.cols[0].other = null; r.cols[0].peak = null;")
    assert [p['zero'] for p in c['paths']] == ['50', '200']      # no path element at all, not an empty d
    assert all(p['d'] for p in c['paths'])
    assert sorted(l['text'] for l in c['labels']) == ['200 yd', '25 yd', '50 yd']
    lab = next(l for l in c['labels'] if l['zero'] == '25')
    assert lab['x'] >= c['grid']['300'] and abs(lab['y'] + lab['h'] / 2 - c['losY']) < 40    # at the right edge, near the line of sight
    assert not NASTY.search(c['markup'])


def test_a_column_with_one_point_is_a_dot(page, app_url):
    open_screen(page, app_url)
    c = stubbed_compare(page, [25, 50, 200], "r.cols[1].path = r.cols[1].path.map((v, i) => i === 3 ? v : null); r.cols[1].other = null;")
    assert [p['zero'] for p in c['paths']] == ['25', '200']
    assert [d['zero'] for d in c['dots']] == ['50']
    want = page.evaluate("BALZ.YDS[3]")
    assert c['dots'][0]['x'] == pytest.approx(c['grid']['0'] + want / 300 * (c['grid']['300'] - c['grid']['0']), abs=0.02)
    assert sorted(l['text'] for l in c['labels']) == ['200 yd', '25 yd', '50 yd']
    assert not NASTY.search(c['markup'])
