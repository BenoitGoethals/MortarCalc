import math

import pytest

from mortarcalc.geo import (
    Position, polar, offset, mgrs_to_utm, utm_to_mgrs, utm_to_latlon, latlon_to_utm,
    validate_mgrs, normalize_mgrs, MGRSError,
)


def _pos(e, n, alt=0.0):
    return Position(easting=e, northing=n, zone=31, hemisphere="N", altitude_m=alt)


def test_polar_north():
    p = polar(_pos(0, 0), _pos(0, 1000))
    assert math.isclose(p.range_m, 1000.0)
    assert math.isclose(p.azimuth_mils, 0.0, abs_tol=1e-6)


def test_polar_east():
    p = polar(_pos(0, 0), _pos(1000, 0))
    assert math.isclose(p.range_m, 1000.0)
    assert math.isclose(p.azimuth_mils, 1600.0)  # 90° = 1600 streep


def test_polar_south():
    p = polar(_pos(0, 0), _pos(0, -1000))
    assert math.isclose(p.azimuth_mils, 3200.0)


def test_polar_west():
    p = polar(_pos(0, 0), _pos(-1000, 0))
    assert math.isclose(p.azimuth_mils, 4800.0)


def test_polar_delta_height():
    p = polar(_pos(0, 0, 100), _pos(1000, 0, 150))
    assert math.isclose(p.delta_height_m, 50.0)


def test_offset_roundtrip():
    origin = _pos(500000, 5500000, 50)
    moved = offset(origin, azimuth_mils=2400, range_m=1500)
    back = polar(origin, moved)
    assert math.isclose(back.range_m, 1500.0, abs_tol=1e-6)
    assert math.isclose(back.azimuth_mils, 2400.0, abs_tol=1e-6)


def test_mgrs_roundtrip():
    mgrs_str = "31UDS1234567890"
    pos = mgrs_to_utm(mgrs_str, altitude_m=100)
    assert utm_to_mgrs(pos) == mgrs_str


def test_utm_latlon_roundtrip():
    pos = mgrs_to_utm("31UDS1234567890", altitude_m=120)
    lat, lon = utm_to_latlon(pos)
    pos2 = latlon_to_utm(lat, lon, altitude_m=120)
    assert math.isclose(pos2.easting, pos.easting, abs_tol=0.5)
    assert math.isclose(pos2.northing, pos.northing, abs_tol=0.5)


def test_cross_zone_raises():
    a = Position(0, 0, zone=31, hemisphere="N")
    b = Position(0, 0, zone=32, hemisphere="N")
    with pytest.raises(ValueError):
        polar(a, b)


# ---------------------------------------------------------------- MGRS validation
def test_validate_mgrs_normalizes_spaces_and_case():
    assert validate_mgrs(" 31u ds 12345 67890 ") == "31UDS1234567890"
    assert normalize_mgrs(" 31u ds 123 ") == "31UDS123"


@pytest.mark.parametrize("good", [
    "31UDS1234567890",   # 10-digit
    "31UDS12345678",     # 8-digit
    "31UDS123456",       # 6-digit
    "31UDS1267",         # 4-digit
    "4QFJ1267",          # single-digit zone
])
def test_validate_mgrs_accepts_valid(good):
    assert validate_mgrs(good) == good.upper()


@pytest.mark.parametrize("bad", [
    "",                  # empty
    "HELLO",             # garbage
    "31UDS123456789",    # odd digit count
    "31IDS1234567890",   # band I not allowed
    "31UDS1234567890I",  # trailing junk / odd
    "99UDS1234567890",   # zone out of range
    "31UIO1234567890",   # square letter I
    "31UDS123456789012", # too many digits
])
def test_validate_mgrs_rejects_invalid(bad):
    with pytest.raises(MGRSError):
        validate_mgrs(bad)


def test_mgrs_to_utm_raises_clear_error_on_invalid():
    with pytest.raises(MGRSError):
        mgrs_to_utm("not-a-grid")
