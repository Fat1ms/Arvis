# Arvis AI Assistant · Copilot Guide

## 🎯 Статус проекта: Производство (v1.5.1)
- **Версия**: Централизована в `version.py` (используй для всех версионирования)
- **Статус**: Стабилен, production-ready
- **Фокус**: Исправление багов, оптимизация, документация (НЕ структурные изменения без тестирования)
- **Python**: 3.11 или 3.12 (3.13 имеет проблемы с PyAudio)

## 📦 Архитектура: Desktop + Server

Arvis — это **гибридная система** из двух независимых репозиториев:

### Arvis-Client (этот репозиторий)
- **Назначение**: Desktop приложение (голосовой ассистент PyQt6)
- **Технологии**: PyQt6 (UI), Vosk (STT), Silero (TTS),Bark (TTS), Ollama (LLM), SQLite (локальные пользователи)
- **Архитектура**: MVC-подобная с асинхронными компонентами
- **Безопасность**: RBAC + 2FA (TOTP), audit logging, гибридная аутентификация

### Arvis-Server (отдельный репозиторий)
- **Назначение**: REST API (FastAPI) для аутентификации и управления пользователями
- **API**: Admin API (`/api/*`) + Client API (`/api/client/*`)
- **Подключение**: config.json → `security.auth.use_remote_server: true`

## 🏗️ Ключевые компоненты Arvis-Client

### Точка входа
```
main.py
  ├─ ArvisApp.init_app() → создаёт Qt application
  ├─ ArvisApp.show_splash_screen() → SplashScreen с прогрессом
  └─ MainWindow (PyQt6)
      ├─ LoginDialog → HybridAuthManager.authenticate()
      └─ src/gui/main_window.py (безрамочное окно, темная тема)
```

### Центральный движок (src/core/arvis_core.py)
```python
class ArvisCore(QObject):
    # Главный компонент для обработки сообщений, TTS/STT, модулей
    
    # Сигналы для UI
    response_ready, partial_response, error_occurred
    
    # Компоненты
    llm_client      → LLMClient (стриминг от Ollama)
    tts_engine      → TTSEngine / SileroTTSEngine / BarkTTSEngine (Factory pattern)
    stt_engine      → STTEngine (Vosk, офлайн распознавание)
    wake_word_detector → KaldiWakeWordDetector (опциональный wake word)
    
    # Модули функций
    weather_module, news_module, search_module, system_control, calendar_module
```

### Потоки данных

#### Обработка текстового сообщения
```
ChatPanel.send_message(text)
  → ArvisCore.process_message(text)
     ├─ RBAC проверка: Permission.CHAT_USE
     ├─ handle_module_commands(text) → погода, новости, системные команды
     └─ LLMClient.stream_response(text)
        ├─ Ollama стриминг → partial_response.emit()
        ├─ ChatPanel обновляет UI в реальном времени
        └─ TTSEngine.speak_streaming(chunk) → озвучивание по мере поступления
```

#### Голосовая активация (wake word)
```
KaldiWakeWordDetector слушает "Арвис/Jarvis"
  → wake_word_detected.emit()
  → ArvisCore._on_wake_word_detected()
     ├─ Останавливает wake word detection
     ├─ Проигрывает подтверждение ("Слушаю")
     ├─ Ждёт окончания TTS (_speak_and_start_recording_after_tts)
     └─ STTEngine.start_recording() → распознавание голоса
        → ArvisCore.process_voice_input(text)
           └─ process_message(text) или просто повторно запустить wake word
```

**Критично**: Wake word detection ВСЕГДА останавливается перед TTS и перезапускается после (см. `_is_tts_playing` флаг).

## 🔐 Система безопасности (RBAC + 2FA)

### Роли и разрешения
```python
# utils/security/rbac.py
Role.GUEST      → минимальные (CHAT_USE, погода, новости)
Role.USER       → стандартные (+ модули, история, блокировка)
Role.POWER_USER → расширенные (+ перезагрузка, скрипты)
Role.ADMIN      → ВСЕ разрешения (+ управление пользователями)
```

### Проверка прав
```python
# Декоратор
@require_permission(Permission.SYSTEM_SHUTDOWN)
def shutdown():
    ...

# Явная проверка в коде
if not self.rbac.has_permission(Permission.MODULE_WEATHER):
    raise PermissionError("Доступ запрещён")
```

### Аутентификация (гибридная, 4-уровневая)
```
HybridAuthManager.authenticate(username, password)
  ├─ 1. ArvisClientAPI.login() → /api/client/login (Client API, основной способ)
  ├─ 2. RemoteAuthClient.login() → /api/auth/login (Admin API, fallback)
  ├─ 3. LocalAuth.authenticate() → data/users.db (локальная БД)
  └─ 4. Если strict_server_mode=true → ошибка (только сервер)
```

**Режимы**:
```json
// config.json

// Гибридный (по умолчанию): сервер → локальная БД
{"security": {"auth": {"use_remote_server": true}}}

// Только локально: автономный режим
{"security": {"auth": {"use_remote_server": false}}}

// Только сервер: требует доступа к Arvis-Server
{"security": {"auth": {"strict_server_mode": true}}}
```

### 2FA (TOTP)
- **Setup**: utils/security/totp.py → генерирует секрет + QR
- **UI**: src/gui/two_factor_setup_dialog.py, two_factor_verification_dialog.py
- **Backup коды**: Генерируются и хранятся хешированные
- **Проверка**: При логине требуется 6-значный код из Google Authenticator

### Audit logging
```
logs/audit/*.jsonl → автоматическая ротация (10 МБ) и очистка (90 дней)
Логирует все операции: login, permission_denied, config_change и т.д.
```

## 🛠️ Рабочие процессы

### Установка и запуск (Windows)
```bat
# Полная установка
INSTALL.bat

# Запуск приложения
LAUNCH.bat

# Диагностика (проверка окружения, зависимостей)
diagnose_setup.bat

# Мониторинг (CPU, RAM, GPU)
diagnose_performance.bat

# Быстрая проверка статуса
STATUS.bat

# Управление Ollama
ollama_manager.bat
```

### Развёртывание
```python
# Проверка Python
INSTALL.bat проверяет версию (3.11/3.12, предупреждает о 3.13)

# Создание venv
python -m venv venv
venv\Scripts\activate.bat

# Установка зависимостей
pip install -r requirements.txt

# Специальная обработка PyAudio (несовместим с 3.13)
# pip install pyaudio==0.2.13  # Для 3.11-3.12
# pipwin install pyaudio       # Для 3.13 (если нужно)
```

### Тестирование
```bash
# Unit тесты
pytest tests/

# Проверка голосовой интеграции
python tests/debug_test.py

# Pre-commit хуки (перед коммитом)
pre-commit run --all-files
```

## 📐 Паттерны и конвенции

### Асинхронные задачи (неблокирующие UI)
```python
from utils.async_manager import task_manager

def long_operation():
    # Долгая операция (HTTP, audio, ML)
    return result

task_manager.run_async(
    "unique_task_id",
    long_operation,
    on_complete=lambda tid, res: self.update_ui(res),
    on_error=lambda tid, err: self.show_error(err)
)

# Никогда не вызывай долгие операции напрямую в Qt обработчиках событий!
```

### HTTP запросы к Ollama
```python
from utils.fast_http import FastHTTPClient

# Автоматически заменяет localhost → 127.0.0.1 (избегаем IPv6 зависания)
client = FastHTTPClient("http://localhost:11434", timeout=5.0)
result = client.get("/api/tags")  # Кешируется 5 сек
```

### TTS буферизация (оптимизация)
```python
# TTSEngine буферизирует текст перед озвучиванием
# Минимум 20 символов или граница слова (., !, ?)
# Если долгая операция → fallback на subprocess worker

tts_engine.speak_streaming(text)  # Неблокирующий (async)
```

### Конфигурация
```python
from config.config import Config

config = Config()
value = config.get("llm.default_model", "auto")
config.set("modules.voice_activation_enabled", True)
```

### Локализация (i18n)
```python
from i18n import _, apply_to_widget_tree

# Все UI строки обязательно в _()
label.setText(_("Привет, мир!"))

# Переключение языка
I18N.get().set_language("en")
apply_to_widget_tree(self)  # Обновить весь UI
```

### История разговоров
```python
from utils.conversation_history import ConversationHistory

history = ConversationHistory(config)
history.add_message("user", "Привет")
history.add_message("assistant", "Привет!")
# Автосохранение каждые 5 сообщений в data/conversation_history.json
# Триммится до 50 последних
```

## 🔧 TTS Factory Pattern (Days 4-5)

Проект использует **Factory pattern** для выбора TTS движка:

```python
# ArvisCore инициализирует TTS
tts_engine = self._create_tts_engine_with_fallback(engine_type)

# Доступные движки (в порядке приоритета):
1. silero       → modules/silero_tts_engine.py (быстро, офлайн)
2. bark         → modules/bark_tts_engine.py (медленнее, офлайн)
3. legacy       → modules/tts_engine.py (fallback, простой)
4. subprocess   → modules/tts_worker_subprocess.py (для долгих операций)

# Сервер может предложить движок (если гибридный режим)
server_engine = self._negotiate_engine_with_server()
```

**Почему Factory?** Позволяет:
- Выбирать лучший движок в runtime
- Fallback если движок недоступен
- Подключение новых движков без изменения ArvisCore
- Согласование с сервером

## ⚠️ Частые ловушки и решения

### 1. IPv6 зависания с localhost
```python
# ❌ Плохо: localhost резолвится в ::1 (IPv6)
url = "http://localhost:11434"

# ✅ Хорошо: явный IPv4
url = "http://127.0.0.1:11434"

# ✅ Или используй FastHTTPClient (автозамена)
client = FastHTTPClient("http://localhost:11434")
```

### 2. Долгая инициализация Vosk
```json
// config.json
{
  "stt": {
    "model_path": "models/vosk-model-ru-0.22",           // Полная модель
    "kaldi_model_path": "models/vosk-model-small-ru-0.22", // Маленькая для wake word
    "wake_word_engine": "kaldi"
  }
}
```

### 3. TTS блокирует UI
```python
# ✅ TTS автоматически асинхронный через task_manager
tts_engine.speak(text)  # Не блокирует

# Если нужен subprocess fallback для очень долгих операций:
# modules/tts_worker_subprocess.py уже реализован
```

### 4. Wake word слушает во время TTS
```python
# ✅ ArvisCore._on_wake_word_detected() автоматически:
# 1. Останавливает wake word detection
# 2. Воспроизводит TTS подтверждение
# 3. Перезапускает wake word после TTS
```

### 5. Audit логи разрастаются
```json
// config.json
{
  "audit": {
    "enabled": true,
    "max_log_size": 10485760,    // 10 МБ
    "max_log_age_days": 90       // Автоудаление старых логов
  }
}
```

### 6. Python 3.13 + PyAudio
```bat
# PyAudio несовместим с Python 3.13
# INSTALL.bat автоматически предупредит

# Решение: используй Python 3.11 или 3.12
# Или используй pipwin для 3.13 (если нужно)
pipwin install pyaudio
```

## 📂 Структура файлов (ключевые)

```
Arvis-Client/
├── main.py                      # Точка входа
├── version.py                   # Централизованная версия
├── config/
│   ├── config.py               # Менеджер конфигурации
│   └── config.json             # Основные настройки
├── src/
│   ├── core/
│   │   └── arvis_core.py       # ⭐ Центральный движок
│   └── gui/
│       ├── main_window.py      # Главное окно (безрамочное)
│       ├── login_dialog.py     # Диалог входа
│       └── ...
├── modules/                     # STT, TTS, LLM, функции
│   ├── stt_engine.py           # Vosk распознавание
│   ├── tts_engine.py           # Силеро синтез
│   ├── tts_factory.py          # Factory для выбора TTS
│   ├── llm_client.py           # Ollama интеграция
│   ├── {weather,news,search}_module.py
│   └── wake_word_detector.py   # Кальди детектор пробуждения
├── utils/
│   ├── async_manager.py        # Асинхронные задачи
│   ├── fast_http.py            # HTTP клиент (оптимизированный)
│   ├── conversation_history.py # История диалогов
│   └── security/
│       ├── hybrid_auth.py      # Гибридная аутентификация
│       ├── client_api.py       # Client API клиент
│       ├── rbac.py             # RBAC система
│       ├── audit.py            # Audit logging
│       └── totp.py             # 2FA (TOTP)
├── data/
│   ├── users.db                # Локальная БД пользователей (SQLite)
│   └── conversation_history.json
├── logs/
│   ├── arvis.log               # Главный лог
│   └── audit/*.jsonl           # Audit логи (ротация)
└── requirements.txt            # Зависимости
```

## 🎓 Быстрые примеры кода

### Добавить модуль функции
```python
# 1. Создать modules/my_module.py
class MyModule:
    def __init__(self, config):
        self.config = config
    
    def process(self, message: str) -> str:
        return f"Result: {message}"

# 2. Зарегистрировать в ArvisCore.init_modules()
self.my_module = MyModule(self.config)

# 3. Добавить обработку в handle_module_commands()
if "ключевое_слово" in message.lower():
    if self.rbac.has_permission(Permission.MODULE_MY):
        return self.my_module.process(message)

# 4. Добавить Permission в utils/security/rbac.py
```

### Проверить права пользователя
```python
from utils.security import get_rbac_manager, Permission

rbac = get_rbac_manager()
if rbac.has_permission(Permission.SYSTEM_SHUTDOWN):
    os.system("shutdown /s /t 0")
else:
    raise PermissionError("Доступ запрещён")
```

### Запустить долгую операцию без блокировки
```python
from utils.async_manager import task_manager

def fetch_weather():
    # Долгий HTTP запрос
    return requests.get("...").json()

task_manager.run_async(
    "weather_task",
    fetch_weather,
    on_complete=lambda tid, res: self.update_ui(res),
    on_error=lambda tid, err: self.logger.error(err)
)
```

### Озвучить текст асинхронно
```python
from modules.tts_engine import TTSEngine

tts = TTSEngine(config)
tts.speak(text="Привет мир!")  # Неблокирующий
# tts.is_speaking → проверить статус
```

## 🔄 Миграция между версиями

При обновлении версии:
1. **Проверь** `version.py` → обнови версию там (единая точка)
2. **Миграция БД**: `migrate_db.py` если изменилась структура
3. **Конфиг**: `config.json.example` → новые поля
4. **Документация**: Обнови CHANGELOG.md, README.md
5. **Тесты**: `pytest tests/` → должны пройти
6. **Pre-commit**: `pre-commit run --all-files` → без ошибок

## 📞 Специальные команды разработчика

```bash
# Проверка конфигурации
python check_config.py

# Создание минимальной конфигурации
python create_minimal_config.py

# Миграция БД пользователей
python migrate_db.py

# Тестирование TTS
python test_tts_engine_final.py
python test_silero_direct.py
python test_bark_tts.py

# Миграция на PyQt6
python migrate_to_pyqt6.py

# Исправление PyAudio
python fix_pyaudio.bat

# Проверка версии CLI
--version   # Shows app version
```

## 🔒 Правила разработки

1. **Обратная совместимость**: Не ломай config.json, users.db, conversation_history.json
2. **RBAC везде**: Все критические операции проверяй через `rbac.has_permission()`
3. **Audit логирование**: Логируй все операции с пользователями через `self.audit.log_event()`
4. **Асинхронность**: Никогда не вызывай долгие операции в Qt обработчиках
5. **Локализация**: Все UI строки в `_()`
6. **Версионирование**: Изменяй только `version.py`, остальное автоматически

---

**Версия документа**: 3.0 (26.10.2025)  
**Контакт**: Fat1ms (GitHub)  
**Лицензия**: MIT
