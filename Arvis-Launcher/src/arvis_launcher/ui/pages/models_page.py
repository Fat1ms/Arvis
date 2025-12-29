"""
Models page - Ollama, STT, and TTS model management
"""

from __future__ import annotations

from typing import Optional, List, TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QProgressBar,
    QFrame,
    QScrollArea,
    QGroupBox,
    QMessageBox,
    QSizePolicy,
    QTabWidget,
    QComboBox,
)

from ...config import LauncherConfig
from ...ollama_manager import OllamaManager, OllamaModel, OllamaState, RECOMMENDED_MODELS
from ...voice_models import VoiceModelsManager, VoiceModel, ModelType, VOSK_MODELS, SILERO_MODELS
from ...styles import (
    COLORS,
    PAGE_TITLE_STYLE,
    PAGE_SUBTITLE_STYLE,
    PRIMARY_BUTTON_STYLE,
    SECONDARY_BUTTON_STYLE,
    DANGER_BUTTON_STYLE,
    SUCCESS_BUTTON_STYLE,
    PROGRESS_BAR_STYLE,
    GROUP_BOX_STYLE,
    SCROLL_AREA_STYLE,
    COMBO_BOX_STYLE,
)


class VoiceModelCard(QFrame):
    """Card widget for STT/TTS model"""
    
    def __init__(
        self,
        model: VoiceModel,
        on_install: callable,
        on_remove: callable,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.model = model
        self.on_install = on_install
        self.on_remove = on_remove
        
        self._build_ui()
    
    def _build_ui(self):
        self.setObjectName("voice_model_card")
        self.setStyleSheet(f"""
            QFrame#voice_model_card {{
                background-color: {COLORS['bg_secondary']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
            }}
            QFrame#voice_model_card:hover {{
                border-color: {COLORS['text_muted']};
            }}
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)
        
        # Model type icon
        icon_text = "🎤" if self.model.model_type == ModelType.STT else "🔊"
        icon = QLabel(icon_text)
        icon.setStyleSheet("font-size: 20px;")
        layout.addWidget(icon)
        
        # Model info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        
        name_label = QLabel(self.model.display_name)
        name_label.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 13px; font-weight: bold;")
        info_layout.addWidget(name_label)
        
        details = f"{self.model.size} • {self.model.language.upper()}"
        details_label = QLabel(details)
        details_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px;")
        info_layout.addWidget(details_label)
        
        layout.addLayout(info_layout, 1)
        
        # Status / Action button
        if self.model.is_installed:
            status = QLabel("✓")
            status.setStyleSheet(f"color: {COLORS['success']}; font-size: 14px;")
            layout.addWidget(status)
            
            if self.model.model_type == ModelType.STT:  # Only STT can be removed
                btn = QPushButton("✕")
                btn.setFixedSize(28, 28)
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: transparent;
                        color: {COLORS['error']};
                        border: 1px solid {COLORS['error']};
                        border-radius: 14px;
                        font-size: 12px;
                    }}
                    QPushButton:hover {{
                        background-color: rgba(200, 50, 50, 0.1);
                    }}
                """)
                btn.clicked.connect(lambda: self.on_remove(self.model))
                layout.addWidget(btn)
        else:
            btn = QPushButton("Скачать")
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['accent']};
                    color: {COLORS['text_primary']};
                    border: none;
                    border-radius: 4px;
                    padding: 6px 12px;
                    font-size: 11px;
                }}
                QPushButton:hover {{
                    background-color: {COLORS['accent_hover']};
                }}
            """)
            btn.clicked.connect(lambda: self.on_install(self.model))
            layout.addWidget(btn)


class ModelCard(QFrame):
    """Card widget for a single model"""
    
    def __init__(
        self,
        model: OllamaModel,
        on_install: callable,
        on_remove: callable,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.model = model
        self.on_install = on_install
        self.on_remove = on_remove
        
        self._build_ui()
    
    def _build_ui(self):
        self.setObjectName("model_card")
        self.setStyleSheet(f"""
            QFrame#model_card {{
                background-color: {COLORS['bg_secondary']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
            }}
            QFrame#model_card:hover {{
                border-color: {COLORS['text_muted']};
            }}
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)
        
        # Model info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)
        
        # Name
        name_label = QLabel(self.model.display_name)
        name_label.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 14px; font-weight: bold;")
        info_layout.addWidget(name_label)
        
        # Details
        details = f"{self.model.name}"
        if self.model.size:
            details += f" • {self.model.size}"
        details_label = QLabel(details)
        details_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
        info_layout.addWidget(details_label)
        
        layout.addLayout(info_layout, 1)
        
        # Status / Action button
        if self.model.is_installed:
            # Installed indicator
            status = QLabel("✓ Установлена")
            status.setStyleSheet(f"color: {COLORS['success']}; font-size: 12px;")
            layout.addWidget(status)
            
            # Remove button
            btn = QPushButton("Удалить")
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {COLORS['error']};
                    border: 1px solid {COLORS['error']};
                    border-radius: 4px;
                    padding: 6px 12px;
                    font-size: 12px;
                }}
                QPushButton:hover {{
                    background-color: rgba(200, 50, 50, 0.1);
                }}
            """)
            btn.clicked.connect(lambda: self.on_remove(self.model.name))
            layout.addWidget(btn)
        else:
            # Install button
            btn = QPushButton("Скачать")
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['accent']};
                    color: {COLORS['text_primary']};
                    border: none;
                    border-radius: 4px;
                    padding: 6px 16px;
                    font-size: 12px;
                }}
                QPushButton:hover {{
                    background-color: {COLORS['accent_hover']};
                }}
            """)
            btn.clicked.connect(lambda: self.on_install(self.model.name))
            layout.addWidget(btn)


class ModelsPage(QWidget):
    """Models management page with tabs for LLM, STT, TTS"""
    
    def __init__(
        self,
        config: LauncherConfig,
        ollama_manager: OllamaManager,
        voice_manager: Optional[VoiceModelsManager] = None,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.config = config
        self.ollama = ollama_manager
        self.voice_manager = voice_manager
        
        self._build_ui()
        self._connect_signals()
    
    def _build_ui(self):
        """Build the models page UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)
        
        # Header
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        title_layout = QVBoxLayout()
        title_layout.setSpacing(4)
        
        title = QLabel("Управление моделями")
        title.setStyleSheet(PAGE_TITLE_STYLE)
        title_layout.addWidget(title)
        
        subtitle = QLabel("AI, распознавание и синтез речи")
        subtitle.setStyleSheet(PAGE_SUBTITLE_STYLE)
        title_layout.addWidget(subtitle)
        
        header_layout.addLayout(title_layout, 1)
        layout.addWidget(header)
        
        # Progress section (hidden by default)
        self._build_progress_section()
        layout.addWidget(self.progress_widget)
        self.progress_widget.hide()
        
        # Tab widget
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                background-color: {COLORS['bg_primary']};
            }}
            QTabBar::tab {{
                background-color: {COLORS['bg_secondary']};
                color: {COLORS['text_secondary']};
                border: 1px solid {COLORS['border']};
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                padding: 8px 20px;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background-color: {COLORS['bg_primary']};
                color: {COLORS['text_primary']};
            }}
            QTabBar::tab:hover:!selected {{
                background-color: {COLORS['bg_tertiary']};
            }}
        """)
        
        # LLM Tab
        self.llm_tab = self._build_llm_tab()
        self.tabs.addTab(self.llm_tab, "🤖 LLM (Ollama)")
        
        # STT Tab
        self.stt_tab = self._build_stt_tab()
        self.tabs.addTab(self.stt_tab, "🎤 STT (Vosk)")
        
        # TTS Tab  
        self.tts_tab = self._build_tts_tab()
        self.tabs.addTab(self.tts_tab, "🔊 TTS (Silero)")
        
        layout.addWidget(self.tabs, 1)
    
    def _build_llm_tab(self) -> QWidget:
        """Build LLM/Ollama tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Ollama status card
        self._build_ollama_status()
        layout.addWidget(self.ollama_status_card)
        
        # Models list
        self._build_models_list()
        layout.addWidget(self.models_scroll, 1)
        
        return tab
    
    def _build_stt_tab(self) -> QWidget:
        """Build STT/Vosk tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Info
        info = QLabel(
            "🎤 Vosk — офлайн распознавание речи. "
            "Выберите модель для вашего языка."
        )
        info.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
        info.setWordWrap(True)
        layout.addWidget(info)
        
        # Active model selection
        active_group = QGroupBox("Активная модель STT")
        active_group.setStyleSheet(GROUP_BOX_STYLE)
        active_layout = QHBoxLayout(active_group)
        active_layout.setContentsMargins(12, 16, 12, 12)
        
        active_label = QLabel("Использовать:")
        active_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        active_layout.addWidget(active_label)
        
        self.stt_model_combo = QComboBox()
        self.stt_model_combo.setStyleSheet(COMBO_BOX_STYLE)
        self.stt_model_combo.setMinimumWidth(200)
        self.stt_model_combo.currentTextChanged.connect(self._on_stt_model_changed)
        active_layout.addWidget(self.stt_model_combo, 1)
        
        layout.addWidget(active_group)
        
        # STT models scroll
        self.stt_scroll = QScrollArea()
        self.stt_scroll.setWidgetResizable(True)
        self.stt_scroll.setStyleSheet(SCROLL_AREA_STYLE + f"""
            QScrollArea {{ background-color: transparent; border: none; }}
        """)
        
        self.stt_container = QWidget()
        self.stt_layout = QVBoxLayout(self.stt_container)
        self.stt_layout.setContentsMargins(0, 0, 8, 0)
        self.stt_layout.setSpacing(8)
        
        # Add STT model cards
        self._refresh_stt_list()
        
        self.stt_scroll.setWidget(self.stt_container)
        layout.addWidget(self.stt_scroll, 1)
        
        return tab
    
    def _build_tts_tab(self) -> QWidget:
        """Build TTS/Silero tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Info
        info = QLabel(
            "🔊 Silero TTS — офлайн синтез речи. "
            "Модели загружаются автоматически при первом использовании."
        )
        info.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
        info.setWordWrap(True)
        layout.addWidget(info)
        
        # Active model and voice selection
        active_group = QGroupBox("Настройки TTS")
        active_group.setStyleSheet(GROUP_BOX_STYLE)
        active_layout = QVBoxLayout(active_group)
        active_layout.setContentsMargins(12, 16, 12, 12)
        active_layout.setSpacing(8)
        
        # Model selection
        model_row = QHBoxLayout()
        model_label = QLabel("Модель:")
        model_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        model_label.setMinimumWidth(60)
        model_row.addWidget(model_label)
        
        self.tts_model_combo = QComboBox()
        self.tts_model_combo.setStyleSheet(COMBO_BOX_STYLE)
        self.tts_model_combo.addItem("🇷🇺 Русский (v3_1_ru)", "v3_1_ru")
        self.tts_model_combo.addItem("🇬🇧 English (v3_en)", "v3_en")
        self.tts_model_combo.addItem("🇩🇪 Deutsch (v3_de)", "v3_de")
        self.tts_model_combo.currentIndexChanged.connect(self._on_tts_model_changed)
        model_row.addWidget(self.tts_model_combo, 1)
        active_layout.addLayout(model_row)
        
        # Voice selection
        voice_row = QHBoxLayout()
        voice_label = QLabel("Голос:")
        voice_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        voice_label.setMinimumWidth(60)
        voice_row.addWidget(voice_label)
        
        self.tts_voice_combo = QComboBox()
        self.tts_voice_combo.setStyleSheet(COMBO_BOX_STYLE)
        self._populate_tts_voices()
        self.tts_voice_combo.currentIndexChanged.connect(self._on_tts_voice_changed)
        voice_row.addWidget(self.tts_voice_combo, 1)
        active_layout.addLayout(voice_row)
        
        layout.addWidget(active_group)
        
        # TTS models scroll (for info/download status)
        self.tts_scroll = QScrollArea()
        self.tts_scroll.setWidgetResizable(True)
        self.tts_scroll.setStyleSheet(SCROLL_AREA_STYLE + f"""
            QScrollArea {{ background-color: transparent; border: none; }}
        """)
        
        self.tts_container = QWidget()
        self.tts_layout = QVBoxLayout(self.tts_container)
        self.tts_layout.setContentsMargins(0, 0, 8, 0)
        self.tts_layout.setSpacing(8)
        
        # Add TTS model cards
        self._refresh_tts_list()
        
        self.tts_scroll.setWidget(self.tts_container)
        layout.addWidget(self.tts_scroll, 1)
        
        # Pre-download button
        self.btn_preload_tts = QPushButton("📥  Загрузить Silero заранее")
        self.btn_preload_tts.setStyleSheet(SECONDARY_BUTTON_STYLE)
        self.btn_preload_tts.clicked.connect(self._on_preload_tts)
        layout.addWidget(self.btn_preload_tts)
        
        # Load saved selections
        self._load_voice_settings()
        
        return tab
    
    def _build_ollama_status(self):
        """Build Ollama status card"""
        self.ollama_status_card = QFrame()
        self.ollama_status_card.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_secondary']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
            }}
        """)
        
        layout = QHBoxLayout(self.ollama_status_card)
        layout.setContentsMargins(16, 12, 16, 12)
        
        # Status info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)
        
        title = QLabel("Ollama")
        title.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 14px; font-weight: bold;")
        info_layout.addWidget(title)
        
        self.ollama_status_label = QLabel("Проверка...")
        self.ollama_status_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
        info_layout.addWidget(self.ollama_status_label)
        
        layout.addLayout(info_layout, 1)
        
        # Action buttons
        self.btn_install_ollama = QPushButton("Установить Ollama")
        self.btn_install_ollama.setStyleSheet(SUCCESS_BUTTON_STYLE)
        self.btn_install_ollama.hide()
        layout.addWidget(self.btn_install_ollama)
        
        self.btn_start_ollama = QPushButton("Запустить")
        self.btn_start_ollama.setStyleSheet(SECONDARY_BUTTON_STYLE)
        self.btn_start_ollama.hide()
        layout.addWidget(self.btn_start_ollama)
        
        self.btn_stop_ollama = QPushButton("Остановить")
        self.btn_stop_ollama.setStyleSheet(DANGER_BUTTON_STYLE)
        self.btn_stop_ollama.hide()
        layout.addWidget(self.btn_stop_ollama)
    
    def _build_progress_section(self):
        """Build progress indicator"""
        self.progress_widget = QWidget()
        layout = QVBoxLayout(self.progress_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet(PROGRESS_BAR_STYLE)
        self.progress_bar.setMinimumHeight(20)
        layout.addWidget(self.progress_bar)
        
        self.progress_label = QLabel("")
        self.progress_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
        layout.addWidget(self.progress_label)
    
    def _build_models_list(self):
        """Build scrollable models list"""
        self.models_scroll = QScrollArea()
        self.models_scroll.setWidgetResizable(True)
        self.models_scroll.setStyleSheet(SCROLL_AREA_STYLE + f"""
            QScrollArea {{
                background-color: transparent;
                border: none;
            }}
        """)
        
        self.models_container = QWidget()
        self.models_layout = QVBoxLayout(self.models_container)
        self.models_layout.setContentsMargins(0, 0, 8, 0)
        self.models_layout.setSpacing(8)
        
        # Add section headers
        installed_header = QLabel("Установленные модели")
        installed_header.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px; font-weight: bold; margin-top: 8px;")
        self.models_layout.addWidget(installed_header)
        self.installed_header = installed_header
        
        # Placeholder for installed models
        self.installed_placeholder = QLabel("Нет установленных моделей")
        self.installed_placeholder.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px; padding: 12px;")
        self.models_layout.addWidget(self.installed_placeholder)
        
        # Recommended section
        recommended_header = QLabel("Рекомендуемые модели")
        recommended_header.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px; font-weight: bold; margin-top: 16px;")
        self.models_layout.addWidget(recommended_header)
        
        self.models_layout.addStretch()
        
        self.models_scroll.setWidget(self.models_container)
    
    def _connect_signals(self):
        """Connect signals"""
        self.btn_install_ollama.clicked.connect(self._on_install_ollama)
        self.btn_start_ollama.clicked.connect(self._on_start_ollama)
        self.btn_stop_ollama.clicked.connect(self._on_stop_ollama)
        
        self.ollama.progress.connect(self._on_progress)
        self.ollama.operation_finished.connect(self._on_operation_finished)
    
    def on_ollama_state_changed(self, state: str):
        """Handle Ollama state changes"""
        state_enum = OllamaState(state)
        
        # Update status label
        if state_enum == OllamaState.NOT_INSTALLED:
            self.ollama_status_label.setText("Не установлен")
            self.ollama_status_label.setStyleSheet(f"color: {COLORS['error']}; font-size: 12px;")
            self.btn_install_ollama.show()
            self.btn_start_ollama.hide()
            self.btn_stop_ollama.hide()
        elif state_enum == OllamaState.STOPPED:
            self.ollama_status_label.setText("Остановлен")
            self.ollama_status_label.setStyleSheet(f"color: {COLORS['warning']}; font-size: 12px;")
            self.btn_install_ollama.hide()
            self.btn_start_ollama.show()
            self.btn_stop_ollama.hide()
        elif state_enum == OllamaState.RUNNING:
            self.ollama_status_label.setText("Работает")
            self.ollama_status_label.setStyleSheet(f"color: {COLORS['success']}; font-size: 12px;")
            self.btn_install_ollama.hide()
            self.btn_start_ollama.hide()
            self.btn_stop_ollama.show()
        else:
            self.ollama_status_label.setText("Неизвестно")
            self.ollama_status_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px;")
    
    def on_models_updated(self, models: List[OllamaModel]):
        """Handle models list update"""
        self._refresh_models_list(models)
    
    def _refresh_models_list(self, installed_models: List[OllamaModel]):
        """Refresh the models list"""
        # Clear existing model cards
        while self.models_layout.count() > 0:
            item = self.models_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Installed section
        installed_header = QLabel("Установленные модели")
        installed_header.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px; font-weight: bold; margin-top: 8px;")
        self.models_layout.addWidget(installed_header)
        
        if installed_models:
            for model in installed_models:
                card = ModelCard(model, self._on_install_model, self._on_remove_model)
                self.models_layout.addWidget(card)
        else:
            placeholder = QLabel("Нет установленных моделей")
            placeholder.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px; padding: 12px;")
            self.models_layout.addWidget(placeholder)
        
        # Recommended section
        recommended_header = QLabel("Рекомендуемые модели")
        recommended_header.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px; font-weight: bold; margin-top: 16px;")
        self.models_layout.addWidget(recommended_header)
        
        # Get recommended models with status
        installed_names = {m.name.split(":")[0] for m in installed_models}
        
        for model in RECOMMENDED_MODELS:
            model_copy = OllamaModel(
                name=model.name,
                size=model.size,
                is_installed=model.name.split(":")[0] in installed_names
            )
            if not model_copy.is_installed:
                card = ModelCard(model_copy, self._on_install_model, self._on_remove_model)
                self.models_layout.addWidget(card)
        
        self.models_layout.addStretch()
    
    def _on_progress(self, percent: int, message: str):
        """Handle progress updates"""
        self.progress_widget.show()
        self.progress_bar.setValue(percent)
        self.progress_label.setText(message)
    
    def _on_operation_finished(self, success: bool, message: str):
        """Handle operation completion"""
        self.progress_widget.hide()
        
        if not success:
            QMessageBox.warning(self, "Ошибка", message)
    
    def _on_install_ollama(self):
        """Install Ollama"""
        reply = QMessageBox.question(
            self,
            "Установка Ollama",
            "Скачать и установить Ollama?\n\n"
            "Это необходимо для работы AI-моделей.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.btn_install_ollama.setEnabled(False)
            self.ollama.install_ollama()
    
    def _on_start_ollama(self):
        """Start Ollama service"""
        self.ollama.start_service()
    
    def _on_stop_ollama(self):
        """Stop Ollama service"""
        self.ollama.stop_service()
    
    def _on_install_model(self, model_name: str):
        """Install a model"""
        if self.ollama.state != OllamaState.RUNNING:
            QMessageBox.warning(
                self,
                "Ollama не запущен",
                "Сначала запустите Ollama для скачивания моделей."
            )
            return
        
        self.ollama.pull_model(model_name)
    
    def _on_remove_model(self, model_name: str):
        """Remove a model"""
        reply = QMessageBox.question(
            self,
            "Удаление модели",
            f"Удалить модель {model_name}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.ollama.remove_model(model_name)
    
    # ========== STT Methods ==========
    
    def _refresh_stt_list(self):
        """Refresh STT models list"""
        # Clear
        while self.stt_layout.count() > 0:
            item = self.stt_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Group by language
        languages = {}
        for model in VOSK_MODELS:
            if model.language not in languages:
                languages[model.language] = []
            languages[model.language].append(model)
        
        lang_names = {"ru": "Русский", "en": "English", "uk": "Українська", "es": "Español"}
        
        for lang, models in languages.items():
            # Language header
            header = QLabel(f"🌐 {lang_names.get(lang, lang)}")
            header.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px; font-weight: bold; margin-top: 8px;")
            self.stt_layout.addWidget(header)
            
            for model in models:
                card = VoiceModelCard(model, self._on_install_stt, self._on_remove_stt)
                self.stt_layout.addWidget(card)
        
        self.stt_layout.addStretch()
    
    def _on_install_stt(self, model: VoiceModel):
        """Install STT model"""
        if self.voice_manager:
            self.voice_manager.download_model(model)
        else:
            QMessageBox.warning(self, "Ошибка", "Менеджер моделей не инициализирован")
    
    def _on_remove_stt(self, model: VoiceModel):
        """Remove STT model"""
        reply = QMessageBox.question(
            self,
            "Удаление модели",
            f"Удалить модель {model.display_name}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes and self.voice_manager:
            self.voice_manager.remove_model(model)
    
    # ========== TTS Methods ==========
    
    def _refresh_tts_list(self):
        """Refresh TTS models list"""
        # Clear
        while self.tts_layout.count() > 0:
            item = self.tts_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        for model in SILERO_MODELS:
            card = VoiceModelCard(model, self._on_install_tts, lambda m: None)
            self.tts_layout.addWidget(card)
        
        self.tts_layout.addStretch()
    
    def _on_install_tts(self, model: VoiceModel):
        """Install TTS model"""
        if self.voice_manager:
            self.voice_manager.download_model(model)
        else:
            QMessageBox.warning(self, "Ошибка", "Менеджер моделей не инициализирован")
    
    def _on_preload_tts(self):
        """Pre-download Silero TTS"""
        reply = QMessageBox.question(
            self,
            "Загрузка Silero",
            "Загрузить модели Silero TTS заранее?\n\n"
            "Это позволит использовать синтез речи офлайн.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self._on_install_tts(SILERO_MODELS[0])
    
    def on_voice_models_updated(self, models: List[VoiceModel]):
        """Handle voice models update"""
        self._refresh_stt_list()
        self._refresh_tts_list()
        self._update_stt_combo()
    
    # ========== Voice Settings Methods ==========
    
    def _update_stt_combo(self):
        """Update STT model combo box with installed models"""
        if not hasattr(self, 'stt_model_combo'):
            return
        
        self.stt_model_combo.blockSignals(True)
        self.stt_model_combo.clear()
        
        # Add "Not selected" option
        self.stt_model_combo.addItem("— Не выбрано —", "")
        
        # Add installed models
        models_dir = self.config.get_models_dir()
        if models_dir.exists():
            for folder in models_dir.iterdir():
                if folder.is_dir() and folder.name.startswith("vosk-model"):
                    display_name = folder.name.replace("vosk-model-", "").replace("-", " ").title()
                    self.stt_model_combo.addItem(f"✓ {display_name}", folder.name)
        
        # Select current model
        current = self.config.voice_models.stt_model
        if current:
            index = self.stt_model_combo.findData(current)
            if index >= 0:
                self.stt_model_combo.setCurrentIndex(index)
        
        self.stt_model_combo.blockSignals(False)
    
    def _populate_tts_voices(self):
        """Populate TTS voice combo based on selected model"""
        if not hasattr(self, 'tts_voice_combo'):
            return
        
        self.tts_voice_combo.blockSignals(True)
        self.tts_voice_combo.clear()
        
        model = self.tts_model_combo.currentData() if hasattr(self, 'tts_model_combo') else "v3_1_ru"
        
        # Russian voices
        if model == "v3_1_ru":
            voices = [
                ("Айдар (муж)", "aidar"),
                ("Борис (муж)", "baya"),
                ("Ксения (жен)", "kseniya"),
                ("Евгений (муж)", "eugene"),
                ("Рандом", "random"),
            ]
        # English voices
        elif model == "v3_en":
            voices = [
                ("EN Speaker 0", "en_0"),
                ("EN Speaker 1", "en_1"),
                ("EN Speaker 2", "en_2"),
                ("Random", "random"),
            ]
        # German voices
        elif model == "v3_de":
            voices = [
                ("DE Speaker 0", "de_0"),
                ("DE Speaker 1", "de_1"),
                ("Random", "random"),
            ]
        else:
            voices = [("Default", "default")]
        
        for display, value in voices:
            self.tts_voice_combo.addItem(display, value)
        
        self.tts_voice_combo.blockSignals(False)
    
    def _load_voice_settings(self):
        """Load saved voice model settings from config"""
        # STT
        if hasattr(self, 'stt_model_combo'):
            self._update_stt_combo()
        
        # TTS model
        if hasattr(self, 'tts_model_combo'):
            self.tts_model_combo.blockSignals(True)
            index = self.tts_model_combo.findData(self.config.voice_models.tts_model)
            if index >= 0:
                self.tts_model_combo.setCurrentIndex(index)
            self.tts_model_combo.blockSignals(False)
            
            # Populate voices for selected model
            self._populate_tts_voices()
            
            # Select saved voice
            if hasattr(self, 'tts_voice_combo'):
                self.tts_voice_combo.blockSignals(True)
                voice_index = self.tts_voice_combo.findData(self.config.voice_models.tts_voice)
                if voice_index >= 0:
                    self.tts_voice_combo.setCurrentIndex(voice_index)
                self.tts_voice_combo.blockSignals(False)
    
    def _on_stt_model_changed(self, text: str):
        """Handle STT model selection change"""
        model_name = self.stt_model_combo.currentData()
        self.config.voice_models.stt_model = model_name or ""
        self.config.save()
        self._sync_voice_settings_to_client()
    
    def _on_tts_model_changed(self, index: int):
        """Handle TTS model selection change"""
        model = self.tts_model_combo.currentData()
        self.config.voice_models.tts_model = model or "v3_1_ru"
        
        # Update voices for new model
        self._populate_tts_voices()
        
        # Reset to first voice
        if self.tts_voice_combo.count() > 0:
            self.config.voice_models.tts_voice = self.tts_voice_combo.itemData(0) or "aidar"
        
        self.config.save()
        self._sync_voice_settings_to_client()
    
    def _on_tts_voice_changed(self, index: int):
        """Handle TTS voice selection change"""
        voice = self.tts_voice_combo.currentData()
        self.config.voice_models.tts_voice = voice or "aidar"
        self.config.save()
        self._sync_voice_settings_to_client()
    
    def _sync_voice_settings_to_client(self):
        """Sync voice model settings to client config"""
        import json
        
        client_root = self.config.get_client_root()
        if not client_root:
            return
        
        config_path = client_root / "config" / "config.json"
        if not config_path.exists():
            return
        
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
            
            # Update STT settings
            if "stt" not in data:
                data["stt"] = {}
            
            if self.config.voice_models.stt_model:
                models_dir = self.config.get_models_dir()
                stt_path = models_dir / self.config.voice_models.stt_model
                data["stt"]["model_path"] = str(stt_path)
            
            # Update TTS settings
            if "tts" not in data:
                data["tts"] = {}
            
            data["tts"]["voice"] = self.config.voice_models.tts_voice
            # Silero model is auto-downloaded based on language, but we can hint
            
            config_path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        except Exception:
            pass
