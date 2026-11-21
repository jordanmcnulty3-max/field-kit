/* ---------- Import and export: GPX and KML files ----------
   Two parts kept apart. TIO is pure: text in, text or plain records out (DOMParser is the only browser API it uses; no storage,
   no FK). The IIFE after it holds the Export and Import sheets and TIO.merge, which stores through FK.tac.
   Field Kit's own files carry each item's kind, type and ring radii as extra data (GPX <extensions> in the fk namespace, KML
   <ExtendedData>), so they read back exactly; other apps ignore it. Nothing read from a file is ever put into the page as markup:
   only plain strings come out of TIO, and the sheets show them with textContent. Nothing a file refers to (links, icons,
   schemas, entities) is fetched. */
const TIO = (() => {
  const NS = 'https://jordanmcnulty3-max.github.io/field-kit/ns/1';
  /* The same ids and labels as FK.tac.KINDS (a test keeps them equal); GPX <sym> carries the label. */
  const KINDS = [
    ['point', 'Point'], ['camp', 'Camp'], ['vehicle', 'Vehicle'], ['water', 'Water'], ['cache', 'Cache'], ['hazard', 'Hazard'],
    ['rally', 'Rally point'], ['observe', 'Observation point'], ['medical', 'Medical'],
    ['friend', 'Friend'], ['hostile', 'Hostile'], ['neutral', 'Neutral'], ['unknown', 'Unknown']
  ].map(([id, label]) => ({ id, label }));
  const KIND_IDS = new Set(KINDS.map(k => k.id));
  const LABEL_KIND = new Map(KINDS.map(k => [k.label.toLowerCase(), k.id]));
  /* MAX_PTS, MAX_SHAPES and MAX_NAME are tac-data's limits (a test keeps MAX_NAME equal; plan() is given MAX_SHAPES). */
  const MAX_PTS = 200, MAX_ITEMS = 5000, MAX_MARKERS = 2000, MAX_R = 50000, MAX_SHAPES = 100, MAX_NAME = 60;

  const fin = v => typeof v === 'number' && Number.isFinite(v);
  const pad = n => String(n).padStart(2, '0');
  /* Local date, YYYY-MM-DD. */
  const day = t => { const d = new Date(fin(t) ? t : Date.now()); return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`; };

  /* ---------- Writing ---------- */
  /* Characters XML 1.0 forbids: control characters other than tab, LF and CR, U+FFFE/U+FFFF, and lone surrogates (a pair is kept). */
  const BAD = /[\uD800-\uDBFF][\uDC00-\uDFFF]|[\uD800-\uDFFF]|[\u0000-\u0008\u000B\u000C\u000E-\u001F￾￿]/g;
  const clean = s => String(s == null ? '' : s).replace(BAD, m => (m.length === 2 ? m : ''));
  const XE = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&apos;' };
  const x = s => clean(s).replace(/[&<>"']/g, c => XE[c]);
  /* A KML <description> is HTML: a note is escaped as HTML first (so Google Earth shows it as typed) with each line break as
     <br>, then as XML. Import reads it back through plain(), which turns <br> into a line break again. */
  const HE = { '&': '&amp;', '<': '&lt;', '>': '&gt;' };
  const asHtml = s => clean(s).replace(/[&<>]/g, c => HE[c]).replace(/\r\n?|\n/g, '<br>');
  const c6 = v => String(+(+v).toFixed(6));     // 6 decimal places, no trailing zeros, never "-0"
  const a1 = v => String(+(+v).toFixed(1));
  const iso = t => (fin(t) && t > 0 && t < 8.64e15 ? new Date(t).toISOString() : '');
  const kindOf = k => (KIND_IDS.has(k) ? k : 'point');
  const labelOf = k => KINDS.find(o => o.id === kindOf(k)).label;
  const radii = s => (Array.isArray(s.r) ? s.r.filter(v => fin(v) && v > 0) : []);
  const trackName = track => `Field Kit track ${day(track[0] && track[0][3])}`;
  const lists = d => ({ markers: (d && d.markers) || [], shapes: (d && d.shapes) || [], track: (d && d.track) || [] });

  /* GPX 1.1, children in the schema's order: wpt, rte, trk; in a wpt ele, time, name, desc, sym, extensions; in a rte name,
     extensions, rtept. An area is a closed route; a ring is a route of one point (its centre) with its radii as extra data. */
  function toGPX(data) {
    const { markers, shapes, track } = lists(data);
    const out = ['<?xml version="1.0" encoding="UTF-8"?>',
      `<gpx version="1.1" creator="Field Kit" xmlns="http://www.topografix.com/GPX/1/1" xmlns:fk="${NS}">`];
    markers.forEach(m => {
      let s = `<wpt lat="${c6(m.lat)}" lon="${c6(m.lon)}">`;
      if (fin(m.alt)) s += `<ele>${a1(m.alt)}</ele>`;
      if (iso(m.t)) s += `<time>${iso(m.t)}</time>`;
      s += `<name>${x(m.name)}</name>`;
      if (m.note) s += `<desc>${x(m.note)}</desc>`;
      s += `<sym>${x(labelOf(m.kind))}</sym><extensions><fk:kind>${kindOf(m.kind)}</fk:kind></extensions></wpt>`;
      out.push(s);
    });
    shapes.forEach(sh => {
      const pts = sh.type === 'ring' ? sh.pts.slice(0, 1) : sh.type === 'area' ? sh.pts.concat([sh.pts[0]]) : sh.pts;
      const ext = sh.type === 'area' ? '<fk:type>area</fk:type>'
        : sh.type === 'ring' ? `<fk:type>ring</fk:type><fk:r>${radii(sh).join(' ')}</fk:r>` : '';
      out.push(`<rte><name>${x(sh.name)}</name>${ext ? `<extensions>${ext}</extensions>` : ''}` +
        pts.map(p => `<rtept lat="${c6(p[0])}" lon="${c6(p[1])}"/>`).join('') + '</rte>');
    });
    if (track.length) {
      out.push(`<trk><name>${x(trackName(track))}</name><trkseg>`);
      track.forEach(p => out.push(`<trkpt lat="${c6(p[0])}" lon="${c6(p[1])}">${fin(p[2]) ? `<ele>${a1(p[2])}</ele>` : ''}` +
        `${iso(p[3]) ? `<time>${iso(p[3])}</time>` : ''}</trkpt>`));
      out.push('</trkseg></trk>');
    }
    out.push('</gpx>', '');
    return out.join('\n');
  }

  /* KML 2.2: one Document, a Folder for each part that has something in it. A ring is drawn as one 72-point circle per radius
     (so other apps see circles) and carries its centre and radii, so Field Kit restores the ring itself. */
  function toKML(data) {
    const { markers, shapes, track } = lists(data);
    const ext = o => '<ExtendedData>' + Object.keys(o).map(k => `<Data name="${k}"><value>${x(o[k])}</value></Data>`).join('') + '</ExtendedData>';
    const co = (lat, lon, alt) => `${c6(lon)},${c6(lat)}` + (fin(alt) ? `,${a1(alt)}` : '');
    const line = pts => pts.map(p => co(p[0], p[1], p[2])).join(' ');
    const poly = pts => `<Polygon><tessellate>1</tessellate><outerBoundaryIs><LinearRing><coordinates>${line(pts)}</coordinates></LinearRing></outerBoundaryIs></Polygon>`;
    const pm = (name, inner) => `<Placemark><name>${x(name)}</name>${inner}</Placemark>`;
    const folder = (name, items) => (items.length ? `<Folder><name>${name}</name>\n${items.join('\n')}\n</Folder>` : '');
    const parts = [
      folder('Markers', markers.map(m => pm(m.name, (m.note ? `<description>${x(asHtml(m.note))}</description>` : '') +
        (iso(m.t) ? `<TimeStamp><when>${iso(m.t)}</when></TimeStamp>` : '') +
        ext({ 'fk:kind': kindOf(m.kind) }) +
        `<Point>${fin(m.alt) ? '<altitudeMode>absolute</altitudeMode>' : ''}<coordinates>${co(m.lat, m.lon, m.alt)}</coordinates></Point>`))),
      folder('Routes, areas and rings', shapes.map(sh => {
        if (sh.type === 'ring') {
          const c = sh.pts[0], r = radii(sh);
          return pm(sh.name, ext({ 'fk:type': 'ring', 'fk:r': r.join(' '), 'fk:center': `${c6(c[0])},${c6(c[1])}` }) +
            `<MultiGeometry>${r.map(m => poly(TGEOM.ring(c[0], c[1], m))).join('')}</MultiGeometry>`);
        }
        if (sh.type === 'area') return pm(sh.name, ext({ 'fk:type': 'area' }) + poly(sh.pts.concat([sh.pts[0]])));
        return pm(sh.name, ext({ 'fk:type': 'route' }) + `<LineString><tessellate>1</tessellate><coordinates>${line(sh.pts)}</coordinates></LineString>`);
      })),
      folder('Track', track.length ? [pm(trackName(track), `<LineString><tessellate>1</tessellate><coordinates>${line(track)}</coordinates></LineString>`)] : [])
    ].filter(Boolean);
    return ['<?xml version="1.0" encoding="UTF-8"?>', '<kml xmlns="http://www.opengis.net/kml/2.2">', '<Document><name>Field Kit</name>',
      ...parts, '</Document>', '</kml>', ''].join('\n');
  }

  /* ---------- Reading ----------
     Elements are matched by local name, so namespace prefixes and namespace URIs (GPX 1.0 or 1.1, KML 2.1 or 2.2, upper case,
     none at all) make no difference. Only textContent and attributes are read. */
  const all = (el, name) => el.getElementsByTagNameNS('*', name);
  const kid = (el, name) => { for (let c = el.firstElementChild; c; c = c.nextElementSibling) if (c.localName === name) return c; return null; };
  const kids = (el, name) => { const out = []; for (let c = el.firstElementChild; c; c = c.nextElementSibling) if (c.localName === name) out.push(c); return out; };
  const text = (el, name) => { const c = kid(el, name); return c ? c.textContent.trim() : ''; };
  const deep = (el, name) => { const c = el && all(el, name)[0]; return c ? c.textContent.trim() : ''; };
  const num = s => { const t = String(s == null ? '' : s).trim(); return t ? Number(t) : NaN; };
  const okLL = (lat, lon) => fin(lat) && fin(lon) && Math.abs(lat) <= 90 && Math.abs(lon) <= 180;
  /* More than MAX_PTS points: the first and the last kept, the rest spaced evenly by index. */
  const thin = pts => (pts.length <= MAX_PTS ? pts : Array.from({ length: MAX_PTS }, (_, i) => pts[Math.round(i * (pts.length - 1) / (MAX_PTS - 1))]));
  const radiiOf = s => String(s || '').trim().split(/\s+/).map(num).filter(v => fin(v) && v > 0 && v <= MAX_R).slice(0, 3);

  function addLine(out, name, pts) {
    if (pts.length < 2) { out.skipped++; return; }
    out.shapes.push({ type: 'route', name, pts: thin(pts) });
  }
  function addArea(out, name, pts) {
    const n = pts.length;
    if (n > 1 && pts[0][0] === pts[n - 1][0] && pts[0][1] === pts[n - 1][1]) pts = pts.slice(0, -1);   // the closing point
    if (pts.length < 3) { out.skipped++; return; }
    out.shapes.push({ type: 'area', name, pts: thin(pts) });
  }
  function addRing(out, name, centre, r) {
    const rs = radiiOf(r);
    if (!centre || !rs.length) { out.skipped++; return; }
    out.shapes.push({ type: 'ring', name, pts: [[centre[0], centre[1]]], r: rs });
  }

  /* GPX: points from lat/lon attributes; one that fails is dropped. */
  const gpxPts = els => { const out = []; els.forEach(e => { const lat = num(e.getAttribute('lat')), lon = num(e.getAttribute('lon')); if (okLL(lat, lon)) out.push([lat, lon]); }); return out; };
  function readGPX(root, out) {
    for (const w of all(root, 'wpt')) {
      const lat = num(w.getAttribute('lat')), lon = num(w.getAttribute('lon'));
      if (!okLL(lat, lon)) { out.skipped++; continue; }
      const fk = deep(kid(w, 'extensions'), 'kind'), ele = num(text(w, 'ele')), t = Date.parse(text(w, 'time'));
      out.markers.push({ name: text(w, 'name'), lat, lon, alt: fin(ele) ? ele : null,
        kind: KIND_IDS.has(fk) ? fk : LABEL_KIND.get(text(w, 'sym').toLowerCase()) || 'point',
        note: text(w, 'desc') || text(w, 'cmt'), t: fin(t) ? t : 0 });
    }
    for (const r of all(root, 'rte')) {
      const ext = kid(r, 'extensions'), type = deep(ext, 'type').toLowerCase(), name = text(r, 'name'), pts = gpxPts(kids(r, 'rtept'));
      if (type === 'ring') addRing(out, name, pts[0], deep(ext, 'r'));
      else if (type === 'area') addArea(out, name, pts);
      else addLine(out, name, pts);
    }
    for (const t of all(root, 'trk')) {   // one route per trk, its segments joined in order
      const pts = [];
      kids(t, 'trkseg').forEach(seg => gpxPts(kids(seg, 'trkpt')).forEach(p => pts.push(p)));
      addLine(out, text(t, 'name') || 'Track', pts);
    }
  }

  /* KML coordinates: lon,lat[,alt] tuples split by any whitespace. Whitespace next to a comma is joined first, so "lon, lat"
     reads; a tuple that then has other than two or three numbers is dropped, as is one off the globe. */
  function tuples(t) {
    const out = [], s = String(t || '').replace(/\s*,\s*/g, ',').trim();
    if (!s) return out;
    for (const tok of s.split(/\s+/)) {
      const v = tok.split(',');
      if (v.length < 2 || v.length > 3) continue;
      const lon = num(v[0]), lat = num(v[1]), alt = v.length === 3 ? num(v[2]) : NaN;
      if (okLL(lat, lon)) out.push([lat, lon, fin(alt) ? alt : null]);
    }
    return out;
  }
  const coords = el => tuples(deep(el, 'coordinates'));
  const ll = pts => pts.map(p => [p[0], p[1]]);
  /* A description is HTML: its text, read from an inert parsed document (never put in the page; nothing in it loads or runs).
     Inner spaces and line breaks are kept; leading and trailing whitespace is trimmed (as GPX notes are, by text()). */
  function plain(s) {
    if (!s) return '';
    if (!/[<&]/.test(s)) return s.trim();
    const d = new DOMParser().parseFromString(s, 'text/html');
    d.querySelectorAll('script,style,template').forEach(e => e.remove());
    d.querySelectorAll('br').forEach(e => e.replaceWith('\n'));
    return (d.body ? d.body.textContent : '').trim();
  }
  function extData(pm) {
    const o = Object.create(null), ed = kid(pm, 'ExtendedData');
    if (ed) kids(ed, 'Data').forEach(d => { const k = d.getAttribute('name'); if (k && !(k in o)) o[k] = text(d, 'value'); });
    return o;
  }
  const GEOMS = new Set(['Point', 'LineString', 'LinearRing', 'Polygon', 'MultiGeometry', 'Model', 'Track', 'MultiTrack']);
  const flat = (el, list) => { if (el.localName === 'MultiGeometry') { for (let c = el.firstElementChild; c; c = c.nextElementSibling) if (GEOMS.has(c.localName)) flat(c, list); } else list.push(el); return list; };
  const NOT_READ = ['GroundOverlay', 'ScreenOverlay', 'PhotoOverlay', 'NetworkLink', 'Tour'];

  /* What readKML will read: each part of a MultiGeometry is an item; a Placemark with no geometry still counts as one. Stops
     counting once past MAX_ITEMS. */
  function kmlItems(root) {
    let n = 0;
    for (const pm of all(root, 'Placemark')) {
      const geoms = [];
      for (let c = pm.firstElementChild; c; c = c.nextElementSibling) if (GEOMS.has(c.localName)) flat(c, geoms);
      n += Math.max(1, geoms.length);
      if (n > MAX_ITEMS) break;
    }
    return n;
  }
  function readKML(root, out) {
    NOT_READ.forEach(n => { out.skipped += all(root, n).length; });
    for (const pm of all(root, 'Placemark')) {
      const name = text(pm, 'name'), data = extData(pm);
      if ((data['fk:type'] || '').toLowerCase() === 'ring') {
        const c = String(data['fk:center'] || '').split(',').map(num);
        if (c.length === 2 && okLL(c[0], c[1]) && radiiOf(data['fk:r']).length) { addRing(out, name, c, data['fk:r']); continue; }
      }
      const geoms = [];
      for (let c = pm.firstElementChild; c; c = c.nextElementSibling) if (GEOMS.has(c.localName)) flat(c, geoms);
      if (!geoms.length) { out.skipped++; continue; }
      const multi = geoms.length > 1 || !kid(pm, geoms[0].localName);   // parts of a MultiGeometry: Name, Name 2, ...
      const note = plain(text(pm, 'description')), kind = KIND_IDS.has(data['fk:kind']) ? data['fk:kind'] : 'point';
      const when = Date.parse(deep(kid(pm, 'TimeStamp'), 'when')), t = fin(when) ? when : 0;
      geoms.forEach((g, i) => {
        const nm = multi && i && name ? `${name} ${i + 1}` : name, type = g.localName;
        if (type === 'Point') {
          const p = coords(g)[0];
          if (!p) { out.skipped++; return; }
          /* Under KML's default altitudeMode (clampToGround) the third number means nothing (Google Earth writes 0 on every
             point): an altitude is kept only when the Point says absolute, or the file is Field Kit's own (fk:kind). */
          const keepAlt = deep(g, 'altitudeMode') === 'absolute' || 'fk:kind' in data;
          out.markers.push({ name: nm, lat: p[0], lon: p[1], alt: keepAlt ? p[2] : null, kind, note, t });
        } else if (type === 'LineString') addLine(out, nm, ll(coords(g)));
        else if (type === 'Polygon') {
          const outer = kid(g, 'outerBoundaryIs');
          if (outer) addArea(out, nm, ll(coords(outer))); else out.skipped++;   // inner rings are not read
        } else out.skipped++;   // gx:Track, Model, a bare LinearRing
      });
    }
  }

  /* -> { ok: true, markers, shapes, skipped, cut } with plain records not yet stored, or { ok: false, reason }:
     'not-xml', 'kmz' (a zip), 'unknown' (XML but neither GPX nor KML), 'too-many' (over MAX_ITEMS items: wpt, rte and trk;
     KML Placemarks with each MultiGeometry part counted). The kind of file is
     told by its content, never its name. cut: more than MAX_MARKERS markers, only the first were kept. */
  function parse(input) {
    const fail = reason => ({ ok: false, reason });
    if (typeof input !== 'string') return fail('not-xml');
    const s = input.charCodeAt(0) === 0xFEFF ? input.slice(1) : input;
    if (s.startsWith('PK')) return fail('kmz');
    if (!s.trim()) return fail('not-xml');
    let doc;
    try { doc = new DOMParser().parseFromString(s, 'application/xml'); } catch (e) { return fail('not-xml'); }
    if (!doc || !doc.documentElement || all(doc, 'parsererror').length) return fail('not-xml');
    const root = doc.documentElement, kind = root.localName.toLowerCase();
    if (kind !== 'gpx' && kind !== 'kml') return fail('unknown');
    if ((kind === 'gpx' ? all(root, 'wpt').length + all(root, 'rte').length + all(root, 'trk').length : kmlItems(root)) > MAX_ITEMS) return fail('too-many');
    const out = { ok: true, markers: [], shapes: [], skipped: 0, cut: false };
    if (kind === 'gpx') readGPX(root, out); else readKML(root, out);
    if (out.markers.length > MAX_MARKERS) { out.markers = out.markers.slice(0, MAX_MARKERS); out.cut = true; }
    return out;
  }

  /* ---------- Duplicates ----------
     A marker equal to one already held (or earlier in the file) in kind and name, with coordinates the same to 5 places, is a
     duplicate; a shape equal in type, name, (a ring) radii, and every point the same to 5 places. "The same to 5 places" is
     read as less than 0.00001 degrees apart, not as equal after rounding: a file written to 6 places can move a point across a
     rounding edge (43.0012346 is 43.00123, but written as 43.001235 it rounds to 43.00124), and then a phone's own file would
     come back as new. Names compare as the data module stores them. */
  const nm = s => String(s == null ? '' : s).trim().slice(0, MAX_NAME);
  const TOL = 1e-5;
  const near = (a, b) => Math.abs(a[0] - b[0]) < TOL && Math.abs(a[1] - b[1]) < TOL;
  /* An item with no name in the file gets a default name when stored (WP 3, Route 2), so it is matched by place alone: the
     loose key leaves the name out. A named item must match the name too. */
  const mLoose = m => JSON.stringify([kindOf(m.kind)]);
  const sLoose = s => JSON.stringify([s.type, s.pts.length, s.type === 'ring' ? s.r : null]);
  const mSame = (a, b) => near([a.lat, a.lon], [b.lat, b.lon]);
  const sSame = (a, b) => a.pts.every((p, i) => near(p, b.pts[i]));
  /* -> { markers, shapes, duplicates, repeats, overLimit }: what would be added to existing ({ markers, shapes }), how many
     items were already held, how many repeat an earlier item of the file, and how many shapes would not fit under maxShapes. Items are grouped by everything but their coordinates, so each is compared with few others. */
  function plan(parsed, existing, maxShapes = MAX_SHAPES) {
    const have = existing || {}, oldS = have.shapes || [];
    let duplicates = 0, repeats = 0;   // already held before the import / an earlier item of the same file
    const sift = (list, held, loose, same) => {
      const groups = new Map(), out = [], old = new Set(held);
      const add = (k, o) => { if (!groups.has(k)) groups.set(k, []); groups.get(k).push(o); };
      const put = o => { const l = loose(o); add(l, o); add(l + nm(o.name), o); };
      const match = o => { const g = groups.get(loose(o) + nm(o.name)); return g ? g.find(h => same(o, h)) : null; };
      held.forEach(put);
      (list || []).forEach(o => {
        const h = match(o);
        if (h) { if (old.has(h)) duplicates++; else repeats++; return; }
        put(o); out.push(o);
      });
      return out;
    };
    const markers = sift(parsed && parsed.markers, have.markers || [], mLoose, mSame);
    const shapes = sift(parsed && parsed.shapes, oldS, sLoose, sSame);
    const room = Math.max(0, maxShapes - oldS.length);
    return { markers, shapes: shapes.slice(0, room), duplicates, repeats, overLimit: Math.max(0, shapes.length - room) };
  }

  /* "12 markers, 2 routes, 1 area, 1 ring" (zero kinds left out). */
  const counts = p => {
    const c = { markers: (p.markers || []).length, routes: 0, areas: 0, rings: 0 };
    (p.shapes || []).forEach(s => { c[s.type + 's']++; });
    return c;
  };
  const WORDS = [['markers', 'marker'], ['routes', 'route'], ['areas', 'area'], ['rings', 'ring']];
  const summary = c => WORDS.filter(([k]) => c[k] > 0).map(([k, one]) => `${c[k].toLocaleString('en-US')} ${c[k] === 1 ? one : k}`).join(', ');

  return { NS, KINDS, MAX_ITEMS, MAX_MARKERS, MAX_NAME, MAX_PTS, toGPX, toKML, parse, plan, counts, summary, day };
})();

/* ---------- The Export and Import sheets ---------- */
(() => {
  const FK = window.FK;
  const { $, $$, store, toast } = FK;
  const ATAK = 'Saved to Downloads. ATAK imports it from Import → Local SD.';
  const NOT_XML = "That file isn't a GPX or KML file.";
  const MSG = {
    'not-xml': NOT_XML, unknown: NOT_XML,
    kmz: "Zipped KML (.kmz) can't be read. Export plain KML instead.",
    'too-many': 'That file has too many items (over 5,000).'
  };
  const TOO_BIG = 'That file is too large (over 5 MB).';
  const NOTHING = 'Nothing to import: that file has no points, lines or areas.';
  const CAP = 'That file has more than 2,000 markers. The first 2,000 were read.';
  const MAX_BYTES = 5 * 1024 * 1024;
  const plural = (n, one, many) => `${n.toLocaleString('en-US')} ${n === 1 ? one : many}`;

  /* ---------- Export ---------- */
  const edlg = $('#dlgExport');
  const HINT = { GPX: 'Opens in ATAK, Gaia and most GPS apps.', KML: 'Opens in Google Earth and ATAK.' };
  let fmt = 'GPX';
  const PARTS = [
    { cb: '#exMarkers', lab: '#exMarkersL', n: () => FK.tac.markers().length, text: n => `Markers (${n || 'none'})` },
    { cb: '#exShapes', lab: '#exShapesL', n: () => FK.tac.shapes().length, text: n => `Routes, areas and rings (${n || 'none'})` },
    { cb: '#exTrack', lab: '#exTrackL', n: () => FK.map.track().length, text: n => `Recorded track (${n ? plural(n, 'point', 'points') : 'none'})` }
  ];
  function showFmt() {
    $$('#exFormat button').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.fmt.toUpperCase() === fmt)));
    $('#exFmtHint').textContent = HINT[fmt];
  }
  const syncSave = () => { $('#exSave').disabled = !PARTS.some(p => $(p.cb).checked); };
  /* Counts and states only: the controls themselves stay as they are (a part that empties is unticked; one that fills is ticked). */
  function counts(fresh) {
    PARTS.forEach(p => {
      const n = p.n(), cb = $(p.cb);
      $(p.lab).textContent = p.text(n);
      if (fresh || cb.disabled !== !n) cb.checked = !!n;
      cb.disabled = !n;
    });
    syncSave();
  }
  function openExport() {
    fmt = store.get('ioFormat', 'GPX') === 'KML' ? 'KML' : 'GPX';
    showFmt();
    counts(true);
    FK.sheet.open(edlg, { onOpen: () => $('#exTitle').focus() });
  }
  ['wps', 'shapes', 'track'].forEach(e => FK.on(e, () => { if (edlg.open) counts(false); }));
  $('#exFormat').addEventListener('click', e => {
    const b = e.target.closest('[data-fmt]');
    if (!b) return;
    fmt = b.dataset.fmt.toUpperCase();
    store.set('ioFormat', fmt);
    showFmt();
  });
  PARTS.forEach(p => $(p.cb).addEventListener('change', syncSave));
  $('#exCancel').addEventListener('click', () => FK.sheet.close(edlg));
  $('#exSave').addEventListener('click', () => {
    const data = { markers: $('#exMarkers').checked ? FK.tac.markers() : [], shapes: $('#exShapes').checked ? FK.tac.shapes() : [],
      track: $('#exTrack').checked ? FK.map.track() : [] };
    if (!data.markers.length && !data.shapes.length && !data.track.length) return;
    const kml = fmt === 'KML';
    FK.download(`fieldkit-${TIO.day()}.${kml ? 'kml' : 'gpx'}`, kml ? TIO.toKML(data) : TIO.toGPX(data),
      kml ? 'application/vnd.google-earth.kml+xml' : 'application/gpx+xml');
    FK.sheet.close(edlg);
    toast(ATAK);
  });

  /* ---------- Import ---------- */
  /* Stores what plan() says is new; -> { added: { markers, routes, areas, rings }, duplicates, repeats, overLimit, ok, points }.
     ok false: storage refused part of it (the items stay on screen this session; tac-data has shown the full-storage message).
     points: [lat, lon] covering what was added, for the map to show. */
  TIO.merge = parsed => {
    const pl = TIO.plan(parsed, { markers: FK.tac.markers(), shapes: FK.tac.shapes() }, FK.tac.MAX_SHAPES);
    const m = FK.tac.addMarkers(pl.markers), s = FK.tac.addShapes(pl.shapes);
    const points = m.added.map(w => [w.lat, w.lon]);
    s.added.forEach(sh => {
      if (sh.type === 'ring') TGEOM.ring(sh.pts[0][0], sh.pts[0][1], Math.max(...sh.r), 8).forEach(p => points.push(p));
      else sh.pts.forEach(p => points.push(p));
    });
    return { added: TIO.counts({ markers: m.added, shapes: s.added }), duplicates: pl.duplicates, repeats: pl.repeats, overLimit: pl.overLimit + s.over,
      ok: m.ok && s.ok, points };
  };

  /* The system file picker, made once. It is reset after each choice so the same file can be chosen again. */
  const input = Object.assign(document.createElement('input'), {
    type: 'file', id: 'ioFile', hidden: true,
    accept: '.gpx,.kml,application/gpx+xml,application/vnd.google-earth.kml+xml,text/xml,application/xml'
  });
  input.setAttribute('aria-hidden', 'true');
  document.body.appendChild(input);
  input.addEventListener('change', async () => {
    const file = input.files && input.files[0];
    input.value = '';
    if (!file) return;
    if (file.size > MAX_BYTES) { toast(TOO_BIG); return; }
    let text;
    try { text = await file.text(); } catch (e) { toast(NOT_XML); return; }
    const p = TIO.parse(text);
    if (!p.ok) { toast(MSG[p.reason] || NOT_XML); return; }
    if (!p.markers.length && !p.shapes.length) { toast(NOTHING); return; }
    showCount(file.name, p);
  });

  const idlg = $('#dlgImport');
  let pending = null;
  function showCount(name, p) {
    if (idlg.open) return;
    pending = p;
    $('#imFile').textContent = name;
    $('#imFound').textContent = TIO.summary(TIO.counts(p));
    const pl = TIO.plan(p, { markers: FK.tac.markers(), shapes: FK.tac.shapes() }, FK.tac.MAX_SHAPES);
    const notes = [];
    if (pl.duplicates) notes.push(`${pl.duplicates.toLocaleString('en-US')} already on this phone`);
    if (pl.repeats) notes.push(`${pl.repeats.toLocaleString('en-US')} repeated in the file`);
    if (p.skipped) notes.push(`${plural(p.skipped, 'item', 'items')} skipped: not a point, line or area`);
    if (pl.overLimit) notes.push(`${plural(pl.overLimit, 'shape', 'shapes')} won't be added: the app holds ${FK.tac.MAX_SHAPES} at most.`);
    if (p.cut) notes.push(CAP);
    $('#imNotes').replaceChildren(...notes.map(t => Object.assign(document.createElement('li'), { textContent: t })));
    const none = !pl.markers.length && !pl.shapes.length, add = $('#imAdd');
    add.disabled = none;
    add.textContent = none ? 'Nothing new to add' : 'Add to map';
    FK.sheet.open(idlg, { onClose: () => { pending = null; }, onOpen: () => $('#imTitle').focus() });
  }
  $('#imCancel').addEventListener('click', () => FK.sheet.close(idlg));
  $('#imAdd').addEventListener('click', () => {
    if (!pending) return;
    const res = TIO.merge(pending);
    pending = null;
    FK.sheet.close(idlg);
    FK.sheet.afterStep(() => {
      FK.map.fit(res.points);
      const s = TIO.summary(res.added);
      if (res.ok && s) toast(`Added ${s}.`);
    });
  });

  /* Icons: Import is a document with an arrow into it; Export an arrow up out of a tray (Save map for offline's arrow points
     down to a line). The picker opens straight from the tap on the Tools row (now: true): Safari opens a file picker only from a user's tap. */
  FK.mapTools.addRow({ id: 'import', label: 'Import', hint: 'Bring in markers and routes from a GPX or KML file', now: true, run: () => input.click(),
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><path d="M14 3v6h6"/><path d="M12 11v7"/><path d="m9 15 3 3 3-3"/></svg>' });
  FK.mapTools.addRow({ id: 'export', label: 'Export', hint: 'Save markers, routes and the track as a file', run: openExport,
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3v12"/><path d="m7 8 5-5 5 5"/><path d="M5 15v4a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-4"/></svg>' });

  FK.io = { openExport, openImport: () => input.click() };
})();
