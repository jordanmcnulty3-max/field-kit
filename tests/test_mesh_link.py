"""MLINK: the Bluetooth link to a Meshtastic radio, driven against the scripted fake radio (tests/radio.py)."""
import pytest

from . import meshref, radio

MAKE = """() => {
  window.__msgs = []; window.__states = [];
  window.__link = MLINK.create({
    bluetooth: navigator.bluetooth,
    onMessage: m => window.__msgs.push(m),
    onState: s => window.__states.push(Object.assign({}, s, { seen: window.__msgs.length })),
  });
}"""
TYPES = '() => window.__msgs.map(m => m.type)'
STATES = '() => window.__states.map(s => s.state)'
START_UP = ['myInfo', 'channel', 'nodeInfo', 'nodeInfo', 'nodeInfo', 'configComplete']


def boot(page, app_url, script=None, complete=True, clock=False, **kw):
    radio.install(page, script=script, complete=complete, **kw)
    if clock:
        page.clock.install()
    page.goto(app_url)
    page.wait_for_function('typeof MLINK !== "undefined"')
    page.evaluate(MAKE)
    return page


def connected(page, app_url, **kw):
    boot(page, app_url, **kw)
    assert page.evaluate('() => __link.connect()') is True
    return page


def text_packet(id, text=b'hi'):
    return meshref.ref_from_radio(packet=meshref.mesh_packet(frm=0x0A0B0C02, to=meshref.BROADCAST, id=id,
                                                             portnum=meshref.PORT['TEXT'], payload=text))


def packet_ids(page):
    return page.evaluate('() => window.__msgs.filter(m => m.type === "packet").map(m => m.id)')


def test_start_up_download_reaches_on(page, app_url):
    connected(page, app_url)
    assert page.evaluate(STATES) == ['connecting', 'syncing', 'on']
    assert page.evaluate(TYPES) == START_UP
    st = page.evaluate('() => window.__states')
    assert st[-1]['name'] == 'Meshtastic_a1b2' and st[-1]['seen'] == len(START_UP)   # every start-up message arrived before 'on'
    assert page.evaluate('() => __link.state()') == 'on'
    assert page.evaluate('() => FakeRadio.lastOptions') == {'filters': [{'services': [radio.SERVICE]}]}
    msgs = page.evaluate('() => window.__msgs.map(m => ({ type: m.type, num: m.myNodeNum, name: m.name, psk: m.psk && m.psk.length, prec: m.positionPrecision }))')
    assert msgs[0]['num'] == radio.MY_NUM
    assert (msgs[1]['name'], msgs[1]['psk'], msgs[1]['prec']) == ('Team', 32, 32)
    sent = radio.sent(page)
    assert len(sent) == 1 and sent[0][0] == 0x18   # one wantConfig, nothing else


def test_messages_arrive_in_order_and_once(page, app_url):
    connected(page, app_url)
    for i in (1, 2, 3):
        radio.push(page, text_packet(i))
    page.wait_for_function('window.__msgs.filter(m => m.type === "packet").length >= 3')
    page.evaluate('() => new Promise(r => setTimeout(r, 100))')
    assert packet_ids(page) == [1, 2, 3]
    assert page.evaluate(TYPES) == START_UP + ['packet'] * 3


def test_notification_during_a_drain_is_not_lost(page, app_url):
    connected(page, app_url)
    radio.hold_reads(page)
    radio.notify(page)   # a drain starts and its read (empty) is held
    page.wait_for_function('FakeRadio.heldReads === 1')
    radio.push(page, text_packet(9))   # arrives while that drain is running: the empty read was computed before it
    page.evaluate('() => new Promise(r => setTimeout(r, 50))')
    assert page.evaluate('() => FakeRadio.heldReads') == 1   # still one loop only
    radio.release_reads(page)
    page.wait_for_function('window.__msgs.some(m => m.type === "packet")')
    assert packet_ids(page) == [9]


def test_send_queues_one_write_at_a_time(page, app_url):
    connected(page, app_url)
    radio.slow_writes(page, 30)
    res = page.evaluate('() => Promise.all([0, 1, 2, 3, 4].map(i => __link.send(Uint8Array.of(0x42, i))))')
    assert res == [True] * 5
    assert page.evaluate('() => FakeRadio.maxActive') == 1
    assert [m for m in radio.sent(page)[1:]] == [bytes([0x42, i]) for i in range(5)]


def test_cancelled_chooser_goes_back_to_off(page, app_url):
    boot(page, app_url)
    radio.refuse(page, 'cancel')
    assert page.evaluate('() => __link.connect()') is False
    last = page.evaluate('() => window.__states[window.__states.length - 1]')
    assert (last['state'], last['reason']) == ('off', 'cancelled')
    assert page.evaluate('() => FakeRadio.connects') == 0
    assert page.evaluate('() => __link.reconnect()') is False   # no device was chosen: nothing to reconnect


@pytest.mark.parametrize('how', ['gatt', 'no-service'])
def test_refused_connection_goes_back_to_off(page, app_url, how):
    boot(page, app_url)
    radio.refuse(page, how)
    assert page.evaluate('() => __link.connect()') is False
    last = page.evaluate('() => window.__states[window.__states.length - 1]')
    assert (last['state'], last['reason']) == ('off', 'failed')
    assert page.evaluate('() => FakeRadio.connected()') is False
    radio.refuse(page, None)   # the chosen device stays: reconnect works without a chooser
    assert page.evaluate('() => __link.reconnect()') is True
    assert page.evaluate('() => FakeRadio.choosers') == 1


def test_double_connect_opens_one_chooser(page, app_url):
    boot(page, app_url)
    r = page.evaluate('() => { const a = __link.connect(), b = __link.connect(); return Promise.all([a, b]).then(v => [a === b, v]); }')
    assert r == [True, [True, True]]
    assert page.evaluate('() => FakeRadio.choosers') == 1
    assert len(radio.sent(page)) == 1


def test_drop_reports_lost_then_reconnect_reruns_download(page, app_url):
    connected(page, app_url)
    radio.drop(page)
    page.wait_for_function('__link.state() === "lost"')
    assert page.evaluate('() => __link.send(Uint8Array.of(1))') is False   # nothing is written while disconnected
    assert len(radio.sent(page)) == 1
    assert page.evaluate('() => __link.reconnect()') is True
    assert page.evaluate(STATES) == ['connecting', 'syncing', 'on', 'lost', 'connecting', 'syncing', 'on']
    assert page.evaluate(TYPES) == START_UP * 2
    assert page.evaluate('() => FakeRadio.choosers') == 1
    radio.push(page, text_packet(5))   # notifications work again after the reconnect
    page.wait_for_function('window.__msgs.some(m => m.type === "packet")')


def test_reboot_restarts_download(page, app_url):
    connected(page, app_url)
    radio.push(page, text_packet(1))
    page.wait_for_function('window.__msgs.some(m => m.type === "packet")')
    radio.reboot(page)   # fromnum goes down
    page.wait_for_function('window.__msgs.filter(m => m.type === "configComplete").length === 2')
    page.wait_for_function('__link.state() === "on"')
    assert len([m for m in radio.sent(page) if m[0] == 0x18]) == 2
    assert page.evaluate(STATES) == ['connecting', 'syncing', 'on', 'syncing', 'on']


def test_rebooted_message_restarts_download(page, app_url):
    connected(page, app_url)
    radio.push(page, meshref.ref_from_radio(rebooted=True))
    page.wait_for_function('window.__msgs.filter(m => m.type === "configComplete").length === 2')
    page.wait_for_function('__link.state() === "on"')
    assert page.evaluate(TYPES).count('rebooted') == 1
    assert len([m for m in radio.sent(page) if m[0] == 0x18]) == 2


def test_garbage_message_does_not_stop_the_loop(page, app_url):
    connected(page, app_url)
    radio.push(page, b'\xff\xff\xff')   # not a protobuf message: non-empty, so keep reading
    radio.push(page, text_packet(3))
    page.wait_for_function('window.__msgs.some(m => m.type === "packet")')
    assert page.evaluate(TYPES) == START_UP + ['packet']   # the garbage itself is not passed on
    assert page.evaluate('() => __link.state()') == 'on'


def test_config_complete_with_another_nonce_is_ignored(page, app_url):
    connected_ = boot(page, app_url, complete=False)
    page.evaluate('() => { window.__r = __link.connect().then(v => (window.__res = v)); }')
    page.wait_for_function('window.__msgs.length === 5')
    nonce = meshref.mesh_pb2.ToRadio.FromString(radio.sent(connected_)[0]).want_config_id
    radio.push(page, meshref.ref_from_radio(config_complete=nonce + 1))
    page.wait_for_function('window.__msgs.length === 6')
    assert page.evaluate('() => __link.state()') == 'syncing'
    radio.push(page, meshref.ref_from_radio(config_complete=nonce))
    page.wait_for_function('window.__res === true')
    assert page.evaluate('() => __link.state()') == 'on'


def test_stalled_start_up_times_out(page, app_url):
    boot(page, app_url, complete=False, clock=True)
    page.evaluate('() => { __link.connect().then(v => (window.__res = v)); }')
    page.wait_for_function('__link.state() === "syncing"')
    page.clock.run_for(29_000)
    assert page.evaluate('() => [__link.state(), window.__res]') == ['syncing', None]
    page.clock.run_for(1_500)
    page.wait_for_function('window.__res === false')
    last = page.evaluate('() => window.__states[window.__states.length - 1]')
    assert (last['state'], last['reason']) == ('off', 'failed')
    assert page.evaluate('() => FakeRadio.connected()') is False   # the half-open link is closed


def test_heartbeat_every_300_s(page, app_url):
    connected(page, app_url, clock=True)
    beat = meshref.ref_heartbeat()
    page.clock.run_for(299_000)
    assert len(radio.sent(page)) == 1   # only wantConfig so far
    page.clock.run_for(1_000)
    page.wait_for_function('FakeRadio.sent.length === 2')
    assert radio.sent(page)[1] == beat
    page.clock.run_for(300_000)
    page.wait_for_function('FakeRadio.sent.length === 3')
    page.evaluate('() => __link.disconnect()')
    page.clock.run_for(900_000)
    assert len(radio.sent(page)) == 3   # no timer survives disconnect()
    assert page.evaluate('() => __link.state()') == 'off'
    last = page.evaluate('() => window.__states[window.__states.length - 1]')
    assert last['reason'] == 'user'


def test_unsupported_browser(page, app_url):
    page.add_init_script("Object.defineProperty(navigator, 'bluetooth', { value: undefined, configurable: true });")
    page.goto(app_url)
    page.wait_for_function('typeof MLINK !== "undefined"')
    assert page.evaluate('() => MLINK.supported()') is False
    assert page.evaluate('() => MLINK.supported({ requestDevice() {} })') is True
    page.evaluate(MAKE)
    assert page.evaluate('() => __link.connect()') is False
    last = page.evaluate('() => window.__states[window.__states.length - 1]')
    assert (last['state'], last['reason']) == ('off', 'unsupported')


def last_state(page):
    return page.evaluate('() => window.__states[window.__states.length - 1]')


def start_connect(page):
    page.evaluate('() => { window.__res = undefined; __link.connect().then(v => (window.__res = v)); }')


def test_disconnect_during_chooser_then_late_pick_does_not_connect(page, app_url):
    boot(page, app_url)
    radio.hold(page, 'chooser')
    start_connect(page)
    page.wait_for_function('FakeRadio.choosers === 1')
    page.evaluate('() => __link.disconnect()')
    assert (last_state(page)['state'], last_state(page)['reason']) == ('off', 'user')
    radio.release(page, 'chooser')   # the user picks a radio after all
    page.wait_for_function('window.__res === false')
    assert page.evaluate('() => FakeRadio.connects') == 0
    assert page.evaluate('() => FakeRadio.connected()') is False
    assert (last_state(page)['state'], last_state(page)['reason']) == ('off', 'user')
    assert page.evaluate('() => __link.connect()') is True   # a following connect opens exactly one new chooser
    assert page.evaluate('() => FakeRadio.choosers') == 2


def test_disconnect_during_gatt_connect_leaves_the_radio_free(page, app_url):
    boot(page, app_url)
    radio.hold(page, 'gatt')
    start_connect(page)
    page.wait_for_function('FakeRadio.connects === 1')
    page.evaluate('() => __link.disconnect()')
    radio.release(page, 'gatt')   # the connection completes after the user said disconnect
    page.wait_for_function('window.__res === false')
    assert page.evaluate('() => FakeRadio.connected()') is False
    assert (last_state(page)['state'], last_state(page)['reason']) == ('off', 'user')
    assert page.evaluate('() => __link.connect()') is True
    assert page.evaluate('() => FakeRadio.choosers') == 2
    assert page.evaluate('() => FakeRadio.connected()') is True


def test_hung_gatt_connect_times_out(page, app_url):
    boot(page, app_url, clock=True)
    radio.hold(page, 'gatt')   # never released
    start_connect(page)
    page.wait_for_function('FakeRadio.connects === 1')
    page.clock.run_for(59_000)   # connecting and pairing (a PIN typed by hand) get 60 s
    assert page.evaluate('() => [__link.state(), window.__res]') == ['connecting', None]
    page.clock.run_for(1_500)
    page.wait_for_function('window.__res === false')
    assert (last_state(page)['state'], last_state(page)['reason']) == ('off', 'failed')


# ---------- Final fix round: one GATT queue (P2), start-up timers (P5), nonces (P9), heartbeat (P12) ----------

def test_reads_and_writes_never_overlap(page, app_url):
    """Android rejects a GATT operation while another is running: reads (the drain) and writes (sends) share one queue."""
    connected(page, app_url)
    radio.strict_gatt(page)
    radio.slow_writes(page, 20)
    page.evaluate("""() => { window.__sends = [0, 1, 2, 3, 4, 5].map(i => __link.send(Uint8Array.of(0x42, i))); }""")
    for i in range(1, 7):
        radio.push(page, text_packet(i))
    page.wait_for_function('window.__msgs.filter(m => m.type === "packet").length >= 6')
    assert page.evaluate('() => Promise.all(window.__sends)') == [True] * 6
    assert page.evaluate('() => [FakeRadio.rejected, FakeRadio.maxOps, __link.state()]') == [0, 1, 'on']
    assert packet_ids(page) == [1, 2, 3, 4, 5, 6]


def test_one_failed_read_is_retried(page, app_url):
    connected(page, app_url)
    radio.fail_once(page, 'read')
    radio.push(page, text_packet(5))
    page.wait_for_function('window.__msgs.some(m => m.type === "packet")')
    assert packet_ids(page) == [5]
    assert page.evaluate('() => __link.state()') == 'on'
    assert page.evaluate(STATES) == ['connecting', 'syncing', 'on']   # never 'lost'


def test_one_failed_write_is_retried(page, app_url):
    connected(page, app_url)
    radio.fail_once(page, 'write')
    assert page.evaluate('() => __link.send(Uint8Array.of(0x42, 9))') is True
    assert radio.sent(page)[-1] == bytes([0x42, 9])
    assert page.evaluate('() => __link.state()') == 'on'


def test_two_failed_reads_lose_the_link(page, app_url):
    connected(page, app_url)
    radio.fail_once(page, 'read', times=2)
    radio.notify(page)
    page.wait_for_function('__link.state() === "lost"', timeout=5000)


def test_big_node_database_at_bluetooth_speed_reaches_on(page, app_url):
    """250 nodes at 50-150 ms a read take longer than 30 s in all: the start-up timer counts silence, not the whole download."""
    boot(page, app_url, script=radio.realistic_script(nodes=radio.node_db(250)), clock=True)
    radio.slow_reads(page, 90, 150)   # within the 50-150 ms a read takes on a phone, slow end
    start_connect(page)
    page.wait_for_function('__link.state() === "syncing"')
    t0 = page.evaluate('() => Date.now()')
    for _ in range(80):   # 80 s of page time, a second at a time
        page.clock.run_for(1000)
        if page.evaluate('() => window.__res') is not None:
            break
    assert page.evaluate('() => window.__res') is True
    assert page.evaluate('() => Date.now()') - t0 > 30_000   # longer than the old 30 s for the whole download
    assert page.evaluate('() => window.__msgs.filter(m => m.type === "nodeInfo").length') == 250


def test_start_up_silence_of_30_s_still_fails(page, app_url):
    boot(page, app_url, complete=False, clock=True)
    start_connect(page)
    page.wait_for_function('__link.state() === "syncing"')
    page.wait_for_function('window.__msgs.length === 5')
    page.clock.run_for(29_000)
    assert page.evaluate('() => window.__res') is None
    radio.push(page, text_packet(3))   # a message: the silence starts again
    page.wait_for_function('window.__msgs.length === 6')
    page.clock.run_for(29_000)
    assert page.evaluate('() => [__link.state(), window.__res]') == ['syncing', None]
    page.clock.run_for(1_500)
    page.wait_for_function('window.__res === false')
    assert (last_state(page)['state'], last_state(page)['reason']) == ('off', 'failed')


def test_pairing_pin_may_take_40_s(page, app_url):
    """startNotifications waits while Android asks for the radio's PIN."""
    boot(page, app_url, clock=True)
    radio.slow_notifications(page, 40_000)
    start_connect(page)
    page.wait_for_function('FakeRadio.connects === 1')
    for _ in range(45):
        page.clock.run_for(1000)
    page.wait_for_function('window.__res !== undefined')
    assert page.evaluate('() => window.__res') is True


def test_nonce_is_never_a_special_value(page, app_url):
    """69420 and 69421 ask current firmware for config only / nodes only; 0 is no request."""
    boot(page, app_url)
    page.evaluate("""() => { const vals = [69419.5 / 0xFFFFFFFE, 69420.5 / 0xFFFFFFFE, 0.25];
      let i = 0; const real = Math.random; Math.random = () => i < vals.length ? vals[i++] : real(); }""")
    assert page.evaluate('() => __link.connect()') is True
    nonce = meshref.mesh_pb2.ToRadio.FromString(radio.sent(page)[0]).want_config_id
    assert nonce not in (0, 69420, 69421)


def test_heartbeat_carries_nonce_0(page, app_url):
    """Heartbeat.nonce 1 would make the radio broadcast its NodeInfo: ours is always 0 (absent)."""
    connected(page, app_url, clock=True)
    page.clock.run_for(300_500)
    page.wait_for_function('FakeRadio.sent.length === 2')
    tr = meshref.mesh_pb2.ToRadio.FromString(radio.sent(page)[1])
    assert tr.HasField('heartbeat') and tr.heartbeat.nonce == 0


def test_stale_config_complete_during_resync_is_ignored(page, app_url):
    """After a reboot the radio may first end the earlier download: only our new nonce ends the new one."""
    connected(page, app_url, stale_complete=True)
    radio.reboot(page)
    page.wait_for_function('FakeRadio.nonces.length === 2')
    page.wait_for_function('window.__states.filter(s => s.state === "on").length === 2')
    st = page.evaluate('() => window.__states')
    second_on = [i for i, x in enumerate(st) if x['state'] == 'on'][1]
    assert st[second_on]['seen'] == len(page.evaluate(TYPES))   # 'on' came after every message of the new download
    assert page.evaluate(TYPES)[-1] == 'configComplete'
