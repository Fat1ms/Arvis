"""
TTS Controller: минимальная обвязка вокруг TTS для Live Mode

Отвечает за подписку на единый сигнал playback_finished у текущего TTS-движка
и мягкий запуск записи (через переданный callback) при активном Live Mode.
"""

from typing import Callable, Optional

from PyQt6.QtCore import QObject, QTimer

from modules.tts_base import TTSEngineBase
from utils.logger import ModuleLogger


class TTSController(QObject):
    def __init__(
        self,
        logger: Optional[ModuleLogger] = None,
        start_recording_cb: Optional[Callable[[], None]] = None,
    ) -> None:
        super().__init__()
        self.logger = logger or ModuleLogger("TTSController")
        self._engine: Optional[TTSEngineBase] = None
        self._live_enabled: bool = False
        self._start_recording_cb = start_recording_cb

    def attach_engine(self, engine: Optional[TTSEngineBase]) -> None:
        """Подключить/переключить текущий TTS engine."""
        try:
            if self._engine and hasattr(self._engine, "playback_finished"):
                try:
                    self._engine.playback_finished.disconnect(self._on_playback_finished)
                except Exception:
                    pass
        except Exception:
            pass

        self._engine = engine

        if self._engine and hasattr(self._engine, "playback_finished"):
            try:
                self._engine.playback_finished.connect(self._on_playback_finished)
            except Exception:
                pass

    def set_live_mode(self, enabled: bool) -> None:
        self._live_enabled = bool(enabled)
        state = "ON" if self._live_enabled else "OFF"
        self.logger.info(f"TTSController Live Mode: {state}")

    def _on_playback_finished(self) -> None:
        """Реакция на завершение TTS.

        Если Live включен — спустя короткую задержку запускаем запись.
        """
        try:
            self.logger.debug("TTSController: playback_finished received")
            
            if not self._live_enabled:
                self.logger.debug("TTSController: Live mode disabled, skipping auto-recording")
                return
                
            if not self._start_recording_cb:
                self.logger.debug("TTSController: start_recording callback not set")
                return

            # Небольшая задержка, чтобы звуковая подсистема отпустила устройство
            self.logger.info("TTSController: Starting auto-recording in Live mode")
            QTimer.singleShot(120, self._safe_start_recording)
        except Exception as e:
            self.logger.debug(f"TTSController: playback_finished error: {e}")

    def _safe_start_recording(self) -> None:
        """Безопасный запуск записи с обработкой ошибок"""
        try:
            if not self._start_recording_cb:
                self.logger.warning("TTSController: Recording callback is None")
                return
                
            self.logger.info("TTSController: Executing auto-recording callback")
            self._start_recording_cb()
            self.logger.debug("TTSController: Auto-recording started successfully")
        except Exception as e:
            self.logger.error(f"TTSController: Failed to start recording: {e}")
