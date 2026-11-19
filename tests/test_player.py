import pytest
from playwright.sync_api import expect
import json
import re

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


def go_back_settled(page):
    """Android Back, then wait until the address has changed (instead of a fixed wait)."""
    before = page.url
    page.go_back()
    page.wait_for_function('h => location.href !== h', arg=before, timeout=5000)


def assert_back_leaves_for_good(page):
    """After leaving, one Android Back must not land in a protocol."""
    go_back_settled(page)
    assert not page.locator('#player').is_visible()


def test_header_back_then_android_back_does_not_reenter(page, app_url):
    open_from_home(page, app_url)
    page.click('#player [data-act="next"]')
    page.click('#player [data-act="home"]')
    wait_hash(page, '#/emergency')
    assert not page.locator('#player').is_visible()
    assert page.evaluate('history.length') >= 2
    go_back_settled(page)
    assert '/branchy' not in hash_of(page)
    assert not page.locator('#player').is_visible()


def test_android_back_after_done_does_not_reenter(page, app_url):
    inject(page)
    page.goto(app_url + '#/emergency')
    page.evaluate("FK.protocol.open('drafty')")
    page.click('#player [data-act="done"]')
    wait_hash(page, '#/emergency')
    go_back_settled(page)
    assert 'drafty' not in hash_of(page)
    assert not page.locator('#player').is_visible()


def test_android_back_after_end_protocol_does_not_reenter(page, app_url):
    open_from_home(page, app_url)
    page.click('#player [data-act="next"]')
    page.click('#player [data-act="toggleAll"]')
    page.click('#player [data-act="end"]')
    wait_hash(page, '#/emergency')
    assert page.evaluate('FK.protocol.active()') is None
    go_back_settled(page)
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
    go_back_settled(page)
    assert not page.locator('#player').is_visible()


def test_first_step_back_leaves_player_cleanly(page, app_url):
    open_from_home(page, app_url, 'drafty')
    page.click('#player [data-act="back"]')
    wait_hash(page, '#/emergency')
    go_back_settled(page)
    assert 'drafty' not in hash_of(page)


def test_deep_link_then_header_back_then_android_back_does_not_reenter(page, app_url):
    inject(page)
    page.goto(app_url + '#/emergency/branchy')
    page.click('#player [data-act="next"]')
    page.click('#player [data-act="home"]')
    wait_hash(page, '#/emergency')
    assert not page.locator('#player').is_visible()
    go_back_settled(page)
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
    page.evaluate("window.__gos = 0; const g = history.go.bind(history); history.go = n => { window.__gos++; setTimeout(() => g(n), 150); }; 0")
    page.evaluate("const b = document.querySelector('#player [data-act=\"home\"]'); b.click(); setTimeout(() => b.click(), 0)")
    wait_hash(page, '#/emergency')
    expect(page.locator('#player')).to_be_hidden()
    assert page.evaluate('window.__gos') == 1   # the second tap did not unwind again
    assert page.url.endswith('#/emergency')
    assert page.locator('#tab-emergency').is_visible()


def test_bad_deep_link_repaired_at_boot_is_a_deep_link_entry(page, app_url):
    page.goto(app_url + '#/emergency/bleeding/zzz')
    assert page.url.endswith('#/emergency/bleeding')
    assert action(page) == page.evaluate("FK.protocol.get('bleeding').steps[0].text")   # repaired to the first step
    page.evaluate("window.__gos = 0; const g = history.go.bind(history); history.go = n => { window.__gos++; g(n); }; 0")
    page.click('#player [data-act="home"]')
    wait_hash(page, '#/emergency')
    assert page.evaluate('window.__gos') == 0   # replaced in place: nothing before it to jump to
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


# ---------- Final review fixes ----------

T0 = 1_800_000_000_000
FULL_STORAGE = "Storage.prototype.setItem = function () { throw new DOMException('full', 'QuotaExceededError'); }; 0"
TIMED = {
    'id': 'timed', 'title': 'Timed test', 'category': 'injury', 'reviewed': '2026-11-16', 'sources': [{'name': 'Fixture'}],
    'steps': [
        {'id': 'a', 'text': 'Cool the burn', 'timer': {'seconds': 60, 'label': 'Cooling'}},
        {'id': 'b', 'text': 'Count the rate', 'tool': 'rate'},
        {'id': 'c', 'text': 'Cover it', 'log': 'Burn covered'},
        {'id': 'd', 'text': 'Last step', 'end': True},
    ],
    'notes': ['First <b>note</b>', 'Second note'],
}
OTHER = {'id': 'other', 'title': 'Other test', 'category': 'injury', 'reviewed': '2026-11-16', 'sources': [{'name': 'Fixture'}],
         'steps': [{'id': 'a', 'text': 'Other one'}, {'id': 'b', 'text': 'Other two'}]}


def boot_timed(page, app_url, hash_='#/emergency', clock=True):
    if clock:
        page.clock.install(time=T0 // 1000)
    inject_protocols(page, FIXTURES + [TIMED, OTHER])
    page.goto(app_url + hash_)
    page.wait_for_function('window.FK && FK.protocol && FK.tools && FK.tools.cpr')


def timer_text(page):
    return page.locator('#player .pp-timerval').inner_text()


def start_cooling(page):
    page.evaluate("FK.protocol.open('timed')")
    expect(page.locator('#player .pp-action')).to_have_text('Cool the burn')
    page.click('#player [data-act="timer"]')
    expect(page.locator('#player .pp-timerbar')).to_be_visible()


# Important 2: the acknowledgement works with storage full

def test_advanced_acknowledgement_opens_procedures_when_storage_is_full(page, app_url):
    inject(page)
    page.goto(app_url + '#/emergency/adv')
    expect(page.locator('#player [data-act="ack"]')).to_be_visible()
    page.evaluate(FULL_STORAGE)
    page.click('text=I understand, show procedures')
    expect(page.locator('#player [data-act="start"]')).to_be_visible()
    assert 'Ind one' in page.locator('#player').inner_text()
    page.click('#player [data-act="start"]')
    assert action(page) == 'Adv step one'
    page.go_back()   # and it stays acknowledged for the session
    expect(page.locator('#player [data-act="ack"]')).to_have_count(0)


# Important 3: the step timer belongs to the protocol run

def test_step_timer_survives_opening_and_closing_a_tool(page, app_url):
    boot_timed(page, app_url)
    start_cooling(page)
    page.click('#player [data-act="next"]')
    expect(page.locator('#player .pp-action')).to_have_text('Count the rate')
    assert timer_text(page) == '1:00'
    page.click('#player [data-act="tool"]')
    expect(page).to_have_url(re.compile(r'#/emergency/tool/rate$'))
    page.clock.run_for(10_000)
    page.click('#toolClose')
    expect(page).to_have_url(re.compile(r'#/emergency/timed/b$'))
    expect(page.locator('#player .pp-timerbar')).to_be_visible()
    assert page.locator('#player .pp-timerlabel').inner_text() == 'Cooling'
    assert timer_text(page) == '0:50'
    page.clock.run_for(51_000)
    assert timer_text(page) == 'Done'
    assert 'Cooling finished' in page.inner_text('#ppLive')


def test_step_timer_survives_search_and_next_then_back(page, app_url):
    boot_timed(page, app_url)
    start_cooling(page)
    page.click('#player [data-act="search"]')
    page.wait_for_selector('#searchPane', state='visible')
    page.keyboard.press('Escape')
    page.wait_for_selector('#searchPane', state='hidden')
    page.click('#player [data-act="next"]')
    page.clock.run_for(5_000)
    page.click('#player [data-act="back"]')
    expect(page.locator('#player .pp-action')).to_have_text('Cool the burn')
    expect(page.locator('#player .pp-timerbar')).to_be_visible()
    assert timer_text(page) == '0:55'


def test_step_timer_survives_reload(page, app_url):
    boot_timed(page, app_url)
    start_cooling(page)
    page.clock.run_for(20_000)
    saved = page.evaluate("JSON.parse(localStorage.getItem('fk.proto.active'))")
    assert saved['timer']['label'] == 'Cooling' and saved['timer']['step'] == 'a' and saved['timer']['done'] is False
    page.reload()
    page.wait_for_function('window.FK && FK.protocol')
    expect(page.locator('#player .pp-timerbar')).to_be_visible()
    assert timer_text(page) in ('0:40', '0:39')
    page.clock.run_for(41_000)
    assert timer_text(page) == 'Done'


def test_step_timer_shows_in_home_strip_and_announces_there(page, app_url):
    boot_timed(page, app_url)
    start_cooling(page)
    page.go_back()   # Android Back off the first step: home, the run is not ended
    expect(page).to_have_url(re.compile(r'#/emergency$'))
    row = page.locator('#emActive [data-resume="timed"]')
    expect(row).to_be_visible()
    assert row.inner_text().replace('\n', ' ') == 'Timed test: Cooling 1:00'
    assert row.bounding_box()['height'] >= 56
    page.clock.run_for(12_000)
    assert page.inner_text('#emActive [data-resume="timed"] b') == '0:48'
    page.clock.run_for(49_000)
    assert 'Timed test: Cooling finished' in page.inner_text('#toast')
    assert page.get_attribute('#toast', 'role') == 'status'
    row.click()   # back to the step that started it
    expect(page).to_have_url(re.compile(r'#/emergency/timed(/a)?$'))
    assert action(page) == 'Cool the burn'
    assert timer_text(page) == 'Done'


def test_step_timer_is_stopped_by_header_back_done_and_end(page, app_url):
    boot_timed(page, app_url)
    for how in ('home', 'end', 'done', 'other'):
        start_cooling(page)
        if how == 'home':
            page.click('#player [data-act="home"]')
        elif how == 'end':
            page.click('#player [data-act="toggleAll"]')
            page.click('#player [data-act="end"]')
        elif how == 'done':
            page.evaluate("FK.route.go('/emergency/timed/d')")
            page.click('#player [data-act="done"]')
        else:
            page.go_back()
            expect(page).to_have_url(re.compile(r'#/emergency$'))
            page.evaluate("FK.protocol.open('other')")   # a different protocol ends the run's timer
            expect(page.locator('#player .pp-action')).to_have_text('Other one')
            assert page.evaluate('FK.protocol.timer()') is None, how
            page.click('#player [data-act="home"]')
        expect(page).to_have_url(re.compile(r'#/emergency$'))
        assert page.evaluate('FK.protocol.timer()') is None, how
        assert page.locator('#emActive [data-resume]').count() == 0, how
        page.clock.run_for(70_000)
        assert 'finished' not in page.inner_text('#toast'), how


# Minor 4: one log entry per step per run, with a toast

def test_step_log_written_once_per_run_with_a_toast(page, app_url):
    boot_timed(page, app_url, clock=False)
    page.evaluate("FK.protocol.open('timed', 'c')")
    page.click('#player [data-act="next"]')
    expect(page.locator('#toast')).to_have_text('Logged: Burn covered')
    page.click('#player [data-act="back"]')
    page.click('#player [data-act="next"]')
    page.go_back()   # Android Back over the logged step, then NEXT again
    expect(page.locator('#player .pp-action')).to_have_text('Cover it')
    page.click('#player [data-act="next"]')
    texts = page.evaluate('FK.patients.all()[0].entries.map(e => e.text)')
    assert texts == ['Burn covered']
    cid = page.evaluate('FK.patients.all()[0].id')
    assert page.evaluate("JSON.parse(localStorage.getItem('fk.proto.active')).logged") == {cid: ['c']}   # per casualty
    page.reload()   # the run survives a reload, and so does what it logged
    page.wait_for_function('window.FK && FK.protocol')
    page.evaluate("FK.route.go('/emergency/timed/c')")
    page.click('#player [data-act="next"]')
    assert page.evaluate('FK.patients.all()[0].entries.length') == 1
    page.click('#player [data-act="done"]')   # a new run may log again
    page.evaluate("FK.protocol.open('timed', 'c')")
    page.click('#player [data-act="next"]')
    assert page.evaluate('FK.patients.all()[0].entries.map(e => e.text)') == ['Burn covered', 'Burn covered']


def test_step_log_not_marked_when_the_log_write_fails(page, app_url):
    boot_timed(page, app_url, clock=False)
    page.evaluate("FK.protocol.open('timed', 'c')")
    page.evaluate("window.__n = 0; FK.log = () => { window.__n++; return false; }; 0")
    page.click('#player [data-act="next"]')
    page.click('#player [data-act="back"]')
    page.click('#player [data-act="next"]')
    assert page.evaluate('window.__n') == 2   # not counted as logged, so it is tried again
    assert 'Logged' not in page.inner_text('#toast')


# Important 5: notes in the all-steps view

def test_notes_shown_in_all_steps_view_escaped(page, app_url):
    boot_timed(page, app_url, '#/emergency/timed/all', clock=False)
    sec = page.locator('#player .pp-notes')
    assert sec.locator('h3').inner_text() == 'Notes'
    assert 'First <b>note</b>' in sec.inner_text() and 'Second note' in sec.inner_text()
    assert sec.locator('b').count() == 0
    page.goto(app_url + '#/emergency/branchy/all')   # no notes, no heading
    assert page.locator('#player .pp-notes').count() == 0


# Minor 10: tool button labels come from the tool registry

def test_tool_button_label_is_the_registry_label(page, app_url):
    page.goto(app_url + '#/emergency/bleeding/s5')
    assert page.inner_text('#player [data-act="tool"]') == page.evaluate("FK.tools.label('tq')") == 'Tourniquet timers'


# Minor 9: only well-formed protocols reach the player, home and search

def test_malformed_protocols_are_skipped_everywhere(page, app_url):
    bad = [None, {'id': 'nosteps', 'title': 'Zxqv no steps', 'category': 'injury'},
           {'id': 'emptysteps', 'title': 'Zxqv empty steps', 'category': 'injury', 'steps': []},
           {'id': 'nullstep', 'title': 'Zxqv null step', 'category': 'injury', 'steps': [None]},
           {'id': '', 'title': 'Zxqv blank id', 'category': 'injury', 'steps': [{'id': 'a', 'text': 'x'}]}]
    inject_protocols(page, FIXTURES + bad)
    page.goto(app_url + '#/emergency/nosteps')
    expect(page).to_have_url(re.compile(r'#/emergency$'))
    expect(page.locator('#player')).to_be_hidden()
    assert page.locator('.tabbar').is_visible()
    page.evaluate("location.hash = '#/emergency/emptysteps'")
    expect(page).to_have_url(re.compile(r'#/emergency$'))
    expect(page.locator('#player')).to_be_hidden()
    page.click('#emCats summary[data-cat="injury"]')
    assert 'Zxqv' not in page.inner_text('#emHome')
    assert page.locator('#emCats [data-open]').count() > 0   # the good ones still list
    assert [r['key'] for r in page.evaluate("FK.search.query('zxqv')")] == []
    assert page.evaluate("FK.protocol.get('nullstep')") is None
    assert page.evaluate("FK.protocols().every(p => p && p.steps.length)") is True


# Minor 2: focus goes back to the control that opened the screen

def test_focus_returns_to_opener_after_header_back(page, app_url):
    page.goto(app_url + '#/emergency')
    page.click('#emLife [data-open="bleeding"]')
    expect(page.locator('#player')).to_be_visible()
    page.click('#player [data-act="home"]')
    expect(page).to_have_url(re.compile(r'#/emergency$'))
    page.wait_for_function("document.activeElement && document.activeElement.dataset.open === 'bleeding'")


def test_focus_goes_to_heading_when_opener_is_gone(page, app_url):
    page.goto(app_url + '#/emergency/bleeding')   # deep link: nothing opened it
    page.click('#player [data-act="home"]')
    expect(page).to_have_url(re.compile(r'#/emergency$'))
    page.wait_for_function("document.activeElement && document.activeElement.id === 'title'")
    assert page.inner_text('#title') == 'Emergency'


# R1: the automatic patient log is kept per casualty, and a protocol opened again from outside starts a new run

TQ = 'Tourniquet applied'


def bleeding_home(page, app_url, storage=None):
    inject(page)
    if storage:
        page.add_init_script(
            "if (!sessionStorage.getItem('seeded')) { sessionStorage.setItem('seeded', '1');"
            + ''.join(f"localStorage.setItem('fk.{k}', {json.dumps(json.dumps(v))});" for k, v in storage.items()) + '}')
    page.goto(app_url + '#/emergency')
    page.wait_for_function('window.FK && FK.protocol && FK.patients')


def open_bleeding_from_home(page):
    page.click('#emLife [data-open="bleeding"]')
    expect(page.locator('#player .pp-count')).to_have_text(re.compile(r'^1 of '))


def walk_s1_to_s6(page):
    for act in ['next', 'next', 'yes', 'yes', 'next']:
        page.click(f'#player [data-act="{act}"]')
    expect(page.locator('#player .pp-action')).to_have_text(re.compile(r'^Still bleeding'))


def clear_toast(page):
    page.evaluate("document.querySelector('#toast').textContent = ''; 0")


def entries_of(page):
    return page.evaluate('FK.patients.all().map(p => [p.name, p.entries.map(e => e.text)])')


def android_back_home(page):
    while page.evaluate('location.hash') != '#/emergency':
        go_back_settled(page)
    expect(page.locator('#player')).to_be_hidden()


def test_r1_same_protocol_opened_again_from_home_logs_again(page, app_url):
    bleeding_home(page, app_url)
    open_bleeding_from_home(page)
    walk_s1_to_s6(page)
    expect(page.locator('#toast')).to_have_text('Logged: ' + TQ)
    page.click('#player [data-act="back"]')   # guard: Back then NEXT over the same step logs once
    page.click('#player [data-act="next"]')
    assert entries_of(page) == [['Casualty 1', [TQ]]]
    android_back_home(page)
    clear_toast(page)
    open_bleeding_from_home(page)   # a new run
    walk_s1_to_s6(page)
    expect(page.locator('#toast')).to_have_text('Logged: ' + TQ)
    assert entries_of(page) == [['Casualty 1', [TQ, TQ]]]


def test_r1_second_casualty_made_current_gets_the_entry(page, app_url):
    bleeding_home(page, app_url)
    open_bleeding_from_home(page)
    walk_s1_to_s6(page)
    page.evaluate('FK.patients.create(); 0')   # Casualty 2 is now current
    clear_toast(page)
    page.click('#player [data-act="back"]')   # continue the same run over the same step
    page.click('#player [data-act="next"]')
    expect(page.locator('#toast')).to_have_text('Logged: ' + TQ)
    page.click('#player [data-act="back"]')
    page.click('#player [data-act="next"]')
    assert entries_of(page) == [['Casualty 1', [TQ]], ['Casualty 2', [TQ]]]
    logged = page.evaluate("JSON.parse(localStorage.getItem('fk.proto.active')).logged")
    ids = page.evaluate('FK.patients.all().map(p => p.id)')
    assert logged == {ids[0]: ['s5'], ids[1]: ['s5']}
    android_back_home(page)   # and a re-walk from home logs to Casualty 2 again (new run)
    open_bleeding_from_home(page)
    walk_s1_to_s6(page)
    assert entries_of(page) == [['Casualty 1', [TQ]], ['Casualty 2', [TQ, TQ]]]


def test_r1_reviewer_reproduction_delete_casualty_reload_and_walk_again(page, app_url):
    bleeding_home(page, app_url)
    open_bleeding_from_home(page)
    walk_s1_to_s6(page)
    go_back_settled(page)   # Android Back to s5
    page.evaluate('FK.patients.remove(FK.patients.all()[0].id); 0')
    assert entries_of(page) == []
    page.reload()
    page.wait_for_function('window.FK && FK.protocol && FK.patients')
    page.evaluate("FK.route.go('/emergency')")
    expect(page.locator('#player')).to_be_hidden()
    clear_toast(page)
    open_bleeding_from_home(page)
    walk_s1_to_s6(page)
    expect(page.locator('#toast')).to_have_text('Logged: ' + TQ)
    assert entries_of(page) == [['Casualty 1', [TQ]]]


def test_r1_resume_reload_and_return_from_tool_do_not_relog(page, app_url):
    bleeding_home(page, app_url)
    open_bleeding_from_home(page)
    walk_s1_to_s6(page)
    page.click('#player [data-act="home"]')   # leave, then Resume
    expect(page.locator('#player')).to_be_hidden()
    page.click('#emResume [data-resume="bleeding"]')
    expect(page.locator('#player .pp-action')).to_have_text(re.compile(r'^Still bleeding'))
    page.click('#player [data-act="back"]')
    page.click('#player [data-act="next"]')
    assert entries_of(page) == [['Casualty 1', [TQ]]]
    page.click('#player [data-act="back"]')   # reload mid-protocol
    page.reload()
    page.wait_for_function('window.FK && FK.protocol && FK.patients')
    expect(page.locator('#player .pp-action')).to_have_text(re.compile(r'^Put a tourniquet'))
    page.click('#player [data-act="next"]')
    assert entries_of(page) == [['Casualty 1', [TQ]]]
    page.click('#player [data-act="back"]')   # out to a tool and back
    page.click('#player [data-act="tool"]')
    expect(page.locator('#toolPane')).to_be_visible()
    page.click('#toolClose')
    expect(page.locator('#player .pp-action')).to_have_text(re.compile(r'^Put a tourniquet'))
    page.click('#player [data-act="next"]')
    page.click('#player [data-act="back"]')   # out to search and back
    page.click('#player [data-act="search"]')
    go_back_settled(page)
    expect(page.locator('#player .pp-action')).to_have_text(re.compile(r'^Put a tourniquet'))
    page.click('#player [data-act="next"]')
    assert entries_of(page) == [['Casualty 1', [TQ]]]


@pytest.mark.parametrize('logged', [['s5'], 's5', None, {'junk': 5, 'x': ['s5', 3], '': 'a'}, 7])
def test_r1_old_or_malformed_logged_record_loads_and_logs(page, app_url, logged):
    rec = {'id': 'bleeding', 'step': 's5', 'started': 1}
    if logged is not None:
        rec['logged'] = logged
    bleeding_home(page, app_url, storage={'proto.active': rec, 'patients': [
        {'id': 'x', 'name': 'Casualty 1', 'created': 1, 'used': 1, 'entries': []}]})
    page.evaluate("FK.route.go('/emergency/bleeding/s5')")   # Resume-like: the same run
    expect(page.locator('#player .pp-action')).to_have_text(re.compile(r'^Put a tourniquet'))
    page.click('#player [data-act="next"]')
    # an old flat list belongs to no casualty; junk is ignored
    expected = [] if isinstance(logged, dict) else [TQ]
    assert entries_of(page) == [['Casualty 1', expected]]


def test_r1_new_run_from_home_stops_the_same_protocols_step_timer(page, app_url):
    boot_timed(page, app_url)
    start_cooling(page)
    go_back_settled(page)   # Android Back keeps the run and its timer
    expect(page).to_have_url(re.compile(r'#/emergency$'))
    assert page.evaluate('FK.protocol.timer()')['label'] == 'Cooling'
    old = page.evaluate("JSON.parse(localStorage.getItem('fk.proto.active')).started")
    page.clock.run_for(5000)
    page.evaluate("FK.protocol.open('timed')")   # opened again from outside: a new run
    expect(page.locator('#player .pp-action')).to_have_text('Cool the burn')
    assert page.evaluate('FK.protocol.timer()') is None
    expect(page.locator('#player .pp-timerbar')).to_be_hidden()
    rec = page.evaluate("JSON.parse(localStorage.getItem('fk.proto.active'))")
    assert rec['step'] == 'a' and 'timer' not in rec and 'logged' not in rec and rec['started'] >= old + 5000


# ---------- Task 11: timer-stopped notice; no stale finished timer at startup ----------

SPY_TOASTS = "(() => { window.__toasts = []; const t = FK.toast; FK.toast = m => { window.__toasts.push(m); return t(m); }; })(); 0"
SPY_VIBRATE = "window.__vibes = []; navigator.vibrate = p => { window.__vibes.push(p); return true; };"


def stopped_toasts(page):
    return [m for m in page.evaluate('window.__toasts') if m.startswith('Timer stopped')]


def test_t11_discarding_a_running_timer_says_so_once(page, app_url):
    boot_timed(page, app_url)
    page.evaluate(SPY_TOASTS)
    # a different protocol opened while the timer runs
    start_cooling(page)
    go_back_settled(page)
    expect(page).to_have_url(re.compile(r'#/emergency$'))
    page.evaluate("FK.protocol.open('other')")
    expect(page.locator('#player .pp-action')).to_have_text('Other one')
    assert stopped_toasts(page) == ['Timer stopped: Timed test']
    assert page.evaluate('FK.protocol.timer()') is None
    # the same protocol restarted from its home tile
    page.click('#player [data-act="home"]')
    expect(page).to_have_url(re.compile(r'#/emergency$'))
    page.evaluate('window.__toasts = []')
    start_cooling(page)
    go_back_settled(page)
    expect(page).to_have_url(re.compile(r'#/emergency$'))
    page.click('#emHome [data-open="timed"]')
    expect(page.locator('#player .pp-action')).to_have_text('Cool the burn')
    assert stopped_toasts(page) == ['Timer stopped: Timed test']
    assert page.evaluate('FK.protocol.timer()') is None


def test_t11_resume_and_finished_timers_show_no_stopped_toast(page, app_url):
    boot_timed(page, app_url)
    page.evaluate(SPY_TOASTS)
    start_cooling(page)
    go_back_settled(page)
    expect(page).to_have_url(re.compile(r'#/emergency$'))
    page.click('#emResume [data-resume="timed"]')   # Resume keeps the run and its timer
    expect(page.locator('#player .pp-action')).to_have_text('Cool the burn')
    assert stopped_toasts(page) == []
    assert page.evaluate('FK.protocol.timer()')['label'] == 'Cooling'
    assert timer_text(page) != 'Done'
    # a timer that already finished is not running: discarding it is silent
    page.clock.run_for(61_000)
    assert timer_text(page) == 'Done'
    go_back_settled(page)
    page.evaluate("FK.protocol.open('other')")
    expect(page.locator('#player .pp-action')).to_have_text('Other one')
    assert stopped_toasts(page) == []


def seed_timed_run(page, end, done=False):
    rec = {'id': 'timed', 'step': 'a', 'started': T0 - 90_000,
           'timer': {'step': 'a', 'label': 'Cooling', 'end': end, 'done': done}}
    page.add_init_script(f"localStorage.setItem('fk.proto.active', {json.dumps(json.dumps(rec))});")


def test_t11_timer_that_ended_while_closed_is_over_without_vibration_or_done_entry(page, app_url):
    page.add_init_script(SPY_VIBRATE)
    seed_timed_run(page, T0 - 30_000)
    boot_timed(page, app_url)
    assert page.evaluate('window.__vibes') == []
    assert page.evaluate('FK.protocol.timer()') is None
    expect(page.locator('#emActive [data-resume="timed"]')).to_have_count(0)
    assert 'Done' not in page.inner_text('#emActive')
    assert 'finished' not in page.inner_text('#toast')
    page.clock.run_for(2_000)
    assert page.evaluate('window.__vibes') == []


def test_t11_timer_still_running_at_startup_is_restored_and_vibrates_when_it_ends(page, app_url):
    page.add_init_script(SPY_VIBRATE)
    seed_timed_run(page, T0 + 20_000)
    boot_timed(page, app_url)
    assert page.evaluate('FK.protocol.timer()')['label'] == 'Cooling'
    assert page.evaluate('window.__vibes') == []
    page.clock.run_for(21_000)
    assert page.evaluate('window.__vibes') == [[300, 150, 300]]
    assert page.evaluate('FK.protocol.timer()')['done'] is True


def test_no_shipped_protocol_title_runs_under_the_pin_star_at_360(page, app_url):
    # Final review I4: "Radiation decontamination (cleaning off fallout)" ran "decontamin|" under the pin star.
    page.add_init_script("localStorage.setItem('fk.advAck', 'true')")
    page.goto(app_url + '#/emergency')
    page.wait_for_function('window.FK && FK.protocols')
    ids = page.evaluate('FK.protocols().map(p => p.id)')
    assert 'radiation-decontamination' in ids
    bad = []
    for pid in ids:
        page.goto(app_url + '#/emergency/' + pid)
        page.wait_for_selector('#ppTitle')
        r = page.evaluate("""(() => { const t = document.getElementById('ppTitle'), star = t.parentElement.querySelector('[data-act="pin"]');
            const range = document.createRange(); range.selectNodeContents(t);
            const right = Math.max(...[...range.getClientRects()].map(x => x.right));
            return [t.textContent, right, star.getBoundingClientRect().left, t.scrollWidth - t.clientWidth]; })()""")
        if r[1] > r[2] or r[3] > 0:
            bad.append(r)
    assert bad == [], bad


def test_snakebite_title_stays_on_one_line_at_360(page, app_url):
    # Re-review R2: with overflow-wrap:anywhere and an 8px header gap the 80px title column broke it as "Snakebit / e";
    # v7.3 showed it on one line. The header gap is 7.5px, the smallest that keeps every v7.3 line break (final fix report).
    page.goto(app_url + '#/emergency/snakebite')
    page.wait_for_selector('#ppTitle')
    r = page.evaluate("""(() => { const t = document.getElementById('ppTitle'), range = document.createRange(); range.selectNodeContents(t);
        const tops = new Set([...range.getClientRects()].map(x => Math.round(x.top)));
        const star = t.parentElement.querySelector('[data-act="pin"]').getBoundingClientRect().left;
        return [t.textContent, tops.size, Math.max(...[...range.getClientRects()].map(x => x.right)) <= star]; })()""")
    assert r == ['Snakebite', 1, True], r
