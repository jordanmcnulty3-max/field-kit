# Comms release 1: the live radio link (design)

Date: 2026-11-22. Target version: 7.11 (the next free number at release; rule 4 of the status doc).
Working branch: `comms`.

## Intent

The group's stated end goal is to see each other live on a map, off-grid. Each person carries a
Meshtastic radio. This release makes Field Kit talk to that radio over Bluetooth, so the Tactical
map shows where teammates are and markers can be shared across the group, including with iPhone
users who run the official Meshtastic app.

"Comms" here is the live link only. The Survival content pack on comms (radios, setup, signals)
is a separate release.

## Goals (Jordan's, 2026-11-22)

1. Connect Field Kit to a Meshtastic radio.
2. See teammates' positions on the Tactical map.
3. Share markers that teammates see and can edit and delete, in both directions, with iPhone users
   on the official Meshtastic app.

## Non-goals for this release

- Texting (next comms release, after this one is proven on real radios).
- Routes, areas and range rings over the radio (they need the TAK V2 format; later).
- Creating or sharing a channel inside Field Kit (proposal below; the official app does it).
- Changing any radio setting, or firmware updates.
- Sending the phone's own GPS position to the radio. The radio's own GPS reports its position.
  (Worth revisiting if the chosen radio's GPS proves weak.)
- Any Bluetooth on iPhone. Safari has no Web Bluetooth.

## Anti-goals (a failure even if it works)

- Broadcasting anything the user did not choose to share. Markers saved before this update must
  never go out on their own.
- Sending the group's positions or markers on a channel whose key is public.
- A teammate's old position looking current.
- Field Kit telling the user to act against a person. It records and shows; it never advises.
- Channel keys, the home town or real coordinates in the public repo. Tests use 43.0, -76.0.

## Constraints

- **Offline, no bundler.** The app is one `index.html` built by `build.py` from `src/`. New code
  is plain script files added to the list in `build.py`.
- **Android Chrome only for the link.** Web Bluetooth needs HTTPS (GitHub Pages is) and a tap to
  choose the device. The link drops when the app goes to the background or the screen locks.
- **One app per radio.** If the Meshtastic app is connected to the radio, Field Kit cannot connect.
- **A build session has no Bluetooth.** Everything real-radio goes on Jordan's phone check, and
  the release is not proven until he has run it on two radios.
- **Status doc rules bind this work**, in particular rule 14: Tactical sheets go through
  `src/sheet.js`; no `prompt`, `confirm` or `alert`; words on screen are "Marker", never
  "waypoint". Read `sheet.js` whole before touching it.

## Approaches

1. **Copy in the official Meshtastic JavaScript SDK.** Least code, and it ships a fake radio. But
   its licence is GPL-3.0 on the pages that state one (and listed as Apache-2.0 elsewhere), which
   would oblige Field Kit to be GPL-3.0; it is built around a reactive-state library and expects a
   bundler; and the package has been renamed and restructured several times.
2. **Write our own small link (chosen by Jordan).** The Bluetooth connection plus a reader and
   writer for only the messages this release needs. No licence tie, no bundler, small. The cost:
   we maintain it, and it is our reading of the published protocol.
3. **Leave Bluetooth to the Meshtastic app and exchange files.** Rejected: not live, and Jordan
   wants the app self-contained.

**Rule for approach 2:** write from the published protocol documentation and message definitions
(field names, numbers and types are facts of the protocol). Do not copy code from any Meshtastic
repository into `src/`.

## What Jordan decided (as he decided it)

- Shared markers travel as standard Meshtastic waypoints, so the official app sees and edits them
  (option A, decided before this chat).
- **Each marker has a Share switch, off by default.** Nothing already saved is broadcast.
- **Every shared marker is open:** anyone in the group can edit, move or delete it.
- **When a teammate deletes a marker you made, it goes from everyone's map except yours.** On the
  maker's phone it stays as a private marker with a note saying who deleted it.
- **Teammates look different from Friend markers:** a blue ring with the radio's name and the age
  always showing; dashed and hollow once older than 30 minutes; never removed for age. Tapping one
  shows name, grid, distance and bearing, age and Go to. No edit, no delete.
- Build our own link (approach 2); test on real radios when they arrive.
- **The link ships switched off.** Settings gets a "Radio link (testing)" switch, off by default.
  With it off there is no radio button, no Radio sheet and no Share switch, and no Bluetooth code
  runs. Jordan turns it on for the phone check; the switch is removed once the link is proven.
- **The primary channel must be private** (see "Is the channel private?").
- **A shared Friend, Hostile, Neutral or Unknown marker carries when it was seen** at the start of
  its note, for example "Seen 22 Nov 14:32", so its age is true on every phone and iPhone users
  see it too.

## The design

### Parts

| File | Job |
|---|---|
| `src/mesh-pb.js` | Reads and writes the handful of protocol messages as bytes. Pure, no browser calls. |
| `src/mesh-link.js` | The Bluetooth connection: choose device, connect, the start-up download, the read loop, the send queue, reconnect. Knows nothing about maps. |
| `src/mesh.js` | `FK.mesh`: the state the rest of the app reads (link status, my radio, the channel verdict, teammates) and the two commands (send a marker, delete a marker). Emits events on the app's bus. |
| `src/tac-team.js` | Teammates on the map and the teammate sheet. |
| `src/mesh-ui.js` | The radio button on the map and the Radio sheet. |
| `src/tac-data.js`, `src/tac-markers.js` | Markers gain the shared state and the Share switch. |

Each part can be tested alone: the codec against bytes, the link against a fake Bluetooth device,
the map parts against `FK.mesh` fed by a test hook.

### The link (facts from Meshtastic's client API page; verify each when building)

- One Bluetooth service, `6ba1b218-15a8-461f-9fa8-5dcae273eafd`, with three endpoints: `toradio`
  (write), `fromradio` (read), `fromnum` (notify).
- Start-up: write a "want config" request with a random number; read `fromradio` repeatedly until
  an empty read; the radio sends its own details, its channels and settings, every radio it knows
  (with last position), then echoes the number to say it is done. Dispatch on each message's
  type; do not depend on the order.
- After that, a `fromnum` notification means "read `fromradio` until empty".
- If `fromnum` goes down, the radio rebooted: start again.
- Sending: write one message to `toradio`. Writes go through one queue, one at a time.
- Messages needed: ToRadio, FromRadio, MyNodeInfo, NodeInfo, User, Position, Channel and its
  settings, MeshPacket, Data, Waypoint. Unknown fields and unknown message types are skipped, never
  an error: the firmware will add fields.

### Is the channel private?

Field Kit reads the radio's primary channel. If its key is the public default (or there is no key),
Field Kit connects but **sends nothing and shows nothing from the mesh**, and the Radio sheet says
why and what to do (set up a private channel in the Meshtastic app and share it with the group by
QR). **Jordan's decision (2026-11-22): strict.** The primary channel itself must be private; a
public primary with a private secondary channel is refused the same way, because Meshtastic sends
markers on the primary channel only. Field Kit never displays, stores or exports the key.

The Radio sheet also warns when the channel is set to send no position, or an approximate one
(a per-channel setting in Meshtastic), because then teammates will not appear or will appear in
the wrong place.

### Teammates

- A teammate is any other radio the connected radio knows on the primary channel. My own radio is
  not drawn (the blue dot is me).
- Position and its time come from the start-up download and then from live position messages.
  The age shown is from the position's own time; if it has none, from when the radio last heard it.
- A radio with no position yet is listed in the Radio sheet ("no position yet"), not drawn.
- Teammates are kept on the phone between sessions (last known position survives a restart and a
  dropped link) and are **not** written to a backup: a stale position must not pass as current on
  another phone, as with the user's own fix today.
- Drawn in their own map layer, above areas and below markers.

```
   ◉ Mike            ◌ Sam              tap ->  Mike
     4 min ago         52 min ago               18T VK 1234 5678
                                                 1.2 km, 045° from you
                                                 Position from 4 min ago
                                                 [ Go to ]   [ Close ]
```

Go to uses the existing point target (never saved as a marker); it does not follow the teammate as
they move in this release.

### Shared markers

- A marker gains a shared record: the waypoint's number, the radio that made it, that radio's
  name, and when it was last sent or received. No record means private, which is every marker that
  exists today.
- **Share switch on the marker sheet**, shown only when a radio is connected on a private channel
  (or the marker is already shared). Turning it on and pressing Save sends it. Saving any later
  change sends it again under the same number. Move sends it again.
- **Limits.** A shared marker's name is at most 30 characters and its note 100 (Meshtastic's
  limits; check whether they are bytes or characters, and use the stricter). With Share on, the
  sheet enforces them and says so; turning Share on for a longer marker asks the user to shorten
  it, never cuts it silently.
- **Kinds travel as the emoji icon** (one code point each; my proposal):

  | Kind | Icon | Kind | Icon |
  |---|---|---|---|
  | Point | 📍 | Observation point | 🔭 |
  | Camp | ⛺ | Medical | 🏥 |
  | Vehicle | 🚙 | Friend | 🟦 |
  | Water | 💧 | Hostile | ♦ |
  | Cache | 📦 | Neutral | 🟩 |
  | Hazard | ⚠ | Unknown | ❓ |
  | Rally point | 🚩 | | |

  An incoming marker whose icon is not in the table becomes a Point that shows its own emoji, and
  keeps that emoji when Field Kit sends it again, so an iPhone user's icon is never rewritten.
- **Seen time.** For the four affiliation kinds, Field Kit writes "Seen DD Mon HH:MM" (24-hour,
  the sender's local time, about 18 characters) at the start of the outgoing note, from the
  marker's own marked time, and does not show that prefix in its own note box. The user's note
  gets the remaining characters, and the sheet's counter reflects that. On receipt Field Kit reads
  the prefix back into the marker's time, so the 24-hour dashed rule works as it does today. An
  affiliation marker arriving without a readable prefix (made in the official app) is timed at
  receipt and its sheet says "Received ..." in place of "Marked ...". The year is taken as the
  most recent one that puts the time in the past. Place kinds carry no prefix.
- **Incoming marker:** a number Field Kit already holds updates that marker; a new number adds
  one. The marker sheet shows "Shared by Mike" and "Changed by Sam, 3 min ago".
- **Deleting a shared marker** in Field Kit asks: "Delete for everyone" or "Delete on this phone
  only". (The official app offers the same two.) An incoming delete removes the marker, except on
  the maker's phone, where it becomes private with "Deleted by Sam" added to the note.
- **Stop sharing** (Share switched off on a marker you hold) makes your copy private and sends
  nothing; others keep their copies.
- **An incoming change while the same marker's sheet is open with unsaved typing:** the typing is
  kept, a line in the sheet says the marker changed, and Save wins. Named risk: this touches
  `sheet.js`'s guard and the sheet's snapshot.
- **Radios do not store markers.** A teammate whose radio was off or out of range when a marker
  was sent never gets it. So a shared marker's sheet has **Send again**, and the Radio sheet has
  "Send all my shared markers again" (spaced out, a few seconds apart, to respect airtime). No
  automatic re-sending in this release.
- Markers received from the mesh while on a public channel: none (see above).
- **Deleted markers stay deleted (my call).** Field Kit remembers the number of every shared
  marker deleted here ("for everyone" or "on this phone only") or deleted by a teammate, for 30
  days, and ignores anything arriving under that number. Without this, a teammate who missed the
  delete would bring the marker back for everyone with one Send again.
- **Send again** on one marker is open to anyone who holds it (a deliberate act). **"Send all my
  shared markers again" sends only markers this phone made**, so one person cannot overwrite the
  whole group's edits with old copies.
- **Accepted limit:** a waypoint carries no version. A Send again from a phone holding an older
  copy overwrites a newer edit. The sheet's "Changed by ..., ... ago" line is how a user notices.
- **Expiry (my call).** Field Kit's own shared markers never expire. An incoming marker with an
  expiry is removed at that time, as it is on the official apps, and keeps its expiry if Field Kit
  sends it again. Delete and expiry are one rule: a marker whose expiry has passed is gone.
- **Cap (my call):** at most 500 markers received from the mesh are held; past that the oldest
  received marker that this phone did not make is dropped, with a line in the Radio sheet.

### Where it lives

A radio button joins the map's buttons, showing the link state at a glance (off, connecting,
connected, problem). It opens the **Radio sheet**:

```
 Radio
 ● Connected to "Jordan's M1"          [ Disconnect ]
 Channel: private

 Teammates (3)
  Mike     1.2 km   4 min ago
  Sam      3.4 km   52 min ago
  Alex     no position yet

 [ Send all my shared markers again ]
```

Not connected: one button, "Connect a radio", and two lines on what is needed (a Meshtastic radio
already set up in the Meshtastic app; close that app first). On a phone whose browser has no
Bluetooth (every iPhone): the sheet says Field Kit cannot reach a radio on this phone, and that
the Meshtastic app will still share positions and markers with the group.

### Dropped links

- Coming back to the foreground, Field Kit reconnects to the same radio by itself and reruns the
  start-up download (the radio kept collecting while the phone was away).
- After the app is fully closed and reopened, the browser needs a tap: the radio button shows
  "off" and the Radio sheet's button reconnects.
- A marker saved with Share on while the link is down is kept, marked "not sent yet", and sent on
  the next connection.
- While disconnected, teammates stay on the map with their ages growing.

## Testing

- **Codec:** bytes checked against an independent implementation. Preferred: the official
  `meshtastic` Python package, installed for tests only, encodes and decodes the same messages;
  our codec must agree both ways. It is a test tool and is never copied into the app.
- **Link:** a fake Bluetooth device in the test page (replacing `navigator.bluetooth`) that plays
  a scripted radio: start-up download, live packets, a reboot, a drop, a refused connection.
- **Map and markers:** through `FK.mesh` with a `FK._test` hook, in the style of `tests/tac.py`.
- **Whole suite after every task; a reviewer after every task; a final tester who drives the built
  app at phone size** (status doc rules 7 and 8).
- **Phone check, two radios:** pairing and PIN; connect; a teammate appears and ages; share, edit,
  move and delete a marker both ways between Field Kit and the Meshtastic app on an iPhone; lock
  the screen and come back; the public-channel refusal on a factory-fresh radio.

## Left to the builder

- Exact field numbers and types, from the published definitions.
- Whether the radio needs a periodic keep-alive message, and hop and acknowledgement settings for
  a broadcast marker.
- How a delete is expressed on the wire (believed: the same marker sent with an expiry in the
  past), confirmed against the official apps' behaviour.
- Whether Chrome on Android can reconnect without a tap after a reload.
- Icons for the radio button states; exact wording within the on-screen word rules.
- Storage key names and the backup's handling of the shared record.

## Known risks

1. **Our reading of the protocol may be wrong on a real radio.** Mitigated by the Python
   cross-check; only the phone check proves it.
2. **Pairing.** Radios with a screen show a PIN; others use a fixed one. Chrome on Android is
   expected to hand this to the system; unproven until the phone check.
3. **The marker sheet is the most fault-prone code in the app** (five history faults in v7.8).
   Share, limits, the delete question and incoming changes all land there.
4. **Clocks.** A teammate's age depends on the radio's clock and the phone's agreeing. A position
   timed in the future shows no age rather than a wrong one, as markers do today.
5. **Airtime.** 10 to 15 radios on one channel is fine for positions at Meshtastic's defaults;
   re-sending many markers at once is not, hence the spacing.
