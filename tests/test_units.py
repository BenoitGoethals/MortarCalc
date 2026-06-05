import math

from mortarcalc.units import deg_to_mils, mils_to_deg, rad_to_mils, mils_to_rad, normalize_mils


def test_deg_mils_roundtrip():
    for d in (0, 45, 90, 180, 359.9):
        assert math.isclose(mils_to_deg(deg_to_mils(d)), d, abs_tol=1e-9)


def test_rad_mils_roundtrip():
    for r in (0, math.pi / 4, math.pi, 1.5):
        assert math.isclose(mils_to_rad(rad_to_mils(r)), r, abs_tol=1e-9)


def test_known_conversions():
    assert math.isclose(deg_to_mils(90), 1600.0)
    assert math.isclose(deg_to_mils(360), 6400.0)
    assert math.isclose(mils_to_deg(3200), 180.0)


def test_normalize_mils():
    assert normalize_mils(7000) == 600
    assert normalize_mils(-100) == 6300
    assert normalize_mils(0) == 0
    assert normalize_mils(6399.9) == 6399.9
