"""
Calendar module for Arvis with AI-powered reminders
"""

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from config.config import Config
from utils.logger import ModuleLogger
from utils.security import AuditEventType, AuditSeverity, Permission, get_audit_logger, get_rbac_manager


class CalendarModule:
    """Calendar and reminders module with AI integration"""

    def __init__(self, config: Config):
        self.config = config
        self.logger = ModuleLogger("CalendarModule")

        # RBAC и Audit (v1.4.0: Phase 2)
        self.rbac_enabled = bool(
            self.config.get("security.rbac.enabled", self.config.get("security.rbac_enabled", False))
        )
        self.rbac = get_rbac_manager() if self.rbac_enabled else None
        self.audit = get_audit_logger(config)
        self.current_user = None

        # Database setup
        self.db_path = Path("data/calendar.db")
        self.db_path.parent.mkdir(exist_ok=True)

        self.init_database()

    def set_current_user(self, user_id: Optional[str]):
        """Установить текущего пользователя для RBAC проверок"""
        self.current_user = user_id
        if self.rbac:
            self.rbac.set_current_user(user_id)

    def init_database(self):
        """Initialize SQLite database for calendar data"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Create reminders table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS reminders (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        description TEXT,
                        datetime TEXT NOT NULL,
                        is_completed BOOLEAN DEFAULT FALSE,
                        reminder_type TEXT DEFAULT 'reminder',
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """
                )

                # Create events table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        description TEXT,
                        start_datetime TEXT NOT NULL,
                        end_datetime TEXT,
                        location TEXT,
                        is_all_day BOOLEAN DEFAULT FALSE,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """
                )

                conn.commit()
                self.logger.info("Calendar database initialized")

        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")

    def add_reminder(self, title: str, datetime_str: str, description: str = "") -> str:
        """Add a new reminder"""
        # RBAC: проверка разрешений
        if self.rbac and not self.rbac.has_permission(Permission.MODULE_CALENDAR):
            self.audit.log_event(
                event_type=AuditEventType.PERMISSION_DENIED,
                action="add_reminder",
                user_id=self.current_user,
                severity=AuditSeverity.WARNING,
                details={"module": "calendar", "title": title},
                success=False,
            )
            return "❌ У вас нет прав для использования модуля календаря"

        try:
            # Parse datetime
            reminder_datetime = self.parse_datetime(datetime_str)
            if not reminder_datetime:
                return (
                    "❌ Не удалось распознать дату и время. Используйте формат: 'YYYY-MM-DD HH:MM' или '15:30 завтра'"
                )

            # Save to database
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO reminders (title, description, datetime)
                    VALUES (?, ?, ?)
                """,
                    (title, description, reminder_datetime.isoformat()),
                )

                conn.commit()
                reminder_id = cursor.lastrowid

            formatted_date = reminder_datetime.strftime("%d.%m.%Y в %H:%M")
            self.logger.info(f"Added reminder: {title} at {formatted_date}")

            return f"✅ Напоминание добавлено:\n📝 {title}\n📅 {formatted_date}"

        except Exception as e:
            self.logger.error(f"Error adding reminder: {e}")
            return f"❌ Ошибка добавления напоминания: {str(e)}"

    def parse_datetime(self, datetime_str: str) -> Optional[datetime]:
        """Parse various datetime formats"""
        datetime_str = datetime_str.lower().strip()
        now = datetime.now()

        try:
            # Standard format: YYYY-MM-DD HH:MM
            if len(datetime_str) >= 16 and "-" in datetime_str and ":" in datetime_str:
                return datetime.fromisoformat(datetime_str.replace("T", " "))

            # Time only (today)
            if ":" in datetime_str and len(datetime_str) <= 5:
                time_part = datetime_str
                today = now.date()
                time_obj = datetime.strptime(time_part, "%H:%M").time()
                return datetime.combine(today, time_obj)

            # Relative time parsing
            if "завтра" in datetime_str:
                tomorrow = now + timedelta(days=1)
                if ":" in datetime_str:
                    time_part = datetime_str.split()[-1]
                    if ":" in time_part:
                        time_obj = datetime.strptime(time_part, "%H:%M").time()
                        return datetime.combine(tomorrow.date(), time_obj)
                else:
                    return tomorrow.replace(hour=9, minute=0, second=0, microsecond=0)

            elif "послезавтра" in datetime_str:
                day_after = now + timedelta(days=2)
                if ":" in datetime_str:
                    time_part = datetime_str.split()[-1]
                    if ":" in time_part:
                        time_obj = datetime.strptime(time_part, "%H:%M").time()
                        return datetime.combine(day_after.date(), time_obj)
                else:
                    return day_after.replace(hour=9, minute=0, second=0, microsecond=0)

            elif "через" in datetime_str:
                # "через 30 минут", "через 2 часа", "через 3 дня"
                parts = datetime_str.split()
                if len(parts) >= 3:
                    try:
                        amount = int(parts[1])
                        unit = parts[2]

                        if "минут" in unit:
                            return now + timedelta(minutes=amount)
                        elif "час" in unit:
                            return now + timedelta(hours=amount)
                        elif "дн" in unit or "день" in unit:
                            return now + timedelta(days=amount)
                    except ValueError:
                        pass

            # Days of week
            weekdays = {
                "понедельник": 0,
                "вторник": 1,
                "среда": 2,
                "четверг": 3,
                "пятница": 4,
                "суббота": 5,
                "воскресенье": 6,
            }

            for day_name, day_num in weekdays.items():
                if day_name in datetime_str:
                    days_ahead = day_num - now.weekday()
                    if days_ahead <= 0:  # Target day already happened this week
                        days_ahead += 7
                    target_date = now + timedelta(days=days_ahead)

                    if ":" in datetime_str:
                        time_part = datetime_str.split()[-1]
                        if ":" in time_part:
                            time_obj = datetime.strptime(time_part, "%H:%M").time()
                            return datetime.combine(target_date.date(), time_obj)
                    else:
                        return target_date.replace(hour=9, minute=0, second=0, microsecond=0)

        except Exception as e:
            self.logger.debug(f"Datetime parsing error: {e}")

        return None

    def get_upcoming_reminders(self, days: int = 7) -> str:
        """Get upcoming reminders"""
        try:
            end_date = datetime.now() + timedelta(days=days)

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT id, title, description, datetime, is_completed
                    FROM reminders
                    WHERE datetime >= ? AND datetime <= ? AND is_completed = FALSE
                    ORDER BY datetime ASC
                """,
                    (datetime.now().isoformat(), end_date.isoformat()),
                )

                reminders = cursor.fetchall()

            if not reminders:
                return f"📅 Нет напоминаний на ближайшие {days} дней"

            response = f"📅 Предстоящие напоминания ({len(reminders)}):\n\n"

            for reminder_id, title, description, datetime_str, is_completed in reminders:
                reminder_datetime = datetime.fromisoformat(datetime_str)
                formatted_date = reminder_datetime.strftime("%d.%m в %H:%M")

                # Calculate time until reminder
                time_until = reminder_datetime - datetime.now()
                if time_until.days > 0:
                    time_desc = f"(через {time_until.days} дн.)"
                elif time_until.seconds > 3600:
                    hours = time_until.seconds // 3600
                    time_desc = f"(через {hours} ч.)"
                elif time_until.seconds > 60:
                    minutes = time_until.seconds // 60
                    time_desc = f"(через {minutes} мин.)"
                else:
                    time_desc = "(скоро!)"

                response += f"⏰ {formatted_date} {time_desc}\n"
                response += f"📝 {title}\n"
                if description:
                    response += f"📄 {description}\n"
                response += "\n"

            return response

        except Exception as e:
            self.logger.error(f"Error getting reminders: {e}")
            return f"❌ Ошибка получения напоминаний: {str(e)}"

    def complete_reminder(self, reminder_id: int) -> str:
        """Mark reminder as completed"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE reminders
                    SET is_completed = TRUE, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """,
                    (reminder_id,),
                )

                if cursor.rowcount > 0:
                    conn.commit()
                    return f"✅ Напоминание #{reminder_id} выполнено"
                else:
                    return f"❌ Напоминание #{reminder_id} не найдено"

        except Exception as e:
            self.logger.error(f"Error completing reminder: {e}")
            return f"❌ Ошибка: {str(e)}"

    def delete_reminder(self, reminder_id: int) -> str:
        """Delete reminder"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))

                if cursor.rowcount > 0:
                    conn.commit()
                    return f"✅ Напоминание #{reminder_id} удалено"
                else:
                    return f"❌ Напоминание #{reminder_id} не найдено"

        except Exception as e:
            self.logger.error(f"Error deleting reminder: {e}")
            return f"❌ Ошибка: {str(e)}"

    def add_event(
        self, title: str, start_datetime_str: str, end_datetime_str: str = "", description: str = "", location: str = ""
    ) -> str:
        """Add calendar event"""
        try:
            start_datetime = self.parse_datetime(start_datetime_str)
            if not start_datetime:
                return "❌ Не удалось распознать дату начала события"

            end_datetime = None
            if end_datetime_str:
                end_datetime = self.parse_datetime(end_datetime_str)

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO events (title, description, start_datetime, end_datetime, location)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    (
                        title,
                        description,
                        start_datetime.isoformat(),
                        end_datetime.isoformat() if end_datetime else None,
                        location,
                    ),
                )

                conn.commit()
                event_id = cursor.lastrowid

            formatted_start = start_datetime.strftime("%d.%m.%Y в %H:%M")
            response = f"✅ Событие добавлено:\n📝 {title}\n📅 {formatted_start}"

            if end_datetime:
                formatted_end = end_datetime.strftime("%d.%m.%Y в %H:%M")
                response += f" - {formatted_end}"

            if location:
                response += f"\n📍 {location}"

            return response

        except Exception as e:
            self.logger.error(f"Error adding event: {e}")
            return f"❌ Ошибка добавления события: {str(e)}"

    def get_today_schedule(self) -> str:
        """Get today's schedule"""
        try:
            today = datetime.now().date()
            tomorrow = today + timedelta(days=1)

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Get today's events
                cursor.execute(
                    """
                    SELECT title, description, start_datetime, end_datetime, location
                    FROM events
                    WHERE date(start_datetime) = ?
                    ORDER BY start_datetime ASC
                """,
                    (today.isoformat(),),
                )

                events = cursor.fetchall()

                # Get today's reminders
                cursor.execute(
                    """
                    SELECT title, description, datetime
                    FROM reminders
                    WHERE date(datetime) = ? AND is_completed = FALSE
                    ORDER BY datetime ASC
                """,
                    (today.isoformat(),),
                )

                reminders = cursor.fetchall()

            if not events and not reminders:
                return "📅 На сегодня ничего не запланировано"

            response = f"📅 Расписание на сегодня ({today.strftime('%d.%m.%Y')}):\n\n"

            # Combine and sort events and reminders
            schedule_items = []

            for event in events:
                title, description, start_dt_str, end_dt_str, location = event
                start_dt = datetime.fromisoformat(start_dt_str)
                schedule_items.append((start_dt, "event", event))

            for reminder in reminders:
                title, description, dt_str = reminder
                dt = datetime.fromisoformat(dt_str)
                schedule_items.append((dt, "reminder", reminder))

            # Sort by time
            schedule_items.sort(key=lambda x: x[0])

            for dt, item_type, item_data in schedule_items:
                time_str = dt.strftime("%H:%M")

                if item_type == "event":
                    title, description, start_dt_str, end_dt_str, location = item_data
                    response += f"📆 {time_str} - {title}\n"
                    if end_dt_str:
                        end_dt = datetime.fromisoformat(end_dt_str)
                        response += f"    ⏰ до {end_dt.strftime('%H:%M')}\n"
                    if location:
                        response += f"    📍 {location}\n"

                else:  # reminder
                    title, description, dt_str = item_data
                    response += f"⏰ {time_str} - {title}\n"

                if item_data[1]:  # description
                    response += f"    📝 {item_data[1]}\n"
                response += "\n"

            return response

        except Exception as e:
            self.logger.error(f"Error getting today's schedule: {e}")
            return f"❌ Ошибка получения расписания: {str(e)}"

    def process_natural_reminder(self, text: str, llm_client=None) -> str:
        """Process natural language reminder using AI"""
        try:
            # Simple keyword extraction for now
            # In a full implementation, this would use the LLM to extract:
            # - Task/reminder title
            # - Date/time
            # - Additional details

            # Basic patterns
            if any(word in text.lower() for word in ["напомни", "напоминание", "не забыть"]):
                # Try to extract time and task
                words = text.lower().split()

                # Look for time indicators
                time_indicators = [
                    "в",
                    "завтра",
                    "через",
                    "понедельник",
                    "вторник",
                    "среда",
                    "четверг",
                    "пятница",
                    "суббота",
                    "воскресенье",
                ]

                title_words = []
                datetime_words = []

                collecting_time = False
                for word in words:
                    if word in time_indicators or ":" in word:
                        collecting_time = True
                        datetime_words.append(word)
                    elif collecting_time:
                        datetime_words.append(word)
                        if word.endswith((".", ",", "!")):
                            collecting_time = False
                    elif not collecting_time and word not in ["напомни", "напоминание", "не", "забыть"]:
                        title_words.append(word)

                title = " ".join(title_words) if title_words else "Напоминание"
                datetime_str = " ".join(datetime_words) if datetime_words else "завтра 9:00"

                return self.add_reminder(title, datetime_str)

            else:
                return "❓ Не удалось распознать запрос на создание напоминания"

        except Exception as e:
            self.logger.error(f"Error processing natural reminder: {e}")
            return f"❌ Ошибка обработки: {str(e)}"

    def get_overdue_reminders(self) -> List[Tuple[int, str, str, datetime]]:
        """Get overdue reminders for notification"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT id, title, description, datetime
                    FROM reminders
                    WHERE datetime <= ? AND is_completed = FALSE
                    ORDER BY datetime ASC
                """,
                    (datetime.now().isoformat(),),
                )

                overdue = []
                for row in cursor.fetchall():
                    reminder_id, title, description, datetime_str = row
                    reminder_datetime = datetime.fromisoformat(datetime_str)
                    overdue.append((reminder_id, title, description, reminder_datetime))

                return overdue

        except Exception as e:
            self.logger.error(f"Error getting overdue reminders: {e}")
            return []

    def cleanup(self):
        """Cleanup calendar module"""
        self.logger.info("Calendar module cleanup complete")

    def get_status(self) -> Dict[str, Any]:
        """Get calendar module status"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute("SELECT COUNT(*) FROM reminders WHERE is_completed = FALSE")
                active_reminders = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM events WHERE start_datetime >= ?", (datetime.now().isoformat(),))
                upcoming_events = cursor.fetchone()[0]

            return {"database_ready": True, "active_reminders": active_reminders, "upcoming_events": upcoming_events}

        except Exception as e:
            self.logger.error(f"Error getting status: {e}")
            return {"database_ready": False, "error": str(e)}
