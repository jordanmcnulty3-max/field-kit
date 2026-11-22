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


def boot(page, app_url, script=None, complete=True, clock=False):
    radio.install(page, script=script, complete=complete)
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
