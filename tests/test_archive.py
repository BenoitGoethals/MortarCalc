"""Tests for archive snapshots and restore."""
import time

from mortarcalc.battery import Piece
from mortarcalc.geo import mgrs_to_utm
from mortarcalc.state import StateRepository


def test_archive_creates_timestamped_file(tmp_path, peloton_4x2):
    repo = StateRepository(tmp_path / "autosave.json")
    path = repo.archive(peloton_4x2, [], [], label="snapshot")
    assert path.exists()
    assert path.suffix == ".json"
    assert "snapshot" in path.name
    # Filename should include date-time pattern
    assert any(part.isdigit() for part in path.stem.split("_"))


def test_archive_dir_in_subfolder(tmp_path, peloton_4x2):
    repo = StateRepository(tmp_path / "autosave.json")
    path = repo.archive(peloton_4x2, [], [])
    assert path.parent == repo.archive_dir
    assert repo.archive_dir.is_dir()


def test_list_archives_newest_first(tmp_path, peloton_4x2):
    repo = StateRepository(tmp_path / "autosave.json")
    p1 = repo.archive(peloton_4x2, [], [], label="first")
    time.sleep(1.05)  # different mtime granularity is 1s on some FS
    p2 = repo.archive(peloton_4x2, [], [], label="second")
    listing = repo.list_archives()
    assert listing == [p2, p1]


def test_load_archive_roundtrip(tmp_path, peloton_4x2):
    repo = StateRepository(tmp_path / "autosave.json")
    peloton_4x2.set_ammo("A", "HE", 25)
    peloton_4x2.allocate_fm_id()
    path = repo.archive(peloton_4x2, [], [])
    pel2, hist, active = repo.load_archive(path)
    assert pel2.ammo_of("A", "HE") == 25
    assert pel2.next_fm_number == 2


def test_archive_does_not_overwrite_autosave(tmp_path, peloton_4x2):
    repo = StateRepository(tmp_path / "autosave.json")
    repo.save(peloton_4x2, [], [])
    auto_size = repo.path.stat().st_size
    repo.archive(peloton_4x2, [], [], label="test")
    # Autosave file unchanged
    assert repo.path.stat().st_size == auto_size


def test_label_sanitized(tmp_path, peloton_4x2):
    """Unsafe label characters get replaced with underscores."""
    repo = StateRepository(tmp_path / "autosave.json")
    path = repo.archive(peloton_4x2, [], [], label="my/bad:label")
    assert "/" not in path.name
    assert ":" not in path.name


def test_workflow_archive_then_reset(tmp_path, peloton_4x2):
    """Simulate the reset flow: archive, mutate, can recover from archive."""
    repo = StateRepository(tmp_path / "autosave.json")
    peloton_4x2.set_ammo("A", "HE", 30)
    archive_path = repo.archive(peloton_4x2, [], [], label="before_reset")
    # Now reset: clear pieces
    peloton_4x2.pieces.clear()
    peloton_4x2.ammo.clear()
    assert peloton_4x2.pieces == []
    # Recover from archive
    pel_back, _, _ = repo.load_archive(archive_path)
    assert len(pel_back.pieces) == 4
    assert pel_back.ammo_of("A", "HE") == 30
