/* ---------- FK.mesh: app state for the radio link (Meshtastic over Bluetooth) ----------
   The Bluetooth link (MLINK) is built only when the Settings switch is on and the user connects, so with the switch off nothing
   here reads navigator.bluetooth. This module decides what the channel is (private, public, unknown), keeps teammates from the
   radio's list and live packets, and sends a marker to the team. It holds no channel key: the key is looked at once to reach a
   verdict and dropped. Storage: meshOn (the switch), meshMe (the last known number of this phone's radio), meshTeam (teammates;
   a session-only key, never in a backup). Bus events: 'mesh', 'team', 'meshWaypoint' { wp, from, name }. */
(() => {
  const { store, fin, okLatLon, emit, on } = FK;
  const MAX_TEAM = 100, MAX_NAME = 40;

  let enabled = store.get('meshOn', false) === true;
  let myNum = (n => Number.isInteger(n) && n > 0 && n <= 0xFFFFFFFF ? n : null)(store.get('meshMe', null));
  let myName = '';
  let link = null;                                   // MLINK.create(...) result, made on the first connect()
  let st = { state: 'off', name: '', reason: undefined };
  let channel = 'unknown', positions = 'unknown';
  let lora = null;                                   // { region, hopLimit, txEnabled } from the radio's Config.lora, this download

  /* ---- teammates ---- */
  const cleanName = s => typeof s === 'string' ? s.slice(0, MAX_NAME) : '';
  const cleanTeam = v => (Array.isArray(v) ? v : []).filter(x => x && Number.isInteger(x.num) && x.num > 0 && x.num <= 0xFFFFFFFF).slice(0, MAX_TEAM).map(x => ({
    num: x.num, long: cleanName(x.long), short: cleanName(x.short),
    lat: okLatLon(x.lat, x.lon) ? x.lat : null, lon: okLatLon(x.lat, x.lon) ? x.lon : null,
    t: fin(x.t) && x.t > 0 ? x.t : 0, heard: fin(x.heard) && x.heard > 0 ? x.heard : 0,
    ph: fin(x.ph) && x.ph > 0 ? x.ph : 0, approx: x.approx === true   // ph: when the stored position was heard
  }));
  let team = cleanTeam(store.get('meshTeam', []));
  const saveTeam = () => { store.set('meshTeam', team); emit('team'); };

  const radioName = num => 'Radio ' + (num & 0xFFFF).toString(16).padStart(4, '0');
  const nameOf = num => {
    const m = team.find(x => x.num === num);
    const n = m ? (m.long || m.short) : num === myNum ? myName : '';
    return n || radioName(num);
  };

  const goodPos = p => !!p && okLatLon(p.lat, p.lon) && !(p.lat === 0 && p.lon === 0);
  /* A radio time (seconds) as ms, or 0 when there is none or it is more than 2 minutes ahead of this phone's clock (a radio
     clock that far off says nothing true about when). */
  const SKEW_MS = 2 * 60000;
  const radioTime = s => { const t = fin(s) && s > 0 ? s * 1000 : 0; return t > Date.now() + SKEW_MS ? 0 : t; };

  /* Add or update one teammate; `patch` may hold long, short, pos ({ lat, lon, time, precisionBits }), heard, and live (the
     position came in a live packet: with no time of its own it takes the time it was heard; from the radio's node database
     it stays "time unknown"). A stored position is never replaced by an older one; when either has no time, the one heard
     later wins. Saves and emits when it changed. */
  function touch(num, patch) {
    if (!Number.isInteger(num) || num <= 0 || num === myNum || num === 0xFFFFFFFF) return;
    let m = team.find(x => x.num === num);
    const before = m ? JSON.stringify(m) : '';
    if (!m) { m = { num, long: '', short: '', lat: null, lon: null, t: 0, heard: 0, ph: 0, approx: false }; team.push(m); }
    if (patch.long) m.long = cleanName(patch.long);
    if (patch.short) m.short = cleanName(patch.short);
    if (goodPos(patch.pos)) {
      const heard = fin(patch.heard) && patch.heard > 0 ? patch.heard : 0;
      const t = radioTime(patch.pos.time) || (patch.live ? heard : 0);
      const newer = m.lat === null || (t && m.t ? t >= m.t : heard >= m.ph);
      if (newer) {
        const bits = patch.pos.precisionBits;
        m.lat = patch.pos.lat; m.lon = patch.pos.lon; m.t = t; m.ph = heard; m.approx = bits > 0 && bits < 32;
      }
    }
    if (patch.heard > m.heard) m.heard = patch.heard;
    if (team.length > MAX_TEAM) {   // least recently heard goes first
      let drop = team[0];
      for (const x of team) if (x.heard < drop.heard) drop = x;
      team = team.filter(x => x !== drop);
    }
    if (JSON.stringify(m) !== before) saveTeam();
  }

  /* ---- the channel verdict ---- */
  function setVerdict(c, p) {
    if (c === channel && p === positions) return;
    channel = c; positions = p;
    emit('mesh');
  }
  /* The published default key (meshtastic.org; channel.proto; docs/content-review.md). A one-byte key picks it or a variant
     of it, and so does a 16-byte key whose first 15 bytes are its own (the firmware counts those as public); a key of all
     zeros encrypts nothing. Not a secret. */
  const DEFAULT_KEY = [0xd4, 0xf1, 0xbb, 0x3a, 0x20, 0x29, 0x07, 0x59, 0xf0, 0xbc, 0xff, 0xab, 0xcf, 0x4e, 0x69, 0x01];
  function keyVerdict(psk) {
    const n = psk ? psk.length : 0;
    if (n <= 1) return 'public';
    if (Array.prototype.every.call(psk, b => b === 0)) return 'public';
    if (n === 16 && DEFAULT_KEY.slice(0, 15).every((b, i) => psk[i] === b)) return 'public';
    return n === 16 || n === 32 ? 'private' : 'unknown';
  }
  function verdict(m) {
    if (m.role !== 'primary') return;                // only the primary channel is what a marker is sent on
    if (m.index !== 0) { setVerdict('unknown', 'unknown'); return; }   // sends and filters use index 0: anything else is not understood
    setVerdict(keyVerdict(m.psk), m.positionPrecision === 32 ? 'precise' : m.positionPrecision === 0 ? 'off' : 'approx');
  }

  /* ---- messages and link state from the radio ---- */
  /* The start-up messages may come in any order, so until the primary channel's verdict is known, nothing from the mesh is shown
     or emitted: teammate updates and waypoint packets wait here (200 at most, oldest dropped). A private verdict applies them in
     order; a public verdict, the end of the download with no verdict, or a new download discards them. */
  const MAX_HELD = 200;
  let held = [];
  /* A direct message (pki) is never channel traffic, though it arrives as channel 0; a waypoint counts only when it was sent
     to everyone. A position addressed to this radio is still a teammate's (radios answer a position request directly). */
  const isMesh = m => (m.type === 'nodeInfo' && !(m.num && m.num === myNum)) ||
    (m.type === 'packet' && m.channel === 0 && !m.pki &&
      (m.portnum === MPB.PORT.POSITION || m.portnum === MPB.PORT.NODEINFO || (m.portnum === MPB.PORT.WAYPOINT && m.to === MPB.BROADCAST)));
  /* Nodes the owner ignores, and nodes seen only through an internet bridge (MQTT), are never teammates. */
  const notMate = num => {
    const was = team.length;
    team = team.filter(x => x.num !== num);
    if (team.length !== was) saveTeam();
  };
  const blocked = new Set();   // numbers flagged that way in this session: their live packets do not bring them back

  /* now: when the phone got the message. A live packet was heard at its rx_time when the radio gave a plausible one. */
  function apply(m, now) {
    if (m.type === 'nodeInfo') {
      if (m.viaMqtt || m.isIgnored) { blocked.add(m.num); notMate(m.num); return; }
      blocked.delete(m.num);
      if (m.channel === 0) touch(m.num, { long: m.longName, short: m.shortName, pos: m.position, heard: radioTime(m.lastHeard) });
      return;
    }
    if (blocked.has(m.from)) return;
    const heard = radioTime(m.rxTime) || now;
    if (m.portnum === MPB.PORT.POSITION && m.payload) touch(m.from, { pos: MPB.dec.position(m.payload), heard, live: true });
    else if (m.portnum === MPB.PORT.NODEINFO && m.payload) {
      const u = MPB.dec.user(m.payload);
      if (u) touch(m.from, { long: u.longName, short: u.shortName, heard });
    } else if (m.portnum === MPB.PORT.WAYPOINT && m.payload) {
      const wp = MPB.dec.waypoint(m.payload);
      if (wp) emit('meshWaypoint', { wp, from: m.from, name: nameOf(m.from) });
    }
  }
  function onMessage(m) {
    if (!enabled || !m) return;
    if (m.type === 'myInfo') {
      myNum = m.myNodeNum || null;
      store.set('meshMe', myNum);
      if (myNum && team.some(x => x.num === myNum)) { team = team.filter(x => x.num !== myNum); saveTeam(); }
    } else if (m.type === 'config') {
      if (m.lora) { const was = radioProblem(); lora = m.lora; if (radioProblem() !== was) emit('mesh'); }
    } else if (m.type === 'channel') {
      verdict(m);
      if (channel === 'private') { const h = held; held = []; h.forEach(x => apply(x.m, x.at)); }
      else if (channel === 'public') held = [];
    } else if (m.type === 'nodeInfo' && m.num && m.num === myNum) {
      if (m.longName || m.shortName) myName = cleanName(m.longName) || cleanName(m.shortName);
    } else if (isMesh(m)) {
      if (channel === 'private') apply(m, Date.now());
      else if (channel === 'unknown') { held.push({ m, at: Date.now() }); if (held.length > MAX_HELD) held.shift(); }
    }
  }
  function onState(s) {
    if (!enabled) return;
    st = { state: s.state, name: s.name || '', reason: s.reason };
    if (s.state === 'syncing') { channel = 'unknown'; positions = 'unknown'; held = []; lora = null; }   // every start-up download decides afresh
    else if (s.state === 'on' && channel === 'unknown') held = [];                          // the download ended with no verdict
    emit('mesh');
  }

  /* ---- the switch and the link ---- */
  function setEnabled(v) {
    v = !!v;
    if (v === enabled) return;
    enabled = v;
    store.set('meshOn', v);
    if (!v) {
      if (link) link.disconnect();                   // its 'off' report is ignored now: enabled is false
      st = { state: 'off', name: '', reason: 'user' };
      channel = 'unknown'; positions = 'unknown'; held = []; lora = null;
    }
    emit('mesh');
  }
  const supported = () => { try { return enabled && MLINK.supported(navigator.bluetooth); } catch (e) { return false; } };
  /* 'region' (no region set: the radio will not transmit), 'txoff' (its transmitter is switched off) or null (fine, or not
     known yet: no Config.lora in this download). */
  function radioProblem() {
    if (!enabled || !lora) return null;
    return !lora.region ? 'region' : !lora.txEnabled ? 'txoff' : null;
  }
  const canShare = () => enabled && st.state === 'on' && channel === 'private' && !radioProblem();
  /* Every packet goes out with the radio's own hop limit: left at 0 with no ack wanted, the firmware sends it zero-hop and no
     radio relays it. 3 (the firmware default) until the config has arrived, or when it reads 0. */
  const hops = () => { const h = lora && lora.hopLimit; return Number.isInteger(h) && h >= 1 ? Math.min(h, 7) : 3; };
  const ensureLink = () => link || (link = MLINK.create({ bluetooth: navigator.bluetooth, onMessage, onState }));

  const randId = () => 1 + Math.floor(Math.random() * 0xFFFFFFFE);
  async function sendWaypoint(wp) {
    if (!canShare() || !wp || !okLatLon(wp.lat, wp.lon)) return false;
    const payload = MPB.enc.waypoint({ id: wp.id || randId(), lat: wp.lat, lon: wp.lon, expire: wp.expire, lockedTo: wp.lockedTo,
                                       name: wp.name, description: wp.description, icon: wp.icon });
    return link.send(MPB.enc.packet({ to: MPB.BROADCAST, channel: 0, id: randId(), portnum: MPB.PORT.WAYPOINT, payload, hopLimit: hops() }));
  }

  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible' && enabled && link && st.state === 'lost') link.reconnect();
  });

  FK.mesh = {
    enabled: () => enabled, setEnabled, supported,
    status: () => enabled ? { state: st.state, name: st.name, reason: st.reason } : { state: 'off', name: '', reason: 'user' },
    channel: () => channel, positions: () => positions, canShare, radioProblem,
    myNum: () => myNum, nameOf,
    teammates: () => team.map(m => ({ num: m.num, name: m.long || m.short || radioName(m.num), lat: m.lat, lon: m.lon, t: m.t, heard: m.heard,
                                       approx: m.approx })),
    connect: () => enabled ? ensureLink().connect() : Promise.resolve(false),
    reconnect: () => enabled && link ? link.reconnect() : Promise.resolve(false),
    disconnect: () => { if (link) link.disconnect(); },
    sendWaypoint
  };
  FK._test.mesh = { feed: onMessage, link: (state, name, reason) => onState({ state, name, reason }) };

  /* ---- Settings: the switch ---- */
  const sw = FK.$('#meshOn');
  sw.checked = enabled;
  sw.addEventListener('change', () => FK.mesh.setEnabled(sw.checked));
  on('mesh', () => { sw.checked = enabled; });
})();
