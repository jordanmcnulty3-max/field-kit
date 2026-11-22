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
    const res = {}, wts = {}, n = b.length;
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
      if (!depth && num > 0) { res[num] = v; wts[num] = wt; if (order) order.push(num); }
    }
    if (depth) throw 0;
    Object.defineProperty(res, 'wt', { value: wts });   // wire type of each field present, for the checked accessors
    return res;
  }
  const safe = (f) => (b) => { try { return f(b); } catch (e) { return null; } };
  /* Checked accessors: an absent field reads as its proto3 default, a field sent with the wrong wire type throws (so the
     decoder returns null / 'other' instead of a wrong-typed value). V varint, F fixed32, L length-delimited. */
  const chk = (f, k, wt) => { if (f[k] !== undefined && f.wt[k] !== wt) throw 0; return f[k]; };
  const V = (f, k) => chk(f, k, 0) || 0, F = (f, k) => chk(f, k, 5) || 0;
  const L = (f, k) => chk(f, k, 2);
  const str = (f, k) => { const v = L(f, k); return v ? D.decode(v) : ''; };
  const bytes = (f, k) => L(f, k) || EMPTY;
  const sgn = v => (v | 0);   // int32 / sfixed32 from the unsigned low 32 bits
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
  const NONE = parse(EMPTY);   // stands in for an absent nested message
  const position = safe(b => {
    const f = parse(b);
    if (f[1] === undefined && f[2] === undefined) return null;   // no fix
    return { lat: deg(F(f, 1)), lon: deg(F(f, 2)), alt: sgn(V(f, 3)), time: F(f, 4), precisionBits: V(f, 23) };
  });
  const user = safe(b => { const f = parse(b); return { longName: str(f, 2), shortName: str(f, 3) }; });
  const waypoint = safe(b => {
    const f = parse(b);
    return { id: V(f, 1), lat: deg(F(f, 2)), lon: deg(F(f, 3)), expire: V(f, 4), lockedTo: V(f, 5), name: str(f, 6), description: str(f, 7), icon: F(f, 8) };
  });

  function packet(b) {
    /* pki: a direct message encrypted to this radio's own key (field 17): it arrives with channel 0 but is not channel traffic. */
    const f = parse(b), m = { type: 'packet', from: F(f, 1), to: F(f, 2), channel: V(f, 3), id: F(f, 6), rxTime: F(f, 7), portnum: null, payload: null,
                              pki: !!V(f, 17) };
    if (L(f, 5) !== undefined && L(f, 4) === undefined) return m;   // still encrypted
    if (f[4]) { const d = parse(L(f, 4)); m.portnum = V(d, 1); m.payload = bytes(d, 2); }
    return m;
  }
  function nodeInfo(b) {
    const f = parse(b), us = f[2] ? user(L(f, 2)) : null, ps = f[3] ? position(L(f, 3)) : null;
    if (f[2] && !us) throw 0;
    return { type: 'nodeInfo', num: V(f, 1), longName: us ? us.longName : '', shortName: us ? us.shortName : '',
             position: ps, lastHeard: F(f, 5), channel: V(f, 7), viaMqtt: !!V(f, 8), isIgnored: !!V(f, 11) };
  }
  function channel(b) {
    const f = parse(b), s = f[2] ? parse(L(f, 2)) : NONE, ms = s[7] ? parse(L(s, 7)) : NONE, role = V(f, 3);
    return { type: 'channel', index: sgn(V(f, 1)), role: role === 1 ? 'primary' : role === 2 ? 'secondary' : 'disabled',
             name: str(s, 3), psk: bytes(s, 2), positionPrecision: V(ms, 1) };
  }

  /* FromRadio.config (5) is a oneof of Config members; only lora (6) is read: region (7, 0 = UNSET: the radio will not
     transmit), hop_limit (8), tx_enabled (9; a radio's own default is true, so false means switched off). */
  function config(b) {
    const f = parse(b);
    if (!f[6]) return { type: 'config', lora: null };
    const lo = parse(L(f, 6));
    return { type: 'config', lora: { region: V(lo, 7), hopLimit: V(lo, 8), txEnabled: !!V(lo, 9) } };
  }

  const fromRadio = (b) => {
    try {
      const order = [], f = parse(b, order);
      let last = 0;   // the FromRadio payload is a oneof: the last member present wins
      for (const k of order) if (k === 2 || k === 3 || k === 4 || k === 5 || k === 7 || k === 8 || k === 10) last = k;
      switch (last) {
        case 2: return packet(L(f, 2));
        case 3: return { type: 'myInfo', myNodeNum: V(parse(L(f, 3)), 1) };
        case 4: return nodeInfo(L(f, 4));
        case 5: return config(L(f, 5));
        case 7: return { type: 'configComplete', id: V(f, 7) };
        case 8: V(f, 8); return { type: 'rebooted' };
        case 10: return channel(L(f, 10));
      }
    } catch (e) { /* fall through */ }
    return { type: 'other' };
  };

  return { PORT, BROADCAST, enc, dec: { fromRadio, position, user, waypoint } };
})();
