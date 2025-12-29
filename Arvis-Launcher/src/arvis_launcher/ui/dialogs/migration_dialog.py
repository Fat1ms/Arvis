"""
Migration Dialog - prompts user to migrate settings from client
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QProgressBar,
    QTextEdit,
    QCheckBox,
)

from ...styles import (
    COLORS,
    PRIMARY_BUTTON_STYLE,
    SECONDARY_BUTTON_STYLE,
)
from ...migration import SettingsMigrator, MigrationResult


class MigrationDialog(QDialog):
    """Dialog for migrating settings from client to launcher"""
    
    def __init__(
        self,
        client_root: Path,
        launcher_config_path: Path,
        parent=None
    ):
        super().__init__(parent)
        self.client_root = client_root
        self.migrator = SettingsMigrator(launcher_config_path, self)
        self._result: Optional[MigrationResult] = None
        
        self.setWindowTitle("Миграция настроек")
        self.setFixedSize(500, 400)
        self.setModal(True)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {COLORS['bg_primary']};
            }}
            QLabel {{
                color: {COLORS['text_primary']};
            }}
        """)
        
        self._build_ui()
        self._connect_signals()
    
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        # Icon and title
        title = QLabel("🔄  Миграция настроек")
        title.setStyleSheet(f"""
            color: {COLORS['text_primary']};
            font-size: 20px;
            font-weight: bold;
        """)
        layout.addWidget(title)
        
        # Description
        desc = QLabel(
            "Обнаружены настройки в клиенте Arvis.\n\n"
            "Глобальные настройки (язык интерфейса, сервер, аккаунт) будут "
            "перенесены в лаунчер для централизованного управления.\n\n"
            "Настройки моделей (TTS, STT, LLM) останутся в клиенте."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 13px;")
        layout.addWidget(desc)
        
        # Migration options
        self.check_settings = QCheckBox("Перенести глобальные настройки")
        self.check_settings.setChecked(True)
        self.check_settings.setStyleSheet(f"color: {COLORS['text_primary']};")
        layout.addWidget(self.check_settings)
        
        self.check_session = QCheckBox("Перенести данные авторизации")
        self.check_session.setChecked(True)
        self.check_session.setStyleSheet(f"color: {COLORS['text_primary']};")
        layout.addWidget(self.check_session)
        
        # Progress bar (hidden initially)
        self.progress = QProgressBar()
        self.progress.setStyleSheet(f"""
            QProgressBar {{
                background-color: {COLORS['bg_tertiary']};
                border: none;
                border-radius: 4px;
                height: 8px;
            }}
            QProgressBar::chunk {{
                background-color: {COLORS['accent']};
                border-radius: 4px;
            }}
        """)
        self.progress.hide()
        layout.addWidget(self.progress)
        
        # Status log (hidden initially)
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(100)
        self.log.setStyleSheet(f"""
            QTextEdit {{
                background-color: {COLORS['bg_secondary']};
                color: {COLORS['text_secondary']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                font-family: Consolas, monospace;
                font-size: 11px;
            }}
        """)
        self.log.hide()
        layout.addWidget(self.log)
        
        layout.addStretch()
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        
        self.btn_skip = QPushButton("Пропустить")
        self.btn_skip.setStyleSheet(SECONDARY_BUTTON_STYLE)
        self.btn_skip.setMinimumWidth(120)
        btn_layout.addWidget(self.btn_skip)
        
        btn_layout.addStretch()
        
        self.btn_migrate = QPushButton("Перенести")
        self.btn_migrate.setStyleSheet(PRIMARY_BUTTON_STYLE)
        self.btn_migrate.setMinimumWidth(140)
        btn_layout.addWidget(self.btn_migrate)
        
        layout.addLayout(btn_layout)
    
    def _connect_signals(self):
        self.btn_skip.clicked.connect(self.reject)
        self.btn_migrate.clicked.connect(self._start_migration)
        
        self.migrator.migration_progress.connect(self._on_progress)
        self.migrator.migration_complete.connect(self._on_complete)
    
    def _start_migration(self):
        """Start migration process"""
        self.btn_migrate.setEnabled(False)
        self.btn_skip.setEnabled(False)
        self.progress.show()
        self.progress.setRange(0, 0)  # Indeterminate
        self.log.show()
        
        # Run migration
        self._result = self.migrator.migrate_from_client(self.client_root)
    
    def _on_progress(self, message: str):
        """Handle progress update"""
        self.log.append(message)
    
    def _on_complete(self, result: MigrationResult):
        """Handle migration completion"""
        self._result = result
        self.progress.setRange(0, 100)
        self.progress.setValue(100)
        
        if result.success:
            self.log.append(f"\n✓ Миграция завершена успешно")
            self.log.append(f"  Перенесено ключей: {len(result.migrated_keys)}")
            if result.backup_path:
                self.log.append(f"  Резервная копия: {result.backup_path}")
            
            self.btn_migrate.setText("Готово")
            self.btn_migrate.setEnabled(True)
            self.btn_migrate.clicked.disconnect()
            self.btn_migrate.clicked.connect(self.accept)
            self.btn_skip.hide()
        else:
            self.log.append(f"\n✗ Ошибка миграции:")
            for error in result.errors:
                self.log.append(f"  • {error}")
            
            self.btn_migrate.setText("Повторить")
            self.btn_migrate.setEnabled(True)
            self.btn_skip.setEnabled(True)
    
    @property
    def result(self) -> Optional[MigrationResult]:
        return self._result
