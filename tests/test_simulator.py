"""Tests for the demo-scenario generator."""
from __future__ import annotations

from mortarcalc.simulator import build_demo_peloton, DOS_LOAD, default_scenario_path


def test_demo_has_three_sections_of_two_tubes():
    pel = build_demo_peloton()
    assert len(pel.pieces) == 6
    assert len(pel.groups) == 3
    for g in pel.groups:
        assert len(g.member_names) == 2


def test_demo_each_section_has_base_and_limits():
    pel = build_demo_peloton()
    for g in pel.groups:
        assert pel.base_of(g) is not None, f"{g.name} has no base gun"
        assert g.has_limits(), f"{g.name} has no sector limits"
        assert g.sector_width_mils() == 1600.0


def test_demo_dos_ammo_on_every_tube():
    pel = build_demo_peloton()
    for p in pel.pieces:
        assert pel.ammo[p.name] == DOS_LOAD


def test_demo_two_fos_per_section_and_aiming_points():
    pel = build_demo_peloton()
    assert len(pel.observers) == 6          # 2 per section × 3
    assert len(pel.aiming_points) == 3
    # call signs are unique
    assert len({o.call_sign for o in pel.observers}) == 6


def test_demo_round_trips_through_persistence(tmp_path):
    from mortarcalc.persistence import save_state, load_state
    pel = build_demo_peloton()
    path = tmp_path / "demo.json"
    save_state(path, pel, [], [])
    loaded, _, _ = load_state(path)
    assert len(loaded.pieces) == 6
    assert len(loaded.observers) == 6
    assert all(loaded.base_of(g) is not None for g in loaded.groups)
    assert all(g.has_limits() for g in loaded.groups)
    assert len(loaded.fire_plan) == len(pel.fire_plan)
    assert any(t.is_fpf for t in loaded.fire_plan)


def test_demo_fire_plan_targets_are_in_sector_and_range():
    from mortarcalc.geo import polar
    pel = build_demo_peloton()
    assert len(pel.fire_plan) >= 5
    # mix of natures present
    shells = {t.shell for t in pel.fire_plan}
    assert {"HE", "SMOKE", "ILLUM"} <= shells
    assert any(t.is_fpf for t in pel.fire_plan)
    for t in pel.fire_plan:
        g = pel.group(t.suggested_group)            # suggested section exists
        gt = polar(pel.base_of(g).position, t.position)
        rel = (gt.azimuth_mils - g.left_limit_mils) % 6400.0
        assert rel <= g.sector_width_mils(), f"{t.name} outside {g.name} sector"
        assert 75 <= gt.range_m <= 5675, f"{t.name} out of range"


def test_demo_is_on_otterburn_utm_zone_30():
    pel = build_demo_peloton()
    # Otterburn (Northumberland) sits in UTM zone 30, MGRS square WG.
    for p in pel.pieces:
        assert p.position.zone == 30
        assert p.position.to_mgrs().startswith("30UWG")


def test_bundled_scenario_json_loads():
    from mortarcalc.persistence import load_state
    path = default_scenario_path()
    assert path.is_file(), "bundled otterburn.json missing — run `python -m mortarcalc.simulator`"
    pel, history, active = load_state(path)
    assert len(pel.pieces) == 6
    assert len(pel.groups) == 3
    assert len(pel.observers) == 6
    assert len(pel.fire_plan) == 6
    assert all(pel.base_of(g) is not None for g in pel.groups)


def test_app_default_scenario_loader():
    from mortarcalc.app import _load_default_scenario
    pel, history, active = _load_default_scenario()
    assert len(pel.pieces) == 6 and len(pel.observers) == 6
    assert history == [] and active == []


def test_write_scenario_json_round_trip(tmp_path):
    from mortarcalc.simulator import write_scenario_json
    from mortarcalc.persistence import load_state
    out = write_scenario_json(tmp_path / "scn.json")
    assert out.is_file()
    pel, _, _ = load_state(out)
    assert len(pel.pieces) == 6 and len(pel.fire_plan) == 6
