"""Comms release 1, final fix round: what the three final reviews found in the marker sheet, the map, the Markers list,
the Radio button and sheet, the teammate sheet and the Settings menu (items T1-T15, C3, C4, S2, S3, S5, the rare false
toast, P8 and P11 on screen). Real taps and real key presses; a slowed history.go wherever a sheet opens or closes."""
import json

import pytest
from playwright.sync_api import expect

from . import meshref, radio
from .tac import store, open_map
from .test_marker_share import (BRAVO, CHARLIE, HOME, ICON, ME, MIN, NOW, SLOW_GO, WPT, boot, clear_toast, incoming, markers,
                                mk, net, one, open_marker, open_new, pin, retype, sent_wps, sheet, toast)
from .test_mesh_state import feed, node

mesh_pb2 = pytest.importorskip('meshtastic.protobuf.mesh_pb2')

TOO_LONG = 'Too long to share. Accents and emoji count extra. Shorten the name or note, or turn Share off.'
NOT_SENT = 'Saved. Not sent yet: it goes out when the radio connects.'
SEEN_HINT = 'A shared sighting carries the time it was seen, which uses part of the note.'
PUBLIC = ('This radio’s main channel is public, so Field Kit is not sending or showing anything. In the Meshtastic app, make '
          'your private channel the main (primary) one, share it with your group, then connect again.')
POS_OFF = 'This channel is set to send no positions: yours isn’t shared and teammates’ won’t arrive.'
REGION = 'This radio has no region set, so it can’t transmit. Set the region in the Meshtastic app.'
TXOFF = 'This radio’s transmitter is switched off in its settings.'


def mine(wid, **kw):
    return net(wid, frm=ME, by='Alpha', **kw)


def open_radio(page):
    page.click('#mRadio')
    page.wait_for_selector('#dlgRadio[open]')


def label(page):
    return page.get_attribute('#mRadio', 'aria-label')


# ---------------------------------------------------------------- T1 Send again

def test_send_again_hides_while_typing_and_says_to_save(page, app_url):
    boot(page, app_url, [mk('s1', 'Rally', mine(70), note='gate')])
    open_marker(page, 's1')
    expect(page.locator('#mkResend')).to_be_visible()
    expect(page.locator('#mkSendHint')).to_be_hidden()
    retype(page, '#mkNote', 'gate, north side')
    expect(page.locator('#mkResend')).to_be_hidden()
    expect(page.locator('#mkSendHint')).to_have_text('Save your changes to send them.')
    retype(page, '#mkNote', 'gate')                        # back to what is saved: nothing unsaved
    expect(page.locator('#mkResend')).to_be_visible()
    expect(page.locator('#mkSendHint')).to_be_hidden()
    page.click('#dlgMarker [data-kind="camp"]')            # a kind change is typing too
    expect(page.locator('#mkResend')).to_be_hidden()
    expect(page.locator('#mkSendHint')).to_be_visible()


def test_send_again_hidden_once_share_is_unticked(page, app_url):
    boot(page, app_url, [mk('s1', 'Rally', mine(71))])
    open_marker(page, 's1')
    expect(page.locator('#mkResend')).to_be_visible()
    page.click('#mkShare')
    expect(page.locator('#mkResend')).to_be_hidden()
    expect(page.locator('#mkSendHint')).to_be_hidden()      # the row's own hint says what Save will do
    expect(page.locator('#mkShareHint')).to_have_text('Your copy becomes private. Teammates keep theirs.')


def test_send_again_hidden_for_a_marker_over_the_limits(page, app_url):
    boot(page, app_url, [mk('t1', 'A teammate’s very long marker name here', net(72))])
    open_marker(page, 't1')
    expect(page.locator('#mkShare')).to_be_checked()
    expect(page.locator('#mkResend')).to_be_hidden()


def test_send_again_says_sent_on_the_button_not_in_a_toast(page, app_url):
    boot(page, app_url, [mk('s1', 'Rally', mine(73))])
    open_marker(page, 's1')
    clear_toast(page)
    page.click('#mkResend')
    expect(page.locator('#mkResend')).to_have_text('Sent')
    assert [x.id for x in sent_wps(page)] == [73]
    page.wait_for_timeout(200)
    assert toast(page).inner_text() == ''                    # no toast behind an open sheet


# ---------------------------------------------------------------- T2 badges, T7 the sender's icon

def badge(scope):
    return scope.locator('.mk-net')


def test_shared_and_not_sent_badges_on_pins_and_list_rows(page, app_url):
    boot(page, app_url, [mk('s', 'Shared one', mine(80)), mk('p', 'Waiting', mine(81, pending=True), lat=HOME[0] + 0.002),
                         mk('w', 'Private', lat=HOME[0] + 0.004)], link='private')   # nothing goes out: 'p' stays pending
    expect(badge(pin(page, 's'))).to_have_attribute('aria-label', 'Shared with teammates')
    expect(badge(pin(page, 'p'))).to_have_attribute('aria-label', 'Shared, not sent yet')
    expect(badge(pin(page, 'w'))).to_have_count(0)
    assert pin(page, 's').get_attribute('class') == 'mk-pin' and pin(page, 'w').get_attribute('class') == 'mk-pin'
    for i in ('s', 'w'):
        box = pin(page, i).bounding_box()
        assert (round(box['width']), round(box['height'])) == (30, 30)
        assert page.evaluate("id => getComputedStyle(document.querySelector(`.mk-pin[data-id='${id}'] .mk-net`) || document.body).pointerEvents", i) in ('none', 'auto')
    b = badge(pin(page, 's')).bounding_box()
    assert b['width'] <= 14 and b['height'] <= 14
    assert page.evaluate("getComputedStyle(document.querySelector('.mk-pin[data-id=s] .mk-net')).pointerEvents") == 'none'
    page.click('#mList')
    page.wait_for_selector('#dlgList[open]')
    rows = {r.get_attribute('data-id'): r for r in page.locator('#lsList button[data-id]').all()}
    expect(badge(rows['s'])).to_have_attribute('aria-label', 'Shared with teammates')
    expect(badge(rows['p'])).to_have_attribute('aria-label', 'Shared, not sent yet')
    expect(badge(rows['w'])).to_have_count(0)


def test_no_badges_with_the_switch_off(page, app_url):
    boot(page, app_url, [mk('s', 'Shared one', mine(82)), mk('p', 'Waiting', mine(83, pending=True), lat=HOME[0] + 0.002)],
         link='off')
    expect(pin(page, 's')).to_be_visible()
    assert page.locator('.mk-net').count() == 0
    page.click('#mList')
    page.wait_for_selector('#dlgList[open]')
    assert page.locator('.mk-net').count() == 0


def test_a_teammates_own_emoji_shows_on_its_point(page, app_url):
    boot(page, app_url)
    incoming(page, BRAVO, id=90, lat=43.0, lon=-76.0, name='Deer stand', icon=0x1F98C)
    m = markers(page)[0]
    assert m['kind'] == 'point' and m['net']['icon'] == 0x1F98C
    expect(pin(page, m['id']).locator('i .mk-emoji')).to_have_text('🦌')
    page.click('#mList')
    page.wait_for_selector('#dlgList[open]')
    expect(page.locator(f'#lsList button[data-id="{m["id"]}"] .mk-emoji')).to_have_text('🦌')
    page.evaluate(SLOW_GO)
    page.click(f'#lsList button[data-id="{m["id"]}"]')
    expect(sheet(page)).to_be_visible()
    expect(page.locator('#mkEmoji')).to_have_text('Sender’s icon: 🦌')
    page.click('#dlgMarker [data-kind="camp"]')
    expect(page.locator('#mkEmoji')).to_be_hidden()           # a Camp is sent as a Camp: the emoji goes


# ---------------------------------------------------------------- T3, C4 what a save says

def test_saving_a_change_to_a_shared_marker_says_sent_to_teammates(page, app_url):
    boot(page, app_url, [mk('s1', 'Rally', mine(74))])
    open_marker(page, 's1')
    retype(page, '#mkNote', 'by the gate')
    page.click('#mkSave')
    expect(sheet(page)).to_be_hidden()
    expect(toast(page)).to_have_text('Sent to teammates')


def test_a_save_that_cannot_go_out_says_not_sent_yet(page, app_url):
    boot(page, app_url, [mk('s1', 'Rally', mine(75), lat=HOME[0] + 0.002)])
    page.evaluate(SLOW_GO)
    # a new share, the link dropped while the sheet was open
    open_new(page)
    page.click('#mkShare')
    radio.drop(page)
    page.wait_for_function('FK.mesh.status().state === "lost"')
    page.click('#mkSave')
    expect(sheet(page)).to_be_hidden()
    expect(toast(page)).to_have_text(NOT_SENT)
    clear_toast(page)
    # a change to a shared marker
    open_marker(page, 's1')
    retype(page, '#mkNote', 'by the gate')
    page.click('#mkSave')
    expect(sheet(page)).to_be_hidden()
    expect(toast(page)).to_have_text(NOT_SENT)
    clear_toast(page)
    # Move
    open_marker(page, 's1')
    page.click('#mkMove')
    expect(sheet(page)).to_be_hidden()
    page.wait_for_selector('#toolBar:not([hidden])')
    page.click('#tbPlace')
    expect(toast(page)).to_have_text(NOT_SENT)


def test_send_all_again_reports_on_its_button(page, app_url):
    boot(page, app_url, [mk('a', 'One', mine(61)), mk('b', 'Two', mine(62), lat=HOME[0] + 0.002),
                         mk('c', 'Theirs', net(63), lat=HOME[0] + 0.004)])
    open_radio(page)
    clear_toast(page)
    page.click('#rdResend')
    expect(page.locator('#rdResend')).to_have_text('Sending 2 markers…')
    expect(page.locator('#rdResend')).to_be_disabled()
    page.clock.run_for(3500)
    expect(page.locator('#rdResend')).to_have_text('Sent 2 markers')
    expect(page.locator('#rdResend')).to_be_enabled()
    assert sorted(x.id for x in sent_wps(page)) == [61, 62]
    assert toast(page).inner_text() == ''


def test_send_all_again_with_nothing_that_fits(page, app_url):
    boot(page, app_url, [mk('a', 'A name far too long to be shared at all', mine(64))])
    open_radio(page)
    page.click('#rdResend')
    expect(page.locator('#rdResend')).to_have_text('Nothing to send')
    assert sent_wps(page) == []


# ---------------------------------------------------------------- T5, T6 notices and counters

def in_actions(page, sel):
    return page.evaluate("s => !!document.querySelector(s).closest('.mk-act')", sel)


def test_refused_save_message_sits_above_the_buttons(page, app_url):
    boot(page, app_url)
    open_new(page)
    page.click('#mkShare')
    retype(page, '#mkName', 'Café ⛺ north ridge lookout')    # 25 characters, 29 bytes
    expect(page.locator('#mkNameLeft')).to_have_text('Room for 0 more')
    page.keyboard.type('s')
    expect(page.locator('#mkNameLeft')).to_have_text('1 over the limit')
    retype(page, '#mkName', 'Short')
    retype(page, '#mkNote', 'x' * 120)
    page.click('#mkSave')
    expect(page.locator('#mkNotice')).to_have_text(TOO_LONG)
    assert in_actions(page, '#mkNotice')
    expect(page.locator('#mkNotice')).to_be_in_viewport()
    expect(page.locator('#mkLeft')).to_have_text('21 over the limit')
    expect(page.locator('#mkLeft')).to_be_in_viewport()          # the over-limit field still comes into view
    assert page.locator('#mkShareBox .mk-msg').count() == 0     # the Share row keeps switch, hint and status line only
    retype(page, '#mkNote', 'x' * 99)
    expect(page.locator('#mkNotice')).to_be_hidden()
    expect(page.locator('#mkLeft')).to_have_text('Room for 0 more')


def test_an_affiliation_kind_says_why_the_note_is_shorter(page, app_url):
    boot(page, app_url)
    open_new(page)
    expect(page.locator('#mkSeenHint')).to_be_hidden()
    page.click('#mkShare')
    expect(page.locator('#mkSeenHint')).to_be_hidden()
    page.click('#dlgMarker [data-kind="hostile"]')
    expect(page.locator('#mkSeenHint')).to_have_text(SEEN_HINT)
    expect(page.locator('#mkLeft')).to_have_text('Room for 80 more')
    page.click('#mkShare')
    expect(page.locator('#mkSeenHint')).to_be_hidden()


def test_a_teammates_change_while_typing_shows_above_the_buttons(page, app_url):
    boot(page, app_url, [mk('s1', 'Rally', net(76))])
    open_marker(page, 's1')
    retype(page, '#mkNote', 'my words ' * 8)
    page.evaluate("document.querySelector('#dlgMarker .mk-body').scrollTop = 9999")
    incoming(page, CHARLIE, id=76, lat=43.0, lon=-76.0, name='Rally theirs', icon=ICON['point'])
    expect(page.locator('#mkNotice')).to_have_text('This marker was changed by Charlie while you were editing. Saving keeps your version.')
    assert in_actions(page, '#mkNotice')
    expect(page.locator('#mkNotice')).to_be_in_viewport()
    expect(page.locator('#mkShareLine')).not_to_contain_text('while you were editing')


def test_a_teammates_delete_while_typing_shows_above_the_buttons(page, app_url):
    boot(page, app_url, [mk('s1', 'Rally', net(77))])
    open_marker(page, 's1')
    retype(page, '#mkNote', 'my words')
    incoming(page, BRAVO, id=77, lat=43.0, lon=-76.0, name='Rally', expire=1, icon=ICON['point'])
    expect(page.locator('#mkNotice')).to_have_text('Bravo deleted this marker for everyone. Save keeps what you typed as a private marker of your own.')
    expect(page.locator('#mkNotice')).to_be_in_viewport()


# ---------------------------------------------------------------- T8 "Deleted by" kept

def test_deleted_by_line_survives_a_save_of_typed_text(page, app_url):
    boot(page, app_url, [mk('s1', 'Rally', mine(78), note='north side')])
    open_marker(page, 's1')
    retype(page, '#mkNote', 'meet here at dawn')
    incoming(page, BRAVO, id=78, lat=43.0, lon=-76.0, name='Rally', expire=1, icon=ICON['point'])
    expect(page.locator('#mkNotice')).to_have_text('Bravo deleted this marker for everyone. Your copy is now private.')
    page.click('#mkSave')
    expect(sheet(page)).to_be_hidden()
    m = one(page, 's1')
    assert 'net' not in m and m['note'] == 'Deleted by Bravo. meet here at dawn'


# ---------------------------------------------------------------- T13 expiry

def test_a_shared_marker_with_an_expiry_says_when(page, app_url):
    exp = (NOW + 5 * 3600 * 1000) // 1000
    boot(page, app_url, [mk('t1', 'Temp rally', net(79, expire=exp))])
    open_marker(page, 't1')
    want = page.evaluate("""s => { const d = new Date(s * 1000), M = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
      const p = n => String(n).padStart(2, '0'); return `Expires ${d.getDate()} ${M[d.getMonth()]} ${p(d.getHours())}:${p(d.getMinutes())}`; }""", exp)
    expect(page.locator('#mkShareLine')).to_contain_text(want)


# ---------------------------------------------------------------- S2 the open marker is spared

def test_a_teammates_marker_expiring_while_typing_keeps_the_typing(page, app_url):
    exp = (NOW + 30_000) // 1000
    boot(page, app_url, [mk('t1', 'Temp', net(84, expire=exp))])
    open_marker(page, 't1')
    retype(page, '#mkNote', 'still typing')
    page.clock.run_for(65_000)                                # the minute sweep passes the expiry
    assert one(page, 't1') is not None
    page.click('#mkSave')
    expect(sheet(page)).to_be_hidden()
    page.wait_for_timeout(100)
    assert 'no longer exists' not in toast(page).inner_text()


# ---------------------------------------------------------------- S3 Go to stopped by a teammate's delete

def test_a_teammates_delete_of_the_go_to_target_says_so(page, app_url):
    boot(page, app_url, [mk('t1', 'Deer stand', net(85))], target='t1')
    assert page.evaluate('FK.tac.target()') == {'type': 'marker', 'id': 't1'}
    incoming(page, BRAVO, id=85, lat=43.0, lon=-76.0, name='Deer stand', expire=1, icon=ICON['point'])
    assert page.evaluate('FK.tac.target()') is None
    expect(toast(page)).to_have_text('Bravo deleted Deer stand, so Go to stopped.')


# ---------------------------------------------------------------- the rare false toast

def test_delete_for_everyone_after_a_teammates_delete_says_nothing_false(page, app_url):
    boot(page, app_url, [mk('s1', 'Rally', mine(86))])
    page.evaluate(SLOW_GO)
    open_marker(page, 's1')
    page.click('#mkDel')
    expect(page.locator('#dlgMkDel')).to_be_visible()
    incoming(page, BRAVO, id=86, lat=43.0, lon=-76.0, name='Rally', expire=1, icon=ICON['point'])
    clear_toast(page)
    page.click('#mdAll')
    expect(sheet(page)).to_be_hidden()
    page.wait_for_timeout(400)
    assert 'teammates still have it' not in toast(page).inner_text()


# ---------------------------------------------------------------- S5 restore

def test_a_restored_backup_does_not_send_old_pending_markers(page, app_url, tmp_path):
    from .test_migration import pick, restore_now
    boot(page, app_url, link=False)
    data = {'fk.wps': json.dumps([mk('p1', 'Old', mine(87, pending=True))]), 'fk.meshOn': 'true'}
    pick(page, tmp_path, {'app': 'Field Kit', 'version': '7.10', 'saved': '2027-01-01T00:00:00Z', 'data': data})
    restore_now(page)
    page.wait_for_function('window.FK && FK.tac && FK.share')
    assert one(page, 'p1')['net']['pending'] is False
    assert page.evaluate('() => FK.mesh.connect()') is True
    page.clock.run_for(4000)
    page.wait_for_timeout(200)
    assert sent_wps(page) == []


# ---------------------------------------------------------------- the Radio button (T4) and sheet (T10, T11, T15, C3, P11)

def team_script(**kw):
    now = NOW // 1000
    nodes = [meshref.ref_from_radio(node=dict(num=BRAVO, long='Bravo', pos=(43.01, -76.01, 0, now - 5 * 60), last_heard=now - 5 * 60)),
             meshref.ref_from_radio(node=dict(num=CHARLIE, long='Charlie', pos=None, last_heard=now - 60))]
    return radio.realistic_script(nodes=nodes, **kw)


def boot_team(page, app_url, **kw):
    """The page clock at NOW, a radio with Bravo (a position 5 min old) and Charlie (no position), connected."""
    page.clock.install(time=NOW / 1000)
    radio.install(page, script=team_script(**kw))
    page.goto('about:blank')
    store(page, meshOn=True, advAck=True, mapFollow=False, mapView={'lat': HOME[0], 'lon': HOME[1], 'z': 15})
    open_map(page, app_url)
    page.wait_for_function('window.FK && FK.mesh')
    assert page.evaluate('() => FK.mesh.connect()') is True


def test_radio_button_warns_whenever_it_cannot_share(page, app_url):
    boot_team(page, app_url)
    page.wait_for_function("document.querySelector('#mRadio').getAttribute('aria-label') === 'Radio: connected'")
    assert 'warn' not in (page.get_attribute('#mRadio', 'class') or '')
    feed(page, dict(type='channel', index=0, role='primary', name='', psk=[], positionPrecision=32))
    page.wait_for_function("document.querySelector('#mRadio').classList.contains('warn')")
    assert label(page) == 'Radio: connected, not sharing (public channel)'
    page.evaluate("() => FK._test.mesh.feed({ type: 'channel', index: 0, role: 'primary', name: '', psk: Uint8Array.from({ length: 16 }, (_, i) => i + 1), positionPrecision: 32 })")
    feed(page, dict(type='config', lora=dict(region=0, hopLimit=3, txEnabled=True)))
    page.wait_for_function("document.querySelector('#mRadio').getAttribute('aria-label') === 'Radio: connected, can’t transmit'")
    assert 'warn' in page.get_attribute('#mRadio', 'class')
    feed(page, dict(type='config', lora=dict(region=1, hopLimit=3, txEnabled=True)))
    page.wait_for_function("document.querySelector('#mRadio').getAttribute('aria-label') === 'Radio: connected'")
    assert 'warn' not in page.get_attribute('#mRadio', 'class')
    radio.drop(page)
    page.wait_for_function("document.querySelector('#mRadio').getAttribute('aria-label') === 'Radio: connection lost'")
    assert 'warn' in page.get_attribute('#mRadio', 'class')
    box = page.locator('#mRadio').bounding_box()
    assert (round(box['width']), round(box['height'])) == (48, 48)


def test_radio_sheet_wording_for_public_positions_off_and_cannot_transmit(page, app_url):
    boot_team(page, app_url, region=0)
    open_radio(page)
    expect(page.locator('#rdProblem')).to_have_text(REGION)
    feed(page, dict(type='config', lora=dict(region=1, hopLimit=3, txEnabled=False)))
    expect(page.locator('#rdProblem')).to_have_text(TXOFF)
    feed(page, dict(type='config', lora=dict(region=1, hopLimit=3, txEnabled=True)))
    expect(page.locator('#rdProblem')).to_be_hidden()
    page.evaluate("() => FK._test.mesh.feed({ type: 'channel', index: 0, role: 'primary', name: '', psk: Uint8Array.from({ length: 16 }, (_, i) => i + 1), positionPrecision: 0 })")
    expect(page.locator('#rdPos')).to_have_text(POS_OFF)
    feed(page, dict(type='channel', index=0, role='primary', name='', psk=[], positionPrecision=32))
    expect(page.locator('#rdWarn')).to_have_text(PUBLIC)


def test_disconnect_is_quiet_and_lost_offers_only_connect_again(page, app_url):
    boot_team(page, app_url)
    open_radio(page)
    expect(page.locator('#rdDisconnect')).to_be_visible()
    assert 'ghost' in page.get_attribute('#rdDisconnect', 'class')
    radio.drop(page)
    expect(page.locator('#rdConnect')).to_have_text('Connect again')
    expect(page.locator('#rdDisconnect')).to_be_hidden()
    assert 'ghost' not in page.get_attribute('#rdConnect', 'class')


def test_radio_sheet_ages_move_on_while_it_is_open(page, app_url):
    boot_team(page, app_url)
    open_radio(page)
    expect(page.locator('#rdTeam')).to_contain_text('5 min ago')
    page.clock.run_for(61_000)
    expect(page.locator('#rdTeam')).to_contain_text('6 min ago')


def test_lost_link_lists_last_known_teammates_and_a_row_opens_the_teammate(page, app_url):
    boot_team(page, app_url)
    radio.drop(page)
    page.wait_for_function('FK.mesh.status().state === "lost"')
    page.evaluate(SLOW_GO)
    open_radio(page)
    expect(page.locator('#rdTeamH')).to_have_text('Teammates, last known (2)')
    expect(page.locator('#rdTeam')).to_contain_text('Bravo')
    expect(page.locator('#rdTeam')).to_contain_text('Charlie')
    assert page.locator('#rdTeam button').count() == 1         # Charlie has no position: not a button
    page.locator('#rdTeam button', has_text='Bravo').click()
    expect(page.locator('#dlgRadio')).to_be_hidden()
    expect(page.locator('#dlgMate')).to_be_visible()
    expect(page.locator('#tmTitle')).to_have_text('Bravo')
    c = page.evaluate('() => FK.leafletMap().getCenter()')
    assert abs(c['lat'] - 43.01) < 1e-4 and abs(c['lng'] + 76.01) < 1e-4
    page.click('#tmClose')
    expect(page.locator('#dlgMate')).to_be_hidden()
    page.wait_for_function('!history.state.fkSheet')


def test_after_a_reload_the_radio_sheet_still_lists_last_known_teammates(page, app_url):
    boot_team(page, app_url)
    page.reload()
    page.wait_for_function('window.FK && FK.mesh && document.querySelector("#mRadio")')
    open_radio(page)
    expect(page.locator('#rdTeamH')).to_have_text('Teammates, last known (2)')


# ---------------------------------------------------------------- P8 approximate position

def test_teammate_sheet_says_approximate_position(page, app_url):
    boot_team(page, app_url)
    feed(page, node(0x0A0B0C05, long='Delta', pos=dict(lat=43.004, lon=-76.004, alt=0, time=NOW // 1000 - 60, precisionBits=13)))
    page.locator('.tm-pin[data-num="%d"]' % 0x0A0B0C05).click()
    expect(page.locator('#dlgMate')).to_be_visible()
    expect(page.locator('#tmApprox')).to_have_text('Approximate position')
    page.click('#tmClose')
    expect(page.locator('#dlgMate')).to_be_hidden()
    page.evaluate('() => FK.mapShow(43.01, -76.01)')
    page.locator('.tm-pin[data-num="%d"]' % BRAVO).click()
    expect(page.locator('#dlgMate')).to_be_visible()
    expect(page.locator('#tmApprox')).to_be_hidden()


# ---------------------------------------------------------------- T14 the Settings menu

def test_settings_close_is_on_screen_at_360_by_640(page, app_url):
    page.add_init_script("localStorage.setItem('fk.advAck', 'true'); localStorage.setItem('fk.meshOn', 'true')")
    page.goto(app_url + '#/tactical/map')
    page.wait_for_function('window.FK && FK.sheet')
    page.click('#menuBtn')
    page.wait_for_selector('#dlgMenu[open]')
    d = page.locator('#dlgMenu').bounding_box()
    c = page.locator('#menuClose').bounding_box()
    assert c['y'] >= d['y'] and c['y'] + c['height'] <= d['y'] + d['height'] and c['y'] + c['height'] <= 640, (c, d)
    page.evaluate("document.querySelector('#dlgMenu').scrollTop = 0")
    c = page.locator('#menuClose').bounding_box()
    assert c['y'] + c['height'] <= d['y'] + d['height']
    assert page.evaluate("document.querySelector('#dlgMenu h2').getBoundingClientRect().top") >= d['y']   # nothing above moved off
    page.click('#menuClose')
    expect(page.locator('#dlgMenu')).to_be_hidden()
