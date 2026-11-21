"""Task 9: Survival tools registry and the SOS light page (#/survival/tool/sos).
Task 10: the Daylight and moon page (#/survival/tool/daylight)."""
import json
import math
import re
import zlib
from datetime import datetime
from zoneinfo import ZoneInfo

from playwright.sync_api import expect

import pytest

from .conftest import inject_data
from .test_survival_topic import XSS, topic, wait_hash
from .test_tools import T0, boot as tools_boot
from .test_astro import ROWS, ak_page, ny_page   # noqa: F401  (pytest fixtures with a fixed time zone)

SOS = '#/survival/tool/sos'
PANEL = '#survPage .sv-light'
# Morse SOS at a 200 ms unit: on 1, off 1, on 1, off 1, on 1, off 3, on 3, off 1, on 3, off 1, on 3, off 3, on 1, off 1, on 1, off 1, on 1, off 7
GROUP = [1, 1, 1, 1, 1, 3, 3, 1, 3, 1, 3, 3, 1, 1, 1, 1, 1, 7]
UNIT = 200
FAKE_LOCK = """
  window.__locks = { requested: 0, released: 0 };
  Object.defineProperty(navigator, 'wakeLock', { configurable: true, value: { request: async () => {
    window.__locks.requested++;
    const l = new EventTarget();
    l.release = async () => { window.__locks.released++; };
    return l;
  } } });"""


def boot(page, app_url, hash_='#/survival', **kw):
    tools_boot(page, app_url, hash_=hash_, **kw)
    page.clock.pause_at(T0 // 1000 + 60)   # time now moves only when a test says so


def start(page):
    page.get_by_role('button', name='Start SOS').click()


def lit(page):
    return page.locator(PANEL).get_attribute('data-on') == '1'


def sample_units(page, n):
    out = []
    for _ in range(n):
        out.append('1' if lit(page) else '0')
        page.clock.run_for(UNIT)
    return ''.join(out)


def test_registry_lists_sos_and_home_shows_it_under_tools(page, app_url):
    boot(page, app_url)
    assert page.evaluate('FK.survival.tools().map(t => [t.name, t.label])') == [['sos', 'SOS light'], ['daylight', 'Daylight and moon'], ['water', 'Water planner'], ['windchill', 'Wind chill']]
    assert page.locator('#survTools h2').text_content() == 'Tools'
    page.locator('#survTools button[data-key="u:sos"]').click()
    wait_hash(page, SOS)
    expect(page.locator('#survPage h2')).to_have_text('SOS light')
    assert page.evaluate('FK.survival.open("u:nope")') is False
    assert page.evaluate('FK.survival.open("u:sos", { replace: true })') is True


def test_unknown_tool_address_is_corrected_to_the_survival_home(page, app_url):
    boot(page, app_url, '#/survival/tool/nope')
    wait_hash(page, '#/survival')


def test_page_has_start_steady_warning_and_reduced_motion_note(page, app_url):
    boot(page, app_url, SOS)
    start_btn = page.get_by_role('button', name='Start SOS')
    steady = page.get_by_role('button', name='Steady light')
    expect(start_btn).to_be_visible()
    expect(steady).to_be_visible()
    assert start_btn.bounding_box()['height'] >= 48 and steady.bounding_box()['height'] >= 48
    assert 'A flashing screen can be seen from far away and gives away your position.' in page.inner_text('#survPage')
    desc = page.locator('#' + start_btn.get_attribute('aria-describedby')).inner_text().lower()
    assert 'reduced motion' in desc
    assert not page.locator(PANEL).is_visible()


def test_one_full_group_flashes_dot_dot_dot_dash_dash_dash_dot_dot_dot_at_200ms_units(page, app_url):
    boot(page, app_url, SOS)
    start(page)
    expect(page.locator(PANEL)).to_be_visible()
    expected = ''.join(('1' if i % 2 == 0 else '0') * u for i, u in enumerate(GROUP))
    assert len(expected) == 34
    assert sample_units(page, 34) == expected
    assert sample_units(page, 34) == expected   # then it repeats


def test_panel_is_white_full_screen_above_the_chrome_in_day_and_night(page, app_url):
    boot(page, app_url, SOS)
    start(page)
    vp = page.viewport_size
    b = page.locator(PANEL).bounding_box()
    assert (b['x'], b['y'], b['width'], b['height']) == (0, 0, vp['width'], vp['height'])
    assert page.evaluate("document.elementFromPoint(5, innerHeight - 5).closest('.sv-light') !== null")   # over the tab bar
    for night in (False, True):
        page.evaluate(f"document.documentElement.setAttribute('data-theme', {'\"night\"' if night else '\"day\"'})")
        assert page.locator(PANEL).evaluate("el => el.dataset.on") == '1'
        assert page.locator(PANEL).evaluate("el => getComputedStyle(el).backgroundColor") == 'rgb(255, 255, 255)'


def test_tap_stops_the_light_and_focus_returns_to_start(page, app_url):
    boot(page, app_url, SOS)
    start(page)
    page.clock.run_for(UNIT * 3)
    page.locator(PANEL).click()
    expect(page.locator(PANEL)).to_be_hidden()
    expect(page.get_by_role('button', name='Start SOS')).to_be_focused()
    page.clock.run_for(UNIT * 40)
    expect(page.locator(PANEL)).to_be_hidden()   # no timer left running


def test_keyboard_enter_and_space_stop_the_light(page, app_url):
    boot(page, app_url, SOS)
    for key in ('Enter', 'Space'):
        start(page)
        expect(page.locator(PANEL)).to_be_focused()
        page.keyboard.press(key)
        expect(page.locator(PANEL)).to_be_hidden()
        expect(page.get_by_role('button', name='Start SOS')).to_be_focused()
    assert page.locator(PANEL).get_attribute('role') in (None, 'button')
    assert page.locator(PANEL).evaluate('el => el.tagName') == 'BUTTON'


def test_steady_light_stays_lit_until_stopped(page, app_url):
    boot(page, app_url, SOS)
    page.get_by_role('button', name='Steady light').click()
    assert sample_units(page, 40) == '1' * 40
    page.locator(PANEL).click()
    expect(page.locator(PANEL)).to_be_hidden()


def test_back_ends_the_light_and_hides_the_panel(page, app_url):
    boot(page, app_url, '#/survival')
    page.locator('#survTools button[data-key="u:sos"]').click()
    wait_hash(page, SOS)
    start(page)
    page.go_back()
    wait_hash(page, '#/survival')
    expect(page.locator(PANEL)).to_have_count(0)
    page.clock.run_for(UNIT * 40)
    expect(page.locator('#survHome')).to_be_visible()


def test_switching_tab_ends_the_light(page, app_url):
    boot(page, app_url, SOS)
    start(page)
    page.evaluate("FK.route.go('/emergency')")
    page.wait_for_function("location.hash.startsWith('#/emergency')")
    expect(page.locator(PANEL)).to_have_count(0)


def test_opening_another_page_ends_the_light(page, app_url):
    boot(page, app_url, SOS)
    start(page)
    page.evaluate("FK.route.go('/survival')")
    wait_hash(page, '#/survival')
    expect(page.locator(PANEL)).to_have_count(0)


def test_hiding_the_tab_ends_the_light(page, app_url):
    boot(page, app_url, SOS, init=FAKE_LOCK)
    start(page)
    page.wait_for_function('window.__locks.requested === 1')
    page.evaluate("""() => { Object.defineProperty(document, 'hidden', { configurable: true, get: () => true });
      document.dispatchEvent(new Event('visibilitychange')); }""")
    expect(page.locator(PANEL)).to_be_hidden()
    page.wait_for_function('window.__locks.released === 1')


def test_wake_lock_is_held_while_running_and_released_on_stop(page, app_url):
    boot(page, app_url, SOS, init=FAKE_LOCK)
    start(page)
    page.wait_for_function('window.__locks.requested === 1')
    assert page.evaluate('window.__locks.released') == 0
    page.locator(PANEL).click()
    page.wait_for_function('window.__locks.released === 1')


def test_no_wake_lock_support_causes_no_error(page, app_url):
    boot(page, app_url, SOS, strip_apis=True)
    assert page.evaluate("'wakeLock' in navigator") is False
    start(page)
    assert sample_units(page, 3) == '101'
    page.locator(PANEL).click()
    expect(page.locator(PANEL)).to_be_hidden()
    page.clock.run_for(50)


def test_rejected_wake_lock_request_causes_no_error(page, app_url):
    boot(page, app_url, SOS, init="Object.defineProperty(navigator, 'wakeLock', { configurable: true, value: { request: () => Promise.reject(new Error('denied')) } });")
    start(page)
    assert sample_units(page, 3) == '101'
    page.locator(PANEL).click()
    page.clock.run_for(50)


def test_opening_records_recent_and_pin_star_pins_the_tool(page, app_url):
    boot(page, app_url, '#/survival')
    assert page.evaluate('FK.recent.all()') == []
    page.locator('#survTools button[data-key="u:sos"]').click()
    wait_hash(page, SOS)
    assert page.evaluate('FK.recent.all()') == ['u:sos']
    star = page.locator('#survPage .sv-head [data-act="pin"]')
    assert star.get_attribute('aria-pressed') == 'false'
    star.click()
    assert star.get_attribute('aria-pressed') == 'true'
    assert page.evaluate("FK.pins.has('u:sos')") is True
    page.go_back()
    wait_hash(page, '#/survival')
    assert page.locator('#survPinned button[data-key="u:sos"]').count() == 1
    assert page.locator('#survRecent button[data-key="u:sos"]').count() == 1


def test_search_finds_the_tool_and_opens_it(page, app_url):
    boot(page, app_url, '#/survival')
    page.click('#searchBtn')
    page.fill('#searchInput', 'sos')
    page.click('#searchBody .sr-item[data-key="u:sos"]')
    wait_hash(page, SOS)
    expect(page.locator('#survPage h2')).to_have_text('SOS light')
    assert page.evaluate('FK.recent.all()') == ['u:sos']


# ---------- Daylight and moon ----------
DAYLIGHT = '#/survival/tool/daylight'
SYR = (43.0, -76.0)
UTQ = (71.29, -156.79)
NO_POS = 'No position yet. Get a fix on the Position screen, or type one here.'
GEO_SPY = """
  window.__geo = 0;
  if (navigator.geolocation) { navigator.geolocation.watchPosition = () => { window.__geo++; return 1; };
    navigator.geolocation.getCurrentPosition = () => { window.__geo++; }; }"""


def epoch_ms(tz, *local):
    return int(datetime(*local, tzinfo=ZoneInfo(tz)).timestamp() * 1000)


def dl_boot(page, app_url, tz, local, fix=None, fix_age_min=5, storage=None):
    now = epoch_ms(tz, *local)
    page.clock.install(time=now / 1000)
    seed = dict(storage or {})
    if fix:
        seed['lastFix'] = {'lat': fix[0], 'lon': fix[1], 'alt': None, 'acc': 8, 'spd': None, 't': now - fix_age_min * 60_000}
    tools_boot(page, app_url, storage=seed, hash_=DAYLIGHT, clock=False, init=GEO_SPY)
    expect(page.locator('#survPage h2')).to_have_text('Daylight and moon')


def card(page, i):
    return page.locator('#survPage .dl-day').nth(i)


def cell(page, i, k):
    return card(page, i).locator(f'[data-k="{k}"] dd').inner_text().strip()


def minutes(text):
    """'7:26 AM' -> minutes after midnight."""
    hm, ampm = text.split()
    h, m = map(int, hm.split(':'))
    return (h % 12 + (12 if ampm == 'PM' else 0)) * 60 + m


def fixture_row(place, date):
    return next(r for r in ROWS if r['place'].startswith(place) and r['date'] == date)


def assert_card_matches(page, i, row):
    names = {'dawn': 'dawn', 'rise': 'rise', 'set': 'set', 'dusk': 'dusk'}
    for k, want in row['sun'].items():
        hh, mm = map(int, want.split(':'))
        got = minutes(cell(page, i, names[k]))
        assert abs(got - (hh * 60 + mm)) <= 2, f"{row['date']} {k}: shows {cell(page, i, k)}, reference {want}"
    for k, want in (row.get('moon') or {}).items():
        shown = cell(page, i, 'moon' + k)
        if want is None:
            assert shown.startswith('—'), f"{row['date']} moon{k}: shows {shown}"
        else:
            hh, mm = map(int, want.split(':'))
            assert abs(minutes(shown) - (hh * 60 + mm)) <= 5, f"{row['date']} moon{k}: shows {shown}, reference {want}"


def test_daylight_with_last_fix_shows_position_age_and_seven_days(ny_page, app_url):
    page = ny_page
    dl_boot(page, app_url, 'America/New_York', (2026, 11, 17, 10, 0), fix=SYR, fix_age_min=12)
    pos = page.locator('#survPage .dl-pos').inner_text()
    assert 'Last GPS fix' in pos and '12 min ago' in pos and '43.0' in pos and '76.0' in pos
    expect(page.locator('#survPage .dl-day')).to_have_count(7)
    assert card(page, 0).locator('h3').inner_text().startswith('Today')
    assert 'Wed' in card(page, 1).locator('h3').inner_text() and 'Nov 18' in card(page, 1).locator('h3').inner_text()
    labels = card(page, 0).locator('dt').all_inner_texts()
    assert labels == ['First light', 'Sunrise', 'Sunset', 'Last light', 'Day length', 'Moonrise', 'Moonset', 'Moon']
    assert 'lit' in cell(page, 0, 'phase')
    assert page.evaluate('FK.recent.all()') == ['u:daylight']
    # the tool never starts GPS (app start-up may, before the address is read, so count from a second opening)
    page.evaluate("window.__geo = 0; FK.route.go('/survival')")
    wait_hash(page, '#/survival')
    page.evaluate("FK.survival.open('u:daylight')")
    expect(page.locator('#survPage .dl-day')).to_have_count(7)
    assert page.evaluate('window.__geo') == 0


def test_daylight_clock_change_in_march_shows_local_times(ny_page, app_url):
    page = ny_page
    dl_boot(page, app_url, 'America/New_York', (2026, 3, 7, 10, 0), fix=SYR)
    for i, date in enumerate(['2026-03-07', '2026-03-08', '2026-03-09']):
        assert_card_matches(page, i, fixture_row('Syracuse', date))
    for k in ('dawn', 'rise', 'set', 'dusk'):   # on Sunday 8 March the clock jumps an hour
        jump = minutes(cell(page, 1, k)) - minutes(cell(page, 0, k))
        assert 56 <= jump <= 63, f'{k} moved {jump} min across the clock change'
    assert cell(page, 1, 'moonrise').startswith('—')   # USNO: no moonrise on 8 March


def test_daylight_clock_change_in_november_shows_local_times(ny_page, app_url):
    page = ny_page
    dl_boot(page, app_url, 'America/New_York', (2026, 10, 31, 10, 0), fix=SYR)
    for i, date in enumerate(['2026-10-31', '2026-11-01', '2026-11-02']):
        assert_card_matches(page, i, fixture_row('Syracuse', date))
    assert cell(page, 2, 'moonrise').startswith('—')   # the moon rises just after midnight on the 3rd
    assert cell(page, 2, 'phase').startswith('Waning crescent')
    assert cell(page, 1, 'phase').startswith('Last quarter')


def test_daylight_utqiagvik_june_does_not_set(ak_page, app_url):
    page = ak_page
    dl_boot(page, app_url, 'America/Anchorage', (2026, 6, 21, 12, 0), fix=UTQ)
    assert cell(page, 0, 'set') == 'Does not set'
    assert cell(page, 0, 'len') == '24 h 0 min'
    assert cell(page, 0, 'dawn') == cell(page, 0, 'dusk') == 'Light all night'   # USNO: continuously above the twilight limit
    assert_card_matches(page, 0, {**fixture_row('Utqiagvik', '2026-06-21'), 'sun': {}})   # moonrise 15:00, moonset 02:09


def test_daylight_utqiagvik_december_does_not_rise_but_has_first_and_last_light(ak_page, app_url):
    """USNO 2026-12-21: sun continuously below the horizon, civil twilight 11:56 to 14:55, moon above the horizon all day."""
    page = ak_page
    dl_boot(page, app_url, 'America/Anchorage', (2026, 12, 21, 12, 0), fix=UTQ)
    assert cell(page, 0, 'rise') == 'Does not rise'
    assert cell(page, 0, 'len') == '0 h 0 min'
    row = fixture_row('Utqiagvik', '2026-12-21')
    assert_card_matches(page, 0, {**row, 'sun': {'dawn': row['sun']['dawn'], 'dusk': row['sun']['dusk']}})
    assert cell(page, 0, 'moonrise').startswith('—') and cell(page, 0, 'moonset').startswith('—')


def test_daylight_without_fix_asks_and_accepts_a_typed_position(ny_page, app_url):
    page = ny_page
    dl_boot(page, app_url, 'America/New_York', (2026, 11, 17, 10, 0))
    assert NO_POS in page.inner_text('#survPage')
    expect(page.locator('#survPage .dl-day')).to_have_count(0)
    lat, lon = page.get_by_label('Latitude', exact=True), page.get_by_label('Longitude', exact=True)
    assert lat.bounding_box()['height'] >= 48 and lon.bounding_box()['height'] >= 48
    lat.fill('43.0')
    lon.fill('76.0')   # W is the default: no minus key needed
    use = page.get_by_role('button', name='Use this position')
    assert use.bounding_box()['height'] >= 48
    use.click()
    expect(page.locator('#survPage .dl-day')).to_have_count(7)
    assert 'Typed position' in page.locator('#survPage .dl-pos').inner_text()
    assert json.loads(page.evaluate("localStorage.getItem('fk.daylightPos')")) == {'lat': 43.0, 'lon': -76.0, 'on': True}
    page.reload()
    expect(page.locator('#survPage .dl-day')).to_have_count(7)   # remembered


def test_daylight_refuses_latitude_91_with_an_announced_message(ny_page, app_url):
    page = ny_page
    dl_boot(page, app_url, 'America/New_York', (2026, 11, 17, 10, 0))
    page.get_by_label('Latitude', exact=True).fill('91')
    page.get_by_label('Longitude', exact=True).fill('76.0')
    page.get_by_role('button', name='Use this position').click()
    alert = page.locator('#survPage [role="alert"]')
    expect(alert).to_have_text('Latitude must be a number from 0 to 90.')
    expect(page.locator('#survPage .dl-day')).to_have_count(0)
    assert page.evaluate("localStorage.getItem('fk.daylightPos')") is None
    page.get_by_label('Longitude', exact=True).fill('181')
    page.get_by_label('Latitude', exact=True).fill('43')
    page.get_by_role('button', name='Use this position').click()
    expect(alert).to_have_text('Longitude must be a number from 0 to 180.')
    page.get_by_label('Latitude', exact=True).fill('abc')
    page.get_by_role('button', name='Use this position').click()
    expect(alert).to_have_text('Latitude must be a number from 0 to 90.')
    page.get_by_label('Latitude', exact=True).fill('-43')   # the sign is chosen with N / S, not typed
    page.get_by_role('button', name='Use this position').click()
    expect(alert).to_have_text('Latitude must be a number from 0 to 90.')


def test_daylight_typed_position_is_used_only_when_chosen(ny_page, app_url):
    page = ny_page
    dl_boot(page, app_url, 'America/New_York', (2026, 11, 17, 10, 0), fix=SYR,
            storage={'daylightPos': {'lat': 10, 'lon': 20, 'on': False}})
    assert 'Last GPS fix' in page.locator('#survPage .dl-pos').inner_text()
    page.get_by_role('button', name='Type a position').click()
    expect(page.get_by_label('Latitude', exact=True)).to_have_value('10')   # the remembered one is offered
    page.get_by_role('button', name='Use this position').click()
    assert 'Typed position' in page.locator('#survPage .dl-pos').inner_text()
    page.get_by_role('button', name='Use last GPS fix').click()
    assert 'Last GPS fix' in page.locator('#survPage .dl-pos').inner_text()
    assert json.loads(page.evaluate("localStorage.getItem('fk.daylightPos')")) == {'lat': 10, 'lon': 20, 'on': False}


def test_daylight_ignores_malformed_stored_positions(ny_page, app_url):
    page = ny_page
    dl_boot(page, app_url, 'America/New_York', (2026, 11, 17, 10, 0),
            storage={'lastFix': {'lat': 'x<b>', 'lon': 500, 't': 'now'}, 'daylightPos': {'lat': 95, 'lon': '<i>', 'on': True}})
    assert NO_POS in page.inner_text('#survPage')
    expect(page.locator('#survPage .dl-day')).to_have_count(0)
    assert page.locator('#survPage b, #survPage i').count() == 0
    expect(page.get_by_label('Latitude', exact=True)).to_have_value('')


def test_search_finds_daylight_by_sunrise_and_moon(page, app_url):
    boot(page, app_url, '#/survival')
    page.click('#searchBtn')
    for q in ('sunrise', 'moon'):
        page.fill('#searchInput', q)
        expect(page.locator('#searchBody .sr-item[data-key="u:daylight"]')).to_have_count(1)
    page.click('#searchBody .sr-item[data-key="u:daylight"]')
    wait_hash(page, DAYLIGHT)
    expect(page.locator('#survPage h2')).to_have_text('Daylight and moon')


# ---------- Final fix wave ----------

def test_f3_update_bar_waits_while_the_light_runs(page, app_url):
    boot(page, app_url, SOS)
    bar = page.locator('#updBar')
    page.evaluate('FK.updateAvailable()')
    expect(bar).to_be_visible()
    assert page.evaluate('FK.survival.lightOn()') is False
    start(page)
    assert page.evaluate('FK.survival.lightOn()') is True
    expect(bar).to_be_hidden()   # its Reload would end the light
    page.locator(PANEL).click()
    assert page.evaluate('FK.survival.lightOn()') is False
    expect(bar).to_be_visible()
    page.get_by_role('button', name='Steady light').click()
    expect(bar).to_be_hidden()
    page.evaluate("FK.route.go('/survival')")   # leaving the page ends the light
    wait_hash(page, '#/survival')
    assert page.evaluate('FK.survival.lightOn()') is False
    expect(bar).to_be_visible()


def test_f10_start_button_names_what_is_running(page, app_url):
    boot(page, app_url, SOS)
    page.get_by_role('button', name='Steady light').click()
    assert page.locator('#svSosStart').inner_text() == 'Stop light'
    page.locator(PANEL).click()
    assert page.locator('#svSosStart').inner_text() == 'Start SOS'
    start(page)
    assert page.locator('#svSosStart').inner_text() == 'Stop SOS'


def test_f10_escape_stops_the_light(page, app_url):
    boot(page, app_url, SOS)
    for which in ('Start SOS', 'Steady light'):
        page.get_by_role('button', name=which).click()
        expect(page.locator(PANEL)).to_be_visible()
        page.keyboard.press('Escape')
        expect(page.locator(PANEL)).to_be_hidden()
        expect(page.get_by_role('button', name=which)).to_be_focused()
    page.clock.run_for(UNIT * 40)
    expect(page.locator(PANEL)).to_be_hidden()


def test_f4_cards_move_on_when_midnight_passes_with_the_page_open(ny_page, app_url):
    page = ny_page
    dl_boot(page, app_url, 'America/New_York', (2026, 11, 17, 23, 58), fix=SYR)
    assert 'Nov 17' in card(page, 0).locator('h3').inner_text()
    page.clock.run_for(3 * 60_000)
    expect(card(page, 0).locator('h3')).to_contain_text('Nov 18')
    assert card(page, 0).locator('h3').inner_text().startswith('Today')


def test_f4_cards_move_on_when_the_page_becomes_visible_again(ny_page, app_url):
    page = ny_page
    dl_boot(page, app_url, 'America/New_York', (2026, 11, 17, 23, 58), fix=SYR)
    page.clock.pause_at(epoch_ms('America/New_York', 2026, 11, 17, 23, 59) / 1000)
    page.clock.set_fixed_time(epoch_ms('America/New_York', 2026, 11, 18, 9, 0) / 1000)   # the phone slept: no timer ran
    assert 'Nov 17' in card(page, 0).locator('h3').inner_text()
    page.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
    expect(card(page, 0).locator('h3')).to_contain_text('Nov 18')


def test_f4_leaving_the_page_stops_its_timer_and_listener(ny_page, app_url):
    page = ny_page
    dl_boot(page, app_url, 'America/New_York', (2026, 11, 17, 23, 58), fix=SYR)
    page.evaluate("FK.route.go('/survival')")
    wait_hash(page, '#/survival')
    page.evaluate("""() => { window.__redrawn = 0; const S = window.FK_ASTRO.sun;
      window.FK_ASTRO.sun = (...a) => { window.__redrawn++; return S(...a); }; }""")
    page.clock.run_for(3 * 60_000)
    page.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
    assert page.evaluate('window.__redrawn') == 0


FULL_POS = """() => {
  const orig = Storage.prototype.setItem;
  Storage.prototype.setItem = function (k, v) { if (k === 'fk.daylightPos') throw new DOMException('full', 'QuotaExceededError'); return orig.call(this, k, v); };
}"""


def test_f7_typed_position_is_used_even_when_storage_is_full(ny_page, app_url):
    page = ny_page
    dl_boot(page, app_url, 'America/New_York', (2026, 11, 17, 10, 0))
    page.evaluate(FULL_POS)
    page.get_by_label('Latitude', exact=True).fill('43.0')
    page.get_by_label('Longitude', exact=True).fill('76.0')
    page.get_by_role('button', name='Use this position').click()
    expect(page.locator('#survPage .dl-day')).to_have_count(7)
    assert 'Typed position' in page.locator('#survPage .dl-pos').inner_text()
    assert page.inner_text('#toast') == "Couldn’t save: phone storage for Field Kit is full. Back up, then delete old tracks or saved maps."
    assert page.evaluate("localStorage.getItem('fk.daylightPos')") is None


def hem(page, name):
    return page.get_by_role('radio', name=name, exact=True)


def test_f8_position_is_typed_without_a_sign_and_chosen_with_n_s_and_w_e(ny_page, app_url):
    page = ny_page
    dl_boot(page, app_url, 'America/New_York', (2026, 11, 17, 10, 0))
    lat, lon = page.get_by_label('Latitude', exact=True), page.get_by_label('Longitude', exact=True)
    for f in (lat, lon):
        assert f.get_attribute('inputmode') == 'decimal'
    expect(hem(page, 'North')).to_be_checked()
    expect(hem(page, 'West')).to_be_checked()
    for n in ('North', 'South', 'West', 'East'):
        b = page.locator('#survPage label', has=hem(page, n)).bounding_box()
        assert b['height'] >= 48 and b['width'] >= 48, n
    assert page.locator('#survPage [role="radiogroup"]').evaluate_all('g => g.map(e => e.getAttribute("aria-label"))') == \
        ['Latitude: north or south', 'Longitude: west or east']
    lat.fill('33,87')   # a comma works as the decimal separator
    lon.fill('151,21')
    page.locator('#survPage label', has=hem(page, 'South')).click()
    page.locator('#survPage label', has=hem(page, 'East')).click()
    page.get_by_role('button', name='Use this position').click()
    expect(page.locator('#survPage .dl-day')).to_have_count(7)
    assert json.loads(page.evaluate("localStorage.getItem('fk.daylightPos')")) == {'lat': -33.87, 'lon': 151.21, 'on': True}
    assert '33.8700° S, 151.2100° E' in page.locator('#survPage .dl-pos').inner_text()


def test_f8_a_stored_signed_position_loads_with_the_right_directions(ny_page, app_url):
    page = ny_page
    dl_boot(page, app_url, 'America/New_York', (2026, 11, 17, 10, 0), storage={'daylightPos': {'lat': 43.0, 'lon': -76.0, 'on': True}})
    expect(page.locator('#survPage .dl-day')).to_have_count(7)
    assert '43.0000° N, 76.0000° W' in page.locator('#survPage .dl-pos').inner_text()
    page.get_by_role('button', name='Change position').click()
    expect(page.get_by_label('Latitude', exact=True)).to_have_value('43')
    expect(page.get_by_label('Longitude', exact=True)).to_have_value('76')
    expect(hem(page, 'North')).to_be_checked()
    expect(hem(page, 'West')).to_be_checked()
    page.get_by_role('button', name='Use this position').click()
    assert json.loads(page.evaluate("localStorage.getItem('fk.daylightPos')")) == {'lat': 43.0, 'lon': -76.0, 'on': True}


def test_f14_position_screen_is_a_button_that_opens_it(ny_page, app_url):
    page = ny_page
    dl_boot(page, app_url, 'America/New_York', (2026, 11, 17, 10, 0))
    btn = page.get_by_role('button', name='Position screen')
    assert btn.bounding_box()['height'] >= 48
    btn.click()
    page.wait_for_function("location.hash === '#/tactical/position'")


# ---------- Wind chill (#/survival/tool/windchill) ----------
WC = '#/survival/tool/windchill'
OFF_CHART = 'Off the National Weather Service chart. No figure is shown.'
WC_MISSING = 'The wind chill tool’s numbers are not available yet. Nothing is shown until they have been checked against sources.'
WHOLE = 'Enter a whole number.'
NO_BAND = 'Fixture: no frostbite time is shaded at this wind chill.'
CONSTS = {k: {'value': v, 'unit': u, 'note': 'fixture'} for k, v, u in
          (('c0', 35.74, '°F'), ('cT', 0.6215, ''), ('cV', 35.75, ''), ('cTV', 0.4275, ''), ('exp', 0.16, ''))}


def js_round(x):
    return math.floor(x + 0.5)


def formula(t, v, c=CONSTS):
    e = v ** c['exp']['value']
    return js_round(c['c0']['value'] + c['cT']['value'] * t - c['cV']['value'] * e + c['cTV']['value'] * t * e)


def make_wc(temps, winds, bands, **extra):
    chill = [[formula(t, v) for t in temps] for v in winds]
    d = {'id': 'windchill', 'title': NO_BAND, 'values': CONSTS,
         'grid': {'temps': temps, 'winds': winds, 'chill': chill, 'bands': bands, 'bandMinutes': [5, 10, 30]},
         'sources': [{'name': 'Fixture weather service', 'used': 'formula'}, {'name': 'Second source', 'used': 'chart'}],
         'reviewed': '2026-11-18'}
    d.update(extra)
    return d


SMALL = make_wc([10, 0, -10], [5, 15, 30], [[0, 0, 30], [0, 30, 10], [30, 10, 5]])
REAL_T = list(range(40, -50, -5))
REAL_V = list(range(5, 65, 5))


def real_band(t, v):
    c = formula(t, v)
    return 0 if c > -19 else 30 if c > -35 else 10 if c > -48 else 5


REAL = make_wc(REAL_T, REAL_V, [[real_band(t, v) for t in REAL_T] for v in REAL_V])


def wc_boot(page, app_url, data=SMALL, hash_=WC, storage=None, topics=None, night=False):
    page.set_default_timeout(4000)
    kw = {'topics': topics} if topics is not None else {}
    inject_data(page, tooldata={'windchill': data} if data is not None else {'other': {'id': 'other'}}, only=True, **kw)
    seed = {'fk.advAck': 'true', **({'fk.night': 'true'} if night else {}), **{'fk.' + k: json.dumps(v) for k, v in (storage or {}).items()}}
    page.add_init_script("if (!sessionStorage.getItem('seeded')) { sessionStorage.setItem('seeded', '1'); const d = %s;"
                         " for (const k in d) localStorage.setItem(k, d[k]); }" % json.dumps(seed))
    page.goto(app_url + hash_)
    page.wait_for_function('window.FK && FK.survival && FK.survival.tools')


def wc_in(page, temp, wind):
    t = page.locator('#survPage').get_by_label('Air temperature (°F)', exact=True)
    w = page.locator('#survPage').get_by_label('Wind (mph)', exact=True)
    for f, v in ((t, str(temp)), (w, str(wind))):
        if v == '':
            f.fill('0')   # a field that was never typed in has nothing to say; typing and then clearing it does
        f.fill(v)
    return t, w


def wc_out(page):
    return page.locator('#survPage .wc-res').inner_text()


def wc_clean(page):
    t = page.inner_text('#survPage')
    assert 'NaN' not in t and 'Infinity' not in t and 'undefined' not in t, t
    return t


def wc_nothing(page):
    """No figure, no band."""
    t = wc_clean(page)
    assert 'Feels like' not in t and 'Frostbite possible' not in t
    assert page.locator('#survPage [data-k="chill"], #survPage [data-k="band"]').count() == 0
    return t


def wc_expect(page, chill, band):
    expect(page.locator('#survPage [data-k="chill"]')).to_have_text(f'Feels like {chill}°F')
    if band:
        expect(page.locator('#survPage [data-k="band"]')).to_have_text(f'Frostbite possible in about {band} minutes on exposed skin')
    else:
        expect(page.locator('#survPage [data-k="band"]')).to_have_text(NO_BAND)


def test_wc_initial_state_has_two_empty_labelled_fields_no_result_no_error(page, app_url):
    wc_boot(page, app_url)
    expect(page.locator('#survPage h2')).to_have_text('Wind chill')
    for name in ('Air temperature (°F)', 'Wind (mph)'):
        f = page.locator('#survPage').get_by_label(name, exact=True)
        assert f.input_value() == ''
    t = wc_nothing(page)
    assert WHOLE not in t and OFF_CHART not in t and WC_MISSING not in t
    assert page.locator('#survPage .wc-err').all_inner_texts() == ['', '']
    assert page.evaluate('FK.recent.all()') == ['u:windchill']


def test_wc_one_filled_field_shows_nothing_for_the_other(page, app_url):
    wc_boot(page, app_url)
    page.locator('#survPage').get_by_label('Air temperature (°F)', exact=True).fill('0')
    t = wc_nothing(page)
    assert WHOLE not in t and OFF_CHART not in t


@pytest.mark.parametrize('fx', [SMALL, REAL], ids=['small', 'real-shape'])
def test_wc_every_cell_returns_its_own_chill_and_band(page, app_url, fx):
    wc_boot(page, app_url, fx)
    g = fx['grid']
    for wi, v in enumerate(g['winds']):
        for ti, t in enumerate(g['temps']):
            wc_in(page, t, v)
            wc_expect(page, g['chill'][wi][ti], g['bands'][wi][ti])
            wc_clean(page)


def test_wc_the_four_corners_and_every_edge_cell_return_their_own_band(page, app_url):
    wc_boot(page, app_url)
    # (temp, wind) -> band, read off SMALL by hand: rows are winds 5, 15, 30; columns temps 10, 0, -10
    for (t, v), band in {(10, 5): 0, (-10, 5): 30, (10, 30): 30, (-10, 30): 5,   # corners
                         (0, 5): 0, (10, 15): 0, (-10, 15): 10, (0, 30): 10}.items():   # edge middles
        wc_in(page, t, v)
        wc_expect(page, formula(t, v), band)


def test_wc_between_cells_the_band_is_the_next_colder_temp_and_higher_wind_but_the_formula_uses_the_real_inputs(page, app_url):
    wc_boot(page, app_url)
    # T=-3 is between 0 and -10: use -10. V=10 is between 5 and 15: use 15. Band = bands[15][-10] = 10
    wc_in(page, -3, 10)
    wc_expect(page, formula(-3, 10), 10)
    assert formula(-3, 10) not in (formula(-10, 15), formula(0, 5))
    # T=9 uses 0, V=6 uses 15: bands[15][0] = 30
    wc_in(page, 9, 6)
    wc_expect(page, formula(9, 6), 30)
    # on a chart temperature, between winds: V=16 uses 30
    wc_in(page, 10, 16)
    wc_expect(page, formula(10, 16), 30)
    # on a chart wind, between temperatures: T=-1 uses -10, V=15 uses 15
    wc_in(page, -1, 15)
    wc_expect(page, formula(-1, 15), 10)


def test_wc_between_cells_on_the_real_shape_chart(page, app_url):
    wc_boot(page, app_url, REAL)
    g = REAL['grid']
    for t, v in ((-12, 13), (7, 59), (39, 6), (-44, 1 + 5)):
        ti = min(i for i, x in enumerate(g["temps"]) if x <= t)   # largest chart temp <= t
        wi = min(i for i, x in enumerate(g['winds']) if x >= v)
        wc_in(page, t, v)
        wc_expect(page, formula(t, v), g['bands'][wi][ti])


def test_wc_a_band_of_zero_shows_the_wind_chill_and_the_datas_own_no_band_sentence(page, app_url):
    wc_boot(page, app_url)
    wc_in(page, 10, 5)
    wc_expect(page, formula(10, 5), 0)
    assert 'Frostbite possible' not in wc_out(page)
    assert NO_BAND in wc_out(page)


def test_wc_source_name_is_the_first_source_under_the_result(page, app_url):
    wc_boot(page, app_url)
    wc_in(page, 0, 15)
    out = wc_out(page)
    assert out.rstrip().endswith('Source: Fixture weather service'), out
    assert 'Second source' not in out


@pytest.mark.parametrize('temp,wind', [
    ('', ''), ('abc', '10'), ('0', 'abc'), ('12.7', '10'), ('0', '12.7'), ('1e9', '10'), ('0', '1e9'), ('', '10'), ('0', ''),
    ('--5', '10'), ('5-', '10'), (' ', '10'), ('0x10', '10'), ('+5', '10'), ('1,5', '10'), ('Infinity', '10'), ('NaN', '10'),
], ids=repr)
def test_review_focus_1_invalid_fields_show_a_plain_message_and_no_figure(page, app_url, temp, wind):
    wc_boot(page, app_url)
    wc_in(page, temp, wind)
    t = wc_nothing(page)
    assert OFF_CHART not in t
    # every typed field that is not a whole number (a blank one included) says so under itself
    expected = [WHOLE if not re.fullmatch(r'-?\d+', v.strip()) else '' for v in (temp, wind)]
    assert page.locator('#survPage .wc-err').all_inner_texts() == expected


@pytest.mark.parametrize('wind', ['-5', '0', '-1', '4', '61', '1000000000', '99999999999999999999999999'])
def test_review_focus_1_wind_outside_the_chart_is_off_chart_with_no_figure(page, app_url, wind):
    wc_boot(page, app_url, REAL)
    wc_in(page, 0, wind)
    t = wc_nothing(page)
    assert OFF_CHART in t and WHOLE not in t


@pytest.mark.parametrize('temp', ['41', '-46', '1000000000', '-1000000000'])
def test_review_focus_1_temperature_outside_the_chart_is_off_chart_with_no_figure(page, app_url, temp):
    wc_boot(page, app_url, REAL)
    wc_in(page, temp, 10)
    t = wc_nothing(page)
    assert OFF_CHART in t and WHOLE not in t


def test_review_focus_2_one_step_outside_every_edge_is_off_chart(page, app_url):
    wc_boot(page, app_url)
    for t, v in ((11, 15), (-11, 15), (0, 4), (0, 31), (11, 4), (-11, 31)):   # SMALL spans -10..10 and 5..30
        wc_in(page, t, v)
        assert OFF_CHART in wc_nothing(page), (t, v)
    for t, v in ((10, 5), (-10, 30), (-10, 5), (10, 30)):   # and the edges themselves are on the chart
        wc_in(page, t, v)
        assert OFF_CHART not in wc_clean(page)
        assert page.locator('#survPage [data-k="chill"]').count() == 1


def test_wc_whitespace_around_a_whole_number_is_accepted_and_a_minus_sign_is_allowed(page, app_url):
    wc_boot(page, app_url)
    wc_in(page, ' -10 ', ' 30 ')
    wc_expect(page, formula(-10, 30), 5)


def test_wc_typographic_minus_is_a_minus_sign(page, app_url):
    # U+2212 is what the stepper button shows and what some keyboards and pasted text produce
    wc_boot(page, app_url)
    wc_in(page, '\u22125', '10')
    wc_expect(page, formula(-5, 10), SMALL['grid']['bands'][1][2])   # -5 -> chart -10, 10 -> 15
    wc_in(page, ' \u221210 ', '30')
    wc_expect(page, formula(-10, 30), 5)
    page.get_by_role('button', name='One degree warmer', exact=True).click()
    assert page.locator('#survPage').get_by_label('Air temperature (°F)', exact=True).input_value() == '-9'


@pytest.mark.parametrize('temp', ['\u2212', '\u2212\u22125', '-\u22125', '5\u2212', '\u2212 5', '\u22125.5', '\u2013 5', '\u20135'], ids=repr)
def test_wc_typographic_minus_does_not_let_other_malformed_input_through(page, app_url, temp):
    wc_boot(page, app_url)
    wc_in(page, temp, '10')
    wc_nothing(page)
    assert page.locator('#survPage .wc-err').all_inner_texts() == [WHOLE, '']


def test_wc_temperature_field_gets_a_keyboard_with_a_minus_and_wind_stays_numeric(page, app_url):
    # iPhone number pads (numeric and decimal) have no minus key; temperatures below zero are what the tool is for
    wc_boot(page, app_url)
    t = page.locator('#survPage').get_by_label('Air temperature (°F)', exact=True)
    w = page.locator('#survPage').get_by_label('Wind (mph)', exact=True)
    assert t.get_attribute('type') == 'text' and t.get_attribute('inputmode') == 'text'
    assert (t.get_attribute('autocapitalize'), t.get_attribute('autocorrect'), t.get_attribute('spellcheck')) == ('off', 'off', 'false')
    assert w.get_attribute('type') == 'text' and w.get_attribute('inputmode') == 'numeric'


def test_wc_error_sits_under_its_own_field_and_marks_it_invalid(page, app_url):
    wc_boot(page, app_url)
    t, w = wc_in(page, 'abc', '10')
    assert t.get_attribute('aria-invalid') == 'true' and w.get_attribute('aria-invalid') != 'true'
    err = page.locator('#survPage .wc-err').first
    assert err.inner_text() == WHOLE
    desc = t.get_attribute('aria-describedby')
    assert err.get_attribute('id') in desc.split()
    assert err.bounding_box()['y'] > t.bounding_box()['y']
    t.fill('0')
    assert page.locator('#survPage .wc-err').all_inner_texts() == ['', '']
    assert t.get_attribute('aria-invalid') != 'true'


def test_wc_steppers_step_by_one_across_zero_and_are_48px(page, app_url):
    wc_boot(page, app_url)
    wc_in(page, 1, 10)
    colder = page.get_by_role('button', name='One degree colder', exact=True)
    warmer = page.get_by_role('button', name='One degree warmer', exact=True)
    for b in (colder, warmer, page.get_by_role('button', name='One mph more', exact=True), page.get_by_role('button', name='One mph less', exact=True)):
        box = b.bounding_box()
        assert box['width'] >= 48 and box['height'] >= 48
    colder.click()
    colder.click()
    t = page.locator('#survPage').get_by_label('Air temperature (°F)', exact=True)
    assert t.input_value() == '-1'
    wc_expect(page, formula(-1, 10), SMALL['grid']['bands'][1][2])   # -1 -> chart -10, 10 -> 15
    warmer.click()
    assert t.input_value() == '0'
    page.get_by_role('button', name='One mph more', exact=True).click()
    assert page.locator('#survPage').get_by_label('Wind (mph)', exact=True).input_value() == '11'
    wc_expect(page, formula(0, 11), SMALL['grid']['bands'][1][1])


def test_wc_a_stepper_on_an_invalid_field_starts_from_zero(page, app_url):
    wc_boot(page, app_url)
    t, w = wc_in(page, 'abc', '')
    page.get_by_role('button', name='One degree warmer', exact=True).click()
    page.get_by_role('button', name='One mph more', exact=True).click()
    assert t.input_value() == '1' and w.input_value() == '1'
    assert page.locator('#survPage .wc-err').all_inner_texts() == ['', '']


def test_wc_keyboard_only_use(page, app_url):
    wc_boot(page, app_url)
    assert page.evaluate('document.activeElement.id') == 'svTitle'
    names = []
    for _ in range(6):
        page.keyboard.press('Tab')
        names.append(page.evaluate('document.activeElement.getAttribute("aria-label") || document.activeElement.dataset.act || document.activeElement.id'))
    assert names[:6] == ['Pin this tool', 'One degree colder', 'wcT', 'One degree warmer', 'One mph less', 'wcV'], names
    page.keyboard.press('Shift+Tab'); page.keyboard.press('Shift+Tab'); page.keyboard.press('Shift+Tab')   # back to the temperature field
    assert page.evaluate('document.activeElement.id') == 'wcT'
    page.keyboard.type('-3')
    page.keyboard.press('Tab'); page.keyboard.press('Tab'); page.keyboard.press('Tab')
    assert page.evaluate('document.activeElement.id') == 'wcV'
    page.keyboard.type('10')
    page.keyboard.press('Tab')
    assert page.evaluate('document.activeElement.getAttribute("aria-label")') == 'One mph more'
    page.keyboard.press('Space')   # 11
    wc_expect(page, formula(-3, 11), 10)


def test_wc_result_is_announced_politely(page, app_url):
    wc_boot(page, app_url)
    assert page.locator('#survPage .wc-res').get_attribute('role') == 'status' or page.locator('#survPage .wc-res').get_attribute('aria-live') == 'polite'


def test_wc_nothing_is_saved(page, app_url):
    wc_boot(page, app_url)
    before = page.evaluate('JSON.stringify(Object.entries(localStorage).sort())')
    wc_in(page, -3, 10)
    page.get_by_role('button', name='One mph more', exact=True).click()
    assert page.evaluate('JSON.stringify(Object.entries(localStorage).sort())') == before
    page.reload()
    page.wait_for_function('window.FK && FK.survival && FK.survival.tools')
    assert page.locator('#survPage').get_by_label('Wind (mph)', exact=True).input_value() == ''
    wc_nothing(page)


@pytest.mark.parametrize('night', [False, True])
def test_wc_fits_360px_in_day_and_night_with_every_state(page, app_url, night):
    wc_boot(page, app_url, REAL, night=night)
    assert (page.evaluate("document.documentElement.dataset.theme") == 'night') is night

    def fits():
        assert page.evaluate('document.documentElement.scrollWidth') <= 360
        over = page.evaluate("""[...document.querySelectorAll('#survPage *')].filter(el => {
            const r = el.getBoundingClientRect(); return r.width && (r.right > innerWidth + 0.5 || r.left < -0.5); }).map(el => el.outerHTML.slice(0, 80))""")
        assert over == []
    fits()
    wc_in(page, -45, 60)
    wc_expect(page, formula(-45, 60), real_band(-45, 60))
    fits()
    wc_in(page, 40, 5)
    fits()
    wc_in(page, 'abc', 1000000000)
    fits()
    wc_in(page, 99, 99)
    fits()
    if night:   # text stays readable: result text is not the same colour as its panel
        res = page.evaluate("(() => { const c = getComputedStyle(document.querySelector('#survPage .wp-out')); return [c.color, c.backgroundColor]; })()")
        assert res[0] != res[1]


@pytest.mark.parametrize('data', [
    None,
    {**SMALL, 'draft': True},
    {k: v for k, v in SMALL.items() if k != 'grid'},
    {k: v for k, v in SMALL.items() if k != 'values'},
    {**SMALL, 'values': {**CONSTS, 'exp': {'value': 'x'}}},
    {**SMALL, 'values': {**CONSTS, 'c0': {'value': None}}},
    {**SMALL, 'values': {k: v for k, v in CONSTS.items() if k != 'cTV'}},
    {**SMALL, 'values': {**CONSTS, 'cV': 35.75}},
    {**SMALL, 'grid': {**SMALL['grid'], 'chill': SMALL['grid']['chill'][:2]}},
    {**SMALL, 'grid': {**SMALL['grid'], 'chill': [r[:2] if i == 1 else r for i, r in enumerate(SMALL['grid']['chill'])]}},   # ragged chill row
    {**SMALL, 'grid': {**SMALL['grid'], 'bands': [r[:2] if i == 1 else r for i, r in enumerate(SMALL['grid']['bands'])]}},   # ragged band row
    {**SMALL, 'grid': {**SMALL['grid'], 'bands': SMALL['grid']['bands'] + [[0, 0, 0]]}},
    {**SMALL, 'grid': {**SMALL['grid'], 'bands': [[0, 0, 7], [0, 30, 10], [30, 10, 5]]}},   # band not in the allowed set
    {**SMALL, 'grid': {**SMALL['grid'], 'bands': [[0, 0, '30'], [0, 30, 10], [30, 10, 5]]}},
    {**SMALL, 'grid': {**SMALL['grid'], 'temps': [10, -10, 0]}},   # not descending
    {**SMALL, 'grid': {**SMALL['grid'], 'temps': [10, 10, -10]}},   # not strictly
    {**SMALL, 'grid': {**SMALL['grid'], 'temps': [-10, 0, 10]}},   # ascending
    {**SMALL, 'grid': {**SMALL['grid'], 'winds': [5, 30, 15]}},   # not ascending
    {**SMALL, 'grid': {**SMALL['grid'], 'winds': [0, 15, 30]}},   # wind must be above zero
    {**SMALL, 'grid': {**SMALL['grid'], 'winds': [-5, 15, 30]}},
    {**SMALL, 'grid': {**SMALL['grid'], 'winds': [5, 15, 15]}},
    {**SMALL, 'grid': {k: v for k, v in SMALL['grid'].items() if k != 'bandMinutes'}},
    {**SMALL, 'grid': {**SMALL['grid'], 'bandMinutes': []}},
    {**SMALL, 'grid': {**SMALL['grid'], 'temps': []}},
    {**SMALL, 'grid': 'grid'},
    {**SMALL, 'grid': {**SMALL['grid'], 'temps': [10, 0, None]}},
    {**SMALL, 'grid': {**SMALL['grid'], 'chill': [[None, 1, 2], [0, 0, 0], [0, 0, 0]]}},
], ids=lambda d: 'none' if d is None else format(zlib.crc32(json.dumps(d, sort_keys=True).encode()), 'x'))
def test_review_focus_3_missing_draft_or_damaged_data_shows_only_the_not_available_message(page, app_url, data):
    wc_boot(page, app_url, data)
    t = wc_nothing(page)
    assert WC_MISSING in t
    assert page.locator('#survPage input, #survPage .sv-step, #survPage .wc-res, #survPage .sv-link').count() == 0
    assert OFF_CHART not in t and WHOLE not in t


def test_wc_a_band_of_zero_with_no_sentence_in_the_data_is_not_shown_as_a_figure(page, app_url):
    wc_boot(page, app_url, {**SMALL, 'title': ' '})
    wc_in(page, 10, 5)
    t = wc_clean(page)
    assert WC_MISSING in t and 'Feels like' not in t
    wc_in(page, -10, 30)   # a banded cell does not need the sentence
    wc_expect(page, formula(-10, 30), 5)


def test_wc_data_text_is_shown_as_text(page, app_url):
    wc_boot(page, app_url, {**SMALL, 'title': 'T ' + XSS, 'sources': [{'name': 'S ' + XSS, 'used': 'U ' + XSS}]})
    wc_in(page, 10, 5)
    page.evaluate('new Promise(r => setTimeout(r, 50))')
    assert page.evaluate('window.__xss') is None
    assert page.locator('#survPage img').count() == 0
    out = wc_out(page)
    assert 'T ' + XSS in out and 'S ' + XSS in out


def test_wc_links_appear_only_for_keys_that_resolve(page, app_url):
    wc_boot(page, app_url, topics=[])   # no surv-wind-chill topic (one ships from batch C): the hypothermia and frostbite protocols are shipped
    links = page.locator('#survPage .sv-link')
    assert links.evaluate_all('els => els.map(e => e.dataset.link)') == ['p:hypothermia', 'p:frostbite']
    assert page.locator('#survPage button[data-link="s:surv-wind-chill"]').count() == 0
    assert all(links.nth(i).bounding_box()['height'] >= 48 for i in range(2))


def test_wc_links_include_the_topic_once_it_exists_and_open_it(page, app_url):
    wc_boot(page, app_url, topics=[topic('surv-wind-chill', 'Wind chill and cold exposure', [{'h': 'Only', 'blocks': [{'p': 'Body.'}]}])])
    links = page.locator('#survPage .sv-link')
    assert links.evaluate_all('els => els.map(e => e.dataset.link)') == ['s:surv-wind-chill', 'p:hypothermia', 'p:frostbite']
    links.first.click()
    wait_hash(page, '#/survival/surv-wind-chill')
    expect(page.locator('#survPage h2')).to_have_text('Wind chill and cold exposure')


def test_wc_links_lead_with_the_shipped_wind_chill_topic(page, app_url):
    wc_boot(page, app_url)   # shipped topics: batch C's surv-wind-chill resolves
    links = page.locator('#survPage .sv-link')
    assert links.evaluate_all('els => els.map(e => e.dataset.link)') == ['s:surv-wind-chill', 'p:hypothermia', 'p:frostbite']
    assert 'Wind chill and cold danger' in links.first.inner_text()


def test_wc_link_opens_the_emergency_protocol(page, app_url):
    wc_boot(page, app_url)
    page.locator('#survPage button[data-link="p:frostbite"]').click()
    page.wait_for_function("location.hash.includes('frostbite')")


def test_wc_is_on_the_survival_home_and_search_finds_it_by_wind_chill_and_frostbite(page, app_url):
    wc_boot(page, app_url, hash_='#/survival')
    assert page.locator('#survTools button[data-key="u:windchill"]').inner_text().startswith('Wind chill')
    page.locator('#survTools button[data-key="u:windchill"]').click()
    wait_hash(page, WC)
    page.go_back()
    wait_hash(page, '#/survival')
    page.click('#searchBtn')
    for words in ('wind chill', 'frostbite', 'windchill', 'feels like'):
        page.fill('#searchInput', words)
        expect(page.locator('#searchBody .sr-item[data-key="u:windchill"]')).to_have_count(1)
    page.click('#searchBody .sr-item[data-key="u:windchill"]')
    wait_hash(page, WC)
    expect(page.locator('#survPage h2')).to_have_text('Wind chill')


def test_wc_pin_star_pins_the_tool(page, app_url):
    wc_boot(page, app_url)
    page.click('#survPage .sv-head [data-act="pin"]')
    assert page.evaluate("FK.pins.has('u:windchill')") is True


def test_wc_leaving_the_page_leaves_no_listeners_that_break(page, app_url):
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
    wc_boot(page, app_url)
    wc_in(page, 0, 10)
    page.evaluate("FK.route.go('/survival')")
    wait_hash(page, '#/survival')
    assert errors == []


# ---------- Wind chill: the shipped NWS chart (src/tooldata/windchill.json) ----------
SHIPPED_WC = json.loads((__import__('pathlib').Path(__file__).resolve().parent.parent / 'src' / 'tooldata' / 'windchill.json').read_text(encoding='utf-8'))


def test_wc_shipped_every_chart_cell_is_the_nws_formula_with_the_files_constants():
    """Every transcribed cell is reproduced by the formula, with the file's own constants and JS Math.round."""
    g = SHIPPED_WC['grid']
    assert len(g['chill']) == len(g['winds']) and all(len(r) == len(g['temps']) for r in g['chill'])
    wrong = [(v, t, g['chill'][wi][ti], formula(t, v, SHIPPED_WC['values']))
             for wi, v in enumerate(g['winds']) for ti, t in enumerate(g['temps'])
             if g['chill'][wi][ti] != formula(t, v, SHIPPED_WC['values'])]
    assert wrong == [], 'cells (wind, temp, chart, formula) that the formula does not reproduce: %r' % wrong
    assert len(g['winds']) * len(g['temps']) == 216


def test_wc_shipped_build_shows_nothing_while_the_file_is_a_draft_and_a_figure_once_it_is_not(page, app_url):
    """The built app with no injected data, at 0°F and 15 mph."""
    page.set_default_timeout(4000)
    page.add_init_script("localStorage.setItem('fk.advAck', 'true')")
    page.goto(app_url + WC)
    page.wait_for_function('window.FK && FK.survival && FK.survival.tools')
    if SHIPPED_WC.get('draft') is True:
        expect(page.locator('#survPage')).to_contain_text(WC_MISSING)
        assert 'Feels like' not in wc_clean(page)
    else:
        wc_in(page, 0, 15)
        expect(page.locator('#survPage [data-k="chill"]')).to_have_text('Feels like -19°F')


def test_wc_shipped_file_undrafted_shows_a_figure_for_a_mid_chart_input(page, app_url):
    """0°F and 15 mph, the NWS example: -19°F, with the file's own no-band sentence and first source."""
    wc_boot(page, app_url, {k: v for k, v in SHIPPED_WC.items() if k != 'draft'})
    wc_in(page, 0, 15)
    expect(page.locator('#survPage [data-k="chill"]')).to_have_text('Feels like -19°F')
    expect(page.locator('#survPage [data-k="band"]')).to_have_text(SHIPPED_WC['title'])
    assert wc_out(page).rstrip().endswith('Source: ' + SHIPPED_WC['sources'][0]['name'])
    wc_clean(page)
