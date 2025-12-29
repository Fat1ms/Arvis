"""
Main window for Arvis Launcher
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, QTimer, QPoint
from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QFrame,
    QSizePolicy,
)

from ..config import LauncherConfig
from ..process import ClientProcess
from ..installer import Installer
from ..ollama_manager import OllamaManager
from ..updater import UpdateManager, get_local_version
from ..session import SessionManager
from ..migration import SettingsMigrator
from ..voice_models import VoiceModelsManager
from ..i18n import tr, set_language
from ..styles import (
    COLORS,
    get_global_stylesheet,
    TITLE_BAR_STYLE,
    TITLE_LABEL_STYLE,
    WINDOW_BUTTON_STYLE,
    CLOSE_BUTTON_STYLE,
    NAV_PANEL_STYLE,
    NAV_BUTTON_STYLE,
    SEPARATOR_STYLE,
)

from .pages.home_page import HomePage
from .pages.models_page import ModelsPage
from .pages.settings_page import SettingsPage
from .pages.debug_page import DebugPage
from .pages.account_page import AccountPage
from .dialogs import MigrationDialog


class LauncherMainWindow(QMainWindow):
    """Main launcher window"""
    
    def __init__(self, config: LauncherConfig):
        super().__init__()
        self.config = config
        
        # Set language from config
        set_language(config.language)
        
        # Initialize managers
        self.session_manager = SessionManager(self)
        self.client_process = ClientProcess(self.session_manager, self)
        self.installer = Installer(self)
        self.ollama_manager = OllamaManager(self)
        self.update_manager = UpdateManager(self)
        
        # Voice models manager (needs models dir)
        models_dir = config.get_models_dir()
        self.voice_manager = VoiceModelsManager(models_dir, self)
        
        # Window setup
        self.setWindowTitle(tr("app.title"))
        self.setMinimumSize(900, 550)
        self.resize(config.window.width, config.window.height)
        
        # Set window icon
        self._set_window_icon()
        
        # Frameless window
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        
        # Apply global styles
        self.setStyleSheet(get_global_stylesheet())
        
        # For window dragging
        self._drag_pos: Optional[QPoint] = None
        
        # Build UI
        self._build_ui()
        self._connect_signals()
        
        # Initial state
        QTimer.singleShot(100, self._on_startup)
    
    def _set_window_icon(self):
        """Set window icon from resources"""
        import sys
        
        # Find icon file based on whether we're frozen (PyInstaller) or running as script
        if getattr(sys, 'frozen', False):
            # Running as compiled .exe
            base_path = Path(sys._MEIPASS)
            icon_paths = [
                base_path / "resources" / "arvis_launcher.ico",
                base_path / "resources" / "arvis_launcher.png",
            ]
        else:
            # Running as script
            base_path = Path(__file__).parent.parent.parent.parent
            icon_paths = [
                base_path / "resources" / "arvis_launcher.ico",
                base_path / "resources" / "arvis_launcher.png",
            ]
        
        for icon_path in icon_paths:
            if icon_path.exists():
                self.setWindowIcon(QIcon(str(icon_path)))
                break
    
    def _build_ui(self):
        """Build the main UI"""
        central = QWidget()
        self.setCentralWidget(central)
        
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Title bar
        self._build_title_bar()
        main_layout.addWidget(self.title_bar)
        
        # Separator
        separator = QFrame()
        separator.setFixedHeight(1)
        separator.setStyleSheet(f"background-color: {COLORS['border']};")
        main_layout.addWidget(separator)
        
        # Content area (nav + pages)
        content = QWidget()
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        # Navigation panel
        self._build_nav_panel()
        content_layout.addWidget(self.nav_panel)
        
        # Pages stack
        self._build_pages()
        content_layout.addWidget(self.pages_stack, 1)
        
        main_layout.addWidget(content, 1)
    
    def _build_title_bar(self):
        """Build custom title bar"""
        self.title_bar = QWidget()
        self.title_bar.setObjectName("title_bar")
        self.title_bar.setFixedHeight(32)
        self.title_bar.setStyleSheet(TITLE_BAR_STYLE)
        
        layout = QHBoxLayout(self.title_bar)
        layout.setContentsMargins(10, 4, 4, 4)
        layout.setSpacing(3)
        
        # Title
        self.title_label = QLabel("Arvis Launcher")
        self.title_label.setStyleSheet(TITLE_LABEL_STYLE)
        layout.addWidget(self.title_label)
        
        layout.addStretch()
        
        # Window controls
        self.btn_minimize = QPushButton("─")
        self.btn_maximize = QPushButton("□")
        self.btn_close = QPushButton("×")
        
        self.btn_minimize.setStyleSheet(WINDOW_BUTTON_STYLE)
        self.btn_maximize.setStyleSheet(WINDOW_BUTTON_STYLE)
        self.btn_close.setStyleSheet(CLOSE_BUTTON_STYLE)
        
        self.btn_minimize.setFixedSize(24, 24)
        self.btn_maximize.setFixedSize(24, 24)
        self.btn_close.setFixedSize(24, 24)
        
        layout.addWidget(self.btn_minimize)
        layout.addWidget(self.btn_maximize)
        layout.addWidget(self.btn_close)
        
        # Connect
        self.btn_minimize.clicked.connect(self.showMinimized)
        self.btn_maximize.clicked.connect(self._toggle_maximize)
        self.btn_close.clicked.connect(self.close)
        
        # Make draggable
        self.title_bar.mousePressEvent = self._title_mouse_press
        self.title_bar.mouseMoveEvent = self._title_mouse_move
        self.title_bar.mouseDoubleClickEvent = lambda e: self._toggle_maximize()
    
    def _build_nav_panel(self):
        """Build navigation panel"""
        self.nav_panel = QWidget()
        self.nav_panel.setObjectName("nav_panel")
        self.nav_panel.setFixedWidth(200)
        self.nav_panel.setStyleSheet(NAV_PANEL_STYLE)
        
        layout = QVBoxLayout(self.nav_panel)
        layout.setContentsMargins(8, 12, 8, 12)
        layout.setSpacing(4)
        
        # Navigation buttons
        self.nav_buttons = []
        nav_items = [
            (tr("nav.home"), 0),
            (tr("nav.models"), 1),
            (tr("nav.settings"), 2),
            (tr("nav.account"), 3),
            (tr("nav.debug"), 4),
        ]
        
        for text, index in nav_items:
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setStyleSheet(NAV_BUTTON_STYLE)
            btn.clicked.connect(lambda checked, i=index: self._navigate_to(i))
            layout.addWidget(btn)
            self.nav_buttons.append(btn)
        
        layout.addStretch()
        
        # Version info at bottom
        version_label = QLabel("v1.0.0")
        version_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version_label)
        
        # Set first button checked
        self.nav_buttons[0].setChecked(True)
    
    def _build_pages(self):
        """Build page stack"""
        self.pages_stack = QStackedWidget()
        
        # Create pages
        self.home_page = HomePage(
            self.config,
            self.client_process,
            self.installer,
            self.update_manager,
            self
        )
        self.models_page = ModelsPage(self.config, self.ollama_manager, self.voice_manager, self)
        self.settings_page = SettingsPage(self.config, self)
        self.account_page = AccountPage(self.session_manager, self)
        self.debug_page = DebugPage(self.config, self.client_process, self)
        
        self.pages_stack.addWidget(self.home_page)
        self.pages_stack.addWidget(self.models_page)
        self.pages_stack.addWidget(self.settings_page)
        self.pages_stack.addWidget(self.account_page)
        self.pages_stack.addWidget(self.debug_page)
    
    def _connect_signals(self):
        """Connect all signals"""
        # Client process
        self.client_process.output_line.connect(self.debug_page.append_log)
        self.client_process.state_changed.connect(self.home_page.on_client_state_changed)
        
        # Installer
        self.installer.progress.connect(self.home_page.on_install_progress)
        self.installer.log_line.connect(self.debug_page.append_log)
        self.installer.finished.connect(self.home_page.on_install_finished)
        
        # Ollama
        self.ollama_manager.log_line.connect(self.debug_page.append_log)
        self.ollama_manager.state_changed.connect(self.models_page.on_ollama_state_changed)
        self.ollama_manager.models_updated.connect(self.models_page.on_models_updated)
        
        # Voice models
        self.voice_manager.log_line.connect(self.debug_page.append_log)
        self.voice_manager.models_updated.connect(self.models_page.on_voice_models_updated)
        self.voice_manager.progress.connect(self._on_voice_progress)
        self.voice_manager.operation_finished.connect(self._on_voice_finished)
        
        # Update manager
        self.update_manager.update_available.connect(self.home_page.on_update_available)
        self.update_manager.log_line.connect(self.debug_page.append_log)
    
    def _on_voice_progress(self, percent: int, message: str):
        """Handle voice model download progress"""
        self.models_page._on_progress(percent, message)
    
    def _on_voice_finished(self, success: bool, message: str):
        """Handle voice model operation finished"""
        self.models_page._on_operation_finished(success, message)
    
    def _navigate_to(self, index: int):
        """Navigate to page by index"""
        # Update button states
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)
        
        self.pages_stack.setCurrentIndex(index)
    
    def _on_startup(self):
        """Called after window is shown"""
        # Check installation status
        client_root = self.config.get_client_root()
        
        if client_root:
            installed = self.installer.is_installed(client_root)
            self.home_page.set_installed(installed)
            self.debug_page.append_log(f"Client root: {client_root}")
            self.debug_page.append_log(f"Installed: {installed}")
            
            # Check if migration is needed (first run with existing client)
            if not self.config.migration_done:
                self._check_migration(client_root)
            
            # Migrate session from client if not logged in yet
            if not self.session_manager.is_logged_in:
                client_config = client_root / "config" / "config.json"
                if self.session_manager.migrate_from_client(client_config):
                    self.debug_page.append_log("Session migrated from client config")
            
            # Check for updates
            if self.config.update.auto_check:
                version = get_local_version(client_root)
                self.update_manager.check_for_updates(
                    self.config.update.github_repo,
                    version,
                    self.config.update.branch == "dev"
                )
        else:
            self.debug_page.append_log("WARNING: client_root is None!")
        # Start Ollama monitoring
        self.ollama_manager.start_monitoring()
    
    def _check_migration(self, client_root: Path):
        """Check and offer migration from client config"""
        migrator = SettingsMigrator(self.config.get_config_path(), self)
        
        if migrator.needs_migration(client_root):
            self.debug_page.append_log("Migration needed - showing dialog")
            dialog = MigrationDialog(
                client_root=client_root,
                launcher_config_path=self.config.get_config_path(),
                parent=self
            )
            if dialog.exec():
                result = dialog.result
                if result and result.success:
                    self.debug_page.append_log(f"Migration complete: {len(result.migrated_keys)} keys")
                    # Mark migration as done
                    self.config.migration_done = True
                    self.config.save()
        else:
            # No migration needed, mark as done
            self.config.migration_done = True
            self.config.save()
    
    def _toggle_maximize(self):
        """Toggle maximized state"""
        if self.isMaximized():
            self.showNormal()
            self.btn_maximize.setText("□")
        else:
            self.showMaximized()
            self.btn_maximize.setText("❐")
    
    def _title_mouse_press(self, event):
        """Handle title bar mouse press for dragging"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
    
    def _title_mouse_move(self, event):
        """Handle title bar mouse move for dragging"""
        if self._drag_pos and event.buttons() == Qt.MouseButton.LeftButton:
            if self.isMaximized():
                self.showNormal()
                self.btn_maximize.setText("□")
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
    
    def closeEvent(self, event):
        """Handle window close"""
        # Save window state
        if not self.isMaximized():
            self.config.window.width = self.width()
            self.config.window.height = self.height()
        
        self.config.save()
        
        # Stop client if running
        if self.client_process.is_running():
            self.client_process.stop()
        
        # Stop Ollama monitoring
        self.ollama_manager.stop_monitoring()
        
        event.accept()
