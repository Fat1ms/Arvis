# Интеграция системы активации в Arvis Launcher

## Обзор изменений

Система активации интегрирована в лаунчер для контроля доступа к Arvis через ключи активации.

## Добавленные файлы

### `src/arvis_launcher/activation.py`
Модуль управления активацией, содержит:
- `ActivationManager` - основной класс для работы с ключами активации
- Поддержка онлайн и офлайн валидации
- Сохранение данных активации в `activation.json`
- Grace period для офлайн работы

### `src/arvis_launcher/ui/dialogs/activation_dialog.py`
UI компоненты:
- `ActivationDialog` - диалог ввода ключа активации
- `ActivationStatusWidget` - виджет статуса активации для страницы аккаунта
- `ActivationWorker` - фоновый поток для проверки ключа

## Изменённые файлы

### `src/arvis_launcher/config.py`
- Добавлен `ActivationConfig` dataclass с настройками:
  - `enabled` - включена ли проверка активации
  - `server_url` - URL сервера активации
  - `check_interval_hours` - интервал онлайн-проверки
  - `offline_grace_days` - дней офлайн работы без проверки

### `src/arvis_launcher/ui/main_window.py`
- Добавлена инициализация `ActivationManager`
- Добавлена проверка активации при запуске (`_check_activation`)
- Добавлен метод `show_activation_dialog` для показа диалога из других частей UI

### `src/arvis_launcher/ui/pages/account_page.py`
- Добавлен виджет статуса активации
- Добавлена поддержка деактивации

### `src/arvis_launcher/ui/dialogs/__init__.py`
- Экспорт `ActivationDialog` и `ActivationStatusWidget`

### `src/arvis_launcher/i18n.py`
- Добавлены строки локализации для системы активации (ru, en, uk)

### `launcher_config.json`
- Добавлена секция `activation` с настройками по умолчанию

## Форматы ключей

| Тип | Формат | Срок действия |
|-----|--------|---------------|
| Beta | `ARVIS-BETA-XXXXXXXX` | 90 дней |
| Monthly | `ARVIS-MNTH-XXXXXXXX-YYMM` | До конца месяца |
| Permanent | `ARVIS-PERM-XXXXXXXX-XXXX` | Бессрочно |
| Trial | `ARVIS-TRIAL-XXXXXXXX` | 14 дней |

## Конфигурация

В `launcher_config.json`:
```json
{
  "activation": {
    "enabled": true,
    "server_url": "http://localhost:8080",
    "check_interval_hours": 24,
    "offline_grace_days": 7
  }
}
```

## API Сервера

### Валидация ключа
```
POST /api/keys/validate
Content-Type: application/json

{
    "key": "ARVIS-BETA-A1B2C3D4E5F6",
    "user_email": "user@example.com"  // опционально
}
```

### Информация о ключе
```
GET /api/keys/info/ARVIS-BETA-A1B2C3D4E5F6
```

## Логика работы

1. При запуске лаунчера проверяется `activation.enabled`
2. Если включено - проверяется наличие сохранённой активации
3. Если активация не найдена или недействительна - показывается диалог
4. При вводе ключа происходит онлайн-валидация
5. При успешной валидации данные сохраняются локально
6. Периодическая онлайн-проверка происходит каждые `check_interval_hours`
7. При отсутствии интернета работает grace period (`offline_grace_days`)

## Отключение проверки

Для отключения проверки активации установите в конфиге:
```json
{
  "activation": {
    "enabled": false
  }
}
```

## Файлы данных

Данные активации сохраняются в `activation.json` рядом с `launcher_config.json`:
```json
{
  "key": "ARVIS-BETA-XXXXXXXX",
  "email": "user@example.com",
  "key_type": "beta",
  "activated_at": "2025-01-01T00:00:00",
  "last_online_check": "2025-01-01T00:00:00",
  "expires_at": "2025-03-31T23:59:59",
  "offline_activation": false
}
```
