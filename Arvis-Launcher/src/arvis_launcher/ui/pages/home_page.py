"""
Home page - Main control panel
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, TYPE_CHECKING

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QProgressBar,
    QFrame,
    QGroupBox,
    QTextEdit,
    QMessageBox,
    QSizePolicy,
)

from ...config import LauncherConfig
from ...process import ClientProcess
from ...installer import Installer
from ...updater import UpdateManager, ReleaseInfo
from ...styles import (
    COLORS,
    PAGE_TITLE_STYLE,
    PAGE_SUBTITLE_STYLE,
    PRIMARY_BUTTON_STYLE,
    SECONDARY_BUTTON_STYLE,
    DANGER_BUTTON_STYLE,
    SUCCESS_BUTTON_STYLE,
    PROGRESS_BAR_STYLE,
    STATUS_LABEL_STYLE,
    GROUP_BOX_STYLE,
)


class HomePage(QWidget):
    """Home page with main controls"""
    
    def __init__(
        self,
        config: LauncherConfig,
        client_process: ClientProcess,
        installer: Installer,
        update_manager: UpdateManager,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.config = config
        self.client_process = client_process
        self.installer = installer
        self.update_manager = update_manager
        
        self._is_installed = False
        self._pending_update: Optional[ReleaseInfo] = None
        
        self._build_ui()
        self._connect_signals()
    
    def _build_ui(self):
        """Build the home page UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)
        
        # Header
        header = QWidget()
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(4)
        
        title = QLabel("Arvis AI Assistant")
        title.setStyleSheet(PAGE_TITLE_STYLE)
        header_layout.addWidget(title)
        
        self.subtitle = QLabel("Персональный AI-ассистент")
        self.subtitle.setStyleSheet(PAGE_SUBTITLE_STYLE)
        header_layout.addWidget(self.subtitle)
        
        layout.addWidget(header)
        
        # Status card
        self._build_status_card()
        layout.addWidget(self.status_card)
        
        # Control buttons
        self._build_controls()
        layout.addWidget(self.controls_widget)
        
        # Progress section (hidden by default)
        self._build_progress_section()
        layout.addWidget(self.progress_widget)
        self.progress_widget.hide()
        
        # Update notification (hidden by default)
        self._build_update_notification()
        layout.addWidget(self.update_widget)
        self.update_widget.hide()
        
        # News section
        self._build_news_section()
        layout.addWidget(self.news_widget, 1)
    
    def _build_status_card(self):
        """Build status indicator card"""
        self.status_card = QFrame()
        self.status_card.setObjectName("card")
        self.status_card.setStyleSheet(f"""
            QFrame#card {{
                background-color: {COLORS['bg_secondary']};
                border: 1px solid {COLORS['border']};
                border-radius: 12px;
                padding: 16px;
            }}
        """)
        
        layout = QHBoxLayout(self.status_card)
        layout.setContentsMargins(20, 16, 20, 16)
        
        # Status indicator
        status_layout = QVBoxLayout()
        status_layout.setSpacing(4)
        
        status_title = QLabel("Статус")
        status_title.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
        status_layout.addWidget(status_title)
        
        self.status_label = QLabel("● Остановлен")
        self.status_label.setStyleSheet(STATUS_LABEL_STYLE["stopped"])
        self.status_label.setFont(self.status_label.font())
        status_layout.addWidget(self.status_label)
        
        layout.addLayout(status_layout)
        layout.addStretch()
        
        # Client path
        path_layout = QVBoxLayout()
        path_layout.setSpacing(4)
        
        path_title = QLabel("Путь к клиенту")
        path_title.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
        path_layout.addWidget(path_title)
        
        client_root = self.config.get_client_root()
        path_text = str(client_root) if client_root else "Не настроен"
        self.path_label = QLabel(path_text)
        self.path_label.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 13px;")
        path_layout.addWidget(self.path_label)
        
        layout.addLayout(path_layout)
    
    def _build_controls(self):
        """Build control buttons"""
        self.controls_widget = QWidget()
        layout = QHBoxLayout(self.controls_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        
        # Main launch button
        self.btn_launch = QPushButton("▶  Запустить Arvis")
        self.btn_launch.setStyleSheet(PRIMARY_BUTTON_STYLE)
        self.btn_launch.setMinimumHeight(50)
        self.btn_launch.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.btn_launch)
        
        # Stop button
        self.btn_stop = QPushButton("⏹  Остановить")
        self.btn_stop.setStyleSheet(DANGER_BUTTON_STYLE)
        self.btn_stop.setMinimumHeight(50)
        self.btn_stop.setMinimumWidth(140)
        self.btn_stop.setEnabled(False)
        layout.addWidget(self.btn_stop)
        
        # Install button (shown when not installed)
        self.btn_install = QPushButton("📦  Установить")
        self.btn_install.setStyleSheet(SUCCESS_BUTTON_STYLE)
        self.btn_install.setMinimumHeight(50)
        self.btn_install.setMinimumWidth(140)
        layout.addWidget(self.btn_install)
    
    def _build_progress_section(self):
        """Build progress indicator section"""
        self.progress_widget = QWidget()
        layout = QVBoxLayout(self.progress_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet(PROGRESS_BAR_STYLE)
        self.progress_bar.setMinimumHeight(24)
        layout.addWidget(self.progress_bar)
        
        # Progress label
        self.progress_label = QLabel("Подготовка...")
        self.progress_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
        layout.addWidget(self.progress_label)
    
    def _build_update_notification(self):
        """Build update notification banner"""
        self.update_widget = QFrame()
        self.update_widget.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(100, 150, 255, 0.1);
                border: 1px solid {COLORS['accent']};
                border-radius: 8px;
            }}
        """)
        
        layout = QHBoxLayout(self.update_widget)
        layout.setContentsMargins(16, 12, 16, 12)
        
        # Info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        
        self.update_title = QLabel("🔄 Доступно обновление")
        self.update_title.setStyleSheet(f"color: {COLORS['accent']}; font-weight: bold;")
        info_layout.addWidget(self.update_title)
        
        self.update_desc = QLabel("Новая версия готова к установке")
        self.update_desc.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
        info_layout.addWidget(self.update_desc)
        
        layout.addLayout(info_layout, 1)
        
        # Update button
        self.btn_update = QPushButton("Обновить")
        self.btn_update.setStyleSheet(SECONDARY_BUTTON_STYLE)
        layout.addWidget(self.btn_update)
    
    def _build_news_section(self):
        """Build news/changelog section"""
        self.news_widget = QGroupBox("Новости и обновления")
        self.news_widget.setStyleSheet(GROUP_BOX_STYLE)
        
        layout = QVBoxLayout(self.news_widget)
        layout.setContentsMargins(12, 16, 12, 12)
        
        self.news_text = QTextEdit()
        self.news_text.setReadOnly(True)
        self.news_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: transparent;
                border: none;
                color: {COLORS['text_secondary']};
                font-size: 13px;
            }}
        """)
        self.news_text.setHtml("""
            <h3 style="color: white;">Добро пожаловать в Arvis!</h3>
            <p>Arvis — это ваш персональный AI-ассистент с голосовым управлением.</p>
            <h4 style="color: white;">Быстрый старт:</h4>
            <ol>
                <li>Нажмите <b>Установить</b> для первой настройки</li>
                <li>Перейдите в <b>Модели</b> для загрузки AI-моделей</li>
                <li>Нажмите <b>Запустить Arvis</b> для начала работы</li>
            </ol>
            <p style="color: #888;">Версия 1.0.0 • Декабрь 2025</p>
        """)
        layout.addWidget(self.news_text)
    
    def _connect_signals(self):
        """Connect button signals"""
        self.btn_launch.clicked.connect(self._on_launch)
        self.btn_stop.clicked.connect(self._on_stop)
        self.btn_install.clicked.connect(self._on_install)
        self.btn_update.clicked.connect(self._on_update)
    
    def set_installed(self, installed: bool):
        """Set installation state"""
        self._is_installed = installed
        self.btn_launch.setEnabled(installed)
        self.btn_install.setVisible(not installed)
        
        if installed:
            self.status_label.setText("● Остановлен")
            self.status_label.setStyleSheet(STATUS_LABEL_STYLE["stopped"])
        else:
            self.status_label.setText("● Не установлен")
            self.status_label.setStyleSheet(STATUS_LABEL_STYLE["error"])
    
    def on_client_state_changed(self, state: str):
        """Handle client state changes"""
        states = {
            "stopped": ("● Остановлен", "stopped"),
            "starting": ("● Запускается...", "starting"),
            "running": ("● Работает", "running"),
        }
        
        text, style_key = states.get(state, ("● Неизвестно", "stopped"))
        self.status_label.setText(text)
        self.status_label.setStyleSheet(STATUS_LABEL_STYLE[style_key])
        
        running = state in ("running", "starting")
        self.btn_launch.setEnabled(not running and self._is_installed)
        self.btn_stop.setEnabled(running)
    
    def on_install_progress(self, percent: int, message: str):
        """Handle installation progress"""
        self.progress_widget.show()
        self.progress_bar.setValue(percent)
        self.progress_label.setText(message)
    
    def on_install_finished(self, success: bool, message: str):
        """Handle installation completion"""
        self.progress_widget.hide()
        
        if success:
            self._is_installed = True
            self.btn_install.hide()
            self.btn_launch.setEnabled(True)
            self.status_label.setText("● Остановлен")
            self.status_label.setStyleSheet(STATUS_LABEL_STYLE["stopped"])
            
            QMessageBox.information(self, "Установка завершена", message)
        else:
            QMessageBox.warning(self, "Ошибка установки", message)
    
    def on_update_available(self, release: ReleaseInfo):
        """Handle update availability"""
        self._pending_update = release
        self.update_title.setText(f"🔄 Доступна версия {release.version}")
        self.update_desc.setText(f"Опубликовано: {release.published_date}")
        self.update_widget.show()
        
        # Update news with changelog
        if release.body:
            self.news_text.setHtml(f"""
                <h3 style="color: white;">Обновление {release.version}</h3>
                <p style="color: #888;">{release.published_date}</p>
                <div>{release.body.replace(chr(10), '<br>')}</div>
            """)
    
    def _on_launch(self):
        """Handle launch button click"""
        client_root = self.config.get_client_root()
        if not client_root:
            QMessageBox.warning(self, "Ошибка", "Путь к клиенту не настроен")
            return
        
        result = self.client_process.start(client_root)
        if not result.ok:
            QMessageBox.warning(self, "Ошибка запуска", result.error)
    
    def _on_stop(self):
        """Handle stop button click"""
        self.client_process.stop()
    
    def _on_install(self):
        """Handle install button click"""
        client_root = self.config.get_client_root()
        if not client_root:
            QMessageBox.warning(self, "Ошибка", "Путь к клиенту не настроен")
            return
        
        # Ask about full installation
        reply = QMessageBox.question(
            self,
            "Установка зависимостей",
            "Установить полный набор зависимостей?\n\n"
            "• Да — все возможности (больше места)\n"
            "• Нет — только базовые функции",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
        )
        
        if reply == QMessageBox.StandardButton.Cancel:
            return
        
        full_install = reply == QMessageBox.StandardButton.Yes
        
        self.btn_install.setEnabled(False)
        self.btn_launch.setEnabled(False)
        self.installer.install(client_root, full=full_install)
    
    def _on_update(self):
        """Handle update button click"""
        if not self._pending_update:
            return
        
        client_root = self.config.get_client_root()
        if not client_root:
            return
        
        reply = QMessageBox.question(
            self,
            "Обновление",
            f"Установить версию {self._pending_update.version}?\n\n"
            "Ваши настройки и данные будут сохранены.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        self.btn_update.setEnabled(False)
        self.update_manager.progress.connect(self.on_install_progress)
        self.update_manager.update_finished.connect(self._on_update_finished)
        self.update_manager.download_update(client_root)
    
    def _on_update_finished(self, success: bool, message: str):
        """Handle update completion"""
        self.progress_widget.hide()
        self.btn_update.setEnabled(True)
        
        if success:
            self.update_widget.hide()
            self._pending_update = None
            QMessageBox.information(self, "Обновление завершено", message)
        else:
            QMessageBox.warning(self, "Ошибка обновления", message)
