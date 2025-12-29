"""
Local TTS Provider (Silero)
Локальный провайдер Text-to-Speech на основе Silero

Priority: 0 (максимальный приоритет для локальных компонентов)
"""

from typing import Optional

from config.config import Config
from modules.tts_engine import TTSEngine
from utils.logger import ModuleLogger
from utils.providers import TTSProvider


class SileroTTSProvider(TTSProvider):
    """
    Провайдер для локального синтеза речи через Silero.
    
    Требует:
    - PyTorch для Silero модели
    - Примерно 500MB для скачивания модели с Hugging Face
    """

    def __init__(self, config: Config):
        super().__init__("silero")
        self.config = config
        self.tts_engine: Optional[TTSEngine] = None
        self._initialized = False

    def get_priority(self) -> int:
        """Локальные компоненты имеют максимальный приоритет"""
        return 0

    def initialize(self) -> bool:
        """Инициализировать Silero TTS"""
        try:
            if self._initialized:
                return self.is_available()

            self.logger.info("Initializing Silero TTS engine...")
            self.tts_engine = TTSEngine(self.config)

            if not self.tts_engine:
                self.logger.error("Failed to create TTS engine")
                self._status.value = "unavailable"
                return False

            self._initialized = True
            self._status.value = "available"
            self.logger.info("✓ Silero TTS initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize Silero TTS: {e}")
            self.set_error(str(e))
            return False

    def is_available(self) -> bool:
        """Проверить доступность Silero TTS"""
        try:
            if not self._initialized:
                return False

            if self.tts_engine is None:
                return False

            # Дополнительная проверка
            return self.config.get("tts.engine") == "silero" or self.config.get("tts.enabled", True)

        except Exception as e:
            self.logger.debug(f"Silero availability check failed: {e}")
            return False

    def synthesize(self, text: str, language: Optional[str] = None) -> bytes:
        """
        Синтезировать речь из текста.
        
        Args:
            text: Текст для синтеза
            language: Язык (ru, en, etc). Если None - использовать из конфига
            
        Returns:
            Аудиоданные в байтах (WAV)
        """
        if not self.is_available():
            raise RuntimeError("Silero TTS is not available")

        try:
            if self.tts_engine is None:
                raise RuntimeError("TTS engine not initialized")

            # Используем встроенный метод TTS engine для синтеза
            # Возвращает путь к файлу или аудиоданные
            audio_path = self.tts_engine.synthesize(text)

            # Читаем аудиофайл
            if isinstance(audio_path, str):
                with open(audio_path, "rb") as f:
                    return f.read()
            else:
                # Если это уже байты
                return audio_path

        except Exception as e:
            self.logger.error(f"Silero synthesis failed: {e}")
            raise RuntimeError(f"Silero synthesis error: {e}")

    def stream_synthesize(self, text: str, language: Optional[str] = None):
        """
        Синтезировать речь потоком (для real-time).
        
        Args:
            text: Текст для синтеза
            language: Язык
            
        Yields:
            Чанки аудиоданных
        """
        if not self.is_available():
            raise RuntimeError("Silero TTS is not available")

        try:
            if self.tts_engine is None:
                raise RuntimeError("TTS engine not initialized")

            # Для потокового синтеза используем встроенный метод
            for chunk in self.tts_engine.synthesize_stream(text):
                yield chunk

        except Exception as e:
            self.logger.error(f"Silero stream synthesis failed: {e}")
            raise RuntimeError(f"Silero stream synthesis error: {e}")

    def shutdown(self) -> bool:
        """Завершить работу Silero TTS"""
        try:
            if self.tts_engine:
                self.tts_engine.stop()
                self.tts_engine = None

            self._initialized = False
            self._status.value = "unavailable"
            self.logger.info("✓ Silero TTS shutdown complete")
            return True

        except Exception as e:
            self.logger.error(f"Silero TTS shutdown failed: {e}")
            return False
