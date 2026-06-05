"""Tests voor de uitgebreide call-for-fire elementen."""
import math

import pytest

from mortarcalc.firemission import (
    FireMission, MethodOfFire, Sheaf, TargetType, Fuze, FireControl,
    Observer, TargetByGrid, solve_mission,
)
from mortarcalc.geo import mgrs_to_utm


def _fo():
    return Observer(call_sign="OP1", position=mgrs_to_utm("31UDS1100066000", 110))


def _fm(group="Noord", **kwargs) -> FireMission:
    base = dict(
        id="T", group_name=group, observer=_fo(),
        target_spec=TargetByGrid(mgrs_to_utm("31UDS1500070000", 95)),
    )
    base.update(kwargs)
    return FireMission(**base)


def test_defaults():
    fm = _fm()
    assert fm.method_of_fire == MethodOfFire.AF
    assert fm.sheaf == Sheaf.CONVERGED
    assert fm.target_type == TargetType.POINT
    assert fm.fuze == Fuze.QUICK
    assert fm.control == FireControl.WHEN_READY
    assert fm.rounds_per_piece == 1
    assert fm.rounds_fired == {}


def test_record_salvo_increments():
    fm = _fm(rounds_per_piece=3)
    fm.record_salvo(["A", "B"], rounds=1)
    fm.record_salvo(["A", "B"], rounds=1)
    assert fm.rounds_fired == {"A": 2, "B": 2}
    assert fm.total_rounds_fired() == 4
    assert fm.rounds_remaining("A") == 1


def test_record_salvo_per_piece():
    fm = _fm(rounds_per_piece=2)
    fm.record_salvo(["A"], rounds=2)
    assert fm.rounds_remaining("A") == 0
    assert fm.rounds_remaining("B") == 2


def test_overfire_gives_negative_remaining():
    fm = _fm(rounds_per_piece=2)
    fm.record_salvo(["A"], rounds=5)
    assert fm.rounds_remaining("A") == -3


def test_call_for_fire_brief_contains_key_elements():
    fm = _fm(target_description="troops in open", rounds_per_piece=3,
             method_of_fire=MethodOfFire.FFE, sheaf=Sheaf.PARALLEL, fuze=Fuze.VT)
    brief = fm.call_for_fire_brief()
    assert "OP1" in brief
    assert "Noord" in brief
    assert "FFE" in brief
    assert "3rd" in brief
    assert "parallel" in brief
    assert "VT" in brief
    assert "troops in open" in brief


def test_converged_sheaf_gives_different_az_per_piece(peloton_4x2, firetable):
    fm = _fm(sheaf=Sheaf.CONVERGED)
    sols = solve_mission(fm, peloton_4x2, firetable)
    az_set = {round(s.azimuth_mils, 1) for s in sols}
    # 2 stukken in groep Noord, op verschillende posities → ietwat verschillende az
    assert len(az_set) == 2


def test_parallel_sheaf_same_az_per_piece(peloton_4x2, firetable):
    fm = _fm(sheaf=Sheaf.PARALLEL)
    sols = solve_mission(fm, peloton_4x2, firetable)
    az_set = {s.azimuth_mils for s in sols}
    elev_set = {s.elevation_mils for s in sols}
    charge_set = {s.charge for s in sols}
    # Parallel: alle stukken dezelfde firing data
    assert len(az_set) == 1
    assert len(elev_set) == 1
    assert len(charge_set) == 1


def test_parallel_uses_base_piece_when_in_group(peloton_4x2, firetable):
    # Basisstuk A zit in groep Noord
    fm = _fm(group="Noord", sheaf=Sheaf.PARALLEL)
    sols_par = solve_mission(fm, peloton_4x2, firetable)
    # Converged-solution voor A apart berekenen
    fm_conv = _fm(group="Noord", sheaf=Sheaf.CONVERGED)
    sols_conv = solve_mission(fm_conv, peloton_4x2, firetable)
    sol_a_conv = next(s for s in sols_conv if s.piece == "A")
    # Parallel-solution moet match'en met A's converged-solution (A is geleidingsstuk)
    assert all(s.azimuth_mils == sol_a_conv.azimuth_mils for s in sols_par)
    assert all(s.elevation_mils == sol_a_conv.elevation_mils for s in sols_par)
