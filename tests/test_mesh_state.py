"""FK.mesh: the Settings switch, the channel verdict, teammates' data and sending a marker, against the scripted fake radio."""
import json

from . import meshref, radio

R = meshref.ref_from_radio
BC = meshref.BROADCAST
ME, BRAVO, CHARLIE, DELTA = radio.MY_NUM, 0x0A0B0C02, 0x0A0B0C03, 0x0A0B0C04
PRIV = bytes(range(1, 17))


def boot(page, app_url, on=True, script=None, complete=True):
    radio.install(page, script=script, complete=complete)
    page.goto(app_url)
    page.wait_for_function('window.FK && FK.mesh')
    if on:
        page.evaluate('() => FK.mesh.setEnabled(true)')
    return page


def connected(page, app_url, **kw):
    boot(page, app_url, **kw)
    assert page.evaluate('() => FK.mesh.connect()') is True
    return page


def watch(page):
    """Count bus events from now on: window.__ev = { mesh, team, meshWaypoint: [details] }."""
    page.evaluate("""() => { window.__ev = { mesh: [], team: [], meshWaypoint: [] };
      for (const k of Object.keys(window.__ev)) FK.on(k, d => window.__ev[k].push(d === undefined ? null : d)); }""")


def events(page, k):
    return page.evaluate('k => window.__ev[k]', k)


def chan(page, role='primary', psk=b'', precision=0, index=0):
    page.evaluate('m => { m.psk = Uint8Array.from(m.psk); FK._test.mesh.feed(m); }',
                  dict(type='channel', index=index, role=role, name='', psk=list(psk), positionPrecision=precision))


def feed(page, msg):
    page.evaluate('m => FK._test.mesh.feed(m)', msg)


def node(num, long='', short='', pos=None, heard=0, channel=0):
    return dict(type='nodeInfo', num=num, longName=long, shortName=short, position=pos, lastHeard=heard, channel=channel)


def pkt(frm, portnum, payload, channel=0):
    return dict(type='packet', **{'from': frm}, to=BC, channel=channel, id=7, rxTime=0, portnum=portnum,
                payload=list(payload))


def feed_packet(page, frm, portnum, payload, channel=0):
    page.evaluate('m => { m.payload = Uint8Array.from(m.payload); FK._test.mesh.feed(m); }', pkt(frm, portnum, payload, channel))


def team(page):
    return {t['num']: t for t in page.evaluate('() => FK.mesh.teammates()')}


def open_menu(page):
    page.click('#menuBtn')
    page.wait_for_selector('#dlgMenu[open]')


def test_switch_off_by_default_and_nothing_shows(page, app_url):
    boot(page, app_url, on=False)
    assert page.evaluate('() => FK.mesh.enabled()') is False
    assert page.evaluate('() => FK.mesh.status()')['state'] == 'off'
    assert page.evaluate('() => [FK.mesh.channel(), FK.mesh.positions(), FK.mesh.canShare(), FK.mesh.supported()]') == \
        ['unknown', 'unknown', False, False]
    assert page.evaluate('() => FK.mesh.teammates()') == []
    assert page.evaluate('() => FK.mesh.connect()') is False
    assert page.evaluate('() => FakeRadio.choosers') == 0
    open_menu(page)
    assert page.is_visible('#meshOn') and not page.is_checked('#meshOn')
    assert 'Radio link (testing)' in page.inner_text('#dlgMenu')
    assert 'Connects Field Kit to a Meshtastic radio over Bluetooth. Android only.' in page.inner_text('#dlgMenu')
    assert page.evaluate("() => localStorage.getItem('fk.meshOn')") is None


def test_switch_off_never_touches_bluetooth(page, app_url):
    page.add_init_script("""window.__btReads = 0;
      Object.defineProperty(navigator, 'bluetooth', { configurable: true, get() { window.__btReads++; throw new Error('touched'); } });""")
    page.goto(app_url)
    page.wait_for_function('window.FK && FK.mesh')
    page.evaluate("""async () => { const m = FK.mesh; m.status(); m.supported(); m.channel(); m.canShare(); m.teammates();
      await m.connect(); await m.reconnect(); m.disconnect(); await m.sendWaypoint({ lat: 43, lon: -76, name: 'x' });
      document.dispatchEvent(new Event('visibilitychange')); }""")
    open_menu(page)
    page.click('#menuClose')
    assert page.evaluate('() => window.__btReads') == 0


def test_switch_turns_on_and_off_and_off_disconnects(page, app_url):
    boot(page, app_url, on=False)
    open_menu(page)
    page.check('#meshOn')
    assert page.evaluate('() => FK.mesh.enabled()') is True
    assert page.evaluate("() => localStorage.getItem('fk.meshOn')") == 'true'
    assert page.evaluate('() => FK.mesh.connect()') is True
    assert page.evaluate('() => FK.mesh.status().state') == 'on'
    page.uncheck('#meshOn')
    assert page.evaluate('() => FK.mesh.enabled()') is False
    assert page.evaluate('() => FakeRadio.connected()') is False
    assert page.evaluate('() => FK.mesh.status()')['state'] == 'off'
    assert page.evaluate('() => FK.mesh.canShare()') is False
    # on again: no automatic reconnect, the user's tap does it
    page.check('#meshOn')
    page.wait_for_timeout(200)
    assert page.evaluate('() => [FK.mesh.status().state, FakeRadio.connected(), FakeRadio.choosers]') == ['off', False, 1]
    page.evaluate("() => document.dispatchEvent(new Event('visibilitychange'))")
    page.wait_for_timeout(200)
    assert page.evaluate('() => FakeRadio.connects') == 1


def test_private_channel_verdict(page, app_url):
    connected(page, app_url)   # the default radio: a 32-byte key, positions at full precision
    assert page.evaluate('() => [FK.mesh.channel(), FK.mesh.positions(), FK.mesh.canShare()]') == ['private', 'precise', True]
    page.evaluate('() => FK._test.mesh.link("syncing", "")')
    assert page.evaluate('() => FK.mesh.channel()') == 'unknown'   # each start-up download decides afresh
    chan(page, psk=PRIV, precision=13)   # 16 bytes
    assert page.evaluate('() => [FK.mesh.channel(), FK.mesh.positions()]') == ['private', 'approx']
    # the key itself is nowhere: not in storage, not on FK
    blob = page.evaluate("() => JSON.stringify(Object.assign({}, localStorage)) + Object.keys(FK).join() + Object.keys(FK.mesh).join()")
    assert '1,2,3,4' not in blob and 'psk' not in blob


def test_public_channel_verdict(page, app_url):
    boot(page, app_url)
    chan(page, psk=b'')
    assert page.evaluate('() => FK.mesh.channel()') == 'public'
    chan(page, psk=b'\x01')
    assert page.evaluate('() => FK.mesh.channel()') == 'public'
    chan(page, psk=bytes(range(1, 25)))   # a key length that is neither well-known nor valid: not private either
    assert page.evaluate('() => FK.mesh.channel()') == 'unknown'
    chan(page, psk=bytes(range(1, 33)))
    assert page.evaluate('() => FK.mesh.channel()') == 'private'


def test_secondary_private_does_not_count(page, app_url):
    boot(page, app_url)
    chan(page, role='secondary', psk=PRIV, precision=32, index=1)
    assert page.evaluate('() => [FK.mesh.channel(), FK.mesh.positions()]') == ['unknown', 'unknown']
    chan(page, psk=b'', precision=0)
    chan(page, role='secondary', psk=PRIV, precision=32, index=1)
    chan(page, role='disabled', psk=PRIV, precision=32, index=2)
    assert page.evaluate('() => [FK.mesh.channel(), FK.mesh.positions(), FK.mesh.canShare()]') == ['public', 'off', False]


def test_position_verdicts(page, app_url):
    boot(page, app_url)
    for precision, want in ((32, 'precise'), (0, 'off'), (13, 'approx'), (11, 'approx'), (31, 'approx')):
        chan(page, psk=PRIV, precision=precision)
        assert page.evaluate('() => FK.mesh.positions()') == want, precision


def test_teammates_from_download_and_live_packets(page, app_url):
    boot(page, app_url)
    watch(page)
    assert page.evaluate('() => FK.mesh.connect()') is True
    t = team(page)
    assert set(t) == {BRAVO, CHARLIE}   # Alpha is this phone's own radio
    assert page.evaluate('() => FK.mesh.myNum()') == ME
    b = t[BRAVO]
    assert (b['name'], b['lat'], b['lon'], b['t'], b['heard']) == ('Bravo', 43.01, -76.01, 1766000100000, 1766000100000)
    c = t[CHARLIE]
    assert (c['name'], c['lat'], c['lon'], c['t'], c['heard']) == ('Charlie', None, None, 0, 1766000200000)
    assert len(events(page, 'team')) >= 2 and events(page, 'mesh')
    # live: a position for Charlie, then a name for a new radio, then a name-less radio
    n = len(events(page, 'team'))
    radio.push(page, R(packet=meshref.mesh_packet(frm=CHARLIE, to=BC, id=9, portnum=meshref.PORT['POSITION'],
                                                  payload=meshref.position_bytes(43.0, -76.0, 5, 1766000300))))
    page.wait_for_function('() => FK.mesh.teammates().find(t => t.num === %d).lat === 43' % CHARLIE)
    c = team(page)[CHARLIE]
    assert (c['lon'], c['t']) == (-76.0, 1766000300000) and c['heard'] > 1766000200000
    assert len(events(page, 'team')) == n + 1
    radio.push(page, R(packet=meshref.mesh_packet(frm=DELTA, to=BC, id=10, portnum=meshref.PORT['NODEINFO'],
                                                  payload=meshref.user_bytes('Delta', 'DLT'))))
    page.wait_for_function('() => FK.mesh.teammates().length === 3')
    d = team(page)[DELTA]
    assert (d['name'], d['lat'], d['t']) == ('Delta', None, 0)
    assert page.evaluate('n => FK.mesh.nameOf(n)', DELTA) == 'Delta'
    # name falls back: short name, then the last four hex digits of the number
    feed(page, node(0x0A0B0CAB, short='ZED'))
    feed(page, node(0x0A0B0CEF))
    assert page.evaluate('() => [FK.mesh.nameOf(0x0A0B0CAB), FK.mesh.nameOf(0x0A0B0CEF), FK.mesh.nameOf(0x0A0B1234)]') == \
        ['ZED', 'Radio 0cef', 'Radio 1234']
    # a node entry with no position later never wipes a position already known
    feed(page, node(BRAVO, long='Bravo', pos=None, heard=1766000500))
    assert (team(page)[BRAVO]['lat'], team(page)[BRAVO]['heard']) == (43.01, 1766000500000)


def test_own_radio_is_not_a_teammate(page, app_url):
    connected(page, app_url)
    assert ME not in team(page)
    feed_packet(page, ME, meshref.PORT['POSITION'], meshref.position_bytes(43.0, -76.0, 0, 1766000300))
    feed(page, node(ME, long='Alpha', pos=dict(lat=43.0, lon=-76.0, alt=0, time=1766000000), heard=1766000000))
    assert ME not in team(page)
    assert page.evaluate('() => FK.mesh.nameOf(FK.mesh.myNum())') == 'Alpha'
    # a radio that was a teammate and becomes this phone's own leaves the list
    feed(page, dict(type='myInfo', myNodeNum=BRAVO))
    assert BRAVO not in team(page) and page.evaluate('() => FK.mesh.myNum()') == BRAVO


def test_channel_1_nodes_are_not_teammates(page, app_url):
    connected(page, app_url)
    feed(page, node(DELTA, long='Delta', pos=dict(lat=43.0, lon=-76.0, alt=0, time=1), channel=1))
    feed_packet(page, DELTA, meshref.PORT['POSITION'], meshref.position_bytes(43.0, -76.0, 0, 5), channel=1)
    feed_packet(page, DELTA, meshref.PORT['NODEINFO'], meshref.user_bytes('Delta', 'DLT'), channel=2)
    assert DELTA not in team(page)


def test_zero_zero_position_ignored(page, app_url):
    connected(page, app_url)
    before = team(page)[BRAVO]
    watch(page)
    feed(page, node(BRAVO, long='Bravo', pos=dict(lat=0, lon=0, alt=0, time=1766000900), heard=0))
    feed(page, node(BRAVO, long='Bravo', pos=dict(lat=91, lon=0, alt=0, time=1766000900), heard=0))
    feed(page, node(BRAVO, long='Bravo', pos=dict(lat=10, lon=181, alt=0, time=1766000900), heard=0))
    assert team(page)[BRAVO] == before and events(page, 'team') == []
    feed(page, node(DELTA, long='Delta', pos=dict(lat=0, lon=0, alt=0, time=1766000900)))
    assert (team(page)[DELTA]['lat'], team(page)[DELTA]['lon'], team(page)[DELTA]['t']) == (None, None, 0)
    feed_packet(page, DELTA, meshref.PORT['POSITION'], meshref.position_bytes(95.0, 10.0, 0, 1766000900))
    assert team(page)[DELTA]['lat'] is None


def test_future_position_has_no_time(page, app_url):
    connected(page, app_url)
    now = page.evaluate('() => Date.now()') // 1000
    feed(page, node(DELTA, long='Delta', pos=dict(lat=43.0, lon=-76.0, alt=0, time=now + 2 * 86400)))
    d = team(page)[DELTA]
    assert (d['lat'], d['lon'], d['t']) == (43.0, -76.0, 0)   # the place is kept, the impossible time is not
    feed(page, node(DELTA, long='Delta', pos=dict(lat=43.0, lon=-76.0, alt=0, time=now + 3600)))
    assert team(page)[DELTA]['t'] == (now + 3600) * 1000      # an hour ahead is clock drift, kept


def test_public_channel_emits_nothing(page, app_url):
    connected(page, app_url)
    kept = team(page)
    chan(page, psk=b'\x01')   # the radio now reports the public channel
    watch(page)
    feed(page, node(DELTA, long='Delta', pos=dict(lat=43.0, lon=-76.0, alt=0, time=1766000000)))
    feed(page, node(BRAVO, long='Bravo2', pos=dict(lat=44.0, lon=-77.0, alt=0, time=1766000000)))
    feed_packet(page, DELTA, meshref.PORT['POSITION'], meshref.position_bytes(43.0, -76.0, 0, 1766000300))
    feed_packet(page, DELTA, meshref.PORT['NODEINFO'], meshref.user_bytes('Delta', 'DLT'))
    feed_packet(page, DELTA, meshref.PORT['WAYPOINT'], meshref.waypoint_bytes(id=5, lat=43.0, lon=-76.0, name='Rally'))
    assert events(page, 'team') == [] and events(page, 'meshWaypoint') == []
    assert team(page) == kept   # the list is kept as it was
    assert page.evaluate('() => FK.mesh.channel()') == 'public'


def test_waypoint_event_only_on_private_channel_zero(page, app_url):
    connected(page, app_url)
    watch(page)
    wp = meshref.waypoint_bytes(id=5, lat=43.0, lon=-76.0, name='Rally', description='north gate')
    feed_packet(page, BRAVO, meshref.PORT['WAYPOINT'], wp)
    feed_packet(page, BRAVO, meshref.PORT['WAYPOINT'], wp, channel=1)
    feed_packet(page, 0x0A0B0CCC, meshref.PORT['WAYPOINT'], wp)
    ev = events(page, 'meshWaypoint')
    assert len(ev) == 2
    assert ev[0]['from'] == BRAVO and ev[0]['name'] == 'Bravo' and ev[0]['wp']['name'] == 'Rally' and ev[0]['wp']['lat'] == 43.0
    assert ev[1]['name'] == 'Radio 0ccc'
    chan(page, psk=b'')
    feed_packet(page, BRAVO, meshref.PORT['WAYPOINT'], wp)
    assert len(events(page, 'meshWaypoint')) == 2


def test_teammates_survive_reload_and_are_not_in_a_backup(page, app_url, tmp_path):
    connected(page, app_url)
    before = page.evaluate('() => FK.mesh.teammates()')
    assert len(before) == 2
    open_menu(page)
    with page.expect_download() as d:
        page.click('#bkSave')
    path = tmp_path / 'b.json'
    d.value.save_as(path)
    data = json.loads(path.read_text())['data']
    assert 'fk.meshTeam' not in data and 'fk.meshMe' not in data and data.get('fk.meshOn') == 'true'
    assert page.evaluate("() => localStorage.getItem('fk.meshTeam')") is not None
    page.reload()
    page.wait_for_function('window.FK && FK.mesh')
    assert page.evaluate('() => FK.mesh.teammates()') == before
    assert page.evaluate('() => FK.mesh.myNum()') == ME         # known with no link
    assert page.evaluate('() => FK.mesh.status().state') == 'off'


def test_team_is_capped_and_drops_the_longest_silent(page, app_url):
    boot(page, app_url)
    chan(page, psk=PRIV)
    page.evaluate("""() => { for (let i = 1; i <= 100; i++) FK._test.mesh.feed({ type: 'nodeInfo', num: 5000 + i, longName: 'N' + i,
      shortName: '', position: null, lastHeard: 1000 + i, channel: 0 }); }""")
    assert page.evaluate('() => FK.mesh.teammates().length') == 100
    feed(page, node(9999, long='New', heard=5000))
    nums = [t['num'] for t in page.evaluate('() => FK.mesh.teammates()')]
    assert len(nums) == 100 and 5001 not in nums and 9999 in nums and 5002 in nums


def test_send_waypoint_refused_on_public_and_when_off(page, app_url):
    connected(page, app_url)
    n = len(radio.sent(page))
    chan(page, psk=b'')
    assert page.evaluate("() => FK.mesh.sendWaypoint({ lat: 43.0, lon: -76.0, name: 'Rally' })") is False
    page.evaluate('() => FK._test.mesh.link("syncing", "")')   # unknown while a download runs
    assert page.evaluate("() => FK.mesh.sendWaypoint({ lat: 43.0, lon: -76.0, name: 'Rally' })") is False
    assert len(radio.sent(page)) == n
    page.evaluate('() => FK.mesh.setEnabled(false)')
    assert page.evaluate("() => FK.mesh.sendWaypoint({ lat: 43.0, lon: -76.0, name: 'Rally' })") is False
    assert len(radio.sent(page)) == n


def test_send_waypoint_bytes_match_reference(page, app_url):
    from meshtastic.protobuf import mesh_pb2
    connected(page, app_url)
    assert page.evaluate("() => FK.mesh.canShare()") is True
    assert page.evaluate("() => FK.mesh.sendWaypoint({ lat: 43.01, lon: -76.01, name: 'Rally', description: 'north gate' })") is True
    tr = mesh_pb2.ToRadio.FromString(radio.sent(page)[-1])
    p = tr.packet
    assert p.to == BC and p.channel == 0 and p.decoded.portnum == meshref.PORT['WAYPOINT'] and p.id != 0
    w = mesh_pb2.Waypoint.FromString(p.decoded.payload)
    assert (w.name, w.description, w.latitude_i, w.longitude_i) == ('Rally', 'north gate', 430100000, -760100000) and w.id != 0
    # two sends never share a packet id
    page.evaluate("() => FK.mesh.sendWaypoint({ lat: 43.0, lon: -76.0, name: 'B', id: 77 })")
    q = mesh_pb2.ToRadio.FromString(radio.sent(page)[-1]).packet
    assert q.id not in (0, p.id) and mesh_pb2.Waypoint.FromString(q.decoded.payload).id == 77
    # a position that is not a place is not sent
    assert page.evaluate("() => FK.mesh.sendWaypoint({ lat: 200, lon: 0, name: 'bad' })") is False


def test_foreground_reconnects(page, app_url):
    connected(page, app_url)
    page.evaluate("() => document.dispatchEvent(new Event('visibilitychange'))")   # connected: nothing to do
    page.wait_for_timeout(150)
    assert page.evaluate('() => FakeRadio.connects') == 1
    radio.drop(page)
    page.wait_for_function('() => FK.mesh.status().state === "lost"')
    page.evaluate("() => document.dispatchEvent(new Event('visibilitychange'))")
    page.wait_for_function('() => FK.mesh.status().state === "on"')
    assert page.evaluate('() => [FakeRadio.connects, FakeRadio.choosers]') == [2, 1]   # the same radio, no chooser
    assert page.evaluate('() => FK.mesh.channel()') == 'private'


def test_foreground_does_nothing_when_switch_is_off(page, app_url):
    connected(page, app_url)
    radio.drop(page)
    page.wait_for_function('() => FK.mesh.status().state === "lost"')
    page.evaluate('() => FK.mesh.setEnabled(false)')
    page.evaluate("() => document.dispatchEvent(new Event('visibilitychange'))")
    page.wait_for_timeout(200)
    assert page.evaluate('() => [FakeRadio.connects, FK.mesh.status().state]') == [1, 'off']


WPB = meshref.waypoint_bytes(id=5, lat=43.0, lon=-76.0, name='Rally')


def early(page):
    """Two nodes, a position, and a waypoint, all before any channel message."""
    feed(page, node(BRAVO, long='Bravo', pos=dict(lat=43.01, lon=-76.01, alt=0, time=1766000100), heard=1766000100))
    feed(page, node(CHARLIE, long='Charlie', heard=1766000200))
    feed_packet(page, CHARLIE, meshref.PORT['POSITION'], meshref.position_bytes(43.0, -76.0, 0, 1766000300))
    feed_packet(page, BRAVO, meshref.PORT['WAYPOINT'], WPB)


def test_messages_before_the_channel_wait_for_a_private_verdict(page, app_url):
    boot(page, app_url)
    watch(page)
    early(page)
    assert page.evaluate('() => FK.mesh.teammates()') == [] and events(page, 'team') == [] and events(page, 'meshWaypoint') == []
    chan(page, psk=PRIV, precision=32)
    t = page.evaluate('() => FK.mesh.teammates()')
    assert [x['num'] for x in t] == [BRAVO, CHARLIE]
    assert team(page)[CHARLIE]['lat'] == 43.0 and team(page)[BRAVO]['name'] == 'Bravo'   # the position came after the node entry
    ev = events(page, 'meshWaypoint')
    assert len(ev) == 1 and ev[0]['from'] == BRAVO and ev[0]['name'] == 'Bravo'
    chan(page, psk=PRIV, precision=32)   # a repeat applies nothing twice
    assert len(events(page, 'meshWaypoint')) == 1


def test_messages_before_the_channel_are_dropped_on_a_public_verdict(page, app_url):
    boot(page, app_url)
    watch(page)
    early(page)
    chan(page, psk=b'')
    assert team(page) == {} and events(page, 'team') == [] and events(page, 'meshWaypoint') == []
    chan(page, psk=PRIV)   # nothing is left to apply later either
    assert team(page) == {} and events(page, 'meshWaypoint') == []


def test_download_ending_without_a_channel_applies_nothing(page, app_url):
    script = [R(my_node_num=ME),
              R(node=dict(num=BRAVO, long='Bravo', short='BRV', pos=(43.01, -76.01, 0, 1766000100), last_heard=1766000100))]
    boot(page, app_url, script=script)
    watch(page)
    assert page.evaluate('() => FK.mesh.connect()') is True
    assert page.evaluate('() => [FK.mesh.status().state, FK.mesh.channel()]') == ['on', 'unknown']
    assert team(page) == {} and events(page, 'team') == []
    chan(page, psk=PRIV)   # a verdict long after the download does not resurrect it
    assert team(page) == {} and page.evaluate('() => FK.mesh.canShare()') is True


def test_new_download_empties_what_is_waiting_but_keeps_the_stored_list(page, app_url):
    connected(page, app_url)
    kept = team(page)
    page.evaluate('() => FK._test.mesh.link("syncing", "")')
    assert team(page) == kept   # still on screen while the new download runs
    feed(page, node(DELTA, long='Delta', heard=5))
    page.evaluate('() => FK._test.mesh.link("syncing", "")')   # a second download starts
    chan(page, psk=PRIV)
    assert DELTA not in team(page) and team(page) == kept


def test_waiting_messages_are_capped_and_the_oldest_dropped(page, app_url):
    boot(page, app_url)
    watch(page)
    page.evaluate("""wp => { for (let i = 1; i <= 205; i++) FK._test.mesh.feed({ type: 'packet', from: 7000 + i, to: 0xFFFFFFFF, channel: 0, id: i,
      rxTime: 0, portnum: 8, payload: Uint8Array.from(wp) }); }""", list(WPB))
    chan(page, psk=PRIV)
    froms = [e['from'] for e in events(page, 'meshWaypoint')]
    assert len(froms) == 200 and froms[0] == 7006 and froms[-1] == 7205   # the newest 200, in order
