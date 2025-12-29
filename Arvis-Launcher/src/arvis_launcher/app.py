"""
Arvis Launcher - Main application entry point
"""

from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from arvis_launcher.config import LauncherConfig
from arvis_launcher.ui import LauncherMainWindow


def main() -> int:
    """Main entry point for Arvis Launcher"""
    
    # High DPI support
    try:
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
    except AttributeError:
        pass
    
    app = QApplication(sys.argv)
    
    # Set application info
    app.setApplicationName("Arvis Launcher")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("Arvis")
    
    # Set default font
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    # Load configuration
    config = LauncherConfig.load()
    
    # Create and show main window
    window = LauncherMainWindow(config)
    window.show()
    
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
