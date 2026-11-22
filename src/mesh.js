/* ---------- FK.mesh: app state for the radio link (Meshtastic over Bluetooth) ----------
   The Bluetooth link (MLINK) is built only when the Settings switch is on and the user connects, so with the switch off nothing
   here reads navigator.bluetooth. This module decides what the channel is (private, public, unknown), keeps teammates from the
   radio's list and live packets, and sends a marker to the team. It holds no channel key: the key is looked at once to reach a
   verdict and dropped. Storage: meshOn (the switch), meshMe (the last known number of this phone's radio), meshTeam (teammates;
   a session-only key, never in a backup). Bus events: 'mesh', 'team', 'meshWaypoint' { wp, from, name }. */
(() => {
  const { store, fin, okLatLon, emit, on } = FK;
  const MAX_TEAM = 100, MAX_NAME = 40, DAY = 864e5;

  let enabled = store.get('meshOn', false) === true;
  let myNum = (n => Number.isInteger(n) && n > 0 && n <= 0xFFFFFFFF ? n : null)(store.get('meshMe', null));
  let myName = '';
  let link = null;                                   // MLINK.create(...) result, made on the first connect()
  let st = { state: 'off', name: '', reason: undefined };
  let channel = 'unknown', positions = 'unknown';

  /* ---- teammates ---- */
  const cleanName = s => typeof s === 'string' ? s.slice(0, MAX_NAME) : '';
  const cleanTeam = v => (Array.isArray(v) ? v : []).filter(x => x && Number.isInteger(x.num) && x.num > 0 && x.num <= 0xFFFFFFFF).slice(0, MAX_TEAM).map(x => ({
    num: x.num, long: cleanName(x.long), short: cleanName(x.short),
    lat: okLatLon(x.lat, x.lon) ? x.lat : null, lon: okLatLon(x.lat, x.lon) ? x.lon : null,
    t: fin(x.t) && x.t > 0 ? x.t : 0, heard: fin(x.heard) && x.heard > 0 ? x.heard : 0
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
  const posTime = p => { const t = fin(p.time) && p.time > 0 ? p.time * 1000 : 0; return t > Date.now() + DAY ? 0 : t; };

  /* Add or update one teammate; `patch` may hold long, short, pos ({ lat, lon, time }), heard. Saves and emits when it changed. */
  function touch(num, patch) {
    if (!Number.isInteger(num) || num <= 0 || num === myNum || num === 0xFFFFFFFF) return;
    let m = team.find(x => x.num === num);
    const before = m ? JSON.stringify(m) : '';
    if (!m) { m = { num, long: '', short: '', lat: null, lon: null, t: 0, heard: 0 }; team.push(m); }
    if (patch.long) m.long = cleanName(patch.long);
    if (patch.short) m.short = cleanName(patch.short);
    if (goodPos(patch.pos)) { m.lat = patch.pos.lat; m.lon = patch.pos.lon; m.t = posTime(patch.pos); }
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
  function verdict(m) {
    if (m.role !== 'primary') return;                // only the primary channel is what a marker is sent on
    const n = m.psk ? m.psk.length : 0;
    const c = n <= 1 ? 'public' : n === 16 || n === 32 ? 'private' : 'unknown';
    setVerdict(c, m.positionPrecision === 32 ? 'precise' : m.positionPrecision === 0 ? 'off' : 'approx');
  }

  /* ---- messages and link state from the radio ---- */
  function onMessage(m) {
    if (!enabled || !m) return;
    if (m.type === 'myInfo') {
      myNum = m.myNodeNum || null;
      store.set('meshMe', myNum);
      if (myNum && team.some(x => x.num === myNum)) { team = team.filter(x => x.num !== myNum); saveTeam(); }
    } else if (m.type === 'channel') verdict(m);
    else if (m.type === 'nodeInfo') {
      if (m.num && m.num === myNum) { if (m.longName || m.shortName) myName = cleanName(m.longName) || cleanName(m.shortName); return; }
      if (channel !== 'public' && m.channel === 0) touch(m.num, { long: m.longName, short: m.shortName, pos: m.position, heard: m.lastHeard * 1000 });
    } else if (m.type === 'packet' && m.channel === 0 && channel !== 'public') {
      if (m.portnum === MPB.PORT.POSITION && m.payload) touch(m.from, { pos: MPB.dec.position(m.payload), heard: Date.now() });
      else if (m.portnum === MPB.PORT.NODEINFO && m.payload) {
        const u = MPB.dec.user(m.payload);
        if (u) touch(m.from, { long: u.longName, short: u.shortName, heard: Date.now() });
      } else if (m.portnum === MPB.PORT.WAYPOINT && m.payload && channel === 'private') {
        const wp = MPB.dec.waypoint(m.payload);
        if (wp) emit('meshWaypoint', { wp, from: m.from, name: nameOf(m.from) });
      }
    }
  }
  function onState(s) {
    if (!enabled) return;
    st = { state: s.state, name: s.name || '', reason: s.reason };
    if (s.state === 'syncing') { channel = 'unknown'; positions = 'unknown'; }   // every start-up download decides afresh
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
      channel = 'unknown'; positions = 'unknown';
    }
    emit('mesh');
  }
  const supported = () => { try { return enabled && MLINK.supported(navigator.bluetooth); } catch (e) { return false; } };
  const canShare = () => enabled && st.state === 'on' && channel === 'private';
  const ensureLink = () => link || (link = MLINK.create({ bluetooth: navigator.bluetooth, onMessage, onState }));

  const randId = () => 1 + Math.floor(Math.random() * 0xFFFFFFFE);
  async function sendWaypoint(wp) {
    if (!canShare() || !wp || !okLatLon(wp.lat, wp.lon)) return false;
    const payload = MPB.enc.waypoint({ id: wp.id || randId(), lat: wp.lat, lon: wp.lon, expire: wp.expire, lockedTo: wp.lockedTo,
                                       name: wp.name, description: wp.description, icon: wp.icon });
    return link.send(MPB.enc.packet({ to: MPB.BROADCAST, channel: 0, id: randId(), portnum: MPB.PORT.WAYPOINT, payload }));
  }

  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible' && enabled && link && st.state === 'lost') link.reconnect();
  });

  FK.mesh = {
    enabled: () => enabled, setEnabled, supported,
    status: () => enabled ? { state: st.state, name: st.name, reason: st.reason } : { state: 'off', name: '', reason: 'user' },
    channel: () => channel, positions: () => positions, canShare,
    myNum: () => myNum, nameOf,
    teammates: () => team.map(m => ({ num: m.num, name: m.long || m.short || radioName(m.num), lat: m.lat, lon: m.lon, t: m.t, heard: m.heard })),
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
