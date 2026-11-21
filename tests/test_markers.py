"""Markers: thirteen kinds with icons, one sheet to create and edit a marker, the list sheet, and drawing on the map."""
import json

import pytest
from playwright.sync_api import expect

from .tac import store, open_map, set_fix, center
from .test_map import tiles_ok

HOME = (43.0, -76.0)
HOUR = 3600 * 1000
NOW = 1_800_000_000_000   # the page's clock is frozen here (time then runs on from it), so ages don't depend on when the suite runs
FULL = 'Couldn’t save: phone storage for Field Kit is full. Back up, then delete old tracks or saved maps.'
WPS_FULL = """(() => { const set = Storage.prototype.setItem;
  Storage.prototype.setItem = function (k, v) { if (k === 'fk.wps') throw new DOMException('full', 'QuotaExceededError'); return set.call(this, k, v); }; })()"""
KINDS = ['point', 'camp', 'vehicle', 'water', 'cache', 'hazard', 'rally', 'observe', 'medical',
         'friend', 'hostile', 'neutral', 'unknown']
EVIL = '<img src=x onerror=window.x=1>'


def mk(id_, name, lat=HOME[0], lon=HOME[1], kind='point', t=1, note=''):
    return {'id': id_, 'name': name, 'lat': lat, 'lon': lon, 'alt': None, 't': t, 'kind': kind, 'note': note}


def boot(page, app_url, markers=(), night=False, view=HOME, full=False, **kv):
    """about:blank first, so stepping back too far would leave Field Kit; then the map, centred on view.
    full=True makes saving markers fail as when phone storage is full."""
    page.clock.install(time=NOW / 1000)
    page.goto('about:blank')
    tiles_ok(page)   # no "map isn't loading" note over the markers
    store(page, **{'wps': list(markers), 'advAck': True, 'night': night, 'mapView': {'lat': view[0], 'lon': view[1], 'z': 15},
                   'mapFollow': False, **kv})
    if full:
        page.add_init_script(WPS_FULL)   # after the seeding script, which must still write
    open_map(page, app_url)


def wps(page):
    return page.evaluate("JSON.parse(localStorage.getItem('fk.wps') || '[]')")


def sheet(page):
    return page.locator('#dlgMarker')


def open_new(page):
    page.click('#mMark')
    expect(sheet(page)).to_be_visible()


def pin(page, id_):
    return page.locator(f'.mk-pin[data-id="{id_}"]')


def open_marker(page, id_):
    pin(page, id_).click()
    expect(sheet(page)).to_be_visible()


def no_popup(page):
    assert page.locator('.leaflet-popup').count() == 0


# ---------- New marker ----------

def test_mark_opens_sheet_and_cancel_adds_nothing(page, app_url):
    boot(page, app_url, [mk('w1', 'Camp')])
    open_new(page)
    expect(page.locator('#mkName')).to_have_value('WP 2')
    expect(page.locator('#dlgMarker [data-kind="point"]')).to_have_attribute('aria-pressed', 'true')
    expect(page.locator('#mkGo')).to_be_visible()
    expect(page.locator('#mkDel')).to_be_hidden()
    expect(page.locator('#mkMove')).to_be_hidden()   # Move is for existing markers
    page.click('#mkCancel')
    expect(sheet(page)).to_be_hidden()
    assert [w['id'] for w in wps(page)] == ['w1']


def test_back_cancels_a_new_marker(page, app_url):
    boot(page, app_url)
    open_new(page)
    page.go_back()
    expect(sheet(page)).to_be_hidden()
    assert wps(page) == []
    assert page.evaluate('location.hash') == '#/tactical/map'


def test_save_adds_marker_with_kind_and_note(page, app_url):
    boot(page, app_url)
    center(page, 43.08, -76.3)
    open_new(page)
    page.click('#dlgMarker [data-kind="hazard"]')
    expect(page.locator('#dlgMarker [data-kind="hazard"]')).to_have_attribute('aria-pressed', 'true')
    expect(page.locator('#dlgMarker [data-kind="point"]')).to_have_attribute('aria-pressed', 'false')
    page.fill('#mkNote', 'Washed-out bridge')
    page.click('#mkSave')
    expect(sheet(page)).to_be_hidden()
    w = wps(page)
    assert len(w) == 1
    assert w[0]['kind'] == 'hazard' and w[0]['note'] == 'Washed-out bridge' and w[0]['name'] == 'WP 1'
    assert abs(w[0]['lat'] - 43.08) < 1e-6 and abs(w[0]['lon'] + 76.3) < 1e-6
    expect(pin(page, w[0]['id'])).to_have_count(1)
    # the next new marker starts as a Point again (v7.8 final review: a carried-over kind was easy to miss)
    open_new(page)
    expect(page.locator('#dlgMarker [data-kind="point"]')).to_have_attribute('aria-pressed', 'true')
    expect(page.locator('#dlgMarker [data-kind="hazard"]')).to_have_attribute('aria-pressed', 'false')


def test_affiliation_default_name_follows_kind_until_typed(page, app_url):
    boot(page, app_url, [mk('w1', 'Hostile 1', kind='hostile')])
    open_new(page)
    expect(page.locator('#mkName')).to_have_value('WP 2')
    page.click('#dlgMarker [data-kind="hostile"]')
    expect(page.locator('#mkName')).to_have_value('Hostile 2')
    page.click('#dlgMarker [data-kind="friend"]')
    expect(page.locator('#mkName')).to_have_value('Friend 1')
    page.click('#dlgMarker [data-kind="camp"]')
    expect(page.locator('#mkName')).to_have_value('WP 2')
    page.fill('#mkName', 'Ridge')
    page.click('#dlgMarker [data-kind="neutral"]')
    expect(page.locator('#mkName')).to_have_value('Ridge')
    page.click('#mkSave')
    expect(sheet(page)).to_be_hidden()
    assert [(w['name'], w['kind']) for w in wps(page)][-1] == ('Ridge', 'neutral')


@pytest.mark.parametrize('night', [False, True], ids=['day', 'night'])
def test_all_thirteen_kinds_have_a_button_with_a_visible_label(page, app_url, night):
    boot(page, app_url, night=night)
    assert page.evaluate('FK.tac.KINDS.map(k => k.id)') == KINDS
    labels = page.evaluate('Object.fromEntries(FK.tac.KINDS.map(k => [k.id, k.label]))')
    open_new(page)
    for k in KINDS:
        b = page.locator(f'#dlgMarker [data-kind="{k}"]')
        expect(b).to_have_count(1)
        b.scroll_into_view_if_needed()
        expect(b).to_be_visible()
        expect(b).to_have_text(labels[k])
        box = b.bounding_box()
        assert box['width'] >= 44 and box['height'] >= 44, (k, box)
        assert b.locator('svg').count() == 1
    # affiliation kinds sit under their own label, after the nine places
    expect(page.locator('#dlgMarker .mk-sub')).to_have_text('Affiliation')
    # no sideways scrolling, and Save stays on screen with the sheet inside the viewport
    assert page.evaluate("[...document.querySelectorAll('#dlgMarker, #dlgMarker *')].every(e => e.scrollWidth <= e.clientWidth + 1 || getComputedStyle(e).overflowX === 'hidden' || e.tagName === 'TEXTAREA' || e.tagName === 'INPUT')")
    d = sheet(page).bounding_box()
    assert d['y'] >= 0 and d['y'] + d['height'] <= 640 + 1
    s = page.locator('#mkSave').bounding_box()
    assert s['y'] + s['height'] <= 640 and s['height'] >= 44
    # icons are drawn (not blank) in this theme: place icons use the text colour, frames have a fill or outline
    colour = page.evaluate("getComputedStyle(document.querySelector('#dlgMarker [data-kind=camp] svg')).color")
    bg = page.evaluate("getComputedStyle(document.querySelector('#dlgMarker')).backgroundColor")
    assert colour != bg


def test_note_count_shows_only_near_the_limit(page, app_url):
    boot(page, app_url)
    open_new(page)
    expect(page.locator('#mkNote')).to_have_attribute('maxlength', '500')
    page.fill('#mkNote', 'x' * 440)
    expect(page.locator('#mkLeft')).to_be_hidden()
    page.fill('#mkNote', 'x' * 460)
    expect(page.locator('#mkLeft')).to_be_visible()
    expect(page.locator('#mkLeft')).to_have_text('40 characters left')


def test_grid_and_distance_in_the_sheet(page, app_url):
    boot(page, app_url)
    open_new(page)
    expect(page.locator('#mkGrid')).to_contain_text('18T')
    expect(page.locator('#mkRel')).to_be_hidden()
    page.click('#mkCancel')
    expect(sheet(page)).to_be_hidden()
    set_fix(page, HOME[0] - 0.009, HOME[1])
    center(page, *HOME)
    open_new(page)
    expect(page.locator('#mkRel')).to_be_visible()
    expect(page.locator('#mkRel')).to_have_text('1.00 km at 0° true from you')


def test_far_north_marker_shows_latitude_and_longitude(page, app_url):
    boot(page, app_url, [mk('w1', 'Station', lat=86.5, lon=10.25)], view=(86.5, 10.25))
    page.evaluate("FK.markers.edit('w1')")
    expect(sheet(page)).to_be_visible()
    expect(page.locator('#mkGrid')).to_have_text('86.50000, 10.25000')
    page.click('#mkCancel')
    expect(sheet(page)).to_be_hidden()
    page.evaluate('FK.markers.openList()')
    expect(page.locator('#dlgList')).to_be_visible()
    row = page.locator('#lsList li').first.inner_text()
    assert '86.50000, 10.25000' in row
    for el in ('#dlgList', '#dlgMarker'):
        txt = page.inner_text(el)
        assert 'null' not in txt and 'undefined' not in txt and 'NaN' not in txt


# ---------- Existing marker ----------

def test_tap_marker_opens_its_sheet(page, app_url):
    boot(page, app_url, [mk('w1', 'Camp', kind='camp', note='Two tents')])
    no_popup(page)
    open_marker(page, 'w1')
    no_popup(page)
    expect(page.locator('#mkName')).to_have_value('Camp')
    expect(page.locator('#mkNote')).to_have_value('Two tents')
    expect(page.locator('#dlgMarker [data-kind="camp"]')).to_have_attribute('aria-pressed', 'true')
    expect(page.locator('#mkGo')).to_be_visible()
    expect(page.locator('#mkDel')).to_be_visible()
    expect(page.locator('#mkMove')).to_be_visible()   # Move is for existing markers
    page.wait_for_timeout(200)
    no_popup(page)


def test_edit_changes_name_kind_note(page, app_url):
    boot(page, app_url, [mk('w1', 'Camp')])
    open_marker(page, 'w1')
    page.fill('#mkName', 'Base')
    page.click('#dlgMarker [data-kind="water"]')
    page.fill('#mkNote', 'Spring')
    page.click('#mkSave')
    expect(sheet(page)).to_be_hidden()
    w = wps(page)[0]
    assert (w['name'], w['kind'], w['note'], w['id']) == ('Base', 'water', 'Spring', 'w1')
    expect(pin(page, 'w1').locator('b')).to_have_text('Base')


def test_edits_are_discarded_by_cancel_and_by_back_after_asking(page, app_url):
    boot(page, app_url, [mk('w1', 'Camp')])
    before = wps(page)
    open_marker(page, 'w1')
    page.fill('#mkName', 'Changed')
    page.click('#dlgMarker [data-kind="cache"]')
    page.click('#mkCancel')   # the sheet's own Cancel is the choice to throw the edits away
    expect(sheet(page)).to_be_hidden()
    assert wps(page) == before
    open_marker(page, 'w1')
    expect(page.locator('#mkName')).to_have_value('Camp')
    page.fill('#mkNote', 'Changed')
    page.go_back()   # Back asks first (v7.8 final review)
    expect(page.locator('#cfTitle')).to_have_text('Discard this marker?')
    page.click('#cfOk')
    expect(sheet(page)).to_be_hidden()
    assert wps(page) == before


def test_delete_asks_first(page, app_url):
    boot(page, app_url, [mk('w1', 'Camp'), mk('w2', 'Spring', lat=HOME[0] + 0.003)])
    open_marker(page, 'w1')
    page.click('#mkDel')
    cf = page.locator('#dlgConfirm')
    expect(cf).to_be_visible()
    expect(page.locator('#cfText')).to_have_text('Delete marker Camp? This can’t be undone.')
    expect(cf.locator('[data-act="ok"]')).to_have_text('Delete marker')
    assert page.evaluate('document.activeElement.textContent.trim()') == 'Cancel'
    page.click('#cfCancel')
    expect(cf).to_be_hidden()
    expect(sheet(page)).to_be_visible()
    assert len(wps(page)) == 2
    page.click('#mkDel')
    page.click('#cfOk')
    expect(cf).to_be_hidden()
    expect(sheet(page)).to_be_hidden()
    assert [w['id'] for w in wps(page)] == ['w2']
    expect(pin(page, 'w1')).to_have_count(0)
    page.wait_for_function('history.state.fkSheet === undefined')
    page.wait_for_timeout(600)
    assert page.evaluate('location.hash') == '#/tactical/map'
    page.go_back()
    assert page.url == 'about:blank'


def test_go_to_sets_target(page, app_url):
    boot(page, app_url, [mk('w1', 'Camp')])
    open_marker(page, 'w1')
    expect(page.locator('#mkGo')).to_have_text('Go to')
    page.click('#mkGo')
    expect(sheet(page)).to_be_hidden()
    assert page.evaluate('FK.tac.target()') == {'type': 'marker', 'id': 'w1'}
    expect(pin(page, 'w1')).to_have_class('mk-pin tgt')
    open_marker(page, 'w1')
    expect(page.locator('#mkGo')).to_have_text('Stop')
    page.click('#mkGo')
    expect(sheet(page)).to_be_hidden()
    assert page.evaluate('FK.tac.target()') is None
    expect(pin(page, 'w1')).to_have_class('mk-pin')


def test_note_and_name_are_text_not_markup(page, app_url):
    boot(page, app_url, [mk('w1', EVIL, note=EVIL)])
    expect(pin(page, 'w1').locator('b')).to_have_text(EVIL)
    open_marker(page, 'w1')
    expect(page.locator('#mkName')).to_have_value(EVIL)
    expect(page.locator('#mkNote')).to_have_value(EVIL)
    page.click('#mkCancel')
    expect(sheet(page)).to_be_hidden()
    page.click('#mList')
    expect(page.locator('#dlgList')).to_be_visible()
    expect(page.locator('#lsList li .mk-name')).to_have_text(EVIL)
    assert page.locator('#dlgList img, .leaflet-marker-pane img').count() == 0
    assert page.evaluate('window.x') is None


def test_affiliation_marker_shows_age_and_fades(page, app_url):
    old = NOW - 25 * HOUR
    boot(page, app_url, [mk('h1', 'Hostile 1', kind='hostile', t=old), mk('c1', 'Camp', kind='camp', t=old, lat=HOME[0] + 0.002)])
    expect(pin(page, 'h1')).to_have_class('mk-pin stale')
    expect(pin(page, 'c1')).to_have_class('mk-pin')
    assert pin(page, 'h1').locator('svg .af').get_attribute('fill') == 'none'
    open_marker(page, 'h1')
    expect(page.locator('#mkAge')).to_be_visible()
    expect(page.locator('#mkAge')).to_have_text(__import__('re').compile(r'^Marked .*\d{1,2}:\d{2}, 1 day ago$'))
    page.click('#mkCancel')
    expect(sheet(page)).to_be_hidden()
    open_marker(page, 'c1')
    expect(page.locator('#mkAge')).to_be_hidden()


def test_age_wording(page, app_url):
    boot(page, app_url, [mk('a', 'A', kind='friend', t=NOW - 5 * 60000), mk('b', 'B', kind='unknown', t=NOW - 3 * HOUR - 60000, lat=HOME[0] + 0.001),
                         mk('c', 'C', kind='neutral', t=NOW - 50 * HOUR, lat=HOME[0] + 0.002)])
    ages = page.evaluate("['a', 'b', 'c'].map(id => FK.markers.ageText(FK.tac.markers().find(m => m.id === id).t))")
    assert ages == ['5 min ago', '3 h ago', '2 days ago']
    expect(pin(page, 'a')).to_have_class('mk-pin')
    expect(pin(page, 'c')).to_have_class('mk-pin stale')


def test_icons_are_svg_with_frames_for_affiliations(page, app_url):
    boot(page, app_url)
    out = page.evaluate("FK.tac.KINDS.map(k => [k.id, FK.markers.icon(k.id), FK.markers.icon(k.id, { stale: true })])")
    for kid, svg, stale in out:
        assert svg.startswith('<svg') and 'viewBox="0 0 24 24"' in svg, kid
        if kid in ('friend', 'hostile', 'neutral', 'unknown'):
            assert 'class="af' in svg and 'fill="#' in svg and 'fill="none"' in stale, kid
        else:
            assert 'currentColor' in svg and svg == stale, kid
    assert len({svg for _, svg, _ in out}) == 13
    assert page.evaluate("FK.markers.icon('nonsense')") == page.evaluate("FK.markers.icon('point')")


# ---------- Map ----------

def test_long_press_marks_the_pressed_point(page, app_url):
    boot(page, app_url)
    box = page.locator('#map').bounding_box()
    x, y = box['x'] + 80, box['y'] + 120
    want = page.evaluate('([x, y]) => { const ll = FK.leafletMap().containerPointToLatLng([x, y]); return [ll.lat, ll.lng]; }', [80, 120])
    page.mouse.click(x, y, button='right')
    expect(sheet(page)).to_be_visible()
    page.click('#mkSave')
    expect(sheet(page)).to_be_hidden()
    w = wps(page)[0]
    assert abs(w['lat'] - want[0]) < 1e-5 and abs(w['lon'] - want[1]) < 1e-5


def test_one_marker_of_each_kind_is_drawn_with_its_name(page, app_url):
    ms = [mk(f'k{i}', k.title(), lat=HOME[0] + (i % 4) * 0.001, lon=HOME[1] + (i // 4) * 0.0015, kind=k, t=NOW) for i, k in enumerate(KINDS)]
    boot(page, app_url, ms)
    for m in ms:
        expect(pin(page, m['id']).locator('b')).to_have_text(m['name'])
        assert pin(page, m['id']).locator('svg').count() == 1
    assert page.locator('#mList').is_visible()
    assert page.locator('#mTools').is_visible()
    b = page.locator('#mList').bounding_box()
    assert b['width'] >= 44 and b['height'] >= 44


# ---------- List ----------

def list_names(page):
    return page.locator('#lsList li .mk-name').all_inner_texts()


def test_list_empty_state(page, app_url):
    boot(page, app_url)
    page.click('#mList')
    expect(page.locator('#dlgList')).to_be_visible()
    expect(page.locator('#lsList')).to_have_text('No markers yet. Move the map so the crosshair is where you want one, then press Mark.')


def test_list_sorted_nearest_first_with_fix_and_newest_first_without(page, app_url):
    ms = [mk('a', 'Far old', lat=HOME[0] + 0.02, kind='camp', t=NOW - 3 * HOUR),
          mk('b', 'Near newest', lat=HOME[0] + 0.001, kind='water', t=NOW - 1 * HOUR),
          mk('c', 'Middle', lat=HOME[0] + 0.005, kind='hostile', t=NOW - 2 * HOUR)]
    boot(page, app_url, ms)
    page.click('#mList')
    expect(page.locator('#dlgList')).to_be_visible()
    assert list_names(page) == ['Near newest', 'Middle', 'Far old']
    first = page.locator('#lsList li').first
    assert first.locator('svg').count() == 1
    expect(first).to_contain_text('18T')
    expect(first).not_to_contain_text('true')
    page.click('#lsClose')
    expect(page.locator('#dlgList')).to_be_hidden()
    # with a fix south of Far old, nearest first
    set_fix(page, HOME[0] + 0.03, HOME[1])
    page.click('#mList')
    expect(page.locator('#dlgList')).to_be_visible()
    assert list_names(page) == ['Far old', 'Middle', 'Near newest']
    expect(page.locator('#lsList li').first).to_contain_text('° true')
    expect(page.locator('#lsList li').first).to_contain_text('1.11 km')
    # affiliation rows add the age
    expect(page.locator('#lsList li').nth(1)).to_contain_text('2 h ago')
    expect(page.locator('#lsList li').first).not_to_contain_text('ago')
    # filter: All, then only kinds that exist
    chips = page.locator('#lsChips button').all_inner_texts()
    assert chips == ['All', 'Camp', 'Water', 'Hostile']
    page.click('#lsChips button[data-kind="hostile"]')
    expect(page.locator('#lsChips button[data-kind="hostile"]')).to_have_attribute('aria-pressed', 'true')
    assert list_names(page) == ['Middle']
    page.click('#lsChips button[data-kind="all"]')
    assert list_names(page) == ['Far old', 'Middle', 'Near newest']
    for b in page.locator('#lsChips button').all():
        assert b.bounding_box()['height'] >= 44


def test_list_row_centres_map_and_opens_sheet(page, app_url):
    ms = [mk('a', 'Here', kind='camp'), mk('b', 'Away', lat=43.2, lon=-76.5, kind='cache')]
    boot(page, app_url, ms, mapFollow=True)
    page.click('#mList')
    expect(page.locator('#dlgList')).to_be_visible()
    page.locator('#lsList li', has_text='Away').click()
    expect(page.locator('#dlgList')).to_be_hidden()
    expect(sheet(page)).to_be_visible()
    expect(page.locator('#mkName')).to_have_value('Away')
    c = page.evaluate('(() => { const c = FK.leafletMap().getCenter(); return [c.lat, c.lng]; })()')
    assert abs(c[0] - 43.2) < 1e-4 and abs(c[1] + 76.5) < 1e-4
    expect(page.locator('#mLocate')).to_have_attribute('aria-pressed', 'false')
    page.click('#mkCancel')
    expect(sheet(page)).to_be_hidden()
    page.wait_for_function('history.state.fkSheet === undefined')
    page.wait_for_timeout(600)
    page.go_back()
    assert page.url == 'about:blank'


def test_list_marks_the_target(page, app_url):
    boot(page, app_url, [mk('a', 'One'), mk('b', 'Two', lat=HOME[0] + 0.001)], target='b')
    page.click('#mList')
    expect(page.locator('#lsList li.tgt .mk-name')).to_have_text('Two')


# ---------- Position and search ----------

def test_position_markers_block_counts_and_opens_the_list(page, app_url):
    boot(page, app_url, [mk('a', 'One', t=NOW - HOUR), mk('b', 'Two', lat=HOME[0] + 0.001, t=NOW)])
    page.evaluate("FK.route.go('/tactical/position')")
    page.wait_for_function("FK.view() === 'position'")
    blk = page.locator('#blkWaypoints')
    expect(blk.locator('h2')).to_have_text('Markers')
    expect(page.locator('#wpCount')).to_have_text('2 markers')
    assert page.locator('#wpList').count() == 0
    page.click('#wpOpenList')
    expect(page.locator('#dlgList')).to_be_visible()
    assert page.evaluate("FK.view()") == 'map'
    assert list_names(page) == ['Two', 'One']


def test_position_count_singular_and_none(page, app_url):
    boot(page, app_url, [mk('a', 'One')])
    page.evaluate("FK.route.go('/tactical/position')")
    expect(page.locator('#wpCount')).to_have_text('1 marker')
    page.evaluate("FK.tac.removeMarker('a')")
    expect(page.locator('#wpCount')).to_have_text('No markers yet')


def test_search_waypoints_opens_the_list(page, app_url):
    boot(page, app_url, [mk('a', 'One')])
    page.evaluate("FK.route.go('/tactical/ballistics')")
    page.wait_for_function("FK.view() === 'ballistics'")
    page.click('#searchBtn')
    page.wait_for_selector('#searchPane', state='visible')
    page.fill('#searchInput', 'waypoints')
    page.click('#searchBody .sr-item[data-key="a:waypoints"]')
    expect(page.locator('#dlgList')).to_be_visible()
    assert page.evaluate("FK.view()") == 'map'
    assert list_names(page) == ['One']


def test_no_waypoint_wording_on_the_tactical_screens(page, app_url):
    boot(page, app_url, [mk('a', 'One')])
    open_new(page)
    page.click('#mkCancel')
    page.click('#mList')
    expect(page.locator('#dlgList')).to_be_visible()
    text = page.evaluate("document.body.innerText + [...document.querySelectorAll('[aria-label],[placeholder],[title]')].map(e => (e.getAttribute('aria-label') || '') + (e.getAttribute('placeholder') || '') + (e.getAttribute('title') || '')).join(' ')")
    assert 'waypoint' not in text.lower()


# ---------- Fix round 1 ----------

def toast_cleared(page):
    page.evaluate("document.querySelector('#toast').textContent = ''")


def test_save_new_marker_when_storage_is_full(page, app_url):
    boot(page, app_url, full=True)
    open_new(page)
    page.fill('#mkName', 'Ridge')
    page.click('#dlgMarker [data-kind="hazard"]')
    toast_cleared(page)
    page.click('#mkSave')
    expect(sheet(page)).to_be_hidden()
    expect(page.locator('#toast')).to_have_text(FULL)
    ids = page.evaluate('FK.tac.markers().map(m => m.id)')
    assert len(ids) == 1 and page.evaluate('FK.tac.markers()[0].name') == 'Ridge'
    expect(pin(page, ids[0]).locator('b')).to_have_text('Ridge')
    page.click('#mList')
    expect(page.locator('#lsList li .mk-name')).to_have_text('Ridge')
    page.click('#lsClose')
    expect(page.locator('#dlgList')).to_be_hidden()
    assert page.evaluate("localStorage.getItem('fk.lastKind')") is None
    page.wait_for_timeout(2000)
    toast_cleared(page)
    open_new(page)
    page.fill('#mkName', 'Second')
    page.click('#mkSave')
    expect(sheet(page)).to_be_hidden()
    expect(page.locator('#toast')).to_have_text(FULL)
    assert page.evaluate('FK.tac.markers().map(m => m.name)') == ['Ridge', 'Second']
    assert page.evaluate("localStorage.getItem('fk.lastKind')") is None


def test_save_edit_when_storage_is_full(page, app_url):
    boot(page, app_url, [mk('w1', 'Camp')], full=True)
    for n, name in enumerate(['Base', 'Base two']):
        if n:
            page.wait_for_timeout(2000)
        open_marker(page, 'w1')
        page.fill('#mkName', name)
        page.click('#dlgMarker [data-kind="water"]')
        toast_cleared(page)
        page.click('#mkSave')
        expect(sheet(page)).to_be_hidden()
        expect(page.locator('#toast')).to_have_text(FULL)
        expect(pin(page, 'w1').locator('b')).to_have_text(name)
        assert page.evaluate("FK.tac.markers()[0].kind") == 'water'
    assert page.evaluate("localStorage.getItem('fk.lastKind')") is None
    assert wps(page)[0]['name'] == 'Camp'   # what is stored is unchanged


def test_marker_removed_while_its_sheet_is_open(page, app_url):
    boot(page, app_url, [mk('w2', 'Spring', lat=HOME[0] + 0.003)])
    for button in ('#mkSave', '#mkGo', '#mkDel'):
        nid = page.evaluate("FK.tac.addMarker({ lat: 43.0, lon: -76.0, name: 'Gone' }).id")
        page.evaluate("id => FK.markers.edit(id)", nid)
        expect(sheet(page)).to_be_visible()
        page.evaluate("id => FK.tac.removeMarker(id)", nid)
        toast_cleared(page)
        page.click(button)
        expect(sheet(page)).to_be_hidden()
        expect(page.locator('#toast')).to_have_text('That marker no longer exists.')
        assert page.locator('#dlgConfirm[open]').count() == 0
        page.wait_for_function('history.state.fkSheet === undefined')
    assert [w['id'] for w in wps(page)] == ['w2']
    assert page.evaluate('FK.tac.target()') is None


def test_go_to_on_a_new_marker_saves_it_and_targets_it(page, app_url):
    boot(page, app_url)
    open_new(page)
    page.fill('#mkName', 'Rally')
    page.click('#dlgMarker [data-kind="rally"]')
    page.click('#mkGo')
    expect(sheet(page)).to_be_hidden()
    w = wps(page)
    assert [(x['name'], x['kind']) for x in w] == [('Rally', 'rally')]
    assert page.evaluate('FK.tac.target()') == {'type': 'marker', 'id': w[0]['id']}
    assert page.evaluate("localStorage.getItem('fk.lastKind')") is None   # the kind is not carried to the next marker


def test_go_to_and_stop_save_edits_first(page, app_url):
    boot(page, app_url, [mk('w1', 'Camp')])
    open_marker(page, 'w1')
    page.fill('#mkName', 'Base')
    page.fill('#mkNote', 'by the oak')
    page.click('#mkGo')
    expect(sheet(page)).to_be_hidden()
    assert (wps(page)[0]['name'], wps(page)[0]['note']) == ('Base', 'by the oak')
    assert page.evaluate('FK.tac.target()') == {'type': 'marker', 'id': 'w1'}
    open_marker(page, 'w1')
    expect(page.locator('#mkGo')).to_have_text('Stop')
    page.click('#dlgMarker [data-kind="cache"]')
    page.click('#mkGo')
    expect(sheet(page)).to_be_hidden()
    assert wps(page)[0]['kind'] == 'cache'
    assert page.evaluate('FK.tac.target()') is None


def test_go_to_when_storage_is_full_still_targets(page, app_url):
    boot(page, app_url, full=True)
    open_new(page)
    page.fill('#mkName', 'Spot')
    toast_cleared(page)
    page.click('#mkGo')
    expect(sheet(page)).to_be_hidden()
    expect(page.locator('#toast')).to_have_text(FULL)
    m = page.evaluate('FK.tac.markers()')
    assert [x['name'] for x in m] == ['Spot']
    assert page.evaluate('FK.tac.target()') == {'type': 'marker', 'id': m[0]['id']}
    expect(pin(page, m[0]['id'])).to_have_class('mk-pin tgt')


def test_age_and_fade_refresh_each_minute_while_the_map_shows(page, app_url):
    boot(page, app_url, [mk('h1', 'Hostile 1', kind='hostile', t=NOW - 24 * HOUR + 30000),
                         mk('f1', 'Friend 1', kind='friend', t=NOW - 59 * 60000 - 10000, lat=HOME[0] + 0.002)])
    assert page.evaluate('FK.markers.timerOn()') is True
    expect(pin(page, 'h1')).to_have_class('mk-pin')
    page.click('#mList')
    row = page.locator('#lsList li', has_text='Friend 1')
    expect(row).to_contain_text('59 min ago')
    page.clock.fast_forward('01:00')
    expect(row).to_contain_text('1 h ago')
    expect(pin(page, 'h1')).to_have_class('mk-pin stale')
    page.click('#lsClose')
    expect(page.locator('#dlgList')).to_be_hidden()
    open_marker(page, 'f1')
    expect(page.locator('#mkAge')).to_contain_text('1 h ago')
    page.click('#mkCancel')
    expect(sheet(page)).to_be_hidden()
    # off the map the timer stops, and starts again on return
    page.evaluate("FK.route.go('/tactical/position')")
    page.wait_for_function("FK.view() === 'position'")
    assert page.evaluate('FK.markers.timerOn()') is False
    page.evaluate("FK.route.go('/tactical/map')")
    page.wait_for_function("FK.view() === 'map'")
    assert page.evaluate('FK.markers.timerOn()') is True


def test_confirmed_delete_makes_the_sheet_inert_at_once(page, app_url):
    boot(page, app_url, [mk('w1', 'Camp'), mk('w2', 'Spring', lat=HOME[0] + 0.003)])
    open_marker(page, 'w1')
    page.fill('#mkName', 'Edited')
    page.click('#mkDel')
    expect(page.locator('#dlgConfirm')).to_be_visible()
    page.evaluate("() => { document.querySelector('#cfOk').click(); document.querySelector('#mkSave').click(); document.querySelector('#mkGo').click(); document.querySelector('#mkDel').click(); }")
    expect(sheet(page)).to_be_hidden()
    expect(page.locator('#dlgConfirm')).to_be_hidden()
    assert [(w['id'], w['name']) for w in wps(page)] == [('w2', 'Spring')]
    assert page.evaluate('FK.tac.target()') is None
    page.wait_for_function('history.state.fkSheet === undefined')
    page.wait_for_timeout(600)
    assert page.evaluate("[...document.querySelectorAll('dialog')].filter(d => d.open).length") == 0
    assert page.evaluate('location.hash') == '#/tactical/map'
    page.go_back()
    assert page.url == 'about:blank'


def test_long_names_are_cut_short_on_the_map(page, app_url):
    long = 'Northern ridge observation post above the old logging road X'[:60]
    boot(page, app_url, [mk('w1', long)])
    b = pin(page, 'w1').locator('b')
    w = b.evaluate('e => [e.getBoundingClientRect().width, e.scrollWidth > e.clientWidth, getComputedStyle(e).textOverflow]')
    assert w[0] <= 125 and w[1] is True and w[2] == 'ellipsis'
    short = pin(page, 'w1').locator('b').evaluate('e => e.textContent')
    assert short == long   # the whole name is still there, only clipped on screen
    open_marker(page, 'w1')
    expect(page.locator('#mkName')).to_have_value(long)


def test_open_list_follows_new_fixes_and_keeps_scroll_and_chip(page, app_url):
    ms = [mk(f'c{i}', f'Camp {i}', lat=HOME[0] + i * 0.001, kind='camp', t=NOW - i * 60000) for i in range(12)]
    ms.append(mk('w', 'Well', kind='water', t=NOW))
    boot(page, app_url, ms)
    set_fix(page, HOME[0] - 0.01, HOME[1])
    page.click('#mList')
    expect(page.locator('#dlgList')).to_be_visible()
    page.click('#lsChips button[data-kind="camp"]')
    assert list_names(page)[0] == 'Camp 0'
    page.evaluate("document.querySelector('#dlgList .mk-body').scrollTop = 150")
    top = page.evaluate("document.querySelector('#dlgList .mk-body').scrollTop")
    assert top > 0
    set_fix(page, HOME[0] + 0.02, HOME[1])
    page.wait_for_function("document.querySelector('#lsList li .mk-name').textContent === 'Camp 11'")
    assert list_names(page) == [f'Camp {i}' for i in range(11, -1, -1)]
    expect(page.locator('#lsChips button[data-kind="camp"]')).to_have_attribute('aria-pressed', 'true')
    assert page.evaluate("document.querySelector('#dlgList .mk-body').scrollTop") == top
