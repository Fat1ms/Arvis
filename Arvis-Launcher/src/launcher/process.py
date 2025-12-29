from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QObject, QProcess, pyqtSignal


@dataclass
class ProcessStartResult:
    ok: bool
    error: str | None = None


class ManagedProcess(QObject):
    output_line = pyqtSignal(str)
    state_changed = pyqtSignal(str)  # 'stopped' | 'starting' | 'running'

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._proc = QProcess(self)
        self._proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)

        self._proc.readyReadStandardOutput.connect(self._drain)
        self._proc.readyReadStandardError.connect(self._drain)
        self._proc.stateChanged.connect(self._on_state)

    def is_running(self) -> bool:
        return self._proc.state() != QProcess.ProcessState.NotRunning

    def start_client(self, client_root: Path) -> ProcessStartResult:
        launch_py = client_root / "launch.py"
        if not launch_py.exists():
            return ProcessStartResult(False, f"Не найден файл: {launch_py}")

        # Prefer venv python if present
        python_exe = self._resolve_client_python(client_root)
        if not python_exe:
            return ProcessStartResult(False, "Не найден Python для запуска клиента (ни venv/.venv, ни системный python).")

        workdir = str(client_root)
        env = os.environ.copy()

        self._proc.setWorkingDirectory(workdir)
        self._proc.setProgram(python_exe)
        self._proc.setArguments([str(launch_py)])
        self._proc.setEnvironment([f"{k}={v}" for k, v in env.items()])

        self.output_line.emit(f"[LAUNCHER] Starting: {python_exe} {launch_py}")
        self._proc.start()
        started = self._proc.waitForStarted(3000)
        if not started:
            return ProcessStartResult(False, "Процесс клиента не стартовал (timeout).")
        try:
            self.output_line.emit(f"[LAUNCHER] PID: {int(self._proc.processId())}")
        except Exception:
            pass
        return ProcessStartResult(True)

    def stop(self) -> None:
        if not self.is_running():
            return
        self._proc.terminate()
        if not self._proc.waitForFinished(1500):
            self._proc.kill()

    def restart_client(self, client_root: Path) -> ProcessStartResult:
        self.stop()
        return self.start_client(client_root)

    def _resolve_client_python(self, client_root: Path) -> Optional[str]:
        # client has helper in launch.py to restart within venv, but for better UX
        # we prefer to start inside venv if it exists.
        for venv_name in (".venv", "venv"):
            venv_dir = client_root / venv_name
            if venv_dir.exists():
                if os.name == "nt":
                    p = venv_dir / "Scripts" / "python.exe"
                else:
                    p = venv_dir / "bin" / "python"
                if p.exists():
                    return str(p)

        # fallback to the same interpreter that runs the launcher
        import sys

        return sys.executable

    def _drain(self) -> None:
        data = bytes(self._proc.readAllStandardOutput()).decode(errors="replace")
        if not data:
            data = bytes(self._proc.readAllStandardError()).decode(errors="replace")
        if not data:
            return
        for line in data.splitlines():
            self.output_line.emit(line)

    def _on_state(self, state: QProcess.ProcessState) -> None:
        if state == QProcess.ProcessState.NotRunning:
            self.state_changed.emit("stopped")
        elif state == QProcess.ProcessState.Starting:
            self.state_changed.emit("starting")
        else:
            self.state_changed.emit("running")
