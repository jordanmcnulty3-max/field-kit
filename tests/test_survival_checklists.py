"""Task 8: Survival checklists: ticks, count, Clear ticks, backup and restore, pins, recents, search."""
import json
import re

import pytest
from playwright.sync_api import expect

from .conftest import inject_data
from .test_migration import backup, backup_file, pick, restore_now
from .test_survival_topic import XSS, settle, wait_hash

LIST = '#/survival/list/ten-essentials'
IDS = [f'item{i}' for i in range(1, 11)]
CL = {'id': 'ten-essentials', 'title': 'Ten essentials', 'category': 'basics', 'summary': 'Pack these.',
      'items': [{'id': i, 'text': f'Thing {n}', **({'note': f'Note {n}'} if n % 2 else {})} for n, i in enumerate(IDS, 1)],
      'sources': [{'name': 'Fixture source', 'used': 'everything'}], 'reviewed': '2026-11-10', 'draft': True}
FULL = 'Couldn’t save: phone storage for Field Kit is full. Back up, then delete old tracks or map areas.'


def boot(page, app_url, hash_=LIST, storage=None, checklists=(CL,)):
    page.set_default_timeout(4000)
    inject_data(page, topics=[], checklists=list(checklists), only=True)
    page.add_init_script('window.__len0 = history.length;')
    seed = {'advAck': True, **(storage or {})}
    page.add_init_script(
        "if (!sessionStorage.getItem('seeded')) { sessionStorage.setItem('seeded', '1');"
        + ''.join(f"localStorage.setItem('fk.{k}', {json.dumps(json.dumps(v))});" for k, v in seed.items()) + '}')
    page.goto(app_url + hash_)
    page.wait_for_function('window.FK && FK.tools && FK.survival')


def count(page):
    return page.inner_text('#survPage .sv-count')


def stored(page):
    raw = page.evaluate("localStorage.getItem('fk.checks')")
    return None if raw is None else json.loads(raw)


def box(page, n):
    return page.get_by_role('checkbox', name=f'Thing {n}', exact=True)


def tick(page, *ns):
    for n in ns:
        box(page, n).check()


def test_tick_two_saves_shows_count_and_survives_reload_on_page_and_home(page, app_url):
    boot(page, app_url)
    assert count(page) == '0/10'
    tick(page, 2, 5)
    assert count(page) == '2/10'
    assert stored(page) == {'ten-essentials': ['item2', 'item5']}
    page.reload()
    expect(box(page, 2)).to_be_checked()
    expect(box(page, 5)).to_be_checked()
    expect(box(page, 1)).not_to_be_checked()
    assert count(page) == '2/10'
    page.evaluate("FK.route.go('/survival')")
    wait_hash(page, '#/survival')
    assert page.locator('#survLists h2').inner_text() == 'Checklists'
    assert page.locator('#survLists button[data-key="c:ten-essentials"]').inner_text().replace('\n', ' ') == 'Ten essentials 2/10'


def test_unticking_removes_the_item_and_the_last_one_removes_the_entry(page, app_url):
    boot(page, app_url, storage={'checks': {'ten-essentials': ['item1', 'item2'], 'other-list': ['a']}})
    assert count(page) == '2/10'
    box(page, 1).uncheck()
    assert stored(page) == {'ten-essentials': ['item2'], 'other-list': ['a']}   # another list's ticks are left alone
    box(page, 2).uncheck()
    assert stored(page) == {'other-list': ['a']}
    assert count(page) == '0/10'


def test_home_badge_is_zero_of_n_before_any_tick(page, app_url):
    boot(page, app_url, '#/survival')
    assert page.locator('#survLists button[data-key="c:ten-essentials"]').inner_text().replace('\n', ' ') == 'Ten essentials 0/10'


def test_clear_ticks_needs_a_second_tap_then_empties(page, app_url):
    boot(page, app_url, storage={'checks': {'ten-essentials': ['item1', 'item2', 'item3']}})
    clear = page.locator('#survPage [data-act="clear-ticks"]')
    assert clear.inner_text() == 'Clear ticks'
    clear.click()
    assert clear.inner_text() == 'Confirm clear'
    assert count(page) == '3/10' and stored(page) == {'ten-essentials': ['item1', 'item2', 'item3']}
    clear.click()
    assert clear.inner_text() == 'Clear ticks'
    assert count(page) == '0/10'
    assert stored(page) in ({}, {'ten-essentials': []})
    for n in (1, 2, 3):
        expect(box(page, n)).not_to_be_checked()
    assert clear.bounding_box()['height'] >= 48


def test_clear_ticks_confirm_reverts_by_itself_and_ticking_cancels_it(page, app_url):
    boot(page, app_url, storage={'checks': {'ten-essentials': ['item1']}})
    page.evaluate('FK.tools.confirm.revertMs = 150')
    clear = page.locator('#survPage [data-act="clear-ticks"]')
    clear.click()
    assert clear.inner_text() == 'Confirm clear'
    page.wait_for_function("document.querySelector('#survPage [data-act=clear-ticks]').textContent === 'Clear ticks'")
    assert count(page) == '1/10'
    page.evaluate('FK.tools.confirm.revertMs = 5000')
    clear.click()
    tick(page, 4)
    assert clear.inner_text() == 'Clear ticks'   # a tick since the first tap: ask again
    assert count(page) == '2/10'


def test_clear_ticks_with_nothing_ticked_does_not_ask(page, app_url):
    boot(page, app_url)
    clear = page.locator('#survPage [data-act="clear-ticks"]')
    assert clear.get_attribute('aria-disabled') == 'true'
    clear.click(force=True)   # aria-disabled keeps it focusable, so a tap still lands
    assert clear.inner_text() == 'Clear ticks'


def test_ticks_for_item_ids_that_no_longer_exist_are_ignored(page, app_url):
    boot(page, app_url, storage={'checks': {'ten-essentials': ['item1', 'item1', 'gone', 7, None, 'item3']}})
    assert count(page) == '2/10'
    assert page.evaluate("FK.survival.ticks('ten-essentials')") == ['item1', 'item3']
    assert page.evaluate("FK.survival.ticks('no-such-list')") == []
    tick(page, 2)   # a write keeps only what is real
    assert stored(page) == {'ten-essentials': ['item1', 'item2', 'item3']}


@pytest.mark.parametrize('bad', ['x', [], 7, {'ten-essentials': 'oops'}, {'ten-essentials': {'item1': True}},
                                 {'ten-essentials': [1, {}, None]}, {'__proto__': ['item1']}])
def test_malformed_stored_ticks_give_zero_and_no_error(page, app_url, bad):
    boot(page, app_url, storage={'checks': bad})
    assert count(page) == '0/10'
    assert page.locator('#survPage input:checked').count() == 0
    assert page.evaluate("FK.survival.ticks('ten-essentials')") == []
    tick(page, 1)   # and a new tick replaces the junk
    assert stored(page) == {'ten-essentials': ['item1']}


def test_malformed_ticks_show_zero_on_home(page, app_url):
    boot(page, app_url, '#/survival', storage={'checks': {'ten-essentials': 'oops'}})
    assert page.locator('#survLists button').inner_text().replace('\n', ' ') == 'Ten essentials 0/10'


def test_storage_full_on_tick_shows_the_toast_and_leaves_the_box_unticked(page, app_url):
    boot(page, app_url)
    page.evaluate("""() => {
      const orig = Storage.prototype.setItem;
      Storage.prototype.setItem = function (k, v) { if (k === 'fk.checks') throw new DOMException('full', 'QuotaExceededError'); return orig.call(this, k, v); };
    }""")
    box(page, 3).click()
    assert page.inner_text('#toast') == FULL
    expect(box(page, 3)).not_to_be_checked()
    assert count(page) == '0/10'
    assert stored(page) is None


def test_storage_full_on_clear_keeps_the_ticks(page, app_url):
    boot(page, app_url, storage={'checks': {'ten-essentials': ['item1']}})
    page.evaluate("""() => {
      const orig = Storage.prototype.setItem;
      Storage.prototype.setItem = function (k, v) { if (k === 'fk.checks') throw new DOMException('full', 'QuotaExceededError'); return orig.call(this, k, v); };
    }""")
    clear = page.locator('#survPage [data-act="clear-ticks"]')
    clear.click()
    clear.click()
    assert page.inner_text('#toast') == FULL
    expect(box(page, 1)).to_be_checked()
    assert count(page) == '1/10'


# ---------- Backup and restore ----------

def test_backup_contains_checks_and_restore_brings_ticks_back(page, app_url, tmp_path):
    boot(page, app_url, storage={'checks': {'ten-essentials': ['item2', 'item4']}})
    b = backup(page, tmp_path)
    assert json.loads(b['data']['fk.checks']) == {'ten-essentials': ['item2', 'item4']}
    page.click('#menuClose')
    page.evaluate("localStorage.removeItem('fk.checks')")
    pick(page, tmp_path, b)
    restore_now(page)
    assert json.loads(page.evaluate("localStorage.getItem('fk.checks')")) == {'ten-essentials': ['item2', 'item4']}
    assert count(page) == '2/10'
    expect(box(page, 4)).to_be_checked()


def test_restoring_an_older_backup_with_no_checks_and_five_recents_works(page, app_url, tmp_path):
    boot(page, app_url, '#/survival', storage={'checks': {'ten-essentials': ['item1']}})
    recents = ['p:bleeding', 'p:burns', 's:surv-a', 'c:ten-essentials', 'p:choking']
    pick(page, tmp_path, backup_file({'fk.recent': json.dumps(recents), 'fk.night': 'false'}, version='6'))
    restore_now(page)
    assert page.evaluate("localStorage.getItem('fk.checks')") is None   # a backup without ticks means no ticks
    assert page.evaluate('FK.recent.all()') == recents
    assert page.locator('#survLists button').inner_text().replace('\n', ' ') == 'Ten essentials 0/10'
    assert page.locator('#survRecent button[data-key="c:ten-essentials"]').count() == 1
    settle(page)


def test_restoring_ticks_that_are_junk_shows_none(page, app_url, tmp_path):
    boot(page, app_url, '#/survival')
    for raw in ('"x"', '[]', '{"ten-essentials": "oops"}'):
        pick(page, tmp_path, backup_file({'fk.checks': raw}, version='6'))
        restore_now(page)
        assert page.locator('#survLists button').inner_text().replace('\n', ' ') == 'Ten essentials 0/10'


# ---------- Page structure, keyboard, pins, recents, links ----------

def test_items_are_real_checkboxes_with_labels_notes_and_48px_rows(page, app_url):
    boot(page, app_url)
    expect(page.locator('#survPage h2')).to_have_text('Ten essentials')
    assert page.locator('#survPage input[type="checkbox"]').count() == 10
    assert page.locator('#survPage .sv-draft').inner_text() == 'Draft'
    first = box(page, 1)
    assert first.get_attribute('aria-describedby')
    assert page.locator('#' + first.get_attribute('aria-describedby')).inner_text() == 'Note 1'
    assert page.locator('#survPage .sv-cnote').count() == 5   # only items with a note have one
    for lab in page.locator('#survPage label.sv-check').all():
        assert lab.bounding_box()['height'] >= 48
    box_ = first.bounding_box()
    page.mouse.click(300, box_['y'] + box_['height'] / 2)   # the far end of the row, not the box itself
    expect(first).to_be_checked()
    t = page.inner_text('#survPage')
    assert 'Fixture source' in t and 'Reviewed 2026-11-10' in t
    assert page.get_attribute('#survPage .sv-count', 'role') == 'status'


def test_keyboard_only_ticks_and_clears(page, app_url):
    boot(page, app_url)
    assert page.evaluate("document.activeElement.id") == 'svTitle'
    page.keyboard.press('Tab')   # the pin star
    assert page.evaluate("document.activeElement.dataset.act") == 'pin'
    page.keyboard.press('Tab')   # Clear ticks sits above the list
    assert page.evaluate("document.activeElement.dataset.act") == 'clear-ticks'
    page.keyboard.press('Tab')
    assert page.evaluate("document.activeElement.type") == 'checkbox'
    page.keyboard.press('Space')
    page.keyboard.press('Tab')
    page.keyboard.press('Tab')
    page.keyboard.press('Space')
    assert count(page) == '2/10' and stored(page) == {'ten-essentials': ['item1', 'item3']}
    clear = page.locator('#survPage [data-act="clear-ticks"]')
    clear.focus()
    page.keyboard.press('Enter')
    assert clear.inner_text() == 'Confirm clear'
    assert page.evaluate("document.activeElement.dataset.act") == 'clear-ticks'
    page.keyboard.press('Enter')
    assert count(page) == '0/10'
    assert page.evaluate("document.activeElement.dataset.act") == 'clear-ticks'   # focus stays on the button


def test_pin_star_pins_the_checklist_and_home_lists_it(page, app_url):
    boot(page, app_url)
    star = page.locator('#survPage .sv-head [data-act="pin"]')
    assert star.get_attribute('aria-pressed') == 'false'
    star.click()
    assert star.get_attribute('aria-pressed') == 'true'
    assert page.evaluate("FK.pins.all()") == ['c:ten-essentials']
    page.reload()
    assert page.get_attribute('#survPage .sv-head [data-act="pin"]', 'aria-pressed') == 'true'
    page.evaluate("FK.route.go('/survival')")
    wait_hash(page, '#/survival')
    assert page.locator('#survPinned button[data-key="c:ten-essentials"]').count() == 1
    page.click('#survPinned button[data-key="c:ten-essentials"]')
    wait_hash(page, LIST)
    page.click('#survPage .sv-head [data-act="pin"]')
    assert page.evaluate("FK.pins.all()") == []


def test_opening_records_recent_and_home_button_opens_the_page_and_back_returns(page, app_url):
    boot(page, app_url, '#/survival')
    assert page.evaluate('FK.recent.all()') == []
    n = page.evaluate('history.length')
    page.click('#survLists button[data-key="c:ten-essentials"]')
    wait_hash(page, LIST)
    assert page.evaluate('FK.recent.all()') == ['c:ten-essentials']
    assert page.evaluate('history.length') == n + 1
    page.go_back()
    wait_hash(page, '#/survival')
    expect(page.locator('#survHome')).to_be_visible()
    assert page.locator('#survRecent button[data-key="c:ten-essentials"]').count() == 1
    assert page.evaluate("document.activeElement.dataset.key") == 'c:ten-essentials'


def test_open_c_key_goes_to_the_list_and_unknown_ids_are_refused(page, app_url):
    boot(page, app_url, '#/survival')
    assert page.evaluate("FK.survival.open('c:nope')") is False
    assert page.evaluate("FK.survival.open('c:bad key')") is False
    assert page.evaluate("FK.survival.open('c:ten-essentials')") is True
    wait_hash(page, LIST)
    page.goto(app_url + '#/survival/list/nope')
    wait_hash(page, '#/survival')
    expect(page.locator('#survHome')).to_be_visible()
    assert page.evaluate('FK.recent.all()') == ['c:ten-essentials']


def test_api_checklists_checklist_and_malformed_data_skipped(page, app_url):
    bad = [{'id': 'nope'}, {'id': 'x', 'title': 'No items'}, {'id': 'y', 'title': 'Bad items', 'items': [{'id': 'a'}, {'text': 'b'}, 7, {'id': 'ok', 'text': 'Fine'}]}, None, 'z']
    boot(page, app_url, '#/survival', checklists=[CL, *bad])
    got = page.evaluate("FK.survival.checklists().map(c => [c.id, c.items.length])")
    assert got == [['ten-essentials', 10], ['y', 1]]
    assert page.evaluate("FK.survival.checklist('ten-essentials').title") == 'Ten essentials'
    assert page.evaluate("FK.survival.checklist('nope')") is None


def test_markup_in_title_items_notes_and_sources_is_text(page, app_url):
    evil = {**CL, 'title': 'T ' + XSS, 'items': [{'id': 'a', 'text': 'I ' + XSS, 'note': 'N ' + XSS}],
            'sources': [{'name': 'S ' + XSS, 'used': 'U ' + XSS}], 'reviewed': '2026-11-10'}
    boot(page, app_url, checklists=[evil])
    settle(page)
    assert page.evaluate('window.__xss') is None
    assert page.locator('#survPage img').count() == 0
    t = page.inner_text('#survPage')
    assert 'T ' + XSS in t and 'I ' + XSS in t and 'N ' + XSS in t and 'S ' + XSS in t
    page.click('#survPage input[type=checkbox]')
    assert page.evaluate("FK.survival.ticks('ten-essentials')") == ['a']


def test_search_finds_the_checklist_and_opens_it(page, app_url):
    boot(page, app_url, '#/survival')
    page.click('#searchBtn')
    page.fill('#searchInput', 'Thing 7')
    page.click('#searchBody .sr-item[data-key="c:ten-essentials"]')
    wait_hash(page, LIST)
    assert page.evaluate('FK.recent.all()') == ['c:ten-essentials']


def test_search_go_returns_what_survival_open_returns(page, app_url):
    boot(page, app_url, '#/survival')
    page.evaluate("""() => {
      window.__ret = false;
      FK.survival.tools = () => [{ name: 'sunmoon', label: 'Sun and moon' }];
      FK.survival.open = () => window.__ret;
    }""")
    for key in ('c:ten-essentials', 'u:sunmoon'):
        assert page.evaluate('k => FK.search.go(k)', key) is False, key
    page.evaluate("window.__ret = true")
    for key in ('c:ten-essentials', 'u:sunmoon'):
        assert page.evaluate('k => FK.search.go(k)', key) is True, key
    assert page.evaluate("FK.search.go('c:nope')") is False


# ---------- The shipped Ten essentials checklist ----------

def test_shipped_ten_essentials_matches_the_topic_and_is_a_draft_with_the_placeholder_source(page, app_url):
    page.goto(app_url + '#/survival')
    page.wait_for_function('window.FK && FK.survival')
    c = page.evaluate("FK_DATA.checklists.find(c => c.id === 'ten-essentials')")
    t = page.evaluate("FK_DATA.topics.find(t => t.id === 'surv-ten-essentials')")
    assert c['title'] == 'Ten essentials' and c['category'] == 'basics' and c['draft'] is True and c['reviewed'] == '2026-11-17'
    assert c['sources'] == [{'name': 'Not yet source-checked', 'used': 'Taken from the Ten essentials topic; checked in Task 16'}]
    lines = [x for s in t['sections'] for b in s['blocks'] for x in b.get('list', [])]
    assert len(lines) == 10 and len(c['items']) == 10
    norm = lambda s: re.sub(r'[^a-z0-9]+', ' ', s.lower()).strip()
    for it, line in zip(c['items'], lines):
        assert norm(it['text']) in norm(line) and norm(line).startswith(norm(it['text'])), (it, line)
        if 'note' in it:
            assert norm(it['note']) in norm(line), (it, line)
        assert it['text'].strip() and re.fullmatch(r'[a-z0-9-]+', it['id'])
    assert len({it['id'] for it in c['items']}) == 10
    links = [b for s in t['sections'] for b in s['blocks'] if 'link' in b]
    assert links == [{'link': 'c:ten-essentials', 'label': 'Ten essentials checklist'}]


def test_topic_link_opens_the_shipped_checklist(page, app_url):
    page.add_init_script("localStorage.setItem('fk.advAck', 'true')")
    page.goto(app_url + '#/survival/surv-ten-essentials')
    page.wait_for_function('window.FK && FK.survival')
    page.click('#survPage [data-link="c:ten-essentials"]')
    wait_hash(page, LIST)
    expect(page.locator('#survPage h2')).to_have_text('Ten essentials')
    assert page.locator('#survPage input[type=checkbox]').count() == 10
    assert page.locator('#survPage .sv-draft').inner_text() == 'Draft'
