from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication

from .config import LauncherConfig
from .ui.main_window import LauncherMainWindow


def main() -> int:
    app = QApplication(sys.argv)
    cfg = LauncherConfig.load()
    win = LauncherMainWindow(cfg)
    win.show()
    return int(app.exec())
