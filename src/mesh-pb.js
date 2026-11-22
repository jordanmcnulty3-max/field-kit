/* ---------- MPB: the Meshtastic protobuf byte codec (just the messages Field Kit needs). Pure: no DOM, no FK. ----------
   Field numbers and wire types are recorded in docs/content-review.md (Comms). Decoders never throw: bad bytes give null,
   or { type: 'other' } from fromRadio. */
const MPB = (() => {
  const PORT = { TEXT: 1, POSITION: 3, NODEINFO: 4, WAYPOINT: 8 };
  const BROADCAST = 0xFFFFFFFF;
  const U = new TextEncoder(), D = new TextDecoder('utf-8');
  const EMPTY = new Uint8Array(0);

  /* ---- reader ---- */
  /* Walks every field of a message and returns { fieldNumber: value } (the last occurrence wins, as in protobuf). Values:
     varint -> its low 32 bits as an unsigned number (enough for every field used here, and a negative int32 sent as a
     10-byte varint keeps its low 32 bits; signed fields apply |0), fixed32 -> unsigned number, length-delimited ->
     Uint8Array view. Unknown fields are walked and skipped by wire type. `order`, if given, receives the field numbers in the order they appeared.
     Throws on truncation or a length past the end. */
  function parse(b, order) {
    const res = {}, n = b.length;
    let p = 0, hi = 0;
    const varint = () => {
      let lo = 0, h = 0;
      for (let i = 0; i < 10; i++) {
        if (p >= n) throw 0;
        const c = b[p++];
        if (i < 4) lo |= (c & 127) << (7 * i);
        else if (i === 4) { lo |= (c & 15) << 28; h = (c & 112) >> 4; }   // bits 32..34
        else if (i < 9) h |= (c & 127) << (7 * i - 32);                  // never read, only so hi===0 means "fits in 32 bits"
        else h |= c & 1;
        if (!(c & 128)) { hi = h; return lo >>> 0; }
      }
      throw 0;   // a varint longer than 10 bytes
    };
    const fixed32 = () => { if (p + 4 > n) throw 0; p += 4; return (b[p - 4] | b[p - 3] << 8 | b[p - 2] << 16 | b[p - 1] << 24) >>> 0; };
    let depth = 0;   // open groups being skipped (deprecated wire types 3 and 4; never sent by Meshtastic, skipped leniently)
    while (p < n) {
      const key = varint(), num = key >>> 3, wt = key & 7;
      let v;
      if (wt === 0) v = varint();
      else if (wt === 5) v = fixed32();
      else if (wt === 2) {
        const len = varint();
        if (hi !== 0 || len > n - p) throw 0;
        v = b.subarray(p, p + len); p += len;
      } else if (wt === 1) { if (p + 8 > n) throw 0; p += 8; continue; }
      else if (wt === 3) { depth++; continue; }
      else if (wt === 4) { if (!depth) throw 0; depth--; continue; }
      else throw 0;
      if (!depth && num > 0) { res[num] = v; if (order) order.push(num); }
    }
    if (depth) throw 0;
    return res;
  }
  const safe = (f) => (b) => { try { return f(b); } catch (e) { return null; } };
  const str = v => v ? D.decode(v) : '';
  const bytes = v => v ? v : EMPTY;
  const sgn = v => (v | 0);   // int32 / sfixed32 from the unsigned low 32 bits
  const u = v => v || 0;
  const deg = v => (v | 0) / 1e7;

  /* ---- writer ---- */
  /* A message is built as a plain array of numbers. Zero/absent scalars are left out (proto3), fields are written in
     ascending number order, so output is byte-for-byte what a reference serializer produces. */
  function wv(a, x) { x = Math.floor(x); while (x > 127) { a.push((x % 128) | 128); x = Math.floor(x / 128); } a.push(x); }
  const key = (a, num, wt) => wv(a, num * 8 + wt);
  function wVar(a, num, x) { if (x) { key(a, num, 0); wv(a, x < 0 ? x >>> 0 : x); } }
  function wFix(a, num, x) { if (x) { key(a, num, 5); const v = x | 0; a.push(v & 255, (v >> 8) & 255, (v >> 16) & 255, (v >>> 24) & 255); } }
  function wLen(a, num, bs) { if (bs && bs.length) { key(a, num, 2); wv(a, bs.length); for (let i = 0; i < bs.length; i++) a.push(bs[i]); } }
  const wStr = (a, num, s) => wLen(a, num, U.encode(s || ''));
  const wMsg = (a, num, m) => { key(a, num, 2); wv(a, m.length); for (let i = 0; i < m.length; i++) a.push(m[i]); };   // present even when empty
  const done = a => Uint8Array.from(a);

  const enc = {
    wantConfig(nonce) { const a = []; wVar(a, 3, nonce); return done(a); },
    heartbeat() { const a = []; wMsg(a, 7, []); return done(a); },
    /* A whole ToRadio carrying one MeshPacket with a decoded Data. */
    packet({ to, channel, id, portnum, payload, wantAck, hopLimit }) {
      const data = []; wVar(data, 1, portnum); wLen(data, 2, payload);
      const mp = []; wFix(mp, 2, to); wVar(mp, 3, channel); wMsg(mp, 4, data); wFix(mp, 6, id); wVar(mp, 9, hopLimit);
      if (wantAck) { key(mp, 10, 0); mp.push(1); }
      const a = []; wMsg(a, 1, mp); return done(a);
    },
    waypoint({ id, lat, lon, expire, lockedTo, name, description, icon }) {
      const a = [];
      wVar(a, 1, id); wFix(a, 2, Math.round(lat * 1e7)); wFix(a, 3, Math.round(lon * 1e7)); wVar(a, 4, expire); wVar(a, 5, lockedTo);
      wStr(a, 6, name); wStr(a, 7, description); wFix(a, 8, icon);
      return done(a);
    },
  };

  /* ---- decoders ---- */
  const position = safe(b => {
    const f = parse(b);
    if (f[1] === undefined && f[2] === undefined) return null;   // no fix
    return { lat: deg(f[1]), lon: deg(f[2]), alt: sgn(f[3]), time: u(f[4]) };
  });
  const user = safe(b => { const f = parse(b); return { longName: str(f[2]), shortName: str(f[3]) }; });
  const waypoint = safe(b => {
    const f = parse(b);
    return { id: u(f[1]), lat: deg(f[2]), lon: deg(f[3]), expire: u(f[4]), lockedTo: u(f[5]), name: str(f[6]), description: str(f[7]), icon: u(f[8]) };
  });

  function packet(b) {
    const f = parse(b), m = { type: 'packet', from: u(f[1]), to: u(f[2]), channel: u(f[3]), id: u(f[6]), rxTime: u(f[7]), portnum: null, payload: null };
    if (f[4]) { const d = parse(f[4]); m.portnum = u(d[1]); m.payload = bytes(d[2]); }   // else still encrypted (field 5)
    return m;
  }
  function nodeInfo(b) {
    const f = parse(b), us = f[2] ? user(f[2]) : null;
    return { type: 'nodeInfo', num: u(f[1]), longName: us ? us.longName : '', shortName: us ? us.shortName : '',
             position: f[3] ? position(f[3]) : null, lastHeard: u(f[5]), channel: u(f[7]) };
  }
  function channel(b) {
    const f = parse(b), s = f[2] ? parse(f[2]) : {}, ms = s[7] ? parse(s[7]) : {};
    return { type: 'channel', index: sgn(f[1]), role: f[3] === 1 ? 'primary' : f[3] === 2 ? 'secondary' : 'disabled',
             name: str(s[3]), psk: bytes(s[2]), positionPrecision: u(ms[1]) };
  }

  const fromRadio = (b) => {
    try {
      const order = [], f = parse(b, order);
      let last = 0;   // the FromRadio payload is a oneof: the last member present wins
      for (const k of order) if (k === 2 || k === 3 || k === 4 || k === 7 || k === 8 || k === 10) last = k;
      switch (last) {
        case 2: return packet(f[2]);
        case 3: return { type: 'myInfo', myNodeNum: u(parse(f[3])[1]) };
        case 4: return nodeInfo(f[4]);
        case 7: return { type: 'configComplete', id: f[7] };
        case 8: return { type: 'rebooted' };
        case 10: return channel(f[10]);
      }
    } catch (e) { /* fall through */ }
    return { type: 'other' };
  };

  return { PORT, BROADCAST, enc, dec: { fromRadio, position, user, waypoint } };
})();
