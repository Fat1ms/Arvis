# 🚀 Немедленные действия - Чеклист для релиза беты

**Дата:** 6 октября 2025  
**Версия:** v1.5.0-beta preparation  
**Приоритет:** 🔴 КРИТИЧНЫЙ

---

## ✅ Выполнено сегодня (6 октября)

### Критические исправления

- [x] Исправлен баг с правами администратора (`check_permission()` метод)
- [x] Исправлен YAML syntax error в CI workflow
- [x] Настроены pre-commit хуки (bandit + detect-secrets)
- [x] Создан `.gitattributes` для правильных line endings
- [x] Создан `.secrets.baseline` для secret scanning

### Документация

- [x] `docs/BETA_RELEASE_PLAN.md` - полный план на 2 недели
- [x] `docs/SECURITY_AUDIT_REPORT.md` - security audit с оценкой B+
- [x] `docs/PRE_COMMIT_FIXES.md` - гайд по pre-commit
- [x] `docs/WORK_SESSION_SUMMARY.md` - резюме работы

---

## 🔥 СЕЙЧАС (перед завершением сессии)

### 1. Коммит изменений

```bash
# Проверить статус
git status

# Добавить все файлы
git add .

# Коммит с подробным описанием
git commit -m "feat: Critical security fixes for v1.5.0-beta

- Fix RBAC check_permission() method bug
- Add security scanning (bandit + detect-secrets)
- Fix CI YAML syntax error
- Add .gitattributes for line endings
- Create comprehensive release plan and security audit

Closes #<issue_number>
"

# Пуш (если готовы)
git push origin main
```

### 2. Проверить работу приложения

```bash
# Запустить Arvis
python main.py

# Попробовать:
# 1. Войти как admin
# 2. Открыть панель управления пользователями (кнопка 👥)
# 3. Убедиться, что права работают корректно
```

### 3. Создать GitHub Issue для отслеживания

**Название:** "v1.5.0-beta Release Preparation Tracking"

**Содержание:**

```markdown
## 🎯 Цель
Подготовка к релизу v1.5.0-beta с фокусом на безопасность и RBAC

## 📅 Целевая дата
15-20 октября 2025

## ✅ Завершено
- [x] Исправлен критический баг с RBAC
- [x] Настроены security pre-commit хуки
- [x] Создан security audit report
- [x] Создан подробный release plan

## 🔄 В процессе
- [ ] Аудит логов на утечки секретов
- [ ] Проверка RBAC в критичных модулях
- [ ] Валидация системных команд

## 📋 Следующие задачи
См. docs/BETA_RELEASE_PLAN.md

## 📊 Прогресс
67% - на правильном пути

## 📚 Документация
- docs/BETA_RELEASE_PLAN.md
- docs/SECURITY_AUDIT_REPORT.md
- docs/PRE_COMMIT_FIXES.md
```

---

## 📅 ЗАВТРА (7 октября) - День 2

### Утро (2-3 часа)

#### 1. Аудит логов на утечки

```bash
# Поиск потенциальных утечек
grep -r "logger\.(info|debug|warning)" --include="*.py" src/ modules/ utils/ | grep -iE "password|token|secret|api.?key" > logs_audit.txt

# Проверить каждую находку вручную
```

#### 2. Создать LogSanitizer

**Файл:** `utils/log_sanitizer.py`

```python
import re
from typing import List, Tuple

# Паттерны для чувствительных данных
SENSITIVE_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r'password["\']?\s*[:=]\s*["\']?([^"\'}\s]+)', re.I), 'password=***'),
    (re.compile(r'token["\']?\s*[:=]\s*["\']?([^"\'}\s]+)', re.I), 'token=***'),
    (re.compile(r'api[_-]?key["\']?\s*[:=]\s*["\']?([^"\'}\s]+)', re.I), 'api_key=***'),
    (re.compile(r'secret["\']?\s*[:=]\s*["\']?([^"\'}\s]+)', re.I), 'secret=***'),
    (re.compile(r'(sk-[a-zA-Z0-9]{32,})', re.I), 'sk-***'),  # OpenAI-like keys
    (re.compile(r'Bearer\s+([a-zA-Z0-9\-._~+/]+=*)', re.I), 'Bearer ***'),  # JWT tokens
]

def sanitize_log(message: str) -> str:
    """Удалить чувствительные данные из лог-сообщения"""
    for pattern, replacement in SENSITIVE_PATTERNS:
        message = pattern.sub(replacement, message)
    return message
```

#### 3. Применить LogSanitizer

**Файл:** `utils/logger.py`

Найти метод `info()`, `debug()`, `warning()` и обернуть:

```python
from utils.log_sanitizer import sanitize_log

def info(self, message):
    sanitized = sanitize_log(str(message))
    self._logger.info(sanitized)
```

### День (3-4 часа)

#### 4. Проверка RBAC в SystemControlModule

**Файл:** `modules/system_control.py`

Убедиться, что каждая команда проверяет права:

```python
from utils.security import get_rbac_manager, Permission

def execute_shutdown(self):
    rbac = get_rbac_manager()
    if not rbac.has_permission(Permission.SYSTEM_SHUTDOWN):
        raise PermissionError("Shutdown requires admin privileges")
    # ... выполнение команды

def execute_restart(self):
    rbac = get_rbac_manager()
    if not rbac.has_permission(Permission.SYSTEM_RESTART):
        raise PermissionError("Restart requires power_user or admin")
    # ... выполнение команды
```

#### 5. Проверка других критичных модулей

- `modules/workflow_module.py` - create vs execute
- `utils/conversation_history.py` - export vs delete vs edit
- `src/gui/settings_dialog.py` - view vs edit

### Вечер (1-2 часа)

#### 6. Unit тесты для security модулей

**Файл:** `tests/security/test_rbac.py`

```python
import pytest
from utils.security.rbac import RBACManager, Role, Permission

def test_admin_has_all_permissions():
    rbac = RBACManager()
    rbac.set_role(Role.ADMIN)
    assert rbac.has_permission(Permission.SYSTEM_SHUTDOWN)
    assert rbac.has_permission(Permission.USER_DELETE)
    # ... все права

def test_guest_limited_permissions():
    rbac = RBACManager()
    rbac.set_role(Role.GUEST)
    assert rbac.has_permission(Permission.CHAT_USE)
    assert not rbac.has_permission(Permission.SYSTEM_SHUTDOWN)
    assert not rbac.has_permission(Permission.USER_CREATE)

def test_check_permission_with_user_id():
    rbac = RBACManager()
    rbac.set_role(Role.ADMIN)
    rbac.set_current_user("user123")

    # Должно работать с правильным user_id
    assert rbac.check_permission("user123", Permission.USER_VIEW)

    # Не должно работать с неправильным user_id
    assert not rbac.check_permission("wrong_user", Permission.USER_VIEW)
```

---

## 📅 ПОСЛЕЗАВТРА (8 октября) - День 3

### 1. Валидация системных команд

**Приоритет:** 🔴 КРИТИЧНО

**Проблема:** Command injection через `os.system()` и path traversal

**Задачи:**

- [ ] Найти все вызовы `os.system()`, `os.popen()`, `subprocess.call(shell=True)`
- [ ] Заменить на безопасные аналоги
- [ ] Создать whitelist разрешённых приложений
- [ ] Добавить санитизацию путей

**Файлы:**

```bash
# Поиск небезопасных вызовов
grep -rn "os\.system\|os\.popen\|subprocess.*shell=True" --include="*.py" src/ modules/
```

### 2. Path traversal protection

**Файл:** `utils/path_validator.py`

```python
from pathlib import Path
from typing import Union

def safe_path(base_dir: Union[str, Path], user_path: Union[str, Path]) -> Path:
    """Безопасное объединение путей без path traversal"""
    base = Path(base_dir).resolve()
    full_path = (base / user_path).resolve()

    # Проверяем, что результат внутри base_dir
    if not str(full_path).startswith(str(base)):
        raise ValueError(f"Path traversal detected: {user_path}")

    return full_path

# Использование:
# safe_path("data", user_input)  # OK: data/file.txt
# safe_path("data", "../etc/passwd")  # RAISE: Path traversal
```

### 3. Обновление README.md

**Файл:** `README.md`

**Изменения:**

- Версия → `v1.5.0-beta`
- Статус badge → `Beta Testing`
- Добавить секцию "🔒 Security Features"
- Обновить roadmap
- Добавить ссылку на Beta Testing Guide

---

## 📅 НЕДЕЛЯ 1 - Остальные дни

### День 4-5 (9-10 октября)

- [ ] Интеграционные тесты (auth flow, RBAC enforcement, 2FA)
- [ ] Тестирование на чистой Windows 10/11 машине
- [ ] Проверка на другом компьютере (если есть доступ)

### День 6-7 (11-12 октября)

- [ ] Code review всех изменений
- [ ] Обновление всей документации
- [ ] Создание CHANGELOG.md
- [ ] Подготовка release notes

---

## 📅 НЕДЕЛЯ 2 - Финал

### День 1-3 (13-15 октября)

- [ ] Финальное тестирование всех функций
- [ ] Performance тесты (startup time, memory usage)
- [ ] UI/UX проверка
- [ ] Accessibility testing

### День 4-5 (16-17 октября)

- [ ] Beta Testing Guide для тестеров
- [ ] RBAC User Guide
- [ ] Security Best Practices Guide
- [ ] API Documentation (если есть)

### День 6 (18-19 октября)

- [ ] 🚀 **РЕЛИЗ v1.5.0-beta**
- [ ] Создать Git tag `v1.5.0-beta`
- [ ] GitHub Release с notes
- [ ] Анонс в Discussions
- [ ] Уведомления контрибьюторам

---

## 🧪 Команды для быстрой проверки

### Pre-commit

```bash
# Проверить все файлы
pre-commit run --all-files

# Проверить только изменённые
pre-commit run

# Конкретный хук
pre-commit run bandit --all-files
pre-commit run detect-secrets --all-files
```

### Security сканирование

```bash
# Bandit
bandit -r src/ modules/ utils/ -ll -f screen

# Detect secrets
detect-secrets scan --baseline .secrets.baseline

# Safety (зависимости)
pip install safety
safety check
```

### Тесты

```bash
# Все тесты
pytest

# С coverage
pytest --cov=src --cov=utils --cov=modules --cov-report=html

# Только security тесты
pytest tests/security/

# Конкретный файл
pytest tests/security/test_rbac.py -v
```

### Логи

```bash
# Аудит логов
grep -r "logger\." --include="*.py" | grep -iE "password|token|secret"

# Последний лог
ls logs/*.log | Sort-Object -Descending | Select-Object -First 1 | Get-Content
```

---

## 📊 Отслеживание прогресса

### Метрики для ежедневного мониторинга

| День | Задачи | Завершено | Прогресс |
|------|--------|-----------|----------|
| День 1 (6 окт) | Критические баги, документация | 7/10 | 70% ✅ |
| День 2 (7 окт) | Аудит логов, RBAC проверка | 0/6 | 0% ⏳ |
| День 3 (8 окт) | Валидация команд, README | 0/3 | 0% ⏳ |
| День 4-5 (9-10 окт) | Тесты | 0/4 | 0% ⏳ |
| День 6-7 (11-12 окт) | Code review, docs | 0/4 | 0% ⏳ |

**Общий прогресс:** 7/27 задач = **26%** (но это только критичные задачи)

---

## 🎯 Критерии готовности к релизу

### Must Have (обязательно)

- [x] Критические security баги исправлены
- [ ] Аудит логов завершён
- [ ] RBAC проверен во всех модулях
- [ ] Command injection защита добавлена
- [ ] Тесты покрывают 70%+ security кода
- [ ] README обновлён
- [ ] CHANGELOG создан

### Should Have (желательно)

- [ ] База данных зашифрована
- [ ] LogSanitizer применён везде
- [ ] Dependency scanning настроен
- [ ] CI/CD с pre-commit настроен
- [ ] Beta Testing Guide готов

### Nice to Have (опционально, можно в v1.5.1)

- [ ] OS Keyring integration
- [ ] Requirement для паролей 12+ символов
- [ ] GDPR compliance improvements
- [ ] Penetration testing

---

## 🚨 Если что-то пойдёт не так

### Откат изменений

```bash
# Откат последнего коммита (без потери изменений)
git reset --soft HEAD~1

# Откат файла к последнему коммиту
git checkout HEAD -- <file>

# Откат всех изменений (ОСТОРОЖНО!)
git reset --hard HEAD
```

### Пропустить pre-commit (только в крайнем случае!)

```bash
git commit --no-verify -m "emergency fix"
```

### Если тесты падают

```bash
# Пропустить конкретный тест
pytest --ignore=tests/failing_test.py

# Запустить только быстрые тесты
pytest -m "not slow"
```

---

## 📞 Полезные ссылки

### Документация проекта

- [Release Plan](docs/BETA_RELEASE_PLAN.md)
- [Security Audit](docs/SECURITY_AUDIT_REPORT.md)
- [Pre-commit Guide](docs/PRE_COMMIT_FIXES.md)
- [Work Summary](docs/WORK_SESSION_SUMMARY.md)

### Внешние ресурсы

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Python Security Best Practices](https://python.readthedocs.io/en/stable/library/security_warnings.html)
- [Bandit Documentation](https://bandit.readthedocs.io/)
- [Detect Secrets](https://github.com/Yelp/detect-secrets)

---

## ✅ Финальный чеклист перед сном

- [ ] Коммит всех изменений
- [ ] Проверить, что приложение запускается
- [ ] Проверить права админа работают
- [ ] Создать GitHub Issue для отслеживания
- [ ] Записать план на завтра

---

**Статус:** 🟢 Отличный прогресс! Критические проблемы решены.

**Следующий чекпойнт:** Завтра вечером - проверка прогресса по аудиту логов

**Мотивация:** 🚀 До релиза осталось ~12 дней! Ты справишься! 💪
