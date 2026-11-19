"""Map layers: the retired USGS Imagery + Topo service, its replacement, and the notice shown when a map
does not load. The harness aborts every off-host request, so by default every tile fails."""
import base64, json

from playwright.sync_api import expect

PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==')
AREA = {'id': 'a1', 'name': 'Home', 'layer': 'imagery', 's': 43.0, 'w': -76.3, 'n': 43.2, 'e': -76.0,
        'zMin': 5, 'zMax': 14, 'tiles': 10, 'bytes': 1000}
MAP = '#/tactical/map'


def store(page, **kv):
    page.add_init_script('(() => {' + ''.join(
        f'if (localStorage.getItem({json.dumps("fk." + k)}) === null) localStorage.setItem({json.dumps("fk." + k)}, {json.dumps(json.dumps(v))});'
        for k, v in kv.items()) + '})()')


def tiles_ok(page):
    page.route('https://basemap.nationalmap.gov/**', lambda r: r.fulfill(status=200, content_type='image/png', body=PNG))


def layer_names(page):
    page.click('#mLayers')
    return page.locator('#layerList b').all_inner_texts()


def test_no_layer_points_at_the_retired_service_for_new_saves(page, app_url):
    page.goto(app_url + MAP)
    names = layer_names(page)
    assert names == ['USGS Topo', 'USGS Imagery', 'OpenTopoMap']


def test_stored_retired_layer_moves_to_satellite(page, app_url):
    store(page, mapLayer='imagery')
    urls = []
    page.on('request', lambda r: urls.append(r.url))
    page.goto(app_url + MAP)
    expect(page.locator('#mLayerName')).to_have_text('USGS Imagery')
    expect(page.locator('#mapNote')).to_be_visible()   # wait for a load cycle
    assert page.evaluate("JSON.parse(localStorage.getItem('fk.mapLayer'))") == 'sat'
    assert any('USGSImageryOnly/MapServer/tile/' in u for u in urls)
    assert not any('USGSImageryTopo' in u for u in urls)


def test_retired_layer_stays_while_it_has_saved_areas(page, app_url):
    store(page, mapLayer='imagery', areas=[AREA])
    page.goto(app_url + MAP)
    expect(page.locator('#mLayerName')).to_have_text('USGS Imagery + Topo (retired)')
    assert layer_names(page) == ['USGS Topo', 'USGS Imagery', 'OpenTopoMap', 'USGS Imagery + Topo (retired)']
    page.click('#layersClose')
    page.click('#mSave')
    expect(page.locator('#areaList li')).to_have_count(1)        # the saved area is still listed
    expect(page.locator('#areaList')).to_contain_text('Home')
    expect(page.locator('#saveGo')).to_be_disabled()
    expect(page.locator('#saveEst')).to_contain_text('switched this map off')


def test_notice_when_no_tile_loads(page, app_url):
    page.goto(app_url + MAP)
    note = page.locator('#mapNote')
    expect(note).to_be_visible()
    expect(note).to_contain_text('isn’t loading')
    page.click('#mapNoteLayers')
    expect(page.locator('#dlgLayers')).to_be_visible()


def test_notice_names_the_retirement_on_the_retired_layer(page, app_url):
    store(page, mapLayer='imagery', areas=[AREA])
    page.goto(app_url + MAP)
    expect(page.locator('#mapNote')).to_contain_text('USGS switched this map off on November 16, 2026')


def test_no_notice_when_tiles_load(page, app_url):
    tiles_ok(page)
    page.goto(app_url + MAP)
    page.wait_for_function("document.querySelectorAll('#map img.leaflet-tile-loaded').length > 0")
    page.wait_for_timeout(300)
    expect(page.locator('#mapNote')).to_be_hidden()


def test_notice_clears_after_switching_to_a_map_that_loads(page, app_url):
    page.route('https://basemap.nationalmap.gov/**/USGSImageryOnly/**',
               lambda r: r.fulfill(status=200, content_type='image/png', body=PNG))
    page.goto(app_url + MAP)
    expect(page.locator('#mapNote')).to_be_visible()
    page.click('#mapNoteLayers')
    page.check('#layerList input[value="sat"]')
    expect(page.locator('#mLayerName')).to_have_text('USGS Imagery')
    expect(page.locator('#mapNote')).to_be_hidden()


def test_note_fits_beside_the_map_buttons(page, app_url):
    page.goto(app_url + MAP)
    expect(page.locator('#mapNote')).to_be_visible()
    over = page.evaluate("""() => { const n = document.querySelector('#mapNote').getBoundingClientRect();
      return [...document.querySelectorAll('.mapctl button, .leaflet-control-zoom a, .maptag span:not([hidden])')].some(b => { const r = b.getBoundingClientRect();
        return r.left < n.right && r.right > n.left && r.top < n.bottom && r.bottom > n.top; }); }""")
    assert not over
