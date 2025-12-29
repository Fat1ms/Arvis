# 🎯 ПОЛНЫЙ ПЛАН РЕФАКТОРИНГА ЯДРА (Arvis Core) — v2.0

**Статус:** 🚀 В процессе  
**Цель:** Уменьшить `arvis_core.py` с ~1145 строк до ~400-500 строк через вынос в модульные контроллеры  
**Критерии готовности:**
- Ядро содержит только **orchestration logic** (запуск, координация, сигналы)
- Каждый контроллер отвечает за **одну область**
- Все контроллеры покрыты unit-тестами
- Нет потери функциональности, 100% обратная совместимость

---

## 📐 АРХИТЕКТУРА (целевая)

```
ArvisCore (orchestrator, ~400-500 строк)
├── UIConnector        # Сигналы, состояние, статус (NEW)
├── LifecycleManager   # Init, cleanup (NEW)
├── TTSController      # ✅ DONE
├── WakeController     # ✅ DONE
├── LLMPipeline        # ✅ DONE (external module)
├── STTController      # TODO
├── ModuleController   # TODO
├── SearchController   # TODO
└── VoiceAssetsManager # TODO
```

---

## 🔄 РЕАЛИЗАЦИЯ (Phase 1 → 4)

### **PHASE 1: Инвентаризация (DONE) ✅**

**Что разобрано:**
- ✅ `llm_pipeline.py` — LLM обработка, потоковость, автопродолжение
- ✅ `wake_controller.py` — активация ключевого слова, name-only responses
- ✅ `tts_controller.py` — управление TTS для Live Mode

**Осталось в ядре (~1100 строк):**
- Voice input: STT, запись, распознавание
- Voice assets: preload, cache, ack phrases
- Модули: weather, news, system control, calendar, search
- TTS: fallback, health check, switch engine
- Состояние: генерация, обработка, streaming
- Инициализация, сигналы, таймеры

---

### **PHASE 2: STT & Voice Input Controller (NEXT) 🔴**

**Вынести из ядра (~200-250 строк):**

**Файл:** `src/core/stt_controller.py`

**Методы из ядра:**
```python
# Переносим:
- toggle_voice_recording(source)
- _set_voice_recording(active)
- process_voice_input(text)
- _respond_to_name_only()
- _restart_wake_listening_if_enabled()  # уже в wake_controller, синхронизация
- (внутренние helper для name-only проверки)
```

**Новый интерфейс:**
```python
class STTController:
    def __init__(self, core):
        self.core = core
        
    def start_recording(self, source="user") -> None
    def stop_recording(self) -> None
    def process_voice_input(text: str) -> None
    
    @property
    def is_recording(self) -> bool
    
    def _check_if_name_only(text: str) -> bool
    def _prepare_to_process_message(text: str) -> None
```

**Зависимости:**
- config (voice.wake_word, voice.name_responses)
- stt_engine (start/stop_recording)
- core.is_voice_recording, core.process_message()
- core.error_occurred, core.voice_message_recognized сигналы

**Тесты:** `tests/unit/test_stt_controller.py` (5-7 тестов)

---

### **PHASE 3: Voice Assets Manager (200 строк)**

**Вынести из ядра:**

**Файл:** `src/core/voice_assets_manager.py`

**Методы из ядра:**
```python
# Переносим:
- _prime_name_ack_cache_async(initial)
- _schedule_ack_cache_refill()
- _handle_initial_ack_ready(success)
- _take_preloaded_ack_audio(phrase)
- _collect_ack_phrases()  # перемещена в wake_controller, синхронизируем
- _maybe_play_ready_greeting(force)
- _on_stt_model_ready(model_path)
```

**Новый интерфейс:**
```python
class VoiceAssetsManager:
    def __init__(self, core):
        ...
        
    def prime_assets_async(self, initial=False) -> None
        """Preload acknowledgement phrases."""
        
    def get_ack_audio(self, phrase: str) -> Optional[bytes]
        """Fetch pre-rendered audio if available."""
        
    def play_ready_greeting(self) -> None
        """Announce readiness once all assets loaded."""
        
    def on_stt_model_ready(self, model_path: str) -> None
        """React to STT model readiness."""
        
    @property
    def is_ready(self) -> bool
        """All voice assets and models loaded."""
```

**Зависимости:**
- tts_engine (preload_phrases, speak)
- config (voice.ready_phrase, voice.wake_ack)
- task_manager (async preload)
- core.status_changed, core.voice_assets_ready сигналы

**Тесты:** `tests/unit/test_voice_assets_manager.py` (5-6 тестов)

---

### **PHASE 4: Module Controller (150-200 строк)**

**Вынести из ядра:**

**Файл:** `src/core/module_controller.py`

**Методы из ядра:**
```python
# Переносим:
- handle_module_commands(message) -> Optional[str]
- init_modules()
- Вся логика погоды, новостей, системного контроля, календаря, поиска
```

**Новый интерфейс:**
```python
class ModuleController:
    def __init__(self, core, config):
        self.core = core
        self.weather_module = ...
        self.news_module = ...
        self.system_control_module = ...
        self.calendar_module = ...
        self.search_module = ...
        
    def handle_command(self, message: str) -> Optional[str]
        """Route message to appropriate module."""
        
    def initialize_all(self) -> None
        """Initialize all available modules."""
        
    @property
    def search_enabled(self) -> bool
        """Check if web search is available."""
        
    def get_search_payload(self) -> Optional[Dict]
        """Return pending search results if any."""
```

**Зависимости:**
- weather, news, calendar, system_control, search modules
- config (модули.enabled)
- core._pending_search_results (через метод/свойство)
- core.error_occurred сигнал

**Тесты:** `tests/unit/test_module_controller.py` (3-4 теста)

---

### **PHASE 5: TTS Management Controller (300-400 строк)**

**Вынести из ядра:**

**Файл:** `src/core/tts_manager.py`

**Методы из ядра:**
```python
# Переносим:
- _negotiate_engine_with_server()
- _build_engine_priority_list()
- _create_tts_engine_with_fallback()
- switch_tts_engine_async()
- get_system_info()  # частично
```

**Новый интерфейс:**
```python
class TTSManager:
    def __init__(self, core, config, logger):
        self.core = core
        self._tts_engine = None
        self._tts_engine_type = "silero"
        self._priority_list = []
        
    def initialize_engine(self) -> Optional[TTSEngineBase]
        """Create and initialize default TTS engine with fallback."""
        
    async def switch_engine_async(self, engine_type: str) -> bool
        """Switch to different TTS engine at runtime."""
        
    def get_current_engine(self) -> Optional[TTSEngineBase]
        
    @property
    def engine_type(self) -> str
        
    @property
    def is_healthy(self) -> bool
```

**Зависимости:**
- tts_factory
- config (tts.*)
- core.tts_engine_switched сигнал

**Тесты:** `tests/unit/test_tts_manager.py` (4-5 тестов)

---

### **PHASE 6: UI Connector (Signals & State) (200 строк)**

**Вынести/консолидировать:**

**Файл:** `src/core/ui_connector.py`

**Содержит:**
```python
class UIConnector:
    """Handles all PyQt signals and UI state synchronization."""
    
    def __init__(self, core):
        # Все сигналы из ArvisCore
        self.response_ready = pyqtSignal(str)
        self.partial_response = pyqtSignal(str)
        self.processing_started = pyqtSignal()
        self.processing_finished = pyqtSignal()
        self.status_changed = pyqtSignal(dict)
        self.error_occurred = pyqtSignal(str)
        self.voice_activation_detected = pyqtSignal()
        self.voice_message_recognized = pyqtSignal(str)
        self.components_initialized = pyqtSignal()
        self.stt_model_ready = pyqtSignal(str)
        self.voice_assets_ready = pyqtSignal()
        self.tts_engine_switched = pyqtSignal(str)
        
    def emit_response(self, text: str) -> None
    def emit_error(self, error: str) -> None
    def emit_status(self, status_dict: Dict) -> None
    # ... и т.д.
```

**Зависимости:**
- PyQt6.QtCore (QObject, pyqtSignal)

**Тесты:** `tests/unit/test_ui_connector.py` (2-3 теста)

---

### **PHASE 7: Lifecycle Manager (150 строк)**

**Вынести инициализацию и cleanup:**

**Файл:** `src/core/lifecycle_manager.py`

**Содержит:**
```python
class LifecycleManager:
    def __init__(self, core):
        self.core = core
        
    def initialize(self) -> None
        """Full initialization: components, modules, assets."""
        
    def shutdown(self) -> None
        """Graceful cleanup: stop timers, close connections."""
        
    def _setup_timers(self) -> None
        """Initialize all periodic timers (status, housekeeping, etc)."""
        
    def _setup_housekeeping(self) -> None
        """Periodic cleanup of logs and temp files."""
```

**Тесты:** `tests/unit/test_lifecycle_manager.py` (2 теста)

---

## 📊 ИТОГОВЫЕ МЕТРИКИ

| Компонент | Строк | Статус | Покрытие |
|-----------|-------|--------|---------|
| llm_pipeline.py | ~320 | ✅ | 5/5 tests |
| wake_controller.py | ~270 | ✅ | 5/5 tests |
| tts_controller.py | ~80 | ✅ | - |
| stt_controller.py | ~200 | 🔴 | 0/7 |
| voice_assets_manager.py | ~250 | 🔴 | 0/6 |
| module_controller.py | ~180 | 🔴 | 0/4 |
| tts_manager.py | ~350 | 🔴 | 0/5 |
| ui_connector.py | ~150 | 🔴 | 0/3 |
| lifecycle_manager.py | ~150 | 🔴 | 0/2 |
| **arvis_core.py** | **~450** | 🔴 | - |
| **ИТОГО** | **~2000** | - | **~20-25 tests** |

**Было:** 1145 строк в arvis_core.py  
**Будет:** ~450 строк в arvis_core.py  
**Итого модулей:** ~2000 строк (но более чистая, тестируемая архитектура)

---

## ✅ КРИТЕРИИ ГОТОВНОСТИ

- [ ] Все фазы 1-7 реализованы
- [ ] Каждый контроллер имеет unit-тесты
- [ ] Нет регрессии функционала (все работает как раньше)
- [ ] arvis_core.py содержит только orchestration
- [ ] Все импорты корректны
- [ ] Документация обновлена

---

## 🚀 ЗАПУСК

**Порядок выполнения:**
1. ✅ Phase 1 (инвентаризация) — DONE
2. 🔴 Phase 2 (STT Controller) — NEXT
3. 🔴 Phase 3 (Voice Assets Manager)
4. 🔴 Phase 4 (Module Controller)
5. 🔴 Phase 5 (TTS Manager)
6. 🔴 Phase 6 (UI Connector)
7. 🔴 Phase 7 (Lifecycle Manager)
8. 🎯 Final cleanup & validation

---

**Начинаю Phase 2 прямо сейчас...**
