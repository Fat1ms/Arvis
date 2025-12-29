"""
Arvis Version Information
Централизованная система управления версиями
"""

__version__ = "1.5.1"
__app_name__ = "Arvis - AI Assistant"

# История версий
VERSION_HISTORY = {
    "1.5.1": "HOTFIX: Исправлена проблема установки на Python 3.13 (PyAudio несовместим); добавлена проверка версии Python, документация, интерактивный fix_pyaudio.bat, обновлён setup_arvis.bat с fallback стратегиями",
    "1.5.0": "DEVEX: стабилизация pre-commit на Windows (flake8 аргументы, bandit pbr+encoding, detect-secrets v1.5 baseline), удаление дубликатов хуков; обновлён README и ссылки на безопасность",
    "1.3.3": "DOCS & INFRA: Phase 0 Complete - Добавлена полная документация (CONTRIBUTING, SECURITY, CODE_OF_CONDUCT), GitHub templates (Issues/PR), CI/CD pipeline, pre-commit hooks, обновлён README с roadmap и requirements",
    "1.3.2": "HOTFIX: Исправлен wake word detection - теперь работает постоянно после всех типов запросов; исправлены пути к кнопкам; удалена кнопка остановки голоса; улучшен UI истории чата",
    "1.3.1": "UI: добавлена инициализация i18n и работающее переключение языка; восстановлена ChatPanel; мелкие исправления",
    "1.2.1": "HOTFIX: Исправлена критическая ошибка disconnect() при вызове орба",
    "1.2.0": "Добавлена версия в заголовок окна, централизованная система версий, исправления орба",
    "1.1.2": "Исправления GUI и стабильности",
    "1.1.0": "Базовая версия с GUI",
}


def get_version() -> str:
    """Получить версию приложения"""
    return __version__


def get_app_name() -> str:
    """Получить название приложения"""
    return __app_name__


def get_full_title() -> str:
    """Получить полный заголовок приложения с версией"""
    return f"{__app_name__} v{__version__}"


def get_version_info() -> dict:
    """Получить полную информацию о версии"""
    return {
        "version": __version__,
        "app_name": __app_name__,
        "full_title": get_full_title(),
        "history": VERSION_HISTORY,
    }
