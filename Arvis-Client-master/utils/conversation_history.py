"""
Conversation history manager for Arvis
Handles persistent storage and retrieval of conversation history
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from utils.logger import ModuleLogger


class ConversationHistory:
    """Manages conversation history with persistent storage"""

    def __init__(self, config):
        self.config = config
        self.logger = ModuleLogger("ConversationHistory")

        # История текущей сессии
        self.messages: List[Dict[str, Any]] = []

        # Настройки
        self.max_messages = config.get("history.max_messages", 50)
        self.save_to_file = config.get("history.save_to_file", True)
        self.auto_save_interval = config.get("history.auto_save_interval", 5)  # каждые N сообщений

        # Путь к файлу истории
        data_path = Path(config.get("paths.data", "data"))
        data_path.mkdir(parents=True, exist_ok=True)
        self.history_file = data_path / "conversation_history.json"

        # Папка для архива старых сессий
        self.archive_dir = data_path / "conversation_archive"
        self.archive_dir.mkdir(parents=True, exist_ok=True)

        # Счётчик для автосохранения
        self._save_counter = 0

        # Загружаем историю при инициализации
        if self.save_to_file:
            self.load_from_file()

    def add_message(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        """Добавить сообщение в историю

        Args:
            role: 'user' или 'assistant'
            content: текст сообщения
            metadata: дополнительные данные (timestamp, модуль и т.п.)
        """
        message: Dict[str, Any] = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        }

        if metadata:
            message["metadata"] = dict(metadata)
        else:
            message["metadata"] = {}

        self.messages.append(message)

        # Ограничиваем размер истории
        if self.max_messages > 0 and len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages :]

        # Автосохранение каждые N сообщений
        self._save_counter += 1
        if self.save_to_file and self._save_counter >= self.auto_save_interval:
            self._save_counter = 0
            self.save_to_file_async()

    def get_recent(self, count: int = 6) -> List[Dict[str, Any]]:
        """Получить последние N сообщений для контекста LLM"""
        return self.messages[-count:] if count > 0 else self.messages

    def get_all(self) -> List[Dict[str, Any]]:
        """Получить всю историю текущей сессии"""
        return self.messages.copy()

    def remove_last_message(self, role: Optional[str] = None) -> bool:
        """Удалить последнее сообщение из истории

        Args:
            role: Если указано, удаляет последнее сообщение этой роли (user/assistant)
                  Если None, удаляет самое последнее сообщение

        Returns:
            bool: True если сообщение удалено, False если не найдено
        """
        try:
            if not self.messages:
                self.logger.warning("Cannot remove message: history is empty")
                return False

            if role is None:
                # Удаляем последнее сообщение любой роли
                removed_msg = self.messages.pop()
                self.logger.info(f"Removed last message (role={removed_msg.get('role')})")
                return True
            else:
                # Ищем последнее сообщение указанной роли
                for i in range(len(self.messages) - 1, -1, -1):
                    if self.messages[i].get("role") == role:
                        removed_msg = self.messages.pop(i)
                        self.logger.info(f"Removed last '{role}' message at index {i}")
                        return True

                self.logger.warning(f"No message with role='{role}' found")
                return False

        except Exception as e:
            self.logger.error(f"Error removing last message: {e}")
            return False

    def clear(self):
        """Очистить историю текущей сессии"""
        # Архивируем текущую сессию перед очисткой
        if self.save_to_file and self.messages:
            self._archive_current_session()

        self.messages.clear()
        self._save_counter = 0
        self.logger.info("Conversation history cleared")

    def save_to_file_sync(self):
        """Синхронное сохранение в файл"""
        if not self.save_to_file:
            return

        try:
            data = {
                "session_start": self.messages[0]["timestamp"] if self.messages else None,
                "session_last": self.messages[-1]["timestamp"] if self.messages else None,
                "message_count": len(self.messages),
                "messages": self.messages,
            }

            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            self.logger.debug(f"History saved: {len(self.messages)} messages")

        except Exception as e:
            self.logger.error(f"Failed to save history: {e}")

    def save_to_file_async(self):
        """Асинхронное сохранение в фоне (не блокирует UI)"""
        try:
            from utils.async_manager import task_manager

            def save_worker():
                self.save_to_file_sync()
                return True

            task_id = f"save_history_{int(datetime.now().timestamp() * 1000)}"
            task_manager.run_async(task_id, save_worker)

        except Exception as e:
            # Фоллбэк на синхронное сохранение
            self.logger.debug(f"Async save failed, using sync: {e}")
            self.save_to_file_sync()

    def load_from_file(self):
        """Загрузить историю из файла"""
        if not self.history_file.exists():
            self.logger.info("No existing history file found, starting fresh")
            return

        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            messages = data.get("messages", [])

            # Ограничиваем загружаемую историю
            if self.max_messages > 0 and len(messages) > self.max_messages:
                messages = messages[-self.max_messages :]

            self.messages = messages
            self.logger.info(f"Loaded {len(messages)} messages from history")

        except Exception as e:
            self.logger.error(f"Failed to load history: {e}")
            self.messages = []

    def _archive_current_session(self):
        """Архивировать текущую сессию"""
        if not self.messages:
            return

        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_file = self.archive_dir / f"session_{timestamp}.json"

            data = {
                "session_start": self.messages[0]["timestamp"],
                "session_end": self.messages[-1]["timestamp"],
                "message_count": len(self.messages),
                "messages": self.messages,
            }

            with open(archive_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            self.logger.info(f"Session archived: {archive_file.name}")

        except Exception as e:
            self.logger.error(f"Failed to archive session: {e}")

    def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Поиск в истории по тексту

        Args:
            query: поисковый запрос
            limit: максимум результатов

        Returns:
            Список сообщений, содержащих запрос
        """
        query_lower = query.lower()
        results = []

        for msg in reversed(self.messages):  # Начинаем с конца (свежие первыми)
            if query_lower in msg.get("content", "").lower():
                results.append(msg)
                if len(results) >= limit:
                    break

        return results

    def set_message_feedback(self, message_content: str, feedback: str) -> bool:
        """Сохранить оценку для последнего подходящего ответа ассистента."""
        if feedback not in {"positive", "negative"}:
            self.logger.warning(f"Unsupported feedback value: {feedback}")
            return False

        content_to_match = (message_content or "").strip()

        for msg in reversed(self.messages):
            if msg.get("role") != "assistant":
                continue
            if (msg.get("content") or "").strip() != content_to_match:
                continue

            msg["feedback"] = feedback
            msg.setdefault("metadata", {})["feedback"] = feedback
            msg["feedback_timestamp"] = datetime.now().isoformat()

            if self.save_to_file:
                self.save_to_file_async()

            self.logger.debug(f"Feedback '{feedback}' saved for assistant message")
            return True

        self.logger.warning("Failed to match assistant message for feedback")
        return False

    def get_statistics(self) -> Dict[str, Any]:
        """Получить статистику по истории"""
        if not self.messages:
            return {
                "total_messages": 0,
                "user_messages": 0,
                "assistant_messages": 0,
                "session_start": None,
                "session_duration": None,
            }

        user_count = sum(1 for m in self.messages if m.get("role") == "user")
        assistant_count = sum(1 for m in self.messages if m.get("role") == "assistant")
        positive_feedback = sum(1 for m in self.messages if m.get("feedback") == "positive")
        negative_feedback = sum(1 for m in self.messages if m.get("feedback") == "negative")

        start_time = None
        end_time = None

        try:
            start_time = datetime.fromisoformat(self.messages[0]["timestamp"])
            end_time = datetime.fromisoformat(self.messages[-1]["timestamp"])
            duration = (end_time - start_time).total_seconds()
        except Exception:
            duration = None

        return {
            "total_messages": len(self.messages),
            "user_messages": user_count,
            "assistant_messages": assistant_count,
            "positive_feedback": positive_feedback,
            "negative_feedback": negative_feedback,
            "session_start": self.messages[0]["timestamp"] if self.messages else None,
            "session_duration_seconds": duration,
        }

    def export_to_text(self, output_path: Optional[Path] = None) -> str:
        """Экспортировать историю в читаемый текстовый формат

        Args:
            output_path: путь для сохранения (опционально)

        Returns:
            Текстовое представление истории
        """
        lines = []
        lines.append("=" * 80)
        lines.append("ИСТОРИЯ РАЗГОВОРА С ARVIS")
        lines.append("=" * 80)
        lines.append("")

        stats = self.get_statistics()
        lines.append(f"Всего сообщений: {stats['total_messages']}")
        lines.append(f"От пользователя: {stats['user_messages']}")
        lines.append(f"От Arvis: {stats['assistant_messages']}")

        if stats["session_start"]:
            lines.append(f"Начало сессии: {stats['session_start']}")

        if stats["session_duration_seconds"]:
            duration_min = stats["session_duration_seconds"] / 60
            lines.append(f"Длительность: {duration_min:.1f} минут")

        lines.append("")
        lines.append("-" * 80)
        lines.append("")

        for msg in self.messages:
            role_label = "ПОЛЬЗОВАТЕЛЬ" if msg["role"] == "user" else "ARVIS"
            timestamp = msg.get("timestamp", "")

            # Форматируем timestamp
            try:
                dt = datetime.fromisoformat(timestamp)
                time_str = dt.strftime("%H:%M:%S")
            except Exception:
                time_str = timestamp

            lines.append(f"[{time_str}] {role_label}:")
            lines.append(msg["content"])
            feedback = msg.get("feedback")
            if feedback == "positive":
                lines.append("Оценка: хороший ответ")
            elif feedback == "negative":
                lines.append("Оценка: плохой ответ")
            lines.append("")

        text = "\n".join(lines)

        # Сохраняем в файл если указан путь
        if output_path:
            try:
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(text)
                self.logger.info(f"History exported to: {output_path}")
            except Exception as e:
                self.logger.error(f"Failed to export history: {e}")

        return text

    def import_from_json(self, file_path: Path):
        """Импортировать историю из JSON файла"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            messages = data.get("messages", [])

            if not messages:
                self.logger.warning(f"No messages found in {file_path}")
                return

            # Добавляем к текущей истории (не заменяем)
            self.messages.extend(messages)

            # Ограничиваем размер
            if self.max_messages > 0 and len(self.messages) > self.max_messages:
                self.messages = self.messages[-self.max_messages :]

            self.logger.info(f"Imported {len(messages)} messages from {file_path}")

        except Exception as e:
            self.logger.error(f"Failed to import history: {e}")

    def shutdown(self):
        """Сохранить историю перед завершением работы"""
        if self.save_to_file:
            self.logger.info("Saving conversation history on shutdown...")
            self.save_to_file_sync()
