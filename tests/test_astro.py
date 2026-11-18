"""Task 10: FK_ASTRO sun and moon times against US Naval Observatory values in tests/fixtures/almanac-syracuse.json.

The page runs in the row's own time zone (America/New_York for Syracuse, America/Anchorage for Utqiagvik), so
local midnight and the fixture's local clock times are turned into epoch ms by the browser itself, which also
covers the days either side of the US clock changes (2026-03-08 and 2026-11-01).
"""
import json, os

import pytest

from .conftest import _is_local

FIXTURE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixtures', 'almanac-syracuse.json')
ROWS = json.load(open(FIXTURE, encoding='utf-8'))['rows']
SUN_TOL_MS = 2 * 60_000
MOON_TOL_MS = 5 * 60_000


def tz_page_for(browser, tz):
    """Like conftest's page fixture, but with the context's time zone and locale set."""
    ctx = browser.new_context(viewport={'width': 360, 'height': 640}, service_workers='block', timezone_id=tz, locale='en-US')
    ctx.route('**/*', lambda route: route.continue_() if _is_local(route.request.url) else route.abort())
    pg = ctx.new_page()
    errors = []
    pg.on('pageerror', lambda e: errors.append(f'pageerror: {e}'))
    pg.on('console', lambda m: errors.append(f'console: {m.text}') if m.type == 'error' and _is_local(m.location.get('url') or '') else None)
    return ctx, pg, errors


@pytest.fixture
def ny_page(browser):
    ctx, pg, errors = tz_page_for(browser, 'America/New_York')
    yield pg
    ctx.close()
    assert errors == [], 'browser errors:\n' + '\n'.join(errors)


@pytest.fixture
def ak_page(browser):
    ctx, pg, errors = tz_page_for(browser, 'America/Anchorage')
    yield pg
    ctx.close()
    assert errors == [], 'browser errors:\n' + '\n'.join(errors)


COMPUTE = """([row]) => {
  const [y, m, d] = row.date.split('-').map(Number);
  // new Date(y, m, d, h, min) reads a wall-clock time in the page's time zone, so 06:39 on 2026-11-01 is EST and
  // 07:29 on 2026-03-08 is EDT, as a phone in America/New_York shows them.
  const local = hm => { if (hm === null) return null; const [h, mi] = hm.split(':').map(Number); return new Date(y, m - 1, d, h, mi).getTime(); };
  const start = new Date(y, m - 1, d).getTime();
  const want = { sun: {}, moon: {} };
  for (const k of Object.keys(row.sun)) want.sun[k] = local(row.sun[k]);
  for (const k of Object.keys(row.moon)) want.moon[k] = local(row.moon[k]);
  return { want, sun: FK_ASTRO.sun(start, row.lat, row.lon), moon: FK_ASTRO.moon(start, row.lat, row.lon) };
}"""

PHASE_TOL_PCT = 3


def phase_name_ok(row, got):
    """USNO's daily phase text names a primary phase on some days it happens (New Moon 2026-11-09, Full Moon 11-24,
    First Quarter at Utqiagvik 06-21) but not others (Waxing Gibbous 52% on 11-17, the First Quarter day; Waxing
    Crescent 48% on 06-21 at Syracuse; Waning Gibbous 52% on 11-01, the Last Quarter day). FK_ASTRO names the primary
    phase on the local day it happens. So the name must equal USNO's text, or, on the local date of USNO's closest
    primary phase, equal that primary phase."""
    usno, got = row['phase']['usno'].lower(), got.lower()
    return got == usno or (row['phase']['closestPrimaryDate'] == row['date'] and got == row['phase']['closestPrimary'].lower())


def check_row(pg, app_url, row):
    pg.goto(app_url + '#/survival')
    pg.wait_for_function('window.FK_ASTRO && window.FK && FK.survival')
    r = pg.evaluate(COMPUTE, [row])
    for part, tol in (('sun', SUN_TOL_MS), ('moon', MOON_TOL_MS)):
        for k, want in r['want'][part].items():
            got = r[part][k]
            if want is None:
                assert got is None, f"{row['place']} {row['date']} {part}.{k}: USNO lists none, got {got}"
            else:
                assert got is not None, f"{row['place']} {row['date']} {part}.{k}: USNO {row[part][k]}, got none"
                assert abs(got - want) <= tol, f"{row['place']} {row['date']} {part}.{k}: off by {(got - want) / 60000:.1f} min"
    assert phase_name_ok(row, r['moon']['name']), f"{row['date']}: {r['moon']['name']} vs USNO {row['phase']['usno']}"
    assert abs(r['moon']['illum'] * 100 - row['phase']['illumPct']) <= PHASE_TOL_PCT
    return r


SYR = [r for r in ROWS if r['tz'] == 'America/New_York']
UTQ = [r for r in ROWS if r['tz'] == 'America/Anchorage']


def test_fixture_has_every_planned_row_from_usno():
    assert [r['date'] for r in SYR] == ['2026-03-07', '2026-03-08', '2026-03-09', '2026-03-20', '2026-06-21', '2026-09-22',
                                        '2026-10-31', '2026-11-01', '2026-11-02', '2026-11-09', '2026-11-17', '2026-11-24',
                                        '2026-12-21']
    assert [r['date'] for r in UTQ] == ['2026-06-21', '2026-12-21']
    for r in ROWS:
        assert r['source'].startswith('USNO') and 'aa.usno.navy.mil/calculated/rstt/oneday' in r['source'] and '2026-11-17' in r['source']
        assert set(r['sun']) == {'dawn', 'rise', 'set', 'dusk'} and set(r['moon']) == {'rise', 'set'}
        assert 'confidence' not in r


@pytest.mark.parametrize('row', SYR, ids=[r['date'] for r in SYR])
def test_syracuse_matches_usno(ny_page, app_url, row):
    check_row(ny_page, app_url, row)


@pytest.mark.parametrize('row', UTQ, ids=[r['date'] for r in UTQ])
def test_utqiagvik_matches_usno(ak_page, app_url, row):
    check_row(ak_page, app_url, row)


def test_functions_are_pure_and_shaped(ny_page, app_url):
    ny_page.goto(app_url + '#/survival')
    ny_page.wait_for_function('window.FK_ASTRO')
    out = ny_page.evaluate("""() => {
      const start = new Date(2026, 10, 17).getTime();
      const s = FK_ASTRO.sun(start, 43.05, -76.15), m = FK_ASTRO.moon(start, 43.05, -76.15);
      return { sk: Object.keys(s).sort(), mk: Object.keys(m).sort(), m };
    }""")
    assert out['sk'] == ['dawn', 'dusk', 'rise', 'set']
    assert out['mk'] == ['illum', 'name', 'phase', 'rise', 'set']
    assert 0 <= out['m']['phase'] < 1 and 0 <= out['m']['illum'] <= 1
    assert out['m']['name'] in ['New moon', 'Waxing crescent', 'First quarter', 'Waxing gibbous', 'Full moon',
                                'Waning gibbous', 'Last quarter', 'Waning crescent']


def test_astro_is_first_script_and_has_no_dom_or_fk():
    src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src', 'astro.js'), encoding='utf-8').read()
    for word in ('document', 'FK.', 'window.FK ', 'localStorage', 'navigator'):
        assert word not in src, word
    build = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'build.py'), encoding='utf-8').read()
    assert "for f in ['astro.js', " in build


def test_f12_sun_altitude_constants_are_exported_once(page, app_url):
    page.goto(app_url + '#/survival')
    page.wait_for_function('window.FK_ASTRO')
    assert page.evaluate('[FK_ASTRO.SUN_RISE_ALT, FK_ASTRO.CIVIL_ALT]') == [-0.833, -6]
    tools = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src', 'survival-tools.js'), encoding='utf-8').read()
    assert '-0.833' not in tools and 'CIVIL_ALT = ' not in tools
