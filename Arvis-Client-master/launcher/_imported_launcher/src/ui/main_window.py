from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
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
        layout.addWidget(QLabel("Models (Ollama) — скоро"))
        hint = QLabel("Здесь будет список моделей (ollama list), pull/remove и выбор активных LLM/STT/TTS.")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        layout.addStretch(1)
        return w

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
