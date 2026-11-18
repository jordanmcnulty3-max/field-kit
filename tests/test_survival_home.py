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
    page.evaluate('FK.survival.tools = () => []; FK.survival.refreshHome()')   # the shipped SOS tool would add a Tools section; these tests are about the providers they add


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


# ---------- Task 6: keys, pins and recents across both homes ----------

from .conftest import inject_data
from .test_home import FIXTURES as PROTOS

KEY_TOPICS = [B(f'surv-t{i}', f'Topic {i}') for i in range(1, 7)]
OPEN_ORDER = ['p:burns', 's:surv-t1', 'p:splint', 's:surv-t2', 'p:frostbite', 's:surv-t3',
              'p:snakebite', 's:surv-t4', 'p:fever', 's:surv-t5', 'p:iv', 's:surv-t6']


def boot_both(page, app_url, storage=None, hash_='#/survival'):
    inject_data(page, protocols=PROTOS, topics=KEY_TOPICS, only=True)
    seed = {'advAck': True, **(storage or {})}
    page.add_init_script(
        "if (!sessionStorage.getItem('seeded')) { sessionStorage.setItem('seeded', '1');"
        + ''.join(f"localStorage.setItem('fk.{k}', {json.dumps(json.dumps(v))});" for k, v in seed.items()) + '}')
    page.goto(app_url + hash_)


def shown(page, block):
    return page.evaluate("""id => [...document.querySelectorAll('#' + id + ' button[data-open], #' + id + ' button[data-key]')]
        .map(b => b.dataset.key || 'p:' + b.dataset.open)""", block)


def open_key(page, key):
    if key[0] == 'p':
        page.evaluate(f"FK.protocol.open('{key[2:]}')")
        wait_hash(page, '#/emergency/' + key[2:])
    else:
        page.evaluate(f"FK.survival.open('{key}')")
        wait_hash(page, '#/survival/' + key[2:])


def test_twelve_opens_store_twelve_and_each_home_shows_its_newest_five(page, app_url):
    boot_both(page, app_url)
    for k in OPEN_ORDER:
        open_key(page, k)
    newest = OPEN_ORDER[::-1]
    assert json.loads(page.evaluate("localStorage.getItem('fk.recent')")) == newest
    assert page.evaluate('FK.recent.all()') == newest
    assert page.evaluate("FK.recent.forSection('emergency')") == newest[:5]
    assert page.evaluate("FK.recent.forSection('survival')") == [k for k in newest if k[0] == 's'][:5]
    page.evaluate("FK.route.go('/emergency')")
    wait_hash(page, '#/emergency')
    assert shown(page, 'emRecent') == newest[:5]
    page.evaluate("FK.route.go('/survival')")
    wait_hash(page, '#/survival')
    assert shown(page, 'survRecent') == ['s:surv-t6', 's:surv-t5', 's:surv-t4', 's:surv-t3', 's:surv-t2']
    assert page.locator('#survRecent h2').inner_text() == 'Recent'


def test_recent_keeps_at_most_twenty(page, app_url):
    boot_both(page, app_url)
    page.evaluate("for (let i = 0; i < 25; i++) FK.recent.add('p:x' + i)")
    got = page.evaluate('FK.recent.all()')
    assert len(got) == 20 and got[0] == 'p:x24'
    assert len(json.loads(page.evaluate("localStorage.getItem('fk.recent')"))) == 20


def test_clear_on_survival_home_empties_storage_and_both_homes_and_moves_focus(page, app_url):
    boot_both(page, app_url, storage={'recent': ['s:surv-t1', 'p:burns', 's:surv-t2'], 'pins': ['s:surv-t3']})
    assert shown(page, 'survRecent') == ['s:surv-t1', 's:surv-t2']
    page.click('#survRecent [data-act="clear-recent"]')
    assert page.locator('#survRecent').inner_html() == ''
    assert json.loads(page.evaluate("localStorage.getItem('fk.recent')")) == []
    assert page.evaluate('FK.pins.all()') == ['s:surv-t3']
    assert page.evaluate("document.activeElement === document.querySelector('#survFilters button')")
    page.evaluate("FK.route.go('/emergency')")
    wait_hash(page, '#/emergency')
    assert page.locator('#emRecent').inner_html() == ''
    assert page.locator('#survPinned [data-act="clear-recent"]').count() == 0


def test_pinned_topic_on_both_homes_pinned_protocol_only_on_emergency(page, app_url):
    boot_both(page, app_url, storage={'pins': ['s:surv-t3', 'p:burns', 'p:shock']})
    assert shown(page, 'survPinned') == ['s:surv-t3']
    assert page.locator('#survPinned h2').inner_text() == '★ Pinned'
    assert page.evaluate("FK.pins.forSection('survival')") == ['s:surv-t3']
    page.evaluate("FK.route.go('/emergency')")
    wait_hash(page, '#/emergency')
    assert shown(page, "emPinned") == ["s:surv-t3", "p:burns", "p:shock"]
    page.evaluate("FK.route.go('/survival')")
    wait_hash(page, '#/survival')
    page.click('#survPinned [data-key="s:surv-t3"]')
    wait_hash(page, '#/survival/surv-t3')


def test_pinning_a_topic_updates_the_survival_home_live(page, app_url):
    boot_both(page, app_url)
    assert page.locator('#survPinned').inner_html() == ''
    page.evaluate("FK.pins.toggle('s:surv-t2')")
    assert shown(page, 'survPinned') == ['s:surv-t2']


JUNK = ['s:surv-gone', 'c:nope', 'u:nope', 'z:what', 'p:bleeding']


def test_unknown_stored_keys_are_skipped_on_both_homes_without_errors(page, app_url):
    boot_both(page, app_url, storage={'pins': JUNK, 'recent': JUNK})
    assert page.locator('#survPinned').inner_html() == '' and page.locator('#survRecent').inner_html() == ''
    assert page.evaluate("FK.pins.all()") == [k for k in JUNK if k != 'z:what']
    page.evaluate("FK.route.go('/emergency')")
    wait_hash(page, '#/emergency')
    assert shown(page, 'emPinned') == ['p:bleeding'] and shown(page, 'emRecent') == ['p:bleeding']
    settle(page)   # any console error fails the test at teardown


def test_open_category_keeps_focus_when_recent_changes(page, app_url):
    boot_both(page, app_url)
    page.focus('#survCats summary')
    page.keyboard.press('Enter')
    assert page.locator('#survCats details[open]').count() == 1
    page.evaluate("document.querySelector('#survCats summary').dataset.mark = 'same'")
    page.evaluate("FK.recent.add('s:surv-t1'); FK.survival.refreshHome()")   # a full redraw of the home
    assert shown(page, 'survRecent') == ['s:surv-t1']
    assert page.evaluate("document.activeElement === document.querySelector('#survCats summary')")
    assert page.evaluate("document.activeElement.dataset.mark") == 'same'
    assert page.locator('#survCats details[open]').count() == 1
