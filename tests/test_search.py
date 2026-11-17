import json

from .conftest import inject_protocols


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


def boot(page, app_url, fixtures=FIXTURES, storage=None, hash_='#/emergency'):
    inject_protocols(page, fixtures)
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
    boot(page, app_url)
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


def test_survival_topic_result_opens_that_topic(page, app_url):
    boot(page, app_url, hash_='#/tactical/map')
    open_search(page)
    type_q(page, 'bowline')
    key = page.eval_on_selector('#searchBody .sr-item', 'e => e.dataset.key')
    assert key.startswith('s:surv-')
    page.click('#searchBody .sr-item')
    assert page.locator('#tab-survival').is_visible()
    topic = page.locator('#' + key[2:])
    assert topic.evaluate('d => d.open') is True
    assert topic.locator('summary').is_visible()
    assert page.evaluate('FK.route.current().tab') == 'survival'
    assert not page.locator('#searchPane').is_visible()


def test_survival_topic_hidden_by_in_tab_search_is_revealed(page, app_url):
    boot(page, app_url, hash_='#/survival')
    page.fill('#survSearch', 'knot')
    assert page.locator('#surv-shelter').is_hidden()
    open_search(page)
    type_q(page, 'shelter')
    page.click('#searchBody .sr-item[data-key="s:surv-shelter"]')
    assert page.locator('#surv-shelter').is_visible() and page.evaluate("document.getElementById('surv-shelter').open")


def test_survival_ids_stable(page, app_url):
    boot(page, app_url, hash_='#/survival')
    ids = page.eval_on_selector_all('#survTopics details.ref', 'ds => ds.map(d => d.id)')
    assert len(ids) == 14 and all(i.startswith('surv-') for i in ids) and len(set(ids)) == 14
    page.fill('#survSearch', 'fire')   # the in-tab search still filters
    assert page.locator('#survTopics details.ref:visible').count() >= 1
    assert page.locator('#surv-knots').is_hidden() or page.evaluate("document.getElementById('surv-knots').textContent.toLowerCase().includes('fire')")


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
    boot(page, app_url, storage={'pins': ['p:splint', 't:tq', 'p:gone-away'], 'recent': ['a:ballistics', 's:surv-knots', 'p:choking']})
    open_search(page)
    heads = page.eval_on_selector_all('#searchBody .sr-h', 'e => e.map(x => x.textContent)')
    assert heads == ['Pinned', 'Recent']
    assert keys(page) == ['p:splint', 't:tq', 'a:ballistics', 's:surv-knots', 'p:choking']
    page.fill('#searchInput', 'x')
    page.fill('#searchInput', '')
    assert keys(page)[0] == 'p:splint'


def test_selecting_adds_to_recent_and_home_renders_survival_and_screen_keys(page, app_url):
    boot(page, app_url)
    open_search(page)
    type_q(page, 'bowline')
    page.click('#searchBody .sr-item')
    page.evaluate("FK.route.go('/emergency')")
    assert page.evaluate('FK.recent.all()')[0].startswith('s:surv-')
    open_search(page)
    type_q(page, 'compass')
    page.click('#searchBody .sr-item[data-key="a:position"]')
    page.evaluate("FK.route.go('/emergency')")
    recent = page.locator('#emRecent .em-btn')
    texts = recent.all_inner_texts()
    assert 'Position and compass' in texts and any('Knots' in t for t in texts)
    recent.filter(has_text='Position and compass').click()
    assert page.locator('#view-position').is_visible()


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


def test_settings_from_search_does_not_reemit_route(page, app_url):
    boot(page, app_url, storage={'advAck': True})
    page.evaluate("FK.protocol.open('choking'); window.routes = 0; FK.on('route', () => window.routes++)")
    page.evaluate("FK.route.go('/search')")
    type_q(page, 'backup')
    page.click('#searchBody .sr-item[data-key="a:settings"]')
    assert page.evaluate('window.routes') == 0
    assert page.locator('#dlgMenu').is_visible() and page.url.endswith('/emergency/choking')
