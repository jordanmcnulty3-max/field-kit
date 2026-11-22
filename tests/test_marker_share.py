"""Share on the marker sheet (comms Task 7): the Share switch, the shared-marker limits (bytes), the status lines, the delete
question, Send again, an incoming change or delete of the marker being edited, and the Radio sheet's re-send button.

Everything a person does in the sheet is a real tap or real key presses. Incoming waypoints are fed as decoded packets
(FK._test.mesh.feed) and what is sent is read back as real bytes from the fake radio (tests/radio.py)."""
import os
import re
import subprocess
import sys

import pytest
from playwright.sync_api import expect

from . import meshref, radio
from .tac import store, open_map, center
from .test_map import tiles_ok
from .test_mesh_state import BRAVO, CHARLIE, ME, PRIV, chan, feed_packet

mesh_pb2 = pytest.importorskip('meshtastic.protobuf.mesh_pb2')

HOME = (43.0, -76.0)
NOW = 1_800_000_000_000
MIN = 60_000
WPT = meshref.PORT['WAYPOINT']
ICON = {'point': 0x1F4CD, 'camp': 0x26FA, 'hostile': 0x2666}
FULL = 'Couldn’t save: phone storage for Field Kit is full. Back up, then delete old tracks or saved maps.'
TOO_LONG = 'Too long to share. Accents and emoji count extra. Shorten the name or note, or turn Share off.'   # final fix T6
SLOW_GO = "const g = history.go.bind(history); history.go = k => { setTimeout(() => g(k), 250); }; 0"   # a slow phone
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def net(wid, frm=BRAVO, by='Bravo', **kw):
    kw.setdefault('mine', frm in (ME, 0))
    return dict(dict(wid=wid, by=by, t=NOW - 10 * MIN, chBy='', chT=0, icon=0, expire=0, pending=False, rx=False, **{'from': frm}), **kw)


def mk(id_, name, n=None, lat=HOME[0], lon=HOME[1], kind='point', t=NOW - 10 * MIN, note=''):
    d = {'id': id_, 'name': name, 'lat': lat, 'lon': lon, 'alt': None, 't': t, 'kind': kind, 'note': note}
    if n is not None:
        d['net'] = n
    return d


def boot(page, app_url, markers=(), link=True, night=False, **kv):
    """about:blank first (stepping back too far would leave Field Kit), then the map. link: True connects the fake radio
    (private channel, can share); 'private' gives a private channel verdict with no link (nothing can be sent); False leaves
    the switch on and the radio off; 'off' leaves the Settings switch off."""
    page.clock.install(time=NOW / 1000)
    radio.install(page)
    page.goto('about:blank')
    tiles_ok(page)
    seed = {'wps': list(markers), 'advAck': True, 'night': night, 'mapFollow': False,
            'mapView': {'lat': HOME[0], 'lon': HOME[1], 'z': 15}, **kv}
    if link != 'off':
        seed['meshOn'] = True
        if link is not True:
            seed['meshMe'] = ME
    store(page, **seed)
    open_map(page, app_url)
    page.wait_for_function('window.FK && FK.share && FK.mesh')
    if link is True:
        assert page.evaluate('() => FK.mesh.connect()') is True
        page.wait_for_function('FK.mesh.canShare()')
    elif link == 'private':
        chan(page, psk=PRIV)
    return page


def sheet(page):
    return page.locator('#dlgMarker')


def pin(page, id_):
    return page.locator(f'.mk-pin[data-id="{id_}"]')


def open_marker(page, id_):
    pin(page, id_).click()
    expect(sheet(page)).to_be_visible()


def open_new(page):
    page.click('#mMark')
    expect(sheet(page)).to_be_visible()


def retype(page, sel, text):
    """Select everything in the field and type text with real key presses."""
    page.click(sel)
    page.keyboard.press('Control+A')
    page.keyboard.press('Backspace')
    if text:
        page.keyboard.type(text)


def markers(page):
    return page.evaluate('() => FK.tac.markers()')


def one(page, id_):
    return next((m for m in markers(page) if m['id'] == id_), None)


def stored(page):
    return page.evaluate("() => JSON.parse(localStorage.getItem('fk.wps') || '[]')")


def sent_wps(page):
    out = []
    for b in radio.sent(page):
        tr = mesh_pb2.ToRadio.FromString(b)
        if tr.HasField('packet') and tr.packet.decoded.portnum == WPT:
            out.append(mesh_pb2.Waypoint.FromString(tr.packet.decoded.payload))
    return out


def tombs(page):
    return [t['wid'] for t in page.evaluate("() => JSON.parse(localStorage.getItem('fk.meshTombs') || '[]')")]


def incoming(page, frm=BRAVO, **wp):
    feed_packet(page, frm, WPT, meshref.waypoint_bytes(**wp))
    page.evaluate('() => FK._test.share.flush()')


def toast(page):
    return page.locator('#toast')


def clear_toast(page):
    page.evaluate("document.querySelector('#toast').textContent = ''")


def history_clean(page):
    """No sheet entry left; Back leaves Field Kit (the page before it was about:blank)."""
    page.wait_for_function('!history.state.fkSheet && FK.sheet.top() === null')
    page.wait_for_timeout(600)
    assert page.evaluate("[...document.querySelectorAll('dialog')].filter(d => d.open).length") == 0
    assert page.evaluate('location.hash') == '#/tactical/map'
    assert page.evaluate('FK.route.index() === history.state.fkIdx')
    page.go_back()
    assert page.url == 'about:blank'


# ---------------------------------------------------------------- the Share row

def test_share_row_absent_when_switch_off(page, app_url):
    boot(page, app_url, [mk('w1', 'Camp'), mk('s1', 'Rally', net(40), lat=HOME[0] + 0.002)], link='off')
    for open_it in (lambda: open_new(page), lambda: open_marker(page, 's1')):
        open_it()
        expect(page.locator('#mkShare')).to_be_hidden()
        expect(page.locator('#mkShareLine')).to_be_hidden()
        expect(page.locator('#mkResend')).to_be_hidden()
        expect(page.locator('#mkNameLeft')).to_be_hidden()
        txt = sheet(page).inner_text()
        assert 'Share' not in txt and 'Shared' not in txt and 'Send' not in txt
        page.click('#mkCancel')
        expect(sheet(page)).to_be_hidden()
    # saving a shared marker with the switch off keeps it shared and sends nothing
    open_marker(page, 's1')
    retype(page, '#mkNote', 'by the gate')
    page.click('#mkSave')
    expect(sheet(page)).to_be_hidden()
    assert one(page, 's1')['net']['wid'] == 40 and one(page, 's1')['note'] == 'by the gate'
    assert page.evaluate('() => FakeRadio.sent.length') == 0


def test_share_row_shows_when_a_radio_can_share_and_a_new_marker_starts_off(page, app_url):
    boot(page, app_url)
    open_new(page)
    expect(page.locator('#mkShare')).to_be_visible()
    expect(page.locator('#mkShare')).not_to_be_checked()
    expect(page.locator('#mkShare')).to_have_attribute('role', 'switch')
    expect(page.locator('#mkResend')).to_be_hidden()
    expect(page.locator('#mkShareLine')).to_be_hidden()
    # Save with Share off: a private marker, nothing sent
    page.click('#mkSave')
    expect(sheet(page)).to_be_hidden()
    assert 'net' not in markers(page)[0] and sent_wps(page) == []


def test_the_share_switch_is_on_screen_when_a_new_marker_opens(page, app_url):
    boot(page, app_url)
    open_new(page)
    sw = page.locator('#dlgMarker .mk-share .opt').bounding_box()
    save = page.locator('#mkSave').bounding_box()
    assert sw['y'] >= 0 and sw['y'] + sw['height'] <= save['y'], (sw, save)
    assert page.evaluate("document.querySelector('#dlgMarker .mk-body').scrollTop") == 0


def test_a_refused_save_brings_the_over_limit_field_into_view(page, app_url):
    boot(page, app_url)
    open_new(page)
    page.click('#mkShare')
    retype(page, '#mkName', 'n' * 35)
    page.evaluate("document.querySelector('#dlgMarker .mk-body').scrollTop = 9999")   # scrolled down to the note
    page.click('#mkSave')
    expect(page.locator('#mkNotice')).to_be_visible()
    for sel in ('#mkNameLeft', '#mkNotice'):
        expect(page.locator(sel)).to_be_in_viewport()
    expect(page.locator('#mkNameLeft')).to_have_text('6 over the limit')
    # an over-long note (name fine): the note's counter comes into view
    retype(page, '#mkName', 'Short')
    page.evaluate("document.querySelector('#dlgMarker .mk-body').scrollTop = 0")
    retype(page, '#mkNote', 'x' * 120)
    page.evaluate("document.querySelector('#dlgMarker .mk-body').scrollTop = 0")
    page.click('#mkSave')
    expect(page.locator('#mkLeft')).to_have_text('21 over the limit')
    expect(page.locator('#mkLeft')).to_be_in_viewport()
    assert markers(page) == []


def test_share_row_needs_a_link_or_a_shared_marker(page, app_url):
    boot(page, app_url, [mk('w1', 'Camp'), mk('s1', 'Rally', net(41), lat=HOME[0] + 0.002)], link='private')
    open_new(page)
    expect(page.locator('#mkShare')).to_be_hidden()       # switch on, but nothing can be sent
    page.click('#mkCancel')
    expect(sheet(page)).to_be_hidden()
    open_marker(page, 'w1')
    expect(page.locator('#mkShare')).to_be_hidden()
    page.click('#mkCancel')
    expect(sheet(page)).to_be_hidden()
    open_marker(page, 's1')                                 # already shared: the switch shows, on
    expect(page.locator('#mkShare')).to_be_visible()
    expect(page.locator('#mkShare')).to_be_checked()
    expect(page.locator('#mkResend')).to_be_hidden()        # Send again needs a radio that can send


def test_share_on_and_save_sends_it_and_says_shared(page, app_url):
    boot(page, app_url)
    open_new(page)
    retype(page, '#mkName', 'Ridge camp')
    page.click('#dlgMarker [data-kind="camp"]')
    page.click('#mkShare')
    expect(page.locator('#mkShare')).to_be_checked()
    page.click('#mkSave')
    expect(sheet(page)).to_be_hidden()
    expect(toast(page)).to_have_text('Shared')
    m = markers(page)[0]
    assert m['net']['mine'] is True and m['net']['pending'] is False
    w = sent_wps(page)
    assert [(x.id, x.name, x.icon) for x in w] == [(m['net']['wid'], 'Ridge camp', ICON['camp'])]
    history_clean(page)


def test_share_saved_with_the_radio_gone_is_not_sent_yet(page, app_url):
    boot(page, app_url)
    open_new(page)
    page.click('#mkShare')
    page.evaluate('() => FK._test.mesh.link("lost", "")')    # the link drops while the sheet is open
    expect(page.locator('#mkShare')).to_be_visible()          # the switch the user turned on stays where it is
    clear_toast(page)
    page.click('#mkSave')
    expect(sheet(page)).to_be_hidden()
    m = markers(page)[0]
    assert m['net']['pending'] is True and sent_wps(page) == []
    page.wait_for_timeout(300)
    assert toast(page).inner_text() != 'Shared'
    open_marker(page, m['id'])
    expect(page.locator('#mkShareLine')).to_contain_text('Not sent yet: no radio connected')


def test_share_with_storage_full_leaves_the_marker_private(page, app_url):
    boot(page, app_url, [mk('w1', 'Camp')])
    page.evaluate("""() => { const set = Storage.prototype.setItem;
      Storage.prototype.setItem = function (k, v) { if (k === 'fk.wps') throw new DOMException('full', 'QuotaExceededError'); return set.call(this, k, v); }; }""")
    open_marker(page, 'w1')
    page.click('#mkShare')
    clear_toast(page)
    page.click('#mkSave')
    expect(sheet(page)).to_be_hidden()
    expect(toast(page)).to_have_text(FULL)
    assert 'net' not in one(page, 'w1') and sent_wps(page) == []
    open_marker(page, 'w1')
    expect(page.locator('#mkShare')).not_to_be_checked()


# ---------------------------------------------------------------- limits: bytes, not characters

def test_bytes_not_characters_at_the_limit(page, app_url):
    boot(page, app_url)
    open_new(page)
    page.click('#mkShare')
    retype(page, '#mkName', 'Café ⛺ north ridge lookout')     # 25 characters, 29 bytes
    expect(page.locator('#mkNameLeft')).to_have_text('Room for 0 more')
    page.keyboard.type('s')                                    # one byte more
    expect(page.locator('#mkNameLeft')).to_have_text('1 over the limit')
    page.click('#mkSave')
    expect(sheet(page)).to_be_visible()
    expect(page.locator('#mkNotice')).to_have_text(TOO_LONG)
    expect(page.locator('#mkNotice')).to_be_visible()
    assert markers(page) == [] and sent_wps(page) == []
    page.click('#mkName')
    page.keyboard.press('End')
    page.keyboard.press('Backspace')
    expect(page.locator('#mkNameLeft')).to_have_text('Room for 0 more')
    expect(page.locator('#mkNotice')).to_be_hidden()
    page.click('#mkSave')
    expect(sheet(page)).to_be_hidden()
    assert [x.name for x in sent_wps(page)] == ['Café ⛺ north ridge lookout']   # whole, never cut
    assert markers(page)[0]['name'] == 'Café ⛺ north ridge lookout'


def test_note_room_follows_the_kind(page, app_url):
    boot(page, app_url)
    open_new(page)
    page.click('#mkShare')
    retype(page, '#mkNote', 'n' * 90)
    expect(page.locator('#mkLeft')).to_have_text('Room for 9 more')
    page.click('#dlgMarker [data-kind="hostile"]')             # the seen time takes 19 bytes of an affiliation note
    expect(page.locator('#mkLeft')).to_have_text('10 over the limit')
    page.click('#mkSave')
    expect(sheet(page)).to_be_visible()
    expect(page.locator('#mkNotice')).to_have_text(TOO_LONG)
    assert markers(page) == []
    page.click('#dlgMarker [data-kind="camp"]')
    expect(page.locator('#mkLeft')).to_have_text('Room for 9 more')
    expect(page.locator('#mkNotice')).to_be_hidden()
    page.click('#mkSave')
    expect(sheet(page)).to_be_hidden()
    assert sent_wps(page)[0].description == 'n' * 90


def test_turning_share_on_for_a_long_marker_asks_to_shorten_and_off_saves_it_whole(page, app_url):
    long = 'Northern ridge observation post'   # 31 bytes
    boot(page, app_url, [mk('w1', long, note='x' * 120)])
    open_marker(page, 'w1')
    expect(page.locator('#mkNameLeft')).to_be_hidden()        # Share off: the counters are as they always were
    expect(page.locator('#mkLeft')).to_be_hidden()
    page.click('#mkShare')
    expect(page.locator('#mkNameLeft')).to_have_text('2 over the limit')
    expect(page.locator('#mkLeft')).to_have_text('21 over the limit')
    expect(page.locator('#mkNotice')).to_be_hidden()             # the message comes with a refused Save
    for button in ('#mkSave', '#mkGo', '#mkMove'):             # nothing that saves goes through
        page.click(button)
        expect(sheet(page)).to_be_visible()
        expect(page.locator('#mkNotice')).to_have_text(TOO_LONG)
    assert 'net' not in one(page, 'w1') and sent_wps(page) == []
    assert page.evaluate('FK.tac.target()') is None and page.evaluate('FK.mapTools.mode()') is None
    page.click('#mkShare')                                     # Share off: the long name is fine again
    expect(page.locator('#mkNotice')).to_be_hidden()
    expect(page.locator('#mkNameLeft')).to_be_hidden()
    page.click('#mkSave')
    expect(sheet(page)).to_be_hidden()
    assert one(page, 'w1')['name'] == long and 'net' not in one(page, 'w1')


def test_a_paste_over_the_limit_is_shown_not_hidden(page, app_url):
    """The name box keeps its 60-character maxlength; a pasted 100 characters is cut to 60 by the browser, which is still far
    over 29 bytes, so the counter and the message show it. Nothing is saved or sent."""
    boot(page, app_url)
    page.context.grant_permissions(['clipboard-read', 'clipboard-write'])
    open_new(page)
    page.click('#mkShare')
    page.evaluate("() => navigator.clipboard.writeText('p'.repeat(100))")
    page.click('#mkName')
    page.keyboard.press('Control+A')
    page.keyboard.press('Control+V')
    expect(page.locator('#mkName')).to_have_value('p' * 60)
    expect(page.locator('#mkNameLeft')).to_have_text('31 over the limit')
    page.click('#mkSave')
    expect(page.locator('#mkNotice')).to_have_text(TOO_LONG)
    expect(sheet(page)).to_be_visible()
    assert markers(page) == [] and sent_wps(page) == []


# ---------------------------------------------------------------- status lines

def test_status_shared_by_and_changed_by(page, app_url):
    boot(page, app_url, [mk('s1', 'Rally', net(42, chBy='Charlie', chT=NOW - 3 * MIN)),
                         mk('s2', 'Cache', net(43, frm=ME, by='Alpha'), lat=HOME[0] + 0.002)])
    open_marker(page, 's1')
    expect(page.locator('#mkShareLine')).to_have_text('Shared by Bravo\nChanged by Charlie, 3 min ago')
    page.click('#mkCancel')
    expect(sheet(page)).to_be_hidden()
    open_marker(page, 's2')
    expect(page.locator('#mkShareLine')).to_have_text('Shared by you')


def test_names_from_other_radios_are_text(page, app_url):
    evil = '<img src=x onerror=window.x=1>'
    boot(page, app_url, [mk('s1', 'Rally', net(44, by=evil[:40], chBy=evil[:40], chT=NOW - MIN))])
    open_marker(page, 's1')
    expect(page.locator('#mkShareLine')).to_contain_text('Shared by ' + evil[:40])
    assert page.locator('#dlgMarker img').count() == 0 and page.evaluate('window.x') is None


def test_an_affiliation_marker_timed_on_receipt_says_received(page, app_url):
    boot(page, app_url, [mk('h1', 'Watcher', net(45, rx=True), kind='hostile', t=NOW - 5 * MIN),
                         mk('h2', 'Seen', net(46), kind='hostile', t=NOW - 5 * MIN, lat=HOME[0] + 0.002)])
    open_marker(page, 'h1')
    expect(page.locator('#mkAge')).to_have_text(re.compile(r'^Received \d{1,2}:\d{2}, 5 min ago$'))
    page.click('#mkCancel')
    expect(sheet(page)).to_be_hidden()
    open_marker(page, 'h2')
    expect(page.locator('#mkAge')).to_have_text(re.compile(r'^Marked \d{1,2}:\d{2}, 5 min ago$'))


# ---------------------------------------------------------------- saving, moving and stopping a shared marker

def test_save_on_a_shared_marker_sends_the_change(page, app_url):
    boot(page, app_url, [mk('s1', 'Rally', net(47, chBy='Charlie', chT=NOW - MIN))])
    open_marker(page, 's1')
    retype(page, '#mkName', 'Rally north')
    page.click('#mkSave')
    expect(sheet(page)).to_be_hidden()
    assert [(x.id, x.name) for x in sent_wps(page)] == [(47, 'Rally north')]
    assert one(page, 's1')['net']['chBy'] == ''                # this phone's own change is not "changed by" anyone


def test_save_unchanged_sends_nothing(page, app_url):
    boot(page, app_url, [mk('s1', 'Rally', net(48))])
    open_marker(page, 's1')
    page.click('#mkSave')
    expect(sheet(page)).to_be_hidden()
    page.wait_for_timeout(300)
    assert sent_wps(page) == []


def test_move_on_a_shared_marker_sends_the_new_place(page, app_url):
    boot(page, app_url, [mk('s1', 'Rally', net(49))])
    open_marker(page, 's1')
    page.click('#mkMove')
    page.wait_for_selector('#tbPlace:visible')
    center(page, 43.004, -76.0)
    page.click('#tbPlace')
    page.wait_for_function("FK.mapTools.mode() === null")
    page.wait_for_function('() => FakeRadio.sent.length > 0')
    w, m = sent_wps(page), one(page, 's1')
    assert abs(m['lat'] - 43.0) > 0.002                          # it did move
    assert [x.id for x in w] == [49] and abs(w[0].latitude_i / 1e7 - m['lat']) < 1e-6


def test_share_off_on_a_teammates_marker_stops_sharing(page, app_url):
    boot(page, app_url, [mk('s1', 'Rally', net(50))])
    open_marker(page, 's1')
    expect(page.locator('#mkShareHint')).to_be_hidden()
    page.click('#mkShare')
    expect(page.locator('#mkShare')).not_to_be_checked()
    expect(page.locator('#mkShareHint')).to_have_text('Your copy becomes private. Teammates keep theirs.')
    page.click('#mkSave')
    expect(sheet(page)).to_be_hidden()
    assert 'net' not in one(page, 's1') and 50 in tombs(page)
    page.wait_for_timeout(300)
    assert sent_wps(page) == []


def test_the_guard_counts_the_share_switch(page, app_url):
    boot(page, app_url, [mk('w1', 'Camp')])
    open_marker(page, 'w1')
    page.click('#mkShare')
    page.go_back()
    expect(page.locator('#cfTitle')).to_have_text('Discard this marker?')
    page.click('#cfCancel')                                    # Keep editing
    expect(page.locator('#dlgConfirm')).to_be_hidden()
    expect(sheet(page)).to_be_visible()
    page.click('#mkShare')                                     # back as it was: nothing to lose
    page.go_back()
    expect(sheet(page)).to_be_hidden()
    assert page.locator('#dlgConfirm[open]').count() == 0
    assert 'net' not in one(page, 'w1')


# ---------------------------------------------------------------- the delete question

def ask_delete(page):
    page.click('#mkDel')
    expect(page.locator('#dlgMkDel')).to_be_visible()
    expect(page.locator('#mdTitle')).to_have_text('Delete this marker?')


def test_delete_on_a_shared_marker_asks_and_cancel_keeps_it(page, app_url):
    boot(page, app_url, [mk('s1', 'Rally', net(51))])
    page.evaluate(SLOW_GO)
    open_marker(page, 's1')
    ask_delete(page)
    expect(page.locator('#mdAll')).to_have_text('Delete for everyone')
    expect(page.locator('#mdHere')).to_have_text('Delete on this phone only')
    expect(page.locator('#mdCancel')).to_have_text('Cancel')
    assert page.evaluate('document.activeElement.id') == 'mdTitle'   # a stray Enter takes no choice
    page.click('#mdCancel')
    expect(page.locator('#dlgMkDel')).to_be_hidden()
    expect(sheet(page)).to_be_visible()
    assert one(page, 's1') is not None
    for how in ('back', 'Escape'):                              # any other way out is Cancel too
        page.wait_for_timeout(400)
        ask_delete(page)
        if how == 'back':
            page.go_back()
        else:
            page.keyboard.press('Escape')
        expect(page.locator('#dlgMkDel')).to_be_hidden()
        expect(sheet(page)).to_be_visible()
    assert one(page, 's1') is not None and sent_wps(page) == []
    page.wait_for_timeout(400)
    page.click('#mkCancel')
    expect(sheet(page)).to_be_hidden()
    history_clean(page)


def test_delete_for_everyone_sends_the_delete(page, app_url):
    boot(page, app_url, [mk('s1', 'Rally', net(52)), mk('w2', 'Spring', lat=HOME[0] + 0.003)])
    page.evaluate(SLOW_GO)
    open_marker(page, 's1')
    ask_delete(page)
    page.click('#mdAll')
    expect(page.locator('#dlgMkDel')).to_be_hidden()
    expect(sheet(page)).to_be_hidden()
    expect(toast(page)).to_have_text('Deleted for everyone')
    assert [m['id'] for m in markers(page)] == ['w2'] and 52 in tombs(page)
    w = sent_wps(page)
    assert [(x.id, x.expire, x.name) for x in w] == [(52, 1, 'Rally')]
    history_clean(page)


def test_delete_on_this_phone_only_sends_nothing(page, app_url):
    boot(page, app_url, [mk('s1', 'Rally', net(53)), mk('w2', 'Spring', lat=HOME[0] + 0.003)])
    page.evaluate(SLOW_GO)
    open_marker(page, 's1')
    clear_toast(page)
    ask_delete(page)
    page.click('#mdHere')
    expect(sheet(page)).to_be_hidden()
    assert [m['id'] for m in markers(page)] == ['w2'] and 53 in tombs(page)
    page.wait_for_timeout(300)
    assert sent_wps(page) == [] and toast(page).inner_text() == ''
    history_clean(page)


def test_delete_for_everyone_is_offered_only_when_the_radio_can_send(page, app_url):
    boot(page, app_url, [mk('s1', 'Rally', net(54))], link='private')
    open_marker(page, 's1')
    ask_delete(page)
    expect(page.locator('#mdAll')).to_be_hidden()
    expect(page.locator('#mdHere')).to_be_visible()
    page.click('#mdHere')
    expect(sheet(page)).to_be_hidden()
    assert markers(page) == [] and 54 in tombs(page)


def test_delete_for_everyone_when_the_radio_drops_says_teammates_still_have_it(page, app_url):
    boot(page, app_url, [mk('s1', 'Rally', net(55))])
    open_marker(page, 's1')
    ask_delete(page)
    page.evaluate('() => FK._test.mesh.link("lost", "")')      # gone while the question is open
    page.click('#mdAll')
    expect(sheet(page)).to_be_hidden()
    expect(toast(page)).to_have_text('Deleted on this phone. Couldn’t reach the radio, so teammates still have it.')
    assert markers(page) == [] and 55 in tombs(page) and sent_wps(page) == []


def test_delete_on_a_private_marker_is_unchanged(page, app_url):
    boot(page, app_url, [mk('w1', 'Camp')])
    open_marker(page, 'w1')
    page.click('#mkDel')
    expect(page.locator('#dlgConfirm')).to_be_visible()
    expect(page.locator('#cfText')).to_have_text('Delete marker Camp? This can’t be undone.')
    assert page.locator('#dlgMkDel[open]').count() == 0
    page.click('#cfOk')
    expect(sheet(page)).to_be_hidden()
    assert markers(page) == [] and tombs(page) == []


# ---------------------------------------------------------------- Send again

def test_send_again(page, app_url):
    boot(page, app_url, [mk('s1', 'Rally', net(56))])
    open_marker(page, 's1')
    expect(page.locator('#mkResend')).to_have_text('Send again')
    page.click('#mkResend')
    expect(page.locator('#mkResend')).to_have_text('Sent')     # on the button: a toast would sit behind the sheet (T3)
    expect(sheet(page)).to_be_visible()                        # the sheet stays open
    assert [x.id for x in sent_wps(page)] == [56]
    page.evaluate('() => FK._test.mesh.link("lost", "")')
    expect(page.locator('#mkResend')).to_be_hidden()


# ---------------------------------------------------------------- incoming changes to the open marker

def test_an_incoming_change_refills_a_sheet_with_nothing_typed(page, app_url):
    boot(page, app_url, [mk('s1', 'Rally', net(57))])
    open_marker(page, 's1')
    incoming(page, CHARLIE, id=57, lat=43.0, lon=-76.0, name='Rally south', description='moved', icon=ICON['camp'])
    expect(page.locator('#mkName')).to_have_value('Rally south')
    expect(page.locator('#mkNote')).to_have_value('moved')
    expect(page.locator('#dlgMarker [data-kind="camp"]')).to_have_attribute('aria-pressed', 'true')
    expect(page.locator('#mkShareLine')).to_contain_text('Changed by Charlie')
    page.go_back()                                             # the refilled sheet has nothing unsaved
    expect(sheet(page)).to_be_hidden()
    assert page.locator('#dlgConfirm[open]').count() == 0


def test_an_incoming_change_keeps_what_was_typed_and_save_wins(page, app_url):
    boot(page, app_url, [mk('s1', 'Rally', net(58))])
    open_marker(page, 's1')
    retype(page, '#mkName', 'Rally mine')
    incoming(page, CHARLIE, id=58, lat=43.0, lon=-76.0, name='Rally theirs', icon=ICON['point'])
    expect(page.locator('#mkNotice')).to_have_text(
        'This marker was changed by Charlie while you were editing. Saving keeps your version.')
    expect(page.locator('#mkName')).to_have_value('Rally mine')
    assert one(page, 's1')['name'] == 'Rally theirs'
    page.click('#mkSave')
    expect(sheet(page)).to_be_hidden()
    assert one(page, 's1')['name'] == 'Rally mine'
    assert [(x.id, x.name) for x in sent_wps(page)] == [(58, 'Rally mine')]


DRAFT = 'Bravo deleted this marker for everyone. Save keeps what you typed as a private marker of your own.'


def test_an_incoming_delete_closes_the_sheet_with_nothing_typed(page, app_url):
    boot(page, app_url, [mk('s1', 'Rally', net(59))])
    page.evaluate(SLOW_GO)
    open_marker(page, 's1')
    incoming(page, BRAVO, id=59, lat=43.0, lon=-76.0, name='Rally', expire=1, icon=ICON['point'])
    expect(sheet(page)).to_be_hidden()
    expect(toast(page)).to_have_text('Bravo deleted this marker')
    assert page.locator('#dlgConfirm[open]').count() == 0      # no "Discard?" for a marker that is gone
    assert markers(page) == []
    history_clean(page)


def deleted_while_typing(page, app_url, wid):
    boot(page, app_url, [mk('s1', 'Rally', net(wid), lat=43.002, note='north')])
    page.evaluate(SLOW_GO)
    open_marker(page, 's1')
    retype(page, '#mkName', 'Rally kept')
    page.click('#dlgMarker [data-kind="water"]')
    retype(page, '#mkNote', 'my typing')
    incoming(page, BRAVO, id=wid, lat=43.002, lon=-76.0, name='Rally', expire=1, icon=ICON['point'])
    expect(page.locator('#mkNotice')).to_have_text(DRAFT)
    expect(sheet(page)).to_be_visible()
    expect(page.locator('#mkTitle')).to_have_text('New marker')
    expect(page.locator('#mkName')).to_have_value('Rally kept')
    expect(page.locator('#mkNote')).to_have_value('my typing')
    expect(page.locator('#dlgMarker [data-kind="water"]')).to_have_attribute('aria-pressed', 'true')
    for hidden in ('#mkDel', '#mkMove', '#mkResend'):
        expect(page.locator(hidden)).to_be_hidden()
    expect(page.locator('#mkShare')).not_to_be_checked()
    assert markers(page) == [] and wid in tombs(page)


def test_a_teammates_delete_while_typing_keeps_the_typing_as_a_new_private_draft(page, app_url):
    deleted_while_typing(page, app_url, 66)
    page.click('#mkSave')
    expect(sheet(page)).to_be_hidden()
    ms = markers(page)
    assert len(ms) == 1 and ms[0]['id'] != 's1' and 'net' not in ms[0]
    assert (ms[0]['name'], ms[0]['note'], ms[0]['kind']) == ('Rally kept', 'my typing', 'water')
    assert abs(ms[0]['lat'] - 43.002) < 1e-9
    page.wait_for_timeout(300)
    assert sent_wps(page) == [] and 66 in tombs(page)
    history_clean(page)


def test_a_teammates_delete_while_typing_then_cancel_asks_before_discarding(page, app_url):
    deleted_while_typing(page, app_url, 67)
    page.click('#mkCancel')
    expect(page.locator('#cfTitle')).to_have_text('Discard this marker?')
    page.click('#cfOk')
    expect(page.locator('#dlgConfirm')).to_be_hidden()
    expect(sheet(page)).to_be_hidden()
    assert markers(page) == [] and sent_wps(page) == []
    history_clean(page)


def test_a_teammates_delete_while_typing_then_back_asks_before_discarding(page, app_url):
    deleted_while_typing(page, app_url, 68)
    page.go_back()
    expect(page.locator('#cfTitle')).to_have_text('Discard this marker?')
    page.click('#cfCancel')                                    # Keep editing: the draft is still there
    expect(page.locator('#dlgConfirm')).to_be_hidden()
    expect(page.locator('#mkNote')).to_have_value('my typing')
    page.wait_for_timeout(400)
    page.go_back()
    expect(page.locator('#cfTitle')).to_have_text('Discard this marker?')
    page.click('#cfOk')
    expect(sheet(page)).to_be_hidden()
    assert markers(page) == []
    history_clean(page)


def test_an_incoming_delete_while_discard_is_asked_keeps_the_draft_under_it(page, app_url):
    boot(page, app_url, [mk('s1', 'Rally', net(64))])
    page.evaluate(SLOW_GO)
    open_marker(page, 's1')
    retype(page, '#mkNote', 'typing')
    page.go_back()                                             # Back with typing: "Discard this marker?"
    expect(page.locator('#cfTitle')).to_have_text('Discard this marker?')
    incoming(page, BRAVO, id=64, lat=43.0, lon=-76.0, name='Rally', expire=1, icon=ICON['point'])
    expect(page.locator('#dlgConfirm')).to_be_visible()        # the question stays; the sheet under it is now a draft
    expect(page.locator('#mkTitle')).to_have_text('New marker')
    page.click('#cfOk')                                        # Discard
    expect(page.locator('#dlgConfirm')).to_be_hidden()
    expect(sheet(page)).to_be_hidden()
    assert markers(page) == [] and sent_wps(page) == []
    history_clean(page)


def test_an_incoming_delete_while_the_delete_question_is_open_closes_both(page, app_url):
    boot(page, app_url, [mk('s2', 'Spring', net(65))])
    page.evaluate(SLOW_GO)
    open_marker(page, 's2')
    ask_delete(page)
    incoming(page, BRAVO, id=65, lat=43.0, lon=-76.0, name='Spring', expire=1, icon=ICON['point'])
    expect(page.locator('#dlgMkDel')).to_be_hidden()
    expect(sheet(page)).to_be_hidden()
    expect(toast(page)).to_have_text('Bravo deleted this marker')
    assert sent_wps(page) == []
    history_clean(page)


def test_an_incoming_delete_of_mine_while_typing_keeps_the_typing_and_makes_it_private(page, app_url):
    boot(page, app_url, [mk('s1', 'Rally', net(69, frm=ME, by='Alpha'), note='north side')])
    open_marker(page, 's1')
    retype(page, '#mkNote', 'south side')
    incoming(page, BRAVO, id=69, lat=43.0, lon=-76.0, name='Rally', expire=1, icon=ICON['point'])
    expect(page.locator('#mkNotice')).to_have_text('Bravo deleted this marker for everyone. Your copy is now private.')
    expect(page.locator('#mkNote')).to_have_value('south side')
    expect(page.locator('#mkShare')).not_to_be_checked()
    expect(page.locator('#mkTitle')).to_have_text('Marker')
    page.click('#mkSave')
    expect(sheet(page)).to_be_hidden()
    m = one(page, 's1')
    assert m['note'] == 'Deleted by Bravo. south side' and 'net' not in m   # T8: the line is kept in front of what was typed
    page.wait_for_timeout(300)
    assert sent_wps(page) == []


def test_an_incoming_delete_of_mine_refills_it_as_private(page, app_url):
    boot(page, app_url, [mk('s1', 'Rally', net(60, frm=ME, by='Alpha'), note='north side')])
    open_marker(page, 's1')
    expect(page.locator('#mkShare')).to_be_checked()
    incoming(page, BRAVO, id=60, lat=43.0, lon=-76.0, name='Rally', expire=1, icon=ICON['point'])
    expect(page.locator('#mkNote')).to_have_value('Deleted by Bravo. north side')
    expect(page.locator('#mkShare')).not_to_be_checked()
    expect(page.locator('#mkResend')).to_be_hidden()
    expect(sheet(page)).to_be_visible()
    page.click('#mkSave')
    expect(sheet(page)).to_be_hidden()
    assert 'net' not in one(page, 's1')
    page.wait_for_timeout(300)
    assert sent_wps(page) == []


# ---------------------------------------------------------------- the Radio sheet

def test_radio_sheet_send_all_mine_again(page, app_url):
    boot(page, app_url, [mk('a', 'One', net(61, frm=ME)), mk('b', 'Two', net(62, frm=ME), lat=HOME[0] + 0.002),
                         mk('c', 'Theirs', net(63), lat=HOME[0] + 0.004)])
    page.click('#mRadio')
    page.wait_for_selector('#dlgRadio[open]')
    expect(page.locator('#rdResend')).to_be_visible()
    page.click('#rdResend')
    expect(page.locator('#rdResend')).to_have_text('Sending 2 markers…')   # on the button (T3)
    page.wait_for_function('() => FakeRadio.sent.length >= 1')
    page.clock.run_for(3500)
    page.wait_for_function('() => FakeRadio.sent.filter(Boolean).length >= 2')
    page.wait_for_timeout(200)
    assert sorted(x.id for x in sent_wps(page)) == [61, 62]
    page.evaluate('() => FK._test.mesh.link("lost", "")')
    expect(page.locator('#rdResend')).to_be_hidden()


def test_radio_sheet_resend_hidden_without_markers_of_mine(page, app_url):
    boot(page, app_url, [mk('c', 'Theirs', net(63)), mk('w', 'Private', lat=HOME[0] + 0.002)])
    page.click('#mRadio')
    page.wait_for_selector('#dlgRadio[open]')
    expect(page.locator('#rdStatus')).to_be_visible()
    expect(page.locator('#rdResend')).to_be_hidden()
    expect(page.locator('#rdDropped')).to_be_hidden()


def test_radio_sheet_says_when_older_markers_were_dropped(page, app_url):
    many = [mk(f't{i}', f'T{i}', net(1000 + i, t=NOW - (600 - i) * MIN), lat=HOME[0] + (i % 20) * 0.001,
               lon=HOME[1] + (i // 20) * 0.001) for i in range(501)]
    boot(page, app_url, many)
    assert page.evaluate('FK.share.dropped()') == 1
    page.click('#mRadio')
    page.wait_for_selector('#dlgRadio[open]')
    expect(page.locator('#rdDropped')).to_have_text('Some older markers from teammates were dropped: this phone holds 500.')


# ---------------------------------------------------------------- the existing marker tests, run as they are

def test_existing_marker_tests_unchanged():
    if os.environ.get('FK_NESTED'):
        pytest.skip('already inside a nested run')
    env = dict(os.environ, FK_NESTED='1')
    r = subprocess.run([sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider', '-p', 'no:xdist',
                        os.path.join(ROOT, 'tests', 'test_markers.py')], cwd=ROOT, env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-2000:]
