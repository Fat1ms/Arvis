"""
Core functionality for Arvis AI Assistant
"""

import asyncio
import json
import random
import re
import time
from enum import Enum
from typing import Any, Dict, List, Optional

from PyQt6.QtCore import QObject, QThread, QTimer, pyqtSignal
from PyQt6.QtWidgets import QApplication

from config.config import Config
from i18n import _
from modules.calendar_module import CalendarModule
from modules.llm_client import LLMClient
from modules.news_module import NewsModule
from modules.search_module import SearchModule
from modules.stt_engine import STTEngine
from modules.system_control import SystemControlModule
from modules.tts_base import TTSEngineBase
from modules.tts_engine import TTSEngine
from modules.tts_factory import TTSFactory
from src.core.tts_controller import TTSController
from src.core.llm_pipeline import process_with_llm as _pipeline_process_with_llm
from src.core.wake_controller import WakeController
from src.core.stt_controller import STTController
from src.core.audio_cache_manager import AudioCacheManager
from src.audio.sound_effects import init_sound_effects
from modules.wake_word_detector import KaldiWakeWordDetector
from modules.weather_module import WeatherModule
from utils.conversation_history import ConversationHistory
from utils.logger import ModuleLogger
from utils.performance_monitor import performance_monitor
from utils.async_manager import task_manager as _global_task_manager
from utils.security import (
    AuditEventType,
    AuditSeverity,
    Permission,
    Role,
    get_audit_logger,
    get_auth_manager,
    get_rbac_manager,
)
# from utils.task_manager import TaskManager  # Закомментировано: модуль не существует

# Простая заглушка для TaskManager
class TaskManagerStub(QObject):
    """Заглушка для TaskManager"""
    task_completed = pyqtSignal(str)
    task_failed = pyqtSignal(str, str)
    
    def __init__(self):
        super().__init__()
    
    def is_task_running(self, task_id):
        return False
    
    def run_async(self, task_id, worker):
        """Заглушка - не выполняет асинхронные задачи"""
        pass


class GenerationState(Enum):
    """State machine for message generation"""

    IDLE = "idle"
    GENERATING = "generating"
    REGENERATING = "regenerating"
    CANCELLED = "cancelled"


class ArvisCore(QObject):
    """Main core class for Arvis functionality"""

    # Signals
    response_ready = pyqtSignal(str)
    partial_response = pyqtSignal(str)
    processing_started = pyqtSignal()
    processing_finished = pyqtSignal()
    status_changed = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    voice_activation_detected = pyqtSignal()
    voice_message_recognized = pyqtSignal(str)  # Сигнал для распознанного голосового сообщения
    components_initialized = pyqtSignal()
    stt_model_ready = pyqtSignal(str)
    voice_assets_ready = pyqtSignal()
    tts_engine_switched = pyqtSignal(str)  # NEW: Emits engine type when switched

    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        self.logger = ModuleLogger("ArvisCore")
        
        # Инициализация звуковых эффектов
        try:
            sound_effects = init_sound_effects(config)
            sound_effects.set_enabled(config.get("ui.sound_effects_enabled", True))
        except Exception as _sound_err:
            self.logger.debug(f"Sound effects init failed: {_sound_err}")

        # Security & RBAC (v1.5.0+)
        self.rbac_enabled = bool(
            self.config.get("security.rbac.enabled", self.config.get("security.rbac_enabled", False))
        )
        self.rbac = get_rbac_manager() if self.rbac_enabled else None
        self.audit = get_audit_logger(config) if self.config.get("audit.enabled", False) else None
        self.current_user_id = None  # ID текущего пользователя (Day 4 integration)
        self.current_user = None  # Текущий аутентифицированный пользователь

        # Устанавливаем роль по умолчанию если RBAC выключен
        if self.rbac and not self.rbac_enabled:
            self.rbac.set_role(Role.ADMIN)  # Полный доступ если RBAC выключен
        elif self.rbac:
            # Роль по умолчанию из конфига
            default_role_str = str(
                self.config.get("security.rbac.default_role", self.config.get("security.default_role", "user"))
                or "user"
            )
            try:
                self.rbac.set_role(Role[default_role_str.upper()])
            except (KeyError, AttributeError):
                self.rbac.set_role(Role.USER)

        # Core components
        # Prefer the real async manager to avoid blocking UI.
        try:
            self.task_manager = _global_task_manager
        except Exception:
            self.task_manager = TaskManagerStub()  # Fallback
        self.stt_engine: Optional[STTEngine] = None
        self.wake_word_detector: Optional[KaldiWakeWordDetector] = None
        self._stt_model_ready = False
        self._voice_assets_ready = False
        self._ready_greeting_pending = True
        self._initial_ack_retry_attempts = 0
        self._preloaded_ack_cache: Dict[str, List[Any]] = {}
        self._pending_ack_task_id: Optional[str] = None
        self._is_tts_playing = False
        self._recording_source = "none"
        self.is_voice_recording = False
        self._last_wake_ts = 0.0
        self._pending_search_results: Optional[Dict[str, Any]] = None
        self.generation_state = GenerationState.IDLE
        self._auto_continue_attempts = 0
        self._stream_buffer_text = ""
        self._is_streaming_current = False
        self.live_mode = False
        # Настройки автопродолжения с приведением типов
        try:
            self._auto_continue_enabled = bool(self.config.get("llm.auto_continue", True))
        except Exception:
            self._auto_continue_enabled = True
        try:
            ac_val = self.config.get("llm.auto_continue_max", 2)
            if isinstance(ac_val, (int, float, str)):
                try:
                    self._auto_continue_max_attempts = int(float(ac_val))
                except Exception:
                    self._auto_continue_max_attempts = 2
            else:
                self._auto_continue_max_attempts = 2
        except Exception:
            self._auto_continue_max_attempts = 2
        self._tts_factory = TTSFactory()
        self._tts_engine_type: str = "silero"
        self._tts_engine_priority: List[str] = []
        self.conversation_history_manager = ConversationHistory(self.config)
        self.conversation_history: List[Dict[str, str]] = []
        
        # Command Only Mode & Audio Cache
        self.command_only_mode = False
        self.audio_cache_manager = None # Initialized in init_components

        # Timers
        self._user_timer: Optional[QTimer] = None
        self._user_timer_deadline_ts: Optional[float] = None

        # Initialize components
        self.init_components()

        # Контроллер TTS для Live Mode (подписка на playback_finished)
        try:
            self.tts_controller = TTSController(self.logger, start_recording_cb=lambda: self.toggle_voice_recording(source="wake"))
            self.tts_controller.attach_engine(getattr(self, "tts_engine", None))
        except Exception as _tc_err:
            self.logger.debug(f"TTSController init failed: {_tc_err}")

        # Контроллер Wake Word для управления активацией
        try:
            self.wake_controller = WakeController(self)
        except Exception as _wc_err:
            self.logger.debug(f"WakeController init failed: {_wc_err}")
            self.wake_controller = None

        # Если voice activation включён в конфиге, запускаем wake listening сразу
        try:
            self._configure_voice_activation()
        except Exception as _wake_cfg_err:
            self.logger.debug(f"Wake activation initial config failed: {_wake_cfg_err}")

        # Контроллер STT для управления записью голоса
        try:
            self.stt_controller = STTController(self)
        except Exception as _sc_err:
            self.logger.debug(f"STTController init failed: {_sc_err}")
            self.stt_controller = None

        # Быстрый статус таймер
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self._update_status_fast)
        self.status_timer.start(7000)  # Каждые ~7 секунд, неблокирующе

        # Таймер для отложенной генерации фраз подтверждения после полной инициализации
        self.ack_init_timer = QTimer()
        self.ack_init_timer.setSingleShot(True)
        self.ack_init_timer.timeout.connect(lambda: self._prime_name_ack_cache_async(initial=True))

        # Периодическая очистка логов/временных файлов
        try:
            from utils.housekeeping import run_periodic_housekeeping

            run_periodic_housekeeping(self.config)  # первый прогон
            self.housekeeping_timer = QTimer()
            self.housekeeping_timer.timeout.connect(lambda: run_periodic_housekeeping(self.config))
            self.housekeeping_timer.start(10 * 60 * 1000)  # каждые 10 минут
        except Exception:
            pass

    def init_components(self):
        """Initialize all core components synchronously (legacy, for reference)"""
        self.logger.info("Initializing Arvis core components...")
        self.llm_client = LLMClient(self.config)
        # Инициализация TTS через фабрику с fallback и единым API/сигналом playback_finished
        try:
            self._build_engine_priority_list()
            primary = str(self.config.get("tts.default_engine", "silero") or "silero")
            negotiated = self._negotiate_engine_with_server()
            engine_type = str(negotiated or primary)
            self.tts_engine = self._create_tts_engine_with_fallback(engine_type)
            # Сообщаем контроллеру новый движок
            try:
                if hasattr(self, "tts_controller") and self.tts_controller:
                    self.tts_controller.attach_engine(self.tts_engine)
            except Exception:
                pass
        except Exception as e:
            self.logger.error(f"Failed to initialize TTS via factory: {e}")
            self.tts_engine = None
        self.stt_engine = STTEngine(self.config)
        self.stt_engine.speech_recognized.connect(self.process_voice_input)
        try:
            self.stt_engine.model_ready.connect(self._on_stt_model_ready)
        except Exception:
            pass
        try:
            self.stt_engine.wake_word_detected.connect(self._on_wake_word_detected)
        except Exception:
            pass

        # Optional: dedicated wake word detector (Kaldi/Vosk grammar) for better accuracy
        try:
            wake_word_engine = str(self.config.get("stt.wake_word_engine", "vosk") or "vosk").lower()
        except Exception:
            wake_word_engine = "vosk"
        if wake_word_engine == "porcupine":
            wake_word_engine = "vosk"

        if wake_word_engine == "kaldi":
            try:
                shared_model = None
                try:
                    shared_model = self.stt_engine.get_model()
                except Exception:
                    shared_model = None
                self.wake_word_detector = KaldiWakeWordDetector(self.config, shared_model=shared_model)
                try:
                    self.wake_word_detector.wake_word_detected.connect(self._on_wake_word_detected)
                except Exception:
                    pass
                self.logger.info("Kaldi wake word detector initialized")
            except Exception as _kw_err:
                self.wake_word_detector = None
                self.logger.warning(f"Failed to initialize Kaldi wake word detector: {_kw_err}")
        self.init_modules()
        self.logger.info("All core components initialized")
        self.components_initialized.emit()


    def _set_voice_recording(self, active: bool):
        """Безопасно установить флаг записи и оповестить UI."""
        try:
            self.is_voice_recording = bool(active)
            # Быстрый пинг статуса
            self.status_changed.emit(
                {"is_recording": self.is_voice_recording, "recording_by_user": self._recording_source == "user"}
            )
        except Exception:
            pass

    def _on_stt_model_ready(self, model_path: str):
        """Handle STT model readiness and notify observers."""
        try:
            self._stt_model_ready = True
            self._stt_model_path = model_path
            self.logger.info(f"STT model ready: {model_path}")
        except Exception as exc:
            self.logger.debug(f"Failed to record STT readiness state: {exc}")

        status_payload = {"stt_model_ready": True, "stt_model_path": model_path, "stt_ready": True}
        try:
            self.status_changed.emit(status_payload)
        except Exception:
            pass

        try:
            self.stt_model_ready.emit(model_path)
        except Exception:
            pass

        try:
            if self.ack_init_timer and not self.ack_init_timer.isActive():
                self.ack_init_timer.start(250)
        except Exception:
            pass

        # Перепроверяем конфигурацию голосовой активации на случай, если она ожидала готовности модели
        try:
            self._configure_voice_activation()
        except Exception as cfg_error:
            self.logger.debug(f"Wake activation reconfig failed after STT ready: {cfg_error}")

        self._maybe_play_ready_greeting()

    def _prime_name_ack_cache_async(self, initial: bool = False):
        """Asynchronously pre-generate quick acknowledgement phrases for TTS."""
        try:
            if not self.tts_engine or not self.tts_engine.is_ready():
                return

            phrases = self._collect_ack_phrases()
            if not phrases:
                return

            max_slots = max(1, min(3, len(phrases)))
            self._ack_cache_target = max_slots
            phrases_to_prepare = phrases[:max_slots]

            # Выясняем, какие фразы ещё не имеют буфера
            needed = [p for p in phrases_to_prepare if len(self._preloaded_ack_cache.get(p, [])) == 0]
            if not needed:
                if initial:
                    self.logger.debug("Acknowledgement cache already primed")
                return

            # TaskManager отключен - пропускаем асинхронную загрузку
            if not self.task_manager:
                self.logger.debug("TaskManager not available, skipping async ack preload")
                if initial:
                    self._handle_initial_ack_ready(False)
                return

            if self._pending_ack_task_id and self.task_manager.is_task_running(self._pending_ack_task_id):
                return

            import time

            task_id = f"preload_name_ack_{int(time.time() * 1000)}"
            self._pending_ack_task_id = task_id

            def worker():
                engine = self.tts_engine
                if not engine or not hasattr(engine, "preload_phrases"):
                    return {}
                return engine.preload_phrases(needed, limit=len(needed))

            def on_complete(tid, result):
                if tid != task_id:
                    return
                try:
                    self.task_manager.task_completed.disconnect(on_complete)
                except Exception:
                    pass
                try:
                    self.task_manager.task_failed.disconnect(on_fail)
                except Exception:
                    pass
                self._pending_ack_task_id = None

                success = False
                if isinstance(result, dict):
                    for text, clips in result.items():
                        if not clips:
                            continue
                        cache_list = self._preloaded_ack_cache.setdefault(text, [])
                        cache_list.extend(clips)
                        # Ограничиваем до двух клипов на фразу, чтобы не разрастался кеш
                        if len(cache_list) > 2:
                            del cache_list[:-2]
                        success = True
                    total = sum(len(v) for v in self._preloaded_ack_cache.values())
                    self.logger.info(f"Preloaded acknowledgement cache updated ({total} clip(s) available)")
                else:
                    self.logger.debug("Acknowledgement preload returned no data")

                if initial:
                    self._handle_initial_ack_ready(success)
                else:
                    self._schedule_ack_cache_refill()

            def on_fail(tid, error):
                if tid != task_id:
                    return
                try:
                    self.task_manager.task_completed.disconnect(on_complete)
                except Exception:
                    pass
                try:
                    self.task_manager.task_failed.disconnect(on_fail)
                except Exception:
                    pass
                self._pending_ack_task_id = None
                self.logger.debug(f"Ack preload task failed: {error}")
                if initial:
                    self._handle_initial_ack_ready(False)
                else:
                    self._schedule_ack_cache_refill()

            self.task_manager.task_completed.connect(on_complete)
            self.task_manager.task_failed.connect(on_fail)
            self.task_manager.run_async(task_id, worker)

        except Exception as exc:
            self.logger.debug(f"Ack preload scheduling error: {exc}")
            self._pending_ack_task_id = None

    def _schedule_ack_cache_refill(self):
        """Schedule cache refill when fewer than target clips remain."""
        try:
            target = getattr(self, "_ack_cache_target", 3)
            total_cached = sum(len(v) for v in self._preloaded_ack_cache.values())
            if total_cached >= target:
                return
            if self._pending_ack_task_id and self.task_manager.is_task_running(self._pending_ack_task_id):
                return
            QTimer.singleShot(500, lambda: self._prime_name_ack_cache_async())
        except Exception as exc:
            self.logger.debug(f"Ack cache refill scheduling error: {exc}")

    def _handle_initial_ack_ready(self, success: bool):
        """React to the very first acknowledgement preload completion."""
        try:
            if success:
                self._voice_assets_ready = True
                self._initial_ack_retry_attempts = 0
                self.logger.info("Wake acknowledgement phrases prepared successfully")
                try:
                    self.voice_assets_ready.emit()
                except Exception:
                    pass
                try:
                    self.status_changed.emit({"voice_assets_ready": True})
                except Exception:
                    pass
                self._schedule_ack_cache_refill()
            else:
                self._voice_assets_ready = False
                self._initial_ack_retry_attempts += 1
                self.logger.warning("Wake acknowledgement preload failed; scheduling retry")
                if self._initial_ack_retry_attempts <= 3:
                    QTimer.singleShot(2000, lambda: self._prime_name_ack_cache_async(initial=True))
                else:
                    self.logger.error("Wake acknowledgement preload exceeded retry limit")
        except Exception as exc:
            self.logger.debug(f"Initial ack handling error: {exc}")

        # Попытка проговорить приветствие после загрузки активов (или после неудачи)
        force_greeting = not success and self._initial_ack_retry_attempts > 0
        self._maybe_play_ready_greeting(force=force_greeting)

    def _maybe_play_ready_greeting(self, force: bool = False):
        """Speak the ready greeting once everything is loaded."""
        if not self._ready_greeting_pending:
            return

        if not self._stt_model_ready:
            return

        engine = self.tts_engine
        if not engine or not engine.is_ready():
            # Подождём и попробуем ещё раз
            QTimer.singleShot(1000, lambda: self._maybe_play_ready_greeting(force))
            return

        if not force and not self._voice_assets_ready:
            return

        try:
            phrase = "Готов к работе"
            cfg_value = self.config.get("voice.ready_phrase", phrase)
            if isinstance(cfg_value, str) and cfg_value.strip():
                phrase = cfg_value.strip()
        except Exception:
            phrase = "Готов к работе"

        self.logger.info(f"Announcing readiness phrase: '{phrase}'")
        try:
            engine.speak(phrase)
            try:
                self.status_changed.emit({"ready_greeting_played": True})
            except Exception:
                pass
        except Exception as exc:
            self.logger.error(f"Failed to speak ready greeting: {exc}")
        finally:
            self._ready_greeting_pending = False

    def _take_preloaded_ack_audio(self, phrase: str):
        """Fetch pre-generated audio for a specific phrase if available."""
        try:
            queue = self._preloaded_ack_cache.get(phrase)
            if queue:
                audio = queue.pop(0)
                if not queue:
                    self._preloaded_ack_cache.pop(phrase, None)
                return audio
        except Exception as exc:
            self.logger.debug(f"Ack cache retrieval error: {exc}")
        return None

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

    def _configure_voice_activation(self):
        """Запустить или остановить слежение за ключевым словом на основе настроек."""
        if self.wake_controller:
            self.wake_controller.configure_voice_activation()

    def _on_wake_word_detected(self):
        """Обработка события активации голосом с защитами от ложных срабатываний."""
        if self.wake_controller:
            self.wake_controller.on_wake_word_detected()

    def process_voice_input(self, text: str):
        """Process recognized voice input through STT controller."""
        if self.stt_controller:
            self.stt_controller.process_voice_input(text)
        else:
            self.logger.warning("STT controller not available, skipping voice input processing")

    def _restart_wake_listening_if_enabled(self):
        """Перезапуск слежения за wake word, если включено в настройках."""
        if self.wake_controller:
            self.wake_controller.restart_wake_listening_if_enabled()

    def _respond_to_name_only(self):
        """Ответить на обращение только по имени и продолжить слушать."""
        if self.wake_controller:
            self.wake_controller.respond_to_name_only()

    def init_modules(self):
        """Initialize functional modules"""
        try:
            # Weather module
            self.weather_module = WeatherModule(self.config)

            # News module
            self.news_module = NewsModule(self.config)

            # System control module
            self.system_control_module = SystemControlModule(self.config)

            # Calendar module
            self.calendar_module = CalendarModule(self.config)

            # Web search module
            try:
                self.search_module = SearchModule(self.config)
                if not self.search_module.is_enabled():
                    self.logger.info("Search module initialized but currently disabled")
            except Exception as search_error:
                self.search_module = None
                self.logger.error(f"Failed to initialize search module: {search_error}")

            self.logger.info("All modules initialized")

        except Exception as e:
            self.logger.error(f"Failed to initialize modules: {e}")

        # Initialize Audio Cache Manager
        if self.tts_engine:
            try:
                self.audio_cache_manager = AudioCacheManager(self.config, self.tts_engine)
                # Generate cache in background
                QTimer.singleShot(1000, lambda: self.audio_cache_manager.ensure_cache())
            except Exception as e:
                self.logger.error(f"Failed to initialize AudioCacheManager: {e}")

    def _update_status_fast(self):
        """Лёгкий монитор ресурсов и предупреждения в UI"""
        try:
            import psutil

            cpu = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory().percent

            def _as_int(v, d):
                try:
                    if isinstance(v, int):
                        return v
                    if isinstance(v, str) and v.strip().isdigit():
                        return int(v)
                except Exception:
                    pass
                return d

            warn_cpu = _as_int(self.config.get("performance.cpu_warn_percent", 85), 85)
            warn_mem = _as_int(self.config.get("performance.mem_warn_percent", 85), 85)
            # Сообщаем в UI только при превышении порогов, не чаще 1 раза в 30с
            now = time.time()
            if cpu >= warn_cpu:
                last = getattr(self, "_last_cpu_warn", 0)
                if now - last > 30:
                    self._emit_status_message(f"⚠️ Высокая загрузка CPU: {cpu:.0f}%")
                    self._last_cpu_warn = now
            if mem >= warn_mem:
                last = getattr(self, "_last_mem_warn", 0)
                if now - last > 30:
                    self._emit_status_message(f"⚠️ Мало свободной памяти: {mem:.0f}% занято")
                    self._last_mem_warn = now
        except Exception:
            pass

    def _emit_status_message(self, text: str):
        """Отправка системного сообщения в панель статуса через сигнал error_occurred как инфо."""
        try:
            # Используем error_occurred для всплывашки, но с мягким текстом
            self.error_occurred.emit(text)
        except Exception:
            pass

    def process_message(self, message: str, is_regeneration: bool = False):
        """Process user message with performance monitoring

        Args:
            message: User message to process
            is_regeneration: If True, do not add message to history (for retry functionality)
        """
        # RBAC: Проверка прав на использование чата (v1.5.0+)
        if self.rbac and not self.rbac.has_permission(Permission.CHAT_USE):
            error_msg = "❌ У вас нет прав для использования чата"
            self.logger.warning(f"Permission denied: CHAT_USE for role {self.rbac.get_role()}")
            if self.audit:
                self.audit.log_event(
                    AuditEventType.PERMISSION_DENIED,
                    "Attempted to use chat without permission",
                    username=self.current_user.username if self.current_user else None,
                    details={"required_permission": "CHAT_USE"},
                    success=False,
                    severity=AuditSeverity.WARNING,
                )
            self.error_occurred.emit(error_msg)
            return

        # Проверка состояния генерации для предотвращения конкурентности
        if self.generation_state == GenerationState.GENERATING:
            self.logger.warning(
                f"Generation already in progress (state: {self.generation_state}), ignoring new message"
            )
            # Проверяем, не завис ли предыдущий запрос
            if hasattr(self, "_processing_start_time"):
                elapsed_time = time.time() - self._processing_start_time
                if elapsed_time > 10.0:
                    self.logger.warning(f"Force-resetting stuck generation after {elapsed_time:.1f}s")
                    self._force_reset_processing_state()
                    self.error_occurred.emit("Предыдущий запрос был прерван. Повторите попытку.")
                else:
                    self.logger.info(f"Still generating (elapsed: {elapsed_time:.1f}s), ignoring")
                    self.error_occurred.emit(
                        f"Запрос обрабатывается ({elapsed_time:.0f}с). Подождите или попробуйте позже."
                    )
                    return
            else:
                self.logger.warning("Generation state inconsistent, force-resetting")
                self._force_reset_processing_state()
                self.error_occurred.emit("Сброс состояния. Повторите запрос.")

        from utils.performance_monitor import performance_monitor

        start_time = time.time()

        # Устанавливаем состояние генерации
        if is_regeneration:
            self.generation_state = GenerationState.REGENERATING
            self.logger.info(f"Starting regeneration for message: {message[:50]}...")
        else:
            self.generation_state = GenerationState.GENERATING
            self.logger.info(f"Starting new generation for message: {message[:50]}...")

        # Сброс счетчиков автопродолжения и буфера на новый запрос
        self._auto_continue_attempts = 0
        self._stream_buffer_text = ""
        self._is_streaming_current = False

        self.is_processing = True
        self._processing_start_time = start_time  # Отслеживаем время начала

        # Очищаем предыдущий timeout timer если есть
        if hasattr(self, "_timeout_timer") and self._timeout_timer:
            try:
                self._timeout_timer.stop()
                self._timeout_timer.deleteLater()
                self._timeout_timer = None
            except Exception:
                pass

        self.processing_started.emit()

        try:
            # Add to conversation history только если это НЕ регенерация
            if not is_regeneration:
                self.logger.info(f"Processing message: {message}")
                self.conversation_history_manager.add_message("user", message)
                # Обновляем временный список для обратной совместимости
                self.conversation_history = self.conversation_history_manager.get_all()
            else:
                self.logger.info(f"Regenerating response for: {message}")
                # При регенерации НЕ добавляем сообщение пользователя повторно

            # Сбрасываем результаты веб-поиска, ожидая новую обработку
            self._pending_search_results = None

            # Special: allow explicit LLM query prefix even in Command Only Mode
            llm_override, llm_message = self._extract_llm_override(message)

            # Check if this is a module command (non-AI)
            module_response = None
            if not llm_override:
                module_response = self.handle_module_commands(message)
            
            # Command Only Mode Logic
            if self.command_only_mode and not llm_override:
                if module_response:
                    self.logger.info(f"Command executed in Command Mode: {message}")
                    self._play_cached_audio("done")
                    self.response_ready.emit(module_response)
                else:
                    self.logger.info(f"Command not recognized in Command Mode: {message}")
                    self._play_cached_audio("cant_chat")
                    self.error_occurred.emit(_("В этом режиме я выполняю только команды"))

                self.is_processing = False
                self.generation_state = GenerationState.IDLE
                self.processing_finished.emit()
                QTimer.singleShot(2000, lambda: self._restart_wake_listening_if_enabled())
                return

            if module_response:
                self.response_ready.emit(module_response)
                # Сохраняем ответ модуля в истории
                self.conversation_history_manager.add_message(
                    "assistant", module_response, metadata={"source": "module"}
                )
                self.conversation_history = self.conversation_history_manager.get_all()
                # Finish processing immediately for module commands
                self.is_processing = False
                self.generation_state = GenerationState.IDLE  # Сбрасываем состояние
                self.processing_finished.emit()
                # Перезапускаем wake word detection после модульной команды
                # Увеличенная задержка (3 сек) дает TTS время озвучить ответ
                QTimer.singleShot(3000, lambda: self._restart_wake_listening_if_enabled())
                performance_monitor.record_operation_time("module_command", time.time() - start_time)
            else:
                # Process with LLM (время будет измерено в process_with_llm)
                self.process_with_llm(llm_message if llm_override else message)

        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
            self.error_occurred.emit(f"Ошибка обработки: {e}")
            # Ensure proper cleanup
            self._force_reset_processing_state()
            performance_monitor.record_operation_time("message_error", time.time() - start_time)

    def set_command_only_mode(self, enabled: bool):
        """Set command only mode (no LLM chat, only system commands)"""
        self.command_only_mode = enabled
        self.logger.info(f"Command Only Mode set to: {enabled}")

    def clear_conversation_history(self) -> None:
        """Clear conversation history (UI-safe)."""
        try:
            if hasattr(self, "conversation_history_manager") and self.conversation_history_manager:
                self.conversation_history_manager.clear()
                self.conversation_history = self.conversation_history_manager.get_all()
            else:
                self.conversation_history = []
            self.logger.info("Conversation history cleared")
        except Exception as e:
            self.logger.error(f"Failed to clear conversation history: {e}")

    def _play_cached_audio(self, key: str):
        """Play a pre-generated audio file from cache"""
        if not self.audio_cache_manager:
            return
            
        path = self.audio_cache_manager.get_audio_path(key)
        if path:
            try:
                from PyQt6.QtMultimedia import QSoundEffect
                from PyQt6.QtCore import QUrl
                
                # Stop previous effect if playing
                if hasattr(self, "_sound_effect") and self._sound_effect:
                    self._sound_effect.stop()
                    
                self._sound_effect = QSoundEffect()
                self._sound_effect.setSource(QUrl.fromLocalFile(path))
                self._sound_effect.setVolume(1.0)
                self._sound_effect.play()
            except Exception as e:
                self.logger.error(f"Failed to play cached audio: {e}")
        else:
            self.logger.warning(f"Cached audio for '{key}' not found")

    def handle_module_commands(self, message: str) -> Optional[str]:
        """Handle non-AI module commands with RBAC checks (v1.5.0+)"""
        message_lower = message.lower()

        # Coin flip
        if any(phrase in message_lower for phrase in [
            "подбрось монетку",
            "подкинь монетку",
            "брось монетку",
            "кинь монетку",
            "монетку",
            "орёл или решка",
            "орел или решка",
        ]):
            return "🪙 " + ("Орёл" if random.random() < 0.5 else "Решка")

        # Random number
        if any(phrase in message_lower for phrase in ["случайное число", "рандомное число", "рандом", "random число"]):
            m = re.search(r"(\d+)\s*(?:до|\-|—)\s*(\d+)", message_lower)
            if m:
                a = int(m.group(1))
                b = int(m.group(2))
                lo, hi = (a, b) if a <= b else (b, a)
                return f"🎲 Случайное число: {random.randint(lo, hi)}"
            return f"🎲 Случайное число: {random.randint(1, 100)}"

        # Time/date
        if any(phrase in message_lower for phrase in ["который час", "сколько времени", "время сейчас", "время"]):
            try:
                import datetime

                now = datetime.datetime.now()
                return f"🕒 Сейчас {now.strftime('%H:%M')}"
            except Exception:
                pass
        if any(phrase in message_lower for phrase in ["какая сегодня дата", "какая дата", "сегодня какое число", "дата"]):
            try:
                import datetime

                now = datetime.datetime.now()
                return f"📅 Сегодня {now.strftime('%d.%m.%Y')}"
            except Exception:
                pass

        # Timer commands
        if any(k in message_lower for k in ["таймер", "засеки", "поставь таймер", "поставить таймер", "будильник", "напомни"]):
            if any(word in message_lower for word in ["отмени", "сброс", "стоп", "останов", "выключи"]):
                return self._cancel_user_timer()
            duration_ms = self._parse_duration_ms(message_lower)
            if duration_ms is None:
                return "⏱️ Скажи, на сколько поставить таймер: например «таймер на 5 минут», «напомни через 10 минут», «таймер на 30 секунд»."
            return self._start_user_timer(duration_ms)

        # Internet speedtest
        if any(phrase in message_lower for phrase in ["проверь интернет", "проверить интернет", "скорость интернета", "спидтест", "speedtest"]):
            return self._start_internet_check_async()

        # Air alert check
        if "тревог" in message_lower or "повітря" in message_lower or "воздуш" in message_lower:
            if any(phrase in message_lower for phrase in ["есть ли тревога", "есть тревога", "тревога сейчас", "сейчас тревога", "карта тревог"]):
                return self._start_air_alert_check_async(message_lower)

        # Weather commands - ПРИОРИТЕТ: специализированный модуль
        if any(word in message_lower for word in ["погода", "температура", "weather"]):
            # RBAC: Проверка прав на модуль погоды
            if self.rbac and not self.rbac.can_use_module("weather"):
                self.logger.warning(f"Permission denied: MODULE_WEATHER for role {self.rbac.get_role()}")
                if self.audit:
                    self.audit.log_event(
                        AuditEventType.PERMISSION_DENIED,
                        "Attempted to use weather module without permission",
                        username=self.current_user.username if self.current_user else None,
                        success=False,
                        severity=AuditSeverity.INFO,
                    )
                return "❌ У вас нет прав для использования модуля погоды (требуется роль User или выше)"

            if self.weather_module:
                return self.weather_module.get_weather()

        # News commands - ПРИОРИТЕТ: специализированный модуль
        if any(word in message_lower for word in ["новости", "news"]):
            # RBAC: Проверка прав на модуль новостей
            if self.rbac and not self.rbac.can_use_module("news"):
                self.logger.warning(f"Permission denied: MODULE_NEWS for role {self.rbac.get_role()}")
                if self.audit:
                    self.audit.log_event(
                        AuditEventType.PERMISSION_DENIED,
                        "Attempted to use news module without permission",
                        username=self.current_user.username if self.current_user else None,
                        success=False,
                        severity=AuditSeverity.INFO,
                    )
                return "❌ У вас нет прав для использования модуля новостей (требуется роль User или выше)"

            if self.news_module:
                return self.news_module.get_news()

        # System control commands - ПРИОРИТЕТ: специализированный модуль
        if any(word in message_lower for word in ["запусти", "открой", "включи", "выключи"]):
            if self.system_control_module:
                # Проверка прав будет внутри SystemControlModule
                return self.system_control_module.execute_command(message)

        # Audio control commands - ПРИОРИТЕТ: специализированный модуль
        if any(word in message_lower for word in ["громкость", "звук", "музыка"]):
            if self.system_control_module:
                return self.system_control_module.control_audio(message)

        # Web search commands - FALLBACK: только если специализированные модули не сработали
        if self.search_module and self.search_module.is_enabled():
            try:
                if self.search_module.should_handle(message):
                    search_payload = self.search_module.search(message)
                    if search_payload and search_payload.get("results"):
                        self._pending_search_results = search_payload
                        self.logger.info(
                            f"Collected {len(search_payload['results'])} web results for query '{search_payload['query']}'"
                        )
                        # Продолжаем обработку через LLM, чтобы сформировать ответ с источниками
                        return None
                    elif search_payload and search_payload.get("error"):
                        self.logger.warning(f"Search module error: {search_payload.get('error')}")
                        self.error_occurred.emit(_("Не удалось выполнить веб-поиск. Проверьте соединение."))
                        return None
                    else:
                        self.logger.info("Search module returned no results")
                        self.error_occurred.emit(_("Мне не удалось найти актуальные источники в сети."))
                        return None
            except Exception as search_exception:
                self.logger.error(f"Search module failure: {search_exception}")
                self.error_occurred.emit(_("Ошибка веб-поиска: {error}").format(error=search_exception))
                return None

        return None

    def _extract_llm_override(self, message: str) -> tuple[bool, str]:
        """Detect explicit 'ask the neural net' prefix and strip it for LLM."""
        try:
            text = (message or "").strip()
            lowered = text.lower().strip()
            prefixes = [
                "спроси у нейронки",
                "спроси нейронку",
                "спроси у нейросети",
                "нейронка",
                "нейросеть",
            ]
            for p in prefixes:
                if lowered.startswith(p):
                    remainder = text[len(p) :].lstrip(" :,-—\t")
                    if remainder:
                        return True, remainder
                    return True, ""
        except Exception:
            pass
        return False, message

    def _parse_duration_ms(self, text: str) -> Optional[int]:
        """Parse simple RU duration from text into milliseconds."""
        try:
            t = (text or "").lower()
            # Support patterns like: 5 минут, 30 секунд, 1 час, 1.5 минуты
            m = re.search(r"(\d+(?:[\.,]\d+)?)\s*(сек(?:унд[а-я]*)?|мин(?:ут[а-я]*)?|час(?:ов|а)?)", t)
            if not m:
                return None
            raw = m.group(1).replace(",", ".")
            value = float(raw)
            unit = m.group(2)
            if unit.startswith("сек"):
                seconds = value
            elif unit.startswith("мин"):
                seconds = value * 60
            elif unit.startswith("час"):
                seconds = value * 3600
            else:
                return None
            if seconds <= 0:
                return None
            # Cap to 24 hours to avoid runaway timers
            seconds = min(seconds, 24 * 3600)
            return int(seconds * 1000)
        except Exception:
            return None

    def _start_user_timer(self, duration_ms: int) -> str:
        try:
            # Reset existing timer
            if self._user_timer:
                try:
                    self._user_timer.stop()
                    self._user_timer.deleteLater()
                except Exception:
                    pass
                self._user_timer = None

            self._user_timer = QTimer()
            self._user_timer.setSingleShot(True)
            self._user_timer_deadline_ts = time.time() + (duration_ms / 1000.0)

            def _on_timeout():
                try:
                    self._user_timer_deadline_ts = None
                    self.response_ready.emit("⏰ Таймер! Время вышло.")
                    self.conversation_history_manager.add_message(
                        "assistant", "⏰ Таймер! Время вышло.", metadata={"source": "timer"}
                    )
                except Exception:
                    pass

            self._user_timer.timeout.connect(_on_timeout)
            self._user_timer.start(int(duration_ms))

            # Human-friendly confirmation
            seconds = max(1, int(round(duration_ms / 1000.0)))
            if seconds >= 3600:
                hours = seconds // 3600
                minutes = (seconds % 3600) // 60
                if minutes:
                    return f"⏱️ Таймер поставлен на {hours} ч {minutes} мин"
                return f"⏱️ Таймер поставлен на {hours} ч"
            if seconds >= 60:
                minutes = seconds // 60
                rem = seconds % 60
                if rem:
                    return f"⏱️ Таймер поставлен на {minutes} мин {rem} сек"
                return f"⏱️ Таймер поставлен на {minutes} мин"
            return f"⏱️ Таймер поставлен на {seconds} сек"
        except Exception as e:
            self.logger.error(f"Failed to start timer: {e}")
            return f"❌ Не удалось поставить таймер: {e}"

    def _cancel_user_timer(self) -> str:
        try:
            if self._user_timer and self._user_timer.isActive():
                self._user_timer.stop()
                self._user_timer_deadline_ts = None
                return "⏹️ Таймер отменён"
            self._user_timer_deadline_ts = None
            return "ℹ️ Таймер не был запущен"
        except Exception as e:
            return f"❌ Не удалось отменить таймер: {e}"

    def _start_internet_check_async(self) -> str:
        task_id = "internet_speedtest"
        try:
            if hasattr(self.task_manager, "is_task_running") and self.task_manager.is_task_running(task_id):
                return "⏳ Уже проверяю интернет…"

            def worker():
                # Optional dependency
                import speedtest

                st = speedtest.Speedtest(secure=True)
                st.get_best_server()
                download_bps = st.download()
                upload_bps = st.upload(pre_allocate=False)
                ping_ms = float(getattr(st.results, "ping", 0.0) or 0.0)

                down_mbps = download_bps / 1_000_000
                up_mbps = upload_bps / 1_000_000
                return {
                    "ping_ms": ping_ms,
                    "down_mbps": down_mbps,
                    "up_mbps": up_mbps,
                }

            def on_complete(_tid: str, result: Any):
                try:
                    ping = float(result.get("ping_ms", 0.0))
                    down = float(result.get("down_mbps", 0.0))
                    up = float(result.get("up_mbps", 0.0))
                    text = f"📶 Интернет: ping {ping:.0f} мс, ↓ {down:.1f} Мбит/с, ↑ {up:.1f} Мбит/с"
                    self.response_ready.emit(text)
                    self.conversation_history_manager.add_message(
                        "assistant", text, metadata={"source": "internet"}
                    )
                except Exception as e:
                    try:
                        self.error_occurred.emit(f"❌ Ошибка обработки результата speedtest: {e}")
                    except Exception:
                        pass

            def on_error(_tid: str, err: Exception):
                msg = str(err)
                if "No module named" in msg and "speedtest" in msg:
                    self.error_occurred.emit(
                        "❌ Speedtest не установлен. Установите пакет speedtest-cli (pip install speedtest-cli) и повторите."
                    )
                else:
                    self.error_occurred.emit(f"❌ Не удалось проверить интернет: {msg}")

            started = self.task_manager.run_async(task_id, worker, on_complete=on_complete, on_error=on_error)
            if not started:
                return "⏳ Уже проверяю интернет…"
            return "⏳ Проверяю интернет (speedtest)…"
        except Exception as e:
            self.logger.error(f"Failed to start internet check: {e}")
            return f"❌ Не удалось запустить проверку интернета: {e}"

    def _start_air_alert_check_async(self, message_lower: str) -> str:
        """Check air alert status via configurable API.

        Note: provider requires configuration; defaults are intentionally conservative.
        """
        task_id = "air_alert_check"
        try:
            api_url = str(self.config.get("modules.alerts.api_url", "") or "").strip()
            api_token = str(self.config.get("modules.alerts.api_token", "") or "").strip()
            if not api_url:
                return (
                    "⚠️ Модуль тревог не настроен. Добавьте в config.json: modules.alerts.api_url "
                    "(и при необходимости modules.alerts.api_token), затем повторите." 
                )

            # Simple region extraction
            region = "киев"
            if "київ" in message_lower or "киев" in message_lower:
                region = "kyiv"
            if "обла" in message_lower and ("київ" in message_lower or "киев" in message_lower):
                region = "kyiv_oblast"

            if hasattr(self.task_manager, "is_task_running") and self.task_manager.is_task_running(task_id):
                return "⏳ Уже проверяю тревоги…"

            def worker():
                import requests

                headers = {"User-Agent": "Arvis-Client"}
                if api_token:
                    headers["Authorization"] = f"Bearer {api_token}"
                r = requests.get(api_url, headers=headers, timeout=6)
                r.raise_for_status()
                data = r.json()
                return {"region": region, "data": data}

            def on_complete(_tid: str, result: Any):
                try:
                    region_key = result.get("region")
                    data = result.get("data")
                    # Heuristic parsing: accept dict with region keys or list of objects
                    is_alert = None
                    if isinstance(data, dict):
                        candidate = data.get(region_key) or data.get(region_key.replace("_", "-"))
                        if isinstance(candidate, dict) and "alert" in candidate:
                            is_alert = bool(candidate.get("alert"))
                        elif isinstance(candidate, bool):
                            is_alert = bool(candidate)
                    elif isinstance(data, list):
                        for item in data:
                            if not isinstance(item, dict):
                                continue
                            name = str(item.get("region") or item.get("name") or item.get("title") or "").lower()
                            if region_key in name or (region_key == "kyiv" and "ки" in name and "ки" in name):
                                if "alert" in item:
                                    is_alert = bool(item.get("alert"))
                                    break
                                if "is_alert" in item:
                                    is_alert = bool(item.get("is_alert"))
                                    break

                    if is_alert is None:
                        text = "⚠️ Не удалось разобрать ответ API тревог. Проверьте формат данных провайдера."
                    else:
                        if region_key == "kyiv_oblast":
                            where = "Киевской области"
                        else:
                            where = "Киеве"
                        text = ("🚨 Сейчас тревога в " + where) if is_alert else ("✅ Сейчас нет тревоги в " + where)

                    self.response_ready.emit(text)
                    self.conversation_history_manager.add_message(
                        "assistant", text, metadata={"source": "alerts"}
                    )
                except Exception as e:
                    self.error_occurred.emit(f"❌ Ошибка обработки тревог: {e}")

            def on_error(_tid: str, err: Exception):
                self.error_occurred.emit(f"❌ Не удалось проверить тревоги: {err}")

            started = self.task_manager.run_async(task_id, worker, on_complete=on_complete, on_error=on_error)
            if not started:
                return "⏳ Уже проверяю тревоги…"
            return "⏳ Проверяю тревоги…"
        except Exception as e:
            self.logger.error(f"Failed to start air alert check: {e}")
            return f"❌ Не удалось запустить проверку тревог: {e}"

    def process_with_llm(self, message: str):
        """Process message with LLM (delegated to llm_pipeline)."""
        return _pipeline_process_with_llm(self, message)


    # process_voice_input реализован выше с перезапуском wake listening

    def toggle_voice_recording(self, source: str = "user"):
        """Toggle voice recording state through STT controller.

        source: 'user' (кнопка) | 'wake' (ключевое слово) — влияет на UI-индикацию.
        """
        if self.stt_controller:
            self.stt_controller.toggle_recording(source=source)
        else:
            self.error_occurred.emit("STT контроллер не инициализирован")

    def set_live_mode(self, enabled: bool):
        """Включает или выключает Live Mode."""
        self.live_mode = bool(enabled)
        self.logger.info(f"Live Mode has been {'enabled' if enabled else 'disabled'}.")
        
        # Уведомляем TTS контроллер
        try:
            if hasattr(self, "tts_controller") and self.tts_controller:
                self.tts_controller.set_live_mode(self.live_mode)
        except Exception:
            pass
        
        # Управление wake word детекцией при Live режиме
        try:
            # Получаем настройку: отключать ли wake word в Live режиме
            disable_wake_in_live = bool(self.config.get("modes.live_disable_wake_word", True))
            
            if disable_wake_in_live and hasattr(self, "wake_controller") and self.wake_controller:
                if enabled:
                    # Live включен → останавливаем wake word
                    self.logger.info("Live Mode enabled: stopping wake word detection")
                    self._stop_wake_word_detection()
                else:
                    # Live выключен → перезапускаем wake word если включён в настройках
                    voice_activation_enabled = bool(self.config.get("modules.voice_activation_enabled", False))
                    if voice_activation_enabled:
                        self.logger.info("Live Mode disabled: restarting wake word detection")
                        self.wake_controller.restart_wake_listening_if_enabled()
        except Exception as e:
            self.logger.debug(f"Failed to manage wake word in Live mode: {e}")
        
        # КРИТИЧНО: При включении Live Mode автоматически запускаем запись
        if enabled:
            self.logger.info("Live Mode enabled: starting initial voice recording")
            QTimer.singleShot(300, lambda: self._start_live_recording())
        else:
            # При выключении Live Mode останавливаем запись если она активна
            if getattr(self, "is_voice_recording", False):
                self.logger.info("Live Mode disabled: stopping voice recording")
                self.toggle_voice_recording(source="live")
        
        # Уведомляем UI через сигнал status_changed
        try:
            self.status_changed.emit({
                "live_mode": self.live_mode,
                "is_recording": getattr(self, "is_voice_recording", False),
                "is_processing": getattr(self, "is_processing", False)
            })
        except Exception as e:
            self.logger.debug(f"Failed to emit live_mode status: {e}")
    
    def _stop_wake_word_detection(self):
        """Останавливает wake word детекцию (внутренний метод)"""
        try:
            wake_word_engine = str(self.config.get("stt.wake_word_engine", "vosk") or "vosk").lower()
            if wake_word_engine == "porcupine":
                wake_word_engine = "vosk"
            
            if wake_word_engine == "kaldi" and hasattr(self, "wake_word_detector") and self.wake_word_detector:
                self.wake_word_detector.stop_detection()
                self.logger.debug("Kaldi wake word detection stopped")
            elif hasattr(self, "stt_engine") and self.stt_engine:
                self.stt_engine.stop_wake_word_detection()
                self.logger.debug("Vosk wake word detection stopped")
        except Exception as e:
            self.logger.debug(f"Error stopping wake word detection: {e}")
    
    def _start_live_recording(self):
        """Запускает запись при активации Live Mode"""
        try:
            # Проверяем, что Live Mode всё ещё активен
            if not self.live_mode:
                self.logger.debug("Live Mode was disabled before recording could start")
                return
            
            # Проверяем, что запись ещё не активна
            if getattr(self, "is_voice_recording", False):
                self.logger.debug("Recording already active, skipping Live Mode auto-start")
                return
            
            self.logger.info("Starting Live Mode voice recording")
            self.toggle_voice_recording(source="live")
        except Exception as e:
            self.logger.error(f"Failed to start Live Mode recording: {e}")

    def on_playback_finished(self):
        """Устарело: обработка перенесена в TTSController (оставлено для совместимости)."""
        try:
            if hasattr(self, "tts_controller") and self.tts_controller:
                # Ничего не делаем: TTSController уже обрабатывает playback_finished
                self.logger.debug("on_playback_finished routed to TTSController")
                return
        except Exception:
            pass
        # Fallback на случай отсутствия контроллера
        if self.live_mode and not getattr(self, "is_voice_recording", False):
            QTimer.singleShot(120, lambda: self.toggle_voice_recording(source="wake"))

    def set_current_user(self, user_id: Optional[str]):
        """Set the current user ID for context"""
        self.current_user_id = user_id
        self.logger.info(f"Set current user: {user_id or 'Guest'}")

        # Propagate to RBAC
        if self.rbac:
            self.rbac.set_current_user(user_id)

        # Propagate to modules that need user context
        if self.calendar_module and hasattr(self.calendar_module, "set_current_user"):
            self.calendar_module.set_current_user(user_id)
            self.logger.debug("Calendar module user updated")

        if self.search_module and hasattr(self.search_module, "set_current_user"):
            self.search_module.set_current_user(user_id)
            self.logger.debug("Search module user updated")

        if self.system_control_module and hasattr(self.system_control_module, "set_current_user"):
            self.system_control_module.set_current_user(user_id)
            self.logger.debug("System control module user updated")

        # Audit log
        if self.audit and user_id:
            self.audit.log_event(
                event_type=AuditEventType.LOGIN_SUCCESS,
                action=f"User set in ArvisCore: {user_id}",
                user_id=user_id,
                severity=AuditSeverity.INFO,
            )

    

    def get_system_info(self) -> Dict[str, Any]:
        """Get system information"""
        return {
            "version": "1.0.0",
            "llm_model": self.config.get("llm.default_model"),
            "ollama_url": self.config.get("llm.ollama_url"),
            "user_name": self.config.get("user.name"),
            "modules_active": {
                "weather": self.weather_module is not None,
                "news": self.news_module is not None,
                "system_control": self.system_control_module is not None,
                "calendar": self.calendar_module is not None,
            },
        }

    # ========== TTS Factory Methods (Days 4-5) ==========

    def _negotiate_engine_with_server(self) -> Optional[str]:
        """Query server for preferred TTS engine (hybrid system).
        
        Currently a placeholder. Will be implemented to query:
        GET /api/client/engine-preference
        
        Returns: engine type string or None if unavailable
        """
        try:
            self.logger.debug("Querying server for engine preference...")
            # TODO: Implement server API call when Client API extended
            # For now: return None (use local config)
            return None
        except Exception as e:
            self.logger.warning(f"Server engine negotiation failed: {e}")
            return None

    def _build_engine_priority_list(self) -> None:
        """Build fallback priority list from config.
        
        Priority: configured default → available engines
        """
        # Prefer explicit priority from config when present
        try:
            cfg_priority = self.config.get("tts.engines_priority", None)
        except Exception:
            cfg_priority = None

        if isinstance(cfg_priority, list) and cfg_priority:
            priority = [str(e) for e in cfg_priority]
        else:
            # Fallback to all registered engines order
            priority = self._tts_factory.list_available_engines()

        # Filter SAPI if disabled in config
        try:
            sapi_allowed = bool(self.config.get("tts.sapi_enabled", False))
        except Exception:
            sapi_allowed = False
        if not sapi_allowed:
            priority = [e for e in priority if e != "sapi"]

        # Primary engine from config (default_engine)
        primary = str(self.config.get("tts.default_engine", "silero") or "silero")
        # Ensure primary is first if present in list; otherwise prepend it (will be filtered later if unknown)
        pr_list = [primary] + [e for e in priority if e != primary]
        self._tts_engine_priority = pr_list
        self.logger.info(f"TTS engine priority: {self._tts_engine_priority}")

    def _create_tts_engine_with_fallback(self, engine_type: str) -> TTSEngineBase:
        """Create TTS engine with fallback to alternatives.
        
        Args:
            engine_type: Primary engine type to try
            
        Returns:
            TTSEngineBase instance
            
        Raises:
            RuntimeError: If all engines fail to initialize
        """
        # Try primary first, then fallback list (deduplicated)
        # Merge and de-duplicate list
        engines_to_try: list[str] = []
        seen = set()
        for e in [engine_type] + self._tts_engine_priority:
            if not isinstance(e, str):
                continue
            if e not in seen:
                seen.add(e)
                engines_to_try.append(e)

        # Respect SAPI config flag (double-guard here as we call simple create_engine below)
        try:
            if not bool(self.config.get("tts.sapi_enabled", False)):
                engines_to_try = [e for e in engines_to_try if e != "sapi"]
        except Exception:
            engines_to_try = [e for e in engines_to_try if e != "sapi"]

        # Delegate to factory's fallback creator (it also performs health checks and skips SAPI when disabled)
        engine_obj = self._tts_factory.create_engine_with_fallback(engines_to_try, self.config, self.logger)
        if engine_obj is None:
            # All engines failed
            raise RuntimeError("Could not initialize any TTS engine!")

        # Try to determine engine type name for logging
        etype = None
        try:
            status = engine_obj.get_status() if hasattr(engine_obj, "get_status") else {}
            etype = status.get("engine") if isinstance(status, dict) else None
        except Exception:
            etype = None
        if not etype:
            cls_name = engine_obj.__class__.__name__.lower()
            if "silero" in cls_name:
                etype = "silero"
            elif "bark" in cls_name:
                etype = "bark"
            elif "sapi" in cls_name:
                etype = "sapi"
            else:
                etype = "unknown"

        self._tts_engine_type = etype
        self.logger.info(f"✅ Successfully initialized {etype} TTS engine")
        return engine_obj

    async def switch_tts_engine_async(self, new_engine_type: str) -> bool:
        """Switch to different TTS engine at runtime.
        
        Args:
            new_engine_type: Engine type to switch to (e.g., "bark", "silero")
            
        Returns:
            True if switch successful, False otherwise
        """
        try:
            self.logger.info(f"Switching TTS engine: {self._tts_engine_type} → {new_engine_type}")
            
            # Check if new engine available
            if not self._tts_factory.is_engine_available(new_engine_type):
                self.logger.error(f"Engine {new_engine_type} not available")
                return False
            
            # Stop current engine if speaking
            try:
                if self.tts_engine and hasattr(self.tts_engine, "get_status"):
                    status = self.tts_engine.get_status()
                    if status and hasattr(status, "value"):
                        if status.value in ["SPEAKING", "INITIALIZING"]:
                            await self.tts_engine.stop()
            except Exception as stop_error:
                self.logger.warning(f"Failed to stop current engine: {stop_error}")
            
            # Create new engine
            new_engine = self._tts_factory.create_engine(new_engine_type, self.config, self.logger)
            if not new_engine:
                self.logger.error(f"Engine {new_engine_type} creation returned None")
                return False
            
            # Run health check
            try:
                health = new_engine.health_check()
                if not health.healthy:
                    self.logger.error(f"{new_engine_type} health check failed: {health.message}")
                    return False
            except Exception as hc_error:
                self.logger.error(f"Health check for {new_engine_type} failed: {hc_error}")
                return False
            
            # Switch
            self.tts_engine = new_engine
            self._tts_engine_type = new_engine_type
            self.logger.info(f"✅ Successfully switched to {new_engine_type}")
            
            # Emit signal for UI update
            try:
                self.tts_engine_switched.emit(new_engine_type)
            except Exception:
                pass
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to switch engine: {e}")
            return False

    def _speak_and_start_recording_after_tts(self, text: str):
        """Speak a phrase and start recording after TTS finishes."""
        if not self.tts_engine:
            self.toggle_voice_recording(source="wake")
            return

        # Disconnect any previous connection to avoid multiple triggers
        try:
            self.tts_engine.playback_finished.disconnect(self._start_recording_post_tts)
        except TypeError:
            pass  # Signal was not connected

        self.tts_engine.playback_finished.connect(self._start_recording_post_tts)
        self.tts_engine.speak(text)

    def _start_recording_post_tts(self):
        """Slot to start recording, called after TTS playback."""
        # Disconnect immediately to prevent it from running on subsequent playbacks
        if self.tts_engine:
            try:
                self.tts_engine.playback_finished.disconnect(self._start_recording_post_tts)
            except TypeError:
                pass
        
        # Use a short delay to ensure audio system has released the output channel
        QTimer.singleShot(150, lambda: self.toggle_voice_recording(source="wake"))

    def _force_reset_processing_state(self):
        """Forcefully resets all processing-related state."""
        self.logger.warning("Force-resetting processing state...")
        self.is_processing = False
        self.generation_state = GenerationState.IDLE
        self.cancel_flag = False
        self._is_streaming_current = False
        self._stream_buffer_text = ""
        self._auto_continue_attempts = 0
        
        # Stop any running timers
        if hasattr(self, "_timeout_timer") and self._timeout_timer:
            self._timeout_timer.stop()
        if hasattr(self, "_no_stream_progress_timer") and self._no_stream_progress_timer:
            self._no_stream_progress_timer.stop()

        # Attempt to stop worker thread
        if hasattr(self, "_current_llm_worker") and self._current_llm_worker:
            try:
                if self._current_llm_worker.isRunning():
                    self._current_llm_worker.quit()
                    self._current_llm_worker.wait(1000) # Wait a bit
            except Exception as e:
                self.logger.error(f"Error stopping LLM worker: {e}")
        
        self.processing_finished.emit()

    def _cleanup_processing_state(self):
        """Cleans up state after processing is fully complete."""
        self.is_processing = False
        self.generation_state = GenerationState.IDLE
        if hasattr(self, "_timeout_timer") and self._timeout_timer:
            self._timeout_timer.stop()
        self.processing_finished.emit()
        # Restart wake word listening after a delay to allow TTS to finish
        QTimer.singleShot(3000, self._restart_wake_listening_if_enabled)
