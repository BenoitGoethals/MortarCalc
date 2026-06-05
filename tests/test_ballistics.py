import pytest

from mortarcalc.ballistics import solve
from mortarcalc.ballistics.firetable import TableRow
from mortarcalc.ballistics.solver import apply_drift


def test_interpolation_midpoint(firetable):
    c = firetable.charge_for(1500)
    row: TableRow = c.interp(1500)
    assert row.range_m == 1500
    # elevatie tussen tabel-buren in
    assert row.elevation_mils > 0


def test_charge_selection_lowest(firetable):
    # 400 m past in lading 0; lowest moet 0 zijn
    sol = solve(firetable, range_m=400, prefer_charge="lowest")
    assert sol.charge == 0


def test_charge_selection_highest(firetable):
    sol = solve(firetable, range_m=400, prefer_charge="highest")
    # 400 m valt binnen lading 0; lading 1 begint pas bij 200 m maar dekt 400 ook
    assert sol.charge >= 0
    # tenminste niet exceptioneel: hogere lading
    sol_h = solve(firetable, range_m=600, prefer_charge="highest")
    sol_l = solve(firetable, range_m=600, prefer_charge="lowest")
    assert sol_h.charge >= sol_l.charge


def test_delta_height_reduces_equiv_range_when_target_higher(firetable):
    # Δh > 0 (doel hoger) → equiv_range < raw_range
    sol = solve(firetable, range_m=2000, delta_height_m=+100)
    assert sol.equiv_range_m < sol.raw_range_m


def test_delta_height_increases_equiv_range_when_target_lower(firetable):
    sol = solve(firetable, range_m=2000, delta_height_m=-100)
    assert sol.equiv_range_m > sol.raw_range_m


def test_out_of_range_raises(firetable):
    with pytest.raises(ValueError):
        solve(firetable, range_m=10000)


def test_apply_drift_subtracts():
    # drift naar rechts (positief) → schiet links → azimut -drift
    assert apply_drift(1000, 10) == 990
    # wrap-around
    assert apply_drift(5, 10) == 6395
