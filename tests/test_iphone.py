"""iPhone first-test fixes (v7.8 task 11i): the compass asks for motion permission from a tap where the browser has
DeviceOrientationEvent.requestPermission, and AbortSignal.timeout has a fallback in the app and the service worker.

No iPhone runs here. The iPhone is stood in for by an init script: requestPermission returns a promise the test settles, and
ondeviceorientationabsolute is removed so the app listens for plain deviceorientation, as on Safari. The test Chromium (157)
itself has requestPermission, as Chrome has had since 152, so the "older Android" case deletes it."""
import os
import re

import pytest

from playwright.sync_api import expect

from .tac import store, open_map, center, open_save
from .test_tactical_existing import tiles_cors, HOME

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOW = 1_800_000_000_000
BLOCKED = 'The compass is blocked. Allow motion and orientation access for this site in your browser or phone settings, then reload.'
NO_SENSOR = 'No compass sensor found. Distances and bearings to markers still work.'
CALIBRATE = 'Compass may need calibrating: move the phone in a figure-8.'

# Records each call: how many, whether the page had user activation, and whether the call came while the tap's click event
# was still being dispatched (a capture listener on window runs before the button's handler, a bubble listener after it).
IPHONE = """(() => {
  for (const o of [window, Window.prototype]) {
    const d = Object.getOwnPropertyDescriptor(o, 'ondeviceorientationabsolute');
    if (d && d.configurable) delete o.ondeviceorientationabsolute;
  }
  window.__rp = { calls: 0, active: [], inClick: [], settle: null };
  let inClick = false;
  window.addEventListener('click', () => { inClick = true; }, true);
  window.addEventListener('click', () => { inClick = false; }, false);
  DeviceOrientationEvent.requestPermission = function () {
    __rp.calls++;
    __rp.active.push(!!(navigator.userActivation && navigator.userActivation.isActive));
    __rp.inClick.push(inClick);
    return new Promise((res, rej) => { __rp.settle = { res, rej }; });
  };
})()"""
# Chrome before 152 and other Android browsers: no requestPermission at all.
ANDROID_OLD = "(() => { try { delete DeviceOrientationEvent.requestPermission; } catch (e) {} })()"
# Chrome 152 and later: requestPermission exists, but readings arrive without it (the default setting allows sensors).
CHROME_NEW = """(() => { window.__rp = { calls: 0 };
  DeviceOrientationEvent.requestPermission = () => { __rp.calls++; return Promise.resolve('granted'); }; })()"""


def at_position(page, app_url, stub=IPHONE, wait_ask=True):
    """Open Position with the page clock paused. wait_ask: let 900 ms of page time pass so Turn on compass is due (it shows
    only after 800 ms with no reading)."""
    page.clock.install(time=NOW / 1000)
    page.clock.pause_at(NOW / 1000 + 1)
    if stub:
        page.add_init_script(stub)
    store(page, declMode='manual', advAck=True)
    page.goto(app_url + '#/tactical/position')
    page.wait_for_function("window.FK && FK._test && FK.view() === 'position' && !document.querySelector('#view-position').hidden")
    if wait_ask:
        page.clock.run_for(900)


def ori(page, **props):
    """Dispatch a real orientation event of this type with these properties (webkitCompassHeading, alpha, ...)."""
    kind = props.pop('kind', 'deviceorientation')
    page.evaluate("([k, p]) => window.dispatchEvent(Object.assign(new Event(k), p))", [kind, props])


def settle(page, how, value=None):
    if how == 'res':
        page.evaluate("v => __rp.settle.res(v)", value)
    else:
        page.evaluate("() => __rp.settle.rej(new DOMException('denied', 'NotAllowedError'))")


def rp(page):
    return page.evaluate('__rp')


# ---------- Compass permission ----------

def test_iphone_shows_the_button_and_never_the_no_sensor_message(page, app_url):
    at_position(page, app_url)
    btn = page.locator('#compassAsk')
    expect(btn).to_be_visible()
    expect(btn).to_have_text('Turn on compass')
    assert btn.bounding_box()['height'] >= 48
    page.clock.run_for(6000)
    expect(page.locator('#hdgRef')).to_have_text('Hold the phone flat')
    assert rp(page)['calls'] == 0


def test_the_tap_calls_request_permission_once_inside_the_tap(page, app_url):
    at_position(page, app_url)
    page.click('#compassAsk')
    page.click('#compassAsk')                 # a second tap while the question is open does not ask again
    r = rp(page)
    assert r['calls'] == 1
    assert r['inClick'] == [True]             # called while the click was being handled: no await or timer before it
    assert r['active'] == [True]


def test_granted_hides_the_button_and_readings_show(page, app_url):
    at_position(page, app_url)
    page.click('#compassAsk')
    settle(page, 'res', 'granted')
    expect(page.locator('#compassAsk')).to_be_hidden()
    ori(page, webkitCompassHeading=90, alpha=0)
    expect(page.locator('#hdg')).to_have_text('90°')
    expect(page.locator('#hdgRef')).to_have_text('E, 1600 mils, magnetic')


def test_granted_with_no_reading_shows_the_no_sensor_message_after_4_seconds(page, app_url):
    at_position(page, app_url)
    page.click('#compassAsk')
    settle(page, 'res', 'granted')
    expect(page.locator('#compassAsk')).to_be_hidden()
    page.clock.run_for(3000)
    expect(page.locator('#hdgRef')).to_have_text('Hold the phone flat')
    page.clock.run_for(1500)
    expect(page.locator('#hdgRef')).to_have_text(NO_SENSOR)


def test_denied_shows_the_blocked_text_and_keeps_the_button(page, app_url):
    at_position(page, app_url)
    expect(page.locator('#compassBlocked')).to_be_hidden()
    page.click('#compassAsk')
    settle(page, 'res', 'denied')
    expect(page.locator('#compassBlocked')).to_have_text(BLOCKED)
    expect(page.locator('#compassBlocked')).to_be_visible()
    expect(page.locator('#compassAsk')).to_be_visible()
    page.clock.run_for(6000)
    expect(page.locator('#hdgRef')).to_have_text('Hold the phone flat')


def test_a_rejected_request_is_handled_like_denied(page, app_url):
    at_position(page, app_url)
    page.click('#compassAsk')
    settle(page, 'rej')
    expect(page.locator('#compassBlocked')).to_have_text(BLOCKED)
    expect(page.locator('#compassAsk')).to_be_visible()
    # Asking again after a refusal is allowed (the person may have changed the setting without reloading).
    page.click('#compassAsk')
    assert rp(page)['calls'] == 2
    settle(page, 'res', 'granted')
    expect(page.locator('#compassAsk')).to_be_hidden()
    expect(page.locator('#compassBlocked')).to_be_hidden()


def test_request_permission_throwing_is_handled_like_denied(page, app_url):
    at_position(page, app_url)
    page.evaluate("() => { DeviceOrientationEvent.requestPermission = () => { throw new TypeError('no'); }; }")
    page.click('#compassAsk')
    expect(page.locator('#compassBlocked')).to_have_text(BLOCKED)


def test_a_negative_accuracy_still_shows_the_heading_with_a_calibrating_hint(page, app_url):
    """What a negative webkitCompassAccuracy means was not confirmed, so it never hides the heading: it only adds a hint."""
    at_position(page, app_url)
    page.evaluate("window.__hdgs = []; FK.on('heading', h => __hdgs.push(h))")
    page.click('#compassAsk')
    settle(page, 'res', 'granted')
    expect(page.locator('#compassAsk')).to_be_hidden()
    ori(page, webkitCompassHeading=90, webkitCompassAccuracy=-1)
    expect(page.locator('#hdg')).to_have_text('90°')
    expect(page.locator('#hdgRef')).to_have_text('E, 1600 mils, magnetic. ' + CALIBRATE)
    assert page.evaluate('__hdgs') == [90]
    page.click('#declSeg [data-decl="manual"]')
    page.fill('#decl', '-10')                              # a redraw from the declination keeps the hint
    expect(page.locator('#hdgRef')).to_have_text('E, 1422 mils, true. ' + CALIBRATE)
    page.fill('#decl', '')
    ori(page, webkitCompassHeading=90, webkitCompassAccuracy=15)
    expect(page.locator('#hdgRef')).to_have_text('E, 1600 mils, magnetic')
    ori(page, webkitCompassHeading=90, webkitCompassAccuracy=-1)
    expect(page.locator('#hdgRef')).to_contain_text(CALIBRATE)
    ori(page, webkitCompassHeading=90)                     # no accuracy at all: no hint
    expect(page.locator('#hdgRef')).to_have_text('E, 1600 mils, magnetic')


def test_a_prompt_answer_is_not_a_refusal(page, app_url):
    at_position(page, app_url)
    page.click('#compassAsk')
    settle(page, 'res', 'prompt')
    page.wait_for_function('!document.querySelector("#compassAsk").disabled')
    page.clock.run_for(100)
    expect(page.locator('#compassAsk')).to_be_visible()
    expect(page.locator('#compassBlocked')).to_be_hidden()
    page.click('#compassAsk')                              # and the button still works
    assert rp(page)['calls'] == 2


def test_only_denied_or_a_rejection_shows_the_blocked_text(page, app_url):
    at_position(page, app_url)
    for how, value, blocked in (('res', 'prompt', False), ('res', 'denied', True), ('res', 'prompt', False), ('rej', None, True)):
        page.click('#compassAsk')
        settle(page, how, value)
        page.clock.run_for(100)
        if blocked:
            expect(page.locator('#compassBlocked')).to_be_visible()
        else:
            expect(page.locator('#compassBlocked')).to_be_hidden()
        expect(page.locator('#compassAsk')).to_be_visible()
    assert rp(page)['calls'] == 4


def test_a_question_that_never_answers_frees_the_button_after_10_seconds(page, app_url):
    at_position(page, app_url)
    page.click('#compassAsk')
    page.click('#compassAsk')
    assert rp(page)['calls'] == 1
    page.clock.run_for(9000)
    page.click('#compassAsk')
    assert rp(page)['calls'] == 1
    page.clock.run_for(1500)
    page.click('#compassAsk')
    assert rp(page)['calls'] == 2
    expect(page.locator('#compassBlocked')).to_be_hidden()


def test_permission_is_asked_again_after_a_reload(page, app_url):
    at_position(page, app_url)
    page.click('#compassAsk')
    settle(page, 'res', 'granted')
    expect(page.locator('#compassAsk')).to_be_hidden()
    page.reload()
    page.wait_for_function("window.FK && FK._test && FK.view() === 'position'")
    page.clock.run_for(900)
    expect(page.locator('#compassAsk')).to_be_visible()


def test_navigate_panel_has_the_button_and_one_grant_hides_both(page, app_url):
    at_position(page, app_url)
    page.evaluate(f"FK._test.fix({{ lat: {HOME[0]}, lon: {HOME[1]}, acc: 5, t: Date.now() }})")
    page.evaluate(f"FK.tac.setTarget({{ type: 'point', lat: {HOME[0] + 0.003}, lon: {HOME[1]}, name: 'Rally 1' }})")
    expect(page.locator('#nvNoCompass')).to_be_visible()
    expect(page.locator('#nvCompassAsk')).to_be_visible()
    expect(page.locator('#nvCompassAsk')).to_have_text('Turn on compass')
    assert page.locator('#nvCompassAsk').bounding_box()['height'] >= 48
    page.click('#nvCompassAsk')
    settle(page, 'res', 'denied')
    expect(page.locator('#nvCompassBlocked')).to_have_text(BLOCKED)
    expect(page.locator('#compassBlocked')).to_have_text(BLOCKED)
    page.click('#nvCompassAsk')
    settle(page, 'res', 'granted')
    expect(page.locator('#nvCompassAsk')).to_be_hidden()
    expect(page.locator('#compassAsk')).to_be_hidden()
    expect(page.locator('#nvCompassBlocked')).to_be_hidden()
    expect(page.locator('#nvNoCompass')).to_be_visible()   # still no heading until a reading comes
    ori(page, webkitCompassHeading=0)
    expect(page.locator('#nvNoCompass')).to_be_hidden()
    expect(page.locator('#nvArrow')).to_be_visible()


def test_older_android_has_no_button_and_the_no_sensor_message(page, app_url):
    at_position(page, app_url, stub=ANDROID_OLD)
    assert page.evaluate('typeof DeviceOrientationEvent.requestPermission') == 'undefined'
    expect(page.locator('#compassAsk')).to_be_hidden()
    page.evaluate(f"FK._test.fix({{ lat: {HOME[0]}, lon: {HOME[1]}, acc: 5, t: Date.now() }})")
    page.evaluate(f"FK.tac.setTarget({{ type: 'point', lat: {HOME[0] + 0.003}, lon: {HOME[1]}, name: 'Rally 1' }})")
    expect(page.locator('#nvNoCompass')).to_be_visible()
    expect(page.locator('#nvCompassAsk')).to_be_hidden()
    page.clock.run_for(4500)
    expect(page.locator('#hdgRef')).to_have_text(NO_SENSOR)
    ori(page, kind='deviceorientationabsolute', alpha=270, absolute=True)
    expect(page.locator('#hdg')).to_have_text('90°')


def test_newer_chrome_never_shows_the_button_when_a_reading_comes_soon(page, app_url):
    """Chrome 152+ on Android has requestPermission but sends readings anyway: a reading inside 800 ms means no button ever."""
    at_position(page, app_url, stub=CHROME_NEW, wait_ask=False)
    page.evaluate("""() => { window.__seen = false;
      new MutationObserver(() => { if (!document.querySelector('#compassAskWrap').hidden) __seen = true; })
        .observe(document.querySelector('#compassAskWrap'), { attributes: true }); }""")
    btn = page.locator('#compassAsk')
    expect(btn).to_be_hidden()                                   # 0 ms
    page.clock.run_for(100)
    ori(page, kind='deviceorientationabsolute', alpha=270, absolute=True)
    expect(btn).to_be_hidden()                                   # 100 ms
    expect(page.locator('#hdg')).to_have_text('90°')
    page.clock.run_for(800)
    expect(btn).to_be_hidden()                                   # 900 ms
    page.clock.run_for(4100)
    expect(btn).to_be_hidden()                                   # 5,000 ms
    assert page.evaluate('__seen') is False
    assert rp(page)['calls'] == 0


def test_native_request_permission_a_soon_reading_never_shows_the_button(page, app_url):
    """The owner's own phone: Chrome's own requestPermission, no stub at all."""
    at_position(page, app_url, stub=None, wait_ask=False)
    if page.evaluate("typeof DeviceOrientationEvent === 'undefined' || typeof DeviceOrientationEvent.requestPermission !== 'function'"):
        pytest.skip('this test browser has no native DeviceOrientationEvent.requestPermission')
    page.evaluate("""() => { window.__seen = false;
      new MutationObserver(() => { if (!document.querySelector('#compassAskWrap').hidden) __seen = true; })
        .observe(document.querySelector('#compassAskWrap'), { attributes: true }); }""")
    btn = page.locator('#compassAsk')
    expect(btn).to_be_hidden()                                   # 0 ms
    page.clock.run_for(100)
    ori(page, kind='deviceorientationabsolute', alpha=270, absolute=True)
    expect(btn).to_be_hidden()                                   # 100 ms
    expect(page.locator('#hdg')).to_have_text('90°')
    page.clock.run_for(800)
    expect(btn).to_be_hidden()                                   # 900 ms
    page.clock.run_for(4100)
    expect(btn).to_be_hidden()                                   # 5,000 ms
    assert page.evaluate('__seen') is False


def test_with_no_reading_the_button_shows_between_700_and_900_ms(page, app_url):
    at_position(page, app_url, wait_ask=False)
    btn = page.locator('#compassAsk')
    page.clock.run_for(700)
    expect(btn).to_be_hidden()
    page.clock.run_for(200)
    expect(btn).to_be_visible()
    page.clock.run_for(5000)
    expect(page.locator('#hdgRef')).to_have_text('Hold the phone flat')   # no "no sensor" message while the button is the way on


def test_newer_chrome_with_no_reading_shows_the_button_not_the_no_sensor_message(page, app_url):
    at_position(page, app_url, stub=CHROME_NEW, wait_ask=False)
    page.clock.run_for(5000)
    expect(page.locator('#compassAsk')).to_be_visible()
    expect(page.locator('#hdgRef')).to_have_text('Hold the phone flat')


def test_leaving_position_before_800_ms_stops_the_button_timer(page, app_url):
    at_position(page, app_url, wait_ask=False)
    page.clock.run_for(500)
    page.evaluate("FK.route.go('/tactical/ballistics')")
    page.wait_for_function("FK.view() === 'ballistics'")
    page.clock.run_for(1000)
    assert page.evaluate("document.querySelector('#compassAskWrap').hidden") is True
    page.evaluate("FK.route.go('/tactical/position')")
    page.wait_for_function("FK.view() === 'position'")
    page.clock.run_for(700)
    expect(page.locator('#compassAsk')).to_be_hidden()
    page.clock.run_for(200)
    expect(page.locator('#compassAsk')).to_be_visible()


# ---------- AbortSignal.timeout fallback ----------

NO_TIMEOUT = "(() => { delete AbortSignal.timeout; })()"


def test_timeout_signal_fallback_aborts_after_the_time(page, app_url):
    page.add_init_script(NO_TIMEOUT)
    page.goto(app_url + '#/tactical/position')
    page.wait_for_function('window.FK && FK.map')
    assert page.evaluate('typeof AbortSignal.timeout') == 'undefined'
    took = page.evaluate("""() => new Promise(res => {
      const s = FK.map.timeoutSignal(50), t0 = performance.now();
      if (!s || s.aborted) return res(-1);
      s.addEventListener('abort', () => res(performance.now() - t0));
    })""")
    assert 40 <= took < 1000
    assert page.evaluate("(() => { const A = window.AbortController; delete window.AbortController; "
                         "const s = FK.map.timeoutSignal(50); window.AbortController = A; return s === undefined; })()")


def test_timeout_signal_uses_the_native_function_when_there(page, app_url):
    page.goto(app_url + '#/tactical/position')
    page.wait_for_function('window.FK && FK.map')
    assert page.evaluate("""(() => {
      const real = AbortSignal.timeout; let got = null, ms = null;
      AbortSignal.timeout = m => { ms = m; got = real.call(AbortSignal, m); return got; };
      const s = FK.map.timeoutSignal(1234);
      AbortSignal.timeout = real;
      return s === got && ms === 1234;
    })()""")


def test_save_for_offline_works_without_abort_signal_timeout(page, app_url):
    page.add_init_script(NO_TIMEOUT)
    tiles_cors(page)
    open_map(page, app_url)
    center(page, *HOME, z=14)
    open_save(page)
    page.select_option('#saveZ', '13')
    page.fill('#saveName', 'Test area')
    page.click('#saveGo')
    expect(page.locator('#saveStatus')).to_have_text('Saved Test area. It works offline now.', timeout=30000)
    expect(page.locator('#areaList')).to_contain_text('Test area')


def test_a_tile_that_never_answers_is_counted_failed_not_hung(page, app_url):
    page.clock.install(time=NOW / 1000)
    page.add_init_script(NO_TIMEOUT)
    from .test_map import PNG
    held = []

    def tile(route):
        req = route.request
        if req.resource_type == 'fetch' and '/tile/13/' in req.url and (not held or held[0] == req.url):
            held.append(req.url)               # never answered, every try
            return
        route.fulfill(status=200, content_type='image/png', body=PNG, headers={'access-control-allow-origin': '*'})

    page.route('https://basemap.nationalmap.gov/**', tile)
    store(page, advAck=True)
    open_map(page, app_url)
    center(page, *HOME, z=14)
    open_save(page)
    page.select_option('#saveZ', '13')
    page.fill('#saveName', 'Test area')
    page.click('#saveGo')
    status = page.locator('#saveStatus')
    for _ in range(120):                       # 3 tries of 15 s plus the waits between them, a second of page time at a go
        if 'failed' in status.inner_text():
            break
        page.clock.run_for(1000)
        page.wait_for_timeout(20)
    expect(status).to_have_text('Saved Test area, but 1 tiles failed. Download it again to fill the gaps.')
    assert len(held) == 3
    expect(page.locator('#areaList')).to_contain_text('Test area')


def _without_helper(src):
    m = re.search(r'\n\s*function timeoutSignal\(ms\) \{\n.*?\n\s*\}\n', src, re.S)
    assert m, 'timeoutSignal(ms) helper not found'
    return src[:m.start()] + src[m.end():], m.group(0)


def test_abort_signal_timeout_is_called_only_inside_the_helper():
    for path, uses in (('src/map.js', 3), ('src/sw.js', 1)):
        with open(os.path.join(ROOT, path), encoding='utf-8') as f:
            src = f.read()
        rest, helper = _without_helper(src)
        assert 'AbortSignal.timeout(' in helper, path
        assert 'AbortSignal.timeout(' not in rest, path
        assert rest.count('timeoutSignal(') == uses, path


def test_service_worker_helper_falls_back(page, app_url):
    with open(os.path.join(ROOT, 'src/sw.js'), encoding='utf-8') as f:
        _, helper = _without_helper(f.read())
    page.goto(app_url + '#/tactical/position')
    page.wait_for_function('window.FK')
    took = page.evaluate("""h => new Promise(res => {
      delete AbortSignal.timeout;
      const timeoutSignal = new Function(h + '; return timeoutSignal;')();
      const s = timeoutSignal(50), t0 = performance.now();
      if (!s || s.aborted) return res(-1);
      s.addEventListener('abort', () => res(performance.now() - t0));
    })""", helper)
    assert 40 <= took < 1000
    assert page.evaluate("""h => { delete window.AbortController;
      return new Function(h + '; return timeoutSignal;')()(50) === undefined; }""", helper)
