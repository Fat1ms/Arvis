# Phase 3: Quick Start Guide
## Пошаговое руководство по реализации

**Версия**: 1.0  
**Дата**: 21 октября 2025  
**Статус**: 🟢 Готово к реализации

---

## 🎯 Первые 24 часа: Setup и Planning

### День 1: Подготовка окружения

#### 1. Создать feature branches
```bash
# Для каждой фичи создаем отдельную ветку
git checkout -b feature/tts-factory
git checkout -b feature/llm-streaming-optimizer
git checkout -b feature/health-checks
git checkout -b feature/split-arvis-core
git checkout -b feature/metrics-collector
git checkout -b feature/unit-tests
git checkout -b feature/pyqt6-prep
git checkout -b feature/config-improvements
git checkout -b feature/notification-system
```

#### 2. Setup development tools
```bash
# Убедиться что все dev dependencies установлены
pip install -r requirements-dev.txt

# Установить дополнительные пакеты для Phase 3
pip install pytest pytest-asyncio pytest-cov pytest-mock
pip install bark transformers[torch] soundfile
pip install jsonschema psutil

# Установить pre-commit hooks
pre-commit install
```

#### 3. Создать fixture директории для тестов
```bash
mkdir -p tests/fixtures
mkdir -p tests/unit
mkdir -p tests/integration
mkdir -p tests/performance

# Создать conftest.py для pytest
touch tests/conftest.py
```

---

## 🔥 ФИЧА #1: TTS Factory (Дни 1-5)

### Day 1: Архитектура и базовые классы

#### Шаг 1.1: Создать абстрактный базовый класс
```bash
cd d:\AI\Arvis-Client
```

```python
# modules/tts_base.py
"""Base class for TTS engines"""

from abc import ABC, abstractmethod
from typing import Callable, Dict, Any
from enum import Enum

class TTSStatus(Enum):
    IDLE = "idle"
    INITIALIZING = "initializing"
    READY = "ready"
    SPEAKING = "speaking"
    ERROR = "error"

class TTSEngineBase(ABC):
    """Abstract base class for all TTS engines"""
    
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.status = TTSStatus.IDLE
        self.engine_name = "base"
    
    @abstractmethod
    def speak(self, text: str, stream: bool = False) -> bool:
        """
        Synthesize and play text.
        
        Args:
            text: Text to synthesize
            stream: If True, stream audio in real-time
        
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def speak_streaming(self, text: str, chunk_callback: Callable[[bytes], None]) -> bool:
        """
        Stream synthesis with callback for audio chunks.
        
        Args:
            text: Text to synthesize
            chunk_callback: Function called with each audio chunk (PCM bytes)
        
        Returns:
            True if successful
        """
        pass
    
    @abstractmethod
    def stop(self) -> None:
        """Stop current playback"""
        pass
    
    def get_status(self) -> Dict[str, Any]:
        """Get engine status"""
        return {
            "engine": self.engine_name,
            "status": self.status.value,
            "ready": self.status == TTSStatus.READY
        }
    
    def health_check(self) -> Dict[str, Any]:
        """
        Health check result.
        
        Returns:
            Dict with "healthy" (bool), "message" (str), "details" (dict)
        """
        return {
            "healthy": self.status in [TTSStatus.READY, TTSStatus.SPEAKING],
            "message": f"TTS engine status: {self.status.value}",
            "details": self.get_status()
        }
```

#### Шаг 1.2: Создать TTS Factory
```python
# modules/tts_factory.py
"""Factory for creating TTS engines"""

from typing import Optional, List
from modules.tts_base import TTSEngineBase
from utils.logger import ModuleLogger

class TTSFactory:
    """Factory for TTS engine creation and management"""
    
    # Registry of available engines
    _engines = {}
    _logger = ModuleLogger("TTSFactory")
    
    @classmethod
    def register_engine(cls, name: str, engine_class: type):
        """Register a new TTS engine"""
        cls._engines[name] = engine_class
        cls._logger.debug(f"Registered TTS engine: {name}")
    
    @classmethod
    def create_engine(cls, engine_name: str, config, logger) -> Optional[TTSEngineBase]:
        """
        Create TTS engine by name.
        
        Args:
            engine_name: Name of engine (silero, bark, sapi)
            config: Config object
            logger: Logger instance
        
        Returns:
            TTSEngineBase instance or None if not found
        
        Raises:
            ValueError: If engine not found
        """
        if engine_name not in cls._engines:
            raise ValueError(f"Unknown TTS engine: {engine_name}. Available: {list(cls._engines.keys())}")
        
        engine_class = cls._engines[engine_name]
        try:
            instance = engine_class(config, logger)
            cls._logger.info(f"Created TTS engine: {engine_name}")
            return instance
        except Exception as e:
            cls._logger.error(f"Failed to create TTS engine {engine_name}: {e}")
            raise
    
    @classmethod
    def list_available_engines(cls) -> List[str]:
        """List all available TTS engines"""
        return list(cls._engines.keys())
    
    @classmethod
    def get_engine_info(cls, engine_name: str) -> dict:
        """Get info about TTS engine"""
        if engine_name not in cls._engines:
            return {}
        
        engine_class = cls._engines[engine_name]
        return {
            "name": engine_name,
            "class": engine_class.__name__,
            "module": engine_class.__module__,
        }

# Register built-in engines
def register_builtin_engines():
    """Register built-in TTS engines"""
    from modules.silero_tts_engine import SileroTTSEngine
    
    TTSFactory.register_engine("silero", SileroTTSEngine)
    
    try:
        from modules.bark_tts_engine import BarkTTSEngine
        TTSFactory.register_engine("bark", BarkTTSEngine)
    except ImportError:
        pass  # Bark optional
    
    try:
        from modules.system_tts import SAPITTSEngine
        TTSFactory.register_engine("sapi", SAPITTSEngine)
    except ImportError:
        pass  # SAPI Windows-only

# Call on module import
register_builtin_engines()
```

#### Шаг 1.3: Refactor существующего Silero engine
```python
# modules/silero_tts_engine.py (updated)
"""Silero TTS engine implementation"""

import torch
import torchaudio
from modules.tts_base import TTSEngineBase, TTSStatus

class SileroTTSEngine(TTSEngineBase):
    """Silero TTS engine implementation"""
    
    def __init__(self, config, logger):
        super().__init__(config, logger)
        self.engine_name = "silero"
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = None
        self.sample_rate = config.get("tts.sample_rate", 48000)
        
        # Async load model
        self._load_model_async()
    
    def _load_model_async(self):
        """Load Silero model in background"""
        from utils.async_manager import task_manager
        
        def load():
            try:
                self.model = torch.hub.load(
                    repo_or_dir='snakers4/silero-models',
                    model='silero_tts',
                    language='ru',
                    speaker='xenia'
                )
                self.model.to(self.device)
                self.status = TTSStatus.READY
                self.logger.info("Silero model loaded")
                return True
            except Exception as e:
                self.status = TTSStatus.ERROR
                self.logger.error(f"Failed to load Silero model: {e}")
                return False
        
        task_manager.run_async("silero_load", load)
    
    def speak(self, text: str, stream: bool = False) -> bool:
        """Speak using Silero"""
        if not self.model or self.status != TTSStatus.READY:
            self.logger.warning("Silero model not ready")
            return False
        
        try:
            self.status = TTSStatus.SPEAKING
            
            # Generate audio
            audio = self.model.apply_tts(text=text, speaker='xenia', sample_rate=self.sample_rate)
            
            # Play audio
            self._play_audio(audio)
            
            self.status = TTSStatus.READY
            return True
        except Exception as e:
            self.logger.error(f"Silero TTS failed: {e}")
            self.status = TTSStatus.ERROR
            return False
    
    def speak_streaming(self, text: str, chunk_callback) -> bool:
        """Stream synthesis"""
        # Silero doesn't support true streaming, so we chunk the text
        sentences = text.split('.')
        
        for i, sentence in enumerate(sentences):
            if not sentence.strip():
                continue
            
            try:
                audio = self.model.apply_tts(text=sentence.strip(), speaker='xenia', sample_rate=self.sample_rate)
                # Convert to PCM bytes
                pcm_bytes = (audio * 32767).astype("int16").tobytes()
                chunk_callback(pcm_bytes)
            except Exception as e:
                self.logger.error(f"Streaming chunk failed: {e}")
                return False
        
        return True
    
    def stop(self) -> None:
        """Stop playback"""
        self.status = TTSStatus.IDLE
        # TODO: Implement stop logic for actual playback
    
    def _play_audio(self, audio):
        """Play audio"""
        # TODO: Use pyaudio to play
        pass
```

#### Шаг 1.4: Создать тесты для factory
```python
# tests/unit/test_tts_factory.py
"""Tests for TTS Factory"""

import pytest
from modules.tts_factory import TTSFactory
from modules.tts_base import TTSEngineBase
from config.config import Config
from utils.logger import ModuleLogger

@pytest.fixture
def config():
    return Config("tests/fixtures/config_test.json")

@pytest.fixture
def logger():
    return ModuleLogger("test")

class TestTTSFactory:
    
    def test_list_available_engines(self):
        """Test listing available engines"""
        engines = TTSFactory.list_available_engines()
        assert "silero" in engines
        assert isinstance(engines, list)
    
    def test_create_silero_engine(self, config, logger):
        """Test creating Silero engine"""
        engine = TTSFactory.create_engine("silero", config, logger)
        assert isinstance(engine, TTSEngineBase)
        assert engine.engine_name == "silero"
    
    def test_create_invalid_engine(self, config, logger):
        """Test creating invalid engine raises error"""
        with pytest.raises(ValueError):
            TTSFactory.create_engine("invalid_engine", config, logger)
    
    def test_get_engine_info(self):
        """Test getting engine info"""
        info = TTSFactory.get_engine_info("silero")
        assert "name" in info
        assert info["name"] == "silero"
    
    def test_engine_status(self, config, logger):
        """Test getting engine status"""
        engine = TTSFactory.create_engine("silero", config, logger)
        status = engine.get_status()
        assert "engine" in status
        assert "status" in status
```

### Day 2-3: BarkTTSEngine Implementation

#### Шаг 1.5: Создать Bark engine
```python
# modules/bark_tts_engine.py
"""Bark TTS engine implementation"""

import numpy as np
from modules.tts_base import TTSEngineBase, TTSStatus
from typing import Callable

class BarkTTSEngine(TTSEngineBase):
    """Bark TTS engine from Suno AI"""
    
    def __init__(self, config, logger):
        super().__init__(config, logger)
        self.engine_name = "bark"
        self.device = config.get("tts.bark.device", "cpu")
        self.model = None
        self.processor = None
        self.sample_rate = 24000
        
        # Async load
        self._load_model_async()
    
    def _load_model_async(self):
        """Load Bark model"""
        from utils.async_manager import task_manager
        
        def load():
            try:
                from bark import SAMPLE_RATE, preload_models
                preload_models(device=self.device)
                self.status = TTSStatus.READY
                self.logger.info(f"Bark model loaded on {self.device}")
                return True
            except Exception as e:
                self.status = TTSStatus.ERROR
                self.logger.error(f"Failed to load Bark: {e}")
                return False
        
        task_manager.run_async("bark_load", load)
    
    def speak(self, text: str, stream: bool = False) -> bool:
        """Speak using Bark"""
        if self.status != TTSStatus.READY:
            self.logger.warning("Bark model not ready")
            return False
        
        try:
            self.status = TTSStatus.SPEAKING
            
            from bark import generate_audio, SAMPLE_RATE
            
            voice = self.config.get("tts.bark.voice", "v2/en_speaker_6")
            audio = generate_audio(text, voice_preset=voice)
            
            # Play audio
            self._play_audio(audio, SAMPLE_RATE)
            
            self.status = TTSStatus.READY
            return True
        except Exception as e:
            self.logger.error(f"Bark TTS failed: {e}")
            self.status = TTSStatus.ERROR
            return False
    
    def speak_streaming(self, text: str, chunk_callback: Callable[[bytes], None]) -> bool:
        """Stream synthesis"""
        if self.status != TTSStatus.READY:
            return False
        
        try:
            from bark import generate_audio, SAMPLE_RATE
            
            voice = self.config.get("tts.bark.voice", "v2/en_speaker_6")
            audio_array = generate_audio(text, voice_preset=voice)
            
            # Stream in chunks
            chunk_duration_ms = self.config.get("tts.bark.chunk_duration_ms", 500)
            chunk_samples = int(SAMPLE_RATE * chunk_duration_ms / 1000)
            
            for i in range(0, len(audio_array), chunk_samples):
                chunk = audio_array[i:i+chunk_samples]
                # Convert to PCM bytes
                pcm_bytes = (chunk * 32767).astype(np.int16).tobytes()
                chunk_callback(pcm_bytes)
            
            return True
        except Exception as e:
            self.logger.error(f"Bark streaming failed: {e}")
            return False
    
    def stop(self) -> None:
        """Stop playback"""
        self.status = TTSStatus.IDLE
    
    def _play_audio(self, audio: np.ndarray, sample_rate: int):
        """Play audio array"""
        # TODO: Use pyaudio
        pass
```

### Day 4-5: Integration и testing

#### Шаг 1.6: Обновить ArvisCore для использования factory
```python
# src/core/core_components.py (snippet)
"""Component initialization with factory pattern"""

def _init_tts(self):
    """Initialize TTS engine using factory"""
    try:
        from modules.tts_factory import TTSFactory
        
        engine_name = self.config.get("tts.engine", "silero")
        self.tts_engine = TTSFactory.create_engine(engine_name, self.config, self.logger)
        
        # Connect signals if available
        if hasattr(self.tts_engine, 'speech_started'):
            self.tts_engine.speech_started.connect(self._on_tts_started)
        if hasattr(self.tts_engine, 'speech_finished'):
            self.tts_engine.speech_finished.connect(self._on_tts_finished)
        
        self.logger.info(f"TTS engine initialized: {engine_name}")
    except Exception as e:
        self.logger.error(f"Failed to init TTS: {e}")
        self.error_occurred.emit(f"TTS init failed: {e}")
```

#### Шаг 1.7: Добавить конфиг параметры
```json
{
  "tts": {
    "engine": "silero",
    "sample_rate": 48000,
    "silero": {
      "speaker": "xenia",
      "language": "ru"
    },
    "bark": {
      "device": "cpu",
      "voice": "v2/en_speaker_6",
      "temperature": 0.6,
      "top_p": 0.9,
      "chunk_duration_ms": 500
    },
    "sapi": {
      "voice_index": 0,
      "rate": 0
    }
  }
}
```

---

## 🚀 ФИЧА #2: LLM Streaming Optimizer (Дни 6-11)

### Day 6: Stream Buffer Implementation

```python
# modules/llm_streaming_optimizer.py
"""LLM stream optimization"""

from typing import Optional, Generator, Callable
import time

class StreamBuffer:
    """Adaptive buffer for LLM streaming"""
    
    MIN_CHUNK_SIZE = 20
    WORD_BOUNDARIES = {'.', ',', '!', '?', ';', ':', '\n', ' '}
    
    def __init__(self, min_size: int = 20, word_boundary: bool = True):
        self.min_size = min_size
        self.word_boundary = word_boundary
        self.buffer = ""
    
    def add_chunk(self, text: str) -> Optional[str]:
        """Add chunk and return ready text if available"""
        self.buffer += text
        
        if len(self.buffer) >= self.min_size:
            if self.word_boundary:
                # Find last word boundary
                for i in range(len(self.buffer) - 1, -1, -1):
                    if self.buffer[i] in self.WORD_BOUNDARIES:
                        result = self.buffer[:i+1]
                        self.buffer = self.buffer[i+1:]
                        return result
                
                # If no boundary found but buffer is too big, return anyway
                if len(self.buffer) > self.min_size * 2:
                    result = self.buffer[:self.min_size]
                    self.buffer = self.buffer[self.min_size:]
                    return result
            else:
                result = self.buffer[:self.min_size]
                self.buffer = self.buffer[self.min_size:]
                return result
        
        return None
    
    def flush(self) -> str:
        """Return remaining buffer"""
        result = self.buffer
        self.buffer = ""
        return result
    
    def is_empty(self) -> bool:
        return len(self.buffer) == 0

class LLMPerformanceMonitor:
    """Monitor LLM generation performance"""
    
    def __init__(self):
        self.tokens = []  # List of (num, timestamp, text)
        self.start_time = None
        self.first_token_time = None
    
    def start_generation(self):
        """Start tracking"""
        self.tokens.clear()
        self.start_time = time.time()
        self.first_token_time = None
    
    def track_token(self, token_num: int, token_text: str):
        """Track token"""
        current_time = time.time()
        self.tokens.append((token_num, current_time, token_text))
        
        if token_num == 1 and not self.first_token_time:
            self.first_token_time = current_time
    
    def get_ttft(self) -> float:
        """Time To First Token in ms"""
        if not self.first_token_time or not self.start_time:
            return 0.0
        return (self.first_token_time - self.start_time) * 1000
    
    def get_throughput(self) -> float:
        """Tokens per second"""
        if len(self.tokens) < 2:
            return 0.0
        
        first_time = self.tokens[0][1]
        last_time = self.tokens[-1][1]
        elapsed = last_time - first_time
        
        return len(self.tokens) / elapsed if elapsed > 0 else 0.0
    
    def get_latency(self) -> float:
        """Average token latency in ms"""
        if len(self.tokens) < 2:
            return 0.0
        
        total_time = self.tokens[-1][1] - self.tokens[0][1]
        return (total_time / (len(self.tokens) - 1) * 1000) if len(self.tokens) > 1 else 0.0
    
    def get_report(self) -> dict:
        """Get performance report"""
        return {
            "ttft_ms": round(self.get_ttft(), 2),
            "throughput_tokens_per_sec": round(self.get_throughput(), 2),
            "avg_token_latency_ms": round(self.get_latency(), 2),
            "total_tokens": len(self.tokens),
            "total_text": "".join(t[2] for t in self.tokens)
        }

class LLMStreamingOptimizer:
    """Optimize LLM streaming"""
    
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.monitor = LLMPerformanceMonitor()
        self.enabled = config.get("llm.stream_optimization_enabled", True)
    
    def optimize_stream(self, stream_generator: Generator, model_info: dict = None) -> Generator:
        """Wrap stream with optimization"""
        if not self.enabled:
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
                
                ready_text = buffer.add_chunk(chunk)
                if ready_text:
                    yield ready_text
            
            remaining = buffer.flush()
            if remaining:
                yield remaining
        
        except Exception as e:
            self.logger.error(f"Stream error: {e}")
            remaining = buffer.flush()
            if remaining:
                yield remaining
        
        finally:
            report = self.monitor.get_report()
            self.logger.debug(f"LLM Performance: {report}")
    
    def get_performance_stats(self) -> dict:
        """Get performance statistics"""
        return self.monitor.get_report()
```

---

## 📝 Тестирование для ФИЧА #1-2

```python
# tests/conftest.py
"""Pytest configuration and fixtures"""

import pytest
from config.config import Config
from utils.logger import ModuleLogger

@pytest.fixture
def config():
    """Load test config"""
    return Config("config/config.json")

@pytest.fixture
def logger():
    """Get test logger"""
    return ModuleLogger("test")

@pytest.fixture
def mock_llm_stream():
    """Mock LLM stream generator"""
    def stream():
        chunks = ["Hello", " ", "world", "! ", "How", " are", " you", "?"]
        for chunk in chunks:
            yield chunk
    return stream()

# tests/unit/test_stream_buffer.py
"""Test StreamBuffer"""

import pytest
from modules.llm_streaming_optimizer import StreamBuffer

class TestStreamBuffer:
    
    def test_add_chunk_basic(self):
        """Test adding chunks"""
        buf = StreamBuffer(min_size=5, word_boundary=False)
        result = buf.add_chunk("Hello")
        assert result is None  # < 5 chars
        
        result = buf.add_chunk("World")
        assert result is not None
        assert len(result) >= 5
    
    def test_word_boundary(self):
        """Test word boundary detection"""
        buf = StreamBuffer(min_size=5, word_boundary=True)
        result = buf.add_chunk("Hello")
        assert result is None  # No boundary
        
        result = buf.add_chunk(" ")
        assert result == "Hello "
    
    def test_flush(self):
        """Test buffer flush"""
        buf = StreamBuffer()
        buf.add_chunk("Hello")
        result = buf.flush()
        assert result == "Hello"
        assert buf.is_empty()
```

---

## 📋 Запуск и тестирование

### Запустить тесты для ФИЧА #1-2:
```bash
# Run specific test file
pytest tests/unit/test_tts_factory.py -v

# Run with coverage
pytest tests/unit/test_tts_factory.py --cov=modules.tts_factory --cov-report=html

# Run stream buffer tests
pytest tests/unit/test_stream_buffer.py -v

# Run all unit tests
pytest tests/unit/ -v --tb=short
```

### Проверить integration:
```bash
# Start Ollama
ollama serve

# In another terminal, test LLM streaming
python -m pytest tests/integration/test_llm_streaming.py -v -s
```

---

## 🔄 Git workflow для каждой фичи

```bash
# 1. Создать feature branch
git checkout -b feature/tts-factory

# 2. Сделать изменения (не забыть тесты!)
# ... файлы ...

# 3. Проверить код
pre-commit run --all-files

# 4. Запустить тесты
pytest tests/ -v --cov=modules

# 5. Commit с описанием
git add .
git commit -m "feat(tts): implement factory pattern for TTS engines

- Add TTSEngineBase abstract class
- Create TTSFactory for dynamic engine creation
- Refactor SileroTTSEngine to inherit from base
- Add BarkTTSEngine implementation
- Update config with engine selection
- Add unit tests for factory

Closes #XXX"

# 6. Push и создать PR
git push origin feature/tts-factory
```

---

## 📊 Tracking Progress

### Метрики для отслеживания:

| Фича | Статус | Коммиты | Tests | Coverage | ETA |
|------|--------|---------|-------|----------|-----|
| TTS Factory | 🟡 In Progress | 3/5 | 8/10 | 85% | Oct 27 |
| LLM Streaming | 🔵 Not Started | - | - | - | Nov 5 |
| Health Checks | 🔵 Not Started | - | - | - | Nov 10 |
| Split Core | 🔵 Not Started | - | - | - | Nov 12 |
| Metrics | 🔵 Not Started | - | - | - | Nov 15 |
| Unit Tests | 🔵 Not Started | - | - | - | Nov 20 |
| PyQt6 Prep | 🔵 Not Started | - | - | - | Nov 23 |
| Config | 🔵 Not Started | - | - | - | Nov 25 |
| Notifications | 🔵 Not Started | - | - | - | Nov 27 |

---

## ✅ Checklist перед началом каждого дня

- [ ] Все предыдущие тесты проходят
- [ ] Pre-commit хуки работают
- [ ] Ветка synchronized с master
- [ ] Config нужные параметры добавлены
- [ ] Docs обновлены
- [ ] Логирование настроено

---

**Quick Start v1.0** | Обновлено: 21 октября 2025
