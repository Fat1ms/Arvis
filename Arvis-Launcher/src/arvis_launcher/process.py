"""
Client process management for Arvis Launcher
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, TYPE_CHECKING

from PyQt6.QtCore import QObject, QProcess, QProcessEnvironment, pyqtSignal

if TYPE_CHECKING:
    from .session import SessionManager


@dataclass
class ProcessResult:
    """Result of a process operation"""
    ok: bool
    error: Optional[str] = None
    message: Optional[str] = None


class ClientProcess(QObject):
    """Manages the Arvis Client process"""
    
    # Signals
    output_line = pyqtSignal(str)          # New log line
    error_line = pyqtSignal(str)           # Error line
    state_changed = pyqtSignal(str)        # 'stopped' | 'starting' | 'running'
    process_finished = pyqtSignal(int, str) # exit_code, exit_status
    
    def __init__(self, session_manager: Optional["SessionManager"] = None, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._proc: Optional[QProcess] = None
        self._client_root: Optional[Path] = None
        self._session_manager = session_manager
        self._init_process()
    
    def _init_process(self) -> None:
        """Initialize QProcess instance"""
        self._proc = QProcess(self)
        self._proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        
        self._proc.readyReadStandardOutput.connect(self._on_stdout)
        self._proc.readyReadStandardError.connect(self._on_stderr)
        self._proc.stateChanged.connect(self._on_state_changed)
        self._proc.finished.connect(self._on_finished)
        self._proc.errorOccurred.connect(self._on_error)
    
    def is_running(self) -> bool:
        """Check if client is currently running"""
        if not self._proc:
            return False
        return self._proc.state() != QProcess.ProcessState.NotRunning
    
    def get_state(self) -> str:
        """Get current state as string"""
        if not self._proc:
            return "stopped"
        state = self._proc.state()
        if state == QProcess.ProcessState.NotRunning:
            return "stopped"
        elif state == QProcess.ProcessState.Starting:
            return "starting"
        else:
            return "running"
    
    def start(self, client_root: Path) -> ProcessResult:
        """Start the Arvis Client"""
        if self.is_running():
            return ProcessResult(False, "Клиент уже запущен")
        
        client_root = Path(client_root)
        self._client_root = client_root
        
        # Validate client root
        if not client_root.exists():
            return ProcessResult(False, f"Папка клиента не найдена: {client_root}")
        
        # Find launch script
        launch_script = self._find_launch_script(client_root)
        if not launch_script:
            return ProcessResult(False, f"Не найден файл запуска (launch.py/main.py) в: {client_root}")
        
        # Find Python executable
        python_exe = self._find_python(client_root)
        if not python_exe:
            return ProcessResult(
                False, 
                "Не найден Python. Необходимо установить зависимости (кнопка 'Установить')."
            )
        
        # Configure process
        self._proc.setWorkingDirectory(str(client_root))
        self._proc.setProgram(python_exe)
        self._proc.setArguments([str(launch_script)])
        
        # Set environment
        env_dict = self._build_environment(client_root)
        process_env = QProcessEnvironment.systemEnvironment()
        for key, value in env_dict.items():
            process_env.insert(key, value)
        self._proc.setProcessEnvironment(process_env)
        
        # Start
        self.output_line.emit(f"[LAUNCHER] Запуск: {python_exe} {launch_script}")
        self._proc.start()
        
        if not self._proc.waitForStarted(5000):
            error = self._proc.errorString()
            return ProcessResult(False, f"Не удалось запустить клиент: {error}")
        
        pid = self._proc.processId()
        self.output_line.emit(f"[LAUNCHER] Клиент запущен (PID: {pid})")
        
        return ProcessResult(True, message="Клиент запущен")
    
    def stop(self) -> ProcessResult:
        """Stop the client gracefully"""
        if not self.is_running():
            return ProcessResult(True, message="Клиент не запущен")
        
        self.output_line.emit("[LAUNCHER] Остановка клиента...")
        
        # Try graceful termination first
        self._proc.terminate()
        if self._proc.waitForFinished(3000):
            return ProcessResult(True, message="Клиент остановлен")
        
        # Force kill if needed
        self.output_line.emit("[LAUNCHER] Принудительная остановка...")
        self._proc.kill()
        self._proc.waitForFinished(2000)
        
        return ProcessResult(True, message="Клиент остановлен принудительно")
    
    def restart(self, client_root: Path) -> ProcessResult:
        """Restart the client"""
        self.stop()
        return self.start(client_root)
    
    def _find_launch_script(self, client_root: Path) -> Optional[Path]:
        """Find the client launch script"""
        # Priority: launch.py > main.py
        for script_name in ("launch.py", "main.py"):
            script = client_root / script_name
            if script.exists():
                return script
        return None
    
    def _find_python(self, client_root: Path) -> Optional[str]:
        """Find Python executable to use"""
        # 1. Check for venv in client folder
        for venv_name in (".venv", "venv"):
            venv_dir = client_root / venv_name
            if not venv_dir.exists():
                continue
            
            if sys.platform == "win32":
                python_exe = venv_dir / "Scripts" / "python.exe"
            else:
                python_exe = venv_dir / "bin" / "python"
            
            if python_exe.exists():
                return str(python_exe)
        
        # 2. Check for embedded Python (portable distribution)
        embedded_dir = client_root / "python"
        if embedded_dir.exists():
            if sys.platform == "win32":
                python_exe = embedded_dir / "python.exe"
                if python_exe.exists():
                    return str(python_exe)
        
        # 3. Fallback to system Python (not ideal, but better than nothing)
        # Only if we're sure it exists and works
        try:
            import shutil
            system_python = shutil.which("python") or shutil.which("python3")
            if system_python:
                return system_python
        except Exception:
            pass
        
        return None
    
    def _build_environment(self, client_root: Path) -> dict:
        """Build environment variables for the client process"""
        env = os.environ.copy()
        
        # Ensure proper encoding
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        
        # Add client root to PYTHONPATH if needed
        pythonpath = env.get("PYTHONPATH", "")
        if str(client_root) not in pythonpath:
            if pythonpath:
                env["PYTHONPATH"] = f"{client_root}{os.pathsep}{pythonpath}"
            else:
                env["PYTHONPATH"] = str(client_root)
        
        # Pass session to client via environment variable
        if self._session_manager and self._session_manager.is_logged_in:
            session_data = self._session_manager.to_dict()
            env["ARVIS_SESSION"] = json.dumps(session_data, ensure_ascii=False)
        
        return env
    
    def _on_stdout(self) -> None:
        """Handle stdout data"""
        if not self._proc:
            return
        data = bytes(self._proc.readAllStandardOutput())
        self._emit_lines(data)
    
    def _on_stderr(self) -> None:
        """Handle stderr data"""
        if not self._proc:
            return
        data = bytes(self._proc.readAllStandardError())
        self._emit_lines(data, is_error=True)
    
    def _emit_lines(self, data: bytes, is_error: bool = False) -> None:
        """Emit log lines from data"""
        try:
            text = data.decode("utf-8", errors="replace")
        except Exception:
            text = str(data)
        
        for line in text.splitlines():
            if line.strip():
                if is_error:
                    self.error_line.emit(line)
                self.output_line.emit(line)
    
    def _on_state_changed(self, state: QProcess.ProcessState) -> None:
        """Handle process state changes"""
        if state == QProcess.ProcessState.NotRunning:
            self.state_changed.emit("stopped")
        elif state == QProcess.ProcessState.Starting:
            self.state_changed.emit("starting")
        else:
            self.state_changed.emit("running")
    
    def _on_finished(self, exit_code: int, exit_status: QProcess.ExitStatus) -> None:
        """Handle process finish"""
        status_str = "normal" if exit_status == QProcess.ExitStatus.NormalExit else "crashed"
        self.output_line.emit(f"[LAUNCHER] Клиент завершён (код: {exit_code}, статус: {status_str})")
        self.process_finished.emit(exit_code, status_str)
    
    def _on_error(self, error: QProcess.ProcessError) -> None:
        """Handle process errors"""
        error_messages = {
            QProcess.ProcessError.FailedToStart: "Не удалось запустить процесс",
            QProcess.ProcessError.Crashed: "Процесс упал",
            QProcess.ProcessError.Timedout: "Таймаут процесса",
            QProcess.ProcessError.WriteError: "Ошибка записи",
            QProcess.ProcessError.ReadError: "Ошибка чтения",
            QProcess.ProcessError.UnknownError: "Неизвестная ошибка",
        }
        msg = error_messages.get(error, "Ошибка процесса")
        self.error_line.emit(f"[LAUNCHER] ОШИБКА: {msg}")
