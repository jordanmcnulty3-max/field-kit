"""Map tools: the Tools sheet, the tool modes (Measure, Route, Area, Move), Range ring, Go to grid, drawn shapes and the
shape sheet. Points are placed the way a person does it: move the map so the crosshair is on the spot, press Add point.

(tests/test_tools.py is the Emergency tools' file; these are the Tactical map's tools.)"""
import json

import pytest
from playwright.sync_api import expect

from .tac import store, open_map, set_fix
from .test_map import tiles_ok

HOME = (43.0, -76.0)
NOW = 1_800_000_000_000
FULL = 'Couldn’t save: phone storage for Field Kit is full. Back up, then delete old tracks or saved maps.'
HELP = 'Couldn’t read that location. Try a grid like 18T VN 12345 67890, or 43.0000, -76.0000, or 43°00′00″N 76°00′00″W.'
EVIL = '<img src=x onerror=window.x=1>'
ROWS = ['Measure', 'Route', 'Area', 'Range ring', 'Go to grid', 'Track recording', 'Save map for offline', 'Import', 'Export']


def mk(id_, name, lat=HOME[0], lon=HOME[1], kind='point', t=1):
    return {'id': id_, 'name': name, 'lat': lat, 'lon': lon, 'alt': 120, 't': t, 'kind': kind, 'note': ''}


def shape(id_, type_, pts, name=None, r=None, t=1):
    s = {'id': id_, 'type': type_, 'name': name or f'{type_.title()} {id_}', 'pts': pts, 't': t}
    if r is not None:
        s['r'] = r
    return s


def boot(page, app_url, markers=(), shapes=(), night=False, view=HOME, full=None, **kv):
    page.clock.install(time=NOW / 1000)
    page.goto('about:blank')
    tiles_ok(page)
    store(page, **{'wps': list(markers), 'shapes': list(shapes), 'advAck': True, 'night': night,
                   'mapView': {'lat': view[0], 'lon': view[1], 'z': 15}, 'mapFollow': False, **kv})
    if full:
        page.add_init_script("""(() => { const set = Storage.prototype.setItem;
          Storage.prototype.setItem = function (k, v) { if (k === %s) throw new DOMException('full', 'QuotaExceededError'); return set.call(this, k, v); }; })()"""
                             % json.dumps('fk.' + full))
    open_map(page, app_url)


def center(page, lat, lon, z=15):
    """Move the map so the crosshair is exactly here (a plain setView pans by whole pixels, up to 2 m off at zoom 15)."""
    page.evaluate('([a, b, z]) => FK.leafletMap().setView([a, b], z, { animate: false, reset: true })', [lat, lon, z])


def ev(page, js, arg=None):
    return page.evaluate(js, arg)


def dest(page, lat, lon, brg, m):
    return ev(page, 'a => { const p = TGEOM.dest(...a); return [p.lat, p.lon]; }', [lat, lon, brg, m])


def dist(page, a, b):
    return ev(page, '([a, b]) => GEO.distance(a[0], a[1], b[0], b[1])', [list(a), list(b)])


def map_center(page):
    return ev(page, '() => { const c = FK.leafletMap().getCenter().wrap(); return [c.lat, c.lng]; }')


def stored(page, key):
    return ev(page, 'k => JSON.parse(localStorage.getItem("fk." + k) || "null")', key)


def idx_ok(page):
    page.wait_for_timeout(50)
    assert ev(page, 'FK.route.index() === history.state.fkIdx')


def tap_at(page, lat, lon, dy=0):
    """Tap the map at a place, as a finger would (dy pixels below it)."""
    pt = ev(page, """([a, b]) => { const p = FK.leafletMap().latLngToContainerPoint([a, b]); const r = document.querySelector('#map').getBoundingClientRect();
      return [r.left + p.x, r.top + p.y]; }""", [lat, lon])
    page.mouse.click(pt[0], pt[1] + dy)


def tap_route(page):
    page.wait_for_selector('path.shp-hit[data-id="s1"]', state='attached')
    tap_at(page, 43.0, -75.995)   # the middle of ROUTE's first leg


def close_shape(page):
    page.click('#shClose')
    expect(page.locator('#dlgShape')).to_be_hidden()


def open_tools(page):
    page.click('#mTools')
    expect(page.locator('#dlgTools')).to_be_visible()


def tool(page, id_):
    open_tools(page)
    page.click(f'#dlgTools [data-tool="{id_}"]')
    expect(page.locator('#dlgTools')).to_be_hidden()


def start(page, mode):
    tool(page, mode)
    expect(page.locator('#toolBar')).to_be_visible()
    page.wait_for_function(f"FK.mapTools.mode() === '{mode}' && history.state.fkLayer")


def add(page, lat, lon):
    center(page, lat, lon)
    page.click('#tbAdd')


def read(page):
    return page.locator('#tbRead')


def toast(page):
    return page.locator('#toast')


def bar_closed(page):
    expect(page.locator('#toolBar')).to_be_hidden()
    page.wait_for_function('FK.mapTools.mode() === null && !history.state.fkLayer')


# ---------- Map buttons and the Tools sheet ----------

def test_four_map_buttons_and_the_tools_sheet_rows(page, app_url):
    boot(page, app_url)
    assert ev(page, "[...document.querySelectorAll('.mapctl button')].map(b => b.id)") == ['mLayers', 'mLocate', 'mTools', 'mList']
    open_tools(page)
    rows = page.locator('#dlgTools [data-tool]')
    assert [t.split('\n')[0] for t in rows.all_inner_texts()] == ROWS
    for i in range(rows.count()):
        b = rows.nth(i)
        assert b.bounding_box()['height'] >= 48
        expect(b.locator('.hint')).not_to_be_empty()
    expect(page.locator('#dlgTools [data-tool="measure"] .hint')).to_have_text('Distance and bearing between points')
    page.go_back()
    expect(page.locator('#dlgTools')).to_be_hidden()
    idx_ok(page)


def test_a_later_file_can_add_a_row(page, app_url):
    boot(page, app_url)
    ev(page, "FK.mapTools.addRow({ id: 'x', label: 'Extra', hint: 'Added later', run: () => { window.__ran = true; } })")
    open_tools(page)
    assert page.locator('#dlgTools [data-tool]').last.inner_text().startswith('Extra')
    page.click('#dlgTools [data-tool="x"]')
    page.wait_for_function('window.__ran === true')
    expect(page.locator('#dlgTools')).to_be_hidden()


def test_track_recording_and_save_map_open_from_tools(page, app_url):
    boot(page, app_url)
    tool(page, 'track')
    expect(page.locator('#dlgTrack')).to_be_visible()
    page.click('#trkClose')
    expect(page.locator('#dlgTrack')).to_be_hidden()
    tool(page, 'save')
    expect(page.locator('#dlgSave')).to_be_visible()
    page.go_back()
    expect(page.locator('#dlgSave')).to_be_hidden()
    idx_ok(page)
    assert ev(page, "typeof FK.map.openTrack === 'function' && typeof FK.map.openSave === 'function'")


def test_recording_chip_opens_track_recording(page, app_url):
    boot(page, app_url, recording=True)
    chip = page.locator('#recChip')
    expect(chip).to_be_visible()
    box = chip.bounding_box()
    assert box['height'] >= 44
    chip.click()
    expect(page.locator('#dlgTrack')).to_be_visible()


def test_recorded_track_saves_as_a_route_thinned_to_200_points(page, app_url):
    track = [[43.0 + i * 0.0001, -76.0, None, NOW + i * 1000] for i in range(450)]
    boot(page, app_url, track=track)
    tool(page, 'track')
    page.click('#trkRoute')
    expect(page.locator('#dlgTrack')).to_be_hidden()
    page.wait_for_function('FK.tac.shapes().length === 1')
    s = ev(page, 'FK.tac.shapes()[0]')
    assert s['type'] == 'route' and len(s['pts']) == 200
    assert s['pts'][0] == [43.0, -76.0] and s['pts'][-1] == [track[-1][0], -76.0]
    assert s['name'].startswith('Track ')
    expect(toast(page)).to_contain_text(s['name'])
    expect(page.locator(f'path.shp-route[data-id="{s["id"]}"]')).to_have_count(1)


def test_track_save_as_route_needs_two_points(page, app_url):
    boot(page, app_url, track=[[43.0, -76.0, None, NOW]])
    tool(page, 'track')
    expect(page.locator('#trkRoute')).to_be_disabled()


# ---------- Measure ----------

def test_measure_reads_distance_and_bearing_and_total(page, app_url):
    boot(page, app_url)
    start(page, 'measure')
    expect(read(page)).to_have_text('Move the map so the crosshair is on the first point.')
    expect(page.locator('#mMark')).to_be_hidden()
    expect(page.locator('#tbSaveRoute')).to_be_visible()
    a = HOME
    b = dest(page, *a, 90, 1000)
    add(page, *a)
    add(page, *b)
    expect(read(page)).to_contain_text('1.00 km at 90° true')
    c = dest(page, *b, 0, 500)
    add(page, *c)
    expect(read(page)).to_have_text('Leg 500 m at 0° true. Total 1.50 km.')
    # the leg follows the live crosshair, and the total includes it
    center(page, *dest(page, *c, 0, 250))
    expect(read(page)).to_have_text('Leg 250 m at 0° true. Total 1.75 km.')
    page.click('#tbUndo')
    expect(read(page)).to_contain_text('Total')
    assert ev(page, 'FK.mapTools.points().length') == 2


def test_measure_one_point_reads_live_as_the_map_moves(page, app_url):
    boot(page, app_url)
    start(page, 'measure')
    add(page, *HOME)
    center(page, *dest(page, *HOME, 180, 300))
    expect(read(page)).to_have_text('300 m at 180° true')
    center(page, *dest(page, *HOME, 270, 2000))
    expect(read(page)).to_have_text('2.00 km at 270° true')
    page.click('#tbUndo')
    expect(read(page)).to_have_text('Move the map so the crosshair is on the first point.')
    expect(page.locator('#tbUndo')).to_be_disabled()


def test_measure_done_keeps_nothing_and_save_as_route_stores_one(page, app_url):
    boot(page, app_url)
    start(page, 'measure')
    add(page, *HOME)
    add(page, *dest(page, *HOME, 45, 800))
    page.click('#tbDone')
    bar_closed(page)
    expect(page.locator('#mMark')).to_be_visible()
    assert ev(page, 'FK.tac.shapes()') == []
    idx_ok(page)
    start(page, 'measure')
    p1, p2 = HOME, dest(page, *HOME, 45, 800)
    add(page, *p1)
    add(page, *p2)
    page.click('#tbSaveRoute')
    expect(page.locator('#dlgAsk')).to_be_visible()
    expect(page.locator('#askTitle')).to_have_text('Name this route')
    expect(page.locator('#askInput')).to_have_value('Route 1')
    page.click('#askOk')
    bar_closed(page)
    s = ev(page, 'FK.tac.shapes()')
    assert len(s) == 1 and s[0]['type'] == 'route' and s[0]['name'] == 'Route 1'
    assert dist(page, s[0]['pts'][0], p1) < 0.5 and dist(page, s[0]['pts'][1], p2) < 0.5
    idx_ok(page)


def test_measure_back_just_leaves(page, app_url):
    boot(page, app_url)
    start(page, 'measure')
    add(page, *HOME)
    add(page, *dest(page, *HOME, 45, 800))
    page.go_back()
    bar_closed(page)
    expect(page.locator('#dlgConfirm')).to_be_hidden()
    assert ev(page, 'FK.tac.shapes()') == []
    idx_ok(page)


# ---------- Route ----------

def test_route_done_names_and_stores_it(page, app_url):
    boot(page, app_url)
    start(page, 'route')
    expect(page.locator('#tbSaveRoute')).to_be_hidden()
    pts = [HOME, dest(page, *HOME, 90, 400), dest(page, *HOME, 60, 900)]
    for p in pts:
        add(page, *p)
    expect(page.locator('path.tool-done')).to_have_count(1)
    expect(page.locator('path.tool-band')).to_have_count(1)
    page.click('#tbDone')
    expect(page.locator('#askTitle')).to_have_text('Name this route')
    expect(page.locator('#askInput')).to_have_value('Route 1')
    page.fill('#askInput', 'To the ridge')
    page.click('#askOk')
    bar_closed(page)
    s = ev(page, 'FK.tac.shapes()')
    assert len(s) == 1 and s[0]['name'] == 'To the ridge' and len(s[0]['pts']) == 3
    expect(toast(page)).to_have_text('Saved To the ridge')
    expect(page.locator('path.tool-band')).to_have_count(0)
    expect(page.locator(f'path.shp-route[data-id="{s[0]["id"]}"]')).to_have_count(1)
    idx_ok(page)


def test_route_name_cancel_returns_to_the_mode_with_every_point(page, app_url):
    boot(page, app_url)
    start(page, 'route')
    add(page, *HOME)
    add(page, *dest(page, *HOME, 90, 400))
    page.click('#tbDone')
    expect(page.locator('#dlgAsk')).to_be_visible()
    page.click('#askCancel')
    expect(page.locator('#dlgAsk')).to_be_hidden()
    page.wait_for_function("history.state.fkLayer && !history.state.fkSheet")
    assert ev(page, 'FK.mapTools.mode()') == 'route' and ev(page, 'FK.mapTools.points().length') == 2
    assert ev(page, 'FK.tac.shapes()') == []
    idx_ok(page)


def test_route_needs_two_points(page, app_url):
    boot(page, app_url)
    start(page, 'route')
    add(page, *HOME)
    page.click('#tbDone')
    expect(toast(page)).to_have_text('A route needs at least two points')
    expect(page.locator('#dlgAsk')).to_be_hidden()
    assert ev(page, 'FK.mapTools.mode()') == 'route'


def test_route_refuses_the_201st_point(page, app_url):
    boot(page, app_url)
    start(page, 'route')
    ev(page, """() => { const m = FK.leafletMap();
      for (let i = 0; i < 200; i++) { m.setView([43.0 + i * 0.0005, -76.0], 15, { animate: false }); document.querySelector('#tbAdd').click(); } }""")
    assert ev(page, 'FK.mapTools.points().length') == 200
    add(page, 43.0, -76.0)
    expect(toast(page)).to_have_text("That's the most points one route can hold (200)")
    assert ev(page, 'FK.mapTools.points().length') == 200


def test_route_shape_limit(page, app_url):
    many = [shape(f's{i}', 'route', [[43.0, -76.0], [42.91, -76.0]], name=f'R{i}') for i in range(99)]
    boot(page, app_url, shapes=many)
    start(page, 'route')
    ev(page, "FK.tac.addShape({ type: 'route', pts: [[43, -76], [42.92, -76]] })")   # the 100th arrives while the route is drawn
    add(page, *HOME)
    add(page, *dest(page, *HOME, 90, 400))
    page.click('#tbDone')
    page.click('#askOk')
    expect(toast(page)).to_have_text('You have 100 shapes, the most the app can hold. Delete one first.')
    page.wait_for_function("history.state.fkLayer && !history.state.fkSheet")
    assert ev(page, 'FK.mapTools.mode()') == 'route' and ev(page, 'FK.tac.shapes().length') == 100


def test_route_saved_when_storage_is_full_stays_on_screen(page, app_url):
    boot(page, app_url, full='shapes')
    start(page, 'route')
    add(page, *HOME)
    add(page, *dest(page, *HOME, 90, 400))
    page.click('#tbDone')
    page.click('#askOk')
    bar_closed(page)
    expect(toast(page)).to_have_text(FULL)
    assert len(ev(page, 'FK.tac.shapes()')) == 1
    expect(page.locator('path.shp-route')).to_have_count(1)


def test_crosshair_on_the_last_point_is_not_added_twice(page, app_url):
    boot(page, app_url)
    start(page, 'route')
    add(page, *HOME)
    page.click('#tbAdd')
    assert ev(page, 'FK.mapTools.points().length') == 1


# ---------- Back, Cancel, navigation, restore ----------

def test_back_with_unsaved_points_asks_before_discarding(page, app_url):
    boot(page, app_url)
    start(page, 'route')
    add(page, *HOME)
    add(page, *dest(page, *HOME, 90, 400))
    page.go_back()
    expect(page.locator('#dlgConfirm')).to_be_visible()
    expect(page.locator('#cfTitle')).to_have_text('Discard this route?')
    page.click('#cfCancel')
    expect(page.locator('#dlgConfirm')).to_be_hidden()
    page.wait_for_function("history.state.fkLayer && !history.state.fkSheet")
    assert ev(page, 'FK.mapTools.mode()') == 'route' and ev(page, 'FK.mapTools.points().length') == 2
    expect(page.locator('#toolBar')).to_be_visible()
    idx_ok(page)
    page.go_back()
    expect(page.locator('#dlgConfirm')).to_be_visible()
    page.click('#cfOk')
    bar_closed(page)
    assert ev(page, 'FK.tac.shapes()') == []
    idx_ok(page)
    assert ev(page, 'location.hash') == '#/tactical/map'
    page.go_back()
    assert page.url == 'about:blank'


@pytest.mark.parametrize('n', [0, 1])
def test_back_with_one_point_or_none_just_leaves(page, app_url, n):
    boot(page, app_url)
    start(page, 'area')
    for i in range(n):
        add(page, *dest(page, *HOME, 90, 100 * i))
    page.go_back()
    bar_closed(page)
    expect(page.locator('#dlgConfirm')).to_be_hidden()
    idx_ok(page)
    page.go_back()
    assert page.url == 'about:blank'


def test_cancel_with_points_asks_and_with_none_leaves(page, app_url):
    boot(page, app_url)
    start(page, 'area')
    page.click('#tbCancel')
    bar_closed(page)
    start(page, 'area')
    add(page, *HOME)
    add(page, *dest(page, *HOME, 90, 400))
    page.click('#tbCancel')
    expect(page.locator('#cfTitle')).to_have_text('Discard this area?')
    page.click('#cfOk')
    bar_closed(page)
    idx_ok(page)
    page.go_back()
    assert page.url == 'about:blank'


def test_navigating_away_leaves_the_mode_and_keeps_nothing(page, app_url):
    boot(page, app_url)
    start(page, 'route')
    add(page, *HOME)
    add(page, *dest(page, *HOME, 90, 400))
    expect(page.locator('#tacSeg')).to_be_hidden()   # the Map / Position / Ballistics switch makes room while a mode is on
    page.click('.tabbar [data-tab="survival"]')
    page.wait_for_function("location.hash.startsWith('#/survival')")
    assert ev(page, 'FK.mapTools.mode()') is None and ev(page, 'FK.tac.shapes()') == []
    idx_ok(page)
    page.go_back()
    page.wait_for_function("location.hash === '#/tactical/map' && !history.state.fkLayer")
    expect(page.locator('#toolBar')).to_be_hidden()
    expect(page.locator('#mMark')).to_be_visible()
    idx_ok(page)


def test_a_restore_while_a_mode_is_on_leaves_it_with_nothing_stored(page, app_url):
    boot(page, app_url)
    start(page, 'route')
    add(page, *HOME)
    add(page, *dest(page, *HOME, 90, 400))
    ev(page, "FK.emit('restoring')")
    bar_closed(page)
    assert ev(page, 'FK.tac.shapes()') == []
    idx_ok(page)


def test_while_a_mode_is_on_taps_on_markers_and_shapes_and_long_press_do_nothing(page, app_url):
    a, b = HOME, (HOME[0], HOME[1] + 0.01)
    boot(page, app_url, markers=[mk('w1', 'Camp', 43.002, -76.0)],
         shapes=[shape('s1', 'route', [list(a), list(b)], name='Walk')])
    start(page, 'measure')
    page.locator('.mk-pin[data-id="w1"]').click()
    tap_at(page, 43.0, -75.995)
    page.locator('#map').click(button='right', position={'x': 60, 'y': 200})
    page.wait_for_timeout(200)
    expect(page.locator('#dlgMarker')).to_be_hidden()
    expect(page.locator('#dlgShape')).to_be_hidden()
    assert ev(page, 'FK.mapTools.mode()') == 'measure'


def test_the_map_stays_large_with_the_mode_bar_showing(page, app_url):
    boot(page, app_url)
    start(page, 'route')
    add(page, *HOME)
    add(page, *dest(page, *HOME, 90, 400))
    g = ev(page, """() => { const r = s => document.querySelector(s).getBoundingClientRect();
      const w = r('#mapWrap'), t = r('#toolBar'), m = r('.mapbar'), c = r('.cross');
      return { visible: t.top - w.top, crossBottom: c.bottom, barTop: t.top, barBottom: t.bottom, gridTop: m.top, width: t.width }; }""")
    assert g['visible'] >= 300, g
    assert g['crossBottom'] <= g['barTop'], g
    assert g['barBottom'] <= g['gridTop'] + 0.5, g
    for sel in ('#tbAdd', '#tbUndo', '#tbDone', '#tbCancel'):
        bb = page.locator(sel).bounding_box()
        assert bb['height'] >= 44 and bb['width'] >= 44, (sel, bb)
    assert page.locator('#tbAdd').bounding_box()['width'] > page.locator('#tbUndo').bounding_box()['width']
    expect(page.locator('#mCenter')).to_be_visible()


# ---------- Area ----------

def test_area_needs_three_points_then_stores_and_its_sheet_shows_perimeter_and_area(page, app_url):
    boot(page, app_url)
    start(page, 'area')
    a, b = HOME, dest(page, *HOME, 90, 100)
    c = dest(page, *b, 0, 100)
    add(page, *a)
    add(page, *b)
    page.click('#tbDone')
    expect(toast(page)).to_have_text('An area needs at least three points')
    add(page, *c)
    expect(read(page)).to_contain_text('Area ')
    expect(page.locator('path.tool-close')).to_have_count(1)
    page.click('#tbDone')
    expect(page.locator('#askTitle')).to_have_text('Name this area')
    expect(page.locator('#askInput')).to_have_value('Area 1')
    page.click('#askOk')
    bar_closed(page)
    s = ev(page, 'FK.tac.shapes()')
    assert len(s) == 1 and s[0]['type'] == 'area' and len(s[0]['pts']) == 3
    sid = s[0]['id']
    tap_at(page, *dest(page, *a, 90, 50))   # on its first edge
    expect(page.locator('#dlgShape')).to_be_visible()
    expect(page.locator('#shName')).to_have_text('Area 1')
    info = page.locator('#shInfo')
    expect(info).to_contain_text('Perimeter 341 m')
    expect(info).to_contain_text('Area 5000 m²')
    close_shape(page)
    ev(page, "FK.tac.setUnit('us')")
    tap_at(page, *dest(page, *a, 90, 50))   # on its first edge
    expect(info).to_contain_text('Perimeter 373 yd')
    expect(info).to_contain_text('Area 1.2 acres')


# ---------- Range ring ----------

def ring_sheet(page):
    tool(page, 'ring')
    expect(page.locator('#dlgRing')).to_be_visible()


def test_range_ring_three_radii_at_the_crosshair(page, app_url):
    boot(page, app_url)
    center(page, 43.08, -76.3)
    ring_sheet(page)
    assert page.locator('#dlgRing input[type="number"]').count() == 3
    assert page.locator('#rgR4').count() == 0
    expect(page.locator('#dlgRing label[for="rgR1"]')).to_contain_text('(m)')
    page.fill('#rgR1', '300')
    page.fill('#rgR2', '100')
    page.fill('#rgR3', '500')
    page.click('#rgSave')
    expect(page.locator('#dlgRing')).to_be_hidden()
    page.wait_for_function('FK.tac.shapes().length === 1')
    s = ev(page, 'FK.tac.shapes()[0]')
    assert s['type'] == 'ring' and s['r'] == [100, 300, 500] and s['name'] == 'Ring 1'
    assert dist(page, s['pts'][0], (43.08, -76.3)) < 0.5
    expect(page.locator(f'path.shp-ring[data-id="{s["id"]}"]')).to_have_count(3)
    expect(page.locator(f'.shp-rlab[data-id="{s["id"]}"]')).to_have_count(3)
    expect(page.locator('.shp-rlab').first).to_have_text('100 m')
    expect(toast(page)).to_have_text('Added Ring 1')
    idx_ok(page)


def test_range_ring_refusals(page, app_url):
    boot(page, app_url)
    ring_sheet(page)
    page.click('#rgSave')
    expect(page.locator('#rgMsg')).to_have_text('Enter at least one radius')
    page.fill('#rgR1', '60000')
    page.click('#rgSave')
    expect(page.locator('#rgMsg')).to_have_text('Rings can be up to 50 km')
    page.fill('#rgR1', '0')
    page.click('#rgSave')
    expect(page.locator('#rgMsg')).to_have_text('A radius must be more than zero')
    page.fill('#rgR1', '-5')
    page.click('#rgSave')
    expect(page.locator('#rgMsg')).to_have_text('A radius must be more than zero')
    assert ev(page, 'FK.tac.shapes()') == []
    expect(page.locator('#dlgRing')).to_be_visible()
    page.fill('#rgR1', '50000')
    page.click('#rgSave')
    page.wait_for_function('FK.tac.shapes().length === 1')


def test_range_ring_in_us_units_takes_yards_and_stores_metres(page, app_url):
    boot(page, app_url, distUnit='us')
    ring_sheet(page)
    expect(page.locator('#dlgRing label[for="rgR1"]')).to_contain_text('(yd)')
    page.fill('#rgR1', '100')
    page.fill('#rgR3', '1000')
    page.click('#rgSave')
    page.wait_for_function('FK.tac.shapes().length === 1')
    r = ev(page, 'FK.tac.shapes()[0].r')
    assert len(r) == 2 and abs(r[0] - 91.44) < 1e-6 and abs(r[1] - 914.4) < 1e-6
    expect(page.locator('.shp-rlab').first).to_have_text('100 yd')


def test_range_ring_centred_on_a_marker_nearest_first(page, app_url):
    far, near = mk('w1', 'Far', 43.2, -76.0), mk('w2', 'Near', 43.01, -76.0)
    boot(page, app_url, markers=[far, near])
    set_fix(page, *HOME)
    ring_sheet(page)
    opts = page.locator('#rgCentre option').all_inner_texts()
    assert opts[0] == 'The crosshair' and opts[1].startswith('Near') and opts[2].startswith('Far')
    page.select_option('#rgCentre', 'w1')
    page.fill('#rgR1', '200')
    page.click('#rgSave')
    page.wait_for_function('FK.tac.shapes().length === 1')
    assert ev(page, 'FK.tac.shapes()[0].pts[0]') == [43.2, -76.0]


# ---------- Go to grid ----------

def goto(page, text):
    tool(page, 'goto')
    expect(page.locator('#dlgGoto')).to_be_visible()
    page.fill('#gtInput', text)
    page.click('#gtGo')


@pytest.mark.parametrize('kind', ['mgrs', 'dd', 'dms'])
def test_go_to_grid_centres_the_map_and_turns_follow_off(page, app_url, kind):
    boot(page, app_url, mapFollow=True)
    want = (42.95, -75.95)
    text = {'mgrs': ev(page, 'GEO.toMGRS(42.95, -75.95).text'), 'dd': '42.95, -75.95', 'dms': '42°57′00″N 75°57′00″W'}[kind]
    goto(page, text)
    expect(page.locator('#dlgGoto')).to_be_hidden()
    page.wait_for_function('FK.leafletMap().getZoom() >= 15')
    assert dist(page, map_center(page), want) < 2
    expect(page.locator('#mLocate')).to_have_attribute('aria-pressed', 'false')
    expect(page.locator('#mCenter')).to_have_text(ev(page, 'GEO.toMGRS(42.95, -75.95).text'))   # the map's own bar: one panel
    idx_ok(page)


def test_go_to_grid_mark_opens_the_marker_sheet_there(page, app_url):
    boot(page, app_url)
    goto(page, '42.95, -75.95')
    expect(page.locator('#dlgGoto')).to_be_hidden()
    page.wait_for_timeout(400)
    page.click('#mMark')
    expect(page.locator('#dlgMarker')).to_be_visible()
    expect(page.locator('#mkGrid')).to_have_text(ev(page, 'GEO.toMGRS(42.95, -75.95).text'))


def test_go_to_grid_adds_no_second_panel(page, app_url):
    boot(page, app_url)
    goto(page, '42.95, -75.95')
    expect(page.locator('#dlgGoto')).to_be_hidden()
    assert ev(page, "[...document.querySelectorAll('#mapWrap button')].filter(b => b.offsetParent && /Mark/.test(b.textContent)).length") == 1


def test_go_to_grid_nonsense_shows_the_help_and_does_not_move(page, app_url):
    boot(page, app_url)
    before = map_center(page)
    goto(page, 'not a place')
    expect(page.locator('#gtMsg')).to_have_text(HELP)
    expect(page.locator('#dlgGoto')).to_be_visible()
    assert dist(page, map_center(page), before) < 0.5
    page.go_back()
    expect(page.locator('#dlgGoto')).to_be_hidden()
    idx_ok(page)


def test_go_to_grid_help_text_is_the_position_add_rows(page, app_url):
    boot(page, app_url)
    assert ev(page, 'FK.GRID_HELP') == HELP


# ---------- Drawn shapes and the shape sheet ----------

ROUTE = shape('s1', 'route', [[43.0, -76.0], [43.0, -75.99], [43.005, -75.99]], name='Ridge walk')


def test_shapes_are_drawn_with_names(page, app_url):
    area = shape('s2', 'area', [[42.99, -76.01], [42.99, -76.005], [42.995, -76.005]], name='Field')
    ring = shape('s3', 'ring', [[43.0, -76.01]], name='Watch', r=[100, 200])
    boot(page, app_url, shapes=[ROUTE, area, ring])
    expect(page.locator('path.shp-route[data-id="s1"]')).to_have_count(1)
    expect(page.locator('path.shp-area[data-id="s2"]')).to_have_count(1)
    expect(page.locator('path.shp-ring[data-id="s3"]')).to_have_count(2)
    for sid, name in (('s1', 'Ridge walk'), ('s2', 'Field'), ('s3', 'Watch')):
        expect(page.locator(f'.shp-lab.shp-text[data-id="{sid}"]')).to_have_text(name)
    # redrawn after a reload
    page.reload()
    page.wait_for_function('window.FK && FK.sheet && document.querySelector("#map .leaflet-pane")')
    expect(page.locator('path.shp-ring[data-id="s3"]')).to_have_count(2)
    # and on a unit change
    ev(page, "FK.tac.setUnit('us')")
    expect(page.locator('.shp-rlab[data-id="s3"]').first).to_have_text('109 yd')


def test_shapes_redraw_after_a_restore(page, app_url, tmp_path):
    boot(page, app_url)
    backup = {'app': 'Field Kit', 'version': '7.7', 'saved': '2026-11-10T14:30:00.000Z',
              'data': {'fk.shapes': json.dumps([ROUTE])}}
    path = tmp_path / 'b.json'
    path.write_text(json.dumps(backup))
    page.click('#menuBtn')
    page.wait_for_selector('#dlgMenu[open]')
    page.set_input_files('#bkFile', str(path))
    page.wait_for_selector('#bkConfirm:not([hidden])')
    page.click('#bkGo')
    page.wait_for_timeout(ev(page, 'FK.tools.confirm.ignoreMs') + 100)
    with page.expect_navigation():
        page.click('#bkGo')
    page.wait_for_function('window.FK && FK.tac')
    if ev(page, 'location.hash') != '#/tactical/map':
        ev(page, "FK.route.go('/tactical/map')")
    expect(page.locator('path.shp-route[data-id="s1"]')).to_have_count(1)


def test_shape_names_are_text_not_markup(page, app_url):
    boot(page, app_url, shapes=[dict(ROUTE, name=EVIL)])
    expect(page.locator('.shp-lab.shp-text[data-id="s1"]')).to_have_text(EVIL)
    tap_route(page)
    expect(page.locator('#shName')).to_have_text(EVIL)
    assert ev(page, 'window.x') is None


def test_shape_sheet_for_a_route_rename_delete_walk(page, app_url):
    boot(page, app_url, shapes=[ROUTE])
    tap_route(page)
    expect(page.locator('#dlgShape')).to_be_visible()
    expect(page.locator('#shName')).to_have_text('Ridge walk')
    expect(page.locator('#shType')).to_have_text('Route, 3 points')
    legs = page.locator('#shLegs li')
    expect(legs).to_have_count(2)
    expect(legs.first).to_contain_text('1 → 2')
    expect(legs.first).to_contain_text('° true')
    expect(page.locator('#shInfo')).to_contain_text('Length 1.37 km')
    page.click('#shRename')
    expect(page.locator('#askInput')).to_have_value('Ridge walk')
    page.fill('#askInput', 'Creek walk')
    page.click('#askOk')
    expect(page.locator('#shName')).to_have_text('Creek walk')
    assert ev(page, 'FK.tac.shapes()[0].name') == 'Creek walk'
    page.click('#shWalk')
    expect(page.locator('#dlgShape')).to_be_hidden()
    assert ev(page, 'FK.tac.target()') == {'type': 'route', 'id': 's1', 'i': 0}
    expect(toast(page)).to_have_text('Walking Creek walk. Open Position for the arrow.')
    expect(page.locator('path.shp-route.tgt[data-id="s1"]')).to_have_count(1)
    tap_route(page)
    expect(page.locator('#shWalk')).to_have_text('Stop walking')
    page.click('#shWalk')
    expect(page.locator('#dlgShape')).to_be_hidden()
    assert ev(page, 'FK.tac.target()') is None
    tap_route(page)
    page.click('#shDelete')
    expect(page.locator('#cfText')).to_have_text('Delete route Creek walk? This can’t be undone.')
    expect(page.locator('#cfOk')).to_have_text('Delete route')
    page.click('#cfCancel')
    assert len(ev(page, 'FK.tac.shapes()')) == 1
    page.click('#shDelete')
    page.click('#cfOk')
    expect(page.locator('#dlgShape')).to_be_hidden()
    assert ev(page, 'FK.tac.shapes()') == []
    expect(page.locator('path.shp-route')).to_have_count(0)
    idx_ok(page)


def test_ring_sheet_shows_radii_and_delete_label(page, app_url):
    boot(page, app_url, shapes=[shape('s3', 'ring', [[43.0, -76.0]], name='Watch', r=[100, 300, 500])])
    ev(page, "FK.mapTools.editShape('s3')")
    expect(page.locator('#shInfo')).to_contain_text('100 m, 300 m, 500 m')
    expect(page.locator('#shWalk')).to_be_hidden()
    page.click('#shDelete')
    expect(page.locator('#cfOk')).to_have_text('Delete ring')


def test_a_marker_on_a_shape_wins_the_tap(page, app_url):
    boot(page, app_url, markers=[mk('w1', 'Camp', 43.0, -75.995)], shapes=[ROUTE])
    page.locator('.mk-pin[data-id="w1"]').click()
    expect(page.locator('#dlgMarker')).to_be_visible()
    expect(page.locator('#dlgShape')).to_be_hidden()


def test_a_tap_near_a_line_selects_it(page, app_url):
    boot(page, app_url, shapes=[ROUTE], view=(43.0, -75.995))
    page.wait_for_selector('path.shp-hit[data-id="s1"]', state='attached')
    tap_at(page, 43.0, -75.995, dy=10)   # 10 px off the line
    expect(page.locator('#dlgShape')).to_be_visible()


def test_a_tap_inside_an_area_selects_nothing_and_mark_still_works(page, app_url):
    area = shape('s2', 'area', [[42.995, -76.005], [42.995, -75.995], [43.005, -75.995], [43.005, -76.005]], name='Field')
    boot(page, app_url, shapes=[area])
    page.wait_for_selector('path.shp-hit[data-id="s2"]', state='attached')
    tap_at(page, 43.0, -75.998, dy=30)
    page.wait_for_timeout(300)
    expect(page.locator('#dlgShape')).to_be_hidden()
    page.click('#mMark')
    expect(page.locator('#dlgMarker')).to_be_visible()


def test_a_route_across_the_date_line_is_drawn_the_short_way(page, app_url):
    boot(page, app_url, shapes=[shape('s1', 'route', [[43.0, 179.0], [43.0, -179.0]], name='Dateline')], view=(43.0, 179.5))
    page.wait_for_selector('path.shp-route[data-id="s1"]', state='attached')
    w = ev(page, """() => { let b = null; FK.leafletMap().eachLayer(l => { if (l.getBounds && l.options.className && l.options.className.includes('shp-route')) b = l.getBounds(); });
      return b.getEast() - b.getWest(); }""")
    assert w < 10


# ---------- Move a marker ----------

def test_move_a_marker(page, app_url):
    boot(page, app_url, markers=[mk('w1', 'Camp')])
    page.locator('.mk-pin[data-id="w1"]').click()
    page.fill('#mkName', 'Camp moved')
    page.click('#mkMove')
    expect(page.locator('#dlgMarker')).to_be_hidden()
    expect(page.locator('#toolBar')).to_be_visible()
    expect(read(page)).to_have_text('Move the map until the crosshair is on the new spot')
    expect(page.locator('#tbPlace')).to_be_visible()
    expect(page.locator('#tbAdd')).to_be_hidden()
    page.wait_for_function("FK.mapTools.mode() === 'move' && history.state.fkLayer")
    assert ev(page, 'FK.tac.markers()[0].name') == 'Camp moved'
    center(page, 43.08, -76.3)
    page.click('#tbPlace')
    bar_closed(page)
    w = ev(page, 'FK.tac.markers()[0]')
    assert dist(page, (w['lat'], w['lon']), (43.08, -76.3)) < 0.5 and w['alt'] is None
    expect(page.locator('#dlgMarker')).to_be_hidden()
    idx_ok(page)


def test_move_cancel_leaves_the_marker(page, app_url):
    boot(page, app_url, markers=[mk('w1', 'Camp')])
    ev(page, "FK.mapTools.moveMarker('w1')")
    expect(page.locator('#toolBar')).to_be_visible()
    center(page, 43.08, -76.3)
    page.click('#tbCancel')
    bar_closed(page)
    w = ev(page, 'FK.tac.markers()[0]')
    assert (w['lat'], w['lon'], w['alt']) == (HOME[0], HOME[1], 120)
    idx_ok(page)


def test_new_marker_has_no_move(page, app_url):
    boot(page, app_url)
    page.click('#mMark')
    expect(page.locator('#dlgMarker')).to_be_visible()
    expect(page.locator('#mkMove')).to_be_hidden()


# ---------- No fix ----------

def test_tools_work_with_no_fix(page, app_url):
    boot(page, app_url)
    assert ev(page, 'FK.getFix()') is None
    start(page, 'measure')
    add(page, *HOME)
    center(page, *dest(page, *HOME, 90, 1000))
    expect(read(page)).to_have_text('1.00 km at 90° true')
    page.click('#tbDone')
    bar_closed(page)
    start(page, 'route')
    add(page, *HOME)
    add(page, *dest(page, *HOME, 90, 1000))
    page.click('#tbDone')
    page.click('#askOk')
    bar_closed(page)
    ring_sheet(page)
    page.fill('#rgR1', '100')
    page.click('#rgSave')
    goto(page, '42.95, -75.95')
    page.wait_for_function('FK.tac.shapes().length === 2')
    page.wait_for_timeout(400)
    page.click('#mList')
    expect(page.locator('#lsList li')).to_have_count(2)


# ---------- The list ----------

def test_list_shows_shapes_with_markers(page, app_url):
    area = shape('s2', 'area', [[43.2, -76.01], [43.2, -76.005], [43.205, -76.005]], name='Field', t=5)
    ring = shape('s3', 'ring', [[43.08, -76.0]], name='Watch', r=[100, 300], t=3)
    boot(page, app_url, markers=[mk('w1', 'Camp', 43.05, -76.0, t=4)], shapes=[ROUTE, area, ring])
    set_fix(page, *HOME)
    page.click('#mList')
    rows = page.locator('#lsList li')
    expect(rows).to_have_count(4)
    names = page.locator('#lsList .mk-name').all_inner_texts()
    assert names == ['Ridge walk', 'Camp', 'Watch', 'Field']   # nearest first: first point, or the centre of a ring
    assert page.locator('#lsChips button').all_inner_texts() == ['All', 'Point', 'Routes', 'Areas', 'Rings']
    expect(rows.nth(0)).to_contain_text('1.37 km')
    expect(rows.nth(2)).to_contain_text('100 m, 300 m')
    expect(rows.nth(3)).to_contain_text('11.3 ha')
    page.click('#lsChips [data-kind="ring"]')
    expect(rows).to_have_count(1)
    expect(rows.first).to_contain_text('Watch')
    page.click('#lsList [data-shape="s3"]')
    expect(page.locator('#dlgList')).to_be_hidden()
    expect(page.locator('#dlgShape')).to_be_visible()
    expect(page.locator('#shName')).to_have_text('Watch')
    assert dist(page, map_center(page), (43.08, -76.0)) < 30
    idx_ok(page)


def test_list_without_a_fix_is_newest_first(page, app_url):
    boot(page, app_url, markers=[mk('w1', 'Camp', t=4)], shapes=[dict(ROUTE, t=9), shape('s3', 'ring', [[43.08, -76.0]], name='Watch', r=[100], t=1)])
    page.click('#mList')
    assert page.locator('#lsList .mk-name').all_inner_texts() == ['Ridge walk', 'Camp', 'Watch']


def test_list_row_while_a_mode_is_on_only_centres_the_map(page, app_url):
    boot(page, app_url, markers=[mk('w1', 'Camp', 43.05, -76.0)])
    start(page, 'route')
    page.click('#mList')
    page.click('#lsList [data-id="w1"]')
    expect(page.locator('#dlgList')).to_be_hidden()
    page.wait_for_function("history.state.fkLayer && !history.state.fkSheet")
    expect(page.locator('#dlgMarker')).to_be_hidden()
    assert dist(page, map_center(page), (43.05, -76.0)) < 1
    assert ev(page, 'FK.mapTools.mode()') == 'route'


# ---------- Saved maps naming ----------

def test_saved_maps_are_called_saved_maps(page, app_url):
    boot(page, app_url)
    tool(page, 'save')
    dlg = page.locator('#dlgSave')
    expect(dlg.locator('h3')).to_have_text('Saved maps')
    text = dlg.inner_text()
    assert 'area' not in text.lower().replace('saved maps', ''), text
    assert 'saved areas' not in ev(page, 'FK.FULL_MSG').lower() and 'saved maps' in ev(page, 'FK.FULL_MSG')


def test_search_finds_saved_maps_by_both_names(page, app_url):
    boot(page, app_url)
    assert ev(page, "FK.search.describe('a:areas').title") == 'Saved maps'
    assert ev(page, "FK.search.query('saved areas')[0].key") == 'a:areas'
    assert ev(page, "FK.search.query('saved maps')[0].key") == 'a:areas'


# ---------- Review fixes ----------

def test_cancel_with_the_tools_sheet_open_leaves_history_clean(page, app_url):
    boot(page, app_url)
    start(page, 'route')
    add(page, *HOME)
    add(page, *dest(page, *HOME, 90, 400))
    open_tools(page)
    ev(page, 'FK.mapTools.cancel()')
    page.wait_for_function('!history.state.fkLayer && !history.state.fkSheet')
    page.wait_for_timeout(600)
    assert ev(page, "[...document.querySelectorAll('dialog')].filter(d => d.open).length") == 0
    assert ev(page, 'FK.mapTools.mode()') is None
    idx_ok(page)
    start(page, 'measure')
    page.go_back()
    bar_closed(page)
    idx_ok(page)
    assert ev(page, 'location.hash') == '#/tactical/map'
    page.go_back()
    assert page.url == 'about:blank'


C0 = (43.0, -76.0)


def test_route_under_a_later_ring_still_takes_its_tap(page, app_url):
    rc = (42.982, -76.0)   # 2 km south of the route's start: the whole route lies inside the 3 km ring
    ring = shape('s9', 'ring', [list(rc)], name='Big', r=[3000], t=2)
    boot(page, app_url, shapes=[ROUTE, ring])
    center(page, *rc, z=12)
    page.wait_for_selector('path.shp-hit[data-id="s9"]', state='attached')
    tap_route(page)
    expect(page.locator('#dlgShape')).to_be_visible()
    expect(page.locator('#shName')).to_have_text('Ridge walk')
    close_shape(page)
    tap_at(page, *dest(page, *rc, 270, 3000))   # on the ring's circle
    expect(page.locator('#dlgShape')).to_be_visible()
    expect(page.locator('#shName')).to_have_text('Big')
    close_shape(page)
    tap_at(page, *dest(page, *rc, 250, 1500))   # empty map inside the ring
    page.wait_for_timeout(300)
    expect(page.locator('#dlgShape')).to_be_hidden()
    page.click('#mMark')
    expect(page.locator('#dlgMarker')).to_be_visible()


def test_route_under_a_later_area_still_takes_its_tap(page, app_url):
    area = shape('s8', 'area', [[42.998, -76.003], [42.998, -75.987], [43.003, -75.987], [43.003, -76.003]], name='Block', t=2)
    boot(page, app_url, shapes=[ROUTE, area], view=(43.0, -75.995))
    page.wait_for_selector('path.shp-hit[data-id="s8"]', state='attached')
    tap_route(page)
    expect(page.locator('#dlgShape')).to_be_visible()
    expect(page.locator('#shName')).to_have_text('Ridge walk')
    close_shape(page)
    tap_at(page, 43.003, -75.996)   # the area's north edge
    expect(page.locator('#dlgShape')).to_be_visible()
    expect(page.locator('#shName')).to_have_text('Block')
    close_shape(page)
    tap_at(page, 43.0015, -75.997)   # inside the area, off every line
    page.wait_for_timeout(300)
    expect(page.locator('#dlgShape')).to_be_hidden()


def test_a_name_label_opens_its_shape_and_is_a_comfortable_target(page, app_url):
    ring = shape('s3', 'ring', [[43.001, -76.0]], name='Watch', r=[100, 200])
    boot(page, app_url, shapes=[ring])
    lab = page.locator('.shp-lab:not(.shp-text)[data-id="s3"]')
    assert lab.bounding_box()['height'] >= 44
    lab.click()
    expect(page.locator('#shName')).to_have_text('Watch')


RETIRED = {'id': 'a1', 'name': 'Home', 'layer': 'imagery', 's': 43.0, 'w': -76.3, 'n': 43.08, 'e': -76.0,
           'zMin': 5, 'zMax': 14, 'tiles': 10, 'bytes': 1000}
TAC_TEXT = """() => {
  const ids = ['view-map', 'dlgTools', 'dlgShape', 'dlgRing', 'dlgGoto', 'dlgMarker', 'dlgList', 'dlgLayers', 'dlgSave', 'dlgTrack', 'dlgAsk', 'dlgConfirm'];
  return ids.map(id => { const c = document.getElementById(id).cloneNode(true);
    c.querySelectorAll('[data-tool="area"], [data-kind="area"]').forEach(e => e.remove());   // the drawn-shape tool and chip
    return id + ': ' + c.textContent.replace(/\\s+/g, ' '); }).join('\\n'); }"""


def fill_tactical_text(page):
    """Open the Tactical dialogs that fill their text when opened, so their whole wording is in the page."""
    for opener, closer in (("FK.map.openSave()", '#saveClose'), ("FK.map.openTrack()", '#trkClose'), ("FK.mapTools.open()", '#tlClose'),
                           ("FK.shapes.openRing()", '#rgCancel'), ("document.querySelector('#mLayers').click()", '#layersClose')):
        ev(page, opener)
        page.wait_for_timeout(150)
        page.click(closer)
        page.wait_for_timeout(150)


def no_saved_map_called_area(text):
    import re
    hits = [text[max(0, m.start() - 40):m.end() + 40] for m in re.finditer(r'area', text, re.I)]
    assert hits == [], hits


def test_no_saved_map_is_called_an_area_anywhere_on_tactical(page, app_url):
    boot(page, app_url, mapLayer='imagery', areas=[RETIRED], recording=True)
    page.route('https://basemap.nationalmap.gov/**', lambda r: r.abort())
    page.reload()
    page.wait_for_function('window.FK && FK.sheet && document.querySelector("#map .leaflet-pane")')
    expect(page.locator('#mapNote')).to_contain_text('maps you saved')   # the retired layer's notice
    fill_tactical_text(page)
    no_saved_map_called_area(ev(page, TAC_TEXT))
    # offline, outside every saved map
    page.context.set_offline(True)
    page.click('#mLayers')
    page.check('#layerList input[value="topo"]')
    expect(page.locator('#mapNote')).to_contain_text('outside your saved maps')
    no_saved_map_called_area(ev(page, TAC_TEXT))
    page.context.set_offline(False)


def test_backup_message_calls_saved_maps_saved_maps(page, app_url, tmp_path):
    boot(page, app_url)
    page.click('#menuBtn')
    page.wait_for_selector('#dlgMenu[open]')
    with page.expect_download():
        page.click('#bkSave')
    expect(page.locator('#bkMsg')).to_contain_text('download those saved maps again on a new phone.')
    assert 'area' not in page.inner_text('#bkMsg').lower()


LIMIT = 'You have 100 shapes, the most the app can hold. Delete one first.'


@pytest.mark.parametrize('tool_id', ['route', 'area', 'ring'])
def test_at_100_shapes_route_area_and_ring_do_not_start(page, app_url, tool_id):
    many = [shape(f's{i}', 'route', [[43.0, -76.0], [42.91, -76.0]], name=f'R{i}') for i in range(100)]
    boot(page, app_url, shapes=many)
    tool(page, tool_id)
    expect(toast(page)).to_have_text(LIMIT)
    page.wait_for_timeout(300)
    assert ev(page, 'FK.mapTools.mode()') is None
    expect(page.locator('#toolBar')).to_be_hidden()
    expect(page.locator('#dlgRing')).to_be_hidden()
    idx_ok(page)


def test_focus_moves_to_the_primary_button_and_back_to_tools(page, app_url):
    boot(page, app_url, markers=[mk('w1', 'Camp')])
    start(page, 'route')
    page.wait_for_function("document.activeElement && document.activeElement.id === 'tbAdd'")
    page.click('#tbCancel')
    bar_closed(page)
    page.wait_for_function("document.activeElement && document.activeElement.id === 'mTools'")
    ev(page, "FK.mapTools.moveMarker('w1')")
    page.wait_for_function("document.activeElement && document.activeElement.id === 'tbPlace'")


def test_screen_reader_reading_waits_for_the_map_to_stop(page, app_url):
    boot(page, app_url)
    start(page, 'measure')
    assert page.get_attribute('#tbLive', 'aria-live') == 'polite' and page.get_attribute('#tbRead', 'aria-live') is None
    add(page, *HOME)
    expect(page.locator('#tbLive')).to_have_text(page.inner_text('#tbRead'))
    ev(page, "() => { const m = FK.leafletMap(); m.fire('movestart'); m._rawPanBy([80, 0]); m.fire('move'); }")
    live_before = page.inner_text('#tbLive')
    assert page.inner_text('#tbRead') != live_before
    ev(page, "FK.leafletMap().fire('moveend')")
    expect(page.locator('#tbLive')).to_have_text(page.inner_text('#tbRead'))


def test_a_long_name_wraps_in_the_shape_sheet(page, app_url):
    boot(page, app_url, shapes=[dict(ROUTE, name='W' * 60)])
    tap_route(page)
    expect(page.locator('#dlgShape')).to_be_visible()
    assert ev(page, "(() => { const d = document.querySelector('#dlgShape'); const b = d.querySelector('.mk-body'); return b.scrollWidth <= b.clientWidth + 1 && d.scrollWidth <= d.clientWidth + 1; })()")


def test_recording_chip_label_carries_the_distance(page, app_url):
    boot(page, app_url, recording=True, track=[[43.0, -76.0, None, NOW], [43.01, -76.0, None, NOW + 60000]])
    expect(page.locator('#recChip')).to_have_attribute('aria-label', 'Recording, 1.11 km. Open Track recording.')


def test_forward_onto_a_dead_mode_entry_bounces_back_to_the_map(page, app_url):
    boot(page, app_url)
    start(page, 'measure')
    page.go_back()
    bar_closed(page)
    page.go_forward()
    page.wait_for_timeout(400)
    page.wait_for_function('!history.state.fkLayer')
    assert ev(page, 'FK.mapTools.mode()') is None and ev(page, 'location.hash') == '#/tactical/map'
    idx_ok(page)
    page.go_back()
    assert page.url == 'about:blank'


def test_opening_search_during_a_mode_ends_it_and_closing_search_resumes_it_on_the_map(page, app_url):
    boot(page, app_url)
    start(page, 'route')
    add(page, *HOME)
    add(page, *dest(page, *HOME, 90, 400))
    page.click('#searchBtn')
    expect(page.locator('#searchPane')).to_be_visible()
    assert ev(page, 'FK.mapTools.mode()') is None and ev(page, 'FK.tac.shapes()') == []
    page.click('#searchClose')
    expect(page.locator('#searchPane')).to_be_hidden()
    # v7.8 final review: the unfinished route comes back with its points and its own history entry
    page.wait_for_function("location.hash === '#/tactical/map' && history.state.fkLayer && FK.mapTools.points().length === 2")
    idx_ok(page)
    expect(page.locator('#toolBar')).to_be_visible()
    page.click('#tbCancel')
    page.click('#cfOk')
    bar_closed(page)
    idx_ok(page)
    page.go_back()
    assert page.url == 'about:blank'


def test_a_tap_on_a_line_straight_after_close_opens_the_sheet_again(page, app_url):
    boot(page, app_url, shapes=[ROUTE])
    tap_route(page)
    expect(page.locator('#dlgShape')).to_be_visible()
    pt = ev(page, """() => { const p = FK.leafletMap().latLngToContainerPoint([43.0, -75.995]); const r = document.querySelector('#map').getBoundingClientRect();
      return [r.left + p.x, r.top + p.y]; }""")
    close = page.locator('#shClose').bounding_box()
    fails = 0
    for _ in range(20):
        page.mouse.click(close['x'] + close['width'] / 2, close['y'] + close['height'] / 2)
        page.mouse.click(*pt)   # no wait in between
        page.wait_for_timeout(60)
        if not ev(page, "document.querySelector('#dlgShape').open"):
            fails += 1
            tap_route(page)
            expect(page.locator('#dlgShape')).to_be_visible()
    assert fails == 0, f'{fails} of 20'
    assert ev(page, 'history.state.fkSheet') == 'dlgShape'
    idx_ok(page)
