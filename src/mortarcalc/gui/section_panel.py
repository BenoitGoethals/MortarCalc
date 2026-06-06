"""Tab 'Platoon & Lay': pieces, aiming points, sections (groups) + 'lay on watch'."""
from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QFormLayout, QLineEdit, QPushButton, QDoubleSpinBox, QGroupBox,
    QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, QMessageBox,
    QListWidget, QListWidgetItem, QAbstractItemView,
    QSplitter, QDialog, QDialogButtonBox,
)

from ..battery import Peloton, Group
from .position_diagram import BatteryDiagram
from .piece_dialog import AddPieceDialog, AddAimingPointDialog
from .section_dialog import EditSectionDialog


class SectionPanel(QWidget):
    """Main tab for platoon configuration."""

    def __init__(
        self,
        peloton: Peloton,
        on_changed: Callable[[], None],
        archive_callback: Callable[[str], object] | None = None,
    ) -> None:
        super().__init__()
        self.peloton = peloton
        self.on_changed = on_changed
        self.archive_callback = archive_callback

        splitter = QSplitter(Qt.Horizontal)
        left = QWidget(); left_layout = QVBoxLayout(left)
        left_layout.addWidget(self._build_pieces_group())
        left_layout.addWidget(self._build_aiming_points_group())
        left_layout.addStretch(1)
        splitter.addWidget(left)
        right = QWidget(); right_layout = QVBoxLayout(right)
        right_layout.addWidget(self._build_groups_panel(), stretch=1)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        root = QVBoxLayout(self)
        root.addWidget(splitter)

    # ---------- pieces ----------
    def _build_pieces_group(self) -> QGroupBox:
        box = QGroupBox("Pieces (1–4)")
        wrap = QVBoxLayout(box)

        btns = QHBoxLayout()
        b_add = QPushButton("Add piece…"); b_add.clicked.connect(self._add_piece)
        b_edit = QPushButton("Edit selected…"); b_edit.clicked.connect(self._edit_piece)
        b_del = QPushButton("Remove selected"); b_del.clicked.connect(self._remove_piece)
        b_reset = QPushButton("Reset all"); b_reset.clicked.connect(self._reset_pieces)
        btns.addWidget(b_add); btns.addWidget(b_edit); btns.addWidget(b_del)
        btns.addStretch(1); btns.addWidget(b_reset)

        self.pieces_table = QTableWidget(0, 6)
        self.pieces_table.setHorizontalHeaderLabels(
            ["Name", "MGRS", "Altitude", "Base", "Section", "Ammunition"]
        )
        self.pieces_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.pieces_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.pieces_table.verticalHeader().setVisible(False)
        self.pieces_table.cellDoubleClicked.connect(
            lambda row, _col: self._edit_piece_row(row)
        )
        wrap.addLayout(btns); wrap.addWidget(self.pieces_table)
        return box

    def _add_piece(self) -> None:
        dlg = AddPieceDialog(self.peloton, self)
        if dlg.exec() != QDialog.Accepted or dlg.result_piece is None:
            return
        try:
            self.peloton.add_piece(dlg.result_piece)
        except ValueError as e:
            QMessageBox.warning(self, "Piece", str(e)); return
        for shell, count in dlg.result_ammo.items():
            self.peloton.set_ammo(dlg.result_piece.name, shell, count)
        self._refresh_all()

    def _edit_piece(self) -> None:
        rows = {i.row() for i in self.pieces_table.selectedIndexes()}
        if len(rows) != 1:
            QMessageBox.information(
                self, "Edit piece", "Select exactly one piece to edit."
            )
            return
        self._edit_piece_row(next(iter(rows)))

    def _edit_piece_row(self, row: int) -> None:
        item = self.pieces_table.item(row, 0)
        if item is None:
            return
        name = item.text()
        try:
            piece = self.peloton.piece(name)
        except KeyError:
            return
        ammo = dict(self.peloton.ammo.get(name, {}))
        dlg = AddPieceDialog(self.peloton, self, piece=piece, ammo=ammo)
        if dlg.exec() != QDialog.Accepted or dlg.result_piece is None:
            return
        try:
            self.peloton.update_piece(name, dlg.result_piece)
        except ValueError as e:
            QMessageBox.warning(self, "Piece", str(e)); return
        for shell, count in dlg.result_ammo.items():
            self.peloton.set_ammo(dlg.result_piece.name, shell, count)
        self._refresh_all()

    def _remove_piece(self) -> None:
        rows = {i.row() for i in self.pieces_table.selectedIndexes()}
        for r in sorted(rows, reverse=True):
            name = self.pieces_table.item(r, 0).text()
            self.peloton.remove_piece(name)
        self._refresh_all()

    # ---------- aiming points ----------
    def _build_aiming_points_group(self) -> QGroupBox:
        box = QGroupBox("Aiming Points (shared across all sections)")
        wrap = QVBoxLayout(box)
        btns = QHBoxLayout()
        b_add = QPushButton("Add aiming point…"); b_add.clicked.connect(self._add_ap)
        b_reset = QPushButton("Reset all"); b_reset.clicked.connect(self._reset_aps)
        btns.addWidget(b_add); btns.addStretch(1); btns.addWidget(b_reset)
        self.ap_table = QTableWidget(0, 3)
        self.ap_table.setHorizontalHeaderLabels(["Name", "MGRS", "Altitude"])
        self.ap_table.verticalHeader().setVisible(False)
        wrap.addLayout(btns); wrap.addWidget(self.ap_table)
        return box

    def _add_ap(self) -> None:
        dlg = AddAimingPointDialog(self.peloton, self)
        if dlg.exec() != QDialog.Accepted or dlg.result_ap is None:
            return
        try:
            self.peloton.add_aiming_point(dlg.result_ap)
        except ValueError as e:
            QMessageBox.warning(self, "Aiming point", str(e)); return
        self._refresh_all()

    def _archive_then(self, label: str) -> bool:
        if self.archive_callback is None:
            return True
        try:
            self.archive_callback(label)
        except Exception:
            return False
        return True

    def _confirm_reset(self, what: str) -> bool:
        return QMessageBox.question(
            self, f"Reset {what}",
            f"Archive current state and remove all {what}?\n"
            "Snapshot will be saved under Archives → Browse archives.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        ) == QMessageBox.Yes

    def _reset_pieces(self) -> None:
        if not self.peloton.pieces:
            return
        if not self._confirm_reset("pieces"):
            return
        self._archive_then("before_reset_pieces")
        self.peloton.pieces.clear()
        self.peloton.ammo.clear()
        for g in self.peloton.groups:
            g.member_names.clear()
        self._refresh_all()

    def _reset_aps(self) -> None:
        if not self.peloton.aiming_points:
            return
        if not self._confirm_reset("aiming points"):
            return
        self._archive_then("before_reset_aps")
        self.peloton.aiming_points.clear()
        self._refresh_all()

    def _reset_groups(self) -> None:
        if not self.peloton.groups:
            return
        if not self._confirm_reset("sections"):
            return
        self._archive_then("before_reset_sections")
        self.peloton.groups.clear()
        self._refresh_all()

    # ---------- sections (groups) ----------
    def _build_groups_panel(self) -> QGroupBox:
        box = QGroupBox("Fire Sections — select a section, then Edit")
        wrap = QVBoxLayout(box)

        btn_row = QHBoxLayout()
        b_new = QPushButton("New section…"); b_new.clicked.connect(self._add_group)
        self.b_edit_sec = QPushButton("Edit selected…"); self.b_edit_sec.clicked.connect(self._edit_selected_group)
        self.b_del_sec = QPushButton("Delete selected"); self.b_del_sec.clicked.connect(self._delete_selected_group)
        b_reset_sec = QPushButton("Reset sections"); b_reset_sec.clicked.connect(self._reset_groups)
        btn_row.addWidget(b_new); btn_row.addWidget(self.b_edit_sec); btn_row.addWidget(self.b_del_sec)
        btn_row.addStretch(1); btn_row.addWidget(b_reset_sec)
        wrap.addLayout(btn_row)

        # Selectable section list — pick one, then edit/delete it.
        self.groups_list = QListWidget()
        self.groups_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.groups_list.setMaximumHeight(160)
        self.groups_list.itemSelectionChanged.connect(self._on_group_selection_changed)
        self.groups_list.itemDoubleClicked.connect(self._open_group_dialog)
        wrap.addWidget(self.groups_list)

        # Always-visible battery diagram
        self.battery_diagram = BatteryDiagram(self.peloton)
        wrap.addWidget(self.battery_diagram, stretch=1)
        return box

    def _selected_group_name(self) -> str | None:
        items = self.groups_list.selectedItems()
        if not items:
            return None
        return items[0].data(Qt.UserRole)

    def _on_group_selection_changed(self) -> None:
        name = self._selected_group_name()
        self.b_edit_sec.setEnabled(name is not None)
        self.b_del_sec.setEnabled(name is not None)
        # Highlight the picked section's arrows in the battery diagram.
        self.battery_diagram.set_highlight(name)
        self.battery_diagram.update()

    def _edit_selected_group(self) -> None:
        name = self._selected_group_name()
        if name is None:
            QMessageBox.information(self, "Edit section", "Select a section first.")
            return
        self._open_group_dialog_by_name(name)

    def _delete_selected_group(self) -> None:
        name = self._selected_group_name()
        if name is None:
            QMessageBox.information(self, "Delete section", "Select a section first.")
            return
        if QMessageBox.question(
            self, "Delete section",
            f"Delete section '{name}'? Pieces become unassigned.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        ) != QMessageBox.Yes:
            return
        self.peloton.remove_group(name)
        self._refresh_all()

    def _add_group(self) -> None:
        dlg = QDialog(self)
        dlg.setWindowTitle("New section")
        dlg.setModal(True)
        form = QFormLayout(dlg)
        name_edit = QLineEdit()
        name_edit.setPlaceholderText("e.g. North, Section 1")
        name_edit.setMinimumWidth(220)
        pdf_spin = QDoubleSpinBox()
        pdf_spin.setRange(0, 6399); pdf_spin.setSuffix(" mils"); pdf_spin.setDecimals(0)
        form.addRow("Name", name_edit)
        form.addRow("Primary Direction of Fire", pdf_spin)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        name_edit.returnPressed.connect(dlg.accept)
        form.addRow(buttons)
        if dlg.exec() != QDialog.Accepted:
            return
        name = name_edit.text().strip()
        if not name:
            QMessageBox.information(self, "Name", "Provide a section name.")
            return
        try:
            self.peloton.add_group(Group(name=name, pdf_mils=pdf_spin.value()))
        except ValueError as e:
            QMessageBox.warning(self, "Section", str(e))
            return
        self._refresh_all()

    def _open_group_dialog(self, item: QListWidgetItem) -> None:
        self._open_group_dialog_by_name(item.data(Qt.UserRole))

    def _open_group_dialog_by_name(self, name: str) -> None:
        try:
            group = self.peloton.group(name)
        except KeyError:
            return
        # Highlight that section's arrows in the battery diagram while editing
        self.battery_diagram.set_highlight(name)
        dlg = EditSectionDialog(
            peloton=self.peloton,
            group=group,
            on_changed=self._refresh_all,
            parent=self,
        )
        dlg.exec()
        self.battery_diagram.set_highlight(None)
        self._refresh_all()

    # ---------- refresh ----------
    def _refresh_all(self) -> None:
        self._refresh_pieces_table()
        self._refresh_ap_table()
        self._refresh_groups_list()
        self.battery_diagram.update()
        self.on_changed()

    def _refresh_pieces_table(self) -> None:
        from ..battery import KNOWN_SHELLS
        self.pieces_table.setRowCount(len(self.peloton.pieces))
        thresh = self.peloton.low_ammo_threshold
        for i, p in enumerate(self.peloton.pieces):
            g = self.peloton.group_of(p.name)
            self.pieces_table.setItem(i, 0, QTableWidgetItem(p.name))
            self.pieces_table.setItem(i, 1, QTableWidgetItem(p.position.to_mgrs()))
            self.pieces_table.setItem(i, 2, QTableWidgetItem(f"{p.position.altitude_m:.0f} m"))
            self.pieces_table.setItem(i, 3, QTableWidgetItem("yes" if p.is_base else ""))
            self.pieces_table.setItem(i, 4, QTableWidgetItem(g.name if g else "—"))
            # Per-shell breakdown — show only shells with non-zero stock,
            # plus HE always so users see "HE 0" rather than no info.
            stocks = self.peloton.ammo.get(p.name, {})
            parts: list[str] = []
            seen: set[str] = set()
            for shell in KNOWN_SHELLS:
                if shell == "HE" or stocks.get(shell, 0) > 0:
                    parts.append(f"{shell} {stocks.get(shell, 0)}")
                    seen.add(shell)
            for shell, count in stocks.items():
                if shell not in seen and count > 0:
                    parts.append(f"{shell} {count}")
            ammo_item = QTableWidgetItem(" · ".join(parts))
            he = stocks.get("HE", 0)
            if he <= thresh:
                ammo_item.setForeground(Qt.red)
                ammo_item.setToolTip(f"HE ≤ {thresh} (low-ammo threshold)")
            self.pieces_table.setItem(i, 5, ammo_item)

    def _refresh_ap_table(self) -> None:
        self.ap_table.setRowCount(len(self.peloton.aiming_points))
        for i, ap in enumerate(self.peloton.aiming_points):
            self.ap_table.setItem(i, 0, QTableWidgetItem(ap.name))
            self.ap_table.setItem(i, 1, QTableWidgetItem(ap.position.to_mgrs()))
            self.ap_table.setItem(i, 2, QTableWidgetItem(f"{ap.position.altitude_m:.0f} m"))

    def _refresh_groups_list(self) -> None:
        prev = self._selected_group_name()
        self.groups_list.blockSignals(True)
        self.groups_list.clear()
        if not self.peloton.groups:
            placeholder = QListWidgetItem("(no sections — click 'New section…')")
            placeholder.setForeground(Qt.gray)
            placeholder.setFlags(Qt.NoItemFlags)
            self.groups_list.addItem(placeholder)
            self.groups_list.blockSignals(False)
            self._on_group_selection_changed()
            return
        for g in self.peloton.groups:
            item = QListWidgetItem(
                f"  {g.name}  ·  PDF {g.pdf_mils:.0f} mils  ·  "
                f"{len(g.member_names)} pc(s)"
            )
            item.setData(Qt.UserRole, g.name)
            item.setToolTip("Double-click to edit, or select and use the buttons above")
            self.groups_list.addItem(item)
            if g.name == prev:
                item.setSelected(True)
                self.groups_list.setCurrentItem(item)
        self.groups_list.blockSignals(False)
        self._on_group_selection_changed()

    def showEvent(self, ev) -> None:  # type: ignore[override]
        self._refresh_all()
        super().showEvent(ev)
