from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication

from arvis_launcher.config import LauncherConfig
from arvis_launcher.ui.main_window import LauncherMainWindow


def main() -> int:
    app = QApplication(sys.argv)
    cfg = LauncherConfig.load()
    win = LauncherMainWindow(cfg)
    win.show()
    return int(app.exec())
