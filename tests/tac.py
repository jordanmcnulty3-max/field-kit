"""Shared helpers for the tactical map tests."""
import json


def store(page, **kv):
    """Seed localStorage keys (as fk.<name>) before the page loads, only where nothing is stored yet."""
    page.add_init_script('(() => { if (!location.protocol.startsWith("http")) return;' + ''.join(
        f'if (localStorage.getItem({json.dumps("fk." + k)}) === null) localStorage.setItem({json.dumps("fk." + k)}, {json.dumps(json.dumps(v))});'
        for k, v in kv.items()) + '})()')


def open_map(page, app_url):
    """Load the Tactical map screen and wait until the app and the map are ready."""
    page.goto(app_url + '#/tactical/map')
    page.wait_for_function('window.FK && FK.sheet && document.querySelector("#map .leaflet-pane")')


def set_fix(page, lat, lon, acc=5, alt=None, spd=None):
    """Feed a GPS fix through the same path as a real one (stores it, renders, emits 'fix')."""
    page.evaluate('f => FK._test.fix(f)', {'lat': lat, 'lon': lon, 'acc': acc, 'alt': alt, 'spd': spd})


def heading(page, deg):
    """Feed a compass reading of this magnetic heading through the same path as a real one."""
    page.evaluate('d => FK._test.heading(d)', deg)


def center(page, lat, lon, z=15):
    """Move the map (it must exist already: use open_map first)."""
    page.evaluate('([a, b, z]) => FK.leafletMap().setView([a, b], z, { animate: false })', [lat, lon, z])


def open_tool(page, tool_id):
    """Open the map's Tools sheet and choose a row (Track recording, Save map for offline, ...)."""
    page.click('#mTools')
    page.click(f'#dlgTools [data-tool="{tool_id}"]')


def open_track(page):
    open_tool(page, 'track')
    page.wait_for_selector('#dlgTrack[open]')


def open_save(page):
    open_tool(page, 'save')
    page.wait_for_selector('#dlgSave[open]')


def gps_searching(page):
    """A GPS that is allowed but has no fix yet (the test browser's own geolocation is blocked)."""
    page.add_init_script('navigator.geolocation.watchPosition = () => 7; navigator.geolocation.clearWatch = () => {};')
