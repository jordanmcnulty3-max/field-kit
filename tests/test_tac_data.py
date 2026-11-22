"""FK.tac: markers, shapes, target and unit. Storage keys stay wps, target; new keys are shapes and distUnit."""
import json

import pytest

from .tac import store

FULL = 'Couldn’t save: phone storage for Field Kit is full. Back up, then delete old tracks or saved maps.'
W1 = {'id': 'w1', 'name': 'Camp', 'lat': 43.01, 'lon': -76.02, 'alt': 120, 't': 1}
W2 = {'id': 'w2', 'name': 'Spring', 'lat': 43.2, 'lon': -76.1, 'alt': None, 't': 2}


@pytest.fixture
def ready(page, app_url):
    def go(hash_='', **seed):
        page.goto('about:blank')
        store(page, advAck=True, **seed)
        page.goto(app_url + hash_)
        page.wait_for_function('window.FK && FK.tac && FK.route')
        return page
    return go


def ev(page, expr, arg=None):
    return page.evaluate(expr, arg)


def ls(page, key):
    return page.evaluate('k => localStorage.getItem("fk." + k)', key)


def test_v77_waypoints_load_as_point_markers(ready):
    page = ready(wps=[W1, W2], target='w1')
    ms = ev(page, 'FK.tac.markers()')
    assert [m['id'] for m in ms] == ['w1', 'w2']
    assert all(m['kind'] == 'point' and m['note'] == '' for m in ms)
    assert ms[0]['alt'] == 120 and ms[1]['alt'] is None
    assert ev(page, 'FK.tac.target()') == {'type': 'marker', 'id': 'w1'}


def test_bad_records_are_dropped(ready):
    bad = [dict(W1, id='b1', lat=999), dict(W1, id=42), dict(W1, id='b3', kind='<img>'), dict(W1, id='b4', note='x' * 5000),
           dict(W1, id='b5', kind='camp', note=7), 'junk', None, dict(W1, id='b7', lon='x')]
    page = ready(wps=bad)   # the harness fails the test on any console error
    ms = {m['id']: m for m in ev(page, 'FK.tac.markers()')}
    assert sorted(ms) == ['b3', 'b4', 'b5']
    assert ms['b3']['kind'] == 'point'
    assert len(ms['b4']['note']) == 500
    assert ms['b5']['kind'] == 'camp' and ms['b5']['note'] == ''


def shape(type_, n, **kw):
    return dict({'id': f's{type_}{n}', 'type': type_, 'name': '', 'pts': [[43 + i * 0.001, -76] for i in range(n)], 't': 1}, **kw)


def test_shapes_validate(ready):
    seeded = [shape('route', 1), shape('area', 2), shape('ring', 1, r=[]), shape('ring', 1, r=[0]),
              shape('ring', 1, r=[1, 2, 3, 4]), shape('route', 201), dict(shape('route', 3), type='blob'),
              dict(shape('route', 3), id='bad id!'), shape('route', 2), shape('area', 3), shape('ring', 1, r=[100, 200])]
    page = ready(shapes=seeded)
    got = ev(page, 'FK.tac.shapes()')
    assert [s['id'] for s in got] == ['sroute2', 'sarea3', 'sring1']
    assert [s['name'] for s in got] == ['Route 1', 'Area 1', 'Ring 1']
    assert got[2]['r'] == [100, 200]
    # the same rules on the way in: refused, nothing stored
    assert ev(page, 'FK.tac.addShape({ type: "route", pts: [[43, -76]] })') is None
    assert ev(page, 'FK.tac.addShape({ type: "ring", pts: [[43, -76]], r: [] })') is None
    assert len(ev(page, 'FK.tac.shapes()')) == 3


def test_shape_add_update_remove_and_default_names(ready):
    page = ready()
    s = ev(page, 'FK.tac.addShape({ type: "route", pts: [[43, -76], [43.01, -76]] })')
    assert s['name'] == 'Route 1' and s['type'] == 'route'
    assert ev(page, 'FK.tac.addShape({ type: "route", pts: [[43, -76], [43.02, -76]] }).name') == 'Route 2'
    assert ev(page, 'id => FK.tac.updateShape(id, { name: "Loop" })', s['id']) is True
    assert json.loads(ls(page, 'shapes'))[0]['name'] == 'Loop'
    ev(page, 'id => FK.tac.removeShape(id)', s['id'])
    assert [x['name'] for x in ev(page, 'FK.tac.shapes()')] == ['Route 2']


def test_shape_limits(ready):
    page = ready()
    res = ev(page, """() => { const out = [];
      for (let i = 0; i < 101; i++) out.push(FK.tac.addShape({ type: 'route', pts: [[43, -76], [43.001, -76]] }));
      return [out.slice(0, 100).every(x => x && x.id), out[100], FK.tac.shapes().length]; }""")
    assert res == [True, 'limit', 100]
    assert ev(page, 'FK.tac.addShape({ type: "route", pts: Array.from({ length: 201 }, (_, i) => [43 + i / 1e4, -76]) })') is None


def test_marker_add_update_remove(ready):
    page = ready()
    m = ev(page, 'FK.tac.addMarker({ lat: 43, lon: -76, name: " Ridge ", kind: "water", note: "good", alt: 100 })')
    assert m['name'] == 'Ridge' and m['kind'] == 'water' and m['note'] == 'good' and m['alt'] == 100
    assert ev(page, 'FK.tac.addMarker({ lat: 43.01, lon: -76 }).name') == 'WP 2'
    assert ev(page, 'FK.tac.addMarker({ lat: 43.01, lon: -76, kind: "zzz" }).kind') == 'point'
    assert ev(page, 'FK.tac.addMarker({ lat: 999, lon: -76 })') is None
    assert ev(page, '([id]) => FK.tac.updateMarker(id, { name: "Top", kind: "hazard", note: "n" })', [m['id']]) is True
    assert ev(page, '([id]) => FK.tac.updateMarker(id, { lat: 500 })', [m['id']]) is False
    assert ev(page, 'FK.tac.updateMarker("nope", { name: "x" })') is False
    stored = json.loads(ls(page, 'wps'))
    assert stored[0]['name'] == 'Top' and stored[0]['kind'] == 'hazard' and stored[0]['lat'] == 43
    ev(page, 'id => FK.tac.removeMarker(id)', m['id'])
    assert len(json.loads(ls(page, 'wps'))) == 2


def test_events_fire(ready):
    page = ready()
    got = ev(page, """() => { const seen = []; ['wps', 'shapes', 'target', 'unit'].forEach(e => FK.on(e, () => seen.push(e)));
      const m = FK.tac.addMarker({ lat: 43, lon: -76 });
      FK.tac.addShape({ type: 'route', pts: [[43, -76], [43.01, -76]] });
      FK.tac.setTarget({ type: 'marker', id: m.id }); FK.tac.setUnit('metric'); return seen; }""")
    assert {'wps', 'shapes', 'target', 'unit'} <= set(got)


def test_storage_full_keeps_the_marker_on_screen(page, app_url):
    page.goto('about:blank')
    store(page, advAck=True)
    page.add_init_script("""(() => { const set = Storage.prototype.setItem;
      Storage.prototype.setItem = function (k, v) { if (k === 'fk.wps') throw new DOMException('full', 'QuotaExceededError'); return set.call(this, k, v); }; })()""")
    page.goto(app_url)
    page.wait_for_function('window.FK && FK.tac')
    assert ev(page, 'FK.tac.addMarker({ lat: 43, lon: -76, name: "Camp" })') is None
    assert ev(page, 'FK.tac.markers().length') == 1
    assert page.inner_text('#toast') == FULL


def test_target_survives_reload_and_stale_target_is_dropped(ready):
    page = ready(wps=[W1, W2], shapes=[shape('route', 3)], target='w2')
    assert ev(page, 'FK.tac.target()') == {'type': 'marker', 'id': 'w2'}
    assert ev(page, 'FK.tac.setTarget({ type: "route", id: "sroute3", i: 1 })') is True
    assert json.loads(ls(page, 'target')) == {'type': 'route', 'id': 'sroute3', 'i': 1}
    page.reload()
    page.wait_for_function('window.FK && FK.tac')
    assert ev(page, 'FK.tac.target()') == {'type': 'route', 'id': 'sroute3', 'i': 1}
    p = ev(page, 'FK.tac.targetPoint()')
    assert p['lat'] == pytest.approx(43.001) and p['step'] == [1, 3]
    ev(page, 'FK.tac.setTarget({ type: "point", lat: 43.5, lon: -76.5, name: "Start" })')
    page.reload()
    page.wait_for_function('window.FK && FK.tac')
    assert ev(page, 'FK.tac.target()') == {'type': 'point', 'lat': 43.5, 'lon': -76.5, 'name': 'Start'}
    assert ev(page, 'FK.tac.targetPoint()') == {'lat': 43.5, 'lon': -76.5, 'name': 'Start'}
    # a marker target goes back to the plain id string v7.7 wrote
    ev(page, 'FK.tac.setTarget({ type: "marker", id: "w1" })')
    assert json.loads(ls(page, 'target')) == 'w1'
    assert ev(page, 'FK.tac.targetPoint().name') == 'Camp'
    # deleting the target's marker or route clears it
    ev(page, 'FK.tac.removeMarker("w1")')
    assert ev(page, 'FK.tac.target()') is None and json.loads(ls(page, 'target')) is None
    ev(page, 'FK.tac.setTarget({ type: "route", id: "sroute3", i: 0 })')
    ev(page, 'FK.tac.removeShape("sroute3")')
    assert ev(page, 'FK.tac.target()') is None
    # anything pointing at nothing is refused
    assert ev(page, 'FK.tac.setTarget({ type: "marker", id: "gone" })') is False
    assert ev(page, 'FK.tac.setTarget({ type: "route", id: "gone", i: 0 })') is False
    assert ev(page, 'FK.tac.setTarget(null)') is True


@pytest.mark.parametrize('stored', ['gone', {'type': 'route', 'id': 'nope', 'i': 0}, {'type': 'route', 'id': 'sroute3', 'i': 9},
                                     {'type': 'point', 'lat': 'x', 'lon': 1, 'name': 'a'}, 42, ['w1']])
def test_stale_target_is_dropped_on_load(ready, stored):
    page = ready(wps=[W1], shapes=[shape('route', 3)], target=stored)
    assert ev(page, 'FK.tac.target()') is None
    assert ev(page, 'FK.tac.targetPoint()') is None


def test_unit_defaults_and_persists(ready):
    page = ready()
    assert ev(page, 'FK.tac.unit()') == 'metric'
    assert ls(page, 'distUnit') is None   # nothing is written at startup
    ev(page, 'FK.tac.setUnit("us")')
    assert json.loads(ls(page, 'distUnit')) == 'us'
    ev(page, 'FK.tac.setUnit("furlongs")')
    assert ev(page, 'FK.tac.unit()') == 'us'
    page.reload()
    page.wait_for_function('window.FK && FK.tac')
    assert ev(page, 'FK.tac.unit()') == 'us'


@pytest.mark.parametrize('junk', ['furlongs', 7, None, ['us']])
def test_junk_stored_unit_reads_as_metric(ready, junk):
    page = ready(distUnit=junk)
    assert ev(page, 'FK.tac.unit()') == 'metric'


def test_kinds(ready):
    page = ready()
    ks = ev(page, 'FK.tac.KINDS')
    assert [k['id'] for k in ks] == ['point', 'camp', 'vehicle', 'water', 'cache', 'hazard', 'rally', 'observe', 'medical',
                                       'friend', 'hostile', 'neutral', 'unknown']
    assert [k['label'] for k in ks] == ['Point', 'Camp', 'Vehicle', 'Water', 'Cache', 'Hazard', 'Rally point', 'Observation point',
                                         'Medical', 'Friend', 'Hostile', 'Neutral', 'Unknown']
    assert {k['group'] for k in ks[:9]} == {'place'} and {k['group'] for k in ks[9:]} == {'affil'}


def backup(page, tmp_path):
    page.click('#menuBtn')
    page.wait_for_selector('#dlgMenu[open]')
    with page.expect_download() as d:
        page.click('#bkSave')
    path = tmp_path / 'b.json'
    d.value.save_as(path)
    return json.loads(path.read_text())


def test_backup_carries_markers_shapes_unit(ready, tmp_path):
    page = ready(wps=[dict(W1, kind='camp', note='north side')], shapes=[shape('route', 3)], distUnit='metric', target='w1')
    b = backup(page, tmp_path)
    for k in ('fk.wps', 'fk.shapes', 'fk.distUnit', 'fk.target'):
        assert k in b['data'], k
    assert json.loads(b['data']['fk.wps'])[0]['note'] == 'north side'
    assert json.loads(b['data']['fk.distUnit']) == 'metric'


def test_restore_of_a_v77_backup_and_confirm_wording(ready, tmp_path):
    page = ready()
    old = {'app': 'Field Kit', 'version': '7.7', 'saved': '2026-11-10T14:30:00.000Z',
           'data': {'fk.wps': json.dumps([W1, W2]), 'fk.target': json.dumps('w2')}}
    path = tmp_path / 'old.json'
    path.write_text(json.dumps(old))
    page.click('#menuBtn')
    page.wait_for_selector('#dlgMenu[open]')
    page.set_input_files('#bkFile', str(path))
    page.wait_for_selector('#bkConfirm:not([hidden])')
    assert 'markers, routes and areas' in page.inner_text('#bkAsk')
    page.click('#bkGo')
    page.wait_for_timeout(ev(page, 'FK.tools.confirm.ignoreMs') + 100)
    with page.expect_navigation():
        page.click('#bkGo')
    page.wait_for_function('window.FK && FK.tac')
    ms = ev(page, 'FK.tac.markers()')
    assert [m['id'] for m in ms] == ['w1', 'w2'] and all(m['kind'] == 'point' for m in ms)
    assert ev(page, 'FK.tac.target()') == {'type': 'marker', 'id': 'w2'}
    assert ev(page, 'FK.tac.shapes()') == []


def test_far_north_marker_has_no_grid(ready, app_url):
    page = ready('#/tactical/position', wps=[dict(W1, id='n1', name='Pole camp', lat=85, lon=10)], mapView={'lat': 85, 'lon': 10, 'z': 8})
    assert ev(page, 'FK.tac.markers().length') == 1
    page.click('#wpOpenList')
    page.wait_for_selector('#dlgList[open] #lsList li')
    txt = page.inner_text('#lsList')
    assert 'Pole camp' in txt and 'null' not in txt and 'undefined' not in txt and '85.00000, 10.00000' in txt
    page.click('#lsList li button')
    page.wait_for_selector('#dlgMarker[open]')
    txt = page.inner_text('#dlgMarker')
    assert '85.00000, 10.00000' in txt and 'null' not in txt and 'undefined' not in txt
    assert page.locator('.mk-pin[data-id="n1"] b').inner_text() == 'Pole camp'
    assert page.locator('.leaflet-popup').count() == 0


def test_fix_and_heading_hooks(ready):
    page = ready('#/tactical/position', declMode='manual')   # By hand, nothing typed: the heading stays magnetic
    ev(page, 'FK._test.fix({ lat: 43, lon: -76, acc: 8, alt: 100, spd: 1.5 })')
    assert ev(page, 'FK.getFix().lat') == 43 and ev(page, 'FK.getFix().acc') == 8
    assert '±8 m' in page.inner_text('#sAcc')
    got = ev(page, "() => new Promise(r => { FK.on('heading', h => r(h)); FK._test.heading(53); })")
    assert got == pytest.approx(53, abs=0.01)


def test_editing_a_route_keeps_the_target_valid(ready):
    page = ready(shapes=[shape('route', 3)], target={'type': 'route', 'id': 'sroute3', 'i': 2})
    n = ev(page, """() => { window.__n = 0; FK.on('target', () => window.__n++);
      return FK.tac.updateShape('sroute3', { pts: [[43, -76], [43.001, -76]] }); }""")
    assert n is True
    assert ev(page, 'FK.tac.target()') == {'type': 'route', 'id': 'sroute3', 'i': 1}
    assert ev(page, 'FK.tac.targetPoint()')['lat'] == pytest.approx(43.001)
    assert ev(page, 'window.__n') == 1
    assert json.loads(ls(page, 'target'))['i'] == 1
    ev(page, 'FK.tac.updateShape("sroute3", { name: "Renamed" })')
    assert ev(page, 'window.__n') == 1   # unchanged target, no event
    # no longer a route: cleared
    ev(page, 'FK.tac.updateShape("sroute3", { type: "area", pts: [[43, -76], [43.001, -76], [43.001, -75.999]] })')
    assert ev(page, 'FK.tac.shapes()[0].type') == 'area'
    assert ev(page, 'FK.tac.target()') is None and ev(page, 'FK.tac.targetPoint()') is None
    assert ev(page, 'window.__n') == 2


@pytest.mark.parametrize('bad', [{'type': 'route', 'id': 'sroute3', 'i': 99}, {'type': 'route', 'id': 'sroute3', 'i': -1},
                                  {'type': 'route', 'id': 'sroute3', 'i': 'x'}, {'type': 'route', 'i': 1}, {'type': 'marker'},
                                  {'type': 'route', 'id': 'sroute3'}, 'toString', {'type': 'point'}])
def test_target_point_never_throws_on_corrupt_target(ready, bad):
    page = ready(shapes=[shape('route', 3)], target=bad)
    assert ev(page, 'FK.tac.targetPoint()') is None   # a thrown error would also fail the test teardown


def test_ids_are_unique_however_fast_items_are_added(ready):
    page = ready(wps=[dict(W1, id='m1')])
    res = ev(page, """() => { for (let i = 0; i < 500; i++) FK.tac.addMarker({ lat: 43, lon: -76 });
      for (let i = 0; i < 100; i++) FK.tac.addShape({ type: 'route', pts: [[43, -76], [43.001, -76]] });
      const ids = [...FK.tac.markers(), ...FK.tac.shapes()].map(x => x.id);
      return [ids.length, new Set(ids).size]; }""")
    assert res == [601, 601]


def test_repeated_ids_keep_the_first_on_load(ready):
    page = ready(wps=[dict(W1, name='First'), dict(W1, name='Second'), W2],
                 shapes=[dict(shape('route', 2), name='A'), dict(shape('route', 2), name='B')])
    assert [m['name'] for m in ev(page, 'FK.tac.markers()')] == ['First', 'Spring']
    assert [s['name'] for s in ev(page, 'FK.tac.shapes()')] == ['A']


def test_names_are_cut_to_60(ready):
    long = 'n' * 10000
    page = ready(wps=[dict(W1, name=long)], shapes=[dict(shape('route', 2), name=long)], target={'type': 'point', 'lat': 43, 'lon': -76, 'name': long})
    assert len(ev(page, 'FK.tac.markers()[0].name')) == 60
    assert len(ev(page, 'FK.tac.shapes()[0].name')) == 60
    assert len(ev(page, 'FK.tac.target().name')) == 60
    assert len(ev(page, 'n => FK.tac.addMarker({ lat: 43, lon: -76, name: n }).name', long)) == 60
    assert len(ev(page, 'n => FK.tac.addShape({ type: "route", pts: [[43, -76], [43.01, -76]], name: n }).name', long)) == 60
    ev(page, 'n => { FK.tac.updateMarker("w1", { name: n }); FK.tac.updateShape("sroute2", { name: n }); }', long)
    assert len(ev(page, 'FK.tac.markers()[0].name')) == 60 and len(ev(page, 'FK.tac.shapes()[0].name')) == 60


def test_update_marker_only_takes_its_own_fields(ready):
    page = ready(wps=[W1])
    before = ls(page, 'wps')
    for patch in ['{ constructor: 1 }', '{ toString: 1 }', '{ __proto__: {} }', '{}', 'JSON.parse(\'{"__proto__": {"name": "x"}}\')',
                  '{ name: "ok", constructor: 1 }']:
        assert ev(page, f'FK.tac.updateMarker("w1", {patch})') is False, patch
    assert ev(page, 'FK.tac.markers()[0].name') == 'Camp' and ls(page, 'wps') == before


# ---------- The shared record (marker.net, comms Task 6) ----------
NET = {'wid': 5, 'from': 0x0A0B0C02, 'by': 'Bravo', 't': 1, 'chBy': '', 'chT': 0, 'icon': 0, 'expire': 0, 'pending': False, 'rx': False}


def test_net_is_kept_only_when_well_formed(ready):
    page = ready(wps=[dict(W1, net=NET), dict(W2, net=dict(NET, wid=0)), dict(W1, id='w3', net=dict(NET, wid=6, by='b' * 99, chBy='c' * 99)),
                      dict(W1, id='w4', net=dict(NET, wid=7, icon=0x1F600)), dict(W1, id='w5', kind='camp', net=dict(NET, wid=8, icon=0x1F600)),
                      dict(W1, id='w6', net=dict(NET, wid=9, icon=0x26FA)), dict(W1, id='w7', net=dict(NET, extra=1, wid=10)),
                      dict(W1, id='w8', net=NET)])   # a repeated wid: the first keeps it
    ms = {m['id']: m for m in ev(page, 'FK.tac.markers()')}
    assert ms['w1']['net'] == NET and 'net' not in ms['w2'] and 'net' not in ms['w8']
    assert (len(ms['w3']['net']['by']), len(ms['w3']['net']['chBy'])) == (40, 40)
    assert ms['w4']['net']['icon'] == 0x1F600                 # a foreign icon on a Point is kept
    assert ms['w5']['net']['icon'] == 0 and ms['w6']['net']['icon'] == 0   # never on another kind, never a known icon
    assert ms['w7']['net'] == dict(NET, wid=10)               # only the known fields


def test_set_net_and_add_shared(ready):
    page = ready(wps=[W1, W2])
    assert ev(page, 'n => FK.tac.setNet("w1", n)', NET) is True
    assert ev(page, 'FK.tac.markers()[0].net.wid') == 5
    assert ev(page, 'n => FK.tac.setNet("w2", n)', NET) is False             # a wid another marker holds
    assert ev(page, 'n => FK.tac.setNet("w2", n)', dict(NET, wid=6, rx='no')) is False
    assert ev(page, 'n => FK.tac.setNet("nope", n)', dict(NET, wid=6)) is False
    assert json.loads(ls(page, 'wps'))[0]['net']['wid'] == 5
    assert ev(page, 'FK.tac.setNet("w1", null)') is True
    assert 'net' not in ev(page, 'FK.tac.markers()[0]')
    m = ev(page, 'n => FK.tac.addShared({ name: " Spring ", lat: 43.01, lon: -76, kind: "water", note: "n".repeat(900), t: 7, net: n })',
           dict(NET, wid=11))
    assert (m['name'], m['kind'], len(m['note']), m['t'], m['net']['wid'], m['alt']) == ('Spring', 'water', 500, 7, 11, None)
    assert ev(page, 'n => FK.tac.addShared({ name: "", lat: 43, lon: -76, kind: "zzz", note: 5, net: n }).name', dict(NET, wid=12)) == 'Marker'
    assert ev(page, 'n => FK.tac.addShared({ name: "x", lat: 43, lon: -76, net: n })', dict(NET, wid=11)) is None   # held
    assert ev(page, 'n => FK.tac.addShared({ name: "x", lat: 99, lon: -76, net: n })', dict(NET, wid=13)) is None
    assert ev(page, '() => FK.tac.addShared({ name: "x", lat: 43, lon: -76, net: null })') is None
    assert len(json.loads(ls(page, 'wps'))) == 4


def test_add_marker_never_takes_a_net(ready):
    page = ready()
    assert 'net' not in ev(page, 'n => FK.tac.addMarker({ lat: 43, lon: -76, name: "x", net: n })', NET)
    assert 'net' not in ev(page, 'n => FK.tac.addMarkers([{ lat: 43, lon: -76, name: "x", net: n }]).added[0]', NET)
    assert ev(page, 'n => FK.tac.updateMarker(FK.tac.markers()[0].id, { net: n })', NET) is False


def test_update_marker_takes_a_time(ready):
    page = ready(wps=[W1])
    assert ev(page, 'FK.tac.updateMarker("w1", { t: 1766000000000 })') is True
    assert ev(page, 'FK.tac.markers()[0].t') == 1766000000000
    assert ev(page, 'FK.tac.updateMarker("w1", { t: "soon" })') is False
    assert ev(page, 'FK.tac.updateMarker("w1", { t: Infinity })') is False


def test_batch_writes_once_and_emits_once(ready):
    page = ready(wps=[W1, W2])
    ev(page, 'FK.tac.setTarget({ type: "marker", id: "w2" })')
    r = ev(page, """n => { let writes = 0, events = 0; const set = Storage.prototype.setItem;
      Storage.prototype.setItem = function (k, v) { if (k === 'fk.wps') writes++; return set.call(this, k, v); };
      FK.on('wps', () => events++);
      const out = FK.tac.batch(() => { FK.tac.addShared({ name: 'a', lat: 43, lon: -76, net: n });
        FK.tac.updateMarker('w1', { name: 'b' }); FK.tac.removeMarker('w2'); FK.tac.setNet('w1', null); return 42; });
      const inside = [writes, events];
      Storage.prototype.setItem = set;
      return { inside, out, writes, events, n: FK.tac.markers().length }; }""", NET)
    assert r == {'inside': [1, 1], 'out': 42, 'writes': 1, 'events': 1, 'n': 2}
    assert ev(page, 'FK.tac.target()') is None and len(json.loads(ls(page, 'wps'))) == 2
    assert ev(page, '() => { let e = 0; FK.on("wps", () => e++); FK.tac.batch(() => {}); return e; }') == 0   # nothing changed
