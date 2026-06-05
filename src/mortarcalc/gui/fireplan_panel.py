"""Tab 'Fire Plan' — beheer van voorbereide doelen (incl. FPF) en quick-engage."""
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Callable

from PySide6.QtCore import Qt, QTimer, QDateTime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, QDoubleSpinBox,
    QSpinBox, QPushButton, QGroupBox, QComboBox, QMessageBox, QLabel,
    QTableWidget, QTableWidgetItem, QAbstractItemView, QCheckBox, QSplitter,
    QDateTimeEdit,
)

from ..ballistics import FireTable
from ..battery import Peloton, PlannedTarget, KNOWN_SHELLS, shell_label, normalise_shell
from ..geo import mgrs_to_utm
from ..geo.current_location import get_current_position, LocationUnavailable
from .coord_dialog import prompt_position
from ..firemission import (
    FireMission, MethodOfFire, Sheaf, TargetType, Fuze, FireControl,
    Observer, TargetByGrid, solve_mission,
)


SHEAF_OPTIONS = ["converged", "parallel", "linear"]
TYPE_OPTIONS = ["point", "area", "linear"]
FUZE_OPTIONS = ["quick", "delay", "vt", "time", "illum"]


class FirePlanPanel(QWidget):
    """Beheer fire plan + quick-engage door FM aan te maken."""

    def __init__(
        self,
        peloton: Peloton,
        firetable: FireTable,
        engage_callback: Callable[[FireMission, list], None],
        archive_callback: Callable[[str], object] | None = None,
    ) -> None:
        super().__init__()
        self.peloton = peloton
        self.firetable = firetable
        self.engage_callback = engage_callback
        self.archive_callback = archive_callback

        root = QVBoxLayout(self)
        root.addWidget(self._build_hhour_group())
        root.addWidget(self._build_table_group(), stretch=2)
        root.addWidget(self._build_form_group(), stretch=1)

        # Live refresh van schedule-status (countdown / ACTIVE / PAST)
        self._tick_timer = QTimer(self)
        self._tick_timer.timeout.connect(self._refresh_schedule_only)
        self._tick_timer.start(1000)

    def _build_hhour_group(self) -> QGroupBox:
        box = QGroupBox("H-hour (reference time for all plan timings)")
        layout = QHBoxLayout(box)
        self.h_edit = QDateTimeEdit()
        self.h_edit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.h_edit.setCalendarPopup(True)
        self.h_edit.setDateTime(QDateTime.currentDateTime())
        b_set = QPushButton("Set H-hour")
        b_set.clicked.connect(self._set_h_hour)
        b_now = QPushButton("Now")
        b_now.clicked.connect(self._h_hour_now)
        b_clear = QPushButton("Clear")
        b_clear.clicked.connect(self._clear_h_hour)
        self.h_status = QLabel("H-hour: not set")
        self.h_status.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.h_edit)
        layout.addWidget(b_set); layout.addWidget(b_now); layout.addWidget(b_clear)
        layout.addStretch(1)
        layout.addWidget(self.h_status)
        return box

    def _set_h_hour(self) -> None:
        py = self.h_edit.dateTime().toPython()
        # interpreteer als lokale tijd → naar timezone-aware UTC
        if py.tzinfo is None:
            py = py.astimezone()
        self.peloton.h_hour = py
        self.refresh()

    def _h_hour_now(self) -> None:
        now = datetime.now().astimezone()
        self.peloton.h_hour = now
        self.h_edit.setDateTime(QDateTime.currentDateTime())
        self.refresh()

    def _clear_h_hour(self) -> None:
        self.peloton.h_hour = None
        self.refresh()

    def _build_table_group(self) -> QGroupBox:
        box = QGroupBox("Fire plan — preplotted targets")
        wrap = QVBoxLayout(box)
        self.table = QTableWidget(0, 12)
        self.table.setHorizontalHeaderLabels([
            "#", "Name", "MGRS", "Alt", "Description", "Type",
            "Munition/Fuze", "Sheaf/Rounds", "FPF",
            "Timing", "Scheduled", "Status",
        ])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.itemSelectionChanged.connect(self._load_selected_into_form)
        wrap.addWidget(self.table)

        btns = QHBoxLayout()
        b_del = QPushButton("Remove selected")
        b_del.clicked.connect(self._delete_selected)
        b_reset = QPushButton("Reset fire plan")
        b_reset.clicked.connect(self._reset_plan)

        b_engage = QPushButton("Engage selected target")
        b_engage.setStyleSheet("font-weight: bold;")
        b_engage.clicked.connect(self._engage_selected)

        self.engage_group_combo = QComboBox()
        self.engage_fo_call = QLineEdit(); self.engage_fo_call.setPlaceholderText("FO call sign")
        self.engage_fo_mgrs = QLineEdit(); self.engage_fo_mgrs.setPlaceholderText("FO MGRS")
        self.engage_fo_alt = QDoubleSpinBox(); self.engage_fo_alt.setRange(-500, 9000); self.engage_fo_alt.setSuffix(" m")

        engage_row = QHBoxLayout()
        engage_row.addWidget(QLabel("Section:")); engage_row.addWidget(self.engage_group_combo)
        engage_row.addWidget(QLabel("FO:")); engage_row.addWidget(self.engage_fo_call)
        engage_row.addWidget(self.engage_fo_mgrs); engage_row.addWidget(self.engage_fo_alt)
        engage_row.addWidget(b_engage)
        wrap.addLayout(engage_row)
        bot_row = QHBoxLayout(); bot_row.addWidget(b_del); bot_row.addStretch(1); bot_row.addWidget(b_reset)
        wrap.addLayout(bot_row)
        return box

    def _build_form_group(self) -> QGroupBox:
        box = QGroupBox("Add / edit target")
        form = QFormLayout(box)
        self.f_name = QLineEdit(); self.f_name.setPlaceholderText("bv. AB1001")
        self.f_mgrs = QLineEdit(); self.f_mgrs.setPlaceholderText("MGRS"); self.f_mgrs.setMinimumWidth(200)
        self.f_alt = QDoubleSpinBox(); self.f_alt.setRange(-500, 9000); self.f_alt.setSuffix(" m")
        b_loc = QPushButton("Current location"); b_loc.clicked.connect(self._fill_loc)
        mgrs_row = QHBoxLayout(); mgrs_row.addWidget(self.f_mgrs, 1); mgrs_row.addWidget(b_loc)

        self.f_desc = QLineEdit(); self.f_desc.setPlaceholderText("bv. kruispunt N9 / kerk")
        self.f_type = QComboBox(); self.f_type.addItems(TYPE_OPTIONS)
        self.f_shell = QComboBox(); self.f_shell.setEditable(True)
        for s in KNOWN_SHELLS:
            self.f_shell.addItem(shell_label(s), s)
        self.f_fuze = QComboBox(); self.f_fuze.addItems(FUZE_OPTIONS)
        self.f_sheaf = QComboBox(); self.f_sheaf.addItems(SHEAF_OPTIONS)
        self.f_rounds = QSpinBox(); self.f_rounds.setRange(1, 50); self.f_rounds.setValue(3)
        self.f_group = QComboBox(); self.f_group.setEditable(True)
        self.f_fpf = QCheckBox("FPF (Final Protective Fire)")

        # voor LINEAR
        self.f_line_az = QDoubleSpinBox(); self.f_line_az.setRange(0, 6399); self.f_line_az.setSuffix(" mils")
        self.f_line_len = QDoubleSpinBox(); self.f_line_len.setRange(0, 5000); self.f_line_len.setValue(200); self.f_line_len.setSuffix(" m")
        # timings
        self.f_on_call = QCheckBox("On Call (no fixed timing)")
        self.f_on_call.setChecked(True)
        self.f_offset = QSpinBox(); self.f_offset.setRange(-720, 720); self.f_offset.setSuffix(" min rel. to H")
        self.f_offset.setEnabled(False)
        self.f_duration = QSpinBox(); self.f_duration.setRange(0, 240); self.f_duration.setSuffix(" min")
        self.f_on_call.toggled.connect(lambda chk: self.f_offset.setEnabled(not chk))

        form.addRow("Name", self.f_name)
        form.addRow("MGRS", mgrs_row)
        form.addRow("Altitude", self.f_alt)
        form.addRow("Description", self.f_desc)
        form.addRow("Target type", self.f_type)
        form.addRow("Munition", self.f_shell)
        form.addRow("Fuze", self.f_fuze)
        form.addRow("Sheaf", self.f_sheaf)
        form.addRow("Rounds/piece", self.f_rounds)
        form.addRow("Suggested section", self.f_group)
        form.addRow(self.f_on_call)
        form.addRow("Timing", self.f_offset)
        form.addRow("Duration (sustained)", self.f_duration)
        form.addRow(self.f_fpf)

        btn_row = QHBoxLayout()
        b_add = QPushButton("Add / update"); b_add.clicked.connect(self._add_or_update)
        b_clear = QPushButton("Clear fields"); b_clear.clicked.connect(self._clear_form)
        btn_row.addWidget(b_add); btn_row.addWidget(b_clear); btn_row.addStretch(1)
        form.addRow(btn_row)

        # LINEAR parameters — shown only when target type is "linear"
        self.f_linear_box = QGroupBox("LINEAR parameters")
        lin_form = QFormLayout(self.f_linear_box)
        lin_form.addRow("Line azimuth", self.f_line_az)
        lin_form.addRow("Line length", self.f_line_len)
        self.f_linear_box.setVisible(False)
        self.f_type.currentTextChanged.connect(
            lambda t: self.f_linear_box.setVisible(t == "linear")
        )
        form.addRow(self.f_linear_box)
        return box

    # ---------- acties ----------
    def _fill_loc(self) -> None:
        try:
            pos = get_current_position()
        except LocationUnavailable as e:
            ret = QMessageBox.question(
                self, "GPS unavailable",
                f"{e}\n\nEnter coordinates manually?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes,
            )
            if ret != QMessageBox.Yes:
                return
            pos = prompt_position(self)
            if pos is None:
                return
        self.f_mgrs.setText(pos.to_mgrs()); self.f_alt.setValue(pos.altitude_m)

    def _add_or_update(self) -> None:
        name = self.f_name.text().strip()
        if not name:
            QMessageBox.information(self, "Name", "Provide a name (e.g. AB1001)."); return
        try:
            pos = mgrs_to_utm(self.f_mgrs.text().strip(), altitude_m=self.f_alt.value())
        except Exception as e:
            QMessageBox.warning(self, "MGRS", str(e)); return
        # update bestaand of nieuw
        existing = next((t for t in self.peloton.fire_plan if t.name == name), None)
        target = PlannedTarget(
            name=name, position=pos,
            description=self.f_desc.text().strip(),
            target_type=self.f_type.currentText(),
            shell=self._shell_value(),
            fuze=self.f_fuze.currentText(),
            sheaf=self.f_sheaf.currentText(),
            rounds_per_piece=self.f_rounds.value(),
            suggested_group=self.f_group.currentText().strip(),
            is_fpf=self.f_fpf.isChecked(),
            line_azimuth_mils=self.f_line_az.value(),
            line_length_m=self.f_line_len.value(),
            start_offset_min=None if self.f_on_call.isChecked() else self.f_offset.value(),
            duration_min=self.f_duration.value(),
        )
        if existing is not None:
            idx = self.peloton.fire_plan.index(existing)
            self.peloton.fire_plan[idx] = target
        else:
            self.peloton.fire_plan.append(target)
        self.refresh()

    def _shell_value(self) -> str:
        """Read the shell combobox as a canonical upper-case string."""
        data = self.f_shell.currentData()
        if isinstance(data, str) and data:
            return normalise_shell(data)
        return normalise_shell(self.f_shell.currentText()) or "HE"

    def _clear_form(self) -> None:
        for w in (self.f_name, self.f_mgrs, self.f_desc):
            w.clear()
        # Reset shell combo to HE (index 0)
        if self.f_shell.count():
            self.f_shell.setCurrentIndex(0)
        self.f_alt.setValue(0); self.f_rounds.setValue(3)
        self.f_type.setCurrentIndex(0); self.f_fuze.setCurrentIndex(0); self.f_sheaf.setCurrentIndex(0)
        self.f_fpf.setChecked(False)
        self.f_line_az.setValue(0); self.f_line_len.setValue(200)
        self.f_group.setCurrentIndex(0) if self.f_group.count() else None
        self.f_linear_box.setVisible(False)

    def _reset_plan(self) -> None:
        if not self.peloton.fire_plan and self.peloton.h_hour is None:
            return
        if QMessageBox.question(
            self, "Reset fire plan",
            "Archive current state and remove all planned targets + H-hour?\n"
            "Snapshot saved under Archives → Browse archives.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        ) != QMessageBox.Yes:
            return
        if self.archive_callback is not None:
            try: self.archive_callback("before_reset_plan")
            except Exception: pass
        self.peloton.fire_plan.clear()
        self.peloton.h_hour = None
        self.refresh()

    def _delete_selected(self) -> None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self.peloton.fire_plan):
            return
        del self.peloton.fire_plan[row]
        self.refresh()

    def _load_selected_into_form(self) -> None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self.peloton.fire_plan):
            return
        t = self.peloton.fire_plan[row]
        self.f_name.setText(t.name)
        self.f_mgrs.setText(t.position.to_mgrs())
        self.f_alt.setValue(t.position.altitude_m)
        self.f_desc.setText(t.description)
        idx = TYPE_OPTIONS.index(t.target_type) if t.target_type in TYPE_OPTIONS else 0
        self.f_type.setCurrentIndex(idx)
        # Shell — match by data, else use raw text in editable combo
        sh_norm = normalise_shell(t.shell)
        found = False
        for i in range(self.f_shell.count()):
            if normalise_shell(str(self.f_shell.itemData(i) or "")) == sh_norm:
                self.f_shell.setCurrentIndex(i); found = True; break
        if not found:
            self.f_shell.setEditText(t.shell)
        self.f_fuze.setCurrentIndex(FUZE_OPTIONS.index(t.fuze) if t.fuze in FUZE_OPTIONS else 0)
        self.f_sheaf.setCurrentIndex(SHEAF_OPTIONS.index(t.sheaf) if t.sheaf in SHEAF_OPTIONS else 0)
        self.f_rounds.setValue(t.rounds_per_piece)
        self.f_group.setCurrentText(t.suggested_group)
        self.f_fpf.setChecked(t.is_fpf)
        self.f_line_az.setValue(t.line_azimuth_mils)
        self.f_line_len.setValue(t.line_length_m)
        self.f_linear_box.setVisible(t.target_type == "linear")
        self.f_on_call.setChecked(t.start_offset_min is None)
        if t.start_offset_min is not None:
            self.f_offset.setValue(t.start_offset_min)
        self.f_duration.setValue(t.duration_min)
        # default engage-groep ook updaten
        if t.suggested_group:
            i = self.engage_group_combo.findText(t.suggested_group)
            if i >= 0:
                self.engage_group_combo.setCurrentIndex(i)

    def _engage_selected(self) -> None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self.peloton.fire_plan):
            QMessageBox.information(self, "Selection", "Select a target first."); return
        if self.engage_group_combo.count() == 0:
            QMessageBox.information(self, "Section", "No sections available."); return
        group_name = self.engage_group_combo.currentText()
        t = self.peloton.fire_plan[row]
        try:
            fo_pos = mgrs_to_utm(self.engage_fo_mgrs.text().strip(),
                                 altitude_m=self.engage_fo_alt.value())
        except Exception as e:
            QMessageBox.warning(self, "FO MGRS", f"Enter a valid FO position.\n{e}"); return
        fm = FireMission(
            id=self.peloton.allocate_fm_id(),
            group_name=group_name,
            observer=Observer(call_sign=self.engage_fo_call.text().strip() or "FO", position=fo_pos),
            target_spec=TargetByGrid(position=t.position),
            target_description=f"{t.name} {t.description}".strip(),
            target_type=_enum_or_default(TargetType, t.target_type, TargetType.POINT),
            shell=t.shell,
            fuze=_enum_or_default(Fuze, t.fuze, Fuze.QUICK),
            method_of_fire=MethodOfFire.FFE if not t.is_fpf else MethodOfFire.FPF,
            sheaf=_enum_or_default(Sheaf, t.sheaf, Sheaf.CONVERGED),
            rounds_per_piece=t.rounds_per_piece,
            control=FireControl.WHEN_READY,
            line_azimuth_mils=t.line_azimuth_mils,
            line_length_m=t.line_length_m,
        )
        try:
            sols = solve_mission(fm, self.peloton, self.firetable)
        except Exception as e:
            QMessageBox.critical(self, "Computation failed", str(e)); return
        fm.note(f"Engaged from fire plan: {t.name}")
        self.engage_callback(fm, sols)
        QMessageBox.information(self, "Engaged", f"FM created for {t.name} on section {group_name}.\nSee 'Fire Missions' tab.")

    # ---------- refresh ----------
    def refresh(self) -> None:
        # Sync h_edit met peloton.h_hour
        if self.peloton.h_hour is not None:
            qdt = QDateTime.fromString(
                self.peloton.h_hour.astimezone().strftime("%Y-%m-%d %H:%M:%S"),
                "yyyy-MM-dd HH:mm:ss",
            )
            if qdt.isValid():
                self.h_edit.setDateTime(qdt)
        # update group combo
        prev = self.engage_group_combo.currentText()
        self.engage_group_combo.clear()
        self.engage_group_combo.addItems([g.name for g in self.peloton.groups])
        if prev:
            i = self.engage_group_combo.findText(prev)
            if i >= 0:
                self.engage_group_combo.setCurrentIndex(i)
        prev_g = self.f_group.currentText()
        self.f_group.clear()
        self.f_group.addItem("")  # leeg (geen voorkeur)
        self.f_group.addItems([g.name for g in self.peloton.groups])
        if prev_g:
            self.f_group.setCurrentText(prev_g)
        # H-hour status-label
        if self.peloton.h_hour is not None:
            local = self.peloton.h_hour.astimezone()
            self.h_status.setText(f"H-hour: {local.strftime('%Y-%m-%d %H:%M:%S')}")
            self.h_status.setStyleSheet("font-weight: bold; color: #2ecc71;")
        else:
            self.h_status.setText("H-hour: not set")
            self.h_status.setStyleSheet("font-weight: bold; color: #aaa;")

        # Chronologisch sorteren: gevulde timings eerst (vroegst → laatst), on-call achteraan
        def _sort_key(t):
            return (0, t.start_offset_min) if t.start_offset_min is not None else (1, 0)

        ordered = sorted(self.peloton.fire_plan, key=_sort_key)
        # zorg dat de underliggende lijst dezelfde volgorde houdt (zodat _engage/delete op row-index klopt)
        self.peloton.fire_plan[:] = ordered

        self.table.setRowCount(len(ordered))
        now_aware = datetime.now().astimezone()
        for i, t in enumerate(ordered):
            self.table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            name_item = QTableWidgetItem(t.name)
            if t.is_fpf:
                name_item.setForeground(Qt.red)
            self.table.setItem(i, 1, name_item)
            self.table.setItem(i, 2, QTableWidgetItem(t.position.to_mgrs()))
            self.table.setItem(i, 3, QTableWidgetItem(f"{t.position.altitude_m:.0f}"))
            self.table.setItem(i, 4, QTableWidgetItem(t.description))
            self.table.setItem(i, 5, QTableWidgetItem(t.target_type))
            self.table.setItem(i, 6, QTableWidgetItem(f"{t.shell} / {t.fuze}"))
            extra = ""
            if t.sheaf == "linear":
                extra = f" · az{t.line_azimuth_mils:.0f}/{t.line_length_m:.0f}m"
            self.table.setItem(i, 7, QTableWidgetItem(f"{t.sheaf} · {t.rounds_per_piece}rnd{extra}"))
            self.table.setItem(i, 8, QTableWidgetItem("FPF" if t.is_fpf else ""))

            timing_label = t.offset_label()
            if t.duration_min > 0:
                timing_label += f" ({t.duration_min}m)"
            self.table.setItem(i, 9, QTableWidgetItem(timing_label))

            sched = t.scheduled_start(self.peloton.h_hour)
            sched_str = sched.astimezone().strftime("%H:%M:%S") if sched else "—"
            self.table.setItem(i, 10, QTableWidgetItem(sched_str))

            status_str, color = self._status_text(t, now_aware)
            status_item = QTableWidgetItem(status_str)
            if color is not None:
                status_item.setForeground(color)
            self.table.setItem(i, 11, status_item)

    def _refresh_schedule_only(self) -> None:
        """Lichte refresh elke seconde: enkel timing-status kolommen."""
        if self.peloton.h_hour is None and not self.peloton.fire_plan:
            return
        now_aware = datetime.now().astimezone()
        for i, t in enumerate(self.peloton.fire_plan):
            if i >= self.table.rowCount():
                break
            text, color = self._status_text(t, now_aware)
            item = self.table.item(i, 11)
            if item is None:
                item = QTableWidgetItem(text)
                self.table.setItem(i, 11, item)
            else:
                item.setText(text)
            if color is not None:
                item.setForeground(color)

    def _status_text(self, t, now_aware):
        from PySide6.QtGui import QColor
        if t.start_offset_min is None:
            return ("On Call", QColor("#888"))
        h = self.peloton.h_hour
        if h is None:
            return ("(H-hour ?)", QColor("#888"))
        sched = t.scheduled_start(h)
        diff = (sched - now_aware).total_seconds()
        st = t.status_at(now_aware, h)
        if st == "SCHEDULED":
            mins, secs = divmod(int(diff), 60)
            return (f"in {mins:02d}:{secs:02d}", QColor("#3498db"))
        if st == "DUE":
            return ("DUE — NOW", QColor("#f1c40f"))
        if st == "ACTIVE":
            end = t.scheduled_end(h)
            rem = (end - now_aware).total_seconds()
            mins, secs = divmod(int(max(0, rem)), 60)
            return (f"ACTIVE ({mins:02d}:{secs:02d} left)", QColor("#e74c3c"))
        return ("PAST", QColor("#666"))

    def showEvent(self, ev) -> None:  # type: ignore[override]
        self.refresh()
        super().showEvent(ev)


def _enum_or_default(enum_cls, value: str, default):
    try:
        return enum_cls(value)
    except ValueError:
        return default
