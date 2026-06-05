import json
from datetime import datetime

from mortarcalc.firemission import (
    FireMission, MissionState, Observer, TargetByGrid, solve_mission,
    MethodOfFire, Sheaf, Fuze, TargetType, FireControl,
)
from mortarcalc.firemission.solution import PieceSolution
from mortarcalc.geo import mgrs_to_utm
from mortarcalc.persistence import (
    save_state, load_state, peloton_from_dict, peloton_to_dict, VERSION,
)


def test_peloton_roundtrip(peloton_4x2):
    d = peloton_to_dict(peloton_4x2)
    pel2 = peloton_from_dict(d)
    assert [p.name for p in pel2.pieces] == [p.name for p in peloton_4x2.pieces]
    assert [g.name for g in pel2.groups] == [g.name for g in peloton_4x2.groups]
    assert pel2.group("Noord").member_names == ["A", "B"]
    assert pel2.aiming_point("RP1").name == "RP1"


def test_save_load_with_history(tmp_path, peloton_4x2, firetable):
    fm = FireMission(
        id="FM00001", group_name="Noord",
        observer=Observer("OP1", mgrs_to_utm("31UDS1100066000", 110)),
        target_spec=TargetByGrid(mgrs_to_utm("31UDS1500070000", 95)),
        target_description="test",
        target_type=TargetType.AREA,
        fuze=Fuze.VT,
        method_of_fire=MethodOfFire.FFE,
        sheaf=Sheaf.PARALLEL,
        rounds_per_piece=3,
        control=FireControl.AT_MY_COMMAND,
    )
    sols = solve_mission(fm, peloton_4x2, firetable)
    fm.record_salvo(["A", "B"], rounds=2)
    fm.state = MissionState.END_OF_MISSION
    fm.final_solutions = sols

    path = tmp_path / "state.json"
    save_state(path, peloton_4x2, [fm])
    pel2, missions, _active = load_state(path)

    assert len(missions) == 1
    fm2 = missions[0]
    assert fm2.id == fm.id
    assert fm2.group_name == "Noord"
    assert fm2.state == MissionState.END_OF_MISSION
    assert fm2.target_position is not None
    assert fm2.final_solutions is not None
    assert {s.piece for s in fm2.final_solutions} == {"A", "B"}
    # nieuwe v2 velden
    assert fm2.method_of_fire == MethodOfFire.FFE
    assert fm2.sheaf == Sheaf.PARALLEL
    assert fm2.fuze == Fuze.VT
    assert fm2.target_type == TargetType.AREA
    assert fm2.rounds_per_piece == 3
    assert fm2.control == FireControl.AT_MY_COMMAND
    assert fm2.rounds_fired == {"A": 2, "B": 2}


def test_load_v1_file_uses_defaults(tmp_path, peloton_4x2):
    """Oude v1 JSON moet inleesbaar zijn (defaults voor nieuwe velden)."""
    payload = {
        "version": 1,
        "peloton": peloton_to_dict(peloton_4x2),
        "missions": [{
            "id": "OLD01", "group_name": "Noord",
            "observer": {"call_sign": "FO", "position": {
                "easting": 100000, "northing": 5000000, "zone": 31, "hemisphere": "N", "altitude_m": 100,
            }},
            "target_spec": {"kind": "grid", "position": {
                "easting": 105000, "northing": 5003000, "zone": 31, "hemisphere": "N", "altitude_m": 110,
            }},
            "target_description": "legacy", "shell": "HE",
            "state": "end_of_mission",
            "received_at": "2025-01-01T00:00:00",
            "log": ["legacy log"],
        }],
    }
    path = tmp_path / "v1.json"
    path.write_text(json.dumps(payload))
    _p, missions, _a = load_state(path)
    assert len(missions) == 1
    fm = missions[0]
    assert fm.method_of_fire == MethodOfFire.AF  # default
    assert fm.sheaf == Sheaf.CONVERGED
    assert fm.rounds_per_piece == 1
    assert fm.rounds_fired == {}


def test_version_check(tmp_path, peloton_4x2):
    path = tmp_path / "bad.json"
    payload = {"version": 999, "peloton": {}, "missions": []}
    path.write_text(json.dumps(payload))
    try:
        load_state(path)
    except ValueError as e:
        assert "version" in str(e).lower()
    else:
        assert False, "expected ValueError"


def test_version_constant_is_current():
    assert VERSION == 5


def test_ammo_roundtrip(tmp_path, peloton_4x2):
    peloton_4x2.set_ammo("A", "HE", 30)
    peloton_4x2.set_ammo("B", "HE", 5)
    peloton_4x2.set_ammo("A", "WP", 4)
    path = tmp_path / "ammo.json"
    save_state(path, peloton_4x2, [])
    pel2, _h, _a = load_state(path)
    assert pel2.ammo_of("A", "HE") == 30
    assert pel2.ammo_of("B", "HE") == 5
    assert pel2.ammo_of("A", "WP") == 4


def test_fire_plan_roundtrip(tmp_path, peloton_4x2):
    from mortarcalc.battery import PlannedTarget
    from mortarcalc.geo import mgrs_to_utm
    peloton_4x2.fire_plan.append(PlannedTarget(
        name="AB1001", position=mgrs_to_utm("31UDS1500070000", 95),
        description="kruispunt", target_type="point",
        shell="HE", fuze="vt", sheaf="converged", rounds_per_piece=3,
        suggested_group="Noord", is_fpf=False,
    ))
    peloton_4x2.fire_plan.append(PlannedTarget(
        name="FPF_NORTH", position=mgrs_to_utm("31UDS1400070000", 100),
        description="FPF Noord", target_type="linear",
        sheaf="linear", line_azimuth_mils=1600, line_length_m=300,
        rounds_per_piece=2, is_fpf=True,
    ))
    path = tmp_path / "plan.json"
    save_state(path, peloton_4x2, [])
    pel2, _h, _a = load_state(path)
    assert len(pel2.fire_plan) == 2
    assert pel2.fire_plan[0].name == "AB1001"
    assert pel2.fire_plan[1].is_fpf is True
    assert pel2.fire_plan[1].line_length_m == 300
