"""Tests for sequential FM IDs, active-mission persistence, autosave repository."""
from pathlib import Path

from mortarcalc.battery import Peloton
from mortarcalc.firemission import (
    FireMission, MissionState, Observer, TargetByGrid, solve_mission,
)
from mortarcalc.geo import mgrs_to_utm
from mortarcalc.persistence import save_state, load_state, VERSION
from mortarcalc.state import StateRepository


def test_sequential_fm_ids():
    pel = Peloton()
    ids = [pel.allocate_fm_id() for _ in range(3)]
    assert ids == ["FM001", "FM002", "FM003"]
    assert pel.next_fm_number == 4


def test_fm_counter_survives_roundtrip(tmp_path, peloton_4x2):
    peloton_4x2.allocate_fm_id()
    peloton_4x2.allocate_fm_id()
    peloton_4x2.allocate_fm_id()
    assert peloton_4x2.next_fm_number == 4
    path = tmp_path / "state.json"
    save_state(path, peloton_4x2, [], [])
    pel2, _, _ = load_state(path)
    assert pel2.next_fm_number == 4
    assert pel2.allocate_fm_id() == "FM004"


def test_active_missions_persist(tmp_path, peloton_4x2, firetable):
    """Active missions are saved separately from history and restored intact."""
    fm = FireMission(
        id=peloton_4x2.allocate_fm_id(), group_name="Noord",
        observer=Observer("OP1", mgrs_to_utm("31UDS1100066000", 110)),
        target_spec=TargetByGrid(mgrs_to_utm("31UDS1500070000", 95)),
        target_description="active when saved",
        rounds_per_piece=3,
    )
    solve_mission(fm, peloton_4x2, firetable)
    fm.record_salvo(["A", "B"], rounds=1)
    fm.state = MissionState.ADJUSTING

    path = tmp_path / "state.json"
    save_state(path, peloton_4x2, history=[], active_missions=[fm])
    pel2, history, active = load_state(path)
    assert history == []
    assert len(active) == 1
    fm2 = active[0]
    assert fm2.id == "FM001"
    assert fm2.state == MissionState.ADJUSTING
    assert fm2.rounds_fired == {"A": 1, "B": 1}
    assert fm2.target_description == "active when saved"


def test_repository_roundtrip(tmp_path, peloton_4x2):
    repo = StateRepository(tmp_path / "autosave.json")
    assert not repo.exists()
    repo.save(peloton_4x2, [], [])
    assert repo.exists()
    assert repo.last_save is not None
    pel2, history, active = repo.load()
    assert len(pel2.pieces) == 4
    assert history == [] and active == []


def test_repository_atomic_write(tmp_path, peloton_4x2):
    """During save, no stray .tmp file should remain after success."""
    repo = StateRepository(tmp_path / "autosave.json")
    repo.save(peloton_4x2, [], [])
    leftovers = list(tmp_path.glob("*.tmp"))
    assert leftovers == []


def test_repository_delete(tmp_path, peloton_4x2):
    repo = StateRepository(tmp_path / "autosave.json")
    repo.save(peloton_4x2, [], [])
    repo.delete()
    assert not repo.exists()


def test_default_autosave_path_is_in_app_support():
    from mortarcalc.state import default_autosave_path
    p = default_autosave_path()
    assert p.name == "autosave.json"
    assert "MortarCalc" in str(p)
