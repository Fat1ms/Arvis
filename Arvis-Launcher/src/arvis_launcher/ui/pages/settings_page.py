"""
Settings page - Global configuration
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QCheckBox,
    QComboBox,
    QGroupBox,
    QScrollArea,
    QFileDialog,
    QMessageBox,
    QSpinBox,
    QFrame,
    QTextEdit,
)
import json

from ...config import LauncherConfig
from ...styles import (
    COLORS,
    PAGE_TITLE_STYLE,
    PAGE_SUBTITLE_STYLE,
    SECONDARY_BUTTON_STYLE,
    GROUP_BOX_STYLE,
    LINE_EDIT_STYLE,
    CHECK_BOX_STYLE,
    COMBO_BOX_STYLE,
    SCROLL_AREA_STYLE,
)


class SettingsPage(QWidget):
    """Settings page for global configuration"""
    
    def __init__(
        self,
        config: LauncherConfig,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.config = config
        
        self._build_ui()
        self._load_settings()
        self._connect_signals()
    
    def _build_ui(self):
        """Build the settings page UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)
        
        # Header
        title = QLabel("Настройки")
        title.setStyleSheet(PAGE_TITLE_STYLE)
        layout.addWidget(title)
        
        subtitle = QLabel("Глобальные настройки лаунчера и Arvis")
        subtitle.setStyleSheet(PAGE_SUBTITLE_STYLE)
        layout.addWidget(subtitle)
        
        # Scrollable content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(SCROLL_AREA_STYLE + f"""
            QScrollArea {{
                background-color: transparent;
                border: none;
            }}
        """)
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 12, 0)
        content_layout.setSpacing(16)
        
        # User settings section (name, city)
        self._build_user_section(content_layout)
        
        # Language section (UI + speech)
        self._build_language_section(content_layout)
        
        # Paths section
        self._build_paths_section(content_layout)
        
        # Updates section
        self._build_updates_section(content_layout)
        
        # Ollama section
        self._build_ollama_section(content_layout)
        
        # Modules section
        self._build_modules_section(content_layout)
        
        # Extensions section
        self._build_extensions_section(content_layout)
        
        # UI section
        self._build_ui_section(content_layout)
        
        content_layout.addStretch()
        
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)
        
        # Save button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.btn_save = QPushButton("💾  Сохранить настройки")
        self.btn_save.setStyleSheet(SECONDARY_BUTTON_STYLE)
        self.btn_save.setMinimumWidth(180)
        btn_layout.addWidget(self.btn_save)
        
        layout.addLayout(btn_layout)
    
    def _build_user_section(self, parent_layout):
        """Build user settings section (name, city)"""
        group = QGroupBox("👤  Пользователь")
        group.setStyleSheet(GROUP_BOX_STYLE)
        
        layout = QVBoxLayout(group)
        layout.setContentsMargins(16, 20, 16, 16)
        layout.setSpacing(12)
        
        # User name
        row1 = QHBoxLayout()
        row1.setSpacing(8)
        
        label1 = QLabel("Имя:")
        label1.setMinimumWidth(120)
        label1.setStyleSheet(f"color: {COLORS['text_secondary']};")
        row1.addWidget(label1)
        
        self.edit_user_name = QLineEdit()
        self.edit_user_name.setStyleSheet(LINE_EDIT_STYLE)
        self.edit_user_name.setPlaceholderText("Как вас называть")
        row1.addWidget(self.edit_user_name, 1)
        
        layout.addLayout(row1)
        
        # User city
        row2 = QHBoxLayout()
        row2.setSpacing(8)
        
        label2 = QLabel("Город:")
        label2.setMinimumWidth(120)
        label2.setStyleSheet(f"color: {COLORS['text_secondary']};")
        row2.addWidget(label2)
        
        self.edit_user_city = QLineEdit()
        self.edit_user_city.setStyleSheet(LINE_EDIT_STYLE)
        self.edit_user_city.setPlaceholderText("Для прогноза погоды")
        row2.addWidget(self.edit_user_city, 1)
        
        layout.addLayout(row2)
        
        parent_layout.addWidget(group)
    
    def _build_language_section(self, parent_layout):
        """Build language settings section (UI + Speech)"""
        group = QGroupBox("🌐  Язык")
        group.setStyleSheet(GROUP_BOX_STYLE)
        
        layout = QVBoxLayout(group)
        layout.setContentsMargins(16, 20, 16, 16)
        layout.setSpacing(12)
        
        # UI Language
        row1 = QHBoxLayout()
        row1.setSpacing(8)
        
        label1 = QLabel("Интерфейс:")
        label1.setMinimumWidth(120)
        label1.setStyleSheet(f"color: {COLORS['text_secondary']};")
        row1.addWidget(label1)
        
        self.combo_ui_language = QComboBox()
        self.combo_ui_language.setStyleSheet(COMBO_BOX_STYLE)
        self.combo_ui_language.addItem("🇷🇺  Русский", "ru")
        self.combo_ui_language.addItem("🇬🇧  English", "en")
        self.combo_ui_language.addItem("🇺🇦  Українська", "uk")
        self.combo_ui_language.addItem("🇪🇸  Español", "es")
        row1.addWidget(self.combo_ui_language)
        
        note1 = QLabel("(требуется перезапуск)")
        note1.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
        row1.addWidget(note1)
        
        row1.addStretch()
        layout.addLayout(row1)
        
        # Speech Language
        row2 = QHBoxLayout()
        row2.setSpacing(8)
        
        label2 = QLabel("Речь (STT/TTS):")
        label2.setMinimumWidth(120)
        label2.setStyleSheet(f"color: {COLORS['text_secondary']};")
        row2.addWidget(label2)
        
        self.combo_speech_language = QComboBox()
        self.combo_speech_language.setStyleSheet(COMBO_BOX_STYLE)
        self.combo_speech_language.addItem("🇷🇺  Русский", "ru")
        self.combo_speech_language.addItem("🇬🇧  English", "en")
        self.combo_speech_language.addItem("🇺🇦  Українська", "uk")
        self.combo_speech_language.addItem("🇪🇸  Español", "es")
        row2.addWidget(self.combo_speech_language)
        
        row2.addStretch()
        layout.addLayout(row2)
        
        parent_layout.addWidget(group)
    
    def _build_paths_section(self, parent_layout):
        """Build paths configuration section"""
        group = QGroupBox("📁  Пути")
        group.setStyleSheet(GROUP_BOX_STYLE)
        
        layout = QVBoxLayout(group)
        layout.setContentsMargins(16, 20, 16, 16)
        layout.setSpacing(12)
        
        # Client root
        row1 = QHBoxLayout()
        row1.setSpacing(8)
        
        label1 = QLabel("Папка клиента:")
        label1.setMinimumWidth(120)
        label1.setStyleSheet(f"color: {COLORS['text_secondary']};")
        row1.addWidget(label1)
        
        self.edit_client_root = QLineEdit()
        self.edit_client_root.setStyleSheet(LINE_EDIT_STYLE)
        self.edit_client_root.setPlaceholderText("Путь к Arvis Client")
        row1.addWidget(self.edit_client_root, 1)
        
        btn_browse = QPushButton("...")
        btn_browse.setFixedWidth(40)
        btn_browse.setStyleSheet(SECONDARY_BUTTON_STYLE)
        btn_browse.clicked.connect(self._browse_client_root)
        row1.addWidget(btn_browse)
        
        layout.addLayout(row1)
        
        # Models directory
        row2 = QHBoxLayout()
        row2.setSpacing(8)
        
        label2 = QLabel("Папка моделей:")
        label2.setMinimumWidth(120)
        label2.setStyleSheet(f"color: {COLORS['text_secondary']};")
        row2.addWidget(label2)
        
        self.edit_models_dir = QLineEdit()
        self.edit_models_dir.setStyleSheet(LINE_EDIT_STYLE)
        self.edit_models_dir.setPlaceholderText("По умолчанию: client/models")
        row2.addWidget(self.edit_models_dir, 1)
        
        btn_browse2 = QPushButton("...")
        btn_browse2.setFixedWidth(40)
        btn_browse2.setStyleSheet(SECONDARY_BUTTON_STYLE)
        btn_browse2.clicked.connect(self._browse_models_dir)
        row2.addWidget(btn_browse2)
        
        layout.addLayout(row2)
        
        # Client logs directory
        row3 = QHBoxLayout()
        row3.setSpacing(8)

        label3 = QLabel("Папка логов клиента:")
        label3.setMinimumWidth(120)
        label3.setStyleSheet(f"color: {COLORS['text_secondary']};")
        row3.addWidget(label3)

        self.edit_client_logs = QLineEdit()
        self.edit_client_logs.setStyleSheet(LINE_EDIT_STYLE)
        self.edit_client_logs.setPlaceholderText("Путь для логов Arvis Client (client/config.paths.logs)")
        row3.addWidget(self.edit_client_logs, 1)

        btn_browse3 = QPushButton("...")
        btn_browse3.setFixedWidth(40)
        btn_browse3.setStyleSheet(SECONDARY_BUTTON_STYLE)
        btn_browse3.clicked.connect(self._browse_client_logs)
        row3.addWidget(btn_browse3)

        layout.addLayout(row3)
        
        parent_layout.addWidget(group)
    
    def _build_updates_section(self, parent_layout):
        """Build updates configuration section"""
        group = QGroupBox("🔄  Обновления")
        group.setStyleSheet(GROUP_BOX_STYLE)
        
        layout = QVBoxLayout(group)
        layout.setContentsMargins(16, 20, 16, 16)
        layout.setSpacing(12)
        
        # Auto-check
        self.chk_auto_update = QCheckBox("Автоматически проверять обновления")
        self.chk_auto_update.setStyleSheet(CHECK_BOX_STYLE)
        layout.addWidget(self.chk_auto_update)
        
        # Branch selection
        row = QHBoxLayout()
        row.setSpacing(8)
        
        label = QLabel("Ветка обновлений:")
        label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        row.addWidget(label)
        
        self.combo_branch = QComboBox()
        self.combo_branch.setStyleSheet(COMBO_BOX_STYLE)
        self.combo_branch.addItem("Stable (стабильная)", "stable")
        self.combo_branch.addItem("Dev (тестовая)", "dev")
        row.addWidget(self.combo_branch)
        
        row.addStretch()
        layout.addLayout(row)
        
        # GitHub repo
        row2 = QHBoxLayout()
        row2.setSpacing(8)
        
        label2 = QLabel("GitHub репозиторий:")
        label2.setStyleSheet(f"color: {COLORS['text_secondary']};")
        row2.addWidget(label2)
        
        self.edit_repo = QLineEdit()
        self.edit_repo.setStyleSheet(LINE_EDIT_STYLE)
        self.edit_repo.setPlaceholderText("owner/repo")
        row2.addWidget(self.edit_repo, 1)
        
        layout.addLayout(row2)
        
        parent_layout.addWidget(group)
    
    def _build_ollama_section(self, parent_layout):
        """Build Ollama configuration section"""
        group = QGroupBox("🤖  Ollama")
        group.setStyleSheet(GROUP_BOX_STYLE)
        
        layout = QVBoxLayout(group)
        layout.setContentsMargins(16, 20, 16, 16)
        layout.setSpacing(12)
        
        # Auto-install
        self.chk_ollama_auto_install = QCheckBox("Предлагать установку Ollama при первом запуске")
        self.chk_ollama_auto_install.setStyleSheet(CHECK_BOX_STYLE)
        layout.addWidget(self.chk_ollama_auto_install)
        
        # Auto-start
        self.chk_ollama_auto_start = QCheckBox("Автоматически запускать Ollama")
        self.chk_ollama_auto_start.setStyleSheet(CHECK_BOX_STYLE)
        layout.addWidget(self.chk_ollama_auto_start)
        
        # Default model
        row = QHBoxLayout()
        row.setSpacing(8)
        
        label = QLabel("Модель по умолчанию:")
        label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        row.addWidget(label)
        
        self.combo_default_model = QComboBox()
        self.combo_default_model.setStyleSheet(COMBO_BOX_STYLE)
        self.combo_default_model.setEditable(True)
        self.combo_default_model.addItems([
            "gemma2:2b",
            "llama3.2:3b",
            "phi3:mini",
            "mistral:7b",
        ])
        row.addWidget(self.combo_default_model)
        
        row.addStretch()
        layout.addLayout(row)
        
        parent_layout.addWidget(group)
    
    def _build_modules_section(self, parent_layout):
        """Build API keys configuration section"""
        group = QGroupBox("🔑  API Ключи")
        group.setStyleSheet(GROUP_BOX_STYLE)
        
        layout = QVBoxLayout(group)
        layout.setContentsMargins(16, 20, 16, 16)
        layout.setSpacing(12)
        
        # Server API Key
        row1 = QHBoxLayout()
        row1.setSpacing(8)
        
        label1 = QLabel("Сервер:")
        label1.setMinimumWidth(120)
        label1.setStyleSheet(f"color: {COLORS['text_secondary']};")
        row1.addWidget(label1)
        
        self.edit_server_api_key = QLineEdit()
        self.edit_server_api_key.setStyleSheet(LINE_EDIT_STYLE)
        self.edit_server_api_key.setPlaceholderText("API ключ сервера")
        self.edit_server_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        row1.addWidget(self.edit_server_api_key, 1)
        
        layout.addLayout(row1)
        
        # Weather API Key
        row2 = QHBoxLayout()
        row2.setSpacing(8)
        
        label2 = QLabel("Погода:")
        label2.setMinimumWidth(120)
        label2.setStyleSheet(f"color: {COLORS['text_secondary']};")
        row2.addWidget(label2)
        
        self.edit_weather_api_key = QLineEdit()
        self.edit_weather_api_key.setStyleSheet(LINE_EDIT_STYLE)
        self.edit_weather_api_key.setPlaceholderText("OpenWeatherMap API ключ")
        row2.addWidget(self.edit_weather_api_key, 1)
        
        layout.addLayout(row2)
        
        # News API Key
        row3 = QHBoxLayout()
        row3.setSpacing(8)
        
        label3 = QLabel("Новости:")
        label3.setMinimumWidth(120)
        label3.setStyleSheet(f"color: {COLORS['text_secondary']};")
        row3.addWidget(label3)
        
        self.edit_news_api_key = QLineEdit()
        self.edit_news_api_key.setStyleSheet(LINE_EDIT_STYLE)
        self.edit_news_api_key.setPlaceholderText("API ключ для новостей")
        row3.addWidget(self.edit_news_api_key, 1)
        
        layout.addLayout(row3)
        
        # Search API Key
        row4 = QHBoxLayout()
        row4.setSpacing(8)
        
        label4 = QLabel("Поиск (API):")
        label4.setMinimumWidth(120)
        label4.setStyleSheet(f"color: {COLORS['text_secondary']};")
        row4.addWidget(label4)
        
        self.edit_search_api_key = QLineEdit()
        self.edit_search_api_key.setStyleSheet(LINE_EDIT_STYLE)
        self.edit_search_api_key.setPlaceholderText("Google CSE API ключ")
        row4.addWidget(self.edit_search_api_key, 1)
        
        layout.addLayout(row4)
        
        # Search Engine ID
        row5 = QHBoxLayout()
        row5.setSpacing(8)
        
        label5 = QLabel("Поиск (ID):")
        label5.setMinimumWidth(120)
        label5.setStyleSheet(f"color: {COLORS['text_secondary']};")
        row5.addWidget(label5)
        
        self.edit_search_engine_id = QLineEdit()
        self.edit_search_engine_id.setStyleSheet(LINE_EDIT_STYLE)
        self.edit_search_engine_id.setPlaceholderText("Google Search Engine ID")
        row5.addWidget(self.edit_search_engine_id, 1)
        
        layout.addLayout(row5)
        
        parent_layout.addWidget(group)
    
    def _build_extensions_section(self, parent_layout):
        """Build advanced settings: Logging and Ollama server"""
        group = QGroupBox("⚙️  Расширенные")
        group.setStyleSheet(GROUP_BOX_STYLE)
        
        layout = QVBoxLayout(group)
        layout.setContentsMargins(16, 20, 16, 16)
        layout.setSpacing(12)
        
        # Logging subsection
        sub_group = QGroupBox("📝  Логирование")
        sub_group.setStyleSheet(f"""
            QGroupBox {{
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 8px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px;
            }}
        """)
        sub_layout = QVBoxLayout(sub_group)
        sub_layout.setContentsMargins(12, 16, 12, 12)
        sub_layout.setSpacing(10)
        
        # Log level
        row1 = QHBoxLayout()
        row1.setSpacing(8)
        
        label1 = QLabel("Уровень:")
        label1.setMinimumWidth(100)
        label1.setStyleSheet(f"color: {COLORS['text_secondary']};")
        row1.addWidget(label1)
        
        self.combo_log_level = QComboBox()
        self.combo_log_level.setStyleSheet(COMBO_BOX_STYLE)
        self.combo_log_level.addItem("DEBUG", "DEBUG")
        self.combo_log_level.addItem("INFO", "INFO")
        self.combo_log_level.addItem("WARNING", "WARNING")
        self.combo_log_level.addItem("ERROR", "ERROR")
        row1.addWidget(self.combo_log_level)
        
        row1.addStretch()
        sub_layout.addLayout(row1)
        
        # Max size MB
        row2 = QHBoxLayout()
        row2.setSpacing(8)
        
        label2 = QLabel("Макс. размер (МБ):")
        label2.setMinimumWidth(100)
        label2.setStyleSheet(f"color: {COLORS['text_secondary']};")
        row2.addWidget(label2)
        
        self.spin_log_size = QSpinBox()
        self.spin_log_size.setStyleSheet(COMBO_BOX_STYLE)
        self.spin_log_size.setRange(1, 100)
        self.spin_log_size.setValue(10)
        row2.addWidget(self.spin_log_size)
        
        row2.addStretch()
        sub_layout.addLayout(row2)
        
        # Backup count
        row3 = QHBoxLayout()
        row3.setSpacing(8)
        
        label3 = QLabel("Копий логов:")
        label3.setMinimumWidth(100)
        label3.setStyleSheet(f"color: {COLORS['text_secondary']};")
        row3.addWidget(label3)
        
        self.spin_log_backup = QSpinBox()
        self.spin_log_backup.setStyleSheet(COMBO_BOX_STYLE)
        self.spin_log_backup.setRange(1, 20)
        self.spin_log_backup.setValue(5)
        row3.addWidget(self.spin_log_backup)
        
        row3.addStretch()
        sub_layout.addLayout(row3)
        
        # File logging checkbox
        self.chk_file_logging = QCheckBox("Записывать логи в файл")
        self.chk_file_logging.setStyleSheet(CHECK_BOX_STYLE)
        sub_layout.addWidget(self.chk_file_logging)

        # Logs directory
        row4 = QHBoxLayout()
        row4.setSpacing(8)

        label4 = QLabel("Папка логов:")
        label4.setMinimumWidth(100)
        label4.setStyleSheet(f"color: {COLORS['text_secondary']};")
        row4.addWidget(label4)

        self.edit_logs_dir = QLineEdit()
        self.edit_logs_dir.setStyleSheet(LINE_EDIT_STYLE)
        self.edit_logs_dir.setPlaceholderText("Путь к папке с логами (по умолчанию: launcher/logs)")
        row4.addWidget(self.edit_logs_dir, 1)

        btn_browse_logs = QPushButton("...")
        btn_browse_logs.setFixedWidth(40)
        btn_browse_logs.setStyleSheet(SECONDARY_BUTTON_STYLE)
        btn_browse_logs.clicked.connect(self._browse_logs_dir)
        row4.addWidget(btn_browse_logs)

        sub_layout.addLayout(row4)
        
        layout.addWidget(sub_group)
        
        # Ollama server subsection
        ollama_group = QGroupBox("🤖  Ollama Сервер")
        ollama_group.setStyleSheet(f"""
            QGroupBox {{
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 8px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px;
            }}
        """)
        ollama_layout = QVBoxLayout(ollama_group)
        ollama_layout.setContentsMargins(12, 16, 12, 12)
        ollama_layout.setSpacing(10)
        
        # Ollama URL
        row4 = QHBoxLayout()
        row4.setSpacing(8)
        
        label4 = QLabel("URL сервера:")
        label4.setMinimumWidth(100)
        label4.setStyleSheet(f"color: {COLORS['text_secondary']};")
        row4.addWidget(label4)
        
        self.edit_ollama_url = QLineEdit()
        self.edit_ollama_url.setStyleSheet(LINE_EDIT_STYLE)
        self.edit_ollama_url.setPlaceholderText("http://127.0.0.1:11434")
        row4.addWidget(self.edit_ollama_url, 1)
        
        ollama_layout.addLayout(row4)
        
        # Launch mode
        row5 = QHBoxLayout()
        row5.setSpacing(8)
        
        label5 = QLabel("Режим запуска:")
        label5.setMinimumWidth(100)
        label5.setStyleSheet(f"color: {COLORS['text_secondary']};")
        row5.addWidget(label5)
        
        self.combo_ollama_mode = QComboBox()
        self.combo_ollama_mode.setStyleSheet(COMBO_BOX_STYLE)
        self.combo_ollama_mode.addItem("Консоль", "console")
        self.combo_ollama_mode.addItem("Фоновый", "background")
        self.combo_ollama_mode.addItem("Служба", "service")
        row5.addWidget(self.combo_ollama_mode)
        
        row5.addStretch()
        ollama_layout.addLayout(row5)
        
        # Bind address
        row6 = QHBoxLayout()
        row6.setSpacing(8)
        
        label6 = QLabel("Адрес:")
        label6.setMinimumWidth(100)
        label6.setStyleSheet(f"color: {COLORS['text_secondary']};")
        row6.addWidget(label6)
        
        self.edit_ollama_bind = QLineEdit()
        self.edit_ollama_bind.setStyleSheet(LINE_EDIT_STYLE)
        self.edit_ollama_bind.setPlaceholderText("127.0.0.1")
        row6.addWidget(self.edit_ollama_bind, 1)
        
        ollama_layout.addLayout(row6)
        
        # Allow external connections
        self.chk_ollama_external = QCheckBox("Разрешить внешние подключения")
        self.chk_ollama_external.setStyleSheet(CHECK_BOX_STYLE)
        ollama_layout.addWidget(self.chk_ollama_external)
        
        # Auto restart
        self.chk_ollama_auto_restart = QCheckBox("Автоматический перезапуск")
        self.chk_ollama_auto_restart.setStyleSheet(CHECK_BOX_STYLE)
        ollama_layout.addWidget(self.chk_ollama_auto_restart)
        
        layout.addWidget(ollama_group)
        
        parent_layout.addWidget(group)
    
    def _build_ui_section(self, parent_layout):
        """Build UI configuration section"""
        group = QGroupBox("🖥️  Интерфейс")
        group.setStyleSheet(GROUP_BOX_STYLE)
        
        layout = QVBoxLayout(group)
        layout.setContentsMargins(16, 20, 16, 16)
        layout.setSpacing(12)
        
        # Autostart with Windows
        self.chk_autostart_windows = QCheckBox("Запускать лаунчер вместе с Windows")
        self.chk_autostart_windows.setStyleSheet(CHECK_BOX_STYLE)
        layout.addWidget(self.chk_autostart_windows)
        
        # Auto-start client when launcher opens
        self.chk_auto_start_client = QCheckBox("Автоматически запускать Arvis при старте лаунчера")
        self.chk_auto_start_client.setStyleSheet(CHECK_BOX_STYLE)
        layout.addWidget(self.chk_auto_start_client)
        
        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"background-color: {COLORS['border']};")
        sep.setFixedHeight(1)
        layout.addWidget(sep)
        
        # Auto-hide on client start
        self.chk_auto_hide = QCheckBox("Сворачивать лаунчер при запуске Arvis")
        self.chk_auto_hide.setStyleSheet(CHECK_BOX_STYLE)
        layout.addWidget(self.chk_auto_hide)
        
        # Minimize to tray (TODO: implement system tray)
        self.chk_minimize_to_tray = QCheckBox("Сворачивать в системный трей")
        self.chk_minimize_to_tray.setStyleSheet(CHECK_BOX_STYLE)
        self.chk_minimize_to_tray.setToolTip("Скоро: сворачивание в трей вместо панели задач")
        self.chk_minimize_to_tray.setEnabled(False)  # TODO: enable when tray is implemented
        layout.addWidget(self.chk_minimize_to_tray)
        
        # Autoscroll logs
        self.chk_autoscroll = QCheckBox("Автопрокрутка логов")
        self.chk_autoscroll.setStyleSheet(CHECK_BOX_STYLE)
        layout.addWidget(self.chk_autoscroll)
        
        parent_layout.addWidget(group)
    
    def _connect_signals(self):
        """Connect signals"""
        self.btn_save.clicked.connect(self._save_settings)
    
    def _load_settings(self):
        """Load settings into UI"""
        # User settings
        self.edit_user_name.setText(self.config.user.name)
        self.edit_user_city.setText(self.config.user.city)
        
        # Language settings
        index_ui = self.combo_ui_language.findData(self.config.languages.ui)
        if index_ui >= 0:
            self.combo_ui_language.setCurrentIndex(index_ui)
        index_speech = self.combo_speech_language.findData(self.config.languages.speech)
        if index_speech >= 0:
            self.combo_speech_language.setCurrentIndex(index_speech)
        
        # Paths
        if self.config.paths.client_root:
            self.edit_client_root.setText(self.config.paths.client_root)
        if self.config.paths.models_dir:
            self.edit_models_dir.setText(self.config.paths.models_dir)
        if getattr(self.config.paths, 'client_logs_dir', None):
            self.edit_client_logs.setText(self.config.paths.client_logs_dir)
        
        # Updates
        self.chk_auto_update.setChecked(self.config.update.auto_check)
        index = self.combo_branch.findData(self.config.update.branch)
        if index >= 0:
            self.combo_branch.setCurrentIndex(index)
        self.edit_repo.setText(self.config.update.github_repo)
        
        # Ollama
        self.chk_ollama_auto_install.setChecked(self.config.ollama.auto_install)
        self.chk_ollama_auto_start.setChecked(self.config.ollama.auto_start)
        self.combo_default_model.setCurrentText(self.config.ollama.default_model)
        
        # API Keys
        self.edit_server_api_key.setText(self.config.api_keys.server_api_key)
        self.edit_weather_api_key.setText(self.config.api_keys.weather_api_key)
        self.edit_news_api_key.setText(self.config.api_keys.news_api_key)
        self.edit_search_api_key.setText(self.config.api_keys.search_api_key)
        self.edit_search_engine_id.setText(self.config.api_keys.search_engine_id)
        
        # Logging
        index = self.combo_log_level.findData(self.config.logging.level)
        if index >= 0:
            self.combo_log_level.setCurrentIndex(index)
        self.spin_log_size.setValue(self.config.logging.max_size_mb)
        self.spin_log_backup.setValue(self.config.logging.backup_count)
        self.chk_file_logging.setChecked(self.config.logging.file_logging)
        # Logs directory
        if self.config.paths.logs_dir:
            self.edit_logs_dir.setText(self.config.paths.logs_dir)
        
        # Ollama Server
        self.edit_ollama_url.setText(self.config.ollama_server.url)
        index = self.combo_ollama_mode.findData(self.config.ollama_server.launch_mode)
        if index >= 0:
            self.combo_ollama_mode.setCurrentIndex(index)
        self.edit_ollama_bind.setText(self.config.ollama_server.bind_address)
        self.chk_ollama_external.setChecked(self.config.ollama_server.allow_external)
        self.chk_ollama_auto_restart.setChecked(self.config.ollama_server.auto_restart)
        
        # UI
        self.chk_autostart_windows.setChecked(self.config.startup.run_on_system_start)
        self.chk_auto_start_client.setChecked(self.config.startup.auto_start_client)
        self.chk_auto_hide.setChecked(self.config.window.auto_hide_on_client_start)
        self.chk_minimize_to_tray.setChecked(self.config.window.minimize_to_tray)
        self.chk_autoscroll.setChecked(self.config.autoscroll_logs)
    
    def _load_api_keys(self):
        """Load API keys from config (for backwards compatibility)"""
        self.edit_server_api_key.setText(self.config.api_keys.server_api_key)
        self.edit_weather_api_key.setText(self.config.api_keys.weather_api_key)
        self.edit_news_api_key.setText(self.config.api_keys.news_api_key)
        self.edit_search_api_key.setText(self.config.api_keys.search_api_key)
        self.edit_search_engine_id.setText(self.config.api_keys.search_engine_id)
    
    def _save_api_keys(self):
        """Save API keys to config"""
        self.config.api_keys.server_api_key = self.edit_server_api_key.text().strip()
        self.config.api_keys.weather_api_key = self.edit_weather_api_key.text().strip()
        self.config.api_keys.news_api_key = self.edit_news_api_key.text().strip()
        self.config.api_keys.search_api_key = self.edit_search_api_key.text().strip()
        self.config.api_keys.search_engine_id = self.edit_search_engine_id.text().strip()
        self.config.save()
        QMessageBox.information(self, "Сохранено", "API ключи сохранены")
    
    def _save_settings(self):
        """Save settings from UI"""
        # User settings
        self.config.user.name = self.edit_user_name.text().strip()
        self.config.user.city = self.edit_user_city.text().strip()
        
        # Language settings
        new_ui_lang = self.combo_ui_language.currentData()
        new_speech_lang = self.combo_speech_language.currentData()
        ui_lang_changed = new_ui_lang != self.config.languages.ui
        speech_lang_changed = new_speech_lang != self.config.languages.speech
        self.config.languages.ui = new_ui_lang
        self.config.languages.speech = new_speech_lang
        self.config.language = new_ui_lang  # Backward compat
        
        # Paths
        client_root = self.edit_client_root.text().strip()
        if client_root:
            # Validate path
            if not Path(client_root).exists():
                QMessageBox.warning(
                    self,
                    "Ошибка",
                    f"Папка не существует: {client_root}"
                )
                return
            self.config.paths.client_root = client_root
        
        models_dir = self.edit_models_dir.text().strip()
        self.config.paths.models_dir = models_dir if models_dir else None
        # Client logs
        client_logs = self.edit_client_logs.text().strip()
        self.config.paths.client_logs_dir = client_logs if client_logs else None
        
        # Updates
        self.config.update.auto_check = self.chk_auto_update.isChecked()
        self.config.update.branch = self.combo_branch.currentData()
        self.config.update.github_repo = self.edit_repo.text().strip()
        
        # Ollama
        self.config.ollama.auto_install = self.chk_ollama_auto_install.isChecked()
        self.config.ollama.auto_start = self.chk_ollama_auto_start.isChecked()
        self.config.ollama.default_model = self.combo_default_model.currentText()
        
        # API Keys
        self.config.api_keys.server_api_key = self.edit_server_api_key.text().strip()
        self.config.api_keys.weather_api_key = self.edit_weather_api_key.text().strip()
        self.config.api_keys.news_api_key = self.edit_news_api_key.text().strip()
        self.config.api_keys.search_api_key = self.edit_search_api_key.text().strip()
        self.config.api_keys.search_engine_id = self.edit_search_engine_id.text().strip()
        
        # Logging
        self.config.logging.level = self.combo_log_level.currentData()
        self.config.logging.max_size_mb = self.spin_log_size.value()
        self.config.logging.backup_count = self.spin_log_backup.value()
        self.config.logging.file_logging = self.chk_file_logging.isChecked()

        # Logs directory
        logs_dir = self.edit_logs_dir.text().strip()
        if logs_dir:
            try:
                p = Path(logs_dir)
                if not p.exists():
                    p.mkdir(parents=True, exist_ok=True)
                if not p.is_dir():
                    QMessageBox.warning(self, "Ошибка", f"Путь не является папкой: {logs_dir}")
                    return
                self.config.paths.logs_dir = logs_dir
            except Exception as e:
                QMessageBox.warning(self, "Ошибка", f"Не удалось создать/использовать папку логов: {e}")
                return
        else:
            self.config.paths.logs_dir = None
        
        # Ollama Server
        self.config.ollama_server.url = self.edit_ollama_url.text().strip()
        self.config.ollama_server.launch_mode = self.combo_ollama_mode.currentData()
        self.config.ollama_server.bind_address = self.edit_ollama_bind.text().strip()
        self.config.ollama_server.allow_external = self.chk_ollama_external.isChecked()
        self.config.ollama_server.auto_restart = self.chk_ollama_auto_restart.isChecked()
        
        # UI
        new_autostart_windows = self.chk_autostart_windows.isChecked()
        autostart_changed = new_autostart_windows != self.config.startup.run_on_system_start
        self.config.startup.run_on_system_start = new_autostart_windows
        self.config.startup.auto_start_client = self.chk_auto_start_client.isChecked()
        self.config.window.auto_hide_on_client_start = self.chk_auto_hide.isChecked()
        self.config.window.minimize_to_tray = self.chk_minimize_to_tray.isChecked()
        self.config.autoscroll_logs = self.chk_autoscroll.isChecked()
        
        # Save
        try:
            self.config.save()
            
            # Sync settings to client config if changed
            if client_root and (ui_lang_changed or speech_lang_changed or self.config.paths.client_logs_dir):
                    self._sync_settings_to_client(
                        Path(client_root),
                        new_ui_lang if ui_lang_changed else None,
                        new_speech_lang if speech_lang_changed else None,
                        self.config.paths.client_logs_dir
                    )
            
            # Sync Windows autostart if changed
            if autostart_changed:
                self._sync_autostart(new_autostart_windows)
            
            QMessageBox.information(self, "Сохранено", "Настройки сохранены")
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось сохранить: {e}")
    
    def _sync_autostart(self, enabled: bool):
        """Sync autostart setting with Windows registry"""
        try:
            from ..autostart import set_autostart, is_autostart_enabled
            import sys
            
            # Only sync for frozen executables
            if not getattr(sys, 'frozen', False):
                if enabled:
                    QMessageBox.information(
                        self,
                        "Автозапуск",
                        "Автозапуск с Windows работает только для скомпилированной версии (.exe).\n"
                        "При запуске из исходников эта настройка будет проигнорирована."
                    )
                return
            
            if set_autostart(enabled):
                # Verify it was set
                if is_autostart_enabled() != enabled:
                    QMessageBox.warning(
                        self,
                        "Автозапуск",
                        "Не удалось изменить настройку автозапуска.\n"
                        "Возможно, требуются права администратора."
                    )
            else:
                QMessageBox.warning(
                    self,
                    "Ошибка",
                    "Не удалось изменить настройку автозапуска."
                )
        except Exception as e:
            QMessageBox.warning(self, "Ошибка автозапуска", f"Ошибка: {e}")
    
    def _sync_settings_to_client(
        self,
        client_root: Path,
        ui_language: Optional[str] = None,
        speech_language: Optional[str] = None,
        client_logs: Optional[str] = None,
    ):
        """Sync settings to client config"""
        import json
        
        config_path = client_root / "config" / "config.json"
        if not config_path.exists():
            return
        
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
            
            # Update language settings if provided
            if ui_language or speech_language:
                if "language" not in data:
                    data["language"] = {}
                
                if ui_language:
                    data["language"]["ui"] = ui_language
                
                if speech_language:
                    data["language"]["tts"] = speech_language
                    data["language"]["stt"] = speech_language
                    data["language"]["speech"] = speech_language
            
            # Sync user name and city
            if "user" not in data:
                data["user"] = {}
            data["user"]["name"] = self.config.user.name
            data["user"]["city"] = self.config.user.city

            # Sync client logs path if provided
            if client_logs:
                if "paths" not in data or not isinstance(data["paths"], dict):
                    data["paths"] = {}
                data["paths"]["logs"] = client_logs
            
            config_path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        except Exception:
            pass  # Silently fail if client config can't be updated
    
    def _open_models_page(self):
        """Ask parent window to switch to Models page (index may vary)"""
        try:
            parent = self.parent()
            # Try known navigation method
            if parent and hasattr(parent, '_navigate_to'):
                parent._navigate_to(1)  # Models index in main window
            elif parent and hasattr(parent, 'pages_stack'):
                # Try to find models page index
                for i in range(parent.pages_stack.count()):
                    w = parent.pages_stack.widget(i)
                    if w.__class__.__name__ == 'ModelsPage':
                        parent.pages_stack.setCurrentIndex(i)
                        break
        except Exception:
            pass
    
    def _browse_client_root(self):
        """Browse for client root directory"""
        path = QFileDialog.getExistingDirectory(
            self,
            "Выберите папку Arvis Client",
            self.edit_client_root.text() or str(Path.home())
        )
        if path:
            self.edit_client_root.setText(path)
    
    def _browse_models_dir(self):
        """Browse for models directory"""
        path = QFileDialog.getExistingDirectory(
            self,
            "Выберите папку для моделей",
            self.edit_models_dir.text() or str(Path.home())
        )
        if path:
            self.edit_models_dir.setText(path)

    def _browse_client_logs(self):
        """Browse for client logs directory"""
        path = QFileDialog.getExistingDirectory(
            self,
            "Выберите папку для логов клиента",
            self.edit_client_logs.text() or str(Path.home())
        )
        if path:
            self.edit_client_logs.setText(path)

    def _browse_logs_dir(self):
        """Browse for logs directory"""
        path = QFileDialog.getExistingDirectory(
            self,
            "Выберите папку для логов лаунчера",
            self.edit_logs_dir.text() or str(Path.home())
        )
        if path:
            self.edit_logs_dir.setText(path)
