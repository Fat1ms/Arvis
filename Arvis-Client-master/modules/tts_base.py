"""
Base class for TTS engines
Базовый класс для всех TTS engine'ов с абстрактными методами
"""

from abc import ABCMeta, abstractmethod
from enum import Enum
from typing import Callable, Dict, Any, Optional, List
from dataclasses import dataclass
from PyQt6.QtCore import QObject, pyqtSignal


class TTSStatus(Enum):
    """Статус TTS engine"""
    IDLE = "idle"
    INITIALIZING = "initializing"
    READY = "ready"
    SPEAKING = "speaking"
    ERROR = "error"


@dataclass
class HealthCheckResult:
    """Результат health check"""
    healthy: bool
    message: str
    details: Optional[Dict[str, Any]] = None


# Создаём совместимый метакласс для QObject + ABC
class QObjectABCMeta(ABCMeta, type(QObject)):
    """Метакласс, совместимый с QObject и ABC"""
    pass


class TTSEngineBase(QObject, metaclass=QObjectABCMeta):
    """
    Абстрактный базовый класс для всех TTS engine'ов.
    
    Все TTS engine'ы должны наследоваться от этого класса и реализовать
    методы speak(), speak_streaming(), stop(), get_status()
    """
    # Унифицированный сигнал окончания воспроизведения для всех реализаций
    playback_finished = pyqtSignal()

    def __init__(self, config, logger):
        """
        Инициализация TTS engine.
        
        Args:
            config: Config объект
            logger: Logger экземпляр
        """
        super().__init__()
        self.config = config
        self.logger = logger
        self.status = TTSStatus.IDLE
        self.engine_name = "base"
    
    @abstractmethod
    def speak(self, text: str, stream: bool = False) -> bool:
        """
        Синтезировать и воспроизвести текст.
        
        Args:
            text: Текст для синтеза
            stream: Если True, стриминг аудио в реальном времени
        
        Returns:
            True если успешно, False в противном случае
        """
        pass
    
    @abstractmethod
    def speak_streaming(self, text: str, chunk_callback: Callable[[bytes], None]) -> bool:
        """
        Потоковый синтез с callback'ом для аудио чанков.
        
        Args:
            text: Текст для синтеза
            chunk_callback: Функция, вызываемая с каждым аудио чанком (PCM bytes)
        
        Returns:
            True если успешно, False в противном случае
        """
        pass

    @abstractmethod
    def save_to_file(self, text: str, output_path: str) -> bool:
        """
        Синтезировать текст и сохранить в файл.
        
        Args:
            text: Текст для синтеза
            output_path: Путь к выходному файлу (wav)
            
        Returns:
            True если успешно, False в противном случае
        """
        pass
    
    @abstractmethod
    def stop(self) -> None:
        """Остановить воспроизведение"""
        pass
    
    def get_status(self) -> Dict[str, Any]:
        """
        Получить статус engine'а.
        
        Returns:
            Dict с engine, status, ready полями
        """
        return {
            "engine": self.engine_name,
            "status": self.status.value,
            "ready": self.status == TTSStatus.READY
        }

    # Единая точка проверки готовности (можно переопределять)
    def is_ready(self) -> bool:
        """Готовность TTS по умолчанию по статусу."""
        try:
            return self.status in (TTSStatus.READY, TTSStatus.SPEAKING)
        except Exception:
            return False
    
    def health_check(self) -> HealthCheckResult:
        """
        Проверка здоровья engine'а.
        
        Returns:
            HealthCheckResult с healthy, message, details
        """
        is_healthy = self.status in [TTSStatus.READY, TTSStatus.SPEAKING]
        return HealthCheckResult(
            healthy=is_healthy,
            message=f"TTS engine status: {self.status.value}",
            details=self.get_status()
        )

    def set_mode(self, mode: str) -> None:
        """Set TTS mode (optional, override in subclasses)
        
        Args:
            mode: Mode name
        """
        pass

    def set_enabled(self, enabled: bool) -> None:
        """Enable/disable TTS (optional, override in subclasses)
        
        Args:
            enabled: True to enable, False to disable
        """
        pass

    # Опциональный API: предзагрузка озвучек коротких фраз (для wake-ack кеша)
    def preload_phrases(self, phrases: List[str], limit: int = 1) -> Dict[str, Any]:
        """Предзагрузка коротких фраз. Базовая реализация возвращает пусто.

        Args:
            phrases: список фраз
            limit: желаемое количество вариантов на фразу

        Returns:
            Dict[str, Any] описание предзагруженных ресурсов (реализация-заглушка).
        """
        return {}
