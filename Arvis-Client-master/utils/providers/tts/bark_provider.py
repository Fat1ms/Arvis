"""
Bark TTS Provider (Text-to-Speech)
Провайдер для синтеза речи через Bark

Priority: 2 (высокий приоритет, локальный)
Язык документации: Русский + English
"""

from typing import Optional, Generator, Tuple
import numpy as np

from config.config import Config
from utils.logger import ModuleLogger
from utils.providers import TTSProvider, ProviderStatus


class BarkTTSProvider(TTSProvider):
    """
    Провайдер для локального синтеза речи через Bark от Suno AI.
    
    Параметры:
    - use_gpu: Использовать GPU ускорение (default: False)
    - voice_preset: ID голоса для синтеза (например "v2/en_speaker_0")
    - temperature: Температура генерации (0.1-1.0)
    - language: Язык синтеза ("en", "ru", и т.д.)
    
    Требования:
    - bark установлен (pip install bark)
    - Модели загружены (первый запуск загружает ~3 ГБ)
    - GPU рекомендуется (CPU медленный)
    
    Качество: ⭐⭐⭐⭐⭐ Отличное
    Скорость: ⚡ Медленно на CPU, быстро на GPU
    """

    def __init__(
        self,
        config: Config,
        use_gpu: Optional[bool] = None,
        voice_preset: Optional[str] = None,
        temperature: float = 0.7,
        language: str = "ru"
    ):
        """
        Инициализация Bark TTS провайдера.
        
        Args:
            config: Объект конфигурации приложения
            use_gpu: Использовать GPU (если None, берётся из config)
            voice_preset: ID голоса (если None, выбирается автоматически)
            temperature: Температура (0.1-1.0)
            language: Язык синтеза ("en", "ru", etc.)
        """
        super().__init__("bark")
        self.config = config
        self.language = language
        self.temperature = temperature
        
        # Загрузить конфиг Bark если есть
        bark_cfg = config.get("tts.bark_config", {})
        
        self.use_gpu = use_gpu if use_gpu is not None else bark_cfg.get("use_gpu", False)
        self.voice_preset = voice_preset or bark_cfg.get("voice_preset", "v2/en_speaker_0")
        self.use_small_model = bark_cfg.get("use_small_model", False)
        
        self.bark_module = None
        self.sample_rate = 24000  # Bark стандартная частота дискретизации
        self._initialized = False
        
        self.logger.info(f"🎤 Bark TTS Provider initialized (gpu={self.use_gpu}, lang={language})")

    def get_priority(self) -> int:
        """
        Приоритет провайдера.
        Bark - локальный TTS, высокий приоритет.
        """
        return 2

    def initialize(self) -> bool:
        """
        Инициализировать Bark TTS провайдер.
        
        Требует:
        - bark установлен
        - Модели загружены (первый раз долгий процесс)
        
        Returns:
            True если инициализация успешна, иначе False
        """
        try:
            if self._initialized:
                return self.is_available()

            self.logger.info("🚀 Initializing Bark TTS...")

            # Импортировать Bark
            try:
                from bark import SAMPLE_RATE, preload_models, generate_audio
                self.logger.info("📦 Bark module imported successfully")
            except ImportError:
                self.logger.error("❌ Bark not installed. Install: pip install bark")
                self._status.value = "unavailable"
                return False

            # Сохранить ссылки на функции
            self.SAMPLE_RATE = SAMPLE_RATE
            self.preload_models = preload_models
            self.generate_audio = generate_audio
            self.sample_rate = SAMPLE_RATE

            # Предзагрузить модели (долго на первый раз!)
            self.logger.info("⏳ Preloading Bark models (this may take a minute)...")
            try:
                self.preload_models()
                self.logger.info("✅ Bark models loaded successfully")
            except Exception as e:
                self.logger.error(f"❌ Failed to preload models: {e}")
                self._status.value = "unavailable"
                return False

            # Проверить GPU если требуется
            if self.use_gpu:
                try:
                    import torch
                    if not torch.cuda.is_available():
                        self.logger.warning("⚠️ GPU requested but not available, falling back to CPU")
                        self.use_gpu = False
                    else:
                        self.logger.info(f"✓ GPU available: {torch.cuda.get_device_name(0)}")
                except ImportError:
                    self.logger.warning("⚠️ torch not found, GPU acceleration disabled")
                    self.use_gpu = False

            self._initialized = True
            self._status.value = "available"
            self.logger.info("✅ Bark TTS initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"❌ Failed to initialize Bark TTS: {e}")
            self.set_error(str(e))
            self._status.value = "error"
            return False

    def is_available(self) -> bool:
        """
        Проверить доступность Bark TTS провайдера.
        
        Returns:
            True если провайдер готов к работе, иначе False
        """
        try:
            if not self._initialized:
                return False

            # Проверить что Bark загружен
            return self.generate_audio is not None

        except Exception as e:
            self.logger.debug(f"Bark availability check failed: {e}")
            return False

    def synthesize(
        self,
        text: str,
        language: Optional[str] = None,
        voice_preset: Optional[str] = None,
        temperature: Optional[float] = None,
        use_small_model: Optional[bool] = None,
    ) -> np.ndarray:
        """
        Синтезировать речь из текста.
        
        Args:
            text: Текст для синтеза
            language: Язык (default из конструктора)
            voice_preset: ID голоса (например "v2/en_speaker_0")
            temperature: Температура (0.1-1.0)
            use_small_model: Использовать малую модель (быстрее, ниже качество)
            
        Returns:
            NumPy array с аудио (16 bit, mono, 24000 Hz)
            
        Raises:
            RuntimeError: Если провайдер недоступен
        """
        if not self.is_available():
            raise RuntimeError("Bark TTS is not available")

        try:
            lang = language or self.language
            voice = voice_preset or self.voice_preset
            temp = temperature if temperature is not None else self.temperature
            small_model = use_small_model if use_small_model is not None else self.use_small_model

            # Подготовить входные данные для Bark
            # Bark ожидает специальный формат для многоязычности
            if lang == "ru":
                # Для русского - необходимо явно указать
                formatted_text = f"[{lang}] {text}"
            else:
                formatted_text = text

            self.logger.debug(f"🎤 Synthesizing: {text[:50]}...")

            # Синтезировать аудио
            audio_array = self.generate_audio(
                text=formatted_text,
                history_prompt=voice,
                text_temp=temp,
                waveform_temp=0.7,
                use_small_model=small_model,
            )

            # Bark возвращает float32 в диапазоне [-1.0, 1.0]
            # Конвертировать в int16
            audio_int16 = self._float_to_int16(audio_array)

            self.logger.debug(f"✓ Generated audio: {len(audio_int16)} samples")
            return audio_int16

        except Exception as e:
            self.logger.error(f"❌ Synthesis failed: {e}")
            raise RuntimeError(f"Bark synthesis error: {e}")

    def stream_synthesize(
        self,
        text: str,
        language: Optional[str] = None,
        voice_preset: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> Generator[Tuple[np.ndarray, str], None, None]:
        """
        Синтезировать речь потоком (sentence by sentence).
        
        Разбивает текст на предложения и генерирует каждое отдельно.
        Это позволяет начать воспроизведение раньше, чем весь текст готов.
        
        Args:
            text: Полный текст для синтеза
            language: Язык синтеза
            voice_preset: ID голоса
            temperature: Температура
            
        Yields:
            Tuple[audio_array, label] где label="sentence_1", "sentence_2", etc.
            
        Raises:
            RuntimeError: Если провайдер недоступен
        """
        if not self.is_available():
            raise RuntimeError("Bark TTS is not available")

        try:
            # Разбить текст на предложения
            import re
            sentences = re.split(r'[.!?]+', text)
            sentences = [s.strip() for s in sentences if s.strip()]

            self.logger.info(f"🎤 Streaming synthesis of {len(sentences)} sentences...")

            for i, sentence in enumerate(sentences):
                if not sentence:
                    continue

                # Синтезировать предложение
                audio = self.synthesize(
                    sentence,
                    language=language,
                    voice_preset=voice_preset,
                    temperature=temperature,
                )

                label = f"sentence_{i+1}"
                self.logger.debug(f"✓ Generated {label}: {sentence[:30]}...")
                yield (audio, label)

        except Exception as e:
            self.logger.error(f"❌ Stream synthesis failed: {e}")
            raise RuntimeError(f"Bark stream synthesis error: {e}")

    def adjust_speed(
        self,
        audio: np.ndarray,
        speed_factor: float = 1.0
    ) -> np.ndarray:
        """
        Регулировать скорость аудио (не по смыслу, а физически).
        
        Это меняет длительность без изменения питча.
        
        Args:
            audio: Аудио массив
            speed_factor: Коэффициент скорости (0.5 = медленнее, 2.0 = быстрее)
            
        Returns:
            Модифицированный аудио массив
        """
        if speed_factor == 1.0:
            return audio

        try:
            import librosa
            # Изменить скорость без изменения питча
            adjusted = librosa.effects.time_stretch(audio.astype(float), rate=speed_factor)
            return self._float_to_int16(adjusted)
        except ImportError:
            self.logger.warning("librosa not installed, cannot adjust speed")
            return audio

    def get_available_voices(self, language: str = "ru") -> list[str]:
        """
        Получить доступные голоса для языка.
        
        Args:
            language: Код языка ("ru", "en", etc.)
            
        Returns:
            Список доступных voice presets
        """
        # Bark поддерживает несколько голосов на языке
        voices = []
        for i in range(10):  # Обычно 10 голосов на язык
            voices.append(f"v2/{language}_speaker_{i}")
        return voices

    def shutdown(self) -> bool:
        """
        Завершить работу Bark TTS.
        
        Returns:
            True если успешно, иначе False
        """
        try:
            # Очистить GPU память если используется
            if self.use_gpu:
                try:
                    import torch
                    torch.cuda.empty_cache()
                    self.logger.info("✓ GPU memory cleared")
                except:
                    pass

            self.bark_module = None
            self._initialized = False
            self._status.value = "unavailable"

            self.logger.info("✅ Bark TTS shutdown complete")
            return True

        except Exception as e:
            self.logger.error(f"❌ Bark TTS shutdown failed: {e}")
            return False

    # Вспомогательные методы

    def _float_to_int16(self, audio: np.ndarray) -> np.ndarray:
        """
        Конвертировать аудио из float [-1, 1] в int16 [-32768, 32767].
        
        Args:
            audio: Float аудио массив
            
        Returns:
            Int16 аудио массив
        """
        # Убедиться что float в диапазоне [-1, 1]
        audio = np.clip(audio, -1.0, 1.0)
        # Конвертировать
        audio_int16 = (audio * 32767).astype(np.int16)
        return audio_int16

    def _int16_to_float(self, audio: np.ndarray) -> np.ndarray:
        """
        Конвертировать аудио из int16 в float [-1, 1].
        
        Args:
            audio: Int16 аудио массив
            
        Returns:
            Float аудио массив
        """
        return audio.astype(np.float32) / 32767.0

    def get_model_info(self) -> dict:
        """
        Получить информацию о текущей модели.
        
        Returns:
            Словарь с информацией о модели
        """
        return {
            "name": "Bark TTS",
            "provider": "Suno AI",
            "language": self.language,
            "quality": 5,  # Максимальное качество
            "speed": "slow" if not self.use_gpu else "medium",
            "use_gpu": self.use_gpu,
            "voice_preset": self.voice_preset,
            "sample_rate": self.sample_rate,
            "available": self.is_available(),
            "priority": self.get_priority(),
            "supports": [
                "100+ languages",
                "emotional intonation",
                "sound effects",
                "streaming synthesis"
            ],
        }
