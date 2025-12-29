"""
Пример интеграции RBAC с модулями Arvis
Демонстрация использования системы прав доступа
"""

# ===============================================
# Пример 1: SystemControlModule с RBAC
# ===============================================

from utils.security import AuditEventType, AuditSeverity, Permission, get_audit_logger, get_rbac_manager


class SystemControlModuleWithRBAC:
    """System control с проверкой прав доступа"""

    def __init__(self, config):
        self.config = config
        self.rbac = get_rbac_manager()
        self.audit = get_audit_logger()

    def execute_command(self, command: str, username: str = None) -> str:
        """Выполнение команды с проверкой прав"""
        command_lower = command.lower()

        # Запуск приложений
        if any(word in command_lower for word in ["запусти", "открой"]):
            if not self.rbac.has_permission(Permission.SYSTEM_APPS):
                self.audit.log_event(
                    AuditEventType.PERMISSION_DENIED,
                    f"Attempted to launch app: {command}",
                    username=username,
                    success=False,
                    severity=AuditSeverity.WARNING,
                )
                return "❌ У вас нет прав для запуска приложений"

            result = self.launch_application(command_lower)
            self.audit.log_event(AuditEventType.APP_LAUNCHED, f"Launched application: {command}", username=username)
            return result

        # Открытие сайтов
        elif any(word in command_lower for word in ["сайт", "веб"]):
            if not self.rbac.has_permission(Permission.SYSTEM_WEBSITES):
                return "❌ У вас нет прав для открытия сайтов"

            result = self.open_website(command_lower)
            self.audit.log_event(AuditEventType.WEBSITE_OPENED, f"Opened website: {command}", username=username)
            return result

        # Выключение/перезагрузка
        elif "выключи" in command_lower:
            if not self.rbac.has_permission(Permission.SYSTEM_SHUTDOWN):
                self.audit.log_event(
                    AuditEventType.PERMISSION_DENIED,
                    "Attempted system shutdown without permission",
                    username=username,
                    severity=AuditSeverity.CRITICAL,
                    success=False,
                )
                return "❌ Недостаточно прав для выключения системы (требуется роль Admin)"

            # Критическое действие - требует подтверждения
            self.audit.log_event(
                AuditEventType.SYSTEM_SHUTDOWN,
                "System shutdown initiated",
                username=username,
                severity=AuditSeverity.CRITICAL,
            )
            return self.shutdown_system()

        elif "перезагрузи" in command_lower:
            if not self.rbac.has_permission(Permission.SYSTEM_RESTART):
                return "❌ Недостаточно прав для перезагрузки (требуется Power User или Admin)"

            self.audit.log_event(
                AuditEventType.SYSTEM_RESTART,
                "System restart initiated",
                username=username,
                severity=AuditSeverity.WARNING,
            )
            return self.restart_system()

        return "❓ Команда не распознана"

    def launch_application(self, command: str) -> str:
        # Реализация запуска
        return "✅ Приложение запущено"

    def open_website(self, command: str) -> str:
        # Реализация открытия сайта
        return "✅ Сайт открыт"

    def shutdown_system(self) -> str:
        # Реализация выключения
        return "✅ Система будет выключена через 30 секунд"

    def restart_system(self) -> str:
        # Реализация перезагрузки
        return "✅ Система будет перезагружена через 30 секунд"


# ===============================================
# Пример 2: ConversationHistory с RBAC
# ===============================================


class ConversationHistoryWithRBAC:
    """История разговоров с проверкой прав"""

    def __init__(self, config):
        self.config = config
        self.rbac = get_rbac_manager()
        self.audit = get_audit_logger()
        self.messages = []

    def export_history(self, format: str, username: str = None) -> str:
        """Экспорт истории"""
        if not self.rbac.has_permission(Permission.HISTORY_EXPORT):
            self.audit.log_event(
                AuditEventType.PERMISSION_DENIED,
                f"Attempted history export without permission",
                username=username,
                success=False,
            )
            return None

        # Выполнение экспорта
        self.audit.log_event(
            AuditEventType.HISTORY_EXPORTED,
            f"History exported to {format}",
            username=username,
            details={"format": format, "messages_count": len(self.messages)},
        )
        return f"Exported {len(self.messages)} messages to {format}"

    def import_history(self, file_path: str, username: str = None) -> bool:
        """Импорт истории"""
        if not self.rbac.has_permission(Permission.HISTORY_IMPORT):
            return False

        # Импорт данных
        self.audit.log_event(
            AuditEventType.HISTORY_IMPORTED,
            f"History imported from {file_path}",
            username=username,
            severity=AuditSeverity.WARNING,
        )
        return True

    def clear_history(self, username: str = None) -> bool:
        """Очистка истории"""
        if not self.rbac.has_permission(Permission.HISTORY_DELETE):
            return False

        count = len(self.messages)
        self.messages.clear()

        self.audit.log_event(
            AuditEventType.HISTORY_CLEARED,
            f"Cleared {count} messages",
            username=username,
            severity=AuditSeverity.WARNING,
        )
        return True

    def gdpr_erase(self, username: str = None) -> bool:
        """GDPR удаление всех данных"""
        if not self.rbac.has_permission(Permission.HISTORY_GDPR):
            self.audit.log_event(
                AuditEventType.PERMISSION_DENIED,
                "Attempted GDPR erase without admin permission",
                username=username,
                severity=AuditSeverity.CRITICAL,
                success=False,
            )
            return False

        # Полное удаление
        self.messages.clear()
        # Удаление файлов
        # Удаление архивов

        self.audit.log_event(
            AuditEventType.HISTORY_GDPR_ERASE,
            "GDPR: Complete data erasure performed",
            username=username,
            severity=AuditSeverity.CRITICAL,
        )
        return True


# ===============================================
# Пример 3: ArvisCore с RBAC
# ===============================================


class ArvisCoreWithRBAC:
    """Ядро Arvis с интегрированным RBAC"""

    def __init__(self, config):
        self.config = config
        self.rbac = get_rbac_manager()
        self.audit = get_audit_logger()
        self.current_user = None

        # Модули
        self.system_control = SystemControlModuleWithRBAC(config)
        self.history = ConversationHistoryWithRBAC(config)

    def set_user(self, user):
        """Установить текущего пользователя и его роль"""
        self.current_user = user
        self.rbac.set_role(user.role)

        self.audit.log_event(
            AuditEventType.LOGIN_SUCCESS,
            f"User session started",
            user_id=user.user_id,
            username=user.username,
            details={"role": user.role.value},
        )

    def process_message(self, message: str) -> str:
        """Обработка сообщения с проверкой прав"""
        username = self.current_user.username if self.current_user else None

        # Базовая проверка права на использование чата
        if not self.rbac.has_permission(Permission.CHAT_USE):
            return "❌ У вас нет прав для использования чата"

        # Проверка модулей
        if "погода" in message.lower():
            if not self.rbac.can_use_module("weather"):
                return "❌ Модуль погоды недоступен для вашей роли"
            return self.get_weather()

        elif "новости" in message.lower():
            if not self.rbac.can_use_module("news"):
                return "❌ Модуль новостей недоступен"
            return self.get_news()

        elif "календарь" in message.lower():
            if not self.rbac.can_use_module("calendar"):
                return "❌ Модуль календаря доступен только для роли User и выше"
            return self.get_calendar()

        # Системные команды
        elif any(word in message.lower() for word in ["запусти", "выключи", "перезагрузи"]):
            return self.system_control.execute_command(message, username)

        # LLM обработка
        return self.process_with_llm(message)

    def get_weather(self):
        return "☀️ Сегодня солнечно, +22°C"

    def get_news(self):
        return "📰 Последние новости..."

    def get_calendar(self):
        return "📅 У вас 3 события сегодня"

    def process_with_llm(self, message: str):
        return f"LLM ответ на: {message}"


# ===============================================
# Пример 4: Декораторы для защиты функций
# ===============================================

from utils.security import Role, require_permission, require_role


class AdminPanel:
    """Панель администратора с защитой декораторами"""

    @require_permission(Permission.USER_VIEW)
    def list_users(self):
        """Просмотр списка пользователей (только admin)"""
        return ["admin", "user1", "user2"]

    @require_permission(Permission.USER_CREATE)
    def create_user(self, username: str, password: str):
        """Создание пользователя (только admin)"""
        return f"User {username} created"

    @require_role(Role.POWER_USER)
    def view_logs(self):
        """Просмотр логов (power_user или admin)"""
        return "Log entries: ..."

    @require_permission(Permission.SECURITY_MANAGE)
    def change_security_settings(self, settings: dict):
        """Изменение настроек безопасности (только admin)"""
        return "Security settings updated"


# ===============================================
# Пример 5: Workflow с RBAC
# ===============================================


class WorkflowEngine:
    """Движок workflows с проверкой прав"""

    def __init__(self):
        self.rbac = get_rbac_manager()
        self.audit = get_audit_logger()

    def execute_workflow(self, workflow_data: dict, username: str = None) -> str:
        """Выполнение workflow"""
        if not self.rbac.has_permission(Permission.WORKFLOW_EXECUTE):
            return "❌ Нет прав для выполнения workflows"

        # Проверка требуемых прав workflow
        required_role = workflow_data.get("permissions", {}).get("required_role")
        if required_role:
            current_role = self.rbac.get_role()
            role_hierarchy = [Role.GUEST, Role.USER, Role.POWER_USER, Role.ADMIN]

            if role_hierarchy.index(current_role) < role_hierarchy.index(Role[required_role.upper()]):
                return f"❌ Workflow требует роль {required_role} или выше"

        self.audit.log_event(
            AuditEventType.WORKFLOW_EXECUTED,
            f"Executed workflow: {workflow_data.get('name')}",
            username=username,
            details={"workflow": workflow_data.get("name")},
        )

        return "✅ Workflow выполнен успешно"

    def create_workflow(self, workflow_data: dict, username: str = None) -> bool:
        """Создание нового workflow"""
        if not self.rbac.has_permission(Permission.WORKFLOW_CREATE):
            return False

        self.audit.log_event(
            AuditEventType.WORKFLOW_CREATED, f"Created workflow: {workflow_data.get('name')}", username=username
        )
        return True

    def edit_workflow(self, workflow_id: str, changes: dict, username: str = None) -> bool:
        """Редактирование workflow"""
        if not self.rbac.has_permission(Permission.WORKFLOW_EDIT):
            return False

        self.audit.log_event(
            AuditEventType.WORKFLOW_EDITED,
            f"Edited workflow: {workflow_id}",
            username=username,
            details={"changes": changes},
        )
        return True


# ===============================================
# Пример использования
# ===============================================

if __name__ == "__main__":
    from utils.security import Role, get_auth_manager

    # Инициализация
    auth = get_auth_manager()
    rbac = get_rbac_manager()

    # Создание пользователей
    admin = auth.create_user("admin", "AdminPass123!", Role.ADMIN)
    user = auth.create_user("john", "UserPass123!", Role.USER)
    guest = auth.create_user("guest", "GuestPass123!", Role.GUEST)

    # Тест 1: Гость пытается выключить систему
    print("\n=== Test 1: Guest shutdown ===")
    rbac.set_role(Role.GUEST)
    system = SystemControlModuleWithRBAC(None)
    result = system.execute_command("выключи компьютер", "guest")
    print(result)
    # Вывод: ❌ Недостаточно прав для выключения системы

    # Тест 2: Admin выключает систему
    print("\n=== Test 2: Admin shutdown ===")
    rbac.set_role(Role.ADMIN)
    result = system.execute_command("выключи компьютер", "admin")
    print(result)
    # Вывод: ✅ Система будет выключена через 30 секунд

    # Тест 3: User экспортирует историю
    print("\n=== Test 3: User export ===")
    rbac.set_role(Role.USER)
    history = ConversationHistoryWithRBAC(None)
    result = history.export_history("json", "john")
    print(result)
    # Вывод: Exported 0 messages to json

    # Тест 4: Декораторы
    print("\n=== Test 4: Decorators ===")
    admin_panel = AdminPanel()

    rbac.set_role(Role.USER)
    try:
        admin_panel.list_users()
    except PermissionError as e:
        print(f"User cannot list users: {e}")

    rbac.set_role(Role.ADMIN)
    users = admin_panel.list_users()
    print(f"Admin can list users: {users}")

    # Тест 5: Workflow
    print("\n=== Test 5: Workflow ===")
    workflow_engine = WorkflowEngine()

    workflow = {"name": "morning_briefing", "permissions": {"required_role": "user"}}

    rbac.set_role(Role.GUEST)
    result = workflow_engine.execute_workflow(workflow, "guest")
    print(result)
    # Вывод: ❌ Workflow требует роль user или выше

    rbac.set_role(Role.USER)
    result = workflow_engine.execute_workflow(workflow, "john")
    print(result)
    # Вывод: ✅ Workflow выполнен успешно

    # Просмотр аудит-лога
    print("\n=== Audit Log ===")
    audit = get_audit_logger()
    events = audit.query_events(limit=5)
    for event in events:
        print(f"{event.timestamp.strftime('%H:%M:%S')} - {event.action} by {event.username}")
