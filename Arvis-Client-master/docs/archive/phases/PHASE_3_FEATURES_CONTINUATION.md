# Phase 3: Детальные планы реализации (часть 2)
## Фичи #4-9

---

## FEATURE 4️⃣: Разделить arvis_core.py на модули

### 4.1 Текущее состояние
- `src/core/arvis_core.py`: 1873 строки
- Включает: инициализацию, обработку сообщений, управление модулями, security, state management
- Сложность для тестирования и поддержки

### 4.2 План разделения

```
src/core/
├── __init__.py (переэкспорт ArvisCore)
│
├── core_base.py (450 строк)
│   ├── ArvisCore (base class)
│   ├── Все Qt signals
│   ├── Config и logger инициализация
│   ├── Lifecyle (init, destroy)
│   └── Event loop setup
│
├── core_processing.py (400 строк)
│   ├── process_message(text, source)
│   ├── process_voice_input(text)
│   ├── handle_llm_response(response)
│   ├── handle_module_commands(message)
│   ├── _stream_response_with_tts()
│   └── Auto-continue logic
│
├── core_modules.py (350 строк)
│   ├── init_modules()
│   ├── Module manager methods
│   ├── Weather, News, Calendar, System Control, Search modules
│   ├── Module command parsing
│   └── Module state tracking
│
├── core_security.py (300 строк)
│   ├── _setup_rbac()
│   ├── _check_permission()
│   ├── _audit_log()
│   ├── User authentication integration
│   └── 2FA handling
│
├── core_state.py (250 строк)
│   ├── State machine (GenerationState, ProcessingState)
│   ├── State transitions
│   ├── State validation
│   └── State recovery
│
├── core_components.py (300 строк)
│   ├── init_components_async()
│   ├── Initialize STT, TTS, LLM, Wake Word
│   ├── Component lifecycle
│   └── Component error handling
│
└── core_voice.py (250 строк)
    ├── Voice recording management
    ├── Wake word detection
    ├── Audio playback control
    └── Voice acknowledgement phrases
```

### 4.3 Реализация шаги

**Шаг 1**: Создать `core_base.py`
```python
# src/core/core_base.py
from PyQt5.QtCore import QObject, pyqtSignal
from typing import Optional, Dict, Any

class ArvisCore(QObject):
    """Base class with signals and initialization"""
    
    # Signals (all here)
    response_ready = pyqtSignal(str)
    partial_response = pyqtSignal(str)
    processing_started = pyqtSignal()
    processing_finished = pyqtSignal()
    status_changed = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    voice_activation_detected = pyqtSignal()
    voice_message_recognized = pyqtSignal(str)
    components_initialized = pyqtSignal()
    stt_model_ready = pyqtSignal(str)
    voice_assets_ready = pyqtSignal()
    health_status_changed = pyqtSignal(list)  # List[HealthCheckResult]
    
    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        self.logger = ModuleLogger("ArvisCore")
        
        # Security
        self.rbac_enabled = bool(config.get("security.rbac.enabled", False))
        self.rbac = get_rbac_manager() if self.rbac_enabled else None
        self.audit = get_audit_logger(config) if config.get("audit.enabled", False) else None
        self.current_user_id = None
        self.current_user = None
        
        # Components (инициализируются отдельно)
        self.llm_client = None
        self.tts_engine = None
        self.stt_engine = None
        self.wake_word_detector = None
        
        # Modules
        self.weather_module = None
        self.news_module = None
        self.system_control_module = None
        self.calendar_module = None
        self.search_module = None
        
        # History
        self.conversation_history_manager = ConversationHistory(config)
        self.conversation_history = []
        
        # State
        self.is_processing = False
        self.generation_state = GenerationState.IDLE
        self.is_voice_recording = False
        self.is_audio_playback_paused = False
        self._is_tts_playing = False
        
        # Task manager
        from utils.async_manager import task_manager
        self.task_manager = task_manager
        
        # Health checker
        self.health_checker = None
    
    def _setup_logging(self):
        """Setup logging"""
        pass
    
    def _setup_security(self):
        """Setup RBAC and audit"""
        pass
    
    def start(self):
        """Start initialization sequence"""
        self.init_components_async()
        self.init_modules_async()
        self.start_health_checks()
    
    def stop(self):
        """Cleanup and shutdown"""
        pass
```

**Шаг 2**: Создать `core_components.py`
```python
# src/core/core_components.py
class ComponentInitializer:
    """Handles initialization of all components"""
    
    def __init__(self, arvis_core):
        self.core = arvis_core
    
    def init_components_async(self):
        """Initialize STT, TTS, LLM in background"""
        from utils.async_manager import task_manager
        
        def load_components():
            # 1. LLM (быстро)
            self._init_llm()
            # 2. TTS (медленно)
            self._init_tts()
            # 3. STT (медленно)
            self._init_stt()
            # 4. Wake Word (опционально)
            self._init_wake_word()
            
            self.core.components_initialized.emit()
        
        task_manager.run_async("init_components", load_components)
    
    def _init_llm(self):
        """Initialize LLM client"""
        try:
            from modules.llm_client import LLMClient
            self.core.llm_client = LLMClient(self.core.config, self.core.logger)
            self.core.logger.info("LLM client initialized")
        except Exception as e:
            self.core.logger.error(f"Failed to init LLM: {e}")
            self.core.error_occurred.emit(f"LLM init failed: {e}")
    
    def _init_tts(self):
        """Initialize TTS engine"""
        try:
            from modules.tts_factory import TTSFactory
            engine_name = self.core.config.get("tts.engine", "silero")
            self.core.tts_engine = TTSFactory.create_engine(engine_name, self.core.config, self.core.logger)
            # Connect signals
            if hasattr(self.core.tts_engine, 'speech_started'):
                self.core.tts_engine.speech_started.connect(self._on_tts_started)
            if hasattr(self.core.tts_engine, 'speech_finished'):
                self.core.tts_engine.speech_finished.connect(self._on_tts_finished)
            self.core.logger.info(f"TTS engine initialized: {engine_name}")
        except Exception as e:
            self.core.logger.error(f"Failed to init TTS: {e}")
            self.core.error_occurred.emit(f"TTS init failed: {e}")
    
    def _init_stt(self):
        """Initialize STT engine"""
        try:
            from modules.stt_engine import STTEngine
            self.core.stt_engine = STTEngine(self.core.config, self.core.logger)
            # Connect signals
            self.core.stt_engine.speech_recognized.connect(self.core.process_voice_input)
            self.core.stt_engine.model_ready.connect(self._on_stt_model_ready)
            self.core.logger.info("STT engine initialized")
        except Exception as e:
            self.core.logger.error(f"Failed to init STT: {e}")
            self.core.error_occurred.emit(f"STT init failed: {e}")
    
    def _init_wake_word(self):
        """Initialize wake word detector (optional)"""
        if not self.core.config.get("stt.wake_word_engine"):
            return
        
        try:
            from modules.wake_word_detector import KaldiWakeWordDetector
            self.core.wake_word_detector = KaldiWakeWordDetector(self.core.config, self.core.logger)
            self.core.wake_word_detector.wake_word_detected.connect(self._on_wake_word_detected)
            self.core.logger.info("Wake word detector initialized")
        except Exception as e:
            self.core.logger.warning(f"Wake word detector not available: {e}")
    
    def _on_tts_started(self):
        """TTS started"""
        self.core._is_tts_playing = True
    
    def _on_tts_finished(self):
        """TTS finished"""
        self.core._is_tts_playing = False
    
    def _on_stt_model_ready(self, model_path):
        """STT model loaded"""
        self.core.stt_model_ready.emit(model_path)
    
    def _on_wake_word_detected(self):
        """Wake word detected"""
        self.core.voice_activation_detected.emit()
```

**Шаг 3**: Создать `core_processing.py`
```python
# src/core/core_processing.py
class MessageProcessor:
    """Handles message processing, LLM calls, TTS"""
    
    def __init__(self, arvis_core):
        self.core = arvis_core
    
    def process_message(self, message: str, source: str = "user"):
        """
        Main message processing pipeline.
        
        Args:
            message: User message
            source: "user" | "voice" | "module"
        """
        if self.core.is_processing:
            self.core.logger.warning("Already processing, ignoring")
            return
        
        try:
            # Check permission
            if not self._check_permission(Permission.CHAT_USE):
                raise PermissionError("No permission for chat")
            
            # Set state
            self.core.is_processing = True
            self.core.generation_state = GenerationState.GENERATING
            self.core.processing_started.emit()
            
            # Try module commands first
            if not self._try_module_command(message):
                # Fallback to LLM
                self._handle_llm_request(message)
        
        except PermissionError as e:
            self.core.error_occurred.emit(f"Access denied: {e}")
        except Exception as e:
            self.core.logger.error(f"Message processing failed: {e}")
            self.core.error_occurred.emit(f"Processing failed: {e}")
        finally:
            self.core.is_processing = False
            self.core.processing_finished.emit()
    
    def process_voice_input(self, text: str):
        """Handle recognized voice input"""
        self.core.voice_message_recognized.emit(text)
        
        # Check if just the name without command
        if text.lower() in ["арвис", "jarvis"]:
            self.core.tts_engine.speak("Слушаю", stream=False)
            return
        
        # Process as normal message
        self.process_message(text, source="voice")
    
    def _try_module_command(self, message: str) -> bool:
        """
        Try to handle as module command.
        Returns: True if handled, False if should use LLM
        """
        message_lower = message.lower()
        
        # Check weather
        if any(word in message_lower for word in ["погода", "weather", "температура", "temperature"]):
            if self._check_permission(Permission.MODULE_WEATHER):
                result = self.core.weather_module.get_weather(message)
                self.core.response_ready.emit(result)
                return True
        
        # Check news
        if any(word in message_lower for word in ["новости", "news", "читай новости"]):
            if self._check_permission(Permission.MODULE_NEWS):
                result = self.core.news_module.get_news()
                self.core.response_ready.emit(result)
                return True
        
        # ... More module checks
        return False
    
    def _handle_llm_request(self, message: str):
        """Send request to LLM with streaming"""
        # Add to history
        self.core.conversation_history_manager.add_message("user", message)
        
        # Get conversation context
        messages = self.core.conversation_history_manager.get_messages(max_count=10)
        
        # Stream response
        full_response = ""
        try:
            for chunk in self.core.llm_client.stream_response(messages):
                full_response += chunk
                self.core.partial_response.emit(chunk)
                
                # Stream to TTS in parallel
                if len(full_response) >= 20:
                    self.core.tts_engine.speak_streaming(chunk, lambda _: None)
        
        except Exception as e:
            self.core.logger.error(f"LLM error: {e}")
            self.core.error_occurred.emit(f"LLM error: {e}")
        
        # Save full response
        if full_response:
            self.core.conversation_history_manager.add_message("assistant", full_response)
            self.core.response_ready.emit(full_response)
    
    def _check_permission(self, permission: Permission) -> bool:
        """Check if current user has permission"""
        if not self.core.rbac:
            return True  # RBAC disabled
        
        has_perm = self.core.rbac.has_permission(permission)
        if not has_perm and self.core.audit:
            self.core.audit.log_event(
                event_type=AuditEventType.PERMISSION_DENIED,
                severity=AuditSeverity.WARNING,
                details={"permission": permission.name}
            )
        return has_perm
```

**Шаг 4**: Создать `core_modules.py`
```python
# src/core/core_modules.py
class ModuleManager:
    """Manages all extension modules"""
    
    def __init__(self, arvis_core):
        self.core = arvis_core
    
    def init_modules_async(self):
        """Initialize all modules"""
        try:
            from modules.weather_module import WeatherModule
            from modules.news_module import NewsModule
            from modules.calendar_module import CalendarModule
            from modules.system_control import SystemControlModule
            from modules.search_module import SearchModule
            
            self.core.weather_module = WeatherModule(self.core.config)
            self.core.news_module = NewsModule(self.core.config)
            self.core.calendar_module = CalendarModule(self.core.config)
            self.core.system_control_module = SystemControlModule(self.core.config)
            self.core.search_module = SearchModule(self.core.config)
            
            self.core.logger.info("All modules initialized")
        except Exception as e:
            self.core.logger.error(f"Module initialization failed: {e}")
    
    def get_available_modules(self) -> List[str]:
        """List available modules"""
        modules = []
        if self.core.weather_module:
            modules.append("weather")
        if self.core.news_module:
            modules.append("news")
        if self.core.calendar_module:
            modules.append("calendar")
        if self.core.system_control_module:
            modules.append("system_control")
        if self.core.search_module:
            modules.append("search")
        return modules
```

**Шаг 5**: Создать `core_security.py`
```python
# src/core/core_security.py
class SecurityManager:
    """Handles RBAC, 2FA, audit logging"""
    
    def __init__(self, arvis_core):
        self.core = arvis_core
    
    def set_current_user(self, user_id: str, user_data: dict):
        """Set authenticated user"""
        self.core.current_user_id = user_id
        self.core.current_user = user_data
        
        if self.core.rbac:
            role = user_data.get("role", "user")
            self.core.rbac.set_role(Role[role.upper()])
        
        self._audit_log(AuditEventType.USER_LOGIN, AuditSeverity.INFO)
    
    def clear_current_user(self):
        """Clear user session"""
        if self.core.current_user_id:
            self._audit_log(AuditEventType.USER_LOGOUT, AuditSeverity.INFO)
        
        self.core.current_user_id = None
        self.core.current_user = None
    
    def _audit_log(self, event_type: AuditEventType, severity: AuditSeverity, details: dict = None):
        """Log audit event"""
        if not self.core.audit:
            return
        
        self.core.audit.log_event(
            event_type=event_type,
            severity=severity,
            user_id=self.core.current_user_id,
            details=details or {}
        )
```

**Шаг 6**: Создать `core_state.py`
```python
# src/core/core_state.py
class StateManager:
    """Manages state transitions and validation"""
    
    def __init__(self, arvis_core):
        self.core = arvis_core
    
    def transition_to(self, new_state: GenerationState):
        """Transition to new state with validation"""
        old_state = self.core.generation_state
        
        # Validate transition
        if not self._is_valid_transition(old_state, new_state):
            self.core.logger.warning(f"Invalid transition: {old_state} -> {new_state}")
            return False
        
        self.core.generation_state = new_state
        self.core.status_changed.emit({"state": new_state.value})
        
        return True
    
    def _is_valid_transition(self, old_state: GenerationState, new_state: GenerationState) -> bool:
        """Check if transition is valid"""
        # Define allowed transitions
        allowed = {
            GenerationState.IDLE: [GenerationState.GENERATING],
            GenerationState.GENERATING: [GenerationState.IDLE, GenerationState.REGENERATING, GenerationState.CANCELLED],
            GenerationState.REGENERATING: [GenerationState.GENERATING, GenerationState.IDLE],
            GenerationState.CANCELLED: [GenerationState.IDLE],
        }
        return new_state in allowed.get(old_state, [])
```

**Шаг 7**: Создать `__init__.py`
```python
# src/core/__init__.py
from .core_base import ArvisCore
from .core_components import ComponentInitializer
from .core_processing import MessageProcessor
from .core_modules import ModuleManager
from .core_security import SecurityManager
from .core_state import StateManager
from .core_voice import VoiceManager

__all__ = [
    "ArvisCore",
    "ComponentInitializer",
    "MessageProcessor",
    "ModuleManager",
    "SecurityManager",
    "StateManager",
    "VoiceManager",
]
```

**Шаг 8**: Мixin pattern для объединения
```python
# src/core/core_base.py (расширение)

class ArvisCore(QObject, ComponentInitializer, MessageProcessor, ModuleManager, SecurityManager, StateManager):
    """Combined core with all functionality"""
    
    def __init__(self, config: Config):
        super().__init__()
        # Base initialization
        self.config = config
        self.logger = ModuleLogger("ArvisCore")
        # ... rest of init
        
        # Initialize mixins
        ComponentInitializer.__init__(self, self)
        MessageProcessor.__init__(self, self)
        ModuleManager.__init__(self, self)
        SecurityManager.__init__(self, self)
        StateManager.__init__(self, self)
```

---

## FEATURE 5️⃣: Metrics Collector

### 5.1 Архитектура
```
utils/metrics_collector.py (Фасад)
├── MetricsCollector (singleton)
│   ├── collect_llm_metrics(latency, tokens, ...)
│   ├── collect_tts_metrics(synthesis_time, ...)
│   ├── collect_stt_metrics(recognition_time, ...)
│   ├── collect_system_metrics() → Dict
│   └── get_report() → Dict

utils/metrics/
├── __init__.py
├── base_metrics.py
│   └── MetricPoint (dataclass с timestamp)
├── performance_metrics.py
│   └── PerformanceMetrics (CPU, RAM, GPU, temps)
├── llm_metrics.py
│   └── LLMMetrics (TTFT, throughput, latency)
├── tts_metrics.py
│   └── TTSMetrics (synthesis_time, quality)
├── stt_metrics.py
│   └── STTMetrics (WER, recognition_time)
└── storage.py
    └── MetricsStorage (JSON/CSV с rolling, max 100MB)
```

### 5.2 Реализация

```python
# utils/metrics_collector.py
from typing import Dict, List, Any
import time
import json
from pathlib import Path

class MetricsCollector:
    """Singleton collector for all metrics"""
    _instance = None
    
    def __new__(cls, config: Config = None, logger = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, config: Config = None, logger = None):
        if self._initialized:
            return
        
        self.config = config
        self.logger = logger
        self.enabled = config.get("metrics.enabled", False) if config else False
        
        self.llm_metrics = {}
        self.tts_metrics = {}
        self.stt_metrics = {}
        self.perf_metrics = {}
        
        self._initialized = True
    
    def collect_llm_metrics(self, **kwargs):
        """
        Collect LLM metrics.
        
        Args:
            ttft_ms: Time to first token
            throughput: Tokens per second
            latency_ms: Average token latency
            total_tokens: Number of tokens generated
            model: Model name
        """
        if not self.enabled:
            return
        
        self.llm_metrics[time.time()] = {
            "ttft_ms": kwargs.get("ttft_ms"),
            "throughput": kwargs.get("throughput"),
            "latency_ms": kwargs.get("latency_ms"),
            "total_tokens": kwargs.get("total_tokens"),
            "model": kwargs.get("model")
        }
    
    def collect_tts_metrics(self, **kwargs):
        """Collect TTS metrics"""
        if not self.enabled:
            return
        
        self.tts_metrics[time.time()] = {
            "synthesis_time_ms": kwargs.get("synthesis_time_ms"),
            "text_length": kwargs.get("text_length"),
            "engine": kwargs.get("engine"),
            "sample_rate": kwargs.get("sample_rate")
        }
    
    def collect_stt_metrics(self, **kwargs):
        """Collect STT metrics"""
        if not self.enabled:
            return
        
        self.stt_metrics[time.time()] = {
            "recognition_time_ms": kwargs.get("recognition_time_ms"),
            "audio_duration_ms": kwargs.get("audio_duration_ms"),
            "confidence": kwargs.get("confidence"),
            "model": kwargs.get("model")
        }
    
    def collect_system_metrics(self) -> Dict[str, Any]:
        """Collect system performance metrics"""
        import psutil
        
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            
            return {
                "timestamp": time.time(),
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_mb": memory.used / (1024 * 1024),
                "memory_available_mb": memory.available / (1024 * 1024)
            }
        except Exception as e:
            self.logger.warning(f"Failed to collect system metrics: {e}")
            return {}
    
    def get_report(self) -> Dict[str, Any]:
        """Get comprehensive metrics report"""
        return {
            "timestamp": time.time(),
            "llm_metrics": self._aggregate_metrics(self.llm_metrics),
            "tts_metrics": self._aggregate_metrics(self.tts_metrics),
            "stt_metrics": self._aggregate_metrics(self.stt_metrics),
            "system_metrics": self.collect_system_metrics()
        }
    
    def _aggregate_metrics(self, metrics: Dict) -> Dict[str, Any]:
        """Aggregate metrics with averages and stats"""
        if not metrics:
            return {"count": 0}
        
        values = list(metrics.values())
        first_metric = values[0]
        
        result = {"count": len(values)}
        
        # Calculate averages
        for key in first_metric:
            if isinstance(first_metric[key], (int, float)):
                all_values = [m.get(key, 0) for m in values if isinstance(m.get(key), (int, float))]
                if all_values:
                    result[f"{key}_avg"] = sum(all_values) / len(all_values)
                    result[f"{key}_min"] = min(all_values)
                    result[f"{key}_max"] = max(all_values)
        
        return result
    
    def save_to_file(self, filepath: str = None):
        """Save metrics to JSON file"""
        if not filepath:
            filepath = self.config.get("metrics.storage_path", "logs/metrics.json")
        
        data = {
            "timestamp": time.time(),
            "llm_metrics": self.llm_metrics,
            "tts_metrics": self.tts_metrics,
            "stt_metrics": self.stt_metrics
        }
        
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)
```

### 5.3 Integration

```python
# Integrация в ArvisCore
from utils.metrics_collector import MetricsCollector

class ArvisCore:
    def __init__(self, config: Config):
        # ...
        self.metrics = MetricsCollector(config, self.logger)
    
    def _handle_llm_request(self, message: str):
        # ...
        start_time = time.time()
        token_count = 0
        
        for chunk in self.llm_client.stream_response(messages):
            token_count += 1
            # ...
        
        elapsed = (time.time() - start_time) * 1000
        throughput = token_count / (elapsed / 1000) if elapsed > 0 else 0
        
        self.metrics.collect_llm_metrics(
            ttft_ms=self.llm_client.stream_optimizer.monitor.get_ttft(),
            throughput=throughput,
            latency_ms=elapsed / token_count,
            total_tokens=token_count,
            model=self.config.get("llm.default_model")
        )
```

---

## FEATURE 6️⃣: Unit Tests (80% coverage)

### 6.1 Test Suite Structure

```
tests/
├── conftest.py (pytest fixtures)
├── unit/
│   ├── test_config.py (Config validation, loading, migration)
│   ├── test_rbac.py (Roles, permissions, inheritance)
│   ├── test_llm_client.py (Stream, timeout, errors)
│   ├── test_tts_factory.py (Engine creation, switching)
│   ├── test_health_check.py (All check types, status)
│   ├── test_metrics.py (Collection, aggregation, storage)
│   ├── test_message_processor.py (Module commands, LLM fallback)
│   ├── test_state_manager.py (State transitions)
│   └── test_security_manager.py (User auth, audit)
│
├── integration/
│   ├── test_llm_tts_integration.py
│   ├── test_voice_flow.py
│   └── test_module_commands.py
│
└── performance/
    ├── test_llm_streaming_performance.py
    ├── test_tts_performance.py
    └── test_stt_performance.py
```

### 6.2 Testing Examples

```python
# tests/unit/test_config.py
import pytest
from config.config import Config

class TestConfig:
    @pytest.fixture
    def config(self):
        return Config("tests/fixtures/config_test.json")
    
    def test_load_config(self, config):
        assert config is not None
        assert config.get("app.name") is not None
    
    def test_get_with_default(self, config):
        value = config.get("nonexistent.key", "default_value")
        assert value == "default_value"
    
    def test_set_and_get(self, config):
        config.set("test.key", "test_value")
        assert config.get("test.key") == "test_value"
    
    def test_config_validation(self, config):
        # Test invalid config doesn't break
        config.set("llm.temperature", 2.5)  # > 1.0
        # Should either clamp or warn
        assert config.get("llm.temperature") <= 1.0

# tests/unit/test_health_check.py
@pytest.mark.asyncio
async def test_health_check_stt(mock_stt_engine, health_checker):
    result = await health_checker.check_component("stt")
    assert result.component == "stt"
    assert result.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]

@pytest.mark.asyncio
async def test_health_check_all(mock_arvis_core, health_checker):
    results = await health_checker.check_all()
    assert len(results) > 0
    assert all(isinstance(r, HealthCheckResult) for r in results)
```

---

## FEATURE 7️⃣: Подготовка к PyQt6

### 7.1 Compatibility Layer

```python
# utils/qt_compat.py
"""Qt compatibility layer for PyQt5/PyQt6 migration"""

import sys

try:
    from PyQt5.QtCore import QObject, QThread, QTimer, pyqtSignal
    PYQT_VERSION = 5
except ImportError:
    from PyQt6.QtCore import QObject, QThread, QTimer, pyqtSignal
    PYQT_VERSION = 6

# Known breaking changes to check
BREAKING_CHANGES = {
    "pyqtSignal": "pyqtSignal signature unchanged",
    "QTimer": "QTimer.singleShot signature may differ",
    "QThread": "QThread.started signal behavior identical",
    "PyQt5.QtWidgets": "Moved to PyQt6.QtWidgets",
}

def get_pyqt_version() -> int:
    """Get active PyQt version"""
    return PYQT_VERSION

def check_compatibility(feature: str) -> bool:
    """Check if feature is compatible"""
    return feature in BREAKING_CHANGES
```

### 7.2 Breaking Changes Audit

```python
# tests/migration/pyqt6_compatibility_check.py
"""Check for PyQt6 breaking changes"""

import ast
import re
from pathlib import Path

class PyQt6CompatibilityChecker:
    PATTERNS = {
        # Old PyQt5 patterns
        r'from PyQt5.QtWidgets import.*': 'import OK, but check specific widgets',
        r'QThread\.currentThread': 'Use QThread.currentThread() - OK in both',
        r'pyqtSignal\(\s*int\s*,\s*str\s*\)': 'Signal signature OK',
        r'QTimer\.singleShot\(\s*0\s*,': 'Check if using Qt.QueuedConnection',
    }
    
    def check_file(self, filepath: str) -> List[str]:
        """Check file for PyQt6 issues"""
        with open(filepath, 'r') as f:
            content = f.read()
        
        issues = []
        for pattern, info in self.PATTERNS.items():
            if re.search(pattern, content):
                issues.append(f"{filepath}: {info}")
        
        return issues
    
    def check_project(self, project_root: str) -> Dict[str, List[str]]:
        """Check entire project"""
        results = {}
        for py_file in Path(project_root).rglob("*.py"):
            issues = self.check_file(str(py_file))
            if issues:
                results[str(py_file)] = issues
        
        return results
```

### 7.3 Migration Guide

```markdown
# PyQt5 → PyQt6 Migration Guide

## Установка PyQt6
```bash
pip uninstall PyQt5
pip install PyQt6 PyQt6-Qt6 PyQt6-sip
```

## Основные изменения
1. Import пути одинаковые (PyQt6.QtWidgets, etc.)
2. Signal/slot mechanism неизменен
3. QThread API неизменен
4. Требует Python 3.6+

## Тестирование
Перед миграцией:
- Запустить `python tests/migration/pyqt6_compatibility_check.py`
- Запустить все unit tests
- Проверить GUI вручную
```

---

## FEATURE 8️⃣: Улучшить конфигурацию

### 8.1 Config Validation with JSON Schema

```python
# utils/config_validator.py
import jsonschema
from pathlib import Path

CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "app": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "version": {"type": "string"},
                "debug": {"type": "boolean"}
            },
            "required": ["name"]
        },
        "llm": {
            "type": "object",
            "properties": {
                "default_model": {"type": "string"},
                "temperature": {"type": "number", "minimum": 0, "maximum": 1},
                "max_tokens": {"type": "integer", "minimum": 1}
            }
        },
        # ... More schema
    },
    "required": ["app"]
}

class ConfigValidator:
    def validate(self, config_data: dict) -> List[str]:
        """Validate config against schema"""
        try:
            jsonschema.validate(config_data, CONFIG_SCHEMA)
            return []
        except jsonschema.ValidationError as e:
            return [str(e)]

# utils/config_migrator.py
class ConfigMigrator:
    """Migrate old config formats to new"""
    
    def migrate_v1_5_to_v1_6(self, config: dict) -> dict:
        """Migrate config from 1.5 to 1.6"""
        # Handle legacy keys
        if "tts_engine" in config:
            config["tts"] = {"engine": config.pop("tts_engine")}
        
        # ... More migrations
        return config
```

### 8.2 CLI для управления конфигом

```python
# config/config_cli.py
import argparse

def main():
    parser = argparse.ArgumentParser(description="Arvis Config Manager")
    subparsers = parser.add_subparsers(dest="command")
    
    # get command
    get_parser = subparsers.add_parser("get", help="Get config value")
    get_parser.add_argument("key", help="Config key path (e.g., llm.temperature)")
    
    # set command
    set_parser = subparsers.add_parser("set", help="Set config value")
    set_parser.add_argument("key", help="Config key path")
    set_parser.add_argument("value", help="Value to set")
    
    # validate command
    subparsers.add_parser("validate", help="Validate config")
    
    # list command
    subparsers.add_parser("list", help="List all config keys")
    
    args = parser.parse_args()
    
    config = Config()
    
    if args.command == "get":
        value = config.get(args.key)
        print(f"{args.key} = {value}")
    elif args.command == "set":
        config.set(args.key, args.value)
        print(f"Set {args.key} = {args.value}")
    elif args.command == "validate":
        validator = ConfigValidator()
        errors = validator.validate(config.config_data)
        if errors:
            print("Validation errors:")
            for error in errors:
                print(f"  - {error}")
        else:
            print("Config is valid")

if __name__ == "__main__":
    main()
```

---

## FEATURE 9️⃣: Система Уведомлений

### 9.1 Архитектура

```
utils/notification_manager.py
├── NotificationLevel (CRITICAL > ERROR > WARNING > INFO > DEBUG)
├── NotificationChannel (UI, TTS, AUDIO, LOG, AUDIT)
├── NotificationManager (singleton)
│   ├── send(message, level, channels)
│   ├── send_async(...)
│   ├── set_rate_limit(max_per_minute)
│   └── get_history() → List[Notification]
│
src/gui/notification_center.py
├── NotificationCenterWidget
│   ├── Show notification toasts
│   ├── Display history
│   └── Settings for channels
```

### 9.2 Реализация

```python
# utils/notification_manager.py
from enum import Enum
from typing import List, Set
from dataclasses import dataclass
from datetime import datetime
import time

class NotificationLevel(Enum):
    DEBUG = 0
    INFO = 1
    WARNING = 2
    ERROR = 3
    CRITICAL = 4

class NotificationChannel(Enum):
    UI = "ui"
    TTS = "tts"
    AUDIO = "audio"
    LOG = "log"
    AUDIT = "audit"

@dataclass
class Notification:
    message: str
    level: NotificationLevel
    timestamp: float
    channel: NotificationChannel
    details: dict = None

class NotificationManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.notifications: List[Notification] = []
        self.max_history = 1000
        self.rate_limit = 60  # notifications per minute
        self._rate_limit_window = {}
        self._initialized = True
    
    def send(self, message: str, level: NotificationLevel = NotificationLevel.INFO,
             channels: Set[NotificationChannel] = None):
        """Send notification to specified channels"""
        if channels is None:
            channels = {NotificationChannel.LOG}
        
        # Rate limiting
        if not self._check_rate_limit():
            return False
        
        notification = Notification(
            message=message,
            level=level,
            timestamp=time.time(),
            channel=list(channels)[0] if channels else NotificationChannel.LOG
        )
        
        # Store in history
        self.notifications.append(notification)
        if len(self.notifications) > self.max_history:
            self.notifications.pop(0)
        
        # Send to channels
        for channel in channels:
            self._send_to_channel(notification, channel)
        
        return True
    
    def _send_to_channel(self, notification: Notification, channel: NotificationChannel):
        """Send to specific channel"""
        if channel == NotificationChannel.UI:
            # Emit Qt signal
            pass
        elif channel == NotificationChannel.TTS:
            # Use TTS to speak
            pass
        elif channel == NotificationChannel.AUDIO:
            # Play sound
            pass
        elif channel == NotificationChannel.LOG:
            # Log to file
            pass
        elif channel == NotificationChannel.AUDIT:
            # Log to audit
            pass
    
    def _check_rate_limit(self) -> bool:
        """Check if rate limit exceeded"""
        now = time.time()
        window_start = now - 60
        
        # Clean old entries
        self._rate_limit_window = {
            ts: count for ts, count in self._rate_limit_window.items()
            if ts > window_start
        }
        
        count = sum(self._rate_limit_window.values())
        return count < self.rate_limit
    
    def get_history(self, limit: int = 100) -> List[Notification]:
        """Get recent notifications"""
        return self.notifications[-limit:]
```

---

## 📋 Итоговый Чеклист для Phase 3

- [ ] TTS Factory реализована и протестирована
- [ ] LLM Streaming Optimizer интегрирован (TTFT < 500ms)
- [ ] Health Checks система запущена и мониторит
- [ ] arvis_core.py разбита на модули (< 400 строк каждый)
- [ ] Metrics Collector собирает данные о производительности
- [ ] 80%+ code coverage для core modules
- [ ] PyQt6 compatibility check tool готов
- [ ] Config validation и migration реализованы
- [ ] Notification system развернута
- [ ] Все документы обновлены
- [ ] Version bumped to 1.6.0
- [ ] Все коммиты рассмотрены и merged

---

**Document version**: 1.0 | **Updated**: 21 October 2025
