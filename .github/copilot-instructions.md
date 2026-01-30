# Arvis AI Assistant · Copilot Guide

## 🏁 Быстрый старт для AI-агентов
- Основная версия хранится в `version.py` (используй для всех проверок и миграций)
- Python 3.11 или 3.12 (3.13 не поддерживается для PyAudio)
- Для установки и запуска на Windows: `INSTALL.bat`, затем `LAUNCH.bat`
- Диагностика: `diagnose_setup.bat`, мониторинг: `diagnose_performance.bat`
- Все ключевые команды и тесты — в корне и в папке Arvis-Client

## 🏗️ Архитектура и компоненты
- **Arvis-Client** — десктоп-клиент (PyQt6, Vosk, Silero, Bark, Ollama, SQLite)
- **Arvis-Server** — отдельный сервер (FastAPI, REST, аутентификация)
- Вход: `main.py` → `ArvisApp` → `MainWindow` (UI)
- Центральный движок: `src/core/arvis_core.py` (обработка сообщений, TTS/STT, модули)
- Модули: `modules/` (STT, TTS, LLM, weather, news, system_control и др.)
- Асинхронность: через `utils/async_manager.py` (никогда не блокируй Qt-UI)
- Безопасность: RBAC + 2FA (TOTP), audit logging (`utils/security/`)
- Конфиг: `config/config.py`, `config/config.json`

## 🔑 Ключевые паттерны и правила
- Все долгие операции — только через `task_manager.run_async()`
- Все UI-строки — через функцию локализации `_()`
- Проверяй права через `rbac.has_permission()` (см. `utils/security/rbac.py`)
- TTS/STT движки выбираются через Factory (`modules/tts_factory.py`)
- HTTP-запросы — через `utils/fast_http.py` (авто-IPv4)
- История диалогов — через `utils/conversation_history.py` (автосохранение)
- Все изменения версии — только в `version.py`
- Не ломай обратную совместимость: `config.json`, `users.db`, `conversation_history.json`

## 🛠️ Рабочие процессы
- Установка: `INSTALL.bat` (создаёт venv, ставит зависимости)
- Запуск: `LAUNCH.bat`
- Тесты: `pytest tests/`, голосовые тесты — отдельные скрипты в корне
- Pre-commit: `pre-commit run --all-files`
- Миграция БД: `migrate_db.py`
- Исправление PyAudio: `fix_pyaudio.bat`
- Проверка конфигурации: `check_config.py`

## ⚠️ Частые ловушки
- Не используй localhost без FastHTTPClient — только IPv4 (127.0.0.1)
- PyAudio не работает с Python 3.13
- Wake word detection всегда останавливается на время TTS
- Audit-логи автоочищаются (см. config)

## 📂 Ключевые файлы и директории
- `main.py`, `version.py`, `config/`, `src/core/arvis_core.py`, `modules/`, `utils/`, `data/`, `logs/`
- Примеры модулей: `modules/weather_module.py`, `modules/tts_engine.py`, `modules/llm_client.py`
- Безопасность: `utils/security/`

## 📚 Документация
- Полный индекс: `docs/INDEX.md`
- Архитектура: `docs/technical/HYBRID_ARCHITECTURE_DESIGN.md`
- User/2FA: `docs/user-guide/USER_MANAGEMENT_GUIDE.md`, `docs/user-guide/USER_GUIDE_2FA.md`

---
Версия: 26.01.2026. Контакт: Fat1ms (GitHub). Лицензия: MIT.
