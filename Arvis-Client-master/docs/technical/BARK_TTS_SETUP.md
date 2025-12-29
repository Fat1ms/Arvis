# 🎤 Интеграция Bark для TTS

**Документ**: Инструкция по установке и использованию Bark TTS с Arvis  
**Дата**: October 21, 2025  
**Статус**: Готовая документация  
**Язык**: Русский + English

---

## 📋 Содержание

1. [Что такое Bark?](#что-такое-bark)
2. [Сравнение TTS движков](#сравнение-tts-движков)
3. [Системные требования](#системные-требования)
4. [Установка](#установка)
5. [Конфигурация](#конфигурация)
6. [Использование](#использование)
7. [Кастомизация голоса](#кастомизация-голоса)
8. [Оптимизация](#оптимизация)
9. [Troubleshooting](#troubleshooting)

---

## Что такое Bark?

**Bark** — это текстовый синтез речи (TTS) с поддержкой эмоций и тонов:

| Параметр | Значение |
|----------|----------|
| **Разработчик** | Suno AI |
| **Лицензия** | MIT (открытый исходный код) |
| **Качество голоса** | Очень высокое (естественное) |
| **Язык** | 100+ языков включая русский |
| **Особенности** | Эмоции, звуковые эффекты, музыка |
| **Скорость** | Медленнее чем Silero (3-5x realtime) |
| **RAM** | 4-6 ГБ |
| **GPU** | Рекомендуется (ускоряет в 10x) |

**Преимущества**:
- ✅ Очень естественный голос
- ✅ Поддерживает эмоции ("cheerful", "sad", "angry")
- ✅ Звуковые эффекты (смех, кашель, вздохи)
- ✅ 100+ языков
- ✅ Полностью локальный (офлайн)

**Недостатки**:
- ⚠️ Медленнее чем Silero (синтез может занять 5-30 сек)
- ⚠️ Требует GPU для нормальной скорости
- ⚠️ На CPU практически непригоден для боевого использования
- ⚠️ Требует ~3 ГБ VRAM

---

## Сравнение TTS движков

| Параметр | Silero | Bark | gTTS | Azure |
|----------|--------|------|------|-------|
| **Скорость** | ⚡⚡⚡ (realtime) | ⚡ (5x realtime) | ⚡⚡ (2x realtime) | ⚡⚡ (2x realtime) |
| **Качество** | ⭐⭐⭐ (хорошо) | ⭐⭐⭐⭐⭐ (отлично) | ⭐⭐ (среднее) | ⭐⭐⭐⭐ (отлично) |
| **Эмоции** | Нет | ✅ Да | Нет | ✅ Да (ограниченные) |
| **Локальность** | ✅ Локально | ✅ Локально | ❌ Облако | ❌ Облако |
| **Требования** | CPU | GPU | Интернет | Интернет |
| **Русский** | ✅ Отлично | ✅ Хорошо | ✅ Да | ✅ Да |
| **Рекомендация** | Боевое | Качество | Облако | Облако |

**Рекомендация**:
- **Боевое использование** → Silero (быстро, локально)
- **Максимальное качество** → Bark (+ GPU)
- **С интернетом** → gTTS или Azure (облачные)

---

## Системные требования

### Минимум (CPU-only - НЕ рекомендуется)
```
CPU: Intel Core i7 / AMD Ryzen 7 (8+ ядер)
RAM: 8 ГБ + 4 ГБ подкачка
GPU: Нет
Синтез: 30-60 сек на предложение
```

### Рекомендуется (GPU)
```
CPU: Intel Core i7 / AMD Ryzen 7
RAM: 8 ГБ
GPU: NVIDIA (CUDA 11.8+) с 4+ ГБ VRAM
Синтез: 3-10 сек на предложение
```

### Оптимально
```
CPU: Intel Core i9 / AMD Ryzen 9
RAM: 16 ГБ
GPU: NVIDIA RTX 3060+ (12 ГБ VRAM)
Синтез: 1-3 сек на предложение
```

---

## Установка

### Вариант 1: Через pip (рекомендуется)

#### Шаг 1: Установить зависимости

```bash
# Базовые зависимости
.venv\Scripts\pip install bark

# Дополнительно (для GPU)
.venv\Scripts\pip install numpy==1.24.3  # Совместимость
```

#### Шаг 2: Загрузить модель

```bash
# Первый раз загрузится ~3 ГБ (долгий процесс!)
python -c "from bark import preload_models; preload_models()"

# Вывод должен быть:
# ✓ Fine-grained bark model loaded
# ✓ Coarse bark model loaded
```

#### Шаг 3: Проверить установку

```bash
python -c "
from bark import SAMPLE_RATE, generate_audio, preload_models
import numpy as np

preload_models()

# Синтезировать 'Hello'
audio = generate_audio('Hello')
print(f'✓ Generated audio: {audio.shape}')
"
```

✅ Готово! Bark установлен и работает.

### Вариант 2: С GPU ускорением (NVIDIA)

```bash
# 1. Установить CUDA 11.8+ (если еще нет)
# Скачать с https://developer.nvidia.com/cuda-downloads

# 2. Установить torch с CUDA поддержкой
.venv\Scripts\pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# 3. Установить bark
.venv\Scripts\pip install bark

# 4. Проверить GPU доступна
python -c "import torch; print(f'GPU: {torch.cuda.is_available()}')"
```

---

## Конфигурация

### Обновить config.json

```json
{
    "tts": {
        "engine": "silero",
        "voice": "ru_v3",
        "sample_rate": 48000,
        "device": "cpu",
        "enabled": true,
        "mode": "realtime",
        "sapi_enabled": false,
        "bark_enabled": true,
        "bark_config": {
            "model_preset": "v2_en",
            "use_gpu": true,
            "voice_preset": "v2/en_speaker_0",
            "language": "en",
            "temperature": 0.7,
            "top_k": 250,
            "top_p": 0.85
        }
    }
}
```

### Или в code (Python)

```python
from config.config import Config

config = Config()
config.set("tts.bark_enabled", True)
config.set("tts.bark_config.use_gpu", True)
config.set("tts.bark_config.temperature", 0.7)
```

---

## Использование

### Базовое использование

```python
from utils.providers.tts.bark_provider import BarkTTSProvider

provider = BarkTTSProvider(config)
provider.initialize()

# Синтезировать речь
audio_array = provider.synthesize(
    text="Привет, это Bark TTS",
    language="ru"
)

# Сохранить в файл
import soundfile as sf
sf.write("output.wav", audio_array, provider.sample_rate)
```

### С потоком

```python
# Потоковый синтез (для длинных текстов)
for chunk in provider.stream_synthesize(
    text="Это очень длинный текст который будет синтезирован по частям",
    language="ru"
):
    # chunk = (audio_array, label)
    audio, label = chunk
    print(f"Generated: {label}")
```

### С эмоциями

```python
# Генерировать с эмоцией
audio = provider.synthesize(
    text="Я очень рад!",
    language="ru",
    emotion="cheerful",  # или "angry", "sad", "neutral"
    temperature=0.8  # Больше вариативности
)
```

### С кастомным голосом

```python
audio = provider.synthesize(
    text="Привет",
    language="ru",
    voice_preset="v2/en_speaker_5",  # ID голоса
    temperature=0.6
)
```

---

## Кастомизация голоса

### Доступные параметры

```python
provider.synthesize(
    text="Тестовый текст",
    language="ru",
    
    # Голос
    voice_preset="v2/en_speaker_0",  # 0-9 голосов на языке
    temperature=0.7,  # 0.1 (консервативный) - 1.0 (вариативный)
    
    # Качество
    use_small_model=False,  # True = быстрее, False = качественнее
    
    # Звуковые эффекты
    emotion="neutral",  # Не влияет напрямую, влияет на инtonацию
    
    # Специальные маркеры
    # "[clears throat]" - кашель
    # "[sighs]" - вздох
    # "[laughs]" - смех
)
```

### Примеры с звуковыми эффектами

```python
# С кашлем в начале
audio = provider.synthesize(
    "[clears throat] Доброе утро!",
    language="ru"
)

# Со смехом
audio = provider.synthesize(
    "Вот это да! [laughs]",
    language="ru"
)

# С вздохом
audio = provider.synthesize(
    "Это сложно... [sighs]",
    language="ru"
)
```

### Выбор голоса

```python
# Русские голоса (примеры)
voice_presets = [
    "v2/ru_speaker_0",  # Голос 0 на русском
    "v2/ru_speaker_1",  # Голос 1 на русском
    "v2/ru_speaker_2",  # Голос 2 на русском
    # ... до 9 голосов на языке
]

for preset in voice_presets:
    audio = provider.synthesize(
        "Привет, как дела?",
        language="ru",
        voice_preset=preset
    )
    # Сравнить и выбрать понравившийся
```

---

## Оптимизация

### 1. Использовать GPU

```json
{
    "tts": {
        "bark_config": {
            "use_gpu": true
        }
    }
}
```

**Результат**: Ускорение в 10-50x (в зависимости от GPU)

### 2. Кешировать популярные фразы

```python
from functools import lru_cache

@lru_cache(maxsize=256)
def get_cached_audio(text: str, language: str = "ru") -> np.ndarray:
    return provider.synthesize(text, language=language)

# Первый вызов: медленно (~5 сек)
audio = get_cached_audio("Привет!")

# Второй вызов: быстро (из кеша)
audio = get_cached_audio("Привет!")
```

### 3. Использовать малую модель для быстрого прототипирования

```python
provider.synthesize(
    text,
    use_small_model=True  # Быстрее, но хуже качество
)
```

### 4. Разбить длинный текст на предложения

```python
import re

def split_into_sentences(text: str) -> list[str]:
    """Разбить текст на предложения."""
    return re.split(r'[.!?]+', text)

# Генерировать каждое предложение отдельно
text = "Первое предложение. Второе предложение. Третье!"
for sentence in split_into_sentences(text):
    audio = provider.synthesize(sentence)
    # Обрабатывать...
```

### 5. Буферизировать вывод

```python
# Генерировать в фоне, выдавать по частям
def stream_with_buffering(text: str, buffer_size: int = 3):
    sentences = split_into_sentences(text)
    buffer = []
    
    for sentence in sentences:
        audio = provider.synthesize(sentence)
        buffer.append(audio)
        
        if len(buffer) >= buffer_size:
            # Выдать буферизированный результат
            yield np.concatenate(buffer)
            buffer = []
    
    # Выдать остаток
    if buffer:
        yield np.concatenate(buffer)
```

---

## Troubleshooting

### ❌ "CUDA out of memory"

**Решение 1**: Использовать CPU (медленнее)
```json
{
    "tts": {
        "bark_config": {
            "use_gpu": false
        }
    }
}
```

**Решение 2**: Использовать малую модель
```python
provider.synthesize(
    text,
    use_small_model=True
)
```

**Решение 3**: Очистить GPU память
```python
import torch
torch.cuda.empty_cache()
```

---

### ❌ "Models not found" 

**Решение**: Предзагрузить модели
```bash
python -c "from bark import preload_models; preload_models()"
```

---

### ❌ "Slow synthesis on CPU"

**Проблема**: Bark на CPU очень медленный (30-60 сек)

**Решение 1**: Установить GPU (NVIDIA CUDA 11.8+)

**Решение 2**: Использовать Silero для боевого использования, Bark для качества

**Решение 3**: Синтезировать в фоне и кешировать

```python
from utils.async_manager import task_manager

def synthesize_async(text: str):
    """Синтезировать в фоне."""
    audio = provider.synthesize(text)
    return audio

task_manager.run_async(
    "bark_synthesis",
    lambda: synthesize_async("Привет!"),
    on_complete=lambda tid, audio: save_audio(audio)
)
```

---

### ❌ "Low audio quality"

**Решение 1**: Увеличить temperature
```python
provider.synthesize(
    text,
    temperature=0.9  # Больше вариативности
)
```

**Решение 2**: Использовать большую модель
```python
provider.synthesize(
    text,
    use_small_model=False  # Лучшее качество
)
```

**Решение 3**: Выбрать другой голос
```python
provider.synthesize(
    text,
    voice_preset="v2/ru_speaker_3"  # Попробовать разные
)
```

---

### ❌ "Russian accent is wrong"

**Решение 1**: Явно указать язык
```python
provider.synthesize(
    text,
    language="ru"  # Убедиться что русский
)
```

**Решение 2**: Использовать русский голос
```python
provider.synthesize(
    text,
    language="ru",
    voice_preset="v2/ru_speaker_0"  # Русский голос
)
```

---

## 📊 Примеры использования

### Пример 1: Интеграция с Arvis

```python
from utils.providers.tts.bark_provider import BarkTTSProvider

class ArvisWithBark:
    def __init__(self, config):
        self.config = config
        self.bark_tts = BarkTTSProvider(config)
        self.bark_tts.initialize()
    
    def speak(self, text: str, quality: str = "normal"):
        """Озвучить текст через Bark."""
        if quality == "fast":
            # Использовать Silero для скорости
            return self.silero_tts.speak(text)
        else:
            # Использовать Bark для качества
            audio = self.bark_tts.synthesize(text)
            return audio
```

### Пример 2: Выбор TTS в зависимости от контекста

```python
def get_tts_for_context(context: str) -> str:
    """Выбрать TTS на основе контекста."""
    if context in ["quick_response", "real_time"]:
        return "silero"  # Быстро
    elif context in ["presentation", "important"]:
        return "bark"    # Качественно
    else:
        return "silero"  # По умолчанию

# Использование
tts_engine = get_tts_for_context("presentation")
```

### Пример 3: С потоком для длинных текстов

```python
def stream_long_text(text: str):
    """Синтезировать длинный текст потоком."""
    sentences = text.split('. ')
    
    print("Generating audio stream...")
    for i, sentence in enumerate(sentences):
        audio = bark_provider.synthesize(sentence)
        print(f"✓ Sentence {i+1}/{len(sentences)} completed")
        yield audio
```

---

## ✅ Checklist установки

- [ ] Bark установлен (`pip list | grep bark`)
- [ ] Модели загружены (`python -c "from bark import preload_models; preload_models()"`)
- [ ] Bark синтезирует ("Hello" → audio)
- [ ] GPU доступен если установлен (`.venv\Scripts\python.exe -c "import torch; print(torch.cuda.is_available())"`)
- [ ] Config.json обновлен с `bark_enabled: true`
- [ ] BarkTTSProvider создан в `utils/providers/tts/`
- [ ] Интегрировано с Arvis как опциональный TTS
- [ ] Тесты проходят

---

**Версия документа**: 1.0  
**Статус**: Готово  
**Дата обновления**: October 21, 2025
