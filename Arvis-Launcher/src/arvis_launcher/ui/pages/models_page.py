"""
Models page - Ollama, STT, and TTS model management
"""

from __future__ import annotations

import json
import sys
import tempfile
import threading
import subprocess
from pathlib import Path
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
        self.tabs.addTab(self.tts_tab, "🔊 TTS (Multi)")
        
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
        
        # Active model selection
        active_group = QGroupBox("Активная модель LLM")
        active_group.setStyleSheet(GROUP_BOX_STYLE)
        active_layout = QHBoxLayout(active_group)
        active_layout.setContentsMargins(12, 16, 12, 12)
        
        active_label = QLabel("Использовать:")
        active_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        active_layout.addWidget(active_label)
        
        self.llm_model_combo = QComboBox()
        self.llm_model_combo.setStyleSheet(COMBO_BOX_STYLE)
        self.llm_model_combo.setMinimumWidth(250)
        self.llm_model_combo.setPlaceholderText("Выберите модель...")
        self.llm_model_combo.currentTextChanged.connect(self._on_llm_model_changed)
        active_layout.addWidget(self.llm_model_combo, 1)
        
        self.btn_save_llm = QPushButton("💾 Сохранить")
        self.btn_save_llm.setStyleSheet(SECONDARY_BUTTON_STYLE)
        self.btn_save_llm.clicked.connect(self._on_save_llm_model)
        active_layout.addWidget(self.btn_save_llm)
        
        layout.addWidget(active_group)
        
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
        
        self.btn_save_stt = QPushButton("💾 Сохранить")
        self.btn_save_stt.setStyleSheet(SECONDARY_BUTTON_STYLE)
        self.btn_save_stt.clicked.connect(self._on_save_stt_model)
        active_layout.addWidget(self.btn_save_stt)
        
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

        # Ensure STT combo is populated on build
        self._update_stt_combo()
        
        return tab
    
    def _build_tts_tab(self) -> QWidget:
        """Build TTS tab with multiple engine support - full scrollable layout"""
        tab = QWidget()
        main_layout = QVBoxLayout(tab)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Main scroll area for entire TTS tab content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(SCROLL_AREA_STYLE + f"""
            QScrollArea {{ 
                background-color: transparent; 
                border: none;
            }}
            QScrollArea > QWidget > QWidget {{
                background-color: transparent;
            }}
        """)
        
        scroll_content = QWidget()
        layout = QVBoxLayout(scroll_content)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Info header
        info = QLabel(
            "🔊 Синтез речи (TTS). Выберите движок и модель для озвучивания. "
            "Доступны: Silero, Piper, Kokoro, StyleTTS2, F5-TTS, Bark."
        )
        info.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
        info.setWordWrap(True)
        layout.addWidget(info)
        
        # ============ TTS Engine Selection Group ============
        engine_group = QGroupBox("🎯 Выбор TTS движка")
        engine_group.setStyleSheet(GROUP_BOX_STYLE)
        engine_layout = QVBoxLayout(engine_group)
        engine_layout.setContentsMargins(12, 16, 12, 12)
        engine_layout.setSpacing(8)
        
        # Engine selection row
        engine_row = QHBoxLayout()
        engine_label = QLabel("Движок:")
        engine_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        engine_label.setMinimumWidth(80)
        engine_row.addWidget(engine_label)
        
        self.tts_engine_combo = QComboBox()
        self.tts_engine_combo.setStyleSheet(COMBO_BOX_STYLE)
        self.tts_engine_combo.addItem("🚀 Silero (быстрый, офлайн)", "silero")
        self.tts_engine_combo.addItem("⚡ Piper (очень быстрый, офлайн)", "piper")
        self.tts_engine_combo.addItem("🎵 Kokoro (высокое качество)", "kokoro")
        self.tts_engine_combo.addItem("🎭 StyleTTS 2 (экспрессивный)", "styletts2")
        self.tts_engine_combo.addItem("🎤 F5-TTS (клонирование голоса)", "f5tts")
        self.tts_engine_combo.addItem("🌳 Bark (многоязычный)", "bark")
        self.tts_engine_combo.currentIndexChanged.connect(self._on_tts_engine_changed)
        engine_row.addWidget(self.tts_engine_combo, 1)
        engine_layout.addLayout(engine_row)
        
        # Engine description
        self.tts_engine_desc = QLabel("Быстрый офлайн синтез речи. Русский, английский, немецкий.")
        self.tts_engine_desc.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
        self.tts_engine_desc.setWordWrap(True)
        engine_layout.addWidget(self.tts_engine_desc)
        
        # Engine status (installed/not installed)
        self.tts_engine_status = QLabel("✓ Установлен")
        self.tts_engine_status.setStyleSheet(f"color: {COLORS['success']}; font-size: 11px;")
        engine_layout.addWidget(self.tts_engine_status)
        
        layout.addWidget(engine_group)
        
        # ============ Model and Voice Selection Group ============
        active_group = QGroupBox("🎛️ Настройки модели и голоса")
        active_group.setStyleSheet(GROUP_BOX_STYLE)
        active_layout = QVBoxLayout(active_group)
        active_layout.setContentsMargins(12, 16, 12, 12)
        active_layout.setSpacing(8)
        
        # Model/Language selection
        model_row = QHBoxLayout()
        model_label = QLabel("Модель/Язык:")
        model_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        model_label.setMinimumWidth(90)
        model_row.addWidget(model_label)
        
        self.tts_model_combo = QComboBox()
        self.tts_model_combo.setStyleSheet(COMBO_BOX_STYLE)
        self.tts_model_combo.setMaxVisibleItems(12)  # Show more items in dropdown
        self._update_tts_model_combo()
        self.tts_model_combo.currentIndexChanged.connect(self._on_tts_model_changed)
        model_row.addWidget(self.tts_model_combo, 1)
        active_layout.addLayout(model_row)
        
        # Voice selection
        voice_row = QHBoxLayout()
        voice_label = QLabel("Голос:")
        voice_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        voice_label.setMinimumWidth(90)
        voice_row.addWidget(voice_label)
        
        self.tts_voice_combo = QComboBox()
        self.tts_voice_combo.setStyleSheet(COMBO_BOX_STYLE)
        self.tts_voice_combo.setMaxVisibleItems(15)  # Show more voices
        self._populate_tts_voices()
        self.tts_voice_combo.currentIndexChanged.connect(self._on_tts_voice_changed)
        voice_row.addWidget(self.tts_voice_combo, 1)
        active_layout.addLayout(voice_row)
        
        # Speed control (for engines that support it)
        speed_row = QHBoxLayout()
        speed_label = QLabel("Скорость:")
        speed_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        speed_label.setMinimumWidth(90)
        speed_row.addWidget(speed_label)
        
        self.tts_speed_combo = QComboBox()
        self.tts_speed_combo.setStyleSheet(COMBO_BOX_STYLE)
        self.tts_speed_combo.addItem("🐢 Медленно (0.8x)", "0.8")
        self.tts_speed_combo.addItem("🚶 Нормально (1.0x)", "1.0")
        self.tts_speed_combo.addItem("🏃 Быстро (1.2x)", "1.2")
        self.tts_speed_combo.addItem("🚀 Очень быстро (1.5x)", "1.5")
        self.tts_speed_combo.setCurrentIndex(1)  # Default normal
        speed_row.addWidget(self.tts_speed_combo, 1)
        active_layout.addLayout(speed_row)
        
        # Save button row
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        
        self.btn_test_tts = QPushButton("🔊 Тест")
        self.btn_test_tts.setStyleSheet(SECONDARY_BUTTON_STYLE)
        self.btn_test_tts.setToolTip("Прослушать выбранный голос")
        self.btn_test_tts.clicked.connect(self._on_test_tts)
        btn_row.addWidget(self.btn_test_tts)
        
        self.btn_save_tts = QPushButton("💾 Сохранить")
        self.btn_save_tts.setStyleSheet(SECONDARY_BUTTON_STYLE)
        self.btn_save_tts.clicked.connect(self._on_save_tts_settings)
        btn_row.addWidget(self.btn_save_tts)
        active_layout.addLayout(btn_row)
        
        layout.addWidget(active_group)
        
        # ============ Available TTS Engines Group ============
        engines_group = QGroupBox("📦 Доступные TTS движки")
        engines_group.setStyleSheet(GROUP_BOX_STYLE)
        engines_layout = QVBoxLayout(engines_group)
        engines_layout.setContentsMargins(12, 16, 12, 12)
        engines_layout.setSpacing(8)
        
        # TTS engines info grid
        self.tts_engines_container = QWidget()
        self.tts_engines_layout = QVBoxLayout(self.tts_engines_container)
        self.tts_engines_layout.setContentsMargins(0, 0, 0, 0)
        self.tts_engines_layout.setSpacing(8)
        
        # Populate engine cards
        self._populate_tts_engines()
        
        engines_layout.addWidget(self.tts_engines_container)
        layout.addWidget(engines_group)
        
        # ============ Language Models Section ============
        langs_group = QGroupBox("🌍 Языковые наборы (по движку)")
        langs_group.setStyleSheet(GROUP_BOX_STYLE)
        langs_layout = QVBoxLayout(langs_group)
        langs_layout.setContentsMargins(12, 16, 12, 12)
        langs_layout.setSpacing(8)
        
        self.tts_langs_container = QWidget()
        self.tts_langs_layout = QVBoxLayout(self.tts_langs_container)
        self.tts_langs_layout.setContentsMargins(0, 0, 0, 0)
        self.tts_langs_layout.setSpacing(6)
        
        # Populate language info
        self._populate_tts_languages()
        
        langs_layout.addWidget(self.tts_langs_container)
        layout.addWidget(langs_group)
        
        # Spacer at bottom
        layout.addStretch()
        
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll, 1)
        
        # Bottom action bar (always visible)
        action_bar = QFrame()
        action_bar.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_secondary']};
                border-top: 1px solid {COLORS['border']};
                padding: 8px;
            }}
        """)
        action_layout = QHBoxLayout(action_bar)
        action_layout.setContentsMargins(16, 8, 16, 8)
        
        self.btn_preload_tts = QPushButton("📥 Скачать выбранную модель")
        self.btn_preload_tts.setStyleSheet(PRIMARY_BUTTON_STYLE)
        self.btn_preload_tts.clicked.connect(self._on_preload_tts)
        action_layout.addWidget(self.btn_preload_tts)
        
        action_layout.addStretch()
        
        self.btn_download_all_langs = QPushButton("📦 Скачать все языки")
        self.btn_download_all_langs.setStyleSheet(SECONDARY_BUTTON_STYLE)
        self.btn_download_all_langs.setToolTip("Скачать все доступные языковые модели для текущего движка")
        self.btn_download_all_langs.clicked.connect(self._on_download_all_tts_langs)
        action_layout.addWidget(self.btn_download_all_langs)
        
        main_layout.addWidget(action_bar)
        
        # Load saved selections
        self._load_voice_settings()
        
        return tab
    
    def _populate_tts_engines(self):
        """Populate TTS engines info cards"""
        # Clear existing
        while self.tts_engines_layout.count():
            item = self.tts_engines_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        engines_info = [
            ("silero", "🚀 Silero TTS", "Быстрый офлайн. ru/en/de", "~50 МБ"),
            ("piper", "⚡ Piper TTS", "Очень быстрый VITS. ru/en/de/uk/es", "~20-100 МБ"),
            ("kokoro", "🎵 Kokoro TTS", "Высокое качество. en/ja/zh/ko", "~500 МБ"),
            ("styletts2", "🎭 StyleTTS 2", "Экспрессивный. en", "~800 МБ"),
            ("f5tts", "🎤 F5-TTS", "Клонирование голоса. multi", "~1.2 ГБ"),
            ("bark", "🌳 Bark", "Многоязычный. multi", "~5 ГБ"),
        ]
        
        for engine_id, name, desc, size in engines_info:
            # Check if engine is installed
            installed = False
            if self.voice_manager:
                installed = self.voice_manager.is_tts_engine_installed(engine_id)
            
            card = QFrame()
            card.setObjectName(f"engine_card_{engine_id}")
            card.setStyleSheet(f"""
                QFrame#engine_card_{engine_id} {{
                    background-color: {COLORS['bg_primary']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 6px;
                    padding: 8px;
                }}
            """)
            card_layout = QHBoxLayout(card)
            card_layout.setContentsMargins(8, 6, 8, 6)
            card_layout.setSpacing(8)
            
            # Info
            info_layout = QVBoxLayout()
            info_layout.setSpacing(2)
            
            name_label = QLabel(name)
            name_label.setStyleSheet(f"color: {COLORS['text_primary']}; font-weight: bold; font-size: 12px;")
            info_layout.addWidget(name_label)
            
            desc_label = QLabel(f"{desc} • {size}")
            desc_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 10px;")
            info_layout.addWidget(desc_label)
            
            card_layout.addLayout(info_layout, 1)
            
            # Status/Action
            if installed:
                status = QLabel("✓ Установлен")
                status.setStyleSheet(f"color: {COLORS['success']}; font-size: 11px;")
                card_layout.addWidget(status)
            else:
                btn = QPushButton("Установить")
                btn.setFixedWidth(80)
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {COLORS['accent']};
                        color: white;
                        border: none;
                        border-radius: 4px;
                        padding: 4px 8px;
                        font-size: 11px;
                    }}
                    QPushButton:hover {{
                        background-color: {COLORS['accent_hover']};
                    }}
                """)
                btn.clicked.connect(lambda checked, eid=engine_id: self._on_install_tts_engine(eid))
                card_layout.addWidget(btn)
            
            self.tts_engines_layout.addWidget(card)
    
    def _populate_tts_languages(self):
        """Populate language models info"""
        # Clear existing
        while self.tts_langs_layout.count():
            item = self.tts_langs_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Languages per current engine
        current_engine = self.tts_engine_combo.currentData() if hasattr(self, 'tts_engine_combo') else "silero"
        
        langs_by_engine = {
            "silero": [
                ("🇷🇺 Русский", "v3_1_ru", True),
                ("🇬🇧 English", "v3_en", True),
                ("🇩🇪 Deutsch", "v3_de", True),
                ("🇪🇸 Español", "v3_es", False),
                ("🇫🇷 Français", "v3_fr", False),
            ],
            "piper": [
                ("🇷🇺 Русский", "ru_RU-ruslan", True),
                ("🇬🇧 English (US)", "en_US-lessac", True),
                ("🇬🇧 English (GB)", "en_GB-alan", False),
                ("🇩🇪 Deutsch", "de_DE-thorsten", False),
                ("🇺🇦 Українська", "uk_UA-lada", False),
                ("🇪🇸 Español", "es_ES-sharvard", False),
            ],
            "kokoro": [
                ("🇬🇧 English", "kokoro-en-v1", True),
                ("🇯🇵 日本語", "kokoro-ja-v1", False),
                ("🇨🇳 中文", "kokoro-zh-v1", False),
                ("🇰🇷 한국어", "kokoro-ko-v1", False),
            ],
            "styletts2": [
                ("🇬🇧 English", "styletts2-ljspeech", True),
            ],
            "f5tts": [
                ("🌍 Multilingual", "f5-tts-base", True),
            ],
            "bark": [
                ("🌍 Multilingual", "bark-small", False),
            ],
        }
        
        langs = langs_by_engine.get(current_engine, [])
        
        for lang_name, model_id, installed in langs:
            row = QFrame()
            row.setStyleSheet(f"""
                QFrame {{
                    background-color: {COLORS['bg_primary']};
                    border-radius: 4px;
                    padding: 4px;
                }}
            """)
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(8, 4, 8, 4)
            row_layout.setSpacing(8)
            
            lang_label = QLabel(lang_name)
            lang_label.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 12px;")
            row_layout.addWidget(lang_label)
            
            model_label = QLabel(model_id)
            model_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 10px;")
            row_layout.addWidget(model_label, 1)
            
            if installed:
                status = QLabel("✓")
                status.setStyleSheet(f"color: {COLORS['success']}; font-size: 12px;")
                row_layout.addWidget(status)
            else:
                btn = QPushButton("📥")
                btn.setFixedSize(24, 24)
                btn.setToolTip(f"Скачать {lang_name}")
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: transparent;
                        color: {COLORS['accent']};
                        border: 1px solid {COLORS['accent']};
                        border-radius: 4px;
                        font-size: 10px;
                    }}
                    QPushButton:hover {{
                        background-color: {COLORS['accent']};
                        color: white;
                    }}
                """)
                btn.clicked.connect(lambda checked, mid=model_id: self._on_download_tts_lang(mid))
                row_layout.addWidget(btn)
            
            self.tts_langs_layout.addWidget(row)
    
    def _on_install_tts_engine(self, engine_id: str):
        """Handle TTS engine installation"""
        if not self.voice_manager:
            QMessageBox.warning(self, "Ошибка", "Менеджер моделей не инициализирован")
            return
        
        engine_names = {
            "silero": "Silero TTS",
            "piper": "Piper TTS",
            "kokoro": "Kokoro TTS",
            "styletts2": "StyleTTS 2",
            "f5tts": "F5-TTS",
            "bark": "Bark TTS",
        }
        engine_name = engine_names.get(engine_id, engine_id)
        
        # Confirm installation
        reply = QMessageBox.question(
            self,
            "Установка TTS движка",
            f"Установить {engine_name}?\n\n"
            "Это может занять несколько минут и потребовать загрузки данных из интернета.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Show progress
        self.progress_widget.show()
        self.progress_bar.setValue(0)
        self.progress_label.setText(f"Установка {engine_name}...")
        
        # Connect signals for progress updates
        self.voice_manager.progress.connect(self._on_tts_install_progress)
        self.voice_manager.operation_finished.connect(self._on_tts_install_finished)
        
        # Start installation in a thread
        import threading
        thread = threading.Thread(
            target=self.voice_manager.install_tts_engine,
            args=(engine_id,),
            daemon=True
        )
        thread.start()
    
    def _on_tts_install_progress(self, percent: int, message: str):
        """Handle TTS installation progress"""
        self.progress_bar.setValue(percent)
        self.progress_label.setText(message)
    
    def _on_tts_install_finished(self, success: bool, message: str):
        """Handle TTS installation completion"""
        # Disconnect signals
        try:
            self.voice_manager.progress.disconnect(self._on_tts_install_progress)
            self.voice_manager.operation_finished.disconnect(self._on_tts_install_finished)
        except:
            pass
        
        # Hide progress
        self.progress_widget.hide()
        
        # Show result
        if success:
            QMessageBox.information(self, "Успех", message)
            # Refresh the TTS engines list and status
            self._populate_tts_engines()
            self._populate_tts_languages()
            # Update engine status in the selection section
            self._update_tts_engine_status()
        else:
            QMessageBox.warning(self, "Ошибка", message)
    
    def _update_tts_engine_status(self):
        """Update the TTS engine installation status display"""
        if not hasattr(self, 'tts_engine_combo') or not hasattr(self, 'tts_engine_status'):
            return
        
        engine = self.tts_engine_combo.currentData()
        is_installed = False
        
        if self.voice_manager:
            is_installed = self.voice_manager.is_tts_engine_installed(engine)
        
        if is_installed:
            self.tts_engine_status.setText("✓ Установлен")
            self.tts_engine_status.setStyleSheet(f"color: {COLORS['success']}; font-size: 11px;")
        else:
            self.tts_engine_status.setText("⚠ Не установлен (нажмите 'Установить' ниже)")
            self.tts_engine_status.setStyleSheet(f"color: {COLORS['warning']}; font-size: 11px;")
    
    def _on_download_tts_lang(self, model_id: str):
        """Handle language model download"""
        QMessageBox.information(
            self,
            "Скачивание",
            f"Скачивание модели {model_id}...\n"
            "Эта функция будет доступна в следующем обновлении."
        )
    
    def _on_download_all_tts_langs(self):
        """Download all language models for current engine"""
        engine = self.tts_engine_combo.currentData()
        QMessageBox.information(
            self,
            "Скачивание всех языков",
            f"Скачивание всех языковых моделей для {engine}...\n"
            "Эта функция будет доступна в следующем обновлении."
        )
    
    def _on_test_tts(self):
        """Test current TTS voice - generate and play speech"""
        import tempfile
        import threading
        import subprocess
        import os
        from pathlib import Path
        
        # Get current settings
        engine = self.tts_engine_combo.currentData() if hasattr(self, 'tts_engine_combo') else "silero"
        voice = self.tts_voice_combo.currentData() if hasattr(self, 'tts_voice_combo') else "aidar"
        
        # Test text
        test_text = "Привет! Это тест синтеза речи."
        
        # Find Arvis-Client path - try multiple locations
        # Current file: Arvis-Launcher/src/arvis_launcher/ui/pages/models_page.py
        current_file = Path(__file__).resolve()
        
        # Method 1: Look for Arvis-Client-master in parent directory (same level as Arvis-Launcher)
        # File: /Arvis/Arvis-Launcher/src/arvis_launcher/ui/pages/models_page.py
        # We need to go up to /Arvis where both Arvis-Launcher and Arvis-Client-master are
        workspace_root = current_file.parents[5]  # Go up to /Arvis
        arvis_client_path = workspace_root / "Arvis-Client-master"
        
        if not arvis_client_path.exists():
            # Method 2: Look for Arvis-Client
            arvis_client_path = workspace_root / "Arvis-Client"
        
        if not arvis_client_path.exists():
            # Method 3: Try current file's parent directories more carefully
            # File: /Arvis/Arvis-Launcher/src/arvis_launcher/ui/pages/models_page.py
            # We need: /Arvis/Arvis-Client-master
            arvis_client_path = current_file.parents[4] / "Arvis-Client-master"
        
        if not arvis_client_path.exists():
            arvis_client_path = current_file.parents[4] / "Arvis-Client"
        
        # Check for modules directory
        worker_path = arvis_client_path / "modules" / "tts_worker_subprocess.py"
        
        print(f"DEBUG: Current file: {current_file}")
        print(f"DEBUG: Workspace root: {workspace_root}")
        print(f"DEBUG: Arvis client path: {arvis_client_path}")
        print(f"DEBUG: Worker path: {worker_path}")
        print(f"DEBUG: Worker exists: {worker_path.exists()}")
        
        if not worker_path.exists():
            QMessageBox.warning(
                self,
                "Ошибка",
                f"TTS worker не найден: {worker_path}\\n\\nПроверьте, что Arvis-Client установлен рядом с Arvis-Launcher."
            )
            return
        
        # Use venv python if available
        venv_python = arvis_client_path / "venv" / "Scripts" / "python.exe"
        if not venv_python.exists():
            venv_python = arvis_client_path / "venv" / "bin" / "python"  # Linux/Mac
        if not venv_python.exists():
            venv_python = sys.executable
        
        # Create temp file for output
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            output_file = tmp.name
        
        try:
            # Build command
            args = [
                str(venv_python),
                str(worker_path),
                "--text",
                test_text,
                "--voice",
                voice,
                "--sample-rate",
                "48000",
                "--device",
                "cpu",
                "--output",
                output_file,
                "--sapi-enabled",
            ]
            
            # Run in thread to not block UI
            def run_tts():
                try:
                    result = subprocess.run(
                        args,
                        capture_output=True,
                        text=True,
                        timeout=45,
                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                    )
                    
                    # Check for errors
                    if result.returncode != 0:
                        print(f"TTS worker error: {result.stderr}")
                    
                    # Play audio
                    if Path(output_file).exists():
                        import soundfile as sf
                        import sounddevice as sd
                        
                        data, sr = sf.read(output_file, dtype='float32')
                        sd.play(data, samplerate=sr)
                        sd.wait()
                        print("TTS playback finished")
                    
                except subprocess.TimeoutExpired:
                    print("TTS generation timed out")
                except Exception as e:
                    print(f"TTS test error: {e}")
                finally:
                    # Cleanup
                    try:
                        Path(output_file).unlink(missing_ok=True)
                    except:
                        pass
            
            # Start generation
            self.btn_test_tts.setEnabled(False)
            self.btn_test_tts.setText("🔊 Генерация...")
            
            def on_finished():
                self.btn_test_tts.setEnabled(True)
                self.btn_test_tts.setText("🔊 Тест")
            
            thread = threading.Thread(target=run_tts, daemon=True)
            thread.start()
            
            # Schedule re-enable after a delay (approximate)
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(5000, on_finished)
            
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Ошибка запуска TTS: {e}")
            try:
                Path(output_file).unlink(missing_ok=True)
            except:
                pass
    
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
        self.models_scroll.setStyleSheet(SCROLL_AREA_STYLE + """
            QScrollArea { background-color: transparent; border: none; }
        """)
        
        self.models_container = QWidget()
        self.models_layout = QVBoxLayout(self.models_container)
        self.models_layout.setContentsMargins(0, 0, 8, 0)
        self.models_layout.setSpacing(8)
        
        # Add model cards
        self._refresh_models_list()
        
        self.models_scroll.setWidget(self.models_container)
    
    def _refresh_models_list(self):
        """Refresh the list of available models"""
        # Clear existing cards
        while self.models_layout.count():
            item = self.models_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Check if ollama is available
        if not self.ollama.is_available():
            label = QLabel("Ollama не запущена. Запустите Ollama для работы с моделями.")
            label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px; padding: 8px;")
            self.models_layout.addWidget(label)
            return
        
        # Get installed models
        installed_models = self.ollama.get_installed_models()
        
        # Check for updates
        try:
            updates = self.ollama.check_updates()
        except Exception:
            updates = []
        
        # Add model cards
        for model in installed_models:
            has_update = model.name in updates
            card = self._create_model_card(model, has_update)
            self.models_layout.addWidget(card)
        
        # Add placeholder if no models
        if not installed_models:
            label = QLabel("Модели не установлены. Выберите и установите модель из списка рекомендуемых.")
            label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px; padding: 8px;")
            label.setWordWrap(True)
            self.models_layout.addWidget(label)
    
    def _create_model_card(self, model: OllamaModel, has_update: bool = False) -> QWidget:
        """Create a card for a model"""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_secondary']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 8px;
            }}
        """)
        
        layout = QHBoxLayout(card)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)
        
        # Icon
        icon = QLabel("🤖")
        icon.setStyleSheet("font-size: 20px;")
        layout.addWidget(icon)
        
        # Info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        
        name = QLabel(model.display_name)
        name.setStyleSheet(f"color: {COLORS['text_primary']}; font-weight: bold; font-size: 13px;")
        info_layout.addWidget(name)
        
        details = QLabel(f"{model.name}")
        details.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px;")
        info_layout.addWidget(details)
        
        layout.addLayout(info_layout, 1)
        
        # Update indicator or delete button
        if has_update:
            update_btn = QPushButton("⬆️ Обновить")
            update_btn.setFixedWidth(100)
            update_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['accent']};
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 4px 8px;
                    font-size: 11px;
                }}
                QPushButton:hover {{
                    background-color: {COLORS['accent_hover']};
                }}
            """)
            update_btn.clicked.connect(lambda: self._on_update_model(model.name))
            layout.addWidget(update_btn)
        else:
            delete_btn = QPushButton("✕")
            delete_btn.setFixedSize(28, 28)
            delete_btn.setStyleSheet(f"""
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
            delete_btn.clicked.connect(lambda: self._on_remove_model(model.name))
            layout.addWidget(delete_btn)
        
        return card
    
    def _refresh_stt_list(self):
        """Refresh STT models list"""
        # Clear existing
        while self.stt_layout.count():
            item = self.stt_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        if not self.voice_manager:
            return
        
        # Get available STT models
        stt_models = self.voice_manager.get_stt_models()
        
        for model in stt_models:
            card = VoiceModelCard(
                model=model,
                on_install=lambda m: self._on_install_stt_model(m),
                on_remove=lambda m: self._on_remove_stt_model(m),
            )
            self.stt_layout.addWidget(card)
    
    def _on_install_stt_model(self, model: VoiceModel):
        """Handle STT model installation"""
        QMessageBox.information(
            self,
            "Скачивание STT модели",
            f"Скачивание модели {model.display_name}...\n"
            "Эта функция будет доступна в следующем обновлении."
        )
    
    def _on_remove_stt_model(self, model: VoiceModel):
        """Handle STT model removal"""
        reply = QMessageBox.question(
            self,
            "Удаление модели",
            f"Удалить {model.display_name}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        self.voice_manager.remove_model(model)
        self._refresh_stt_list()
    
    def _on_update_model(self, model_name: str):
        """Update a model"""
        QMessageBox.information(
            self,
            "Обновление модели",
            f"Обновление модели {model_name}...\n"
            "Эта функция будет доступна в следующем обновлении."
        )
    
    def _on_remove_model(self, model_name: str):
        """Remove a model"""
        reply = QMessageBox.question(
            self,
            "Удаление модели",
            f"Удалить {model_name}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        try:
            success = self.ollama.remove_model(model_name)
            if success:
                self._refresh_models_list()
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось удалить модель")
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Ошибка удаления: {e}")
    
    def _connect_signals(self):
        """Connect signals"""
        self.ollama.status_changed.connect(self._on_ollama_status_changed)
        self.ollama.models_changed.connect(self._on_ollama_models_changed)
    
    def _on_ollama_status_changed(self, status: OllamaState, message: str):
        """Handle Ollama status changes"""
        if hasattr(self, 'ollama_status_label'):
            self.ollama_status_label.setText(message)
            
            if status == OllamaState.RUNNING:
                self.ollama_status_label.setStyleSheet(f"color: {COLORS['success']}; font-size: 12px;")
                self.btn_start_ollama.hide()
                self.btn_stop_ollama.show()
                self.btn_install_ollama.hide()
            elif status == OllamaState.STOPPED:
                self.ollama_status_label.setStyleSheet(f"color: {COLORS['warning']}; font-size: 12px;")
                self.btn_start_ollama.show()
                self.btn_stop_ollama.hide()
                self.btn_install_ollama.hide()
            elif status == OllamaState.NOT_INSTALLED:
                self.ollama_status_label.setStyleSheet(f"color: {COLORS['error']}; font-size: 12px;")
                self.btn_start_ollama.hide()
                self.btn_stop_ollama.hide()
                self.btn_install_ollama.show()
            else:
                self.ollama_status_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
    
    def _on_ollama_models_changed(self):
        """Handle Ollama models changes"""
        self._refresh_models_list()
        self._update_llm_combo()
    
    def _on_llm_model_changed(self, text: str):
        """Handle LLM model selection change"""
        pass
    
    def _on_save_llm_model(self):
        """Save selected LLM model"""
        current = self.llm_model_combo.currentText()
        if not current:
            QMessageBox.warning(self, "Предупреждение", "Выберите модель")
            return
        
        model_name = current.split(" (")[0] if " (" in current else current
        self.config.set("llm.model", model_name)
        self.config.save()
        QMessageBox.information(self, "Успех", f"Модель {model_name} сохранена")
    
    def _on_stt_model_changed(self, text: str):
        """Handle STT model selection change"""
        pass
    
    def _on_save_stt_model(self):
        """Save selected STT model"""
        current = self.stt_model_combo.currentText()
        if not current:
            QMessageBox.warning(self, "Предупреждение", "Выберите модель")
            return
        
        self.config.set("stt.model", current)
        self.config.save()
        QMessageBox.information(self, "Успех", f"Модель STT сохранена: {current}")
    
    def _update_llm_combo(self):
        """Update LLM model combo box"""
        self.llm_model_combo.clear()
        
        if not self.ollama.is_available():
            return
        
        # Get installed models
        installed_models = self.ollama.get_installed_models()
        
        # Get recommended models
        recommended = [m for m in RECOMMENDED_MODELS if m not in [im.name for im in installed_models]]
        
        # Add installed models first
        for model in installed_models:
            self.llm_model_combo.addItem(f"{model.display_name} (установлена)", model.name)
        
        # Add recommended models
        for model_name in recommended:
            self.llm_model_combo.addItem(f"{model_name} (рекомендуется)", model_name)
        
        # Restore saved selection
        saved_model = self.config.get("llm.model")
        if saved_model:
            index = self.llm_model_combo.findData(saved_model)
            if index >= 0:
                self.llm_model_combo.setCurrentIndex(index)
    
    def _update_stt_combo(self):
        """Update STT model combo box"""
        self.stt_model_combo.clear()
        
        if not self.voice_manager:
            return
        
        # Get available STT models
        stt_models = self.voice_manager.get_stt_models()
        
        for model in stt_models:
            if model.is_installed:
                self.stt_model_combo.addItem(f"{model.display_name} ✓", model.name)
            else:
                self.stt_model_combo.addItem(model.display_name, model.name)
        
        # Restore saved selection
        saved_model = self.config.get("stt.model")
        if saved_model:
            index = self.stt_model_combo.findData(saved_model)
            if index >= 0:
                self.stt_model_combo.setCurrentIndex(index)
    
    def _on_tts_engine_changed(self, index: int):
        """Handle TTS engine selection change"""
        engine_id = self.tts_engine_combo.itemData(index)
        
        # Update description
        descriptions = {
            "silero": "Быстрый офлайн синтез речи. Русский, английский, немецкий.",
            "piper": "Очень быстрый VITS синтез. Много голосов, высокое качество.",
            "kokoro": "Высококачественный нейросетевой TTS. Английский, японский, китайский, корейский.",
            "styletts2": "Экспрессивный TTS с передачей стиля речи. Только английский.",
            "f5tts": "Zero-shot клонирование голоса по короткому образцу. Мультиязычный.",
            "bark": "Многоязычный TTS с генерацией эмоций. Требует много памяти.",
        }
        self.tts_engine_desc.setText(descriptions.get(engine_id, ""))
        
        # Update engine status
        self._update_tts_engine_status()
        
        # Update model combo
        self._update_tts_model_combo(engine_id)
        
        # Update voices
        self._populate_tts_voices()
        
        # Update languages
        self._populate_tts_languages()
    
    def _update_tts_model_combo(self, engine: str = None):
        """Update TTS model/language combo based on selected engine"""
        if engine is None:
            engine = self.tts_engine_combo.currentData()
        
        self.tts_model_combo.clear()
        
        models_by_engine = {
            "silero": [("Русский v3.1", "v3_1_ru"), ("English v3", "v3_en"), ("Deutsch v3", "v3_de")],
            "piper": [("Русский", "ru_RU"), ("English US", "en_US"), ("English GB", "en_GB"), ("Deutsch", "de_DE"), ("Українська", "uk_UA")],
            "kokoro": [("English", "en"), ("日本語", "ja"), ("中文", "zh"), ("한국어", "ko")],
            "styletts2": [("English LJSpeech", "ljspeech"), ("English LibriTTS", "libritts")],
            "f5tts": [("Multilingual", "base")],
            "bark": [("Multilingual", "small")],
        }
        
        models = models_by_engine.get(engine, [])
        for name, model_id in models:
            self.tts_model_combo.addItem(name, model_id)
    
    def _populate_tts_voices(self):
        """Populate TTS voices based on selected engine/model"""
        self.tts_voice_combo.clear()
        
        engine = self.tts_engine_combo.currentData()
        
        voices_by_engine = {
            "silero": [
                ("aidar (женский)", "aidar"),
                ("baya (женский)", "baya"),
                ("kseniya (женский)", "kseniya"),
                ("xenia (женский)", "xenia"),
                ("eugene (мужской)", "eugene"),
                ("random (случайный)", "random"),
            ],
            "piper": [
                ("Ирина (RU)", "irina"),
                ("Дмитрий (RU)", "dmitri"),
                ("Lessac (EN)", "lessac"),
                ("Amy (EN)", "amy"),
                ("Thorsten (DE)", "thorsten"),
            ],
            "kokoro": [
                ("af_heart (женский)", "af_heart"),
                ("af_sarah (женский)", "af_sarah"),
                ("am_adam (мужской)", "am_adam"),
                ("am_michael (мужской)", "am_michael"),
            ],
            "styletts2": [
                ("LJSpeech", "ljspeech"),
            ],
            "f5tts": [
                ("Default (male)", "male"),
                ("Default (female)", "female"),
            ],
            "bark": [
                ("Default", "v2"),
            ],
        }
        
        voices = voices_by_engine.get(engine, [("Default", "default")])
        for name, voice_id in voices:
            self.tts_voice_combo.addItem(name, voice_id)
    
    def _on_tts_model_changed(self, index: int):
        """Handle TTS model selection change"""
        pass
    
    def _on_tts_voice_changed(self, index: int):
        """Handle TTS voice selection change"""
        pass
    
    def _on_save_tts_settings(self):
        """Save TTS settings"""
        engine = self.tts_engine_combo.currentData()
        model = self.tts_model_combo.currentData()
        voice = self.tts_voice_combo.currentData()
        speed = self.tts_speed_combo.currentData()
        
        self.config.set("tts.engine", engine)
        self.config.set("tts.model", model)
        self.config.set("tts.voice", voice)
        self.config.set("tts.speed", speed)
        # Keep legacy/launcher-specific voice_models in sync
        try:
            self.config.set("voice_models.tts_engine", engine)
            self.config.set("voice_models.tts_model", model)
            self.config.set("voice_models.tts_voice", voice)
        except Exception:
            pass
        self.config.save()
        
        QMessageBox.information(self, "Успех", "Настройки TTS сохранены")
    
    def _load_voice_settings(self):
        """Load saved voice settings"""
        # Load engine
        # Support both new `tts.*` keys and legacy `voice_models.*` keys
        saved_engine = self.config.get("tts.engine", None)
        if not saved_engine:
            saved_engine = self.config.get("voice_models.tts_engine", "silero")
        engine_idx = self.tts_engine_combo.findData(saved_engine)
        if engine_idx >= 0:
            self.tts_engine_combo.setCurrentIndex(engine_idx)
        else:
            self.tts_engine_combo.setCurrentIndex(0)
        
        # Load model
        saved_model = self.config.get("tts.model") or self.config.get("voice_models.tts_model")
        if saved_model:
            idx = self.tts_model_combo.findData(saved_model)
            if idx >= 0:
                self.tts_model_combo.setCurrentIndex(idx)
        
        # Load voice - validate that saved voice is valid for current engine
        saved_voice = self.config.get("tts.voice") or self.config.get("voice_models.tts_voice")
        engine = self.tts_engine_combo.currentData()
        
        # Define valid voices per engine
        valid_voices_by_engine = {
            "silero": ["aidar", "baya", "kseniya", "xenia", "eugene", "random"],
            "piper": ["irina", "dmitri", "lessac", "amy", "thorsten"],
            "kokoro": ["af_heart", "af_sarah", "am_adam", "am_michael"],
            "styletts2": ["ljspeech"],
            "f5tts": ["male", "female"],
            "bark": ["v2"],
        }
        
        # Validate saved voice
        valid_voices = valid_voices_by_engine.get(engine, [])
        if saved_voice and saved_voice in valid_voices:
            idx = self.tts_voice_combo.findData(saved_voice)
            if idx >= 0:
                self.tts_voice_combo.setCurrentIndex(idx)
        else:
            # Reset to first voice if saved voice is not valid for this engine
            if self.tts_voice_combo.count() > 0:
                self.tts_voice_combo.setCurrentIndex(0)
        
        # Load speed
        saved_speed = self.config.get("tts.speed", "1.0")
        idx = self.tts_speed_combo.findData(saved_speed)
        if idx >= 0:
            self.tts_speed_combo.setCurrentIndex(idx)
    
    def _on_preload_tts(self):
        """Download selected TTS model"""
        engine = self.tts_engine_combo.currentData()
        model = self.tts_model_combo.currentData()
        
        QMessageBox.information(
            self,
            "Скачивание модели",
            f"Скачивание модели {model} для движка {engine}...\n"
            "Эта функция будет доступна в следующем обновлении."
        )
    
    def refresh(self):
        """Refresh page data"""
        # Update LLM
        self._update_llm_combo()
        self._refresh_models_list()
        
        # Update STT
        self._update_stt_combo()
        self._refresh_stt_list()
        
        # Update TTS
        self._update_tts_engine_status()
        self._populate_tts_engines()
        self._populate_tts_languages()
