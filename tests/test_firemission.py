import math

from mortarcalc.firemission import (
    Observer, FireMission, MissionState,
    TargetByGrid, TargetByPolar, TargetByShift,
    Correction, apply_correction, solve_mission, resolve_target,
)
from mortarcalc.geo import mgrs_to_utm, polar


def _fo():
    return Observer(call_sign="OP1", position=mgrs_to_utm("31UDS1100066000", 110))


def test_resolve_target_grid(peloton_4x2):
    pos = mgrs_to_utm("31UDS1500070000", 95)
    out = resolve_target(TargetByGrid(pos), _fo(), peloton_4x2)
    assert out.easting == pos.easting and out.northing == pos.northing


def test_resolve_target_polar(peloton_4x2):
    fo = _fo()
    out = resolve_target(TargetByPolar(azimuth_mils=0, range_m=1000, delta_height_m=20), fo, peloton_4x2)
    # 1000 m noord van FO
    assert math.isclose(out.northing, fo.position.northing + 1000, abs_tol=1e-6)
    assert math.isclose(out.altitude_m, fo.position.altitude_m + 20)


def test_resolve_target_shift(peloton_4x2):
    fo = _fo()
    ap = peloton_4x2.aiming_point("RP1")
    spec = TargetByShift(reference_name="RP1", right_m=100, add_m=50, delta_height_m=0)
    out = resolve_target(spec, fo, peloton_4x2)
    # add gaat langs OT-lijn (fo→ap), right perpendiculair → check afstand vanaf RP1
    dx = out.easting - ap.position.easting
    dy = out.northing - ap.position.northing
    assert math.isclose(math.hypot(dx, dy), math.hypot(100, 50), abs_tol=0.1)


def test_solve_mission_only_for_group_pieces(peloton_4x2, firetable):
    fm = FireMission(
        id="T01", group_name="Noord", observer=_fo(),
        target_spec=TargetByGrid(mgrs_to_utm("31UDS1500070000", 95)),
    )
    sols = solve_mission(fm, peloton_4x2, firetable)
    pieces = {s.piece for s in sols}
    assert pieces == {"A", "B"}  # niet C of D


def test_correction_moves_target_along_ot_for_add(peloton_4x2, firetable):
    fm = FireMission(
        id="T02", group_name="Noord", observer=_fo(),
        target_spec=TargetByGrid(mgrs_to_utm("31UDS1500070000", 95)),
    )
    solve_mission(fm, peloton_4x2, firetable)
    before = fm.target_position
    apply_correction(fm, Correction(add_m=100))
    after = fm.target_position
    # afstand FO→doel zou ~100 m langer moeten zijn (volledig add, geen right)
    d_before = polar(fm.observer.position, before).range_m
    d_after = polar(fm.observer.position, after).range_m
    assert math.isclose(d_after - d_before, 100.0, abs_tol=0.5)


def test_correction_right_perpendicular_to_ot(peloton_4x2, firetable):
    fm = FireMission(
        id="T03", group_name="Noord", observer=_fo(),
        target_spec=TargetByGrid(mgrs_to_utm("31UDS1500070000", 95)),
    )
    solve_mission(fm, peloton_4x2, firetable)
    before = fm.target_position
    apply_correction(fm, Correction(right_m=100))
    after = fm.target_position
    # afstand FO→doel ~gelijk (zuiver perpendiculair)
    d_before = polar(fm.observer.position, before).range_m
    d_after = polar(fm.observer.position, after).range_m
    assert abs(d_after - d_before) < 5.0
