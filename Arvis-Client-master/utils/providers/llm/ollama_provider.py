"""
Local LLM Provider (Ollama)
Локальный провайдер Language Model на основе Ollama

Priority: 1 (очень высокий приоритет для локальных компонентов)
"""

from typing import Optional

from config.config import Config
from modules.llm_client import LLMClient
from utils.logger import ModuleLogger
from utils.providers import LLMProvider


class OllamaLLMProvider(LLMProvider):
    """
    Провайдер для локальных языковых моделей через Ollama.
    
    Требует:
    - Ollama server запущен на localhost:11434
    - Загруженная модель (mistral:7b, llama2, etc)
    """

    def __init__(self, config: Config):
        super().__init__("ollama")
        self.config = config
        self.llm_client: Optional[LLMClient] = None
        self._initialized = False

    def get_priority(self) -> int:
        """Локальные компоненты имеют максимальный приоритет"""
        return 1

    def initialize(self) -> bool:
        """Инициализировать Ollama LLM"""
        try:
            if self._initialized:
                return self.is_available()

            self.logger.info("Initializing Ollama LLM client...")
            self.llm_client = LLMClient(self.config)

            if not self.llm_client:
                self.logger.error("Failed to create LLM client")
                self._status.value = "unavailable"
                return False

            # Проверить доступность Ollama
            if not self.llm_client.check_connection():
                self.logger.warning("Ollama server is not reachable")
                self._status.value = "unavailable"
                return False

            self._initialized = True
            self._status.value = "available"
            self.logger.info("✓ Ollama LLM initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize Ollama LLM: {e}")
            self.set_error(str(e))
            return False

    def is_available(self) -> bool:
        """Проверить доступность Ollama LLM"""
        try:
            if not self._initialized or self.llm_client is None:
                return False

            # Проверяем соединение
            return self.llm_client.check_connection()

        except Exception as e:
            self.logger.debug(f"Ollama availability check failed: {e}")
            return False

    def generate_response(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None,
    ) -> str:
        """
        Сгенерировать ответ на запрос.
        
        Args:
            prompt: Текст запроса
            temperature: Температура (0.0 - 1.0)
            max_tokens: Максимальное количество токенов
            system_prompt: Системный промпт
            
        Returns:
            Сгенерированный ответ
        """
        if not self.is_available():
            raise RuntimeError("Ollama LLM is not available")

        try:
            if self.llm_client is None:
                raise RuntimeError("LLM client not initialized")

            # Используем встроенный метод LLM client
            response = self.llm_client.generate(
                prompt=prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                system_prompt=system_prompt,
                stream=False,
            )

            return response

        except Exception as e:
            self.logger.error(f"Ollama generation failed: {e}")
            raise RuntimeError(f"Ollama generation error: {e}")

    def stream_response(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None,
    ):
        """
        Сгенерировать ответ потоком (streaming).
        
        Args:
            prompt: Текст запроса
            temperature: Температура
            max_tokens: Максимальное количество токенов
            system_prompt: Системный промпт
            
        Yields:
            Чанки ответа
        """
        if not self.is_available():
            raise RuntimeError("Ollama LLM is not available")

        try:
            if self.llm_client is None:
                raise RuntimeError("LLM client not initialized")

            # Используем встроенный метод для потокового ответа
            for chunk in self.llm_client.stream_response(
                prompt=prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                system_prompt=system_prompt,
            ):
                yield chunk

        except Exception as e:
            self.logger.error(f"Ollama stream generation failed: {e}")
            raise RuntimeError(f"Ollama stream generation error: {e}")

    def shutdown(self) -> bool:
        """Завершить работу Ollama LLM"""
        try:
            if self.llm_client:
                # LLMClient не требует явного завершения
                self.llm_client = None

            self._initialized = False
            self._status.value = "unavailable"
            self.logger.info("✓ Ollama LLM shutdown complete")
            return True

        except Exception as e:
            self.logger.error(f"Ollama LLM shutdown failed: {e}")
            return False
