"""Task 5: Survival home, category lists, filters and homeItems providers."""
import glob
import json
import os
import re
import subprocess

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
    page.locator('#survCats summary', has_text=label).first.click()   # first: 'Food' comes before 'Food from the land'


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
    assert page.locator('#survTools h2').text_content() == 'Tools'
    btns = page.locator('#survTools button')
    assert btns.count() == 1
    assert btns.first.get_attribute('data-key') == 'u:lamp'
    assert btns.first.inner_text().replace('\n', ' ') == 'Lamp 4/10'
    assert page.locator('#survLists').inner_text() == ''   # no items: no heading either
    page.evaluate("window.__lists = [{ key: 'c:ten', title: 'Ten essentials' }]; window.__tools = []; FK.survival.refreshHome()")
    assert page.locator('#survTools').inner_text() == ''
    assert page.locator('#survLists h2').text_content() == 'Checklists'
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

KEY_TOPICS = [B(f'surv-t{i}', f'Topic {i}', **({'where': ['woods']} if i == 1 else {})) for i in range(1, 7)]   # one tag, so the Where row is shown
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
    assert page.locator('#survRecent h2').text_content() == 'Recent'


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
    assert page.locator('#survPinned h2').text_content() == '★ Pinned'
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


# ---------- Final fix wave ----------

def shipped_home(page, app_url, storage=None):
    """The Survival home with the shipped topics and checklists (no fixtures)."""
    seed = {'advAck': True, **(storage or {})}
    page.add_init_script(
        "if (!sessionStorage.getItem('seeded')) { sessionStorage.setItem('seeded', '1');"
        + ''.join(f"localStorage.setItem('fk.{k}', {json.dumps(json.dumps(v))});" for k, v in seed.items()) + '}')
    page.goto(app_url + '#/survival')
    expect(page.locator('#survHome')).to_be_visible()


def listed(page):
    return page.evaluate("[...document.querySelectorAll('#survCats button[data-key]')].map(b => b.dataset.key)")


ALWAYS = ['s:surv-dangerous-animals', 's:surv-priorities', 's:surv-make-water-safe', 's:surv-find-water',
          's:surv-wells-without-power',   # untagged by ruling (Task 5 fix round 1): well shock, pit and CO warnings
          's:surv-toilet-no-water', 's:surv-handwashing', 's:surv-water-how-much',   # water pack: protected, no tag may hide them
          's:surv-clean-and-disinfect', 's:surv-stomach-illness-in-a-group', 's:surv-water-in-the-house',   # sanitation safety topics
          # heat pack (Task 10): the hub and every fuel-burning topic; winter storms (downed lines, stranded car) and
          # sleep warm (heater and engine sleep rules) by ruling of the Task 9 review (I4)
          's:surv-heat-out', 's:surv-carbon-monoxide', 's:surv-wood-stoves-fireplaces', 's:surv-portable-heaters',
          's:surv-generators', 's:surv-store-fuel', 's:surv-winter-storms', 's:surv-sleep-warm',
          # radiation pack (Task 8): all ten topics, so no Where or When filter can hide fallout guidance (spec 4)
          's:surv-fallout-warning', 's:surv-fallout-where-to-shelter', 's:surv-fallout-how-long', 's:surv-fallout-shelter-living',
          's:surv-fallout-coming-inside', 's:surv-fallout-water-and-food', 's:surv-fallout-leaving', 's:surv-dirty-bomb',
          's:surv-potassium-iodide', 's:surv-fallout-get-ready',
          # food pack (Task 8): all ten topics, so no Where or When filter can hide food safety (spec 4)
          's:surv-food-power-out', 's:surv-food-still-good', 's:surv-food-cooking-no-power', 's:surv-food-poisoning', 's:surv-food-how-much',
          's:surv-food-storage', 's:surv-food-when-short', 's:surv-food-clean-kitchen', 's:surv-food-babies-children', 's:surv-food-preserving',
          # land pack (v7.7): every topic of Food from the land carries no tag (the three older ones lost theirs), so no filter can hide them
          's:surv-traps-and-fishing', 's:surv-field-dressing-game', 's:surv-food-and-wild-plants',
          's:surv-land-start', 's:surv-land-big-game', 's:surv-land-small-game', 's:surv-land-trapping', 's:surv-land-butchering',
          's:surv-land-fish-cleaning', 's:surv-land-keeping-meat', 's:surv-land-ny-rules', 's:surv-land-after-fallout']
RADIATION = ['s:surv-fallout-warning', 's:surv-fallout-where-to-shelter', 's:surv-fallout-how-long', 's:surv-fallout-shelter-living',
             's:surv-fallout-coming-inside', 's:surv-fallout-water-and-food', 's:surv-fallout-leaving', 's:surv-dirty-bomb',
             's:surv-potassium-iodide', 's:surv-fallout-get-ready']   # named, so a later pack appending to ALWAYS cannot shift it
FOOD = ['s:surv-food-power-out', 's:surv-food-still-good', 's:surv-food-cooking-no-power', 's:surv-food-poisoning', 's:surv-food-how-much',
        's:surv-food-storage', 's:surv-food-when-short', 's:surv-food-clean-kitchen', 's:surv-food-babies-children', 's:surv-food-preserving']
MOVED = ['s:surv-traps-and-fishing', 's:surv-field-dressing-game', 's:surv-food-and-wild-plants']
LAND = ['s:surv-land-start', 's:surv-traps-and-fishing', 's:surv-land-fish-cleaning', 's:surv-land-trapping', 's:surv-land-big-game',
        's:surv-land-small-game', 's:surv-field-dressing-game', 's:surv-land-butchering', 's:surv-land-keeping-meat',
        's:surv-food-and-wild-plants', 's:surv-land-ny-rules', 's:surv-land-after-fallout']   # the hub first, then as the hub lists them
assert set(RADIATION) <= set(ALWAYS) and set(FOOD) <= set(ALWAYS) and set(MOVED) <= set(LAND) <= set(ALWAYS)
# Topics tagged when: cold: listed under Any and Cold, hidden under Warm, for every Where value.
WHEN_COLD = ['s:surv-unheated-house', 's:surv-dress-for-cold', 's:surv-wind-chill', 's:surv-water-winter']
WHERES = ('any', 'town', 'rural', 'woods', 'coast')


def test_f1_safety_topics_are_never_filtered_out_of_the_shipped_home(page, app_url):
    shipped_home(page, app_url)
    for where in WHERES:
        for when in ('any', 'cold', 'warm'):
            page.evaluate(f"FK.store.set('survFilter', {{ where: '{where}', when: '{when}' }}); FK.survival.refreshHome()")
            keys = listed(page)
            for k in ALWAYS:
                assert k in keys, f'{k} hidden by where={where} when={when}'
            for k in WHEN_COLD:
                assert (k in keys) == (when != 'warm'), f'{k} wrong for where={where} when={when}'
            if where == 'coast':
                assert 's:surv-shelter' in keys and 's:surv-river-crossings' in keys, f'Coast hides shelter or river crossings (when={when})'


def test_heat_pack_when_cold_tags_are_exactly_the_four_cold_only_topics():
    """Shipped data: no other topic carries a when tag, so nothing else can be hidden under Warm (Task 9 review I4)."""
    import glob, os
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    tagged = set()
    for p in glob.glob(os.path.join(root, 'src', 'survival', '*.json')):
        t = json.load(open(p, encoding='utf-8'))
        if t.get('when'):
            assert t['when'] == ['cold'], t['id']
            tagged.add('s:' + t['id'])
    assert tagged == set(WHEN_COLD)


HEAT = 'Heat, shelter and winter'


def test_fire_and_shelter_are_listed_under_heat_with_the_hub_first(page, app_url):
    shipped_home(page, app_url)
    open_cat(page, HEAT)
    heat = page.evaluate("[...document.querySelectorAll('#survCats details[data-cat=\"heat\"] button[data-key]')].map(b => b.dataset.key)")
    basics = page.evaluate("[...document.querySelectorAll('#survCats details[data-cat=\"basics\"] button[data-key]')].map(b => b.dataset.key)")
    assert 's:surv-fire' in heat and 's:surv-shelter' in heat
    assert 's:surv-fire' not in basics and 's:surv-shelter' not in basics
    assert basics[0] == 's:surv-priorities' and len(basics) == 8   # Basics keeps its eight remaining topics (the three land topics moved out of it in v7.7)
    assert len(heat) == 14
    assert heat[0] == 's:surv-heat-out'   # the hub leads its category, as Priorities leads Basics
    page.click('#survCats [data-key="s:surv-fire"]')
    wait_hash(page, '#/survival/surv-fire')


def test_heat_category_header_and_its_fourteen_rows_fit_360px(page, app_url):
    shipped_home(page, app_url)
    open_cat(page, HEAT)
    for night in (False, True):
        if night:
            page.click('#nightBtn')
            assert page.evaluate('document.documentElement.dataset.theme') == 'night'
        d = page.locator('#survCats details[data-cat="heat"]')
        boxes = [d.locator('summary').bounding_box()] + [b.bounding_box() for b in d.locator('button[data-key]').all()]
        assert len(boxes) == 15
        for b in boxes:
            assert b['x'] >= 0 and b['x'] + b['width'] <= 360, b
        assert page.evaluate('document.documentElement.scrollWidth') <= 360
        # each title's text stays inside its row (no clipped or spilled title)
        spill = page.evaluate("""[...document.querySelectorAll('#survCats details[data-cat="heat"] button[data-key]')].filter(b => {
            const r = b.getBoundingClientRect(), s = b.querySelector('span').getBoundingClientRect();
            return s.left < r.left || s.right > r.right || b.scrollWidth > b.clientWidth + 1; }).map(b => b.textContent)""")
        assert spill == []


def test_f2_when_row_shows_only_when_a_topic_has_a_when_tag(page, app_url):
    home(page, app_url)   # the fixtures include a topic tagged when: cold
    assert page.locator('#survFilters [role="group"]').evaluate_all('g => g.map(e => e.getAttribute("aria-label"))') == ['Where', 'When']


def test_f2_when_row_hidden_when_no_fixture_has_a_when_tag(page, app_url):
    no_when = [t for t in TOPICS if 'when' not in t]
    home(page, app_url, topics=no_when, storage={'survFilter': {'where': 'any', 'when': 'warm'}})
    assert page.locator('#survFilters [role="group"]').evaluate_all('g => g.map(e => e.getAttribute("aria-label"))') == ['Where']
    assert page.locator('#survFilters button[data-dim="when"]').count() == 0
    assert page.evaluate('FK.survival.filter()') == {'where': 'any', 'when': 'any'}   # a stored When value counts as Any while the row is hidden
    open_cat(page, 'Basics')
    assert len(titles(page, 'Basics')) == 4


def test_f2_shipped_data_shows_the_when_row(page, app_url):
    shipped_home(page, app_url)   # surv-water-winter (water pack) is the first shipped topic with a when tag
    assert page.locator('#survFilters [role="group"]').evaluate_all('g => g.map(e => e.getAttribute("aria-label"))') == ['Where', 'When']


def test_f5_survival_recent_clear_is_at_least_48px(page, app_url):
    boot_both(page, app_url, storage={'recent': ['s:surv-t1']})
    b = page.locator('#survRecent [data-act="clear-recent"]').bounding_box()
    assert b['height'] >= 48 and b['width'] >= 48


def test_f6_focus_returns_to_the_topic_button_after_a_detour_through_emergency(page, app_url):
    from .test_survival_topic import TOPICS as PAGE_TOPICS
    boot(page, app_url, topics=PAGE_TOPICS)
    expect(page.locator('#survHome')).to_be_visible()
    open_cat(page, 'Basics')
    page.click('#survCats [data-key="s:surv-fix"]')
    wait_hash(page, '#/survival/surv-fix')
    page.click('#survPage [data-link="p:bleeding"]')
    page.wait_for_function("location.hash.startsWith('#/emergency/bleeding')")
    page.go_back()
    wait_hash(page, '#/survival/surv-fix')
    page.go_back()
    wait_hash(page, '#/survival')
    page.wait_for_function("document.activeElement && document.activeElement.dataset.key === 's:surv-fix'")
    assert page.evaluate("document.activeElement.closest('#survCats') !== null")


def test_f11_dead_recent_keys_do_not_shrink_either_home(page, app_url):
    live = [f's:surv-t{i}' for i in range(1, 7)]
    boot_both(page, app_url, storage={'recent': ['s:surv-gone', 'c:nope', 'u:nope'] + live})
    assert shown(page, 'survRecent') == live[:5]
    page.evaluate("FK.route.go('/emergency')")
    wait_hash(page, '#/emergency')
    assert shown(page, 'emRecent') == live[:5]


def test_f12_survival_uses_the_shared_key_pattern(page, app_url):
    import os
    src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src', 'survival.js'), encoding='utf-8').read()
    assert '[scu]' not in src and 'FK.keyPattern' in src
    home(page, app_url)
    assert page.evaluate("FK.survival.open('u:bad key')") is False
    assert page.evaluate("FK.survival.open('x:surv-alpha')") is False
    assert page.evaluate("FK.survival.open('s:surv-alpha')") is True
    wait_hash(page, '#/survival/surv-alpha')


def test_f14_not_found_message_is_cleared_when_the_home_is_next_shown(page, app_url):
    boot(page, app_url, '#/survival/nope', topics=TOPICS)
    wait_hash(page, '#/survival')
    expect(page.locator('#survLive')).to_have_text('That Survival page was not found.')
    page.evaluate("FK.route.go('/emergency')")
    wait_hash(page, '#/emergency')
    page.evaluate("FK.route.go('/survival')")
    wait_hash(page, '#/survival')
    expect(page.locator('#survLive')).to_have_text('')


# ---------- Radiation pack (Task 8): category home, protected topics, links ----------

RAD = 'Radiation and fallout'


def _shipped(folder):
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return {os.path.basename(p)[:-5]: json.load(open(p, encoding='utf-8')) for p in glob.glob(os.path.join(root, 'src', folder, '*.json'))}


def test_radiation_topics_carry_no_where_or_when_key_in_the_shipped_data():
    rad = {i: t for i, t in _shipped('survival').items() if t.get('category') == 'radiation'}
    assert sorted('s:' + i for i in rad) == sorted(RADIATION)
    for i, t in rad.items():
        assert 'where' not in t and 'when' not in t, i


def test_radiation_hub_leads_the_category_and_all_ten_are_listed_under_every_filter(page, app_url):
    shipped_home(page, app_url)
    open_cat(page, RAD)
    for where in WHERES:
        for when in ('any', 'cold', 'warm'):
            page.evaluate(f"FK.store.set('survFilter', {{ where: '{where}', when: '{when}' }}); FK.survival.refreshHome()")
            rad = page.evaluate("[...document.querySelectorAll('#survCats details[data-cat=\"radiation\"] button[data-key]')].map(b => b.dataset.key)")
            assert sorted(rad) == sorted(RADIATION), f'where={where} when={when}: {rad}'
            assert rad[0] == 's:surv-fallout-warning', f'where={where} when={when}: {rad}'


def test_radiation_category_header_and_its_ten_rows_fit_360px(page, app_url):
    shipped_home(page, app_url)
    open_cat(page, RAD)
    for night in (False, True):
        if night:
            page.click('#nightBtn')
            assert page.evaluate('document.documentElement.dataset.theme') == 'night'
        d = page.locator('#survCats details[data-cat="radiation"]')
        boxes = [d.locator('summary').bounding_box()] + [b.bounding_box() for b in d.locator('button[data-key]').all()]
        assert len(boxes) == 11
        for b in boxes:
            assert b['x'] >= 0 and b['x'] + b['width'] <= 360, b
        assert page.evaluate('document.documentElement.scrollWidth') <= 360
        assert all(b['height'] >= 48 for b in boxes), [b['height'] for b in boxes]   # 48 px touch targets, header and rows
        spill = page.evaluate("""[...document.querySelectorAll('#survCats details[data-cat="radiation"] button[data-key]')].filter(b => {
            const r = b.getBoundingClientRect(), s = b.querySelector('span').getBoundingClientRect();
            return s.left < r.left || s.right > r.right || b.scrollWidth > b.clientWidth + 1; }).map(b => b.textContent)""")
        assert spill == []


def _links(node):
    """Every link key in a topic's section blocks."""
    out = []
    for sec in node.get('sections', []):
        for b in sec.get('blocks', []):
            if isinstance(b, dict) and 'link' in b:
                out.append(b['link'])
    return out


RADIATION_PROTOCOLS = ['p:radiation-decontamination', 'p:radiation-sickness']


def test_every_link_in_the_radiation_topics_and_the_six_protected_topics_resolves():
    from tools.validate import TOOL_NAMES
    topics, protocols, lists = _shipped('survival'), _shipped('protocols'), _shipped('checklists')
    known = ({'p:' + i for i in protocols} | {'s:' + i for i in topics} | {'c:' + i for i in lists}
             | {'u:' + n for n in TOOL_NAMES} | {'t:tq', 't:cpr', 't:rate', 't:burn', 'r:9line', 'r:mist'}
             | {'a:' + n for n in ('map', 'position', 'ballistics', 'areas', 'waypoints', 'settings')})
    assert 'u:fallout' not in known   # ruled out: no fallout tool
    assert 'c:fallout-shelter-kit' in known
    for tid in [k[2:] for k in RADIATION] + list(SIX):
        for k in _links(topics[tid]):
            assert k in known, f'{tid}: unknown link {k}'


def test_the_hub_links_every_other_radiation_topic_and_both_protocols():
    hub = _links(_shipped('survival')['surv-fallout-warning'])
    for k in RADIATION[1:] + RADIATION_PROTOCOLS:
        assert k in hub, k
    assert 'c:fallout-shelter-kit' in hub
    labels = [b['label'] for sec in _shipped('survival')['surv-fallout-warning']['sections'] for b in sec['blocks'] if b.get('link') == 'c:fallout-shelter-kit']
    assert labels == [_shipped('checklists')['fallout-shelter-kit']['title']]


# link blocks that earlier writers could not add because the targets did not exist (docs/v7.4-rulings.md, "Links later tasks must add")
LATER_LINKS = {
    'surv-fallout-warning': ['s:surv-fallout-coming-inside', 's:surv-fallout-water-and-food', 's:surv-fallout-leaving', 's:surv-dirty-bomb',
                             's:surv-potassium-iodide', 's:surv-fallout-get-ready', 'p:radiation-decontamination', 'p:radiation-sickness'],
    'surv-fallout-how-long': ['s:surv-fallout-leaving', 's:surv-fallout-coming-inside', 'p:radiation-decontamination'],
    'surv-fallout-where-to-shelter': ['s:surv-fallout-leaving', 's:surv-fallout-coming-inside'],
    'surv-fallout-shelter-living': ['s:surv-fallout-water-and-food', 's:surv-fallout-coming-inside', 'p:radiation-decontamination', 's:surv-fallout-leaving'],
    'surv-dirty-bomb': ['p:radiation-decontamination', 'p:radiation-sickness', 's:surv-fallout-leaving'],
    'surv-fallout-get-ready': ['s:surv-fallout-water-and-food', 's:surv-fallout-coming-inside', 'p:radiation-decontamination', 's:surv-fallout-leaving'],
    'surv-fallout-leaving': ['p:radiation-sickness', 'p:radiation-decontamination'],
    'surv-fallout-coming-inside': ['p:radiation-decontamination', 'p:radiation-sickness'],
}


@pytest.mark.parametrize('tid,wanted', sorted(LATER_LINKS.items()))
def test_links_the_earlier_radiation_writers_could_not_add_are_there(tid, wanted):
    have = _links(_shipped('survival')[tid])
    for k in wanted:
        assert k in have, f'{tid} lacks {k}'


def test_get_ready_reaches_the_shelter_kit_checklist():
    assert 'c:fallout-shelter-kit' in _links(_shipped('survival')['surv-fallout-get-ready'])


# the six checked topics each gain exactly one link block to a radiation topic and nothing else
SIX = {'surv-priorities': 's:surv-fallout-warning', 'surv-shelter': 's:surv-fallout-where-to-shelter',
       'surv-heat-out': 's:surv-fallout-shelter-living', 'surv-carbon-monoxide': 's:surv-fallout-shelter-living',
       'surv-water-store': 's:surv-fallout-water-and-food', 'surv-water-in-the-house': 's:surv-fallout-water-and-food'}


V73_RELEASE = '1cded2e'   # the v7.3 release commit: a fixed base, so this test stays true after the radiation pack merges


def _main_text(name):
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    r = subprocess.run(['git', 'show', f'{V73_RELEASE}:src/survival/{name}.json'], cwd=root, capture_output=True, text=True, encoding='utf-8')
    if r.returncode != 0:
        pytest.skip(f'v7.3 release commit {V73_RELEASE} is not in this clone, so the checked topics cannot be compared with it')
    return json.loads(r.stdout)


@pytest.mark.parametrize('tid,target', sorted(SIX.items()))
def test_the_six_checked_topics_differ_from_v73_release_by_one_added_link_block_apart_from_the_food_pack_link(tid, target):
    now, was = _shipped('survival')[tid], _main_text(tid)
    extra = []
    now_sections = json.loads(json.dumps(now['sections']))
    assert len(now_sections) == len(was['sections']), tid
    if tid in CHECKED_FOOD_LINKS:   # the food pack (v7.5) also adds one link block to four of the six: filtered out here, checked against v7.4 below
        for sn in now_sections:
            sn['blocks'] = [b for b in sn['blocks'] if b.get('link') != CHECKED_FOOD_LINKS[tid]]
    if tid in CHECKED_LAND_LINKS:   # and the land pack (v7.7) one to Priorities: filtered out here, checked against v7.4 below
        for sn in now_sections:
            sn['blocks'] = [b for b in sn['blocks'] if b.get('link') != CHECKED_LAND_LINKS[tid]]
    for sn, sw in zip(now_sections, was['sections']):
        assert sn['h'] == sw['h'], tid
        bn, bw = sn['blocks'], sw['blocks']
        if bn != bw:
            # the new block is the only difference: removing it gives back main's blocks
            added = [i for i in range(len(bn)) if bn[:i] + bn[i + 1:] == bw]
            assert added, f'{tid}: section {sn["h"]!r} differs by more than one block'
            extra.append(bn[added[0]])
    assert len(extra) == 1, f'{tid}: expected one added block, found {extra}'
    assert set(extra[0]) == {'link', 'label'} and extra[0]['link'] == target, extra[0]
    assert all(isinstance(v, str) and v for v in extra[0].values())
    for k in now:
        if k != 'sections':
            assert now[k] == was[k], f'{tid}: {k} changed'
    assert set(now) == set(was)


# ---------- Food pack (Task 8): category home, protected topics, links ----------

FOOD_CAT = 'Food'


def test_food_topics_carry_no_where_or_when_key_in_the_shipped_data():
    food = {i: t for i, t in _shipped('survival').items() if t.get('category') == 'food'}
    assert sorted('s:' + i for i in food) == sorted(FOOD)   # the three older food topics are under Basics, not here
    for i, t in food.items():
        assert 'where' not in t and 'when' not in t, i


def test_food_hub_leads_the_category_and_all_ten_are_listed_under_all_fifteen_filters(page, app_url):
    shipped_home(page, app_url)
    open_cat(page, FOOD_CAT)
    for where in WHERES:
        for when in ('any', 'cold', 'warm'):
            page.evaluate(f"FK.store.set('survFilter', {{ where: '{where}', when: '{when}' }}); FK.survival.refreshHome()")
            food = page.evaluate("[...document.querySelectorAll('#survCats details[data-cat=\"food\"] button[data-key]')].map(b => b.dataset.key)")
            assert sorted(food) == sorted(FOOD), f'where={where} when={when}: {food}'
            assert food[0] == 's:surv-food-power-out', f'where={where} when={when}: {food}'


def test_food_category_header_and_its_ten_rows_fit_360px(page, app_url):
    shipped_home(page, app_url)
    open_cat(page, FOOD_CAT)
    for night in (False, True):
        if night:
            page.click('#nightBtn')
            assert page.evaluate('document.documentElement.dataset.theme') == 'night'
        d = page.locator('#survCats details[data-cat="food"]')
        boxes = [d.locator('summary').bounding_box()] + [b.bounding_box() for b in d.locator('button[data-key]').all()]
        assert len(boxes) == 11
        for b in boxes:
            assert b['x'] >= 0 and b['x'] + b['width'] <= 360, b
        assert page.evaluate('document.documentElement.scrollWidth') <= 360
        assert all(b['height'] >= 48 for b in boxes), [b['height'] for b in boxes]
        spill = page.evaluate("""[...document.querySelectorAll('#survCats details[data-cat="food"] button[data-key]')].filter(b => {
            const r = b.getBoundingClientRect(), s = b.querySelector('span').getBoundingClientRect();
            return s.left < r.left || s.right > r.right || b.scrollWidth > b.clientWidth + 1; }).map(b => b.textContent)""")
        assert spill == []


def _known_keys():
    from tools.validate import TOOL_NAMES
    topics, protocols, lists = _shipped('survival'), _shipped('protocols'), _shipped('checklists')
    return ({'p:' + i for i in protocols} | {'s:' + i for i in topics} | {'c:' + i for i in lists}
            | {'u:' + n for n in TOOL_NAMES} | {'t:tq', 't:cpr', 't:rate', 't:burn', 'r:9line', 'r:mist'}
            | {'a:' + n for n in ('map', 'position', 'ballistics', 'areas', 'waypoints', 'settings')})


def _title_of(key):
    kind, i = key.split(':', 1)
    folder = {'p': 'protocols', 's': 'survival', 'c': 'checklists'}[kind]
    return _shipped(folder)[i]['title']


CHECKED_FOOD_LINKS = {'surv-priorities': 's:surv-food-how-much', 'surv-stomach-illness-in-a-group': 's:surv-food-clean-kitchen',
         'surv-generators': 's:surv-food-power-out', 'surv-fallout-water-and-food': 's:surv-food-still-good',
         'surv-fallout-get-ready': 's:surv-food-how-much', 'surv-water-store': 's:surv-food-how-much',
         'surv-heat-out': 's:surv-food-power-out', 'surv-carbon-monoxide': 's:surv-food-cooking-no-power'}


def test_every_link_in_the_food_pages_and_the_checked_topics_resolves_and_is_labelled_with_the_title():
    topics = _shipped('survival')
    known = _known_keys()
    assert 'u:food' not in known and 'p:botulism' not in known   # ruled out in this release: no food planner, no botulism protocol
    pantry = _shipped('checklists')['pantry']
    assert pantry['title'] == 'Pantry'
    for tid in [k[2:] for k in FOOD]:
        for sec in topics[tid]['sections']:
            for b in sec['blocks']:
                if 'link' in b:
                    assert b['link'] in known, f'{tid}: unknown link {b["link"]}'
                    if b['link'][:2] in ('p:', 's:', 'u:', 'c:'):
                        assert b['label'] == _title_of(b['link']), f'{tid}: label {b["label"]!r} for {b["link"]}'
    for tid, target in CHECKED_FOOD_LINKS.items():
        for k in _links(topics[tid]):
            assert k in known, f'{tid}: unknown link {k}'
        added = [b for sec in topics[tid]['sections'] for b in sec['blocks'] if b.get('link') == target]
        assert added and all(b['label'] == _title_of(target) for b in added), tid


def test_the_food_hub_links_every_other_food_topic_and_the_checklist():
    hub = _shipped('survival')['surv-food-power-out']
    keys = _links(hub)
    for k in FOOD[1:] + ['c:pantry']:
        assert k in keys, k
    assert 's:surv-generators' in keys
    everything = [b['link'] for sec in hub['sections'] if sec['h'] == 'Everything on food' for b in sec['blocks'] if 'link' in b]
    assert everything[0] == 's:surv-food-how-much'   # how much to store is linked first (spec 10, call 7)
    assert 'c:pantry' in [b['link'] for sec in hub['sections'] if sec['h'] == 'Get ready before it happens' for b in sec['blocks'] if 'link' in b]


# link blocks that earlier writers could not add because their targets did not exist (docs/v7.5-rulings.md, "Links later tasks must add"):
# topic -> {section: [keys]}; there is no u:food and no p:botulism in this release
FOOD_LATER_LINKS = {
    'surv-food-power-out': {'Everything on food': ['s:surv-food-how-much', 's:surv-food-storage', 's:surv-food-when-short', 's:surv-food-clean-kitchen',
                                                   's:surv-food-babies-children', 's:surv-food-preserving'],
                            'Get ready before it happens': ['s:surv-food-how-much', 'c:pantry']},
    'surv-food-still-good': {'Cans and jars': ['s:surv-food-storage'], 'Home-canned food': ['s:surv-food-preserving'],
                             'Flood water': ['s:surv-food-clean-kitchen'], 'More': ['s:surv-food-clean-kitchen', 's:surv-food-babies-children']},
    'surv-food-cooking-no-power': {'Cook it through': ['s:surv-food-clean-kitchen'], 'Eat it cold': ['s:surv-food-how-much']},
    'surv-food-poisoning': {'Honey and babies': ['s:surv-food-babies-children'], 'Several people sick': ['s:surv-food-clean-kitchen'],
                            'Getting rid of a suspect can or jar': ['s:surv-food-preserving']},
    'surv-food-how-much': {'Babies, children and special needs': ['s:surv-food-babies-children']},
    'surv-food-storage': {'Dates on food': ['s:surv-food-babies-children'], 'In the freezer': ['s:surv-food-preserving'],
                          'Insects and rodents': ['s:surv-food-clean-kitchen']},
    'surv-food-when-short': {'Who must not go short': ['s:surv-food-babies-children'], 'Make what you have last': ['s:surv-food-preserving']},
    'surv-food-babies-children': {'From 12 months': ['s:surv-food-when-short'], 'When formula runs out': ['c:pantry'],
                                  'Formula: which kind': ['s:surv-food-storage']},
    'surv-food-clean-kitchen': {'Raw and cooked apart': ['s:surv-food-storage']},
    'surv-food-preserving': {'Cold storage': ['s:surv-food-storage'], 'Learning in normal times': ['s:surv-food-storage', 's:surv-food-how-much']},
}


@pytest.mark.parametrize('tid', sorted(FOOD_LATER_LINKS))
def test_links_the_food_writers_could_not_add_are_in_their_sections(tid):
    sections = {sec['h']: [b['link'] for b in sec['blocks'] if 'link' in b] for sec in _shipped('survival')[tid]['sections']}
    for h, wanted in FOOD_LATER_LINKS[tid].items():
        for k in wanted:
            assert k in sections[h], f'{tid} / {h} lacks {k}'


PACK_COMMIT = '4375170'   # the v7.4 release commit: a fixed base, so this test stays true after the food pack merges


def _v74_text(name):
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    r = subprocess.run(['git', 'show', f'{PACK_COMMIT}:src/survival/{name}.json'], cwd=root, capture_output=True, text=True, encoding='utf-8')
    if r.returncode != 0:
        pytest.skip(f'v7.4 release commit {PACK_COMMIT} is not in this clone, so the checked topics cannot be compared with it')
    return json.loads(r.stdout)


# the land pack (v7.7) adds a second link block to one of them (spec 7, Fallout): filtered out here after checking it is there exactly once
CHECKED_LAND_LINKS = {'surv-fallout-water-and-food': 's:surv-land-after-fallout',
                      'surv-priorities': 's:surv-land-start'}   # and Priorities one block to the land hub (land plan, Task 7)


@pytest.mark.parametrize('tid,target', sorted(CHECKED_FOOD_LINKS.items()))
def test_the_checked_topics_differ_from_v74_release_by_one_added_link_block(tid, target):
    now, was = _shipped('survival')[tid], _v74_text(tid)
    extra = []
    now_sections = json.loads(json.dumps(now['sections']))
    assert len(now_sections) == len(was['sections']), tid
    if tid in CHECKED_LAND_LINKS:
        land = [b for sn in now_sections for b in sn['blocks'] if b.get('link') == CHECKED_LAND_LINKS[tid]]
        assert land == [{'link': CHECKED_LAND_LINKS[tid], 'label': _title_of(CHECKED_LAND_LINKS[tid])}], land
        for sn in now_sections:
            sn['blocks'] = [b for b in sn['blocks'] if b.get('link') != CHECKED_LAND_LINKS[tid]]
    for sn, sw in zip(now_sections, was['sections']):
        assert sn['h'] == sw['h'], tid
        bn, bw = sn['blocks'], sw['blocks']
        if bn != bw:
            added = [i for i in range(len(bn)) if bn[:i] + bn[i + 1:] == bw]
            assert added, f'{tid}: section {sn["h"]!r} differs by more than one block'
            extra.append(bn[added[0]])
    assert len(extra) == 1, f'{tid}: expected one added block, found {extra}'
    assert set(extra[0]) == {'link', 'label'} and extra[0]['link'] == target, extra[0]
    assert all(isinstance(v, str) and v for v in extra[0].values())
    for k in now:
        if k != 'sections':
            assert now[k] == was[k], f'{tid}: {k} changed'
    assert set(now) == set(was)


def test_cooking_or_the_power_out_hub_links_field_dressing_game_by_its_title():
    # v7.5 kept this link out for the "dressing" search (docs/v7.5-rulings.md); v7.7 lifts the ban (land spec 12) and requires the link
    # from one of the two food pages that send people to the game rule. Preserving food points to Preserving game meat instead.
    topics = _shipped('survival')
    blocks = [b for tid in ('surv-food-cooking-no-power', 'surv-food-power-out') for sec in topics[tid]['sections']
              for b in sec['blocks'] if b.get('link') == 's:surv-field-dressing-game']
    assert blocks, 'neither Cook without power nor Food when the power goes out links Field dressing game'
    assert all(b['label'] == topics['surv-field-dressing-game']['title'] == 'Field dressing game' for b in blocks), blocks
    assert 's:surv-field-dressing-game' not in _links(topics['surv-food-preserving'])
    assert 's:surv-land-keeping-meat' in _links(topics['surv-food-preserving'])


def test_home_section_headings_have_space_above_and_read_as_labels(page, app_url):
    """Every home heading is the first child of its own section, so the space above has to come from the
    section: in v7.5 the headings sat flush against the card above them."""
    page.goto(app_url + '#/survival')
    page.wait_for_selector('#survLists h2')
    gaps = page.evaluate("""() => ['survTopics', 'survTools', 'survLists'].map(id => {
      const el = document.getElementById(id), h = el.querySelector('h2'), cs = getComputedStyle(h);
      let prev = el.previousElementSibling;
      while (prev && !prev.getBoundingClientRect().height) prev = prev.previousElementSibling;
      return { id, gap: h.getBoundingClientRect().top - prev.getBoundingClientRect().bottom,
               upper: cs.textTransform, size: parseFloat(cs.fontSize) };
    })""")
    for g in gaps:
        assert g['gap'] >= 24, g
        assert g['upper'] == 'uppercase' and g['size'] < 16, g
    row = page.evaluate("parseFloat(getComputedStyle(document.querySelector('#survCats summary')).fontSize)")
    assert row > gaps[0]['size']


# ---------- Food from the land (v7.7): the land category ----------

def test_the_three_moved_topics_are_category_land_and_carry_no_where_or_when_key_in_the_shipped_data():
    land = {i: t for i, t in _shipped('survival').items() if t.get('category') == 'land'}
    assert sorted('s:' + i for i in land if not i.startswith('surv-land-')) == sorted(MOVED)   # the rest of the pack arrives with its content
    for i, t in land.items():
        assert 'where' not in t and 'when' not in t, i


def test_land_category_sits_after_food_and_holds_the_three_moved_topics(page, app_url):
    shipped_home(page, app_url)
    heads = page.evaluate("[...document.querySelectorAll('#survCats details[data-cat] > summary')].map(s => s.textContent.trim())")   # CSS capitals are not in textContent
    assert 'Food from the land' in heads and heads.index('Food from the land') == heads.index('Food') + 1, heads
    cat = lambda c: page.evaluate(f"[...document.querySelectorAll('#survCats details[data-cat=\"{c}\"] button[data-key]')].map(b => b.dataset.key)")
    assert set(MOVED) <= set(cat('land'))
    assert not set(MOVED) & set(cat('basics'))


def test_moved_topics_are_listed_under_all_fifteen_filters(page, app_url):
    shipped_home(page, app_url)
    for where in WHERES:
        for when in ('any', 'cold', 'warm'):
            page.evaluate(f"FK.store.set('survFilter', {{ where: '{where}', when: '{when}' }}); FK.survival.refreshHome()")
            land = page.evaluate("[...document.querySelectorAll('#survCats details[data-cat=\"land\"] button[data-key]')].map(b => b.dataset.key)")
            assert set(MOVED) <= set(land), f'where={where} when={when}: {land}'


def test_land_hub_leads_the_category_and_every_land_topic_is_listed_under_all_fifteen_filters(page, app_url):
    shipped_home(page, app_url)
    every = sorted('s:' + i for i, t in _shipped('survival').items() if t.get('category') == 'land')
    assert 's:surv-land-start' in every
    open_cat(page, 'Food from the land')
    for where in WHERES:
        for when in ('any', 'cold', 'warm'):
            page.evaluate(f"FK.store.set('survFilter', {{ where: '{where}', when: '{when}' }}); FK.survival.refreshHome()")
            land = page.evaluate("[...document.querySelectorAll('#survCats details[data-cat=\"land\"] button[data-key]')].map(b => b.dataset.key)")
            assert sorted(land) == every, f'where={where} when={when}: {land}'
            assert land[0] == 's:surv-land-start', f'where={where} when={when}: {land}'


def test_the_land_hub_links_every_other_land_topic_and_the_checklist():
    topics = _shipped('survival')
    hub = topics['surv-land-start']
    keys = _links(hub)
    for tid, t in topics.items():
        if t.get('category') == 'land' and tid != 'surv-land-start':
            assert 's:' + tid in keys, tid
    assert 'c:land-kit' in keys and _shipped('checklists')['land-kit']['category'] == 'land'
    known = _known_keys()
    for k in keys:
        assert k in known, k


def _texts(t):
    out = list(t.get('doFirst', []))
    for sec in t['sections']:
        for b in sec['blocks']:
            for k in ('p', 'warn'):
                if k in b:
                    out.append(b[k])
            for k in ('list', 'steps'):
                out.extend(b.get(k, []))
    return out


def test_wild_plants_keeps_the_quoted_sentences_the_mushroom_rule_and_the_poisoning_link_and_draws_no_plant():
    # spec 10 calls 2, 3 and 9: the sentences Rationing food quotes word for word are frozen; the mushroom warning stays word for word
    topics = _shipped('survival')
    t = topics['surv-food-and-wild-plants']
    assert t['title'] == 'Wild plants' and t['category'] == 'land'
    texts = _texts(t)
    for quoted in ('Food is the lowest priority: you can survive about three weeks without it. Don’t spend energy or risk poisoning chasing it early.',
                   'Only eat a plant you can identify with certainty.'):
        assert quoted in texts, quoted
        assert quoted in ' '.join(_texts(topics['surv-food-when-short'])), quoted
    assert ('Never eat a wild mushroom unless an expert has identified it. Poisonous mushrooms can look like edible ones, there is no field '
            'test that shows a mushroom is safe, and cooking does not destroy the poisons.') in texts
    assert 'p:poisoning' in _links(t)
    assert not any('fig' in b for sec in t['sections'] for b in sec['blocks'])


def test_the_cdc_bottle_soak_is_on_the_babies_page_for_that_use_only_and_clean_and_disinfect_names_the_special_mixes():
    # spec 7 "Bleach" and spec 12: the soak is added as CDC gives it; Clean and disinfect gains one sentence naming the special mixes
    topics = _shipped('survival')
    texts = _texts(topics['surv-food-babies-children'])
    assert 'For each 1/2 gallon (1.9 L) or 8 cups of water, add 1 teaspoon (5 mL) of unscented bleach (CDC).' in texts
    assert 'Soak for 2 minutes (CDC).' in texts
    assert 'CDC’s bleach soak is for baby bottles and feeding items only. Never use it for drinking water.' in texts
    assert not any('is not on this page' in x for x in texts)
    special = [x for x in _texts(topics['surv-clean-and-disinfect']) if 'three more special-purpose bleach mixes' in x]
    assert len(special) == 1 and 'Feeding babies and young children' in special[0] and 'Food poisoning and botulism' in special[0]
    assert 'Butchering deer and small game' in special[0]   # the knife and tool soak (whole-pack read, C1)
    assert 'never for drinking water' in special[0]
    assert '5 parts clean water' in ' '.join(_texts(topics['surv-food-poisoning']))   # the clean-up mix is where the sentence says


def test_the_one_to_one_knife_soak_is_for_knives_and_tools_only_and_trapping_sends_knives_to_it():
    # whole-pack read C1: Clean and disinfect owns the household mixes, so counters get its food mix; NYS DOH's 1:1 soak stays on
    # Butchering for knives and tools only, and Trapping's "clean and disinfect knives and tools" opens the page that has it
    topics = _shipped('survival')
    land = [x for tid, t in topics.items() if t.get('category') == 'land' for x in _texts(t)]
    soak = [x for x in land if 'equal amount of water' in x]
    assert len(soak) == 1, soak
    assert 'for knives and tools only' in soak[0] and 'never put it on counters' in soak[0], soak[0]
    assert 'never use it for drinking water' in soak[0]
    for x in land:
        low = x.lower()
        assert not ('counter' in low and ('same mix' in low or 'equal amount' in low) and 'never put it on counters' not in low), x
    butcher = ' '.join(_texts(topics['surv-land-butchering']))
    assert 'To sanitize counters and other surfaces, and the tools you used on any animal other than a deer, use the food mix in Clean and disinfect.' in butcher
    assert 's:surv-clean-and-disinfect' in _links(topics['surv-land-butchering'])
    trap = topics['surv-land-trapping']
    sec = next(s for s in trap['sections'] if s['h'] == 'Rabies, disease and handling')
    item = next(x for b in sec['blocks'] for x in b.get('list', []) if x.startswith('Clean and disinfect knives and tools'))
    assert 'Butchering deer and small game' in item, item
    assert 's:surv-land-butchering' in [b['link'] for b in sec['blocks'] if 'link' in b]

def _all_texts(t):
    # every user-visible string of a topic: the summary, Do first, blocks and table cells
    out = [t.get('summary', '')] + list(t.get('doFirst', []))
    for sec in t['sections']:
        out.append(sec['h'])
        for b in sec['blocks']:
            for k in ('p', 'warn', 'cap'):
                if k in b:
                    out.append(b[k])
            for k in ('list', 'steps'):
                out.extend(b.get(k, []))
            if 'table' in b:
                out.extend(b['table']['head'])
                out.extend(c for row in b['table']['rows'] for c in row)
    return out


def test_warm_meat_time_limits_each_have_one_owner():
    # whole-pack read C2: Is it still good? owns the 2-hour and 1-hour rule for perishable food (quoted, never restated); Field dressing
    # game owns how fast a carcass is chilled (3 to 4 hours in air above 40°F, 24 hours otherwise) and NYS DOH's 45°F sentence; Preserving
    # game meat quotes or links it
    topics = _shipped('survival')
    still = 'never leave perishable food out for more than 2 hours, or 1 hour if it is above 90°F (32°C) (CDC).'
    assert still in ' '.join(_all_texts(topics['surv-food-still-good']))
    land = {tid: t for tid, t in topics.items() if t.get('category') == 'land'}
    for tid, t in land.items():
        for x in _all_texts(t):
            rest = x.replace(still, '')
            if 'perishable' in rest.lower():   # a perishable-food time limit only inside the quoted rule
                assert not re.search(r'\bhours?\b', rest), (tid, x)
            # whole-branch review I3: Preserving game meat quotes the owner's caution word for word; the hours appear nowhere else
            owner = '“This app’s caution: meat you can’t chill within 3 to 4 hours of the kill, cook within that time or don’t eat it.”'
            if tid == 'surv-land-keeping-meat':
                x = x.replace(owner, '')
            if '3 to 4 hours' in x or 'three to four hours' in x:
                assert tid == 'surv-field-dressing-game', (tid, x)
            n45 = len(re.findall(r'(?<!\d)45°F', x))   # not 145°F
            if n45 and tid != 'surv-field-dressing-game':
                assert n45 == x.count('“Keep game cool, with ice or below 45°F (7°C) (the meat), until it is butchered'), (tid, x)
    fd = _all_texts(land['surv-field-dressing-game'])
    assert any(still in x for x in fd)
    cooling = next(s for s in land['surv-field-dressing-game']['sections'] if s['h'] == 'Cooling the carcass')
    text = ' '.join(_all_texts({'sections': [cooling]}))
    for must in ('within 3 to 4 hours of the kill (Ohio State University Extension)', 'No ice, snow or fridge, and the air above 40°F',
                 'Found later.', 'This app’s caution: don’t eat it.'):
        assert must in text, must
    assert 's:surv-food-still-good' in _links({'sections': [cooling]})
    keep = land['surv-land-keeping-meat']
    assert 'Hanging a carcass below' in keep['doFirst'][0] and '45°F' not in keep['doFirst'][0]
    hanging = next(s for s in keep['sections'] if s['h'] == 'Hanging a carcass')
    assert 's:surv-field-dressing-game' in _links({'sections': [hanging]})
    for tid in ('surv-land-big-game', 'surv-land-keeping-meat'):
        assert 's:surv-field-dressing-game' in _links(land[tid]), tid

def test_preserving_game_meat_says_the_agency_jerky_needs_a_working_oven_or_dehydrator_and_never_sends_drying_outdoors():
    # whole-pack read C3 and C4: the summary and Do first name the dehydrator or oven and the power outage; "outdoors only" is for smoke
    # and fire, never for drying; the jerky method quotes Cook without power on the gas oven, word for word, and links it
    topics = _shipped('survival')
    keep = topics['surv-land-keeping-meat']
    box = ' '.join(keep['doFirst'])
    for where in (keep['summary'], box):
        assert 'dehydrator' in where and 'oven that holds 140°F (60°C)' in where and 'without power' in where or 'no power' in where, where
        assert 'the agencies advise against drying meat in the sun or open air' in where.lower(), where
    for x in _all_texts(keep):
        low = x.lower()
        assert 'dry meat outdoors' not in low and 'smoke and dry meat' not in low and 'dry meat only outdoors' not in low, x
    oven = 'Never the oven: most can’t be lit by hand in an outage (GE, Whirlpool, KitchenAid), and Wolf says not to try.'
    assert oven in ' '.join(_texts(topics['surv-food-cooking-no-power']))
    jerky = next(sec for sec in keep['sections'] if sec['h'] == 'Jerky')
    jtext = ' '.join(_all_texts({'sections': [jerky]}))
    assert oven in jtext and 'this method can’t be done' in jtext
    assert 's:surv-food-cooking-no-power' in _links({'sections': [jerky]})

def test_whole_pack_read_fixes_keep_one_answer_per_question():
    # whole-pack read, Important and Minor findings and carried items: each page that used to contradict another now links or quotes it
    topics = _shipped('survival')
    t = lambda tid: ' '.join(_all_texts(topics[tid]))
    fd, butcher, hub = t('surv-field-dressing-game'), t('surv-land-butchering'), t('surv-land-start')
    # I1: game with no thermometer gets a plain answer; the fish page gives FDA's own words for fish
    assert 'No thermometer: no source opened gives a sign you can go by for game.' in fd
    assert 'well past the point they look done; never eat game rare.' in fd   # re-check R3
    assert 'Cooling the carcass, and what to do with no ice, snow or fridge or with a deer found later' in t('surv-land-keeping-meat')   # R1
    assert 'a gut-shot deer left overnight in mild air is not eaten' in t('surv-land-big-game')   # R5
    assert '“If you don’t have a food thermometer, there are other ways to determine whether seafood is done.”' in t('surv-land-fish-cleaning')
    # I2: one decision on a deer's heart and liver, on Butchering; Field dressing and the kit point to it
    assert ('eat a deer’s heart and liver only if the deer has tested negative for chronic wasting disease (testing is possible only in '
            'normal times); with no test, leave them.') in butcher and 'in normal times, eat a deer' not in butcher
    assert 'Keep the heart and liver in a clean bag if they look healthy' not in fd and 'Heart, liver and tongue' in fd
    kit = {i['id']: i for i in _shipped('checklists')['land-kit']['items']}
    assert 'when Butchering deer and small game says to keep them' in kit['bags']['note']
    # I3: an animal already caught or shot that looks sick has steps on the owner page, and Trapping and Small game link to them
    assert any(sec['h'] == 'Already caught or shot, and it looks sick' for sec in topics['surv-field-dressing-game']['sections'])
    for tid in ('surv-land-trapping', 'surv-land-small-game'):
        assert '“Already caught or shot, and it looks sick”' in t(tid), tid
    assert 'In normal times, report sick rabbits' in t('surv-land-small-game')
    # I4: the hub's spring cattail line carries the iris warning from Wild plants, word for word
    iris = 'Yellow iris can be confused with cattail, especially when it is not in bloom: their leaves are very similar (Government of Alberta).'
    assert iris in t('surv-food-and-wild-plants') and '“' + iris + '”' in hub
    # I5: no plant is eaten on looks alone
    assert 'looks like a store-bought' not in t('surv-food-and-wild-plants')
    # I6: the kit's saw note follows Butchering, not the pelvis and breastbone
    assert 'pelvis' not in kit['hatchet-saw']['note'] and 'Butchering deer and small game' in kit['hatchet-saw']['note']
    # I7: Field dressing's birds link the migratory bird rule
    birds = next(sec for sec in topics['surv-field-dressing-game']['sections'] if sec['h'] == 'Birds')
    assert 's:surv-land-ny-rules' in _links({'sections': [birds]})
    # I8: the babies page links the fish advice
    assert 's:surv-land-fish-cleaning' in _links(topics['surv-food-babies-children'])
    # I10: bear jerky is sent to the page that has it
    assert 'why bear is never made into jerky is in Preserving game meat' in t('surv-land-big-game')
    assert 'bear' in t('surv-land-keeping-meat').lower() and 'jerky' not in fd.lower()
    # M1: Butchering's summary names every part its never-eat box names
    assert 'spleen, pancreas, tonsils' in topics['surv-land-butchering']['summary']
    # M2: the hub quotes Fishing for food's ice warning word for word
    ice = next(b['warn'] for sec in topics['surv-traps-and-fishing']['sections'] if sec['h'] == 'Ice fishing' for b in sec['blocks'] if 'warn' in b)
    quoted = ice.split(' Slush ice')[0]
    assert '“' + quoted + '”' in hub and '3 to 4 inches' not in hub
    # M3: gloves always, above all with rabbits, hares and rodents
    assert kit['gloves']['note'].startswith('Always;')
    # carried 1: the low-head dam warning sits with the line that sends people below a dam
    where = next(sec for sec in topics['surv-traps-and-fishing']['sections'] if sec['h'] == 'Where the fish are')
    assert any('Low-head dams' in b.get('warn', '') for b in where['blocks'])
    # carried 4: Trapping's lead-in sits directly above the manual's steps
    kill = next(sec for sec in topics['surv-land-trapping']['sections'] if sec['h'] == 'Killing a trapped animal')
    i = next(n for n, b in enumerate(kill['blocks']) if 'steps' in b)
    assert kill['blocks'][i - 1] == {'p': 'The steps, from the NYS DEC trapper manual, in its order:'}
    assert 'From the NYS DEC trapper manual, in its order.' not in t('surv-land-trapping')
    # carried 5: no cell says both "eat by the statewide table" and "don't eat" in the old words
    assert 'As the first table' not in t('surv-land-fish-cleaning')

def test_fishing_fish_cleaning_and_trapping_split_the_old_traps_topic():
    # land pack batch C (spec 4 rows 2, 5, 7; spec 10 calls 4, 7, 9): Fishing for food keeps the id and is fishing only; the fish
    # cooking sentence Cook without power quotes word for word from Field dressing game is carried identically by the new owner of
    # fish at 145°F; Trapping states New York's position on snares and deadfalls on the same page; no land topic has a Where or When tag
    topics = _shipped('survival')
    fishing, clean, trap = topics['surv-traps-and-fishing'], topics['surv-land-fish-cleaning'], topics['surv-land-trapping']
    assert fishing['title'] == 'Fishing for food'
    for t in (fishing, clean, trap):
        assert t['category'] == 'land' and 'where' not in t and 'when' not in t
    quoted = 'Cook all wild game and birds to at least 165°F in the thickest part, and fish to 145°F.'
    assert quoted in ' '.join(_texts(clean))
    assert quoted in ' '.join(_texts(topics['surv-food-cooking-no-power']))
    fish_text = ' '.join(_texts(fishing)).lower()
    for word in ('snare', 'deadfall', 'body-gripping', 'foothold'):
        assert word not in fish_text, word
    trap_text = ' '.join(_texts(trap))
    assert 'New York law forbids setting a snare or any noose that can take an animal' in trap_text
    assert 'New York law counts a deadfall as a trapping device' in trap_text
    assert 'This app’s caution: don’t set one without asking DEC.' in trap_text and 'Illegal in normal times' not in trap_text
    assert 'touch the eye or mouth with the striking tool, never your hand' in trap_text
    assert 's:surv-land-ny-rules' in _links(trap) and 's:surv-land-ny-rules' in _links(fishing)
    assert {'s:surv-land-butchering', 's:surv-land-keeping-meat', 's:surv-field-dressing-game'} <= set(_links(trap))
    fd = topics['surv-field-dressing-game']
    assert 's:surv-land-fish-cleaning' in _links(fd) and quoted in ' '.join(_texts(fd))
    for t in ('surv-food-when-short', 'surv-food-power-out'):
        labels = [b['label'] for s in topics[t]['sections'] for b in s['blocks'] if b.get('link') == 's:surv-traps-and-fishing']
        assert labels == ['Fishing for food'], (t, labels)
    assert 's:surv-land-fish-cleaning' in _links(fishing) and 's:surv-traps-and-fishing' in _links(clean)


# ---------- Food from the land (v7.7): home, links and labels after the content ----------

LAND_CAT = 'Food from the land'


def test_land_category_holds_exactly_the_twelve_land_topics_and_basics_none_of_the_moved_ones(page, app_url):
    assert sorted('s:' + i for i, t in _shipped('survival').items() if t.get('category') == 'land') == sorted(LAND)
    shipped_home(page, app_url)
    open_cat(page, LAND_CAT)
    land = page.evaluate("[...document.querySelectorAll('#survCats details[data-cat=\"land\"] button[data-key]')].map(b => b.dataset.key)")
    basics = page.evaluate("[...document.querySelectorAll('#survCats details[data-cat=\"basics\"] button[data-key]')].map(b => b.dataset.key)")
    assert land[0] == 's:surv-land-start' and sorted(land) == sorted(LAND), land
    assert len(basics) == 8 and not set(LAND) & set(basics), basics


def test_land_category_header_and_its_twelve_rows_fit_360px(page, app_url):
    shipped_home(page, app_url)
    open_cat(page, LAND_CAT)
    for night in (False, True):
        if night:
            page.click('#nightBtn')
            assert page.evaluate('document.documentElement.dataset.theme') == 'night'
        d = page.locator('#survCats details[data-cat="land"]')
        boxes = [d.locator('summary').bounding_box()] + [b.bounding_box() for b in d.locator('button[data-key]').all()]
        assert len(boxes) == 13
        for b in boxes:
            assert b['x'] >= 0 and b['x'] + b['width'] <= 360, b
        assert page.evaluate('document.documentElement.scrollWidth') <= 360
        assert all(b['height'] >= 48 for b in boxes), [b['height'] for b in boxes]
        spill = page.evaluate("""[...document.querySelectorAll('#survCats details[data-cat="land"] button[data-key]')].filter(b => {
            const r = b.getBoundingClientRect(), s = b.querySelector('span').getBoundingClientRect();
            return s.left < r.left || s.right > r.right || b.scrollWidth > b.clientWidth + 1; }).map(b => b.textContent)""")
        assert spill == []


def test_every_link_in_every_land_topic_resolves_and_is_labelled_with_the_title():
    topics = _shipped('survival')
    known = _known_keys()
    seen = 0
    for tid in [k[2:] for k in LAND]:
        for sec in topics[tid]['sections']:
            for b in sec['blocks']:
                if 'link' in b:
                    seen += 1
                    assert b['link'] in known, f'{tid} / {sec["h"]}: unknown link {b["link"]}'
                    if b['link'][:2] in ('p:', 's:', 'c:'):
                        assert b['label'] == _title_of(b['link']), f'{tid} / {sec["h"]}: label {b["label"]!r} for {b["link"]}'
                    elif b['link'].startswith('u:'):
                        assert b['label'].strip(), f'{tid}: empty label for {b["link"]}'
    assert seen > 100   # a handful would mean the walk found nothing


LAND_BASE = '0244043'   # the search changes, before any land content: what the older pages looked like before this pack


def _base_topic(name):
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    r = subprocess.run(['git', 'show', f'{LAND_BASE}:src/survival/{name}.json'], cwd=root, capture_output=True, text=True, encoding='utf-8')
    if r.returncode != 0:   # a clone without the base commit must not pass these checks by skipping them
        pytest.fail(f'commit {LAND_BASE} is not in this clone, so the older pages cannot be compared with it: '
                    f'fetch the full history (git fetch --unshallow) and run again. git said: {r.stderr.strip()}')
    return json.loads(r.stdout)


def _link_blocks(t):
    return [b for sec in t['sections'] for b in sec['blocks'] if 'link' in b]


def test_every_link_the_land_pack_added_or_relabelled_on_older_pages_resolves_and_is_labelled_with_the_title():
    # older pages keep labels they always had (some are not their target's title, e.g. "Hypothermia care"); every link block this pack
    # added or relabelled carries the target's title, and every link on an edited older page still resolves
    topics, known = _shipped('survival'), _known_keys()
    edited = []
    for tid, t in sorted(topics.items()):
        if t.get('category') == 'land':
            continue
        was = _base_topic(tid)
        if was == t:
            continue
        edited.append(tid)
        old = _link_blocks(was)
        for b in _link_blocks(t):
            assert b['link'] in known, f'{tid}: unknown link {b["link"]}'
            if b not in old and b['link'][:2] in ('p:', 's:', 'c:'):
                assert b['label'] == _title_of(b['link']), f'{tid}: label {b["label"]!r} for {b["link"]}'
    assert {'surv-priorities', 'surv-dangerous-animals', 'surv-food-when-short', 'surv-food-power-out', 'surv-food-cooking-no-power',
            'surv-food-preserving', 'surv-clean-and-disinfect', 'surv-fallout-water-and-food'} <= set(edited), edited


# The plan's list (land plan, Task 7): one link block each from the older page into the pack, and no second
LAND_POINTERS = {'surv-priorities': 's:surv-land-start', 'surv-dangerous-animals': 's:surv-land-big-game',
                 'surv-food-when-short': 's:surv-land-start', 'surv-food-power-out': 's:surv-land-start',
                 'surv-food-cooking-no-power': 's:surv-field-dressing-game'}


@pytest.mark.parametrize('tid,target', sorted(LAND_POINTERS.items()))
def test_the_older_pages_on_the_plan_list_gain_exactly_one_link_block_into_the_pack(tid, target):
    topics = _shipped('survival')
    now, was = topics[tid], _base_topic(tid)
    land = {'s:' + i for i, t in topics.items() if t.get('category') == 'land'} | {'c:land-kit'}
    old_links = [b['link'] for b in _link_blocks(was)]
    added = [b for b in _link_blocks(now) if b['link'] not in old_links]
    assert added == [{'link': target, 'label': _title_of(target)}], added
    assert target in land
    # nothing else was reworded: with the added block left out, every block is as it was, apart from labels and names that now follow
    # a renamed title (spec 10 call 9)
    renamed = lambda x: json.loads(json.dumps(x).replace('Food and wild plants', 'Wild plants').replace('Traps and fishing', 'Fishing for food'))
    for sn, sw in zip(now['sections'], was['sections']):
        assert sn['h'] == sw['h']
        bn = [b for b in sn['blocks'] if b not in added]
        assert len(bn) == len(sw['blocks']), (tid, sn['h'])
        for a, b in zip(bn, sw['blocks']):
            if a != b:
                assert a == renamed(b), (tid, a, b)
                if 'link' in a:
                    assert a['label'] == _title_of(a['link']), (tid, a)
    assert len(now['sections']) == len(was['sections'])


def test_the_land_hub_links_trapping_fish_cleaning_and_new_york_rules_where_its_text_names_them():
    hub = _shipped('survival')['surv-land-start']
    sections = {sec['h']: [b['link'] for b in sec['blocks'] if 'link' in b] for sec in hub['sections']}
    everything = sections['Everything in Food from the land']
    assert everything[:3] == ['s:surv-traps-and-fishing', 's:surv-land-fish-cleaning', 's:surv-land-trapping'], everything
    assert 's:surv-land-ny-rules' in sections['Who should not go out']   # its text says "see New York rules"


def test_fishing_fish_cleaning_and_trapping_link_the_hub_and_preserving_food_points_to_preserving_game_meat():
    topics = _shipped('survival')
    for tid in ('surv-traps-and-fishing', 'surv-land-fish-cleaning', 'surv-land-trapping', 'surv-food-and-wild-plants',
                'surv-field-dressing-game', 'surv-land-butchering', 'surv-land-keeping-meat', 'surv-land-ny-rules', 'surv-land-after-fallout'):
        assert 's:surv-land-start' in _links(topics[tid]), tid
    assert topics['surv-land-keeping-meat']['title'] == 'Preserving game meat'
    pointers = [b for b in _link_blocks(topics['surv-food-preserving']) if b['link'] == 's:surv-land-keeping-meat']
    assert pointers and all(b['label'] == 'Preserving game meat' for b in pointers)
    rules = _links(topics['surv-land-ny-rules'])
    for k in ('s:surv-land-trapping', 's:surv-traps-and-fishing', 's:surv-land-fish-cleaning', 's:surv-land-big-game', 's:surv-land-small-game'):
        assert k in rules, k


# ---------- Food from the land (v7.7): whole-branch review fixes ----------

FISH_SENSITIVE = 'People who may become pregnant (under age 50) and children under 15'   # NYS DOH's own definition, re-opened


def test_every_fish_advice_table_names_both_groups_in_its_head_and_each_water_has_its_own_table():
    # whole-branch review I1: a 39-row table left the two advice columns unlabelled after a screen; now every advice table is one water
    # (or the statewide advice) and carries both groups in its head; the advice in the rows is unchanged
    t = _shipped('survival')['surv-land-fish-cleaning']
    sec = next(s for s in t['sections'] if s['h'] == 'New York’s advice on eating fish you catch')
    blocks = sec['blocks']
    tables = [(n, b['table']) for n, b in enumerate(blocks) if 'table' in b]
    assert len(tables) >= 20, len(tables)
    assert tables[0][1]['head'] == ['Fish (statewide advice)', 'Most people', FISH_SENSITIVE]
    rows = []
    for n, tb in tables[1:]:
        assert tb['head'] == ['Fish', 'Most people', FISH_SENSITIVE], tb['head']
        assert 'p' in blocks[n - 1], 'each water is named in the line above its table'
        rows += tb['rows']
    assert len(rows) == 38 and all(len(r) == 3 for r in rows)
    caution = ['Every other fish', 'State advice: statewide table. This app’s caution: don’t eat', 'Don’t eat']
    assert rows.count(caution) == 2   # the app's more cautious cells stay as approved
    for x in _all_texts(t):
        assert 'Sensitive' not in x, x
    assert 'one-half pound (227 g)' in ' '.join(_texts(t))


def test_no_topic_carries_a_hard_coded_swipe_sentence():
    # whole-branch review I6: the app shows its own cue above a table that scrolls; a sentence in the content showed above tables that fit
    for tid, t in _shipped('survival').items():
        for x in _all_texts(t):
            assert 'swipe' not in x.lower(), (tid, x)


def test_warm_weather_meat_gets_one_answer_on_field_dressing_and_preserving_game_meat():
    # whole-branch review I3: the cooling limit comes first and belongs to Field dressing game; no keeping method extends it. Both pages
    # say so in the same words, labelled as the app's caution, and Preserving game meat quotes the owner's line and links it
    topics = _shipped('survival')
    fd, keep = topics['surv-field-dressing-game'], topics['surv-land-keeping-meat']
    cooling = next(s for s in fd['sections'] if s['h'] == 'Cooling the carcass')
    kinds = [next(iter(b)) for b in cooling['blocks']]
    noice = cooling['blocks'][2]['warn']
    assert cooling['blocks'][1]['warn'].startswith('How long you have.') and noice.startswith('No ice, snow or fridge')   # minor M3
    assert cooling['blocks'][3]['p'].startswith('Found later.') and kinds[4] == 'link'
    owner = 'This app’s caution: meat you can’t chill within 3 to 4 hours of the kill, cook within that time or don’t eat it.'
    assert owner in noice
    shared = ('and cook the meat to 165°F (74°C) before eating, as each method', 'such as smoke-drying and sun and air drying, are not '
              'agency-verified, for warm weather or any other.')
    assert 'This app’s caution: no way of keeping meat in Preserving game meat makes that time longer.' in noice
    labels = next(s for s in keep['sections'] if s['h'] == 'The two labels')
    joined = [b['p'] for b in labels['blocks'] if 'p' in b and 'makes that time longer' in b['p']]
    assert len(joined) == 1 and '“' + owner + '”' in joined[0]
    assert 'This app’s caution, the same as Field dressing game’s: no method on this page makes that time longer.' in joined[0]
    for part in shared:
        assert part in noice and part in joined[0], part
    assert 's:surv-field-dressing-game' in _links({'sections': [labels]})


def test_trapping_says_how_to_tell_the_traps_apart_and_how_to_set_them_before_where_to_set_them():
    # whole-branch review I2: a first-time trapper holding a borrowed trap is told which kind it is and how it is set, from the trapper
    # manuals; what no source opened gives (every body-gripping step, setting a cage trap) is the app's caution, never written from memory
    trap = _shipped('survival')['surv-land-trapping']
    heads = [s['h'] for s in trap['sections']]
    i = heads.index('Which trap you have, and setting it')
    assert heads[i - 1] == 'The kinds of trap' and heads[i + 1].startswith('Muskrat, beaver and raccoon')
    sec = trap['sections'][i]
    text = ' '.join(_texts({'sections': [sec]}))
    for kind in ('Foothold trap:', 'Body-gripping trap, also called a Conibear trap:', 'Cage or box trap:'):
        assert kind in text, kind
    steps = next(b['steps'] for b in sec['blocks'] if 'steps' in b)
    assert len(steps) == 5 and steps[0].startswith('Put the palm of each hand on one of the springs')
    assert 'Setting a coil-spring foothold trap, from the IAFWA trapper education manual, in its order.' in text
    for must in ('setting tongs', 'safety gripper', 'have someone who has set one show you how to set it and how to release it safely',
                 'This app’s caution: this page does not teach every step of setting a body-gripping trap, or how to set a cage trap.',
                 'Never set a body-gripping trap until someone who has set one has shown you how.'):
        assert must in text, must
    assert 's:surv-land-ny-rules' in _links({'sections': [sec]})
    assert any(s['name'].startswith('International Association of Fish and Wildlife Agencies, Trapper Education Manual') for s in trap['sources'])


def test_whole_branch_review_minor_fixes():
    topics = _shipped('survival')
    # M2: Wild plants' Do first says where the Poisoning link is, and it is there
    plants = topics['surv-food-and-wild-plants']
    assert 'It is the first link under “Before you eat any wild plant”, below.' in plants['doFirst'][0]
    before = next(s for s in plants['sections'] if s['h'] == 'Before you eat any wild plant')
    assert _links({'sections': [before]})[0] == 'p:poisoning'
    # M5: a v7.6 pin on "Traps and fishing" opens Fishing for food, whose first link block reaches Trapping
    first = topics['surv-traps-and-fishing']['sections'][0]
    assert {'link': 's:surv-land-trapping', 'label': 'Trapping'} in first['blocks']
    # M10: Butchering names its Massachusetts source in full once, as the source list does
    assert 'Massachusetts deer processing workshop, instructor notes, called “Massachusetts notes” below' in ' '.join(_texts(topics['surv-land-butchering']))
