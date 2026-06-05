"""Peloton (FDC-niveau) en Waakgroepen (tactische subgroepen).

Structuur:
  Peloton
    ├── pieces[]            (1-4 mortieren met GPS)
    ├── groups[]            (1-4 waakgroepen)
    │     ├── name
    │     ├── pdf_mils      (eigen waakrichting)
    │     ├── member_names  (subset van piece-namen, exclusief)
    │     └── (actieve FireMission wordt elders bijgehouden)
    └── aiming_points[]     (gedeelde merkpunten)

Invariant: elke piece-naam zit in hoogstens één group.member_names.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from ..geo import Position
from .piece import Piece


@dataclass(frozen=True)
class AimingPoint:
    name: str
    position: Position


@dataclass
class Group:
    """Waakgroep: subset van stukken met eigen PDF.

    `member_names` verwijst naar Piece.name in het bovenliggende Peloton.
    """
    name: str
    pdf_mils: float = 0.0
    member_names: list[str] = field(default_factory=list)

    def set_pdf(self, pdf_mils: float) -> None:
        self.pdf_mils = pdf_mils % 6400.0


DEFAULT_LOW_AMMO_THRESHOLD = 5


@dataclass
class Peloton:
    """FDC/Peloton-niveau: stukken + groepen + merkpunten + munitievoorraad + fire plan."""
    pieces: list[Piece] = field(default_factory=list)
    groups: list[Group] = field(default_factory=list)
    aiming_points: list[AimingPoint] = field(default_factory=list)
    # munitie: { piece_name: { shell_type: aantal } }
    ammo: dict[str, dict[str, int]] = field(default_factory=dict)
    low_ammo_threshold: int = DEFAULT_LOW_AMMO_THRESHOLD
    # fire plan: lijst van voorbereide doelen (PlannedTarget — gedefinieerd in fireplan.py)
    fire_plan: list = field(default_factory=list)
    # H-hour: referentie-tijd voor alle timings in het fire plan (None = onbepaald)
    h_hour: datetime | None = None
    # Auto-incrementing counter for fire mission IDs (FM001, FM002, ...)
    next_fm_number: int = 1

    def allocate_fm_id(self) -> str:
        """Allocate the next sequential fire mission ID. Increments the counter."""
        fm_id = f"FM{self.next_fm_number:03d}"
        self.next_fm_number += 1
        return fm_id

    # ---------- stukken ----------
    def base(self) -> Piece:
        for p in self.pieces:
            if p.is_base:
                return p
        raise ValueError("Geen basisstuk gedefinieerd.")

    def piece(self, name: str) -> Piece:
        for p in self.pieces:
            if p.name == name:
                return p
        raise KeyError(name)

    def add_piece(self, piece: Piece) -> None:
        if any(p.name == piece.name for p in self.pieces):
            raise ValueError(f"Stuk '{piece.name}' bestaat al.")
        if piece.is_base:
            self.pieces = [
                Piece(name=p.name, position=p.position, is_base=False) for p in self.pieces
            ]
        self.pieces.append(piece)

    def remove_piece(self, name: str) -> None:
        self.pieces = [p for p in self.pieces if p.name != name]
        for g in self.groups:
            if name in g.member_names:
                g.member_names.remove(name)

    # ---------- groepen ----------
    def group(self, name: str) -> Group:
        for g in self.groups:
            if g.name == name:
                return g
        raise KeyError(name)

    def add_group(self, group: Group) -> None:
        if any(g.name == group.name for g in self.groups):
            raise ValueError(f"Groep '{group.name}' bestaat al.")
        for pname in group.member_names:
            self._detach_piece(pname)
        self.groups.append(group)

    def remove_group(self, name: str) -> None:
        self.groups = [g for g in self.groups if g.name != name]

    def assign_piece_to_group(self, piece_name: str, group_name: str) -> None:
        """Verplaats een stuk naar een groep (verwijdert eerst uit huidige groep)."""
        if not any(p.name == piece_name for p in self.pieces):
            raise KeyError(f"Stuk '{piece_name}' bestaat niet.")
        self._detach_piece(piece_name)
        self.group(group_name).member_names.append(piece_name)

    def unassigned_pieces(self) -> list[Piece]:
        assigned: set[str] = {n for g in self.groups for n in g.member_names}
        return [p for p in self.pieces if p.name not in assigned]

    def group_of(self, piece_name: str) -> Group | None:
        for g in self.groups:
            if piece_name in g.member_names:
                return g
        return None

    def pieces_in(self, group: Group) -> list[Piece]:
        return [self.piece(n) for n in group.member_names]

    def _detach_piece(self, piece_name: str) -> None:
        for g in self.groups:
            if piece_name in g.member_names:
                g.member_names.remove(piece_name)

    # ---------- merkpunten ----------
    def add_aiming_point(self, ap: AimingPoint) -> None:
        if any(a.name == ap.name for a in self.aiming_points):
            raise ValueError(f"Merkpunt '{ap.name}' bestaat al.")
        self.aiming_points.append(ap)

    def aiming_point(self, name: str) -> AimingPoint:
        for ap in self.aiming_points:
            if ap.name == name:
                return ap
        raise KeyError(name)

    # ---------- munitie ----------
    def set_ammo(self, piece_name: str, shell: str, count: int) -> None:
        if not any(p.name == piece_name for p in self.pieces):
            raise KeyError(f"Stuk '{piece_name}' bestaat niet.")
        self.ammo.setdefault(piece_name, {})[shell.upper()] = max(0, int(count))

    def ammo_of(self, piece_name: str, shell: str) -> int:
        return self.ammo.get(piece_name, {}).get(shell.upper(), 0)

    def consume_ammo(self, piece_name: str, shell: str, rounds: int) -> int:
        """Verminder voorraad met `rounds`; return werkelijk verbruikte aantal."""
        have = self.ammo_of(piece_name, shell)
        used = min(have, max(0, int(rounds)))
        self.ammo.setdefault(piece_name, {})[shell.upper()] = have - used
        return used

    def low_ammo_pieces(self, shell: str = "HE") -> list[str]:
        """Stukken waarvan de voorraad van `shell` onder de drempel zit."""
        return [
            p.name for p in self.pieces
            if self.ammo_of(p.name, shell) <= self.low_ammo_threshold
        ]
