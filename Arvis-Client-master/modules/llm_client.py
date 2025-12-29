"""
LLM Client for Ollama integration
"""

import json
from typing import Any, Dict, List, Optional

import requests

from config.config import Config
from utils.logger import ModuleLogger


class LLMClient:
    """Client for communicating with Ollama LLM server"""

    def __init__(self, config: Config):
        self.config = config
        self.logger = ModuleLogger("LLMClient")
        # Принудительно используем 127.0.0.1 вместо localhost, чтобы избежать IPv6/hosts проблем
        cfg_url = config.get("llm.ollama_url", "http://localhost:11434")
        self.base_url = cfg_url.replace("localhost", "127.0.0.1")
        self.default_model = config.get("llm.default_model", "auto")
        self.temperature = config.get("llm.temperature", 0.7)
        self.max_tokens = config.get("llm.max_tokens", 2048)

        # Используем быстрый HTTP клиент
        from utils.fast_http import FastHTTPClient

        # Чуть более щадящий таймаут для стабильного /api/tags
        self.http_client = FastHTTPClient(self.base_url, timeout=6.0)

        # Резервная сессия для стриминга
        self.session = requests.Session()
        # Игнорировать системные прокси для локальных запросов
        self.session.trust_env = False
        self.session.timeout = 30

    def is_connected(self) -> bool:
        """Check if Ollama server is accessible (very fast)"""
        # Сначала лёгкая проверка /api/version (быстрее и менее шумная), затем /api/tags
        try:
            ver = self.session.get(f"{self.base_url}/api/version", timeout=(2.0, 3.0))
            if ver.status_code != 200:
                return False
        except Exception:
            return False

        result = self.http_client.is_alive()

        if result:
            self.logger.debug("Ollama connection confirmed")
        else:
            self.logger.debug("Ollama connection failed")

        return result

    def is_connected_async(self, callback):
        """Асинхронная проверка соединения"""
        from utils.async_manager import task_manager

        def check():
            return self.is_connected()

        task_manager.task_completed.connect(
            lambda task_id, result: callback(result) if task_id == "ollama_check" else None
        )
        task_manager.run_async("ollama_check", check)

    def get_available_models(self) -> List[str]:
        """Get list of available models (cached)"""
        result = self.http_client.get("/api/tags")
        try:
            if result["success"] and result["data"]:
                models = [
                    model.get("name", "") for model in result["data"].get("models", []) if isinstance(model, dict)
                ]
                models = [m for m in models if m]
                self.logger.debug(f"Found {len(models)} models")
                return models
            else:
                self.logger.error(f"Failed to get models: {result.get('error', 'unknown')}")
                return []
        except Exception as e:
            self.logger.error(f"Error parsing models list: {e}")
            return []

    def _ensure_model_selected(self):
        """Ensure a valid model is selected; fallback to first available."""
        try:
            available = self.get_available_models()
            if not available:
                return
            # If configured as 'auto' or selected model not present, pick the first available
            if self.default_model in (None, "", "auto") or self.default_model not in available:
                chosen = available[0]
                self.logger.info(f"Selecting available LLM model: {chosen}")
                self.default_model = chosen
                # Persist selection to config
                try:
                    self.config.set("llm.default_model", chosen)
                except Exception:
                    pass
        except Exception as e:
            self.logger.debug(f"Model selection check failed: {e}")

    def pull_model(self, model_name: str) -> bool:
        """Pull/download a model"""
        try:
            self.logger.info(f"Pulling model: {model_name}")
            response = self.session.post(f"{self.base_url}/api/pull", json={"name": model_name}, stream=True)

            if response.status_code == 200:
                self.logger.info(f"Model {model_name} pulled successfully")
                return True
            else:
                self.logger.error(f"Failed to pull model: {response.text}")
                return False

        except Exception as e:
            self.logger.error(f"Error pulling model: {e}")
            return False

    def get_response(
        self, message: str, context: str = "", conversation_history: List[Dict[str, str]] = None
    ) -> Optional[str]:
        """Get response from LLM"""
        try:
            # Build prompt
            prompt = self.build_prompt(message, context, conversation_history or [])
            # Ensure model is selected/available
            self._ensure_model_selected()

            # Prepare request data
            request_data = {
                "model": self.default_model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": self.temperature,
                    "num_predict": self.max_tokens,
                    "top_k": 40,
                    "top_p": 0.9,
                    "repeat_last_n": 64,
                    "repeat_penalty": 1.1,
                },
            }

            self.logger.debug(f"Sending request to {self.base_url}/api/generate")

            # Send request
            response = self.session.post(f"{self.base_url}/api/generate", json=request_data, timeout=60)

            if response.status_code == 200:
                data = response.json()
                llm_response = data.get("response", "").strip()

                if llm_response:
                    self.logger.info("Got response from LLM")
                    return llm_response
                else:
                    self.logger.warning("Empty response from LLM")
                    return "Извините, я не смог сформулировать ответ."
            else:
                self.logger.error(f"LLM request failed: {response.status_code} - {response.text}")
                return f"Ошибка сервера LLM: {response.status_code}"

        except requests.exceptions.Timeout:
            self.logger.error("LLM request timed out")
            return "Извините, запрос занял слишком много времени. Попробуйте еще раз."

        except requests.exceptions.ConnectionError:
            self.logger.error("Failed to connect to Ollama server")
            return "Не удается подключиться к серверу Ollama. Убедитесь, что он запущен."

        except Exception as e:
            self.logger.error(f"Error getting LLM response: {e}")
            return f"Произошла ошибка: {str(e)}"

    def stream_response(self, message: str, context: str = "", conversation_history: List[Dict[str, str]] = None):
        """Yield response chunks from LLM using Ollama's streaming API.

        Yields strings (partial tokens or fragments). Caller is responsible
        for assembling them.
        """
        try:
            prompt = self.build_prompt(message, context, conversation_history or [])
            self._ensure_model_selected()
            request_data = {
                "model": self.default_model,
                "prompt": prompt,
                "stream": True,
                "options": {
                    "temperature": self.temperature,
                    "num_predict": self.max_tokens,
                    "top_k": 40,
                    "top_p": 0.9,
                    "repeat_last_n": 64,
                    "repeat_penalty": 1.1,
                },
            }

            self.logger.debug(f"Starting streaming request to {self.base_url}/api/generate")

            response = self.session.post(f"{self.base_url}/api/generate", json=request_data, stream=True, timeout=120)

            # Debug: log HTTP status and headers to help diagnose streaming stalls
            try:
                self.logger.debug(
                    f"Streaming HTTP status={getattr(response, 'status_code', None)}, headers={getattr(response, 'headers', {})}"
                )
            except Exception:
                pass

            response.raise_for_status()

            try:
                for line in response.iter_lines(decode_unicode=True, chunk_size=1024):
                    if not line or line.isspace():
                        continue

                    try:
                        # Debug: log raw line for troubleshooting
                        try:
                            self.logger.debug(f"LLM stream raw line: {str(line)[:200]}")
                        except Exception:
                            pass

                        data = json.loads(line)
                        chunk = data.get("response", "")
                        if chunk:
                            yield chunk
                        if data.get("done", False):
                            break
                    except json.JSONDecodeError as je:
                        self.logger.debug(f"Non-JSON line received (ignoring): {line[:50]}...")
                        continue
                    except Exception as e:
                        self.logger.warning(f"Error processing stream line: {e}")
                        continue

            finally:
                # Ensure response is properly closed
                try:
                    response.close()
                except Exception:
                    pass

        except requests.exceptions.Timeout:
            self.logger.warning("Streaming request timed out")
            yield ""
        except requests.exceptions.ConnectionError as ce:
            self.logger.error(f"Connection error during streaming: {ce}")
            yield ""
        except Exception as e:
            self.logger.error(f"Streaming error: {e}")
            yield ""

    def build_prompt(self, message: str, context: str, conversation_history: List[Dict[str, str]]) -> str:
        """Build complete prompt with context and history"""
        prompt_parts = []

        # Определяем язык интерфейса для ответов
        ui_language = self.config.get("language.ui", "ru")
        language_map = {"ru": "русском", "uk": "украинском", "en": "английском", "es": "испанском"}
        response_language = language_map.get(ui_language, "русском")

        # ═══════════════════════════════════════════════════════════════════
        # СИСТЕМНЫЙ ПРОМПТ ARVIS - здесь определяется личность и поведение ИИ
        # ═══════════════════════════════════════════════════════════════════
        system_prompt = f"""Ты - Arvis, персональный голосовой ИИ-ассистент.

ТВОЯ РОЛЬ И ВОЗМОЖНОСТИ:
{context}

СТИЛЬ ОБЩЕНИЯ:
- Отвечай на {response_language} языке
- По умолчанию - КРАТКО и ПО СУЩЕСТВУ (1-3 предложения)
- Развёрнуто отвечай только когда пользователь явно просит "расскажи подробнее", "объясни детально" и т.п.
- НЕ перечисляй свои возможности в каждом ответе - пользователь уже знает что ты умеешь
- Используй естественный разговорный тон, как живой помощник

ПРАВИЛА ОТВЕТОВ:
1. Прямой вопрос → Прямой ответ (без вступлений "Конечно!", "Хорошо!" и т.п.)
2. Не уверен → Честно признайся вместо выдумывания
3. Ошибка/непонятно → Переспроси конкретно что нужно
4. Уже выполнено модулем → Не дублируй информацию
5. Технические термины → Объясняй простыми словами если не попросили иначе

ОСОБЕННОСТИ:
- У тебя есть ДОЛГОВРЕМЕННАЯ ПАМЯТЬ - ты помнишь всю историю разговоров даже после перезапуска
- В каждый запрос передаются последние 6 сообщений для контекста, но вся история сохраняется
- Для команд компьютера ("открой Chrome", "выключи звук") давай подтверждение выполнения
- Для фактов (погода, новости) не добавляй лишних рассуждений
- Можешь использовать эмодзи для наглядности, но умеренно

Будь полезным помощником с хорошей памятью, а не болтливым роботом."""

        prompt_parts.append(system_prompt)

        # Add conversation history (last 6 messages to keep context manageable)
        if conversation_history:
            recent_history = conversation_history[-6:]
            for entry in recent_history:
                role = "Пользователь" if entry["role"] == "user" else "Arvis"
                prompt_parts.append(f"{role}: {entry['content']}")

        # Current message
        prompt_parts.append(f"Пользователь: {message}")
        prompt_parts.append("Arvis:")

        return "\n\n".join(prompt_parts)

    def warm_up_model(self) -> bool:
        """Warm up the model with a simple request"""
        try:
            self.logger.info("Warming up LLM model...")
            response = self.get_response("Привет!", "Ты - Arvis, ИИ-ассистент.")
            return response is not None
        except Exception as e:
            self.logger.error(f"Model warm-up failed: {e}")
            return False

    def check_model_exists(self, model_name: str) -> bool:
        """Check if a specific model exists locally"""
        available_models = self.get_available_models()
        return model_name in available_models

    def set_model(self, model_name: str):
        """Set the active model"""
        if self.check_model_exists(model_name):
            self.default_model = model_name
            self.config.set("llm.default_model", model_name)
            self.logger.info(f"Model set to: {model_name}")
            return True
        else:
            self.logger.error(f"Model {model_name} not found")
            return False

    def get_model_info(self, model_name: str = None) -> Optional[Dict[str, Any]]:
        """Get information about a model"""
        try:
            target_model = model_name or self.default_model
            response = self.session.post(f"{self.base_url}/api/show", json={"name": target_model})

            if response.status_code == 200:
                return response.json()
            else:
                self.logger.error(f"Failed to get model info: {response.text}")
                return None

        except Exception as e:
            self.logger.error(f"Error getting model info: {e}")
            return None

    def diagnose_connection(self) -> Dict[str, Any]:
        """Детальная диагностика подключения к Ollama"""
        diagnosis = {
            "base_url": self.base_url,
            "connection_status": "unknown",
            "available_models": [],
            "selected_model": self.default_model,
            "errors": [],
        }

        try:
            # Проверяем основное соединение
            response = self.session.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                diagnosis["connection_status"] = "connected"

                # Получаем список моделей
                data = response.json()
                models = [model["name"] for model in data.get("models", [])]
                diagnosis["available_models"] = models

                # Проверяем наличие выбранной модели
                if self.default_model not in models and models:
                    diagnosis["errors"].append(f"Выбранная модель '{self.default_model}' не найдена")

                self.logger.info(f"Ollama диагностика: подключено, моделей: {len(models)}")
            else:
                diagnosis["connection_status"] = "error"
                diagnosis["errors"].append(f"HTTP {response.status_code}: {response.text}")

        except requests.exceptions.ConnectionError:
            diagnosis["connection_status"] = "no_connection"
            diagnosis["errors"].append("Не удается подключиться к Ollama серверу")

        except requests.exceptions.Timeout:
            diagnosis["connection_status"] = "timeout"
            diagnosis["errors"].append("Таймаут подключения к Ollama")

        except Exception as e:
            diagnosis["connection_status"] = "error"
            diagnosis["errors"].append(f"Ошибка: {str(e)}")

        return diagnosis
