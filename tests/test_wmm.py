"""WMM: magnetic declination from the World Magnetic Model (WMM2025). The coefficient source and NOAA's test values are
recorded in docs/content-review.md (v7.8 Tactical)."""
import math

import pytest

# NOAA "Test Values for WMM2025": (decimal year, height above the WGS84 ellipsoid in km, lat, lon, D in degrees).
# Every row of NOAA's main table. NOAA prints D to two decimals; the model must reproduce it to 0.01 degrees.
NOAA = [
    (2025.0, 0, 80, 0, 1.28),
    (2025.0, 0, 0, 120, -0.16),
    (2025.0, 0, -80, 240, 68.78),
    (2025.0, 100, 80, 0, 0.85),
    (2025.0, 100, 0, 120, -0.15),
    (2025.0, 100, -80, 240, 68.21),
    (2027.5, 0, 80, 0, 2.59),
    (2027.5, 0, 0, 120, -0.24),
    (2027.5, 0, -80, 240, 68.49),
    (2027.5, 100, 80, 0, 2.16),
    (2027.5, 100, 0, 120, -0.23),
    (2027.5, 100, -80, 240, 67.93),
]


@pytest.fixture
def ready(page, app_url):
    page.goto(app_url)
    page.wait_for_function('window.FK && typeof WMM !== "undefined"')
    return page


def decl(page, lat, lon, alt, year):
    return page.evaluate('([a, b, c, d]) => WMM.declination(a, b, c, d)', [lat, lon, alt, year])


@pytest.mark.parametrize('row', NOAA, ids=[f'{r[0]}-{r[1]}km-{r[2]},{r[3]}' for r in NOAA])
def test_matches_noaa_test_values(ready, row):
    year, alt, lat, lon, d = row
    assert abs(decl(ready, lat, lon, alt, year) - d) <= 0.01


def test_model_identity(ready):
    assert ready.evaluate('[WMM.name, WMM.epoch, WMM.validUntil]') == ['WMM2025', 2025.0, 2030.0]


def test_central_new_york_is_about_twelve_west(ready):
    """A sanity check against a wrong sign or unit, not a source of truth."""
    assert -14 < decl(ready, 43.0, -76.0, 0, 2026.9) < -10


@pytest.mark.parametrize('lat,lon', [(89.9, 180), (89.9, -180), (-89.9, 180), (-89.9, -180), (0, 180), (0, -180)])
def test_finite_near_poles_and_date_line(ready, lat, lon):
    v = decl(ready, lat, lon, 0, 2026.5)
    assert v is not None and math.isfinite(v)


@pytest.mark.parametrize('lat', [90, -90])
def test_exact_pole_is_null_or_finite_without_throwing(ready, lat):
    v = decl(ready, lat, 0, 0, 2026.5)
    assert v is None or math.isfinite(v)


def test_altitude_changes_little(ready):
    a, b = decl(ready, 43.0, -76.0, 0, 2026.5), decl(ready, 43.0, -76.0, 100, 2026.5)
    assert a != b and abs(a - b) < 0.5


@pytest.mark.parametrize('year', [1970.0, 2024.5, 2031.0, 2099.0])
def test_outside_validity_still_returns_a_number(ready, year):
    v = decl(ready, 43.0, -76.0, 0, year)
    assert v is not None and math.isfinite(v)


@pytest.mark.parametrize('bad', [[float('nan'), 0, 0, 2026], [0, 0, 0, None], [91, 0, 0, 2026]])
def test_bad_input_is_null(ready, bad):
    assert ready.evaluate('a => WMM.declination(...a)', bad) is None
