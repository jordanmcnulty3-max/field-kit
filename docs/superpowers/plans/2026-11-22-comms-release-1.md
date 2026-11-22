# Comms Release 1 (Radio Link) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Field Kit connects to a Meshtastic radio over Web Bluetooth, shows teammates on the Tactical map, and shares markers both ways as standard Meshtastic waypoints, all behind a Settings switch that is off by default.

**Architecture:** Five new plain-script modules with one job each: a pure byte codec (`MPB`), a Bluetooth link (`MLINK`), app state (`FK.mesh`), pure marker-to-waypoint mapping (`MMK`), and sharing rules (`FK.share`); plus two UI modules (radio sheet, teammates). Existing marker storage gains one optional `net` record. Nothing runs unless the switch is on.

**Tech Stack:** Vanilla JS inlined by `build.py` (no bundler, no npm). Tests: pytest + Playwright at 360 x 640, and the `meshtastic` Python package (tests only) as the independent byte reference.

**Spec:** `docs/superpowers/specs/2026-11-22-comms-design.md`. Read it and `claude/FIELD-KIT-STATUS.md` rules 1 to 15 (given to you by the controller) before any task.

## Global Constraints

- Edit only `src/`, `figs/`, `tools/`, `tests/`, `docs/`, `vendor/`, `build.py`. Root `index.html`, `sw.js`, `manifest.json` are build output.
- **No code copied from any Meshtastic repository or package into `src/`.** Write from the published message definitions. The `meshtastic` Python package may be imported by tests only.
- The repo is public: no channel keys, no home town. Test coordinates are 43.0, -76.0 (offsets like 43.01 are fine).
- Words on screen: "Marker" (never waypoint), "Radio", "Teammate". No text advising action against a person. No internal wording ("Task 3", "net record").
- Sheets go through `FK.sheet.open/close/ask/confirm`; no `prompt`, `confirm`, `alert`. A sheet built on `mk-sheet` never gives a flex item `flex: 1` (use `flex: 1 1 auto`). Read `src/sheet.js` whole before changing a sheet.
- With the switch off (`fk.meshOn` absent or false): no radio button, no Radio sheet, no Share switch, no call to `navigator.bluetooth`, and every existing test passes unchanged.
- Shared-marker limits: name at most 29 UTF-8 bytes, note at most 99 UTF-8 bytes on the wire (stricter than Meshtastic's 30 and 100, safe whether the firmware counts bytes or characters).
- Web research: built-in search and fetch only; fetch only URLs a search returned.
- Run the whole suite after every task (three chunks or in the background: a foreground command is cut at 10 minutes): `python3 -m unittest tests.test_validate && python3 -m pytest tests -q`.
- Commit at least every 15 minutes on branch `comms`. Never push to `main`.

## Review Focus

1. **Garbage or cut-off bytes from the radio** (a truncated message, an unknown field, a huge length): the codec returns `{ type: 'other' }` or `null`, never throws, and the link keeps reading. (Task 1, Task 2)
2. **A name with emoji or accents at the limit:** the sheet counts UTF-8 bytes, so "Café ⛺ north ridge lookout" is refused or accepted by bytes, never cut mid-character. (Task 5, Task 7)
3. **The Meshtastic app already holds the radio, or the user cancels the chooser, or double-taps Connect:** a plain message, state back to "off", never stuck on "Connecting". (Task 2, Task 4)
4. **A wrong clock:** a teammate position or a "Seen" time in the future shows no age rather than a wrong one. (Task 5, Task 6)
5. **A hostile or broken waypoint:** latitude 0/longitude 0, out-of-range coordinates, an empty name, markup in the name, 10,000 markers in a minute: ignored, defaulted, escaped, capped. (Task 5, Task 7)

---

### Task 1: The byte codec

**Files:**
- Create: `src/mesh-pb.js`
- Modify: `build.py` (add `mesh-pb.js` to the script list after `wmm.js`)
- Create: `tests/test_mesh_pb.py`, `tests/meshref.py`
- Modify: `docs/content-review.md` (new section "Comms": each message, its fields, the page opened)

**Interfaces:**
- Produces: global `MPB` (pure; no DOM, no `FK`):
  - `MPB.PORT = { TEXT: 1, POSITION: 3, NODEINFO: 4, WAYPOINT: 8 }`, `MPB.BROADCAST = 0xFFFFFFFF`
  - `MPB.enc.wantConfig(nonce: number) -> Uint8Array`
  - `MPB.enc.heartbeat() -> Uint8Array`
  - `MPB.enc.packet({ to, channel, id, portnum, payload: Uint8Array, wantAck?: boolean, hopLimit?: number }) -> Uint8Array` (a whole ToRadio)
  - `MPB.enc.waypoint({ id, lat, lon, expire, lockedTo, name, description, icon }) -> Uint8Array` (lat and lon in degrees)
  - `MPB.dec.fromRadio(bytes) -> msg | null`, where `msg.type` is one of:
    - `'myInfo'` `{ myNodeNum }`
    - `'nodeInfo'` `{ num, longName, shortName, position: { lat, lon, alt, time } | null, lastHeard, channel }`
    - `'channel'` `{ index, role: 'primary'|'secondary'|'disabled', name, psk: Uint8Array, positionPrecision }`
    - `'configComplete'` `{ id }`
    - `'rebooted'` `{}`
    - `'packet'` `{ from, to, channel, id, rxTime, portnum: number|null, payload: Uint8Array|null }` (null when still encrypted)
    - `'other'` `{}`
  - `MPB.dec.position(bytes) -> { lat, lon, alt, time } | null`, `MPB.dec.user(bytes) -> { longName, shortName } | null`, `MPB.dec.waypoint(bytes) -> { id, lat, lon, expire, lockedTo, name, description, icon } | null`
  - Times are epoch seconds as sent. Coordinates are degrees (the codec applies the 1e-7 scale).
- `tests/meshref.py`: `ref_from_radio(**kw) -> bytes` and friends, built on `meshtastic.protobuf.mesh_pb2` / `channel_pb2` / `portnums_pb2`; `pytest.importorskip('meshtastic')` at the top, and CI installs it: add `meshtastic` to whatever the repo uses to list test dependencies (if none, document `pip install meshtastic` in `README.md`'s test section).

Field numbers believed correct (verify every one against the Python package's descriptors, which are the authority, and record them in `docs/content-review.md`): ToRadio packet=1, want_config_id=3, heartbeat=7. FromRadio packet=2, my_info=3, node_info=4, config_complete_id=7, rebooted=8, channel=10. MeshPacket from=1, to=2, channel=3, decoded=4, encrypted=5, id=6, rx_time=7, hop_limit=9, want_ack=10. Data portnum=1, payload=2. Position latitude_i=1, longitude_i=2, altitude=3, time=4. User long_name=2, short_name=3. NodeInfo num=1, user=2, position=3, last_heard=5, channel=7. MyNodeInfo my_node_num=1. Channel index=1, settings=2, role=3. ChannelSettings psk=2, name=3, module_settings=7 (position_precision=1). Waypoint id=1, latitude_i=2, longitude_i=3, expire=4, locked_to=5, name=6, description=7, icon=8.

- [ ] **Step 1: Write the failing tests** in `tests/test_mesh_pb.py` (each runs the codec in the page with `page.evaluate` and compares with `meshref`):

```python
def test_waypoint_round_trip_matches_reference(page, app_url):
    # ours -> reference decodes the same values
    b = enc(page, 'waypoint', dict(id=305419896, lat=43.0125, lon=-76.0375, expire=0, lockedTo=0,
                                    name='Rally 1', description='Seen 22 Nov 14:32. gate', icon=0x1F6A9))
    w = mesh_pb2.Waypoint(); w.ParseFromString(b)
    assert (w.id, w.latitude_i, w.longitude_i, w.name, w.icon) == (305419896, 430125000, -760375000, 'Rally 1', 0x1F6A9)
    # reference -> ours decodes the same values
    assert dec(page, 'waypoint', w.SerializeToString())['lat'] == pytest.approx(43.0125, abs=1e-7)

def test_from_radio_every_type_matches_reference(page, app_url): ...   # myInfo, nodeInfo with and without position,
                                                                       # channel (psk b'\x01', 16 and 32 bytes; precision 0, 13, 32),
                                                                       # configComplete, rebooted, packet (POSITION, NODEINFO, WAYPOINT, encrypted)
def test_to_radio_matches_reference(page, app_url): ...                # wantConfig(nonce), heartbeat, packet(to=BROADCAST, channel=0)
def test_negative_and_large_values(page, app_url): ...                 # lat -43.0, lon -76.0, node numbers above 2**31, altitude -12
def test_unknown_fields_are_skipped(page, app_url): ...                # reference message + extra field 999 of each wire type
def test_garbage_never_throws(page, app_url): ...                      # every prefix of a valid message; 200 random buffers; a length of 2**31
```

- [ ] **Step 2: Run and see them fail** — `python3 -m pytest tests/test_mesh_pb.py -q` — FAIL: `MPB is not defined`.
- [ ] **Step 3: Implement `src/mesh-pb.js`.** A small reader (varint, fixed32, sfixed32, length-delimited, skip-by-wire-type, bounds-checked) and writer; every decoder wrapped so a malformed buffer returns `null` (or `{ type: 'other' }` from `fromRadio`).
- [ ] **Step 4: Run** the file, then the whole suite. PASS.
- [ ] **Step 5: Commit** `Comms: byte codec checked against the reference package`.

**Named risks for the reviewer:** signed versus unsigned 32-bit values in JS (`>>> 0`); sfixed32 negatives; varints above 2^32; strings as UTF-8.

---

### Task 2: The Bluetooth link and the fake radio

**Files:**
- Create: `src/mesh-link.js`, `tests/radio.py`, `tests/test_mesh_link.py`
- Modify: `build.py` (after `mesh-pb.js`)

**Interfaces:**
- Consumes: `MPB` (Task 1).
- Produces: global `MLINK`:
  - `MLINK.supported(bt = navigator.bluetooth) -> boolean`
  - `MLINK.create({ bluetooth, onMessage(msg), onState({ state, name, reason }) }) -> link`
  - `link.connect() -> Promise<boolean>` (must be called from a tap: opens the chooser filtered on the service UUID)
  - `link.reconnect() -> Promise<boolean>` (same device object, no chooser; false when there is none)
  - `link.disconnect()`, `link.send(bytes: Uint8Array) -> Promise<boolean>`, `link.state()`
  - States: `'off' | 'connecting' | 'syncing' | 'on' | 'lost'`. Reasons on `'off'`: `'cancelled'`, `'unsupported'`, `'failed'`, `'user'`.
  - `'on'` is reported only after `configComplete` with our nonce. On `'on'` the link has already delivered every start-up message to `onMessage`.
- `tests/radio.py`: `install(page, script=None)` adds an init script defining `window.FakeRadio` and replacing `navigator.bluetooth` with a fake whose device plays a scripted radio; Python helpers `radio.push(page, bytes)` (queue a FromRadio and notify), `radio.sent(page) -> list[bytes]`, `radio.drop(page)`, `radio.refuse(page, how)` (`'cancel'`, `'gatt'`, `'no-service'`), `radio.reboot(page)` (fromnum goes down). The default script answers `wantConfig` with: myInfo (num 0x0A0B0C01), primary channel "Team" with a 32-byte key and precision 32, three nodeInfos, configComplete.

UUIDs (from Meshtastic's client API page; confirm when building): service `6ba1b218-15a8-461f-9fa8-5dcae273eafd`, toradio `f75c76d2-129e-4dad-a1dd-7866124401e7`, fromradio `2c55e69e-4993-11ed-b878-0242ac120002`, fromnum `ed9da18c-a800-4f66-a670-aa7547e34453`.

Behaviour pinned: read `fromradio` until an empty read, at start-up and on every `fromnum` notification; one read loop at a time (a notification during a drain sets a "again" flag); writes go through one queue, one at a time; a heartbeat every 300 s while `'on'`; `gattserverdisconnected` gives `'lost'`; `fromnum` going down, or a `rebooted` message, restarts the start-up download; start-up not complete within 30 s gives `'off'`/`'failed'`; a second `connect()` while one is in flight returns the same promise.

- [ ] **Step 1: Write the failing tests** (`tests/test_mesh_link.py`): `test_start_up_download_reaches_on`, `test_messages_arrive_in_order_and_once`, `test_notification_during_a_drain_is_not_lost`, `test_send_queues_one_write_at_a_time`, `test_cancelled_chooser_goes_back_to_off` (reason `'cancelled'`), `test_refused_connection_goes_back_to_off` (reason `'failed'`), `test_double_connect_opens_one_chooser`, `test_drop_reports_lost_then_reconnect_reruns_download`, `test_reboot_restarts_download`, `test_garbage_message_does_not_stop_the_loop`, `test_stalled_start_up_times_out` (fake clock), `test_heartbeat_every_300_s` (fake clock), `test_unsupported_browser` (`navigator.bluetooth` undefined: `supported()` false, `connect()` false with `'unsupported'`).
- [ ] **Step 2: Run, see FAIL** (`MLINK is not defined`).
- [ ] **Step 3: Implement `src/mesh-link.js`.**
- [ ] **Step 4: Run the file and the whole suite. PASS.**
- [ ] **Step 5: Commit** `Comms: Bluetooth link and scripted fake radio`.

**Named risks:** a rejected GATT promise left unhandled (the test harness fails on any console error: keep that); two drains interleaving; a write while disconnected; timers left running after `disconnect()`.

---

### Task 3: `FK.mesh`, the switch, the channel verdict, teammates' data

**Files:**
- Create: `src/mesh.js`, `tests/test_mesh_state.py`
- Modify: `build.py` (after `tac-data.js`), `src/shell.html` (Settings: one switch row), `src/app.js` (`SESSION_ONLY` gains `'fk.meshTeam'`; `_test` gains `mesh`)

**Interfaces:**
- Consumes: `MPB`, `MLINK`, `FK.store`, `FK.emit`, `FK.on`.
- Produces `FK.mesh`:
  - `enabled() -> boolean` (stored `meshOn`), `setEnabled(on)`; `supported() -> boolean`
  - `status() -> { state, name, reason }` (the link's, `'off'` when disabled)
  - `channel() -> 'private' | 'public' | 'unknown'`; `positions() -> 'precise' | 'approx' | 'off' | 'unknown'`
  - `canShare() -> boolean` (state `'on'` and channel `'private'`)
  - `myNum() -> number | null`, `nameOf(num) -> string` (long name, else short name, else `'Radio ' + last four hex digits`)
  - `teammates() -> [{ num, name, lat, lon, t, heard }]` (`lat`/`lon` null when no position; `t` ms of the position, 0 when unknown; `heard` ms)
  - `connect()`, `reconnect()`, `disconnect()` (pass-through; `connect` only from a tap)
  - `sendWaypoint(wp) -> Promise<boolean>` (broadcast, channel 0, WAYPOINT port, random non-zero packet id; false unless `canShare()`)
  - Events on the bus: `'mesh'` (status, channel or positions changed), `'team'` (teammates changed), `'meshWaypoint'` with `{ wp, from, name }` (only while channel is `'private'` and `packet.channel === 0`).
- `FK._test.mesh = { feed(msg), link(state, name) }`: `feed` takes a decoded `MPB` message through the same path as a real one; `link` sets the status as the link would.

Rules pinned:
- Channel verdict from the `'channel'` message with role `'primary'`: `psk.length <= 1` is `'public'` (no key, or one of Meshtastic's well-known one-byte keys); 16 or 32 bytes is `'private'`. `positionPrecision` 32 is `'precise'`, 0 is `'off'`, anything else `'approx'`. The key is never stored, logged or exposed.
- While `'public'`: no `'team'` updates from the mesh (the stored list is kept but not added to), no `'meshWaypoint'`, `sendWaypoint` false.
- A teammate is a `nodeInfo` or a POSITION/NODEINFO packet with `channel === 0` whose `num`/`from` is not `myNum()`. A position with lat 0 and lon 0, or out of range, is ignored. A position time more than 24 h in the future is stored as `t: 0`.
- Teammates persist in `meshTeam` (session-only key: never in a backup), at most 100, least recently heard dropped first. Verdicts reset to `'unknown'` on every new start-up download.
- Coming to the foreground (`visibilitychange` to visible) while enabled and `'lost'`: `reconnect()`.
- Settings row: label "Radio link (testing)", hint "Connects Field Kit to a Meshtastic radio over Bluetooth. Android only." Turning it off disconnects.

- [ ] **Step 1: Failing tests:** `test_switch_off_by_default_and_nothing_shows`, `test_switch_off_never_touches_bluetooth` (a `navigator.bluetooth` getter that throws), `test_private_channel_verdict` (16 and 32 bytes), `test_public_channel_verdict` (empty and `b'\x01'`), `test_secondary_private_does_not_count`, `test_position_verdicts`, `test_teammates_from_download_and_live_packets`, `test_own_radio_is_not_a_teammate`, `test_channel_1_nodes_are_not_teammates`, `test_zero_zero_position_ignored`, `test_future_position_has_no_time`, `test_public_channel_emits_nothing`, `test_teammates_survive_reload_and_are_not_in_a_backup`, `test_send_waypoint_refused_on_public_and_when_off`, `test_send_waypoint_bytes_match_reference` (the ToRadio the fake radio received parses with `meshref` as a broadcast WAYPOINT on channel 0), `test_foreground_reconnects`.
- [ ] **Step 2: FAIL. Step 3: Implement. Step 4: whole suite PASS. Step 5: Commit** `Comms: mesh state, testing switch, channel verdict, teammates data`.

---

### Task 4: Radio button and Radio sheet

**Files:**
- Create: `src/mesh-ui.js`, `tests/test_mesh_ui.py`
- Modify: `src/shell.html` (button `#mRadio` in the map's button column, hidden unless enabled; `<dialog id="dlgRadio" class="sheet mk-sheet">`), `build.py` (after `tac-markers.js`)

**Interfaces:**
- Consumes: `FK.mesh` and its events, `FK.sheet`, `FK.relText`, `TGEOM.fmtDist`.
- Produces: `FK.radioSheet.open()`. The row for "Send all my shared markers again" is `#rdResend`, hidden in this task (Task 7 wires it).

Exact copy:
- Button `aria-label`: "Radio: off" / "Radio: connecting" / "Radio: connected" / "Radio: connection lost". Each state has its own icon shape, not colour alone.
- Not connected: button "Connect a radio"; lines "You need a Meshtastic radio that is already set up in the Meshtastic app." and "Close the Meshtastic app first: a radio talks to one app at a time."
- Reasons: cancelled: nothing shown. failed: "Couldn’t connect. If the Meshtastic app is open, close it and try again."
- Unsupported: "This phone’s browser can’t reach a radio. The Meshtastic app will still share your position and markers with the group." (no Connect button)
- Public channel: "This radio is on a public channel, so Field Kit is not sending or showing anything. Set up a private channel in the Meshtastic app and share it with your group."
- Positions off: "This channel is set to send no positions, so teammates won’t appear." Approximate: "This channel sends approximate positions, so teammates may show in the wrong place."
- Connected: `Connected to "<name>"`, "Channel: private", "Teammates (N)", rows `name · distance · age` or `name · no position yet`, button "Disconnect".

- [ ] **Step 1: Failing tests:** `test_no_button_when_switch_off`, `test_button_label_follows_state`, `test_sheet_not_connected_copy`, `test_connect_tap_opens_chooser_once` (double tap), `test_failed_connection_message_and_state_off`, `test_cancel_shows_no_error`, `test_unsupported_copy_and_no_connect_button`, `test_public_channel_warning`, `test_position_warnings`, `test_teammate_rows_sorted_by_distance_then_no_position`, `test_names_are_escaped` (a radio named `<img src=x onerror=1>`), `test_back_closes_the_sheet`, `test_sheet_fits_iphone_guard` (add `dlgRadio` to the `mk-sheet` guard in `tests/test_iphone.py`).
- [ ] **Steps 2 to 5** as before. Commit `Comms: radio button and Radio sheet`.

---

### Task 5: Marker-to-waypoint mapping (pure) and teammates on the map

**Files:**
- Create: `src/mesh-marker.js`, `src/tac-team.js`, `tests/test_mesh_marker.py`, `tests/test_team_map.py`
- Modify: `build.py`, `src/map.js` (a `map._fkTeam` layer group added after `_fkAreas` and before `_fkWps`; render on `'team'`), `src/shell.html` (`<dialog id="dlgMate" class="sheet mk-sheet">`, styles)

**Interfaces:**
- Produces global `MMK` (pure):
  - `MMK.ICON = { point: 0x1F4CD, camp: 0x26FA, vehicle: 0x1F699, water: 0x1F4A7, cache: 0x1F4E6, hazard: 0x26A0, rally: 0x1F6A9, observe: 0x1F52D, medical: 0x1F3E5, friend: 0x1F7E6, hostile: 0x2666, neutral: 0x1F7E9, unknown: 0x2753 }`
  - `MMK.kindFor(icon) -> kind | null`
  - `MMK.bytes(s) -> number` (UTF-8 length); `MMK.NAME_MAX = 29`, `MMK.NOTE_MAX = 99`
  - `MMK.seen(t: ms) -> string` e.g. `'Seen 22 Nov 14:32. '` (local time, English month, 24 h)
  - `MMK.noteRoom(kind) -> number` (99 for a place kind; 99 minus the prefix's bytes for an affiliation kind)
  - `MMK.fits(marker) -> { ok, name: boolean, note: boolean }`
  - `MMK.toWaypoint(marker, wid, keep = { icon: 0, expire: 0 }) -> wp` (affiliation kinds get the prefix; `keep.icon` wins when the marker's kind is `'point'` and `keep.icon` is a foreign icon)
  - `MMK.fromWaypoint(wp, now) -> { name, note, kind, lat, lon, t, rx: boolean, icon, expire } | null` (null for bad coordinates; empty name becomes `'Marker'`; a readable prefix is removed from the note and becomes `t`, with the year chosen as the latest that puts it at or before `now + 24 h`; otherwise `t = now`, `rx = true`)
- Produces `FK.team.render()` and the teammate sheet. A teammate pin: class `tm-pin`, plus `old` when `now - t > 30 min` or `t === 0`; label is the name and the age (`ageText`-style: "4 min ago"), no age when `t` is 0 or in the future (then "age unknown"). Tap opens `#dlgMate`: name, grid, distance and bearing (`FK.relText`), "Position from 4 min ago", buttons "Go to" (`FK.tac.setTarget({ type: 'point', lat, lon, name })`) and "Close". No edit, no delete. Inert while a tool mode is on.

- [ ] **Step 1: Failing tests** (`test_mesh_marker.py`): every kind round-trips through `toWaypoint`/`fromWaypoint`; unknown icon becomes `'point'` and keeps the icon; `seen` prefix round-trips across midnight and across New Year; a prefix timed after `now` rolls to last year; no prefix gives `rx`; byte counting for "Café ⛺ north ridge lookout"; `fits` false at 30 bytes, true at 29; lat 0 lon 0 gives null; lat 91 gives null; markup in a name is returned as text (escaping is the renderer's job, asserted in the map test).
- [ ] **Step 2: Failing tests** (`test_team_map.py`): pins drawn for teammates with a position only; `old` class after 30 minutes (fake clock); no age for a future time; my own radio absent; a name with markup is escaped; tap opens the sheet with grid, distance and age; Go to sets a point target; the sheet has no Save or Delete; pins sit under marker pins; nothing drawn when the switch is off; `dlgMate` in the iPhone `mk-sheet` guard; the 30-minute flip happens without a new `'team'` event (a one-minute redraw timer while the map is showing).
- [ ] **Steps 3 to 5:** implement, whole suite, commit `Comms: marker mapping and teammates on the map`.

---

### Task 6: Shared record in marker storage, incoming rules

**Files:**
- Create: `src/tac-share.js`, `tests/test_share_rules.py`
- Modify: `src/tac-data.js` (`cleanMarker` keeps a validated `net`; new `FK.tac.setNet`, `FK.tac.addShared`), `build.py`, `tests/test_tac_data.py`

**Interfaces:**
- Marker gains optional `net: { wid: number, from: number, by: string, t: number, chBy: string, chT: number, icon: number, expire: number, pending: boolean, rx: boolean }`. `cleanMarker` keeps `net` only when `wid` is an integer in 1..0xFFFFFFFF and the rest have the right types (strings cut to 40); otherwise `net` is dropped and the marker is private. Markers stored before this release have no `net`.
- `FK.tac.setNet(id, net | null) -> boolean`; `FK.tac.addShared({ name, lat, lon, kind, note, t, net }) -> marker | null`; `updateMarker`'s `PATCH` gains `t` (a finite time).
- Produces `FK.share`:
  - `share(id) -> 'sent' | 'pending' | 'toolong' | 'no'`
  - `resend(id)`, `resendMine() -> number` (queued count; 3 s apart)
  - `unshare(id)` (private copy, nothing sent)
  - `remove(id, everyone: boolean)`
  - `changed(id)` (call after a shared marker's save or move: sends again under the same `wid`)
  - `isShared(id)`, `mine(id)` (`net.from === FK.mesh.myNum()`)
  - Storage: `meshTombs` `[{ wid, t }]`, kept 30 days.

Rules pinned (each is a test):
- Incoming `'meshWaypoint'`: `wid` in tombs: ignore. `expire` non-zero and at or before now: it is a delete. Otherwise `MMK.fromWaypoint`; null: ignore. Known `wid`: update name, note, kind, position, `t` (only when the prefix gave one), `net.chBy`, `net.chT`. New `wid`: `addShared` with `net.from` = sender, `net.by` = sender's name.
- Incoming delete: remove the marker and add a tomb, **unless `mine(id)`**: then `setNet(id, null)` and the note gains `Deleted by <name>.` at its start (cut to the note limit), and a tomb is added.
- `remove(id, true)`: send the waypoint with `expire = 1` (delete on the wire is believed to be a past expiry: confirm from the official apps' documentation or the reference package before relying on it, and record the source), add a tomb, remove locally. `remove(id, false)`: tomb and local removal, nothing sent.
- `share` when `MMK.fits` fails: `'toolong'`, nothing changed. When `!FK.mesh.canShare()`: `net.pending = true`, `'pending'`. New `wid`: random 1..0xFFFFFFFF not already held.
- On `'mesh'` reaching `canShare()`: every `pending` marker is sent, 3 s apart, and `pending` cleared on a true result.
- Expiry: a held marker whose `net.expire` passes is removed with a tomb (checked on load, on each incoming message, and each minute while the map shows). Field Kit's own shares send `expire = 0`; a re-send keeps the stored `expire` and `icon`.
- Cap: at most 500 markers with a `net` not `mine`; past that the one with the oldest `net.t` is dropped (no tomb) and `FK.share.dropped()` counts it for the Radio sheet line "Some older markers from teammates were dropped: this phone holds 500."
- A burst (10,000 incoming in one tick) costs one storage write and one `'wps'` event per animation frame, not one per message.
- Backup and restore carry `net` and `meshTombs` as they are.

- [ ] **Step 1: Failing tests** for each rule above, plus: `test_old_markers_have_no_net_and_are_never_sent` (seed v7.10 markers, connect, assert the fake radio received no WAYPOINT), `test_bad_net_in_a_backup_is_dropped`, `test_stale_resend_overwrites` (documents the accepted limit).
- [ ] **Steps 2 to 5:** FAIL, implement, whole suite, commit `Comms: shared markers in storage and the incoming rules`.

**Named risks:** `fixTarget` when an incoming delete removes the navigation target; two tabs writing whole lists (existing limit); the "Deleted by" line pushing a note past its limit.

---

### Task 7: The marker sheet: Share, limits, delete question, Send again

**Files:**
- Modify: `src/tac-markers.js`, `src/shell.html` (`#dlgMarker`: a Share row `#mkShare` (checkbox styled as a switch) with status line `#mkShareLine`, button `#mkResend`), `src/mesh-ui.js` (wire `#rdResend`), `tests/test_markers.py`
- Create: `tests/test_marker_share.py`

**Interfaces:**
- Consumes: `FK.share`, `FK.mesh`, `MMK`, `FK.sheet.ask`.

Behaviour pinned:
- The Share row shows only when `FK.mesh.enabled()` and (`FK.mesh.canShare()` or the marker has a `net`). New markers: Share off.
- With Share on, the name box counts bytes against 29 and the note against `MMK.noteRoom(kind)`; the counter line reads "N characters left" using the remaining bytes; over the limit, Save is refused with "A shared marker’s name can be 29 characters and its note N. Shorten it, or turn Share off." Nothing is ever cut silently. Changing kind re-checks.
- Status line: "Shared by <name>" (or "Shared by you"); "Changed by <name>, 3 min ago" when `chBy`; "Not sent yet: no radio connected" when `pending`; for an affiliation marker with `rx`: "Received 5 min ago" in place of "Marked ...".
- Save with Share newly on: `FK.share.share(id)`. Save or Move on a shared marker: `FK.share.changed(id)`. Share switched off and saved: `FK.share.unshare(id)`.
- Delete on a shared marker: `FK.sheet.ask` titled "Delete this marker?" with "Delete for everyone", "Delete on this phone only", "Cancel". "Delete for everyone" is offered only when `FK.mesh.canShare()`.
- `#mkResend` "Send again" shows on a shared marker when `canShare()`; toast "Sent".
- An incoming change to the marker whose sheet is open: with no unsaved typing the sheet refills; with unsaved typing the fields are kept and `#mkShareLine` reads "This marker was changed by <name> while you were editing. Saving keeps your version." An incoming delete of the open marker closes the sheet with toast "<name> deleted this marker" (or, for the maker, refills it as private).
- `#rdResend` "Send all my shared markers again": `FK.share.resendMine()`, toast "Sending N markers".
- The dirty guard's snapshot includes the Share state.

- [ ] **Step 1: Failing tests** for each line above, using real key presses and real taps (a fix to event handling here needs them: v7.10), with `history.go` slowed for the delete question and the incoming-delete close (v7.8's sheet faults). Include `test_share_row_absent_when_switch_off`, `test_bytes_not_characters_at_the_limit` ("Café ⛺ north ridge lookout"), `test_existing_marker_tests_unchanged` (run `tests/test_markers.py` untouched).
- [ ] **Steps 2 to 5:** FAIL, implement, whole suite, commit `Comms: Share on the marker sheet`.

---

### Task 8: Records, version, final reviews, stop for Jordan

**Files:**
- Create: `docs/comms-rulings.md` (every decision made during the build with its cost if wrong; what could not be tested; the phone check)
- Modify: `docs/iphone-first-test.md` (one line: Radio link is Android only), `src/app.js` and `src/sw.js` (version 7.11, or the next free number after `git fetch origin main` and a merge), `README.md` if the test dependency is documented there

- [ ] **Step 1:** `git fetch origin main`, merge into `comms`, read what changed, take the next free version number.
- [ ] **Step 2:** Three final reviews in parallel: a whole-branch code review (told to read `sheet.js` and `tac-markers.js` as one design and to triage every deferred minor); a protocol review (re-opens the published definitions and the client API page, re-derives three messages by hand, and checks the fake radio's script against the documented flow); a tester who drives the built app at 360 x 640 with the fake radio, as a person, with screenshots: switch on, connect, public-channel refusal, teammates ageing, share / edit / move / delete both ways, drop and return, day and night mode.
- [ ] **Step 3:** One fix round with a ruling beside each finding, then one re-check that drives the app.
- [ ] **Step 4:** Whole suite. `python3 build.py --release /tmp/out` (not the repo root).
- [ ] **Step 5:** Push `comms`. **Stop.** Give Jordan the decision ledger and the phone-check list. Nothing goes to `main` without his go.

Phone check to hand over (real radios; cannot be proved in a build session): the switch appears in Settings and is off; pairing and PIN on each radio model; connect, and the name shown is the radio's; a factory-fresh radio is refused as public; after the private channel is set in the Meshtastic app, teammates appear and age; a marker shared from Field Kit shows in the Meshtastic app on an iPhone with the right emoji, and edits, moves and "delete for everyone" travel both ways; a Hostile marker shows "Seen ..." on the iPhone and the right age in Field Kit; lock the screen for five minutes and come back (reconnects by itself, missed positions arrive); close the app fully and reopen (one tap reconnects); with the Meshtastic app holding the radio, Field Kit says so; with the switch off again, every trace of the radio is gone.
