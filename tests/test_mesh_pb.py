"""MPB: the Meshtastic byte codec, checked against the official Python package (tests/meshref.py).
Field numbers and wire types are recorded in docs/content-review.md (Comms)."""
import random

import pytest

from . import meshref
from .meshref import channel_pb2, mesh_pb2

ARRAYS = 'v => v instanceof Uint8Array ? Array.from(v) : (v && typeof v === "object" ? Object.fromEntries(Object.entries(v).map(([k, x]) => [k, ARRAYS(x)])) : v)'
RUN = f"""([path, arg]) => {{
  const ARRAYS = {ARRAYS};
  if (arg && !Array.isArray(arg) && typeof arg === 'object' && arg.payload) arg.payload = Uint8Array.from(arg.payload);
  const fn = path.split('.').reduce((o, k) => o[k], MPB);
  const r = Array.isArray(arg) ? fn(Uint8Array.from(arg)) : fn(arg);
  return ARRAYS(r);
}}"""


@pytest.fixture
def ready(page, app_url):
    page.goto(app_url)
    page.wait_for_function('typeof MPB !== "undefined"')
    return page


def enc(page, name, arg=None):
    return bytes(page.evaluate(RUN, ['enc.' + name, arg]))


def dec(page, name, data):
    return page.evaluate(RUN, ['dec.' + name, list(data)])


def test_waypoint_round_trip_matches_reference(ready):
    page = ready
    # ours -> reference decodes the same values
    b = enc(page, 'waypoint', dict(id=305419896, lat=43.0125, lon=-76.0375, expire=0, lockedTo=0,
                                   name='Rally 1', description='Seen 22 Nov 14:32. gate', icon=0x1F6A9))
    w = mesh_pb2.Waypoint()
    w.ParseFromString(b)
    assert (w.id, w.latitude_i, w.longitude_i, w.name, w.icon) == (305419896, 430125000, -760375000, 'Rally 1', 0x1F6A9)
    assert w.description == 'Seen 22 Nov 14:32. gate'
    assert b == w.SerializeToString()
    # reference -> ours decodes the same values
    got = dec(page, 'waypoint', w.SerializeToString())
    assert got['lat'] == pytest.approx(43.0125, abs=1e-7) and got['lon'] == pytest.approx(-76.0375, abs=1e-7)
    assert (got['id'], got['name'], got['icon'], got['expire'], got['lockedTo']) == (305419896, 'Rally 1', 0x1F6A9, 0, 0)


def test_waypoint_utf8_and_expiry(ready):
    b = enc(ready, 'waypoint', dict(id=7, lat=43.0, lon=-76.0, expire=1766000000, lockedTo=4000000000,
                                    name='Café ⚑', description='日本', icon=0))
    w = mesh_pb2.Waypoint()
    w.ParseFromString(b)
    assert (w.name, w.description, w.expire, w.locked_to) == ('Café ⚑', '日本', 1766000000, 4000000000)
    got = dec(ready, 'waypoint', meshref.waypoint_bytes(id=7, lat=43.0, lon=-76.0, name='Café ⚑', description='日本',
                                                        expire=1766000000, locked_to=4000000000))
    assert (got['name'], got['description'], got['expire'], got['lockedTo']) == ('Café ⚑', '日本', 1766000000, 4000000000)


def test_from_radio_every_type_matches_reference(ready):
    page = ready
    P = meshref.PORT
    assert dec(page, 'fromRadio', meshref.ref_from_radio(my_node_num=3000000001)) == {'type': 'myInfo', 'myNodeNum': 3000000001}

    n = dec(page, 'fromRadio', meshref.ref_from_radio(node=dict(num=2864434397, long='Alpha One', short='AL1',
                                                                 pos=(43.0, -76.0, 120, 1766000000), last_heard=1766000100, channel=2)))
    assert n['type'] == 'nodeInfo' and (n['num'], n['longName'], n['shortName'], n['lastHeard'], n['channel']) == (2864434397, 'Alpha One', 'AL1', 1766000100, 2)
    assert n['position'] == {'lat': pytest.approx(43.0), 'lon': pytest.approx(-76.0), 'alt': 120, 'time': 1766000000}

    n = dec(page, 'fromRadio', meshref.ref_from_radio(node=dict(num=5, long='Bravo', short='BR')))
    assert n['position'] is None and n['longName'] == 'Bravo' and n['lastHeard'] == 0

    for psk in (b'\x01', bytes(range(16)), bytes(range(32))):
        for prec in (0, 13, 32):
            c = dec(page, 'fromRadio', meshref.ref_from_radio(channel=dict(
                index=1, role=channel_pb2.Channel.SECONDARY, name='Crew', psk=psk, precision=prec)))
            assert c == {'type': 'channel', 'index': 1, 'role': 'secondary', 'name': 'Crew', 'psk': list(psk), 'positionPrecision': prec}
    c = dec(page, 'fromRadio', meshref.ref_from_radio(channel=dict(index=0, role=channel_pb2.Channel.PRIMARY, name='', psk=b'\x01')))
    assert (c['index'], c['role'], c['name'], c['psk']) == (0, 'primary', '', [1])
    c = dec(page, 'fromRadio', meshref.ref_from_radio(channel=dict(index=3, role=channel_pb2.Channel.DISABLED)))
    assert (c['index'], c['role'], c['psk']) == (3, 'disabled', [])

    assert dec(page, 'fromRadio', meshref.ref_from_radio(config_complete=123456)) == {'type': 'configComplete', 'id': 123456}
    assert dec(page, 'fromRadio', meshref.ref_from_radio(rebooted=True)) == {'type': 'rebooted'}

    pos = meshref.position_bytes(43.0, -76.0, 5, 1766000000)
    for port, payload in ((P['POSITION'], pos), (P['NODEINFO'], meshref.user_bytes('Alpha', 'A')),
                          (P['WAYPOINT'], meshref.waypoint_bytes(id=9, lat=43.0, lon=-76.0, name='w')), (P['TEXT'], 'hi'.encode())):
        m = dec(page, 'fromRadio', meshref.ref_from_radio(packet=meshref.mesh_packet(
            frm=3000000000, to=0xFFFFFFFF, channel=1, id=4000000000, rx_time=1766000000, portnum=port, payload=payload)))
        assert m == {'type': 'packet', 'from': 3000000000, 'to': 0xFFFFFFFF, 'channel': 1, 'id': 4000000000,
                     'rxTime': 1766000000, 'portnum': port, 'payload': list(payload)}
    m = dec(page, 'fromRadio', meshref.ref_from_radio(packet=meshref.mesh_packet(frm=7, to=8, id=9, encrypted=b'\xde\xad\xbe\xef')))
    assert (m['type'], m['from'], m['to'], m['portnum'], m['payload']) == ('packet', 7, 8, None, None)

    assert dec(page, 'fromRadio', mesh_pb2.FromRadio(id=5, queueStatus=mesh_pb2.QueueStatus(free=3)).SerializeToString()) == {'type': 'other'}
    assert dec(page, 'fromRadio', b'') == {'type': 'other'}

    assert dec(page, 'position', pos) == {'lat': pytest.approx(43.0), 'lon': pytest.approx(-76.0), 'alt': 5, 'time': 1766000000}
    assert dec(page, 'user', meshref.user_bytes('Alpha', 'A')) == {'longName': 'Alpha', 'shortName': 'A'}


def test_to_radio_matches_reference(ready):
    page = ready
    assert enc(page, 'wantConfig', 69420) == meshref.ref_want_config(69420)
    assert enc(page, 'wantConfig', 4294967295) == meshref.ref_want_config(4294967295)
    assert enc(page, 'heartbeat') == meshref.ref_heartbeat()
    pl = 'hello'.encode()
    got = enc(page, 'packet', dict(to=0xFFFFFFFF, channel=0, id=305419896, portnum=1, payload=list(pl)))
    assert got == meshref.ref_to_radio_packet(0xFFFFFFFF, 0, 305419896, 1, pl)
    got = enc(page, 'packet', dict(to=3000000000, channel=2, id=4000000000, portnum=8, payload=list(b'\x00' * 200),
                                   wantAck=True, hopLimit=3))
    assert got == meshref.ref_to_radio_packet(3000000000, 2, 4000000000, 8, b'\x00' * 200, True, 3)
    tr = mesh_pb2.ToRadio()
    tr.ParseFromString(got)
    assert (tr.packet.to, tr.packet.id, tr.packet.want_ack, tr.packet.hop_limit) == (3000000000, 4000000000, True, 3)


def test_negative_and_large_values(ready):
    page = ready
    p = dec(page, 'position', meshref.position_bytes(-43.0, -76.0, -12, 4000000000))
    assert p['lat'] == pytest.approx(-43.0, abs=1e-7) and p['lon'] == pytest.approx(-76.0, abs=1e-7)
    assert p['alt'] == -12 and p['time'] == 4000000000
    # negative int32 altitude is a 10-byte varint on the wire: the reference writes it, we must read it
    assert len(meshref.position_bytes(43.0, 76.0, -12)) > len(meshref.position_bytes(43.0, 76.0, 12)) + 5
    w = dec(page, 'waypoint', meshref.waypoint_bytes(id=4294967295, lat=-43.0, lon=-76.0, locked_to=3999999999, icon=0xFFFFFFFF))
    assert (w['id'], w['lockedTo'], w['icon']) == (4294967295, 3999999999, 0xFFFFFFFF)
    assert (w['lat'], w['lon']) == (pytest.approx(-43.0, abs=1e-7), pytest.approx(-76.0, abs=1e-7))
    n = dec(page, 'fromRadio', meshref.ref_from_radio(node=dict(num=4294967295, long='x', short='y', pos=(-43.0, -76.0, -12, 1), last_heard=4294967295)))
    assert (n['num'], n['lastHeard'], n['position']['alt']) == (4294967295, 4294967295, -12)
    m = dec(page, 'fromRadio', meshref.ref_from_radio(my_node_num=2147483649))
    assert m['myNodeNum'] == 2147483649
    # a channel index sent as a negative int32 keeps its sign
    c = dec(page, 'fromRadio', meshref.ref_from_radio(channel=dict(index=-1, role=channel_pb2.Channel.PRIMARY)))
    assert c['index'] == -1
    # a varint that uses all 64 bits (-1 as int64) is read without error, low 32 bits kept
    assert dec(page, 'position', bytes([0x18] + [0xff] * 9 + [0x01, 0x08, 0x01, 0x10, 0x01]))['alt'] == -1
    # written ids above 2**31 survive as unsigned fixed32
    got = enc(page, 'waypoint', dict(id=4294967295, lat=-43.0, lon=-76.0, icon=0x80000000))
    w = mesh_pb2.Waypoint()
    w.ParseFromString(got)
    assert (w.id, w.latitude_i, w.longitude_i, w.icon) == (4294967295, -430000000, -760000000, 0x80000000)


def _extra_fields():
    # field 999 of each wire type: varint, fixed64, length-delimited, fixed32, and a (deprecated) group
    key = lambda wt: bytes([(999 << 3 | wt) & 0x7f | 0x80, (999 << 3 | wt) >> 7])
    return [key(0) + b'\x96\x01', key(1) + bytes(8), key(2) + b'\x03abc', key(5) + bytes(4), key(3) + b'\x08\x01' + key(4)]


def test_unknown_fields_are_skipped(ready):
    page = ready
    base = {
        'fromRadio': meshref.ref_from_radio(node=dict(num=11, long='Alpha', short='A', pos=(43.0, -76.0, 3, 9), last_heard=5)),
        'waypoint': meshref.waypoint_bytes(id=3, lat=43.0, lon=-76.0, name='n', icon=5),
        'position': meshref.position_bytes(43.0, -76.0, 3, 9),
    }
    for name, b in base.items():
        want = dec(page, name, b)
        assert want is not None
        for extra in _extra_fields():
            assert dec(page, name, extra + b) == want, (name, extra)
            assert dec(page, name, b + extra) == want, (name, extra)
    # inside nested messages as well
    inner = meshref.ref_from_radio(packet=meshref.mesh_packet(frm=1, to=2, id=3, portnum=3, payload=base['position']))
    want = dec(page, 'fromRadio', inner)
    assert want['type'] == 'packet'
    fr = mesh_pb2.FromRadio()
    fr.ParseFromString(inner)
    for extra in _extra_fields():
        fr.packet.decoded.SetInParent()
        nested = fr.SerializeToString()
        # splice the extra field into the Data message by rebuilding it with the reference's own bytes plus ours
        data = fr.packet.decoded.SerializeToString() + extra
        mp = mesh_pb2.MeshPacket(**{'from': 1}, to=2, id=3)
        mp_bytes = mp.SerializeToString() + bytes([0x22, len(data)]) + data
        assert dec(page, 'fromRadio', bytes([0x12, len(mp_bytes)]) + mp_bytes)['payload'] == want['payload'], extra
    # fields the codec does not know are not mistaken for known ones: field 12 as a varint on Position
    assert dec(page, 'position', base['position'] + bytes([12 << 3, 5]))['alt'] == 3


def test_garbage_never_throws(ready):
    page = ready
    valid = [
        meshref.ref_from_radio(node=dict(num=11, long='Alpha', short='A', pos=(43.0, -76.0, -3, 9), last_heard=5)),
        meshref.ref_from_radio(channel=dict(index=1, role=2, name='Crew', psk=bytes(range(16)), precision=13)),
        meshref.ref_from_radio(packet=meshref.mesh_packet(frm=1, to=2, id=3, portnum=8, payload=meshref.waypoint_bytes(id=3, lat=43.0, lon=-76.0, name='n'))),
        meshref.waypoint_bytes(id=3, lat=43.0, lon=-76.0, name='n', description='d', icon=5),
    ]
    rnd = random.Random(7)
    bufs = [b[:i] for b in valid for i in range(len(b) + 1)]
    bufs += [bytes(rnd.randrange(256) for _ in range(rnd.randrange(1, 80))) for _ in range(200)]
    bufs += [bytes([0x12, 0x80, 0x80, 0x80, 0x80, 0x08]),               # a length of 2**31
             bytes([0x12, 0x80, 0x80, 0x80, 0x80, 0x10]),               # a length of 2**32: its low 32 bits are 0
             bytes([0x12] + [0xff] * 10), bytes([0x08] + [0x80] * 12),  # over-long varints
             bytes([0x0b] * 50), bytes([0x0c]), bytes([0x0f, 0x0f])]    # groups: nested starts, a stray end, wire types 7
    res = page.evaluate("""(bufs) => {
      const bad = [];
      for (const a of bufs) {
        const u = Uint8Array.from(a);
        for (const f of ['fromRadio', 'position', 'user', 'waypoint']) {
          try { const r = MPB.dec[f](u); if (f === 'fromRadio' && (!r || typeof r.type !== 'string')) bad.push([f, 'shape', a]); }
          catch (e) { bad.push([f, String(e), a]); }
        }
      }
      return bad;
    }""", [list(b) for b in bufs])
    assert res == []
    # the over-long and oversized-length cases are rejected, not half-read
    assert dec(page, 'fromRadio', bytes([0x12, 0x80, 0x80, 0x80, 0x80, 0x10])) == {'type': 'other'}
    assert dec(page, 'position', bytes([0x08] + [0x80] * 12)) is None
    assert dec(page, 'waypoint', bytes([0x32, 0x80, 0x80, 0x80, 0x80, 0x08])) is None
