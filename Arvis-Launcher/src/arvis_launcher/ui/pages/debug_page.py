"""
Debug page - Logs, diagnostics and troubleshooting
"""

from __future__ import annotations

from pathlib import Path
from datetime import datetime
from typing import Optional
import zipfile
import tempfile
import os

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QCheckBox,
    QGroupBox,
    QFileDialog,
    QMessageBox,
    QPlainTextEdit,
)

from ...config import LauncherConfig
from ...process import ClientProcess
from ...styles import (
    COLORS,
    PAGE_TITLE_STYLE,
    PAGE_SUBTITLE_STYLE,
    SECONDARY_BUTTON_STYLE,
    DANGER_BUTTON_STYLE,
    SUCCESS_BUTTON_STYLE,
    LOG_VIEW_STYLE,
    GROUP_BOX_STYLE,
    CHECK_BOX_STYLE,
)


class DebugPage(QWidget):
    """Debug and diagnostics page"""
    
    MAX_LOG_LINES = 1000
    
    def __init__(
        self,
        config: LauncherConfig,
        client_process: ClientProcess,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.config = config
        self.client_process = client_process
        
        self._log_lines = []
        
        self._build_ui()
        self._connect_signals()
    
    def _build_ui(self):
        """Build the debug page UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)
        
        # Header
        header = QHBoxLayout()
        
        title_layout = QVBoxLayout()
        title_layout.setSpacing(4)
        
        title = QLabel("Отладка")
        title.setStyleSheet(PAGE_TITLE_STYLE)
        title_layout.addWidget(title)
        
        subtitle = QLabel("Логи, диагностика и устранение неполадок")
        subtitle.setStyleSheet(PAGE_SUBTITLE_STYLE)
        title_layout.addWidget(subtitle)
        
        header.addLayout(title_layout, 1)
        
        layout.addLayout(header)
        
        # Quick actions
        self._build_actions_section()
        layout.addWidget(self.actions_widget)
        
        # Log viewer
        self._build_log_viewer()
        layout.addWidget(self.log_group, 1)
        
        # Bug report section
        self._build_bug_report_section()
        layout.addWidget(self.bug_report_widget)
    
    def _build_actions_section(self):
        """Build quick actions section"""
        self.actions_widget = QWidget()
        layout = QHBoxLayout(self.actions_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # Reinstall dependencies
        self.btn_reinstall = QPushButton("🔄  Переустановить зависимости")
        self.btn_reinstall.setStyleSheet(SECONDARY_BUTTON_STYLE)
        self.btn_reinstall.clicked.connect(self._on_reinstall)
        layout.addWidget(self.btn_reinstall)
        
        # Clear venv
        self.btn_clear_venv = QPushButton("🗑️  Очистить venv")
        self.btn_clear_venv.setStyleSheet(DANGER_BUTTON_STYLE)
        self.btn_clear_venv.clicked.connect(self._on_clear_venv)
        layout.addWidget(self.btn_clear_venv)
        
        # Check Ollama
        self.btn_check_ollama = QPushButton("🔍  Проверить Ollama")
        self.btn_check_ollama.setStyleSheet(SECONDARY_BUTTON_STYLE)
        self.btn_check_ollama.clicked.connect(self._on_check_ollama)
        layout.addWidget(self.btn_check_ollama)
        
        layout.addStretch()
    
    def _build_log_viewer(self):
        """Build log viewer section"""
        self.log_group = QGroupBox("Консоль логов")
        self.log_group.setStyleSheet(GROUP_BOX_STYLE)
        
        layout = QVBoxLayout(self.log_group)
        layout.setContentsMargins(12, 16, 12, 12)
        layout.setSpacing(8)
        
        # Log controls
        controls = QHBoxLayout()
        
        self.chk_autoscroll = QCheckBox("Автопрокрутка")
        self.chk_autoscroll.setStyleSheet(CHECK_BOX_STYLE)
        self.chk_autoscroll.setChecked(self.config.autoscroll_logs)
        controls.addWidget(self.chk_autoscroll)
        
        controls.addStretch()
        
        self.btn_clear_log = QPushButton("Очистить")
        self.btn_clear_log.setStyleSheet(SECONDARY_BUTTON_STYLE)
        self.btn_clear_log.clicked.connect(self._clear_log)
        controls.addWidget(self.btn_clear_log)
        
        self.btn_save_log = QPushButton("Сохранить")
        self.btn_save_log.setStyleSheet(SECONDARY_BUTTON_STYLE)
        self.btn_save_log.clicked.connect(self._save_log)
        controls.addWidget(self.btn_save_log)
        
        layout.addLayout(controls)
        
        # Log text area
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setStyleSheet(LOG_VIEW_STYLE.replace("QTextEdit", "QPlainTextEdit"))
        self.log_view.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        layout.addWidget(self.log_view, 1)
    
    def _build_bug_report_section(self):
        """Build bug report section"""
        self.bug_report_widget = QGroupBox("Сообщить о проблеме")
        self.bug_report_widget.setStyleSheet(GROUP_BOX_STYLE)
        
        layout = QVBoxLayout(self.bug_report_widget)
        layout.setContentsMargins(12, 16, 12, 12)
        layout.setSpacing(8)
        
        info = QLabel(
            "Создайте диагностический пакет для отправки разработчикам. "
            "Пакет содержит логи и конфигурацию (без личных данных)."
        )
        info.setWordWrap(True)
        info.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
        layout.addWidget(info)
        
        buttons = QHBoxLayout()
        
        self.btn_create_report = QPushButton("📦  Создать диагностический пакет")
        self.btn_create_report.setStyleSheet(SUCCESS_BUTTON_STYLE)
        self.btn_create_report.clicked.connect(self._create_diagnostic_package)
        buttons.addWidget(self.btn_create_report)
        
        self.btn_open_github = QPushButton("🐛  GitHub Issues")
        self.btn_open_github.setStyleSheet(SECONDARY_BUTTON_STYLE)
        self.btn_open_github.clicked.connect(self._open_github_issues)
        buttons.addWidget(self.btn_open_github)
        
        buttons.addStretch()
        layout.addLayout(buttons)
    
    def _connect_signals(self):
        """Connect signals"""
        self.chk_autoscroll.toggled.connect(self._on_autoscroll_changed)
    
    def append_log(self, line: str):
        """Append a line to the log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted = f"[{timestamp}] {line}"
        
        self._log_lines.append(formatted)
        
        # Trim if too many lines
        if len(self._log_lines) > self.MAX_LOG_LINES:
            self._log_lines = self._log_lines[-self.MAX_LOG_LINES:]
        
        self.log_view.appendPlainText(formatted)
        
        # Autoscroll
        if self.chk_autoscroll.isChecked():
            scrollbar = self.log_view.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
    
    def _clear_log(self):
        """Clear the log view"""
        self._log_lines.clear()
        self.log_view.clear()
    
    def _save_log(self):
        """Save log to file"""
        if not self._log_lines:
            QMessageBox.information(self, "Пусто", "Нет логов для сохранения")
            return
        
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить логи",
            f"arvis_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            "Text Files (*.txt)"
        )
        
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write("\n".join(self._log_lines))
                QMessageBox.information(self, "Сохранено", f"Логи сохранены: {path}")
            except Exception as e:
                QMessageBox.warning(self, "Ошибка", f"Не удалось сохранить: {e}")
    
    def _on_autoscroll_changed(self, checked: bool):
        """Handle autoscroll toggle"""
        self.config.autoscroll_logs = checked
        try:
            self.config.save()
        except:
            pass
    
    def _on_reinstall(self):
        """Reinstall dependencies"""
        reply = QMessageBox.question(
            self,
            "Переустановка",
            "Переустановить все зависимости?\n\n"
            "Это может занять несколько минут.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # TODO: Trigger reinstall via installer
            self.append_log("[DEBUG] Переустановка зависимостей запрошена")
            QMessageBox.information(
                self,
                "В разработке",
                "Функция переустановки в разработке.\n\n"
                "Пока вы можете удалить папку .venv и нажать 'Установить' на главной странице."
            )
    
    def _on_clear_venv(self):
        """Clear virtual environment"""
        client_root = self.config.get_client_root()
        if not client_root:
            QMessageBox.warning(self, "Ошибка", "Путь к клиенту не настроен")
            return
        
        venv_path = client_root / ".venv"
        if not venv_path.exists():
            venv_path = client_root / "venv"
        
        if not venv_path.exists():
            QMessageBox.information(self, "Нет venv", "Виртуальное окружение не найдено")
            return
        
        reply = QMessageBox.warning(
            self,
            "Удаление venv",
            f"Удалить виртуальное окружение?\n\n{venv_path}\n\n"
            "После этого потребуется переустановка зависимостей.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                import shutil
                shutil.rmtree(venv_path)
                self.append_log(f"[DEBUG] Удалено: {venv_path}")
                QMessageBox.information(self, "Готово", "Виртуальное окружение удалено")
            except Exception as e:
                QMessageBox.warning(self, "Ошибка", f"Не удалось удалить: {e}")
    
    def _on_check_ollama(self):
        """Check Ollama status"""
        import shutil
        import subprocess
        
        self.append_log("[DEBUG] Проверка Ollama...")
        
        ollama_exe = shutil.which("ollama")
        if not ollama_exe:
            self.append_log("[DEBUG] ✗ Ollama не найден в PATH")
            QMessageBox.warning(self, "Ollama", "Ollama не установлен или не в PATH")
            return
        
        self.append_log(f"[DEBUG] ✓ Ollama найден: {ollama_exe}")
        
        try:
            result = subprocess.run(
                [ollama_exe, "list"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                self.append_log("[DEBUG] ✓ Ollama запущен")
                models = result.stdout.strip()
                self.append_log(f"[DEBUG] Модели:\n{models}")
                
                QMessageBox.information(
                    self,
                    "Ollama OK",
                    f"Ollama работает\n\nМодели:\n{models}"
                )
            else:
                self.append_log(f"[DEBUG] ✗ Ollama не запущен: {result.stderr}")
                QMessageBox.warning(
                    self,
                    "Ollama",
                    "Ollama установлен, но не запущен.\n\n"
                    "Перейдите в раздел 'Модели' и нажмите 'Запустить'."
                )
        except subprocess.TimeoutExpired:
            self.append_log("[DEBUG] ✗ Таймаут при проверке Ollama")
            QMessageBox.warning(self, "Ollama", "Таймаут при проверке Ollama")
        except Exception as e:
            self.append_log(f"[DEBUG] ✗ Ошибка: {e}")
            QMessageBox.warning(self, "Ошибка", f"Ошибка проверки: {e}")
    
    def _create_diagnostic_package(self):
        """Create diagnostic package"""
        # Choose save location
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить диагностический пакет",
            f"arvis_diagnostic_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
            "Zip Files (*.zip)"
        )
        
        if not path:
            return
        
        try:
            with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as zf:
                # Add current logs
                if self._log_lines:
                    zf.writestr("launcher_log.txt", "\n".join(self._log_lines))
                
                # Add launcher config (sanitized)
                config_data = {
                    "paths": {
                        "client_root": str(self.config.paths.client_root) if self.config.paths.client_root else None,
                    },
                    "update": {
                        "branch": self.config.update.branch,
                    },
                    "ollama": {
                        "default_model": self.config.ollama.default_model,
                    },
                }
                import json
                zf.writestr("launcher_config.json", json.dumps(config_data, indent=2))
                
                # Add client logs if available
                client_root = self.config.get_client_root()
                if client_root:
                    logs_dir = client_root / "logs"
                    if logs_dir.exists():
                        for log_file in logs_dir.glob("*.log"):
                            try:
                                zf.write(log_file, f"client_logs/{log_file.name}")
                            except:
                                pass
                
                # Add system info
                import platform
                import sys
                system_info = f"""
System Information
==================
OS: {platform.system()} {platform.release()}
Python: {sys.version}
Date: {datetime.now().isoformat()}
"""
                zf.writestr("system_info.txt", system_info)
            
            QMessageBox.information(
                self,
                "Готово",
                f"Диагностический пакет создан:\n{path}\n\n"
                "Приложите этот файл при создании issue на GitHub."
            )
            
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось создать пакет: {e}")
    
    def _open_github_issues(self):
        """Open GitHub issues page"""
        import webbrowser
        repo = self.config.update.github_repo
        url = f"https://github.com/{repo}/issues/new"
        webbrowser.open(url)
