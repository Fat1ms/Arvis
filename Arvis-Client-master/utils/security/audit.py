"""
Audit logging system for Arvis
Система аудита действий пользователей
"""

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from utils.logger import ModuleLogger


class AuditEventType(Enum):
    """Типы событий аудита"""

    # Аутентификация
    LOGIN_SUCCESS = "auth.login.success"
    LOGIN_FAILED = "auth.login.failed"
    LOGOUT = "auth.logout"
    PASSWORD_CHANGED = "auth.password.changed"

    # 2FA События (Phase 2 Day 5)
    TWO_FACTOR_ENABLED = "auth.2fa.enabled"
    TWO_FACTOR_DISABLED = "auth.2fa.disabled"
    TWO_FACTOR_VERIFIED = "auth.2fa.verified"
    TWO_FACTOR_FAILED = "auth.2fa.failed"
    TWO_FACTOR_RESET = "auth.2fa.reset"
    BACKUP_CODE_USED = "auth.backup_code.used"
    BACKUP_CODE_REGENERATED = "auth.backup_code.regenerated"

    # Управление пользователями
    USER_CREATED = "user.created"
    USER_DELETED = "user.deleted"
    USER_ROLE_CHANGED = "user.role.changed"
    USER_ACTIVATED = "user.activated"
    USER_DEACTIVATED = "user.deactivated"

    # Системные команды
    SYSTEM_SHUTDOWN = "system.shutdown"
    SYSTEM_RESTART = "system.restart"
    SYSTEM_LOCK = "system.lock"
    APP_LAUNCHED = "system.app.launched"
    WEBSITE_OPENED = "system.website.opened"
    PROCESS_KILLED = "system.process.killed"

    # Исполнение кода
    CODE_EXECUTED = "code.executed"
    SCRIPT_RUN = "script.run"
    WORKFLOW_EXECUTED = "workflow.executed"

    # История и данные
    HISTORY_EXPORTED = "history.exported"
    HISTORY_IMPORTED = "history.imported"
    HISTORY_CLEARED = "history.cleared"
    HISTORY_DELETED = "history.deleted"
    HISTORY_GDPR_ERASE = "history.gdpr.erase"

    # API
    API_CALL = "api.call"
    API_ERROR = "api.error"

    # Настройки
    SETTINGS_CHANGED = "settings.changed"

    # Безопасность
    PERMISSION_DENIED = "security.permission.denied"
    SUSPICIOUS_ACTIVITY = "security.suspicious"
    RATE_LIMIT_EXCEEDED = "security.rate_limit"


class AuditSeverity(Enum):
    """Уровни важности событий"""

    INFO = "info"  # Информационное событие
    WARNING = "warning"  # Предупреждение
    ERROR = "error"  # Ошибка
    CRITICAL = "critical"  # Критическое событие


@dataclass
class AuditEvent:
    """Событие аудита"""

    event_id: str
    timestamp: datetime
    event_type: AuditEventType
    severity: AuditSeverity
    user_id: Optional[str]
    username: Optional[str]
    ip_address: Optional[str]
    action: str
    details: Dict[str, Any]
    success: bool
    error_message: Optional[str] = None


class AuditLogger:
    """Логгер аудита действий"""

    def __init__(self, config=None, log_dir: Optional[Path] = None):
        self.logger = ModuleLogger("AuditLogger")
        self.config = config or {}

        # Настройка директории для логов
        if log_dir is None:
            data_path = Path(self.config.get("paths.data", "data"))
            log_dir = data_path / "audit"

        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Файл текущего лога
        self.current_log_file = self.log_dir / "audit.jsonl"

        # Настройки ротации
        self.max_log_size = self.config.get("audit.max_log_size", 10 * 1024 * 1024)  # 10 MB
        self.max_log_age_days = self.config.get("audit.max_log_age_days", 90)  # 90 дней

        # Буфер событий (для производительности)
        self.event_buffer: List[AuditEvent] = []
        self.buffer_size = 10

        self.logger.info("Audit logger initialized")

    def log_event(
        self,
        event_type: AuditEventType,
        action: str,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        ip_address: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        success: bool = True,
        severity: AuditSeverity = AuditSeverity.INFO,
        error_message: Optional[str] = None,
    ):
        """Записать событие аудита"""
        import secrets

        event = AuditEvent(
            event_id=secrets.token_urlsafe(16),
            timestamp=datetime.now(),
            event_type=event_type,
            severity=severity,
            user_id=user_id,
            username=username,
            ip_address=ip_address,
            action=action,
            details=details or {},
            success=success,
            error_message=error_message,
        )

        # Добавляем в буфер
        self.event_buffer.append(event)

        # Записываем буфер если достигнут размер
        if len(self.event_buffer) >= self.buffer_size:
            self._flush_buffer()

        # Логируем также в основной лог
        log_msg = f"[{event_type.value}] {action}"
        if username:
            log_msg += f" by {username}"
        if not success:
            log_msg += f" FAILED: {error_message}"

        if severity == AuditSeverity.CRITICAL:
            self.logger.critical(log_msg)
        elif severity == AuditSeverity.ERROR:
            self.logger.error(log_msg)
        elif severity == AuditSeverity.WARNING:
            self.logger.warning(log_msg)
        else:
            self.logger.info(log_msg)

    def _flush_buffer(self):
        """Записать буфер событий в файл"""
        if not self.event_buffer:
            return

        try:
            # Проверяем ротацию
            self._check_rotation()

            # Записываем события
            with open(self.current_log_file, "a", encoding="utf-8") as f:
                for event in self.event_buffer:
                    event_dict = asdict(event)
                    # Конвертируем enum в строки
                    event_dict["event_type"] = event.event_type.value
                    event_dict["severity"] = event.severity.value
                    event_dict["timestamp"] = event.timestamp.isoformat()

                    f.write(json.dumps(event_dict, ensure_ascii=False) + "\n")

            # Очищаем буфер
            self.event_buffer.clear()

        except Exception as e:
            self.logger.error(f"Failed to flush audit buffer: {e}")

    def _check_rotation(self):
        """Проверить необходимость ротации лога"""
        if not self.current_log_file.exists():
            return

        # Проверяем размер файла
        file_size = self.current_log_file.stat().st_size

        if file_size > self.max_log_size:
            # Ротация по размеру
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_name = f"audit_{timestamp}.jsonl"
            archive_path = self.log_dir / archive_name

            self.current_log_file.rename(archive_path)
            self.logger.info(f"Rotated audit log to {archive_name}")

            # Очистка старых логов
            self._cleanup_old_logs()

    def _cleanup_old_logs(self):
        """Удалить старые логи"""
        from datetime import timedelta

        cutoff_date = datetime.now() - timedelta(days=self.max_log_age_days)

        for log_file in self.log_dir.glob("audit_*.jsonl"):
            try:
                # Парсим дату из имени файла
                timestamp_str = log_file.stem.replace("audit_", "")
                file_date = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")

                if file_date < cutoff_date:
                    log_file.unlink()
                    self.logger.info(f"Deleted old audit log: {log_file.name}")
            except Exception as e:
                self.logger.warning(f"Failed to process log file {log_file}: {e}")

    def query_events(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        event_types: Optional[List[AuditEventType]] = None,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        severity: Optional[AuditSeverity] = None,
        limit: int = 100,
    ) -> List[AuditEvent]:
        """Запросить события аудита

        Args:
            start_date: Начальная дата
            end_date: Конечная дата
            event_types: Фильтр по типам событий
            user_id: Фильтр по ID пользователя
            username: Фильтр по имени пользователя
            severity: Фильтр по уровню важности
            limit: Максимальное количество результатов

        Returns:
            Список событий
        """
        # Сначала записываем буфер
        self._flush_buffer()

        events = []

        # Читаем все log файлы
        log_files = sorted(list(self.log_dir.glob("audit*.jsonl")), reverse=True)  # Новые первыми

        for log_file in log_files:
            try:
                with open(log_file, "r", encoding="utf-8") as f:
                    for line in f:
                        try:
                            event_dict = json.loads(line)

                            # Конвертируем обратно в объекты
                            event_dict["event_type"] = AuditEventType(event_dict["event_type"])
                            event_dict["severity"] = AuditSeverity(event_dict["severity"])
                            event_dict["timestamp"] = datetime.fromisoformat(event_dict["timestamp"])

                            event = AuditEvent(**event_dict)

                            # Применяем фильтры
                            if start_date and event.timestamp < start_date:
                                continue
                            if end_date and event.timestamp > end_date:
                                continue
                            if event_types and event.event_type not in event_types:
                                continue
                            if user_id and event.user_id != user_id:
                                continue
                            if username and event.username != username:
                                continue
                            if severity and event.severity != severity:
                                continue

                            events.append(event)

                            if len(events) >= limit:
                                break
                        except Exception as e:
                            self.logger.warning(f"Failed to parse audit event: {e}")
                            continue

                if len(events) >= limit:
                    break

            except Exception as e:
                self.logger.error(f"Failed to read audit log {log_file}: {e}")
                continue

        return events

    def get_user_activity(self, username: str, days: int = 7) -> Dict[str, Any]:
        """Получить активность пользователя за период

        Returns:
            Статистика активности
        """
        from collections import Counter
        from datetime import timedelta

        start_date = datetime.now() - timedelta(days=days)
        events = self.query_events(start_date=start_date, username=username, limit=10000)

        # Подсчитываем статистику
        event_types = Counter([e.event_type.value for e in events])
        severities = Counter([e.severity.value for e in events])

        failed_events = [e for e in events if not e.success]

        return {
            "username": username,
            "period_days": days,
            "total_events": len(events),
            "event_types": dict(event_types),
            "severities": dict(severities),
            "failed_events": len(failed_events),
            "last_activity": events[0].timestamp.isoformat() if events else None,
        }

    def close(self):
        """Закрыть аудит-логгер"""
        self._flush_buffer()
        self.logger.info("Audit logger closed")


# Глобальный экземпляр аудит-логгера
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger(config=None) -> AuditLogger:
    """Получить глобальный экземпляр аудит-логгера"""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger(config)
    return _audit_logger
