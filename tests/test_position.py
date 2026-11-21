"""Position screen (v7.8 Tactical, design section 6): declination worked out from the position with the World Magnetic Model,
the Auto / By hand switch, the larger heading, the section headings, and Share position."""
import re
from datetime import datetime, timezone

import pytest
from playwright.sync_api import expect

from .tac import store, heading
from .test_nav import boot, position, fix, ev, txt, rotation, mk, dest, HOME, NOW
from .test_tactical_existing import go

OUT_OF_DATE = 'The magnetic model is out of date. Check a current map.'
SHARE_STUB = """(() => { window.__shared = []; window.__shareErr = null;
  Object.defineProperty(navigator, 'share', { configurable: true, value: async d => {
    window.__shared.push(d); if (window.__shareErr) { const e = new Error('no'); e.name = window.__shareErr; throw e; } } }); })()"""
NO_SHARE = "(() => { try { delete Navigator.prototype.share; } catch (e) {} Object.defineProperty(navigator, 'share', { configurable: true, value: undefined }); })()"
CLIP_STUB = """(() => { window.__clip = []; window.__clipFail = false;
  Object.defineProperty(navigator, 'clipboard', { configurable: true, value: {
    writeText: async t => { if (window.__clipFail) throw new Error('denied'); window.__clip.push(t); } } }); })()"""


def at_position(page, app_url, **kv):
    boot(page, app_url, decl_mode=None, **kv)
    position(page)


def wmm(page, lat, lon, year):
    return ev(page, '([a, b, y]) => WMM.declination(a, b, 0, y)', [lat, lon, year])


def year_now(page):
    return ev(page, """(() => { const y = new Date().getUTCFullYear(), a = Date.UTC(y, 0, 1), b = Date.UTC(y + 1, 0, 1);
      return y + (Date.now() - a) / (b - a); })()""")


def fmt(d):
    r = round(d, 1)
    return '0.0°' if r == 0 else f'{abs(r):.1f}° {"W" if r < 0 else "E"}'


# ---------- Declination ----------

def test_fresh_install_works_declination_out_from_the_position(page, app_url):
    at_position(page, app_url)
    assert ev(page, "JSON.parse(localStorage.getItem('fk.declMode'))") == 'auto'
    fix(page, *HOME)
    d = wmm(page, *HOME, year_now(page))
    assert -14 < d < -10
    expect(page.locator('#declLine')).to_have_text(
        f'Declination {fmt(d)} (worked out from your position, model valid to December 2029)')
    expect(page.locator('#decl')).to_be_hidden()
    heading(page, 90)
    expect(page.locator('#hdg')).to_have_text(f'{round(90 + d)}°')
    expect(page.locator('#hdgRef')).to_contain_text('true')
    assert abs(ev(page, 'FK.trueHeading()') - (90 + d)) < 1e-6


def test_stored_typed_declination_from_v77_stays_by_hand(page, app_url):
    at_position(page, app_url, decl=-12)
    assert ev(page, "JSON.parse(localStorage.getItem('fk.declMode'))") == 'manual'
    expect(page.locator('#decl')).to_be_visible()
    expect(page.locator('#decl')).to_have_value('-12')
    expect(page.locator('#declSeg [data-decl="manual"]')).to_have_attribute('aria-pressed', 'true')
    fix(page, *HOME)
    heading(page, 90)
    expect(page.locator('#hdg')).to_have_text('78°')
    expect(page.locator('#hdgRef')).to_contain_text('true')


def test_stored_zero_declination_is_auto(page, app_url):
    at_position(page, app_url, decl=0)
    assert ev(page, "JSON.parse(localStorage.getItem('fk.declMode'))") == 'auto'


def test_switch_by_hand_and_back_restores_the_computed_value(page, app_url):
    at_position(page, app_url)
    fix(page, *HOME)
    heading(page, 90)
    d = wmm(page, *HOME, year_now(page))
    page.click('#declSeg [data-decl="manual"]')
    expect(page.locator('#decl')).to_be_visible()
    expect(page.locator('#declLine')).to_be_hidden()
    page.fill('#decl', '-5')
    expect(page.locator('#hdg')).to_have_text('85°')
    assert ev(page, "JSON.parse(localStorage.getItem('fk.declMode'))") == 'manual'
    page.click('#declSeg [data-decl="auto"]')
    expect(page.locator('#decl')).to_be_hidden()
    expect(page.locator('#hdg')).to_have_text(f'{round(90 + d)}°')
    expect(page.locator('#declLine')).to_contain_text(fmt(d))
    assert ev(page, "JSON.parse(localStorage.getItem('fk.decl'))") == -5   # the typed value is kept, never overwritten


def test_by_hand_zero_reads_magnetic(page, app_url):
    at_position(page, app_url, declMode='manual', decl=0)
    fix(page, *HOME)
    heading(page, 90)
    expect(page.locator('#hdg')).to_have_text('90°')
    expect(page.locator('#hdgRef')).to_contain_text('magnetic')


def test_no_fix_waits_and_reads_magnetic(page, app_url):
    at_position(page, app_url)
    expect(page.locator('#declLine')).to_have_text('Declination: waiting for a position')
    heading(page, 90)
    expect(page.locator('#hdg')).to_have_text('90°')
    expect(page.locator('#hdgRef')).to_have_text('E, 1600 mils, magnetic')
    assert ev(page, 'FK.trueHeading()') == 90


def test_no_fix_does_not_fall_back_to_a_typed_value(page, app_url):
    at_position(page, app_url, declMode='auto', decl=-7)
    heading(page, 90)
    expect(page.locator('#hdg')).to_have_text('90°')
    expect(page.locator('#hdgRef')).to_contain_text('magnetic')


@pytest.mark.parametrize('when', [datetime(2030, 6, 1, tzinfo=timezone.utc), datetime(2024, 6, 1, tzinfo=timezone.utc)],
                         ids=['after-valid-until', 'before-epoch'])
def test_out_of_date_model_says_so_and_still_shows_the_value(page, app_url, when):
    page.clock.install(time=when.timestamp())
    page.goto('about:blank')
    store(page, advAck=True)
    page.goto(app_url + '#/tactical/position')
    page.wait_for_function('window.FK && FK._test && !document.querySelector("#view-position").hidden')
    fix(page, *HOME)
    d = wmm(page, *HOME, min(2030.0, max(2025.0, year_now(page))))   # the model's date is clamped to its valid years
    expect(page.locator('#declLine')).to_contain_text(f'Declination {fmt(d)}')
    expect(page.locator('#declLine')).to_contain_text(OUT_OF_DATE)
    heading(page, 90)
    expect(page.locator('#hdg')).to_have_text(f'{round(90 + d)}°')


def test_recomputed_only_when_the_position_moves_far(page, app_url):
    at_position(page, app_url)
    ev(page, """(() => { window.__n = 0; const o = WMM.declination;
      WMM.declination = (...a) => { window.__n++; return o(...a); }; })()""")
    fix(page, *HOME)
    n1 = ev(page, 'window.__n')
    assert n1 >= 1
    for i in range(5):
        fix(page, *dest(*HOME, 45, 1000 + i * 100))   # about a kilometre away
    assert ev(page, 'window.__n') == n1
    fix(page, *dest(*HOME, 45, 20000))
    assert ev(page, 'window.__n') > n1


def test_nav_arrow_follows_a_declination_change(page, app_url):
    target = dest(*HOME, 73, 412)
    boot(page, app_url, markers=[mk('w1', 'Rally', *target)], declMode='manual', decl=0)
    ev(page, "FK.tac.setTarget({ type: 'marker', id: 'w1' })")
    position(page)
    fix(page, *HOME)
    heading(page, 90)
    r0 = rotation(page)
    page.fill('#decl', '-12')
    page.wait_for_function('r => { const m = /rotate\\((-?[\\d.]+)deg\\)/.exec(document.querySelector("#nvArrowG").style.transform); return m && Math.abs(+m[1] - r) > 1; }', arg=r0)
    assert abs((rotation(page) - r0) - 12) < 0.01


# ---------- Heading and layout ----------

def test_heading_is_large_and_not_clipped(page, app_url):
    at_position(page, app_url)
    heading(page, 358)
    expect(page.locator('#hdg')).to_have_text('358°')
    size = ev(page, "parseFloat(getComputedStyle(document.querySelector('#hdg')).fontSize)")
    assert size >= 56
    box = page.locator('#hdg').bounding_box()
    assert box['x'] >= 0 and box['x'] + box['width'] <= 360
    assert ev(page, "(e => e.scrollWidth <= e.clientWidth)(document.querySelector('.hdg'))")
    assert ev(page, 'document.documentElement.scrollWidth') <= 360


def test_sections_have_home_style_headings(page, app_url):
    at_position(page, app_url)
    heads = page.locator('#view-position h2.sv-cat')
    expect(heads).to_have_text(['Position', 'Compass', 'Markers'])


def test_nav_panel_stays_on_top_when_a_target_is_set(page, app_url):
    boot(page, app_url, markers=[mk('w1', 'Rally', *dest(*HOME, 73, 412))], decl_mode=None)
    ev(page, "FK.tac.setTarget({ type: 'marker', id: 'w1' })")
    position(page)
    fix(page, *HOME)
    expect(page.locator('#navPanel')).to_be_visible()
    assert ev(page, """(() => { const p = document.querySelector('#navPanel').getBoundingClientRect();
      return [...document.querySelectorAll('#view-position h2.sv-cat')].every(h => h.getBoundingClientRect().top > p.bottom); })()""")


def test_controls_are_at_least_44px(page, app_url):
    at_position(page, app_url)
    for sel in ['#declSeg [data-decl="auto"]', '#declSeg [data-decl="manual"]', '#shareBtn']:
        b = page.locator(sel).bounding_box()
        assert b['height'] >= 44 and b['width'] >= 44, sel


# ---------- Share position ----------

def local_hm(page, t):
    return ev(page, "t => { const d = new Date(t); return String(d.getHours()).padStart(2, '0') + ':' + String(d.getMinutes()).padStart(2, '0'); }", t)


def share_fix(page, lat, lon, alt=None, acc=5, ago=0):
    page.evaluate('f => FK._test.fix({ lat: f.lat, lon: f.lon, acc: f.acc, alt: f.alt, t: Date.now() - f.ago })',
                  {'lat': lat, 'lon': lon, 'acc': acc, 'alt': alt, 'ago': ago})


def expected_time(page, t):
    z = datetime.fromtimestamp(t / 1000, tz=timezone.utc)
    return f'Time {local_hm(page, t)} local, {z:%H:%M}Z {z.day:02d} {z:%b %Y}'


def test_share_uses_the_share_sheet_with_the_full_block(page, app_url):
    page.add_init_script(SHARE_STUB)
    at_position(page, app_url)
    share_fix(page, *HOME, alt=150.0, acc=4.6)
    grid = ev(page, '([a, b]) => GEO.toMGRS(a, b).text', list(HOME))
    page.click('#shareBtn')
    page.wait_for_function('window.__shared.length === 1')
    text = ev(page, 'window.__shared[0].text')
    assert text.split('\n') == [
        f'Position {grid}',
        '43.00000, -76.00000',
        'Altitude 492 ft',
        'Accuracy ±5 m',
        expected_time(page, NOW),
    ]
    expect(page.locator('#dlgShare')).not_to_be_visible()


@pytest.mark.parametrize('ago,line', [(30_000, None), (75_000, 'Position is 75 s old'), (300_000, 'Position is 5 min old')])
def test_share_states_an_old_position_and_uses_the_fix_time(page, app_url, ago, line):
    page.add_init_script(SHARE_STUB)
    at_position(page, app_url)
    share_fix(page, *HOME, ago=ago)
    page.click('#shareBtn')
    page.wait_for_function('window.__shared.length === 1')
    lines = ev(page, 'window.__shared[0].text').split('\n')
    assert expected_time(page, NOW - ago) in lines
    assert not any(l.startswith('Altitude') for l in lines)   # unknown altitude: no line
    assert (lines[-1] == line) if line else not lines[-1].startswith('Position is')


def test_share_where_mgrs_does_not_exist_starts_with_lat_long(page, app_url):
    page.add_init_script(SHARE_STUB)
    at_position(page, app_url)
    share_fix(page, 85.0, -76.0)
    page.click('#shareBtn')
    page.wait_for_function('window.__shared.length === 1')
    assert ev(page, 'window.__shared[0].text').split('\n')[0] == 'Position 85.00000, -76.00000'


def test_share_cancelled_does_nothing_more(page, app_url):
    page.add_init_script(SHARE_STUB)
    page.add_init_script(CLIP_STUB)
    at_position(page, app_url)
    share_fix(page, *HOME)
    ev(page, "window.__shareErr = 'AbortError'")
    page.click('#shareBtn')
    page.wait_for_function('window.__shared.length === 1')
    page.wait_for_timeout(100)
    assert ev(page, 'window.__clip') == []
    expect(page.locator('#dlgShare')).not_to_be_visible()


def test_share_failing_falls_back_to_copy(page, app_url):
    page.add_init_script(SHARE_STUB)
    page.add_init_script(CLIP_STUB)
    at_position(page, app_url)
    share_fix(page, *HOME)
    ev(page, "window.__shareErr = 'NotAllowedError'")
    page.click('#shareBtn')
    expect(page.locator('#dlgShare')).to_be_visible()
    page.wait_for_function('window.__clip.length === 1')
    assert ev(page, 'window.__clip[0]') == txt(page, '#psText')


def test_no_share_copies_and_shows_the_text(page, app_url):
    page.add_init_script(NO_SHARE)
    page.add_init_script(CLIP_STUB)
    at_position(page, app_url)
    share_fix(page, *HOME, alt=150.0)
    page.click('#shareBtn')
    expect(page.locator('#dlgShare')).to_be_visible()
    page.wait_for_function('window.__clip.length === 1')
    shown = txt(page, '#psText')
    assert ev(page, 'window.__clip[0]') == shown
    assert shown.startswith('Position 18T ') and 'Altitude 492 ft' in shown and 'Z ' in shown
    expect(page.locator('#psMsg')).to_have_text('Copied.')


def test_no_share_and_clipboard_refused_still_shows_the_text(page, app_url):
    page.add_init_script(NO_SHARE)
    page.add_init_script(CLIP_STUB)
    at_position(page, app_url)
    share_fix(page, *HOME)
    ev(page, 'window.__clipFail = true')
    page.click('#shareBtn')
    expect(page.locator('#dlgShare')).to_be_visible()
    expect(page.locator('#psText')).to_contain_text('43.00000, -76.00000')
    expect(page.locator('#psMsg')).to_have_text('Not copied. Press and hold the text to select it.')
    ev(page, 'window.__clipFail = false')
    page.click('#psCopy')
    page.wait_for_function('window.__clip.length === 1')
    expect(page.locator('#psMsg')).to_have_text('Copied.')
    page.click('#psClose')
    expect(page.locator('#dlgShare')).not_to_be_visible()


def test_share_with_no_fix_says_so(page, app_url):
    from .tac import gps_searching
    gps_searching(page)
    page.add_init_script(SHARE_STUB)
    at_position(page, app_url)
    expect(page.locator('#shareBtn')).to_be_enabled()
    page.click('#shareBtn')
    expect(page.locator('#toast')).to_have_text('No position yet. Wait for a GPS fix.')
    assert ev(page, 'window.__shared') == []


# ---------- Review round: clamped model date, arrow sign both ways, time zones, last known position, no -0 ----------

def boot_at(page, app_url, when, **kv):
    page.clock.install(time=when.timestamp())
    page.goto('about:blank')
    store(page, advAck=True, **kv)
    page.goto(app_url + '#/tactical/position')
    page.wait_for_function('window.FK && FK._test && !document.querySelector("#view-position").hidden')


@pytest.mark.parametrize('when,clamp', [(datetime(1970, 1, 1, tzinfo=timezone.utc), 2025.0),
                                        (datetime(2099, 1, 1, tzinfo=timezone.utc), 2030.0)], ids=['1970', '2099'])
def test_wrong_clock_uses_the_model_at_its_nearest_valid_date(page, app_url, when, clamp):
    boot_at(page, app_url, when)
    fix(page, *HOME)
    d = wmm(page, *HOME, clamp)
    assert fmt(d) == {2025.0: '12.0° W', 2030.0: '11.8° W'}[clamp]   # reviewer's -11.993 and -11.765, one decimal
    expect(page.locator('#declLine')).to_contain_text(f'Declination {fmt(d)}')
    expect(page.locator('#declLine')).to_contain_text(OUT_OF_DATE)
    heading(page, 90)
    assert abs(ev(page, 'FK.trueHeading()') - (90 + d)) < 1e-6


def test_inside_the_window_the_date_is_not_clamped(page, app_url):
    at_position(page, app_url)
    fix(page, *HOME)
    heading(page, 90)
    y = year_now(page)
    assert 2025 < y < 2030
    assert abs(ev(page, 'FK.trueHeading()') - (90 + wmm(page, *HOME, y))) < 1e-9
    expect(page.locator('#declLine')).not_to_contain_text(OUT_OF_DATE)


EAST = (45.0, -120.0)   # a round position in the western United States; its sign is checked from the model, not assumed


@pytest.mark.parametrize('here,side', [(HOME, 'right'), (EAST, 'left')], ids=['west-declination', 'east-declination'])
def test_auto_arrow_turns_the_right_way(page, app_url, here, side):
    north = dest(*here, 0, 1000)
    boot(page, app_url, markers=[mk('w1', 'North', *north)], decl_mode=None, view=here)
    ev(page, "FK.tac.setTarget({ type: 'marker', id: 'w1' })")
    position(page)
    fix(page, *here)
    d = wmm(page, *here, year_now(page))
    if side == 'right':
        assert -14 < d < -10
    else:
        assert d > 8
    heading(page, 0)
    th = ev(page, 'FK.trueHeading()')
    assert abs(th - (d % 360)) < 1e-6
    expect(page.locator('#nvTurn')).to_have_text(f'Turn {round(abs(d))}° {side}')
    rot = rotation(page)
    assert abs(rot - (-d)) < 0.05
    assert (rot > 0) == (side == 'right')


def tz_page(browser, tz):
    ctx = browser.new_context(viewport={'width': 360, 'height': 640}, service_workers='block', timezone_id=tz)
    ctx.route('**/*', lambda r: r.continue_() if r.request.url.startswith(('http://127.0.0.1', 'data:', 'blob:', 'about:')) else r.abort())
    pg = ctx.new_page()
    errors = []
    pg.on('pageerror', lambda e: errors.append(str(e)))
    return ctx, pg, errors


@pytest.mark.parametrize('tz,t,line', [
    ('America/New_York', datetime(2027, 1, 15, 0, 10, tzinfo=timezone.utc), 'Time 19:10 local, 00:10Z 15 Jan 2027'),
    ('Asia/Kolkata', datetime(2027, 1, 15, 0, 10, tzinfo=timezone.utc), 'Time 05:40 local, 00:10Z 15 Jan 2027'),
    ('Asia/Kolkata', datetime(2027, 1, 14, 18, 45, tzinfo=timezone.utc), 'Time 00:15 local, 18:45Z 14 Jan 2027'),
], ids=['new-york-after-utc-midnight', 'kolkata-after-utc-midnight', 'kolkata-after-local-midnight'])
def test_share_time_line_in_other_time_zones(browser, app_url, tz, t, line):
    ctx, pg, errors = tz_page(browser, tz)
    try:
        pg.add_init_script(SHARE_STUB)
        ms = int(t.timestamp() * 1000)
        pg.clock.install(time=t.timestamp() + 5)
        pg.goto('about:blank')
        store(pg, advAck=True)
        pg.goto(app_url + '#/tactical/position')
        pg.wait_for_function('window.FK && FK._test && !document.querySelector("#view-position").hidden')
        pg.evaluate('t => FK._test.fix({ lat: 43, lon: -76, acc: 5, t })', ms)
        pg.click('#shareBtn')
        pg.wait_for_function('window.__shared.length === 1')
        assert line in pg.evaluate('window.__shared[0].text').split('\n')
        assert errors == []
    finally:
        ctx.close()


LAST = 'worked out from your last known position, model valid to December 2029'
LIVE = 'worked out from your position, model valid to December 2029'


def test_stored_last_position_is_named_as_such_until_a_live_fix(page, app_url):
    at_position(page, app_url, lastFix={'lat': 43.0, 'lon': -76.0, 'alt': None, 'acc': 5, 'spd': None, 't': NOW - 3600_000})
    d = wmm(page, *HOME, year_now(page))
    expect(page.locator('#declLine')).to_have_text(f'Declination {fmt(d)} ({LAST})')
    fix(page, *HOME)
    expect(page.locator('#declLine')).to_have_text(f'Declination {fmt(d)} ({LIVE})')


def test_after_reload_the_position_is_last_known_again(page, app_url):
    at_position(page, app_url)
    fix(page, *HOME)
    expect(page.locator('#declLine')).to_contain_text(LIVE)
    page.reload()
    page.wait_for_function('window.FK && FK._test && !document.querySelector("#view-position").hidden')
    expect(page.locator('#declLine')).to_contain_text(LAST)


def test_share_never_prints_negative_zero(page, app_url):
    page.add_init_script(SHARE_STUB)
    at_position(page, app_url)
    share_fix(page, -0.000001, -0.000001)
    page.click('#shareBtn')
    page.wait_for_function('window.__shared.length === 1')
    text = ev(page, 'window.__shared[0].text')
    assert '0.00000, 0.00000' in text.split('\n')
    assert '-0.00000' not in text
