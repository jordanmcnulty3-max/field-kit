/* ---------- MMK: Field Kit marker <-> Meshtastic waypoint (pure: no DOM, no FK) ----------
   A waypoint has an id, a position, an emoji icon (a code point), a name (30 bytes on the wire: 29 usable here) and a
   description (100 bytes: 99 here). The icon carries the marker's kind. An affiliation marker (Friend, Hostile, Neutral,
   Unknown) also carries when it was seen, as a prefix of the description: "Seen 22 Nov 14:32. ", written and read in this
   phone's local time. A waypoint from another app has no such prefix; it is taken as seen when it arrived. */
const MMK = (() => {
  const ICON = { point: 0x1F4CD, camp: 0x26FA, vehicle: 0x1F699, water: 0x1F4A7, cache: 0x1F4E6, hazard: 0x26A0, rally: 0x1F6A9,
    observe: 0x1F52D, medical: 0x1F3E5, friend: 0x1F7E6, hostile: 0x2666, neutral: 0x1F7E9, unknown: 0x2753 };
  const AFFIL = ['friend', 'hostile', 'neutral', 'unknown'];
  const NAME_MAX = 29, NOTE_MAX = 99, DAY = 864e5;
  const MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const BY_ICON = new Map(Object.entries(ICON).map(([k, v]) => [v, k]));
  const kindFor = icon => BY_ICON.get(icon) || null;
  const isAffil = kind => AFFIL.includes(kind);

  /* UTF-8 length of a string, counted by hand (a lone surrogate is 3 bytes, as the encoder's replacement character). */
  function cpBytes(c) { return c < 0x80 ? 1 : c < 0x800 ? 2 : c < 0x10000 ? 3 : 4; }
  const bytes = s => { let n = 0; for (const ch of String(s == null ? '' : s)) n += cpBytes(ch.codePointAt(0)); return n; };
  /* The longest start of s that fits in max bytes, never cutting a character in half. */
  function clip(s, max) {
    s = String(s == null ? '' : s);
    let n = 0, out = '';
    for (const ch of s) { const b = cpBytes(ch.codePointAt(0)); if (n + b > max) break; n += b; out += ch; }
    return out;
  }

  const p2 = n => String(n).padStart(2, '0');
  const seen = t => { const d = new Date(t); return `Seen ${d.getDate()} ${MON[d.getMonth()]} ${p2(d.getHours())}:${p2(d.getMinutes())}. `; };
  /* The prefix is up to 19 bytes ("Seen 22 Nov 14:32. "; a day under 10 is one byte shorter). The room for a note keeps
     the longest, so the answer does not depend on the day. */
  const PREFIX_MAX = 19;
  const noteRoom = kind => isAffil(kind) ? NOTE_MAX - PREFIX_MAX : NOTE_MAX;
  const fits = m => {
    const name = bytes(m && m.name) <= NAME_MAX, note = bytes(m && m.note) <= noteRoom(m && m.kind);
    return { ok: name && note, name, note };
  };

  /* A marker as the waypoint to send. Too long a name or note is cut at a character boundary (fits() says beforehand).
     keep: what an earlier waypoint with this id had. Its expiry is kept, and so is its icon when this marker is a plain Point
     and that icon is one this app has no kind for (another app's emoji), so a resend does not change it. */
  function toWaypoint(m, wid, keep) {
    keep = keep || {};
    const kind = ICON[m.kind] ? m.kind : 'point';
    let icon = ICON[kind];
    if (kind === 'point' && Number.isInteger(keep.icon) && keep.icon > 0 && !kindFor(keep.icon)) icon = keep.icon;
    const stamp = isAffil(kind) && m.t > 0 ? seen(m.t) : '';
    return { id: wid, lat: m.lat, lon: m.lon, expire: keep.expire > 0 ? keep.expire : 0, lockedTo: 0,
      name: clip(m.name, NAME_MAX), description: stamp + clip(m.note, noteRoom(kind)), icon };
  }

  /* "Seen 22 Nov 14:32. " at the start of a description: the time as ms, the text after it, or null. The year is the latest
     one that puts the time at or before now + 24 h (a little ahead is a phone clock a little off; further ahead is last year). */
  const PREFIX = /^Seen (\d{1,2}) (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) (\d{2}):(\d{2})\. /;
  function parseSeen(text, now) {
    const m = PREFIX.exec(text);
    if (!m) return null;
    const day = +m[1], mon = MON.indexOf(m[2]), hh = +m[3], mm = +m[4];
    if (day < 1 || day > 31 || hh > 23 || mm > 59) return null;
    const limit = now + DAY;
    for (let y = new Date(limit).getFullYear(), n = 0; n < 8; y--, n++) {
      const d = new Date(y, mon, day, hh, mm);
      if (d.getMonth() !== mon || d.getDate() !== day) continue;   // 29 Feb in a year without one
      if (d.getTime() <= limit) return { t: d.getTime(), rest: text.slice(m[0].length) };
    }
    return null;
  }

  const okPos = (lat, lon) => typeof lat === 'number' && typeof lon === 'number' && Number.isFinite(lat) && Number.isFinite(lon) &&
    Math.abs(lat) <= 90 && Math.abs(lon) <= 180 && !(lat === 0 && lon === 0);   // 0, 0 is a radio with no position
  /* A received waypoint as a marker's fields, or null when its position is no place. The text is returned as it came (it is
     another person's text; whoever draws it escapes it). A foreign icon gives a Point that still reports the icon.
     t and rx: for an affiliation marker with the prefix, t is the time in it and rx is false; otherwise t is `now` and rx is
     true (received just now). A Point or other place never has a prefix, so it is always rx. */
  function fromWaypoint(wp, now) {
    if (!wp || !okPos(wp.lat, wp.lon)) return null;
    const icon = Number.isInteger(wp.icon) && wp.icon > 0 ? wp.icon : 0;
    const kind = kindFor(icon) || 'point';
    const name = String(wp.name == null ? '' : wp.name).trim() || 'Marker';
    let note = String(wp.description == null ? '' : wp.description), t = now, rx = true;
    if (isAffil(kind)) {
      const s = parseSeen(note, now);
      if (s) { t = s.t; rx = false; note = s.rest; }
    }
    return { name, note, kind, lat: wp.lat, lon: wp.lon, t, rx, icon, expire: Number.isFinite(wp.expire) && wp.expire > 0 ? wp.expire : 0 };
  }

  return { ICON, kindFor, bytes, NAME_MAX, NOTE_MAX, seen, noteRoom, fits, toWaypoint, fromWaypoint };
})();
