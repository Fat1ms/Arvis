from typing import Dict, Optional

from PyQt6.QtWidgets import QCheckBox, QComboBox, QGroupBox, QLabel, QLineEdit, QPushButton, QWidget


class I18N:
    """Simple i18n manager for runtime UI language switching without .qm files.
    Provides dictionary-based translations and utilities to translate Qt widgets.
    """

    _instance: Optional["I18N"] = None

    def __init__(self, lang: str = "ru"):
        self.lang = lang
        self._translations: Dict[str, Dict[str, str]] = {}
        self._build_defaults()

    @classmethod
    def get(cls) -> "I18N":
        if cls._instance is None:
            cls._instance = I18N()
        return cls._instance

    def set_language(self, lang: str):
        self.lang = lang or "ru"

    def t(self, text: str) -> str:
        if not text:
            return text
        table = self._translations.get(self.lang) or {}
        return table.get(text, text)

    def _build_defaults(self):
        # Base English translations
        en: Dict[str, str] = {
            # Common
            "Настройки Arvis": "Arvis Settings",
            "Настройки": "Settings",
            "Сохранить": "Save",
            "Отмена": "Cancel",
            "Сохранить и перезагрузить": "Save and Restart",
            # Sections
            "Общие": "General",
            "LLM": "LLM",
            "TTS | STT": "TTS | STT",
            "Язык": "Language",
            "Модули": "Modules",
            "Расширенные": "Advanced",
            # General tab
            "Пользователь": "User",
            "Имя:": "Name:",
            "Город:": "City:",
            "Запуск": "Startup",
            "Автозапуск Ollama": "Autostart Ollama",
            "Предзагрузка модели": "Preload model",
            "Сворачивать в трей": "Minimize to tray",
            "Автозапуск Arvis вместе с системой": "Start Arvis with system",
            # LLM tab
            "URL сервера:": "Server URL:",
            "Модель по умолчанию:": "Default model:",
            "Генерация": "Generation",
            "Температура:": "Temperature:",
            "Макс. токенов:": "Max tokens:",
            "Вывод ответа": "Output",
            "Режим:": "Mode:",
            "Реальный стрим": "Real streaming",
            "Симуляция (после генерации)": "Simulation (after generation)",
            "Отключено": "Disabled",
            # TTS/STT
            "Text-to-Speech": "Text-to-Speech",
            "Движок:": "Engine:",
            "Голос:": "Voice:",
            "Частота:": "Sample rate:",
            "Режим озвучки:": "TTS mode:",
            "Реальное время (стрим)": "Realtime (stream)",
            "По предложениям": "Sentence by sentence",
            "После завершения": "After complete",
            "Озвучивать сгенерированный текст": "Speak generated text",
            "Разрешить SAPI (Windows) как запасной вариант": "Allow SAPI (Windows) as fallback",
            "Speech-to-Text": "Speech-to-Text",
            "Слово активации:": "Wake word:",
            "Путь к модели:": "Model path:",
            "Обзор...": "Browse...",
            # Language tab
            "Язык интерфейса": "UI language",
            "Интерфейс:": "Interface:",
            "Речь (распознавание и озвучка)": "Speech (STT/TTS)",
            "Речь (STT/TTS):": "Speech (STT/TTS):",
            "Скачать/обновить модели Vosk для выбранного языка": "Download/Update Vosk models for selected language",
            "Модели Vosk": "Vosk models",
            "Ошибка загрузки": "Download error",
            # Modules
            "API Ключи": "API Keys",
            "OpenWeather:": "OpenWeather:",
            "NewsAPI:": "NewsAPI:",
            "Модули": "Modules",
            "Модуль погоды": "Weather module",
            "Модуль новостей": "News module",
            "Модуль календаря": "Calendar module",
            "Управление системой": "System control",
            "Голосовая активация": "Voice activation",
            # Advanced
            "Логирование": "Logging",
            "Уровень логов:": "Log level:",
            "Записывать логи в файл": "Write logs to file",
            "Пути": "Paths",
            "Папка логов:": "Logs folder:",
            "Папка моделей:": "Models folder:",
            "Управление логами": "Logs management",
            "Очистить старые логи": "Clear old logs",
            "Удалить все логи, кроме текущей сессии": "Delete all logs except current session",
            "Очистка логов": "Clear logs",
            "Папка логов не найдена.": "Logs folder not found.",
            "Удалено файлов логов: ": "Deleted log files: ",
            "Текущая сессия сохранена.": "Current session preserved.",
            "Ошибка": "Error",
            # ChatPanel tooltips and labels
            "Введите сообщение...": "Type a message...",
            "Голосовой ввод": "Voice input",
            "Отправить сообщение": "Send message",
            "Отменить текущий запрос": "Cancel current request",
            "Очистить чат": "Clear chat",
            "Остановить голос": "Stop voice",
            "Показать/Скрыть орб": "Show/Hide orb",
            "Настройки": "Settings",
            "Микрофон активен": "Microphone active",
            "Arvis печатает…": "Arvis is typing…",
            "Arvis думает…": "Arvis is thinking…",
            "Чат очищен. Как дела?": "Chat cleared. How are you?",
            "История разговоров": "Chat history",
            "Всего": "Total",
            "От вас": "From you",
            "От Arvis": "From Arvis",
            "🔍 Поиск по истории...": "Search history...",
            "Очистить поиск": "Clear search",
            "Экспорт": "Export",
            "Очистить историю": "Clear history",
            "Закрыть": "Close",
            "Ошибка загрузки истории": "Failed to load history",
            "📭 История пуста": "History is empty",
            "Ничего не найдено по запросу: {query}": "No results for: {query}",
            "Экспортировать историю": "Export history",
            "Экспортировать историю в текстовый файл": "Export history to a text file",
            "Текстовые файлы (*.txt);;Все файлы (*)": "Text files (*.txt);;All files (*)",
            "Экспорт завершён": "Export complete",
            "История успешно экспортирована в:\n{path}": "History saved to:\n{path}",
            "Ошибка экспорта": "Export error",
            "Не удалось экспортировать историю:\n{error}": "Could not export history:\n{error}",
            "Подтверждение": "Confirmation",
            "Вы уверены, что хотите очистить всю историю?\n\nТекущая сессия будет архивирована в:\n{path}": "Are you sure you want to clear history?\n\nThe session will be archived to:\n{path}",
            "История очищена": "History cleared",
            "История успешно очищена и архивирована": "History cleared and archived",
            "Очистить всю историю (с архивацией)": "Clear entire history (with archiving)",
            "Не удалось очистить историю:\n{error}": "Failed to clear history:\n{error}",
            "Положительных оценок": "Positive ratings",
            "Отрицательных оценок": "Negative ratings",
            "👤 Вы": "👤 You",
            "🤖 Arvis": "🤖 Arvis",
            "👍 Хороший ответ": "👍 Good response",
            "👎 Плохой ответ": "👎 Poor response",
            "✓ Отзыв принят: Хороший ответ": "Feedback saved: good response",
            "✗ Отзыв принят: Плохой ответ": "Feedback saved: poor response",
            "⚠️ Не удалось сохранить оценку.": "Couldn't save feedback.",
            "История недоступна": "History unavailable",
            "Система истории разговоров ещё не инициализирована.\nПожалуйста, подождите.": "Chat history system isn't ready yet.\nPlease wait.",
            "Не удалось открыть историю:\n{error}": "Couldn't open history:\n{error}",
            "🔎 Источники:": "🔎 Sources:",
            "Источник": "Source",
            "Google Search API:": "Google Search API:",
            "ID поисковой системы (CX):": "Search engine ID (CX):",
            "Веб-поиск Google": "Google Web Search",
        }

        es: Dict[str, str] = {
            "Настройки Arvis": "Configuración de Arvis",
            "Настройки": "Configuración",
            "Сохранить": "Guardar",
            "Отмена": "Cancelar",
            "Сохранить и перезагрузить": "Guardar y reiniciar",
            "Общие": "General",
            "Язык": "Idioma",
            "Модули": "Módulos",
            "Расширенные": "Avanzado",
            # ... (short set for demo)
            "Введите сообщение...": "Escribe un mensaje...",
            "История разговоров": "Historial de chat",
            "Всего": "Total",
            "От вас": "De ti",
            "От Arvis": "De Arvis",
            "🔍 Поиск по истории...": "Buscar en el historial...",
            "Очистить поиск": "Limpiar búsqueda",
            "Экспорт": "Exportar",
            "Очистить историю": "Borrar historial",
            "Закрыть": "Cerrar",
            "Ошибка загрузки истории": "Error al cargar el historial",
            "📭 История пуста": "El historial está vacío",
            "Ничего не найдено по запросу: {query}": "No se encontró nada para: {query}",
            "Экспортировать историю": "Exportar historial",
            "Экспортировать историю в текстовый файл": "Exportar historial a un archivo de texto",
            "Текстовые файлы (*.txt);;Все файлы (*)": "Archivos de texto (*.txt);;Todos los archivos (*)",
            "Экспорт завершён": "Exportación completada",
            "История успешно экспортирована в:\n{path}": "Historial guardado en:\n{path}",
            "Ошибка экспорта": "Error de exportación",
            "Не удалось экспортировать историю:\n{error}": "No se pudo exportar el historial:\n{error}",
            "Подтверждение": "Confirmación",
            "Вы уверены, что хотите очистить всю историю?\n\nТекущая сессия будет архивирована в:\n{path}": "¿Seguro que quieres borrar el historial?\n\nLa sesión se archivará en:\n{path}",
            "История очищена": "Historial borrado",
            "История успешно очищена и архивирована": "Historial borrado y archivado",
            "Очистить всю историю (с архивацией)": "Borrar todo el historial (con archivo)",
            "Не удалось очистить историю:\n{error}": "No se pudo borrar el historial:\n{error}",
            "Положительных оценок": "Valoraciones positivas",
            "Отрицательных оценок": "Valoraciones negativas",
            "👤 Вы": "👤 Tú",
            "🤖 Arvis": "🤖 Arvis",
            "👍 Хороший ответ": "👍 Buena respuesta",
            "👎 Плохой ответ": "👎 Mala respuesta",
            "✓ Отзыв принят: Хороший ответ": "Comentario guardado: buena respuesta",
            "✗ Отзыв принят: Плохой ответ": "Comentario guardado: mala respuesta",
            "⚠️ Не удалось сохранить оценку.": "No se pudo guardar el comentario.",
            "История недоступна": "Historial no disponible",
            "Система истории разговоров ещё не инициализирована.\nПожалуйста, подождите.": "El historial aún no está listo.\nPor favor, espera.",
            "Не удалось открыть историю:\n{error}": "No se pudo abrir el historial:\n{error}",
            "🔎 Источники:": "🔎 Fuentes:",
            "Источник": "Fuente",
            "Google Search API:": "Google Search API:",
            "ID поисковой системы (CX):": "ID del motor de búsqueda (CX):",
            "Веб-поиск Google": "Búsqueda web de Google",
        }

        uk: Dict[str, str] = {
            "Настройки Arvis": "Налаштування Arvis",
            "Настройки": "Налаштування",
            "Сохранить": "Зберегти",
            "Отмена": "Скасувати",
            "Сохранить и перезагрузить": "Зберегти і перезапустити",
            "Общие": "Загальні",
            "Язык": "Мова",
            "Модули": "Модулі",
            "Расширенные": "Розширені",
            "Введите сообщение...": "Введіть повідомлення...",
            "История разговоров": "Історія розмов",
            "Всего": "Всього",
            "От вас": "Від вас",
            "От Arvis": "Від Arvis",
            "🔍 Поиск по истории...": "Пошук по історії...",
            "Очистить поиск": "Очистити пошук",
            "Экспорт": "Експорт",
            "Очистить историю": "Очистити історію",
            "Закрыть": "Закрити",
            "Ошибка загрузки истории": "Помилка завантаження історії",
            "📭 История пуста": "Історія порожня",
            "Ничего не найдено по запросу: {query}": "Нічого не знайдено за запитом: {query}",
            "Экспортировать историю": "Експортувати історію",
            "Экспортировать историю в текстовый файл": "Експортувати історію у текстовий файл",
            "Текстовые файлы (*.txt);;Все файлы (*)": "Текстові файли (*.txt);;Усі файли (*)",
            "Экспорт завершён": "Експорт завершено",
            "История успешно экспортирована в:\n{path}": "Історію збережено в:\n{path}",
            "Ошибка экспорта": "Помилка експорту",
            "Не удалось экспортировать историю:\n{error}": "Не вдалося експортувати історію:\n{error}",
            "Подтверждение": "Підтвердження",
            "Вы уверены, что хотите очистить всю историю?\n\nТекущая сессия будет архивирована в:\n{path}": "Ви впевнені, що хочете очистити всю історію?\n\nСесію буде збережено в архів:\n{path}",
            "История очищена": "Історію очищено",
            "История успешно очищена и архивирована": "Історію очищено й заархівовано",
            "Очистить всю историю (с архивацией)": "Очистити всю історію (зі збереженням)",
            "Не удалось очистить историю:\n{error}": "Не вдалося очистити історію:\n{error}",
            "Положительных оценок": "Позитивних оцінок",
            "Отрицательных оценок": "Негативних оцінок",
            "👤 Вы": "👤 Ви",
            "🤖 Arvis": "🤖 Arvis",
            "👍 Хороший ответ": "👍 Хороша відповідь",
            "👎 Плохой ответ": "👎 Погана відповідь",
            "✓ Отзыв принят: Хороший ответ": "Відгук збережено: хороша відповідь",
            "✗ Отзыв принят: Плохой ответ": "Відгук збережено: погана відповідь",
            "⚠️ Не удалось сохранить оценку.": "Не вдалося зберегти оцінку.",
            "История недоступна": "Історія недоступна",
            "Система истории разговоров ещё не инициализирована.\nПожалуйста, подождите.": "Систему історії ще не ініціалізовано.\nБудь ласка, зачекайте.",
            "Не удалось открыть историю:\n{error}": "Не вдалося відкрити історію:\n{error}",
            "🔎 Источники:": "🔎 Джерела:",
            "Источник": "Джерело",
            "Google Search API:": "Google Search API:",
            "ID поисковой системы (CX):": "Ідентифікатор пошукової системи (CX):",
            "Веб-поиск Google": "Пошук Google",
        }

        # Russian is identity mapping (optional)
        ru: Dict[str, str] = {}

        self._translations = {
            "en": en,
            "es": es,
            "uk": uk,
            "ru": ru,
        }


# Shorthand for translating string literals


def _(text: str) -> str:
    return I18N.get().t(text)


def apply_to_widget_tree(root: QWidget):
    """Translate titles, texts, tooltips and combo items for a widget subtree."""
    t = I18N.get().t

    def translate_widget(w: QWidget):
        try:
            # Window title
            if hasattr(w, "windowTitle") and callable(getattr(w, "windowTitle")):
                title = w.windowTitle()
                if isinstance(title, str) and title:
                    w.setWindowTitle(t(title))

            if isinstance(w, QLabel):
                txt = w.text()
                if txt:
                    w.setText(t(txt))
                tip = w.toolTip()
                if tip:
                    w.setToolTip(t(tip))
            elif isinstance(w, QPushButton):
                txt = w.text()
                if txt:
                    w.setText(t(txt))
                tip = w.toolTip()
                if tip:
                    w.setToolTip(t(tip))
            elif isinstance(w, QGroupBox):
                w.setTitle(t(w.title()))
            elif isinstance(w, QCheckBox):
                txt = w.text()
                if txt:
                    w.setText(t(txt))
                tip = w.toolTip()
                if tip:
                    w.setToolTip(t(tip))
            elif isinstance(w, QLineEdit):
                ph = w.placeholderText()
                if ph:
                    w.setPlaceholderText(t(ph))
                tip = w.toolTip()
                if tip:
                    w.setToolTip(t(tip))
            elif isinstance(w, QComboBox):
                tip = w.toolTip()
                if tip:
                    w.setToolTip(t(tip))
                for i in range(w.count()):
                    w.setItemText(i, t(w.itemText(i)))
        except Exception:
            pass

    def walk(widget: QWidget):
        translate_widget(widget)
        for child in widget.findChildren(QWidget):
            walk(child)

    if root is not None:
        walk(root)
