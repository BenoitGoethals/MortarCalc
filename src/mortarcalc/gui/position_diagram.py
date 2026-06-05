"""Top-down plan-view: gun positions + PDF direction arrow for one section."""
from __future__ import annotations

import math

from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QPainter, QPen, QBrush, QColor, QPolygonF
from PySide6.QtWidgets import QWidget, QSizePolicy

from ..battery import Peloton, Group

_BG    = QColor("#1a2535")
_FG    = QColor("#ecf0f1")
_RED   = QColor("#e74c3c")
_GREEN = QColor("#27ae60")
_BLUE  = QColor("#2980b9")
_GREY  = QColor("#7f8c8d")

# Per-section PDF arrow colours (cycled). Limited to 4 sections by domain rule.
_SECTION_COLORS = [
    QColor("#e74c3c"),   # red
    QColor("#3498db"),   # blue
    QColor("#f39c12"),   # orange
    QColor("#9b59b6"),   # purple
]


class SectionDiagram(QWidget):
    """Plan-view diagram: gun positions (dots) + PDF direction (red arrows)."""

    _PAD       = 32    # pixels of padding around the plot area
    _GUN_R     = 7     # gun circle radius in px
    _ARROW_LEN = 54    # PDF arrow length in px

    def __init__(self, peloton: Peloton, group: Group, parent=None) -> None:
        super().__init__(parent)
        self.peloton = peloton
        self.group   = group
        self.setMinimumSize(180, 180)
        self.setMaximumHeight(210)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    # ------------------------------------------------------------------ paint
    def paintEvent(self, event) -> None:  # type: ignore[override]
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), _BG)

        pieces = [pc for pc in self.peloton.pieces
                  if pc.name in self.group.member_names]
        w, h = float(self.width()), float(self.height())

        if not pieces:
            p.setPen(_GREY)
            p.drawText(self.rect(), Qt.AlignCenter, "No pieces assigned")
            self._north(p, w - 18.0, 14.0)
            return

        # ---- coordinate → screen mapping ----
        es = [pc.position.easting  for pc in pieces]
        ns = [pc.position.northing for pc in pieces]
        ce = sum(es) / len(es)
        cn = sum(ns) / len(ns)
        span = max(
            (max(es) - min(es)) if len(pieces) > 1 else 0.0,
            (max(ns) - min(ns)) if len(pieces) > 1 else 0.0,
            50.0,
        )
        usable = min(w, h) - 2.0 * self._PAD
        scale  = usable / span
        cx, cy = w / 2.0, h / 2.0

        def sc(e: float, n: float) -> QPointF:
            return QPointF(cx + (e - ce) * scale,
                           cy - (n - cn) * scale)   # north = up

        # ---- PDF arrows (drawn behind guns) ----
        rad  = self.group.pdf_mils * 2.0 * math.pi / 6400.0
        udx  =  math.sin(rad)
        udy  = -math.cos(rad)   # screen Y is flipped
        p.setPen(QPen(_RED, 2))
        for pc in pieces:
            origin = sc(pc.position.easting, pc.position.northing)
            tip    = QPointF(origin.x() + udx * self._ARROW_LEN,
                             origin.y() + udy * self._ARROW_LEN)
            p.drawLine(origin, tip)
            _arrowhead(p, origin, tip, _RED)

        # ---- gun symbols ----
        for pc in pieces:
            pos   = sc(pc.position.easting, pc.position.northing)
            color = _GREEN if pc.is_base else _BLUE
            p.setBrush(QBrush(color))
            p.setPen(QPen(_FG, 1))
            p.drawEllipse(pos, float(self._GUN_R), float(self._GUN_R))
            font = p.font(); font.setPointSize(8); p.setFont(font)
            p.setPen(_FG)
            p.drawText(QPointF(pos.x() + self._GUN_R + 3, pos.y() + 4), pc.name)

        # ---- decorations ----
        self._north(p, w - 18.0, 14.0)
        self._scale_bar(p, scale, h)

        # PDF label bottom-right
        font = p.font(); font.setPointSize(8); p.setFont(font)
        p.setPen(_RED)
        p.drawText(QRectF(w / 2, h - 16, w / 2 - 4, 14),
                   Qt.AlignRight | Qt.AlignVCenter,
                   f"PDF  {int(self.group.pdf_mils)} mils ▶")

        # legend bottom-left
        font.setPointSize(7); p.setFont(font)
        p.setPen(_GREEN)
        p.drawText(QRectF(4, h - 28, 60, 12), Qt.AlignLeft, "● basisstuk")
        p.setPen(_BLUE)
        p.drawText(QRectF(4, h - 16, 60, 12), Qt.AlignLeft, "● stuk")

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _scale_bar(p: QPainter, scale: float, h: float) -> None:
        for metres in (500, 200, 100, 50, 20, 10):
            px = metres * scale
            if px >= 24:
                break
        else:
            return
        x0, y0 = 70.0, h - 20.0
        p.setPen(QPen(_GREY, 2))
        p.drawLine(QPointF(x0, y0), QPointF(x0 + px, y0))
        p.drawLine(QPointF(x0,      y0 - 3), QPointF(x0,      y0 + 3))
        p.drawLine(QPointF(x0 + px, y0 - 3), QPointF(x0 + px, y0 + 3))
        font = p.font(); font.setPointSize(7); p.setFont(font)
        p.setPen(_GREY)
        p.drawText(QRectF(x0, y0 - 13, px + 40, 11), Qt.AlignLeft,
                   f"{metres} m")

    @staticmethod
    def _north(p: QPainter, x: float, y: float) -> None:
        shaft = 14.0
        tip   = QPointF(x, y)
        base  = QPointF(x, y + shaft)
        p.setPen(QPen(_GREY, 1))
        p.drawLine(base, tip)
        _arrowhead(p, base, tip, _GREY, size=6)
        font = p.font(); font.setPointSize(7); p.setFont(font)
        p.setPen(_GREY)
        p.drawText(QRectF(x - 5, y + shaft + 1, 10, 10), Qt.AlignCenter, "N")


class BatteryDiagram(QWidget):
    """Plan view of the whole platoon: every piece + every section's PDF.

    - Pieces are dots labeled with their name (green=base, blue=slave,
      grey=unassigned to any section).
    - For every section, a coloured arrow is drawn from every member piece
      in the section's PDF direction.
    - An optional `highlight_group` name draws that section's arrows thicker.
    """

    _PAD       = 36
    _GUN_R     = 7
    _ARROW_LEN = 60

    def __init__(self, peloton: Peloton, parent=None) -> None:
        super().__init__(parent)
        self.peloton = peloton
        self.highlight_group: str | None = None
        self.setMinimumHeight(220)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_highlight(self, group_name: str | None) -> None:
        self.highlight_group = group_name
        self.update()

    # ------------------------------------------------------------------ paint
    def paintEvent(self, event) -> None:  # type: ignore[override]
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), _BG)

        w, h = float(self.width()), float(self.height())
        pieces = list(self.peloton.pieces)

        if not pieces:
            p.setPen(_GREY)
            p.drawText(self.rect(), Qt.AlignCenter,
                       "No pieces yet — Add piece…")
            self._north(p, w - 18.0, 14.0)
            return

        # ---- coordinate → screen mapping ----
        es = [pc.position.easting  for pc in pieces]
        ns = [pc.position.northing for pc in pieces]
        ce = sum(es) / len(es)
        cn = sum(ns) / len(ns)
        span = max(
            (max(es) - min(es)) if len(pieces) > 1 else 0.0,
            (max(ns) - min(ns)) if len(pieces) > 1 else 0.0,
            100.0,
        )
        usable = min(w, h) - 2.0 * self._PAD
        scale  = usable / span
        cx, cy = w / 2.0, h / 2.0

        def sc(e: float, n: float) -> QPointF:
            return QPointF(cx + (e - ce) * scale,
                           cy - (n - cn) * scale)

        # ---- PDF arrows per section (behind guns) ----
        for gi, group in enumerate(self.peloton.groups):
            color = _SECTION_COLORS[gi % len(_SECTION_COLORS)]
            is_hi = (group.name == self.highlight_group)
            pen_w = 3 if is_hi else 2
            p.setPen(QPen(color, pen_w))
            rad = group.pdf_mils * 2.0 * math.pi / 6400.0
            udx =  math.sin(rad)
            udy = -math.cos(rad)
            length = self._ARROW_LEN if is_hi else int(self._ARROW_LEN * 0.85)
            for pname in group.member_names:
                pc = next((x for x in pieces if x.name == pname), None)
                if pc is None:
                    continue
                origin = sc(pc.position.easting, pc.position.northing)
                tip    = QPointF(origin.x() + udx * length,
                                 origin.y() + udy * length)
                p.drawLine(origin, tip)
                _arrowhead(p, origin, tip, color,
                           size=10 if is_hi else 8)

        # ---- gun symbols ----
        for pc in pieces:
            pos = sc(pc.position.easting, pc.position.northing)
            in_section = self.peloton.group_of(pc.name) is not None
            if pc.is_base:
                color = _GREEN
            elif in_section:
                color = _BLUE
            else:
                color = _GREY
            p.setBrush(QBrush(color))
            p.setPen(QPen(_FG, 1))
            p.drawEllipse(pos, float(self._GUN_R), float(self._GUN_R))
            font = p.font(); font.setPointSize(8); p.setFont(font)
            p.setPen(_FG)
            p.drawText(QPointF(pos.x() + self._GUN_R + 3, pos.y() + 4), pc.name)

        # ---- decorations ----
        self._north(p, w - 18.0, 14.0)
        self._scale_bar(p, scale, h)
        self._legend(p, w, h)

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _scale_bar(p: QPainter, scale: float, h: float) -> None:
        for metres in (1000, 500, 200, 100, 50, 20, 10):
            px = metres * scale
            if px >= 28:
                break
        else:
            return
        x0, y0 = 70.0, h - 22.0
        p.setPen(QPen(_GREY, 2))
        p.drawLine(QPointF(x0, y0), QPointF(x0 + px, y0))
        p.drawLine(QPointF(x0,      y0 - 3), QPointF(x0,      y0 + 3))
        p.drawLine(QPointF(x0 + px, y0 - 3), QPointF(x0 + px, y0 + 3))
        font = p.font(); font.setPointSize(7); p.setFont(font)
        p.setPen(_GREY)
        p.drawText(QRectF(x0, y0 - 13, px + 40, 11), Qt.AlignLeft, f"{metres} m")

    @staticmethod
    def _north(p: QPainter, x: float, y: float) -> None:
        shaft = 14.0
        tip   = QPointF(x, y)
        base  = QPointF(x, y + shaft)
        p.setPen(QPen(_GREY, 1))
        p.drawLine(base, tip)
        _arrowhead(p, base, tip, _GREY, size=6)
        font = p.font(); font.setPointSize(7); p.setFont(font)
        p.setPen(_GREY)
        p.drawText(QRectF(x - 5, y + shaft + 1, 10, 10), Qt.AlignCenter, "N")

    def _legend(self, p: QPainter, w: float, h: float) -> None:
        font = p.font(); font.setPointSize(7); p.setFont(font)
        x = w - 6
        y = h - 6
        # piece legend along bottom-right (right→left)
        for label, color in (
            ("● unassigned", _GREY),
            ("● slave", _BLUE),
            ("● basisstuk", _GREEN),
        ):
            p.setPen(color)
            r = p.fontMetrics().boundingRect(label)
            p.drawText(QPointF(x - r.width(), y), label)
            x -= r.width() + 10
        # PDF colour key bottom-left
        x = 8
        font.setPointSize(7); p.setFont(font)
        for gi, group in enumerate(self.peloton.groups):
            color = _SECTION_COLORS[gi % len(_SECTION_COLORS)]
            label = f"▶ {group.name} {int(group.pdf_mils)} mils"
            p.setPen(color)
            r = p.fontMetrics().boundingRect(label)
            p.drawText(QPointF(x, y), label)
            x += r.width() + 12
            if x > w - 240:
                break


def _arrowhead(p: QPainter, start: QPointF, tip: QPointF,
               color: QColor, size: int = 9) -> None:
    dx = tip.x() - start.x()
    dy = tip.y() - start.y()
    length = math.hypot(dx, dy)
    if length < 1.0:
        return
    ux, uy = dx / length, dy / length
    left  = QPointF(tip.x() - size * ux + size * 0.42 * uy,
                    tip.y() - size * uy - size * 0.42 * ux)
    right = QPointF(tip.x() - size * ux - size * 0.42 * uy,
                    tip.y() - size * uy + size * 0.42 * ux)
    p.setBrush(QBrush(color))
    p.setPen(Qt.NoPen)
    p.drawPolygon(QPolygonF([tip, left, right]))
