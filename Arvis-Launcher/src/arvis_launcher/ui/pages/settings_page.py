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
)

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
        group = QGroupBox("Пути")
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
        
        parent_layout.addWidget(group)
    
    def _build_updates_section(self, parent_layout):
        """Build updates configuration section"""
        group = QGroupBox("Обновления")
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
        group = QGroupBox("Ollama")
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
    
    def _build_ui_section(self, parent_layout):
        """Build UI configuration section"""
        group = QGroupBox("🖥️  Интерфейс")
        group.setStyleSheet(GROUP_BOX_STYLE)
        
        layout = QVBoxLayout(group)
        layout.setContentsMargins(16, 20, 16, 16)
        layout.setSpacing(12)
        
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
        
        # UI
        self.chk_autoscroll.setChecked(self.config.autoscroll_logs)
    
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
        
        # Updates
        self.config.update.auto_check = self.chk_auto_update.isChecked()
        self.config.update.branch = self.combo_branch.currentData()
        self.config.update.github_repo = self.edit_repo.text().strip()
        
        # Ollama
        self.config.ollama.auto_install = self.chk_ollama_auto_install.isChecked()
        self.config.ollama.auto_start = self.chk_ollama_auto_start.isChecked()
        self.config.ollama.default_model = self.combo_default_model.currentText()
        
        # UI
        self.config.autoscroll_logs = self.chk_autoscroll.isChecked()
        
        # Save
        try:
            self.config.save()
            
            # Sync settings to client config if changed
            if client_root and (ui_lang_changed or speech_lang_changed):
                self._sync_settings_to_client(
                    Path(client_root),
                    new_ui_lang if ui_lang_changed else None,
                    new_speech_lang if speech_lang_changed else None
                )
            
            QMessageBox.information(self, "Сохранено", "Настройки сохранены")
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось сохранить: {e}")
    
    def _sync_settings_to_client(
        self,
        client_root: Path,
        ui_language: Optional[str] = None,
        speech_language: Optional[str] = None
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
            
            config_path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        except Exception:
            pass  # Silently fail if client config can't be updated
    
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
