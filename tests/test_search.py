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
    # each result names its kind
    open_search(page)
    type_q(page, 'go bag')
    assert page.locator('#searchBody .sr-item small').first.text_content().startswith('Checklist')


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
    assert page.locator('#searchBody .sr-item small').first.text_content().startswith('Tool')


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
    assert keys(page)[0] == 'p:cricothyrotomy'
    assert page.locator('#searchBody .sr-item small').first.text_content().startswith('Advanced')
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


def test_whole_keyword_beats_a_title_prefix_and_loses_to_a_whole_title_word(page, app_url):
    # v7.7: a searched word that is a whole keyword beats a title that merely starts with it, at any length ("fall" is Head injury's
    # keyword and only the start of "fallout"). A prefix of a keyword gets nothing, and a whole title word still comes first.
    fx = [proto('zq-title', 'Zqualm thing'), proto('zq-kw', 'Other thing', keywords=['zq alarm']),
          proto('zqx-title', 'Zqxlong thing'), proto('zqx-kw', 'Another thing', keywords=['zqx']),
          proto('zqw-word', 'Zqw thing'), proto('zqw-kw', 'More thing', keywords=['zqw']), proto('zqw-pre', 'Zqwmore thing')]
    boot(page, app_url, FIXTURES + fx)
    assert [r['key'] for r in q(page, 'zq')][:2] == ['p:zq-kw', 'p:zq-title']
    assert [r['key'] for r in q(page, 'ZQX')][:2] == ['p:zqx-kw', 'p:zqx-title']   # three letters: the whole keyword is first now
    assert [r['key'] for r in q(page, 'z')][:1] == ['p:zq-title']                 # "z" is no whole keyword anywhere
    assert [r['key'] for r in q(page, 'zqxl')][:1] == ['p:zqx-title']             # no keyword starts with it: the title prefix stands
    assert [r['key'] for r in q(page, 'zqw')][:3] == ['p:zqw-word', 'p:zqw-kw', 'p:zqw-pre']   # title word, keyword, title prefix


def test_a_keyword_with_an_ending_counts_as_the_whole_word_one_way_only(page, app_url):
    # searching "zqcollapse" finds the keyword "zqcollapsed" as a whole word; searching the longer form does not promote the shorter
    fx = [proto('zqc-title', 'Zqcollapsexyz thing'), proto('zqc-kw', 'Other thing', keywords=['zqcollapsed']),
          proto('zqb-title', 'Zqbreathingxyz thing'), proto('zqb-kw', 'Another thing', keywords=['zqbreath'])]
    boot(page, app_url, FIXTURES + fx)
    assert [r['key'] for r in q(page, 'zqcollapse')][:2] == ['p:zqc-kw', 'p:zqc-title']
    assert [r['key'] for r in q(page, 'zqbreathing')] == ['p:zqb-title']


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


FOOD_KEYS = {'s:surv-food-power-out', 's:surv-food-still-good', 's:surv-food-cooking-no-power', 's:surv-food-poisoning', 's:surv-food-how-much',
             's:surv-food-storage', 's:surv-food-when-short', 's:surv-food-clean-kitchen', 's:surv-food-babies-children',
             's:surv-food-preserving', 'c:pantry'}


def on_screen(page, text):
    type_q(page, text)
    page.wait_for_selector('#searchBody .sr-item')
    return keys(page)


@pytest.mark.parametrize('text', ['fallout', 'nuclear'])
def test_fallout_and_nuclear_show_the_fallout_warning_hub_in_the_first_three_on_screen(page, app_url, text):
    # The hub is indexed after every v7.3 page and after the two pack protocols (re-review R1), so it wins no tie with an older page.
    page.goto(app_url + '#/survival')
    page.wait_for_function('window.FK && FK.search')
    open_search(page)
    ks = on_screen(page, text)
    assert 's:surv-fallout-warning' in ks[:3], f'{text!r}: {ks[:5]}'


# ---------- v7.7: one list in rank order ----------
# Until v7.7 the overlay regrouped results by kind and showed the leading kind's whole group first, and a title that merely started
# with the searched word outranked a protocol with that word as its keyword. Both changed in v7.7 (docs/v7.7-rulings.md, Search), so
# the lists pinned against the v7.3 and v7.4 releases were replaced by the one below: the first five results on screen for every search
# those lists pinned, plus the searches named in the v7.5 and v7.7 rulings, recorded from the v7.7 overlay at 360x640 on #/survival.
# docs/v7.7-search-comparison.md shows each list beside what v7.6 showed. A later pack must not change them without a ruling.
V77_ON_SCREEN = json.load(open(os.path.join(os.path.dirname(__file__), 'fixtures', 'search_v77_on_screen.json'), encoding='utf-8'))


@pytest.mark.parametrize('text', sorted(V77_ON_SCREEN))
def test_v77_first_five_on_screen_are_unchanged(page, app_url, text):
    page.goto(app_url + '#/survival')
    page.wait_for_function('window.FK && FK.search')
    open_search(page)
    now = on_screen(page, text)[:5]
    assert now == V77_ON_SCREEN[text], f'{text!r}: first five on screen {now} (v7.7: {V77_ON_SCREEN[text]})'


def test_milk_allergy_still_shows_anaphylaxis_first(page, app_url):
    # "milk" now lists Game, fish, milk and gardens after fallout first and Anaphylaxis leaves its first five (docs/v7.7-rulings.md,
    # batch D ruling 12); a search for the allergy must still put the protocol first
    page.goto(app_url + '#/survival')
    page.wait_for_function('window.FK && FK.search')
    open_search(page)
    assert on_screen(page, 'milk allergy')[0] == 'p:anaphylaxis'


@pytest.mark.parametrize('text', ['bleeding', 'cold', 'food poisoning', 'dressing', 'water', 'CO', 'fall', 'shelter in place'])
def test_the_screen_shows_results_in_rank_order_with_no_group_headings(page, app_url, text):
    page.goto(app_url + '#/survival')
    page.wait_for_function('window.FK && FK.search')
    open_search(page)
    assert on_screen(page, text) == [r['key'] for r in q(page, text)]
    assert page.locator('#searchBody .sr-h').count() == 0
    kinds = page.eval_on_selector_all('#searchBody .sr-item small', "els => els.map(e => e.textContent.split(' · ')[0])")
    assert kinds == [r['where'] for r in q(page, text)]   # every row names its kind


# What a person types in a hurry, and the protocol that has to be on the first screen for it. Each of these was wrong before v7.7.
@pytest.mark.parametrize('text,key,place', [
    ('fall', 'p:head-injury', 1), ('collapse', 'p:cpr-adult', 1), ('breathing', 'p:cpr-adult', 1), ('burn', 'p:burns', 1),
    ('vomit', 'p:vomiting-diarrhea', 1), ('tourniquet', 'p:bleeding', 3), ('food poisoning', 'p:vomiting-diarrhea', 2),
    ('cold hands', 'p:frostbite', 3), ('cold feet', 'p:frostbite', 3), ('generator', 'p:carbon-monoxide', 2),
    ('dressing', 'p:wound-care', 2), ('fire', 'p:burns', 3), ('wound packing', 'p:bleeding', 3), ('dirty bomb', 'p:radiation-decontamination', 3)])
def test_hurried_words_put_their_protocol_on_the_first_screen(page, app_url, text, key, place):
    page.goto(app_url + '#/survival')
    page.wait_for_function('window.FK && FK.search')
    open_search(page)
    ks = on_screen(page, text)
    assert key in ks[:place], f'{text!r}: {ks[:5]}'


FOOD_FIRST = ['food', 'freezer', 'pantry', 'spoiled', 'botulism', 'formula', 'canning', 'power out', 'refreeze']


@pytest.mark.parametrize('text', FOOD_FIRST)
def test_food_words_show_a_food_page_in_the_first_three_on_screen(page, app_url, text):
    page.goto(app_url + '#/survival')
    page.wait_for_function('window.FK && FK.search')
    open_search(page)
    ks = on_screen(page, text)[:3]
    assert any(k.startswith('s:surv-food-') or k == 'c:pantry' for k in ks), f'{text!r}: {ks}'


def test_food_pages_are_indexed_after_every_older_page_hub_first(page, app_url):
    # "fishing" matches the Traps topic by title and an older protocol and three food pages by body text alone, all at the same score:
    # at equal score the older page is listed first, then the food hub, then the other food pages
    page.goto(app_url + '#/survival')
    page.wait_for_function('window.FK && FK.search')
    ks = [r['key'] for r in q(page, 'fishing')]
    older, hub = ks.index('p:impaled-object'), ks.index('s:surv-food-power-out')
    assert older < hub and all(hub < ks.index(k) for k in ks if k.startswith('s:surv-food-') and k != 's:surv-food-power-out'), ks


# Guard: every shipped protocol, its title and each of its keywords, typed into the overlay on #/survival, must show that protocol in
# the first three. The failures must be exactly the list below, so a fixed one has to leave it and a new one cannot slip in.
# v7.5 had 26; the v7.7 list and scoring changes fixed 16 and added none (docs/v7.7-rulings.md, Search). What is left: another protocol
# or a page titled with the word fits it at least as well ("wound", "cut", "bite", "shot", "cold", "unresponsive", "breathing",
# "collapse"), or the phrase is two title words of three older pages ("nuclear fallout").
GUARD_V77 = {
    ('bleeding', 'wound'), ('hypothermia', 'cold'), ('hypothermia', 'cold water'), ('march', 'shot'),
    ('radiation-sickness', 'nuclear fallout'), ('recovery-position', 'breathing'), ('recovery-position', 'unresponsive'),
    ('shock', 'collapse'), ('wound-care', 'bite'), ('wound-care', 'cut'),
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
    assert {tuple(x) for x in out} == GUARD_V77, sorted(map(tuple, out))


def _packs():
    # the PACKS literal of src/search.js, read as text (the list is private to the module)
    src = open(os.path.join(os.path.dirname(__file__), '..', 'src', 'search.js'), encoding='utf-8').read()
    body = re.search(r'const PACKS = \[(.*?)\n  \];', src, re.S).group(1)
    packs = []
    for m in re.finditer(r"\{ topic: '([^']+)', hub: '([^']+)', protocols: \[([^\]]*)\], checklists: \[([^\]]*)\](?:, older: \[([^\]]*)\])? \}", body):
        ids = lambda g: re.findall(r"'([^']+)'", g or '')
        packs.append({'topic': m.group(1), 'hub': m.group(2), 'protocols': ids(m.group(3)), 'checklists': ids(m.group(4)), 'older': ids(m.group(5))})
    return packs


def test_every_id_in_PACKS_exists_and_each_pack_holds_its_category():
    root = os.path.join(os.path.dirname(__file__), '..', 'src')
    load = lambda d: {j['id']: j for j in (json.load(open(f, encoding='utf-8')) for f in glob.glob(os.path.join(root, d, '*.json')))}
    protocols, checklists, topics = load('protocols'), load('checklists'), load('survival')
    packs = _packs()
    assert [k['topic'] for k in packs] == ['radiation', 'food', 'land'], packs   # the order is the index order: oldest pack first
    seen = []
    for k in packs:
        assert k['hub'].startswith('s:'), k['hub']
        assert k['hub'][2:] in topics, k['hub']
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
    # "older" lists topics of the pack's category that were indexed before the pack existed: they keep that place, so each must be
    # a shipped topic of the category; every other topic of the category is newer than v7.6 (its id starts surv-land-)
    land = packs[2]
    assert land['older'] == ['s:surv-traps-and-fishing', 's:surv-field-dressing-game', 's:surv-food-and-wild-plants'], land
    assert land['hub'] == 's:surv-land-start' and land['checklists'] == ['land-kit'] and land['protocols'] == []
    for k in packs[:2]:
        assert k['older'] == [], k
    for tid, t in topics.items():
        if t.get('category') == 'land':
            assert 's:' + tid in land['older'] or tid.startswith('surv-land-'), tid
    assert [i for i in land['older'] if i[2:] not in topics or topics[i[2:]]['category'] != 'land'] == []


@pytest.mark.parametrize('text,page_key', [('cross contamination', 's:surv-food-clean-kitchen'), ('how long can food sit out', 's:surv-food-still-good'),
                                           ('running out of food', 's:surv-food-when-short'), ('infant formula', 's:surv-food-babies-children'),
                                           ('gas range', 's:surv-food-cooking-no-power'), ('kitchen range', 's:surv-food-cooking-no-power'),
                                           ('power outage food', 's:surv-food-power-out'), ('power outage freezer', 's:surv-food-power-out'),
                                           ('when in doubt throw it out', 's:surv-food-still-good'), ('defrost', 's:surv-food-still-good'),
                                           ('food gone bad', 's:surv-food-still-good'), ('sterilize', 's:surv-food-babies-children')])
def test_food_phrases_find_their_page(page, app_url, text, page_key):
    page.goto(app_url + '#/survival')
    page.wait_for_function('window.FK && FK.search')
    open_search(page)
    ks = on_screen(page, text)[:3]
    assert page_key in ks, ks
    if text != 'infant formula':   # "infant formula" finds the babies page second, after Water and food after fallout (as in v7.4)
        assert ks[0] == page_key, ks


def test_power_outage_lists_the_food_hub_in_the_first_four_after_the_v74_results(page, app_url):
    # final review I1: the hub's own text says "power outage"; v7.4's first three stay as they were
    page.goto(app_url + '#/survival')
    page.wait_for_function('window.FK && FK.search')
    open_search(page)
    ks = on_screen(page, 'power outage')[:4]
    assert ks == V77_ON_SCREEN['power outage'][:4] and 's:surv-food-power-out' in ks, ks


LAND_OLDER_ORDER = json.load(open(os.path.join(os.path.dirname(__file__), 'fixtures', 'search_land_older_order.json'), encoding='utf-8'))


@pytest.mark.parametrize('text', sorted(LAND_OLDER_ORDER))
def test_moved_topics_keep_their_index_position(page, app_url, text):
    # the three older topics moved to category land but stay indexed where a topic in no pack is: FK.search.query() lists the same
    # keys in the same order as the v7.6 build did (recorded in tests/fixtures/search_land_older_order.json before the move)
    # Pages that are new in the land pack (v7.7) did not exist when the fixture was recorded; they index after every older page and
    # are left out of the comparison, so what is checked is that every page that existed in v7.6 keeps its place.
    page.goto(app_url + '#/survival')
    page.wait_for_function('window.FK && FK.search')
    # the pack's new pages (ids surv-land-*, checklist land-kit) are not in the v7.6 build; leaving them out, every other key keeps its v7.6 order
    new = lambda k: k.startswith('s:surv-land-') or k == 'c:land-kit'
    assert [r['key'] for r in q(page, text) if not new(r['key'])] == LAND_OLDER_ORDER[text]
