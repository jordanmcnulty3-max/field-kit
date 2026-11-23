"""v7.8 final review fixes: one test (or a few) per finding, in the brief's order."""
import json

import pytest
from playwright.sync_api import expect

from .tac import store, open_map, set_fix
from .test_map import tiles_ok
from .test_map_tools import boot, center, ev, mk, shape, NOW

HOME = (43.0, -76.0)
DAY = 24 * 3600 * 1000


def top_is(page, sel):
    """Whether the element drawn at sel's centre is sel itself (or inside it)."""
    return ev(page, """s => { const e = document.querySelector(s), r = e.getBoundingClientRect();
      const pe = e.style.pointerEvents; e.style.pointerEvents = 'auto';   // the toast never takes taps; hit-test it anyway
      const at = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
      e.style.pointerEvents = pe;
      return !!at && (at === e || e.contains(at)); }""", sel)


# ---------- 1. Messages are drawn above the map ----------

def test_toast_and_update_bar_are_above_the_map(page, app_url):
    boot(page, app_url, markers=[mk('a', 'Alpha', lat=HOME[0], lon=HOME[1])], view=HOME)
    ev(page, "FK.toast('Hello there, this is a message')")
    expect(page.locator('#toast')).to_have_class('toast show')
    page.clock.run_for(400)
    assert top_is(page, '#toast')
    ev(page, 'FK.updateAvailable()')
    expect(page.locator('#updBar')).to_be_visible()
    assert top_is(page, '#updBar')


def test_toast_is_above_the_map_in_a_tool_mode(page, app_url):
    boot(page, app_url, view=HOME)
    ev(page, "FK.mapTools.start('route')")
    expect(page.locator('#toolBar')).to_be_visible()
    page.click('#tbAdd')
    page.click('#tbAdd')   # same spot: "That point is already placed"
    expect(page.locator('#toast')).to_have_class('toast show')
    page.clock.run_for(400)
    assert top_is(page, '#toast')


# ---------- 2. An old fix is the last position, not the current one ----------

OLD_FIX = {'lat': HOME[0] - 0.009, 'lon': HOME[1], 'alt': 120, 'acc': 5, 'spd': 3, 't': NOW - 3 * DAY}


def test_a_stored_fix_from_days_ago_is_the_last_position_on_the_map(page, app_url):
    boot(page, app_url, markers=[mk('a', 'Alpha', lat=HOME[0], lon=HOME[1])], lastFix=OLD_FIX)
    center(page, *HOME)
    rel = page.locator('#mCenterRel')
    expect(rel).to_have_text('1.00 km at 0° true from last position')
    center(page, OLD_FIX['lat'], OLD_FIX['lon'])
    expect(rel).to_have_text(f'Last position, 3 days ago, {ev(page, "t => new Date(t).toLocaleDateString(\'en-US\', { month: \'short\', day: \'numeric\' })", OLD_FIX["t"])}')
    ev(page, "FK.markers.edit('a')")
    expect(page.locator('#mkRel')).to_have_text('1.00 km at 0° true from last position')
    page.click('#mkCancel')
    expect(page.locator('#dlgMarker')).to_be_hidden()
    page.click('#mList')
    expect(page.locator('#lsList')).to_contain_text('from last position')
    expect(page.locator('#lsList')).not_to_contain_text('from you')
    page.click('#lsClose')
    expect(page.locator('#dlgList')).to_be_hidden()
    ev(page, 'FK.shapes.openRing()')
    expect(page.locator('#rgCentre')).to_contain_text('Alpha (1.00 km from last position)')


def test_position_screen_names_an_old_fix_and_hides_its_speed(page, app_url):
    boot(page, app_url, lastFix=OLD_FIX)
    ev(page, "FK.route.go('/tactical/position')")
    expect(page.locator('#gpsStatus')).to_contain_text('Last position, 3 days ago')
    expect(page.locator('#gpsStatus')).not_to_contain_text('Live fix')
    expect(page.locator('#sSpd')).to_have_text('—')


def test_a_live_fix_goes_stale_after_30_seconds(page, app_url):
    boot(page, app_url, markers=[mk('a', 'Alpha', lat=HOME[0], lon=HOME[1])])
    set_fix(page, HOME[0] - 0.009, HOME[1], spd=3)
    center(page, *HOME)
    expect(page.locator('#mCenterRel')).to_have_text('1.00 km at 0° true from you')
    page.clock.fast_forward(3 * DAY)
    expect(page.locator('#mCenterRel')).to_have_text('1.00 km at 0° true from last position')
    ev(page, "FK.route.go('/tactical/position')")
    expect(page.locator('#gpsStatus')).to_contain_text('Last position, 3 days ago')
    expect(page.locator('#sSpd')).to_have_text('—')


def test_no_fix_has_no_position_words(page, app_url):
    boot(page, app_url)
    expect(page.locator('#mCenterRel')).to_have_text('Grid at the crosshair')


def test_share_of_an_old_fix_carries_its_time(page, app_url):
    boot(page, app_url, lastFix=OLD_FIX)
    text = ev(page, 'FK._test.positionText(FK.getFix(), Date.now())')
    assert 'Time ' in text and 'Position is 3 days old' in text


# ---------- 3. Unsaved marker changes are not thrown away without asking ----------

def wps(page):
    return ev(page, "JSON.parse(localStorage.getItem('fk.wps') || '[]')")


def typed_new_marker(page):
    page.click('#mMark')
    expect(page.locator('#dlgMarker')).to_be_visible()
    page.fill('#mkName', 'Ridge top')
    page.fill('#mkNote', 'Water below the ridge')


@pytest.mark.parametrize('how', ['back', 'escape', 'backdrop'])
def test_dismissing_a_marker_with_typed_text_asks_first(page, app_url, how):
    page.goto('about:blank')
    boot(page, app_url)
    typed_new_marker(page)
    for attempt in ('keep', 'discard'):
        if how == 'back':
            page.go_back()
        elif how == 'escape':
            page.keyboard.press('Escape')
        else:
            page.mouse.click(2, 2)
        expect(page.locator('#dlgConfirm')).to_be_visible()
        expect(page.locator('#cfTitle')).to_have_text('Discard this marker?')
        expect(page.locator('#cfCancel')).to_have_text('Keep editing')
        expect(page.locator('#cfOk')).to_have_text('Discard')
        if attempt == 'keep':
            page.click('#cfCancel')
            expect(page.locator('#dlgConfirm')).to_be_hidden()
            expect(page.locator('#dlgMarker')).to_be_visible()
            expect(page.locator('#mkName')).to_have_value('Ridge top')
            expect(page.locator('#mkNote')).to_have_value('Water below the ridge')
            page.wait_for_function("history.state.fkSheet === 'dlgMarker'")
        else:
            page.click('#cfOk')
            expect(page.locator('#dlgMarker')).to_be_hidden()
            page.wait_for_function('history.state.fkSheet === undefined')
    assert wps(page) == []
    assert ev(page, 'location.hash') == '#/tactical/map'
    page.go_back()
    assert page.url == 'about:blank'


def test_dismissing_an_unchanged_marker_does_not_ask(page, app_url):
    boot(page, app_url, markers=[mk('a', 'Alpha')])
    ev(page, "FK.markers.edit('a')")
    expect(page.locator('#dlgMarker')).to_be_visible()
    page.keyboard.press('Escape')
    expect(page.locator('#dlgMarker')).to_be_hidden()
    expect(page.locator('#dlgConfirm')).to_be_hidden()


def test_a_drag_from_inside_the_sheet_to_the_backdrop_does_not_close_it(page, app_url):
    boot(page, app_url)
    page.evaluate("FK.sheet.open(document.querySelector('#dlgLayers'))")
    expect(page.locator('#dlgLayers')).to_be_visible()
    box = page.locator('#dlgLayers').bounding_box()
    page.mouse.move(box['x'] + box['width'] / 2, box['y'] + 30)
    page.mouse.down()
    page.mouse.move(2, 2)
    page.mouse.up()
    expect(page.locator('#dlgLayers')).to_be_visible()
    page.mouse.click(2, 2)
    expect(page.locator('#dlgLayers')).to_be_hidden()


# ---------- 4. The discard question says Keep editing / Discard ----------

def test_route_discard_buttons_say_keep_editing_and_discard(page, app_url):
    boot(page, app_url)
    ev(page, "FK.mapTools.start('route')")
    page.click('#tbAdd')
    center(page, HOME[0], HOME[1] + 0.005)
    page.click('#tbAdd')
    page.click('#tbCancel')
    expect(page.locator('#cfTitle')).to_have_text('Discard this route?')
    expect(page.locator('#cfCancel')).to_have_text('Keep editing')
    expect(page.locator('#cfOk')).to_have_text('Discard')
    page.click('#cfCancel')
    expect(page.locator('#toolBar')).to_be_visible()
    ev(page, "void FK.sheet.confirm({ title: 'Delete?', ok: 'Delete' })")
    expect(page.locator('#cfCancel')).to_have_text('Cancel')   # other confirms keep their Cancel


def test_ring_sheet_with_a_typed_radius_asks_on_back(page, app_url):
    boot(page, app_url)
    ev(page, 'FK.shapes.openRing()')
    expect(page.locator('#dlgRing')).to_be_visible()
    page.fill('#rgR1', '300')
    page.keyboard.press('Escape')
    expect(page.locator('#cfTitle')).to_have_text('Discard this ring?')
    expect(page.locator('#cfCancel')).to_have_text('Keep editing')
    page.click('#cfOk')
    expect(page.locator('#dlgRing')).to_be_hidden()


# ---------- 5. An unfinished route or area survives a tab tap or Search ----------

from .test_map_tools import start as tool_start, add as tool_add, dest, bar_closed, idx_ok


@pytest.mark.parametrize('kind', ['route', 'area'])
def test_unfinished_shape_is_kept_across_a_tab_tap(page, app_url, kind):
    boot(page, app_url)
    tool_start(page, kind)
    tool_add(page, *HOME)
    tool_add(page, *dest(page, *HOME, 90, 400))
    page.click('.tabbar [data-tab="survival"]')
    expect(page.locator('#tab-survival')).to_be_visible()
    page.click('.tabbar [data-tab="tactical"]')
    page.wait_for_function(f"FK.mapTools.mode() === '{kind}' && history.state.fkLayer")
    assert ev(page, 'FK.mapTools.points().length') == 2
    expect(page.locator('#toolBar')).to_be_visible()
    expect(page.locator('#toast')).to_have_text(f'Your unfinished {kind} is still here')
    idx_ok(page)
    page.go_back()   # Back still asks, as before the tab tap
    expect(page.locator('#cfTitle')).to_have_text(f'Discard this {kind}?')
    page.click('#cfOk')
    bar_closed(page)
    idx_ok(page)


def test_unfinished_route_is_kept_across_search(page, app_url):
    boot(page, app_url)
    tool_start(page, 'route')
    tool_add(page, *HOME)
    tool_add(page, *dest(page, *HOME, 90, 400))
    page.click('#searchBtn')
    expect(page.locator('#searchPane')).to_be_visible()
    page.click('#searchClose')
    expect(page.locator('#searchPane')).to_be_hidden()
    page.wait_for_function("FK.mapTools.mode() === 'route' && history.state.fkLayer")
    assert ev(page, 'FK.mapTools.points().length') == 2
    page.click('#tbDone')
    expect(page.locator('#dlgAsk')).to_be_visible()
    page.click('#askOk')
    bar_closed(page)
    assert len(ev(page, 'FK.tac.shapes()')) == 1
    idx_ok(page)


# ---------- 6. A protocol's question sits right above its Yes / No buttons ----------

import glob as _glob, hashlib as _hashlib, os as _os
from .conftest import ROOT, inject_protocols

QSTEPS = sorted((json.load(open(f))['id'], s['id'], s['ask'].get('q') or s['text'])
                for f in _glob.glob(_os.path.join(ROOT, 'src', 'protocols', '*.json'))
                for s in json.load(open(f))['steps'] if s.get('ask'))

QBOX = """() => { const q = document.querySelector('#player #ppQ'), yes = document.querySelector('#player [data-act="yes"]'),
  no = document.querySelector('#player [data-act="no"]');
  if (!q || !yes) return null;
  const r = q.getBoundingClientRect(), y = yes.getBoundingClientRect(), n = no.getBoundingClientRect();
  return { text: q.textContent, top: r.top, bottom: r.bottom, yTop: y.top, yBottom: y.bottom, nBottom: n.bottom, h: innerHeight,
    scrollW: q.scrollWidth, clientW: q.clientWidth,
    inBody: document.querySelector('#ppBody').textContent.includes(q.textContent) && document.querySelector('#ppBody .pp-q') !== null }; }"""


@pytest.mark.parametrize('night', [False, True])
def test_every_question_is_on_screen_above_its_buttons(page, app_url, night):
    store(page, advAck=True, night=night)
    page.goto(app_url + '#/emergency')
    page.wait_for_function('window.FK && FK.route')
    bad = []
    for pid, sid, q in QSTEPS:
        ev(page, 'p => FK.route.go(p)', f'/emergency/{pid}/{sid}')
        page.wait_for_function('document.querySelector("#player #ppQ")')
        b = ev(page, QBOX)
        ok = (b and b['text'] == q and b['top'] >= 0 and b['bottom'] <= b['yTop'] + 0.5 and b['yBottom'] <= b['h']
              and b['nBottom'] <= b['h'] and b['scrollW'] <= b['clientW'] and not b['inBody'])
        if not ok:
            bad.append((pid, sid, b))
    assert bad == []
    if night:
        colors = ev(page, "() => { const c = getComputedStyle(document.querySelector('#ppQ')); return [c.color, c.backgroundColor]; }")
        assert colors[0] != colors[1]


def test_a_three_line_question_keeps_the_buttons_on_screen(page, app_url):
    long_q = 'Is the person awake and talking to you clearly, and are they breathing normally, without gasping, without pauses, and without any noisy sound?'
    inject_protocols(page, [{'id': 'longq', 'title': 'Long question', 'category': 'life', 'reviewed': '2026-11-16',
                             'sources': [{'name': 'Fixture'}],
                             'steps': [{'id': 'q', 'text': 'Check them', 'detail': 'word ' * 400, 'ask': {'q': long_q, 'yes': 'y', 'no': 'n'}},
                                       {'id': 'y', 'text': 'Yes', 'end': True}, {'id': 'n', 'text': 'No', 'end': True}]}])
    page.goto(app_url + '#/emergency/longq/q')
    page.wait_for_function('document.querySelector("#player #ppQ")')
    b = ev(page, QBOX)
    assert b['text'] == long_q and b['bottom'] - b['top'] > 50   # it wrapped onto several lines
    assert b['top'] >= 0 and b['bottom'] <= b['yTop'] + 0.5 and b['nBottom'] <= b['h']


def test_v77_search_fixture_is_unchanged():
    f = _os.path.join(ROOT, 'tests', 'fixtures', 'search_v77_on_screen.json')
    # The fixture as released in v7.7 and v7.8. This used to ask git to compare with a commit on the v7.8 work branch;
    # that history was removed from GitHub at the v7.8 release, so the check failed in every fresh clone.
    import hashlib
    with open(f, 'rb') as fh:
        assert hashlib.sha256(fh.read()).hexdigest() == '733dd05b86b7d8dbd8ed42657106dab13fe403edf81922e0dfabdcf01407ccc7'


# ---------- 7. Sightings older than 24 h are drawn as outlines on the map ----------

def stale_ids(page):
    return ev(page, "[...document.querySelectorAll('#map .mk-pin.stale')].map(e => e.dataset.id).sort()")


def fill_of(page, id_):
    return ev(page, "id => { const e = document.querySelector(`#map .mk-pin[data-id='${id_}'] .af`); return getComputedStyle(e).fill; }".replace('${id_}', id_))


@pytest.mark.parametrize('night', [False, True])
def test_sightings_fade_after_24_hours_with_the_clock_and_after_a_reload(page, app_url, night):
    boot(page, app_url, markers=[mk('f', 'Mike', kind='friend', t=NOW - 3600_000),
                                 mk('h', 'Two men', lat=HOME[0] + 0.002, kind='hostile', t=NOW - 3600_000),
                                 mk('p', 'Camp', lat=HOME[0] - 0.002, kind='camp', t=NOW - 3600_000)], night=night)
    page.wait_for_selector("#map .mk-pin[data-id='f']")
    assert stale_ids(page) == []
    fresh = fill_of(page, 'f')
    assert fresh != 'none'
    page.clock.fast_forward(3 * DAY)
    page.wait_for_function("document.querySelectorAll('#map .mk-pin.stale').length === 2")
    assert stale_ids(page) == ['f', 'h']
    assert fill_of(page, 'f') == 'none'
    page.reload()
    page.wait_for_selector("#map .mk-pin[data-id='f']")
    assert stale_ids(page) == ['f', 'h']


def test_sightings_fade_when_the_map_is_shown_again(page, app_url):
    boot(page, app_url, markers=[mk('f', 'Mike', kind='friend', t=NOW - 23 * 3600_000)])
    page.wait_for_selector("#map .mk-pin[data-id='f']")
    ev(page, "FK.route.go('/tactical/position')")
    page.clock.set_system_time(NOW + 2 * 3600_000)   # the clock jumps while the map is not on screen (no timer fires)
    ev(page, "FK.route.go('/tactical/map')")
    page.wait_for_selector("#map .mk-pin.stale[data-id='f']")


# ---------- 8. A halt does not count as moving ----------

SIM = """([sd, rho, seed, speed]) => {
  // the reviewer's simulation: one fix a second for 30 min, correlated noise (AR(1) per axis) of sd metres,
  // reported accuracy the 95% radius of that noise (the Geolocation spec's meaning of accuracy)
  let s = seed * 9301 + 49297;
  const rnd = () => { s = (s * 16807) % 2147483647; return (s - 1) / 2147483646; };
  const gauss = () => Math.sqrt(-2 * Math.log(rnd() || 1e-12)) * Math.cos(2 * Math.PI * rnd());
  const k = Math.sqrt(1 - rho * rho) * sd, t0 = Date.now();
  let x = 0, y = 0;
  for (let t = 0; t < 1800; t++) {
    x = rho * x + gauss() * k; y = rho * y + gauss() * k;
    const X = x + speed * t;
    FK._test.fix({ lat: 43 + y / 111320, lon: -76 + X / (111320 * Math.cos(43 * Math.PI / 180)), acc: 2.45 * sd, t: t0 + t * 1000 });
  }
  return TGEOM.trackStats(FK.map.track());
}"""
CASES = [(3, 0.9), (5, 0.9), (5, 0.97), (8, 0.95), (10, 0.98)]


@pytest.mark.parametrize('sd,rho', CASES)
def test_standing_still_for_30_minutes_is_not_moving(page, app_url, sd, rho):
    boot(page, app_url, recording=True)
    for seed in range(3):
        ev(page, "localStorage.setItem('fk.track', '[]')")
        page.reload()
        page.wait_for_function('window.FK && FK.map')
        st = ev(page, SIM, [sd, rho, seed, 0])
        assert st['movingMs'] < 120000 and st['dist'] < 100, (seed, st)


@pytest.mark.parametrize('sd,rho', CASES)
def test_a_walk_with_the_same_noise_still_reads_right(page, app_url, sd, rho):
    boot(page, app_url, recording=True)
    st = ev(page, SIM, [sd, rho, 1, 1.4])
    assert abs(st['dist'] / (1.4 * 1799) - 1) < 0.15, st


def test_a_leg_with_no_time_gap_is_not_moving(page, app_url):
    boot(page, app_url)
    st = ev(page, "TGEOM.trackStats([[43, -76, null, 1000], [43.001, -76, null, 1000], [43.002, -76, null, 2000]])")
    assert st['movingMs'] == 1000 and abs(st['movingDist'] - 111.2) < 1


# ---------- 11. The map stays put across Map -> Position -> Map ----------

@pytest.mark.parametrize('how', ['route', 'tap'])
def test_map_centre_and_zoom_survive_three_round_trips(page, app_url, how):
    boot(page, app_url, markers=[mk('a', 'Alpha')])
    center(page, HOME[0] + 0.003, HOME[1] + 0.004, 14)
    before = ev(page, '(() => { const m = FK.leafletMap(), c = m.getCenter(); return [c.lat, c.lng, m.getZoom()]; })()')
    for _ in range(3):
        if how == 'route':
            ev(page, "FK.route.go('/tactical/position')")
            ev(page, "FK.route.go('/tactical/map')")
        else:
            page.click('#tacSeg [data-view="position"]')
            expect(page.locator('#view-position')).to_be_visible()
            page.click('#tacSeg [data-view="map"]')
        expect(page.locator('#view-map')).to_be_visible()
        page.wait_for_timeout(150)
    after = ev(page, '(() => { const m = FK.leafletMap(), c = m.getCenter(); return [c.lat, c.lng, m.getZoom()]; })()')
    assert after[2] == before[2]
    assert ev(page, '([a, b]) => GEO.distance(a[0], a[1], b[0], b[1])', [before, after]) < 1, (before, after)


# ---------- 12. Location blocked says so everywhere ----------

BLOCKED = 'Location is blocked. Allow location for this site in Chrome’s site settings, then reload.'


def deny(page):
    page.add_init_script("""navigator.geolocation.watchPosition = (ok, err) => { setTimeout(() => err({ code: 1, message: 'denied' }), 0); return 7; };
      navigator.geolocation.clearWatch = () => {};""")


def test_blocked_location_shows_on_the_map(page, app_url):
    deny(page)
    boot(page, app_url)
    expect(page.locator('#mapGps')).to_be_visible()
    expect(page.locator('#mapGps')).to_have_text(BLOCKED)
    assert top_is(page, '#mapGps')


def test_blocked_location_refuses_to_start_recording(page, app_url):
    deny(page)
    boot(page, app_url)
    expect(page.locator('#mapGps')).to_be_visible()
    ev(page, 'FK.map.openTrack()')
    page.click('#trkToggle')
    expect(page.locator('#trkMsg')).to_have_text(BLOCKED)
    expect(page.locator('#recChip')).to_be_hidden()
    assert ev(page, 'FK.isRecording()') is False
    expect(page.locator('#trkToggle')).to_have_text('Start recording')


def test_blocked_location_share_says_blocked(page, app_url):
    deny(page)
    boot(page, app_url)
    ev(page, "FK.route.go('/tactical/position')")
    expect(page.locator('#gpsStatus')).to_contain_text('Location is blocked')
    page.click('#shareBtn')
    expect(page.locator('#toast')).to_have_text(BLOCKED)


def test_a_fix_clears_the_blocked_note(page, app_url):
    deny(page)
    boot(page, app_url)
    expect(page.locator('#mapGps')).to_be_visible()
    set_fix(page, *HOME)
    expect(page.locator('#mapGps')).to_be_hidden()


# ---------- 13. Recording after a long break asks: continue or start a new track ----------

def old_track(age_ms):
    t = NOW - age_ms
    return [[HOME[0], HOME[1], None, t - 60000], [HOME[0] + 0.001, HOME[1], None, t]]


@pytest.mark.parametrize('choice', ['continue', 'new', 'back'])
def test_start_recording_on_an_old_track_asks(page, app_url, choice):
    boot(page, app_url, track=old_track(31 * 60000))
    ev(page, 'FK.map.openTrack()')
    page.click('#trkToggle')
    expect(page.locator('#dlgTrkOld')).to_be_visible()
    expect(page.locator('#toContinue')).to_have_text('Continue the old track')
    expect(page.locator('#toNew')).to_have_text('Start a new track (the old one is cleared)')
    if choice == 'continue':
        page.click('#toContinue')
        expect(page.locator('#dlgTrkOld')).to_be_hidden()
        assert ev(page, 'FK.isRecording()') and len(ev(page, 'FK.map.track()')) == 2
    elif choice == 'new':
        page.click('#toNew')
        expect(page.locator('#dlgTrkOld')).to_be_hidden()
        assert ev(page, 'FK.isRecording()') and ev(page, 'FK.map.track()') == []
    else:
        page.go_back()
        expect(page.locator('#dlgTrkOld')).to_be_hidden()
        assert not ev(page, 'FK.isRecording()') and len(ev(page, 'FK.map.track()')) == 2
    expect(page.locator('#dlgTrack')).to_be_visible()
    page.wait_for_function("history.state.fkSheet === 'dlgTrack'")


def test_start_recording_on_a_recent_track_just_continues(page, app_url):
    boot(page, app_url, track=old_track(20 * 60000))
    ev(page, 'FK.map.openTrack()')
    page.click('#trkToggle')
    expect(page.locator('#trkToggle')).to_have_text('Stop recording')
    expect(page.locator('#dlgTrkOld')).to_be_hidden()
    assert len(ev(page, 'FK.map.track()')) == 2


# ---------- 14. Walking a route: follow on, moving-away hint with Next / Stop on the map, Arrived on the map ----------

WALK = shape('r1', 'route', [[HOME[0], HOME[1]], [HOME[0] + 0.004, HOME[1]], [HOME[0] - 0.006, HOME[1]]], name='To camp')   # point 3 is back south


def walk_fixes(page, pts, every=5000):
    """Feed fixes [lat, lon] ending now, every ms apart."""
    ev(page, """([pts, every]) => { const now = Date.now();
      pts.forEach((p, i) => FK._test.fix({ lat: p[0], lon: p[1], acc: 5, t: now - (pts.length - 1 - i) * every })); }""", [pts, every])


def test_walk_this_route_turns_follow_on(page, app_url):
    boot(page, app_url, shapes=[WALK])
    set_fix(page, *HOME)
    expect(page.locator('#mLocate')).to_have_attribute('aria-pressed', 'false')
    ev(page, "FK.shapes.edit('r1')")
    page.click('#shWalk')
    expect(page.locator('#dlgShape')).to_be_hidden()
    expect(page.locator('#mLocate')).to_have_attribute('aria-pressed', 'true')


def test_moving_away_from_the_point_shows_next_and_stop_on_the_map(page, app_url):
    boot(page, app_url, shapes=[WALK], target={'type': 'route', 'id': 'r1', 'i': 1})
    # walking south, away from point 2 (to the north): 10 fixes over 45 s, 60 m further away
    walk_fixes(page, [[HOME[0] - 0.00006 * i, HOME[1]] for i in range(10)])
    away = page.locator('#nsAway')
    expect(away).to_be_visible()
    expect(page.locator('#nsAwayText')).to_have_text('Moving away from point 2')
    assert top_is(page, '#nsNext') and top_is(page, '#nsStop')
    page.click('#nsNext')
    assert ev(page, 'FK.tac.target().i') == 2
    expect(away).to_be_hidden()
    ev(page, "FK.route.go('/tactical/position')")
    expect(page.locator('#nvAway')).to_be_hidden()


def test_moving_away_shows_on_position_too_and_stop_ends_it(page, app_url):
    boot(page, app_url, shapes=[WALK], target={'type': 'route', 'id': 'r1', 'i': 1})
    walk_fixes(page, [[HOME[0] - 0.00006 * i, HOME[1]] for i in range(10)])
    expect(page.locator('#nsAway')).to_be_visible()
    page.click('#nsStop')
    assert ev(page, 'FK.tac.target()') is None
    expect(page.locator('#navStrip')).to_be_hidden()


def test_walking_toward_the_point_shows_no_hint(page, app_url):
    boot(page, app_url, shapes=[WALK], target={'type': 'route', 'id': 'r1', 'i': 1})
    walk_fixes(page, [[HOME[0] + 0.00006 * i, HOME[1]] for i in range(10)])
    expect(page.locator('#navStrip')).to_be_visible()
    expect(page.locator('#nsAway')).to_be_hidden()


def test_arrived_shows_on_the_map_strip(page, app_url):
    boot(page, app_url, markers=[mk('a', 'Alpha', lat=HOME[0] + 0.002)], target='a')
    set_fix(page, HOME[0] + 0.002, HOME[1])
    expect(page.locator('#nsDist')).to_have_text('Arrived')


# ---------- 15. A new marker starts as a Point every time ----------

def test_after_a_friend_the_next_new_marker_is_a_point(page, app_url):
    boot(page, app_url)
    page.click('#mMark')
    page.click('#dlgMarker [data-kind="friend"]')
    page.click('#mkSave')
    expect(page.locator('#dlgMarker')).to_be_hidden()
    page.click('#mMark')
    expect(page.locator('#dlgMarker [data-kind="point"]')).to_have_attribute('aria-pressed', 'true')
    expect(page.locator('#mkName')).to_have_value('WP 2')


# ---------- 16. A double tap on Save does not land on what is under the sheet ----------

def test_second_tap_of_a_double_tap_on_save_is_swallowed(page, app_url):
    boot(page, app_url)
    page.click('#mMark')
    expect(page.locator('#dlgMarker')).to_be_visible()
    box = page.locator('#mkSave').bounding_box()
    x, y = box['x'] + box['width'] / 2, box['y'] + box['height'] / 2
    under = ev(page, '([x, y]) => { const d = document.querySelector("#dlgMarker"); d.close(); const e = document.elementFromPoint(x, y); d.showModal(); return e && (e.closest("button") || e).outerHTML.slice(0, 60); }', [x, y])
    ev(page, "window.__taps = 0; document.addEventListener('click', e => { if (!e.target.closest('dialog')) window.__taps++; })")
    page.mouse.click(x, y)
    page.mouse.click(x, y)   # the second tap of a double tap
    expect(page.locator('#dlgMarker')).to_be_hidden()
    assert ev(page, 'window.__taps') == 0, under
    assert ev(page, 'location.hash') == '#/tactical/map'
    page.wait_for_timeout(400)
    page.click('.tabbar [data-tab="survival"]')   # later taps work
    expect(page.locator('#tab-survival')).to_be_visible()


# ---------- 17. Save as route says so ----------

def test_saving_a_track_as_a_route_says_so_above_the_map(page, app_url):
    boot(page, app_url, track=[[HOME[0] + i * 0.0003, HOME[1], None, NOW - 600000 + i * 10000] for i in range(5)])
    ev(page, 'FK.map.openTrack()')
    page.click('#trkRoute')
    expect(page.locator('#dlgTrack')).to_be_hidden()
    name = ev(page, 'FK.tac.shapes()[0].name')
    expect(page.locator('#toast')).to_have_text(f'Saved as route {name}')
    page.clock.run_for(300)
    assert top_is(page, '#toast')


# ---------- 19. A route's name is drawn once, at its middle ----------

def test_route_name_is_drawn_once_at_the_middle(page, app_url):
    r = shape('r1', 'route', [[HOME[0], HOME[1]], [HOME[0] + 0.004, HOME[1]], [HOME[0] + 0.004, HOME[1] + 0.00547]], name='To camp')
    boot(page, app_url, markers=[mk('t', 'Truck')], shapes=[r], view=(HOME[0] + 0.002, HOME[1] + 0.001))
    page.wait_for_selector('.shp-lab.shp-text[data-id="r1"]')
    assert ev(page, "document.querySelectorAll('.shp-lab.shp-text[data-id=\"r1\"]').length") == 1
    c = ev(page, """() => { const r = document.querySelector('.shp-lab.shp-text[data-id="r1"]').getBoundingClientRect(),
      m = document.querySelector('#map').getBoundingClientRect(), ll = FK.leafletMap().containerPointToLatLng([r.left + r.width / 2 - m.left, r.top + r.height / 2 - m.top]);
      return [ll.lat, ll.lng]; }""")
    mid = (HOME[0] + 0.004, HOME[1])   # the route is 2 x 445 m: halfway is the corner
    assert ev(page, '([a, b]) => GEO.distance(a[0], a[1], b[0], b[1])', [c, list(mid)]) < 25
    truck = page.locator('.mk-pin[data-id="t"] b').bounding_box()
    lab = page.locator('.shp-lab.shp-text[data-id="r1"]').bounding_box()
    assert truck['x'] + truck['width'] < lab['x'] or lab['x'] + lab['width'] < truck['x'] or truck['y'] + truck['height'] < lab['y'] or lab['y'] + lab['height'] < truck['y']


# ---------- 20. Lines differ by pattern, not only colour; the heading cone shows at night ----------

@pytest.mark.parametrize('night', [False, True])
def test_route_track_ring_area_and_navigate_line_differ_by_pattern(page, app_url, night):
    shapes = [shape('r1', 'route', [[HOME[0], HOME[1]], [HOME[0] + 0.003, HOME[1]]], name='R'),
              shape('a1', 'area', [[HOME[0], HOME[1] + 0.002], [HOME[0] + 0.002, HOME[1] + 0.002], [HOME[0] + 0.002, HOME[1] + 0.004]], name='A'),
              shape('g1', 'ring', [[HOME[0], HOME[1]]], name='G', r=[200])]
    boot(page, app_url, shapes=shapes, markers=[mk('m', 'M', lat=HOME[0] - 0.002)], target='m', night=night,
         track=[[HOME[0], HOME[1] - 0.001, None, NOW - 60000], [HOME[0] + 0.002, HOME[1] - 0.001, None, NOW]])
    set_fix(page, HOME[0] + 0.001, HOME[1] - 0.001)
    page.wait_for_selector('path.shp-route', state='attached')
    style = """s => { const e = document.querySelector(s), c = getComputedStyle(e);
      return [c.strokeDasharray, c.strokeWidth, c.fill === 'none' || c.fillOpacity === '0' ? 'none' : 'fill'].join('|'); }"""
    looks = {k: ev(page, style, sel) for k, sel in [('route', 'path.shp-route'), ('track', 'path.trk'), ('nav', 'path.tgt-line'),
                                                  ('ring', 'path.shp-ring'), ('area', 'path.shp-area')]}
    assert len(set(looks.values())) == 5, looks
    cone = ev(page, "getComputedStyle(document.querySelector('.me .cone path')).opacity")
    assert float(cone) >= (0.5 if night else 0.25)


# ---------- 21. Reviewer items ----------

def test_measure_has_a_clear_button(page, app_url):
    boot(page, app_url)
    ev(page, "FK.mapTools.start('measure')")
    expect(page.locator('#tbClear')).to_be_visible()
    expect(page.locator('#tbClear')).to_be_disabled()
    page.click('#tbAdd')
    center(page, HOME[0] + 0.002, HOME[1])
    page.click('#tbAdd')
    page.click('#tbClear')
    assert ev(page, 'FK.mapTools.points()') == []
    assert ev(page, "FK.mapTools.mode()") == 'measure'
    b = page.locator('#tbClear').bounding_box()
    assert b['height'] >= 44 and b['width'] >= 44
    ev(page, "FK.mapTools.cancel()")
    ev(page, "FK.mapTools.start('route')")
    expect(page.locator('#tbClear')).to_be_hidden()


def test_router_replace_drops_sheet_and_layer_markers(page, app_url):
    boot(page, app_url)
    ev(page, "history.replaceState({ ...history.state, fkSheet: 'dlgX', fkLayer: 'tool.9' }, '')")
    ev(page, "FK.route.go('/tactical/position', { replace: true })")
    st = ev(page, 'history.state')
    assert 'fkSheet' not in st and 'fkLayer' not in st and 'fkIdx' in st


def test_marker_grid_keeps_its_text_for_screen_readers(page, app_url):
    boot(page, app_url, markers=[mk('a', 'Alpha')])
    ev(page, "FK.markers.edit('a')")
    g = page.locator('#mkGrid')
    expect(g).to_be_visible()
    assert g.get_attribute('aria-label') is None
    expect(g).to_have_accessible_name(g.inner_text())


def test_a_marker_timed_in_the_future_shows_no_age(page, app_url):
    boot(page, app_url, markers=[mk('h', 'Two men', kind='hostile', t=NOW + 3600_000)])
    page.click('#mList')
    expect(page.locator('#lsList')).not_to_contain_text('ago')
    page.click('#lsClose')
    ev(page, "FK.markers.edit('h')")
    expect(page.locator('#mkAge')).not_to_contain_text('ago')
    expect(page.locator('#mkAge')).to_contain_text('Marked')


def test_ring_refusal_in_yards(page, app_url):
    boot(page, app_url, distUnit='us')
    ev(page, 'FK.shapes.openRing()')
    page.fill('#rgR1', '60000')
    page.click('#rgSave')
    expect(page.locator('#rgMsg')).to_have_text('Rings can be up to 54,680 yd (31 mi)')


def test_new_ids_stay_unique_in_one_millisecond(page, app_url):
    boot(page, app_url)
    ids = ev(page, "FK.tac.addMarkers(Array.from({ length: 300 }, (_, i) => ({ lat: 43, lon: -76 + i * 1e-5 }))).added.map(m => m.id)")
    assert len(set(ids)) == 300


def test_no_leaflet_popup_css_is_left():
    import os
    css = open(os.path.join(ROOT, 'src', 'shell.html'), encoding='utf-8').read()
    assert '.leaflet-popup' not in css and '.pop-act' not in css


# ---------- 22. An area reads its Perimeter, closing side included ----------

def test_area_reading_is_the_perimeter_with_the_closing_side(page, app_url):
    boot(page, app_url)
    ev(page, "FK.mapTools.start('area')")
    a = HOME
    b = dest(page, *HOME, 0, 300)
    c = dest(page, *b, 90, 400)
    for p in (a, b, c):
        center(page, *p)
        page.click('#tbAdd')
    # the crosshair on the last point: the three sides 300 + 400 + 500
    expect(page.locator('#tbRead')).to_contain_text('Perimeter 1.20 km.')
    expect(page.locator('#tbRead')).not_to_contain_text('Total')
    ev(page, "FK.mapTools.cancel()")
    ev(page, "FK.mapTools.start('route')")
    for p in (a, b):
        center(page, *p)
        page.click('#tbAdd')
    expect(page.locator('#tbRead')).to_contain_text('Total 300 m.')


# ---------- 23. Icons: Medical in a badge, Friend clearly a rectangle ----------

def test_medical_has_a_badge_and_friend_is_at_least_1_6_to_1(page, app_url):
    boot(page, app_url)
    medical = ev(page, "(() => { const d = document.createElement('div'); d.innerHTML = FK.markers.icon('medical'); return d.querySelectorAll('rect').length; })()")
    assert medical == 1
    w, h = ev(page, "(() => { const d = document.createElement('div'); d.innerHTML = FK.markers.icon('friend'); const r = d.querySelector('rect.af'); return [+r.getAttribute('width'), +r.getAttribute('height')]; })()")
    assert w / h >= 1.6


# ---------- 24. Follow does not look on with no position, and says why ----------

def test_locate_is_not_pressed_with_no_fix_and_says_why(page, app_url):
    boot(page, app_url, mapFollow=True)
    expect(page.locator('#mLocate')).to_have_attribute('aria-pressed', 'false')
    page.click('#mLocate')
    expect(page.locator('#toast')).to_contain_text('No position yet')
    set_fix(page, *HOME)
    expect(page.locator('#mLocate')).to_have_attribute('aria-pressed', 'true')


# ---------- 25. The "map isn't loading" note keeps clear of the crosshair and mentions saved maps ----------

def test_map_note_is_clear_of_the_crosshair_and_mentions_saved_maps(page, app_url):
    page.goto(app_url + '#/tactical/map')   # tiles are not served here
    expect(page.locator('#mapNote')).to_be_visible()
    expect(page.locator('#mapNote')).to_contain_text('saved for offline')
    n, c = page.locator('#mapNote').bounding_box(), page.locator('.cross').bounding_box()
    assert n['y'] >= c['y'] + c['height'] or n['y'] + n['height'] <= c['y']
    b = page.locator('#mapNoteLayers').bounding_box()
    assert b['height'] >= 44


# ---------- 26. Save map fields are not cut off; no empty strip above the map in a tool mode ----------

def test_save_map_fields_show_in_full(page, app_url):
    boot(page, app_url)
    ev(page, 'FK.map.openSave()')
    expect(page.locator('#dlgSave')).to_be_visible()
    for sel in ('#saveName', '#saveZ'):
        b = page.locator(sel).bounding_box()
        assert b['width'] >= 250, (sel, b)
    fits = ev(page, """() => { const i = document.querySelector('#saveName'), c = document.createElement('canvas').getContext('2d');
      c.font = getComputedStyle(i).font; return c.measureText(i.placeholder).width <= i.clientWidth - 16; }""")
    assert fits


def test_no_empty_strip_above_the_map_in_a_tool_mode(page, app_url):
    boot(page, app_url)
    ev(page, "FK.mapTools.start('route')")
    expect(page.locator('#toolBar')).to_be_visible()
    page.wait_for_timeout(100)
    gap = ev(page, "document.querySelector('#mapWrap').getBoundingClientRect().top - document.querySelector('.top').getBoundingClientRect().bottom")
    assert gap <= 1, gap


# ---------- Follow-up F1: an unfinished route waits for a sheet a Search result opened ----------

@pytest.mark.parametrize('key,q,dlg,close', [('a:waypoints', 'markers', '#dlgList', '#lsClose'), ('a:areas', 'saved maps', '#dlgSave', '#saveClose')])
@pytest.mark.parametrize('n', [1, 2])
def test_unfinished_route_waits_for_a_sheet_opened_from_search(page, app_url, key, q, dlg, close, n):
    boot(page, app_url)
    tool_start(page, 'route')
    for i in range(n):
        tool_add(page, *dest(page, *HOME, 90, 400 * i))
    page.click('#searchBtn')
    page.fill('#searchInput', q)
    page.click(f'#searchBody .sr-item[data-key="{key}"]')
    page.wait_for_selector(f'{dlg}[open]')
    page.evaluate('new Promise(r => FK.sheet.afterStep(r))')   # the sheet's history step has landed (was a fixed 300 ms)
    assert ev(page, 'FK.mapTools.mode()') is None
    assert ev(page, 'history.state.fkLayer') is None
    page.click(close)
    expect(page.locator(dlg)).to_be_hidden()
    expect(page.locator('#dlgConfirm')).to_be_hidden()
    page.wait_for_function("FK.mapTools.mode() === 'route' && history.state.fkLayer && !history.state.fkSheet")
    assert ev(page, 'FK.mapTools.points().length') == n
    idx_ok(page)
    page.go_back()
    if n >= 2:
        expect(page.locator('#cfTitle')).to_have_text('Discard this route?')
        page.click('#cfOk')
    bar_closed(page)


# ---------- Follow-up F2: a continuous walk in poor accuracy is moving ----------

WALKSIM = """([acc, speed, secs, halt]) => {
  // the reviewer's walk: one fix a second, AR(1) noise rho .95, sd = acc / 2.45; optional halt [from, to] in seconds
  let s = 12345;
  const rnd = () => { s = (s * 16807) % 2147483647; return (s - 1) / 2147483646; };
  const gauss = () => Math.sqrt(-2 * Math.log(rnd() || 1e-12)) * Math.cos(2 * Math.PI * rnd());
  const rho = 0.95, sd = acc / 2.45, k = Math.sqrt(1 - rho * rho) * sd, t0 = Date.now();
  let x = 0, y = 0, X0 = 0;
  for (let t = 0; t < secs; t++) {
    x = rho * x + gauss() * k; y = rho * y + gauss() * k;
    if (!(halt && t >= halt[0] && t < halt[1])) X0 += speed;
    const X = x + X0;
    FK._test.fix({ lat: 43 + y / 111320, lon: -76 + X / (111320 * Math.cos(43 * Math.PI / 180)), acc, t: t0 + t * 1000 });
  }
  return { st: TGEOM.trackStats(FK.map.track()), walked: X0 };
}"""


@pytest.mark.parametrize('acc', [20, 25, 30, 40])
@pytest.mark.parametrize('speed', [0.8, 1.0])
def test_a_30_minute_walk_in_poor_accuracy_is_moving(page, app_url, acc, speed):
    boot(page, app_url, recording=True)
    r = ev(page, WALKSIM, [acc, speed, 1800, None])
    st = r['st']
    print(f'F2 acc {acc} speed {speed}: moving {st["movingMs"] / 60000:.1f} of 30 min, distance {st["dist"]:.0f} of {r["walked"]:.0f} m')
    assert st['movingMs'] >= 27 * 60000, st
    assert abs(st['dist'] / r['walked'] - 1) < 0.10, (st, r['walked'])


def test_a_20_minute_halt_in_a_walk_is_not_moving(page, app_url):
    boot(page, app_url, recording=True)
    r = ev(page, WALKSIM, [10, 1.2, 2400, [600, 1800]])   # 10 min walk, 20 min halt, 10 min walk
    st = r['st']
    assert st['movingMs'] <= 22 * 60000 and st['elapsedMs'] >= 39 * 60000, st


# ---------- Follow-up F3: a stale sighting differs by shape (dashed outline), not only by fill ----------

AFFIL = ['friend', 'hostile', 'neutral', 'unknown']


@pytest.mark.parametrize('look', ['day', 'night', 'sat'])
def test_stale_frames_are_dashed_and_fresh_ones_solid(page, app_url, look):
    ms = []
    for i, k in enumerate(AFFIL):
        ms.append(mk(f'f{k}', f'New {k}', lat=HOME[0] + 0.001 * i, lon=HOME[1] - 0.002, kind=k, t=NOW - 3600_000))
        ms.append(mk(f's{k}', f'Old {k}', lat=HOME[0] + 0.001 * i, lon=HOME[1] + 0.002, kind=k, t=NOW - 3 * DAY))
    boot(page, app_url, markers=ms, night=look == 'night', mapLayer='sat' if look == 'sat' else 'topo')
    page.wait_for_selector("#map .mk-pin[data-id='sfriend']")
    dash = "s => getComputedStyle(document.querySelector(s)).strokeDasharray"
    fill = "s => getComputedStyle(document.querySelector(s)).fill"
    for k in AFFIL:
        fresh, stale = f"#map .mk-pin[data-id='f{k}'] .af", f"#map .mk-pin[data-id='s{k}'] .af"
        assert ev(page, dash, fresh) == 'none' and ev(page, dash, stale) not in ('none', ''), k
        assert ev(page, fill, stale) == 'none' and ev(page, fill, fresh) != 'none', k
    page.click('#mList')
    expect(page.locator('#dlgList')).to_be_visible()
    assert ev(page, "[...document.querySelectorAll('#lsList .mk-ic.stale .af')].every(e => getComputedStyle(e).strokeDasharray !== 'none')")
    assert ev(page, "[...document.querySelectorAll('#lsList .mk-ic:not(.stale) .af')].every(e => getComputedStyle(e).strokeDasharray === 'none')")
    if look == 'night':   # a fresh frame's fill is clearly lighter than the night map
        lum = ev(page, """s => { const f = getComputedStyle(document.querySelector(s)).fill, k = f.startsWith('color(') ? 255 : 1;
          const m = f.replace(/^color\\(srgb/, '').match(/[\\d.]+/g).map(n => Number(n) * k);
          return 0.2126 * m[0] + 0.7152 * m[1] + 0.0722 * m[2]; }""", "#map .mk-pin[data-id='ffriend'] .af")
        assert lum >= 100, lum


# ---------- Follow-up F4: a recording carried over while location is blocked says so on its pill ----------

def test_recording_pill_says_location_is_blocked(page, app_url):
    deny(page)
    boot(page, app_url, recording=True)
    chip = page.locator('#recChip')
    expect(chip).to_be_visible()
    expect(chip).to_have_text(BLOCKED)
    assert 'Recording' in chip.get_attribute('aria-label') and 'blocked' in chip.get_attribute('aria-label')
    set_fix(page, *HOME)
    expect(chip).to_have_text('Recording, 0 m')


# ---------- Follow-up F5: the help text's examples are Central New York round values, and each one reads ----------

def test_grid_help_examples_are_local_and_each_parses(page, app_url):
    boot(page, app_url)
    help_ = ev(page, 'FK.GRID_HELP')
    assert '38.' not in help_ and '77' not in help_
    for ex in ('18T VN 12345 67890', '43.0000, -76.0000', '43°00′00″N 76°00′00″W'):
        assert ex in help_
        p = ev(page, 's => GEO.parseAny(s)', ex)
        assert p and abs(p['lat'] - 43.0) < 0.6 and abs(p['lon'] + 76.0) < 1.2, (ex, p)


# ---------- A slow history step: a route must not resume under a sheet opened right after the list closes ----------

@pytest.mark.parametrize('n', [1, 2])
def test_unfinished_route_stays_out_of_the_way_of_a_marker_opened_from_the_list_on_a_slow_phone(page, app_url, n):
    boot(page, app_url)
    ev(page, 'FK.tac.addMarker({ lat: 43.002, lon: -76.002, name: "Spring" }).id')
    tool_start(page, 'route')
    for i in range(n):
        tool_add(page, *dest(page, *HOME, 90, 400 * i))
    page.click('#searchBtn')
    page.fill('#searchInput', 'markers')
    page.click('#searchBody .sr-item[data-key="a:waypoints"]')
    page.wait_for_selector('#dlgList[open]')
    page.evaluate('new Promise(r => FK.sheet.afterStep(r))')   # the sheet's history step has landed (was a fixed 300 ms)
    # a slow phone: every history step lands a quarter of a second late
    page.evaluate("const g = history.go.bind(history); history.go = k => { setTimeout(() => g(k), 250); }; 0")
    page.click('#dlgList [data-id]')
    page.wait_for_selector('#dlgMarker[open]')
    page.evaluate('new Promise(r => FK.sheet.afterStep(r))')   # the slowed step has landed (was a fixed 700 ms)
    assert ev(page, 'FK.mapTools.mode()') is None
    assert ev(page, 'history.state.fkLayer') is None
    assert ev(page, 'history.state.fkSheet') == 'dlgMarker'
    page.click('#mkCancel')
    expect(page.locator('#dlgMarker')).to_be_hidden()
    expect(page.locator('#dlgConfirm')).to_be_hidden()
    page.wait_for_function("FK.mapTools.mode() === 'route' && history.state.fkLayer && !history.state.fkSheet")
    assert ev(page, 'FK.mapTools.points().length') == n
