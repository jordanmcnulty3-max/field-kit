import json

from .conftest import inject_protocols

T0 = 1_800_000_000_000   # fixed fake clock so stored start times are exact


def proto(pid, title, category='life', **extra):
    p = {'id': pid, 'title': title, 'category': category, 'reviewed': '2026-11-16', 'sources': [{'name': 'Fixture'}],
         'steps': [{'id': 's1', 'text': 'One.'}, {'id': 's2', 'text': 'Two.', 'tool': 'tq'}, {'id': 's3', 'text': 'Three.'}]}
    p.update(extra)
    return p


FIXTURES = [proto('bleeding', 'Severe bleeding'), proto('cpr-adult', 'CPR adult'),
            proto('cpr-child', 'CPR child', coach={'compressions': 15, 'breaths': 2})]


def boot(page, app_url, storage=None, hash_='#/emergency', fixtures=FIXTURES, clock=True, strip_apis=False, init='', only=False):
    if clock:
        page.clock.install(time=T0 // 1000)   # Python API takes seconds
    inject_protocols(page, fixtures, only)
    if strip_apis:
        page.add_init_script("""
          delete window.AudioContext; delete window.webkitAudioContext;
          delete Navigator.prototype.vibrate; delete Navigator.prototype.wakeLock;""")
    if init:
        page.add_init_script(init)
    seed = {'advAck': True, **(storage or {})}
    page.add_init_script(
        "if (!sessionStorage.getItem('seeded')) { sessionStorage.setItem('seeded', '1');"
        + ''.join(f"localStorage.setItem('fk.{k}', {json.dumps(json.dumps(v))});" for k, v in seed.items()) + '}')
    page.goto(app_url + hash_)
    page.wait_for_function('window.FK && FK.tools && FK.tools.cpr')


def tool_open(page):
    return page.locator('#toolPane').is_visible()


def count_text(page):
    return page.inner_text('#cprCount')


# ---------- Tourniquet timers ----------

def test_v5_running_tourniquet_timer_survives_update(page, app_url):
    boot(page, app_url, storage={'tq': [{'id': 'abc123', 'limb': 'Left leg', 'start': T0 - 872_000}]}, hash_='#/emergency/tool/tq')
    assert page.inner_text('#tqList .timer b') == '0:14:32'
    assert 'Left leg' in page.inner_text('#tqList .timer')
    assert page.evaluate('FK.tools.tq.active()') == [{'id': 'abc123', 'limb': 'Left leg', 'start': T0 - 872_000}]
    assert json.loads(page.evaluate("localStorage.getItem('fk.tq')")) == [{'id': 'abc123', 'limb': 'Left leg', 'start': T0 - 872_000}]


def test_start_timer_adds_row_and_persists(page, app_url):
    boot(page, app_url, hash_='#/emergency/tool/tq')
    page.evaluate("window.logged = []; FK.log = m => logged.push(m); 0")
    page.click('[data-limb="Right arm"]')
    assert page.locator('#tqList .timer').count() == 1
    assert 'Right arm' in page.inner_text('#tqList .timer')
    assert page.evaluate('logged') == ['Tourniquet applied: Right arm']
    page.clock.run_for(5000)
    assert page.inner_text('#tqList .timer b') == '0:00:05'
    saved = json.loads(page.evaluate("localStorage.getItem('fk.tq')"))
    assert len(saved) == 1 and saved[0]['limb'] == 'Right arm' and T0 <= saved[0]['start'] < T0 + 5000
    page.reload()
    page.wait_for_function('window.FK && FK.tools && FK.tools.tq')
    assert page.evaluate('FK.tools.tq.active().length') == 1


def test_start_without_fk_log_does_not_fail(page, app_url):
    boot(page, app_url, hash_='#/emergency/tool/tq')
    page.evaluate('delete FK.log')   # the patient log defines it; the timers must work without it
    assert page.evaluate('typeof FK.log') == 'undefined'
    page.click('[data-limb="Left leg"]')
    assert page.locator('#tqList .timer').count() == 1


def test_clear_needs_inline_second_tap_and_no_browser_dialog(page, app_url):
    boot(page, app_url, storage={'tq': [{'id': 'a', 'limb': 'Left arm', 'start': T0 - 1000}]}, hash_='#/emergency/tool/tq')
    dialogs = []
    page.on('dialog', lambda d: (dialogs.append(d.message), d.dismiss()))
    page.click('#tqList [data-act="clear"]')
    assert 'Only clear once responders have the time' in page.inner_text('#tqList .timer')
    assert page.evaluate('FK.tools.tq.active().length') == 1
    page.clock.run_for(800)
    page.click('#tqList [data-act="confirm"]')
    assert page.locator('#tqList .timer').count() == 0
    assert json.loads(page.evaluate("localStorage.getItem('fk.tq')")) == []
    assert dialogs == []


def test_clear_confirmation_expires(page, app_url):
    boot(page, app_url, storage={'tq': [{'id': 'a', 'limb': 'Left arm', 'start': T0 - 1000}]}, hash_='#/emergency/tool/tq')
    page.click('#tqList [data-act="clear"]')
    page.clock.run_for(5100)
    assert page.locator('#tqList [data-act="clear"]').count() == 1
    assert page.evaluate('FK.tools.tq.active().length') == 1


def test_active_timers_strip_on_home_links_to_tool(page, app_url):
    boot(page, app_url, storage={'tq': [{'id': 'a', 'limb': 'Left leg', 'start': T0 - 872_000}]})
    s = page.locator('#emActive button')
    assert s.count() == 1 and s.inner_text().replace('\n', ' ') == 'TQ left leg 0:14:32'
    page.clock.run_for(3000)
    assert page.inner_text('#emActive b') == '0:14:35'
    assert s.bounding_box()['height'] >= 56
    s.click()
    page.wait_for_function("location.hash === '#/emergency/tool/tq'")
    assert tool_open(page) and page.locator('#tqList .timer').count() == 1


def test_strip_empty_without_timers_and_updates_stop_when_page_hidden(page, app_url):
    boot(page, app_url)
    assert page.locator('#emActive button').count() == 0
    page.evaluate("""FK.store.set('tq', [{id: 'a', limb: 'Other', start: Date.now() - 1000}]); location.reload()""")
    page.wait_for_function('window.FK && FK.tools && FK.tools.tq')
    page.clock.run_for(2000)
    assert page.inner_text('#emActive b') == '0:00:03'
    page.evaluate("""Object.defineProperty(document, 'hidden', {configurable: true, get: () => true});
        document.dispatchEvent(new Event('visibilitychange'))""")
    page.clock.run_for(5000)
    assert page.inner_text('#emActive b') == '0:00:03'
    page.evaluate("""Object.defineProperty(document, 'hidden', {configurable: true, get: () => false});
        document.dispatchEvent(new Event('visibilitychange'))""")
    page.clock.run_for(1000)
    assert page.inner_text('#emActive b') == '0:00:09'


# ---------- Overlay and navigation ----------

def test_tools_category_buttons_open_overlay_and_android_back_closes(page, app_url):
    boot(page, app_url)
    page.click('#emCats summary[data-cat="tools"]')
    page.click('#emCats [data-tool="cpr"]')
    page.wait_for_function("location.hash === '#/emergency/tool/cpr'")
    assert tool_open(page) and page.inner_text('#toolTitle') == 'CPR coach'
    page.go_back()
    page.wait_for_function("location.hash === '#/emergency'")
    assert not tool_open(page)
    assert page.locator('#emHome').is_visible()


def test_close_button_returns_home_when_opened_from_home(page, app_url):
    boot(page, app_url)
    page.evaluate("FK.tools.start('tq')")
    page.wait_for_function("location.hash === '#/emergency/tool/tq'")
    page.click('#toolClose')
    page.wait_for_function("location.hash === '#/emergency'")
    assert not tool_open(page)


def test_tool_from_protocol_returns_to_same_step_by_close_and_by_back(page, app_url):
    boot(page, app_url, hash_='#/emergency/bleeding/s2')
    page.click('[data-act="tool"]')
    page.wait_for_function("location.hash === '#/emergency/tool/tq'")
    assert tool_open(page)
    page.click('#toolClose')
    page.wait_for_function("location.hash === '#/emergency/bleeding/s2'")
    assert not tool_open(page) and 'Two.' in page.inner_text('#ppAction')
    page.click('[data-act="tool"]')
    page.wait_for_function("location.hash === '#/emergency/tool/tq'")
    page.go_back()
    page.wait_for_function("location.hash === '#/emergency/bleeding/s2'")
    assert not tool_open(page) and 'Two.' in page.inner_text('#ppAction')


def test_reloaded_tool_address_closes_to_home(page, app_url):
    boot(page, app_url, hash_='#/emergency/tool/tq')
    assert tool_open(page)
    page.click('#toolClose')
    page.wait_for_function("location.hash === '#/emergency'")
    assert not tool_open(page)


def test_unknown_or_unbuilt_tool_does_nothing(page, app_url):
    boot(page, app_url)
    assert page.evaluate("FK.tools.start('ghost')") is False
    assert page.evaluate("FK.tools.start('phantom')") is False
    assert page.evaluate("FK.tools.start('../x')") is False
    assert page.evaluate("location.hash") == '#/emergency' and not tool_open(page)
    page.goto(app_url + '#/emergency/tool/ghost')
    page.wait_for_function("location.hash === '#/emergency'")
    assert not tool_open(page)


def test_register_adds_a_tool_that_can_open(page, app_url):
    boot(page, app_url)
    page.evaluate("""window.stopped = 0;
        FK.tools.register('gauge', { label: 'Gauge', render(el, opts) { el.textContent = 'hello ' + (opts.n || ''); }, stop() { stopped++; } })""")
    assert page.evaluate("FK.tools.start('gauge', { n: 7 })") is True
    page.wait_for_function("location.hash === '#/emergency/tool/gauge'")
    assert page.inner_text('#toolBody') == 'hello 7' and page.inner_text('#toolTitle') == 'Gauge'
    page.go_back()
    page.wait_for_function("location.hash === '#/emergency'")
    assert page.evaluate('stopped') == 1


def test_opening_a_tool_adds_recent_and_pinned_and_recent_render_and_open_it(page, app_url):
    boot(page, app_url)
    page.evaluate("FK.tools.start('tq')")
    page.wait_for_function("location.hash === '#/emergency/tool/tq'")
    assert page.evaluate('FK.recent.all()') == ['t:tq']
    page.click('#toolPin')
    assert page.evaluate('FK.pins.all()') == ['t:tq']
    page.click('#toolClose')
    page.wait_for_function("location.hash === '#/emergency'")
    assert page.locator('#emPinned [data-tool="tq"]').inner_text() == 'Tourniquet timers'
    assert page.locator('#emRecent [data-tool="tq"]').count() == 1
    page.click('#emRecent [data-tool="tq"]')
    page.wait_for_function("location.hash === '#/emergency/tool/tq'")
    assert tool_open(page)


def test_pinned_key_for_unbuilt_tool_is_not_rendered(page, app_url):
    boot(page, app_url, storage={'pins': ['t:ghost', 't:cpr']})
    assert [b.get_attribute('data-tool') for b in page.locator('#emPinned [data-tool]').all()] == ['cpr']


# ---------- CPR coach ----------

def start_cpr(page, app_url, **kw):
    boot(page, app_url, hash_='#/emergency/tool/cpr', **kw)
    page.click('#cprBtn')


def test_cpr_state_is_a_pure_function_of_elapsed_time(page, app_url):
    boot(page, app_url)
    st = lambda ms, **c: page.evaluate('([ms, c]) => FK.tools.cpr.state(ms, { compressions: 30, breaths: 2, compressionOnly: false, ...c })', [ms, c])
    assert st(0)['count'] == 1 and st(0)['phase'] == 'compress' and st(0)['cycle'] == 1
    assert st(545)['count'] == 1 and st(546)['count'] == 2          # 110 per minute = 545.45 ms per beat
    assert st(15_819)['count'] == 30 and st(16_300)['phase'] == 'compress'
    assert st(16_400)['phase'] == 'breaths' and st(20_300)['phase'] == 'breaths'
    after = st(20_400)
    assert after['phase'] == 'compress' and after['count'] == 1 and after['cycle'] == 2
    long = st(1_000_000)   # 49 full cycles of 20.36 s, then 2.1 s into the 50th
    assert long['cycle'] == 50 and long['beats'] == 49 * 30 + long['count']
    only = st(60_000, compressionOnly=True)
    assert only['phase'] == 'compress' and only['beats'] == 111   # beat 1 sounds at 0 s, so 110 per minute means beat 111 lands at 60 s
    assert st(0, compressions=15)['phase'] == 'compress' and st(8_300, compressions=15)['phase'] == 'breaths'


def test_cpr_counts_to_30_then_prompts_breaths(page, app_url):
    start_cpr(page, app_url)
    assert count_text(page) == '1'
    page.clock.run_for(2000)
    assert count_text(page) == '4'
    page.clock.run_for(14_000)                   # 16 s: the 30th compression, no prompt yet
    assert count_text(page) == '30'
    page.clock.run_for(1000)                     # 17 s: breaths hold
    assert count_text(page) == '2 breaths'
    page.clock.run_for(3000)                     # 20 s: still holding
    assert count_text(page) == '2 breaths'
    page.clock.run_for(600)                      # 20.6 s: compressions resumed
    assert count_text(page) == '1' and page.inner_text('#cprCycle') == 'Cycle 2'


def test_cpr_count_follows_elapsed_time_when_timers_are_throttled(page, app_url):
    start_cpr(page, app_url)
    page.clock.fast_forward(17_000)              # background tab: the interval never fired in between
    page.clock.run_for(60)
    assert count_text(page) == '2 breaths'
    page.clock.fast_forward(5_000)
    page.clock.run_for(60)
    assert page.inner_text('#cprCycle') == 'Cycle 2'


def test_cpr_compression_only_never_prompts_breaths(page, app_url):
    boot(page, app_url, hash_='#/emergency/tool/cpr')
    page.click('#cprOnly')
    page.click('#cprBtn')
    seen = set()
    for _ in range(80):
        page.clock.run_for(500)
        seen.add(count_text(page))
    assert not any('breath' in s for s in seen)
    assert seen >= {str(n) for n in range(1, 31)}
    assert page.inner_text('#cprCycle') == 'Cycle 3'


def test_cpr_swap_prompt_at_120_seconds_of_compressions(page, app_url):
    boot(page, app_url, hash_='#/emergency/tool/cpr')
    page.click('#cprOnly')
    page.click('#cprBtn')
    page.clock.run_for(118_000)
    assert page.locator('#cprSwap').is_hidden()
    page.clock.run_for(3000)
    assert page.locator('#cprSwap').is_visible() and 'Swap rescuers' in page.inner_text('#cprSwap')
    page.click('#cprSwapped')
    assert page.locator('#cprSwap').is_hidden()
    page.clock.run_for(118_000)
    assert page.locator('#cprSwap').is_hidden()
    page.clock.run_for(3000)
    assert page.locator('#cprSwap').is_visible()


def test_cpr_swap_counts_only_compression_time_when_breaths_are_given(page, app_url):
    start_cpr(page, app_url)
    page.clock.run_for(130_000)                  # 130 s wall clock is about 105 s of compressions
    assert page.locator('#cprSwap').is_hidden()
    page.clock.run_for(25_000)
    assert page.locator('#cprSwap').is_visible()


def test_cpr_modes_and_open_steps(page, app_url):
    boot(page, app_url, hash_='#/emergency/tool/cpr', only=True)
    assert [b.inner_text() for b in page.locator('[data-mode]').all()] == ['Adult', 'Child', 'Infant']
    assert page.locator('[data-mode="adult"]').get_attribute('aria-pressed') == 'true'
    page.click('[data-mode="infant"]')
    assert page.locator('#cprSteps').is_hidden()   # no cpr-infant protocol in this fixture set
    page.click('[data-mode="child"]')
    page.click('#cprSteps')
    page.wait_for_function("location.hash === '#/emergency/cpr-child'")
    page.go_back()
    page.wait_for_function("location.hash === '#/emergency/tool/cpr'")
    assert tool_open(page)


def test_cpr_opened_from_its_protocol_preselects_mode_and_open_steps_goes_back(page, app_url):
    steps = [{'id': 's1', 'text': 'One.'}, {'id': 's2', 'text': 'Two.', 'tool': 'cpr'}]
    boot(page, app_url, hash_='#/emergency/cpr-child/s2', fixtures=[proto('cpr-child', 'CPR child', steps=steps)])
    page.click('[data-act="tool"]')
    page.wait_for_function("location.hash === '#/emergency/tool/cpr'")
    assert page.locator('[data-mode="child"]').get_attribute('aria-pressed') == 'true'
    page.click('#cprSteps')
    page.wait_for_function("location.hash === '#/emergency/cpr-child/s2'")


def test_cpr_ratio_comes_from_protocol_coach_object(page, app_url):
    boot(page, app_url, hash_='#/emergency/tool/cpr')
    page.click('[data-mode="child"]')
    page.click('#cprBtn')
    page.clock.run_for(8000)                     # 15 compressions take 8.2 s
    assert count_text(page) == '15'
    page.clock.run_for(1000)
    assert count_text(page) == '2 breaths'


def test_cpr_malformed_coach_falls_back_to_30_2(page, app_url):
    boot(page, app_url, hash_='#/emergency/tool/cpr', fixtures=[proto('cpr-adult', 'CPR adult', coach={'compressions': 'x', 'breaths': 2})])
    page.click('#cprBtn')
    page.clock.run_for(16_000)
    assert count_text(page) == '30'


def test_cpr_works_without_audio_vibrate_wakelock(page, app_url):
    boot(page, app_url, hash_='#/emergency/tool/cpr', strip_apis=True)
    assert page.evaluate("[typeof AudioContext, typeof webkitAudioContext, typeof navigator.vibrate, typeof navigator.wakeLock]") == ['undefined'] * 4
    page.click('#cprBtn')
    page.clock.run_for(20_600)
    assert count_text(page) == '1' and page.inner_text('#cprCycle') == 'Cycle 2'
    page.click('#cprBtn')
    page.clock.run_for(800)
    page.click('#cprBtn')
    assert page.inner_text('#cprBtn') == 'Start'
    page.click('#toolClose')
    page.wait_for_function("location.hash === '#/emergency'")


def test_cpr_touch_targets_at_least_56px(page, app_url):
    boot(page, app_url, hash_='#/emergency/tool/cpr')
    heights = page.evaluate("[...document.querySelectorAll('#toolPane button')].filter(e => e.offsetParent !== null).map(e => e.getBoundingClientRect().height)")
    assert heights and min(heights) >= 56


# ---------- Review fixes ----------

def test_clear_confirm_ignores_a_bounced_second_tap(page, app_url):
    boot(page, app_url, storage={'tq': [{'id': 'a', 'limb': 'Left arm', 'start': T0 - 1000}]}, hash_='#/emergency/tool/tq')
    page.evaluate("""document.querySelector('#tqList [data-act="clear"]').click();
        document.querySelector('#tqList [data-act="confirm"]').click(); 0""")
    assert page.evaluate('FK.tools.tq.active().length') == 1
    page.clock.run_for(800)
    page.click('#tqList [data-act="confirm"]')
    assert page.evaluate('FK.tools.tq.active().length') == 0


def test_limb_is_a_required_choice_one_tap_each_with_big_buttons(page, app_url):
    boot(page, app_url, hash_='#/emergency/tool/tq')
    limbs = [b.get_attribute('data-limb') for b in page.locator('#toolBody [data-limb]').all()]
    assert limbs == ['Left arm', 'Right arm', 'Left leg', 'Right leg', 'Other']
    assert page.locator('#toolBody select').count() == 0
    assert page.evaluate('FK.tools.tq.active().length') == 0
    assert min(b['height'] for b in [x.bounding_box() for x in page.locator('#toolBody [data-limb]').all()]) >= 56
    page.click('[data-limb="Left leg"]')
    assert [t['limb'] for t in page.evaluate('FK.tools.tq.active()')] == ['Left leg']


def test_stale_open_options_do_not_apply_to_the_next_open(page, app_url):
    boot(page, app_url)
    page.evaluate("FK.tools.start('cpr')")
    page.wait_for_function("location.hash === '#/emergency/tool/cpr'")
    page.evaluate("FK.tools.start('cpr', { mode: 'child' })")   # already open: nothing to do
    page.click('#toolClose')
    page.wait_for_function("location.hash === '#/emergency'")
    page.evaluate("FK.route.go('/emergency/tool/cpr')")     # opened by address, not through start(): no options at all
    assert page.locator('[data-mode="adult"]').get_attribute('aria-pressed') == 'true'


def running_cpr(page, app_url, **kw):
    boot(page, app_url, **kw)
    page.evaluate("FK.tools.start('cpr')")
    page.wait_for_function("location.hash === '#/emergency/tool/cpr'")
    page.click('#cprBtn')


def reopen_cpr(page):
    page.evaluate("FK.tools.start('cpr')")
    page.wait_for_function("location.hash === '#/emergency/tool/cpr'")


def test_cpr_keeps_running_when_overlay_closes_by_every_route(page, app_url):
    running_cpr(page, app_url)
    page.clock.run_for(2000)
    for how in ('back', 'close', 'escape'):
        before = count_text(page)
        if how == 'back':
            page.go_back()
        elif how == 'close':
            page.click('#toolClose')
        else:
            page.keyboard.press('Escape')
        page.wait_for_function("location.hash === '#/emergency'")
        assert not tool_open(page)
        page.clock.run_for(2000)
        reopen_cpr(page)
        assert page.inner_text('#cprBtn') == 'Stop', how
        assert count_text(page) != before and page.inner_text('#cprCycle').startswith('Cycle'), how
    assert page.evaluate("FK.tools.cpr.running()") is True


def test_cpr_reopened_shows_live_state_not_a_fresh_one(page, app_url):
    running_cpr(page, app_url)
    page.click('#toolClose')
    page.wait_for_function("location.hash === '#/emergency'")
    page.clock.run_for(22_000)
    reopen_cpr(page)
    assert page.inner_text('#cprCycle') == 'Cycle 2'


def test_cpr_stop_is_two_step_with_ignore_window_and_revert(page, app_url):
    running_cpr(page, app_url)
    page.clock.run_for(800)
    page.click('#cprBtn')
    assert page.inner_text('#cprBtn') == 'Confirm stop'
    page.evaluate("document.querySelector('#cprBtn').click(); 0")   # bounced second tap
    assert page.evaluate("FK.tools.cpr.running()") is True
    page.clock.run_for(5100)
    assert page.inner_text('#cprBtn') == 'Stop'
    page.click('#cprBtn')
    page.clock.run_for(800)
    page.click('#cprBtn')
    assert page.evaluate("FK.tools.cpr.running()") is False
    assert page.inner_text('#cprBtn') == 'Start' and count_text(page) == '0'


def test_cpr_mode_toggles_stay_disabled_while_running(page, app_url):
    running_cpr(page, app_url)
    assert page.locator('#cprOnly').is_disabled() and page.locator('[data-mode="child"]').is_disabled()


def test_active_strip_shows_running_cpr_and_opens_the_tool(page, app_url):
    running_cpr(page, app_url)
    page.click('#toolClose')
    page.wait_for_function("location.hash === '#/emergency'")
    page.clock.run_for(22_000)
    b = page.locator('#emActive button')
    assert b.count() == 1 and b.inner_text().strip().startswith('CPR running, cycle 2')   # headless may also add the wake-lock warning
    b.click()
    page.wait_for_function("location.hash === '#/emergency/tool/cpr'")
    assert page.inner_text('#cprBtn') == 'Stop'


def test_cpr_keeps_running_while_steps_are_open_and_back_returns_to_live_tool(page, app_url):
    running_cpr(page, app_url)
    page.click('#cprSteps')
    page.wait_for_function("location.hash === '#/emergency/cpr-adult'")
    page.clock.run_for(22_000)
    assert page.evaluate("FK.tools.cpr.running()") is True
    page.go_back()
    page.wait_for_function("location.hash === '#/emergency/tool/cpr'")
    assert page.inner_text('#cprBtn') == 'Stop' and page.inner_text('#cprCycle') == 'Cycle 2'


NOTICE = 'This phone may turn its screen off and stop the clicks. Keep the screen awake.'


def test_cpr_warns_when_wake_lock_is_missing(page, app_url):
    boot(page, app_url, hash_='#/emergency/tool/cpr', strip_apis=True)
    assert page.locator('#cprWake').is_hidden()
    page.click('#cprBtn')
    assert page.inner_text('#cprWake') == NOTICE


def test_cpr_warns_when_wake_lock_request_is_rejected(page, app_url):
    boot(page, app_url, hash_='#/emergency/tool/cpr', init="""
        Object.defineProperty(navigator, 'wakeLock', { configurable: true, value: { request: () => Promise.reject(new DOMException('no', 'NotAllowedError')) } });""")
    page.click('#cprBtn')
    page.wait_for_function("document.querySelector('#cprWake') && !document.querySelector('#cprWake').hidden")
    assert page.inner_text('#cprWake') == NOTICE


FAKE_AUDIO = """
  (() => {
    window.__starts = []; window.__oscs = [];
    const dest = { dest: true };
    const now = () => performance.now() / 1000;
    const node = () => ({ out: null, connect(n) { this.out = n; return n; }, disconnect() { this.out = null; } });
    window.AudioContext = class {
      constructor() { this.state = 'running'; }
      get currentTime() { return now(); }
      resume() { return Promise.resolve(); }
      get destination() { return dest; }
      createGain() { return Object.assign(node(), { gain: { setValueAtTime() {}, exponentialRampToValueAtTime() {} } }); }
      createOscillator() {
        const o = Object.assign(node(), { frequency: {}, when: null, stopAt: null,
          start(w) { this.when = w; window.__starts.push([w, now(), this.frequency.value]); },
          stop(w) { this.stopAt = w === undefined ? now() : w; } });
        window.__oscs.push(o); return o;
      }
    };
    // Starts later than `after` (seconds) that would still be heard: wired to the speaker and not stopped first.
    window.__audibleAfter = after => window.__oscs.filter(o => {
      let n = o, hops = 0; while (n && !n.dest && hops++ < 10) n = n.out;
      return n && n.dest && o.when > after && !(o.stopAt !== null && o.stopAt <= o.when);
    }).map(o => o.when);
  })();"""


def test_cpr_clicks_are_scheduled_ahead_on_the_audio_clock(page, app_url):
    boot(page, app_url, hash_='#/emergency/tool/cpr', init=FAKE_AUDIO)
    page.click('#cprBtn')
    page.clock.run_for(3000)
    starts = page.evaluate('__starts')
    whens = [w for w, _, _ in starts]
    assert any(w > now + 0.5 for w, now, _ in starts)            # sounds are queued ahead of the tick that queued them
    gaps = [b - a for a, b in zip(whens, whens[1:])]
    assert all(abs(g - 60 / 110) < 0.01 for g in gaps)            # evenly spaced, none bunched or doubled
    assert starts[0][2] == 1320 and starts[1][2] == 880          # accent on the first compression of a cycle


def test_cpr_late_tick_does_not_bunch_clicks(page, app_url):
    boot(page, app_url, hash_='#/emergency/tool/cpr', init=FAKE_AUDIO)
    page.click('#cprBtn')
    page.clock.fast_forward(5000)                                # page was throttled: one very late tick
    page.clock.run_for(2000)
    whens = [w for w, _, _ in page.evaluate('__starts')]
    gaps = [b - a for a, b in zip(whens, whens[1:])]
    assert gaps and min(gaps) > 0.4   # one beat may land up to 200 ms late, never doubled up


def stop_cpr(page):
    page.click('#cprBtn')
    page.clock.run_for(800)
    page.click('#cprBtn')
    assert page.evaluate('FK.tools.cpr.running()') is False


def test_cpr_stop_silences_clicks_already_queued_ahead(page, app_url):
    boot(page, app_url, hash_='#/emergency/tool/cpr', init=FAKE_AUDIO)
    page.click('#cprBtn')
    page.clock.run_for(3000)
    stop_cpr(page)
    stopped_at = page.evaluate('performance.now() / 1000')
    assert page.evaluate('__starts.filter(s => s[0] > performance.now() / 1000).length') > 0   # something was queued ahead
    assert page.evaluate('after => __audibleAfter(after)', stopped_at) == []
    page.clock.run_for(3000)
    assert page.evaluate('after => __audibleAfter(after)', stopped_at) == []


def test_cpr_restart_right_after_stop_does_not_overlap_the_old_run(page, app_url):
    boot(page, app_url, hash_='#/emergency/tool/cpr', init=FAKE_AUDIO)
    page.click('#cprBtn')
    page.clock.run_for(3000)
    stop_cpr(page)
    stopped_at = page.evaluate('performance.now() / 1000')
    page.click('#cprBtn')
    page.clock.run_for(2500)
    whens = page.evaluate('after => __audibleAfter(after)', stopped_at)
    assert len(whens) >= 4
    assert all(b - a > 0.5 for a, b in zip(whens, whens[1:]))
    assert abs(whens[0] - stopped_at) < 1.0     # the first audible click belongs to the new run


def test_cpr_stop_during_breaths_hold_plays_nothing_afterwards(page, app_url):
    boot(page, app_url, hash_='#/emergency/tool/cpr', init=FAKE_AUDIO)
    page.click('#cprBtn')
    page.clock.run_for(17_000)                   # in the 4 s hold
    page.click('#cprBtn')
    page.clock.run_for(2000)                     # next cycle's first click is now queued ahead
    assert count_text(page) == '2 breaths'
    page.click('#cprBtn')
    stopped_at = page.evaluate('performance.now() / 1000')
    page.clock.run_for(5000)
    assert page.evaluate('after => __audibleAfter(after)', stopped_at) == []


def test_cpr_bounced_tap_on_start_does_not_arm_confirm_stop(page, app_url):
    boot(page, app_url, hash_='#/emergency/tool/cpr')
    page.evaluate("document.querySelector('#cprBtn').click(); document.querySelector('#cprBtn').click(); 0")
    assert page.inner_text('#cprBtn') == 'Stop'
    page.clock.run_for(800)
    page.click('#cprBtn')
    assert page.inner_text('#cprBtn') == 'Confirm stop'


def test_active_strip_cpr_line_carries_the_wake_lock_warning(page, app_url):
    boot(page, app_url, strip_apis=True)
    page.evaluate("FK.tools.start('cpr')")
    page.click('#cprBtn')
    page.click('#toolClose')
    page.wait_for_function("location.hash === '#/emergency'")
    assert page.inner_text('#emActive button').strip() == 'CPR running, cycle 1, screen may sleep'


# ---------- Final review fixes ----------

SUSPENDED_AUDIO = """
  (() => {
    window.__resumes = 0; window.__allowResume = false;
    const node = () => ({ connect(n) { return n; }, disconnect() {} });
    window.AudioContext = class {
      constructor() { this.state = 'suspended'; this._l = []; }
      get currentTime() { return performance.now() / 1000; }
      get destination() { return {}; }
      addEventListener(t, f) { if (t === 'statechange') this._l.push(f); }
      resume() {
        window.__resumes++;
        if (window.__allowResume && this.state !== 'running') { this.state = 'running'; this._l.forEach(f => f()); }
        return Promise.resolve();
      }
      createGain() { return Object.assign(node(), { gain: { setValueAtTime() {}, exponentialRampToValueAtTime() {} } }); }
      createOscillator() { return Object.assign(node(), { frequency: {}, start() {}, stop() {} }); }
    };
  })();"""


def test_cpr_says_when_sound_is_off_and_a_tap_turns_it_back_on(page, app_url):
    running_cpr(page, app_url, init=SUSPENDED_AUDIO)
    page.clock.run_for(1500)
    notice = page.locator('#cprSound')
    assert notice.is_visible() and notice.inner_text() == 'Sound is off. Tap to turn it back on.'
    assert notice.bounding_box()['height'] >= 56
    assert page.evaluate('window.__resumes') >= 2   # it keeps asking the audio to resume on its own
    page.click('#toolClose')
    page.wait_for_function("location.hash === '#/emergency'")
    assert page.inner_text('#emActive [data-tool="cpr"]').strip().endswith(', no sound')
    reopen_cpr(page)
    page.evaluate('window.__allowResume = true')   # a tap is a user gesture: now it may resume
    page.click('#cprSound')
    page.clock.run_for(100)
    assert page.locator('#cprSound').is_hidden()
    page.click('#toolClose')
    page.wait_for_function("location.hash === '#/emergency'")
    assert 'no sound' not in page.inner_text('#emActive [data-tool="cpr"]')


def test_cpr_resumes_sound_when_the_page_becomes_visible(page, app_url):
    running_cpr(page, app_url, init=SUSPENDED_AUDIO)
    page.evaluate('window.__allowResume = true; window.__resumes = 0')
    page.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
    assert page.evaluate('window.__resumes') >= 1
    page.clock.run_for(100)
    assert page.locator('#cprSound').is_hidden()


def test_cpr_sets_playback_audio_session_where_it_exists_and_hint_mentions_silent_switch(page, app_url):
    running_cpr(page, app_url, init="Object.defineProperty(navigator, 'audioSession', { configurable: true, value: { type: 'auto' } });")
    assert page.evaluate('navigator.audioSession.type') == 'playback'
    assert 'On an iPhone, the ring/silent switch must be off silent.' in page.inner_text('#toolBody .hint')


def test_cpr_starts_without_audio_session(page, app_url):
    running_cpr(page, app_url)
    assert page.evaluate("'audioSession' in navigator") is False
    assert page.evaluate('FK.tools.cpr.running()') is True


def test_cpr_uses_webkit_audio_context_when_it_is_the_only_one(page, app_url):
    running_cpr(page, app_url, init="window.__wk = 0; window.webkitAudioContext = class extends AudioContext { constructor() { super(); window.__wk++; } }; delete window.AudioContext;")
    assert page.evaluate('window.__wk') == 1


def test_tourniquet_clear_and_confirm_buttons_are_at_least_56px(page, app_url):
    boot(page, app_url, storage={'tq': [{'id': 'a', 'limb': 'Left arm', 'start': T0 - 1000}]}, hash_='#/emergency/tool/tq')
    for sel in ('clear', 'confirm'):
        if sel == 'confirm':
            page.click('#tqList [data-act="clear"]')
        box = page.locator(f'#tqList [data-act="{sel}"]').bounding_box()
        assert box['height'] >= 56 and box['width'] >= 56, (sel, box)


def test_selecting_the_open_tool_again_keeps_its_state(page, app_url):
    boot(page, app_url, clock=False)
    page.evaluate("FK.tools.start('burn')")
    page.wait_for_function("location.hash === '#/emergency/tool/burn'")
    page.click('#burnSvg [data-r="chest"][role="button"]')
    assert page.inner_text('#burnTotal') == '9%'
    page.evaluate("document.querySelector('#toolBody').dataset.mark = 'same'")
    page.evaluate("FK.tools.start('burn')")
    assert page.inner_text('#burnTotal') == '9%'
    page.click('#toolSearch')   # and picking it from search over itself
    page.fill('#searchInput', 'burn area')
    page.click('#searchBody .sr-item[data-key="t:burn"]')
    page.wait_for_selector('#searchPane', state='hidden')
    assert page.inner_text('#burnTotal') == '9%'
    assert page.locator('#burnSvg [data-r="chest"].on').count() >= 1
    page.click('#toolClose')   # close still lands where the tool was opened from, in one press
    page.wait_for_function("location.hash === '#/emergency'")
    assert not tool_open(page)


def test_rate_count_survives_selecting_rate_again(page, app_url):
    boot(page, app_url, clock=False)
    page.evaluate("FK.tools.start('rate')")
    page.wait_for_function("location.hash === '#/emergency/tool/rate'")
    page.click('#rateTap'); page.click('#rateTap')
    page.evaluate("FK.tools.start('rate')")
    assert page.inner_text('#rateCount') == '2 taps'


def test_focus_returns_to_the_tool_button_after_close(page, app_url):
    boot(page, app_url, clock=False)
    page.click('#emCats summary[data-cat="tools"]')
    page.click('#emCats [data-tool="rate"]')
    page.wait_for_function("location.hash === '#/emergency/tool/rate'")
    page.click('#toolClose')
    page.wait_for_function("location.hash === '#/emergency'")
    page.wait_for_function("document.activeElement && document.activeElement.dataset.tool === 'rate'")
