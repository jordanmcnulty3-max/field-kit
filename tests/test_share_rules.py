"""FK.share: the shared record on a marker (marker.net), sharing, and the rules for incoming markers (comms Task 6).

Incoming waypoints are fed as decoded packets on a private channel (FK._test.mesh.feed, as tests/test_mesh_state.py does);
what is sent is read back as real bytes from the fake radio (tests/radio.py) and parsed with the reference package.
Times: waypoint `expire` is epoch SECONDS on the wire and in net.expire; every other time is ms."""
import json

import pytest

from . import meshref, radio
from .tac import store
from .test_mesh_state import BRAVO, CHARLIE, DELTA, ME, PRIV, boot, chan, connected, feed_packet

mesh_pb2 = pytest.importorskip('meshtastic.protobuf.mesh_pb2')

WPT = meshref.PORT['WAYPOINT']
T0 = 1766000000000           # a stored marker time (ms)
NOW = 1800000000000          # the fake clock's start, for clock tests (ms)
DAY = 86_400_000
ICON = {'point': 0x1F4CD, 'camp': 0x26FA, 'hostile': 0x2666}
SMILE = 0x1F600              # an emoji Field Kit has no kind for (another app's icon)


def net(wid, frm=BRAVO, by='Bravo', **kw):
    return dict(dict(wid=wid, by=by, t=T0, chBy='', chT=0, icon=0, expire=0, pending=False, rx=False, **{'from': frm}), **kw)


def mk(id_, n=None, name='Camp', lat=43.0, lon=-76.0, kind='point', note='', t=T0):
    d = dict(id=id_, name=name, lat=lat, lon=lon, alt=None, t=t, kind=kind, note=note)
    if n is not None:
        d['net'] = n
    return d


def start(page, app_url, wps=(), tombs=None, link=True, clock=None, me=ME, **seed):
    """Seed storage, load, switch the radio link on. link=True connects the fake radio (private channel, can share);
    link='private' only sets a private channel verdict (incoming works, nothing can be sent); link=False does neither."""
    if clock is not None:   # a paused clock: time moves only with run_for / fast_forward, so spacing is exact
        page.clock.install(time=(clock - 1000) / 1000)
        page.clock.pause_at(clock / 1000)
    kv = dict(advAck=True, wps=list(wps), **seed)
    if tombs is not None:
        kv['meshTombs'] = tombs
    if me is not None and link != True:   # noqa: E712  (a connect stores it by itself)
        kv['meshMe'] = me
    store(page, **kv)
    if link is True:
        connected(page, app_url)
    else:
        boot(page, app_url)
        if link == 'private':
            chan(page, psk=PRIV)
    page.wait_for_function('window.FK && FK.share')
    return page


def settle(page, clock=False):
    """Let the incoming queue apply (it applies once per animation frame)."""
    if clock:
        page.clock.run_for(100)
    else:
        page.evaluate('() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))')


def incoming(page, frm=BRAVO, clock=False, **wp):
    feed_packet(page, frm, WPT, meshref.waypoint_bytes(**wp))
    settle(page, clock)


def markers(page):
    return page.evaluate('() => FK.tac.markers()')


def one(page, id_):
    return next((m for m in markers(page) if m['id'] == id_), None)


def by_wid(page):
    return {m['net']['wid']: m for m in markers(page) if m.get('net')}


def tombs(page):
    return [t['wid'] for t in page.evaluate("() => JSON.parse(localStorage.getItem('fk.meshTombs') || '[]')")]


def sent_wps(page):
    out = []
    for b in radio.sent(page):
        tr = mesh_pb2.ToRadio.FromString(b)
        if tr.HasField('packet') and tr.packet.decoded.portnum == WPT:
            out.append(mesh_pb2.Waypoint.FromString(tr.packet.decoded.payload))
    return out


def now_s(page):
    return page.evaluate('() => Math.floor(Date.now() / 1000)')


def js(page, expr, arg=None):
    return page.evaluate(expr, arg)


# ---------------------------------------------------------------- the three named tests

def test_old_markers_have_no_net_and_are_never_sent(page, app_url):
    old = [mk('w1'), mk('w2', name='Spring', kind='water', note='north side'), mk('w3', name='Bad', kind='hostile')]
    start(page, app_url, wps=old)
    assert all('net' not in m for m in markers(page))
    assert js(page, "() => ['w1', 'w2', 'w3'].map(id => [FK.share.isShared(id), FK.share.mine(id)])") == [[False, False]] * 3
    assert js(page, '() => FK.share.resendMine()') == 0
    # a fresh start-up download (canShare goes false, then true again) sends nothing either
    js(page, '() => FK._test.mesh.link("syncing", "")')
    chan(page, psk=PRIV)
    js(page, '() => FK._test.mesh.link("on", "Meshtastic_a1b2")')
    page.wait_for_timeout(400)
    assert sent_wps(page) == []
    assert json.loads(js(page, "() => localStorage.getItem('fk.wps')")) == old   # storage untouched


BAD_NETS = {
    'b0': net(0), 'b1': net(0x100000000), 'b2': net(1.5), 'b3': net(13, by=7), 'b4': net(14, pending='yes'),
    'b5': {k: v for k, v in net(15).items() if k != 'rx'}, 'b6': 'junk', 'b7': net(17, expire=-1), 'b8': net(18, icon=1.5),
    'b9': net(19, t='x'), 'b10': net(20, chT=None), 'b11': net(21, frm=-4), 'b12': [21], 'b13': net(23, chBy=5),
}


def test_bad_net_in_a_backup_is_dropped(page, app_url, tmp_path):
    start(page, app_url, link=False)
    wps = [mk(k, n) for k, n in BAD_NETS.items()] + [mk('ok', net(30, frm=ME, by='x' * 90)), mk('dup', net(30, frm=ME))]
    data = {'fk.wps': json.dumps(wps), 'fk.meshOn': 'true', 'fk.meshTombs': json.dumps([{'wid': 99, 't': 1}])}
    path = tmp_path / 'b.json'
    path.write_text(json.dumps({'app': 'Field Kit', 'version': '7.10', 'saved': '2026-11-20T10:00:00.000Z', 'data': data}))
    page.click('#menuBtn')
    page.wait_for_selector('#dlgMenu[open]')
    page.set_input_files('#bkFile', str(path))
    page.wait_for_selector('#bkConfirm:not([hidden])')
    page.click('#bkGo')
    page.wait_for_timeout(js(page, '() => FK.tools.confirm.ignoreMs') + 100)
    with page.expect_navigation():
        page.click('#bkGo')
    page.wait_for_function('window.FK && FK.share')
    ms = {m['id']: m for m in markers(page)}
    assert sorted(ms) == sorted(list(BAD_NETS) + ['ok', 'dup'])                 # every marker kept...
    assert [k for k, m in ms.items() if 'net' in m] == ['ok']                    # ...but only the good record is shared
    assert ms['ok']['net']['by'] == 'x' * 40                                    # strings cut to 40
    assert js(page, '() => FK.mesh.connect()') is True
    assert js(page, '() => FK.share.resendMine()') == 1
    page.wait_for_timeout(300)
    assert [w.id for w in sent_wps(page)] == [30]                               # the bad ones never go out


def test_stale_resend_overwrites(page, app_url):
    """The accepted limit: a waypoint carries no version, so an older copy sent later wins. "Changed by" shows who."""
    start(page, app_url, wps=[mk('a', net(50), name='Rally')], link='private')
    incoming(page, CHARLIE, id=50, lat=43.0, lon=-76.0, name='Rally north', icon=ICON['point'])
    m = by_wid(page)[50]
    assert (m['name'], m['net']['chBy']) == ('Rally north', 'Radio 0c03')
    incoming(page, DELTA, id=50, lat=43.0, lon=-76.0, name='Rally', icon=ICON['point'])   # Delta missed the edit
    m = by_wid(page)[50]
    assert (m['name'], m['net']['chBy']) == ('Rally', 'Radio 0c04')
    assert len(markers(page)) == 1


# ---------------------------------------------------------------- incoming

def test_incoming_new_wid_adds_a_shared_marker(page, app_url):
    start(page, app_url, link='private')
    before = js(page, '() => Date.now()')
    incoming(page, BRAVO, id=77, lat=43.01, lon=-76.01, name='Spring', description='clear water', icon=0x1F4A7)
    [m] = markers(page)
    n = m['net']
    assert (m['name'], m['note'], m['kind'], m['lat'], m['lon']) == ('Spring', 'clear water', 'water', 43.01, -76.01)
    assert (n['wid'], n['from'], n['by'], n['chBy'], n['chT'], n['pending'], n['rx'], n['expire'], n['icon']) == \
        (77, BRAVO, 'Radio 0c02', '', 0, False, True, 0, 0)
    assert before <= m['t'] == n['t'] <= js(page, '() => Date.now()')
    assert js(page, 'id => [FK.share.isShared(id), FK.share.mine(id)]', m['id']) == [True, False]
    assert m['id'] in js(page, '() => JSON.parse(localStorage.getItem("fk.wps")).map(m => m.id)')


def test_incoming_known_wid_updates_name_note_kind_position_and_changed_by(page, app_url):
    start(page, app_url, wps=[mk('a', net(60), note='old')], link='private')
    js(page, "() => FK.tac.updateMarker('a', { alt: 120 })")
    t1 = js(page, '() => Math.floor((Date.now() - 3600000) / 60000) * 60000')
    seen = js(page, 't => MMK.seen(t)', t1)
    incoming(page, CHARLIE, id=60, lat=43.02, lon=-76.02, name='Watcher', description=seen + 'on the ridge', icon=ICON['hostile'])
    m = one(page, 'a')
    assert (m['name'], m['note'], m['kind'], m['lat'], m['lon'], m['alt'], m['t']) == \
        ('Watcher', 'on the ridge', 'hostile', 43.02, -76.02, None, t1)                 # t from the prefix
    n = m['net']
    assert (n['from'], n['by'], n['chBy'], n['rx']) == (BRAVO, 'Bravo', 'Radio 0c03', False)  # the maker is unchanged
    assert n['chT'] > T0 and n['t'] == n['chT']
    # an update with no prefix (a place kind) leaves t alone
    incoming(page, DELTA, id=60, lat=43.02, lon=-76.02, name='Camp again', description='', icon=ICON['camp'])
    m = one(page, 'a')
    assert (m['name'], m['kind'], m['t'], m['net']['chBy']) == ('Camp again', 'camp', t1, 'Radio 0c04')
    assert len(markers(page)) == 1


def test_teammate_update_of_mine_keeps_it_mine(page, app_url):
    start(page, app_url, wps=[mk('a', net(65, frm=ME, by='Alpha'))], link='private')
    incoming(page, BRAVO, id=65, lat=43.01, lon=-76.0, name='Camp moved', icon=ICON['camp'])
    m = one(page, 'a')
    assert (m['name'], m['kind'], m['lat'], m['net']['from'], m['net']['by'], m['net']['chBy']) == \
        ('Camp moved', 'camp', 43.01, ME, 'Alpha', 'Radio 0c02')
    assert js(page, "() => FK.share.mine('a')") is True and len(markers(page)) == 1


def test_after_unshare_a_teammates_resend_is_ignored(page, app_url):
    """Stop sharing tombs the number: a teammate's later resend does not re-create it beside the private copy."""
    start(page, app_url, wps=[mk('a', net(67, frm=ME), name='Camp')], link='private')
    assert js(page, "() => FK.share.unshare('a')") is True
    assert tombs(page) == [67]
    before = markers(page)
    incoming(page, BRAVO, id=67, lat=43.0, lon=-76.0, name='Camp')
    incoming(page, BRAVO, id=67, lat=43.0, lon=-76.0, expire=1)
    assert markers(page) == before and 'net' not in one(page, 'a') and tombs(page) == [67]


# The reference package's delete (meshtastic Python deleteWaypoint): only the id, expire 0, no position, no name.
def test_bare_delete_removes_a_held_marker_from_a_teammate_and_tombs(page, app_url):
    start(page, app_url, wps=[mk('a', net(130)), mk('p')], link='private')
    incoming(page, CHARLIE, id=130)
    assert [m['id'] for m in markers(page)] == ['p'] and tombs(page) == [130]


def test_bare_delete_of_mine_keeps_a_private_copy_with_a_note(page, app_url):
    start(page, app_url, wps=[mk('a', net(131, frm=ME), note='by the oak')], link='private')
    incoming(page, BRAVO, id=131)
    a = one(page, 'a')
    assert 'net' not in a and a['note'] == 'Deleted by Radio 0c02. by the oak' and tombs(page) == [131]


def test_bare_delete_for_a_number_not_held_is_ignored_and_adds_no_tomb(page, app_url):
    start(page, app_url, wps=[mk('a', net(132))], link='private')
    before = markers(page)
    incoming(page, CHARLIE, id=133)
    assert markers(page) == before and tombs(page) == []


def test_a_bare_packet_with_a_name_or_a_position_is_not_a_delete(page, app_url):
    start(page, app_url, wps=[mk('a', net(134), name='Camp'), mk('b', net(135), name='Spring')], link='private')
    incoming(page, CHARLIE, id=134, name='Renamed')                       # a name, no position: malformed, ignored
    incoming(page, CHARLIE, id=135, lat=43.01, lon=-76.01)               # a position, no name: an update
    a, b = by_wid(page)[134], by_wid(page)[135]
    assert (a['name'], a['lat']) == ('Camp', 43.0)
    assert (b['name'], b['lat']) == ('Marker', 43.01)
    assert tombs(page) == []


def test_incoming_past_expiry_is_a_delete(page, app_url):
    start(page, app_url, wps=[mk('a', net(61)), mk('b', net(62))], link='private')
    incoming(page, CHARLIE, id=61, lat=43.0, lon=-76.0, name='Camp', expire=1)
    incoming(page, CHARLIE, id=62, lat=43.0, lon=-76.0, name='Camp', expire=now_s(page) - 5)
    assert markers(page) == [] and sorted(tombs(page)) == [61, 62]
    incoming(page, CHARLIE, id=63, expire=1)          # a delete for a number this phone never held: remembered too
    assert markers(page) == [] and 63 in tombs(page)


def test_incoming_malformed_is_ignored(page, app_url):
    start(page, app_url, wps=[mk('a', net(64), name='Camp'), mk('m', net(66, frm=ME), name='Mine')], link='private')
    before = markers(page)
    incoming(page, CHARLIE, id=64, name='No place')                          # no position (0, 0)
    incoming(page, CHARLIE, id=64, lat=95.0, lon=-76.0, name='Off the map')
    incoming(page, CHARLIE, id=0, lat=43.0, lon=-76.0, name='No number')    # no waypoint number
    incoming(page, CHARLIE, id=65, name='Nowhere new')
    incoming(page, CHARLIE, id=66, lat=0.0, lon=0.0, name='Mine moved to nowhere')
    feed_packet(page, CHARLIE, WPT, b'\xff\xff\xff')                          # bytes that do not decode
    settle(page)
    assert markers(page) == before and tombs(page) == []


def test_incoming_delete_removes_and_tombs(page, app_url):
    start(page, app_url, wps=[mk('a', net(66)), mk('b', net(67, frm=CHARLIE)), mk('p')], link='private')
    incoming(page, CHARLIE, id=66, lat=43.0, lon=-76.0, expire=1)
    assert [m['id'] for m in markers(page)] == ['b', 'p'] and tombs(page) == [66]


def test_incoming_delete_of_mine_keeps_a_private_copy_with_a_note(page, app_url):
    start(page, app_url, wps=[mk('a', net(68, frm=ME), note='by the oak'), mk('b', net(69, frm=ME), note='x' * 495),
                              mk('c', net(70, frm=ME))], link='private')
    for wid in (68, 69, 70):
        incoming(page, BRAVO, id=wid, lat=43.0, lon=-76.0, expire=1)
    assert one(page, 'c')['note'] == 'Deleted by Radio 0c02.' and 'net' not in one(page, 'c')
    a, b = one(page, 'a'), one(page, 'b')
    assert 'net' not in a and a['note'] == 'Deleted by Radio 0c02. by the oak'     # the deleter's radio name
    assert 'net' not in b and b['note'] == ('Deleted by Radio 0c02. ' + 'x' * 495)[:500] and len(b['note']) == 500
    assert sorted(tombs(page)) == [68, 69, 70]
    # deleted markers stay deleted: a teammate who missed the delete cannot bring it back
    incoming(page, CHARLIE, id=68, lat=43.0, lon=-76.0, name='Camp')
    assert len(markers(page)) == 3 and 'net' not in one(page, 'a')


@pytest.mark.parametrize('event', ['update', 'delete', 'future', 'malformed'])
def test_incoming_wid_in_tombs_is_ignored(page, app_url, event):
    start(page, app_url, wps=[mk('p', note='mine, formerly shared')], tombs=[{'wid': 70, 't': NOW - DAY}], link='private',
          clock=NOW)
    wp = {'update': dict(lat=43.0, lon=-76.0, name='Back'), 'delete': dict(lat=43.0, lon=-76.0, expire=1),
          'future': dict(lat=43.0, lon=-76.0, name='Back', expire=NOW // 1000 + 3600), 'malformed': dict(name='x')}[event]
    before = markers(page)
    incoming(page, BRAVO, clock=True, id=70, **wp)
    assert markers(page) == before and tombs(page) == [70]


def test_incoming_delete_clears_the_navigation_target(page, app_url):
    start(page, app_url, wps=[mk('a', net(71))], link='private')
    assert js(page, "() => FK.tac.setTarget({ type: 'marker', id: 'a' })") is True
    incoming(page, BRAVO, id=71, lat=43.0, lon=-76.0, expire=1)
    assert js(page, '() => FK.tac.target()') is None and markers(page) == []


def test_echo_of_own_send_changes_nothing(page, app_url):
    start(page, app_url, wps=[mk('a', kind='hostile', note='at the bend')])
    assert js(page, "() => FK.share.share('a')") == 'sent'
    before = markers(page)
    wire = radio.sent(page)[-1]
    tr = mesh_pb2.ToRadio.FromString(wire)
    feed_packet(page, ME, WPT, tr.packet.decoded.payload)                # our own radio's number, our own bytes
    settle(page)
    assert markers(page) == before                                      # no copy, no "changed by" ourselves, t not rounded
    # and an echo of a delete we sent
    assert js(page, "() => FK.share.remove('a', true)") == 'sent'
    feed_packet(page, ME, WPT, mesh_pb2.ToRadio.FromString(radio.sent(page)[-1]).packet.decoded.payload)
    settle(page)
    assert markers(page) == []


def test_future_seen_time_is_clamped_to_receipt(page, app_url):
    start(page, app_url, link='private')
    ahead = js(page, '() => Math.floor((Date.now() + 3 * 3600000) / 60000) * 60000')
    before = js(page, '() => Date.now()')
    incoming(page, BRAVO, id=72, lat=43.0, lon=-76.0, name='Watcher', icon=ICON['hostile'],
             description=js(page, 't => MMK.seen(t)', ahead) + 'moving')
    [m] = markers(page)
    assert before <= m['t'] <= js(page, '() => Date.now()') < ahead
    assert m['net']['rx'] is False and m['note'] == 'moving'


def test_incoming_future_expiry_is_kept_and_removed_when_it_passes(page, app_url):
    start(page, app_url, wps=[mk('b', net(73)), mk('c', net(74, frm=ME))], link='private', clock=NOW)
    exp = NOW // 1000 + 600
    incoming(page, CHARLIE, clock=True, id=75, lat=43.0, lon=-76.0, name='New', expire=exp)      # no marker
    incoming(page, CHARLIE, clock=True, id=73, lat=43.0, lon=-76.0, name='Upd', expire=exp)      # shared, not mine
    incoming(page, CHARLIE, clock=True, id=74, lat=43.0, lon=-76.0, name='Mine', expire=exp)     # shared, mine
    w = by_wid(page)
    assert {k: v['net']['expire'] for k, v in w.items()} == {73: exp, 74: exp, 75: exp}
    page.clock.run_for(601_000)
    incoming(page, CHARLIE, clock=True, id=76, lat=43.0, lon=-76.0, name='Other')                # any incoming checks
    assert list(by_wid(page)) == [76] and sorted(tombs(page)) == [73, 74, 75]


# ---------------------------------------------------------------- sharing

def test_share_sends_a_new_random_wid_with_expire_0(page, app_url):
    start(page, app_url, wps=[mk('a', name='Camp', kind='camp', note='dry'), mk('h', name='Two', kind='hostile', t=T0 + 60000)])
    assert js(page, "() => FK.share.share('a')") == 'sent'
    n = one(page, 'a')['net']
    assert 1 <= n['wid'] <= 0xFFFFFFFF
    assert (n['from'], n['by'], n['pending'], n['expire'], n['icon'], n['chBy']) == (ME, 'Alpha', False, 0, 0, '')
    w = sent_wps(page)[-1]
    assert (w.id, w.name, w.description, w.icon, w.expire, w.latitude_i) == (n['wid'], 'Camp', 'dry', ICON['camp'], 0, 430000000)
    assert js(page, "() => FK.share.share('h')") == 'sent'
    w = sent_wps(page)[-1]
    assert w.description == js(page, 't => MMK.seen(t)', T0 + 60000) and w.icon == ICON['hostile']
    assert w.id != n['wid']
    assert js(page, "() => [FK.share.mine('a'), FK.share.isShared('a')]") == [True, True]


def test_share_new_wid_is_never_one_already_held(page, app_url):
    start(page, app_url, wps=[mk('t', net(5)), mk('a')], tombs=[{'wid': 6, 't': NOW}])
    js(page, """() => { const seq = [4 / 0xFFFFFFFF, 5 / 0xFFFFFFFF, 7 / 0xFFFFFFFF]; let i = 0; const r = Math.random;
      Math.random = () => i < seq.length ? seq[i++] : r(); }""")
    assert js(page, "() => FK.share.share('a')") == 'sent'
    assert one(page, 'a')['net']['wid'] == 8      # 1 + floor(r * 0xFFFFFFFF): 5 is held, 6 is a tomb, 8 is free


def test_share_too_long_changes_nothing(page, app_url):
    start(page, app_url, wps=[mk('a', name='N' * 30), mk('b', note='x' * 100), mk('c', kind='hostile', note='x' * 81)])
    before = markers(page)
    assert js(page, "() => Promise.all(['a', 'b', 'c'].map(id => FK.share.share(id)))") == ['toolong'] * 3
    assert markers(page) == before and sent_wps(page) == []


def test_share_without_a_link_is_pending(page, app_url):
    start(page, app_url, wps=[mk('a')], link='private')
    assert js(page, "() => FK.share.share('a')") == 'pending'
    n = one(page, 'a')['net']
    assert n['pending'] is True and n['from'] == ME
    assert js(page, "() => FK.share.share('nope')") == 'no'


def test_pending_markers_are_sent_on_connect_3s_apart(page, app_url):
    wps = [mk('a', net(81, frm=ME, pending=True)), mk('b', net(82, frm=ME)), mk('c', net(83, pending=True)),
           mk('d', net(84, frm=ME, pending=True))]
    start(page, app_url, wps=wps, link=False, clock=NOW)
    assert js(page, '() => FK.mesh.connect()') is True
    assert sent_wps(page) == []                            # never from inside the start-up handler: a timer starts it
    page.clock.run_for(50)
    assert [w.id for w in sent_wps(page)] == [81]          # the first at once
    page.clock.run_for(2_900)
    assert len(sent_wps(page)) == 1
    page.clock.run_for(100)
    assert [w.id for w in sent_wps(page)] == [81, 83]      # anyone's pending marker; never a marker that is not pending
    page.clock.run_for(3_000)
    assert [w.id for w in sent_wps(page)] == [81, 83, 84]
    page.clock.run_for(10_000)
    assert len(sent_wps(page)) == 3
    assert [m['net']['pending'] for m in markers(page)] == [False, False, False, False]


def test_pending_marker_shared_before_any_radio_becomes_mine_when_sent(page, app_url):
    start(page, app_url, wps=[mk('a')], link=False, me=None)
    assert js(page, '() => FK.mesh.myNum()') is None
    assert js(page, "() => FK.share.share('a')") == 'pending'
    assert one(page, 'a')['net']['from'] == 0 and js(page, "() => FK.share.mine('a')") is False
    assert js(page, '() => FK.mesh.connect()') is True
    page.wait_for_function("() => FK.tac.markers()[0].net.pending === false")
    n = one(page, 'a')['net']
    assert (n['from'], n['by']) == (ME, 'Alpha') and js(page, "() => FK.share.mine('a')") is True
    assert [w.id for w in sent_wps(page)] == [n['wid']]


def test_mine_is_false_before_any_radio_has_connected(page, app_url):
    start(page, app_url, wps=[mk('a', net(85, frm=ME)), mk('b', net(86, frm=0))], link=False, me=None)
    assert js(page, '() => [FK.mesh.myNum(), FK.share.mine("a"), FK.share.mine("b"), FK.share.isShared("a")]') == \
        [None, False, False, True]


def test_resend_mine_sends_only_mine_3s_apart(page, app_url):
    wps = [mk('a', net(91, frm=ME)), mk('b', net(92)), mk('c', net(93, frm=ME)), mk('d'), mk('e', net(94, frm=ME), name='N' * 30)]
    start(page, app_url, wps=wps, link=False, clock=NOW)
    assert js(page, '() => FK.share.resendMine()') == 0     # no link: nothing queued
    assert js(page, '() => FK.mesh.connect()') is True
    page.clock.run_for(3_100)
    assert js(page, '() => FK.share.resendMine()') == 2     # mine and fits (e is too long now)
    assert js(page, '() => FK.share.resendMine()') == 0     # already queued
    page.clock.run_for(10)
    assert [w.id for w in sent_wps(page)] == [91]
    page.clock.run_for(2_900)
    assert len(sent_wps(page)) == 1
    page.clock.run_for(100)
    assert [w.id for w in sent_wps(page)] == [91, 93]


def test_own_shares_send_expire_0_and_a_resend_keeps_expire_and_icon(page, app_url):
    exp = 2_000_000_000
    start(page, app_url, wps=[mk('a', net(95, expire=exp, icon=SMILE), name='Theirs'), mk('b')])
    assert js(page, "() => FK.share.share('b')") == 'sent'
    assert sent_wps(page)[-1].expire == 0
    assert js(page, "() => FK.share.resend('a')") == 'sent'
    w = sent_wps(page)[-1]
    assert (w.id, w.expire, w.icon, w.name) == (95, exp, SMILE, 'Theirs')


def test_foreign_icon_kept_while_point_and_cleared_when_the_kind_changes(page, app_url):
    start(page, app_url)
    incoming(page, BRAVO, id=96, lat=43.0, lon=-76.0, name='Smile', icon=SMILE)
    m = by_wid(page)[96]
    assert (m['kind'], m['net']['icon']) == ('point', SMILE)
    assert js(page, 'id => FK.share.resend(id)', m['id']) == 'sent'
    assert sent_wps(page)[-1].icon == SMILE
    assert js(page, "id => FK.tac.updateMarker(id, { kind: 'camp' })", m['id']) is True
    assert one(page, m['id'])['net']['icon'] == 0
    assert js(page, 'id => FK.share.changed(id)', m['id']) == 'sent'
    assert sent_wps(page)[-1].icon == ICON['camp']
    assert js(page, "id => FK.tac.updateMarker(id, { kind: 'point' })", m['id']) is True
    assert js(page, 'id => FK.share.changed(id)', m['id']) == 'sent'
    assert sent_wps(page)[-1].icon == ICON['point']      # the foreign emoji does not come back


def test_changed_sends_again_under_the_same_wid(page, app_url):
    start(page, app_url, wps=[mk('a', net(97, chBy='Bravo', chT=T0))])
    assert js(page, "() => FK.tac.updateMarker('a', { name: 'Camp east', lat: 43.01 })") is True
    assert js(page, "() => FK.share.changed('a')") == 'sent'
    w = sent_wps(page)[-1]
    assert (w.id, w.name, w.latitude_i) == (97, 'Camp east', 430100000)
    n = one(page, 'a')['net']
    assert (n['chBy'], n['chT'], n['from']) == ('', 0, BRAVO)     # our own change is not "changed by" anyone
    assert js(page, "() => FK.tac.updateMarker('a', { name: 'N'.repeat(30) })") is True
    assert js(page, "() => FK.share.changed('a')") == 'toolong' and len(sent_wps(page)) == 1
    js(page, "() => FK.tac.addMarker({ lat: 43, lon: -76, name: 'Private' })")
    assert js(page, "() => Promise.all([FK.share.changed('nope'), FK.share.changed(FK.tac.markers()[1].id)])") == ['no', 'no']


def test_unshare_makes_a_private_copy_and_sends_nothing(page, app_url):
    start(page, app_url, wps=[mk('a', net(98, frm=ME))])
    assert js(page, "() => FK.share.unshare('a')") is True
    assert 'net' not in one(page, 'a') and sent_wps(page) == [] and tombs(page) == [98]
    assert js(page, "() => FK.share.unshare('a')") is False


def test_remove_for_everyone_sends_expire_1_tombs_and_removes(page, app_url):
    start(page, app_url, wps=[mk('a', net(99), name='Theirs'), mk('p')])
    assert js(page, "() => FK.share.remove('a', true)") == 'sent'   # anyone may delete a shared marker for everyone
    w = sent_wps(page)[-1]
    assert (w.id, w.expire, w.name, w.icon, w.latitude_i, w.longitude_i) == (99, 1, 'Theirs', ICON['point'], 430000000, -760000000)
    assert [m['id'] for m in markers(page)] == ['p'] and tombs(page) == [99]
    assert js(page, "() => FK.share.remove('p', true)") == 'local'  # a private marker: removed, nothing sent, no tomb
    assert markers(page) == [] and len(sent_wps(page)) == 1 and tombs(page) == [99]
    assert js(page, "() => FK.share.remove('nope', true)") == 'no'


def test_remove_for_everyone_without_a_link_is_local(page, app_url):
    start(page, app_url, wps=[mk('a', net(136))], link='private')
    assert js(page, "() => FK.share.remove('a', true)") == 'local'
    assert markers(page) == [] and tombs(page) == [136]


def test_remove_for_everyone_when_the_send_fails_is_local(page, app_url):
    start(page, app_url, wps=[mk('a', net(137))])
    js(page, '() => { FK.mesh.sendWaypoint = async () => false; }')
    assert js(page, "() => FK.share.remove('a', true)") == 'local'
    assert markers(page) == [] and tombs(page) == [137] and sent_wps(page) == []


def test_remove_on_this_phone_only_tombs_and_sends_nothing(page, app_url):
    start(page, app_url, wps=[mk('a', net(100))])
    assert js(page, "() => FK.share.remove('a', false)") == 'local'
    assert markers(page) == [] and tombs(page) == [100] and sent_wps(page) == []
    incoming(page, BRAVO, id=100, lat=43.0, lon=-76.0, name='Back')
    assert markers(page) == []


# ---------------------------------------------------------------- storage over time

def test_expiry_on_load_on_incoming_and_each_minute_on_the_map(page, app_url):
    s = NOW // 1000
    wps = [mk('gone', net(101, expire=s - 1)), mk('b', net(102, expire=s + 120)), mk('c', net(103, expire=s + 300)),
           mk('keep', net(104))]
    start(page, app_url, wps=wps, link='private', clock=NOW)
    js(page, "() => FK.route.go('/emergency')")
    assert [m['id'] for m in markers(page)] == ['b', 'c', 'keep'] and tombs(page) == [101]     # on load
    page.clock.run_for(130_000)                                       # not on the map: no timer
    assert [m['id'] for m in markers(page)] == ['b', 'c', 'keep']
    incoming(page, CHARLIE, clock=True, id=105, lat=43.0, lon=-76.0, name='New')
    assert [m['id'] for m in markers(page)][:2] == ['c', 'keep'] and 102 in tombs(page)       # on an incoming message
    js(page, "() => FK.route.go('/tactical/map')")
    page.clock.run_for(240_000)                                       # past c's expiry, then the minute timer
    assert 'c' not in [m['id'] for m in markers(page)] and 103 in tombs(page)


def test_tombs_are_kept_30_days(page, app_url):
    start(page, app_url, wps=[mk('a', net(110))], link='private', clock=NOW)
    assert js(page, "() => FK.share.remove('a', false)") == 'local'
    for _ in range(29):   # a day at a time: one call of 29 days in ms overflows
        page.clock.fast_forward(DAY)
    incoming(page, BRAVO, clock=True, id=110, lat=43.0, lon=-76.0, name='Back')
    assert markers(page) == [] and tombs(page) == [110]
    page.clock.fast_forward(DAY + 60_000)
    incoming(page, BRAVO, clock=True, id=110, lat=43.0, lon=-76.0, name='Back')
    assert [m['name'] for m in markers(page)] == ['Back'] and tombs(page) == []


def test_cap_500_drops_the_oldest_from_teammates(page, app_url):
    wps = [mk(f't{i}', net(1000 + i, t=T0 + i * 1000)) for i in range(500)] + [mk('mine', net(9, frm=ME, t=1))]
    start(page, app_url, wps=wps, link='private')
    assert js(page, '() => FK.share.dropped()') == 0
    incoming(page, CHARLIE, id=2000, lat=43.0, lon=-76.0, name='New')
    ids = [m['id'] for m in markers(page)]
    assert len(ids) == 501 and 't0' not in ids and 'mine' in ids and 2000 in by_wid(page)   # no tomb for a dropped one
    assert js(page, '() => FK.share.dropped()') == 1 and tombs(page) == []
    incoming(page, CHARLIE, id=1001, lat=43.0, lon=-76.0, name='Upd')                       # an update refreshes its time
    incoming(page, CHARLIE, id=2001, lat=43.0, lon=-76.0, name='New 2')
    ids = [m['id'] for m in markers(page)]
    assert 't1' in ids and 't2' not in ids and js(page, '() => FK.share.dropped()') == 2


def test_burst_of_10000_costs_one_write_and_one_event_per_frame(page, app_url):
    start(page, app_url, link='private')
    r = js(page, """() => new Promise(done => {
      const writes = { wps: 0, all: 0 }, set = Storage.prototype.setItem;
      Storage.prototype.setItem = function (k, v) { writes.all++; if (k === 'fk.wps') writes.wps++; return set.call(this, k, v); };
      let events = 0; FK.on('wps', () => events++);
      for (let i = 0; i < 10000; i++) FK._test.mesh.feed({ type: 'packet', from: 0x0A0B0C02, to: 0xFFFFFFFF, channel: 0, id: i + 1,
        rxTime: 0, portnum: MPB.PORT.WAYPOINT, payload: MPB.enc.waypoint({ id: i + 1, lat: 43, lon: -76, expire: 0, lockedTo: 0,
          name: 'W' + i, description: '', icon: 0 }) });
      const fed = { wps: writes.wps, events };
      requestAnimationFrame(() => requestAnimationFrame(() => { Storage.prototype.setItem = set;
        done({ fed, wps: writes.wps, events, n: FK.tac.markers().length, first: FK.tac.markers()[0].name,
               dropped: FK.share.dropped() }); }));
    })""")
    assert r['fed'] == {'wps': 0, 'events': 0}          # nothing written while the messages arrive
    assert (r['wps'], r['events']) == (1, 1)
    assert (r['n'], r['first'], r['dropped']) == (500, 'W9500', 9500)


def test_backup_carries_net_and_tombs_as_they_are(page, app_url, tmp_path):
    start(page, app_url, wps=[mk('a', net(120, expire=2_000_000_000, icon=SMILE))], tombs=[{'wid': 7, 't': 1}], link=False)
    stored_wps, stored_tombs = js(page, "() => [localStorage.getItem('fk.wps'), localStorage.getItem('fk.meshTombs')]")
    page.click('#menuBtn')
    page.wait_for_selector('#dlgMenu[open]')
    with page.expect_download() as d:
        page.click('#bkSave')
    path = tmp_path / 'b.json'
    d.value.save_as(path)
    data = json.loads(path.read_text())['data']
    assert data['fk.wps'] == stored_wps and data['fk.meshTombs'] == stored_tombs
    assert json.loads(data['fk.wps'])[0]['net'] == net(120, expire=2_000_000_000, icon=SMILE)
