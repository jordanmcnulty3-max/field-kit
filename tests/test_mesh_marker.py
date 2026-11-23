"""MMK: a Field Kit marker as a Meshtastic waypoint and back. Pure functions, run in the page. Times are the phone's LOCAL
time, so every date here is built in the page (month is 0-based there) and the tests pass in any time zone."""
import pytest

KINDS = ['point', 'camp', 'vehicle', 'water', 'cache', 'hazard', 'rally', 'observe', 'medical', 'friend', 'hostile', 'neutral', 'unknown']
AFFIL = ['friend', 'hostile', 'neutral', 'unknown']
ICONS = dict(point=0x1F4CD, camp=0x26FA, vehicle=0x1F699, water=0x1F4A7, cache=0x1F4E6, hazard=0x26A0, rally=0x1F6A9,
             observe=0x1F52D, medical=0x1F3E5, friend=0x1F7E6, hostile=0x2666, neutral=0x1F7E9, unknown=0x2753)

# JS helper: at(y, month1to12, day, h, m) -> local ms
AT = '(y, mo, d, h, mi) => new Date(y, mo - 1, d, h, mi).getTime()'


@pytest.fixture
def ready(page, app_url):
    page.goto(app_url)
    page.wait_for_function('typeof MMK !== "undefined"')
    return page


def js(page, body, arg=None):
    """Run `body` (a JS function expression taking (arg, at)) in the page."""
    return page.evaluate(f'([arg]) => ({body})(arg, {AT})', [arg])


def test_the_icons_are_the_agreed_code_points(ready):
    assert js(ready, '(a) => MMK.ICON') == ICONS
    assert js(ready, '(a) => [MMK.NAME_MAX, MMK.NOTE_MAX]') == [29, 99]


def test_kind_for_knows_each_icon_and_nothing_else(ready):
    for k, i in ICONS.items():
        assert js(ready, '(a) => MMK.kindFor(a)', i) == k
    for i in (0, 0x1F600, 0x1F4CE, 1):
        assert js(ready, '(a) => MMK.kindFor(a)', i) is None


@pytest.mark.parametrize('kind', KINDS)
def test_every_kind_round_trips(ready, kind):
    r = js(ready, """(k, at) => {
      const t = at(2026, 11, 22, 14, 32), now = at(2026, 11, 22, 15, 0);
      const wp = MMK.toWaypoint({ name: 'Rally 1', note: 'by the gate', kind: k, lat: 43.01, lon: -76.02, t }, 777);
      return { wp, back: MMK.fromWaypoint(wp, now), t, now };
    }""", kind)
    wp, back = r['wp'], r['back']
    assert wp['id'] == 777 and wp['icon'] == ICONS[kind] and wp['lockedTo'] == 0 and wp['expire'] == 0
    assert (wp['lat'], wp['lon'], wp['name']) == (43.01, -76.02, 'Rally 1')
    assert (back['kind'], back['name'], back['note'], back['lat'], back['lon'], back['icon']) == (kind, 'Rally 1', 'by the gate', 43.01, -76.02, ICONS[kind])
    if kind in AFFIL:
        assert wp['description'].endswith('. by the gate') and wp['description'].startswith('Seen ')
        assert back['t'] == r['t'] and back['rx'] is False
    else:
        assert wp['description'] == 'by the gate'
        assert back['t'] == r['now'] and back['rx'] is True


def test_the_seen_prefix_reads_like_the_example_in_english_24_hour(ready):
    assert js(ready, '(a, at) => MMK.seen(at(2026, 11, 22, 14, 32))') == 'Seen 22 Nov 14:32. '
    assert js(ready, '(a, at) => MMK.seen(at(2027, 1, 3, 9, 5))') == 'Seen 3 Jan 09:05. '
    assert js(ready, '(a, at) => MMK.seen(at(2026, 12, 31, 0, 0))') == 'Seen 31 Dec 00:00. '


def test_an_unknown_icon_becomes_a_point_and_keeps_its_icon(ready):
    back = js(ready, """(a, at) => MMK.fromWaypoint({ id: 5, lat: 43, lon: -76, name: 'Fuel', description: 'diesel', icon: 0x1F6E2, expire: 0 }, at(2026, 11, 22, 15, 0))""")
    assert (back['kind'], back['icon'], back['note'], back['rx']) == ('point', 0x1F6E2, 'diesel', True)
    none = js(ready, "(a, at) => MMK.fromWaypoint({ lat: 43, lon: -76, name: 'x', description: '', icon: 0 }, at(2026, 11, 22, 15, 0))")
    assert (none['kind'], none['icon']) == ('point', 0)


def test_a_resend_keeps_the_foreign_icon_and_the_expiry(ready):
    r = js(ready, """() => {
      const m = k => ({ name: 'Fuel', note: '', kind: k, lat: 43, lon: -76, t: 0 });
      return {
        foreign: MMK.toWaypoint(m('point'), 1, { icon: 0x1F6E2, expire: 1800000000 }),
        known: MMK.toWaypoint(m('point'), 1, { icon: 0x26FA, expire: 0 }),          // a known icon never wins
        changed: MMK.toWaypoint(m('camp'), 1, { icon: 0x1F6E2, expire: 0 }),         // only a Point keeps it
        zero: MMK.toWaypoint(m('point'), 1, { icon: 0, expire: 0 }),
        none: MMK.toWaypoint(m('point'), 1),
        friend: MMK.toWaypoint(m('friend'), 1, { icon: 0x1F6E2, expire: 0 })
      };
    }""")
    assert (r['foreign']['icon'], r['foreign']['expire']) == (0x1F6E2, 1800000000)
    assert r['known']['icon'] == ICONS['point']
    assert r['changed']['icon'] == ICONS['camp']
    assert r['zero']['icon'] == ICONS['point'] and r['none']['icon'] == ICONS['point'] and r['none']['expire'] == 0
    assert r['friend']['icon'] == ICONS['friend']


def test_the_prefix_round_trips_across_midnight_and_new_year(ready):
    r = js(ready, """(a, at) => {
      const rt = (t, now) => { const wp = MMK.toWaypoint({ name: 'A', note: 'n', kind: 'hostile', lat: 43, lon: -76, t }, 1); return MMK.fromWaypoint(wp, now); };
      const x1 = { t: at(2026, 11, 21, 23, 50), now: at(2026, 11, 22, 0, 10) };       // seen before midnight, received after
      const x2 = { t: at(2026, 12, 31, 23, 50), now: at(2027, 1, 1, 0, 10) };          // across New Year
      const x3 = { t: at(2026, 1, 1, 0, 5), now: at(2026, 12, 20, 23, 55) };          // early January seen from late December: this year
      return [x1, x2, x3].map(x => ({ ...rt(x.t, x.now), want: x.t }));
    }""")
    for x in r:
        assert x['t'] == x['want'] and x['rx'] is False and x['note'] == 'n'


def test_a_prefix_timed_after_now_rolls_back_a_year(ready):
    r = js(ready, """(a, at) => {
      const wp = d => ({ lat: 43, lon: -76, name: 'x', icon: 0x1F7E6, description: d + 'gate' });
      const now = at(2026, 11, 22, 10, 0);
      return {
        later_today: MMK.fromWaypoint(wp('Seen 22 Nov 14:32. '), now),     // 4.5 h ahead: a clock a little off, same year
        next_week: MMK.fromWaypoint(wp('Seen 30 Nov 09:00. '), now),       // beyond now + 24 h: last year
        want_later: at(2026, 11, 22, 14, 32), want_last: at(2025, 11, 30, 9, 0)
      };
    }""")
    assert r['later_today']['t'] == r['want_later'] and r['next_week']['t'] == r['want_last']
    assert r['next_week']['rx'] is False and r['next_week']['note'] == 'gate'


def test_a_leap_day_goes_to_the_latest_leap_year(ready):
    r = js(ready, """(a, at) => ({
      t: MMK.fromWaypoint({ lat: 43, lon: -76, name: 'x', icon: 0x1F7E6, description: 'Seen 29 Feb 12:00. ' }, at(2026, 11, 22, 10, 0)).t,
      want: at(2024, 2, 29, 12, 0) })""")
    assert r['t'] == r['want']


def test_no_prefix_means_received_now(ready):
    r = js(ready, """(a, at) => { const now = at(2026, 11, 22, 10, 0);
      return { back: MMK.fromWaypoint({ lat: 43, lon: -76, name: 'Gate', description: 'plain text', icon: 0x1F7E9 }, now), now }; }""")
    assert r['back']['rx'] is True and r['back']['t'] == r['now'] and r['back']['note'] == 'plain text' and r['back']['kind'] == 'neutral'


def test_text_that_only_looks_like_a_prefix_is_left_alone(ready):
    r = js(ready, """(a, at) => { const now = at(2026, 11, 22, 10, 0);
      const f = d => MMK.fromWaypoint({ lat: 43, lon: -76, name: 'x', icon: 0x1F7E6, description: d }, now);
      return [f('Seen 32 Nov 10:00. a'), f('Seen 22 Nov 25:00. a'), f('Seen 22 Nov 10:00 a'), f('seen 22 Nov 10:00. a'), f('Seen 22 Nov 10:61. a')]; }""")
    for x in r:
        assert x['rx'] is True and x['note'].startswith(('Seen', 'seen'))


def test_a_place_kind_note_is_never_parsed_for_a_prefix(ready):
    back = js(ready, """(a, at) => MMK.fromWaypoint({ lat: 43, lon: -76, name: 'x', icon: 0x26FA, description: 'Seen 22 Nov 10:00. we camped' }, at(2026, 11, 22, 12, 0))""")
    assert back['kind'] == 'camp' and back['note'] == 'Seen 22 Nov 10:00. we camped' and back['rx'] is True


def test_byte_counting_counts_utf8_not_characters(ready):
    s = 'Café ⛺ north ridge lookout'
    assert js(ready, '(a) => MMK.bytes(a)', s) == len(s.encode('utf-8')) == 29   # 26 characters; é is 2 bytes, ⛺ is 3
    assert js(ready, '(a) => MMK.bytes(a)', s + 'x') == 30
    assert js(ready, '(a) => MMK.bytes(a)', '') == 0
    assert js(ready, '(a) => MMK.bytes(a)', '😀') == 4


def test_fits_at_the_name_and_note_limits(ready):
    r = js(ready, """() => {
      const m = (name, note, kind) => MMK.fits({ name, note, kind: kind || 'point' });
      return { n29: m('a'.repeat(29), ''), n30: m('a'.repeat(30), ''), n29b: m('Café ⛺ north ridge lookout', ''), n30b: m('Café ⛺ north ridge lookout!', ''),
        // 29 bytes with a multi-byte character in it
        multi: m('é'.repeat(14) + 'a', ''), multi_over: m('é'.repeat(15), ''),
        p99: m('x', 'a'.repeat(99)), p100: m('x', 'a'.repeat(100)),
        f80: m('x', 'a'.repeat(80), 'friend'), f81: m('x', 'a'.repeat(81), 'friend'),
        room: ['point', 'camp', 'friend', 'hostile', 'neutral', 'unknown'].map(k => MMK.noteRoom(k)) };
    }""")
    assert r['n29'] == dict(ok=True, name=True, note=True)
    assert r['n30'] == dict(ok=False, name=False, note=True)
    assert r['n29b']['name'] is True and r['n30b']['name'] is False and r['multi']['name'] is True and r['multi_over']['name'] is False
    assert r['p99']['ok'] is True and r['p100'] == dict(ok=False, name=True, note=False)
    assert r['f80']['ok'] is True and r['f81'] == dict(ok=False, name=True, note=False)
    assert r['room'] == [99, 99, 80, 80, 80, 80]   # 99 minus "Seen 22 Nov 14:32. " (19 bytes)


def test_to_waypoint_always_fits_the_wire_and_never_cuts_a_character(ready):
    r = js(ready, """(a, at) => ['point', 'friend'].map(kind => {
      const wp = MMK.toWaypoint({ name: 'é'.repeat(20), note: '⛺'.repeat(40), kind, lat: 43, lon: -76, t: at(2026, 11, 22, 14, 32) }, 9);
      return { name: wp.name, nameBytes: MMK.bytes(wp.name), descBytes: MMK.bytes(wp.description), desc: wp.description };
    })""")
    for x in r:
        assert x['nameBytes'] <= 29 and x['name'] == 'é' * 14 and x['descBytes'] <= 99
        assert '�' not in x['desc'] and '�' not in x['name']
    assert r[0]['desc'] == '⛺' * 33 and r[1]['desc'].startswith('Seen 22 Nov 14:32. ⛺') and r[1]['descBytes'] == 19 + 3 * 26


def test_an_affiliation_marker_with_no_time_gets_no_prefix(ready):
    wp = js(ready, "() => MMK.toWaypoint({ name: 'A', note: 'n', kind: 'friend', lat: 43, lon: -76, t: 0 }, 1)")
    assert wp['description'] == 'n'


@pytest.mark.parametrize('lat,lon', [(0, 0), (91, 10), (-91, 10), (10, 181), (10, -181), (None, 10), ('43', '-76'), (float('nan'), 1)])
def test_bad_positions_give_null(ready, lat, lon):
    assert js(ready, "(a, at) => MMK.fromWaypoint({ lat: a[0], lon: a[1], name: 'x', icon: 0x1F4CD, description: '' }, at(2026, 11, 22, 12, 0))", [lat, lon]) is None
    assert js(ready, '(a) => MMK.fromWaypoint(null, 1)') is None


def test_lat_zero_alone_is_a_real_place_and_extremes_are_kept(ready):
    r = js(ready, """(a, at) => [[0, 10], [10, 0], [90, 180], [-90, -180]].map(p => MMK.fromWaypoint({ lat: p[0], lon: p[1], name: 'x', icon: 0, description: '' }, at(2026, 11, 22, 12, 0)))""")
    assert all(x is not None for x in r)


def test_empty_name_becomes_marker_and_markup_is_returned_as_text(ready):
    r = js(ready, """(a, at) => { const now = at(2026, 11, 22, 12, 0);
      const f = (name, d) => MMK.fromWaypoint({ lat: 43, lon: -76, name, icon: 0x1F4CD, description: d }, now);
      return [f('', ''), f('   ', ''), f('<img src=x onerror=1>', '<b>hi</b> & "q"')]; }""")
    assert r[0]['name'] == 'Marker' and r[1]['name'] == 'Marker'
    assert r[2]['name'] == '<img src=x onerror=1>' and r[2]['note'] == '<b>hi</b> & "q"'


def test_expire_passes_through_and_bad_values_are_zero(ready):
    r = js(ready, """(a, at) => [1800000000, 0, -5, null, 'x'].map(e => MMK.fromWaypoint({ lat: 43, lon: -76, name: 'x', icon: 0, description: '', expire: e }, at(2026, 11, 22, 12, 0)).expire)""")
    assert r == [1800000000, 0, 0, 0, 0]


def test_mmk_is_pure(ready):
    src = ready.evaluate('() => MMK.toWaypoint.toString() + MMK.fromWaypoint.toString() + MMK.fits.toString() + MMK.seen.toString()')
    assert 'document' not in src and 'FK.' not in src
