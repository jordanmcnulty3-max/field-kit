"""Distance units: the Settings choice, every distance following it, and the scale bar."""
import math
import re

import pytest
from playwright.sync_api import expect

from .tac import store, open_map, set_fix, center, open_track
from .test_map import tiles_ok

HOME = (43.0, -76.0)
NOW = 1_800_000_000_000


def boot(page, app_url, night=False, z=15, **kv):
    page.clock.install(time=NOW / 1000)
    page.goto('about:blank')
    tiles_ok(page)
    store(page, **{'advAck': True, 'night': night, 'mapView': {'lat': HOME[0], 'lon': HOME[1], 'z': z}, 'mapFollow': False, **kv})
    open_map(page, app_url)


def centre_away(page, metres, bearing=90, z=15):
    """Put the crosshair this far from the fix."""
    p = page.evaluate('([a, b, c]) => TGEOM.dest(43.0, -76.0, a, b)', [bearing, metres, 0])
    center(page, p['lat'], p['lon'], z)


def v77(m):
    """How v7.7 wrote a distance."""
    return f'{round(m)} m' if m < 1000 else f'{m / 1000:.{2 if m < 10000 else 1}f} km'


def rel(page):
    return page.locator('#mCenterRel')


def choose(page, unit):
    """Through the Settings sheet, as a user does."""
    page.click('#menuBtn')
    page.locator(f'#unitDist button[data-unit="{unit}"]').click()
    page.click('#menuClose')


def scale(page):
    page.wait_for_function('() => document.querySelector("#mapScale .lab").textContent !== ""')
    return page.evaluate("""() => { const e = document.querySelector('#mapScale'); const l = e.querySelector('.line');
      return { label: e.querySelector('.lab').textContent, w: l.getBoundingClientRect().width, hidden: e.hidden }; }""")


def label_m(label):
    n, u = re.match(r'([\d.]+) (\w+)', label).groups()
    return float(n) * {'m': 1, 'km': 1000, 'yd': 0.9144, 'mi': 1609.344}[u]


def m_per_px(page):
    """Ground metres per screen pixel from the Web Mercator formula, not from the app's or Leaflet's own maths:
    156543.03 m a pixel at zoom 0 on the equator, times cos(latitude), halved at each zoom."""
    lat, z = page.evaluate('(() => { const m = FK.leafletMap(); return [m.getCenter().lat, m.getZoom()]; })()')
    return 156543.03 * math.cos(math.radians(lat)) / 2 ** z


def test_default_is_metric_and_reads_as_v77(page, app_url):
    boot(page, app_url)
    set_fix(page, *HOME)
    assert page.evaluate('FK.tac.unit()') == 'metric'
    assert page.evaluate("localStorage.getItem('fk.distUnit')") is None
    for m in (412, 2400, 14000):
        centre_away(page, m)
        got = rel(page).inner_text()
        want = page.evaluate('() => { const c = FK.leafletMap().getCenter().wrap(); return GEO.distance(43.0, -76.0, c.lat, c.lng); }')
        assert got.startswith(v77(want)), (got, v77(want))


def test_the_setting_is_a_labelled_44px_choice_in_settings(page, app_url):
    boot(page, app_url)
    page.click('#menuBtn')
    expect(page.locator('#dlgMenu')).to_contain_text('Distances')
    btns = page.locator('#unitDist button')
    assert btns.all_inner_texts() == ['Metric (m, km)', 'US (yd, mi)']
    for i in range(2):
        assert btns.nth(i).bounding_box()['height'] >= 44
    assert btns.nth(0).get_attribute('aria-selected') == 'true'
    assert btns.nth(1).get_attribute('aria-selected') == 'false'


def test_switching_to_us_changes_everything_without_a_reload(page, app_url):
    wps = [{'id': 'a', 'name': 'Alpha', 'lat': 43.0, 'lon': -76.0 + 0.0052, 'alt': None, 't': 1, 'kind': 'point', 'note': ''}]
    track = [[43.0, -76.0, None, NOW - 600000], [43.0, -76.0 + 0.0052, None, NOW]]
    boot(page, app_url, wps=wps, track=track, target='a')
    page.evaluate('window.__same = 1')
    set_fix(page, *HOME)
    centre_away(page, 412)
    page.wait_for_function("document.querySelector('#mCenterRel').textContent.includes(' m at ')")
    before = scale(page)['label']
    assert before.endswith(' m')
    choose(page, 'us')
    expect(rel(page)).to_contain_text(re.compile(r'45\d yd at'))
    assert scale(page)['label'].endswith(' yd')
    page.click('#mList')
    row = page.locator('#lsList li .hint').first
    expect(row).to_contain_text(re.compile(r'\d+ yd at'))
    page.evaluate("FK.sheet.close(document.querySelector('#dlgList'))")
    open_track(page)
    expect(page.locator('#trkInfo')).to_contain_text(re.compile(r'\d+ yd over'))
    page.evaluate("FK.sheet.close(document.querySelector('#dlgTrack'))")
    page.evaluate("FK.route.go('/tactical/position')")
    page.wait_for_function("!document.querySelector('#navPanel').hidden && !document.querySelector('#nvDist').hidden")
    info = page.locator('#navPanel').inner_text()
    assert re.search(r'^\d+ yd$', page.locator('#nvDist').inner_text()) and ' km' not in info and ' mi' not in info
    assert page.evaluate('window.__same') == 1


def test_position_screen_follows_the_setting_in_both_units(page, app_url):
    wps = [{'id': 'a', 'name': 'Alpha', 'lat': 43.0, 'lon': -76.0 + 0.0052, 'alt': None, 't': 1, 'kind': 'point', 'note': ''}]
    boot(page, app_url, wps=wps, target='a', distUnit='us')
    set_fix(page, *HOME, alt=100, spd=10)
    page.evaluate("FK.route.go('/tactical/position')")
    page.wait_for_function("!document.querySelector('#navPanel').hidden && !document.querySelector('#nvDist').hidden")
    assert page.locator('#nvDist').inner_text().endswith(' yd')
    assert page.locator('#sAlt').inner_text() == '328 ft'
    assert page.locator('#sSpd').inner_text() == '22.4 mph'
    page.evaluate("FK.tac.setUnit('metric')")
    assert re.search(r'^\d+ m$', page.locator('#nvDist').inner_text())
    assert page.locator('#sAlt').inner_text() == '328 ft'
    assert page.locator('#sSpd').inner_text() == '22.4 mph'


def test_the_setting_survives_a_reload(page, app_url):
    boot(page, app_url)
    choose(page, 'us')
    assert page.evaluate("localStorage.getItem('fk.distUnit')") == '"us"'
    page.reload()
    page.wait_for_function('window.FK && FK.tac && document.querySelector("#map .leaflet-pane")')
    assert page.evaluate('FK.tac.unit()') == 'us'
    assert scale(page)['label'].endswith((' yd', ' mi'))
    page.click('#menuBtn')
    assert page.locator('#unitDist button[data-unit="us"]').get_attribute('aria-selected') == 'true'


@pytest.mark.parametrize('z', [8, 11, 13, 15, 17, 18])
@pytest.mark.parametrize('unit', ['metric', 'us'])
def test_scale_bar_width_times_metres_per_pixel_equals_its_label(page, app_url, unit, z):
    boot(page, app_url, z=z, distUnit=unit)
    s = scale(page)
    assert 0 < s['w'] <= 120
    want = label_m(s['label'])
    got = s['w'] * m_per_px(page)
    assert abs(got / want - 1) < 0.02, (s, got, want)


def test_scale_bar_updates_on_zoom_and_on_unit(page, app_url):
    boot(page, app_url, z=13)
    a = scale(page)['label']
    page.evaluate('FK.leafletMap().setZoom(17, { animate: false })')
    page.wait_for_function('l => document.querySelector("#mapScale .lab").textContent !== l', arg=a)
    b = scale(page)
    assert abs(b['w'] * m_per_px(page) / label_m(b['label']) - 1) < 0.02
    page.evaluate("FK.tac.setUnit('us')")
    page.wait_for_function('() => /yd|mi/.test(document.querySelector("#mapScale .lab").textContent)')


def test_scale_bar_sits_above_the_bar_clear_of_attribution_and_reads_in_night(page, app_url):
    boot(page, app_url, night=True)
    sc = page.locator('#mapScale')
    bar, att = page.locator('.mapbar').bounding_box(), page.locator('.leaflet-control-attribution')
    b = sc.bounding_box()
    assert b['y'] + b['height'] <= bar['y'] + 0.5 and b['x'] < 60
    if att.count() and att.is_visible():
        a = att.bounding_box()
        assert b['y'] + b['height'] <= a['y'] + 0.5 or b['x'] + b['width'] <= a['x'] or a['y'] + a['height'] <= b['y']
    assert page.evaluate("getComputedStyle(document.querySelector('#mapScale .lab')).textShadow") != 'none' or \
        page.evaluate("getComputedStyle(document.querySelector('#mapScale')).backgroundColor") != 'rgba(0, 0, 0, 0)'
