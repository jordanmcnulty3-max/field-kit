from playwright.sync_api import expect
import json

from .conftest import inject_protocols

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
    inject_protocols(page, FIXTURES)


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
    expect(page.locator('#player .pp-action')).to_have_text('Step A action')
    page.go_back()
    expect(page.locator('#player')).to_be_hidden()
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
    page.wait_for_url('**/branchy/q')
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
    # Tool addresses are owned by the tools overlay (tests/test_tools.py): the player just stays out of them.
    page.goto(app_url + '#/emergency/tool/tq')
    assert not page.locator('#player').is_visible()
    assert page.locator('#toolPane').is_visible()
    assert page.url.endswith('#/emergency/tool/tq')
    page.goto(app_url + '#/emergency/report/mist')   # reports share the tools overlay (tests/test_reports.py); an unknown report goes home there
    assert not page.locator('#player').is_visible()
    assert page.locator('#toolPane').is_visible()
    assert page.url.endswith('#/emergency/report/mist')  # not redirected away


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
    page.goto(app_url + '#/emergency')
    page.evaluate("delete FK.tools; FK.protocol.open('bleeding', 's5')")
    assert page.locator('#player [data-act="tool"]').count() == 0   # no tools module: no button
    page.evaluate("window.__t = []; FK.tools = { start: (n, o) => window.__t.push([n, o]) }")
    page.goto(app_url + '#/emergency')
    page.evaluate("FK.protocol.open('bleeding', 's5')")
    page.click('#player [data-act="tool"]')
    assert page.evaluate('window.__t') == [['tq', {'protocol': 'bleeding'}]]


def test_log_hook_called_on_next(page, app_url):
    page.goto(app_url + '#/emergency/bleeding/s5')   # the tourniquet step
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


def hash_of(page):
    return page.evaluate('location.hash')


def wait_hash(page, h):
    page.wait_for_function(f"location.hash === {json.dumps(h)}")


def open_from_home(page, app_url, path='branchy'):
    inject(page)
    page.goto(app_url + '#/emergency')
    page.evaluate(f"FK.protocol.open('{path}')")


def assert_back_leaves_for_good(page):
    """After leaving, one Android Back must not land in a protocol."""
    page.go_back()
    page.wait_for_timeout(150)
    assert not page.locator('#player').is_visible()


def test_header_back_then_android_back_does_not_reenter(page, app_url):
    open_from_home(page, app_url)
    page.click('#player [data-act="next"]')
    page.click('#player [data-act="home"]')
    wait_hash(page, '#/emergency')
    assert not page.locator('#player').is_visible()
    assert page.evaluate('history.length') >= 2
    page.go_back()
    page.wait_for_timeout(150)
    assert '/branchy' not in hash_of(page)
    assert not page.locator('#player').is_visible()


def test_android_back_after_done_does_not_reenter(page, app_url):
    inject(page)
    page.goto(app_url + '#/emergency')
    page.evaluate("FK.protocol.open('drafty')")
    page.click('#player [data-act="done"]')
    wait_hash(page, '#/emergency')
    page.go_back()
    page.wait_for_timeout(150)
    assert 'drafty' not in hash_of(page)
    assert not page.locator('#player').is_visible()


def test_android_back_after_end_protocol_does_not_reenter(page, app_url):
    open_from_home(page, app_url)
    page.click('#player [data-act="next"]')
    page.click('#player [data-act="toggleAll"]')
    page.click('#player [data-act="end"]')
    wait_hash(page, '#/emergency')
    assert page.evaluate('FK.protocol.active()') is None
    page.go_back()
    page.wait_for_timeout(150)
    assert 'branchy' not in hash_of(page)


def test_all_steps_toggle_adds_no_history(page, app_url):
    open_from_home(page, app_url)
    n = page.evaluate('history.length')
    page.click('#player [data-act="toggleAll"]')
    page.click('#player [data-act="toggleAll"]')
    assert page.evaluate('history.length') == n


def test_ui_back_then_android_back_does_not_return_to_left_step(page, app_url):
    open_from_home(page, app_url)
    page.click('#player [data-act="next"]')        # q
    page.click('#player [data-act="yes"]')         # y
    page.click('#player [data-act="back"]')        # UI back -> q
    assert action(page) == 'Is it yes?'
    page.go_back()                                 # Android back -> first step, not y
    expect(page.locator('#player .pp-action')).to_have_text('Step A action')
    page.go_back()
    page.wait_for_timeout(150)
    assert not page.locator('#player').is_visible()


def test_first_step_back_leaves_player_cleanly(page, app_url):
    open_from_home(page, app_url, 'drafty')
    page.click('#player [data-act="back"]')
    wait_hash(page, '#/emergency')
    page.go_back()
    page.wait_for_timeout(150)
    assert 'drafty' not in hash_of(page)


def test_deep_link_then_header_back_then_android_back_does_not_reenter(page, app_url):
    inject(page)
    page.goto(app_url + '#/emergency/branchy')
    page.click('#player [data-act="next"]')
    page.click('#player [data-act="home"]')
    wait_hash(page, '#/emergency')
    assert not page.locator('#player').is_visible()
    page.go_back()
    page.wait_for_timeout(150)
    assert 'branchy' not in hash_of(page)
    assert not page.locator('#player').is_visible()


WAKE_STUB = """
  window.__wake = { req: 0, rel: 0 };
  Object.defineProperty(navigator, 'wakeLock', { configurable: true, value: {
    request: () => new Promise(res => setTimeout(() => {
      window.__wake.req++;
      const l = { release: () => { window.__wake.rel++; return Promise.resolve(); }, addEventListener() {} };
      res(l);
    }, 30)) } });
"""


def test_wake_lock_requested_on_open_and_released_on_close(page, app_url):
    page.add_init_script(WAKE_STUB)
    page.goto(app_url + '#/emergency')
    page.evaluate("FK.protocol.open('bleeding')")
    page.wait_for_function('window.__wake.req === 1')
    page.evaluate('FK.protocol.close()')
    page.wait_for_function('window.__wake.rel === 1')


def test_wake_lock_survives_quick_open_close_open(page, app_url):
    page.add_init_script(WAKE_STUB)
    page.goto(app_url + '#/emergency')
    page.evaluate("FK.protocol.open('bleeding')")
    page.evaluate('FK.protocol.close()')            # closes while the request is pending
    page.wait_for_function('window.__wake.rel >= 1')
    page.evaluate("FK.protocol.open('cpr-adult')")
    page.wait_for_function('window.__wake.req >= 2')
    page.wait_for_timeout(100)
    assert page.evaluate('window.__wake.rel') == 1   # the second lock is still held
    page.evaluate('FK.protocol.close()')
    page.wait_for_function('window.__wake.rel === 2')


def test_focus_goes_to_heading_on_intro_and_all_steps(page, app_url):
    inject(page)
    page.goto(app_url + '#/emergency/adv')
    page.click('text=I understand, show procedures')
    assert page.evaluate("document.activeElement.id") == 'ppTitle'
    page.goto(app_url + '#/emergency/branchy/all')
    assert page.evaluate("document.activeElement.id") == 'ppTitle'


def test_starting_timer_keeps_focus_inside_player(page, app_url):
    inject(page)
    page.goto(app_url + '#/emergency/branchy/n')
    page.click('#player [data-act="timer"]')
    assert page.evaluate("document.activeElement.id") == 'ppTimerBar'


def test_wake_lock_rejection_does_not_hang_page(page, app_url):
    page.add_init_script("""
      window.__req = 0;
      Object.defineProperty(navigator, 'wakeLock', { configurable: true, value: {
        request: () => { window.__req++; return Promise.reject(new DOMException('denied', 'NotAllowedError')); } } });
    """)
    page.goto(app_url + '#/emergency/bleeding')
    page.wait_for_timeout(200)
    page.click('#player [data-act="next"]', timeout=3000)
    assert page.url.endswith('/bleeding/s2')
    assert page.evaluate('window.__req') <= 3


def test_double_tap_on_header_back_does_not_overshoot(page, app_url):
    inject(page)
    page.goto(app_url + '#/survival')
    page.goto(app_url + '#/tactical/map')   # earlier entries an overshoot would land on
    page.goto(app_url + '#/emergency')
    page.evaluate("FK.protocol.open('branchy')")
    page.click('#player [data-act="next"]')
    # history.go is asynchronous; widen the window in which the player is still showing
    page.evaluate("const g = history.go.bind(history); history.go = n => setTimeout(() => g(n), 150)")
    page.evaluate("const b = document.querySelector('#player [data-act=\"home\"]'); b.click(); setTimeout(() => b.click(), 0)")
    page.wait_for_timeout(500)
    assert page.url.endswith('#/emergency')
    assert page.locator('#tab-emergency').is_visible()


def test_bad_deep_link_repaired_at_boot_is_a_deep_link_entry(page, app_url):
    page.goto(app_url + '#/emergency/bleeding/zzz')
    assert page.url.endswith('#/emergency/bleeding')
    assert action(page) == page.evaluate("FK.protocol.get('bleeding').steps[0].text")   # repaired to the first step
    page.click('#player [data-act="home"]')
    wait_hash(page, '#/emergency')
    page.wait_for_timeout(200)
    assert page.url.startswith(app_url)
    assert not page.locator('#player').is_visible()


def test_every_fig_step_renders_an_svg(page, app_url):
    page.goto(app_url)
    pairs = page.evaluate("FK_DATA.protocols.flatMap(p => p.steps.filter(s => s.fig).map(s => [p.id, s.id, s.fig]))")
    assert sorted(map(tuple, pairs)) == sorted([
        ('bleeding', 's5', 'tq-placement'), ('bleeding', 's11', 'pressure-dressing'), ('choking', 's6', 'back-blows'),
        ('choking', 's7', 'abdominal-thrusts'), ('cpr-infant', 's4', 'cpr-infant'), ('cpr-adult', 's4', 'cpr-hands-adult'),
        ('tick', 's4', 'tick'), ('fracture', 's11', 'splint-forearm')]), pairs
    for pid, sid, fig in pairs:
        page.evaluate(f"location.hash = '#/emergency/{pid}/{sid}'")
        svg = page.locator('#player .pp-fig svg')
        expect(svg).to_have_count(1)
        box = svg.bounding_box()
        assert box['width'] > 100 and box['height'] > 50, (pid, sid, fig, box)
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), (pid, sid, fig)
        assert page.evaluate("(() => { const b = document.querySelector('#player .pp-body'); return b.scrollWidth <= b.clientWidth; })()"), (pid, sid, fig)
        assert box['x'] >= 0 and box['x'] + box['width'] <= 360, (pid, sid, fig, box)


# ---------- Warnings are seen; Do not / Evacuate when reachable from every step; no dial links ----------

LISTY = {
    'id': 'listy', 'title': 'List test', 'category': 'life', 'reviewed': '2026-11-16',
    'sources': [{'name': 'Fixture'}],
    'steps': [
        {'id': 'a', 'text': 'First action', 'detail': 'First detail para one\n\nFirst detail para two', 'warn': 'First warn'},
        {'id': 'b', 'text': 'Second action', 'detail': LONG, 'warn': 'Second warn'},
        {'id': 'c', 'text': 'Third action', 'end': True},
    ],
    'donts': ['Do not <b>press</b> here', 'Do not wait'],
    'evacuate': ['Evacuate <i>now</i> if worse', 'Evacuate if blue'],
}
BARE = {'id': 'bare', 'title': 'Bare', 'category': 'life', 'reviewed': '2026-11-16', 'sources': [{'name': 'Fixture'}],
        'steps': [{'id': 'a', 'text': 'Only step'}, {'id': 'b', 'text': 'Other step'}]}


def inject_listy(page):
    inject_protocols(page, FIXTURES + [LISTY, BARE])


def top(page, sel):
    return page.eval_on_selector(sel, 'e => e.getBoundingClientRect().top')


def test_warn_is_above_detail_and_inside_first_640px_in_step_mode(page, app_url):
    inject(page)
    page.goto(app_url + '#/emergency/branchy/n')
    assert len(page.locator('#player .pp-detail').inner_text()) >= 3000
    assert top(page, '#player .pp-warn') < top(page, '#player .pp-detail')
    assert top(page, '#player .pp-action') < top(page, '#player .pp-warn')
    warn = page.locator('#player .pp-warn').bounding_box()
    assert 0 <= warn['y'] and warn['y'] + warn['height'] <= 640, warn


def test_warn_is_above_detail_in_all_steps_view(page, app_url):
    inject(page)
    page.goto(app_url + '#/emergency/branchy/all')
    step = page.locator('#player .pp-step', has_text='No branch')
    assert step.locator('.pp-warn').bounding_box()['y'] < step.locator('.pp-detail').bounding_box()['y']


def test_no_draft_label_when_no_protocol_is_a_draft(page, app_url):
    inject(page)
    page.goto(app_url + '#/emergency/branchy')
    assert page.locator('#player .pp-draft').count() == 0
    page.click('#player [data-act="toggleAll"]')
    assert page.locator('#player .pp-draft').count() == 0
    page.goto(app_url + '#/emergency/drafty')
    assert page.locator('#player .pp-draft').count() == 1


def test_shipped_protocols_have_no_draft_flag(page, app_url):
    page.goto(app_url)
    assert page.evaluate("FK_DATA.protocols.filter(p => p.draft === true).map(p => p.id)") == []


def test_lists_are_collapsed_by_default_on_every_step_and_buttons_show_item_counts(page, app_url):
    inject_listy(page)
    page.goto(app_url + '#/emergency/listy')
    assert page.locator('#player .pp-list').count() == 0
    assert page.inner_text('#ppLists [data-list="donts"]').replace('\n', ' ').startswith('Do not (2)')
    assert page.inner_text('#ppLists [data-list="evacuate"]').startswith('Evacuate when (2)')
    assert page.get_attribute('#ppLists [data-list="donts"]', 'aria-expanded') == 'false'
    page.click('#ppLists [data-list="donts"]')   # opens directly below the row, before the detail
    panel = page.locator('#player .pp-list[data-list="donts"]')
    row, det, pb = page.locator('#ppLists').bounding_box(), page.locator('#player .pp-detail').bounding_box(), panel.bounding_box()
    assert 'Do not wait' in panel.inner_text()
    assert row['y'] + row['height'] <= pb['y'] + 1 and pb['y'] + pb['height'] <= det['y'] + 1
    page.click('#player [data-act="next"]')
    assert page.locator('#player .pp-list').count() == 0
    page.click('#player [data-act="back"]')   # leaving and returning does not leave it open
    assert action(page) == 'First action'
    assert page.locator('#player .pp-list').count() == 0


def test_shipped_bleeding_buttons_show_counts(page, app_url):
    page.goto(app_url + '#/emergency/bleeding')
    n = page.evaluate("[FK_DATA.protocols.find(p => p.id === 'bleeding').donts.length, FK_DATA.protocols.find(p => p.id === 'bleeding').evacuate.length]")
    assert page.inner_text('#ppLists [data-list="donts"]').startswith(f'Do not ({n[0]})')
    assert page.inner_text('#ppLists [data-list="evacuate"]').startswith(f'Evacuate when ({n[1]})')


def test_step_body_order_action_warn_figure_list_row_detail(page, app_url):
    page.goto(app_url + '#/emergency/bleeding/s5')
    order = [top(page, f'#player {sel}') for sel in ('.pp-action', '.pp-warn', '.pp-fig', '#ppLists', '.pp-detail')]
    assert order == sorted(order) and len(set(order)) == 5, order
    fig = page.locator('#player .pp-fig').bounding_box()
    assert fig['y'] < 640   # the picture starts inside the first screen


def test_action_is_the_first_content_and_nothing_above_it_is_taller_than_the_progress_bar(page, app_url):
    inject_listy(page)
    for path in ('#/emergency/listy', '#/emergency/listy/b', '#/emergency/bleeding/s5'):
        page.goto(app_url + path)
        assert top(page, '#player .pp-action') < top(page, '#ppLists'), path
        assert page.evaluate("document.querySelector('#ppBody').firstElementChild.id") == 'ppAction'
        heights = page.evaluate("""[...document.querySelectorAll('#player > *')].filter(e => e.id !== 'ppBody' && !e.classList.contains('pp-head') && !e.classList.contains('pp-prog')
          && e.getBoundingClientRect().top < document.querySelector('#ppAction').getBoundingClientRect().top).map(e => e.getBoundingClientRect().height)""")
        assert all(h <= 16 for h in heights), (path, heights)   # besides the header and progress bar, nothing above the action is taller than 16px
        assert page.eval_on_selector('#player .pp-prog', 'e => e.getBoundingClientRect().height') <= 40
        bad = page.evaluate("""(() => {
          const probe = document.createElement('i'); probe.style.color = 'var(--ink)'; document.body.appendChild(probe);
          const ink = getComputedStyle(probe).color; probe.remove();
          return [...document.querySelectorAll('#ppLists button')].filter(b => getComputedStyle(b).backgroundColor === ink).length;
        })()""")
        assert bad == 0, path   # no list control has a solid ink background


def test_donts_and_evacuate_open_and_close_from_any_step_without_history_or_step_change(page, app_url):
    inject_listy(page)
    page.goto(app_url + '#/emergency/listy/b')
    for kind, text in (('donts', 'Do not wait'), ('evacuate', 'Evacuate if blue')):
        btn = page.locator(f'#ppLists [data-list="{kind}"]')
        box = btn.bounding_box()
        assert box['height'] >= 56 and box['width'] >= 56 and 0 <= box['y'] < 640, box   # in view without scrolling
        assert text not in page.locator('#player').inner_text()
        hist, url = page.evaluate('history.length'), page.url
        stored = page.evaluate("localStorage.getItem('fk.proto.active')")
        btn.click()
        assert page.locator(f'#player .pp-list[data-list="{kind}"]').is_visible()
        assert text in page.locator('#player .pp-list').inner_text()
        assert btn.get_attribute('aria-expanded') == 'true'
        assert action(page) == 'Second action'
        assert page.evaluate('history.length') == hist and page.url == url
        btn.click()
        assert page.locator('#player .pp-list').count() == 0
        assert btn.get_attribute('aria-expanded') == 'false'
        assert action(page) == 'Second action' and page.url == url and page.evaluate('history.length') == hist
        assert page.evaluate("localStorage.getItem('fk.proto.active')") == stored
    # both can be open at once
    page.click('#ppLists [data-list="donts"]')
    page.click('#ppLists [data-list="evacuate"]')
    assert page.locator('#player .pp-list').count() == 2
    # opening a list pushed no entry, so Android Back leaves the protocol rather than a list
    page.goto(app_url + '#/emergency')
    page.evaluate("FK.protocol.open('listy', 'b')")
    page.click('#ppLists [data-list="donts"]')
    page.go_back()
    expect(page.locator('#player')).to_be_hidden()


def test_list_content_is_escaped_and_close_button_inside_panel_is_big(page, app_url):
    inject_listy(page)
    page.goto(app_url + '#/emergency/listy')
    page.click('#ppLists [data-list="donts"]')
    assert page.locator('#player .pp-list b').count() == 0
    assert 'Do not <b>press</b> here' in page.locator('#player .pp-list').inner_text()
    page.click('#ppLists [data-list="evacuate"]')
    assert page.locator('#player .pp-list i').count() == 0
    assert 'Evacuate <i>now</i> if worse' in page.locator('#player').inner_text()
    close = page.locator('#player .pp-list[data-list="evacuate"] [data-act="list"]')
    assert close.bounding_box()['height'] >= 56
    close.click()
    assert page.locator('#player .pp-list[data-list="evacuate"]').count() == 0


def test_no_list_controls_when_the_protocol_has_no_lists(page, app_url):
    inject_listy(page)
    page.goto(app_url + '#/emergency/bare')
    assert page.locator('#player [data-act="list"]').count() == 0
    assert page.locator('#player .pp-list').count() == 0


def test_user_can_open_and_collapse_the_first_step_list(page, app_url):
    inject_listy(page)
    page.goto(app_url + '#/emergency/listy')
    page.click('#ppLists [data-list="donts"]')
    assert page.locator('#player .pp-list').count() == 1
    page.click('#ppLists [data-list="donts"]')
    assert page.locator('#player .pp-list').count() == 0
    assert action(page) == 'First action'


def test_format_detection_meta_and_no_tel_links_anywhere(page, app_url):
    page.goto(app_url)
    assert page.get_attribute('meta[name="format-detection"]', 'content') == 'telephone=no'
    src = page.request.get(app_url).text()
    assert 'href="tel:' not in src.lower() and "href='tel:" not in src.lower()
    assert page.evaluate("document.querySelectorAll('[href^=\"tel:\" i]').length") == 0
    page.goto(app_url + '#/emergency/choking')
    assert page.evaluate("document.querySelectorAll('[href^=\"tel:\" i]').length") == 0
