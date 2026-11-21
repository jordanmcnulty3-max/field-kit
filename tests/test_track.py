"""Track recording additions: elapsed time and average moving speed. (No climb figure: phone GPS altitude is too noisy, see docs/v7.8-rulings.md.)

(tests/test_tools.py is the Emergency tools' file; the Track dialog belongs to the Tactical map.)"""
import pytest
from playwright.sync_api import expect

from .tac import store, open_map, open_track

T0 = 1_800_000_000_000
LAT0, LON0 = 43.0, -76.0
STEP = 0.00003            # degrees of latitude: about 3.34 m
M_PER_DEG = 6371008.8 * 3.141592653589793 / 180
FT = 3.28084


def pt(i, alt=None, t=None, lat=None):
    return [round(LAT0 + STEP * i if lat is None else lat, 6), LON0, alt, T0 + 1000 * i if t is None else t]


def info(page):
    return page.locator('#trkInfo').inner_text()


def stats(page, track):
    return page.evaluate('t => TGEOM.trackStats(t)', track)


@pytest.fixture
def ready(page, app_url):
    page.goto(app_url)
    page.wait_for_function('window.FK && typeof TGEOM !== "undefined"')
    return page


# ---------- trackStats (pure) ----------

def test_stats_empty_and_single_point(ready):
    assert stats(ready, []) == {'dist': 0, 'elapsedMs': 0, 'movingMs': 0, 'movingDist': 0}
    assert stats(ready, [pt(0, 100)]) == {'dist': 0, 'elapsedMs': 0, 'movingMs': 0, 'movingDist': 0}


def test_stats_distance_elapsed_and_moving(ready):
    s = stats(ready, [pt(i) for i in range(11)])
    assert s['elapsedMs'] == 10000 and s['movingMs'] == 10000
    assert abs(s['dist'] - 10 * STEP * M_PER_DEG) < 0.5


def test_stats_a_leg_is_moving_by_its_own_speed_up_to_a_10_minute_gap(ready):
    # v7.8 follow-up F2: a leg moves when it covers at least 0.3 m/s and its gap is at most 10 min
    m = lambda metres: LAT0 + metres / M_PER_DEG
    t = [pt(0, t=T0, lat=m(0)),
         pt(0, t=T0 + 60000, lat=m(60)),               # 60 m in 60 s: moving
         pt(0, t=T0 + 120000, lat=m(70)),              # 10 m in 60 s (0.17 m/s): a pause
         pt(0, t=T0 + 720000, lat=m(370)),             # 300 m in 600 s (0.5 m/s, gap exactly 10 min): moving
         pt(0, t=T0 + 1320001, lat=m(1370))]           # gap over 10 min: a pause whatever its speed
    s = stats(ready, t)
    assert s['elapsedMs'] == 1320001 and s['movingMs'] == 660000














# ---------- the screen ----------

def test_info_with_pace(page, app_url):
    alts = [100 + 50 * i / 19 for i in range(20)]       # clean, steadily rising altitude on every point
    tr = [[round(LAT0 + 0.00018 * i, 6), LON0, a, T0 + 10000 * i] for i, a in enumerate(alts)]
    store(page, track=tr)
    open_map(page, app_url)
    open_track(page)
    d = page.evaluate('t => TGEOM.fmtDist(TGEOM.trackStats(t).dist, FK.tac.unit())', tr)
    # 19 steps of 20 m in 190 s: 380 m / 190 s = 2.0 m/s = 4.5 mph
    text = info(page)
    assert text == f'{d} over 3 min, 20 points. Moving average 4.5 mph.'
    assert 'Climb' not in text and ' ft' not in text


def test_info_pause_is_not_moving_time(page, app_url):
    first = [pt(i) for i in range(10)]
    second = [pt(8 + i, t=T0 + 9000 + 300000 + 1000 * i) for i in range(1, 11)]
    store(page, track=first + second)
    open_map(page, app_url)
    open_track(page)
    # the user stood still through the pause: 18 steps in 18 s of moving time, 3.336 m/s = 7.5 mph
    mph = 18 * STEP * M_PER_DEG / 18 / 0.44704
    d = page.evaluate('t => TGEOM.fmtDist(TGEOM.trackStats(t).dist, FK.tac.unit())', first + second)
    assert info(page) == f'{d} over 5 min (under 1 min moving), 20 points. Moving average {mph:.1f} mph.'


def test_info_moving_time_shown_in_hours_and_minutes(page, app_url):
    # 40 minutes walking (70 m a minute), a 30 minute stop, 5 more points a minute apart: elapsed 1 h 15 min, moving 44 min
    walk = lambda i: LAT0 + 70 * i / M_PER_DEG
    pts = [pt(0, t=T0 + 60000 * i, lat=walk(i)) for i in range(41)]
    pts += [pt(0, t=T0 + 40 * 60000 + 30 * 60000 + 60000 * i, lat=walk(40 + i)) for i in range(1, 6)]
    store(page, track=pts)
    open_map(page, app_url)
    open_track(page)
    assert ' over 1 h 15 min (44 min moving), 46 points.' in info(page)


def test_info_short_pause_is_not_mentioned(page, app_url):
    store(page, track=[pt(0, t=T0, lat=LAT0), pt(0, t=T0 + 30000, lat=LAT0 + 40 / M_PER_DEG), pt(0, t=T0 + 90000, lat=LAT0 + 80 / M_PER_DEG)])
    open_map(page, app_url)
    open_track(page)
    assert 'moving)' not in info(page)


def test_info_no_speed_when_barely_moving_or_barely_timed(page, app_url):
    store(page, track=[pt(0, t=T0), pt(1, t=T0 + 5000)])      # 5 s of movement
    open_map(page, app_url)
    open_track(page)
    assert info(page).endswith('2 points.')
    assert 'Moving average' not in info(page)


def test_info_no_speed_under_10_m(page, app_url):
    store(page, track=[pt(0, t=T0), pt(1, t=T0 + 30000), pt(2, t=T0 + 60000)])    # about 6.7 m in a minute
    open_map(page, app_url)
    open_track(page)
    assert 'Moving average' not in info(page)


def test_info_one_point_says_point(page, app_url):
    store(page, track=[pt(0, 100)])
    open_map(page, app_url)
    open_track(page)
    assert info(page).endswith(' over 0 min, 1 point.')


def test_info_updates_while_recording(page, app_url):
    from .tac import gps_searching
    gps_searching(page)
    open_map(page, app_url)
    page.evaluate('() => { FK.map.openTrack(); }')
    page.click('#trkToggle')
    for i in range(4):
        page.evaluate('f => FK._test.fix(f)', {'lat': LAT0 + 0.0003 * i, 'lon': LON0, 'acc': 5, 'alt': 100, 'spd': None, 't': T0 + 10000 * i})
    expect(page.locator('#trkInfo')).to_contain_text('4 points')
    assert 'Moving average' in info(page)


def test_dialog_does_not_scroll_sideways_at_360(page, app_url):
    page.set_viewport_size({'width': 360, 'height': 740})
    alts = [100 + 50 * i / 19 for i in range(20)]
    store(page, track=[[round(LAT0 + 0.00018 * i, 6), LON0, alts[i], T0 + (10000 if i < 10 else 3_700_000) * i] for i in range(20)])
    open_map(page, app_url)
    open_track(page)
    assert 'moving)' in info(page)
    over = page.evaluate("""() => { const d = document.querySelector('#dlgTrack'); const r = [d.scrollWidth - d.clientWidth];
      d.querySelectorAll('*').forEach(e => { const b = e.getBoundingClientRect(); if (b.width && b.right > document.documentElement.clientWidth + 0.5) r.push(e.id || e.tagName); });
      return r; }""")
    assert over[0] <= 0 and len(over) == 1, over


# ---------- times that make no sense ----------

BAD_TIMES = {
    'reversed': [pt(i, t=T0 + 1000 * (9 - i)) for i in range(10)],
    'shuffled': [pt(i, t=T0 + 1000 * k) for i, k in enumerate([5, 1, 8, 0, 9, 3, 7, 2, 6, 4])],
    'duplicate': [pt(i, t=T0) for i in range(10)],
    'missing': [pt(i) if i else [round(LAT0, 6), LON0, None] for i in range(10)],
    'seconds': [pt(i, t=T0 // 1000 + i) for i in range(10)],
    'all_missing': [[round(LAT0 + STEP * i, 6), LON0, None] for i in range(5)],
}


@pytest.mark.parametrize('name', list(BAD_TIMES))
def test_stats_odd_times_are_never_negative_or_not_numbers(ready, name):
    s = stats(ready, BAD_TIMES[name])
    for k in ('elapsedMs', 'movingMs'):
        assert isinstance(s[k], (int, float)) and s[k] >= 0 and s[k] < 1e15, (k, s)
    assert s['movingMs'] <= s['elapsedMs']


def test_stats_reversed_and_shuffled_use_latest_minus_earliest(ready):
    assert stats(ready, BAD_TIMES['reversed'])['elapsedMs'] == 9000
    assert stats(ready, BAD_TIMES['shuffled'])['elapsedMs'] == 9000
    assert stats(ready, BAD_TIMES['reversed'])['movingMs'] == 0     # every gap runs backwards
    assert stats(ready, BAD_TIMES['duplicate']) ['elapsedMs'] == 0
    assert stats(ready, BAD_TIMES['missing'])['elapsedMs'] == 8000
    assert stats(ready, BAD_TIMES['all_missing']) ['elapsedMs'] == 0


@pytest.mark.parametrize('name', ['reversed', 'shuffled', 'duplicate', 'seconds'])
def test_info_odd_times_show_no_negative_or_broken_number(page, app_url, name):
    store(page, track=BAD_TIMES[name])
    open_map(page, app_url)
    open_track(page)
    text = info(page)
    for bad in ('-', 'NaN', 'Infinity', 'undefined'):
        assert bad not in text, text
    assert text.startswith(page.evaluate('t => TGEOM.fmtDist(TGEOM.pathLength(t), FK.tac.unit())', BAD_TIMES[name]) + ' over ')


def test_info_follows_the_distance_unit_while_open(page, app_url):
    tr = [[round(LAT0 + 0.00018 * i, 6), LON0, None, T0 + 10000 * i] for i in range(20)]
    store(page, track=tr)
    open_map(page, app_url)
    open_track(page)
    page.evaluate("FK.tac.setUnit('metric')")
    before = info(page)
    assert before.startswith('380 m over 3 min') and before.endswith('Moving average 4.5 mph.')
    page.evaluate("FK.tac.setUnit('us')")
    after = info(page)
    assert after.startswith('416 yd over 3 min') and after.endswith('Moving average 4.5 mph.')


# ---------- speed counts only the distance covered while moving ----------

def gps_off_track():
    """10 points 3 m apart a second apart, 12 minutes with the GPS off while about 500 m was covered (a gap over 10 min is
    a pause), then 10 more points."""
    first = [pt(i) for i in range(10)]
    jump = 9 + 500 / (STEP * M_PER_DEG / 1)      # latitude steps: 500 m further on
    second = [pt(jump + i, t=T0 + 9000 + 720000 + 1000 * i) for i in range(10)]
    return first + second


def test_stats_moving_dist_leaves_out_the_distance_across_a_pause(ready):
    s = stats(ready, gps_off_track())
    assert s['movingMs'] == 18000
    assert s['dist'] > 500 and 55 <= s['movingDist'] <= 65, s     # 18 steps of about 3.3 m


def test_info_speed_ignores_distance_covered_during_a_gps_gap(page, app_url):
    tr = gps_off_track()
    store(page, track=tr)
    open_map(page, app_url)
    open_track(page)
    s = page.evaluate('t => TGEOM.trackStats(t)', tr)
    mph = s['movingDist'] / 18 / 0.44704
    text = info(page)
    assert f'Moving average {mph:.1f} mph.' in text and mph < 25, text
    assert 'over 12 min (under 1 min moving), 20 points.' in text


def test_info_speed_for_a_stationary_pause_is_unchanged(page, app_url):
    first = [pt(i) for i in range(10)]
    second = [pt(8 + i, t=T0 + 9000 + 300000 + 1000 * i) for i in range(1, 11)]     # no movement in the gap
    store(page, track=first + second)
    open_map(page, app_url)
    open_track(page)
    assert info(page).endswith('Moving average 7.5 mph.')


def test_info_unbroken_track_text_is_pinned(page, app_url):
    store(page, track=[[round(LAT0 + 0.00018 * i, 6), LON0, None, T0 + 10000 * i] for i in range(20)])
    open_map(page, app_url)
    open_track(page)
    assert info(page) == '380 m over 3 min, 20 points. Moving average 4.5 mph.'


def test_stats_moving_dist_never_exceeds_dist(ready):
    for name, tr in list(BAD_TIMES.items()) + [('gps_off', gps_off_track())]:
        s = stats(ready, tr)
        assert 0 <= s['movingDist'] <= s['dist'] + 1e-9, (name, s)


def test_info_one_long_gap_has_no_speed(page, app_url):
    store(page, track=[pt(0, t=T0), pt(0.0, t=T0 + 660000, lat=LAT0 + 1000 / M_PER_DEG)])   # over 10 min: a pause
    open_map(page, app_url)
    open_track(page)
    text = info(page)
    assert text.startswith('1.00 km over 11 min') and 'Moving average' not in text
