import math

import pytest

from mortarcalc.battery import Peloton, Piece, Group, AimingPoint, lay_on_watch
from mortarcalc.geo import mgrs_to_utm


def test_piece_exclusivity_in_groups(peloton_4x2):
    # A zit in Noord, verplaats naar Zuid
    peloton_4x2.assign_piece_to_group("A", "Zuid")
    assert "A" in peloton_4x2.group("Zuid").member_names
    assert "A" not in peloton_4x2.group("Noord").member_names


def test_remove_piece_removes_from_group(peloton_4x2):
    peloton_4x2.remove_piece("A")
    assert all("A" not in g.member_names for g in peloton_4x2.groups)
    assert all(p.name != "A" for p in peloton_4x2.pieces)


def test_unassigned_pieces():
    pel = Peloton()
    pel.add_piece(Piece("X", mgrs_to_utm("31UDS1234567890", 80)))
    pel.add_piece(Piece("Y", mgrs_to_utm("31UDS1234567890", 80)))
    pel.add_group(Group("G", pdf_mils=0, member_names=["X"]))
    names = [p.name for p in pel.unassigned_pieces()]
    assert names == ["Y"]


def test_each_section_has_own_base_piece():
    """Het peloton mag meerdere basisstukken hebben — één per sectie."""
    pel = Peloton()
    pel.add_piece(Piece("A", mgrs_to_utm("31UDS1234567890", 80), is_base=True))
    pel.add_piece(Piece("B", mgrs_to_utm("31UDS1235067900", 82)))
    pel.add_piece(Piece("C", mgrs_to_utm("31UDS1240067850", 79), is_base=True))
    pel.add_piece(Piece("D", mgrs_to_utm("31UDS1245067920", 81)))
    pel.add_group(Group("Noord", pdf_mils=1600, member_names=["A", "B"]))
    pel.add_group(Group("Zuid", pdf_mils=2400, member_names=["C", "D"]))

    # Beide basisstukken blijven bestaan (geen globale exclusiviteit meer).
    assert [p.name for p in pel.pieces if p.is_base] == ["A", "C"]
    assert pel.base_of(pel.group("Noord")).name == "A"
    assert pel.base_of(pel.group("Zuid")).name == "C"


def test_single_base_per_section_enforced():
    """Twee basisstukken in dezelfde sectie → de andere wordt gedegradeerd."""
    pel = Peloton()
    pel.add_piece(Piece("A", mgrs_to_utm("31UDS1234567890", 80), is_base=True))
    pel.add_piece(Piece("B", mgrs_to_utm("31UDS1235067900", 82), is_base=True))
    pel.add_group(Group("G", pdf_mils=0, member_names=["A"]))
    pel.assign_piece_to_group("B", "G")  # B (ook basis) komt bij A in dezelfde sectie
    assert pel.base_of(pel.group("G")).name == "B"
    assert [p.name for p in pel.pieces if p.is_base] == ["B"]


def test_section_without_base_returns_none(peloton_4x2):
    # Zuid heeft in de fixture geen basisstuk.
    assert peloton_4x2.base_of(peloton_4x2.group("Zuid")) is None


def test_group_sector_limits():
    g = Group("S", pdf_mils=1600, left_limit_mils=800, right_limit_mils=2400)
    assert g.has_limits()
    assert g.sector_width_mils() == 1600.0
    # clockwise wrap-around sector across north
    g.set_limits(6000, 400)
    assert g.sector_width_mils() == 800.0
    # normalisation
    g.set_limits(7000, -200)
    assert g.left_limit_mils == 600.0 and g.right_limit_mils == 6200.0


def test_group_without_limits_is_full_circle():
    g = Group("S", pdf_mils=0)
    assert not g.has_limits()
    assert g.sector_width_mils() == 6400.0


def test_section_limits_persist_round_trip(tmp_path):
    from mortarcalc.persistence import save_state, load_state
    pel = Peloton()
    pel.add_piece(Piece("A", mgrs_to_utm("31UDS1234567890", 80)))
    pel.add_group(Group("N", pdf_mils=1600, member_names=["A"],
                        left_limit_mils=800, right_limit_mils=2400))
    path = tmp_path / "s.json"
    save_state(path, pel, [], [])
    loaded, _, _ = load_state(path)
    g = loaded.group("N")
    assert g.left_limit_mils == 800.0 and g.right_limit_mils == 2400.0


def test_observer_crud_and_uniqueness():
    from mortarcalc.battery import Observer
    pel = Peloton()
    pel.add_observer(Observer("OP1", mgrs_to_utm("31UDS1500068000", 120)))
    assert pel.observer("OP1").call_sign == "OP1"
    with pytest.raises(ValueError):
        pel.add_observer(Observer("OP1", mgrs_to_utm("31UDS1500068000", 120)))
    pel.update_observer("OP1", Observer("OP1A", mgrs_to_utm("31UDS1510068100", 130)))
    assert [o.call_sign for o in pel.observers] == ["OP1A"]
    pel.remove_observer("OP1A")
    assert pel.observers == []


def test_observers_persist_round_trip(tmp_path):
    from mortarcalc.battery import Observer
    from mortarcalc.persistence import save_state, load_state
    pel = Peloton()
    pel.add_observer(Observer("OP1", mgrs_to_utm("31UDS1500068000", 120)))
    pel.add_observer(Observer("OP2", mgrs_to_utm("31UDS1100066000", 90)))
    path = tmp_path / "s.json"
    save_state(path, pel, [], [])
    loaded, _, _ = load_state(path)
    assert [o.call_sign for o in loaded.observers] == ["OP1", "OP2"]
    assert loaded.observer("OP2").position.altitude_m == 90


def test_duplicate_piece_name_raises():
    pel = Peloton()
    pel.add_piece(Piece("A", mgrs_to_utm("31UDS1234567890")))
    with pytest.raises(ValueError):
        pel.add_piece(Piece("A", mgrs_to_utm("31UDS1234567890")))


def test_lay_on_watch_uses_group_pdf(peloton_4x2):
    g = peloton_4x2.group("Noord")
    ap = peloton_4x2.aiming_point("RP1")
    settings = lay_on_watch(peloton_4x2, g, ap)
    assert {s.piece for s in settings} == {"A", "B"}
    # Verschillende stukken zien hetzelfde AP onder licht andere hoek → verschillende vizier-instelling
    a, b = settings
    assert a.sight_mils != b.sight_mils


def test_lay_on_watch_with_distant_ap_minimizes_parallax():
    """Twee stukken op 20 m van elkaar, AP op 5 km → vizier-instellingen bijna gelijk."""
    pel = Peloton()
    pel.add_piece(Piece("A", mgrs_to_utm("31UDS5000050000", 50), is_base=True))
    pel.add_piece(Piece("B", mgrs_to_utm("31UDS5002050000", 50)))
    pel.add_group(Group("G", pdf_mils=0, member_names=["A", "B"]))
    ap_far = mgrs_to_utm("31UDS5000055000", 50)  # 5 km noord
    pel.add_aiming_point(AimingPoint("FAR", ap_far))
    settings = lay_on_watch(pel, pel.group("G"), pel.aiming_point("FAR"))
    # circulair verschil (wrap-around bij 0/6400)
    diff = abs(settings[0].sight_mils - settings[1].sight_mils) % 6400
    diff = min(diff, 6400 - diff)
    assert diff < 10
