"""Tab 'Kaart' — Leaflet kaart in QtWebEngine met stukken, merkpunten, FO en doelen."""
from __future__ import annotations

import json
from importlib.resources import files
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QUrl
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QHBoxLayout, QLabel,
    QFileDialog, QMessageBox,
)
from PySide6.QtWebEngineCore import QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView

from ..battery import Peloton
from ..firemission.mission import TargetType, Sheaf
from ..geo import utm_to_latlon, offset
from .mbtiles_server import TileServer

if TYPE_CHECKING:
    from .mission_panel import MissionPanel


def _latlon(pos) -> tuple[float, float]:
    return utm_to_latlon(pos)


class MapPanel(QWidget):
    """Toont peloton + actieve fire missions op een Leaflet-kaart."""

    def __init__(self, peloton: Peloton, mission_panel: "MissionPanel") -> None:
        super().__init__()
        self.peloton = peloton
        self.mission_panel = mission_panel
        self.loaded = False
        self._tile_server = TileServer()

        root = QVBoxLayout(self)
        bar = QHBoxLayout()
        self._mbtiles_label = QLabel("MBTiles: (none)")
        b_mbtiles = QPushButton("Load MBTiles…")
        b_mbtiles.clicked.connect(self._on_load_mbtiles)
        b_clear = QPushButton("Clear MBTiles")
        b_clear.clicked.connect(self._on_clear_mbtiles)
        b_refresh = QPushButton("Refresh")
        b_refresh.clicked.connect(self.refresh)
        bar.addWidget(QLabel("Live overview of platoon and active fire missions."))
        bar.addStretch(1)
        bar.addWidget(self._mbtiles_label)
        bar.addWidget(b_mbtiles)
        bar.addWidget(b_clear)
        bar.addWidget(b_refresh)
        root.addLayout(bar)

        self.view = QWebEngineView()
        # map.html is loaded from a local file:// URL, so by default QtWebEngine
        # blocks the HTTPS tile requests and the canvas stays black. Allow the
        # local page to fetch remote tile URLs (and the local MBTiles server).
        settings = self.view.settings()
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessFileUrls, True)
        self.view.loadFinished.connect(self._on_loaded)
        html_path = files("mortarcalc.gui.assets").joinpath("map.html")
        self.view.load(QUrl.fromLocalFile(str(html_path)))
        root.addWidget(self.view, stretch=1)

    # ---------- MBTiles ----------
    def _on_load_mbtiles(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select MBTiles file", "", "MBTiles (*.mbtiles);;All files (*)",
        )
        if not path:
            return
        try:
            self._tile_server.load(Path(path))
        except Exception as e:
            QMessageBox.critical(self, "MBTiles load failed", str(e))
            return
        self._mbtiles_label.setText(f"MBTiles: {Path(path).name}")
        if self.loaded:
            url = self._tile_server.url_template
            js = (
                f"window.mc_set_mbtiles({json.dumps(url)},"
                f"{json.dumps(self._tile_server.store.metadata if self._tile_server.store else {})});"
            )
            self.view.page().runJavaScript(js)
        self.refresh()

    def _on_clear_mbtiles(self) -> None:
        self._tile_server.shutdown()
        self._mbtiles_label.setText("MBTiles: (none)")
        if self.loaded:
            self.view.page().runJavaScript("window.mc_set_mbtiles(null, null);")

    def _on_loaded(self, ok: bool) -> None:
        self.loaded = ok
        if ok:
            # If MBTiles were already loaded, hand them to JS before the first render.
            if self._tile_server.url_template:
                js = (
                    f"window.mc_set_mbtiles({json.dumps(self._tile_server.url_template)},"
                    f"{json.dumps(self._tile_server.store.metadata if self._tile_server.store else {})});"
                )
                self.view.page().runJavaScript(js)
            self.refresh()

    def refresh(self) -> None:
        if not self.loaded:
            return
        payload = self._build_payload()
        js = f"window.mc_render({json.dumps(json.dumps(payload))});"
        self.view.page().runJavaScript(js)

    # ---------- data ----------
    def _build_payload(self) -> dict:
        pieces = []
        pdf_arrows = []
        for p in self.peloton.pieces:
            lat, lon = _latlon(p.position)
            g = self.peloton.group_of(p.name)
            pieces.append({
                "name": p.name, "lat": lat, "lon": lon,
                "mgrs": p.position.to_mgrs(), "is_base": p.is_base,
                "group": g.name if g else None,
            })
            if g is not None:
                # 200 m pijl in PDF-richting vanuit het stuk
                tip = offset(p.position, g.pdf_mils, 200.0)
                tlat, tlon = _latlon(tip)
                pdf_arrows.append({
                    "from_lat": lat, "from_lon": lon,
                    "to_lat": tlat, "to_lon": tlon,
                })

        aps = []
        for ap in self.peloton.aiming_points:
            lat, lon = _latlon(ap.position)
            aps.append({"name": ap.name, "lat": lat, "lon": lon, "mgrs": ap.position.to_mgrs()})

        fos = []
        targets = []
        gt_lines = []
        seen_fos: set[str] = set()
        for group_name, fm in self.mission_panel.active.items():
            if fm is None:
                continue
            key = f"{fm.observer.call_sign}:{fm.observer.position.easting:.0f},{fm.observer.position.northing:.0f}"
            if key not in seen_fos:
                seen_fos.add(key)
                lat, lon = _latlon(fm.observer.position)
                fos.append({"call_sign": fm.observer.call_sign, "lat": lat, "lon": lon,
                            "mgrs": fm.observer.position.to_mgrs()})
            if fm.target_position is not None:
                tlat, tlon = _latlon(fm.target_position)
                target_entry: dict = {
                    "fm_id": fm.id, "group": group_name, "lat": tlat, "lon": tlon,
                    "mgrs": fm.target_position.to_mgrs(),
                    "type": fm.target_type.value,
                    "description": fm.target_description or "",
                    "sheaf": fm.sheaf.value,
                }
                # Voor lijn-doel of LINEAR sheaf: bereken twee eindpunten van de lijn.
                if fm.target_type == TargetType.LINEAR or fm.sheaf == Sheaf.LINEAR:
                    half = max(0.0, fm.line_length_m) / 2.0
                    az = fm.line_azimuth_mils
                    end_a = offset(fm.target_position, az, half)
                    end_b = offset(fm.target_position, (az + 3200.0) % 6400.0, half)
                    a_lat, a_lon = _latlon(end_a)
                    b_lat, b_lon = _latlon(end_b)
                    target_entry["line"] = {
                        "a_lat": a_lat, "a_lon": a_lon,
                        "b_lat": b_lat, "b_lon": b_lon,
                        "length_m": fm.line_length_m,
                        "azimuth_mils": fm.line_azimuth_mils,
                    }
                targets.append(target_entry)
                # GT-lijnen vanaf elk stuk in de groep naar het doel
                try:
                    group = self.peloton.group(group_name)
                except KeyError:
                    continue
                for piece in self.peloton.pieces_in(group):
                    plat, plon = _latlon(piece.position)
                    gt_lines.append({"from_lat": plat, "from_lon": plon,
                                     "to_lat": tlat, "to_lon": tlon})

        return {
            "pieces": pieces,
            "pdf_arrows": pdf_arrows,
            "aiming_points": aps,
            "fos": fos,
            "targets": targets,
            "gt_lines": gt_lines,
        }

    # ---------- cleanup ----------
    def closeEvent(self, event) -> None:  # noqa: N802
        self._tile_server.shutdown()
        super().closeEvent(event)
