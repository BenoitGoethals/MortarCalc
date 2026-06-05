"""Coordinaten: MGRS ↔ UTM ↔ Lat/Lon.

Alle interne berekeningen gebeuren in UTM (meters, zone-lokaal). MGRS wordt
gebruikt voor invoer/uitvoer naar de gebruiker en voor uitwisseling met FO.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import mgrs
import pyproj


@dataclass(frozen=True)
class Position:
    """Een punt op de grond, intern UTM (meters)."""
    easting: float
    northing: float
    zone: int            # UTM zone-nummer (1-60)
    hemisphere: str      # 'N' of 'S'
    altitude_m: float = 0.0

    def to_mgrs(self, precision: int = 5) -> str:
        return utm_to_mgrs(self, precision=precision)

    def __str__(self) -> str:
        return f"{self.to_mgrs()} @ {self.altitude_m:.0f}m"


@lru_cache(maxsize=1)
def _mgrs() -> mgrs.MGRS:
    return mgrs.MGRS()


def mgrs_to_utm(mgrs_str: str, altitude_m: float = 0.0) -> Position:
    """Parse een MGRS-string (bv. '31UDS1234567890') naar UTM Position."""
    zone, hemisphere, easting, northing = _mgrs().MGRSToUTM(mgrs_str.replace(" ", ""))
    return Position(
        easting=float(easting),
        northing=float(northing),
        zone=int(zone),
        hemisphere=hemisphere,
        altitude_m=altitude_m,
    )


def utm_to_mgrs(pos: Position, precision: int = 5) -> str:
    """UTM Position → MGRS-string. precision=5 → 1 m (10-cijferig grid)."""
    return _mgrs().UTMToMGRS(
        pos.zone, pos.hemisphere, pos.easting, pos.northing, MGRSPrecision=precision
    )


def utm_to_latlon(pos: Position) -> tuple[float, float]:
    """UTM Position → (lat, lon) in WGS84 graden."""
    transformer = pyproj.Transformer.from_crs(
        f"+proj=utm +zone={pos.zone} +{'south' if pos.hemisphere == 'S' else 'north'} +ellps=WGS84",
        "EPSG:4326",
        always_xy=True,
    )
    lon, lat = transformer.transform(pos.easting, pos.northing)
    return lat, lon


def latlon_to_utm(lat: float, lon: float, altitude_m: float = 0.0) -> Position:
    """WGS84 lat/lon (graden) → UTM Position in de juiste zone."""
    zone = int((lon + 180) / 6) + 1
    hemisphere = "N" if lat >= 0 else "S"
    transformer = pyproj.Transformer.from_crs(
        "EPSG:4326",
        f"+proj=utm +zone={zone} +{'south' if hemisphere == 'S' else 'north'} +ellps=WGS84",
        always_xy=True,
    )
    east, north = transformer.transform(lon, lat)
    return Position(easting=east, northing=north, zone=zone, hemisphere=hemisphere, altitude_m=altitude_m)
