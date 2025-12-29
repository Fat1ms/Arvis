"""
Ollama Process Manager
Безопасное управление Ollama сервером без использования .bat файлов
"""

import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional, Tuple

import requests

from utils.logger import ModuleLogger


class OllamaManager:
    """Manages Ollama server process lifecycle"""

    def __init__(self, config):
        self.config = config
        self.logger = ModuleLogger("OllamaManager")
        self.process: Optional[subprocess.Popen] = None
        self.ollama_url = config.get("llm.ollama_url", "http://127.0.0.1:11434")
        # Новая структура настроек безопасности (v1.5.0)
        self.bind_address = str(
            config.get(
                "security.ollama.bind_address",
                config.get("security.ollama_bind_address", "127.0.0.1"),
            )
            or "127.0.0.1"
        )
        self.allow_external = bool(
            config.get(
                "security.ollama.allow_external",
                config.get("security.ollama_allow_external", False),
            )
        )
        if self.allow_external and self.bind_address == "127.0.0.1":
            self.bind_address = "0.0.0.0"
        elif not self.allow_external and self.bind_address == "0.0.0.0":
            self.bind_address = "127.0.0.1"
        if hasattr(config, "get_ollama_launch_mode"):
            self.launch_mode = str(config.get_ollama_launch_mode() or "background").lower()
        else:
            self.launch_mode = str(
                config.get(
                    "security.ollama.launch_mode",
                    config.get("startup.ollama_launch_mode", "background"),
                )
                or "background"
            ).lower()
        self.auto_restart = bool(config.get("security.ollama.auto_restart", True))
        self.logs_path = Path(str(config.get("paths.logs", "logs") or "logs"))
        self.logs_path.mkdir(parents=True, exist_ok=True)
        self._managed_streams = []

    def is_ollama_running(self) -> bool:
        """Check if Ollama server is already running"""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=2)
            return response.status_code == 200
        except Exception:
            return False

    def find_ollama_executable(self) -> Optional[str]:
        """Find Ollama executable in system PATH"""
        try:
            # Try to find ollama in PATH
            if os.name == "nt":  # Windows
                # Check common installation paths
                possible_paths = [
                    r"C:\Users\{}\AppData\Local\Programs\Ollama\ollama.exe".format(os.environ.get("USERNAME", "")),
                    r"C:\Program Files\Ollama\ollama.exe",
                    r"C:\Program Files (x86)\Ollama\ollama.exe",
                ]

                for path in possible_paths:
                    if os.path.exists(path):
                        self.logger.info(f"Found Ollama at: {path}")
                        return path

                # Try using 'where' command
                result = subprocess.run(
                    ["where", "ollama"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
                if result.returncode == 0 and result.stdout.strip():
                    path = result.stdout.strip().split("\n")[0]
                    self.logger.info(f"Found Ollama via 'where': {path}")
                    return path
            else:  # Linux/Mac
                result = subprocess.run(["which", "ollama"], capture_output=True, text=True, timeout=5)
                if result.returncode == 0 and result.stdout.strip():
                    path = result.stdout.strip()
                    self.logger.info(f"Found Ollama at: {path}")
                    return path

            self.logger.warning("Ollama executable not found in PATH")
            return None

        except Exception as e:
            self.logger.error(f"Error finding Ollama executable: {e}")
            return None

    def start_ollama(self, wait_for_ready: bool = True, launch_mode: Optional[str] = None) -> Tuple[bool, str]:
        """
        Start Ollama server process

        Args:
            wait_for_ready: Wait for server to be ready before returning
            launch_mode: Override launch mode (background|console|detached)

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            # Check if already running
            if self.is_ollama_running():
                self.logger.info("Ollama is already running")
                return True, "Ollama уже запущен"

            mode = str(launch_mode or self.launch_mode or "background").lower()
            if mode not in {"background", "console", "detached"}:
                self.logger.warning(f"Unknown Ollama launch mode '{mode}', fallback to 'background'")
                mode = "background"

            # Find executable
            ollama_exe = self.find_ollama_executable()
            if not ollama_exe:
                return False, "Ollama не найден. Установите Ollama с https://ollama.ai"

            # Prepare environment
            env = os.environ.copy()

            # Set bind address for security
            if not self.allow_external:
                env["OLLAMA_HOST"] = f"{self.bind_address}:11434"
                self.logger.info(f"Ollama will bind to {self.bind_address} (local only)")
            else:
                env["OLLAMA_HOST"] = "0.0.0.0:11434"
                self.logger.warning("Ollama will bind to 0.0.0.0 (external access allowed)")

            # Start process
            self.logger.info(f"Starting Ollama server ({mode} mode): {ollama_exe} serve")

            stdout_target = subprocess.PIPE
            stderr_target = subprocess.PIPE
            startupinfo = None
            creationflags = 0
            popen_kwargs = {
                "env": env,
                "stdin": subprocess.DEVNULL,
                "cwd": str(Path(ollama_exe).parent),
            }

            if os.name == "nt":  # Windows
                if mode == "console":
                    creationflags = subprocess.CREATE_NEW_CONSOLE | subprocess.CREATE_NEW_PROCESS_GROUP
                    stdout_target = None
                    stderr_target = None
                elif mode == "detached":
                    creationflags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
                    stdout_target = open(self.logs_path / "ollama.out.log", "a", encoding="utf-8")
                    stderr_target = open(self.logs_path / "ollama.err.log", "a", encoding="utf-8")
                    for stream in (stdout_target, stderr_target):
                        if stream is not None:
                            self._managed_streams.append(stream)
                else:  # background (default)
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    startupinfo.wShowWindow = subprocess.SW_HIDE
                    creationflags = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
            else:  # Linux/Mac
                if mode == "detached":
                    stdout_target = open(self.logs_path / "ollama.out.log", "a", encoding="utf-8")
                    stderr_target = open(self.logs_path / "ollama.err.log", "a", encoding="utf-8")
                    for stream in (stdout_target, stderr_target):
                        if stream is not None:
                            self._managed_streams.append(stream)
                elif mode == "console":
                    stdout_target = None
                    stderr_target = None
                popen_kwargs["start_new_session"] = True

            self.process = subprocess.Popen(
                [ollama_exe, "serve"],
                stdout=stdout_target,
                stderr=stderr_target,
                startupinfo=startupinfo,
                creationflags=creationflags,
                **popen_kwargs,
            )

            self.logger.info(f"Ollama process started (PID: {self.process.pid})")

            # Wait for server to be ready
            if wait_for_ready:
                self.logger.info("Waiting for Ollama server to be ready...")
                max_wait = 30  # seconds
                start_time = time.time()

                while time.time() - start_time < max_wait:
                    if self.is_ollama_running():
                        elapsed = time.time() - start_time
                        self.logger.info(f"Ollama server ready in {elapsed:.1f}s")
                        return True, f"Ollama запущен успешно ({elapsed:.1f}s)"

                    time.sleep(0.5)

                # Timeout
                self.logger.error("Ollama server failed to start within timeout")
                return False, "Ollama не ответил за 30 секунд"

            return True, "Ollama запускается..."

        except Exception as e:
            error_msg = f"Ошибка запуска Ollama: {e}"
            self.logger.error(error_msg)
            for stream in self._managed_streams:
                try:
                    if stream and not stream.closed:
                        stream.close()
                except Exception:
                    pass
            self._managed_streams.clear()
            return False, error_msg

    def stop_ollama(self) -> Tuple[bool, str]:
        """
        Stop Ollama server process

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            if not self.process:
                self.logger.warning("No Ollama process tracked, cannot stop")
                return False, "Процесс Ollama не отслеживается"

            self.logger.info(f"Stopping Ollama process (PID: {self.process.pid})")

            # Try graceful shutdown first
            self.process.terminate()

            # Wait for graceful shutdown
            try:
                self.process.wait(timeout=10)
                self.logger.info("Ollama stopped gracefully")
            except subprocess.TimeoutExpired:
                # Force kill if necessary
                self.logger.warning("Ollama didn't stop gracefully, forcing...")
                self.process.kill()
                self.process.wait(timeout=5)
                self.logger.info("Ollama force-stopped")

            self.process = None
            # Close managed streams
            for stream in self._managed_streams:
                try:
                    if stream and not stream.closed:
                        stream.close()
                except Exception:
                    pass
            self._managed_streams.clear()
            return True, "Ollama остановлен"

        except Exception as e:
            error_msg = f"Ошибка остановки Ollama: {e}"
            self.logger.error(error_msg)
            return False, error_msg

    def restart_ollama(self) -> Tuple[bool, str]:
        """
        Restart Ollama server

        Returns:
            Tuple of (success: bool, message: str)
        """
        self.logger.info("Restarting Ollama server...")

        # Stop if running
        if self.process:
            success, msg = self.stop_ollama()
            if not success:
                return False, f"Не удалось остановить Ollama: {msg}"

        # Wait a bit
        time.sleep(2)

        # Start again
        return self.start_ollama(wait_for_ready=True)

    def get_status(self) -> dict:
        """
        Get Ollama server status

        Returns:
            Dictionary with status information
        """
        status = {
            "running": False,
            "process_tracked": self.process is not None,
            "url": self.ollama_url,
            "models": [],
            "version": None,
        }

        try:
            # Check if running
            if self.is_ollama_running():
                status["running"] = True

                # Get available models
                try:
                    response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
                    if response.status_code == 200:
                        data = response.json()
                        status["models"] = [model.get("name", "") for model in data.get("models", [])]
                except Exception as e:
                    self.logger.debug(f"Failed to get models: {e}")

                # Get version
                try:
                    response = requests.get(f"{self.ollama_url}/api/version", timeout=5)
                    if response.status_code == 200:
                        status["version"] = response.json().get("version")
                except Exception as e:
                    self.logger.debug(f"Failed to get version: {e}")

        except Exception as e:
            self.logger.error(f"Error getting Ollama status: {e}")

        return status

    def ensure_model_available(self, model_name: str) -> Tuple[bool, str]:
        """
        Check if model is available, pull if necessary

        Args:
            model_name: Name of the model (e.g., "mistral:7b")

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            if not self.is_ollama_running():
                return False, "Ollama не запущен"

            # Check if model exists
            status = self.get_status()
            if model_name in status["models"]:
                return True, f"Модель {model_name} доступна"

            # Model not found, need to pull
            self.logger.info(f"Model {model_name} not found, pulling...")

            # Note: Pulling models should be done through LLM client or manually
            # This is just a check
            return False, f"Модель {model_name} не найдена. Выполните: ollama pull {model_name}"

        except Exception as e:
            error_msg = f"Ошибка проверки модели: {e}"
            self.logger.error(error_msg)
            return False, error_msg

    def cleanup(self):
        """Cleanup on shutdown"""
        try:
            autostart = self.config.get("startup.autostart_ollama", False)

            if self.process and autostart:
                # If we started Ollama, we should stop it on cleanup
                self.logger.info("Cleaning up: stopping Ollama process")
                self.stop_ollama()
        except Exception as e:
            self.logger.error(f"Cleanup error: {e}")


# Global instance
_ollama_manager_instance: Optional[OllamaManager] = None


def get_ollama_manager(config=None) -> OllamaManager:
    """Get or create global OllamaManager instance"""
    global _ollama_manager_instance
    if _ollama_manager_instance is None:
        if config is None:
            from config.config import Config

            config = Config()
        _ollama_manager_instance = OllamaManager(config)
    return _ollama_manager_instance
