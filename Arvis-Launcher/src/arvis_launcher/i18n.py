"""
Internationalization module for Arvis Launcher
Supports: Russian (ru), English (en), Ukrainian (uk)
"""

from __future__ import annotations
from typing import Dict, Optional
import json
from pathlib import Path

# Default language
DEFAULT_LANG = "ru"

# Translations dictionary
TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "ru": {
        # App
        "app.title": "Arvis Launcher",
        "app.subtitle": "Персональный AI-ассистент",
        
        # Navigation
        "nav.home": "🏠  Главная",
        "nav.models": "🤖  Модели",
        "nav.settings": "⚙️  Настройки",
        "nav.account": "👤  Аккаунт",
        "nav.debug": "🔧  Отладка",
        
        # Home page
        "home.title": "Arvis AI Assistant",
        "home.subtitle": "Персональный AI-ассистент",
        "home.status.stopped": "● Остановлен",
        "home.status.starting": "● Запускается...",
        "home.status.running": "● Работает",
        "home.status.not_installed": "● Не установлен",
        "home.status.error": "● Ошибка",
        "home.btn.launch": "🚀  Запустить Arvis",
        "home.btn.stop": "⏹  Остановить",
        "home.btn.install": "📦  Установить",
        "home.btn.update": "Обновить",
        
        # Installation
        "install.title": "Установка зависимостей",
        "install.question": "Установить полный набор зависимостей?\n\n• Да — все возможности (больше места)\n• Нет — только базовые функции",
        "install.complete": "Установка завершена",
        "install.error": "Ошибка установки",
        "install.cancelled": "Отменено",
        "install.preparing": "Подготовка...",
        "install.step.python": "Проверка Python",
        "install.step.venv": "Создание виртуального окружения",
        "install.step.deps_minimal": "Установка базовых зависимостей",
        "install.step.deps_full": "Установка полных зависимостей",
        "install.step.done": "Готово!",
        
        # Update
        "update.available": "🔄 Доступно обновление",
        "update.title": "Обновление",
        "update.question": "Установить версию {version}?\n\nВаши настройки и данные будут сохранены.",
        "update.complete": "Обновление завершено",
        "update.error": "Ошибка обновления",
        "update.desc": "Новая версия готова к установке",
        "update.published": "Опубликовано: {date}",
        
        # Models page
        "models.title": "AI Модели",
        "models.subtitle": "Управление локальными AI моделями через Ollama",
        "models.ollama_status": "Статус Ollama",
        "models.ollama.running": "● Запущен",
        "models.ollama.stopped": "● Остановлен",
        "models.ollama.not_installed": "● Не установлен",
        "models.ollama.install": "Установить Ollama",
        "models.ollama.start": "Запустить",
        "models.ollama.stop": "Остановить",
        "models.installed": "Установленные модели",
        "models.no_models": "Нет установленных моделей",
        "models.add_model": "Добавить модель",
        "models.btn.download": "Скачать",
        "models.btn.remove": "Удалить",
        "models.downloading": "Загрузка...",
        "models.default_hint": "Рекомендуемая модель: {model}",
        
        # Settings page
        "settings.title": "Настройки",
        "settings.subtitle": "Настройки лаунчера и обновлений",
        "settings.paths": "📁  Пути",
        "settings.client_path": "Путь к клиенту",
        "settings.browse": "Обзор...",
        "settings.updates": "🔄  Обновления",
        "settings.auto_check": "Автоматически проверять обновления",
        "settings.pre_release": "Получать pre-release версии",
        "settings.ollama": "🤖  Ollama",
        "settings.auto_start": "Запускать Ollama при старте лаунчера",
        "settings.default_model": "Модель по умолчанию",
        "settings.interface": "🎨  Интерфейс",
        "settings.language": "Язык интерфейса",
        "settings.theme": "Тема оформления",
        "settings.theme.dark": "Тёмная",
        "settings.theme.light": "Светлая",
        "settings.save": "💾  Сохранить настройки",
        "settings.saved": "Настройки сохранены",
        
        # Debug page
        "debug.title": "Отладка",
        "debug.subtitle": "Логи и диагностика",
        "debug.logs": "📋  Логи",
        "debug.clear": "Очистить",
        "debug.copy": "Копировать",
        "debug.diagnostics": "🔍  Диагностика",
        "debug.run_diagnostics": "Запустить диагностику",
        "debug.report": "📝  Создать отчёт об ошибке",
        "debug.bug_report": "Баг-репорт",
        
        # Common
        "common.yes": "Да",
        "common.no": "Нет",
        "common.cancel": "Отмена",
        "common.ok": "ОК",
        "common.error": "Ошибка",
        "common.warning": "Предупреждение",
        "common.info": "Информация",
        "common.success": "Успешно",
        
        # News/Welcome
        "news.welcome.title": "Добро пожаловать в Arvis!",
        "news.welcome.desc": "Arvis — это ваш персональный AI-ассистент с голосовым управлением.",
        "news.quickstart.title": "Быстрый старт:",
        "news.quickstart.step1": "Нажмите <b>Установить</b> для первой настройки",
        "news.quickstart.step2": "Перейдите в <b>Модели</b> для загрузки AI-моделей",
        "news.quickstart.step3": "Нажмите <b>Запустить Arvis</b> для начала работы",
    },
    
    "en": {
        # App
        "app.title": "Arvis Launcher",
        "app.subtitle": "Personal AI Assistant",
        
        # Navigation
        "nav.home": "🏠  Home",
        "nav.models": "🤖  Models",
        "nav.settings": "⚙️  Settings",
        "nav.account": "👤  Account",
        "nav.debug": "🔧  Debug",
        
        # Home page
        "home.title": "Arvis AI Assistant",
        "home.subtitle": "Personal AI Assistant",
        "home.status.stopped": "● Stopped",
        "home.status.starting": "● Starting...",
        "home.status.running": "● Running",
        "home.status.not_installed": "● Not installed",
        "home.status.error": "● Error",
        "home.btn.launch": "🚀  Launch Arvis",
        "home.btn.stop": "⏹  Stop",
        "home.btn.install": "📦  Install",
        "home.btn.update": "Update",
        
        # Installation
        "install.title": "Install Dependencies",
        "install.question": "Install full dependencies?\n\n• Yes — all features (more space)\n• No — basic features only",
        "install.complete": "Installation complete",
        "install.error": "Installation error",
        "install.cancelled": "Cancelled",
        "install.preparing": "Preparing...",
        "install.step.python": "Checking Python",
        "install.step.venv": "Creating virtual environment",
        "install.step.deps_minimal": "Installing basic dependencies",
        "install.step.deps_full": "Installing full dependencies",
        "install.step.done": "Done!",
        
        # Update
        "update.available": "🔄 Update available",
        "update.title": "Update",
        "update.question": "Install version {version}?\n\nYour settings and data will be preserved.",
        "update.complete": "Update complete",
        "update.error": "Update error",
        "update.desc": "New version ready to install",
        "update.published": "Published: {date}",
        
        # Models page
        "models.title": "AI Models",
        "models.subtitle": "Manage local AI models via Ollama",
        "models.ollama_status": "Ollama Status",
        "models.ollama.running": "● Running",
        "models.ollama.stopped": "● Stopped",
        "models.ollama.not_installed": "● Not installed",
        "models.ollama.install": "Install Ollama",
        "models.ollama.start": "Start",
        "models.ollama.stop": "Stop",
        "models.installed": "Installed Models",
        "models.no_models": "No models installed",
        "models.add_model": "Add Model",
        "models.btn.download": "Download",
        "models.btn.remove": "Remove",
        "models.downloading": "Downloading...",
        "models.default_hint": "Recommended model: {model}",
        
        # Settings page
        "settings.title": "Settings",
        "settings.subtitle": "Launcher and update settings",
        "settings.paths": "📁  Paths",
        "settings.client_path": "Client path",
        "settings.browse": "Browse...",
        "settings.updates": "🔄  Updates",
        "settings.auto_check": "Automatically check for updates",
        "settings.pre_release": "Receive pre-release versions",
        "settings.ollama": "🤖  Ollama",
        "settings.auto_start": "Start Ollama with launcher",
        "settings.default_model": "Default model",
        "settings.interface": "🎨  Interface",
        "settings.language": "Interface language",
        "settings.theme": "Theme",
        "settings.theme.dark": "Dark",
        "settings.theme.light": "Light",
        "settings.save": "💾  Save Settings",
        "settings.saved": "Settings saved",
        
        # Debug page
        "debug.title": "Debug",
        "debug.subtitle": "Logs and diagnostics",
        "debug.logs": "📋  Logs",
        "debug.clear": "Clear",
        "debug.copy": "Copy",
        "debug.diagnostics": "🔍  Diagnostics",
        "debug.run_diagnostics": "Run Diagnostics",
        "debug.report": "📝  Create Bug Report",
        "debug.bug_report": "Bug Report",
        
        # Common
        "common.yes": "Yes",
        "common.no": "No",
        "common.cancel": "Cancel",
        "common.ok": "OK",
        "common.error": "Error",
        "common.warning": "Warning",
        "common.info": "Information",
        "common.success": "Success",
        
        # News/Welcome
        "news.welcome.title": "Welcome to Arvis!",
        "news.welcome.desc": "Arvis is your personal AI assistant with voice control.",
        "news.quickstart.title": "Quick Start:",
        "news.quickstart.step1": "Click <b>Install</b> for first-time setup",
        "news.quickstart.step2": "Go to <b>Models</b> to download AI models",
        "news.quickstart.step3": "Click <b>Launch Arvis</b> to start",
    },
    
    "uk": {
        # App
        "app.title": "Arvis Launcher",
        "app.subtitle": "Персональний AI-асистент",
        
        # Navigation
        "nav.home": "🏠  Головна",
        "nav.models": "🤖  Моделі",
        "nav.settings": "⚙️  Налаштування",
        "nav.account": "👤  Обліковий запис",
        "nav.debug": "🔧  Відладка",
        
        # Home page
        "home.title": "Arvis AI Assistant",
        "home.subtitle": "Персональний AI-асистент",
        "home.status.stopped": "● Зупинено",
        "home.status.starting": "● Запускається...",
        "home.status.running": "● Працює",
        "home.status.not_installed": "● Не встановлено",
        "home.status.error": "● Помилка",
        "home.btn.launch": "🚀  Запустити Arvis",
        "home.btn.stop": "⏹  Зупинити",
        "home.btn.install": "📦  Встановити",
        "home.btn.update": "Оновити",
        
        # Installation
        "install.title": "Встановлення залежностей",
        "install.question": "Встановити повний набір залежностей?\n\n• Так — усі можливості (більше місця)\n• Ні — тільки базові функції",
        "install.complete": "Встановлення завершено",
        "install.error": "Помилка встановлення",
        "install.cancelled": "Скасовано",
        "install.preparing": "Підготовка...",
        "install.step.python": "Перевірка Python",
        "install.step.venv": "Створення віртуального середовища",
        "install.step.deps_minimal": "Встановлення базових залежностей",
        "install.step.deps_full": "Встановлення повних залежностей",
        "install.step.done": "Готово!",
        
        # Update
        "update.available": "🔄 Доступне оновлення",
        "update.title": "Оновлення",
        "update.question": "Встановити версію {version}?\n\nВаші налаштування та дані будуть збережені.",
        "update.complete": "Оновлення завершено",
        "update.error": "Помилка оновлення",
        "update.desc": "Нова версія готова до встановлення",
        "update.published": "Опубліковано: {date}",
        
        # Models page
        "models.title": "AI Моделі",
        "models.subtitle": "Керування локальними AI моделями через Ollama",
        "models.ollama_status": "Статус Ollama",
        "models.ollama.running": "● Запущено",
        "models.ollama.stopped": "● Зупинено",
        "models.ollama.not_installed": "● Не встановлено",
        "models.ollama.install": "Встановити Ollama",
        "models.ollama.start": "Запустити",
        "models.ollama.stop": "Зупинити",
        "models.installed": "Встановлені моделі",
        "models.no_models": "Немає встановлених моделей",
        "models.add_model": "Додати модель",
        "models.btn.download": "Завантажити",
        "models.btn.remove": "Видалити",
        "models.downloading": "Завантаження...",
        "models.default_hint": "Рекомендована модель: {model}",
        
        # Settings page
        "settings.title": "Налаштування",
        "settings.subtitle": "Налаштування лаунчера та оновлень",
        "settings.paths": "📁  Шляхи",
        "settings.client_path": "Шлях до клієнта",
        "settings.browse": "Огляд...",
        "settings.updates": "🔄  Оновлення",
        "settings.auto_check": "Автоматично перевіряти оновлення",
        "settings.pre_release": "Отримувати pre-release версії",
        "settings.ollama": "🤖  Ollama",
        "settings.auto_start": "Запускати Ollama при старті лаунчера",
        "settings.default_model": "Модель за замовчуванням",
        "settings.interface": "🎨  Інтерфейс",
        "settings.language": "Мова інтерфейсу",
        "settings.theme": "Тема оформлення",
        "settings.theme.dark": "Темна",
        "settings.theme.light": "Світла",
        "settings.save": "💾  Зберегти налаштування",
        "settings.saved": "Налаштування збережено",
        
        # Debug page
        "debug.title": "Відладка",
        "debug.subtitle": "Логи та діагностика",
        "debug.logs": "📋  Логи",
        "debug.clear": "Очистити",
        "debug.copy": "Копіювати",
        "debug.diagnostics": "🔍  Діагностика",
        "debug.run_diagnostics": "Запустити діагностику",
        "debug.report": "📝  Створити звіт про помилку",
        "debug.bug_report": "Баг-репорт",
        
        # Common
        "common.yes": "Так",
        "common.no": "Ні",
        "common.cancel": "Скасувати",
        "common.ok": "ОК",
        "common.error": "Помилка",
        "common.warning": "Попередження",
        "common.info": "Інформація",
        "common.success": "Успішно",
        
        # News/Welcome
        "news.welcome.title": "Ласкаво просимо до Arvis!",
        "news.welcome.desc": "Arvis — це ваш персональний AI-асистент з голосовим керуванням.",
        "news.quickstart.title": "Швидкий старт:",
        "news.quickstart.step1": "Натисніть <b>Встановити</b> для першого налаштування",
        "news.quickstart.step2": "Перейдіть до <b>Моделі</b> для завантаження AI-моделей",
        "news.quickstart.step3": "Натисніть <b>Запустити Arvis</b> для початку роботи",
    }
}

# Language names for UI
LANGUAGE_NAMES = {
    "ru": "Русский",
    "en": "English", 
    "uk": "Українська",
}


class I18n:
    """Internationalization manager"""
    
    _instance: Optional['I18n'] = None
    _current_lang: str = DEFAULT_LANG
    
    @classmethod
    def instance(cls) -> 'I18n':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        self._lang = DEFAULT_LANG
        self._custom_translations: Dict[str, Dict[str, str]] = {}
    
    @property
    def current_language(self) -> str:
        return self._lang
    
    def set_language(self, lang: str) -> None:
        """Set current language"""
        if lang in TRANSLATIONS:
            self._lang = lang
            I18n._current_lang = lang
        else:
            print(f"[i18n] Warning: unknown language '{lang}', using '{DEFAULT_LANG}'")
            self._lang = DEFAULT_LANG
    
    def get(self, key: str, **kwargs) -> str:
        """Get translated string by key"""
        # Try current language
        text = TRANSLATIONS.get(self._lang, {}).get(key)
        
        # Try custom translations
        if text is None:
            text = self._custom_translations.get(self._lang, {}).get(key)
        
        # Fallback to default language
        if text is None:
            text = TRANSLATIONS.get(DEFAULT_LANG, {}).get(key)
        
        # Fallback to key itself
        if text is None:
            text = key
        
        # Format with kwargs
        if kwargs:
            try:
                text = text.format(**kwargs)
            except KeyError:
                pass
        
        return text
    
    def load_custom(self, path: Path) -> bool:
        """Load custom translations from JSON file"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for lang, trans in data.items():
                    if lang not in self._custom_translations:
                        self._custom_translations[lang] = {}
                    self._custom_translations[lang].update(trans)
            return True
        except Exception as e:
            print(f"[i18n] Error loading custom translations: {e}")
            return False
    
    @staticmethod
    def available_languages() -> Dict[str, str]:
        """Get available languages with their display names"""
        return LANGUAGE_NAMES.copy()


# Global instance
_i18n = I18n.instance()


def tr(key: str, **kwargs) -> str:
    """Translate a string (shortcut function)"""
    return _i18n.get(key, **kwargs)


def set_language(lang: str) -> None:
    """Set current language (shortcut function)"""
    _i18n.set_language(lang)


def get_language() -> str:
    """Get current language (shortcut function)"""
    return _i18n.current_language


def available_languages() -> Dict[str, str]:
    """Get available languages (shortcut function)"""
    return _i18n.available_languages()
