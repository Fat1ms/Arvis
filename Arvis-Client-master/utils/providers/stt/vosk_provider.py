"""
Local STT Provider (Vosk)
Локальный провайдер Speech-to-Text на основе Vosk

Priority: 0 (максимальный приоритет для локальных компонентов)
"""

from typing import Optional

from config.config import Config
from modules.stt_engine import STTEngine
from utils.logger import ModuleLogger
from utils.providers import STTProvider


class VoskSTTProvider(STTProvider):
    """
    Провайдер для локального распознавания речи через Vosk.
    
    Требует:
    - Vosk моделей в папке models/
    - PyAudio для захвата аудио
    """

    def __init__(self, config: Config):
        super().__init__("vosk")
        self.config = config
        self.stt_engine: Optional[STTEngine] = None
        self._initialized = False

    def get_priority(self) -> int:
        """Локальные компоненты имеют максимальный приоритет"""
        return 0

    def initialize(self) -> bool:
        """Инициализировать Vosk STT"""
        try:
            if self._initialized:
                return self.is_available()

            self.logger.info("Initializing Vosk STT engine...")
            self.stt_engine = STTEngine(self.config)

            if not self.stt_engine:
                self.logger.error("Failed to create STT engine")
                self._status.value = "unavailable"
                return False

            self._initialized = True
            self._status.value = "available"
            self.logger.info("✓ Vosk STT initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize Vosk STT: {e}")
            self.set_error(str(e))
            return False

    def is_available(self) -> bool:
        """Проверить доступность Vosk STT"""
        try:
            if not self._initialized:
                return False

            if self.stt_engine is None:
                return False

            # Дополнительная проверка
            return self.config.get("stt.engine") == "vosk"

        except Exception as e:
            self.logger.debug(f"Vosk availability check failed: {e}")
            return False

    def recognize(self, audio: bytes, language: Optional[str] = None) -> str:
        """
        Распознать речь из аудиобайтов.
        
        Args:
            audio: Аудиоданные в байтах (WAV или RAW PCM)
            language: Игнорируется для Vosk (используется модель из конфига)
            
        Returns:
            Распознанный текст
        """
        if not self.is_available():
            raise RuntimeError("Vosk STT is not available")

        try:
            # Vosk работает через микрофон, не через буфер
            # Для прямого распознавания нужно использовать stream_recognize
            raise NotImplementedError("Use stream_recognize for Vosk STT")

        except Exception as e:
            self.logger.error(f"Vosk recognition failed: {e}")
            raise RuntimeError(f"Vosk recognition error: {e}")

    def stream_recognize(self, audio_stream) -> str:
        """
        Распознать речь из потока.
        
        Args:
            audio_stream: Поток аудиоданных или микрофонный поток
            
        Returns:
            Распознанный текст
        """
        if not self.is_available():
            raise RuntimeError("Vosk STT is not available")

        try:
            if self.stt_engine is None:
                raise RuntimeError("STT engine not initialized")

            # Используем встроенный метод STT engine
            # Это будет работать с микрофоном
            result = self.stt_engine.recognize()
            return result

        except Exception as e:
            self.logger.error(f"Vosk stream recognition failed: {e}")
            raise RuntimeError(f"Vosk stream recognition error: {e}")

    def shutdown(self) -> bool:
        """Завершить работу Vosk STT"""
        try:
            if self.stt_engine:
                self.stt_engine.stop()
                self.stt_engine = None

            self._initialized = False
            self._status.value = "unavailable"
            self.logger.info("✓ Vosk STT shutdown complete")
            return True

        except Exception as e:
            self.logger.error(f"Vosk STT shutdown failed: {e}")
            return False
