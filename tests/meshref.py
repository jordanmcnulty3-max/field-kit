"""Reference bytes for the Meshtastic codec tests, built with the official `meshtastic` Python package
(pip install meshtastic). The package is the authority for field numbers and wire types."""
import pytest

pytest.importorskip('meshtastic')
from meshtastic.protobuf import channel_pb2, config_pb2, mesh_pb2, portnums_pb2  # noqa: E402,F401

PORT = {'TEXT': portnums_pb2.TEXT_MESSAGE_APP, 'POSITION': portnums_pb2.POSITION_APP,
        'NODEINFO': portnums_pb2.NODEINFO_APP, 'WAYPOINT': portnums_pb2.WAYPOINT_APP}
BROADCAST = 0xFFFFFFFF


def position_bytes(lat, lon, alt=None, time=None, precision_bits=None):
    p = mesh_pb2.Position(latitude_i=round(lat * 1e7), longitude_i=round(lon * 1e7))
    if alt is not None:
        p.altitude = alt
    if time is not None:
        p.time = time
    if precision_bits is not None:
        p.precision_bits = precision_bits
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


def mesh_packet(frm=0, to=0, channel=0, id=0, rx_time=0, portnum=None, payload=b'', encrypted=None, pki_encrypted=False):
    mp = mesh_pb2.MeshPacket(**{'from': frm}, to=to, channel=channel, id=id, rx_time=rx_time, pki_encrypted=pki_encrypted)
    if encrypted is not None:
        mp.encrypted = encrypted
    elif portnum is not None:
        mp.decoded.portnum = portnum
        mp.decoded.payload = payload
    return mp


def ref_from_radio(**kw):
    """kw is exactly one of: my_node_num=, node=dict(num, long, short, pos=(lat, lon, alt, time)|None, last_heard, channel,
    via_mqtt, is_ignored, precision_bits), channel=dict(index, role, name, psk, precision), config_complete=, rebooted=True,
    packet=mesh_packet(...), lora=dict(hop_limit, region, tx_enabled) (FromRadio.config carrying Config.lora),
    device_config=True (FromRadio.config carrying another Config member), module_config=True, metadata=True,
    queue_status=True."""
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
            fr.node_info.position.ParseFromString(position_bytes(lat, lon, alt, t, n.get('precision_bits')))
        fr.node_info.last_heard = n.get('last_heard', 0)
        fr.node_info.channel = n.get('channel', 0)
        fr.node_info.via_mqtt = n.get('via_mqtt', False)
        fr.node_info.is_ignored = n.get('is_ignored', False)
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
    elif 'lora' in kw:
        lo = kw['lora']
        fr.config.lora.use_preset = True
        fr.config.lora.region = lo.get('region', 0)
        fr.config.lora.hop_limit = lo.get('hop_limit', 0)
        fr.config.lora.tx_enabled = lo.get('tx_enabled', True)
    elif 'device_config' in kw:
        fr.config.device.node_info_broadcast_secs = 10800
    elif 'module_config' in kw:
        fr.moduleConfig.telemetry.device_update_interval = 900
    elif 'metadata' in kw:
        fr.metadata.firmware_version = '2.7.11.0'
        fr.metadata.device_state_version = 24
    elif 'queue_status' in kw:
        fr.queueStatus.free = 16
        fr.queueStatus.maxlen = 16
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
