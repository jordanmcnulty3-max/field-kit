"""The Radio button on the Tactical map and the Radio sheet, with real taps, against the scripted fake radio."""
import pytest
from playwright.sync_api import expect

from . import meshref, radio
from .tac import open_map, set_fix, store
from .test_iphone import SHEET_BASIS
from .test_mesh_state import chan, feed, node

R = meshref.ref_from_radio
PRIV = bytes(range(1, 17))
EVIL = '<img src=x onerror=1>'
NOT_CONNECTED = ['You need a Meshtastic radio that is already set up in the Meshtastic app.',
                 'Close the Meshtastic app first: a radio talks to one app at a time.']
FAILED = 'Couldn’t connect. If the Meshtastic app is open, close it and try again.'
UNSUPPORTED = ('This phone’s browser can’t reach a radio. The Meshtastic app will still share your position and markers '
               'with the group.')
PUBLIC = ('This radio is on a public channel, so Field Kit is not sending or showing anything. Set up a private channel in '
          'the Meshtastic app and share it with your group.')
POS_OFF = 'This channel is set to send no positions, so teammates won’t appear.'
POS_APPROX = 'This channel sends approximate positions, so teammates may show in the wrong place.'


def boot_map(page, app_url, on=True, **kw):
    radio.install(page, **kw)
    if on:
        store(page, meshOn=True)
    open_map(page, app_url)
    page.wait_for_function('window.FK && FK.mesh')


def open_sheet(page):
    page.click('#mRadio')
    page.wait_for_selector('#dlgRadio[open]')


def state(page):
    return page.evaluate('() => FK.mesh.status().state')


def connect(page):
    """Open the sheet and tap Connect a radio; wait for the link to be on."""
    open_sheet(page)
    page.click('#rdConnect')
    page.wait_for_function("FK.mesh.status().state === 'on'")
    page.wait_for_function("document.querySelector('#rdDisconnect') && !document.querySelector('#rdDisconnect').hidden")


def sheet_text(page):
    return page.inner_text('#dlgRadio')


def label(page):
    return page.get_attribute('#mRadio', 'aria-label')


def test_no_button_when_switch_off(page, app_url):
    boot_map(page, app_url, on=False)
    assert page.locator('#mRadio').count() == 0 and page.is_hidden('#mRadio')
    assert page.evaluate('() => FakeRadio.choosers') == 0


def test_button_appears_and_goes_with_the_switch_without_reload(page, app_url):
    boot_map(page, app_url, on=False)
    page.click('#menuBtn')
    page.click('#meshOn')   # the switch row in the menu
    page.keyboard.press('Escape')
    expect(page.locator('#mRadio')).to_be_visible()
    assert page.evaluate('() => FK.sheet.top()') is None
    page.click('#menuBtn')
    page.click('#meshOn')
    page.keyboard.press('Escape')
    expect(page.locator('#mRadio')).to_be_hidden()


def test_button_label_follows_state(page, app_url):
    boot_map(page, app_url)
    expect(page.locator('#mRadio')).to_be_visible()
    assert label(page) == 'Radio: off'
    icons = {'off': page.inner_html('#mRadio')}
    radio.hold(page, 'chooser')
    open_sheet(page)
    page.click('#rdConnect')
    page.wait_for_function("document.querySelector('#mRadio').getAttribute('aria-label') === 'Radio: connecting'")
    icons['connecting'] = page.inner_html('#mRadio')
    radio.release(page, 'chooser')
    page.wait_for_function("document.querySelector('#mRadio').getAttribute('aria-label') === 'Radio: connected'")
    icons['on'] = page.inner_html('#mRadio')
    radio.drop(page)
    page.wait_for_function("document.querySelector('#mRadio').getAttribute('aria-label') === 'Radio: connection lost'")
    icons['lost'] = page.inner_html('#mRadio')
    assert len(set(icons.values())) == 4, 'each state has its own icon shape'
    box = page.locator('#mRadio').bounding_box()
    assert box['width'] >= 44 and box['height'] >= 44


def test_sheet_not_connected_copy(page, app_url):
    boot_map(page, app_url)
    open_sheet(page)
    txt = sheet_text(page)
    assert page.inner_text('#rdTitle') == 'Radio'
    for line in NOT_CONNECTED:
        assert line in txt
    assert page.inner_text('#rdConnect') == 'Connect a radio'
    assert page.is_hidden('#rdDisconnect') and page.is_hidden('#rdResend')
    assert 'Teammates' not in txt and 'Channel:' not in txt
    assert FAILED not in txt


def test_connect_tap_opens_chooser_once(page, app_url):
    boot_map(page, app_url)
    open_sheet(page)
    page.dblclick('#rdConnect')
    page.wait_for_function("FK.mesh.status().state === 'on'")
    page.wait_for_timeout(300)
    assert page.evaluate('() => FakeRadio.choosers') == 1
    assert state(page) == 'on'
    assert page.inner_text('#rdStatus') == 'Connected to "Meshtastic_a1b2"'


def test_failed_connection_message_and_state_off(page, app_url):
    boot_map(page, app_url)
    radio.refuse(page, 'gatt')
    open_sheet(page)
    page.click('#rdConnect')
    page.wait_for_function("FK.mesh.status().reason === 'failed'")
    assert state(page) == 'off'
    expect(page.locator('#dlgRadio')).to_contain_text(FAILED)
    assert page.is_visible('#rdConnect') and page.is_enabled('#rdConnect')
    assert label(page) == 'Radio: off'
    radio.refuse(page, None)
    page.click('#rdConnect')
    page.wait_for_function("FK.mesh.status().state === 'on'")
    expect(page.locator('#dlgRadio')).not_to_contain_text(FAILED)


def test_cancel_shows_no_error(page, app_url):
    boot_map(page, app_url)
    radio.refuse(page, 'cancel')
    open_sheet(page)
    page.click('#rdConnect')
    page.wait_for_function("FK.mesh.status().reason === 'cancelled'")
    page.wait_for_timeout(100)
    assert state(page) == 'off'
    txt = sheet_text(page)
    assert FAILED not in txt and 'Couldn' not in txt and 'cancel' not in txt.lower()
    assert page.is_visible('#rdConnect') and page.is_enabled('#rdConnect')
    for line in NOT_CONNECTED:
        assert line in txt


def test_unsupported_copy_and_no_connect_button(page, app_url):
    page.add_init_script("Object.defineProperty(navigator, 'bluetooth', { value: undefined, configurable: true })")
    store(page, meshOn=True)
    open_map(page, app_url)
    page.wait_for_function('window.FK && FK.mesh')
    assert page.evaluate('() => FK.mesh.supported()') is False
    open_sheet(page)
    assert UNSUPPORTED in sheet_text(page)
    assert page.is_hidden('#rdConnect')
    for line in NOT_CONNECTED:
        assert line not in sheet_text(page)
    assert label(page) == 'Radio: off'


def test_connected_sheet(page, app_url):
    boot_map(page, app_url)
    connect(page)
    txt = sheet_text(page)
    assert page.inner_text('#rdStatus') == 'Connected to "Meshtastic_a1b2"'
    assert 'Channel: private' in txt
    assert PUBLIC not in txt and POS_OFF not in txt and POS_APPROX not in txt
    assert page.inner_text('#rdDisconnect') == 'Disconnect'
    assert page.is_hidden('#rdConnect')
    for line in NOT_CONNECTED:
        assert line not in txt
    page.wait_for_timeout(450)   # a tap this soon after Connect is taken for the second tap of a double tap
    page.click('#rdDisconnect')
    page.wait_for_function("FK.mesh.status().state === 'off'")
    expect(page.locator('#rdConnect')).to_be_visible()
    assert 'Channel:' not in sheet_text(page) and 'Teammates' not in sheet_text(page)


def test_public_channel_warning(page, app_url):
    script = [R(my_node_num=radio.MY_NUM), R(channel=dict(index=0, role=1, name='', psk=b'\x01', precision=32)),
              R(node=dict(num=0x0A0B0C02, long='Bravo', short='BRV', pos=(43.01, -76.01, 0, 1766000100), last_heard=1766000100))]
    boot_map(page, app_url, script=script)
    connect(page)
    txt = sheet_text(page)
    assert PUBLIC in txt
    assert 'Teammates' not in txt and 'Bravo' not in txt and 'Channel: private' not in txt
    assert POS_OFF not in txt and POS_APPROX not in txt


def test_position_warnings(page, app_url):
    boot_map(page, app_url)
    connect(page)
    chan(page, psk=PRIV, precision=0)
    page.wait_for_function("document.querySelector('#dlgRadio').innerText.includes('send no positions')")
    assert POS_OFF in sheet_text(page) and POS_APPROX not in sheet_text(page)
    chan(page, psk=PRIV, precision=13)
    page.wait_for_function("document.querySelector('#dlgRadio').innerText.includes('approximate positions')")
    assert POS_APPROX in sheet_text(page) and POS_OFF not in sheet_text(page)
    chan(page, psk=PRIV, precision=32)
    page.wait_for_function("!document.querySelector('#dlgRadio').innerText.includes('approximate positions')")
    assert POS_OFF not in sheet_text(page)
    # a stale verdict is not shown once the link is lost
    chan(page, psk=PRIV, precision=0)
    page.wait_for_function("document.querySelector('#dlgRadio').innerText.includes('send no positions')")
    radio.drop(page)
    page.wait_for_function("FK.mesh.status().state === 'lost'")
    page.wait_for_function("!document.querySelector('#dlgRadio').innerText.includes('send no positions')")
    assert 'Channel:' not in sheet_text(page) and 'Connection lost' in sheet_text(page)


def rows(page):
    return page.eval_on_selector_all('#rdTeam > li', 'els => els.map(e => e.innerText.replace(/\\s+/g, " ").trim())')


def test_teammate_rows_sorted_by_distance_then_no_position(page, app_url):
    boot_map(page, app_url)
    set_fix(page, 43.0, -76.0)
    connect(page)
    now = page.evaluate('() => Math.floor(Date.now() / 1000)')
    feed(page, node(0x0A0B0C05, 'Echo', 'ECH', dict(lat=43.001, lon=-76.0, time=now - 300), 0))
    feed(page, node(0x0A0B0C06, 'Zulu', 'ZUL', None, 0))
    page.wait_for_function("document.querySelectorAll('#rdTeam > li').length === 4")
    assert page.inner_text('#rdTeamH') == 'Teammates (4)'
    r = rows(page)
    assert [x.split(' · ')[0] for x in r] == ['Echo', 'Bravo', 'Charlie', 'Zulu']
    assert r[0].startswith('Echo · ') and ' m ' in r[0] and r[0].endswith('5 min ago'), r[0]
    assert 'km' in r[1] or ' mi' in r[1], r[1]
    assert r[2].endswith('no position yet') and r[3] == 'Zulu · no position yet', r
    assert 'Teammates (4)' in sheet_text(page)


def test_age_is_never_wrong(page, app_url):
    boot_map(page, app_url)
    set_fix(page, 43.0, -76.0)
    connect(page)
    feed(page, node(0x0A0B0C07, 'Yankee', 'YNK', dict(lat=43.002, lon=-76.0, time=0), 0))
    page.wait_for_function("document.querySelectorAll('#rdTeam > li').length === 3")
    soon = page.evaluate('() => Math.floor(Date.now() / 1000) + 3600')
    feed(page, node(0x0A0B0C08, 'Xray', 'XRY', dict(lat=43.003, lon=-76.0, time=soon), 0))
    page.wait_for_function("document.querySelectorAll('#rdTeam > li').length === 4")
    by = {x.split(' · ')[0]: x for x in rows(page)}
    assert by['Yankee'].endswith('age unknown'), by['Yankee']
    assert 'ago' not in by['Xray'] and by['Xray'].endswith('age unknown'), by['Xray']


def test_names_are_escaped(page, app_url):
    radio.install(page, name=EVIL)
    store(page, meshOn=True)
    open_map(page, app_url)
    page.wait_for_function('window.FK && FK.mesh')
    connect(page)
    feed(page, node(0x0A0B0C09, EVIL, 'EV', dict(lat=43.001, lon=-76.0, time=1766000000), 0))
    page.wait_for_function("document.querySelectorAll('#rdTeam > li').length === 3")
    assert page.evaluate("() => document.querySelectorAll('#dlgRadio img').length") == 0
    assert page.evaluate("() => window.__x") is None
    txt = sheet_text(page)
    assert txt.count(EVIL) >= 2     # as the radio's name and as a teammate, as text
    assert f'Connected to "{EVIL}"' in txt


def test_bursts_of_team_events_redraw_once_per_frame(page, app_url):
    boot_map(page, app_url)
    connect(page)
    n = page.evaluate("""async () => {
      const ul = document.querySelector('#rdTeam');
      let mut = 0;
      const mo = new MutationObserver(l => { mut += l.length; }); mo.observe(ul, { childList: true });
      for (let i = 0; i < 100; i++) FK._test.mesh.feed({ type: 'nodeInfo', num: 0x0B000000 + i, longName: 'N' + i, shortName: 'N', position: null, lastHeard: 0, channel: 0 });
      await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
      mo.disconnect();
      return mut;
    }""")
    assert n <= 2, n    # one rebuild, not 100
    assert page.inner_text('#rdTeamH') == 'Teammates (100)'


def test_sheet_closed_gets_no_redraw_and_reopens_current(page, app_url):
    boot_map(page, app_url)
    connect(page)
    page.click('#rdClose')
    page.wait_for_function("!document.querySelector('#dlgRadio').open")
    feed(page, node(0x0A0B0C0A, 'Late', 'LT', None, 0))
    page.wait_for_timeout(100)
    assert 'Late' not in page.evaluate("() => document.querySelector('#rdTeam').innerText")
    open_sheet(page)
    assert any(x.startswith('Late') for x in rows(page))


def test_back_closes_the_sheet(page, app_url):
    boot_map(page, app_url)
    open_sheet(page)
    page.go_back()
    page.wait_for_function("!document.querySelector('#dlgRadio').open")
    assert page.evaluate('() => location.hash') == '#/tactical/map'


def test_switch_off_closes_the_sheet(page, app_url):
    boot_map(page, app_url)
    connect(page)
    page.evaluate('() => FK.mesh.setEnabled(false)')
    page.wait_for_function("!document.querySelector('#dlgRadio').open")
    expect(page.locator('#mRadio')).to_be_hidden()


def test_sheet_fits_iphone_guard(page, app_url):
    boot_map(page, app_url)
    connect(page)
    assert page.evaluate(SHEET_BASIS, '#dlgRadio') == []
    box = page.evaluate("""() => { const r = document.querySelector('#dlgRadio').getBoundingClientRect();
      const b = document.querySelector('#rdDisconnect').getBoundingClientRect();
      return { top: r.top, bottom: r.bottom, btnBottom: b.bottom, h: innerHeight, sw: document.documentElement.scrollWidth, w: innerWidth }; }""")
    assert box['bottom'] <= box['h'] + 1 and box['btnBottom'] <= box['h'] and box['sw'] <= box['w']
    ids = page.evaluate("[...document.querySelectorAll('dialog.mk-sheet')].map(d => d.id)")
    assert 'dlgRadio' in ids


def test_map_button_column_with_the_switch_on_and_off(page, app_url):
    ids = "[...document.querySelectorAll('.mapctl button')].map(b => b.id)"
    boot_map(page, app_url)
    page.wait_for_selector('#mRadio')
    assert page.evaluate(ids) == ['mLayers', 'mLocate', 'mTools', 'mList', 'mRadio']
    page.evaluate('() => FK.mesh.setEnabled(false)')
    page.wait_for_function("!document.querySelector('#mRadio')")
    assert page.evaluate(ids) == ['mLayers', 'mLocate', 'mTools', 'mList']
