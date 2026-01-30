"""
Installation and dependency management for Arvis Launcher
"""

from __future__ import annotations

import os
import subprocess
import sys
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Callable
from enum import Enum

from PyQt6.QtCore import QObject, QThread, pyqtSignal


class InstallStep(Enum):
    """Installation step identifiers"""
    CHECK_PYTHON = "check_python"
    CREATE_VENV = "create_venv"
    INSTALL_MINIMAL = "install_minimal"
    INSTALL_FULL = "install_full"
    VERIFY = "verify"


@dataclass
class InstallResult:
    """Result of installation operation"""
    ok: bool
    error: Optional[str] = None
    message: Optional[str] = None


class InstallWorker(QThread):
    """Background worker for installation tasks"""
    
    progress = pyqtSignal(int, str)          # percent, message
    step_started = pyqtSignal(str)           # step name
    step_completed = pyqtSignal(str, bool)   # step name, success
    log_line = pyqtSignal(str)               # log output
    finished_result = pyqtSignal(bool, str)  # success, message
    
    def __init__(
        self, 
        client_root: Path, 
        install_full: bool = False,
        parent: Optional[QObject] = None
    ):
        super().__init__(parent)
        self.client_root = Path(client_root)
        self.install_full = install_full
        self._cancelled = False
    
    def cancel(self) -> None:
        """Request cancellation"""
        self._cancelled = True
    
    def run(self) -> None:
        """Run installation process"""
        try:
            self.log_line.emit("=== Начало установки ===")
            self.log_line.emit(f"Client root: {self.client_root}")
            self.log_line.emit(f"Full install: {self.install_full}")
            self._do_install()
        except Exception as e:
            import traceback
            self.log_line.emit(f"!!! EXCEPTION: {e}")
            self.log_line.emit(traceback.format_exc())
            self.finished_result.emit(False, f"Ошибка установки: {e}")
    
    def _do_install(self) -> None:
        """Perform the installation"""
        steps = [
            (InstallStep.CHECK_PYTHON, "Проверка Python", self._check_python),
            (InstallStep.CREATE_VENV, "Создание виртуального окружения", self._create_venv),
            (InstallStep.INSTALL_MINIMAL, "Установка базовых зависимостей", self._install_minimal),
        ]
        
        if self.install_full:
            steps.append(
                (InstallStep.INSTALL_FULL, "Установка полных зависимостей", self._install_full)
            )
        
        steps.append(
            (InstallStep.VERIFY, "Проверка установки", self._verify_install)
        )
        
        total_steps = len(steps)
        
        for i, (step_id, step_name, step_func) in enumerate(steps):
            if self._cancelled:
                self.finished_result.emit(False, "Установка отменена")
                return
            
            percent = int((i / total_steps) * 100)
            self.progress.emit(percent, step_name)
            self.step_started.emit(step_name)
            self.log_line.emit(f"\n=== {step_name} ===")
            
            try:
                result = step_func()
                if not result.ok:
                    self.step_completed.emit(step_name, False)
                    self.finished_result.emit(False, result.error or "Ошибка")
                    return
                self.step_completed.emit(step_name, True)
            except Exception as e:
                self.step_completed.emit(step_name, False)
                self.finished_result.emit(False, f"{step_name}: {e}")
                return
        
        self.progress.emit(100, "Готово!")
        self.finished_result.emit(True, "Установка завершена успешно!")
    
    def _check_python(self) -> InstallResult:
        """Check if Python is available"""
        # Check for system Python
        python_exe = self._find_system_python()
        
        if not python_exe:
            return InstallResult(
                False, 
                "Python не найден. Установите Python 3.10+ с python.org"
            )
        
        # Check version
        try:
            result = subprocess.run(
                [python_exe, "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            version_str = result.stdout.strip() or result.stderr.strip()
            self.log_line.emit(f"Найден: {version_str}")
            
            # Parse version
            import re
            match = re.search(r"(\d+)\.(\d+)", version_str)
            if match:
                major, minor = int(match.group(1)), int(match.group(2))
                if major < 3 or (major == 3 and minor < 10):
                    return InstallResult(
                        False,
                        f"Требуется Python 3.10+, найден: {version_str}"
                    )
            
            self.log_line.emit(f"✓ Python OK: {python_exe}")
            return InstallResult(True, message=python_exe)
            
        except Exception as e:
            return InstallResult(False, f"Ошибка проверки Python: {e}")
    
    def _create_venv(self) -> InstallResult:
        """Create virtual environment"""
        venv_dir = self.client_root / ".venv"
        
        # Check if already exists
        if venv_dir.exists():
            python_in_venv = self._get_venv_python(venv_dir)
            if python_in_venv and Path(python_in_venv).exists():
                self.log_line.emit(f"✓ Виртуальное окружение уже существует: {venv_dir}")
                return InstallResult(True)
            else:
                # Broken venv, recreate
                self.log_line.emit("Повреждённое venv, пересоздаю...")
                shutil.rmtree(venv_dir, ignore_errors=True)
        
        python_exe = self._find_system_python()
        if not python_exe:
            return InstallResult(False, "Python не найден")
        
        self.log_line.emit(f"Создание venv в {venv_dir}...")
        
        try:
            result = subprocess.run(
                [python_exe, "-m", "venv", str(venv_dir)],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(self.client_root)
            )
            
            if result.returncode != 0:
                error = result.stderr or result.stdout
                return InstallResult(False, f"Ошибка создания venv: {error}")
            
            self.log_line.emit(f"✓ Виртуальное окружение создано")
            return InstallResult(True)
            
        except subprocess.TimeoutExpired:
            return InstallResult(False, "Таймаут при создании venv")
        except Exception as e:
            return InstallResult(False, f"Ошибка: {e}")
    
    def _install_minimal(self) -> InstallResult:
        """Install minimal dependencies"""
        result = self._pip_install("requirements-minimal.txt")
        if not result.ok:
            # Fallback to direct package installation
            self.log_line.emit("⚠ Файл requirements не читается, устанавливаю напрямую...")
            return self._pip_install_direct()
        return result
    
    def _install_full(self) -> InstallResult:
        """Install full dependencies"""
        result = self._pip_install("requirements.txt")
        if not result.ok:
            # Fallback to direct package installation
            self.log_line.emit("⚠ Файл requirements не читается, устанавливаю напрямую...")
            return self._pip_install_direct(full=True)
        return result
    
    def _pip_install_direct(self, full: bool = False) -> InstallResult:
        """Direct package installation without requirements file"""
        venv_dir = self.client_root / ".venv"
        pip_exe = self._get_venv_pip(venv_dir)
        
        if not pip_exe or not Path(pip_exe).exists():
            return InstallResult(False, "pip не найден в venv")
        
        # Core packages that are always needed
        # Note: removed numpy<2 restriction as Python 3.12+ only has numpy 2.x
        packages = [
            "PyQt6",
            "pyttsx3",
            "soundfile",
            "sounddevice", 
            "numpy",
            "requests",
            "urllib3",
            "certifi",
            "pyotp",
            "qrcode",
            "Pillow",
            "pyjwt",
            "psutil",
            "pywin32",
            "python-dateutil",
            "python-dotenv",
            "cryptography",
            "omegaconf",
            "vosk",
        ]
        
        if full:
            packages.extend([
                "torch",
                "torchaudio",
                "transformers",
            ])
        
        self.log_line.emit(f"Установка {len(packages)} пакетов...")
        
        try:
            # Upgrade pip first
            subprocess.run(
                [pip_exe, "install", "--upgrade", "pip", "wheel", "setuptools"],
                capture_output=True,
                timeout=120
            )
            
            # Install packages with --only-binary for numpy to avoid compilation
            # This prevents errors on systems without C compiler
            install_args = [
                pip_exe, "install",
                "--only-binary", "numpy,scipy,pandas",
                "--prefer-binary",
            ] + packages
            
            process = subprocess.Popen(
                install_args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=str(self.client_root)
            )
            
            while True:
                if self._cancelled:
                    process.terminate()
                    return InstallResult(False, "Отменено")
                
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                if line:
                    line = line.strip()
                    if line and any(x in line.lower() for x in ["installing", "successfully", "error", "collecting", "downloading"]):
                        self.log_line.emit(line)
            
            if process.returncode != 0:
                return InstallResult(False, "Ошибка установки пакетов")
            
            self.log_line.emit(f"✓ Пакеты установлены")
            return InstallResult(True)
            
        except Exception as e:
            return InstallResult(False, f"Ошибка: {e}")
    
    def _pip_install(self, requirements_file: str) -> InstallResult:
        """Run pip install with requirements file"""
        req_path = self.client_root / requirements_file
        
        if not req_path.exists():
            # If minimal doesn't exist, try regular requirements
            if requirements_file == "requirements-minimal.txt":
                req_path = self.client_root / "requirements.txt"
                if not req_path.exists():
                    self.log_line.emit("✗ Файл requirements.txt не найден")
                    return InstallResult(False, "Файл requirements.txt не найден")
            else:
                self.log_line.emit(f"✗ Файл {requirements_file} не найден")
                return InstallResult(False, f"Файл {requirements_file} не найден")
        
        venv_dir = self.client_root / ".venv"
        pip_exe = self._get_venv_pip(venv_dir)
        
        self.log_line.emit(f"pip path: {pip_exe}")
        
        if not pip_exe or not Path(pip_exe).exists():
            self.log_line.emit(f"✗ pip не найден: {pip_exe}")
            return InstallResult(False, "pip не найден в venv")
        
        self.log_line.emit(f"Установка зависимостей из {req_path.name}...")
        self.log_line.emit(f"Файл: {req_path}")
        
        try:
            # Upgrade pip first
            self.log_line.emit("Обновление pip...")
            upgrade_result = subprocess.run(
                [pip_exe, "install", "--upgrade", "pip"],
                capture_output=True,
                text=True,
                timeout=120
            )
            if upgrade_result.returncode != 0:
                self.log_line.emit(f"⚠ pip upgrade warning: {upgrade_result.stderr}")
            
            # Install requirements with explicit encoding handling
            # Use --prefer-binary to avoid compilation issues on systems without C compiler
            self.log_line.emit(f"Запуск: {pip_exe} install -r {req_path}")
            
            # Set environment to use UTF-8
            env = os.environ.copy()
            env['PYTHONUTF8'] = '1'
            env['PYTHONIOENCODING'] = 'utf-8'
            
            process = subprocess.Popen(
                [pip_exe, "install", "-r", str(req_path), 
                 "--prefer-binary",
                 "--only-binary", "numpy,scipy,pandas,soundfile"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=str(self.client_root),
                env=env,
                encoding='utf-8',
                errors='replace'
            )
            
            while True:
                if self._cancelled:
                    process.terminate()
                    return InstallResult(False, "Отменено")
                
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                if line:
                    line = line.strip()
                    if line:
                        # Emit important lines
                        if any(x in line.lower() for x in ["installing", "successfully", "error", "warning", "collecting"]):
                            self.log_line.emit(line)
            
            if process.returncode != 0:
                return InstallResult(False, "Ошибка установки зависимостей")
            
            self.log_line.emit(f"✓ Зависимости установлены")
            return InstallResult(True)
            
        except subprocess.TimeoutExpired:
            return InstallResult(False, "Таймаут установки (слишком долго)")
        except Exception as e:
            return InstallResult(False, f"Ошибка pip: {e}")
    
    def _verify_install(self) -> InstallResult:
        """Verify the installation works"""
        venv_dir = self.client_root / ".venv"
        python_exe = self._get_venv_python(venv_dir)
        
        if not python_exe or not Path(python_exe).exists():
            return InstallResult(False, "Python в venv не найден")
        
        self.log_line.emit("Проверка установки...")
        
        # Try to import key modules
        test_imports = ["PyQt6.QtCore", "PyQt6.QtWidgets"]
        
        for module in test_imports:
            try:
                result = subprocess.run(
                    [python_exe, "-c", f"import {module}; print('OK')"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    cwd=str(self.client_root)
                )
                if result.returncode != 0:
                    self.log_line.emit(f"⚠ {module}: не установлен")
                else:
                    self.log_line.emit(f"✓ {module}: OK")
            except Exception as e:
                self.log_line.emit(f"⚠ {module}: ошибка проверки")
        
        self.log_line.emit("✓ Проверка завершена")
        return InstallResult(True)
    
    def _find_system_python(self) -> Optional[str]:
        """Find system Python executable"""
        # Try common names
        for name in ("python", "python3", "py"):
            exe = shutil.which(name)
            if exe:
                return exe
        
        # Windows-specific paths
        if sys.platform == "win32":
            common_paths = [
                Path(os.environ.get("LOCALAPPDATA", "")) / "Programs/Python",
                Path("C:/Python310"),
                Path("C:/Python311"),
                Path("C:/Python312"),
            ]
            for base in common_paths:
                if base.exists():
                    for subdir in base.iterdir():
                        python_exe = subdir / "python.exe"
                        if python_exe.exists():
                            return str(python_exe)
        
        return None
    
    def _get_venv_python(self, venv_dir: Path) -> Optional[str]:
        """Get Python executable in venv"""
        if sys.platform == "win32":
            return str(venv_dir / "Scripts" / "python.exe")
        return str(venv_dir / "bin" / "python")
    
    def _get_venv_pip(self, venv_dir: Path) -> Optional[str]:
        """Get pip executable in venv"""
        if sys.platform == "win32":
            return str(venv_dir / "Scripts" / "pip.exe")
        return str(venv_dir / "bin" / "pip")


class Installer(QObject):
    """High-level installer interface"""
    
    progress = pyqtSignal(int, str)
    log_line = pyqtSignal(str)
    finished = pyqtSignal(bool, str)
    
    # Core packages that must be installed for client to work
    REQUIRED_PACKAGES = ["PyQt6", "requests", "psutil"]
    
    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._worker: Optional[InstallWorker] = None
    
    def is_installed(self, client_root: Path) -> bool:
        """Check if client is properly installed with dependencies"""
        client_root = Path(client_root)
        
        # Check for venv
        venv_dir = client_root / ".venv"
        if not venv_dir.exists():
            venv_dir = client_root / "venv"
        
        if not venv_dir.exists():
            return False
        
        # Check for python in venv
        if sys.platform == "win32":
            python_exe = venv_dir / "Scripts" / "python.exe"
        else:
            python_exe = venv_dir / "bin" / "python"
        
        if not python_exe.exists():
            return False
        
        # Check that core packages are installed
        try:
            result = subprocess.run(
                [str(python_exe), "-c", "import PyQt6.QtCore; print('OK')"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode != 0:
                return False
        except Exception:
            return False
        
        return True
    
    def needs_update(self, client_root: Path) -> bool:
        """Check if dependencies need update (requirements changed)"""
        # TODO: Compare requirements hash
        return False
    
    def install(self, client_root: Path, full: bool = False) -> None:
        """Start installation in background"""
        if self._worker and self._worker.isRunning():
            return
        
        self._worker = InstallWorker(client_root, install_full=full)
        self._worker.progress.connect(self.progress.emit)
        self._worker.log_line.connect(self.log_line.emit)
        self._worker.finished_result.connect(self._on_finished)
        self._worker.start()
    
    def cancel(self) -> None:
        """Cancel current installation"""
        if self._worker:
            self._worker.cancel()
    
    def _on_finished(self, success: bool, message: str) -> None:
        """Handle worker finish"""
        self.finished.emit(success, message)
        self._worker = None
