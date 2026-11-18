"""Task 4: Survival topics drawn from FK_DATA.topics, their addresses, and page providers (registerPage)."""
import json

import pytest
from playwright.sync_api import expect

from .conftest import inject_data

SVG = '<svg viewBox="0 0 10 10" class="fixfig"><circle cx="5" cy="5" r="4"/></svg>'
XSS = '<img src=x onerror="window.__xss=1">'


def topic(tid, title, sections, **extra):
    t = {'id': tid, 'title': title, 'category': 'basics', 'keywords': [], 'summary': '',
         'sections': sections, 'sources': [{'name': 'Fixture source', 'used': 'everything'}], 'reviewed': '2026-11-10'}
    t.update(extra)
    return t


FIX = topic('surv-fix', 'Fixture topic', [
    {'h': 'Words', 'blocks': [{'p': 'Para one.'}, {'list': ['Bullet A', 'Bullet B']}, {'steps': ['Step one', 'Step two']}]},
    {'h': 'Careful', 'blocks': [{'warn': 'Hot surface.'}, {'table': {'head': ['Item', 'Amount'], 'rows': [['Salt', '1 tsp'], ['Water', '1 l']]}}]},
    {'h': 'Picture', 'blocks': [{'fig': 'kit', 'cap': 'Caption of fig.', 'figSvg': SVG, 'figLabel': 'Kit label'}]},
    {'h': 'Elsewhere', 'blocks': [{'link': 'p:bleeding', 'label': 'Bleeding protocol'}, {'link': 's:surv-other', 'label': 'Other topic'}]},
], doFirst=['First thing', 'Second thing', 'Third thing'], asOf='2026-11-01',
    sources=[{'name': 'Source one', 'used': 'numbers'}, {'name': 'Source two', 'used': 'steps'}])
OTHER = topic('surv-other', 'Other topic', [{'h': 'Only', 'blocks': [{'p': 'Other body.'}, {'link': 's:surv-fix', 'label': 'Back to fixture'}]}],
              draft=True)
EVIL = topic('surv-evil', 'Evil ' + XSS, [
    {'h': 'H ' + XSS, 'blocks': [{'p': 'P ' + XSS}, {'list': ['L ' + XSS]}, {'steps': ['S ' + XSS]}, {'warn': 'W ' + XSS},
                                 {'table': {'head': ['T ' + XSS], 'rows': [['C ' + XSS]]}},
                                 {'fig': 'kit', 'cap': 'F ' + XSS, 'figSvg': SVG, 'figLabel': 'A ' + XSS},
                                 {'link': 's:surv-fix', 'label': 'K ' + XSS}]}],
    doFirst=['D ' + XSS], sources=[{'name': 'N ' + XSS, 'used': 'U ' + XSS}], reviewed='R ' + XSS, asOf='O ' + XSS)
WIDE = topic('surv-wide', 'Wide table', [{'h': 'Six columns', 'blocks': [{'table': {
    'head': [f'Column heading number {i}' for i in range(1, 7)],
    'rows': [[f'Cell {r}-{c} with a few words in it' for c in range(1, 7)] for r in range(1, 4)]}}]}])
TOPICS = [FIX, OTHER, EVIL, WIDE]


def boot(page, app_url, hash_='#/survival', topics=TOPICS, storage=None):
    inject_data(page, topics=topics, only=True)
    page.add_init_script('window.__len0 = history.length;')
    if storage:
        page.add_init_script(
            "if (!sessionStorage.getItem('seeded')) { sessionStorage.setItem('seeded', '1');"
            + ''.join(f"localStorage.setItem('fk.{k}', {json.dumps(json.dumps(v))});" for k, v in storage.items()) + '}')
    page.goto(app_url + hash_)


def wait_hash(page, h):
    page.wait_for_function(f"location.hash === {json.dumps(h)}")


def settle(page):
    page.evaluate('new Promise(r => setTimeout(r, 50))')


def text(page):
    return page.inner_text('#survPage')


def test_topic_page_shows_title_do_first_every_block_and_footer_in_order(page, app_url):
    boot(page, app_url, '#/survival/surv-fix')
    expect(page.locator('#survPage')).to_be_visible()
    expect(page.locator('#survHome')).to_be_hidden()
    assert page.inner_text('#survPage h2').strip() == 'Fixture topic'
    assert [li.inner_text() for li in page.locator('#survPage .sv-first li').all()] == ['First thing', 'Second thing', 'Third thing']
    t = text(page)
    order = ['Fixture topic', 'Do first', 'First thing', 'Words', 'Para one.', 'Bullet A', 'Bullet B', 'Step one', 'Step two',
             'Careful', 'Hot surface.', 'Salt', '1 tsp', 'Picture', 'Caption of fig.', 'Elsewhere', 'Bleeding protocol', 'Other topic',
             'Source one', 'numbers', 'Source two', 'steps', 'Reviewed 2026-11-10', 'As of 2026-11-01']
    t = t.replace(page.inner_text('#survPage .sv-jump'), '', 1)   # the jump list repeats the headings
    at = 0
    for s in order:   # each piece appears after the one before it
        found = t.find(s, at)
        assert found >= 0, (s, t[at:])
        at = found + len(s)
    assert page.locator('#survPage ul li', has_text='Bullet A').count() == 1
    assert page.locator('#survPage ol.steps li', has_text='Step two').count() == 1
    assert page.locator('#survPage .sv-warn', has_text='Hot surface.').count() == 1
    assert page.locator('#survPage .tablewrap table th', has_text='Amount').count() == 1
    assert page.locator('#survPage figure.fig button svg.fixfig').count() == 1
    assert page.get_attribute('#survPage figure.fig button', 'aria-label') == 'Enlarge diagram: Kit label'
    assert 'Draft' not in t


def test_jump_list_only_with_four_or_more_sections_and_it_moves_to_the_section(page, app_url):
    boot(page, app_url, '#/survival/surv-fix')
    jumps = page.locator('#survPage .sv-jump button')
    assert [b.inner_text() for b in jumps.all()] == ['Words', 'Careful', 'Picture', 'Elsewhere']
    jumps.nth(3).click()
    assert page.evaluate('document.activeElement.textContent') == 'Elsewhere'
    assert page.evaluate("location.hash") == '#/survival/surv-fix'   # jumping is not navigation
    page.goto(app_url + '#/survival/surv-other')
    expect(page.locator('#survPage h2')).to_have_text('Other topic')
    assert page.locator('#survPage .sv-jump').count() == 0


def test_diagram_enlarges_in_dialog(page, app_url):
    boot(page, app_url, '#/survival/surv-fix')
    page.click('#survPage figure.fig button')
    expect(page.locator('#dlgFig')).to_be_visible()
    assert page.locator('#figBody svg.fixfig').count() == 1
    assert page.inner_text('#figCap') == 'Caption of fig.'
    page.click('#figClose')
    expect(page.locator('#dlgFig')).to_be_hidden()


def test_as_of_only_when_present_and_draft_tag(page, app_url):
    boot(page, app_url, '#/survival/surv-other')
    expect(page.locator('#survPage h2')).to_have_text('Other topic')
    t = text(page)
    assert 'As of' not in t and 'Reviewed 2026-11-10' in t
    assert page.locator('#survPage .sv-draft').inner_text() == 'Draft'


def test_link_to_protocol_opens_it(page, app_url):
    boot(page, app_url, '#/survival/surv-fix')
    page.click('#survPage [data-link="p:bleeding"]')
    wait_hash(page, '#/emergency/bleeding')
    expect(page.locator('#player')).to_be_visible()


def test_link_to_topic_opens_it_and_back_returns_to_first(page, app_url):
    boot(page, app_url, '#/survival/surv-fix')
    n = page.evaluate('history.length')
    page.click('#survPage [data-link="s:surv-other"]')
    wait_hash(page, '#/survival/surv-other')
    expect(page.locator('#survPage h2')).to_have_text('Other topic')
    assert page.evaluate('history.length') == n + 1
    page.go_back()
    wait_hash(page, '#/survival/surv-fix')
    expect(page.locator('#survPage h2')).to_have_text('Fixture topic')


def test_home_lists_topics_back_from_topic_returns_home_and_history_grew_by_one(page, app_url):
    boot(page, app_url, '#/survival')
    expect(page.locator('#survHome')).to_be_visible()
    expect(page.locator('#survPage')).to_be_hidden()
    assert 'Basics' in page.inner_text('#survHome')
    page.click('#survHome summary')   # categories open in place
    n = page.evaluate('history.length')
    page.click('#survHome [data-key="s:surv-fix"]')
    wait_hash(page, '#/survival/surv-fix')
    assert page.evaluate('history.length') == n + 1
    assert page.evaluate('document.activeElement.id') == 'svTitle'   # focus moves to the topic title
    assert page.evaluate('FK.recent.all()[0]') == 's:surv-fix'
    page.go_back()
    wait_hash(page, '#/survival')
    expect(page.locator('#survHome')).to_be_visible()
    expect(page.locator('#survPage')).to_be_hidden()
    page.wait_for_function("document.activeElement && document.activeElement.dataset.key === 's:surv-fix'")   # focus back on the opener


@pytest.mark.parametrize('bad', ['/survival/nope', '/survival/list/nope', '/survival/tool/nope', '/survival/surv-fix/extra', '/survival/list'])
def test_bad_address_on_load_ends_at_home_without_history_entry(page, app_url, bad):
    boot(page, app_url, '#' + bad)
    wait_hash(page, '#/survival')
    settle(page)
    assert page.evaluate('location.hash') == '#/survival'
    expect(page.locator('#survHome')).to_be_visible()
    expect(page.locator('#survPage')).to_be_hidden()
    assert page.evaluate('history.length') == page.evaluate('window.__len0')


@pytest.mark.parametrize('bad', ['#/survival/nope', '#/survival/list/nope', '#/survival/tool/nope'])
def test_bad_address_typed_after_load_is_replaced(page, app_url, bad):
    boot(page, app_url, '#/survival/surv-fix')
    n = page.evaluate('history.length')
    page.evaluate(f'location.hash = {json.dumps(bad)}')   # the edit itself adds one entry; the fix must not add another
    wait_hash(page, '#/survival')
    settle(page)
    assert page.evaluate('location.hash') == '#/survival'
    assert page.evaluate('history.length') == n + 1
    expect(page.locator('#survHome')).to_be_visible()
    page.go_back()
    wait_hash(page, '#/survival/surv-fix')
    expect(page.locator('#survPage h2')).to_have_text('Fixture topic')


def test_markup_in_text_renders_as_text(page, app_url):
    boot(page, app_url, '#/survival/surv-evil')
    expect(page.locator('#survPage')).to_be_visible()
    settle(page)
    assert page.evaluate('window.__xss') is None
    assert page.locator('#survPage img').count() == 0
    t = text(page)
    for p in ['Evil', 'H', 'P', 'L', 'S', 'W', 'T', 'C', 'F', 'K', 'D', 'N', 'U', 'Reviewed R', 'As of O']:
        assert p + ' ' + XSS in t, p
    assert page.get_attribute('#survPage figure.fig button', 'aria-label') == 'Enlarge diagram: A ' + XSS
    page.goto(app_url + '#/survival')
    page.click('#survHome summary')
    assert page.locator('#survHome img').count() == 0 and 'Evil ' + XSS in page.inner_text('#survHome')


def test_six_column_table_does_not_scroll_page_sideways_at_360(page, app_url):
    boot(page, app_url, '#/survival/surv-wide')
    expect(page.locator('#survPage table')).to_be_visible()
    assert page.evaluate('document.documentElement.scrollWidth') <= 360
    assert page.eval_on_selector('#survPage .tablewrap', 'e => e.scrollWidth > e.clientWidth')   # it scrolls inside its own box


def test_pin_star_toggles_pin(page, app_url):
    boot(page, app_url, '#/survival/surv-fix')
    star = page.locator('#survPage [data-act="pin"]')
    assert star.get_attribute('aria-pressed') == 'false'
    star.click()
    assert page.evaluate("FK.pins.has('s:surv-fix')") is True
    assert star.get_attribute('aria-pressed') == 'true'
    star.click()
    assert page.evaluate("FK.pins.has('s:surv-fix')") is False
    assert star.get_attribute('aria-pressed') == 'false'
    box = star.bounding_box()
    assert box['height'] >= 48 and box['width'] >= 48


def test_data_access_skips_malformed_topics(page, app_url):
    boot(page, app_url, topics=TOPICS + [None, 'x', {'id': 'surv-bad', 'title': 'No sections'}, {'id': 7, 'title': 'T', 'sections': []},
                                          {'id': 'surv-empty', 'title': '', 'sections': []}])
    ids = page.evaluate('FK.survival.topics().map(t => t.id)')
    assert ids == ['surv-fix', 'surv-other', 'surv-evil', 'surv-wide']
    assert page.evaluate("FK.survival.topic('surv-bad')") is None
    assert page.evaluate("FK.survival.topic('surv-other').title") == 'Other topic'


def test_open_handles_topic_keys_only(page, app_url):
    boot(page, app_url)
    assert page.evaluate("[FK.survival.open('s:nope'), FK.survival.open('z:surv-fix'), FK.survival.open(7), FK.survival.open('c:x')]") == [False] * 4
    n = page.evaluate('history.length')
    assert page.evaluate("FK.survival.open('s:surv-other', { replace: true })") is True
    wait_hash(page, '#/survival/surv-other')
    assert page.evaluate('history.length') == n


REGISTER = """
  window.__cleaned = 0;
  FK.survival.registerPage('list', (id, el) => {
    if (id !== 'demo') return false;
    el.innerHTML = '<h2 id="demoTitle">Demo list</h2>';
    return () => { window.__cleaned++; };
  });
  FK.survival.registerPage('tool', (id, el) => {
    if (id !== 'lamp') return false;
    el.innerHTML = '<h2 id="lampTitle">Lamp</h2>';
    return true;
  });
"""


def test_register_page_draws_provider_and_calls_cleanup_on_close(page, app_url):
    boot(page, app_url)
    page.evaluate(REGISTER)
    page.evaluate("FK.route.go('/survival/list/demo')")
    expect(page.locator('#survPage #demoTitle')).to_be_visible()
    expect(page.locator('#survHome')).to_be_hidden()
    assert page.evaluate('window.__cleaned') == 0
    page.go_back()
    wait_hash(page, '#/survival')
    expect(page.locator('#survHome')).to_be_visible()
    assert page.evaluate('window.__cleaned') == 1
    assert page.locator('#demoTitle').count() == 0
    # Leaving for another tab closes the page too
    page.evaluate("FK.route.go('/survival/list/demo')")
    expect(page.locator('#demoTitle')).to_be_visible()
    page.click('.tabbar button[data-tab="emergency"]')
    wait_hash(page, '#/emergency')
    assert page.evaluate('window.__cleaned') == 2
    # A provider with no cleanup, and one page replacing another
    page.evaluate("FK.route.go('/survival/list/demo')")
    page.evaluate("FK.route.go('/survival/tool/lamp')")
    expect(page.locator('#survPage #lampTitle')).to_be_visible()
    assert page.locator('#demoTitle').count() == 0
    assert page.evaluate('window.__cleaned') == 3


def test_register_page_unknown_id_goes_home_without_history_entry(page, app_url):
    boot(page, app_url)
    page.evaluate(REGISTER)
    n = page.evaluate('history.length')
    page.evaluate("FK.route.go('/survival/list/other', { replace: true })")
    wait_hash(page, '#/survival')
    settle(page)
    expect(page.locator('#survHome')).to_be_visible()
    assert page.evaluate('history.length') == n
    assert page.evaluate("[FK.survival.registerPage('bogus', () => true), FK.survival.registerPage('list', 'x')]") == [None, None]
