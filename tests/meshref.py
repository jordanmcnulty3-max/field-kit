"""Reference bytes for the Meshtastic codec tests, built with the official `meshtastic` Python package
(pip install meshtastic). The package is the authority for field numbers and wire types."""
import pytest

pytest.importorskip('meshtastic')
from meshtastic.protobuf import channel_pb2, mesh_pb2, portnums_pb2  # noqa: E402

PORT = {'TEXT': portnums_pb2.TEXT_MESSAGE_APP, 'POSITION': portnums_pb2.POSITION_APP,
        'NODEINFO': portnums_pb2.NODEINFO_APP, 'WAYPOINT': portnums_pb2.WAYPOINT_APP}
BROADCAST = 0xFFFFFFFF


def position_bytes(lat, lon, alt=None, time=None):
    p = mesh_pb2.Position(latitude_i=round(lat * 1e7), longitude_i=round(lon * 1e7))
    if alt is not None:
        p.altitude = alt
    if time is not None:
        p.time = time
    return p.SerializeToString()


def user_bytes(long_name, short_name):
    return mesh_pb2.User(id='!00000000', long_name=long_name, short_name=short_name).SerializeToString()


def waypoint_bytes(**kw):
    w = mesh_pb2.Waypoint(**{k: v for k, v in kw.items() if k not in ('lat', 'lon')})
    if 'lat' in kw:
        w.latitude_i = round(kw['lat'] * 1e7)
    if 'lon' in kw:
        w.longitude_i = round(kw['lon'] * 1e7)
    return w.SerializeToString()


def mesh_packet(frm=0, to=0, channel=0, id=0, rx_time=0, portnum=None, payload=b'', encrypted=None):
    mp = mesh_pb2.MeshPacket(**{'from': frm}, to=to, channel=channel, id=id, rx_time=rx_time)
    if encrypted is not None:
        mp.encrypted = encrypted
    elif portnum is not None:
        mp.decoded.portnum = portnum
        mp.decoded.payload = payload
    return mp


def ref_from_radio(**kw):
    """kw is exactly one of: my_node_num=, node=dict(num, long, short, pos=(lat, lon, alt, time)|None, last_heard, channel),
    channel=dict(index, role, name, psk, precision), config_complete=, rebooted=True, packet=mesh_packet(...)."""
    fr = mesh_pb2.FromRadio(id=1)
    if 'my_node_num' in kw:
        fr.my_info.my_node_num = kw['my_node_num']
    elif 'node' in kw:
        n = kw['node']
        fr.node_info.num = n['num']
        fr.node_info.user.long_name = n.get('long', '')
        fr.node_info.user.short_name = n.get('short', '')
        if n.get('pos'):
            lat, lon, alt, t = n['pos']
            fr.node_info.position.ParseFromString(position_bytes(lat, lon, alt, t))
        fr.node_info.last_heard = n.get('last_heard', 0)
        fr.node_info.channel = n.get('channel', 0)
    elif 'channel' in kw:
        c = kw['channel']
        fr.channel.index = c['index']
        fr.channel.role = c['role']
        fr.channel.settings.name = c.get('name', '')
        fr.channel.settings.psk = c.get('psk', b'')
        fr.channel.settings.module_settings.position_precision = c.get('precision', 0)
    elif 'config_complete' in kw:
        fr.config_complete_id = kw['config_complete']
    elif 'rebooted' in kw:
        fr.rebooted = True
    elif 'packet' in kw:
        fr.packet.CopyFrom(kw['packet'])
    return fr.SerializeToString()


def ref_want_config(nonce):
    return mesh_pb2.ToRadio(want_config_id=nonce).SerializeToString()


def ref_heartbeat():
    tr = mesh_pb2.ToRadio()
    tr.heartbeat.SetInParent()
    return tr.SerializeToString()


def ref_to_radio_packet(to, channel, id, portnum, payload, want_ack=False, hop_limit=0):
    tr = mesh_pb2.ToRadio()
    tr.packet.CopyFrom(mesh_pb2.MeshPacket(to=to, channel=channel, id=id, hop_limit=hop_limit, want_ack=want_ack))
    tr.packet.decoded.portnum = portnum
    tr.packet.decoded.payload = payload
    return tr.SerializeToString()
