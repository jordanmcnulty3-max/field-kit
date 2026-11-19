"""Task 5: Survival home, category lists, filters and homeItems providers."""
import glob
import json
import os
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
          's:surv-food-storage', 's:surv-food-when-short', 's:surv-food-clean-kitchen', 's:surv-food-babies-children', 's:surv-food-preserving']
RADIATION = ['s:surv-fallout-warning', 's:surv-fallout-where-to-shelter', 's:surv-fallout-how-long', 's:surv-fallout-shelter-living',
             's:surv-fallout-coming-inside', 's:surv-fallout-water-and-food', 's:surv-fallout-leaving', 's:surv-dirty-bomb',
             's:surv-potassium-iodide', 's:surv-fallout-get-ready']   # named, so a later pack appending to ALWAYS cannot shift it
FOOD = ['s:surv-food-power-out', 's:surv-food-still-good', 's:surv-food-cooking-no-power', 's:surv-food-poisoning', 's:surv-food-how-much',
        's:surv-food-storage', 's:surv-food-when-short', 's:surv-food-clean-kitchen', 's:surv-food-babies-children', 's:surv-food-preserving']
assert set(RADIATION) <= set(ALWAYS) and set(FOOD) <= set(ALWAYS)
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
    assert basics[0] == 's:surv-priorities' and len(basics) >= 10   # Basics keeps its remaining topics
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
def test_the_six_checked_topics_differ_from_v73_release_by_one_added_link_block(tid, target):
    now, was = _shipped('survival')[tid], _main_text(tid)
    extra = []
    now_sections = json.loads(json.dumps(now['sections']))
    assert len(now_sections) == len(was['sections']), tid
    if tid in SEVEN:   # the food pack (v7.5) adds its own one block to some of these topics: it is checked against v7.4, below
        for sn in now_sections:
            sn['blocks'] = [b for b in sn['blocks'] if b.get('link') != SEVEN[tid]]
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


SEVEN = {'surv-priorities': 's:surv-food-how-much', 'surv-stomach-illness-in-a-group': 's:surv-food-clean-kitchen',
         'surv-generators': 's:surv-food-power-out', 'surv-fallout-water-and-food': 's:surv-food-still-good',
         'surv-fallout-get-ready': 's:surv-food-how-much', 'surv-water-store': 's:surv-food-how-much',
         'surv-heat-out': 's:surv-food-power-out'}


def test_every_link_in_the_food_pages_and_the_seven_checked_topics_resolves_and_is_labelled_with_the_title():
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
    for tid, target in SEVEN.items():
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
                            'Get ready before it happens': ['s:surv-food-how-much', 'c:pantry'], 'Keep it cold longer': ['s:surv-food-preserving']},
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


@pytest.mark.parametrize('tid,target', sorted(SEVEN.items()))
def test_the_seven_checked_topics_differ_from_v74_release_by_one_added_link_block(tid, target):
    now, was = _shipped('survival')[tid], _v74_text(tid)
    extra = []
    now_sections = json.loads(json.dumps(now['sections']))
    assert len(now_sections) == len(was['sections']), tid
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


def test_the_food_pack_does_not_link_field_dressing_game_until_v76():
    # Its label puts the food pages above Wound cleaning and care for "dressing" (docs/v7.5-rulings.md); the link returns with v7.6
    for tid in [k[2:] for k in FOOD]:
        assert 's:surv-field-dressing-game' not in _links(_shipped('survival')[tid]), tid
