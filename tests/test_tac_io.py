"""Import and export (GPX and KML): the pure TIO functions tested directly, then the Export sheet and the Import flow
through the screen. Fixture files under tests/fixtures/tac/ are written by hand with round coordinates near 43.0, -76.0."""
import json
import os
import re
import pytest
from playwright.sync_api import expect

from .tac import open_map
from .test_map_tools import boot, mk, shape, stored, ev, FULL

FIX = os.path.join(os.path.dirname(__file__), 'fixtures', 'tac')
NS = 'https://jordanmcnulty3-max.github.io/field-kit/ns/1'
ATAK = 'Saved to Downloads. ATAK imports it from Import → Local SD.'
NOT_XML = "That file isn't a GPX or KML file."
KMZ = "Zipped KML (.kmz) can't be read. Export plain KML instead."
TOO_BIG = 'That file is too large (over 5 MB).'
TOO_MANY = 'That file has too many items (over 5,000).'
NOTHING = 'Nothing to import: that file has no points, lines or areas.'
CAP = 'That file has more than 2,000 markers. The first 2,000 were read.'
KINDS = ['point', 'camp', 'vehicle', 'water', 'cache', 'hazard', 'rally', 'observe', 'medical', 'friend', 'hostile', 'neutral', 'unknown']


def fixture(name):
    with open(os.path.join(FIX, name), encoding='utf-8') as f:
        return f.read()


def parse(page, text):
    return ev(page, 't => TIO.parse(t)', text)


def no_error(page, xml):
    """The text parses as XML with no parsererror, and its root's local name."""
    return ev(page, """t => { const d = new DOMParser().parseFromString(t, 'application/xml');
      return d.getElementsByTagName('parsererror').length ? 'ERROR' : d.documentElement.localName; }""", xml)


def toast(page):
    return page.locator('#toast')


def r5(x):
    return round(x, 5)


def sample_markers():
    out = []
    for i, k in enumerate(KINDS):
        out.append(mk(f'm{i}', f'{k.title()} {i}', lat=43.0 + i * 0.001234567, lon=-76.0 - i * 0.00098765, kind=k, t=1_700_000_000_000 + i))
        out[-1]['note'] = f'Note for {k}: fish & chips <b>{i}</b>\nsecond line' if i % 2 == 0 else ''
        out[-1]['alt'] = None if i % 3 == 0 else 100.4 + i
    out[2]['alt'] = 0   # a true 0 m stays 0 m
    out[4]['note'] = '  two  spaces\n\nafter a blank line\r\nand CRLF  \n'   # inner whitespace kept; the ends trimmed on import
    out[0]['name'] = 'Spring & <Creek> "quoted" \'single\''
    return out


def sample_shapes():
    return [
        shape('s1', 'route', [[43.0, -76.0], [43.01, -76.01], [43.02, -76.005]], name='Ridge & <walk>'),
        shape('s2', 'area', [[43.03, -76.03], [43.03, -76.02], [43.04, -76.02], [43.04, -76.03]], name='Camp field'),
        shape('s3', 'ring', [[43.05, -76.05]], name='Overwatch', r=[100, 300]),
    ]


TRACK = [[43.0, -76.0, 100, 1_700_000_000_000], [43.001, -76.0, None, 1_700_000_060_000], [43.002, -76.0, 101.5, 1_700_000_120_000]]


# ---------- Pure functions ----------

def test_kind_table_and_name_limit_match_the_data_module(page, app_url):
    boot(page, app_url)
    assert ev(page, '() => JSON.stringify(TIO.KINDS) === JSON.stringify(FK.tac.KINDS.map(k => ({ id: k.id, label: k.label })))')
    assert ev(page, '() => [TIO.MAX_NAME, TIO.MAX_MARKERS > 0]') == [ev(page, 'FK.tac.MAX_NAME'), True]
    assert ev(page, 'FK.tac.MAX_NAME') == 60 and ev(page, 'TIO.MAX_PTS === FK.tac.MAX_PTS')


def test_gpx_parses_with_the_schema_order_and_field_kit_extras(page, app_url):
    boot(page, app_url)
    gpx = ev(page, 'd => TIO.toGPX(d)', {'markers': sample_markers(), 'shapes': sample_shapes(), 'track': TRACK})
    assert no_error(page, gpx) == 'gpx'
    info = ev(page, """t => { const d = new DOMParser().parseFromString(t, 'application/xml'), r = d.documentElement;
      const kids = e => [...e.children].map(c => c.localName);
      const wpts = [...r.children].filter(c => c.localName === 'wpt');
      const rtes = [...r.children].filter(c => c.localName === 'rte');
      return { version: r.getAttribute('version'), creator: r.getAttribute('creator'), ns: r.namespaceURI,
        fk: r.lookupNamespaceURI('fk'), top: kids(r), wpt0: kids(wpts[0]), wpt1: kids(wpts[1]),
        rtes: rtes.map(x => ({ kids: kids(x), n: x.getElementsByTagName('rtept').length,
          type: (x.getElementsByTagNameNS('%s', 'type')[0] || {}).textContent || null,
          r: (x.getElementsByTagNameNS('%s', 'r')[0] || {}).textContent || null,
          first: [...x.getElementsByTagName('rtept')].slice(0, 1).map(p => [p.getAttribute('lat'), p.getAttribute('lon')])[0],
          last: [...x.getElementsByTagName('rtept')].slice(-1).map(p => [p.getAttribute('lat'), p.getAttribute('lon')])[0] })),
        kind1: wpts[1].getElementsByTagNameNS('%s', 'kind')[0].textContent, sym1: wpts[1].getElementsByTagName('sym')[0].textContent,
        trk: kids(r.getElementsByTagName('trk')[0]), trkpts: r.getElementsByTagName('trkpt').length }; }""".replace('%s', NS), gpx)
    assert info['version'] == '1.1' and info['creator'] == 'Field Kit' and info['ns'] == 'http://www.topografix.com/GPX/1/1'
    assert info['fk'] == NS
    top = info['top']
    assert top == ['wpt'] * 13 + ['rte'] * 3 + ['trk'], top
    # marker 0: no altitude, a note; marker 1: altitude, no note
    assert info['wpt0'] == ['time', 'name', 'desc', 'sym', 'extensions']
    assert info['wpt1'] == ['ele', 'time', 'name', 'sym', 'extensions']
    assert info['kind1'] == 'camp' and info['sym1'] == 'Camp'
    route, area, ring = info['rtes']
    assert route['kids'] == ['name', 'rtept', 'rtept', 'rtept'] and route['type'] is None
    assert area['kids'][:2] == ['name', 'extensions'] and area['type'] == 'area' and area['n'] == 5 and area['first'] == area['last']
    assert ring['type'] == 'ring' and ring['r'] == '100 300' and ring['n'] == 1 and ring['first'] == ['43.05', '-76.05']
    assert info['trk'] == ['name', 'trkseg'] and info['trkpts'] == 3
    assert '<trkpt lat="43.001" lon="-76"><time>2023-11-14T22:14:20.000Z</time></trkpt>' in gpx
    assert '<ele>100</ele><time>2023-11-14T22:13:20.000Z</time>' in gpx
    assert '<name>Spring &amp; &lt;Creek&gt; &quot;quoted&quot; &apos;single&apos;</name>' in gpx
    assert '<name>Ridge &amp; &lt;walk&gt;</name>' in gpx


def test_kml_has_folders_extended_data_and_ring_circles(page, app_url):
    boot(page, app_url)
    kml = ev(page, 'd => TIO.toKML(d)', {'markers': sample_markers(), 'shapes': sample_shapes(), 'track': TRACK})
    assert no_error(page, kml) == 'kml'
    info = ev(page, """t => { const d = new DOMParser().parseFromString(t, 'application/xml'), r = d.documentElement;
      const doc = r.children[0], data = (pm, n) => { const x = [...pm.getElementsByTagName('Data')].find(e => e.getAttribute('name') === n);
        return x ? x.getElementsByTagName('value')[0].textContent : null; };
      const folders = [...doc.children].filter(c => c.localName === 'Folder');
      const pms = f => [...f.getElementsByTagName('Placemark')];
      const mk = pms(folders[0])[1], sh = pms(folders[1]), tr = pms(folders[2])[0];
      return { ns: r.namespaceURI, docKids: [...doc.children].map(c => c.localName),
        folders: folders.map(f => f.getElementsByTagName('name')[0].textContent), nMk: pms(folders[0]).length,
        mkKids: [...mk.children].map(c => c.localName), mkKind: data(mk, 'fk:kind'),
        mkPt: [...mk.getElementsByTagName('Point')[0].children].map(c => [c.localName, c.textContent]),
        mk0Pt: [...pms(folders[0])[0].getElementsByTagName('Point')[0].children].map(c => c.localName),
        mkCoord: mk.getElementsByTagName('coordinates')[0].textContent, mk0Coord: pms(folders[0])[0].getElementsByTagName('coordinates')[0].textContent,
        route: [sh[0].getElementsByTagName('LineString').length, data(sh[0], 'fk:type')],
        area: [sh[1].getElementsByTagName('Polygon').length, data(sh[1], 'fk:type'), sh[1].getElementsByTagName('coordinates')[0].textContent.trim().split(/\\s+/)],
        ring: [sh[2].getElementsByTagName('MultiGeometry').length, sh[2].getElementsByTagName('Polygon').length, data(sh[2], 'fk:type'), data(sh[2], 'fk:r'), data(sh[2], 'fk:center'),
               [...sh[2].getElementsByTagName('coordinates')].map(c => c.textContent.trim().split(/\\s+/).length)],
        track: [tr.getElementsByTagName('name')[0].textContent, tr.getElementsByTagName('coordinates')[0].textContent.trim().split(/\\s+/)] }; }""", kml)
    assert info['ns'] == 'http://www.opengis.net/kml/2.2'
    assert info['folders'] == ['Markers', 'Routes, areas and rings', 'Track']
    assert info['nMk'] == 13
    assert info['mkKids'] == ['name', 'TimeStamp', 'ExtendedData', 'Point'] and info['mkKind'] == 'camp'
    assert info['mkCoord'] == '-76.000988,43.001235,101.4'   # 6 places, altitude when known
    assert info['mkPt'][0] == ['altitudeMode', 'absolute']  # a GPS altitude is above sea level, not ground
    assert info['mk0Coord'] == '-76,43' and info['mk0Pt'] == ['coordinates']   # no altitude: none written
    assert info['route'] == [1, 'route'] or info['route'] == [1, None]
    assert info['area'][0] == 1 and info['area'][1] == 'area' and info['area'][2][0] == info['area'][2][-1] and len(info['area'][2]) == 5
    assert info['ring'][:5] == [1, 2, 'ring', '100 300', '43.05,-76.05'] and info['ring'][5] == [73, 73]
    assert re.fullmatch(r'Field Kit track \d{4}-\d{2}-\d{2}', info['track'][0])
    assert info['track'][1] == ['-76,43,100', '-76,43.001', '-76,43.002,101.5']
    assert '<name>Spring &amp; &lt;Creek&gt; &quot;quoted&quot; &apos;single&apos;</name>' in kml


def test_folders_without_content_are_left_out(page, app_url):
    boot(page, app_url)
    kml = ev(page, 'd => TIO.toKML(d)', {'markers': [], 'shapes': sample_shapes()[:1], 'track': []})
    assert '<name>Routes, areas and rings</name>' in kml and '<name>Markers</name>' not in kml and '<name>Track</name>' not in kml
    gpx = ev(page, 'd => TIO.toGPX(d)', {'markers': sample_markers()[:1], 'shapes': [], 'track': []})
    assert '<rte>' not in gpx and '<trk>' not in gpx and gpx.count('<wpt ') == 1


def test_characters_xml_forbids_are_stripped(page, app_url):
    boot(page, app_url)
    for fn in ('toGPX', 'toKML'):
        r = ev(page, """fn => { const c = String.fromCharCode;
          const m = { id: 'm1', name: 'A' + c(0) + 'B' + c(11) + 'C' + c(7) + 'D' + c(0xd800) + 'E' + String.fromCodePoint(0x1F600) + 'F' + c(9) + 'G', lat: 43, lon: -76,
            alt: null, t: 1, kind: 'point', note: 'x' + c(31) + 'y' + c(0xdc00) + 'z' + c(0xfffe) };
          const s = { id: 's1', type: 'route', name: 'R' + c(1) + c(12), pts: [[43, -76], [43.01, -76.01]] };
          const out = TIO[fn]({ markers: [m], shapes: [s], track: [] });
          const d = new DOMParser().parseFromString(out, 'application/xml');
          return { err: d.getElementsByTagName('parsererror').length, back: TIO.parse(out) }; }""", fn)
        assert r['err'] == 0, fn
        back = r['back']
        assert back['ok'] and back['markers'][0]['name'] == 'ABCDE\U0001F600F\tG', back
        assert back['markers'][0]['note'] == 'xyz'
        assert back['shapes'][0]['name'] == 'R'


def round_trip(page, fmt):
    markers, shapes = sample_markers(), sample_shapes()
    out = ev(page, f'd => TIO.{fmt}(d)', {'markers': markers, 'shapes': shapes, 'track': TRACK})
    back = parse(page, out)
    assert back['ok'] and back['skipped'] == 0, back
    assert len(back['markers']) == len(markers)
    for a, b in zip(markers, back['markers']):
        # Stated behaviour: a note keeps its inner spaces and line breaks (CRLF read as LF); leading and trailing whitespace is trimmed.
        assert b['kind'] == a['kind'] and b['name'] == a['name'] and b['note'] == a['note'].replace('\r\n', '\n').strip(), (a, b)
        assert abs(b['lat'] - a['lat']) <= 5e-7 and abs(b['lon'] - a['lon']) <= 5e-7   # written to 6 places
        assert (b['alt'] is None) if a['alt'] is None else round(b['alt']) == round(a['alt'])
        assert round(b['t'] / 1000) == round(a['t'] / 1000), (a, b)   # the marker's time, to the second
    got = back['shapes']
    assert [s['type'] for s in got] == ['route', 'area', 'ring', 'route']
    for a, b in zip(shapes, got):
        assert b['name'] == a['name'] and len(b['pts']) == len(a['pts']), (a, b)
        assert all(abs(p[0] - q[0]) <= 5e-7 and abs(p[1] - q[1]) <= 5e-7 for p, q in zip(a['pts'], b['pts'])), (a, b)
        assert b.get('r') == a.get('r')
    assert re.fullmatch(r'Field Kit track \d{4}-\d{2}-\d{2}', got[3]['name']) and got[3]['pts'] == [[p[0], p[1]] for p in TRACK]
    return out


def test_round_trip_gpx(page, app_url):
    boot(page, app_url)
    round_trip(page, 'toGPX')


def test_round_trip_kml(page, app_url):
    boot(page, app_url)
    out = round_trip(page, 'toKML')
    # a line break in a note is a <br> in the description's HTML, so Google Earth shows it
    desc = ev(page, """t => [...new DOMParser().parseFromString(t, 'application/xml').getElementsByTagName('description')].map(d => d.textContent)""", out)
    assert desc[0] == 'Note for point: fish &amp; chips &lt;b&gt;0&lt;/b&gt;<br>second line'
    assert all('\n' not in d and '\r' not in d for d in desc)


def test_refusals(page, app_url):
    boot(page, app_url)
    assert parse(page, '') == {'ok': False, 'reason': 'not-xml'}
    assert parse(page, '   \n') == {'ok': False, 'reason': 'not-xml'}
    assert parse(page, 'hello, world') == {'ok': False, 'reason': 'not-xml'}
    assert parse(page, '<gpx><wpt lat="1" lon="2"></gpx>') == {'ok': False, 'reason': 'not-xml'}
    assert parse(page, 'PK\u0003\u0004doc.kml') == {'ok': False, 'reason': 'kmz'}
    assert parse(page, '<html><body/></html>') == {'ok': False, 'reason': 'unknown'}
    assert parse(page, '<?xml version="1.0"?><rss/>') == {'ok': False, 'reason': 'unknown'}
    # a byte order mark and CRLF line ends are fine
    ok = parse(page, '﻿<?xml version="1.0" encoding="UTF-8"?>\r\n<gpx version="1.1" xmlns="http://www.topografix.com/GPX/1/1">\r\n<wpt lat="43" lon="-76"><name>A</name></wpt>\r\n</gpx>\r\n')
    assert ok['ok'] and ok['markers'][0]['name'] == 'A'


def test_google_earth_kml(page, app_url):
    boot(page, app_url)
    p = parse(page, fixture('google-earth.kml'))
    assert p['ok']
    ms = [(m['name'], m['lat'], m['lon'], m['kind'], m['alt']) for m in p['markers']]
    # Google Earth's ",0" under the default clampToGround is not an altitude: unknown
    assert ms == [('Trailhead', 43.0, -76.0, 'point', None), ('Lookouts', 43.04, -76.05, 'point', None), ('Lookouts 2', 43.04, -76.06, 'point', None)]
    assert p['markers'][0]['note'] == 'Park here & walk north.\nGate shuts at 9.'
    sh = [(s['type'], s['name'], s['pts']) for s in p['shapes']]
    assert sh[0] == ('route', 'Ridge walk', [[43.0, -76.0], [43.01, -76.01], [43.015, -76.02], [43.02, -76.03]])   # nested Folder
    assert sh[1] == ('area', 'Camp field', [[43.02, -76.04], [43.02, -76.03], [43.03, -76.03], [43.03, -76.04]])   # outer ring, open
    assert sh[2] == ('route', 'Lookouts 3', [[43.04, -76.05], [43.04, -76.06]])                                    # MultiGeometry part
    assert len(sh) == 3
    assert p['skipped'] == 3   # gx:Track, Model, GroundOverlay (the inner ring is not counted)


def test_kml_altitude_only_when_absolute_or_field_kit(page, app_url):
    boot(page, app_url)
    def alt(point, ext=''):
        return parse(page, f'<kml xmlns:gx="http://www.google.com/kml/ext/2.2"><Placemark><name>P</name>{ext}{point}</Placemark></kml>')['markers'][0]['alt']
    assert alt('<Point><altitudeMode>absolute</altitudeMode><coordinates>-76,43,123.4</coordinates></Point>') == 123.4
    assert alt('<Point><gx:altitudeMode>absolute</gx:altitudeMode><coordinates>-76,43,7</coordinates></Point>') == 7
    assert alt('<Point><coordinates>-76,43,123.4</coordinates></Point>') is None
    assert alt('<Point><altitudeMode>clampToGround</altitudeMode><coordinates>-76,43,123.4</coordinates></Point>') is None
    assert alt('<Point><altitudeMode>relativeToGround</altitudeMode><coordinates>-76,43,30</coordinates></Point>') is None
    fk = '<ExtendedData><Data name="fk:kind"><value>camp</value></Data></ExtendedData>'
    assert alt('<Point><coordinates>-76,43,55</coordinates></Point>', fk) == 55   # Field Kit's own (older) file


def test_google_earth_markers_export_without_elevation(page, app_url):
    boot(page, app_url)
    import_sheet(page, 'ge.kml', fixture('google-earth.kml'))
    page.click('#imAdd')
    page.wait_for_function('!document.querySelector("#dlgImport").open')
    assert [w['alt'] for w in stored(page, 'wps')] == [None, None, None]
    gpx = ev(page, '() => TIO.toGPX({ markers: FK.tac.markers(), shapes: [], track: [] })')
    assert gpx.count('<wpt ') == 3 and '<ele>' not in gpx


def test_garmin_gpx(page, app_url):
    boot(page, app_url)
    p = parse(page, fixture('garmin.gpx'))
    assert p['ok']
    ms = [(m['name'], m['lat'], m['lon'], m['kind'], m['note'], m['alt']) for m in p['markers']]
    assert ms == [('001', 43.0, -76.0, 'point', 'Parking', 120.37), ('SPRING', 43.01, -76.01, 'water', 'Flows in spring only', 131),
                  ('Bad point', 43.02, -76.02, 'point', '', None)]
    sh = [(s['type'], s['name'], len(s['pts'])) for s in p['shapes']]
    assert sh == [('route', 'To the lake', 3), ('route', 'ACTIVE LOG 03 OCT 2026', 4), ('route', 'Track', 2)]
    assert p['shapes'][1]['pts'] == [[43.0, -76.0], [43.001, -76.0], [43.002, -76.0], [43.003, -76.001]]   # segments joined
    assert p['skipped'] == 1   # the point off the globe


def test_other_namespaces_and_versions(page, app_url):
    boot(page, app_url)
    g10 = parse(page, '<?xml version="1.0"?><gpx version="1.0" creator="x" xmlns="http://www.topografix.com/GPX/1/0">'
                      '<wpt lat="43.01" lon="-76.1"><name>Ten</name><desc>d</desc></wpt>'
                      '<rte><rtept lat="43" lon="-76"/><rtept lat="43.01" lon="-76"/></rte></gpx>')
    assert g10['ok'] and g10['markers'][0]['name'] == 'Ten' and g10['shapes'][0]['type'] == 'route' and g10['shapes'][0]['name'] == ''
    for ns in ('', ' xmlns="http://earth.google.com/kml/2.1"', ' xmlns="http://www.opengis.net/kml/2.2"', ' xmlns="HTTP://WWW.OPENGIS.NET/KML/2.2"'):
        k = parse(page, f'<kml{ns}><Document><Folder><Placemark><name>P</name><Point><coordinates>-76,43</coordinates></Point></Placemark></Folder></Document></kml>')
        assert k['ok'] and k['markers'][0]['name'] == 'P' and k['markers'][0]['alt'] is None, ns
    # a prefixed root
    k = parse(page, '<kml:kml xmlns:kml="http://www.opengis.net/kml/2.2"><kml:Placemark><kml:Point><kml:coordinates>-76,43</kml:coordinates></kml:Point></kml:Placemark></kml:kml>')
    assert k['ok'] and len(k['markers']) == 1


def kml_line(coords):
    return f'<kml><Placemark><name>L</name><LineString><coordinates>{coords}</coordinates></LineString></Placemark></kml>'


def test_coordinate_text_forms(page, app_url):
    """Accepted: lon,lat[,alt] tuples split by any whitespace (spaces, tabs, CR, LF); spaces next to the commas inside a
    tuple are joined first. A tuple without exactly two or three numbers is dropped, as is one off the globe."""
    boot(page, app_url)
    pts = lambda t: parse(page, kml_line(t))['shapes'][0]['pts']
    assert pts('-76,43 -76.1,43.01') == [[43, -76], [43.01, -76.1]]
    assert pts('\r\n\t-76,43,0\r\n\t-76.1,43.01,12\r\n') == [[43, -76], [43.01, -76.1]]
    assert pts('-76, 43, 0   -76.1 ,43.01') == [[43, -76], [43.01, -76.1]]
    assert pts('-76,43 bad,43 -76,43,1,2 -76.02,95 -190,43 -76.1,43.01 1e1,4e1') == [[43, -76], [43.01, -76.1], [40, 10]]
    one = parse(page, kml_line('-76,43 -76.02,95'))
    assert one['ok'] and one['shapes'] == [] and one['skipped'] == 1   # a route left with one point
    area = parse(page, '<kml><Placemark><Polygon><outerBoundaryIs><LinearRing><coordinates>-76,43 -76.1,43 -76,43</coordinates></LinearRing></outerBoundaryIs></Polygon></Placemark></kml>')
    assert area['shapes'] == [] and area['skipped'] == 1


def test_long_lines_are_thinned_to_200(page, app_url):
    boot(page, app_url)
    coords = ' '.join(f'{-76 - i * 0.0001:.4f},{43 + i * 0.0001:.4f}' for i in range(450))
    p = parse(page, kml_line(coords))
    s = p['shapes'][0]['pts']
    assert len(s) == 200 and s[0] == [43, -76] and s[-1] == [round(43 + 449 * 0.0001, 4), round(-76 - 449 * 0.0001, 4)]
    idx = [round((x[0] - 43) / 0.0001) for x in s]
    assert idx == [round(i * 449 / 199) for i in range(200)]


def big_track_gpx(n=50_000):
    pts = ''.join(f'<trkpt lat="{43 + i * 1e-6:.6f}" lon="{-76 - i * 1e-6:.6f}"><ele>{100 + i % 50}.0</ele><time>2026-10-03T14:00:00Z</time></trkpt>\n'
                  for i in range(n))
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<gpx version="1.1" creator="t" xmlns="http://www.topografix.com/GPX/1/1"><trk><name>Long</name><trkseg>\n{pts}</trkseg></trk></gpx>\n'


def test_a_50000_point_track_becomes_one_route_quickly(page, app_url):
    boot(page, app_url)
    text = big_track_gpx()
    assert 4_000_000 < len(text.encode()) <= 5 * 1024 * 1024
    t = ev(page, """t => { const a = performance.now(), p = TIO.parse(t); return { ms: performance.now() - a, n: p.shapes.length,
      pts: p.shapes[0].pts.length, first: p.shapes[0].pts[0], last: p.shapes[0].pts[p.shapes[0].pts.length - 1], name: p.shapes[0].name }; }""", text)
    assert t['ms'] < 5000, t
    assert t['n'] == 1 and t['pts'] == 200 and t['name'] == 'Long'
    assert t['first'] == [43.0, -76.0] and t['last'] == [round(43 + 49_999e-6, 6), round(-76 - 49_999e-6, 6)]


def test_too_many_items(page, app_url):
    boot(page, app_url)
    wpts = ''.join('<wpt lat="43" lon="-76"/>' for _ in range(4999))
    assert parse(page, f'<gpx>{wpts}<rte/><trk/></gpx>') == {'ok': False, 'reason': 'too-many'}
    ok = parse(page, f'<gpx>{wpts}<rte/></gpx>')
    assert ok['ok'] and len(ok['markers']) == 2000 and ok['cut'] is True


def test_items_are_counted_after_multigeometry_is_opened(page, app_url):
    boot(page, app_url)
    lines = '<LineString><coordinates>0,0 1,1</coordinates></LineString>' * 60_000
    text = f'<kml><Placemark><name>Many</name><MultiGeometry>{lines}</MultiGeometry></Placemark></kml>'
    assert parse(page, text) == {'ok': False, 'reason': 'too-many'}
    ok = parse(page, f'<kml><Placemark><MultiGeometry>{"<Point><coordinates>0,0</coordinates></Point>" * 4999}</MultiGeometry></Placemark>'
                     '<Placemark><Point><coordinates>1,1</coordinates></Point></Placemark></kml>')
    assert ok['ok'] and len(ok['markers']) == 2000 and ok['cut']
    run_import(page, 'many.kml', text)
    expect(toast(page)).to_have_text(TOO_MANY)
    assert page.locator('#dlgImport[open]').count() == 0


def test_ring_radii_are_checked(page, app_url):
    boot(page, app_url)
    def ring(r):
        return parse(page, f'<gpx xmlns:fk="{NS}"><rte><name>R</name><extensions><fk:type>ring</fk:type><fk:r>{r}</fk:r></extensions>'
                           '<rtept lat="43" lon="-76"/><rtept lat="44" lon="-76"/></rte></gpx>')
    p = ring('0 -5 abc Infinity 60000 100 200 300 400')
    assert p['shapes'] == [{'type': 'ring', 'name': 'R', 'pts': [[43, -76]], 'r': [100, 200, 300]}]
    assert ring('50000')['shapes'][0]['r'] == [50000]
    bad = ring('0 abc')
    assert bad['shapes'] == [] and bad['skipped'] == 1
    k = parse(page, '<kml><Placemark><name>K</name><ExtendedData><Data name="fk:type"><value>ring</value></Data>'
                    '<Data name="fk:r"><value>250</value></Data><Data name="fk:center"><value>43.5,-76.5</value></Data></ExtendedData>'
                    '<Point><coordinates>0,0</coordinates></Point></Placemark></kml>')
    assert k['shapes'] == [{'type': 'ring', 'name': 'K', 'pts': [[43.5, -76.5]], 'r': [250]}] and k['markers'] == []


def test_entity_tricks_do_not_hang_or_fetch(page, app_url):
    boot(page, app_url)
    seen = []
    page.on('request', lambda r: seen.append(r.url))
    laughs = ('<?xml version="1.0"?><!DOCTYPE gpx [<!ENTITY a "lollollollollollollollollollol">'
              + ''.join(f'<!ENTITY {chr(98 + i)} "{("&" + chr(97 + i) + ";") * 10}">' for i in range(9))
              + ']><gpx><wpt lat="43" lon="-76"><name>&j;</name></wpt></gpx>')
    ext = ('<?xml version="1.0"?><!DOCTYPE kml [<!ENTITY x SYSTEM "http://fk-test-entity.invalid/secret">]>'
           '<kml><Placemark><name>&x;</name><Point><coordinates>-76,43</coordinates></Point></Placemark></kml>')
    dtd = ('<?xml version="1.0"?><!DOCTYPE gpx SYSTEM "http://fk-test-dtd.invalid/gpx.dtd">'
           '<gpx><wpt lat="43" lon="-76"><name>D</name></wpt></gpx>')
    for text in (laughs, ext, dtd):
        r = ev(page, """t => { const a = performance.now(), p = TIO.parse(t);
          return { ms: performance.now() - a, ok: p.ok, len: p.ok ? JSON.stringify(p).length : 0 }; }""", text)
        assert r['ms'] < 3000 and r['len'] < 100_000, r
    page.wait_for_timeout(200)
    assert not [u for u in seen if 'fk-test' in u], seen


def test_plan_finds_duplicates_and_the_shape_limit(page, app_url):
    boot(page, app_url)
    existing = {'markers': [mk('a', 'Camp', 43.000001, -76.0, 'camp')], 'shapes': [shape('x', 'route', [[43, -76], [43.01, -76]], name='R')]}
    parsed = {'ok': True, 'skipped': 0, 'markers': [
        {'name': 'Camp', 'lat': 43.0, 'lon': -76.000004, 'kind': 'camp', 'note': 'n', 'alt': None},   # same to 5 places
        {'name': 'Camp', 'lat': 43.0, 'lon': -76.0, 'kind': 'water', 'note': '', 'alt': None},       # other kind
        {'name': 'Camp ', 'lat': 43.0, 'lon': -76.0, 'kind': 'water', 'note': '', 'alt': None}],     # repeat in the file (trimmed)
        'shapes': [{'type': 'route', 'name': 'R', 'pts': [[43.000001, -76], [43.01, -76]]},
                   {'type': 'area', 'name': 'R', 'pts': [[43, -76], [43.01, -76], [43.01, -76.1]]},
                   {'type': 'ring', 'name': 'G', 'pts': [[43, -76]], 'r': [100]},
                   {'type': 'ring', 'name': 'G', 'pts': [[43, -76]], 'r': [100, 200]}]}
    p = ev(page, '([p, e]) => TIO.plan(p, e, 3)', [parsed, existing])
    assert [m['kind'] for m in p['markers']] == ['water']
    assert [(s['type'], s.get('r')) for s in p['shapes']] == [('area', None), ('ring', [100])]
    assert p['duplicates'] == 2 and p['repeats'] == 1 and p['overLimit'] == 1


def test_a_point_on_a_rounding_edge_is_still_a_duplicate(page, app_url):
    """43.0012346 rounds to 43.00123 but, written to 6 places as 43.001235, to 43.00124: still the same marker."""
    boot(page, app_url)
    existing = {'markers': [mk('a', 'Edge', 43.0012346, -76.0012346)], 'shapes': []}
    out = ev(page, 'd => TIO.toGPX(d)', {'markers': existing['markers'], 'shapes': [], 'track': []})
    back = parse(page, out)
    assert back['markers'][0]['lat'] == 43.001235
    p = ev(page, '([p, e]) => TIO.plan(p, e)', [back, existing])
    assert p['markers'] == [] and p['duplicates'] == 1
    far = dict(back['markers'][0], lat=43.00125)
    assert len(ev(page, '([p, e]) => TIO.plan(p, e)', [{'markers': [far], 'shapes': []}, existing])['markers']) == 1


def test_an_unnamed_item_matches_a_held_one_by_place(page, app_url):
    boot(page, app_url)
    existing = {'markers': [mk('a', 'WP 1', 43.0, -76.0, 'point')], 'shapes': [shape('x', 'route', [[43, -76], [43.01, -76]], name='Route 1')]}
    parsed = {'markers': [{'name': '', 'lat': 43.0, 'lon': -76.0, 'kind': 'point', 'note': '', 'alt': None},
                          {'name': '', 'lat': 43.0, 'lon': -76.0, 'kind': 'camp', 'note': '', 'alt': None},     # another kind: new
                          {'name': 'Named', 'lat': 43.0, 'lon': -76.0, 'kind': 'point', 'note': '', 'alt': None}],  # a name: exact rule
              'shapes': [{'type': 'route', 'name': '', 'pts': [[43, -76], [43.01, -76]]},
                         {'type': 'area', 'name': '', 'pts': [[43, -76], [43.01, -76], [43.01, -76.1]]}]}
    p = ev(page, '([p, e]) => TIO.plan(p, e)', [parsed, existing])
    assert [(m['kind'], m['name']) for m in p['markers']] == [('camp', ''), ('point', 'Named')]
    assert [s['type'] for s in p['shapes']] == ['area'] and p['duplicates'] == 2


# ---------- Through the screen ----------

def run_import(page, name, data):
    """Choose a file through Tools → Import as a person does (the system file picker)."""
    page.click('#mTools')
    with page.expect_file_chooser() as fc:
        page.click('#dlgTools [data-tool="import"]')
    fc.value.set_files({'name': name, 'mimeType': 'application/octet-stream', 'buffer': data if isinstance(data, bytes) else data.encode('utf-8')})


def import_sheet(page, name, data):
    run_import(page, name, data)
    page.wait_for_selector('#dlgImport[open]')


def counts_kml(markers=12, routes=2, areas=1, skipped=3):
    pm = ''.join(f'<Placemark><name>M{i}</name><Point><coordinates>{-76 - i * 0.001},{43 + i * 0.001}</coordinates></Point></Placemark>' for i in range(markers))
    pm += ''.join(f'<Placemark><name>R{i}</name><LineString><coordinates>-76,43 {-76.01 - i * 0.001},43.01</coordinates></LineString></Placemark>' for i in range(routes))
    pm += ''.join(f'<Placemark><name>A{i}</name><Polygon><outerBoundaryIs><LinearRing><coordinates>-76.02,43.02 -76.03,43.02 -76.03,{43.03 + i * 0.001} -76.02,43.02</coordinates></LinearRing></outerBoundaryIs></Polygon></Placemark>' for i in range(areas))
    pm += ''.join('<GroundOverlay><name>G</name></GroundOverlay>' for _ in range(skipped))
    return f'<?xml version="1.0" encoding="UTF-8"?><kml xmlns="http://www.opengis.net/kml/2.2"><Document><Folder>{pm}</Folder></Document></kml>'


def test_tools_sheet_has_import_and_export_after_save(page, app_url):
    boot(page, app_url)
    page.click('#mTools')
    rows = page.locator('#tlList [data-tool]')
    ids = [rows.nth(i).get_attribute('data-tool') for i in range(rows.count())]
    i = ids.index('save')
    assert ids[i + 1:i + 3] == ['import', 'export']
    imp = page.locator('#tlList [data-tool="import"]')
    expect(imp).to_contain_text('Import')
    expect(imp).to_contain_text('Bring in markers and routes from a GPX or KML file')
    expect(page.locator('#tlList [data-tool="export"]')).to_contain_text('Save markers, routes and the track as a file')


def test_old_export_buttons_are_gone(page, app_url):
    boot(page, app_url, markers=[mk('w1', 'Camp')])
    assert page.locator('#wpExport, #trkExport').count() == 0


def open_export_tools(page):
    page.click('#mTools')
    page.click('#dlgTools [data-tool="export"]')
    page.wait_for_selector('#dlgExport[open]')


def test_export_sheet_choices(page, app_url):
    boot(page, app_url, markers=[mk('w1', 'Camp'), mk('w2', 'Car', kind='vehicle')], shapes=[sample_shapes()[0]])
    open_export_tools(page)
    expect(page.locator('#exMarkersL')).to_have_text('Markers (2)')
    expect(page.locator('#exShapesL')).to_have_text('Routes, areas and rings (1)')
    expect(page.locator('#exTrackL')).to_have_text('Recorded track (none)')
    expect(page.locator('#exMarkers')).to_be_checked()
    expect(page.locator('#exShapes')).to_be_checked()
    expect(page.locator('#exTrack')).to_be_disabled()
    expect(page.locator('#exTrack')).not_to_be_checked()
    expect(page.locator('#exFormat [data-fmt="gpx"]')).to_have_attribute('aria-pressed', 'true')
    page.uncheck('#exMarkers')
    page.uncheck('#exShapes')
    expect(page.locator('#exSave')).to_be_disabled()
    page.check('#exShapes')
    expect(page.locator('#exSave')).to_be_enabled()
    page.click('#exFormat [data-fmt="kml"]')
    expect(page.locator('#exFormat [data-fmt="kml"]')).to_have_attribute('aria-pressed', 'true')
    assert stored(page, 'ioFormat') == 'KML'
    page.click('#exCancel')
    page.wait_for_function('!document.querySelector("#dlgExport").open')
    open_export_tools(page)
    expect(page.locator('#exFormat [data-fmt="kml"]')).to_have_attribute('aria-pressed', 'true')
    expect(page.locator('#exMarkers')).to_be_checked()   # every part ticked again on each opening


def test_export_with_nothing_saved(page, app_url):
    boot(page, app_url)
    open_export_tools(page)
    for cb in ('#exMarkers', '#exShapes', '#exTrack'):
        expect(page.locator(cb)).to_be_disabled()
    expect(page.locator('#exMarkersL')).to_have_text('Markers (none)')
    expect(page.locator('#exSave')).to_be_disabled()


def local_day(page):
    return ev(page, "() => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`; }")


def test_export_gpx_leaves_unticked_parts_out(page, app_url):
    boot(page, app_url, markers=sample_markers()[:3], shapes=sample_shapes(), track=TRACK)
    open_export_tools(page)
    expect(page.locator('#exTrackL')).to_have_text('Recorded track (3 points)')
    page.uncheck('#exShapes')
    with page.expect_download() as dl:
        page.click('#exSave')
    assert dl.value.suggested_filename == f'fieldkit-{local_day(page)}.gpx'
    gpx = open(dl.value.path(), encoding='utf-8').read()
    assert no_error(page, gpx) == 'gpx'
    assert gpx.count('<wpt ') == 3 and '<rte>' not in gpx and gpx.count('<trkpt ') == 3
    expect(toast(page)).to_have_text(ATAK)
    page.wait_for_function('!document.querySelector("#dlgExport").open')


def test_export_kml(page, app_url):
    boot(page, app_url, markers=sample_markers()[:2], shapes=sample_shapes(), track=TRACK)
    open_export_tools(page)
    page.click('#exFormat [data-fmt="kml"]')
    page.uncheck('#exMarkers')
    page.uncheck('#exTrack')
    with page.expect_download() as dl:
        page.click('#exSave')
    assert dl.value.suggested_filename == f'fieldkit-{local_day(page)}.kml'
    kml = open(dl.value.path(), encoding='utf-8').read()
    assert no_error(page, kml) == 'kml'
    assert '<name>Markers</name>' not in kml and '<name>Track</name>' not in kml and kml.count('<Placemark>') == 3
    assert '<name>Ridge &amp; &lt;walk&gt;</name>' in kml


def test_export_opens_from_position_and_track(page, app_url):
    boot(page, app_url, markers=[mk('w1', 'Camp')], track=TRACK)
    page.click('#mTools')
    page.click('#dlgTools [data-tool="track"]')
    page.wait_for_selector('#dlgTrack[open]')
    page.click('#trkExportOpen')
    page.wait_for_selector('#dlgExport[open]')
    page.wait_for_function('!document.querySelector("#dlgTrack").open')
    page.click('#exCancel')
    page.wait_for_function('!document.querySelector("#dlgExport").open')
    page.goto(app_url + '#/tactical/position')
    page.wait_for_selector('#posExport')
    expect(page.locator('#posExport')).to_have_text('Export…')
    page.click('#posExport')
    page.wait_for_selector('#dlgExport[open]')
    expect(page.locator('#exMarkersL')).to_have_text('Markers (1)')


def test_import_shows_counts_and_adds_nothing_until_asked(page, app_url):
    boot(page, app_url, markers=[mk('w1', 'Old')], mapFollow=True)
    import_sheet(page, 'plan.kml', counts_kml())
    expect(page.locator('#imFile')).to_have_text('plan.kml')
    expect(page.locator('#imFound')).to_have_text('12 markers, 2 routes, 1 area')
    expect(page.locator('#imNotes')).to_contain_text('3 items skipped: not a point, line or area')
    expect(page.locator('#imNotes')).not_to_contain_text('already on this phone')
    expect(page.locator('#imAdd')).to_have_text('Add to map')
    assert len(stored(page, 'wps')) == 1 and stored(page, 'shapes') == []
    ev(page, '() => FK.leafletMap().setView([10, 10], 5, { animate: false })')
    page.click('#imAdd')
    page.wait_for_function('!document.querySelector("#dlgImport").open')
    expect(toast(page)).to_have_text('Added 12 markers, 2 routes, 1 area.')
    assert len(stored(page, 'wps')) == 13 and len(stored(page, 'shapes')) == 3
    page.wait_for_function('FK.leafletMap().getBounds().contains([43.011, -76.011]) && FK.leafletMap().getBounds().contains([43.03, -76.03])')
    assert stored(page, 'mapFollow') is False


def test_import_cancel_adds_nothing(page, app_url):
    boot(page, app_url)
    import_sheet(page, 'g.gpx', fixture('garmin.gpx'))
    expect(page.locator('#imFound')).to_have_text('3 markers, 3 routes')
    expect(page.locator('#imNotes')).to_contain_text('1 item skipped: not a point, line or area')
    page.click('#imCancel')
    page.wait_for_function('!document.querySelector("#dlgImport").open')
    assert stored(page, 'wps') == [] and stored(page, 'shapes') == []


def test_same_file_twice_and_singular_wording(page, app_url):
    boot(page, app_url)
    text = counts_kml(markers=1, routes=1, areas=0, skipped=0)
    for _ in range(2):
        import_sheet(page, 'one.kml', text)
        expect(page.locator('#imFound')).to_have_text('1 marker, 1 route')
        page.click('#imCancel')
        page.wait_for_function('!document.querySelector("#dlgImport").open')


@pytest.mark.parametrize('fmt', ['gpx', 'kml'])
def test_reimporting_own_export_adds_nothing(page, app_url, fmt):
    boot(page, app_url, markers=sample_markers(), shapes=sample_shapes(), track=TRACK, ioFormat=fmt.upper())
    open_export_tools(page)
    page.uncheck('#exTrack')   # the track would come back as a new route
    with page.expect_download() as dl:
        page.click('#exSave')
    data = open(dl.value.path(), 'rb').read()
    page.wait_for_function('!document.querySelector("#dlgExport").open')
    import_sheet(page, f'mine.{fmt}', data)
    expect(page.locator('#imFound')).to_have_text('13 markers, 1 route, 1 area, 1 ring')
    expect(page.locator('#imNotes')).to_contain_text('16 already on this phone')
    expect(page.locator('#imAdd')).to_be_disabled()
    expect(page.locator('#imAdd')).to_have_text('Nothing new to add')


def test_an_unnamed_file_imported_twice_adds_nothing_the_second_time(page, app_url):
    boot(page, app_url)
    wpts = ''.join(f'<wpt lat="{43 + i * 0.001}" lon="-76"/>' for i in range(5))
    text = f'<gpx>{wpts}<rte><rtept lat="43" lon="-76"/><rtept lat="43.01" lon="-76.01"/></rte></gpx>'
    import_sheet(page, 'unnamed.gpx', text)
    page.click('#imAdd')
    page.wait_for_function('!document.querySelector("#dlgImport").open')
    assert [w['name'] for w in stored(page, 'wps')] == ['WP 1', 'WP 2', 'WP 3', 'WP 4', 'WP 5']
    assert [s['name'] for s in stored(page, 'shapes')] == ['Route 1']
    import_sheet(page, 'unnamed.gpx', text)
    expect(page.locator('#imNotes')).to_contain_text('6 already on this phone')
    expect(page.locator('#imAdd')).to_be_disabled()


def test_repeats_in_one_file_are_not_already_on_this_phone(page, app_url):
    boot(page, app_url)
    import_sheet(page, 'twice.gpx', '<gpx><wpt lat="43" lon="-76"><name>A</name></wpt><wpt lat="43" lon="-76"><name>A</name></wpt></gpx>')
    expect(page.locator('#imFound')).to_have_text('2 markers')
    expect(page.locator('#imNotes')).to_have_text('1 repeated in the file')
    page.click('#imAdd')
    page.wait_for_function('!document.querySelector("#dlgImport").open')
    expect(toast(page)).to_have_text('Added 1 marker.')
    assert len(stored(page, 'wps')) == 1


DAY = 86_400_000


def test_imported_marker_keeps_its_time(page, app_url):
    from .test_map_tools import NOW
    boot(page, app_url)
    iso = lambda t: ev(page, 't => new Date(t).toISOString()', t)
    old = NOW - 3 * DAY
    text = (f'<gpx><wpt lat="43" lon="-76"><time>{iso(old)}</time><name>Seen</name><sym>Hostile</sym></wpt>'
            '<wpt lat="43.001" lon="-76"><time>1970-01-02T00:00:00Z</time><name>Old</name></wpt>'
            '<wpt lat="43.002" lon="-76"><time>2999-01-01T00:00:00Z</time><name>Future</name></wpt>'
            '<wpt lat="43.003" lon="-76"><time>yesterday-ish</time><name>Garbage</name></wpt></gpx>')
    import_sheet(page, 'times.gpx', text)
    page.click('#imAdd')
    page.wait_for_function('!document.querySelector("#dlgImport").open')
    w = {x['name']: x for x in stored(page, 'wps')}
    assert w['Seen']['t'] == old and w['Seen']['kind'] == 'hostile'
    for n in ('Old', 'Future', 'Garbage'):
        assert abs(w[n]['t'] - NOW) < 60_000, (n, w[n]['t'])
    page.wait_for_selector('#map .mk-pin.stale')   # an affiliation marker three days old fades, as a stale one does
    assert page.locator('#map .mk-pin.stale').count() == 1


def test_import_stops_at_the_shape_limit(page, app_url):
    have = [shape(f's{i}', 'route', [[43, -76 - i * 0.001], [43.01, -76]], name=f'Mine {i}') for i in range(98)]
    boot(page, app_url, shapes=have)
    import_sheet(page, 'routes.kml', counts_kml(markers=0, routes=5, areas=0, skipped=0))
    expect(page.locator('#imNotes')).to_contain_text("3 shapes won't be added: the app holds 100 at most.")
    page.click('#imAdd')
    page.wait_for_function('!document.querySelector("#dlgImport").open')
    expect(toast(page)).to_have_text('Added 2 routes.')
    assert len(stored(page, 'shapes')) == 100


def test_marker_cap_is_said_on_the_sheet(page, app_url):
    boot(page, app_url)
    wpts = ''.join(f'<wpt lat="{43 + i * 1e-5:.5f}" lon="-76"><name>P{i}</name></wpt>' for i in range(2100))
    import_sheet(page, 'many.gpx', f'<gpx>{wpts}</gpx>')
    expect(page.locator('#imFound')).to_have_text('2,000 markers')
    expect(page.locator('#imNotes')).to_contain_text(CAP)
    page.click('#imAdd')
    page.wait_for_function('!document.querySelector("#dlgImport").open')
    assert len(stored(page, 'wps')) == 2000


def test_refusals_are_toasts_and_change_nothing(page, app_url):
    boot(page, app_url)
    ev(page, '() => { window.textCalls = 0; const t = Blob.prototype.text; Blob.prototype.text = function () { window.textCalls++; return t.call(this); }; }')
    cases = [('a.gpx', b'not xml at all', NOT_XML), ('empty.gpx', b'', NOT_XML), ('plan.kmz', b'PK\x03\x04\x14\x00rest', KMZ),
             ('page.kml', b'<html><body>hi</body></html>', NOT_XML),
             ('blank.kml', b'<kml><Document><GroundOverlay/></Document></kml>', NOTHING),
             ('many.gpx', ('<gpx>' + '<wpt lat="43" lon="-76"/>' * 5001 + '</gpx>').encode(), TOO_MANY)]
    for name, data, msg in cases:
        run_import(page, name, data)
        expect(toast(page)).to_have_text(msg)
        assert page.locator('#dlgImport[open]').count() == 0
        ev(page, '() => { const t = document.querySelector("#toast"); t.textContent = ""; }')
    calls = ev(page, 'window.textCalls')
    run_import(page, 'huge.gpx', b' ' * (6 * 1024 * 1024))
    expect(toast(page)).to_have_text(TOO_BIG)
    assert ev(page, 'window.textCalls') == calls   # refused without reading
    assert stored(page, 'wps') == [] and stored(page, 'shapes') == []


def test_markup_in_names_is_text(page, app_url):
    boot(page, app_url)
    import_sheet(page, '<b>x</b>.kml', fixture('script-name.kml'))
    expect(page.locator('#imFile')).to_have_text('<b>x</b>.kml')
    page.click('#imAdd')
    page.wait_for_function('!document.querySelector("#dlgImport").open')
    wps = stored(page, 'wps')
    assert wps[0]['name'] == '<script>window.pwned=1</script>Rally'
    assert wps[0]['note'] == 'Meet here'
    assert stored(page, 'shapes')[0]['name'] == '<img src=x onerror="window.pwned=4">Creek'
    page.wait_for_timeout(300)
    assert ev(page, 'window.pwned') is None
    assert page.locator('#map script, #map img[src="x"]').count() == 0
    page.click('#mList')
    expect(page.locator('#lsList')).to_contain_text('<script>window.pwned=1</script>Rally')
    expect(page.locator('#lsList')).to_contain_text('<img src=x onerror="window.pwned=4">Creek')
    assert ev(page, 'window.pwned') is None


def test_no_network_request_during_import(page, app_url):
    boot(page, app_url)
    seen = []
    page.on('request', lambda r: seen.append(r.url))
    for name in ('references.kml', 'google-earth.kml', 'garmin.gpx', 'script-name.kml'):
        import_sheet(page, name, fixture(name))
        page.click('#imAdd')
        page.wait_for_function('!document.querySelector("#dlgImport").open')
    page.wait_for_timeout(500)
    assert not [u for u in seen if 'fk-test' in u], seen
    assert len(stored(page, 'wps')) >= 6


def test_storage_full_part_way_keeps_items_for_the_session(page, app_url):
    boot(page, app_url, full='wps')
    import_sheet(page, 'plan.kml', counts_kml(markers=3, routes=1, areas=0, skipped=0))
    page.click('#imAdd')
    page.wait_for_function('!document.querySelector("#dlgImport").open')
    expect(toast(page)).to_have_text(FULL)
    assert ev(page, 'FK.tac.markers().length') == 3 and len(stored(page, 'shapes')) == 1
