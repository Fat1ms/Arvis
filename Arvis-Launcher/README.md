# Arvis Launcher (PyQt6)

Отдельный portable-лаунчер для **Arvis Client**.

## Что уже умеет (MVP)

- GUI (PyQt6) с вкладками: Home / Models / Settings / Debug.
- Portable-настройки лаунчера: `Arvis-Launcher/launcher_config.json`.
- Запуск клиента кнопкой **Start** (через `Arvis-Client-master/launch.py`).
- Логи запуска клиента в реальном времени.
- Stop/Restart клиента.

## Хранение настроек

- Лаунчер: `Arvis-Launcher/launcher_config.json`
- Клиент: `Arvis-Client-master/config/config.json` (лаунчер будет менять «глобальные» поля позже)

## Запуск (разработка)

```powershell
Set-Location "C:\Users\JarvisSantinel\Desktop\Arvis\Arvis-Launcher"
python .\src\main.py
```

> Важно: чтобы запустился GUI, PyQt6 должен быть установлен в том Python, которым запускаешь лаунчер.

## Планы

- Менеджер моделей Ollama (list/pull/remove, выбор активной модели)
- Настройки клиента (аккаунт, пути, режим окна, update-канал)
- Обновления через GitHub Releases + rollback
- Diagnostic bundle (zip логов/конфигов)
