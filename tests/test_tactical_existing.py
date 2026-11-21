"""Existing Tactical behaviour, pinned before the screens are rearranged: GPS on/off rules, compass,
track recording, saved offline maps, the date line, GPX export. These describe what the app does today."""
import json, re

from playwright.sync_api import expect

from .tac import store, open_map, set_fix, heading, center, open_track, open_save
from .test_map import PNG

MAP = '#/tactical/map'
HOME = (43.0, -76.0)
M100 = 0.0009   # degrees of latitude, about 100 m

GPS_STUB = """(() => {
  window.__watch = 0; window.__clear = 0; let id = 0;
  Object.defineProperty(navigator, 'geolocation', { configurable: true, value: {
    watchPosition() { window.__watch++; return ++id; },
    clearWatch() { window.__clear++; },
    getCurrentPosition() {} } });
})()"""


def active_watches(page):
    return page.evaluate('window.__watch - window.__clear')


def watches_become(page, n):
    """Wait for the number of live GPS watches to settle at n (navigation and sheets finish on later turns)."""
    page.wait_for_function('n => window.__watch - window.__clear === n', arg=n)


def go(page, path):
    page.evaluate('p => FK.route.go(p)', path)


def watch_stays(page, n, hash_):
    """The watch count is still n once the screen has changed to hash_ and settled: checked after the move, not before it
    (waiting for n alone passes at once when it was n already)."""
    page.wait_for_function('h => location.hash.startsWith(h)', arg=hash_)
    cleared = page.evaluate('window.__clear')
    page.wait_for_timeout(150)
    assert page.evaluate('window.__watch - window.__clear') == n and page.evaluate('window.__clear') == cleared


def tiles_cors(page):
    page.route('https://basemap.nationalmap.gov/**', lambda r: r.fulfill(
        status=200, content_type='image/png', body=PNG, headers={'access-control-allow-origin': '*'}))


def stored(page, key):
    return page.evaluate('k => JSON.parse(localStorage.getItem("fk." + k))', key)


def start_recording(page):
    open_track(page)
    page.click('#trkToggle')
    expect(page.locator('#trkToggle')).to_have_text('Stop recording')


# ---------- GPS ----------

def test_a_fix_shows_a_grid(page, app_url):
    open_map(page, app_url)
    set_fix(page, *HOME)
    mgrs = page.locator('#mgrs')
    expect(mgrs).not_to_have_text('No fix yet')
    expect(mgrs).to_contain_text('18T')               # 43.0, -76.0 is in grid zone 18T
    expect(page.locator('#latlon')).to_have_text('43.000000, -76.000000')


def test_gps_watch_runs_on_map_and_position_only(page, app_url):
    page.add_init_script(GPS_STUB)
    open_map(page, app_url)
    watches_become(page, 1)
    go(page, '/tactical/position')
    watch_stays(page, 1, '#/tactical/position')
    go(page, '/tactical/ballistics')
    watches_become(page, 0)
    go(page, '/tactical/map')
    watches_become(page, 1)
    go(page, '/survival')
    watches_become(page, 0)
    go(page, '/emergency')
    watches_become(page, 0)
    go(page, '/tactical/position')
    watches_become(page, 1)
    assert page.evaluate('window.__watch') == 3 and page.evaluate('window.__clear') == 2   # never two at once


def test_gps_stays_on_in_other_tabs_while_recording(page, app_url):
    page.add_init_script(GPS_STUB)
    open_map(page, app_url)
    start_recording(page)
    page.click('#trkClose')
    go(page, '/tactical/ballistics')
    watch_stays(page, 1, '#/tactical/ballistics')
    go(page, '/survival')
    watch_stays(page, 1, '#/survival')
    # stopping the recording lets the watch go once the screen is not a GPS screen
    go(page, '/tactical/map')
    open_track(page)
    page.click('#trkToggle')
    page.click('#trkClose')
    go(page, '/survival')
    watches_become(page, 0)


def test_recording_from_a_previous_session_keeps_gps_on_elsewhere(page, app_url):
    page.add_init_script(GPS_STUB)
    store(page, recording=True)
    page.goto(app_url + '#/survival')
    page.wait_for_function('window.FK && FK.sheet')
    watches_become(page, 1)
    watch_stays(page, 1, '#/survival')


# ---------- Compass ----------

def test_compass_shows_heading_and_direction(page, app_url):
    page.goto(app_url + '#/tactical/position')
    page.wait_for_function('window.FK && FK._test')
    heading(page, 90)
    expect(page.locator('#hdg')).to_have_text('90°')
    expect(page.locator('#hdgRef')).to_have_text('E, 1600 mils, magnetic')


def test_declination_turns_magnetic_into_true(page, app_url):
    page.goto(app_url + '#/tactical/position')
    page.wait_for_function('window.FK && FK._test')
    page.click('#declSeg [data-decl="manual"]')   # v7.8: a fresh install works declination out; typing is By hand
    page.fill('#decl', '-12')
    heading(page, 90)
    expect(page.locator('#hdg')).to_have_text('78°')
    expect(page.locator('#hdgRef')).to_contain_text('true')
    assert stored(page, 'decl') == -12


def test_stored_declination_applies_after_reload(page, app_url):
    store(page, decl=-12)
    page.goto(app_url + '#/tactical/position')
    page.wait_for_function('window.FK && FK._test')
    expect(page.locator('#decl')).to_have_value('-12')
    heading(page, 90)
    expect(page.locator('#hdg')).to_have_text('78°')


# ---------- Track ----------

def test_recording_adds_points_and_shows_distance(page, app_url):
    open_map(page, app_url)
    start_recording(page)
    for i in range(3):
        set_fix(page, HOME[0] + i * M100, HOME[1])
    info = page.locator('#trkInfo')
    expect(info).to_contain_text('3 points')
    text = info.inner_text()
    assert text.split(' m ')[0].isdigit() and 195 <= int(text.split(' m ')[0]) <= 205, text
    assert len(stored(page, 'track')) == 3
    assert stored(page, 'recording') is True
    expect(page.locator('#recChip')).to_be_visible()


def test_poor_accuracy_and_tiny_moves_are_ignored(page, app_url):
    open_map(page, app_url)
    start_recording(page)
    set_fix(page, *HOME)
    set_fix(page, HOME[0] + M100, HOME[1], acc=80)           # too inaccurate
    set_fix(page, HOME[0] + 0.00002, HOME[1])                # about 2 m from the last point
    expect(page.locator('#trkInfo')).to_have_text(re.compile(r', 1 points?\.$'))   # the wording (point/points) is not what this pins
    assert len(stored(page, 'track')) == 1
    set_fix(page, HOME[0] + M100, HOME[1], acc=50)           # 50 m is still accepted
    expect(page.locator('#trkInfo')).to_contain_text('2 points')


def test_nothing_is_recorded_unless_recording(page, app_url):
    open_map(page, app_url)
    set_fix(page, *HOME)
    set_fix(page, HOME[0] + M100, HOME[1])
    assert stored(page, 'track') is None
    open_track(page)
    expect(page.locator('#trkInfo')).to_have_text('No track recorded yet.')


def test_clear_is_refused_while_recording_then_confirmed_after(page, app_url):
    open_map(page, app_url)
    start_recording(page)
    set_fix(page, *HOME)
    set_fix(page, HOME[0] + M100, HOME[1])
    expect(page.locator('#trkClear')).to_be_disabled()
    page.click('#trkToggle')
    expect(page.locator('#trkClear')).to_be_enabled()
    page.click('#trkClear')
    expect(page.locator('#dlgConfirm')).to_be_visible()
    page.click('#cfCancel')
    assert len(stored(page, 'track')) == 2                  # cancelling keeps the track
    page.click('#trkClear')
    page.click('#cfOk')
    expect(page.locator('#trkInfo')).to_have_text('No track recorded yet.')
    assert stored(page, 'track') == []


# ---------- Saved offline maps ----------

def frame_small_area(page, z=14):
    center(page, *HOME, z=z)


def test_download_lists_then_delete_removes_area_and_tiles(page, app_url):
    tiles_cors(page)
    open_map(page, app_url)
    frame_small_area(page)
    open_save(page)
    page.select_option('#saveZ', '13')
    page.fill('#saveName', 'Test area')
    expect(page.locator('#saveEst')).to_contain_text('USGS Topo: about')
    page.click('#saveGo')
    expect(page.locator('#saveStatus')).to_have_text('Saved Test area. It works offline now.', timeout=30000)
    expect(page.locator('#areaList li')).to_have_count(1)
    expect(page.locator('#areaList')).to_contain_text('Test area')
    areas = stored(page, 'areas')
    assert len(areas) == 1 and areas[0]['layer'] == 'topo' and areas[0]['zMax'] == 13 and areas[0]['partial'] is False
    n = page.evaluate("caches.open('fk-tiles').then(c => c.keys()).then(k => k.length)")
    assert n >= areas[0]['tiles'] > 0
    page.click('#areaList [data-area="del"]')
    expect(page.locator('#dlgConfirm')).to_be_visible()
    page.click('#cfOk')
    expect(page.locator('#areaList')).to_contain_text('No saved maps yet')
    assert stored(page, 'areas') == []
    assert page.evaluate("caches.open('fk-tiles').then(c => c.keys()).then(k => k.filter(r => r.url.includes('/USGSTopo/')).length)") == 0


def test_cancelling_the_delete_keeps_the_area(page, app_url):
    store(page, areas=[{'id': 'a1', 'name': 'Home', 'layer': 'topo', 's': 43.0, 'w': -76.1, 'n': 43.01, 'e': -76.0,
                        'zMin': 4, 'zMax': 13, 'tiles': 10, 'bytes': 1000}])
    open_map(page, app_url)
    open_save(page)
    page.click('#areaList [data-area="del"]')
    page.click('#cfCancel')
    expect(page.locator('#areaList li')).to_have_count(1)
    assert len(stored(page, 'areas')) == 1


def test_opentopomap_cannot_be_saved(page, app_url):
    open_map(page, app_url)
    page.click('#mLayers')
    page.check('#layerList input[value="otm"]')
    open_save(page)
    expect(page.locator('#saveGo')).to_be_disabled()
    expect(page.locator('#saveEst')).to_contain_text('OpenTopoMap can’t be saved')


# ---------- Date line ----------

def test_saving_past_the_date_line_gives_a_sane_area(page, app_url):
    tiles_cors(page)
    open_map(page, app_url)
    page.evaluate('FK.leafletMap().setView([43, 181], 8, { animate: false })')
    open_save(page)
    page.select_option('#saveZ', '13')
    est = page.locator('#saveEst')
    expect(est).to_contain_text('about')
    text = est.inner_text()
    assert 'too many' not in text and 'NaN' not in text, text
    n = int(text.split('about ')[1].split(' tiles')[0].replace(',', ''))
    assert 0 < n <= 30000, text
    # the same pan at a closer zoom is small enough to download: the stored longitudes stay within +-180
    page.click('#saveClose')
    page.evaluate('FK.leafletMap().setView([43, 180.05], 11, { animate: false })')
    open_save(page)
    page.click('#saveGo')
    expect(page.locator('#saveStatus')).to_contain_text('It works offline now.', timeout=30000)
    areas = stored(page, 'areas')
    assert len(areas) == 1
    a = areas[0]
    assert -180 <= a['w'] < a['e'] <= 180 and a['tiles'] > 0 and a['partial'] is False, a


# ---------- GPX (the Track dialog's Export… opens the Export sheet, tac-io.js) ----------

def export_from_track(page):
    open_track(page)
    page.click('#trkExportOpen')
    page.wait_for_selector('#dlgExport[open]')


def test_gpx_export_has_each_marker_and_track_point(page, app_url):
    store(page, wps=[{'id': 'w1', 'name': 'Camp', 'lat': 43.01, 'lon': -76.02, 'alt': 120, 't': 1},
                     {'id': 'w2', 'name': 'Spring & Creek', 'lat': 43.2, 'lon': -76.1, 'alt': None, 't': 2}],
          track=[[43.0, -76.0, 100, 1700000000000], [43.001, -76.0, None, 1700000060000], [43.002, -76.0, 101.5, 1700000120000]])
    open_map(page, app_url)
    export_from_track(page)
    with page.expect_download() as dl:
        page.click('#exSave')
    assert dl.value.suggested_filename.startswith('fieldkit-') and dl.value.suggested_filename.endswith('.gpx')
    with open(dl.value.path(), encoding='utf-8') as f:
        gpx = f.read()
    assert gpx.count('<wpt ') == 2 and gpx.count('<trkpt ') == 3
    assert '<name>Spring &amp; Creek</name>' in gpx
    assert '<ele>120</ele>' in gpx
    assert '<trkpt lat="43.001" lon="-76">' in gpx
    assert '<time>2023-11-14T22:13:20.000Z</time>' in gpx


def test_gpx_export_with_markers_only_has_no_track(page, app_url):
    store(page, wps=[{'id': 'w1', 'name': 'Camp', 'lat': 43.01, 'lon': -76.02, 'alt': None, 't': 1}])
    open_map(page, app_url)
    export_from_track(page)
    with page.expect_download() as dl:
        page.click('#exSave')
    gpx = open(dl.value.path(), encoding='utf-8').read()
    assert gpx.count('<wpt ') == 1 and '<trk>' not in gpx


def test_gpx_export_is_off_with_nothing_to_export(page, app_url):
    open_map(page, app_url)
    export_from_track(page)
    expect(page.locator('#exSave')).to_be_disabled()
