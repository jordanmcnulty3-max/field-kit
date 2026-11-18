"""Task 9: Survival tools registry and the SOS light page (#/survival/tool/sos)."""
from playwright.sync_api import expect

from .test_survival_topic import wait_hash
from .test_tools import T0, boot as tools_boot

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
    assert page.evaluate('FK.survival.tools().map(t => [t.name, t.label])') == [['sos', 'SOS light']]
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
