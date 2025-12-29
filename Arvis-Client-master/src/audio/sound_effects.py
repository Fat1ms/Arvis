"""
Sound Effects Manager: управление звуковыми эффектами

Отвечает за:
- Воспроизведение системных звуков (начало/конец записи, уведомления)
- Генерация простых звуков через winsound/beep
- Поддержка отключения звуков через настройки
"""

import platform
from typing import Optional
from PyQt6.QtCore import QThread, pyqtSignal

from utils.logger import ModuleLogger


class SoundEffectPlayer(QThread):
    """Фоновый плеер для звуковых эффектов (чтобы не блокировать UI)."""
    
    finished_signal = pyqtSignal()
    
    def __init__(self, effect_type: str, frequency: int = 800, duration: int = 100):
        super().__init__()
        self.effect_type = effect_type
        self.frequency = frequency
        self.duration = duration
    
    def run(self):
        try:
            if platform.system() == "Windows":
                import winsound
                winsound.Beep(self.frequency, self.duration)
        except Exception:
            pass
        finally:
            self.finished_signal.emit()


class SoundEffects:
    """Менеджер звуковых эффектов."""
    
    def __init__(self, config=None):
        self.config = config
        self.logger = ModuleLogger("SoundEffects")
        self._enabled = True
        self._current_player: Optional[SoundEffectPlayer] = None
        
        # Загружаем настройки
        if config:
            self._enabled = config.get("sound_effects.enabled", True)
    
    def set_enabled(self, enabled: bool):
        """Включить/выключить звуковые эффекты."""
        self._enabled = enabled
        self.logger.info(f"Sound effects {'enabled' if enabled else 'disabled'}")
    
    def is_enabled(self) -> bool:
        """Проверить, включены ли звуки."""
        return self._enabled
    
    def play_start_recording(self):
        """Звук начала записи - высокий короткий тон."""
        if not self._enabled:
            return
        self._play_beep(frequency=880, duration=80)  # A5
    
    def play_stop_recording(self):
        """Звук окончания записи - два коротких тона вниз."""
        if not self._enabled:
            return
        # Один низкий тон
        self._play_beep(frequency=660, duration=80)  # E5
    
    def play_message_sent(self):
        """Звук отправки сообщения - мягкий восходящий тон."""
        if not self._enabled:
            return
        self._play_beep(frequency=523, duration=60)  # C5
    
    def play_message_received(self):
        """Звук получения ответа - два восходящих тона."""
        if not self._enabled:
            return
        self._play_beep(frequency=698, duration=100)  # F5
    
    def play_error(self):
        """Звук ошибки - низкий длинный тон."""
        if not self._enabled:
            return
        self._play_beep(frequency=220, duration=200)  # A3
    
    def play_wake_word_detected(self):
        """Звук при распознавании wake word - короткий высокий чирп."""
        if not self._enabled:
            return
        self._play_beep(frequency=1047, duration=50)  # C6
    
    def play_notification(self):
        """Звук уведомления."""
        if not self._enabled:
            return
        self._play_beep(frequency=784, duration=100)  # G5
    
    def _play_beep(self, frequency: int, duration: int):
        """Воспроизвести beep в фоновом потоке."""
        try:
            if platform.system() != "Windows":
                return
            
            # Очищаем предыдущий плеер если есть
            if self._current_player and self._current_player.isRunning():
                self._current_player.wait(100)
            
            self._current_player = SoundEffectPlayer(
                effect_type="beep",
                frequency=frequency,
                duration=duration
            )
            self._current_player.start()
        except Exception as e:
            self.logger.debug(f"Could not play sound: {e}")


# Глобальный экземпляр для удобства
_sound_effects: Optional[SoundEffects] = None


def get_sound_effects(config=None) -> SoundEffects:
    """Получить глобальный менеджер звуковых эффектов."""
    global _sound_effects
    if _sound_effects is None:
        _sound_effects = SoundEffects(config)
    return _sound_effects


def init_sound_effects(config) -> SoundEffects:
    """Инициализировать менеджер звуковых эффектов с конфигом."""
    global _sound_effects
    _sound_effects = SoundEffects(config)
    return _sound_effects
