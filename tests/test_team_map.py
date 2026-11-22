"""Teammates on the Tactical map: the ring pins, the Teammate sheet, and what keeps them honest. Real taps throughout.
The page clock is fake (test_map_tools.boot), so times are exact: NOW is 1_800_000_000_000 ms."""
import pytest
from playwright.sync_api import expect

from .tac import set_fix
from .test_iphone import SHEET_BASIS
from .test_map_tools import HOME, NOW, boot as boot_map, center, ev, mk
from .test_mesh_state import chan, feed, node

PRIV = bytes(range(1, 17))
EVIL = '<img src=x onerror=window.__x=1>'
SEC = NOW // 1000
ALPHA, BRAVO, CHARLIE = 0x0A0B0C11, 0x0A0B0C12, 0x0A0B0C13


def pos(dlat=0.001, dlon=0.0, ago=240):
    return dict(lat=HOME[0] + dlat, lon=HOME[1] + dlon, time=SEC - ago)


def boot(page, app_url, on=True, private=True, **kw):
    if on:
        kw['meshOn'] = True
    boot_map(page, app_url, **kw)
    page.wait_for_function('window.FK && FK.mesh && FK.team')
    if on and private:
        chan(page, psk=PRIV, precision=32)


def pins(page):
    return page.eval_on_selector_all('#map .tm-pin', """els => els.map(e => ({ cls: e.className, name: e.querySelector('b').textContent,
      age: e.querySelector('em').textContent, num: e.dataset.num }))""")


def wait_pins(page, n):
    page.wait_for_function(f"document.querySelectorAll('#map .tm-pin').length === {n}")


def test_pins_are_drawn_only_for_teammates_with_a_position(page, app_url):
    boot(page, app_url)
    feed(page, node(ALPHA, 'Alpha', 'ALP', pos(), 0))
    feed(page, node(BRAVO, 'Bravo', 'BRV', None, 0))
    wait_pins(page, 1)
    page.wait_for_timeout(100)
    p = pins(page)
    assert len(p) == 1 and p[0]['name'] == 'Alpha' and p[0]['age'] == '4 min ago' and p[0]['cls'] == 'tm-pin'
    # a first position later adds the second pin
    feed(page, node(BRAVO, 'Bravo', 'BRV', pos(-0.001), 0))
    wait_pins(page, 2)


def test_a_pin_older_than_30_minutes_is_old_and_flips_with_time_alone(page, app_url):
    boot(page, app_url)
    feed(page, node(ALPHA, 'Alpha', 'ALP', pos(ago=29 * 60), 0))
    feed(page, node(BRAVO, 'Bravo', 'BRV', pos(-0.001, ago=31 * 60), 0))
    wait_pins(page, 2)
    by = {x['name']: x for x in pins(page)}
    assert by['Alpha']['cls'] == 'tm-pin' and by['Alpha']['age'] == '29 min ago'
    assert by['Bravo']['cls'] == 'tm-pin old' and by['Bravo']['age'] == '31 min ago'
    assert ev(page, 'FK.team.timerOn()') is True
    ev(page, "window.__n = 0; FK.on('team', () => { window.__n++; })")
    page.clock.run_for(2 * 60_000)   # no new 'team' event: the one-minute timer redraws
    page.wait_for_function("[...document.querySelectorAll('#map .tm-pin.old b')].some(b => b.textContent === 'Alpha')")
    by = {x['name']: x for x in pins(page)}
    assert by['Alpha']['cls'] == 'tm-pin old' and by['Alpha']['age'] == '31 min ago', by
    assert ev(page, 'window.__n') == 0


def test_the_flip_is_the_pin_itself_dashed_and_hollow_not_just_a_colour(page, app_url):
    boot(page, app_url)
    feed(page, node(ALPHA, 'Alpha', 'ALP', pos(ago=60), 0))
    feed(page, node(BRAVO, 'Bravo', 'BRV', pos(-0.001, ago=3600), 0))
    wait_pins(page, 2)
    st = ev(page, """() => Object.fromEntries([...document.querySelectorAll('#map .tm-pin')].map(p => {
      const cs = getComputedStyle(p.querySelector('i')); return [p.querySelector('b').textContent, [cs.borderTopStyle, cs.backgroundColor, cs.borderRadius]]; }))""")
    assert st['Alpha'][0] == 'solid' and st['Alpha'][1] != 'rgba(0, 0, 0, 0)'
    assert st['Bravo'][0] == 'dashed' and st['Bravo'][1] == 'rgba(0, 0, 0, 0)'
    assert st['Alpha'][2] == st['Bravo'][2] == '50%'


@pytest.mark.parametrize('t', [0, 3600])
def test_unknown_or_future_time_shows_age_unknown_and_is_old(page, app_url, t):
    boot(page, app_url)
    feed(page, node(ALPHA, 'Alpha', 'ALP', dict(lat=HOME[0] + 0.001, lon=HOME[1], time=(SEC + t) if t else 0), 0))
    wait_pins(page, 1)
    p = pins(page)[0]
    assert p['age'] == 'age unknown' and p['cls'] == 'tm-pin old' and 'ago' not in p['age']
    page.click('#map .tm-pin')
    page.wait_for_selector('#dlgMate[open]')
    assert 'ago' not in page.inner_text('#tmAge') and 'unknown' in page.inner_text('#tmAge')


def test_my_own_radio_is_not_drawn(page, app_url):
    boot(page, app_url)
    feed(page, node(ALPHA, 'Alpha', 'ALP', pos(), 0))
    feed(page, node(BRAVO, 'Bravo', 'BRV', pos(-0.001), 0))
    wait_pins(page, 2)
    feed(page, dict(type='myInfo', myNodeNum=BRAVO))   # this phone's radio turns out to be Bravo
    wait_pins(page, 1)
    feed(page, node(BRAVO, 'Bravo', 'BRV', pos(-0.002), 0))
    page.wait_for_timeout(150)
    assert [x['name'] for x in pins(page)] == ['Alpha']


def test_a_name_with_markup_is_text_in_the_pin_and_the_sheet(page, app_url):
    boot(page, app_url)
    feed(page, node(ALPHA, EVIL, 'EV', pos(), 0))
    wait_pins(page, 1)
    assert pins(page)[0]['name'] == EVIL
    assert ev(page, "document.querySelectorAll('#map .tm-pin img, #map .tm-pin script').length") == 0
    page.click('#map .tm-pin')
    page.wait_for_selector('#dlgMate[open]')
    assert page.inner_text('#tmTitle') == EVIL
    assert ev(page, "document.querySelectorAll('#dlgMate img').length") == 0 and ev(page, 'window.__x') is None


def test_tap_opens_the_sheet_with_grid_distance_and_age(page, app_url):
    boot(page, app_url)
    set_fix(page, *HOME)
    center(page, *HOME)
    feed(page, node(ALPHA, 'Alpha', 'ALP', pos(0.001), 0))
    wait_pins(page, 1)
    page.click('#map .tm-pin')
    page.wait_for_selector('#dlgMate[open]')
    assert page.inner_text('#tmTitle') == 'Alpha' and 'Teammate' in page.inner_text('#dlgMate')
    assert page.inner_text('#tmGrid') == ev(page, '([a, b]) => GEO.toMGRS(a, b).text', [HOME[0] + 0.001, HOME[1]])
    rel = page.inner_text('#tmRel')
    assert rel == ev(page, "FK.relText(%r, %r, m => TGEOM.fmtDist(m, FK.tac.unit()))" % (HOME[0] + 0.001, HOME[1]))
    assert rel.endswith(' m at 0° true from you') and 105 <= float(rel.split(' ')[0]) <= 115, rel   # 0.001 degree of latitude
    assert page.inner_text('#tmAge') == 'Position from 4 min ago'
    assert ev(page, 'FK.sheet.top() && FK.sheet.top().id') == 'dlgMate'


def test_distance_line_is_left_out_with_no_fix(page, app_url):
    boot(page, app_url)
    feed(page, node(ALPHA, 'Alpha', 'ALP', pos(), 0))
    wait_pins(page, 1)
    page.click('#map .tm-pin')
    page.wait_for_selector('#dlgMate[open]')
    expect(page.locator('#tmRel')).to_be_hidden()


def test_go_to_sets_a_point_target_and_closes(page, app_url):
    boot(page, app_url)
    set_fix(page, *HOME)
    feed(page, node(ALPHA, 'Alpha', 'ALP', pos(0.002), 0))
    wait_pins(page, 1)
    page.click('#map .tm-pin')
    page.wait_for_selector('#dlgMate[open]')
    page.click('#tmGo')
    page.wait_for_function("!document.querySelector('#dlgMate').open")
    t = ev(page, 'FK.tac.target()')
    assert t == {'type': 'point', 'lat': HOME[0] + 0.002, 'lon': HOME[1], 'name': 'Alpha'}
    assert ev(page, 'FK.tac.markers().length') == 0   # a teammate never becomes a saved marker


def test_the_sheet_is_read_only_and_closes_with_close_and_back(page, app_url):
    boot(page, app_url)
    feed(page, node(ALPHA, 'Alpha', 'ALP', pos(), 0))
    wait_pins(page, 1)
    page.click('#map .tm-pin')
    page.wait_for_selector('#dlgMate[open]')
    assert page.eval_on_selector_all('#dlgMate button', 'b => b.map(x => x.textContent.trim())') == ['Go to', 'Close']
    assert page.eval_on_selector_all('#dlgMate input, #dlgMate textarea', 'x => x.length') == 0
    txt = page.inner_text('#dlgMate')
    assert 'Save' not in txt and 'Delete' not in txt and 'Edit' not in txt and 'waypoint' not in txt.lower()
    assert ev(page, "document.querySelector('#dlgMate').getAttribute('aria-labelledby')") == 'tmTitle'
    page.click('#tmClose')
    page.wait_for_function("!document.querySelector('#dlgMate').open")
    page.click('#map .tm-pin')
    page.wait_for_selector('#dlgMate[open]')
    page.go_back()
    page.wait_for_function("!document.querySelector('#dlgMate').open")
    assert ev(page, 'location.hash') == '#/tactical/map'


def test_the_sheet_sizes_from_content_on_safari(page, app_url):
    boot(page, app_url)
    feed(page, node(ALPHA, 'Alpha', 'ALP', pos(), 0))
    wait_pins(page, 1)
    page.click('#map .tm-pin')
    page.wait_for_selector('#dlgMate[open]')
    assert ev(page, SHEET_BASIS, '#dlgMate') == []
    assert 'mk-sheet' in page.get_attribute('#dlgMate', 'class')


def test_an_open_sheet_follows_a_new_position(page, app_url):
    boot(page, app_url)
    feed(page, node(ALPHA, 'Alpha', 'ALP', pos(), 0))
    wait_pins(page, 1)
    page.click('#map .tm-pin')
    page.wait_for_selector('#dlgMate[open]')
    before = page.inner_text('#tmGrid')
    feed(page, node(ALPHA, 'Alpha', 'ALP', pos(0.01), 0))
    page.wait_for_function("t => document.querySelector('#tmGrid').textContent !== t", arg=before)
    page.click('#tmGo')
    t = ev(page, 'FK.tac.target()')
    assert abs(t['lat'] - (HOME[0] + 0.01)) < 1e-9


def test_pins_sit_under_marker_pins_and_the_layer_is_between_areas_and_markers(page, app_url):
    boot(page, app_url, markers=[mk('m', 'Gate', lat=HOME[0] + 0.001, lon=HOME[1])], view=(HOME[0] + 0.001, HOME[1]))
    feed(page, node(ALPHA, 'Alpha', 'ALP', pos(0.001), 0))   # the same spot as the marker
    wait_pins(page, 1)
    ids = ev(page, "(() => { const m = FK.leafletMap(); return [m._fkAreas, m._fkTeam, m._fkWps].map(g => L.stamp(g)); })()")
    assert ids == sorted(ids) and len(set(ids)) == 3
    top = ev(page, """() => { const r = document.querySelector('#map .tm-pin').getBoundingClientRect();
      const e = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
      return e && (e.closest('.mk-pin') ? 'marker' : e.closest('.tm-pin') ? 'teammate' : e.className); }""")
    assert top == 'marker'
    # a tap there opens the marker, not the teammate
    page.click('#map .mk-pin i')
    page.wait_for_selector('#dlgMarker[open]')
    assert not ev(page, "document.querySelector('#dlgMate').open")


def test_pins_are_inert_while_a_tool_mode_is_on(page, app_url):
    boot(page, app_url)
    feed(page, node(ALPHA, 'Alpha', 'ALP', pos(0.002), 0))
    wait_pins(page, 1)
    ev(page, "FK.mapTools.start('route')")
    expect(page.locator('#toolBar')).to_be_visible()
    page.click('#map .tm-pin')
    page.wait_for_timeout(200)
    assert not ev(page, "document.querySelector('#dlgMate').open")


def test_nothing_is_drawn_and_no_timer_runs_while_the_switch_is_off(page, app_url):
    stored = [dict(num=ALPHA, long='Alpha', short='ALP', lat=HOME[0] + 0.001, lon=HOME[1], t=NOW - 60_000, heard=NOW - 60_000)]
    boot(page, app_url, on=False, meshTeam=stored)
    page.wait_for_timeout(200)
    assert ev(page, 'FK.mesh.teammates().length') == 1   # the data is there ...
    assert page.locator('#map .tm-pin').count() == 0     # ... and nothing is drawn
    assert ev(page, 'FK.team.timerOn()') is False
    assert ev(page, "FK.leafletMap()._fkTeam.getLayers().length") == 0


def test_turning_the_switch_off_removes_the_pins_and_stops_the_timer(page, app_url):
    boot(page, app_url)
    feed(page, node(ALPHA, 'Alpha', 'ALP', pos(), 0))
    wait_pins(page, 1)
    assert ev(page, 'FK.team.timerOn()') is True
    page.click('#map .tm-pin')
    page.wait_for_selector('#dlgMate[open]')
    ev(page, 'FK.mesh.setEnabled(false)')
    wait_pins(page, 0)
    page.wait_for_function("!document.querySelector('#dlgMate').open")
    assert ev(page, 'FK.team.timerOn()') is False
    ev(page, 'FK.mesh.setEnabled(true)')
    assert ev(page, 'FK.team.timerOn()') is True


def test_a_public_channel_draws_nothing(page, app_url):
    boot(page, app_url, private=False)
    chan(page, psk=b'', precision=0)   # public
    page.wait_for_timeout(100)
    assert page.locator('#map .tm-pin').count() == 0


def test_bursts_of_team_events_redraw_once_per_frame(page, app_url):
    boot(page, app_url)
    n = ev(page, """async () => {
      let calls = 0; const real = FK.team.render;
      FK.team.render = () => { calls++; return real(); };
      for (let i = 0; i < 100; i++) FK._test.mesh.feed({ type: 'nodeInfo', num: 0x0B000000 + i, longName: 'N' + i, shortName: 'N',
        position: { lat: 43.0 + i / 10000, lon: -76.0, time: %d }, lastHeard: 0, channel: 0 });
      await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
      FK.team.render = real;
      return calls;
    }""" % (SEC - 60))
    assert n == 1, n
    wait_pins(page, 100)


def test_no_pins_are_drawn_before_the_map_exists(page, app_url):
    """A team event with the map screen never opened draws nothing and breaks nothing (a console error fails the test)."""
    boot_map_no_map(page, app_url)
    feed(page, node(ALPHA, 'Alpha', 'ALP', pos(), 0))
    page.wait_for_timeout(150)
    assert ev(page, '!FK.leafletMap()') is True and ev(page, 'FK.team.timerOn()') is False
    ev(page, "FK.route.go('/tactical/map')")
    page.wait_for_function("document.querySelector('#map .leaflet-pane')")
    wait_pins(page, 1)


def boot_map_no_map(page, app_url):
    from .tac import store
    page.clock.install(time=NOW / 1000)
    page.goto('about:blank')
    store(page, meshOn=True, advAck=True)
    page.goto(app_url + '#/survival')
    page.wait_for_function('window.FK && FK.mesh && FK.team')
    chan(page, psk=PRIV, precision=32)


def test_the_night_theme_keeps_the_ring_round_and_the_friend_a_rectangle(page, app_url):
    boot(page, app_url, night=True, markers=[mk('f', 'Mike', lat=HOME[0] - 0.002, kind='friend', t=NOW - 60_000)])
    feed(page, node(ALPHA, 'Alpha', 'ALP', pos(0.002), 0))
    wait_pins(page, 1)
    r = ev(page, """() => { const t = document.querySelector('#map .tm-pin i'), f = document.querySelector('#map .mk-pin[data-kind=friend] svg rect');
      return { round: getComputedStyle(t).borderRadius, border: getComputedStyle(t).borderTopWidth, rect: !!f, circle: !!document.querySelector('#map .tm-pin i svg circle') }; }""")
    assert r['round'] == '50%' and r['border'] == '3px' and r['rect'] is True


@pytest.mark.parametrize('ahead,fresh', [(5, True), (119, True), (121, False), (None, False)])
def test_a_slightly_fast_radio_clock_reads_as_now_and_the_two_lists_agree(page, app_url, ahead, fresh):
    """Up to 2 min ahead of the phone: fresh pin, youngest age. More, or t = 0: age unknown, old. The Radio sheet says the same."""
    boot(page, app_url)
    t = 0 if ahead is None else SEC + ahead
    feed(page, node(ALPHA, 'Alpha', 'ALP', dict(lat=HOME[0] + 0.001, lon=HOME[1], time=t), 0))
    wait_pins(page, 1)
    p = pins(page)[0]
    if fresh:
        assert p['cls'] == 'tm-pin' and p['age'] == '1 min ago', p
    else:
        assert p['cls'] == 'tm-pin old' and p['age'] == 'age unknown', p
    ev(page, "FK._test.mesh.link('on', 'Radio')")   # the list shows while the link is on
    ev(page, "FK.radioSheet.open()")
    page.wait_for_selector('#dlgRadio[open]')
    page.wait_for_function("document.querySelectorAll('#rdTeam > li').length > 0")
    row = page.eval_on_selector_all('#rdTeam > li', 'els => els.map(e => e.innerText.replace(/\\s+/g, " ").trim()).filter(x => x.startsWith("Alpha"))')[0]
    assert row.endswith(p['age']), (row, p)
    page.keyboard.press('Escape')
    page.wait_for_function("!document.querySelector('#dlgRadio').open")
    page.click('#map .tm-pin')
    page.wait_for_selector('#dlgMate[open]')
    sheet = page.inner_text('#tmAge')
    assert sheet == ('Position from 1 min ago' if fresh else 'Position time unknown')
