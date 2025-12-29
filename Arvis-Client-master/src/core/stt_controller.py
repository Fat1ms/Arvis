"""
STT Controller: управление записью голоса и обработкой ввода

Отвечает за:
- Запуск/остановка записи (с отслеживанием источника: пользователь или wake word)
- Обработку распознанного текста
- Проверку name-only вызовов (когда произнесено только имя ассистента)
- Перезапуск слежения за wake word после обработки

Дизайн:
- Принимает ссылку на ArvisCore-like объект
- Работает с config, stt_engine, wake_controller
- Эмитирует события через core.voice_message_recognized
- Сохраняет 1:1 поведение оригинальной реализации
"""

import re
import time
from typing import Any, Optional

from PyQt6.QtCore import QTimer

from utils.logger import ModuleLogger
from src.audio.sound_effects import get_sound_effects


class STTController:
    """Контроллер для управления записью голоса и обработкой ввода."""

    def __init__(self, core: Any):
        """
        Инициализация контроллера.

        Args:
            core: ArvisCore-like объект с доступом к config, stt_engine, wake_controller,
                  и методам process_message, error_occurred, voice_message_recognized.
        """
        self.core = core
        self.config = core.config
        self.logger = ModuleLogger("STTController")
        self._recording_source = "none"

    def start_recording(self, source: str = "user") -> None:
        """Начать запись голоса.

        Args:
            source: Источник запроса ('user' для кнопки, 'wake' для ключевого слова).
        """
        if not getattr(self.core, "stt_engine", None):
            self.logger.error("STT engine not initialized")
            try:
                self.core.error_occurred.emit("STT движок не инициализирован")
            except Exception:
                pass
            return

        try:
            self.logger.info(f"Starting voice recording (source: {source})")

            # Если wake listening активен, остановим его перед захватом микрофона
            try:
                if source == "user" and getattr(self.core, "stt_engine", None):
                    if getattr(self.core.stt_engine, "is_listening_for_wake_word", False):
                        self.core.stt_engine.stop_wake_word_detection()
            except Exception:
                pass

            ok = bool(self.core.stt_engine.start_recording())
            if not ok:
                self.core.is_voice_recording = False
                self._recording_source = "none"
                self.logger.warning("Voice recording not started (audio unavailable)")
                try:
                    self.core.status_changed.emit({"is_recording": False, "recording_by_user": False})
                except Exception:
                    pass
                try:
                    reason = getattr(self.core.stt_engine, "last_audio_error", None)
                    if isinstance(reason, str):
                        reason = reason.strip()
                    else:
                        reason = ""

                    if reason:
                        reason_l = reason.lower()
                        if "pyaudio" in reason_l or "no module named" in reason_l or "not installed" in reason_l:
                            self.core.error_occurred.emit("❌ Микрофон недоступен. Установите PyAudio (pyaudio)")
                        else:
                            self.core.error_occurred.emit(f"❌ Микрофон недоступен: {reason}")
                    else:
                        self.core.error_occurred.emit("❌ Микрофон недоступен. Проверьте устройство микрофона и права доступа.")
                except Exception:
                    pass
                return

            self.core.is_voice_recording = True
            self._recording_source = "user" if source == "user" else "wake"
            self.logger.info("Voice recording started")
            
            # Воспроизводим звук начала записи
            try:
                get_sound_effects().play_start_recording()
            except Exception:
                pass
            
            # Обновляем статус
            try:
                self.core.status_changed.emit({
                    "is_recording": True,
                    "recording_by_user": self._recording_source == "user"
                })
            except Exception:
                pass
        except Exception as e:
            self.logger.error(f"Failed to start recording: {e}")
            try:
                self.core.error_occurred.emit(f"Ошибка при запуске записи: {e}")
            except Exception:
                pass

    def stop_recording(self) -> None:
        """Остановить запись голоса."""
        if not getattr(self.core, "stt_engine", None):
            return

        try:
            self.logger.info("Stopping voice recording")
            self.core.stt_engine.stop_recording()
            self.core.is_voice_recording = False
            self._recording_source = "none"
            self.logger.info("Voice recording stopped")
            
            # Воспроизводим звук окончания записи
            try:
                get_sound_effects().play_stop_recording()
            except Exception:
                pass
        except Exception as e:
            self.logger.error(f"Failed to stop recording: {e}")

    def toggle_recording(self, source: str = "user") -> None:
        """Переключить состояние записи (для обратной совместимости с UI)."""
        if self.core.is_voice_recording:
            self.stop_recording()
        else:
            self.start_recording(source=source)

    def process_voice_input(self, text: str) -> None:
        """Обработать распознанный голосовой ввод.

        Args:
            text: Распознанный текст от STT.
        """
        self.logger.info(f"Voice input recognized: '{text}'")

        # Останавливаем запись
        try:
            if getattr(self.core, "stt_engine", None) and self.core.is_voice_recording:
                self.core.stt_engine.stop_recording()
                self.core.is_voice_recording = False
        except Exception:
            pass

        # Обработка пустого ввода (пользователь молчал)
        if not text.strip():
            self.logger.info("No speech detected from user")
            # В Live Mode перезапускаем запись, иначе wake word
            if getattr(self.core, "live_mode", False):
                self.logger.info("Live Mode active: restarting recording after silence")
                QTimer.singleShot(300, lambda: self._restart_recording_if_live())
            else:
                self.logger.info("Restarting wake word detection after silence")
                QTimer.singleShot(300, lambda: self._restart_wake_if_enabled())
            return

        # Проверяем, не является ли текст просто именем ассистента
        if self._check_if_name_only(text):
            self.logger.info("Detected name-only call, responding...")
            if getattr(self.core, "wake_controller", None):
                self.core.wake_controller.respond_to_name_only()
            return

        # Эмитируем сигнал для добавления сообщения пользователя в UI и обрабатываем
        try:
            self.core.voice_message_recognized.emit(text)
        except Exception:
            pass

        # Обрабатываем сообщение через основной pipeline
        if hasattr(self.core, "process_message"):
            self.core.process_message(text)

        # После обработки: в Live Mode ждём TTS, иначе перезапускаем wake word
        # В Live Mode TTSController автоматически запустит запись после TTS
        if not getattr(self.core, "live_mode", False):
            QTimer.singleShot(600, lambda: self._restart_wake_if_enabled())

    def _check_if_name_only(self, text: str) -> bool:
        """Проверить, содержит ли текст только имя ассистента (без команды).

        Args:
            text: Текст для проверки.

        Returns:
            True, если текст содержит только имя ассистента.
        """
        try:
            wake_word = str(self.config.get("stt.wake_word", "арвис")).lower()
            # Варианты распознавания имени
            wake_variants = [wake_word, "джарвис", "арвіс", "jarvis"]
            text_lower = text.lower().strip()

            # Убираем пробелы, знаки препинания и т.д.
            text_clean = re.sub(r"[^\w]", "", text_lower).lower()

            self.logger.debug(f"Comparing: '{text_lower}' (clean: '{text_clean}') with wake variants")

            # Проверяем все варианты
            for variant in wake_variants:
                if text_lower == variant or text_clean == re.sub(r"[^\w]", "", variant).lower():
                    return True

            return False
        except Exception as e:
            self.logger.error(f"Error checking wake word: {e}")
            return False

    def _restart_wake_if_enabled(self) -> None:
        """Перезапуск слежения за wake word, если включено в настройках."""
        try:
            # Не запускаем wake word в Live Mode
            if getattr(self.core, "live_mode", False):
                self.logger.debug("Live Mode active: skipping wake word restart")
                return
                
            if not bool(self.config.get("modules.voice_activation_enabled", False)):
                return

            # Не запускаем, если уже идёт запись
            if self.core.is_voice_recording:
                return

            if getattr(self.core, "wake_controller", None):
                self.core.wake_controller.restart_wake_listening_if_enabled()
        except Exception as e:
            self.logger.debug(f"Error restarting wake word detection: {e}")
    
    def _restart_recording_if_live(self) -> None:
        """Перезапуск записи в Live Mode после обработки."""
        try:
            # Проверяем, что Live Mode всё ещё активен
            if not getattr(self.core, "live_mode", False):
                self.logger.debug("Live Mode was disabled, not restarting recording")
                return
            
            # Не запускаем, если уже идёт запись
            if self.core.is_voice_recording:
                self.logger.debug("Recording already active")
                return
            
            self.logger.info("Live Mode: Restarting recording")
            self.start_recording(source="live")
        except Exception as e:
            self.logger.error(f"Error restarting Live Mode recording: {e}")

    @property
    def is_recording(self) -> bool:
        """Проверить, идёт ли в данный момент запись."""
        return getattr(self.core, "is_voice_recording", False)

    @property
    def recording_source(self) -> str:
        """Получить источник текущей записи."""
        return self._recording_source
