"""
Operation Mode and Provider framework for hybrid Arvis architecture
Фреймворк режимов работы и провайдеров для гибридной архитектуры Arvis

v1.0 - October 21, 2025
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from utils.logger import ModuleLogger


class OperationMode(Enum):
    """
    Режимы работы Arvis приложения
    
    STANDALONE: Полностью локальный режим (без интернета, без сервера)
    HYBRID: Локальный + опциональное подключение к серверу/облаку
    CLOUD: Облачный режим (требует интернета)
    """

    STANDALONE = "standalone"
    HYBRID = "hybrid"
    CLOUD = "cloud"

    def get_display_name(self) -> str:
        """Получить локализованное имя режима"""
        names = {
            OperationMode.STANDALONE: "Автономный режим",
            OperationMode.HYBRID: "Гибридный режим",
            OperationMode.CLOUD: "Облачный режим",
        }
        return names.get(self, self.value)

    def requires_internet(self) -> bool:
        """Требуется ли интернет для этого режима"""
        return self != OperationMode.STANDALONE

    def requires_server(self) -> bool:
        """Требуется ли сервер для этого режима"""
        return self in [OperationMode.HYBRID, OperationMode.CLOUD]

    def is_offline_capable(self) -> bool:
        """Может ли работать в офлайн режиме"""
        return self in [OperationMode.STANDALONE, OperationMode.HYBRID]


class ProviderType(Enum):
    """Типы провайдеров"""

    STT = "stt"  # Speech-to-Text
    TTS = "tts"  # Text-to-Speech
    LLM = "llm"  # Language Model
    AUTH = "auth"  # Authentication


class ProviderStatus(Enum):
    """Статус провайдера"""

    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    ERROR = "error"
    INITIALIZING = "initializing"
    DEGRADED = "degraded"  # Частичная функциональность


class Provider(ABC):
    """
    Базовый интерфейс для всех провайдеров
    
    Все STT, TTS, LLM, Auth провайдеры должны наследоваться от этого класса.
    """

    def __init__(self, name: str, provider_type: ProviderType):
        self.name = name
        self.provider_type = provider_type
        self.logger = ModuleLogger(f"{provider_type.value.upper()}_{name}")
        self._status = ProviderStatus.INITIALIZING
        self._last_error: Optional[str] = None

    @abstractmethod
    def is_available(self) -> bool:
        """
        Проверить, доступен ли провайдер.
        
        Returns:
            True если провайдер доступен и готов к использованию
        """
        pass

    @abstractmethod
    def initialize(self) -> bool:
        """
        Инициализировать провайдера.
        
        Returns:
            True если инициализация успешна
        """
        pass

    @abstractmethod
    def shutdown(self) -> bool:
        """
        Корректно завершить работу провайдера.
        
        Returns:
            True если завершение успешно
        """
        pass

    def get_priority(self) -> int:
        """
        Приоритет провайдера (ниже = приоритетнее).
        
        Используется в FallbackManager для выбора порядка попыток.
        Локальные провайдеры должны иметь приоритет 0-10
        Облачные провайдеры должны иметь приоритет 20-100
        """
        return 50

    def get_name(self) -> str:
        """Получить имя провайдера"""
        return self.name

    def get_status(self) -> Dict[str, Any]:
        """
        Получить полный статус провайдера.
        
        Returns:
            Dict с информацией о статусе
        """
        return {
            "name": self.name,
            "type": self.provider_type.value,
            "available": self.is_available(),
            "status": self._status.value,
            "last_error": self._last_error,
        }

    def set_error(self, error: str):
        """Установить статус ошибки"""
        self._last_error = error
        self._status = ProviderStatus.ERROR
        self.logger.error(f"Provider error: {error}")

    def clear_error(self):
        """Очистить статус ошибки"""
        self._last_error = None
        if self.is_available():
            self._status = ProviderStatus.AVAILABLE
        else:
            self._status = ProviderStatus.UNAVAILABLE


class STTProvider(Provider):
    """Интерфейс для Speech-to-Text провайдеров"""

    def __init__(self, name: str):
        super().__init__(name, ProviderType.STT)

    @abstractmethod
    def recognize(self, audio: bytes, language: Optional[str] = None) -> str:
        """
        Распознать речь в аудиофайле.
        
        Args:
            audio: Аудиоданные в байтах
            language: Язык (например, 'ru', 'en'). Если None - использовать по умолчанию
            
        Returns:
            Распознанный текст
            
        Raises:
            RuntimeError: Если распознавание не удалось
        """
        pass

    @abstractmethod
    def stream_recognize(self, audio_stream) -> str:
        """
        Распознать речь из потока (для real-time).
        
        Args:
            audio_stream: Поток аудиоданных
            
        Returns:
            Распознанный текст
        """
        pass


class TTSProvider(Provider):
    """Интерфейс для Text-to-Speech провайдеров"""

    def __init__(self, name: str):
        super().__init__(name, ProviderType.TTS)

    @abstractmethod
    def synthesize(self, text: str, language: Optional[str] = None) -> bytes:
        """
        Синтезировать речь из текста.
        
        Args:
            text: Текст для синтеза
            language: Язык (например, 'ru', 'en'). Если None - использовать по умолчанию
            
        Returns:
            Аудиоданные в байтах
            
        Raises:
            RuntimeError: Если синтез не удалось
        """
        pass

    @abstractmethod
    def stream_synthesize(self, text: str, language: Optional[str] = None):
        """
        Синтезировать речь из текста потоком.
        
        Args:
            text: Текст для синтеза
            language: Язык
            
        Yields:
            Чанки аудиоданных
        """
        pass


class LLMProvider(Provider):
    """Интерфейс для Language Model провайдеров"""

    def __init__(self, name: str):
        super().__init__(name, ProviderType.LLM)

    @abstractmethod
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
            max_tokens: Максимальное количество токенов в ответе
            system_prompt: Системный промпт (инструкции для модели)
            
        Returns:
            Сгенерированный ответ
            
        Raises:
            RuntimeError: Если генерация не удалось
        """
        pass

    @abstractmethod
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
        pass


class AuthProvider(Provider):
    """Интерфейс для Authentication провайдеров"""

    def __init__(self, name: str):
        super().__init__(name, ProviderType.AUTH)

    @abstractmethod
    def authenticate(self, username: str, password: str, totp_code: Optional[str] = None) -> Dict[str, Any]:
        """
        Аутентифицировать пользователя.
        
        Args:
            username: Имя пользователя
            password: Пароль
            totp_code: TOTP код для двухфакторной аутентификации
            
        Returns:
            Dict с информацией о пользователе и токенами
            
        Raises:
            RuntimeError: Если аутентификация не удалось
        """
        pass

    @abstractmethod
    def validate_token(self, token: str) -> bool:
        """
        Проверить валидность токена.
        
        Args:
            token: Токен для проверки
            
        Returns:
            True если токен валиден
        """
        pass


class FallbackManager:
    """
    Менеджер для управления fallback логикой между провайдерами.
    
    Попытается использовать провайдеры по приоритету.
    Если один провайдер не работает, переключится на следующий.
    """

    def __init__(self, providers: List[Provider], logger: Optional[ModuleLogger] = None):
        """
        Args:
            providers: Список провайдеров (будет отсортирован по приоритету)
            logger: Logger для логирования операций
        """
        self.providers = sorted(providers, key=lambda p: p.get_priority())
        self.logger = logger or ModuleLogger("FallbackManager")
        self.execution_stats = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "provider_stats": {p.get_name(): {"success": 0, "failed": 0} for p in self.providers},
        }

    def execute(
        self,
        operation: Callable,
        *args,
        operation_name: str = "operation",
        **kwargs,
    ) -> Any:
        """
        Выполнить операцию с fallback между провайдерами.
        
        Args:
            operation: Функция для выполнения (должна принять провайдера как первый аргумент)
            *args: Позиционные аргументы для operation
            operation_name: Имя операции для логирования
            **kwargs: Именованные аргументы для operation
            
        Returns:
            Результат операции
            
        Raises:
            RuntimeError: Если все провайдеры не удались
        """
        self.execution_stats["total_calls"] += 1
        last_error: Optional[Exception] = None

        for provider in self.providers:
            provider_name = provider.get_name()

            if not provider.is_available():
                self.logger.debug(f"Provider '{provider_name}' not available, skipping {operation_name}")
                continue

            try:
                self.logger.debug(f"Trying provider '{provider_name}' for {operation_name}")
                result = operation(provider, *args, **kwargs)

                self.logger.info(f"✓ Success with provider '{provider_name}' for {operation_name}")
                self.execution_stats["successful_calls"] += 1
                self.execution_stats["provider_stats"][provider_name]["success"] += 1

                return result

            except Exception as e:
                last_error = e
                self.logger.warning(
                    f"✗ Provider '{provider_name}' failed for {operation_name}: {type(e).__name__}: {e}"
                )
                self.execution_stats["provider_stats"][provider_name]["failed"] += 1
                provider.set_error(str(e))
                continue

        # Все провайдеры не удались
        self.execution_stats["failed_calls"] += 1
        self.logger.error(f"✗ All providers failed for {operation_name}")

        if last_error:
            raise last_error
        else:
            raise RuntimeError(f"No available providers for {operation_name}")

    def get_available_providers(self) -> List[Provider]:
        """Получить список доступных провайдеров"""
        return [p for p in self.providers if p.is_available()]

    def get_status(self) -> Dict[str, Any]:
        """Получить статус всех провайдеров"""
        return {
            "providers": [p.get_status() for p in self.providers],
            "available_count": len(self.get_available_providers()),
            "stats": self.execution_stats,
        }

    def initialize_all(self) -> bool:
        """Инициализировать всех провайдеров"""
        all_initialized = True
        for provider in self.providers:
            try:
                if not provider.initialize():
                    self.logger.warning(f"Provider '{provider.get_name()}' initialization failed")
                    all_initialized = False
            except Exception as e:
                self.logger.error(f"Provider '{provider.get_name()}' initialization error: {e}")
                all_initialized = False

        if not self.get_available_providers():
            self.logger.error("No available providers after initialization")
            return False

        return all_initialized

    def shutdown_all(self) -> bool:
        """Корректно завершить работу всех провайдеров"""
        all_shutdown = True
        for provider in self.providers:
            try:
                if not provider.shutdown():
                    self.logger.warning(f"Provider '{provider.get_name()}' shutdown failed")
                    all_shutdown = False
            except Exception as e:
                self.logger.error(f"Provider '{provider.get_name()}' shutdown error: {e}")
                all_shutdown = False

        return all_shutdown
