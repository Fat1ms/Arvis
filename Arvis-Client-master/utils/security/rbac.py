"""
Role-Based Access Control (RBAC) system for Arvis
Управление ролями и правами доступа
"""

from enum import Enum
from typing import Dict, List, Optional, Set


class Role(Enum):
    """Роли пользователей"""

    GUEST = "guest"  # Только просмотр, минимальные права
    USER = "user"  # Стандартные функции
    POWER_USER = "power_user"  # Расширенные функции
    ADMIN = "admin"  # Полный доступ


class Permission(Enum):
    """Права доступа"""

    # Базовые права
    CHAT_USE = "chat.use"  # Использование чата
    CHAT_HISTORY_VIEW = "chat.history.view"  # Просмотр истории

    # Модули
    MODULE_WEATHER = "module.weather"  # Модуль погоды
    MODULE_NEWS = "module.news"  # Модуль новостей
    MODULE_CALENDAR = "module.calendar"  # Модуль календаря
    MODULE_SEARCH = "module.search"  # Модуль поиска

    # Системные команды
    SYSTEM_APPS = "system.apps"  # Запуск приложений
    SYSTEM_WEBSITES = "system.websites"  # Открытие сайтов
    SYSTEM_SHUTDOWN = "system.shutdown"  # Выключение системы
    SYSTEM_RESTART = "system.restart"  # Перезагрузка системы
    SYSTEM_LOCK = "system.lock"  # Блокировка системы

    # Скрипты и код
    CODE_EXECUTE = "code.execute"  # Выполнение кода
    SCRIPT_RUN = "script.run"  # Запуск скриптов
    WORKFLOW_EXECUTE = "workflow.execute"  # Выполнение workflows
    WORKFLOW_CREATE = "workflow.create"  # Создание workflows
    WORKFLOW_EDIT = "workflow.edit"  # Редактирование workflows

    # История и данные
    HISTORY_EXPORT = "history.export"  # Экспорт истории
    HISTORY_IMPORT = "history.import"  # Импорт истории
    HISTORY_DELETE = "history.delete"  # Удаление истории
    HISTORY_EDIT = "history.edit"  # Редактирование истории
    HISTORY_GDPR = "history.gdpr"  # GDPR удаление

    # API
    API_USE = "api.use"  # Использование API
    API_MANAGE = "api.manage"  # Управление API

    # Настройки
    SETTINGS_VIEW = "settings.view"  # Просмотр настроек
    SETTINGS_EDIT = "settings.edit"  # Изменение настроек
    SETTINGS_ADVANCED = "settings.advanced"  # Расширенные настройки

    # Управление пользователями
    USER_VIEW = "user.view"  # Просмотр пользователей
    USER_CREATE = "user.create"  # Создание пользователей
    USER_EDIT = "user.edit"  # Редактирование пользователей
    USER_DELETE = "user.delete"  # Удаление пользователей
    USER_ROLE_MANAGE = "user.role.manage"  # Управление ролями

    # Аудит и безопасность
    AUDIT_VIEW = "audit.view"  # Просмотр аудит-лога
    SECURITY_MANAGE = "security.manage"  # Управление безопасностью


# Матрица прав: Role -> Set[Permission]
ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.GUEST: {
        # Минимальные права для гостя
        Permission.CHAT_USE,
        Permission.CHAT_HISTORY_VIEW,
        Permission.MODULE_WEATHER,
        Permission.MODULE_NEWS,
    },
    Role.USER: {
        # Стандартные права пользователя
        Permission.CHAT_USE,
        Permission.CHAT_HISTORY_VIEW,
        Permission.MODULE_WEATHER,
        Permission.MODULE_NEWS,
        Permission.MODULE_CALENDAR,
        Permission.MODULE_SEARCH,
        Permission.SYSTEM_APPS,
        Permission.SYSTEM_WEBSITES,
        Permission.SYSTEM_LOCK,
        Permission.HISTORY_EXPORT,
        Permission.WORKFLOW_EXECUTE,
        Permission.SETTINGS_VIEW,
    },
    Role.POWER_USER: {
        # Расширенные права
        Permission.CHAT_USE,
        Permission.CHAT_HISTORY_VIEW,
        Permission.MODULE_WEATHER,
        Permission.MODULE_NEWS,
        Permission.MODULE_CALENDAR,
        Permission.MODULE_SEARCH,
        Permission.SYSTEM_APPS,
        Permission.SYSTEM_WEBSITES,
        Permission.SYSTEM_LOCK,
        Permission.SYSTEM_RESTART,
        Permission.SCRIPT_RUN,
        Permission.WORKFLOW_EXECUTE,
        Permission.WORKFLOW_CREATE,
        Permission.WORKFLOW_EDIT,
        Permission.HISTORY_EXPORT,
        Permission.HISTORY_IMPORT,
        Permission.HISTORY_DELETE,
        Permission.HISTORY_EDIT,
        Permission.API_USE,
        Permission.SETTINGS_VIEW,
        Permission.SETTINGS_EDIT,
    },
    Role.ADMIN: {
        # Полный доступ
        perm
        for perm in Permission
    },
}


class RBACManager:
    """Менеджер системы ролей и прав доступа"""

    def __init__(self):
        self.current_role: Role = Role.USER  # Роль по умолчанию
        self.current_user: Optional[str] = None  # ID текущего пользователя

    def set_role(self, role: Role):
        """Установить текущую роль пользователя"""
        self.current_role = role

    def set_current_user(self, user_id: Optional[str]):
        """Установить ID текущего пользователя"""
        self.current_user = user_id

    def get_current_user(self) -> Optional[str]:
        """Получить ID текущего пользователя"""
        return self.current_user

    def get_role(self) -> Role:
        """Получить текущую роль"""
        return self.current_role

    def has_permission(self, permission: Permission) -> bool:
        """Проверить наличие права у текущего пользователя"""
        role_perms = ROLE_PERMISSIONS.get(self.current_role, set())
        return permission in role_perms

    def check_permission(self, user_id: Optional[str], permission: Permission) -> bool:
        """Проверить наличие права у конкретного пользователя

        Args:
            user_id: ID пользователя для проверки (может быть None)
            permission: Требуемое право

        Returns:
            True если пользователь имеет право, False иначе
        """
        # Если передан user_id, он должен совпадать с текущим
        if user_id and user_id != self.current_user:
            return False

        # Проверяем право для текущей роли
        return self.has_permission(permission)

    def has_any_permission(self, permissions: List[Permission]) -> bool:
        """Проверить наличие хотя бы одного из прав"""
        return any(self.has_permission(perm) for perm in permissions)

    def has_all_permissions(self, permissions: List[Permission]) -> bool:
        """Проверить наличие всех указанных прав"""
        return all(self.has_permission(perm) for perm in permissions)

    def get_role_permissions(self, role: Optional[Role] = None) -> Set[Permission]:
        """Получить все права роли"""
        if role is None:
            role = self.current_role
        return ROLE_PERMISSIONS.get(role, set())

    def can_execute_system_command(self, command_type: str) -> bool:
        """Проверить возможность выполнения системной команды"""
        command_map = {
            "shutdown": Permission.SYSTEM_SHUTDOWN,
            "restart": Permission.SYSTEM_RESTART,
            "lock": Permission.SYSTEM_LOCK,
            "app": Permission.SYSTEM_APPS,
            "website": Permission.SYSTEM_WEBSITES,
        }

        required_perm = command_map.get(command_type)
        if required_perm:
            return self.has_permission(required_perm)
        return False

    def can_use_module(self, module_name: str) -> bool:
        """Проверить возможность использования модуля"""
        module_map = {
            "weather": Permission.MODULE_WEATHER,
            "news": Permission.MODULE_NEWS,
            "calendar": Permission.MODULE_CALENDAR,
            "search": Permission.MODULE_SEARCH,
        }

        required_perm = module_map.get(module_name)
        if required_perm:
            return self.has_permission(required_perm)
        return True  # Неизвестные модули доступны по умолчанию

    def require_permission(self, permission: Permission) -> bool:
        """Требовать наличие права (для декораторов)"""
        return self.has_permission(permission)

    def get_missing_permissions(self, required: List[Permission]) -> List[Permission]:
        """Получить список недостающих прав"""
        current_perms = self.get_role_permissions()
        return [perm for perm in required if perm not in current_perms]


# Глобальный экземпляр менеджера RBAC
_rbac_manager: Optional[RBACManager] = None


def get_rbac_manager() -> RBACManager:
    """Получить глобальный экземпляр RBAC менеджера"""
    global _rbac_manager
    if _rbac_manager is None:
        _rbac_manager = RBACManager()
    return _rbac_manager


def require_permission(permission: Permission):
    """Декоратор для проверки прав доступа"""

    def decorator(func):
        def wrapper(*args, **kwargs):
            rbac = get_rbac_manager()
            if not rbac.has_permission(permission):
                raise PermissionError(
                    f"Access denied: required permission '{permission.value}' "
                    f"(current role: {rbac.get_role().value})"
                )
            return func(*args, **kwargs)

        return wrapper

    return decorator


def require_role(role: Role):
    """Декоратор для проверки роли"""

    def decorator(func):
        def wrapper(*args, **kwargs):
            rbac = get_rbac_manager()
            current_role = rbac.get_role()

            # Проверяем иерархию ролей
            role_hierarchy = [Role.GUEST, Role.USER, Role.POWER_USER, Role.ADMIN]
            required_level = role_hierarchy.index(role)
            current_level = role_hierarchy.index(current_role)

            if current_level < required_level:
                raise PermissionError(
                    f"Access denied: required role '{role.value}' or higher " f"(current role: {current_role.value})"
                )
            return func(*args, **kwargs)

        return wrapper

    return decorator
