# 🚀 Phase 3: Расширенные возможности и оптимизация
## Полный план реализации (октябрь-декабрь 2025)

**Версия документа**: 1.0  
**Дата**: 21 октября 2025  
**Статус**: 🟡 В начале реализации  
**Версия приложения**: v1.5.1 → v1.6.0  

---

## 📋 Оглавление
1. [Обзор Phase 3](#обзор-phase-3)
2. [Фичи и их приоритеты](#фичи-и-их-приоритеты)
3. [Детальные планы реализации](#детальные-планы-реализации)
4. [Зависимости и последовательность](#зависимости-и-последовательность)
5. [Testing Strategy](#testing-strategy)
6. [Git Workflow](#git-workflow)
7. [Timelines](#timelines)
8. [Post-Implementation Checklist](#post-implementation-checklist)

---

## 🎯 Обзор Phase 3

### Цели
- **Производительность**: Оптимизация LLM streaming для Gemma 2B и TTS buffering
- **Reliability**: Система health checks и metrics для мониторинга
- **Maintainability**: Разделение monolithic arvis_core.py на модули
- **Quality**: Полное покрытие unit tests (80%+)
- **Future-proofing**: Подготовка к PyQt6 и улучшения конфигурации

### Key Metrics (целевые)
- TTFT (Time To First Token): < 500ms (Gemma 2B)
- Throughput: > 15 tokens/sec (Gemma 2B)
- Health check duration: < 3 sec (all checks)
- Test coverage: ≥ 80% для core modules
- Code complexity: arvis_core.py в 5 файлах < 400 строк каждый

---

## 🔥 Фичи и их приоритеты

| # | Фича | Приоритет | Сложность | Est. Days | Зависит от |
|---|------|-----------|-----------|----------|-----------|
| 1 | Bark TTS Factory pattern | 🔴 HIGH | ⭐⭐⭐ | 5 | - |
| 2 | Оптимизация LLM streaming | 🔴 HIGH | ⭐⭐⭐ | 6 | LLMClient |
| 3 | Health checks система | 🟡 MEDIUM | ⭐⭐ | 4 | STT, TTS, LLM |
| 4 | Разделить arvis_core.py | 🟡 MEDIUM | ⭐⭐⭐⭐ | 7 | - |
| 5 | Metrics collector | 🟡 MEDIUM | ⭐⭐ | 4 | Health checks |
| 6 | Unit tests (80%) | 🟡 MEDIUM | ⭐⭐ | 8 | 1-5 |
| 7 | Подготовка PyQt6 | 🔵 LOW | ⭐⭐ | 3 | - |
| 8 | Улучшить конфиг | 🔵 LOW | ⭐⭐ | 4 | - |
| 9 | Система уведомлений | 🔵 LOW | ⭐⭐ | 3 | - |

**Рекомендуемый порядок реализации**:
1. Фича #1 (TTS Factory) — фундамент для остальных TTS-related
2. Фича #2 (LLM streaming) — критично для производительности
3. Фича #3 (Health checks) — нужна для #5
4. Фича #4 (arvis_core split) — параллельно #2-3
5. Фича #5 (Metrics) — использует results из #1-3
6. Фича #6 (Tests) — после #1-5, покрывает все
7. Фичи #7-9 — параллельно в конце

---

## 📐 Детальные планы реализации

### FEATURE 1️⃣: Bark TTS Factory Pattern

#### 1.1 Архитектура
```
modules/tts_factory.py
├── TTSFactory (class)
│   ├── create_engine(engine_name, config) → TTSEngineBase
│   ├── list_available_engines() → List[str]
│   └── validate_engine_config(engine_name, config) → bool
│
├── TTSEngineBase (abstract)
│   ├── speak(text, stream=False)
│   ├── speak_streaming(text, chunk_callback)
│   ├── stop()
│   ├── get_status() → Dict
│   └── get_config() → Dict
│
├── SileroTTSEngine (existing, refactored)
├── BarkTTSEngine (new)
├── SAPITTSEngine (existing, refactored)
└── MockTTSEngine (for testing)

modules/bark_tts_engine.py
├── BarkTTSEngine
│   ├── __init__(config, logger)
│   ├── _load_model_async() → Future
│   ├── speak(text, stream=False) → bool
│   ├── speak_streaming(text, chunk_callback)
│   ├── _synthesize_with_bark(text) → np.ndarray
│   ├── _stream_audio(audio_data, chunk_callback)
│   └── health_check() → HealthCheckResult
```

#### 1.2 Требования к Bark
```
Установка:
pip install bark transformers[torch] soundfile numpy scipy torch torchaudio

Модель будет скачана при первом использовании (~2 GB)
Кеширование в ~/.cache/huggingface/

Config параметры (config.json):
{
  "tts": {
    "engine": "bark",  // "silero", "sapi", "bark"
    "bark": {
      "device": "cuda",  // "cpu", "cuda", "mps"
      "precision": "float32",  // "float32", "float16"
      "sample_rate": 24000,
      "chunk_duration_ms": 500,
      "voice": "v2/en_speaker_6",
      "temperature": 0.6,
      "top_p": 0.9,
      "top_k": 50
    }
  }
}
```

#### 1.3 Реализация шаги

**Шаг 1**: Создать абстрактный базовый класс
```python
# modules/tts_factory.py
class TTSEngineBase(ABC):
    @abstractmethod
    def speak(self, text: str, stream: bool = False) -> bool:
        """Синтезировать и проиграть текст"""
        
    @abstractmethod
    def speak_streaming(self, text: str, chunk_callback: Callable) -> bool:
        """Потоковый синтез с callback'ом"""
        
    @abstractmethod
    def stop(self) -> None:
        """Остановить воспроизведение"""
        
    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Получить статус engine'а"""
        
    def health_check(self) -> HealthCheckResult:
        """Проверка здоровья (может быть переопределена)"""
        return HealthCheckResult(
            component="tts",
            status=HealthStatus.HEALTHY,
            message="TTS engine ready"
        )
```

**Шаг 2**: Refactor существующих engines
- Refactor `SileroTTSEngine` ← наследует `TTSEngineBase`
- Refactor `SAPITTSEngine` ← наследует `TTSEngineBase`
- Добавить `speak_streaming()` в `SileroTTSEngine` (если нет)

**Шаг 3**: Реализовать BarkTTSEngine
```python
# modules/bark_tts_engine.py
class BarkTTSEngine(TTSEngineBase):
    def __init__(self, config: Config, logger):
        self.config = config
        self.logger = logger
        self.model = None
        self.processor = None
        self.device = config.get("tts.bark.device", "cpu")
        self._is_speaking = False
        
        # Асинхронная загрузка модели
        self._load_model_async()
    
    def _load_model_async(self):
        """Загрузить модель в фоновом потоке"""
        from utils.async_manager import task_manager
        
        def load():
            try:
                from bark import SAMPLE_RATE, generate_audio, preload_models
                preload_models(device=self.device)
                self.logger.info(f"Bark model loaded on {self.device}")
                return True
            except Exception as e:
                self.logger.error(f"Failed to load Bark: {e}")
                return False
        
        task_manager.run_async("bark_load", load)
    
    def speak_streaming(self, text: str, chunk_callback: Callable[[bytes], None]) -> bool:
        """Потоковый синтез Bark"""
        from bark import SAMPLE_RATE, generate_audio
        import soundfile as sf
        import io
        
        if not self.model:
            self.logger.warning("Bark model not loaded yet")
            return False
        
        try:
            # Синтез полного текста (для Bark не поддерживается streaming, только чанки по предложениям)
            audio_array = generate_audio(
                text,
                voice_preset=self.config.get("tts.bark.voice", "v2/en_speaker_6"),
                temperature=self.config.get("tts.bark.temperature", 0.6)
            )
            
            # Стримим аудио чанками
            self._stream_audio(audio_array, chunk_callback, SAMPLE_RATE)
            return True
        except Exception as e:
            self.logger.error(f"Bark synthesis failed: {e}")
            return False
    
    def _stream_audio(self, audio_array, chunk_callback, sample_rate):
        """Стримить аудио массив чанками"""
        chunk_samples = int(sample_rate * self.config.get("tts.bark.chunk_duration_ms", 500) / 1000)
        
        for i in range(0, len(audio_array), chunk_samples):
            chunk = audio_array[i:i+chunk_samples]
            # Конвертировать в PCM bytes
            pcm_bytes = (chunk * 32767).astype(np.int16).tobytes()
            chunk_callback(pcm_bytes)
            self._is_speaking = True
        
        self._is_speaking = False
```

**Шаг 4**: Реализовать Factory
```python
# modules/tts_factory.py
class TTSFactory:
    _engines = {
        "silero": "modules.silero_tts_engine:SileroTTSEngine",
        "bark": "modules.bark_tts_engine:BarkTTSEngine",
        "sapi": "modules.system_tts:SAPITTSEngine",
    }
    
    @classmethod
    def create_engine(cls, engine_name: str, config: Config, logger) -> TTSEngineBase:
        """Создать TTS engine по имени"""
        if engine_name not in cls._engines:
            raise ValueError(f"Unknown TTS engine: {engine_name}")
        
        # Dynamic import
        module_path, class_name = cls._engines[engine_name].rsplit(":", 1)
        module = __import__(module_path, fromlist=[class_name])
        engine_class = getattr(module, class_name)
        
        return engine_class(config, logger)
    
    @classmethod
    def list_available_engines(cls) -> List[str]:
        """Список доступных engines"""
        return list(cls._engines.keys())
```

**Шаг 5**: Обновить ArvisCore
```python
# src/core/arvis_core.py
def init_tts_engine_async(self):
    """Инициализировать TTS engine через factory"""
    from modules.tts_factory import TTSFactory
    
    engine_name = self.config.get("tts.engine", "silero")
    try:
        self.tts_engine = TTSFactory.create_engine(engine_name, self.config, self.logger)
        self.logger.info(f"TTS engine initialized: {engine_name}")
    except Exception as e:
        self.logger.error(f"Failed to initialize TTS: {e}")
        self.error_occurred.emit(f"TTS initialization failed: {e}")
```

#### 1.4 Testing для TTS Factory
```python
# tests/unit/test_tts_factory.py
import pytest
from modules.tts_factory import TTSFactory, TTSEngineBase
from config.config import Config

class TestTTSFactory:
    def test_create_engine_silero(self):
        """Создать Silero engine"""
        config = Config()
        engine = TTSFactory.create_engine("silero", config, logger)
        assert isinstance(engine, TTSEngineBase)
    
    def test_create_engine_bark(self):
        """Создать Bark engine"""
        config = Config()
        config.set("tts.bark.device", "cpu")  # Быстрее на тестах
        engine = TTSFactory.create_engine("bark", config, logger)
        assert isinstance(engine, TTSEngineBase)
    
    def test_create_engine_invalid(self):
        """Исключение на неверном engine"""
        with pytest.raises(ValueError):
            TTSFactory.create_engine("invalid", config, logger)
    
    def test_list_available_engines(self):
        """Проверить список доступных engines"""
        engines = TTSFactory.list_available_engines()
        assert "silero" in engines
        assert "bark" in engines
    
    @pytest.mark.slow
    def test_bark_speak_streaming(self):
        """Тест потокового синтеза Bark"""
        config = Config()
        config.set("tts.bark.device", "cpu")
        engine = TTSFactory.create_engine("bark", config, logger)
        
        chunks = []
        def on_chunk(data):
            chunks.append(data)
        
        result = engine.speak_streaming("Hello world", on_chunk)
        assert result is True
        assert len(chunks) > 0
```

---

### FEATURE 2️⃣: Оптимизация LLM Streaming для Gemma 2B

#### 2.1 Проблема и решение

**Проблема**:
- Первый токен приходит ~800ms (TTFT high)
- Пропускная способность < 10 tokens/sec на Gemma 2B
- UI зависает при стриминге больших ответов
- Buffering не оптимален для медленных генераций

**Решение**:
- Adaptive buffering (минимум 20 символов ИЛИ граница слова)
- Batch processing для улучшения throughput
- Кеширование КВИН/значений для ускорения
- Quantization detection для выбора оптимальных параметров
- Async buffering без блокировки UI

#### 2.2 Архитектура
```
modules/llm_streaming_optimizer.py
├── LLMStreamingOptimizer (class)
│   ├── optimize_stream(stream_generator, config) → Generator
│   ├── detect_quantization(model_path) → str
│   ├── calculate_optimal_batch_size(model_info) → int
│   ├── get_performance_stats() → Dict
│   └── reset_stats()
│
└── StreamBuffer
    ├── add_chunk(text: str)
    ├── get_buffer() → str  (if min_size or boundary reached)
    ├── flush() → str
    └── is_ready() → bool

modules/llm_performance_monitor.py
├── LLMPerformanceMonitor
│   ├── track_token(token_num, time, token_text)
│   ├── get_ttft() → float (Time To First Token)
│   ├── get_throughput() → float (tokens/sec)
│   ├── get_latency() → float (avg token latency)
│   └── get_report() → Dict
```

#### 2.3 Реализация

**Шаг 1**: Создать Stream Buffer с adaptive logic
```python
# modules/llm_streaming_optimizer.py
class StreamBuffer:
    MIN_CHUNK_SIZE = 20  # символов
    WORD_BOUNDARIES = {'.', ',', '!', '?', ';', ':', '\n', ' '}
    
    def __init__(self, min_size: int = 20, word_boundary: bool = True):
        self.min_size = min_size
        self.word_boundary = word_boundary
        self.buffer = ""
    
    def add_chunk(self, text: str) -> Optional[str]:
        """
        Добавить чанк текста.
        Вернуть готовый буфер если:
        1. Достаточно символов (>= min_size) И последний символ на границе слова
        2. Или просто достаточно символов и word_boundary=False
        """
        self.buffer += text
        
        if len(self.buffer) >= self.min_size:
            if self.word_boundary:
                # Найти последнюю границу слова
                for i in range(len(self.buffer) - 1, -1, -1):
                    if self.buffer[i] in self.WORD_BOUNDARIES:
                        result = self.buffer[:i+1]
                        self.buffer = self.buffer[i+1:]
                        return result
                # Если нет границы, все равно вернуть если слишком много
                if len(self.buffer) > self.min_size * 2:
                    return self.buffer
            else:
                result = self.buffer[:self.min_size]
                self.buffer = self.buffer[self.min_size:]
                return result
        return None
    
    def flush(self) -> str:
        """Вернуть оставшиеся данные"""
        result = self.buffer
        self.buffer = ""
        return result
    
    def is_empty(self) -> bool:
        return len(self.buffer) == 0
```

**Шаг 2**: Создать Performance Monitor
```python
# modules/llm_performance_monitor.py
import time
from typing import List, Tuple

class LLMPerformanceMonitor:
    def __init__(self):
        self.tokens: List[Tuple[int, float, str]] = []  # (num, timestamp, text)
        self.start_time = None
        self.first_token_time = None
    
    def start_generation(self):
        """Начать отслеживание"""
        self.tokens.clear()
        self.start_time = time.time()
        self.first_token_time = None
    
    def track_token(self, token_num: int, token_text: str):
        """Отследить токен"""
        current_time = time.time()
        self.tokens.append((token_num, current_time, token_text))
        
        if token_num == 1 and not self.first_token_time:
            self.first_token_time = current_time
    
    def get_ttft(self) -> float:
        """Time To First Token (мс)"""
        if not self.first_token_time or not self.start_time:
            return 0.0
        return (self.first_token_time - self.start_time) * 1000
    
    def get_throughput(self) -> float:
        """Токены в секунду"""
        if len(self.tokens) < 2:
            return 0.0
        
        first_token_time = self.tokens[0][1]
        last_token_time = self.tokens[-1][1]
        elapsed = last_token_time - first_token_time
        
        if elapsed == 0:
            return 0.0
        
        token_count = len(self.tokens)
        return token_count / elapsed
    
    def get_latency(self) -> float:
        """Средняя задержка токена (мс)"""
        if len(self.tokens) < 2:
            return 0.0
        
        total_time = self.tokens[-1][1] - self.tokens[0][1]
        token_count = len(self.tokens) - 1
        
        return (total_time / token_count * 1000) if token_count > 0 else 0.0
    
    def get_report(self) -> dict:
        """Полный отчет о производительности"""
        return {
            "ttft_ms": round(self.get_ttft(), 2),
            "throughput_tokens_per_sec": round(self.get_throughput(), 2),
            "avg_token_latency_ms": round(self.get_latency(), 2),
            "total_tokens": len(self.tokens),
            "total_text": "".join(t[2] for t in self.tokens)
        }
```

**Шаг 3**: Реализовать Streaming Optimizer
```python
# modules/llm_streaming_optimizer.py
class LLMStreamingOptimizer:
    def __init__(self, config: Config, logger):
        self.config = config
        self.logger = logger
        self.monitor = LLMPerformanceMonitor()
        self.enabled = config.get("llm.stream_optimization_enabled", True)
    
    def optimize_stream(self, stream_generator, model_info: dict = None):
        """
        Обертка для stream generator с оптимизацией.
        Yields: tuple (token_text, buffered_text_ready)
        """
        if not self.enabled:
            # Проходим поток как есть
            for chunk in stream_generator:
                yield chunk
            return
        
        buffer = StreamBuffer(
            min_size=self.config.get("llm.buffer_threshold", 20),
            word_boundary=True
        )
        
        token_num = 0
        self.monitor.start_generation()
        
        try:
            for chunk in stream_generator:
                token_num += 1
                self.monitor.track_token(token_num, chunk)
                
                # Добавить в буфер и получить готовый текст
                ready_text = buffer.add_chunk(chunk)
                
                if ready_text:
                    yield ready_text
            
            # Вернуть оставшиеся данные
            remaining = buffer.flush()
            if remaining:
                yield remaining
        
        except Exception as e:
            self.logger.error(f"Stream optimization error: {e}")
            # Сбросить буфер при ошибке
            remaining = buffer.flush()
            if remaining:
                yield remaining
        
        finally:
            # Логировать производительность
            report = self.monitor.get_report()
            self.logger.debug(f"LLM Performance: {report}")
    
    def detect_quantization(self, model_path: str) -> str:
        """
        Определить, квантизирована ли модель.
        Возвращает: "float32", "float16", "int8", "unknown"
        """
        # Проверить сигнатуру файла или метаинформацию
        try:
            import os
            if not os.path.exists(model_path):
                return "unknown"
            
            # Простая эвристика: проверить размер
            size_mb = os.path.getsize(model_path) / (1024 * 1024)
            
            # Примерные размеры для Gemma 2B
            if size_mb < 1000:
                return "int8"  # Квантизирована
            elif size_mb < 5000:
                return "float16"
            else:
                return "float32"
        except Exception as e:
            self.logger.warning(f"Failed to detect quantization: {e}")
            return "unknown"
    
    def calculate_optimal_batch_size(self, model_info: dict) -> int:
        """
        Вычислить оптимальный размер батча на основе ресурсов.
        
        Args:
            model_info: {"vram_mb": 2000, "quantization": "float16", ...}
        """
        vram_mb = model_info.get("vram_mb", 2000)
        quantization = model_info.get("quantization", "float16")
        
        # Базовый размер батча в зависимости от квантизации
        base_batch = {"float32": 1, "float16": 2, "int8": 4}.get(quantization, 1)
        
        # Масштабировать в зависимости от VRAM
        if vram_mb >= 8000:
            return base_batch * 4
        elif vram_mb >= 4000:
            return base_batch * 2
        else:
            return base_batch
    
    def get_performance_stats(self) -> dict:
        """Получить статистику производительности"""
        return self.monitor.get_report()
    
    def reset_stats(self):
        """Сбросить статистику"""
        self.monitor = LLMPerformanceMonitor()
```

**Шаг 4**: Интеграция в LLMClient
```python
# modules/llm_client.py (модификация в stream_response)

def stream_response(self, messages, **kwargs):
    """
    Stream response with optimization.
    """
    if not hasattr(self, 'stream_optimizer'):
        from modules.llm_streaming_optimizer import LLMStreamingOptimizer
        self.stream_optimizer = LLMStreamingOptimizer(self.config, self.logger)
    
    # Получить сырой поток от Ollama
    raw_stream = self._get_ollama_stream(messages, **kwargs)
    
    # Оптимизировать поток
    optimized_stream = self.stream_optimizer.optimize_stream(raw_stream)
    
    for chunk in optimized_stream:
        yield chunk
```

**Шаг 5**: Config параметры
```json
{
  "llm": {
    "stream_optimization_enabled": true,
    "buffer_threshold": 20,
    "word_boundary_buffering": true,
    "batch_size": "auto",
    "cache_kv": true,
    "cache_size_mb": 512
  }
}
```

#### 2.4 Testing для LLM Streaming
```python
# tests/unit/test_llm_streaming_optimizer.py
import pytest
from modules.llm_streaming_optimizer import StreamBuffer, LLMStreamingOptimizer

class TestStreamBuffer:
    def test_buffer_adds_chunk(self):
        buf = StreamBuffer(min_size=20, word_boundary=False)
        result = buf.add_chunk("Hello ")
        assert result is None  # Недостаточно
        
        result = buf.add_chunk("world this is a test!")
        assert result is not None
        assert len(result) >= 20
    
    def test_buffer_respects_word_boundary(self):
        buf = StreamBuffer(min_size=5, word_boundary=True)
        result = buf.add_chunk("Hello")
        assert result is None  # Нет границы
        
        result = buf.add_chunk(" ")
        assert result is not None
        assert result.endswith(" ")
    
    def test_buffer_flush(self):
        buf = StreamBuffer()
        buf.add_chunk("Hello")
        result = buf.flush()
        assert result == "Hello"
        assert buf.is_empty()

class TestLLMPerformanceMonitor:
    def test_ttft_calculation(self):
        monitor = LLMPerformanceMonitor()
        monitor.start_generation()
        
        import time
        time.sleep(0.1)
        monitor.track_token(1, "Hello")
        
        ttft = monitor.get_ttft()
        assert ttft >= 100  # Минимум 100ms
        assert ttft < 1000  # Максимум 1 сек
    
    def test_throughput_calculation(self):
        monitor = LLMPerformanceMonitor()
        monitor.start_generation()
        
        # Добавить несколько токенов
        import time
        for i in range(10):
            monitor.track_token(i, f"token{i}")
            time.sleep(0.01)
        
        throughput = monitor.get_throughput()
        assert throughput > 0
        assert throughput < 1000  # Разумное значение

class TestLLMStreamingOptimizer:
    def test_optimize_stream(self):
        config = Config()
        optimizer = LLMStreamingOptimizer(config, logger)
        
        # Симуляция потока
        def mock_stream():
            chunks = ["Hello", " ", "world", "! ", "How", " are", " you?"]
            for chunk in chunks:
                yield chunk
        
        result = list(optimizer.optimize_stream(mock_stream()))
        assert len(result) > 0
        # Все токены должны быть объединены
        full_text = "".join(result)
        assert "Hello world" in full_text
    
    def test_detect_quantization(self):
        optimizer = LLMStreamingOptimizer(Config(), logger)
        # Тест с несуществующим файлом
        result = optimizer.detect_quantization("/nonexistent/model")
        assert result in ["float32", "float16", "int8", "unknown"]
```

---

### FEATURE 3️⃣: Health Checks System

**[Продолжение в следующем разделе]**

#### 3.1 Архитектура

```
utils/health_check.py
├── HealthStatus (enum: HEALTHY, DEGRADED, UNHEALTHY, UNKNOWN)
├── HealthCheckResult (dataclass)
│   ├── component: str
│   ├── status: HealthStatus
│   ├── message: str
│   ├── timestamp: float
│   └── details: Dict
│
├── HealthChecker (facade)
│   ├── check_all() → List[HealthCheckResult]
│   ├── check_component(name: str) → HealthCheckResult
│   ├── start_periodic_checks(interval_sec)
│   ├── stop_periodic_checks()
│   └── get_last_results() → Dict[str, HealthCheckResult]
│
└── Специфичные checkers:
    ├── STTHealthChecker
    ├── TTSHealthChecker
    ├── LLMHealthChecker
    ├── ModulesHealthChecker
    └── NetworkHealthChecker
```

#### 3.2 Реализация

```python
# utils/health_check.py
from enum import Enum
from dataclasses import dataclass
from typing import List, Dict, Optional
from datetime import datetime
import asyncio

class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"

@dataclass
class HealthCheckResult:
    component: str
    status: HealthStatus
    message: str
    timestamp: float
    details: Dict[str, any] = None
    
    def to_dict(self):
        return {
            "component": self.component,
            "status": self.status.value,
            "message": self.message,
            "timestamp": self.timestamp,
            "details": self.details or {}
        }

class STTHealthChecker:
    @staticmethod
    async def check(stt_engine, logger) -> HealthCheckResult:
        """Проверить состояние STT"""
        try:
            # Быстрая проверка: тестовое распознавание
            result = await asyncio.wait_for(
                stt_engine.test_recognition("test"),
                timeout=3.0
            )
            
            if result:
                return HealthCheckResult(
                    component="stt",
                    status=HealthStatus.HEALTHY,
                    message="STT engine ready",
                    timestamp=time.time(),
                    details={"model": str(stt_engine.model_path)}
                )
            else:
                return HealthCheckResult(
                    component="stt",
                    status=HealthStatus.DEGRADED,
                    message="STT recognition returned empty",
                    timestamp=time.time()
                )
        except asyncio.TimeoutError:
            return HealthCheckResult(
                component="stt",
                status=HealthStatus.UNHEALTHY,
                message="STT timeout (>3s)",
                timestamp=time.time()
            )
        except Exception as e:
            logger.error(f"STT health check failed: {e}")
            return HealthCheckResult(
                component="stt",
                status=HealthStatus.UNHEALTHY,
                message=f"STT error: {str(e)[:100]}",
                timestamp=time.time()
            )

class TTSHealthChecker:
    @staticmethod
    async def check(tts_engine, logger) -> HealthCheckResult:
        """Проверить состояние TTS"""
        try:
            # Быстрая проверка: синтез короткого текста
            result = await asyncio.wait_for(
                tts_engine.speak("test"),
                timeout=3.0
            )
            
            if result:
                return HealthCheckResult(
                    component="tts",
                    status=HealthStatus.HEALTHY,
                    message="TTS engine ready",
                    timestamp=time.time(),
                    details={"engine": tts_engine.engine_name if hasattr(tts_engine, 'engine_name') else "unknown"}
                )
            else:
                return HealthCheckResult(
                    component="tts",
                    status=HealthStatus.DEGRADED,
                    message="TTS returned false",
                    timestamp=time.time()
                )
        except asyncio.TimeoutError:
            return HealthCheckResult(
                component="tts",
                status=HealthStatus.UNHEALTHY,
                message="TTS timeout (>3s)",
                timestamp=time.time()
            )
        except Exception as e:
            logger.error(f"TTS health check failed: {e}")
            return HealthCheckResult(
                component="tts",
                status=HealthStatus.UNHEALTHY,
                message=f"TTS error: {str(e)[:100]}",
                timestamp=time.time()
            )

class LLMHealthChecker:
    @staticmethod
    async def check(llm_client, logger) -> HealthCheckResult:
        """Проверить состояние LLM"""
        try:
            # Проверить доступность Ollama
            result = await asyncio.wait_for(
                llm_client.check_ollama_health(),
                timeout=2.0
            )
            
            if result:
                return HealthCheckResult(
                    component="llm",
                    status=HealthStatus.HEALTHY,
                    message="LLM (Ollama) ready",
                    timestamp=time.time(),
                    details={"ollama_url": llm_client.ollama_url}
                )
            else:
                return HealthCheckResult(
                    component="llm",
                    status=HealthStatus.UNHEALTHY,
                    message="Ollama not responding",
                    timestamp=time.time()
                )
        except asyncio.TimeoutError:
            return HealthCheckResult(
                component="llm",
                status=HealthStatus.UNHEALTHY,
                message="Ollama timeout (>2s)",
                timestamp=time.time()
            )
        except Exception as e:
            logger.error(f"LLM health check failed: {e}")
            return HealthCheckResult(
                component="llm",
                status=HealthStatus.UNHEALTHY,
                message=f"LLM error: {str(e)[:100]}",
                timestamp=time.time()
            )

class HealthChecker:
    """Фасад для проверки здоровья системы"""
    
    def __init__(self, arvis_core, config, logger):
        self.arvis_core = arvis_core
        self.config = config
        self.logger = logger
        self.last_results: Dict[str, HealthCheckResult] = {}
        self._periodic_task = None
    
    async def check_all(self) -> List[HealthCheckResult]:
        """Проверить все компоненты параллельно"""
        tasks = []
        
        if self.arvis_core.stt_engine:
            tasks.append(STTHealthChecker.check(self.arvis_core.stt_engine, self.logger))
        
        if self.arvis_core.tts_engine:
            tasks.append(TTSHealthChecker.check(self.arvis_core.tts_engine, self.logger))
        
        if self.arvis_core.llm_client:
            tasks.append(LLMHealthChecker.check(self.arvis_core.llm_client, self.logger))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Сохранить результаты
        for result in results:
            if isinstance(result, HealthCheckResult):
                self.last_results[result.component] = result
        
        return [r for r in results if isinstance(r, HealthCheckResult)]
    
    async def check_component(self, component_name: str) -> HealthCheckResult:
        """Проверить конкретный компонент"""
        if component_name == "stt":
            return await STTHealthChecker.check(self.arvis_core.stt_engine, self.logger)
        elif component_name == "tts":
            return await TTSHealthChecker.check(self.arvis_core.tts_engine, self.logger)
        elif component_name == "llm":
            return await LLMHealthChecker.check(self.arvis_core.llm_client, self.logger)
        else:
            return HealthCheckResult(
                component=component_name,
                status=HealthStatus.UNKNOWN,
                message=f"Unknown component: {component_name}",
                timestamp=time.time()
            )
    
    def start_periodic_checks(self, interval_sec: int = 60):
        """Начать периодические проверки"""
        from utils.async_manager import task_manager
        
        async def periodic_check():
            while True:
                try:
                    await asyncio.sleep(interval_sec)
                    results = await self.check_all()
                    
                    # Проверить на нездоровые компоненты
                    unhealthy = [r for r in results if r.status == HealthStatus.UNHEALTHY]
                    if unhealthy:
                        self.logger.warning(f"Health check: {len(unhealthy)} unhealthy components")
                        # Отправить сигнал в ArvisCore (если есть)
                        if hasattr(self.arvis_core, 'health_status_changed'):
                            self.arvis_core.health_status_changed.emit(results)
                
                except Exception as e:
                    self.logger.error(f"Periodic health check failed: {e}")
        
        self._periodic_task = task_manager.run_async("periodic_health_checks", periodic_check)
    
    def stop_periodic_checks(self):
        """Остановить периодические проверки"""
        if self._periodic_task:
            # TODO: Реализовать cancellation в task_manager
            self._periodic_task = None
    
    def get_last_results(self) -> Dict[str, dict]:
        """Получить последние результаты проверок"""
        return {name: result.to_dict() for name, result in self.last_results.items()}
```

**[ПРОДОЛЖЕНИЕ - ДРУГИЕ ФИЧИ]**

Due to token limit, будет продолжение в следующем файле. Создам дополнительный документ с остальными фичами:

---

## 🔄 Зависимости и последовательность

```
ФИЧА 1: TTS Factory       (День 1-5)
    ↓
ФИЧА 2: LLM Streaming     (День 6-11, параллельно с 4)
    ↓
ФИЧА 3: Health Checks     (День 12-15)
    ↓ (использует результаты 1-3)
ФИЧА 5: Metrics Collector (День 16-19)
    ↓
ФИЧА 4: Split arvis_core  (День 10-16, параллельно)
    ↓
ФИЧА 6: Unit Tests        (День 17-24, покрывает 1-5)
    ↓
ФИЧА 7-9: PyQt6, Config, Notifications (День 25-30, параллельно)
```

## 🧪 Testing Strategy

Для каждой фичи:
1. **Unit tests** (>80% coverage)
2. **Integration tests** (с реальными компонентами)
3. **Performance tests** (TTFT, throughput, latency)
4. **UI tests** (для PyQt компонентов)
5. **Regression tests** (проверить старую функциональность)

---

## 📊 Post-Implementation Checklist

- [ ] Все тесты проходят (pytest с coverage)
- [ ] pre-commit хуки проходят
- [ ] Документация обновлена
- [ ] CHANGELOG обновлен
- [ ] Version bump (1.5.1 → 1.6.0)
- [ ] Performance metrics подтверждают улучшения
- [ ] Code review пройден
- [ ] Release notes готовы

---

**Версия документа**: 1.0 | **Обновлено**: 21 октября 2025
