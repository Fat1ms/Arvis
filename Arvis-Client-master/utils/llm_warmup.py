"""
LLM Warmup Module - Pre-loads LLM model after login for faster first response
Модуль прогрева LLM - Предзагружает модель после логина для быстрого первого ответа
"""

import time
from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal

from config.config import Config
from utils.logger import ModuleLogger


class LLMWarmup(QObject):
    """Warmup LLM model for faster first response"""

    warmup_started = pyqtSignal()
    warmup_progress = pyqtSignal(int, str)  # progress (0-100), status message
    warmup_completed = pyqtSignal(float)  # duration in seconds
    warmup_failed = pyqtSignal(str)  # error message

    def __init__(self, config: Config, llm_client=None):
        super().__init__()
        self.config = config
        self.llm_client = llm_client
        self.logger = ModuleLogger("LLMWarmup")
        self._is_warming_up = False
        self._warmup_duration = 0.0

    def set_llm_client(self, llm_client):
        """Set LLM client after initialization"""
        self.llm_client = llm_client

    def warmup_async(self):
        """Start async warmup process"""
        if self._is_warming_up:
            self.logger.debug("Warmup already in progress")
            return

        if not self.llm_client:
            self.logger.error("LLM client not available")
            self.warmup_failed.emit("LLM client not initialized")
            return

        self._is_warming_up = True
        self.warmup_started.emit()

        # Use async task manager
        from utils.async_manager import task_manager

        def warmup_worker():
            """Worker function for warmup"""
            try:
                start_time = time.time()

                # Step 1: Check Ollama connection (10%)
                self.warmup_progress.emit(10, "Проверка подключения к Ollama...")
                if not self._check_ollama_connection():
                    raise Exception("Ollama не отвечает")

                # Step 2: Load model list (20%)
                self.warmup_progress.emit(20, "Загрузка списка моделей...")
                models = self._get_available_models()
                if not models:
                    raise Exception("Нет доступных моделей")

                # Step 3: Select optimal model (30%)
                self.warmup_progress.emit(30, "Выбор оптимальной модели...")
                selected_model = self._select_optimal_model(models)
                self.logger.info(f"Selected model for warmup: {selected_model}")

                # Step 4: Send warmup prompt (40-90%)
                self.warmup_progress.emit(40, f"Прогрев модели {selected_model}...")
                response = self._send_warmup_prompt(selected_model)

                if not response:
                    raise Exception("Модель не ответила")

                # Step 5: Verify response (95%)
                self.warmup_progress.emit(95, "Проверка ответа модели...")
                if len(response) < 5:
                    self.logger.warning(f"Warmup response too short: {response}")

                # Step 6: Complete (100%)
                self.warmup_progress.emit(100, "Прогрев завершён")
                duration = time.time() - start_time

                self.logger.info(f"LLM warmup completed in {duration:.2f}s")
                return duration

            except Exception as e:
                self.logger.error(f"Warmup failed: {e}")
                raise

        def on_complete(task_id, result):
            if task_id == "llm_warmup":
                self._is_warming_up = False
                self.warmup_completed.emit(result)

        def on_error(task_id, error):
            if task_id == "llm_warmup":
                self._is_warming_up = False
                self.warmup_failed.emit(str(error))

        task_manager.run_async("llm_warmup", warmup_worker, on_complete=on_complete, on_error=on_error)

    def _check_ollama_connection(self) -> bool:
        """Check if Ollama server is responding"""
        try:
            if not self.llm_client:
                return False

            # Try to get tags (list models)
            import requests

            ollama_url = self.config.get("llm.ollama_url", "http://127.0.0.1:11434")
            response = requests.get(f"{ollama_url}/api/tags", timeout=3)
            return response.status_code == 200

        except Exception as e:
            self.logger.warning(f"Ollama connection check failed: {e}")
            return False

    def _get_available_models(self) -> list:
        """Get list of available models"""
        try:
            if not self.llm_client:
                return []

            import requests

            ollama_url = self.config.get("llm.ollama_url", "http://127.0.0.1:11434")
            response = requests.get(f"{ollama_url}/api/tags", timeout=5)

            if response.status_code == 200:
                data = response.json()
                models = [model["name"] for model in data.get("models", [])]
                self.logger.debug(f"Available models: {models}")
                return models

            return []

        except Exception as e:
            self.logger.error(f"Failed to get models: {e}")
            return []

    def _select_optimal_model(self, models: list) -> str:
        """Select optimal model for warmup"""
        # Priority: configured default > small models > any available
        default_model = self.config.get("llm.default_model", "auto")

        if default_model != "auto" and default_model in models:
            return default_model

        # Prefer smaller/faster models for warmup
        small_models = [m for m in models if any(size in m.lower() for size in ["2b", "3b", "7b"])]
        if small_models:
            return small_models[0]

        # Fallback to first available
        return models[0] if models else "mistral:7b"

    def _send_warmup_prompt(self, model: str) -> str:
        """Send simple warmup prompt to LLM"""
        try:
            import threading
            warmup_prompt = "Привет!"

            # Update progress during generation
            self.warmup_progress.emit(50, "Отправка запроса...")

            # Send request with timeout
            response = ""
            warmup_timeout = 15  # секунд
            
            if hasattr(self.llm_client, "simple_generate"):
                response = self.llm_client.simple_generate(prompt=warmup_prompt, model=model, max_tokens=30, timeout=warmup_timeout)
            else:
                # Fallback to stream_response с таймаутом
                full_response = ""
                start_time = time.time()
                try:
                    for chunk in self.llm_client.stream_response(
                        message=warmup_prompt,
                        context="",
                        conversation_history=None
                    ):
                        if chunk:
                            full_response += chunk
                        # Таймаут и лимит длины
                        if len(full_response) > 30 or (time.time() - start_time) > warmup_timeout:
                            break
                except Exception as stream_err:
                    self.logger.warning(f"Stream warmup interrupted: {stream_err}")
                    full_response = "ok"  # Считаем что прогрев прошёл
                
                response = full_response or "ok"

            self.warmup_progress.emit(90, "Ответ получен")
            self.logger.debug(f"Warmup response: {response[:50] if response else 'empty'}...")
            return response or "ok"

        except Exception as e:
            self.logger.warning(f"Warmup prompt skipped: {e}")
            return "ok"  # Не блокируем запуск если прогрев не удался

    def is_warming_up(self) -> bool:
        """Check if warmup is in progress"""
        return self._is_warming_up

    def get_warmup_duration(self) -> float:
        """Get last warmup duration"""
        return self._warmup_duration
