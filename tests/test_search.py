import glob
import json
import os
import re

import pytest

from .conftest import inject_data, inject_protocols


def proto(pid, title, category='injury', keywords=None, summary=None, steps=None, tier=None, draft=False):
    p = {'id': pid, 'title': title, 'category': category, 'reviewed': '2026-11-16', 'sources': [{'name': 'Fixture'}],
         'steps': steps or [{'id': 's1', 'text': f'{title} first step'}, {'id': 's2', 'text': f'{title} second step'}]}
    if keywords:
        p['keywords'] = keywords
    if summary:
        p['summary'] = summary
    if tier:
        p['tier'] = tier
    if draft:
        p['draft'] = True
    return p


FIXTURES = [
    proto('choking', 'Choking', 'life', keywords=['heimlich', 'airway blocked']),
    proto('stings', 'Stings', 'bites', keywords=['bee', 'wasp']),
    proto('splint', 'Splinting', summary='Immobilise a broken bone before moving.'),
    proto('body-hit', 'Shock', 'life', steps=[{'id': 's1', 'text': 'Keep the casualty warm. Heimlich is not needed here.'}]),
    proto('cricothyrotomy', 'Surgical airway', 'advanced', tier='advanced', keywords=['cric']),
    proto('draftie', 'Draft protocol', draft=True),
    proto('long-detail', 'Wound care', steps=[{'id': 's1', 'text': 'Rinse the wound.',
          'detail': 'Use clean water and plenty of it. Never pack a <b>dirty</b> wound with cotton. Flush debris out gently before dressing.'}]),
]


def boot(page, app_url, fixtures=FIXTURES, storage=None, hash_='#/emergency', only=False):
    inject_protocols(page, fixtures, only)
    seed = {'advAck': False, **(storage or {})}
    page.add_init_script(
        "if (!sessionStorage.getItem('seeded')) { sessionStorage.setItem('seeded', '1');"
        + ''.join(f"localStorage.setItem('fk.{k}', {json.dumps(json.dumps(v))});" for k, v in seed.items()) + '}')
    page.goto(app_url + hash_)


def open_search(page):
    page.click('#searchBtn')
    page.wait_for_selector('#searchPane', state='visible')


def type_q(page, q):
    page.fill('#searchInput', q)


def keys(page):
    return page.eval_on_selector_all('#searchBody .sr-item', 'els => els.map(e => e.dataset.key)')


def q(page, text):
    return page.evaluate('t => FK.search.query(t)', text)


def test_every_protocol_found_by_title(page, app_url):
    boot(page, app_url)
    ids = page.evaluate('FK_DATA.protocols.map(p => [p.id, p.title])')
    assert len(ids) >= 8
    for pid, title in ids:
        assert 'p:' + pid in [r['key'] for r in q(page, title)], title


def test_every_protocol_found_by_first_keyword(page, app_url):
    boot(page, app_url)
    pairs = page.evaluate('FK_DATA.protocols.filter(p => p.keywords && p.keywords.length).map(p => [p.id, p.keywords[0]])')
    assert len(pairs) >= 3
    for pid, kw in pairs:
        assert 'p:' + pid in [r['key'] for r in q(page, kw)], kw


def test_title_match_ranks_above_body_match(page, app_url):
    boot(page, app_url, only=True)   # shipped data has its own Shock protocol
    ks = [r['key'] for r in q(page, 'heimlich')]
    assert ks[0] == 'p:choking'            # keyword match
    assert 'p:body-hit' in ks              # step-text match
    assert ks.index('p:choking') < ks.index('p:body-hit')
    ks = [r['key'] for r in q(page, 'shock')]
    assert ks[0] == 'p:body-hit'           # title


def test_matching_rules(page, app_url):
    boot(page, app_url)
    assert 'p:choking' in [r['key'] for r in q(page, 'CHOK')]          # prefix, case-insensitive
    assert 'p:choking' in [r['key'] for r in q(page, 'airway heim')]   # all words, any field
    assert q(page, 'heimlich zzzz') == []                              # every word must match
    assert 'p:splint' in [r['key'] for r in q(page, 'immobilise')]     # summary
    assert 'p:splint' in [r['key'] for r in q(page, 'immobilíse, BONE!')]   # diacritics and punctuation ignored
    assert q(page, '   ') == []
    assert 'p:stings' not in [r['key'] for r in q(page, 'synonym')]    # no built-in synonyms


def test_at_most_thirty_results(page, app_url):
    many = [proto(f'x{i}', f'Zebra {i}') for i in range(45)]
    boot(page, app_url, FIXTURES + many)
    assert len(q(page, 'zebra')) == 30


ORIGINAL_TOPIC_IDS = ['surv-dangerous-animals', 'surv-field-dressing-game', 'surv-find-water', 'surv-fire', 'surv-food-and-wild-plants', 'surv-knots',
                      'surv-make-water-safe', 'surv-navigation-without-a-compass', 'surv-river-crossings', 'surv-shelter', 'surv-signal-for-rescue',
                      'surv-ten-essentials', 'surv-traps-and-fishing', 'surv-weather-and-lightning']


def stopic(tid, title, category='basics', keywords=None, summary='', do_first=None, sections=None, **extra):
    t = {'id': tid, 'title': title, 'category': category, 'keywords': keywords or [], 'summary': summary,
         'sections': sections or [{'h': 'Overview', 'blocks': [{'p': f'{title} overview text.'}]}],
         'sources': [{'name': 'Fixture'}], 'reviewed': '2026-11-16'}
    if do_first:
        t['doFirst'] = do_first
    t.update(extra)
    return t


TOPICS = [
    stopic('surv-gizmo', 'Gizmo basics', sections=[
        {'h': 'Amounts', 'blocks': [{'p': 'Intro.'}, {'table': {'head': ['Item', 'Amount'], 'rows': [['Quokkaberry', '1 tsp'], ['Water', '1 l']]}}]},
        {'h': 'Cautions', 'blocks': [{'warn': 'Mind the narwhalrope.'}, {'list': ['Bullet A']}]}]),
    stopic('surv-kw', 'Plain title', keywords=['zorblax'], summary='Nothing here.'),
    stopic('surv-body', 'Other title', sections=[{'h': 'Text', 'blocks': [{'p': 'The zorblax appears only in the body.'}]}]),
    stopic('surv-first', 'First thing', do_first=['Boil the frobnicate water'], summary='A summary about glimmerwort.'),
    stopic('surv-heading', 'Heading holder', sections=[{'h': 'Wibblesprocket handling', 'blocks': [{'p': 'x'}]}]),
    stopic('surv-townonly', 'Townonly topic', where=['town'], when=['warm'], keywords=['urbanzibar']),
]


def sboot(page, app_url, topics=TOPICS, hash_='#/emergency', storage=None, only=True):
    inject_data(page, protocols=FIXTURES, topics=topics, only=only)
    page.add_init_script(
        "if (!sessionStorage.getItem('seeded')) { sessionStorage.setItem('seeded', '1');"
        + ''.join(f"localStorage.setItem('fk.{k}', {json.dumps(json.dumps(v))});" for k, v in {'advAck': False, **(storage or {})}.items()) + '}')
    page.goto(app_url + hash_)


def test_word_only_in_a_table_cell_finds_the_topic_with_a_snippet(page, app_url):
    sboot(page, app_url)
    r = [x for x in q(page, 'quokkaberry') if x['key'] == 's:surv-gizmo']
    assert r and r[0]['where'] == 'Survival'
    assert '<mark>Quokkaberry</mark>' in r[0]['snippet']
    r = [x for x in q(page, 'narwhalrope') if x['key'] == 's:surv-gizmo']   # a warning block counts too
    assert r and '<mark>narwhalrope</mark>' in r[0]['snippet']


def test_topic_keyword_outranks_body_text_and_summary_do_first_headings_are_found(page, app_url):
    sboot(page, app_url)
    ks = [r['key'] for r in q(page, 'zorblax')]
    assert ks[:2] == ['s:surv-kw', 's:surv-body']
    assert [r['key'] for r in q(page, 'frobnicate')] == ['s:surv-first']       # Do first
    assert [r['key'] for r in q(page, 'glimmerwort')] == ['s:surv-first']      # summary
    assert [r['key'] for r in q(page, 'wibblesprocket')] == ['s:surv-heading']  # section heading
    assert [r['key'] for r in q(page, 'gizmo')][0] == 's:surv-gizmo'            # title


def test_topic_weights_title_over_keywords_over_summary_over_body(page, app_url):
    topics = [stopic('t-body', 'Aaa', sections=[{'h': 'H', 'blocks': [{'p': 'plimsoll'}]}]),
              stopic('t-sum', 'Bbb', summary='plimsoll'),
              stopic('t-kw', 'Ccc', keywords=['plimsoll']),
              stopic('t-title', 'Plimsoll')]
    sboot(page, app_url, topics)
    assert [r['key'] for r in q(page, 'plimsoll')] == ['s:t-title', 's:t-kw', 's:t-sum', 's:t-body']


def test_survival_topic_result_opens_that_topic_and_back_returns_to_the_screen_before_search(page, app_url):
    sboot(page, app_url, hash_='#/survival')
    open_search(page)
    type_q(page, 'quokkaberry')
    assert keys(page)[0] == 's:surv-gizmo'
    page.click('#searchBody .sr-item')
    page.wait_for_function("location.hash === '#/survival/surv-gizmo'")
    assert page.locator('#survPage').is_visible() and page.locator('#searchPane').is_hidden()
    assert page.evaluate('FK.recent.all()')[0] == 's:surv-gizmo'
    page.go_back()   # the search entry was replaced: straight back to the Survival home
    page.wait_for_function("location.hash === '#/survival'")
    assert page.locator('#survHome').is_visible() and page.locator('#searchPane').is_hidden()


def test_search_results_ignore_the_survival_home_filter(page, app_url):
    sboot(page, app_url, hash_='#/survival', storage={'survFilter': {'where': 'woods', 'when': 'cold'}})
    ks = [r['key'] for r in q(page, 'urbanzibar')]
    assert ks == ['s:surv-townonly']
    open_search(page)
    type_q(page, 'urbanzibar')
    page.click('#searchBody .sr-item')
    page.wait_for_function("location.hash === '#/survival/surv-townonly'")
    assert page.locator('#survPage').inner_text().startswith('Townonly topic')


def test_survival_ids_stable_in_the_shipped_data(page, app_url):
    page.goto(app_url + '#/survival')
    page.wait_for_function('window.FK && FK.search')
    ids = page.evaluate('FK_DATA.topics.map(t => t.id)')
    assert set(ORIGINAL_TOPIC_IDS) <= set(ids) and len(ORIGINAL_TOPIC_IDS) == 14 and len(set(ids)) == len(ids)
    for tid in ORIGINAL_TOPIC_IDS:   # every original topic is searchable by its title and opens through its old key
        assert 's:' + tid in [r['key'] for r in page.evaluate('t => FK.search.query(t)', page.evaluate('id => FK.survival.topic(id).title', tid))], tid
        assert page.evaluate('k => FK.search.describe(k)', 's:' + tid)['where'] == 'Survival'


def test_checklists_and_survival_tools_are_indexed_when_they_exist(page, app_url):
    sboot(page, app_url)
    page.evaluate("""() => {
      FK.survival.checklists = () => [{ id: 'cl-bag', title: 'Go bag', items: [{ text: 'Pack headlamp spares' }, { text: 'Water filter' }] }, { id: 'cl-bad' }, null];
      FK.survival.tools = () => [{ name: 'sunmoon', label: 'Sun and moon' }, { name: 'bad' }];
    }""")
    r = {x['key']: x for x in q(page, 'go bag')}
    assert r['c:cl-bag']['where'] == 'Checklist' and r['c:cl-bag']['title'] == 'Go bag'
    r = {x['key']: x for x in q(page, 'headlamp')}
    assert r['c:cl-bag']['snippet'].count('<mark>headlamp</mark>') == 1
    r = {x['key']: x for x in q(page, 'sun moon')}
    assert r['u:sunmoon']['where'] == 'Tool' and r['u:sunmoon']['title'] == 'Sun and moon'
    assert not any(k in {'c:cl-bad', 'u:bad'} for k in [x['key'] for x in q(page, 'bad')])
    assert page.evaluate("FK.search.describe('c:cl-bag')") == {'key': 'c:cl-bag', 'title': 'Go bag', 'where': 'Checklist', 'draft': False}
    assert page.evaluate("FK.search.describe('u:sunmoon')")['where'] == 'Tool'
    assert page.evaluate("FK.search.describe('c:nope')") is None and page.evaluate("FK.search.describe('u:nope')") is None
    # results are grouped with their kind as the heading
    open_search(page)
    type_q(page, 'go bag')
    assert page.eval_on_selector_all('#searchBody .sr-h', 'e => e.map(x => x.textContent)')[0] == 'Checklist'


def test_checklist_result_goes_through_survival_open(page, app_url):
    sboot(page, app_url, hash_='#/survival')
    page.evaluate("""() => {
      window.__opened = [];
      FK.survival.checklists = () => [{ id: 'cl-bag', title: 'Go bag', items: [{ text: 'Water filter' }] }];
      FK.survival.tools = () => [{ name: 'sunmoon', label: 'Sun and moon' }];
      FK.survival.open = (key, opts) => { window.__opened.push([key, opts && opts.replace === true]); return true; };
    }""")
    open_search(page)
    type_q(page, 'go bag')
    page.click('#searchBody .sr-item[data-key="c:cl-bag"]')
    page.evaluate("FK.route.go('/search')")
    type_q(page, 'sun moon')
    page.click('#searchBody .sr-item[data-key="u:sunmoon"]')
    assert page.evaluate('window.__opened') == [['c:cl-bag', True], ['u:sunmoon', True]]


def test_app_screen_result_opens_ballistics(page, app_url):
    boot(page, app_url)
    open_search(page)
    type_q(page, 'ballistics')
    assert keys(page)[0] == 'a:ballistics'
    page.click('#searchBody .sr-item')
    assert page.locator('#view-ballistics').is_visible()
    assert page.url.endswith('#/tactical/ballistics')


def test_saved_areas_settings_and_waypoints_screens(page, app_url):
    boot(page, app_url, hash_='#/tactical/ballistics')
    open_search(page)
    type_q(page, 'saved areas')
    page.click('#searchBody .sr-item[data-key="a:areas"]')
    page.wait_for_selector('#dlgSave[open]')
    assert page.locator('#view-map').is_visible()
    page.click('#saveClose')
    open_search(page)
    type_q(page, 'backup')
    page.click('#searchBody .sr-item[data-key="a:settings"]')
    assert page.locator('#dlgMenu').is_visible()
    page.click('#menuClose')
    open_search(page)
    type_q(page, 'waypoints')
    page.click('#searchBody .sr-item[data-key="a:waypoints"]')
    assert page.locator('#view-position').is_visible()
    top = page.eval_on_selector('#blkWaypoints', 'e => e.getBoundingClientRect().top')
    assert 0 <= top < 600   # in view (the page may be too short to scroll it to the very top)


def test_tool_and_report_results(page, app_url):
    boot(page, app_url)
    open_search(page)
    type_q(page, 'medevac')
    assert keys(page)[0] == 'r:9line'
    page.click('#searchBody .sr-item')
    assert page.locator('#toolPane').is_visible()
    assert page.url.endswith('#/emergency/report/9line')
    page.go_back()   # straight back to the Emergency home, no search entry in between
    page.wait_for_url('**/index.html#/emergency')
    page.evaluate("FK.route.go('/search')")
    type_q(page, 'tourniquet timers')
    assert keys(page)[0] == 't:tq'
    labels = page.eval_on_selector_all('#searchBody .sr-h', 'e => e.map(x => x.textContent)')
    assert labels[0] == 'Tool'


def test_empty_query_shows_pinned_and_recent(page, app_url):
    sboot(page, app_url, storage={'pins': ['p:splint', 't:tq', 'p:gone-away'], 'recent': ['a:ballistics', 's:surv-gizmo', 'p:choking']})
    open_search(page)
    heads = page.eval_on_selector_all('#searchBody .sr-h', 'e => e.map(x => x.textContent)')
    assert heads == ['Pinned', 'Recent']
    assert keys(page) == ['p:splint', 't:tq', 'a:ballistics', 's:surv-gizmo', 'p:choking']
    page.fill('#searchInput', 'x')
    page.fill('#searchInput', '')
    assert keys(page)[0] == 'p:splint'


def test_selecting_adds_to_recent_and_home_renders_survival_and_screen_keys(page, app_url):
    sboot(page, app_url)
    open_search(page)
    type_q(page, 'quokkaberry')
    page.click('#searchBody .sr-item')
    page.wait_for_function("location.hash === '#/survival/surv-gizmo'")
    page.evaluate("FK.route.go('/emergency')")
    assert page.evaluate('FK.recent.all()')[0] == 's:surv-gizmo'
    open_search(page)
    type_q(page, 'compass')
    page.click('#searchBody .sr-item[data-key="a:position"]')
    page.evaluate("FK.route.go('/emergency')")
    recent = page.locator('#emRecent .em-btn')
    texts = recent.all_inner_texts()
    assert 'Position and compass' in texts and any('Gizmo basics' in t for t in texts)
    recent.filter(has_text='Position and compass').click()
    assert page.locator('#view-position').is_visible()


def test_pinned_and_recent_survival_buttons_on_the_emergency_home_open_the_topic(page, app_url):
    sboot(page, app_url, storage={'pins': ['s:surv-gizmo'], 'recent': ['s:surv-kw']})
    page.wait_for_selector('#emPinned .em-btn')
    page.click('#emPinned [data-key="s:surv-gizmo"]')
    page.wait_for_function("location.hash === '#/survival/surv-gizmo'")
    assert page.locator('#survPage').is_visible()
    page.evaluate("FK.route.go('/emergency')")
    page.click('#emRecent [data-key="s:surv-kw"]')
    page.wait_for_function("location.hash === '#/survival/surv-kw'")
    assert page.locator('#survPage').inner_text().startswith('Plain title')


def test_clear_in_the_search_screen_empties_recent_on_both_homes(page, app_url):
    sboot(page, app_url, storage={'pins': ['p:splint'], 'recent': ['s:surv-gizmo', 'p:choking']})
    open_search(page)
    assert page.locator('#searchBody [data-act="clear-recent"]').count() == 1
    assert page.locator('#searchBody [data-act="clear-recent"]').bounding_box()['height'] >= 44
    page.click('#searchBody [data-act="clear-recent"]')
    assert page.evaluate('FK.recent.all()') == []
    heads = page.eval_on_selector_all('#searchBody .sr-h', 'e => e.map(x => x.textContent)')
    assert heads == ['Pinned'] and page.locator('#searchBody [data-act="clear-recent"]').count() == 0
    page.keyboard.press('Escape')
    page.wait_for_selector('#searchPane', state='hidden')
    assert page.locator('#emRecent .em-btn').count() == 0
    page.evaluate("FK.route.go('/survival')")
    assert page.locator('#survRecent .em-btn').count() == 0


def test_back_closes_search(page, app_url):
    boot(page, app_url)
    open_search(page)
    assert page.url.endswith('#/search')
    page.go_back()
    page.wait_for_url('**/index.html#/emergency')
    page.wait_for_selector('#searchPane', state='hidden')
    assert page.locator('#tab-emergency').is_visible()
    assert page.evaluate('document.activeElement.id') == 'searchBtn'


def test_close_button_and_escape(page, app_url):
    boot(page, app_url)
    open_search(page)
    page.click('#searchClose')
    page.wait_for_selector('#searchPane', state='hidden')
    page.wait_for_url('**/index.html#/emergency')
    open_search(page)
    page.keyboard.press('Escape')
    page.wait_for_selector('#searchPane', state='hidden')
    assert page.evaluate('document.activeElement.id') == 'searchBtn'


def test_result_replaces_search_entry_so_back_returns_to_previous_screen(page, app_url):
    boot(page, app_url, hash_='#/survival')
    open_search(page)
    type_q(page, 'choking')
    page.click('#searchBody .sr-item')
    assert page.locator('#player').is_visible()
    page.go_back()
    assert page.locator('#tab-survival').is_visible()
    assert not page.locator('#player').is_visible()
    assert not page.locator('#searchPane').is_visible()


def test_search_over_open_protocol_and_back_returns_to_it(page, app_url):
    boot(page, app_url, storage={'advAck': True})
    page.evaluate("FK.protocol.open('choking')")
    assert page.locator('#player').is_visible()
    url = page.url
    page.evaluate("FK.route.go('/search')")
    page.wait_for_selector('#searchPane', state='visible')
    assert page.locator('#searchInput').evaluate('e => document.activeElement === e')
    page.go_back()
    page.wait_for_url(url)
    page.wait_for_selector('#searchPane', state='hidden')
    assert page.locator('#player').is_visible()
    # open another protocol from search, then leave it: back where the first one was
    page.evaluate("FK.route.go('/search')")
    type_q(page, 'stings')
    page.click('#searchBody .sr-item')
    assert page.url.endswith('/emergency/stings')
    page.go_back()
    page.wait_for_url(url)


def test_search_over_open_tool(page, app_url):
    boot(page, app_url)
    page.evaluate("FK.tools.start('tq')")
    page.evaluate("FK.route.go('/search')")
    page.wait_for_selector('#searchPane', state='visible')
    page.keyboard.press('Escape')
    page.wait_for_selector('#searchPane', state='hidden')
    page.wait_for_url('**#/emergency/tool/tq')
    assert page.locator('#toolPane').is_visible()


def test_advanced_result_labelled_and_goes_through_acknowledgement(page, app_url):
    boot(page, app_url)
    open_search(page)
    type_q(page, 'cric')
    assert page.eval_on_selector_all('#searchBody .sr-h', 'e => e.map(x => x.textContent)')[0] == 'Advanced'
    assert keys(page)[0] == 'p:cricothyrotomy'
    page.click('#searchBody .sr-item')
    assert page.locator('#player [data-act="ack"]').is_visible()


def test_draft_tag(page, app_url):
    boot(page, app_url)
    open_search(page)
    type_q(page, 'draft protocol')
    assert 'Draft' in page.locator('#searchBody .sr-item').first.inner_text()


def test_snippet_marks_match_and_escapes(page, app_url):
    boot(page, app_url)
    r = [x for x in q(page, 'dirty') if x['key'] == 'p:long-detail'][0]
    assert '<mark>dirty</mark>' in r['snippet'] and '<b>' not in r['snippet'] and '&lt;b&gt;' in r['snippet']
    import re
    assert len(re.sub(r'<[^>]+>|&lt;|&gt;|…', 'x', r['snippet'])) <= 100
    r = [x for x in q(page, 'choking') if x['key'] == 'p:choking'][0]
    assert r['snippet'] == ''   # title match: nothing to explain


def test_no_matches_echoes_query_escaped(page, app_url):
    boot(page, app_url)
    open_search(page)
    type_q(page, '<img src=x onerror=alert(1)>')
    body = page.locator('#searchBody')
    assert 'No matches' in body.inner_text()
    assert body.locator('img').count() == 0
    assert '<img' in body.inner_text()


def test_input_attributes_clear_button_and_target_size(page, app_url):
    boot(page, app_url)
    open_search(page)
    i = page.locator('#searchInput')
    assert i.get_attribute('type') == 'search' and i.get_attribute('enterkeyhint') == 'search' and i.get_attribute('autocomplete') == 'off'
    assert i.evaluate('e => document.activeElement === e')
    assert page.locator('#searchClear').is_hidden()
    type_q(page, 'chok')
    assert page.locator('#searchClear').is_visible()
    page.click('#searchClear')
    assert i.input_value() == '' and i.evaluate('e => document.activeElement === e')
    type_q(page, 'e')
    heights = page.eval_on_selector_all('#searchBody .sr-item', 'els => els.map(e => e.getBoundingClientRect().height)')
    assert heights and min(heights) >= 56


def test_keyboard_arrows_and_enter(page, app_url):
    boot(page, app_url)
    open_search(page)
    type_q(page, 'ballistics')
    page.keyboard.press('ArrowDown')
    assert page.evaluate('document.activeElement.dataset.key') == 'a:ballistics'
    page.keyboard.press('ArrowUp')
    assert page.evaluate('document.activeElement.id') == 'searchInput'
    page.keyboard.press('Enter')   # Enter in the box opens the best result
    assert page.locator('#view-ballistics').is_visible()


def test_magnifier_visible_on_every_tab_and_in_map_mode(page, app_url):
    boot(page, app_url, hash_='#/tactical/map')
    assert page.evaluate("document.body.classList.contains('mapmode')")
    for h in ['#/tactical/map', '#/tactical/position', '#/survival', '#/emergency']:
        page.evaluate(f"FK.route.go('{h[1:]}')")
        assert page.locator('#searchBtn').is_visible(), h
        box = page.eval_on_selector('#searchBtn', 'e => e.getBoundingClientRect().width')
        assert box >= 44
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    open_search(page)
    assert page.locator('#searchPane').is_visible()


def test_reload_on_search_address_lands_on_tab(page, app_url):
    boot(page, app_url, hash_='#/search')
    assert not page.locator('#searchPane').is_visible()
    assert page.locator('.tab:visible').count() == 1
    assert '#/search' not in page.url


def test_router_parses_search(page, app_url):
    boot(page, app_url)
    r = page.evaluate("FK.route.parse('#/search')")
    assert r['search'] is True and r['tab'] == 'emergency'


def test_first_open_is_fast_with_sixty_protocols(page, app_url):
    many = [proto(f'p{i}', f'Protocol number {i}', steps=[{'id': f's{j}', 'text': f'Step {j} of protocol {i}, with some words to index.',
                                                          'detail': 'Detail text that runs a little longer than the step text itself does.'} for j in range(1, 9)]) for i in range(60)]
    boot(page, app_url, many)
    ms = page.evaluate("(() => { const t = performance.now(); FK.search.query('protocol'); return performance.now() - t; })()")
    assert ms < 50, ms
    ms = page.evaluate("(() => { const t = performance.now(); FK.search.query('protocol 7'); return performance.now() - t; })()")
    assert ms < 10, ms


def test_first_query_on_real_shipped_data_is_fast(page, app_url):
    """Guards the index cost against content growth: every protocol, topic and checklist that ships is indexed by the first query."""
    page.goto(app_url + '#/emergency')   # no fixtures: whatever ships
    page.wait_for_function('window.FK && FK.search')
    ms = page.evaluate("(() => { const t = performance.now(); FK.search.query('protocol'); return performance.now() - t; })()")
    assert ms < 50, ms


def test_real_shipped_data_found_by_title_and_first_keyword(page, app_url):
    page.goto(app_url + '#/emergency')   # no fixtures: whatever protocols ship
    page.wait_for_function('window.FK && FK.search')
    bad = page.evaluate("""FK_DATA.protocols.flatMap(p => {
      const out = [];
      if (!FK.search.query(p.title).some(r => r.key === 'p:' + p.id)) out.push(p.id + ' by title');
      if (p.keywords && p.keywords.length && !FK.search.query(p.keywords[0]).some(r => r.key === 'p:' + p.id)) out.push(p.id + ' by keyword');
      return out; })""")
    assert page.evaluate('FK_DATA.protocols.length') >= 1
    assert bad == []


def test_search_button_inside_protocol_returns_to_the_step(page, app_url):
    boot(page, app_url, storage={'advAck': True})
    page.evaluate("FK.protocol.open('choking')")
    page.wait_for_selector('#player [data-act="search"]')
    assert page.locator('#player [data-act="search"]').bounding_box()['height'] >= 56
    url = page.url
    page.click('#player [data-act="search"]')
    page.wait_for_selector('#searchPane', state='visible')
    assert page.url.endswith('#/search')
    page.keyboard.press('Escape')
    page.wait_for_selector('#searchPane', state='hidden')
    page.wait_for_url(url)
    assert page.locator('#player').is_visible()
    assert page.evaluate("document.activeElement.dataset.act") == 'search'   # focus returns to that button
    page.click('#player [data-act="search"]')
    type_q(page, 'stings')
    page.click('#searchBody .sr-item')
    assert page.url.endswith('/emergency/stings')
    page.go_back()
    page.wait_for_url(url)
    assert page.locator('#player').is_visible()


def test_search_button_inside_tool_and_cpr_keeps_running(page, app_url):
    boot(page, app_url)
    page.evaluate("FK.tools.start('cpr')")
    page.wait_for_selector('#cprBtn')
    page.click('#cprBtn')
    page.wait_for_function('FK.tools.cpr.running()')
    assert page.locator('#toolSearch').bounding_box()['height'] >= 56
    url = page.url
    page.click('#toolSearch')
    page.wait_for_selector('#searchPane', state='visible')
    page.keyboard.press('Escape')
    page.wait_for_selector('#searchPane', state='hidden')
    page.wait_for_url(url)
    assert page.locator('#toolPane').is_visible()
    assert page.evaluate("document.activeElement.id") == 'toolSearch'
    page.click('#toolSearch')
    type_q(page, 'ballistics')
    page.click('#searchBody .sr-item')
    assert page.locator('#view-ballistics').is_visible()
    assert page.evaluate('FK.tools.cpr.running()') is True
    page.evaluate('FK.tools.start("cpr")')   # leave the coach running; the page closes at teardown


def test_toast_is_above_search_pane(page, app_url):
    boot(page, app_url)
    z = page.evaluate("[getComputedStyle(document.getElementById('toast')).zIndex, getComputedStyle(document.getElementById('searchPane')).zIndex].map(Number)")
    assert z[0] > z[1]


def test_settings_from_search_over_a_protocol_opens_settings_and_leaving_still_works(page, app_url):
    """Behaviour, not mechanism: Settings opens over the step, and the protocol is left in one tap afterwards."""
    boot(page, app_url, storage={'advAck': True})
    page.evaluate("FK.protocol.open('choking')")
    page.wait_for_selector('#player:not([hidden])')
    page.evaluate("FK.route.go('/search')")
    type_q(page, 'backup')
    page.click('#searchBody .sr-item[data-key="a:settings"]')
    page.wait_for_selector('#dlgMenu[open]')
    assert page.url.endswith('/emergency/choking') and page.locator('#searchPane').is_hidden()
    page.click('#menuClose')
    page.click('#player [data-act="home"]')
    page.wait_for_function("location.hash === '#/emergency'")
    assert page.locator('#player').is_hidden()


def test_protocol_notes_are_indexed_like_the_summary(page, app_url):
    noted = {**proto('noted', 'Noted thing'), 'notes': ['Rule of palms zanzibarite']}
    summed = proto('summed', 'Summed thing', summary='zanzibarite in the summary')
    body = proto('bodied', 'Bodied thing', steps=[{'id': 's1', 'text': 'zanzibarite in a step'}])
    boot(page, app_url, FIXTURES + [body, noted, summed])
    ks = [r['key'] for r in q(page, 'zanzibarite')]
    assert set(ks) == {'p:noted', 'p:summed', 'p:bodied'}
    assert ks.index('p:noted') < ks.index('p:bodied') and ks.index('p:summed') < ks.index('p:bodied')


def test_update_banner_does_not_cover_search_and_returns_when_search_closes(page, app_url):
    boot(page, app_url)
    page.evaluate('FK.updateAvailable()')
    assert page.locator('#updBar').is_visible()
    open_search(page)
    type_q(page, 'bleeding')
    page.wait_for_selector('#searchBody .sr-item')
    bar = page.locator('#updBar')
    assert bar.is_hidden()
    page.click('#searchClose')
    page.wait_for_selector('#searchPane', state='hidden')
    assert bar.is_visible()
    assert page.locator('#updReload').is_enabled()


WATER_PACK_SEARCHES = [
    ('water purification', 's:surv-make-water-safe'),
    ('outhouse', 's:surv-latrines'),
    ('bathroom', 's:surv-toilet-no-water'),
    ('bleach', 's:surv-make-water-safe'),
    ('bleach', 's:surv-clean-and-disinfect'),
    ('boil', 's:surv-make-water-safe'),
    ('frozen pipes', 's:surv-water-winter'),
    ('wash hands', 's:surv-handwashing'),
    ('diarrhea', 'p:vomiting-diarrhea'),
    ('diarrhea', 's:surv-stomach-illness-in-a-group'),
]


@pytest.mark.parametrize('text,expected', WATER_PACK_SEARCHES)
def test_water_pack_hurried_searches_find_their_topic_in_the_shipped_data(page, app_url, text, expected):
    page.goto(app_url + '#/survival')
    page.wait_for_function('window.FK && FK.search')
    open_search(page)
    type_q(page, text)
    page.wait_for_selector('#searchBody .sr-item')
    assert expected in keys(page), f'{text!r} did not list {expected}: {keys(page)}'


@pytest.mark.parametrize('text', ['CO', 'co'])
def test_co_puts_the_carbon_monoxide_protocol_then_topic_first_in_the_shipped_data(page, app_url, text):
    # "CO" is what the alarm and the packaging say. Both pages carry "co" as a whole keyword; at equal
    # score the index order puts Emergency protocols before Survival topics.
    page.goto(app_url + '#/survival')
    page.wait_for_function('window.FK && FK.search')
    assert [r['key'] for r in q(page, text)][:2] == ['p:carbon-monoxide', 's:surv-carbon-monoxide']


def test_short_whole_keyword_bonus_needs_a_whole_keyword_and_a_short_word(page, app_url):
    # A one- or two-letter query that is a whole keyword beats a title that merely starts with it;
    # a prefix of a keyword, or a longer whole keyword, gets no such bonus.
    fx = [proto('zq-title', 'Zqualm thing'), proto('zq-kw', 'Other thing', keywords=['zq alarm']),
          proto('zqx-title', 'Zqxlong thing'), proto('zqx-kw', 'Another thing', keywords=['zqx'])]
    boot(page, app_url, FIXTURES + fx)
    assert [r['key'] for r in q(page, 'zq')][:2] == ['p:zq-kw', 'p:zq-title']
    assert [r['key'] for r in q(page, 'ZQX')][:2] == ['p:zqx-title', 'p:zqx-kw']   # three letters: title prefix still first
    assert [r['key'] for r in q(page, 'z')][:1] == ['p:zq-title']                 # "z" is no whole keyword anywhere


@pytest.mark.parametrize('text,first', [('od', 'p:overdose'), ('no', 'p:cpr-adult'), ('mr', 's:surv-portable-heaters')])
def test_other_short_shipped_queries_keep_their_first_result(page, app_url, text, first):
    page.goto(app_url + '#/survival')
    page.wait_for_function('window.FK && FK.search')
    assert [r['key'] for r in q(page, text)][0] == first


HEAT_PACK_SEARCHES = [
    ('frost bite', 's:surv-wind-chill'),
    ('snowed in', 's:surv-winter-storms'),
    ('lost power', 's:surv-heat-out'),
    ('no electricity', 's:surv-heat-out'),
]


@pytest.mark.parametrize('text,expected', HEAT_PACK_SEARCHES)
def test_heat_pack_hurried_searches_find_their_topic_in_the_first_three(page, app_url, text, expected):
    page.goto(app_url + '#/survival')
    page.wait_for_function('window.FK && FK.search')
    ks = [r['key'] for r in q(page, text)]
    assert expected in ks[:3], f'{text!r} did not list {expected} in the first three: {ks[:5]}'


@pytest.mark.parametrize('text,first', [
    ('in shock', ['p:shock']),
    ('hit by car', ['p:head-injury', 'p:lightning']),
    ('no pulse', ['p:cpr-adult', 'p:shock', 'p:cpr-child', 'p:cpr-infant']),   # order as in v7.2 and before the short-word bonus
    ('no', ['p:cpr-adult', 'p:cpr-child', 'p:cpr-infant']),
])
def test_little_words_in_a_search_get_no_short_keyword_bonus(page, app_url, text, first):
    # "in", "by", "no" are whole words inside unrelated pages' keyword phrases; they must not reorder what a frightened person types
    page.goto(app_url + '#/survival')
    page.wait_for_function('window.FK && FK.search')
    assert [r['key'] for r in q(page, text)][:len(first)] == first


# ---------- Radiation pack (Task 8, Review Focus 5) ----------

RADIATION_SEARCHES = ['fallout', 'nuke', 'nuclear', 'radiation', 'dirty bomb', 'KI', 'iodine', 'decon']
RADIATION_KEYS = {'s:surv-fallout-warning', 's:surv-fallout-where-to-shelter', 's:surv-fallout-how-long', 's:surv-fallout-shelter-living',
                  's:surv-fallout-coming-inside', 's:surv-fallout-water-and-food', 's:surv-fallout-leaving', 's:surv-dirty-bomb',
                  's:surv-potassium-iodide', 's:surv-fallout-get-ready', 'p:radiation-decontamination', 'p:radiation-sickness'}


@pytest.mark.parametrize('text', RADIATION_SEARCHES)
def test_radiation_hurried_searches_find_a_radiation_page_in_the_first_three(page, app_url, text):
    page.goto(app_url + '#/survival')
    page.wait_for_function('window.FK && FK.search')
    ks = [r['key'] for r in q(page, text)]
    assert RADIATION_KEYS & set(ks[:3]), f'{text!r} found no radiation topic or protocol in the first three: {ks[:5]}'


# The full v7.3 result lists on main (built from main, in order). The radiation pages may join a list
# but must not reorder or displace any v7.3 result, so the v7.3 keys in today's list keep their order.
V73_RESULTS = {
    'CO': ['p:carbon-monoxide', 's:surv-carbon-monoxide', 'p:head-injury', 'p:tourniquet-conversion', 't:cpr', 't:rate', 's:surv-dress-for-cold',
           's:surv-navigation-without-a-compass', 's:surv-wind-chill', 'a:position', 'p:animal-bite', 'p:cpr-adult', 'p:cpr-child', 'p:cpr-infant',
           'p:drowning', 'p:fainting', 'p:fracture', 'p:frostbite', 'p:heat-illness', 'p:hemostatic-packing', 'p:hypothermia',
           'p:needle-decompression', 'p:pelvic-binder', 'p:poisoning', 'p:seizure', 'p:shock', 'p:snakebite', 'p:spine-injury',
           'p:sprain-dislocation', 's:surv-fire'],
    'bleach': ['p:poisoning', 's:surv-clean-and-disinfect', 's:surv-make-water-safe', 's:surv-water-store', 's:surv-toilet-no-water',
               'p:poison-plants', 'p:vomiting-diarrhea', 's:surv-find-water', 's:surv-garbage-and-greywater', 's:surv-stomach-illness-in-a-group',
               's:surv-water-winter', 's:surv-wells-without-power', 'c:home-water-store', 'c:sanitation-kit'],
    'burn': ['t:burn', 'p:burns', 's:surv-carbon-monoxide', 'p:poison-plants', 's:surv-garbage-and-greywater', 's:surv-wood-stoves-fireplaces',
             's:surv-firewood', 's:surv-portable-heaters', 's:surv-sleep-warm', 's:surv-store-fuel', 'p:blisters', 'p:carbon-monoxide',
             'p:cricothyrotomy', 'p:hypothermia', 'p:lightning', 'p:march', 'p:poisoning', 'p:spider-scorpion', 'p:wound-care', 's:surv-fire',
             's:surv-generators', 's:surv-heat-out', 's:surv-latrines', 's:surv-make-water-safe', 's:surv-priorities', 's:surv-shelter',
             's:surv-unheated-house', 's:surv-water-in-the-house', 's:surv-water-winter', 's:surv-winter-storms'],
}


FOOD_KEYS = {'s:surv-food-power-out', 's:surv-food-still-good', 's:surv-food-cooking-no-power', 's:surv-food-poisoning', 's:surv-food-how-much',
             's:surv-food-storage', 's:surv-food-when-short', 's:surv-food-clean-kitchen', 's:surv-food-babies-children',
             's:surv-food-preserving', 'c:pantry'}


@pytest.mark.parametrize('text', sorted(V73_RESULTS))
def test_v73_results_for_co_bleach_and_burn_keep_their_order_with_the_radiation_and_food_pages_added(page, app_url, text):
    page.goto(app_url + '#/survival')
    page.wait_for_function('window.FK && FK.search')
    ks = [r['key'] for r in q(page, text)]
    old = V73_RESULTS[text]
    assert ks[:3] == old[:3], f'{text!r}: top three changed: {ks[:3]} (v7.3: {old[:3]})'   # radiation pages only below position 3
    kept = [k for k in ks if k in old]
    assert kept == old[:len(kept)], f'{text!r}: v7.3 results reordered: {kept}'
    assert [k for k in ks if k not in old and k not in RADIATION_KEYS and k not in FOOD_KEYS] == []   # nothing but radiation and food pages joins the list (the 30-result cap may push a v7.3 tail result out)


# ---------- Final review I1 and I2: tie order, measured on screen ----------
# The first three results as the search overlay shows them (grouped by kind, groups in order of their best result) in the
# real v7.3 release (1cded2e), recorded from a v7.3 build at 360x640 by typing each query into the overlay on #/survival.
# The radiation pack must not change them.
V73_ON_SCREEN = {
    'CO': ['p:carbon-monoxide', 'p:head-injury', 'p:animal-bite'],
    'bleach': ['p:poisoning', 'p:poison-plants', 'p:vomiting-diarrhea'],
    'burn': ['t:burn', 'p:burns', 'p:poison-plants'],
    'bleeding': ['p:bleeding', 'p:abdominal-wound', 'p:amputation'],
    'cpr': ['p:cpr-adult', 'p:cpr-child', 'p:cpr-infant'],
    'choking': ['p:choking', 'p:choking-infant', 'p:anaphylaxis'],
    'shock': ['p:shock', 'p:burns', 'p:abdominal-wound'],
    'in shock': ['p:shock', 'p:abdominal-wound', 'p:amputation'],
    'frostbite': ['p:frostbite', 'p:wound-care', 's:surv-priorities'],
    'frost bite': ['s:surv-wind-chill', 's:surv-priorities', 'p:wound-care'],
    'hypothermia': ['p:hypothermia', 'p:frostbite', 'p:march'],
    'water': ['s:surv-find-water', 's:surv-garbage-and-greywater', 's:surv-handwashing'],
    'generator': ['s:surv-generators', 's:surv-carbon-monoxide', 's:surv-wells-without-power'],
    'tourniquet': ['p:tourniquet-conversion', 'p:junctional-bleeding', 'p:hemostatic-packing'],
    'seizure': ['p:seizure', 'p:recovery-position', 'p:carbon-monoxide'],
    'overdose': ['p:overdose', 'p:cpr-adult', 'p:poisoning'],
    'poison': ['p:poison-plants', 'p:carbon-monoxide', 'p:poisoning'],
    'snake': ['p:snakebite', 's:surv-dangerous-animals'],
    'heat': ['p:heat-illness', 'p:carbon-monoxide', 'p:hypothermia'],
    'no': ['p:cpr-adult', 'p:cpr-child', 'p:cpr-infant'],
    'food': ['s:surv-food-and-wild-plants', 's:surv-stomach-illness-in-a-group', 's:surv-unheated-house'],
    'shelter': ['s:surv-shelter', 's:surv-heat-out', 's:surv-priorities'],
    # re-review R1: words from the hub's text whose v7.3 lists a hub indexed first of all had taken over
    'mushroom': ['p:poisoning', 'p:vomiting-diarrhea', 's:surv-food-and-wild-plants'],
    'blast': ['p:amputation', 'p:march', 'p:eye-injury'],
    'serious': ['p:shock', 'p:bleeding', 'p:burns'],
    'lie': ['p:fainting', 'p:shock', 'p:altitude'],
    'emergency': ['p:low-blood-sugar', 'p:seizure', 'p:abdominal-wound'],
    'wall': ['p:chest-wound', 'p:march', 'p:wound-care'],
    'now': ['p:animal-bite', 'p:head-injury', 'p:overdose'],
}


def on_screen(page, text):
    type_q(page, text)
    page.wait_for_selector('#searchBody .sr-item')
    return keys(page)


# Two queries where a radiation page outscores a v7.3 result (a title or keyword match against a weaker match), so no tie order can
# restore v7.3. Accepted by controller ruling (v7.4 rulings F2): a page titled for fallout is a fair result for these words, and the
# general topic stays first. Today's first three on screen, so any further change is caught.
V73_ON_SCREEN_OUTSCORED = {
    'food': ['s:surv-food-and-wild-plants', 's:surv-fallout-water-and-food', 's:surv-stomach-illness-in-a-group'],   # title word (5.5) over keyword (4)
    'shelter': ['s:surv-shelter', 's:surv-fallout-where-to-shelter', 's:surv-fallout-warning'],   # title word (5.5) and keyword (4) over body (3)
}


@pytest.mark.parametrize('text', sorted(V73_ON_SCREEN))
def test_v73_first_three_on_screen_are_unchanged(page, app_url, text):
    page.goto(app_url + '#/survival')
    page.wait_for_function('window.FK && FK.search')
    open_search(page)
    now = on_screen(page, text)[:3]
    if text in V75_ACCEPTED:   # changed again by the food pack: pinned in V75_ACCEPTED, below
        assert now == V75_ACCEPTED[text], f'{text!r}: {now}'
    elif text in V73_ON_SCREEN_OUTSCORED:
        assert now == V73_ON_SCREEN_OUTSCORED[text], f'{text!r}: {now}'
        assert now != V73_ON_SCREEN[text]   # if v7.3 comes back, move the query out of the outscored list
    else:
        assert now == V73_ON_SCREEN[text], f'{text!r}: first three on screen {now} (v7.3: {V73_ON_SCREEN[text]})'


@pytest.mark.parametrize('text', ['fallout', 'nuclear'])
def test_fallout_and_nuclear_show_the_fallout_warning_hub_in_the_first_three_on_screen(page, app_url, text):
    # The hub is indexed after every v7.3 page and after the two pack protocols (re-review R1), so it wins no tie with an older page.
    page.goto(app_url + '#/survival')
    page.wait_for_function('window.FK && FK.search')
    open_search(page)
    ks = on_screen(page, text)
    assert 's:surv-fallout-warning' in ks[:3], f'{text!r}: {ks[:5]}'


def test_fall_keeps_head_injury_in_the_first_three_on_screen(page, app_url):
    # re-review R3: "fall" is a prefix of the title word "Fallout"; with the pack protocols indexed before the hub,
    # Radiation decontamination takes first place and Head injury (v7.3's first) stays second.
    page.goto(app_url + '#/survival')
    page.wait_for_function('window.FK && FK.search')
    open_search(page)
    ks = on_screen(page, 'fall')
    assert ks[:3] == ['p:radiation-decontamination', 'p:head-injury', 'p:march'], ks[:5]


# ---------- Food pack (v7.5 Task 8): the on-screen first three against the v7.4 release ----------
# First three results as the overlay shows them (grouped by kind), recorded from a build of the v7.4 release (4375170) at 360x640 by
# typing each query into the overlay on #/survival: the queries pinned above, the words people type in a kitchen emergency, and the
# words the batch reviewers named. The food pack must not change them, except the lists in the four dicts below (docs/v7.5-rulings.md,
# "Search results that changed, accepted" and its lists below it), each pinned as it now stands.
V74_ON_SCREEN = {
    'CO': ['p:carbon-monoxide', 'p:head-injury', 'p:animal-bite'],
    'bleach': ['p:poisoning', 'p:poison-plants', 'p:vomiting-diarrhea'],
    'burn': ['t:burn', 'p:burns', 'p:poison-plants'],
    'bleeding': ['p:bleeding', 'p:abdominal-wound', 'p:amputation'],
    'cpr': ['p:cpr-adult', 'p:cpr-child', 'p:cpr-infant'],
    'choking': ['p:choking', 'p:choking-infant', 'p:anaphylaxis'],
    'shock': ['p:shock', 'p:burns', 'p:abdominal-wound'],
    'in shock': ['p:shock', 'p:abdominal-wound', 'p:amputation'],
    'frostbite': ['p:frostbite', 'p:wound-care', 's:surv-priorities'],
    'frost bite': ['s:surv-wind-chill', 's:surv-priorities', 'p:wound-care'],
    'hypothermia': ['p:hypothermia', 'p:frostbite', 'p:march'],
    'water': ['s:surv-find-water', 's:surv-garbage-and-greywater', 's:surv-handwashing'],
    'generator': ['s:surv-generators', 's:surv-carbon-monoxide', 's:surv-wells-without-power'],
    'tourniquet': ['p:tourniquet-conversion', 'p:junctional-bleeding', 'p:hemostatic-packing'],
    'seizure': ['p:seizure', 'p:recovery-position', 'p:carbon-monoxide'],
    'overdose': ['p:overdose', 'p:cpr-adult', 'p:poisoning'],
    'poison': ['p:poison-plants', 'p:carbon-monoxide', 'p:poisoning'],
    'snake': ['p:snakebite', 's:surv-dangerous-animals'],
    'heat': ['p:heat-illness', 'p:carbon-monoxide', 'p:hypothermia'],
    'no': ['p:cpr-adult', 'p:cpr-child', 'p:cpr-infant'],
    'food': ['s:surv-food-and-wild-plants', 's:surv-fallout-water-and-food', 's:surv-stomach-illness-in-a-group'],
    'shelter': ['s:surv-shelter', 's:surv-fallout-where-to-shelter', 's:surv-fallout-warning'],
    'mushroom': ['p:poisoning', 'p:vomiting-diarrhea', 's:surv-food-and-wild-plants'],
    'blast': ['p:amputation', 'p:march', 'p:eye-injury'],
    'serious': ['p:shock', 'p:bleeding', 'p:burns'],
    'lie': ['p:fainting', 'p:shock', 'p:altitude'],
    'emergency': ['p:low-blood-sugar', 'p:seizure', 'p:abdominal-wound'],
    'wall': ['p:chest-wound', 'p:march', 'p:wound-care'],
    'now': ['p:animal-bite', 'p:head-injury', 'p:overdose'],
    'cook': ['s:surv-fire', 's:surv-field-dressing-game', 's:surv-wells-without-power'],
    'fire': ['p:stings', 'p:burns', 'p:poisoning'],
    'stove': ['s:surv-wood-stoves-fireplaces', 's:surv-carbon-monoxide', 's:surv-fallout-shelter-living'],
    'sick': ['p:altitude', 'p:radiation-sickness', 'p:vomiting-diarrhea'],
    'vomiting': ['p:vomiting-diarrhea', 'p:dehydration', 'p:recovery-position'],
    'baby': ['p:choking-infant', 'p:cpr-infant', 'p:burns'],
    'milk': ['s:surv-fallout-water-and-food', 's:surv-fire', 's:surv-food-and-wild-plants'],
    'can': ['s:surv-potassium-iodide', 's:surv-store-fuel', 's:surv-unheated-house'],
    'salt': ['p:dehydration', 'p:heat-illness', 'p:vomiting-diarrhea'],
    'ice': ['p:sprain-dislocation', 'p:snakebite', 'p:amputation'],
    'freezer': ['s:surv-water-store', 's:surv-fallout-water-and-food'],
    'power': ['s:surv-wells-without-power', 's:surv-generators', 's:surv-heat-out'],
    'pantry': ['s:surv-fallout-water-and-food'],
    'spoiled': [],
    'botulism': [],
    'formula': ['s:surv-fallout-water-and-food', 's:surv-wind-chill', 'c:fallout-shelter-kit'],
    'canning': [],
    'power out': ['s:surv-heat-out', 's:surv-wells-without-power', 's:surv-generators'],
    'breastfeeding': ['s:surv-fallout-water-and-food', 's:surv-potassium-iodide', 'p:dehydration'],
    'honey': ['p:burns', 'p:stings'],
    'fever': ['p:tick', 'p:altitude', 'p:animal-bite'],
    'dehydration': ['p:dehydration', 'p:vomiting-diarrhea', 'p:altitude'],
    'meat': ['p:stings', 's:surv-field-dressing-game'],
    'thermometer': ['p:frostbite', 'p:heat-illness', 's:surv-field-dressing-game'],
    'power outage': ['s:surv-generators', 's:surv-heat-out', 's:surv-wells-without-power'],
    'flood': ['s:surv-wells-without-power', 's:surv-find-water', 's:surv-latrines'],
    'canned': ['s:surv-unheated-house', 's:surv-fallout-water-and-food', 's:surv-water-in-the-house'],
    'oven': ['s:surv-carbon-monoxide', 's:surv-heat-out', 's:surv-fallout-shelter-living'],
    'range': ['a:ballistics', 's:surv-carbon-monoxide', 's:surv-heat-out'],
    'grill': ['s:surv-carbon-monoxide', 's:surv-heat-out', 's:surv-fallout-shelter-living'],
    'store': ['s:surv-store-fuel', 's:surv-water-store', 's:surv-unheated-house'],
    'storing': ['s:surv-find-water', 's:surv-firewood', 's:surv-handwashing'],
    'storage': ['s:surv-store-fuel', 's:surv-water-store', 's:surv-fallout-where-to-shelter'],
    'what to buy': ['s:surv-fallout-get-ready', 's:surv-portable-heaters', 's:surv-store-fuel'],
    'date': ['p:tick', 'p:animal-bite', 's:surv-water-store'],
    'insects': ['s:surv-food-and-wild-plants', 's:surv-find-water', 's:surv-latrines'],
    'throw out': ['s:surv-portable-heaters', 's:surv-dirty-bomb', 's:surv-latrines'],
    'bottles': ['s:surv-water-store', 's:surv-make-water-safe', 's:surv-fallout-water-and-food'],
    'raw': [],
    'feeding': ['s:surv-generators', 's:surv-handwashing', 's:surv-traps-and-fishing'],
    'children': ['s:surv-dress-for-cold', 's:surv-water-how-much', 's:surv-dirty-bomb'],
    'child': ['p:choking', 'p:cpr-child', 'p:animal-bite'],
    'dishes': ['s:surv-clean-and-disinfect', 's:surv-find-water', 's:surv-garbage-and-greywater'],
    'clean': ['s:surv-clean-and-disinfect', 's:surv-fallout-coming-inside', 's:surv-find-water'],
    'keep': ['s:surv-heat-out', 's:surv-carbon-monoxide', 's:surv-find-water'],
    'rationing': [],
    'preserving': [],
    'dressing': ['s:surv-field-dressing-game', 's:surv-traps-and-fishing', 'p:wound-care'],
    'field dressing': ['s:surv-field-dressing-game', 's:surv-traps-and-fishing', 'p:burns'],
    'wound dressing': ['p:wound-care', 'p:chest-wound', 'p:abdominal-wound'],
    'wound': ['p:chest-wound', 'p:wound-care', 'p:abdominal-wound'],
    'food poisoning': ['p:vomiting-diarrhea', 'p:poisoning', 'p:radiation-sickness'],
    'feed': ['s:surv-generators', 's:surv-dangerous-animals', 's:surv-handwashing'],
    'rat': ['t:rate', 'p:snakebite', 'p:abdominal-wound'],
    'thawed': ['p:frostbite', 's:surv-unheated-house'],
    'smelling': ['p:dehydration', 'p:poisoning', 'p:vomiting-diarrhea'],
    'swallowing': ['p:low-blood-sugar', 'p:poison-plants', 'p:snakebite'],
}

# Rule (b): an older Survival page may leave the first three only for a food page with the query word in its title. ("freezer" is named
# by the controller as an example; its match is the hub's summary and Do first, not its title.) No Emergency protocol leaves these lists.
V75_ACCEPTED = {
    'food': ['s:surv-food-and-wild-plants', 's:surv-fallout-water-and-food', 's:surv-food-power-out'],
    'cook': ['s:surv-food-cooking-no-power', 's:surv-fire', 's:surv-field-dressing-game'],
    'power': ['s:surv-wells-without-power', 's:surv-food-power-out', 's:surv-food-cooking-no-power'],
    'power out': ['s:surv-food-power-out', 's:surv-heat-out', 's:surv-wells-without-power'],
    'pantry': ['c:pantry', 's:surv-food-storage', 's:surv-fallout-water-and-food'],
    'storing': ['s:surv-food-storage', 's:surv-find-water', 's:surv-firewood'],
    'store': ['s:surv-store-fuel', 's:surv-water-store', 's:surv-food-how-much'],
    'feeding': ['s:surv-food-babies-children', 's:surv-generators', 's:surv-handwashing'],
    'children': ['s:surv-food-babies-children', 's:surv-dress-for-cold', 's:surv-water-how-much'],
    'clean': ['s:surv-clean-and-disinfect', 's:surv-food-clean-kitchen', 's:surv-fallout-coming-inside'],
    'keep': ['s:surv-food-clean-kitchen', 's:surv-heat-out', 's:surv-food-power-out'],
    'freezer': ['s:surv-food-power-out', 's:surv-food-still-good', 's:surv-food-preserving'],
}

# Words v7.4 had no result for: a food page is now the answer and nothing is displaced.
V75_NEW_RESULTS = {
    'spoiled': ['s:surv-food-poisoning', 's:surv-food-still-good'],
    'botulism': ['s:surv-food-poisoning', 's:surv-food-preserving', 's:surv-food-power-out'],
    'canning': ['s:surv-food-preserving', 's:surv-food-still-good'],
    'raw': ['s:surv-food-clean-kitchen', 's:surv-food-babies-children', 's:surv-food-how-much'],
    'rationing': ['s:surv-food-when-short', 's:surv-food-power-out', 's:surv-food-babies-children'],
    'preserving': ['s:surv-food-preserving', 's:surv-food-power-out', 's:surv-food-poisoning'],
}

# Ruled: a protocol that held a first-three place only through body or summary text is fairly displaced by a page whose summary or Do first
# is about the word (no keyword is the cause). Pinned as they stand so a later change is caught. An Emergency protocol leaves "meat",
# "thermometer", "thawed", "smelling" and "swallowing".
V75_ACCEPTED_WEAK = {
    'milk': ['s:surv-fallout-water-and-food', 's:surv-food-power-out', 's:surv-food-babies-children'],
    'formula': ['s:surv-fallout-water-and-food', 's:surv-food-babies-children', 's:surv-wind-chill'],
    'meat': ['s:surv-food-power-out', 's:surv-food-clean-kitchen', 's:surv-food-cooking-no-power'],
    'thermometer': ['s:surv-food-cooking-no-power', 's:surv-field-dressing-game', 's:surv-heat-out'],
    'flood': ['s:surv-wells-without-power', 's:surv-food-still-good', 's:surv-find-water'],
    'canned': ['s:surv-unheated-house', 's:surv-fallout-water-and-food', 's:surv-food-cooking-no-power'],
    'what to buy': ['s:surv-fallout-get-ready', 's:surv-food-how-much', 's:surv-portable-heaters'],
    'throw out': ['s:surv-food-still-good', 's:surv-food-power-out', 's:surv-portable-heaters'],
    'storage': ['s:surv-store-fuel', 's:surv-water-store', 's:surv-food-storage'],
    'dishes': ['s:surv-clean-and-disinfect', 's:surv-food-clean-kitchen', 's:surv-find-water'],
    'thawed': ['s:surv-food-still-good', 's:surv-unheated-house', 's:surv-food-babies-children'],
    'smelling': ['s:surv-food-still-good', 's:surv-store-fuel', 'p:dehydration'],
    'swallowing': ['s:surv-food-poisoning', 'p:low-blood-sugar', 'p:poison-plants'],
}

# Already ruled (docs/v7.5-rulings.md, batch C ruling 13): the babies page, and for "honey" also Food poisoning and botulism, lead;
# Dehydration ("breastfeeding") and Stings ("honey") are no longer in the first three.
V75_RULED = {
    'breastfeeding': ['s:surv-fallout-water-and-food', 's:surv-food-babies-children', 's:surv-potassium-iodide'],
    'honey': ['s:surv-food-poisoning', 's:surv-food-babies-children', 'p:burns'],
}

# Ruled accepted although the protocol matched by title or keyword: the page titled for the word is the right first result
# ("food poisoning": its Do first box sends the reader to the protocols; "feed" and "rat": a title-word prefix while typing).
V75_STRONG_ACCEPTED = {
    'food poisoning': ['s:surv-food-poisoning', 's:surv-food-and-wild-plants', 's:surv-food-power-out'],
    'feed': ['s:surv-food-babies-children', 's:surv-generators', 's:surv-food-poisoning'],
    'rat': ['t:rate', 's:surv-food-when-short', 's:surv-dangerous-animals'],
}

# Not resolved: Wound cleaning and care (and Burns for "field dressing") were asked to stay in the first three, with the food pack's
# link to Field dressing game removed. Food pages still match "dressing" by text that cannot be reworded (a sentence that names Field
# dressing game and two table rows, "dressings", in the USDA/FoodSafety charts), and the overlay lists every Survival result above every
# Emergency result once a Survival page leads, so the protocol is SIXTH for "dressing" and Burns fourth for "field dressing" (first
# three in V75_CHANGED, the longer lists below are pinned too). Pinned as they stand (docs/v7.5-rulings.md, Deferred: overlay grouping).
V75_OPEN = {
    'dressing': ['s:surv-field-dressing-game', 's:surv-traps-and-fishing', 's:surv-food-cooking-no-power'],
    'field dressing': ['s:surv-field-dressing-game', 's:surv-traps-and-fishing', 's:surv-food-cooking-no-power'],
}
V75_OPEN_LONGER = {
    'dressing': ['s:surv-field-dressing-game', 's:surv-traps-and-fishing', 's:surv-food-cooking-no-power', 's:surv-food-still-good',
                 's:surv-food-storage', 'p:wound-care'],
    'field dressing': ['s:surv-field-dressing-game', 's:surv-traps-and-fishing', 's:surv-food-cooking-no-power', 'p:burns'],
}

V75_CHANGED = {**V75_ACCEPTED, **V75_NEW_RESULTS, **V75_ACCEPTED_WEAK, **V75_RULED, **V75_STRONG_ACCEPTED, **V75_OPEN}
FOOD_FIRST = ['food', 'freezer', 'pantry', 'spoiled', 'botulism', 'formula', 'canning', 'power out', 'refreeze']


@pytest.mark.parametrize('text', sorted(V74_ON_SCREEN))
def test_v74_first_three_on_screen_are_unchanged_by_the_food_pack(page, app_url, text):
    page.goto(app_url + '#/survival')
    page.wait_for_function('window.FK && FK.search')
    open_search(page)
    now = on_screen(page, text)[:3]
    if text in V75_CHANGED:
        assert now == V75_CHANGED[text], f'{text!r}: {now}'
        assert now != V74_ON_SCREEN[text]   # if v7.4 comes back, take the query out of the changed lists
        if text in V75_ACCEPTED:   # an Emergency protocol never leaves an accepted list
            assert [k for k in V74_ON_SCREEN[text] if k.startswith('p:') and k not in now] == []
    else:
        assert now == V74_ON_SCREEN[text], f'{text!r}: first three on screen {now} (v7.4: {V74_ON_SCREEN[text]})'


@pytest.mark.parametrize('text', FOOD_FIRST)
def test_food_words_show_a_food_page_in_the_first_three_on_screen(page, app_url, text):
    page.goto(app_url + '#/survival')
    page.wait_for_function('window.FK && FK.search')
    open_search(page)
    ks = on_screen(page, text)[:3]
    assert any(k.startswith('s:surv-food-') or k == 'c:pantry' for k in ks), f'{text!r}: {ks}'


FIRST_FIVE = {
    'breastfeeding': ['s:surv-fallout-water-and-food', 's:surv-food-babies-children', 's:surv-potassium-iodide', 's:surv-food-when-short', 'p:dehydration'],
    'honey': ['s:surv-food-poisoning', 's:surv-food-babies-children', 'p:burns', 'p:stings'],
    'food poisoning': ['s:surv-food-poisoning', 's:surv-food-and-wild-plants', 's:surv-food-power-out', 's:surv-food-clean-kitchen', 's:surv-food-preserving'],
}


@pytest.mark.parametrize('text', sorted(FIRST_FIVE))
def test_first_five_on_screen_are_pinned_as_they_stand(page, app_url, text):
    # "breastfeeding": Dehydration is fifth (Rationing food also matches); "honey": Stings is fourth; "food poisoning": the protocols
    # come after five Survival pages, the page titled for it first
    page.goto(app_url + '#/survival')
    page.wait_for_function('window.FK && FK.search')
    open_search(page)
    assert on_screen(page, text)[:5] == FIRST_FIVE[text]


def test_food_pages_are_indexed_after_every_older_page_hub_first(page, app_url):
    # "fishing" matches the Traps topic by title and an older protocol and three food pages by body text alone, all at the same score:
    # at equal score the older page is listed first, then the food hub, then the other food pages
    page.goto(app_url + '#/survival')
    page.wait_for_function('window.FK && FK.search')
    ks = [r['key'] for r in q(page, 'fishing')]
    older, hub = ks.index('p:impaled-object'), ks.index('s:surv-food-power-out')
    assert older < hub and all(hub < ks.index(k) for k in ks if k.startswith('s:surv-food-') and k != 's:surv-food-power-out'), ks


@pytest.mark.parametrize('text', sorted(V75_OPEN_LONGER))
def test_dressing_lists_are_pinned_past_the_first_three(page, app_url, text):
    page.goto(app_url + '#/survival')
    page.wait_for_function('window.FK && FK.search')
    open_search(page)
    assert on_screen(page, text)[:len(V75_OPEN_LONGER[text])] == V75_OPEN_LONGER[text]


# Guard for the food pack's rule on keywords: a food page may not take an Emergency protocol out of the first three on screen when the
# query is that protocol's own title or one of its keywords. Every shipped protocol, every title and keyword, typed into the overlay on
# #/survival. The failures must be exactly the two lists below, so a fixed one has to leave the list and a new one cannot slip in.
# Ruled (docs/v7.5-rulings.md): "food poisoning" (the page titled for it leads; Vomiting and diarrhea follows its Do first box) and
# "dressing" (Wound cleaning and care is sixth; the overlay lists every Survival result above the Emergency group).
GUARD_RULED = {('vomiting-diarrhea', 'food poisoning'), ('wound-care', 'dressing')}
# Pre-existing in v7.4 (4375170): the protocol is already outside the first three there, for the same query, behind older Survival
# pages and protocols that match by keyword. Checked against a build of v7.4 when this guard was added; not the food pack's doing.
GUARD_PRE_EXISTING_V74 = {
    ('bleeding', 'tourniquet'), ('bleeding', 'wound'), ('bleeding', 'wound packing'), ('burns', 'hot water'), ('burns', 'boiling water'),
    ('burns', 'stove'), ('carbon-monoxide', 'generator'), ('drowning', 'river'), ('drowning', 'cold water'), ('frostbite', 'cold hands'),
    ('frostbite', 'cold feet'), ('hypothermia', 'cold'), ('hypothermia', 'wet and cold'), ('hypothermia', 'cold water'),
    ('lightning', 'storm'), ('march', 'shot'), ('poisoning', 'fuel'), ('radiation-decontamination', 'dirty bomb'),
    ('recovery-position', 'unresponsive'), ('recovery-position', 'breathing'), ('shock', 'cold sweat'), ('shock', 'collapse'),
    ('wound-care', 'cut'), ('wound-care', 'bite'),
}


def test_every_protocol_title_and_keyword_keeps_its_protocol_in_the_first_three(page, app_url):
    page.goto(app_url + '#/survival')
    page.wait_for_function('window.FK && FK.search')
    open_search(page)
    out = page.evaluate("""() => {
      const pairs = FK_DATA.protocols.flatMap(p => [[p.id, p.title], ...(p.keywords || []).map(k => [p.id, k])]);
      const input = document.querySelector('#searchInput');
      return pairs.filter(([id, text]) => {
        input.value = text; input.dispatchEvent(new Event('input', {bubbles: true}));
        return ![...document.querySelectorAll('#searchBody .sr-item')].slice(0, 3).some(e => e.dataset.key === 'p:' + id);
      }); }""")
    assert len(out) < 40   # the lists below are a handful; a flood means the overlay did not run
    assert {tuple(x) for x in out} == GUARD_RULED | GUARD_PRE_EXISTING_V74, sorted(map(tuple, out))


def _packs():
    # the PACKS literal of src/search.js, read as text (the list is private to the module)
    src = open(os.path.join(os.path.dirname(__file__), '..', 'src', 'search.js'), encoding='utf-8').read()
    body = re.search(r'const PACKS = \[(.*?)\n  \];', src, re.S).group(1)
    packs = []
    for m in re.finditer(r"\{ topic: '([^']+)', hub: '([^']+)', protocols: \[([^\]]*)\], checklists: \[([^\]]*)\] \}", body):
        ids = lambda g: re.findall(r"'([^']+)'", g)
        packs.append({'topic': m.group(1), 'hub': m.group(2), 'protocols': ids(m.group(3)), 'checklists': ids(m.group(4))})
    return packs


def test_every_id_in_PACKS_exists_and_each_pack_holds_its_category():
    root = os.path.join(os.path.dirname(__file__), '..', 'src')
    load = lambda d: {j['id']: j for j in (json.load(open(f, encoding='utf-8')) for f in glob.glob(os.path.join(root, d, '*.json')))}
    protocols, checklists, topics = load('protocols'), load('checklists'), load('survival')
    packs = _packs()
    assert [k['topic'] for k in packs] == ['radiation', 'food'], packs   # the order is the index order: oldest pack first
    seen = []
    for k in packs:
        assert k['hub'].startswith('s:') and k['hub'][2:] in topics, k['hub']
        assert topics[k['hub'][2:]]['category'] == k['topic'], k['hub']   # the hub is a topic of its own pack
        assert [i for i in k['protocols'] if i not in protocols] == [], k   # every listed protocol and checklist ships
        assert [i for i in k['checklists'] if i not in checklists] == [], k
        assert [i for i in k['checklists'] if checklists[i].get('category') != k['topic']] == [], k   # and belongs to this pack's category
        seen += [('p', i) for i in k['protocols']] + [('c', i) for i in k['checklists']]
    assert len(seen) == len(set(seen))   # in no two packs
    food = packs[1]
    assert food['checklists'] == ['pantry'] and food['protocols'] == []
    for tid, t in topics.items():   # every food topic is in a pack category, and the food category is whole
        if t.get('category') == 'food':
            assert tid.startswith('surv-food-')
    assert sum(1 for t in topics.values() if t.get('category') == 'food') == 10
    assert 'pantry' in food['checklists'] and checklists['pantry'].get('category') == 'food'   # c:pantry is indexed in the food pack
    # Pack membership is by category for checklists and topics: one whose category is a pack's category belongs to that pack, so a new
    # one has to be listed. Protocols carry no pack field (the radiation protocols are in the injury categories), so their explicit lists
    # are asserted above (the food pack has none).
    for k in packs:
        assert sorted(i for i, c in checklists.items() if c.get('category') == k['topic']) == sorted(k['checklists']), k['topic']
