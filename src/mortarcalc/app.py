"""Application entry-point — wires up autosave + crash recovery."""
from __future__ import annotations

import sys
from importlib.resources import files

from PySide6.QtWidgets import QApplication, QMessageBox

from .ballistics import load_firetable
from .battery import Peloton
from .gui.main_window import MainWindow
from .state import StateRepository


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("MortarCalc")
    app.setOrganizationName("MortarCalc")

    firetable_path = files("mortarcalc.data.firetables").joinpath("m821_81mm_he.json")
    firetable = load_firetable(str(firetable_path))

    autosave = StateRepository()
    peloton = Peloton()

    if autosave.exists():
        ret = QMessageBox.question(
            None, "Restore previous session?",
            f"An autosave was found:\n{autosave.path}\n\n"
            "Restore the previous session (pieces, fire plan, active and "
            "completed fire missions)?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes,
        )
        if ret == QMessageBox.Yes:
            try:
                loaded_pel, history, active = autosave.load()
                peloton = loaded_pel
                window = MainWindow(peloton=peloton, firetable=firetable, autosave=autosave)
                window.history_panel.set_history(history)
                window.mission_panel.restore_active(active)
                window.show()
                return app.exec()
            except Exception as e:
                QMessageBox.warning(None, "Restore failed",
                                    f"Could not load autosave:\n{e}\n\nStarting fresh.")
                peloton = Peloton()

    window = MainWindow(peloton=peloton, firetable=firetable, autosave=autosave)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
