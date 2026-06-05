"""Gedeelde fixtures voor de testsuite."""
from __future__ import annotations

from importlib.resources import files

import pytest

from mortarcalc.ballistics import load_firetable
from mortarcalc.battery import AimingPoint, Group, Peloton, Piece
from mortarcalc.geo import mgrs_to_utm


@pytest.fixture
def firetable():
    return load_firetable(str(files("mortarcalc.data.firetables").joinpath("m821_81mm_he.json")))


@pytest.fixture
def peloton_4x2() -> Peloton:
    """Peloton met 4 stukken, 2 groepen (Noord{A,B}, Zuid{C,D}), 2 merkpunten."""
    pel = Peloton()
    pel.add_piece(Piece("A", mgrs_to_utm("31UDS1234567890", 80), is_base=True))
    pel.add_piece(Piece("B", mgrs_to_utm("31UDS1235067900", 82)))
    pel.add_piece(Piece("C", mgrs_to_utm("31UDS1240067850", 79)))
    pel.add_piece(Piece("D", mgrs_to_utm("31UDS1245067920", 81)))
    pel.add_group(Group("Noord", pdf_mils=1600, member_names=["A", "B"]))
    pel.add_group(Group("Zuid",  pdf_mils=2400, member_names=["C", "D"]))
    pel.add_aiming_point(AimingPoint("RP1", mgrs_to_utm("31UDS1300068000", 120)))
    pel.add_aiming_point(AimingPoint("RP2", mgrs_to_utm("31UDS1280066500", 110)))
    return pel
