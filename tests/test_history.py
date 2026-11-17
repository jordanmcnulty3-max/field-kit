"""Leaving a protocol or a tool lands where the user came from, whatever happened to history in between.

Regression tests for the final review's Important 1: a duplicated history entry (Settings from search),
a search result equal to the screen underneath, and a reload inside a protocol or tool."""
import json

from playwright.sync_api import expect

from .conftest import inject_protocols
from .test_player import FIXTURES


def boot(page, app_url, hash_='#/emergency'):
    """An entry from outside the app first, so an overshoot would leave Field Kit."""
    inject_protocols(page, FIXTURES)
    page.add_init_script(
        "if (location.protocol.startsWith('http') && !sessionStorage.getItem('seeded')) { sessionStorage.setItem('seeded', '1'); localStorage.setItem('fk.advAck', 'true'); }")
    page.goto('about:blank')
    page.goto(app_url + hash_)
    page.wait_for_function('window.FK && FK.protocol && FK.search')


def wait_hash(page, h):
    page.wait_for_function(f"location.hash === {json.dumps(h)}")


def action(page):
    return page.locator('#player .pp-action').inner_text()


def resume_step(page):
    a = page.evaluate("JSON.parse(localStorage.getItem('fk.proto.active'))")
    return a and a['step']


def open_branchy_at_q(page):
    page.evaluate("FK.protocol.open('branchy')")
    page.click('#player [data-act="next"]')
    expect(page.locator('#player .pp-action')).to_have_text('Is it yes?')
    assert resume_step(page) == 'q'


def settings_from_search(page):
    page.evaluate("FK.route.go('/search')")
    page.wait_for_selector('#searchPane', state='visible')
    page.fill('#searchInput', 'backup')
    page.click('#searchBody .sr-item[data-key="a:settings"]')
    expect(page.locator('#dlgMenu')).to_be_visible()
    expect(page.locator('#searchPane')).to_be_hidden()
    page.click('#menuClose')
    expect(page.locator('#dlgMenu')).to_be_hidden()


def assert_left_to_home(page, app_url):
    wait_hash(page, '#/emergency')
    expect(page.locator('#player')).to_be_hidden()
    assert page.url.startswith(app_url)
    assert page.locator('#tab-emergency').is_visible()


# ---------- (a) Settings from search while a protocol is open ----------

def test_settings_from_search_then_header_back_leaves_in_one_tap(page, app_url):
    boot(page, app_url)
    open_branchy_at_q(page)
    settings_from_search(page)
    expect(page.locator('#player .pp-action')).to_have_text('Is it yes?')
    page.click('#player [data-act="home"]')
    assert_left_to_home(page, app_url)
    assert resume_step(page) == 'q'   # not overwritten by landing on an earlier step
    page.go_back()   # and Android Back from home does not go into the protocol
    page.wait_for_function("!location.hash.includes('branchy')")
    expect(page.locator('#player')).to_be_hidden()


def test_settings_from_search_leaves_history_as_it_was(page, app_url):
    boot(page, app_url)
    open_branchy_at_q(page)
    n = page.evaluate('FK.route.index()')
    settings_from_search(page)
    assert page.evaluate('FK.route.index()') == n   # back on the entry the search was opened from, not a copy of it
    assert page.evaluate("location.hash") == '#/emergency/branchy/q'
    page.go_back()   # Android Back steps back one step, as before search
    expect(page.locator('#player .pp-action')).to_have_text('Step A action')


def test_settings_from_search_then_footer_back_works_on_first_tap(page, app_url):
    boot(page, app_url)
    open_branchy_at_q(page)
    settings_from_search(page)
    page.click('#player [data-act="back"]')
    expect(page.locator('#player .pp-action')).to_have_text('Step A action')
    wait_hash(page, '#/emergency/branchy')


def test_settings_from_search_on_home_opens_settings_and_keeps_home(page, app_url):
    boot(page, app_url)
    settings_from_search(page)
    assert page.evaluate("location.hash") == '#/emergency'
    assert page.locator('#emHome').is_visible()


# ---------- (b) A search result equal to the screen underneath ----------

def test_search_result_same_protocol_then_android_back_then_header_back(page, app_url):
    boot(page, app_url)
    page.evaluate("FK.protocol.open('branchy')")
    expect(page.locator('#player .pp-action')).to_have_text('Step A action')
    page.click('#player [data-act="search"]')
    page.wait_for_selector('#searchPane', state='visible')
    page.fill('#searchInput', 'Branch test')
    page.click('#searchBody .sr-item[data-key="p:branchy"]')
    expect(page.locator('#searchPane')).to_be_hidden()
    wait_hash(page, '#/emergency/branchy')
    page.go_back()   # Android Back: the same step again, from an older entry
    wait_hash(page, '#/emergency/branchy')
    page.wait_for_timeout(100)
    expect(page.locator('#player')).to_be_visible()
    page.click('#player [data-act="home"]')
    assert_left_to_home(page, app_url)
    # the header back button is not dead afterwards
    page.evaluate("FK.protocol.open('branchy')")
    expect(page.locator('#player')).to_be_visible()
    page.click('#player [data-act="home"]')
    assert_left_to_home(page, app_url)


def test_search_result_same_protocol_then_first_step_back_leaves(page, app_url):
    boot(page, app_url)
    page.evaluate("FK.protocol.open('branchy')")
    page.click('#player [data-act="search"]')
    page.wait_for_selector('#searchPane', state='visible')
    page.fill('#searchInput', 'Branch test')
    page.click('#searchBody .sr-item[data-key="p:branchy"]')
    page.go_back()
    wait_hash(page, '#/emergency/branchy')
    page.wait_for_timeout(100)
    page.click('#player [data-act="back"]')
    assert_left_to_home(page, app_url)


# ---------- (c) Reload inside a protocol ----------

def test_reload_inside_protocol_then_header_back_then_android_back(page, app_url):
    boot(page, app_url)
    open_branchy_at_q(page)
    page.reload()
    page.wait_for_function('window.FK && FK.protocol')
    expect(page.locator('#player .pp-action')).to_have_text('Is it yes?')
    page.click('#player [data-act="home"]')
    assert_left_to_home(page, app_url)
    assert resume_step(page) == 'q'
    page.go_back()   # the entry before home is outside the app here: Field Kit is left, never re-entered at a step
    page.wait_for_timeout(150)
    assert 'branchy' not in page.url


def test_reload_inside_protocol_android_back_still_steps_back(page, app_url):
    boot(page, app_url)
    open_branchy_at_q(page)
    page.reload()
    page.wait_for_function('window.FK && FK.protocol')
    page.go_back()
    expect(page.locator('#player .pp-action')).to_have_text('Step A action')
    page.go_back()
    expect(page.locator('#player')).to_be_hidden()
    wait_hash(page, '#/emergency')


def test_leave_falls_back_home_when_history_does_not_move(page, app_url):
    boot(page, app_url)
    open_branchy_at_q(page)
    page.evaluate("history.go = () => {}; 0")   # an out-of-range jump does nothing in an installed app
    page.click('#player [data-act="home"]')
    page.wait_for_timeout(700)
    assert_left_to_home(page, app_url)


# ---------- (d) Settings from search over a tool, and a reload inside a tool ----------

def test_settings_from_search_over_a_tool_then_close_works_first_press(page, app_url):
    boot(page, app_url)
    page.evaluate("FK.tools.start('tq')")
    wait_hash(page, '#/emergency/tool/tq')
    settings_from_search(page)
    expect(page.locator('#toolPane')).to_be_visible()
    page.click('#toolClose')
    wait_hash(page, '#/emergency')
    expect(page.locator('#toolPane')).to_be_hidden()
    assert page.url.startswith(app_url)


def test_reload_inside_a_tool_then_close_then_android_back(page, app_url):
    boot(page, app_url)
    page.evaluate("FK.protocol.open('branchy')")
    page.evaluate("FK.tools.start('rate')")
    wait_hash(page, '#/emergency/tool/rate')
    page.reload()
    page.wait_for_function('window.FK && FK.tools && FK.tools.cpr')
    expect(page.locator('#toolPane')).to_be_visible()
    page.click('#toolClose')   # back to the protocol step it was opened from
    wait_hash(page, '#/emergency/branchy')
    expect(page.locator('#player .pp-action')).to_have_text('Step A action')
    page.go_back()
    wait_hash(page, '#/emergency')
    expect(page.locator('#player')).to_be_hidden()


def test_tool_close_falls_back_home_when_history_does_not_move(page, app_url):
    boot(page, app_url)
    page.evaluate("FK.tools.start('rate')")
    wait_hash(page, '#/emergency/tool/rate')
    page.evaluate("history.go = () => {}; 0")
    page.click('#toolClose')
    page.wait_for_timeout(700)
    wait_hash(page, '#/emergency')
    expect(page.locator('#toolPane')).to_be_hidden()
    page.evaluate("FK.tools.start('rate')")   # and the overlay still opens and closes afterwards
    wait_hash(page, '#/emergency/tool/rate')
