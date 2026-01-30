"""
Arvis Launcher - Main application entry point
"""

from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

from arvis_launcher.config import LauncherConfig
from arvis_launcher.ui import LauncherMainWindow


def parse_args() -> dict:
    """Parse command line arguments"""
    args = {
        "minimized": False,
        "auto_start": False,
    }
    
    for arg in sys.argv[1:]:
        if arg in ("--minimized", "-m"):
            args["minimized"] = True
        elif arg in ("--auto-start", "-a"):
            args["auto_start"] = True
    
    return args


def main() -> int:
    """Main entry point for Arvis Launcher"""
    
    # Parse command line arguments
    args = parse_args()
    
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
    
    # Create main window
    window = LauncherMainWindow(config)
    
    # Show window (minimized if --minimized flag is set)
    if args["minimized"]:
        window.showMinimized()
    else:
        window.show()
    
    # Auto-start client if configured and --auto-start flag is set OR config says so
    should_auto_start = args["auto_start"] or (args["minimized"] and config.startup.auto_start_client)
    if should_auto_start:
        # Delay auto-start to let the window initialize
        QTimer.singleShot(1500, lambda: _auto_start_client(window, config))
    
    return app.exec()


def _auto_start_client(window: LauncherMainWindow, config: LauncherConfig):
    """Auto-start the Arvis client"""
    try:
        client_root = config.get_client_root()
        if client_root and client_root.exists():
            result = window.client_process.start(client_root)
            if not result.ok:
                window.debug_page.append_log(f"[AUTO-START] Failed: {result.error}")
            else:
                window.debug_page.append_log("[AUTO-START] Client started successfully")
    except Exception as e:
        window.debug_page.append_log(f"[AUTO-START] Error: {e}")


if __name__ == "__main__":
    sys.exit(main())
