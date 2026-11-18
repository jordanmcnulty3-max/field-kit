import json

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
