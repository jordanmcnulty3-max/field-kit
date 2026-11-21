"""Navigate display (v7.8 Tactical, design section 5): the panel at the top of Position, the strip on the map, route stepping,
time to go and Back to start. The pure rules (turn text, arrival and advance radii, speed from a window of fixes, time text,
position age) are on TNAV and are tested directly as well as through the screen."""
import math
import re

import pytest
from playwright.sync_api import expect

from .tac import store, open_map, heading, open_track
from .test_map import tiles_ok
from .test_tactical_existing import GPS_STUB, watches_become, go

HOME = (43.0, -76.0)
NOW = 1_800_000_000_000
R = 6371008.8
WAKE_STUB = """(() => { Object.defineProperty(navigator, 'wakeLock', { configurable: true, value: {
  request: async () => ({ addEventListener() {}, release: async () => {} }) } }); })()"""


def dest(lat, lon, brg, m):
    """The same great-circle formula as TGEOM.dest."""
    p1, l1, b, dr = math.radians(lat), math.radians(lon), math.radians(brg), m / R
    p2 = math.asin(math.sin(p1) * math.cos(dr) + math.cos(p1) * math.sin(dr) * math.cos(b))
    l2 = l1 + math.atan2(math.sin(b) * math.sin(dr) * math.cos(p1), math.cos(dr) - math.sin(p1) * math.sin(p2))
    return (math.degrees(p2), (math.degrees(l2) + 540) % 360 - 180)


def mk(id_, name, lat, lon):
    return {'id': id_, 'name': name, 'lat': lat, 'lon': lon, 'alt': None, 't': 1, 'kind': 'rally', 'note': ''}


RALLY = dest(*HOME, 73, 412)
P1 = dest(*HOME, 0, 300)
P2 = dest(*P1, 90, 300)
ROUTE = {'id': 'r1', 'type': 'route', 'name': 'Ridge walk', 'pts': [list(HOME), list(P1), list(P2)], 't': 1}


def boot(page, app_url, markers=(), shapes=(), night=False, view=HOME, path='#/tactical/map', decl_mode='manual', **kv):
    """decl_mode 'manual' with no typed value keeps the compass magnetic, so the arrow and turn figures here are plain
    numbers (v7.8 works declination out from the position on a fresh install). None seeds no mode, like a fresh install."""
    page.clock.install(time=NOW / 1000)
    page.goto('about:blank')
    tiles_ok(page)
    if decl_mode:
        kv = {'declMode': decl_mode, **kv}
    store(page, **{'wps': list(markers), 'shapes': list(shapes), 'advAck': True, 'night': night,
                   'mapView': {'lat': view[0], 'lon': view[1], 'z': 15}, 'mapFollow': False, **kv})
    open_map(page, app_url)
    if path != '#/tactical/map':
        go(page, path[1:])
        page.wait_for_function('p => location.hash === p', arg=path)


def position(page):
    go(page, '/tactical/position')
    page.wait_for_function("FK.view() === 'position' && !document.querySelector('#view-position').hidden")


def fix(page, lat, lon, acc=5, ago=0):
    """A GPS fix taken `ago` milliseconds before the page's now."""
    page.evaluate('f => FK._test.fix({ lat: f.lat, lon: f.lon, acc: f.acc, t: Date.now() - f.ago })',
                  {'lat': lat, 'lon': lon, 'acc': acc, 'ago': ago})


def ev(page, js, arg=None):
    return page.evaluate(js, arg)


def txt(page, sel):
    return page.locator(sel).inner_text()


def rotation(page):
    m = re.search(r'rotate\((-?[\d.]+)deg\)', ev(page, "document.querySelector('#nvArrowG').style.transform"))
    return float(m.group(1))


def lcg(seed):
    """A fixed linear congruential generator (Numerical Recipes constants): the same jitter on every run."""
    x = seed & 0xFFFFFFFF
    while True:
        x = (1664525 * x + 1013904223) & 0xFFFFFFFF
        yield x / 2 ** 32


def fixes_js(target, n=60, speed=1.4, togo=420, step_ms=1000, skip=None, wild=None, wild_m=200, t0=NOW, acc=5,
             mode='toward', jitter=0, seed=0, wild_brg=90):
    """n fixes one step_ms apart, the newest at t0, moving at `speed` m/s. mode toward: straight at target from due south, the
    newest `togo` m short of it; away: straight away from it, the newest `togo` m off; across: at right angles, passing `togo`
    m south of it half-way through the window. skip: (a, b) drops fixes a..b-1; wild: index of a fix moved wild_m metres east
    (a GPS jump); jitter: each fix moved up to +-jitter metres north and east by a seeded generator."""
    out, rnd = [], lcg(seed)
    for k in range(n):
        back = (n - 1 - k) * speed * step_ms / 1000
        if mode == 'toward':
            lat, lon = dest(*target, 180, togo + back)
        elif mode == 'away':
            lat, lon = dest(*target, 180, togo - back)
        else:
            lat, lon = dest(*dest(*target, 180, togo), 90, (k - (n - 1) / 2) * speed * step_ms / 1000)
        if jitter:
            lat, lon = dest(lat, lon, 0, (2 * next(rnd) - 1) * jitter)
            lat, lon = dest(lat, lon, 90, (2 * next(rnd) - 1) * jitter)
        if wild is not None and k == wild:
            lat, lon = dest(lat, lon, wild_brg, wild_m)
        if not (skip and skip[0] <= k < skip[1]):
            out.append({'lat': lat, 'lon': lon, 't': t0 - (n - 1 - k) * step_ms, 'acc': acc})
    return out


def walk(page, target, **kw):
    """Feed fixes_js's fixes through the real GPS path, the newest taken now."""
    pts = [{**p, 'ago': -p['t']} for p in fixes_js(target, t0=0, **kw)]
    page.evaluate('ps => { const now = Date.now(); ps.forEach(p => FK._test.fix({ lat: p.lat, lon: p.lon, acc: p.acc, t: now - p.ago })); }', pts)


def closing(page, fixes, target):
    return ev(page, '([f, t]) => TNAV.closing(f, { lat: t[0], lon: t[1] })', [fixes, list(target)])


def pace(page, fixes, target):
    return ev(page, '([f, t]) => TNAV.pace(f, { lat: t[0], lon: t[1] })', [fixes, list(target)])


@pytest.fixture
def ready(page, app_url):
    page.goto(app_url)
    page.wait_for_function('window.FK && typeof TNAV !== "undefined"')
    return page


# ---------- TNAV: pure rules ----------

@pytest.mark.parametrize('brg,hdg,want', [
    (73, 53, 'Turn 20° right'), (73, 93, 'Turn 20° left'), (73, 70, 'Straight ahead'), (73, 78, 'Straight ahead'),
    (73, 68, 'Straight ahead'), (73, 66, 'Turn 7° right'), (10, 350, 'Turn 20° right'), (350, 10, 'Turn 20° left'),
    (180, 0, 'Turn 180° right'), (0, 180, 'Turn 180° right'), (90, 270, 'Turn 180° right'), (0, 0, 'Straight ahead'),
    (100.4, 0, 'Turn 100° right'), (0, 359.9, 'Straight ahead')])
def test_turn_text(ready, brg, hdg, want):
    assert ev(ready, '([b, h]) => TNAV.turnText(b, h)', [brg, hdg]) == want


@pytest.mark.parametrize('brg,hdg,want', [(73, 53, 20), (10, 350, 20), (350, 10, -20), (180, 0, 180), (0, 180, 180), (5, 5, 0)])
def test_turn_angle_takes_the_short_way(ready, brg, hdg, want):
    assert ev(ready, '([b, h]) => TNAV.turnAngle(b, h)', [brg, hdg]) == pytest.approx(want)


@pytest.mark.parametrize('acc,want', [(5, 15), (15, 15), (30, 30), (50, 50), (80, 50), (None, 15)])
def test_arrival_radius(ready, acc, want):
    assert ev(ready, 'a => TNAV.arriveRadius(a)', acc) == want


@pytest.mark.parametrize('acc,want', [(5, 25), (25, 25), (40, 40), (100, 100), (101, None), (500, None), (None, None)])
def test_advance_radius(ready, acc, want):
    assert ev(ready, 'a => TNAV.advanceRadius(a)', acc) == want


TGT = dest(*HOME, 0, 1000)


def test_closing_speed_walking_at_the_target(ready):
    f = fixes_js(TGT)
    assert closing(ready, f, TGT) == pytest.approx(1.4, abs=0.01)
    v = pace(ready, f, TGT)
    assert ev(ready, '([m, v]) => TNAV.timeText(m, v)', [420, v]) == 'about 5 min'


def test_closing_speed_ignores_fixes_older_than_60_seconds(ready):
    old = fixes_js(TGT, n=30, speed=10, togo=420 + 1.4 * 60, t0=NOW - 61000)   # driving, a minute ago
    assert closing(ready, old + fixes_js(TGT), TGT) == pytest.approx(1.4, abs=0.01)


def test_closing_speed_window_rules(ready):
    assert closing(ready, fixes_js(TGT, n=2, step_ms=15000), TGT) is None             # two fixes
    assert closing(ready, fixes_js(TGT, n=3, step_ms=15000), TGT) is None             # three fixes over 30 s
    assert closing(ready, fixes_js(TGT, n=5, step_ms=7500), TGT) is None              # five fixes over 30 s
    assert closing(ready, fixes_js(TGT, n=6, step_ms=6000), TGT) == pytest.approx(1.4, abs=0.01)   # six over 30 s
    assert closing(ready, fixes_js(TGT, n=6, step_ms=5990), TGT) is None              # six over 29.95 s
    assert closing(ready, fixes_js(TGT, n=21), TGT) is None                            # 20 s span
    assert closing(ready, fixes_js(TGT, n=30), TGT) is None                            # 29 s span
    assert closing(ready, fixes_js(TGT, n=31), TGT) == pytest.approx(1.4, abs=0.01)   # 30 s span
    assert closing(ready, fixes_js(TGT, skip=(30, 44)), TGT) == pytest.approx(1.4, abs=0.01)   # a 15 s gap
    assert closing(ready, fixes_js(TGT, skip=(30, 45)), TGT) is None                  # a 16 s gap
    assert closing(ready, fixes_js(TGT, skip=(10, 50)), TGT) is None                  # a 41 s hole
    assert closing(ready, [], TGT) is None
    assert ev(ready, 'f => TNAV.closing(f, null)', fixes_js(TGT)) is None


def test_closing_speed_keeps_only_fixes_of_50_m_or_better(ready):
    assert closing(ready, fixes_js(TGT, acc=80), TGT) is None
    assert closing(ready, fixes_js(TGT, acc=50), TGT) == pytest.approx(1.4, abs=0.01)
    no_acc = [{k: v for k, v in f.items() if k != 'acc'} for f in fixes_js(TGT)]
    assert closing(ready, no_acc, TGT) is None
    # Poor fixes in the middle leave a hole: 16 s of them is a gap over 15 s.
    f = fixes_js(TGT)
    for p in f[20:36]:
        p['acc'] = 80
    assert closing(ready, f, TGT) is None
    for p in f[20:36]:
        p['acc'] = 5
    for p in f[22:36]:
        p['acc'] = 80          # 15 s between the kept fixes either side
    assert closing(ready, f, TGT) == pytest.approx(1.4, abs=0.01)
    # The newest 16 fixes poor: the kept ones end more than 15 s before the newest fix.
    f = fixes_js(TGT)
    for p in f[44:]:
        p['acc'] = 80
    assert closing(ready, f, TGT) is None


@pytest.mark.parametrize('n', [31, 60], ids=['window-just-filled-30s', 'full-60s'])
@pytest.mark.parametrize('jitter', [3, 8])
def test_a_stationary_phone_never_gets_a_time(ready, jitter, n):
    for seed in range(20):
        f = fixes_js(TGT, n=n, speed=0, jitter=jitter, seed=seed)
        assert pace(ready, f, TGT) is None, seed
        assert abs(closing(ready, f, TGT)) < 0.5, seed


def test_walking_away_or_across_gets_no_time(ready):
    assert closing(ready, fixes_js(TGT, mode='away'), TGT) == pytest.approx(-1.4, abs=0.01)
    assert pace(ready, fixes_js(TGT, mode='away'), TGT) is None
    assert abs(closing(ready, fixes_js(TGT, mode='across'), TGT)) < 0.05
    assert pace(ready, fixes_js(TGT, mode='across'), TGT) is None


def test_one_gps_jump_does_not_decide_it(ready):
    mid = fixes_js(TGT, wild=30)
    assert pace(ready, mid, TGT) == pytest.approx(1.4, abs=0.01)                       # only the ends count
    newest = fixes_js(TGT, wild=59)
    assert pace(ready, newest, TGT) == pytest.approx(1.4, abs=0.01)                    # the median of the newest three
    oldest = fixes_js(TGT, wild=0)
    assert pace(ready, oldest, TGT) == pytest.approx(1.4, abs=0.01)


def test_six_fixes_closing_30_m_are_enough_and_three_are_not(ready):
    assert pace(ready, fixes_js(TGT, n=3, step_ms=10000), TGT) is None
    # Six fixes over 30 s at 1.4 m/s: the median ends (2nd and 5th fix) are 18 s apart, 25 m nearer: under 30 m, no time.
    assert closing(ready, fixes_js(TGT, n=6, step_ms=6000), TGT) == pytest.approx(1.4, abs=0.01)
    assert pace(ready, fixes_js(TGT, n=6, step_ms=6000), TGT) is None
    # Six over 37.5 s: the ends are 22.5 s apart, 31.5 m nearer.
    v = pace(ready, fixes_js(TGT, n=6, step_ms=7500), TGT)
    assert v == pytest.approx(1.4, abs=0.01)
    assert ev(ready, '([m, v]) => TNAV.timeText(m, v)', [420, v]) == 'about 5 min'


def test_a_newest_jump_toward_the_target_with_six_fixes_shows_no_time(ready):
    f = fixes_js(TGT, n=6, step_ms=7500, wild=5, wild_brg=0)    # the newest fix 200 m nearer the target
    assert closing(ready, f, TGT) == pytest.approx(1.4, abs=0.01)    # the median of the newest three outvotes it
    # but the jump is in the scatter (about 80 m around the line), so 4 x scatter is far more than the 31.5 m closed: no time.
    assert ev(ready, '([f, t]) => TNAV.scatter(f, { lat: t[0], lon: t[1] })', [f, list(TGT)]) > 60
    assert pace(ready, f, TGT) is None


def test_pace_only_between_half_and_twelve_metres_a_second(ready):
    target = dest(*HOME, 0, 5000)
    assert pace(ready, fixes_js(target, speed=0.2), target) is None
    assert pace(ready, fixes_js(target, speed=0), target) is None
    assert pace(ready, fixes_js(target, speed=0.51), target) is None            # 29 m between the ends: under 30 m
    assert pace(ready, fixes_js(target, speed=0.6), target) == pytest.approx(0.6, abs=0.005)
    assert pace(ready, fixes_js(target, speed=11.9), target) == pytest.approx(11.9, abs=0.05)
    assert pace(ready, fixes_js(target, speed=13), target) is None


# ---------- Time to go: start and keep (one bit of memory) ----------

def alternating(n, speed, a, target=TGT, togo=420):
    """n fixes 1 s apart at `speed` toward target, each moved a metres nearer then farther in turn (first one nearer)."""
    out = []
    for k in range(n):
        lat, lon = dest(*target, 180, togo + (n - 1 - k) * speed)
        lat, lon = dest(lat, lon, 0, a if k % 2 == 0 else -a)
        out.append({'lat': lat, 'lon': lon, 't': NOW - (n - 1 - k) * 1000, 'acc': 5})
    return out


def gate(page, fixes, target, on):
    return ev(page, '([f, t, on]) => TNAV.timeGate(f, { lat: t[0], lon: t[1] }, on)', [fixes, list(target), on])


def test_scatter_is_the_spread_around_a_straight_line(ready):
    assert ev(ready, '([f, t]) => TNAV.scatter(f, { lat: t[0], lon: t[1] })', [fixes_js(TGT), list(TGT)]) < 0.01
    sc = ev(ready, '([f, t]) => TNAV.scatter(f, { lat: t[0], lon: t[1] })', [alternating(61, 0.7, 11), list(TGT)])
    assert sc == pytest.approx(11 * math.sqrt(61 / 59), abs=0.2)


def test_time_starts_on_the_strict_rule_and_keeps_on_the_loose_one(ready):
    # Ends 40.6 m nearer (0.7 m/s over 58 s) with a scatter of 11.2 m: 4 x 11.2 = 44.7 is more than 40.6, so no time starts;
    # 2.5 x 11.2 = 28 is less, so a time already showing stays.
    f = alternating(61, 0.7, 11)
    assert gate(ready, f, TGT, False) == {'on': False, 'v': None}
    g = gate(ready, f, TGT, True)
    assert g['on'] is True and g['v'] == pytest.approx(0.7, abs=0.01)
    # 0.45 m/s: 26 m over 58 s. Too slow and too short to start (30 m, 0.5 m/s); enough to keep (20 m, 0.35 m/s).
    slow = fixes_js(TGT, speed=0.45)
    assert gate(ready, slow, TGT, False)['on'] is False
    assert gate(ready, slow, TGT, True)['on'] is True
    # 0.3 m/s: 17 m, below both.
    assert gate(ready, fixes_js(TGT, speed=0.3), TGT, True)['on'] is False
    # Keep still needs every window rule and at most 12 m/s.
    assert gate(ready, fixes_js(TGT, skip=(30, 45)), TGT, True)['on'] is False
    assert gate(ready, fixes_js(TGT, acc=80), TGT, True)['on'] is False
    assert gate(ready, fixes_js(TGT, speed=13, togo=420), TGT, True)['on'] is False
    assert gate(ready, fixes_js(TGT, mode='away'), TGT, True)['on'] is False
    assert ev(ready, 'TNAV.START') == {'m': 30, 'k': 4, 'v': 0.5}
    assert ev(ready, 'TNAV.KEEP') == {'m': 20, 'k': 2.5, 'v': 0.35}


# ---------- Sliding-window simulation (the review's method) ----------
# Fixes at 1 Hz with accuracy 8 and independent Gaussian noise (Box-Muller on a fixed LCG) on north and east. The window slides
# one second at a time, the newest fix being "now", carrying the one bit of memory from second to second as the screen does.
# Each second either shows a time or not. 20 seeds (1-20). A run is a list of phases [seconds, speed]: speed > 0 toward the
# target (1000 m north of the start), < 0 away, 0 standing. "steady": 360 s judged from second 60 on.
SLIDE = """([seed, sd, phases, togo0, from]) => {
  let x = seed >>> 0;
  const u = () => { x = (Math.imul(1664525, x) + 1013904223) >>> 0; return (x + 0.5) / 4294967296; };
  const g = () => Math.sqrt(-2 * Math.log(u())) * Math.cos(2 * Math.PI * u());
  const T = TGEOM.dest(43, -76, 0, togo0), fixes = [], truth = [], out = [];
  let along = 0, k = 0;
  phases.forEach(([secs, v]) => { for (let i = 0; i < secs; i++, k++) {
    if (k) along += v;
    let p = TGEOM.dest(43, -76, 0, along);
    p = TGEOM.dest(p.lat, p.lon, 0, sd * g()); p = TGEOM.dest(p.lat, p.lon, 90, sd * g());
    fixes.push({ lat: p.lat, lon: p.lon, t: k * 1000, acc: 8 }); truth.push([v, along]);
  } });
  let on = false;
  for (let i = 0; i < fixes.length; i++) {
    const win = fixes.slice(Math.max(0, i - 60), i + 1), f = fixes[i], r = TNAV.timeGate(win, T, on);
    on = r.on;
    if (i < from) continue;
    const [v, al] = truth[i];
    // [showing, shown time over the true time to go (walking toward only)]
    out.push([r.on, r.on && v > 0 ? (GEO.distance(f.lat, f.lon, T.lat, T.lon) / r.v) / ((togo0 - al) / v) : null]);
  }
  return out;
}"""
SEEDS = range(1, 21)


def slide(page, sd, phases, steady=False):
    """Per seed, [showing, ratio] for each second."""
    return [page.evaluate(SLIDE, [seed, sd, phases, 1000, 60 if steady else 0]) for seed in SEEDS]


def toggles(shown):
    return [i for i in range(1, len(shown)) if shown[i] != shown[i - 1]]


def most_toggles_in_a_minute(shown):
    t = toggles(shown)
    return max([sum(1 for x in t if s <= x < s + 60) for s in range(len(shown))] or [0])


def ratios(runs):
    return [r for run in runs for on, r in run if r is not None]


@pytest.mark.parametrize('sd', [5, 10, 15])
@pytest.mark.parametrize('steady', [False, True], ids=['from-start', 'steady'])
def test_slide_a_standing_phone_never_shows_a_time(ready, sd, steady):
    runs = slide(ready, sd, [[360 if steady else 300, 0]], steady)
    assert sum(on for run in runs for on, _ in run) == 0


def test_slide_a_walker_at_1_4_sd5_gets_a_steady_time_by_45_s(ready):
    runs = slide(ready, 5, [[300, 1.4]])
    for run in runs:
        shown = [on for on, _ in run]
        first = shown.index(True)
        assert first <= 45
        assert toggles(shown[first:]) == []
    assert all(0.5 <= r <= 1.5 for r in ratios(runs))


def test_slide_a_walker_at_1_4_sd10_toggles_at_most_twice(ready):
    runs = slide(ready, 10, [[300, 1.4]])
    for run in runs:
        assert len(toggles([on for on, _ in run])) <= 2


def test_slide_a_walker_at_1_4_sd10_within_the_accepted_tail(ready):
    # Measured: 18 of 5,319 shown seconds (0.3%) outside +-60%, mostly at seconds 37-51; range 0.60-2.31 x true.
    # Accepted (docs/v7.8-rulings.md, Accepted limits): at least 99% within +-60%, none below 0.4 x or beyond 2.5 x.
    r = ratios(slide(ready, 10, [[300, 1.4]]))
    assert sum(0.4 <= x <= 1.6 for x in r) >= 0.99 * len(r)
    assert all(0.4 <= x <= 2.5 for x in r)


def test_slide_a_walker_at_0_7_sd5_toggles_at_most_3_in_a_minute(ready):
    for run in slide(ready, 5, [[300, 0.7]]):
        assert most_toggles_in_a_minute([on for on, _ in run]) <= 3


def test_slide_a_walker_at_0_7_sd5_within_the_accepted_tail(ready):
    # Measured: 3 of 5,148 shown seconds (0.06%) outside +-60%; range 0.60-1.79 x true.
    # Accepted (docs/v7.8-rulings.md, Accepted limits): at least 99.5% within +-60%, none below 0.5 x or beyond 2.0 x.
    r = ratios(slide(ready, 5, [[300, 0.7]]))
    assert sum(0.4 <= x <= 1.6 for x in r) >= 0.995 * len(r)
    assert all(0.5 <= x <= 2.0 for x in r)


def gone_after(run, at):
    """Seconds after `at` until the last second a time showed (0 if none showed after it)."""
    shown = [on for on, _ in run]
    return max([i - at + 1 for i in range(at, len(shown)) if shown[i]] or [0])


def test_slide_a_walker_who_stops_dead_loses_the_time_within_60_s(ready):
    runs = slide(ready, 5, [[150, 1.4], [150, 0]])
    worst = max(gone_after(run, 150) for run in runs)
    assert all(any(on for on, _ in run[:150]) for run in runs)
    assert worst <= 60, worst


def test_slide_a_walker_who_turns_round_loses_the_time_within_45_s(ready):
    runs = slide(ready, 5, [[150, 1.4], [150, -1.4]])
    worst = max(gone_after(run, 150) for run in runs)
    assert worst <= 45, worst


def test_the_time_kept_by_hysteresis_goes_when_the_target_changes(page, app_url):
    target = time_boot(page, app_url)
    pts = []
    for k in range(120):        # a minute at 1.4 m/s, then a minute at 0.45 m/s, the newest fix 420 m short
        back = sum(1.4 if j < 60 else 0.45 for j in range(k + 1, 120))
        lat, lon = dest(*target, 180, 420 + back)
        pts.append({'lat': lat, 'lon': lon, 'acc': 5, 'ago': (119 - k) * 1000})
    page.evaluate('ps => { const now = Date.now(); ps.forEach(p => FK._test.fix({ lat: p.lat, lon: p.lon, acc: p.acc, t: now - p.ago })); }', pts)
    expect(page.locator('#nvTime')).to_have_text('about 16 min')     # 420 m at 0.45 m/s: kept, though it could not start
    ev(page, "t => FK.tac.setTarget({ type: 'point', lat: t[0], lon: t[1], name: 'Rally 1' })", list(target))
    expect(page.locator('#nvTime')).to_be_hidden()                   # the same target set again: the memory is reset


@pytest.mark.parametrize('m,v,want', [
    (420, 1.4, 'about 5 min'), (421.4, 1.4, 'about 6 min'), (50, 1.4, 'under 1 min'), (84, 1.4, 'about 1 min'),
    (85, 1.4, 'about 2 min'), (7200, 1, 'about 120 min'), (7201, 1, 'about 2 h 1 min'), (7500, 1, 'about 2 h 5 min'),
    (10800, 1, 'about 3 h'), (14399, 1, 'about 4 h'), (10860, 1, 'about 3 h 1 min')])
def test_time_text(ready, m, v, want):
    assert ev(ready, '([m, v]) => TNAV.timeText(m, v)', [m, v]) == want


@pytest.mark.parametrize('ms,want', [
    (0, ''), (30000, ''), (31000, 'Position is 31 s old'), (90000, 'Position is 90 s old'), (91000, 'Position is 2 min old'),
    (200000, 'Position is 3 min old'), (90 * 60000, 'Position is 90 min old'), (3 * 3600000, 'Position is 3 h old')])
def test_age_text(ready, ms, want):
    assert ev(ready, 'ms => TNAV.ageText(ms)', ms) == want


# ---------- The panel on Position ----------

def test_no_target_position_looks_as_before(page, app_url):
    boot(page, app_url, path='#/tactical/position')
    fix(page, *HOME)
    expect(page.locator('#navPanel')).to_be_hidden()
    expect(page.locator('#nvBackWrap')).to_be_hidden()
    assert ev(page, "document.querySelector('#wakeBtn').closest('#navPanel') === null")
    expect(page.locator('#wakeBtn')).to_be_visible()
    expect(page.locator('#tgtInfo')).to_have_count(0)


def test_marker_target_with_fix_and_heading(page, app_url):
    boot(page, app_url, [mk('a', 'Rally 1', *RALLY)], target='a', path='#/tactical/position')
    fix(page, *HOME)
    heading(page, 53)
    panel = page.locator('#navPanel')
    expect(panel).to_be_visible()
    expect(page.get_by_role('region', name='Navigation')).to_be_visible()
    expect(page.locator('#nvName')).to_have_text('Rally 1')
    expect(page.locator('#nvDist')).to_have_text('412 m')
    expect(page.locator('#nvBrg')).to_have_text('73° true')
    expect(page.locator('#nvTurn')).to_have_text('Turn 20° right')
    expect(page.locator('#nvArrow')).to_be_visible()
    assert abs(rotation(page) - 20) <= 1
    expect(page.locator('#nvNoCompass')).to_be_hidden()
    expect(page.locator('#nvStep')).to_be_hidden()
    expect(page.locator('#nvTime')).to_be_hidden()       # one fix: no pace
    box = page.locator('#nvArrow').bounding_box()
    assert box['width'] >= 96 and box['height'] >= 96
    assert float(ev(page, "getComputedStyle(document.querySelector('#nvDist')).fontSize")[:-2]) >= 40
    expect(page.locator('#tgtMark')).to_be_attached()
    assert ev(page, "!document.querySelector('#tgtMark').hasAttribute('hidden')")
    heading(page, 70)
    expect(page.locator('#nvTurn')).to_have_text('Straight ahead')
    heading(page, 93)
    expect(page.locator('#nvTurn')).to_have_text('Turn 20° left')


def test_arrow_shape_has_one_point_furthest_out(ready):
    """The arrow turns about the ring's centre (50, 50). Its tip must be the point furthest from there by at least 15% and the
    only sharp corner (every other interior angle at least 80 degrees), so the tail can't be read as the point at any angle."""
    d = ev(ready, "document.querySelector('#nvArrowG path').getAttribute('d')")
    assert ev(ready, "getComputedStyle(document.querySelector('#nvArrowG')).transformOrigin") == '50px 50px'
    nums = [float(x) for x in re.findall(r'-?\d+(?:\.\d+)?', d)]
    assert d.startswith('M') and d.endswith('Z') and set(re.sub(r'[\d.\s-]', '', d)) <= set('MLZ')
    pts = list(zip(nums[0::2], nums[1::2]))
    n = len(pts)
    far = [math.hypot(x - 50, y - 50) for x, y in pts]
    tip = max(range(n), key=lambda i: far[i])
    assert pts[tip] == (50, 6)
    assert all(far[tip] >= 1.15 * far[i] for i in range(n) if i != tip)
    area = sum(pts[i][0] * pts[(i + 1) % n][1] - pts[(i + 1) % n][0] * pts[i][1] for i in range(n))
    for i, v in enumerate(pts):
        p, q = pts[i - 1], pts[(i + 1) % n]
        a, b = (p[0] - v[0], p[1] - v[1]), (q[0] - v[0], q[1] - v[1])
        th = math.degrees(math.acos((a[0] * b[0] + a[1] * b[1]) / math.hypot(*a) / math.hypot(*b)))
        convex = ((v[0] - p[0]) * (q[1] - v[1]) - (v[1] - p[1]) * (q[0] - v[0]) > 0) == (area > 0)
        inner = th if convex else 360 - th
        if i != tip:
            assert inner >= 80, (v, inner)
    # A head at least twice as wide as the shaft.
    xs_head = [x for x, y in pts if y < 50]
    xs_shaft = [x for x, y in pts if y > 60]
    assert max(xs_head) - min(xs_head) >= 2 * (max(xs_shaft) - min(xs_shaft))


def test_arrow_takes_the_short_way_across_north(page, app_url):
    boot(page, app_url, [mk('a', 'Rally 1', *RALLY)], target='a', path='#/tactical/position')
    fix(page, *HOME)
    heading(page, 63)
    assert abs(rotation(page) - 10) <= 1
    heading(page, 83)
    assert abs(rotation(page) + 10) <= 1                  # -10, not 350
    heading(page, 253)
    r = rotation(page)
    assert abs(abs(r) - 180) <= 1
    heading(page, 63)
    assert abs(rotation(page) - 10) <= 1 or abs(rotation(page) - (10 - 360)) <= 1 or abs(rotation(page) - 370) <= 1


def test_no_heading_shows_the_bearing_as_a_number(page, app_url):
    boot(page, app_url, [mk('a', 'Rally 1', *RALLY)], target='a', path='#/tactical/position')
    fix(page, *HOME)
    expect(page.locator('#nvDist')).to_have_text('412 m')
    expect(page.locator('#nvBrg')).to_have_text('73° true')
    expect(page.locator('#nvArrow')).to_be_hidden()
    expect(page.locator('#nvNoCompass')).to_have_text('No compass: bearing shown as a number')
    expect(page.locator('#nvTurn')).to_be_hidden()


def test_no_fix_waits_for_a_position(page, app_url):
    boot(page, app_url, [mk('a', 'Rally 1', *RALLY)], target='a', path='#/tactical/position')
    heading(page, 53)
    expect(page.locator('#nvName')).to_have_text('Rally 1')
    expect(page.locator('#nvWait')).to_have_text('Waiting for a position')
    for sel in ('#nvDist', '#nvBrg', '#nvArrow', '#nvTurn', '#nvTime', '#nvEnd', '#nvNoCompass', '#nvAge'):
        expect(page.locator(sel)).to_be_hidden()
    expect(page.locator('#nvStop')).to_be_visible()
    fix(page, *HOME)
    expect(page.locator('#nvWait')).to_be_hidden()
    expect(page.locator('#nvDist')).to_have_text('412 m')


def test_old_position_is_said_and_ticks(page, app_url):
    boot(page, app_url, [mk('a', 'Rally 1', *RALLY)], target='a', path='#/tactical/position')
    fix(page, *HOME, ago=25000)
    expect(page.locator('#nvDist')).to_have_text('412 m')
    expect(page.locator('#nvAge')).to_be_hidden()
    page.clock.fast_forward(10000)
    expect(page.locator('#nvAge')).to_have_text(re.compile(r'^Position is 3[5-7] s old$'))
    page.clock.fast_forward(200000)
    expect(page.locator('#nvAge')).to_have_text(re.compile(r'^Position is [34] min old$'))
    fix(page, *HOME)
    expect(page.locator('#nvAge')).to_be_hidden()


def test_marker_arrival_keeps_the_target(page, app_url):
    near = dest(*HOME, 73, 10)
    boot(page, app_url, [mk('a', 'Rally 1', *near)], target='a', path='#/tactical/position')
    fix(page, *HOME)
    expect(page.locator('#nvArrived')).to_have_text('Arrived')
    expect(page.locator('#nvDist')).to_have_text('10 m')
    assert ev(page, 'FK.tac.target()') == {'type': 'marker', 'id': 'a'}
    far = dest(*near, 253, 35)      # 35 m short
    fix(page, *far, acc=5)
    expect(page.locator('#nvArrived')).to_be_hidden()
    fix(page, *far, acc=40)         # radius 40
    expect(page.locator('#nvArrived')).to_have_text('Arrived')
    far = dest(*near, 253, 45)
    fix(page, *far, acc=200)        # radius capped at 50
    expect(page.locator('#nvArrived')).to_have_text('Arrived')
    far = dest(*near, 253, 60)
    fix(page, *far, acc=200)
    expect(page.locator('#nvArrived')).to_be_hidden()
    expect(page.locator('#nvDist')).to_have_text('60 m')
    assert ev(page, 'FK.tac.target()') == {'type': 'marker', 'id': 'a'}


def test_arrived_hides_the_arrow_and_turn_line(page, app_url):
    near = dest(*HOME, 73, 10)
    boot(page, app_url, [mk('a', 'Rally 1', *near)], target='a', path='#/tactical/position')
    fix(page, *dest(*near, 253, 40))
    heading(page, 53)
    expect(page.locator('#nvArrow')).to_be_visible()
    expect(page.locator('#nvTurn')).to_have_text('Turn 20° right')
    fix(page, *HOME)
    expect(page.locator('#nvArrived')).to_have_text('Arrived')
    expect(page.locator('#nvArrow')).to_be_hidden()
    expect(page.locator('#nvTurn')).to_be_hidden()
    expect(page.locator('#nvDist')).to_have_text('10 m')
    expect(page.locator('#nvBrg')).to_have_text('73° true')
    page.clock.fast_forward(6000)
    expect(page.locator('#nvLive')).to_have_text('Arrived. 10 m, 73° true')


def test_an_old_position_never_arrives_or_advances(page, app_url):
    near = dest(*HOME, 73, 10)
    boot(page, app_url, [mk('a', 'Rally 1', *near)], shapes=[ROUTE], target='a', path='#/tactical/position')
    fix(page, *HOME, ago=45000)
    expect(page.locator('#nvAge')).to_have_text('Position is 45 s old')
    expect(page.locator('#nvArrived')).to_be_hidden()
    fix(page, *HOME)
    expect(page.locator('#nvArrived')).to_have_text('Arrived')
    page.clock.fast_forward(31000)                     # the same fix grows old: Arrived goes
    expect(page.locator('#nvArrived')).to_be_hidden()
    ev(page, "FK.tac.setTarget({ type: 'route', id: 'r1', i: 0 })")
    fix(page, *dest(*HOME, 180, 10), ago=31000)        # within 25 m of point 1, but 31 s old
    page.wait_for_timeout(50)
    assert ev(page, 'FK.tac.target().i') == 0
    expect(page.locator('#nvStepText')).to_have_text('Point 1 of 3')
    fix(page, *dest(*HOME, 180, 10))
    expect(page.locator('#nvStepText')).to_have_text('Point 2 of 3')


# ---------- Time to go ----------

def time_boot(page, app_url):
    boot(page, app_url, path='#/tactical/position')
    target = dest(*HOME, 0, 1000)
    ev(page, "t => FK.tac.setTarget({ type: 'point', lat: t[0], lon: t[1], name: 'Rally 1' })", list(target))
    return target


def test_time_to_go_at_walking_pace(page, app_url):
    target = time_boot(page, app_url)
    walk(page, target)
    expect(page.locator('#nvDist')).to_have_text('420 m')
    expect(page.locator('#nvTime')).to_have_text('about 5 min')


@pytest.mark.parametrize('case', ['slow', 'stationary3', 'stationary8', 'hole', 'away', 'across', 'acc80'])
def test_time_to_go_hidden(page, app_url, case):
    target = time_boot(page, app_url)
    kw = {'slow': {'speed': 0.2}, 'stationary3': {'speed': 0, 'jitter': 3, 'seed': 7}, 'stationary8': {'speed': 0, 'jitter': 8, 'seed': 7},
          'hole': {'skip': (10, 50)}, 'away': {'mode': 'away'}, 'across': {'mode': 'across'}, 'acc80': {'acc': 80}}[case]
    walk(page, target, **kw)
    expect(page.locator('#nvDist')).to_be_visible()
    page.wait_for_timeout(50)
    expect(page.locator('#nvTime')).to_be_hidden()


def test_time_to_go_with_a_gps_jump(page, app_url):
    target = time_boot(page, app_url)
    walk(page, target, wild=30)                       # a 200 m jump in the middle of the minute
    expect(page.locator('#nvDist')).to_have_text('420 m')
    expect(page.locator('#nvTime')).to_have_text('about 5 min')
    page.clock.fast_forward(61000)
    # The jump is the newest fix: the pace (median of the newest three) is still 1.4 m/s, but the distance shown is from the
    # jumped fix, 200 m east: sqrt(420^2 + 200^2) = 465 m, 332 s, so about 6 min. Never under 1 min.
    walk(page, target, wild=59)
    expect(page.locator('#nvDist')).to_have_text('465 m')
    expect(page.locator('#nvTime')).to_have_text('about 6 min')


def test_time_to_go_needs_six_fixes_closing_30_m(page, app_url):
    target = time_boot(page, app_url)
    walk(page, target, n=3, step_ms=10000)
    expect(page.locator('#nvDist')).to_have_text('420 m')
    page.wait_for_timeout(50)
    expect(page.locator('#nvTime')).to_be_hidden()
    page.clock.fast_forward(61000)
    walk(page, target, n=6, step_ms=7500)
    expect(page.locator('#nvTime')).to_have_text('about 5 min')


def test_newest_fix_jumped_toward_the_target_with_six_fixes(page, app_url):
    target = time_boot(page, app_url)
    # The distance shown is from the jumped fix (220 m, the accepted cost of trusting the phone); the jump widens the scatter
    # so no time shows at all, and never under 1 min.
    walk(page, target, n=6, step_ms=7500, wild=5, wild_brg=0)
    expect(page.locator('#nvDist')).to_have_text('220 m')
    page.wait_for_timeout(50)
    expect(page.locator('#nvTime')).to_be_hidden()


def test_no_time_when_the_position_is_old(page, app_url):
    target = time_boot(page, app_url)
    walk(page, target)
    expect(page.locator('#nvTime')).to_have_text('about 5 min')
    page.clock.fast_forward(31000)
    expect(page.locator('#nvAge')).to_be_visible()
    expect(page.locator('#nvTime')).to_be_hidden()


# ---------- Routes ----------

def test_route_stepping_and_arrival(page, app_url):
    boot(page, app_url, shapes=[ROUTE], target={'type': 'route', 'id': 'r1', 'i': 0}, path='#/tactical/position')
    step, prev, nxt = page.locator('#nvStepText'), page.locator('#nvPrev'), page.locator('#nvNext')
    expect(page.locator('#nvName')).to_have_text('Ridge walk')
    expect(step).to_have_text('Point 1 of 3')
    expect(prev).to_be_disabled()
    expect(nxt).to_be_enabled()
    for b in (prev, nxt):
        bb = b.bounding_box()
        assert bb['width'] >= 48 and bb['height'] >= 48
    start = dest(*HOME, 180, 100)
    fix(page, *start)                                  # 100 m from point 1: stays
    expect(step).to_have_text('Point 1 of 3')
    expect(page.locator('#nvDist')).to_have_text('100 m')
    want_end = ev(page, """([f, pts]) => TGEOM.fmtDist(GEO.distance(f[0], f[1], pts[0][0], pts[0][1]) + TGEOM.pathLength(pts), 'metric')""",
                  [list(start), ROUTE['pts']])
    expect(page.locator('#nvEnd')).to_have_text(f'{want_end} to the end')
    assert want_end == '700 m'
    fix(page, *dest(*HOME, 180, 20))                   # within 25 m: advances
    expect(step).to_have_text('Point 2 of 3')
    assert ev(page, 'FK.tac.target()') == {'type': 'route', 'id': 'r1', 'i': 1}
    fix(page, *dest(*P1, 180, 45), acc=40)              # 45 m with accuracy 40: stays
    expect(step).to_have_text('Point 2 of 3')
    fix(page, *dest(*P1, 180, 10), acc=500)             # 10 m but accuracy 500: never advances
    expect(step).to_have_text('Point 2 of 3')
    fix(page, *dest(*P1, 180, 38), acc=40)              # 38 m with accuracy 40: advances
    expect(step).to_have_text('Point 3 of 3')
    expect(nxt).to_be_disabled()
    expect(prev).to_be_enabled()
    expect(page.locator('#nvEnd')).to_be_hidden()       # the current point is the end
    fix(page, *dest(*P2, 270, 20))
    expect(page.locator('#nvArrived')).to_have_text('Arrived')
    expect(page.locator('#nvDist')).to_have_text('20 m')
    expect(step).to_have_text('Point 3 of 3')
    fix(page, *dest(*P2, 270, 10))
    assert ev(page, 'FK.tac.target()') == {'type': 'route', 'id': 'r1', 'i': 2}
    prev.click()
    expect(step).to_have_text('Point 2 of 3')
    expect(page.locator('#nvArrived')).to_be_hidden()
    prev.click()
    expect(step).to_have_text('Point 1 of 3')
    expect(prev).to_be_disabled()
    prev.click(force=True)
    expect(step).to_have_text('Point 1 of 3')
    nxt.click()
    nxt.click()
    expect(step).to_have_text('Point 3 of 3')
    nxt.click(force=True)
    expect(step).to_have_text('Point 3 of 3')
    assert ev(page, 'FK.tac.target()') == {'type': 'route', 'id': 'r1', 'i': 2}
    page.click('#nvStop')
    expect(page.locator('#navPanel')).to_be_hidden()
    assert ev(page, 'FK.tac.target()') is None


def test_close_points_advance_one_per_fix(page, app_url):
    pts = [list(dest(*HOME, b, 8)) for b in (0, 72, 144, 216, 288)]    # five points all within 20 m of each other
    boot(page, app_url, shapes=[{**ROUTE, 'pts': pts}], target={'type': 'route', 'id': 'r1', 'i': 0}, path='#/tactical/position')
    for i in range(1, 5):
        fix(page, *HOME)
        page.wait_for_timeout(50)
        assert ev(page, 'FK.tac.target().i') == i
    fix(page, *HOME)
    assert ev(page, 'FK.tac.target().i') == 4
    expect(page.locator('#nvArrived')).to_have_text('Arrived')


def test_a_later_point_in_range_does_not_skip_ahead(page, app_url):
    boot(page, app_url, shapes=[ROUTE], target={'type': 'route', 'id': 'r1', 'i': 0}, path='#/tactical/position')
    fix(page, *P1)                                       # standing on point 2 while point 1 is the target
    page.wait_for_timeout(50)
    assert ev(page, 'FK.tac.target().i') == 0
    expect(page.locator('#nvStepText')).to_have_text('Point 1 of 3')


def test_route_time_is_to_the_current_point_and_the_end_has_no_time(page, app_url):
    far = dest(*HOME, 0, 2000)
    route = {**ROUTE, 'pts': [list(dest(*HOME, 0, 1000)), list(far)]}
    boot(page, app_url, shapes=[route], target={'type': 'route', 'id': 'r1', 'i': 0}, path='#/tactical/position')
    walk(page, route['pts'][0])
    expect(page.locator('#nvDist')).to_have_text('420 m')
    expect(page.locator('#nvTime')).to_have_text('about 5 min')
    expect(page.locator('#nvEnd')).to_have_text('1.42 km to the end')


# ---------- GPS while navigating ----------

def test_gps_keeps_running_in_every_tab_while_a_target_is_set(page, app_url):
    page.add_init_script(GPS_STUB)
    boot(page, app_url, [mk('a', 'Rally 1', *RALLY)])
    watches_become(page, 1)
    go(page, '/emergency')
    watches_become(page, 0)
    ev(page, "FK.tac.setTarget({ type: 'marker', id: 'a' })")
    watches_become(page, 1)
    go(page, '/survival')
    page.wait_for_function("location.hash.startsWith('#/survival')")
    watches_become(page, 1)
    go(page, '/tactical/ballistics')
    page.wait_for_function("FK.view() === 'ballistics'")
    watches_become(page, 1)
    go(page, '/emergency')
    page.wait_for_function("location.hash.startsWith('#/emergency')")
    watches_become(page, 1)
    ev(page, 'FK.tac.setTarget(null)')
    watches_become(page, 0)
    go(page, '/tactical/position')
    watches_become(page, 1)
    ev(page, "FK.tac.setTarget({ type: 'marker', id: 'a' })")
    ev(page, 'FK.tac.setTarget(null)')
    page.wait_for_timeout(50)
    watches_become(page, 1)                              # Position is showing: GPS stays on
    assert page.evaluate('window.__watch - window.__clear') == 1


def test_gps_on_at_boot_in_another_tab_with_a_stored_target(page, app_url):
    page.add_init_script(GPS_STUB)
    page.clock.install(time=NOW / 1000)
    store(page, wps=[mk('a', 'Rally 1', *RALLY)], target='a', advAck=True)
    page.goto(app_url + '#/emergency')
    page.wait_for_function('window.FK && FK.sheet && FK.tac')
    watches_become(page, 1)


# ---------- Back to start ----------

def test_back_to_start_only_while_recording_with_a_point(page, app_url):
    page.add_init_script(WAKE_STUB)
    boot(page, app_url)
    position(page)
    expect(page.locator('#nvBack')).to_be_hidden()
    go(page, '/tactical/map')
    page.wait_for_function("FK.view() === 'map'")
    open_track(page)
    expect(page.locator('#trkBack')).to_be_hidden()
    page.click('#trkToggle')
    expect(page.locator('#trkToggle')).to_have_text('Stop recording')
    expect(page.locator('#trkBack')).to_be_hidden()      # recording, no point yet
    fix(page, *HOME)
    expect(page.locator('#trkBack')).to_be_visible()
    expect(page.locator('#trkBack')).to_have_text('Back to start')
    page.click('#trkClose')
    position(page)
    expect(page.locator('#nvBack')).to_be_visible()
    expect(page.locator('#navPanel')).to_be_hidden()
    fix(page, *dest(*HOME, 90, 200))
    page.click('#nvBack')
    t = ev(page, 'FK.tac.target()')
    assert t['type'] == 'point' and t['name'] == 'Start'
    assert abs(t['lat'] - HOME[0]) < 1e-6 and abs(t['lon'] - HOME[1]) < 1e-6
    expect(page.locator('#nvName')).to_have_text('Start')
    expect(page.locator('#nvDist')).to_have_text('200 m')
    expect(page.locator('#nvBrg')).to_have_text('270° true')
    ev(page, "FK.tac.setTarget(null)")
    go(page, '/tactical/map')
    page.wait_for_function("FK.view() === 'map'")
    open_track(page)
    page.click('#trkBack')
    expect(page.locator('#dlgTrack')).to_be_hidden()
    assert ev(page, 'FK.tac.target().name') == 'Start'
    open_track(page)
    page.click('#trkToggle')
    expect(page.locator('#trkBack')).to_be_hidden()
    page.click('#trkClose')
    position(page)
    expect(page.locator('#nvBack')).to_be_hidden()


# ---------- Map strip ----------

def test_strip_on_the_map(page, app_url):
    boot(page, app_url, [mk('a', 'Rally 1', *RALLY)], shapes=[ROUTE])
    strip = page.locator('#navStrip')
    expect(strip).to_be_hidden()
    ev(page, "FK.tac.setTarget({ type: 'marker', id: 'a' })")
    expect(strip).to_be_visible()
    expect(strip).to_contain_text('Rally 1')
    expect(strip).to_contain_text('waiting for a position')
    fix(page, *HOME)
    expect(page.locator('#nsName')).to_have_text('Rally 1')
    expect(page.locator('#nsDist')).to_have_text('412 m')
    expect(page.locator('#nsBrg')).to_have_text('73°')
    expect(page.locator('#nsStep')).to_be_hidden()
    bb = strip.bounding_box()
    assert bb['height'] >= 44
    # Not over the crosshair, the map buttons or the layer chip.
    cross = page.locator('.cross').bounding_box()
    ctl = page.locator('.mapctl').bounding_box()
    chip = page.locator('#mLayerName').bounding_box()
    assert bb['y'] + bb['height'] <= cross['y']
    assert bb['x'] + bb['width'] <= ctl['x']
    assert bb['y'] >= chip['y'] + chip['height']
    assert bb['x'] >= 0
    ev(page, "FK.tac.setTarget({ type: 'route', id: 'r1', i: 1 })")
    expect(page.locator('#nsStep')).to_have_text('2/3')
    expect(page.locator('#nsName')).to_have_text('Ridge walk')
    ev(page, "FK.mapTools.start('measure')")
    expect(strip).to_be_hidden()
    ev(page, 'FK.mapTools.cancel()')
    expect(strip).to_be_visible()
    strip.click()
    page.wait_for_function("FK.view() === 'position' && location.hash === '#/tactical/position'")
    expect(page.locator('#navPanel')).to_be_visible()


def test_strip_says_when_the_position_is_old(page, app_url):
    boot(page, app_url, [mk('a', 'Rally 1', *RALLY)], target='a')
    strip, dist, rest = page.locator('#navStrip'), page.locator('#nsDist'), page.locator('#nsRest')
    expect(page.locator('#nsWait')).to_have_text('waiting for a position')
    expect(dist).to_be_hidden()
    fix(page, *HOME, ago=45000)
    expect(dist).to_have_text('412 m, 45 s old')
    expect(rest).to_have_class('old')
    expect(page.locator('#nsWait')).to_be_hidden()
    assert ev(page, "getComputedStyle(document.querySelector('#nsDist')).color") != ev(page, "getComputedStyle(document.querySelector('#nsName')).color")
    expect(strip).to_have_attribute('aria-label', 'Rally 1: 412 m at 73° true, from a position 45 s old. Open Position.')
    page.clock.fast_forward(160000)                   # the timer keeps it current: 205 s
    expect(dist).to_have_text('412 m, 3 min old')
    fix(page, *HOME)
    expect(dist).to_have_text('412 m')
    expect(rest).not_to_have_class('old')
    expect(strip).to_have_attribute('aria-label', 'Rally 1: 412 m at 73° true. Open Position.')


def test_strip_reads_bearing_then_distance_and_short_names_fit(page, app_url):
    boot(page, app_url, [mk('a', 'Rally 1', *RALLY), mk('b', 'North ridge rally point by the old fire tower', *RALLY)], target='a')
    fits = "(() => { const e = document.querySelector('#nsName'); return e.scrollWidth <= e.clientWidth; })()"
    expect(page.locator('#nsWait')).to_be_visible()
    assert ev(page, fits)                              # "Rally 1  waiting for a position" fits at 360 px
    fix(page, *HOME, ago=45000)
    order = ev(page, "['nsName', 'nsBrg', 'nsDist'].map(id => document.getElementById(id).getBoundingClientRect().left)")
    assert order == sorted(order)
    assert [txt(page, s) for s in ('#nsName', '#nsBrg', '#nsDist')] == ['Rally 1', '73°', '412 m, 45 s old']
    ev(page, "FK.tac.setTarget({ type: 'marker', id: 'b' })")
    assert not ev(page, fits)                          # a long name is cut off with an ellipsis
    assert ev(page, "getComputedStyle(document.querySelector('#nsName')).textOverflow") == 'ellipsis'
    for sel in ('#nsBrg', '#nsDist'):
        b = page.locator(sel).bounding_box()
        assert b['x'] + b['width'] <= page.locator('#navStrip').bounding_box()['x'] + page.locator('#navStrip').bounding_box()['width']


@pytest.mark.parametrize('big', [False, True], ids=['normal-text', 'large-text'])
def test_map_note_sits_below_the_chips_and_strip(page, app_url, big):
    # Field Kit has no text-size setting of its own; 22 px in the stack stands in for the phone's system text scaling,
    # which Playwright can't emulate (accepted by the controller in review round 1).
    page.add_init_script(WAKE_STUB)
    if big:   # the phone's text size turned up: every px size in the stack 1.5 times
        page.add_init_script("""document.addEventListener('DOMContentLoaded', () => { const s = document.createElement('style');
          s.textContent = '.maptag span, .maptag button, #navStrip span { font-size: 22px !important; }'; document.head.appendChild(s); })""")
    page.clock.install(time=NOW / 1000)
    page.goto('about:blank')
    store(page, wps=[mk('a', 'North ridge rally point by the old fire tower', *RALLY)], target='a', recording=True, advAck=True,
          mapView={'lat': HOME[0], 'lon': HOME[1], 'z': 15}, mapFollow=False)
    open_map(page, app_url)   # tiles are not served here, so the "not loading" note shows
    fix(page, *HOME, ago=45000)
    expect(page.locator('#mapNote')).to_be_visible()
    expect(page.locator('#recChip')).to_be_visible()
    expect(page.locator('#navStrip')).to_be_visible()
    page.wait_for_timeout(100)
    note = page.locator('#mapNote').bounding_box()
    for sel in ('#mLayerName', '#recChip', '#navStrip'):
        b = page.locator(sel).bounding_box()
        assert b['y'] + b['height'] <= note['y'], sel
    ev(page, 'FK.tac.setTarget(null)')
    page.wait_for_timeout(100)
    rec = page.locator('#recChip').bounding_box()
    assert rec['y'] + rec['height'] <= page.locator('#mapNote').bounding_box()['y']


def test_hiding_the_page_stops_gps_and_showing_it_restarts(page, app_url):
    page.add_init_script(GPS_STUB)
    boot(page, app_url, [mk('a', 'Rally 1', *RALLY)], target='a')
    go(page, '/emergency')
    page.wait_for_function("location.hash.startsWith('#/emergency')")
    watches_become(page, 1)
    hide = "h => { Object.defineProperty(document, 'hidden', { configurable: true, get: () => h }); document.dispatchEvent(new Event('visibilitychange')); }"
    ev(page, hide, True)
    watches_become(page, 0)
    assert ev(page, 'FK.nav.ticking()') is False
    ev(page, hide, False)
    watches_become(page, 1)
    assert ev(page, 'FK.nav.ticking()') is True
    assert ev(page, 'window.__watch') == 2 and ev(page, 'window.__clear') == 1


# ---------- Stop, everywhere ----------

def test_stop_in_the_panel_clears_everything(page, app_url):
    boot(page, app_url, [mk('a', 'Rally 1', *RALLY)], target='a')
    fix(page, *HOME)
    expect(page.locator('#navStrip')).to_be_visible()
    position(page)
    page.click('#nvStop')
    expect(page.locator('#navPanel')).to_be_hidden()
    expect(page.locator('#navStrip')).to_be_hidden()
    assert ev(page, 'FK.tac.target()') is None
    assert ev(page, "document.querySelector('#tgtMark').hasAttribute('hidden')")


def test_stop_in_the_marker_sheet_and_the_shape_sheet(page, app_url):
    from .test_markers import open_marker
    from .test_map_tools import tap_route, ROUTE as MT_ROUTE, HOME as MT_HOME
    boot(page, app_url, [mk('w1', 'Camp', *dest(*MT_HOME, 200, 150))], shapes=[MT_ROUTE], view=MT_HOME, target='w1')
    fix(page, *MT_HOME)
    expect(page.locator('#navStrip')).to_be_visible()
    open_marker(page, 'w1')
    expect(page.locator('#mkGo')).to_have_text('Stop')
    page.click('#mkGo')
    expect(page.locator('#navStrip')).to_be_hidden()
    ev(page, "FK.tac.setTarget({ type: 'route', id: 's1', i: 0 })")
    expect(page.locator('#navStrip')).to_be_visible()
    tap_route(page)
    expect(page.locator('#shWalk')).to_have_text('Stop walking')
    page.click('#shWalk')
    expect(page.locator('#navStrip')).to_be_hidden()
    position(page)
    expect(page.locator('#navPanel')).to_be_hidden()


# ---------- Keep screen on, redraws, live text, the timer ----------

def test_keep_screen_on_sits_in_the_panel_and_works(page, app_url):
    page.add_init_script(WAKE_STUB)
    boot(page, app_url, [mk('a', 'Rally 1', *RALLY)], path='#/tactical/position')
    home = ev(page, "document.querySelector('#wakeBtn').parentElement.id || document.querySelector('#wakeBtn').parentElement.tagName")
    ev(page, "FK.tac.setTarget({ type: 'marker', id: 'a' })")
    wake = page.locator('#navPanel #wakeBtn')
    expect(wake).to_be_visible()
    expect(page.locator('#wakeBtn')).to_have_count(1)
    expect(wake).to_have_text('Keep screen on')
    wake.click()
    expect(wake).to_have_attribute('aria-pressed', 'true')
    expect(wake).to_have_text('Screen stays on')
    assert ev(page, 'FK.wakeOn()') is True
    page.click('#nvStop')
    expect(page.locator('#wakeBtn')).to_be_visible()
    assert ev(page, "document.querySelector('#wakeBtn').closest('#navPanel') === null")
    assert ev(page, "document.querySelector('#wakeBtn').parentElement.id || document.querySelector('#wakeBtn').parentElement.tagName") == home
    expect(page.locator('#wakeBtn')).to_have_attribute('aria-pressed', 'true')
    page.click('#wakeBtn')
    expect(page.locator('#wakeBtn')).to_have_text('Keep screen on')
    assert ev(page, 'FK.wakeOn()') is False


def test_redraws_keep_the_buttons_and_focus(page, app_url):
    boot(page, app_url, shapes=[ROUTE], target={'type': 'route', 'id': 'r1', 'i': 1}, path='#/tactical/position')
    ev(page, "window.__btns = ['#nvPrev', '#nvNext', '#nvStop', '#wakeBtn'].map(s => document.querySelector(s))")
    page.focus('#nvNext')
    for k in range(5):
        fix(page, *dest(*HOME, 180, 100 + k))
        heading(page, 10 * k)
    ev(page, "FK.tac.setUnit('us')")
    page.clock.fast_forward(3000)
    assert ev(page, "window.__btns.every((b, i) => b === document.querySelector(['#nvPrev', '#nvNext', '#nvStop', '#wakeBtn'][i]) && b.isConnected)")
    assert ev(page, 'document.activeElement.id') == 'nvNext'
    page.keyboard.press('Enter')
    expect(page.locator('#nvStepText')).to_have_text('Point 3 of 3')
    assert ev(page, 'document.activeElement.id') == 'nvNext'   # still focused at the end (marked disabled, not removed from focus)
    expect(page.locator('#nvNext')).to_be_disabled()


def test_live_text_at_most_every_five_seconds(page, app_url):
    boot(page, app_url, [mk('a', 'Rally 1', *RALLY)], target='a', path='#/tactical/position')
    live = page.locator('#nvLive')
    assert ev(page, "document.querySelector('#nvLive').getAttribute('aria-live')") == 'polite'
    fix(page, *HOME)
    heading(page, 53)
    page.clock.fast_forward(6000)
    expect(live).to_have_text('412 m, 73° true. Turn 20° right')
    fix(page, *dest(*HOME, 73, 12))
    expect(page.locator('#nvDist')).to_have_text('400 m')
    expect(live).to_have_text('412 m, 73° true. Turn 20° right')     # visible text moved; the spoken one waits
    page.clock.fast_forward(6000)
    expect(live).to_have_text(re.compile(r'^400 m, 73° true\. Turn 2\d° right$'))


def test_one_timer_runs_only_while_a_target_is_set_and_the_page_shows(page, app_url):
    boot(page, app_url, [mk('a', 'Rally 1', *RALLY)], path='#/tactical/position')
    assert ev(page, 'FK.nav.ticking()') is False
    ev(page, "FK.tac.setTarget({ type: 'marker', id: 'a' })")
    assert ev(page, 'FK.nav.ticking()') is True
    ev(page, "FK.tac.setTarget({ type: 'marker', id: 'a' })")
    assert ev(page, 'FK.nav.ticking()') is True
    ev(page, "Object.defineProperty(document, 'hidden', { configurable: true, get: () => true }); document.dispatchEvent(new Event('visibilitychange'))")
    assert ev(page, 'FK.nav.ticking()') is False
    ev(page, "Object.defineProperty(document, 'hidden', { configurable: true, get: () => false }); document.dispatchEvent(new Event('visibilitychange'))")
    assert ev(page, 'FK.nav.ticking()') is True
    ev(page, 'FK.tac.setTarget(null)')
    assert ev(page, 'FK.nav.ticking()') is False


def test_names_are_text_not_markup(page, app_url):
    evil = '<img src=x onerror=window.x=1>'
    boot(page, app_url, [mk('a', evil, *RALLY)], target='a', path='#/tactical/position')
    fix(page, *HOME)
    expect(page.locator('#nvName')).to_have_text(evil)
    expect(page.locator('#nsName')).to_have_text(evil)
    assert ev(page, 'window.x') is None


def test_us_units(page, app_url):
    boot(page, app_url, [mk('a', 'Rally 1', *RALLY)], target='a', distUnit='us', path='#/tactical/position')
    fix(page, *HOME)
    expect(page.locator('#nvDist')).to_have_text('451 yd')
    ev(page, "FK.tac.setUnit('metric')")
    expect(page.locator('#nvDist')).to_have_text('412 m')
