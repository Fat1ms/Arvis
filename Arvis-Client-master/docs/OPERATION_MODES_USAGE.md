# 🔧 Operation Modes Framework - Использование

**Версия**: 1.0  
**Статус**: Production-Ready  
**Последнее обновление**: 21 октября 2025  

---

## 📚 Содержание

1. [Быстрый старт](#быстрый-старт)
2. [Архитектура](#архитектура)
3. [Провайдеры](#провайдеры)
4. [FallbackManager](#fallbackmanager)
5. [OperationModeManager](#operationmodemanager)
6. [Примеры кода](#примеры-кода)
7. [Расширение](#расширение)

---

## 🚀 Быстрый старт

### Инициализация менеджера режимов:

```python
from config.config import Config
from utils.operation_mode_manager import OperationModeManager
from utils.providers.stt import VoskSTTProvider
from utils.providers.tts import SileroTTSProvider
from utils.providers.llm import OllamaLLMProvider
from utils.providers.auth import LocalAuthProvider

# Создаём конфиг
config = Config()

# Создаём менеджер
mode_manager = OperationModeManager(config)

# Регистрируем провайдеры
mode_manager.register_provider(VoskSTTProvider(config))
mode_manager.register_provider(SileroTTSProvider(config))
mode_manager.register_provider(OllamaLLMProvider(config))
mode_manager.register_provider(LocalAuthProvider(config))

# Инициализируем текущий режим
if mode_manager.initialize_mode():
    print("✓ Mode initialized successfully")
else:
    print("✗ Mode initialization failed")
```

### Получение текущего режима:

```python
current_mode = mode_manager.get_current_mode()
print(f"Current mode: {current_mode.get_display_name()}")
print(f"Requires internet: {current_mode.requires_internet()}")
print(f"Offline capable: {current_mode.is_offline_capable()}")
```

### Получение статуса:

```python
status = mode_manager.get_status()
print(f"Mode: {status['mode_name']}")
print(f"Available STT providers: {len(status['stt']['available_count'])}")
print(f"Available TTS providers: {len(status['tts']['available_count'])}")
```

---

## 🏗️ Архитектура

### OperationMode (Enum)

```python
from utils.providers import OperationMode

# Режимы работы
OperationMode.STANDALONE  # Полностью локальный
OperationMode.HYBRID      # Локальный + опциональный облак
OperationMode.CLOUD       # Облачный с локальным fallback

# Методы
mode.get_display_name()       # "Автономный режим"
mode.requires_internet()       # True/False
mode.requires_server()         # True/False
mode.is_offline_capable()      # True/False
```

### Provider (Base Class)

Все провайдеры наследуются от базового класса `Provider`:

```python
from utils.providers import Provider, ProviderType, ProviderStatus

class MyProvider(Provider):
    def __init__(self, name: str):
        super().__init__(name, ProviderType.STT)  # или TTS, LLM, AUTH
    
    def initialize(self) -> bool:
        """Инициализировать провайдера"""
        pass
    
    def is_available(self) -> bool:
        """Проверить доступность"""
        pass
    
    def shutdown(self) -> bool:
        """Завершить работу"""
        pass
    
    def get_priority(self) -> int:
        """Приоритет (ниже = приоритетнее)"""
        return 50
    
    def get_status(self) -> Dict[str, Any]:
        """Получить статус"""
        return {
            "name": self.name,
            "available": self.is_available(),
            "status": self._status.value,
        }
```

### ProviderType (Enum)

```python
from utils.providers import ProviderType

ProviderType.STT    # Speech-to-Text
ProviderType.TTS    # Text-to-Speech
ProviderType.LLM    # Language Model
ProviderType.AUTH   # Authentication
```

### ProviderStatus (Enum)

```python
from utils.providers import ProviderStatus

ProviderStatus.AVAILABLE      # Провайдер доступен
ProviderStatus.UNAVAILABLE    # Провайдер недоступен
ProviderStatus.ERROR          # Ошибка
ProviderStatus.INITIALIZING   # Инициализируется
ProviderStatus.DEGRADED       # Частичная функциональность
```

---

## 📦 Провайдеры

### STTProvider (Speech-to-Text)

```python
from utils.providers import STTProvider

class MySTTProvider(STTProvider):
    def recognize(self, audio: bytes, language: Optional[str] = None) -> str:
        """Распознать речь"""
        pass
    
    def stream_recognize(self, audio_stream) -> str:
        """Распознать речь из потока"""
        pass
```

**Встроенные реализации:**
- `VoskSTTProvider` - локальное распознавание через Vosk

**Планируются:**
- `OpenAIWhisperProvider`
- `AzureSpeechProvider`
- `GoogleSpeechToTextProvider`

### TTSProvider (Text-to-Speech)

```python
from utils.providers import TTSProvider

class MyTTSProvider(TTSProvider):
    def synthesize(self, text: str, language: Optional[str] = None) -> bytes:
        """Синтезировать речь"""
        pass
    
    def stream_synthesize(self, text: str, language: Optional[str] = None):
        """Синтезировать речь потоком"""
        yield chunk
```

**Встроенные реализации:**
- `SileroTTSProvider` - локальный синтез речи

**Планируются:**
- `AzureTTSProvider`
- `ElevenLabsProvider`
- `GoogleTTSProvider`

### LLMProvider (Language Model)

```python
from utils.providers import LLMProvider

class MyLLMProvider(LLMProvider):
    def generate_response(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None,
    ) -> str:
        """Генерировать ответ"""
        pass
    
    def stream_response(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None,
    ):
        """Генерировать ответ потоком"""
        yield chunk
```

**Встроенные реализации:**
- `OllamaLLMProvider` - локальные модели через Ollama

**Планируются:**
- `OpenAIProvider`
- `ClaudeProvider`
- `LlamaProvider`

### AuthProvider (Authentication)

```python
from utils.providers import AuthProvider

class MyAuthProvider(AuthProvider):
    def authenticate(
        self,
        username: str,
        password: str,
        totp_code: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Аутентифицировать пользователя"""
        return {
            "user_id": 1,
            "username": username,
            "role": "user",
        }
    
    def validate_token(self, token: str) -> bool:
        """Проверить токен"""
        pass
```

**Встроенные реализации:**
- `LocalAuthProvider` - локальная аутентификация через SQLite

**Планируются:**
- `RemoteAuthProvider`
- `OAuth2Provider`

---

## 🔄 FallbackManager

`FallbackManager` управляет списком провайдеров и автоматически переключается между ними при отказе.

### Использование:

```python
from utils.providers import FallbackManager

# Создаём список провайдеров (по приоритету)
providers = [
    VoskSTTProvider(config),          # Приоритет 0 (максимальный)
    OpenAIWhisperProvider(config),    # Приоритет 20
]

# Создаём fallback менеджер
fallback = FallbackManager(providers)

# Инициализируем всех провайдеров
if fallback.initialize_all():
    print("✓ All providers initialized")

# Выполняем операцию с fallback
try:
    result = fallback.execute(
        operation=lambda provider: provider.recognize(audio_data),
        operation_name="speech_recognition",
    )
    print(f"Recognized: {result}")
except RuntimeError as e:
    print(f"All providers failed: {e}")

# Получаем статус
status = fallback.get_status()
print(f"Available providers: {status['available_count']}")
print(f"Total calls: {status['stats']['total_calls']}")
print(f"Successful: {status['stats']['successful_calls']}")

# Завершаем работу
fallback.shutdown_all()
```

### Приоритеты провайдеров:

```python
# Локальные провайдеры (максимальный приоритет)
class LocalProvider:
    def get_priority(self) -> int:
        return 0-10   # Выполняются первыми

# Облачные провайдеры (низкий приоритет)
class CloudProvider:
    def get_priority(self) -> int:
        return 20-100  # Выполняются если локальные не работают
```

---

## 🎛️ OperationModeManager

### Регистрация провайдеров:

```python
manager = OperationModeManager(config)

# Регистрируем STT провайдеры
manager.register_provider(VoskSTTProvider(config))
manager.register_provider(OpenAIWhisperProvider(config))

# Регистрируем TTS провайдеры
manager.register_provider(SileroTTSProvider(config))
manager.register_provider(AzureTTSProvider(config))

# Регистрируем LLM провайдеры
manager.register_provider(OllamaLLMProvider(config))
manager.register_provider(OpenAILLMProvider(config))

# Регистрируем Auth провайдеры
manager.register_provider(LocalAuthProvider(config))
manager.register_provider(RemoteAuthProvider(config))
```

### Инициализация режима:

```python
if manager.initialize_mode():
    print("✓ Mode initialized")
    
    # Получаем доступные провайдеры
    stt_providers = manager.get_available_providers(ProviderType.STT)
    for provider in stt_providers:
        print(f"  STT: {provider.get_name()}")
else:
    print("✗ Mode initialization failed")
```

### Переключение между режимами:

```python
# Получить текущий режим
current = manager.get_current_mode()
print(f"Current: {current.get_display_name()}")

# Переключиться на новый режим
if manager.switch_mode(OperationMode.STANDALONE):
    print("✓ Switched to STANDALONE mode")
    
    # Проверяем новый режим
    new_mode = manager.get_current_mode()
    print(f"New mode: {new_mode.get_display_name()}")
else:
    print("✗ Mode switch failed")
```

### Получение статуса:

```python
status = manager.get_status()

print(f"Mode: {status['mode_name']}")
print(f"STT providers available: {status['stt']['available_count']}")
print(f"TTS providers available: {status['tts']['available_count']}")
print(f"LLM providers available: {status['llm']['available_count']}")
print(f"Auth providers available: {status['auth']['available_count']}")
print(f"Backups: {status['backups_count']}")
```

---

## 💻 Примеры кода

### Пример 1: Распознавание речи с fallback

```python
def recognize_speech(audio_data: bytes) -> str:
    """Распознать речь с автоматическим fallback"""
    try:
        # Используем fallback менеджер STT
        result = mode_manager.stt_fallback.execute(
            operation=lambda provider: provider.recognize(audio_data),
            operation_name="speech_recognition",
        )
        return result
    except RuntimeError as e:
        logger.error(f"Speech recognition failed: {e}")
        return None
```

### Пример 2: Синтез речи с fallback

```python
def synthesize_speech(text: str) -> bytes:
    """Синтезировать речь с автоматическим fallback"""
    try:
        audio = mode_manager.tts_fallback.execute(
            operation=lambda provider: provider.synthesize(text),
            operation_name="speech_synthesis",
        )
        return audio
    except RuntimeError as e:
        logger.error(f"Speech synthesis failed: {e}")
        return None
```

### Пример 3: Потоковое генерирование ответа

```python
def generate_response_stream(prompt: str):
    """Генерировать ответ потоком"""
    try:
        for chunk in mode_manager.llm_fallback.execute(
            operation=lambda provider: provider.stream_response(prompt),
            operation_name="llm_generation",
        ):
            yield chunk
    except RuntimeError as e:
        logger.error(f"LLM generation failed: {e}")
```

### Пример 4: Аутентификация

```python
def authenticate_user(username: str, password: str) -> Optional[Dict]:
    """Аутентифицировать пользователя с fallback"""
    try:
        user_data = mode_manager.auth_fallback.execute(
            operation=lambda provider: provider.authenticate(username, password),
            operation_name="authentication",
        )
        logger.info(f"User {username} authenticated")
        return user_data
    except RuntimeError as e:
        logger.error(f"Authentication failed: {e}")
        return None
```

### Пример 5: Выбор режима при запуске приложения

```python
def setup_operation_mode():
    """Настроить режим работы при запуске"""
    manager = OperationModeManager(config)
    
    # Регистрируем провайдеры
    mode_manager.register_provider(VoskSTTProvider(config))
    manager.register_provider(SileroTTSProvider(config))
    manager.register_provider(OllamaLLMProvider(config))
    manager.register_provider(LocalAuthProvider(config))
    
    # Если нужны облачные провайдеры
    if config.get("operation_mode") in ["hybrid", "cloud"]:
        try:
            manager.register_provider(OpenAIWhisperProvider(config))
            manager.register_provider(AzureTTSProvider(config))
            manager.register_provider(OpenAILLMProvider(config))
        except Exception as e:
            logger.warning(f"Could not register cloud providers: {e}")
    
    # Инициализируем режим
    if manager.initialize_mode():
        logger.info(f"✓ {manager.get_current_mode().get_display_name()} initialized")
        return manager
    else:
        logger.error("Failed to initialize operation mode")
        return None
```

---

## 🔌 Расширение

### Добавление нового облачного провайдера STT

```python
# utils/providers/stt/openai_provider.py
from utils.providers import STTProvider

class OpenAIWhisperProvider(STTProvider):
    """OpenAI Whisper провайдер для STT"""
    
    def __init__(self, config: Config):
        super().__init__("openai_whisper")
        self.config = config
        self.api_key = config.get("cloud_providers.stt.openai.api_key")
        self.client = None
    
    def get_priority(self) -> int:
        """Облачные провайдеры имеют низкий приоритет"""
        return 20
    
    def initialize(self) -> bool:
        try:
            import openai
            openai.api_key = self.api_key
            self.client = openai.Client(api_key=self.api_key)
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize OpenAI: {e}")
            return False
    
    def is_available(self) -> bool:
        return self.client is not None and bool(self.api_key)
    
    def recognize(self, audio: bytes, language: Optional[str] = None) -> str:
        if not self.is_available():
            raise RuntimeError("OpenAI Whisper not available")
        
        try:
            import io
            audio_file = io.BytesIO(audio)
            
            transcript = self.client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language=language,
            )
            
            return transcript.text
        except Exception as e:
            self.logger.error(f"OpenAI recognition failed: {e}")
            raise RuntimeError(f"OpenAI recognition error: {e}")
    
    def stream_recognize(self, audio_stream) -> str:
        # Whisper не поддерживает стриминг
        return self.recognize(audio_stream.read())
    
    def shutdown(self) -> bool:
        self.client = None
        return True

# Регистрация в config.json
{
  "cloud_providers": {
    "stt": {
      "openai": {
        "api_key": "sk-...",
        "model": "whisper-1"
      }
    }
  }
}

# Использование
manager.register_provider(OpenAIWhisperProvider(config))
```

### Добавление нового локального провайдера LLM

```python
# utils/providers/llm/huggingface_provider.py
from utils.providers import LLMProvider

class HuggingFaceLLMProvider(LLMProvider):
    """Hugging Face провайдер для LLM"""
    
    def __init__(self, config: Config):
        super().__init__("huggingface")
        self.config = config
        self.model = None
    
    def get_priority(self) -> int:
        """Локальный провайдер имеет высокий приоритет"""
        return 5
    
    def initialize(self) -> bool:
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
            
            model_name = self.config.get("llm.huggingface.model", "gpt2")
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForCausalLM.from_pretrained(model_name)
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize HuggingFace: {e}")
            return False
    
    def is_available(self) -> bool:
        return self.model is not None
    
    def generate_response(self, prompt: str, **kwargs) -> str:
        if not self.is_available():
            raise RuntimeError("HuggingFace LLM not available")
        
        try:
            inputs = self.tokenizer.encode(prompt, return_tensors="pt")
            outputs = self.model.generate(inputs, max_length=100)
            return self.tokenizer.decode(outputs[0])
        except Exception as e:
            self.logger.error(f"Generation failed: {e}")
            raise RuntimeError(f"Generation error: {e}")
    
    def stream_response(self, prompt: str, **kwargs):
        # Базовая реализация (для полного потокового нужна более сложная логика)
        yield self.generate_response(prompt, **kwargs)
    
    def shutdown(self) -> bool:
        self.model = None
        return True
```

---

## 🧪 Тестирование

```bash
# Запуск тестов
pytest tests/test_operation_modes.py -v

# Запуск конкретного теста
pytest tests/test_operation_modes.py::TestFallbackManager -v

# Запуск с покрытием
pytest tests/test_operation_modes.py --cov=utils.providers --cov=utils.operation_mode_manager
```

---

## 📖 Дополнительное чтение

- [HYBRID_ARCHITECTURE_DESIGN.md](./HYBRID_ARCHITECTURE_DESIGN.md) - Архитектурный дизайн
- [CONTRIBUTING.md](../CONTRIBUTING.md) - Правила разработки
- [Copilot Instructions](./.github/copilot-instructions.md) - Инструкции для Copilot

---

**Документация в разработке.** Обновляется по мере развития проекта.
