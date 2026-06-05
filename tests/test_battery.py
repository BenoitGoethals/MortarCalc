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
