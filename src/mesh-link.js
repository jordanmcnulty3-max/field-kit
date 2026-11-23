/* ---------- MLINK: the Bluetooth link to a Meshtastic radio. No FK, no DOM; needs MPB. ----------
   The Web Bluetooth object is passed in (MLINK.create({ bluetooth })), and nothing here touches navigator.bluetooth at load time.
   Service and characteristic UUIDs are recorded in docs/content-review.md (Comms).
   States: 'off' (reason: 'cancelled' | 'unsupported' | 'failed' | 'user'), 'connecting', 'syncing', 'on', 'lost'.
   'on' is reported only after configComplete carrying our nonce, so every start-up message has already reached onMessage.
   onMessage gets each decoded FromRadio (MPB.dec.fromRadio) except { type: 'other' }, which is read and dropped. */
const MLINK = (() => {
  const UUID = {
    service: '6ba1b218-15a8-461f-9fa8-5dcae273eafd',
    toradio: 'f75c76d2-129e-4dad-a1dd-7866124401e7',
    fromradio: '2c55e69e-4993-11ed-b878-0242ac120002',
    fromnum: 'ed9da18c-a800-4f66-a670-aa7547e34453',
  };
  /* OPEN_MS bounds connecting, finding the service and turning notifications on (Android may ask for the radio's PIN then,
     and a person types it); SYNC_MS is the longest silence allowed while the radio's list downloads (a big node database
     over Bluetooth takes longer than that in all, but a message arrives every fraction of a second). */
  const OPEN_MS = 60000, SYNC_MS = 30000, BEAT_MS = 300000;
  /* want_config_id 69420 and 69421 ask current firmware for the config only / the nodes only: never use them. */
  const nonce = () => { let n; do n = 1 + Math.floor(Math.random() * 0xFFFFFFFE); while (n === 69420 || n === 69421); return n; };
  const warn = e => { try { console.warn('Field Kit radio:', e && e.name); } catch (x) { /* no console */ } };

  const supported = (bt = navigator.bluetooth) => !!(bt && typeof bt.requestDevice === 'function');

  function create({ bluetooth = navigator.bluetooth, onMessage, onState } = {}) {
    let st = 'off';
    let device = null;      // the chosen radio, kept across connections so reconnect() needs no chooser
    let S = null;           // the live connection (null when there is none); every async step checks it is still current
    let inflight = null;    // the connect()/reconnect() promise in progress
    const say = (fn, arg) => { try { if (fn) fn(arg); } catch (e) { console.error('MLINK callback failed', e); } };
    const setState = (state, reason) => {
      st = state;
      say(onState, { state, name: device && device.name ? device.name : '', reason: state === 'off' ? reason : undefined });
    };
    const onGone = () => { if (S && S.device === device) closed(S); };

    /* Drop the live connection quietly: stop timers and listeners, close GATT, resolve whoever waits. */
    function teardown() {
      const s = S;
      if (!s) return;
      S = null;
      clearTimeout(s.syncTimer); clearInterval(s.beatTimer);
      if (s.num) s.num.removeEventListener('characteristicvaluechanged', s.onNum);
      try { if (s.device.gatt && s.device.gatt.connected) s.device.gatt.disconnect(); } catch (e) { /* already gone */ }
      if (s.done) { const d = s.done; s.done = null; d(false); }
    }
    function fail(s, reason) {
      if (S !== s) return;
      teardown();
      setState('off', reason);
    }
    function closed(s) {   // GATT went away under us
      if (S !== s) return;
      if (s.wasOn) { teardown(); setState('lost'); } else fail(s, 'failed');
    }

    /* Every GATT operation (a read, a write, turning notifications on) goes through one queue, one at a time: Android can
       reject an operation started while another is running. One that fails is tried once more before it counts as failed. */
    function gatt(s, fn) {
      const run = async () => {
        if (S !== s || !s.device.gatt.connected) throw new DOMException('Not connected', 'NetworkError');
        try { return await fn(); } catch (e) {
          if (S !== s || !s.device.gatt.connected) throw e;
          return await fn();
        }
      };
      const p = s.queue.then(run);
      s.queue = p.catch(() => {});
      return p;
    }
    /* A write that cannot happen (not connected, GATT error twice) resolves false. */
    function write(s, bytes) {
      const data = Uint8Array.from(bytes);
      return gatt(s, () => s.to.writeValueWithResponse ? s.to.writeValueWithResponse(data) : s.to.writeValue(data))
        .then(() => true, e => { if (S === s) warn(e); return false; });
    }
    const arm = (s, ms) => { clearTimeout(s.syncTimer); s.syncTimer = setTimeout(() => fail(s, 'failed'), ms); };

    function handle(s, m) {
      if (m.type === 'other') return;
      say(onMessage, m);
      if (S !== s) return;
      if (m.type === 'configComplete' && m.id === s.nonce && st === 'syncing') {
        clearTimeout(s.syncTimer);
        s.wasOn = true;
        setState('on');
        s.beatTimer = setInterval(() => { write(s, MPB.enc.heartbeat()); }, BEAT_MS);
        if (s.done) { const d = s.done; s.done = null; d(true); }
      } else if (m.type === 'rebooted') startSync(s);
    }

    /* Read fromradio until an empty read. A notification during a drain only sets `again`. */
    async function drain(s) {
      if (s.draining) { s.again = true; return; }
      s.draining = true;
      try {
        do {
          s.again = false;
          for (;;) {
            const v = await gatt(s, () => s.from.readValue());
            if (S !== s) return;
            if (!v.byteLength) break;   // empty: the radio's queue is drained
            if (st === 'syncing') arm(s, SYNC_MS);   // the download is moving: the allowed silence starts again
            const bytes = new Uint8Array(v.byteLength);   // a fresh buffer per message: the decoder returns views onto it
            bytes.set(new Uint8Array(v.buffer, v.byteOffset, v.byteLength));
            handle(s, MPB.dec.fromRadio(bytes));
            if (S !== s) return;
          }
        } while (s.again);
      } catch (e) {
        if (S === s) { warn(e); if (s.wasOn) { teardown(); setState('lost'); } else fail(s, 'failed'); }
      } finally { s.draining = false; }
    }

    /* Ask the radio for its whole state and read it (at connect, and again after a reboot). */
    function startSync(s) {
      s.nonce = nonce();
      clearInterval(s.beatTimer);
      arm(s, SYNC_MS);
      setState('syncing');
      write(s, MPB.enc.wantConfig(s.nonce)).then(ok => { if (!ok) closed(s); else drain(s); });
    }

    function open(choose) {
      teardown();
      setState('connecting');
      const s = S = { device: null, to: null, from: null, num: null, queue: Promise.resolve(), draining: false, again: false,
                      nonce: 0, lastNum: null, wasOn: false, syncTimer: 0, beatTimer: 0, done: null, onNum: null };
      const result = new Promise(res => { s.done = res; });   // teardown() resolves it false; reaching 'on' resolves it true
      const go = async () => {
        let stage = 'chooser';
        try {
          if (choose) {
            const d = await bluetooth.requestDevice({ filters: [{ services: [UUID.service] }] });
            if (S !== s) return;   // disconnect() while the chooser was open: a late pick does nothing
            if (device && device !== d) device.removeEventListener('gattserverdisconnected', onGone);
            device = d;
            device.removeEventListener('gattserverdisconnected', onGone);
            device.addEventListener('gattserverdisconnected', onGone);
          }
          s.device = device;
          stage = 'gatt';
          arm(s, OPEN_MS);   // the chooser is the user's to dismiss; every step after it is bounded
          const server = await device.gatt.connect();
          if (S !== s) { if (!S) { try { server.disconnect(); } catch (e) { /* already gone */ } } return; }   // a newer attempt shares this GATT object: leave it
          const service = await server.getPrimaryService(UUID.service);
          s.to = await service.getCharacteristic(UUID.toradio);
          s.from = await service.getCharacteristic(UUID.fromradio);
          s.num = await service.getCharacteristic(UUID.fromnum);
          if (S !== s) return;
          s.onNum = (ev) => {
            const v = ev.target.value;
            const n = v && v.byteLength >= 4 ? v.getUint32(0, true) : null;
            if (n !== null) {
              const down = s.lastNum !== null && n < s.lastNum;
              s.lastNum = n;
              if (down) { startSync(s); return; }   // the radio's counter restarted: it rebooted
            }
            drain(s);
          };
          s.num.addEventListener('characteristicvaluechanged', s.onNum);
          await gatt(s, () => s.num.startNotifications());
          if (S !== s) return;
          startSync(s);
        } catch (e) {
          if (S === s) {
            warn(e);
            const cancelled = stage === 'chooser' && e && e.name === 'NotFoundError';
            teardown();
            setState('off', cancelled ? 'cancelled' : 'failed');
          }
        }
      };
      go();
      return result;
    }

    function begin(choose) {
      if (inflight) return inflight;
      if (st === 'on' || st === 'syncing') return Promise.resolve(true);
      if (choose && !supported(bluetooth)) { setState('off', 'unsupported'); return Promise.resolve(false); }
      if (!choose && !device) return Promise.resolve(false);
      const p = open(choose).then(ok => { if (inflight === p) inflight = null; return ok; });
      inflight = p;
      return p;
    }

    return {
      connect: () => begin(true),
      reconnect: () => begin(false),
      disconnect() {
        inflight = null;
        const had = st !== 'off';
        teardown();
        if (had) setState('off', 'user');
      },
      send(bytes) { return S && st === 'on' ? write(S, bytes) : Promise.resolve(false); },
      state: () => st,
    };
  }

  return { supported, create };
})();
