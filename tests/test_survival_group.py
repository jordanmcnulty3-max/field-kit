"""Water pack Task 2: the saved group (people, days), checklists whose quantities scale with it, and the water planner
(#/survival/tool/water). Every case in the plan's Review Focus 1 to 3 is here; Review Focus 4 is in test_migration.py."""
import json
import math
import re
from decimal import Decimal, ROUND_CEILING

import pytest
from playwright.sync_api import expect

from .conftest import inject_data
from .test_survival_topic import XSS, settle, wait_hash

FULL = 'Couldn’t save: phone storage for Field Kit is full. Back up, then delete old tracks or map areas.'
WATER_URL = '#/survival/tool/water'
LIST_URL = '#/survival/list/store-water'
NOT_AVAILABLE = 'The water planner’s numbers are not available yet'

LPG = 3.785411784
LBG = 8.34
WATER = {
    'id': 'water', 'title': 'Water for drinking and cooking',
    'values': {
        'drinkPerPersonDay': {'value': 1, 'unit': 'gal', 'note': 'This covers drinking and cooking only. It does not cover washing or flushing.'},
        'planDays': {'value': 14, 'unit': 'days'},
        'extraHotPerPersonDay': {'value': 1, 'unit': 'gal', 'note': 'Hot weather'},
        'extraSickPerPersonDay': {'value': 0.1, 'unit': 'gal', 'note': 'Someone is sick'},
        'lbPerGallon': {'value': LBG, 'unit': 'lb'},
        'litersPerGallon': {'value': LPG, 'unit': 'L'},
        'notAnExtra': {'value': 9, 'unit': 'gal', 'note': 'Must not become a toggle'},
    },
    'sources': [{'name': 'Fixture agency', 'used': 'the per-person amount'}, {'name': 'Fixture standards body', 'used': 'weight and litres per gallon'}],
    'reviewed': '2026-11-18',
}
QCL = {'id': 'store-water', 'title': 'Store water', 'category': 'water', 'summary': 'For the whole group.',
       'items': [
           {'id': 'water', 'text': 'Drinking water', 'qty': {'amount': 1, 'unit': 'gal', 'per': 'personDay'}},
           {'id': 'tabs', 'text': 'Tablets', 'qty': {'amount': 0.3, 'unit': 'tablets', 'per': 'personDay'}},
           {'id': 'cups', 'text': 'Cups', 'note': 'One each', 'qty': {'amount': 1, 'unit': 'cups', 'per': 'person'}},
           {'id': 'funnel', 'text': 'Funnel'},
           {'id': 'junk', 'text': 'Junk quantity', 'qty': {'amount': -2, 'unit': 'gal', 'per': 'personDay'}},
           {'id': 'junk2', 'text': 'Junk per', 'qty': {'amount': 2, 'unit': 'gal', 'per': 'week'}},
       ],
       'sources': [{'name': 'Fixture source', 'used': 'everything'}], 'reviewed': '2026-11-18'}
PLAIN_CL = {'id': 'plain', 'title': 'Plain list', 'category': 'basics', 'items': [{'id': 'a', 'text': 'Thing A'}],
            'sources': [{'name': 'Fixture source', 'used': 'everything'}], 'reviewed': '2026-11-18'}


def boot(page, app_url, hash_=WATER_URL, storage=None, raw=None, water=WATER, checklists=(QCL, PLAIN_CL), topics=()):
    """water=None leaves no water data at all (a dummy entry replaces the shipped tool data)."""
    page.set_default_timeout(4000)
    inject_data(page, topics=list(topics), checklists=list(checklists),
                tooldata={'water': water} if water is not None else {'other': {'id': 'other'}}, only=True)
    seed = {'fk.advAck': 'true', **{'fk.' + k: json.dumps(v) for k, v in (storage or {}).items()}, **(raw or {})}
    page.add_init_script("if (!sessionStorage.getItem('seeded')) { sessionStorage.setItem('seeded', '1'); const d = %s;"
                         " for (const k in d) localStorage.setItem(k, d[k]); }" % json.dumps(seed))
    page.goto(app_url + hash_)
    page.wait_for_function('window.FK && FK.survival && FK.survival.group')


def group(page):
    return page.evaluate('FK.survival.group()')


def stored_group(page):
    raw = page.evaluate("localStorage.getItem('fk.group')")
    return None if raw is None else json.loads(raw)


def res(page, k):
    """A planner result: the number in front of its unit, as an int (thousands separators removed)."""
    t = page.locator(f'#survPage [data-k="{k}"]').inner_text()
    m = re.match(r'^([\d,]+)\s', t)
    assert m, (k, t)
    return int(m.group(1).replace(',', ''))


def qty(page, item):
    return page.locator(f'#survPage [data-qty="{item}"]').inner_text()


def ceil_dec(x):
    return int(Decimal(x).to_integral_value(rounding=ROUND_CEILING))


def expected(p, d, per):
    """Exact totals worked out with decimals: gallons, litres, pounds, jugs, 5-gallon containers, 55-gallon drums."""
    gal = ceil_dec(Decimal(p) * Decimal(d) * Decimal(str(per)))
    return {'gal': gal, 'litres': ceil_dec(Decimal(gal) * Decimal(str(LPG))), 'lb': ceil_dec(Decimal(gal) * Decimal(str(LBG))),
            'jugs': gal, 'fives': math.ceil(gal / 5), 'drums': math.ceil(gal / 55)}


def no_bad_numbers(page):
    t = page.inner_text('#survPage')
    assert 'NaN' not in t and 'Infinity' not in t and 'undefined' not in t, t
    assert not re.search(r'(^|[^\w])-\s?\d', t), t   # no negative number
    return t


def no_overflow(page):
    assert page.evaluate('document.documentElement.scrollWidth') <= 360
    over = page.evaluate("""[...document.querySelectorAll('#survPage *')].filter(el => {
        const r = el.getBoundingClientRect(); return r.width && (r.right > innerWidth + 0.5 || r.left < -0.5); }).map(el => el.outerHTML.slice(0, 80))""")
    assert over == []


def editor_input(page, name):
    return page.locator('#survPage .sv-group').get_by_label(name, exact=True)


def set_field(page, name, value):
    f = editor_input(page, name)
    f.fill(str(value))
    f.press('Enter')


# ---------- The group setting ----------

def test_default_group_is_one_person_and_the_datas_planning_days(page, app_url):
    boot(page, app_url, water={**WATER, 'values': {**WATER['values'], 'planDays': {'value': 10, 'unit': 'days'}}})
    assert group(page) == {'people': 1, 'days': 10}
    assert stored_group(page) is None   # reading never writes


def test_default_days_are_fourteen_with_no_or_draft_water_data(page, app_url):
    boot(page, app_url, water=None)
    assert group(page) == {'people': 1, 'days': 14}
    page.evaluate("FK_DATA.tooldata.water = { draft: true, values: { planDays: { value: 3, unit: 'days' } } }")
    assert group(page) == {'people': 1, 'days': 14}


# Review Focus 1: malformed or absurd stored groups.
@pytest.mark.parametrize('bad, want', [
    ('"x"', {'people': 1, 'days': 14}),
    ('{"people": 0}', {'people': 1, 'days': 14}),
    ('{"days": 0}', {'people': 1, 'days': 14}),             # below range: the default, not the minimum
    ('{"people": -3, "days": 30}', {'people': 1, 'days': 30}),
    ('{"people": 1e9, "days": -3}', {'people': 50, 'days': 14}),   # above range clamps; below range falls back
    ('{"people": 2.5, "days": 3.2}', {'people': 3, 'days': 4}),
    ('{"people": 1e999, "days": -1e999}', {'people': 1, 'days': 14}),   # JSON.parse gives Infinity
    ('{"people": "5", "days": true}', {'people': 1, 'days': 14}),
    ('[4, 7]', {'people': 1, 'days': 14}),
    ('null', {'people': 1, 'days': 14}),
    ('not json', {'people': 1, 'days': 14}),
    ('{"people": -0.5, "days": 400}', {'people': 1, 'days': 365}),
])
def test_review_focus_1_malformed_stored_group_falls_back_and_clamps_everywhere(page, app_url, bad, want):
    boot(page, app_url, raw={'fk.group': bad})
    assert group(page) == want
    assert editor_input(page, 'People').input_value() == str(want['people'])
    assert editor_input(page, 'Days').input_value() == str(want['days'])
    no_bad_numbers(page)
    per = 1
    e = expected(want['people'], want['days'], per)
    for k in ('gal', 'litres', 'lb', 'jugs', 'fives', 'drums'):
        assert res(page, k) == e[k], k
    page.evaluate(f"FK.route.go('/survival/list/store-water')")
    wait_hash(page, LIST_URL)
    no_bad_numbers(page)
    assert qty(page, 'water') == f"{want['people'] * want['days']:,} gal"
    assert qty(page, 'cups') == f"{want['people']:,} cups"


def test_set_group_clamps_stores_integers_and_emits_group_once_per_change(page, app_url):
    boot(page, app_url, '#/survival')
    page.evaluate("window.__g = []; FK.on('group', g => window.__g.push(g))")
    assert page.evaluate("FK.survival.setGroup({ people: 4, days: 30 })") is True
    assert stored_group(page) == {'people': 4, 'days': 30}
    assert page.evaluate("FK.survival.setGroup({ people: 4, days: 30 })") is True   # no change: no event
    assert page.evaluate("FK.survival.setGroup({ people: 999, days: 0 })") is True
    assert stored_group(page) == {'people': 50, 'days': 1}
    assert page.evaluate("FK.survival.setGroup({ people: 2.1, days: 6.5 })") is True
    assert stored_group(page) == {'people': 3, 'days': 7}
    assert page.evaluate("FK.survival.setGroup({ people: 'x' })") is True   # a missing or junk field keeps its value
    assert stored_group(page) == {'people': 3, 'days': 7}
    assert page.evaluate('window.__g') == [{'people': 4, 'days': 30}, {'people': 50, 'days': 1}, {'people': 3, 'days': 7}]


def test_group_persists_across_reload(page, app_url):
    boot(page, app_url)
    set_field(page, 'People', 6)
    set_field(page, 'Days', 21)
    assert stored_group(page) == {'people': 6, 'days': 21}
    page.reload()
    page.wait_for_function('window.FK && FK.survival && FK.survival.group')
    assert editor_input(page, 'People').input_value() == '6'
    assert editor_input(page, 'Days').input_value() == '21'
    assert res(page, 'gal') == 126


def test_storage_full_keeps_the_typed_group_for_the_page_and_shows_the_toast(page, app_url):
    boot(page, app_url, storage={'group': {'people': 2, 'days': 14}})
    page.evaluate("""() => {
      const orig = Storage.prototype.setItem;
      Storage.prototype.setItem = function (k, v) { if (k === 'fk.group') throw new DOMException('full', 'QuotaExceededError'); return orig.call(this, k, v); };
    }""")
    set_field(page, 'People', 5)
    expect(page.locator('#toast')).to_have_text(FULL)
    assert stored_group(page) == {'people': 2, 'days': 14}
    assert editor_input(page, 'People').input_value() == '5'
    assert group(page) == {'people': 5, 'days': 14}
    assert res(page, 'gal') == 70
    page.evaluate("FK.route.go('/survival/list/store-water')")   # the rest of this visit uses the typed group too
    wait_hash(page, LIST_URL)
    assert qty(page, 'water') == '70 gal'


# ---------- The group editor ----------

def test_editor_has_labelled_fields_48px_steppers_and_clamps_on_change(page, app_url):
    boot(page, app_url)
    ed = page.locator('#survPage .sv-group')
    expect(ed).to_have_count(1)
    people, days = editor_input(page, 'People'), editor_input(page, 'Days')
    assert people.get_attribute('min') == '1' and people.get_attribute('max') == '50'
    assert days.get_attribute('min') == '1' and days.get_attribute('max') == '365'
    for name in ('One fewer person', 'One more person', 'One fewer day', 'One more day'):
        b = ed.get_by_role('button', name=name, exact=True).bounding_box()
        assert b['width'] >= 48 and b['height'] >= 48, name
    for f in (people, days):
        assert f.bounding_box()['height'] >= 48
    set_field(page, 'People', 80)
    assert people.input_value() == '50' and group(page)['people'] == 50
    set_field(page, 'Days', 0)
    assert days.input_value() == '1' and group(page)['days'] == 1
    set_field(page, 'Days', '')   # blank goes back to the saved value
    assert days.input_value() == '1'
    ed.get_by_role('button', name='One more person', exact=True).click(force=True)   # at 50 already; aria-disabled keeps it focusable
    assert group(page)['people'] == 50
    assert ed.get_by_role('button', name='One more person', exact=True).get_attribute('aria-disabled') == 'true'
    ed.get_by_role('button', name='One fewer person', exact=True).click()
    assert group(page) == {'people': 49, 'days': 1} and people.input_value() == '49'


def test_live_total_announces_on_change_not_on_every_keystroke(page, app_url):
    boot(page, app_url, storage={'group': {'people': 2, 'days': 14}})
    live = page.locator('#survPage .sv-gsum')
    assert live.get_attribute('role') == 'status' or live.get_attribute('aria-live') == 'polite'
    before = live.inner_text()
    assert '28 gallons' in before
    f = editor_input(page, 'People')
    f.click()
    f.press('Control+a')
    f.type('12')   # one input event per key
    assert live.inner_text() == before
    f.press('Tab')   # change happens on leaving the field
    expect(live).to_contain_text('168 gallons')


def test_keyboard_only_sets_the_group_and_toggles_an_extra(page, app_url):
    boot(page, app_url)
    assert page.evaluate('document.activeElement.id') == 'svTitle'
    page.keyboard.press('Tab')   # pin
    assert page.evaluate('document.activeElement.dataset.act') == 'pin'
    page.keyboard.press('Tab')
    assert page.evaluate('document.activeElement.getAttribute("aria-label")') == 'One fewer person'
    page.keyboard.press('Tab')
    assert page.evaluate('document.activeElement.dataset.gfield') == 'people'
    page.keyboard.press('Control+a')
    page.keyboard.type('3')
    page.keyboard.press('Tab')
    assert page.evaluate('document.activeElement.getAttribute("aria-label")') == 'One more person'
    page.keyboard.press('Enter')
    page.keyboard.press('Space')
    assert group(page)['people'] == 5
    page.keyboard.press('Tab')
    page.keyboard.press('Tab')
    assert page.evaluate('document.activeElement.dataset.gfield') == 'days'
    page.keyboard.press('ArrowUp')   # the native spin button
    assert group(page)['days'] == 15
    page.keyboard.press('Tab')
    page.keyboard.press('Tab')
    assert page.evaluate('document.activeElement.dataset.extra') == 'extraHotPerPersonDay'
    page.keyboard.press('Space')
    assert res(page, 'gal') == 5 * 15 * 2


# ---------- Scaling checklists ----------

def test_checklist_rows_show_scaled_totals_after_the_text_and_junk_quantities_are_ignored(page, app_url):
    boot(page, app_url, LIST_URL, storage={'group': {'people': 3, 'days': 10}})
    assert qty(page, 'water') == '30 gal'
    assert qty(page, 'tabs') == '9 tablets'    # 0.3 x 30 is 8.999999999999998 in floating point: still 9, never 8
    assert qty(page, 'cups') == '3 cups'        # per person: days do not count
    for it in ('funnel', 'junk', 'junk2'):
        assert page.locator(f'#survPage [data-qty="{it}"]').count() == 0
    row = page.locator('#survPage label.sv-check').first
    assert row.inner_text().replace('\n', ' ').startswith('Drinking water')   # the total comes after the item text
    box = page.get_by_role('checkbox', name='Drinking water', exact=True)   # the quantity is a description, not part of the name
    desc = ' '.join(page.locator('#' + i).inner_text() for i in box.get_attribute('aria-describedby').split())
    assert 'For your group: 30 gal' in desc   # a lead keeps the total from running into the item text
    cups = page.get_by_role('checkbox', name='Cups', exact=True)
    desc = ' '.join(page.locator('#' + i).inner_text() for i in cups.get_attribute('aria-describedby').split())
    assert '3 cups' in desc and 'One each' in desc
    assert page.locator('#survPage .sv-group').count() == 1
    order = page.evaluate("[...document.querySelectorAll('#survPage .sv-group, #survPage .sv-checkbar, #survPage .sv-checks')].map(e => e.className)")
    assert order == ['sv-group', 'sv-checkbar', 'sv-checks']


def test_a_checklist_with_no_quantity_has_no_editor(page, app_url):
    boot(page, app_url, '#/survival/list/plain')
    expect(page.locator('#survPage h2')).to_have_text('Plain list')
    assert page.locator('#survPage .sv-group').count() == 0
    assert page.locator('#survPage [data-qty]').count() == 0


# Review Focus 3: group of 1 and 50 over 1 and 365 days.
@pytest.mark.parametrize('people, days', [(1, 1), (1, 365), (50, 1), (50, 365)])
def test_review_focus_3_quantities_readable_no_overflow_and_ticks_kept(page, app_url, people, days):
    boot(page, app_url, LIST_URL, storage={'checks': {'store-water': ['water', 'cups']}})
    page.get_by_role('checkbox', name='Tablets', exact=True).check()
    before = json.loads(page.evaluate("localStorage.getItem('fk.checks')"))
    assert page.evaluate(f'FK.survival.setGroup({{ people: {people}, days: {days} }})') is True
    n = people * days
    assert qty(page, 'water') == f'{n:,} gal'
    assert qty(page, 'tabs') == f'{ceil_dec(Decimal("0.3") * n):,} tablets'
    assert qty(page, 'cups') == f'{people:,} cups'
    if n >= 1000:
        assert ',' in qty(page, 'water')
    no_bad_numbers(page)
    no_overflow(page)
    assert json.loads(page.evaluate("localStorage.getItem('fk.checks')")) == before
    for name in ('Drinking water', 'Tablets', 'Cups'):
        expect(page.get_by_role('checkbox', name=name, exact=True)).to_be_checked()
    expect(page.get_by_role('checkbox', name='Funnel', exact=True)).not_to_be_checked()
    assert page.inner_text('#survPage .sv-count') == '3/6'


def test_checklist_editor_changes_the_group_and_the_rows_follow(page, app_url):
    boot(page, app_url, LIST_URL)
    set_field(page, 'People', 4)
    assert qty(page, 'water') == '56 gal' and qty(page, 'cups') == '4 cups'
    assert stored_group(page) == {'people': 4, 'days': 14}
    expect(page.locator('#survPage .sv-gsum')).to_have_text('Quantities for 4 people for 14 days')


def test_checklist_and_planner_update_live_on_the_group_event(page, app_url):
    boot(page, app_url, LIST_URL)
    focus_before = page.evaluate('document.activeElement.id')
    page.evaluate('FK.survival.setGroup({ people: 7, days: 3 })')
    assert qty(page, 'water') == '21 gal'
    assert editor_input(page, 'People').input_value() == '7'
    assert page.evaluate('document.activeElement.id') == focus_before   # rows are not redrawn
    page.evaluate("FK.route.go('/survival/tool/water')")
    wait_hash(page, WATER_URL)
    assert res(page, 'gal') == 21
    page.evaluate('FK.survival.setGroup({ people: 2, days: 2 })')
    assert res(page, 'gal') == 4
    assert editor_input(page, 'Days').input_value() == '2'


def test_leaving_a_page_stops_its_group_watcher(page, app_url):
    watchers = lambda: page.evaluate('FK.survival._groupWatchers()')
    boot(page, app_url, LIST_URL)
    assert watchers() == 1   # the checklist's editor
    page.evaluate("FK.route.go('/survival/tool/water')")
    wait_hash(page, WATER_URL)
    assert watchers() == 1   # the checklist's went with it; the planner's is the only one
    page.evaluate("FK.route.go('/survival')")
    wait_hash(page, '#/survival')
    assert watchers() == 0   # leaving the planner
    page.evaluate("FK.route.go('/survival/list/store-water')")
    wait_hash(page, LIST_URL)
    assert watchers() == 1
    page.go_back()
    wait_hash(page, '#/survival')
    assert watchers() == 0   # leaving a checklist
    page.evaluate("FK.route.go('/survival/list/plain')")   # no quantities: no editor, no watcher
    wait_hash(page, '#/survival/list/plain')
    assert watchers() == 0
    page.evaluate('FK.survival.setGroup({ people: 9, days: 9 })')
    settle(page)


# ---------- The water planner ----------

def test_planner_is_registered_searchable_pinnable_and_recorded(page, app_url):
    boot(page, app_url, '#/survival')
    assert ['water', 'Water planner'] in page.evaluate('FK.survival.tools().map(t => [t.name, t.label])')
    page.locator('#survTools button[data-key="u:water"]').click()
    wait_hash(page, WATER_URL)
    expect(page.locator('#survPage h2')).to_have_text('Water planner')
    assert page.evaluate('FK.recent.all()') == ['u:water']
    page.click('#survPage .sv-head [data-act="pin"]')
    assert page.evaluate("FK.pins.has('u:water')") is True
    page.evaluate("FK.route.go('/survival')")
    wait_hash(page, '#/survival')
    assert page.locator('#survPinned button[data-key="u:water"]').count() == 1
    page.click('#searchBtn')
    for words in ('how much water', 'gallons', 'water storage', 'litres'):
        page.fill('#searchInput', words)
        expect(page.locator('#searchBody .sr-item[data-key="u:water"]')).to_have_count(1)
    page.click('#searchBody .sr-item[data-key="u:water"]')
    wait_hash(page, WATER_URL)


def test_planner_shows_every_result_with_its_unit_basis_source_and_what_it_does_not_cover(page, app_url):
    boot(page, app_url, storage={'group': {'people': 4, 'days': 14}})
    t = no_bad_numbers(page)
    e = expected(4, 14, 1)
    assert e['gal'] == 56
    for k in e:
        assert res(page, k) == e[k], k
    assert page.locator('#survPage [data-k="gal"]').inner_text() == '56 gallons'
    assert page.locator('#survPage [data-k="litres"]').inner_text() == f"{e['litres']} litres"
    assert page.locator('#survPage [data-k="lb"]').inner_text() == f"{e['lb']} lb"
    assert page.locator('#survPage [data-k="jugs"]').inner_text() == '56 jugs'
    assert page.locator('#survPage [data-k="fives"]').inner_text() == '12 containers'
    assert page.locator('#survPage [data-k="drums"]').inner_text() == '2 drums'
    assert 'Water for drinking and cooking' in t
    assert '1 gal per person per day' in t
    assert page.locator('#survPage .wp-basis').inner_text() == ('Based on 1 gal per person per day, for 4 people for 14 days. '
                                                                'Source: Fixture agency, and 1 more under Sources.')
    assert 'This covers drinking and cooking only. It does not cover washing or flushing.' in t
    assert 'Reviewed 2026-11-18' in t
    out = page.locator('#survPage .wp-out')
    assert out.locator('.wp-basis').count() == 1   # under the result
    assert out.locator('.wp-note').all_inner_texts() == [WATER['title'], WATER['values']['drinkPerPersonDay']['note']]
    no_overflow(page)


def test_extras_are_toggles_labelled_by_their_note_not_stored(page, app_url):
    boot(page, app_url, storage={'group': {'people': 3, 'days': 10}})
    toggles = page.locator('#survPage input[data-extra]')
    assert toggles.count() == 2
    assert page.locator('#survPage [data-extra="notAnExtra"]').count() == 0
    hot = page.get_by_role('checkbox', name='Hot weather', exact=True)
    sick = page.get_by_role('checkbox', name='Someone is sick', exact=True)
    assert hot.bounding_box()['height'] >= 24
    assert page.locator('#survPage label:has(input[data-extra])').first.bounding_box()['height'] >= 48
    assert res(page, 'gal') == 30
    sick.check()
    assert res(page, 'gal') == 33   # 3 x 10 x 1.1 is 33.000000000000004 in floating point: 33, not 34
    hot.check()
    assert res(page, 'gal') == 63
    expect(page.locator('#survPage .sv-gsum')).to_contain_text('63 gallons')
    assert 'plus' in page.locator('#survPage .wp-basis').inner_text()
    keys = page.evaluate('Object.keys(localStorage)')
    assert not any('extra' in k.lower() for k in keys)
    page.reload()
    page.wait_for_function('window.FK && FK.survival && FK.survival.group')
    assert page.locator('#survPage input[data-extra]:checked').count() == 0
    assert res(page, 'gal') == 30


# Review Focus 2: totals never round down.
@pytest.mark.parametrize('people, days, extras', [
    (1, 1, ()), (3, 10, ('extraSickPerPersonDay',)), (7, 13, ('extraSickPerPersonDay',)),
    (11, 3, ('extraHotPerPersonDay', 'extraSickPerPersonDay')), (50, 365, ('extraHotPerPersonDay', 'extraSickPerPersonDay')),
    (49, 364, ('extraSickPerPersonDay',)),
])
def test_review_focus_2_planner_totals_round_up_and_never_understate(page, app_url, people, days, extras):
    boot(page, app_url, storage={'group': {'people': people, 'days': days}})
    for k in extras:
        page.locator(f'#survPage input[data-extra="{k}"]').check()
    per = Decimal(1) + sum((Decimal(str(WATER['values'][k]['value'])) for k in extras), Decimal(0))
    e = expected(people, days, per)
    for k in e:
        assert res(page, k) == e[k], k
    exact = Decimal(people) * Decimal(days) * per
    assert res(page, 'gal') >= exact
    assert res(page, 'litres') >= exact * Decimal(str(LPG))
    assert res(page, 'lb') >= exact * Decimal(str(LBG))
    assert res(page, 'fives') * 5 >= exact and res(page, 'drums') * 55 >= exact
    no_bad_numbers(page)
    t = page.locator('#survPage .wp-out').inner_text()
    if e['gal'] >= 1000:
        assert f"{e['gal']:,} gallons" in t
    no_overflow(page)


def test_review_focus_2_awkward_fractions_round_up(page, app_url):
    w = {**WATER, 'values': {**WATER['values'], 'drinkPerPersonDay': {'value': 0.7, 'unit': 'gal', 'note': 'n'},
                             'litersPerGallon': {'value': 3.785, 'unit': 'L'}, 'lbPerGallon': {'value': 8.3, 'unit': 'lb'}}}
    boot(page, app_url, water=w, storage={'group': {'people': 3, 'days': 1}})
    assert res(page, 'gal') == 3          # 2.1 -> 3
    assert res(page, 'litres') == 12      # 3 x 3.785 = 11.355 -> 12
    assert res(page, 'lb') == 25          # 3 x 8.3 = 24.9 -> 25
    page.evaluate('FK.survival.setGroup({ people: 10, days: 1 })')
    assert res(page, 'gal') == 7          # 0.7 x 10 is 7.000000000000001 in floating point: 7
    assert res(page, 'fives') == 2 and res(page, 'drums') == 1


@pytest.mark.parametrize('water', [None, {**WATER, 'draft': True},
                                   {**WATER, 'values': {'planDays': {'value': 14, 'unit': 'days'}}},
                                   {**WATER, 'values': {**WATER['values'], 'drinkPerPersonDay': {'value': 'lots', 'unit': 'gal'}}},
                                   {**WATER, 'values': {**WATER['values'], 'litersPerGallon': {'value': 0, 'unit': 'L'}}},
                                   {**WATER, 'values': {**WATER['values'], 'drinkPerPersonDay': {'value': 4, 'unit': 'L'}}},
                                   {**WATER, 'values': {**WATER['values'], 'lbPerGallon': {'value': 0.0833, 'unit': 'lb'}}},
                                   {**WATER, 'values': {**WATER['values'], 'litersPerGallon': {'value': 37.85, 'unit': 'L'}}},
                                   {**WATER, 'values': {**WATER['values'], 'lbPerGallon': {'value': 8.5, 'unit': 'lb'}}},
                                   {**WATER, 'values': {**WATER['values'], 'litersPerGallon': {'value': 3.77, 'unit': 'L'}}},
                                   'junk'])
def test_planner_says_numbers_are_not_available_when_data_is_missing_draft_or_broken(page, app_url, water):
    boot(page, app_url, water=water)
    t = no_bad_numbers(page)
    assert NOT_AVAILABLE in t
    assert page.locator('#survPage [data-k]').count() == 0
    assert page.locator('#survPage input[data-extra]').count() == 0
    assert 'gallons' not in t


def test_planner_markup_from_data_is_text(page, app_url):
    w = {**WATER, 'title': 'T ' + XSS, 'values': {**WATER['values'],
                                               'drinkPerPersonDay': {'value': 1, 'unit': 'gal', 'note': 'N ' + XSS},
                                               'extraHotPerPersonDay': {'value': 1, 'unit': 'gal', 'note': 'E ' + XSS}},
         'sources': [{'name': 'S ' + XSS, 'used': 'U ' + XSS}]}
    boot(page, app_url, water=w)
    settle(page)
    assert page.evaluate('window.__xss') is None
    assert page.locator('#survPage img').count() == 0
    t = page.inner_text('#survPage')
    for s in ('T ', 'N ', 'E ', 'S '):
        assert s + XSS in t


@pytest.mark.parametrize('night', [False, True])
def test_planner_and_scaling_checklist_fit_360px_in_day_and_night(page, app_url, night):
    boot(page, app_url, storage={'group': {'people': 50, 'days': 365}, 'night': night})
    assert (page.evaluate("document.documentElement.dataset.theme") == 'night') is night
    page.locator('#survPage input[data-extra="extraHotPerPersonDay"]').check()
    no_overflow(page)
    page.evaluate("FK.route.go('/survival/list/store-water')")
    wait_hash(page, LIST_URL)
    no_overflow(page)


def test_planner_totals_that_are_not_safe_integers_show_not_available(page, app_url):
    w = {**WATER, 'values': {**WATER['values'], 'drinkPerPersonDay': {'value': 1e306, 'unit': 'gal', 'note': 'n'}}}
    boot(page, app_url, water=w, storage={'group': {'people': 2, 'days': 3}})
    t = no_bad_numbers(page)
    assert NOT_AVAILABLE in t
    assert page.locator('#survPage [data-k]').count() == 0
    assert 'e+' not in t and 'gallons' not in t
    w2 = {**WATER, 'values': {**WATER['values'], 'drinkPerPersonDay': {'value': 1e12, 'unit': 'gal', 'note': 'n'}}}
    page2 = page.context.new_page()
    boot(page2, app_url, water=w2, storage={'group': {'people': 1, 'days': 1}})
    assert res(page2, 'gal') == 10 ** 12   # safe for 1 x 1 ...
    page2.evaluate('FK.survival.setGroup({ people: 50, days: 365 })')   # ... not for 50 x 365 (its litres pass 2^53)
    assert NOT_AVAILABLE in no_bad_numbers(page2)
    assert page2.locator('#survPage [data-k]').count() == 0
    page2.evaluate('FK.survival.setGroup({ people: 1, days: 1 })')
    assert res(page2, 'gal') == 10 ** 12
    page2.close()


def test_checklist_title_and_quantity_unit_markup_is_text(page, app_url):
    evil = {**QCL, 'title': 'T ' + XSS, 'items': [{'id': 'w', 'text': 'Water', 'qty': {'amount': 1, 'unit': 'U ' + XSS, 'per': 'personDay'}}]}
    boot(page, app_url, LIST_URL, checklists=[evil], storage={'group': {'people': 2, 'days': 3}})
    page.evaluate('FK.survival.setGroup({ people: 3, days: 3 })')   # the live update writes the unit too
    settle(page)
    assert page.evaluate('window.__xss') is None
    assert page.locator('#survPage img').count() == 0
    assert page.inner_text('#survPage h2') == 'T ' + XSS
    assert qty(page, 'w') == '9\u00a0U ' + XSS


def test_planner_on_the_shipped_water_data_gives_the_pack_figures(page, app_url):
    """Final review, Minor 2: the planner run on src/tooldata/water.json as shipped (no fixture), so a renamed value
    or changed unit there cannot ship a planner that says "not available" while --release passes."""
    page.add_init_script("localStorage.setItem('fk.advAck', 'true')")
    page.goto(app_url + WATER_URL)
    page.wait_for_function('window.FK && FK.survival && FK.survival.group')
    expect(page.locator('#survPage [data-k="gal"]')).to_be_visible()
    t = no_bad_numbers(page)
    assert NOT_AVAILABLE not in t
    assert group(page) == {'people': 1, 'days': 14}
    assert page.locator('#survPage [data-k="gal"]').inner_text() == '14 gallons'
    assert page.locator('#survPage [data-k="litres"]').inner_text() == '53 litres'
    assert page.locator('#survPage [data-k="lb"]').inner_text() == '117 lb'
    assert 'This does not cover flushing toilets, bathing or laundry: plan that water separately.' in t
    no_overflow(page)


# ---------- The Days field: only on a checklist with an item that is per person per day ----------

FALLOUT_URL = '#/survival/list/fallout-shelter-kit'
PERSON_CL = {'id': 'per-person', 'title': 'Per person only', 'category': 'basics', 'summary': 'One each.',
             'items': [{'id': 'cups', 'text': 'Cups', 'qty': {'amount': 2, 'unit': 'cups', 'per': 'person'}},
                       {'id': 'bags', 'text': 'Bags', 'qty': {'amount': 1, 'unit': 'bags', 'per': 'person'}},
                       {'id': 'plain', 'text': 'Plain'}],
             'sources': [{'name': 'Fixture source', 'used': 'everything'}], 'reviewed': '2026-11-18'}
BAD_QTY_CL = {'id': 'bad-qty', 'title': 'Bad quantities', 'category': 'basics', 'summary': 'Broken data.',
              'items': [{'id': 'cups', 'text': 'Cups', 'qty': {'amount': 2, 'unit': 'cups', 'per': 'person'}},
                        {'id': 'n1', 'text': 'Null qty', 'qty': None},
                        {'id': 'n2', 'text': 'String qty', 'qty': 'lots'},
                        {'id': 'n3', 'text': 'Array qty', 'qty': [1, 2]},
                        {'id': 'n4', 'text': 'Negative per day', 'qty': {'amount': -2, 'unit': 'gal', 'per': 'personDay'}},
                        {'id': 'n5', 'text': 'No unit', 'qty': {'amount': 2, 'per': 'personDay'}},
                        {'id': 'n6', 'text': 'Bad per', 'qty': {'amount': 2, 'unit': 'gal', 'per': 'week'}},
                        {'id': 'n7', 'text': 'Missing per', 'qty': {'amount': 2, 'unit': 'gal'}}],
              'sources': [{'name': 'Fixture source', 'used': 'everything'}], 'reviewed': '2026-11-18'}


def boot_shipped(page, app_url, hash_=FALLOUT_URL, storage=None):
    """The shipped checklists and data, with an optional saved group."""
    page.set_default_timeout(4000)
    seed = {'fk.advAck': 'true', **{'fk.' + k: json.dumps(v) for k, v in (storage or {}).items()}}
    page.add_init_script("if (!sessionStorage.getItem('seeded')) { sessionStorage.setItem('seeded', '1'); const d = %s;"
                         " for (const k in d) localStorage.setItem(k, d[k]); }" % json.dumps(seed))
    page.goto(app_url + hash_)
    page.wait_for_function('window.FK && FK.survival && FK.survival.group')
    page.wait_for_selector('#survPage .sv-page')


def status(page):
    return page.locator('#survPage .sv-gsum').inner_text()


def day_field(page):
    return page.locator('#survPage .sv-group').get_by_label('Days', exact=True)


def test_shipped_fallout_kit_shows_people_only_and_no_days_wording(page, app_url):
    boot_shipped(page, app_url, storage={'group': {'people': 4, 'days': 14}})
    expect(page.locator('#survPage .sv-group')).to_have_count(1)
    expect(day_field(page)).to_have_count(0)
    expect(page.locator('#survPage .sv-group [data-gfield="days"]')).to_have_count(0)
    assert status(page) == 'Quantities for 4 people'
    assert 'day' not in status(page).lower()
    assert 'Day' not in page.locator('#survPage .sv-group').inner_text()
    clothes, sleeping = qty(page, 'clothes'), qty(page, 'bedding')
    assert clothes and sleeping
    set_field(page, 'People', 7)
    assert status(page) == 'Quantities for 7 people'
    assert qty(page, 'clothes') != clothes and qty(page, 'bedding') != sleeping
    set_field(page, 'People', 1)
    assert status(page) == 'Quantities for 1 person'
    assert group(page)['days'] == 14   # untouched


def test_shipped_checklist_with_a_per_day_item_still_shows_days(page, app_url):
    boot_shipped(page, app_url, '#/survival/list/home-water-store', storage={'group': {'people': 4, 'days': 14}})
    expect(day_field(page)).to_have_count(1)
    assert status(page) == 'Quantities for 4 people for 14 days'
    ids = page.evaluate("[...document.querySelectorAll('#survPage [data-qty]')].map(x => x.dataset.qty)")
    assert ids
    before = {i: qty(page, i) for i in ids}
    set_field(page, 'Days', 3)
    assert status(page) == 'Quantities for 4 people for 3 days'
    assert {i: qty(page, i) for i in ids} != before


def test_days_value_survives_a_visit_to_a_checklist_without_days(page, app_url):
    boot(page, app_url, LIST_URL, checklists=(QCL, PERSON_CL))
    set_field(page, 'Days', 30)
    assert group(page)['days'] == 30
    page.evaluate("FK.route.go('/survival/list/per-person')")
    wait_hash(page, '#/survival/list/per-person')
    expect(day_field(page)).to_have_count(0)
    assert status(page) == 'Quantities for 1 person'
    assert group(page)['days'] == 30 and stored_group(page) in (None, {'people': 1, 'days': 30})
    set_field(page, 'People', 3)
    assert stored_group(page) == {'people': 3, 'days': 30}   # days kept when people is saved
    page.go_back()
    wait_hash(page, LIST_URL)
    assert day_field(page).input_value() == '30'
    assert status(page) == 'Quantities for 3 people for 30 days'


def test_fallout_kit_keyboard_order_and_48px_targets_are_unchanged_without_days(page, app_url):
    boot_shipped(page, app_url)
    ed = page.locator('#survPage .sv-group')
    for name in ('One fewer person', 'One more person'):
        b = ed.get_by_role('button', name=name, exact=True).bounding_box()
        assert b['width'] >= 48 and b['height'] >= 48, name
    assert editor_input(page, 'People').bounding_box()['height'] >= 48
    assert ed.get_by_role('button').count() == 2
    assert page.evaluate('document.activeElement.id') == 'svTitle'
    order = []
    for _ in range(4):
        page.keyboard.press('Tab')
        order.append(page.evaluate('document.activeElement.dataset.act || document.activeElement.getAttribute("aria-label") || document.activeElement.dataset.gfield'))
    assert order == ['pin', 'One fewer person', 'people', 'One more person']
    page.keyboard.press('Tab')   # past the group box, not into a Days control
    assert page.evaluate("document.activeElement.dataset.act") == 'clear-ticks'


@pytest.mark.parametrize('night', [False, True])
def test_fallout_kit_people_only_box_fits_360px_in_day_and_night(page, app_url, night):
    boot_shipped(page, app_url, storage={'group': {'people': 50, 'days': 365}, 'night': night})
    assert (page.evaluate("document.documentElement.dataset.theme") == 'night') is night
    assert status(page) == 'Quantities for 50 people'
    no_overflow(page)


def test_malformed_quantities_are_ignored_and_do_not_count_as_per_day(page, app_url):
    boot(page, app_url, '#/survival/list/bad-qty', checklists=(BAD_QTY_CL,))
    expect(day_field(page)).to_have_count(0)
    assert status(page) == 'Quantities for 1 person'
    assert page.locator('#survPage [data-qty]').count() == 1
    set_field(page, 'People', 2)
    assert qty(page, 'cups').replace('\xa0', ' ') == '4 cups'
    no_bad_numbers(page)


def test_a_checklist_with_no_scaled_items_still_has_no_group_box(page, app_url):
    boot(page, app_url, '#/survival/list/plain')
    expect(page.locator('#survPage .sv-page')).to_have_count(1)
    expect(page.locator('#survPage .sv-group')).to_have_count(0)
