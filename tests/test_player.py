import json

LONG = ('word ' * 600).strip()  # 2999 chars

FIXTURES = [
    {
        'id': 'branchy', 'title': 'Branch test', 'category': 'life', 'reviewed': '2026-11-16',
        'sources': [{'name': 'Fixture source', 'year': 2025}],
        'steps': [
            {'id': 'a', 'text': 'Step A action'},
            {'id': 'q', 'text': 'Is it yes?', 'ask': {'q': 'Is it yes?', 'yes': 'y', 'no': 'n'}},
            {'id': 'y', 'text': 'Yes branch', 'end': True},
            {'id': 'n', 'text': 'No branch', 'detail': LONG + '\n\nSecond <b>para</b>', 'warn': 'Careful <i>now</i>',
             'timer': {'seconds': 2, 'label': 'Hold it'}},
            {'id': 'z', 'text': 'Final step', 'log': 'Did the thing'},
        ],
        'donts': ['Do not panic'], 'evacuate': ['Evacuate if worse'],
    },
    {
        'id': 'adv', 'title': 'Advanced proc', 'category': 'advanced', 'tier': 'advanced', 'reviewed': '2026-11-16',
        'sources': [{'name': 'Fixture'}],
        'indications': ['Ind one'], 'contraindications': ['Contra one'], 'equipment': ['Gear one'],
        'complications': ['Complication one'],
        'steps': [{'id': 's1', 'text': 'Adv step one'}, {'id': 's2', 'text': 'Adv step two'}],
    },
    {
        'id': 'drafty', 'title': 'Draft one', 'category': 'life', 'draft': True, 'reviewed': '2026-11-16',
        'sources': [{'name': 'Fixture'}], 'steps': [{'id': 's1', 'text': 'Draft step'}],
    },
]


def inject(page):
    """FK_DATA is assigned by an inline script after init scripts run, so trap the assignment
    and append fixtures to its protocols."""
    page.add_init_script(f"""
      (() => {{
        const extra = {json.dumps(FIXTURES)};
        let val;
        Object.defineProperty(window, 'FK_DATA', {{
          configurable: true,
          get() {{ return val; }},
          set(v) {{ val = v; v.protocols.push(...extra); }}
        }});
      }})();
    """)


def action(page):
    return page.locator('#player .pp-action').inner_text()


def test_open_shows_first_step_action_and_progress(page, app_url):
    inject(page)
    page.goto(app_url + '#/emergency/branchy')
    assert page.locator('#player').is_visible()
    assert action(page) == 'Step A action'
    assert page.locator('#player .pp-count').inner_text() == '1 of 5'
    size = page.eval_on_selector('#player .pp-action', 'e => parseFloat(getComputedStyle(e).fontSize)')
    assert size >= 20
    assert not page.locator('.tabbar').is_visible()


def test_next_and_back_move_one_step_and_update_hash(page, app_url):
    inject(page)
    page.goto(app_url + '#/emergency/branchy')
    page.click('#player [data-act="next"]')
    assert page.url.endswith('#/emergency/branchy/q')
    assert action(page) == 'Is it yes?'
    page.click('#player [data-act="back"]')
    assert page.url.endswith('#/emergency/branchy')
    assert action(page) == 'Step A action'


def test_android_back_steps_back_then_leaves_player(page, app_url):
    inject(page)
    page.goto(app_url + '#/emergency')
    page.evaluate("FK.protocol.open('branchy')")
    page.click('#player [data-act="next"]')
    assert action(page) == 'Is it yes?'
    page.go_back()
    assert action(page) == 'Step A action'
    page.go_back()
    assert not page.locator('#player').is_visible()
    assert page.locator('#tab-emergency').is_visible()
    assert page.locator('.tabbar').is_visible()


def test_branch_yes_and_no_go_to_named_steps(page, app_url):
    inject(page)
    page.goto(app_url + '#/emergency/branchy/q')
    page.click('#player [data-act="yes"]')
    assert page.url.endswith('/branchy/y')
    assert action(page) == 'Yes branch'
    assert page.locator('#player [data-act="done"]').is_visible()  # end:true -> Done, not NEXT
    page.go_back()
    page.click('#player [data-act="no"]')
    assert page.url.endswith('/branchy/n')
    # UI Back after a branch returns to the question, not the previous array item
    page.click('#player [data-act="back"]')
    assert page.url.endswith('/branchy/q')


def test_detail_text_is_shown_untruncated_and_escaped(page, app_url):
    inject(page)
    page.goto(app_url + '#/emergency/branchy/n')
    detail = page.locator('#player .pp-detail')
    assert len(detail.inner_text()) >= 3000
    assert page.locator('#player .pp-detail p').count() == 2
    assert page.locator('#player .pp-detail b').count() == 0  # markup in data stays text
    assert '<b>para</b>' in detail.inner_text()
    assert page.locator('#player .pp-warn i').count() == 0
    assert 'Careful <i>now</i>' in page.locator('#player .pp-warn').inner_text()


def test_all_steps_view_lists_every_step_donts_evacuate_sources_reviewed(page, app_url):
    inject(page)
    page.goto(app_url + '#/emergency/branchy')
    page.click('#player [data-act="toggleAll"]')
    assert page.url.endswith('/branchy/all')
    text = page.locator('#player').inner_text()
    for s in ('Step A action', 'Is it yes?', 'Yes branch', 'No branch', 'Final step',
              'Do not panic', 'Evacuate if worse', 'Fixture source', '2026-11-16'):
        assert s in text, s
    assert len(text) > 3000  # full detail present too


def test_progress_survives_reload_and_offers_resume(page, app_url):
    inject(page)
    page.goto(app_url + '#/emergency/branchy')
    page.click('#player [data-act="next"]')
    stored = page.evaluate("JSON.parse(localStorage.getItem('fk.proto.active'))")
    assert stored['id'] == 'branchy' and stored['step'] == 'q' and stored['started'] > 0
    page.reload()
    act = page.evaluate('FK.protocol.active()')
    assert act['id'] == 'branchy' and act['step'] == 'q'
    assert action(page) == 'Is it yes?'


def test_done_on_last_step_clears_progress(page, app_url):
    inject(page)
    page.goto(app_url + '#/emergency/branchy/z')
    assert page.evaluate('FK.protocol.active()')['step'] == 'z'
    page.evaluate("window.__logged = []; FK.log = s => window.__logged.push(s); 0")
    page.click('#player [data-act="done"]')
    assert page.evaluate('window.__logged') == ['Did the thing']
    assert page.evaluate('FK.protocol.active()') is None
    assert not page.locator('#player').is_visible()
    assert page.url.endswith('#/emergency')


def test_unknown_protocol_id_goes_to_emergency_home(page, app_url):
    page.goto(app_url + '#/emergency/nope')
    assert not page.locator('#player').is_visible()
    assert page.locator('#tab-emergency').is_visible()
    assert page.url.endswith('#/emergency')


def test_unknown_protocol_id_via_back_is_replaced(page, app_url):
    page.goto(app_url + '#/emergency')
    page.evaluate("history.pushState(null, '', '#/emergency/nope'); dispatchEvent(new PopStateEvent('popstate'))")
    page.wait_for_function("location.hash === '#/emergency'")
    assert not page.locator('#player').is_visible()


def test_reserved_segments_leave_emergency_showing(page, app_url):
    for seg in ('tool/tq', 'report/x'):
        page.goto(app_url + '#/emergency/' + seg)
        assert not page.locator('#player').is_visible()
        assert page.locator('#tab-emergency').is_visible()
        assert page.url.endswith('#/emergency/' + seg)  # not redirected away


def test_stale_active_step_is_cleared(page, app_url):
    inject(page)
    page.goto(app_url)
    page.evaluate("localStorage.setItem('fk.proto.active', JSON.stringify({id:'branchy', step:'gone', started: 1}))")
    page.reload()
    assert page.evaluate('FK.protocol.active()') is None
    assert page.evaluate("localStorage.getItem('fk.proto.active')") in (None, 'null')


def test_unknown_step_in_address_goes_to_first_step(page, app_url):
    inject(page)
    page.goto(app_url + '#/emergency/branchy/gone')
    assert page.url.endswith('#/emergency/branchy')
    assert action(page) == 'Step A action'


def test_advanced_requires_acknowledgement_once(page, app_url):
    inject(page)
    page.goto(app_url + '#/emergency/adv')
    assert 'These procedures can kill if done wrong or when they are not needed. They are a reference for people who have trained on them hands-on. Reading this is not training.' in page.locator('#player').inner_text()
    assert 'Adv step one' not in page.locator('#player').inner_text()
    page.click('text=I understand, show procedures')
    assert page.evaluate("JSON.parse(localStorage.getItem('fk.advAck'))") is True
    text = page.locator('#player').inner_text()
    for s in ('When to do this', 'Ind one', 'When not to', 'Contra one', 'Equipment', 'Gear one',
              'What can go wrong', 'Complication one'):
        assert s in text, s
    page.click('#player [data-act="start"]')
    assert action(page) == 'Adv step one'
    page.reload()
    assert 'I understand' not in page.locator('#player').inner_text()


def test_draft_label_in_player_and_all_steps(page, app_url):
    inject(page)
    page.goto(app_url + '#/emergency/drafty')
    assert 'Draft, not source-checked' in page.locator('#player .pp-head').inner_text()
    page.click('#player [data-act="toggleAll"]')
    assert 'Draft, not source-checked' in page.locator('#player').inner_text()


def test_focus_moves_to_action_on_step_change(page, app_url):
    inject(page)
    page.goto(app_url + '#/emergency/branchy')
    page.click('#player [data-act="next"]')
    assert page.evaluate("document.activeElement.classList.contains('pp-action')")


def test_next_button_height_at_least_56px(page, app_url):
    inject(page)
    page.goto(app_url + '#/emergency/branchy')
    for sel in ('next', 'back'):
        h = page.eval_on_selector(f'#player [data-act="{sel}"]', 'e => e.getBoundingClientRect().height')
        assert h >= 56
    page.goto(app_url + '#/emergency/branchy/q')
    for sel in ('yes', 'no'):
        h = page.eval_on_selector(f'#player [data-act="{sel}"]', 'e => e.getBoundingClientRect().height')
        assert h >= 56


def test_timer_counts_down_and_announces_completion(page, app_url):
    inject(page)
    page.goto(app_url + '#/emergency/branchy/n')
    page.click('#player [data-act="timer"]')
    assert page.locator('#player .pp-timerbar').is_visible()
    page.wait_for_function("document.querySelector('#ppLive').textContent.includes('Hold it')", timeout=5000)
    assert page.locator('#ppLive').get_attribute('aria-live') == 'polite'


def test_tool_button_only_when_tools_exist_and_calls_start(page, app_url):
    page.goto(app_url + '#/emergency/bleeding/s4')
    assert page.locator('#player [data-act="tool"]').count() == 0  # FK.tools undefined (Task 5)
    page.evaluate("window.__t = []; FK.tools = { start: (n, o) => window.__t.push([n, o]) }")
    page.goto(app_url + '#/emergency')
    page.evaluate("FK.protocol.open('bleeding', 's4')")
    page.click('#player [data-act="tool"]')
    assert page.evaluate('window.__t') == [['tq', {'protocol': 'bleeding'}]]


def test_log_hook_called_on_next(page, app_url):
    page.goto(app_url + '#/emergency/bleeding/s4')
    page.evaluate("window.__l = []; FK.log = s => window.__l.push(s); 0")
    page.click('#player [data-act="next"]')
    assert page.evaluate('window.__l') == ['Tourniquet applied']


def test_close_and_get_api(page, app_url):
    page.goto(app_url + '#/emergency/bleeding')
    assert page.evaluate("FK.protocol.get('bleeding').title") == 'Severe bleeding'
    assert page.evaluate("FK.protocol.get('zzz')") is None
    page.evaluate('FK.protocol.close()')
    assert not page.locator('#player').is_visible()
    assert page.url.endswith('#/emergency')


def test_works_without_wake_lock_api(page, app_url):
    page.add_init_script("Object.defineProperty(navigator, 'wakeLock', {value: undefined})")
    page.goto(app_url + '#/emergency/bleeding')
    assert page.locator('#player').is_visible()
