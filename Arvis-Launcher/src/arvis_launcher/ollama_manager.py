"""
Ollama management for Arvis Launcher
Handles installation, model management and process control
"""

from __future__ import annotations

import os
import subprocess
import shutil
import json
import urllib.request
import urllib.error
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Dict, Any
from enum import Enum

from PyQt6.QtCore import QObject, QThread, pyqtSignal, QTimer


class OllamaState(Enum):
    """Ollama service state"""
    NOT_INSTALLED = "not_installed"
    STOPPED = "stopped"
    RUNNING = "running"
    UNKNOWN = "unknown"


@dataclass
class OllamaModel:
    """Represents an Ollama model"""
    name: str
    size: str = ""
    modified: str = ""
    digest: str = ""
    is_installed: bool = False
    
    @property
    def display_name(self) -> str:
        """Get human-readable name"""
        name = self.name.split(":")[0]
        return name.replace("-", " ").title()
    
    @property
    def tag(self) -> str:
        """Get model tag (version)"""
        if ":" in self.name:
            return self.name.split(":")[1]
        return "latest"


# Recommended models catalog
RECOMMENDED_MODELS = [
    OllamaModel("gemma2:2b", "1.6 GB", "", "", False),
    OllamaModel("llama3.2:3b", "2.0 GB", "", "", False),
    OllamaModel("phi3:mini", "2.3 GB", "", "", False),
    OllamaModel("mistral:7b", "4.1 GB", "", "", False),
    OllamaModel("llama3.1:8b", "4.7 GB", "", "", False),
    OllamaModel("gemma2:9b", "5.5 GB", "", "", False),
]


class OllamaInstallWorker(QThread):
    """Background worker for Ollama installation"""
    
    progress = pyqtSignal(int, str)
    log_line = pyqtSignal(str)
    finished_result = pyqtSignal(bool, str)
    
    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._cancelled = False
    
    def cancel(self):
        self._cancelled = True
    
    def run(self):
        try:
            self._install_ollama()
        except Exception as e:
            self.finished_result.emit(False, f"Ошибка: {e}")
    
    def _install_ollama(self):
        """Download and install Ollama on Windows"""
        import tempfile
        import sys
        
        if sys.platform != "win32":
            self.finished_result.emit(False, "Автоустановка поддерживается только на Windows")
            return
        
        self.progress.emit(0, "Скачивание Ollama...")
        self.log_line.emit("Скачивание Ollama installer...")
        
        # Download URL for Windows
        download_url = "https://ollama.com/download/OllamaSetup.exe"
        
        try:
            # Download to temp file
            with tempfile.NamedTemporaryFile(suffix=".exe", delete=False) as tmp:
                tmp_path = tmp.name
            
            # Download with progress
            def reporthook(block_num, block_size, total_size):
                if self._cancelled:
                    raise InterruptedError("Cancelled")
                if total_size > 0:
                    downloaded = block_num * block_size
                    percent = min(int(downloaded * 50 / total_size), 50)
                    self.progress.emit(percent, f"Скачивание: {downloaded // 1024 // 1024} MB")
            
            urllib.request.urlretrieve(download_url, tmp_path, reporthook)
            
            self.progress.emit(50, "Запуск установщика...")
            self.log_line.emit(f"Запуск: {tmp_path}")
            
            # Run installer (silent mode)
            result = subprocess.run(
                [tmp_path, "/S"],  # /S for silent install
                capture_output=True,
                timeout=300  # 5 minutes timeout
            )
            
            # Clean up
            try:
                os.unlink(tmp_path)
            except:
                pass
            
            if result.returncode != 0:
                self.finished_result.emit(False, "Ошибка установки Ollama")
                return
            
            self.progress.emit(100, "Готово!")
            self.log_line.emit("✓ Ollama установлен")
            self.finished_result.emit(True, "Ollama успешно установлен!")
            
        except InterruptedError:
            self.finished_result.emit(False, "Установка отменена")
        except urllib.error.URLError as e:
            self.finished_result.emit(False, f"Ошибка скачивания: {e}")
        except Exception as e:
            self.finished_result.emit(False, f"Ошибка: {e}")


class OllamaPullWorker(QThread):
    """Background worker for pulling models"""
    
    progress = pyqtSignal(int, str)
    log_line = pyqtSignal(str)
    finished_result = pyqtSignal(bool, str)
    
    def __init__(self, model_name: str, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.model_name = model_name
        self._cancelled = False
    
    def cancel(self):
        self._cancelled = True
    
    def run(self):
        try:
            self._pull_model()
        except Exception as e:
            self.finished_result.emit(False, f"Ошибка: {e}")
    
    def _pull_model(self):
        """Pull a model from Ollama registry"""
        self.progress.emit(0, f"Скачивание {self.model_name}...")
        self.log_line.emit(f"ollama pull {self.model_name}")
        
        ollama_exe = shutil.which("ollama")
        if not ollama_exe:
            self.finished_result.emit(False, "Ollama не найден")
            return
        
        try:
            process = subprocess.Popen(
                [ollama_exe, "pull", self.model_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
            
            while True:
                if self._cancelled:
                    process.terminate()
                    self.finished_result.emit(False, "Отменено")
                    return
                
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                if line:
                    line = line.strip()
                    if line:
                        self.log_line.emit(line)
                        # Parse progress from output
                        if "%" in line:
                            try:
                                # Format: "pulling ... 45%"
                                percent = int(line.split("%")[0].split()[-1])
                                self.progress.emit(percent, f"Скачивание: {percent}%")
                            except:
                                pass
            
            if process.returncode != 0:
                self.finished_result.emit(False, f"Ошибка скачивания {self.model_name}")
                return
            
            self.progress.emit(100, "Готово!")
            self.log_line.emit(f"✓ Модель {self.model_name} установлена")
            self.finished_result.emit(True, f"Модель {self.model_name} готова!")
            
        except Exception as e:
            self.finished_result.emit(False, f"Ошибка: {e}")


class OllamaManager(QObject):
    """Manages Ollama installation and models"""
    
    # Signals
    state_changed = pyqtSignal(str)          # OllamaState value
    # New signal for status with human message: (OllamaState, str)
    status_changed = pyqtSignal(object, str)
    models_updated = pyqtSignal(list)         # List of OllamaModel
    progress = pyqtSignal(int, str)           # percent, message
    log_line = pyqtSignal(str)
    operation_finished = pyqtSignal(bool, str)  # success, message
    
    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._worker = None
        self._state = OllamaState.UNKNOWN
        self._models: List[OllamaModel] = []
        
        # Auto-refresh timer
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self.refresh_state)

        # Backwards-compatible signal name for models
        self.models_changed = self.models_updated
    
    @property
    def state(self) -> OllamaState:
        return self._state
    
    @property
    def models(self) -> List[OllamaModel]:
        return self._models.copy()
    
    def start_monitoring(self, interval_ms: int = 10000):
        """Start periodic state monitoring"""
        self._refresh_timer.start(interval_ms)
        self.refresh_state()
    
    def stop_monitoring(self):
        """Stop periodic monitoring"""
        self._refresh_timer.stop()
    
    def refresh_state(self):
        """Refresh Ollama state and models"""
        old_state = self._state
        
        # Check if installed
        ollama_exe = shutil.which("ollama")
        if not ollama_exe:
            self._state = OllamaState.NOT_INSTALLED
            if old_state != self._state:
                # Emit both legacy and new signals
                self.state_changed.emit(self._state.value)
                self.status_changed.emit(self._state, "Ollama not installed")
            return
        
        # Check if running by trying to list models
        try:
            result = subprocess.run(
                [ollama_exe, "list"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                self._state = OllamaState.RUNNING
                self._parse_models(result.stdout)
            else:
                # Ollama installed but not running
                self._state = OllamaState.STOPPED
                self._models = []
            
        except subprocess.TimeoutExpired:
            self._state = OllamaState.STOPPED
        except Exception:
            self._state = OllamaState.UNKNOWN
        
        if old_state != self._state:
            # Emit legacy string-based state and richer status with message
            self.state_changed.emit(self._state.value)
            # Map to simple message
            if self._state == OllamaState.RUNNING:
                msg = "Running"
            elif self._state == OllamaState.STOPPED:
                msg = "Stopped"
            elif self._state == OllamaState.NOT_INSTALLED:
                msg = "Not installed"
            else:
                msg = "Unknown"
            self.status_changed.emit(self._state, msg)
        
        self.models_updated.emit(self._models)
    
    def _parse_models(self, output: str):
        """Parse 'ollama list' output"""
        self._models = []
        lines = output.strip().split("\n")
        
        # Skip header line
        for line in lines[1:]:
            if not line.strip():
                continue
            parts = line.split()
            if len(parts) >= 1:
                name = parts[0]
                size = parts[2] if len(parts) > 2 else ""
                modified = " ".join(parts[3:5]) if len(parts) > 4 else ""
                
                model = OllamaModel(
                    name=name,
                    size=size,
                    modified=modified,
                    is_installed=True
                )
                self._models.append(model)
    
    def is_installed(self) -> bool:
        """Check if Ollama is installed"""
        return self._state != OllamaState.NOT_INSTALLED
    
    def is_running(self) -> bool:
        """Check if Ollama service is running"""
        return self._state == OllamaState.RUNNING
    
    def has_model(self, model_name: str) -> bool:
        """Check if a model is installed"""
        base_name = model_name.split(":")[0]
        for model in self._models:
            if model.name == model_name or model.name.startswith(base_name + ":"):
                return True
        return False

    # Compatibility wrappers expected by UI
    def is_available(self) -> bool:
        """Compatibility: whether Ollama is available for model operations."""
        return self.is_running()

    def get_installed_models(self) -> List[OllamaModel]:
        """Return list of installed models (compatibility wrapper)."""
        return self.models

    def check_updates(self) -> List[str]:
        """Check for model updates. Currently returns empty list as placeholder."""
        # Placeholder: real implementation could query a registry or compare digests
        return []
    
    def install_ollama(self):
        """Start Ollama installation"""
        if self._worker and self._worker.isRunning():
            return
        
        self._worker = OllamaInstallWorker()
        self._worker.progress.connect(self.progress.emit)
        self._worker.log_line.connect(self.log_line.emit)
        self._worker.finished_result.connect(self._on_install_finished)
        self._worker.start()
    
    def _on_install_finished(self, success: bool, message: str):
        """Handle installation completion"""
        if success:
            QTimer.singleShot(2000, self.refresh_state)
        self.operation_finished.emit(success, message)
        self._worker = None
    
    def start_service(self) -> bool:
        """Start Ollama service"""
        ollama_exe = shutil.which("ollama")
        if not ollama_exe:
            return False
        
        try:
            # Start ollama serve in background
            if os.name == "nt":
                # Windows: use start command
                subprocess.Popen(
                    ["cmd", "/c", "start", "/b", ollama_exe, "serve"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            else:
                subprocess.Popen(
                    [ollama_exe, "serve"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True
                )
            
            # Wait a bit and refresh
            QTimer.singleShot(2000, self.refresh_state)
            return True
            
        except Exception:
            return False
    
    def stop_service(self) -> bool:
        """Stop Ollama service"""
        if os.name == "nt":
            try:
                subprocess.run(
                    ["taskkill", "/f", "/im", "ollama.exe"],
                    capture_output=True
                )
                QTimer.singleShot(1000, self.refresh_state)
                return True
            except:
                return False
        else:
            try:
                subprocess.run(["pkill", "ollama"], capture_output=True)
                QTimer.singleShot(1000, self.refresh_state)
                return True
            except:
                return False
    
    def pull_model(self, model_name: str):
        """Pull a model from registry"""
        if self._worker and self._worker.isRunning():
            return
        
        if self._state != OllamaState.RUNNING:
            self.operation_finished.emit(False, "Ollama не запущен")
            return
        
        self._worker = OllamaPullWorker(model_name)
        self._worker.progress.connect(self.progress.emit)
        self._worker.log_line.connect(self.log_line.emit)
        self._worker.finished_result.connect(self._on_pull_finished)
        self._worker.start()
    
    def _on_pull_finished(self, success: bool, message: str):
        """Handle model pull completion"""
        if success:
            self.refresh_state()
        self.operation_finished.emit(success, message)
        self._worker = None
    
    def remove_model(self, model_name: str) -> bool:
        """Remove a model"""
        ollama_exe = shutil.which("ollama")
        if not ollama_exe:
            return False
        
        try:
            result = subprocess.run(
                [ollama_exe, "rm", model_name],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                self.log_line.emit(f"✓ Модель {model_name} удалена")
                self.refresh_state()
                return True
            else:
                self.log_line.emit(f"✗ Ошибка удаления: {result.stderr}")
                return False
                
        except Exception as e:
            self.log_line.emit(f"✗ Ошибка: {e}")
            return False
    
    def cancel_operation(self):
        """Cancel current operation"""
        if self._worker:
            self._worker.cancel()
    
    def get_recommended_models(self) -> List[OllamaModel]:
        """Get list of recommended models with install status"""
        models = []
        for model in RECOMMENDED_MODELS:
            model_copy = OllamaModel(
                name=model.name,
                size=model.size,
                is_installed=self.has_model(model.name)
            )
            models.append(model_copy)
        return models
