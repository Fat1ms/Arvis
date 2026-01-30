"""
Installation Wizard Dialog
Full installation with location selection, shortcuts, license agreement
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QCheckBox,
    QTextEdit,
    QFileDialog,
    QStackedWidget,
    QWidget,
    QProgressBar,
    QMessageBox,
    QFrame,
    QRadioButton,
    QButtonGroup,
)

from ...styles import (
    COLORS,
    PRIMARY_BUTTON_STYLE,
    SECONDARY_BUTTON_STYLE,
    LINE_EDIT_STYLE,
    CHECK_BOX_STYLE,
)


# MIT License text for Arvis
LICENSE_TEXT = """MIT License

Copyright (c) 2024-2026 Arvis Project

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

---

This software uses the following open-source components:

• PyQt6 - GPL v3 / Commercial License
• Vosk - Apache 2.0 License
• Silero TTS - MIT License
• Ollama - MIT License

For full license information, see the documentation.
"""


class InstallWizardDialog(QDialog):
    """Multi-step installation wizard"""
    
    installation_complete = pyqtSignal(dict)  # Emits installation config
    
    # TTS Engine info for wizard
    TTS_ENGINES_INFO = {
        "silero": {
            "name": "Silero TTS",
            "icon": "🚀",
            "desc": "Быстрый офлайн синтез. Русский, английский, немецкий.",
            "size": "~50 МБ",
            "quality": "★★★☆☆",
            "speed": "★★★★★",
            "languages": ["ru", "en", "de"],
        },
        "piper": {
            "name": "Piper TTS",
            "icon": "⚡",
            "desc": "Очень быстрый офлайн TTS на базе VITS.",
            "size": "~20-100 МБ",
            "quality": "★★★★☆",
            "speed": "★★★★★",
            "languages": ["ru", "en", "de", "uk", "es", "fr"],
        },
        "kokoro": {
            "name": "Kokoro TTS",
            "icon": "🎵",
            "desc": "Высокое качество, нейросетевой синтез.",
            "size": "~500 МБ",
            "quality": "★★★★★",
            "speed": "★★★☆☆",
            "languages": ["en", "ja", "zh", "ko", "fr", "es"],
        },
        "styletts2": {
            "name": "StyleTTS 2",
            "icon": "🎭",
            "desc": "Экспрессивный синтез с передачей стиля.",
            "size": "~800 МБ",
            "quality": "★★★★★",
            "speed": "★★☆☆☆",
            "languages": ["en"],
        },
        "f5tts": {
            "name": "F5-TTS",
            "icon": "🎤",
            "desc": "Zero-shot клонирование голоса.",
            "size": "~1.2 ГБ",
            "quality": "★★★★★",
            "speed": "★★☆☆☆",
            "languages": ["en", "zh", "ja", "ko", "fr", "de"],
        },
    }
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self.setWindowTitle("🚀 Мастер установки Arvis")
        self.setFixedSize(650, 550)
        self.setModal(True)
        
        # Installation config
        self.install_config = {
            "install_path": str(Path.home() / "Arvis"),
            "install_type": "full",  # full or compact
            "create_desktop_shortcut": True,
            "create_start_menu": True,
            "autostart_with_system": False,
            "install_dependencies": True,
            "license_accepted": False,
            "tts_engine": "silero",  # Selected TTS engine
            "install_tts_models": ["silero"],  # TTS engines to install
        }
        
        self._build_ui()
        self._connect_signals()
    
    def _build_ui(self):
        """Build the wizard UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header
        header = QFrame()
        header.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['accent']};
                padding: 20px;
            }}
        """)
        header_layout = QVBoxLayout(header)
        
        self.header_title = QLabel("Установка Arvis")
        self.header_title.setStyleSheet(f"""
            color: white;
            font-size: 18px;
            font-weight: bold;
        """)
        header_layout.addWidget(self.header_title)
        
        self.header_subtitle = QLabel("Шаг 1 из 4")
        self.header_subtitle.setStyleSheet(f"""
            color: rgba(255, 255, 255, 0.8);
            font-size: 12px;
        """)
        header_layout.addWidget(self.header_subtitle)
        
        layout.addWidget(header)
        
        # Content stack
        self.stack = QStackedWidget()
        self.stack.setStyleSheet(f"""
            QStackedWidget {{
                background-color: {COLORS['surface']};
            }}
        """)
        
        # Create pages
        self._create_welcome_page()
        self._create_license_page()
        self._create_location_page()
        self._create_tts_page()  # New TTS selection page
        self._create_options_page()
        self._create_progress_page()
        
        layout.addWidget(self.stack, 1)
        
        # Footer with navigation buttons
        footer = QFrame()
        footer.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface']};
                border-top: 1px solid {COLORS['border']};
                padding: 16px;
            }}
        """)
        footer_layout = QHBoxLayout(footer)
        
        self.btn_back = QPushButton("← Назад")
        self.btn_back.setStyleSheet(SECONDARY_BUTTON_STYLE)
        self.btn_back.setMinimumWidth(100)
        footer_layout.addWidget(self.btn_back)
        
        footer_layout.addStretch()
        
        self.btn_cancel = QPushButton("Отмена")
        self.btn_cancel.setStyleSheet(SECONDARY_BUTTON_STYLE)
        self.btn_cancel.setMinimumWidth(100)
        footer_layout.addWidget(self.btn_cancel)
        
        self.btn_next = QPushButton("Далее →")
        self.btn_next.setStyleSheet(PRIMARY_BUTTON_STYLE)
        self.btn_next.setMinimumWidth(100)
        footer_layout.addWidget(self.btn_next)
        
        layout.addWidget(footer)
        
        # Initial state
        self.btn_back.setVisible(False)
    
    def _create_welcome_page(self):
        """Page 0: Welcome"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(20)
        
        # Welcome text
        welcome = QLabel("👋 Добро пожаловать в мастер установки!")
        welcome.setStyleSheet(f"""
            color: {COLORS['text_primary']};
            font-size: 16px;
            font-weight: bold;
        """)
        layout.addWidget(welcome)
        
        description = QLabel(
            "Этот мастер поможет вам установить Arvis - вашего персонального "
            "голосового AI-ассистента.\n\n"
            "Arvis работает полностью локально и не требует подключения к интернету "
            "для основных функций.\n\n"
            "Нажмите 'Далее' для продолжения."
        )
        description.setStyleSheet(f"color: {COLORS['text_secondary']};")
        description.setWordWrap(True)
        layout.addWidget(description)
        
        # Features list
        features_frame = QFrame()
        features_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_primary']};
                border-radius: 8px;
                padding: 16px;
            }}
        """)
        features_layout = QVBoxLayout(features_frame)
        
        features_title = QLabel("✨ Возможности Arvis:")
        features_title.setStyleSheet(f"color: {COLORS['text_primary']}; font-weight: bold;")
        features_layout.addWidget(features_title)
        
        features = [
            "🎤 Голосовое управление (Vosk STT)",
            "🔊 Синтез речи (Silero TTS)",
            "🤖 Локальный AI (Ollama LLM)",
            "🌤️ Погода, новости, календарь",
            "⚙️ Управление системой",
        ]
        for feature in features:
            lbl = QLabel(feature)
            lbl.setStyleSheet(f"color: {COLORS['text_secondary']}; padding-left: 8px;")
            features_layout.addWidget(lbl)
        
        layout.addWidget(features_frame)
        layout.addStretch()
        
        self.stack.addWidget(page)
    
    def _create_license_page(self):
        """Page 1: License agreement"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(16)
        
        title = QLabel("📜 Лицензионное соглашение")
        title.setStyleSheet(f"""
            color: {COLORS['text_primary']};
            font-size: 16px;
            font-weight: bold;
        """)
        layout.addWidget(title)
        
        description = QLabel("Пожалуйста, прочитайте и примите лицензионное соглашение:")
        description.setStyleSheet(f"color: {COLORS['text_secondary']};")
        layout.addWidget(description)
        
        # License text
        license_text = QTextEdit()
        license_text.setReadOnly(True)
        license_text.setPlainText(LICENSE_TEXT)
        license_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {COLORS['bg_primary']};
                color: {COLORS['text_secondary']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 12px;
                font-family: monospace;
                font-size: 11px;
            }}
        """)
        layout.addWidget(license_text, 1)
        
        # Accept checkbox
        self.chk_accept_license = QCheckBox("Я принимаю условия лицензионного соглашения")
        self.chk_accept_license.setStyleSheet(CHECK_BOX_STYLE)
        layout.addWidget(self.chk_accept_license)
        
        self.stack.addWidget(page)
    
    def _create_location_page(self):
        """Page 2: Installation location and type"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(16)
        
        title = QLabel("📁 Папка установки")
        title.setStyleSheet(f"""
            color: {COLORS['text_primary']};
            font-size: 16px;
            font-weight: bold;
        """)
        layout.addWidget(title)
        
        # Install path
        path_layout = QHBoxLayout()
        
        path_label = QLabel("Путь:")
        path_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        path_label.setMinimumWidth(80)
        path_layout.addWidget(path_label)
        
        self.edit_install_path = QLineEdit()
        self.edit_install_path.setStyleSheet(LINE_EDIT_STYLE)
        self.edit_install_path.setText(self.install_config["install_path"])
        path_layout.addWidget(self.edit_install_path, 1)
        
        btn_browse = QPushButton("...")
        btn_browse.setFixedWidth(40)
        btn_browse.setStyleSheet(SECONDARY_BUTTON_STYLE)
        btn_browse.clicked.connect(self._browse_install_path)
        path_layout.addWidget(btn_browse)
        
        layout.addLayout(path_layout)
        
        # Space info
        self.lbl_space_info = QLabel("")
        self.lbl_space_info.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
        layout.addWidget(self.lbl_space_info)
        self._update_space_info()
        
        # Installation type
        type_title = QLabel("📦 Тип установки:")
        type_title.setStyleSheet(f"color: {COLORS['text_primary']}; font-weight: bold; margin-top: 16px;")
        layout.addWidget(type_title)
        
        self.install_type_group = QButtonGroup(self)
        
        # Full installation
        full_frame = QFrame()
        full_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 12px;
            }}
        """)
        full_layout = QVBoxLayout(full_frame)
        
        self.radio_full = QRadioButton("Полная установка (~2 ГБ)")
        self.radio_full.setChecked(True)
        self.radio_full.setStyleSheet(f"color: {COLORS['text_primary']}; font-weight: bold;")
        self.install_type_group.addButton(self.radio_full, 0)
        full_layout.addWidget(self.radio_full)
        
        full_desc = QLabel("Включает все компоненты: STT модель (Vosk), TTS модель (Silero)")
        full_desc.setStyleSheet(f"color: {COLORS['text_secondary']}; padding-left: 24px;")
        full_layout.addWidget(full_desc)
        
        layout.addWidget(full_frame)
        
        # Compact installation
        compact_frame = QFrame()
        compact_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 12px;
            }}
        """)
        compact_layout = QVBoxLayout(compact_frame)
        
        self.radio_compact = QRadioButton("Компактная установка (~500 МБ)")
        self.radio_compact.setStyleSheet(f"color: {COLORS['text_primary']}; font-weight: bold;")
        self.install_type_group.addButton(self.radio_compact, 1)
        compact_layout.addWidget(self.radio_compact)
        
        compact_desc = QLabel("Только основные файлы. Модели можно скачать позже из лаунчера.")
        compact_desc.setStyleSheet(f"color: {COLORS['text_secondary']}; padding-left: 24px;")
        compact_layout.addWidget(compact_desc)
        
        layout.addWidget(compact_frame)
        
        layout.addStretch()
        
        self.stack.addWidget(page)
    
    def _create_tts_page(self):
        """Page 3: TTS engine selection"""
        from PyQt6.QtWidgets import QScrollArea
        
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(32, 24, 32, 16)
        layout.setSpacing(12)
        
        title = QLabel("🔊 Выбор TTS движка")
        title.setStyleSheet(f"""
            color: {COLORS['text_primary']};
            font-size: 16px;
            font-weight: bold;
        """)
        layout.addWidget(title)
        
        description = QLabel(
            "Выберите движок синтеза речи. Вы сможете изменить выбор "
            "позже в настройках лаунчера и установить дополнительные движки."
        )
        description.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
        description.setWordWrap(True)
        layout.addWidget(description)
        
        # Scroll area for TTS engines
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                background-color: transparent;
                border: none;
            }}
            QScrollArea > QWidget > QWidget {{
                background-color: transparent;
            }}
        """)
        
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 8, 0)
        scroll_layout.setSpacing(8)
        
        self.tts_engine_group = QButtonGroup(self)
        self.tts_engine_checkboxes = {}
        
        for engine_id, info in self.TTS_ENGINES_INFO.items():
            frame = QFrame()
            frame.setObjectName(f"tts_frame_{engine_id}")
            frame.setStyleSheet(f"""
                QFrame#tts_frame_{engine_id} {{
                    background-color: {COLORS['bg_primary']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 8px;
                    padding: 12px;
                }}
                QFrame#tts_frame_{engine_id}:hover {{
                    border-color: {COLORS['accent']};
                }}
            """)
            frame_layout = QVBoxLayout(frame)
            frame_layout.setSpacing(4)
            
            # Header row with radio and name
            header_layout = QHBoxLayout()
            
            radio = QRadioButton(f"{info['icon']} {info['name']}")
            radio.setStyleSheet(f"color: {COLORS['text_primary']}; font-weight: bold; font-size: 13px;")
            if engine_id == "silero":
                radio.setChecked(True)
            self.tts_engine_group.addButton(radio)
            header_layout.addWidget(radio)
            
            header_layout.addStretch()
            
            # Size label
            size_label = QLabel(info['size'])
            size_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
            header_layout.addWidget(size_label)
            
            frame_layout.addLayout(header_layout)
            
            # Description
            desc_label = QLabel(info['desc'])
            desc_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px; padding-left: 24px;")
            desc_label.setWordWrap(True)
            frame_layout.addWidget(desc_label)
            
            # Quality/Speed row
            stats_layout = QHBoxLayout()
            stats_layout.setContentsMargins(24, 4, 0, 0)
            
            quality_label = QLabel(f"Качество: {info['quality']}")
            quality_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 10px;")
            stats_layout.addWidget(quality_label)
            
            speed_label = QLabel(f"Скорость: {info['speed']}")
            speed_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 10px;")
            stats_layout.addWidget(speed_label)
            
            # Languages
            langs = ", ".join(info['languages'][:4])
            if len(info['languages']) > 4:
                langs += "..."
            langs_label = QLabel(f"Языки: {langs}")
            langs_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 10px;")
            stats_layout.addWidget(langs_label)
            
            stats_layout.addStretch()
            frame_layout.addLayout(stats_layout)
            
            scroll_layout.addWidget(frame)
            self.tts_engine_checkboxes[engine_id] = radio
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll, 1)
        
        # Info about additional engines
        note = QLabel(
            "💡 Совет: Silero рекомендуется для начала. "
            "Другие движки можно установить позже из лаунчера."
        )
        note.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
        note.setWordWrap(True)
        layout.addWidget(note)
        
        self.stack.addWidget(page)
    
    def _create_options_page(self):
        """Page 4: Additional options"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(16)
        
        title = QLabel("⚙️ Дополнительные опции")
        title.setStyleSheet(f"""
            color: {COLORS['text_primary']};
            font-size: 16px;
            font-weight: bold;
        """)
        layout.addWidget(title)
        
        # Shortcuts section
        shortcuts_frame = QFrame()
        shortcuts_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_primary']};
                border-radius: 8px;
                padding: 16px;
            }}
        """)
        shortcuts_layout = QVBoxLayout(shortcuts_frame)
        
        shortcuts_title = QLabel("🔗 Ярлыки:")
        shortcuts_title.setStyleSheet(f"color: {COLORS['text_primary']}; font-weight: bold;")
        shortcuts_layout.addWidget(shortcuts_title)
        
        self.chk_desktop_shortcut = QCheckBox("Создать ярлык на рабочем столе")
        self.chk_desktop_shortcut.setChecked(True)
        self.chk_desktop_shortcut.setStyleSheet(CHECK_BOX_STYLE)
        shortcuts_layout.addWidget(self.chk_desktop_shortcut)
        
        self.chk_start_menu = QCheckBox("Добавить в меню 'Пуск'")
        self.chk_start_menu.setChecked(True)
        self.chk_start_menu.setStyleSheet(CHECK_BOX_STYLE)
        shortcuts_layout.addWidget(self.chk_start_menu)
        
        layout.addWidget(shortcuts_frame)
        
        # Startup section
        startup_frame = QFrame()
        startup_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_primary']};
                border-radius: 8px;
                padding: 16px;
            }}
        """)
        startup_layout = QVBoxLayout(startup_frame)
        
        startup_title = QLabel("🚀 Запуск:")
        startup_title.setStyleSheet(f"color: {COLORS['text_primary']}; font-weight: bold;")
        startup_layout.addWidget(startup_title)
        
        self.chk_autostart = QCheckBox("Запускать Arvis вместе с Windows")
        self.chk_autostart.setStyleSheet(CHECK_BOX_STYLE)
        startup_layout.addWidget(self.chk_autostart)
        
        layout.addWidget(startup_frame)
        
        # Dependencies section
        deps_frame = QFrame()
        deps_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_primary']};
                border-radius: 8px;
                padding: 16px;
            }}
        """)
        deps_layout = QVBoxLayout(deps_frame)
        
        deps_title = QLabel("📦 Зависимости:")
        deps_title.setStyleSheet(f"color: {COLORS['text_primary']}; font-weight: bold;")
        deps_layout.addWidget(deps_title)
        
        self.chk_install_deps = QCheckBox("Установить Python-зависимости (requirements.txt)")
        self.chk_install_deps.setChecked(True)
        self.chk_install_deps.setStyleSheet(CHECK_BOX_STYLE)
        deps_layout.addWidget(self.chk_install_deps)
        
        deps_note = QLabel("Примечание: для работы требуется Python 3.10+")
        deps_note.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px; padding-left: 24px;")
        deps_layout.addWidget(deps_note)
        
        layout.addWidget(deps_frame)
        
        layout.addStretch()
        
        self.stack.addWidget(page)
    
    def _create_progress_page(self):
        """Page 4: Installation progress"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(16)
        
        title = QLabel("📥 Установка...")
        title.setStyleSheet(f"""
            color: {COLORS['text_primary']};
            font-size: 16px;
            font-weight: bold;
        """)
        layout.addWidget(title)
        
        self.lbl_progress_status = QLabel("Подготовка к установке...")
        self.lbl_progress_status.setStyleSheet(f"color: {COLORS['text_secondary']};")
        layout.addWidget(self.lbl_progress_status)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {COLORS['bg_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                height: 24px;
                text-align: center;
                color: {COLORS['text_primary']};
            }}
            QProgressBar::chunk {{
                background-color: {COLORS['accent']};
                border-radius: 7px;
            }}
        """)
        layout.addWidget(self.progress_bar)
        
        # Log output
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setStyleSheet(f"""
            QTextEdit {{
                background-color: {COLORS['bg_primary']};
                color: {COLORS['text_secondary']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 12px;
                font-family: monospace;
                font-size: 11px;
            }}
        """)
        layout.addWidget(self.log_output, 1)
        
        self.stack.addWidget(page)
    
    def _connect_signals(self):
        """Connect signals"""
        self.btn_next.clicked.connect(self._on_next)
        self.btn_back.clicked.connect(self._on_back)
        self.btn_cancel.clicked.connect(self.reject)
        self.chk_accept_license.stateChanged.connect(self._on_license_changed)
        self.edit_install_path.textChanged.connect(self._update_space_info)
    
    def _on_next(self):
        """Handle next button"""
        current = self.stack.currentIndex()
        
        # Validation for each page
        if current == 1:  # License page
            if not self.chk_accept_license.isChecked():
                QMessageBox.warning(
                    self,
                    "Лицензия",
                    "Для продолжения необходимо принять лицензионное соглашение."
                )
                return
            self.install_config["license_accepted"] = True
        
        elif current == 2:  # Location page
            path = self.edit_install_path.text().strip()
            if not path:
                QMessageBox.warning(self, "Путь", "Укажите папку для установки.")
                return
            self.install_config["install_path"] = path
            self.install_config["install_type"] = "full" if self.radio_full.isChecked() else "compact"
        
        elif current == 3:  # TTS selection page
            # Get selected TTS engine
            for engine_id, radio in self.tts_engine_checkboxes.items():
                if radio.isChecked():
                    self.install_config["tts_engine"] = engine_id
                    self.install_config["install_tts_models"] = [engine_id]
                    break
        
        elif current == 4:  # Options page
            self.install_config["create_desktop_shortcut"] = self.chk_desktop_shortcut.isChecked()
            self.install_config["create_start_menu"] = self.chk_start_menu.isChecked()
            self.install_config["autostart_with_system"] = self.chk_autostart.isChecked()
            self.install_config["install_dependencies"] = self.chk_install_deps.isChecked()
            
            # Start installation
            self._start_installation()
        
        # Navigate
        if current < 4:
            self.stack.setCurrentIndex(current + 1)
            self._update_navigation()
    
    def _on_back(self):
        """Handle back button"""
        current = self.stack.currentIndex()
        if current > 0:
            self.stack.setCurrentIndex(current - 1)
            self._update_navigation()
    
    def _update_navigation(self):
        """Update navigation buttons and header"""
        current = self.stack.currentIndex()
        
        # Header (6 pages total: Welcome, License, Location, TTS, Options, Progress)
        titles = ["Добро пожаловать", "Лицензия", "Папка установки", "TTS движок", "Опции", "Установка"]
        self.header_title.setText(titles[current])
        self.header_subtitle.setText(f"Шаг {current + 1} из 6")
        
        # Buttons
        self.btn_back.setVisible(current > 0 and current < 5)
        
        if current == 4:
            self.btn_next.setText("Установить ✓")
        elif current == 5:
            self.btn_next.setText("Готово")
            self.btn_cancel.setVisible(False)
        else:
            self.btn_next.setText("Далее →")
    
    def _on_license_changed(self, state):
        """Handle license checkbox change"""
        # Visual feedback
        pass
    
    def _browse_install_path(self):
        """Browse for installation directory"""
        path = QFileDialog.getExistingDirectory(
            self,
            "Выберите папку для установки",
            self.edit_install_path.text() or str(Path.home())
        )
        if path:
            self.edit_install_path.setText(path)
    
    def _update_space_info(self):
        """Update disk space information"""
        path = self.edit_install_path.text().strip()
        if not path:
            self.lbl_space_info.setText("")
            return
        
        try:
            # Get drive from path
            if os.name == 'nt':
                drive = os.path.splitdrive(path)[0] or "C:"
                import ctypes
                free_bytes = ctypes.c_ulonglong(0)
                ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                    drive, None, None, ctypes.byref(free_bytes)
                )
                free_gb = free_bytes.value / (1024 ** 3)
                self.lbl_space_info.setText(f"💾 Доступно: {free_gb:.1f} ГБ")
            else:
                import shutil
                total, used, free = shutil.disk_usage(path if os.path.exists(path) else "/")
                free_gb = free / (1024 ** 3)
                self.lbl_space_info.setText(f"💾 Доступно: {free_gb:.1f} ГБ")
        except Exception:
            self.lbl_space_info.setText("")
    
    def _start_installation(self):
        """Start the installation process"""
        self.stack.setCurrentIndex(5)  # Progress page is now index 5
        self._update_navigation()
        
        # Disable buttons during installation
        self.btn_next.setEnabled(False)
        self.btn_back.setEnabled(False)
        
        # Log config
        self._log(f"📁 Папка: {self.install_config['install_path']}")
        self._log(f"📦 Тип: {'Полная' if self.install_config['install_type'] == 'full' else 'Компактная'}")
        
        # Log TTS selection
        tts_engine = self.install_config.get('tts_engine', 'silero')
        tts_info = self.TTS_ENGINES_INFO.get(tts_engine, {})
        self._log(f"🔊 TTS: {tts_info.get('name', tts_engine)}")
        
        # Simulate installation steps (in real implementation, this would be actual work)
        import threading
        thread = threading.Thread(target=self._run_installation, daemon=True)
        thread.start()
    
    def _run_installation(self):
        """Run installation in background thread"""
        import time
        from PyQt6.QtCore import QMetaObject, Qt, Q_ARG
        
        # Get TTS engine name for log
        tts_engine = self.install_config.get('tts_engine', 'silero')
        tts_info = self.TTS_ENGINES_INFO.get(tts_engine, {})
        tts_name = tts_info.get('name', tts_engine)
        
        steps = [
            (10, "Создание папки установки..."),
            (20, "Копирование файлов клиента..."),
            (40, "Копирование файлов лаунчера..."),
            (55, "Настройка конфигурации..."),
            (65, "Создание ярлыков..."),
            (75, "Установка зависимостей..."),
            (85, f"Подготовка TTS движка ({tts_name})..."),
            (95, "Скачивание TTS модели..."),
            (100, "✅ Установка завершена!"),
        ]
        
        for progress, message in steps:
            QMetaObject.invokeMethod(
                self, "_update_progress",
                Qt.ConnectionType.QueuedConnection,
                Q_ARG(int, progress),
                Q_ARG(str, message)
            )
            time.sleep(0.5)  # Simulate work
        
        # Enable finish button
        QMetaObject.invokeMethod(
            self, "_installation_finished",
            Qt.ConnectionType.QueuedConnection
        )
    
    @pyqtSlot(int, str)
    def _update_progress(self, value: int, message: str):
        """Update progress bar and status"""
        self.progress_bar.setValue(value)
        self.lbl_progress_status.setText(message)
        self._log(message)
    
    @pyqtSlot()
    def _installation_finished(self):
        """Called when installation is complete"""
        self.btn_next.setEnabled(True)
        self.btn_next.setText("Готово ✓")
        self.btn_next.clicked.disconnect()
        self.btn_next.clicked.connect(self._finish_installation)
    
    def _finish_installation(self):
        """Finish and close wizard"""
        self.installation_complete.emit(self.install_config)
        self.accept()
    
    def _log(self, message: str):
        """Add message to log"""
        self.log_output.append(message)
