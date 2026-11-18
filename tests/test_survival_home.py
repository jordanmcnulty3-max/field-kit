"""Task 5: Survival home, category lists, filters and homeItems providers."""
import json

import pytest
from playwright.sync_api import expect

from .conftest import inject_data
from .test_survival_topic import boot, settle, wait_hash, topic, XSS

B = lambda tid, title, cat='basics', **kw: topic(tid, title, [{'h': 'S', 'blocks': [{'p': 'x'}]}], category=cat, **kw)
TOPICS = [
    B('surv-zeta', 'Zeta basics'),
    B('surv-alpha', 'Alpha basics'),
    B('surv-priorities', 'Priorities of survival'),
    B('surv-woods', 'Woods only', where=['woods']),
    B('surv-untagged', 'Untagged thing', 'water'),
    B('surv-town', 'Town only', 'water', where=['town']),
    B('surv-coldw', 'Cold woods', 'heat', where=['woods'], when=['cold']),
    B('surv-draft', 'Drafty', 'comms', draft=True),
]
CAT_LABELS = ['Basics', 'Water and sanitation', 'Heat, shelter and winter', 'Comms']


def home(page, app_url, storage=None, topics=TOPICS):
    boot(page, app_url, '#/survival', topics=topics, storage=storage)
    expect(page.locator('#survHome')).to_be_visible()


def cats(page):
    return [s.inner_text() for s in page.locator('#survCats summary').all()]


def open_cat(page, label):
    page.locator('#survCats summary', has_text=label).click()


def titles(page, label):
    d = page.locator('#survCats details', has=page.locator('summary', has_text=label))
    return [b.inner_text().replace('\nDraft', '').strip() for b in d.locator('button.em-btn').all()]


def test_only_categories_with_topics_in_shared_order(page, app_url):
    home(page, app_url)
    assert cats(page) == CAT_LABELS
    assert page.locator('#survCats details[open]').count() == 0


def test_category_opens_in_place_with_priorities_first_then_by_title(page, app_url):
    home(page, app_url)
    n = page.evaluate('history.length')
    open_cat(page, 'Basics')
    assert titles(page, 'Basics') == ['Priorities of survival', 'Alpha basics', 'Woods only', 'Zeta basics']
    expect(page.locator('#survHome')).to_be_visible()
    assert page.evaluate('history.length') == n
    page.click('#survCats [data-key="s:surv-alpha"]')
    wait_hash(page, '#/survival/surv-alpha')


def test_sections_in_order_and_placeholders_present(page, app_url):
    home(page, app_url)
    ids = page.evaluate("[...document.getElementById('survHome').children].map(e => e.id)")
    assert ids == ['survFilters', 'survPinned', 'survRecent', 'survTopics', 'survTools', 'survLists']
    assert page.locator('#survTools').inner_text() == '' and page.locator('#survLists').inner_text() == ''
    assert page.locator('#survPinned').inner_text() == ''


def test_town_hides_woods_only_keeps_untagged_and_survives_reload(page, app_url):
    home(page, app_url)
    for c in ('Basics', 'Water and sanitation'):
        open_cat(page, c)
    page.click('button[data-dim="where"][data-val="town"]')
    assert titles(page, 'Basics') == ['Priorities of survival', 'Alpha basics', 'Zeta basics']
    assert titles(page, 'Water and sanitation') == ['Town only', 'Untagged thing']
    assert page.evaluate("FK.survival.filter()") == {'where': 'town', 'when': 'any'}
    assert page.evaluate("FK.store.get('survFilter')") == {'where': 'town', 'when': 'any'}
    page.reload()
    expect(page.locator('#survHome')).to_be_visible()
    assert page.get_attribute('button[data-dim="where"][data-val="town"]', 'aria-pressed') == 'true'
    open_cat(page, 'Basics')
    assert 'Woods only' not in titles(page, 'Basics')


def test_when_and_where_combine(page, app_url):
    home(page, app_url)
    page.click('button[data-dim="when"][data-val="warm"]')
    open_cat(page, 'Heat')
    assert page.locator('#survCats details', has=page.locator('summary', has_text='Heat')).inner_text().count('Cold woods') == 0
    page.click('button[data-dim="when"][data-val="cold"]')
    assert titles(page, 'Heat') == ['Cold woods']


def test_category_with_everything_filtered_out_says_so(page, app_url):
    home(page, app_url)
    page.click('button[data-dim="where"][data-val="coast"]')
    open_cat(page, 'Heat')
    d = page.locator('#survCats details[data-cat="heat"]')
    assert 'No topics for this filter' in d.inner_text()
    assert d.locator('button').count() == 0
    assert cats(page) == CAT_LABELS   # still listed


@pytest.mark.parametrize('stored', [{'where': 'moon', 'when': 7}, 'x', 7, None, [], {'where': 'town'}])
def test_bad_stored_filter_behaves_as_any(page, app_url, stored):
    home(page, app_url, storage={'survFilter': stored})
    f = page.evaluate('FK.survival.filter()')
    assert f == {'where': 'town' if stored == {'where': 'town'} else 'any', 'when': 'any'}
    open_cat(page, 'Basics')
    pressed = [b.get_attribute('data-val') for b in page.locator('#survFilters button[aria-pressed="true"]').all()]
    assert pressed == ([f['where'], 'any'])


def test_filter_buttons_are_toggles_at_least_48px_with_labels(page, app_url):
    home(page, app_url)
    btns = page.locator('#survFilters button')
    assert [b.inner_text() for b in btns.all()] == ['Any', 'Town', 'Rural', 'Woods', 'Coast', 'Any', 'Cold', 'Warm']
    for b in btns.all():
        assert b.get_attribute('aria-pressed') in ('true', 'false')
        assert b.bounding_box()['height'] >= 48
    assert page.locator('#survFilters [role="group"]').evaluate_all('g => g.map(e => e.getAttribute("aria-label"))') == ['Where', 'When']
    assert page.get_attribute('button[data-dim="where"][data-val="any"]', 'aria-pressed') == 'true'
    page.click('button[data-dim="where"][data-val="rural"]')
    assert page.get_attribute('button[data-dim="where"][data-val="rural"]', 'aria-pressed') == 'true'
    assert page.get_attribute('button[data-dim="where"][data-val="any"]', 'aria-pressed') == 'false'
    assert page.locator('#survCats summary').first.bounding_box()['height'] >= 48


def test_filter_change_keeps_focus_and_opened_categories(page, app_url):
    home(page, app_url)
    open_cat(page, 'Basics')
    open_cat(page, 'Comms')
    page.focus('button[data-dim="where"][data-val="woods"]')
    page.keyboard.press('Enter')
    assert page.evaluate("document.activeElement.dataset.val + document.activeElement.dataset.dim") == 'woodswhere'
    assert page.locator('#survCats details[open]').count() == 2
    assert 'Woods only' in titles(page, 'Basics')
    page.click('button[data-dim="when"][data-val="cold"]')
    assert page.locator('#survCats details[open]').count() == 2
    assert page.evaluate("document.activeElement.dataset.dim") == 'when'


def test_markup_in_titles_and_badges_is_text(page, app_url):
    evil = B('surv-evil', 'Evil ' + XSS)
    home(page, app_url, topics=[evil])
    page.evaluate("""FK.survival.homeItems('tool', () => [{ key: 'u:lamp', title: 'Lamp """ + XSS.replace("'", "\\'") + """', badge: '1/2 """ + XSS.replace("'", "\\'") + """' }])""")
    page.evaluate('FK.survival.refreshHome()')
    open_cat(page, 'Basics')
    settle(page)
    assert page.evaluate('window.__xss') is None
    assert page.locator('#survHome img').count() == 0
    assert 'Evil ' + XSS in page.inner_text('#survHome') and '1/2 ' + XSS in page.inner_text('#survTools')


PROVIDERS = """
  window.__tools = [{ key: 'u:lamp', title: 'Lamp', badge: '4/10' }, { key: 'u:bad key', title: 'Skipped' }, { key: 'u:x', title: '' }, null];
  window.__lists = [];
  FK.survival.homeItems('tool', () => window.__tools);
  FK.survival.homeItems('list', () => window.__lists);
  FK.survival.homeItems('tool', () => { throw new Error('boom'); });
  FK.survival.homeItems('nope', () => []);
  FK.survival.homeItems('tool', 'x');
"""


def test_home_items_sections_appear_with_badge_and_hide_when_empty(page, app_url):
    home(page, app_url)
    page.evaluate(PROVIDERS)
    expect(page.locator('#survTools')).to_have_text('')   # nothing until a redraw is asked for
    page.evaluate('FK.survival.refreshHome()')
    assert page.locator('#survTools h2').inner_text() == 'Tools'
    btns = page.locator('#survTools button')
    assert btns.count() == 1
    assert btns.first.get_attribute('data-key') == 'u:lamp'
    assert btns.first.inner_text().replace('\n', ' ') == 'Lamp 4/10'
    assert page.locator('#survLists').inner_text() == ''   # no items: no heading either
    page.evaluate("window.__lists = [{ key: 'c:ten', title: 'Ten essentials' }]; window.__tools = []; FK.survival.refreshHome()")
    assert page.locator('#survTools').inner_text() == ''
    assert page.locator('#survLists h2').inner_text() == 'Checklists'
    assert page.locator('#survLists button').inner_text() == 'Ten essentials'


def test_home_item_button_calls_open(page, app_url):
    home(page, app_url)
    page.evaluate(PROVIDERS + "; window.__opened = []; FK.survival.open = k => { window.__opened.push(k); return true; }; FK.survival.refreshHome();")
    page.click('#survTools [data-key="u:lamp"]')
    assert page.evaluate('window.__opened') == ['u:lamp']


def test_refresh_does_not_redraw_unchanged_blocks(page, app_url):
    home(page, app_url)
    page.evaluate(PROVIDERS + "; FK.survival.refreshHome();")
    page.focus('#survTools button')
    page.evaluate('FK.survival.refreshHome()')
    assert page.evaluate("document.activeElement.dataset.key") == 'u:lamp'


def test_throwing_page_provider_goes_home_without_history_entry(page, app_url):
    boot(page, app_url, topics=TOPICS)
    page.evaluate("FK.survival.registerPage('list', () => { throw new Error('boom'); })")
    warns = []
    page.on('console', lambda m: warns.append(m.type) if m.type == 'warning' else None)
    n = page.evaluate('history.length')
    page.evaluate("FK.route.go('/survival/list/anything', { replace: true })")
    wait_hash(page, '#/survival')
    settle(page)
    expect(page.locator('#survHome')).to_be_visible()
    expect(page.locator('#survPage')).to_be_hidden()
    assert page.inner_html('#survPage') == ''
    assert page.evaluate('history.length') == n
    assert warns == ['warning']
