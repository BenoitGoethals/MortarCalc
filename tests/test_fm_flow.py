"""Tests for the proper FM flow: phases, fire commands, MTO, re-engage."""
import pytest

from mortarcalc.firemission import (
    FireMission, MissionState, Observer, TargetByGrid, solve_mission,
    MethodOfFire, Fuze, FireControl, Sheaf,
    format_mto, format_fire_command, format_all_fire_commands,
)
from mortarcalc.geo import mgrs_to_utm


def _basic_fm(group="Noord", **kwargs) -> FireMission:
    base = dict(
        id="FM001", group_name=group,
        observer=Observer("OP1", mgrs_to_utm("31UDS1100066000", 110)),
        target_spec=TargetByGrid(mgrs_to_utm("31UDS1500070000", 95)),
        target_description="troops in open",
    )
    base.update(kwargs)
    return FireMission(**base)


def test_mission_state_has_all_nato_phases():
    expected = {"received", "computed", "mto_sent", "ready", "shot", "splash",
                "adjusting", "in_effect", "rounds_complete", "end_of_mission"}
    assert {s.value for s in MissionState} == expected


def test_phase_sequence_can_advance():
    fm = _basic_fm()
    seq = [MissionState.RECEIVED, MissionState.COMPUTED, MissionState.MTO_SENT,
           MissionState.READY, MissionState.SHOT, MissionState.SPLASH,
           MissionState.ADJUSTING, MissionState.IN_EFFECT,
           MissionState.ROUNDS_COMPLETE, MissionState.END_OF_MISSION]
    for s in seq:
        fm.state = s
        assert fm.state == s


def test_format_mto_contains_required_elements(peloton_4x2, firetable):
    fm = _basic_fm(group="Noord", rounds_per_piece=3,
                   method_of_fire=MethodOfFire.FFE, fuze=Fuze.VT)
    sols = solve_mission(fm, peloton_4x2, firetable)
    mto = format_mto(fm, sols)
    assert "MTO" in mto
    assert "FM001" in mto
    assert "NOORD" in mto
    assert "PIECE A" in mto    # adjusting piece = first in section
    assert "HE" in mto
    assert "VT" in mto
    assert "TOF" in mto
    assert "OVER" in mto


def test_format_mto_uses_1_round_for_adjust_fire(peloton_4x2, firetable):
    fm = _basic_fm(method_of_fire=MethodOfFire.AF, rounds_per_piece=3)
    sols = solve_mission(fm, peloton_4x2, firetable)
    mto = format_mto(fm, sols)
    assert "1 ROUND" in mto


def test_format_fire_command_has_doctrinal_elements(peloton_4x2, firetable):
    fm = _basic_fm(method_of_fire=MethodOfFire.FFE, rounds_per_piece=2,
                   fuze=Fuze.DELAY, control=FireControl.AT_MY_COMMAND)
    sols = solve_mission(fm, peloton_4x2, firetable)
    cmd = format_fire_command(sols[0], fm)
    # Must mention: piece, charge, deflection, quadrant, shell, fuze, round count, control
    assert "PIECE A" in cmd
    assert "CHARGE" in cmd
    assert "DEFLECTION" in cmd
    assert "QUADRANT" in cmd
    assert "SHELL" in cmd and "HE" in cmd
    assert "FUZE DELAY" in cmd
    assert "2 ROUNDS" in cmd
    assert "AT MY COMMAND" in cmd


def test_format_all_fire_commands_one_per_piece(peloton_4x2, firetable):
    fm = _basic_fm()
    sols = solve_mission(fm, peloton_4x2, firetable)
    txt = format_all_fire_commands(fm, sols)
    for s in sols:
        assert f"PIECE {s.piece}" in txt


def test_format_fire_command_singular_round_word(peloton_4x2, firetable):
    fm = _basic_fm(method_of_fire=MethodOfFire.AF)
    sols = solve_mission(fm, peloton_4x2, firetable)
    cmd = format_fire_command(sols[0], fm)
    assert "1 ROUND" in cmd
    assert "1 ROUNDS" not in cmd


def test_mto_empty_solutions():
    fm = _basic_fm()
    txt = format_mto(fm, [])
    assert "NO SOLUTION" in txt
