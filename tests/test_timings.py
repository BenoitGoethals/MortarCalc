"""Tests voor H-hour en fire-plan timings."""
from datetime import datetime, timedelta, timezone

import pytest

from mortarcalc.battery import PlannedTarget
from mortarcalc.geo import mgrs_to_utm


H = datetime(2026, 5, 19, 14, 0, 0, tzinfo=timezone.utc)


def _t(**kwargs):
    base = dict(
        name="T", position=mgrs_to_utm("31UDS1500070000", 95),
        description="", shell="HE", fuze="quick", sheaf="converged",
        rounds_per_piece=1,
    )
    base.update(kwargs)
    return PlannedTarget(**base)


def test_offset_label_basic():
    assert _t(start_offset_min=None).offset_label() == "On Call"
    assert _t(start_offset_min=0).offset_label() == "H"
    assert _t(start_offset_min=5).offset_label() == "H+5"
    assert _t(start_offset_min=-30).offset_label() == "H−30"


def test_scheduled_start_uses_h_hour():
    t = _t(start_offset_min=-30)
    assert t.scheduled_start(H) == H - timedelta(minutes=30)
    assert t.scheduled_start(None) is None
    assert _t(start_offset_min=None).scheduled_start(H) is None


def test_scheduled_end_with_duration():
    t = _t(start_offset_min=0, duration_min=10)
    assert t.scheduled_end(H) == H + timedelta(minutes=10)


def test_status_scheduled_due_active_past():
    t = _t(start_offset_min=0, duration_min=5)
    assert t.status_at(H - timedelta(minutes=1), H) == "SCHEDULED"
    assert t.status_at(H + timedelta(seconds=10), H) == "ACTIVE"
    assert t.status_at(H + timedelta(minutes=6), H) == "PAST"


def test_status_due_for_instant_target():
    """Doel zonder duur (FFE): DUE binnen 60s na H, daarna PAST."""
    t = _t(start_offset_min=0, duration_min=0)
    assert t.status_at(H + timedelta(seconds=10), H) == "DUE"
    assert t.status_at(H + timedelta(seconds=70), H) == "PAST"


def test_status_on_call():
    t = _t(start_offset_min=None)
    assert t.status_at(H, H) == "ON_CALL"


def test_persistence_roundtrip(tmp_path, peloton_4x2):
    """H-hour en timing-velden worden in v4 JSON bewaard."""
    from mortarcalc.persistence import save_state, load_state
    peloton_4x2.h_hour = H
    peloton_4x2.fire_plan.append(_t(name="AB1001", start_offset_min=-10, duration_min=0))
    peloton_4x2.fire_plan.append(_t(name="AB1002", start_offset_min=5, duration_min=15))
    peloton_4x2.fire_plan.append(_t(name="AB1003", start_offset_min=None))
    path = tmp_path / "plan.json"
    save_state(path, peloton_4x2, [])
    pel2, _h, _a = load_state(path)
    assert pel2.h_hour == H
    assert pel2.fire_plan[0].start_offset_min == -10
    assert pel2.fire_plan[1].duration_min == 15
    assert pel2.fire_plan[2].start_offset_min is None
