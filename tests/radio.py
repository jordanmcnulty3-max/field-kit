"""A scripted fake Meshtastic radio for tests. It replaces navigator.bluetooth, so code under test (MLINK in src/mesh-link.js, and
the later tasks built on it) talks to it exactly as it would to Web Bluetooth.

Use:
    from . import radio
    radio.install(page)              # BEFORE page.goto: adds the init script (and, with page.clock.install(), install the clock
                                     # first as well; the fake itself uses no timers except the optional slow_writes delay)
    page.goto(app_url)
    ... create a link in the page with MLINK.create({ bluetooth: navigator.bluetooth, ... }) and connect ...
    radio.push(page, meshref.ref_from_radio(...))   # queue a FromRadio and notify fromnum
    radio.sent(page)                                # every ToRadio written so far, as a list of bytes (wantConfig, heartbeat, ...)

install(page, script=None, complete=True, name='Meshtastic_a1b2')
    script: list of FromRadio byte strings the radio plays when it receives wantConfig (default: default_script()).
    complete: when True (default) a configComplete carrying the wantConfig nonce follows the script; False leaves the radio
    silent after the script (a stalled start-up).
Helpers (all take the page):
    push(page, data)        queue one FromRadio (bytes) and notify fromnum (the counter goes up by one)
    notify(page)            notify fromnum without queueing anything (a spurious notification)
    sent(page)              list of bytes, every ToRadio the link wrote, in order
    drop(page)              the radio goes away: gatt.connected false, 'gattserverdisconnected' fires
    refuse(page, how)       next attempts fail: 'cancel' (chooser dismissed), 'gatt' (gatt.connect rejects),
                            'no-service' (getPrimaryService rejects); None clears it
    reboot(page)            the radio restarts: queue emptied, fromnum goes down to 0 and notifies
    hold_reads(page)        fromradio reads compute their result, then wait; release_reads(page) lets them finish
                            (this makes "a notification arrives while a drain is in progress" reproducible)
    release_reads(page)
    slow_writes(page, ms)   each ToRadio write takes ms real milliseconds (so overlapping writes would show)
    default_script()        the FromRadio list the default radio plays
In the page, window.FakeRadio holds the live state for assertions: sent, queue, fromnum, choosers (requestDevice calls),
connects (gatt.connect calls), connected(), maxActive (most writes ever in flight at once), heldReads, lastOptions (what
requestDevice was given). The fake models: requestDevice({filters:[{services:[uuid]}]}), device.name, device.gatt
(connect, connected, disconnect, getPrimaryService), service.getCharacteristic, characteristics with readValue (a fresh DataView
every time), writeValue / writeValueWithResponse, startNotifications and 'characteristicvaluechanged', and the device event
'gattserverdisconnected'.
"""
import json

from . import meshref

SERVICE = '6ba1b218-15a8-461f-9fa8-5dcae273eafd'
TORADIO = 'f75c76d2-129e-4dad-a1dd-7866124401e7'
FROMRADIO = '2c55e69e-4993-11ed-b878-0242ac120002'
FROMNUM = 'ed9da18c-a800-4f66-a670-aa7547e34453'

MY_NUM = 0x0A0B0C01
TEST_KEY = bytes(range(1, 33))   # a made-up 32-byte key for tests only


def default_script():
    r = meshref.ref_from_radio
    return [
        r(my_node_num=MY_NUM),
        r(channel=dict(index=0, role=1, name='Team', psk=TEST_KEY, precision=32)),
        r(node=dict(num=0x0A0B0C01, long='Alpha', short='ALP', pos=(43.0, -76.0, 100, 1766000000), last_heard=1766000000)),
        r(node=dict(num=0x0A0B0C02, long='Bravo', short='BRV', pos=(43.01, -76.01, 0, 1766000100), last_heard=1766000100)),
        r(node=dict(num=0x0A0B0C03, long='Charlie', short='CHA', pos=None, last_heard=1766000200)),
    ]


def install(page, script=None, complete=True, name='Meshtastic_a1b2'):
    script = default_script() if script is None else script
    cfg = dict(script=[list(m) for m in script], complete=complete, name=name,
               uuids=dict(service=SERVICE, toradio=TORADIO, fromradio=FROMRADIO, fromnum=FROMNUM))
    page.add_init_script('const FAKE_RADIO_CFG = ' + json.dumps(cfg) + ';\n' + _JS)


def _call(page, expr, arg=None):
    return page.evaluate('(a) => ' + expr, arg)


def push(page, data):
    _call(page, 'FakeRadio.push(a)', list(data))


def notify(page):
    _call(page, 'FakeRadio.notify()')


def sent(page):
    return [bytes(m) for m in _call(page, 'FakeRadio.sent')]


def drop(page):
    _call(page, 'FakeRadio.drop()')


def refuse(page, how):
    assert how in (None, 'cancel', 'gatt', 'no-service')
    _call(page, 'FakeRadio.refuse = a', how)


def reboot(page):
    _call(page, 'FakeRadio.reboot()')


def hold_reads(page):
    _call(page, 'FakeRadio.hold = true')


def release_reads(page):
    _call(page, 'FakeRadio.releaseReads()')


def slow_writes(page, ms):
    _call(page, 'FakeRadio.writeDelay = a', ms)


_JS = r"""
(() => {
  const C = FAKE_RADIO_CFG, U = C.uuids;
  const realSetTimeout = window.setTimeout.bind(window);
  const dv = (arr) => { const b = new Uint8Array(arr); return new DataView(b.buffer); };
  const err = (name, msg) => new DOMException(msg, name);
  const varint = (n) => { const a = []; while (n > 127) { a.push((n % 128) | 128); n = Math.floor(n / 128); } a.push(n); return a; };
  const readVarint = (b, p) => { let x = 0, m = 1; for (;; p++) { x += (b[p] & 127) * m; m *= 128; if (!(b[p] & 128)) return x; } };

  class Char extends EventTarget {
    constructor(uuid) { super(); this.uuid = uuid; this.value = null; this.notifying = false; }
    async startNotifications() { this.notifying = true; return this; }
    async stopNotifications() { this.notifying = false; return this; }
  }
  const toradio = new Char(U.toradio), fromradio = new Char(U.fromradio), fromnum = new Char(U.fromnum);
  const chars = { [U.toradio]: toradio, [U.fromradio]: fromradio, [U.fromnum]: fromnum };

  const R = window.FakeRadio = {
    queue: [], sent: [], fromnum: 0, refuse: null, hold: false, heldReads: 0, waiters: [],
    choosers: 0, connects: 0, active: 0, maxActive: 0, writeDelay: 0, lastOptions: null,
    connected: () => gatt.connected,
    push(bytes) { R.queue.push(bytes); R.fromnum++; R.notify(); },
    notify() {
      if (!gatt.connected || !fromnum.notifying) return;
      const n = R.fromnum;
      Promise.resolve().then(() => {
        if (!gatt.connected) return;
        fromnum.value = dv([n & 255, (n >> 8) & 255, (n >> 16) & 255, (n >>> 24) & 255]);
        fromnum.dispatchEvent(new Event('characteristicvaluechanged'));
      });
    },
    drop() { gatt.disconnect(); },
    reboot() { R.queue = []; R.fromnum = 0; R.notify(); },
    releaseReads() { R.hold = false; const w = R.waiters; R.waiters = []; w.forEach(f => f()); },
    play(nonce) {
      C.script.forEach(m => R.push(m));
      if (C.complete) R.push([0x38, ...varint(nonce)]);   // FromRadio.config_complete_id (field 7, varint)
    },
  };

  fromradio.readValue = async () => {
    if (!gatt.connected) throw err('NetworkError', 'GATT Server is disconnected.');
    const next = R.queue.shift();
    const value = dv(next || []);   // empty read = queue drained
    if (R.hold) { R.heldReads++; await new Promise(f => R.waiters.push(f)); R.heldReads--; }
    if (!gatt.connected) throw err('NetworkError', 'GATT Server is disconnected.');
    return value;
  };
  fromnum.readValue = async () => { const n = R.fromnum; return dv([n & 255, (n >> 8) & 255, (n >> 16) & 255, (n >>> 24) & 255]); };
  toradio.readValue = async () => dv([]);

  const write = async (data) => {
    if (!gatt.connected) throw err('NetworkError', 'GATT Server is disconnected.');
    const b = Uint8Array.from(data instanceof ArrayBuffer ? new Uint8Array(data) : new Uint8Array(data.buffer || data, data.byteOffset || 0, data.byteLength));
    R.active++; R.maxActive = Math.max(R.maxActive, R.active);
    try {
      if (R.writeDelay) await new Promise(f => realSetTimeout(f, R.writeDelay)); else await Promise.resolve();
      if (!gatt.connected) throw err('NetworkError', 'GATT Server is disconnected.');
    } finally { R.active--; }
    R.sent.push(Array.from(b));
    if (b[0] === 0x18) R.play(readVarint(b, 1));   // ToRadio.want_config_id (field 3, varint)
  };
  toradio.writeValue = write;
  toradio.writeValueWithResponse = write;

  const device = new EventTarget();
  device.id = 'fake-radio'; device.name = C.name;
  const service = { uuid: U.service, getCharacteristic: async (u) => {
    const c = chars[String(u).toLowerCase()];
    if (!c) throw err('NotFoundError', 'No Characteristics matching UUID ' + u + ' found in Service.');
    return c;
  } };
  const gatt = device.gatt = {
    connected: false, device,
    async connect() {
      R.connects++;
      if (R.refuse === 'gatt') throw err('NetworkError', 'Connection attempt failed.');
      gatt.connected = true;
      return gatt;
    },
    disconnect() {
      if (!gatt.connected) return;
      gatt.connected = false;
      fromnum.notifying = false;
      Promise.resolve().then(() => device.dispatchEvent(new Event('gattserverdisconnected')));
    },
    async getPrimaryService(u) {
      if (!gatt.connected) throw err('NetworkError', 'GATT Server is disconnected.');
      if (R.refuse === 'no-service' || String(u).toLowerCase() !== U.service) throw err('NotFoundError', 'No Services matching UUID ' + u + ' found in Device.');
      return service;
    },
  };

  const bluetooth = {
    async requestDevice(opts) {
      R.choosers++; R.lastOptions = JSON.parse(JSON.stringify(opts || {}));
      if (R.refuse === 'cancel') throw err('NotFoundError', 'User cancelled the requestDevice() chooser.');
      return device;
    },
    async getAvailability() { return true; },
  };
  Object.defineProperty(navigator, 'bluetooth', { value: bluetooth, configurable: true });
})();
"""
