"""Task 10: FK_ASTRO sun and moon times against the reference values in tests/fixtures/almanac-syracuse.json.

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
  const local = hm => { if (hm === null) return null; const [h, mi] = hm.split(':').map(Number); return new Date(y, m - 1, d, h, mi).getTime(); };
  const start = new Date(y, m - 1, d).getTime();
  const want = { sun: {}, moon: {} };
  for (const k of Object.keys(row.sun)) want.sun[k] = local(row.sun[k]);
  for (const k of Object.keys(row.moon || {})) want.moon[k] = local(row.moon[k]);
  return { want, sun: FK_ASTRO.sun(start, row.lat, row.lon), moon: FK_ASTRO.moon(start, row.lat, row.lon) };
}"""


def check_row(pg, app_url, row):
    pg.goto(app_url + '#/survival')
    pg.wait_for_function('window.FK_ASTRO && window.FK && FK.survival')
    r = pg.evaluate(COMPUTE, [row])
    for part, tol in (('sun', SUN_TOL_MS), ('moon', MOON_TOL_MS)):
        for k, want in r['want'][part].items():
            got = r[part][k]
            if want is None:
                assert got is None, f"{row['place']} {row['date']} {part}.{k}: expected none, got {got}"
            else:
                assert got is not None, f"{row['place']} {row['date']} {part}.{k}: expected {row[part][k]}, got none"
                assert abs(got - want) <= tol, f"{row['place']} {row['date']} {part}.{k}: off by {(got - want) / 60000:.1f} min"
    if 'phase' in row:
        lo, hi = min(row['phase']['illumSources']) - 0.03, max(row['phase']['illumSources']) + 0.03
        assert r['moon']['name'] == row['phase']['name']
        assert lo <= r['moon']['illum'] <= hi
    return r


SYR = [r for r in ROWS if r['tz'] == 'America/New_York']
UTQ = [r for r in ROWS if r['tz'] == 'America/Anchorage']


def test_fixture_has_the_verified_rows():
    """Planned: Syracuse 2026-03-07/08/09, 03-20, 06-21, 09-22, 10-31, 11-01, 11-02, 12-21 and Utqiagvik 06-21, 12-21, sun
    and moon. The March and June Syracuse rows and all moonrise/moonset times are left out until a source that can be
    trusted (USNO) is fetched: see docs/content-review.md, 'Daylight and moon reference values'."""
    assert [r['date'] for r in SYR] == ['2026-09-22', '2026-10-31', '2026-11-01', '2026-11-02', '2026-12-21']
    assert [r['date'] for r in UTQ] == ['2026-06-21', '2026-12-21']


@pytest.mark.parametrize('row', SYR, ids=[r['date'] for r in SYR])
def test_syracuse_matches_reference(ny_page, app_url, row):
    check_row(ny_page, app_url, row)


@pytest.mark.parametrize('row', UTQ, ids=[r['date'] for r in UTQ])
def test_utqiagvik_matches_reference(ak_page, app_url, row):
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


def test_phase_names_through_a_month(ny_page, app_url):
    """Primary phases are named on the local day they happen (November 2026: new 9th, first quarter 17th, full 24th,
    per time-ok.com's November table recorded in content-review); days between take the in-between names."""
    ny_page.goto(app_url + '#/survival')
    ny_page.wait_for_function('window.FK_ASTRO')
    names = ny_page.evaluate("""() => { const out = {};
      for (const d of [5, 9, 12, 17, 20, 24, 27]) out[d] = FK_ASTRO.moon(new Date(2026, 10, d).getTime(), 43.05, -76.15).name;
      return out; }""")
    assert names == {'5': 'Waning crescent', '9': 'New moon', '12': 'Waxing crescent', '17': 'First quarter',
                     '20': 'Waxing gibbous', '24': 'Full moon', '27': 'Waning gibbous'}


def test_astro_is_first_script_and_has_no_dom_or_fk():
    src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src', 'astro.js'), encoding='utf-8').read()
    for word in ('document', 'FK.', 'window.FK ', 'localStorage', 'navigator'):
        assert word not in src, word
    build = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'build.py'), encoding='utf-8').read()
    assert "for f in ['astro.js', " in build
