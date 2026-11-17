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


def boot(page, app_url, storage=None, hash_='#/emergency', fixtures=FIXTURES, clock=True, strip_apis=False):
    if clock:
        page.clock.install(time=T0 // 1000)   # Python API takes seconds
    inject_protocols(page, fixtures)
    if strip_apis:
        page.add_init_script("""
          delete window.AudioContext; delete window.webkitAudioContext;
          delete Navigator.prototype.vibrate; delete Navigator.prototype.wakeLock;""")
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
    page.select_option('#tqLimb', 'Right arm')
    page.click('#tqStart')
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
    assert page.evaluate('typeof FK.log') == 'undefined'
    page.click('#tqStart')
    assert page.locator('#tqList .timer').count() == 1


def test_clear_needs_inline_second_tap_and_no_browser_dialog(page, app_url):
    boot(page, app_url, storage={'tq': [{'id': 'a', 'limb': 'Left arm', 'start': T0 - 1000}]}, hash_='#/emergency/tool/tq')
    dialogs = []
    page.on('dialog', lambda d: (dialogs.append(d.message), d.dismiss()))
    page.click('#tqList [data-act="clear"]')
    assert 'Only clear once responders have the time' in page.inner_text('#tqList .timer')
    assert page.evaluate('FK.tools.tq.active().length') == 1
    page.click('#tqList [data-act="confirm"]')
    assert page.locator('#tqList .timer').count() == 0
    assert json.loads(page.evaluate("localStorage.getItem('fk.tq')")) == []
    assert dialogs == []


def test_clear_confirmation_expires(page, app_url):
    boot(page, app_url, storage={'tq': [{'id': 'a', 'limb': 'Left arm', 'start': T0 - 1000}]}, hash_='#/emergency/tool/tq')
    page.click('#tqList [data-act="clear"]')
    page.clock.run_for(7000)
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
    assert page.evaluate("FK.tools.start('rate')") is False
    assert page.evaluate("FK.tools.start('burn')") is False
    assert page.evaluate("FK.tools.start('../x')") is False
    assert page.evaluate("location.hash") == '#/emergency' and not tool_open(page)
    page.goto(app_url + '#/emergency/tool/rate')
    page.wait_for_function("location.hash === '#/emergency'")
    assert not tool_open(page)


def test_register_adds_a_tool_that_can_open(page, app_url):
    boot(page, app_url)
    page.evaluate("""window.stopped = 0;
        FK.tools.register('rate', { label: 'Rate counter', render(el, opts) { el.textContent = 'hello ' + (opts.n || ''); }, stop() { stopped++; } })""")
    assert page.evaluate("FK.tools.start('rate', { n: 7 })") is True
    page.wait_for_function("location.hash === '#/emergency/tool/rate'")
    assert page.inner_text('#toolBody') == 'hello 7' and page.inner_text('#toolTitle') == 'Rate counter'
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
    boot(page, app_url, storage={'pins': ['t:rate', 't:cpr']})
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
    boot(page, app_url, hash_='#/emergency/tool/cpr')
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


def test_cpr_stops_when_overlay_closes(page, app_url):
    boot(page, app_url)
    page.evaluate("FK.tools.start('cpr')")
    page.click('#cprBtn')
    page.clock.run_for(2000)
    page.go_back()
    page.wait_for_function("location.hash === '#/emergency'")
    page.clock.run_for(30_000)
    page.click('#emCats summary[data-cat="tools"]')
    page.click('#emCats [data-tool="cpr"]')
    assert count_text(page) == '0' and page.inner_text('#cprBtn') == 'Start'


def test_cpr_works_without_audio_vibrate_wakelock(page, app_url):
    boot(page, app_url, hash_='#/emergency/tool/cpr', strip_apis=True)
    assert page.evaluate("[typeof AudioContext, typeof webkitAudioContext, typeof navigator.vibrate, typeof navigator.wakeLock]") == ['undefined'] * 4
    page.click('#cprBtn')
    page.clock.run_for(20_600)
    assert count_text(page) == '1' and page.inner_text('#cprCycle') == 'Cycle 2'
    page.click('#cprBtn')
    assert page.inner_text('#cprBtn') == 'Start'
    page.click('#toolClose')
    page.wait_for_function("location.hash === '#/emergency'")


def test_cpr_touch_targets_at_least_56px(page, app_url):
    boot(page, app_url, hash_='#/emergency/tool/cpr')
    heights = page.evaluate("[...document.querySelectorAll('#toolPane button')].filter(e => e.offsetParent !== null).map(e => e.getBoundingClientRect().height)")
    assert heights and min(heights) >= 56
