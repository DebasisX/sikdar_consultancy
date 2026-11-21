"""Entry point."""
from __future__ import annotations

import ctypes
import os
import sys
import tempfile
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from sikdar import paths
from sikdar.context import AppContext
from sikdar.ui import icons, theme
from sikdar.ui.brand import app_icon
from sikdar.ui.main_window import MainWindow
from sikdar.ui.widgets import PopupPolishFilter


def build_stylesheet() -> str:
    chevron = Path(tempfile.gettempdir()) / "sikdar_chevron.png"
    icons.pixmap("chevron-down", theme.TEXT_2, 14).save(str(chevron), "PNG")
    return theme.QSS.replace("@@CHEVRON@@", chevron.as_posix())


def main() -> int:
    if sys.platform == "win32":
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("SikdarConsultancy.App")
        except Exception:  # noqa: BLE001
            pass
    app = QApplication(sys.argv)
    app.setApplicationName(paths.APP_NAME)
    app.setOrganizationName(paths.APP_NAME)
    app.setWindowIcon(app_icon())
    app.setStyle("Fusion")
    font = QFont("Segoe UI Variable Text")
    font.setStyleHint(QFont.SansSerif)
    font.setPixelSize(13)
    app.setFont(font)
    app.setStyleSheet(build_stylesheet())
    popup_filter = PopupPolishFilter(app)
    app.installEventFilter(popup_filter)

    ctx = AppContext()
    win = MainWindow(ctx)
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
