"""Tests voor munitie-tracking, linear sheaf en fire plan."""
import math

import pytest

from mortarcalc.battery import Peloton, Piece, Group, PlannedTarget
from mortarcalc.firemission import (
    FireMission, Sheaf, MethodOfFire, Observer, TargetByGrid, solve_mission,
)
from mortarcalc.geo import mgrs_to_utm, polar


def test_set_ammo_and_consume(peloton_4x2):
    peloton_4x2.set_ammo("A", "HE", 30)
    assert peloton_4x2.ammo_of("A", "HE") == 30
    used = peloton_4x2.consume_ammo("A", "HE", 5)
    assert used == 5
    assert peloton_4x2.ammo_of("A", "HE") == 25


def test_consume_does_not_go_negative(peloton_4x2):
    peloton_4x2.set_ammo("A", "HE", 3)
    used = peloton_4x2.consume_ammo("A", "HE", 10)
    assert used == 3
    assert peloton_4x2.ammo_of("A", "HE") == 0


def test_set_ammo_unknown_piece_raises(peloton_4x2):
    with pytest.raises(KeyError):
        peloton_4x2.set_ammo("Z", "HE", 10)


def test_low_ammo_threshold(peloton_4x2):
    for p in peloton_4x2.pieces:
        peloton_4x2.set_ammo(p.name, "HE", 20)
    peloton_4x2.set_ammo("A", "HE", 3)  # onder default (5)
    low = peloton_4x2.low_ammo_pieces("HE")
    assert "A" in low and "B" not in low


def test_linear_sheaf_distributes_along_line(peloton_4x2, firetable):
    fm = FireMission(
        id="L01", group_name="Noord",
        observer=Observer("OP1", mgrs_to_utm("31UDS1100066000", 110)),
        target_spec=TargetByGrid(mgrs_to_utm("31UDS1500070000", 95)),
        sheaf=Sheaf.LINEAR,
        line_azimuth_mils=1600,  # oost
        line_length_m=400,
    )
    sols = solve_mission(fm, peloton_4x2, firetable)
    assert len(sols) == 2
    # Met 2 stukken: een op -200m, een op +200m langs azimut 1600
    # → dracht van A en B naar hun aim points moet ~400m verschillen in oost-richting
    # Hier vergelijken we gewoon dat de drachten verschillen (anders zou alles op hetzelfde punt aim'en)
    ranges = sorted([s.range_m for s in sols])
    assert ranges[1] - ranges[0] > 50  # voldoende spreiding


def test_linear_single_piece_no_offset(peloton_4x2, firetable):
    # Groep met enkel stuk A → spreiding moet 0 zijn
    peloton_4x2.add_group(Group("Solo", pdf_mils=1600, member_names=["A"]))
    fm = FireMission(
        id="L02", group_name="Solo",
        observer=Observer("OP1", mgrs_to_utm("31UDS1100066000", 110)),
        target_spec=TargetByGrid(mgrs_to_utm("31UDS1500070000", 95)),
        sheaf=Sheaf.LINEAR, line_azimuth_mils=1600, line_length_m=400,
    )
    sols = solve_mission(fm, peloton_4x2, firetable)
    assert len(sols) == 1


def test_planned_target_can_be_stored(peloton_4x2):
    t = PlannedTarget(
        name="AB1001",
        position=mgrs_to_utm("31UDS1500070000", 95),
        description="kruispunt N9",
        target_type="point", shell="HE", fuze="vt",
        sheaf="converged", rounds_per_piece=4,
        suggested_group="Noord",
    )
    peloton_4x2.fire_plan.append(t)
    assert len(peloton_4x2.fire_plan) == 1
    assert peloton_4x2.fire_plan[0].name == "AB1001"
    assert peloton_4x2.fire_plan[0].rounds_per_piece == 4
