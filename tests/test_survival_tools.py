"""Task 9: Survival tools registry and the SOS light page (#/survival/tool/sos).
Task 10: the Daylight and moon page (#/survival/tool/daylight)."""
import json
from datetime import datetime
from zoneinfo import ZoneInfo

from playwright.sync_api import expect

from .test_survival_topic import wait_hash
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
    assert page.evaluate('FK.survival.tools().map(t => [t.name, t.label])') == [['sos', 'SOS light'], ['daylight', 'Daylight and moon']]
    assert page.locator('#survTools h2').inner_text() == 'Tools'
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
SYR = (43.05, -76.15)
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
    assert 'Last GPS fix' in pos and '12 min ago' in pos and '43.05' in pos and '76.15' in pos
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
    """No trusted March reference yet (see content-review), so this checks the clock change itself: on Sunday 8 March
    the clock jumps an hour, so every time shows about an hour later than on the 7th, and each card shows what
    FK_ASTRO computes for that local day."""
    page = ny_page
    dl_boot(page, app_url, 'America/New_York', (2026, 3, 7, 10, 0), fix=SYR)
    want = page.evaluate("""() => [7, 8, 9].map(d => { const s = FK_ASTRO.sun(new Date(2026, 2, d).getTime(), 43.05, -76.15), out = {};
      for (const k of ['dawn', 'rise', 'set', 'dusk']) { const t = new Date(s[k]); out[k] = t.getHours() * 60 + t.getMinutes(); }
      return out; })""")
    for i in range(3):
        for k in ('dawn', 'rise', 'set', 'dusk'):
            assert minutes(cell(page, i, k)) == want[i][k], f'card {i} {k}'
    for k in ('dawn', 'rise', 'set', 'dusk'):
        jump = minutes(cell(page, 1, k)) - minutes(cell(page, 0, k))
        assert 56 <= jump <= 63, f'{k} moved {jump} min across the clock change'
        assert abs(minutes(cell(page, 2, k)) - minutes(cell(page, 1, k))) <= 3


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


def test_daylight_utqiagvik_december_does_not_rise(ak_page, app_url):
    page = ak_page
    dl_boot(page, app_url, 'America/Anchorage', (2026, 12, 21, 12, 0), fix=UTQ)
    assert cell(page, 0, 'rise') == 'Does not rise'
    assert cell(page, 0, 'len') == '0 h 0 min'


def test_daylight_without_fix_asks_and_accepts_a_typed_position(ny_page, app_url):
    page = ny_page
    dl_boot(page, app_url, 'America/New_York', (2026, 11, 17, 10, 0))
    assert NO_POS in page.inner_text('#survPage')
    expect(page.locator('#survPage .dl-day')).to_have_count(0)
    lat, lon = page.get_by_label('Latitude', exact=True), page.get_by_label('Longitude', exact=True)
    assert lat.bounding_box()['height'] >= 48 and lon.bounding_box()['height'] >= 48
    lat.fill('43.05')
    lon.fill('-76.15')
    use = page.get_by_role('button', name='Use this position')
    assert use.bounding_box()['height'] >= 48
    use.click()
    expect(page.locator('#survPage .dl-day')).to_have_count(7)
    assert 'Typed position' in page.locator('#survPage .dl-pos').inner_text()
    assert json.loads(page.evaluate("localStorage.getItem('fk.daylightPos')")) == {'lat': 43.05, 'lon': -76.15, 'on': True}
    page.reload()
    expect(page.locator('#survPage .dl-day')).to_have_count(7)   # remembered


def test_daylight_refuses_latitude_91_with_an_announced_message(ny_page, app_url):
    page = ny_page
    dl_boot(page, app_url, 'America/New_York', (2026, 11, 17, 10, 0))
    page.get_by_label('Latitude', exact=True).fill('91')
    page.get_by_label('Longitude', exact=True).fill('-76.15')
    page.get_by_role('button', name='Use this position').click()
    alert = page.locator('#survPage [role="alert"]')
    expect(alert).to_have_text('Latitude must be a number from -90 to 90.')
    expect(page.locator('#survPage .dl-day')).to_have_count(0)
    assert page.evaluate("localStorage.getItem('fk.daylightPos')") is None
    page.get_by_label('Longitude', exact=True).fill('181')
    page.get_by_label('Latitude', exact=True).fill('43')
    page.get_by_role('button', name='Use this position').click()
    expect(alert).to_have_text('Longitude must be a number from -180 to 180.')
    page.get_by_label('Latitude', exact=True).fill('abc')
    page.get_by_role('button', name='Use this position').click()
    expect(alert).to_have_text('Latitude must be a number from -90 to 90.')


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
