from __future__ import annotations

import json
import subprocess
from pathlib import Path

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from launcher.config import LauncherConfig
from launcher.process import ManagedProcess


class LauncherMainWindow(QMainWindow):
    def __init__(self, cfg: LauncherConfig):
        super().__init__()
        self.cfg = cfg
        self.proc = ManagedProcess(self)

        self.setWindowTitle("Arvis Launcher")
        self.resize(cfg.window.width, cfg.window.height)

        self._build_ui()
        self._wire()

    def closeEvent(self, event):
        # save window size (portable)
        try:
            sz = self.size()
            self.cfg.window.width = int(sz.width())
            self.cfg.window.height = int(sz.height())
            self.cfg.save()
        except Exception:
            pass
        return super().closeEvent(event)

    def _build_ui(self):
        root = QWidget(self)
        self.setCentralWidget(root)

        splitter = QSplitter(Qt.Orientation.Horizontal, root)

        # Sidebar
        self.nav = QListWidget(splitter)
        self.nav.setFixedWidth(220)
        self.nav.setFrameShape(QFrame.Shape.NoFrame)

        for name in ("Home", "Models", "Settings", "Debug"):
            item = QListWidgetItem(name)
            self.nav.addItem(item)
        self.nav.setCurrentRow(0)

        # Pages
        self.pages = QStackedWidget(splitter)
        self.pages.addWidget(self._page_home())
        self.pages.addWidget(self._page_models())
        self.pages.addWidget(self._page_settings())
        self.pages.addWidget(self._page_debug())

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(splitter)

    def _page_home(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        title = QLabel("Arvis Launcher")
        title.setFont(QFont("Segoe UI", 16))

        self.status = QLabel("Status: stopped")

        btn_row = QHBoxLayout()
        self.btn_start = QPushButton("Start Arvis")
        self.btn_stop = QPushButton("Stop")
        self.btn_restart = QPushButton("Restart")
        self.btn_stop.setEnabled(False)
        self.btn_restart.setEnabled(False)

        btn_row.addWidget(self.btn_start)
        btn_row.addWidget(self.btn_stop)
        btn_row.addWidget(self.btn_restart)
        btn_row.addStretch(1)

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)

        self.chk_autoscroll = QCheckBox("Autoscroll logs")
        self.chk_autoscroll.setChecked(bool(self.cfg.autoscroll_logs))

        layout.addWidget(title)
        layout.addWidget(self.status)
        layout.addLayout(btn_row)
        layout.addWidget(self.chk_autoscroll)
        layout.addWidget(self.log_view, 1)
        return w

    def _page_models(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        title = QLabel("Модели")
        title.setFont(QFont("Segoe UI", 14))
        layout.addWidget(title)

        # === LLM Section ===
        llm_group = QGroupBox("LLM (Ollama)")
        llm_layout = QVBoxLayout(llm_group)

        # Model selector row
        model_row = QHBoxLayout()
        model_row.addWidget(QLabel("Активная модель:"))
        self.llm_combo = QComboBox()
        self.llm_combo.setMinimumWidth(250)
        self.llm_combo.setPlaceholderText("Загрузка...")
        model_row.addWidget(self.llm_combo)
        
        self.btn_refresh_models = QPushButton("🔄 Обновить")
        self.btn_refresh_models.setFixedWidth(100)
        self.btn_refresh_models.clicked.connect(self._refresh_ollama_models)
        model_row.addWidget(self.btn_refresh_models)
        model_row.addStretch(1)
        llm_layout.addLayout(model_row)

        # Status and actions
        self.llm_status = QLabel("")
        llm_layout.addWidget(self.llm_status)

        # Save button
        btn_row = QHBoxLayout()
        self.btn_save_model = QPushButton("💾 Сохранить выбор")
        self.btn_save_model.clicked.connect(self._save_selected_model)
        btn_row.addWidget(self.btn_save_model)
        btn_row.addStretch(1)
        llm_layout.addLayout(btn_row)

        layout.addWidget(llm_group)

        # === Info ===
        info = QLabel(
            "💡 Рекомендуемые модели:\n"
            "• gemma2:2b — быстрая, для слабых ПК\n"
            "• mistral:7b — баланс скорости и качества\n"
            "• llama3.1:8b — качественная, требует 8GB+ VRAM\n"
            "• wizard-vicuna-uncensored — без цензуры\n"
            "• dolphin-mixtral — умная, без цензуры"
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #888; margin-top: 10px;")
        layout.addWidget(info)

        layout.addStretch(1)

        # Load models on page creation
        self._refresh_ollama_models()

        return w

    def _refresh_ollama_models(self):
        """Fetch available models from Ollama"""
        self.llm_combo.clear()
        self.llm_combo.setPlaceholderText("Загрузка...")
        self.llm_status.setText("Получение списка моделей...")
        
        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            if result.returncode != 0:
                self.llm_status.setText("❌ Ollama не запущена или не установлена")
                return
            
            # Parse output: NAME ID SIZE MODIFIED
            lines = result.stdout.strip().split('\n')
            models = []
            for line in lines[1:]:  # Skip header
                if line.strip():
                    parts = line.split()
                    if parts:
                        models.append(parts[0])
            
            if models:
                self.llm_combo.addItems(models)
                self.llm_status.setText(f"✅ Найдено моделей: {len(models)}")
                
                # Try to select current model from client config
                current = self._get_current_model()
                if current:
                    idx = self.llm_combo.findText(current)
                    if idx >= 0:
                        self.llm_combo.setCurrentIndex(idx)
            else:
                self.llm_status.setText("⚠️ Нет установленных моделей. Используйте: ollama pull <model>")
                
        except subprocess.TimeoutExpired:
            self.llm_status.setText("❌ Таймаут при обращении к Ollama")
        except FileNotFoundError:
            self.llm_status.setText("❌ Ollama не найдена. Установите ollama.ai")
        except Exception as e:
            self.llm_status.setText(f"❌ Ошибка: {e}")

    def _get_current_model(self) -> str:
        """Get current model from client config"""
        try:
            client_root = self.cfg.get_client_root()
            if client_root:
                config_path = client_root / "config" / "config.json"
                if config_path.exists():
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                    return config.get("llm", {}).get("default_model", "")
        except Exception:
            pass
        return self.cfg.ollama.default_model

    def _save_selected_model(self):
        """Save selected model to client config"""
        model = self.llm_combo.currentText()
        if not model:
            QMessageBox.warning(self, "Ошибка", "Выберите модель из списка")
            return
        
        client_root = self.cfg.get_client_root()
        if not client_root:
            QMessageBox.warning(self, "Ошибка", "Путь к клиенту не настроен")
            return
        
        try:
            config_path = client_root / "config" / "config.json"
            
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            else:
                config = {}
            
            # Update LLM section
            if "llm" not in config:
                config["llm"] = {}
            config["llm"]["default_model"] = model
            
            # Also update models list if model not in it
            if "models" not in config["llm"]:
                config["llm"]["models"] = []
            if model not in config["llm"]["models"]:
                config["llm"]["models"].append(model)
            
            # Save
            config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            
            # Also save to launcher config
            self.cfg.ollama.default_model = model
            self.cfg.save()
            
            self.llm_status.setText(f"✅ Модель '{model}' сохранена!")
            QMessageBox.information(self, "Успех", f"Модель '{model}' будет использоваться при следующем запуске Arvis")
            
        except Exception as e:
            self.llm_status.setText(f"❌ Ошибка сохранения: {e}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить настройки:\n{e}")

    def _page_settings(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.addWidget(QLabel("Settings — скоро"))
        hint = QLabel(
            "Здесь будут глобальные настройки: аккаунт, выбор моделей, пути к логам/БД, режим окна. "
            "Настройки хранятся portable в launcher_config.json и частично пишутся в config/config.json клиента."
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)
        layout.addStretch(1)
        return w

    def _page_debug(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.addWidget(QLabel("Debug — скоро"))
        hint = QLabel("Позже: диагностический пакет (zip), проверка Ollama, ремонт зависимостей.")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        layout.addStretch(1)
        return w

    def _wire(self):
        self.nav.currentRowChanged.connect(self.pages.setCurrentIndex)

        self.btn_start.clicked.connect(self._start_client)
        self.btn_stop.clicked.connect(self._stop_client)
        self.btn_restart.clicked.connect(self._restart_client)

        self.chk_autoscroll.toggled.connect(self._save_autoscroll)

        self.proc.output_line.connect(self._append_log)
        self.proc.state_changed.connect(self._on_state)

    def _save_autoscroll(self, val: bool):
        self.cfg.autoscroll_logs = bool(val)
        try:
            self.cfg.save()
        except Exception:
            pass

    def _append_log(self, line: str):
        self.log_view.append(line)
        if self.chk_autoscroll.isChecked():
            self.log_view.moveCursor(self.log_view.textCursor().MoveOperation.End)

    def _on_state(self, state: str):
        self.status.setText(f"Status: {state}")
        running = state == "running" or state == "starting"
        self.btn_start.setEnabled(not running)
        self.btn_stop.setEnabled(running)
        self.btn_restart.setEnabled(running)

    def _start_client(self):
        res = self.proc.start_client(self.cfg.client_root)
        if not res.ok:
            self._append_log(f"[LAUNCHER] ERROR: {res.error}")

    def _stop_client(self):
        self.proc.stop()

    def _restart_client(self):
        res = self.proc.restart_client(self.cfg.client_root)
        if not res.ok:
            self._append_log(f"[LAUNCHER] ERROR: {res.error}")
