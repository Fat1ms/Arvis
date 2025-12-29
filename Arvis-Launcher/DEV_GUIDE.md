# Arvis Launcher - Руководство разработчика

## Обзор

Arvis Launcher — это приложение для управления AI-ассистентом Arvis. Лаунчер обеспечивает:
- Установку и обновление клиента
- Управление AI-моделями через Ollama
- Настройку параметров
- Диагностику и отладку

## Архитектура проекта

```
Arvis-Launcher/
├── main.py                 # Точка входа
├── requirements.txt        # Зависимости Python
├── ArvisLauncher.spec      # PyInstaller spec для сборки .exe
├── generate_icons.py       # Скрипт генерации иконок
├── launcher_config.json    # Файл конфигурации (генерируется)
├── resources/
│   ├── arvis_launcher.ico  # Иконка лаунчера
│   ├── arvis_launcher.png  # PNG версия иконки
│   └── arvis_client.ico    # Иконка для клиента
└── src/arvis_launcher/
    ├── __init__.py
    ├── app.py              # QApplication класс
    ├── config.py           # Управление конфигурацией
    ├── process.py          # Запуск клиента (QProcess)
    ├── installer.py        # Установка venv и зависимостей
    ├── updater.py          # Проверка обновлений с GitHub
    ├── ollama_manager.py   # Управление Ollama
    ├── styles.py           # Стили UI (тёмная тема)
    ├── i18n.py             # Локализация (RU/EN/UK)
    └── ui/
        ├── main_window.py  # Главное окно
        └── pages/
            ├── home_page.py      # Главная страница
            ├── models_page.py    # Управление моделями
            ├── settings_page.py  # Настройки
            └── debug_page.py     # Отладка и логи
```

## Основные модули

### config.py
Управление настройками лаунчера через JSON файл.
- Автоопределение пути к клиенту
- Сохранение настроек окна, обновлений, Ollama
- Поддержка языка интерфейса

### installer.py
Установка клиента в фоновом потоке (QThread).
- Проверка Python 3.10+
- Создание venv
- Установка зависимостей из requirements.txt

### process.py
Запуск клиента через QProcess.
- Перенаправление вывода в логи
- Отслеживание состояния (stopped/starting/running)
- Корректное завершение

### ollama_manager.py
Интеграция с Ollama.
- Проверка установки Ollama
- Запуск/остановка службы
- Загрузка/удаление моделей
- Мониторинг состояния

### updater.py
Обновления через GitHub Releases API.
- Проверка новых версий
- Скачивание zip-архива
- Применение обновления с сохранением настроек

### i18n.py
Система локализации.
- Поддержка: Русский (ru), English (en), Українська (uk)
- Функция `tr(key)` для получения переводов
- Возможность добавления кастомных переводов

## Сборка .exe

```bash
# Установка PyInstaller
pip install -r requirements.txt
pip install pyinstaller

# Сборка
pyinstaller ArvisLauncher.spec

# Результат в папке dist/ArvisLauncher.exe
```

## Зависимости

- **PyQt6** — GUI фреймворк
- **requests** — HTTP запросы для GitHub API
- **Pillow** — Генерация иконок (опционально)

## Стиль UI

Тёмная тема соответствует клиенту Arvis:
- Основной фон: `rgb(43, 43, 43)`
- Панели: `rgb(50, 50, 50)`
- Акцент: `rgb(100, 150, 255)`
- Текст: белый/серый

## Конфигурация

Файл `launcher_config.json`:
```json
{
  "window": {"width": 1000, "height": 650},
  "paths": {"client_root": "C:/path/to/Arvis-Client"},
  "update": {
    "auto_check": true,
    "branch": "stable",
    "github_repo": "Fat1ms/Arvis-Client"
  },
  "ollama": {
    "auto_install": true,
    "default_model": "gemma2:2b",
    "auto_start": false
  },
  "language": "ru"
}
```

## Статус реализации

### ✅ Реализовано
- [x] Главное окно с frameless темой
- [x] Навигация по страницам
- [x] Проверка установки клиента
- [x] Установка venv и зависимостей
- [x] Запуск и остановка клиента
- [x] Управление Ollama (статус, модели)
- [x] Настройки лаунчера
- [x] Просмотр логов
- [x] Проверка обновлений GitHub
- [x] Иконка приложения
- [x] Локализация RU/EN/UK

### 🔄 В работе
- [ ] Скачивание обновлений
- [ ] Автообновление при запуске

### 📋 Планируется
- [ ] Синхронизация настроек через аккаунт
- [ ] Форма баг-репорта с отправкой в GitHub Issues
- [ ] Управление STT/TTS моделями
- [ ] Светлая тема

## Дебаг

При запуске из исходников:
```bash
cd Arvis-Launcher
python main.py
```

Логи выводятся во вкладку "Отладка" в лаунчере.
