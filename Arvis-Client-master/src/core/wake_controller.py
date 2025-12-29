"""
Wake Word Controller: управление активацией и реагирование на ключевое слово

Отвечает за:
- Настройку детектирования wake word (Vosk или внешний Kaldi)
- Обработку события активации (с защитой от ложных срабатываний)
- Ответ на name-only вызовы (когда произнесено только имя ассистента)
- Перезапуск прослушивания после обработки сообщения

Дизайн:
- Принимает ссылку на ArvisCore-like объект (или набор зависимостей)
- Работает с config, stt_engine, wake_word_detector, tts_engine/tts_controller
- Эмитирует события через PyQt сигналы (если доступны в core)
- Сохраняет 1:1 поведение оригинальной реализации
"""

import re
import time
import random
from typing import Any, List, Optional

from PyQt6.QtCore import QTimer

from utils.logger import ModuleLogger


class WakeController:
    """Контроллер для управления активацией и обработкой wake word."""

    def __init__(self, core: Any):
        """
        Инициализация контроллера.

        Args:
            core: ArvisCore-like объект с доступом к config, stt_engine, wake_word_detector,
                  tts_engine, tts_controller и методам toggle_voice_recording, error_occurred и т.д.
        """
        self.core = core
        self.config = core.config
        self.logger = ModuleLogger("WakeController")
        self._last_wake_ts = 0.0

    def configure_voice_activation(self) -> None:
        """Запустить или остановить слежение за ключевым словом на основе настроек."""
        try:
            enabled = bool(self.config.get("modules.voice_activation_enabled", False))
        except Exception:
            enabled = False

        try:
            # Получаем текущий движок для распознавания wake word
            wake_word_engine = str(self.config.get("stt.wake_word_engine", "vosk") or "vosk").lower()
            if wake_word_engine == "porcupine":
                wake_word_engine = "vosk"

            # Если используем внешний движок wake word (Kaldi)
            if wake_word_engine == "kaldi" and getattr(self.core, "wake_word_detector", None):
                engine_label = "Kaldi"

                if enabled:
                    if self.core.wake_word_detector.is_ready():
                        self.core.wake_word_detector.start_detection()
                        self.logger.info(f"{engine_label} wake word detection enabled")
                    else:
                        self.logger.warning(f"{engine_label} wake word detector not ready")
                else:
                    self.core.wake_word_detector.stop_detection()
                    self.logger.info(f"{engine_label} wake word detection disabled")

            # Если используем встроенный в Vosk
            elif getattr(self.core, "stt_engine", None) and self.core.stt_engine.is_ready():
                if enabled:
                    # Запускаем прослушивание wake word через Vosk
                    started = bool(self.core.stt_engine.start_wake_word_detection())
                    if started:
                        self.logger.info("Vosk wake word detection enabled")
                    else:
                        if getattr(self.core.stt_engine, "is_listening_for_wake_word", False):
                            self.logger.debug("Vosk wake word detection already active")
                        elif getattr(self.core.stt_engine, "is_recording", False):
                            self.logger.warning("Vosk wake word detection not started: recording is active")
                        else:
                            reason = getattr(self.core.stt_engine, "last_audio_error", None)
                            if isinstance(reason, str) and reason.strip():
                                self.logger.warning(f"Vosk wake word detection not started: {reason}")
                            else:
                                self.logger.warning("Vosk wake word detection not started (audio unavailable)")
                else:
                    # Отключаем если было включено
                    self.core.stt_engine.stop_wake_word_detection()
                    self.logger.info("Vosk wake word detection disabled")
            else:
                self.logger.warning("No suitable wake word detector available")

        except Exception as e:
            self.logger.debug(f"Voice activation config error: {e}")

    def on_wake_word_detected(self) -> None:
        """Обработка события активации голосом с защитами от ложных срабатываний."""
        try:
            now = time.time()
            # Кулдаун 2 секунды между активациями
            if now - self._last_wake_ts < 2.0:
                self.logger.debug("Wake ignored: cooldown active")
                return
            self._last_wake_ts = now

            # Не активируемся во время проигрывания TTS или активной обработки
            if getattr(self.core, "_is_tts_playing", False) or getattr(self.core, "is_processing", False):
                self.logger.debug("Wake ignored: TTS playing or processing in progress")
                return

            self.logger.info("Wake word detected, preparing acknowledgement")

            # ОСТАНАВЛИВАЕМ СЛЕЖЕНИЕ ЗА WAKE WORD ПЕРЕД ОТВЕТОМ
            try:
                # Определяем текущий движок wake word
                wake_word_engine = str(self.config.get("stt.wake_word_engine", "vosk") or "vosk").lower()
                if wake_word_engine == "porcupine":
                    wake_word_engine = "vosk"

                if wake_word_engine == "kaldi" and getattr(self.core, "wake_word_detector", None):
                    self.core.wake_word_detector.stop_detection()
                    self.logger.debug("Kaldi wake word detection stopped before TTS")
                elif getattr(self.core, "stt_engine", None):
                    self.core.stt_engine.stop_wake_word_detection()
                    self.logger.debug("Vosk wake word detection stopped before TTS")
            except Exception as e:
                self.logger.debug(f"Error stopping wake word detection: {e}")

            # Сообщаем UI о триггере (можно подсветить микрофон)
            try:
                if hasattr(self.core, "voice_activation_detected"):
                    self.core.voice_activation_detected.emit()
            except Exception:
                pass

            # Произнесём короткую фразу подтверждения, затем начнём запись
            ack = str(self.config.get("voice.wake_ack", "Слушаю"))
            self._speak_and_start_recording_after_tts(ack)
        except Exception as e:
            self.logger.debug(f"Wake handler error: {e}")

    def restart_wake_listening_if_enabled(self) -> None:
        """Перезапуск слежения за wake word, если включено в настройках."""
        try:
            if not bool(self.config.get("modules.voice_activation_enabled", False)):
                return

            # Не запускаем, если уже идёт запись
            if getattr(self.core, "is_voice_recording", False):
                return

            # Определяем текущий движок wake word
            wake_word_engine = str(self.config.get("stt.wake_word_engine", "vosk") or "vosk").lower()
            if wake_word_engine == "porcupine":
                wake_word_engine = "vosk"

            # Запускаем соответствующий детектор
            if wake_word_engine == "kaldi" and getattr(self.core, "wake_word_detector", None):
                self.logger.debug("Restarting Kaldi wake word detection")
                self.core.wake_word_detector.start_detection()
            elif getattr(self.core, "stt_engine", None):
                self.logger.debug("Restarting Vosk wake word detection")
                started = bool(self.core.stt_engine.start_wake_word_detection())
                if not started:
                    if getattr(self.core.stt_engine, "is_listening_for_wake_word", False):
                        self.logger.debug("Vosk wake word restart skipped: already active")
                    elif getattr(self.core.stt_engine, "is_recording", False):
                        self.logger.warning("Vosk wake word restart skipped: recording is active")
                    else:
                        reason = getattr(self.core.stt_engine, "last_audio_error", None)
                        if isinstance(reason, str) and reason.strip():
                            self.logger.warning(f"Vosk wake word restart skipped: {reason}")
                        else:
                            self.logger.warning("Vosk wake word restart skipped (audio unavailable)")

        except Exception as e:
            self.logger.debug(f"Error restarting wake word detection: {e}")

    def respond_to_name_only(self) -> None:
        """Ответить на обращение только по имени и продолжить слушать."""
        try:
            phrases = self._collect_ack_phrases()
            if not phrases:
                phrases = ["Да?", "Слушаю вас", "Чем могу помочь?"]

            # Проверяем кэш готовых фраз
            preloaded_cache = getattr(self.core, "_preloaded_ack_cache", {})
            cached_options = [p for p in phrases if len(preloaded_cache.get(p, [])) > 0]

            if cached_options:
                response = random.choice(cached_options)
            else:
                response = random.choice(phrases)

            # Говорим короткую фразу и начинаем слушать снова
            self.logger.info(f"Will respond with phrase: '{response}'")
            self._speak_and_start_recording_after_tts(response)
            self.logger.info(f"Responded to name-only call with: {response}")

        except Exception as e:
            self.logger.error(f"Error responding to name only: {e}")
            # При ошибке пытаемся просто начать слушать
            if hasattr(self.core, "toggle_voice_recording"):
                self.core.toggle_voice_recording(source="wake")

    def _collect_ack_phrases(self) -> List[str]:
        """Собрать список коротких фраз подтверждения для быстрой реакции."""
        phrases: List[str] = []
        try:
            ack_phrase = str(self.config.get("voice.wake_ack", "Слушаю") or "").strip()
        except Exception:
            ack_phrase = "Слушаю"
        if ack_phrase:
            phrases.append(ack_phrase)

        default_responses = ["Да?", "Слушаю вас", "Чем могу помочь?"]
        try:
            raw_responses_cfg = self.config.get("voice.name_responses", default_responses)
        except Exception:
            raw_responses_cfg = default_responses

        if isinstance(raw_responses_cfg, (list, tuple)):
            responses_iter = [str(item) for item in raw_responses_cfg]
        elif isinstance(raw_responses_cfg, str):
            responses_iter = [seg.strip() for seg in raw_responses_cfg.split(",") if seg.strip()]
        else:
            responses_iter = default_responses

        for item in responses_iter:
            phrase = str(item or "").strip()
            if phrase and phrase not in phrases:
                phrases.append(phrase)

        return phrases

    def _speak_and_start_recording_after_tts(self, text: str) -> None:
        """Speak a phrase and start recording after TTS finishes."""
        if not getattr(self.core, "tts_engine", None):
            if hasattr(self.core, "toggle_voice_recording"):
                self.core.toggle_voice_recording(source="wake")
            return

        # Disconnect any previous connection to avoid multiple triggers
        try:
            self.core.tts_engine.playback_finished.disconnect(self._start_recording_post_tts)
        except TypeError:
            pass  # Signal was not connected

        self.core.tts_engine.playback_finished.connect(self._start_recording_post_tts)
        self.core.tts_engine.speak(text)

    def _start_recording_post_tts(self) -> None:
        """Slot to start recording, called after TTS playback."""
        # Disconnect immediately to prevent it from running on subsequent playbacks
        if getattr(self.core, "tts_engine", None):
            try:
                self.core.tts_engine.playback_finished.disconnect(self._start_recording_post_tts)
            except TypeError:
                pass

        # Use a short delay to ensure audio system has released the output channel
        QTimer.singleShot(150, lambda: self._safe_start_recording())

    def _safe_start_recording(self) -> None:
        """Safely start recording after TTS playback."""
        try:
            if hasattr(self.core, "toggle_voice_recording"):
                self.core.toggle_voice_recording(source="wake")
        except Exception as e:
            self.logger.debug(f"Error starting recording after TTS: {e}")
